__FILENAME__ = actions
# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, unicode_literals

from django.contrib import messages
from django.views.generic import TemplateView
from django.utils.encoding import force_text
from django.utils.text import capfirst
from django.utils.translation import ugettext_lazy, ungettext, pgettext_lazy
from django.utils.translation import ugettext as _

from . import permissions, utils
from .viewmixins import AdminModel2Mixin


def get_description(action):
    if hasattr(action, 'description'):
        # This is for classes
        return action.description
    else:
        # This if for functions
        return capfirst(action.__name__.replace('_', ' '))


class BaseListAction(AdminModel2Mixin, TemplateView):

    permission_classes = (permissions.IsStaffPermission,)

    empty_message = ugettext_lazy(
        'Items must be selected in order to perform actions '
        'on them. No items have been changed.'
    )

    only_selected = True

    queryset = None

    def __init__(self, queryset, *args, **kwargs):
        self.queryset = queryset
        self.model = queryset.model

        options = utils.model_options(self.model)

        self.app_label = options.app_label
        self.model_name = options.module_name

        self.item_count = len(queryset)

        if self.item_count <= 1:
            objects_name = options.verbose_name
        else:
            objects_name = options.verbose_name_plural
        self.objects_name = unicode(objects_name)

        super(BaseListAction, self).__init__(*args, **kwargs)

    def get_queryset(self):
        """ Replaced `get_queryset` from `AdminModel2Mixin`"""
        return self.queryset

    def description(self):
        raise NotImplementedError("List action classes require"
                                  " a description attribute.")

    @property
    def success_message(self):
        raise NotImplementedError(
            "List actions classes require a success_message"
        )

    @property
    def success_message_plural(self):
        """
        A plural form for the success_message

        If not provided, falls back to the regular form
        """
        return self.success_message

    @property
    def default_template_name(self):
        raise NotImplementedError(
            "List actions classes using display_nested_response"
            " require a template"
        )

    def get_context_data(self, **kwargs):
        """ Utility method when you want to display nested objects
            (such as during a bulk update/delete)
        """
        context = super(BaseListAction, self).get_context_data()

        def _format_callback(obj):
            opts = utils.model_options(obj)
            return '%s: %s' % (force_text(capfirst(opts.verbose_name)),
                               force_text(obj))

        collector = utils.NestedObjects(using=None)
        collector.collect(self.queryset)

        context.update({
            'view': self,
            'objects_name': self.objects_name,
            'queryset': self.queryset,
            'deletable_objects': collector.nested(_format_callback),
        })

        return context

    def get(self, request):
        if self.item_count > 0:
            return super(BaseListAction, self).get(request)

        message = _(self.empty_message)
        messages.add_message(request, messages.INFO, message)

        return None

    def post(self, request):
        if self.process_queryset() is None:

            # objects_name should already be pluralized, see __init__
            message = ungettext(
                self.success_message,
                self.success_message_plural,
                self.item_count
            ) % {
                'count': self.item_count, 'items': self.objects_name
            }

            messages.add_message(request, messages.INFO, message)

            return None

    def process_queryset(self):
        msg = 'Must be provided to do some actions with queryset'
        raise NotImplementedError(msg)


class DeleteSelectedAction(BaseListAction):
    # TODO: Check that user has permission to delete all related obejcts.  See
    # `get_deleted_objects` in contrib.admin.util for how this is currently
    # done.  (Hint: I think we can do better.)

    default_template_name = "actions/delete_selected_confirmation.html"

    description = ugettext_lazy("Delete selected items")

    success_message = pgettext_lazy(
        'singular form',
        'Successfully deleted %(count)s %(items)s',
    )
    success_message_plural = pgettext_lazy(
        'plural form',
        'Successfully deleted %(count)s %(items)s',
    )

    permission_classes = BaseListAction.permission_classes + (
        permissions.ModelDeletePermission,
    )

    def post(self, request):
        if request.POST.get('confirmed'):
            super(DeleteSelectedAction, self).post(request)
        else:
            # The user has not confirmed that they want to delete the
            # objects, so render a template asking for their confirmation.
            return self.get(request)


    def process_queryset(self):
        # The user has confirmed that they want to delete the objects.
        self.get_queryset().delete()

########NEW FILE########
__FILENAME__ = admin2
# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, unicode_literals

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.contrib.sites.models import Site

from rest_framework.relations import PrimaryKeyRelatedField

import djadmin2
from djadmin2.forms import UserCreationForm, UserChangeForm
from djadmin2.apiviews import Admin2APISerializer


class GroupSerializer(Admin2APISerializer):
    permissions = PrimaryKeyRelatedField(many=True)

    class Meta:
        model = Group


class GroupAdmin2(djadmin2.ModelAdmin2):
    api_serializer_class = GroupSerializer


class UserSerializer(Admin2APISerializer):
    user_permissions = PrimaryKeyRelatedField(many=True)

    class Meta:
        model = User
        exclude = ('passwords',)


class UserAdmin2(djadmin2.ModelAdmin2):
    create_form_class = UserCreationForm
    update_form_class = UserChangeForm
    search_fields = ('username', 'groups__name', 'first_name', 'last_name',
                     'email')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')

    api_serializer_class = UserSerializer


#  Register each model with the admin
djadmin2.default.register(User, UserAdmin2)
djadmin2.default.register(Group, GroupAdmin2)


# Register the sites app if it's been activated in INSTALLED_APPS
if "django.contrib.sites" in settings.INSTALLED_APPS:

    class SiteAdmin2(djadmin2.ModelAdmin2):
        list_display = ('domain', 'name')
        search_fields = ('domain', 'name')

    djadmin2.default.register(Site, SiteAdmin2)

########NEW FILE########
__FILENAME__ = apiviews
# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, unicode_literals

from django.utils.encoding import force_str

from rest_framework import fields, generics, serializers
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from . import utils
from .viewmixins import Admin2Mixin

API_VERSION = '0.1'


class Admin2APISerializer(serializers.HyperlinkedModelSerializer):
    _default_view_name = 'admin2:%(app_label)s_%(model_name)s_api_detail'

    pk = fields.Field(source='pk')
    __str__ = fields.Field(source='__unicode__')


class Admin2APIMixin(Admin2Mixin):
    raise_exception = True

    def get_serializer_class(self):
        if self.serializer_class is None:
            model_class = self.get_model()

            class ModelAPISerilizer(Admin2APISerializer):
                # we need to reset this here, since we don't know anything
                # about the name of the admin instance when declaring the
                # Admin2APISerializer base class
                _default_view_name = ':'.join((
                    self.model_admin.admin.name,
                    '%(app_label)s_%(model_name)s_api_detail'))

                class Meta:
                    model = model_class

            return ModelAPISerilizer
        return super(Admin2APIMixin, self).get_serializer_class()


class IndexAPIView(Admin2APIMixin, APIView):
    apps = None
    registry = None
    app_verbose_names = None
    app_verbose_name = None

    def get_model_data(self, model):
        model_admin = self.registry[model]
        model_options = utils.model_options(model)
        opts = {
            'current_app': model_admin.admin.name,
            'app_label': model_options.app_label,
            'model_name': model_options.object_name.lower(),
        }
        model_url = reverse(
            '%(current_app)s:%(app_label)s_%(model_name)s_api_list' % opts,
            request=self.request,
            format=self.kwargs.get('format'))
        model_options = utils.model_options(model)
        return {
            'url': model_url,
            'verbose_name': force_str(model_options.verbose_name),
            'verbose_name_plural': force_str(model_options.verbose_name_plural),
        }

    def get_app_data(self, app_label, models):
        model_data = []
        for model in models:
            model_data.append(self.get_model_data(model))
        return {
            'app_label': app_label,
            'models': model_data,
            'app_verbose_name': force_str(self.app_verbose_names.get(app_label))
        }

    def get(self, request):
        app_data = []
        for app_label, registry in self.apps.items():
            models = registry.keys()
            app_data.append(self.get_app_data(app_label, models))
        index_data = {
            'version': API_VERSION,
            'apps': app_data,
        }
        return Response(index_data)


class ListCreateAPIView(Admin2APIMixin, generics.ListCreateAPIView):
    pass


class RetrieveUpdateDestroyAPIView(Admin2APIMixin, generics.RetrieveUpdateDestroyAPIView):
    pass

########NEW FILE########
__FILENAME__ = core
# -*- coding: utf-8 -*-:
"""
WARNING: This file about to undergo major refactoring by @pydanny per
Issue #99.
"""
from __future__ import division, absolute_import, unicode_literals

from django.conf.urls import patterns, include, url
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.importlib import import_module


from . import apiviews
from . import types
from . import utils
from . import views


class Admin2(object):
    """
    The base Admin2 object.
    It keeps a registry of all registered Models and collects the urls of their
    related ModelAdmin2 instances.

    It also provides an index view that serves as an entry point to the
    admin site.
    """
    index_view = views.IndexView
    app_index_view = views.AppIndexView
    api_index_view = apiviews.IndexAPIView

    def __init__(self, name='admin2'):
        self.registry = {}
        self.apps = {}
        self.app_verbose_names = {}
        self.name = name

    def register(self, model, model_admin=None, **kwargs):
        """
        Registers the given model with the given admin class. Once a model is
        registered in self.registry, we also add it to app registries in
        self.apps.

        If no model_admin is passed, it will use ModelAdmin2. If keyword
        arguments are given they will be passed to the admin class on
        instantiation.

        If a model is already registered, this will raise ImproperlyConfigured.
        """
        if model in self.registry:
            raise ImproperlyConfigured(
                '%s is already registered in django-admin2' % model)
        if not model_admin:
            model_admin = types.ModelAdmin2
        self.registry[model] = model_admin(model, admin=self, **kwargs)

        # Add the model to the apps registry
        app_label = utils.model_options(model).app_label
        if app_label in self.apps.keys():
            self.apps[app_label][model] = self.registry[model]
        else:
            self.apps[app_label] = {model: self.registry[model]}

    def deregister(self, model):
        """
        Deregisters the given model. Remove the model from the self.app as well

        If the model is not already registered, this will raise
        ImproperlyConfigured.
        """
        try:
            del self.registry[model]
        except KeyError:
            raise ImproperlyConfigured(
                '%s was never registered in django-admin2' % model)

        # Remove the model from the apps registry
        # Get the app label
        app_label = utils.model_options(model).app_label
        # Delete the model from it's app registry
        del self.apps[app_label][model]

        # if no more models in an app's registry
        # then delete the app from the apps.
        if self.apps[app_label] is {}:
            del self.apps[app_label]  # no

    def register_app_verbose_name(self, app_label, app_verbose_name):
        """
        Registers the given app label with the given app verbose name.

        If a app_label is already registered, this will raise
        ImproperlyConfigured.
        """
        if app_label in self.app_verbose_names:
            raise ImproperlyConfigured(
                '%s is already registered in django-admin2' % app_label)

        self.app_verbose_names[app_label] = app_verbose_name

    def deregister_app_verbose_name(self, app_label):
        """
        Deregisters the given app label. Remove the app label from the
        self.app_verbose_names as well.

        If the app label is not already registered, this will raise
        ImproperlyConfigured.
        """
        try:
            del self.app_verbose_names[app_label]
        except KeyError:
            raise ImproperlyConfigured(
                '%s app label was never registered in django-admin2' % app_label)

    def autodiscover(self):
        """
        Autodiscovers all admin2.py modules for apps in INSTALLED_APPS by
        trying to import them.
        """
        for app_name in [x for x in settings.INSTALLED_APPS]:
            try:
                import_module("%s.admin2" % app_name)
            except ImportError as e:
                if str(e) == "No module named admin2":
                    continue
                raise e

    def get_admin_by_name(self, name):
        """
        Returns the admin instance that was registered with the passed in
        name.
        """
        for object_admin in self.registry.values():
            if object_admin.name == name:
                return object_admin
        raise ValueError(
            u'No object admin found with name {}'.format(repr(name)))

    def get_index_kwargs(self):
        return {
            'registry': self.registry,
            'app_verbose_names': self.app_verbose_names,
            'apps': self.apps,
        }

    def get_app_index_kwargs(self):
        return {
            'registry': self.registry,
            'app_verbose_names': self.app_verbose_names,
            'apps': self.apps,
        }

    def get_api_index_kwargs(self):
        return {
            'registry': self.registry,
            'app_verbose_names': self.app_verbose_names,
            'apps': self.apps,
        }

    def get_urls(self):
        urlpatterns = patterns(
            '',
            url(regex=r'^$',
                view=self.index_view.as_view(**self.get_index_kwargs()),
                name='dashboard'
                ),
            url(regex='^auth/user/(?P<pk>\d+)/update/password/$',
                view=views.PasswordChangeView.as_view(),
                name='password_change'
                ),
            url(regex='^password_change_done/$',
                view=views.PasswordChangeDoneView.as_view(),
                name='password_change_done'
                ),
            url(regex='^logout/$',
                view=views.LogoutView.as_view(),
                name='logout'
                ),
            url(regex=r'^(?P<app_label>\w+)/$',
                view=self.app_index_view.as_view(
                    **self.get_app_index_kwargs()),
                name='app_index'
                ),
            url(regex=r'^api/v0/$',
                view=self.api_index_view.as_view(
                    **self.get_api_index_kwargs()),
                name='api_index'
                ),
        )
        for model, model_admin in self.registry.iteritems():
            model_options = utils.model_options(model)
            urlpatterns += patterns(
                '',
                url('^{}/{}/'.format(
                    model_options.app_label,
                    model_options.object_name.lower()),
                    include(model_admin.urls)),
                url('^api/v0/{}/{}/'.format(
                    model_options.app_label,
                    model_options.object_name.lower()),
                    include(model_admin.api_urls)),
            )
        return urlpatterns

    @property
    def urls(self):
        # We set the application and instance namespace here
        return self.get_urls(), self.name, self.name

########NEW FILE########
__FILENAME__ = filters
# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, unicode_literals

import collections
from itertools import chain

from django import forms
from django.forms.util import flatatt
from django.utils.html import format_html
from django.utils.encoding import force_text
from django.utils.safestring import mark_safe
from django.forms import widgets as django_widgets
from django.utils.translation import ugettext_lazy

import django_filters

LINK_TEMPLATE = '<a href=?{0}={1} {2}>{3}</a>'


class NumericDateFilter(django_filters.DateFilter):
    field_class = forms.IntegerField


class ChoicesAsLinksWidget(django_widgets.Select):
    """Select form widget taht renders links for choices
    instead of select element with options.
    """
    def render(self, name, value, attrs=None, choices=()):
        links = []
        for choice_value, choice_label in chain(self.choices, choices):
            links.append(format_html(
                LINK_TEMPLATE,
                name, choice_value, flatatt(attrs), force_text(choice_label),
            ))
        return mark_safe(u"<br />".join(links))


class NullBooleanLinksWidget(
    ChoicesAsLinksWidget,
    django_widgets.NullBooleanSelect
):
    def __init__(self, attrs=None, choices=()):
        super(ChoicesAsLinksWidget, self).__init__(attrs)
        self.choices = [
            ('1', ugettext_lazy('Unknown')),
            ('2', ugettext_lazy('Yes')),
            ('3', ugettext_lazy('No')),
        ]

#: Maps `django_filter`'s field filters types to our
#: custom form widget.
FILTER_TYPE_TO_WIDGET = {
    django_filters.BooleanFilter: NullBooleanLinksWidget,
    django_filters.ChoiceFilter: ChoicesAsLinksWidget,
    django_filters.ModelChoiceFilter: ChoicesAsLinksWidget,
}


def build_list_filter(request, model_admin, queryset):
    """Builds :class:`~django_filters.FilterSet` instance
    for :attr:`djadmin2.ModelAdmin2.Meta.list_filter` option.

    If :attr:`djadmin2.ModelAdmin2.Meta.list_filter` is not
    sequence, it's considered to be class with interface like
    :class:`django_filters.FilterSet` and its instantiate wit
    `request.GET` and `queryset`.
    """
    # if ``list_filter`` is not iterable return it right away
    if not isinstance(model_admin.list_filter, collections.Iterable):
        return model_admin.list_filter(
            request.GET,
            queryset=queryset,
        )
    # otherwise build :mod:`django_filters.FilterSet`
    filters = []
    for field_filter in model_admin.list_filter:
        if isinstance(field_filter, basestring):
            filters.append(get_filter_for_field_name(
                queryset.model,
                field_filter,
            ))
        else:
            filters.append(field_filter)
    filterset_dict = {}
    for field_filter in filters:
        filterset_dict[field_filter.name] = field_filter
    fields = filterset_dict.keys()
    filterset_dict['Meta'] = type(
        b'Meta',
        (),
        {
            'model': queryset.model,
            'fields': fields,
        },
    )
    return type(
        b'%sFilterSet' % queryset.model.__name__,
        (django_filters.FilterSet, ),
        filterset_dict,
    )(request.GET, queryset=queryset)


def build_date_filter(request, model_admin, queryset):
    filterset_dict = {
        "year": NumericDateFilter(
            name="published_date",
            lookup_type="year",
        ),
        "month": NumericDateFilter(
            name="published_date",
            lookup_type="month",
        ),
        "day": NumericDateFilter(
            name="published_date",
            lookup_type="day",
        )
    }

    return type(
        b'%sDateFilterSet' % queryset.model.__name__,
        (django_filters.FilterSet,),
        filterset_dict,
    )(request.GET, queryset=queryset)


def get_filter_for_field_name(model, field_name):
    """Returns filter for model field by field name.
    """
    filter_ = django_filters.FilterSet.filter_for_field(
        django_filters.filterset.get_model_field(model, field_name,),
        field_name,
    )
    filter_.widget = FILTER_TYPE_TO_WIDGET.get(
        filter_.__class__,
        filter_.widget,
    )
    return filter_

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, unicode_literals

from copy import deepcopy

from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
import django
import django.forms
import django.forms.models
import django.forms.extras.widgets
from django.utils.translation import ugettext_lazy

import floppyforms


_WIDGET_COMMON_ATTRIBUTES = (
    'is_hidden',
    'needs_multipart_form',
    'is_localized',
    'is_required')

_WIDGET_COMMON_ARGUMENTS = ('attrs',)


def _copy_attributes(original, new_widget, attributes):
    for attr in attributes:
        original_value = getattr(original, attr)
        original_value = deepcopy(original_value)

        # Don't set the attribute if it is a property. In that case we can be
        # sure that the widget class is taking care of the calculation for that
        # property.
        old_value_on_new_widget = getattr(new_widget.__class__, attr, None)
        if not isinstance(old_value_on_new_widget, property):
            setattr(new_widget, attr, original_value)


def _create_widget(widget_class, copy_attributes=(), init_arguments=()):
    # attach defaults that apply for all widgets
    copy_attributes = tuple(copy_attributes) + _WIDGET_COMMON_ATTRIBUTES
    init_arguments = tuple(init_arguments) + _WIDGET_COMMON_ARGUMENTS

    def create_new_widget(original):
        kwargs = {}
        for argname in init_arguments:
            kwargs[argname] = getattr(original, argname)
        new_widget = widget_class(**kwargs)
        _copy_attributes(
            original,
            new_widget,
            copy_attributes)
        return new_widget
    return create_new_widget


def _create_radioselect(original):
    # return original widget if the renderer is something else than what
    # django ships with by default. This means if this condition evaluates to
    # true, then a custom renderer was specified. We cannot emulate its
    # behaviour so we shouldn't guess and just return the original widget
    if original.renderer is not django.forms.widgets.RadioFieldRenderer:
        return original
    create_new_widget = _create_widget(
        floppyforms.widgets.RadioSelect,
        ('choices', 'allow_multiple_selected',))
    return create_new_widget(original)


def _create_splitdatetimewidget(widget_class):
    def create_new_widget(original):
        new_widget = widget_class(
            attrs=original.attrs,
            date_format=original.widgets[0].format,
            time_format=original.widgets[1].format)
        _copy_attributes(original, new_widget, _WIDGET_COMMON_ARGUMENTS)
        return new_widget
    return create_new_widget


def _create_multiwidget(widget_class, copy_attributes=(), init_arguments=()):
    create_new_widget = _create_widget(widget_class, copy_attributes,
                                       init_arguments)

    def create_new_multiwidget(original):
        multiwidget = create_new_widget(original)
        multiwidget.widgets = [
            floppify_widget(widget)
            for widget in multiwidget.widgets]
        return multiwidget
    return create_new_multiwidget


# this dictionary keeps a mapping from django's widget classes to a callable
# that will accept an instance of this class. It will return a new instance of
# a corresponding floppyforms widget, with the same semantics -- all relevant
# attributes will be copied to the new widget.
_django_to_floppyforms_widget = {
    django.forms.widgets.Input:
        _create_widget(floppyforms.widgets.Input, ('input_type',)),
    django.forms.widgets.TextInput:
        _create_widget(floppyforms.widgets.TextInput, ('input_type',)),
    django.forms.widgets.PasswordInput:
        _create_widget(floppyforms.widgets.PasswordInput, ('input_type',)),
    django.forms.widgets.HiddenInput:
        _create_widget(floppyforms.widgets.HiddenInput, ('input_type',)),
    django.forms.widgets.MultipleHiddenInput:
        _create_widget(
            floppyforms.widgets.MultipleHiddenInput,
            ('input_type',),
            init_arguments=('choices',)),
    django.forms.widgets.FileInput:
        _create_widget(floppyforms.widgets.FileInput, ('input_type',)),
    django.forms.widgets.ClearableFileInput:
        _create_widget(
            floppyforms.widgets.ClearableFileInput,
            (
                'input_type', 'initial_text', 'input_text',
                'clear_checkbox_label', 'template_with_initial',
                'template_with_clear')),
    django.forms.widgets.Textarea:
        _create_widget(floppyforms.widgets.Textarea),
    django.forms.widgets.DateInput:
        _create_widget(
            floppyforms.widgets.DateInput,
            init_arguments=('format',)),
    django.forms.widgets.DateTimeInput:
        _create_widget(
            floppyforms.widgets.DateTimeInput,
            init_arguments=('format',)),
    django.forms.widgets.TimeInput:
        _create_widget(
            floppyforms.widgets.TimeInput,
            init_arguments=('format',)),
    django.forms.widgets.CheckboxInput:
        _create_widget(floppyforms.widgets.CheckboxInput, ('check_test',)),
    django.forms.widgets.Select:
        _create_widget(
            floppyforms.widgets.Select,
            ('choices', 'allow_multiple_selected',)),
    django.forms.widgets.NullBooleanSelect:
        _create_widget(
            floppyforms.widgets.NullBooleanSelect,
            ('choices', 'allow_multiple_selected',)),
    django.forms.widgets.SelectMultiple:
        _create_widget(
            floppyforms.widgets.SelectMultiple,
            ('choices', 'allow_multiple_selected',)),
    django.forms.widgets.RadioSelect:
        _create_radioselect,
    django.forms.widgets.CheckboxSelectMultiple:
        _create_widget(
            floppyforms.widgets.CheckboxSelectMultiple,
            ('choices', 'allow_multiple_selected',)),
    django.forms.widgets.MultiWidget:
        _create_widget(
            floppyforms.widgets.MultiWidget,
            init_arguments=('widgets',)),
    django.forms.widgets.SplitDateTimeWidget:
        _create_splitdatetimewidget(
            floppyforms.widgets.SplitDateTimeWidget),
    django.forms.widgets.SplitHiddenDateTimeWidget:
        _create_splitdatetimewidget(
            floppyforms.widgets.SplitHiddenDateTimeWidget),
    django.forms.extras.widgets.SelectDateWidget:
        _create_widget(
            floppyforms.widgets.SelectDateWidget,
            init_arguments=('years', 'required')),
}

