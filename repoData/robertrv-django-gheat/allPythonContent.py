__FILENAME__ = widgets
from django import forms
from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.text import truncate_words
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

    class Media:
        css = {
            'all': ('django_extensions/css/jquery.autocomplete.css',)
        }
        js = (
            'django_extensions/js/jquery.js',
            'django_extensions/js/jquery.bgiframe.min.js',
            'django_extensions/js/jquery.ajaxQueue.js',
            'django_extensions/js/jquery.autocomplete.js',
        )

    def label_for_value(self, value):
        key = self.rel.get_related_field().name
        obj = self.rel.to._default_manager.get(**{key: value})
        return truncate_words(obj, 14)

    def __init__(self, rel, search_fields, attrs=None):
        self.search_fields = search_fields
        super(ForeignKeySearchInput, self).__init__(rel, attrs)

    def render(self, name, value, attrs=None):
        if attrs is None:
            attrs = {}
        output = [super(ForeignKeySearchInput, self).render(name, value, attrs)]
        opts = self.rel.to._meta
        app_label = opts.app_label
        model_name = opts.object_name.lower()
        related_url = '../../../%s/%s/' % (app_label, model_name)
        params = self.url_parameters()
        if params:
            url = '?' + '&amp;'.join(['%s=%s' % (k, v) for k, v in params.items()])
        else:
            url = ''
        if not attrs.has_key('class'):
            attrs['class'] = 'vForeignKeyRawIdAdminField'
        # Call the TextInput render method directly to have more control
        output = [forms.TextInput.render(self, name, value, attrs)]
        if value:
            label = self.label_for_value(value)
        else:
            label = u''
        context = {
            'url': url,
            'related_url': related_url,
            'admin_media_prefix': settings.ADMIN_MEDIA_PREFIX,
            'search_path': self.search_path,
            'search_fields': ','.join(self.search_fields),
            'model_name': model_name,
            'app_label': app_label,
            'label': label,
            'name': name,
        }
        output.append(render_to_string(self.widget_template or (
            'django_extensions/widgets/%s/%s/foreignkey_searchinput.html' % (app_label, model_name),
            'django_extensions/widgets/%s/foreignkey_searchinput.html' % app_label,
            'django_extensions/widgets/foreignkey_searchinput.html',
        ), context))
        output.reverse()
        return mark_safe(u''.join(output))

########NEW FILE########
__FILENAME__ = models
"""
Django Extensions abstract base model classes.
"""

from django.db import models
from django_extensions.db.fields import ModificationDateTimeField, CreationDateTimeField

class TimeStampedModel(models.Model):
    """ TimeStampedModel
    An abstract base class model that provides self-managed "created" and
    "modified" fields.
    """
    created = CreationDateTimeField()
    modified = ModificationDateTimeField()
    
    class Meta:
        abstract = True

########NEW FILE########
__FILENAME__ = cache_cleanup
"""
Daily cleanup job.

Can be run as a cronjob to clean out old data from the database (only expired
sessions at the moment).
"""

from django_extensions.management.jobs import DailyJob

class Job(DailyJob):
    help = "Cache (db) cleanup Job"

    def execute(self):
	from django.conf import settings
	import os

	if settings.CACHE_BACKEND.startswith('db://'):
	    os.environ['TZ'] = settings.TIME_ZONE
	    table_name = settings.CACHE_BACKEND[5:]
	    cursor = connection.cursor()
	    cursor.execute("DELETE FROM %s WHERE %s < UTC_TIMESTAMP()" % \
		(backend.quote_name(table_name), backend.quote_name('expires')))
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
	# TODO: Remove the old way when Django 1.0 lands
	try:
	    # old way of doing cleanup (pre r7844 in svn)
	    from django.bin.daily_cleanup import clean_up
	    clean_up()
	except:
	    # new way using the management.call_command function
	    from django.core import management
	    management.call_command("cleanup")

########NEW FILE########
__FILENAME__ = color
"""
Sets up the terminal color scheme.
"""

from django.core.management import color
from django.utils import termcolors

def color_style():
    style = color.color_style()
    style.URL = termcolors.make_style(fg='green', opts=('bold',))
    style.MODULE = termcolors.make_style(fg='yellow')
    style.MODULE_NAME = termcolors.make_style(opts=('bold',))
    return style

########NEW FILE########
__FILENAME__ = clean_pyc
from django.core.management.base import NoArgsCommand
from django_extensions.management.utils import get_project_root
from random import choice
from optparse import make_option
from os.path import join as _j
import os

class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--optimize', '-o', '-O', action='store_true', dest='optimize', 
            help='Remove optimized python bytecode files'),
        make_option('--path', '-p', action='store', dest='path', 
            help='Specify path to recurse into'),
    )
    help = "Removes all python bytecode compiled files from the project."
    
    requires_model_validation = False
    
    def handle_noargs(self, **options):
	project_root = options.get("path", None)
	if not project_root:
    	    project_root = get_project_root()
	exts = options.get("optimize", False) and [".pyc", ".pyo"] or [".pyc"]
	verbose = int(options.get("verbosity", 1))>1

	for root, dirs, files in os.walk(project_root):
	    for file in files:
		ext = os.path.splitext(file)[1]
		if ext in exts:
		    full_path = _j(root, file)
		    if verbose:
			print full_path
		    os.remove(full_path)

# Backwards compatibility for Django r9110
if not [opt for opt in Command.option_list if opt.dest=='verbosity']:
    Command.option_list += (
	make_option('--verbosity', '-v', action="store", dest="verbosity",
	    default='1', type='choice', choices=['0', '1', '2'],
	    help="Verbosity level; 0=minimal output, 1=normal output, 2=all output"),
    )

########NEW FILE########
__FILENAME__ = compile_pyc
from django.core.management.base import NoArgsCommand
from django_extensions.management.utils import get_project_root
from random import choice
from optparse import make_option
from os.path import join as _j
import py_compile 
import os

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
    	    project_root = get_project_root()
	verbose = int(options.get("verbosity", 1))>1
	
	for root, dirs, files in os.walk(project_root):
	    for file in files:
		ext = os.path.splitext(file)[1]
		if ext==".py":
		    full_path = _j(root, file)
		    if verbose:
			print "%sc" % full_path
		    py_compile.compile(full_path)
		    

# Backwards compatibility for Django r9110
if not [opt for opt in Command.option_list if opt.dest=='verbosity']:
    Command.option_list += (
	make_option('--verbosity', '-v', action="store", dest="verbosity",
	    default='1', type='choice', choices=['0', '1', '2'],
	    help="Verbosity level; 0=minimal output, 1=normal output, 2=all output"),
    )

########NEW FILE########
__FILENAME__ = create_app
import os
import re
import django_extensions
from django.core.management.base import CommandError, LabelCommand, _make_writeable
from optparse import make_option

class Command(LabelCommand):
    option_list = LabelCommand.option_list + (
        make_option('--template', '-t', action='store', dest='app_template', 
            help='The path to the app template'),
        make_option('--parent_path', '-p', action='store', dest='parent_path', 
            help='The parent path of the app to be created'),
    )
    
    help = ("Creates a Django application directory structure based on the specified template directory.")
    args = "[appname]"
    label = 'application name'
    
    requires_model_validation = False
    can_import_settings = True
    
    def handle_label(self, label, **options):
        project_dir = os.getcwd()
        project_name = os.path.split(project_dir)[-1]
        app_name =label
        app_template = options.get('app_template') or os.path.join(django_extensions.__path__[0], 'conf', 'app_template')
        app_dir = os.path.join(options.get('parent_path') or project_dir, app_name)
                
        if not os.path.exists(app_template):
            raise CommandError("The template path, %r, does not exist." % app_template)
        
        if not re.search(r'^\w+$', label):
            raise CommandError("%r is not a valid application name. Please use only numbers, letters and underscores." % label)
        try:
            os.makedirs(app_dir)
        except OSError, e:
            raise CommandError(e)
        
        copy_template(app_template, app_dir, project_name, app_name)
        
def copy_template(app_template, copy_to, project_name, app_name):
    """copies the specified template directory to the copy_to location"""
    import shutil
    
    # walks the template structure and copies it
    for d, subdirs, files in os.walk(app_template):
        relative_dir = d[len(app_template)+1:]
        if relative_dir and not os.path.exists(os.path.join(copy_to, relative_dir)):
            os.mkdir(os.path.join(copy_to, relative_dir))
        for i, subdir in enumerate(subdirs):
            if subdir.startswith('.'):
                del subdirs[i]
        for f in files:
            if f.endswith('.pyc') or f.startswith('.DS_Store'):
                continue
            path_old = os.path.join(d, f)
            path_new = os.path.join(copy_to, relative_dir, f.replace('app_name', app_name))
            if os.path.exists(path_new):
                path_new = os.path.join(copy_to, relative_dir, f)
                if os.path.exists(path_new):
                    continue
            path_new = path_new.rstrip(".tmpl")
            fp_old = open(path_old, 'r')
            fp_new = open(path_new, 'w')
            fp_new.write(fp_old.read().replace('{{ app_name }}', app_name).replace('{{ project_name }}', project_name))
            fp_old.close()
            fp_new.close()
            try:
                shutil.copymode(path_old, path_new)
                _make_writeable(path_new)
            except OSError:
                sys.stderr.write(style.NOTICE("Notice: Couldn't set permission bits on %s. You're probably using an uncommon filesystem setup. No problem.\n" % path_new))

########NEW FILE########
__FILENAME__ = create_command
import os
from django.core.management.base import CommandError, AppCommand, _make_writeable
from optparse import make_option

class Command(AppCommand):
    option_list = AppCommand.option_list + (
        make_option('--name', '-n', action='store', dest='command_name', default='sample',
            help='The name to use for the management command'),
        make_option('--base', '-b', action='store', dest='base_command', default='Base',
            help='The base class used for implementation of this command. Should be one of Base, App, Label, or NoArgs'),
    )
    
    help = ("Creates a Django management command directory structure for the given app name"
            " in the current directory.")
    args = "[appname]"
    label = 'application name'

    requires_model_validation = False
    # Can't import settings during this command, because they haven't
    # necessarily been created.
    can_import_settings = True

    def handle_app(self, app, **options):
        directory = os.getcwd()
        app_name = app.__name__.split('.')[-2]
        project_dir = os.path.join(directory, app_name)
        if not os.path.exists(project_dir):
            try:
                os.mkdir(project_dir)
            except OSError, e:
                raise CommandError(e)
        
        copy_template('command_template', project_dir, options.get('command_name'), '%sCommand' % options.get('base_command'))
            
def copy_template(template_name, copy_to, command_name, base_command):
    """copies the specified template directory to the copy_to location"""
    import django_extensions
    import re
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
        relative_dir = d[len(template_dir)+1:]
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
                sys.stderr.write(style.NOTICE("Notice: Couldn't set permission bits on %s. You're probably using an uncommon filesystem setup. No problem.\n" % path_new))

########NEW FILE########
__FILENAME__ = create_jobs
import os
import sys
from django.core.management.base import CommandError, AppCommand, _make_writeable

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
    import re
    import shutil
    
    template_dir = os.path.join(django_extensions.__path__[0], 'conf', template_name)

    # walks the template structure and copies it
    for d, subdirs, files in os.walk(template_dir):
        relative_dir = d[len(template_dir)+1:]
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
                sys.stderr.write(style.NOTICE("Notice: Couldn't set permission bits on %s. You're probably using an uncommon filesystem setup. No problem.\n" % path_new))

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
        if fields and not f.name in fields:
            continue
        formfield = f.formfield()
        if not '__dict__' in dir(formfield):
            continue
        attrs = {}
        valid_fields = ['required', 'initial', 'max_length', 'min_length', 'max_value', 'min_value', 'max_digits', 'decimal_places', 'choices', 'help_text', 'label']
        for k,v in formfield.__dict__.items():
            if k in valid_fields and v != None:
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
        field_list.append('    %(field_name)s = forms.%(field_type)s(%(params)s)' % { 'field_name': f.name, 
                                                                                  'field_type': formfield.__class__.__name__, 
                                                                                  'params': params })
                                                                               
    return '''
from django import forms
from %(app_name)s.models import %(object_name)s
    
class %(object_name)sForm(forms.Form):
%(field_list)s
''' % { 'app_name': app_name, 'object_name': opts.object_name,  'field_list': '\n'.join(field_list) }

########NEW FILE########
__FILENAME__ = dumpscript
#!/usr/bin/env python
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
      populate script :)

Improvements:
    See TODOs and FIXMEs scattered throughout :-)

"""

import sys
from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.utils.encoding import smart_unicode, force_unicode
from django.contrib.contenttypes.models import ContentType

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
        print Script(models=models, context=context)


def get_models(app_labels):
    """ Gets a list of models for the given app labels, with some exceptions. 
        TODO: If a required model is referenced, it should also be included.
        Or at least discovered with a get_or_create() call.
    """

    from django.db.models import get_app, get_apps, get_model
    from django.db.models import get_models as get_all_models

    # These models are not to be output, e.g. because they can be generated automatically
    # TODO: This should be "appname.modelname" string
    from django.contrib.contenttypes.models import ContentType
    EXCLUDED_MODELS = (ContentType, )

    models = []

    # If no app labels are given, return all
    if not app_labels:
        for app in get_apps():
            models += [ m for m in get_all_models(app) if m not in EXCLUDED_MODELS ]

    # Get all relevant apps
    for app_label in app_labels:
        # If a specific model is mentioned, get only that model
        if "." in app_label:
            app_label, model_name = app_label.split(".", 1)
            models.append(get_model(app_label, model_name))
        # Get all models for a given app
        else:
            models += [ m for m in get_all_models(get_app(app_label)) if m not in EXCLUDED_MODELS ]

    return models



class Code(object):
    """ A snippet of python script. 
        This keeps track of import statements and can be output to a string.
        In the future, other features such as custom indentation might be included
        in this class.
    """

    def __init__(self):
        self.imports = {}
        self.indent = -1 

    def __str__(self):
        """ Returns a string representation of this script. 
        """
        if self.imports:
            sys.stderr.write(repr(self.import_lines))
            return flatten_blocks([""] + self.import_lines + [""] + self.lines, num_indents=self.indent)
        else:
            return flatten_blocks(self.lines, num_indents=self.indent)

    def get_import_lines(self):
        """ Takes the stored imports and converts them to lines
        """
        if self.imports:
            return [ "from %s import %s" % (value, key) for key, value in self.imports.items() ]
        else:
            return []
    import_lines = property(get_import_lines)


class ModelCode(Code):
    " Produces a python script that can recreate data for a given model class. "

    def __init__(self, model, context={}):
        self.model = model
        self.context = context
        self.instances = []
        self.indent = 0

    def get_imports(self):
        """ Returns a dictionary of import statements, with the variable being
            defined as the key. 
        """
        return { self.model.__name__: smart_unicode(self.model.__module__) }
    imports = property(get_imports)

    def get_lines(self):
        """ Returns a list of lists or strings, representing the code body. 
            Each list is a block, each string is a statement.
        """
        code = []

        for counter, item in enumerate(self.model.objects.all()):
            instance = InstanceCode(instance=item, id=counter+1, context=self.context)
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

    def __init__(self, instance, id, context={}):
        """ We need the instance in question and an id """

        self.instance = instance
        self.model = self.instance.__class__
        self.context = context
        self.variable_name = "%s_%s" % (self.instance._meta.db_table, id)
        self.skip_me = None
        self.instantiated = False

        self.indent  = 0 
        self.imports = {}

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
            code_lines.append("%s.save()\n" % (self.variable_name))

        code_lines += self.get_many_to_many_lines(force=force)

        return code_lines
    lines = property(get_lines)

    def skip(self):
        """ Determine whether or not this object should be skipped.
            If this model is a parent of a single subclassed instance, skip it.
            The subclassed instance will create this parent instance for us.

            TODO: Allow the user to force its creation?
        """

        if self.skip_me is not None:
            return self.skip_me

        try:
            # Django trunk since r7722 uses CollectedObjects instead of dict
            from django.db.models.query import CollectedObjects
            sub_objects = CollectedObjects()
        except ImportError:
            # previous versions don't have CollectedObjects
            sub_objects = {}
        self.instance._collect_sub_objects(sub_objects)
        if reduce(lambda x, y: x+y, [self.model in so._meta.parents for so in sub_objects.keys()]) == 1:
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
            except SkipValue, e:
                # Remove from the waiting list and move on
                self.waiting_list.remove(field)
                continue
            except DoLater, e:
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
                        value = "%s.objects.get(%s=%s)" % (rel_item._meta.object_name, pk_name, getattr(rel_item, pk_name))
                        lines.append('%s.%s.add(%s)' % (self.variable_name, field.name, value))
                        self.many_to_many_waiting_list[field].remove(rel_item)

        if lines:
            lines.append("")

        return lines


class Script(Code):
    " Produces a complete python script that can recreate data for the given apps. "

    def __init__(self, models, context={}):
        self.models = models
        self.context = context

        self.indent = -1 
        self.imports = {}

    def get_lines(self):
        """ Returns a list of lists or strings, representing the code body. 
            Each list is a block, each string is a statement.
        """
        code = [ self.FILE_HEADER.strip() ]

        # Queue and process the required models
        for model_class in queue_models(self.models, context=self.context):
            sys.stderr.write('Processing model: %s\n' % model_class.model.__name__)
            code.append(model_class.import_lines)
            code.append("")
            code.append(model_class.lines)

        # Process left over foreign keys from cyclic models
        for model in self.models:
            sys.stderr.write('Re-processing model: %s\n' % model.model.__name__)
            for instance in model.instances:
                if instance.waiting_list or instance.many_to_many_waiting_list:
                    code.append(instance.get_lines(force=True))

        return code

    lines = property(get_lines)

    # A user-friendly file header
    FILE_HEADER = """

