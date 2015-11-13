__FILENAME__ = admin
from django.db import transaction, models
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.contrib.admin.util import unquote, flatten_fieldsets
from django.contrib.admin.options import BaseModelAdmin, ModelAdmin
from django.contrib.admin.helpers import AdminForm
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.utils.translation import ugettext as _
from django.utils.encoding import force_unicode
from django.utils.html import escape
from django.forms.formsets import all_valid
from django.contrib.admin import helpers
from django.utils.safestring import mark_safe
from django.forms.models import (inlineformset_factory, BaseInlineFormSet)
from django import forms
from django.utils.functional import curry

csrf_protect_m = method_decorator(csrf_protect)


def __init__(self, form, fieldsets, prepopulated_fields, readonly_fields=None, model_admin=None):
    """
    Monkey-patch for django 1.5
    """
    def normalize_fieldsets(fieldsets):
        """
        Make sure the keys in fieldset dictionaries are strings. Returns the
        normalized data.
        """
        result = []
        for name, options in fieldsets:
            result.append((name, normalize_dictionary(options)))
        return result

    def normalize_dictionary(data_dict):
        """
        Converts all the keys in "data_dict" to strings. The keys must be
        convertible using str().
        """
        for key, value in data_dict.items():
            if not isinstance(key, str):
                del data_dict[key]
                data_dict[str(key)] = value
        return data_dict
    if isinstance(prepopulated_fields, list):
        prepopulated_fields = dict()
    self.form, self.fieldsets = form, normalize_fieldsets(fieldsets)
    self.prepopulated_fields = [{
        'field': form[field_name],
        'dependencies': [form[f] for f in dependencies]
    } for field_name, dependencies in prepopulated_fields.items()]
    self.model_admin = model_admin
    if readonly_fields is None:
        readonly_fields = ()
    self.readonly_fields = readonly_fields

AdminForm.__init__ = __init__


class NestedModelAdmin(ModelAdmin):

    @csrf_protect_m
    @transaction.commit_on_success
    def add_view(self, request, form_url='', extra_context=None):
        "The 'add' admin view for this model."
        model = self.model
        opts = model._meta

        if not self.has_add_permission(request):
            raise PermissionDenied
        ModelForm = self.get_form(request)
        formsets = []
        if request.method == 'POST':
            form = ModelForm(request.POST, request.FILES)
            if form.is_valid():
                new_object = self.save_form(request, form, change=False)
                form_validated = True
            else:
                form_validated = False
                new_object = self.model()
            prefixes = {}
            for FormSet, inline in zip(self.get_formsets(request), self.get_inline_instances(request)):
                prefix = FormSet.get_default_prefix()
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
                if prefixes[prefix] != 1:
                    prefix = "%s-%s" % (prefix, prefixes[prefix])
                formset = FormSet(data=request.POST, files=request.FILES,
                                  instance=new_object,
                                  save_as_new="_saveasnew" in request.POST,
                                  prefix=prefix, queryset=inline.queryset(request))
                formsets.append(formset)
                for inline in self.get_inline_instances(request):
                    # If this is the inline that matches this formset, and
                    # we have some nested inlines to deal with, then we need
                    # to get the relevant formset for each of the forms in
                    # the current formset.
                    if inline.inlines and inline.model == formset.model:
                        for nested in inline.inline_instances:
                            for the_form in formset.forms:
                                InlineFormSet = nested.get_formset(request, the_form.instance)
                                prefix = "%s-%s" % (the_form.prefix, InlineFormSet.get_default_prefix())
                                formsets.append(InlineFormSet(request.POST, request.FILES, instance=the_form.instance, prefix=prefix))
            if all_valid(formsets) and form_validated:
                self.save_model(request, new_object, form, change=False)
                form.save_m2m()
                for formset in formsets:
                    self.save_formset(request, form, formset, change=False)

                self.log_addition(request, new_object)
                return self.response_add(request, new_object)
        else:
            # Prepare the dict of initial data from the request.
            # We have to special-case M2Ms as a list of comma-separated PKs.
            initial = dict(request.GET.items())
            for k in initial:
                try:
                    f = opts.get_field(k)
                except models.FieldDoesNotExist:
                    continue
                if isinstance(f, models.ManyToManyField):
                    initial[k] = initial[k].split(",")
            form = ModelForm(initial=initial)
            prefixes = {}
            for FormSet, inline in zip(self.get_formsets(request),
                                       self.get_inline_instances(request)):
                prefix = FormSet.get_default_prefix()
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
                if prefixes[prefix] != 1:
                    prefix = "%s-%s" % (prefix, prefixes[prefix])
                formset = FormSet(instance=self.model(), prefix=prefix,
                                  queryset=inline.queryset(request))
                formsets.append(formset)

        adminForm = helpers.AdminForm(form, list(self.get_fieldsets(request)),
            self.prepopulated_fields, self.get_readonly_fields(request),
            model_admin=self)
        media = self.media + adminForm.media

        inline_admin_formsets = []
        for inline, formset in zip(self.get_inline_instances(request), formsets):
            fieldsets = list(inline.get_fieldsets(request))
            readonly = list(inline.get_readonly_fields(request))
            inline_admin_formset = helpers.InlineAdminFormSet(inline, formset,
                fieldsets, readonly, model_admin=self)
            if inline.inlines:
                for form in formset.forms:
                    if form.instance.pk:
                        instance = form.instance
                    else:
                        instance = None
                    form.inlines = inline.get_inlines(request, instance, prefix=form.prefix)
                inline_admin_formset.inlines = inline.get_inlines(request)
            inline_admin_formsets.append(inline_admin_formset)
            media = media + inline_admin_formset.media

        context = {
            'title': _('Add %s') % force_unicode(opts.verbose_name),
            'adminform': adminForm,
            'is_popup': "_popup" in request.REQUEST,
            'show_delete': False,
            'media': mark_safe(media),
            'inline_admin_formsets': inline_admin_formsets,
            'errors': helpers.AdminErrorList(form, formsets),
            'app_label': opts.app_label,
        }
        context.update(extra_context or {})
        return self.render_change_form(request, context, form_url=form_url, add=True)

    @csrf_protect_m
    @transaction.commit_on_success
    def change_view(self, request, object_id, extra_context=None):
        "The 'change' admin view for this model."
        model = self.model
        opts = model._meta
        obj = self.get_object(request, unquote(object_id))

        if not self.has_change_permission(request, obj):
            raise PermissionDenied

        if obj is None:
            raise Http404(_('%(name)s object with primary key %(key)r does not exist.') % {'name': force_unicode(opts.verbose_name), 'key': escape(object_id)})

        if request.method == 'POST' and "_saveasnew" in request.POST:
            return self.add_view(request, form_url='../add/')

        ModelForm = self.get_form(request, obj)
        formsets = []
        if request.method == 'POST':
            form = ModelForm(request.POST, request.FILES, instance=obj)
            if form.is_valid():
                form_validated = True
                new_object = self.save_form(request, form, change=True)
            else:
                form_validated = False
                new_object = obj
            prefixes = {}
            for FormSet, inline in zip(self.get_formsets(request, new_object),
                                       self.get_inline_instances(request)):
                prefix = FormSet.get_default_prefix()
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
                if prefixes[prefix] != 1:
                    prefix = "%s-%s" % (prefix, prefixes[prefix])
                formset = FormSet(request.POST, request.FILES,
                                  instance=new_object, prefix=prefix,
                                  queryset=inline.queryset(request))

                formsets.append(formset)
                for inline in self.get_inline_instances(request):
                    # If this is the inline that matches this formset, and
                    # we have some nested inlines to deal with, then we need
                    # to get the relevant formset for each of the forms in
                    # the current formset.
                    if inline.inlines and inline.model == formset.model:
                        for nested in inline.inline_instances:
                            for the_form in formset.forms:
                                InlineFormSet = nested.get_formset(request, the_form.instance)
                                prefix = "%s-%s" % (the_form.prefix, InlineFormSet.get_default_prefix())
                                formsets.append(InlineFormSet(request.POST, request.FILES, instance=the_form.instance, prefix=prefix))
            if all_valid(formsets) and form_validated:
                self.save_model(request, new_object, form, change=True)
                form.save_m2m()
                for formset in formsets:
                    self.save_formset(request, form, formset, change=True)

                change_message = self.construct_change_message(request, form, formsets)
                self.log_change(request, new_object, change_message)
                return self.response_change(request, new_object)

        else:
            form = ModelForm(instance=obj)
            prefixes = {}
            for FormSet, inline in zip(self.get_formsets(request, obj), self.get_inline_instances(request)):
                prefix = FormSet.get_default_prefix()
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
                if prefixes[prefix] != 1:
                    prefix = "%s-%s" % (prefix, prefixes[prefix])
                formset = FormSet(instance=obj, prefix=prefix,
                                  queryset=inline.queryset(request))
                formsets.append(formset)

        adminForm = helpers.AdminForm(form, self.get_fieldsets(request, obj),
            self.prepopulated_fields, self.get_readonly_fields(request, obj),
            model_admin=self)
        media = self.media + adminForm.media

        inline_admin_formsets = []
        for inline, formset in zip(self.get_inline_instances(request), formsets):
            fieldsets = list(inline.get_fieldsets(request, obj))
            readonly = list(inline.get_readonly_fields(request, obj))
            inline_admin_formset = helpers.InlineAdminFormSet(inline, formset,
                fieldsets, readonly, model_admin=self)
            if inline.inlines:
                for form in formset.forms:
                    if form.instance.pk:
                        instance = form.instance
                    else:
                        instance = None
                    form.inlines = inline.get_inlines(request, instance, prefix=form.prefix)
                inline_admin_formset.inlines = inline.get_inlines(request)
            inline_admin_formsets.append(inline_admin_formset)
            media = media + inline_admin_formset.media

        context = {
            'title': _('Change %s') % force_unicode(opts.verbose_name),
            'adminform': adminForm,
            'object_id': object_id,
            'original': obj,
            'is_popup': "_popup" in request.REQUEST,
            'media': mark_safe(media),
            'inline_admin_formsets': inline_admin_formsets,
            'errors': helpers.AdminErrorList(form, formsets),
            'app_label': opts.app_label,
        }
        context.update(extra_context or {})
        return self.render_change_form(request, context, change=True, obj=obj)

    def get_inlines(self, request, obj=None, prefix=None):
        nested_inlines = []
        for inline in self.get_inline_instances(request):
            FormSet = inline.get_formset(request, obj)
            prefix = "%s-%s" % (prefix, FormSet.get_default_prefix())
            formset = FormSet(instance=obj, prefix=prefix)
            fieldsets = list(inline.get_fieldsets(request, obj))
            nested_inline = helpers.InlineAdminFormSet(inline, formset, fieldsets)
            nested_inlines.append(nested_inline)
        return nested_inlines