_django_field_to_floppyform_widget = {
    django.forms.fields.FloatField:
        _create_widget(floppyforms.widgets.NumberInput),
    django.forms.fields.DecimalField:
        _create_widget(floppyforms.widgets.NumberInput),
    django.forms.fields.IntegerField:
        _create_widget(floppyforms.widgets.NumberInput),
    django.forms.fields.EmailField:
        _create_widget(floppyforms.widgets.EmailInput),
    django.forms.fields.URLField:
        _create_widget(floppyforms.widgets.URLInput),
    django.forms.fields.SlugField:
        _create_widget(floppyforms.widgets.SlugInput),
    django.forms.fields.IPAddressField:
        _create_widget(floppyforms.widgets.IPAddressInput),
    django.forms.fields.SplitDateTimeField:
        _create_splitdatetimewidget(floppyforms.widgets.SplitDateTimeWidget),
}


def allow_floppify_widget_for_field(field):
    '''
    We only allow to replace a widget with the floppyform counterpart if the
    original, by django determined widget is still in place. We don't want to
    override custom widgets that a user specified.
    '''
    # There is a special case for IntegerFields (and all subclasses) that
    # replaces the default TextInput with a NumberInput, if localization is
    # turned off. That applies for Django 1.6 upwards.
    # See the relevant source code in django:
    # https://github.com/django/django/blob/1.6/django/forms/fields.py#L225
    if django.VERSION >= (1, 6):
        if isinstance(field, django.forms.IntegerField) and not field.localize:
            if field.widget.__class__ is django.forms.NumberInput:
                return True

    # We can check if the widget was replaced by comparing the class of the
    # specified widget with the default widget that is specified on the field
    # class.
    if field.widget.__class__ is field.__class__.widget:
        return True

    # At that point we are assuming that the user replaced the original widget
    # with a custom one. So we don't allow to overwrite it.
    return False


def floppify_widget(widget, field=None):
    '''
    Get an instance of django.forms.widgets.Widget and return a new widget
    instance but using the corresponding floppyforms widget class.

    Only original django widgets will be replaced with a floppyforms version.
    The widget will be returned unaltered if it is not known, e.g. if it's a
    custom widget from a third-party app.

    The optional parameter ``field`` can be used to influence the widget
    creation further. This is useful since floppyforms supports more widgets
    than django does. For example is django using a ``TextInput`` for a
    ``EmailField``, but floppyforms has a better suiting widget called
    ``EmailInput``. If a widget is found specifically for the passed in
    ``field``, it will take precendence to the first parameter ``widget``
    which will effectively be ignored.
    '''
    if field is not None:
        create_widget = _django_field_to_floppyform_widget.get(
            field.__class__)
        if create_widget is not None:
            if allow_floppify_widget_for_field(field):
                return create_widget(widget)
    create_widget = _django_to_floppyforms_widget.get(widget.__class__)
    if create_widget is not None:
        return create_widget(widget)
    return widget


def floppify_form(form_class):
    '''
    Take a normal form and return a subclass of that form that replaces all
    django widgets with the corresponding floppyforms widgets.
    '''
    new_form_class = type(form_class.__name__, (form_class,), {})
    for field in new_form_class.base_fields.values():
        field.widget = floppify_widget(field.widget, field=field)
    return new_form_class


def modelform_factory(model, form=django.forms.models.ModelForm, fields=None,
                      exclude=None, formfield_callback=None, widgets=None):
    form_class = django.forms.models.modelform_factory(
        model=model,
        form=form,
        fields=fields,
        exclude=exclude,
        formfield_callback=formfield_callback,
        widgets=widgets)
    return floppify_form(form_class)


# Translators : %(username)s will be replaced by the username_field name
# (default : username, but could be email, or something else)
ERROR_MESSAGE = ugettext_lazy("Please enter the correct %(username)s and password "
        "for a staff account. Note that both fields may be case-sensitive.")


class AdminAuthenticationForm(AuthenticationForm):
    """
    A custom authentication form used in the admin app.
    Liberally copied from django.contrib.admin.forms.AdminAuthenticationForm

    """
    error_messages = {
        'required': ugettext_lazy("Please log in again, because your session has expired."),
    }
    this_is_the_login_form = django.forms.BooleanField(widget=floppyforms.HiddenInput,
            initial=1, error_messages=error_messages)

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        message = ERROR_MESSAGE

        if username and password:
            self.user_cache = authenticate(username=username, password=password)
            if self.user_cache is None:
                raise floppyforms.ValidationError(message % {
                    'username': self.username_field.verbose_name
                })
            elif not self.user_cache.is_active or not self.user_cache.is_staff:
                raise floppyforms.ValidationError(message % {
                    'username': self.username_field.verbose_name
                })
        return self.cleaned_data


UserCreationForm = floppify_form(UserCreationForm)
UserChangeForm = floppify_form(UserChangeForm)

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
""" Boilerplate for now, will serve a purpose soon! """
from __future__ import division, absolute_import, unicode_literals

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import signals
from django.utils.encoding import force_text
from django.utils.encoding import smart_text
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext, ugettext_lazy as _

from . import permissions
from .utils import quote


class LogEntryManager(models.Manager):
    def log_action(self, user_id, obj, action_flag, change_message=''):
        content_type_id = ContentType.objects.get_for_model(obj).id
        e = self.model(None, None, user_id, content_type_id,
                       smart_text(obj.id), force_text(obj)[:200],
                       action_flag, change_message)
        e.save()


@python_2_unicode_compatible
class LogEntry(models.Model):
    ADDITION = 1
    CHANGE = 2
    DELETION = 3

    action_time = models.DateTimeField(_('action time'), auto_now=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             related_name='log_entries')
    content_type = models.ForeignKey(ContentType, blank=True, null=True,
                                     related_name='log_entries')
    object_id = models.TextField(_('object id'), blank=True, null=True)
    object_repr = models.CharField(_('object repr'), max_length=200)
    action_flag = models.PositiveSmallIntegerField(_('action flag'))
    change_message = models.TextField(_('change message'), blank=True)

    objects = LogEntryManager()

    class Meta:
        verbose_name = _('log entry')
        verbose_name_plural = _('log entries')
        ordering = ('-action_time',)

    def __repr__(self):
        return smart_text(self.action_time)

    def __str__(self):
        if self.action_flag == self.ADDITION:
            return ugettext('Added "%(object)s".') % {
                'object': self.object_repr}
        elif self.action_flag == self.CHANGE:
            return ugettext('Changed "%(object)s" - %(changes)s') % {
                'object': self.object_repr,
                'changes': self.change_message,
            }
        elif self.action_flag == self.DELETION:
            return ugettext('Deleted "%(object)s."') % {
                'object': self.object_repr}

        return ugettext('LogEntry Object')

    def is_addition(self):
        return self.action_flag == self.ADDITION

    def is_change(self):
        return self.action_flag == self.CHANGE

    def is_deletion(self):
        return self.action_flag == self.DELETION

    @property
    def action_type(self):
        if self.is_addition():
            return _('added')
        if self.is_change():
            return _('changed')
        if self.is_deletion():
            return _('deleted')
        return ''

    def get_edited_object(self):
        "Returns the edited object represented by this log entry"
        return self.content_type.get_object_for_this_type(pk=self.object_id)

    def get_admin_url(self):
        """
        Returns the admin URL to edit the object represented by this log entry.
        This is relative to the Django admin index page.
        """
        if self.content_type and self.object_id:
            return '{0.app_label}/{0.model}/{1}'.format(
                self.content_type,
                quote(self.object_id)
            )
        return None

# setup signal handlers here, since ``models.py`` will be imported by django
# for sure if ``djadmin2`` is listed in the ``INSTALLED_APPS``.

signals.post_syncdb.connect(
    permissions.create_view_permissions,
    dispatch_uid="django-admin2.djadmin2.permissions.create_view_permissions")

########NEW FILE########
__FILENAME__ = permissions
# -*- coding: utf-8 -*-
"""
djadmin2's permission handling. The permission classes have the same API as
the permission handling classes of the django-rest-framework. That way, we can
reuse them in the admin's REST API.

The permission checks take place in callables that follow the following
interface:

* They get passed in the current ``request``, an instance of the currently
  active ``view`` and optionally the object that should be used for
  object-level permission checking.
* Return ``True`` if the permission shall be granted, ``False`` otherwise.

The permission classes are then just fancy wrappers of these basic checks of
which it can hold multiple.
"""
from __future__ import division, absolute_import, unicode_literals

import logging
import re

from django.contrib.auth import models as auth_models
from django.contrib.contenttypes import models as contenttypes_models
from django.db.models import get_models
from django.utils import six

from . import utils


logger = logging.getLogger('djadmin2')


def is_authenticated(request, view, obj=None):
    '''
    Checks if the current user is authenticated.
    '''
    return request.user.is_authenticated()


def is_staff(request, view, obj=None):
    '''
    Checks if the current user is a staff member.
    '''
    return request.user.is_staff


def is_superuser(request, view, obj=None):
    '''
    Checks if the current user is a superuser.
    '''
    return request.user.is_superuser


def model_permission(permission):
    '''
    This is actually a permission check factory. It means that it will return
    a function that can then act as a permission check. The returned callable
    will check if the user has the with ``permission`` provided model
    permission. You can use ``{app_label}`` and ``{model_name}`` as
    placeholders in the permission name. They will be replaced with the
    ``app_label`` and the ``model_name`` (in lowercase) of the model that the
    current view is operating on.

    Example:

    .. code-block:: python

        check_add_perm = model_permission('{app_label}.add_{model_name}')

        class ModelAddPermission(permissions.BasePermission):
            permissions = [check_add_perm]
    '''
    def has_permission(request, view, obj=None):
        model_class = getattr(view, 'model', None)
        queryset = getattr(view, 'queryset', None)

        if model_class is None and queryset is not None:
            model_class = queryset.model

        assert model_class, (
            'Cannot apply model permissions on a view that does not '
            'have a `.model` or `.queryset` property.')

        permission_name = permission.format(
            app_label=model_class._meta.app_label,
            model_name=model_class._meta.module_name)
        return request.user.has_perm(permission_name, obj)
    return has_permission


class BasePermission(object):
    '''
    Provides a base class with a common API. It implements a compatible
    interface to django-rest-framework permission backends.
    '''
    permissions = []
    permissions_for_method = {}

    def get_permission_checks(self, request, view):
        permission_checks = []
        permission_checks.extend(self.permissions)
        method_permissions = self.permissions_for_method.get(request.method, ())
        permission_checks.extend(method_permissions)
        return permission_checks

    # needs to be compatible to django-rest-framework
    def has_permission(self, request, view, obj=None):
        if request.user:
            for permission_check in self.get_permission_checks(request, view):
                if not permission_check(request, view, obj):
                    return False
            return True
        return False

    # needs to be compatible to django-rest-framework
    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view, obj)


class IsStaffPermission(BasePermission):
    '''
    It ensures that the user is authenticated and is a staff member.
    '''
    permissions = (
        is_authenticated,
        is_staff)


class IsSuperuserPermission(BasePermission):
    '''
    It ensures that the user is authenticated and is a superuser. However it
    does not check if the user is a staff member.
    '''
    permissions = (
        is_authenticated,
        is_superuser)


# TODO: needs documentation
# TODO: needs integration into the REST API
class ModelPermission(BasePermission):
    '''
    Checks if the necessary model permissions are set for the accessed object.
    '''
    # Map methods into required permission codes.
    # Override this if you need to also provide 'view' permissions,
    # or if you want to provide custom permission checks.
    permissions_for_method = {
        'GET': (),
        'OPTIONS': (),
        'HEAD': (),
        'POST': (model_permission('{app_label}.add_{model_name}'),),
        'PUT': (model_permission('{app_label}.change_{model_name}'),),
        'PATCH': (model_permission('{app_label}.change_{model_name}'),),
        'DELETE': (model_permission('{app_label}.delete_{model_name}'),),
    }


class ModelViewPermission(BasePermission):
    '''
    Checks if the user has the ``<app>.view_<model>`` permission.
    '''
    permissions = (model_permission('{app_label}.view_{model_name}'),)


class ModelAddPermission(BasePermission):
    '''
    Checks if the user has the ``<app>.add_<model>`` permission.
    '''
    permissions = (model_permission('{app_label}.add_{model_name}'),)


class ModelChangePermission(BasePermission):
    '''
    Checks if the user has the ``<app>.change_<model>`` permission.
    '''
    permissions = (model_permission('{app_label}.change_{model_name}'),)


class ModelDeletePermission(BasePermission):
    '''
    Checks if the user has the ``<app>.delete_<model>`` permission.
    '''
    permissions = (model_permission('{app_label}.delete_{model_name}'),)


class TemplatePermissionChecker(object):
    '''
    Can be used in the template like:

    .. code-block:: html+django

        {{ permissions.has_view_permission }}
        {{ permissions.has_add_permission }}
        {{ permissions.has_change_permission }}
        {{ permissions.has_delete_permission }}
        {{ permissions.blog_post.has_view_permission }}
        {{ permissions.blog_comment.has_add_permission }}

    So in general:

    .. code-block:: html+django

        {{ permissions.has_<view_name>_permission }}
        {{ permissions.<object admin name>.has_<view name>_permission }}

    And using object-level permissions:

    .. code-block:: html+django

        {% load admin2_tags %}
        {{ permissions.has_delete_permission|for_object:object }}
        {% with permissions|for_object:object as object_permissions %}
            {{ object_permissions.has_delete_permission }}
        {% endwith %}

    And dynamically checking the permissions on a different admin:

    .. code-block:: html+django

        {% load admin2_tags %}
        {% for admin in list_of_model_admins %}
            {% with permissions|for_admin:admin as permissions %}
                {{ permissions.has_delete_permission }}
            {% endwith %}
        {% endfor %}

    If you don't know the permission you want to check at compile time (e.g.
    you cannot put ``has_add_permission`` in the template because the exact
    permission name might be passed into the context dynamically) you can bind
    the view name with the ``for_view`` filter:

    .. code-block:: html+django

        {% load admin2_tags %}
        {% with "add" as view_name %}
            {% if permissions|for_view:view_name %}
                <a href="...">{{ view_name|capfirst }} model</a>
            {% endif %}
        {% endwith %}

    The attribute access of ``has_<view name>_permission`` will check for the
    permissions of the view on the currently bound model admin not with the
    name ``<view name>``, but with the name that the ``view_name_mapping``
    returns for it. That step is needed since ``add`` is not the real
    attribute name in which the ``ModelAddFormView`` on the model admin lives.

    In the future we might get rid of that and this will also make it possible
    to check for any view assigned to the admin, like
    ``{{ permissions.auth_user.has_change_password_permission }}``. But this
    needs an interface beeing implemented like suggested in:
    https://github.com/twoscoops/django-admin2/issues/142
    '''
    _has_named_permission_regex = re.compile('^has_(?P<name>\w+)_permission$')

    view_name_mapping = {
        'view': 'detail_view',
        'add': 'create_view',
        'change': 'update_view',
        'delete': 'delete_view',
    }

    def __init__(self, request, model_admin, view=None, obj=None):
        self._request = request
        self._model_admin = model_admin
        self._view = view
        self._obj = obj

    def clone(self):
        return self.__class__(
            request=self._request,
            model_admin=self._model_admin,
            view=self._view,
            obj=self._obj)

    def bind_admin(self, admin):
        '''
        Return a clone of the permission wrapper with a new model_admin bind
        to it.
        '''
        if isinstance(admin, six.string_types):
            try:
                admin = self._model_admin.admin.get_admin_by_name(admin)
            except ValueError:
                return ''
        new_permissions = self.clone()
        new_permissions._view = None
        new_permissions._model_admin = admin
        return new_permissions

    def bind_view(self, view):
        '''
        Return a clone of the permission wrapper with a new view bind to it.
        '''
        if isinstance(view, six.string_types):
            if view not in self.view_name_mapping:
                return ''
            view_name = self.view_name_mapping[view]
            view = getattr(self._model_admin, view_name).view
        # we don't support binding view classes yet, only the name of views
        # are processed. We have the problem with view classes that we cannot
        # tell which model admin it was attached to.
        else:
            return ''
        # if view is a class and not instantiated yet, do it!
        if isinstance(view, type):
            view = view(
                request=self._request,
                **self._model_admin.get_default_view_kwargs())
        new_permissions = self.clone()
        new_permissions._view = view
        return new_permissions

    def bind_object(self, obj):
        '''
        Return a clone of the permission wrapper with a new object bind
        to it for object-level permissions.
        '''
        new_permissions = self.clone()
        new_permissions._obj = obj
        return new_permissions

    #########################################
    # interface exposed to the template users

    def __getitem__(self, key):
        match = self._has_named_permission_regex.match(key)
        if match:
            # the key was a has_*_permission, so bind the correspodning view
            view_name = match.groupdict()['name']
            return self.bind_view(view_name)
        # the name might be a named object admin. So get that one and bind it
        # to the permission checking
        try:
            admin_site = self._model_admin.admin
            model_admin = admin_site.get_admin_by_name(key)
        except ValueError:
            raise KeyError
        return self.bind_admin(model_admin)

    def __nonzero__(self):
        # if no view is bound we will return false, since we don't know which
        # permission to check we stay save in disallowing the access
        if self._view is None:
            return False
        if self._obj is None:
            return self._view.has_permission()
        else:
            return self._view.has_permission(self._obj)

    def __unicode__(self):
        if self._view is None:
            return ''
        return unicode(bool(self))


def create_view_permissions(app, created_models, verbosity, **kwargs):
    """
    Create 'view' permissions for all models.

    ``django.contrib.auth`` only creates add, change and delete permissions.
    Since we want to support read-only views, we need to add our own
    permission.

    Copied from ``django.contrib.auth.management.create_permissions``.
    """
    # Is there any reason for doing this import here?

    app_models = get_models(app)

    # This will hold the permissions we're looking for as
    # (content_type, (codename, name))
    searched_perms = list()
    # The codenames and ctypes that should exist.
    ctypes = set()
    for klass in app_models:
        ctype = contenttypes_models.ContentType.objects.get_for_model(klass)
        ctypes.add(ctype)

        opts = utils.model_options(klass)
        perm = ('view_%s' % opts.object_name.lower(), u'Can view %s' % opts.verbose_name_raw)
        searched_perms.append((ctype, perm))

    # Find all the Permissions that have a content_type for a model we're
    # looking for.  We don't need to check for codenames since we already have
    # a list of the ones we're going to create.
    all_perms = set(auth_models.Permission.objects.filter(
        content_type__in=ctypes,
    ).values_list(
        "content_type", "codename"
    ))

    perms = [
        auth_models.Permission(codename=codename, name=name, content_type=ctype)
        for ctype, (codename, name) in searched_perms
        if (ctype.pk, codename) not in all_perms
    ]
    auth_models.Permission.objects.bulk_create(perms)
    if verbosity >= 2:
        for perm in perms:
            logger.info("Adding permission '%s'" % perm)

########NEW FILE########
__FILENAME__ = renderers
# -*- coding: utf-8 -*-
"""
There are currently a few renderers that come directly with django-admin2. They
are used by default for some field types.
"""
from __future__ import division, absolute_import, unicode_literals

import os.path
from datetime import date, time, datetime

from django.db import models
from django.utils import formats, timezone
from django.template.loader import render_to_string

from djadmin2 import settings


def boolean_renderer(value, field):
    """
    Render a boolean value as icon.

    This uses the template ``renderers/boolean.html``.

    :param value: The value to process.
    :type value: boolean
    :param field: The model field instance
    :type field: django.db.models.fields.Field
    :rtype: unicode

    """
    # TODO caching of template
    tpl = os.path.join(settings.ADMIN2_THEME_DIRECTORY, 'renderers/boolean.html')
    return render_to_string(tpl, {'value': value})


def datetime_renderer(value, field):
    """
    Localize and format the specified date.

    :param value: The value to process.
    :type value: datetime.date or datetime.time or datetime.datetime
    :param field: The model field instance
    :type field: django.db.models.fields.Field
    :rtype: unicode

    """
    if isinstance(value, datetime):
        return formats.localize(timezone.template_localtime(value))
    elif isinstance(value, (date, time)):
        return formats.localize(value)
    else:
        return value


def title_renderer(value, field):
    """
    Render a string in title case (capitalize every word).

    :param value: The value to process.
    :type value: str or unicode
    :param field: The model field instance
    :type field: django.db.models.fields.Field
    :rtype: unicode

    """
    return unicode(value).title()


def number_renderer(value, field):
    """
    Format a number.

    :param value: The value to process.
    :type value: float or long
    :param field: The model field instance
    :type field: django.db.models.fields.Field
    :rtype: unicode

    """
    if isinstance(field, models.DecimalField):
        return formats.number_format(value, field.decimal_places)
    return formats.number_format(value)

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, unicode_literals

from django.conf import settings


# Restricts the attributes that are passed from ModelAdmin2 classes to their
#   views. This is a security feature.
# See the docstring on djadmin2.types.ModelAdmin2 for more detail.
MODEL_ADMIN_ATTRS = (
    'actions_selection_counter', "date_hierarchy", 'list_display',
    'list_display_links', 'list_filter', 'admin', 'search_fields',
    'field_renderers', 'index_view', 'detail_view', 'create_view',
    'update_view', 'delete_view', 'get_default_view_kwargs',
    'get_list_actions', 'get_ordering', 'actions_on_bottom', 'actions_on_top',
    'ordering', 'save_on_top', 'save_on_bottom', 'readonly_fields', )

ADMIN2_THEME_DIRECTORY = getattr(settings, "ADMIN2_THEME_DIRECTORY", "djadmin2theme_default")

########NEW FILE########
__FILENAME__ = admin2_tags
# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, unicode_literals

from numbers import Number
from datetime import date, time, datetime

from django import template
from django.db.models.fields import FieldDoesNotExist

from .. import utils, renderers, models


register = template.Library()


@register.filter
def admin2_urlname(view, action):
    """
    Converts the view and the specified action into a valid namespaced URLConf name.
    """
    return utils.admin2_urlname(view, action)


@register.filter
def model_app_label(obj):
    """
    Returns the app label of a model instance or class.
    """
    return utils.model_app_label(obj)


@register.filter
def model_verbose_name(obj):
    """
    Returns the verbose name of a model instance or class.
    """
    return utils.model_verbose_name(obj)


@register.filter
def model_verbose_name_plural(obj):
    """
    Returns the pluralized verbose name of a model instance or class.
    """
    return utils.model_verbose_name_plural(obj)


@register.filter
def verbose_name_for(verbose_names, app_label):
    """
    Returns the verbose name of an app.
    """
    return verbose_names.get(app_label, None)


@register.filter
def model_attr_verbose_name(obj, attr):
    """
    Returns the verbose name of a model field or method.
    """
    try:
        return utils.model_field_verbose_name(obj, attr)
    except FieldDoesNotExist:
        return utils.model_method_verbose_name(obj, attr)


@register.filter
def formset_visible_fieldlist(formset):
    """
    Returns the labels of a formset's visible fields as an array.
    """
    return [f.label for f in formset.forms[0].visible_fields()]


@register.filter
def for_admin(permissions, admin):
    """
    Only useful in the permission handling. This filter binds a new admin to
    the permission handler to allow checking views of an arbitrary admin.
    """
    # some permission check has failed earlier, so we don't bother trying to
    # bind a new admin to it.
    if permissions == '':
        return permissions
    return permissions.bind_admin(admin)


@register.filter
def for_view(permissions, view):
    """
    Only useful in the permission handling. This filter binds a new view to
    the permission handler to check for view names that are not known during
    template compile time.
    """
    # some permission check has failed earlier, so we don't bother trying to
    # bind a new admin to it.
    if permissions == '':
        return permissions
    return permissions.bind_view(view)