#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file has been automatically generated, changes may be lost if you
# go and generate it again. It was generated with the following command:
# %s

import datetime
from decimal import Decimal
from django.contrib.contenttypes.models import ContentType

def run():

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
    if isinstance(lines, basestring):
        return INDENTATION * num_indents + lines

    # If this is not a string, join the lines and recurse
    return "\n".join([ flatten_blocks(line, num_indents+1) for line in lines ])




def get_attribute_value(item, field, context, force=False):
    """ Gets a string version of the given attribute's value, like repr() might. """

    # Find the value of the field, catching any database issues
    try:
        value = getattr(item, field.name)
    except ObjectDoesNotExist:
        raise SkipValue('Could not find object for %s.%s, ignoring.\n' % (item.__class__.__name__, field.name))

    # AutoField: We don't include the auto fields, they'll be automatically recreated
    if isinstance(field, models.AutoField):
        raise SkipValue()

    # Some databases (eg MySQL) might store boolean values as 0/1, this needs to be cast as a bool
    elif isinstance(field, models.BooleanField) and value is not None:
        return repr(bool(value))

    # Post file-storage-refactor, repr() on File/ImageFields no longer returns the path
    elif isinstance(field, models.FileField):
        return repr(force_unicode(value))

    # ForeignKey fields, link directly using our stored python variable name
    elif isinstance(field, models.ForeignKey) and value is not None:

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
        elif force:
            return "%s.objects.get(%s=%s)" % (value._meta.object_name, pk_name, getattr(value, pk_name))
        else:
            raise DoLater('(FK) %s.%s\n' % (item.__class__.__name__, field.name))


    # A normal field (e.g. a python built-in)
    else:
        return repr(value)

def queue_models(models, context):
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
        if check_dependencies(model, model_queue):
            model_class = ModelCode(model=model, context=context)
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
                missing_models = [ ModelCode(model=m, context=context) for m in models ]
                model_queue += missing_models
                # Replace the models with the model class objects 
                # (sure, this is a little bit of hackery)
                models[:] = missing_models
                break
        else:
            allowed_cycles = MAX_CYCLES

    return model_queue


def check_dependencies(model, model_queue):
    " Check that all the depenedencies for this model are already in the queue. "

    # A list of allowed links: existing fields, itself and the special case ContentType
    allowed_links = [ m.model.__name__ for m in model_queue ] + [model.__name__, 'ContentType']

    # For each ForeignKey or ManyToMany field, check that a link is possible
    for field in model._meta.fields + model._meta.many_to_many:
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
from django.contrib.auth.models import User, Group
from optparse import make_option
from sys import stdout
from csv import writer

FORMATS = [
    'address',
    'google',
    'outlook',
    'linkedin',
    'vcard',
]

def full_name(first_name, last_name, username, **extra):
    name = u" ".join(n for n in [first_name, last_name] if n)
    if not name: return username
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
    encoding = 'utf-8' # RED_FLAG: add as an option -DougN

    def handle(self, *args, **options):
        if len(args) > 1:
            raise CommandError("extra arguments supplied")
        group = options['group']
        if group and not Group.objects.filter(name=group).count()==1:
            names = u"', '".join(g['name'] for g in Group.objects.values('name')).encode('utf-8')
            if names: names = "'" + names + "'."
            raise CommandError("Unknown group '" + group + "'. Valid group names are: " + names)
        if len(args) and args[0] != '-':
            outfile = file(args[0], 'w')
        else:
            outfile = stdout

        qs = User.objects.all().order_by('last_name', 'first_name', 'username', 'email')
        if group: qs = qs.filter(group__name=group).distinct()
        qs = qs.values('last_name', 'first_name', 'username', 'email')
        getattr(self, options['format'])(qs, outfile)

    def address(self, qs, out):
        """simple single entry per line in the format of:
            "full name" <my@address.com>;
        """
        out.write(u"\n".join(u'"%s" <%s>;' % (full_name(**ent), ent['email']) 
                             for ent in qs).encode(self.encoding))
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
        columns = ['Name','E-mail Address','Notes','E-mail 2 Address','E-mail 3 Address',
                   'Mobile Phone','Pager','Company','Job Title','Home Phone','Home Phone 2',
                   'Home Fax','Home Address','Business Phone','Business Phone 2',
                   'Business Fax','Business Address','Other Phone','Other Fax','Other Address']
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
            print self.style.ERROR_OUTPUT("Please install python-vobject to use the vcard export format.")
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
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from django_extensions.management.modelviz import generate_dot

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--disable-fields', '-d', action='store_true', dest='disable_fields',
            help='Do not show the class member fields'),
        make_option('--group-models', '-g', action='store_true', dest='group_models',
            help='Group models together respective to there application'),
        make_option('--all-applications', '-a', action='store_true', dest='all_applications',
            help='Automaticly include all applications from INSTALLED_APPS'),
        make_option('--output', '-o', action='store', dest='outputfile',
            help='Render output file. Type of output dependend on file extensions. Use png or jpg to render graph to image.'),
        make_option('--layout', '-l', action='store', dest='layout', default='dot',
            help='Layout to be used by GraphViz for visualization. Layouts: circo dot fdp neato nop nop1 nop2 twopi'),
    )

    help = ("Creates a GraphViz dot file for the specified app names.  You can pass multiple app names and they will all be combined into a single model.  Output is usually directed to a dot file.")
    args = "[appname]"
    label = 'application name'

    requires_model_validation = True
    can_import_settings = True

    def handle(self, *args, **options):
        if len(args) < 1 and not options['all_applications']:
            raise CommandError("need one or more arguments for appname")

        dotdata = generate_dot(args, **options)
        if options['outputfile']:
            self.render_output(dotdata, **options)
        else:
            self.print_output(dotdata)

    def print_output(self, dotdata):
        print dotdata

    def render_output(self, dotdata, **kwargs):
        try:
            import pygraphviz
        except ImportError, e:
            raise CommandError("need pygraphviz python module ( apt-get install python-pygraphviz )")

        vizdata = ' '.join(dotdata.split("\n")).strip()
	version = pygraphviz.__version__.rstrip("-svn")
	try:
	    if [int(v) for v in version.split('.')]<(0,36):
                # HACK around old/broken AGraph before version 0.36 (ubuntu ships with this old version)
                import tempfile
                tmpfile = tempfile.NamedTemporaryFile()
                tmpfile.write(vizdata)
                tmpfile.seek(0)
                vizdata = tmpfile.name
	except ValueError:
	    pass

        graph = pygraphviz.AGraph(vizdata)
        graph.layout(prog=kwargs['layout'])
        graph.draw(kwargs['outputfile'])

########NEW FILE########
__FILENAME__ = mail_debug
from django.core.management.base import BaseCommand
import sys
import smtpd
import asyncore

class Command(BaseCommand):
    help = "Starts a test mail server for development."
    args = '[optional port number or ippaddr:port]'

    requires_model_validation = False

    def handle(self, addrport='', *args, **options):
        if args:
            raise CommandError('Usage is runserver %s' % self.args)
        if not addrport:
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

        quit_command = (sys.platform == 'win32') and 'CTRL-BREAK' or 'CONTROL-C'

        def inner_run():
            print "Now accepting mail at %s:%s" % (addr, port)
            server = smtpd.DebuggingServer((addr,port), None)
            asyncore.loop()

        try: 
            inner_run()
        except KeyboardInterrupt:
            pass

########NEW FILE########
__FILENAME__ = passwd
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
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

        try:
            u = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError("user %s does not exist" % username)

        print "Changing password for user", u.username
        p1 = p2 = ""
        while "" in (p1, p2) or p1 != p2:
            p1 = getpass.getpass()
            p2 = getpass.getpass("Password (again): ")
            if p1 != p2:
                print "Passwords do not match, try again"
            elif "" in (p1, p2):
                raise CommandError("aborted")

        u.set_password(p1)
        u.save()

        return "Password changed successfully for user", u.username

########NEW FILE########
__FILENAME__ = print_user_for_session
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
import re

SESSION_RE = re.compile("^[0-9a-f]{20,40}$")

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
        if not SESSION_RE.match(key):
            raise CommandError("malformed session key")
        try:
            session = Session.objects.get(pk=key)
        except Session.DoesNotExist:
            print "Session Key does not exist. Expired?"
            return

        data = session.get_decoded()
        print 'Session to Expire:', session.expire_date
        print 'Raw Data:', data
        uid = data.get('_auth_user_id', None)
        if uid is None:
            print 'No user associated with session'
            return
        print "User id:", uid
        try:
            user = User.objects.get(pk=uid)
        except User.DoesNotExist:
            print "No user associated with that id."
            return
        for key in ['username', 'email', 'first_name', 'last_name']:
            print key+': ' + getattr(user, key)




########NEW FILE########
__FILENAME__ = reset_db
"""
originally from http://www.djangosnippets.org/snippets/828/ by dnordberg

"""


from django.conf import settings
from django.core.management.base import CommandError, BaseCommand
from django.db import connection
import logging
from optparse import make_option
        
class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--noinput', action='store_false',
                    dest='interactive', default=True,
                    help='Tells Django to NOT prompt the user for input of any kind.'),
        make_option('--no-utf8', action='store_true',
                    dest='no_utf8_support', default=False,
                    help='Tells Django to not create a UTF-8 charset database'),
    )
    help = "Resets the database for this project."

    def handle(self, *args, **options):
        """
        Resets the database for this project.
    
        Note: Transaction wrappers are in reverse as a work around for
        autocommit, anybody know how to do this the right way?
        """

        if options.get('interactive'):
            confirm = raw_input("""
You have requested a database reset.
This will IRREVERSIBLY DESTROY
ALL data in the database "%s".
Are you sure you want to do this?

Type 'yes' to continue, or 'no' to cancel: """ % (settings.DATABASE_NAME,))
        else:
            confirm = 'yes'

        if confirm != 'yes':
            print "Reset cancelled."
            return

        engine = settings.DATABASE_ENGINE
    
        if engine == 'sqlite3':
            import os
            try:
                logging.info("Unlinking sqlite3 database")
                os.unlink(settings.DATABASE_NAME)
            except OSError:
                pass
        elif engine == 'mysql':
            import MySQLdb as Database
            kwargs = {
                'user': settings.DATABASE_USER,
                'passwd': settings.DATABASE_PASSWORD,
            }
            if settings.DATABASE_HOST.startswith('/'):
                kwargs['unix_socket'] = settings.DATABASE_HOST
            else:
                kwargs['host'] = settings.DATABASE_HOST
            if settings.DATABASE_PORT:
                kwargs['port'] = int(settings.DATABASE_PORT)
            connection = Database.connect(**kwargs)
            drop_query = 'DROP DATABASE IF EXISTS %s' % settings.DATABASE_NAME
            utf8_support = options.get('no_utf8_support', False) and '' or 'CHARACTER SET utf8'
            create_query = 'CREATE DATABASE %s %s' % (settings.DATABASE_NAME, utf8_support)
            logging.info('Executing... "' + drop_query + '"')
            connection.query(drop_query)
            logging.info('Executing... "' + create_query + '"')
            connection.query(create_query)
        elif engine == 'postgresql' or engine == 'postgresql_psycopg2':
            if engine == 'postgresql':
                import psycopg as Database
            elif engine == 'postgresql_psycopg2':
                import psycopg2 as Database
    
            if settings.DATABASE_NAME == '':
                from django.core.exceptions import ImproperlyConfigured
                raise ImproperlyConfigured, "You need to specify DATABASE_NAME in your Django settings file."
            if settings.DATABASE_USER:
                conn_string = "user=%s" % (settings.DATABASE_USER)
            if settings.DATABASE_PASSWORD:
                conn_string += " password='%s'" % settings.DATABASE_PASSWORD
            if settings.DATABASE_HOST:
                conn_string += " host=%s" % settings.DATABASE_HOST
            if settings.DATABASE_PORT:
                conn_string += " port=%s" % settings.DATABASE_PORT
            connection = Database.connect(conn_string)
            connection.set_isolation_level(0) #autocommit false
            cursor = connection.cursor()
            drop_query = 'DROP DATABASE %s' % settings.DATABASE_NAME
            logging.info('Executing... "' + drop_query + '"')
    
            try:
                cursor.execute(drop_query)
            except Database.ProgrammingError, e:
                logging.info("Error: "+str(e))
    
            # Encoding should be SQL_ASCII (7-bit postgres default) or prefered UTF8 (8-bit)
            create_query = ("""
CREATE DATABASE %s
    WITH OWNER = %s
        ENCODING = 'UTF8'
        TABLESPACE = pg_default;
""" % (settings.DATABASE_NAME, settings.DATABASE_USER))
            logging.info('Executing... "' + create_query + '"')
            cursor.execute(create_query)
    
        else:
            raise CommandError, "Unknown database engine %s", engine
    
        print "Reset successful."

########NEW FILE########
__FILENAME__ = runjob
from django.core.management.base import LabelCommand
from optparse import make_option
from django_extensions.management.jobs import get_job, print_jobs

class Command(LabelCommand):
    option_list = LabelCommand.option_list + (
        make_option('--list', '-l', action="store_true", dest="list_jobs",
            help="List all jobs with there description"),
    )
    help = "Run a single maintenance job."
    args = "[app_name] job_name"
    label = ""
    
    requires_model_validation = True

    def runjob(self, app_name, job_name, options):
        verbosity = int(options.get('verbosity', 1))
        if verbosity>1:
            print "Executing job: %s (app: %s)" % (job_name, app_name)
        try:
            job = get_job(app_name, job_name)
        except KeyError, e:
            if app_name:
                print "Error: Job %s for applabel %s not found" % (app_name, job_name)
            else:
                print "Error: Job %s not found" % job_name
            print "Use -l option to view all the available jobs"
            return
        try:
            job().execute()
        except Exception, e:
            import traceback
            print "ERROR OCCURED IN JOB: %s (APP: %s)" % (job_name, app_name)
            print "START TRACEBACK:"
            traceback.print_exc()
            print "END TRACEBACK\n"
    
    def handle(self, *args, **options):
        app_name = None
        job_name = None
        if len(args)==1:
            job_name = args[0]
        elif len(args)==2:
            app_name, job_name = args
        if options.get('list_jobs'):
            print_jobs(only_scheduled=False, show_when=True, show_appname=True)
        else:
            if not job_name:
                print "Run a single maintenance job. Please specify the name of the job."
                return
            self.runjob(app_name, job_name, options)

# Backwards compatibility for Django r9110
if not [opt for opt in Command.option_list if opt.dest=='verbosity']:
    Command.option_list += (
	make_option('--verbosity', '-v', action="store", dest="verbosity",
	    default='1', type='choice', choices=['0', '1', '2'],
	    help="Verbosity level; 0=minimal output, 1=normal output, 2=all output"),
    )

########NEW FILE########
__FILENAME__ = runjobs
from django.core.management.base import LabelCommand
from optparse import make_option
from django_extensions.management.jobs import get_jobs, print_jobs

class Command(LabelCommand):
    option_list = LabelCommand.option_list + (
        make_option('--list', '-l', action="store_true", dest="list_jobs",
            help="List all jobs with there description"),
    )
    help = "Runs scheduled maintenance jobs."
    args = "[hourly daily weekly monthly]"
    label = ""

    requires_model_validation = True

    def usage_msg(self):
        print "Run scheduled jobs. Please specify 'hourly', 'daily', 'weekly' or 'monthly'"

    def runjobs(self, when, options):
        verbosity = int(options.get('verbosity', 1))
        jobs = get_jobs(when, only_scheduled=True)
        list = jobs.keys()
        list.sort()
        for app_name, job_name in list:
            job = jobs[(app_name, job_name)]
            if verbosity>1:
                print "Executing %s job: %s (app: %s)" % (when, job_name, app_name)
            try:
                job().execute()
            except Exception, e:
                import traceback
                print "ERROR OCCURED IN %s JOB: %s (APP: %s)" % (when.upper(), job_name, app_name)
                print "START TRACEBACK:"
                traceback.print_exc()
                print "END TRACEBACK\n"

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
            if verbosity>1:
                app_name = '.'.join(app.__name__.rsplit('.')[:-1])
                print "Sending %s job signal for: %s" % (when, app_name)
            if when == 'hourly':
                signals.run_hourly_jobs.send(sender=app, app=app)
            elif when == 'daily':
                signals.run_daily_jobs.send(sender=app, app=app)
            elif when == 'weekly':
                signals.run_weekly_jobs.send(sender=app, app=app)
            elif when == 'monthly':
                signals.run_monthly_jobs.send(sender=app, app=app)

    def handle(self, *args, **options):
        when = None
        if len(args)>1:
            self.usage_msg()
            return
        elif len(args)==1:
            if not args[0] in ['hourly', 'daily', 'weekly', 'monthly']:
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

