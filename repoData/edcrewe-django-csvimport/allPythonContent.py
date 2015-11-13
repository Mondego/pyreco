__FILENAME__ = admin
from datetime import datetime
from django import forms
from django.db import models
from django.contrib import admin
from django.contrib.admin import ModelAdmin

from csvimport.models import CSVImport

class CSVImportAdmin(ModelAdmin):
    ''' Custom model to not have much editable! '''
    readonly_fields = ['file_name',
                       'upload_method',
                       'error_log_html',
                       'import_user']
    fields = [
                'model_name',
                'field_list',
                'upload_file',
                'file_name',
                'encoding',
                'upload_method',
                'error_log_html',
                'import_user']
    formfield_overrides = {
        models.CharField: {'widget': forms.Textarea(attrs={'rows':'4',
                                                           'cols':'60'})},
        }

    def save_model(self, request, obj, form, change):
        """ Do save and process command - cant commit False
            since then file wont be found for reopening via right charset
        """
        form.save()
        from csvimport.management.commands.csvimport import Command
        cmd = Command()
        if obj.upload_file:
            obj.file_name = obj.upload_file.name
            obj.encoding = ''
            defaults = self.filename_defaults(obj.file_name)
            cmd.setup(mappings=obj.field_list,
                      modelname=obj.model_name,
                      charset=obj.encoding,
                      uploaded=obj.upload_file,
                      defaults=defaults)
        errors = cmd.run(logid=obj.id)
        if errors:
            obj.error_log = '\n'.join(errors)
        obj.import_user = str(request.user)
        obj.import_date = datetime.now()
        obj.save()

    def filename_defaults(self, filename):
        """ Override this method to supply filename based data """
        defaults = []
        splitters = {'/':-1, '.':0, '_':0}
        for splitter, index in splitters.items():
            if filename.find(splitter)>-1:
                filename = filename.split(splitter)[index]
        return defaults

admin.site.register(CSVImport, CSVImportAdmin)

########NEW FILE########
__FILENAME__ = conf
from appconf import AppConf
from django.conf import settings


class CSVImportConf(AppConf):
    MODELS = []
    MEDIA_ROOT = settings.MEDIA_ROOT

########NEW FILE########
__FILENAME__ = csvimport
# Run sql files via django#
# www.heliosfoundation.org
import os, csv, re
from datetime import datetime
import codecs
import chardet
from ...signals import imported_csv, importing_csv

from django.db import DatabaseError
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import LabelCommand, BaseCommand
from optparse import make_option
from django.db import models
from django.contrib.contenttypes.models import ContentType

from django.conf import settings
CSVIMPORT_LOG = getattr(settings, 'CSVIMPORT_LOG', 'screen')
if CSVIMPORT_LOG == 'logger':
    import logging
    logger = logging.getLogger(__name__)

INTEGER = ['BigIntegerField', 'IntegerField', 'AutoField',
           'PositiveIntegerField', 'PositiveSmallIntegerField']
FLOAT = ['DecimalField', 'FloatField']
NUMERIC = INTEGER + FLOAT
BOOLEAN = ['BooleanField', 'NullBooleanField']
BOOLEAN_TRUE = [1, '1', 'Y', 'Yes', 'yes', 'True', 'true', 'T', 't']
# Note if mappings are manually specified they are of the following form ...
# MAPPINGS = "column1=shared_code,column2=org(Organisation|name),column3=description"
# statements = re.compile(r";[ \t]*$", re.M)

def save_csvimport(props=None, instance=None):
    """ To avoid circular imports do saves here """
    try:
        if not instance:
            from csvimport.models import CSVImport
            csvimp = CSVImport()
        if props:
            for key, value in props.items():
                setattr(csvimp, key, value)
        csvimp.save()
        return csvimp.id
    except:
        # Running as command line
        print 'Assumed charset = %s\n' % instance.charset
        print '###############################\n'
        for line in instance.loglist:
            if type(line) != type(''):
                for subline in line:
                    print subline
                    print
            else:
                print line
                print