@register.filter
def for_object(permissions, obj):
    """
    Only useful in the permission handling. This filter binds a new object to
    the permission handler to check for object-level permissions.
    """
    # some permission check has failed earlier, so we don't bother trying to
    # bind a new object to it.
    if permissions == '':
        return permissions
    return permissions.bind_object(obj)


@register.simple_tag(takes_context=True)
def render(context, model_instance, attribute_name):
    """
    This filter applies all renderers specified in admin2.py to the field.
    """
    value = utils.get_attr(model_instance, attribute_name)

    # Get renderer
    admin = context['view'].model_admin
    renderer = admin.field_renderers.get(attribute_name, False)
    if renderer is None:
        # Renderer has explicitly been overridden
        return value
    if not renderer:
        # Try to automatically pick best renderer
        if isinstance(value, bool):
            renderer = renderers.boolean_renderer
        elif isinstance(value, (date, time, datetime)):
            renderer = renderers.datetime_renderer
        elif isinstance(value, Number):
            renderer = renderers.number_renderer
        else:
            return value

    # Apply renderer and return value
    try:
        field = model_instance._meta.get_field_by_name(attribute_name)[0]
    except FieldDoesNotExist:
        # There is no field with the specified name.
        # It must be a method instead.
        field = None
    return renderer(value, field)


@register.inclusion_tag('djadmin2theme_default/includes/history.html',
                        takes_context=True)
def action_history(context):
    actions = models.LogEntry.objects.filter(user__pk=context['user'].pk)
    return {'actions': actions}

########NEW FILE########
__FILENAME__ = test_actions
from django.db import models
from django.test import TestCase

from ..core import Admin2
from ..actions import get_description


class Thing(models.Model):
    pass


class TestAction(object):
    description = "Test Action Class"


def test_function():
    pass


class ActionTest(TestCase):
    def setUp(self):
        self.admin2 = Admin2()

    def test_action_description(self):
        self.admin2.register(Thing)
        self.admin2.registry[Thing].list_actions.extend([
            TestAction,
            test_function,
            ])
        self.assertEquals(
            get_description(
                self.admin2.registry[Thing].list_actions[0]
                ),
            'Delete selected items'
            )
        self.assertEquals(
            get_description(
                self.admin2.registry[Thing].list_actions[1]
                ),
            'Test Action Class'
            )
        self.assertEquals(
            get_description(
                self.admin2.registry[Thing].list_actions[2]
                ),
            'Test function'
            )
        self.admin2.registry[Thing].list_actions.remove(TestAction)
        self.admin2.registry[Thing].list_actions.remove(test_function)

########NEW FILE########
__FILENAME__ = test_admin2tags
from django.db import models
from django import forms
from django.forms.formsets import formset_factory
from django.test import TestCase

from ..templatetags import admin2_tags
from ..views import IndexView


class TagsTestsModel(models.Model):

    field1 = models.CharField(max_length=23)
    field2 = models.CharField('second field', max_length=42)

    def was_published_recently(self):
        return True
    was_published_recently.boolean = True
    was_published_recently.short_description = 'Published recently?'

    class Meta:
        verbose_name = "Tags Test Model"
        verbose_name_plural = "Tags Test Models"


class TagsTestForm(forms.Form):
    visible_1 = forms.CharField()
    visible_2 = forms.CharField()
    invisible_1 = forms.HiddenInput()


TagsTestFormSet = formset_factory(TagsTestForm)


class TagsTests(TestCase):

    def setUp(self):
        self.instance = TagsTestsModel()

    def test_admin2_urlname(self):
        self.assertEquals(
            "admin2:None_None_index",
            admin2_tags.admin2_urlname(IndexView, "index")
        )

    def test_model_verbose_name_as_model_class(self):
        self.assertEquals(
            TagsTestsModel._meta.verbose_name,
            admin2_tags.model_verbose_name(TagsTestsModel)
        )

    def test_model_verbose_name_as_model_instance(self):
        self.assertEquals(
            self.instance._meta.verbose_name,
            admin2_tags.model_verbose_name(self.instance)
        )

    def test_model_verbose_name_plural_as_model_class(self):
        self.assertEquals(
            TagsTestsModel._meta.verbose_name_plural,
            admin2_tags.model_verbose_name_plural(TagsTestsModel)
        )

    def test_model_verbose_name_plural_as_model_instance(self):
        self.assertEquals(
            self.instance._meta.verbose_name_plural,
            admin2_tags.model_verbose_name_plural(self.instance)
        )

    def test_model_field_verbose_name_autogenerated(self):
        self.assertEquals(
            'field1',
            admin2_tags.model_attr_verbose_name(self.instance, 'field1')
        )

    def test_model_field_verbose_name_overridden(self):
        self.assertEquals(
            'second field',
            admin2_tags.model_attr_verbose_name(self.instance, 'field2')
        )

    def test_model_method_verbose_name(self):
        self.assertEquals(
            'Published recently?',
            admin2_tags.model_attr_verbose_name(self.instance, 'was_published_recently')
        )

    def test_formset_visible_fieldlist(self):
        formset = TagsTestFormSet()
        self.assertEquals(
            admin2_tags.formset_visible_fieldlist(formset),
            [u'Visible 1', u'Visible 2']
        ) 

    def test_verbose_name_for(self):
        app_verbose_names = {
            u'app_one_label': 'App One Verbose Name',
        }
        self.assertEquals(
            "App One Verbose Name",
            admin2_tags.verbose_name_for(app_verbose_names, 'app_one_label')
        )

########NEW FILE########
__FILENAME__ = test_auth_admin
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import RequestFactory

import floppyforms

import djadmin2
from ..admin2 import UserAdmin2


class UserAdminTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User(
            username='admin',
            is_staff=True,
            is_superuser=True)
        self.user.set_password('admin')
        self.user.save()

    def test_create_form_uses_floppyform_widgets(self):
        form = UserAdmin2.create_form_class()
        self.assertTrue(
            isinstance(form.fields['username'].widget,
                       floppyforms.TextInput))

        request = self.factory.get(reverse('admin2:auth_user_create'))
        request.user = self.user
        model_admin = UserAdmin2(User, djadmin2.default)
        view = model_admin.create_view.view.as_view(
            **model_admin.get_create_kwargs())
        response = view(request)
        form = response.context_data['form']
        self.assertTrue(
            isinstance(form.fields['username'].widget,
                       floppyforms.TextInput))

    def test_update_form_uses_floppyform_widgets(self):
        form = UserAdmin2.update_form_class()
        self.assertTrue(
            isinstance(form.fields['username'].widget,
                       floppyforms.TextInput))
        self.assertTrue(
            isinstance(form.fields['date_joined'].widget,
                       floppyforms.DateTimeInput))

        request = self.factory.get(
            reverse('admin2:auth_user_update', args=(self.user.pk,)))
        request.user = self.user
        model_admin = UserAdmin2(User, djadmin2.default)
        view = model_admin.update_view.view.as_view(
            **model_admin.get_update_kwargs())
        response = view(request, pk=self.user.pk)
        form = response.context_data['form']
        self.assertTrue(
            isinstance(form.fields['username'].widget,
                       floppyforms.TextInput))
        self.assertTrue(
            isinstance(form.fields['date_joined'].widget,
                       floppyforms.DateTimeInput))

########NEW FILE########
__FILENAME__ = test_core
from django.db import models
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.contrib.auth.models import Group, User
from django.contrib.sites.models import Site

import djadmin2
from ..types import ModelAdmin2
from ..core import Admin2


class Thing(models.Model):
    pass


APP_LABEL, APP_VERBOSE_NAME = 'app_one_label', 'App One Verbose Name'


class Admin2Test(TestCase):
    def setUp(self):
        self.admin2 = Admin2()

    def test_register(self):
        self.admin2.register(Thing)
        self.assertTrue(isinstance(self.admin2.registry[Thing], ModelAdmin2))

    def test_register_error(self):
        self.admin2.register(Thing)
        self.assertRaises(ImproperlyConfigured, self.admin2.register, Thing)

    def test_deregister(self):
        self.admin2.register(Thing)
        self.admin2.deregister(Thing)
        self.assertTrue(Thing not in self.admin2.registry)

    def test_deregister_error(self):
        self.assertRaises(ImproperlyConfigured, self.admin2.deregister, Thing)

    def test_register_app_verbose_name(self):
        self.admin2.register_app_verbose_name(APP_LABEL, APP_VERBOSE_NAME)
        self.assertEquals(
            self.admin2.app_verbose_names[APP_LABEL],
            APP_VERBOSE_NAME
        )

    def test_register_app_verbose_name_error(self):
        self.admin2.register_app_verbose_name(APP_LABEL, APP_VERBOSE_NAME)
        self.assertRaises(
            ImproperlyConfigured,
            self.admin2.register_app_verbose_name,
            APP_LABEL,
            APP_VERBOSE_NAME
        )

    def test_deregister_app_verbose_name(self):
        self.admin2.register_app_verbose_name(APP_LABEL, APP_VERBOSE_NAME)
        self.admin2.deregister_app_verbose_name(APP_LABEL)
        self.assertTrue(APP_LABEL not in self.admin2.app_verbose_names)

    def test_deregister_app_verbose_name_error(self):
        self.assertRaises(
            ImproperlyConfigured,
            self.admin2.deregister_app_verbose_name,
            APP_LABEL
        )

    def test_get_urls(self):
        self.admin2.register(Thing)
        self.assertEquals(8, len(self.admin2.get_urls()))

    def test_default_entries(self):
        expected_default_models = (User, Group, Site)
        for model in expected_default_models:
            self.assertTrue(isinstance(djadmin2.default.registry[model], ModelAdmin2))

########NEW FILE########
__FILENAME__ = test_renderers
# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, unicode_literals

import datetime as dt
from decimal import Decimal

from django.test import TestCase
from django.db import models
from django.utils.translation import activate

from .. import renderers


class RendererTestModel(models.Model):
    decimal = models.DecimalField(decimal_places=5)


class BooleanRendererTest(TestCase):
    
    def setUp(self):
        self.renderer = renderers.boolean_renderer

    def test_boolean(self):
        out1 = self.renderer(True, None)
        self.assertIn('icon-ok-sign', out1)
        out2 = self.renderer(False, None)
        self.assertIn('icon-minus-sign', out2)

    def test_string(self):
        out1 = self.renderer('yeah', None)
        self.assertIn('icon-ok-sign', out1)
        out2 = self.renderer('', None)
        self.assertIn('icon-minus-sign', out2)


class DatetimeRendererTest(TestCase):

    def setUp(self):
        self.renderer = renderers.datetime_renderer

    def tearDown(self):
        activate('en_US')

    def test_date_german(self):
        activate('de')
        out = self.renderer(dt.date(2013, 7, 6), None)
        self.assertEqual('6. Juli 2013', out)

    def test_date_spanish(self):
        activate('es')
        out = self.renderer(dt.date(2013, 7, 6), None)
        self.assertEqual('6 de Julio de 2013', out)

    def test_date_default(self):
        out = self.renderer(dt.date(2013, 7, 6), None)
        self.assertEqual('July 6, 2013', out)

    def test_time_german(self):
        activate('de')
        out = self.renderer(dt.time(13, 37, 01), None)
        self.assertEqual('13:37:01', out)

    def test_time_chinese(self):
        activate('zh')
        out = self.renderer(dt.time(13, 37, 01), None)
        self.assertEqual('1:37 p.m.', out)

    def test_datetime(self):
        out = self.renderer(dt.datetime(2013, 7, 6, 13, 37, 01), None)
        self.assertEqual('July 6, 2013, 1:37 p.m.', out)

    # TODO test timezone localization


class TitleRendererTest(TestCase):

    def setUp(self):
        self.renderer = renderers.title_renderer

    def testLowercase(self):
        out = self.renderer('oh hello there!', None)
        self.assertEqual('Oh Hello There!', out)

    def testTitlecase(self):
        out = self.renderer('Oh Hello There!', None)
        self.assertEqual('Oh Hello There!', out)

    def testUppercase(self):
        out = self.renderer('OH HELLO THERE!', None)
        self.assertEqual('Oh Hello There!', out)


class NumberRendererTest(TestCase):

    def setUp(self):
        self.renderer = renderers.number_renderer

    def testInteger(self):
        out = self.renderer(42, None)
        self.assertEqual('42', out)

    def testFloat(self):
        out = self.renderer(42.5, None)
        self.assertEqual('42.5', out)

    def testEndlessFloat(self):
        out = self.renderer(1.0/3, None)
        self.assertEqual('0.333333333333', out)

    def testPlainDecimal(self):
        number = '0.123456789123456789123456789'
        out = self.renderer(Decimal(number), None)
        self.assertEqual(number, out)

    def testFieldDecimal(self):
        field = RendererTestModel._meta.get_field_by_name('decimal')[0]
        out = self.renderer(Decimal('0.123456789'), field)
        self.assertEqual('0.12345', out)

########NEW FILE########
__FILENAME__ = test_types
from django.db import models
from django.test import TestCase
from django.views.generic import View

from .. import views
from ..types import ModelAdmin2, immutable_admin_factory
from ..core import Admin2


class ModelAdmin(object):
    model_admin_attributes = ['a', 'b', 'c']
    a = 1  # covered
    b = 2  # covered
    c = 3  # covered
    d = 4  # not covered


class ImmutableAdminFactoryTests(TestCase):

    def setUp(self):
        self.immutable_admin = immutable_admin_factory(ModelAdmin)

    def test_immutability(self):
        with self.assertRaises(AttributeError):
            # can't set attribute
            self.immutable_admin.a = 10
        with self.assertRaises(AttributeError):
            # 'ImmutableAdmin' object has no attribute 'e'
            self.immutable_admin.e = 5
        with self.assertRaises(AttributeError):
            # can't delete attribute
            del self.immutable_admin.a

    def test_attributes(self):
        self.assertEquals(self.immutable_admin.a, 1)
        self.assertEquals(self.immutable_admin.b, 2)
        self.assertEquals(self.immutable_admin.c, 3)
        with self.assertRaises(AttributeError):
            # 'ImmutableAdmin' object has no attribute 'd'
            self.immutable_admin.d


class Thing(models.Model):
    pass


class ModelAdminTest(TestCase):

    def setUp(self):
        class MyModelAdmin(ModelAdmin2):
            my_view = views.AdminView(r'^$', views.ModelListView)

        self.model_admin = MyModelAdmin

    def test_views(self):
        self.assertIn(
            self.model_admin.my_view,
            self.model_admin.views
        )

    def test_get_index_kwargs(self):
        admin_instance = ModelAdmin2(Thing, Admin2)
        self.assertIn(
            'paginate_by',
            admin_instance.get_index_kwargs().keys()
        )

########NEW FILE########
__FILENAME__ = test_utils
from django.db import models
from django.test import TestCase

from .. import utils
from ..views import IndexView


class UtilsTestModel(models.Model):

    field1 = models.CharField(max_length=23)
    field2 = models.CharField('second field', max_length=42)

    def simple_method(self):
        return 42

    def was_published_recently(self):
        return True
    was_published_recently.boolean = True
    was_published_recently.short_description = 'Published recently?'

    class Meta:
        verbose_name = "Utils Test Model"
        verbose_name_plural = "Utils Test Models"


class UtilsTest(TestCase):

    def setUp(self):
        self.instance = UtilsTestModel()

    def test_as_model_class(self):
        self.assertEquals(
            UtilsTestModel._meta,
            utils.model_options(UtilsTestModel)
        )
        UtilsTestModel._meta.verbose_name = "Utils Test Model is singular"
        UtilsTestModel._meta.verbose_name_plural = "Utils Test Model are " +\
            " plural"
        self.assertEquals(
            UtilsTestModel._meta,
            utils.model_options(UtilsTestModel)
            )
        UtilsTestModel._meta.verbose_name = "Utils Test Model"
        UtilsTestModel._meta.verbose_name_plural = "Utils Test Models"

    def test_as_model_instance(self):
        self.assertEquals(
            self.instance._meta,
            utils.model_options(self.instance)
        )
        self.instance._meta.verbose_name = "Utils Test Model is singular"
        self.instance._meta.verbose_name_plural = "Utils Test Model are " +\
            " plural"
        self.assertEquals(
            self.instance._meta,
            utils.model_options(self.instance)
            )
        self.instance._meta.verbose_name = "Utils Test Model"
        self.instance._meta.verbose_name_plural = "Utils Test Models"

    def test_admin2_urlname(self):
        self.assertEquals(
            "admin2:None_None_index",
            utils.admin2_urlname(IndexView, "index")
        )

    def test_model_app_label_as_model_class(self):
        self.assertEquals(
            UtilsTestModel._meta.app_label,
            utils.model_app_label(UtilsTestModel)
        )

    def test_model_app_label_as_model_instance(self):
        self.assertEquals(
            self.instance._meta.app_label,
            utils.model_app_label(UtilsTestModel)
        )

    def test_model_verbose_name_as_model_class(self):
        self.assertEquals(
            UtilsTestModel._meta.verbose_name,
            utils.model_verbose_name(UtilsTestModel)
        )

    def test_model_verbose_name_as_model_instance(self):
        self.assertEquals(
            self.instance._meta.verbose_name,
            utils.model_verbose_name(self.instance)
        )

    def test_model_verbose_name_plural_as_model_class(self):
        self.assertEquals(
            UtilsTestModel._meta.verbose_name_plural,
            utils.model_verbose_name_plural(UtilsTestModel)
        )

    def test_model_verbose_name_plural_as_model_instance(self):
        self.assertEquals(
            self.instance._meta.verbose_name_plural,
            utils.model_verbose_name_plural(self.instance)
        )

    def test_model_field_verbose_name_autogenerated(self):
        self.assertEquals(
            'field1',
            utils.model_field_verbose_name(self.instance, 'field1')
        )

    def test_model_field_verbose_name_overridden(self):
        self.assertEquals(
            'second field',
            utils.model_field_verbose_name(self.instance, 'field2')
        )

    def test_model_method_verbose_name(self):
        self.assertEquals(
            'Published recently?',
            utils.model_method_verbose_name(self.instance, 'was_published_recently')
        )

    def test_model_method_verbose_name_fallback(self):
        self.assertEquals(
            'simple_method',
            utils.model_method_verbose_name(self.instance, 'simple_method')
        )

    def test_app_label_as_model_class(self):
        self.assertEquals(
            UtilsTestModel._meta.app_label,
            utils.model_app_label(UtilsTestModel)
        )

    def test_app_label_as_model_instance(self):
        self.assertEquals(
            self.instance._meta.app_label,
            utils.model_app_label(self.instance)
        )

    def test_get_attr_callable(self):
        class Klass(object):
            def hello(self):
                return "hello"

        self.assertEquals(
            utils.get_attr(Klass(), "hello"),
            "hello"
        )

    def test_get_attr_str(self):
        class Klass(object):
            def __str__(self):
                return "str"

            def __unicode__(self):
                return "unicode"

        self.assertEquals(
            utils.get_attr(Klass(), "__str__"),
            "unicode"
        )

    def test_get_attr(self):
        class Klass(object):
            attr = "value"

        self.assertEquals(
            utils.get_attr(Klass(), "attr"),
            "value"
        )

########NEW FILE########
__FILENAME__ = test_views
from django.test import TestCase
from django.views.generic import View

from .. import views


class AdminViewTest(TestCase):

    def setUp(self):
        self.admin_view = views.AdminView(r'^$', views.ModelListView, name='admin-view')

    def test_url(self):
        self.assertEquals(self.admin_view.url, r'^$')

    def test_view(self):
        self.assertEquals(self.admin_view.view, views.ModelListView)

    def test_name(self):
        self.assertEquals(self.admin_view.name, 'admin-view')

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = types
# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, unicode_literals

from collections import namedtuple
import logging
import os
import sys

from django.core.urlresolvers import reverse
from django.conf.urls import patterns, url
from django.utils.six import with_metaclass

import extra_views

from . import apiviews
from . import settings
from . import views
from . import actions
from . import utils
from .forms import modelform_factory


logger = logging.getLogger('djadmin2')


class ModelAdminBase2(type):

    def __new__(cls, name, bases, attrs):
        new_class = super(ModelAdminBase2, cls).__new__(cls, name,
                                                        bases, attrs)
        view_list = getattr(new_class, 'views', [])

        for key, value in attrs.items():
            if isinstance(value, views.AdminView):
                if not value.name:
                    value.name = key
                view_list.append(value)

        setattr(new_class, 'views', view_list)
        return new_class


class ModelAdmin2(with_metaclass(ModelAdminBase2)):
    """
    Adding new ModelAdmin2 attributes:

        Step 1: Add the attribute to this class
        Step 2: Add the attribute to djadmin2.settings.MODEL_ADMIN_ATTRS

        Reasoning:

            Changing values on ModelAdmin2 objects or their attributes from
            within a view results in leaky scoping issues. Therefore, we use
            the immutable_admin_factory to render the ModelAdmin2 class
            practically immutable before passing it to the view. To constrain
            things further (in order to protect ourselves from causing
            hard-to-find security problems), we also restrict which attrs are
            passed to the final ImmutableAdmin object (i.e. a namedtuple).
            This prevents us from easily implementing methods/setters which
            bypass the blocking features of the ImmutableAdmin.
    """
    actions_selection_counter = True
    date_hierarchy = False
    list_display = ('__str__',)
    list_display_links = ()
    list_filter = ()
    list_select_related = False
    list_per_page = 100
    list_max_show_all = 200
    list_editable = ()
    search_fields = ()
    save_as = False
    save_on_top = False
    verbose_name = None
    verbose_name_plural = None
    model_admin_attributes = settings.MODEL_ADMIN_ATTRS
    ordering = False
    save_on_top = False
    save_on_bottom = True

    # Not yet implemented. See #267 and #268
    actions_on_bottom = False
    actions_on_top = True

    search_fields = []

    # Show the fields to be displayed as columns
    # TODO: Confirm that this is what the Django admin uses
    list_fields = []

    # This shows up on the DocumentListView of the Posts
    list_actions = [actions.DeleteSelectedAction]

    # This shows up in the DocumentDetailView of the Posts.
    document_actions = []

    # Shows up on a particular field
    field_actions = {}

    # Defines custom field renderers
    field_renderers = {}

    fields = None
    exclude = None
    fieldsets = None
    form_class = None
    filter_vertical = ()
    filter_horizontal = ()
    radio_fields = {}
    prepopulated_fields = {}
    formfield_overrides = {}
    readonly_fields = ()
    ordering = None

    create_form_class = None
    update_form_class = None

    inlines = []

    #  Views
    index_view = views.AdminView(r'^$', views.ModelListView, name='index')
    create_view = views.AdminView(r'^create/$', views.ModelAddFormView, name='create')
    update_view = views.AdminView(r'^(?P<pk>[0-9]+)/$', views.ModelEditFormView, name='update')
    detail_view = views.AdminView(r'^(?P<pk>[0-9]+)/update/$', views.ModelDetailView, name='detail')
    delete_view = views.AdminView(r'^(?P<pk>[0-9]+)/delete/$', views.ModelDeleteView, name='delete')
    history_view = views.AdminView(r'^(?P<pk>[0-9]+)/history/$', views.ModelHistoryView, name='history')
    views = []

    # API configuration
    api_serializer_class = None

    # API Views
    api_list_view = apiviews.ListCreateAPIView
    api_detail_view = apiviews.RetrieveUpdateDestroyAPIView

    def __init__(self, model, admin, name=None, **kwargs):
        self.name = name
        self.model = model
        self.admin = admin
        model_options = utils.model_options(model)
        self.app_label = model_options.app_label
        self.model_name = model_options.object_name.lower()

        if self.name is None:
            self.name = '{}_{}'.format(self.app_label, self.model_name)

        if self.verbose_name is None:
            self.verbose_name = model_options.verbose_name
        if self.verbose_name_plural is None:
            self.verbose_name_plural = model_options.verbose_name_plural

    def get_default_view_kwargs(self):
        return {
            'app_label': self.app_label,
            'model': self.model,
            'model_name': self.model_name,
            'model_admin': immutable_admin_factory(self),
        }

    def get_index_kwargs(self):
        kwargs = self.get_default_view_kwargs()
        kwargs.update({
            'paginate_by': self.list_per_page,
        })
        return kwargs

    def get_default_api_view_kwargs(self):
        kwargs = self.get_default_view_kwargs()
        kwargs.update({
            'serializer_class': self.api_serializer_class,
        })
        return kwargs

    def get_prefixed_view_name(self, view_name):
        return '{}_{}'.format(self.name, view_name)

    def get_create_kwargs(self):
        kwargs = self.get_default_view_kwargs()
        kwargs.update({
            'inlines': self.inlines,
            'form_class': (self.create_form_class if
                           self.create_form_class else self.form_class),
        })
        return kwargs

    def get_update_kwargs(self):
        kwargs = self.get_default_view_kwargs()
        form_class = (self.update_form_class if
                      self.update_form_class else self.form_class)
        if form_class is None:
            form_class = modelform_factory(self.model)
        kwargs.update({
            'inlines': self.inlines,
            'form_class': form_class,
        })
        return kwargs

    def get_index_url(self):
        return reverse('admin2:{}'.format(
            self.get_prefixed_view_name('index')))

    def get_api_list_kwargs(self):
        kwargs = self.get_default_api_view_kwargs()
        kwargs.update({
            'paginate_by': self.list_per_page,
        })
        return kwargs

    def get_api_detail_kwargs(self):
        return self.get_default_api_view_kwargs()

    def get_urls(self):
        pattern_list = []
        for admin_view in self.views:
            admin_view.model_admin = self
            get_kwargs = getattr(self, "get_%s_kwargs" % admin_view.name, None)
            if not get_kwargs:
                get_kwargs = admin_view.get_view_kwargs
            try:
                view_instance = admin_view.view.as_view(**get_kwargs())
            except Exception as e:
                trace = sys.exc_info()[2]
                new_exception = TypeError(
                    'Cannot instantiate admin view "{}.{}". '
                    'The error that got raised was: {}'.format(
                        self.__class__.__name__, admin_view.name, e))
                raise new_exception, None, trace
            pattern_list.append(
                url(
                    regex=admin_view.url,
                    view=view_instance,
                    name=self.get_prefixed_view_name(admin_view.name)
                )
            )
        return patterns('', *pattern_list)

    def get_api_urls(self):
        return patterns(
            '',
            url(
                regex=r'^$',
                view=self.api_list_view.as_view(**self.get_api_list_kwargs()),
                name=self.get_prefixed_view_name('api_list'),
            ),
            url(
                regex=r'^(?P<pk>[0-9]+)/$',
                view=self.api_detail_view.as_view(
                    **self.get_api_detail_kwargs()),
                name=self.get_prefixed_view_name('api_detail'),
            ),
        )

    @property
    def urls(self):
        # We set the application and instance namespace here
        return self.get_urls(), None, None

    @property
    def api_urls(self):
        return self.get_api_urls(), None, None

    def get_list_actions(self):
        actions_dict = {}

        for cls in type(self).mro()[::-1]:
            class_actions = getattr(cls, 'list_actions', [])
            for action in class_actions:
                actions_dict[action.__name__] = {
                    'name': action.__name__,
                    'description': actions.get_description(action),
                    'action_callable': action
                }
        return actions_dict

    def get_ordering(self, request):
        return self.ordering


