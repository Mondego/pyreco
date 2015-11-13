__FILENAME__ = documentoptions
import sys
from collections import MutableMapping
from types import MethodType

from django.db.models.fields import FieldDoesNotExist
from django.utils.text import capfirst
from django.db.models.options import get_verbose_name
from django.utils.functional import LazyObject
from django.conf import settings

from mongoengine.fields import ReferenceField, ListField


def patch_document(function, instance, bound=True):
    if bound:
        method = MethodType(function, instance)
    else:
        method = function
    setattr(instance, function.__name__, method)


def create_verbose_name(name):
    name = get_verbose_name(name)
    name = name.replace('_', ' ')
    return name


class Relation(object):
    # just an empty dict to make it useable with Django
    # mongoengine has no notion of this
    limit_choices_to = {}

    def __init__(self, to):
        self._to = to

    @property
    def to(self):
        if not isinstance(self._to._meta, (DocumentMetaWrapper, LazyDocumentMetaWrapper)):
            self._to._meta = DocumentMetaWrapper(self._to)
        return self._to

    @to.setter
    def to(self, value):
        self._to = value


class PkWrapper(object):
    editable = False
    fake = False
    
    def __init__(self, wrapped):
        self.obj = wrapped

    def __getattr__(self, attr):
        if attr in dir(self.obj):
            return getattr(self.obj, attr)
        raise AttributeError

    def __setattr__(self, attr, value):
        if attr != 'obj' and hasattr(self.obj, attr):
            setattr(self.obj, attr, value)
        super(PkWrapper, self).__setattr__(attr, value)


class LazyDocumentMetaWrapper(LazyObject):
    _document = None
    _meta = None
    
    def __init__(self, document):
        self._document = document
        self._meta = document._meta
        super(LazyDocumentMetaWrapper, self).__init__()
        
    def _setup(self):
        self._wrapped = DocumentMetaWrapper(self._document, self._meta)
        
    def __setattr__(self, name, value):
        if name in ["_document", "_meta",]:
            object.__setattr__(self, name, value)
        else:
            super(LazyDocumentMetaWrapper, self).__setattr__(name, value)
    
    def __dir__(self):
        return self._wrapped.__dir__()
    
    def __getitem__(self, key):
        return self._wrapped.__getitem__(key)
    
    def __setitem__(self, key, value):
        return self._wrapped.__getitem__(key, value)
        
    def __delitem__(self, key):
        return self._wrapped.__delitem__(key)
        
    def __len__(self):
        return self._wrapped.__len__()
        
    def __contains__(self, key):
        return self._wrapped.__contains__(key)
        

class DocumentMetaWrapper(MutableMapping):
    """
    Used to store mongoengine's _meta dict to make the document admin
    as compatible as possible to django's meta class on models.
    """
    # attributes Django deprecated. Not really sure when to remove them
    _deprecated_attrs = {'module_name': 'model_name'}

    pk = None
    pk_name = None
    _app_label = None
    model_name = None
    _verbose_name = None
    has_auto_field = False
    object_name = None
    proxy = []
    parents = {}
    many_to_many = []
    _field_cache = None
    document = None
    _meta = None
    concrete_model = None
    concrete_managers = []
    virtual_fields = []
    auto_created = False

    def __init__(self, document, meta=None):
        super(DocumentMetaWrapper, self).__init__()

        self.document = document
        # used by Django to distinguish between abstract and concrete models
        # here for now always the document
        self.concrete_model = document
        if meta is None:
            meta = getattr(document, '_meta', {})
            if isinstance(meta, LazyDocumentMetaWrapper):
                meta = meta._meta
        self._meta = meta

        try:
            self.object_name = self.document.__name__
        except AttributeError:
            self.object_name = self.document.__class__.__name__

        self.model_name = self.object_name.lower()

        # add the gluey stuff to the document and it's fields to make
        # everything play nice with Django
        self._setup_document_fields()
        # Setup self.pk if the document has an id_field in it's meta
        # if it doesn't have one it's an embedded document
        #if 'id_field' in self._meta:
        #    self.pk_name = self._meta['id_field']
        self._init_pk()

    def _setup_document_fields(self):
        for f in self.document._fields.values():
            # Yay, more glue. Django expects fields to have a couple attributes
            # at least in the admin, probably in more places.
            if not hasattr(f, 'rel'):
                # need a bit more for actual reference fields here
                if isinstance(f, ReferenceField):
                    f.rel = Relation(f.document_type)
                elif isinstance(f, ListField) and \
                        isinstance(f.field, ReferenceField):
                    f.field.rel = Relation(f.field.document_type)
                else:
                    f.rel = None
            if not hasattr(f, 'verbose_name') or f.verbose_name is None:
                f.verbose_name = capfirst(create_verbose_name(f.name))
            if not hasattr(f, 'flatchoices'):
                flat = []
                if f.choices is not None:
                    for choice, value in f.choices:
                        if isinstance(value, (list, tuple)):
                            flat.extend(value)
                        else:
                            flat.append((choice, value))
                f.flatchoices = flat
            if isinstance(f, ReferenceField) and not \
                    isinstance(f.document_type._meta, (DocumentMetaWrapper, LazyDocumentMetaWrapper)) and \
                    self.document != f.document_type:
                f.document_type._meta = LazyDocumentMetaWrapper(f.document_type)

    def _init_pk(self):
        """
        Adds a wrapper around the documents pk field. The wrapper object gets
        the attributes django expects on the pk field, like name and attname.

        The function also adds a _get_pk_val method to the document.
        """
        if 'id_field' in self._meta:
            self.pk_name = self._meta['id_field']
            pk_field = getattr(self.document, self.pk_name)
        else:
            pk_field = None
        self.pk = PkWrapper(pk_field)

        def _get_pk_val(self):
            return self._pk_val
        
        if pk_field is not None:
            self.pk.name = self.pk_name
            self.pk.attname = self.pk_name
            self.document._pk_val = pk_field
            patch_document(_get_pk_val, self.document)
        else:
            self.pk.fake = True
            # this is used in the admin and used to determine if the admin
            # needs to add a hidden pk field. It does not for embedded fields.
            # So we pretend to have an editable pk field and just ignore it otherwise
            self.pk.editable = True
    
    @property
    def app_label(self):
        if self._app_label is None:
            model_module = sys.modules[self.document.__module__]
            self._app_label = model_module.__name__.split('.')[-2]
        return self._app_label
            
    @property
    def verbose_name(self):
        """
        Returns the verbose name of the document.
        
        Checks the original meta dict first. If it is not found
        then generates a verbose name from the object name.
        """
        if self._verbose_name is None:
            verbose_name = self._meta.get('verbose_name', self.object_name)
            self._verbose_name = capfirst(create_verbose_name(verbose_name))
        return self._verbose_name
    
    @property
    def verbose_name_raw(self):
        return self.verbose_name
    
    @property
    def verbose_name_plural(self):
        return "%ss" % self.verbose_name
                
    def get_add_permission(self):
        return 'add_%s' % self.object_name.lower()

    def get_change_permission(self):
        return 'change_%s' % self.object_name.lower()

    def get_delete_permission(self):
        return 'delete_%s' % self.object_name.lower()
    
    def get_ordered_objects(self):
        return []
    
    def get_field_by_name(self, name):
        """
        Returns the (field_object, model, direct, m2m), where field_object is
        the Field instance for the given name, model is the model containing
        this field (None for local fields), direct is True if the field exists
        on this model, and m2m is True for many-to-many relations. When
        'direct' is False, 'field_object' is the corresponding RelatedObject
        for this field (since the field doesn't have an instance associated
        with it).
        """
        if name in self.document._fields:
            field = self.document._fields[name]
            if isinstance(field, ReferenceField):
                return (field, field.document_type, False, False)
            else:
                return (field, None, True, False)
        else:
            raise FieldDoesNotExist('%s has no field named %r' %
                                    (self.object_name, name))
         
    def get_field(self, name, many_to_many=True):
        """
        Returns the requested field by name. Raises FieldDoesNotExist on error.
        """
        return self.get_field_by_name(name)[0]
    
    @property
    def swapped(self):
        """
        Has this model been swapped out for another? If so, return the model
        name of the replacement; otherwise, return None.

        For historical reasons, model name lookups using get_model() are
        case insensitive, so we make sure we are case insensitive here.
        
        NOTE: Not sure this is actually usefull for documents. So at the
        moment it's really only here because the admin wants it. It might
        prove usefull for someone though, so it's more then just a dummy.
        """
        if self._meta.get('swappable', False):
            model_label = '%s.%s' % (self.app_label, self.object_name.lower())
            swapped_for = getattr(settings, self.swappable, None)
            if swapped_for:
                try:
                    swapped_label, swapped_object = swapped_for.split('.')
                except ValueError:
                    # setting not in the format app_label.model_name
                    # raising ImproperlyConfigured here causes problems with
                    # test cleanup code - instead it is raised in
                    # get_user_model or as part of validation.
                    return swapped_for

                if '%s.%s' % (swapped_label, swapped_object.lower()) \
                        not in (None, model_label):
                    return swapped_for
        return None
    
    def __getattr__(self, name):
        if name in self._deprecated_attrs:
            return getattr(self, self._deprecated_attrs.get(name))
            
        try:
            return self._meta[name]
        except KeyError:
            raise AttributeError
                    
    def __setattr__(self, name, value):
        if not hasattr(self, name):
            self._meta[name] = value
        else:
            super(DocumentMetaWrapper, self).__setattr__(name, value)
    
    def __contains__(self, key):
        return key in self._meta
    
    def __getitem__(self, key):
        return self._meta[key]
    
    def __setitem__(self, key, value):
        self._meta[key] = value

    def __delitem__(self, key):
        return self._meta.__delitem__(key)

    def __iter__(self):
        return self._meta.__iter__()

    def __len__(self):
        return self._meta.__len__()

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default
    
    def get_parent_list(self):
        return []
    
    def get_all_related_objects(self, *args, **kwargs):
        return []

    def iteritems(self):
        return iter(self._meta.items())