class NestedTabularInline(BaseModelAdmin):
    """
    Options for inline editing of ``model`` instances.

    Provide ``name`` to specify the attribute name of the ``ForeignKey`` from
    ``model`` to its parent. This is required if ``model`` has more than one
    ``ForeignKey`` to its parent.
    """
    model = None
    fk_name = None
    formset = BaseInlineFormSet
    extra = 3
    max_num = None
    template = None
    verbose_name = None
    verbose_name_plural = None
    can_delete = True
    template = 'common/admin/nested_tabular.html'
    inlines = []

    def __init__(self, parent_model, admin_site):
        self.admin_site = admin_site
        self.parent_model = parent_model
        self.opts = self.model._meta
        super(NestedTabularInline, self).__init__()
        if self.verbose_name is None:
            self.verbose_name = self.model._meta.verbose_name
        if self.verbose_name_plural is None:
            self.verbose_name_plural = self.model._meta.verbose_name_plural
        self.inline_instances = []
        for inline_class in self.inlines:
            inline_instance = inline_class(self.model, self.admin_site)
            self.inline_instances.append(inline_instance)

    def _media(self):
        from django.conf import settings
        js = ['js/jquery.min.js', 'js/jquery.init.js', 'js/inlines.min.js']
        if self.prepopulated_fields:
            js.append('js/urlify.js')
            js.append('js/prepopulate.min.js')
        if self.filter_vertical or self.filter_horizontal:
            js.extend(['js/SelectBox.js', 'js/SelectFilter2.js'])
        return forms.Media(js=['%s%s' % (settings.ADMIN_MEDIA_PREFIX, url) for url in js])
    media = property(_media)

    def get_formset(self, request, obj=None, **kwargs):
        """Returns a BaseInlineFormSet class for use in admin add/change views."""
        if self.declared_fieldsets:
            fields = flatten_fieldsets(self.declared_fieldsets)
        else:
            fields = None
        if self.exclude is None:
            exclude = []
        else:
            exclude = list(self.exclude)
        exclude.extend(kwargs.get("exclude", []))
        exclude.extend(self.get_readonly_fields(request, obj))
        # if exclude is an empty list we use None, since that's the actual
        # default
        exclude = exclude or None
        defaults = {
            "form": self.form,
            "formset": self.formset,
            "fk_name": self.fk_name,
            "fields": fields,
            "exclude": exclude,
            "formfield_callback": curry(self.formfield_for_dbfield, request=request),
            "extra": self.extra,
            "max_num": self.max_num,
            "can_delete": self.can_delete,
        }
        defaults.update(kwargs)
        return inlineformset_factory(self.parent_model, self.model, **defaults)

    def get_fieldsets(self, request, obj=None):
        if self.declared_fieldsets:
            return self.declared_fieldsets
        form = self.get_formset(request).form
        fields = form.base_fields.keys() + list(self.get_readonly_fields(request, obj))
        return [(None, {'fields': fields})]

    def get_inlines(self, request, obj=None, prefix=None):
        nested_inlines = []
        for inline in self.inline_instances:
            FormSet = inline.get_formset(request, obj)
            prefix = "%s-%s" % (prefix, FormSet.get_default_prefix())
            formset = FormSet(instance=obj, prefix=prefix)
            fieldsets = list(inline.get_fieldsets(request, obj))
            nested_inline = helpers.InlineAdminFormSet(inline, formset, fieldsets)
            nested_inlines.append(nested_inline)
        return nested_inlines

########NEW FILE########
__FILENAME__ = auth_backends
import logging

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User


class EmailBackend(ModelBackend):
    def authenticate(self, username=None, password=None):
        """
        "username" being passed is really email address and being compared to as such.
        """
        try:
            user = User.objects.get(email=username)
            if user.check_password(password):
                return user
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            logging.warn('Unsuccessful login attempt using username/email: %s' % username)
        
        return None

########NEW FILE########
__FILENAME__ = classmaker
# From http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/204197

import inspect, types, __builtin__

############## preliminary: two utility functions #####################

def skip_redundant(iterable, skipset=None):
    "Redundant items are repeated items or items in the original skipset."
    if skipset is None: skipset = set()
    for item in iterable:
        if item not in skipset:
            skipset.add(item)
            yield item


def remove_redundant(metaclasses):
    skipset = set([types.ClassType])
    for meta in metaclasses: # determines the metaclasses to be skipped
        skipset.update(inspect.getmro(meta)[1:])
    return tuple(skip_redundant(metaclasses, skipset))

##################################################################
## now the core of the module: two mutually recursive functions ##
##################################################################

memoized_metaclasses_map = {}

def get_noconflict_metaclass(bases, left_metas, right_metas):
    """Not intended to be used outside of this module, unless you know
    what you are doing."""
    # make tuple of needed metaclasses in specified priority order
    metas = left_metas + tuple(map(type, bases)) + right_metas
    needed_metas = remove_redundant(metas)

    # return existing confict-solving meta, if any
    if needed_metas in memoized_metaclasses_map:
      return memoized_metaclasses_map[needed_metas]
    # nope: compute, memoize and return needed conflict-solving meta
    elif not needed_metas:         # wee, a trivial case, happy us
        meta = type
    elif len(needed_metas) == 1: # another trivial case
       meta = needed_metas[0]
    # check for recursion, can happen i.e. for Zope ExtensionClasses
    elif needed_metas == bases: 
        raise TypeError("Incompatible root metatypes", needed_metas)
    else: # gotta work ...
        metaname = '_' + ''.join([m.__name__ for m in needed_metas])
        meta = classmaker()(metaname, needed_metas, {})
    memoized_metaclasses_map[needed_metas] = meta
    return meta

def classmaker(left_metas=(), right_metas=()):
    def make_class(name, bases, adict):
        metaclass = get_noconflict_metaclass(bases, left_metas, right_metas)
        return metaclass(name, bases, adict)
    return make_class

########NEW FILE########
__FILENAME__ = context_processors
from django.conf import settings as django_settings
from django_common.session import SessionManager


def common_settings(request):
    return {
        'domain_name': django_settings.DOMAIN_NAME,
        'www_root': django_settings.WWW_ROOT,
        'is_dev': django_settings.IS_DEV,
        'is_prod': django_settings.IS_PROD,
        'usertime': SessionManager(request).get_usertime()
    }

########NEW FILE########
__FILENAME__ = db_fields
import binascii
import random
import string

from django.db.models import fields
from django.template.defaultfilters import slugify
from django.db import models
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import simplejson as json
from django import forms
from django.conf import settings


from south.modelsinspector import add_introspection_rules
from django_common.helper import md5_hash


class JSONField(models.TextField):
    """
    JSONField is a generic textfield that neatly serializes/unserializes JSON objects seamlessly
    """

    # Used so to_python() is called
    __metaclass__ = models.SubfieldBase

    def to_python(self, value):
        """Convert our string value to JSON after we load it from the DB"""

        if value == "":
            return None

        try:
            if isinstance(value, basestring):
                return json.loads(value)
        except ValueError:
            pass

        return value

    def get_db_prep_save(self, value, connection=None):
        """Convert our JSON object to a string before we save"""

        if value == "":
            return None

        if isinstance(value, dict):
            value = json.dumps(value, cls=DjangoJSONEncoder)

        return super(JSONField, self).get_db_prep_save(value, connection)


class UniqueSlugField(fields.SlugField):
    """
    Represents a self-managing sluf field, that makes sure that the slug value is unique on the db table. Slugs by
    default get a db_index on them. The "Unique" in the class name is a misnomer since it does support unique=False

    @requires "prepopulate_from" in the constructor. This could be a field or a function in the model class which is using
    this field

    Defaults update_on_save to False

    Taken and edited from: http://www.djangosnippets.org/snippets/728/
    """
    def __init__(self, prepopulate_from='id', *args, **kwargs):
        if kwargs.get('update_on_save'):
            self.__update_on_save = kwargs.pop('update_on_save')
        else:
            self.__update_on_save = False
        self.prepopulate_from = prepopulate_from
        super(UniqueSlugField, self).__init__(*args, **kwargs)

    def pre_save(self, model_instance, add):
        prepopulate_field = getattr(model_instance, self.prepopulate_from)
        if callable(prepopulate_field):
            prepopulate_value = prepopulate_field()
        else:
            prepopulate_value = prepopulate_field

        # if object has an id, and not to update on save, then return existig model instance's slug value
        if getattr(model_instance, 'id') and not self.__update_on_save:
            return getattr(model_instance, self.name)

        # if this is a previously saved object, and current instance's slug is same as one being proposed
        if getattr(model_instance, 'id') and getattr(model_instance, self.name) == slugify(prepopulate_value):
            return getattr(model_instance, self.name)

        # if a unique slug is not required (not the default of course)
        if not self.unique:
            return self.__set_and_return(model_instance, self.name, slugify(prepopulate_value))

        return self.__unique_slug(model_instance.__class__, model_instance, self.name,
                                  prepopulate_value)

    def __unique_slug(self, model, model_instance, slug_field, slug_value):
        orig_slug = slug = slugify(slug_value)
        index = 1
        while True:
            try:
                model.objects.get(**{slug_field: slug})
                index += 1
                slug = orig_slug + '-' + str(index)
            except model.DoesNotExist:
                return self.__set_and_return(model_instance, slug_field, slug)

    def __set_and_return(self, model_instance, slug_field, slug):
        setattr(model_instance, slug_field, slug)
        return slug

