__FILENAME__ = widgets
import six
import django

from django import forms
from django.contrib.admin.sites import site
from django.utils.safestring import mark_safe
from django.utils.text import Truncator
from django.template.loader import render_to_string
from django.contrib.admin.widgets import ForeignKeyRawIdWidget


class ForeignKeySearchInput(ForeignKeyRawIdWidget):
    """
    A Widget for displaying ForeignKeys in an autocomplete search input
    instead in a <select> box.
    """
    # Set in subclass to render the widget with a different template
    widget_template = None
    # Set this to the patch of the search view
    search_path = '../foreignkey_autocomplete/'

    def _media(self):
        js_files = ['django_extensions/js/jquery.bgiframe.min.js',
                    'django_extensions/js/jquery.ajaxQueue.js',
                    'django_extensions/js/jquery.autocomplete.js']

        # Use a newer version of jquery if django version <= 1.5.x
        # When removing this compatibility code also remove jquery-1.7.2.min.js file.
        if int(django.get_version()[2]) <= 5:
            js_files.insert(0, 'django_extensions/js/jquery-1.7.2.min.js')

        return forms.Media(css={'all': ('django_extensions/css/jquery.autocomplete.css',)},
                           js=js_files)

    media = property(_media)

    def label_for_value(self, value):
        key = self.rel.get_related_field().name
        obj = self.rel.to._default_manager.get(**{key: value})

        return Truncator(obj).words(14, truncate='...')

    def __init__(self, rel, search_fields, attrs=None):
        self.search_fields = search_fields
        super(ForeignKeySearchInput, self).__init__(rel, site, attrs)

    def render(self, name, value, attrs=None):
        if attrs is None:
            attrs = {}
        #output = [super(ForeignKeySearchInput, self).render(name, value, attrs)]
        opts = self.rel.to._meta
        app_label = opts.app_label
        model_name = opts.object_name.lower()
        related_url = '../../../%s/%s/' % (app_label, model_name)
        params = self.url_parameters()
        if params:
            url = '?' + '&amp;'.join(['%s=%s' % (k, v) for k, v in params.items()])
        else:
            url = ''

        if 'class' not in attrs:
            attrs['class'] = 'vForeignKeyRawIdAdminField'
        # Call the TextInput render method directly to have more control
        output = [forms.TextInput.render(self, name, value, attrs)]

        if value:
            label = self.label_for_value(value)
        else:
            label = six.u('')

        context = {
            'url': url,
            'related_url': related_url,
            'search_path': self.search_path,
            'search_fields': ','.join(self.search_fields),
            'app_label': app_label,
            'model_name': model_name,
            'label': label,
            'name': name,
        }
        output.append(render_to_string(self.widget_template or (
            'django_extensions/widgets/%s/%s/foreignkey_searchinput.html' % (app_label, model_name),
            'django_extensions/widgets/%s/foreignkey_searchinput.html' % app_label,
            'django_extensions/widgets/foreignkey_searchinput.html',
        ), context))
        output.reverse()

        return mark_safe(six.u('').join(output))

########NEW FILE########
__FILENAME__ = encrypted
import sys
import six
from django.db import models
from django.core.exceptions import ImproperlyConfigured
from django import forms
from django.conf import settings
import warnings

try:
    from keyczar import keyczar
except ImportError:
    raise ImportError('Using an encrypted field requires the Keyczar module. '
                      'You can obtain Keyczar from http://www.keyczar.org/.')


class EncryptionWarning(RuntimeWarning):
    pass


class BaseEncryptedField(models.Field):
    prefix = 'enc_str:::'

    def __init__(self, *args, **kwargs):
        if not hasattr(settings, 'ENCRYPTED_FIELD_KEYS_DIR'):
            raise ImproperlyConfigured('You must set the settings.ENCRYPTED_FIELD_KEYS_DIR '
                                       'setting to your Keyczar keys directory.')
        crypt_class = self.get_crypt_class()
        self.crypt = crypt_class.Read(settings.ENCRYPTED_FIELD_KEYS_DIR)

        # Encrypted size is larger than unencrypted
        self.unencrypted_length = max_length = kwargs.get('max_length', None)
        if max_length:
            max_length = len(self.prefix) + len(self.crypt.Encrypt('x' * max_length))
            # TODO: Re-examine if this logic will actually make a large-enough
            # max-length for unicode strings that have non-ascii characters in them.
            kwargs['max_length'] = max_length

        super(BaseEncryptedField, self).__init__(*args, **kwargs)

    def get_crypt_class(self):
        """
        Get the Keyczar class to use.

        The class can be customized with the ENCRYPTED_FIELD_MODE setting. By default,
        this setting is DECRYPT_AND_ENCRYPT. Set this to ENCRYPT to disable decryption.
        This is necessary if you are only providing public keys to Keyczar.

        Returns:
            keyczar.Encrypter if ENCRYPTED_FIELD_MODE is ENCRYPT.
            keyczar.Crypter if ENCRYPTED_FIELD_MODE is DECRYPT_AND_ENCRYPT.

        Override this method to customize the type of Keyczar class returned.
        """

        crypt_type = getattr(settings, 'ENCRYPTED_FIELD_MODE', 'DECRYPT_AND_ENCRYPT')
        if crypt_type == 'ENCRYPT':
            crypt_class_name = 'Encrypter'
        elif crypt_type == 'DECRYPT_AND_ENCRYPT':
            crypt_class_name = 'Crypter'
        else:
            raise ImproperlyConfigured(
                'ENCRYPTED_FIELD_MODE must be either DECRYPT_AND_ENCRYPT '
                'or ENCRYPT, not %s.' % crypt_type)
        return getattr(keyczar, crypt_class_name)

    def to_python(self, value):
        if isinstance(self.crypt.primary_key, keyczar.keys.RsaPublicKey):
            retval = value
        elif value and (value.startswith(self.prefix)):
            if hasattr(self.crypt, 'Decrypt'):
                retval = self.crypt.Decrypt(value[len(self.prefix):])
                if sys.version_info < (3,):
                    if retval:
                        retval = retval.decode('utf-8')
            else:
                retval = value
        else:
            retval = value
        return retval

    def get_db_prep_value(self, value, connection, prepared=False):
        if value and not value.startswith(self.prefix):
            # We need to encode a unicode string into a byte string, first.
            # keyczar expects a bytestring, not a unicode string.
            if sys.version_info < (3,):
                if type(value) == six.types.UnicodeType:
                    value = value.encode('utf-8')
            # Truncated encrypted content is unreadable,
            # so truncate before encryption
            max_length = self.unencrypted_length
            if max_length and len(value) > max_length:
                warnings.warn("Truncating field %s from %d to %d bytes" % (
                    self.name, len(value), max_length), EncryptionWarning
                )
                value = value[:max_length]

            value = self.prefix + self.crypt.Encrypt(value)
        return value

    def deconstruct(self):
        name, path, args, kwargs = super(BaseEncryptedField, self).deconstruct()
        kwargs['max_length'] = self.max_length
        return name, path, args, kwargs


class EncryptedTextField(six.with_metaclass(models.SubfieldBase,
                                            BaseEncryptedField)):
    def get_internal_type(self):
        return 'TextField'

    def formfield(self, **kwargs):
        defaults = {'widget': forms.Textarea}
        defaults.update(kwargs)
        return super(EncryptedTextField, self).formfield(**defaults)

    def south_field_triple(self):
        "Returns a suitable description of this field for South."
        # We'll just introspect the _actual_ field.
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.TextField"
        args, kwargs = introspector(self)
        # That's our definition!
        return (field_class, args, kwargs)


class EncryptedCharField(six.with_metaclass(models.SubfieldBase,
                                            BaseEncryptedField)):
    def __init__(self, *args, **kwargs):
        super(EncryptedCharField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return "CharField"

    def formfield(self, **kwargs):
        defaults = {'max_length': self.max_length}
        defaults.update(kwargs)
        return super(EncryptedCharField, self).formfield(**defaults)

    def south_field_triple(self):
        "Returns a suitable description of this field for South."
        # We'll just introspect the _actual_ field.
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.CharField"
        args, kwargs = introspector(self)
        # That's our definition!
        return (field_class, args, kwargs)

########NEW FILE########
__FILENAME__ = json
"""
JSONField automatically serializes most Python terms to JSON data.
Creates a TEXT field with a default value of "{}".  See test_json.py for
more information.

 from django.db import models
 from django_extensions.db.fields import json

 class LOL(models.Model):
     extra = json.JSONField()
"""
from __future__ import absolute_import
import six
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder

try:
    # Django >= 1.7
    import json
except ImportError:
    # Django <= 1.6 backwards compatibility
    from django.utils import simplejson as json


def dumps(value):
    return DjangoJSONEncoder().encode(value)


def loads(txt):
    value = json.loads(
        txt,
        parse_float=Decimal,
        encoding=settings.DEFAULT_CHARSET
    )
    return value


class JSONDict(dict):
    """
    Hack so repr() called by dumpdata will output JSON instead of
    Python formatted data.  This way fixtures will work!
    """
    def __repr__(self):
        return dumps(self)


class JSONUnicode(six.text_type):
    """
    As above
    """
    def __repr__(self):
        return dumps(self)


class JSONList(list):
    """
    As above
    """
    def __repr__(self):
        return dumps(self)


class JSONField(six.with_metaclass(models.SubfieldBase, models.TextField)):
    """JSONField is a generic textfield that neatly serializes/unserializes
    JSON objects seamlessly.  Main thingy must be a dict object."""

    def __init__(self, *args, **kwargs):
        default = kwargs.get('default', None)
        if default is None:
            kwargs['default'] = '{}'
        elif isinstance(default, (list, dict)):
            kwargs['default'] = dumps(default)
        models.TextField.__init__(self, *args, **kwargs)

    def to_python(self, value):
        """Convert our string value to JSON after we load it from the DB"""
        if value is None or value == '':
            return {}
        elif isinstance(value, six.string_types):
            res = loads(value)
            if isinstance(res, dict):
                return JSONDict(**res)
            elif isinstance(res, six.string_types):
                return JSONUnicode(res)
            elif isinstance(res, list):
                return JSONList(res)
            return res
        else:
            return value

    def get_db_prep_save(self, value, connection, **kwargs):
        """Convert our JSON object to a string before we save"""
        if value is None and self.null:
            return None
        return super(JSONField, self).get_db_prep_save(dumps(value), connection=connection)

    def south_field_triple(self):
        """Returns a suitable description of this field for South."""
        # We'll just introspect the _actual_ field.
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.TextField"
        args, kwargs = introspector(self)
        # That's our definition!
        return (field_class, args, kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(JSONField, self).deconstruct()
        if self.default == '{}':
            del kwargs['default']
        return name, path, args, kwargs

########NEW FILE########
__FILENAME__ = models
"""
Django Extensions abstract base model classes.
"""
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django_extensions.db.fields import (ModificationDateTimeField,
                                         CreationDateTimeField, AutoSlugField)

try:
    from django.utils.timezone import now as datetime_now
    assert datetime_now
except ImportError:
    import datetime
    datetime_now = datetime.datetime.now


class TimeStampedModel(models.Model):
    """ TimeStampedModel
    An abstract base class model that provides self-managed "created" and
    "modified" fields.
    """
    created = CreationDateTimeField(_('created'))
    modified = ModificationDateTimeField(_('modified'))

    class Meta:
        get_latest_by = 'modified'
        ordering = ('-modified', '-created',)
        abstract = True


class TitleSlugDescriptionModel(models.Model):
    """ TitleSlugDescriptionModel
    An abstract base class model that provides title and description fields
    and a self-managed "slug" field that populates from the title.
    """
    title = models.CharField(_('title'), max_length=255)
    slug = AutoSlugField(_('slug'), populate_from='title')
    description = models.TextField(_('description'), blank=True, null=True)

    class Meta:
        abstract = True


class ActivatorQuerySet(models.query.QuerySet):
    """ ActivatorQuerySet
    Query set that returns statused results
    """
    def active(self):
        """ Returns active query set """
        return self.filter(status=ActivatorModel.ACTIVE_STATUS)

    def inactive(self):
        """ Returns inactive query set """
        return self.filter(status=ActivatorModel.INACTIVE_STATUS)


class ActivatorModelManager(models.Manager):
    """ ActivatorModelManager
    Manager to return instances of ActivatorModel: SomeModel.objects.active() / .inactive()
    """
    def get_query_set(self):
        """ Proxy to `get_queryset`, drop this when Django < 1.6 is no longer supported """
        return self.get_queryset()

    def get_queryset(self):
        """ Use ActivatorQuerySet for all results """
        return ActivatorQuerySet(model=self.model, using=self._db)

    def active(self):
        """ Returns active instances of ActivatorModel: SomeModel.objects.active(),
        proxy to ActivatorQuerySet.active """
        return self.get_query_set().active()

    def inactive(self):
        """ Returns inactive instances of ActivatorModel: SomeModel.objects.inactive(),
        proxy to ActivatorQuerySet.inactive """
        return self.get_query_set().inactive()


class ActivatorModel(models.Model):
    """ ActivatorModel
    An abstract base class model that provides activate and deactivate fields.
    """
    INACTIVE_STATUS, ACTIVE_STATUS = range(2)
    STATUS_CHOICES = (
        (INACTIVE_STATUS, _('Inactive')),
        (ACTIVE_STATUS, _('Active')),
    )
    status = models.IntegerField(_('status'), choices=STATUS_CHOICES, default=ACTIVE_STATUS)
    activate_date = models.DateTimeField(blank=True, null=True, help_text=_('keep empty for an immediate activation'))
    deactivate_date = models.DateTimeField(blank=True, null=True, help_text=_('keep empty for indefinite activation'))
    objects = ActivatorModelManager()

    class Meta:
        ordering = ('status', '-activate_date',)
        abstract = True

    def save(self, *args, **kwargs):
        if not self.activate_date:
            self.activate_date = datetime_now()
        super(ActivatorModel, self).save(*args, **kwargs)

########NEW FILE########
__FILENAME__ = future_1_5
"""
A forwards compatibility module.

Implements some features of Django 1.5 related to the 'Custom User Model' feature
when the application is run with a lower version of Django.
"""
from __future__ import unicode_literals

from django.contrib.auth.models import User

User.USERNAME_FIELD = "username"
User.get_username = lambda self: self.username


def get_user_model():
    return User

########NEW FILE########
__FILENAME__ = cache_cleanup
"""
Daily cleanup job.

Can be run as a cronjob to clean out old data from the database (only expired
sessions at the moment).
"""

import six
from django_extensions.management.jobs import DailyJob


class Job(DailyJob):
    help = "Cache (db) cleanup Job"

    def execute(self):
        from django.conf import settings
        from django.db import transaction
        import os

        try:
            from django.utils import timezone
        except ImportError:
            timezone = None

        if hasattr(settings, 'CACHES') and timezone:
            from django.core.cache import get_cache
            from django.db import router, connections

            for cache_name, cache_options in six.iteritems(settings.CACHES):
                if cache_options['BACKEND'].endswith("DatabaseCache"):
                    cache = get_cache(cache_name)
                    db = router.db_for_write(cache.cache_model_class)
                    cursor = connections[db].cursor()
                    now = timezone.now()
                    cache._cull(db, cursor, now)
                    transaction.commit_unless_managed(using=db)
            return

        if hasattr(settings, 'CACHE_BACKEND'):
            if settings.CACHE_BACKEND.startswith('db://'):
                from django.db import connection
                os.environ['TZ'] = settings.TIME_ZONE
                table_name = settings.CACHE_BACKEND[5:]
                cursor = connection.cursor()
                cursor.execute(
                    "DELETE FROM %s WHERE %s < current_timestamp;" % (
                        connection.ops.quote_name(table_name),
                        connection.ops.quote_name('expires')
                    )
                )
                transaction.commit_unless_managed()

########NEW FILE########
__FILENAME__ = daily_cleanup
"""
Daily cleanup job.

Can be run as a cronjob to clean out old data from the database (only expired
sessions at the moment).
"""

from django_extensions.management.jobs import DailyJob


class Job(DailyJob):
    help = "Django Daily Cleanup Job"

    def execute(self):
        from django.core import management
        management.call_command("cleanup")

########NEW FILE########
__FILENAME__ = base
import sys

from django.core.management.base import BaseCommand
from django.utils.log import getLogger


logger = getLogger('django.commands')


class LoggingBaseCommand(BaseCommand):
    """
    A subclass of BaseCommand that logs run time errors to `django.commands`.
    To use this, create a management command subclassing LoggingBaseCommand:

        from django_extensions.management.base import LoggingBaseCommand

        class Command(LoggingBaseCommand):
            help = 'Test error'

            def handle(self, *args, **options):
                raise Exception


    And then define a logging handler in settings.py:

        LOGGING = {
            ... # Other stuff here

            'handlers': {
                'mail_admins': {
                    'level': 'ERROR',
                    'filters': ['require_debug_false'],
                    'class': 'django.utils.log.AdminEmailHandler'
                },
            },
            'loggers': {
                'django.commands': {
                    'handlers': ['mail_admins'],
                    'level': 'ERROR',
                    'propagate': False,
                },
            }

        }

    """

    def execute(self, *args, **options):
        try:
            super(LoggingBaseCommand, self).execute(*args, **options)
        except Exception as e:
            logger.error(e, exc_info=sys.exc_info(), extra={'status_code': 500})
            raise

########NEW FILE########
__FILENAME__ = color
"""
Sets up the terminal color scheme.
"""

from django.core.management import color
from django.utils import termcolors


def color_style():
    style = color.color_style()
    if color.supports_color():
        style.INFO = termcolors.make_style(fg='green')
        style.WARN = termcolors.make_style(fg='yellow')
        style.BOLD = termcolors.make_style(opts=('bold',))
        style.URL = termcolors.make_style(fg='green', opts=('bold',))
        style.MODULE = termcolors.make_style(fg='yellow')
        style.MODULE_NAME = termcolors.make_style(opts=('bold',))
        style.URL_NAME = termcolors.make_style(fg='red')
    return style

########NEW FILE########
__FILENAME__ = clean_pyc
import os
import time
import fnmatch
import warnings
from django.core.management.base import NoArgsCommand
from django.conf import settings
from django_extensions.management.utils import get_project_root
from optparse import make_option
from os.path import join as _j


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--optimize', '-o', '-O', action='store_true',
                    dest='optimize',
                    help='Remove optimized python bytecode files'),
        make_option('--path', '-p', action='store', dest='path',
                    help='Specify path to recurse into'),
    )
    help = "Removes all python bytecode compiled files from the project."

    requires_model_validation = False

    def handle_noargs(self, **options):
        project_root = options.get("path", getattr(settings, 'BASE_DIR', None))
        if not project_root:
            project_root = getattr(settings, 'BASE_DIR', None)

        verbosity = int(options.get("verbosity"))
        if not project_root:
            warnings.warn("settings.BASE_DIR or specifying --path will become mandatory in 1.4.0", DeprecationWarning)
            project_root = get_project_root()
            if verbosity > 0:
                self.stdout.write("""No path specified and settings.py does not contain BASE_DIR.
Assuming '%s' is the project root.

Please add BASE_DIR to your settings.py future versions 1.4.0 and higher of Django-Extensions
will require either BASE_DIR or specifying the --path option.

Waiting for 30 seconds. Press ctrl-c to abort.
""" % project_root)
                if getattr(settings, 'CLEAN_PYC_DEPRECATION_WAIT', True):
                    try:
                        time.sleep(30)
                    except KeyboardInterrupt:
                        self.stdout.write("Aborted\n")
                        return
        exts = options.get("optimize", False) and "*.py[co]" or "*.pyc"

        for root, dirs, filenames in os.walk(project_root):
            for filename in fnmatch.filter(filenames, exts):
                full_path = _j(root, filename)
                if verbosity > 1:
                    self.stdout.write("%s\n" % full_path)
                os.remove(full_path)

########NEW FILE########
__FILENAME__ = compile_pyc
import os
import time
import fnmatch
import warnings
import py_compile
from django.core.management.base import NoArgsCommand
from django.conf import settings
from django_extensions.management.utils import get_project_root
from optparse import make_option
from os.path import join as _j


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--path', '-p', action='store', dest='path',
                    help='Specify path to recurse into'),
    )
    help = "Compile python bytecode files for the project."

    requires_model_validation = False

    def handle_noargs(self, **options):
        project_root = options.get("path", None)
        if not project_root:
            project_root = getattr(settings, 'BASE_DIR', None)

        verbosity = int(options.get("verbosity"))
        if not project_root:
            warnings.warn("settings.BASE_DIR or specifying --path will become mandatory in 1.4.0", DeprecationWarning)
            project_root = get_project_root()
            if verbosity > 0:
                self.stdout.write("""No path specified and settings.py does not contain BASE_DIR.
Assuming '%s' is the project root.

Please add BASE_DIR to your settings.py future versions 1.4.0 and higher of Django-Extensions
will require either BASE_DIR or specifying the --path option.

Waiting for 30 seconds. Press ctrl-c to abort.
""" % project_root)
                if getattr(settings, 'COMPILE_PYC_DEPRECATION_WAIT', True):
                    try:
                        time.sleep(30)
                    except KeyboardInterrupt:
                        self.stdout.write("Aborted\n")
                        return

        for root, dirs, filenames in os.walk(project_root):
            for filename in fnmatch.filter(filenames, '*.py'):
                full_path = _j(root, filename)
                if verbosity > 1:
                    self.stdout.write("Compiling %s...\n" % full_path)
                py_compile.compile(full_path)

########NEW FILE########
__FILENAME__ = create_app
import os
import re
import sys
import django_extensions
from django.conf import settings
from django.db import connection
from django.core.management.base import CommandError, LabelCommand
from django.template import Template, Context
from django_extensions.settings import REPLACEMENTS
from django_extensions.utils.dia2django import dia2django
from django_extensions.management.utils import _make_writeable
from optparse import make_option


class Command(LabelCommand):
    option_list = LabelCommand.option_list + (
        make_option('--template', '-t', action='store', dest='app_template',
                    help='The path to the app template'),
        make_option('--parent_path', '-p', action='store', dest='parent_path',
                    help='The parent path of the application to be created'),
        make_option('-d', action='store_true', dest='dia_parse',
                    help='Generate model.py and admin.py from [APP_NAME].dia file'),
        make_option('--diagram', action='store', dest='dia_path',
                    help='The diagram path of the app to be created. -d is implied'),
    )

    help = ("Creates an application directory structure for the specified application name.")
    args = "APP_NAME"
    label = 'application name'

    requires_model_validation = False
    can_import_settings = True

    def handle_label(self, label, **options):
        project_dir = os.getcwd()
        project_name = os.path.split(project_dir)[-1]
        app_name = label
        app_template = options.get('app_template') or os.path.join(django_extensions.__path__[0], 'conf', 'app_template')
        app_dir = os.path.join(options.get('parent_path') or project_dir, app_name)
        dia_path = options.get('dia_path') or os.path.join(project_dir, '%s.dia' % app_name)

        if not os.path.exists(app_template):
            raise CommandError("The template path, %r, does not exist." % app_template)

        if not re.search(r'^\w+$', label):
            raise CommandError("%r is not a valid application name. Please use only numbers, letters and underscores." % label)

        dia_parse = options.get('dia_path') or options.get('dia_parse')
        if dia_parse:
            if not os.path.exists(dia_path):
                raise CommandError("The diagram path, %r, does not exist." % dia_path)
            if app_name in settings.INSTALLED_APPS:
                raise CommandError("The application %s should not be defined in the settings file. Please remove %s now, and add it after using this command." % (app_name, app_name))
            tables = [name for name in connection.introspection.table_names() if name.startswith('%s_' % app_name)]
            if tables:
                raise CommandError("%r application has tables in the database. Please delete them." % app_name)

        try:
            os.makedirs(app_dir)
        except OSError as e:
            raise CommandError(e)

        copy_template(app_template, app_dir, project_name, app_name)

        if dia_parse:
            generate_models_and_admin(dia_path, app_dir, project_name, app_name)
            print("Application %r created." % app_name)
            print("Please add now %r and any other dependent application in settings.INSTALLED_APPS, and run 'manage syncdb'" % app_name)


def copy_template(app_template, copy_to, project_name, app_name):
    """copies the specified template directory to the copy_to location"""
    import shutil

    app_template = os.path.normpath(app_template)
    # walks the template structure and copies it
    for d, subdirs, files in os.walk(app_template):
        relative_dir = d[len(app_template) + 1:]
        d_new = os.path.join(copy_to, relative_dir).replace('app_name', app_name)
        if relative_dir and not os.path.exists(d_new):
            os.mkdir(d_new)
        for i, subdir in enumerate(subdirs):
            if subdir.startswith('.'):
                del subdirs[i]
        replacements = {'app_name': app_name, 'project_name': project_name}
        replacements.update(REPLACEMENTS)
        for f in files:
            if f.endswith('.pyc') or f.startswith('.DS_Store'):
                continue
            path_old = os.path.join(d, f)
            path_new = os.path.join(d_new, f.replace('app_name', app_name))
            if os.path.exists(path_new):
                path_new = os.path.join(d_new, f)
                if os.path.exists(path_new):
                    continue
            if path_new.endswith('.tmpl'):
                path_new = path_new[:-5]
            fp_old = open(path_old, 'r')
            fp_new = open(path_new, 'w')
            fp_new.write(Template(fp_old.read()).render(Context(replacements)))
            fp_old.close()
            fp_new.close()
            try:
                shutil.copymode(path_old, path_new)
                _make_writeable(path_new)
            except OSError:
                sys.stderr.write("Notice: Couldn't set permission bits on %s. You're probably using an uncommon filesystem setup. No problem.\n" % path_new)


def generate_models_and_admin(dia_path, app_dir, project_name, app_name):
    """Generates the models.py and admin.py files"""

    def format_text(string, indent=False):
        """format string in lines of 80 or less characters"""
        retval = ''
        while string:
            line = string[:77]
            last_space = line.rfind(' ')
            if last_space != -1 and len(string) > 77:
                retval += "%s \\\n" % string[:last_space]
                string = string[last_space + 1:]
            else:
                retval += "%s\n" % string
                string = ''
            if string and indent:
                string = '    %s' % string
        return retval

    model_path = os.path.join(app_dir, 'models.py')
    admin_path = os.path.join(app_dir, 'admin.py')

    models_txt = 'from django.db import models\n' + dia2django(dia_path)
    open(model_path, 'w').write(models_txt)

    classes = re.findall('class (\w+)', models_txt)
    admin_txt = 'from django.contrib.admin import site, ModelAdmin\n' + format_text('from %s.%s.models import %s' % (project_name, app_name, ', '.join(classes)), indent=True)
    admin_txt += format_text('\n\n%s' % '\n'.join(map((lambda t: 'site.register(%s)' % t), classes)))
    open(admin_path, 'w').write(admin_txt)

########NEW FILE########
__FILENAME__ = create_command
import os
import sys
from django.core.management.base import AppCommand
from django_extensions.management.utils import _make_writeable
from optparse import make_option


class Command(AppCommand):
    option_list = AppCommand.option_list + (
        make_option('--name', '-n', action='store', dest='command_name', default='sample',
                    help='The name to use for the management command'),
        make_option('--base', '-b', action='store', dest='base_command', default='Base',
                    help='The base class used for implementation of this command. Should be one of Base, App, Label, or NoArgs'),
    )

    help = ("Creates a Django management command directory structure for the given app name"
            " in the app's directory.")
    args = "[appname]"
    label = 'application name'

    requires_model_validation = False
    # Can't import settings during this command, because they haven't
    # necessarily been created.
    can_import_settings = True

    def handle_app(self, app, **options):
        app_dir = os.path.dirname(app.__file__)
        copy_template('command_template', app_dir, options.get('command_name'), '%sCommand' % options.get('base_command'))


def copy_template(template_name, copy_to, command_name, base_command):
    """copies the specified template directory to the copy_to location"""
    import django_extensions
    import shutil

    template_dir = os.path.join(django_extensions.__path__[0], 'conf', template_name)

    handle_method = "handle(self, *args, **options)"
    if base_command == 'AppCommand':
        handle_method = "handle_app(self, app, **options)"
    elif base_command == 'LabelCommand':
        handle_method = "handle_label(self, label, **options)"
    elif base_command == 'NoArgsCommand':
        handle_method = "handle_noargs(self, **options)"

    # walks the template structure and copies it
    for d, subdirs, files in os.walk(template_dir):
        relative_dir = d[len(template_dir) + 1:]
        if relative_dir and not os.path.exists(os.path.join(copy_to, relative_dir)):
            os.mkdir(os.path.join(copy_to, relative_dir))
        for i, subdir in enumerate(subdirs):
            if subdir.startswith('.'):
                del subdirs[i]
        for f in files:
            if f.endswith('.pyc') or f.startswith('.DS_Store'):
                continue
            path_old = os.path.join(d, f)
            path_new = os.path.join(copy_to, relative_dir, f.replace('sample', command_name))
            if os.path.exists(path_new):
                path_new = os.path.join(copy_to, relative_dir, f)
                if os.path.exists(path_new):
                    continue
            path_new = path_new.rstrip(".tmpl")
            fp_old = open(path_old, 'r')
            fp_new = open(path_new, 'w')
            fp_new.write(fp_old.read().replace('{{ command_name }}', command_name).replace('{{ base_command }}', base_command).replace('{{ handle_method }}', handle_method))
            fp_old.close()
            fp_new.close()
            try:
                shutil.copymode(path_old, path_new)
                _make_writeable(path_new)
            except OSError:
                sys.stderr.write("Notice: Couldn't set permission bits on %s. You're probably using an uncommon filesystem setup. No problem.\n" % path_new)

########NEW FILE########
__FILENAME__ = create_jobs
import os
import sys
from django.core.management.base import AppCommand
from django_extensions.management.utils import _make_writeable


class Command(AppCommand):
    help = ("Creates a Django jobs command directory structure for the given app name in the current directory.")
    args = "[appname]"
    label = 'application name'

    requires_model_validation = False
    # Can't import settings during this command, because they haven't
    # necessarily been created.
    can_import_settings = True

    def handle_app(self, app, **options):
        app_dir = os.path.dirname(app.__file__)
        copy_template('jobs_template', app_dir)


def copy_template(template_name, copy_to):
    """copies the specified template directory to the copy_to location"""
    import django_extensions
    import shutil

    template_dir = os.path.join(django_extensions.__path__[0], 'conf', template_name)

    # walks the template structure and copies it
    for d, subdirs, files in os.walk(template_dir):
        relative_dir = d[len(template_dir) + 1:]
        if relative_dir and not os.path.exists(os.path.join(copy_to, relative_dir)):
            os.mkdir(os.path.join(copy_to, relative_dir))
        for i, subdir in enumerate(subdirs):
            if subdir.startswith('.'):
                del subdirs[i]
        for f in files:
            if f.endswith('.pyc') or f.startswith('.DS_Store'):
                continue
            path_old = os.path.join(d, f)
            path_new = os.path.join(copy_to, relative_dir, f)
            if os.path.exists(path_new):
                path_new = os.path.join(copy_to, relative_dir, f)
                if os.path.exists(path_new):
                    continue
            path_new = path_new.rstrip(".tmpl")
            fp_old = open(path_old, 'r')
            fp_new = open(path_new, 'w')
            fp_new.write(fp_old.read())
            fp_old.close()
            fp_new.close()
            try:
                shutil.copymode(path_old, path_new)
                _make_writeable(path_new)
            except OSError:
                sys.stderr.write("Notice: Couldn't set permission bits on %s. You're probably using an uncommon filesystem setup. No problem.\n" % path_new)

########NEW FILE########
__FILENAME__ = create_template_tags
import os
import sys
from django.core.management.base import AppCommand
from django_extensions.management.utils import _make_writeable
from optparse import make_option


class Command(AppCommand):
    option_list = AppCommand.option_list + (
        make_option('--name', '-n', action='store', dest='tag_library_name', default='appname_tags',
                    help='The name to use for the template tag base name. Defaults to `appname`_tags.'),
        make_option('--base', '-b', action='store', dest='base_command', default='Base',
                    help='The base class used for implementation of this command. Should be one of Base, App, Label, or NoArgs'),
    )

    help = ("Creates a Django template tags directory structure for the given app name"
            " in the apps's directory")
    args = "[appname]"
    label = 'application name'

    requires_model_validation = False
    # Can't import settings during this command, because they haven't
    # necessarily been created.
    can_import_settings = True

    def handle_app(self, app, **options):
        app_dir = os.path.dirname(app.__file__)
        tag_library_name = options.get('tag_library_name')
        if tag_library_name == 'appname_tags':
            tag_library_name = '%s_tags' % os.path.basename(app_dir)
        copy_template('template_tags_template', app_dir, tag_library_name)


def copy_template(template_name, copy_to, tag_library_name):
    """copies the specified template directory to the copy_to location"""
    import django_extensions
    import shutil

    template_dir = os.path.join(django_extensions.__path__[0], 'conf', template_name)

    # walks the template structure and copies it
    for d, subdirs, files in os.walk(template_dir):
        relative_dir = d[len(template_dir) + 1:]
        if relative_dir and not os.path.exists(os.path.join(copy_to, relative_dir)):
            os.mkdir(os.path.join(copy_to, relative_dir))
        for i, subdir in enumerate(subdirs):
            if subdir.startswith('.'):
                del subdirs[i]
        for f in files:
            if f.endswith('.pyc') or f.startswith('.DS_Store'):
                continue
            path_old = os.path.join(d, f)
            path_new = os.path.join(copy_to, relative_dir, f.replace('sample', tag_library_name))
            if os.path.exists(path_new):
                path_new = os.path.join(copy_to, relative_dir, f)
                if os.path.exists(path_new):
                    continue
            path_new = path_new.rstrip(".tmpl")
            fp_old = open(path_old, 'r')
            fp_new = open(path_new, 'w')
            fp_new.write(fp_old.read())
            fp_old.close()
            fp_new.close()
            try:
                shutil.copymode(path_old, path_new)
                _make_writeable(path_new)
            except OSError:
                sys.stderr.write("Notice: Couldn't set permission bits on %s. You're probably using an uncommon filesystem setup. No problem.\n" % path_new)

########NEW FILE########
__FILENAME__ = describe_form
from django.core.management.base import LabelCommand, CommandError
from django.utils.encoding import force_unicode


class Command(LabelCommand):
    help = "Outputs the specified model as a form definition to the shell."
    args = "[app.model]"
    label = 'application name and model name'

    requires_model_validation = True
    can_import_settings = True

    def handle_label(self, label, **options):
        return describe_form(label)


def describe_form(label, fields=None):
    """
    Returns a string describing a form based on the model
    """
    from django.db.models.loading import get_model
    try:
        app_name, model_name = label.split('.')[-2:]
    except (IndexError, ValueError):
        raise CommandError("Need application and model name in the form: appname.model")
    model = get_model(app_name, model_name)

    opts = model._meta
    field_list = []
    for f in opts.fields + opts.many_to_many:
        if not f.editable:
            continue
        if fields and f.name not in fields:
            continue
        formfield = f.formfield()
        if '__dict__' not in dir(formfield):
            continue
        attrs = {}
        valid_fields = ['required', 'initial', 'max_length', 'min_length', 'max_value', 'min_value', 'max_digits', 'decimal_places', 'choices', 'help_text', 'label']
        for k, v in formfield.__dict__.items():
            if k in valid_fields and v is not None:
                # ignore defaults, to minimize verbosity
                if k == 'required' and v:
                    continue
                if k == 'help_text' and not v:
                    continue
                if k == 'widget':
                    attrs[k] = v.__class__
                elif k in ['help_text', 'label']:
                    attrs[k] = force_unicode(v).strip()
                else:
                    attrs[k] = v

        params = ', '.join(['%s=%r' % (k, v) for k, v in attrs.items()])
        field_list.append('    %(field_name)s = forms.%(field_type)s(%(params)s)' % {
            'field_name': f.name,
            'field_type': formfield.__class__.__name__,
            'params': params
        })
    return '''
from django import forms
from %(app_name)s.models import %(object_name)s

class %(object_name)sForm(forms.Form):
%(field_list)s
''' % {'app_name': app_name, 'object_name': opts.object_name, 'field_list': '\n'.join(field_list)}

########NEW FILE########
__FILENAME__ = dumpscript
# -*- coding: UTF-8 -*-
"""
      Title: Dumpscript management command
    Project: Hardytools (queryset-refactor version)
     Author: Will Hardy (http://willhardy.com.au)
       Date: June 2008
      Usage: python manage.py dumpscript appname > scripts/scriptname.py
  $Revision: 217 $

Description:
    Generates a Python script that will repopulate the database using objects.
    The advantage of this approach is that it is easy to understand, and more
    flexible than directly populating the database, or using XML.

    * It also allows for new defaults to take effect and only transfers what is
      needed.
    * If a new database schema has a NEW ATTRIBUTE, it is simply not
      populated (using a default value will make the transition smooth :)
    * If a new database schema REMOVES AN ATTRIBUTE, it is simply ignored
      and the data moves across safely (I'm assuming we don't want this
      attribute anymore.
    * Problems may only occur if there is a new model and is now a required
      ForeignKey for an existing model. But this is easy to fix by editing the
      populate script. Half of the job is already done as all ForeingKey
      lookups occur though the locate_object() function in the generated script.

Improvements:
    See TODOs and FIXMEs scattered throughout :-)

"""

import sys
import datetime
import six

import django
from django.db.models import AutoField, BooleanField, FileField, ForeignKey, DateField, DateTimeField
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand

# conditional import, force_unicode was renamed in Django 1.5
from django.contrib.contenttypes.models import ContentType
try:
    from django.utils.encoding import smart_unicode, force_unicode  # NOQA
except ImportError:
    from django.utils.encoding import smart_text as smart_unicode, force_text as force_unicode  # NOQA