########NEW FILE########
__FILENAME__ = documents
import os
import itertools
from collections import Callable, OrderedDict
from functools import reduce

from django.forms.forms import (BaseForm, get_declared_fields,
                                NON_FIELD_ERRORS, pretty_name)
from django.forms.widgets import media_property
from django.core.exceptions import FieldError
from django.core.validators import EMPTY_VALUES
from django.forms.util import ErrorList
from django.forms.formsets import BaseFormSet, formset_factory
from django.utils.translation import ugettext_lazy as _, ugettext
from django.utils.text import capfirst, get_valid_filename

from mongoengine.fields import (ObjectIdField, ListField, ReferenceField,
                                FileField, MapField, EmbeddedDocumentField)
try:
    from mongoengine.base import ValidationError
except ImportError:
    from mongoengine.errors import ValidationError
from mongoengine.queryset import OperationError, Q
from mongoengine.queryset.base import BaseQuerySet
from mongoengine.connection import get_db, DEFAULT_CONNECTION_NAME
from mongoengine.base import NON_FIELD_ERRORS as MONGO_NON_FIELD_ERRORS

from gridfs import GridFS

from mongodbforms.documentoptions import DocumentMetaWrapper
from mongodbforms.util import with_metaclass, load_field_generator

_fieldgenerator = load_field_generator()


def _get_unique_filename(name, db_alias=DEFAULT_CONNECTION_NAME,
                         collection_name='fs'):
    fs = GridFS(get_db(db_alias), collection_name)
    file_root, file_ext = os.path.splitext(get_valid_filename(name))
    count = itertools.count(1)
    while fs.exists(filename=name):
        # file_ext includes the dot.
        name = os.path.join("%s_%s%s" % (file_root, next(count), file_ext))
    return name
    

def _save_iterator_file(field, instance, uploaded_file, file_data=None):
    """
    Takes care of saving a file for a list field. Returns a Mongoengine
    fileproxy object or the file field.
    """
    # for a new file we need a new proxy object
    if file_data is None:
        file_data = field.field.get_proxy_obj(key=field.name,
                                              instance=instance)
    
    if file_data.instance is None:
        file_data.instance = instance
    if file_data.key is None:
        file_data.key = field.name
    
    if file_data.grid_id:
        file_data.delete()
        
    uploaded_file.seek(0)
    filename = _get_unique_filename(uploaded_file.name, field.field.db_alias,
                                    field.field.collection_name)
    file_data.put(uploaded_file, content_type=uploaded_file.content_type,
                  filename=filename)
    file_data.close()
        
    return file_data


def construct_instance(form, instance, fields=None, exclude=None):
    """
    Constructs and returns a document instance from the bound ``form``'s
    ``cleaned_data``, but does not save the returned instance to the
    database.
    """
    cleaned_data = form.cleaned_data
    file_field_list = []
    
    # check wether object is instantiated
    if isinstance(instance, type):
        instance = instance()
        
    for f in instance._fields.values():
        if isinstance(f, ObjectIdField):
            continue
        if not f.name in cleaned_data:
            continue
        if fields is not None and f.name not in fields:
            continue
        if exclude and f.name in exclude:
            continue
        # Defer saving file-type fields until after the other fields, so a
        # callable upload_to can use the values from other fields.
        if isinstance(f, FileField) or \
                (isinstance(f, (MapField, ListField)) and
                 isinstance(f.field, FileField)):
            file_field_list.append(f)
        else:
            setattr(instance, f.name, cleaned_data.get(f.name))

    for f in file_field_list:
        if isinstance(f, MapField):
            map_field = getattr(instance, f.name)
            uploads = cleaned_data[f.name]
            for key, uploaded_file in uploads.items():
                if uploaded_file is None:
                    continue
                file_data = map_field.get(key, None)
                map_field[key] = _save_iterator_file(f, instance,
                                                     uploaded_file, file_data)
            setattr(instance, f.name, map_field)
        elif isinstance(f, ListField):
            list_field = getattr(instance, f.name)
            uploads = cleaned_data[f.name]
            for i, uploaded_file in enumerate(uploads):
                if uploaded_file is None:
                    continue
                try:
                    file_data = list_field[i]
                except IndexError:
                    file_data = None
                file_obj = _save_iterator_file(f, instance,
                                               uploaded_file, file_data)
                try:
                    list_field[i] = file_obj
                except IndexError:
                    list_field.append(file_obj)
            setattr(instance, f.name, list_field)
        else:
            field = getattr(instance, f.name)
            upload = cleaned_data[f.name]
            if upload is None:
                continue
            
            try:
                upload.file.seek(0)
                # delete first to get the names right
                if field.grid_id:
                    field.delete()
                filename = _get_unique_filename(upload.name, f.db_alias,
                                                f.collection_name)
                field.put(upload, content_type=upload.content_type,
                          filename=filename)
                setattr(instance, f.name, field)
            except AttributeError:
                # file was already uploaded and not changed during edit.
                # upload is already the gridfsproxy object we need.
                upload.get()
                setattr(instance, f.name, upload)
            
    return instance


def save_instance(form, instance, fields=None, fail_message='saved',
                  commit=True, exclude=None, construct=True):
    """
    Saves bound Form ``form``'s cleaned_data into document ``instance``.

    If commit=True, then the changes to ``instance`` will be saved to the
    database. Returns ``instance``.

    If construct=False, assume ``instance`` has already been constructed and
    just needs to be saved.
    """
    if construct:
        instance = construct_instance(form, instance, fields, exclude)
        
    if form.errors:
        raise ValueError("The %s could not be %s because the data didn't"
                         " validate." % (instance.__class__.__name__,
                                         fail_message))
    
    if commit and hasattr(instance, 'save'):
        # see BaseDocumentForm._post_clean for an explanation
        #if len(form._meta._dont_save) > 0:
        #    data = instance._data
        #    new_data = dict([(n, f) for n, f in data.items() if not n \
        #                    in form._meta._dont_save])
        #    instance._data = new_data
        #    instance.save()
        #    instance._data = data
        #else:
        instance.save()
    return instance


def document_to_dict(instance, fields=None, exclude=None):
    """
    Returns a dict containing the data in ``instance`` suitable for passing as
    a Form's ``initial`` keyword argument.

    ``fields`` is an optional list of field names. If provided, only the named
    fields will be included in the returned dict.

    ``exclude`` is an optional list of field names. If provided, the named
    fields will be excluded from the returned dict, even if they are listed in
    the ``fields`` argument.
    """
    data = {}
    for f in instance._fields.values():
        if fields and not f.name in fields:
            continue
        if exclude and f.name in exclude:
            continue
        data[f.name] = getattr(instance, f.name, '')
    return data


def fields_for_document(document, fields=None, exclude=None, widgets=None,
                        formfield_callback=None,
                        field_generator=_fieldgenerator):
    """
    Returns a ``SortedDict`` containing form fields for the given model.

    ``fields`` is an optional list of field names. If provided, only the named
    fields will be included in the returned fields.

    ``exclude`` is an optional list of field names. If provided, the named
    fields will be excluded from the returned fields, even if they are listed
    in the ``fields`` argument.
    """
    field_list = []
    if isinstance(field_generator, type):
        field_generator = field_generator()
        
    if formfield_callback and not isinstance(formfield_callback, Callable):
        raise TypeError('formfield_callback must be a function or callable')
    
    for name in document._fields_ordered:
        f = document._fields.get(name)
        if isinstance(f, ObjectIdField):
            continue
        if fields and not f.name in fields:
            continue
        if exclude and f.name in exclude:
            continue
        if widgets and f.name in widgets:
            kwargs = {'widget': widgets[f.name]}
        else:
            kwargs = {}

        if formfield_callback:
            formfield = formfield_callback(f, **kwargs)
        else:
            formfield = field_generator.generate(f, **kwargs)

        if formfield:
            field_list.append((f.name, formfield))
    
    field_dict = OrderedDict(field_list)
    if fields:
        field_dict = OrderedDict(
            [(f, field_dict.get(f)) for f in fields
                if ((not exclude) or (exclude and f not in exclude))]
        )

    return field_dict


class ModelFormOptions(object):
    def __init__(self, options=None):
        # document class can be declared with 'document =' or 'model ='
        self.document = getattr(options, 'document', None)
        if self.document is None:
            self.document = getattr(options, 'model', None)
            
        self.model = self.document
        meta = getattr(self.document, '_meta', {})
        # set up the document meta wrapper if document meta is a dict
        if self.document is not None and \
                not isinstance(meta, DocumentMetaWrapper):
            self.document._meta = DocumentMetaWrapper(self.document)
        self.fields = getattr(options, 'fields', None)
        self.exclude = getattr(options, 'exclude', None)
        self.widgets = getattr(options, 'widgets', None)
        self.embedded_field = getattr(options, 'embedded_field_name', None)
        self.formfield_generator = getattr(options, 'formfield_generator',
                                           _fieldgenerator)
        
        self._dont_save = []
        
        
