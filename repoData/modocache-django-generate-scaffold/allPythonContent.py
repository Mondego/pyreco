__FILENAME__ = base
from django.db.models.fields import DateField, DateTimeField, \
                                    FieldDoesNotExist

from generate_scaffold.utils.modules import import_child


FIELD_ALIASES = {
    'autofield': ['auto', 'autofield'],
    'bigintegerfield': [
        'bigint', 'biginteger', 'bigintfield', 'bigintegerfield'
    ],
    'booleanfield': ['bool', 'boolean', 'booleanfield'],
    'charfield': ['string', 'char', 'charfield'],
    'commaseparatedintegerfield': [
        'comma', 'commaseparatedint', 'commaseparatedinteger',
        'commaseparatedintegerfield'
    ],
    'datefield': ['date', 'datefield'],
    'datetimefield': ['datetime', 'datetimefield'],
    'decimalfield': ['decimal', 'decimalfield'],
    'emailfield': ['email', 'emailfield'],
    'filefield': ['file', 'filefield'],
    'filepathfield': ['path', 'filepath', 'filepathfield'],
    'floatfield': ['float', 'floatfield'],
    'foreignkey': ['foreign', 'foreignkey', 'foreignkeyfield'],
    'genericipaddressfield': [
        'genericip', 'genericipaddress', 'genericipaddressfield'
    ],
    'imagefield': ['image', 'imagefield'],
    'integerfield': ['int', 'integer', 'integerfield'],
    'ipaddressfield': ['ip', 'ipaddress', 'ipaddressfield'],
    'manytomanyfield': ['many', 'manytomany', 'manytomanyfield'],
    'nullbooleanfield': ['nullbool', 'nullboolean', 'nullbooleanfield'],
    'onetoonefield': ['one', 'onetoone', 'onetoonefield'],
    'positiveintegerfield': [
        'posint', 'positiveint', 'positiveinteger', 'positiveintegerfield'
    ],
    'positivesmallintegerfield': [
        'positivesmallint', 'positivesmallinteger', 'positivesmallintegerfield'
    ],
    'slugfield': ['slug', 'slugfield'],
    'smallintegerfield': ['smallint', 'smallinteger', 'smallintegerfield'],
    'textfield': ['text', 'textfield'],
    'timefield': ['time', 'timefield'],
    'urlfield': ['url', 'urlfield'],
}


RELATIONSHIP_FIELDS = set(['foreignkey', 'manytomanyfield', 'onetoonefield'])


class GeneratorError(Exception):
    pass


class BaseGenerator(object):

    def __init__(self, app_name):
        self.app_name = app_name

    def get_app_module(self, module_name):
        import_path = '{0}.{1}'.format(self.app_name, module_name)
        import_filepath = '{0}/{1}.py'.format(self.app_name, module_name)

        try:
            module = import_child(import_path)
        except ImportError:
            raise GeneratorError(
                'Could not import {0}. Make sure {1} exists and does not '
                'contain any syntax '
                'errors.'.format(import_path, import_filepath)
            )

        return module

    def get_timestamp_field(self, model, timestamp_fieldname=None):
        if timestamp_fieldname:
            try:
                timestamp_field = model._meta.get_field(timestamp_fieldname)
            except FieldDoesNotExist:
                raise GeneratorError(
                    '{0} does not have a field named "{1}"'.format(
                        model, timestamp_fieldname)
                )
            if type(timestamp_field) not in [DateField, DateTimeField]:
                raise GeneratorError(
                    '{0} is not a DateField or a DateTimeField, it cannot '
                    'be used as a timestamp field.'.format(
                        timestamp_field)
                )
            return timestamp_field

        else:
            for field in model._meta._fields():
                if type(field) in [DateField, DateTimeField]:
                    return field

        return None

########NEW FILE########
__FILENAME__ = models
import inspect

from django.template import Context
from django.template.defaultfilters import slugify
from django.template.loader import get_template

from generate_scaffold.generators.base import BaseGenerator, GeneratorError, \
                                              FIELD_ALIASES, \
                                              RELATIONSHIP_FIELDS
from generate_scaffold.utils.strings import dumb_capitalized, \
                                            get_valid_variable


class ModelsGenerator(BaseGenerator):

    def get_field_key(self, name):
        for field_key, aliases in FIELD_ALIASES.items():
            if name in aliases:
                return field_key

        return None

    def render_field(self, field_name, field_key_alias, other_model=None):
        original_field_name = field_name
        field_name = get_valid_variable(field_name)
        if not field_name:
            raise GeneratorError(
                '{0} is not a valid field name.'.format(original_field_name))
        field_name = field_name.lower()

        field_key = self.get_field_key(field_key_alias)
        if not field_key:
            raise GeneratorError(
                '{0} is not a recognized django.db.models.fields '
                'type.'.format(field_key))

        if field_key in RELATIONSHIP_FIELDS and other_model is None:
            raise GeneratorError(
                '{0} requires a related model to be '
                'specified.'.format(field_key)
            )

        tpl_name = \
            'generate_scaffold/models/fields/{0}.txt'.format(field_key)
        tpl = get_template(tpl_name)
        c = {
            'field_name': field_name,
            'other_model': other_model,
        }
        context = Context(c)
        return tpl.render(context)

    def render_model(self, model_name, fields, add_timestamp=True):
        # FIXME - Ensure model_name is valid
        rendered_fields = [self.render_field(*field) for field in fields]

        app_models_module = self.get_app_module('models')

        if hasattr(app_models_module, model_name):
            raise GeneratorError('{0}.models.{1} already exists.'.format(
                self.app_name, model_name))
        elif hasattr(app_models_module, dumb_capitalized(model_name)):
            raise GeneratorError('{0}.models.{1} already exists.'.format(
                self.app_name, dumb_capitalized(model_name)))

        available_modules = inspect.getmembers(
            app_models_module, inspect.ismodule)

        import_db_models = False
        if not [m for m in available_modules
          if m[0] == 'models' and m[-1].__name__ == 'django.db.models']:
            import_db_models = True

        app_models_functions = inspect.getmembers(
            app_models_module, inspect.isfunction)

        import_now = add_timestamp
        if [f for f in app_models_functions
          if f[0] == 'now' and f[-1].__module__ == 'django.utils.timezone']:
            import_now = False

        model_template = get_template('generate_scaffold/models/models.txt')
        model_slug = slugify(model_name)
        class_name = dumb_capitalized(model_name)
        c = {
            'import_db_models': import_db_models,
            'import_now': import_now,
            'app_name': self.app_name,
            'model_slug': model_slug,
            'class_name': class_name,
            'fields': rendered_fields,
            'is_timestamped_model': add_timestamp,
        }
        return model_template.render(Context(c)), class_name

########NEW FILE########
__FILENAME__ = templates
import os

from django import VERSION as DJANGO_VERSION
from django.template import Context
from django.template.defaultfilters import slugify
from django.template.loader import get_template

from generate_scaffold.generators.base import BaseGenerator
from generate_scaffold.utils.directories import get_templates_in_dir


class TemplatesGenerator(BaseGenerator):

    def get_model_fields(self, model):
        return [f.name for f in model._meta.fields if f.name != 'id']

    def render_templates(
            self, model, model_templates_dirpath, timestamp_fieldname=None):

        template_templates = \
            get_templates_in_dir('generate_scaffold', 'tpls')

        class_name = model._meta.concrete_model.__name__
        model_slug = slugify(class_name)
        model_fields = self.get_model_fields(model)

        timestamp_field = self.get_timestamp_field(
            model, timestamp_fieldname)
        is_timestamped = True if timestamp_field else False

        context_keys = {
            'year': 'year.year' if DJANGO_VERSION >= (1, 5) else 'year'
        }

        for template_template in template_templates:

            if not is_timestamped and '_archive' in template_template:
                # Do not render templates for date-based views.
                continue

            filename = os.path.basename(template_template)
            dst_filename = filename.replace('MODEL_NAME', model_slug)
            dst_abspath = os.path.join(model_templates_dirpath, dst_filename)
            t = get_template(template_template)
            c = {
                'app_name': self.app_name,
                'model_slug': model_slug,
                'model_fields': model_fields,
                'class_name': class_name,
                'filename': dst_abspath,
                'is_timestamped': is_timestamped,
                'context_keys': context_keys
            }
            if is_timestamped:
                c['timestamp_field'] = timestamp_field.name

            rendered_template = t.render(Context(c))
            yield dst_abspath, rendered_template

########NEW FILE########
__FILENAME__ = urls
from django.template import Context
from django.template.defaultfilters import slugify
from django.template.loader import get_template

from generate_scaffold.generators.base import BaseGenerator
from generate_scaffold.utils.directories import get_templates_in_dir


class UrlsGenerator(BaseGenerator):

    # FIXME - Accomodate for empty urls.py, without 
    #         url imports.
    def render_urls(self, model, timestamp_fieldname=None):
        urls_module = self.get_app_module('urls')
        is_urlpatterns_available = \
            hasattr(urls_module, 'urlpatterns')

        url_pattern_templates = \
            get_templates_in_dir('generate_scaffold', 'urls', 'urls')

        class_name = model._meta.concrete_model.__name__
        model_slug = slugify(class_name)

        if self.get_timestamp_field(model, timestamp_fieldname):
            is_timestamped = True
        else:
            is_timestamped = False

        rendered_url_patterns = []
        for url_pattern_template in url_pattern_templates:
            t = get_template(url_pattern_template)
            c = {
                'app_name': self.app_name,
                'model_slug': model_slug,
                'class_name': class_name,
                'is_timestamped': is_timestamped,
            }
            rendered_url_patterns.append(t.render(Context(c)))

        url_patterns_operator = '+=' if is_urlpatterns_available else '='
        urls_template = get_template('generate_scaffold/urls/urls.txt')
        c = {
            'app_name': self.app_name,
            'model_slug': model_slug,
            'url_patterns_operator': url_patterns_operator,
            'urls': rendered_url_patterns,
        }
        return urls_template.render(Context(c))

