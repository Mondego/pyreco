__FILENAME__ = decorators
from django.utils.decorators import decorator_from_middleware

from audit_log.middleware import UserLoggingMiddleware
log_current_user = decorator_from_middleware(UserLoggingMiddleware)
########NEW FILE########
__FILENAME__ = middleware
from django.db.models import signals
from django.utils.functional import curry

from audit_log import registration
from audit_log.models import fields

class UserLoggingMiddleware(object):
    def process_request(self, request):
        if not request.method in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
            if hasattr(request, 'user') and request.user.is_authenticated():
                user = request.user
            else:
                user = None
            
            session = request.session.session_key
       

            update_pre_save_info = curry(self._update_pre_save_info, user, session)
            update_post_save_info = curry(self._update_post_save_info, user, session)

            signals.pre_save.connect(update_pre_save_info,  dispatch_uid = (self.__class__, request,), weak = False)
            signals.post_save.connect(update_post_save_info,  dispatch_uid = (self.__class__, request,), weak = False)

    
    def process_response(self, request, response):
        signals.pre_save.disconnect(dispatch_uid =  (self.__class__, request,))
        signals.post_save.disconnect(dispatch_uid =  (self.__class__, request,))
        return response
    

    def _update_pre_save_info(self, user, session, sender, instance, **kwargs):
        
        registry = registration.FieldRegistry(fields.LastUserField)
        if sender in registry:
            for field in registry.get_fields(sender):
                setattr(instance, field.name, user)

        registry = registration.FieldRegistry(fields.LastSessionKeyField)
        if sender in registry:
            for field in registry.get_fields(sender):
                setattr(instance, field.name, session)


    def _update_post_save_info(self, user, session, sender, instance, created, **kwargs ):
        if created:
            registry = registration.FieldRegistry(fields.CreatingUserField)
            if sender in registry:
                for field in registry.get_fields(sender):
                    setattr(instance, field.name, user)
                    setattr(instance, "_audit_log_ignore_update", True)
                    instance.save()
                    instance._audit_log_ignore_update = False
            
            registry = registration.FieldRegistry(fields.CreatingSessionKeyField)
            if sender in registry:
                for field in registry.get_fields(sender):
                    setattr(instance, field.name, session)
                    setattr(instance, "_audit_log_ignore_update", True)
                    instance.save()
                    instance._audit_log_ignore_update = False
########NEW FILE########
__FILENAME__ = fields
from django.db import models
from django.conf import settings

from audit_log import registration


class LastUserField(models.ForeignKey):
    """
    A field that keeps the last user that saved an instance
    of a model. None will be the value for AnonymousUser.
    """
    
    def __init__(self, to = getattr(settings, 'AUTH_USER_MODEL', 'auth.User'), null = True, editable = False,  **kwargs):
        super(LastUserField, self).__init__(to = to, null = null, editable = editable, **kwargs)
    
    def contribute_to_class(self, cls, name):
        super(LastUserField, self).contribute_to_class(cls, name)
        registry = registration.FieldRegistry(self.__class__)
        registry.add_field(cls, self)

class LastSessionKeyField(models.CharField):
    """
    A field that keeps a reference to the last session key that was used to access the model.
    """
    
    def __init__(self, max_length  = 40, null = True, editable = False,  **kwargs):
        super(LastSessionKeyField, self).__init__(max_length = 40, null = null, editable = editable, **kwargs)
    
    def contribute_to_class(self, cls, name):
        super(LastSessionKeyField, self).contribute_to_class(cls, name)
        registry = registration.FieldRegistry(self.__class__)
        registry.add_field(cls, self)

class CreatingUserField(LastUserField):
    """
    A field that keeps track of the user that created a model instance.
    This will only be set once upon an INSERT in the database.
    """
    #dont actually need to do anything, everything is handled by the parent class
    #the different logic goes in the middleware
    pass