class Admin2Inline(extra_views.InlineFormSet):
    """
    A simple extension of django-extra-view's InlineFormSet that
    adds some useful functionality.
    """
    template = None

    def construct_formset(self):
        """
        Overrides construct_formset to attach the model class as
        an attribute of the returned formset instance.
        """
        formset = super(Admin2Inline, self).construct_formset()
        formset.model = self.inline_model
        formset.template = self.template
        return formset


class Admin2TabularInline(Admin2Inline):
    template = os.path.join(
        settings.ADMIN2_THEME_DIRECTORY, 'edit_inlines/tabular.html')


class Admin2StackedInline(Admin2Inline):
    template = os.path.join(
        settings.ADMIN2_THEME_DIRECTORY, 'edit_inlines/stacked.html')


def immutable_admin_factory(model_admin):
    """
    Provide an ImmutableAdmin to make it harder for developers to
    dig themselves into holes.
    See https://github.com/twoscoops/django-admin2/issues/99
    Frozen class implementation as namedtuple suggested by Audrey Roy

    Note: This won't stop developers from saving mutable objects to
    the result, but hopefully developers attempting that
    'workaround/hack' will read our documentation.
    """
    ImmutableAdmin = namedtuple('ImmutableAdmin',
                                model_admin.model_admin_attributes,
                                verbose=False)
    return ImmutableAdmin(*[getattr(
        model_admin, x) for x in model_admin.model_admin_attributes])

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, unicode_literals

from django.db.models import ProtectedError
from django.db.models import ManyToManyRel
from django.db.models.deletion import Collector
from django.db.models.related import RelatedObject
from django.utils import six


def lookup_needs_distinct(opts, lookup_path):
    """
    Returns True if 'distinct()' should be used to query the given lookup path.

    This is adopted from the Django core. django-admin2 mandates that code
    doesn't depend on imports from django.contrib.admin.

    https://github.com/django/django/blob/1.5.1/django/contrib/admin/util.py#L20
    """
    field_name = lookup_path.split('__', 1)[0]
    field = opts.get_field_by_name(field_name)[0]
    condition1 = hasattr(field, 'rel') and isinstance(field.rel, ManyToManyRel)
    condition2 = isinstance(field, RelatedObject) and not field.field.unique
    return condition1 or condition2


def model_options(model):
    """
    Wrapper for accessing model._meta. If this access point changes in core
    Django, this function allows django-admin2 to address the change with
    what should hopefully be less disruption to the rest of the code base.

    Works on model classes and objects.
    """
    return model._meta


def admin2_urlname(view, action):
    """
    Converts the view and the specified action into a valid namespaced URLConf name.
    """
    return 'admin2:%s_%s_%s' % (view.app_label, view.model_name, action)


def model_verbose_name(model):
    """
    Returns the verbose name of a model instance or class.
    """
    return model_options(model).verbose_name


def model_verbose_name_plural(model):
    """
    Returns the pluralized verbose name of a model instance or class.
    """
    return model_options(model).verbose_name_plural


def model_field_verbose_name(model, field_name):
    """
    Returns the verbose name of a model field.
    """
    meta = model_options(model)
    field = meta.get_field_by_name(field_name)[0]
    return field.verbose_name


def model_method_verbose_name(model, method_name):
    """
    Returns the verbose name / short description of a model field.
    """
    method = getattr(model, method_name)
    try:
        return method.short_description
    except AttributeError:
        return method_name


def model_app_label(obj):
    """
    Returns the app label of a model instance or class.
    """
    return model_options(obj).app_label


def get_attr(obj, attr):
    """
    Get the right value for the attribute. Handle special cases like callables
    and the __str__ attribute.
    """
    if attr == '__str__':
        value = unicode(obj)
    else:
        attribute = getattr(obj, attr)
        value = attribute() if callable(attribute) else attribute
    return value


class NestedObjects(Collector):
    """
    This is adopted from the Django core. django-admin2 mandates that code
    doesn't depend on imports from django.contrib.admin.

    https://github.com/django/django/blob/1.5.1/django/contrib/admin/util.py#L144-L199
    """
    def __init__(self, *args, **kwargs):
        super(NestedObjects, self).__init__(*args, **kwargs)
        self.edges = {}  # {from_instance: [to_instances]}
        self.protected = set()

    def add_edge(self, source, target):
        self.edges.setdefault(source, []).append(target)

    def collect(self, objs, source_attr=None, **kwargs):
        for obj in objs:
            if source_attr:
                self.add_edge(getattr(obj, source_attr), obj)
            else:
                self.add_edge(None, obj)
        try:
            return super(NestedObjects, self).collect(
                objs, source_attr=source_attr, **kwargs)
        except ProtectedError as e:
            self.protected.update(e.protected_objects)

    def related_objects(self, related, objs):
        qs = super(NestedObjects, self).related_objects(related, objs)
        return qs.select_related(related.field.name)

    def _nested(self, obj, seen, format_callback):
        if obj in seen:
            return []
        seen.add(obj)
        children = []
        for child in self.edges.get(obj, ()):
            children.extend(self._nested(child, seen, format_callback))
        if format_callback:
            ret = [format_callback(obj)]
        else:
            ret = [obj]
        if children:
            ret.append(children)
        return ret

    def nested(self, format_callback=None):
        """
        Return the graph as a nested list.

        """
        seen = set()
        roots = []
        for root in self.edges.get(None, ()):
            roots.extend(self._nested(root, seen, format_callback))
        return roots

    def can_fast_delete(self, *args, **kwargs):
        """
        We always want to load the objects into memory so that we can display
        them to the user in confirm page.
        """
        return False


def quote(s):
    """
    Ensure that primary key values do not confuse the admin URLs by escaping
    any '/', '_' and ':' and similarly problematic characters.
    Similar to urllib.quote, except that the quoting is slightly different so
    that it doesn't get automatically unquoted by the Web browser.

    This is adopted from the Django core. django-admin2 mandates that code
    doesn't depend on imports from django.contrib.admin.

    https://github.com/django/django/blob/1.5.1/django/contrib/admin/util.py#L48-L62
    """
    if not isinstance(s, six.string_types):
        return s
    res = list(s)
    for i in range(len(res)):
        c = res[i]
        if c in """:/_#?;@&=+$,"<>%\\""":
            res[i] = '_%02X' % ord(c)
    return ''.join(res)

########NEW FILE########
__FILENAME__ = viewmixins
# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, unicode_literals

import os

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse, reverse_lazy
from django.forms.models import modelform_factory
from django.http import HttpResponseRedirect
from django.utils.encoding import force_text
from django.utils.text import get_text_list
from django.utils.translation import ugettext as _

from braces.views import AccessMixin

from . import settings, permissions
from .utils import admin2_urlname, model_options


class PermissionMixin(AccessMixin):
    do_not_call_in_templates = True
    permission_classes = (permissions.IsStaffPermission,)
    login_url = reverse_lazy('admin2:dashboard')

    def __init__(self, **kwargs):
        self.permissions = [
            permission_class()
            for permission_class in self.permission_classes]
        super(PermissionMixin, self).__init__(**kwargs)

    def has_permission(self, obj=None):
        '''
        Return ``True`` if the permission for this view shall be granted,
        ``False`` otherwise. Supports object-level permission by passing the
        related object as first argument.
        '''
        for permission in self.permissions:
            if not permission.has_permission(self.request, self, obj):
                return False
        return True

    def dispatch(self, request, *args, **kwargs):
        # Raise exception or redirect to login if user doesn't have
        # permissions.
        if not self.has_permission():
            if self.raise_exception:
                raise PermissionDenied  # return a forbidden response
            else:
                return redirect_to_login(
                    request.get_full_path(),
                    self.get_login_url(),
                    self.get_redirect_field_name())
        return super(PermissionMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(PermissionMixin, self).get_context_data(**kwargs)
        permission_checker = permissions.TemplatePermissionChecker(
            self.request, self.model_admin)
        context.update({
            'permissions': permission_checker,
        })
        return context


class Admin2Mixin(PermissionMixin):
    # are set in the ModelAdmin2 class when creating the view via
    # .as_view(...)
    model_admin = None
    model_name = None
    app_label = None

    index_path = reverse_lazy('admin2:dashboard')

    def get_template_names(self):
        return [os.path.join(
            settings.ADMIN2_THEME_DIRECTORY, self.default_template_name)]

    def get_model(self):
        return self.model

    def get_queryset(self):
        return self.get_model()._default_manager.all()

    def get_form_class(self):
        if self.form_class is not None:
            return self.form_class
        return modelform_factory(self.get_model())

    def is_user(self, request):
        return hasattr(request, 'user') and not (request.user.is_active and
                                                 request.user.is_staff)

    def dispatch(self, request, *args, **kwargs):

        if self.is_user(request):
            from .views import LoginView

            if request.path == reverse('admin2:logout'):
                return HttpResponseRedirect(self.index_path)

            if request.path == self.index_path:
                extra = {
                    'next': request.GET.get('next', self.index_path)
                }
                return LoginView().dispatch(request, extra_context=extra,
                                            *args, **kwargs)

        return super(Admin2Mixin, self).dispatch(request, *args, **kwargs)


class AdminModel2Mixin(Admin2Mixin):
    model_admin = None

    def get_context_data(self, **kwargs):
        context = super(AdminModel2Mixin, self).get_context_data(**kwargs)
        model = self.get_model()
        model_meta = model_options(model)
        app_verbose_names = self.model_admin.admin.app_verbose_names
        context.update({
            'app_label': model_meta.app_label,
            'app_verbose_name': app_verbose_names.get(model_meta.app_label),
            'model_name': model_meta.verbose_name,
            'model_name_pluralized': model_meta.verbose_name_plural
        })
        return context

    def get_model(self):
        return self.model

    def get_queryset(self):
        return self.get_model()._default_manager.all()

    def get_form_class(self):
        if self.form_class is not None:
            return self.form_class
        return modelform_factory(self.get_model())


class Admin2ModelFormMixin(object):
    def get_success_url(self):
        if '_continue' in self.request.POST:
            view_name = admin2_urlname(self, 'update')
            return reverse(view_name, kwargs={'pk': self.object.pk})

        if '_addanother' in self.request.POST:
            return reverse(admin2_urlname(self, 'create'))

        # default to index view
        return reverse(admin2_urlname(self, 'index'))

    def construct_change_message(self, request, form, formsets):
        """ Construct a change message from a changed object """
        change_message = []
        if form.changed_data:
            change_message.append(
                _('Changed {0}.'.format(
                    get_text_list(form.changed_data, _('and')))))

        if formsets:
            for formset in formsets:
                for added_object in formset.new_objects:
                    change_message.append(
                        _('Added {0} "{1}".'.format(
                            force_text(added_object._meta.verbose_name),
                            force_text(added_object))))
                for changed_object, changed_fields in formset.changed_objects:
                    change_message.append(
                        _('Changed {0} for {1} "{2}".'.format(
                            get_text_list(changed_fields, _('and')),
                            force_text(changed_object._meta.verbose_name),
                            force_text(changed_object))))
                for deleted_object in formset.deleted_objects:
                    change_message.append(
                        _('Deleted {0} "{1}".'.format(
                            force_text(deleted_object._meta.verbose_name),
                            force_text(deleted_object))))

        change_message = ' '.join(change_message)
        return change_message or _('No fields changed.')

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, unicode_literals

import operator
from datetime import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (PasswordChangeForm,
                                       AdminPasswordChangeForm)
from django.contrib.auth.views import (logout as auth_logout,
                                       login as auth_login)
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse, reverse_lazy
from django.db import models
from django.db.models.fields import FieldDoesNotExist
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.encoding import force_text
from django.utils.text import capfirst
from django.utils.translation import ugettext_lazy
from django.views import generic

import extra_views


from . import permissions, utils
from .forms import AdminAuthenticationForm
from .models import LogEntry
from .viewmixins import Admin2Mixin, AdminModel2Mixin, Admin2ModelFormMixin
from .filters import build_list_filter, build_date_filter


class AdminView(object):

    def __init__(self, url, view, name=None):
        self.url = url
        self.view = view
        self.name = name

    def get_view_kwargs(self):
        return {
            'app_label': self.model_admin.app_label,
            'model': self.model_admin.model,
            'model_name': self.model_admin.model_name,
            'model_admin': self.model_admin,
        }


class IndexView(Admin2Mixin, generic.TemplateView):
    """Context Variables

    :apps: A dictionary of apps, each app being a dictionary with keys
           being models and the value being djadmin2.types.ModelAdmin2
           objects.
    :app_verbose_names: A dictionary containing the app verbose names,
                        each item has a key being the `app_label` and
                        the value being a string, (or even a lazy
                        translation object), with the custom app name.
    """
    default_template_name = "index.html"
    registry = None
    apps = None
    app_verbose_names = None

    def get_context_data(self, **kwargs):
        data = super(IndexView, self).get_context_data(**kwargs)
        data.update({
            'apps': self.apps,
            'app_verbose_names': self.app_verbose_names,
        })
        return data


class AppIndexView(Admin2Mixin, generic.TemplateView):
    """Context Variables

    :app_label: Name of your app
    :registry: A dictionary of registered models for a given app, each
               item has a key being the model and the value being
               djadmin2.types.ModelAdmin2 objects.
    :app_verbose_names: A dictionary containing the app verbose name for
                        a given app, the item has a key being the
                        `app_label` and the value being a string, (or
                        even a lazy translation object), with the custom
                        app name.
    """
    default_template_name = "app_index.html"
    registry = None
    apps = None
    app_verbose_names = None

    def get_context_data(self, **kwargs):
        data = super(AppIndexView, self).get_context_data(**kwargs)
        app_label = self.kwargs['app_label']
        registry = self.apps[app_label]
        data.update({
            'app_label': app_label,
            'registry': registry,
            'app_verbose_names': self.app_verbose_names,
        })
        return data


class ModelListView(AdminModel2Mixin, generic.ListView):
    """Context Variables

    :is_paginated: If the page is paginated (page has a next button)
    :model: Type of object you are editing
    :model_name: Name of the object you are editing
    :app_label: Name of your app
    :app_verbose_names: A dictionary containing the app verbose name for
                        a given app, the item has a key being the
                        `app_label` and the value being a string, (or
                        even a lazy translation object), with the custom
                        app name.
    """
    default_template_name = "model_list.html"
    permission_classes = (
        permissions.IsStaffPermission,
        permissions.ModelViewPermission)

    def post(self, request):
        action_name = request.POST['action']
        action_callable = self.get_actions()[action_name]['action_callable']
        selected_model_pks = request.POST.getlist('selected_model_pk')
        if getattr(action_callable, "only_selected", True):
            queryset = self.model.objects.filter(pk__in=selected_model_pks)
        else:
            queryset = self.model.objects.all()

        #  If action_callable is a class subclassing from
        #  actions.BaseListAction then we generate the callable object.
        if hasattr(action_callable, "process_queryset"):
            response = action_callable.as_view(queryset=queryset, model_admin=self.model_admin)(request)
        else:
            # generate the reponse if a function.
            response = action_callable(request, queryset)

        if response is None:
            return HttpResponseRedirect(self.get_success_url())
        else:
            return response

    def get_search_results(self, queryset, search_term):
        # Lifted from django.contrib.admin
        def construct_search(field_name):
            if field_name.startswith('^'):
                return "%s__istartswith" % field_name[1:]
            elif field_name.startswith('='):
                return "%s__iexact" % field_name[1:]
            elif field_name.startswith('@'):
                return "%s__search" % field_name[1:]
            else:
                return "%s__icontains" % field_name

        use_distinct = False

        orm_lookups = [construct_search(str(search_field))
                       for search_field in self.model_admin.search_fields]

        for bit in search_term.split():
            or_queries = [models.Q(**{orm_lookup: bit})
                          for orm_lookup in orm_lookups]
            queryset = queryset.filter(reduce(operator.or_, or_queries))

        if not use_distinct:
            for search_spec in orm_lookups:
                opts = utils.model_options(self.get_model())
                if utils.lookup_needs_distinct(opts, search_spec):
                    use_distinct = True
                    break

        return queryset, use_distinct

    def get_queryset(self):
        queryset = super(ModelListView, self).get_queryset()
        search_term = self.request.GET.get('q', None)
        search_use_distinct = False
        if self.model_admin.search_fields and search_term:
            queryset, search_use_distinct = self.get_search_results(
                queryset, search_term)

        queryset = self._modify_queryset_for_ordering(queryset)

        if self.model_admin.list_filter:
            queryset = self.build_list_filter(queryset).qs

        if self.model_admin.date_hierarchy:
            queryset = self.build_date_filter(queryset).qs

        queryset = self._modify_queryset_for_sort(queryset)

        if search_use_distinct:
            return queryset.distinct()
        else:
            return queryset

    def _modify_queryset_for_ordering(self, queryset):
        ordering = self.model_admin.get_ordering(self.request)
        if ordering:
            queryset = queryset.order_by(*ordering)
        return queryset

    def _modify_queryset_for_sort(self, queryset):
        # If we are sorting AND the field exists on the model
        sort_by = self.request.GET.get('sort', None)
        if sort_by:
            # Special case when we are not explicityly displaying fields
            if sort_by == '-__str__':
                queryset = queryset[::-1]
            try:
                # If we sort on '-' remove it before looking for that field
                field_exists = sort_by
                if field_exists[0] == '-':
                    field_exists = field_exists[1:]

                options = utils.model_options(self.model)
                options.get_field(field_exists)
                queryset = queryset.order_by(sort_by)
            except FieldDoesNotExist:
                # If the field does not exist then we dont sort on it
                pass
        return queryset

    def build_list_filter(self, queryset=None):
        if not hasattr(self, '_list_filter'):
            if queryset is None:
                queryset = self.get_queryset()
            self._list_filter = build_list_filter(
                self.request,
                self.model_admin,
                queryset,
            )
        return self._list_filter

    def build_date_filter(self, queryset=None):
        if not hasattr(self, "_date_filter"):
            if queryset is None:
                queryset = self.get_queryset()
            self._date_filter = build_date_filter(
                self.request,
                self.model_admin,
                queryset,
            )

        return self._date_filter

    def get_context_data(self, **kwargs):
        context = super(ModelListView, self).get_context_data(**kwargs)
        context['model'] = self.get_model()
        context['actions'] = self.get_actions().values()
        context['search_fields'] = self.get_search_fields()
        context['search_term'] = self.request.GET.get('q', '')
        context['list_filter'] = self.build_list_filter()
        context['sort_term'] = self.request.GET.get('sort', '')

        if self.model_admin.date_hierarchy:
            year = self.request.GET.get("year", False)
            month = self.request.GET.get("month", False)
            day = self.request.GET.get("day", False)

            if year and month and day:
                new_date = datetime.strptime(
                    "%s %s %s" % (month, day, year),
                    "%m %d %Y",
                )
                context["previous_date"] = {
                    "link": "?year=%s&month=%s" % (year, month),
                    "text": "‹ %s" % new_date.strftime("%B %Y")
                }

                context["active_day"] = new_date.strftime("%B %d")

                context["dates"] = self._format_days(context)
            elif year and month:
                context["previous_date"] = {
                    "link": "?year=%s" % (year),
                    "text": "‹ %s" % year,
                }

                context["dates"] = self._format_days(context)
            elif year:
                context["previous_date"] = {
                    "link": "?",
                    "text": ugettext_lazy("‹ All dates"),
                }

                context["dates"] = self._format_months(context)
            else:
                context["dates"] = self._format_years(context)

        return context

    def _format_years(self, context):
        years = context['object_list'].dates('published_date', 'year')
        if len(years) == 1:
            return self._format_months(context)
        else:
            return [
                (("?year=%s" % year.strftime("%Y")), year.strftime("%Y"))
                for year in
                context['object_list'].dates('published_date', 'year')
            ]

    def _format_months(self, context):
        return [
            (
                "?year=%s&month=%s" % (
                    date.strftime("%Y"), date.strftime("%m")
                ),
                date.strftime("%B %Y")
            ) for date in
            context["object_list"].dates('published_date', 'month')
        ]

    def _format_days(self, context):
        return [
            (
                "?year=%s&month=%s&day=%s" % (
                    date.strftime("%Y"),
                    date.strftime("%m"),
                    date.strftime("%d"),
                ),
                date.strftime("%B %d")
            ) for date in
            context["object_list"].dates('published_date', 'day')
        ]

    def get_success_url(self):
        view_name = 'admin2:{}_{}_index'.format(
            self.app_label, self.model_name)
        return reverse(view_name)

    def get_actions(self):
        return self.model_admin.get_list_actions()

    def get_search_fields(self):
        return self.model_admin.search_fields


class ModelDetailView(AdminModel2Mixin, generic.DetailView):
    """Context Variables

    :model: Type of object you are editing
    :model_name: Name of the object you are editing
    :app_label: Name of your app
    :app_verbose_names: A dictionary containing the app verbose name for
                        a given app, the item has a key being the
                        `app_label` and the value being a string, (or
                        even a lazy translation object), with the custom
                        app name.
    """
    default_template_name = "model_detail.html"
    permission_classes = (
        permissions.IsStaffPermission,
        permissions.ModelViewPermission)


class ModelEditFormView(AdminModel2Mixin, Admin2ModelFormMixin,
                        extra_views.UpdateWithInlinesView):
    """Context Variables

    :model: Type of object you are editing
    :model_name: Name of the object you are editing
    :app_label: Name of your app
    :app_verbose_names: A dictionary containing the app verbose name for
                        a given app, the item has a key being the
                        `app_label` and the value being a string, (or
                        even a lazy translation object), with the custom
                        app name.
    """
    form_class = None
    default_template_name = "model_update_form.html"
    permission_classes = (
        permissions.IsStaffPermission,
        permissions.ModelChangePermission)

    def get_context_data(self, **kwargs):
        context = super(ModelEditFormView, self).get_context_data(**kwargs)
        context['model'] = self.get_model()
        context['action'] = "Change"
        context['action_name'] = ugettext_lazy("Change")
        return context

    def forms_valid(self, form, inlines):
        response = super(ModelEditFormView, self).forms_valid(form, inlines)
        LogEntry.objects.log_action(
            self.request.user.id,
            self.object,
            LogEntry.CHANGE,
            self.construct_change_message(self.request, form, inlines))
        return response


class ModelAddFormView(AdminModel2Mixin, Admin2ModelFormMixin,
                       extra_views.CreateWithInlinesView):
    """Context Variables

    :model: Type of object you are editing
    :model_name: Name of the object you are editing
    :app_label: Name of your app
    :app_verbose_names: A dictionary containing the app verbose name for
                        a given app, the item has a key being the
                        `app_label` and the value being a string, (or
                        even a lazy translation object), with the custom
                        app name.
    """
    form_class = None
    default_template_name = "model_update_form.html"
    permission_classes = (
        permissions.IsStaffPermission,
        permissions.ModelAddPermission)

    def get_context_data(self, **kwargs):
        context = super(ModelAddFormView, self).get_context_data(**kwargs)
        context['model'] = self.get_model()
        context['action'] = "Add"
        context['action_name'] = ugettext_lazy("Add")
        return context

    def forms_valid(self, form, inlines):
        response = super(ModelAddFormView, self).forms_valid(form, inlines)
        LogEntry.objects.log_action(
            self.request.user.id,
            self.object,
            LogEntry.ADDITION,
            'Object created.')
        return response


class ModelDeleteView(AdminModel2Mixin, generic.DeleteView):
    """Context Variables

    :model: Type of object you are editing
    :model_name: Name of the object you are editing
    :app_label: Name of your app
    :deletable_objects: Objects to delete
    :app_verbose_names: A dictionary containing the app verbose name for
                        a given app, the item has a key being the
                        `app_label` and the value being a string, (or
                        even a lazy translation object), with the custom
                        app name.
    """
    success_url = "../../"  # TODO - fix this!
    default_template_name = "model_confirm_delete.html"
    permission_classes = (
        permissions.IsStaffPermission,
        permissions.ModelDeletePermission)

    def get_context_data(self, **kwargs):
        context = super(ModelDeleteView, self).get_context_data(**kwargs)

        def _format_callback(obj):
            opts = utils.model_options(obj)
            return '%s: %s' % (force_text(capfirst(opts.verbose_name)),
                               force_text(obj))

        collector = utils.NestedObjects(using=None)
        collector.collect([self.get_object()])
        context.update({
            'deletable_objects': collector.nested(_format_callback)
        })
        return context

    def delete(self, request, *args, **kwargs):
        LogEntry.objects.log_action(
            request.user.id,
            self.get_object(),
            LogEntry.DELETION,
            'Object deleted.')
        return super(ModelDeleteView, self).delete(request, *args, **kwargs)


class ModelHistoryView(AdminModel2Mixin, generic.ListView):
    """Context Variables

    :model: Type of object you are editing
    :model_name: Name of the object you are editing
    :app_label: Name of your app
    :app_verbose_names: A dictionary containing the app verbose name for
                        a given app, the item has a key being the
                        `app_label` and the value being a string, (or
                        even a lazy translation object), with the custom
                        app name.
    """
    default_template_name = "model_history.html"
    permission_classes = (
        permissions.IsStaffPermission,
        permissions.ModelChangePermission
    )

    def get_context_data(self, **kwargs):
        context = super(ModelHistoryView, self).get_context_data(**kwargs)
        context['model'] = self.get_model()
        context['object'] = self.get_object()
        return context

    def get_object(self):
        return get_object_or_404(self.get_model(), pk=self.kwargs.get('pk'))

    def get_queryset(self):
        content_type = ContentType.objects.get_for_model(self.get_object())
        return LogEntry.objects.filter(
            content_type=content_type,
            object_id=self.get_object().id
        )


class PasswordChangeView(Admin2Mixin, generic.UpdateView):

    default_template_name = 'auth/password_change_form.html'
    form_class = AdminPasswordChangeForm
    admin_form_class = PasswordChangeForm
    model = get_user_model()
    success_url = reverse_lazy('admin2:password_change_done')

    def get_form_kwargs(self, **kwargs):
        data = {'user': self.get_object()}

        if self.request.method in ('POST', 'PUT'):
            data.update({
                'data': self.request.POST
            })

        return data

    def get_form_class(self):
        if self.request.user == self.get_object():
            return self.admin_form_class
        return super(PasswordChangeView, self).get_form_class()


class PasswordChangeDoneView(Admin2Mixin, generic.TemplateView):

    default_template_name = 'auth/password_change_done.html'


class LoginView(Admin2Mixin, generic.TemplateView):
    """Context Variables

    :site_name: Name of the site
    """

    default_template_name = 'auth/login.html'
    authentication_form = AdminAuthenticationForm

    def dispatch(self, request, *args, **kwargs):
        return auth_login(request,
                          authentication_form=self.authentication_form,
                          template_name=self.get_template_names(),
                          *args, **kwargs)


class LogoutView(Admin2Mixin, generic.TemplateView):
    """Context Variables

    :site_name: Name of the site
    """

    default_template_name = 'auth/logout.html'

    def get(self, request, *args, **kwargs):
        return auth_logout(request, template_name=self.get_template_names(),
                           *args, **kwargs)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-admin2 documentation build configuration file, created by
# sphinx-quickstart on Sat May 18 12:59:02 2013.
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

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
project_directory = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))