########NEW FILE########
__FILENAME__ = views
from django.template import Context
from django.template.defaultfilters import slugify
from django.template.loader import get_template

from generate_scaffold.generators.base import BaseGenerator
from generate_scaffold.utils.directories import get_templates_in_dir


class ViewsGenerator(BaseGenerator):

    def render_views(self, model, timestamp_fieldname=None):
        views_class_templates = \
            get_templates_in_dir('generate_scaffold', 'views', 'views')

        class_name = model._meta.concrete_model.__name__
        model_slug = slugify(class_name)

        timestamp_field = self.get_timestamp_field(
            model, timestamp_fieldname)
        is_timestamped = True if timestamp_field else False

        views_context = {
            'app_name': self.app_name,
            'model_slug': model_slug,
            'class_name': class_name,
            'is_timestamped': is_timestamped,
        }
        if is_timestamped:
            views_context['timestamp_field'] = timestamp_field.name

        rendered_views_classes = []
        for view_class_template in views_class_templates:
            t = get_template(view_class_template)
            rendered_views_classes.append(t.render(Context(views_context)))

        views_template = get_template('generate_scaffold/views/views.txt')
        views_context['views'] = rendered_views_classes
        return views_template.render(Context(views_context))

########NEW FILE########
__FILENAME__ = generatescaffold
import os
from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import get_model
from django.template.defaultfilters import slugify
from django.utils import translation
from django.utils.encoding import smart_str
from django.utils.translation import ugettext as _

from generate_scaffold.generators import ModelsGenerator, ViewsGenerator, \
                                         UrlsGenerator, TemplatesGenerator, \
                                         GeneratorError
from generate_scaffold.management.transactions import FilesystemTransaction
from generate_scaffold.management.verbosity import VerboseCommandMixin
from generate_scaffold.utils.cacheclear import clean_pyc_in_dir, \
                                               reload_django_appcache
from generate_scaffold.utils.modules import import_child


class Command(VerboseCommandMixin, BaseCommand):
    command_name = os.path.split(__file__)[-1].split('.')[0]
    help = (
        'Rails-like view/template generator.\n\n'
        'manage.py {cmd_name} <app_name> [options] <model_name> '
        '[field_name:field_type ...]\n\n'
        'For example, to generate a scaffold for a model named "Post" '
        'in an app named "blogs",\nyou can issue the following command:\n\n'
        'manage.py {cmd_name} blogs Post title:char body:text '
        'blog:foreignkey=Blog'.format(cmd_name=command_name)
    )
    option_list = BaseCommand.option_list + (
        make_option('-d', '--dry-run',
            action='store_true',
            dest='dry_run',
            default=False,
            help=_('Do not actually do anything, but print what '
                   'would have happened to the console.')
        ),
        make_option('-m', '--model',
            dest='existing_model',
            help=_('An existing model to generate views/templates for.')
        ),
        make_option('-t', '--timestamp-field',
            dest='timestamp_fieldname',
            help=_('The name of the field used as a timestamp for date-based '
                   'views. This option may only be used when passing a model '
                   'via the `--model` option.')
        ),
        make_option('-n', '--no-timestamps',
            action='store_false',
            dest='is_timestamped',
            default=True,
            help=_('Do not automatically append created_at and updated_at '
                   'DateTimeFields to generated models.')
        ),
    )

    def handle(self, *args, **options):
        if settings.USE_I18N:
            translation.activate(settings.LANGUAGE_CODE)

        try:
            self.generate_scaffold(*args, **options)
        finally:
            if settings.USE_I18N:
                translation.deactivate()


    def generate_scaffold(self, *args, **options):
        self.verbose = int(options.get('verbosity')) > 1
        self.dry_run = options.get('dry_run', False)
        self.is_timestamped = options.get('is_timestamped', True)
        self.existing_model = options.get('existing_model', None)
        self.timestamp_fieldname = options.get('timestamp_fieldname', None)

        if self.timestamp_fieldname and not self.existing_model:
            raise CommandError(smart_str(_(
                'The --timestamp-field option can only be used if --model '
                'is specified.')))

        try:
            app_name = args[0]
        except IndexError:
            raise CommandError('You must provide an app_name.')

        if app_name not in settings.INSTALLED_APPS:
            raise CommandError(smart_str(_(
                'You must add {0} to your INSTALLED_APPS '
                'in order for {1} to generate templates.'.format(
                    app_name, self.command_name))))

        try:
            app_module = __import__(app_name)
        except ImportError:
            raise CommandError(smart_str(_(
                'Could not import app with name: {0}'.format(app_name))))

        app_dirpath = app_module.__path__[0]

        if not self.existing_model:
            try:
                model_name = args[1]
            except IndexError:
                raise CommandError(
                    smart_str(_('You must provide a model_name.')))
        else:
            model_name = self.existing_model

        app_views_dirpath = os.path.join(app_dirpath, 'views')
        model_views_filename = '{0}_views.py'.format(slugify(model_name))
        model_views_filepath = os.path.join(
            app_views_dirpath, model_views_filename)

        # TODO - Append to views file if already exists
        if os.path.isfile(model_views_filepath):
            raise CommandError(smart_str(_(
                '{0} already exists.'.format(model_views_filepath))))

        pos_args = [a.split(':') for a in args[2:]]
        model_field_args = []
        for a in pos_args:
            # Split for other_model relationship
            split = [item for sublist in a for item in sublist.split('=')]
            model_field_args.append(split)

        if not model_field_args and not self.existing_model:
            # TODO - Allow models with only a primary key?
            raise CommandError(smart_str(_(
                'Cannot generate model with no fields.')))

        for arg in [a for a in model_field_args if len(a) < 2]:
            raise CommandError(smart_str(_(
                'No field type specified for model field: {0}'.format(arg))))

        if not self.existing_model:
            models_generator = ModelsGenerator(app_name)
            try:
                rendered_model, rendered_model_name = \
                    models_generator.render_model(
                        model_name, model_field_args, self.is_timestamped)
            except GeneratorError as err:
                raise CommandError(smart_str(_(
                    'Could not generate model.\n{0}'.format(err))))

        app_urls_filepath = os.path.join(app_dirpath, 'urls.py')
        if not os.path.isfile(app_urls_filepath) and self.dry_run:
            raise CommandError(smart_str(_(
                'It appears you don\'t have a valid URLconf in your '
                '{app_name} app. Please create a valid urls.py file '
                'and try again.\nAlternatively, you can try again without '
                'appending --dry-run to this command, in which case '
                '{cmd_name} will make a valid URLconf for you.'.format(
                    app_name=app_name, cmd_name=self.command_name))))


        with FilesystemTransaction(self.dry_run, self) as transaction:
            ### Generate model ###
            app_models_filepath = os.path.join(app_dirpath, 'models.py')

            if not self.existing_model:
                with transaction.open(app_models_filepath, 'a+') as f:
                    f.write(rendered_model)
                    f.seek(0)
                    self.log(f.read())

                # FIXME - Reload models, use namespace
                reload_django_appcache()
                exec('from {0}.models import *'.format(app_name))

            # The rest of the generators use model introspection to
            # generate views, urlpatterns, etc.
            if not self.existing_model and self.dry_run:
                # Since the model is not actually created on dry run,
                # execute the model code. This is probably a Very Bad
                # Idea.
                with open(app_models_filepath, 'r') as f:
                    code = compile(
                        f.read() + rendered_model, '<string>', 'exec')

                # Ensure django.db.models is available in namespace
                import_child('django.db.models')

                # FIXME - Use namespace dictionary
                exec code in globals()

                # Get reference to generated_model
                code_str = 'generated_model = {0}().__class__'.format(
                        rendered_model_name)
                code = compile(code_str, '<string>', 'exec')
                exec code in globals()
                generated_model = globals()['generated_model']
            else:
                generated_model = get_model(app_name, model_name)

            if not generated_model:
                raise CommandError(smart_str(_(
                    'Something when wrong when generating model '
                    '{0}'.format(model_name))))


            ### Generate views ###
            transaction.mkdir(app_views_dirpath)
            app_views_init_filepath = \
                os.path.join(app_views_dirpath, '__init__.py')

            if os.path.isdir(app_views_init_filepath):
                raise CommandError(smart_str(_(
                    'Could not create file: {0}\n'
                    'Please remove the directory at that location '
                    'and try again.'.format(app_views_init_filepath))))
            elif not os.path.exists(app_views_init_filepath):
                with transaction.open(app_views_init_filepath, 'a+') as f:
                    f.write('')
            else:
                self.msg('exists', app_views_init_filepath)

            views_generator = ViewsGenerator(app_name)
            rendered_views = views_generator.render_views(
                generated_model, self.timestamp_fieldname)

            with transaction.open(model_views_filepath, 'a+') as f:
                f.write(rendered_views)
                f.seek(0)
                self.log(f.read())


            ### Generate URLs ###
            if not os.path.isfile(app_urls_filepath):
                with transaction.open(app_urls_filepath, 'a+') as f:
                    s = 'from django.conf.urls import patterns, url\n\n'
                    f.write(s)
                    f.seek(0)
                    self.log(f.read())
            else:
                self.msg('exists', app_urls_filepath)

            urls_generator = UrlsGenerator(app_name)
            rendered_urls = urls_generator.render_urls(
                generated_model, self.timestamp_fieldname)

            with transaction.open(app_urls_filepath, 'a+') as f:
                f.write(rendered_urls)
                f.seek(0)
                self.log(f.read())


            ### Generate templates ###
            app_templates_root_dirpath = \
                os.path.join(app_dirpath, 'templates')
            transaction.mkdir(app_templates_root_dirpath)

            app_templates_app_dirpath = os.path.join(
                app_templates_root_dirpath, app_name)
            transaction.mkdir(app_templates_app_dirpath)

            model_templates_dirpath = os.path.join(
                app_templates_app_dirpath, slugify(model_name))
            transaction.mkdir(model_templates_dirpath)

            templates_generator = TemplatesGenerator(app_name)

            rendered_templates = templates_generator.render_templates(
                generated_model,
                model_templates_dirpath,
                self.timestamp_fieldname
            )

            for dst_abspath, rendered_template in rendered_templates:
                if os.path.isfile(dst_abspath):
                    self.msg('exists', dst_abspath)
                else:
                    with transaction.open(dst_abspath, 'a+') as f:
                        f.write(rendered_template)
                        f.seek(0)
                        self.log(f.read())


        # Compiled files cause problems when run
        # immediately after generation
        clean_pyc_in_dir(app_dirpath)