class CreatingSessionKeyField(LastSessionKeyField):
    """
    A field that keeps track of the last session key with which a model instance was created.
    This will only be set once upon an INSERT in the database.
    """
    #dont actually need to do anything, everything is handled by the parent class
    #the different logic goes in the middleware
    pass


#South stuff:

rules = [((LastUserField, CreatingUserField),
    [],    
    {   
        'to': ['rel.to', {'default': getattr(settings, 'AUTH_USER_MODEL', 'auth.User')}],
        'null': ['null', {'default': True}],
    },)]

try:
    from south.modelsinspector import add_introspection_rules
    # Add the rules for the `LastUserField`
    add_introspection_rules(rules, ['^audit_log\.models\.fields\.LastUserField'])
    add_introspection_rules(rules, ['^audit_log\.models\.fields\.CreatingUserField'])
    add_introspection_rules([], ['^audit_log\.models\.fields\.LastSessionKeyField'])
    add_introspection_rules([], ['^audit_log\.models\.fields\.CreatingSessionKeyField'])
except ImportError:
    pass
########NEW FILE########
__FILENAME__ = managers
import copy
import datetime
from django.db import models
from django.utils.functional import curry
from django.utils.translation import ugettext_lazy as _

from audit_log.models.fields import LastUserField


try:
    from django.utils.timezone import now as datetime_now
    assert datetime_now
except ImportError:
    import datetime
    datetime_now = datetime.datetime.now


class LogEntryObjectDescriptor(object):
    def __init__(self, model):
        self.model = model
    
    def __get__(self, instance, owner):
        kwargs = dict((f.attname, getattr(instance, f.attname))
                    for f in self.model._meta.fields
                    if hasattr(instance, f.attname))
        return self.model(**kwargs)
        
      
class AuditLogManager(models.Manager):
    def __init__(self, model, instance = None):
        super(AuditLogManager, self).__init__()
        self.model = model
        self.instance = instance
    
    def get_queryset(self):
        if self.instance is None:
            return super(AuditLogManager, self).get_queryset()
        
        f = {self.instance._meta.pk.name : self.instance.pk}
        return super(AuditLogManager, self).get_queryset().filter(**f)
    
            
class AuditLogDescriptor(object):
    def __init__(self, model, manager_class):
        self.model = model
        self._manager_class = manager_class
    
    def __get__(self, instance, owner):
        if instance is None:
            return self._manager_class(self.model)
        return self._manager_class(self.model, instance)

