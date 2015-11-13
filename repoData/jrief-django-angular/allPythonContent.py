__FILENAME__ = urlresolvers
# -*- coding: utf-8 -*-
from inspect import isclass
from django.utils import six
from django.utils.module_loading import import_by_path
from django.core.urlresolvers import (get_resolver, get_urlconf, get_script_prefix,
    get_ns_resolver, iri_to_uri, resolve, reverse, NoReverseMatch)
from django.core.exceptions import ImproperlyConfigured
from djangular.views.mixins import JSONResponseMixin


def urls_by_namespace(namespace, urlconf=None, args=None, kwargs=None, prefix=None, current_app=None):
    """
    Return a dictionary containing the name together with the URL of all configured
    URLs specified for this namespace.
    """
    if urlconf is None:
        urlconf = get_urlconf()
    resolver = get_resolver(urlconf)
    args = args or []
    kwargs = kwargs or {}

    if prefix is None:
        prefix = get_script_prefix()

    if not namespace or not isinstance(namespace, six.string_types):
        raise AttributeError('Attribute namespace must be of type string')
    path = namespace.split(':')
    path.reverse()
    resolved_path = []
    ns_pattern = ''
    while path:
        ns = path.pop()

        # Lookup the name to see if it could be an app identifier
        try:
            app_list = resolver.app_dict[ns]
            # Yes! Path part matches an app in the current Resolver
            if current_app and current_app in app_list:
                # If we are reversing for a particular app,
                # use that namespace
                ns = current_app
            elif ns not in app_list:
                # The name isn't shared by one of the instances
                # (i.e., the default) so just pick the first instance
                # as the default.
                ns = app_list[0]
        except KeyError:
            pass

        try:
            extra, resolver = resolver.namespace_dict[ns]
            resolved_path.append(ns)
            ns_pattern = ns_pattern + extra
        except KeyError as key:
            if resolved_path:
                raise NoReverseMatch("%s is not a registered namespace inside '%s'" %
                    (key, ':'.join(resolved_path)))
            else:
                raise NoReverseMatch("%s is not a registered namespace" % key)
    resolver = get_ns_resolver(ns_pattern, resolver)
    return dict((name, iri_to_uri(resolver._reverse_with_prefix(name, prefix, *args, **kwargs)))
                for name in resolver.reverse_dict.keys() if isinstance(name, six.string_types))


def _get_remote_methods_for(view_object, url):
    # view_object can be a view class or instance
    result = {}
    for field in dir(view_object):
        member = getattr(view_object, field, None)
        if callable(member) and hasattr(member, 'allow_rmi'):
            config = {
                'url': url,
                'method': getattr(member, 'allow_rmi'),
                'headers': {'DjNg-Remote-Method': field},
            }
            result.update({field: config})
    return result


def get_all_remote_methods(resolver=None, ns_prefix=''):
    """
    Returns a dictionary to be used for calling ``djangoCall.configure()``, which itself extends the
    Angular API to the client, offering him to call remote methods.
    """
    if not resolver:
        resolver = get_resolver(get_urlconf())
    result = {}
    for name in resolver.reverse_dict.keys():
        if not isinstance(name, six.string_types):
            continue
        try:
            url = reverse(ns_prefix + name)
            resmgr = resolve(url)
            ViewClass = import_by_path('{0}.{1}'.format(resmgr.func.__module__, resmgr.func.__name__))
            if isclass(ViewClass) and issubclass(ViewClass, JSONResponseMixin):
                result[name] = _get_remote_methods_for(ViewClass, url)
        except (NoReverseMatch, ImproperlyConfigured):
            pass
    for namespace, ns_pattern in resolver.namespace_dict.items():
        sub_res = get_all_remote_methods(ns_pattern[1], ns_prefix + namespace + ':')
        if sub_res:
            result[namespace] = sub_res
    return result


def get_current_remote_methods(view):
    if isinstance(view, JSONResponseMixin):
        return _get_remote_methods_for(view, view.request.path_info)

########NEW FILE########
__FILENAME__ = add_placeholder
# -*- coding: utf-8 -*-
from django import forms


class AddPlaceholderFormMixin(object):
    """
    Iterate over all fields in a form and add an attribute placeholder containing the current label.
    Use this in Django-1.4, it can be removed with Django-1.5, since there fields are handled in a
    more flexible way.
    """
    def __init__(self, *args, **kwargs):
        super(AddPlaceholderFormMixin, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, (forms.widgets.TextInput, forms.widgets.PasswordInput)):
                field.widget.attrs.setdefault('placeholder', field.label)

########NEW FILE########
__FILENAME__ = angular_base
# -*- coding: utf-8 -*-
import six
from base64 import b64encode
from django.forms import forms
from django.utils.html import format_html
from django.utils.encoding import force_text
from django.utils.safestring import mark_safe, SafeData


class SafeTuple(SafeData, tuple):
    """
    Used to bypass escaping of TupleErrorList by the ``conditional_escape`` function in Django's form rendering.
    """
    pass


class TupleErrorList(list):
    """
    A list of errors, which in comparison to Django's ErrorList contains a tuple for each item.
    This tuple consists of the following fields:
    0: identifier: This is the model name of the field.
    1: property: $pristine or $dirty used by ng-show on the wrapping <ul>-element.
    2: A arbitrary property used by ng-show on the actual <li>-element.
    3: The CSS class added to the <li>-element.
    4: The used error message. If this contains the magic word '$message' it will be added with
       ``ng-bind`` rather than rendered inside the list item.
    """
    ul_format = '<ul class="djng-form-errors" ng-show="{0}.{1}" ng-cloak>{2}</ul>'
    li_format = '<li ng-show="{0}.{1}" class="{2}">{3}</li>'
    li_format_bind = '<li ng-show="{0}.{1}" class="{2}" ng-bind="{0}.{3}"></li>'

    def __str__(self):
        return self.as_ul()

    def __repr__(self):
        return repr([force_text(e[4]) for e in self])

    def as_ul(self):
        if not self:
            return ''
        pristine_list_items = []
        dirty_list_items = []
        for e in self:
            li_format = e[4] == '$message' and self.li_format_bind or self.li_format
            err_tuple = (e[0], e[2], e[3], force_text(e[4]))
            if e[1] == '$pristine':
                pristine_list_items.append(format_html(li_format, *err_tuple))
            else:
                dirty_list_items.append(format_html(li_format, *err_tuple))
        # renders and combine both of these lists
        return (pristine_list_items and
                format_html(self.ul_format, self[0][0], '$pristine', mark_safe(''.join(pristine_list_items))) or '') + \
            (dirty_list_items and
             format_html(self.ul_format, self[0][0], '$dirty', mark_safe(''.join(dirty_list_items))) or '')

    def as_text(self):
        if not self:
            return ''
        return '\n'.join(['* %s' % force_text(e[4]) for e in self if bool(e[4])])


class NgBoundField(forms.BoundField):
    @property
    def errors(self):
        """
        Returns a TupleErrorList for this field. This overloaded method adds additional error lists
        to the errors as detected by the form validator.
        """
        if not hasattr(self, '_errors_cache'):
            self._errors_cache = self.form.get_field_errors(self)
        return self._errors_cache


class NgFormBaseMixin(object):
    def __init__(self, *args, **kwargs):
        try:
            form_name = self.form_name
        except AttributeError:
            # if form_name is unset, then generate a pseudo unique name, based upon the class name
            form_name = b64encode(six.b(self.__class__.__name__)).rstrip(six.b('='))
        self.form_name = kwargs.pop('form_name', form_name)
        error_class = kwargs.pop('error_class', TupleErrorList)
        kwargs.setdefault('error_class', error_class)
        super(NgFormBaseMixin, self).__init__(*args, **kwargs)

    def __getitem__(self, name):
        "Returns a NgBoundField with the given name."
        try:
            field = self.fields[name]
        except KeyError:
            raise KeyError('Key %r not found in Form' % name)
        return NgBoundField(self, field, name)

    def add_prefix(self, field_name):
        """
        Rewrite the model keys to use dots instead of dashes, since thats the syntax
        used in Angular models.
        """
        return self.prefix and ('%s.%s' % (self.prefix, field_name)) or field_name

    def get_field_errors(self, field):
        """
        Return server side errors. Shall be overridden by derived forms to add their extra errors for AngularJS.
        """
        identifier = format_html('{0}.{1}', self.form_name, field.name)
        return self.error_class([SafeTuple((identifier, '$pristine', '$pristine', 'invalid', e))
                         for e in self.errors.get(field.name, [])])

    def non_field_errors(self):
        errors = super(NgFormBaseMixin, self).non_field_errors()
        return self.error_class([SafeTuple((self.form_name, '$pristine', '$pristine', 'invalid', e))
                         for e in errors])