# Backwards compatibility for Django r9110
if not [opt for opt in Command.option_list if opt.dest=='verbosity']:
    Command.option_list += (
	make_option('--verbosity', '-v', action="store", dest="verbosity",
	    default='1', type='choice', choices=['0', '1', '2'],
	    help="Verbosity level; 0=minimal output, 1=normal output, 2=all output"),
    )

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
import os
import sys

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
        print >> out_file, 'events: Ticks'
        self._print_summary()
        for entry in self.data:
            self._entry(entry)

    def _print_summary(self):
        max_cost = 0
        for entry in self.data:
            totaltime = int(entry.totaltime * 1000)
            max_cost = max(max_cost, totaltime)
        print >> self.out_file, 'summary: %d' % (max_cost,)

    def _entry(self, entry):
        out_file = self.out_file

        code = entry.code
        #print >> out_file, 'ob=%s' % (code.co_filename,)
        if isinstance(code, str):
            print >> out_file, 'fi=~'
        else:
            print >> out_file, 'fi=%s' % (code.co_filename,)
        print >> out_file, 'fn=%s' % (label(code),)

        inlinetime = int(entry.inlinetime * 1000)
        if isinstance(code, str):
            print >> out_file, '0 ', inlinetime
        else:
            print >> out_file, '%d %d' % (code.co_firstlineno, inlinetime)

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
        print >> out_file

    def _subentry(self, lineno, subentry):
        out_file = self.out_file
        code = subentry.code
        #print >> out_file, 'cob=%s' % (code.co_filename,)
        print >> out_file, 'cfn=%s' % (label(code),)
        if isinstance(code, str):
            print >> out_file, 'cfi=~'
            print >> out_file, 'calls=%d 0' % (subentry.callcount,)
        else:
            print >> out_file, 'cfi=%s' % (code.co_filename,)
            print >> out_file, 'calls=%d %d' % (
                subentry.callcount, code.co_firstlineno)

        totaltime = int(subentry.totaltime * 1000)
        print >> out_file, '%d %d' % (lineno, totaltime)

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--noreload', action='store_false', dest='use_reloader', default=True,
            help='Tells Django to NOT use the auto-reloader.'),
        make_option('--adminmedia', dest='admin_media_path', default='',
            help='Specifies the directory from which to serve admin media.'),
        make_option('--prof-path', dest='prof_path', default='/tmp',
            help='Specifies the directory which to save profile information in.'),
        make_option('--nomedia', action='store_true', dest='no_media', default=False,
            help='Do not profile MEDIA_URL and ADMIN_MEDIA_URL'),
        make_option('--use-cprofile', action='store_true', dest='use_cprofile', default=False,
            help='Use cProfile if available, this is disabled per default because of incompatibilities.'),
        make_option('--kcachegrind', action='store_true', dest='use_lsprof', default=False,
            help='Create kcachegrind compatible lsprof files, this requires and automatically enables cProfile.'),
    )
    help = "Starts a lightweight Web server with profiling enabled."
    args = '[optional port number, or ipaddr:port]'

    # Validation is called explicitly each time the server is reloaded.
    requires_model_validation = False

    def handle(self, addrport='', *args, **options):
        import django
        from django.core.servers.basehttp import run, AdminMediaHandler, WSGIServerException
        from django.core.handlers.wsgi import WSGIHandler
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
        admin_media_path = options.get('admin_media_path', '')
        shutdown_message = options.get('shutdown_message', '')
        no_media = options.get('no_media', False)
        quit_command = (sys.platform == 'win32') and 'CTRL-BREAK' or 'CONTROL-C'

        def inner_run():
            from django.conf import settings

            import hotshot, time, os
            USE_CPROFILE = options.get('use_cprofile', False)
            USE_LSPROF = options.get('use_lsprof', False)
            if USE_LSPROF:
               USE_CPROFILE = True
            if USE_CPROFILE:
                try:
                    import cProfile
                    USE_CPROFILE = True
                except ImportError:
                    print "cProfile disabled, module cannot be imported!"
                    USE_CPROFILE = False
            if USE_LSPROF and not USE_CPROFILE:
        	raise SystemExit("Kcachegrind compatible output format required cProfile from Python 2.5")
            prof_path = options.get('prof_path', '/tmp')
            def make_profiler_handler(inner_handler):
                def handler(environ, start_response):
                    path_info = environ['PATH_INFO']
                    # normally /media/ is MEDIA_URL, but in case still check it in case it's differently
                    # should be hardly a penalty since it's an OR expression.
                    # TODO: fix this to check the configuration settings and not make assumpsions about where media are on the url
                    if no_media and (path_info.startswith('/media') or path_info.startswith(settings.MEDIA_URL)):
                        return inner_handler(environ, start_response)
                    path_name = path_info.strip("/").replace('/', '.') or "root"
                    profname = "%s.%.3f.prof" % (path_name, time.time())
                    profname = os.path.join(prof_path, profname)
                    if USE_CPROFILE:
                        prof = cProfile.Profile()
                    else:
                        prof = hotshot.Profile(profname)
                    try:
                        return prof.runcall(inner_handler, environ, start_response)
                    finally:
                        if USE_LSPROF:
                            kg = KCacheGrind(prof)
                            kg.output(file(profname, 'w'))
                        elif USE_CPROFILE:
                            prof.dump_stats(profname)
                return handler

            print "Validating models..."
            self.validate(display_num_errors=True)
            print "\nDjango version %s, using settings %r" % (django.get_version(), settings.SETTINGS_MODULE)
            print "Development server is running at http://%s:%s/" % (addr, port)
            print "Quit the server with %s." % quit_command
            try:
                path = admin_media_path or django.__path__[0] + '/contrib/admin/media'
                handler = make_profiler_handler(AdminMediaHandler(WSGIHandler(), path))
                run(addr, int(port), handler)
            except WSGIServerException, e:
                # Use helpful error messages instead of ugly tracebacks.
                ERRORS = {
                    13: "You don't have permission to access that port.",
                    98: "That port is already in use.",
                    99: "That IP address can't be assigned-to.",
                }
                try:
                    error_text = ERRORS[e.args[0].args[0]]
                except (AttributeError, KeyError):
                    error_text = str(e)
                sys.stderr.write(self.style.ERROR("Error: %s" % error_text) + '\n')
                # Need to use an OS exit because sys.exit doesn't work in a thread
                os._exit(1)
            except KeyboardInterrupt:
                if shutdown_message:
                    print shutdown_message
                sys.exit(0)
        if use_reloader:
            from django.utils import autoreload
            autoreload.main(inner_run)
        else:
            inner_run()

########NEW FILE########
__FILENAME__ = runscript
from django.core.management.base import BaseCommand
from django.core.management.color import no_style
from optparse import make_option
import sys
import os

try:
    set
except NameError:
    from sets import Set as set   # Python 2.3 fallback

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--fixtures', action='store_true', dest='infixtures', default=False,
            help='Only look in app.fixtures subdir'),
        make_option('--noscripts', action='store_true', dest='noscripts', default=False,
            help='Look in app.scripts subdir'),
    )
    help = 'Runs a script in django context.'
    args = "script [script ...]"

    def handle(self, *scripts, **options):
        from django.db.models import get_apps

        subdirs = []

        if not options.get('noscripts'):
            subdirs.append('scripts')
        if options.get('infixtures'):
            subdirs.append('fixtures')
        verbosity = int(options.get('verbosity', 1))
        show_traceback = options.get('traceback', False)

        if len(subdirs) < 1:
            print "No subdirs to run left."
            return

        if len(scripts) < 1:
            print "Script name required."
            return

        def run_script(name):
            if verbosity > 1:
                print "check for %s" % name
            try:
                t = __import__(name, [], [], [" "])

                if verbosity > 0:
                    print "Found script %s ..." %name
                if hasattr(t, "run"):
                    if verbosity > 1:
                        print "found run() in %s. executing..." % name
                    # TODO: add arguments to run
                    try:
                        t.run()
                    except Exception, e:
                        if verbosity > 0:
                            print "Exception while running run() in %s" %name
                        if show_traceback:
                            raise
                else:
                    if verbosity > 1:
                        print "no run() function found."
                    
            except ImportError:
                pass


        for app in get_apps():
            app_name = app.__name__.split(".")[:-1] # + ['fixtures']

            for subdir in subdirs:
                for script in scripts:
                    run_script(".".join(app_name + [subdir, script]))

        # try app.DIR.script import
        for script in scripts:
            sa = script.split(".")
            for subdir in subdirs:
                nn = ".".join(sa[:-1] + [subdir, sa[-1]])
                run_script(nn)

            # try direct import
            if script.find(".") != -1:
                run_script(script)



# Backwards compatibility for Django r9110
if not [opt for opt in Command.option_list if opt.dest=='verbosity']:
    Command.option_list += (
	make_option('--verbosity', '-v', action="store", dest="verbosity",
	    default='1', type='choice', choices=['0', '1', '2'],
	    help="Verbosity level; 0=minimal output, 1=normal output, 2=all output"),
    )

########NEW FILE########
__FILENAME__ = runserver_plus
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import os
import sys

def null_technical_500_response(request, exc_type, exc_value, tb):
    raise exc_type, exc_value, tb

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--noreload', action='store_false', dest='use_reloader', default=True,
            help='Tells Django to NOT use the auto-reloader.'),
        make_option('--browser', action='store_true', dest='open_browser',
            help='Tells Django to open a browser.'),
        make_option('--adminmedia', dest='admin_media_path', default='',
            help='Specifies the directory from which to serve admin media.'),
    )
    help = "Starts a lightweight Web server for development."
    args = '[optional port number, or ipaddr:port]'

    # Validation is called explicitly each time the server is reloaded.
    requires_model_validation = False

    def handle(self, addrport='', *args, **options):
        import django
        from django.core.servers.basehttp import run, AdminMediaHandler, WSGIServerException
        from django.core.handlers.wsgi import WSGIHandler
        try:
            from werkzeug import run_simple, DebuggedApplication
        except:
            raise CommandError("Werkzeug is required to use runserver_plus.  Please visit http://werkzeug.pocoo.org/download")

        # usurp django's handler
        from django.views import debug
        debug.technical_500_response = null_technical_500_response

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
        open_browser = options.get('open_browser', False)
        admin_media_path = options.get('admin_media_path', '')
        shutdown_message = options.get('shutdown_message', '')
        quit_command = (sys.platform == 'win32') and 'CTRL-BREAK' or 'CONTROL-C'

        def inner_run():
            from django.conf import settings
            print "Validating models..."
            self.validate(display_num_errors=True)
            print "\nDjango version %s, using settings %r" % (django.get_version(), settings.SETTINGS_MODULE)
            print "Development server is running at http://%s:%s/" % (addr, port)
            print "Using the Werkzeug debugger (http://werkzeug.pocoo.org/)"
            print "Quit the server with %s." % quit_command
            path = admin_media_path or django.__path__[0] + '/contrib/admin/media'
            handler = AdminMediaHandler(WSGIHandler(), path)
            if open_browser:
                import webbrowser
                url = "http://%s:%s/" % (addr, port)
                webbrowser.open(url)
            run_simple(addr, int(port), DebuggedApplication(handler, True), 
                       use_reloader=use_reloader, use_debugger=True)            
        inner_run()

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
            
        from django.contrib.auth.models import User, Group
        email = options.get('default_email', DEFAULT_FAKE_EMAIL)
        include_regexp = options.get('include_regexp', None)
        exclude_regexp = options.get('exclude_regexp', None)
        include_groups = options.get('include_groups', None)
        exclude_groups = options.get('exclude_groups', None)
        no_admin = options.get('no_admin', False)
        no_staff = options.get('no_staff', False)
        
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
            
        print 'Changed %d emails' % users.count()

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
            
        from django.contrib.auth.models import User
        if options.get('prompt_passwd', False):
            from getpass import getpass
            passwd = getpass('Password: ')
            if not passwd:
                raise CommandError('You must enter a valid password')
        else:
            passwd = options.get('default_passwd', DEFAULT_FAKE_PASSWORD)
        
        users = User.objects.all()
        for user in users:
            user.set_password(passwd)
            user.save()
            
        print 'Reset %d passwords' % users.count()

########NEW FILE########
__FILENAME__ = shell_plus
import os
from django.core.management.base import NoArgsCommand
from optparse import make_option

class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--plain', action='store_true', dest='plain',
            help='Tells Django to use plain Python, not IPython.'),
        make_option('--no-pythonrc', action='store_true', dest='no_pythonrc',
            help='Tells Django to use plain Python, not IPython.'),
    )
    help = "Like the 'shell' command but autoloads the models of all installed Django apps."

    requires_model_validation = True

    def handle_noargs(self, **options):
        # XXX: (Temporary) workaround for ticket #1796: force early loading of all
        # models from installed apps. (this is fixed by now, but leaving it here
        # for people using 0.96 or older trunk (pre [5919]) versions.
        from django.db.models.loading import get_models, get_apps
        loaded_models = get_models()

        use_plain = options.get('plain', False)
        use_pythonrc = not options.get('no_pythonrc', True)

        # Set up a dictionary to serve as the environment for the shell, so
        # that tab completion works on objects that are imported at runtime.
        # See ticket 5082.
        from django.conf import settings
        imported_objects = {'settings': settings}
        for app_mod in get_apps():
            app_models = get_models(app_mod)
            if not app_models:
                continue
            model_labels = ", ".join([model.__name__ for model in app_models])
            print self.style.SQL_COLTYPE("From '%s' autoload: %s" % (app_mod.__name__.split('.')[-2], model_labels))
            for model in app_models:
                try:
                    imported_objects[model.__name__] = getattr(__import__(app_mod.__name__, {}, {}, model.__name__), model.__name__)
                except AttributeError, e:
                    print self.style.ERROR_OUTPUT("Failed to import '%s' from '%s' reason: %s" % (model.__name__, app_mod.__name__.split('.')[-2], str(e)))
                    continue
        try:
            if use_plain:
                # Don't bother loading IPython, because the user wants plain Python.
                raise ImportError
            import IPython
            # Explicitly pass an empty list as arguments, because otherwise IPython
            # would use sys.argv from this script.
            shell = IPython.Shell.IPShell(argv=[], user_ns=imported_objects)
            shell.mainloop()
        except ImportError:
            # Using normal Python shell
            import code
            try: # Try activating rlcompleter, because it's handy.
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
                    try: 
                        execfile(pythonrc) 
                    except NameError: 
                        pass
                # This will import .pythonrc.py as a side-effect
                import user
            code.interact(local=imported_objects)

########NEW FILE########
__FILENAME__ = show_urls
from django.conf import settings
from django.core.management.base import BaseCommand
try:
    # 2008-05-30 admindocs found in newforms-admin brand
    from django.contrib.admindocs.views import extract_views_from_urlpatterns, simplify_regex
except ImportError:
    # fall back to trunk, pre-NFA merge
    from django.contrib.admin.views.doc import extract_views_from_urlpatterns, simplify_regex
        
from django_extensions.management.color import color_style

class Command(BaseCommand):
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
        
        views = []
        for settings_mod in settings_modules:
            try:
                urlconf = __import__(settings_mod.ROOT_URLCONF, {}, {}, [''])
            except Exception, e:
                if options.get('traceback', None):
                    import traceback
                    traceback.print_exc()
                print style.ERROR("Error occurred while trying to load %s: %s" % (settings_mod.ROOT_URLCONF, str(e)))
                continue
            view_functions = extract_views_from_urlpatterns(urlconf.urlpatterns)
            for (func, regex) in view_functions:
                func_name = hasattr(func, '__name__') and func.__name__ or repr(func)
                views.append("%(url)s\t%(module)s.%(name)s" % {'name': style.MODULE_NAME(func_name),
                                       'module': style.MODULE(func.__module__),
                                       'url': style.URL(simplify_regex(regex))})
        
        return "\n".join([v for v in views])

########NEW FILE########
__FILENAME__ = sqldiff
"""
sqldiff.py - Prints the (approximated) difference between models and database

TODO:
 - seperate out PostgreSQL specific introspection hacks, to facilitate easier
   writing backend specific code. (like the constrains check's)
 - general cleanup
 - better support for relations
 
KNOWN ISSUES:
 - MySQL has numerous problems with introspection. It's not recommanded to use
   sqldiff in conjuction with MySQL. But if you do, expect to see a hole lot
   of false positives. Mainly:
   - Booleans are reported back as Integers, so there's know way to know if
     there was a real change.
   - Varchar sizes are reported back without unicode support so there size
     may change in comparison to the real length of the varchar.   
"""

from django.core.management.base import AppCommand
from django.db import transaction
from optparse import make_option