# having the example project first, so that the settings module will be found
sys.path.insert(0, os.path.join(project_directory, 'example'))
sys.path.insert(1, project_directory)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.example.settings")

sys.path.insert(0, os.path.abspath('../../'))
sys.path.insert(0, os.path.abspath('../'))

# For intersphinx
ext_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "_ext"))
sys.path.append(ext_path)

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['djangodocs', 'sphinx.ext.autodoc', 'sphinx.ext.intersphinx',
'sphinx.ext.todo']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-admin2'
copyright = u'2013, Daniel Greenfeld'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.5'
# The full version, including alpha/beta/rc tags.
release = '0.5.2'

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

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


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
htmlhelp_basename = 'django-admin2doc'


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
  ('index', 'django-admin2.tex', u'django-admin2 Documentation',
   u'Daniel Greenfeld', 'manual'),
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
    ('index', 'django-admin2', u'django-admin2 Documentation',
     [u'Daniel Greenfeld'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'django-admin2', u'django-admin2 Documentation',
   u'Daniel Greenfeld', 'django-admin2', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    'python': ('http://python.readthedocs.org/en/v2.7.2/', None),
    'django': (
        'http://docs.djangoproject.com/en/dev/',
        'http://docs.djangoproject.com/en/dev/_objects/'
    ),
}

########NEW FILE########
__FILENAME__ = djangodocs
# Taken from https://github.com/django/django/blob/master/docs/_ext/djangodocs.py

import re
from sphinx import addnodes


# RE for option descriptions without a '--' prefix
simple_option_desc_re = re.compile(
        r'([-_a-zA-Z0-9]+)(\s*.*?)(?=,\s+(?:/|-|--)|$)')


def setup(app):
    app.add_crossref_type(
        directivename="setting",
        rolename="setting",
        indextemplate="pair: %s; setting",
    )
    app.add_crossref_type(
        directivename="templatetag",
        rolename="ttag",
        indextemplate="pair: %s; template tag"
    )
    app.add_crossref_type(
        directivename="templatefilter",
        rolename="tfilter",
        indextemplate="pair: %s; template filter"
    )
    app.add_crossref_type(
        directivename="fieldlookup",
        rolename="lookup",
        indextemplate="pair: %s; field lookup type",
    )
    app.add_description_unit(
        directivename="django-admin",
        rolename="djadmin",
        indextemplate="pair: %s; django-admin command",
        parse_node=parse_django_admin_node,
    )
    app.add_description_unit(
        directivename="django-admin-option",
        rolename="djadminopt",
        indextemplate="pair: %s; django-admin command-line option",
        parse_node=parse_django_adminopt_node,
    )


def parse_django_admin_node(env, sig, signode):
    command = sig.split(' ')[0]
    env._django_curr_admin_command = command
    title = "django-admin.py %s" % sig
    signode += addnodes.desc_name(title, title)
    return sig


def parse_django_adminopt_node(env, sig, signode):
    """A copy of sphinx.directives.CmdoptionDesc.parse_signature()"""
    from sphinx.domains.std import option_desc_re
    count = 0
    firstname = ''
    for m in option_desc_re.finditer(sig):
        optname, args = m.groups()
        if count:
            signode += addnodes.desc_addname(', ', ', ')
        signode += addnodes.desc_name(optname, optname)
        signode += addnodes.desc_addname(args, args)
        if not count:
            firstname = optname
        count += 1
    if not count:
        for m in simple_option_desc_re.finditer(sig):
            optname, args = m.groups()
            if count:
                signode += addnodes.desc_addname(', ', ', ')
            signode += addnodes.desc_name(optname, optname)
            signode += addnodes.desc_addname(args, args)
            if not count:
                firstname = optname
            count += 1
    if not firstname:
        raise ValueError
    return firstname

########NEW FILE########
__FILENAME__ = actions
# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, unicode_literals

from django.utils.translation import ugettext_lazy, pgettext_lazy
from django.contrib import messages

from djadmin2.actions import BaseListAction
from djadmin2 import permissions



class CustomPublishAction(BaseListAction):

    permission_classes = BaseListAction.permission_classes + (
        permissions.ModelChangePermission,
    )

    description = ugettext_lazy('Publish selected items')
    success_message = pgettext_lazy('singular form',
            'Successfully published %(count)s %(items)s')
    success_message_plural = pgettext_lazy('plural form',
            'Successfully published %(count)s %(items)s')

    default_template_name = "actions/publish_selected_items.html"

    def process_queryset(self):
        self.get_queryset().update(published=True)


class PublishAllItemsAction(BaseListAction):
    permission_classes = BaseListAction.permission_classes + (
        permissions.ModelChangePermission,
    )

    description = ugettext_lazy('Publish all items')
    success_message = pgettext_lazy(
        'singular form',
        'Successfully published %(count)s %(items)s',
    )

    success_message_plural = pgettext_lazy(
        'plural form',
        'Successfully published %(count)s %(items)s',
    )

    default_template_name = "model_list.html"
    only_selected = False

    def process_queryset(self):
        self.get_queryset().update(published=True)


def unpublish_items(request, queryset):
    queryset.update(published=False)
    messages.add_message(request, messages.INFO, ugettext_lazy(u'Items unpublished'))

# Translators : action description
unpublish_items.description = ugettext_lazy('Unpublish selected items')


def unpublish_all_items(request, queryset):
    queryset.update(published=False)
    messages.add_message(
        request,
        messages.INFO,
        ugettext_lazy('Items unpublished'),
    )

unpublish_all_items.description = ugettext_lazy('Unpublish all items')
unpublish_all_items.only_selected = False

########NEW FILE########
__FILENAME__ = admin
# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, unicode_literals

from django.contrib import admin

from .models import Post, Comment


class CommentInline(admin.TabularInline):
    model = Comment


class PostAdmin(admin.ModelAdmin):
    inlines = [CommentInline, ]
    search_fields = ('title', 'body', "published_date")
    list_filter = ['published', 'title']
    date_hierarchy = "published_date"

admin.site.register(Post, PostAdmin)
admin.site.register(Comment)

########NEW FILE########
__FILENAME__ = admin2
# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, unicode_literals

from django.utils.translation import ugettext_lazy

import djadmin2
from djadmin2 import renderers
from djadmin2.actions import DeleteSelectedAction

# Import your custom models
from .actions import (CustomPublishAction, PublishAllItemsAction,
                      unpublish_items, unpublish_all_items)
from .models import Post, Comment


class CommentInline(djadmin2.Admin2TabularInline):
    model = Comment


class PostAdmin(djadmin2.ModelAdmin2):
    list_actions = [
        DeleteSelectedAction, CustomPublishAction,
        PublishAllItemsAction, unpublish_items,
        unpublish_all_items,
    ]
    inlines = [CommentInline]
    search_fields = ('title', '^body')
    list_display = ('title', 'body', 'published', "published_date",)
    field_renderers = {
        'title': renderers.title_renderer,
    }
    save_on_top = True
    date_hierarchy = "published_date"
    ordering = ["-published_date", "title",]


class CommentAdmin(djadmin2.ModelAdmin2):
    search_fields = ('body', '=post__title')
    list_filter = ['post', ]
    actions_on_top = True
    actions_on_bottom = True
    actions_selection_counter = False

# Register the blog app with a verbose name
djadmin2.default.register_app_verbose_name(
    'blog',
    ugettext_lazy('My Blog')
)

#  Register each model with the admin
djadmin2.default.register(Post, PostAdmin)
djadmin2.default.register(Comment, CommentAdmin)


########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, unicode_literals

from django.db import models
from django.utils import six
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _


class Post(models.Model):
    title = models.CharField(max_length=255, verbose_name=_('title'))
    body = models.TextField(verbose_name=_('body'))
    published = models.BooleanField(default=False, verbose_name=_('published'))
    published_date = models.DateField(blank=True, null=True)

    def __unicode__(self):
        return self.title

    class Meta:
        verbose_name = _('post')
        verbose_name_plural = _('posts')


class Comment(models.Model):
    post = models.ForeignKey(Post, verbose_name=_('post'), related_name="comments")
    body = models.TextField(verbose_name=_('body'))

    def __unicode__(self):
        return self.body

    class Meta:
        verbose_name = _('comment')
        verbose_name_plural = _('comments')


#### Models needed for testing NestedObjects

@python_2_unicode_compatible
class Count(models.Model):
    num = models.PositiveSmallIntegerField()
    parent = models.ForeignKey('self', null=True)

    def __str__(self):
        return six.text_type(self.num)


class Event(models.Model):
    date = models.DateTimeField(auto_now_add=True)


class Location(models.Model):
    event = models.OneToOneField(Event, verbose_name='awesome event')


class Guest(models.Model):
    event = models.OneToOneField(Event)
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name = "awesome guest"


class EventGuide(models.Model):
    event = models.ForeignKey(Event, on_delete=models.DO_NOTHING)

########NEW FILE########
__FILENAME__ = test_apiviews
from django.contrib.auth.models import AnonymousUser, User
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import RequestFactory
from django.utils import simplejson as json


from djadmin2 import apiviews
from djadmin2 import default
from djadmin2 import ModelAdmin2
from ..models import Post


class APITestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User(
            username='admin',
            is_staff=True)
        self.user.set_password('admin')
        self.user.save()

    def get_model_admin(self, model):
        return ModelAdmin2(model, default)


class IndexAPIViewTest(APITestCase):
    def test_response_ok(self):
        request = self.factory.get(reverse('admin2:api_index'))
        request.user = self.user
        view = apiviews.IndexAPIView.as_view(**default.get_api_index_kwargs())
        response = view(request)
        self.assertEqual(response.status_code, 200)

    def test_view_permission(self):
        request = self.factory.get(reverse('admin2:api_index'))
        request.user = AnonymousUser()
        view = apiviews.IndexAPIView.as_view(**default.get_api_index_kwargs())
        self.assertRaises(PermissionDenied, view, request)


class ListCreateAPIViewTest(APITestCase):
    def test_response_ok(self):
        request = self.factory.get(reverse('admin2:blog_post_api_list'))
        request.user = self.user
        model_admin = self.get_model_admin(Post)
        view = apiviews.ListCreateAPIView.as_view(
            **model_admin.get_api_list_kwargs())
        response = view(request)
        self.assertEqual(response.status_code, 200)

    def test_view_permission(self):
        request = self.factory.get(reverse('admin2:blog_post_api_list'))
        request.user = AnonymousUser()
        model_admin = self.get_model_admin(Post)
        view = apiviews.ListCreateAPIView.as_view(
            **model_admin.get_api_list_kwargs())
        self.assertRaises(PermissionDenied, view, request)

    def test_list_includes_unicode_field(self):
        Post.objects.create(title='Foo', body='Bar')
        request = self.factory.get(reverse('admin2:blog_post_api_list'))
        request.user = self.user
        model_admin = self.get_model_admin(Post)
        view = apiviews.ListCreateAPIView.as_view(
            **model_admin.get_api_list_kwargs())
        response = view(request)
        response.render()

        self.assertEqual(response.status_code, 200)
        self.assertIn('"__str__": "Foo"', response.content)

    def test_pagination(self):
        request = self.factory.get(reverse('admin2:blog_post_api_list'))
        request.user = self.user
        model_admin = self.get_model_admin(Post)
        view = apiviews.ListCreateAPIView.as_view(
            **model_admin.get_api_list_kwargs())
        response = view(request)
        response.render()

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['count'], 0)
        # next and previous fields exist, but are null because we have no
        # content
        self.assertTrue('next' in data)
        self.assertEqual(data['next'], None)
        self.assertTrue('previous' in data)
        self.assertEqual(data['previous'], None)


class RetrieveUpdateDestroyAPIViewTest(APITestCase):
    def test_response_ok(self):
        post = Post.objects.create(title='Foo', body='Bar')
        request = self.factory.get(
            reverse('admin2:blog_post_api_detail',
            kwargs={'pk': post.pk}))
        request.user = self.user
        model_admin = self.get_model_admin(Post)
        view = apiviews.RetrieveUpdateDestroyAPIView.as_view(
            **model_admin.get_api_detail_kwargs())
        response = view(request, pk=post.pk)
        self.assertEqual(response.status_code, 200)

    def test_view_permission(self):
        post = Post.objects.create(title='Foo', body='Bar')
        request = self.factory.get(
            reverse('admin2:blog_post_api_detail',
            kwargs={'pk': post.pk}))
        request.user = AnonymousUser()
        model_admin = self.get_model_admin(Post)
        view = apiviews.RetrieveUpdateDestroyAPIView.as_view(
            **model_admin.get_api_detail_kwargs())
        self.assertRaises(PermissionDenied, view, request, pk=post.pk)

########NEW FILE########
__FILENAME__ = test_builtin_api_resources
from django.contrib.auth.models import Group, User
from django.core.urlresolvers import reverse

from .test_apiviews import APITestCase


class UserAPITest(APITestCase):
    def test_list_response_ok(self):
        self.client.login(username='admin', password='admin')
        response = self.client.get(reverse('admin2:auth_user_api_list'))
        self.assertEqual(response.status_code, 200)

    def test_list_view_permission(self):
        response = self.client.get(reverse('admin2:auth_user_api_list'))
        self.assertEqual(response.status_code, 403)

    def test_detail_response_ok(self):
        self.client.login(username='admin', password='admin')
        user = User.objects.create_user(
            username='Foo',
            password='bar')
        response = self.client.get(
            reverse('admin2:auth_user_api_detail', args=(user.pk,)))
        self.assertEqual(response.status_code, 200)

    def test_detail_view_permission(self):
        user = User.objects.create_user(
            username='Foo',
            password='bar')
        response = self.client.get(
            reverse('admin2:auth_user_api_detail', args=(user.pk,)))
        self.assertEqual(response.status_code, 403)


class GroupAPITest(APITestCase):
    def test_list_response_ok(self):
        self.client.login(username='admin', password='admin')
        response = self.client.get(reverse('admin2:auth_group_api_list'))
        self.assertEqual(response.status_code, 200)

    def test_list_view_permission(self):
        response = self.client.get(reverse('admin2:auth_group_api_list'))
        self.assertEqual(response.status_code, 403)

    def test_detail_response_ok(self):
        self.client.login(username='admin', password='admin')
        group = Group.objects.create(name='group')
        response = self.client.get(
            reverse('admin2:auth_group_api_detail', args=(group.pk,)))
        self.assertEqual(response.status_code, 200)

    def test_detail_view_permission(self):
        group = Group.objects.create(name='group')
        response = self.client.get(
            reverse('admin2:auth_group_api_detail', args=(group.pk,)))
        self.assertEqual(response.status_code, 403)

########NEW FILE########
__FILENAME__ = test_filters
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.test.client import RequestFactory
from django.core.urlresolvers import reverse

from ..models import Post

import djadmin2
import djadmin2.filters as djadmin2_filters

import django_filters


class PostAdminSimple(djadmin2.ModelAdmin2):
    list_filter = ['published', ]


class PostAdminWithFilterInstances(djadmin2.ModelAdmin2):
    list_filter = [
        django_filters.BooleanFilter(name='published'),
    ]


class FS(django_filters.FilterSet):
    class Meta:
        model = Post
        fields = ['published']


class PostAdminWithFilterSetInst(djadmin2.ModelAdmin2):
    list_filter = FS


class ListFilterBuilderTest(TestCase):

    def setUp(self):
        self.rf = RequestFactory()

    def test_filter_building(self):
        Post.objects.create(title="post_1_title", body="body")
        Post.objects.create(title="post_2_title", body="another body")
        request = self.rf.get(reverse("admin2:dashboard"))
        list_filter_inst = djadmin2_filters.build_list_filter(
            request,
            PostAdminSimple,
            Post.objects.all(),
        )
        self.assertTrue(
            issubclass(list_filter_inst.__class__, django_filters.FilterSet)
        )
        self.assertEqual(
            list_filter_inst.filters['published'].widget,
            djadmin2_filters.NullBooleanLinksWidget,
        )
        list_filter_inst = djadmin2_filters.build_list_filter(
            request,
            PostAdminWithFilterInstances,
            Post.objects.all(),
        )
        self.assertNotEqual(
            list_filter_inst.filters['published'].widget,
            djadmin2_filters.NullBooleanLinksWidget,
        )
        list_filter_inst = djadmin2_filters.build_list_filter(
            request,
            PostAdminWithFilterSetInst,
            Post.objects.all(),
        )
        self.assertTrue(isinstance(list_filter_inst, FS))

########NEW FILE########
__FILENAME__ = test_modelforms
from django import forms
from django.test import TestCase

import floppyforms

from djadmin2.forms import floppify_widget, floppify_form, modelform_factory
from ..models import Post


class ModelFormFactoryTest(TestCase):
    def test_modelform_factory(self):
        form_class = modelform_factory(Post)
        self.assertTrue(form_class)
        field = form_class.base_fields['title']
        self.assertTrue(isinstance(field.widget, floppyforms.TextInput))