########NEW FILE########
__FILENAME__ = angular_model
# -*- coding: utf-8 -*-
from django.forms.util import ErrorDict
from django.utils.html import format_html
from django.http import QueryDict
from djangular.forms.angular_base import NgFormBaseMixin, SafeTuple


class NgModelFormMixin(NgFormBaseMixin):
    """
    Add this NgModelFormMixin to every class derived from forms.Form, if
    you want to manage that form through an Angular controller.
    It adds attributes ng-model, and optionally ng-change, ng-class and ng-style
    to each of your input fields.
    If form validation fails, the ErrorDict is rewritten in a way, so that the
    Angular controller can access the error strings using the same key values as
    for its models.
    """

    def __init__(self, data=None, *args, **kwargs):
        self.scope_prefix = kwargs.pop('scope_prefix', getattr(self, 'scope_prefix', None))
        if hasattr(self, 'Meta') and hasattr(self.Meta, 'ng_models'):
            if not isinstance(self.Meta.ng_models, list):
                raise TypeError('Meta.ng_model is not of type list')
            ng_models = self.Meta.ng_models
        else:
            ng_models = None
        directives = {}
        for key in list(kwargs.keys()):
            if key.startswith('ng_'):
                fmtstr = kwargs.pop(key)
                directives[key.replace('_', '-')] = fmtstr
        if ng_models is None and 'ng-model' not in directives:
            directives['ng-model'] = '%(model)s'
        self.prefix = kwargs.get('prefix')
        if self.prefix and data:
            data = dict((self.add_prefix(name), value) for name, value in data.get(self.prefix).items())
        for name, field in self.base_fields.items():
            identifier = self.add_prefix(name)
            ng = {
                'name': name,
                'identifier': identifier,
                'model': self.scope_prefix and ('%s.%s' % (self.scope_prefix, identifier)) or identifier
            }
            if ng_models and name in ng_models:
                field.widget.attrs['ng-model'] = ng['model']
            for key, fmtstr in directives.items():
                field.widget.attrs[key] = fmtstr % ng
            try:
                if isinstance(data, QueryDict):
                    data = field.implode_multi_values(name, data.copy())
            except AttributeError:
                pass
        super(NgModelFormMixin, self).__init__(data, *args, **kwargs)
        if self.scope_prefix == self.form_name:
            raise ValueError("The form's name may not be identical with its scope_prefix")

    def _post_clean(self):
        """
        Rewrite the error dictionary, so that its keys correspond to the model fields.
        """
        super(NgModelFormMixin, self)._post_clean()
        if self._errors and self.prefix:
            self._errors = ErrorDict((self.add_prefix(name), value) for name, value in self._errors.items())

    def get_initial_data(self):
        """
        Return a dictionary specifying the defaults for this form. This dictionary
        shall be used to inject the initial values for an Angular controller using
        the directive 'ng-init={{thisform.get_initial_data|js|safe}}'.
        """
        data = {}
        for name, field in self.fields.items():
            if hasattr(field, 'widget') and 'ng-model' in field.widget.attrs:
                data[name] = self.initial and self.initial.get(name) or field.initial
        return data

    def get_field_errors(self, field):
        errors = super(NgModelFormMixin, self).get_field_errors(field)
        identifier = format_html('{0}.{1}', self.form_name, field.name)
        errors.append(SafeTuple((identifier, '$pristine', '$message', 'invalid', '$message')))
        return errors

    def non_field_errors(self):
        errors = super(NgModelFormMixin, self).non_field_errors()
        errors.append(SafeTuple((self.form_name, '$pristine', '$message', 'invalid', '$message')))
        return errors

########NEW FILE########
__FILENAME__ = angular_validation
# -*- coding: utf-8 -*-
import types
from django.conf import settings
from django.utils.importlib import import_module
from django.utils.html import format_html
from django.utils.encoding import force_text
from djangular.forms.angular_base import NgFormBaseMixin, SafeTuple

VALIDATION_MAPPING_MODULE = import_module(getattr(settings, 'DJANGULAR_VALIDATION_MAPPING_MODULE', 'djangular.forms.patched_fields'))


class NgFormValidationMixin(NgFormBaseMixin):
    """
    Add this NgFormValidationMixin to every class derived from forms.Form, which shall be
    auto validated using the Angular's validation mechanism.
    """
    def __init__(self, *args, **kwargs):
        super(NgFormValidationMixin, self).__init__(*args, **kwargs)
        for name, field in self.fields.items():
            # add ng-model to each model field
            ng_model = self.add_prefix(name)
            field.widget.attrs.setdefault('ng-model', ng_model)

    def get_field_errors(self, bound_field):
        """
        Determine the kind of input field and create a list of potential errors which may occur
        during validation of that field. This list is returned to be displayed in '$dirty' state
        if the field does not validate for that criteria.
        """
        errors = super(NgFormValidationMixin, self).get_field_errors(bound_field)
        identifier = format_html('{0}.{1}', self.form_name, self.add_prefix(bound_field.name))
        errors_function = '{0}_angular_errors'.format(bound_field.field.__class__.__name__)
        try:
            errors_function = getattr(VALIDATION_MAPPING_MODULE, errors_function)
            potential_errors = types.MethodType(errors_function, bound_field.field)()
        except (TypeError, AttributeError):
            errors_function = getattr(VALIDATION_MAPPING_MODULE, 'Default_angular_errors')
            potential_errors = types.MethodType(errors_function, bound_field.field)()
        errors.append(SafeTuple((identifier, '$dirty', '$valid', 'valid', '')))  # for valid fields
        errors.extend([SafeTuple((identifier, '$dirty', pe[0], 'invalid', force_text(pe[1])))
                       for pe in potential_errors])
        return errors

########NEW FILE########
__FILENAME__ = fields
# -*- coding: utf-8 -*-
from django import forms
from django.utils.html import format_html
from django.forms.util import flatatt
from django.forms.widgets import (RendererMixin, ChoiceFieldRenderer, CheckboxChoiceInput,
                                  SelectMultiple)


class DjngCheckboxChoiceInput(CheckboxChoiceInput):
    def tag(self):
        if 'id' in self.attrs:
            self.attrs['id'] = '%s_%s' % (self.attrs['id'], self.index)
        self.attrs['ng-model'] = '%s.%s' % (self.attrs['ng-model'], self.choice_value)
        name = '%s.%s' % (self.name, self.choice_value)
        final_attrs = dict(self.attrs, type=self.input_type, name=name, value=self.choice_value)
        if self.is_checked():
            final_attrs['checked'] = 'checked'
        return format_html('<input{0} />', flatatt(final_attrs))


class DjngCheckboxFieldRenderer(ChoiceFieldRenderer):
    choice_input_class = DjngCheckboxChoiceInput


class DjngCheckboxSelectMultiple(RendererMixin, SelectMultiple):
    renderer = DjngCheckboxFieldRenderer
    _empty_value = []


class DjngMultipleCheckboxField(forms.MultipleChoiceField):
    widget = DjngCheckboxSelectMultiple

    def implode_multi_values(self, name, data):
        mkeys = [k for k in data.keys() if k.startswith(name + '.')]
        mvls = [data.pop(k)[0] for k in mkeys]
        if mvls:
            data.setlist(name, mvls)
        return data

########NEW FILE########
__FILENAME__ = patched_fields
# -*- coding: utf-8 -*-
"""
Class methods to be added to form fields such as django.forms.fields. These methods add additional
error messages for AngularJS form validation.
"""
from django.utils.translation import gettext_lazy, ungettext_lazy


def _input_required(field):
    field.widget.attrs['ng-required'] = str(field.required).lower()
    errors = []
    for key, msg in field.error_messages.items():
        if key == 'required':
            errors.append(('$error.required', msg))
    return errors


def _min_max_length_errors(field):
    errors = []
    if hasattr(field, 'min_length') and field.min_length > 0:
        field.widget.attrs['ng-minlength'] = field.min_length
    if hasattr(field, 'max_length') and field.max_length > 0:
        field.widget.attrs['ng-maxlength'] = field.max_length
    for item in field.validators:
        if getattr(item, 'code', None) == 'min_length':
            message = ungettext_lazy(
                'Ensure this value has at least %(limit_value)d character',
                'Ensure this value has at least %(limit_value)d characters')
            errors.append(('$error.minlength', message % {'limit_value': field.min_length}))
        if getattr(item, 'code', None) == 'max_length':
            message = ungettext_lazy(
                'Ensure this value has at most %(limit_value)d character',
                'Ensure this value has at most %(limit_value)d characters')
            errors.append(('$error.maxlength', message % {'limit_value': field.max_length}))
    return errors