class Command(AppCommand):
    option_list = AppCommand.option_list + (
        make_option('--all-applications', '-a', action='store_true', dest='all_applications',
                    help="Automaticly include all application from INSTALLED_APPS."),
        make_option('--not-only-existing', '-e', action='store_false', dest='only_existing',
                    help="Check all tables that exist in the database, not only tables that should exist based on models."),
        make_option('--dense-output', '-d', action='store_true', dest='dense_output',
                    help="Shows the output in dense format, normally output is spreaded over multiple lines."),
        make_option('--output_sql', '-s', action='store_true', dest='sql',
                    help="Outputs the differences as SQL when available"),
    )
    
    help = """Prints the (approximated) difference between models and fields in the database for the given app name(s).

It indicates how columns in the database are different from the sql that would
be generated by Django. This command is not a database migration tool. (Though
it can certainly help) It's purpose is to show the current differences as a way
to check/debug ur models compared to the real database tables and columns."""

    output_transaction = False

    def handle(self, *app_labels, **options):
        if options.get('all_applications', False) and not app_labels:
            from django.db import models
            app_labels = [app.__name__.split('.')[-2] for app in models.get_apps()]
        super(Command, self).handle(*app_labels, **options)

    def handle_app(self, app, **options):
        from django.conf import settings
        self.is_pgsql = settings.DATABASE_ENGINE.startswith("postgresql")
        self.is_sqlite = settings.DATABASE_ENGINE.startswith("sqlite")
        self.is_mysql = settings.DATABASE_ENGINE.startswith("mysql")
        self.handle_diff(app, **options)
    
    @transaction.commit_manually
    def handle_diff(self, app, **options):
        from django.db import models, connection
        from django.core.management import sql as _sql
        
        app_name = app.__name__.split('.')[-2]
        
	try:
	    django_tables = connection.introspection.django_table_names(only_existing=options.get('only_existing', True))
	except AttributeError:
	    # backwards compatibility for before introspection refactoring (r8296)
    	    try:
        	django_tables = _sql.django_table_names(only_existing=options.get('only_existing', True))
    	    except AttributeError:
        	# backwards compatibility for before svn r7568 
    	        django_tables = _sql.django_table_list(only_existing=options.get('only_existing', True))
        django_tables = [django_table for django_table in django_tables if django_table.startswith(app_name)]
        
        app_models = models.get_models(app)
        if not app_models:
            return
        
	try:
	    from django.db import get_introspection_module
            introspection_module = get_introspection_module()
	except ImportError:
	    introspection_module = connection.introspection
	
        cursor = connection.cursor()
        model_diffs = []
        for app_model in app_models:
            _constraints = None
            _meta = app_model._meta
            table_name = _meta.db_table
            table_indexes = introspection_module.get_indexes(cursor, table_name)
	    
            fieldmap = dict([(field.get_attname(), field) for field in _meta.fields])
            try:
                table_description = introspection_module.get_table_description(cursor, table_name)
            except Exception, e:
                model_diffs.append((app_model.__name__, [str(e).strip()]))
                transaction.rollback() # reset transaction
                continue
            diffs = []
            for i, row in enumerate(table_description):
                att_name = row[0].lower()
		try:
        	    db_field_reverse_type = introspection_module.data_types_reverse[row[1]]
		except AttributeError:
		    # backwards compatibility for before introspection refactoring (r8296)
		    db_field_reverse_type = introspection_module.DATA_TYPES_REVERSE.get(row[1])
                kwargs = {}
		if isinstance(db_field_reverse_type, tuple):
		    kwargs.update(db_field_reverse_type[1])
		    db_field_reverse_type = db_field_reverse_type[0]
		
                if db_field_reverse_type == "CharField" and row[3]:
                    kwargs['max_length'] = row[3]
		
                if db_field_reverse_type == "DecimalField":
                    kwargs['max_digits'] = row[4]
                    kwargs['decimal_places'] = row[5]
		
                if row[6]:
                    kwargs['blank'] = True
                    if not db_field_reverse_type in ('TextField', 'CharField'):
                        kwargs['null'] = True

                if fieldmap.has_key(att_name):
                    field = fieldmap.pop(att_name)
                    # check type
                    def clean(s):
                        s = s.split(" ")[0]
                        s = s.split("(")[0]
                        return s
                    def cmp_or_serialcmp(x, y):
                        result = x==y
                        if result:
                            return result
                        is_serial = lambda x,y: x.startswith("serial") and y.startswith("integer")
                        strip_serial = lambda x: x.lstrip("serial").lstrip("integer")
                        serial_logic = is_serial(x, y) or is_serial(y, x)
                        if result==False and serial_logic:
                            # use alternate serial logic
                            result = strip_serial(x)==strip_serial(y)
                        return result
                    db_field_type = getattr(models, db_field_reverse_type)(**kwargs).db_type()
                    model_type = field.db_type()
		    
                    # remove mysql's auto_increment keyword
                    if self.is_mysql and model_type.endswith("AUTO_INCREMENT"):
                        model_type = model_type.rsplit(' ', 1)[0].strip()
		    
                    # check if we can for constraints (only enabled on postgresql atm)
                    if self.is_pgsql:
                        if _constraints==None:
                            sql = """
                            SELECT
                                pg_constraint.conname, pg_get_constraintdef(pg_constraint.oid)
                            FROM
                                pg_constraint, pg_attribute
                            WHERE
                                pg_constraint.conrelid = pg_attribute.attrelid
                                AND pg_attribute.attnum = any(pg_constraint.conkey)
                                AND pg_constraint.conname ~ %s"""
                            cursor.execute(sql, [table_name])
                            _constraints = [r for r in cursor.fetchall() if r[0].endswith("_check")]
                        for r_name, r_check in _constraints:
                            if table_name+"_"+att_name==r_name.rsplit("_check")[0]:
                                r_check = r_check.replace("((", "(").replace("))", ")")
                                pos = r_check.find("(")
                                r_check = "%s\"%s" % (r_check[:pos+1], r_check[pos+1:])
                                pos = pos+r_check[pos:].find(" ")
                                r_check = "%s\" %s" % (r_check[:pos], r_check[pos+1:])
                                db_field_type += " "+r_check
                    else:
                        # remove constraints
                        model_type = model_type.split("CHECK")[0].strip()
                    c_db_field_type = clean(db_field_type)
                    c_model_type = clean(model_type)

                    if self.is_sqlite and (c_db_field_type=="varchar" and c_model_type=="char"):
                        c_db_field_type = "char"
                        db_field_type = db_field_type.lstrip("var")

                    if not cmp_or_serialcmp(c_model_type, c_db_field_type):
                        diffs.append({
                            'text' : "field '%s' not of same type: db=%s, model=%s" % (att_name, c_db_field_type, c_model_type),
                            'type' : 'type',
                            'data' : (table_name, att_name, c_db_field_type, c_model_type)
                        })
                        continue
                    if not cmp_or_serialcmp(db_field_type, model_type):
                        diffs.append({
                            'text' : "field '%s' parameters differ: db=%s, model=%s" % (att_name, db_field_type, model_type),
                            'type' : 'param',
                            'data' : (table_name, att_name, db_field_type, model_type)
                        })
                        continue
                else:
                    diffs.append({
                        'text' : "field '%s' missing in model: %s" % (att_name, model_type),
                        'type' : 'missing-in-model',
                        'data' : (table_name, att_name, db_field_type, model_type)
                    })
            for field in _meta.fields:
                if field.db_index:
                    if not field.attname in table_indexes and not field.unique:
                        diffs.append({
                            'text' : "field '%s' INDEX defined in model missing in database" % (field.attname),
                        })
            if fieldmap:
                for att_name, field in fieldmap.items():
                    diffs.append({
                        'text' : "field '%s' missing in database: %s" % (att_name, field.db_type()),
                        'type' : 'missing-in-db',
                        'data' : (table_name, att_name, field.db_type())
                    })
            if diffs:
                model_diffs.append((app_model.__name__, diffs))
	
        if model_diffs:
            NOTICE = self.style.NOTICE
            ERROR_OUTPUT = self.style.ERROR_OUTPUT
            SQL_TABLE = self.style.SQL_TABLE
            SQL_FIELD = self.style.SQL_FIELD
            SQL_COLTYPE = self.style.SQL_COLTYPE
            SQL_KEYWORD = self.style.SQL_KEYWORD
            modify_command = self.is_pgsql and "TYPE" or "MODIFY"
            
            if self.is_mysql:
                print ERROR_OUTPUT("""\
Using sqldiff in conjuction with MySQL has known problems.
Please see the explanations about these problems in source
code of sqldiff.py. 

Use at your own risk, and but sure to tripple check every
result. This program will continue in 5 seconds.		
		""")
                import time
                time.sleep(5)
	    
            if options.get('sql', False):
                lines = ["", SQL_KEYWORD("BEGIN;")]
                
                for model_name, diffs in model_diffs:
                    for diff in diffs:
                        if not diff: continue
                        if not diff.get('data', False): continue
                        
                        if self.is_sqlite and diff['type'] == 'param':
                                lines.append(NOTICE('-- %s' % diff['text']))
                                lines.append(NOTICE('-- SQLite does not feature type alteration on columns'))
                                continue
                        lines.append('%s %s' % (SQL_KEYWORD('ALTER TABLE'), SQL_TABLE(diff['data'][0])) )
                        if diff['type'] == 'missing-in-db':
                            lines.append('\t%s %s %s;' %  (SQL_KEYWORD('ADD'), SQL_FIELD(diff['data'][1]), SQL_COLTYPE(diff['data'][2]),) )
                        if diff['type'] == 'missing-in-model':
                            lines.append('\t%s %s;' % (SQL_KEYWORD('DROP COLUMN') , SQL_FIELD(diff['data'][1]) ))
                        if diff['type'] in ['type', 'param']:
                            lines.append('\t%s %s %s %s;' % (SQL_KEYWORD('ALTER'), SQL_FIELD(diff['data'][1]), SQL_KEYWORD(modify_command), SQL_COLTYPE(diff['data'][3])))                  
                lines.append(SQL_KEYWORD("COMMIT;"))
                
                print "\n".join(lines)
            else:
                dense = options.get('dense_output', False)
                if not dense:
                    print NOTICE("+ Application:"), SQL_TABLE(app_name)
                for model_name, diffs in model_diffs:
                    if not diffs: continue
                    if not dense:
                        print NOTICE("|-+ Differences for model:"), SQL_TABLE(model_name)
                    for diff in diffs:
                        if not dense:
                            print NOTICE("|--+"), ERROR_OUTPUT(diff['text'])
                        else:
                            print NOTICE("App"), SQL_TABLE(app_name), NOTICE('Model'), SQL_TABLE(model_name), ERROR_OUTPUT(diff['text'])


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

from django.core.management.base import BaseCommand
from django.core.management.color import no_style
from optparse import make_option
import sys
import os

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
            current_ids = set( [x.id for x in current] )
            keep_ids = set( [x.id for x in objects_to_keep[class_]] )

            remove_these_ones = current_ids.difference(keep_ids)
            if remove_these_ones:

                for obj in current:
                    if obj.id in remove_these_ones:
                        obj.delete()
                        if verbosity >= 2:
                            print "Deleted object: "+ unicode(obj)

            if verbosity > 0 and remove_these_ones:
                num_deleted = len(remove_these_ones)
                if num_deleted > 1:
                    type_deleted = unicode(class_._meta.verbose_name_plural)
                else:
                    type_deleted = unicode(class_._meta.verbose_name)

                print "Deleted "+ str(num_deleted) +" "+ type_deleted

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

        app_fixtures = [os.path.join(os.path.dirname(app.__file__), 'fixtures') \
                        for app in get_apps()]
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
                    print "Loading '%s' fixtures..." % fixture_name
            else:
                sys.stderr.write(
                    self.style.ERROR("Problem installing fixture '%s': %s is not a known "+ \
                                     "serialization format." % (fixture_name, format))
                    )
                transaction.rollback()
                transaction.leave_transaction_management()
                return

            if os.path.isabs(fixture_name):
                fixture_dirs = [fixture_name]
            else:
                fixture_dirs = app_fixtures + list(settings.FIXTURE_DIRS) + ['']

            for fixture_dir in fixture_dirs:
                if verbosity > 1:
                    print "Checking %s for fixtures..." % humanize(fixture_dir)

                label_found = False
                for format in formats:
                    serializer = serializers.get_serializer(format)
                    if verbosity > 1:
                        print "Trying %s for %s fixture '%s'..." % \
                            (humanize(fixture_dir), format, fixture_name)
                    try:
                        full_path = os.path.join(fixture_dir, '.'.join([fixture_name, format]))
                        fixture = open(full_path, 'r')
                        if label_found:
                            fixture.close()
                            print self.style.ERROR("Multiple fixtures named '%s' in %s. Aborting." %
                                (fixture_name, humanize(fixture_dir)))
                            transaction.rollback()
                            transaction.leave_transaction_management()
                            return
                        else:
                            fixture_count += 1
                            objects_per_fixture.append(0)
                            if verbosity > 0:
                                print "Installing %s fixture '%s' from %s." % \
                                    (format, fixture_name, humanize(fixture_dir))
                            try:
                                objects_to_keep = {}
                                objects = serializers.deserialize(format, fixture)
                                for obj in objects:
                                    object_count += 1
                                    objects_per_fixture[-1] += 1

                                    class_ = obj.object.__class__
                                    if not class_ in objects_to_keep:
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
                                    sys.stderr.write(
                                        self.style.ERROR("Problem installing fixture '%s': %s\n" %
                                             (full_path, traceback.format_exc())))
                                return
                            fixture.close()
                    except:
                        if verbosity > 1:
                            print "No %s fixture '%s' in %s." % \
                                (format, fixture_name, humanize(fixture_dir))

        # If any of the fixtures we loaded contain 0 objects, assume that an 
        # error was encountered during fixture loading.
        if 0 in objects_per_fixture:
            sys.stderr.write(
                self.style.ERROR("No fixture data found for '%s'. (File format may be invalid.)" %
                    (fixture_name)))
            transaction.rollback()
            transaction.leave_transaction_management()
            return
            
        # If we found even one object in a fixture, we need to reset the 
        # database sequences.
        if object_count > 0:
            sequence_sql = connection.ops.sequence_reset_sql(self.style, models)
            if sequence_sql:
                if verbosity > 1:
                    print "Resetting sequences"
                for line in sequence_sql:
                    cursor.execute(line)
            
        transaction.commit()
        transaction.leave_transaction_management()

        if object_count == 0:
            if verbosity > 1:
                print "No fixtures found."
        else:
            if verbosity > 0:
                print "Installed %d object(s) from %d fixture(s)" % (object_count, fixture_count)
                
        # Close the DB connection. This is required as a workaround for an
        # edge case in MySQL: if the same connection is used to
        # create tables, load data, and query, the query can return
        # incorrect results. See Django #7572, MySQL #37735.
        connection.close()

# Backwards compatibility for Django r9110
if not [opt for opt in Command.option_list if opt.dest=='verbosity']:
    Command.option_list += (
	make_option('--verbosity', '-v', action="store", dest="verbosity",
	    default='1', type='choice', choices=['0', '1', '2'],
	    help="Verbosity level; 0=minimal output, 1=normal output, 2=all output"),
    )

########NEW FILE########
__FILENAME__ = sync_media_s3
"""
Sync Media to S3
================

Django command that scans all files in your settings.MEDIA_ROOT folder and
uploads them to S3 with the same directory structure.

This command can optionally do the following but it is off by default:
* gzip compress any CSS and Javascript files it finds and adds the appropriate
  'Content-Encoding' header.
* set a far future 'Expires' header for optimal caching.

Note: This script requires the Python boto library and valid Amazon Web
Services API keys.

Required settings.py variables:
AWS_ACCESS_KEY_ID = ''
AWS_SECRET_ACCESS_KEY = ''
AWS_BUCKET_NAME = ''

Command options are:
  -p PREFIX, --prefix=PREFIX
                        The prefix to prepend to the path on S3.
  --gzip                Enables gzipping CSS and Javascript files.
  --expires             Enables setting a far future expires header.
  --force               Skip the file mtime check to force upload of all
                        files.

TODO:
* Make FILTER_LIST an optional argument

"""
import datetime
import email
import mimetypes
import optparse
import os
import sys
import time

from django.core.management.base import BaseCommand, CommandError

# Make sure boto is available
try:
    import boto
    import boto.exception
except ImportError:
    raise ImportError, "The boto Python library is not installed."