add_introspection_rules([
    (
        [UniqueSlugField],  # Class(es) these apply to
        [],         # Positional arguments (not used)
        {           # Keyword argument
            "prepopulate_from": ["prepopulate_from", {"default": 'id'}],
        },
    ),
], ["^django_common\.db_fields\.UniqueSlugField"])


class RandomHashField(fields.CharField):
    """
    Store a random hash for a certain model field.

    @param update_on_save optional field whether to update this hash or not, everytime the model instance is saved
    """
    def __init__(self, update_on_save=False, hash_length=None, *args, **kwargs):
        #TODO: args & kwargs serve no purpose but to make django evolution to work
        self.update_on_save = update_on_save
        self.hash_length = hash_length
        super(fields.CharField, self).__init__(max_length=128, unique=True, blank=False, null=False, db_index=True, default=md5_hash(max_length=self.hash_length))

    def pre_save(self, model_instance, add):
        if not add and not self.update_on_save:
            return getattr(model_instance, self.name)

        random_hash = md5_hash(max_length=self.hash_length)
        setattr(model_instance, self.name, random_hash)
        return random_hash

add_introspection_rules([
    (
        [RandomHashField],  # Class(es) these apply to
        [],         # Positional arguments (not used)
        {           # Keyword argument
            "update_on_save": ["update_on_save", {"default": False}],
            "hash_length": ["hash_length", {"default": None}],
        },
    ),
], ["^django_common\.db_fields\.RandomHashField"])


class BaseEncryptedField(models.Field):
    '''This code is based on the djangosnippet #1095
    You can find the original at http://www.djangosnippets.org/snippets/1095/'''

    def __init__(self, *args, **kwargs):
        cipher = kwargs.pop('cipher', 'AES')
        imp = __import__('Crypto.Cipher', globals(), locals(), [cipher], -1)
        self.cipher = getattr(imp, cipher).new(settings.SECRET_KEY[:32])
        self.prefix = '$%s$' % cipher

        max_length = kwargs.get('max_length', 40)
        mod = max_length % self.cipher.block_size
        if mod > 0:
            max_length += self.cipher.block_size - mod
        kwargs['max_length'] = max_length * 2 + len(self.prefix)

        models.Field.__init__(self, *args, **kwargs)

    def _is_encrypted(self, value):
        return isinstance(value, basestring) and value.startswith(self.prefix)

    def _get_padding(self, value):
        mod = len(value) % self.cipher.block_size
        if mod > 0:
            return self.cipher.block_size - mod
        return 0

    def to_python(self, value):
        if self._is_encrypted(value):
            return self.cipher.decrypt(binascii.a2b_hex(value[len(self.prefix):])).split('\0')[0]
        return value

    def get_db_prep_value(self, value, connection=None, prepared=None):
        if value is not None and not self._is_encrypted(value):
            padding = self._get_padding(value)
            if padding > 0:
                value += "\0" + ''.join([random.choice(string.printable) for index in range(padding - 1)])
            value = self.prefix + binascii.b2a_hex(self.cipher.encrypt(value))
        return value


class EncryptedTextField(BaseEncryptedField):
    __metaclass__ = models.SubfieldBase

    def get_internal_type(self):
        return 'TextField'

    def formfield(self, **kwargs):
        defaults = {'widget': forms.Textarea}
        defaults.update(kwargs)
        return super(EncryptedTextField, self).formfield(**defaults)

add_introspection_rules([
    (
        [EncryptedTextField], [], {},
    ),
], ["^django_common\.db_fields\.EncryptedTextField"])


class EncryptedCharField(BaseEncryptedField):
    __metaclass__ = models.SubfieldBase

    def get_internal_type(self):
        return "CharField"

    def formfield(self, **kwargs):
        defaults = {'max_length': self.max_length}
        defaults.update(kwargs)
        return super(EncryptedCharField, self).formfield(**defaults)

add_introspection_rules([
    (
        [EncryptedCharField], [], {},
    ),
], ["^django_common\.db_fields\.EncryptedCharField"])

########NEW FILE########
__FILENAME__ = decorators
try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps

import inspect

from django.conf import settings
from django.http import HttpResponseRedirect


def ssl_required(allow_non_ssl=False):
    """Views decorated with this will always get redirected to https except when allow_non_ssl is set to true."""
    def wrapper(view_func):
        def _checkssl(request, *args, **kwargs):
            # allow_non_ssl=True lets non-https requests to come through to this view (and hence not redirect)
            if hasattr(settings, 'SSL_ENABLED') and settings.SSL_ENABLED and not request.is_secure() and not allow_non_ssl:
                return HttpResponseRedirect(request.build_absolute_uri().replace('http://', 'https://'))
            return view_func(request, *args, **kwargs)
        
        return _checkssl
    return wrapper

def disable_for_loaddata(signal_handler):
    """
    See: https://code.djangoproject.com/ticket/8399
    Disables signal from firing if its caused because of loaddata
    """
    @wraps(signal_handler)
    def wrapper(*args, **kwargs):
        for fr in inspect.stack():
            if inspect.getmodulename(fr[1]) == 'loaddata':
                return
        signal_handler(*args, **kwargs)
    return wrapper

def anonymous_required(view, redirect_to=None):
    """
    Only allow if user is NOT authenticated.
    """

    if redirect_to is None:
        redirect_to = settings.LOGIN_REDIRECT_URL

    @wraps(view)
    def wrapper(request, *a, **k):
        if request.user and request.user.is_authenticated():
            return HttpResponseRedirect(redirect_to)
        return view(request, *a, **k)
    return wrapper


########NEW FILE########
__FILENAME__ = email_backends
import os

from django.conf import settings

from django.core.mail.backends.smtp import EmailBackend
from django.core.mail.backends.filebased import EmailBackend as FileEmailBackend
from django.core.mail import message


class TestEmailBackend(EmailBackend):
    """
        Email Backend to overwrite TO, CC and BCC in all outgoing emails to custom
        values.

        Sample values from setting.py:
        EMAIL_BACKEND = 'django_common.email_backends.TestEmailBackend'
        TEST_EMAIL_TO = ['dev@tivix.com']  # default are addresses form ADMINS
        TEST_EMAIL_CC = ['dev-cc@tivix.com']  # default is empty list
        TEST_EMAIL_BCC = ['dev-bcc@tivix.com']  # default is empty list
    """

    def _send(self, email_message):
        """A helper method that does the actual sending."""
        if not email_message.recipients():
            return False
        from_email = email_message.from_email
        if hasattr(message, 'sanitize_address'):
            from_email = message.sanitize_address(email_message.from_email,
                                                  email_message.encoding)
        if hasattr(settings, 'TEST_EMAIL_TO'):
            email_message.to = settings.TEST_EMAIL_TO
        else:
            email_message.to = dict(getattr(settings, 'ADMINS', ())).values()
        email_message.cc = getattr(settings, 'TEST_EMAIL_CC', [])
        email_message.bcc = getattr(settings, 'TEST_EMAIL_BCC', [])
        if hasattr(message, 'sanitize_address'):
            recipients = [message.sanitize_address(addr, email_message.encoding)
                          for addr in email_message.recipients()]
        else:
            recipients = email_message.recipients()
        try:
            self.connection.sendmail(from_email, recipients,
                                     email_message.message().as_string())
        except:
            if not self.fail_silently:
                raise
            return False
        return True


class CustomFileEmailBackend(FileEmailBackend):
    """
        Email Backend to save emails as file with custom extension. It makes easier
        to open emails in email applications, f.e. with eml extension for mozilla
        thunderbird.

        Sample values from setting.py:
        EMAIL_BACKEND = 'django_common.email_backends.CustomFileEmailBackend'
        EMAIL_FILE_PATH = '/email/file/path/'
        EMAIL_FILE_EXT = 'eml'
    """

    def _get_filename(self):
        filename = super(CustomFileEmailBackend, self)._get_filename()
        if hasattr(settings, 'EMAIL_FILE_EXT'):
            filename = '%s.%s' % (os.path.splitext(filename)[0], settings.EMAIL_FILE_EXT.strip('.'))
        return filename

########NEW FILE########
__FILENAME__ = helper
"Some common routines that can be used throughout the code."
import hashlib, os, logging, datetime, threading

from django.utils import simplejson
from django.utils.encoding import force_unicode
from django.template import Context
from django.template.loader import get_template
from django.core import exceptions

from django_common.tzinfo import utc, Pacific


class AppException(exceptions.ValidationError):
    """Base class for exceptions used in our system.

    A common base class permits application code to distinguish between exceptions raised in our code from ones raised
    in libraries.
    """
    pass


class InvalidContentType(AppException):
    def __init__(self, file_types, msg=None):
        msg = msg or 'Only the following file content types are permitted: %s' % str(file_types)
        super(self.__class__, self).__init__(msg)
        self.file_types = file_types