def _min_max_value_errors(field):
    errors = []
    if isinstance(getattr(field, 'min_value', None), int):
        field.widget.attrs['min'] = field.min_value
    if isinstance(getattr(field, 'max_value', None), int):
        field.widget.attrs['max'] = field.max_value
    errkeys = []
    for key, msg in field.error_messages.items():
        if key == 'min_value':
            errors.append(('$error.min', msg))
            errkeys.append(key)
        if key == 'max_value':
            errors.append(('$error.max', msg))
            errkeys.append(key)
    for item in field.validators:
        if getattr(item, 'code', None) == 'min_value' and 'min_value' not in errkeys:
            errors.append(('$error.min', item.message % {'limit_value': field.min_value}))
            errkeys.append('min_value')
        if getattr(item, 'code', None) == 'max_value' and 'max_value' not in errkeys:
            errors.append(('$error.max', item.message % {'limit_value': field.max_value}))
            errkeys.append('max_value')
    return errors


def _invalid_value_errors(field, ng_error_key):
    errors = []
    errkeys = []
    for key, msg in field.error_messages.items():
        if key == 'invalid':
            errors.append(('$error.{0}'.format(ng_error_key), msg))
            errkeys.append(key)
    for item in field.validators:
        if getattr(item, 'code', None) == 'invalid' and 'invalid' not in errkeys:
            errmsg = getattr(item, 'message', gettext_lazy('This input field does not contain valid data.'))
            errors.append(('$error.{0}'.format(ng_error_key), errmsg))
            errkeys.append('invalid')
    return errors


def DecimalField_angular_errors(field):
    errors = _input_required(field)
    field.widget.attrs['ng-minlength'] = 1
    if hasattr(field, 'max_digits') and field.max_digits > 0:
        field.widget.attrs['ng-maxlength'] = field.max_digits + 1
    errors.extend(_min_max_value_errors(field))
    return errors


def CharField_angular_errors(field):
    errors = _input_required(field)
    errors.extend(_min_max_length_errors(field))
    return errors


def EmailField_angular_errors(field):
    errors = _input_required(field)
    errors.extend(_invalid_value_errors(field, 'email'))
    return errors


def DateField_angular_errors(field):
    errors = _input_required(field)
    errors.extend(_invalid_value_errors(field, 'date'))
    return errors


def FloatField_angular_errors(field):
    errors = _input_required(field)
    errors.extend(_min_max_value_errors(field))
    return errors


def IntegerField_angular_errors(field):
    errors = _input_required(field)
    errors.extend(_min_max_value_errors(field))
    return errors


def SlugField_angular_errors(field):
    errors = _input_required(field)
    return errors


def RegexField_angular_errors(field):
    # Probably Python Regex can't be translated 1:1 into JS regex. Any hints on how to convert these?
    field.widget.attrs['ng-pattern'] = '/{0}/'.format(field.regex.pattern)
    errors = _input_required(field)
    errors.extend(_min_max_length_errors(field))
    errors.extend(_invalid_value_errors(field, 'pattern'))
    return errors


def Default_angular_errors(field):
    errors = _input_required(field)
    return errors

########NEW FILE########
__FILENAME__ = models
# Django needs this to see it as a project

########NEW FILE########
__FILENAME__ = djangular_tags
# -*- coding: utf-8 -*-
import json
from django.template import Library
from django.template.base import Node
from django.core.exceptions import ImproperlyConfigured
from django.utils.safestring import mark_safe
from djangular.core.urlresolvers import get_all_remote_methods, get_current_remote_methods
register = Library()


class CsrfValueNode(Node):
    def render(self, context):
        csrf_token = context.get('csrf_token', None)
        if not csrf_token:
            raise ImproperlyConfigured('Template must be rendered using a RequestContext')
        if csrf_token == 'NOTPROVIDED':
            return mark_safe('')
        else:
            return mark_safe(csrf_token)


@register.tag(name='csrf_value')
def render_csrf_value(parser, token):
    return CsrfValueNode()


@register.simple_tag(name='djng_all_rmi')
def djng_all_rmi():
    """
    Returns a dictionary of all methods for all Views available for this project, marked with the
    ``@allow_remote_invocation`` decorator. The return string can be used directly to initialize
    the AngularJS provider, such as ``djangoRMIProvider.configure({­% djng_rmi_configs %­});``
    """
    return mark_safe(json.dumps(get_all_remote_methods()))


@register.simple_tag(name='djng_current_rmi', takes_context=True)
def djng_current_rmi(context):
    """
    Returns a dictionary of all methods for the current View of this request, marked with the
    @allow_remote_invocation decorator. The return string can be used directly to initialize
    the AngularJS provider, such as ``djangoRMIProvider.configure({­% djng_current_rmi %­});``
    """
    return mark_safe(json.dumps(get_current_remote_methods(context['view'])))

########NEW FILE########
__FILENAME__ = crud
# -*- coding: utf-8 -*-
import json

from django.core.exceptions import ValidationError
from django.core import serializers
from django.forms.models import modelform_factory
from django.views.generic import FormView

from djangular.views.mixins import JSONBaseMixin, JSONResponseException


class NgMissingParameterError(ValueError):
    pass


class NgCRUDView(JSONBaseMixin, FormView):
    """
    Basic view to support default angular $resource CRUD actions on server side
    Subclass and override ``model`` with your model

    Optional 'pk' GET parameter must be passed when object identification is required (save to update and delete)

    If fields != None the serialized data will only contain field names from fields array
    """
    model = None
    fields = None
    slug_field = 'slug'
    serialize_natural_keys = False

    def dispatch(self, request, *args, **kwargs):
        """
        Override dispatch to call appropriate methods:
        * $query - ng_query
        * $get - ng_get
        * $save - ng_save
        * $delete and $remove - ng_delete
        """
        try:
            if request.method == 'GET':
                if 'pk' in request.GET or self.slug_field in request.GET:
                    return self.ng_get(request, *args, **kwargs)
                return self.ng_query(request, *args, **kwargs)
            elif request.method == 'POST':
                return self.ng_save(request, *args, **kwargs)
            elif request.method == 'DELETE':
                return self.ng_delete(request, *args, **kwargs)
        except self.model.DoesNotExist as e:
            return self.error_json_response(e.args[0], 404)
        except NgMissingParameterError as e:
            return self.error_json_response(e.args[0])
        except JSONResponseException as e:
            return self.error_json_response(e.args[0], e.status_code)
        except ValidationError as e:
            if hasattr(e, 'error_dict'):
                return self.error_json_response('Form not valid', detail=e.message_dict)
            else:
                return self.error_json_response(e.message)

        return self.error_json_response('This view can not handle method {0}'.format(request.method), 405)

    def get_form_class(self):
        """
        Build ModelForm from model
        """
        return modelform_factory(self.model)

    def build_json_response(self, data, **kwargs):
        return self.json_response(self.serialize_to_json(data), separators=(',', ':'), **kwargs)

    def error_json_response(self, message, status_code=400, detail=None):
        response_data = {
            "message": message,
            "detail": detail,
        }
        return self.json_response(response_data, status=status_code, separators=(',', ':'))

    def serialize_to_json(self, queryset):
        """
        Return JSON serialized data
        serialize() only works on iterables, so to serialize a single object we put it in a list
        """
        object_data = []
        is_queryset = False
        query_fields = self.get_fields()
        try:
            iter(queryset)
            is_queryset = True
            raw_data = serializers.serialize('python', queryset, fields=query_fields, use_natural_keys=self.serialize_natural_keys)
        except TypeError:  # Not iterable
            raw_data = serializers.serialize('python', [queryset, ], fields=query_fields, use_natural_keys=self.serialize_natural_keys)

        for obj in raw_data:  # Add pk to fields
            obj['fields']['pk'] = obj['pk']
            object_data.append(obj['fields'])

        if is_queryset:
            return object_data
        return object_data[0]  # If there's only one object

    def get_form_kwargs(self):
        kwargs = super(NgCRUDView, self).get_form_kwargs()
        # Since angular sends data in JSON rather than as POST parameters, the default data (request.POST)
        # is replaced with request.body that contains JSON encoded data
        kwargs['data'] = json.loads(self.request.body.decode('utf-8'))
        if 'pk' in self.request.GET or self.slug_field in self.request.GET:
            kwargs['instance'] = self.get_object()
        return kwargs

    def get_object(self):
        if 'pk' in self.request.GET:
            return self.model.objects.get(pk=self.request.GET['pk'])
        elif self.slug_field in self.request.GET:
            return self.model.objects.get(**{self.slug_field: self.request.GET[self.slug_field]})
        raise NgMissingParameterError("Attempted to get an object by 'pk' or slug field, but no identifier is present. Missing GET parameter?")

    def get_fields(self):
        """
        Get fields to return from a query.
        Can be overridden (e.g. to use a query parameter).
        """
        return self.fields

    def get_queryset(self):
        """
        Get query to use in ng_query
        Allows for easier overriding
        """
        return self.model.objects.all()

    def ng_query(self, request, *args, **kwargs):
        """
        Used when angular's query() method is called
        Build an array of all objects, return json response
        """
        return self.build_json_response(self.get_queryset())

    def ng_get(self, request, *args, **kwargs):
        """
        Used when angular's get() method is called
        Returns a JSON response of a single object dictionary
        """
        return self.build_json_response(self.get_object())

    def ng_save(self, request, *args, **kwargs):
        """
        Called on $save()
        Use modelform to save new object or modify an existing one
        """
        form = self.get_form(self.get_form_class())
        if form.is_valid():
            obj = form.save()
            return self.build_json_response(obj)

        raise ValidationError(form.errors)

    def ng_delete(self, request, *args, **kwargs):
        """
        Delete object and return it's data in JSON encoding
        """
        if 'pk' not in request.GET:
            raise NgMissingParameterError("Object id is required to delete.")

        obj = self.get_object()
        obj.delete()
        return self.build_json_response(obj)