def orm_item_locator(orm_obj):
    """
    This function is called every time an object that will not be exported is required.
    Where orm_obj is the referred object.
    We postpone the lookup to locate_object() which will be run on the generated script

    """

    the_class = orm_obj._meta.object_name
    original_class = the_class
    pk_name = orm_obj._meta.pk.name
    original_pk_name = pk_name
    pk_value = getattr(orm_obj, pk_name)

    while hasattr(pk_value, "_meta") and hasattr(pk_value._meta, "pk") and hasattr(pk_value._meta.pk, "name"):
        the_class = pk_value._meta.object_name
        pk_name = pk_value._meta.pk.name
        pk_value = getattr(pk_value, pk_name)

    clean_dict = make_clean_dict(orm_obj.__dict__)

    for key in clean_dict:
        v = clean_dict[key]
        if v is not None and not isinstance(v, (six.string_types, six.integer_types, float, datetime.datetime)):
            clean_dict[key] = six.u("%s" % v)

    output = """ importer.locate_object(%s, "%s", %s, "%s", %s, %s ) """ % (
        original_class, original_pk_name,
        the_class, pk_name, pk_value, clean_dict
    )
    return output


class Command(BaseCommand):
    help = 'Dumps the data as a customised python script.'
    args = '[appname ...]'

    def handle(self, *app_labels, **options):

        # Get the models we want to export
        models = get_models(app_labels)

        # A dictionary is created to keep track of all the processed objects,
        # so that foreign key references can be made using python variable names.
        # This variable "context" will be passed around like the town bicycle.
        context = {}

        # Create a dumpscript object and let it format itself as a string
        self.stdout.write(str(Script(models=models, context=context, stdout=self.stdout, stderr=self.stderr)))
        self.stdout.write("\n")


def get_models(app_labels):
    """ Gets a list of models for the given app labels, with some exceptions.
        TODO: If a required model is referenced, it should also be included.
        Or at least discovered with a get_or_create() call.
    """

    from django.db.models import get_app, get_apps, get_model
    from django.db.models import get_models as get_all_models

    # These models are not to be output, e.g. because they can be generated automatically
    # TODO: This should be "appname.modelname" string
    EXCLUDED_MODELS = (ContentType, )

    models = []

    # If no app labels are given, return all
    if not app_labels:
        for app in get_apps():
            models += [m for m in get_all_models(app) if m not in EXCLUDED_MODELS]

    # Get all relevant apps
    for app_label in app_labels:
        # If a specific model is mentioned, get only that model
        if "." in app_label:
            app_label, model_name = app_label.split(".", 1)
            models.append(get_model(app_label, model_name))
        # Get all models for a given app
        else:
            models += [m for m in get_all_models(get_app(app_label)) if m not in EXCLUDED_MODELS]

    return models


class Code(object):
    """ A snippet of python script.
        This keeps track of import statements and can be output to a string.
        In the future, other features such as custom indentation might be included
        in this class.
    """

    def __init__(self, indent=-1, stdout=None, stderr=None):

        if not stdout:
            stdout = sys.stdout
        if not stderr:
            stderr = sys.stderr

        self.indent = indent
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self):
        """ Returns a string representation of this script.
        """
        if self.imports:
            self.stderr.write(repr(self.import_lines))
            return flatten_blocks([""] + self.import_lines + [""] + self.lines, num_indents=self.indent)
        else:
            return flatten_blocks(self.lines, num_indents=self.indent)

    def get_import_lines(self):
        """ Takes the stored imports and converts them to lines
        """
        if self.imports:
            return ["from %s import %s" % (value, key) for key, value in self.imports.items()]
        else:
            return []
    import_lines = property(get_import_lines)


class ModelCode(Code):
    " Produces a python script that can recreate data for a given model class. "

    def __init__(self, model, context=None, stdout=None, stderr=None):
        super(ModelCode, self).__init__(indent=0, stdout=stdout, stderr=stderr)
        self.model = model
        if context is None:
            context = {}
        self.context = context
        self.instances = []

    def get_imports(self):
        """ Returns a dictionary of import statements, with the variable being
            defined as the key.
        """
        return {self.model.__name__: smart_unicode(self.model.__module__)}
    imports = property(get_imports)

    def get_lines(self):
        """ Returns a list of lists or strings, representing the code body.
            Each list is a block, each string is a statement.
        """
        code = []

        for counter, item in enumerate(self.model._default_manager.all()):
            instance = InstanceCode(instance=item, id=counter + 1, context=self.context, stdout=self.stdout, stderr=self.stderr)
            self.instances.append(instance)
            if instance.waiting_list:
                code += instance.lines

        # After each instance has been processed, try again.
        # This allows self referencing fields to work.
        for instance in self.instances:
            if instance.waiting_list:
                code += instance.lines

        return code

    lines = property(get_lines)


class InstanceCode(Code):
    " Produces a python script that can recreate data for a given model instance. "

    def __init__(self, instance, id, context=None, stdout=None, stderr=None):
        """ We need the instance in question and an id """

        super(InstanceCode, self).__init__(indent=0, stdout=stdout, stderr=stderr)
        self.imports = {}

        self.instance = instance
        self.model = self.instance.__class__
        if context is None:
            context = {}
        self.context = context
        self.variable_name = "%s_%s" % (self.instance._meta.db_table, id)
        self.skip_me = None
        self.instantiated = False

        self.waiting_list = list(self.model._meta.fields)

        self.many_to_many_waiting_list = {}
        for field in self.model._meta.many_to_many:
            self.many_to_many_waiting_list[field] = list(getattr(self.instance, field.name).all())

    def get_lines(self, force=False):
        """ Returns a list of lists or strings, representing the code body.
            Each list is a block, each string is a statement.

            force (True or False): if an attribute object cannot be included,
            it is usually skipped to be processed later. With 'force' set, there
            will be no waiting: a get_or_create() call is written instead.
        """
        code_lines = []

        # Don't return anything if this is an instance that should be skipped
        if self.skip():
            return []

        # Initialise our new object
        # e.g. model_name_35 = Model()
        code_lines += self.instantiate()

        # Add each field
        # e.g. model_name_35.field_one = 1034.91
        #      model_name_35.field_two = "text"
        code_lines += self.get_waiting_list()

        if force:
            # TODO: Check that M2M are not affected
            code_lines += self.get_waiting_list(force=force)

        # Print the save command for our new object
        # e.g. model_name_35.save()
        if code_lines:
            code_lines.append("%s = importer.save_or_locate(%s)\n" % (self.variable_name, self.variable_name))

        code_lines += self.get_many_to_many_lines(force=force)

        return code_lines
    lines = property(get_lines)

    def skip(self):
        """ Determine whether or not this object should be skipped.
            If this model instance is a parent of a single subclassed
            instance, skip it. The subclassed instance will create this
            parent instance for us.

            TODO: Allow the user to force its creation?
        """

        if self.skip_me is not None:
            return self.skip_me

        def get_skip_version():
            """ Return which version of the skip code should be run

                Django's deletion code was refactored in r14507 which
                was just two days before 1.3 alpha 1 (r14519)
            """
            if not hasattr(self, '_SKIP_VERSION'):
                version = django.VERSION
                # no, it isn't lisp. I swear.
                self._SKIP_VERSION = (
                    version[0] > 1 or (  # django 2k... someday :)
                        version[0] == 1 and (  # 1.x
                            version[1] >= 4 or  # 1.4+
                            version[1] == 3 and not (  # 1.3.x
                                (version[3] == 'alpha' and version[1] == 0)
                            )
                        )
                    )
                ) and 2 or 1  # NOQA
            return self._SKIP_VERSION

        if get_skip_version() == 1:
            try:
                # Django trunk since r7722 uses CollectedObjects instead of dict
                from django.db.models.query import CollectedObjects
                sub_objects = CollectedObjects()
            except ImportError:
                # previous versions don't have CollectedObjects
                sub_objects = {}
            self.instance._collect_sub_objects(sub_objects)
            sub_objects = sub_objects.keys()

        elif get_skip_version() == 2:
            from django.db.models.deletion import Collector
            from django.db import router
            cls = self.instance.__class__
            using = router.db_for_write(cls, instance=self.instance)
            collector = Collector(using=using)
            collector.collect([self.instance], collect_related=False)

            # collector stores its instances in two places. I *think* we
            # only need collector.data, but using the batches is needed
            # to perfectly emulate the old behaviour
            # TODO: check if batches are really needed. If not, remove them.
            sub_objects = sum([list(i) for i in collector.data.values()], [])

            if hasattr(collector, 'batches'):
                # Django 1.6 removed batches for being dead code
                # https://github.com/django/django/commit/a170c3f755351beb35f8166ec3c7e9d524d9602
                for batch in collector.batches.values():
                    # batch.values can be sets, which must be converted to lists
                    sub_objects += sum([list(i) for i in batch.values()], [])

        sub_objects_parents = [so._meta.parents for so in sub_objects]
        if [self.model in p for p in sub_objects_parents].count(True) == 1:
            # since this instance isn't explicitly created, it's variable name
            # can't be referenced in the script, so record None in context dict
            pk_name = self.instance._meta.pk.name
            key = '%s_%s' % (self.model.__name__, getattr(self.instance, pk_name))
            self.context[key] = None
            self.skip_me = True
        else:
            self.skip_me = False

        return self.skip_me

    def instantiate(self):
        " Write lines for instantiation "
        # e.g. model_name_35 = Model()
        code_lines = []

        if not self.instantiated:
            code_lines.append("%s = %s()" % (self.variable_name, self.model.__name__))
            self.instantiated = True

            # Store our variable name for future foreign key references
            pk_name = self.instance._meta.pk.name
            key = '%s_%s' % (self.model.__name__, getattr(self.instance, pk_name))
            self.context[key] = self.variable_name

        return code_lines

    def get_waiting_list(self, force=False):
        " Add lines for any waiting fields that can be completed now. "

        code_lines = []

        # Process normal fields
        for field in list(self.waiting_list):
            try:
                # Find the value, add the line, remove from waiting list and move on
                value = get_attribute_value(self.instance, field, self.context, force=force)
                code_lines.append('%s.%s = %s' % (self.variable_name, field.name, value))
                self.waiting_list.remove(field)
            except SkipValue:
                # Remove from the waiting list and move on
                self.waiting_list.remove(field)
                continue
            except DoLater:
                # Move on, maybe next time
                continue

        return code_lines

    def get_many_to_many_lines(self, force=False):
        """ Generates lines that define many to many relations for this instance. """

        lines = []

        for field, rel_items in self.many_to_many_waiting_list.items():
            for rel_item in list(rel_items):
                try:
                    pk_name = rel_item._meta.pk.name
                    key = '%s_%s' % (rel_item.__class__.__name__, getattr(rel_item, pk_name))
                    value = "%s" % self.context[key]
                    lines.append('%s.%s.add(%s)' % (self.variable_name, field.name, value))
                    self.many_to_many_waiting_list[field].remove(rel_item)
                except KeyError:
                    if force:
                        item_locator = orm_item_locator(rel_item)
                        self.context["__extra_imports"][rel_item._meta.object_name] = rel_item.__module__
                        lines.append('%s.%s.add( %s )' % (self.variable_name, field.name, item_locator))
                        self.many_to_many_waiting_list[field].remove(rel_item)

        if lines:
            lines.append("")

        return lines


class Script(Code):
    " Produces a complete python script that can recreate data for the given apps. "

    def __init__(self, models, context=None, stdout=None, stderr=None):
        super(Script, self).__init__(stdout=stdout, stderr=stderr)
        self.imports = {}

        self.models = models
        if context is None:
            context = {}
        self.context = context

        self.context["__avaliable_models"] = set(models)
        self.context["__extra_imports"] = {}

    def _queue_models(self, models, context):
        """ Works an an appropriate ordering for the models.
            This isn't essential, but makes the script look nicer because
            more instances can be defined on their first try.
        """

        # Max number of cycles allowed before we call it an infinite loop.
        MAX_CYCLES = 5

        model_queue = []
        number_remaining_models = len(models)
        allowed_cycles = MAX_CYCLES

        while number_remaining_models > 0:
            previous_number_remaining_models = number_remaining_models

            model = models.pop(0)

            # If the model is ready to be processed, add it to the list
            if check_dependencies(model, model_queue, context["__avaliable_models"]):
                model_class = ModelCode(model=model, context=context, stdout=self.stdout, stderr=self.stderr)
                model_queue.append(model_class)

            # Otherwise put the model back at the end of the list
            else:
                models.append(model)

            # Check for infinite loops.
            # This means there is a cyclic foreign key structure
            # That cannot be resolved by re-ordering
            number_remaining_models = len(models)
            if number_remaining_models == previous_number_remaining_models:
                allowed_cycles -= 1
                if allowed_cycles <= 0:
                    # Add the remaining models, but do not remove them from the model list
                    missing_models = [ModelCode(model=m, context=context, stdout=self.stdout, stderr=self.stderr) for m in models]
                    model_queue += missing_models
                    # Replace the models with the model class objects
                    # (sure, this is a little bit of hackery)
                    models[:] = missing_models
                    break
            else:
                allowed_cycles = MAX_CYCLES

        return model_queue

    def get_lines(self):
        """ Returns a list of lists or strings, representing the code body.
            Each list is a block, each string is a statement.
        """
        code = [self.FILE_HEADER.strip()]

        # Queue and process the required models
        for model_class in self._queue_models(self.models, context=self.context):
            msg = 'Processing model: %s\n' % model_class.model.__name__
            self.stderr.write(msg)
            code.append("    # " + msg)
            code.append(model_class.import_lines)
            code.append("")
            code.append(model_class.lines)

        # Process left over foreign keys from cyclic models
        for model in self.models:
            msg = 'Re-processing model: %s\n' % model.model.__name__
            self.stderr.write(msg)
            code.append("    # " + msg)
            for instance in model.instances:
                if instance.waiting_list or instance.many_to_many_waiting_list:
                    code.append(instance.get_lines(force=True))

        code.insert(1, "    # Initial Imports")
        code.insert(2, "")
        for key, value in self.context["__extra_imports"].items():
            code.insert(2, "    from %s import %s" % (value, key))

        return code

    lines = property(get_lines)

    # A user-friendly file header
    FILE_HEADER = """

#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file has been automatically generated.
# Instead of changing it, create a file called import_helper.py
# and put there a class called ImportHelper(object) in it.
#
# This class will be specially casted so that instead of extending object,
# it will actually extend the class BasicImportHelper()
#
# That means you just have to overload the methods you want to
# change, leaving the other ones inteact.
#
# Something that you might want to do is use transactions, for example.
#
# Also, don't forget to add the necessary Django imports.
#
# This file was generated with the following command:
# %s
#
# to restore it, run
# manage.py runscript module_name.this_script_name
#
# example: if manage.py is at ./manage.py
# and the script is at ./some_folder/some_script.py
# you must make sure ./some_folder/__init__.py exists
# and run  ./manage.py runscript some_folder.some_script

from django.db import transaction

class BasicImportHelper(object):

    def pre_import(self):
        pass

    # You probably want to uncomment on of these two lines
    # @transaction.atomic  # Django 1.6
    # @transaction.commit_on_success  # Django <1.6
    def run_import(self, import_data):
        import_data()

    def post_import(self):
        pass

    def locate_similar(self, current_object, search_data):
        # You will probably want to call this method from save_or_locate()
        # Example:
        #   new_obj = self.locate_similar(the_obj, {"national_id": the_obj.national_id } )

        the_obj = current_object.__class__.objects.get(**search_data)
        return the_obj

    def locate_object(self, original_class, original_pk_name, the_class, pk_name, pk_value, obj_content):
        # You may change this function to do specific lookup for specific objects
        #
        # original_class class of the django orm's object that needs to be located
        # original_pk_name the primary key of original_class
        # the_class      parent class of original_class which contains obj_content
        # pk_name        the primary key of original_class
        # pk_value       value of the primary_key
        # obj_content    content of the object which was not exported.
        #
        # You should use obj_content to locate the object on the target db
        #
        # An example where original_class and the_class are different is
        # when original_class is Farmer and the_class is Person. The table
        # may refer to a Farmer but you will actually need to locate Person
        # in order to instantiate that Farmer
        #
        # Example:
        #   if the_class == SurveyResultFormat or the_class == SurveyType or the_class == SurveyState:
        #       pk_name="name"
        #       pk_value=obj_content[pk_name]
        #   if the_class == StaffGroup:
        #       pk_value=8

        search_data = { pk_name: pk_value }
        the_obj = the_class.objects.get(**search_data)
        #print(the_obj)
        return the_obj


    def save_or_locate(self, the_obj):
        # Change this if you want to locate the object in the database
        try:
            the_obj.save()
        except:
            print("---------------")
            print("Error saving the following object:")
            print(the_obj.__class__)
            print(" ")
            print(the_obj.__dict__)
            print(" ")
            print(the_obj)
            print(" ")
            print("---------------")

            raise
        return the_obj


importer = None
try:
    import import_helper
    # We need this so ImportHelper can extend BasicImportHelper, although import_helper.py
    # has no knowlodge of this class
    importer = type("DynamicImportHelper", (import_helper.ImportHelper, BasicImportHelper ) , {} )()
except ImportError as e:
    if str(e) == "No module named import_helper":
        importer = BasicImportHelper()
    else:
        raise

import datetime
from decimal import Decimal
from django.contrib.contenttypes.models import ContentType

try:
    import dateutil.parser
except ImportError:
    print("Please install python-dateutil")
    sys.exit(os.EX_USAGE)

def run():
    importer.pre_import()
    importer.run_import(import_data)
    importer.post_import()

def import_data():

""" % " ".join(sys.argv)


# HELPER FUNCTIONS
#-------------------------------------------------------------------------------

def flatten_blocks(lines, num_indents=-1):
    """ Takes a list (block) or string (statement) and flattens it into a string
        with indentation.
    """

    # The standard indent is four spaces
    INDENTATION = " " * 4

    if not lines:
        return ""

    # If this is a string, add the indentation and finish here
    if isinstance(lines, six.string_types):
        return INDENTATION * num_indents + lines

    # If this is not a string, join the lines and recurse
    return "\n".join([flatten_blocks(line, num_indents + 1) for line in lines])


def get_attribute_value(item, field, context, force=False):
    """ Gets a string version of the given attribute's value, like repr() might. """

    # Find the value of the field, catching any database issues
    try:
        value = getattr(item, field.name)
    except ObjectDoesNotExist:
        raise SkipValue('Could not find object for %s.%s, ignoring.\n' % (item.__class__.__name__, field.name))

    # AutoField: We don't include the auto fields, they'll be automatically recreated
    if isinstance(field, AutoField):
        raise SkipValue()

    # Some databases (eg MySQL) might store boolean values as 0/1, this needs to be cast as a bool
    elif isinstance(field, BooleanField) and value is not None:
        return repr(bool(value))

    # Post file-storage-refactor, repr() on File/ImageFields no longer returns the path
    elif isinstance(field, FileField):
        return repr(force_unicode(value))

    # ForeignKey fields, link directly using our stored python variable name
    elif isinstance(field, ForeignKey) and value is not None:

        # Special case for contenttype foreign keys: no need to output any
        # content types in this script, as they can be generated again
        # automatically.
        # NB: Not sure if "is" will always work
        if field.rel.to is ContentType:
            return 'ContentType.objects.get(app_label="%s", model="%s")' % (value.app_label, value.model)

        # Generate an identifier (key) for this foreign object
        pk_name = value._meta.pk.name
        key = '%s_%s' % (value.__class__.__name__, getattr(value, pk_name))

        if key in context:
            variable_name = context[key]
            # If the context value is set to None, this should be skipped.
            # This identifies models that have been skipped (inheritance)
            if variable_name is None:
                raise SkipValue()
            # Return the variable name listed in the context
            return "%s" % variable_name
        elif value.__class__ not in context["__avaliable_models"] or force:
            context["__extra_imports"][value._meta.object_name] = value.__module__
            item_locator = orm_item_locator(value)
            return item_locator
        else:
            raise DoLater('(FK) %s.%s\n' % (item.__class__.__name__, field.name))

    elif isinstance(field, (DateField, DateTimeField)):
        return "dateutil.parser.parse(\"%s\")" % value.isoformat()

    # A normal field (e.g. a python built-in)
    else:
        return repr(value)


def make_clean_dict(the_dict):
    if "_state" in the_dict:
        clean_dict = the_dict.copy()
        del clean_dict["_state"]
        return clean_dict
    return the_dict


def check_dependencies(model, model_queue, avaliable_models):
    " Check that all the depenedencies for this model are already in the queue. "

    # A list of allowed links: existing fields, itself and the special case ContentType
    allowed_links = [m.model.__name__ for m in model_queue] + [model.__name__, 'ContentType']

    # For each ForeignKey or ManyToMany field, check that a link is possible

    for field in model._meta.fields:
        if field.rel and field.rel.to.__name__ not in allowed_links:
            if field.rel.to not in avaliable_models:
                continue
            return False

    for field in model._meta.many_to_many:
        if field.rel and field.rel.to.__name__ not in allowed_links:
            return False

    return True


# EXCEPTIONS
#-------------------------------------------------------------------------------

class SkipValue(Exception):
    """ Value could not be parsed or should simply be skipped. """


class DoLater(Exception):
    """ Value could not be parsed or should simply be skipped. """

########NEW FILE########
__FILENAME__ = export_emails
from django.core.management.base import BaseCommand, CommandError
try:
    from django.contrib.auth import get_user_model  # Django 1.5
except ImportError:
    from django_extensions.future_1_5 import get_user_model
from django.contrib.auth.models import Group
from optparse import make_option
from sys import stdout
from csv import writer
import six

FORMATS = [
    'address',
    'emails',
    'google',
    'outlook',
    'linkedin',
    'vcard',
]


def full_name(first_name, last_name, username, **extra):
    name = six.u(" ").join(n for n in [first_name, last_name] if n)
    if not name:
        return username
    return name


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--group', '-g', action='store', dest='group', default=None,
                    help='Limit to users which are part of the supplied group name'),
        make_option('--format', '-f', action='store', dest='format', default=FORMATS[0],
                    help="output format. May be one of '" + "', '".join(FORMATS) + "'."),
    )

    help = ("Export user email address list in one of a number of formats.")
    args = "[output file]"
    label = 'filename to save to'

    requires_model_validation = True
    can_import_settings = True
    encoding = 'utf-8'  # RED_FLAG: add as an option -DougN

    def handle(self, *args, **options):
        if len(args) > 1:
            raise CommandError("extra arguments supplied")
        group = options['group']
        if group and not Group.objects.filter(name=group).count() == 1:
            names = six.u("', '").join(g['name'] for g in Group.objects.values('name')).encode('utf-8')
            if names:
                names = "'" + names + "'."
            raise CommandError("Unknown group '" + group + "'. Valid group names are: " + names)
        if len(args) and args[0] != '-':
            outfile = open(args[0], 'w')
        else:
            outfile = stdout

        User = get_user_model()
        qs = User.objects.all().order_by('last_name', 'first_name', 'username', 'email')
        if group:
            qs = qs.filter(groups__name=group).distinct()
        qs = qs.values('last_name', 'first_name', 'username', 'email')
        getattr(self, options['format'])(qs, outfile)

    def address(self, qs, out):
        """simple single entry per line in the format of:
            "full name" <my@address.com>;
        """
        out.write(six.u("\n").join('"%s" <%s>;' % (full_name(**ent), ent['email'])
                                   for ent in qs).encode(self.encoding))
        out.write("\n")

    def emails(self, qs, out):
        """simpler single entry with email only in the format of:
            my@address.com,
        """
        out.write(six.u(",\n").join(ent['email'] for ent in qs).encode(self.encoding))
        out.write("\n")

    def google(self, qs, out):
        """CSV format suitable for importing into google GMail
        """
        csvf = writer(out)
        csvf.writerow(['Name', 'Email'])
        for ent in qs:
            csvf.writerow([full_name(**ent).encode(self.encoding),
                           ent['email'].encode(self.encoding)])

    def outlook(self, qs, out):
        """CSV format suitable for importing into outlook
        """
        csvf = writer(out)
        columns = ['Name', 'E-mail Address', 'Notes', 'E-mail 2 Address', 'E-mail 3 Address',
                   'Mobile Phone', 'Pager', 'Company', 'Job Title', 'Home Phone', 'Home Phone 2',
                   'Home Fax', 'Home Address', 'Business Phone', 'Business Phone 2',
                   'Business Fax', 'Business Address', 'Other Phone', 'Other Fax', 'Other Address']
        csvf.writerow(columns)
        empty = [''] * (len(columns) - 2)
        for ent in qs:
            csvf.writerow([full_name(**ent).encode(self.encoding),
                           ent['email'].encode(self.encoding)] + empty)

    def linkedin(self, qs, out):
        """CSV format suitable for importing into linkedin Groups.
        perfect for pre-approving members of a linkedin group.
        """
        csvf = writer(out)
        csvf.writerow(['First Name', 'Last Name', 'Email'])
        for ent in qs:
            csvf.writerow([ent['first_name'].encode(self.encoding),
                           ent['last_name'].encode(self.encoding),
                           ent['email'].encode(self.encoding)])

    def vcard(self, qs, out):
        try:
            import vobject
        except ImportError:
            print(self.style.ERROR("Please install python-vobject to use the vcard export format."))
            import sys
            sys.exit(1)
        for ent in qs:
            card = vobject.vCard()
            card.add('fn').value = full_name(**ent)
            if not ent['last_name'] and not ent['first_name']:
                # fallback to fullname, if both first and lastname are not declared
                card.add('n').value = vobject.vcard.Name(full_name(**ent))
            else:
                card.add('n').value = vobject.vcard.Name(ent['last_name'], ent['first_name'])
            emailpart = card.add('email')
            emailpart.value = ent['email']
            emailpart.type_param = 'INTERNET'
            out.write(card.serialize().encode(self.encoding))

########NEW FILE########
__FILENAME__ = find_template
from django.core.management.base import LabelCommand
from django.template import loader
from django.template import TemplateDoesNotExist
import sys


def get_template_path(path):
    try:
        template = loader.find_template(path)
        if template[1]:
            return template[1].name
        # work arround https://code.djangoproject.com/ticket/17199 issue
        for template_loader in loader.template_source_loaders:
            try:
                source, origin = template_loader.load_template_source(path)
                return origin
            except TemplateDoesNotExist:
                pass
        raise TemplateDoesNotExist(path)
    except TemplateDoesNotExist:
        return None


class Command(LabelCommand):
    help = "Finds the location of the given template by resolving its path"
    args = "[template_path]"
    label = 'template path'

    def handle_label(self, template_path, **options):
        path = get_template_path(template_path)
        if path is None:
            sys.stderr.write("No template found\n")
            sys.exit(1)
        else:
            print(path)

########NEW FILE########
__FILENAME__ = generate_secret_key
from random import choice
from django.core.management.base import NoArgsCommand


class Command(NoArgsCommand):
    help = "Generates a new SECRET_KEY that can be used in a project settings file."

    requires_model_validation = False

    def handle_noargs(self, **options):
        return ''.join([choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for i in range(50)])

########NEW FILE########
__FILENAME__ = graph_models
import six
import sys
from optparse import make_option, NO_DEFAULT
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django_extensions.management.modelviz import generate_dot


try:
    import pygraphviz
    HAS_PYGRAPHVIZ = True
except ImportError:
    HAS_PYGRAPHVIZ = False

try:
    import pydot
    HAS_PYDOT = True
except ImportError:
    HAS_PYDOT = False


class Command(BaseCommand):
    graph_models_options = (
        make_option('--pygraphviz', action='store_true', dest='pygraphviz',
                    help='Use PyGraphViz to generate the image.'),
        make_option('--pydot', action='store_true', dest='pydot',
                    help='Use PyDot to generate the image.'),
        make_option('--disable-fields', '-d', action='store_true', dest='disable_fields',
                    help='Do not show the class member fields'),
        make_option('--group-models', '-g', action='store_true', dest='group_models',
                    help='Group models together respective to their application'),
        make_option('--all-applications', '-a', action='store_true', dest='all_applications',
                    help='Automatically include all applications from INSTALLED_APPS'),
        make_option('--output', '-o', action='store', dest='outputfile',
                    help='Render output file. Type of output dependend on file extensions. Use png or jpg to render graph to image.'),
        make_option('--layout', '-l', action='store', dest='layout', default='dot',
                    help='Layout to be used by GraphViz for visualization. Layouts: circo dot fdp neato nop nop1 nop2 twopi'),
        make_option('--verbose-names', '-n', action='store_true', dest='verbose_names',
                    help='Use verbose_name of models and fields'),
        make_option('--language', '-L', action='store', dest='language',
                    help='Specify language used for verbose_name localization'),
        make_option('--exclude-columns', '-x', action='store', dest='exclude_columns',
                    help='Exclude specific column(s) from the graph. Can also load exclude list from file.'),
        make_option('--exclude-models', '-X', action='store', dest='exclude_models',
                    help='Exclude specific model(s) from the graph. Can also load exclude list from file.'),
        make_option('--include-models', '-I', action='store', dest='include_models',
                    help='Restrict the graph to specified models.'),
        make_option('--inheritance', '-e', action='store_true', dest='inheritance', default=True,
                    help='Include inheritance arrows (default)'),
        make_option('--no-inheritance', '-E', action='store_false', dest='inheritance',
                    help='Do not include inheritance arrows'),
        make_option('--hide-relations-from-fields', '-R', action='store_false', dest="relations_as_fields",
                    default=True, help="Do not show relations as fields in the graph."),
        make_option('--disable-sort-fields', '-S', action="store_false", dest="sort_fields",
                    default=True, help="Do not sort fields"),
    )
    option_list = BaseCommand.option_list + graph_models_options

    help = "Creates a GraphViz dot file for the specified app names.  You can pass multiple app names and they will all be combined into a single model.  Output is usually directed to a dot file."
    args = "[appname]"
    label = 'application name'

    requires_model_validation = True
    can_import_settings = True

    def handle(self, *args, **options):
        self.options_from_settings(options)

        if len(args) < 1 and not options['all_applications']:
            raise CommandError("need one or more arguments for appname")

        use_pygraphviz = options.get('pygraphviz', False)
        use_pydot = options.get('pydot', False)
        cli_options = ' '.join(sys.argv[2:])
        dotdata = generate_dot(args, cli_options=cli_options, **options)
        dotdata = dotdata.encode('utf-8')
        if options['outputfile']:
            if not use_pygraphviz and not use_pydot:
                if HAS_PYGRAPHVIZ:
                    use_pygraphviz = True
                elif HAS_PYDOT:
                    use_pydot = True
            if use_pygraphviz:
                self.render_output_pygraphviz(dotdata, **options)
            elif use_pydot:
                self.render_output_pydot(dotdata, **options)
            else:
                raise CommandError("Neither pygraphviz nor pydot could be found to generate the image")
        else:
            self.print_output(dotdata)

    def options_from_settings(self, options):
        defaults = getattr(settings, 'GRAPH_MODELS', None)
        if defaults:
            for option in self.graph_models_options:
                long_opt = option._long_opts[0]
                if long_opt:
                    long_opt = long_opt.lstrip("-").replace("-", "_")
                    if long_opt in defaults:
                        default_value = None
                        if not option.default == NO_DEFAULT:
                            default_value = option.default
                        if options[option.dest] == default_value:
                            options[option.dest] = defaults[long_opt]

    def print_output(self, dotdata):
        if six.PY3 and isinstance(dotdata, six.binary_type):
            dotdata = dotdata.decode()

        print(dotdata)

    def render_output_pygraphviz(self, dotdata, **kwargs):
        """Renders the image using pygraphviz"""
        if not HAS_PYGRAPHVIZ:
            raise CommandError("You need to install pygraphviz python module")

        version = pygraphviz.__version__.rstrip("-svn")
        try:
            if tuple(int(v) for v in version.split('.')) < (0, 36):
                # HACK around old/broken AGraph before version 0.36 (ubuntu ships with this old version)
                import tempfile
                tmpfile = tempfile.NamedTemporaryFile()
                tmpfile.write(dotdata)
                tmpfile.seek(0)
                dotdata = tmpfile.name
        except ValueError:
            pass

        graph = pygraphviz.AGraph(dotdata)
        graph.layout(prog=kwargs['layout'])
        graph.draw(kwargs['outputfile'])

    def render_output_pydot(self, dotdata, **kwargs):
        """Renders the image using pydot"""
        if not HAS_PYDOT:
            raise CommandError("You need to install pydot python module")

        graph = pydot.graph_from_dot_data(dotdata)
        if not graph:
            raise CommandError("pydot returned an error")
        output_file = kwargs['outputfile']
        formats = ['bmp', 'canon', 'cmap', 'cmapx', 'cmapx_np', 'dot', 'dia', 'emf',
                   'em', 'fplus', 'eps', 'fig', 'gd', 'gd2', 'gif', 'gv', 'imap',
                   'imap_np', 'ismap', 'jpe', 'jpeg', 'jpg', 'metafile', 'pdf',
                   'pic', 'plain', 'plain-ext', 'png', 'pov', 'ps', 'ps2', 'svg',
                   'svgz', 'tif', 'tiff', 'tk', 'vml', 'vmlz', 'vrml', 'wbmp', 'xdot']
        ext = output_file[output_file.rfind('.') + 1:]
        format = ext if ext in formats else 'raw'
        graph.write(output_file, format=format)

########NEW FILE########
__FILENAME__ = mail_debug
from django_extensions.management.utils import setup_logger
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from smtpd import SMTPServer
import sys
import asyncore
from logging import getLogger


logger = getLogger(__name__)


class ExtensionDebuggingServer(SMTPServer):
    """Duplication of smtpd.DebuggingServer, but using logging instead of print."""
    # Do something with the gathered message
    def process_message(self, peer, mailfrom, rcpttos, data):
        """Output will be sent to the module logger at INFO level."""
        inheaders = 1
        lines = data.split('\n')
        logger.info('---------- MESSAGE FOLLOWS ----------')
        for line in lines:
            # headers first
            if inheaders and not line:
                logger.info('X-Peer: %s' % peer[0])
                inheaders = 0
            logger.info(line)
        logger.info('------------ END MESSAGE ------------')


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--output', dest='output_file', default=None,
                    help='Specifies an output file to send a copy of all messages (not flushed immediately).'),
        make_option('--use-settings', dest='use_settings',
                    action='store_true', default=False,
                    help='Uses EMAIL_HOST and HOST_PORT from Django settings.'),
    )
    help = "Starts a test mail server for development."
    args = '[optional port number or ippaddr:port]'

    requires_model_validation = False

    def handle(self, addrport='', *args, **options):
        if args:
            raise CommandError('Usage is mail_debug %s' % self.args)
        if not addrport:
            if options.get('use_settings', False):
                from django.conf import settings
                addr = getattr(settings, 'EMAIL_HOST', '')
                port = str(getattr(settings, 'EMAIL_PORT', '1025'))
            else:
                addr = ''
                port = '1025'
        else:
            try:
                addr, port = addrport.split(':')
            except ValueError:
                addr, port = '', addrport
        if not addr:
            addr = '127.0.0.1'

        if not port.isdigit():
            raise CommandError("%r is not a valid port number." % port)
        else:
            port = int(port)

        # Add console handler
        setup_logger(logger, stream=self.stdout, filename=options.get('output_file', None))

        def inner_run():
            quit_command = (sys.platform == 'win32') and 'CTRL-BREAK' or 'CONTROL-C'
            print("Now accepting mail at %s:%s -- use %s to quit" % (addr, port, quit_command))

            ExtensionDebuggingServer((addr, port), None)
            asyncore.loop()

        try:
            inner_run()
        except KeyboardInterrupt:
            pass

########NEW FILE########
__FILENAME__ = notes
from __future__ import with_statement
from django.core.management.base import BaseCommand
from django.conf import settings
import os
import re

ANNOTATION_RE = re.compile("\{?#[\s]*?(TODO|FIXME|BUG|HACK|WARNING|NOTE|XXX)[\s:]?(.+)")
ANNOTATION_END_RE = re.compile("(.*)#\}(.*)")


class Command(BaseCommand):
    help = 'Show all annotations like TODO, FIXME, BUG, HACK, WARNING, NOTE or XXX in your py and HTML files.'
    args = 'tag'
    label = 'annotation tag (TODO, FIXME, BUG, HACK, WARNING, NOTE, XXX)'

    def handle(self, *args, **options):
        # don't add django internal code
        apps = filter(lambda app: not app.startswith('django.contrib'), settings.INSTALLED_APPS)
        template_dirs = getattr(settings, 'TEMPLATE_DIRS', [])
        if template_dirs:
            apps += template_dirs
        for app_dir in apps:
            app_dir = app_dir.replace(".", "/")
            for top, dirs, files in os.walk(app_dir):
                for f in files:
                    if os.path.splitext(f)[1] in ('.py', '.html'):
                        fpath = os.path.join(top, f)
                        annotation_lines = []
                        with open(fpath, 'r') as f:
                            i = 0
                            for line in f.readlines():
                                i += 1
                                if ANNOTATION_RE.search(line):
                                    tag, msg = ANNOTATION_RE.findall(line)[0]
                                    if len(args) == 1:
                                        search_for_tag = args[0].upper()
                                        if not search_for_tag == tag:
                                            break

                                    if ANNOTATION_END_RE.search(msg.strip()):
                                        msg = ANNOTATION_END_RE.findall(msg.strip())[0][0]

                                    annotation_lines.append("[%3s] %-5s %s" % (i, tag, msg.strip()))
                            if annotation_lines:
                                print("%s:" % fpath)
                                for annotation in annotation_lines:
                                    print("  * %s" % annotation)
                                print("")

########NEW FILE########
__FILENAME__ = passwd
from django.core.management.base import BaseCommand, CommandError
try:
    from django.contrib.auth import get_user_model  # Django 1.5
except ImportError:
    from django_extensions.future_1_5 import get_user_model
import getpass


class Command(BaseCommand):
    help = "Clone of the UNIX program ``passwd'', for django.contrib.auth."

    requires_model_validation = False

    def handle(self, *args, **options):
        if len(args) > 1:
            raise CommandError("need exactly one or zero arguments for username")

        if args:
            username, = args
        else:
            username = getpass.getuser()

        User = get_user_model()
        try:
            u = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError("user %s does not exist" % username)

        print("Changing password for user: %s" % u.username)
        p1 = p2 = ""
        while "" in (p1, p2) or p1 != p2:
            p1 = getpass.getpass()
            p2 = getpass.getpass("Password (again): ")
            if p1 != p2:
                print("Passwords do not match, try again")
            elif "" in (p1, p2):
                raise CommandError("aborted")

        u.set_password(p1)
        u.save()

        return "Password changed successfully for user %s\n" % u.username