class Command(BaseCommand):

    # Extra variables to avoid passing these around
    AWS_ACCESS_KEY_ID = ''
    AWS_SECRET_ACCESS_KEY = ''
    AWS_BUCKET_NAME = ''
    DIRECTORY = ''
    FILTER_LIST = ['.DS_Store',]
    GZIP_CONTENT_TYPES = (
        'text/css',
        'application/javascript',
        'application/x-javascript'
    )

    upload_count = 0
    skip_count = 0

    option_list = BaseCommand.option_list + (
        optparse.make_option('-p', '--prefix',
            dest='prefix', default='',
            help="The prefix to prepend to the path on S3."),
        optparse.make_option('--gzip',
            action='store_true', dest='gzip', default=False,
            help="Enables gzipping CSS and Javascript files."),
        optparse.make_option('--expires',
            action='store_true', dest='expires', default=False,
            help="Enables setting a far future expires header."),
        optparse.make_option('--force',
            action='store_true', dest='force', default=False,
            help="Skip the file mtime check to force upload of all files.")
    )

    help = 'Syncs the complete MEDIA_ROOT structure and files to S3 into the given bucket name.'
    args = 'bucket_name'

    can_import_settings = True

    def handle(self, *args, **options):
        from django.conf import settings

        # Check for AWS keys in settings
        if not hasattr(settings, 'AWS_ACCESS_KEY_ID') or \
           not hasattr(settings, 'AWS_SECRET_ACCESS_KEY'):
           raise CommandError('Missing AWS keys from settings file.  Please' +
                     'supply both AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.')
        else:
            self.AWS_ACCESS_KEY_ID = settings.AWS_ACCESS_KEY_ID
            self.AWS_SECRET_ACCESS_KEY = settings.AWS_SECRET_ACCESS_KEY

        if not hasattr(settings, 'AWS_BUCKET_NAME'):
            raise CommandError('Missing bucket name from settings file. Please' +
                ' add the AWS_BUCKET_NAME to your settings file.')
        else:
            if not settings.AWS_BUCKET_NAME:
                raise CommandError('AWS_BUCKET_NAME cannot be empty.')
        self.AWS_BUCKET_NAME = settings.AWS_BUCKET_NAME

        if not hasattr(settings, 'MEDIA_ROOT'):
            raise CommandError('MEDIA_ROOT must be set in your settings.')
        else:
            if not settings.MEDIA_ROOT:
                raise CommandError('MEDIA_ROOT must be set in your settings.')
        self.DIRECTORY = settings.MEDIA_ROOT

        self.verbosity = int(options.get('verbosity'))
        self.prefix = options.get('prefix')
        self.do_gzip = options.get('gzip')
        self.do_expires = options.get('expires')
        self.do_force = options.get('force')

        # Now call the syncing method to walk the MEDIA_ROOT directory and
        # upload all files found.
        self.sync_s3()

        print
        print "%d files uploaded." % (self.upload_count)
        print "%d files skipped." % (self.skip_count)

    def sync_s3(self):
        """
        Walks the media directory and syncs files to S3
        """
        bucket, key = self.open_s3()
        os.path.walk(self.DIRECTORY, self.upload_s3,
            (bucket, key, self.AWS_BUCKET_NAME, self.DIRECTORY))

    def compress_string(self, s):
        """Gzip a given string."""
        import cStringIO, gzip
        zbuf = cStringIO.StringIO()
        zfile = gzip.GzipFile(mode='wb', compresslevel=6, fileobj=zbuf)
        zfile.write(s)
        zfile.close()
        return zbuf.getvalue()

    def open_s3(self):
        """
        Opens connection to S3 returning bucket and key
        """
        conn = boto.connect_s3(self.AWS_ACCESS_KEY_ID, self.AWS_SECRET_ACCESS_KEY)
        try:
            bucket = conn.get_bucket(self.AWS_BUCKET_NAME)
        except boto.exception.S3ResponseError:
            bucket = conn.create_bucket(self.AWS_BUCKET_NAME)
        return bucket, boto.s3.key.Key(bucket)

    def upload_s3(self, arg, dirname, names):
        """
        This is the callback to os.path.walk and where much of the work happens
        """
        bucket, key, bucket_name, root_dir = arg # expand arg tuple

        if root_dir == dirname:
            return # We're in the root media folder

        # Later we assume the MEDIA_ROOT ends with a trailing slash
        # TODO: Check if we should check os.path.sep for Windows
        if not root_dir.endswith('/'):
            root_dir = root_dir + '/'

        for file in names:
            headers = {}

            if file in self.FILTER_LIST:
                continue # Skip files we don't want to sync

            filename = os.path.join(dirname, file)
            if os.path.isdir(filename):
                continue # Don't try to upload directories

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
                            print "File %s hasn't been modified since last " \
                                "being uploaded" % (file_key)
                        continue

            # File is newer, let's process and upload
            if self.verbosity > 0:
                print "Uploading %s..." % (file_key)

            content_type = mimetypes.guess_type(filename)[0]
            if content_type:
                headers['Content-Type'] = content_type
            file_obj = open(filename, 'rb')
            file_size = os.fstat(file_obj.fileno()).st_size
            filedata = file_obj.read()
            if self.do_gzip:
                # Gzipping only if file is large enough (>1K is recommended) 
                # and only if file is a common text type (not a binary file)
                if file_size > 1024 and content_type in self.GZIP_CONTENT_TYPES:
                    filedata = self.compress_string(filedata)
                    headers['Content-Encoding'] = 'gzip'
                    if self.verbosity > 1:
                        print "\tgzipped: %dk to %dk" % \
                            (file_size/1024, len(filedata)/1024)
            if self.do_expires:
                # HTTP/1.0
                headers['Expires'] = '%s GMT' % (email.Utils.formatdate(
                    time.mktime((datetime.datetime.now() +
                    datetime.timedelta(days=365*2)).timetuple())))
                # HTTP/1.1
                headers['Cache-Control'] = 'max-age %d' % (3600 * 24 * 365 * 2)
                if self.verbosity > 1:
                    print "\texpires: %s" % (headers['Expires'])
                    print "\tcache-control: %s" % (headers['Cache-Control'])

            try:
                key.name = file_key
                key.set_contents_from_string(filedata, headers, replace=True)
                key.make_public()
            except boto.s3.connection.S3CreateError, e:
                print "Failed: %s" % e
            except Exception, e:
                print e
                raise
            else:
                self.upload_count += 1

            file_obj.close()

# Backwards compatibility for Django r9110
if not [opt for opt in Command.option_list if opt.dest=='verbosity']:
    Command.option_list += (
        optparse.make_option('-v', '--verbosity',
            dest='verbosity', default=1, action='count',
            help="Verbose mode. Multiple -v options increase the verbosity."),
    )

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

class HourlyJob(BaseJob):
    when = "hourly"

class DailyJob(BaseJob):
    when = "daily"

class WeeklyJob(BaseJob):
    when = "weekly"

class MonthlyJob(BaseJob):
    when = "monthly"

def my_import(name):
    imp = __import__(name)
    mods = name.split('.')
    if len(mods)>1:
        for mod in mods[1:]:
            imp = getattr(imp, mod)
    return imp

def find_jobs(jobs_dir):
    try:
        return [f[:-3] for f in os.listdir(jobs_dir) \
                if not f.startswith('_') and f.endswith(".py")]
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
    if when and not (job.when == when or job.when == None):
        raise JobError("Job %s is not a %s job." % (jobmodule, when))
    return job

def get_jobs(when=None, only_scheduled=False):
    """
    Returns a dictionary mapping of job names together with there respective
    application class.
    """
    global _jobs
    # FIXME: HACK: make sure the project dir is on the path when executed as ./manage.py
    import sys
    try:
        cpath = os.path.dirname(os.path.realpath(sys.argv[0]))
        ppath = os.path.dirname(cpath)
        if ppath not in sys.path:
            sys.path.append(ppath)
    except:
        pass
    if _jobs is None:
        _jobs = {}
        if True:
            from django.conf import settings
            for app_name in settings.INSTALLED_APPS:
                scandirs = (None, 'hourly', 'daily', 'weekly', 'monthly')
                if when:
                    scandirs = None, when
                for subdir in scandirs:
                    try:
                        path = find_job_module(app_name, subdir)
                        for name in find_jobs(path):
                            if (app_name, name) in _jobs:
                                raise JobError("Duplicate job %s" % name)
                            job = import_job(app_name, name, subdir)
                            if only_scheduled and job.when == None:
                                # only include jobs which are scheduled
                                continue
                            if when and job.when != when:
                                # generic job not in same schedule
                                continue
                            _jobs[(app_name, name)] = job
                    except ImportError:
                        pass # No job module -- continue scanning
    return _jobs

def get_job(app_name, job_name):
    jobs = get_jobs()
    if app_name:
        return jobs[(app_name, job_name)]
    else:
        for a, j in jobs.keys():
            if j==job_name:
                return jobs[(a, j)]
        raise KeyError("Job not found: %s" % job_name)

def print_jobs(when=None, only_scheduled=False, show_when=True, \
                show_appname=False, show_header=True):
    jobmap = get_jobs(when, only_scheduled=only_scheduled)
    print "Job List: %i jobs" % len(jobmap)
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
        print line
        print "-"*80

    for app_name, job_name in jlist:
        job = jobmap[(app_name, job_name)]
        line = " "
        if show_appname:
            line += appname_spacer % app_name + " - "
        line += name_spacer % job_name
        if show_when:
            line += " - " + when_spacer % (job.when and job.when or "")
        line += " - " + job.help
        print line

########NEW FILE########
__FILENAME__ = modelviz
#!/usr/bin/env python
"""Django model to DOT (Graphviz) converter
by Antonio Cavedoni <antonio@cavedoni.org>

Make sure your DJANGO_SETTINGS_MODULE is set to your project or
place this script in the same directory of the project and call
the script like this:

$ python modelviz.py [-h] [-a] [-d] [-g] [-i <model_names>] <app_label> ... <app_label> > <filename>.dot
$ dot <filename>.dot -Tpng -o <filename>.png

options:
    -h, --help
    show this help message and exit.

    -a, --all_applications
    show models from all applications.

    -d, --disable_fields
    don't show the class member fields.

    -g, --group_models
    draw an enclosing box around models from the same app.

    -i, --include_models=User,Person,Car
    only include selected models in graph.
"""
__version__ = "0.9"
__svnid__ = "$Id$"
__license__ = "Python"
__author__ = "Antonio Cavedoni <http://cavedoni.com/>"
__contributors__ = [
   "Stefano J. Attardi <http://attardi.org/>",
   "limodou <http://www.donews.net/limodou/>",
   "Carlo C8E Miron",
   "Andre Campos <cahenan@gmail.com>",
   "Justin Findlay <jfindlay@gmail.com>",
   "Alexander Houben <alexander@houben.ch>",
   "Bas van Oostveen <v.oostveen@gmail.com>",
]

import getopt, sys

from django.core.management import setup_environ

try:
    import settings
except ImportError:
    pass
else:
    setup_environ(settings)

from django.utils.safestring import mark_safe
from django.template import Template, Context
from django.db import models
from django.db.models import get_models
from django.db.models.fields.related import \
    ForeignKey, OneToOneField, ManyToManyField

try:
    from django.db.models.fields.generic import GenericRelation
except ImportError:
    from django.contrib.contenttypes.generic import GenericRelation

head_template = """
digraph name {
  fontname = "Helvetica"
  fontsize = 8

  node [
    fontname = "Helvetica"
    fontsize = 8
    shape = "plaintext"
  ]
  edge [
    fontname = "Helvetica"
    fontsize = 8
  ]

"""

body_template = """
{% if use_subgraph %}
subgraph {{ cluster_app_name }} {
  label=<
        <TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0">
        <TR><TD COLSPAN="2" CELLPADDING="4" ALIGN="CENTER"
        ><FONT FACE="Helvetica Bold" COLOR="Black" POINT-SIZE="12"
        >{{ app_name }}</FONT></TD></TR>
        </TABLE>
        >
  color=olivedrab4
  style="rounded"
{% endif %}

  {% for model in models %}
    {{ model.app_name }}_{{ model.name }} [label=<
    <TABLE BGCOLOR="palegoldenrod" BORDER="0" CELLBORDER="0" CELLSPACING="0">
     <TR><TD COLSPAN="2" CELLPADDING="4" ALIGN="CENTER" BGCOLOR="olivedrab4"
     ><FONT FACE="Helvetica Bold" COLOR="white"
     >{{ model.name }}{% if model.abstracts %}<BR/>&lt;<FONT FACE="Helvetica Italic">{{ model.abstracts|join:"," }}</FONT>&gt;{% endif %}</FONT></TD></TR>

    {% if not disable_fields %}
        {% for field in model.fields %}
        <TR><TD ALIGN="LEFT" BORDER="0"
        ><FONT {% if field.blank %}COLOR="#7B7B7B" {% endif %}FACE="Helvetica {% if field.abstract %}Italic{% else %}Bold{% endif %}">{{ field.name }}</FONT
        ></TD>
        <TD ALIGN="LEFT"
        ><FONT {% if field.blank %}COLOR="#7B7B7B" {% endif %}FACE="Helvetica {% if field.abstract %}Italic{% else %}Bold{% endif %}">{{ field.type }}</FONT
        ></TD></TR>
        {% endfor %}
    {% endif %}
    </TABLE>
    >]
  {% endfor %}

{% if use_subgraph %}
}
{% endif %}
"""

rel_template = """
  {% for model in models %}
    {% for relation in model.relations %}
    {% if relation.needs_node %}
    {{ relation.target_app }}_{{ relation.target }} [label=<
        <TABLE BGCOLOR="palegoldenrod" BORDER="0" CELLBORDER="0" CELLSPACING="0">
        <TR><TD COLSPAN="2" CELLPADDING="4" ALIGN="CENTER" BGCOLOR="olivedrab4"
        ><FONT FACE="Helvetica Bold" COLOR="white"
        >{{ relation.target }}</FONT></TD></TR>
        </TABLE>
        >]
    {% endif %}
    {{ model.app_name }}_{{ model.name }} -> {{ relation.target_app }}_{{ relation.target }}
    [label="{{ relation.name }}"] {{ relation.arrows }};
    {% endfor %}
  {% endfor %}
"""

tail_template = """
}
"""

def generate_dot(app_labels, **kwargs):
    disable_fields = kwargs.get('disable_fields', False)
    include_models = kwargs.get('include_models', [])
    all_applications = kwargs.get('all_applications', False)
    use_subgraph = kwargs.get('group_models', False)

    dot = head_template

    apps = []
    if all_applications:
        apps = models.get_apps()

    for app_label in app_labels:
        app = models.get_app(app_label)
        if not app in apps:
            apps.append(app)

    graphs = []
    for app in apps:
        graph = Context({
            'name': '"%s"' % app.__name__,
            'app_name': "%s" % '.'.join(app.__name__.split('.')[:-1]),
            'cluster_app_name': "cluster_%s" % app.__name__.replace(".", "_"),
            'disable_fields': disable_fields,
            'use_subgraph': use_subgraph,
            'models': []
        })

        for appmodel in get_models(app):
    	    abstracts = [e.__name__ for e in appmodel.__bases__ if hasattr(e, '_meta') and e._meta.abstract]
    	    abstract_fields = []
    	    for e in appmodel.__bases__:
    		if hasattr(e, '_meta') and e._meta.abstract:
    		    abstract_fields.extend(e._meta.fields)
            model = {
                'app_name': app.__name__.replace(".", "_"),
                'name': appmodel.__name__,
                'abstracts': abstracts,
                'fields': [],
                'relations': []
            }

            # consider given model name ?
            def consider(model_name):
                return not include_models or model_name in include_models

            if not consider(appmodel._meta.object_name):
                continue

            # model attributes
            def add_attributes(field):
                model['fields'].append({
                    'name': field.name,
                    'type': type(field).__name__,
                    'blank': field.blank,
                    'abstract': field in abstract_fields,
                })

            for field in appmodel._meta.fields:
                add_attributes(field)

            if appmodel._meta.many_to_many:
                for field in appmodel._meta.many_to_many:
                    add_attributes(field)

            # relations
            def add_relation(field, extras=""):
                _rel = {
                    'target_app': field.rel.to.__module__.replace('.','_'),
                    'target': field.rel.to.__name__,
                    'type': type(field).__name__,
                    'name': field.name,
                    'arrows': extras,
                    'needs_node': True
                }
                if _rel not in model['relations'] and consider(_rel['target']):
                    model['relations'].append(_rel)

            for field in appmodel._meta.fields:
                if isinstance(field, ForeignKey):
                    add_relation(field)
                elif isinstance(field, OneToOneField):
                    add_relation(field, '[arrowhead=none arrowtail=none]')

            if appmodel._meta.many_to_many:
                for field in appmodel._meta.many_to_many:
                    if isinstance(field, ManyToManyField) and getattr(field, 'creates_table', False):
                        add_relation(field, '[arrowhead=normal arrowtail=normal]')
                    elif isinstance(field, GenericRelation):
                        add_relation(field, mark_safe('[style="dotted"] [arrowhead=normal arrowtail=normal]'))
            graph['models'].append(model)
        graphs.append(graph)

    nodes = []
    for graph in graphs:
        nodes.extend([e['name'] for e in graph['models']])

    for graph in graphs:
        # don't draw duplication nodes because of relations
        for model in graph['models']:
            for relation in model['relations']:
                if relation['target'] in nodes:
                    relation['needs_node'] = False
        # render templates
        t = Template(body_template)
        dot += '\n' + t.render(graph)

    for graph in graphs:
        t = Template(rel_template)
        dot += '\n' + t.render(graph)

    dot += '\n' + tail_template
    return dot

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hadgi:",
                    ["help", "all_applications", "disable_fields", "group_models", "include_models="])
    except getopt.GetoptError, error:
        print __doc__
        sys.exit(error)
    
    kwargs = {}
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print __doc__
            sys.exit()
        if opt in ("-a", "--all_applications"):
            kwargs['all_applications'] = True
        if opt in ("-d", "--disable_fields"):
            kwargs['disable_fields'] = True
        if opt in ("-g", "--group_models"):
            kwargs['group_models'] = True
        if opt in ("-i", "--include_models"):
            kwargs['include_models'] = arg.split(',')

    if not args and not kwargs.get('all_applications', False):
        print __doc__
        sys.exit()

    print generate_dot(args, **kwargs)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = signals
"""
signals we use to trigger regular batch jobs
"""
from django.dispatch import Signal

run_hourly_jobs = Signal()
run_daily_jobs = Signal()
run_weekly_jobs = Signal()
run_monthly_jobs = Signal()

########NEW FILE########
__FILENAME__ = utils
from django.conf import settings
import os

def get_project_root():
    """ get the project root directory """
    settings_mod = __import__(settings.SETTINGS_MODULE, {}, {}, [''])
    return os.path.dirname(os.path.abspath(settings_mod.__file__))

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
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name,guess_lexer,ClassNotFound

register = template.Library()