class FileTooLarge(AppException):
    def __init__(self, file_size_kb, msg=None):
        msg = msg or 'Files may not be larger than %s KB' % file_size_kb
        super(self.__class__, self).__init__(msg)
        self.file_size = file_size_kb


def get_class(kls):
    """
    Converts a string to a class.
    Courtesy: http://stackoverflow.com/questions/452969/does-python-have-an-equivalent-to-java-class-forname/452981#452981
    """
    parts = kls.split('.')
    module = ".".join(parts[:-1])
    m = __import__(module)
    for comp in parts[1:]:
        m = getattr(m, comp)
    return m


def is_among(value, *possibilities):
    """Ensure that the method that has been used for the request is one of the expected ones (e.g., GET or POST)."""
    for possibility in possibilities:
        if value == possibility:
            return True
    raise Exception, 'A different request value was encountered than expected: %s' % value


def form_errors_serialize(form):
    errors = {}
    for field in form.fields.keys():
        if form.errors.has_key(field):
            if form.prefix:
                errors['%s-%s' % (form.prefix, field)] = force_unicode(form.errors[field])
            else:
                errors[field] = force_unicode(form.errors[field])

    if form.non_field_errors():
        errors['non_field_errors'] = force_unicode(form.non_field_errors())
    return {'errors': errors}


def json_response(data={}, errors=[], success=True):
    data.update({
        'errors': errors,
        'success': len(errors) == 0 and success,
    })
    return simplejson.dumps(data)


def sha224_hash():
    return hashlib.sha224(os.urandom(224)).hexdigest()


def sha1_hash():
    return hashlib.sha1(os.urandom(224)).hexdigest()


def md5_hash(image=None, max_length=None):
    # TODO:  Figure out how much entropy is actually needed, and reduce the current number of bytes if possible if doing
    # so will result in a performance improvement.
    if max_length:
        assert max_length > 0

    ret = hashlib.md5(image or os.urandom(224)).hexdigest()
    return ret if not max_length else ret[:max_length]


def start_thread(target, *args):
    t = threading.Thread(target=target, args=args)
    t.setDaemon(True)
    t.start()


def send_mail(subject, message, from_email, recipient_emails, files=None,
        html=False, reply_to=None, bcc=None, cc=None, files_manually=None):
    """Sends email with advanced optional parameters

    To attach non-file content (e.g. content not saved on disk), use
    files_manually parameter and provide list of 3 element tuples, e.g.
    [('design.png', img_data, 'image/png'),] which will be passed to
    email.attach().
    """
    import django.core.mail
    try:
        logging.debug('Sending mail to: %s' % ', '.join(r for r in recipient_emails))
        logging.debug('Message: %s' % message)
        email = django.core.mail.EmailMessage(subject, message, from_email, recipient_emails, bcc, cc=cc)
        if html:
            email.content_subtype = "html"
        if files:
            for file in files:
                email.attach_file(file)
        if files_manually:
            for filename, content, mimetype in files_manually:
                email.attach(filename, content, mimetype)
        if reply_to:
            email.extra_headers = {'Reply-To': reply_to}
        email.send()
    except Exception, e:
        # TODO:  Raise error again so that more information is included in the logs?
        logging.error('Error sending message [%s] from %s to %s %s' % (subject, from_email, recipient_emails, e))


def send_mail_in_thread(subject, message, from_email, recipient_emails, files=None, html=False, reply_to=None, bcc=None, cc=None, files_manually=None):
    start_thread(send_mail, subject, message, from_email, recipient_emails, files, html, reply_to, bcc, cc, files_manually)


def send_mail_using_template(subject, template_name, from_email, recipient_emails, context_map, in_thread=False, files=None, html=False, reply_to=None, bcc=None, cc=None, files_manually=None):
    t = get_template(template_name)
    message = t.render(Context(context_map))
    if in_thread:
        return send_mail_in_thread(subject, message, from_email, recipient_emails, files, html, reply_to, bcc, cc, files_manually)
    else:
        return send_mail(subject, message, from_email, recipient_emails, files, html, reply_to, bcc, cc, files_manually)


def utc_to_pacific(timestamp):
    return timestamp.replace(tzinfo=utc).astimezone(Pacific)


def pacific_to_utc(timestamp):
    return timestamp.replace(tzinfo=Pacific).astimezone(utc)


def humanize_time_since(timestamp = None):
    """Returns a fuzzy time since. Will only return the largest time. EX: 20 days, 14 min"""

    timeDiff = datetime.datetime.now() - timestamp
    days = timeDiff.days
    hours = timeDiff.seconds/3600
    minutes = timeDiff.seconds%3600/60
    seconds = timeDiff.seconds%3600%60

    str = ""
    tStr = ""
    if days > 0:
        if days == 1:   tStr = "day"
        else:           tStr = "days"
        str = str + "%s %s" %(days, tStr)
        return str
    elif hours > 0:
        if hours == 1:  tStr = "hour"
        else:           tStr = "hours"
        str = str + "%s %s" %(hours, tStr)
        return str
    elif minutes > 0:
        if minutes == 1:tStr = "min"
        else:           tStr = "mins"
        str = str + "%s %s" %(minutes, tStr)
        return str
    elif seconds > 0:
        if seconds == 1:tStr = "sec"
        else:           tStr = "secs"
        str = str + "%s %s" %(seconds, tStr)
        return str
    else:
        return str


def chunks(l, n):
    """ split successive n-sized chunks from a list."""
    for i in xrange(0, len(l), n):
        yield l[i:i+n]

########NEW FILE########
__FILENAME__ = http
from StringIO import StringIO

from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponsePermanentRedirect, HttpResponseRedirect, Http404
from django.utils import simplejson


class JsonResponse(HttpResponse):
  def __init__(self, data={ }, errors=[ ], success=True):
    """
    data is a map, errors a list
    """
    json = json_response(data=data, errors=errors, success=success)
    super(JsonResponse, self).__init__(json, mimetype='application/json')

class JsonpResponse(HttpResponse):
  """
  Padded JSON response, used for widget XSS
  """
  def __init__(self, request, data={ }, errors=[ ], success=True):
    """
    data is a map, errors a list
    """
    json = json_response(data=data, errors=errors, success=success)
    js = "%s(%s)" % (request.GET.get("jsonp", "jsonp_callback"), json)
    super(JsonpResponse, self).__init__(js, mimetype='application/javascipt')

def json_response(data={ }, errors=[ ], success=True):
  data.update({
    'errors': errors,
    'success': len(errors) == 0 and success,
  })
  return simplejson.dumps(data)


class XMLResponse(HttpResponse):
  def __init__(self, data):
    """
    data is the entire xml body/document
    """
    super(XMLResponse, self).__init__(data, mimetype='text/xml')

########NEW FILE########
__FILENAME__ = scaffold
from django.core.management.base import BaseCommand

from optparse import make_option

from django_common.scaffold import Scaffold
from django_common import settings


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--model', default=None, dest='model', \
            help="""model name - only one model name per run is allowed. \n
            It requires additional fields parameters:

            char - CharField \t\t\t\t
            text - TextField \t\t\t\t
            int - IntegerFIeld \t\t\t\t
            decimal -DecimalField \t\t\t\t
            datetime - DateTimeField \t\t\t\t
            foreign - ForeignKey \t\t\t\t

            Example usages: \t\t\t\t

                --model forum char:title  text:body int:posts datetime:create_date \t\t
                --model blog foreign:blog:Blog, foreign:post:Post, foreign:added_by:User \t\t
                --model finance decimal:total_cost:10:2

            """),
    )

    def handle(self, *args, **options):
        if len(args) == 0:
            print "You must provide app name. For example:\n\npython manage.py scallfold my_app\n"
            return
        scaffold = Scaffold(args[0], options['model'], args)
        scaffold.run()

    def get_version(self):
        return 'django-common version: %s' % settings.VERSION

########NEW FILE########
__FILENAME__ = middleware
from django.conf import settings
from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect
from django_common.session import SessionManager

WWW = 'www'

class WWWRedirectMiddleware(object):
    """
    Redirect requests for example from http://www.mysirw.com/* to http://mysite.com/*
    """
    def process_request(self, request):
        if settings.IS_PROD and request.get_host() != settings.DOMAIN_NAME:
            return HttpResponsePermanentRedirect('http%s://%s%s' % ('s' if request.is_secure() else '',\
                settings.DOMAIN_NAME, request.get_full_path()))
            return None

class UserTimeTrackingMiddleware(object):
    """
    Tracking time user have been on site
    """
    def process_request(self, request):
        if request.user and request.user.is_authenticated():
            SessionManager(request).ping_usertime()
        else:
            SessionManager(request).clear_usertime()

class SSLRedirectMiddleware(object):
    """Redirects all the requests that are non SSL to a SSL url"""
    def process_request(self, request):
        if not request.is_secure():
            return HttpResponseRedirect('https://%s%s' % (settings.DOMAIN_NAME, request.get_full_path()))
        return None

class NoSSLRedirectMiddleware(object):
    """
    Redirects if a non-SSL required view is hit. This middleware assumes a SSL protected view has been decorated
    by the 'ssl_required' decorator (see decorators.py)

    Redirects to https for admin though only for PROD
    """

    __DECORATOR_INNER_FUNC_NAME = '_checkssl'

    def __is_in_admin(self, request):
        return True if request.path.startswith('/admin/') else False

    def process_view(self, request, view_func, view_args, view_kwargs):
        if view_func.func_name != self.__DECORATOR_INNER_FUNC_NAME and\
            not (self.__is_in_admin(request) and settings.IS_PROD) and\
            request.is_secure(): # request is secure, but view is not decorated
            return HttpResponseRedirect('http://%s%s' % (settings.DOMAIN_NAME, request.get_full_path()))
        elif self.__is_in_admin(request) and not request.is_secure() and settings.IS_PROD:
            return HttpResponseRedirect('https://%s%s' % (settings.DOMAIN_NAME, request.get_full_path()))

########NEW FILE########
__FILENAME__ = scaffold
from os import path, system, listdir, sys, mkdir
from django.conf import settings
# VIEW CONSTS

LIST_VIEW = """
from %(app)s.forms import %(model)sForm
def %(lower_model)s_list(request, template='%(lower_model)s/list.html'):
    d = {}
    d['form'] = %(model)sForm()
    if request.method == 'POST':
        form = %(model)sForm(request.POST)
        if form.is_valid():
            item = form.save()
            return JsonResponse(data={'id': item.id, 'name': str(item), 'form': %(model)sForm().as_p(), 'token': get_token(request)})
        else:
            d['form'] = form
            return JsonResponse(data={'form': d['form'].as_p(), 'token': get_token(request)}, success=False)
    d['%(lower_model)s_list'] = %(model)s.objects.all()
    return render(request, template, d)