########NEW FILE########
__FILENAME__ = mixins
# -*- coding: utf-8 -*-
import json
import warnings
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden


def allow_remote_invocation(func, method='auto'):
    """
    All methods which shall be callable through a given Ajax 'action' must be
    decorated with @allowed_action. This is required for safety reasons. It
    inhibits the caller to invoke all available methods of a class.
    """
    setattr(func, 'allow_rmi', method)
    return func


def allowed_action(func):
    warnings.warn("Decorator `@allowed_action` is deprecated. Use `@allow_remote_invocation` instead.", DeprecationWarning)
    return allow_remote_invocation(func)


class JSONResponseException(Exception):
    """
    Exception class for triggering HTTP 4XX responses with JSON content, where expected.
    """
    status_code = 400

    def __init__(self, message=None, status=None, *args, **kwargs):
        if status is not None:
            self.status_code = status
        super(JSONResponseException, self).__init__(message, *args, **kwargs)


class JSONBaseMixin(object):
    """
    Basic mixin for encoding HTTP responses in JSON format.
    """
    json_content_type = 'application/json;charset=UTF-8'

    def json_response(self, response_data, status=200, **kwargs):
        out_data = json.dumps(response_data, cls=DjangoJSONEncoder, **kwargs)
        response = HttpResponse(out_data, self.json_content_type, status=status)
        response['Cache-Control'] = 'no-cache'
        return response


class JSONResponseMixin(JSONBaseMixin):
    """
    A mixin for View classes that dispatches requests containing the private HTTP header
    ``DjNg-Remote-Method`` onto a method of an instance of this class, with the given method name.
    This named method must be decorated with ``@allow_remote_invocation`` and shall return a
    list or dictionary which is serializable to JSON.
    The returned HTTP responses are of kind ``application/json;charset=UTF-8``.
    """
    def get(self, request, *args, **kwargs):
        if not request.is_ajax():
            return self._dispatch_super(request, *args, **kwargs)
        if 'action' in kwargs:
            warnings.warn("Using the keyword 'action' in URLresolvers is deprecated. Please use 'invoke_method' instead", DeprecationWarning)
            remote_method = kwargs['action']
        else:
            remote_method = kwargs.get('invoke_method')
        if remote_method:
            # method for invocation is determined programmatically
            handler = getattr(self, remote_method)
        else:
            # method for invocation is determined by HTTP header
            remote_method = request.META.get('HTTP_DJNG_REMOTE_METHOD')
            handler = remote_method and getattr(self, remote_method, None)
            if not callable(handler):
                return self._dispatch_super(request, *args, **kwargs)
            if not hasattr(handler, 'allow_rmi'):
                return HttpResponseForbidden("Method '{0}.{1}' has no decorator '@allow_remote_invocation'"
                                             .format(self.__class__.__name__, remote_method))
        try:
            response_data = handler()
        except JSONResponseException as e:
            return self.json_response({'message': e.args[0]}, e.status_code)
        return self.json_response(response_data)

    def post(self, request, *args, **kwargs):
        if not request.is_ajax():
            return self._dispatch_super(request, *args, **kwargs)
        try:
            in_data = json.loads(request.body.decode('utf-8'))
        except ValueError:
            in_data = request.body.decode('utf-8')
        if 'action' in in_data:
            warnings.warn("Using the keyword 'action' inside the payload is deprecated. Please use 'djangoRMI' from module 'ng.django.forms'", DeprecationWarning)
            remote_method = in_data.pop('action')
        else:
            remote_method = request.META.get('HTTP_DJNG_REMOTE_METHOD')
        handler = remote_method and getattr(self, remote_method, None)
        if not callable(handler):
            return self._dispatch_super(request, *args, **kwargs)
        if not hasattr(handler, 'allow_rmi'):
            return HttpResponseForbidden("Method '{0}.{1}' has no decorator '@allow_remote_invocation'"
                                         .format(self.__class__.__name__, remote_method), 403)
        try:
            response_data = handler(in_data)
        except JSONResponseException as e:
            return self.json_response({'message': e.args[0]}, e.status_code)
        return self.json_response(response_data)

    def _dispatch_super(self, request, *args, **kwargs):
        base = super(JSONResponseMixin, self)
        handler = getattr(base, request.method.lower(), None)
        if callable(handler):
            return handler(request, *args, **kwargs)
        # HttpResponseNotAllowed expects permitted methods.
        return HttpResponseBadRequest('This view can not handle method {0}'.format(request.method), status=405)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-angular documentation build configuration file, created by
# sphinx-quickstart on Sun Jun 23 09:19:57 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import os
import sys
import datetime

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))
from djangular import __version__

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
project = u'django-angular'
copyright = datetime.date.today().strftime(u'Copyright %Y, Jacob Rief')

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = __version__
# The full version, including alpha/beta/rc tags.
release = __version__

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
htmlhelp_basename = 'django-angulardoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-angular.tex', u'django-angular Documentation',
   u'Jacob Rief', 'manual'),
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

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'django-angular', u'django-angular Documentation',
     [u'Jacob Rief'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'django-angular', u'django-angular Documentation',
   u'Jacob Rief', 'django-angular', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

sys.path[0:0] = [os.path.abspath('..'), os.path.abspath('../../django-websocket-redis/')]

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from djangular.forms import NgFormValidationMixin, NgModelFormMixin
from djangular.forms.fields import DjngMultipleCheckboxField


def reject_addresses(value):
    try:
        value.lower().index('@example.')
        raise ValidationError(u'Email address \'{0}\' is rejected by the server.'.format(value))
    except ValueError:
        pass


class SubscriptionForm(forms.Form):
    CONTINENT_CHOICES = (('am', 'America'), ('eu', 'Europe'), ('as', 'Asia'), ('af', 'Africa'),
                         ('au', 'Australia'), ('oc', 'Oceania'), ('an', 'Antartica'),)
    TRAVELLING_BY = (('foot', 'Foot'), ('bike', 'Bike'), ('mc', 'Motorcycle'), ('car', 'Car'),
        ('bus', 'Bus'), ('taxi', 'Taxi'), ('tram', 'Tram'), ('subway', 'Subway'), ('train', 'Train'),
        ('boat', 'Boat'), ('funicular', 'Funicular'), ('air', 'Airplane'),)
    NOTIFY_BY = (('email', 'EMail'), ('phone', 'Phone'), ('sms', 'SMS'), ('postal', 'Postcard'),)

    first_name = forms.CharField(label='First name', min_length=3, max_length=20)
    last_name = forms.RegexField(r'^[A-Z][a-z -]?', label='Last name',
        error_messages={'invalid': 'Last names shall start in upper case'},
        help_text=u'The name ‘John Doe’ is rejected by the server.')
    sex = forms.ChoiceField(choices=(('m', 'Male'), ('f', 'Female')),
         widget=forms.RadioSelect,
         error_messages={'invalid_choice': 'Please select your sex'})
    email = forms.EmailField(label='E-Mail', validators=[reject_addresses, validate_email],
        help_text=u'Addresses containing ‘@example’ are rejected by the server.')
    subscribe = forms.BooleanField(initial=False, label='Subscribe Newsletter', required=False)
    phone = forms.RegexField(r'^\+?[0-9 .-]{4,25}$', label='Phone number',
        error_messages={'invalid': 'Phone number have 4-25 digits and may start with +'})
    birth_date = forms.DateField(label='Date of birth',
        widget=forms.DateInput(attrs={'validate-date': '^(\d{4})-(\d{1,2})-(\d{1,2})$'}),
        help_text=u'Allowed date format: yyyy-mm-dd.')
    continent = forms.ChoiceField(choices=CONTINENT_CHOICES, label='Living on continent',
         error_messages={'invalid_choice': 'Please select your continent'})
    weight = forms.IntegerField(min_value=42, max_value=95, label='Weight in kg',
        error_messages={'min_value': 'You are too lightweight'})
    height = forms.FloatField(min_value=1.48, max_value=1.95, label='Height in meters',
        error_messages={'max_value': 'You are too tall'})
    traveling = forms.MultipleChoiceField(choices=TRAVELLING_BY, label='Traveling by')
    notifyme = DjngMultipleCheckboxField(choices=NOTIFY_BY, label='Notify by')
    annotation = forms.CharField(required=False, label='Annotation',
        widget=forms.Textarea(attrs={'cols': '80', 'rows': '3'}))

    def clean(self):
        if self.cleaned_data.get('first_name') == 'John' and self.cleaned_data.get('last_name') == 'Doe':
            raise ValidationError(u'The full name \'John Doe\' is rejected by the server.')
        return super(SubscriptionForm, self).clean()


class SubscriptionFormWithNgValidation(NgFormValidationMixin, SubscriptionForm):
    form_name = 'valid_form'
    pass


class SubscriptionFormWithNgModel(NgModelFormMixin, SubscriptionForm):
    form_name = 'valid_form'
    scope_prefix = 'subscribe_data'


class SubscriptionFormWithNgValidationAndModel(NgModelFormMixin, NgFormValidationMixin, SubscriptionForm):
    form_name = 'valid_form'
    scope_prefix = 'subscribe_data'

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
import datetime
from django.db import models


class DummyModel(models.Model):
    name = models.CharField(max_length=255)
    model2 = models.ForeignKey('DummyModel2')
    timefield = models.DateTimeField(default=datetime.datetime.now)


class DummyModel2(models.Model):
    name = models.CharField(max_length=255)


class SimpleModel(models.Model):
    name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)