class Command(LabelCommand):
    """
    Parse and map a CSV resource to a Django model.

    Notice that the doc tests are merely illustrational, and will not run
    as is.
    """

    option_list = BaseCommand.option_list + (
               make_option('--mappings', default='',
                           help='Please provide the file to import from'),
               make_option('--model', default='iisharing.Item',
                           help='Please provide the model to import to'),
               make_option('--charset', default='',
                           help='Force the charset conversion used rather than detect it')
                   )
    help = "Imports a CSV file to a model"


    def __init__(self):
        """ Set default attributes data types """
        super(Command, self).__init__()
        self.props = {}
        self.debug = False
        self.errors = []
        self.loglist = []
        self.mappings = []
        self.defaults = []
        self.app_label = ''
        self.model = ''
        self.fieldmap = {}
        self.file_name = ''
        self.nameindexes = False
        self.deduplicate = True
        self.csvfile = []
        self.charset = ''

    def handle_label(self, label, **options):
        """ Handle the circular reference by passing the nested
            save_csvimport function
        """
        filename = label
        mappings = options.get('mappings', [])
        modelname = options.get('model', 'Item')
        charset = options.get('charset', '')
        # show_traceback = options.get('traceback', True)
        self.setup(mappings, modelname, charset, filename)
        if not hasattr(self.model, '_meta'):
            msg = 'Sorry your model could not be found please check app_label.modelname'
            try:
                print msg
            except:
                self.loglist.append(msg)
            return
        errors = self.run()
        if self.props:
            save_csvimport(self.props, self)
        self.loglist.extend(errors)
        return

    def setup(self, mappings, modelname, charset, csvfile='', defaults='',
              uploaded=None, nameindexes=False, deduplicate=True):
        """ Setup up the attributes for running the import """
        self.defaults = self.__mappings(defaults)
        if modelname.find('.') > -1:
            app_label, model = modelname.split('.')
        self.charset = charset
        self.app_label = app_label
        self.model = models.get_model(app_label, model)
        for field in self.model._meta.fields:
            self.fieldmap[field.name] = field
            if field.__class__ == models.ForeignKey:
                self.fieldmap[field.name+"_id"] = field
        if mappings:
            # Test for column=name or just name list format
            if mappings.find('=') == -1:
                mappings = self.parse_header(mappings.split(','))
            self.mappings = self.__mappings(mappings)
        self.nameindexes = bool(nameindexes)
        self.file_name = csvfile
        self.deduplicate = deduplicate
        if uploaded:
            self.csvfile = self.__csvfile(uploaded.path)
        else:
            self.check_filesystem(csvfile)

    def check_fkey(self, key, field):
        """ Build fkey mapping via introspection of models """
        #TODO fix to find related field name rather than assume second field
        if not key.endswith('_id'):
            if field.__class__ == models.ForeignKey:
                key += '(%s|%s)' % (field.related.parent_model.__name__,
                                    field.related.parent_model._meta.fields[1].name,)
        return key

    def check_filesystem(self, csvfile):
        """ Check for files on the file system """
        if os.path.exists(csvfile):
            if os.path.isdir(csvfile):
                self.csvfile = []
                for afile in os.listdir(csvfile):
                    if afile.endswith('.csv'):
                        filepath = os.path.join(csvfile, afile)
                        try:
                            lines = self.__csvfile(filepath)
                            self.csvfile.extend(lines)
                        except:
                            pass
            else:
                self.csvfile = self.__csvfile(csvfile)
        if not getattr(self, 'csvfile', []):
            raise Exception('File %s not found' % csvfile)

    def run(self, logid=0):
        """ Run the csvimport """
        loglist = []
        if self.nameindexes:
            indexes = self.csvfile.pop(0)
        counter = 0
        if logid:
            csvimportid = logid
        else:
            csvimportid = 0

        if self.mappings:
            loglist.append('Using manually entered mapping list')
        else:
            mappingstr = self.parse_header(self.csvfile[0])
            if mappingstr:
                loglist.append('Using mapping from first row of CSV file')
                self.mappings = self.__mappings(mappingstr)
        if not self.mappings:
            loglist.append('''No fields in the CSV file match %s.%s\n
                                   - you must add a header field name row
                                   to the CSV file or supply a mapping list''' %
                                (self.model._meta.app_label, self.model.__name__))
            return loglist
        for row in self.csvfile[1:]:
            if CSVIMPORT_LOG == 'logger':
                logger.info("Import %s %i", self.model.__name__, counter)
            counter += 1

            model_instance = self.model()
            model_instance.csvimport_id = csvimportid


            for (column, field, foreignkey) in self.mappings:
                field_type = self.fieldmap.get(field).get_internal_type()
                if self.nameindexes:
                    column = indexes.index(column)
                else:
                    column = int(column)-1

                try:
                    row[column] = row[column].strip()
                except AttributeError:
                    pass

                if foreignkey:
                    row[column] = self.insert_fkey(foreignkey, row[column])

                if self.debug:
                    loglist.append('%s.%s = "%s"' % (self.model.__name__,
                                                          field, row[column]))
                # Tidy up boolean data
                if field_type in BOOLEAN:
                    row[column] = row[column] in BOOLEAN_TRUE

                # Tidy up numeric data
                if field_type in NUMERIC:
                    if not row[column]:
                        row[column] = 0
                    else:
                        try:
                            row[column] = float(row[column])
                        except:
                            loglist.append('Column %s = %s is not a number so is set to 0' \
                                                % (field, row[column]))
                            row[column] = 0
                    if field_type in INTEGER:
                        if row[column] > 9223372036854775807:
                            loglist.append('Column %s = %s more than the max integer 9223372036854775807' \
                                                % (field, row[column]))
                        if str(row[column]).lower() in ('nan', 'inf', '+inf', '-inf'):
                            loglist.append('Column %s = %s is not an integer so is set to 0' \
                                                % (field, row[column]))
                            row[column] = 0
                        row[column] = int(row[column])
                        if row[column] < 0 and field_type.startswith('Positive'):
                            loglist.append('Column %s = %s, less than zero so set to 0' \
                                                % (field, row[column]))
                            row[column] = 0
                try:
                    model_instance.__setattr__(field, row[column])
                except:
                    try:
                        row[column] = model_instance.getattr(field).to_python(row[column])
                    except:
                        try:
                            row[column] = datetime(row[column])
                        except:
                            row[column] = None
                            loglist.append('Column %s failed' % field)

            if self.defaults:
                for (field, value, foreignkey) in self.defaults:
                    try:
                        done = model_instance.getattr(field)
                    except:
                        done = False
                    if not done:
                        if foreignkey:
                            value = self.insert_fkey(foreignkey, value)
                        model_instance.__setattr__(field, value)
            if self.deduplicate:
                matchdict = {}
                for (column, field, foreignkey) in self.mappings:
                    matchdict[field + '__exact'] = getattr(model_instance,
                                                           field, None)
                try:
                    self.model.objects.get(**matchdict)
                    continue
                except ObjectDoesNotExist:
                    pass
                except OverflowError:
                    pass
            try:

                importing_csv.send(sender=model_instance,
                                    row=dict(zip(self.csvfile[:1][0], row)))
                model_instance.save()
                imported_csv.send(sender=model_instance,
                                  row=dict(zip(self.csvfile[:1][0], row)))

            except DatabaseError, err:
                try:
                    error_number, error_message = err
                except:
                    error_message = err
                    error_number = 0
                # Catch duplicate key error.
                if error_number != 1062:
                    loglist.append(
                        'Database Error: %s, Number: %d' % (error_message,
                                                            error_number))
            except OverflowError:
                pass

            if CSVIMPORT_LOG == 'logger':
                for line in loglist:
                    logger.info(line)
            self.loglist.extend(loglist)
            loglist = []
        if self.loglist:
            self.props = {'file_name':self.file_name,
                          'import_user':'cron',
                          'upload_method':'cronjob',
                          'error_log':'\n'.join(loglist),
                          'import_date':datetime.now()}
            return self.loglist
        else:
            return ['No logging', ]

    def parse_header(self, headlist):
        """ Parse the list of headings and match with self.fieldmap """
        mapping = []
        for i, heading in enumerate(headlist):
            for key in ((heading, heading.lower(),
                         ) if heading != heading.lower() else (heading,)):
                if self.fieldmap.has_key(key):
                    field = self.fieldmap[key]
                    key = self.check_fkey(key, field)
                    mapping.append('column%s=%s' % (i+1, key))
        if mapping:
            return ','.join(mapping)
        return ''

    def insert_fkey(self, foreignkey, rowcol):
        """ Add fkey if not present
            If there is corresponding data in the model already,
            we do not need to add more, since we are dealing with
            foreign keys, therefore foreign data
        """
        fk_key, fk_field = foreignkey
        if fk_key and fk_field:
            try:
                new_app_label = ContentType.objects.get(model=fk_key).app_label
            except:
                new_app_label = self.app_label
            fk_model = models.get_model(new_app_label, fk_key)
            matches = fk_model.objects.filter(**{fk_field+'__exact':
                                                 rowcol})

            if not matches:
                key = fk_model()
                key.__setattr__(fk_field, rowcol)
                key.save()

            rowcol = fk_model.objects.filter(**{fk_field+'__exact': rowcol})[0]
        return rowcol

    def error(self, message, type=1):
        """
        Types:
            0. A fatal error. The most drastic one. Will quit the program.
            1. A notice. Some minor thing is in disorder.
        """

        types = (
            ('Fatal error', FatalError),
            ('Notice', None),
        )

        self.errors.append((message, type))

        if type == 0:
            # There is nothing to do. We have to quit at this point
            raise types[0][1], message
        elif self.debug == True:
            print "%s: %s" % (types[type][0], message)

    def __csvfile(self, datafile):
        """ Detect file encoding and open appropriately """
        filehandle = open(datafile)
        if not self.charset:
            diagnose = chardet.detect(filehandle.read())
            self.charset = diagnose['encoding']
        try:
            csvfile = codecs.open(datafile, 'r', self.charset)
        except IOError:
            self.error('Could not open specified csv file, %s, or it does not exist' % datafile, 0)
        else:
            # CSV Reader returns an iterable, but as we possibly need to
            # perform list commands and since list is an acceptable iterable,
            # we'll just transform it.
            return list(self.charset_csv_reader(csv_data=csvfile,
                                                charset=self.charset))

    def charset_csv_reader(self, csv_data, dialect=csv.excel,
                           charset='utf-8', **kwargs):
        csv_reader = csv.reader(self.charset_encoder(csv_data, charset),
                                dialect=dialect, **kwargs)
        for row in csv_reader:
            # decode charset back to Unicode, cell by cell:
            yield [unicode(cell, charset) for cell in row]

    def charset_encoder(self, csv_data, charset='utf-8'):
        for line in csv_data:
            yield line.encode(charset)

    def __mappings(self, mappings):
        """
        Parse the mappings, and return a list of them.
        """
        if not mappings:
            return []

        def parse_mapping(args):
            """
            Parse the custom mapping syntax (column1=field1(ForeignKey|field),
            etc.)

            >>> parse_mapping('a=b(c|d)')
            [('a', 'b', '(c|d)')]
            """

            pattern = re.compile(r'(\w+)=(\w+)(\(\w+\|\w+\))?')
            mappings = pattern.findall(args)

            mappings = list(mappings)
            for mapping in mappings:
                mapp = mappings.index(mapping)
                mappings[mapp] = list(mappings[mapp])
                mappings[mapp][2] = parse_foreignkey(mapping[2])
                mappings[mapp] = tuple(mappings[mapp])
            mappings = list(mappings)
            
            return mappings

        def parse_foreignkey(key):
            """
            Parse the foreignkey syntax (Key|field)

            >>> parse_foreignkey('(a|b)')
            ('a', 'b')
            """

            pattern = re.compile(r'(\w+)\|(\w+)', re.U)
            if key.startswith('(') and key.endswith(')'):
                key = key[1:-1]

            found = pattern.search(key)

            if found != None:
                return (found.group(1), found.group(2))
            else:
                return None

        mappings = mappings.replace(',', ' ')
        mappings = mappings.replace('column', '')
        return parse_mapping(mappings)