########NEW FILE########
__FILENAME__ = pipchecker
import os
import pip
import sys
import json
import urllib2
import urlparse
import xmlrpclib
from distutils.version import LooseVersion
from django.core.management.base import NoArgsCommand
from django_extensions.management.color import color_style
from optparse import make_option
from pip.req import parse_requirements

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option(
            "-t", "--github-api-token", action="store", dest="github_api_token",
            help="A github api authentication token."
        ),
        make_option(
            "-r", "--requirement", action="append", dest="requirements",
            default=[], metavar="FILENAME",
            help="Check all the packages listed in the given requirements file. "
                 "This option can be used multiple times."
        ),
        make_option(
            "-n", "--newer", action="store_true", dest="show_newer",
            help="Also show when newer version then available is installed."
        ),
    )
    help = "Scan pip requirement files for out-of-date packages."

    def handle_noargs(self, **options):
        self.style = color_style()

        self.options = options
        if options["requirements"]:
            req_files = options["requirements"]
        elif os.path.exists("requirements.txt"):
            req_files = ["requirements.txt"]
        elif os.path.exists("requirements"):
            req_files = ["requirements/{0}".format(f) for f in os.listdir("requirements")
                         if os.path.isfile(os.path.join("requirements", f)) and
                         f.lower().endswith(".txt")]
        else:
            sys.exit("requirements not found")

        self.reqs = {}
        for filename in req_files:
            class Object(object):
                pass
            mockoptions = Object()
            mockoptions.default_vcs = "git"
            mockoptions.skip_requirements_regex = None
            for req in parse_requirements(filename, options=mockoptions):
                self.reqs[req.name] = {
                    "pip_req": req,
                    "url": req.url,
                }

        if options["github_api_token"]:
            self.github_api_token = options["github_api_token"]
        elif os.environ.get("GITHUB_API_TOKEN"):
            self.github_api_token = os.environ.get("GITHUB_API_TOKEN")
        else:
            self.github_api_token = None  # only 50 requests per hour

        self.check_pypi()
        if HAS_REQUESTS:
            self.check_github()
        else:
            print(self.style.ERROR("Cannot check github urls. The requests library is not installed. ( pip install requests )"))
        self.check_other()

    def _urlopen_as_json(self, url, headers=None):
        """Shorcut for return contents as json"""
        req = urllib2.Request(url, headers=headers)
        return json.loads(urllib2.urlopen(req).read())

    def check_pypi(self):
        """
        If the requirement is frozen to pypi, check for a new version.
        """
        for dist in pip.get_installed_distributions():
            name = dist.project_name
            if name in self.reqs.keys():
                self.reqs[name]["dist"] = dist

        pypi = xmlrpclib.ServerProxy("http://pypi.python.org/pypi")
        for name, req in self.reqs.items():
            if req["url"]:
                continue  # skipping github packages.
            elif "dist" in req:
                dist = req["dist"]
                dist_version = LooseVersion(dist.version)
                available = pypi.package_releases(req["pip_req"].url_name)
                try:
                    available_version = LooseVersion(available[0])
                except IndexError:
                    available_version = None

                if not available_version:
                    msg = self.style.WARN("release is not on pypi (check capitalization and/or --extra-index-url)")
                elif self.options['show_newer'] and dist_version > available_version:
                    msg = self.style.INFO("{0} available (newer installed)".format(available_version))
                elif available_version > dist_version:
                    msg = self.style.INFO("{0} available".format(available_version))
                else:
                    msg = "up to date"
                    del self.reqs[name]
                    continue
                pkg_info = self.style.BOLD("{dist.project_name} {dist.version}".format(dist=dist))
            else:
                msg = "not installed"
                pkg_info = name
            print("{pkg_info:40} {msg}".format(pkg_info=pkg_info, msg=msg))
            del self.reqs[name]

    def check_github(self):
        """
        If the requirement is frozen to a github url, check for new commits.

        API Tokens
        ----------
        For more than 50 github api calls per hour, pipchecker requires
        authentication with the github api by settings the environemnt
        variable ``GITHUB_API_TOKEN`` or setting the command flag
        --github-api-token='mytoken'``.

        To create a github api token for use at the command line::
             curl -u 'rizumu' -d '{"scopes":["repo"], "note":"pipchecker"}' https://api.github.com/authorizations

        For more info on github api tokens:
            https://help.github.com/articles/creating-an-oauth-token-for-command-line-use
            http://developer.github.com/v3/oauth/#oauth-authorizations-api

        Requirement Format
        ------------------
        Pipchecker gets the sha of frozen repo and checks if it is
        found at the head of any branches. If it is not found then
        the requirement is considered to be out of date.

        Therefore, freezing at the commit hash will provide the expected
        results, but if freezing at a branch or tag name, pipchecker will
        not be able to determine with certainty if the repo is out of date.

        Freeze at the commit hash (sha)::
            git+git://github.com/django/django.git@393c268e725f5b229ecb554f3fac02cfc250d2df#egg=Django

        Freeze with a branch name::
            git+git://github.com/django/django.git@master#egg=Django

        Freeze with a tag::
            git+git://github.com/django/django.git@1.5b2#egg=Django

        Do not freeze::
            git+git://github.com/django/django.git#egg=Django

        """
        for name, req in self.reqs.items():
            req_url = req["url"]
            if not req_url:
                continue
            if req_url.startswith("git") and "github.com/" not in req_url:
                continue
            if req_url.endswith(".tar.gz") or req_url.endswith(".tar.bz2") or req_url.endswith(".zip"):
                continue

            headers = {
                "content-type": "application/json",
            }
            if self.github_api_token:
                headers["Authorization"] = "token {0}".format(self.github_api_token)
            try:
                user, repo = urlparse.urlparse(req_url).path.split("#")[0].strip("/").rstrip("/").split("/")
            except (ValueError, IndexError) as e:
                print(self.style.ERROR("\nFailed to parse %r: %s\n" % (req_url, e)))
                continue

            try:
                #test_auth = self._urlopen_as_json("https://api.github.com/django/", headers=headers)
                test_auth = requests.get("https://api.github.com/django/", headers=headers).json()
            except urllib2.HTTPError as e:
                print("\n%s\n" % str(e))
                return

            if "message" in test_auth and test_auth["message"] == "Bad credentials":
                print(self.style.ERROR("\nGithub API: Bad credentials. Aborting!\n"))
                return
            elif "message" in test_auth and test_auth["message"].startswith("API Rate Limit Exceeded"):
                print(self.style.ERROR("\nGithub API: Rate Limit Exceeded. Aborting!\n"))
                return

            frozen_commit_sha = None
            if ".git" in repo:
                repo_name, frozen_commit_full = repo.split(".git")
                if frozen_commit_full.startswith("@"):
                    frozen_commit_sha = frozen_commit_full[1:]
            elif "@" in repo:
                repo_name, frozen_commit_sha = repo.split("@")

            if frozen_commit_sha is None:
                msg = self.style.ERROR("repo is not frozen")

            if frozen_commit_sha:
                branch_url = "https://api.github.com/repos/{0}/{1}/branches".format(user, repo_name)
                #branch_data = self._urlopen_as_json(branch_url, headers=headers)
                branch_data = requests.get(branch_url, headers=headers).json()

                frozen_commit_url = "https://api.github.com/repos/{0}/{1}/commits/{2}".format(
                    user, repo_name, frozen_commit_sha
                )
                #frozen_commit_data = self._urlopen_as_json(frozen_commit_url, headers=headers)
                frozen_commit_data = requests.get(frozen_commit_url, headers=headers).json()

                if "message" in frozen_commit_data and frozen_commit_data["message"] == "Not Found":
                    msg = self.style.ERROR("{0} not found in {1}. Repo may be private.".format(frozen_commit_sha[:10], name))
                elif frozen_commit_sha in [branch["commit"]["sha"] for branch in branch_data]:
                    msg = self.style.BOLD("up to date")
                else:
                    msg = self.style.INFO("{0} is not the head of any branch".format(frozen_commit_data["sha"][:10]))

            if "dist" in req:
                pkg_info = "{dist.project_name} {dist.version}".format(dist=req["dist"])
            elif frozen_commit_sha is None:
                pkg_info = name
            else:
                pkg_info = "{0} {1}".format(name, frozen_commit_sha[:10])
            print("{pkg_info:40} {msg}".format(pkg_info=pkg_info, msg=msg))
            del self.reqs[name]

    def check_other(self):
        """
        If the requirement is frozen somewhere other than pypi or github, skip.

        If you have a private pypi or use --extra-index-url, consider contributing
        support here.
        """
        if self.reqs:
            print(self.style.ERROR("\nOnly pypi and github based requirements are supported:"))
            for name, req in self.reqs.items():
                if "dist" in req:
                    pkg_info = "{dist.project_name} {dist.version}".format(dist=req["dist"])
                elif "url" in req:
                    pkg_info = "{url}".format(url=req["url"])
                else:
                    pkg_info = "unknown package"
                print(self.style.BOLD("{pkg_info:40} is not a pypi or github requirement".format(pkg_info=pkg_info)))

########NEW FILE########
__FILENAME__ = print_settings
"""
print_settings
==============

Django command similar to 'diffsettings' but shows all active Django settings.
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from optparse import make_option


class Command(BaseCommand):
    """print_settings command"""

    help = "Print the active Django settings."

    option_list = BaseCommand.option_list + (
        make_option('--format', default='simple', dest='format',
                    help='Specifies output format.'),
        make_option('--indent', default=4, dest='indent', type='int',
                    help='Specifies indent level for JSON and YAML'),
    )

    def handle(self, *args, **options):
        a_dict = {}

        for attr in dir(settings):
            if self.include_attr(attr, args):
                value = getattr(settings, attr)
                a_dict[attr] = value

        for setting in args:
            if setting not in a_dict:
                raise CommandError('%s not found in settings.' % setting)

        output_format = options.get('format', 'json')
        indent = options.get('indent', 4)

        if output_format == 'json':
            json = self.import_json()
            print(json.dumps(a_dict, indent=indent))
        elif output_format == 'yaml':
            import yaml  # requires PyYAML
            print(yaml.dump(a_dict, indent=indent))
        elif output_format == 'pprint':
            from pprint import pprint
            pprint(a_dict)
        else:
            self.print_simple(a_dict)

    @staticmethod
    def include_attr(attr, args):
        """Whether or not to include attribute in output"""

        if not attr.startswith('__'):
            if args is not ():
                if attr in args:
                    return True
            else:
                return True
        else:
            return False

    @staticmethod
    def print_simple(a_dict):
        """A very simple output format"""

        for key, value in a_dict.items():
            print('%-40s = %r' % (key, value))

    @staticmethod
    def import_json():
        """Import a module for JSON"""

        try:
            import json
        except ImportError:
            import simplejson as json  # NOQA
        return json

########NEW FILE########
__FILENAME__ = print_user_for_session
from importlib import import_module
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

try:
    from django.contrib.auth import get_user_model  # Django 1.5
except ImportError:
    from django_extensions.future_1_5 import get_user_model

try:
    from django.contrib.sessions.backends.base import VALID_KEY_CHARS  # Django 1.5
except ImportError:
    VALID_KEY_CHARS = "abcdef0123456789"


class Command(BaseCommand):
    help = ("print the user information for the provided session key. "
            "this is very helpful when trying to track down the person who "
            "experienced a site crash.")
    args = "session_key"
    label = 'session key for the user'

    requires_model_validation = True
    can_import_settings = True

    def handle(self, *args, **options):
        if len(args) > 1:
            raise CommandError("extra arguments supplied")

        if len(args) < 1:
            raise CommandError("session_key argument missing")

        key = args[0].lower()

        if not set(key).issubset(set(VALID_KEY_CHARS)):
            raise CommandError("malformed session key")

        engine = import_module(settings.SESSION_ENGINE)

        if not engine.SessionStore().exists(key):
            print("Session Key does not exist. Expired?")
            return

        session = engine.SessionStore(key)
        data = session.load()

        print('Session to Expire: %s' % session.get_expiry_date())
        print('Raw Data: %s' % data)

        uid = data.get('_auth_user_id', None)

        if uid is None:
            print('No user associated with session')
            return

        print("User id: %s" % uid)

        User = get_user_model()
        try:
            user = User.objects.get(pk=uid)
        except User.DoesNotExist:
            print("No user associated with that id.")
            return

        username_field = 'username'

        if hasattr(User, 'USERNAME_FIELD') and User.USERNAME_FIELD is not None:
            username_field = User.USERNAME_FIELD

        for key in [username_field, 'email', 'first_name', 'last_name']:
            print("%s: %s" % (key, getattr(user, key)))

########NEW FILE########
__FILENAME__ = reset_db
"""
originally from http://www.djangosnippets.org/snippets/828/ by dnordberg
"""
import logging
from optparse import make_option

from django.conf import settings
from django.core.management.base import CommandError, BaseCommand
from six.moves import input


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--noinput', action='store_false',
                    dest='interactive', default=True,
                    help='Tells Django to NOT prompt the user for input of any kind.'),
        make_option('--no-utf8', action='store_true',
                    dest='no_utf8_support', default=False,
                    help='Tells Django to not create a UTF-8 charset database'),
        make_option('-U', '--user', action='store',
                    dest='user', default=None,
                    help='Use another user for the database then defined in settings.py'),
        make_option('-O', '--owner', action='store',
                    dest='owner', default=None,
                    help='Use another owner for creating the database then the user defined in settings or via --user'),
        make_option('-P', '--password', action='store',
                    dest='password', default=None,
                    help='Use another password for the database then defined in settings.py'),
        make_option('-D', '--dbname', action='store',
                    dest='dbname', default=None,
                    help='Use another database name then defined in settings.py'),
        make_option('-R', '--router', action='store',
                    dest='router', default='default',
                    help='Use this router-database other then defined in settings.py'),
    )
    help = "Resets the database for this project."

    def handle(self, *args, **options):
        """
        Resets the database for this project.

        Note: Transaction wrappers are in reverse as a work around for
        autocommit, anybody know how to do this the right way?
        """

        if args:
            raise CommandError("reset_db takes no arguments")

        router = options.get('router')
        dbinfo = settings.DATABASES.get(router)
        if dbinfo is None:
            raise CommandError("Unknown database router %s" % router)

        engine = dbinfo.get('ENGINE').split('.')[-1]
        user = options.get('user') or dbinfo.get('USER')
        password = options.get('password') or dbinfo.get('PASSWORD')
        owner = options.get('owner') or user

        database_name = options.get('dbname') or dbinfo.get('NAME')
        if database_name == '':
            raise CommandError("You need to specify DATABASE_NAME in your Django settings file.")

        database_host = dbinfo.get('HOST')
        database_port = dbinfo.get('PORT')

        verbosity = int(options.get('verbosity', 1))
        if options.get('interactive'):
            confirm = input("""
You have requested a database reset.
This will IRREVERSIBLY DESTROY
ALL data in the database "%s".
Are you sure you want to do this?

Type 'yes' to continue, or 'no' to cancel: """ % (database_name,))
        else:
            confirm = 'yes'

        if confirm != 'yes':
            print("Reset cancelled.")
            return

        if engine in ('sqlite3', 'spatialite'):
            import os
            try:
                logging.info("Unlinking %s database" % engine)
                os.unlink(database_name)
            except OSError:
                pass

        elif engine in ('mysql',):
            import MySQLdb as Database
            kwargs = {
                'user': user,
                'passwd': password,
            }
            if database_host.startswith('/'):
                kwargs['unix_socket'] = database_host
            else:
                kwargs['host'] = database_host

            if database_port:
                kwargs['port'] = int(database_port)

            connection = Database.connect(**kwargs)
            drop_query = 'DROP DATABASE IF EXISTS `%s`' % database_name
            utf8_support = options.get('no_utf8_support', False) and '' or 'CHARACTER SET utf8'
            create_query = 'CREATE DATABASE `%s` %s' % (database_name, utf8_support)
            logging.info('Executing... "' + drop_query + '"')
            connection.query(drop_query)
            logging.info('Executing... "' + create_query + '"')
            connection.query(create_query)

        elif engine in ('postgresql', 'postgresql_psycopg2', 'postgis'):
            if engine == 'postgresql':
                import psycopg as Database  # NOQA
            elif engine in ('postgresql_psycopg2', 'postgis'):
                import psycopg2 as Database  # NOQA

            conn_string = "dbname=template1"
            if user:
                conn_string += " user=%s" % user
            if password:
                conn_string += " password='%s'" % password
            if database_host:
                conn_string += " host=%s" % database_host
            if database_port:
                conn_string += " port=%s" % database_port

            connection = Database.connect(conn_string)
            connection.set_isolation_level(0)  # autocommit false
            cursor = connection.cursor()
            drop_query = 'DROP DATABASE %s;' % database_name
            logging.info('Executing... "' + drop_query + '"')

            try:
                cursor.execute(drop_query)
            except Database.ProgrammingError as e:
                logging.info("Error: %s" % str(e))

            create_query = "CREATE DATABASE %s" % database_name
            if owner:
                create_query += " WITH OWNER = \"%s\" " % owner
            create_query += " ENCODING = 'UTF8'"

            if engine == 'postgis':
                create_query += ' TEMPLATE = template_postgis'

            if settings.DEFAULT_TABLESPACE:
                create_query += ' TABLESPACE = %s;' % settings.DEFAULT_TABLESPACE
            else:
                create_query += ';'

            logging.info('Executing... "' + create_query + '"')
            cursor.execute(create_query)

        else:
            raise CommandError("Unknown database engine %s" % engine)

        if verbosity >= 2 or options.get('interactive'):
            print("Reset successful.")

########NEW FILE########
__FILENAME__ = runjob
from django.core.management.base import LabelCommand
from optparse import make_option
from django_extensions.management.jobs import get_job, print_jobs


class Command(LabelCommand):
    option_list = LabelCommand.option_list + (
        make_option('--list', '-l', action="store_true", dest="list_jobs",
                    help="List all jobs with their description"),
    )
    help = "Run a single maintenance job."
    args = "[app_name] job_name"
    label = ""

    requires_model_validation = True

    def runjob(self, app_name, job_name, options):
        verbosity = int(options.get('verbosity', 1))
        if verbosity > 1:
            print("Executing job: %s (app: %s)" % (job_name, app_name))
        try:
            job = get_job(app_name, job_name)
        except KeyError:
            if app_name:
                print("Error: Job %s for applabel %s not found" % (job_name, app_name))
            else:
                print("Error: Job %s not found" % job_name)
            print("Use -l option to view all the available jobs")
            return
        try:
            job().execute()
        except Exception:
            import traceback
            print("ERROR OCCURED IN JOB: %s (APP: %s)" % (job_name, app_name))
            print("START TRACEBACK:")
            traceback.print_exc()
            print("END TRACEBACK\n")

    def handle(self, *args, **options):
        app_name = None
        job_name = None
        if len(args) == 1:
            job_name = args[0]
        elif len(args) == 2:
            app_name, job_name = args
        if options.get('list_jobs'):
            print_jobs(only_scheduled=False, show_when=True, show_appname=True)
        else:
            if not job_name:
                print("Run a single maintenance job. Please specify the name of the job.")
                return
            self.runjob(app_name, job_name, options)

########NEW FILE########
__FILENAME__ = runjobs
from django.core.management.base import LabelCommand
from optparse import make_option
from django_extensions.management.jobs import get_jobs, print_jobs


class Command(LabelCommand):
    option_list = LabelCommand.option_list + (
        make_option('--list', '-l', action="store_true", dest="list_jobs",
                    help="List all jobs with their description"),
    )
    help = "Runs scheduled maintenance jobs."
    args = "[minutely quarter_hourly hourly daily weekly monthly yearly]"
    label = ""

    requires_model_validation = True

    def usage_msg(self):
        print("Run scheduled jobs. Please specify 'minutely', 'quarter_hourly', 'hourly', 'daily', 'weekly', 'monthly' or 'yearly'")

    def runjobs(self, when, options):
        verbosity = int(options.get('verbosity', 1))
        jobs = get_jobs(when, only_scheduled=True)
        list = jobs.keys()
        list.sort()
        for app_name, job_name in list:
            job = jobs[(app_name, job_name)]
            if verbosity > 1:
                print("Executing %s job: %s (app: %s)" % (when, job_name, app_name))
            try:
                job().execute()
            except Exception:
                import traceback
                print("ERROR OCCURED IN %s JOB: %s (APP: %s)" % (when.upper(), job_name, app_name))
                print("START TRACEBACK:")
                traceback.print_exc()
                print("END TRACEBACK\n")

    def runjobs_by_signals(self, when, options):
        """ Run jobs from the signals """
        # Thanks for Ian Holsman for the idea and code
        from django_extensions.management import signals
        from django.db import models
        from django.conf import settings

        verbosity = int(options.get('verbosity', 1))
        for app_name in settings.INSTALLED_APPS:
            try:
                __import__(app_name + '.management', '', '', [''])
            except ImportError:
                pass

        for app in models.get_apps():
            if verbosity > 1:
                app_name = '.'.join(app.__name__.rsplit('.')[:-1])
                print("Sending %s job signal for: %s" % (when, app_name))
            if when == 'minutely':
                signals.run_minutely_jobs.send(sender=app, app=app)
            elif when == 'quarter_hourly':
                signals.run_quarter_hourly_jobs.send(sender=app, app=app)
            elif when == 'hourly':
                signals.run_hourly_jobs.send(sender=app, app=app)
            elif when == 'daily':
                signals.run_daily_jobs.send(sender=app, app=app)
            elif when == 'weekly':
                signals.run_weekly_jobs.send(sender=app, app=app)
            elif when == 'monthly':
                signals.run_monthly_jobs.send(sender=app, app=app)
            elif when == 'yearly':
                signals.run_yearly_jobs.send(sender=app, app=app)

    def handle(self, *args, **options):
        when = None
        if len(args) > 1:
            self.usage_msg()
            return
        elif len(args) == 1:
            if not args[0] in ['minutely', 'quarter_hourly', 'hourly', 'daily', 'weekly', 'monthly', 'yearly']:
                self.usage_msg()
                return
            else:
                when = args[0]
        if options.get('list_jobs'):
            print_jobs(when, only_scheduled=True, show_when=True, show_appname=True)
        else:
            if not when:
                self.usage_msg()
                return
            self.runjobs(when, options)
            self.runjobs_by_signals(when, options)

########NEW FILE########
__FILENAME__ = runprofileserver
"""
runprofileserver.py

    Starts a lightweight Web server with profiling enabled.

Credits for kcachegrind support taken from lsprofcalltree.py go to:
 David Allouche
 Jp Calderone & Itamar Shtull-Trauring
 Johan Dahlin