class DocumentFormMetaclass(type):
    def __new__(cls, name, bases, attrs):
        formfield_callback = attrs.pop('formfield_callback', None)
        try:
            parents = [
                b for b in bases
                if issubclass(b, DocumentForm) or
                issubclass(b, EmbeddedDocumentForm)
            ]
        except NameError:
            # We are defining DocumentForm itself.
            parents = None
        declared_fields = get_declared_fields(bases, attrs, False)
        new_class = super(DocumentFormMetaclass, cls).__new__(cls, name,
                                                              bases, attrs)
        if not parents:
            return new_class

        if 'media' not in attrs:
            new_class.media = media_property(new_class)
        
        opts = new_class._meta = ModelFormOptions(
            getattr(new_class, 'Meta', None)
        )
        if opts.document:
            formfield_generator = getattr(opts,
                                          'formfield_generator',
                                          _fieldgenerator)
            
            # If a model is defined, extract form fields from it.
            fields = fields_for_document(opts.document, opts.fields,
                                         opts.exclude, opts.widgets,
                                         formfield_callback,
                                         formfield_generator)
            # make sure opts.fields doesn't specify an invalid field
            none_document_fields = [k for k, v in fields.items() if not v]
            missing_fields = (set(none_document_fields) -
                              set(declared_fields.keys()))
            if missing_fields:
                message = 'Unknown field(s) (%s) specified for %s'
                message = message % (', '.join(missing_fields),
                                     opts.model.__name__)
                raise FieldError(message)
            # Override default model fields with any custom declared ones
            # (plus, include all the other declared fields).
            fields.update(declared_fields)
        else:
            fields = declared_fields
            
        new_class.declared_fields = declared_fields
        new_class.base_fields = fields
        return new_class
    
    
class BaseDocumentForm(BaseForm):
    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix=':',
                 empty_permitted=False, instance=None):
        
        opts = self._meta
        
        if instance is None:
            if opts.document is None:
                raise ValueError('A document class must be provided.')
            # if we didn't get an instance, instantiate a new one
            self.instance = opts.document
            object_data = {}
        else:
            self.instance = instance
            object_data = document_to_dict(instance, opts.fields, opts.exclude)
        
        # if initial was provided, it should override the values from instance
        if initial is not None:
            object_data.update(initial)
        
        # self._validate_unique will be set to True by BaseModelForm.clean().
        # It is False by default so overriding self.clean() and failing to call
        # super will stop validate_unique from being called.
        self._validate_unique = False
        super(BaseDocumentForm, self).__init__(data, files, auto_id, prefix,
                                               object_data, error_class,
                                               label_suffix, empty_permitted)

    def _update_errors(self, message_dict):
        for k, v in list(message_dict.items()):
            if k != NON_FIELD_ERRORS:
                self._errors.setdefault(k, self.error_class()).extend(v)
                # Remove the invalid data from the cleaned_data dict
                if k in self.cleaned_data:
                    del self.cleaned_data[k]
        if NON_FIELD_ERRORS in message_dict:
            messages = message_dict[NON_FIELD_ERRORS]
            self._errors.setdefault(NON_FIELD_ERRORS,
                                    self.error_class()).extend(messages)

    def _get_validation_exclusions(self):
        """
        For backwards-compatibility, several types of fields need to be
        excluded from model validation. See the following tickets for
        details: #12507, #12521, #12553
        """
        exclude = []
        # Build up a list of fields that should be excluded from model field
        # validation and unique checks.
        for f in self.instance._fields.values():
            # Exclude fields that aren't on the form. The developer may be
            # adding these values to the model after form validation.
            if f.name not in self.fields:
                exclude.append(f.name)

            # Don't perform model validation on fields that were defined
            # manually on the form and excluded via the ModelForm's Meta
            # class. See #12901.
            elif self._meta.fields and f.name not in self._meta.fields:
                exclude.append(f.name)
            elif self._meta.exclude and f.name in self._meta.exclude:
                exclude.append(f.name)

            # Exclude fields that failed form validation. There's no need for
            # the model fields to validate them as well.
            elif f.name in list(self._errors.keys()):
                exclude.append(f.name)

            # Exclude empty fields that are not required by the form, if the
            # underlying model field is required. This keeps the model field
            # from raising a required error. Note: don't exclude the field from
            # validaton if the model field allows blanks. If it does, the blank
            # value may be included in a unique check, so cannot be excluded
            # from validation.
            else:
                field_value = self.cleaned_data.get(f.name, None)
                if not f.required and field_value in EMPTY_VALUES:
                    exclude.append(f.name)
        return exclude

    def clean(self):
        self._validate_unique = True
        return self.cleaned_data

    def _post_clean(self):
        opts = self._meta
        
        # Update the model instance with self.cleaned_data.
        self.instance = construct_instance(self, self.instance, opts.fields,
                                           opts.exclude)
        changed_fields = getattr(self.instance, '_changed_fields', [])

        exclude = self._get_validation_exclusions()
        try:
            for f in self.instance._fields.values():
                value = getattr(self.instance, f.name)
                if f.name not in exclude:
                    f.validate(value)
                elif value in EMPTY_VALUES and f.name not in changed_fields:
                    # mongoengine chokes on empty strings for fields
                    # that are not required. Clean them up here, though
                    # this is maybe not the right place :-)
                    setattr(self.instance, f.name, None)
                    #opts._dont_save.append(f.name)
        except ValidationError as e:
            err = {f.name: [e.message]}
            self._update_errors(err)

        # Call validate() on the document. Since mongoengine
        # does not provide an argument to specify which fields
        # should be excluded during validation, we replace
        # instance._fields_ordered with a version that does
        # not include excluded fields. The attribute gets
        # restored after validation.
        original_fields = self.instance._fields_ordered
        self.instance._fields_ordered = tuple(
            [f for f in original_fields if f not in exclude]
        )
        try:
            self.instance.validate()
        except ValidationError as e:
            if MONGO_NON_FIELD_ERRORS in e.errors:
                error = e.errors.get(MONGO_NON_FIELD_ERRORS)
            else:
                error = e.message
            self._update_errors({NON_FIELD_ERRORS: [error, ]})
        finally:
            self.instance._fields_ordered = original_fields

        # Validate uniqueness if needed.
        if self._validate_unique:
            self.validate_unique()

    def validate_unique(self):
        """
        Validates unique constrains on the document.
        unique_with is supported now.
        """
        errors = []
        exclude = self._get_validation_exclusions()
        for f in self.instance._fields.values():
            if f.unique and f.name not in exclude:
                filter_kwargs = {
                    f.name: getattr(self.instance, f.name),
                    'q_obj': None,
                }
                if f.unique_with:
                    for u_with in f.unique_with:
                        u_with_field = self.instance._fields[u_with]
                        u_with_attr = getattr(self.instance, u_with)
                        # handling ListField(ReferenceField()) sucks big time
                        # What we need to do is construct a Q object that
                        # queries for the pk of every list entry and only
                        # accepts lists with the same length as our list
                        if isinstance(u_with_field, ListField) and \
                                isinstance(u_with_field.field, ReferenceField):
                            q_list = [Q(**{u_with: k.pk}) for k in u_with_attr]
                            q = reduce(lambda x, y: x & y, q_list)
                            size_key = '%s__size' % u_with
                            q = q & Q(**{size_key: len(u_with_attr)})
                            filter_kwargs['q_obj'] = q & filter_kwargs['q_obj']
                        else:
                            filter_kwargs[u_with] = u_with_attr
                qs = self.instance.__class__.objects.clone()
                qs = qs.no_dereference().filter(**filter_kwargs)
                # Exclude the current object from the query if we are editing
                # an instance (as opposed to creating a new one)
                if self.instance.pk is not None:
                    qs = qs.filter(pk__ne=self.instance.pk)
                if qs.count() > 0:
                    message = _("%s with this %s already exists.") % (
                        str(capfirst(self.instance._meta.verbose_name)),
                        str(pretty_name(f.name))
                    )
                    err_dict = {f.name: [message]}
                    self._update_errors(err_dict)
                    errors.append(err_dict)
        
        return errors
                
    def save(self, commit=True):
        """
        Saves this ``form``'s cleaned_data into model instance
        ``self.instance``.

        If commit=True, then the changes to ``instance`` will be saved to the
        database. Returns ``instance``.
        """
        try:
            if self.instance.pk is None:
                fail_message = 'created'
            else:
                fail_message = 'changed'
        except (KeyError, AttributeError):
            fail_message = 'embedded document saved'
        obj = save_instance(self, self.instance, self._meta.fields,
                            fail_message, commit, construct=False)

        return obj
    save.alters_data = True


class DocumentForm(with_metaclass(DocumentFormMetaclass, BaseDocumentForm)):
    pass
    