########NEW FILE########
__FILENAME__ = transactions
import codecs
import os
import shutil
import StringIO
import tempfile


class Filelike(StringIO.StringIO):
    def __enter__(self):
        return self

    def __exit__(self, error_type, error_value, error_traceback):
        self.close()

    def seek(self, offset, whence=None):
        pass

    def read(self):
        return self.getvalue()


class FileModification(object):
    def __init__(self, transaction, filename):
        self.transaction = transaction
        self.filename = filename
        self.backup_path = None

    def execute(self):
        self.backup_path = self.transaction.generate_path()
        shutil.copy2(self.filename, self.backup_path)
        self.transaction.msg('backup', self.filename)

    def rollback(self):
        if not self.transaction.is_dry_run:
            shutil.copy2(self.backup_path, self.filename)
        self.transaction.msg('revert', self.filename)

    def commit(self):
        self.transaction.msg('append', self.filename)
        os.remove(self.backup_path)


class FileCreation(object):
    def __init__(self, transaction, filename):
        self.transaction = transaction
        self.filename = filename

    def execute(self):
        pass

    def commit(self):
        self.transaction.msg('create', self.filename)

    def rollback(self):
        if not self.transaction.is_dry_run:
            os.remove(self.filename)
        self.transaction.msg('revert', self.filename)


class DirectoryCreation(object):
    def __init__(self, transaction, dirname):
        self.transaction = transaction
        self.dirname = dirname

    def execute(self):
        if not self.transaction.is_dry_run:
            os.mkdir(self.dirname)
        self.transaction.msg('create', self.dirname)

    def commit(self):
        pass

    def rollback(self):
        if not self.transaction.is_dry_run:
            os.rmdir(self.dirname)
        self.transaction.msg('revert', self.dirname)


class FilesystemTransaction(object):
    def __init__(self, is_dry_run=False, delegate=None):
        self.is_dry_run = is_dry_run
        self.delegate = delegate
        self.log = []
        self.counter = 0
        self.temp_directory = tempfile.mkdtemp()

    def __enter__(self):
        return self

    def __exit__(self, error_type, error_value, error_traceback):
        if error_type is None:
            self.commit()
        else:
            self.rollback()

    def msg(self, action, msg):
        if hasattr(self.delegate, 'msg'):
            self.delegate.msg(action, msg)

    def generate_path(self):
        self.counter += 1
        return os.path.join(self.temp_directory, str(self.counter))

    def rollback(self):
        for entry in reversed(self.log):
            entry.rollback()

    def commit(self):
        for entry in self.log:
            entry.commit()

    def open(self, filename, mode):
        if os.path.exists(filename):
            modification = FileModification(self, filename)
        else:
            modification = FileCreation(self, filename)
        modification.execute()
        self.log.append(modification)
        if self.is_dry_run:
            return Filelike()
        else:
            return codecs.open(filename, encoding='utf-8', mode=mode)

    def mkdir(self, dirname):
        if os.path.exists(dirname):
            self.msg('exists', dirname)
        else:
            modification = DirectoryCreation(self, dirname)
            modification.execute()
            self.log.append(modification)

########NEW FILE########
__FILENAME__ = verbosity
import os

from django.core.management.color import supports_color
from django.utils import termcolors


class VerboseCommandMixin(object):

    def __init__(self, *args, **kwargs):
        super(VerboseCommandMixin, self).__init__(*args, **kwargs)
        self.dry_run = False
        if supports_color():
            opts = ('bold',)
            self.style.EXISTS = \
                termcolors.make_style(fg='blue', opts=opts)
            self.style.APPEND = \
                termcolors.make_style(fg='yellow', opts=opts)
            self.style.CREATE = \
                termcolors.make_style(fg='green', opts=opts)
            self.style.REVERT = \
                termcolors.make_style(fg='magenta', opts=opts)
            self.style.BACKUP = \
                termcolors.make_style(fg='cyan', opts=opts)

    def msg(self, action, path):
        is_withholding_action = False
        non_actions = set(['create', 'append', 'revert'])
        if self.dry_run and action in non_actions:
            is_withholding_action = True

        if hasattr(self.style, action.upper()):
            s = getattr(self.style, action.upper())
            action = s(action)

        if is_withholding_action:
            action = self.style.NOTICE('did not ') + action

        output = '\t{0:>25}\t{1:<}\n'.format(action, os.path.relpath(path))
        self.stdout.write(output)

    def log(self, output):
        if self.verbose:
            self.stdout.write(output)

########NEW FILE########
__FILENAME__ = cacheclear
import os

from django.db.models.loading import AppCache
from django.utils.datastructures import SortedDict


def reload_django_appcache():
    cache = AppCache()

    cache.app_store = SortedDict()
    cache.app_models = SortedDict()
    cache.app_errors = {}
    cache.handled = {}
    cache.loaded = False

    for app in cache.get_apps():
        __import__(app.__name__)
        reload(app)


def clean_pyc_in_dir(dirpath):
    for root, _, files in os.walk(dirpath):
        for f in [f for f in files if os.path.splitext(f)[-1] == '.pyc']:
            os.remove(os.path.join(root, f))


########NEW FILE########
__FILENAME__ = directories
import os

from django.template.loaders import app_directories


def get_templates_in_dir(*dirs):
    dir_suffix = os.path.sep.join(dirs)
    template_dirs = []
    for app_template_dir in app_directories.app_template_dirs:
        for root, _, _ in os.walk(app_template_dir):
            if root.endswith(dir_suffix):
                template_dirs.append(root)

    for template_dir in template_dirs:
        for root, _, files in os.walk(template_dir):
            public_files = [f for f in files if not f.startswith('.')]

            for f in sorted(public_files):
                yield os.path.join(root, f)

########NEW FILE########
__FILENAME__ = modules
def import_child(module_name):
    module = __import__(module_name)
    for layer in module_name.split('.')[1:]:
        module = getattr(module, layer)
    return module

########NEW FILE########
__FILENAME__ = strings
import keyword
import re


def dumb_capitalized(s):
    return s[0].upper() + s[1:]


def get_valid_variable(candidate):
    # Remove invalid characters
    s = re.sub('[^0-9a-zA-Z_]', '', candidate)
    # Remove leading characters until we find a letter or underscore
    s = re.sub('^[^a-zA-Z_]+', '', s)

    if any([keyword.iskeyword(v) for v in [s, s.lower()]]):
        return None

    return s

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_project.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.timezone import now


class PreExistingModel(models.Model):
    description = models.TextField()


class PreExistingDatedModel(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True, default=now(), editable=False)

########NEW FILE########
__FILENAME__ = create_tests
from django.utils import unittest
from noseselenium.cases import SeleniumTestCaseMixin


class CreateTest(unittest.TestCase, SeleniumTestCaseMixin):

    url = '/test_app/generatednotimestampmodel/create/'

    def test_ok(self):
        s = self.selenium
        s.open(self.url)
        self.failUnless(s.is_text_present('GeneratedNoTimestampModel Create'))

    def test_create(self):
        s = self.selenium
        s.open(self.url)
        s.type('id_title', 'My Generated No Timestamp Model')
        s.type('id_description', 'This is a new instance of my model.')
        s.click('css=button[type="submit"]')
        s.wait_for_page_to_load('30000')

        self.failUnless(s.is_text_present('GeneratedNoTimestampModel Detail'))
        self.failUnless(s.is_text_present('My Generated No Timestamp Model'))

########NEW FILE########
__FILENAME__ = delete_tests
from django.utils import unittest
from noseselenium.cases import SeleniumTestCaseMixin


class DeleteTest(unittest.TestCase, SeleniumTestCaseMixin):

    selenium_fixtures = ['test_generatednotimestamp_model.json']
    url = '/test_app/generatednotimestampmodel/1/'

    def test_delete(self):
        s = self.selenium

        # Ensure fixture model is displayed on list view
        s.open('/test_app/generatednotimestampmodel/')
        self.failUnless(s.is_text_present('GeneratedNoTimestampModel List'))
        self.failUnless(s.is_text_present('Generated No Timestamp Model Fixture'))

        # Open detail view
        s.open('/test_app/generatednotimestampmodel/1/')
        self.failUnless(s.is_text_present('GeneratedNoTimestampModel Detail'))
        self.failUnless(s.is_text_present('Generated No Timestamp Model Fixture'))
        # Click Delete button
        s.click('css=button[type="submit"]')
        s.wait_for_page_to_load('30000')

        # Ensure fixture model is no longer displayed on list view
        self.failUnless(s.is_text_present('GeneratedNoTimestampModel List'))
        self.failIf(s.is_text_present('Generated No Timestamp Model Fixture'))

########NEW FILE########
__FILENAME__ = detail_tests
from django.utils import unittest
from noseselenium.cases import SeleniumTestCaseMixin


class DetailTest(unittest.TestCase, SeleniumTestCaseMixin):

    selenium_fixtures = ['test_generatednotimestamp_model.json']
    url = '/test_app/generatednotimestampmodel/1/'

    def test_ok(self):
        s = self.selenium
        s.open(self.url)

        self.failUnless(s.is_text_present('GeneratedNoTimestampModel Detail'))
        self.failUnless(s.is_text_present('Generated No Timestamp Model Fixture'))

    def test_update(self):
        s = self.selenium
        s.open(self.url)
        s.click('link=Update')
        s.wait_for_page_to_load('30000')

        self.failUnless(s.is_text_present('GeneratedNoTimestampModel Update'))

    def test_no_timestamps(self):
        s = self.selenium
        s.open(self.url)

        self.failIf(s.is_text_present('created_at'))
        self.failIf(s.is_text_present('updated_at'))