def generate_pygments_css(path=None):
    if path is None:
        import os
        path = os.path.join(os.getcwd(),'pygments.css')
    f = open(path,'w')
    f.write(HtmlFormatter().get_style_defs('.highlight'))
    f.close()


def get_lexer(value,arg):
    if arg is None:
        return guess_lexer(value)
    return get_lexer_by_name(arg)

@register.filter(name='colorize')
@stringfilter
def colorize(value, arg=None):
    try:
        return mark_safe(highlight(value,get_lexer(value,arg),HtmlFormatter()))
    except ClassNotFound:
        return value


@register.filter(name='colorize_table')
@stringfilter
def colorize_table(value,arg=None):
    try:
        return mark_safe(highlight(value,get_lexer(value,arg),HtmlFormatter(linenos='table')))
    except ClassNotFound:
        return value

    

########NEW FILE########
__FILENAME__ = truncate_letters
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
    except ValueError: # invalid literal for int()
        return value # Fail silently
    return truncate_letters(value, length)

truncateletters.is_safe = True
truncateletters = stringfilter(truncateletters)
register.filter(truncateletters)

########NEW FILE########
__FILENAME__ = text
from django.utils.encoding import force_unicode
from django.utils.functional import allow_lazy

def truncate_letters(s, num):
    """ truncates a string to a number of letters, similar to truncate_words """
    s = force_unicode(s)
    length = int(num)
    if len(s)>length:
        s = s[:length]
    if not s.endswith('...'):
        s += '...'
    return s
truncate_letters = allow_lazy(truncate_letters, unicode)

########NEW FILE########
__FILENAME__ = uuid
r"""UUID objects (universally unique identifiers) according to RFC 4122.

This module provides immutable UUID objects (class UUID) and the functions
uuid1(), uuid3(), uuid4(), uuid5() for generating version 1, 3, 4, and 5
UUIDs as specified in RFC 4122.

If all you want is a unique ID, you should probably call uuid1() or uuid4().
Note that uuid1() may compromise privacy since it creates a UUID containing
the computer's network address.  uuid4() creates a random UUID.

Typical usage:

    >>> import uuid

    # make a UUID based on the host ID and current time
    >>> uuid.uuid1()
    UUID('a8098c1a-f86e-11da-bd1a-00112444be1e')

    # make a UUID using an MD5 hash of a namespace UUID and a name
    >>> uuid.uuid3(uuid.NAMESPACE_DNS, 'python.org')
    UUID('6fa459ea-ee8a-3ca4-894e-db77e160355e')

    # make a random UUID
    >>> uuid.uuid4()
    UUID('16fd2706-8baf-433b-82eb-8c7fada847da')

    # make a UUID using a SHA-1 hash of a namespace UUID and a name
    >>> uuid.uuid5(uuid.NAMESPACE_DNS, 'python.org')
    UUID('886313e1-3b8a-5372-9b90-0c9aee199e5d')

    # make a UUID from a string of hex digits (braces and hyphens ignored)
    >>> x = uuid.UUID('{00010203-0405-0607-0809-0a0b0c0d0e0f}')

    # convert a UUID to a string of hex digits in standard form
    >>> str(x)
    '00010203-0405-0607-0809-0a0b0c0d0e0f'

    # get the raw 16 bytes of the UUID
    >>> x.bytes
    '\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f'

    # make a UUID from a 16-byte string
    >>> uuid.UUID(bytes=x.bytes)
    UUID('00010203-0405-0607-0809-0a0b0c0d0e0f')
"""

__author__ = 'Ka-Ping Yee <ping@zesty.ca>'

RESERVED_NCS, RFC_4122, RESERVED_MICROSOFT, RESERVED_FUTURE = [
    'reserved for NCS compatibility', 'specified in RFC 4122',
    'reserved for Microsoft compatibility', 'reserved for future definition']

class UUID(object):
    """Instances of the UUID class represent UUIDs as specified in RFC 4122.
    UUID objects are immutable, hashable, and usable as dictionary keys.
    Converting a UUID to a string with str() yields something in the form
    '12345678-1234-1234-1234-123456789abc'.  The UUID constructor accepts
    five possible forms: a similar string of hexadecimal digits, or a tuple
    of six integer fields (with 32-bit, 16-bit, 16-bit, 8-bit, 8-bit, and
    48-bit values respectively) as an argument named 'fields', or a string
    of 16 bytes (with all the integer fields in big-endian order) as an
    argument named 'bytes', or a string of 16 bytes (with the first three
    fields in little-endian order) as an argument named 'bytes_le', or a
    single 128-bit integer as an argument named 'int'.

    UUIDs have these read-only attributes:

        bytes       the UUID as a 16-byte string (containing the six
                    integer fields in big-endian byte order)

        bytes_le    the UUID as a 16-byte string (with time_low, time_mid,
                    and time_hi_version in little-endian byte order)

        fields      a tuple of the six integer fields of the UUID,
                    which are also available as six individual attributes
                    and two derived attributes:

            time_low                the first 32 bits of the UUID
            time_mid                the next 16 bits of the UUID
            time_hi_version         the next 16 bits of the UUID
            clock_seq_hi_variant    the next 8 bits of the UUID
            clock_seq_low           the next 8 bits of the UUID
            node                    the last 48 bits of the UUID

            time                    the 60-bit timestamp
            clock_seq               the 14-bit sequence number

        hex         the UUID as a 32-character hexadecimal string

        int         the UUID as a 128-bit integer

        urn         the UUID as a URN as specified in RFC 4122

        variant     the UUID variant (one of the constants RESERVED_NCS,
                    RFC_4122, RESERVED_MICROSOFT, or RESERVED_FUTURE)

        version     the UUID version number (1 through 5, meaningful only
                    when the variant is RFC_4122)
    """

    def __init__(self, hex=None, bytes=None, bytes_le=None, fields=None,
                       int=None, version=None):
        r"""Create a UUID from either a string of 32 hexadecimal digits,
        a string of 16 bytes as the 'bytes' argument, a string of 16 bytes
        in little-endian order as the 'bytes_le' argument, a tuple of six
        integers (32-bit time_low, 16-bit time_mid, 16-bit time_hi_version,
        8-bit clock_seq_hi_variant, 8-bit clock_seq_low, 48-bit node) as
        the 'fields' argument, or a single 128-bit integer as the 'int'
        argument.  When a string of hex digits is given, curly braces,
        hyphens, and a URN prefix are all optional.  For example, these
        expressions all yield the same UUID:

        UUID('{12345678-1234-5678-1234-567812345678}')
        UUID('12345678123456781234567812345678')
        UUID('urn:uuid:12345678-1234-5678-1234-567812345678')
        UUID(bytes='\x12\x34\x56\x78'*4)
        UUID(bytes_le='\x78\x56\x34\x12\x34\x12\x78\x56' +
                      '\x12\x34\x56\x78\x12\x34\x56\x78')
        UUID(fields=(0x12345678, 0x1234, 0x5678, 0x12, 0x34, 0x567812345678))
        UUID(int=0x12345678123456781234567812345678)

        Exactly one of 'hex', 'bytes', 'bytes_le', 'fields', or 'int' must
        be given.  The 'version' argument is optional; if given, the resulting
        UUID will have its variant and version set according to RFC 4122,
        overriding the given 'hex', 'bytes', 'bytes_le', 'fields', or 'int'.
        """

        if [hex, bytes, bytes_le, fields, int].count(None) != 4:
            raise TypeError('need one of hex, bytes, bytes_le, fields, or int')
        if hex is not None:
            hex = hex.replace('urn:', '').replace('uuid:', '')
            hex = hex.strip('{}').replace('-', '')
            if len(hex) != 32:
                raise ValueError('badly formed hexadecimal UUID string')
            int = long(hex, 16)
        if bytes_le is not None:
            if len(bytes_le) != 16:
                raise ValueError('bytes_le is not a 16-char string')
            bytes = (bytes_le[3] + bytes_le[2] + bytes_le[1] + bytes_le[0] +
                     bytes_le[5] + bytes_le[4] + bytes_le[7] + bytes_le[6] +
                     bytes_le[8:])
        if bytes is not None:
            if len(bytes) != 16:
                raise ValueError('bytes is not a 16-char string')
            int = long(('%02x'*16) % tuple(map(ord, bytes)), 16)
        if fields is not None:
            if len(fields) != 6:
                raise ValueError('fields is not a 6-tuple')
            (time_low, time_mid, time_hi_version,
             clock_seq_hi_variant, clock_seq_low, node) = fields
            if not 0 <= time_low < 1<<32L:
                raise ValueError('field 1 out of range (need a 32-bit value)')
            if not 0 <= time_mid < 1<<16L:
                raise ValueError('field 2 out of range (need a 16-bit value)')
            if not 0 <= time_hi_version < 1<<16L:
                raise ValueError('field 3 out of range (need a 16-bit value)')
            if not 0 <= clock_seq_hi_variant < 1<<8L:
                raise ValueError('field 4 out of range (need an 8-bit value)')
            if not 0 <= clock_seq_low < 1<<8L:
                raise ValueError('field 5 out of range (need an 8-bit value)')
            if not 0 <= node < 1<<48L:
                raise ValueError('field 6 out of range (need a 48-bit value)')
            clock_seq = (clock_seq_hi_variant << 8L) | clock_seq_low
            int = ((time_low << 96L) | (time_mid << 80L) |
                   (time_hi_version << 64L) | (clock_seq << 48L) | node)
        if int is not None:
            if not 0 <= int < 1<<128L:
                raise ValueError('int is out of range (need a 128-bit value)')
        if version is not None:
            if not 1 <= version <= 5:
                raise ValueError('illegal version number')
            # Set the variant to RFC 4122.
            int &= ~(0xc000 << 48L)
            int |= 0x8000 << 48L
            # Set the version number.
            int &= ~(0xf000 << 64L)
            int |= version << 76L
        self.__dict__['int'] = int

    def __cmp__(self, other):
        if isinstance(other, UUID):
            return cmp(self.int, other.int)
        return NotImplemented

    def __hash__(self):
        return hash(self.int)

    def __int__(self):
        return self.int

    def __repr__(self):
        return 'UUID(%r)' % str(self)

    def __setattr__(self, name, value):
        raise TypeError('UUID objects are immutable')

    def __str__(self):
        hex = '%032x' % self.int
        return '%s-%s-%s-%s-%s' % (
            hex[:8], hex[8:12], hex[12:16], hex[16:20], hex[20:])

    def get_bytes(self):
        bytes = ''
        for shift in range(0, 128, 8):
            bytes = chr((self.int >> shift) & 0xff) + bytes
        return bytes

    bytes = property(get_bytes)

    def get_bytes_le(self):
        bytes = self.bytes
        return (bytes[3] + bytes[2] + bytes[1] + bytes[0] +
                bytes[5] + bytes[4] + bytes[7] + bytes[6] + bytes[8:])

    bytes_le = property(get_bytes_le)

    def get_fields(self):
        return (self.time_low, self.time_mid, self.time_hi_version,
                self.clock_seq_hi_variant, self.clock_seq_low, self.node)

    fields = property(get_fields)

    def get_time_low(self):
        return self.int >> 96L

    time_low = property(get_time_low)

    def get_time_mid(self):
        return (self.int >> 80L) & 0xffff

    time_mid = property(get_time_mid)

    def get_time_hi_version(self):
        return (self.int >> 64L) & 0xffff

    time_hi_version = property(get_time_hi_version)

    def get_clock_seq_hi_variant(self):
        return (self.int >> 56L) & 0xff

    clock_seq_hi_variant = property(get_clock_seq_hi_variant)

    def get_clock_seq_low(self):
        return (self.int >> 48L) & 0xff

    clock_seq_low = property(get_clock_seq_low)

    def get_time(self):
        return (((self.time_hi_version & 0x0fffL) << 48L) |
                (self.time_mid << 32L) | self.time_low)

    time = property(get_time)

    def get_clock_seq(self):
        return (((self.clock_seq_hi_variant & 0x3fL) << 8L) |
                self.clock_seq_low)

    clock_seq = property(get_clock_seq)

    def get_node(self):
        return self.int & 0xffffffffffff

    node = property(get_node)

    def get_hex(self):
        return '%032x' % self.int

    hex = property(get_hex)

    def get_urn(self):
        return 'urn:uuid:' + str(self)

    urn = property(get_urn)

    def get_variant(self):
        if not self.int & (0x8000 << 48L):
            return RESERVED_NCS
        elif not self.int & (0x4000 << 48L):
            return RFC_4122
        elif not self.int & (0x2000 << 48L):
            return RESERVED_MICROSOFT
        else:
            return RESERVED_FUTURE

    variant = property(get_variant)

    def get_version(self):
        # The version bits are only meaningful for RFC 4122 UUIDs.
        if self.variant == RFC_4122:
            return int((self.int >> 76L) & 0xf)

    version = property(get_version)

def _find_mac(command, args, hw_identifiers, get_index):
    import os
    for dir in ['', '/sbin/', '/usr/sbin']:
        executable = os.path.join(dir, command)
        if not os.path.exists(executable):
            continue

        try:
            # LC_ALL to get English output, 2>/dev/null to
            # prevent output on stderr
            cmd = 'LC_ALL=C %s %s 2>/dev/null' % (executable, args)
            pipe = os.popen(cmd)
        except IOError:
            continue

        for line in pipe:
            words = line.lower().split()
            for i in range(len(words)):
                if words[i] in hw_identifiers:
                    return int(words[get_index(i)].replace(':', ''), 16)
    return None

def _ifconfig_getnode():
    """Get the hardware address on Unix by running ifconfig."""

    # This works on Linux ('' or '-a'), Tru64 ('-av'), but not all Unixes.
    for args in ('', '-a', '-av'):
        mac = _find_mac('ifconfig', args, ['hwaddr', 'ether'], lambda i: i+1)
        if mac:
            return mac

    import socket
    ip_addr = socket.gethostbyname(socket.gethostname())

    # Try getting the MAC addr from arp based on our IP address (Solaris).
    mac = _find_mac('arp', '-an', [ip_addr], lambda i: -1)
    if mac:
        return mac

    # This might work on HP-UX.
    mac = _find_mac('lanscan', '-ai', ['lan0'], lambda i: 0)
    if mac:
        return mac

    return None

def _ipconfig_getnode():
    """Get the hardware address on Windows by running ipconfig.exe."""
    import os, re
    dirs = ['', r'c:\windows\system32', r'c:\winnt\system32']
    try:
        import ctypes
        buffer = ctypes.create_string_buffer(300)
        ctypes.windll.kernel32.GetSystemDirectoryA(buffer, 300)
        dirs.insert(0, buffer.value.decode('mbcs'))
    except:
        pass
    for dir in dirs:
        try:
            pipe = os.popen(os.path.join(dir, 'ipconfig') + ' /all')
        except IOError:
            continue
        for line in pipe:
            value = line.split(':')[-1].strip().lower()
            if re.match('([0-9a-f][0-9a-f]-){5}[0-9a-f][0-9a-f]', value):
                return int(value.replace('-', ''), 16)

def _netbios_getnode():
    """Get the hardware address on Windows using NetBIOS calls.
    See http://support.microsoft.com/kb/118623 for details."""
    import win32wnet, netbios
    ncb = netbios.NCB()
    ncb.Command = netbios.NCBENUM
    ncb.Buffer = adapters = netbios.LANA_ENUM()
    adapters._pack()
    if win32wnet.Netbios(ncb) != 0:
        return
    adapters._unpack()
    for i in range(adapters.length):
        ncb.Reset()
        ncb.Command = netbios.NCBRESET
        ncb.Lana_num = ord(adapters.lana[i])
        if win32wnet.Netbios(ncb) != 0:
            continue
        ncb.Reset()
        ncb.Command = netbios.NCBASTAT
        ncb.Lana_num = ord(adapters.lana[i])
        ncb.Callname = '*'.ljust(16)
        ncb.Buffer = status = netbios.ADAPTER_STATUS()
        if win32wnet.Netbios(ncb) != 0:
            continue
        status._unpack()
        bytes = map(ord, status.adapter_address)
        return ((bytes[0]<<40L) + (bytes[1]<<32L) + (bytes[2]<<24L) +
                (bytes[3]<<16L) + (bytes[4]<<8L) + bytes[5])

# Thanks to Thomas Heller for ctypes and for his help with its use here.

# If ctypes is available, use it to find system routines for UUID generation.
_uuid_generate_random = _uuid_generate_time = _UuidCreate = None
try:
    import ctypes, ctypes.util
    _buffer = ctypes.create_string_buffer(16)

    # The uuid_generate_* routines are provided by libuuid on at least
    # Linux and FreeBSD, and provided by libc on Mac OS X.
    for libname in ['uuid', 'c']:
        try:
            lib = ctypes.CDLL(ctypes.util.find_library(libname))
        except:
            continue
        if hasattr(lib, 'uuid_generate_random'):
            _uuid_generate_random = lib.uuid_generate_random
        if hasattr(lib, 'uuid_generate_time'):
            _uuid_generate_time = lib.uuid_generate_time

    # On Windows prior to 2000, UuidCreate gives a UUID containing the
    # hardware address.  On Windows 2000 and later, UuidCreate makes a
    # random UUID and UuidCreateSequential gives a UUID containing the
    # hardware address.  These routines are provided by the RPC runtime.
    # NOTE:  at least on Tim's WinXP Pro SP2 desktop box, while the last
    # 6 bytes returned by UuidCreateSequential are fixed, they don't appear
    # to bear any relationship to the MAC address of any network device
    # on the box.
    try:
        lib = ctypes.windll.rpcrt4
    except:
        lib = None
    _UuidCreate = getattr(lib, 'UuidCreateSequential',
                          getattr(lib, 'UuidCreate', None))