########NEW FILE########
__FILENAME__ = settings
# Django settings for unit test project.
import os

DEBUG = True

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'test.sqlite',
    },
}

SITE_ID = 1

ROOT_URLCONF = 'server.urls'

SECRET_KEY = 'secret'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'django.contrib.staticfiles',
    'djangular',
    'server',
)

USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory that holds static files.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.environ.get('DJANGO_STATIC_ROOT', '')

# URL that handles the static files served from STATIC_ROOT.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'client', 'src'),
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.tz',
    'django.core.context_processors.request',
    'django.contrib.messages.context_processors.messages',
)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

TIME_ZONE = 'Europe/Berlin'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '[%(asctime)s %(module)s] %(levelname)s: %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# if package django-websocket-redis is installed, some more tests can be be added
try:
    import ws4redis

    INSTALLED_APPS += ('ws4redis',)

    TEMPLATE_CONTEXT_PROCESSORS += ('ws4redis.context_processors.default',)

    # This setting is required to override the Django's main loop, when running in
    # development mode, such as ./manage runserver
    WSGI_APPLICATION = 'ws4redis.django_runserver.application'

    # URL that distinguishes websocket connections from normal requests
    WEBSOCKET_URL = '/ws/'

    # Set the number of seconds each message shall persited
    WS4REDIS_EXPIRE = 3600

    WS4REDIS_HEARTBEAT = '--heartbeat--'

    WS4REDIS_PREFIX = 'djangular'

except ImportError:
    pass

########NEW FILE########
__FILENAME__ = active
from django import template
from django.core.urlresolvers import reverse

register = template.Library()


@register.simple_tag
def active(request, url):
    if request.path.startswith(reverse(url)):
        return 'active'
    return ''

########NEW FILE########
__FILENAME__ = test_crud
# -*- coding: utf-8 -*-
import json

from django.test import TestCase
from django.test.client import RequestFactory

from djangular.views.crud import NgCRUDView
from djangular.views.mixins import JSONResponseMixin
from server.models import DummyModel, DummyModel2, SimpleModel


class CRUDTestViewWithFK(JSONResponseMixin, NgCRUDView):
    """
    Include JSONResponseMixin to make sure there aren't any problems when using both together
    """
    model = DummyModel


class CRUDTestView(JSONResponseMixin, NgCRUDView):
    """
    Include JSONResponseMixin to make sure there aren't any problems when using both together
    """
    model = DummyModel2


class CRUDTestViewWithSlug(NgCRUDView):
    """
    Differs from CRUDTestViewWithFK in slug field 'email', which has a 'unique' constraint and
    can be used as an alternative key (for GET operations only).
    """
    model = SimpleModel
    slug_field = 'email'


class CRUDViewTest(TestCase):
    names = ['John', 'Anne', 'Chris', 'Beatrice', 'Matt']
    emails = ["@".join((name, "example.com")) for name in names]

    def setUp(self):
        self.factory = RequestFactory()

        # DummyModel2 and DummyModel / CRUDTestViewWithFK
        model2 = DummyModel2(name="Model2 name")
        model2.save()
        for name in self.names:
            DummyModel(name=name, model2=model2).save()

        # SimpleModel / CRUDTestViewWithSlug
        for name, email in zip(self.names, self.emails):
            SimpleModel(name=name, email=email).save()

    def test_ng_query(self):
        # CRUDTestViewWithFK
        request = self.factory.get('/crud/')
        response = CRUDTestViewWithFK.as_view()(request)
        data = json.loads(response.content.decode('utf-8'))
        for obj in data:
            db_obj = DummyModel.objects.get(pk=obj['pk'])
            self.assertEqual(obj['name'], db_obj.name)

        # CRUDTestViewWithSlug
        request2 = self.factory.get('/crud/')
        response2 = CRUDTestViewWithSlug.as_view()(request2)
        data2 = json.loads(response2.content.decode('utf-8'))
        for obj in data2:
            db_obj = SimpleModel.objects.get(email=obj['email'])
            self.assertEqual(obj['name'], db_obj.name)

    def test_ng_get(self):
        # CRUDTestViewWithFK
        request = self.factory.get('/crud/?pk=1')
        response = CRUDTestViewWithFK.as_view()(request)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(self.names[0], data['name'])

        # CRUDTestViewWithSlug
        request2 = self.factory.get('/crud/?email={0}'.format(self.emails[0]))
        response2 = CRUDTestViewWithSlug.as_view()(request2)
        data2 = json.loads(response2.content.decode('utf-8'))
        self.assertEqual(self.names[0], data2['name'])

    def test_ng_save_create(self):
        # CRUDTestViewWithFK
        request = self.factory.post('/crud/',
                                    data=json.dumps({'name': 'Leonard'}),
                                    content_type='application/json')
        response = CRUDTestView.as_view()(request)
        data = json.loads(response.content.decode('utf-8'))
        pk = data['pk']

        request2 = self.factory.get('/crud/?pk={0}'.format(pk))
        response2 = CRUDTestView.as_view()(request2)
        data2 = json.loads(response2.content.decode('utf-8'))
        self.assertEqual(data2['name'], 'Leonard')

        # CRUDTestViewWithSlug
        request3 = self.factory.post('/crud/',
                                    data=json.dumps({'name': 'Leonard', 'email': 'Leonard@example.com'}),
                                    content_type='application/json')
        CRUDTestViewWithSlug.as_view()(request3)

        request4 = self.factory.get('/crud/?email={0}'.format('Leonard@example.com'))
        response4 = CRUDTestViewWithSlug.as_view()(request4)
        data4 = json.loads(response4.content.decode('utf-8'))
        self.assertEqual(data4['name'], 'Leonard')

        request5 = self.factory.post('/crud/',
                                    data=json.dumps({'name': 'Leonard2', 'email': 'Leonard@example.com'}),
                                    content_type='application/json')
        response5 = CRUDTestViewWithSlug.as_view()(request5)
        self.assertGreaterEqual(response5.status_code, 400)
        data5 = json.loads(response5.content.decode('utf-8'))
        self.assertTrue('detail' in data5 and 'email' in data5['detail'] and len(data5['detail']['email']) > 0)

    def test_ng_save_update(self):
        # CRUDTestViewWithFK
        request = self.factory.post('/crud/?pk=1',
                                    data=json.dumps({'pk': 1, 'name': 'John2'}),
                                    content_type='application/json')
        response = CRUDTestView.as_view()(request)
        data = json.loads(response.content.decode('utf-8'))
        self.assertEqual(data['name'], 'John2')

        request2 = self.factory.get('/crud/?pk=1')
        response2 = CRUDTestView.as_view()(request2)
        data2 = json.loads(response2.content.decode('utf-8'))
        self.assertEqual(data2['name'], 'John2')

        # CRUDTestViewWithSlug
        request3 = self.factory.post('/crud/?pk=1',
                                    data=json.dumps({'name': 'John', 'email': 'John2@example.com'}),
                                    content_type='application/json')
        response3 = CRUDTestViewWithSlug.as_view()(request3)
        data3 = json.loads(response3.content.decode('utf-8'))
        self.assertEqual(data3['name'], 'John')
        self.assertEqual(data3['email'], 'John2@example.com')

        request4 = self.factory.get('/crud/?email=John2@example.com')
        response4 = CRUDTestViewWithSlug.as_view()(request4)
        data4 = json.loads(response4.content.decode('utf-8'))
        self.assertEqual(data4['name'], 'John')

        request5 = self.factory.post('/crud/?pk=3',  # Modifying "Chris"
                                    data=json.dumps({'pk': 4, 'name': 'John2', 'email': 'John2@example.com'}),
                                    content_type='application/json')
        response5 = CRUDTestViewWithSlug.as_view()(request5)
        self.assertGreaterEqual(response5.status_code, 400)
        data5 = json.loads(response5.content.decode('utf-8'))
        self.assertTrue('detail' in data5 and 'email' in data5['detail'] and len(data5['detail']['email']) > 0)

    def test_ng_delete(self):
        # CRUDTestViewWithFK
        request = self.factory.delete('/crud/?pk=1')
        response = CRUDTestViewWithFK.as_view()(request)
        data = json.loads(response.content.decode('utf-8'))
        deleted_name = data['name']

        request2 = self.factory.get('/crud/')
        response2 = CRUDTestViewWithFK.as_view()(request2)
        data2 = json.loads(response2.content.decode('utf-8'))
        for obj in data2:
            self.assertTrue(deleted_name != obj['name'])

        # CRUDTestViewWithSlug delete is not different from CRUDTestViewWithFK only testing error status codes
        request5 = self.factory.delete('/crud/?email=Anne@example.com')  # Missing pk
        response5 = CRUDTestViewWithSlug.as_view()(request5)
        self.assertEqual(response5.status_code, 400)

        request6 = self.factory.delete('/crud/?pk=100')  # Invalid pk
        response6 = CRUDTestViewWithSlug.as_view()(request6)
        self.assertEqual(response6.status_code, 404)