"""

from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from datetime import datetime
from django.conf import settings
import sys

try:
    from django.contrib.staticfiles.handlers import StaticFilesHandler
    USE_STATICFILES = 'django.contrib.staticfiles' in settings.INSTALLED_APPS
except ImportError as e:
    USE_STATICFILES = False

try:
    any
except NameError:
    # backwards compatibility for <2.5
    def any(iterable):
        for element in iterable:
            if element:
                return True
        return False


def label(code):
    if isinstance(code, str):
        return ('~', 0, code)    # built-in functions ('~' sorts at the end)
    else:
        return '%s %s:%d' % (code.co_name,
                             code.co_filename,
                             code.co_firstlineno)


class KCacheGrind(object):
    def __init__(self, profiler):
        self.data = profiler.getstats()
        self.out_file = None

    def output(self, out_file):
        self.out_file = out_file
        self.out_file.write('events: Ticks\n')
        self._print_summary()
        for entry in self.data:
            self._entry(entry)

    def _print_summary(self):
        max_cost = 0
        for entry in self.data:
            totaltime = int(entry.totaltime * 1000)
            max_cost = max(max_cost, totaltime)
        self.out_file.write('summary: %d\n' % (max_cost,))

    def _entry(self, entry):
        out_file = self.out_file

        code = entry.code
        #print >> out_file, 'ob=%s' % (code.co_filename,)
        if isinstance(code, str):
            out_file.write('fi=~\n')
        else:
            out_file.write('fi=%s\n' % (code.co_filename,))
        out_file.write('fn=%s\n' % (label(code),))

        inlinetime = int(entry.inlinetime * 1000)
        if isinstance(code, str):
            out_file.write('0  %s\n' % inlinetime)
        else:
            out_file.write('%d %d\n' % (code.co_firstlineno, inlinetime))

        # recursive calls are counted in entry.calls
        if entry.calls:
            calls = entry.calls
        else:
            calls = []

        if isinstance(code, str):
            lineno = 0
        else:
            lineno = code.co_firstlineno

        for subentry in calls:
            self._subentry(lineno, subentry)
        out_file.write("\n")

    def _subentry(self, lineno, subentry):
        out_file = self.out_file
        code = subentry.code
        #out_file.write('cob=%s\n' % (code.co_filename,))
        out_file.write('cfn=%s\n' % (label(code),))
        if isinstance(code, str):
            out_file.write('cfi=~\n')
            out_file.write('calls=%d 0\n' % (subentry.callcount,))
        else:
            out_file.write('cfi=%s\n' % (code.co_filename,))
            out_file.write('calls=%d %d\n' % (subentry.callcount, code.co_firstlineno))

        totaltime = int(subentry.totaltime * 1000)
        out_file.write('%d %d\n' % (lineno, totaltime))


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--noreload', action='store_false', dest='use_reloader', default=True,
                    help='Tells Django to NOT use the auto-reloader.'),
        make_option('--adminmedia', dest='admin_media_path', default='',
                    help='Specifies the directory from which to serve admin media.'),
        make_option('--prof-path', dest='prof_path', default='/tmp',
                    help='Specifies the directory which to save profile information in.'),
        make_option('--prof-file', dest='prof_file', default='{path}.{duration:06d}ms.{time}',
                    help='Set filename format, default if "{path}.{duration:06d}ms.{time}".'),
        make_option('--nomedia', action='store_true', dest='no_media', default=False,
                    help='Do not profile MEDIA_URL and ADMIN_MEDIA_URL'),
        make_option('--use-cprofile', action='store_true', dest='use_cprofile', default=False,
                    help='Use cProfile if available, this is disabled per default because of incompatibilities.'),
        make_option('--kcachegrind', action='store_true', dest='use_lsprof', default=False,
                    help='Create kcachegrind compatible lsprof files, this requires and automatically enables cProfile.'),
    )
    if USE_STATICFILES:
        option_list += (
            make_option('--nostatic', action="store_false", dest='use_static_handler', default=True,
                        help='Tells Django to NOT automatically serve static files at STATIC_URL.'),
            make_option('--insecure', action="store_true", dest='insecure_serving', default=False,
                        help='Allows serving static files even if DEBUG is False.'),
        )
    help = "Starts a lightweight Web server with profiling enabled."
    args = '[optional port number, or ipaddr:port]'

    # Validation is called explicitly each time the server is reloaded.
    requires_model_validation = False

    def handle(self, addrport='', *args, **options):
        import django
        import socket
        import errno
        from django.core.servers.basehttp import run
        try:
            from django.core.servers.basehttp import get_internal_wsgi_application as WSGIHandler
        except ImportError:
            from django.core.handlers.wsgi import WSGIHandler  # noqa

        try:
            from django.core.servers.basehttp import AdminMediaHandler
            HAS_ADMINMEDIAHANDLER = True
        except ImportError:
            HAS_ADMINMEDIAHANDLER = False

        try:
            from django.core.servers.basehttp import WSGIServerException as wsgi_server_exc_cls
        except ImportError:  # Django 1.6
            wsgi_server_exc_cls = socket.error

        if args:
            raise CommandError('Usage is runserver %s' % self.args)
        if not addrport:
            addr = ''
            port = '8000'
        else:
            try:
                addr, port = addrport.split(':')
            except ValueError:
                addr, port = '', addrport
        if not addr:
            addr = '127.0.0.1'

        if not port.isdigit():
            raise CommandError("%r is not a valid port number." % port)

        use_reloader = options.get('use_reloader', True)
        shutdown_message = options.get('shutdown_message', '')
        no_media = options.get('no_media', False)
        quit_command = (sys.platform == 'win32') and 'CTRL-BREAK' or 'CONTROL-C'

        def inner_run():
            import os
            import time
            try:
                import hotshot
            except ImportError:
                pass            # python 3.x
            USE_CPROFILE = options.get('use_cprofile', False)
            USE_LSPROF = options.get('use_lsprof', False)
            if USE_LSPROF:
                USE_CPROFILE = True
            if USE_CPROFILE:
                try:
                    import cProfile
                    USE_CPROFILE = True
                except ImportError:
                    print("cProfile disabled, module cannot be imported!")
                    USE_CPROFILE = False
            if USE_LSPROF and not USE_CPROFILE:
                raise SystemExit("Kcachegrind compatible output format required cProfile from Python 2.5")
            prof_path = options.get('prof_path', '/tmp')

            prof_file = options.get('prof_file', '{path}.{duration:06d}ms.{time}')
            if not prof_file.format(path='1', duration=2, time=3):
                prof_file = '{path}.{duration:06d}ms.{time}'
                print("Filename format is wrong. Default format used: '{path}.{duration:06d}ms.{time}'.")

            def get_exclude_paths():
                exclude_paths = []
                media_url = getattr(settings, 'MEDIA_URL', None)
                if media_url:
                    exclude_paths.append(media_url)
                static_url = getattr(settings, 'STATIC_URL', None)
                if static_url:
                    exclude_paths.append(static_url)
                admin_media_prefix = getattr(settings, 'ADMIN_MEDIA_PREFIX', None)
                if admin_media_prefix:
                    exclude_paths.append(admin_media_prefix)
                return exclude_paths

            def make_profiler_handler(inner_handler):
                def handler(environ, start_response):
                    path_info = environ['PATH_INFO']
                    # when using something like a dynamic site middleware is could be necessary
                    # to refetch the exclude_paths every time since they could change per site.
                    if no_media and any(path_info.startswith(p) for p in get_exclude_paths()):
                        return inner_handler(environ, start_response)
                    path_name = path_info.strip("/").replace('/', '.') or "root"
                    profname = "%s.%d.prof" % (path_name, time.time())
                    profname = os.path.join(prof_path, profname)
                    if USE_CPROFILE:
                        prof = cProfile.Profile()
                    else:
                        prof = hotshot.Profile(profname)
                    start = datetime.now()
                    try:
                        return prof.runcall(inner_handler, environ, start_response)
                    finally:
                        # seeing how long the request took is important!
                        elap = datetime.now() - start
                        elapms = elap.seconds * 1000.0 + elap.microseconds / 1000.0
                        if USE_LSPROF:
                            kg = KCacheGrind(prof)
                            kg.output(open(profname, 'w'))
                        elif USE_CPROFILE:
                            prof.dump_stats(profname)
                        profname2 = prof_file.format(path=path_name, duration=int(elapms), time=int(time.time()))
                        profname2 = os.path.join(prof_path, "%s.prof" % profname2)
                        if not USE_CPROFILE:
                            prof.close()
                        os.rename(profname, profname2)
                return handler

            print("Validating models...")
            self.validate(display_num_errors=True)
            print("\nDjango version %s, using settings %r" % (django.get_version(), settings.SETTINGS_MODULE))
            print("Development server is running at http://%s:%s/" % (addr, port))
            print("Quit the server with %s." % quit_command)
            path = options.get('admin_media_path', '')
            if not path:
                admin_media_path = os.path.join(django.__path__[0], 'contrib/admin/static/admin')
                if os.path.isdir(admin_media_path):
                    path = admin_media_path
                else:
                    path = os.path.join(django.__path__[0], 'contrib/admin/media')
            try:
                handler = WSGIHandler()
                if HAS_ADMINMEDIAHANDLER:
                    handler = AdminMediaHandler(handler, path)
                if USE_STATICFILES:
                    use_static_handler = options.get('use_static_handler', True)
                    insecure_serving = options.get('insecure_serving', False)
                    if (use_static_handler and (settings.DEBUG or insecure_serving)):
                        handler = StaticFilesHandler(handler)
                handler = make_profiler_handler(handler)
                run(addr, int(port), handler)
            except wsgi_server_exc_cls as e:
                # Use helpful error messages instead of ugly tracebacks.
                ERRORS = {
                    errno.EACCES: "You don't have permission to access that port.",
                    errno.EADDRINUSE: "That port is already in use.",
                    errno.EADDRNOTAVAIL: "That IP address can't be assigned-to.",
                }
                if not isinstance(e, socket.error):  # Django < 1.6
                    ERRORS[13] = ERRORS.pop(errno.EACCES)
                    ERRORS[98] = ERRORS.pop(errno.EADDRINUSE)
                    ERRORS[99] = ERRORS.pop(errno.EADDRNOTAVAIL)
                try:
                    if not isinstance(e, socket.error):  # Django < 1.6
                        error_text = ERRORS[e.args[0].args[0]]
                    else:
                        error_text = ERRORS[e.errno]
                except (AttributeError, KeyError):
                    error_text = str(e)
                sys.stderr.write(self.style.ERROR("Error: %s" % error_text) + '\n')
                # Need to use an OS exit because sys.exit doesn't work in a thread
                os._exit(1)
            except KeyboardInterrupt:
                if shutdown_message:
                    print(shutdown_message)
                sys.exit(0)
        if use_reloader:
            from django.utils import autoreload
            autoreload.main(inner_run)
        else:
            inner_run()

########NEW FILE########
__FILENAME__ = runscript
from django.core.management.base import BaseCommand
from django.conf import settings
from optparse import make_option
import imp


def vararg_callback(option, opt_str, opt_value, parser):
    parser.rargs.insert(0, opt_value)
    value = []
    for arg in parser.rargs:
        # stop on --foo like options
        if arg[:2] == "--" and len(arg) > 2:
            break
        # stop on -a like options
        if arg[:1] == "-":
            break
        value.append(arg)

    del parser.rargs[:len(value)]
    setattr(parser.values, option.dest, value)


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--fixtures', action='store_true', dest='infixtures', default=False,
                    help='Only look in app.fixtures subdir'),
        make_option('--noscripts', action='store_true', dest='noscripts', default=False,
                    help='Look in app.scripts subdir'),
        make_option('-s', '--silent', action='store_true', dest='silent', default=False,
                    help='Run silently, do not show errors and tracebacks'),
        make_option('--no-traceback', action='store_true', dest='no_traceback', default=False,
                    help='Do not show tracebacks'),
        make_option('--script-args', action='callback', callback=vararg_callback, type='string',
                    help='Space-separated argument list to be passed to the scripts. Note that the '
                         'same arguments will be passed to all named scripts.'),
    )
    help = 'Runs a script in django context.'
    args = "script [script ...]"

    def handle(self, *scripts, **options):
        NOTICE = self.style.SQL_TABLE
        NOTICE2 = self.style.SQL_FIELD
        ERROR = self.style.ERROR
        ERROR2 = self.style.NOTICE

        subdirs = []

        if not options.get('noscripts'):
            subdirs.append('scripts')
        if options.get('infixtures'):
            subdirs.append('fixtures')
        verbosity = int(options.get('verbosity', 1))
        show_traceback = options.get('traceback', True)
        if show_traceback is None:
            # XXX: traceback is set to None from Django ?
            show_traceback = True
        no_traceback = options.get('no_traceback', False)
        if no_traceback:
            show_traceback = False
        silent = options.get('silent', False)
        if silent:
            verbosity = 0

        if len(subdirs) < 1:
            print(NOTICE("No subdirs to run left."))
            return

        if len(scripts) < 1:
            print(ERROR("Script name required."))
            return

        def run_script(mod, *script_args):
            try:
                mod.run(*script_args)
            except Exception:
                if silent:
                    return
                if verbosity > 0:
                    print(ERROR("Exception while running run() in '%s'" % mod.__name__))
                if show_traceback:
                    raise

        def my_import(mod):
            if verbosity > 1:
                print(NOTICE("Check for %s" % mod))
            # check if module exists before importing
            try:
                path = None
                for package in mod.split('.')[:-1]:
                    module_tuple = imp.find_module(package, path)
                    path = imp.load_module(package, *module_tuple).__path__
                imp.find_module(mod.split('.')[-1], path)
                t = __import__(mod, [], [], [" "])
            except (ImportError, AttributeError):
                return False

            #if verbosity > 1:
            #    print(NOTICE("Found script %s ..." % mod))
            if hasattr(t, "run"):
                if verbosity > 1:
                    print(NOTICE2("Found script '%s' ..." % mod))
                #if verbosity > 1:
                #    print(NOTICE("found run() in %s. executing..." % mod))
                return t
            else:
                if verbosity > 1:
                    print(ERROR2("Find script '%s' but no run() function found." % mod))

        def find_modules_for_script(script):
            """ find script module which contains 'run' attribute """
            modules = []
            # first look in apps
            for app in settings.INSTALLED_APPS:
                for subdir in subdirs:
                    mod = my_import("%s.%s.%s" % (app, subdir, script))
                    if mod:
                        modules.append(mod)

            # try app.DIR.script import
            sa = script.split(".")
            for subdir in subdirs:
                nn = ".".join(sa[:-1] + [subdir, sa[-1]])
                mod = my_import(nn)
                if mod:
                    modules.append(mod)

            # try direct import
            if script.find(".") != -1:
                mod = my_import(script)
                if mod:
                    modules.append(mod)

            return modules

        if options.get('script_args'):
            script_args = options['script_args']
        else:
            script_args = []
        for script in scripts:
            modules = find_modules_for_script(script)
            if not modules:
                if verbosity > 0 and not silent:
                    print(ERROR("No module for script '%s' found" % script))
            for mod in modules:
                if verbosity > 1:
                    print(NOTICE2("Running script '%s' ..." % mod.__name__))
                run_script(mod, *script_args)

########NEW FILE########
__FILENAME__ = runserver_plus
import os
import re
import socket
import sys
import time

from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django_extensions.management.utils import setup_logger, RedirectHandler
from django_extensions.management.technical_response import null_technical_500_response


try:
    if 'django.contrib.staticfiles' in settings.INSTALLED_APPS:
        from django.contrib.staticfiles.handlers import StaticFilesHandler
        USE_STATICFILES = True
    elif 'staticfiles' in settings.INSTALLED_APPS:
        from staticfiles.handlers import StaticFilesHandler  # noqa
        USE_STATICFILES = True
    else:
        USE_STATICFILES = False
except ImportError:
    USE_STATICFILES = False


naiveip_re = re.compile(r"""^(?:
(?P<addr>
    (?P<ipv4>\d{1,3}(?:\.\d{1,3}){3}) |         # IPv4 address
    (?P<ipv6>\[[a-fA-F0-9:]+\]) |               # IPv6 address
    (?P<fqdn>[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*) # FQDN
):)?(?P<port>\d+)$""", re.X)
DEFAULT_PORT = "8000"


import logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--ipv6', '-6', action='store_true', dest='use_ipv6', default=False,
                    help='Tells Django to use a IPv6 address.'),
        make_option('--noreload', action='store_false', dest='use_reloader', default=True,
                    help='Tells Django to NOT use the auto-reloader.'),
        make_option('--browser', action='store_true', dest='open_browser',
                    help='Tells Django to open a browser.'),
        make_option('--adminmedia', dest='admin_media_path', default='',
                    help='Specifies the directory from which to serve admin media.'),
        make_option('--threaded', action='store_true', dest='threaded',
                    help='Run in multithreaded mode.'),
        make_option('--output', dest='output_file', default=None,
                    help='Specifies an output file to send a copy of all messages (not flushed immediately).'),
        make_option('--print-sql', action='store_true', default=False,
                    help="Print SQL queries as they're executed"),
        make_option('--cert', dest='cert_path', action="store", type="string",
                    help='To use SSL, specify certificate path.'),

    )
    if USE_STATICFILES:
        option_list += (
            make_option('--nostatic', action="store_false", dest='use_static_handler', default=True,
                        help='Tells Django to NOT automatically serve static files at STATIC_URL.'),
            make_option('--insecure', action="store_true", dest='insecure_serving', default=False,
                        help='Allows serving static files even if DEBUG is False.'),
        )
    help = "Starts a lightweight Web server for development."
    args = '[optional port number, or ipaddr:port]'

    # Validation is called explicitly each time the server is reloaded.
    requires_model_validation = False

    def handle(self, addrport='', *args, **options):
        import django

        setup_logger(logger, self.stderr, filename=options.get('output_file', None))  # , fmt="[%(name)s] %(message)s")
        logredirect = RedirectHandler(__name__)

        # Redirect werkzeug log items
        werklogger = logging.getLogger('werkzeug')
        werklogger.setLevel(logging.INFO)
        werklogger.addHandler(logredirect)
        werklogger.propagate = False

        if options.get("print_sql", False):
            from django.db.backends import util
            try:
                import sqlparse
            except ImportError:
                sqlparse = None  # noqa

            class PrintQueryWrapper(util.CursorDebugWrapper):
                def execute(self, sql, params=()):
                    starttime = time.time()
                    try:
                        return self.cursor.execute(sql, params)
                    finally:
                        raw_sql = self.db.ops.last_executed_query(self.cursor, sql, params)
                        execution_time = time.time() - starttime
                        therest = ' -- [Execution time: %.6fs] [Database: %s]' % (execution_time, self.db.alias)
                        if sqlparse:
                            logger.info(sqlparse.format(raw_sql, reindent=True) + therest)
                        else:
                            logger.info(raw_sql + therest)

            util.CursorDebugWrapper = PrintQueryWrapper

        try:
            from django.core.servers.basehttp import AdminMediaHandler
            USE_ADMINMEDIAHANDLER = True
        except ImportError:
            USE_ADMINMEDIAHANDLER = False

        try:
            from django.core.servers.basehttp import get_internal_wsgi_application as WSGIHandler
        except ImportError:
            from django.core.handlers.wsgi import WSGIHandler  # noqa

        try:
            from werkzeug import run_simple, DebuggedApplication

            # Set colored output
            if settings.DEBUG:
                try:
                    set_werkzeug_log_color()
                except:     # We are dealing with some internals, anything could go wrong
                    print("Wrapping internal werkzeug logger for color highlighting has failed!")
                    pass

        except ImportError:
            raise CommandError("Werkzeug is required to use runserver_plus.  Please visit http://werkzeug.pocoo.org/ or install via pip. (pip install Werkzeug)")

        # usurp django's handler
        from django.views import debug
        debug.technical_500_response = null_technical_500_response

        self.use_ipv6 = options.get('use_ipv6')
        if self.use_ipv6 and not socket.has_ipv6:
            raise CommandError('Your Python does not support IPv6.')
        self._raw_ipv6 = False
        if not addrport:
            try:
                addrport = settings.RUNSERVERPLUS_SERVER_ADDRESS_PORT
            except AttributeError:
                pass
        if not addrport:
            self.addr = ''
            self.port = DEFAULT_PORT
        else:
            m = re.match(naiveip_re, addrport)
            if m is None:
                raise CommandError('"%s" is not a valid port number '
                                   'or address:port pair.' % addrport)
            self.addr, _ipv4, _ipv6, _fqdn, self.port = m.groups()
            if not self.port.isdigit():
                raise CommandError("%r is not a valid port number." %
                                   self.port)
            if self.addr:
                if _ipv6:
                    self.addr = self.addr[1:-1]
                    self.use_ipv6 = True
                    self._raw_ipv6 = True
                elif self.use_ipv6 and not _fqdn:
                    raise CommandError('"%s" is not a valid IPv6 address.'
                                       % self.addr)
        if not self.addr:
            self.addr = '::1' if self.use_ipv6 else '127.0.0.1'

        threaded = options.get('threaded', False)
        use_reloader = options.get('use_reloader', True)
        open_browser = options.get('open_browser', False)
        cert_path = options.get("cert_path")
        quit_command = (sys.platform == 'win32') and 'CTRL-BREAK' or 'CONTROL-C'
        bind_url = "http://%s:%s/" % (
            self.addr if not self._raw_ipv6 else '[%s]' % self.addr, self.port)

        def inner_run():
            print("Validating models...")
            self.validate(display_num_errors=True)
            print("\nDjango version %s, using settings %r" % (django.get_version(), settings.SETTINGS_MODULE))
            print("Development server is running at %s" % (bind_url,))
            print("Using the Werkzeug debugger (http://werkzeug.pocoo.org/)")
            print("Quit the server with %s." % quit_command)
            path = options.get('admin_media_path', '')
            if not path:
                admin_media_path = os.path.join(django.__path__[0], 'contrib/admin/static/admin')
                if os.path.isdir(admin_media_path):
                    path = admin_media_path
                else:
                    path = os.path.join(django.__path__[0], 'contrib/admin/media')
            handler = WSGIHandler()
            if USE_ADMINMEDIAHANDLER:
                handler = AdminMediaHandler(handler, path)
            if USE_STATICFILES:
                use_static_handler = options.get('use_static_handler', True)
                insecure_serving = options.get('insecure_serving', False)
                if use_static_handler and (settings.DEBUG or insecure_serving):
                    handler = StaticFilesHandler(handler)
            if open_browser:
                import webbrowser
                webbrowser.open(bind_url)
            if cert_path:
                """
                OpenSSL is needed for SSL support.

                This will make flakes8 throw warning since OpenSSL is not used
                directly, alas, this is the only way to show meaningful error
                messages. See:
                http://lucumr.pocoo.org/2011/9/21/python-import-blackbox/
                for more information on python imports.
                """
                try:
                    import OpenSSL  # NOQA
                except ImportError:
                    raise CommandError("Python OpenSSL Library is "
                                       "required to use runserver_plus with ssl support. "
                                       "Install via pip (pip install pyOpenSSL).")

                dir_path, cert_file = os.path.split(cert_path)
                if not dir_path:
                    dir_path = os.getcwd()
                root, ext = os.path.splitext(cert_file)
                certfile = os.path.join(dir_path, root + ".crt")
                keyfile = os.path.join(dir_path, root + ".key")
                try:
                    from werkzeug.serving import make_ssl_devcert
                    if os.path.exists(certfile) and \
                            os.path.exists(keyfile):
                                ssl_context = (certfile, keyfile)
                    else:  # Create cert, key files ourselves.
                        ssl_context = make_ssl_devcert(
                            os.path.join(dir_path, root), host='localhost')
                except ImportError:
                    print("Werkzeug version is less than 0.9, trying adhoc certificate.")
                    ssl_context = "adhoc"

            else:
                ssl_context = None
            run_simple(
                self.addr,
                int(self.port),
                DebuggedApplication(handler, True),
                use_reloader=use_reloader,
                use_debugger=True,
                threaded=threaded,
                ssl_context=ssl_context
            )
        inner_run()


def set_werkzeug_log_color():
    """Try to set color to the werkzeug log.
    """
    from django.core.management.color import color_style
    from werkzeug.serving import WSGIRequestHandler
    from werkzeug._internal import _log

    _style = color_style()
    _orig_log = WSGIRequestHandler.log

    def werk_log(self, type, message, *args):
        try:
            msg = '%s - - [%s] %s' % (
                self.address_string(),
                self.log_date_time_string(),
                message % args,
            )
            http_code = str(args[1])
        except:
            return _orig_log(type, message, *args)

        # Utilize terminal colors, if available
        if http_code[0] == '2':
            # Put 2XX first, since it should be the common case
            msg = _style.HTTP_SUCCESS(msg)
        elif http_code[0] == '1':
            msg = _style.HTTP_INFO(msg)
        elif http_code == '304':
            msg = _style.HTTP_NOT_MODIFIED(msg)
        elif http_code[0] == '3':
            msg = _style.HTTP_REDIRECT(msg)
        elif http_code == '404':
            msg = _style.HTTP_NOT_FOUND(msg)
        elif http_code[0] == '4':
            msg = _style.HTTP_BAD_REQUEST(msg)
        else:
            # Any 5XX, or any other response
            msg = _style.HTTP_SERVER_ERROR(msg)

        _log(type, msg)

    WSGIRequestHandler.log = werk_log

########NEW FILE########
__FILENAME__ = set_default_site
"""
set_default_site.py
"""
import socket
from optparse import make_option

from django.core.management.base import NoArgsCommand, CommandError


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--name', dest='site_name', default=None,
                    help='Use this as site name.'),
        make_option('--domain', dest='site_domain', default=None,
                    help='Use this as site domain.'),
        make_option('--system-fqdn', dest='set_as_system_fqdn', default=False,
                    action="store_true", help='Use the systems FQDN (Fully Qualified Domain Name) as name and domain. Can be used in combination with --name'),
    )
    help = "Set parameters of the default django.contrib.sites Site"
    requires_model_validation = True

    def handle_noargs(self, **options):
        from django.contrib.sites.models import Site

        try:
            site = Site.objects.get(pk=1)
        except Site.DoesNotExist:
            raise CommandError("Default site with pk=1 does not exist")
        else:
            name = options.get("site_name", None)
            domain = options.get("site_domain", None)
            if options.get('set_as_system_fqdn', False):
                domain = socket.getfqdn()
                if not domain:
                    raise CommandError("Cannot find systems FQDN")
                if name is None:
                    name = domain

            update_kwargs = {}
            if name and name != site.name:
                update_kwargs["name"] = name

            if domain and domain != site.domain:
                update_kwargs["domain"] = domain

            if update_kwargs:
                Site.objects.filter(pk=1).update(**update_kwargs)
                site = Site.objects.get(pk=1)
                print("Updated default site. You might need to restart django as sites are cached aggressively.")
            else:
                print("Nothing to update (need --name, --domain and/or --system-fqdn)")

            print("Default Site:")
            print("\tid = %s" % site.id)
            print("\tname = %s" % site.name)
            print("\tdomain = %s" % site.domain)

########NEW FILE########
__FILENAME__ = set_fake_emails
"""
set_fake_emails.py

    Give all users a new email account. Useful for testing in a
    development environment. As such, this command is only available when
    setting.DEBUG is True.

"""
from optparse import make_option

from django.conf import settings
from django.core.management.base import NoArgsCommand, CommandError

DEFAULT_FAKE_EMAIL = '%(username)s@example.com'


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--email', dest='default_email', default=DEFAULT_FAKE_EMAIL,
                    help='Use this as the new email format.'),
        make_option('-a', '--no-admin', action="store_true", dest='no_admin', default=False,
                    help='Do not change administrator accounts'),
        make_option('-s', '--no-staff', action="store_true", dest='no_staff', default=False,
                    help='Do not change staff accounts'),
        make_option('--include', dest='include_regexp', default=None,
                    help='Include usernames matching this regexp.'),
        make_option('--exclude', dest='exclude_regexp', default=None,
                    help='Exclude usernames matching this regexp.'),
        make_option('--include-groups', dest='include_groups', default=None,
                    help='Include users matching this group. (use comma seperation for multiple groups)'),
        make_option('--exclude-groups', dest='exclude_groups', default=None,
                    help='Exclude users matching this group. (use comma seperation for multiple groups)'),
    )
    help = '''DEBUG only: give all users a new email based on their account data ("%s" by default). Possible parameters are: username, first_name, last_name''' % (DEFAULT_FAKE_EMAIL, )
    requires_model_validation = False

    def handle_noargs(self, **options):
        if not settings.DEBUG:
            raise CommandError('Only available in debug mode')

        try:
            from django.contrib.auth import get_user_model  # Django 1.5
        except ImportError:
            from django_extensions.future_1_5 import get_user_model
        from django.contrib.auth.models import Group
        email = options.get('default_email', DEFAULT_FAKE_EMAIL)
        include_regexp = options.get('include_regexp', None)
        exclude_regexp = options.get('exclude_regexp', None)
        include_groups = options.get('include_groups', None)
        exclude_groups = options.get('exclude_groups', None)
        no_admin = options.get('no_admin', False)
        no_staff = options.get('no_staff', False)

        User = get_user_model()
        users = User.objects.all()
        if no_admin:
            users = users.exclude(is_superuser=True)
        if no_staff:
            users = users.exclude(is_staff=True)
        if exclude_groups:
            groups = Group.objects.filter(name__in=exclude_groups.split(","))
            if groups:
                users = users.exclude(groups__in=groups)
            else:
                raise CommandError("No group matches filter: %s" % exclude_groups)
        if include_groups:
            groups = Group.objects.filter(name__in=include_groups.split(","))
            if groups:
                users = users.filter(groups__in=groups)
            else:
                raise CommandError("No groups matches filter: %s" % include_groups)
        if exclude_regexp:
            users = users.exclude(username__regex=exclude_regexp)
        if include_regexp:
            users = users.filter(username__regex=include_regexp)
        for user in users:
            user.email = email % {'username': user.username,
                                  'first_name': user.first_name,
                                  'last_name': user.last_name}
            user.save()
        print('Changed %d emails' % users.count())

########NEW FILE########
__FILENAME__ = set_fake_passwords
"""
set_fake_passwords.py

    Reset all user passwords to a common value. Useful for testing in a
    development environment. As such, this command is only available when
    setting.DEBUG is True.

"""
from optparse import make_option

from django.conf import settings
from django.core.management.base import NoArgsCommand, CommandError

DEFAULT_FAKE_PASSWORD = 'password'


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--prompt', dest='prompt_passwd', default=False, action='store_true',
                    help='Prompts for the new password to apply to all users'),
        make_option('--password', dest='default_passwd', default=DEFAULT_FAKE_PASSWORD,
                    help='Use this as default password.'),
    )
    help = 'DEBUG only: sets all user passwords to a common value ("%s" by default)' % (DEFAULT_FAKE_PASSWORD, )
    requires_model_validation = False

    def handle_noargs(self, **options):
        if not settings.DEBUG:
            raise CommandError('Only available in debug mode')

        try:
            from django.contrib.auth import get_user_model  # Django 1.5
        except ImportError:
            from django_extensions.future_1_5 import get_user_model

        if options.get('prompt_passwd', False):
            from getpass import getpass
            passwd = getpass('Password: ')
            if not passwd:
                raise CommandError('You must enter a valid password')
        else:
            passwd = options.get('default_passwd', DEFAULT_FAKE_PASSWORD)

        User = get_user_model()
        user = User()
        user.set_password(passwd)
        count = User.objects.all().update(password=user.password)

        print('Reset %d passwords' % count)

########NEW FILE########
__FILENAME__ = shell_plus
import os
import six
import time
from optparse import make_option

from django.core.management.base import NoArgsCommand
from django.conf import settings

from django_extensions.management.shells import import_objects


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--plain', action='store_true', dest='plain',
                    help='Tells Django to use plain Python, not BPython nor IPython.'),
        make_option('--bpython', action='store_true', dest='bpython',
                    help='Tells Django to use BPython, not IPython.'),
        make_option('--ipython', action='store_true', dest='ipython',
                    help='Tells Django to use IPython, not BPython.'),
        make_option('--notebook', action='store_true', dest='notebook',
                    help='Tells Django to use IPython Notebook.'),
        make_option('--use-pythonrc', action='store_true', dest='use_pythonrc',
                    help='Tells Django to execute PYTHONSTARTUP file (BE CAREFULL WITH THIS!)'),
        make_option('--print-sql', action='store_true', default=False,
                    help="Print SQL queries as they're executed"),
        make_option('--dont-load', action='append', dest='dont_load', default=[],
                    help='Ignore autoloading of some apps/models. Can be used several times.'),
        make_option('--quiet-load', action='store_true', default=False, dest='quiet_load',
                    help='Do not display loaded models messages'),
    )
    help = "Like the 'shell' command but autoloads the models of all installed Django apps."

    requires_model_validation = True

    def handle_noargs(self, **options):
        use_notebook = options.get('notebook', False)
        use_ipython = options.get('ipython', False)
        use_bpython = options.get('bpython', False)
        use_plain = options.get('plain', False)
        use_pythonrc = options.get('use_pythonrc', True)

        if options.get("print_sql", False):
            # Code from http://gist.github.com/118990
            from django.db.backends import util
            sqlparse = None
            try:
                import sqlparse
            except ImportError:
                pass

            class PrintQueryWrapper(util.CursorDebugWrapper):
                def execute(self, sql, params=()):
                    starttime = time.time()
                    try:
                        return self.cursor.execute(sql, params)
                    finally:
                        execution_time = time.time() - starttime
                        raw_sql = self.db.ops.last_executed_query(self.cursor, sql, params)
                        if sqlparse:
                            print(sqlparse.format(raw_sql, reindent=True))
                        else:
                            print(raw_sql)
                        print("")
                        print('Execution time: %.6fs [Database: %s]' % (execution_time, self.db.alias))
                        print("")

            util.CursorDebugWrapper = PrintQueryWrapper

        def run_notebook():
            from django.conf import settings
            try:
                from IPython.html.notebookapp import NotebookApp
            except ImportError:
                from IPython.frontend.html.notebook import notebookapp
                NotebookApp = notebookapp.NotebookApp
            app = NotebookApp.instance()
            ipython_arguments = getattr(settings, 'IPYTHON_ARGUMENTS', ['--ext', 'django_extensions.management.notebook_extension'])
            app.initialize(ipython_arguments)
            app.start()

        def run_plain():
            # Using normal Python shell
            import code
            imported_objects = import_objects(options, self.style)
            try:
                # Try activating rlcompleter, because it's handy.
                import readline
            except ImportError:
                pass
            else:
                # We don't have to wrap the following import in a 'try', because
                # we already know 'readline' was imported successfully.
                import rlcompleter
                readline.set_completer(rlcompleter.Completer(imported_objects).complete)
                readline.parse_and_bind("tab:complete")

            # We want to honor both $PYTHONSTARTUP and .pythonrc.py, so follow system
            # conventions and get $PYTHONSTARTUP first then import user.
            if use_pythonrc:
                pythonrc = os.environ.get("PYTHONSTARTUP")
                if pythonrc and os.path.isfile(pythonrc):
                    global_ns = {}
                    with open(pythonrc) as rcfile:
                        try:
                            six.exec_(compile(rcfile.read(), pythonrc, 'exec'), global_ns)
                            imported_objects.update(global_ns)
                        except NameError:
                            pass
                # This will import .pythonrc.py as a side-effect
                try:
                    import user  # NOQA
                except ImportError:
                    pass
            code.interact(local=imported_objects)

        def run_bpython():
            from bpython import embed
            imported_objects = import_objects(options, self.style)
            embed(imported_objects)

        def run_ipython():
            try:
                from IPython import embed
                imported_objects = import_objects(options, self.style)
                embed(user_ns=imported_objects)
            except ImportError:
                # IPython < 0.11
                # Explicitly pass an empty list as arguments, because otherwise
                # IPython would use sys.argv from this script.
                # Notebook not supported for IPython < 0.11.
                from IPython.Shell import IPShell
                imported_objects = import_objects(options, self.style)
                shell = IPShell(argv=[], user_ns=imported_objects)
                shell.mainloop()

        shells = (
            ('bpython', run_bpython),
            ('ipython', run_ipython),
            ('plain', run_plain),
        )
        SETTINGS_SHELL_PLUS = getattr(settings, 'SHELL_PLUS', None)

        if use_notebook:
            run_notebook()
        elif use_plain:
            run_plain()
        elif use_ipython:
            run_ipython()
        elif use_bpython:
            run_bpython()
        elif SETTINGS_SHELL_PLUS:
            try:
                dict(shells)[SETTINGS_SHELL_PLUS]()
            except ImportError:
                import traceback
                traceback.print_exc()
                print(self.style.ERROR("Could not load '%s' Python environment." % SETTINGS_SHELL_PLUS))
        else:
            for shell_name, func in shells:
                try:
                    func()
                except ImportError:
                    continue
                else:
                    break
            else:
                import traceback
                traceback.print_exc()
                print(self.style.ERROR("Could not load any interactive Python environment."))


########NEW FILE########
__FILENAME__ = show_templatetags
import os
import six
import inspect
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management import color
from django.template import get_library
from django.utils import termcolors

try:
    from django.utils.encoding import smart_text
except ImportError:
    smart_text = six.u


def color_style():
    style = color.color_style()
    style.FILTER = termcolors.make_style(fg='yellow', opts=('bold',))
    style.MODULE_NAME = termcolors.make_style(fg='green', opts=('bold',))
    style.TAG = termcolors.make_style(fg='red', opts=('bold',))
    style.TAGLIB = termcolors.make_style(fg='blue', opts=('bold',))
    return style


def format_block(block, nlspaces=0):
    '''Format the given block of text, trimming leading/trailing
    empty lines and any leading whitespace that is common to all lines.
    The purpose is to let us list a code block as a multiline,
    triple-quoted Python string, taking care of
    indentation concerns.
    http://code.activestate.com/recipes/145672/'''

    import re

    # separate block into lines
    lines = smart_text(block).split('\n')

    # remove leading/trailing empty lines
    while lines and not lines[0]:
        del lines[0]
    while lines and not lines[-1]:
        del lines[-1]

    # look at first line to see how much indentation to trim
    ws = re.match(r'\s*', lines[0]).group(0)
    if ws:
        lines = map(lambda x: x.replace(ws, '', 1), lines)

    # remove leading/trailing blank lines (after leading ws removal)
    # we do this again in case there were pure-whitespace lines
    while lines and not lines[0]:
        del lines[0]
    while lines and not lines[-1]:
        del lines[-1]

    # account for user-specified leading spaces
    flines = ['%s%s' % (' ' * nlspaces, line) for line in lines]

    return '\n'.join(flines) + '\n'


class Command(BaseCommand):
    help = "Displays template tags and filters available in the current project."
    results = ""

    def add_result(self, s, depth=0):
        self.results += '%s\n' % s.rjust(depth * 4 + len(s))

    def handle(self, *args, **options):
        if args:
            appname, = args

        style = color_style()

        if settings.ADMIN_FOR:
            settings_modules = [__import__(m, {}, {}, ['']) for m in settings.ADMIN_FOR]
        else:
            settings_modules = [settings]

        for settings_mod in settings_modules:
            for app in settings_mod.INSTALLED_APPS:
                try:
                    templatetag_mod = __import__(app + '.templatetags', {}, {}, [''])
                except ImportError:
                    continue
                mod_path = inspect.getabsfile(templatetag_mod)
                mod_files = os.listdir(os.path.dirname(mod_path))
                tag_files = [i.rstrip('.py') for i in mod_files if i.endswith('.py') and i[0] != '_']
                app_labeled = False
                for taglib in tag_files:
                    try:
                        lib = get_library(taglib)
                    except:
                        continue
                    if not app_labeled:
                        self.add_result('App: %s' % style.MODULE_NAME(app))
                        app_labeled = True
                    self.add_result('load: %s' % style.TAGLIB(taglib), 1)
                    for items, label, style_func in [(lib.tags, 'Tag:', style.TAG), (lib.filters, 'Filter:', style.FILTER)]:
                        for item in items:
                            self.add_result('%s %s' % (label, style_func(item)), 2)
                            doc = inspect.getdoc(items[item])
                            if doc:
                                self.add_result(format_block(doc, 12))
        return self.results
        # return "\n".join(results)

########NEW FILE########
__FILENAME__ = show_urls
import six
from django.conf import settings
from django.core.exceptions import ViewDoesNotExist
from django.core.urlresolvers import RegexURLPattern, RegexURLResolver
from django.core.management.base import BaseCommand
from django.utils.translation import activate
from optparse import make_option

try:
    # 2008-05-30 admindocs found in newforms-admin brand
    from django.contrib.admindocs.views import simplify_regex
    assert simplify_regex
except ImportError:
    # fall back to trunk, pre-NFA merge
    from django.contrib.admin.views.doc import simplify_regex
import re

from django_extensions.management.color import color_style


FMTR = {
    'dense': "%(url)s\t%(module)s.%(name)s\t%(url_name)s\t%(decorator)s",
    'verbose': "%(url)s\n\tController: %(module)s.%(name)s\n\tURL Name: %(url_name)s\n\tDecorators: %(decorator)s\n",
}


def extract_views_from_urlpatterns(urlpatterns, base=''):
    """
    Return a list of views from a list of urlpatterns.

    Each object in the returned list is a two-tuple: (view_func, regex)
    """
    views = []
    for p in urlpatterns:
        if isinstance(p, RegexURLPattern):
            try:
                views.append((p.callback, base + p.regex.pattern, p.name))
            except ViewDoesNotExist:
                continue
        elif isinstance(p, RegexURLResolver):
            try:
                patterns = p.url_patterns
            except ImportError:
                continue
            views.extend(extract_views_from_urlpatterns(patterns, base + p.regex.pattern))
        elif hasattr(p, '_get_callback'):
            try:
                views.append((p._get_callback(), base + p.regex.pattern, p.name))
            except ViewDoesNotExist:
                continue
        elif hasattr(p, 'url_patterns') or hasattr(p, '_get_url_patterns'):
            try:
                patterns = p.url_patterns
            except ImportError:
                continue
            views.extend(extract_views_from_urlpatterns(patterns, base + p.regex.pattern))
        else:
            raise TypeError("%s does not appear to be a urlpattern object" % p)
    return views


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("--unsorted", "-u", action="store_true", dest="unsorted",
                    help="Show urls unsorted but same order as found in url patterns"),
        make_option("--language", "-l", dest="language",
                    help="Set the language code (useful for i18n_patterns)"),
        make_option("--decorator", "-d", dest="decorator",
                    help="Show the presence of given decorator on views"),
        make_option("--format", "-f", dest="format_style",
                    help="Style of the output. Choices: %s" % FMTR.keys())
    )

    help = "Displays all of the url matching routes for the project."

    requires_model_validation = True

    def handle(self, *args, **options):
        if args:
            appname, = args

        style = color_style()

        if settings.ADMIN_FOR:
            settings_modules = [__import__(m, {}, {}, ['']) for m in settings.ADMIN_FOR]
        else:
            settings_modules = [settings]

        language = options.get('language', None)
        if language is not None:
            activate(language)

        decorator = options.get('decorator')
        if decorator is None:
            decorator = 'login_required'

        format_style = options.get('format_style', 'dense')
        if format_style not in FMTR:
            raise Exception("Format style '%s' does not exist. Options: %s" % (format_style, FMTR.keys()))
        fmtr = FMTR[format_style]

        views = []
        for settings_mod in settings_modules:
            try:
                urlconf = __import__(settings_mod.ROOT_URLCONF, {}, {}, [''])
            except Exception as e:
                if options.get('traceback', None):
                    import traceback
                    traceback.print_exc()
                print(style.ERROR("Error occurred while trying to load %s: %s" % (settings_mod.ROOT_URLCONF, str(e))))
                continue
            view_functions = extract_views_from_urlpatterns(urlconf.urlpatterns)
            for (func, regex, url_name) in view_functions:
                if hasattr(func, '__name__'):
                    func_name = func.__name__
                elif hasattr(func, '__class__'):
                    func_name = '%s()' % func.__class__.__name__
                else:
                    func_name = re.sub(r' at 0x[0-9a-f]+', '', repr(func))
                func_globals = func.__globals__ if six.PY3 else func.func_globals
                views.append(fmtr % {
                    'name': style.MODULE_NAME(func_name),
                    'module': style.MODULE(func.__module__),
                    'url_name': style.URL_NAME(url_name or ''),
                    'url': style.URL(simplify_regex(regex)),
                    'decorator': decorator if decorator in func_globals else '',
                })

        if not options.get('unsorted', False):
            views = sorted(views)

        return "\n".join([v for v in views]) + "\n"

########NEW FILE########
__FILENAME__ = sqlcreate
import sys
import socket

from optparse import make_option

from django.conf import settings
from django.core.management.base import CommandError, BaseCommand


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('-R', '--router', action='store',
                    dest='router', default='default',
                    help='Use this router-database other then defined in settings.py'),
        make_option('-D', '--drop', action='store_true',
                    dest='drop', default=False,
                    help='If given, includes commands to drop any existing user and database.'),
    )
    help = """Generates the SQL to create your database for you, as specified in settings.py
The envisioned use case is something like this:

    ./manage.py sqlcreate [--router=<routername>] | mysql -u <db_administrator> -p
    ./manage.py sqlcreate [--router=<routername>] | psql -U <db_administrator> -W"""

    requires_model_validation = False
    can_import_settings = True

    def handle(self, *args, **options):

        router = options.get('router')
        dbinfo = settings.DATABASES.get(router)
        if dbinfo is None:
            raise CommandError("Unknown database router %s" % router)

        engine = dbinfo.get('ENGINE').split('.')[-1]
        dbuser = dbinfo.get('USER')
        dbpass = dbinfo.get('PASSWORD')
        dbname = dbinfo.get('NAME')
        dbhost = dbinfo.get('HOST')
        dbclient = socket.gethostname()

        # django settings file tells you that localhost should be specified by leaving
        # the DATABASE_HOST blank
        if not dbhost:
            dbhost = 'localhost'

        if engine == 'mysql':
            sys.stderr.write("""-- WARNING!: https://docs.djangoproject.com/en/dev/ref/databases/#collation-settings
-- Please read this carefully! Collation will be set to utf8_bin to have case-sensitive data.
""")
            print("CREATE DATABASE %s CHARACTER SET utf8 COLLATE utf8_bin;" % dbname)
            print("GRANT ALL PRIVILEGES ON %s.* to '%s'@'%s' identified by '%s';" % (
                dbname, dbuser, dbclient, dbpass
            ))

        elif engine == 'postgresql_psycopg2':
            if options.get('drop'):
                print("DROP DATABASE IF EXISTS %s;" % (dbname,))
                print("DROP USER IF EXISTS %s;" % (dbuser,))

            print("CREATE USER %s WITH ENCRYPTED PASSWORD '%s' CREATEDB;" % (dbuser, dbpass))
            print("CREATE DATABASE %s WITH ENCODING 'UTF-8' OWNER \"%s\";" % (dbname, dbuser))
            print("GRANT ALL PRIVILEGES ON DATABASE %s TO %s;" % (dbname, dbuser))

        elif engine == 'sqlite3':
            sys.stderr.write("-- manage.py syncdb will automatically create a sqlite3 database file.\n")

        else:
            # CREATE DATABASE is not SQL standard, but seems to be supported by most.
            sys.stderr.write("-- Don't know how to handle '%s' falling back to SQL.\n" % engine)
            print("CREATE DATABASE %s;" % dbname)
            print("GRANT ALL PRIVILEGES ON DATABASE %s to %s" % (dbname, dbuser))

########NEW FILE########
__FILENAME__ = sqldiff
"""
sqldiff.py - Prints the (approximated) difference between models and database

TODO:
 - better support for relations
 - better support for constraints (mainly postgresql?)
 - support for table spaces with postgresql
 - when a table is not managed (meta.managed==False) then only do a one-way
   sqldiff ? show differences from db->table but not the other way around since
   it's not managed.

KNOWN ISSUES:
 - MySQL has by far the most problems with introspection. Please be
   carefull when using MySQL with sqldiff.
   - Booleans are reported back as Integers, so there's know way to know if
     there was a real change.
   - Varchar sizes are reported back without unicode support so their size
     may change in comparison to the real length of the varchar.
   - Some of the 'fixes' to counter these problems might create false
     positives or false negatives.
"""

import six
from django.core.management.base import BaseCommand
from django.core.management import sql as _sql
from django.core.management import CommandError
from django.core.management.color import no_style
from django.db import transaction, connection
from django.db.models.fields import IntegerField
from optparse import make_option

ORDERING_FIELD = IntegerField('_order', null=True)


def flatten(l, ltypes=(list, tuple)):
    ltype = type(l)
    l = list(l)
    i = 0
    while i < len(l):
        while isinstance(l[i], ltypes):
            if not l[i]:
                l.pop(i)
                i -= 1
                break
            else:
                l[i:i + 1] = l[i]
        i += 1
    return ltype(l)


def all_local_fields(meta):
    all_fields = []
    if meta.managed:
        if meta.proxy:
            for parent in meta.parents:
                all_fields.extend(all_local_fields(parent._meta))
        else:
            for f in meta.local_fields:
                col_type = f.db_type(connection=connection)
                if col_type is None:
                    continue
                all_fields.append(f)
    return all_fields


class SQLDiff(object):
    DATA_TYPES_REVERSE_OVERRIDE = {}

    DIFF_TYPES = [
        'error',
        'comment',
        'table-missing-in-db',
        'field-missing-in-db',
        'field-missing-in-model',
        'fkey-missing-in-db',
        'fkey-missing-in-model',
        'index-missing-in-db',
        'index-missing-in-model',
        'unique-missing-in-db',
        'unique-missing-in-model',
        'field-type-differ',
        'field-parameter-differ',
        'notnull-differ',
    ]
    DIFF_TEXTS = {
        'error': 'error: %(0)s',
        'comment': 'comment: %(0)s',
        'table-missing-in-db': "table '%(0)s' missing in database",
        'field-missing-in-db': "field '%(1)s' defined in model but missing in database",
        'field-missing-in-model': "field '%(1)s' defined in database but missing in model",
        'fkey-missing-in-db': "field '%(1)s' FOREIGN KEY defined in model but missing in database",
        'fkey-missing-in-model': "field '%(1)s' FOREIGN KEY defined in database but missing in model",
        'index-missing-in-db': "field '%(1)s' INDEX defined in model but missing in database",
        'index-missing-in-model': "field '%(1)s' INDEX defined in database schema but missing in model",
        'unique-missing-in-db': "field '%(1)s' UNIQUE defined in model but missing in database",
        'unique-missing-in-model': "field '%(1)s' UNIQUE defined in database schema but missing in model",
        'field-type-differ': "field '%(1)s' not of same type: db='%(3)s', model='%(2)s'",
        'field-parameter-differ': "field '%(1)s' parameters differ: db='%(3)s', model='%(2)s'",
        'notnull-differ': "field '%(1)s' null differ: db='%(3)s', model='%(2)s'",
    }

    SQL_FIELD_MISSING_IN_DB = lambda self, style, qn, args: "%s %s\n\t%s %s %s;" % (style.SQL_KEYWORD('ALTER TABLE'), style.SQL_TABLE(qn(args[0])), style.SQL_KEYWORD('ADD COLUMN'), style.SQL_FIELD(qn(args[1])), ' '.join(style.SQL_COLTYPE(a) if i == 0 else style.SQL_KEYWORD(a) for i, a in enumerate(args[2:])))
    SQL_FIELD_MISSING_IN_MODEL = lambda self, style, qn, args: "%s %s\n\t%s %s;" % (style.SQL_KEYWORD('ALTER TABLE'), style.SQL_TABLE(qn(args[0])), style.SQL_KEYWORD('DROP COLUMN'), style.SQL_FIELD(qn(args[1])))
    SQL_FKEY_MISSING_IN_DB = lambda self, style, qn, args: "%s %s\n\t%s %s %s %s %s (%s)%s;" % (style.SQL_KEYWORD('ALTER TABLE'), style.SQL_TABLE(qn(args[0])), style.SQL_KEYWORD('ADD COLUMN'), style.SQL_FIELD(qn(args[1])), ' '.join(style.SQL_COLTYPE(a) if i == 0 else style.SQL_KEYWORD(a) for i, a in enumerate(args[4:])), style.SQL_KEYWORD('REFERENCES'), style.SQL_TABLE(qn(args[2])), style.SQL_FIELD(qn(args[3])), connection.ops.deferrable_sql())
    SQL_INDEX_MISSING_IN_DB = lambda self, style, qn, args: "%s %s\n\t%s %s (%s%s);" % (style.SQL_KEYWORD('CREATE INDEX'), style.SQL_TABLE(qn("%s" % '_'.join(a for a in args[0:3] if a))), style.SQL_KEYWORD('ON'), style.SQL_TABLE(qn(args[0])), style.SQL_FIELD(qn(args[1])), style.SQL_KEYWORD(args[3]))
    # FIXME: need to lookup index name instead of just appending _idx to table + fieldname
    SQL_INDEX_MISSING_IN_MODEL = lambda self, style, qn, args: "%s %s;" % (style.SQL_KEYWORD('DROP INDEX'), style.SQL_TABLE(qn("%s" % '_'.join(a for a in args[0:3] if a))))
    SQL_UNIQUE_MISSING_IN_DB = lambda self, style, qn, args: "%s %s\n\t%s %s (%s);" % (style.SQL_KEYWORD('ALTER TABLE'), style.SQL_TABLE(qn(args[0])), style.SQL_KEYWORD('ADD'), style.SQL_KEYWORD('UNIQUE'), style.SQL_FIELD(qn(args[1])))
    # FIXME: need to lookup unique constraint name instead of appending _key to table + fieldname
    SQL_UNIQUE_MISSING_IN_MODEL = lambda self, style, qn, args: "%s %s\n\t%s %s %s;" % (style.SQL_KEYWORD('ALTER TABLE'), style.SQL_TABLE(qn(args[0])), style.SQL_KEYWORD('DROP'), style.SQL_KEYWORD('CONSTRAINT'), style.SQL_TABLE(qn("%s_key" % ('_'.join(args[:2])))))
    SQL_FIELD_TYPE_DIFFER = lambda self, style, qn, args: "%s %s\n\t%s %s %s;" % (style.SQL_KEYWORD('ALTER TABLE'), style.SQL_TABLE(qn(args[0])), style.SQL_KEYWORD("MODIFY"), style.SQL_FIELD(qn(args[1])), style.SQL_COLTYPE(args[2]))
    SQL_FIELD_PARAMETER_DIFFER = lambda self, style, qn, args: "%s %s\n\t%s %s %s;" % (style.SQL_KEYWORD('ALTER TABLE'), style.SQL_TABLE(qn(args[0])), style.SQL_KEYWORD("MODIFY"), style.SQL_FIELD(qn(args[1])), style.SQL_COLTYPE(args[2]))
    SQL_NOTNULL_DIFFER = lambda self, style, qn, args: "%s %s\n\t%s %s %s %s;" % (style.SQL_KEYWORD('ALTER TABLE'), style.SQL_TABLE(qn(args[0])), style.SQL_KEYWORD('MODIFY'), style.SQL_FIELD(qn(args[1])), style.SQL_KEYWORD(args[2]), style.SQL_KEYWORD('NOT NULL'))
    SQL_ERROR = lambda self, style, qn, args: style.NOTICE('-- Error: %s' % style.ERROR(args[0]))
    SQL_COMMENT = lambda self, style, qn, args: style.NOTICE('-- Comment: %s' % style.SQL_TABLE(args[0]))
    SQL_TABLE_MISSING_IN_DB = lambda self, style, qn, args: style.NOTICE('-- Table missing: %s' % args[0])

    can_detect_notnull_differ = False

    def __init__(self, app_models, options):
        self.app_models = app_models
        self.options = options
        self.dense = options.get('dense_output', False)

        try:
            self.introspection = connection.introspection
        except AttributeError:
            from django.db import get_introspection_module
            self.introspection = get_introspection_module()

        self.cursor = connection.cursor()
        self.django_tables = self.get_django_tables(options.get('only_existing', True))
        self.db_tables = self.introspection.get_table_list(self.cursor)
        self.differences = []
        self.unknown_db_fields = {}
        self.new_db_fields = set()
        self.null = {}

        self.DIFF_SQL = {
            'error': self.SQL_ERROR,
            'comment': self.SQL_COMMENT,
            'table-missing-in-db': self.SQL_TABLE_MISSING_IN_DB,
            'field-missing-in-db': self.SQL_FIELD_MISSING_IN_DB,
            'field-missing-in-model': self.SQL_FIELD_MISSING_IN_MODEL,
            'fkey-missing-in-db': self.SQL_FKEY_MISSING_IN_DB,
            'fkey-missing-in-model': self.SQL_FIELD_MISSING_IN_MODEL,
            'index-missing-in-db': self.SQL_INDEX_MISSING_IN_DB,
            'index-missing-in-model': self.SQL_INDEX_MISSING_IN_MODEL,
            'unique-missing-in-db': self.SQL_UNIQUE_MISSING_IN_DB,
            'unique-missing-in-model': self.SQL_UNIQUE_MISSING_IN_MODEL,
            'field-type-differ': self.SQL_FIELD_TYPE_DIFFER,
            'field-parameter-differ': self.SQL_FIELD_PARAMETER_DIFFER,
            'notnull-differ': self.SQL_NOTNULL_DIFFER,
        }

        if self.can_detect_notnull_differ:
            self.load_null()

    def load_null(self):
        raise NotImplementedError("load_null functions must be implemented if diff backend has 'can_detect_notnull_differ' set to True")

    def add_app_model_marker(self, app_label, model_name):
        self.differences.append((app_label, model_name, []))

    def add_difference(self, diff_type, *args):
        assert diff_type in self.DIFF_TYPES, 'Unknown difference type'
        self.differences[-1][-1].append((diff_type, args))

    def get_django_tables(self, only_existing):
        try:
            django_tables = self.introspection.django_table_names(only_existing=only_existing)
        except AttributeError:
            # backwards compatibility for before introspection refactoring (r8296)
            try:
                django_tables = _sql.django_table_names(only_existing=only_existing)
            except AttributeError:
                # backwards compatibility for before svn r7568
                django_tables = _sql.django_table_list(only_existing=only_existing)
        return django_tables

    def sql_to_dict(self, query, param):
        """ sql_to_dict(query, param) -> list of dicts

        code from snippet at http://www.djangosnippets.org/snippets/1383/
        """
        cursor = connection.cursor()
        cursor.execute(query, param)
        fieldnames = [name[0] for name in cursor.description]
        result = []
        for row in cursor.fetchall():
            rowset = []
            for field in zip(fieldnames, row):
                rowset.append(field)
            result.append(dict(rowset))
        return result

    def get_field_model_type(self, field):
        return field.db_type(connection=connection)

    def get_field_db_type(self, description, field=None, table_name=None):
        from django.db import models
        # DB-API cursor.description
        #(name, type_code, display_size, internal_size, precision, scale, null_ok) = description
        type_code = description[1]
        if type_code in self.DATA_TYPES_REVERSE_OVERRIDE:
            reverse_type = self.DATA_TYPES_REVERSE_OVERRIDE[type_code]
        else:
            try:
                try:
                    reverse_type = self.introspection.data_types_reverse[type_code]
                except AttributeError:
                    # backwards compatibility for before introspection refactoring (r8296)
                    reverse_type = self.introspection.DATA_TYPES_REVERSE.get(type_code)
            except KeyError:
                reverse_type = self.get_field_db_type_lookup(type_code)
                if not reverse_type:
                    # type_code not found in data_types_reverse map
                    key = (self.differences[-1][:2], description[:2])
                    if key not in self.unknown_db_fields:
                        self.unknown_db_fields[key] = 1
                        self.add_difference('comment', "Unknown database type for field '%s' (%s)" % (description[0], type_code))
                    return None

        kwargs = {}
        if isinstance(reverse_type, tuple):
            kwargs.update(reverse_type[1])
            reverse_type = reverse_type[0]

        if reverse_type == "CharField" and description[3]:
            kwargs['max_length'] = description[3]

        if reverse_type == "DecimalField":
            kwargs['max_digits'] = description[4]
            kwargs['decimal_places'] = description[5] and abs(description[5]) or description[5]

        if description[6]:
            kwargs['blank'] = True
            if reverse_type not in ('TextField', 'CharField'):
                kwargs['null'] = True

        if '.' in reverse_type:
            from django.utils import importlib
            # TODO: when was importlib added to django.utils ? and do we
            # need to add backwards compatibility code ?
            module_path, package_name = reverse_type.rsplit('.', 1)
            module = importlib.import_module(module_path)
            field_db_type = getattr(module, package_name)(**kwargs).db_type(connection=connection)
        else:
            field_db_type = getattr(models, reverse_type)(**kwargs).db_type(connection=connection)
        return field_db_type

    def get_field_db_type_lookup(self, type_code):
        return None

    def get_field_db_nullable(self, field, table_name):
        tablespace = field.db_tablespace
        if tablespace == "":
            tablespace = "public"
        return self.null.get((tablespace, table_name, field.attname), 'fixme')

    def strip_parameters(self, field_type):
        if field_type and field_type != 'double precision':
            return field_type.split(" ")[0].split("(")[0].lower()
        return field_type

    def find_unique_missing_in_db(self, meta, table_indexes, table_constraints, table_name):
        for field in all_local_fields(meta):
            if field.unique:
                attname = field.db_column or field.attname
                db_field_unique = table_indexes[attname]['unique']
                if not db_field_unique and table_constraints:
                    db_field_unique = any(constraint['unique'] for contraint_name, constraint in six.iteritems(table_constraints) if attname in constraint['columns'])
                if attname in table_indexes and db_field_unique:
                    continue
                self.add_difference('unique-missing-in-db', table_name, attname)

    def find_unique_missing_in_model(self, meta, table_indexes, table_constraints, table_name):
        # TODO: Postgresql does not list unique_togethers in table_indexes
        #       MySQL does
        fields = dict([(field.db_column or field.name, field.unique) for field in all_local_fields(meta)])
        for att_name, att_opts in six.iteritems(table_indexes):
            db_field_unique = att_opts['unique']
            if not db_field_unique and table_constraints:
                db_field_unique = any(constraint['unique'] for contraint_name, constraint in six.iteritems(table_constraints) if att_name in constraint['columns'])
            if db_field_unique and att_name in fields and not fields[att_name]:
                if att_name in flatten(meta.unique_together):
                    continue
                self.add_difference('unique-missing-in-model', table_name, att_name)

    def find_index_missing_in_db(self, meta, table_indexes, table_constraints, table_name):
        for field in all_local_fields(meta):
            if field.db_index:
                attname = field.db_column or field.attname
                if attname not in table_indexes:
                    self.add_difference('index-missing-in-db', table_name, attname, '', '')
                    db_type = field.db_type(connection=connection)
                    if db_type.startswith('varchar'):
                        self.add_difference('index-missing-in-db', table_name, attname, 'like', ' varchar_pattern_ops')
                    if db_type.startswith('text'):
                        self.add_difference('index-missing-in-db', table_name, attname, 'like', ' text_pattern_ops')

    def find_index_missing_in_model(self, meta, table_indexes, table_constraints, table_name):
        fields = dict([(field.name, field) for field in all_local_fields(meta)])
        for att_name, att_opts in six.iteritems(table_indexes):
            if att_name in fields:
                field = fields[att_name]
                db_field_unique = att_opts['unique']
                if not db_field_unique and table_constraints:
                    db_field_unique = any(constraint['unique'] for contraint_name, constraint in six.iteritems(table_constraints) if att_name in constraint['columns'])
                if field.db_index:
                    continue
                if att_opts['primary_key'] and field.primary_key:
                    continue
                if db_field_unique and field.unique:
                    continue
                if db_field_unique and att_name in flatten(meta.unique_together):
                    continue
                self.add_difference('index-missing-in-model', table_name, att_name)
                db_type = field.db_type(connection=connection)
                if db_type.startswith('varchar') or db_type.startswith('text'):
                    self.add_difference('index-missing-in-model', table_name, att_name, 'like')

    def find_field_missing_in_model(self, fieldmap, table_description, table_name):
        for row in table_description:
            if row[0] not in fieldmap:
                self.add_difference('field-missing-in-model', table_name, row[0])

    def find_field_missing_in_db(self, fieldmap, table_description, table_name):
        db_fields = [row[0] for row in table_description]
        for field_name, field in six.iteritems(fieldmap):
            if field_name not in db_fields:
                field_output = []
                if field.rel:
                    field_output.extend([field.rel.to._meta.db_table, field.rel.to._meta.get_field(field.rel.field_name).column])
                    op = 'fkey-missing-in-db'
                else:
                    op = 'field-missing-in-db'
                field_output.append(field.db_type(connection=connection))
                if not field.null:
                    field_output.append('NOT NULL')
                self.add_difference(op, table_name, field_name, *field_output)
                self.new_db_fields.add((table_name, field_name))

    def find_field_type_differ(self, meta, table_description, table_name, func=None):
        db_fields = dict([(row[0], row) for row in table_description])
        for field in all_local_fields(meta):
            if field.name not in db_fields:
                continue
            description = db_fields[field.name]

            model_type = self.get_field_model_type(field)
            db_type = self.get_field_db_type(description, field)

            # use callback function if defined
            if func:
                model_type, db_type = func(field, description, model_type, db_type)

            if not self.strip_parameters(db_type) == self.strip_parameters(model_type):
                self.add_difference('field-type-differ', table_name, field.name, model_type, db_type)

    def find_field_parameter_differ(self, meta, table_description, table_name, func=None):
        db_fields = dict([(row[0], row) for row in table_description])
        for field in all_local_fields(meta):
            if field.name not in db_fields:
                continue
            description = db_fields[field.name]

            model_type = self.get_field_model_type(field)
            db_type = self.get_field_db_type(description, field, table_name)

            if not self.strip_parameters(model_type) == self.strip_parameters(db_type):
                continue

            # use callback function if defined
            if func:
                model_type, db_type = func(field, description, model_type, db_type)

            if not model_type == db_type:
                self.add_difference('field-parameter-differ', table_name, field.name, model_type, db_type)

    def find_field_notnull_differ(self, meta, table_description, table_name):
        if not self.can_detect_notnull_differ:
            return

        for field in all_local_fields(meta):
            if (table_name, field.attname) in self.new_db_fields:
                continue
            null = self.get_field_db_nullable(field, table_name)
            if field.null != null:
                action = field.null and 'DROP' or 'SET'
                self.add_difference('notnull-differ', table_name, field.attname, action)

    def get_constraints(self, cursor, table_name, introspection):
        return {}

    @transaction.commit_manually
    def find_differences(self):
        cur_app_label = None
        for app_model in self.app_models:
            meta = app_model._meta
            table_name = meta.db_table
            app_label = meta.app_label

            if cur_app_label != app_label:
                # Marker indicating start of difference scan for this table_name
                self.add_app_model_marker(app_label, app_model.__name__)

            if table_name not in self.db_tables:
                # Table is missing from database
                self.add_difference('table-missing-in-db', table_name)
                continue

            table_indexes = self.introspection.get_indexes(self.cursor, table_name)
            if hasattr(self.introspection, 'get_constraints'):
                table_constraints = self.introspection.get_constraints(self.cursor, table_name)
            else:
                table_constraints = self.get_constraints(self.cursor, table_name, self.introspection)

            fieldmap = dict([(field.db_column or field.get_attname(), field) for field in all_local_fields(meta)])

            # add ordering field if model uses order_with_respect_to
            if meta.order_with_respect_to:
                fieldmap['_order'] = ORDERING_FIELD

            try:
                table_description = self.introspection.get_table_description(self.cursor, table_name)
            except Exception as e:
                self.add_difference('error', 'unable to introspect table: %s' % str(e).strip())
                transaction.rollback()  # reset transaction
                continue
            else:
                transaction.commit()

            # Fields which are defined in database but not in model
            # 1) find: 'unique-missing-in-model'
            self.find_unique_missing_in_model(meta, table_indexes, table_constraints, table_name)
            # 2) find: 'index-missing-in-model'
            self.find_index_missing_in_model(meta, table_indexes, table_constraints, table_name)
            # 3) find: 'field-missing-in-model'
            self.find_field_missing_in_model(fieldmap, table_description, table_name)

            # Fields which are defined in models but not in database
            # 4) find: 'field-missing-in-db'
            self.find_field_missing_in_db(fieldmap, table_description, table_name)
            # 5) find: 'unique-missing-in-db'
            self.find_unique_missing_in_db(meta, table_indexes, table_constraints, table_name)
            # 6) find: 'index-missing-in-db'
            self.find_index_missing_in_db(meta, table_indexes, table_constraints, table_name)

            # Fields which have a different type or parameters
            # 7) find: 'type-differs'
            self.find_field_type_differ(meta, table_description, table_name)
            # 8) find: 'type-parameter-differs'
            self.find_field_parameter_differ(meta, table_description, table_name)
            # 9) find: 'field-notnull'
            self.find_field_notnull_differ(meta, table_description, table_name)

    def print_diff(self, style=no_style()):
        """ print differences to stdout """
        if self.options.get('sql', True):
            self.print_diff_sql(style)
        else:
            self.print_diff_text(style)

    def print_diff_text(self, style):
        if not self.can_detect_notnull_differ:
            print(style.NOTICE("# Detecting notnull changes not implemented for this database backend"))
            print("")

        cur_app_label = None
        for app_label, model_name, diffs in self.differences:
            if not diffs:
                continue
            if not self.dense and cur_app_label != app_label:
                print("%s %s" % (style.NOTICE("+ Application:"), style.SQL_TABLE(app_label)))
                cur_app_label = app_label
            if not self.dense:
                print("%s %s" % (style.NOTICE("|-+ Differences for model:"), style.SQL_TABLE(model_name)))
            for diff in diffs:
                diff_type, diff_args = diff
                text = self.DIFF_TEXTS[diff_type] % dict((str(i), style.SQL_TABLE(e)) for i, e in enumerate(diff_args))
                text = "'".join(i % 2 == 0 and style.ERROR(e) or e for i, e in enumerate(text.split("'")))
                if not self.dense:
                    print("%s %s" % (style.NOTICE("|--+"), text))
                else:
                    print("%s %s %s %s %s" % (style.NOTICE("App"), style.SQL_TABLE(app_label), style.NOTICE('Model'), style.SQL_TABLE(model_name), text))

    def print_diff_sql(self, style):
        if not self.can_detect_notnull_differ:
            print(style.NOTICE("-- Detecting notnull changes not implemented for this database backend"))
            print("")

        cur_app_label = None
        qn = connection.ops.quote_name
        has_differences = max([len(diffs) for app_label, model_name, diffs in self.differences])
        if not has_differences:
            if not self.dense:
                print(style.SQL_KEYWORD("-- No differences"))
        else:
            print(style.SQL_KEYWORD("BEGIN;"))
            for app_label, model_name, diffs in self.differences:
                if not diffs:
                    continue
                if not self.dense and cur_app_label != app_label:
                    print(style.NOTICE("-- Application: %s" % style.SQL_TABLE(app_label)))
                    cur_app_label = app_label
                if not self.dense:
                    print(style.NOTICE("-- Model: %s" % style.SQL_TABLE(model_name)))
                for diff in diffs:
                    diff_type, diff_args = diff
                    text = self.DIFF_SQL[diff_type](style, qn, diff_args)
                    if self.dense:
                        text = text.replace("\n\t", " ")
                    print(text)
            print(style.SQL_KEYWORD("COMMIT;"))


class GenericSQLDiff(SQLDiff):
    can_detect_notnull_differ = False


class MySQLDiff(SQLDiff):
    can_detect_notnull_differ = False

    # All the MySQL hacks together create something of a problem
    # Fixing one bug in MySQL creates another issue. So just keep in mind
    # that this is way unreliable for MySQL atm.
    def get_field_db_type(self, description, field=None, table_name=None):
        from MySQLdb.constants import FIELD_TYPE
        # weird bug? in mysql db-api where it returns three times the correct value for field length
        # if i remember correctly it had something todo with unicode strings
        # TODO: Fix this is a more meaningful and better understood manner
        description = list(description)
        if description[1] not in [FIELD_TYPE.TINY, FIELD_TYPE.SHORT]:  # exclude tinyints from conversion.
            description[3] = description[3] / 3
            description[4] = description[4] / 3
        db_type = super(MySQLDiff, self).get_field_db_type(description)
        if not db_type:
            return
        if field:
            if field.primary_key and (db_type == 'integer' or db_type == 'bigint'):
                db_type += ' AUTO_INCREMENT'
            # MySQL isn't really sure about char's and varchar's like sqlite
            field_type = self.get_field_model_type(field)
            # Fix char/varchar inconsistencies
            if self.strip_parameters(field_type) == 'char' and self.strip_parameters(db_type) == 'varchar':
                db_type = db_type.lstrip("var")
            # They like to call 'bool's 'tinyint(1)' and introspection makes that a integer
            # just convert it back to it's proper type, a bool is a bool and nothing else.
            if db_type == 'integer' and description[1] == FIELD_TYPE.TINY and description[4] == 1:
                db_type = 'bool'
            if db_type == 'integer' and description[1] == FIELD_TYPE.SHORT:
                db_type = 'smallint UNSIGNED'  # FIXME: what about if it's not UNSIGNED ?
        return db_type


class SqliteSQLDiff(SQLDiff):
    can_detect_notnull_differ = True

    def load_null(self):
        for table_name in self.db_tables:
            # sqlite does not support tablespaces
            tablespace = "public"
            # index, column_name, column_type, nullable, default_value
            # see: http://www.sqlite.org/pragma.html#pragma_table_info
            for table_info in self.sql_to_dict("PRAGMA table_info(%s);" % table_name, []):
                key = (tablespace, table_name, table_info['name'])
                self.null[key] = not table_info['notnull']

    # Unique does not seem to be implied on Sqlite for Primary_key's
    # if this is more generic among databases this might be usefull
    # to add to the superclass's find_unique_missing_in_db method
    def find_unique_missing_in_db(self, meta, table_indexes, table_constraints, table_name):
        for field in all_local_fields(meta):
            if field.unique:
                attname = field.db_column or field.attname
                if attname in table_indexes and table_indexes[attname]['unique']:
                    continue
                if attname in table_indexes and table_indexes[attname]['primary_key']:
                    continue
                self.add_difference('unique-missing-in-db', table_name, attname)

    # Finding Indexes by using the get_indexes dictionary doesn't seem to work
    # for sqlite.
    def find_index_missing_in_db(self, meta, table_indexes, table_constraints, table_name):
        pass

    def find_index_missing_in_model(self, meta, table_indexes, table_constraints, table_name):
        pass

    def get_field_db_type(self, description, field=None, table_name=None):
        db_type = super(SqliteSQLDiff, self).get_field_db_type(description)
        if not db_type:
            return
        if field:
            field_type = self.get_field_model_type(field)
            # Fix char/varchar inconsistencies
            if self.strip_parameters(field_type) == 'char' and self.strip_parameters(db_type) == 'varchar':
                db_type = db_type.lstrip("var")
        return db_type


class PostgresqlSQLDiff(SQLDiff):
    can_detect_notnull_differ = True

    DATA_TYPES_REVERSE_OVERRIDE = {
        1042: 'CharField',
        # postgis types (TODO: support is very incomplete)
        17506: 'django.contrib.gis.db.models.fields.PointField',
        55902: 'django.contrib.gis.db.models.fields.MultiPolygonField',
    }

    DATA_TYPES_REVERSE_NAME = {
        'hstore': 'django_hstore.hstore.DictionaryField',
    }

    # Hopefully in the future we can add constraint checking and other more
    # advanced checks based on this database.
    SQL_LOAD_CONSTRAINTS = """
    SELECT nspname, relname, conname, attname, pg_get_constraintdef(pg_constraint.oid)
    FROM pg_constraint
    INNER JOIN pg_attribute ON pg_constraint.conrelid = pg_attribute.attrelid AND pg_attribute.attnum = any(pg_constraint.conkey)
    INNER JOIN pg_class ON conrelid=pg_class.oid
    INNER JOIN pg_namespace ON pg_namespace.oid=pg_class.relnamespace
    ORDER BY CASE WHEN contype='f' THEN 0 ELSE 1 END,contype,nspname,relname,conname;
    """
    SQL_LOAD_NULL = """
    SELECT nspname, relname, attname, attnotnull
    FROM pg_attribute
    INNER JOIN pg_class ON attrelid=pg_class.oid
    INNER JOIN pg_namespace ON pg_namespace.oid=pg_class.relnamespace;
    """

    SQL_FIELD_TYPE_DIFFER = lambda self, style, qn, args: "%s %s\n\t%s %s %s %s;" % (style.SQL_KEYWORD('ALTER TABLE'), style.SQL_TABLE(qn(args[0])), style.SQL_KEYWORD('ALTER'), style.SQL_FIELD(qn(args[1])), style.SQL_KEYWORD("TYPE"), style.SQL_COLTYPE(args[2]))
    SQL_FIELD_PARAMETER_DIFFER = lambda self, style, qn, args: "%s %s\n\t%s %s %s %s;" % (style.SQL_KEYWORD('ALTER TABLE'), style.SQL_TABLE(qn(args[0])), style.SQL_KEYWORD('ALTER'), style.SQL_FIELD(qn(args[1])), style.SQL_KEYWORD("TYPE"), style.SQL_COLTYPE(args[2]))
    SQL_NOTNULL_DIFFER = lambda self, style, qn, args: "%s %s\n\t%s %s %s %s;" % (style.SQL_KEYWORD('ALTER TABLE'), style.SQL_TABLE(qn(args[0])), style.SQL_KEYWORD('ALTER COLUMN'), style.SQL_FIELD(qn(args[1])), style.SQL_KEYWORD(args[2]), style.SQL_KEYWORD('NOT NULL'))

    def __init__(self, app_models, options):
        SQLDiff.__init__(self, app_models, options)
        self.check_constraints = {}
        self.load_constraints()

    def load_null(self):
        for dct in self.sql_to_dict(self.SQL_LOAD_NULL, []):
            key = (dct['nspname'], dct['relname'], dct['attname'])
            self.null[key] = not dct['attnotnull']

    def load_constraints(self):
        for dct in self.sql_to_dict(self.SQL_LOAD_CONSTRAINTS, []):
            key = (dct['nspname'], dct['relname'], dct['attname'])
            if 'CHECK' in dct['pg_get_constraintdef']:
                self.check_constraints[key] = dct

    def get_constraints(self, cursor, table_name, introspection):
        """ backport of django's introspection.get_constraints(...) """
        constraints = {}
        # Loop over the key table, collecting things as constraints
        # This will get PKs, FKs, and uniques, but not CHECK
        cursor.execute("""
            SELECT
                kc.constraint_name,
                kc.column_name,
                c.constraint_type,
                array(SELECT table_name::text || '.' || column_name::text FROM information_schema.constraint_column_usage WHERE constraint_name = kc.constraint_name)
            FROM information_schema.key_column_usage AS kc
            JOIN information_schema.table_constraints AS c ON
                kc.table_schema = c.table_schema AND
                kc.table_name = c.table_name AND
                kc.constraint_name = c.constraint_name
            WHERE
                kc.table_schema = %s AND
                kc.table_name = %s
        """, ["public", table_name])
        for constraint, column, kind, used_cols in cursor.fetchall():
            # If we're the first column, make the record
            if constraint not in constraints:
                constraints[constraint] = {
                    "columns": [],
                    "primary_key": kind.lower() == "primary key",
                    "unique": kind.lower() in ["primary key", "unique"],
                    "foreign_key": tuple(used_cols[0].split(".", 1)) if kind.lower() == "foreign key" else None,
                    "check": False,
                    "index": False,
                }
            # Record the details
            constraints[constraint]['columns'].append(column)
        # Now get CHECK constraint columns
        cursor.execute("""
            SELECT kc.constraint_name, kc.column_name
            FROM information_schema.constraint_column_usage AS kc
            JOIN information_schema.table_constraints AS c ON
                kc.table_schema = c.table_schema AND
                kc.table_name = c.table_name AND
                kc.constraint_name = c.constraint_name
            WHERE
                c.constraint_type = 'CHECK' AND
                kc.table_schema = %s AND
                kc.table_name = %s
        """, ["public", table_name])
        for constraint, column in cursor.fetchall():
            # If we're the first column, make the record
            if constraint not in constraints:
                constraints[constraint] = {
                    "columns": [],
                    "primary_key": False,
                    "unique": False,
                    "foreign_key": None,
                    "check": True,
                    "index": False,
                }
            # Record the details
            constraints[constraint]['columns'].append(column)
        # Now get indexes
        cursor.execute("""
            SELECT
                c2.relname,
                ARRAY(
                    SELECT (SELECT attname FROM pg_catalog.pg_attribute WHERE attnum = i AND attrelid = c.oid)
                    FROM unnest(idx.indkey) i
                ),
                idx.indisunique,
                idx.indisprimary
            FROM pg_catalog.pg_class c, pg_catalog.pg_class c2,
                pg_catalog.pg_index idx
            WHERE c.oid = idx.indrelid
                AND idx.indexrelid = c2.oid
                AND c.relname = %s
        """, [table_name])
        for index, columns, unique, primary in cursor.fetchall():
            if index not in constraints:
                constraints[index] = {
                    "columns": list(columns),
                    "primary_key": primary,
                    "unique": unique,
                    "foreign_key": None,
                    "check": False,
                    "index": True,
                }
        return constraints

    def get_field_db_type(self, description, field=None, table_name=None):
        db_type = super(PostgresqlSQLDiff, self).get_field_db_type(description)
        if not db_type:
            return
        if field:
            if field.primary_key:
                if db_type == 'integer':
                    db_type = 'serial'
                elif db_type == 'bigint':
                    db_type = 'bigserial'
            if table_name:
                tablespace = field.db_tablespace
                if tablespace == "":
                    tablespace = "public"
                check_constraint = self.check_constraints.get((tablespace, table_name, field.attname), {}).get('pg_get_constraintdef', None)
                if check_constraint:
                    check_constraint = check_constraint.replace("((", "(")
                    check_constraint = check_constraint.replace("))", ")")
                    check_constraint = '("'.join([')' in e and '" '.join(p.strip('"') for p in e.split(" ", 1)) or e for e in check_constraint.split("(")])
                    # TODO: might be more then one constraint in definition ?
                    db_type += ' ' + check_constraint
        return db_type

    @transaction.autocommit
    def get_field_db_type_lookup(self, type_code):
        try:
            name = self.sql_to_dict("SELECT typname FROM pg_type WHERE typelem=%s;", [type_code])[0]['typname']
            return self.DATA_TYPES_REVERSE_NAME.get(name.strip('_'))
        except (IndexError, KeyError):
            pass

    """
    def find_field_type_differ(self, meta, table_description, table_name):
        def callback(field, description, model_type, db_type):
            if field.primary_key and db_type=='integer':
                db_type = 'serial'
            return model_type, db_type
        super(PostgresqlSQLDiff, self).find_field_type_differ(meta, table_description, table_name, callback)
    """

DATABASE_SQLDIFF_CLASSES = {
    'postgis': PostgresqlSQLDiff,
    'postgresql_psycopg2': PostgresqlSQLDiff,
    'postgresql': PostgresqlSQLDiff,
    'mysql': MySQLDiff,
    'sqlite3': SqliteSQLDiff,
    'oracle': GenericSQLDiff
}


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--all-applications', '-a', action='store_true', dest='all_applications',
                    help="Automaticly include all application from INSTALLED_APPS."),
        make_option('--not-only-existing', '-e', action='store_false', dest='only_existing',
                    help="Check all tables that exist in the database, not only tables that should exist based on models."),
        make_option('--dense-output', '-d', action='store_true', dest='dense_output',
                    help="Shows the output in dense format, normally output is spreaded over multiple lines."),
        make_option('--output_text', '-t', action='store_false', dest='sql', default=True,
                    help="Outputs the differences as descriptive text instead of SQL"),
    )

    help = """Prints the (approximated) difference between models and fields in the database for the given app name(s).

It indicates how columns in the database are different from the sql that would
be generated by Django. This command is not a database migration tool. (Though
it can certainly help) It's purpose is to show the current differences as a way
to check/debug ur models compared to the real database tables and columns."""

    output_transaction = False
    args = '<appname appname ...>'

    def handle(self, *app_labels, **options):
        from django.db import models
        from django.conf import settings

        engine = None
        if hasattr(settings, 'DATABASES'):
            engine = settings.DATABASES['default']['ENGINE']
        else:
            engine = settings.DATABASE_ENGINE

        if engine == 'dummy':
            # This must be the "dummy" database backend, which means the user
            # hasn't set DATABASE_ENGINE.
            raise CommandError("""Django doesn't know which syntax to use for your SQL statements,
because you haven't specified the DATABASE_ENGINE setting.
Edit your settings file and change DATABASE_ENGINE to something like 'postgresql' or 'mysql'.""")

        if options.get('all_applications', False):
            app_models = models.get_models(include_auto_created=True)
        else:
            if not app_labels:
                raise CommandError('Enter at least one appname.')
            try:
                app_list = [models.get_app(app_label) for app_label in app_labels]
            except (models.ImproperlyConfigured, ImportError) as e:
                raise CommandError("%s. Are you sure your INSTALLED_APPS setting is correct?" % e)

            app_models = []
            for app in app_list:
                app_models.extend(models.get_models(app, include_auto_created=True))

        ## remove all models that are not managed by Django
        #app_models = [model for model in app_models if getattr(model._meta, 'managed', True)]

        if not app_models:
            raise CommandError('Unable to execute sqldiff no models founds.')

        if not engine:
            engine = connection.__module__.split('.')[-2]

        if '.' in engine:
            engine = engine.split('.')[-1]

        cls = DATABASE_SQLDIFF_CLASSES.get(engine, GenericSQLDiff)
        sqldiff_instance = cls(app_models, options)
        sqldiff_instance.find_differences()
        sqldiff_instance.print_diff(self.style)
        return