def documentform_factory(document, form=DocumentForm, fields=None,
                         exclude=None, formfield_callback=None):
    # Build up a list of attributes that the Meta object will have.
    attrs = {'document': document, 'model': document}
    if fields is not None:
        attrs['fields'] = fields
    if exclude is not None:
        attrs['exclude'] = exclude

    # If parent form class already has an inner Meta, the Meta we're
    # creating needs to inherit from the parent's inner meta.
    parent = (object,)
    if hasattr(form, 'Meta'):
        parent = (form.Meta, object)
    Meta = type('Meta', parent, attrs)

    # Give this new form class a reasonable name.
    if isinstance(document, type):
        doc_inst = document()
    else:
        doc_inst = document
    class_name = doc_inst.__class__.__name__ + 'Form'

    # Class attributes for the new form class.
    form_class_attrs = {
        'Meta': Meta,
        'formfield_callback': formfield_callback
    }

    return DocumentFormMetaclass(class_name, (form,), form_class_attrs)


class EmbeddedDocumentForm(with_metaclass(DocumentFormMetaclass,
                                          BaseDocumentForm)):
    def __init__(self, parent_document, data=None, files=None, position=None,
                 *args, **kwargs):
        if self._meta.embedded_field is not None and not \
                self._meta.embedded_field in parent_document._fields:
            raise FieldError("Parent document must have field %s" %
                             self._meta.embedded_field)
        
        instance = kwargs.pop('instance', None)
        
        if isinstance(parent_document._fields.get(self._meta.embedded_field),
                      ListField):
            # if we received a list position of the instance and no instance
            # load the instance from the parent document and proceed as normal
            if instance is None and position is not None:
                instance = getattr(parent_document,
                                   self._meta.embedded_field)[position]
            
            # same as above only the other way around. Note: Mongoengine
            # defines equality as having the same data, so if you have 2
            # objects with the same data the first one will be edited. That
            # may or may not be the right one.
            if instance is not None and position is None:
                emb_list = getattr(parent_document, self._meta.embedded_field)
                position = next(
                    (i for i, obj in enumerate(emb_list) if obj == instance),
                    None
                )
            
        super(EmbeddedDocumentForm, self).__init__(data=data, files=files,
                                                   instance=instance, *args,
                                                   **kwargs)
        self.parent_document = parent_document
        self.position = position
        
    def save(self, commit=True):
        """If commit is True the embedded document is added to the parent
        document. Otherwise the parent_document is left untouched and the
        embedded is returned as usual.
        """
        if self.errors:
            raise ValueError("The %s could not be saved because the data"
                             "didn't validate." %
                             self.instance.__class__.__name__)
        
        if commit:
            field = self.parent_document._fields.get(self._meta.embedded_field)
            if isinstance(field, ListField) and self.position is None:
                # no position given, simply appending to ListField
                try:
                    self.parent_document.update(**{
                        "push__" + self._meta.embedded_field: self.instance
                    })
                except:
                    raise OperationError("The %s could not be appended." %
                                         self.instance.__class__.__name__)
            elif isinstance(field, ListField) and self.position is not None:
                # updating ListField at given position
                try:
                    self.parent_document.update(**{
                        "__".join(("set", self._meta.embedded_field,
                                   str(self.position))): self.instance
                    })
                except:
                    raise OperationError("The %s could not be updated at "
                                         "position %d." %
                                         (self.instance.__class__.__name__,
                                          self.position))
            else:
                # not a listfield on parent, treat as an embedded field
                setattr(self.parent_document, self._meta.embedded_field,
                        self.instance)
                self.parent_document.save()
        return self.instance


class BaseDocumentFormSet(BaseFormSet):
    """
    A ``FormSet`` for editing a queryset and/or adding new objects to it.
    """

    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 queryset=None, **kwargs):
        if not isinstance(queryset, (list, BaseQuerySet)):
            queryset = [queryset]
        self.queryset = queryset
        self._queryset = self.queryset
        self.initial = self.construct_initial()
        defaults = {'data': data, 'files': files, 'auto_id': auto_id,
                    'prefix': prefix, 'initial': self.initial}
        defaults.update(kwargs)
        super(BaseDocumentFormSet, self).__init__(**defaults)

    def construct_initial(self):
        initial = []
        try:
            for d in self.get_queryset():
                initial.append(document_to_dict(d))
        except TypeError:
            pass
        return initial

    def initial_form_count(self):
        """Returns the number of forms that are required in this FormSet."""
        if not (self.data or self.files):
            return len(self.get_queryset())
        return super(BaseDocumentFormSet, self).initial_form_count()

    def get_queryset(self):
        qs = self._queryset or []
        return qs

    def save_object(self, form):
        obj = form.save(commit=False)
        return obj

    def save(self, commit=True):
        """
        Saves model instances for every form, adding and changing instances
        as necessary, and returns the list of instances.
        """
        saved = []
        for form in self.forms:
            if not form.has_changed() and not form in self.initial_forms:
                continue
            obj = self.save_object(form)
            if form.cleaned_data.get("DELETE", False):
                try:
                    obj.delete()
                except AttributeError:
                    # if it has no delete method it is an embedded object. We
                    # just don't add to the list and it's gone. Cool huh?
                    continue
            if commit:
                obj.save()
            saved.append(obj)
        return saved

    def clean(self):
        self.validate_unique()

    def validate_unique(self):
        errors = []
        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue
            errors += form.validate_unique()
            
        if errors:
            raise ValidationError(errors)
        
    def get_date_error_message(self, date_check):
        return ugettext("Please correct the duplicate data for %(field_name)s "
                        "which must be unique for the %(lookup)s "
                        "in %(date_field)s.") % {
            'field_name': date_check[2],
            'date_field': date_check[3],
            'lookup': str(date_check[1]),
        }

    def get_form_error(self):
        return ugettext("Please correct the duplicate values below.")


def documentformset_factory(document, form=DocumentForm,
                            formfield_callback=None,
                            formset=BaseDocumentFormSet,
                            extra=1, can_delete=False, can_order=False,
                            max_num=None, fields=None, exclude=None):
    """
    Returns a FormSet class for the given Django model class.
    """
    form = documentform_factory(document, form=form, fields=fields,
                                exclude=exclude,
                                formfield_callback=formfield_callback)
    FormSet = formset_factory(form, formset, extra=extra, max_num=max_num,
                              can_order=can_order, can_delete=can_delete)
    FormSet.model = document
    FormSet.document = document
    return FormSet


class BaseInlineDocumentFormSet(BaseDocumentFormSet):
    """
    A formset for child objects related to a parent.
    
    self.instance -> the document containing the inline objects
    """
    def __init__(self, data=None, files=None, instance=None,
                 save_as_new=False, prefix=None, queryset=[], **kwargs):
        self.instance = instance
        self.save_as_new = save_as_new
        
        super(BaseInlineDocumentFormSet, self).__init__(data, files,
                                                        prefix=prefix,
                                                        queryset=queryset,
                                                        **kwargs)

    def initial_form_count(self):
        if self.save_as_new:
            return 0
        return super(BaseInlineDocumentFormSet, self).initial_form_count()

    #@classmethod
    def get_default_prefix(cls):
        return cls.document.__name__.lower()
    get_default_prefix = classmethod(get_default_prefix)
    
    def add_fields(self, form, index):
        super(BaseInlineDocumentFormSet, self).add_fields(form, index)

        # Add the generated field to form._meta.fields if it's defined to make
        # sure validation isn't skipped on that field.
        if form._meta.fields:
            if isinstance(form._meta.fields, tuple):
                form._meta.fields = list(form._meta.fields)
            #form._meta.fields.append(self.fk.name)

    def get_unique_error_message(self, unique_check):
        unique_check = [
            field for field in unique_check if field != self.fk.name
        ]
        return super(BaseInlineDocumentFormSet, self).get_unique_error_message(
            unique_check
        )


def inlineformset_factory(document, form=DocumentForm,
                          formset=BaseInlineDocumentFormSet,
                          fields=None, exclude=None,
                          extra=1, can_order=False, can_delete=True,
                          max_num=None, formfield_callback=None):
    """
    Returns an ``InlineFormSet`` for the given kwargs.

    You must provide ``fk_name`` if ``model`` has more than one ``ForeignKey``
    to ``parent_model``.
    """
    kwargs = {
        'form': form,
        'formfield_callback': formfield_callback,
        'formset': formset,
        'extra': extra,
        'can_delete': can_delete,
        'can_order': can_order,
        'fields': fields,
        'exclude': exclude,
        'max_num': max_num,
    }
    FormSet = documentformset_factory(document, **kwargs)
    return FormSet


class EmbeddedDocumentFormSet(BaseDocumentFormSet):
    def __init__(self, data=None, files=None, save_as_new=False,
                 prefix=None, queryset=[], parent_document=None, **kwargs):
        if parent_document is not None:
            self.parent_document = parent_document
            
        if 'instance' in kwargs:
            instance = kwargs.pop('instance')
            if parent_document is None:
                self.parent_document = instance
        
        queryset = getattr(self.parent_document,
                           self.form._meta.embedded_field)
        
        super(EmbeddedDocumentFormSet, self).__init__(data, files, save_as_new,
                                                      prefix, queryset,
                                                      **kwargs)
        
    def _construct_form(self, i, **kwargs):
        defaults = {'parent_document': self.parent_document}
        
        # add position argument to the form. Otherwise we will spend
        # a huge amount of time iterating over the list field on form __init__
        emb_list = getattr(self.parent_document,
                           self.form._meta.embedded_field)
                           
        if emb_list is not None and len(emb_list) > i:
            defaults['position'] = i
        defaults.update(kwargs)
        
        form = super(EmbeddedDocumentFormSet, self)._construct_form(
            i, **defaults)
        return form
        
    @classmethod
    def get_default_prefix(cls):
        return cls.document.__name__.lower()

    @property
    def empty_form(self):
        form = self.form(
            self.parent_document,
            auto_id=self.auto_id,
            prefix=self.add_prefix('__prefix__'),
            empty_permitted=True,
        )
        self.add_fields(form, None)
        return form
    
    def save(self, commit=True):
        # Don't try to save the new documents. Embedded objects don't have
        # a save method anyway.
        objs = super(EmbeddedDocumentFormSet, self).save(commit=False)
        objs = objs or []
        
        if commit and self.parent_document is not None:
            field = self.parent_document._fields.get(self.form._meta.embedded_field, None)
            if isinstance(field, EmbeddedDocumentField):
                try:
                    obj = objs[0]
                except IndexError:
                    obj = None
                setattr(self.parent_document, self.form._meta.embedded_field, obj)
            else:
                setattr(self.parent_document, self.form._meta.embedded_field, objs)
            self.parent_document.save()
        
        return objs
        