########NEW FILE########
__FILENAME__ = test_forms
# -*- coding: utf-8 -*-
import copy
from django.db import models
from django import forms
from django.test import TestCase
from djangular.forms import NgModelFormMixin, AddPlaceholderFormMixin
from pyquery.pyquery import PyQuery
from lxml import html


CHOICES = (('a', 'Choice A'), ('b', 'Choice B'), ('c', 'Choice C'))


class SubModel(models.Model):
    select_choices = models.CharField(max_length=1, choices=CHOICES, default=CHOICES[0][0])
    radio_choices = models.CharField(max_length=1, choices=CHOICES, default=CHOICES[1][0])
    first_name = models.CharField(max_length=40, blank=True)


class SubForm1(NgModelFormMixin, forms.ModelForm):
    class Meta:
        model = SubModel
        widgets = {'radio_choices': forms.RadioSelect()}


class SubForm2(NgModelFormMixin, forms.ModelForm):
    class Meta:
        model = SubModel
        widgets = {'radio_choices': forms.RadioSelect()}
        ng_models = ['select_choices', 'first_name']


class InvalidForm(NgModelFormMixin, forms.ModelForm):
    class Meta:
        model = SubModel
        ng_models = {}


class DummyForm(NgModelFormMixin, forms.Form):
    email = forms.EmailField(label='E-Mail')
    onoff = forms.BooleanField(initial=False, required=True)
    scope_prefix = 'dataroot'

    def __init__(self, *args, **kwargs):
        kwargs.update(auto_id=False, ng_class='fieldClass(\'%(identifier)s\')',
                      scope_prefix=self.scope_prefix)
        super(DummyForm, self).__init__(*args, **kwargs)
        self.sub1 = SubForm1(prefix='sub1', **kwargs)
        self.sub2 = SubForm2(prefix='sub2', **kwargs)

    def get_initial_data(self):
        data = super(DummyForm, self).get_initial_data()
        data.update({
            self.sub1.prefix: self.sub1.get_initial_data(),
            self.sub2.prefix: self.sub2.get_initial_data(),
        })
        return data

    def is_valid(self):
        if not self.sub1.is_valid():
            self.errors.update(self.sub1.errors)
        if not self.sub2.is_valid():
            self.errors.update(self.sub2.errors)
        return super(DummyForm, self).is_valid() and self.sub1.is_valid() and self.sub2.is_valid()


class NgModelFormMixinTest(TestCase):
    valid_data = {
        'email': 'john@example.com',
        'onoff': True,
        'sub1': {
            'select_choices': 'c',
            'radio_choices': 'c',
            'first_name': 'Susan',
        },
        'sub2': {
            'select_choices': 'b',
            'radio_choices': 'a',
        },
    }

    def setUp(self):
        # create an unbound form
        self.unbound_form = DummyForm()
        htmlsource = self.unbound_form.as_p() + self.unbound_form.sub1.as_p() + self.unbound_form.sub2.as_p()
        self.dom = PyQuery(htmlsource)
        self.elements = self.dom('input') + self.dom('select')

    def test_unbound_form(self):
        """Check if Angular attributes are added to the unbound form"""
        self.assertTrue(self.elements, 'No input fields in form')
        self.assertFalse(self.unbound_form.is_bound)
        self.check_form_fields(self.unbound_form)
        self.check_form_fields(self.unbound_form.sub1)
        self.check_form_fields(self.unbound_form.sub2)

    def check_form_fields(self, form):
        for name in form.fields.keys():
            identifier = '%s.%s' % (form.prefix, name) if form.prefix else name
            input_fields = [e for e in self.elements if e.name == identifier]
            self.assertTrue(input_fields)
            for input_field in input_fields:
                self.assertIsInstance(input_field, (html.InputElement, html.SelectElement))
                self.assertEqual(input_field.attrib.get('ng-class'), 'fieldClass(\'%s\')' % identifier)
                if identifier == 'sub2.radio_choices':
                    self.assertFalse(input_field.attrib.get('ng-model'))
                else:
                    model = '%s.%s' % (self.unbound_form.scope_prefix, identifier)
                    self.assertEqual(input_field.attrib.get('ng-model'), model)
                if isinstance(input_field, html.InputElement) and input_field.type == 'radio':
                    if input_field.tail.strip() == CHOICES[1][1]:
                        self.assertTrue(input_field.checked)
                    else:
                        self.assertFalse(input_field.checked)
                elif isinstance(input_field, html.SelectElement):
                    self.assertListEqual(input_field.value_options, [c[0] for c in CHOICES])
                    self.assertEqual(input_field.value, CHOICES[0][0])

    def test_valid_form(self):
        bound_form = DummyForm(data=self.valid_data)
        self.assertTrue(bound_form.is_bound)
        self.assertTrue(bound_form.is_valid())

    def test_invalid_form(self):
        in_data = copy.deepcopy(self.valid_data)
        in_data['email'] = 'no.email.address'
        bound_form = DummyForm(data=in_data)
        self.assertTrue(bound_form.is_bound)
        self.assertFalse(bound_form.is_valid())
        self.assertTrue(bound_form.errors.pop('email', None))
        self.assertFalse(bound_form.errors)

    def test_invalid_subform(self):
        in_data = copy.deepcopy(self.valid_data)
        in_data['sub1']['select_choices'] = 'X'
        in_data['sub1']['radio_choices'] = 'Y'
        bound_form = DummyForm(data=in_data)
        self.assertTrue(bound_form.is_bound)
        self.assertFalse(bound_form.is_valid())
        self.assertTrue(bound_form.errors.pop('sub1.select_choices'))
        self.assertTrue(bound_form.errors.pop('sub1.radio_choices'))
        self.assertFalse(bound_form.errors)

    def test_initial_data(self):
        initial_data = self.unbound_form.get_initial_data()
        initial_keys = list(initial_data.keys())
        initial_keys.sort()
        valid_keys = list(self.valid_data.keys())
        valid_keys.sort()
        self.assertEqual(initial_keys, valid_keys)
        initial_keys = list(initial_data['sub1'].keys())
        initial_keys.sort()
        valid_keys = list(self.valid_data['sub1'].keys())
        valid_keys.sort()
        self.assertEqual(initial_keys, valid_keys)


class InvalidNgModelFormMixinTest(TestCase):
    def test_invalid_form(self):
        # create a form with an invalid Meta class
        self.assertRaises(TypeError, InvalidForm)


class AddPlaceholderFormMixinTest(TestCase):
    class EmailOnlyForm(AddPlaceholderFormMixin, forms.Form):
        email = forms.EmailField(label='E-Mail')
        password = forms.CharField(label='Password', widget=forms.PasswordInput)
        radio = forms.Select(choices=CHOICES)

    def setUp(self):
        self.email_form = self.EmailOnlyForm()
        htmlsource = str(self.email_form)
        self.dom = PyQuery(htmlsource)

    def test_email_field(self):
        email_field = self.dom('input[name=email]')
        self.assertEqual(len(email_field), 1)
        email_field_attrib = dict(email_field[0].attrib.items())
        self.assertDictContainsSubset({'placeholder': 'E-Mail'}, email_field_attrib)

    def test_password_field(self):
        password_field = self.dom('input[name=password]')
        self.assertEqual(len(password_field), 1)
        email_field_attrib = dict(password_field[0].attrib.items())
        self.assertDictContainsSubset({'placeholder': 'Password'}, email_field_attrib)