class AuditLog(object):
    
    manager_class = AuditLogManager
    
    def __init__(self, exclude = []):
        self._exclude = exclude
    
    def contribute_to_class(self, cls, name):
        self.manager_name = name
        models.signals.class_prepared.connect(self.finalize, sender = cls)
    
    
    def create_log_entry(self, instance, action_type):
        manager = getattr(instance, self.manager_name)
        attrs = {}
        for field in instance._meta.fields:
            if field.attname not in self._exclude:
                attrs[field.attname] = getattr(instance, field.attname)
        manager.create(action_type = action_type, **attrs)
    
    def post_save(self, instance, created, **kwargs):
        #_audit_log_ignore_update gets attached right before a save on an instance
        #gets performed in the middleware
        #TODO I don't like how this is done
        if not getattr(instance, "_audit_log_ignore_update", False) or created:
            self.create_log_entry(instance, created and 'I' or 'U')
    
    
    def post_delete(self, instance, **kwargs):
        self.create_log_entry(instance,  'D')
    
    
    def finalize(self, sender, **kwargs):
        log_entry_model = self.create_log_entry_model(sender)
        
        models.signals.post_save.connect(self.post_save, sender = sender, weak = False)
        models.signals.post_delete.connect(self.post_delete, sender = sender, weak = False)
        
        descriptor = AuditLogDescriptor(log_entry_model, self.manager_class)
        setattr(sender, self.manager_name, descriptor)
    
    def copy_fields(self, model):
        """
        Creates copies of the fields we are keeping
        track of for the provided model, returning a 
        dictionary mapping field name to a copied field object.
        """
        fields = {'__module__' : model.__module__}
        
        for field in model._meta.fields:
            
            if not field.name in self._exclude:
                
                field  = copy.deepcopy(field)
            
                if isinstance(field, models.AutoField):
                    #we replace the AutoField of the original model
                    #with an IntegerField because a model can
                    #have only one autofield.
                
                    field.__class__ = models.IntegerField
                
                if field.primary_key:
                    field.serialize = True
            
                if field.primary_key or field.unique:
                    #unique fields of the original model
                    #can not be guaranteed to be unique
                    #in the audit log entry but they
                    #should still be indexed for faster lookups.
                
                    field.primary_key = False
                    field._unique = False
                    field.db_index = True
                    
                
                if field.rel and field.rel.related_name:
                    field.rel.related_name = '_auditlog_%s' % field.rel.related_name
            

                
                fields[field.name] = field
            
        return fields
    

    
    def get_logging_fields(self, model):
        """
        Returns a dictionary mapping of the fields that are used for
        keeping the acutal audit log entries.
        """
        rel_name = '_%s_audit_log_entry'%model._meta.object_name.lower()
      

        def entry_instance_to_unicode(log_entry):
            try:
                result = u'%s: %s %s at %s'%(model._meta.object_name, 
                                                log_entry.object_state, 
                                                log_entry.get_action_type_display().lower(),
                                                log_entry.action_date,
                                                
                                                )
            except AttributeError:
                result = u'%s %s at %s'%(model._meta.object_name,
                                                log_entry.get_action_type_display().lower(),
                                                log_entry.action_date
                                                
                                                )
            return result
        
        return {
            'action_id' : models.AutoField(primary_key = True),
            'action_date' : models.DateTimeField(default = datetime_now, editable = False, blank=False),
            'action_user' : LastUserField(related_name = rel_name, editable = False),
            'action_type' : models.CharField(max_length = 1, editable = False, choices = (
                ('I', _('Created')),
                ('U', _('Changed')),
                ('D', _('Deleted')),
            )),
            'object_state' : LogEntryObjectDescriptor(model),
            '__unicode__' : entry_instance_to_unicode,
        }
            
    
    def get_meta_options(self, model):
        """
        Returns a dictionary of Meta options for the
        autdit log model.
        """
        return {
            'ordering' : ('-action_date',),
            'app_label' : model._meta.app_label,
        }
    
    def create_log_entry_model(self, model):
        """
        Creates a log entry model that will be associated with
        the model provided.
        """
        
        attrs = self.copy_fields(model)
        attrs.update(self.get_logging_fields(model))
        attrs.update(Meta = type('Meta', (), self.get_meta_options(model)))
        name = '%sAuditLogEntry'%model._meta.object_name
        return type(name, (models.Model,), attrs)
        
########NEW FILE########
__FILENAME__ = registration
class FieldRegistry(object):
    _registry = {}
    
    def __init__(self, fieldcls):
        self._fieldcls = fieldcls

    
    def add_field(self, model, field):
        reg = self.__class__._registry.setdefault(self._fieldcls, {}).setdefault(model, [])
        reg.append(field)
    
    def get_fields(self, model):
        return self.__class__._registry.setdefault(self._fieldcls, {}).get(model, [])
    
    def __contains__(self, model):
        return model in self.__class__._registry.setdefault(self._fieldcls, {})


########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-audit-log documentation build configuration file, created by
# sphinx-quickstart on Wed Apr  6 10:51:31 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

sys.path.append(os.path.abspath('.'))
sys.path.append(os.path.abspath('..'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-audit-log'
copyright = u'2011, Vasil Vangelovski (Atomidata)'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
path = os.path.split(os.path.dirname(__file__))[0]
path = os.path.split(path)[0]
sys.path.insert(0, path)
import audit_log


version = '.'.join(map(str, audit_log.VERSION))
# The full version, including alpha/beta/rc tags.
release = audit_log.__version__

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
htmlhelp_basename = 'django-audit-logdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-audit-log.tex', u'django-audit-log Documentation',
   u'Vasil Vangelovski (Atomidata)', 'manual'),
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
    ('index', 'django-audit-log', u'django-audit-log Documentation',
     [u'Vasil Vangelovski (Atomidata)'], 1)
]

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testproject.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