def _get_embedded_field(parent_doc, document, emb_name=None, can_fail=False):
    if emb_name:
        emb_fields = [f for f in parent_doc._fields.values() if f.name == emb_name]
        if len(emb_fields) == 1:
            field = emb_fields[0]
            if not isinstance(field, (EmbeddedDocumentField, ListField)) or \
                    (isinstance(field, EmbeddedDocumentField) and field.document_type != document) or \
                    (isinstance(field, ListField) and
                     isinstance(field.field, EmbeddedDocumentField) and 
                     field.field.document_type != document):
                raise Exception("emb_name '%s' is not a EmbeddedDocumentField or not a ListField to %s" % (emb_name, document))
            elif len(emb_fields) == 0:
                raise Exception("%s has no field named '%s'" % (parent_doc, emb_name))
    else:
        emb_fields = [
            f for f in parent_doc._fields.values()
            if (isinstance(field, EmbeddedDocumentField) and field.document_type == document) or \
            (isinstance(field, ListField) and
             isinstance(field.field, EmbeddedDocumentField) and 
             field.field.document_type == document)
        ]
        if len(emb_fields) == 1:
            field = emb_fields[0]
        elif len(emb_fields) == 0:
            if can_fail:
                return
            raise Exception("%s has no EmbeddedDocumentField or ListField to %s" % (parent_doc, document))
        else:
            raise Exception("%s has more than 1 EmbeddedDocumentField to %s" % (parent_doc, document))
            
    return field
    

def embeddedformset_factory(document, parent_document,
                            form=EmbeddedDocumentForm,
                            formset=EmbeddedDocumentFormSet,
                            embedded_name=None,
                            fields=None, exclude=None,
                            extra=3, can_order=False, can_delete=True,
                            max_num=None, formfield_callback=None):
    """
    Returns an ``InlineFormSet`` for the given kwargs.

    You must provide ``fk_name`` if ``model`` has more than one ``ForeignKey``
    to ``parent_model``.
    """
    emb_field = _get_embedded_field(parent_document, document, emb_name=embedded_name)
    if isinstance(emb_field, EmbeddedDocumentField):
        max_num = 1
    kwargs = {
        'form': form,
        'formfield_callback': formfield_callback,
        'formset': formset,
        'extra': extra,
        'can_delete': can_delete,
        'can_order': can_order,
        'fields': fields,
        'exclude': exclude,
        'max_num': max_num,
    }
    FormSet = documentformset_factory(document, **kwargs)
    FormSet.form._meta.embedded_field = emb_field.name
    return FormSet

########NEW FILE########
__FILENAME__ = fieldgenerator
# -*- coding: utf-8 -*-

"""
Based on django mongotools (https://github.com/wpjunior/django-mongotools) by
Wilson Júnior (wilsonpjunior@gmail.com).
"""
import collections

from django import forms
from django.core.validators import EMPTY_VALUES
try:
    from django.utils.encoding import smart_text as smart_unicode
except ImportError:
    try:
        from django.utils.encoding import smart_unicode
    except ImportError:
        from django.forms.util import smart_unicode
from django.utils.text import capfirst

from mongoengine import (ReferenceField as MongoReferenceField,
                         EmbeddedDocumentField as MongoEmbeddedDocumentField,
                         ListField as MongoListField,
                         MapField as MongoMapField)

from mongodbforms.fields import (MongoCharField, MongoEmailField,
                                 MongoURLField, ReferenceField,
                                 DocumentMultipleChoiceField, ListField,
                                 MapField)
from mongodbforms.widgets import Html5SplitDateTimeWidget
from mongodbforms.documentoptions import create_verbose_name

BLANK_CHOICE_DASH = [("", "---------")]