class FatalError(Exception):
    """
    Something really bad happened.
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


########NEW FILE########
__FILENAME__ = models
from django.db import models
from csvimport.conf import settings
from copy import deepcopy
from django.core.files.storage import FileSystemStorage
import re

fs = FileSystemStorage(location=settings.MEDIA_ROOT)
CHOICES = (('manual', 'manual'), ('cronjob', 'cronjob'))

# Create your models here.
if not settings.CSVIMPORT_MODELS:
    MODELS = ['%s.%s' % (m._meta.app_label,
                         m.__name__) for m in models.loading.get_models()
                         if m._meta.app_label != 'contenttypes']
else:
    MODELS = deepcopy(settings.CSVIMPORT_MODELS)

MODELS = tuple([(m, m) for m in MODELS])


class CSVImport(models.Model):
    """ Logging model for importing files """
    model_name = models.CharField(max_length=255, blank=False,
                                  default='iisharing.Item',
                                  help_text='Please specify the app_label.model_name',
                                  choices=MODELS)
    field_list = models.CharField(max_length=255, blank=True,
                        help_text='''Enter list of fields in order only if
                                     you dont have a header row with matching field names, eg.
                                     "column1=shared_code,column2=org(Organisation|name)"''')
    upload_file = models.FileField(upload_to='csv', storage=fs)
    file_name = models.CharField(max_length=255, blank=True)
    encoding = models.CharField(max_length=32, blank=True)
    upload_method = models.CharField(blank=False, max_length=50,
                                     default='manual', choices=CHOICES)
    error_log = models.TextField(help_text='Each line is an import error')
    import_date = models.DateField(auto_now=True)
    import_user = models.CharField(max_length=255, default='anonymous',
                                   help_text='User id as text', blank=True)

    def error_log_html(self):
        return re.sub('\n', '<br/>', self.error_log)
    error_log_html.allow_tags = True

    def __unicode__(self):
        return self.upload_file.name


class ImportModel(models.Model):
    """ Optional one to one mapper of import file to Model """
    csvimport = models.ForeignKey(CSVImport)
    numeric_id = models.PositiveIntegerField()
    natural_key = models.CharField(max_length=100)

########NEW FILE########
__FILENAME__ = signals
from django import dispatch

imported_csv = dispatch.Signal(providing_args=['instance', 'row'])
importing_csv = dispatch.Signal(providing_args=['instance', 'row'])

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from csvimport.tests.models import Country, UnitOfMeasure, Organisation, Item

admin.site.register(Country)
admin.site.register(UnitOfMeasure)
admin.site.register(Organisation)
admin.site.register(Item)

########NEW FILE########
__FILENAME__ = log_tests
# -*- coding: utf-8 -*-
# Use unicode source code to make test character string writing easier
import os

from csvimport.management.commands.csvimport import CSVIMPORT_LOG
from django.conf import settings
from django.test import TestCase

class LogTest(TestCase):
    """ Run test of file parsing """
    logpath = ''

    def get_log_path(self):
        """ Get the log file that should of been written by the parse tests """
        if CSVIMPORT_LOG != 'logger':
            print '''CSVIMPORT_LOG is not set to 'logger' in settings
                     - assume not using csvimport.tests.settings
                     - so cannot test the log'''
            return False
        logging = getattr(settings, 'LOGGING', '')
        if logging:
            handlers = logging.get('handlers', {})
            if handlers:
                logfile = handlers.get('logfile', {})
                if logfile:
                    self.logpath = logfile.get('filename', '')
        if self.logpath.endswith('.log'):
            if os.path.exists(self.logpath):
                print 'Found csvimport_test.log'
                return True
        print '''cvsimport logging is not set up for %s from
                 csvimport.tests.settings so cannot test the log''' % self.logpath
        return False

    def test_log(self):
        """ Check the log is there and then remove it """
        if self.get_log_path():
            csvlog = open(self.logpath)
            lines = csvlog.read()
            self.assertIn('Column quantity = -23, less than zero so set to 0', lines)
            os.remove(self.logpath)
            print 'Deleted csvimport_test.log'
        return

########NEW FILE########
__FILENAME__ = models
# Test case models for cvsimport - add 'csvimport.tests' to installed apps to run
from django.db import models

class Country(models.Model):
    """
    ISO country (location) codes.
    and lat long for Geopoint Mapping
    """
    code = models.CharField(max_length=4, primary_key=True)
    name = models.CharField(max_length=255)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
    alias = models.CharField(max_length=255, null=True)


    def __unicode__(self):
        return u"%s (%s)" % (self.name, self.code)


class UnitOfMeasure(models.Model):
    name = models.CharField(max_length=32)


    def __unicode__(self):
        return self.name


class Organisation(models.Model):
    name = models.CharField(max_length=255)


    def __unicode__(self):
        return self.name

    class Meta:
        db_table = u'tests_organisation'
        managed = True


class Item(models.Model):
    TYPE = models.PositiveIntegerField(default=0)
    code_share = models.CharField(
        max_length=32,
        help_text = "Cross-organization item code")
    code_org = models.CharField(
        max_length=32,
        help_text="Organization-specfific item code")
    description = models.TextField(null=True)
    quantity = models.PositiveIntegerField(default=1)
    uom = models.ForeignKey(UnitOfMeasure,
                            help_text = 'Unit of Measure')
    organisation = models.ForeignKey(Organisation)
    status = models.CharField(max_length = 10, null=True)
    date = models.DateField(auto_now=True, null=True, validators=[])
    country = models.ForeignKey(Country, null=True)



########NEW FILE########
__FILENAME__ = optional_tests
""" Test use of optional command line args """
from csvimport.tests.testcase import CommandTestCase
from csvimport.management.commands.csvimport import Command
from csvimport.tests.models import Item

class CommandArgsTest(CommandTestCase):
    """ Run test of use of optional command line args - mappings, default and charset """

    def test_mappings(self, filename='test_headless.csv'):
        """ Use custom command to upload file and parse it into Items 
            Handle either mapping format
            TODO: add handling of spaces in defaults?
        """
        # header equivalent only mapping
        mappings='CODE_SHARE,CODE_ORG,ORGANISATION,DESCRIPTION,UOM,QUANTITY,STATUS'
        # errs = ['Using manually entered mapping list']
        self.command(filename, mappings=mappings) #, expected_errs=errs)
        item = self.get_item('sheeting')
        # Check a couple of the fields in Item
        self.assertEqual(item.code_org, 'RF007')
        self.assertEqual(item.description, 'Plastic sheeting, 4*60m, roll')
        # Check related Organisation model is created
        self.assertEqual(item.organisation.name, 'Save UK')
        Item.objects.all().delete()

        # full mapping
        mappings='''column1=code_share,column2=code_org,
                    column3=organisation(Organisation|name),
                    column5=uom(UnitOfMeasure|name),column7=status'''
        defaults='country=KE(Country|code),quantity=5,description=stuff'
        errs = ['Using manually entered mapping list']
        self.command(filename, mappings=mappings, defaults=defaults, expected_errs=errs)
        item = self.get_item('sheeting')
        # Check a couple of the fields in Item
        self.assertEqual(item.quantity, 5)
        self.assertEqual(item.code_org, 'RF007')
        self.assertEqual(item.description, 'stuff')
        # Check related Organisation model is created
        self.assertEqual(item.organisation.name, 'Save UK')
        Item.objects.all().delete()

    def test_default(self, filename='test_char.csv'):
        """ Check the default values over-ride those in the file 
            NB: Should we add an option to only make defaults change null values?
            ... maybe although all of that could be done post import anyway so
            this is more normally used to allow setting values for missing columns
        """
        defaults='code_org=ALLTHESAME,quantity=58'
        self.command(filename, defaults=defaults)
        item = self.get_item('watercan')
        self.assertNotEqual(item.code_org, 'CWATCONT20F')
        self.assertEqual(item.code_org, 'ALLTHESAME')
        self.assertNotEqual(item.quantity, 1000)
        self.assertEqual(item.quantity, 58)
        self.assertEqual(item.organisation.name, 'AID-France')
        Item.objects.all().delete()


########NEW FILE########
__FILENAME__ = parse_tests
# -*- coding: utf-8 -*-
# Use unicode source code to make test character string writing easier
from csvimport.tests.testcase import CommandTestCase
from csvimport.management.commands.csvimport import Command
from csvimport.tests.models import Item


class CommandParseTest(CommandTestCase):
    """ Run test of file parsing """

    def test_plain(self, filename='test_plain.csv'):
        """ Use custom command to upload file and parse it into Items """
        self.command(filename)
        item = self.get_item('sheeting')
        # Check a couple of the fields in Item
        self.assertEqual(item.code_org, 'RF007')
        self.assertEqual(item.description, 'Plastic sheeting, 4*60m, roll')
        # Check related Organisation model is created
        self.assertEqual(item.organisation.name, 'Save UK')
        Item.objects.all().delete()

    def test_char(self, filename='test_char.csv'):
        """ Use custom command parse file - test with odd non-ascii character """
        self.command(filename)
        item = self.get_item('watercan')
        self.assertEqual(item.code_org, 'CWATCONT20F')
        self.assertEqual(item.quantity, 1000)
        # self.assertEqual(unicode(item.uom), u'pi縦e')
        self.assertEqual(item.organisation.name, 'AID-France')
        Item.objects.all().delete()

    def test_char2(self, filename='test_char2.csv'):
        """ Use custom command to parse file with range of unicode characters """
        self.command(filename)
        item = self.get_item(u"Cet élément est utilisé par quelqu'un d'autre et ne peux être modifié")
        self.assertEqual(item.description,
                         "TENTE FAMILIALE, 12 m_, COMPLETE (tapis de sol/double toit)")
        self.assertEqual(item.quantity, 101)
        self.assertEqual(unicode(item.uom), u'删除当前图片')
        self.assertEqual(item.organisation.name, 'AID-France')
        Item.objects.all().delete()

    def test_duplicate(self, filename='test_duplicate.csv'):
        """ Use custom command to upload file and parse it into Items """
        self.command(filename)
        items = Item.objects.all().order_by('code_share')
        # Check a couple of the fields in Item
        self.assertEqual(len(items), 3)
        codes = (u'bucket', u'tent', u'watercan')
        for i, item in enumerate(items):
            self.assertEqual(item.code_share, codes[i])
        Item.objects.all().delete()

    def test_number(self, filename='test_number.csv'):
        """ Use command to parse file with problem numeric fields
            Missing field value, negative, fractions and too big
        """
        errs = [u'Column quantity = -23, less than zero so set to 0',
                u'Column quantity = 1e+28 more than the max integer 9223372036854775807',
                u'Column quantity = Not_a_Number is not a number so is set to 0',
                u'Column quantity = nan is not an integer so is set to 0',
                ]
        self.command(filename, expected_errs=errs)
        # check fractional numbers into integers
        items = Item.objects.filter(code_org='WA017')
        self.assertEqual(items[0].quantity, 33)
        # check empty values into zeros
        items = Item.objects.filter(code_org='WA041')
        self.assertEqual(items[0].quantity, 0)
        # 9223372036854775807 is the reliable limit so this wont work
        # test is to ensure that 1e+28 error above is reported
        items = Item.objects.filter(code_org='RF028')
        self.assertNotEqual(items[0].quantity, 9999999999999999999999999999)
        Item.objects.all().delete()


########NEW FILE########
__FILENAME__ = settings
# Settings to be used when running unit tests
# python manage.py test --settings=django-csvimport.tests.settings django-csvimport
import os

DEBUG = True
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'django-csvimport-test.db',
        'USER': '',     # Not used with sqlite3.
        'PASSWORD': '', # Not used with sqlite3.
        'HOST': '',     # Set to empty string for localhost. 
        'PORT': '',     # Set to empty string for default. 
    }
}
# If not set or CSVIMPORT = 'screen' then it only sends loglines to Admin UI display
CSVIMPORT_LOG = 'logger'
# Turn on logger usage and log to a text file to check for in tests ...
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'logfile': {
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': os.path.join(os.path.dirname(__file__), 
                                          'csvimport_test.log')
        },
    },
   'loggers': {
        'csvimport': {
            'handlers': ['logfile'],
            'level': 'DEBUG',
            'propagate': False,
        },
    }
}
MEDIA_ROOT = ''
MEDIA_URL = '/files/'
# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

INSTALLED_APPS = (
    # Add csvimport app itself and the tests models
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'csvimport',
    'csvimport.tests'
)
SITE_ID = 1

# This merely needs to be present - as long as your test case specifies a
# urls attribute, it does not need to be populated.
ROOT_URLCONF = 'csvimport.tests.urls'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 't_8)4w_csvimport_not_secret_test_key_7^b*s%w$zrud'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

# For CI testing of releases
try:
    import django_jenkins
    CI = True
except:
    CI = False

if CI:
    INSTALLED_APPS += ('django_jenkins',)
    PROJECT_APPS = ('csvimport.tests',)
    JENKINS_TASKS = ('django_jenkins.tasks.run_pylint',
                     'django_jenkins.tasks.with_coverage')


########NEW FILE########
__FILENAME__ = testcase
""" Base test case for command line manage.py csvimport """
import os

from django.test import TestCase
from django.core.exceptions import ObjectDoesNotExist

from csvimport.management.commands.csvimport import Command
from csvimport.tests.models import Item

DEFAULT_ERRS = ['Using mapping from first row of CSV file', ]


class DummyFileObj():
    """ Use to replace html upload / or command arg
        with test fixtures files
    """
    path = ''

    def set_path(self, filename):
        self.path = os.path.join(os.path.dirname(__file__),
                                 'fixtures',
                                 filename)

class CommandTestCase(TestCase):
    """ Run test of use of optional command line args - mappings, default and charset """

    def command(self, filename, 
                defaults='country=KE(Country|code)',
                mappings='',
                expected_errs=[]):
        """ Run core csvimport command to parse file """
        cmd = Command()
        uploaded = DummyFileObj()
        uploaded.set_path(filename)
        cmd.setup(mappings=mappings,
                  modelname='tests.Item',
                  charset='',
                  uploaded=uploaded,
                  defaults=defaults)

        # Report back any unnexpected parse errors
        # and confirm those that are expected.
        # Fail test if they are not matching
        errors = cmd.run(logid='commandtest')
        expected = [err for err in DEFAULT_ERRS]
        if expected_errs:
            expected.extend(expected_errs)
            expected.reverse()
        for err in expected:
            try:
                error = errors.pop()
                self.assertEqual(error, err)
            except:
                pass
        if errors:
            for err in errors:
                print err
        self.assertEqual(errors, [])

    def get_item(self, code_share='sheeting'):
        """ Get item for confirming import is OK """
        try:
            item = Item.objects.get(code_share__exact=code_share)
        except ObjectDoesNotExist:
            item = None
        self.assertTrue(item, 'Failed to get row from imported test.csv Items')
        return item

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.conf import settings
from csvimport.tests.views import index
admin.autodiscover()

# URL patterns for test django-csvimport install

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    (r'^index.html', index)
)

if settings.DEBUG:
    urlpatterns += patterns('',
        url(r'^(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT,
        }),
   )

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse

def index(request, template='README.txt', **kwargs):
    return HttpResponse ('''<html><body><h1>django-csvimport Test app</h1>
                  <p>You have installed the test django-csvimport 
                  application. Click on the <a href="/admin/">admin</a> 
                  to try it</p>
                  <p>NB: you must run<br /> 
                     django-admin.py syncdb --settings=csvimport.tests.settings <br />
                  first to create the test models. 
                  <p>Click on csvimport in the admin</p>
                  <p>Try importing data via the test csv files in
                     django-csvimport/csvimport/tests/fixtures folder</p>
                  <p>Click on Add csvimport</p>
                  <p>For example select Models name: tests.Country and upload the countries.csv file</p>
                  </body></html>''')

########NEW FILE########