except:
    pass

def _unixdll_getnode():
    """Get the hardware address on Unix using ctypes."""
    _uuid_generate_time(_buffer)
    return UUID(bytes=_buffer.raw).node

def _windll_getnode():
    """Get the hardware address on Windows using ctypes."""
    if _UuidCreate(_buffer) == 0:
        return UUID(bytes=_buffer.raw).node

def _random_getnode():
    """Get a random node ID, with eighth bit set as suggested by RFC 4122."""
    import random
    return random.randrange(0, 1<<48L) | 0x010000000000L

_node = None

def getnode():
    """Get the hardware address as a 48-bit positive integer.

    The first time this runs, it may launch a separate program, which could
    be quite slow.  If all attempts to obtain the hardware address fail, we
    choose a random 48-bit number with its eighth bit set to 1 as recommended
    in RFC 4122.
    """

    global _node
    if _node is not None:
        return _node

    import sys
    if sys.platform == 'win32':
        getters = [_windll_getnode, _netbios_getnode, _ipconfig_getnode]
    else:
        getters = [_unixdll_getnode, _ifconfig_getnode]

    for getter in getters + [_random_getnode]:
        try:
            _node = getter()
        except:
            continue
        if _node is not None:
            return _node

_last_timestamp = None

def uuid1(node=None, clock_seq=None):
    """Generate a UUID from a host ID, sequence number, and the current time.
    If 'node' is not given, getnode() is used to obtain the hardware
    address.  If 'clock_seq' is given, it is used as the sequence number;
    otherwise a random 14-bit sequence number is chosen."""

    # When the system provides a version-1 UUID generator, use it (but don't
    # use UuidCreate here because its UUIDs don't conform to RFC 4122).
    if _uuid_generate_time and node is clock_seq is None:
        _uuid_generate_time(_buffer)
        return UUID(bytes=_buffer.raw)

    global _last_timestamp
    import time
    nanoseconds = int(time.time() * 1e9)
    # 0x01b21dd213814000 is the number of 100-ns intervals between the
    # UUID epoch 1582-10-15 00:00:00 and the Unix epoch 1970-01-01 00:00:00.
    timestamp = int(nanoseconds/100) + 0x01b21dd213814000L
    if timestamp <= _last_timestamp:
        timestamp = _last_timestamp + 1
    _last_timestamp = timestamp
    if clock_seq is None:
        import random
        clock_seq = random.randrange(1<<14L) # instead of stable storage
    time_low = timestamp & 0xffffffffL
    time_mid = (timestamp >> 32L) & 0xffffL
    time_hi_version = (timestamp >> 48L) & 0x0fffL
    clock_seq_low = clock_seq & 0xffL
    clock_seq_hi_variant = (clock_seq >> 8L) & 0x3fL
    if node is None:
        node = getnode()
    return UUID(fields=(time_low, time_mid, time_hi_version,
                        clock_seq_hi_variant, clock_seq_low, node), version=1)

def uuid3(namespace, name):
    """Generate a UUID from the MD5 hash of a namespace UUID and a name."""
    import md5
    hash = md5.md5(namespace.bytes + name).digest()
    return UUID(bytes=hash[:16], version=3)

def uuid4():
    """Generate a random UUID."""

    # When the system provides a version-4 UUID generator, use it.
    if _uuid_generate_random:
        _uuid_generate_random(_buffer)
        return UUID(bytes=_buffer.raw)

    # Otherwise, get randomness from urandom or the 'random' module.
    try:
        import os
        return UUID(bytes=os.urandom(16), version=4)
    except:
        import random
        bytes = [chr(random.randrange(256)) for i in range(16)]
        return UUID(bytes=bytes, version=4)

def uuid5(namespace, name):
    """Generate a UUID from the SHA-1 hash of a namespace UUID and a name."""
    import sha
    hash = sha.sha(namespace.bytes + name).digest()
    return UUID(bytes=hash[:16], version=5)

# The following standard UUIDs are for use with uuid3() or uuid5().

NAMESPACE_DNS = UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
NAMESPACE_URL = UUID('6ba7b811-9dad-11d1-80b4-00c04fd430c8')
NAMESPACE_OID = UUID('6ba7b812-9dad-11d1-80b4-00c04fd430c8')
NAMESPACE_X500 = UUID('6ba7b814-9dad-11d1-80b4-00c04fd430c8')

########NEW FILE########
__FILENAME__ = base
import settings
import datetime
import os
import stat

from django.core.exceptions import ImproperlyConfigured

import gheat
import gheat.opacity
from gheat.models import Point
from gheat import gheatsettings as settings
from gheat import gmerc
from gheat import BUILD_EMPTIES, DIRMODE, SIZE, log


class ColorScheme(object):
    """Base class for color scheme representations.
    """

    def __init__(self, name, fspath):
        """Takes the name and filesystem path of the defining PNG.
        """
#        if aspen.mode.DEVDEB:
#            aspen.restarter.track(fspath)
        self.hook_set(fspath)
        self.empties_dir = os.path.join(settings.GHEAT_MEDIA_ROOT, name, 'empties')
        self.build_empties()


    def build_empties(self):
        """Build empty tiles for this color scheme.
        """
        empties_dir = self.empties_dir

        if not BUILD_EMPTIES:
            log.info("not building empty tiles for %s " % self)
        else:    
            if not os.path.isdir(empties_dir):
                os.makedirs(empties_dir, DIRMODE)
            if not os.access(empties_dir, os.R_OK|os.W_OK|os.X_OK):
                raise ImproperlyConfigured( "Permissions too restrictive on "
                                        + "empties directory "
                                        + "(%s)." % empties_dir
                                         )
            for fname in os.listdir(empties_dir):
                if fname.endswith('.png'):
                    os.remove(os.path.join(empties_dir, fname))
            for zoom, opacity in gheat.opacity.zoom_to_opacity.items():
                fspath = os.path.join(empties_dir, str(zoom)+'.png')
                self.hook_build_empty(opacity, fspath)
            
            log.info("building empty tiles in %s" % empties_dir)


    def get_empty_fspath(self, zoom):
        fspath = os.path.join(self.empties_dir, str(zoom)+'.png')
        if not os.path.isfile(fspath):
            self.build_empties() # so we can rebuild empties on the fly
        return fspath


    def hook_set(self):
        """Set things that your backend will want later.
        """
        raise NotImplementedError


    def hook_build_empty(self, opacity, fspath):
        """Given an opacity and a path, save an empty tile.
        """
        raise NotImplementedError


class Dot(object):
    """Base class for dot representations.

    Unlike color scheme, the same basic external API works for both backends. 
    How we compute that API is different, though.

    """

    def __init__(self, zoom):
        """Takes a zoom level.
        """
        name = 'dot%d.png' % zoom
        fspath = os.path.join(settings.GHEAT_CONF_DIR, 'dots', name)
        self.img, self.half_size = self.hook_get(fspath)
        
    def hook_get(self, fspath):
        """Given a filesystem path, return two items.
        """
        raise NotImplementedError


class Tile(object):
    """Base class for tile representations.
    """

    img = None

    def __init__(self, color_scheme, dots, zoom, x, y, fspath):
        """x and y are tile coords per Google Maps.
        """

        # Calculate some things.
        # ======================

        dot = dots[zoom]


        # Translate tile to pixel coords.
        # -------------------------------

        x1 = x * SIZE
        x2 = x1 + 255
        y1 = y * SIZE
        y2 = y1 + 255
    
    
        # Expand bounds by one-half dot width.
        # ------------------------------------
    
        x1 = x1 - dot.half_size
        x2 = x2 + dot.half_size
        y1 = y1 - dot.half_size
        y2 = y2 + dot.half_size
        expanded_size = (x2-x1, y2-y1)
    
    
        # Translate new pixel bounds to lat/lng.
        # --------------------------------------
    
        n, w = gmerc.px2ll(x1, y1, zoom)
        s, e = gmerc.px2ll(x2, y2, zoom)


        # Save
        # ====

        self.dot = dot.img
        self.pad = dot.half_size

        self.x = x
        self.y = y

        self.x1 = x1
        self.y1 = y1

        self.x2 = x2
        self.y2 = y2

        self.expanded_size = expanded_size
        self.llbound = (n,s,e,w)
        self.zoom = zoom
        self.fspath = fspath
        self.opacity = gheat.opacity.zoom_to_opacity[zoom]
        self.color_scheme = color_scheme
  

    def is_empty(self):
        """With attributes set on self, return a boolean.

        Calc lat/lng bounds of this tile (include half-dot-width of padding)
        SELECT count(uid) FROM points
        """
        numpoints = Point.objects.num_points(self)
        return numpoints == 0


    def is_stale(self):
        """With attributes set on self, return a boolean.

        Calc lat/lng bounds of this tile (include half-dot-width of padding)
        SELECT count(uid) FROM points WHERE modtime < modtime_tile
        """
        if not os.path.isfile(self.fspath):
            return True
   
        timestamp = os.stat(self.fspath)[stat.ST_MTIME]
        modtime = datetime.datetime.fromtimestamp(timestamp)

        numpoints = Point.objects.num_points(self, modtime)

        return numpoints > 0


    def rebuild(self):
        """Rebuild the image at self.img. Real work delegated to subclasses.
        """

        # Calculate points.
        # =================
        # Build a closure that gives us the x,y pixel coords of the points
        # to be included on this tile, relative to the top-left of the tile.

        _points = Point.objects.points_inside(self)
   
        def points():
            """Yield x,y pixel coords within this tile, top-left of dot.
            """
            result = []
            for point in _points:
                x, y = gmerc.ll2px(point.latitude, point.longitude, self.zoom)
                x = x - self.x1 # account for tile offset relative to
                y = y - self.y1 #  overall map
                point_density = point.density
                while point_density > 0:
                    result.append((x-self.pad,y-self.pad))
                    point_density = point_density - 1
            return result


        # Main logic
        # ==========
        # Hand off to the subclass to actually build the image, then come back 
        # here to maybe create a directory before handing back to the backend
        # to actually write to disk.

        self.img = self.hook_rebuild(points())

        dirpath = os.path.dirname(self.fspath)
        if dirpath and not os.path.isdir(dirpath):
            os.makedirs(dirpath, DIRMODE)


    def hook_rebuild(self, points, opacity):
        """Rebuild and save the file using the current library.

        The algorithm runs something like this:

            o start a tile canvas/image that is a dots-worth oversized
            o loop through points and multiply dots on the tile
            o trim back down to straight tile size
            o invert/colorize the image
            o make it transparent

        Return the img object; it will be sent back to hook_save after a
        directory is made if needed.

        Trim after looping because we multiply is the only step that needs the
        extra information.

        The coloring and inverting can happen in the same pixel manipulation 
        because you can invert colors.png. That is a 1px by 256px PNG that maps
        grayscale values to color values. You can customize that file to change
        the coloration.

        """
        raise NotImplementedError


    def save(self):
        """Write the image at self.img to disk.
        """
        raise NotImplementedError



########NEW FILE########
__FILENAME__ = gheatsettings
# Let the developer to override generic values for the gheat settings 
# Normally set on a localsettings.py file or the same settings.py of your
# home project
from django.conf import settings

from os.path import dirname, abspath, join
# Default Gheat settings
GHEAT_BACKEND = getattr(settings, 'GHEAT_BACKEND','PIL')
GHEAT_ZOOM_OPAQUE=getattr(settings, 'GHEAT_ZOOM_OPAQUE', -1)
GHEAT_ZOOM_TRANSPARENT=getattr(settings, 'GHEAT_ZOOM_TRANSPARENT', 17)
GHEAT_FULL_OPAQUE=getattr(settings, 'GHEAT_FULL_OPAQUE', True)
GHEAT_BUILD_EMPTIES=getattr(settings, 'GHEAT_BUILD_EMPTIES', True)
GHEAT_ALWAYS_BUILD=getattr(settings, 'GHEAT_ALWAYS_BUILD', True)
GHEAT_DIRMODE = getattr(settings, 'GHEAT_DIRMODE', '0755')

GHEAT_CONF_DIR = getattr(settings, 'GHEAT_CONF_DIR', join(dirname(abspath(__file__)), 'etc'))
GHEAT_MEDIA_ROOT = getattr(settings, 'GHEAT_MEDIA_ROOT', '/tmp/gheat/')
DEBUG = settings.DEBUG



########NEW FILE########
__FILENAME__ = gmerc
"""This is a port of Google's GMercatorProjection.fromLatLngToPixel.

Doco on the original:

  http://code.google.com/apis/maps/documentation/reference.html#GMercatorProjection


Here's how I ported it:

  http://blag.whit537.org/2007/07/how-to-hack-on-google-maps.html


The goofy variable names below are an artifact of Google's javascript
obfuscation.

"""
import math


# Constants
# =========
# My knowledge of what these mean is undefined.

CBK = [128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576, 2097152, 4194304, 8388608, 16777216, 33554432, 67108864, 134217728, 268435456, 536870912, 1073741824, 2147483648, 4294967296, 8589934592, 17179869184, 34359738368, 68719476736, 137438953472]
CEK = [0.7111111111111111, 1.4222222222222223, 2.8444444444444446, 5.688888888888889, 11.377777777777778, 22.755555555555556, 45.51111111111111, 91.02222222222223, 182.04444444444445, 364.0888888888889, 728.1777777777778, 1456.3555555555556, 2912.711111111111, 5825.422222222222, 11650.844444444445, 23301.68888888889, 46603.37777777778, 93206.75555555556, 186413.51111111112, 372827.02222222224, 745654.0444444445, 1491308.088888889, 2982616.177777778, 5965232.355555556, 11930464.711111112, 23860929.422222223, 47721858.844444446, 95443717.68888889, 190887435.37777779, 381774870.75555557, 763549741.5111111]
CFK = [40.74366543152521, 81.48733086305042, 162.97466172610083, 325.94932345220167, 651.8986469044033, 1303.7972938088067, 2607.5945876176133, 5215.189175235227, 10430.378350470453, 20860.756700940907, 41721.51340188181, 83443.02680376363, 166886.05360752725, 333772.1072150545, 667544.214430109, 1335088.428860218, 2670176.857720436, 5340353.715440872, 10680707.430881744, 21361414.86176349, 42722829.72352698, 85445659.44705395, 170891318.8941079, 341782637.7882158, 683565275.5764316, 1367130551.1528633, 2734261102.3057265, 5468522204.611453, 10937044409.222906, 21874088818.445812, 43748177636.891624]


def ll2px(lat, lng, zoom):
    """Given two floats and an int, return a 2-tuple of ints.

    Note that the pixel coordinates are tied to the entire map, not to the map
    section currently in view.

    """
    assert isinstance(lat, (float, int, long)), \
        ValueError("lat must be a float")
    lat = float(lat)
    assert isinstance(lng, (float, int, long)), \
        ValueError("lng must be a float")
    lng = float(lng)
    assert isinstance(zoom, int), TypeError("zoom must be an int from 0 to 30")
    assert 0 <= zoom <= 30, ValueError("zoom must be an int from 0 to 30")

    cbk = CBK[zoom]

    x = int(round(cbk + (lng * CEK[zoom])))

    foo = math.sin(lat * math.pi / 180)
    if foo < -0.9999:
        foo = -0.9999
    elif foo > 0.9999:
        foo = 0.9999

    y = int(round(cbk + (0.5 * math.log((1+foo)/(1-foo)) * (-CFK[zoom]))))

    return (x, y)



def px2ll(x, y, zoom):
    """Given three ints, return a 2-tuple of floats.

    Note that the pixel coordinates are tied to the entire map, not to the map
    section currently in view.

    """
    assert isinstance(x, (int, long)), \
        ValueError("px must be a 2-tuple of ints")
    assert isinstance(y, (int, long)), \
        ValueError("px must be a 2-tuple of ints")
    assert isinstance(zoom, int), TypeError("zoom must be an int from 0 to 30")
    assert 0 <= zoom <= 30, ValueError("zoom must be an int from 0 to 30")

    foo = CBK[zoom]
    lng = (x - foo) / CEK[zoom]
    bar = (y - foo) / -CFK[zoom]
    blam = 2 * math.atan(math.exp(bar)) - math.pi / 2
    lat = blam / (math.pi / 180)

    return (lat, lng)


if __name__ == '__main__':

    # Tests
    # =====
    # The un-round numbers were gotten by calling Google's js function.

    data = [ (3, 39.81447, -98.565388, 463, 777)
           , (3, 40.609538, -80.224528, 568, 771)

           , (0, -90, 180, 256, 330)
           , (0, -90, -180, 0, 330)
           , (0, 90, 180, 256, -74)
           , (0, 90, -180, 0, -74)

           , (1, -90, 180, 512, 660)
           , (1, -90, -180, 0, 660)
           , (1, 90, 180, 512, -148)
           , (1, 90, -180, 0, -148)

           , (2, -90, 180, 1024, 1319)
           , (2, -90, -180, 0, 1319)
           , (2, 90, 180, 1024, -295)
           , (2, 90, -180, 0, -295)

            ]

    def close(floats, floats2):
        """Compare two sets of floats.
        """
        lat_actual = abs(floats[0] - floats2[0])
        lng_actual = abs(floats[1] - floats2[1])
        assert lat_actual < 1, (floats[0], floats2[0])
        assert lng_actual < 1, (floats[1], floats2[1])
        return True

    for zoom, lat, lng, x, y in data:
        assert ll2px(lat, lng, zoom) == (x, y), (lat, lng)
        assert close(px2ll(x, y, zoom), (lat, lng)), (x, y)