########NEW FILE########
__FILENAME__ = settings
# Django settings for testproject project.
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
"""
Django settings for bom_generator project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'testproject.store',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'audit_log.middleware.UserLoggingMiddleware',
)

ROOT_URLCONF = 'testproject.urls'

WSGI_APPLICATION = 'testproject.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'
########NEW FILE########
__FILENAME__ = settings_custom_auth
from .settings import *

AUTH_USER_MODEL = "store.Employee"
########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from models import *

class CategoryAdmin(admin.ModelAdmin):
    pass


class ProductAdmin(admin.ModelAdmin):
    pass


class QuantityInline(admin.TabularInline):
    model = SoldQuantity
    


class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('date',)    
    inlines = [
        QuantityInline,
    ]
    
class ExtremeWidgetAdmin(admin.ModelAdmin):
    list_display  = ('name', 'special_power')
    

admin.site.register(ProductCategory, CategoryAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(WarehouseEntry, admin.ModelAdmin)
admin.site.register(SaleInvoice, InvoiceAdmin)
admin.site.register(ExtremeWidget, ExtremeWidgetAdmin)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.auth.models import (
    BaseUserManager, AbstractBaseUser
)

from audit_log.models.fields import LastUserField, LastSessionKeyField, CreatingUserField
from audit_log.models.managers import AuditLog

import datetime


class EmployeeManager(BaseUserManager):
    def create_user(self, email, password=None):
  
        if not email:
            raise ValueError('Users must have an email address')

        user = self.model(
            email=EmployeeManager.normalize_email(email),
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        u = self.create_user(email, password = password,)
        u.save(using=self._db)
        return u


class Employee(AbstractBaseUser):
    email = models.EmailField(
                        verbose_name='email address',
                        max_length=255, unique = True,
                    )
    USERNAME_FIELD = 'email'

    objects = EmployeeManager()

    @property
    def is_active(self):
        return True

    @property
    def is_superuser(self):
        return True

    @property
    def is_staff(self):
        return True

    @property
    def username(self):
        return self.email

    def get_full_name(self):
        return self.email

    def get_short_name(self):
        return self.email

    def __unicode__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

class ProductCategory(models.Model):
    created_by = CreatingUserField(related_name = "created_categories")
    modified_by = LastUserField(related_name = "modified_categories")
    name = models.CharField(max_length=150, primary_key = True)
    description = models.TextField()
    
    audit_log = AuditLog()
    
    def __unicode__(self):
        return self.name
    
class Product(models.Model):
    name = models.CharField(max_length = 150)
    description = models.TextField()
    price = models.DecimalField(max_digits = 10, decimal_places = 2)
    category = models.ForeignKey(ProductCategory)
    
    audit_log = AuditLog()
    
    
    def __unicode__(self):
        return self.name

class ProductRating(models.Model):
    user = LastUserField()
    session = LastSessionKeyField()
    product = models.ForeignKey(Product)
    rating = models.PositiveIntegerField()

class WarehouseEntry(models.Model):
    product = models.ForeignKey(Product)
    quantity = models.DecimalField(max_digits = 10, decimal_places = 2)
    
    audit_log = AuditLog()
    
    class Meta:
        app_label = "warehouse"


class SaleInvoice(models.Model):

    date = models.DateTimeField(default = datetime.datetime.now)

    audit_log = AuditLog(exclude = ['date',])
    
    
    def __unicode__(self):
        return str(self.date)

class SoldQuantity(models.Model):
    product = models.ForeignKey(Product)
    quantity = models.DecimalField(max_digits = 10, decimal_places = 2)
    sale = models.ForeignKey(SaleInvoice)

    audit_log = AuditLog()
    
    
    def __unicode__(self):
        return "%s X %s"%(self.product.name, self.quantity)


class Widget(models.Model):
    name = models.CharField(max_length = 100)

class ExtremeWidget(Widget):
    special_power = models.CharField(max_length = 100)
    
    audit_log = AuditLog()
########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from testproject.store.models import Product, WarehouseEntry, ProductCategory, ExtremeWidget, SaleInvoice, Employee
from django.test.client import Client

def __setup_admins():
    from django.contrib.auth.models import User
    User.objects.all().delete()
    admin = User(username = "admin@example.com", is_staff = True, is_superuser = True)
    admin.set_password("admin")
    admin.save()
    admin = User(username = "admin1@example.com", is_staff = True, is_superuser = True)
    admin.set_password("admin1")
    admin.save()

def __setup_employees():
    from store.models import Employee
    Employee.objects.all().delete()
    admin = Employee(email = "admin@example.com",)
    admin.set_password("admin")
    admin.save()
    admin = Employee(email = "admin1@example.com",)
    admin.set_password("admin1")
    admin.save()

def _setup_admin():
    from django.conf import settings
    if settings.AUTH_USER_MODEL =="store.Employee":
        __setup_employees()
    else:
        __setup_admins()


class LogEntryMetaOptionsTest(TestCase):
    
    def test_app_label(self):
        self.failUnlessEqual(Product.audit_log.model._meta.app_label, Product._meta.app_label)
        self.failUnlessEqual(WarehouseEntry.audit_log.model._meta.app_label, WarehouseEntry._meta.app_label)
    
    def test_table_name(self):
        self.failUnlessEqual(Product.audit_log.model._meta.db_table, "%sauditlogentry"%Product._meta.db_table)
        self.failUnlessEqual(WarehouseEntry.audit_log.model._meta.db_table, "%sauditlogentry"%WarehouseEntry._meta.db_table)

class TrackingFieldsTest(TestCase):
    def setUp(self):
        category  = ProductCategory.objects.create(name = "gadgets", description = "gadgetry")
        category.product_set.create(name = "new gadget", description = "best gadget eva", price = 100)


    def test_logging_user(self):
        _setup_admin()
        product = Product.objects.get(pk = 1)
        self.assertEqual(product.productrating_set.all().count(), 0)
        c = Client()
        c.login(username = "admin@example.com", password = "admin")
        c.post('/rate/1/', {'rating': 4})
        self.assertEqual(product.productrating_set.all().count(), 1)
        self.assertEqual(product.productrating_set.all()[0].user.username, "admin@example.com")
    
    def test_logging_session(self):
        _setup_admin()
        product = Product.objects.get(pk = 1)
        self.assertEqual(product.productrating_set.all().count(), 0)
        c = Client()
        c.login(username = "admin@example.com", password = "admin")
        c.get('/rate/1/',)
        key = c.session.session_key
        resp = c.post('/rate/1/', {'rating': 4})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(product.productrating_set.all().count(), 1)
        self.assertIsNotNone(product.productrating_set.all()[0].session)
        self.assertEqual(product.productrating_set.all()[0].session, key)

    def test_logging_anon_session(self):
        pass
        #TODO need to find a way to test this
        #product = Product.objects.get(pk = 1)
        #self.assertEqual(product.productrating_set.all().count(), 0)
        #c = Client()
        #resp = c.get('/')
        #self.assert_(hasattr(resp, "session"))
        #key = c.session.session_key
        #c.post('/rate/1', {'rating': 4})
        #self.assertEqual(product.productrating_set.all().count(), 1)
        #self.assertIsNotNone(product.productrating_set.all()[0].session)
        #self.assertEqual(product.productrating_set.all()[0].session, key)

    def test_logging_user_none(self):
        product = Product.objects.get(pk = 1)
        self.assertEqual(product.productrating_set.all().count(), 0)
        c = Client()
        c.post('/rate/1/', {'rating': 4})
        self.assertEqual(product.productrating_set.all().count(), 1)
        self.assertEqual(product.productrating_set.all()[0].user, None)



class LoggingTest(TestCase):
    
    def setup_client(self):
        c = Client()
        c.login(username = "admin@example.com", password = "admin")
        return c
    
    def test_logging_insert_update(self):
        _setup_admin()
        c = self.setup_client()
        c.post('/admin/store/productcategory/add/', {'name': 'Test Category', 'description': 'Test description'})
        self.failUnlessEqual(ProductCategory.objects.all().count(), 1)
        category = ProductCategory.objects.all()[0]
        self.failUnlessEqual(category.audit_log.all()[0].name, category.name)
        self.failUnlessEqual(category.audit_log.all()[0].description, category.description)
        self.failUnlessEqual(category.audit_log.all()[0].action_type, "I")
        self.failUnlessEqual(category.audit_log.all()[0].action_user.username, "admin@example.com")
    
        c.post('/admin/store/productcategory/%s/'%'Test Category', {'name': 'Test Category new name', 'description': 'Test description'})
        category = ProductCategory.objects.get(pk = "Test Category new name")
        self.failUnlessEqual(category.audit_log.all().count(), 1)
        self.failUnlessEqual(category.audit_log.all()[0].name, "Test Category new name")
        self.failUnlessEqual(category.audit_log.all()[0].action_type, "I")
        
        c.post('/admin/store/productcategory/%s/'%'Test Category new name', {'name': 'Test Category new name', 
                                                                            'description': 'Test modified description'})
        category = ProductCategory.objects.get(pk = "Test Category new name")
        self.failUnlessEqual(category.audit_log.all().count(), 2)
        self.failUnlessEqual(category.audit_log.all()[0].description, "Test modified description")
        self.failUnlessEqual(category.audit_log.all()[0].action_type, "U")
    
    def test_logging_delete(self):
        _setup_admin()
        c = self.setup_client()
        c.post('/admin/store/productcategory/add/', {'name': 'Test', 'description': 'Test description'})
        self.failUnlessEqual(ProductCategory.objects.all().count(), 1)
        c.post('/admin/store/productcategory/Test/delete/', {'post': 'yes'})
        self.failUnlessEqual(ProductCategory.objects.all().count(), 0)
        self.failUnlessEqual(ProductCategory.audit_log.all().count(), 2)
        self.failUnlessEqual(ProductCategory.audit_log.all()[0].action_type, "D")        
        
        
    def test_logging_inherited(self):
        _setup_admin()
        c = Client()
        c.login(username = "admin@example.com", password = "admin")
        c.post('/admin/store/extremewidget/add/', {'name': 'Test name', 'special_power': 'Testpower'})
        widget = ExtremeWidget.objects.all()[0]
        self.failUnlessEqual(widget.audit_log.all()[0].name, 'Test name')
        self.failUnlessEqual(hasattr(widget.audit_log.all()[0], 'special_power'), True)
        self.failUnlessEqual(widget.audit_log.all()[0].special_power, "Testpower")
        
        
########NEW FILE########
__FILENAME__ = views
# Create your views here.
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.template import Template, RequestContext
from store.models import Product, ProductRating

def rate_product(request, product_id):
    
    if request.method == 'POST':
        product = get_object_or_404(Product, pk = long(product_id))
        product.productrating_set.create(rating = int(request.POST.get('rating')))
        return HttpResponse(status = 200)
    else:
        c = RequestContext(request, {})
        return HttpResponse(Template("""
            <html><body><form action="." method="post">{% csrf_token %}
            <input type="text" name="rating"/>
            <input type="submit" value="Submit">
            </form></body></html>   
            """).render(c)
            )

def index(request):
    request.session['hello'] = 'world'
    request.session.save()
    return HttpResponse("Hello World")

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^testproject/', include('testproject.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^rate/(\d)/$', 'store.views.rate_product'),
    url(r'^$', 'store.views.index'),
     (r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for bom_generator project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "testproject.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

########NEW FILE########