########NEW FILE########
__FILENAME__ = list_tests
from django.utils import unittest
from noseselenium.cases import SeleniumTestCaseMixin


class ListTest(unittest.TestCase, SeleniumTestCaseMixin):

    selenium_fixtures = ['test_generatednotimestamp_model.json']
    url = '/test_app/generatednotimestampmodel/'

    def test_ok(self):
        s = self.selenium
        s.open(self.url)
        self.failUnless(s.is_text_present('GeneratedNoTimestampModel List'))

    def test_click_on_item(self):
        s = self.selenium
        s.open(self.url)
        s.click('link=001')
        s.wait_for_page_to_load('30000')

        self.failUnless(s.is_text_present('GeneratedNoTimestampModel Detail'))
        self.failUnless(s.is_text_present('Generated No Timestamp Model Fixture'))

########NEW FILE########
__FILENAME__ = update_tests
from django.utils import unittest
from noseselenium.cases import SeleniumTestCaseMixin


class UpdateTest(unittest.TestCase, SeleniumTestCaseMixin):

    selenium_fixtures = ['test_generatednotimestamp_model.json']
    url = '/test_app/generatednotimestampmodel/1/update/'

    def test_ok(self):
        s = self.selenium
        s.open(self.url)
        self.failUnless(s.is_text_present('GeneratedNoTimestampModel Update'))

    def test_update(self):
        s = self.selenium
        s.open(self.url)
        s.type('id_title', 'No Timestamp Model Fixture Update!')
        s.click('css=button[type="submit"]')
        s.wait_for_page_to_load('30000')

        self.failUnless(s.is_text_present('GeneratedNoTimestampModel Detail'))
        self.failUnless(s.is_text_present('No Timestamp Model Fixture Update!'))

########NEW FILE########
__FILENAME__ = archive_day_tests
from django.utils import unittest
from noseselenium.cases import SeleniumTestCaseMixin


class ArchiveDayTest(unittest.TestCase, SeleniumTestCaseMixin):

    selenium_fixtures = ['test_generated_model.json']
    url = '/test_app/generatedmodel/archive/2012/8/11/'

    def setUp(self):
        self.selenium.open(self.url)

    def test_ok(self):
        s = self.selenium
        self.failUnless(s.is_text_present('GeneratedModel Day Archive'))
        self.failUnless(s.is_text_present(
            'GeneratedModels created on Aug. 11, 2012'))
        self.failUnless(s.is_text_present('Generated Model Fixture'))

    def test_link_day_archive(self):
        s = self.selenium
        s.click('link=Day Archive')
        s.wait_for_page_to_load('30000')
        self.failUnless(s.is_text_present('GeneratedModel Day Archive'))

    def test_link_month_archive(self):
        s = self.selenium
        s.click('link=Month Archive')
        s.wait_for_page_to_load('30000')
        self.failUnless(s.is_text_present('GeneratedModel Month Archive'))

    def test_link_year_archive(self):
        s = self.selenium
        s.click('link=Year Archive')
        s.wait_for_page_to_load('30000')
        self.failUnless(s.is_text_present('GeneratedModel Year Archive'))

    def test_link_archive_index(self):
        s = self.selenium
        s.click('link=Archive Index')
        s.wait_for_page_to_load('30000')
        self.failUnless(s.is_text_present('GeneratedModel Archive Index'))

########NEW FILE########
__FILENAME__ = archive_index_tests
from django.utils import unittest
from noseselenium.cases import SeleniumTestCaseMixin


class ArchiveIndexTest(unittest.TestCase, SeleniumTestCaseMixin):

    selenium_fixtures = ['test_generated_model.json']
    url = '/test_app/generatedmodel/archive/'

    def setUp(self):
        self.selenium.open(self.url)

    def test_ok(self):
        s = self.selenium
        self.failUnless(s.is_text_present('GeneratedModel Archive Index'))
        self.failUnless(s.is_text_present('Generated Model Fixture'))

    def test_year_list(self):
        s = self.selenium
        s.click('link=2012')
        s.wait_for_page_to_load('30000')
        self.failUnless(s.is_text_present('GeneratedModel Year Archive'))

    def test_link_archive_index(self):
        s = self.selenium
        s.click('link=Archive Index')
        s.wait_for_page_to_load('30000')
        self.failUnless(s.is_text_present('GeneratedModel Archive Index'))

########NEW FILE########
__FILENAME__ = archive_month_tests
from django.utils import unittest
from noseselenium.cases import SeleniumTestCaseMixin


class ArchiveMonthTest(unittest.TestCase, SeleniumTestCaseMixin):

    selenium_fixtures = ['test_generated_model.json']
    url = '/test_app/generatedmodel/archive/2012/8/'

    def setUp(self):
        self.selenium.open(self.url)

    def test_ok(self):
        s = self.selenium
        self.failUnless(s.is_text_present('GeneratedModel Month Archive'))
        self.failUnless(s.is_text_present('Generated Model Fixture'))

    # FIXME
    # https://github.com/modocache/django-generate-scaffold/issues/2
    # def test_day_list(self):
    #     s = self.selenium
    #     s.click('link=Aug. 11, 2012')
    #     s.wait_for_page_to_load('30000')
    #     self.failUnless(s.is_text_present('GeneratedModel Day Archive'))

    def test_link_month_archive(self):
        s = self.selenium
        s.click('link=Month Archive')
        s.wait_for_page_to_load('30000')
        self.failUnless(s.is_text_present('GeneratedModel Month Archive'))

    def test_link_year_archive(self):
        s = self.selenium
        s.click('link=Year Archive')
        s.wait_for_page_to_load('30000')
        self.failUnless(s.is_text_present('GeneratedModel Year Archive'))

    def test_link_archive_index(self):
        s = self.selenium
        s.click('link=Archive Index')
        s.wait_for_page_to_load('30000')
        self.failUnless(s.is_text_present('GeneratedModel Archive Index'))

########NEW FILE########
__FILENAME__ = archive_week_tests
from django.utils import unittest
from noseselenium.cases import SeleniumTestCaseMixin


class ArchiveWeekTest(unittest.TestCase, SeleniumTestCaseMixin):

    selenium_fixtures = ['test_generated_model.json']
    url = '/test_app/generatedmodel/archive/2012/8/week/32/'

    def setUp(self):
        self.selenium.open(self.url)

    def test_ok(self):
        s = self.selenium
        self.failUnless(s.is_text_present('GeneratedModel Week Archive'))
        self.failUnless(s.is_text_present('Generated Model Fixture'))

########NEW FILE########
__FILENAME__ = archive_year_tests
from django.utils import unittest
from noseselenium.cases import SeleniumTestCaseMixin


class ArchiveYearTest(unittest.TestCase, SeleniumTestCaseMixin):

    selenium_fixtures = ['test_generated_model.json']
    url = '/test_app/generatedmodel/archive/2012/'

    def setUp(self):
        self.selenium.open(self.url)

    def test_ok(self):
        s = self.selenium
        self.failUnless(s.is_text_present('GeneratedModel Year Archive'))
        self.failUnless(s.is_text_present(
            'GeneratedModels created in the year 2012'))
        self.failUnless(s.is_text_present('Generated Model Fixture'))

    # FIXME
    # https://github.com/modocache/django-generate-scaffold/issues/2
    # def test_month_list(self):
    #     s = self.selenium
    #     s.click('link=Aug 2012')
    #     s.wait_for_page_to_load('30000')
    #     self.failUnless(s.is_text_present('GeneratedModel Month Archive'))

    def test_link_year_archive(self):
        s = self.selenium
        s.click('link=Year Archive')
        s.wait_for_page_to_load('30000')
        self.failUnless(s.is_text_present('GeneratedModel Year Archive'))

    def test_link_archive_index(self):
        s = self.selenium
        s.click('link=Archive Index')
        s.wait_for_page_to_load('30000')
        self.failUnless(s.is_text_present('GeneratedModel Archive Index'))

########NEW FILE########
__FILENAME__ = create_tests
from django.utils import unittest
from noseselenium.cases import SeleniumTestCaseMixin


class CreateTest(unittest.TestCase, SeleniumTestCaseMixin):

    url = '/test_app/generatedmodel/create/'

    def test_ok(self):
        s = self.selenium
        s.open(self.url)
        self.failUnless(s.is_text_present('GeneratedModel Create'))

    def test_create(self):
        s = self.selenium
        s.open(self.url)
        s.type('id_title', 'My Generated Model')
        s.type('id_description', 'This is a new instance of my model.')
        s.click('css=button[type="submit"]')
        s.wait_for_page_to_load('30000')

        self.failUnless(s.is_text_present('GeneratedModel Detail'))
        self.failUnless(s.is_text_present('My Generated Model'))

########NEW FILE########
__FILENAME__ = date_detail_tests
from django.utils import unittest
from noseselenium.cases import SeleniumTestCaseMixin