########NEW FILE########
__FILENAME__ = managers
# -*- coding: utf-8 -*-
from django.db import models

class PointManager(models.Manager):

    def actives(self):
        return self.all()

    def points_inside(self,tile):
        '''
            Search all the points inside the Tile
        '''
        lat1, lat2, lng1, lng2 = tile.llbound
        qs = self.filter(
            latitude__lte=lat1,
            latitude__gte=lat2,
            longitude__lte=lng1,
            longitude__gte=lng2,
            density__gt=0,
            )
        return qs

    def num_points(self,tile,modtime=None):
        '''
            Count the number of points in a tile for a certain time
        '''
        qs = self.points_inside(tile)
        if modtime:
            qs.filter(modtime__gt=modtime)

        return qs.count()


    def clear_points(self):
        '''
            Clear all the points of the database
        '''
        self.actives().delete()


########NEW FILE########
__FILENAME__ = models
from django.db import models
from gheat import managers

# Create your models here.
class Point(models.Model):
    """
        A simple representation of a point inside the gheat database
    """
    uid = models.CharField(max_length=100, name='unique identifier')
    latitude = models.FloatField(name='Latitude', db_column='lat', blank=True)
    longitude = models.FloatField(name='Longitude', db_column='lng', blank=True)
    modtime = models.DateTimeField(auto_now = True,
        name='Last modification time', null=True)
    density = models.PositiveIntegerField(default=0, editable=False,
        name='density of the current point')

    objects = managers.PointManager()

    class Meta:
        unique_together = ('uid',)

########NEW FILE########
__FILENAME__ = opacity
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
OPAQUE = 255
TRANSPARENT = 0


def _build_zoom_mapping(MAX_ZOOM=31):
    """Build and return the zoom_to_opacity mapping
    """
    if MAX_ZOOM is None:
        from gheat import MAX_ZOOM # won't use these in testing
        from django.conf import settings

    zoom_opaque = getattr(settings, 'GHEAT_ZOOM_OPAQUE', -15)

    try:
        zoom_opaque = int(zoom_opaque)
    except ValueError:
        raise ImproperlyConfigured("zoom_opaque must be an integer.")
    
    zoom_transparent = getattr(settings, 'GHEAT_ZOOM_TRANSPARENT', 15)
    try:
        zoom_transparent = int(zoom_transparent)
    except ValueError:
        raise ImproperlyConfigured("zoom_transparent must be an integer.")

    num_opacity_steps = zoom_transparent - zoom_opaque
    zoom_to_opacity = dict()
    if num_opacity_steps < 1:               # don't want general fade
        for zoom in range(0, MAX_ZOOM + 1):
            zoom_to_opacity[zoom] = None
    else:                                   # want general fade
        opacity_step = OPAQUE / float(num_opacity_steps) # chunk of opacity
        for zoom in range(0, MAX_ZOOM + 1):
            if zoom <= zoom_opaque:
                opacity = OPAQUE 
            elif zoom >= zoom_transparent:
                opacity = TRANSPARENT
            else:
                opacity = int(OPAQUE - ((zoom - zoom_opaque) * opacity_step))
            zoom_to_opacity[zoom] = opacity

    return zoom_to_opacity

def _opaque_zoom_mapping(settings=None, MAX_ZOOM=31):
    """Build and return the zoom_to_opacity mapping
    """
    if MAX_ZOOM is None:
        from gheat import MAX_ZOOM # won't use these in testing
        
    zoom_to_opacity = dict()
    for zoom in range(0, MAX_ZOOM + 1):
        zoom_to_opacity[zoom] = OPAQUE

    return zoom_to_opacity
        
full_opaque = getattr(settings, 'GHEAT_FULL_OPAQUE', True)

if full_opaque:
    zoom_to_opacity = _opaque_zoom_mapping()
else:
    zoom_to_opacity = _build_zoom_mapping()


########NEW FILE########
__FILENAME__ = pil_
import os

from PIL import Image, ImageChops
from gheat import SIZE, base
from gheat.opacity import OPAQUE


class ColorScheme(base.ColorScheme):

    def hook_set(self, fspath):
        self.colors = Image.open(fspath).load()

    def hook_build_empty(self, opacity, fspath):
        color = self.colors[0, 255]
        if len(color) == 4: # color map has per-pixel alpha
            (conf, pixel) = opacity, color[3] 
            opacity = int(( (conf/255.0)    # from configuration
                          * (pixel/255.0)   # from per-pixel alpha
                           ) * 255)
        color = color[:3] + (opacity,)
        tile = Image.new('RGBA', (SIZE, SIZE), color)
        tile.save(fspath, 'PNG')


class Dot(base.Dot):
    def hook_get(self, fspath):
        img = Image.open(fspath)
        half_size = img.size[0] / 2
        return img, half_size 


class Tile(base.Tile):
    """Represent a tile; use the PIL backend.
    """

    def hook_rebuild(self, points):
        """Given a list of points and an opacity, save a tile.
    
        This uses the PIL backend.
    
        """
        tile = self._start()
        tile = self._add_points(tile, points)
        tile = self._trim(tile)
        foo  = self._colorize(tile) # returns None
        return tile


    def _start(self):
        return Image.new('RGBA', self.expanded_size, 'white')


    def _add_points(self, tile, points):
        for x,y in points:
            dot_placed = Image.new('RGBA', self.expanded_size, 'white')
            dot_placed.paste(self.dot, (x, y))
            tile = ImageChops.multiply(tile, dot_placed)
        return tile
  

    def _trim(self, tile):
        tile = tile.crop((self.pad, self.pad, SIZE+self.pad, SIZE+self.pad))
        tile = ImageChops.duplicate(tile) # converts ImageCrop => Image
        return tile


    def _colorize(self, tile):
        _computed_opacities = dict()
        pix = tile.load() # Image => PixelAccess
        for x in range(SIZE):
            for y in range(SIZE):

                # Get color for this intensity
                # ============================
                # is a value 
                
                val = self.color_scheme.colors[0, pix[x,y][0]]
                try:
                    pix_alpha = val[3] # the color image has transparency
                except IndexError:
                    pix_alpha = OPAQUE # it doesn't
                

                # Blend the opacities
                # ===================

                conf, pixel = self.opacity, pix_alpha
                if (conf, pixel) not in _computed_opacities:
                    opacity = int(( (conf/255.0)    # from configuration
                                  * (pixel/255.0)   # from per-pixel alpha
                                   ) * 255)
                    _computed_opacities[(conf, pixel)] = opacity
                
                pix[x,y] = val[:3] + (_computed_opacities[(conf, pixel)],)

    
    def save(self):
        self.img.save(self.fspath, 'PNG')



########NEW FILE########
__FILENAME__ = pygame_
import os

import numpy
import pygame
from gheat import SIZE, base


WHITE = (255, 255, 255)


# Needed for colors
# =================
# 
#   http://www.pygame.org/wiki/HeadlessNoWindowsNeeded 
# 
# Beyond what is said there, also set the color depth to 32 bits.

os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.display.init()
pygame.display.set_mode((1,1), 0, 32)


class ColorScheme(base.ColorScheme):

    def hook_set(self, fspath):
        colors = pygame.image.load(fspath)
        self.colors = colors = colors.convert_alpha()
        self.color_map = pygame.surfarray.pixels3d(colors)[0] 
        self.alpha_map = pygame.surfarray.pixels_alpha(colors)[0]

    def hook_build_empty(self, opacity, fspath):
        tile = pygame.Surface((SIZE,SIZE), pygame.SRCALPHA, 32)
        tile.fill(self.color_map[255])
        tile.convert_alpha()

        (conf, pixel) = opacity, self.alpha_map[255]
        opacity = int(( (conf/255.0)    # from configuration
                      * (pixel/255.0)   # from per-pixel alpha
                       ) * 255)

        pygame.surfarray.pixels_alpha(tile)[:,:] = opacity 
        pygame.image.save(tile, fspath)


class Dot(base.Dot):
    def hook_get(self, fspath):
        img = pygame.image.load(fspath)
        half_size = img.get_size()[0] / 2
        return img, half_size


class Tile(base.Tile):

    def hook_rebuild(self, points):
        """Given a list of points, save a tile.
    
        This uses the Pygame backend.
   
        Good surfarray tutorial (old but still applies):

            http://www.pygame.org/docs/tut/surfarray/SurfarrayIntro.html

        Split out to give us better profiling granularity.

        """
        tile = self._start()
        tile = self._add_points(tile, points)
        tile = self._trim(tile)
        tile = self._colorize(tile)
        return tile


    def _start(self):
        tile = pygame.Surface(self.expanded_size, 0, 32)
        tile.fill(WHITE)
        return tile
        #@ why do we get green after this step?
 
       
    def _add_points(self, tile, points):
        for dest in points:
            tile.blit(self.dot, dest, None, pygame.BLEND_MULT)
        return tile


    def _trim(self, tile):
        tile = tile.subsurface(self.pad, self.pad, SIZE, SIZE).copy()
        #@ pygame.transform.chop says this or blit; this is plenty fast 
        return tile


    def _colorize(self, tile):

        # Invert/colorize
        # ===============
        # The way this works is that we loop through all pixels in the image,
        # and set their color and their transparency based on an index image.
        # The index image can be as wide as we want; we only look at the first
        # column of pixels. This first column is considered a mapping of 256
        # gray-scale intensity values to color/alpha.

        # Optimized: I had the alpha computation in a separate function because 
        # I'm also using it above in ColorScheme (cause I couldn't get set_alpha
        # working). The inner loop runs 65536 times, and just moving the 
        # computation out of a function and inline into the loop sped things up 
        # about 50%. It sped it up another 50% to cache the values, since each
        # of the 65536 variables only ever takes one of 256 values. Not super
        # fast still, but more reasonable (1.5 seconds instead of 12).
        #
        # I would expect that precomputing the dictionary at start-up time 
        # should give us another boost, but it slowed us down again. Maybe 
        # since with precomputation we have to calculate more than we use, the 
        # size of the dictionary made a difference? Worth exploring ...

        _computed_opacities = dict()

        tile = tile.convert_alpha(self.color_scheme.colors)
        tile.lock()
        pix = pygame.surfarray.pixels3d(tile)
        alp = pygame.surfarray.pixels_alpha(tile)
        for x in range(SIZE):
            for y in range(SIZE):
                key = pix[x,y,0]

                conf, pixel = self.opacity, self.color_scheme.alpha_map[key]
                if (conf, pixel) not in _computed_opacities:
                    opacity = int(( (conf/255.0)    # from configuration
                                  * (pixel/255.0)   # from per-pixel alpha
                                   ) * 255)
                    _computed_opacities[(conf, pixel)] = opacity

                pix[x,y] = self.color_scheme.color_map[key]
                alp[x,y] = _computed_opacities[(conf, pixel)]

        tile.unlock()
   
        return tile


    def save(self):
        pygame.image.save(self.img, self.fspath)



########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *

urlpatterns = patterns('gheat.views',
    url(
        # Example : today/fire/12/3,2.png
        regex = r'^(?P<color_scheme>\w+)/(?P<zoom>\d+)/(?P<x>\d+),(?P<y>\d+).png$',
        view = 'serve_tile',
        name = 'serve_tile',
       ),
    )

########NEW FILE########
__FILENAME__ = views
import os.path
from django.http import HttpResponseRedirect
from gheat import dots
from gheat import backend, color_schemes, translate, ROOT, log, \
        ALWAYS_BUILD

from django.http import HttpResponseBadRequest
from django.conf import settings
from django.views.static import serve

# Create your views here.
def serve_tile(request,color_scheme,zoom,x,y):
    '''
        Responsible for serving png files of the tile for the heat map

        This view will try to serve the file from the filesystem in case already
        exists otherwise just try to genereate it, and serve it.
    '''

    # Asserting request is a correct one
    try:
        assert color_scheme in color_schemes, ( "bad color_scheme: "
                                              + color_scheme
                                               )
        assert zoom.isdigit() and x.isdigit() and y.isdigit(), "not digits"
        zoom = int(zoom)
        x = int(x)
        y = int(y)
        assert 0 <= zoom <= 30, "bad zoom: %d" % zoom
    except AssertionError, err:
        return HttpResponseBadRequest()

    # @TODO: We should return the file in case is already present
    # Also we have to implement a redirection to the front end in case we are not in debug mode ... should we ? 

    fspath = generate_tile(request,color_scheme,zoom,x,y)

    if settings.DEBUG:
        return serve(request, fspath, '/')
    else:
        return HttpResponseRedirect(fspath.replace(ROOT, '/site_media/gheat/'))


def generate_tile(request,color_scheme,zoom,x,y):
    '''
        This view will generate the png file for the current request
    '''
    path = request.path

    path = path[path.index(color_scheme)-1:] # Removing the /gheat/ from the url

    fspath = translate(ROOT, path)

    if os.path.exists(fspath):
        return fspath

    color_scheme = color_schemes[color_scheme]
    tile = backend.Tile(color_scheme, dots, zoom, x, y, fspath)
    if tile.is_empty():
        fspath = color_scheme.get_empty_fspath(zoom)
        log.debug('serving empty tile, request: %s, file %s' % (path,fspath))
    elif tile.is_stale() or ALWAYS_BUILD:
        log.debug('rebuilding %s' % path)
        tile.rebuild()
        tile.save()
    else:
        log.debug('serving cached tile %s' % path)

    return fspath

########NEW FILE########
__FILENAME__ = update_gheat_points
import os.path
import os, logging
import shutil
from datetime import datetime, timedelta

from django_extensions.management.jobs import HourlyJob

from gheat.models import Point
from gheat import ROOT
import feedparser


feeds = [
    #'http://earthquake.usgs.gov/eqcenter/catalogs/eqs7day-M5.xml',
    'http://www.earthpublisher.com/georss.php',
    ]

class Job(HourlyJob):
    help = 'Calculate the points for the gHeat server, fetching them from an'\
            ' internet public georss service'
    

    def execute(self):
        # We should iterate over all the possible filters, any place to have this possible filters ??? __init__.py ? settings.py ?
        shutil.rmtree(ROOT)
        Point.objects.clear_points() # Should be rethought ... probably is no needed ... or it is ?
        
        total_points = 0
        
        for feed in feeds:
            f = feedparser.parse(feed)
            
            for entry in f.entries:
                Point(uid=entry.id if getattr(entry, 'id', None) else total_points,
                    latitude=entry.geo_lat,
                    longitude=entry.geo_long,
                    density=1,
                    ).save()                
                total_points += 1

        logging.info('Finnished calculating new points, total points: %s'
                    % total_points)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template
from django.conf import settings

urlpatterns = patterns('',
    ('^about/$', direct_to_template, {
        'template': 'about.html'
    })
)


urlpatterns = patterns('home.views',
    url(
        regex   = r'', 
        view    = direct_to_template, 
        name    = 'home',
        kwargs  = {
            'template': 'home.html',
            'extra_context': {
                'google_key':settings.GOOGLE_MAPS_KEY,
                }
            }
        ),
)

########NEW FILE########
__FILENAME__ = views


    

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
import sys
from os.path import dirname, abspath, join

# Importing gheat folder to be more easy to test this application. In a real 
# application should be done with python_path
sys.path.append(dirname(dirname(dirname(abspath(__file__)))))

# Importing also django extenions

sys.path.append(join(dirname(dirname(dirname(abspath(__file__)))),'external','django-extensions'))


try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for persisted project.

import os
PROJECT_HOME = os.path.dirname(__file__)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'db/persisted.db'             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
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

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '=wg@x19kr@26sibiaynb9ax5ddp1&yu^+$3n++^_lz1ms80syb'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'persisted.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget toABQIAAAA6NuvWGazX80RVrkSkvrUXBQuY05VDPolZO1YI32txJLc5t1HWBRafKMBWIXOpS9wazP_0ErZiNd8_g use absolute paths, not relative paths.
    os.path.join(PROJECT_HOME, 'templates'),
    
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'gheat',
    'django_extensions',
    'home',
)

#GOOGLE_MAPS_KEY = 'ABQIAAAA2icoFs7d_hisx8EBdZy-mxQF3fr7joqA35-x6JbT4Kx-pk-_6xRkPVambEqUO33n_8g9KWVaLKq8UA' # localhost
#GOOGLE_MAPS_KEY = 'ABQIAAAAnfs7bKE82qgb3Zc2YyS-oBT2yXp_ZAY8_ufC3CFXhHIE1NvwkxSySz_REpPq-4WZA27OwgbtyR3VcA' # external ip
GOOGLE_MAPS_KEY = 'ABQIAAAA6NuvWGazX80RVrkSkvrUXBTpH3CbXHjuCVmaTc5MkkU4wO1RRhSZXiYEMqjgwJ9gi_PC8AA-dDGz6g' # 127.0.0.1:8000




########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    (r'^home/', include('home.urls')),
    (r'^gheat/', include('gheat.urls')),

)

########NEW FILE########