########NEW FILE########
__FILENAME__ = syncdata
"""
SyncData
========

Django command similar to 'loaddata' but also deletes.
After 'syncdata' has run, the database will have the same data as the fixture - anything
missing will of been added, anything different will of been updated,
and anything extra will of been deleted.
"""

import os
import sys
import six
from django.core.management.base import BaseCommand
from django.core.management.color import no_style


class Command(BaseCommand):
    """ syncdata command """

    help = 'Makes the current database have the same data as the fixture(s), no more, no less.'
    args = "fixture [fixture ...]"

    def remove_objects_not_in(self, objects_to_keep, verbosity):
        """
        Deletes all the objects in the database that are not in objects_to_keep.
        - objects_to_keep: A map where the keys are classes, and the values are a
         set of the objects of that class we should keep.
        """
        for class_ in objects_to_keep.keys():
            current = class_.objects.all()
            current_ids = set([x.pk for x in current])
            keep_ids = set([x.pk for x in objects_to_keep[class_]])

            remove_these_ones = current_ids.difference(keep_ids)
            if remove_these_ones:
                for obj in current:
                    if obj.pk in remove_these_ones:
                        obj.delete()
                        if verbosity >= 2:
                            print("Deleted object: %s" % six.u(obj))

            if verbosity > 0 and remove_these_ones:
                num_deleted = len(remove_these_ones)
                if num_deleted > 1:
                    type_deleted = six.u(class_._meta.verbose_name_plural)
                else:
                    type_deleted = six.u(class_._meta.verbose_name)

                print("Deleted %s %s" % (str(num_deleted), type_deleted))

    def handle(self, *fixture_labels, **options):
        """ Main method of a Django command """
        from django.db.models import get_apps
        from django.core import serializers
        from django.db import connection, transaction
        from django.conf import settings

        self.style = no_style()

        verbosity = int(options.get('verbosity', 1))
        show_traceback = options.get('traceback', False)

        # Keep a count of the installed objects and fixtures
        fixture_count = 0
        object_count = 0
        objects_per_fixture = []
        models = set()

        humanize = lambda dirname: dirname and "'%s'" % dirname or 'absolute path'

        # Get a cursor (even though we don't need one yet). This has
        # the side effect of initializing the test database (if
        # it isn't already initialized).
        cursor = connection.cursor()

        # Start transaction management. All fixtures are installed in a
        # single transaction to ensure that all references are resolved.
        transaction.commit_unless_managed()
        transaction.enter_transaction_management()
        transaction.managed(True)

        app_fixtures = [os.path.join(os.path.dirname(app.__file__), 'fixtures') for app in get_apps()]
        for fixture_label in fixture_labels:
            parts = fixture_label.split('.')
            if len(parts) == 1:
                fixture_name = fixture_label
                formats = serializers.get_public_serializer_formats()
            else:
                fixture_name, format = '.'.join(parts[:-1]), parts[-1]
                if format in serializers.get_public_serializer_formats():
                    formats = [format]
                else:
                    formats = []

            if formats:
                if verbosity > 1:
                    print("Loading '%s' fixtures..." % fixture_name)
            else:
                sys.stderr.write(self.style.ERROR("Problem installing fixture '%s': %s is not a known serialization format." % (fixture_name, format)))
                transaction.rollback()
                transaction.leave_transaction_management()
                return

            if os.path.isabs(fixture_name):
                fixture_dirs = [fixture_name]
            else:
                fixture_dirs = app_fixtures + list(settings.FIXTURE_DIRS) + ['']

            for fixture_dir in fixture_dirs:
                if verbosity > 1:
                    print("Checking %s for fixtures..." % humanize(fixture_dir))

                label_found = False
                for format in formats:
                    #serializer = serializers.get_serializer(format)
                    if verbosity > 1:
                        print("Trying %s for %s fixture '%s'..." % (humanize(fixture_dir), format, fixture_name))
                    try:
                        full_path = os.path.join(fixture_dir, '.'.join([fixture_name, format]))
                        fixture = open(full_path, 'r')
                        if label_found:
                            fixture.close()
                            print(self.style.ERROR("Multiple fixtures named '%s' in %s. Aborting." % (fixture_name, humanize(fixture_dir))))
                            transaction.rollback()
                            transaction.leave_transaction_management()
                            return
                        else:
                            fixture_count += 1
                            objects_per_fixture.append(0)
                            if verbosity > 0:
                                print("Installing %s fixture '%s' from %s." % (format, fixture_name, humanize(fixture_dir)))
                            try:
                                objects_to_keep = {}
                                objects = serializers.deserialize(format, fixture)
                                for obj in objects:
                                    object_count += 1
                                    objects_per_fixture[-1] += 1

                                    class_ = obj.object.__class__
                                    if class_ not in objects_to_keep:
                                        objects_to_keep[class_] = set()
                                    objects_to_keep[class_].add(obj.object)

                                    models.add(class_)
                                    obj.save()

                                self.remove_objects_not_in(objects_to_keep, verbosity)

                                label_found = True
                            except (SystemExit, KeyboardInterrupt):
                                raise
                            except Exception:
                                import traceback
                                fixture.close()
                                transaction.rollback()
                                transaction.leave_transaction_management()
                                if show_traceback:
                                    traceback.print_exc()
                                else:
                                    sys.stderr.write(self.style.ERROR("Problem installing fixture '%s': %s\n" % (full_path, traceback.format_exc())))
                                return
                            fixture.close()
                    except:
                        if verbosity > 1:
                            print("No %s fixture '%s' in %s." % (format, fixture_name, humanize(fixture_dir)))

        # If any of the fixtures we loaded contain 0 objects, assume that an
        # error was encountered during fixture loading.
        if 0 in objects_per_fixture:
            sys.stderr.write(
                self.style.ERROR("No fixture data found for '%s'. (File format may be invalid.)" % (fixture_name)))
            transaction.rollback()
            transaction.leave_transaction_management()
            return

        # If we found even one object in a fixture, we need to reset the
        # database sequences.
        if object_count > 0:
            sequence_sql = connection.ops.sequence_reset_sql(self.style, models)
            if sequence_sql:
                if verbosity > 1:
                    print("Resetting sequences")
                for line in sequence_sql:
                    cursor.execute(line)

        transaction.commit()
        transaction.leave_transaction_management()

        if object_count == 0:
            if verbosity > 1:
                print("No fixtures found.")
        else:
            if verbosity > 0:
                print("Installed %d object(s) from %d fixture(s)" % (object_count, fixture_count))

        # Close the DB connection. This is required as a workaround for an
        # edge case in MySQL: if the same connection is used to
        # create tables, load data, and query, the query can return
        # incorrect results. See Django #7572, MySQL #37735.
        connection.close()