class MongoFormFieldGenerator(object):
    """This class generates Django form-fields for mongoengine-fields."""
    
    # used for fields that fit in one of the generate functions
    # but don't actually have the name.
    generator_map = {
        'sortedlistfield': 'generate_listfield',
        'longfield': 'generate_intfield',
    }
    
    form_field_map = {
        'stringfield': MongoCharField,
        'stringfield_choices': forms.TypedChoiceField,
        'stringfield_long': MongoCharField,
        'emailfield': MongoEmailField,
        'urlfield': MongoURLField,
        'intfield': forms.IntegerField,
        'intfield_choices': forms.TypedChoiceField,
        'floatfield': forms.FloatField,
        'decimalfield': forms.DecimalField,
        'booleanfield': forms.BooleanField,
        'booleanfield_choices': forms.TypedChoiceField,
        'datetimefield': forms.SplitDateTimeField,
        'referencefield': ReferenceField,
        'listfield': ListField,
        'listfield_choices': forms.MultipleChoiceField,
        'listfield_references': DocumentMultipleChoiceField,
        'mapfield': MapField,
        'filefield': forms.FileField,
        'imagefield': forms.ImageField,
    }
    
    # uses the same keys as form_field_map
    widget_override_map = {
        'stringfield_long': forms.Textarea,
    }
    
    def __init__(self, field_overrides={}, widget_overrides={}):
        self.form_field_map.update(field_overrides)
        self.widget_override_map.update(widget_overrides)

    def generate(self, field, **kwargs):
        """Tries to lookup a matching formfield generator (lowercase
        field-classname) and raises a NotImplementedError of no generator
        can be found.
        """
        # do not handle embedded documents here. They are more or less special
        # and require some form of inline formset or something more complex
        # to handle then a simple field
        if isinstance(field, MongoEmbeddedDocumentField):
            return
        
        attr_name = 'generate_%s' % field.__class__.__name__.lower()
        if hasattr(self, attr_name):
            return getattr(self, attr_name)(field, **kwargs)

        for cls in field.__class__.__bases__:
            cls_name = cls.__name__.lower()
            
            attr_name = 'generate_%s' % cls_name
            if hasattr(self, attr_name):
                return getattr(self, attr_name)(field, **kwargs)

            if cls_name in self.form_field_map:
                attr = self.generator_map.get(cls_name)
                return getattr(self, attr)(field, **kwargs)
                
        raise NotImplementedError('%s is not supported by MongoForm' %
                                  field.__class__.__name__)

    def get_field_choices(self, field, include_blank=True,
                          blank_choice=BLANK_CHOICE_DASH):
        first_choice = include_blank and blank_choice or []
        return first_choice + list(field.choices)

    def string_field(self, value):
        if value in EMPTY_VALUES:
            return None
        return smart_unicode(value)

    def integer_field(self, value):
        if value in EMPTY_VALUES:
            return None
        return int(value)

    def boolean_field(self, value):
        if value in EMPTY_VALUES:
            return None
        return value.lower() == 'true'

    def get_field_label(self, field):
        if field.verbose_name:
            return capfirst(field.verbose_name)
        if field.name is not None:
            return capfirst(create_verbose_name(field.name))
        return ''

    def get_field_help_text(self, field):
        if field.help_text:
            return field.help_text
        else:
            return ''
            
    def get_field_default(self, field):
        if isinstance(field, (MongoListField, MongoMapField)):
            f = field.field
        else:
            f = field
        d = {}
        if isinstance(f.default, collections.Callable):
            d['initial'] = field.default()
            d['show_hidden_initial'] = True
            return f.default()
        else:
            d['initial'] = field.default
        return f.default
        
    def check_widget(self, map_key):
        if map_key in self.widget_override_map:
            return {'widget': self.widget_override_map.get(map_key)}
        else:
            return {}

    def generate_stringfield(self, field, **kwargs):
        defaults = {
            'label': self.get_field_label(field),
            'initial': self.get_field_default(field),
            'required': field.required,
            'help_text': self.get_field_help_text(field),
        }
        if field.choices:
            map_key = 'stringfield_choices'
            defaults.update({
                'choices': self.get_field_choices(field),
                'coerce': self.string_field,
            })
        elif field.max_length is None:
            map_key = 'stringfield_long'
            defaults.update({
                'min_length': field.min_length,
            })
        else:
            map_key = 'stringfield'
            defaults.update({
                'max_length': field.max_length,
                'min_length': field.min_length,
            })
            if field.regex:
                defaults['regex'] = field.regex
            
        form_class = self.form_field_map.get(map_key)
        defaults.update(self.check_widget(map_key))
        defaults.update(kwargs)
        return form_class(**defaults)

    def generate_emailfield(self, field, **kwargs):
        map_key = 'emailfield'
        defaults = {
            'required': field.required,
            'min_length': field.min_length,
            'max_length': field.max_length,
            'initial': self.get_field_default(field),
            'label': self.get_field_label(field),
            'help_text': self.get_field_help_text(field)
        }
        defaults.update(self.check_widget(map_key))
        form_class = self.form_field_map.get(map_key)
        defaults.update(kwargs)
        return form_class(**defaults)

    def generate_urlfield(self, field, **kwargs):
        map_key = 'urlfield'
        defaults = {
            'required': field.required,
            'min_length': field.min_length,
            'max_length': field.max_length,
            'initial': self.get_field_default(field),
            'label': self.get_field_label(field),
            'help_text': self.get_field_help_text(field)
        }
        form_class = self.form_field_map.get(map_key)
        defaults.update(self.check_widget(map_key))
        defaults.update(kwargs)
        return form_class(**defaults)

    def generate_intfield(self, field, **kwargs):
        defaults = {
            'required': field.required,
            'initial': self.get_field_default(field),
            'label': self.get_field_label(field),
            'help_text': self.get_field_help_text(field)
        }
        if field.choices:
            map_key = 'intfield_choices'
            defaults.update({
                'coerce': self.integer_field,
                'empty_value': None,
                'choices': self.get_field_choices(field),
            })
        else:
            map_key = 'intfield'
            defaults.update({
                'min_value': field.min_value,
                'max_value': field.max_value,
            })
        form_class = self.form_field_map.get(map_key)
        defaults.update(self.check_widget(map_key))
        defaults.update(kwargs)
        return form_class(**defaults)

    def generate_floatfield(self, field, **kwargs):
        map_key = 'floatfield'
        defaults = {
            'label': self.get_field_label(field),
            'initial': self.get_field_default(field),
            'required': field.required,
            'min_value': field.min_value,
            'max_value': field.max_value,
            'help_text': self.get_field_help_text(field)
        }
        form_class = self.form_field_map.get(map_key)
        defaults.update(self.check_widget(map_key))
        defaults.update(kwargs)
        return form_class(**defaults)

    def generate_decimalfield(self, field, **kwargs):
        map_key = 'decimalfield'
        defaults = {
            'label': self.get_field_label(field),
            'initial': self.get_field_default(field),
            'required': field.required,
            'min_value': field.min_value,
            'max_value': field.max_value,
            'decimal_places': field.precision,
            'help_text': self.get_field_help_text(field)
        }
        form_class = self.form_field_map.get(map_key)
        defaults.update(self.check_widget(map_key))
        defaults.update(kwargs)
        return form_class(**defaults)

    def generate_booleanfield(self, field, **kwargs):
        defaults = {
            'required': field.required,
            'initial': self.get_field_default(field),
            'label': self.get_field_label(field),
            'help_text': self.get_field_help_text(field)
        }
        if field.choices:
            map_key = 'booleanfield_choices'
            defaults.update({
                'coerce': self.boolean_field,
                'empty_value': None,
                'choices': self.get_field_choices(field),
            })
        else:
            map_key = 'booleanfield'
        form_class = self.form_field_map.get(map_key)
        defaults.update(self.check_widget(map_key))
        defaults.update(kwargs)
        return form_class(**defaults)

    def generate_datetimefield(self, field, **kwargs):
        map_key = 'datetimefield'
        defaults = {
            'required': field.required,
            'initial': self.get_field_default(field),
            'label': self.get_field_label(field),
        }
        form_class = self.form_field_map.get(map_key)
        defaults.update(self.check_widget(map_key))
        defaults.update(kwargs)
        return form_class(**defaults)

    def generate_referencefield(self, field, **kwargs):
        map_key = 'referencefield'
        defaults = {
            'label': self.get_field_label(field),
            'help_text': self.get_field_help_text(field),
            'required': field.required,
            'queryset': field.document_type.objects.clone(),
        }
        form_class = self.form_field_map.get(map_key)
        defaults.update(self.check_widget(map_key))
        defaults.update(kwargs)
        return form_class(**defaults)

    def generate_listfield(self, field, **kwargs):
        # We can't really handle embedded documents here.
        # So we just ignore them
        if isinstance(field.field, MongoEmbeddedDocumentField):
            return
        
        defaults = {
            'label': self.get_field_label(field),
            'help_text': self.get_field_help_text(field),
            'required': field.required,
        }
        if field.field.choices:
            map_key = 'listfield_choices'
            defaults.update({
                'choices': field.field.choices,
                'widget': forms.CheckboxSelectMultiple
            })
        elif isinstance(field.field, MongoReferenceField):
            map_key = 'listfield_references'
            defaults.update({
                'queryset': field.field.document_type.objects.clone(),
            })
        else:
            map_key = 'listfield'
            form_field = self.generate(field.field)
            defaults.update({
                'contained_field': form_field.__class__,
            })
        form_class = self.form_field_map.get(map_key)
        defaults.update(self.check_widget(map_key))
        defaults.update(kwargs)
        return form_class(**defaults)
        
    def generate_mapfield(self, field, **kwargs):
        # We can't really handle embedded documents here.
        # So we just ignore them
        if isinstance(field.field, MongoEmbeddedDocumentField):
            return
            
        map_key = 'mapfield'
        form_field = self.generate(field.field)
        defaults = {
            'label': self.get_field_label(field),
            'help_text': self.get_field_help_text(field),
            'required': field.required,
            'contained_field': form_field.__class__,
        }
        form_class = self.form_field_map.get(map_key)
        defaults.update(self.check_widget(map_key))
        defaults.update(kwargs)
        return form_class(**defaults)

    def generate_filefield(self, field, **kwargs):
        map_key = 'filefield'
        defaults = {
            'required': field.required,
            'label': self.get_field_label(field),
            'initial': self.get_field_default(field),
            'help_text': self.get_field_help_text(field)
        }
        form_class = self.form_field_map.get(map_key)
        defaults.update(self.check_widget(map_key))
        defaults.update(kwargs)
        return form_class(**defaults)

    def generate_imagefield(self, field, **kwargs):
        map_key = 'imagefield'
        defaults = {
            'required': field.required,
            'label': self.get_field_label(field),
            'initial': self.get_field_default(field),
            'help_text': self.get_field_help_text(field)
        }
        form_class = self.form_field_map.get(map_key)
        defaults.update(self.check_widget(map_key))
        defaults.update(kwargs)
        return form_class(**defaults)


class MongoDefaultFormFieldGenerator(MongoFormFieldGenerator):
    """This class generates Django form-fields for mongoengine-fields."""

    def generate(self, field, **kwargs):
        """Tries to lookup a matching formfield generator (lowercase
        field-classname) and raises a NotImplementedError of no generator
        can be found.
        """
        try:
            sup = super(MongoDefaultFormFieldGenerator, self)
            return sup.generate(field, **kwargs)
        except NotImplementedError:
            # a normal charfield is always a good guess
            # for a widget.
            # TODO: Somehow add a warning
            defaults = {'required': field.required}

            if hasattr(field, 'min_length'):
                defaults['min_length'] = field.min_length

            if hasattr(field, 'max_length'):
                defaults['max_length'] = field.max_length

            if hasattr(field, 'default'):
                defaults['initial'] = field.default

            defaults.update(kwargs)
            return forms.CharField(**defaults)


class Html5FormFieldGenerator(MongoDefaultFormFieldGenerator):
    def check_widget(self, map_key):
        override = super(Html5FormFieldGenerator, self).check_widget(map_key)
        if override != {}:
            return override
        
        chunks = map_key.split('field')
        kind = chunks[0]
        
        if kind == 'email':
            if hasattr(forms, 'EmailInput'):
                return {'widget': forms.EmailInput}
            else:
                input = forms.TextInput
                input.input_type = 'email'
                return {'widget': input}
        elif kind in ['int', 'float'] and len(chunks) < 2:
            if hasattr(forms, 'NumberInput'):
                return {'widget': forms.NumberInput}
            else:
                input = forms.TextInput
                input.input_type = 'number'
                return {'widget': input}
        elif kind == 'url':
            if hasattr(forms, 'URLInput'):
                return {'widget': forms.URLInput}
            else:
                input = forms.TextInput
                input.input_type = 'url'
                return {'widget': input}
        elif kind == 'datetime':
            return {'widget': Html5SplitDateTimeWidget}
        else:
            return {}

########NEW FILE########
__FILENAME__ = fields
# -*- coding: utf-8 -*-

"""
Based on django mongotools (https://github.com/wpjunior/django-mongotools) by
Wilson Júnior (wilsonpjunior@gmail.com).
"""
import copy

from django import forms
from django.core.validators import (EMPTY_VALUES, MinLengthValidator,
                                    MaxLengthValidator)

try:
    from django.utils.encoding import force_text as force_unicode
except ImportError:
    from django.utils.encoding import force_unicode
    
try:
    from django.utils.encoding import smart_text as smart_unicode
except ImportError:
    try:
        from django.utils.encoding import smart_unicode
    except ImportError:
        from django.forms.util import smart_unicode
        
from django.utils.translation import ugettext_lazy as _
from django.forms.util import ErrorList
from django.core.exceptions import ValidationError

try:  # objectid was moved into bson in pymongo 1.9
    from bson.errors import InvalidId
except ImportError:
    from pymongo.errors import InvalidId
    
from mongodbforms.widgets import ListWidget, MapWidget, HiddenMapWidget