class DateDetailTest(unittest.TestCase, SeleniumTestCaseMixin):

    selenium_fixtures = ['test_generated_model.json']
    url = '/test_app/generatedmodel/2012/8/11/1/'

    def setUp(self):
        self.selenium.open(self.url)

    def test_ok(self):
        s = self.selenium
        self.failUnless(s.is_text_present('GeneratedModel Detail'))
        self.failUnless(s.is_text_present('Generated Model Fixture'))

    def test_link_date_detail(self):
        s = self.selenium
        s.click('link=Date Detail')
        s.wait_for_page_to_load('30000')
        self.failUnless(s.is_text_present('GeneratedModel Detail'))
        self.failUnless(s.is_text_present('Generated Model Fixture'))

    def test_link_day_archive(self):
        s = self.selenium
        s.click('link=Day Archive')
        s.wait_for_page_to_load('30000')
        self.failUnless(s.is_text_present('GeneratedModel Day Archive'))

    def test_link_month_archive(self):
        s = self.selenium
        s.click('link=Month Archive')
        s.wait_for_page_to_load('30000')
        self.failUnless(s.is_text_present('GeneratedModel Month Archive'))

    def test_link_year_archive(self):
        s = self.selenium
        s.click('link=Year Archive')
        s.wait_for_page_to_load('30000')
        self.failUnless(s.is_text_present('GeneratedModel Year Archive'))

    def test_link_archive_index(self):
        s = self.selenium
        s.click('link=Archive Index')
        s.wait_for_page_to_load('30000')
        self.failUnless(s.is_text_present('GeneratedModel Archive Index'))

########NEW FILE########
__FILENAME__ = delete_tests
from django.utils import unittest
from noseselenium.cases import SeleniumTestCaseMixin


class DeleteTest(unittest.TestCase, SeleniumTestCaseMixin):

    selenium_fixtures = ['test_generated_model.json']
    url = '/test_app/generatedmodel/1/'

    def test_delete(self):
        s = self.selenium

        # Ensure fixture model is displayed on list view
        s.open('/test_app/generatedmodel/')
        self.failUnless(s.is_text_present('GeneratedModel List'))
        self.failUnless(s.is_text_present('Generated Model Fixture'))

        # Open detail view
        s.open('/test_app/generatedmodel/1/')
        self.failUnless(s.is_text_present('GeneratedModel Detail'))
        self.failUnless(s.is_text_present('Generated Model Fixture'))
        # Click Delete button
        s.click('css=button[type="submit"]')
        s.wait_for_page_to_load('30000')

        # Ensure fixture model is no longer displayed on list view
        self.failUnless(s.is_text_present('GeneratedModel List'))
        self.failIf(s.is_text_present('Generated Model Fixture'))

########NEW FILE########
__FILENAME__ = detail_tests
from django.utils import unittest
from noseselenium.cases import SeleniumTestCaseMixin


class DetailTest(unittest.TestCase, SeleniumTestCaseMixin):

    selenium_fixtures = ['test_generated_model.json']
    url = '/test_app/generatedmodel/1/'

    def test_ok(self):
        s = self.selenium
        s.open(self.url)

        self.failUnless(s.is_text_present('GeneratedModel Detail'))
        self.failUnless(s.is_text_present('Generated Model Fixture'))

    def test_update(self):
        s = self.selenium
        s.open(self.url)
        s.click('link=Update')
        s.wait_for_page_to_load('30000')

        self.failUnless(s.is_text_present('GeneratedModel Update'))

    def test_timetstamps(self):
        s = self.selenium
        s.open(self.url)

        self.failUnless(s.is_text_present('created_at'))
        self.failUnless(s.is_text_present('updated_at'))

########NEW FILE########
__FILENAME__ = list_tests
from django.utils import unittest
from noseselenium.cases import SeleniumTestCaseMixin


class ListTest(unittest.TestCase, SeleniumTestCaseMixin):

    selenium_fixtures = ['test_generated_model.json']
    url = '/test_app/generatedmodel/'

    def test_ok(self):
        s = self.selenium
        s.open(self.url)
        self.failUnless(s.is_text_present('GeneratedModel List'))

    def test_click_on_item(self):
        s = self.selenium
        s.open(self.url)
        s.click('link=001')
        s.wait_for_page_to_load('30000')

        self.failUnless(s.is_text_present('GeneratedModel Detail'))
        self.failUnless(s.is_text_present('Generated Model Fixture'))

########NEW FILE########
__FILENAME__ = update_tests
from django.utils import unittest
from noseselenium.cases import SeleniumTestCaseMixin


class UpdateTest(unittest.TestCase, SeleniumTestCaseMixin):

    selenium_fixtures = ['test_generated_model.json']
    url = '/test_app/generatedmodel/1/update/'

    def test_ok(self):
        s = self.selenium
        s.open(self.url)
        self.failUnless(s.is_text_present('GeneratedModel Update'))

    def test_update(self):
        s = self.selenium
        s.open(self.url)
        s.type('id_title', 'Generated Model Fixture Update!')
        s.click('css=button[type="submit"]')
        s.wait_for_page_to_load('30000')

        self.failUnless(s.is_text_present('GeneratedModel Detail'))
        self.failUnless(s.is_text_present('Generated Model Fixture Update!'))

########NEW FILE########
__FILENAME__ = list_tests
#-*- coding: utf-8 -*-


from django.utils import unittest
from noseselenium.cases import SeleniumTestCaseMixin


class ListTest(unittest.TestCase, SeleniumTestCaseMixin):

    url = '/test_app/i18nmodel/'

    def test_ok(self):
        s = self.selenium
        s.open(self.url)

        # Checking for non-unicode characters is causing issues, so
        # for now simply assert that usual output is not present
        self.failIf(s.is_text_present('I18nModel List'))

########NEW FILE########
__FILENAME__ = base_tests
from types import ModuleType

from nose.tools import eq_, raises

from generate_scaffold.generators import GeneratorError
from generate_scaffold.generators.base import BaseGenerator
from test_app.models import PreExistingModel, PreExistingDatedModel


TEST_APP_NAME = 'test_app'
BASE_GENERATOR = BaseGenerator(TEST_APP_NAME)
DATED_MODEL = PreExistingDatedModel()
NON_DATED_MODEL = PreExistingModel()


def test_init():
    eq_(BASE_GENERATOR.app_name, TEST_APP_NAME)


def test_get_app_module():
    module = BASE_GENERATOR.get_app_module('models')
    eq_(module.__name__, '{}.models'.format(TEST_APP_NAME))
    eq_(type(module), ModuleType)


@raises(GeneratorError)
def test_get_app_module_raises_error():
    BASE_GENERATOR.get_app_module('spaceships')


def test_get_timestamp_field_no_field_not_named():
    eq_(BASE_GENERATOR.get_timestamp_field(NON_DATED_MODEL), None)


@raises(GeneratorError)
def test_get_timestamp_field_no_field_named():
    BASE_GENERATOR.get_timestamp_field(NON_DATED_MODEL, 'doesnt-exist')


@raises(GeneratorError)
def test_get_timestamp_field_field_named_not_timestamp():
    BASE_GENERATOR.get_timestamp_field(NON_DATED_MODEL, 'description')


def test_get_timestamp_field_not_named():
    dated_field = DATED_MODEL._meta.get_field('created_at')
    timestamp_field = BASE_GENERATOR.get_timestamp_field(DATED_MODEL)

    eq_(dated_field, timestamp_field)
    eq_(timestamp_field.__class__.__name__, 'DateTimeField')


def test_get_timestamp_field_named():
    dated_field = DATED_MODEL._meta.get_field('created_at')
    timestamp_field = \
        BASE_GENERATOR.get_timestamp_field(DATED_MODEL, 'created_at')

    eq_(dated_field, timestamp_field)
    eq_(timestamp_field.__class__.__name__, 'DateTimeField')

########NEW FILE########
__FILENAME__ = models_tests
from nose.tools import eq_, raises

from generate_scaffold.generators import ModelsGenerator, GeneratorError
from generate_scaffold.generators.base import FIELD_ALIASES


TEST_APP_NAME = 'test_app'
MODELS_GENERATOR = ModelsGenerator(TEST_APP_NAME)


def test_get_field_key():
    for field_key, aliases in FIELD_ALIASES.items():
        [eq_(field_key, MODELS_GENERATOR.get_field_key(a))
            for a in aliases]


def test_get_field_key_found():
    eq_(MODELS_GENERATOR.get_field_key('bool'), 'booleanfield')


def test_get_field_key_not_found():
    eq_(MODELS_GENERATOR.get_field_key('doesnt-exist'), None)


@raises(GeneratorError)
def test_render_field_bad_variable_name():
    MODELS_GENERATOR.render_field('class', 'text')


@raises(GeneratorError)
def test_render_field_no_such_field():
    MODELS_GENERATOR.render_field('foo', 'doesnt-exist')


def test_render_autofield():
    target_field = u'auto = models.AutoField()\n'
    test_field = MODELS_GENERATOR.render_field('auto', 'auto')
    eq_(target_field, test_field)


def test_render_bigintegerfield():
    target_field = u'bigi = models.BigIntegerField()\n'
    test_field = MODELS_GENERATOR.render_field('bigi', 'bigint')
    eq_(target_field, test_field)


def test_render_booleanfield():
    target_field = u'boo = models.BooleanField()\n'
    test_field = MODELS_GENERATOR.render_field('boo', 'bool')
    eq_(target_field, test_field)


def test_render_charfield():
    target_field = u'char = models.CharField(max_length=200)\n'
    test_field = MODELS_GENERATOR.render_field('char', 'string')
    eq_(target_field, test_field)


def test_render_commaseparatedintegerfield():
    target_field = u'c = models.CommaSeparatedIntegerField()\n'
    test_field = MODELS_GENERATOR.render_field('c', 'comma')
    eq_(target_field, test_field)


def test_render_datefield():
    target_field = u'da = models.DateField()\n'
    test_field = MODELS_GENERATOR.render_field('da', 'date')
    eq_(target_field, test_field)


def test_render_datetimefield():
    target_field = u'dt = models.DateTimeField()\n'
    test_field = MODELS_GENERATOR.render_field('dt', 'datetime')
    eq_(target_field, test_field)


def test_render_decimalfield():
    target_field = \
        u'd = models.DecimalField(max_digits=10, decimal_places=5)\n'
    test_field = MODELS_GENERATOR.render_field('d', 'decimal')
    eq_(target_field, test_field)


def test_render_emailfield():
    target_field = u'emailfield = models.EmailField(max_length=254)\n'
    test_field = MODELS_GENERATOR.render_field('emailfield', 'email')
    eq_(target_field, test_field)