########NEW FILE########
__FILENAME__ = sync_s3
"""
Sync Media to S3
================

Django command that scans all files in your settings.MEDIA_ROOT and
settings.STATIC_ROOT folders and uploads them to S3 with the same directory
structure.

This command can optionally do the following but it is off by default:
* gzip compress any CSS and Javascript files it finds and adds the appropriate
  'Content-Encoding' header.
* set a far future 'Expires' header for optimal caching.
* upload only media or static files.
* use any other provider compatible with Amazon S3.
* set other than 'public-read' ACL.

Note: This script requires the Python boto library and valid Amazon Web
Services API keys.

Required settings.py variables:
AWS_ACCESS_KEY_ID = ''
AWS_SECRET_ACCESS_KEY = ''
AWS_BUCKET_NAME = ''

When you call this command with the `--renamegzip` param, it will add
the '.gz' extension to the file name. But Safari just doesn't recognize
'.gz' files and your site won't work on it! To fix this problem, you can
set any other extension (like .jgz) in the `SYNC_S3_RENAME_GZIP_EXT`
variable.

Command options are:
  -p PREFIX, --prefix=PREFIX
                        The prefix to prepend to the path on S3.
  --gzip                Enables gzipping CSS and Javascript files.
  --expires             Enables setting a far future expires header.
  --force               Skip the file mtime check to force upload of all
                        files.
  --filter-list         Override default directory and file exclusion
                        filters. (enter as comma separated line)
  --renamegzip          Enables renaming of gzipped files by appending '.gz'.
                        to the original file name. This way your original
                        assets will not be replaced by the gzipped ones.
                        You can change the extension setting the
                        `SYNC_S3_RENAME_GZIP_EXT` var in your settings.py
                        file.
  --invalidate          Invalidates the objects in CloudFront after uploading
                        stuff to s3.
  --media-only          Only MEDIA_ROOT files will be uploaded to S3.
  --static-only         Only STATIC_ROOT files will be uploaded to S3.
  --s3host              Override default s3 host.
  --acl                 Override default ACL settings ('public-read' if
                        settings.AWS_DEFAULT_ACL is not defined).

TODO:
 * Use fnmatch (or regex) to allow more complex FILTER_LIST rules.

"""
import datetime
import email
import mimetypes
from optparse import make_option
import os
import time
import gzip
try:
    from cStringIO import StringIO
    assert StringIO
except ImportError:
    from StringIO import StringIO


from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

# Make sure boto is available
try:
    import boto
    import boto.exception
    HAS_BOTO = True
except ImportError:
    HAS_BOTO = False


class Command(BaseCommand):
    # Extra variables to avoid passing these around
    AWS_ACCESS_KEY_ID = ''
    AWS_SECRET_ACCESS_KEY = ''
    AWS_BUCKET_NAME = ''
    AWS_CLOUDFRONT_DISTRIBUTION = ''
    SYNC_S3_RENAME_GZIP_EXT = ''

    DIRECTORIES = ''
    FILTER_LIST = ['.DS_Store', '.svn', '.hg', '.git', 'Thumbs.db']
    GZIP_CONTENT_TYPES = (
        'text/css',
        'application/javascript',
        'application/x-javascript',
        'text/javascript'
    )

    uploaded_files = []
    upload_count = 0
    skip_count = 0

    option_list = BaseCommand.option_list + (
        make_option('-p', '--prefix',
                    dest='prefix',
                    default=getattr(settings, 'SYNC_S3_PREFIX', ''),
                    help="The prefix to prepend to the path on S3."),
        make_option('-d', '--dir',
                    dest='dir',
                    help="Custom static root directory to use"),
        make_option('--s3host',
                    dest='s3host',
                    default=getattr(settings, 'AWS_S3_HOST', ''),
                    help="The s3 host (enables connecting to other providers/regions)"),
        make_option('--acl',
                    dest='acl',
                    default=getattr(settings, 'AWS_DEFAULT_ACL', 'public-read'),
                    help="Enables to override default acl (public-read)."),
        make_option('--gzip',
                    action='store_true', dest='gzip', default=False,
                    help="Enables gzipping CSS and Javascript files."),
        make_option('--renamegzip',
                    action='store_true', dest='renamegzip', default=False,
                    help="Enables renaming of gzipped assets to have '.gz' appended to the filename."),
        make_option('--expires',
                    action='store_true', dest='expires', default=False,
                    help="Enables setting a far future expires header."),
        make_option('--force',
                    action='store_true', dest='force', default=False,
                    help="Skip the file mtime check to force upload of all files."),
        make_option('--filter-list', dest='filter_list',
                    action='store', default='',
                    help="Override default directory and file exclusion filters. (enter as comma seperated line)"),
        make_option('--invalidate', dest='invalidate', default=False,
                    action='store_true',
                    help='Invalidates the associated objects in CloudFront'),
        make_option('--media-only', dest='media_only', default='',
                    action='store_true',
                    help="Only MEDIA_ROOT files will be uploaded to S3"),
        make_option('--static-only', dest='static_only', default='',
                    action='store_true',
                    help="Only STATIC_ROOT files will be uploaded to S3"),
    )

    help = 'Syncs the complete MEDIA_ROOT structure and files to S3 into the given bucket name.'
    args = 'bucket_name'

    can_import_settings = True

    def handle(self, *args, **options):
        if not HAS_BOTO:
            raise ImportError("The boto Python library is not installed.")

        # Check for AWS keys in settings
        if not hasattr(settings, 'AWS_ACCESS_KEY_ID') or not hasattr(settings, 'AWS_SECRET_ACCESS_KEY'):
            raise CommandError('Missing AWS keys from settings file.  Please supply both AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.')
        else:
            self.AWS_ACCESS_KEY_ID = settings.AWS_ACCESS_KEY_ID
            self.AWS_SECRET_ACCESS_KEY = settings.AWS_SECRET_ACCESS_KEY

        if not hasattr(settings, 'AWS_BUCKET_NAME'):
            raise CommandError('Missing bucket name from settings file. Please add the AWS_BUCKET_NAME to your settings file.')
        else:
            if not settings.AWS_BUCKET_NAME:
                raise CommandError('AWS_BUCKET_NAME cannot be empty.')
        self.AWS_BUCKET_NAME = settings.AWS_BUCKET_NAME

        if not hasattr(settings, 'MEDIA_ROOT'):
            raise CommandError('MEDIA_ROOT must be set in your settings.')
        else:
            if not settings.MEDIA_ROOT:
                raise CommandError('MEDIA_ROOT must be set in your settings.')

        self.AWS_CLOUDFRONT_DISTRIBUTION = getattr(settings, 'AWS_CLOUDFRONT_DISTRIBUTION', '')

        self.SYNC_S3_RENAME_GZIP_EXT = \
            getattr(settings, 'SYNC_S3_RENAME_GZIP_EXT', '.gz')

        self.verbosity = int(options.get('verbosity'))
        self.prefix = options.get('prefix')
        self.do_gzip = options.get('gzip')
        self.rename_gzip = options.get('renamegzip')
        self.do_expires = options.get('expires')
        self.do_force = options.get('force')
        self.invalidate = options.get('invalidate')
        self.DIRECTORIES = options.get('dir')
        self.s3host = options.get('s3host')
        self.default_acl = options.get('acl')
        self.FILTER_LIST = getattr(settings, 'FILTER_LIST', self.FILTER_LIST)
        filter_list = options.get('filter_list')
        if filter_list:
            # command line option overrides default filter_list and
            # settings.filter_list
            self.FILTER_LIST = filter_list.split(',')

        self.media_only = options.get('media_only')
        self.static_only = options.get('static_only')
        # Get directories
        if self.media_only and self.static_only:
            raise CommandError("Can't use --media-only and --static-only together. Better not use anything...")
        elif self.media_only:
            self.DIRECTORIES = [settings.MEDIA_ROOT]
        elif self.static_only:
            self.DIRECTORIES = [settings.STATIC_ROOT]
        elif self.DIRECTORIES:
            self.DIRECTORIES = [self.DIRECTORIES]
        else:
            self.DIRECTORIES = [settings.MEDIA_ROOT, settings.STATIC_ROOT]

        # Now call the syncing method to walk the MEDIA_ROOT directory and
        # upload all files found.
        self.sync_s3()

        # Sending the invalidation request to CloudFront if the user
        # requested this action
        if self.invalidate:
            self.invalidate_objects_cf()

        print("")
        print("%d files uploaded." % self.upload_count)
        print("%d files skipped." % self.skip_count)

    def open_cf(self):
        """
        Returns an open connection to CloudFront
        """
        return boto.connect_cloudfront(
            self.AWS_ACCESS_KEY_ID, self.AWS_SECRET_ACCESS_KEY)

    def invalidate_objects_cf(self):
        """
        Split the invalidation request in groups of 1000 objects
        """
        if not self.AWS_CLOUDFRONT_DISTRIBUTION:
            raise CommandError(
                'An object invalidation was requested but the variable '
                'AWS_CLOUDFRONT_DISTRIBUTION is not present in your settings.')

        # We can't send more than 1000 objects in the same invalidation
        # request.
        chunk = 1000

        # Connecting to CloudFront
        conn = self.open_cf()

        # Splitting the object list
        objs = self.uploaded_files
        chunks = [objs[i:i + chunk] for i in range(0, len(objs), chunk)]

        # Invalidation requests
        for paths in chunks:
            conn.create_invalidation_request(
                self.AWS_CLOUDFRONT_DISTRIBUTION, paths)

    def sync_s3(self):
        """
        Walks the media/static directories and syncs files to S3
        """
        bucket, key = self.open_s3()
        for directory in self.DIRECTORIES:
            os.path.walk(directory, self.upload_s3, (bucket, key, self.AWS_BUCKET_NAME, directory))

    def compress_string(self, s):
        """Gzip a given string."""
        zbuf = StringIO()
        zfile = gzip.GzipFile(mode='wb', compresslevel=6, fileobj=zbuf)
        zfile.write(s)
        zfile.close()
        return zbuf.getvalue()

    def get_s3connection_kwargs(self):
        """Returns connection kwargs as a dict"""
        kwargs = {}
        if self.s3host:
            kwargs['host'] = self.s3host
        return kwargs

    def open_s3(self):
        """
        Opens connection to S3 returning bucket and key
        """
        conn = boto.connect_s3(
            self.AWS_ACCESS_KEY_ID,
            self.AWS_SECRET_ACCESS_KEY,
            **self.get_s3connection_kwargs())
        try:
            bucket = conn.get_bucket(self.AWS_BUCKET_NAME)
        except boto.exception.S3ResponseError:
            bucket = conn.create_bucket(self.AWS_BUCKET_NAME)
        return bucket, boto.s3.key.Key(bucket)

    def upload_s3(self, arg, dirname, names):
        """
        This is the callback to os.path.walk and where much of the work happens
        """
        bucket, key, bucket_name, root_dir = arg

        # Skip directories we don't want to sync
        if os.path.basename(dirname) in self.FILTER_LIST:
            # prevent walk from processing subfiles/subdirs below the ignored one
            del names[:]
            return

        # Later we assume the MEDIA_ROOT ends with a trailing slash
        if not root_dir.endswith(os.path.sep):
            root_dir = root_dir + os.path.sep

        for file in names:
            headers = {}

            if file in self.FILTER_LIST:
                continue  # Skip files we don't want to sync

            filename = os.path.join(dirname, file)
            if os.path.isdir(filename):
                continue  # Don't try to upload directories

            file_key = filename[len(root_dir):]
            if self.prefix:
                file_key = '%s/%s' % (self.prefix, file_key)

            # Check if file on S3 is older than local file, if so, upload
            if not self.do_force:
                s3_key = bucket.get_key(file_key)
                if s3_key:
                    s3_datetime = datetime.datetime(*time.strptime(
                        s3_key.last_modified, '%a, %d %b %Y %H:%M:%S %Z')[0:6])
                    local_datetime = datetime.datetime.utcfromtimestamp(
                        os.stat(filename).st_mtime)
                    if local_datetime < s3_datetime:
                        self.skip_count += 1
                        if self.verbosity > 1:
                            print("File %s hasn't been modified since last being uploaded" % file_key)
                        continue

            # File is newer, let's process and upload
            if self.verbosity > 0:
                print("Uploading %s..." % file_key)

            content_type = mimetypes.guess_type(filename)[0]
            if content_type:
                headers['Content-Type'] = content_type
            else:
                headers['Content-Type'] = 'application/octet-stream'

            file_obj = open(filename, 'rb')
            file_size = os.fstat(file_obj.fileno()).st_size
            filedata = file_obj.read()
            if self.do_gzip:
                # Gzipping only if file is large enough (>1K is recommended)
                # and only if file is a common text type (not a binary file)
                if file_size > 1024 and content_type in self.GZIP_CONTENT_TYPES:
                    filedata = self.compress_string(filedata)
                    if self.rename_gzip:
                        # If rename_gzip is True, then rename the file
                        # by appending an extension (like '.gz)' to
                        # original filename.
                        file_key = '%s.%s' % (
                            file_key, self.SYNC_S3_RENAME_GZIP_EXT)
                    headers['Content-Encoding'] = 'gzip'
                    if self.verbosity > 1:
                        print("\tgzipped: %dk to %dk" % (file_size / 1024, len(filedata) / 1024))
            if self.do_expires:
                # HTTP/1.0
                headers['Expires'] = '%s GMT' % (email.Utils.formatdate(time.mktime((datetime.datetime.now() + datetime.timedelta(days=365 * 2)).timetuple())))
                # HTTP/1.1
                headers['Cache-Control'] = 'max-age %d' % (3600 * 24 * 365 * 2)
                if self.verbosity > 1:
                    print("\texpires: %s" % headers['Expires'])
                    print("\tcache-control: %s" % headers['Cache-Control'])

            try:
                key.name = file_key
                key.set_contents_from_string(filedata, headers, replace=True,
                                             policy=self.default_acl)
            except boto.exception.S3CreateError as e:
                print("Failed: %s" % e)
            except Exception as e:
                print(e)
                raise
            else:
                self.upload_count += 1
                self.uploaded_files.append(file_key)

            file_obj.close()

########NEW FILE########
__FILENAME__ = unreferenced_files
from collections import defaultdict
import os
from django.conf import settings
from django.core.management.base import NoArgsCommand
from django.db import models
from django.db.models.loading import cache


class Command(NoArgsCommand):
    help = "Prints a list of all files in MEDIA_ROOT that are not referenced in the database."

    def handle_noargs(self, **options):

        if settings.MEDIA_ROOT == '':
            print("MEDIA_ROOT is not set, nothing to do")
            return

        # Get a list of all files under MEDIA_ROOT
        media = []
        for root, dirs, files in os.walk(settings.MEDIA_ROOT):
            for f in files:
                media.append(os.path.abspath(os.path.join(root, f)))

        # Get list of all fields (value) for each model (key)
        # that is a FileField or subclass of a FileField
        model_dict = defaultdict(list)
        for app in cache.get_apps():
            model_list = cache.get_models(app)
            for model in model_list:
                for field in model._meta.fields:
                    if issubclass(field.__class__, models.FileField):
                        model_dict[model].append(field)

        # Get a list of all files referenced in the database
        referenced = []
        for model in model_dict:
            all = model.objects.all().iterator()
            for object in all:
                for field in model_dict[model]:
                    target_file = getattr(object, field.name)
                    if target_file:
                        referenced.append(os.path.abspath(target_file.path))

        # Print each file in MEDIA_ROOT that is not referenced in the database
        for m in media:
            if m not in referenced:
                print(m)

########NEW FILE########
__FILENAME__ = update_permissions
from django.core.management.base import BaseCommand
from django.db.models import get_models, get_app
from django.contrib.auth.management import create_permissions


class Command(BaseCommand):
    args = '<app app ...>'
    help = 'reloads permissions for specified apps, or all apps if no args are specified'

    def handle(self, *args, **options):
        if not args:
            apps = []
            for model in get_models():
                apps.append(get_app(model._meta.app_label))
        else:
            apps = []
            for arg in args:
                apps.append(get_app(arg))
        for app in apps:
            create_permissions(app, get_models(), int(options.get('verbosity', 0)))


########NEW FILE########
__FILENAME__ = validate_templates
import os
from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import color_style
from django.template.base import add_to_builtins
from django.template.loaders.filesystem import Loader
from django_extensions.utils import validatingtemplatetags

#
# TODO: Render the template with fake request object ?
#


class Command(BaseCommand):
    args = ''
    help = "Validate templates on syntax and compile errors"
    option_list = BaseCommand.option_list + (
        make_option('--break', '-b', action='store_true', dest='break',
                    default=False, help="Break on first error."),
        make_option('--check-urls', '-u', action='store_true', dest='check_urls',
                    default=False, help="Check url tag view names are quoted appropriately"),
        make_option('--force-new-urls', '-n', action='store_true', dest='force_new_urls',
                    default=False, help="Error on usage of old style url tags (without {% load urls from future %}"),
        make_option('--include', '-i', action='append', dest='includes',
                    default=[], help="Append these paths to TEMPLATE_DIRS")
    )

    def handle(self, *args, **options):
        from django.conf import settings
        style = color_style()
        template_dirs = set(settings.TEMPLATE_DIRS)
        template_dirs |= set(options.get('includes', []))
        template_dirs |= set(getattr(settings, 'VALIDATE_TEMPLATES_EXTRA_TEMPLATE_DIRS', []))
        settings.TEMPLATE_DIRS = list(template_dirs)
        settings.TEMPLATE_DEBUG = True
        verbosity = int(options.get('verbosity', 1))
        errors = 0

        template_loader = Loader()

        # Replace built in template tags with our own validating versions
        if options.get('check_urls', False):
            add_to_builtins('django_extensions.utils.validatingtemplatetags')

        for template_dir in template_dirs:
            for root, dirs, filenames in os.walk(template_dir):
                for filename in filenames:
                    if filename.endswith(".swp"):
                        continue
                    if filename.endswith("~"):
                        continue
                    filepath = os.path.join(root, filename)
                    if verbosity > 1:
                        print(filepath)
                    validatingtemplatetags.before_new_template(options.get('force_new_urls', False))
                    try:
                        template_loader.load_template(filename, [root])
                    except Exception as e:
                        errors += 1
                        print("%s: %s" % (filepath, style.ERROR("%s %s" % (e.__class__.__name__, str(e)))))
                    template_errors = validatingtemplatetags.get_template_errors()
                    for origin, line, message in template_errors:
                        errors += 1
                        print("%s(%s): %s" % (origin, line, style.ERROR(message)))
                    if errors and options.get('break', False):
                        raise CommandError("Errors found")

        if errors:
            raise CommandError("%s errors found" % errors)
        print("%s errors found" % errors)


########NEW FILE########
__FILENAME__ = jobs
"""
django_extensions.management.jobs
"""

import os
from imp import find_module

_jobs = None


def noneimplementation(meth):
    return None


class JobError(Exception):
    pass


class BaseJob(object):
    help = "undefined job description."
    when = None

    def execute(self):
        raise NotImplementedError("Job needs to implement the execute method")


class MinutelyJob(BaseJob):
    when = "minutely"


class QuarterHourlyJob(BaseJob):
    when = "quarter_hourly"


class HourlyJob(BaseJob):
    when = "hourly"


class DailyJob(BaseJob):
    when = "daily"


class WeeklyJob(BaseJob):
    when = "weekly"


class MonthlyJob(BaseJob):
    when = "monthly"


class YearlyJob(BaseJob):
    when = "yearly"


def my_import(name):
    try:
        imp = __import__(name)
    except ImportError as err:
        raise JobError("Failed to import %s with error %s" % (name, err))

    mods = name.split('.')
    if len(mods) > 1:
        for mod in mods[1:]:
            imp = getattr(imp, mod)
    return imp


def find_jobs(jobs_dir):
    try:
        return [f[:-3] for f in os.listdir(jobs_dir) if not f.startswith('_') and f.endswith(".py")]
    except OSError:
        return []


def find_job_module(app_name, when=None):
    parts = app_name.split('.')
    parts.append('jobs')
    if when:
        parts.append(when)
    parts.reverse()
    path = None
    while parts:
        part = parts.pop()
        f, path, descr = find_module(part, path and [path] or None)
    return path


def import_job(app_name, name, when=None):
    jobmodule = "%s.jobs.%s%s" % (app_name, when and "%s." % when or "", name)
    job_mod = my_import(jobmodule)
    # todo: more friendly message for AttributeError if job_mod does not exist
    try:
        job = job_mod.Job
    except:
        raise JobError("Job module %s does not contain class instance named 'Job'" % jobmodule)
    if when and not (job.when == when or job.when is None):
        raise JobError("Job %s is not a %s job." % (jobmodule, when))
    return job


def get_jobs(when=None, only_scheduled=False):
    """
    Returns a dictionary mapping of job names together with their respective
    application class.
    """
    # FIXME: HACK: make sure the project dir is on the path when executed as ./manage.py
    import sys
    try:
        cpath = os.path.dirname(os.path.realpath(sys.argv[0]))
        ppath = os.path.dirname(cpath)
        if ppath not in sys.path:
            sys.path.append(ppath)
    except:
        pass
    _jobs = {}
    if True:
        from django.conf import settings
        for app_name in settings.INSTALLED_APPS:
            scandirs = (None, 'minutely', 'quarter_hourly', 'hourly', 'daily', 'weekly', 'monthly', 'yearly')
            if when:
                scandirs = None, when
            for subdir in scandirs:
                try:
                    path = find_job_module(app_name, subdir)
                    for name in find_jobs(path):
                        if (app_name, name) in _jobs:
                            raise JobError("Duplicate job %s" % name)
                        job = import_job(app_name, name, subdir)
                        if only_scheduled and job.when is None:
                            # only include jobs which are scheduled
                            continue
                        if when and job.when != when:
                            # generic job not in same schedule
                            continue
                        _jobs[(app_name, name)] = job
                except ImportError:
                    # No job module -- continue scanning
                    pass
    return _jobs


def get_job(app_name, job_name):
    jobs = get_jobs()
    if app_name:
        return jobs[(app_name, job_name)]
    else:
        for a, j in jobs.keys():
            if j == job_name:
                return jobs[(a, j)]
        raise KeyError("Job not found: %s" % job_name)


def print_jobs(when=None, only_scheduled=False, show_when=True, show_appname=False, show_header=True):
    jobmap = get_jobs(when, only_scheduled=only_scheduled)
    print("Job List: %i jobs" % len(jobmap))
    jlist = jobmap.keys()
    jlist.sort()
    appname_spacer = "%%-%is" % max(len(e[0]) for e in jlist)
    name_spacer = "%%-%is" % max(len(e[1]) for e in jlist)
    when_spacer = "%%-%is" % max(len(e.when) for e in jobmap.values() if e.when)
    if show_header:
        line = " "
        if show_appname:
            line += appname_spacer % "appname" + " - "
        line += name_spacer % "jobname"
        if show_when:
            line += " - " + when_spacer % "when"
        line += " - help"
        print(line)
        print("-" * 80)

    for app_name, job_name in jlist:
        job = jobmap[(app_name, job_name)]
        line = " "
        if show_appname:
            line += appname_spacer % app_name + " - "
        line += name_spacer % job_name
        if show_when:
            line += " - " + when_spacer % (job.when and job.when or "")
        line += " - " + job.help
        print(line)

########NEW FILE########
__FILENAME__ = modelviz
"""
modelviz.py - DOT file generator for Django Models

Based on:
  Django model to DOT (Graphviz) converter
  by Antonio Cavedoni <antonio@cavedoni.org>
  Adapted to be used with django-extensions
"""

__version__ = "1.0"
__license__ = "Python"
__author__ = "Bas van Oostveen <v.oostveen@gmail.com>",
__contributors__ = [
    "Antonio Cavedoni <http://cavedoni.com/>"
    "Stefano J. Attardi <http://attardi.org/>",
    "limodou <http://www.donews.net/limodou/>",
    "Carlo C8E Miron",
    "Andre Campos <cahenan@gmail.com>",
    "Justin Findlay <jfindlay@gmail.com>",
    "Alexander Houben <alexander@houben.ch>",
    "Joern Hees <gitdev@joernhees.de>",
    "Kevin Cherepski <cherepski@gmail.com>",
]

import os
import six
import datetime
from django.utils.translation import activate as activate_language
from django.utils.safestring import mark_safe
from django.template import Context, loader, Template
from django.db import models
from django.db.models import get_models
from django.db.models.fields.related import ForeignKey, OneToOneField, ManyToManyField, RelatedField

try:
    from django.db.models.fields.generic import GenericRelation
    assert GenericRelation
except ImportError:
    from django.contrib.contenttypes.generic import GenericRelation


def parse_file_or_list(arg):
    if not arg:
        return []
    if ',' not in arg and os.path.isfile(arg):
        return [e.strip() for e in open(arg).readlines()]
    return arg.split(',')


def generate_dot(app_labels, **kwargs):
    cli_options = kwargs.get('cli_options', None)
    disable_fields = kwargs.get('disable_fields', False)
    include_models = parse_file_or_list(kwargs.get('include_models', ""))
    all_applications = kwargs.get('all_applications', False)
    use_subgraph = kwargs.get('group_models', False)
    verbose_names = kwargs.get('verbose_names', False)
    inheritance = kwargs.get('inheritance', True)
    relations_as_fields = kwargs.get("relations_as_fields", True)
    sort_fields = kwargs.get("sort_fields", True)
    language = kwargs.get('language', None)
    if language is not None:
        activate_language(language)
    exclude_columns = parse_file_or_list(kwargs.get('exclude_columns', ""))
    exclude_models = parse_file_or_list(kwargs.get('exclude_models', ""))

    def skip_field(field):
        if exclude_columns:
            if verbose_names and field.verbose_name:
                if field.verbose_name in exclude_columns:
                    return True
            if field.name in exclude_columns:
                return True
        return False

    apps = []
    if all_applications:
        apps = models.get_apps()

    for app_label in app_labels:
        app = models.get_app(app_label)
        if app not in apps:
            apps.append(app)

    graphs = []
    for app in apps:
        graph = Context({
            'name': '"%s"' % app.__name__,
            'app_name': "%s" % '.'.join(app.__name__.split('.')[:-1]),
            'cluster_app_name': "cluster_%s" % app.__name__.replace(".", "_"),
            'models': []
        })

        appmodels = get_models(app)
        abstract_models = []
        for appmodel in appmodels:
            abstract_models = abstract_models + [abstract_model for abstract_model in appmodel.__bases__ if hasattr(abstract_model, '_meta') and abstract_model._meta.abstract]
        abstract_models = list(set(abstract_models))  # remove duplicates
        appmodels = abstract_models + appmodels

        for appmodel in appmodels:
            appmodel_abstracts = [abstract_model.__name__ for abstract_model in appmodel.__bases__ if hasattr(abstract_model, '_meta') and abstract_model._meta.abstract]

            # collect all attribs of abstract superclasses
            def getBasesAbstractFields(c):
                _abstract_fields = []
                for e in c.__bases__:
                    if hasattr(e, '_meta') and e._meta.abstract:
                        _abstract_fields.extend(e._meta.fields)
                        _abstract_fields.extend(getBasesAbstractFields(e))
                return _abstract_fields
            abstract_fields = getBasesAbstractFields(appmodel)

            model = {
                'app_name': appmodel.__module__.replace(".", "_"),
                'name': appmodel.__name__,
                'abstracts': appmodel_abstracts,
                'fields': [],
                'relations': []
            }

            # consider given model name ?
            def consider(model_name):
                if exclude_models and model_name in exclude_models:
                    return False
                elif include_models and model_name not in include_models:
                    return False
                return not include_models or model_name in include_models

            if not consider(appmodel._meta.object_name):
                continue

            if verbose_names and appmodel._meta.verbose_name:
                model['label'] = appmodel._meta.verbose_name.decode("utf8")
            else:
                model['label'] = model['name']

            # model attributes
            def add_attributes(field):
                if verbose_names and field.verbose_name:
                    label = field.verbose_name.decode("utf8")
                    if label.islower():
                        label = label.capitalize()
                else:
                    label = field.name

                t = type(field).__name__
                if isinstance(field, (OneToOneField, ForeignKey)):
                    t += " ({0})".format(field.rel.field_name)
                # TODO: ManyToManyField, GenericRelation

                model['fields'].append({
                    'name': field.name,
                    'label': label,
                    'type': t,
                    'blank': field.blank,
                    'abstract': field in abstract_fields,
                    'relation': isinstance(field, RelatedField),
                    'primary_key': field.primary_key,
                })

            attributes = [field for field in appmodel._meta.local_fields]
            if not relations_as_fields:
                # Find all the 'real' attributes. Relations are depicted as graph edges instead of attributes
                attributes = [field for field in attributes if not isinstance(field, RelatedField)]

            # find primary key and print it first, ignoring implicit id if other pk exists
            pk = appmodel._meta.pk
            if pk and not appmodel._meta.abstract and pk in attributes:
                add_attributes(pk)

            for field in attributes:
                if skip_field(field):
                    continue
                if pk and field == pk:
                    continue
                add_attributes(field)

            if sort_fields:
                model['fields'] = sorted(model['fields'], key=lambda field: (not field['primary_key'], not field['relation'], field['label']))

            # FIXME: actually many_to_many fields aren't saved in this model's db table, so why should we add an attribute-line for them in the resulting graph?
            #if appmodel._meta.many_to_many:
            #    for field in appmodel._meta.many_to_many:
            #        if skip_field(field):
            #            continue
            #        add_attributes(field)

            # relations
            def add_relation(field, extras=""):
                if verbose_names and field.verbose_name:
                    label = field.verbose_name.decode("utf8")
                    if label.islower():
                        label = label.capitalize()
                else:
                    label = field.name

                # show related field name
                if hasattr(field, 'related_query_name'):
                    related_query_name = field.related_query_name()
                    if verbose_names and related_query_name.islower():
                        related_query_name = related_query_name.replace('_', ' ').capitalize()
                    label += ' (%s)' % related_query_name

                # handle self-relationships and lazy-relationships
                if isinstance(field.rel.to, six.string_types):
                    if field.rel.to == 'self':
                        target_model = field.model
                    else:
                        raise Exception("Lazy relationship for model (%s) must be explicit for field (%s)" % (field.model.__name__, field.name))
                else:
                    target_model = field.rel.to

                _rel = {
                    'target_app': target_model.__module__.replace('.', '_'),
                    'target': target_model.__name__,
                    'type': type(field).__name__,
                    'name': field.name,
                    'label': label,
                    'arrows': extras,
                    'needs_node': True
                }
                if _rel not in model['relations'] and consider(_rel['target']):
                    model['relations'].append(_rel)

            for field in appmodel._meta.local_fields:
                if field.attname.endswith('_ptr_id'):  # excluding field redundant with inheritance relation
                    continue
                if field in abstract_fields:  # excluding fields inherited from abstract classes. they too show as local_fields
                    continue
                if skip_field(field):
                    continue
                if isinstance(field, OneToOneField):
                    add_relation(field, '[arrowhead=none, arrowtail=none, dir=both]')
                elif isinstance(field, ForeignKey):
                    add_relation(field, '[arrowhead=none, arrowtail=dot, dir=both]')

            for field in appmodel._meta.local_many_to_many:
                if skip_field(field):
                    continue
                if isinstance(field, ManyToManyField):
                    if (getattr(field, 'creates_table', False) or  # django 1.1.
                            (hasattr(field.rel.through, '_meta') and field.rel.through._meta.auto_created)):  # django 1.2
                        add_relation(field, '[arrowhead=dot arrowtail=dot, dir=both]')
                elif isinstance(field, GenericRelation):
                    add_relation(field, mark_safe('[style="dotted", arrowhead=normal, arrowtail=normal, dir=both]'))

            if inheritance:
                # add inheritance arrows
                for parent in appmodel.__bases__:
                    if hasattr(parent, "_meta"):  # parent is a model
                        l = "multi-table"
                        if parent._meta.abstract:
                            l = "abstract"
                        if appmodel._meta.proxy:
                            l = "proxy"
                        l += r"\ninheritance"
                        _rel = {
                            'target_app': parent.__module__.replace(".", "_"),
                            'target': parent.__name__,
                            'type': "inheritance",
                            'name': "inheritance",
                            'label': l,
                            'arrows': '[arrowhead=empty, arrowtail=none, dir=both]',
                            'needs_node': True,
                        }
                        # TODO: seems as if abstract models aren't part of models.getModels, which is why they are printed by this without any attributes.
                        if _rel not in model['relations'] and consider(_rel['target']):
                            model['relations'].append(_rel)

            graph['models'].append(model)
        if graph['models']:
            graphs.append(graph)

    nodes = []
    for graph in graphs:
        nodes.extend([e['name'] for e in graph['models']])

    for graph in graphs:
        for model in graph['models']:
            for relation in model['relations']:
                if relation['target'] in nodes:
                    relation['needs_node'] = False

    now = datetime.datetime.now()
    t = loader.get_template('django_extensions/graph_models/digraph.dot')

    if not isinstance(t, Template):
        raise Exception("Default Django template loader isn't used. "
                        "This can lead to the incorrect template rendering. "
                        "Please, check the settings.")

    c = Context({
        'created_at': now.strftime("%Y-%m-%d %H:%M"),
        'cli_options': cli_options,
        'disable_fields': disable_fields,
        'use_subgraph': use_subgraph,
        'graphs': graphs,
    })
    dot = t.render(c)

    return dot

########NEW FILE########
__FILENAME__ = notebook_extension
def load_ipython_extension(ipython):
    from django.core.management.color import no_style
    from django_extensions.management.shells import import_objects
    imported_objects = import_objects(options={'dont_load': []},
                                      style=no_style())
    ipython.push(imported_objects)

########NEW FILE########
__FILENAME__ = shells
import six
import traceback


class ObjectImportError(Exception):
    pass


def import_items(import_directives, style, quiet_load=False):
    """
    Import the items in import_directives and return a list of the imported items

    Each item in import_directives should be one of the following forms
        * a tuple like ('module.submodule', ('classname1', 'classname2')), which indicates a 'from module.submodule import classname1, classname2'
        * a tuple like ('module.submodule', 'classname1'), which indicates a 'from module.submodule import classname1'
        * a tuple like ('module.submodule', '*'), which indicates a 'from module.submodule import *'
        * a simple 'module.submodule' which indicates 'import module.submodule'.

    Returns a dict mapping the names to the imported items
    """
    imported_objects = {}
    for directive in import_directives:
        try:
            # First try a straight import
            if isinstance(directive, six.string_types):
                imported_object = __import__(directive)
                imported_objects[directive.split('.')[0]] = imported_object
                if not quiet_load:
                    print(style.SQL_COLTYPE("import %s" % directive))
                continue
            elif isinstance(directive, (list, tuple)) and len(directive) == 2:
                if not isinstance(directive[0], six.string_types):
                    if not quiet_load:
                        print(style.ERROR("Unable to import %r: module name must be of type string" % directive[0]))
                    continue
                if isinstance(directive[1], (list, tuple)) and all(isinstance(e, six.string_types) for e in directive[1]):
                    # Try the ('module.submodule', ('classname1', 'classname2')) form
                    imported_object = __import__(directive[0], {}, {}, directive[1])
                    imported_names = []
                    for name in directive[1]:
                        try:
                            imported_objects[name] = getattr(imported_object, name)
                        except AttributeError:
                            if not quiet_load:
                                print(style.ERROR("Unable to import %r from %r: %r does not exist" % (name, directive[0], name)))
                        else:
                            imported_names.append(name)
                    if not quiet_load:
                        print(style.SQL_COLTYPE("from %s import %s" % (directive[0], ', '.join(imported_names))))
                elif isinstance(directive[1], six.string_types):
                    # If it is a tuple, but the second item isn't a list, so we have something like ('module.submodule', 'classname1')
                    # Check for the special '*' to import all
                    if directive[1] == '*':
                        imported_object = __import__(directive[0], {}, {}, directive[1])
                        for k in dir(imported_object):
                            imported_objects[k] = getattr(imported_object, k)
                        if not quiet_load:
                            print(style.SQL_COLTYPE("from %s import *" % directive[0]))
                    else:
                        imported_object = getattr(__import__(directive[0], {}, {}, [directive[1]]), directive[1])
                        imported_objects[directive[1]] = imported_object
                        if not quiet_load:
                            print(style.SQL_COLTYPE("from %s import %s" % (directive[0], directive[1])))
                else:
                    if not quiet_load:
                        print(style.ERROR("Unable to import %r from %r: names must be of type string" % (directive[1], directive[0])))
            else:
                if not quiet_load:
                    print(style.ERROR("Unable to import %r: names must be of type string" % directive))
        except ImportError:
            try:
                if not quiet_load:
                    print(style.ERROR("Unable to import %r" % directive))
            except TypeError:
                if not quiet_load:
                    print(style.ERROR("Unable to import %r from %r" % directive))

    return imported_objects