class GetFloppyformWidgetTest(TestCase):
    def assertExpectWidget(self, instance, new_class_,
        equal_attributes=None, new_attributes=None):
        new_instance = floppify_widget(instance)
        self.assertEqual(new_instance.__class__, new_class_)
        if equal_attributes:
            for attribute in equal_attributes:
                self.assertTrue(
                    hasattr(instance, attribute),
                    'Cannot check attribute %r, not available on original '
                    'widget %r' % (attribute, instance))
                self.assertTrue(
                    hasattr(new_instance, attribute),
                    'Cannot check attribute %r, not available on generated '
                    'widget %r' % (attribute, new_instance))
                old_attr = getattr(instance, attribute)
                new_attr = getattr(new_instance, attribute)
                self.assertEqual(old_attr, new_attr,
                    'Original widget\'s attribute was not copied: %r != %r' %
                    (old_attr, new_attr))
        if new_attributes:
            for attribute, value in new_attributes.items():
                self.assertTrue(
                    hasattr(new_instance, attribute),
                    'Cannot check new attribute %r, not available on '
                    'generated widget %r' % (attribute, new_instance))
                new_attr = getattr(new_instance, attribute)
                self.assertEqual(new_attr, value,
                    'Generated widget\'s attribute is not as expected: '
                    '%r != %r' % (new_attr, value))

    def test_created_widget_doesnt_leak_attributes_into_original_widget(self):
        widget = forms.TextInput()
        widget.is_required = True
        widget.attrs = {'placeholder': 'Search ...'}
        new_widget = floppify_widget(widget)
        self.assertFalse(widget.__dict__ is new_widget.__dict__)
        new_widget.is_required = False
        self.assertEqual(widget.is_required, True)
        new_widget.attrs['placeholder'] = 'Enter name'
        self.assertEqual(widget.attrs['placeholder'], 'Search ...')

    def test_copy_attribute_is_required(self):
        widget = forms.TextInput()
        widget.is_required = True
        self.assertExpectWidget(
            widget,
            floppyforms.TextInput,
            equal_attributes=['is_required'])

    # Test individual widgets

    def test_input_widget(self):
        self.assertExpectWidget(
            forms.widgets.Input(),
            floppyforms.widgets.Input)

        widget = forms.widgets.Input()
        widget.input_type = 'email'
        self.assertExpectWidget(
            widget,
            floppyforms.widgets.Input,
            ['input_type'])

    def test_textinput_widget(self):
        self.assertExpectWidget(
            forms.widgets.TextInput(),
            floppyforms.widgets.TextInput,
            ['input_type'],
            {'input_type': 'text'})

    def test_passwordinput_widget(self):
        self.assertExpectWidget(
            forms.widgets.PasswordInput(),
            floppyforms.widgets.PasswordInput,
            ['input_type'],
            {'input_type': 'password'})

    def test_hiddeninput_widget(self):
        self.assertExpectWidget(
            forms.widgets.HiddenInput(),
            floppyforms.widgets.HiddenInput)

        widget = forms.widgets.HiddenInput()
        widget.is_hidden = False
        self.assertExpectWidget(
            widget,
            floppyforms.widgets.HiddenInput,
            ['input_type'])

    def test_multiplehiddeninput_widget(self):
        self.assertExpectWidget(
            forms.widgets.MultipleHiddenInput(),
            floppyforms.widgets.MultipleHiddenInput)

        widget = forms.widgets.MultipleHiddenInput(choices=(
            ('no', 'Please, No!'),
            ('yes', 'Ok, why not.'),
        ))
        self.assertExpectWidget(
            widget,
            floppyforms.widgets.MultipleHiddenInput,
            ['choices'])

    def test_fileinput_widget(self):
        self.assertExpectWidget(
            forms.widgets.FileInput(),
            floppyforms.widgets.FileInput)

        widget = forms.widgets.FileInput()
        widget.needs_multipart_form = False
        self.assertExpectWidget(
            widget,
            floppyforms.widgets.FileInput,
            ['needs_multipart_form'])

    def test_clearablefileinput_widget(self):
        self.assertExpectWidget(
            forms.widgets.ClearableFileInput(),
            floppyforms.widgets.ClearableFileInput)

        widget = forms.widgets.ClearableFileInput()
        widget.initial_text = 'some random text 1'
        widget.input_text = 'some random text 2'
        widget.clear_checkbox_label = 'some random text 3'
        widget.template_with_initial = 'some random text 4'
        widget.template_with_clear = 'some random text 5'
        self.assertExpectWidget(
            widget,
            floppyforms.widgets.ClearableFileInput,
            ['initial_text', 'input_text', 'clear_checkbox_label',
            'template_with_initial', 'template_with_clear'])

    def test_textarea_widget(self):
        self.assertExpectWidget(
            forms.widgets.Textarea(),
            floppyforms.widgets.Textarea)

    def test_dateinput_widget(self):
        self.assertExpectWidget(
            forms.DateInput(),
            floppyforms.DateInput)

        widget = forms.widgets.DateInput(format='DATE_FORMAT')
        self.assertExpectWidget(
            widget,
            floppyforms.widgets.DateInput,
            ['format'],
            {'input_type': 'date'})

    def test_datetimeinput_widget(self):
        self.assertExpectWidget(
            forms.widgets.DateTimeInput(),
            floppyforms.widgets.DateTimeInput)

        widget = forms.widgets.DateTimeInput(format='DATETIME_FORMAT')
        self.assertExpectWidget(
            widget,
            floppyforms.widgets.DateTimeInput,
            ['format'],
            {'input_type': 'datetime'})

    def test_timeinput_widget(self):
        self.assertExpectWidget(
            forms.widgets.TimeInput(),
            floppyforms.widgets.TimeInput)

        widget = forms.widgets.TimeInput(format='TIME_FORMAT')
        self.assertExpectWidget(
            widget,
            floppyforms.widgets.TimeInput,
            ['format'],
            {'input_type': 'time'})

    def test_checkboxinput_widget(self):
        self.assertExpectWidget(
            forms.widgets.CheckboxInput(),
            floppyforms.widgets.CheckboxInput)

        check_test = lambda v: False
        widget = forms.widgets.CheckboxInput(check_test=check_test)
        new_widget = floppify_widget(widget)
        self.assertEqual(widget.check_test, new_widget.check_test)
        self.assertTrue(new_widget.check_test is check_test)

    def test_select_widget(self):
        choices = (
            ('draft', 'Draft'),
            ('public', 'Public'),
        )

        self.assertExpectWidget(
            forms.widgets.Select(),
            floppyforms.widgets.Select)

        widget = forms.widgets.Select(choices=choices)
        widget.allow_multiple_selected = True
        self.assertExpectWidget(
            widget,
            floppyforms.widgets.Select,
            ('choices', 'allow_multiple_selected',))

    def test_nullbooleanselect_widget(self):
        self.assertExpectWidget(
            forms.widgets.NullBooleanSelect(),
            floppyforms.widgets.NullBooleanSelect,
            ('choices', 'allow_multiple_selected',))
        
        widget = forms.widgets.NullBooleanSelect()
        widget.choices = list(widget.choices)

        value, label = widget.choices[0]
        widget.choices[0] = value, 'Maybe'

        self.assertExpectWidget(
            widget,
            floppyforms.widgets.NullBooleanSelect,
            ('choices', 'allow_multiple_selected',))

    def test_selectmultiple_widget(self):
        choices = (
            ('draft', 'Draft'),
            ('public', 'Public'),
        )

        self.assertExpectWidget(
            forms.widgets.SelectMultiple(),
            floppyforms.widgets.SelectMultiple)

        widget = forms.widgets.SelectMultiple(choices=choices)
        widget.allow_multiple_selected = False
        self.assertExpectWidget(
            widget,
            floppyforms.widgets.SelectMultiple,
            ('choices', 'allow_multiple_selected',))

    def test_radioselect_widget(self):
        choices = (
            ('draft', 'Draft'),
            ('public', 'Public'),
        )

        self.assertExpectWidget(
            forms.widgets.RadioSelect(),
            floppyforms.widgets.RadioSelect)

        self.assertExpectWidget(
            forms.widgets.RadioSelect(choices=choices),
            floppyforms.widgets.RadioSelect,
            ('choices', 'allow_multiple_selected',))

        widget = forms.widgets.RadioSelect(renderer='custom renderer')
        # don't overwrite widget with floppyform widget if a custom renderer
        # was used. We cannot copy this over since floppyform doesn't use the
        # renderer.
        self.assertExpectWidget(
            widget,
            forms.widgets.RadioSelect)

    def test_checkboxselectmultiple_widget(self):
        choices = (
            ('draft', 'Draft'),
            ('public', 'Public'),
        )

        self.assertExpectWidget(
            forms.widgets.CheckboxSelectMultiple(),
            floppyforms.widgets.CheckboxSelectMultiple)

        self.assertExpectWidget(
            forms.widgets.CheckboxSelectMultiple(choices=choices),
            floppyforms.widgets.CheckboxSelectMultiple,
            ('choices', 'allow_multiple_selected',))

    def test_multi_widget(self):
        self.assertExpectWidget(
            forms.widgets.MultiWidget([]),
            floppyforms.widgets.MultiWidget)

        text_input = forms.widgets.TextInput()
        widget = forms.widgets.MultiWidget([text_input])
        new_widget = floppify_widget(widget)
        self.assertEqual(widget.widgets, new_widget.widgets)
        self.assertTrue(new_widget.widgets[0] is text_input)

    def test_splitdatetime_widget(self):
        widget = forms.widgets.SplitDateTimeWidget()
        self.assertExpectWidget(
            widget,
            floppyforms.widgets.SplitDateTimeWidget)

        widget = forms.widgets.SplitDateTimeWidget(
            date_format='DATE_FORMAT', time_format='TIME_FORMAT')
        new_widget = floppify_widget(widget)
        self.assertTrue(isinstance(
            new_widget.widgets[0], floppyforms.widgets.DateInput))
        self.assertTrue(isinstance(
            new_widget.widgets[1], floppyforms.widgets.TimeInput))
        self.assertEqual(new_widget.widgets[0].format, 'DATE_FORMAT')
        self.assertEqual(new_widget.widgets[1].format, 'TIME_FORMAT')

    def test_splithiddendatetime_widget(self):
        widget = forms.widgets.SplitHiddenDateTimeWidget()
        self.assertExpectWidget(
            widget,
            floppyforms.widgets.SplitHiddenDateTimeWidget)

        widget = forms.widgets.SplitHiddenDateTimeWidget(
            date_format='DATE_FORMAT', time_format='TIME_FORMAT')
        new_widget = floppify_widget(widget)
        self.assertTrue(isinstance(
            new_widget.widgets[0], floppyforms.widgets.DateInput))
        self.assertTrue(isinstance(
            new_widget.widgets[1], floppyforms.widgets.TimeInput))
        self.assertEqual(new_widget.widgets[0].format, 'DATE_FORMAT')
        self.assertEqual(new_widget.widgets[0].is_hidden, True)
        self.assertEqual(new_widget.widgets[1].format, 'TIME_FORMAT')
        self.assertEqual(new_widget.widgets[1].is_hidden, True)

    def test_selectdate_widget(self):
        self.assertExpectWidget(
            forms.extras.widgets.SelectDateWidget(),
            floppyforms.widgets.SelectDateWidget)

        widget = forms.extras.widgets.SelectDateWidget(
            attrs={'attribute': 'value'},
            years=[2010, 2011, 2012, 2013],
            required=False)
        self.assertExpectWidget(
            widget,
            floppyforms.widgets.SelectDateWidget,
            ('attrs', 'years', 'required'))


class ModelFormTest(TestCase):
    def test_custom_base_form(self):
        class MyForm(forms.ModelForm):
            pass

        form_class = modelform_factory(model=Post, form=MyForm)
        form = form_class()
        self.assertTrue(isinstance(
            form.fields['title'].widget,
            floppyforms.widgets.TextInput))

    def test_declared_fields(self):
        class MyForm(forms.ModelForm):
            subtitle = forms.CharField()

        form_class = modelform_factory(model=Post, form=MyForm)
        self.assertTrue(isinstance(
            form_class.base_fields['subtitle'].widget,
            floppyforms.widgets.TextInput))
        self.assertTrue(isinstance(
            form_class.declared_fields['subtitle'].widget,
            floppyforms.widgets.TextInput))

        self.assertTrue(isinstance(
            form_class.base_fields['title'].widget,
            floppyforms.widgets.TextInput))
        # title is not defined in declared fields

    def test_additional_form_fields(self):
        class MyForm(forms.ModelForm):
            subtitle = forms.CharField()

        form_class = modelform_factory(model=Post, form=MyForm)
        form = form_class()
        self.assertTrue(isinstance(
            form.fields['subtitle'].widget,
            floppyforms.widgets.TextInput))

    def test_subclassing_forms(self):
        class MyForm(forms.ModelForm):
            subtitle = forms.CharField()

            class Meta:
                model = Post

        class ChildForm(MyForm):
            created = forms.DateField()

        form_class = modelform_factory(model=Post, form=ChildForm)
        form = form_class()
        self.assertTrue(isinstance(
            form.fields['title'].widget,
            floppyforms.widgets.TextInput))
        self.assertTrue(isinstance(
            form.fields['subtitle'].widget,
            floppyforms.widgets.TextInput))
        self.assertTrue(isinstance(
            form.fields['created'].widget,
            floppyforms.widgets.DateInput))


class FieldWidgetTest(TestCase):
    def test_dont_overwrite_none_default_widget(self):
        # we don't create the floppyform EmailInput for the email field here
        # since we have overwritten the default widget. However we replace the
        # django textarea with a floppyforms Textarea
        email_input = forms.widgets.Textarea()

        class MyForm(forms.ModelForm):
            email = forms.EmailField(widget=email_input)

            class Meta:
                model = Post

        form_class = floppify_form(MyForm)
        widget = form_class().fields['email'].widget
        self.assertFalse(isinstance(widget, floppyforms.widgets.EmailInput))
        self.assertTrue(isinstance(widget, floppyforms.widgets.Textarea))

    def test_float_field(self):
        class MyForm(forms.ModelForm):
            float = forms.FloatField()

        form_class = modelform_factory(model=Post, form=MyForm)
        widget = form_class().fields['float'].widget
        self.assertTrue(isinstance(widget, floppyforms.widgets.NumberInput))
        self.assertEqual(widget.input_type, 'number')

    def test_decimal_field(self):
        class MyForm(forms.ModelForm):
            decimal = forms.DecimalField()

        form_class = modelform_factory(model=Post, form=MyForm)
        widget = form_class().fields['decimal'].widget
        self.assertTrue(isinstance(widget, floppyforms.widgets.NumberInput))
        self.assertEqual(widget.input_type, 'number')

    def test_integer_field(self):
        class MyForm(forms.ModelForm):
            integer = forms.IntegerField()

        form_class = modelform_factory(model=Post, form=MyForm)
        widget = form_class().fields['integer'].widget
        self.assertTrue(isinstance(widget, floppyforms.widgets.NumberInput))
        self.assertEqual(widget.input_type, 'number')

    def test_email_field(self):
        class MyForm(forms.ModelForm):
            email = forms.EmailField()

        form_class = modelform_factory(model=Post, form=MyForm)
        widget = form_class().fields['email'].widget
        self.assertTrue(isinstance(widget, floppyforms.widgets.EmailInput))
        self.assertEqual(widget.input_type, 'email')

    def test_url_field(self):
        class MyForm(forms.ModelForm):
            url = forms.URLField()

        form_class = modelform_factory(model=Post, form=MyForm)
        widget = form_class().fields['url'].widget
        self.assertTrue(isinstance(widget, floppyforms.widgets.URLInput))
        self.assertEqual(widget.input_type, 'url')

    def test_slug_field(self):
        class MyForm(forms.ModelForm):
            slug = forms.SlugField()

        form_class = modelform_factory(model=Post, form=MyForm)
        widget = form_class().fields['slug'].widget
        self.assertTrue(isinstance(widget, floppyforms.widgets.SlugInput))
        self.assertEqual(widget.input_type, 'text')

    def test_ipaddress_field(self):
        class MyForm(forms.ModelForm):
            ipaddress = forms.IPAddressField()

        form_class = modelform_factory(model=Post, form=MyForm)
        widget = form_class().fields['ipaddress'].widget
        self.assertTrue(isinstance(widget, floppyforms.widgets.IPAddressInput))
        self.assertEqual(widget.input_type, 'text')

    def test_splitdatetime_field(self):
        class MyForm(forms.ModelForm):
            splitdatetime = forms.SplitDateTimeField()

        form_class = modelform_factory(model=Post, form=MyForm)
        widget = form_class().fields['splitdatetime'].widget
        self.assertTrue(isinstance(
            widget, floppyforms.widgets.SplitDateTimeWidget))
        self.assertTrue(isinstance(
            widget.widgets[0], floppyforms.widgets.DateInput))
        self.assertTrue(isinstance(
            widget.widgets[1], floppyforms.widgets.TimeInput))

########NEW FILE########
__FILENAME__ = test_nestedobjects
from django.db import DEFAULT_DB_ALIAS
from django.test import TestCase

from djadmin2.utils import NestedObjects

from ..models import Count, Event, EventGuide, Guest, Location


class NestedObjectsTests(TestCase):
    """
    Tests for ``NestedObject`` utility collection.

    This is adopted from the Django core. django-admin2 mandates that code
    doesn't depend on imports from django.contrib.admin.

    https://github.com/django/django/blob/1.5.1/tests/regressiontests/admin_util/tests.py
    """
    def setUp(self):
        self.n = NestedObjects(using=DEFAULT_DB_ALIAS)
        self.objs = [Count.objects.create(num=i) for i in range(5)]

    def _check(self, target):
        self.assertEqual(self.n.nested(lambda obj: obj.num), target)

    def _connect(self, i, j):
        self.objs[i].parent = self.objs[j]
        self.objs[i].save()

    def _collect(self, *indices):
        self.n.collect([self.objs[i] for i in indices])

    def test_unrelated_roots(self):
        self._connect(2, 1)
        self._collect(0)
        self._collect(1)
        self._check([0, 1, [2]])

    def test_siblings(self):
        self._connect(1, 0)
        self._connect(2, 0)
        self._collect(0)
        self._check([0, [1, 2]])

    def test_non_added_parent(self):
        self._connect(0, 1)
        self._collect(0)
        self._check([0])

    def test_cyclic(self):
        self._connect(0, 2)
        self._connect(1, 0)
        self._connect(2, 1)
        self._collect(0)
        self._check([0, [1, [2]]])

    def test_queries(self):
        self._connect(1, 0)
        self._connect(2, 0)
        # 1 query to fetch all children of 0 (1 and 2)
        # 1 query to fetch all children of 1 and 2 (none)
        # Should not require additional queries to populate the nested graph.
        self.assertNumQueries(2, self._collect, 0)

    def test_on_delete_do_nothing(self):
        """
        Check that the nested collector doesn't query for DO_NOTHING objects.
        """
        objs = [Event.objects.create()]
        n = NestedObjects(using=None)
        EventGuide.objects.create(event=objs[0])
        with self.assertNumQueries(2):
            # One for Location, one for Guest, and no query for EventGuide
            n.collect(objs)

########NEW FILE########
__FILENAME__ = test_permissions
from django.contrib.auth.models import User, Permission
from django.core.urlresolvers import reverse
from django.template import Template, Context
from django.test import TestCase
from django.test.client import RequestFactory

import djadmin2
from djadmin2 import ModelAdmin2
from djadmin2.permissions import TemplatePermissionChecker

from blog.models import Post


class TemplatePermissionTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User(
            username='admin',
            is_staff=True)
        self.user.set_password('admin')
        self.user.save()

    def render(self, template, context):
        template = Template(template)
        context = Context(context)
        return template.render(context)

    def test_permission_wrapper(self):
        model_admin = ModelAdmin2(Post, djadmin2.default)
        request = self.factory.get(reverse('admin2:blog_post_index'))
        request.user = self.user
        permissions = TemplatePermissionChecker(request, model_admin)
        context = {
            'permissions': permissions,
        }

        result = self.render(
            '{{ permissions.has_unvalid_permission }}',
            context)
        self.assertEqual(result, '')

        result = self.render('{{ permissions.has_add_permission }}', context)
        self.assertEqual(result, 'False')

        post_add_permission = Permission.objects.get(
            content_type__app_label='blog',
            content_type__model='post',
            codename='add_post')
        self.user.user_permissions.add(post_add_permission)
        # invalidate the users permission cache
        if hasattr(self.user, '_perm_cache'):
            del self.user._perm_cache

        result = self.render('{{ permissions.has_add_permission }}', context)
        self.assertEqual(result, 'True')

    def test_admin_traversal_by_name(self):
        post_add_permission = Permission.objects.get(
            content_type__app_label='blog',
            content_type__model='post',
            codename='add_post')
        self.user.user_permissions.add(post_add_permission)

        model_admin = ModelAdmin2(Post, djadmin2.default)
        request = self.factory.get(reverse('admin2:blog_post_index'))
        request.user = self.user
        permissions = TemplatePermissionChecker(request, model_admin)
        context = {
            'permissions': permissions,
        }

        result = self.render('{{ permissions.has_add_permission }}', context)
        self.assertEqual(result, 'True')
        result = self.render('{{ permissions.blog_post.has_add_permission }}', context)
        self.assertEqual(result, 'True')
        result = self.render('{{ permissions.blog_post.has_change_permission }}', context)
        self.assertEqual(result, 'False')
        result = self.render('{{ permissions.auth_user.has_delete_permission }}', context)
        self.assertEqual(result, 'False')

        result = self.render(
            '{{ permissions.unknown_app.has_add_permission }}',
            context)
        self.assertEqual(result, '')

        result = self.render(
            '{{ permissions.blog_post.has_unvalid_permission }}',
            context)
        self.assertEqual(result, '')

    def test_admin_binding(self):
        user_admin = djadmin2.default.get_admin_by_name('auth_user')
        post_admin = djadmin2.default.get_admin_by_name('blog_post')
        request = self.factory.get(reverse('admin2:auth_user_index'))
        request.user = self.user
        permissions = TemplatePermissionChecker(request, user_admin)

        post = Post.objects.create(title='Hello', body='world')
        context = {
            'post': post,
            'post_admin': post_admin,
            'permissions': permissions,
        }

        result = self.render(
            '{% load admin2_tags %}'
            '{{ permissions|for_admin:post_admin }}',
            context)
        self.assertEqual(result, '')

        result = self.render(
            '{% load admin2_tags %}'
            '{{ permissions.has_add_permission }}'
            '{% with permissions|for_admin:post_admin as permissions %}'
                '{{ permissions.has_add_permission }}'
            '{% endwith %}',
            context)
        self.assertEqual(result, 'FalseFalse')

        post_add_permission = Permission.objects.get(
            content_type__app_label='blog',
            content_type__model='post',
            codename='add_post')
        self.user.user_permissions.add(post_add_permission)
        # invalidate the users permission cache
        if hasattr(self.user, '_perm_cache'):
            del self.user._perm_cache

        result = self.render(
            '{% load admin2_tags %}'
            '{{ permissions.has_add_permission }}'
            '{% with permissions|for_admin:post_admin as permissions %}'
                '{{ permissions.has_add_permission }}'
            '{% endwith %}'
            '{{ permissions.blog_post.has_add_permission }}',
            context)
        self.assertEqual(result, 'FalseTrueTrue')

        # giving a string (the name of the admin) also works
        result = self.render(
            '{% load admin2_tags %}'
            '{% with permissions|for_admin:"blog_post" as permissions %}'
                '{{ permissions.has_add_permission }}'
            '{% endwith %}',
            context)
        self.assertEqual(result, 'True')

        # testing invalid admin names
        result = self.render(
            '{% load admin2_tags %}'
            '{% with permissions|for_admin:"invalid_admin_name" as permissions %}'
                '{{ permissions.has_add_permission }}'
            '{% endwith %}',
            context)
        self.assertEqual(result, '')

    def test_view_binding(self):
        user_admin = djadmin2.default.get_admin_by_name('auth_user')
        post_admin = djadmin2.default.get_admin_by_name('blog_post')
        request = self.factory.get(reverse('admin2:auth_user_index'))
        request.user = self.user
        permissions = TemplatePermissionChecker(request, user_admin)

        context = {
            'post_admin': post_admin,
            'post_add_view': post_admin.create_view,
            'permissions': permissions,
        }

        result = self.render(
            '{% load admin2_tags %}'
            '{{ permissions|for_view:"add" }}',
            context)
        self.assertEqual(result, 'False')

        # view classes are not supported yet
        result = self.render(
            '{% load admin2_tags %}'
            '{{ permissions|for_view:post_add_view }}',
            context)
        self.assertEqual(result, '')

        result = self.render(
            '{% load admin2_tags %}'
            # user add permission
            '{{ permissions.has_add_permission }}'
            '{% with permissions|for_admin:"blog_post"|for_view:"add" as post_add_perm %}'
                # post add permission
                '{{ post_add_perm }}'
            '{% endwith %}',
            context)
        self.assertEqual(result, 'FalseFalse')

        post_add_permission = Permission.objects.get(
            content_type__app_label='blog',
            content_type__model='post',
            codename='add_post')
        self.user.user_permissions.add(post_add_permission)
        user_change_permission = Permission.objects.get(
            content_type__app_label='auth',
            content_type__model='user',
            codename='change_user')
        self.user.user_permissions.add(user_change_permission)

        # invalidate the users permission cache
        if hasattr(self.user, '_perm_cache'):
            del self.user._perm_cache

        result = self.render(
            '{% load admin2_tags %}'
            # user add permission
            '{{ permissions.has_add_permission }}'
            '{% with permissions|for_admin:"blog_post"|for_view:"add" as post_add_perm %}'
                # post add permission
                '{{ post_add_perm }}'
            '{% endwith %}'
            # user change permission
            '{{ permissions|for_view:"change" }}',
            context)
        self.assertEqual(result, 'FalseTrueTrue')

        # giving a string (the name of the view) also works
        result = self.render(
            '{% load admin2_tags %}'
            '{% with permissions|for_view:"change" as user_change_perm %}'
                '1{{ user_change_perm }}'
                '2{{ user_change_perm|for_view:"add" }}'
                # this shouldn't return True or False but '' since the
                # previously bound change view doesn't belong to the newly
                # bound blog_post admin
                '3{{ user_change_perm|for_admin:"blog_post" }}'
                '4{{ user_change_perm|for_admin:"blog_post"|for_view:"add" }}'
            '{% endwith %}',
            context)
        self.assertEqual(result, '1True2False34True')

    def test_object_level_permission(self):
        model_admin = ModelAdmin2(Post, djadmin2.default)
        request = self.factory.get(reverse('admin2:blog_post_index'))
        request.user = self.user
        permissions = TemplatePermissionChecker(request, model_admin)

        post = Post.objects.create(title='Hello', body='world')
        context = {
            'post': post,
            'permissions': permissions,
        }

        result = self.render(
            '{% load admin2_tags %}'
            '{{ permissions.has_unvalid_permission|for_object:post }}',
            context)
        self.assertEqual(result, '')

        result = self.render(
            '{% load admin2_tags %}'
            '{{ permissions.has_add_permission|for_object:post }}',
            context)
        self.assertEqual(result, 'False')

        post_add_permission = Permission.objects.get(
            content_type__app_label='blog',
            content_type__model='post',
            codename='add_post')
        self.user.user_permissions.add(post_add_permission)
        # invalidate the users permission cache
        if hasattr(self.user, '_perm_cache'):
            del self.user._perm_cache

        # object level permission are not supported by default. So this will
        # return ``False``.
        result = self.render(
            '{% load admin2_tags %}'
            '{{ permissions.has_add_permission }}'
            '{{ permissions.has_add_permission|for_object:post }}',
            context)
        self.assertEqual(result, 'TrueFalse')

        # binding an object and then checking for a specific view also works
        result = self.render(
            '{% load admin2_tags %}'
            '{{ permissions.has_add_permission }}'
            '{% with permissions|for_object:post as permissions %}'
                '{{ permissions.has_add_permission }}'
            '{% endwith %}',
            context)
        self.assertEqual(result, 'TrueFalse')


class ViewPermissionTest(TestCase):
    def test_view_permission_was_created(self):
        permissions = Permission.objects.filter(
            content_type__app_label='blog',
            content_type__model='post')
        self.assertEqual(len(permissions.filter(codename='view_post')), 1)

########NEW FILE########
__FILENAME__ = test_views
# -*- coding: utf-8 -*-
from datetime import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse
from django.test import TestCase, Client

from ..models import Post, Comment


class BaseIntegrationTest(TestCase):
    """
    Base TestCase for integration tests.
    """
    def setUp(self):
        self.client = Client()
        self.user = get_user_model()(username='user', is_staff=True,
                                     is_superuser=True)
        self.user.set_password("password")
        self.user.save()
        self.client.login(username='user', password='password')


class AdminIndexTest(BaseIntegrationTest):
    def test_view_ok(self):
        response = self.client.get(reverse("admin2:dashboard"))
        self.assertContains(response, reverse("admin2:blog_post_index"))


class UserListTest(BaseIntegrationTest):
    def test_search_users_m2m_group(self):
        # This test should cause the distinct search path to exectue
        group = Group.objects.create(name="Test Group")
        self.user.groups.add(group)

        params = {"q": "group"}
        response = self.client.get(reverse("admin2:auth_user_index"), params)
        self.assertContains(response, 'user')


class CommentListTest(BaseIntegrationTest):
    def test_search_comments(self):
        # Test search across Foriegn Keys
        post_1 = Post.objects.create(title="post_1_title", body="body")
        post_2 = Post.objects.create(title="post_2_title", body="another body")
        Comment.objects.create(body="comment_post_1_a", post=post_1)
        Comment.objects.create(body="comment_post_1_b", post=post_1)
        Comment.objects.create(body="comment_post_2", post=post_2)

        params = {"q": "post_1_title"}
        response = self.client.get(reverse("admin2:blog_comment_index"), params)
        self.assertContains(response, "comment_post_1_a")
        self.assertContains(response, "comment_post_1_b")
        self.assertNotContains(response, "comment_post_2")

    def test_list_selected_hides(self):
        post_1 = Post.objects.create(title="post_1_title", body="body")
        Comment.objects.create(body="comment_post1_body", post=post_1)
        response = self.client.get(reverse("admin2:blog_comment_index"))
        self.assertNotContains(response, "of 1 selected")


class PostListTest(BaseIntegrationTest):
    def _create_posts(self):
        Post.objects.bulk_create([
            Post(
                title="post_1_title",
                body="body",
                published_date=datetime(
                    month=7,
                    day=22,
                    year=2013
                )
            ),
            Post(
                title="post_2_title",
                body="body",
                published_date=datetime(
                    month=5,
                    day=20,
                    year=2012,
                )
            ),
            Post(
                title="post_3_title",
                body="body",
                published_date=datetime(
                    month=5,
                    day=30,
                    year=2012,
                ),
            ),
            Post(
                title="post_4_title",
                body="body",
                published_date=datetime(
                    month=6,
                    day=20,
                    year=2012,
                )
            ),
            Post(
                title="post_5_title",
                body="body",
                published_date=datetime(
                    month=6,
                    day=20,
                    year=2012,
                )
            ),
        ])

    def test_view_ok(self):
        post = Post.objects.create(title="A Post Title", body="body")
        response = self.client.get(reverse("admin2:blog_post_index"))
        self.assertContains(response, post.title)

    def test_list_filter_presence(self):
        Post.objects.create(title="post_1_title", body="body")
        Post.objects.create(title="post_2_title", body="another body")
        response = self.client.get(reverse("admin2:blog_post_index"))
        self.assertContains(response, 'id="list_filter_container"')

    def test_list_selected_shows(self):
        Post.objects.create(title="post_1_title", body="body")
        response = self.client.get(reverse("admin2:blog_post_index"))
        self.assertContains(response, 'class="selected-count"')

    def test_actions_displayed(self):
        response = self.client.get(reverse("admin2:blog_post_index"))
        self.assertInHTML('<a tabindex="-1" href="#" data-name="action" data-value="DeleteSelectedAction">Delete selected items</a>', response.content)

    def test_actions_displayed_twice(self):
        # If actions_on_top and actions_on_bottom are both set
        response = self.client.get(reverse("admin2:blog_comment_index"))
        self.assertContains(response, '<div class="navbar actions-top">')
        self.assertContains(response, '<div class="navbar actions-bottom">')

    def test_delete_selected_post(self):
        post = Post.objects.create(title="A Post Title", body="body")
        params = {'action': 'DeleteSelectedAction', 'selected_model_pk': str(post.pk)}
        response = self.client.post(reverse("admin2:blog_post_index"), params)
        # caution : uses pluralization
        self.assertInHTML('<p>Are you sure you want to delete the selected post? The following item will be deleted:</p>', response.content)

    def test_delete_selected_post_confirmation(self):
        post = Post.objects.create(title="A Post Title", body="body")
        params = {'action': 'DeleteSelectedAction', 'selected_model_pk': str(post.pk), 'confirmed': 'yes'}
        response = self.client.post(reverse("admin2:blog_post_index"), params)
        self.assertRedirects(response, reverse("admin2:blog_post_index"))

    def test_delete_selected_post_none_selected(self):
        Post.objects.create(title="A Post Title", body="body")
        params = {'action': 'DeleteSelectedAction'}
        response = self.client.post(reverse("admin2:blog_post_index"), params, follow=True)
        self.assertContains(response, "Items must be selected in order to perform actions on them. No items have been changed.")

    def test_search_posts(self):
        Post.objects.create(title="A Post Title", body="body")
        Post.objects.create(title="Another Post Title", body="body")
        Post.objects.create(title="Post With Keyword In Body", body="another post body")
        params = {"q": "another"}
        response = self.client.get(reverse("admin2:blog_post_index"), params)
        self.assertContains(response, "Another Post Title")
        self.assertContains(response, "Post With Keyword In Body")
        self.assertNotContains(response, "A Post Title")

    def test_renderer_title(self):
        Post.objects.create(title='a lowercase title', body='body', published=False)
        response = self.client.get(reverse('admin2:blog_post_index'))
        self.assertContains(response, 'A Lowercase Title')

    def test_renderer_body(self):
        Post.objects.create(title='title', body='a lowercase body', published=False)
        response = self.client.get(reverse('admin2:blog_post_index'))
        self.assertContains(response, 'a lowercase body')

    def test_renderer_unpublished(self):
        Post.objects.create(title='title', body='body', published=False)
        response = self.client.get(reverse('admin2:blog_post_index'))
        self.assertContains(response, 'icon-minus-sign')

    def test_renderer_published(self):
        Post.objects.create(title='title', body='body', published=True)
        response = self.client.get(reverse('admin2:blog_post_index'))
        self.assertContains(response, 'icon-ok-sign')

    def test_drilldowns(self):
        self._create_posts()

        response = self.client.get(reverse('admin2:blog_post_index'))
        self.assertContains(response, '<a href="?year=2012">2012</a>')
        self.assertContains(response, "<tr>", 5)

        response = self.client.get(
            "%s?%s" % (
                reverse('admin2:blog_post_index'),
                "year=2012",
            )
        )

        self.assertContains(
            response,
            '<a href="?year=2012&month=05">May 2012</a>',
        )
        self.assertContains(
            response,
            'All dates',
        )
        self.assertContains(response, "<tr>", 4)

        response = self.client.get(
            "%s?%s" % (
                reverse('admin2:blog_post_index'),
                "year=2012&month=5",
            )
        )

        self.assertContains(response, "<tr>", 2)
        self.assertContains(
            response,
            '<a href="?year=2012&month=05&day=20">May 20</a>',
        )
        self.assertContains(response, '<a href="?year=2012">')

        response = self.client.get(
            "%s?%s" % (
                reverse('admin2:blog_post_index'),
                "year=2012&month=05&day=20",
            )
        )

        self.assertContains(response, "<tr>", 1)
        self.assertContains(
            response,
            '<a href="?year=2012&month=05&day=20">May 20</a>',
        )
        self.assertContains(
            response,
            '<li class="active">'
        )
        self.assertContains(
            response,
            'May 2012'
        )

    def test_ordering(self):
        self._create_posts()

        response = self.client.get(reverse("admin2:blog_post_index"))

        model_admin = response.context["view"].model_admin
        response_queryset = response.context["object_list"]
        manual_queryset = Post.objects.order_by("-published_date", "title")

        zipped_queryset = zip(
            list(response_queryset),
            list(manual_queryset),
        )

        self.assertTrue(all([
            model1.pk == model2.pk
            for model1, model2 in zipped_queryset
        ]))

        self.assertEqual(
            model_admin.get_ordering(response.request),
            model_admin.ordering,
        )

    def test_all_unselected_action(self):
        self._create_posts()

        response = self.client.get(reverse("admin2:blog_post_index"))

        self.assertTrue(all([
            not post.published
            for post in response.context["object_list"]
        ]))

        response = self.client.post(
            reverse("admin2:blog_post_index"),
            {
                'action': 'PublishAllItemsAction',
            },
            follow=True
        )

        self.assertTrue(all([
            post.published
            for post in response.context["object_list"]
        ]))

        # Test function-based view
        response = self.client.post(
            reverse("admin2:blog_post_index"),
            {
                'action': 'PublishAllItemsAction',
            },
            follow=True,
        )

        self.assertTrue(all([
            post.published
            for post in response.context["object_list"]
        ]))


class PostListTestCustomAction(BaseIntegrationTest):

    def test_publish_action_displayed_in_list(self):
        response = self.client.get(reverse("admin2:blog_post_index"))
        self.assertInHTML('<a tabindex="-1" href="#" data-name="action" data-value="CustomPublishAction">Publish selected items</a>', response.content)

    def test_publish_selected_items(self):
        post = Post.objects.create(title="A Post Title",
                                   body="body",
                                   published=False)
        self.assertEqual(Post.objects.filter(published=True).count(), 0)

        params = {'action': 'CustomPublishAction',
                  'selected_model_pk': str(post.pk),
                  'confirmed': 'yes'}
        response = self.client.post(reverse("admin2:blog_post_index"), params)
        self.assertRedirects(response, reverse("admin2:blog_post_index"))

        self.assertEqual(Post.objects.filter(published=True).count(), 1)

    def test_unpublish_action_displayed_in_list(self):
        response = self.client.get(reverse("admin2:blog_post_index"))
        self.assertInHTML('<a tabindex="-1" href="#" data-name="action" data-value="unpublish_items">Unpublish selected items</a>', response.content)

    def test_unpublish_selected_items(self):
        post = Post.objects.create(title="A Post Title",
                                   body="body",
                                   published=True)
        self.assertEqual(Post.objects.filter(published=True).count(), 1)

        params = {'action': 'unpublish_items',
                  'selected_model_pk': str(post.pk)}
        response = self.client.post(reverse("admin2:blog_post_index"), params)
        self.assertRedirects(response, reverse("admin2:blog_post_index"))

        self.assertEqual(Post.objects.filter(published=True).count(), 0)


class PostDetailViewTest(BaseIntegrationTest):
    def test_view_ok(self):
        post = Post.objects.create(title="A Post Title", body="body")
        response = self.client.get(reverse("admin2:blog_post_detail",
                                           args=(post.pk, )))
        self.assertContains(response, post.title)


class PostCreateViewTest(BaseIntegrationTest):
    def test_view_ok(self):
        response = self.client.get(reverse("admin2:blog_post_create"))
        self.assertNotIn('''enctype="multipart/form-data"''', response.content)
        self.assertEqual(response.status_code, 200)

    def test_create_post(self):
        # Generated by inspecting the request with the pdb debugger
        post_data = {
            "comments-TOTAL_FORMS": u'2',
            "comments-INITIAL_FORMS": u'0',
            "comments-MAX_NUM_FORMS": u'',
            "comments-0-body": u'Comment Body',
            'comments-0-post': '',
            'comments-0-id': '',
            "title": "A Post Title",
            "body": "a_post_body",
        }

        response = self.client.post(reverse("admin2:blog_post_create"),
                                    post_data,
                                    follow=True)
        self.assertTrue(Post.objects.filter(title="A Post Title").exists())
        Comment.objects.get(body="Comment Body")
        self.assertRedirects(response, reverse("admin2:blog_post_index"))

    def test_save_and_add_another_redirects_to_create(self):
        """
        Tests that choosing 'Save and add another' from the model create
        page redirects the user to the model create page.
        """
        post_data = {
            "comments-TOTAL_FORMS": u'2',
            "comments-INITIAL_FORMS": u'0',
            "comments-MAX_NUM_FORMS": u'',
            "comments-0-body": u'Comment Body',
            'comments-0-post': '',
            'comments-0-id': '',
            "title": "A Post Title",
            "body": "a_post_body",
            "_addanother": ""
        }
        self.client.login(username='admin', password='password')
        response = self.client.post(reverse("admin2:blog_post_create"),
                                    post_data)
        Post.objects.get(title='A Post Title')
        self.assertRedirects(response, reverse("admin2:blog_post_create"))

    def test_save_and_continue_editing_redirects_to_update(self):
        """
        Tests that choosing "Save and continue editing" redirects
        the user to the model update form.
        """
        post_data = {
            "comments-TOTAL_FORMS": u'2',
            "comments-INITIAL_FORMS": u'0',
            "comments-MAX_NUM_FORMS": u'',
            "title": "Unique",
            "body": "a_post_body",
            "_continue": ""
        }
        response = self.client.post(reverse("admin2:blog_post_create"),
                                    post_data)
        post = Post.objects.get(title="Unique")
        self.assertRedirects(response, reverse("admin2:blog_post_update",
                                               args=(post.pk, )))


class PostDeleteViewTest(BaseIntegrationTest):
    def test_view_ok(self):
        post = Post.objects.create(title="A Post Title", body="body")
        response = self.client.get(reverse("admin2:blog_post_delete",
                                           args=(post.pk, )))
        self.assertContains(response, post.title)

    def test_delete_post(self):
        post = Post.objects.create(title="A Post Title", body="body")
        response = self.client.post(reverse("admin2:blog_post_delete",
                                            args=(post.pk, )))
        self.assertRedirects(response, reverse("admin2:blog_post_index"))
        self.assertFalse(Post.objects.filter(pk=post.pk).exists())


class PostDeleteActionTest(BaseIntegrationTest):
    """
    Tests the behaviour of the 'Delete selected items' action.
    """
    def test_confirmation_page(self):
        p1 = Post.objects.create(title="A Post Title", body="body")
        p2 = Post.objects.create(title="A Post Title", body="body")
        post_data = {
            'action': 'DeleteSelectedAction',
            'selected_model_pk': [p1.pk, p2.pk]
        }
        response = self.client.post(reverse("admin2:blog_post_index"),
                                    post_data)
        self.assertContains(response, p1.title)
        self.assertContains(response, p2.title)

    def test_results_page(self):
        p1 = Post.objects.create(title="A Post Title", body="body")
        p2 = Post.objects.create(title="A Post Title", body="body")
        post_data = {
            'action': 'DeleteSelectedAction',
            'selected_model_pk': [p1.pk, p2.pk],
            'confirmed': 'yes'
        }
        response = self.client.post(reverse("admin2:blog_post_index"),
                                    post_data, follow=True)
        self.assertContains(response, "Successfully deleted 2 post")