class MongoChoiceIterator(object):
    def __init__(self, field):
        self.field = field
        self.queryset = field.queryset

    def __iter__(self):
        if self.field.empty_label is not None:
            yield ("", self.field.empty_label)

        for obj in self.queryset.all():
            yield self.choice(obj)

    def __len__(self):
        return len(self.queryset)

    def choice(self, obj):
        return (self.field.prepare_value(obj),
                self.field.label_from_instance(obj))


class NormalizeValueMixin(object):
    """
    mongoengine doesn't treat fields that return an empty string
    as empty. This mixins can be used to create fields that return
    None instead of an empty string.
    """
    def to_python(self, value):
        value = super(NormalizeValueMixin, self).to_python(value)
        if value in EMPTY_VALUES:
            return None
        return value
        
        
class MongoCharField(NormalizeValueMixin, forms.CharField):
    pass
    

class MongoEmailField(NormalizeValueMixin, forms.EmailField):
    pass
    

class MongoSlugField(NormalizeValueMixin, forms.SlugField):
    pass
    

class MongoURLField(NormalizeValueMixin, forms.URLField):
    pass
    

class ReferenceField(forms.ChoiceField):
    """
    Reference field for mongo forms. Inspired by
    `django.forms.models.ModelChoiceField`.
    """
    def __init__(self, queryset, empty_label="---------", *args, **kwargs):
        forms.Field.__init__(self, *args, **kwargs)
        self.empty_label = empty_label
        self.queryset = queryset

    def _get_queryset(self):
        return self._queryset.clone()
    
    def _set_queryset(self, queryset):
        self._queryset = queryset
        self.widget.choices = self.choices
    queryset = property(_get_queryset, _set_queryset)

    def prepare_value(self, value):
        if hasattr(value, '_meta'):
            return value.pk

        return super(ReferenceField, self).prepare_value(value)

    def _get_choices(self):
        return MongoChoiceIterator(self)
    choices = property(_get_choices, forms.ChoiceField._set_choices)

    def label_from_instance(self, obj):
        """
        This method is used to convert objects into strings; it's used to
        generate the labels for the choices presented by this object.
        Subclasses can override this method to customize the display of
        the choices.
        """
        return smart_unicode(obj)

    def clean(self, value):
        # Check for empty values.
        if value in EMPTY_VALUES:
            if self.required:
                raise forms.ValidationError(self.error_messages['required'])
            else:
                return None

        oid = super(ReferenceField, self).clean(value)
        
        try:
            obj = self.queryset.get(pk=oid)
        except (TypeError, InvalidId, self.queryset._document.DoesNotExist):
            raise forms.ValidationError(
                self.error_messages['invalid_choice'] % {'value': value}
            )
        return obj
    
    def __deepcopy__(self, memo):
        result = super(forms.ChoiceField, self).__deepcopy__(memo)
        result.queryset = self.queryset  # self.queryset calls clone()
        result.empty_label = copy.deepcopy(self.empty_label)
        return result


class DocumentMultipleChoiceField(ReferenceField):
    """A MultipleChoiceField whose choices are a model QuerySet."""
    widget = forms.SelectMultiple
    hidden_widget = forms.MultipleHiddenInput
    default_error_messages = {
        'list': _('Enter a list of values.'),
        'invalid_choice': _('Select a valid choice. %s is not one of the'
                            ' available choices.'),
        'invalid_pk_value': _('"%s" is not a valid value for a primary key.')
    }

    def __init__(self, queryset, *args, **kwargs):
        super(DocumentMultipleChoiceField, self).__init__(
            queryset, empty_label=None, *args, **kwargs
        )

    def clean(self, value):
        if self.required and not value:
            raise forms.ValidationError(self.error_messages['required'])
        elif not self.required and not value:
            return []
        if not isinstance(value, (list, tuple)):
            raise forms.ValidationError(self.error_messages['list'])
        
        qs = self.queryset
        try:
            qs = qs.filter(pk__in=value)
        except ValidationError:
            raise forms.ValidationError(
                self.error_messages['invalid_pk_value'] % str(value)
            )
        pks = set([force_unicode(getattr(o, 'pk')) for o in qs])
        for val in value:
            if force_unicode(val) not in pks:
                raise forms.ValidationError(
                    self.error_messages['invalid_choice'] % val
                )
        # Since this overrides the inherited ModelChoiceField.clean
        # we run custom validators here
        self.run_validators(value)
        return list(qs)

    def prepare_value(self, value):
        if hasattr(value, '__iter__') and not hasattr(value, '_meta'):
            sup = super(DocumentMultipleChoiceField, self)
            return [sup.prepare_value(v) for v in value]
        return super(DocumentMultipleChoiceField, self).prepare_value(value)
    
    
class ListField(forms.Field):
    default_error_messages = {
        'invalid': _('Enter a list of values.'),
    }
    widget = ListWidget
    hidden_widget = forms.MultipleHiddenInput

    def __init__(self, contained_field, *args, **kwargs):
        if 'widget' in kwargs:
            self.widget = kwargs.pop('widget')
        
        if isinstance(contained_field, type):
            contained_widget = contained_field().widget
        else:
            contained_widget = contained_field.widget
            
        if isinstance(contained_widget, type):
            contained_widget = contained_widget()
        self.widget = self.widget(contained_widget)
        
        super(ListField, self).__init__(*args, **kwargs)
        
        if isinstance(contained_field, type):
            self.contained_field = contained_field(required=self.required)
        else:
            self.contained_field = contained_field
        
        if not hasattr(self, 'empty_values'):
            self.empty_values = list(EMPTY_VALUES)

    def validate(self, value):
        pass

    def clean(self, value):
        clean_data = []
        errors = ErrorList()
        if not value or isinstance(value, (list, tuple)):
            if not value or not [
                    v for v in value if v not in self.empty_values
            ]:
                if self.required:
                    raise ValidationError(self.error_messages['required'])
                else:
                    return []
        else:
            raise ValidationError(self.error_messages['invalid'])
        
        for field_value in value:
            try:
                clean_data.append(self.contained_field.clean(field_value))
            except ValidationError as e:
                # Collect all validation errors in a single list, which we'll
                # raise at the end of clean(), rather than raising a single
                # exception for the first error we encounter.
                errors.extend(e.messages)
            if self.contained_field.required:
                self.contained_field.required = False
        if errors:
            raise ValidationError(errors)

        self.validate(clean_data)
        self.run_validators(clean_data)
        return clean_data

    def _has_changed(self, initial, data):
        if initial is None:
            initial = ['' for x in range(0, len(data))]
        
        for initial, data in zip(initial, data):
            if self.contained_field._has_changed(initial, data):
                return True
        return False
        
    def prepare_value(self, value):
        value = [] if value is None else value
        value = super(ListField, self).prepare_value(value)
        prep_val = []
        for v in value:
            prep_val.append(self.contained_field.prepare_value(v))
        return prep_val


class MapField(forms.Field):
    default_error_messages = {
        'invalid': _('Enter a list of values.'),
        'key_required': _('A key is required.'),
    }
    widget = MapWidget
    hidden_widget = HiddenMapWidget

    def __init__(self, contained_field, max_key_length=None,
                 min_key_length=None, key_validators=[], field_kwargs={},
                 *args, **kwargs):
        if 'widget' in kwargs:
            self.widget = kwargs.pop('widget')
        
        if isinstance(contained_field, type):
            contained_widget = contained_field().widget
        else:
            contained_widget = contained_field.widget
            
        if isinstance(contained_widget, type):
            contained_widget = contained_widget()
        self.widget = self.widget(contained_widget)
        
        super(MapField, self).__init__(*args, **kwargs)
        
        if isinstance(contained_field, type):
            field_kwargs['required'] = self.required
            self.contained_field = contained_field(**field_kwargs)
        else:
            self.contained_field = contained_field
        
        self.key_validators = key_validators
        if min_key_length is not None:
            self.key_validators.append(MinLengthValidator(int(min_key_length)))
        if max_key_length is not None:
            self.key_validators.append(MaxLengthValidator(int(max_key_length)))
        
        # type of field used to store the dicts value
        if not hasattr(self, 'empty_values'):
            self.empty_values = list(EMPTY_VALUES)

    def _validate_key(self, key):
        if key in self.empty_values and self.required:
            raise ValidationError(self.error_messages['key_required'],
                                  code='key_required')
        errors = []
        for v in self.key_validators:
            try:
                v(key)
            except ValidationError as e:
                if hasattr(e, 'code'):
                    code = 'key_%s' % e.code
                    if code in self.error_messages:
                        e.message = self.error_messages[e.code]
                errors.extend(e.error_list)
        if errors:
            raise ValidationError(errors)

    def validate(self, value):
        pass

    def clean(self, value):
        clean_data = {}
        errors = ErrorList()
        if not value or isinstance(value, dict):
            if not value or not [
                    v for v in value.values() if v not in self.empty_values
            ]:
                if self.required:
                    raise ValidationError(self.error_messages['required'])
                else:
                    return {}
        else:
            raise ValidationError(self.error_messages['invalid'])
        
        # sort out required => at least one element must be in there
        for key, val in value.items():
            # ignore empties. Can they even come up here?
            if key in self.empty_values and val in self.empty_values:
                continue
            
            try:
                val = self.contained_field.clean(val)
            except ValidationError as e:
                # Collect all validation errors in a single list, which we'll
                # raise at the end of clean(), rather than raising a single
                # exception for the first error we encounter.
                errors.extend(e.messages)
                
            try:
                self._validate_key(key)
            except ValidationError as e:
                # Collect all validation errors in a single list, which we'll
                # raise at the end of clean(), rather than raising a single
                # exception for the first error we encounter.
                errors.extend(e.messages)
            
            clean_data[key] = val
                
            if self.contained_field.required:
                self.contained_field.required = False
                
        if errors:
            raise ValidationError(errors)

        self.validate(clean_data)
        self.run_validators(clean_data)
        return clean_data

    def _has_changed(self, initial, data):
        for k, v in data.items():
            if initial is None:
                init_val = ''
            else:
                try:
                    init_val = initial[k]
                except KeyError:
                    return True
            if self.contained_field._has_changed(init_val, v):
                return True
        return False

