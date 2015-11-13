__FILENAME__ = admin
from django.contrib import admin

import models

admin.site.register(models.Project)
admin.site.register(models.ProjectVersion)
admin.site.register(models.Module)
admin.site.register(models.Klass)
admin.site.register(models.Inheritance)
admin.site.register(models.KlassAttribute)
admin.site.register(models.ModuleAttribute)
admin.site.register(models.Method)
admin.site.register(models.Function)

########NEW FILE########
__FILENAME__ = factories
import factory

from .models import Inheritance, Klass, Module, Project, ProjectVersion


class ProjectFactory(factory.DjangoModelFactory):
    FACTORY_FOR = Project
    name = factory.Sequence(lambda n: 'project{0}'.format(n))


class ProjectVersionFactory(factory.DjangoModelFactory):
    FACTORY_FOR = ProjectVersion
    project = factory.SubFactory(ProjectFactory)
    version_number = factory.Sequence(lambda n: str(n))


class ModuleFactory(factory.DjangoModelFactory):
    FACTORY_FOR = Module
    project_version = factory.SubFactory(ProjectVersionFactory)
    name = factory.Sequence(lambda n: 'module{0}'.format(n))


class KlassFactory(factory.DjangoModelFactory):
    FACTORY_FOR = Klass
    module = factory.SubFactory(ModuleFactory)
    name = factory.Sequence(lambda n: 'klass{0}'.format(n))
    line_number = 1
    import_path = factory.LazyAttribute(
        lambda a: '{project}.{module}'.format(
            project=a.module.project_version.project.name,
            module=a.module.name,
        )
    )

class InheritanceFactory(factory.DjangoModelFactory):
    FACTORY_FOR = Inheritance
    parent = factory.SubFactory(KlassFactory)
    child = factory.SubFactory(KlassFactory)
    order = 1

########NEW FILE########
__FILENAME__ = cbv_dumpversion
import json

from django.db.models.query import QuerySet
from django.core.management import call_command
from django.core.management.base import LabelCommand
from django.core import serializers
from cbv import models


class Command(LabelCommand):
    """Dump the django cbv app data for a specific version."""
    def handle_label(self, label, **options):
        filtered_models = (
            (models.ProjectVersion, 'version_number'),
            (models.Module, 'project_version__version_number'),
            (models.ModuleAttribute, 'module__project_version__version_number'),
            (models.Function, 'module__project_version__version_number'),
            (models.Klass, 'module__project_version__version_number'),
            (models.KlassAttribute, 'klass__module__project_version__version_number'),
            (models.Method, 'klass__module__project_version__version_number'),
            (models.Inheritance, 'parent__module__project_version__version_number'),
        )
        objects = []
        for model, version_arg in filtered_models:
            filter_kwargs = {version_arg: label}
            result = model.objects.filter(**filter_kwargs)
            objects = objects + list(result)
        for obj in objects:
            obj.pk = None
        dump = serializers.serialize('json', objects, indent=1, use_natural_keys=True)
        self.stdout.write(dump)

########NEW FILE########
__FILENAME__ = fetch_docs_urls
from blessings import Terminal
from django.core.management.base import BaseCommand
from sphinx.ext.intersphinx import fetch_inventory

from cbv.models import Klass, ProjectVersion

t = Terminal()


class Command(BaseCommand):
    args = ''
    help = 'Fetches the docs urls for CBV Classes.'
    django_doc_url = 'http://docs.djangoproject.com/en/{version}'
    # versions of Django which are supported by CCBV
    django_versions = ProjectVersion.objects.values_list('version_number',
        flat=True)
    # Django has custom inventory file name
    inv_filename = '_objects'

    def bless_prints(self, version, msg):
        # wish the blessings lib supports method chaining..
        a = t.blue('Django ' + version + ': ')
        z = t.green(msg)
        print a + z

    def handle(self, *args, **options):
        """
        Docs urls for Classes can differ between Django versions.
        This script sets correct urls for specific Classes using bits from
        `sphinx.ext.intersphinx` to fetch docs inventory data.
        """

        for v in self.django_versions:
            cnt = 1

            ver_url = self.django_doc_url.format(version=v)
            ver_inv_url = ver_url + '/' + self.inv_filename

            # get flat list of CBV classes per Django version
            qs_lookups = {'module__project_version__version_number': v}
            ver_classes = Klass.objects.filter(**qs_lookups).values_list(
                'name', flat=True)
            self.bless_prints(v, 'Found {0} classes'.format(len(ver_classes)))
            self.bless_prints(v, 'Getting inventory @ {0}'.format(ver_inv_url))
            # fetch some inventory dataz
            # the arg `None` should be a Sphinx instance object..
            invdata = fetch_inventory(None, ver_url, ver_inv_url)
            # we only want classes..
            for item in invdata[u'py:class']:
                # ..which come from django.views
                if 'django.views.' in item:
                    # get class name
                    inv_klass = item.split('.')[-1]
                    # save hits to db and update only required classes
                    for vc in ver_classes:
                        if vc == inv_klass:
                            url = invdata[u'py:class'][item][2]
                            qs_lookups.update({
                                'name': inv_klass
                            })
                            Klass.objects.filter(**qs_lookups).update(
                                docs_url=url)
                            cnt += 1
                            continue
            self.bless_prints(v, 'Updated {0} classes\n'.format(cnt))

########NEW FILE########
__FILENAME__ = populate_cbv
import inspect
import sys

import django
from django.core.management.base import BaseCommand
from django.views import generic

from blessings import Terminal
from cbv.models import Project, ProjectVersion, Module, Klass, Inheritance, KlassAttribute, ModuleAttribute, Method, Function

t = Terminal()