########NEW FILE########
__FILENAME__ = test_templatetags
# -*- coding: utf-8 -*-
from django.test import TestCase
from django.test.client import Client
from django.template import RequestContext, Template


class TemplateTagsTest(TestCase):
    def test_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        request = client.get('/dummy.html')
        request.META = {}
        request.is_secure = lambda: False
        request.get_host = lambda: 'localhost'
        template = Template('{% load djangular_tags %}x="{% csrf_token %}"')
        context = RequestContext(request, {'csrf_token': '123'})
        response = template.render(context)
        self.assertInHTML(response, 'x=""')

########NEW FILE########
__FILENAME__ = test_urlresolvers
# -*- coding: utf-8 -*-
from django.test import TestCase
from django.test.client import RequestFactory
from djangular.core.urlresolvers import get_all_remote_methods, get_current_remote_methods
from server.tests.urls import RemoteMethodsView


class TemplateRemoteMethods(TestCase):
    urls = 'server.tests.urls'

    def setUp(self):
        self.factory = RequestFactory()

    def test_get_current_remote_methods(self):
        view = RemoteMethodsView()
        view.request = self.factory.get('/straight_methods/')
        remote_methods = get_current_remote_methods(view)
        self.assertDictEqual({'foo': {'url': u'/straight_methods/', 'headers': {'DjNg-Remote-Method': 'foo'}, 'method': 'auto'}, 'bar': {'url': u'/straight_methods/', 'headers': {'DjNg-Remote-Method': 'bar'}, 'method': 'auto'}},
                             remote_methods)

    def test_get_all_remote_methods(self):
        remote_methods = get_all_remote_methods()
        self.assertDictEqual(remote_methods, {'submethods': {'sub': {'app': {'foo': {'url': '/sub_methods/sub/app/', 'headers': {'DjNg-Remote-Method': 'foo'}, 'method': 'auto'}, 'bar': {'url': '/sub_methods/sub/app/', 'headers': {'DjNg-Remote-Method': 'bar'}, 'method': 'auto'}}}}, 'straightmethods': {'foo': {'url': '/straight_methods/', 'headers': {'DjNg-Remote-Method': 'foo'}, 'method': 'auto'}, 'bar': {'url': '/straight_methods/', 'headers': {'DjNg-Remote-Method': 'bar'}, 'method': 'auto'}}})

########NEW FILE########
__FILENAME__ = test_validation
# -*- coding: utf-8 -*-
import django
from django.test import TestCase
from pyquery.pyquery import PyQuery
from server.forms import SubscriptionFormWithNgValidation, SubscriptionFormWithNgValidationAndModel
from djangular.forms.angular_base import NgBoundField


class NgFormValidationMixinTest(TestCase):
    def setUp(self):
        self.subscription_form = SubscriptionFormWithNgValidation()
        self.dom = PyQuery(str(self.subscription_form))

    def test_form(self):
        self.assertEqual(self.subscription_form.form_name, 'valid_form')

    def test_ng_length(self):
        first_name = self.dom('input[name=first_name]')
        self.assertEqual(len(first_name), 1)
        attrib = dict(first_name[0].attrib.items())
        self.assertDictContainsSubset({'ng-required': 'true'}, attrib)
        self.assertDictContainsSubset({'ng-minlength': '3'}, attrib)
        self.assertDictContainsSubset({'ng-maxlength': '20'}, attrib)
        lis = self.dom('label[for=id_first_name]').closest('th').next('td').children('ul.djng-form-errors > li')
        if django.VERSION[1] == 5:
            # Django < 1.6 not not know about minlength and maxlength
            self.assertEqual(len(lis), 2)
        else:
            self.assertEqual(len(lis), 4)
        attrib = dict(lis[0].attrib.items())
        self.assertDictContainsSubset({'ng-show': 'valid_form.first_name.$valid'}, attrib)
        attrib = dict(lis[1].attrib.items())
        self.assertDictContainsSubset({'ng-show': 'valid_form.first_name.$error.required'}, attrib)

    def test_type(self):
        email_field = self.dom('input[name=email]')
        self.assertEqual(len(email_field), 1)
        attrib = dict(email_field[0].attrib.items())
        self.assertNotIn('required', attrib)
        self.assertDictContainsSubset({'ng-model': 'email'}, attrib)
        if django.VERSION[1] == 5:
            self.assertDictContainsSubset({'type': 'text'}, attrib)
        else:
            self.assertDictContainsSubset({'type': 'email'}, attrib)

    def test_regex(self):
        last_name = self.dom('input[name=last_name]')
        self.assertEqual(len(last_name), 1)
        attrib = dict(last_name[0].attrib.items())
        self.assertDictContainsSubset({'ng-pattern': '/^[A-Z][a-z -]?/'}, attrib)

    def test_field_as_ul(self):
        bf = self.subscription_form['email']
        html = ''.join((
            '<ul class="djng-form-errors" ng-show="valid_form.email.$dirty" ng-cloak>',
              '<li ng-show="valid_form.email.$valid" class="valid"></li>',
              '<li ng-show="valid_form.email.$error.required" class="invalid">This field is required.</li>',
              '<li ng-show="valid_form.email.$error.email" class="invalid">Enter a valid email address.</li>',
            '</ul>'))
        self.assertHTMLEqual(bf.errors.as_ul(), html)

    def test_field_as_text(self):
        bf = self.subscription_form['email']
        self.assertIsInstance(bf, NgBoundField)
        response = bf.errors.as_text()
        self.assertMultiLineEqual(response, '* This field is required.\n* Enter a valid email address.')


class NgFormValidationWithModelMixinTest(TestCase):
    def setUp(self):
        subscription_form = SubscriptionFormWithNgValidationAndModel(scope_prefix='subscribe_data')
        self.dom = PyQuery(str(subscription_form))

    def test_ng_model(self):
        first_name = self.dom('input[name=first_name]')
        self.assertEqual(len(first_name), 1)
        attrib = dict(first_name[0].attrib.items())
        self.assertDictContainsSubset({'ng-model': 'subscribe_data.first_name'}, attrib)

    def test_decimal_field(self):
        weight = self.dom('input[name=weight]')
        self.assertEqual(len(weight), 1)
        attrib = dict(weight[0].attrib.items())
        if django.VERSION[1] == 5:
            self.assertDictContainsSubset({'type': 'text'}, attrib)
        else:
            self.assertDictContainsSubset({'type': 'number'}, attrib)
        self.assertDictContainsSubset({'min': '42'}, attrib)
        self.assertDictContainsSubset({'max': '95'}, attrib)
        self.assertDictContainsSubset({'ng-model': 'subscribe_data.weight'}, attrib)

    def test_float_field(self):
        height = self.dom('input[name=height]')
        self.assertEqual(len(height), 1)
        attrib = dict(height[0].attrib.items())
        if django.VERSION[1] == 5:
            self.assertDictContainsSubset({'type': 'text'}, attrib)
        else:
            self.assertDictContainsSubset({'type': 'number'}, attrib)
            self.assertDictContainsSubset({'min': '1.48'}, attrib)
            self.assertDictContainsSubset({'max': '1.95'}, attrib)
        self.assertDictContainsSubset({'ng-model': 'subscribe_data.height'}, attrib)

########NEW FILE########
__FILENAME__ = test_views
# -*- coding: utf-8 -*-
import json
import warnings
from django.test import TestCase
from django.test.client import RequestFactory
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse
from django.views.generic import View
from djangular.views.mixins import JSONResponseMixin, allow_remote_invocation, allowed_action


class JSONResponseView(JSONResponseMixin, View):
    @allow_remote_invocation
    def method_allowed(self, in_data=None):
        return {'success': True}

    @allow_remote_invocation
    def method_echo(self, in_data=None):
        return {'success': True, 'echo': in_data}

    def method_forbidden(self, in_data=None):
        """
        decorator @allow_remote_invocation is missing
        """
        return {'success': True}

    @allowed_action
    def deprecated_action(self, in_data):
        return {'success': True}


class DummyView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponse('GET OK')

    def post(self, request, *args, **kwargs):
        return HttpResponse(request.POST.get('foo'))


class DummyResponseView(JSONResponseMixin, DummyView):
    pass


class JSONResponseMixinTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.data = {'foo': 'bar'}

    def test_post_method_echo(self):
        request = self.factory.post('/dummy.json',
            data=json.dumps(self.data, cls=DjangoJSONEncoder),
            content_type='application/json; charset=utf-8;',
            HTTP_DJNG_REMOTE_METHOD='method_echo',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        response = JSONResponseView().post(request)
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response.status_code, 200)
        out_data = json.loads(response.content.decode('utf-8'))
        self.assertTrue(out_data['success'])
        self.assertDictEqual(out_data['echo'], self.data)

    def test_csrf_exempt_dispatch(self):
        request = self.factory.post('/dummy.json')
        response = JSONResponseView.as_view()(request)
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.content.decode('utf-8'), 'This view can not handle method POST')

    def test_post_method_undefined(self):
        request = self.factory.post('/dummy.json',
            data=json.dumps(self.data, cls=DjangoJSONEncoder),
            content_type='application/json; charset=utf-8;',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        response = JSONResponseView().post(request)
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.content.decode('utf-8'), 'This view can not handle method POST')

    def test_post_method_not_callable(self):
        request = self.factory.post('/dummy.json',
            data=json.dumps(self.data, cls=DjangoJSONEncoder),
            content_type='application/json; charset=utf-8;',
            HTTP_DJNG_REMOTE_METHOD='no_such_method',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        response = JSONResponseView().post(request)
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.content.decode('utf-8'), 'This view can not handle method POST')

    def test_post_method_is_forbidden(self):
        request = self.factory.post('/dummy.json',
            data=json.dumps(self.data, cls=DjangoJSONEncoder),
            content_type='application/json; charset=utf-8;',
            HTTP_DJNG_REMOTE_METHOD='method_forbidden',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        response = JSONResponseView().post(request)
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content.decode('utf-8'), "Method 'JSONResponseView.method_forbidden' has no decorator '@allow_remote_invocation'")

    def test_post_deprecated_action(self):
        with warnings.catch_warnings(record=True) as w:
            data = {'foo': 'bar', 'action': 'deprecated_action'}
            request = self.factory.post('/dummy.json',
                data=json.dumps(data, cls=DjangoJSONEncoder),
                content_type='application/json; charset=utf-8;',
                HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            response = JSONResponseView().post(request)
            self.assertIsInstance(response, HttpResponse)
            self.assertEqual(response.status_code, 200)
            out_data = json.loads(response.content.decode('utf-8'))
            self.assertTrue(out_data['success'])
            self.assertEqual(str(w[0].message), "Using the keyword 'action' inside the payload is deprecated. Please use 'djangoRMI' from module 'ng.django.forms'")

    def test_get_method_forbidden_ok(self):
        request = self.factory.get('/dummy.json', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        response = JSONResponseView().get(request, invoke_method='method_forbidden')
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response.status_code, 200)
        out_data = json.loads(response.content.decode('utf-8'))
        self.assertTrue(out_data['success'])

    def test_get_deprecated_action(self):
        with warnings.catch_warnings(record=True) as w:
            request = self.factory.get('/dummy.json', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            response = JSONResponseView().get(request, action='method_forbidden')
            self.assertIsInstance(response, HttpResponse)
            self.assertEqual(response.status_code, 200)
            out_data = json.loads(response.content.decode('utf-8'))
            self.assertTrue(out_data['success'])
            self.assertEqual(str(w[0].message), "Using the keyword 'action' in URLresolvers is deprecated. Please use 'invoke_method' instead")

    def test_get_method_forbidden_fail(self):
        request = self.factory.get('/dummy.json',
            HTTP_DJNG_REMOTE_METHOD='method_forbidden',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        response = JSONResponseView().get(request)
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content.decode('utf-8'), "Method 'JSONResponseView.method_forbidden' has no decorator '@allow_remote_invocation'")

    def test_get_method_not_callable(self):
        request = self.factory.get('/dummy.json',
            HTTP_DJNG_REMOTE_METHOD='no_such_method',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        response = JSONResponseView().get(request)
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.content.decode('utf-8'), "This view can not handle method GET")

    def test_get_method_allowed(self):
        request = self.factory.get('/dummy.json',
            HTTP_DJNG_REMOTE_METHOD='method_allowed',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        response = JSONResponseView().get(request)
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response.status_code, 200)
        out_data = json.loads(response.content.decode('utf-8'))
        self.assertTrue(out_data['success'])

    def test_post_pass_through(self):
        request = self.factory.post('/dummy.json', data=self.data)
        response = DummyResponseView().post(request)
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode('utf-8'), 'bar')

    def test_get_pass_through(self):
        request = self.factory.get('/dummy.json')
        response = DummyResponseView.as_view()(request)
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode('utf-8'), 'GET OK')

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
from django.conf.urls import url, patterns, include
from django.views.generic import View
from django.http import HttpResponse
from djangular.views.mixins import JSONResponseMixin, allow_remote_invocation


class RemoteMethodsView(JSONResponseMixin, View):
    @allow_remote_invocation
    def foo(self, in_data):
        return {'foo': 'abc'}

    @allow_remote_invocation
    def bar(self, in_data):
        return {'bar': 'abc'}

    def get(self, request):
        return HttpResponse('OK')

subsub_patterns = patterns('',
    url(r'^app/$', RemoteMethodsView.as_view(), name='app'),
)

sub_patterns = patterns('',
    url(r'^sub/', include(subsub_patterns, namespace='sub')),
)

urlpatterns = patterns('',
    url(r'^sub_methods/', include(sub_patterns, namespace='submethods')),
    url(r'^straight_methods/$', RemoteMethodsView.as_view(), name='straightmethods'),
)

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
from django.conf.urls import url, patterns
from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView
from server.views import (SubscribeViewWithFormValidation, SubscribeViewWithModelForm,
        SubscribeViewWithModelFormAndValidation, Ng3WayDataBindingView, NgFormDataValidView)


urlpatterns = patterns('',
    url(r'^form_validation/$', SubscribeViewWithFormValidation.as_view(),
        name='djng_form_validation'),
    url(r'^model_form/$', SubscribeViewWithModelForm.as_view(),
        name='djng_model_form'),
    url(r'^model_form_validation/$', SubscribeViewWithModelFormAndValidation.as_view(),
        name='djng_model_form_validation'),
    url(r'^threeway_databinding/$', Ng3WayDataBindingView.as_view(),
        name='djng_3way_databinding'),
    url(r'^form_data_valid', NgFormDataValidView.as_view(), name='form_data_valid'),
    url(r'^$', RedirectView.as_view(url=reverse_lazy('djng_form_validation'))),
)

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
import json
from django.shortcuts import redirect
from django.views.generic.base import TemplateView
from django.conf import settings
from django.http import HttpResponse
from server.forms import SubscriptionFormWithNgValidation, SubscriptionFormWithNgModel, SubscriptionFormWithNgValidationAndModel


class SubscribeFormView(TemplateView):
    def get_context_data(self, form=None, **kwargs):
        context = super(SubscribeFormView, self).get_context_data(**kwargs)
        form.fields['height'].widget.attrs['step'] = 0.05  # Ugly hack to set step size
        context.update(form=form, with_ws4redis=hasattr(settings, 'WEBSOCKET_URL'))
        return context

    def get(self, request, **kwargs):
        form = self.form()
        context = self.get_context_data(form=form, **kwargs)
        return self.render_to_response(context)

    def post(self, request, **kwargs):
        if request.is_ajax():
            return self.ajax(request.body)
        form = self.form(request.POST)
        if form.is_valid():
            return redirect('form_data_valid')
        context = self.get_context_data(form=form, **kwargs)
        return self.render_to_response(context)

    def ajax(self, request_body):
        in_data = json.loads(request_body)
        form = self.form(data=in_data)
        response_data = {'errors': form.errors}
        return HttpResponse(json.dumps(response_data), content_type="application/json")


class SubscribeViewWithFormValidation(SubscribeFormView):
    template_name = 'subscribe-form.html'
    form = SubscriptionFormWithNgValidation


class SubscribeViewWithModelForm(SubscribeFormView):
    template_name = 'model-form.html'
    form = SubscriptionFormWithNgModel


class SubscribeViewWithModelFormAndValidation(SubscribeFormView):
    template_name = 'model-validation-form.html'
    form = SubscriptionFormWithNgValidationAndModel


class Ng3WayDataBindingView(SubscribeViewWithModelForm):
    template_name = 'three-way-data-binding.html'


class NgFormDataValidView(TemplateView):
    """
    This view just displays a success message, when a valid form was posted successfully.
    """
    template_name = 'form-data-valid.html'

    def get_context_data(self, **kwargs):
        context = super(NgFormDataValidView, self).get_context_data(**kwargs)
        context.update(with_ws4redis=hasattr(settings, 'WEBSOCKET_URL'))
        return context

########NEW FILE########