def test_render_filefield():
    target_field = u"__f__ = models.FileField(upload_to='uploaded_files')\n"
    test_field = MODELS_GENERATOR.render_field('__F__', 'file')
    eq_(target_field, test_field)


def test_render_filepathfield():
    target_field = u"foo = models.FilePathField(path='uploaded_files')\n"
    test_field = MODELS_GENERATOR.render_field('%&fo$o**', 'path')
    eq_(target_field, test_field)


def test_render_floatfield():
    target_field = u"this_is_a_really_long_variable_name_this_is_crazy_what_is_going_on = models.FloatField()\n"
    test_field = MODELS_GENERATOR.render_field('this_is_a_really_long_variable_name_this_is_crazy_what_is_going_on', 'float')
    eq_(target_field, test_field)


@raises(GeneratorError)
def test_render_foreignkey_without_other_model():
    MODELS_GENERATOR.render_field('owner', 'foreignkey')


def test_render_foreignkey_with_other_model():
    target_field = u"owner = models.ForeignKey('django.contrib.auth.models.User')\n"
    test_field = MODELS_GENERATOR.render_field('owner', 'foreign', 'django.contrib.auth.models.User')
    eq_(target_field, test_field)


def test_render_genericipaddressfield():
    target_field = u'ip = models.GenericIPAddressField()\n'
    test_field = MODELS_GENERATOR.render_field('ip', 'genericip')
    eq_(target_field, test_field)


def test_render_imagefield():
    target_field = u"image = models.ImageField(upload_to='uploaded_files')\n"
    test_field = MODELS_GENERATOR.render_field('image', 'image')
    eq_(target_field, test_field)


def test_render_integerfield():
    target_field = u'int = models.IntegerField()\n'
    test_field = MODELS_GENERATOR.render_field('int', 'int')
    eq_(target_field, test_field)


def test_render_ipaddressfield():
    target_field = u'ip = models.IPAddressField()\n'
    test_field = MODELS_GENERATOR.render_field('ip', 'ip')
    eq_(target_field, test_field)


@raises(GeneratorError)
def test_render_manytomanyfield_without_other_model():
    MODELS_GENERATOR.render_field('friends', 'many')


def test_render_manytomanyfield_with_other_model():
    target_field = u"friends = models.ManyToManyField('User')\n"
    test_field = MODELS_GENERATOR.render_field('friends', 'many', 'User')
    eq_(target_field, test_field)


def test_render_nullbooleanfield():
    target_field = u'nulbol = models.NullBooleanField()\n'
    test_field = MODELS_GENERATOR.render_field('nulbol', 'nullbool')
    eq_(target_field, test_field)


@raises(GeneratorError)
def test_render_onetoonefield_without_other_model():
    MODELS_GENERATOR.render_field('case', 'one')


def test_render_onetoonefield_with_other_model():
    target_field = u"case = models.OneToOneField('Case')\n"
    test_field = MODELS_GENERATOR.render_field('case', 'onetoone', 'Case')
    eq_(target_field, test_field)


def test_render_positiveintegerfield():
    target_field = u'posint = models.PositiveIntegerField()\n'
    test_field = MODELS_GENERATOR.render_field('posint', 'positiveint')
    eq_(target_field, test_field)


def test_render_positivesmallintegerfield():
    target_field = u'posmall = models.PositiveSmallIntegerField()\n'
    test_field = MODELS_GENERATOR.render_field('posmall', 'positivesmallint')
    eq_(target_field, test_field)


def test_render_slugfield():
    target_field = u'slug = models.SlugField(max_length=200)\n'
    test_field = MODELS_GENERATOR.render_field('slug', 'slug')
    eq_(target_field, test_field)


def test_render_smallintegerfield():
    target_field = u'small = models.SmallIntegerField()\n'
    test_field = MODELS_GENERATOR.render_field('small', 'smallint')
    eq_(target_field, test_field)


def test_render_textfield():
    target_field = u'test = models.TextField()\n'
    test_field = MODELS_GENERATOR.render_field('test', 'text')
    eq_(target_field, test_field)


def test_render_timefield():
    target_field = u'time = models.TimeField()\n'
    test_field = MODELS_GENERATOR.render_field('time', 'time')
    eq_(target_field, test_field)


def test_render_urlfield():
    target_field = u'url = models.URLField()\n'
    test_field = MODELS_GENERATOR.render_field('url', 'url')
    eq_(target_field, test_field)


@raises(GeneratorError)
def test_render_model_already_exists():
    MODELS_GENERATOR.render_model('PreExistingModel', [['foo', 'text']])


@raises(GeneratorError)
def test_render_model_already_exists_with_capitalization():
    MODELS_GENERATOR.render_model('preExistingModel', [['foo', 'text']])


@raises(GeneratorError)
def test_render_model_bad_field_args():
    MODELS_GENERATOR.render_model('BrandNewModel', ['doo', 'boop', 'bebop'])


def test_render_model_without_timestamps():
    test_model = MODELS_GENERATOR.render_model(
        'BrandNewModel', [['foo', 'text'],], add_timestamp=False)
    target_model = (u"""
class BrandNewModel(models.Model):
    foo = models.TextField()


    @models.permalink
    def get_absolute_url(self):
        return ('test_app_brandnewmodel_detail', (), {'pk': self.pk})
""", 'BrandNewModel')

    eq_(test_model, target_model)


# TODO - Should this raise an error?
# @raises(GeneratorError)
# def test_render_model_without_timestamps_or_fields():
#     MODELS_GENERATOR.render_model('BrandNewModel', [], add_timestamp=False)


def test_render_model_with_models_with_now():
    models_generator = ModelsGenerator('test_modelgen_with_models_with_now')
    fields = [['foo', 'text'],]
    test_model = models_generator.render_model('BrandNewModel', fields)
    target_model = (u"""
class BrandNewModel(models.Model):
    foo = models.TextField()
    created_at = models.DateTimeField(
        auto_now_add=True,
        default=now(),
        editable=False,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        default=now(),
        editable=False,
    )

    @models.permalink
    def get_absolute_url(self):
        return ('test_modelgen_with_models_with_now_brandnewmodel_detail', (), {'pk': self.pk})
""", 'BrandNewModel')

    eq_(test_model, target_model)


def test_render_model_with_models_without_now():
    models_generator = ModelsGenerator('test_modelgen_with_models_without_now')
    fields = [['foo', 'text'], ['bar', 'date'], ['biz', 'foreign', 'Blog']]
    test_model = models_generator.render_model('somemodel', fields)
    target_model = (u"""
from django.utils.timezone import now
class Somemodel(models.Model):
    foo = models.TextField()
    bar = models.DateField()
    biz = models.ForeignKey('Blog')
    created_at = models.DateTimeField(
        auto_now_add=True,
        default=now(),
        editable=False,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        default=now(),
        editable=False,
    )

    @models.permalink
    def get_absolute_url(self):
        return ('test_modelgen_with_models_without_now_somemodel_detail', (), {'pk': self.pk})
""", 'Somemodel')

    eq_(test_model, target_model)


def test_render_model_without_models_with_now():
    models_generator = ModelsGenerator('test_modelgen_without_models_with_now')
    fields = []
    test_model = models_generator.render_model('a', fields)
    target_model = (u"""
from django.db import models
class A(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True,
        default=now(),
        editable=False,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        default=now(),
        editable=False,
    )

    @models.permalink
    def get_absolute_url(self):
        return ('test_modelgen_without_models_with_now_a_detail', (), {'pk': self.pk})
""", 'A')

    eq_(test_model, target_model)


def test_render_model_without_models_without_now():
    models_generator = ModelsGenerator('test_modelgen_without_models_without_now')
    fields = [['a', 'bigint'],]
    test_model = models_generator.render_model('THISISALLCAPS', fields)
    target_model = (u"""
from django.db import models
from django.utils.timezone import now
class THISISALLCAPS(models.Model):
    a = models.BigIntegerField()
    created_at = models.DateTimeField(
        auto_now_add=True,
        default=now(),
        editable=False,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        default=now(),
        editable=False,
    )

    @models.permalink
    def get_absolute_url(self):
        return ('test_modelgen_without_models_without_now_thisisallcaps_detail', (), {'pk': self.pk})
""", 'THISISALLCAPS')

    eq_(test_model, target_model)

########NEW FILE########
__FILENAME__ = templates_tests
import os

from nose.tools import eq_

from generate_scaffold.generators import TemplatesGenerator
from test_app.models import PreExistingModel, PreExistingDatedModel


TEST_APP_NAME = 'test_app'
TEST_APP_DIR = __import__(TEST_APP_NAME).__path__[0]
TEST_APP_TPL_DIR = os.path.join(TEST_APP_DIR, 'templates', TEST_APP_NAME)
TEMPLATES_GENERATOR = TemplatesGenerator(TEST_APP_NAME)
TEST_MODEL = PreExistingModel()
TEST_MODEL_TPL_DIR = os.path.join(TEST_APP_TPL_DIR, 'preexistingmodel')
TEST_TIMESTAMPED_MODEL = PreExistingDatedModel()
TEST_TIMESTAMPED_MODEL_TPL_DIR = os.path.join(
    TEST_APP_TPL_DIR, 'preexistingdatedmodel')


def test_get_model_fields():
    fields = TEMPLATES_GENERATOR.get_model_fields(TEST_MODEL)
    target_fields = ['description']
    eq_(fields, target_fields)

    fields = TEMPLATES_GENERATOR.get_model_fields(TEST_TIMESTAMPED_MODEL)
    target_fields = ['created_at']
    eq_(fields, target_fields)