class Command(BaseCommand):
    args = ''
    help = 'Wipes and populates the CBV inspection models.'
    target = generic
    banned_attr_names = (
        '__builtins__',
        '__class__',
        '__dict__',
        '__doc__',
        '__file__',
        '__module__',
        '__name__',
        '__package__',
        '__path__',
        '__weakref__',
    )

    def handle(self, *args, **options):
        # Delete ALL of the things.
        ProjectVersion.objects.filter(
            project__name__iexact='Django',
            version_number=django.get_version(),
        ).delete()
        Inheritance.objects.filter(
            parent__module__project_version__project__name__iexact='Django',
            parent__module__project_version__version_number=django.get_version(),
        ).delete()

        # Setup Project
        self.project_version = ProjectVersion.objects.create(
            project=Project.objects.get_or_create(name='Django')[0],
            version_number=django.get_version(),
        )

        self.klasses = {}
        self.attributes = {}
        self.klass_imports = {}
        print t.red('Tree traversal')
        self.process_member(self.target, self.target.__name__)
        self.create_inheritance()
        self.create_attributes()

    def ok_to_add_module(self, member, parent):
        if member.__package__ is None or not member.__name__.startswith(self.target.__name__):
            return False
        return True

    def ok_to_add_klass(self, member, parent):
        if member.__name__.startswith(self.target.__name__):  # TODO: why?
            return False
        try:
            if inspect.getsourcefile(member) != inspect.getsourcefile(parent):
                if parent.__name__ in member.__module__:
                    self.add_new_import_path(member, parent)
                return False
        except TypeError:
            return False
        return True

    def ok_to_add_method(self, member, parent):
        if inspect.getsourcefile(member) != inspect.getsourcefile(parent):
            return False

        # Use line inspection to work out whether the method is defined on this
        # klass. Possibly not the best way, but I can't think of another atm.
        lines, start_line = inspect.getsourcelines(member)
        parent_lines, parent_start_line = inspect.getsourcelines(parent)
        if start_line < parent_start_line or start_line > parent_start_line + len(parent_lines):
            return False
        return True

    def ok_to_add_function(self, member, member_name, parent):
        if inspect.getsourcefile(member) != inspect.getsourcefile(parent):
            return False
        return True

    def ok_to_add_attribute(self, member, member_name, parent):
        if inspect.isclass(parent) and member in object.__dict__.values():
                return False

        if member_name in self.banned_attr_names:
            return False
        return True

    ok_to_add_klass_attribute = ok_to_add_module_attribute = ok_to_add_attribute

    def get_code(self, member):
            # Strip unneeded whitespace from beginning of code lines
            lines, start_line = inspect.getsourcelines(member)
            whitespace = len(lines[0]) - len(lines[0].lstrip())
            for i, line in enumerate(lines):
                lines[i] = line[whitespace:]

            # Join code lines into one string
            code = ''.join(lines)

            # Get the method arguments
            i_args, i_varargs, i_keywords, i_defaults = inspect.getargspec(member)
            arguments = inspect.formatargspec(i_args, varargs=i_varargs, varkw=i_keywords, defaults=i_defaults)

            return code, arguments, start_line

    def get_docstring(self, member):
        return inspect.getdoc(member) or ''

    def get_value(self, member):
        return "'{0}'".format(member) if isinstance(member, basestring) else unicode(member)

    def get_filename(self, member):
        # Get full file name
        filename = inspect.getfile(member)

        # Find the system path it's in
        sys_folder = max([p for p in sys.path if p in filename], key=len)

        # Get the part of the file name after the folder on the system path.
        filename = filename[len(sys_folder):]

        # Replace `.pyc` file extensions with `.py`
        if filename[-4:] == '.pyc':
            filename = filename[:-1]
        return filename

    def get_line_number(self, member):
        try:
            return inspect.getsourcelines(member)[1]
        except TypeError:
            return -1

    def add_new_import_path(self, member, parent):
        import_path = parent.__name__
        try:
            current_import_path = self.klass_imports[member]
        except KeyError:
            self.klass_imports[member] = parent.__name__
        else:
            self.update_shortest_import_path(member, current_import_path, import_path)

        try:
            existing_member = Klass.objects.get(
                module__project_version__project__name__iexact='Django',
                module__project_version__version_number=django.get_version(),
                name=member.__name__)
        except Klass.DoesNotExist:
            return

        if self.update_shortest_import_path(member, existing_member.import_path, import_path):
            existing_member.import_path = import_path
            existing_member.save()

    def update_shortest_import_path(self, member, current_import_path, new_import_path):
        new_length = len(new_import_path.split('.'))
        current_length = len(current_import_path.split('.'))
        if new_length < current_length:
            self.klass_imports[member] = new_import_path
            return True
        return False

    def process_member(self, member, member_name, parent=None, parent_node=None):
        # BUILTIN
        if inspect.isbuiltin(member):
            return

        # MODULE
        if inspect.ismodule(member):
            # Only traverse under hierarchy
            if not self.ok_to_add_module(member, parent):
                return

            filename = self.get_filename(member)
            print t.yellow('module ' + member.__name__), filename
            # Create Module object
            this_node = Module.objects.create(
                project_version=self.project_version,
                name=member.__name__,
                docstring=self.get_docstring(member),
                filename=filename
            )
            go_deeper = True

        # CLASS
        elif inspect.isclass(member) and inspect.ismodule(parent):
            if not self.ok_to_add_klass(member, parent):
                return

            self.add_new_import_path(member, parent)
            import_path = self.klass_imports[member]

            start_line = self.get_line_number(member)
            print t.green('class ' + member_name), start_line
            this_node = Klass.objects.create(
                module=parent_node,
                name=member_name,
                docstring=self.get_docstring(member),
                line_number=start_line,
                import_path=import_path
            )
            self.klasses[member] = this_node
            go_deeper = True

        # METHOD
        elif inspect.ismethod(member):
            if not self.ok_to_add_method(member, parent):
                return

            print '    def ' + member_name

            code, arguments, start_line = self.get_code(member)

            # Make the Method
            this_node = Method.objects.create(
                klass=parent_node,
                name=member_name,
                docstring=self.get_docstring(member),
                code=code,
                kwargs=arguments[1:-1],
                line_number=start_line,
            )

            go_deeper = False

        # FUNCTION
        elif inspect.isfunction(member):
            if not self.ok_to_add_function(member, member_name, parent):
                return

            code, arguments, start_line = self.get_code(member)
            print t.blue("def {0}{1}".format(member_name, arguments))

            this_node = Function.objects.create(
                module=parent_node,
                name=member_name,
                docstring=self.get_docstring(member),
                code=code,
                kwargs=arguments[1:-1],
                line_number=start_line,
            )
            go_deeper = False

        # (Class) ATTRIBUTE
        elif inspect.isclass(parent):
            if not self.ok_to_add_klass_attribute(member, member_name, parent):
                return

            value = self.get_value(member)
            attr = (member_name, value)
            start_line = self.get_line_number(member)
            try:
                self.attributes[attr] += [(parent_node, start_line)]
            except KeyError:
                self.attributes[attr] = [(parent_node, start_line)]

            print '    {key} = {val}'.format(key=attr[0], val=attr[1])
            go_deeper = False

        # (Module) ATTRIBUTE
        elif inspect.ismodule(parent):
            if not self.ok_to_add_module_attribute(member, member_name, parent):
                return

            start_line = self.get_line_number(member)
            this_node = ModuleAttribute.objects.create(
                module=parent_node,
                name=member_name,
                value=self.get_value(member),
                line_number=start_line,
            )

            print '{key} = {val}'.format(key=this_node.name, val=this_node.value)
            go_deeper = False

        # INSPECTION. We have to go deeper ;)
        if go_deeper:
            # Go through members
            for submember_name, submember_type in inspect.getmembers(member):
                self.process_member(
                    member=submember_type,
                    member_name=submember_name,
                    parent=member,
                    parent_node=this_node
                )

    def create_inheritance(self):
        print ''
        print t.red('Inheritance')
        for klass, representation in self.klasses.iteritems():
            print ''
            print t.green(representation.__unicode__()),
            direct_ancestors = inspect.getclasstree([klass])[-1][0][1]
            for i, ancestor in enumerate(direct_ancestors):
                if ancestor in self.klasses:
                    print '.',
                    Inheritance.objects.create(
                        parent=self.klasses[ancestor],
                        child=representation,
                        order=i
                    )
        print ''

    def create_attributes(self):
        print ''
        print t.red('Attributes')

        # Go over each name/value pair to create KlassAttributes
        for name_and_value, klasses in self.attributes.iteritems():

            # Find all the descendants of each Klass.
            descendants = set()
            for klass, start_line in klasses:
                map(descendants.add, klass.get_all_children())

            # By removing descendants from klasses, we leave behind the
            # klass(s) where the value was defined.
            remaining_klasses = [k_and_l for k_and_l in klasses if k_and_l[0] not in descendants]

            # Now we can create the KlassAttributes
            name, value = name_and_value
            for klass, line in remaining_klasses:
                KlassAttribute.objects.create(
                    klass=klass,
                    line_number=line,
                    name=name,
                    value=value
                )

                print '{0}: {1} = {2}'.format(klass, name, value)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Project'
        db.create_table('cbv_project', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
        ))
        db.send_create_signal('cbv', ['Project'])

        # Adding model 'ProjectVersion'
        db.create_table('cbv_projectversion', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['cbv.Project'])),
            ('version_number', self.gf('django.db.models.fields.CharField')(max_length=200)),
        ))
        db.send_create_signal('cbv', ['ProjectVersion'])

        # Adding model 'Module'
        db.create_table('cbv_module', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project_version', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['cbv.ProjectVersion'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['cbv.Module'], null=True, blank=True)),
        ))
        db.send_create_signal('cbv', ['Module'])

        # Adding model 'Klass'
        db.create_table('cbv_klass', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('module', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['cbv.Module'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
        ))
        db.send_create_signal('cbv', ['Klass'])

        # Adding model 'Inheritance'
        db.create_table('cbv_inheritance', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['cbv.Klass'])),
            ('child', self.gf('django.db.models.fields.related.ForeignKey')(related_name='children', to=orm['cbv.Klass'])),
            ('order', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('cbv', ['Inheritance'])

        # Adding model 'Method'
        db.create_table('cbv_method', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('klass', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['cbv.Klass'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('docstring', self.gf('django.db.models.fields.TextField')()),
            ('code', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('cbv', ['Method'])


    def backwards(self, orm):
        
        # Deleting model 'Project'
        db.delete_table('cbv_project')

        # Deleting model 'ProjectVersion'
        db.delete_table('cbv_projectversion')

        # Deleting model 'Module'
        db.delete_table('cbv_module')

        # Deleting model 'Klass'
        db.delete_table('cbv_klass')

        # Deleting model 'Inheritance'
        db.delete_table('cbv_inheritance')

        # Deleting model 'Method'
        db.delete_table('cbv_method')


    models = {
        'cbv.inheritance': {
            'Meta': {'object_name': 'Inheritance'},
            'child': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'children'", 'to': "orm['cbv.Klass']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Klass']"})
        },
        'cbv.klass': {
            'Meta': {'object_name': 'Klass'},
            'ancestors': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['cbv.Klass']", 'through': "orm['cbv.Inheritance']", 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Module']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.method': {
            'Meta': {'object_name': 'Method'},
            'code': ('django.db.models.fields.TextField', [], {}),
            'docstring': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'klass': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Klass']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.module': {
            'Meta': {'object_name': 'Module'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Module']", 'null': 'True', 'blank': 'True'}),
            'project_version': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.ProjectVersion']"})
        },
        'cbv.project': {
            'Meta': {'object_name': 'Project'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.projectversion': {
            'Meta': {'object_name': 'ProjectVersion'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Project']"}),
            'version_number': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['cbv']

########NEW FILE########
__FILENAME__ = 0002_auto__add_field_method_kwargs__add_field_klass_docstring
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Method.kwargs'
        db.add_column('cbv_method', 'kwargs', self.gf('django.db.models.fields.CharField')(default='', max_length=200), keep_default=False)

        # Adding field 'Klass.docstring'
        db.add_column('cbv_klass', 'docstring', self.gf('django.db.models.fields.TextField')(default=''), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Method.kwargs'
        db.delete_column('cbv_method', 'kwargs')

        # Deleting field 'Klass.docstring'
        db.delete_column('cbv_klass', 'docstring')


    models = {
        'cbv.inheritance': {
            'Meta': {'object_name': 'Inheritance'},
            'child': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'children'", 'to': "orm['cbv.Klass']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Klass']"})
        },
        'cbv.klass': {
            'Meta': {'object_name': 'Klass'},
            'ancestors': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['cbv.Klass']", 'through': "orm['cbv.Inheritance']", 'symmetrical': 'False'}),
            'docstring': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Module']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.method': {
            'Meta': {'object_name': 'Method'},
            'code': ('django.db.models.fields.TextField', [], {}),
            'docstring': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'klass': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Klass']"}),
            'kwargs': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.module': {
            'Meta': {'object_name': 'Module'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Module']", 'null': 'True', 'blank': 'True'}),
            'project_version': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.ProjectVersion']"})
        },
        'cbv.project': {
            'Meta': {'object_name': 'Project'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.projectversion': {
            'Meta': {'object_name': 'ProjectVersion'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Project']"}),
            'version_number': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['cbv']

########NEW FILE########
__FILENAME__ = 0003_auto__add_attribute
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Attribute'
        db.create_table('cbv_attribute', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('klass', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['cbv.Klass'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=200)),
        ))
        db.send_create_signal('cbv', ['Attribute'])


    def backwards(self, orm):
        
        # Deleting model 'Attribute'
        db.delete_table('cbv_attribute')


    models = {
        'cbv.attribute': {
            'Meta': {'object_name': 'Attribute'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'klass': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Klass']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.inheritance': {
            'Meta': {'object_name': 'Inheritance'},
            'child': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'children'", 'to': "orm['cbv.Klass']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Klass']"})
        },
        'cbv.klass': {
            'Meta': {'object_name': 'Klass'},
            'ancestors': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['cbv.Klass']", 'through': "orm['cbv.Inheritance']", 'symmetrical': 'False'}),
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Module']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.method': {
            'Meta': {'object_name': 'Method'},
            'code': ('django.db.models.fields.TextField', [], {}),
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'klass': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Klass']"}),
            'kwargs': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.module': {
            'Meta': {'object_name': 'Module'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Module']", 'null': 'True', 'blank': 'True'}),
            'project_version': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.ProjectVersion']"})
        },
        'cbv.project': {
            'Meta': {'object_name': 'Project'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.projectversion': {
            'Meta': {'object_name': 'ProjectVersion'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Project']"}),
            'version_number': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['cbv']

########NEW FILE########
__FILENAME__ = 0004_auto__add_unique_projectversion_project_version_number__add_unique_mod
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding unique constraint on 'ProjectVersion', fields ['project', 'version_number']
        db.create_unique('cbv_projectversion', ['project_id', 'version_number'])

        # Adding unique constraint on 'Module', fields ['project_version', 'name']
        db.create_unique('cbv_module', ['project_version_id', 'name'])

        # Adding unique constraint on 'Inheritance', fields ['order', 'parent']
        db.create_unique('cbv_inheritance', ['order', 'parent_id'])

        # Adding unique constraint on 'Attribute', fields ['klass', 'name']
        db.create_unique('cbv_attribute', ['klass_id', 'name'])

        # Adding unique constraint on 'Klass', fields ['name', 'module']
        db.create_unique('cbv_klass', ['name', 'module_id'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Klass', fields ['name', 'module']
        db.delete_unique('cbv_klass', ['name', 'module_id'])

        # Removing unique constraint on 'Attribute', fields ['klass', 'name']
        db.delete_unique('cbv_attribute', ['klass_id', 'name'])

        # Removing unique constraint on 'Inheritance', fields ['order', 'parent']
        db.delete_unique('cbv_inheritance', ['order', 'parent_id'])

        # Removing unique constraint on 'Module', fields ['project_version', 'name']
        db.delete_unique('cbv_module', ['project_version_id', 'name'])

        # Removing unique constraint on 'ProjectVersion', fields ['project', 'version_number']
        db.delete_unique('cbv_projectversion', ['project_id', 'version_number'])


    models = {
        'cbv.attribute': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('klass', 'name'),)", 'object_name': 'Attribute'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'klass': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Klass']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.inheritance': {
            'Meta': {'ordering': "('order',)", 'unique_together': "(('parent', 'order'),)", 'object_name': 'Inheritance'},
            'child': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'ancestor_relationships'", 'to': "orm['cbv.Klass']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Klass']"})
        },
        'cbv.klass': {
            'Meta': {'unique_together': "(('module', 'name'),)", 'object_name': 'Klass'},
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Module']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.method': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Method'},
            'code': ('django.db.models.fields.TextField', [], {}),
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'klass': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Klass']"}),
            'kwargs': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.module': {
            'Meta': {'unique_together': "(('project_version', 'name'),)", 'object_name': 'Module'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Module']", 'null': 'True', 'blank': 'True'}),
            'project_version': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.ProjectVersion']"})
        },
        'cbv.project': {
            'Meta': {'object_name': 'Project'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.projectversion': {
            'Meta': {'unique_together': "(('project', 'version_number'),)", 'object_name': 'ProjectVersion'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Project']"}),
            'version_number': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['cbv']

########NEW FILE########
__FILENAME__ = 0005_auto__del_unique_inheritance_order_parent__add_unique_inheritance_orde
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Removing unique constraint on 'Inheritance', fields ['order', 'parent']
        db.delete_unique('cbv_inheritance', ['order', 'parent_id'])

        # Adding unique constraint on 'Inheritance', fields ['order', 'child']
        db.create_unique('cbv_inheritance', ['order', 'child_id'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Inheritance', fields ['order', 'child']
        db.delete_unique('cbv_inheritance', ['order', 'child_id'])

        # Adding unique constraint on 'Inheritance', fields ['order', 'parent']
        db.create_unique('cbv_inheritance', ['order', 'parent_id'])


    models = {
        'cbv.attribute': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('klass', 'name'),)", 'object_name': 'Attribute'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'klass': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Klass']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.inheritance': {
            'Meta': {'ordering': "('order',)", 'unique_together': "(('child', 'order'),)", 'object_name': 'Inheritance'},
            'child': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'ancestor_relationships'", 'to': "orm['cbv.Klass']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Klass']"})
        },
        'cbv.klass': {
            'Meta': {'unique_together': "(('module', 'name'),)", 'object_name': 'Klass'},
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Module']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.method': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Method'},
            'code': ('django.db.models.fields.TextField', [], {}),
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'klass': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Klass']"}),
            'kwargs': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.module': {
            'Meta': {'unique_together': "(('project_version', 'name'),)", 'object_name': 'Module'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Module']", 'null': 'True', 'blank': 'True'}),
            'project_version': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.ProjectVersion']"})
        },
        'cbv.project': {
            'Meta': {'object_name': 'Project'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.projectversion': {
            'Meta': {'unique_together': "(('project', 'version_number'),)", 'object_name': 'ProjectVersion'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Project']"}),
            'version_number': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['cbv']

########NEW FILE########
__FILENAME__ = 0006_auto__add_field_module_docstring
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Module.docstring'
        db.add_column('cbv_module', 'docstring', self.gf('django.db.models.fields.TextField')(default='', blank=True), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Module.docstring'
        db.delete_column('cbv_module', 'docstring')


    models = {
        'cbv.attribute': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('klass', 'name'),)", 'object_name': 'Attribute'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'klass': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Klass']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.inheritance': {
            'Meta': {'ordering': "('order',)", 'unique_together': "(('child', 'order'),)", 'object_name': 'Inheritance'},
            'child': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'ancestor_relationships'", 'to': "orm['cbv.Klass']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Klass']"})
        },
        'cbv.klass': {
            'Meta': {'unique_together': "(('module', 'name'),)", 'object_name': 'Klass'},
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Module']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.method': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Method'},
            'code': ('django.db.models.fields.TextField', [], {}),
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'klass': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Klass']"}),
            'kwargs': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.module': {
            'Meta': {'unique_together': "(('project_version', 'name'),)", 'object_name': 'Module'},
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Module']", 'null': 'True', 'blank': 'True'}),
            'project_version': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.ProjectVersion']"})
        },
        'cbv.project': {
            'Meta': {'object_name': 'Project'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.projectversion': {
            'Meta': {'unique_together': "(('project', 'version_number'),)", 'object_name': 'ProjectVersion'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Project']"}),
            'version_number': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['cbv']

########NEW FILE########
__FILENAME__ = 0007_add_functions_split_attributes
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Removing unique constraint on 'Attribute', fields ['klass', 'name']
        db.delete_unique('cbv_attribute', ['klass_id', 'name'])

        # Deleting model 'Attribute'
        db.delete_table('cbv_attribute')

        # Adding model 'ModuleAttribute'
        db.create_table('cbv_moduleattribute', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('module', self.gf('django.db.models.fields.related.ForeignKey')(related_name='attribute_set', to=orm['cbv.Module'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=200)),
        ))
        db.send_create_signal('cbv', ['ModuleAttribute'])

        # Adding unique constraint on 'ModuleAttribute', fields ['module', 'name']
        db.create_unique('cbv_moduleattribute', ['module_id', 'name'])

        # Adding model 'Function'
        db.create_table('cbv_function', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('module', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['cbv.Module'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('docstring', self.gf('django.db.models.fields.TextField')(default='', blank=True)),
            ('code', self.gf('django.db.models.fields.TextField')()),
            ('kwargs', self.gf('django.db.models.fields.CharField')(max_length=200)),
        ))
        db.send_create_signal('cbv', ['Function'])

        # Adding model 'KlassAttribute'
        db.create_table('cbv_klassattribute', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('klass', self.gf('django.db.models.fields.related.ForeignKey')(related_name='attribute_set', to=orm['cbv.Klass'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=200)),
        ))
        db.send_create_signal('cbv', ['KlassAttribute'])

        # Adding unique constraint on 'KlassAttribute', fields ['klass', 'name']
        db.create_unique('cbv_klassattribute', ['klass_id', 'name'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'KlassAttribute', fields ['klass', 'name']
        db.delete_unique('cbv_klassattribute', ['klass_id', 'name'])

        # Removing unique constraint on 'ModuleAttribute', fields ['module', 'name']
        db.delete_unique('cbv_moduleattribute', ['module_id', 'name'])

        # Adding model 'Attribute'
        db.create_table('cbv_attribute', (
            ('value', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('klass', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['cbv.Klass'])),
        ))
        db.send_create_signal('cbv', ['Attribute'])

        # Adding unique constraint on 'Attribute', fields ['klass', 'name']
        db.create_unique('cbv_attribute', ['klass_id', 'name'])

        # Deleting model 'ModuleAttribute'
        db.delete_table('cbv_moduleattribute')

        # Deleting model 'Function'
        db.delete_table('cbv_function')

        # Deleting model 'KlassAttribute'
        db.delete_table('cbv_klassattribute')


    models = {
        'cbv.function': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Function'},
            'code': ('django.db.models.fields.TextField', [], {}),
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kwargs': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Module']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.inheritance': {
            'Meta': {'ordering': "('order',)", 'unique_together': "(('child', 'order'),)", 'object_name': 'Inheritance'},
            'child': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'ancestor_relationships'", 'to': "orm['cbv.Klass']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Klass']"})
        },
        'cbv.klass': {
            'Meta': {'unique_together': "(('module', 'name'),)", 'object_name': 'Klass'},
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Module']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.klassattribute': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('klass', 'name'),)", 'object_name': 'KlassAttribute'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'klass': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attribute_set'", 'to': "orm['cbv.Klass']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.method': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Method'},
            'code': ('django.db.models.fields.TextField', [], {}),
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'klass': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Klass']"}),
            'kwargs': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.module': {
            'Meta': {'unique_together': "(('project_version', 'name'),)", 'object_name': 'Module'},
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Module']", 'null': 'True', 'blank': 'True'}),
            'project_version': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.ProjectVersion']"})
        },
        'cbv.moduleattribute': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('module', 'name'),)", 'object_name': 'ModuleAttribute'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attribute_set'", 'to': "orm['cbv.Module']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.project': {
            'Meta': {'object_name': 'Project'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.projectversion': {
            'Meta': {'unique_together': "(('project', 'version_number'),)", 'object_name': 'ProjectVersion'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Project']"}),
            'version_number': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['cbv']

########NEW FILE########
__FILENAME__ = 0008_add_filename_and_linenumbers
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'ModuleAttribute.line_number'
        db.add_column('cbv_moduleattribute', 'line_number', self.gf('django.db.models.fields.IntegerField')(default=1), keep_default=False)

        # Adding field 'Module.filename'
        db.add_column('cbv_module', 'filename', self.gf('django.db.models.fields.CharField')(default='', max_length=511), keep_default=False)

        # Adding field 'Function.line_number'
        db.add_column('cbv_function', 'line_number', self.gf('django.db.models.fields.IntegerField')(default=1), keep_default=False)

        # Adding field 'KlassAttribute.line_number'
        db.add_column('cbv_klassattribute', 'line_number', self.gf('django.db.models.fields.IntegerField')(default=1), keep_default=False)

        # Adding field 'Method.line_number'
        db.add_column('cbv_method', 'line_number', self.gf('django.db.models.fields.IntegerField')(default=1), keep_default=False)

        # Adding field 'Klass.line_number'
        db.add_column('cbv_klass', 'line_number', self.gf('django.db.models.fields.IntegerField')(default=1), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'ModuleAttribute.line_number'
        db.delete_column('cbv_moduleattribute', 'line_number')

        # Deleting field 'Module.filename'
        db.delete_column('cbv_module', 'filename')

        # Deleting field 'Function.line_number'
        db.delete_column('cbv_function', 'line_number')

        # Deleting field 'KlassAttribute.line_number'
        db.delete_column('cbv_klassattribute', 'line_number')

        # Deleting field 'Method.line_number'
        db.delete_column('cbv_method', 'line_number')

        # Deleting field 'Klass.line_number'
        db.delete_column('cbv_klass', 'line_number')


    models = {
        'cbv.function': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Function'},
            'code': ('django.db.models.fields.TextField', [], {}),
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kwargs': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'line_number': ('django.db.models.fields.IntegerField', [], {}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Module']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.inheritance': {
            'Meta': {'ordering': "('order',)", 'unique_together': "(('child', 'order'),)", 'object_name': 'Inheritance'},
            'child': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'ancestor_relationships'", 'to': "orm['cbv.Klass']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Klass']"})
        },
        'cbv.klass': {
            'Meta': {'unique_together': "(('module', 'name'),)", 'object_name': 'Klass'},
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'line_number': ('django.db.models.fields.IntegerField', [], {}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Module']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.klassattribute': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('klass', 'name'),)", 'object_name': 'KlassAttribute'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'klass': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attribute_set'", 'to': "orm['cbv.Klass']"}),
            'line_number': ('django.db.models.fields.IntegerField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.method': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Method'},
            'code': ('django.db.models.fields.TextField', [], {}),
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'klass': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Klass']"}),
            'kwargs': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'line_number': ('django.db.models.fields.IntegerField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.module': {
            'Meta': {'unique_together': "(('project_version', 'name'),)", 'object_name': 'Module'},
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '511'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Module']", 'null': 'True', 'blank': 'True'}),
            'project_version': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.ProjectVersion']"})
        },
        'cbv.moduleattribute': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('module', 'name'),)", 'object_name': 'ModuleAttribute'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'line_number': ('django.db.models.fields.IntegerField', [], {}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attribute_set'", 'to': "orm['cbv.Module']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.project': {
            'Meta': {'object_name': 'Project'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.projectversion': {
            'Meta': {'unique_together': "(('project', 'version_number'),)", 'object_name': 'ProjectVersion'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Project']"}),
            'version_number': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['cbv']

########NEW FILE########
__FILENAME__ = 0009_auto__add_field_klass_import_path
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Klass.import_path'
        db.add_column('cbv_klass', 'import_path', self.gf('django.db.models.fields.CharField')(default='', max_length=255), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Klass.import_path'
        db.delete_column('cbv_klass', 'import_path')


    models = {
        'cbv.function': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Function'},
            'code': ('django.db.models.fields.TextField', [], {}),
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kwargs': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'line_number': ('django.db.models.fields.IntegerField', [], {}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Module']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.inheritance': {
            'Meta': {'ordering': "('order',)", 'unique_together': "(('child', 'order'),)", 'object_name': 'Inheritance'},
            'child': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'ancestor_relationships'", 'to': "orm['cbv.Klass']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Klass']"})
        },
        'cbv.klass': {
            'Meta': {'unique_together': "(('module', 'name'),)", 'object_name': 'Klass'},
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'import_path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'line_number': ('django.db.models.fields.IntegerField', [], {}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Module']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.klassattribute': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('klass', 'name'),)", 'object_name': 'KlassAttribute'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'klass': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attribute_set'", 'to': "orm['cbv.Klass']"}),
            'line_number': ('django.db.models.fields.IntegerField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.method': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Method'},
            'code': ('django.db.models.fields.TextField', [], {}),
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'klass': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Klass']"}),
            'kwargs': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'line_number': ('django.db.models.fields.IntegerField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.module': {
            'Meta': {'unique_together': "(('project_version', 'name'),)", 'object_name': 'Module'},
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '511'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Module']", 'null': 'True', 'blank': 'True'}),
            'project_version': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.ProjectVersion']"})
        },
        'cbv.moduleattribute': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('module', 'name'),)", 'object_name': 'ModuleAttribute'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'line_number': ('django.db.models.fields.IntegerField', [], {}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attribute_set'", 'to': "orm['cbv.Module']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.project': {
            'Meta': {'object_name': 'Project'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.projectversion': {
            'Meta': {'unique_together': "(('project', 'version_number'),)", 'object_name': 'ProjectVersion'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Project']"}),
            'version_number': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['cbv']

########NEW FILE########
__FILENAME__ = 0010_auto__add_unique_project_name
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding unique constraint on 'Project', fields ['name']
        db.create_unique('cbv_project', ['name'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Project', fields ['name']
        db.delete_unique('cbv_project', ['name'])


    models = {
        'cbv.function': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Function'},
            'code': ('django.db.models.fields.TextField', [], {}),
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kwargs': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'line_number': ('django.db.models.fields.IntegerField', [], {}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Module']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.inheritance': {
            'Meta': {'ordering': "('order',)", 'unique_together': "(('child', 'order'),)", 'object_name': 'Inheritance'},
            'child': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'ancestor_relationships'", 'to': "orm['cbv.Klass']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Klass']"})
        },
        'cbv.klass': {
            'Meta': {'unique_together': "(('module', 'name'),)", 'object_name': 'Klass'},
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'import_path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'line_number': ('django.db.models.fields.IntegerField', [], {}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Module']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.klassattribute': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('klass', 'name'),)", 'object_name': 'KlassAttribute'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'klass': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attribute_set'", 'to': "orm['cbv.Klass']"}),
            'line_number': ('django.db.models.fields.IntegerField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.method': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Method'},
            'code': ('django.db.models.fields.TextField', [], {}),
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'klass': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Klass']"}),
            'kwargs': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'line_number': ('django.db.models.fields.IntegerField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.module': {
            'Meta': {'unique_together': "(('project_version', 'name'),)", 'object_name': 'Module'},
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '511'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Module']", 'null': 'True', 'blank': 'True'}),
            'project_version': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.ProjectVersion']"})
        },
        'cbv.moduleattribute': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('module', 'name'),)", 'object_name': 'ModuleAttribute'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'line_number': ('django.db.models.fields.IntegerField', [], {}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attribute_set'", 'to': "orm['cbv.Module']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.project': {
            'Meta': {'object_name': 'Project'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'})
        },
        'cbv.projectversion': {
            'Meta': {'ordering': "('-version_number',)", 'unique_together': "(('project', 'version_number'),)", 'object_name': 'ProjectVersion'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Project']"}),
            'version_number': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['cbv']

########NEW FILE########
__FILENAME__ = 0011_auto__del_field_module_parent
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'Module.parent'
        db.delete_column('cbv_module', 'parent_id')


    def backwards(self, orm):
        
        # Adding field 'Module.parent'
        db.add_column('cbv_module', 'parent', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['cbv.Module'], null=True, blank=True), keep_default=False)


    models = {
        'cbv.function': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Function'},
            'code': ('django.db.models.fields.TextField', [], {}),
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kwargs': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'line_number': ('django.db.models.fields.IntegerField', [], {}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Module']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.inheritance': {
            'Meta': {'ordering': "('order',)", 'unique_together': "(('child', 'order'),)", 'object_name': 'Inheritance'},
            'child': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'ancestor_relationships'", 'to': "orm['cbv.Klass']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Klass']"})
        },
        'cbv.klass': {
            'Meta': {'unique_together': "(('module', 'name'),)", 'object_name': 'Klass'},
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'import_path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'line_number': ('django.db.models.fields.IntegerField', [], {}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Module']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.klassattribute': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('klass', 'name'),)", 'object_name': 'KlassAttribute'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'klass': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attribute_set'", 'to': "orm['cbv.Klass']"}),
            'line_number': ('django.db.models.fields.IntegerField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.method': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Method'},
            'code': ('django.db.models.fields.TextField', [], {}),
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'klass': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Klass']"}),
            'kwargs': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'line_number': ('django.db.models.fields.IntegerField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.module': {
            'Meta': {'unique_together': "(('project_version', 'name'),)", 'object_name': 'Module'},
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '511'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'project_version': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.ProjectVersion']"})
        },
        'cbv.moduleattribute': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('module', 'name'),)", 'object_name': 'ModuleAttribute'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'line_number': ('django.db.models.fields.IntegerField', [], {}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attribute_set'", 'to': "orm['cbv.Module']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.project': {
            'Meta': {'object_name': 'Project'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'})
        },
        'cbv.projectversion': {
            'Meta': {'ordering': "('-version_number',)", 'unique_together': "(('project', 'version_number'),)", 'object_name': 'ProjectVersion'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Project']"}),
            'version_number': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['cbv']

########NEW FILE########
__FILENAME__ = 0012_add_docs_url_field
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Klass.docs_url'
        db.add_column('cbv_klass', 'docs_url', self.gf('django.db.models.fields.URLField')(default='', max_length=255), keep_default=False)


    def backwards(self, orm):
        
        # Deleting field 'Klass.docs_url'
        db.delete_column('cbv_klass', 'docs_url')


    models = {
        'cbv.function': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Function'},
            'code': ('django.db.models.fields.TextField', [], {}),
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kwargs': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'line_number': ('django.db.models.fields.IntegerField', [], {}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Module']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.inheritance': {
            'Meta': {'ordering': "('order',)", 'unique_together': "(('child', 'order'),)", 'object_name': 'Inheritance'},
            'child': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'ancestor_relationships'", 'to': "orm['cbv.Klass']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Klass']"})
        },
        'cbv.klass': {
            'Meta': {'ordering': "('module__name', 'name')", 'unique_together': "(('module', 'name'),)", 'object_name': 'Klass'},
            'docs_url': ('django.db.models.fields.URLField', [], {'default': "''", 'max_length': '255'}),
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'import_path': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'line_number': ('django.db.models.fields.IntegerField', [], {}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Module']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.klassattribute': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('klass', 'name'),)", 'object_name': 'KlassAttribute'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'klass': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attribute_set'", 'to': "orm['cbv.Klass']"}),
            'line_number': ('django.db.models.fields.IntegerField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.method': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Method'},
            'code': ('django.db.models.fields.TextField', [], {}),
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'klass': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Klass']"}),
            'kwargs': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'line_number': ('django.db.models.fields.IntegerField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.module': {
            'Meta': {'unique_together': "(('project_version', 'name'),)", 'object_name': 'Module'},
            'docstring': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '511'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'project_version': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.ProjectVersion']"})
        },
        'cbv.moduleattribute': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('module', 'name'),)", 'object_name': 'ModuleAttribute'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'line_number': ('django.db.models.fields.IntegerField', [], {}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attribute_set'", 'to': "orm['cbv.Module']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'cbv.project': {
            'Meta': {'object_name': 'Project'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'})
        },
        'cbv.projectversion': {
            'Meta': {'ordering': "('-version_number',)", 'unique_together': "(('project', 'version_number'),)", 'object_name': 'ProjectVersion'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cbv.Project']"}),
            'version_number': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        }
    }

    complete_apps = ['cbv']

########NEW FILE########
__FILENAME__ = models
from django.db import models


class ProjectManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)

class Project(models.Model):
    """ Represents a project in a python project hierarchy """

    name = models.CharField(max_length=200, unique=True)

    objects = ProjectManager()

    def __unicode__(self):
        return self.name

    def natural_key(self):
        return (self.name,)

    @models.permalink
    def get_absolute_url(self):
        return ('project-detail', (), {
            'package': self.name,
        })


class ProjectVersionManager(models.Manager):

    def get_by_natural_key(self, name, version_number):
        return self.get(
            project=Project.objects.get_by_natural_key(name=name),
            version_number=version_number
            )

    def get_latest(self, name):
        return self.order_by('-version_number')[0]


class ProjectVersion(models.Model):
    """ Represents a particular version of a project in a python project hierarchy """

    project = models.ForeignKey(Project)
    version_number = models.CharField(max_length=200)

    objects = ProjectVersionManager()

    class Meta:
        unique_together = ('project', 'version_number')
        ordering = ('-version_number',)

    def __unicode__(self):
        return self.project.name + " " + self.version_number

    def natural_key(self):
        return self.project.natural_key() + (self.version_number,)
    natural_key.dependencies = ['cbv.Project']

    @models.permalink
    def get_absolute_url(self):
        return ('version-detail', (), {
            'package': self.project.name,
            'version': self.version_number,
        })

    @property
    def docs_version_number(self):
        return '.'.join(self.version_number.split('.')[:2])


class ModuleManager(models.Manager):
    def get_by_natural_key(self, module_name, project_name, version_number):
        return self.get(
            name=module_name,
            project_version=ProjectVersion.objects.get_by_natural_key(
                name=project_name,
                version_number=version_number)
            )

class Module(models.Model):
    """ Represents a module of a python project """

    project_version = models.ForeignKey(ProjectVersion)
    name = models.CharField(max_length=200)
    docstring = models.TextField(blank=True, default='')
    filename = models.CharField(max_length=511, default='')

    objects = ModuleManager()

    class Meta:
        unique_together = ('project_version', 'name')

    def __unicode__(self):
        return self.name

    def short_name(self):
        return self.name.split('.')[-1]

    def natural_key(self):
        return (self.name,) + self.project_version.natural_key()
    natural_key.dependencies = ['cbv.ProjectVersion']

    @models.permalink
    def get_absolute_url(self):
        return ('module-detail', (), {
            'package': self.project_version.project.name,
            'version': self.project_version.version_number,
            'module': self.name,
        })


class KlassManager(models.Manager):
    def get_by_natural_key(self, klass_name, module_name, project_name, version_number):
        return self.get(
            name=klass_name,
            module=Module.objects.get_by_natural_key(
                module_name=module_name,
                project_name=project_name,
                version_number=version_number)
            )

    def get_latest_for_name(self, klass_name, project_name):
        qs = self.filter(
            name=klass_name,
            module__project_version__project__name=project_name,
        ) or self.filter(
            name__iexact=klass_name,
            module__project_version__project__name__iexact=project_name,
        )
        try:
            obj = qs.order_by('-module__project_version__version_number',)[0]
        except IndexError:
            raise self.model.DoesNotExist
        else:
            return obj


# TODO: quite a few of the methods on here should probably be denormed.
class Klass(models.Model):
    """ Represents a class in a module of a python project hierarchy """

    module = models.ForeignKey(Module)
    name = models.CharField(max_length=200)
    docstring = models.TextField(blank=True, default='')
    line_number = models.IntegerField()
    import_path = models.CharField(max_length=255)
    # because docs urls differ between Django versions
    docs_url = models.URLField(max_length=255, default='')

    objects = KlassManager()

    class Meta:
        unique_together = ('module', 'name')
        ordering = ('module__name', 'name')

    def __unicode__(self):
        return self.name

    def natural_key(self):
        return (self.name,) + self.module.natural_key()
    natural_key.dependencies = ['cbv.Module']

    def is_secondary(self):
        return (self.name.startswith('Base') or
                self.name.endswith('Mixin') or
                self.name.endswith('Error') or
                self.name == 'ProcessFormView')

    @models.permalink
    def get_absolute_url(self):
        return ('klass-detail', (), {
            'package': self.module.project_version.project.name,
            'version': self.module.project_version.version_number,
            'module': self.module.name,
            'klass': self.name
        })

    def get_source_url(self):
        url = 'https://github.com/django/django/blob/'
        return url + '{version}{path}#L{line}'.format(
            version=self.module.project_version.version_number,
            path=self.module.filename,
            line=self.line_number,
        )

    def get_ancestors(self):
        if not hasattr(self, '_ancestors'):
            self._ancestors = Klass.objects.filter(inheritance__child=self).order_by('inheritance__order')
        return self._ancestors

    def get_children(self):
        if not hasattr(self, '_descendants'):
            self._descendants = Klass.objects.filter(ancestor_relationships__parent=self).order_by('name')
        return self._descendants

    #TODO: This is all mucho inefficient. Perhaps we should use mptt for
    #       get_all_ancestors, get_all_children, get_methods, & get_attributes?
    def get_all_ancestors(self):
        if not hasattr(self, '_all_ancestors'):
            # Get immediate ancestors.
            ancestors = self.get_ancestors().select_related('module__project_version__project')

            # Flatten ancestors and their forebears into a list.
            tree = []
            for ancestor in ancestors:
                tree.append(ancestor)
                tree += ancestor.get_all_ancestors()

            # Remove duplicates, leaving the last occurence in tact.
            # This is how python's MRO works.
            cleaned_ancestors = []
            for ancestor in reversed(tree):
                if ancestor not in cleaned_ancestors:
                    cleaned_ancestors.insert(0, ancestor)

            # Cache the result on this object.
            self._all_ancestors = cleaned_ancestors
        return self._all_ancestors

    def get_all_children(self):
        if not hasattr(self, '_all_descendants'):
            children = self.get_children().select_related('module__project_version__project')
            for child in children:
                children = children | child.get_all_children()
            self._all_descendants = children
        return self._all_descendants

    def get_methods(self):
        if not hasattr(self, '_methods'):
            methods = self.method_set.all().select_related('klass')
            for ancestor in self.get_all_ancestors():
                methods = methods | ancestor.get_methods()
            self._methods = methods
        return self._methods

    def get_attributes(self):
        if not hasattr(self, '_attributes'):
            attrs = self.attribute_set.all()
            for ancestor in self.get_all_ancestors():
                attrs = attrs | ancestor.get_attributes()
            self._attributes = attrs
        return self._attributes

    def get_prepared_attributes(self):
        attributes = self.get_attributes()
        # Make a dictionary of attributes based on name
        attribute_names = {}
        for attr in attributes:
            try:
                attribute_names[attr.name] += [attr]
            except KeyError:
                attribute_names[attr.name] = [attr]

        ancestors = self.get_all_ancestors()

        # Find overridden attributes
        for name, attrs in attribute_names.iteritems():
            # Skip if we have only one attribute.
            if len(attrs) == 1:
                continue

            # Sort the attributes by ancestors.
            def _key(a):
                try:
                    # If ancestor, return the index (>= 0)
                    return ancestors.index(a.klass)
                except:
                    # else a.klass == self, so return -1
                    return -1
            sorted_attrs = sorted(attrs, key=_key)

            # Mark overriden KlassAttributes
            for a in sorted_attrs[1:]:
                a.overridden = True
        return attributes

    def basic_yuml_data(self, first=False):
        if hasattr(self, '_basic_yuml_data'):
            return self._basic_yuml_data
        yuml_data = []
        template = '[{parent}{{bg:{parent_col}}}]^-[{child}{{bg:{child_col}}}]'
        for ancestor in self.get_ancestors():
            yuml_data.append(template.format(
                parent=ancestor.name,
                child=self.name,
                parent_col='white' if ancestor.is_secondary() else 'lightblue',
                child_col='green' if first else 'white' if self.is_secondary() else 'lightblue',
            ))
            yuml_data += ancestor.basic_yuml_data()
        self._basic_yuml_data = yuml_data
        return self._basic_yuml_data

    def basic_yuml_url(self):
        template = 'http://yuml.me/diagram/plain;/class/{data}.svg'
        data = ', '.join(self.basic_yuml_data(first=True))
        if not data:
            return None
        return template.format(data=data)


class Inheritance(models.Model):
    """ Represents the inheritance relationships for a Klass """

    parent = models.ForeignKey(Klass)
    child = models.ForeignKey(Klass, related_name='ancestor_relationships')
    order = models.IntegerField()

    class Meta:
        ordering = ('order',)
        unique_together = ('child', 'order')

    def __unicode__(self):
        return u'%s <- %s (%d)' % (self.parent, self.child, self.order)


class KlassAttribute(models.Model):
    """ Represents an attribute on a Klass """

    klass = models.ForeignKey(Klass, related_name='attribute_set')
    name = models.CharField(max_length=200)
    value = models.CharField(max_length=200)
    line_number = models.IntegerField()

    class Meta:
        ordering = ('name',)
        unique_together = ('klass', 'name')

    def __unicode__(self):
        return u'%s = %s' % (self.name, self.value)


class ModuleAttribute(models.Model):
    """ Represents an attribute on a Module """

    module = models.ForeignKey(Module, related_name='attribute_set')
    name = models.CharField(max_length=200)
    value = models.CharField(max_length=200)
    line_number = models.IntegerField()

    class Meta:
        ordering = ('name',)
        unique_together = ('module', 'name')

    def __unicode__(self):
        return u'%s = %s' % (self.name, self.value)


class Method(models.Model):
    """ Represents a method on a Klass """

    klass = models.ForeignKey(Klass)
    name = models.CharField(max_length=200)
    docstring = models.TextField(blank=True, default='')
    code = models.TextField()
    kwargs = models.CharField(max_length=200)
    line_number = models.IntegerField()

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('name',)


class Function(models.Model):
    """ Represents a function on a Module """

    module = models.ForeignKey(Module)
    name = models.CharField(max_length=200)
    docstring = models.TextField(blank=True, default='')
    code = models.TextField()
    kwargs = models.CharField(max_length=200)
    line_number = models.IntegerField()

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('name',)

########NEW FILE########
__FILENAME__ = shortcut_urls
from django.conf.urls import patterns, url

from cbv import views

urlpatterns = patterns('',
    url(r'(?P<klass>[a-zA-Z_-]+)/$', views.LatestKlassDetailView.as_view(), name='klass-detail-shortcut'),
)

########NEW FILE########
__FILENAME__ = analytics_tags
from django import template
from django.conf import settings

register = template.Library()


@register.inclusion_tag('_analytics.html')
def analytics():
    return {
        'google_key': 'UA-29872137-1',
        'DEBUG': settings.DEBUG,
    }

########NEW FILE########
__FILENAME__ = cbv_tags
from django import template
from django.core.urlresolvers import reverse
from cbv.models import Klass, ProjectVersion

register = template.Library()


@register.filter
def namesake_methods(parent_klass, name):
    namesakes = [m for m in parent_klass.get_methods() if m.name == name]
    assert(namesakes)
    # Get the methods in order of the klasses
    try:
        result = [next((m for m in namesakes if m.klass == parent_klass))]
        namesakes.pop(namesakes.index(result[0]))
    except StopIteration:
        result = []
    for klass in parent_klass.get_all_ancestors():
        # Move the namesakes from the methods to the results
        try:
            method = next((m for m in namesakes if m.klass == klass))
            namesakes.pop(namesakes.index(method))
            result.append(method)
        except StopIteration:
            pass
    assert(not namesakes)
    return result


@register.inclusion_tag('cbv/includes/nav.html')
def nav(version, module=None, klass=None):
    other_versions = ProjectVersion.objects.filter(project=version.project).exclude(pk=version.pk)
    context = {
        'version': version,
    }
    if module:
        context['this_module'] = module
        if klass:
            context['this_klass'] = klass
            other_versions_of_klass = Klass.objects.filter(
                name=klass.name,
                module__project_version__in=other_versions,
            )
            other_versions_of_klass_dict = {x.module.project_version: x for x in other_versions_of_klass}
            for other_version in other_versions:
                try:
                    other_klass = other_versions_of_klass_dict[other_version]
                except KeyError:
                    pass
                else:
                    other_version.url = other_klass.get_absolute_url()
    context['other_versions'] = other_versions
    return context


@register.filter
def is_final(obj, last):
    return obj == last

########NEW FILE########
__FILENAME__ = tests
from django.core.urlresolvers import reverse
from django.test import TestCase

from .factories import InheritanceFactory, KlassFactory, ProjectVersionFactory
from .views import Sitemap


class SitemapTest(TestCase):
    def test_200(self):
        ProjectVersionFactory.create()
        response = self.client.get(reverse('sitemap'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/xml')

    def test_queryset(self):
        klass = KlassFactory.create()
        with self.assertNumQueries(2):  # Get ProjectVersion, get Klasses.
            url_list = Sitemap().get_queryset()
        self.assertEqual(len(url_list), 2)  # 2 because 1 Klass + homepage.


class KlassAncestorMROTest(TestCase):
    def test_linear(self):
        """
        Test a linear configuration of classes. C inherits from B which
        inherits from A.

        A
        |
        B
        |
        C

        C.__mro__ would be [C, B, A].
        """
        b_child_of_a = InheritanceFactory.create(child__name='b', parent__name='a')
        a = b_child_of_a.parent
        b = b_child_of_a.child
        c = InheritanceFactory.create(parent=b, child__name='c').child

        mro = c.get_all_ancestors()
        self.assertSequenceEqual(mro, [b, a])

    def test_diamond(self):
        """
        Test a diamond configuration of classes. This example has A as a parent
        of B and C, and D has B and C as parents.

          A
         / \
        B   C
         \ /
          D

        D.__mro__ would be [D, B, C, A].
        """
        b_child_of_a = InheritanceFactory.create(child__name='b', parent__name='a')
        a = b_child_of_a.parent
        b = b_child_of_a.child

        c = InheritanceFactory.create(parent=a, child__name='c').child
        d = InheritanceFactory.create(parent=b, child__name='d').child
        InheritanceFactory.create(parent=c, child=d, order=2)

        mro = d.get_all_ancestors()
        self.assertSequenceEqual(mro, [b, c, a])

########NEW FILE########
__FILENAME__ = urls
"""
URL variations:
project
project/version
project/version/module
project/version/module/class

e.g.
django
django/1.41a
django/1.41a/core
django/1.41a/core/DjangoRuntimeWarning

"""

from django.conf.urls import patterns, include, url
from django.views.generic import RedirectView
from django.core.urlresolvers import reverse_lazy
from cbv import views

urlpatterns = patterns('',
    url(r'^$', RedirectView.as_view(url=reverse_lazy('home'))),

    url(r'^(?P<package>[\w-]+)/$', views.RedirectToLatestVersionView.as_view(), {'url_name': 'version-detail'}),
    url(r'^(?P<package>[\w-]+)/latest/$', views.RedirectToLatestVersionView.as_view(), {'url_name': 'version-detail'}, name='latest-version-detail'),
    url(r'^(?P<package>[\w-]+)/(?P<version>[^/]+)/$', views.VersionDetailView.as_view(), name='version-detail'),

    url(r'^(?P<package>[\w-]+)/latest/(?P<module>[\w\.]+)/$', views.RedirectToLatestVersionView.as_view(), {'url_name': 'module-detail'}, name='latest-module-detail'),
    url(r'^(?P<package>[\w-]+)/(?P<version>[^/]+)/(?P<module>[\w\.]+)/$', views.ModuleDetailView.as_view(), name='module-detail'),

    url(r'^(?P<package>[\w-]+)/latest/(?P<module>[\w\.]+)/(?P<klass>[\w]+)/$', views.RedirectToLatestVersionView.as_view(), {'url_name': 'klass-detail'}, name='latest-klass-detail'),
    url(r'^(?P<package>[\w-]+)/(?P<version>[^/]+)/(?P<module>[\w\.]+)/(?P<klass>[\w]+)/$', views.KlassDetailView.as_view(), name='klass-detail'),
)

########NEW FILE########
__FILENAME__ = views
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import Http404
from django.views.generic import DetailView, ListView, RedirectView
from django.views.generic.detail import SingleObjectMixin

from cbv.models import Klass, Module, ProjectVersion


class RedirectToLatestVersionView(RedirectView):
    permanent = False

    def get_redirect_url(self, **kwargs):
        url_name = kwargs.pop('url_name')
        kwargs['version'] = ProjectVersion.objects.get_latest(kwargs.get('package')).version_number
        self.url = reverse_lazy(url_name, kwargs=kwargs)
        return super(RedirectToLatestVersionView, self).get_redirect_url(**kwargs)


class FuzzySingleObjectMixin(SingleObjectMixin):
    push_state_url = None

    def get_object(self, queryset=None):
        try:
            return self.get_precise_object()
        except self.model.DoesNotExist:
            try:
                obj = self.get_fuzzy_object()
                self.push_state_url = obj.get_absolute_url()
                return obj
            except self.model.DoesNotExist:
                raise Http404

    def get_context_data(self, **kwargs):
        context = super(FuzzySingleObjectMixin, self).get_context_data(**kwargs)
        context['push_state_url'] = self.push_state_url
        return context


class KlassDetailView(FuzzySingleObjectMixin, DetailView):
    model = Klass

    def get_queryset(self):
        return super(DetailView, self).get_queryset().select_related()

    def get_precise_object(self):
        return self.model.objects.filter(
            name=self.kwargs['klass'],
            module__name=self.kwargs['module'],
            module__project_version__version_number=self.kwargs['version'],
            module__project_version__project__name=self.kwargs['package'],
        ).select_related('module__project_version__project').get()

    def get_fuzzy_object(self):
        return self.model.objects.filter(
            name__iexact=self.kwargs['klass'],
            module__name__iexact=self.kwargs['module'],
            module__project_version__version_number__iexact=self.kwargs['version'],
            module__project_version__project__name__iexact=self.kwargs['package'],
        ).select_related('module__project_version__project').get()


class LatestKlassDetailView(FuzzySingleObjectMixin, DetailView):
    model = Klass

    def get_queryset(self):
        return super(DetailView, self).get_queryset().select_related()

    def get_precise_object(self):
        # Even if we match case-sensitively,
        # we're still going to be pushing to a new url,
        # so we'll do both lookups in get_fuzzy_object
        raise self.model.DoesNotExist

    def get_fuzzy_object(self):
        return self.model.objects.get_latest_for_name(
            klass_name=self.kwargs['klass'],
            project_name=self.kwargs['package'],
        )


class ModuleDetailView(FuzzySingleObjectMixin, DetailView):
    model = Module

    def dispatch(self, request, *args, **kwargs):
        try:
            self.project_version = ProjectVersion.objects.filter(
                version_number__iexact=kwargs['version'],
                project__name__iexact=kwargs['package'],
            ).select_related('project').get()
        except ProjectVersion.DoesNotExist:
            raise Http404
        return super(ModuleDetailView, self).dispatch(request, *args, **kwargs)

    def get_precise_object(self, queryset=None):
        return self.model.objects.get(
            name=self.kwargs['module'],
            project_version=self.project_version
        )

    def get_fuzzy_object(self, queryset=None):
        return self.model.objects.get(
            name__iexact=self.kwargs['module'],
            project_version__version_number__iexact=self.kwargs['version'],
            project_version__project__name__iexact=self.kwargs['package'],
        )

    def get_context_data(self, **kwargs):
        kwargs.update({
            'project_version': self.project_version,
            'klass_list': Klass.objects.filter(module=self.object).select_related('module__project_version', 'module__project_version__project')
        })
        return super(ModuleDetailView, self).get_context_data(**kwargs)


class VersionDetailView(ListView):
    model = Klass
    template_name = 'cbv/version_detail.html'

    def get_project_version(self, **kwargs):
        project_version = ProjectVersion.objects.filter(
            version_number__iexact=kwargs['version'],
            project__name__iexact=kwargs['package'],
        ).select_related('project').get()
        return project_version

    def get_queryset(self):
        qs = super(VersionDetailView, self).get_queryset()
        return qs.filter(module__project_version=self.project_version)

    def get_context_data(self, **kwargs):
        context = super(VersionDetailView, self).get_context_data(**kwargs)
        context['projectversion'] = self.project_version
        return context

    def dispatch(self, request, *args, **kwargs):
        try:
            self.project_version = self.get_project_version(**kwargs)
        except ProjectVersion.DoesNotExist:
            raise Http404
        return super(VersionDetailView, self).dispatch(request, *args, **kwargs)


class HomeView(VersionDetailView):
    template_name = 'home.html'

    def get_project_version(self, **kwargs):
        return ProjectVersion.objects.get_latest('Django')


class Sitemap(ListView):
    template_name = 'sitemap.xml'
    context_object_name = 'urlset'

    def get_queryset(self):
        latest_version = ProjectVersion.objects.get_latest('Django')
        klasses = Klass.objects.select_related('module__project_version__project')
        urls = [{
            'location': reverse('home'),
            'priority': 1.0,
        }]
        for klass in klasses:
            urls.append({
                'location': klass.get_absolute_url(),
                'priority': 0.9 if klass.module.project_version == latest_version else 0.5,
            })
        return urls

    def render_to_response(self, context, **response_kwargs):
        """
        In django 1.5+ we can replace this method with simply:
        content_type = 'application/xml'
        """
        response_kwargs['content_type'] = 'application/xml'
        return super(Sitemap, self).render_to_response(context, **response_kwargs)

########NEW FILE########
__FILENAME__ = settings
# Django settings for inspector project.

import os
import sys

import dj_database_url


DEBUG = bool(os.environ.get('DEBUG', False))
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Meshy', 'ccbv@meshy.co.uk'),
)

MANAGERS = ADMINS

DATABASES = {'default': dj_database_url.config(default='postgres://localhost/ccbv')}
ALLOWED_HOSTS = ('*',)


def get_cache():
    try:
        os.environ['MEMCACHE_SERVERS'] = os.environ['MEMCACHIER_SERVERS']
        os.environ['MEMCACHE_USERNAME'] = os.environ['MEMCACHIER_USERNAME']
        os.environ['MEMCACHE_PASSWORD'] = os.environ['MEMCACHIER_PASSWORD']
        return {
            'default': {
                'BACKEND': 'django_pylibmc.memcached.PyLibMCCache',
                'LOCATION': os.environ['MEMCACHIER_SERVERS'],
                'TIMEOUT': 500,
                'BINARY': True,
            }
        }
    except:
        return {
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
            }
        }
CACHES = get_cache()

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/London'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-GB'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

DIRNAME = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
STATICFILES_STORAGE = 'storages.backends.s3boto.S3BotoStorage'
S3_URL = 'https://{0}.s3.amazonaws.com/'.format(AWS_STORAGE_BUCKET_NAME)

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.join(DIRNAME, 'client_media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/client_media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(DIRNAME, 'static_media')

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = os.environ.get('STATIC_URL', S3_URL)

ADMIN_MEDIA_PREFIX = STATIC_URL + 'admin/'

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
    'inspector.staticfiles.LegacyAppDirectoriesFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = os.environ.get('SECRET_KEY', 'extra-super-secret-development-key')

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

ROOT_URLCONF = 'inspector.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'inspector.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'cbv',

    'django_extensions',
    'gunicorn',
    'django_pygmy',
    'raven.contrib.django',
    'south',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.sitemaps',
    'django.contrib.staticfiles',
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
__FILENAME__ = staticfiles
from django.contrib.staticfiles.finders import AppDirectoriesFinder
from django.contrib.staticfiles.storage import AppStaticStorage


class LegacyAppMediaStorage(AppStaticStorage):
    """
    A legacy app storage backend that provides a migration path for the
    default directory name in previous versions of staticfiles, "media".
    """
    source_dir = 'media'


class LegacyAppDirectoriesFinder(AppDirectoriesFinder):
    """
    A legacy file finder that provides a migration path for the
    default directory name in previous versions of staticfiles, "media".
    """
    storage_class = LegacyAppMediaStorage

########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic import TemplateView

from cbv.views import HomeView, Sitemap


admin.autodiscover()


urlpatterns = patterns('',
    url(r'^$', HomeView.as_view(), name='home'),
    url(r'^projects/', include('cbv.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^sitemap\.xml$', Sitemap.as_view(), name='sitemap'),
    url(r'^', include('cbv.shortcut_urls'), {'package': 'Django'}),
) + staticfiles_urlpatterns() + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


if settings.DEBUG:
    urlpatterns += patterns('',
        url(r'^404/$', TemplateView.as_view(template_name='404.html')),
        url(r'^500/$', TemplateView.as_view(template_name='500.html')),
    )

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for inspector project.

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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "inspector.settings")

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

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "inspector.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