"""

DETAILS_VIEW = """
from %(app)s.forms import %(model)sForm
def %(lower_model)s_details(request, id, template='%(lower_model)s/details.html'):
    d = {}
    item = get_object_or_404(%(model)s, pk=id)
    d['form'] = %(model)sForm(instance=item)
    if request.method == 'POST':
        form = %(model)sForm(request.POST, instance=item)
        if form.is_valid():
            item = form.save()
            return JsonResponse(data={'form': %(model)sForm(instance=item).as_p(), 'token': get_token(request)})
        else:
            d['form'] = form
            return JsonResponse(data={'form': d['form'].as_p(), 'token': get_token(request)}, success=False)
    d['%(lower_model)s'] = %(model)s.objects.get(pk=id)
    return render(request, template, d)
"""

DELETE_VIEW = """
def %(lower_model)s_delete(request, id):
    item = %(model)s.objects.get(pk=id)
    item.delete()
    return JsonResponse()
"""
# MODELS CONSTS

MODEL_TEMPLATE = """
class %s(models.Model):
    %s
    update_date = models.DateTimeField(auto_now=True)
    create_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']
"""

IMPORT_MODEL_TEMPLATE = """from %(app)s.models import %(model)s"""

CHARFIELD_TEMPLATE = """
    %(name)s = models.CharField(max_length=%(length)s, null=%(null)s, blank=%(null)s)
"""

TEXTFIELD_TEMPLATE = """
    %(name)s = models.TextField(null=%(null)s, blank=%(null)s)
"""

INTEGERFIELD_TEMPLATE = """
    %(name)s = models.IntegerField(null=%(null)s, default=%(default)s)
"""

DECIMALFIELD_TEMPLATE = """
    %(name)s = models.DecimalField(max_digits=%(digits)s, decimal_places=%(places)s, null=%(null)s, default=%(default)s)
"""

DATETIMEFIELD_TEMPLATE = """
    %(name)s = models.DateTimeField(null=%(null)s, default=%(default)s)
"""

FOREIGNFIELD_TEMPLATE = """
    %(name)s = models.ForeignKey(%(foreign)s, null=%(null)s, blank=%(null)s)
"""

TEMPLATE_LIST_CONTENT = """
{%% extends "base.html" %%}

{%% block page-title %%}%(title)s{%% endblock %%}

{%% block content %%}
    <h1>%(model)s list</h1><br />
    <table style="border: solid 1px gray; width: 300px; text-align: center;" id="item-list">
        <tr style="background-color: #DDD">
            <th style="padding: 10px;">ID</th>
            <th>Name</th>
            <th>Action</th>
        </tr>
    {%% for item in %(model)s_list %%}
        <tr>
            <td style="padding: 10px;">{{ item.id }}</td>
            <td>{{ item }}</td>
            <td><a href="{%% url %(model)s-details item.id %%}">show</a></td>
        </tr>
    {%% endfor %%}
    </table>
    <br />
    <input type="button" onclick="$('#add-form-div').toggle();" value="Add new %(model)s"><br /><br />
    <div id="add-form-div" style="display: none;">
        <form action="{%% url %(model)s-list %%}" method="POST" id="add-form">
                <div id="form-fields">
                    {%% csrf_token %%}
                    {{ form }}
                </div>
                <input type="submit" value="Submit" />
        </form>
    </div>

    <script type="text/javascript">
        (new FormHelper('add-form')).bind_for_ajax(
            function(data) {
                $('#item-list').append('<td style="padding: 10px;">' + data.id + '</td><td>' + data.name + '</td><td><a href="{%% url %(model)s-list %%}' + data.id + '/">show</a></td>').hide().fadeIn();
                $('#form-fields').html('');
                $('#form-fields').append('<input type="hidden" value="' + data.token + '" name="csrfmiddlewaretoken">');
                $('#form-fields').append(data.form);
                $('#add-form-div').toggle();
            },
            function(data) {
                $('#form-fields').html('');
                $('#form-fields').append('<input type="hidden" value="' + data.token + '" name="csrfmiddlewaretoken">');
                $('#form-fields').append(data.form).hide().fadeIn();
                $('#add-form input[type=submit]').removeAttr('disabled');
            }
        );
    </script>
{%% endblock %%}
"""

TEMPLATE_DETAILS_CONTENT = """
{%% extends "base.html" %%}

{%% block page-title %%}%(title)s - {{ %(model)s }} {%% endblock %%}

{%% block content %%}
    <div class="item">
        <h1>%(model)s - {{ %(model)s }} </h1><br />
        <table style="border: solid 1px gray; width: 300px; text-align: center;" id="item-list">
            <tr style="background-color: #DDD">
                <th style="padding: 10px;">ID</th>
                <th>Name</th>
                <th>Action</th>
            </tr>
            <tr>
                <td style="padding: 10px;">{{ %(model)s.id }}</td>
                <td>{{ %(model)s }}</td>
                <td><input type="button" href="{%% url %(model)s-delete %(model)s.id %%}" id="delete-item" value="delete" /></td>
            </tr>
        </table>
        <br />
        <br />
        <br />
        <input type="button" onclick="$('#add-form-div').toggle();" value="Edit %(model)s"><br /><br />
        <div id="add-form-div" style="display: none;">
            <form action="{%% url %(model)s-details %(model)s.id %%}" method="POST" id="add-form">
                    <div id="form-fields">
                        {%% csrf_token %%}
                        {{ form }}
                    </div>
                    <input type="submit" value="Submit" />
            </form>
        </div>
    </div>

    <script type="text/javascript">
        (new FormHelper('add-form')).bind_for_ajax(
            function(data) {
                $('#form-fields').html('');
                $('#form-fields').append('<input type="hidden" value="' + data.token + '" name="csrfmiddlewaretoken">');
                $('#form-fields').append(data.form).hide().fadeIn();
                $('#add-form input[type=submit]').removeAttr('disabled');
            },
            function(data) {
                $('#form-fields').html('');
                $('#form-fields').append('<input type="hidden" value="' + data.token + '" name="csrfmiddlewaretoken">');
                $('#form-fields').append(data.form).hide().fadeIn();
                $('#add-form input[type=submit]').removeAttr('disabled');
            }
        );
        $('#delete-item').click(function() {
            $.get($(this).attr('href'), function(data) {
                $('div.item').before('<h1>Item removed</h1><br /><br />');
                $('div.item').remove();
            });
        });
    </script>
    <a href="{%% url %(model)s-list %%}">back to list</a>
{%% endblock %%}
"""

URL_CONTENT = """
from django.conf.urls.defaults import *
from django.contrib.auth import views as auth_views

urlpatterns = patterns('%(app)s.views',
    url(r'^%(model)s/$', '%(model)s_list', name='%(model)s-list'),
    url(r'^%(model)s/(?P<id>\d+)/$', '%(model)s_details', name='%(model)s-details'),
    url(r'^%(model)s/(?P<id>\d+)/delete/$', '%(model)s_delete', name='%(model)s-delete'),
)
"""

URL_EXISTS_CONTENT = """
    url(r'^%(model)s/$', '%(model)s_list', name='%(model)s-list'),
    url(r'^%(model)s/(?P<id>\d+)/$', '%(model)s_details', name='%(model)s-details'),
    url(r'^%(model)s/(?P<id>\d+)/delete/$', '%(model)s_delete', name='%(model)s-delete'),
"""

ADMIN_CONTENT = """
from %(app)s.models import %(model)s
admin.site.register(%(model)s)
"""

FORM_CONTENT = """

from %(app)s.models import %(model)s

class %(model)sForm(forms.ModelForm):
    class Meta:
        model = %(model)s
"""

TESTS_CONTENT = """

from %(app)s.models import %(model)s


class %(model)sTest(TestCase):

    def setUp(self):
        self.user = User.objects.create(username='test_user')

    def tearDown(self):
        self.user.delete()

    def test_list(self):
        response = self.client.get(reverse('%(lower_model)s-list'))
        self.failUnlessEqual(response.status_code, 200)

    def test_crud(self):
        # Create new instance
        response = self.client.post(reverse('%(lower_model)s-list'), {})
        self.assertContains(response, '"success": true')

        # Read instance
        items = %(model)s.objects.all()
        self.failUnlessEqual(items.count(), 1)
        item = items[0]
        response = self.client.get(reverse('%(lower_model)s-details', kwargs={'id': item.id}))
        self.failUnlessEqual(response.status_code, 200)

        # Update instance
        response = self.client.post(reverse('%(lower_model)s-details', kwargs={'id': item.id}), {})
        self.assertContains(response, '"success": true')

        # Delete instance
        response = self.client.post(reverse('%(lower_model)s-delete', kwargs={'id': item.id}), {})
        self.assertContains(response, '"success": true')
        items = %(model)s.objects.all()
        self.failUnlessEqual(items.count(), 0)