def import_objects(options, style):
    # XXX: (Temporary) workaround for ticket #1796: force early loading of all
    # models from installed apps. (this is fixed by now, but leaving it here
    # for people using 0.96 or older trunk (pre [5919]) versions.
    from django.db.models.loading import get_models, get_apps
    mongoengine = False
    try:
        from mongoengine.base import _document_registry
        mongoengine = True
    except:
        pass

    loaded_models = get_models()  # NOQA

    from django.conf import settings
    imported_objects = {}

    dont_load_cli = options.get('dont_load')  # optparse will set this to [] if it doensnt exists
    dont_load_conf = getattr(settings, 'SHELL_PLUS_DONT_LOAD', [])
    dont_load = dont_load_cli + dont_load_conf
    quiet_load = options.get('quiet_load')

    model_aliases = getattr(settings, 'SHELL_PLUS_MODEL_ALIASES', {})

    # Perform pre-imports before any other imports
    SHELL_PLUS_PRE_IMPORTS = getattr(settings, '', {})
    if SHELL_PLUS_PRE_IMPORTS:
        if not quiet_load:
            print(style.SQL_TABLE("# Shell Plus User Imports"))
        imports = import_items(SHELL_PLUS_PRE_IMPORTS, style, quiet_load=quiet_load)
        for k, v in six.iteritems(imports):
            imported_objects[k] = v

    load_models = {}

    if mongoengine:
        for name, mod in six.iteritems(_document_registry):
            name = name.split('.')[-1]
            app_name = mod.__module__.split('.')[-2]
            if app_name in dont_load or ("%s.%s" % (app_name, name)) in dont_load:
                continue

            load_models.setdefault(mod.__module__, [])
            load_models[mod.__module__].append(name)

    for app_mod in get_apps():
        app_models = get_models(app_mod)
        if not app_models:
            continue

        app_name = app_mod.__name__.split('.')[-2]
        if app_name in dont_load:
            continue

        app_aliases = model_aliases.get(app_name, {})
        for mod in app_models:
            if "%s.%s" % (app_name, mod.__name__) in dont_load:
                continue

            load_models.setdefault(mod.__module__, [])
            load_models[mod.__module__].append(mod.__name__)

    if not quiet_load:
        print(style.SQL_TABLE("# Shell Plus Model Imports"))
    for app_mod, models in sorted(six.iteritems(load_models)):
        app_name = app_mod.split('.')[-2]
        app_aliases = model_aliases.get(app_name, {})
        model_labels = []

        for model_name in sorted(models):
            try:
                imported_object = getattr(__import__(app_mod, {}, {}, [model_name]), model_name)

                if "%s.%s" % (app_name, model_name) in dont_load:
                    continue

                alias = app_aliases.get(model_name, model_name)
                imported_objects[alias] = imported_object
                if model_name == alias:
                    model_labels.append(model_name)
                else:
                    model_labels.append("%s (as %s)" % (model_name, alias))

            except AttributeError as e:
                if options.get("traceback"):
                    traceback.print_exc()
                if not quiet_load:
                    print(style.ERROR("Failed to import '%s' from '%s' reason: %s" % (model_name, app_mod, str(e))))
                continue

        if not quiet_load:
            print(style.SQL_COLTYPE("from %s import %s" % (app_mod, ", ".join(model_labels))))

    # Imports often used from Django
    if getattr(settings, 'SHELL_PLUS_DJANGO_IMPORTS', True):
        if not quiet_load:
            print(style.SQL_TABLE("# Shell Plus Django Imports"))
        SHELL_PLUS_DJANGO_IMPORTS = (
            ('django.core.cache', ['cache']),
            ('django.core.urlresolvers', ['reverse']),
            ('django.conf', ['settings']),
            ('django.db', ['transaction']),
            ('django.db.models', ['Avg', 'Count', 'F', 'Max', 'Min', 'Sum', 'Q']),
            ('django.utils', ['timezone']),
        )
        imports = import_items(SHELL_PLUS_DJANGO_IMPORTS, style, quiet_load=quiet_load)
        for k, v in six.iteritems(imports):
            imported_objects[k] = v

    # Perform post-imports after any other imports
    SHELL_PLUS_POST_IMPORTS = getattr(settings, 'SHELL_PLUS_POST_IMPORTS', {})
    if SHELL_PLUS_POST_IMPORTS:
        if not quiet_load:
            print(style.SQL_TABLE("# Shell Plus User Imports"))
        imports = import_items(SHELL_PLUS_POST_IMPORTS, style, quiet_load=quiet_load)
        for k, v in six.iteritems(imports):
            imported_objects[k] = v

    return imported_objects

########NEW FILE########
__FILENAME__ = signals
"""
signals we use to trigger regular batch jobs
"""
from django.dispatch import Signal

run_minutely_jobs = Signal()
run_quarter_hourly_jobs = Signal()
run_hourly_jobs = Signal()
run_daily_jobs = Signal()
run_weekly_jobs = Signal()
run_monthly_jobs = Signal()
run_yearly_jobs = Signal()

########NEW FILE########
__FILENAME__ = technical_response
import six


def null_technical_500_response(request, exc_type, exc_value, tb):
    six.reraise(exc_type, exc_value, tb)


########NEW FILE########
__FILENAME__ = utils
from django.conf import settings
import os
import sys
import logging

try:
    from importlib import import_module
except ImportError:
    try:
        from django.utils.importlib import import_module
    except ImportError:
        def import_module(module):
            return __import__(module, {}, {}, [''])


def get_project_root():
    """ get the project root directory """
    django_settings_module = os.environ.get('DJANGO_SETTINGS_MODULE')
    if not django_settings_module:
        module_str = settings.SETTINGS_MODULE
    else:
        module_str = django_settings_module.split(".")[0]
    mod = import_module(module_str)
    return os.path.dirname(os.path.abspath(mod.__file__))


def _make_writeable(filename):
    """
    Make sure that the file is writeable. Useful if our source is
    read-only.

    """
    import stat
    if sys.platform.startswith('java'):
        # On Jython there is no os.access()
        return
    if not os.access(filename, os.W_OK):
        st = os.stat(filename)
        new_permissions = stat.S_IMODE(st.st_mode) | stat.S_IWUSR
        os.chmod(filename, new_permissions)


def setup_logger(logger, stream, filename=None, fmt=None):
    """Sets up a logger (if no handlers exist) for console output,
    and file 'tee' output if desired."""
    if len(logger.handlers) < 1:
        console = logging.StreamHandler(stream)
        console.setLevel(logging.DEBUG)
        console.setFormatter(logging.Formatter(fmt))
        logger.addHandler(console)
        logger.setLevel(logging.DEBUG)

        if filename:
            outfile = logging.FileHandler(filename)
            outfile.setLevel(logging.INFO)
            outfile.setFormatter(logging.Formatter("%(asctime)s " + (fmt if fmt else '%(message)s')))
            logger.addHandler(outfile)


class RedirectHandler(logging.Handler):
    """Redirect logging sent to one logger (name) to another."""
    def __init__(self, name, level=logging.DEBUG):
        # Contemplate feasibility of copying a destination (allow original handler) and redirecting.
        logging.Handler.__init__(self, level)
        self.name = name
        self.logger = logging.getLogger(name)

    def emit(self, record):
        self.logger.handle(record)

########NEW FILE########
__FILENAME__ = 0001_empty
# -*- coding: utf-8 -*-
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        pass

    def backwards(self, orm):
        pass

    models = {

    }

    complete_apps = ['django_extensions']

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = encrypted
"""
Encrypted fields from Django Extensions, modified for use with mongoDB
"""
from mongoengine.base import BaseField
from django.core.exceptions import ImproperlyConfigured
from django import forms
from django.conf import settings

try:
    from keyczar import keyczar
except ImportError:
    raise ImportError('Using an encrypted field requires the Keyczar module.  You can obtain Keyczar from http://www.keyczar.org/.')