########NEW FILE########
__FILENAME__ = util
from collections import defaultdict

from django.conf import settings

from mongodbforms.documentoptions import DocumentMetaWrapper, LazyDocumentMetaWrapper
from mongodbforms.fieldgenerator import MongoDefaultFormFieldGenerator

try:
    from django.utils.module_loading import import_by_path
except ImportError:
    # this is only in Django's devel version for now
    # and the following code comes from there. Yet it's too nice to
    # pass on this. So we do define it here for now.
    import sys
    from django.core.exceptions import ImproperlyConfigured
    from django.utils.importlib import import_module
    from django.utils import six
    
    def import_by_path(dotted_path, error_prefix=''):
        """
        Import a dotted module path and return the attribute/class designated
        by the last name in the path. Raise ImproperlyConfigured if something
        goes wrong.
        """
        try:
            module_path, class_name = dotted_path.rsplit('.', 1)
        except ValueError:
            raise ImproperlyConfigured("%s%s doesn't look like a module path" %
                                       (error_prefix, dotted_path))
        try:
            module = import_module(module_path)
        except ImportError as e:
            msg = '%sError importing module %s: "%s"' % (
                error_prefix, module_path, e)
            six.reraise(ImproperlyConfigured, ImproperlyConfigured(msg),
                        sys.exc_info()[2])
        try:
            attr = getattr(module, class_name)
        except AttributeError:
            raise ImproperlyConfigured(
                '%sModule "%s" does not define a "%s" attribute/class' %
                (error_prefix, module_path, class_name))
        return attr


def load_field_generator():
    if hasattr(settings, 'MONGODBFORMS_FIELDGENERATOR'):
        return import_by_path(settings.MONGODBFORMS_FIELDGENERATOR)
    return MongoDefaultFormFieldGenerator


def init_document_options(document):
    if not isinstance(document._meta, (DocumentMetaWrapper, LazyDocumentMetaWrapper)):
        document._meta = DocumentMetaWrapper(document)
    return document


def get_document_options(document):
    return DocumentMetaWrapper(document)


def format_mongo_validation_errors(validation_exception):
    """Returns a string listing all errors within a document"""

    def generate_key(value, prefix=''):
        if isinstance(value, list):
            value = ' '.join([generate_key(k) for k in value])
        if isinstance(value, dict):
            value = ' '.join([
                generate_key(v, k) for k, v in value.iteritems()
            ])

        results = "%s.%s" % (prefix, value) if prefix else value
        return results

    error_dict = defaultdict(list)
    for k, v in validation_exception.to_dict().iteritems():
        error_dict[generate_key(v)].append(k)
    return ["%s: %s" % (k, v) for k, v in error_dict.iteritems()]


# Taken from six (https://pypi.python.org/pypi/six)
# by "Benjamin Peterson <benjamin@python.org>"
#
# Copyright (c) 2010-2013 Benjamin Peterson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

def with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""
    return meta("NewBase", bases, {})

########NEW FILE########
__FILENAME__ = widgets
import copy

from django.forms.widgets import (Widget, Media, TextInput,
                                  SplitDateTimeWidget, DateInput, TimeInput,
                                  MultiWidget, HiddenInput)
from django.utils.safestring import mark_safe
from django.core.validators import EMPTY_VALUES
from django.forms.util import flatatt


class Html5SplitDateTimeWidget(SplitDateTimeWidget):
    def __init__(self, attrs=None, date_format=None, time_format=None):
        date_input = DateInput(attrs=attrs, format=date_format)
        date_input.input_type = 'date'
        time_input = TimeInput(attrs=attrs, format=time_format)
        time_input.input_type = 'time'
        widgets = (date_input, time_input)
        MultiWidget.__init__(self, widgets, attrs)


class BaseContainerWidget(Widget):
    def __init__(self, data_widget, attrs=None):
        if isinstance(data_widget, type):
            data_widget = data_widget()
        self.data_widget = data_widget
        self.data_widget.is_localized = self.is_localized
        super(BaseContainerWidget, self).__init__(attrs)
        
    def id_for_label(self, id_):
        # See the comment for RadioSelect.id_for_label()
        if id_:
            id_ += '_0'
        return id_
        
    def format_output(self, rendered_widgets):
        """
        Given a list of rendered widgets (as strings), returns a Unicode string
        representing the HTML for the whole lot.

        This hook allows you to format the HTML design of the widgets, if
        needed.
        """
        return ''.join(rendered_widgets)

    def _get_media(self):
        """
        Media for a multiwidget is the combination of all media of
        the subwidgets.
        """
        media = Media()
        media = media + self.data_widget.media
        return media
    media = property(_get_media)
    
    def __deepcopy__(self, memo):
        obj = super(BaseContainerWidget, self).__deepcopy__(memo)
        obj.data_widget = copy.deepcopy(self.data_widget)
        return obj


class ListWidget(BaseContainerWidget):
    def render(self, name, value, attrs=None):
        if value is not None and not isinstance(value, (list, tuple)):
            raise TypeError(
                "Value supplied for %s must be a list or tuple." % name
            )
                
        output = []
        value = [] if value is None else value
        final_attrs = self.build_attrs(attrs)
        id_ = final_attrs.get('id', None)
        value.append('')
        for i, widget_value in enumerate(value):
            if id_:
                final_attrs = dict(final_attrs, id='%s_%s' % (id_, i))
            output.append(self.data_widget.render(
                name + '_%s' % i, widget_value, final_attrs)
            )
        return mark_safe(self.format_output(output))

    def value_from_datadict(self, data, files, name):
        widget = self.data_widget
        i = 0
        ret = []
        while (name + '_%s' % i) in data or (name + '_%s' % i) in files:
            value = widget.value_from_datadict(data, files, name + '_%s' % i)
            # we need a different list if we handle files. Basicly Django sends
            # back the initial values if we're not dealing with files. If we
            # store files on the list, we need to add empty values to the clean
            # data, so the list positions are kept.
            if value not in EMPTY_VALUES or (value is None and len(files) > 0):
                ret.append(value)
            i = i + 1
        return ret


class MapWidget(BaseContainerWidget):
    def __init__(self, data_widget, attrs=None):
        self.key_widget = TextInput()
        self.key_widget.is_localized = self.is_localized
        super(MapWidget, self).__init__(data_widget, attrs)

    def render(self, name, value, attrs=None):
        if value is not None and not isinstance(value, dict):
            raise TypeError("Value supplied for %s must be a dict." % name)
                
        output = []
        final_attrs = self.build_attrs(attrs)
        id_ = final_attrs.get('id', None)
        fieldset_attr = {}
        
        # in Python 3.X dict.items() returns dynamic *view objects*
        value = list(value.items())
        value.append(('', ''))
        for i, (key, widget_value) in enumerate(value):
            if id_:
                fieldset_attr = dict(
                    final_attrs, id='fieldset_%s_%s' % (id_, i)
                )
            group = []
            if not self.is_hidden:
                group.append(mark_safe('<fieldset %s>' % flatatt(fieldset_attr)))
            
            if id_:
                final_attrs = dict(final_attrs, id='%s_key_%s' % (id_, i))
            group.append(self.key_widget.render(
                name + '_key_%s' % i, key, final_attrs)
            )
            
            if id_:
                final_attrs = dict(final_attrs, id='%s_value_%s' % (id_, i))
            group.append(self.data_widget.render(
                name + '_value_%s' % i, widget_value, final_attrs)
            )
            if not self.is_hidden:
                group.append(mark_safe('</fieldset>'))
            
            output.append(mark_safe(''.join(group)))
        return mark_safe(self.format_output(output))

    def value_from_datadict(self, data, files, name):
        i = 0
        ret = {}
        while (name + '_key_%s' % i) in data:
            key = self.key_widget.value_from_datadict(
                data, files, name + '_key_%s' % i
            )
            value = self.data_widget.value_from_datadict(
                data, files, name + '_value_%s' % i
            )
            if key not in EMPTY_VALUES:
                ret.update(((key, value), ))
            i = i + 1
        return ret

    def _get_media(self):
        """
        Media for a multiwidget is the combination of all media of
        the subwidgets.
        """
        media = super(MapWidget, self)._get_media()
        media = media + self.key_widget.media
        return media
    media = property(_get_media)

    def __deepcopy__(self, memo):
        obj = super(MapWidget, self).__deepcopy__(memo)
        obj.key_widget = copy.deepcopy(self.key_widget)
        return obj

        
class HiddenMapWidget(MapWidget):
    is_hidden = True
    
    def __init__(self, attrs=None):
        data_widget = HiddenInput()
        super(MapWidget, self).__init__(data_widget, attrs)
        self.key_widget = HiddenInput()

########NEW FILE########