"""


class Scaffold(object):

    def _info(self, msg, indent=0):
        print "%s %s" % ("\t" * int(indent), msg)

    def __init__(self, app, model, fields):
        self.app = app
        self.model = model
        self.fields = fields

        try:
            self.SCAFFOLD_APPS_DIR = settings.SCAFFOLD_APPS_DIR
        except:
            self.SCAFFOLD_APPS_DIR = './'

    def get_import(self, model):
        for dir in listdir(self.SCAFFOLD_APPS_DIR):
            if path.isdir('%s%s' % (self.SCAFFOLD_APPS_DIR, dir)) and path.exists('%s%s/models.py' % (self.SCAFFOLD_APPS_DIR, dir)):
                dir_models_file = open('%s%s/models.py' % (self.SCAFFOLD_APPS_DIR, dir), 'r')
                # Check if model exists
                for line in dir_models_file.readlines():
                    if 'class %s(models.Model)' % model in line:
                        #print "Foreign key '%s' was found in app %s..." % (model, dir)
                        return IMPORT_MODEL_TEMPLATE % {'app': dir, 'model': model}
        return None

    def is_imported(self, path, model):
        import_file = open(path, 'r')
        for line in import_file.readlines():
            if 'import %s' % model in line:
                #print "Foreign key '%s' was found in models.py..." % (foreign)
                return True
        return False

    def add_global_view_imports(self, path):
        #from django.shortcuts import render, redirect, get_object_or_404, get_list_or_404
        import_list = list()
        import_file = open(path, 'r')

        need_import_shortcut = True
        need_import_urlresolvers = True
        need_import_users = True
        need_import_token = True
        need_import_JsonResponse = True

        for line in import_file.readlines():
            if 'from django.shortcuts import render, redirect, get_object_or_404' in line:
                need_import_shortcut = False
            if 'from django.core.urlresolvers import reverse' in line:
                need_import_urlresolvers = False
            if 'from django.contrib.auth.models import User, Group' in line:
                need_import_users = False
            if 'from django.middleware.csrf import get_token' in line:
                need_import_token = False
            if 'from django_common.http import JsonResponse' in line:
                need_import_JsonResponse = False

        if need_import_shortcut:
            import_list.append('from django.shortcuts import render, redirect, get_object_or_404')
        if need_import_urlresolvers:
            import_list.append('from django.core.urlresolvers import reverse')
        if need_import_users:
            import_list.append('from django.contrib.auth.models import User, Group')
        if need_import_token:
            import_list.append('from django.middleware.csrf import get_token')
        if need_import_JsonResponse:
            import_list.append('from django_common.http import JsonResponse')

        return import_list

    def view_exists(self, path, view):
        # Check if view already exists
        view_file = open(path, 'r')
        for line in view_file.readlines():
            if 'def %s(' % view in line:
                return True
        return False

    def get_field(self, field):
        field = field.split(':')
        field_type = field[0]
        if field_type.lower() == 'char':
            try:
                length = field[2]
            except:
                length = 255
            try:
                null = field[3]
                null = 'False'
            except:
                null = 'True'
            return CHARFIELD_TEMPLATE % {'name': field[1], 'length': length, 'null': null}
        elif field_type.lower() == 'text':
            try:
                null = field[2]
                null = 'False'
            except:
                null = 'True'
            return TEXTFIELD_TEMPLATE % {'name': field[1], 'null': null}
        elif field_type.lower() == 'int':
            try:
                null = field[2]
                null = 'False'
            except:
                null = 'True'
            try:
                default = field[3]
            except:
                default = None
            return INTEGERFIELD_TEMPLATE % {'name': field[1], 'null': null, 'default': default}
        elif field_type.lower() == 'decimal':
            try:
                null = field[4]
                null = 'False'
            except:
                null = 'True'
            try:
                default = field[5]
            except:
                default = None
            return DECIMALFIELD_TEMPLATE % {'name': field[1], 'digits': field[2], 'places': field[3], 'null': null, 'default': default}
        elif field_type.lower() == 'datetime':
            try:
                null = field[2]
                null = 'False'
            except:
                null = 'True'
            try:
                default = field[3]
            except:
                default = None
            return DATETIMEFIELD_TEMPLATE % {'name': field[1], 'null': null, 'default': default}
        elif field_type.lower() == 'foreign':
            foreign = field[2]
            name = field[1]
            # Check if this foreign key is already in models.py
            if foreign in ('User', 'Group'):
                if not self.is_imported('%s%s/models.py' % (self.SCAFFOLD_APPS_DIR, self.app), foreign):
                    self.imports.append('\nfrom django.contrib.auth.models import User, Group\n')
                return FOREIGNFIELD_TEMPLATE % {'name': name, 'foreign': foreign, 'null': 'True'}
            if self.is_imported('%s%s/models.py' % (self.SCAFFOLD_APPS_DIR, self.app), foreign):
                return FOREIGNFIELD_TEMPLATE % {'name': name, 'foreign': foreign, 'null': 'True'}
            # Check imports
            if self.get_import(foreign):
                self.imports.append(self.get_import(foreign))
                return FOREIGNFIELD_TEMPLATE % {'name': name, 'foreign': foreign, 'null': 'True'}

            self._info('error\t%s%s/models.py\t%s class not found' % (self.SCAFFOLD_APPS_DIR, self.app, foreign), 1)
            return None

    def create_app(self):
        self._info("    App    ")
        self._info("===========")
        if self.SCAFFOLD_APPS_DIR and not path.exists('%s' % self.SCAFFOLD_APPS_DIR):
            raise Exception("SCAFFOLD_APPS_DIR %s does not exists" % self.SCAFFOLD_APPS_DIR)
        if not path.exists('%s%s' % (self.SCAFFOLD_APPS_DIR, self.app)):
            system('python manage.py startapp %s' % self.app)
            system('mv %s %s%s' % (self.app, self.SCAFFOLD_APPS_DIR, self.app))
            self._info("create\t%s%s" % (self.SCAFFOLD_APPS_DIR, self.app), 1)
        else:
            self._info("exists\t%s%s" % (self.SCAFFOLD_APPS_DIR, self.app), 1)

    def create_views(self):
        self._info("   Views   ")
        self._info("===========")
        # Open models.py to read
        view_path = '%s%s/views.py' % (self.SCAFFOLD_APPS_DIR, self.app)

        # Check if urls.py exists

        if path.exists('%s%s/views.py' % (self.SCAFFOLD_APPS_DIR, self.app)):
            self._info('exists\t%s%s/views.py' % (self.SCAFFOLD_APPS_DIR, self.app), 1)
        else:
            open("%s%s/views.py" % (self.SCAFFOLD_APPS_DIR, self.app), 'w')
            self._info('create\t%s%s/views.py' % (self.SCAFFOLD_APPS_DIR, self.app), 1)

        import_list = list()
        view_list = list()

        # Add global imports
        import_list.append('\n'.join(imp for imp in self.add_global_view_imports(view_path)))

        # Add model imports
        if not self.is_imported(view_path, self.model):
            import_list.append(self.get_import(self.model))

        lower_model = self.model.lower()

        # Check if view already exists
        if not self.view_exists(view_path, "%s_list" % lower_model):
            view_list.append(LIST_VIEW % {'lower_model': lower_model, 'model': self.model, 'app': self.app})
            self._info("added \t%s\t%s_view" % (view_path, lower_model), 1)
        else:
            self._info("exists\t%s\t%s_view" % (view_path, lower_model), 1)

        if not self.view_exists(view_path, "%s_details" % lower_model):
            view_list.append(DETAILS_VIEW % {'lower_model': lower_model, 'model': self.model, 'app': self.app})
            self._info("added \t%s\t%s_details" % (view_path, lower_model), 1)
        else:
            self._info("exists\t%s\t%s_details" % (view_path, lower_model), 1)

        if not self.view_exists(view_path, "%s_delete" % lower_model):
            view_list.append(DELETE_VIEW % {'lower_model': lower_model, 'model': self.model})
            self._info("added \t%s\t%s_delete" % (view_path, lower_model), 1)
        else:
            self._info("exists\t%s\t%s_delete" % (view_path, lower_model), 1)

        # Open views.py to append
        view_file = open(view_path, 'a')

        view_file.write('\n'.join(import_line for import_line in import_list))
        view_file.write(''.join(view for view in view_list))

    def create_model(self):
        self._info("   Model   ")
        self._info("===========")
        # Open models.py to read
        self.models_file = open('%s%s/models.py' % (self.SCAFFOLD_APPS_DIR, self.app), 'r')

        # Check if model already exists
        for line in self.models_file.readlines():
            if 'class %s' % self.model in line:
                self._info('exists\t%s%s/models.py' % (self.SCAFFOLD_APPS_DIR, self.app), 1)
                return

        self._info('create\t%s%s/models.py' % (self.SCAFFOLD_APPS_DIR, self.app), 1)
        # Prepare fields
        self.imports = list()
        fields = list()
        for field in self.fields:
            new_field = self.get_field(field)
            if new_field:
                fields.append(new_field)
                self._info('added\t%s%s/models.py\t%s field' % (self.SCAFFOLD_APPS_DIR, self.app, field.split(':')[1]), 1)

        # Open models.py to append
        models_file = open('%s%s/models.py' % (self.SCAFFOLD_APPS_DIR, self.app), 'a')

        models_file.write(''.join(import_line for import_line in self.imports))
        models_file.write(MODEL_TEMPLATE % (self.model, ''.join(field for field in fields)))

    def create_templates(self):
        self._info(" Templates ")
        self._info("===========")

        # Check if template dir exists

        if path.exists('%s%s/templates/' % (self.SCAFFOLD_APPS_DIR, self.app)):
            self._info('exists\t%s%s/templates/' % (self.SCAFFOLD_APPS_DIR, self.app), 1)
        else:
            mkdir("%s%s/templates/" % (self.SCAFFOLD_APPS_DIR, self.app))
            self._info('create\t%s%s/templates/' % (self.SCAFFOLD_APPS_DIR, self.app), 1)

        # Check if model template dir exists

        if path.exists('%s%s/templates/%s/' % (self.SCAFFOLD_APPS_DIR, self.app, self.model.lower())):
            self._info('exists\t%s%s/templates/%s/' % (self.SCAFFOLD_APPS_DIR, self.app, self.model.lower()), 1)
        else:
            mkdir("%s%s/templates/%s/" % (self.SCAFFOLD_APPS_DIR, self.app, self.model.lower()))
            self._info('create\t%s%s/templates/%s/' % (self.SCAFFOLD_APPS_DIR, self.app, self.model.lower()), 1)

        # Check if list.html exists

        if path.exists('%s%s/templates/%s/list.html' % (self.SCAFFOLD_APPS_DIR, self.app, self.model.lower())):
            self._info('exists\t%s%s/templates/%s/list.html' % (self.SCAFFOLD_APPS_DIR, self.app, self.model.lower()), 1)
        else:
            file = open("%s%s/templates/%s/list.html" % (self.SCAFFOLD_APPS_DIR, self.app, self.model.lower()), 'w')
            file.write(TEMPLATE_LIST_CONTENT % {'model': self.model.lower(), 'title': self.model.lower()})
            self._info('create\t%s%s/templates/%s/list.html' % (self.SCAFFOLD_APPS_DIR, self.app, self.model.lower()), 1)

        # Check if details.html exists

        if path.exists('%s%s/templates/%s/details.html' % (self.SCAFFOLD_APPS_DIR, self.app, self.model.lower())):
            self._info('exists\t%s%s/templates/%s/details.html' % (self.SCAFFOLD_APPS_DIR, self.app, self.model.lower()), 1)
        else:
            file = open("%s%s/templates/%s/details.html" % (self.SCAFFOLD_APPS_DIR, self.app, self.model.lower()), 'w')
            file.write(TEMPLATE_DETAILS_CONTENT % {'model': self.model.lower(), 'title': self.model.lower()})
            self._info('create\t%s%s/templates/%s/details.html' % (self.SCAFFOLD_APPS_DIR, self.app, self.model.lower()), 1)

    def create_urls(self):
        self._info("    URLs   ")
        self._info("===========")

        # Check if urls.py exists

        if path.exists('%s%s/urls.py' % (self.SCAFFOLD_APPS_DIR, self.app)):

            # If does we need to add urls
            new_urls = ''
            for line in open("%s%s/urls.py" % (self.SCAFFOLD_APPS_DIR, self.app), 'r').readlines():
                new_urls += line
                if 'urlpatterns' in line:
                    new_urls += URL_EXISTS_CONTENT % {'app': self.app, 'model': self.model.lower()}
            file = open("%s%s/urls.py" % (self.SCAFFOLD_APPS_DIR, self.app), 'w')
            file.write(new_urls)
            self._info('update\t%s%s/urls.py' % (self.SCAFFOLD_APPS_DIR, self.app), 1)
        else:
            file = open("%s%s/urls.py" % (self.SCAFFOLD_APPS_DIR, self.app), 'w')
            file.write(URL_CONTENT % {'app': self.app, 'model': self.model.lower()})
            self._info('create\t%s%s/urls.py' % (self.SCAFFOLD_APPS_DIR, self.app), 1)

    def create_admin(self):
        self._info("    Admin  ")
        self._info("===========")

        # Check if admin.py exists

        if path.exists('%s%s/admin.py' % (self.SCAFFOLD_APPS_DIR, self.app)):
            self._info('exists\t%s%s/admin.py' % (self.SCAFFOLD_APPS_DIR, self.app), 1)
        else:
            file = open("%s%s/admin.py" % (self.SCAFFOLD_APPS_DIR, self.app), 'w')
            file.write("from django.contrib import admin\n")
            self._info('create\t%s%s/urls.py' % (self.SCAFFOLD_APPS_DIR, self.app), 1)

        # Check if admin entry already exists

        content = open("%s%s/admin.py" % (self.SCAFFOLD_APPS_DIR, self.app), 'r').read()
        if "admin.site.register(%s)" % self.model in content:
            self._info('exists\t%s%s/admin.py\t%s' % (self.SCAFFOLD_APPS_DIR, self.app, self.model.lower()), 1)
        else:
            file = open("%s%s/admin.py" % (self.SCAFFOLD_APPS_DIR, self.app), 'a')
            file.write(ADMIN_CONTENT % {'app': self.app, 'model': self.model})
            self._info('added\t%s%s/admin.py\t%s' % (self.SCAFFOLD_APPS_DIR, self.app, self.model.lower()), 1)

    def create_forms(self):
        self._info("    Forms  ")
        self._info("===========")

        # Check if forms.py exists
        if path.exists('%s%s/forms.py' % (self.SCAFFOLD_APPS_DIR, self.app)):
            self._info('exists\t%s%s/forms.py' % (self.SCAFFOLD_APPS_DIR, self.app), 1)
        else:
            file = open("%s%s/forms.py" % (self.SCAFFOLD_APPS_DIR, self.app), 'w')
            file.write("from django import forms\n")
            self._info('create\t%s%s/forms.py' % (self.SCAFFOLD_APPS_DIR, self.app), 1)

        # Check if form entry already exists

        content = open("%s%s/forms.py" % (self.SCAFFOLD_APPS_DIR, self.app), 'r').read()
        if "class %sForm" % self.model in content:
            self._info('exists\t%s%s/forms.py\t%s' % (self.SCAFFOLD_APPS_DIR, self.app, self.model.lower()), 1)
        else:
            file = open("%s%s/forms.py" % (self.SCAFFOLD_APPS_DIR, self.app), 'a')
            file.write(FORM_CONTENT % {'app': self.app, 'model': self.model})
            self._info('added\t%s%s/forms.py\t%s' % (self.SCAFFOLD_APPS_DIR, self.app, self.model.lower()), 1)

    def create_tests(self):
        self._info("   Tests   ")
        self._info("===========")

        # Check if tests.py exists
        if path.exists('%s%s/tests.py' % (self.SCAFFOLD_APPS_DIR, self.app)):
            self._info('exists\t%s%s/tests.py' % (self.SCAFFOLD_APPS_DIR, self.app), 1)
            # Check if imports exists:
            import_testcase = True
            import_user = True
            import_reverse = True
            for line in open("%s%s/tests.py" % (self.SCAFFOLD_APPS_DIR, self.app), 'r').readlines():
                if 'import TestCase' in line:
                    import_testcase = False
                if 'import User' in line:
                    import_user = False
                if 'import reverse' in line:
                    import_reverse = False
            file = open("%s%s/tests.py" % (self.SCAFFOLD_APPS_DIR, self.app), 'a')
            if import_testcase:
                file.write("from django.test import TestCase\n")
            if import_user:
                file.write("from django.contrib.auth.models import User\n")
            if import_reverse:
                file.write("from django.core.urlresolvers import reverse\n")
        else:
            file = open("%s%s/tests.py" % (self.SCAFFOLD_APPS_DIR, self.app), 'w')
            file.write("from django.test import TestCase\n")
            file.write("from django.contrib.auth.models import User\n")
            file.write("from django.core.urlresolvers import reverse\n")
            self._info('create\t%s%s/tests.py' % (self.SCAFFOLD_APPS_DIR, self.app), 1)

        # Check if test class already exists
        content = open("%s%s/tests.py" % (self.SCAFFOLD_APPS_DIR, self.app), 'r').read()
        if "class %sTest" % self.model in content:
            self._info('exists\t%s%s/tests.py\t%s' % (self.SCAFFOLD_APPS_DIR, self.app, self.model.lower()), 1)
        else:
            file = open("%s%s/tests.py" % (self.SCAFFOLD_APPS_DIR, self.app), 'a')
            file.write(TESTS_CONTENT % {'app': self.app, 'model': self.model, 'lower_model': self.model.lower()})
            self._info('added\t%s%s/tests.py\t%s' % (self.SCAFFOLD_APPS_DIR, self.app, self.model.lower()), 1)

    def run(self):
        if not self.app:
            sys.exit("No application name found...")
        if not self.app.isalnum():
            sys.exit("Model name should be alphanumerical...")
        self.create_app()
        if self.model:
            self.create_model()
            self.create_views()
            self.create_admin()
            self.create_forms()
            self.create_urls()
            self.create_templates()
            self.create_tests()

########NEW FILE########
__FILENAME__ = session
from datetime import datetime, timedelta
from django.conf import settings

class SessionManagerBase(object):
    """
    Base class that a "SessionManager" concrete class should extend. It should have a list called _SESSION_KEYS that
    lists all the keys that class uses/depends on.
    
    Ideally each app has a session.py that has this class and is used in the apps views etc.
    """
    def __init__(self, request, prepend_key_with=''):
        self._session = request.session
        self._prepend_key_with = prepend_key_with
  
    def _get_or_set(self, key, value):
        key = '%s%s' % (self._prepend_key_with, key)
        
        if not value is None:
            self._session[key] = value
            return value
        return self._session.get(key)
  
    def reset_keys(self):
        for key in self._SESSION_KEYS:
            key = '%s%s' % (self._prepend_key_with, key)
            
            if self._session.has_key(key):
                del self._session[key]


class SessionManager(SessionManagerBase):
    """Manages storing the cart"""

    USER_ONLINE_TIMEOUT = 180  # 3 min

    USERTIME = 'usertime'
    _GENERIC_VAR_KEY_PREFIX = 'lpvar_'   # handles generic stuff being stored in the session

    _SESSION_KEYS = [
        USERTIME,
    ]

    def __init__(self, request):
        super(SessionManager, self).__init__(request, prepend_key_with=request.get_host())
        if not self._get_or_set(self.USERTIME, None):
            self._get_or_set(self.USERTIME, None)

    def get_usertime(self):
        usertime = self._get_or_set(self.USERTIME, None)
        try:
            return usertime['last'] - usertime['start']
        except:
            return 0

    def ping_usertime(self):
        # Override default user online timeout
        try:
            timeout = int(settings.USER_ONLINE_TIMEOUT)
        except:
            timeout = self.USER_ONLINE_TIMEOUT
        if not self._get_or_set(self.USERTIME, None):
            self._get_or_set(self.USERTIME, {'start': datetime.now(), 'last': datetime.now()})
        else:
            usertime = self._get_or_set(self.USERTIME, None)
            if usertime['last'] + timedelta(seconds=timeout) < datetime.now():
                # This mean user reached timeout - we start from begining
                self._get_or_set(self.USERTIME, {'start': datetime.now(), 'last': datetime.now()})
            else:
                # We just update last time
                usertime['last'] = datetime.now()
        return self._get_or_set(self.USERTIME, None)

    def clear_usertime(self):
        return self._get_or_set(self.USERTIME, {})

    def generic_var(self, key, value=None):
        """Stores generic variables in the session prepending it with
        _GENERIC_VAR_KEY_PREFIX."""
        return self._get_or_set('%s%s' % (self._GENERIC_VAR_KEY_PREFIX, key), value)

########NEW FILE########
__FILENAME__ = settings
VERSION = '0.6.0'

########NEW FILE########
__FILENAME__ = custom_tags
from django import template
from django.forms import widgets
from django.template.loader import get_template
from django.template import Context

register = template.Library()


class FormFieldNode(template.Node):
    """
    Helper class for the render_form_field below
    """
    def __init__(self, form_field, help_text=None, css_classes=None):
        self.form_field = template.Variable(form_field)
        self.help_text = help_text[1:-1] if help_text else help_text
        self.css_classes = css_classes[1:-1] if css_classes else css_classes

    def render(self, context):
        try:
            form_field = self.form_field.resolve(context)
        except template.VariableDoesNotExist:
            return ''

        widget = form_field.field.widget

        if isinstance(widget, widgets.RadioSelect):
            t = get_template('common/fragments/radio_field.html')
        elif isinstance(widget, widgets.CheckboxInput):
            t = get_template('common/fragments/checkbox_field.html')
        elif isinstance(widget, widgets.CheckboxSelectMultiple):
            t = get_template('common/fragments/multi_checkbox_field.html')
        else:
            t = get_template('common/fragments/form_field.html')

        if self.help_text is None:
            self.help_text = form_field.help_text

        return t.render(Context({
            'form_field': form_field,
            'help_text': self.help_text,
            'css_classes': self.css_classes
        }))


@register.tag
def render_form_field(parser, token):
    """
    Usage is {% render_form_field form.field_name optional_help_text optional_css_classes %}

    - optional_help_text and optional_css_classes are strings
    - if optional_help_text is not given, then it is taken from form field object
    """
    try:
        help_text = None
        css_classes = None

        token_split = token.split_contents()
        if len(token_split) == 4:
            tag_name, form_field, help_text, css_classes = token.split_contents()
        elif len(token_split) == 3:
            tag_name, form_field, help_text = token.split_contents()
        else:
            tag_name, form_field = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "Unable to parse arguments for %r" % token.contents.split()[0]

    return FormFieldNode(form_field, help_text=help_text, css_classes=css_classes)


@register.simple_tag
def active(request, pattern):
    """
    Returns the string 'active' if pattern matches. Used to assign a css class in navigation bars to active tab/section
    """
    if request.path == pattern:
        return 'active'
    return ''


@register.simple_tag
def active_starts(request, pattern):
    """
    Returns the string 'active' if request url starts with pattern. Used to assign a css class in navigation bars to
    active tab/section
    """
    if request.path.startswith(pattern):
        return 'active'
    return ''

########NEW FILE########
__FILENAME__ = tests
from django.utils import unittest


class SimpleTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def test_example(self):
        """Some test example"""
        pass

########NEW FILE########
__FILENAME__ = tzinfo
# From the python documentation
# http://docs.python.org/library/datetime.html
from datetime import tzinfo, timedelta, datetime

ZERO = timedelta(0)
HOUR = timedelta(hours=1)

# A UTC class.

class UTC(tzinfo):
    """UTC"""

    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO

utc = UTC()

# A class building tzinfo objects for fixed-offset time zones.
# Note that FixedOffset(0, "UTC") is a different way to build a
# UTC tzinfo object.

class FixedOffset(tzinfo):
    """Fixed offset in minutes east from UTC."""

    def __init__(self, offset, name):
        self.__offset = timedelta(minutes = offset)
        self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return ZERO

# A class capturing the platform's idea of local time.

import time as _time

STDOFFSET = timedelta(seconds = -_time.timezone)
if _time.daylight:
    DSTOFFSET = timedelta(seconds = -_time.altzone)
else:
    DSTOFFSET = STDOFFSET

DSTDIFF = DSTOFFSET - STDOFFSET

class LocalTimezone(tzinfo):

    def utcoffset(self, dt):
        if self._isdst(dt):
            return DSTOFFSET
        else:
            return STDOFFSET

    def dst(self, dt):
        if self._isdst(dt):
            return DSTDIFF
        else:
            return ZERO

    def tzname(self, dt):
        return _time.tzname[self._isdst(dt)]

    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day,
              dt.hour, dt.minute, dt.second,
              dt.weekday(), 0, -1)
        stamp = _time.mktime(tt)
        tt = _time.localtime(stamp)
        return tt.tm_isdst > 0

Local = LocalTimezone()


# A complete implementation of current DST rules for major US time zones.

def first_sunday_on_or_after(dt):
    days_to_go = 6 - dt.weekday()
    if days_to_go:
        dt += timedelta(days_to_go)
    return dt


## US DST Rules
#
# This is a simplified (i.e., wrong for a few cases) set of rules for US
# DST start and end times. For a complete and up-to-date set of DST rules
# and timezone definitions, visit the Olson Database (or try pytz):
# http://www.twinsun.com/tz/tz-link.htm
# http://sourceforge.net/projects/pytz/ (might not be up-to-date)
#
# In the US, since 2007, DST starts at 2am (standard time) on the second
# Sunday in March, which is the first Sunday on or after Mar 8.
DSTSTART_2007 = datetime(1, 3, 8, 2)
# and ends at 2am (DST time; 1am standard time) on the first Sunday of Nov.
DSTEND_2007 = datetime(1, 11, 1, 1)
# From 1987 to 2006, DST used to start at 2am (standard time) on the first
# Sunday in April and to end at 2am (DST time; 1am standard time) on the last
# Sunday of October, which is the first Sunday on or after Oct 25.
DSTSTART_1987_2006 = datetime(1, 4, 1, 2)
DSTEND_1987_2006 = datetime(1, 10, 25, 1)
# From 1967 to 1986, DST used to start at 2am (standard time) on the last
# Sunday in April (the one on or after April 24) and to end at 2am (DST time;
# 1am standard time) on the last Sunday of October, which is the first Sunday
# on or after Oct 25.
DSTSTART_1967_1986 = datetime(1, 4, 24, 2)
DSTEND_1967_1986 = DSTEND_1987_2006

class USTimeZone(tzinfo):

    def __init__(self, hours, reprname, stdname, dstname):
        self.stdoffset = timedelta(hours=hours)
        self.reprname = reprname
        self.stdname = stdname
        self.dstname = dstname

    def __repr__(self):
        return self.reprname

    def tzname(self, dt):
        if self.dst(dt):
            return self.dstname
        else:
            return self.stdname

    def utcoffset(self, dt):
        return self.stdoffset + self.dst(dt)

    def dst(self, dt):
        if dt is None or dt.tzinfo is None:
            # An exception may be sensible here, in one or both cases.
            # It depends on how you want to treat them.  The default
            # fromutc() implementation (called by the default astimezone()
            # implementation) passes a datetime with dt.tzinfo is self.
            return ZERO
        assert dt.tzinfo is self

        # Find start and end times for US DST. For years before 1967, return
        # ZERO for no DST.
        if 2006 < dt.year:
            dststart, dstend = DSTSTART_2007, DSTEND_2007
        elif 1986 < dt.year < 2007:
            dststart, dstend = DSTSTART_1987_2006, DSTEND_1987_2006
        elif 1966 < dt.year < 1987:
            dststart, dstend = DSTSTART_1967_1986, DSTEND_1967_1986
        else:
            return ZERO

        start = first_sunday_on_or_after(dststart.replace(year=dt.year))
        end = first_sunday_on_or_after(dstend.replace(year=dt.year))

        # Can't compare naive to aware objects, so strip the timezone from
        # dt first.
        if start <= dt.replace(tzinfo=None) < end:
            return HOUR
        else:
            return ZERO

Eastern  = USTimeZone(-5, "Eastern",  "EST", "EDT")
Central  = USTimeZone(-6, "Central",  "CST", "CDT")
Mountain = USTimeZone(-7, "Mountain", "MST", "MDT")
Pacific  = USTimeZone(-8, "Pacific",  "PST", "PDT")

########NEW FILE########