class BaseEncryptedField(BaseField):
    prefix = 'enc_str:::'

    def __init__(self, *args, **kwargs):
        if not hasattr(settings, 'ENCRYPTED_FIELD_KEYS_DIR'):
            raise ImproperlyConfigured('You must set settings.ENCRYPTED_FIELD_KEYS_DIR to your Keyczar keys directory.')
        self.crypt = keyczar.Crypter.Read(settings.ENCRYPTED_FIELD_KEYS_DIR)
        super(BaseEncryptedField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if (value.startswith(self.prefix)):
            retval = self.crypt.Decrypt(value[len(self.prefix):])
        else:
            retval = value

        return retval

    def get_db_prep_value(self, value):
        if not value.startswith(self.prefix):
            value = self.prefix + self.crypt.Encrypt(value)
        return value


class EncryptedTextField(BaseEncryptedField):
    def get_internal_type(self):
        return 'StringField'

    def formfield(self, **kwargs):
        defaults = {'widget': forms.Textarea}
        defaults.update(kwargs)
        return super(EncryptedTextField, self).formfield(**defaults)


class EncryptedCharField(BaseEncryptedField):
    def __init__(self, max_length=None, *args, **kwargs):
        if max_length:
            max_length += len(self.prefix)

        super(EncryptedCharField, self).__init__(max_length=max_length, *args, **kwargs)

    def get_internal_type(self):
        return "StringField"

    def formfield(self, **kwargs):
        defaults = {'max_length': self.max_length}
        defaults.update(kwargs)
        return super(EncryptedCharField, self).formfield(**defaults)

########NEW FILE########
__FILENAME__ = json
"""
JSONField automatically serializes most Python terms to JSON data.
Creates a TEXT field with a default value of "{}".  See test_json.py for
more information.

 from django.db import models
 from django_extensions.db.fields import json

 class LOL(models.Model):
     extra = json.JSONField()
"""

import six
import datetime
from decimal import Decimal
from django.conf import settings
from django.utils import simplejson
from mongoengine.fields import StringField


class JSONEncoder(simplejson.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        elif isinstance(obj, datetime.datetime):
            assert settings.TIME_ZONE == 'UTC'
            return obj.strftime('%Y-%m-%dT%H:%M:%SZ')
        return simplejson.JSONEncoder.default(self, obj)


def dumps(value):
    assert isinstance(value, dict)
    return JSONEncoder().encode(value)


def loads(txt):
    value = simplejson.loads(txt, parse_float=Decimal, encoding=settings.DEFAULT_CHARSET)
    assert isinstance(value, dict)
    return value


class JSONDict(dict):
    """
    Hack so repr() called by dumpdata will output JSON instead of
    Python formatted data.  This way fixtures will work!
    """
    def __repr__(self):
        return dumps(self)


class JSONField(StringField):
    """JSONField is a generic textfield that neatly serializes/unserializes
    JSON objects seamlessly.  Main thingy must be a dict object."""

    def __init__(self, *args, **kwargs):
        if 'default' not in kwargs:
            kwargs['default'] = '{}'
        StringField.__init__(self, *args, **kwargs)

    def to_python(self, value):
        """Convert our string value to JSON after we load it from the DB"""
        if not value:
            return {}
        elif isinstance(value, six.string_types):
            res = loads(value)
            assert isinstance(res, dict)
            return JSONDict(**res)
        else:
            return value

    def get_db_prep_save(self, value):
        """Convert our JSON object to a string before we save"""
        if not value:
            return super(JSONField, self).get_db_prep_save("")
        else:
            return super(JSONField, self).get_db_prep_save(dumps(value))


########NEW FILE########
__FILENAME__ = models
"""
Django Extensions abstract base mongoengine Document classes.
"""
import datetime
from mongoengine.document import Document
from mongoengine.fields import StringField, IntField, DateTimeField
from mongoengine.queryset import QuerySetManager
from django.utils.translation import ugettext_lazy as _
from django_extensions.mongodb.fields import ModificationDateTimeField, CreationDateTimeField, AutoSlugField


class TimeStampedModel(Document):
    """ TimeStampedModel
    An abstract base class model that provides self-managed "created" and
    "modified" fields.
    """
    created = CreationDateTimeField(_('created'))
    modified = ModificationDateTimeField(_('modified'))

    class Meta:
        abstract = True


class TitleSlugDescriptionModel(Document):
    """ TitleSlugDescriptionModel
    An abstract base class model that provides title and description fields
    and a self-managed "slug" field that populates from the title.
    """
    title = StringField(_('title'), max_length=255)
    slug = AutoSlugField(_('slug'), populate_from='title')
    description = StringField(_('description'), blank=True, null=True)

    class Meta:
        abstract = True


class ActivatorModelManager(QuerySetManager):
    """ ActivatorModelManager
    Manager to return instances of ActivatorModel: SomeModel.objects.active() / .inactive()
    """
    def active(self):
        """ Returns active instances of ActivatorModel: SomeModel.objects.active() """
        return super(ActivatorModelManager, self).get_query_set().filter(status=1)

    def inactive(self):
        """ Returns inactive instances of ActivatorModel: SomeModel.objects.inactive() """
        return super(ActivatorModelManager, self).get_query_set().filter(status=0)


class ActivatorModel(Document):
    """ ActivatorModel
    An abstract base class model that provides activate and deactivate fields.
    """
    STATUS_CHOICES = (
        (0, _('Inactive')),
        (1, _('Active')),
    )
    status = IntField(_('status'), choices=STATUS_CHOICES, default=1)
    activate_date = DateTimeField(blank=True, null=True, help_text=_('keep empty for an immediate activation'))
    deactivate_date = DateTimeField(blank=True, null=True, help_text=_('keep empty for indefinite activation'))
    objects = ActivatorModelManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.activate_date:
            self.activate_date = datetime.datetime.now()
        super(ActivatorModel, self).save(*args, **kwargs)

########NEW FILE########
__FILENAME__ = settings
import os
from django.conf import settings

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
REPLACEMENTS = {
}
add_replacements = getattr(settings, 'EXTENSIONS_REPLACEMENTS', {})
REPLACEMENTS.update(add_replacements)

########NEW FILE########
__FILENAME__ = highlighting
"""
Similar to syntax_color.py but this is intended more for being able to
copy+paste actual code into your Django templates without needing to
escape or anything crazy.

http://lobstertech.com/2008/aug/30/django_syntax_highlight_template_tag/

Example:

 {% load highlighting %}

 <style>
 @import url("http://lobstertech.com/media/css/highlight.css");
 .highlight { background: #f8f8f8; }
 .highlight { font-size: 11px; margin: 1em; border: 1px solid #ccc;
              border-left: 3px solid #F90; padding: 0; }
 .highlight pre { padding: 1em; overflow: auto; line-height: 120%; margin: 0; }
 .predesc { margin: 1.5em 1.5em -2.5em 1em; text-align: right;
            font: bold 12px Tahoma, Arial, sans-serif;
            letter-spacing: 1px; color: #333; }
 </style>

 <h2>check out this code</h2>

 {% highlight 'python' 'Excerpt: blah.py' %}
 def need_food(self):
     print("Love is <colder> than &death&")
 {% endhighlight %}

"""

from pygments import highlight as pyghighlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from django import template
from django.template import Template, Context, Node, Variable, TemplateSyntaxError
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
@stringfilter
def parse_template(value):
    return mark_safe(Template(value).render(Context()))
parse_template.is_safe = True


class CodeNode(Node):
    def __init__(self, language, nodelist, name=''):
        self.language = Variable(language)
        self.nodelist = nodelist
        if name:
            self.name = Variable(name)
        else:
            self.name = None

    def render(self, context):
        code = self.nodelist.render(context).strip()
        lexer = get_lexer_by_name(self.language.resolve(context))
        formatter = HtmlFormatter(linenos=False)
        html = ""
        if self.name:
            name = self.name.resolve(context)
            html = '<div class="predesc"><span>%s</span></div>' % (name)
        return html + pyghighlight(code, lexer, formatter)


@register.tag
def highlight(parser, token):
    """
    Allows you to put a highlighted source code <pre> block in your code.
    This takes two arguments, the language and a little explaination message
    that will be generated before the code.  The second argument is optional.

    Your code will be fed through pygments so you can use any language it
    supports.

    {% load highlighting %}
    {% highlight 'python' 'Excerpt: blah.py' %}
    def need_food(self):
        print("Love is colder than death")
    {% endhighlight %}
    """
    nodelist = parser.parse(('endhighlight',))
    parser.delete_first_token()
    bits = token.split_contents()[1:]
    if len(bits) < 1:
        raise TemplateSyntaxError("'highlight' statement requires an argument")
    return CodeNode(bits[0], nodelist, *bits[1:])

########NEW FILE########
__FILENAME__ = indent_text
from django import template

register = template.Library()


class IndentByNode(template.Node):
    def __init__(self, nodelist, indent_level, if_statement):
        self.nodelist = nodelist
        self.indent_level = template.Variable(indent_level)
        if if_statement:
            self.if_statement = template.Variable(if_statement)
        else:
            self.if_statement = None

    def render(self, context):
        indent_level = self.indent_level.resolve(context)
        if self.if_statement:
            try:
                if_statement = bool(self.if_statement.resolve(context))
            except template.VariableDoesNotExist:
                if_statement = False
        else:
            if_statement = True
        output = self.nodelist.render(context)
        if if_statement:
            indent = " " * indent_level
            output = indent + indent.join(output.splitlines(True))
        return output


def indentby(parser, token):
    """
    Adds indentation to text between the tags by the given indentation level.

    {% indentby <indent_level> [if <statement>] %}
    ...
    {% endindentby %}

    Arguments:
      indent_level - Number of spaces to indent text with.
      statement - Only apply indent_level if the boolean statement evalutates to True.
    """
    args = token.split_contents()
    largs = len(args)
    if largs not in (2, 4):
        raise template.TemplateSyntaxError("%r tag requires 1 or 3 arguments")
    indent_level = args[1]
    if_statement = None
    if largs == 4:
        if_statement = args[3]
    nodelist = parser.parse(('endindentby', ))
    parser.delete_first_token()
    return IndentByNode(nodelist, indent_level, if_statement)

indentby = register.tag(indentby)

########NEW FILE########
__FILENAME__ = syntax_color
r"""
Template filter for rendering a string with syntax highlighting.
It relies on Pygments to accomplish this.

Some standard usage examples (from within Django templates).
Coloring a string with the Python lexer:

    {% load syntax_color %}
    {{ code_string|colorize:"python" }}

You may use any lexer in Pygments. The complete list of which
can be found [on the Pygments website][1].

[1]: http://pygments.org/docs/lexers/

You may also have Pygments attempt to guess the correct lexer for
a particular string. However, if may not be able to choose a lexer,
in which case it will simply return the string unmodified. This is
less efficient compared to specifying the lexer to use.

    {{ code_string|colorize }}

You may also render the syntax highlighed text with line numbers.

    {% load syntax_color %}
    {{ some_code|colorize_table:"html+django" }}
    {{ let_pygments_pick_for_this_code|colorize_table }}

Please note that before you can load the ``syntax_color`` template filters
you will need to add the ``django_extensions.utils`` application to the
``INSTALLED_APPS``setting in your project's ``settings.py`` file.
"""

__author__ = 'Will Larson <lethain@gmail.com>'


from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from django.core.exceptions import ImproperlyConfigured

try:
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import get_lexer_by_name, guess_lexer, ClassNotFound
except ImportError:
    raise ImproperlyConfigured(
        "Please install 'pygments' library to use syntax_color.")

register = template.Library()


@register.simple_tag
def pygments_css():
    return HtmlFormatter().get_style_defs('.highlight')


def generate_pygments_css(path=None):
    if path is None:
        import os
        path = os.path.join(os.getcwd(), 'pygments.css')
    f = open(path, 'w')
    f.write(pygments_css())
    f.close()


def get_lexer(value, arg):
    if arg is None:
        return guess_lexer(value)
    return get_lexer_by_name(arg)


@register.filter(name='colorize')
@stringfilter
def colorize(value, arg=None):
    try:
        return mark_safe(highlight(value, get_lexer(value, arg), HtmlFormatter()))
    except ClassNotFound:
        return value


@register.filter(name='colorize_table')
@stringfilter
def colorize_table(value, arg=None):
    try:
        return mark_safe(highlight(value, get_lexer(value, arg), HtmlFormatter(linenos='table')))
    except ClassNotFound:
        return value


@register.filter(name='colorize_noclasses')
@stringfilter
def colorize_noclasses(value, arg=None):
    try:
        return mark_safe(highlight(value, get_lexer(value, arg), HtmlFormatter(noclasses=True)))
    except ClassNotFound:
        return value

########NEW FILE########
__FILENAME__ = truncate_letters
import django
from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


def truncateletters(value, arg):
    """
    Truncates a string after a certain number of letters

    Argument: Number of letters to truncate after
    """
    from django_extensions.utils.text import truncate_letters
    try:
        length = int(arg)
    except ValueError:  # invalid literal for int()
        return value  # Fail silently
    return truncate_letters(value, length)

if django.get_version() >= "1.4":
    truncateletters = stringfilter(truncateletters)
    register.filter(truncateletters, is_safe=True)
else:
    truncateletters.is_safe = True
    truncateletters = stringfilter(truncateletters)
    register.filter(truncateletters)


########NEW FILE########
__FILENAME__ = widont
import re
from django.template import Library
try:
    from django.utils.encoding import force_text
except ImportError:
    # Django 1.4 compatibility
    from django.utils.encoding import force_unicode as force_text

register = Library()
re_widont = re.compile(r'\s+(\S+\s*)$')
re_widont_html = re.compile(r'([^<>\s])\s+([^<>\s]+\s*)(</?(?:address|blockquote|br|dd|div|dt|fieldset|form|h[1-6]|li|noscript|p|td|th)[^>]*>|$)', re.IGNORECASE)


def widont(value, count=1):
    """
    Adds an HTML non-breaking space between the final two words of the string to
    avoid "widowed" words.

    Examples:

    >>> print(widont('Test   me   out'))
    Test   me&nbsp;out

    >>> widont('It works with trailing spaces too  ')
    u'It works with trailing spaces&nbsp;too  '

    >>> print(widont('NoEffect'))
    NoEffect
    """
    def replace(matchobj):
        return force_text('&nbsp;%s' % matchobj.group(1))
    for i in range(count):
        value = re_widont.sub(replace, force_text(value))
    return value


def widont_html(value):
    """
    Adds an HTML non-breaking space between the final two words at the end of
    (and in sentences just outside of) block level tags to avoid "widowed"
    words.

    Examples:

    >>> print(widont_html('<h2>Here is a simple  example  </h2> <p>Single</p>'))
    <h2>Here is a simple&nbsp;example  </h2> <p>Single</p>

    >>> print(widont_html('<p>test me<br /> out</p><h2>Ok?</h2>Not in a p<p title="test me">and this</p>'))
    <p>test&nbsp;me<br /> out</p><h2>Ok?</h2>Not in a&nbsp;p<p title="test me">and&nbsp;this</p>

    >>> print(widont_html('leading text  <p>test me out</p>  trailing text'))
    leading&nbsp;text  <p>test me&nbsp;out</p>  trailing&nbsp;text
    """
    def replace(matchobj):
        return force_text('%s&nbsp;%s%s' % matchobj.groups())
    return re_widont_html.sub(replace, force_text(value))

register.filter(widont)
register.filter(widont_html)

if __name__ == "__main__":
    def _test():
        import doctest
        doctest.testmod()
    _test()

########NEW FILE########
__FILENAME__ = encrypted_fields
from contextlib import contextmanager
import functools

from django.conf import settings
from django.db import connection, models
from django.db.models import loading

from django_extensions.tests.models import Secret
from django_extensions.tests.fields import FieldTestCase

# Only perform encrypted fields tests if keyczar is present. Resolves
# http://github.com/django-extensions/django-extensions/issues/#issue/17
try:
    from django_extensions.db.fields.encrypted import EncryptedTextField, EncryptedCharField  # NOQA
    from keyczar import keyczar, keyczart, keyinfo  # NOQA
    keyczar_active = True
except ImportError:
    keyczar_active = False


def run_if_active(func):
    "Method decorator that only runs a test if KeyCzar is available."

    @functools.wraps(func)
    def inner(self):
        if not keyczar_active:
            return
        return func(self)
    return inner


# Locations of both private and public keys.
KEY_LOCS = getattr(settings, 'ENCRYPTED_FIELD_KEYS_DIR', {})


@contextmanager
def keys(purpose, mode=None):
    """
    A context manager that sets up the correct KeyCzar environment for a test.

    Arguments:
        purpose: Either keyczar.keyinfo.DECRYPT_AND_ENCRYPT or
                 keyczar.keyinfo.ENCRYPT.
        mode: If truthy, settings.ENCRYPTED_FIELD_MODE will be set to (and then
              reverted from) this value. If falsy, settings.ENCRYPTED_FIELD_MODE
              will not be changed. Optional. Default: None.

    Yields:
        A Keyczar subclass for the stated purpose. This will be keyczar.Crypter
        for DECRYPT_AND_ENCRYPT or keyczar.Encrypter for ENCRYPT. In addition,
        settings.ENCRYPTED_FIELD_KEYS_DIR will be set correctly, and then
        reverted when the manager exits.
    """
    # Store the original settings so we can restore when the manager exits.
    orig_setting_dir = getattr(settings, 'ENCRYPTED_FIELD_KEYS_DIR', None)
    orig_setting_mode = getattr(settings, 'ENCRYPTED_FIELD_MODE', None)
    try:
        if mode:
            settings.ENCRYPTED_FIELD_MODE = mode

        if purpose == keyinfo.DECRYPT_AND_ENCRYPT:
            settings.ENCRYPTED_FIELD_KEYS_DIR = KEY_LOCS['DECRYPT_AND_ENCRYPT']
            yield keyczar.Crypter.Read(settings.ENCRYPTED_FIELD_KEYS_DIR)
        else:
            settings.ENCRYPTED_FIELD_KEYS_DIR = KEY_LOCS['ENCRYPT']
            yield keyczar.Encrypter.Read(settings.ENCRYPTED_FIELD_KEYS_DIR)

    except:
        raise  # Reraise any exceptions.

    finally:
        # Restore settings.
        settings.ENCRYPTED_FIELD_KEYS_DIR = orig_setting_dir
        if mode:
            if orig_setting_mode:
                settings.ENCRYPTED_FIELD_MODE = orig_setting_mode
            else:
                del settings.ENCRYPTED_FIELD_MODE


@contextmanager
def secret_model():
    """
    A context manager that yields a Secret model defined at runtime.

    All EncryptedField init logic occurs at model class definition time, not at
    object instantiation time. This means that in order to test different keys
    and modes, we must generate a new class definition at runtime, after
    establishing the correct KeyCzar settings. This context manager handles
    that process.

    See http://dynamic-models.readthedocs.org/en/latest/ and
    https://docs.djangoproject.com/en/dev/topics/db/models/
        #differences-between-proxy-inheritance-and-unmanaged-models
    """

    # Store Django's cached model, if present, so we can restore when the
    # manager exits.
    orig_model = None
    try:
        orig_model = loading.cache.app_models['tests']['secret']
        del loading.cache.app_models['tests']['secret']
    except KeyError:
        pass

    try:
        # Create a new class that shadows tests.models.Secret.
        attrs = {
            'name': EncryptedCharField("Name", max_length=Secret._meta.get_field('name').max_length),
            'text': EncryptedTextField("Text"),
            '__module__': 'django_extensions.tests.models',
            'Meta': type('Meta', (object, ), {
                'managed': False,
                'db_table': Secret._meta.db_table
            })
        }
        yield type('Secret', (models.Model, ), attrs)

    except:
        raise  # Reraise any exceptions.

    finally:
        # Restore Django's model cache.
        try:
            loading.cache.app_models['tests']['secret'] = orig_model
        except KeyError:
            pass


class EncryptedFieldsTestCase(FieldTestCase):
    @run_if_active
    def testCharFieldCreate(self):
        """
        Uses a private key to encrypt data on model creation.
        Verifies the data is encrypted in the database and can be decrypted.
        """
        with keys(keyinfo.DECRYPT_AND_ENCRYPT) as crypt:
            with secret_model() as model:
                test_val = "Test Secret"
                secret = model.objects.create(name=test_val)

                cursor = connection.cursor()
                query = "SELECT name FROM %s WHERE id = %d" % (model._meta.db_table, secret.id)
                cursor.execute(query)
                db_val, = cursor.fetchone()
                decrypted_val = crypt.Decrypt(db_val[len(EncryptedCharField.prefix):])
                self.assertEqual(test_val, decrypted_val)

    @run_if_active
    def testCharFieldRead(self):
        """
        Uses a private key to encrypt data on model creation.
        Verifies the data is decrypted when reading the value back from the
        model.
        """
        with keys(keyinfo.DECRYPT_AND_ENCRYPT):
            with secret_model() as model:
                test_val = "Test Secret"
                secret = model.objects.create(name=test_val)
                retrieved_secret = model.objects.get(id=secret.id)
                self.assertEqual(test_val, retrieved_secret.name)

    @run_if_active
    def testTextFieldCreate(self):
        """
        Uses a private key to encrypt data on model creation.
        Verifies the data is encrypted in the database and can be decrypted.
        """
        with keys(keyinfo.DECRYPT_AND_ENCRYPT) as crypt:
            with secret_model() as model:
                test_val = "Test Secret"
                secret = model.objects.create(text=test_val)
                cursor = connection.cursor()
                query = "SELECT text FROM %s WHERE id = %d" % (model._meta.db_table, secret.id)
                cursor.execute(query)
                db_val, = cursor.fetchone()
                decrypted_val = crypt.Decrypt(db_val[len(EncryptedCharField.prefix):])
                self.assertEqual(test_val, decrypted_val)

    @run_if_active
    def testTextFieldRead(self):
        """
        Uses a private key to encrypt data on model creation.
        Verifies the data is decrypted when reading the value back from the
        model.
        """
        with keys(keyinfo.DECRYPT_AND_ENCRYPT):
            with secret_model() as model:
                test_val = "Test Secret"
                secret = model.objects.create(text=test_val)
                retrieved_secret = model.objects.get(id=secret.id)
                self.assertEqual(test_val, retrieved_secret.text)

    @run_if_active
    def testCannotDecrypt(self):
        """
        Uses a public key to encrypt data on model creation.
        Verifies that the data cannot be decrypted using the same key.
        """
        with keys(keyinfo.ENCRYPT, mode=keyinfo.ENCRYPT.name):
            with secret_model() as model:
                test_val = "Test Secret"
                secret = model.objects.create(name=test_val)
                retrieved_secret = model.objects.get(id=secret.id)
                self.assertNotEqual(test_val, retrieved_secret.name)
                self.assertTrue(retrieved_secret.name.startswith(EncryptedCharField.prefix))

    @run_if_active
    def testUnacceptablePurpose(self):
        """
        Tries to create an encrypted field with a mode mismatch.
        A purpose of "DECRYPT_AND_ENCRYPT" cannot be used with a public key,
        since public keys cannot be used for decryption. This should raise an
        exception.
        """
        with self.assertRaises(keyczar.errors.KeyczarError):
            with keys(keyinfo.ENCRYPT):
                with secret_model():
                    # A KeyCzar exception should get raised during class
                    # definition time, so any code in here would never get run.
                    pass

    @run_if_active
    def testDecryptionForbidden(self):
        """
        Uses a private key to encrypt data, but decryption is not allowed.
        ENCRYPTED_FIELD_MODE is explicitly set to ENCRYPT, meaning data should
        not be decrypted, even though the key would allow for it.
        """
        with keys(keyinfo.DECRYPT_AND_ENCRYPT, mode=keyinfo.ENCRYPT.name):
            with secret_model() as model:
                test_val = "Test Secret"
                secret = model.objects.create(name=test_val)
                retrieved_secret = model.objects.get(id=secret.id)
                self.assertNotEqual(test_val, retrieved_secret.name)
                self.assertTrue(retrieved_secret.name.startswith(EncryptedCharField.prefix))

    @run_if_active
    def testEncryptPublicDecryptPrivate(self):
        """
        Uses a public key to encrypt, and a private key to decrypt data.
        """
        test_val = "Test Secret"

        # First, encrypt data with public key and save to db.
        with keys(keyinfo.ENCRYPT, mode=keyinfo.ENCRYPT.name):
            with secret_model() as model:
                secret = model.objects.create(name=test_val)
                enc_retrieved_secret = model.objects.get(id=secret.id)
                self.assertNotEqual(test_val, enc_retrieved_secret.name)
                self.assertTrue(enc_retrieved_secret.name.startswith(EncryptedCharField.prefix))

        # Next, retrieve data from db, and decrypt with private key.
        with keys(keyinfo.DECRYPT_AND_ENCRYPT):
            with secret_model() as model:
                retrieved_secret = model.objects.get(id=secret.id)
                self.assertEqual(test_val, retrieved_secret.name)


########NEW FILE########
__FILENAME__ = fields
import django
from django.conf import settings
from django.core.management import call_command
from django.db.models import loading
from django.db import models
from django.utils import unittest

from django_extensions.db.fields import AutoSlugField
from django_extensions.tests.testapp.models import SluggedTestModel, ChildSluggedTestModel

if django.VERSION[:2] >= (1, 7):
    from django.db import migrations  # NOQA
    from django.db.migrations.writer import MigrationWriter  # NOQA
    from django.utils import six  # NOQA
    import django_extensions  # NOQA


class FieldTestCase(unittest.TestCase):
    def setUp(self):
        self.old_installed_apps = settings.INSTALLED_APPS
        #settings.INSTALLED_APPS = list(settings.INSTALLED_APPS)
        #settings.INSTALLED_APPS.append('django_extensions.tests.testapp')
        loading.cache.loaded = False

        # Don't migrate if south is installed
        migrate = 'south' not in settings.INSTALLED_APPS
        call_command('syncdb', verbosity=0, migrate=migrate)

    def tearDown(self):
        settings.INSTALLED_APPS = self.old_installed_apps

    def safe_exec(self, string, value=None):
        l = {}
        try:
            exec(string, globals(), l)
        except Exception as e:
            if value:
                self.fail("Could not exec %r (from value %r): %s" % (string.strip(), value, e))
            else:
                self.fail("Could not exec %r: %s" % (string.strip(), e))
        return l


class AutoSlugFieldTest(FieldTestCase):
    def tearDown(self):
        super(AutoSlugFieldTest, self).tearDown()

        SluggedTestModel.objects.all().delete()

    def testAutoCreateSlug(self):
        m = SluggedTestModel(title='foo')
        m.save()
        self.assertEqual(m.slug, 'foo')

    def testAutoCreateNextSlug(self):
        m = SluggedTestModel(title='foo')
        m.save()

        m = SluggedTestModel(title='foo')
        m.save()
        self.assertEqual(m.slug, 'foo-2')

    def testAutoCreateSlugWithNumber(self):
        m = SluggedTestModel(title='foo 2012')
        m.save()
        self.assertEqual(m.slug, 'foo-2012')

    def testAutoUpdateSlugWithNumber(self):
        m = SluggedTestModel(title='foo 2012')
        m.save()
        m.save()
        self.assertEqual(m.slug, 'foo-2012')

    def testUpdateSlug(self):
        m = SluggedTestModel(title='foo')
        m.save()
        self.assertEqual(m.slug, 'foo')

        # update m instance without using `save'
        SluggedTestModel.objects.filter(pk=m.pk).update(slug='foo-2012')
        # update m instance with new data from the db
        m = SluggedTestModel.objects.get(pk=m.pk)
        self.assertEqual(m.slug, 'foo-2012')

        m.save()
        self.assertEqual(m.title, 'foo')
        self.assertEqual(m.slug, 'foo-2012')

        # Check slug is not overwrite
        m.title = 'bar'
        m.save()
        self.assertEqual(m.title, 'bar')
        self.assertEqual(m.slug, 'foo-2012')

    def testSimpleSlugSource(self):
        m = SluggedTestModel(title='-foo')
        m.save()
        self.assertEqual(m.slug, 'foo')

        n = SluggedTestModel(title='-foo')
        n.save()
        self.assertEqual(n.slug, 'foo-2')

        n.save()
        self.assertEqual(n.slug, 'foo-2')

    def testEmptySlugSource(self):
        # regression test

        m = SluggedTestModel(title='')
        m.save()
        self.assertEqual(m.slug, '-2')

        n = SluggedTestModel(title='')
        n.save()
        self.assertEqual(n.slug, '-3')

        n.save()
        self.assertEqual(n.slug, '-3')

    def testInheritanceCreatesNextSlug(self):
        m = SluggedTestModel(title='foo')
        m.save()

        n = ChildSluggedTestModel(title='foo')
        n.save()
        self.assertEqual(n.slug, 'foo-2')

        o = SluggedTestModel(title='foo')
        o.save()
        self.assertEqual(o.slug, 'foo-3')

    @unittest.skipIf(django.VERSION[0] <= 1 and django.VERSION[1] <= 6,
                     "Migrations are handled by south in Django <1.7")
    def test_17_migration(self):
        """
        Tests making migrations with Django 1.7+'s migration framework
        """

        fields = {
            'autoslugfield': AutoSlugField(populate_from='otherfield'),
        }

        migration = type(str("Migration"), (migrations.Migration,), {
            "operations": [
                migrations.CreateModel("MyModel", tuple(fields.items()),
                                       {'populate_from': 'otherfield'},
                                       (models.Model,)),
            ],
        })
        writer = MigrationWriter(migration)
        output = writer.as_string()
        # It should NOT be unicode.
        self.assertIsInstance(output, six.binary_type,
                              "Migration as_string returned unicode")
        # We don't test the output formatting - that's too fragile.
        # Just make sure it runs for now, and that things look alright.
        result = self.safe_exec(output)
        self.assertIn("Migration", result)

########NEW FILE########
__FILENAME__ = json_field
from django_extensions.tests.fields import FieldTestCase
from django_extensions.tests.testapp.models import JSONFieldTestModel


class JsonFieldTest(FieldTestCase):
    def testCharFieldCreate(self):
        j = JSONFieldTestModel.objects.create(a=6, j_field=dict(foo='bar'))
        self.assertEqual(j.a, 6)

    def testDefault(self):
        j = JSONFieldTestModel.objects.create(a=1)
        self.assertEqual(j.j_field, {})

    def testEmptyList(self):
        j = JSONFieldTestModel.objects.create(a=6, j_field=[])
        self.assertTrue(isinstance(j.j_field, list))
        self.assertEqual(j.j_field, [])

########NEW FILE########
__FILENAME__ = error_raising_command

from django_extensions.management.base import LoggingBaseCommand


class Command(LoggingBaseCommand):
    help = 'Test error'

    def handle(self, *args, **options):
        raise Exception("Test Error")


########NEW FILE########
__FILENAME__ = management_command
# -*- coding: utf-8 -*-
import logging

try:
    from cStringIO import StringIO  # NOQA
except ImportError:
    from io import StringIO  # NOQA

try:
    import importlib  # NOQA
except ImportError:
    from django.utils import importlib  # NOQA

from django.core.management import call_command
from django.test import TestCase


class MockLoggingHandler(logging.Handler):
    """ Mock logging handler to check for expected logs. """

    def __init__(self, *args, **kwargs):
        self.reset()
        logging.Handler.__init__(self, *args, **kwargs)

    def emit(self, record):
        self.messages[record.levelname.lower()].append(record.getMessage())

    def reset(self):
        self.messages = {
            'debug': [],
            'info': [],
            'warning': [],
            'error': [],
            'critical': [],
        }


class CommandTest(TestCase):
    def test_error_logging(self):
        # Ensure command errors are properly logged and reraised
        from django_extensions.management.base import logger
        logger.addHandler(MockLoggingHandler())
        module_path = "django_extensions.tests.management.commands.error_raising_command"
        module = importlib.import_module(module_path)
        error_raising_command = module.Command()
        self.assertRaises(Exception, error_raising_command.execute)
        handler = logger.handlers[0]
        self.assertEqual(len(handler.messages['error']), 1)


class ShowTemplateTagsTests(TestCase):
    def test_some_output(self):
        out = StringIO()
        call_command('show_templatetags', stdout=out)
        output = out.getvalue()
        # Once django_extension is installed during tests it should appear with
        # its templatetags
        self.assertIn('django_extensions', output)
        # let's check at least one
        self.assertIn('truncate_letters', output)

########NEW FILE########
__FILENAME__ = shortuuid_field
import six
from django.conf import settings
from django.core.management import call_command
from django.db.models import loading
from django.utils import unittest

from django_extensions.tests.testapp.models import ShortUUIDTestModel_field, ShortUUIDTestModel_pk, ShortUUIDTestAgregateModel, ShortUUIDTestManyToManyModel


class ShortUUIDFieldTest(unittest.TestCase):
    def setUp(self):
        self.old_installed_apps = settings.INSTALLED_APPS
        settings.INSTALLED_APPS = list(settings.INSTALLED_APPS)
        settings.INSTALLED_APPS.append('django_extensions.tests')
        loading.cache.loaded = False
        call_command('syncdb', verbosity=0)

    def tearDown(self):
        settings.INSTALLED_APPS = self.old_installed_apps

    def testUUIDFieldCreate(self):
        j = ShortUUIDTestModel_field.objects.create(a=6, uuid_field=six.u('vytxeTZskVKR7C7WgdSP3d'))
        self.assertEqual(j.uuid_field, six.u('vytxeTZskVKR7C7WgdSP3d'))

    def testUUIDField_pkCreate(self):
        j = ShortUUIDTestModel_pk.objects.create(uuid_field=six.u('vytxeTZskVKR7C7WgdSP3d'))
        self.assertEqual(j.uuid_field, six.u('vytxeTZskVKR7C7WgdSP3d'))
        self.assertEqual(j.pk, six.u('vytxeTZskVKR7C7WgdSP3d'))

    def testUUIDField_pkAgregateCreate(self):
        j = ShortUUIDTestAgregateModel.objects.create(a=6)
        self.assertEqual(j.a, 6)
        self.assertIsInstance(j.pk, six.string_types)
        self.assertTrue(len(j.pk) < 23)

    def testUUIDFieldManyToManyCreate(self):
        j = ShortUUIDTestManyToManyModel.objects.create(uuid_field=six.u('vytxeTZskVKR7C7WgdSP3e'))
        self.assertEqual(j.uuid_field, six.u('vytxeTZskVKR7C7WgdSP3e'))
        self.assertEqual(j.pk, six.u('vytxeTZskVKR7C7WgdSP3e'))

########NEW FILE########
__FILENAME__ = models
from django.db import models

from django_extensions.db.models import ActivatorModel
from django_extensions.db.fields import AutoSlugField
from django_extensions.db.fields import UUIDField
from django_extensions.db.fields import ShortUUIDField
from django_extensions.db.fields.json import JSONField


class Secret(models.Model):
    name = models.CharField(blank=True, max_length=255, null=True)
    text = models.TextField(blank=True, null=True)


class Name(models.Model):
    name = models.CharField(max_length=50)


class Note(models.Model):
    note = models.TextField()


class Person(models.Model):
    name = models.ForeignKey(Name)
    age = models.PositiveIntegerField()
    children = models.ManyToManyField('self')
    notes = models.ManyToManyField(Note)


class Post(ActivatorModel):
    title = models.CharField(max_length=255)


class SluggedTestModel(models.Model):
    title = models.CharField(max_length=42)
    slug = AutoSlugField(populate_from='title')


class ChildSluggedTestModel(SluggedTestModel):
    pass


class JSONFieldTestModel(models.Model):
    a = models.IntegerField()
    j_field = JSONField()


class UUIDTestModel_field(models.Model):
    a = models.IntegerField()
    uuid_field = UUIDField()


class UUIDTestModel_pk(models.Model):
    uuid_field = UUIDField(primary_key=True)


class UUIDTestAgregateModel(UUIDTestModel_pk):
    a = models.IntegerField()


class UUIDTestManyToManyModel(UUIDTestModel_pk):
    many = models.ManyToManyField(UUIDTestModel_field)


class ShortUUIDTestModel_field(models.Model):
    a = models.IntegerField()
    uuid_field = ShortUUIDField()


class ShortUUIDTestModel_pk(models.Model):
    uuid_field = ShortUUIDField(primary_key=True)


class ShortUUIDTestAgregateModel(ShortUUIDTestModel_pk):
    a = models.IntegerField()


class ShortUUIDTestManyToManyModel(ShortUUIDTestModel_pk):
    many = models.ManyToManyField(ShortUUIDTestModel_field)

########NEW FILE########
__FILENAME__ = urls

########NEW FILE########
__FILENAME__ = test_clean_pyc
import os
import six
import shutil
import fnmatch
from django.test import TestCase
from django.test.utils import override_settings
from django.core.management import call_command
from django_extensions.management.utils import get_project_root


class CleanPycTests(TestCase):
    def setUp(self):
        self._settings = os.environ.get('DJANGO_SETTINGS_MODULE')
        os.environ['DJANGO_SETTINGS_MODULE'] = 'django_extensions.settings'

    def tearDown(self):
        if self._settings:
            os.environ['DJANGO_SETTINGS_MODULE'] = self._settings

    def _find_pyc(self, path):
        pyc_glob = []
        for root, dirnames, filenames in os.walk(path):
            for filename in fnmatch.filter(filenames, '*.pyc'):
                pyc_glob.append(os.path.join(root, filename))
        return pyc_glob

    @override_settings(CLEAN_PYC_DEPRECATION_WAIT=False)
    def test_assumes_project_root(self):
        out = six.StringIO()
        call_command('clean_pyc', stdout=out)
        expected = "Assuming '%s' is the project root." % get_project_root()
        output = out.getvalue()
        self.assertIn(expected, output)

    def test_removes_pyc_files(self):
        with self.settings(BASE_DIR=get_project_root()):
            call_command('compile_pyc')
        pyc_glob = self._find_pyc(get_project_root())
        self.assertTrue(len(pyc_glob) > 0)
        with self.settings(BASE_DIR=get_project_root()):
            call_command('clean_pyc')
        pyc_glob = self._find_pyc(get_project_root())
        self.assertEqual(len(pyc_glob), 0)

    def test_takes_path(self):
        out = six.StringIO()
        project_root = os.path.join(get_project_root(), 'tests', 'testapp')
        call_command('compile_pyc', path=project_root)
        pyc_glob = self._find_pyc(project_root)
        self.assertTrue(len(pyc_glob) > 0)
        call_command('clean_pyc', verbosity=2, path=project_root, stdout=out)
        output = out.getvalue().splitlines()
        self.assertEqual(sorted(pyc_glob), sorted(output))

    def test_removes_pyo_files(self):
        out = six.StringIO()
        project_root = os.path.join(get_project_root(), 'tests', 'testapp')
        call_command('compile_pyc', path=project_root)
        pyc_glob = self._find_pyc(project_root)
        self.assertTrue(len(pyc_glob) > 0)
        # Create some fake .pyo files since we can't force them to be created.
        pyo_glob = []
        for fn in pyc_glob:
            pyo = '%s.pyo' % os.path.splitext(fn)[0]
            shutil.copyfile(fn, pyo)
            pyo_glob.append(pyo)
        call_command('clean_pyc', verbosity=2, path=project_root,
                     optimize=True, stdout=out)
        output = out.getvalue().splitlines()
        self.assertEqual(sorted(pyc_glob + pyo_glob), sorted(output))

########NEW FILE########
__FILENAME__ = test_compile_pyc
import os
import six
import fnmatch
from django.test import TestCase
from django.test.utils import override_settings
from django.core.management import call_command
from django_extensions.management.utils import get_project_root


class CompilePycTests(TestCase):
    def setUp(self):
        self._settings = os.environ.get('DJANGO_SETTINGS_MODULE')
        os.environ['DJANGO_SETTINGS_MODULE'] = 'django_extensions.settings'

    def tearDown(self):
        if self._settings:
            os.environ['DJANGO_SETTINGS_MODULE'] = self._settings

    def _find_pyc(self, path, mask='*.pyc'):
        pyc_glob = []
        for root, dirs, filenames in os.walk(path):
            for filename in fnmatch.filter(filenames, mask):
                pyc_glob.append(os.path.join(root, filename))
        return pyc_glob

    @override_settings(CLEAN_PYC_DEPRECATION_WAIT=False, COMPILE_PYC_DEPRECATION_WAIT=False)
    def test_assumes_project_root(self):
        out = six.StringIO()
        call_command('compile_pyc', stdout=out)
        expected = "Assuming '%s' is the project root." % get_project_root()
        output = out.getvalue()
        self.assertIn(expected, output)
        call_command('clean_pyc', stdout=out)

    def test_compiles_pyc_files(self):
        with self.settings(BASE_DIR=get_project_root()):
            call_command('clean_pyc')
        pyc_glob = self._find_pyc(get_project_root())
        self.assertEqual(len(pyc_glob), 0)
        with self.settings(BASE_DIR=get_project_root()):
            call_command('compile_pyc')
        pyc_glob = self._find_pyc(get_project_root())
        self.assertTrue(len(pyc_glob) > 0)
        with self.settings(BASE_DIR=get_project_root()):
            call_command('clean_pyc')

    def test_takes_path(self):
        out = six.StringIO()
        project_root = os.path.join(get_project_root(), 'tests', 'testapp')
        with self.settings(BASE_DIR=get_project_root()):
            call_command('clean_pyc', path=project_root)
        pyc_glob = self._find_pyc(project_root)
        self.assertEqual(len(pyc_glob), 0)
        with self.settings(BASE_DIR=get_project_root()):
            call_command('compile_pyc', verbosity=2, path=project_root, stdout=out)
        expected = ['Compiling %s...' % fn for fn in
                    sorted(self._find_pyc(project_root, mask='*.py'))]
        output = out.getvalue().splitlines()
        self.assertEqual(expected, sorted(output))
        with self.settings(BASE_DIR=get_project_root()):
            call_command('clean_pyc')

########NEW FILE########
__FILENAME__ = test_dumpscript
import sys
import six

if sys.version_info[:2] >= (2, 6):
    import ast as compiler  # NOQA
else:
    import compiler  # NOQA

from django.core.management import call_command

from django_extensions.tests.testapp.models import Name, Note, Person
from django_extensions.tests.fields import FieldTestCase


class DumpScriptTests(FieldTestCase):
    def setUp(self):
        super(DumpScriptTests, self).setUp()

        self.real_stdout = sys.stdout
        self.real_stderr = sys.stderr
        sys.stdout = six.StringIO()
        sys.stderr = six.StringIO()

    def tearDown(self):
        super(DumpScriptTests, self).tearDown()

        sys.stdout = self.real_stdout
        sys.stderr = self.real_stderr

    def test_runs(self):
        # lame test...does it run?
        n = Name(name='Gabriel')
        n.save()
        call_command('dumpscript', 'testapp')
        self.assertTrue('Gabriel' in sys.stdout.getvalue())

    #----------------------------------------------------------------------
    def test_replaced_stdout(self):
        # check if stdout can be replaced
        sys.stdout = six.StringIO()
        n = Name(name='Mike')
        n.save()
        tmp_out = six.StringIO()
        call_command('dumpscript', 'testapp', stdout=tmp_out)
        self.assertTrue('Mike' in tmp_out.getvalue())  # script should go to tmp_out
        self.assertEqual(0, len(sys.stdout.getvalue()))  # there should not be any output to sys.stdout
        tmp_out.close()

    #----------------------------------------------------------------------
    def test_replaced_stderr(self):
        # check if stderr can be replaced, without changing stdout
        n = Name(name='Fred')
        n.save()
        tmp_err = six.StringIO()
        sys.stderr = six.StringIO()
        call_command('dumpscript', 'testapp', stderr=tmp_err)
        self.assertTrue('Fred' in sys.stdout.getvalue())  # script should still go to stdout
        self.assertTrue('Name' in tmp_err.getvalue())  # error output should go to tmp_err
        self.assertEqual(0, len(sys.stderr.getvalue()))  # there should not be any output to sys.stderr
        tmp_err.close()

    #----------------------------------------------------------------------
    def test_valid_syntax(self):
        n1 = Name(name='John')
        n1.save()
        p1 = Person(name=n1, age=40)
        p1.save()
        n2 = Name(name='Jane')
        n2.save()
        p2 = Person(name=n2, age=18)
        p2.save()
        p2.children.add(p1)
        note1 = Note(note="This is the first note.")
        note1.save()
        note2 = Note(note="This is the second note.")
        note2.save()
        p2.notes.add(note1, note2)
        tmp_out = six.StringIO()
        call_command('dumpscript', 'testapp', stdout=tmp_out)
        ast_syntax_tree = compiler.parse(tmp_out.getvalue())
        if hasattr(ast_syntax_tree, 'body'):
            self.assertTrue(len(ast_syntax_tree.body) > 1)
        else:
            self.assertTrue(len(ast_syntax_tree.asList()) > 1)
        tmp_out.close()


########NEW FILE########
__FILENAME__ = test_models
from django.test import TestCase

from django_extensions.db.models import ActivatorModel
from django_extensions.tests.testapp.models import Post


class ActivatorModelTestCase(TestCase):
    def test_active_includes_active(self):
        post = Post.objects.create(status=ActivatorModel.ACTIVE_STATUS)
        active = Post.objects.active()
        self.assertIn(post, active)
        post.delete()

    def test_active_excludes_inactive(self):
        post = Post.objects.create(status=ActivatorModel.INACTIVE_STATUS)
        active = Post.objects.active()
        self.assertNotIn(post, active)
        post.delete()

    def test_inactive_includes_inactive(self):
        post = Post.objects.create(status=ActivatorModel.INACTIVE_STATUS)
        inactive = Post.objects.inactive()
        self.assertIn(post, inactive)
        post.delete()

    def test_inactive_excludes_active(self):
        post = Post.objects.create(status=ActivatorModel.ACTIVE_STATUS)
        inactive = Post.objects.inactive()
        self.assertNotIn(post, inactive)
        post.delete()

    def test_active_is_chainable(self):
        post = Post.objects.create(title='Foo', status=ActivatorModel.ACTIVE_STATUS)
        specific_post = Post.objects.filter(title='Foo').active()
        self.assertIn(post, specific_post)
        post.delete()

    def test_inactive_is_chainable(self):
        post = Post.objects.create(title='Foo', status=ActivatorModel.INACTIVE_STATUS)
        specific_post = Post.objects.filter(title='Foo').inactive()
        self.assertIn(post, specific_post)
        post.delete()

########NEW FILE########
__FILENAME__ = test_templatetags
import six

from django.test import TestCase

from django_extensions.templatetags.widont import widont, widont_html


class TemplateTagsTests(TestCase):
    def test_widont(self):
        widont('Test Value')
        widont(six.u('Test Value'))

    def test_widont_html(self):
        widont_html('Test Value')
        widont_html(six.u('Test Value'))

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
import sys
import six

from django.test import TestCase
from django.utils.unittest import skipIf

from django_extensions.utils.text import truncate_letters
try:
    import uuid
    assert uuid
except ImportError:
    from django_extensions.utils import uuid


class TruncateLetterTests(TestCase):
    def test_truncate_more_than_text_length(self):
        self.assertEqual(six.u("hello tests"), truncate_letters("hello tests", 100))

    def test_truncate_text(self):
        self.assertEqual(six.u("hello..."), truncate_letters("hello tests", 5))

    def test_truncate_with_range(self):
        for i in range(10, -1, -1):
            self.assertEqual(
                six.u('hello tests'[:i]) + '...',
                truncate_letters("hello tests", i)
            )

    def test_with_non_ascii_characters(self):
        self.assertEqual(
            six.u('\u5ce0 (\u3068\u3046\u3052 t\u014dg...'),
            truncate_letters("峠 (とうげ tōge - mountain pass)", 10)
        )


class UUIDTests(TestCase):
    @skipIf(sys.version_info >= (2, 5, 0), 'uuid already in stdlib')
    def test_uuid3(self):
        # make a UUID using an MD5 hash of a namespace UUID and a name
        self.assertEqual(
            uuid.UUID('6fa459ea-ee8a-3ca4-894e-db77e160355e'),
            uuid.uuid3(uuid.NAMESPACE_DNS, 'python.org')
        )

    @skipIf(sys.version_info >= (2, 5, 0), 'uuid already in stdlib')
    def test_uuid5(self):
        # make a UUID using a SHA-1 hash of a namespace UUID and a name
        self.assertEqual(
            uuid.UUID('886313e1-3b8a-5372-9b90-0c9aee199e5d'),
            uuid.uuid5(uuid.NAMESPACE_DNS, 'python.org')
        )

    @skipIf(sys.version_info >= (2, 5, 0), 'uuid already in stdlib')
    def test_uuid_str(self):
        # make a UUID from a string of hex digits (braces and hyphens ignored)
        x = uuid.UUID('{00010203-0405-0607-0809-0a0b0c0d0e0f}')
        # convert a UUID to a string of hex digits in standard form
        self.assertEqual('00010203-0405-0607-0809-0a0b0c0d0e0f', str(x))

    @skipIf(sys.version_info >= (2, 5, 0), 'uuid already in stdlib')
    def test_uuid_bytes(self):
        # make a UUID from a string of hex digits (braces and hyphens ignored)
        x = uuid.UUID('{00010203-0405-0607-0809-0a0b0c0d0e0f}')
        # get the raw 16 bytes of the UUID
        self.assertEqual(
            '\\x00\\x01\\x02\\x03\\x04\\x05\\x06\\x07\\x08\\t\\n\\x0b\\x0c\\r\\x0e\\x0f',
            x.bytes
        )

    @skipIf(sys.version_info >= (2, 5, 0), 'uuid already in stdlib')
    def test_make_uuid_from_byte_string(self):
        self.assertEqual(
            uuid.UUID(bytes='\\x00\\x01\\x02\\x03\\x04\\x05\\x06\\x07\\x08\\t\\n\\x0b\\x0c\\r\\x0e\\x0f'),
            uuid.UUID('00010203-0405-0607-0809-0a0b0c0d0e0f')
        )

########NEW FILE########
__FILENAME__ = uuid_field
import re
import uuid

import six

from django_extensions.db.fields import PostgreSQLUUIDField
from django_extensions.tests.fields import FieldTestCase
from django_extensions.tests.testapp.models import UUIDTestModel_field, UUIDTestModel_pk, UUIDTestAgregateModel, UUIDTestManyToManyModel


class UUIDFieldTest(FieldTestCase):
    def testUUIDFieldCreate(self):
        j = UUIDTestModel_field.objects.create(a=6, uuid_field=six.u('550e8400-e29b-41d4-a716-446655440000'))
        self.assertEqual(j.uuid_field, six.u('550e8400-e29b-41d4-a716-446655440000'))

    def testUUIDField_pkCreate(self):
        j = UUIDTestModel_pk.objects.create(uuid_field=six.u('550e8400-e29b-41d4-a716-446655440000'))
        self.assertEqual(j.uuid_field, six.u('550e8400-e29b-41d4-a716-446655440000'))
        self.assertEqual(j.pk, six.u('550e8400-e29b-41d4-a716-446655440000'))

    def testUUIDField_pkAgregateCreate(self):
        j = UUIDTestAgregateModel.objects.create(a=6, uuid_field=six.u('550e8400-e29b-41d4-a716-446655440001'))
        self.assertEqual(j.a, 6)
        self.assertIsInstance(j.pk, six.string_types)
        self.assertEqual(len(j.pk), 36)

    def testUUIDFieldManyToManyCreate(self):
        j = UUIDTestManyToManyModel.objects.create(uuid_field=six.u('550e8400-e29b-41d4-a716-446655440010'))
        self.assertEqual(j.uuid_field, six.u('550e8400-e29b-41d4-a716-446655440010'))
        self.assertEqual(j.pk, six.u('550e8400-e29b-41d4-a716-446655440010'))


class PostgreSQLUUIDFieldTest(FieldTestCase):
    def test_uuid_casting(self):
        # As explain by postgres documentation
        # http://www.postgresql.org/docs/9.1/static/datatype-uuid.html
        # an uuid needs to be a sequence of lower-case hexadecimal digits, in
        # several groups separated by hyphens, specifically a group of 8 digits
        # followed by three groups of 4 digits followed by a group of 12 digits
        matcher = re.compile('^[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}'
                             '-[\da-f]{12}$')
        field = PostgreSQLUUIDField()
        for value in (str(uuid.uuid4()), uuid.uuid4().urn, uuid.uuid4().hex,
                      uuid.uuid4().int, uuid.uuid4().bytes):
            prepared_value = field.get_db_prep_value(value, None)
            self.assertTrue(matcher.match(prepared_value) is not None,
                            prepared_value)

########NEW FILE########
__FILENAME__ = dia2django
# -*- coding: UTF-8 -*-
##Author Igor Támara igor@tamarapatino.org
##Use this little program as you wish, if you
#include it in your work, let others know you
#are using it preserving this note, you have
#the right to make derivative works, Use it
#at your own risk.
#Tested to work on(etch testing 13-08-2007):
#  Python 2.4.4 (#2, Jul 17 2007, 11:56:54)
#  [GCC 4.1.3 20070629 (prerelease) (Debian 4.1.2-13)] on linux2

dependclasses = ["User", "Group", "Permission", "Message"]

import re
import six
import sys
import gzip
import codecs
from xml.dom.minidom import *  # NOQA

#Type dictionary translation types SQL -> Django
tsd = {
    "text": "TextField",
    "date": "DateField",
    "varchar": "CharField",
    "int": "IntegerField",
    "float": "FloatField",
    "serial": "AutoField",
    "boolean": "BooleanField",
    "numeric": "FloatField",
    "timestamp": "DateTimeField",
    "bigint": "IntegerField",
    "datetime": "DateTimeField",
    "date": "DateField",
    "time": "TimeField",
    "bool": "BooleanField",
    "int": "IntegerField",
}

#convert varchar -> CharField
v2c = re.compile('varchar\((\d+)\)')


def index(fks, id):
    """Looks for the id on fks, fks is an array of arrays, each array has on [1]
    the id of the class in a dia diagram.  When not present returns None, else
    it returns the position of the class with id on fks"""
    for i, j in fks.items():
        if fks[i][1] == id:
            return i
    return None


def addparentstofks(rels, fks):
    """Gets a list of relations, between parents and sons and a dict of
    clases named in dia, and modifies the fks to add the parent as fk to get
    order on the output of classes and replaces the base class of the son, to
    put the class parent name.
    """
    for j in rels:
        son = index(fks, j[1])
        parent = index(fks, j[0])
        fks[son][2] = fks[son][2].replace("models.Model", parent)
        if parent not in fks[son][0]:
            fks[son][0].append(parent)


def dia2django(archivo):
    models_txt = ''
    f = codecs.open(archivo, "rb")
    #dia files are gzipped
    data = gzip.GzipFile(fileobj=f).read()
    ppal = parseString(data)
    #diagram -> layer -> object -> UML - Class -> name, (attribs : composite -> name,type)
    datos = ppal.getElementsByTagName("dia:diagram")[0].getElementsByTagName("dia:layer")[0].getElementsByTagName("dia:object")
    clases = {}
    herit = []
    imports = six.u("")
    for i in datos:
        #Look for the classes
        if i.getAttribute("type") == "UML - Class":
            myid = i.getAttribute("id")
            for j in i.childNodes:
                if j.nodeType == Node.ELEMENT_NODE and j.hasAttributes():
                    if j.getAttribute("name") == "name":
                        actclas = j.getElementsByTagName("dia:string")[0].childNodes[0].data[1:-1]
                        myname = "\nclass %s(models.Model) :\n" % actclas
                        clases[actclas] = [[], myid, myname, 0]
                    if j.getAttribute("name") == "attributes":
                        for l in j.getElementsByTagName("dia:composite"):
                            if l.getAttribute("type") == "umlattribute":
                                #Look for the attribute name and type
                                for k in l.getElementsByTagName("dia:attribute"):
                                    if k.getAttribute("name") == "name":
                                        nc = k.getElementsByTagName("dia:string")[0].childNodes[0].data[1:-1]
                                    elif k.getAttribute("name") == "type":
                                        tc = k.getElementsByTagName("dia:string")[0].childNodes[0].data[1:-1]
                                    elif k.getAttribute("name") == "value":
                                        val = k.getElementsByTagName("dia:string")[0].childNodes[0].data[1:-1]
                                        if val == '##':
                                            val = ''
                                    elif k.getAttribute("name") == "visibility" and k.getElementsByTagName("dia:enum")[0].getAttribute("val") == "2":
                                        if tc.replace(" ", "").lower().startswith("manytomanyfield("):
                                                #If we find a class not in our model that is marked as being to another model
                                                newc = tc.replace(" ", "")[16:-1]
                                                if dependclasses.count(newc) == 0:
                                                        dependclasses.append(newc)
                                        if tc.replace(" ", "").lower().startswith("foreignkey("):
                                                #If we find a class not in our model that is marked as being to another model
                                                newc = tc.replace(" ", "")[11:-1]
                                                if dependclasses.count(newc) == 0:
                                                        dependclasses.append(newc)

                                #Mapping SQL types to Django
                                varch = v2c.search(tc)
                                if tc.replace(" ", "").startswith("ManyToManyField("):
                                    myfor = tc.replace(" ", "")[16:-1]
                                    if actclas == myfor:
                                        #In case of a recursive type, we use 'self'
                                        tc = tc.replace(myfor, "'self'")
                                    elif clases[actclas][0].count(myfor) == 0:
                                        #Adding related class
                                        if myfor not in dependclasses:
                                            #In case we are using Auth classes or external via protected dia visibility
                                            clases[actclas][0].append(myfor)
                                    tc = "models." + tc
                                    if len(val) > 0:
                                        tc = tc.replace(")", "," + val + ")")
                                elif tc.find("Field") != -1:
                                    if tc.count("()") > 0 and len(val) > 0:
                                        tc = "models.%s" % tc.replace(")", "," + val + ")")
                                    else:
                                        tc = "models.%s(%s)" % (tc, val)
                                elif tc.replace(" ", "").startswith("ForeignKey("):
                                    myfor = tc.replace(" ", "")[11:-1]
                                    if actclas == myfor:
                                        #In case of a recursive type, we use 'self'
                                        tc = tc.replace(myfor, "'self'")
                                    elif clases[actclas][0].count(myfor) == 0:
                                        #Adding foreign classes
                                        if myfor not in dependclasses:
                                            #In case we are using Auth classes
                                            clases[actclas][0].append(myfor)
                                    tc = "models." + tc
                                    if len(val) > 0:
                                        tc = tc.replace(")", "," + val + ")")
                                elif varch is None:
                                    tc = "models." + tsd[tc.strip().lower()] + "(" + val + ")"
                                else:
                                    tc = "models.CharField(max_length=" + varch.group(1) + ")"
                                    if len(val) > 0:
                                        tc = tc.replace(")", ", " + val + " )")
                                if not (nc == "id" and tc == "AutoField()"):
                                    clases[actclas][2] = clases[actclas][2] + ("    %s = %s\n" % (nc, tc))
        elif i.getAttribute("type") == "UML - Generalization":
            mycons = ['A', 'A']
            a = i.getElementsByTagName("dia:connection")
            for j in a:
                if len(j.getAttribute("to")):
                    mycons[int(j.getAttribute("handle"))] = j.getAttribute("to")
            print(mycons)
            if 'A' not in mycons:
                herit.append(mycons)
        elif i.getAttribute("type") == "UML - SmallPackage":
            a = i.getElementsByTagName("dia:string")
            for j in a:
                if len(j.childNodes[0].data[1:-1]):
                    imports += six.u("from %s.models import *" % j.childNodes[0].data[1:-1])

    addparentstofks(herit, clases)
    #Ordering the appearance of classes
    #First we make a list of the classes each classs is related to.
    ordered = []
    for j, k in six.iteritems(clases):
        k[2] = k[2] + "\n    def __unicode__(self):\n        return u\"\"\n"
        for fk in k[0]:
            if fk not in dependclasses:
                clases[fk][3] += 1
        ordered.append([j] + k)

    i = 0
    while i < len(ordered):
        mark = i
        j = i + 1
        while j < len(ordered):
            if ordered[i][0] in ordered[j][1]:
                mark = j
            j += 1
        if mark == i:
            i += 1
        else:
            # swap %s in %s" % ( ordered[i] , ordered[mark]) to make ordered[i] to be at the end
            if ordered[i][0] in ordered[mark][1] and ordered[mark][0] in ordered[i][1]:
                #Resolving simplistic circular ForeignKeys
                print("Not able to resolve circular ForeignKeys between %s and %s" % (ordered[i][1], ordered[mark][0]))
                break
            a = ordered[i]
            ordered[i] = ordered[mark]
            ordered[mark] = a
        if i == len(ordered) - 1:
            break
    ordered.reverse()
    if imports:
        models_txt = str(imports)
    for i in ordered:
        models_txt += '%s\n' % str(i[3])

    return models_txt

if __name__ == '__main__':
    if len(sys.argv) == 2:
        dia2django(sys.argv[1])
    else:
        print(" Use:\n \n   " + sys.argv[0] + " diagram.dia\n\n")

########NEW FILE########
__FILENAME__ = text
import six

from django.utils.functional import allow_lazy

# conditional import, force_unicode was renamed in Django 1.5
try:
    from django.utils.encoding import force_unicode  # NOQA
except ImportError:
    from django.utils.encoding import force_text as force_unicode  # NOQA


def truncate_letters(s, num):
    """
    truncates a string to a number of letters, similar to truncate_words
    """
    s = force_unicode(s)
    length = int(num)
    if len(s) > length:
        s = s[:length]
        if not s.endswith('...'):
            s += '...'
    return s
truncate_letters = allow_lazy(truncate_letters, six.text_type)

########NEW FILE########
__FILENAME__ = validatingtemplatetags
from django.template.base import Library, Node
from django.template import defaulttags
from django.templatetags import future
register = Library()

error_on_old_style_url_tag = False
new_style_url_tag = False
errors = []


def before_new_template(force_new_urls):
    """Reset state ready for new template"""
    global new_style_url_tag, error_on_old_style_url_tag, errors
    new_style_url_tag = False
    error_on_old_style_url_tag = force_new_urls
    errors = []


def get_template_errors():
    return errors


# Disable extends and include as they are not needed, slow parsing down, and cause duplicate errors
class NoOpNode(Node):
    def render(self, context):
        return ''


@register.tag
def extends(parser, token):
    return NoOpNode()


@register.tag
def include(parser, token):
    return NoOpNode()


# We replace load to determine whether new style urls are in use and re-patch url after
# a future version is loaded
@register.tag
def load(parser, token):
    global new_style_url_tag
    bits = token.contents.split()

    reloaded_url_tag = False
    if len(bits) >= 4 and bits[-2] == "from" and bits[-1] == "future":
        for name in bits[1:-2]:
            if name == "url":
                new_style_url_tag = True
                reloaded_url_tag = True

    try:
        return defaulttags.load(parser, token)
    finally:
        if reloaded_url_tag:
            parser.tags['url'] = new_style_url


@register.tag(name='url')
def old_style_url(parser, token):
    global error_on_old_style_url_tag

    bits = token.split_contents()
    view = bits[1]

    if error_on_old_style_url_tag:
        _error("Old style url tag used (only reported once per file): {%% %s %%}" % (" ".join(bits)), token)
        error_on_old_style_url_tag = False

    if view[0] in "\"'" and view[0] == view[-1]:
        _error("Old style url tag with quotes around view name: {%% %s %%}" % (" ".join(bits)), token)

    return defaulttags.url(parser, token)


def new_style_url(parser, token):
    bits = token.split_contents()
    view = bits[1]

    if view[0] not in "\"'" or view[0] != view[-1]:
        _error("New style url tag without quotes around view name: {%% %s %%}" % (" ".join(bits)), token)

    return future.url(parser, token)


def _error(message, token):
    origin, (start, upto) = token.source
    source = origin.reload()
    line = source.count("\n", 0, start) + 1  # 1 based line numbering
    errors.append((origin, line, message))

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-extensions documentation build configuration file, created by
# sphinx-quickstart on Wed Apr  1 20:39:40 2009.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

#import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-extensions'
copyright = u'Copyright (C) 2008, 2009, 2010, 2011, 2012, 2013 Michael Trier, Bas van Oostveen and contributors'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.3'
# The full version, including alpha/beta/rc tags.
release = '1.3.7'

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
exclude_trees = ['_build']

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

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
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
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'django-extensionsdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [(
    'index', 'django-extensions.tex', u'django-extensions Documentation',
    u'Michael Trier, Bas van Oostveen, and contributors', 'manual'
), ]

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
__FILENAME__ = run_tests
#!/usr/bin/env python

import sys
import shutil
import tempfile

try:
    import django
except ImportError:
    print("Error: missing test dependency:")
    print("  django library is needed to run test suite")
    print("  you can install it with 'pip install django'")
    print("  or use tox to automatically handle test dependencies")
    sys.exit(1)

try:
    import shortuuid
except ImportError:
    print("Error: missing test dependency:")
    print("  shortuuid library is needed to run test suite")
    print("  you can install it with 'pip install shortuuid'")
    print("  or use tox to automatically handle test dependencies")
    sys.exit(1)

try:
    import dateutil
except ImportError:
    print("Error: missing test dependency:")
    print("  dateutil library is needed to run test suite")
    print("  you can install it with 'pip install python-dateutil'")
    print("  or use tox to automatically handle test dependencies")
    sys.exit(1)

try:
    import six
except ImportError:
    print("Error: missing test dependency:")
    print("  six library is needed to run test suite")
    print("  you can install it with 'pip install six'")
    print("  or use tox to automatically handle test dependencies")
    sys.exit(1)

__test_libs__ = [
    django,
    shortuuid,
    dateutil,
    six
]

from django.conf import settings


def main():
    # Dynamically configure the Django settings with the minimum necessary to
    # get Django running tests.
    KEY_LOCS = {}
    try:
        try:
            # If KeyCzar is available, set up the environment.
            from keyczar import keyczart, keyinfo

            # Create an RSA private key.
            keys_dir = tempfile.mkdtemp("django_extensions_tests_keyzcar_rsa_dir")
            keyczart.Create(keys_dir, "test", keyinfo.DECRYPT_AND_ENCRYPT, asymmetric=True)
            keyczart.AddKey(keys_dir, "PRIMARY", size=4096)
            KEY_LOCS['DECRYPT_AND_ENCRYPT'] = keys_dir

            # Create an RSA public key.
            pub_dir = tempfile.mkdtemp("django_extensions_tests_keyzcar_pub_dir")
            keyczart.PubKey(keys_dir, pub_dir)
            KEY_LOCS['ENCRYPT'] = pub_dir
        except ImportError:
            pass

        settings.configure(
            INSTALLED_APPS=[
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'django.contrib.admin',
                'django.contrib.sessions',
                'django_extensions.tests.testapp',
                'django_extensions',
            ],
            # Django replaces this, but it still wants it. *shrugs*
            DATABASE_ENGINE='django.db.backends.sqlite3',
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            MEDIA_ROOT='/tmp/django_extensions_test_media/',
            MEDIA_PATH='/media/',
            ROOT_URLCONF='django_extensions.tests.urls',
            DEBUG=True,
            TEMPLATE_DEBUG=True,
            ENCRYPTED_FIELD_KEYS_DIR=KEY_LOCS,
        )

        if django.VERSION[:2] >= (1, 7):
            django.setup()

        apps = ['django_extensions']
        if django.VERSION[:2] >= (1, 6):
            apps.append('django_extensions.tests.testapp')
            apps.append('django_extensions.tests')

        from django.core.management import call_command
        from django.test.utils import get_runner

        try:
            from django.contrib.auth import get_user_model
        except ImportError:
            USERNAME_FIELD = "username"
        else:
            USERNAME_FIELD = get_user_model().USERNAME_FIELD

        DjangoTestRunner = get_runner(settings)

        class TestRunner(DjangoTestRunner):
            def setup_databases(self, *args, **kwargs):
                result = super(TestRunner, self).setup_databases(*args, **kwargs)
                kwargs = {
                    "interactive": False,
                    "email": "admin@doesnotexit.com",
                    USERNAME_FIELD: "admin",
                }
                call_command("createsuperuser", **kwargs)
                return result

        failures = TestRunner(verbosity=2, interactive=True).run_tests(apps)
        sys.exit(failures)

    finally:
        for name, path in KEY_LOCS.items():
            # cleanup crypto key temp dirs
            shutil.rmtree(path)


if __name__ == '__main__':
    main()

########NEW FILE########