def test_render_templates_no_timestamp():
    template_tuples = list(TEMPLATES_GENERATOR.render_templates(
        TEST_MODEL, TEST_MODEL_TPL_DIR))

    filenames = sorted([os.path.basename(path)
        for path, tpl in template_tuples])
    target_filenames = sorted([
        'base.html',
        'preexistingmodel_confirm_delete.html',
        'preexistingmodel_detail.html',
        'preexistingmodel_form.html',
        'preexistingmodel_list.html',
        'object_table_detail.html',
        'object_table_list.html',
        'pagination.html'
    ])
    eq_(filenames, target_filenames)


def test_render_templates_with_timestamp():
    template_tuples = list(TEMPLATES_GENERATOR.render_templates(
        TEST_TIMESTAMPED_MODEL, TEST_TIMESTAMPED_MODEL_TPL_DIR))

    filenames = sorted([os.path.basename(path)
        for path, tpl in template_tuples])
    target_filenames = sorted([
        'base.html',
        'preexistingdatedmodel_archive.html',
        'preexistingdatedmodel_archive_day.html',
        'preexistingdatedmodel_archive_month.html',
        'preexistingdatedmodel_archive_week.html',
        'preexistingdatedmodel_archive_year.html',
        'preexistingdatedmodel_confirm_delete.html',
        'preexistingdatedmodel_detail.html',
        'preexistingdatedmodel_form.html',
        'preexistingdatedmodel_list.html',
        'object_table_detail.html',
        'object_table_list.html',
        'pagination.html'
    ])
    eq_(filenames, target_filenames)

########NEW FILE########
__FILENAME__ = urls_tests
from nose.tools import ok_, eq_, raises

from generate_scaffold.generators import UrlsGenerator, GeneratorError
from test_app.models import PreExistingModel, PreExistingDatedModel
from test_urlgen_with_urlpatterns.models import URLPreExistingDatedModel


TEST_APP_NAME = 'test_urlgen_no_urlpatterns'
URLS_GENERATOR = UrlsGenerator(TEST_APP_NAME)
DATED_MODEL = PreExistingDatedModel()
NON_DATED_MODEL = PreExistingModel()


@raises(GeneratorError)
def test_render_urls_no_module():
    urls_generator = UrlsGenerator('test_urlgen_without_urls')
    urls_generator.render_urls(NON_DATED_MODEL)


def test_render_urls_with_timestamp():
    test_urlpattern = URLS_GENERATOR.render_urls(DATED_MODEL)
    target_urlpattern = u"""

from test_urlgen_no_urlpatterns.views.preexistingdatedmodel_views import *
urlpatterns = patterns('',
    url(
        regex=r'^preexistingdatedmodel/archive/$',
        view=PreExistingDatedModelArchiveIndexView.as_view(),
        name='test_urlgen_no_urlpatterns_preexistingdatedmodel_archive_index'
    ),
    url(
        regex=r'^preexistingdatedmodel/create/$',
        view=PreExistingDatedModelCreateView.as_view(),
        name='test_urlgen_no_urlpatterns_preexistingdatedmodel_create'
    ),
    url(
        regex=r'^preexistingdatedmodel/(?P<year>\\d{4})/'
               '(?P<month>\\d{1,2})/'
               '(?P<day>\\d{1,2})/'
               '(?P<pk>\\d+?)/$',
        view=PreExistingDatedModelDateDetailView.as_view(),
        name='test_urlgen_no_urlpatterns_preexistingdatedmodel_date_detail'
    ),
    url(
        regex=r'^preexistingdatedmodel/archive/(?P<year>\\d{4})/'
               '(?P<month>\\d{1,2})/'
               '(?P<day>\\d{1,2})/$',
        view=PreExistingDatedModelDayArchiveView.as_view(),
        name='test_urlgen_no_urlpatterns_preexistingdatedmodel_day_archive'
    ),
    url(
        regex=r'^preexistingdatedmodel/(?P<pk>\\d+?)/delete/$',
        view=PreExistingDatedModelDeleteView.as_view(),
        name='test_urlgen_no_urlpatterns_preexistingdatedmodel_delete'
    ),
    url(
        regex=r'^preexistingdatedmodel/(?P<pk>\\d+?)/$',
        view=PreExistingDatedModelDetailView.as_view(),
        name='test_urlgen_no_urlpatterns_preexistingdatedmodel_detail'
    ),
    url(
        regex=r'^preexistingdatedmodel/$',
        view=PreExistingDatedModelListView.as_view(),
        name='test_urlgen_no_urlpatterns_preexistingdatedmodel_list'
    ),
    url(
        regex=r'^preexistingdatedmodel/archive/(?P<year>\\d{4})/'
               '(?P<month>\\d{1,2})/$',
        view=PreExistingDatedModelMonthArchiveView.as_view(),
        name='test_urlgen_no_urlpatterns_preexistingdatedmodel_month_archive'
    ),
    url(
        regex=r'^preexistingdatedmodel/today/$',
        view=PreExistingDatedModelTodayArchiveView.as_view(),
        name='test_urlgen_no_urlpatterns_preexistingdatedmodel_today_archive'
    ),
    url(
        regex=r'^preexistingdatedmodel/(?P<pk>\\d+?)/update/$',
        view=PreExistingDatedModelUpdateView.as_view(),
        name='test_urlgen_no_urlpatterns_preexistingdatedmodel_update'
    ),
    url(
        regex=r'^preexistingdatedmodel/archive/(?P<year>\\d{4})/'
               '(?P<month>\\d{1,2})/'
               'week/(?P<week>\\d{1,2})/$',
        view=PreExistingDatedModelWeekArchiveView.as_view(),
        name='test_urlgen_no_urlpatterns_preexistingdatedmodel_week_archive'
    ),
    url(
        regex=r'^preexistingdatedmodel/archive/(?P<year>\\d{4})/$',
        view=PreExistingDatedModelYearArchiveView.as_view(),
        name='test_urlgen_no_urlpatterns_preexistingdatedmodel_year_archive'
    ),
)
"""
    eq_(test_urlpattern, target_urlpattern)


# FIXME - Use regex to test. Whitespace in between urlpattern
#         definitions, for example, should not be tested.
def test_render_urls_without_timestamp():
    test_urlpattern = URLS_GENERATOR.render_urls(NON_DATED_MODEL)
    target_urlpattern = u"""

from test_urlgen_no_urlpatterns.views.preexistingmodel_views import *
urlpatterns = patterns('',

    url(
        regex=r'^preexistingmodel/create/$',
        view=PreExistingModelCreateView.as_view(),
        name='test_urlgen_no_urlpatterns_preexistingmodel_create'
    ),


    url(
        regex=r'^preexistingmodel/(?P<pk>\\d+?)/delete/$',
        view=PreExistingModelDeleteView.as_view(),
        name='test_urlgen_no_urlpatterns_preexistingmodel_delete'
    ),
    url(
        regex=r'^preexistingmodel/(?P<pk>\\d+?)/$',
        view=PreExistingModelDetailView.as_view(),
        name='test_urlgen_no_urlpatterns_preexistingmodel_detail'
    ),
    url(
        regex=r'^preexistingmodel/$',
        view=PreExistingModelListView.as_view(),
        name='test_urlgen_no_urlpatterns_preexistingmodel_list'
    ),


    url(
        regex=r'^preexistingmodel/(?P<pk>\\d+?)/update/$',
        view=PreExistingModelUpdateView.as_view(),
        name='test_urlgen_no_urlpatterns_preexistingmodel_update'
    ),


)
"""
    eq_(test_urlpattern, target_urlpattern)


def test_render_urls_with_urlpattern():
    model = URLPreExistingDatedModel()
    test_urlpattern = UrlsGenerator(
        'test_urlgen_with_urlpatterns').render_urls(model)
    target_match = "urlpatterns += patterns"

    ok_(target_match in test_urlpattern)

########NEW FILE########
__FILENAME__ = views_tests
from nose.tools import eq_, raises

from generate_scaffold.generators import ViewsGenerator, GeneratorError
from test_app.models import PreExistingModel, PreExistingDatedModel


TEST_APP_NAME = 'test_app'
VIEWS_GENERATOR = ViewsGenerator(TEST_APP_NAME)
TEST_MODEL = PreExistingModel()
TEST_TIMESTAMPED_MODEL = PreExistingDatedModel()


def test_render_views_no_timestamp():
    view = VIEWS_GENERATOR.render_views(TEST_MODEL)
    target_view = \
    '''from django.views.generic import ListView, DetailView, CreateView, \\
                                 DeleteView, UpdateView


from test_app.models import PreExistingModel


class PreExistingModelView(object):
    model = PreExistingModel

    def get_template_names(self):
        """Nest templates within preexistingmodel directory."""
        tpl = super(PreExistingModelView, self).get_template_names()[0]
        app = self.model._meta.app_label
        mdl = \'preexistingmodel\'
        self.template_name = tpl.replace(app, \'{0}/{1}\'.format(app, mdl))
        return [self.template_name]


class PreExistingModelBaseListView(PreExistingModelView):
    paginate_by = 10



class PreExistingModelCreateView(PreExistingModelView, CreateView):
    pass




class PreExistingModelDeleteView(PreExistingModelView, DeleteView):

    def get_success_url(self):
        from django.core.urlresolvers import reverse
        return reverse(\'test_app_preexistingmodel_list\')


class PreExistingModelDetailView(PreExistingModelView, DetailView):
    pass


class PreExistingModelListView(PreExistingModelBaseListView, ListView):
    pass




class PreExistingModelUpdateView(PreExistingModelView, UpdateView):
    pass





'''
    eq_(view, target_view)


@raises(GeneratorError)
def test_render_views_invalid_timestamp_field():
    VIEWS_GENERATOR.render_views(TEST_MODEL, 'created_at')