class TestAuthViews(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = get_user_model()(username='user', is_staff=True,
                                     is_superuser=True)
        self.user.set_password("password")
        self.user.save()

    def test_login_required_redirect_to_index(self):
        index_path = reverse('admin2:dashboard') + '?next=/admin2/blog/post/'
        target_path = reverse('admin2:blog_post_index')
        self.assertRedirects(self.client.get(target_path), index_path)

    def test_login_required_logined_successful(self):
        index_path = reverse('admin2:dashboard')
        self.client.login(username=self.user.username,
                          password='password')
        self.assertContains(self.client.get(index_path),
                            reverse('admin2:blog_post_index'))

    def test_change_password_for_myself(self):
        self.client.login(username=self.user.username,
                          password='password')
        request = self.client.post(reverse('admin2:password_change',
                                           kwargs={'pk': self.user.pk}),
                                   {'old_password': 'password',
                                    'new_password1': 'user',
                                    'new_password2': 'user'})
        self.assertRedirects(request, reverse('admin2:password_change_done'))
        self.client.logout()

        self.assertFalse(self.client.login(username=self.user.username,
                                           password='password'))
        self.assertTrue(self.client.login(username=self.user.username,
                                          password='user'))

    def test_change_password(self):
        self.client.login(username=self.user.username,
                          password='password')

        new_user = get_user_model()(username='new_user')
        new_user.set_password("new_user")
        new_user.save()

        request = self.client.post(reverse('admin2:password_change',
                                           kwargs={'pk': new_user.pk}),
                                   {'old_password': 'new_user',
                                    'password1': 'new_user_password',
                                    'password2': 'new_user_password'})
        self.assertRedirects(request, reverse('admin2:password_change_done'))
        self.client.logout()

        self.assertFalse(self.client.login(username=new_user.username,
                                           password='new_user'))
        self.assertTrue(self.client.login(username=new_user.username,
                                          password='new_user_password'))

    def test_logout(self):
        self.client.login(username=self.user.username,
                          password='password')
        logout_path = reverse('admin2:logout')
        request = self.client.get(logout_path)
        self.assertContains(request, 'Log in again')

        index_path = reverse('admin2:dashboard') + '?next=/admin2/blog/post/'
        target_path = reverse('admin2:blog_post_index')
        self.assertRedirects(self.client.get(target_path), index_path)

########NEW FILE########
__FILENAME__ = views
#from django.shortcuts import render
from django.views.generic import ListView, DetailView

from .models import Post


class BlogListView(ListView):
    model = Post
    template_name = 'blog_list.html'


class BlogDetailView(DetailView):
    model = Post
    template_name = 'blog_detail.html'

########NEW FILE########
__FILENAME__ = settings
# Django settings for example project.
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'example.db',
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
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
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(BASE_DIR, "static"),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '*ymubzn8p_s7vrm%jsqvr6$qnea_5mcp(ao0z-yh1q0gro!0g1'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'example.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'example.wsgi.application'

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
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'floppyforms',
    'rest_framework',
    'crispy_forms',
    'djadmin2',
    'djadmin2.themes.djadmin2theme_default',
    'blog',
    'files',
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


ADMIN2_THEME_DIRECTORY = "djadmin2theme_default"


########## TOOLBAR CONFIGURATION
# See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
INSTALLED_APPS += (
    'debug_toolbar',
)

# See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
INTERNAL_IPS = ('127.0.0.1',)

# See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
MIDDLEWARE_CLASSES += (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
    'SHOW_TEMPLATE_CONTEXT': True,
}
########## END TOOLBAR CONFIGURATION

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.contrib import admin

from blog.views import BlogListView, BlogDetailView

admin.autodiscover()

import djadmin2

djadmin2.default.autodiscover()

urlpatterns = patterns('',
    url(r'^admin2/', include(djadmin2.default.urls)),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^blog/', BlogListView.as_view(template_name="blog/blog_list.html"), name='blog_list'),
    url(r'^blog/detail(?P<pk>\d+)/$', BlogDetailView.as_view(template_name="blog/blog_detail.html"), name='blog_detail'),
    url(r'^$', BlogListView.as_view(template_name="blog/home.html"), name='home'),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for example project.

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

# We defer to a DJANGO_SETTINGS_MODULE already in the environment. This breaks
# if running multiple sites in the same mod_wsgi process. To fix this, use
# mod_wsgi daemon mode with each site in its own daemon process, or use
# os.environ["DJANGO_SETTINGS_MODULE"] = "example.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = admin
# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, unicode_literals

from django.contrib import admin

from .models import CaptionedFile, UncaptionedFile


admin.site.register(CaptionedFile)
admin.site.register(UncaptionedFile)

########NEW FILE########
__FILENAME__ = admin2
# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, unicode_literals

import djadmin2

from .models import CaptionedFile, UncaptionedFile


djadmin2.default.register(CaptionedFile)
djadmin2.default.register(UncaptionedFile)

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _


class CaptionedFile(models.Model):
    caption = models.CharField(max_length=200, verbose_name=_('caption'))
    publication = models.FileField(upload_to='media', verbose_name=_('Uploaded File'))

    def __unicode__(self):
        return self.caption

    class Meta:
        verbose_name = _('Captioned File')
        verbose_name_plural = _('Captioned Files')


class UncaptionedFile(models.Model):
    publication = models.FileField(upload_to='media', verbose_name=_('Uploaded File'))

    def __unicode__(self):
        return unicode(self.publication)

    class Meta:
        verbose_name = _('Uncaptioned File')
        verbose_name_plural = _('Uncaptioned Files')

########NEW FILE########
__FILENAME__ = test_models
from django.test import TestCase
from django.utils import timezone

from files.models import CaptionedFile
from files.models import UncaptionedFile


from os import path


fixture_dir = path.join(path.abspath(path.dirname(__file__)), 'fixtures')


class CaptionedFileTestCase(TestCase):

    def setUp(self):
        self.captioned_file = CaptionedFile.objects.create(
            caption="this is a file",
            publication=path.join('pubtest.txt')
        )
        self.captioned_file.save()

    def test_creation(self):
        cf = CaptionedFile.objects.create(
            caption="lo lo",
            publication=path.join('pubtest.txt')
        )
        cf.save()
        self.assertEqual(CaptionedFile.objects.count(), 2)
        # Cause setup created one already

    def test_update(self):
        self.captioned_file.caption = "I like text files"
        self.captioned_file.save()

        cf = CaptionedFile.objects.get()
        self.assertEqual(cf.caption, "I like text files")

    def test_delete(self):
        cf = CaptionedFile.objects.get()
        cf.delete()

        self.assertEqual(CaptionedFile.objects.count(), 0)


class MultiEncodedAdminFormTest(TestCase):
    def setUp(self):
        self.user = User(
            username='admin',
            is_staff=True,
            is_superuser=True)
        self.user.set_password('admin')
        self.user.save()
        self.create_url = reverse('admin2:example3_captioned_file_create')

########NEW FILE########
__FILENAME__ = test_views
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.test import TestCase, Client
from django.utils import timezone

from ..models import CaptionedFile

from os import path

fixture_dir = path.join(path.abspath(path.dirname(__file__)), 'fixtures')
fixture_file = path.join(fixture_dir, 'pubtest.txt')


class BaseIntegrationTest(TestCase):
    """
    Base TestCase for integration tests.
    """
    def setUp(self):
        self.client = Client()
        self.user = get_user_model()(username='user', is_staff=True,
                                     is_superuser=True)
        self.user.set_password("password")
        self.user.save()
        self.client.login(username='user', password='password')


class AdminIndexTest(BaseIntegrationTest):
    def test_view_ok(self):
        response = self.client.get(reverse("admin2:dashboard"))
        self.assertContains(response, reverse("admin2:files_captionedfile_index"))


class CaptionedFileListTest(BaseIntegrationTest):
    def test_view_ok(self):
        captioned_file = CaptionedFile.objects.create(caption="some file", publication=fixture_file)
        response = self.client.get(reverse("admin2:files_captionedfile_index"))
        self.assertContains(response, captioned_file.caption)

    def test_actions_displayed(self):
        response = self.client.get(reverse("admin2:files_captionedfile_index"))
        self.assertInHTML('<a tabindex="-1" href="#" data-name="action" data-value="DeleteSelectedAction">Delete selected items</a>', response.content)

    def test_delete_selected_captioned_file(self):
        captioned_file = CaptionedFile.objects.create(caption="some file", publication=fixture_file)
        params = {'action': 'DeleteSelectedAction', 'selected_model_pk': str(captioned_file.pk)}
        response = self.client.post(reverse("admin2:files_captionedfile_index"), params)
        self.assertInHTML('<p>Are you sure you want to delete the selected Captioned File? The following item will be deleted:</p>', response.content)

    def test_delete_selected_captioned_file_confirmation(self):
        captioned_file = CaptionedFile.objects.create(caption="some file", publication=fixture_file)
        params = {'action': 'DeleteSelectedAction', 'selected_model_pk': str(captioned_file.pk), 'confirmed': 'yes'}
        response = self.client.post(reverse("admin2:files_captionedfile_index"), params)
        self.assertRedirects(response, reverse("admin2:files_captionedfile_index"))

    def test_delete_selected_captioned_file_none_selected(self):
        CaptionedFile.objects.create(caption="some file", publication=fixture_file)
        params = {'action': 'DeleteSelectedAction'}
        response = self.client.post(reverse("admin2:files_captionedfile_index"), params, follow=True)
        self.assertContains(response, "Items must be selected in order to perform actions on them. No items have been changed.")


class CaptionedFileDetailViewTest(BaseIntegrationTest):
    def test_view_ok(self):
        captioned_file = CaptionedFile.objects.create(caption="some file", publication=fixture_file)
        response = self.client.get(reverse("admin2:files_captionedfile_detail", args=(captioned_file.pk, )))
        self.assertContains(response, captioned_file.caption)


class CaptionedFileCreateViewTest(BaseIntegrationTest):
    def test_view_ok(self):
        response = self.client.get(reverse("admin2:files_captionedfile_create"))
        self.assertIn('''enctype="multipart/form-data"''', response.content)
        self.assertEqual(response.status_code, 200)

    def test_create_captioned_file(self):
        with open(fixture_file, 'r') as fp:
            params = {
                "caption": "some file",
                "publication": fp,
            }
            response = self.client.post(reverse("admin2:files_captionedfile_create"),
                                        params,
                                        follow=True)
        self.assertTrue(CaptionedFile.objects.filter(caption="some file").exists())
        self.assertRedirects(response, reverse("admin2:files_captionedfile_index"))

    def test_save_and_add_another_redirects_to_create(self):
        """
        Tests that choosing 'Save and add another' from the model create
        page redirects the user to the model create page.
        """
        with open(fixture_file, 'r') as fp:
            params = {
                "caption": "some file",
                "publication": fp,
                "_addanother": ""
            }
            response = self.client.post(reverse("admin2:files_captionedfile_create"),
                                        params)
        self.assertTrue(CaptionedFile.objects.filter(caption="some file").exists())
        self.assertRedirects(response, reverse("admin2:files_captionedfile_create"))

    def test_save_and_continue_editing_redirects_to_update(self):
        """
        Tests that choosing "Save and continue editing" redirects
        the user to the model update form.
        """
        with open(fixture_file, 'r') as fp:
            params = {
                "caption": "some file",
                "publication": fp,
                "_continue": ""
            }
            response = self.client.post(reverse("admin2:files_captionedfile_create"),
                                        params)
        captioned_file = CaptionedFile.objects.get(caption="some file")
        self.assertRedirects(response, reverse("admin2:files_captionedfile_update",
                                               args=(captioned_file.pk, )))


class CaptionedFileDeleteViewTest(BaseIntegrationTest):
    def test_view_ok(self):
        captioned_file = CaptionedFile.objects.create(caption="some file", publication=fixture_file)
        response = self.client.get(reverse("admin2:files_captionedfile_delete",
                                           args=(captioned_file.pk, )))
        self.assertContains(response, captioned_file.caption)

    def test_delete_captioned_file(self):
        captioned_file = CaptionedFile.objects.create(caption="some file", publication=fixture_file)
        response = self.client.post(reverse("admin2:files_captionedfile_delete",
                                            args=(captioned_file.pk, )))
        self.assertRedirects(response, reverse("admin2:files_captionedfile_index"))
        self.assertFalse(CaptionedFile.objects.filter(pk=captioned_file.pk).exists())


class FileDeleteActionTest(BaseIntegrationTest):
    """
    Tests the behaviour of the 'Delete selected items' action.
    """
    def test_confirmation_page(self):
        cf1 = captioned_file = CaptionedFile.objects.create(caption="some file", publication=fixture_file)
        cf2 = captioned_file = CaptionedFile.objects.create(caption="some file", publication=fixture_file)
        params = {
            'action': 'DeleteSelectedAction',
            'selected_model_pk': [cf1.pk, cf2.pk]
        }
        response = self.client.post(reverse("admin2:files_captionedfile_index"),
                                    params)
        self.assertContains(response, cf1.caption)
        self.assertContains(response, cf2.caption)

    def test_results_page(self):
        cf1 = captioned_file = CaptionedFile.objects.create(caption="some file", publication=fixture_file)
        cf2 = captioned_file = CaptionedFile.objects.create(caption="some file", publication=fixture_file)
        params = {
            'action': 'DeleteSelectedAction',
            'selected_model_pk': [cf1.pk, cf2.pk],
            'confirmed': 'yes'
        }
        response = self.client.post(reverse("admin2:files_captionedfile_index"),
                                    params, follow=True)
        self.assertContains(response, "Successfully deleted 2 Captioned Files")

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
# Django settings for example2 project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'example2.db',
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
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
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
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
SECRET_KEY = 'vid$84s%19vhcss+(n$*pbc=nad2oab@^2s532_iesz2f6q=(z'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'example2.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'example2.wsgi.application'

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
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'floppyforms',
    'rest_framework',
    'djadmin2',
    'djadmin2.themes.djadmin2theme_default',
    'crispy_forms',
    'polls',
)

try:
    import django_extensions
    INSTALLED_APPS += (
        'django_extensions',
    )
except ImportError:
    pass

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


ADMIN2_THEME_DIRECTORY = "djadmin2theme_default"

########## TOOLBAR CONFIGURATION
# See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
INSTALLED_APPS += (
    'debug_toolbar',
)

# See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
INTERNAL_IPS = ('127.0.0.1',)

# See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
MIDDLEWARE_CLASSES += (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
    'SHOW_TEMPLATE_CONTEXT': True,
}
########## END TOOLBAR CONFIGURATION

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.views.generic import TemplateView

admin.autodiscover()

import djadmin2

djadmin2.default.autodiscover()

urlpatterns = patterns('',
    url(r'^admin2/', include(djadmin2.default.urls)),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^$', TemplateView.as_view(template_name="home.html")),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for example2 project.

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

# We defer to a DJANGO_SETTINGS_MODULE already in the environment. This breaks
# if running multiple sites in the same mod_wsgi process. To fix this, use
# mod_wsgi daemon mode with each site in its own daemon process, or use
# os.environ["DJANGO_SETTINGS_MODULE"] = "example2.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example2.settings")

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
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example2.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = admin
# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, unicode_literals

from django.contrib import admin

from .models import Poll, Choice


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 3


class PollAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['question']}),
        ('Date information', {'fields': ['pub_date'], 'classes': ['collapse']}),
    ]
    inlines = [ChoiceInline]
    list_display = ('question', 'pub_date', 'was_published_recently')
    list_filter = ['pub_date']
    search_fields = ['question']
    date_hierarchy = 'pub_date'


admin.site.register(Poll, PollAdmin)

########NEW FILE########
__FILENAME__ = admin2
# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, unicode_literals

import djadmin2

from .models import Poll, Choice


class ChoiceInline(djadmin2.Admin2TabularInline):
    model = Choice
    extra = 3


class PollAdmin(djadmin2.ModelAdmin2):
    fieldsets = [
        (None, {'fields': ['question']}),
        ('Date information', {'fields': ['pub_date'], 'classes': ['collapse']}),
    ]
    inlines = [ChoiceInline]
    list_display = ('question', 'pub_date', 'was_published_recently')
    list_filter = ['pub_date']
    search_fields = ['question']
    date_hierarchy = 'pub_date'


djadmin2.default.register(Poll, PollAdmin)

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from __future__ import division, absolute_import, unicode_literals

import datetime

from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _


class Poll(models.Model):
    question = models.CharField(max_length=200, verbose_name=_('question'))
    pub_date = models.DateTimeField(verbose_name=_('date published'))

    def __unicode__(self):
        return self.question

    def was_published_recently(self):
        return self.pub_date >= timezone.now() - datetime.timedelta(days=1)
    was_published_recently.admin_order_field = 'pub_date'
    was_published_recently.boolean = True
    was_published_recently.short_description = _('Published recently?')

    class Meta:
        verbose_name = _('poll')
        verbose_name_plural = _('polls')


class Choice(models.Model):
    poll = models.ForeignKey(Poll, verbose_name=_('poll'))
    choice_text = models.CharField(max_length=200, verbose_name=_('choice text'))
    votes = models.IntegerField(default=0, verbose_name=_('votes'))

    def __unicode__(self):
        return self.choice_text

    class Meta:
        verbose_name = _('choice')
        verbose_name_plural = _('choices')

########NEW FILE########
__FILENAME__ = test_models
from django.test import TestCase
from django.utils import timezone

from polls.models import Poll
from polls.models import Choice


class PollTestCase(TestCase):

    def setUp(self):
        self.poll = Poll.objects.create(
            question="mine",
            pub_date=timezone.now()
        )
        self.poll.save()

    def test_creation(self):
        p = Poll.objects.create(
            question="lo lo",
            pub_date=timezone.now()
        )
        p.save()
        self.assertEqual(Poll.objects.count(), 2)
        # Cause setup created one already

    def test_update(self):
        # TODO Add code
        # change self.poll.question to "yours"
        self.poll.question = "yours"
        # do self.poll.save()
        self.poll.save()

        # TODO Add assertions
        # make p = Poll.objects.get()
        p = Poll.objects.get()
        # add self.assertEqual(p.question, "yours")
        self.assertEqual(p.question, "yours")

    def test_delete(self):
        # TODO Add code
        # get from the db using poll question
        p = Poll.objects.get()
        # delete poll from the db
        p.delete()

        # TODO Add assertions
        # check if d is empty
        self.assertEqual(Poll.objects.count(), 0)


class ChoiceTestCase(TestCase):

    def setUp(self):
        self.poll = Poll.objects.create(
            question="mine",
            pub_date=timezone.now()
        )
        self.poll.save()
        self.choice = Choice.objects.create(
            poll=self.poll,
            choice_text="first text",
            votes=2
        )

    def test_choice_creation(self):
        # code
        # add another choice
        p = Choice.objects.create(
            poll=self.poll,
            choice_text="second text",
            votes=5
        )
        p.save()

        # assertion
        #check that there are two choices
        self.assertEqual(Choice.objects.count(), 2)

    def test_choice_update(self):
        # code
        # change a choice
        self.choice.choice_text = "third text"
        self.choice.save()
        p = Choice.objects.get()

        # assertion
        # check the choice is egal to the new choice
        self.assertEqual(p.choice_text, "third text")

    def test_choice_delete(self):
        # code
        # get Choice obj and delete it
        p = Choice.objects.get()
        p.delete()

        # assertion
        # check there are nothing in db
        self.assertEqual(Choice.objects.count(), 0)

########NEW FILE########
__FILENAME__ = test_views
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.test import TestCase, Client
from django.utils import timezone

from ..models import Poll


class BaseIntegrationTest(TestCase):
    """
    Base TestCase for integration tests.
    """
    def setUp(self):
        self.client = Client()
        self.user = get_user_model()(username='user', is_staff=True,
                                     is_superuser=True)
        self.user.set_password("password")
        self.user.save()
        self.client.login(username='user', password='password')


class AdminIndexTest(BaseIntegrationTest):
    def test_view_ok(self):
        response = self.client.get(reverse("admin2:dashboard"))
        self.assertContains(response, reverse("admin2:polls_poll_index"))


class PollListTest(BaseIntegrationTest):
    def test_view_ok(self):
        poll = Poll.objects.create(question="some question", pub_date=timezone.now())
        response = self.client.get(reverse("admin2:polls_poll_index"))
        self.assertContains(response, poll.question)

    def test_actions_displayed(self):
        response = self.client.get(reverse("admin2:polls_poll_index"))
        self.assertInHTML('<a tabindex="-1" href="#" data-name="action" data-value="DeleteSelectedAction">Delete selected items</a>', response.content)

    def test_delete_selected_poll(self):
        poll = Poll.objects.create(question="some question", pub_date=timezone.now())
        params = {'action': 'DeleteSelectedAction', 'selected_model_pk': str(poll.pk)}
        response = self.client.post(reverse("admin2:polls_poll_index"), params)
        self.assertInHTML('<p>Are you sure you want to delete the selected poll? All of the following items will be deleted:</p>', response.content)

    def test_delete_selected_poll_confirmation(self):
        poll = Poll.objects.create(question="some question", pub_date=timezone.now())
        params = {'action': 'DeleteSelectedAction', 'selected_model_pk': str(poll.pk), 'confirmed': 'yes'}
        response = self.client.post(reverse("admin2:polls_poll_index"), params)
        self.assertRedirects(response, reverse("admin2:polls_poll_index"))

    def test_delete_selected_poll_none_selected(self):
        Poll.objects.create(question="some question", pub_date=timezone.now())
        params = {'action': 'DeleteSelectedAction'}
        response = self.client.post(reverse("admin2:polls_poll_index"), params, follow=True)
        self.assertContains(response, "Items must be selected in order to perform actions on them. No items have been changed.")


class PollDetailViewTest(BaseIntegrationTest):
    def test_view_ok(self):
        poll = Poll.objects.create(question="some question", pub_date=timezone.now())
        response = self.client.get(reverse("admin2:polls_poll_detail", args=(poll.pk, )))
        self.assertContains(response, poll.question)


class PollCreateViewTest(BaseIntegrationTest):
    def test_view_ok(self):
        response = self.client.get(reverse("admin2:polls_poll_create"))
        self.assertEqual(response.status_code, 200)

    def test_create_poll(self):
        params = {
            "question": "some question",
            "pub_date": "2012-01-01",
            "choice_set-TOTAL_FORMS": u'0',
            "choice_set-INITIAL_FORMS": u'0',
            "choice_set-MAX_NUM_FORMS": u'',
        }
        response = self.client.post(reverse("admin2:polls_poll_create"),
                                    params,
                                    follow=True)
        self.assertTrue(Poll.objects.filter(question="some question").exists())
        self.assertRedirects(response, reverse("admin2:polls_poll_index"))

    def test_save_and_add_another_redirects_to_create(self):
        """
        Tests that choosing 'Save and add another' from the model create
        page redirects the user to the model create page.
        """
        params = {
            "question": "some question",
            "pub_date": "2012-01-01",
            "choice_set-TOTAL_FORMS": u'0',
            "choice_set-INITIAL_FORMS": u'0',
            "choice_set-MAX_NUM_FORMS": u'',
            "_addanother": ""
        }
        response = self.client.post(reverse("admin2:polls_poll_create"),
                                    params)
        self.assertTrue(Poll.objects.filter(question="some question").exists())
        self.assertRedirects(response, reverse("admin2:polls_poll_create"))

    def test_save_and_continue_editing_redirects_to_update(self):
        """
        Tests that choosing "Save and continue editing" redirects
        the user to the model update form.
        """
        params = {
            "question": "some question",
            "pub_date": "2012-01-01",
            "choice_set-TOTAL_FORMS": u'0',
            "choice_set-INITIAL_FORMS": u'0',
            "choice_set-MAX_NUM_FORMS": u'',
            "_continue": ""
        }
        response = self.client.post(reverse("admin2:polls_poll_create"),
                                    params)
        poll = Poll.objects.get(question="some question")
        self.assertRedirects(response, reverse("admin2:polls_poll_update",
                                               args=(poll.pk, )))


class PollDeleteViewTest(BaseIntegrationTest):
    def test_view_ok(self):
        poll = Poll.objects.create(question="some question", pub_date=timezone.now())
        response = self.client.get(reverse("admin2:polls_poll_delete",
                                           args=(poll.pk, )))
        self.assertContains(response, poll.question)

    def test_delete_poll(self):
        poll = Poll.objects.create(question="some question", pub_date=timezone.now())
        response = self.client.post(reverse("admin2:polls_poll_delete",
                                            args=(poll.pk, )))
        self.assertRedirects(response, reverse("admin2:polls_poll_index"))
        self.assertFalse(Poll.objects.filter(pk=poll.pk).exists())


class PollDeleteActionTest(BaseIntegrationTest):
    """
    Tests the behaviour of the 'Delete selected items' action.
    """
    def test_confirmation_page(self):
        p1 = Poll.objects.create(question="some question", pub_date=timezone.now())
        p2 = Poll.objects.create(question="some question", pub_date=timezone.now())
        params = {
            'action': 'DeleteSelectedAction',
            'selected_model_pk': [p1.pk, p2.pk]
        }
        response = self.client.post(reverse("admin2:polls_poll_index"),
                                    params)
        self.assertContains(response, p1.question)
        self.assertContains(response, p2.question)

    def test_results_page(self):
        p1 = Poll.objects.create(question="some question", pub_date=timezone.now())
        p2 = Poll.objects.create(question="some question", pub_date=timezone.now())
        params = {
            'action': 'DeleteSelectedAction',
            'selected_model_pk': [p1.pk, p2.pk],
            'confirmed': 'yes'
        }
        response = self.client.post(reverse("admin2:polls_poll_index"),
                                    params, follow=True)
        self.assertContains(response, "Successfully deleted 2 polls")

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = fabfile
# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import, unicode_literals

from fabric.api import local, lcd
from fabric.contrib.console import confirm


DIRS = ['djadmin2', 'example/blog', 'example2/polls']


def _run(command, directory):
    with lcd(directory):
        print('\n### Processing %s...' % directory)
        local(command)


def makemessages():
    command = 'django-admin.py makemessages -a'
    for d in DIRS:
        _run(command, d)


def compilemessages():
    command = 'django-admin.py compilemessages'
    for d in DIRS:
        _run(command, d)


def checkmessages():
    command = 'ls -1 locale/*/LC_MESSAGES/django.po | xargs -I {} msgfmt -c {}'
    for d in DIRS:
        _run(command, d)


def pulltx():
    print('\n### Pulling new translations from Transifex...')
    local('tx pull -a')


def pushtx():
    print('\n### Pushing translations and sources to Transifex...')
    print('Warning: This might destroy existing translations. Probably you should pull first.')
    if confirm('Continue anyways?', default=False):
        local('tx push -s -t')
    else:
        print('Aborting.')

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'example.settings'
exampleproject_dir = os.path.join(os.path.dirname(__file__), 'example')
sys.path.insert(0, exampleproject_dir)

from django.test.utils import get_runner
from django.conf import settings


def runtests(tests=('blog', 'files', 'djadmin2')):
    '''
    Takes a list as first argument, enumerating the apps and specific testcases
    that should be executed. The syntax is the same as for what you would pass
    to the ``django-admin.py test`` command.

    Examples::

        # run the default test suite
        runtests()

        # only run the tests from application ``blog``
        runtests(['blog'])

        # only run testcase class ``Admin2Test`` from app ``djadmin2``
        runtests(['djadmin2.Admin2Test'])

        # run all tests from application ``blog`` and the test named
        # ``test_register`` on the ``djadmin2.Admin2Test`` testcase.
        runtests(['djadmin2.Admin2Test.test_register', 'blog'])
    '''
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=1, interactive=True)
    failures = test_runner.run_tests(tests)
    sys.exit(bool(failures))


if __name__ == '__main__':
    if len(sys.argv) > 1:
        tests = sys.argv[1:]
        runtests(tests)
    else:
        runtests()

########NEW FILE########