def test_render_timestamped_views_no_timestamp():
    view = VIEWS_GENERATOR.render_views(TEST_TIMESTAMPED_MODEL)
    target_view = \
    '''from django.views.generic import ListView, DetailView, CreateView, \\
                                 DeleteView, UpdateView, \\
                                 ArchiveIndexView, DateDetailView, \\
                                 DayArchiveView, MonthArchiveView, \\
                                 TodayArchiveView, WeekArchiveView, \\
                                 YearArchiveView


from test_app.models import PreExistingDatedModel


class PreExistingDatedModelView(object):
    model = PreExistingDatedModel

    def get_template_names(self):
        """Nest templates within preexistingdatedmodel directory."""
        tpl = super(PreExistingDatedModelView, self).get_template_names()[0]
        app = self.model._meta.app_label
        mdl = 'preexistingdatedmodel'
        self.template_name = tpl.replace(app, '{0}/{1}'.format(app, mdl))
        return [self.template_name]


class PreExistingDatedModelDateView(PreExistingDatedModelView):
    date_field = 'created_at'
    month_format = '%m'


class PreExistingDatedModelBaseListView(PreExistingDatedModelView):
    paginate_by = 10


class PreExistingDatedModelArchiveIndexView(
    PreExistingDatedModelDateView, PreExistingDatedModelBaseListView, ArchiveIndexView):
    pass


class PreExistingDatedModelCreateView(PreExistingDatedModelView, CreateView):
    pass


class PreExistingDatedModelDateDetailView(PreExistingDatedModelDateView, DateDetailView):
    pass


class PreExistingDatedModelDayArchiveView(
    PreExistingDatedModelDateView, PreExistingDatedModelBaseListView, DayArchiveView):
    pass


class PreExistingDatedModelDeleteView(PreExistingDatedModelView, DeleteView):

    def get_success_url(self):
        from django.core.urlresolvers import reverse
        return reverse('test_app_preexistingdatedmodel_list')


class PreExistingDatedModelDetailView(PreExistingDatedModelView, DetailView):
    pass


class PreExistingDatedModelListView(PreExistingDatedModelBaseListView, ListView):
    pass


class PreExistingDatedModelMonthArchiveView(
    PreExistingDatedModelDateView, PreExistingDatedModelBaseListView, MonthArchiveView):
    pass


class PreExistingDatedModelTodayArchiveView(
    PreExistingDatedModelDateView, PreExistingDatedModelBaseListView, TodayArchiveView):
    pass


class PreExistingDatedModelUpdateView(PreExistingDatedModelView, UpdateView):
    pass


class PreExistingDatedModelWeekArchiveView(
    PreExistingDatedModelDateView, PreExistingDatedModelBaseListView, WeekArchiveView):
    pass


class PreExistingDatedModelYearArchiveView(
    PreExistingDatedModelDateView, PreExistingDatedModelBaseListView, YearArchiveView):
    make_object_list = True



'''
    eq_(view, target_view)


def test_render_timestamped_views_with_timestamp():
    view = VIEWS_GENERATOR.render_views(TEST_TIMESTAMPED_MODEL, 'created_at')
    target_view = \
    '''from django.views.generic import ListView, DetailView, CreateView, \\
                                 DeleteView, UpdateView, \\
                                 ArchiveIndexView, DateDetailView, \\
                                 DayArchiveView, MonthArchiveView, \\
                                 TodayArchiveView, WeekArchiveView, \\
                                 YearArchiveView


from test_app.models import PreExistingDatedModel


class PreExistingDatedModelView(object):
    model = PreExistingDatedModel

    def get_template_names(self):
        """Nest templates within preexistingdatedmodel directory."""
        tpl = super(PreExistingDatedModelView, self).get_template_names()[0]
        app = self.model._meta.app_label
        mdl = 'preexistingdatedmodel'
        self.template_name = tpl.replace(app, '{0}/{1}'.format(app, mdl))
        return [self.template_name]


class PreExistingDatedModelDateView(PreExistingDatedModelView):
    date_field = 'created_at'
    month_format = '%m'


class PreExistingDatedModelBaseListView(PreExistingDatedModelView):
    paginate_by = 10


class PreExistingDatedModelArchiveIndexView(
    PreExistingDatedModelDateView, PreExistingDatedModelBaseListView, ArchiveIndexView):
    pass


class PreExistingDatedModelCreateView(PreExistingDatedModelView, CreateView):
    pass


class PreExistingDatedModelDateDetailView(PreExistingDatedModelDateView, DateDetailView):
    pass


class PreExistingDatedModelDayArchiveView(
    PreExistingDatedModelDateView, PreExistingDatedModelBaseListView, DayArchiveView):
    pass


class PreExistingDatedModelDeleteView(PreExistingDatedModelView, DeleteView):

    def get_success_url(self):
        from django.core.urlresolvers import reverse
        return reverse('test_app_preexistingdatedmodel_list')


class PreExistingDatedModelDetailView(PreExistingDatedModelView, DetailView):
    pass


class PreExistingDatedModelListView(PreExistingDatedModelBaseListView, ListView):
    pass


class PreExistingDatedModelMonthArchiveView(
    PreExistingDatedModelDateView, PreExistingDatedModelBaseListView, MonthArchiveView):
    pass


class PreExistingDatedModelTodayArchiveView(
    PreExistingDatedModelDateView, PreExistingDatedModelBaseListView, TodayArchiveView):
    pass


class PreExistingDatedModelUpdateView(PreExistingDatedModelView, UpdateView):
    pass


class PreExistingDatedModelWeekArchiveView(
    PreExistingDatedModelDateView, PreExistingDatedModelBaseListView, WeekArchiveView):
    pass


class PreExistingDatedModelYearArchiveView(
    PreExistingDatedModelDateView, PreExistingDatedModelBaseListView, YearArchiveView):
    make_object_list = True



'''
    eq_(view, target_view)

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python

from __future__ import print_function

import fileinput
import os
from os.path import dirname
import sys
import subprocess
import time


PROJECT_SETTINGS_ABSPATH = os.path.join(
    dirname(dirname(dirname(__file__))), 'test_project', 'settings.py')


def overwrite_project_language(lang_code):
    for line in fileinput.input(PROJECT_SETTINGS_ABSPATH, inplace=1):
        if line.startswith('LANGUAGE_CODE ='):
            print('LANGUAGE_CODE = \'{}\''.format(lang_code))
        else:
            print(line.strip('\n'))


def runtests():
    """Use generatescaffold to generate a model, then run the test
    suite, before finally cleaning up after generatescaffold. Exits
    with the status code of ./manage.py test."""

    app_abspath = os.path.dirname(os.path.dirname(__file__))
    models_abspath = os.path.join(app_abspath, 'models.py')
    models_exists = os.path.isfile(models_abspath)
    urls_abspath = os.path.join(app_abspath, 'urls.py')
    urls_exists = os.path.isfile(urls_abspath)
    views_abspath = os.path.join(app_abspath, 'views')
    views_exists = os.path.isdir(views_abspath)
    tpls_abspath = os.path.join(app_abspath, 'templates')
    tpls_exists = os.path.isdir(tpls_abspath)

    for f in [models_abspath, urls_abspath]:
        if os.path.isfile(f):
            subprocess.call('cp {} {}.orig'.format(f, f), shell=True)

    if views_exists:
        subprocess.call('cp -r {} {}.orig'.format(views_abspath, views_abspath), shell=True)

    if tpls_exists:
        subprocess.call('cp -r {} {}.orig'.format(tpls_abspath, tpls_abspath), shell=True)

    overwrite_project_language('ja')
    subprocess.call('python manage.py generatescaffold test_app I18nModel title:string', shell=True)
    time.sleep(1)
    overwrite_project_language('en-us')
    time.sleep(1)

    subprocess.call('python manage.py generatescaffold test_app GeneratedNoTimestampModel title:string description:text --no-timestamps', shell=True)
    time.sleep(2) # Give time for Django's AppCache to clear

    subprocess.call('python manage.py generatescaffold test_app GeneratedModel title:string description:text', shell=True)

    test_status = subprocess.call('python manage.py test --with-selenium --with-selenium-fixtures --with-cherrypyliveserver --noinput', shell=True)

    if models_exists:
        subprocess.call('mv {}.orig {}'.format(models_abspath, models_abspath), shell=True)
    else:
        subprocess.call('rm {}'.format(models_abspath), shell=True)

    if urls_exists:
        subprocess.call('mv {}.orig {}'.format(urls_abspath, urls_abspath), shell=True)
    else:
        subprocess.call('rm {}'.format(urls_abspath), shell=True)

    if views_exists:
        subprocess.call('rm -rf {}'.format(views_abspath), shell=True)
        subprocess.call('mv {}.orig {}'.format(views_abspath, views_abspath), shell=True)
    else:
        subprocess.call('rm -rf {}'.format(views_abspath), shell=True)

    if tpls_exists:
        subprocess.call('rm -rf {}'.format(tpls_abspath), shell=True)
        subprocess.call('mv {}.orig {}'.format(tpls_abspath, tpls_abspath), shell=True)
    else:
        subprocess.call('rm -rf {}'.format(tpls_abspath), shell=True)

    subprocess.call('rm {}/*.pyc'.format(app_abspath), shell=True)

    sys.exit(test_status)


if __name__ == '__main__':
    runtests()

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url


########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = models
from django.utils.timezone import now

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.timezone import now

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = settings
# Django settings for test_project project.

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
SELENIUM_DISPLAY = ':99.0'
LIVE_SERVER_PORT = 8000

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'test_app.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
        'TEST_NAME': 'test_app.test.db',
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
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

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
SECRET_KEY = '&amp;%qqycz+krd@izd)s54$-cs1t^lug6@4g1h^f^ycx7ya#8vb8-'

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
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'test_project.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'test_project.wsgi.application'

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
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'generate_scaffold',
    'django_nose',
    'test_app',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
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
from django.conf.urls import patterns, include, url

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
    url(r'^test_app/', include('test_app.urls')),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for test_project project.

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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_project.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.timezone import now


class URLPreExistingDatedModel(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True, default=now(), editable=False)

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url



########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.timezone import now


class URLPreExistingDatedModel(models.Model):
    created_at = models.DateTimeField(
        auto_now_add=True, default=now(), editable=False)

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url


urlpatterns = patterns('', )

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
