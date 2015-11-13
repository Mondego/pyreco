__FILENAME__ = actions
"""
Built-in, globally-available admin actions.
"""

from django import template
from django.core.exceptions import PermissionDenied
from django.contrib.admin import helpers
from django.contrib.admin.util import get_deleted_objects, model_ngettext
from django.db import router
from django.shortcuts import render_to_response
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext_lazy, ugettext as _
from django.db import models

from django.contrib.admin.actions import delete_selected as django_delete_selected

def delete_selected(modeladmin, request, queryset):
    if issubclass(modeladmin.model, models.Model):
        return django_delete_selected(modeladmin, request, queryset)
    else:
        return _delete_selected(modeladmin, request, queryset)

def _delete_selected(modeladmin, request, queryset):
    """
    Default action which deletes the selected objects.

    This action first displays a confirmation page whichs shows all the
    deleteable objects, or, if the user has no permission one of the related
    childs (foreignkeys), a "permission denied" message.

    Next, it delets all selected objects and redirects back to the change list.
    """
    opts = modeladmin.model._meta
    app_label = opts.app_label

    # Check that the user has delete permission for the actual model
    if not modeladmin.has_delete_permission(request):
        raise PermissionDenied

    using = router.db_for_write(modeladmin.model)

    # Populate deletable_objects, a data structure of all related objects that
    # will also be deleted.
    # TODO: Permissions would be so cool...
    deletable_objects, perms_needed, protected = get_deleted_objects(
        queryset, opts, request.user, modeladmin.admin_site, using)

    # The user has already confirmed the deletion.
    # Do the deletion and return a None to display the change list view again.
    if request.POST.get('post'):
        if perms_needed:
            raise PermissionDenied
        n = len(queryset)
        if n:
            for obj in queryset:
                obj_display = force_unicode(obj)
                modeladmin.log_deletion(request, obj, obj_display)
                # call the objects delete method to ensure signals are
                # processed.
                obj.delete()
            # This is what you get if you have to monkey patch every object in a changelist
            # No queryset object, I can tell ya. So we get a new one and delete that. 
            #pk_list = [o.pk for o in queryset]
            #klass = queryset[0].__class__
            #qs = klass.objects.filter(pk__in=pk_list)
            #qs.delete()
            modeladmin.message_user(request, _("Successfully deleted %(count)d %(items)s.") % {
                "count": n, "items": model_ngettext(modeladmin.opts, n)
            })
        # Return None to display the change list page again.
        return None

    if len(queryset) == 1:
        objects_name = force_unicode(opts.verbose_name)
    else:
        objects_name = force_unicode(opts.verbose_name_plural)

    if perms_needed or protected:
        title = _("Cannot delete %(name)s") % {"name": objects_name}
    else:
        title = _("Are you sure?")

    context = {
        "title": title,
        "objects_name": objects_name,
        "deletable_objects": [deletable_objects],
        'queryset': queryset,
        "perms_lacking": perms_needed,
        "protected": protected,
        "opts": opts,
        "root_path": modeladmin.admin_site.root_path,
        "app_label": app_label,
        'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
    }
    
    # Display the confirmation page
    return render_to_response(modeladmin.delete_selected_confirmation_template or [
        "admin/%s/%s/delete_selected_confirmation.html" % (app_label, opts.object_name.lower()),
        "admin/%s/delete_selected_confirmation.html" % app_label,
        "admin/delete_selected_confirmation.html"
    ], context, context_instance=template.RequestContext(request))

delete_selected.short_description = ugettext_lazy("Delete selected %(verbose_name_plural)s")

########NEW FILE########
__FILENAME__ = helpers
from django.contrib.admin.util import lookup_field
from django.contrib.admin.helpers import AdminForm as DjangoAdminForm
from django.contrib.admin.helpers import Fieldset as DjangoFieldSet
from django.contrib.admin.helpers import Fieldline as DjangoFieldLine
from django.contrib.admin.helpers import AdminReadonlyField as DjangoAdminReadonlyField
from django.contrib.admin.helpers import InlineAdminForm as DjangoInlineAdminForm
from django.contrib.admin.helpers import InlineAdminFormSet as DjangoInlineAdminFormSet
from django.contrib.admin.helpers import InlineFieldset as DjangoInlineFieldset
from django.contrib.admin.helpers import AdminField
from django.core.exceptions import ObjectDoesNotExist

from django.utils.encoding import smart_unicode
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from django_mongoengine.admin.util import (display_for_field,
        label_for_field, help_text_for_field)


class AdminForm(DjangoAdminForm):
    def __iter__(self):
        for name, options in self.fieldsets:
            yield Fieldset(self.form, name,
                readonly_fields=self.readonly_fields,
                model_admin=self.model_admin,
                **options
            )


class Fieldset(DjangoFieldSet):
    def __iter__(self):
        for field in self.fields:
            yield Fieldline(self.form, field, self.readonly_fields, model_admin=self.model_admin)


class Fieldline(DjangoFieldLine):
    def __iter__(self):
        for i, field in enumerate(self.fields):
            if field in self.readonly_fields:
                yield AdminReadonlyField(self.form, field, is_first=(i == 0),
                    model_admin=self.model_admin)
            else:
                yield AdminField(self.form, field, is_first=(i == 0))


class AdminReadonlyField(DjangoAdminReadonlyField):
    def __init__(self, form, field, is_first, model_admin=None):
        label = label_for_field(field, form._meta.model, model_admin)
        # Make self.field look a little bit like a field. This means that
        # {{ field.name }} must be a useful class name to identify the field.
        # For convenience, store other field-related data here too.
        if callable(field):
            class_name = field.__name__ != '<lambda>' and field.__name__ or ''
        else:
            class_name = field
        self.field = {
            'name': class_name,
            'label': label,
            'field': field,
            'help_text': help_text_for_field(class_name, form._meta.model)
        }
        self.form = form
        self.model_admin = model_admin
        self.is_first = is_first
        self.is_checkbox = False
        self.is_readonly = True

    def contents(self):
        from django.contrib.admin.templatetags.admin_list import _boolean_icon
        from django.contrib.admin.views.main import EMPTY_CHANGELIST_VALUE
        field, obj, model_admin = self.field['field'], self.form.instance, self.model_admin
        try:
            f, attr, value = lookup_field(field, obj, model_admin)
        except (AttributeError, ValueError, ObjectDoesNotExist):
            result_repr = EMPTY_CHANGELIST_VALUE
        else:
            if f is None:
                boolean = getattr(attr, "boolean", False)
                if boolean:
                    result_repr = _boolean_icon(value)
                else:
                    result_repr = smart_unicode(value)
                    if getattr(attr, "allow_tags", False):
                        result_repr = mark_safe(result_repr)
            else:
                if value is None:
                    result_repr = EMPTY_CHANGELIST_VALUE
                #HERE WE NEED TO CHANGE THIS TEST
                # elif isinstance(f.rel, ManyToManyRel):
                #     result_repr = ", ".join(map(unicode, value.all()))
                else:
                    result_repr = display_for_field(value, f)
        return conditional_escape(result_repr)


class InlineAdminFormSet(DjangoInlineAdminFormSet):
    """
    A wrapper around an inline formset for use in the admin system.
    """
    def __iter__(self):
        for form, original in zip(self.formset.initial_forms, self.formset.get_queryset()):
            yield InlineAdminForm(self.formset, form, self.fieldsets,
                self.opts.prepopulated_fields, original, self.readonly_fields,
                model_admin=self.opts)
        for form in self.formset.extra_forms:
            yield InlineAdminForm(self.formset, form, self.fieldsets,
                self.opts.prepopulated_fields, None, self.readonly_fields,
                model_admin=self.opts)
        yield InlineAdminForm(self.formset, self.formset.empty_form,
            self.fieldsets, self.opts.prepopulated_fields, None,
            self.readonly_fields, model_admin=self.opts)


class InlineAdminForm(DjangoInlineAdminForm, AdminForm):
    """
    A wrapper around an inline form for use in the admin system.
    """
    def __init__(self, formset, form, fieldsets, prepopulated_fields, original,
      readonly_fields=None, model_admin=None):
        self.formset = formset
        self.model_admin = model_admin
        self.original = original
        self.show_url = original and hasattr(original, 'get_absolute_url')
        AdminForm.__init__(self, form, fieldsets, prepopulated_fields,
            readonly_fields, model_admin)

    def pk_field(self):
        # if there is no pk field then it's an embedded form so return none
        if hasattr(self.formset, "_pk_field"):
            return DjangoInlineAdminForm.pk_field(self)
        else:
            return None

    def __iter__(self):
        for name, options in self.fieldsets:
            yield InlineFieldset(self.formset, self.form, name,
                self.readonly_fields, model_admin=self.model_admin, **options)


class InlineFieldset(DjangoInlineFieldset):
    def __iter__(self):
        fk = getattr(self.formset, "fk", None)
        for field in self.fields:
            if fk and fk.name == field:
                continue
            yield Fieldline(self.form, field, self.readonly_fields,
                model_admin=self.model_admin)

########NEW FILE########
__FILENAME__ = createmongodbsuperuser
"""
Management utility to create superusers.
"""
import getpass
import re
import sys
from optparse import make_option

from django_mongoengine.auth.models import User
from django_mongoengine.connection import DEFAULT_CONNECTION_NAME
from django.core import exceptions
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext as _

get_default_username = lambda: "admin"

RE_VALID_USERNAME = re.compile('[\w.@+-]+$')

EMAIL_RE = re.compile(
    r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
    r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-\011\013\014\016-\177])*"' # quoted-string
    r')@(?:[A-Z0-9-]+\.)+[A-Z]{2,6}$', re.IGNORECASE)  # domain


def is_valid_email(value):
    if not EMAIL_RE.search(value):
        raise exceptions.ValidationError(_('Enter a valid e-mail address.'))


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--username', dest='username', default=None,
            help='Specifies the username for the superuser.'),
        make_option('--email', dest='email', default=None,
            help='Specifies the email address for the superuser.'),
        make_option('--noinput', action='store_false', dest='interactive', default=True,
            help=('Tells Django to NOT prompt the user for input of any kind. '
                  'You must use --username and --email with --noinput, and '
                  'superusers created with --noinput will not be able to log '
                  'in until they\'re given a valid password.')),
        make_option('--database', action='store', dest='database',
            default=DEFAULT_CONNECTION_NAME, help='Specifies the database to use. Default is "default".'),
    )
    help = 'Used to create a superuser.'

    def handle(self, *args, **options):
        username = options.get('username', None)
        email = options.get('email', None)
        interactive = options.get('interactive')
        verbosity = int(options.get('verbosity', 1))
        database = options.get('database')

        # Do quick and dirty validation if --noinput
        if not interactive:
            if not username or not email:
                raise CommandError("You must use --username and --email with --noinput.")
            if not RE_VALID_USERNAME.match(username):
                raise CommandError("Invalid username. Use only letters, digits, and underscores")
            try:
                is_valid_email(email)
            except exceptions.ValidationError:
                raise CommandError("Invalid email address.")

        # If not provided, create the user with an unusable password
        password = None

        # Prompt for username/email/password. Enclose this whole thing in a
        # try/except to trap for a keyboard interrupt and exit gracefully.
        if interactive:
            default_username = get_default_username()
            try:

                # Get a username
                while 1:
                    if not username:
                        input_msg = 'Username'
                        if default_username:
                            input_msg += ' (leave blank to use %r)' % default_username
                        username = raw_input(input_msg + ': ')
                    if default_username and username == '':
                        username = default_username
                    if not RE_VALID_USERNAME.match(username):
                        sys.stderr.write("Error: That username is invalid. Use only letters, digits and underscores.\n")
                        username = None
                        continue
                    try:
                        User.objects.get(username=username)
                    except User.DoesNotExist:
                        break
                    else:
                        sys.stderr.write("Error: That username is already taken.\n")
                        username = None

                # Get an email
                while 1:
                    if not email:
                        email = raw_input('E-mail address: ')
                    try:
                        is_valid_email(email)
                    except exceptions.ValidationError:
                        sys.stderr.write("Error: That e-mail address is invalid.\n")
                        email = None
                    else:
                        break

                # Get a password
                while 1:
                    if not password:
                        password = getpass.getpass()
                        password2 = getpass.getpass('Password (again): ')
                        if password != password2:
                            sys.stderr.write("Error: Your passwords didn't match.\n")
                            password = None
                            continue
                    if password.strip() == '':
                        sys.stderr.write("Error: Blank passwords aren't allowed.\n")
                        password = None
                        continue
                    break
            except KeyboardInterrupt:
                sys.stderr.write("\nOperation cancelled.\n")
                sys.exit(1)

        User.create_superuser(username, email, password)
        if verbosity >= 1:
          self.stdout.write("Superuser created successfully.\n")

########NEW FILE########
__FILENAME__ = options
from django import forms, template
from django.forms.formsets import all_valid
from django.forms.models import modelformset_factory
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin import widgets, helpers
from django.contrib.admin.util import unquote, flatten_fieldsets, model_format_dict
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import models, router
from django.db.models.related import RelatedObject
from django.db.models.fields import BLANK_CHOICE_DASH, FieldDoesNotExist
from django.db.models.sql.constants import QUERY_TERMS
from django.db.models.constants import LOOKUP_SEP
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.utils.decorators import method_decorator
from django.utils.datastructures import SortedDict
from django.utils.functional import update_wrapper
from django.utils.html import escape, escapejs
from django.utils.safestring import mark_safe
from django.utils.functional import curry
from django.utils.text import capfirst, get_text_list
from django.utils.translation import ugettext as _
from django.utils.translation import ungettext
from django.utils.encoding import force_unicode
from django.forms.forms import pretty_name

from django_mongoengine.fields import (DateTimeField, URLField, IntField,
                                       ListField, EmbeddedDocumentField,
                                       ReferenceField, StringField, FileField,
                                       ImageField)

from django_mongoengine.admin import helpers as mongodb_helpers
from django_mongoengine.admin.util import RelationWrapper
from django_mongoengine.admin.helpers import AdminForm

from django_mongoengine.forms.document_options import DocumentMetaWrapper
from django_mongoengine.forms.documents import (
    documentform_factory, DocumentForm,
    inlineformset_factory, BaseInlineDocumentFormSet)
from django_mongoengine.forms import (MongoDefaultFormFieldGenerator,
                                      save_instance)

HORIZONTAL, VERTICAL = 1, 2
# returns the <ul> class for a given radio_admin field
get_ul_class = lambda x: 'radiolist%s' % (
    (x == HORIZONTAL) and ' inline' or ''
)


class IncorrectLookupParameters(Exception):
    pass

# Defaults for formfield_overrides. ModelAdmin subclasses can change this
# by adding to ModelAdmin.formfield_overrides.
FORMFIELD_FOR_DBFIELD_DEFAULTS = {
    DateTimeField: {
        'form_class': forms.SplitDateTimeField,
        'widget': widgets.AdminSplitDateTime
    },
    #models.DateField:       {'widget': widgets.AdminDateWidget},
    #models.TimeField:       {'widget': widgets.AdminTimeWidget},
    URLField:       {'widget': widgets.AdminURLFieldWidget},
    IntField:       {'widget': widgets.AdminIntegerFieldWidget},
    ImageField:     {'widget': widgets.AdminFileWidget},
    FileField:      {'widget': widgets.AdminFileWidget},
}

csrf_protect_m = method_decorator(csrf_protect)


def formfield(field, form_class=None, **kwargs):
    """
    Returns a django.forms.Field instance for this database Field.
    """
    defaults = {'required': field.required, 'label': pretty_name(field.name)}
    if field.default is not None:
        if callable(field.default):
            defaults['initial'] = field.default()
            defaults['show_hidden_initial'] = True
        else:
            defaults['initial'] = field.default

    if hasattr(field, 'max_length') and field.choices is None:
        defaults['max_length'] = field.max_length

    if field.choices is not None:
        # Many of the subclass-specific formfield arguments (min_value,
        # max_value) don't apply for choice fields, so be sure to only pass
        # the values that TypedChoiceField will understand.
        for k in kwargs.keys():
            if k not in ('coerce', 'empty_value', 'choices', 'required',
                         'widget', 'label', 'initial', 'help_text',
                         'error_messages', 'show_hidden_initial'):
                del kwargs[k]

    defaults.update(kwargs)

    if form_class is not None:
        return form_class(**defaults)
    else:
        return MongoDefaultFormFieldGenerator().generate(field, **defaults)


class BaseDocumentAdmin(object):
    """Functionality common to both ModelAdmin and InlineAdmin."""
    __metaclass__ = forms.MediaDefiningClass

    raw_id_fields = ()
    fields = None
    exclude = None
    fieldsets = None
    form = DocumentForm
    filter_vertical = ()
    filter_horizontal = ()
    radio_fields = {}
    prepopulated_fields = {}
    formfield_overrides = {}
    readonly_fields = ()
    ordering = None

    def __init__(self):
        super(BaseDocumentAdmin, self).__init__()
        overrides = FORMFIELD_FOR_DBFIELD_DEFAULTS.copy()
        overrides.update(self.formfield_overrides)
        self.formfield_overrides = overrides

    def formfield_for_dbfield(self, db_field, **kwargs):
        """
        Hook for specifying the form Field instance for a given database Field
        instance.

        If kwargs are given, they're passed to the form Field's constructor.
        """
        request = kwargs.pop("request", None)

        # If the field specifies choices, we don't need to look for special
        # admin widgets - we just need to use a select widget of some kind.
        if db_field.choices is not None:
            return self.formfield_for_choice_field(db_field, request, **kwargs)

        if isinstance(db_field, ListField) and isinstance(db_field.field, ReferenceField):
            return self.formfield_for_manytomany(db_field, request, **kwargs)

        # handle RelatedFields
        if isinstance(db_field, ReferenceField):
            # For non-raw_id fields, wrap the widget with a wrapper that adds
            # extra HTML -- the "add other" interface -- to the end of the
            # rendered output. formfield can be None if it came from a
            # OneToOneField with parent_link=True or a M2M intermediary.
            form_field = formfield(db_field, **kwargs)
            if db_field.name not in self.raw_id_fields:
                related_modeladmin = self.admin_site._registry.get(db_field.document_type)
                can_add_related = bool(related_modeladmin and
                            related_modeladmin.has_add_permission(request))
                form_field.widget = widgets.RelatedFieldWidgetWrapper(
                            form_field.widget, RelationWrapper(db_field.document_type), self.admin_site,
                            can_add_related=can_add_related)
                return form_field

        if isinstance(db_field, StringField):
            if db_field.max_length is None:
                kwargs = dict({'widget': widgets.AdminTextareaWidget}, **kwargs)
            else:
                kwargs = dict({'widget': widgets.AdminTextInputWidget}, **kwargs)
            return formfield(db_field, **kwargs)

        # If we've got overrides for the formfield defined, use 'em. **kwargs
        # passed to formfield_for_dbfield override the defaults.
        for klass in db_field.__class__.mro():
            if klass in self.formfield_overrides:
                kwargs = dict(self.formfield_overrides[klass], **kwargs)
                return formfield(db_field, **kwargs)

        # For any other type of field, just call its formfield() method.
        return formfield(db_field, **kwargs)

    def formfield_for_choice_field(self, db_field, request=None, **kwargs):
        """
        Get a form Field for a database Field that has declared choices.
        """
        # If the field is named as a radio_field, use a RadioSelect
        if db_field.name in self.radio_fields:
            # Avoid stomping on custom widget/choices arguments.
            if 'widget' not in kwargs:
                kwargs['widget'] = widgets.AdminRadioSelect(attrs={
                    'class': get_ul_class(self.radio_fields[db_field.name]),
                })
            if 'choices' not in kwargs:
                kwargs['choices'] = db_field.get_choices(
                    include_blank = db_field.blank,
                    blank_choice=[('', _('None'))]
                )
        return formfield(db_field, **kwargs)


    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        """
        Get a form Field for a ManyToManyField.
        """
        db = kwargs.get('using')

        if db_field.name in self.raw_id_fields:
            kwargs['widget'] = widgets.ManyToManyRawIdWidget(db_field.rel, using=db)
            kwargs['help_text'] = ''
        elif db_field.name in (list(self.filter_vertical) + list(self.filter_horizontal)):
            kwargs['widget'] = widgets.FilteredSelectMultiple(pretty_name(db_field.name), (db_field.name in self.filter_vertical))

        return formfield(db_field, **kwargs)

    def _declared_fieldsets(self):
        if self.fieldsets:
            return self.fieldsets
        elif self.fields:
            return [(None, {'fields': self.fields})]
        return None
    declared_fieldsets = property(_declared_fieldsets)

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields

    def queryset(self, request):
        """
        Returns a QuerySet of all model instances that can be edited by the
        admin site. This is used by changelist_view.
        """
        # override documents object class to filter
        qs = self.document.objects()
        #qs = self.model._default_manager.get_query_set()
        # TODO: this should be handled by some parameter to the ChangeList.
        ordering = self.ordering or () # otherwise we might try to *None, which is bad ;)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs

    def lookup_allowed(self, lookup, value):
        model = self.model
        # Check FKey lookups that are allowed, so that popups produced by
        # ForeignKeyRawIdWidget, on the basis of ForeignKey.limit_choices_to,
        # are allowed to work.
        for l in model._meta.related_fkey_lookups:
            for k, v in widgets.url_params_from_lookup_dict(l).items():
                if k == lookup and v == value:
                    return True

        parts = lookup.split(LOOKUP_SEP)

        # Last term in lookup is a query term (__exact, __startswith etc)
        # This term can be ignored.
        if len(parts) > 1 and parts[-1] in QUERY_TERMS:
            parts.pop()

        # Special case -- foo__id__exact and foo__id queries are implied
        # if foo has been specificially included in the lookup list; so
        # drop __id if it is the last part. However, first we need to find
        # the pk attribute name.
        pk_attr_name = None
        for part in parts[:-1]:
            field, _, _, _ = model._meta.get_field_by_name(part)
            if hasattr(field, 'rel'):
                model = field.rel.to
                pk_attr_name = model._meta.pk.name
            elif isinstance(field, RelatedObject):
                model = field.model
                pk_attr_name = model._meta.pk.name
            else:
                pk_attr_name = None
        if pk_attr_name and len(parts) > 1 and parts[-1] == pk_attr_name:
            parts.pop()

        try:
            self.model._meta.get_field_by_name(parts[0])
        except FieldDoesNotExist:
            # Lookups on non-existants fields are ok, since they're ignored
            # later.
            return True
        else:
            if len(parts) == 1:
                return True
            clean_lookup = LOOKUP_SEP.join(parts)
            return clean_lookup in self.list_filter or clean_lookup == self.date_hierarchy


class DocumentAdmin(BaseDocumentAdmin):
    "Encapsulates all admin options and functionality for a given model."

    list_display = ('__str__',)
    list_display_links = ()
    list_filter = ()
    list_select_related = False
    # see __init__ for django < 1.4
    list_max_show_all = 200
    list_per_page = 100
    list_editable = ()
    search_fields = ()
    date_hierarchy = None
    save_as = False
    save_on_top = False
    paginator = Paginator
    inlines = []
    exclude = []

    # Custom templates (designed to be over-ridden in subclasses)
    add_form_template = None
    change_form_template = None
    change_list_template = None
    delete_confirmation_template = None
    delete_selected_confirmation_template = None
    object_history_template = None

    # Actions
    actions = []
    action_form = helpers.ActionForm
    actions_on_top = True
    actions_on_bottom = False
    actions_selection_counter = True

    def __init__(self, document, admin_site):
        super(DocumentAdmin, self).__init__()

        self.model = document
        self.document = self.model
        self.model._admin_opts = DocumentMetaWrapper(document)
        self.model._meta = self.model._admin_opts

        self.opts = self.model._admin_opts

        self.admin_site = admin_site
        self.inline_instances = []

        for inline_class in self.inlines:
            # all embedded admins are handled by self.get_inline_instances()
            if issubclass(inline_class, EmbeddedDocumentAdmin):
                continue
            inline_instance = inline_class(self.document, self.admin_site)
            self.inline_instances.append(inline_instance)

        # Without this exclude is weirdly shared between all
        # instances derived from DocumentAdmin.
        self.exclude = list(self.exclude)
        self.get_inline_instances()

        # If someone patched their MAX_SHOW_ALL_ALLOWED in django 1.3, we
        # get the value here and proceed as normal.
        try:
            from django.contrib.admin.views.main import MAX_SHOW_ALL_ALLOWED
            self.list_max_show_all = MAX_SHOW_ALL_ALLOWED
        except ImportError:
            pass

        from django.conf import settings
        self.log = not settings.DATABASES.get('default', {}).get(
            'ENGINE', 'django.db.backends.dummy').endswith('dummy')

    def get_inline_instances(self):
        for f in self.document._fields.itervalues():
            if not (isinstance(f, ListField) and isinstance(getattr(f, 'field', None), EmbeddedDocumentField)) and not isinstance(f, EmbeddedDocumentField):
                continue
            # Should only reach here if there is an embedded document...
            if f.name in self.exclude:
                continue
            document = self.document()
            if hasattr(f, 'field') and f.field is not None:
                embedded_document = f.field.document_type
            elif hasattr(f, 'document_type'):
                embedded_document = f.document_type
            else:
                # For some reason we found an embedded field were either
                # the field attribute or the field's document type is None.
                # This shouldn't happen, but apparently does happen:
                # https://github.com/jschrewe/django-mongoadmin/issues/4
                # The solution for now is to ignore that field entirely.
                continue
            inline_admin = EmbeddedStackedDocumentAdmin
            # check if there is an admin for the embedded document in
            # self.inlines. If there is, use this, else use default.
            for inline_class in self.inlines:
                if inline_class.document == embedded_document:
                    inline_admin = inline_class
            inline_instance = inline_admin(f, document, self.admin_site)
            # if f is an EmbeddedDocumentField set the maximum allowed form instances to one
            if isinstance(f, EmbeddedDocumentField):
                inline_instance.max_num = 1
                # exclude field from normal form
                if f.name not in self.exclude:
                    self.exclude.append(f.name)
            if f.name == 'created_at' and f.name not in self.exclude:
                self.exclude.append(f.name)
            self.inline_instances.append(inline_instance)

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        info = self.opts.app_label, self.opts.module_name

        urlpatterns = patterns('',
            url(r'^$',
                wrap(self.changelist_view),
                name='%s_%s_changelist' % info),
            url(r'^add/$',
                wrap(self.add_view),
                name='%s_%s_add' % info),
            url(r'^(.+)/history/$',
                wrap(self.history_view),
                name='%s_%s_history' % info),
            url(r'^(.+)/delete/$',
                wrap(self.delete_view),
                name='%s_%s_delete' % info),
            url(r'^(.+)/$',
                wrap(self.change_view),
                name='%s_%s_change' % info),
        )
        return urlpatterns

    def urls(self):
        return self.get_urls()
    urls = property(urls)

    def _media(self):
        from django.conf import settings

        js = ['js/core.js', 'js/admin/RelatedObjectLookups.js',
              'js/jquery.min.js', 'js/jquery.init.js']
        if self.actions is not None:
            js.extend(['js/actions.min.js'])
        if self.prepopulated_fields:
            js.append('js/urlify.js')
            js.append('js/prepopulate.min.js')
        if self.opts.get_ordered_objects():
            js.extend(['js/getElementsBySelector.js', 'js/dom-drag.js' , 'js/admin/ordering.js'])

        return forms.Media(js=['%s%s' % (settings.ADMIN_MEDIA_PREFIX, url) for url in js])
    media = property(_media)

    def has_add_permission(self, request):
        """
        Returns True if the given request has permission to add an object.
        Can be overriden by the user in subclasses.
        """
        opts = self.opts
        return request.user.has_perm(opts.app_label + '.' + opts.get_add_permission())

    def has_change_permission(self, request, obj=None):
        """
        Returns True if the given request has permission to change the given
        Django model instance, the default implementation doesn't examine the
        `obj` parameter.

        Can be overriden by the user in subclasses. In such case it should
        return True if the given request has permission to change the `obj`
        model instance. If `obj` is None, this should return True if the given
        request has permission to change *any* object of the given type.
        """
        opts = self.opts
        return request.user.has_perm(opts.app_label + '.' + opts.get_change_permission())

    def has_delete_permission(self, request, obj=None):
        """
        Returns True if the given request has permission to change the given
        Django model instance, the default implementation doesn't examine the
        `obj` parameter.

        Can be overriden by the user in subclasses. In such case it should
        return True if the given request has permission to delete the `obj`
        model instance. If `obj` is None, this should return True if the given
        request has permission to delete *any* object of the given type.
        """
        opts = self.opts
        return request.user.has_perm(opts.app_label + '.' + opts.get_delete_permission())

    def get_model_perms(self, request):
        """
        Returns a dict of all perms for this model. This dict has the keys
        ``add``, ``change``, and ``delete`` mapping to the True/False for each
        of those actions.
        """
        return {
            'add': self.has_add_permission(request),
            'change': self.has_change_permission(request),
            'delete': self.has_delete_permission(request),
        }

    def get_fieldsets(self, request, obj=None):
        "Hook for specifying fieldsets for the add form."
        if self.declared_fieldsets:
            return self.declared_fieldsets
        form = self.get_form(request, obj)
        fields = form.base_fields.keys() + list(self.get_readonly_fields(request, obj))
        return [(None, {'fields': fields})]

    def get_form(self, request, obj=None, **kwargs):
        """
        Returns a Form class for use in the admin add view. This is used by
        add_view and change_view.
        """
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
        # if exclude is an empty list we pass None to be consistant with the
        # default on modelform_factory
        exclude = exclude or None
        defaults = {
            "form": self.form,
            "fields": fields,
            "exclude": exclude,
            "formfield_callback": curry(self.formfield_for_dbfield, request=request),
        }
        defaults.update(kwargs)
        document = self.document()
        return documentform_factory(document, **defaults)

    def get_changelist(self, request, **kwargs):
        """
        Returns the ChangeList class for use on the changelist page.
        """
        from views import DocumentChangeList
        return DocumentChangeList

    def get_object(self, request, object_id):
        """
        Returns an instance matching the primary key provided. ``None``  is
        returned if no match is found (or the object_id failed validation
        against the primary key field).
        """
        queryset = self.queryset(request)
        model = queryset._document
        model._admin_opts = DocumentMetaWrapper(model)
        try:
            object_id = model._admin_opts.pk.to_python(object_id)
            return queryset.get(pk=object_id)
        except (model.DoesNotExist, ValidationError):
            return None

    def get_changelist_form(self, request, **kwargs):
        """
        Returns a Form class for use in the Formset on the changelist page.
        """
        defaults = {
            "formfield_callback": curry(self.formfield_for_dbfield, request=request),
        }
        defaults.update(kwargs)
        return documentform_factory(self.model, **defaults)

    def get_changelist_formset(self, request, **kwargs):
        """
        Returns a FormSet class for use on the changelist page if list_editable
        is used.
        """
        defaults = {
            "formfield_callback": curry(self.formfield_for_dbfield, request=request),
        }
        defaults.update(kwargs)
        return modelformset_factory(self.model,
            self.get_changelist_form(request), extra=0,
            fields=self.list_editable, **defaults)

    def get_formsets(self, request, obj=None):
        for inline in self.inline_instances:
            yield inline.get_formset(request, obj)

    def get_paginator(self, request, queryset, per_page, orphans=0, allow_empty_first_page=True):
        return self.paginator(queryset, per_page, orphans, allow_empty_first_page)

    def log_addition(self, request, object):
        """
        Log that an object has been successfully added.

        The default implementation creates an admin LogEntry object.
        """
        if not self.log:
            return
        from django.contrib.admin.models import LogEntry, ADDITION
        LogEntry.objects.log_action(
            user_id         = request.user.pk,
            content_type_id = None,
            object_id       = object.pk,
            object_repr     = force_unicode(object),
            action_flag     = ADDITION
        )

    def log_change(self, request, object, message):
        """
        Log that an object has been successfully changed.

        The default implementation creates an admin LogEntry object.
        """
        if not self.log:
            return
        from django.contrib.admin.models import LogEntry, CHANGE
        LogEntry.objects.log_action(
            user_id         = request.user.pk,
            content_type_id = None,
            object_id       = object.pk,
            object_repr     = force_unicode(object),
            action_flag     = CHANGE,
            change_message  = message
        )

    def log_deletion(self, request, object, object_repr):
        """
        Log that an object will be deleted. Note that this method is called
        before the deletion.

        The default implementation creates an admin LogEntry object.
        """
        if not self.log:
            return
        from django.contrib.admin.models import LogEntry, DELETION
        LogEntry.objects.log_action(
            user_id         = request.user.id,
            content_type_id = None,
            object_id       = object.pk,
            object_repr     = object_repr,
            action_flag     = DELETION
        )

    def action_checkbox(self, obj):
        """
        A list_display column containing a checkbox widget.
        """
        return helpers.checkbox.render(helpers.ACTION_CHECKBOX_NAME, force_unicode(obj.pk))
    action_checkbox.short_description = mark_safe('<input type="checkbox" id="action-toggle" />')
    action_checkbox.allow_tags = True

    def get_actions(self, request):
        """
        Return a dictionary mapping the names of all actions for this
        ModelAdmin to a tuple of (callable, name, description) for each action.
        """
        # If self.actions is explicitally set to None that means that we don't
        # want *any* actions enabled on this page.
        from django.contrib.admin.views.main import IS_POPUP_VAR
        if self.actions is None or IS_POPUP_VAR in request.GET:
            return SortedDict()

        actions = []

        # Gather actions from the admin site first
        for (name, func) in self.admin_site.actions:
            description = getattr(func, 'short_description', name.replace('_', ' '))
            actions.append((func, name, description))

        # Then gather them from the model admin and all parent classes,
        # starting with self and working back up.
        for klass in self.__class__.mro()[::-1]:
            class_actions = getattr(klass, 'actions', [])
            # Avoid trying to iterate over None
            if not class_actions:
                continue
            actions.extend([self.get_action(action) for action in class_actions])

        # get_action might have returned None, so filter any of those out.
        actions = filter(None, actions)

        # Convert the actions into a SortedDict keyed by name
        # and sorted by description.
        actions = SortedDict([
            (name, (func, name, desc))
            for func, name, desc in actions
        ])

        return actions

    def get_action_choices(self, request, default_choices=BLANK_CHOICE_DASH):
        """
        Return a list of choices for use in a form object.  Each choice is a
        tuple (name, description).
        """
        choices = [] + default_choices
        for func, name, description in self.get_actions(request).itervalues():
            choice = (name, description % model_format_dict(self.opts))
            choices.append(choice)
        return choices

    def get_action(self, action):
        """
        Return a given action from a parameter, which can either be a callable,
        or the name of a method on the ModelAdmin.  Return is a tuple of
        (callable, name, description).
        """
        # If the action is a callable, just use it.
        if callable(action):
            func = action
            action = action.__name__

        # Next, look for a method. Grab it off self.__class__ to get an unbound
        # method instead of a bound one; this ensures that the calling
        # conventions are the same for functions and methods.
        elif hasattr(self.__class__, action):
            func = getattr(self.__class__, action)

        # Finally, look for a named method on the admin site
        else:
            try:
                func = self.admin_site.get_action(action)
            except KeyError:
                return None

        if hasattr(func, 'short_description'):
            description = func.short_description
        else:
            description = capfirst(action.replace('_', ' '))
        return func, action, description

    def get_list_display(self, request):
        """
        Return a sequence containing the fields to be displayed on the
        changelist.
        """
        return self.list_display

    def get_list_display_links(self, request, list_display):
        """
        Return a sequence containing the fields to be displayed as links
        on the changelist. The list_display parameter is the list of fields
        returned by get_list_display().
        """
        if self.list_display_links or not list_display:
            return self.list_display_links
        else:
            # Use only the first item in list_display as link
            return list(list_display)[:1]

    def get_ordering(self, request):
        """
        Hook for specifying field ordering.
        """
        return self.ordering or ()  # otherwise we might try to *None, which is bad ;)

    def construct_change_message(self, request, form, formsets):
        """
        Construct a change message from a changed object.
        """
        change_message = []
        if form.changed_data:
            change_message.append(_('Changed %s.') % get_text_list(form.changed_data, _('and')))

        if formsets:
            for formset in formsets:
                for added_object in formset.new_objects:
                    change_message.append(_('Added %(name)s "%(object)s".')
                                          % {'name': force_unicode(added_object._meta.verbose_name),
                                             'object': force_unicode(added_object)})
                for changed_object, changed_fields in formset.changed_objects:
                    change_message.append(_('Changed %(list)s for %(name)s "%(object)s".')
                                          % {'list': get_text_list(changed_fields, _('and')),
                                             'name': force_unicode(changed_object._meta.verbose_name),
                                             'object': force_unicode(changed_object)})
                for deleted_object in formset.deleted_objects:
                    change_message.append(_('Deleted %(name)s "%(object)s".')
                                          % {'name': force_unicode(deleted_object._meta.verbose_name),
                                             'object': force_unicode(deleted_object)})
        change_message = ' '.join(change_message)
        return change_message or _('No fields changed.')

    def message_user(self, request, message):
        """
        Send a message to the user. The default implementation
        posts a message using the django.contrib.messages backend.
        """
        messages.info(request, message)

    def save_form(self, request, form, change):
        """
        Given a ModelForm return an unsaved instance. ``change`` is True if
        the object is being changed, and False if it's being added.
        """
        return form.save(commit=False)

    def save_model(self, request, obj, form, change):
        """
        Given a model instance save it to the database.
        """
        save_instance(form, obj)

    def delete_model(self, request, obj):
        """
        Given a model instance delete it from the database.
        """
        obj.delete()

    def save_formset(self, request, form, formset, change):
        """
        Given an inline formset save it to the database.
        """
        return formset.save()

    def render_change_form(self, request, context, add=False, change=False,
                           form_url='', obj=None):
        opts = self.model._admin_opts
        app_label = opts.app_label
        ordered_objects = opts.get_ordered_objects()
        context.update({
            'add': add,
            'change': change,
            'has_add_permission': self.has_add_permission(request),
            'has_change_permission': self.has_change_permission(request, obj),
            'has_delete_permission': self.has_delete_permission(request, obj),
            'has_file_field': True, # FIXME - this should check if form or formsets have a FileField,
            #'has_absolute_url': hasattr(self.model, 'get_absolute_url'),
            'ordered_objects': ordered_objects,
            'form_url': mark_safe(form_url),
            'opts': opts,
            #'content_type_id': ContentType.objects.get_for_model(self.model).id,
            'save_as': self.save_as,
            'save_on_top': self.save_on_top,
            'root_path': self.admin_site.root_path,
        })

        form_template = self.change_form_template
        if add and self.add_form_template is not None:
            form_template = self.add_form_template

        context_instance = template.RequestContext(request, current_app=self.admin_site.name)
        return render_to_response(form_template or [
            "admin/%s/%s/change_form.html" % (app_label, opts.object_name.lower()),
            "admin/%s/change_form.html" % app_label,
            "admin/change_form.html"
        ], context, context_instance=context_instance)

    def response_add(self, request, obj, post_url_continue='../%s/'):
        """
        Determines the HttpResponse for the add_view stage.
        """
        opts = obj._admin_opts
        pk_value = obj.pk.__str__()

        msg = _('The %(name)s "%(obj)s" was added successfully.') % {'name': force_unicode(opts.verbose_name), 'obj': force_unicode(obj)}
        # Here, we distinguish between different save types by checking for
        # the presence of keys in request.POST.
        if "_continue" in request.POST:
            self.message_user(request, msg + ' ' + _("You may edit it again below."))
            if "_popup" in request.POST:
                post_url_continue += "?_popup=1"
            return HttpResponseRedirect(post_url_continue % pk_value)

        if "_popup" in request.POST:
            return HttpResponse('<script type="text/javascript">opener.dismissAddAnotherPopup(window, "%s", "%s");</script>' % \
                # escape() calls force_unicode.
                (escape(pk_value), escapejs(obj)))
        elif "_addanother" in request.POST:
            self.message_user(request, msg + ' ' + (_("You may add another %s below.") % force_unicode(opts.verbose_name)))
            return HttpResponseRedirect(request.path)
        else:
            self.message_user(request, msg)

            # Figure out where to redirect. If the user has change permission,
            # redirect to the change-list page for this object. Otherwise,
            # redirect to the admin index.
            if self.has_change_permission(request, None):
                post_url = '../'
            else:
                post_url = '../../../'
            return HttpResponseRedirect(post_url)

    def response_change(self, request, obj):
        """
        Determines the HttpResponse for the change_view stage.
        """
        opts = obj._admin_opts

        verbose_name = opts.verbose_name
        # Handle proxy models automatically created by .only() or .defer()
        #if obj._deferred:
        #    opts_ = opts.proxy_for_model._meta
        #    verbose_name = opts_.verbose_name

        pk_value = obj.pk.__str__()

        msg = _('The %(name)s "%(obj)s" was changed successfully.') % {'name': force_unicode(verbose_name), 'obj': force_unicode(obj)}
        if "_continue" in request.POST:
            self.message_user(request, msg + ' ' + _("You may edit it again below."))
            if "_popup" in request.REQUEST:
                return HttpResponseRedirect(request.path + "?_popup=1")
            else:
                return HttpResponseRedirect(request.path)
        elif "_saveasnew" in request.POST:
            msg = _('The %(name)s "%(obj)s" was added successfully. You may edit it again below.') % {'name': force_unicode(verbose_name), 'obj': obj}
            self.message_user(request, msg)
            return HttpResponseRedirect("../%s/" % pk_value)
        elif "_addanother" in request.POST:
            self.message_user(request, msg + ' ' + (_("You may add another %s below.") % force_unicode(verbose_name)))
            return HttpResponseRedirect("../add/")
        else:
            self.message_user(request, msg)
            # Figure out where to redirect. If the user has change permission,
            # redirect to the change-list page for this object. Otherwise,
            # redirect to the admin index.
            if self.has_change_permission(request, None):
                return HttpResponseRedirect('../')
            else:
                return HttpResponseRedirect('../../../')

    def response_action(self, request, queryset):
        """
        Handle an admin action. This is called if a request is POSTed to the
        changelist; it returns an HttpResponse if the action was handled, and
        None otherwise.
        """

        # There can be multiple action forms on the page (at the top
        # and bottom of the change list, for example). Get the action
        # whose button was pushed.
        try:
            action_index = int(request.POST.get('index', 0))
        except ValueError:
            action_index = 0

        # Construct the action form.
        data = request.POST.copy()
        data.pop(helpers.ACTION_CHECKBOX_NAME, None)
        data.pop("index", None)

        # Use the action whose button was pushed
        try:
            data.update({'action': data.getlist('action')[action_index]})
        except IndexError:
            # If we didn't get an action from the chosen form that's invalid
            # POST data, so by deleting action it'll fail the validation check
            # below. So no need to do anything here
            pass

        action_form = self.action_form(data, auto_id=None)
        action_form.fields['action'].choices = self.get_action_choices(request)

        # If the form's valid we can handle the action.
        if action_form.is_valid():
            action = action_form.cleaned_data['action']
            select_across = action_form.cleaned_data['select_across']
            func, name, description = self.get_actions(request)[action]

            # Get the list of selected PKs. If nothing's selected, we can't
            # perform an action on it, so bail. Except we want to perform
            # the action explicitly on all objects.
            selected = request.POST.getlist(helpers.ACTION_CHECKBOX_NAME)
            if not selected and not select_across:
                # Reminder that something needs to be selected or nothing will happen
                msg = _("Items must be selected in order to perform "
                        "actions on them. No items have been changed.")
                self.message_user(request, msg)
                return None

            if not select_across:
                # Perform the action only on the selected objects
                queryset = queryset.filter(pk__in=selected)

            response = func(self, request, queryset)

            # Actions may return an HttpResponse, which will be used as the
            # response from the POST. If not, we'll be a good little HTTP
            # citizen and redirect back to the changelist page.
            if isinstance(response, HttpResponse):
                return response
            else:
                return HttpResponseRedirect(request.get_full_path())
        else:
            msg = _("No action selected.")
            self.message_user(request, msg)
            return None


    @csrf_protect_m
    def add_view(self, request, form_url='', extra_context=None):
        "The 'add' admin view for this model."
        model = self.model
        opts = model._admin_opts

        if not self.has_add_permission(request):
            raise PermissionDenied

        DocumentForm = self.get_form(request)
        formsets = []
        if request.method == 'POST':
            form = DocumentForm(request.POST, request.FILES)
            if form.is_valid():
                new_object = self.save_form(request, form, change=False)
                form_validated = True
            else:
                form_validated = False
                new_object = self.model()
            prefixes = {}
            for FormSet, inline in zip(self.get_formsets(request), self.inline_instances):
                prefix = FormSet.get_default_prefix()
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
                if prefixes[prefix] != 1:
                    prefix = "%s-%s" % (prefix, prefixes[prefix])
                formset = FormSet(data=request.POST, files=request.FILES,
                                  instance=new_object,
                                  save_as_new="_saveasnew" in request.POST,
                                  prefix=prefix, queryset=inline.queryset(request))
                formsets.append(formset)

                if formset.is_valid() and form_validated:
                    if isinstance(inline, EmbeddedDocumentAdmin):
                        embedded_object_list = formset.save()
                        if isinstance(inline.field, ListField):
                            setattr(new_object, inline.rel_name, embedded_object_list)
                        elif len(embedded_object_list) > 0:
                            setattr(new_object, inline.rel_name, embedded_object_list[0])
                        else:
                            setattr(new_object, inline.rel_name, None)
                    else:
                        formset.save()

            if all_valid(formsets) and form_validated:
                self.save_model(request, new_object, form, change=False)
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
            form = DocumentForm(initial=initial)
            prefixes = {}
            for FormSet, inline in zip(self.get_formsets(request),
                                       self.inline_instances):
                inline.parent_document = self.document()
                prefix = FormSet.get_default_prefix()
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
                if prefixes[prefix] != 1:
                    prefix = "%s-%s" % (prefix, prefixes[prefix])
                formset = FormSet(instance=self.model(), prefix=prefix,
                                  queryset=inline.queryset(request))
                formsets.append(formset)

        adminForm = AdminForm(form, list(self.get_fieldsets(request)),
            self.prepopulated_fields, self.get_readonly_fields(request),
            model_admin=self)
        media = self.media + adminForm.media

        inline_admin_formsets = []
        for inline, formset in zip(self.inline_instances, formsets):
            fieldsets = list(inline.get_fieldsets(request))
            readonly = list(inline.get_readonly_fields(request))
            inline_admin_formset = mongodb_helpers.InlineAdminFormSet(inline,
                formset, fieldsets, readonly, model_admin=self)
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
            'root_path': self.admin_site.root_path,
            'app_label': opts.app_label,
        }
        context.update(extra_context or {})
        return self.render_change_form(request, context, form_url=form_url, add=True)

    @csrf_protect_m
    def change_view(self, request, object_id, extra_context=None):
        "The 'change' admin view for this model."
        model = self.model
        opts = model._admin_opts

        obj = self.get_object(request, unquote(object_id))

        if not self.has_change_permission(request, obj):
            raise PermissionDenied

        if obj is None:
            raise Http404(_('%(name)s object with primary key %(key)r does not exist.') % {'name': force_unicode(opts.verbose_name), 'key': escape(object_id)})

        if request.method == 'POST' and "_saveasnew" in request.POST:
            return self.add_view(request, form_url='../add/')

        DocumentForm = self.get_form(request, obj)
        formsets = []
        # TODO: Something is wrong if formsets are invalid
        if request.method == 'POST':
            form = DocumentForm(request.POST, request.FILES, instance=obj)
            if form.is_valid():
                form_validated = True
                new_object = self.save_form(request, form, change=True)
            else:
                form_validated = False
                new_object = obj
            prefixes = {}
            for FormSet, inline in zip(self.get_formsets(request, new_object),
                                       self.inline_instances):
                prefix = FormSet.get_default_prefix()
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
                if prefixes[prefix] != 1:
                    prefix = "%s-%s" % (prefix, prefixes[prefix])
                formset = FormSet(request.POST, request.FILES,
                                  instance=new_object, prefix=prefix,
                                  queryset=inline.queryset(request))

                if formset.is_valid() and form_validated:
                    if isinstance(inline, EmbeddedDocumentAdmin):
                        embedded_object_list = formset.save()
                        if isinstance(inline.field, ListField):
                            setattr(new_object, inline.rel_name, embedded_object_list)
                        elif len(embedded_object_list) > 0:
                            setattr(new_object, inline.rel_name, embedded_object_list[0])
                        else:
                            setattr(new_object, inline.rel_name, None)
                    else:
                        formset.save()

            if all_valid(formsets) and form_validated:
                self.save_model(request, new_object, form, change=True)
                for formset in formsets:
                    self.save_formset(request, form, formset, change=True)

                change_message = self.construct_change_message(request, form, formsets)
                self.log_change(request, new_object, change_message)
                return self.response_change(request, new_object)

        else:
            form = DocumentForm(instance=obj)
            prefixes = {}
            # set the actual parent document on the inline admins
            for FormSet, inline in zip(self.get_formsets(request, obj), self.inline_instances):
                inline.parent_document = obj
                prefix = FormSet.get_default_prefix()
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
                if prefixes[prefix] != 1:
                    prefix = "%s-%s" % (prefix, prefixes[prefix])
                formset = FormSet(instance=obj, prefix=prefix,
                                  queryset=inline.queryset(request))
                formsets.append(formset)

        adminForm = AdminForm(form, self.get_fieldsets(request, obj),
            self.prepopulated_fields, self.get_readonly_fields(request, obj),
            model_admin=self)
        media = self.media + adminForm.media

        inline_admin_formsets = []
        for inline, formset in zip(self.inline_instances, formsets):
            fieldsets = list(inline.get_fieldsets(request, obj))
            readonly = list(inline.get_readonly_fields(request, obj))

            inline_admin_formset = mongodb_helpers.InlineAdminFormSet(inline, formset,
                fieldsets, readonly, model_admin=self)

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
            'root_path': self.admin_site.root_path,
            'app_label': opts.app_label,
        }
        context.update(extra_context or {})
        return self.render_change_form(request, context, change=True, obj=obj)

    @csrf_protect_m
    def changelist_view(self, request, extra_context=None):
        "The 'change list' admin view for this model."
        from django.contrib.admin.views.main import ERROR_FLAG
        app_label = self.opts.app_label
        opts = self.opts
        if not self.has_change_permission(request, None):
            raise PermissionDenied

        list_display = self.get_list_display(request)
        list_display_links = self.get_list_display_links(request, list_display)

        # Check actions to see if any are available on this changelist
        actions = self.get_actions(request)
        if actions:
            # Add the action checkboxes if there are any actions available.
            list_display = ['action_checkbox'] +  list(list_display)

        ChangeList = self.get_changelist(request)
        try:
            cl = ChangeList(request, self.model, list_display,
                list_display_links, self.list_filter, self.date_hierarchy,
                self.search_fields, self.list_select_related,
                self.list_per_page, self.list_max_show_all, self.list_editable,
                self)
        except IncorrectLookupParameters:
            # Wacky lookup parameters were given, so redirect to the main
            # changelist page, without parameters, and pass an 'invalid=1'
            # parameter via the query string. If wacky parameters were given
            # and the 'invalid=1' parameter was already in the query string,
            # something is screwed up with the database, so display an error
            # page.
            if ERROR_FLAG in request.GET.keys():
                return render_to_response('admin/invalid_setup.html', {'title': _('Database error')})
            return HttpResponseRedirect(request.path + '?' + ERROR_FLAG + '=1')

        # If the request was POSTed, this might be a bulk action or a bulk
        # edit. Try to look up an action or confirmation first, but if this
        # isn't an action the POST will fall through to the bulk edit check,
        # below.
        action_failed = False
        selected = request.POST.getlist(helpers.ACTION_CHECKBOX_NAME)

        # Actions with no confirmation
        if (actions and request.method == 'POST' and
                'index' in request.POST and '_save' not in request.POST):
            if selected:
                response = self.response_action(request, queryset=cl.get_query_set())
                if response:
                    return response
                else:
                    action_failed = True
            else:
                msg = _("Items must be selected in order to perform "
                        "actions on them. No items have been changed.")
                self.message_user(request, msg)
                action_failed = True

        # Actions with confirmation
        if (actions and request.method == 'POST' and
                helpers.ACTION_CHECKBOX_NAME in request.POST and
                'index' not in request.POST and '_save' not in request.POST):
            if selected:
                response = self.response_action(request, queryset=cl.get_query_set())
                if response:
                    return response
                else:
                    action_failed = True

        # If we're allowing changelist editing, we need to construct a formset
        # for the changelist given all the fields to be edited. Then we'll
        # use the formset to validate/process POSTed data.
        formset = cl.formset = None

        # Handle POSTed bulk-edit data.
        if (request.method == "POST" and cl.list_editable and
                '_save' in request.POST and not action_failed):
            FormSet = self.get_changelist_formset(request)
            formset = cl.formset = FormSet(request.POST, request.FILES, queryset=cl.result_list)
            if formset.is_valid():
                changecount = 0
                for form in formset.forms:
                    if form.has_changed():
                        obj = self.save_form(request, form, change=True)
                        self.save_model(request, obj, form, change=True)
                        form.save_m2m()
                        change_msg = self.construct_change_message(request, form, None)
                        self.log_change(request, obj, change_msg)
                        changecount += 1

                if changecount:
                    if changecount == 1:
                        name = force_unicode(opts.verbose_name)
                    else:
                        name = force_unicode(opts.verbose_name_plural)
                    msg = ungettext("%(count)s %(name)s was changed successfully.",
                                    "%(count)s %(name)s were changed successfully.",
                                    changecount) % {'count': changecount,
                                                    'name': name,
                                                    'obj': force_unicode(obj)}
                    self.message_user(request, msg)

                return HttpResponseRedirect(request.get_full_path())

        # Handle GET -- construct a formset for display.
        elif cl.list_editable:
            FormSet = self.get_changelist_formset(request)
            formset = cl.formset = FormSet(queryset=cl.result_list)

        # Build the list of media to be used by the formset.
        if formset:
            media = self.media + formset.media
        else:
            media = self.media

        # Build the action form and populate it with available actions.
        if actions:
            action_form = self.action_form(auto_id=None)
            action_form.fields['action'].choices = self.get_action_choices(request)
        else:
            action_form = None

        selection_note_all = ungettext('%(total_count)s selected',
            'All %(total_count)s selected', cl.result_count)

        context = {
            'module_name': force_unicode(opts.verbose_name_plural),
            'selection_note': _('0 of %(cnt)s selected') % {'cnt': len(cl.result_list)},
            'selection_note_all': selection_note_all % {'total_count': cl.result_count},
            'title': cl.title,
            'is_popup': cl.is_popup,
            'cl': cl,
            'media': media,
            'has_add_permission': self.has_add_permission(request),
            'root_path': self.admin_site.root_path,
            'app_label': app_label,
            'action_form': action_form,
            'actions_on_top': self.actions_on_top,
            'actions_on_bottom': self.actions_on_bottom,
            'actions_selection_counter': self.actions_selection_counter,
        }
        context.update(extra_context or {})
        context_instance = template.RequestContext(request, current_app=self.admin_site.name)
        return render_to_response(self.change_list_template or [
            'admin/%s/%s/change_document_list.html' % (app_label, opts.object_name.lower()),
            'admin/%s/change_document_list.html' % app_label,
            'admin/change_document_list.html'
        ], context, context_instance=context_instance)

    @csrf_protect_m
    def delete_view(self, request, object_id, extra_context=None):
        "The 'delete' admin view for this model."
        opts = self.model._admin_opts
        app_label = opts.app_label

        obj = self.get_object(request, unquote(object_id))

        if not self.has_delete_permission(request, obj):
            raise PermissionDenied

        if obj is None:
            raise Http404(_('%(name)s object with primary key %(key)r does not exist.') % {'name': force_unicode(opts.verbose_name), 'key': escape(object_id)})

        using = router.db_for_write(self.model)

        # Populate deleted_objects, a data structure of all related objects that
        # will also be deleted.
        print "FIXME: Need to delete nested objects."
        #(deleted_objects, perms_needed, protected) = get_deleted_objects(
        #    [obj], opts, request.user, self.admin_site, using)

        if request.POST: # The user has already confirmed the deletion.
            #if perms_needed:
            #    raise PermissionDenied
            obj_display = force_unicode(obj)
            self.log_deletion(request, obj, obj_display)
            self.delete_model(request, obj)

            self.message_user(request, _('The %(name)s "%(obj)s" was deleted successfully.') % {'name': force_unicode(opts.verbose_name), 'obj': force_unicode(obj_display)})

            if not self.has_change_permission(request, None):
                return HttpResponseRedirect("../../../../")
            return HttpResponseRedirect("../../")

        object_name = force_unicode(opts.verbose_name)

        #if perms_needed or protected:
        #    title = _("Cannot delete %(name)s") % {"name": object_name}
        #else:
        title = _("Are you sure?")

        context = {
            "title": title,
            "object_name": object_name,
            "object": obj,
            #"deleted_objects": deleted_objects,
            #"perms_lacking": perms_needed,
            #"protected": protected,
            "opts": opts,
            "root_path": self.admin_site.root_path,
            "app_label": app_label,
        }
        context.update(extra_context or {})
        context_instance = template.RequestContext(request, current_app=self.admin_site.name)
        return render_to_response(self.delete_confirmation_template or [
            "admin/%s/%s/delete_confirmation.html" % (app_label, opts.object_name.lower()),
            "admin/%s/delete_confirmation.html" % app_label,
            "admin/delete_confirmation.html"
        ], context, context_instance=context_instance)

    def history_view(self, request, object_id, extra_context=None):
        "The 'history' admin view for this model."
        from django.contrib.admin.models import LogEntry
        model = self.model
        opts = model._meta
        app_label = opts.app_label
        action_list = LogEntry.objects.filter(
            object_id = object_id,
            content_type__id__exact = ContentType.objects.get_for_model(model).id
        ).select_related().order_by('action_time')
        # If no history was found, see whether this object even exists.
        obj = get_object_or_404(model, pk=unquote(object_id))
        context = {
            'title': _('Change history: %s') % force_unicode(obj),
            'action_list': action_list,
            'module_name': capfirst(force_unicode(opts.verbose_name_plural)),
            'object': obj,
            'root_path': self.admin_site.root_path,
            'app_label': app_label,
        }
        context.update(extra_context or {})
        context_instance = template.RequestContext(request, current_app=self.admin_site.name)
        return render_to_response(self.object_history_template or [
            "admin/%s/%s/object_history.html" % (app_label, opts.object_name.lower()),
            "admin/%s/object_history.html" % app_label,
            "admin/object_history.html"
        ], context, context_instance=context_instance)


class InlineDocumentAdmin(BaseDocumentAdmin):
    """
    Options for inline editing of ``model`` instances.

    Provide ``name`` to specify the attribute name of the ``ForeignKey`` from
    ``model`` to its parent. This is required if ``model`` has more than one
    ``ForeignKey`` to its parent.
    """
    document = None
    fk_name = None
    formset = BaseInlineDocumentFormSet
    extra = 1
    max_num = None
    template = None
    verbose_name = None
    verbose_name_plural = None
    can_delete = True

    def __init__(self, parent_document, admin_site):
        self.admin_site = admin_site
        self.parent_document = parent_document
        if not hasattr(self.document, '_admin_opts'):
            self.document._admin_opts = DocumentMetaWrapper(self.document)
        self.opts = self.document._admin_opts

        super(InlineDocumentAdmin, self).__init__()

        if self.verbose_name is None:
            self.verbose_name = self.document._admin_opts.verbose_name

        if self.verbose_name_plural is None:
            self.verbose_name_plural = self.document._admin_opts.verbose_name_plural

    def _media(self):
        from django.conf import settings
        js = ['js/jquery.min.js', 'js/jquery.init.js', 'js/inlines.min.js']
        if self.prepopulated_fields:
            js.append('js/urlify.js')
            js.append('js/prepopulate.min.js')
        if self.filter_vertical or self.filter_horizontal:
            js.extend(['js/SelectBox.js' , 'js/SelectFilter2.js'])
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
            "fields": fields,
            "exclude": exclude,
            "formfield_callback": curry(self.formfield_for_dbfield, request=request),
            "extra": self.extra,
            "max_num": self.max_num,
            "can_delete": self.can_delete,
        }
        defaults.update(kwargs)
        return inlineformset_factory(self.document, **defaults)

    def get_fieldsets(self, request, obj=None):
        if self.declared_fieldsets:
            return self.declared_fieldsets
        form = self.get_formset(request).form
        fields = form.base_fields.keys() + list(self.get_readonly_fields(request, obj))
        return [(None, {'fields': fields})]

class EmbeddedDocumentAdmin(InlineDocumentAdmin):
    def __init__(self, field, parent_document, admin_site):
        if hasattr(field, 'field'):
            self.document = field.field.document_type
        else:
            self.document = field.document_type
        self.doc_list = getattr(parent_document, field.name)
        self.field = field
        if not isinstance(self.doc_list, list):
            self.doc_list = []
        self.rel_name = field.name

        self.document._admin_opts = DocumentMetaWrapper(self.document)
        if self.verbose_name is None:
            self.verbose_name = "Field: %s (Document: %s)" % (capfirst(field.name), self.document._admin_opts.verbose_name)

        if self.verbose_name_plural is None:
            self.verbose_name_plural = "Field: %s (Document:  %s)" % (capfirst(field.name), self.document._admin_opts.verbose_name_plural)

        super(EmbeddedDocumentAdmin, self).__init__(parent_document, admin_site)

    def queryset(self, request):
        if isinstance(self.field, ListField): # list field
            self.doc_list = getattr(self.parent_document, self.rel_name)
        else: # embedded field
            emb_doc = getattr(self.parent_document, self.rel_name)
            if emb_doc is None:
                self.doc_list = []
            else:
                self.doc_list = [emb_doc]
        return self.doc_list

class StackedDocumentInline(InlineDocumentAdmin):
    template = 'admin/edit_inline/stacked.html'

class EmbeddedStackedDocumentAdmin(EmbeddedDocumentAdmin):
    template = 'admin/edit_inline/stacked.html'

class TabularDocumentInline(InlineDocumentAdmin):
    template = 'admin/edit_inline/tabular.html'

########NEW FILE########
__FILENAME__ = sites
from django import http, template
from django.contrib.admin import ModelAdmin
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.contenttypes import views as contenttype_views
from django.views.decorators.csrf import csrf_protect
from django.db.models.base import ModelBase
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.utils.functional import update_wrapper
from django.utils.safestring import mark_safe
from django.utils.text import capfirst
from django.utils.translation import ugettext as _
from django.views.decorators.cache import never_cache
from django.conf import settings
from django.contrib.admin.sites import NotRegistered, AlreadyRegistered

from mongoengine.base import TopLevelDocumentMetaclass

from django_mongoengine.admin import actions, DocumentAdmin

LOGIN_FORM_KEY = 'this_is_the_login_form'


class AdminSite(object):
    """
    An AdminSite object encapsulates an instance of the Django admin application, ready
    to be hooked in to your URLconf. Models are registered with the AdminSite using the
    register() method, and the get_urls() method can then be used to access Django view
    functions that present a full admin interface for the collection of registered
    models.
    """
    login_form = None
    index_template = None
    app_index_template = None
    login_template = None
    logout_template = None
    password_change_template = None
    password_change_done_template = None

    def __init__(self, name=None, app_name='admin'):
        self._registry = {} # model_class class -> admin_class instance
        self.root_path = None
        if name is None:
            self.name = 'admin'
        else:
            self.name = name
        self.app_name = app_name
        self._actions = {'delete_selected': actions.delete_selected}
        self._global_actions = self._actions.copy()

    def register(self, model_or_iterable, admin_class=None, **options):
        """
        Registers the given model(s) with the given admin class.

        The model(s) should be Model classes, not instances.

        If an admin class isn't given, it will use ModelAdmin (the default
        admin options). If keyword arguments are given -- e.g., list_display --
        they'll be applied as options to the admin class.

        If a model is already registered, this will raise AlreadyRegistered.

        If a model is abstract, this will raise ImproperlyConfigured.
        """
        if isinstance(model_or_iterable, ModelBase) and not admin_class:
            admin_class = ModelAdmin
        if isinstance(model_or_iterable, TopLevelDocumentMetaclass) and not admin_class:
            admin_class = DocumentAdmin

        # Don't import the humongous validation code unless required
        if admin_class and settings.DEBUG:
            from django_mongoengine.admin.validation import validate
        else:
            validate = lambda model, adminclass: None

        if isinstance(model_or_iterable, ModelBase) or \
                isinstance(model_or_iterable, TopLevelDocumentMetaclass):
            model_or_iterable = [model_or_iterable]

        for model in model_or_iterable:
            if hasattr(model._meta, 'abstract') and model._meta.abstract:
                raise ImproperlyConfigured('The model %s is abstract, so it '
                      'cannot be registered with admin.' % model.__name__)

            if model in self._registry:
                raise AlreadyRegistered('The model %s is already registered' % model.__name__)

            # If we got **options then dynamically construct a subclass of
            # admin_class with those **options.
            if options:
                # For reasons I don't quite understand, without a __module__
                # the created class appears to "live" in the wrong place,
                # which causes issues later on.
                options['__module__'] = __name__
                admin_class = type("%sAdmin" % model.__name__, (admin_class,), options)

            # Validate (which might be a no-op)
            validate(admin_class, model)

            # Instantiate the admin class to save in the registry
            self._registry[model] = admin_class(model, self)

    def unregister(self, model_or_iterable):
        """
        Unregisters the given model(s).

        If a model isn't already registered, this will raise NotRegistered.
        """
        if isinstance(model_or_iterable, ModelBase) or \
                isinstance(model_or_iterable, TopLevelDocumentMetaclass):
            model_or_iterable = [model_or_iterable]
        for model in model_or_iterable:
            if model not in self._registry:
                raise NotRegistered('The model %s is not registered' % model.__name__)
            del self._registry[model]

    def add_action(self, action, name=None):
        """
        Register an action to be available globally.
        """
        name = name or action.__name__
        self._actions[name] = action
        self._global_actions[name] = action

    def disable_action(self, name):
        """
        Disable a globally-registered action. Raises KeyError for invalid names.
        """
        del self._actions[name]

    def get_action(self, name):
        """
        Explicitally get a registered global action wheather it's enabled or
        not. Raises KeyError for invalid names.
        """
        return self._global_actions[name]

    @property
    def actions(self):
        """
        Get all the enabled actions as an iterable of (name, func).
        """
        return self._actions.iteritems()

    def has_permission(self, request):
        """
        Returns True if the given HttpRequest has permission to view
        *at least one* page in the admin site.
        """
        return request.user.is_active and request.user.is_staff

    def check_dependencies(self):
        """
        Check that all things needed to run the admin have been correctly installed.

        The default implementation checks that LogEntry, ContentType and the
        auth context processor are installed.
        """
        from django.contrib.admin.models import LogEntry
        from django.contrib.contenttypes.models import ContentType

        if not LogEntry._meta.installed:
            raise ImproperlyConfigured("Put 'django.contrib.admin' in your "
                "INSTALLED_APPS setting in order to use the admin application.")
        if not ContentType._meta.installed:
            raise ImproperlyConfigured("Put 'django.contrib.contenttypes' in "
                "your INSTALLED_APPS setting in order to use the admin application.")
        if not ('django.contrib.auth.context_processors.auth' in settings.TEMPLATE_CONTEXT_PROCESSORS or
            'django.core.context_processors.auth' in settings.TEMPLATE_CONTEXT_PROCESSORS):
            raise ImproperlyConfigured("Put 'django.contrib.auth.context_processors.auth' "
                "in your TEMPLATE_CONTEXT_PROCESSORS setting in order to use the admin application.")

    def admin_view(self, view, cacheable=False):
        """
        Decorator to create an admin view attached to this ``AdminSite``. This
        wraps the view and provides permission checking by calling
        ``self.has_permission``.

        You'll want to use this from within ``AdminSite.get_urls()``:

            class MyAdminSite(AdminSite):

                def get_urls(self):
                    from django.conf.urls.defaults import patterns, url

                    urls = super(MyAdminSite, self).get_urls()
                    urls += patterns('',
                        url(r'^my_view/$', self.admin_view(some_view))
                    )
                    return urls

        By default, admin_views are marked non-cacheable using the
        ``never_cache`` decorator. If the view can be safely cached, set
        cacheable=True.
        """
        def inner(request, *args, **kwargs):
            if not self.has_permission(request):
                return self.login(request)
            return view(request, *args, **kwargs)
        if not cacheable:
            inner = never_cache(inner)
        # We add csrf_protect here so this function can be used as a utility
        # function for any view, without having to repeat 'csrf_protect'.
        if not getattr(view, 'csrf_exempt', False):
            inner = csrf_protect(inner)
        return update_wrapper(inner, view)

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url, include

        if settings.DEBUG:
            self.check_dependencies()

        def wrap(view, cacheable=False):
            def wrapper(*args, **kwargs):
                return self.admin_view(view, cacheable)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        # Admin-site-wide views.
        urlpatterns = patterns('',
            url(r'^$',
                wrap(self.index),
                name='index'),
            url(r'^logout/$',
                wrap(self.logout),
                name='logout'),
            url(r'^password_change/$',
                wrap(self.password_change, cacheable=True),
                name='password_change'),
            url(r'^password_change/done/$',
                wrap(self.password_change_done, cacheable=True),
                name='password_change_done'),
            url(r'^jsi18n/$',
                wrap(self.i18n_javascript, cacheable=True),
                name='jsi18n'),
            url(r'^r/(?P<content_type_id>\d+)/(?P<object_id>.+)/$',
                wrap(contenttype_views.shortcut)),
            url(r'^(?P<app_label>\w+)/$',
                wrap(self.app_index),
                name='app_list')
        )


        # Add in each model's views.
        for model, model_admin in self._registry.iteritems():
            # Try to read app_label and module_name from classes _meta attribute.
            # If they don't exist we try to add a mongo document. app_label and module_name
            # are then created here and added to the document's _meta.
            try:
                app_label = model._meta.app_label
            except AttributeError:
                app_label = model_admin.opts.app_label

            try:
                module_name = model._meta.module_name
            except AttributeError:
                module_name = model_admin.opts.module_name

            urlpatterns += patterns('',
                url(r'^%s/%s/' % (app_label, module_name),
                    include(model_admin.urls))
            )
        return urlpatterns

    @property
    def urls(self):
        return self.get_urls(), self.app_name, self.name

    def password_change(self, request):
        """
        Handles the "change password" task -- both form display and validation.
        """
        from django.contrib.auth.views import password_change
        if self.root_path is not None:
            url = '%spassword_change/done/' % self.root_path
        else:
            url = reverse('admin:password_change_done', current_app=self.name)
        defaults = {
            'current_app': self.name,
            'post_change_redirect': url
        }
        if self.password_change_template is not None:
            defaults['template_name'] = self.password_change_template
        return password_change(request, **defaults)

    def password_change_done(self, request, extra_context=None):
        """
        Displays the "success" page after a password change.
        """
        from django.contrib.auth.views import password_change_done
        defaults = {
            'current_app': self.name,
            'extra_context': extra_context or {},
        }
        if self.password_change_done_template is not None:
            defaults['template_name'] = self.password_change_done_template
        return password_change_done(request, **defaults)

    def i18n_javascript(self, request):
        """
        Displays the i18n JavaScript that the Django admin requires.

        This takes into account the USE_I18N setting. If it's set to False, the
        generated JavaScript will be leaner and faster.
        """
        if settings.USE_I18N:
            from django.views.i18n import javascript_catalog
        else:
            from django.views.i18n import null_javascript_catalog as javascript_catalog
        return javascript_catalog(request, packages=['django.conf', 'django.contrib.admin'])

    @never_cache
    def logout(self, request, extra_context=None):
        """
        Logs out the user for the given HttpRequest.

        This should *not* assume the user is already logged in.
        """
        from django.contrib.auth.views import logout
        defaults = {
            'current_app': self.name,
            'extra_context': extra_context or {},
        }
        if self.logout_template is not None:
            defaults['template_name'] = self.logout_template
        return logout(request, **defaults)

    @never_cache
    def login(self, request, extra_context=None):
        """
        Displays the login form for the given HttpRequest.
        """
        from django.contrib.auth.views import login
        context = {
            'title': _('Log in'),
            'root_path': self.root_path,
            'app_path': request.get_full_path(),
            REDIRECT_FIELD_NAME: request.get_full_path(),
        }
        context.update(extra_context or {})
        defaults = {
            'extra_context': context,
            'current_app': self.name,
            'authentication_form': self.login_form or AdminAuthenticationForm,
            'template_name': self.login_template or 'admin/login.html',
        }
        return login(request, **defaults)

    @never_cache
    def index(self, request, extra_context=None):
        """
        Displays the main admin index page, which lists all of the installed
        apps that have been registered in this site.
        """
        app_dict = {}
        user = request.user
        for model, model_admin in self._registry.items():
            try:
                app_label = model._meta.app_label
            except AttributeError:
                app_label = model_admin.opts.app_label
            has_module_perms = user.has_module_perms(app_label)

            if has_module_perms:
                perms = model_admin.get_model_perms(request)

                # Check whether user has any perm for this module.
                # If so, add the module to the model_list.
                if True in perms.values():
                    try:
                        name = capfirst(model._meta.verbose_name_plural)
                    except AttributeError:
                        name = capfirst(model_admin.opts.verbose_name_plural)
                    model_dict = {
                        'name': name,
                        'admin_url': mark_safe('%s/%s/' % (app_label, model.__name__.lower())),
                        'perms': perms,
                    }
                    if app_label in app_dict:
                        app_dict[app_label]['models'].append(model_dict)
                    else:
                        app_dict[app_label] = {
                            'name': app_label.title(),
                            'app_url': app_label + '/',
                            'has_module_perms': has_module_perms,
                            'models': [model_dict],
                        }

        # Sort the apps alphabetically.
        app_list = app_dict.values()
        app_list.sort(key=lambda x: x['name'])

        # Sort the models alphabetically within each app.
        for app in app_list:
            app['models'].sort(key=lambda x: x['name'])

        context = {
            'title': _('Site administration'),
            'app_list': app_list,
            'root_path': self.root_path,
        }
        context.update(extra_context or {})
        context_instance = template.RequestContext(request, current_app=self.name)
        return render_to_response(self.index_template or 'admin/index.html', context,
            context_instance=context_instance
        )

    def app_index(self, request, app_label, extra_context=None):
        user = request.user
        has_module_perms = user.has_module_perms(app_label)
        app_dict = {}
        for model, model_admin in self._registry.items():
            try:
                model_app_label = model._meta.app_label
            except AttributeError:
                model_app_label = model._admin_opts.app_label
            if app_label == model_app_label:
                if has_module_perms:
                    perms = model_admin.get_model_perms(request)

                    # Check whether user has any perm for this module.
                    # If so, add the module to the model_list.
                    if True in perms.values():
                        try:
                            name = capfirst(model._meta.verbose_name_plural)
                        except AttributeError:
                            name = capfirst(model._admin_opts.verbose_name_plural)
                        model_dict = {
                            'name': name,
                            'admin_url': '%s/' % model.__name__.lower(),
                            'perms': perms,
                        }
                        if app_dict:
                            app_dict['models'].append(model_dict),
                        else:
                            # First time around, now that we know there's
                            # something to display, add in the necessary meta
                            # information.
                            app_dict = {
                                'name': app_label.title(),
                                'app_url': '',
                                'has_module_perms': has_module_perms,
                                'models': [model_dict],
                            }
        if not app_dict:
            raise http.Http404('The requested admin page does not exist.')
        # Sort the models alphabetically within each app.
        app_dict['models'].sort(key=lambda x: x['name'])
        context = {
            'title': _('%s administration') % capfirst(app_label),
            'app_list': [app_dict],
            'root_path': self.root_path,
        }
        context.update(extra_context or {})
        context_instance = template.RequestContext(request, current_app=self.name)
        return render_to_response(self.app_index_template or ('admin/%s/app_index.html' % app_label,
            'admin/app_index.html'), context,
            context_instance=context_instance
        )

# This global object represents the default admin site, for the common case.
# You can instantiate AdminSite in your own code to create a custom admin site.
site = AdminSite()

########NEW FILE########
__FILENAME__ = documenttags
from django.template import Library

from django.contrib.admin.templatetags.admin_list import (result_hidden_fields, ResultList, items_for_result,
                                                          result_headers)
from django.db.models.fields import FieldDoesNotExist

from mongoengine import fields

from django_mongoengine.forms.document_options import DocumentMetaWrapper

from django_mongoengine.admin.util import label_for_field, display_for_field
from django_mongoengine.forms.utils import patch_document

register = Library()

def serializable_value(self, field_name):
    """
    Returns the value of the field name for this instance. If the field is
    a foreign key, returns the id value, instead of the object. If there's
    no Field object with this name on the model, the model attribute's
    value is returned directly.

    Used to serialize a field's value (in the serializer, or form output,
    for example). Normally, you would just access the attribute directly
    and not use this method.
    """
    try:
        field = self._admin_opts.get_field_by_name(field_name)[0]
    except FieldDoesNotExist:
        return getattr(self, field_name)
    return getattr(self, field.name)

def results(cl):
    """
    Just like the one from Django. Only we add a serializable_value method to
    the document, because Django expects it and mongoengine doesn't have it.
    """
    if cl.formset:
        for res, form in zip(cl.result_list, cl.formset.forms):
            patch_document(serializable_value, res)
            yield ResultList(form, items_for_result(cl, res, form))
    else:
        for res in cl.result_list:
            patch_document(serializable_value, res)
            res._meta = res._admin_opts
            yield ResultList(None, items_for_result(cl, res, None))

def document_result_list(cl):
    """
    Displays the headers and data list together
    """
    headers = list(result_headers(cl))
    try:
        num_sorted_fields = 0
        for h in headers:
            if h['sortable'] and h['sorted']:
                num_sorted_fields += 1
    except KeyError:
        pass

    return {'cl': cl,
            'result_hidden_fields': list(result_hidden_fields(cl)),
            'result_headers': headers,
            'num_sorted_fields': num_sorted_fields,
            'results': list(results(cl))}
result_list = register.inclusion_tag("admin/change_list_results.html")(document_result_list)

########NEW FILE########
__FILENAME__ = mongoadmintags
from django import template
from django.conf import settings

register = template.Library()

class CheckGrappelli(template.Node):
    def __init__(self, var_name):
        self.var_name = var_name
    def render(self, context):
        context[self.var_name] = 'grappelli' in settings.INSTALLED_APPS
        return ''

def check_grappelli(parser, token):
    """
    Checks weather grappelli is in installed apps and sets a variable in the context.
    Unfortunately there is no other way to find out if grappelli is used or not. 
    See: https://github.com/sehmaschine/django-grappelli/issues/32
    
    Usage: {% check_grappelli as <varname> %}
    """
    
    bits = token.contents.split()
    
    if len(bits) != 3:
        raise template.TemplateSyntaxError, "'check_grappelli' tag takes exactly two arguments."
    
    if bits[1] != 'as':
        raise template.TemplateSyntaxError, "The second argument to 'check_grappelli' must be 'as'"
    varname = bits[2]
    
    return CheckGrappelli(varname)

register.tag(check_grappelli)

########NEW FILE########
__FILENAME__ = util
from django.utils.encoding import force_unicode, smart_unicode, smart_str
from django.forms.forms import pretty_name
from django.db.models.fields import FieldDoesNotExist
from django.utils import formats

from mongoengine import fields

from django_mongoengine.forms.document_options import DocumentMetaWrapper
from django_mongoengine.forms.utils import init_document_options


class RelationWrapper(object):
    """
    Wraps a document referenced from a ReferenceField with an Interface similiar to
    django's ForeignKeyField.rel
    """
    def __init__(self, document):
        self.to = init_document_options(document)


def label_for_field(name, model, model_admin=None, return_attr=False):
    attr = None
    model._admin_opts = DocumentMetaWrapper(model)
    try:
        field = model._admin_opts.get_field_by_name(name)[0]
        label = field.name.replace('_', ' ')
    except FieldDoesNotExist:
        if name == "__unicode__":
            label = force_unicode(model._admin_opts.verbose_name)
        elif name == "__str__":
            label = smart_str(model._admin_opts.verbose_name)
        else:
            if callable(name):
                attr = name
            elif model_admin is not None and hasattr(model_admin, name):
                attr = getattr(model_admin, name)
            elif hasattr(model, name):
                attr = getattr(model, name)
            else:
                message = "Unable to lookup '%s' on %s" % (name, model._meta.object_name)
                if model_admin:
                    message += " or %s" % (model_admin.__class__.__name__,)
                raise AttributeError(message)

            if hasattr(attr, "short_description"):
                label = attr.short_description
            elif callable(attr):
                if attr.__name__ == "<lambda>":
                    label = "--"
                else:
                    label = pretty_name(attr.__name__)
            else:
                label = pretty_name(name)
    if return_attr:
        return (label, attr)
    else:
        return label


def display_for_field(value, field):
    from django.contrib.admin.templatetags.admin_list import _boolean_icon
    from django.contrib.admin.views.main import EMPTY_CHANGELIST_VALUE

    # if field.flatchoices:
    #     return dict(field.flatchoices).get(value, EMPTY_CHANGELIST_VALUE)
    # NullBooleanField needs special-case null-handling, so it comes
    # before the general null test.
    if isinstance(field, fields.BooleanField):
        return _boolean_icon(value)
    elif value is None:
        return EMPTY_CHANGELIST_VALUE
    elif isinstance(field, fields.DateTimeField):
        return formats.localize(value)
    elif isinstance(field, fields.DecimalField):
        return formats.number_format(value, field.decimal_places)
    elif isinstance(field, fields.FloatField):
        return formats.number_format(value)
    else:
        return smart_unicode(value)


def help_text_for_field(name, model):
    try:
        help_text = model._meta.get_field_by_name(name)[0].help_text
    except FieldDoesNotExist:
        help_text = ""
    return smart_unicode(help_text, strings_only=True)

########NEW FILE########
__FILENAME__ = validation
from django.contrib.admin.options import flatten_fieldsets, HORIZONTAL, VERTICAL
from django.contrib.admin.util import get_fields_from_path, NotRelationField
from django.contrib.admin.validation import validate as django_validate
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models.fields import FieldDoesNotExist
from django.forms.models import BaseModelForm, _get_foreign_key

from django_mongoengine.forms.documents import (
        DocumentFormMetaclass, fields_for_document, BaseDocumentFormSet
)
from django_mongoengine.forms.document_options import DocumentMetaWrapper

from mongoengine.fields import ListField, EmbeddedDocumentField, ReferenceField
from mongoengine.base import BaseDocument

from options import BaseDocumentAdmin, EmbeddedDocumentAdmin

__all__ = ['validate']


def validate(cls, model):
    if issubclass(model, models.Model):
        django_validate(cls, model)
    else:
        _validate(cls, model)


def _validate(cls, model):
    """
    Does basic ModelAdmin option validation. Calls custom validation
    classmethod in the end if it is provided in cls. The signature of the
    custom validation classmethod should be: def validate(cls, model).
    """
    # Before we can introspect models, they need to be fully loaded so that
    # inter-relations are set up correctly. We force that here.
    #models.get_apps()

    opts = model._meta
    validate_base(cls, model)

    # list_display
    if hasattr(cls, 'list_display'):
        check_isseq(cls, 'list_display', cls.list_display)
        for idx, field in enumerate(cls.list_display):
            if not callable(field):
                if not hasattr(cls, field):
                    if not hasattr(model, field):
                        try:
                            opts.get_field(field)
                        except models.FieldDoesNotExist:
                            raise ImproperlyConfigured("%s.list_display[%d], %r is not a callable or an attribute of %r or found in the model %r."
                                % (cls.__name__, idx, field, cls.__name__, model._meta.object_name))
                    else:
                        # getattr(model, field) could be an X_RelatedObjectsDescriptor
                        f = fetch_attr(cls, model, opts, "list_display[%d]" % idx, field)
                        if isinstance(f, models.ManyToManyField):
                            raise ImproperlyConfigured("'%s.list_display[%d]', '%s' is a ManyToManyField which is not supported."
                                % (cls.__name__, idx, field))

    # list_display_links
    if hasattr(cls, 'list_display_links'):
        check_isseq(cls, 'list_display_links', cls.list_display_links)
        for idx, field in enumerate(cls.list_display_links):
            if field not in cls.list_display:
                raise ImproperlyConfigured("'%s.list_display_links[%d]' "
                        "refers to '%s' which is not defined in 'list_display'."
                        % (cls.__name__, idx, field))

    # list_filter
    if hasattr(cls, 'list_filter'):
        check_isseq(cls, 'list_filter', cls.list_filter)
        #for idx, fpath in enumerate(cls.list_filter):
        #    print idx
        #    print fpath
        #    try:
        #        get_fields_from_path(model, fpath)
        #    except (NotRelationField, FieldDoesNotExist), e:
        #        raise ImproperlyConfigured(
        #            "'%s.list_filter[%d]' refers to '%s' which does not refer to a Field." % (
        ##                cls.__name__, idx, fpath
        #            )
        #        )

    # list_per_page = 100
    if hasattr(cls, 'list_per_page') and not isinstance(cls.list_per_page, int):
        raise ImproperlyConfigured("'%s.list_per_page' should be a integer."
                % cls.__name__)

    # list_editable
    if hasattr(cls, 'list_editable') and cls.list_editable:
        check_isseq(cls, 'list_editable', cls.list_editable)
        for idx, field_name in enumerate(cls.list_editable):
            try:
                field = opts.get_field_by_name(field_name)[0]
            except models.FieldDoesNotExist:
                raise ImproperlyConfigured("'%s.list_editable[%d]' refers to a "
                    "field, '%s', not defined on %s."
                    % (cls.__name__, idx, field_name, model.__name__))
            if field_name not in cls.list_display:
                raise ImproperlyConfigured("'%s.list_editable[%d]' refers to "
                    "'%s' which is not defined in 'list_display'."
                    % (cls.__name__, idx, field_name))
            if field_name in cls.list_display_links:
                raise ImproperlyConfigured("'%s' cannot be in both '%s.list_editable'"
                    " and '%s.list_display_links'"
                    % (field_name, cls.__name__, cls.__name__))
            if not cls.list_display_links and cls.list_display[0] in cls.list_editable:
                raise ImproperlyConfigured("'%s.list_editable[%d]' refers to"
                    " the first field in list_display, '%s', which can't be"
                    " used unless list_display_links is set."
                    % (cls.__name__, idx, cls.list_display[0]))
            if not field.editable:
                raise ImproperlyConfigured("'%s.list_editable[%d]' refers to a "
                    "field, '%s', which isn't editable through the admin."
                    % (cls.__name__, idx, field_name))

    # search_fields = ()
    if hasattr(cls, 'search_fields'):
        check_isseq(cls, 'search_fields', cls.search_fields)

    # date_hierarchy = None
    if cls.date_hierarchy:
        f = get_field(cls, model, opts, 'date_hierarchy', cls.date_hierarchy)
        if not isinstance(f, (models.DateField, models.DateTimeField)):
            raise ImproperlyConfigured("'%s.date_hierarchy is "
                    "neither an instance of DateField nor DateTimeField."
                    % cls.__name__)

    # ordering = None
    if cls.ordering:
        check_isseq(cls, 'ordering', cls.ordering)
        for idx, field in enumerate(cls.ordering):
            if field == '?' and len(cls.ordering) != 1:
                raise ImproperlyConfigured("'%s.ordering' has the random "
                        "ordering marker '?', but contains other fields as "
                        "well. Please either remove '?' or the other fields."
                        % cls.__name__)
            if field == '?':
                continue
            if field.startswith('-'):
                field = field[1:]
            # Skip ordering in the format field1__field2 (FIXME: checking
            # this format would be nice, but it's a little fiddly).
            if '__' in field:
                continue
            get_field(cls, model, opts, 'ordering[%d]' % idx, field)

    if hasattr(cls, "readonly_fields"):
        check_readonly_fields(cls, model, opts)

    # list_select_related = False
    # save_as = False
    # save_on_top = False
    for attr in ('list_select_related', 'save_as', 'save_on_top'):
        if not isinstance(getattr(cls, attr), bool):
            raise ImproperlyConfigured("'%s.%s' should be a boolean."
                    % (cls.__name__, attr))


    # inlines = []
    if hasattr(cls, 'inlines'):
        check_isseq(cls, 'inlines', cls.inlines)
        for idx, inline in enumerate(cls.inlines):
            if not issubclass(inline, BaseDocumentAdmin):
                raise ImproperlyConfigured("'%s.inlines[%d]' does not inherit "
                        "from BaseModelAdmin." % (cls.__name__, idx))
            if not inline.document:
                raise ImproperlyConfigured("'document' is a required attribute "
                        "of '%s.inlines[%d]'." % (cls.__name__, idx))
            if not issubclass(inline.document, BaseDocument):
                raise ImproperlyConfigured("'%s.inlines[%d].model' does not "
                        "inherit from models.Model." % (cls.__name__, idx))
            validate_base(inline, inline.document)
            validate_inline(inline, cls, model)

def validate_inline(cls, parent, parent_model):

    # model is already verified to exist and be a Model
    if cls.fk_name: # default value is None
        f = get_field(cls, cls.model, cls.model._meta, 'fk_name', cls.fk_name)
        if not isinstance(f, models.ForeignKey):
            raise ImproperlyConfigured("'%s.fk_name is not an instance of "
                    "models.ForeignKey." % cls.__name__)

    if not issubclass(cls, EmbeddedDocumentAdmin):
        fk = _get_foreign_key(parent_model, cls.model, fk_name=cls.fk_name, can_fail=True)
    else:
        fk = None

    # extra = 3
    if not isinstance(cls.extra, int):
        raise ImproperlyConfigured("'%s.extra' should be a integer."
                % cls.__name__)

    # max_num = None
    max_num = getattr(cls, 'max_num', None)
    if max_num is not None and not isinstance(max_num, int):
        raise ImproperlyConfigured("'%s.max_num' should be an integer or None (default)."
                % cls.__name__)

    # formset
    if hasattr(cls, 'formset') and not issubclass(cls.formset, BaseDocumentFormSet):
        raise ImproperlyConfigured("'%s.formset' does not inherit from "
                "BaseDocumentFormSet." % cls.__name__)

    # exclude
    if hasattr(cls, 'exclude') and cls.exclude:
        if fk and fk.name in cls.exclude:
            raise ImproperlyConfigured("%s cannot exclude the field "
                    "'%s' - this is the foreign key to the parent model "
                    "%s." % (cls.__name__, fk.name, parent_model.__name__))

    if hasattr(cls, "readonly_fields"):
        check_readonly_fields(cls, cls.document, cls.document._meta)

def validate_base(cls, model):
    opts = model._meta
    if isinstance(opts, dict):
        opts = DocumentMetaWrapper(model)

    # raw_id_fields
    if hasattr(cls, 'raw_id_fields'):
        check_isseq(cls, 'raw_id_fields', cls.raw_id_fields)
        for idx, field in enumerate(cls.raw_id_fields):
            f = get_field(cls, model, opts, 'raw_id_fields', field)
            if not isinstance(f, (models.ForeignKey, models.ManyToManyField)):
                raise ImproperlyConfigured("'%s.raw_id_fields[%d]', '%s' must "
                        "be either a ForeignKey or ManyToManyField."
                        % (cls.__name__, idx, field))

    # fields
    if cls.fields: # default value is None
        check_isseq(cls, 'fields', cls.fields)
        for field in cls.fields:
            if field in cls.readonly_fields:
                # Stuff can be put in fields that isn't actually a model field
                # if it's in readonly_fields, readonly_fields will handle the
                # validation of such things.
                continue
            check_formfield(cls, model, opts, 'fields', field)
            try:
                f = opts.get_field(field)
            except models.FieldDoesNotExist:
                # If we can't find a field on the model that matches,
                # it could be an extra field on the form.
                continue
            if isinstance(f, models.ManyToManyField) and not f.rel.through._meta.auto_created:
                raise ImproperlyConfigured("'%s.fields' can't include the ManyToManyField "
                    "field '%s' because '%s' manually specifies "
                    "a 'through' model." % (cls.__name__, field, field))
        if cls.fieldsets:
            raise ImproperlyConfigured('Both fieldsets and fields are specified in %s.' % cls.__name__)
        if len(cls.fields) > len(set(cls.fields)):
            raise ImproperlyConfigured('There are duplicate field(s) in %s.fields' % cls.__name__)

    # fieldsets
    if cls.fieldsets: # default value is None
        check_isseq(cls, 'fieldsets', cls.fieldsets)
        for idx, fieldset in enumerate(cls.fieldsets):
            check_isseq(cls, 'fieldsets[%d]' % idx, fieldset)
            if len(fieldset) != 2:
                raise ImproperlyConfigured("'%s.fieldsets[%d]' does not "
                        "have exactly two elements." % (cls.__name__, idx))
            check_isdict(cls, 'fieldsets[%d][1]' % idx, fieldset[1])
            if 'fields' not in fieldset[1]:
                raise ImproperlyConfigured("'fields' key is required in "
                        "%s.fieldsets[%d][1] field options dict."
                        % (cls.__name__, idx))
            for fields in fieldset[1]['fields']:
                # The entry in fields might be a tuple. If it is a standalone
                # field, make it into a tuple to make processing easier.
                if type(fields) != tuple:
                    fields = (fields,)
                for field in fields:
                    if field in cls.readonly_fields:
                        # Stuff can be put in fields that isn't actually a
                        # model field if it's in readonly_fields,
                        # readonly_fields will handle the validation of such
                        # things.
                        continue
                    check_formfield(cls, model, opts, "fieldsets[%d][1]['fields']" % idx, field)
                    try:
                        f = opts.get_field(field)
                        if isinstance(f, models.ManyToManyField) and not f.rel.through._meta.auto_created:
                            raise ImproperlyConfigured("'%s.fieldsets[%d][1]['fields']' "
                                "can't include the ManyToManyField field '%s' because "
                                "'%s' manually specifies a 'through' model." % (
                                    cls.__name__, idx, field, field))
                    except models.FieldDoesNotExist:
                        # If we can't find a field on the model that matches,
                        # it could be an extra field on the form.
                        pass
        flattened_fieldsets = flatten_fieldsets(cls.fieldsets)
        if len(flattened_fieldsets) > len(set(flattened_fieldsets)):
            raise ImproperlyConfigured('There are duplicate field(s) in %s.fieldsets' % cls.__name__)

    # exclude
    if cls.exclude: # default value is None
        check_isseq(cls, 'exclude', cls.exclude)
        for field in cls.exclude:
            check_formfield(cls, model, opts, 'exclude', field)
            try:
                f = opts.get_field(field)
            except models.FieldDoesNotExist:
                # If we can't find a field on the model that matches,
                # it could be an extra field on the form.
                continue
        if len(cls.exclude) > len(set(cls.exclude)):
            raise ImproperlyConfigured('There are duplicate field(s) in %s.exclude' % cls.__name__)

    # form
    # TODO: FInd out why issubclass doesn't work!
    if hasattr(cls, 'form') and not (issubclass(cls.form, BaseModelForm) or
                                     cls.form.__class__.__name__ == 'DocumentFormMetaclass'):
        raise ImproperlyConfigured("%s.form does not inherit from "
                "BaseModelForm." % cls.__name__)

    # filter_vertical
    if hasattr(cls, 'filter_vertical'):
        check_isseq(cls, 'filter_vertical', cls.filter_vertical)
        for idx, field in enumerate(cls.filter_vertical):
            f = get_field(cls, model, opts, 'filter_vertical', field)
            if not isinstance(f, models.ManyToManyField):
                raise ImproperlyConfigured("'%s.filter_vertical[%d]' must be "
                    "a ManyToManyField." % (cls.__name__, idx))

    # filter_horizontal
    if hasattr(cls, 'filter_horizontal'):
        check_isseq(cls, 'filter_horizontal', cls.filter_horizontal)
        for idx, field in enumerate(cls.filter_horizontal):
            f = get_field(cls, model, opts, 'filter_horizontal', field)
            if not isinstance(f, ListField) and not isinstance(f.field, ReferenceField):
                raise ImproperlyConfigured("'%s.filter_horizontal[%d]' must be "
                    "a ManyToManyField." % (cls.__name__, idx))

    # radio_fields
    if hasattr(cls, 'radio_fields'):
        check_isdict(cls, 'radio_fields', cls.radio_fields)
        for field, val in cls.radio_fields.items():
            f = get_field(cls, model, opts, 'radio_fields', field)
            if not (isinstance(f, models.ForeignKey) or f.choices):
                raise ImproperlyConfigured("'%s.radio_fields['%s']' "
                        "is neither an instance of ForeignKey nor does "
                        "have choices set." % (cls.__name__, field))
            if not val in (HORIZONTAL, VERTICAL):
                raise ImproperlyConfigured("'%s.radio_fields['%s']' "
                        "is neither admin.HORIZONTAL nor admin.VERTICAL."
                        % (cls.__name__, field))

    # prepopulated_fields
    if hasattr(cls, 'prepopulated_fields'):
        check_isdict(cls, 'prepopulated_fields', cls.prepopulated_fields)
        for field, val in cls.prepopulated_fields.items():
            f = get_field(cls, model, opts, 'prepopulated_fields', field)
            if isinstance(f, (models.DateTimeField, models.ForeignKey,
                models.ManyToManyField)):
                raise ImproperlyConfigured("'%s.prepopulated_fields['%s']' "
                        "is either a DateTimeField, ForeignKey or "
                        "ManyToManyField. This isn't allowed."
                        % (cls.__name__, field))
            check_isseq(cls, "prepopulated_fields['%s']" % field, val)
            for idx, f in enumerate(val):
                get_field(cls, model, opts, "prepopulated_fields['%s'][%d]" % (field, idx), f)

def check_isseq(cls, label, obj):
    if not isinstance(obj, (list, tuple)):
        raise ImproperlyConfigured("'%s.%s' must be a list or tuple." % (cls.__name__, label))

def check_isdict(cls, label, obj):
    if not isinstance(obj, dict):
        raise ImproperlyConfigured("'%s.%s' must be a dictionary." % (cls.__name__, label))

def get_field(cls, model, opts, label, field):
    try:
        return opts.get_field(field)
    except models.FieldDoesNotExist:
        raise ImproperlyConfigured("'%s.%s' refers to field '%s' that is missing from model '%s'."
                % (cls.__name__, label, field, model.__name__))

def check_formfield(cls, model, opts, label, field):
    if getattr(cls.form, 'base_fields', None):
        try:
            cls.form.base_fields[field]
        except KeyError:
            raise ImproperlyConfigured("'%s.%s' refers to field '%s' that "
                "is missing from the form." % (cls.__name__, label, field))
    else:
        fields = fields_for_document(model)
        try:
            fields[field]
        except KeyError:
            if hasattr(model, field) and isinstance(getattr(model, field), ListField):
                if isinstance(model._fields[field].field, EmbeddedDocumentField):
                    return
            if hasattr(model, field) and isinstance(getattr(model, field), EmbeddedDocumentField):
                return
            raise ImproperlyConfigured("'%s.%s' refers to field '%s' that "
                "is missing from the form." % (cls.__name__, label, field))

def fetch_attr(cls, model, opts, label, field):
    try:
        return getattr(model, field)
    except AttributeError:
        raise ImproperlyConfigured("'%s.%s' refers to '%s' that is neither a field, method or property of model '%s'."
            % (cls.__name__, label, field, model.__name__))

def check_readonly_fields(cls, model, opts):
    check_isseq(cls, "readonly_fields", cls.readonly_fields)
    for idx, field in enumerate(cls.readonly_fields):
        if not callable(field):
            if not hasattr(cls, field):
                if not hasattr(model, field):
                    try:
                        opts.get_field(field)
                    except models.FieldDoesNotExist:
                        raise ImproperlyConfigured("%s.readonly_fields[%d], %r is not a callable or an attribute of %r or found in the model %r."
                            % (cls.__name__, idx, field, cls.__name__, model._meta.object_name))

########NEW FILE########
__FILENAME__ = views
import operator

from django.core.exceptions import SuspiciousOperation, ImproperlyConfigured
from django.contrib.admin.views.main import (
    ChangeList, ORDER_VAR, ALL_VAR, ORDER_TYPE_VAR, SEARCH_VAR, IS_POPUP_VAR,
    TO_FIELD_VAR)
from django.contrib.admin.options import IncorrectLookupParameters
from django.core.paginator import InvalidPage
from django.utils.encoding import smart_str

from mongoengine import Q


class DocumentChangeList(ChangeList):
    def __init__(self, request, model, list_display, list_display_links,
            list_filter, date_hierarchy, search_fields, list_select_related,
            list_per_page, list_max_show_all, list_editable, model_admin):
        try:
            super(DocumentChangeList, self).__init__(
                request, model, list_display, list_display_links, list_filter,
                date_hierarchy, search_fields, list_select_related,
                list_per_page, list_max_show_all, list_editable, model_admin)
        except TypeError:
            self.list_max_show_all = list_max_show_all
            # The init for django <= 1.3 takes one parameter less
            super(DocumentChangeList, self).__init__(
                request, model, list_display, list_display_links, list_filter,
                date_hierarchy, search_fields, list_select_related,
                list_per_page, list_editable, model_admin)
        self.pk_attname = self.lookup_opts.pk_name

    def get_results(self, request):
        paginator = self.model_admin.get_paginator(request, self.query_set,
                                                   self.list_per_page)
        # Get the number of objects, with admin filters applied.
        result_count = paginator.count

        # Get the total number of objects, with no admin filters applied.
        # Perform a slight optimization: Check to see whether any filters were
        # given. If not, use paginator.hits to calculate the number of objects,
        # because we've already done paginator.hits and the value is cached.
        if len(self.query_set._query) == 1:
            full_result_count = result_count
        else:
            full_result_count = self.root_query_set.count()

        can_show_all = result_count <= self.list_max_show_all
        multi_page = result_count > self.list_per_page

        # Get the list of objects to display on this page.
        if (self.show_all and can_show_all) or not multi_page:
            result_list = self.query_set.clone()
        else:
            try:
                result_list = paginator.page(self.page_num+1).object_list
            except InvalidPage:
                raise IncorrectLookupParameters

        self.result_count = result_count
        self.full_result_count = full_result_count
        self.result_list = result_list
        self.can_show_all = can_show_all
        self.multi_page = multi_page
        self.paginator = paginator

    def _get_default_ordering(self):
        try:
            ordering = super(DocumentChangeList, self)._get_default_ordering()
        except AttributeError:
            ordering = []
            if self.model_admin.ordering:
                ordering = self.model_admin.ordering
            elif self.lookup_opts.ordering:
                ordering = self.lookup_opts.ordering
        return ordering

    def get_ordering(self, request=None, queryset=None):
        """
        Returns the list of ordering fields for the change list.
        First we check the get_ordering() method in model admin, then we check
        the object's default ordering. Then, any manually-specified ordering
        from the query string overrides anything. Finally, a deterministic
        order is guaranteed by ensuring the primary key is used as the last
        ordering field.
        """
        if queryset is None:
            # with Django < 1.4 get_ordering works without fixes for mongoengine 
            return super(DocumentChangeList, self).get_ordering()

        params = self.params
        ordering = list(self.model_admin.get_ordering(request)
                        or self._get_default_ordering())
        if ORDER_VAR in params:
            # Clear ordering and used params
            ordering = []
            order_params = params[ORDER_VAR].split('.')
            for p in order_params:
                try:
                    none, pfx, idx = p.rpartition('-')
                    field_name = self.list_display[int(idx)]
                    order_field = self.get_ordering_field(field_name)
                    if not order_field:
                        continue # No 'admin_order_field', skip it
                    ordering.append(pfx + order_field)
                except (IndexError, ValueError):
                    continue # Invalid ordering specified, skip it.

        # Add the given query's ordering fields, if any.
        sign = lambda t: t[1] > 0 and '+' or '-'
        qs_ordering = [sign(t) + t[0] for t in queryset._ordering]
        ordering.extend(qs_ordering)

        # Ensure that the primary key is systematically present in the list of
        # ordering fields so we can guarantee a deterministic order across all
        # database backends.
        pk_name = self.lookup_opts.pk.name
        if not (set(ordering) & set(['pk', '-pk', pk_name, '-' + pk_name])):
            # The two sets do not intersect, meaning the pk isn't present. So
            # we add it.
            ordering.append('pk')
        return ordering

    def _lookup_param_1_3(self):
        lookup_params = self.params.copy() # a dictionary of the query string
        for i in (ALL_VAR, ORDER_VAR, ORDER_TYPE_VAR, SEARCH_VAR,
                  IS_POPUP_VAR, TO_FIELD_VAR):
            if i in lookup_params:
                del lookup_params[i]
        for key, value in lookup_params.items():
            if not isinstance(key, str):
                # 'key' will be used as a keyword argument later, so Python
                # requires it to be a string.
                del lookup_params[key]
                lookup_params[smart_str(key)] = value

            # if key ends with __in, split parameter into separate values
            if key.endswith('__in'):
                value = value.split(',')
                lookup_params[key] = value

            # if key ends with __isnull, special case '' and false
            if key.endswith('__isnull'):
                if value.lower() in ('', 'false'):
                    value = False
                else:
                    value = True
                lookup_params[key] = value

            if not self.model_admin.lookup_allowed(key, value):
                raise SuspiciousOperation(
                    "Filtering by %s not allowed" % key
                )
        return lookup_params

    def get_query_set(self, request=None):
        # First, we collect all the declared list filters.
        qs = self.root_query_set.clone()

        try:
            (self.filter_specs, self.has_filters, remaining_lookup_params,
             use_distinct) = self.get_filters(request)

            # Then, we let every list filter modify the queryset to its liking.
            for filter_spec in self.filter_specs:
                new_qs = filter_spec.queryset(request, qs)
                if new_qs is not None:
                    qs = new_qs
        except ValueError:
            # Django < 1.4.
            remaining_lookup_params = self._lookup_param_1_3()

        try:
            # Finally, we apply the remaining lookup parameters from the query
            # string (i.e. those that haven't already been processed by the
            # filters).
            qs = qs.filter(**remaining_lookup_params)
            # TODO: This should probably be mongoengine exceptions 
        except (SuspiciousOperation, ImproperlyConfigured):
            # Allow certain types of errors to be re-raised as-is so that the
            # caller can treat them in a special way.
            raise
        except Exception, e:
            # Every other error is caught with a naked except, because we don't
            # have any other way of validating lookup parameters. They might be
            # invalid if the keyword arguments are incorrect, or if the values
            # are not in the correct type, so we might get FieldError,
            # ValueError, ValidationError, or ?.   
            raise IncorrectLookupParameters(e)

        # Set ordering.
        ordering = self.get_ordering(request, qs)
        qs = qs.order_by(*ordering)

        # Apply keyword searches.
        def construct_search(field_name):
            if field_name.startswith('^'):
                return "%s__istartswith" % field_name[1:]
            elif field_name.startswith('='):
                return "%s__iexact" % field_name[1:]
            # No __search for mongoengine
            #elif field_name.startswith('@'):
            #    return "%s__search" % field_name[1:]
            else:
                return "%s__icontains" % field_name

        if self.search_fields and self.query:
            orm_lookups = [construct_search(str(search_field))
                           for search_field in self.search_fields]
            for bit in self.query.split():
                or_queries = [Q(**{orm_lookup: bit})
                              for orm_lookup in orm_lookups]
                qs = qs.filter(reduce(operator.or_, or_queries))
        return qs
########NEW FILE########
__FILENAME__ = admin
from django.contrib.auth.models import User, Group

from django_mongoengine import admin

admin.site.unregister(Group)
admin.site.unregister(User)

########NEW FILE########
__FILENAME__ = backends
from django.contrib.auth.models import AnonymousUser
from django_mongoengine.auth.models import User


class MongoEngineBackend(object):
    """Authenticate using MongoEngine and mongoengine.django.auth.User.
    """

    supports_object_permissions = False
    supports_anonymous_user = False
    supports_inactive_user = False

    def authenticate(self, username=None, password=None):
        user = User.objects(username=username).first()
        if user:
            if password and user.check_password(password):
                return user
        return None

    def get_user(self, user_id):
        user = User.objects.with_id(user_id)
        user.id.__class__.__int__ = lambda self: int("%s" % self, 17)
        return user


def get_user(userid):
    """Returns a User object from an id (User.id). Django's equivalent takes
    request, but taking an id instead leaves it up to the developer to store
    the id in any way they want (session, signed cookie, etc.)
    """
    if not userid:
        return AnonymousUser()
    return MongoEngineBackend().get_user(userid) or AnonymousUser()

########NEW FILE########
__FILENAME__ = models
import datetime

from django_mongoengine import document
from django_mongoengine import fields

from django.utils.encoding import smart_str
from django.contrib.auth.models import AnonymousUser
from django.utils.translation import ugettext_lazy as _

try:
    from django.contrib.auth.hashers import check_password, make_password
except ImportError:
    """Handle older versions of Django"""
    from django.utils.hashcompat import md5_constructor, sha_constructor

    def get_hexdigest(algorithm, salt, raw_password):
        raw_password, salt = smart_str(raw_password), smart_str(salt)
        if algorithm == 'md5':
            return md5_constructor(salt + raw_password).hexdigest()
        elif algorithm == 'sha1':
            return sha_constructor(salt + raw_password).hexdigest()
        raise ValueError('Got unknown password algorithm type in password')

    def check_password(raw_password, password):
        algo, salt, hash = password.split('$')
        return hash == get_hexdigest(algo, salt, raw_password)

    def make_password(raw_password):
        from random import random
        algo = 'sha1'
        salt = get_hexdigest(algo, str(random()), str(random()))[:5]
        hash = get_hexdigest(algo, salt, raw_password)
        return '%s$%s$%s' % (algo, salt, hash)


class User(document.Document):
    """A User document that aims to mirror most of the API specified by Django
    at http://docs.djangoproject.com/en/dev/topics/auth/#users
    """
    username = fields.StringField(max_length=30, required=True,
                           verbose_name=_('username'),
                           help_text=_("""Required. 30 characters or fewer.
Letters, numbers and @/./+/-/_ characters"""))
    first_name = fields.StringField(max_length=30,
                                    verbose_name=_('first name'))
    last_name = fields.StringField(max_length=30, verbose_name=_('last name'))
    email = fields.EmailField(verbose_name=_('e-mail address'))
    password = fields.StringField(max_length=128, verbose_name=_('password'),
                           help_text=_("""Use
'[algo]$[iterations]$[salt]$[hexdigest]' or use the
<a href=\"password/\">change password form</a>."""))
    is_staff = fields.BooleanField(default=False,
                            verbose_name=_('staff status'),
                            help_text=_("""Designates whether the user can
log into this admin site."""))
    is_active = fields.BooleanField(default=True, verbose_name=_('active'),
                             help_text=_("""Designates whether this user should
be treated as active. Unselect this instead of deleting accounts."""))
    is_superuser = fields.BooleanField(default=False,
                                verbose_name=_('superuser status'),
                                help_text=_("""Designates that this user has
all permissions without explicitly assigning them."""))
    last_login = fields.DateTimeField(default=datetime.datetime.now,
                               verbose_name=_('last login'))
    date_joined = fields.DateTimeField(default=datetime.datetime.now,
                                verbose_name=_('date joined'))

    meta = {
        'allow_inheritance': True,
        'indexes': [
            {'fields': ['username'], 'unique': True}
        ]
    }

    def __unicode__(self):
        return self.username

    def get_full_name(self):
        """Returns the users first and last names, separated by a space.
        """
        full_name = u'%s %s' % (self.first_name or '', self.last_name or '')
        return full_name.strip()

    def is_anonymous(self):
        return False

    def is_authenticated(self):
        return True

    def set_password(self, raw_password):
        """Sets the user's password - always use this rather than directly
        assigning to :attr:`~mongoengine.django.auth.User.password` as the
        password is hashed before storage.
        """
        self.password = make_password(raw_password)
        self.save()
        return self

    def check_password(self, raw_password):
        """Checks the user's password against a provided password - always use
        this rather than directly comparing to
        :attr:`~mongoengine.django.auth.User.password` as the password is
        hashed before storage.
        """
        return check_password(raw_password, self.password)

    @classmethod
    def create_user(cls, username, email, password):
        """Create (and save) a new user with the given username, password and
        email address.
        """
        now = datetime.datetime.now()

        # Normalize the address by lowercasing the domain part of the email
        # address.
        if email is not None:
            try:
                email_name, domain_part = email.strip().split('@', 1)
            except ValueError:
                pass
            else:
                email = '@'.join([email_name, domain_part.lower()])

        user = cls(username=username, email=email, date_joined=now)
        user.set_password(password)
        user.save()
        return user

    @classmethod
    def create_superuser(cls, username, email, password):
        u = cls.create_user(username, email, password)
        u.update(set__is_staff=True,
                 set__is_active=True,
                 set__is_superuser=True)
        return u

    def get_and_delete_messages(self):
        return []

    def has_perm(self, perm, obj=None):
        return True

    def has_perms(self, perm_list, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

########NEW FILE########
__FILENAME__ = operation_tracker
import functools
import time
import inspect
import copy
import sys
import os
import SocketServer

import pymongo
import pymongo.collection
import pymongo.cursor
import pymongo.helpers

from bson import SON


__all__ = ['queries', 'inserts', 'updates', 'removes', 'install_tracker',
           'uninstall_tracker', 'reset', 'response_sizes']


_original_methods = {
    'insert': pymongo.collection.Collection.insert,
    'update': pymongo.collection.Collection.update,
    'remove': pymongo.collection.Collection.remove,
    'refresh': pymongo.cursor.Cursor._refresh,
    '_unpack_response': pymongo.helpers._unpack_response,
}

queries = []
inserts = []
updates = []
removes = []
response_sizes = []

# Wrap helpers._unpack_response for getting response size
@functools.wraps(_original_methods['_unpack_response'])
def _unpack_response(response, *args, **kwargs):

    result = _original_methods['_unpack_response'](
        response,
        *args,
        **kwargs
    )
    response_sizes.append(sys.getsizeof(response) / 1024.0)
    return result

# Wrap Cursor.insert for getting queries
@functools.wraps(_original_methods['insert'])
def _insert(collection_self, doc_or_docs, manipulate=True,
           safe=False, **kwargs):
    start_time = time.time()
    result = _original_methods['insert'](
        collection_self,
        doc_or_docs,
        safe=safe,
        **kwargs
    )
    total_time = (time.time() - start_time) * 1000

    __traceback_hide__ = True
    #stack_trace, internal = _tidy_stacktrace()
    stack_trace, internal = [], False
    inserts.append({
        'document': doc_or_docs,
        'safe': safe,
        'time': total_time,
        'stack_trace': stack_trace,
        'size': response_sizes[-1],
        'internal': internal
    })
    return result

# Wrap Cursor.update for getting queries
@functools.wraps(_original_methods['update'])
def _update(collection_self, spec, document, upsert=False,
           maniuplate=False, safe=False, multi=False, **kwargs):
    start_time = time.time()
    result = _original_methods['update'](
        collection_self,
        spec,
        document,
        upsert=upsert,
        safe=safe,
        multi=multi,
        **kwargs
    )
    total_time = (time.time() - start_time) * 1000

    __traceback_hide__ = True
    #stack_trace, internal = _tidy_stacktrace()
    stack_trace, internal = [], False
    updates.append({
        'document': document,
        'upsert': upsert,
        'multi': multi,
        'spec': spec,
        'safe': safe,
        'time': total_time,
        'stack_trace': stack_trace,
        'size': response_sizes[-1],
        'internal': internal
    })
    return result

# Wrap Cursor.remove for getting queries
@functools.wraps(_original_methods['remove'])
def _remove(collection_self, spec_or_id, safe=False, **kwargs):
    start_time = time.time()
    result = _original_methods['remove'](
        collection_self,
        spec_or_id,
        safe=safe,
        **kwargs
    )
    total_time = (time.time() - start_time) * 1000

    __traceback_hide__ = True
    #stack_trace, internal = _tidy_stacktrace()
    stack_trace, internal = [], False
    removes.append({
        'spec_or_id': spec_or_id,
        'safe': safe,
        'time': total_time,
        '   ': stack_trace,
        'size': response_sizes[-1] if response_sizes else 0,
        'internal': internal
    })
    return result

# Wrap Cursor._refresh for getting queries
@functools.wraps(_original_methods['refresh'])
def _cursor_refresh(cursor_self):
    # Look up __ private instance variables
    def privar(name):
        return getattr(cursor_self, '_Cursor__{0}'.format(name))

    if privar('id') is not None:
        # getMore not query - move on
        return _original_methods['refresh'](cursor_self)

    # NOTE: See pymongo/cursor.py+557 [_refresh()] and
    # pymongo/message.py for where information is stored

    # Time the actual query
    start_time = time.time()
    result = _original_methods['refresh'](cursor_self)
    total_time = (time.time() - start_time) * 1000

    query_son = privar('query_spec')()
    if not isinstance(query_son, SON):
        if not query_son:
            return result

        if "$query" not in query_son:
            query_son = {"$query": query_son}

        data = privar("data")
        if data:
            query_son["data"] = data

        orderby = privar("ordering")
        if orderby:
            query_son["$orderby"] = orderby

        hint = privar("hint")
        if hint:
            query_son["$hint"] = hint

        snapshot = privar("snapshot")
        if snapshot:
            query_son["$snapshot"] = snapshot

        maxScan = privar("max_scan")
        if maxScan:
            query_son["$maxScan"] = maxScan

    __traceback_hide__ = True
    stack_trace, internal = _tidy_stacktrace()
    #stack_trace, internal = [], False
    query_data = {
        'time': total_time,
        'operation': 'query',
        'stack_trace': stack_trace,
        'size': response_sizes[-1],
        'data': copy.copy(privar('data')),
        'internal': internal
    }

    # Collection in format <db_name>.<collection_name>
    collection_name = privar('collection')
    query_data['collection'] = collection_name.full_name.split('.')[1]

    if query_data['collection'] == '$cmd':
        query_data['operation'] = 'command'
        # Handle count as a special case
        if 'count' in query_son:
            # Information is in a different format to a standar query
            query_data['collection'] = query_son['count']
            query_data['operation'] = 'count'
            query_data['skip'] = query_son.get('skip')
            query_data['limit'] = query_son.get('limit')
            query_data['query'] = query_son['query']
    else:
        # Normal Query
        query_data['skip'] = privar('skip')
        query_data['limit'] = privar('limit')
        query_data['query'] = query_son['$query']
        query_data['ordering'] = _get_ordering(query_son)

    queries.append(query_data)

    return result

def install_tracker():
    if pymongo.collection.Collection.insert != _insert:
        pymongo.collection.Collection.insert = _insert
    if pymongo.collection.Collection.update != _update:
        pymongo.collection.Collection.update = _update
    if pymongo.collection.Collection.remove != _remove:
        pymongo.collection.Collection.remove = _remove
    if pymongo.cursor.Cursor._refresh != _cursor_refresh:
        pymongo.cursor.Cursor._refresh = _cursor_refresh
    if pymongo.helpers._unpack_response != _unpack_response:
        pymongo.helpers._unpack_response = _unpack_response

def uninstall_tracker():
    if pymongo.collection.Collection.insert == _insert:
        pymongo.collection.Collection.insert = _original_methods['insert']
    if pymongo.collection.Collection.update == _update:
        pymongo.collection.Collection.update = _original_methods['update']
    if pymongo.collection.Collection.remove == _remove:
        pymongo.collection.Collection.remove = _original_methods['remove']
    if pymongo.cursor.Cursor._refresh == _cursor_refresh:
        pymongo.cursor.Cursor._refresh = _original_methods['cursor_refresh']
    if pymongo.helpers._unpack_response == _unpack_response:
        pymongo.helpers._unpack_response = _original_methods['_unpack_response']

def reset():
    global queries, inserts, updates, removes, response_sizes
    queries = []
    inserts = []
    updates = []
    removes = []
    response_sizes = []

def _get_ordering(son):
    """Helper function to extract formatted ordering from dict.
    """
    def fmt(field, direction):
        return '{0}{1}'.format({-1: '-', 1: '+'}[direction], field)

    if '$orderby' in son:
        return ', '.join(fmt(f, d) for f, d in son['$orderby'].items())

def _tidy_stacktrace():
    """
    Tidy the stack_trace
    """
    socketserver_path = os.path.realpath(os.path.dirname(SocketServer.__file__))
    pymongo_path = os.path.realpath(os.path.dirname(pymongo.__file__))
    paths = ['/site-packages/', '/debug_toolbar/', socketserver_path, pymongo_path]
    internal = False

    start_time = time.time()
    stack = inspect.stack()
    total_time = (time.time() - start_time) * 1000

    start_time = time.time()
    reversed(stack)
    total_time = (time.time() - start_time) * 1000

    start_time = time.time()
    trace = []
    for frame, path, line_no, func_name, text in (f[:5] for f in stack):
        s_path = os.path.realpath(path)
        # Support hiding of frames -- used in various utilities that provide
        # inspection.
        if '__traceback_hide__' in frame.f_locals:
            continue
        hidden = False
        if func_name == "<genexpr>":
            hidden = True
        if any([p for p in paths if p in s_path]):
            hidden = True
        if not text:
            text = ''
        else:
            text = (''.join(text)).strip()
        trace.append((s_path, line_no, func_name, text, hidden))
    total_time = (time.time() - start_time) * 1000

    return trace, internal
########NEW FILE########
__FILENAME__ = panel
from django.conf import settings
from django.template.loader import render_to_string

from debug_toolbar.panels import DebugPanel
import operation_tracker

_ = lambda x: x


class MongoDebugPanel(DebugPanel):
    """Panel that shows information about MongoDB operations (including stack)

    Adapted from https://github.com/hmarr/django-debug-toolbar-mongo
    """
    name = 'MongoDB'
    has_content = True

    def __init__(self, *args, **kwargs):
        """
        Install the tracker
        """
        super(MongoDebugPanel, self).__init__(*args, **kwargs)
        operation_tracker.install_tracker()

    def process_request(self, request):
        operation_tracker.reset()

    def nav_title(self):
        return 'MongoDB'

    def nav_subtitle(self):
        attrs = ['queries', 'inserts', 'updates', 'removes']
        ops = sum(sum((1 for o in getattr(operation_tracker, a)
                         if not o['internal']))
                         for a in attrs)
        total_time = sum(sum(o['time'] for o in getattr(operation_tracker, a))
                         for a in attrs)
        return '{0} operations in {1:.2f}ms'.format(ops, total_time)

    def title(self):
        return 'MongoDB Operations'

    def url(self):
        return ''

    def content(self):
        context = self.context.copy()
        context['queries'] = operation_tracker.queries
        context['inserts'] = operation_tracker.inserts
        context['updates'] = operation_tracker.updates
        context['removes'] = operation_tracker.removes
        context['slow_query_limit'] = getattr(settings, 'MONGODB_DEBUG_PANEL_SLOW_QUERY_LIMIT', 100)
        return render_to_string('mongodb-panel.html', context)

########NEW FILE########
__FILENAME__ = mongodb_debug_tags
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

import pprint
import os

register = template.Library()

@register.filter
def format_stack_trace(value):
    stack_trace = []
    fmt = (
        '<span class="path">{0}/</span>'
        '<span class="file">{1}</span> in <span class="func">{3}</span>'
        '(<span class="lineno">{2}</span>) <span class="code">{4}</span>'
    )
    for frame in value:
        params = map(escape, frame[0].rsplit('/', 1) + list(frame[1:]))
        stack_trace.append(fmt.format(*params))
    return mark_safe('\n'.join(stack_trace))

@register.filter
def embolden_file(path):
    head, tail = os.path.split(escape(path))
    return mark_safe(os.sep.join([head, '<strong>{0}</strong>'.format(tail)]))

@register.filter
def format_dict(value, width=60):
    return pprint.pformat(value, width=int(width))

@register.filter
def highlight(value, language):
    try:
        from pygments import highlight
        from pygments.lexers import get_lexer_by_name
        from pygments.formatters import HtmlFormatter
    except ImportError:
        return value
    # Can't use class-based colouring because the debug toolbar's css rules
    # are more specific so take precedence
    formatter = HtmlFormatter(style='friendly', nowrap=True, noclasses=True)
    return highlight(value, get_lexer_by_name(language), formatter)
########NEW FILE########
__FILENAME__ = documents
import os
import itertools
import gridfs
import datetime

from django.utils.datastructures import SortedDict

from django.forms.forms import BaseForm, get_declared_fields, NON_FIELD_ERRORS, pretty_name
from django.forms.widgets import media_property
from django.core.exceptions import FieldError
from django.core.validators import EMPTY_VALUES
from django.forms.util import ErrorList
from django.forms.formsets import BaseFormSet, formset_factory
from django.utils.translation import ugettext_lazy as _
from django.utils.text import capfirst

from mongoengine.fields import ObjectIdField, ListField, ReferenceField, FileField, ImageField
from mongoengine.base import ValidationError
from mongoengine.connection import _get_db

from .field_generator import MongoFormFieldGenerator
from .document_options import DocumentMetaWrapper


def _get_unique_filename(name):
    fs = gridfs.GridFS(_get_db())
    file_root, file_ext = os.path.splitext(name)
    count = itertools.count(1)
    while fs.exists(filename=name):
        # file_ext includes the dot.
        name = os.path.join("%s_%s%s" % (file_root, count.next(), file_ext))
    return name


def construct_instance(form, instance, fields=None, exclude=None, ignore=None):
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

    for f in instance._fields.itervalues():
        if isinstance(f, ObjectIdField):
            continue
        if not f.name in cleaned_data:
            continue
        if fields is not None and f.name not in fields:
            continue
        if exclude and f.name in exclude:
            continue
        if f.primary_key and cleaned_data[f.name] == getattr(instance, f.name):
            continue

        # Defer saving file-type fields until after the other fields, so a
        # callable upload_to can use the values from other fields.
        if isinstance(f, FileField) or isinstance(f, ImageField):
            file_field_list.append(f)
        else:
            setattr(instance, f.name, cleaned_data[f.name])

    for f in file_field_list:
        upload = cleaned_data[f.name]
        if upload is None:
            continue
        field = getattr(instance, f.name)
        try:
            upload.file.seek(0)
            filename = _get_unique_filename(upload.name)
            field.replace(upload, content_type=upload.content_type, filename=filename)
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
    Saves bound Form ``form``'s cleaned_data into document instance ``instance``.

    If commit=True, then the changes to ``instance`` will be saved to the
    database. Returns ``instance``.

    If construct=False, assume ``instance`` has already been constructed and
    just needs to be saved.
    """
    instance = construct_instance(form, instance, fields, exclude)
    if form.errors:
        raise ValueError("The %s could not be %s because the data didn't"
                         " validate." % (instance.__class__.__name__,
                                         fail_message))

    if commit and hasattr(instance, 'save'):
        # see BaseDocumentForm._post_clean for an explanation
        if hasattr(form, '_delete_before_save'):
            fields = instance._fields
            new_fields = dict([(n, f) for n, f in fields.iteritems()
                                if not n in form._delete_before_save])
            if hasattr(instance, '_changed_fields'):
                for field in form._delete_before_save:
                    instance._changed_fields.remove(field)
            instance._fields = new_fields
            instance.save()
            instance._fields = fields
        else:
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
    for f in instance._fields.itervalues():
        if fields and not f.name in fields:
            continue
        if exclude and f.name in exclude:
            continue
        else:
            data[f.name] = getattr(instance, f.name)
    return data


def fields_for_document(document, fields=None, exclude=None, widgets=None,
                        formfield_callback=None,
                        field_generator=MongoFormFieldGenerator):
    """
    Returns a ``SortedDict`` containing form fields for the given model.

    ``fields`` is an optional list of field names. If provided, only the named
    fields will be included in the returned fields.

    ``exclude`` is an optional list of field names. If provided, the named
    fields will be excluded from the returned fields, even if they are listed
    in the ``fields`` argument.
    """
    field_list = []
    ignored = []
    if isinstance(field_generator, type):
        field_generator = field_generator()

    sorted_fields = sorted(document._fields.values(),
                           key=lambda field: field.creation_counter)

    for f in sorted_fields:
        if isinstance(f, ObjectIdField):
            continue
        if isinstance(f, ListField) and not (f.field.choices or isinstance(f.field, ReferenceField)):
            continue
        if fields is not None and not f.name in fields:
            continue
        if exclude and f.name in exclude:
            continue
        if widgets and f.name in widgets:
            kwargs = {'widget': widgets[f.name]}
        else:
            kwargs = {}

        if formfield_callback is None:
            form_field = field_generator.generate(f, **kwargs)
        elif not callable(formfield_callback):
            raise TypeError('formfield_callback must be a function or callable')
        else:
            form_field = formfield_callback(f, **kwargs)

        if form_field:
            field_list.append((f.name, form_field))
        else:
            ignored.append(f.name)

    field_dict = SortedDict(field_list)
    if fields:
        field_dict = SortedDict(
            [(f, field_dict.get(f)) for f in fields
                if ((not exclude) or (exclude and f not in exclude)) and (f not in ignored)]
        )
    return field_dict


class DocumentFormOptions(object):
    def __init__(self, options=None):
        self.document = getattr(options, 'document', None)
        self.model = self.document
        # set up the document meta wrapper if document meta is a dict
        if self.document is not None:
            if not hasattr(self.document, '_meta'):
                self.document._meta = {}
            if isinstance(self.document._meta, dict):
                self.document._meta = DocumentMetaWrapper(self.document)
                self.document._admin_opts = self.document._meta
        self.fields = getattr(options, 'fields', None)
        self.exclude = getattr(options, 'exclude', None)
        self.widgets = getattr(options, 'widgets', None)
        self.embedded_field = getattr(options, 'embedded_field_name', None)
        self.formfield_generator = getattr(options, 'formfield_generator', MongoFormFieldGenerator)


class DocumentFormMetaclass(type):
    def __new__(cls, name, bases, attrs):
        formfield_callback = attrs.pop('formfield_callback', None)
        try:
            parents = [b for b in bases if issubclass(b, DocumentForm) or issubclass(b, EmbeddedDocumentForm)]
        except NameError:
            # We are defining DocumentForm itself.
            parents = None
        declared_fields = get_declared_fields(bases, attrs, False)
        new_class = super(DocumentFormMetaclass, cls).__new__(cls, name, bases, attrs)
        if not parents:
            return new_class

        if 'media' not in attrs:
            new_class.media = media_property(new_class)

        opts = new_class._meta = DocumentFormOptions(getattr(new_class, 'Meta', None))
        if opts.document:
            formfield_generator = getattr(opts, 'formfield_generator', MongoFormFieldGenerator)

            # If a model is defined, extract form fields from it.
            fields = fields_for_document(opts.document, opts.fields,
                            opts.exclude, opts.widgets, formfield_callback, formfield_generator)
            # make sure opts.fields doesn't specify an invalid field
            none_document_fields = [k for k, v in fields.iteritems() if not v]
            missing_fields = set(none_document_fields) - \
                             set(declared_fields.keys())
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
                raise ValueError('DocumentForm has no document class specified.')
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
        super(BaseDocumentForm, self).__init__(data, files, auto_id, prefix, object_data,
                                            error_class, label_suffix, empty_permitted)

    def _update_errors(self, message_dict):
        for k, v in message_dict.items():
            if k != NON_FIELD_ERRORS:
                self._errors.setdefault(k, self.error_class()).extend(v)
                # Remove the data from the cleaned_data dict since it was invalid
                if k in self.cleaned_data:
                    del self.cleaned_data[k]
        if NON_FIELD_ERRORS in message_dict:
            messages = message_dict[NON_FIELD_ERRORS]
            self._errors.setdefault(NON_FIELD_ERRORS, self.error_class()).extend(messages)

    def _get_validation_exclusions(self):
        """
        For backwards-compatibility, several types of fields need to be
        excluded from model validation. See the following tickets for
        details: #12507, #12521, #12553
        """
        exclude = []
        # Build up a list of fields that should be excluded from model field
        # validation and unique checks.
        for f in self.instance._fields.itervalues():
            field = f.name
            # Exclude fields that aren't on the form. The developer may be
            # adding these values to the model after form validation.
            if field not in self.fields:
                exclude.append(f.name)

            # Don't perform model validation on fields that were defined
            # manually on the form and excluded via the ModelForm's Meta
            # class. See #12901.
            elif self._meta.fields and field not in self._meta.fields:
                exclude.append(f.name)
            elif self._meta.exclude and field in self._meta.exclude:
                exclude.append(f.name)

            # Exclude fields that failed form validation. There's no need for
            # the model fields to validate them as well.
            elif field in self._errors.keys():
                exclude.append(f.name)

            # Exclude empty fields that are not required by the form, if the
            # underlying model field is required. This keeps the model field
            # from raising a required error. Note: don't exclude the field from
            # validaton if the model field allows blanks. If it does, the blank
            # value may be included in a unique check, so cannot be excluded
            # from validation.
            else:
                field_value = self.cleaned_data.get(field, None)
                if not f.required and field_value in EMPTY_VALUES:
                    exclude.append(f.name)
        return exclude

    def clean(self):
        self._validate_unique = True
        return self.cleaned_data

    def validate_unique(self):
        """
        Validates unique constrains on the document.
        unique_with is not checked at the moment.
        """
        errors = []
        exclude = self._get_validation_exclusions()
        for f in self.instance._fields.itervalues():
            if f.unique and f.name not in exclude:
                filter_kwargs = {
                    f.name: getattr(self.instance, f.name)
                }
                qs = self.instance.__class__.objects().filter(**filter_kwargs)
                # Exclude the current object from the query if we are editing an
                # instance (as opposed to creating a new one)
                if self.instance.pk is not None:
                    qs = qs.filter(pk__ne=self.instance.pk)
                if len(qs) > 0:
                    message = _("%(model_name)s with this %(field_label)s already exists.") % {
                                'model_name': unicode(capfirst(self.instance._meta.verbose_name)),
                                'field_label': unicode(pretty_name(f.name))
                    }
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

        if self.errors:
            raise ValueError("The %s could not be %s because the data didn't"
                             " validate." % (self.instance.__class__.__name__, fail_message))

        if self.instance._created:
            self.instance = construct_instance(self, self.instance, self.fields, self._meta.exclude)

            # Validate uniqueness if needed.
            if self._validate_unique:
                self.validate_unique()

            if commit:
                self.instance.save()
        else:
            update = {}
            for name, data in self.cleaned_data.iteritems():

                try:
                    if isinstance(data, datetime.datetime):
                        data = data.replace(tzinfo=None)
                    if getattr(self.instance, name) != data:
                        update['set__' + name] = data
                        setattr(self.instance, name, data)
                except AttributeError:
                    raise Exception('Model %s has not attr %s but form %s has' \
                                    % (type(self.instance),
                                      name,
                                      type(self)))

            # Validate uniqueness if needed.
            if self._validate_unique:
                self.validate_unique()

            if commit and update:
                self.instance.update(**update)
        return self.instance
    save.alters_data = True


class DocumentForm(BaseDocumentForm):
    __metaclass__ = DocumentFormMetaclass


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


class EmbeddedDocumentForm(BaseDocumentForm):
    __metaclass__ = DocumentFormMetaclass

    def __init__(self, parent_document, *args, **kwargs):
        super(EmbeddedDocumentForm, self).__init__(*args, **kwargs)
        self.parent_document = parent_document
        if self._meta.embedded_field is not None and \
                not hasattr(self.parent_document, self._meta.embedded_field):
            raise FieldError("Parent document must have field %s" % self._meta.embedded_field)

    def save(self, commit=True):
        if self.errors:
            raise ValueError("The %s could not be saved because the data didn't"
                         " validate." % self.instance.__class__.__name__)

        if commit:
            instance = construct_instance(self, self.instance, self.fields, self._meta.exclude)
            l = getattr(self.parent_document, self._meta.embedded_field)
            l.append(instance)
            setattr(self.parent_document, self._meta.embedded_field, l)
            self.parent_document.save()

        return self.instance


class BaseDocumentFormSet(BaseFormSet):
    """
    A ``FormSet`` for editing a queryset and/or adding new objects to it.
    """

    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 queryset=None, **kwargs):
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
        return self._queryset

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

            if form in self.deleted_forms:
                try:
                    obj.delete()
                except AttributeError:
                    # if it has no delete method it is an
                    # embedded object. We just don't add to the list
                    # and it's gone. Cook huh?
                    continue
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
        return _("Please correct the duplicate data for %(field_name)s "
            "which must be unique for the %(lookup)s in %(date_field)s.") % {
            'field_name': date_check[2],
            'date_field': date_check[3],
            'lookup': unicode(date_check[1]),
        }

    def get_form_error(self):
        return _("Please correct the duplicate values below.")


def documentformset_factory(document, form=DocumentForm, formfield_callback=None,
                         formset=BaseDocumentFormSet,
                         extra=1, can_delete=False, can_order=False,
                         max_num=None, fields=None, exclude=None):
    """
    Returns a FormSet class for the given Django model class.
    """
    form = documentform_factory(document, form=form, fields=fields, exclude=exclude,
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

        super(BaseInlineDocumentFormSet, self).__init__(data, files, prefix=prefix, queryset=queryset, **kwargs)

    def initial_form_count(self):
        if self.save_as_new:
            return 0
        return super(BaseInlineDocumentFormSet, self).initial_form_count()

    #@classmethod
    def get_default_prefix(cls):
        return cls.model.__name__.lower()
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
        unique_check = [field for field in unique_check if field != self.fk.name]
        return super(BaseInlineDocumentFormSet, self).get_unique_error_message(unique_check)


def inlineformset_factory(document, form=DocumentForm,
                          formset=BaseInlineDocumentFormSet,
                          fields=None, exclude=None,
                          extra=1, can_order=False, can_delete=True, max_num=None,
                          formfield_callback=None):
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


class EmbeddedDocumentFormSet(BaseInlineDocumentFormSet):
    def __init__(self, parent_document=None, data=None, files=None, instance=None,
                 save_as_new=False, prefix=None, queryset=[], **kwargs):
        self.parent_document = parent_document
        super(EmbeddedDocumentFormSet, self).__init__(data, files, instance, save_as_new, prefix, queryset, **kwargs)

    def _construct_form(self, i, **kwargs):
        defaults = {'parent_document': self.parent_document}
        defaults.update(kwargs)
        form = super(BaseDocumentFormSet, self)._construct_form(i, **defaults)
        return form


def embeddedformset_factory(document, parent_document, form=EmbeddedDocumentForm,
                          formset=EmbeddedDocumentFormSet,
                          fields=None, exclude=None,
                          extra=1, can_order=False, can_delete=True, max_num=None,
                          formfield_callback=None):
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
    FormSet = inlineformset_factory(document, **kwargs)
    FormSet.parent_document = parent_document
    return FormSet
########NEW FILE########
__FILENAME__ = document_options
import sys

from django.db.models.fields import FieldDoesNotExist
from django.db.models.options import get_verbose_name
from django.utils.text import capfirst

from mongoengine.fields import ReferenceField


class PkWrapper(object):
    """Used to wrap the Primary Key so it can mimic Django's expectations
    """

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


class DocumentMetaWrapper(object):
    """
    Used to store mongoengine's _meta dict to make the document admin
    as compatible as possible to django's meta class on models.
    """
    _pk = None
    pk_name = None
    app_label = None
    module_name = None
    verbose_name = None
    has_auto_field = False
    object_name = None
    proxy = []
    parents = {}
    many_to_many = []
    _field_cache = None
    document = None
    _meta = None

    def __init__(self, document):
        self.document = document
        self._meta = document._meta or {}
        self.concrete_model = document

        try:
            self.object_name = self.document.__name__
        except AttributeError:
            self.object_name = self.document.__class__.__name__

        self.module_name = self.object_name.lower()
        self.app_label = self.get_app_label()
        self.verbose_name = self.get_verbose_name()

        # EmbeddedDocuments don't have an id field.
        try:
            self.pk_name = self._meta['id_field']
            self._init_pk()
        except KeyError:
            pass

    def get_app_label(self):
        model_module = sys.modules[self.document.__module__]
        return model_module.__name__.split('.')[-2]

    def get_verbose_name(self):
        """
        Returns the verbose name of the document.

        Checks the original meta dict first. If it is not found
        then generates a verbose name from from the object name.
        """
        try:
            return capfirst(get_verbose_name(self._meta['verbose_name']))
        except KeyError:
            return capfirst(get_verbose_name(self.object_name))

    @property
    def verbose_name_raw(self):
        return self.verbose_name

    @property
    def verbose_name_plural(self):
        return "%ss" % self.verbose_name

    @property
    def pk(self):
        if not hasattr(self._pk, 'attname'):
            self._init_pk()
        return self._pk

    def _init_pk(self):
        """
        Adds a wrapper around the documents pk field. The wrapper object gets the attributes
        django expects on the pk field, like name and attname.

        The function also adds a _get_pk_val method to the document.
        """
        if self.id_field is None:
            return

        try:
            pk_field = getattr(self.document, self.id_field)
            self._pk = PkWrapper(pk_field)
            self._pk.name = self.id_field
            self._pk.attname = self.id_field
            self._pk_name = self.id_field

            self.document._pk_val = getattr(self.document, self.pk_name)
            # avoid circular import
            from .utils import patch_document
            def _get_pk_val(self):
                return self._pk_val
            patch_document(_get_pk_val, self.document)
        except AttributeError:
            return

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

        Uses a cache internally, so after the first access, this is very fast.
        """
        try:
            try:
                return self._field_cache[name]
            except TypeError:
                self._init_field_cache()
                return self._field_cache[name]
        except KeyError:
            raise FieldDoesNotExist('%s has no field named %r'
                    % (self.object_name, name))

    def _init_field_cache(self):
        if self._field_cache is None:
            self._field_cache = {}

        for f in self.document._fields.itervalues():
            if isinstance(f, ReferenceField):
                document = f.document_type
                document._meta = DocumentMetaWrapper(document)
                document._admin_opts = document._meta
                self._field_cache[document._meta.module_name] = (f, document, False, False)
            else:
                self._field_cache[f.name] = (f, None, True, False)

        return self._field_cache

    def get_field(self, name, many_to_many=True):
        """
        Returns the requested field by name. Raises FieldDoesNotExist on error.
        """
        return self.get_field_by_name(name)[0]

    def __getattr__(self, name):
        try:
            return self._meta[name]
        except KeyError:
            raise AttributeError

    def __setattr__(self, name, value):
        if not hasattr(self, name):
            self._meta[name] = value
        else:
            super(DocumentMetaWrapper, self).__setattr__(name, value)

    def __getitem__(self, key):
        return self._meta[key]

    def __contains__(self, key):
        return key in self._meta

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
        return self._meta.iteritems()

########NEW FILE########
__FILENAME__ = fields
from django import forms
from django.core.validators import EMPTY_VALUES
from django.core.exceptions import ValidationError
from django.utils.encoding import smart_unicode, force_unicode
from django.utils.translation import ugettext_lazy as _

from django_mongoengine.forms.widgets import Dictionary

from bson.objectid import ObjectId
from bson.errors import InvalidId


class MongoChoiceIterator(object):
    def __init__(self, field):
        self.field = field
        self.queryset = field.queryset

    def __iter__(self):
        if self.field.empty_label is not None:
            yield (u"", self.field.empty_label)

        for obj in self.queryset.all():
            yield self.choice(obj)

    def __len__(self):
        return len(self.queryset)

    def choice(self, obj):
        return (self.field.prepare_value(obj), self.field.label_from_instance(obj))


class MongoCharField(forms.CharField):
    def to_python(self, value):
        if value in EMPTY_VALUES:
            return None
        return smart_unicode(value)


class ReferenceField(forms.ChoiceField):
    """
    Reference field for mongo forms. Inspired by `django.forms.models.ModelChoiceField`.
    """
    def __init__(self, queryset, empty_label=u"---------",
                 *aargs, **kwaargs):

        forms.Field.__init__(self, *aargs, **kwaargs)
        self.queryset = queryset
        self.empty_label = empty_label

    def _get_queryset(self):
        return self._queryset

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
        generate the labels for the choices presented by this object. Subclasses
        can override this method to customize the display of the choices.
        """
        return smart_unicode(obj)

    def clean(self, value):
        if value in EMPTY_VALUES and not self.required:
            return None

        try:
            oid = ObjectId(value)
            oid = super(ReferenceField, self).clean(oid)

            queryset = self.queryset.clone()
            obj = queryset.get(id=oid)
        except (TypeError, InvalidId, self.queryset._document.DoesNotExist):
            raise forms.ValidationError(self.error_messages['invalid_choice'] % {'value': value})
        return obj

    # Fix for Django 1.4
    # TODO: Test with older django versions
    # from django-mongotools by wpjunior
    # https://github.com/wpjunior/django-mongotools/
    def __deepcopy__(self, memo):
        result = super(forms.ChoiceField, self).__deepcopy__(memo)
        result.queryset = result.queryset
        result.empty_label = result.empty_label
        return result


class DocumentMultipleChoiceField(ReferenceField):
    """A MultipleChoiceField whose choices are a model QuerySet."""
    widget = forms.SelectMultiple
    hidden_widget = forms.MultipleHiddenInput
    default_error_messages = {
        'list': _(u'Enter a list of values.'),
        'invalid_choice': _(u'Select a valid choice. %s is not one of the'
                            u' available choices.'),
        'invalid_pk_value': _(u'"%s" is not a valid value for a primary key.')
    }

    def __init__(self, queryset, *args, **kwargs):
        super(DocumentMultipleChoiceField, self).__init__(queryset, empty_label=None, *args, **kwargs)

    def clean(self, value):
        if self.required and not value:
            raise forms.ValidationError(self.error_messages['required'])
        elif not self.required and not value:
            return []
        if not isinstance(value, (list, tuple)):
            raise forms.ValidationError(self.error_messages['list'])
        key = 'pk'

        filter_ids = []
        for pk in value:
            try:
                oid = ObjectId(pk)
                filter_ids.append(oid)
            except InvalidId:
                raise forms.ValidationError(self.error_messages['invalid_pk_value'] % pk)
        qs = self.queryset.clone()
        qs = qs.filter(**{'%s__in' % key: filter_ids})
        pks = set([force_unicode(getattr(o, key)) for o in qs])
        for val in value:
            if force_unicode(val) not in pks:
                raise forms.ValidationError(self.error_messages['invalid_choice'] % val)
        # Since this overrides the inherited ModelChoiceField.clean
        # we run custom validators here
        self.run_validators(value)
        return list(qs)

    def prepare_value(self, value):
        if hasattr(value, '__iter__') and not hasattr(value, '_meta'):
            return [super(DocumentMultipleChoiceField, self).prepare_value(v) for v in value]
        return super(DocumentMultipleChoiceField, self).prepare_value(value)


class DictField(forms.Field):
    """
    DictField for mongo forms
    """

    error_messages = {
        'length': _(u'Ensure the keys length is less than or equal to %s.'),
        'invalid_key': _(u'Ensure the keys are not : %s.'),
        'illegal': _(u'Ensure the keys does not contain any illegal character : %s.'),
        'depth': _(u'Ensure the dictionary depth is less than or equal to %s.')
    }

    #Mongo reserved keywords
    invalid_keys = ['err', 'errmsg']
    #Mongo prohibit . in keys
    illegal_characters = ['.']
    #limit key length for efficiency
    key_limit = 200
    #limit depth for dictionaries
    max_depth = None

    def __init__(self, max_depth=None, flags=None, sub_attrs=None, attrs=None, *args, **kwargs):
        if 'error_messages' in kwargs.keys():
            kwargs['error_messages'].update(self.error_messages)
        else:
            kwargs['error_messages'] = self.error_messages

        self.max_depth = (max_depth if max_depth >= 0 else None)

        if 'widget' not in kwargs.keys():
            schema = None
            #Here it needs to be clearer, because this is only useful when creating an object,
            #if no default value is provided, default is callable
            if 'initial' in kwargs and not callable(kwargs['initial']):
                if isinstance(kwargs['initial'], dict):
                    schema = kwargs['initial']

            #here if other parameters are passed, like max_depth and flags, then we hand them to the dict
            kwargs['widget'] = Dictionary(max_depth=max_depth, flags=flags, schema=schema, sub_attrs=sub_attrs)

        super(DictField, self).__init__(*args, **kwargs)

    def prepare_value(self, value):
        return value

    def to_python(self, value):
        value = self.get_dict(value)
        return value

    def clean(self, value):
        self.max_depth = self.widget.max_depth
        value = self.to_python(value)
        self.validate(value)
        return value

    def get_dict(self, a_list):
        """
        A function that return a dictionary from a list of lists, with any depth
        """
        d = {}
        for k in a_list:
            if (isinstance(k, list)):
                if isinstance(k[1], list) and k[0]:
                    d.update({k[0]: self.get_dict(k[1])})
                elif k[0]:
                    d.update({k[0]: k[1]})
        return d

    def validate(self, value, depth=0):
        #we should not use the super.validate method
        if self.max_depth is not None and depth > self.max_depth:
            raise ValidationError(self.error_messages['depth'] % self.max_depth)
        for k, v in value.items():
            self.run_validators(k)
            if k in self.invalid_keys:
                raise ValidationError(self.error_messages['invalid_key'] % self.invalid_keys)
            if len(k) > self.key_limit:
                raise ValidationError(self.error_messages['length'] % self.key_limit)
            for u in self.illegal_characters:
                if u in k:
                    raise ValidationError(self.error_messages['illegal'] % self.illegal_characters)
            if isinstance(v, dict):
                self.validate(v, depth + 1)

########NEW FILE########
__FILENAME__ = field_generator
from django import forms
from django.core.validators import EMPTY_VALUES, RegexValidator
from django.utils.encoding import smart_unicode
from django.db.models.options import get_verbose_name
from django.utils.text import capfirst

from mongoengine import ReferenceField as MongoReferenceField

from fields import MongoCharField, ReferenceField, DocumentMultipleChoiceField, DictField

BLANK_CHOICE_DASH = [("", "---------")]


class MongoFormFieldGenerator(object):
    """This class generates Django form-fields for mongoengine-fields."""

    def generate(self, field, charfield_default=False, **kwargs):
        """Tries to lookup a matching formfield generator (lowercase
        field-classname) and raises a NotImplementedError of no generator
        can be found.

        :param default: Default to a CharField?
        """
        field_name = field.__class__.__name__.lower()
        if hasattr(self, 'generate_%s' % field_name):
            return getattr(self, 'generate_%s' % field_name)(field, **kwargs)

        for cls in field.__class__.__bases__:
            cls_name = cls.__name__.lower()
            if hasattr(self, 'generate_%s' % cls_name):
                return getattr(self, 'generate_%s' % cls_name)(field, **kwargs)

        if default:
            # Default to a normal CharField
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
            return field.verbose_name
        return capfirst(get_verbose_name(field.name))

    def get_field_help_text(self, field):
        if field.help_text:
            return field.help_text.capitalize()

    def generate_stringfield(self, field, **kwargs):
        form_class = MongoCharField

        defaults = {'label': self.get_field_label(field),
                    'initial': field.default,
                    'required': field.required,
                    'help_text': self.get_field_help_text(field)}

        if field.max_length and not field.choices:
            defaults['max_length'] = field.max_length

        if field.max_length is None and not field.choices:
            defaults['widget'] = forms.Textarea

        if field.regex:
            defaults['regex'] = field.regex
        elif field.choices:
            form_class = forms.TypedChoiceField
            defaults['choices'] = self.get_field_choices(field)
            defaults['coerce'] = self.string_field

            if not field.required:
                defaults['empty_value'] = None

        defaults.update(kwargs)
        return form_class(**defaults)

    def generate_emailfield(self, field, **kwargs):
        defaults = {
            'required': field.required,
            'min_length': field.min_length,
            'max_length': field.max_length,
            'initial': field.default,
            'label': self.get_field_label(field),
            'help_text': self.get_field_help_text(field)
        }

        defaults.update(kwargs)
        return forms.EmailField(**defaults)

    def generate_urlfield(self, field, **kwargs):
        defaults = {
            'required': field.required,
            'min_length': field.min_length,
            'max_length': field.max_length,
            'initial': field.default,
            'label': self.get_field_label(field),
            'help_text':  self.get_field_help_text(field)
        }

        defaults.update(kwargs)
        return forms.URLField(**defaults)

    def generate_intfield(self, field, **kwargs):
        if field.choices:
            defaults = {
                'coerce': self.integer_field,
                'empty_value': None,
                'required': field.required,
                'initial': field.default,
                'label': self.get_field_label(field),
                'choices': self.get_field_choices(field),
                'help_text': self.get_field_help_text(field)
            }

            defaults.update(kwargs)
            return forms.TypedChoiceField(**defaults)
        else:
            defaults = {
                'required': field.required,
                'min_value': field.min_value,
                'max_value': field.max_value,
                'initial': field.default,
                'label': self.get_field_label(field),
                'help_text': self.get_field_help_text(field)
            }

            defaults.update(kwargs)
            return forms.IntegerField(**defaults)

    def generate_floatfield(self, field, **kwargs):

        form_class = forms.FloatField

        defaults = {'label': self.get_field_label(field),
                    'initial': field.default,
                    'required': field.required,
                    'min_value': field.min_value,
                    'max_value': field.max_value,
                    'help_text': self.get_field_help_text(field)}

        defaults.update(kwargs)
        return form_class(**defaults)

    def generate_decimalfield(self, field, **kwargs):
        form_class = forms.DecimalField
        defaults = {'label': self.get_field_label(field),
                    'initial': field.default,
                    'required': field.required,
                    'min_value': field.min_value,
                    'max_value': field.max_value,
                    'help_text': self.get_field_help_text(field)}

        defaults.update(kwargs)
        return form_class(**defaults)

    def generate_booleanfield(self, field, **kwargs):
        if field.choices:
            defaults = {
                'coerce': self.boolean_field,
                'empty_value': None,
                'required': field.required,
                'initial': field.default,
                'label': self.get_field_label(field),
                'choices': self.get_field_choices(field),
                'help_text': self.get_field_help_text(field)
            }

            defaults.update(kwargs)
            return forms.TypedChoiceField(**defaults)
        else:
            defaults = {
                'required': field.required,
                'initial': field.default,
                'label': self.get_field_label(field),
                'help_text': self.get_field_help_text(field)
                }

            defaults.update(kwargs)
            return forms.BooleanField(**defaults)

    def generate_datetimefield(self, field, **kwargs):
        defaults = {
            'required': field.required,
            'initial': field.default,
            'label': self.get_field_label(field),
        }

        defaults.update(kwargs)
        return forms.DateTimeField(**defaults)

    def generate_referencefield(self, field, **kwargs):
        defaults = {
            'label': self.get_field_label(field),
            'help_text': self.get_field_help_text(field),
            'required': field.required
        }

        defaults.update(kwargs)
        return ReferenceField(field.document_type.objects, **defaults)

    def generate_listfield(self, field, **kwargs):
        if field.field.choices:
            defaults = {
                'choices': field.field.choices,
                'required': field.required,
                'label': self.get_field_label(field),
                'help_text': self.get_field_help_text(field),
                'widget': forms.CheckboxSelectMultiple
            }

            defaults.update(kwargs)
            return forms.MultipleChoiceField(**defaults)
        elif isinstance(field.field, MongoReferenceField):
            defaults = {
                'label': self.get_field_label(field),
                'help_text': self.get_field_help_text(field),
                'required': field.required
            }

            defaults.update(kwargs)
            f = DocumentMultipleChoiceField(field.field.document_type.objects, **defaults)
            return f

    def generate_filefield(self, field, **kwargs):
        return forms.FileField(**kwargs)

    def generate_imagefield(self, field, **kwargs):
        return forms.ImageField(**kwargs)

    def generate_dictfield(self, field, **kwargs):
        #remove Mongo reserved words
        validate = [RegexValidator(regex='^[^$_]', message=u'Ensure the keys do not begin with : ["$","_"].', code='invalid_start')]
        defaults = {
            'required': field.required,
            'initial': field.default,
            'label': self.get_field_label(field),
            'help_text': self.get_field_help_text(field),
            'validators': validate,
        }
        return DictField(**defaults)


class MongoDefaultFormFieldGenerator(MongoFormFieldGenerator):
    """This class generates Django form-fields for mongoengine-fields."""

    def generate(self, field, **kwargs):
        """Tries to lookup a matching formfield generator (lowercase
        field-classname) and raises a NotImplementedError of no generator
        can be found.
        """
        try:
            return super(MongoDefaultFormFieldGenerator, self).generate(
                        field, **kwargs)
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

########NEW FILE########
__FILENAME__ = utils
import new

from document_options import DocumentMetaWrapper

def patch_document(function, instance):
    setattr(instance, function.__name__, new.instancemethod(function, instance, instance.__class__))

def init_document_options(document):
    if not hasattr(document, '_meta') or not isinstance(document._meta, DocumentMetaWrapper):
        document._admin_opts = DocumentMetaWrapper(document)
    if not isinstance(document._admin_opts, DocumentMetaWrapper):
        document._admin_opts = document._meta
    return document

def get_document_options(document):
    return DocumentMetaWrapper(document)

########NEW FILE########
__FILENAME__ = widgets
import re

from django.forms.widgets import TextInput, HiddenInput, MultiWidget, Media
from django.utils.safestring import mark_safe

from django_mongoengine.utils import OrderedDict

# The list of JavaScript files to insert to render any Dictionary widget
MEDIAS = ('jquery-1.8.0.min.js', 'dict.js', 'helper.js')
ADD_FIELD_VERBOSE = 'Add Field'
ADD_DICT_VERBOSE = ' - Add subdictionary'


class Dictionary(MultiWidget):
    """
    A widget representing a dictionary field
    """

    def __init__(self, schema=None, no_schema=1, max_depth=None,
                 flags=None, sub_attrs=None, attrs=None, verbose_dict=None,
                 verbose_field=None):
        """
        :param schema: A dictionary representing the future schema of
                       the Dictionary widget. It is responsible for the
                       creation of subwidgets.
        :param no_schema: An integer that can take 3 values : 0,1,2.
                          0 means that no schema was passed.
                          1 means that the schema passed was the default
                          one. This is the default value.
                          2 means that the schema passed was given
                          by a parent widget, and that it actually
                          represent data for rendering.
                          3 means that the schema was rebuilt after
                          retrieving form data.
        :param max_depth: An integer representing the max depth of
                          sub-dicts. If passed, the system will
                          prevent to save dictionaries with depths
                          superior to this parameter.
        :param flags:    A list of flags. Available values :
                         - 'FORCE_SCHEMA' : would force dictionaries
                            to keep a certain schema. Only Pair fields
                            could be added.
        :param sub_attrs:   A dictionary that contains the classes
                            for the keys (key.class) and the values
                            (value.class) of each pair
        :param verbose_field:   verbose for 'Add field'
        :param verbose_dict:    verbose for 'Add dict'
        """
        self.verbose_field = verbose_field or ADD_FIELD_VERBOSE
        self.verbose_dict = verbose_dict or ADD_DICT_VERBOSE
        self.no_schema = no_schema
        self.max_depth = (max_depth if max_depth >= 0 else None)
        self.flags = flags or []
        self.sub_attrs = sub_attrs or {}

        if flags is not None and 'FORCE_SCHEMA' in flags:
            self.pair = StaticPair
            self.subdict = StaticSubDictionary
        else:
            self.pair = Pair
            self.subdict = SubDictionary

        widget_object = []
        if isinstance(schema, dict) and self.no_schema > 0:
            for key in schema:
                if isinstance(schema[key], dict):
                    widget_object.append(self.subdict(key_value=key, schema=schema[key],
                                         max_depth=max_depth, sub_attrs=self.sub_attrs,
                                         attrs=attrs, verbose_field=self.verbose_field,
                                         verbose_dict=self.verbose_dict))
                else:
                    widget_object.append(self.pair(key_value=key, sub_attrs=self.sub_attrs, attrs=attrs))
        else:
            widget_object.append(self.pair(sub_attrs=self.sub_attrs, sattrs=attrs))

        super(Dictionary, self).__init__(widget_object, attrs)

    def decompress(self, value):
        if value and isinstance(value, dict):
            value = self.dict_sort(value)
            value = value.items()

            # If the schema in place wasn't passed by a parent widget
            # we need to rebuild it
            if self.no_schema < 2:
                self.update_widgets(value, erase=True)
            return value
        else:
            return []

    def render(self, name, value, attrs=None):
        if not isinstance(value, list):
            value = self.decompress(value)
        if self.is_localized:
            for widget in self.widgets:
                widget.is_localized = self.is_localized
        output = []
        final_attrs = self.build_attrs(attrs)
        id_ = final_attrs.get('id')
        for i, widget in enumerate(self.widgets):
            try:
                widget_value = value[i]
            except IndexError:
                widget_value = None
            suffix = widget.suffix
            if id_:
                final_attrs = dict(final_attrs, id='%s_%s_%s' %
                                   (id_, i, suffix))
            output.append(widget.render('%s_%s_%s' % (name, i, suffix),
                                        widget_value,
                                        final_attrs))
        return mark_safe(self.format_output(name, output))

    def value_from_datadict(self, data, files, name):
        """
        Process is:
            - erase every widget ;
            - create the new ones from the data dictionary

        It would take into account every modification on the structure, and
        make form repopulation automatic
        """
        data_keys = data.keys()
        self.widgets = []
        html_indexes = []
        prefix = 'st' if self.flags is not None and 'FORCE_SCHEMA' in self.flags else ''
        for data_key in data_keys:
            match = re.match(name + '_(\d+)_%spair_0' % prefix, data_key)
            if match is not None:
                self.widgets.append(self.pair(sub_attrs=self.sub_attrs, attrs=self.attrs))
                html_indexes.append(match.group(1))
            else:
                match = re.match(name + '_(\d+)_%ssubdict_0' % prefix, data_key)
                if match is not None:
                        self.widgets.append(
                            self.subdict(sub_attrs=self.sub_attrs,
                                         no_schema=0,
                                         max_depth=self.max_depth,
                                         flags=self.flags,
                                         attrs=self.attrs)
                        )
                        html_indexes.append(match.group(1))

        return [widget.value_from_datadict(
                    data, files,
                    '%s_%s_%s' % (name, html_indexes[i], widget.suffix))
                    for i, widget in enumerate(self.widgets)]

    def format_output(self, name, rendered_widgets):
        class_depth = ''
        if self.max_depth is not None:
            class_depth = 'depth_%s' % self.max_depth

        params = {'id': "id_%s" % self.id_for_label(name),
         'class_depth': class_depth,
         'widgets': ''.join(rendered_widgets),
         'add_id': 'add_id_%s' % self.id_for_label(name),
         'add_sub_id': 'add_sub_id_%s' % self.id_for_label(name),
         'add_field': ADD_FIELD_VERBOSE,
         'add_dict': ADD_DICT_VERBOSE
        }

        if 'FORCE_SCHEMA' not in self.flags:
            actions = """
<span id="%(add_id)s" class="add_pair_dictionary">%(add_field)s</span>
<span id="%(add_sub_id)s" class="add_sub_dictionary">
    %(add_dict)s
</span>
""" % params
        else:
            actions = ''

        params['actions'] = actions

        return """
<ul id="%(id)s" class="dictionary %(class_depth)s">
  %(widgets)s
</ul>
%(actions)s
""" % params

    def update_widgets(self, keys, erase=False):
        # import pdb
        # pdb.set_trace()
        if erase:
            self.widgets = []
        for k in keys:
            if (isinstance(k[1], dict)):
                self.widgets.append(
                    self.subdict(key_value=k[0], schema=k[1], no_schema=2,
                                 max_depth=self.max_depth, flags=self.flags,
                                 sub_attrs=self.sub_attrs, attrs=self.attrs))
            else:
                self.widgets.append(self.pair(sub_attrs=self.sub_attrs,
                                              key_value=k[1],
                                              attrs=self.attrs))

    def _get_media(self):
        """
        Mimic the MultiWidget '_get_media' method, adding other media
        """
        if 'FORCE_SCHEMA' in self.flags:
            media = Media()
        else:
            media = Media(js=MEDIAS)

        for w in self.widgets:
            media = media + w.media
        return media
    media = property(_get_media)

    def dict_sort(self, d):
        if isinstance(d, dict):
            l = d.items()
            l.sort()
            k = OrderedDict()
            for item in l:
                k[item[0]] = self.dict_sort(item[1])
            return k
        else:
            return d


class Pair(MultiWidget):
    """
    A widget representing a key-value pair in a dictionary
    """

    #default for a pair
    key_type = TextInput
    value_type = TextInput
    suffix = 'pair'

    def __init__(self, sub_attrs, key_value=None, attrs=None, **kwargs):
        widgets = [self.key_type()] if callable(self.key_type) else []
        if self.value_type in [TextInput, HiddenInput]:
            if sub_attrs:
                try:
                    widgets = [self.key_type(attrs=sub_attrs['key']), self.value_type(attrs=sub_attrs['value'])]
                except KeyError:
                    raise(KeyError, "improper synthax for sub_attrs parameter")
            else:
                widgets = [self.key_type(), self.value_type()]
        elif self.value_type == Dictionary:
            if sub_attrs:
                try:
                    widgets = [self.key_type(attrs=sub_attrs['key']), self.value_type(attrs=sub_attrs['value'], **kwargs)]
                except KeyError:
                    raise(KeyError, "improper synthax for sub_attrs parameter")
            else:
                widgets = [self.key_type(), self.value_type(**kwargs)]
        self.sub_attrs = sub_attrs
        #raise error here ?
        self.key_value = key_value if key_value is not None else ''
        super(Pair, self).__init__(widgets, attrs)

    #this method should be overwritten by subclasses
    def decompress(self, value):
        if value is not None:
            return list(value)
        else:
            return ['', '']

    def render(self, name, value, attrs=None):
        if self.is_localized:
            for widget in self.widgets:
                widget.is_localized = self.is_localized
        if not isinstance(value, list):
            value = self.decompress(value)
        output = []
        final_attrs = self.build_attrs(attrs)
        id_ = final_attrs.get('id')
        for i, widget in enumerate(self.widgets):
            try:
                widget_value = value[i]
            except IndexError:
                widget_value = None
            if id_:
                final_attrs = dict(final_attrs, id='%s_%s' % (id_, i))
            output.append(widget.render(name + '_%s' % i, widget_value, final_attrs))
        return mark_safe(self.format_output(output, name))

    def value_from_datadict(self, data, files, name):
        return [widget.value_from_datadict(data, files, name + '_%s' % i) for i, widget in enumerate(self.widgets)]

    def format_output(self, rendered_widgets, name):
        return '<li>' + ' : '.join(rendered_widgets) + '<span class="del_pair" id="del_%s"> - Delete</span></li>\n' % name


class SubDictionary(Pair):
    """
    A widget representing a key-value pair in a dictionary, where value is a dictionary
    """
    key_type = TextInput
    value_type = Dictionary
    suffix = 'subdict'

    def __init__(self, sub_attrs, schema=None, **kwargs):
        if schema is None:
            schema = {'key': 'value'}
        super(SubDictionary, self).__init__(schema=schema,
                                            sub_attrs=sub_attrs, **kwargs)

    def decompress(self, value):
        if value is not None:
            return list(value)
        else:
            return ['', {}]

    def format_output(self, rendered_widgets, name):
        params = {
            "widgets": ' : '.join(rendered_widgets),
            "del_id": "del_%s" % name
        }
        return """
<li> %(widgets)s <span class="del_dict" id="%(del_id)s"> - Delete</span>
</li>""" % params


class StaticPair(Pair):
    """
    A widget representing a key-value pair in a dictionary, where key is just
    text (this is only relevant when FORCE_SCHEMA flag is used)
    """

    key_type = HiddenInput
    value_type = TextInput
    suffix = 'stpair'

    # def __init__(self, key_value, attrs=None):
    #     super(StaticPair, self).__init__(key_value=key_value, attrs=attrs)

    def decompress(self, value):
        value = super(StaticPair, self).decompress(value)
        self.key_value = value[0]
        return value

    def format_output(self, rendered_widgets, name):
        params = {
            "html_class": self.sub_attrs.get('key', {}).get('class', ''),
            "key": self.key_value,
            "widgets": ''.join(rendered_widgets)
        }
        return """
<li><span class="static_key %(html_class)s">%(key)s</span> :  %(widgets)s
</li>""" % params


class StaticSubDictionary(SubDictionary):
    """
    A widget representing a key-value pair in a dictionary, where key is just
    text (this is only relevant when FORCE_SCHEMA flag is used)
    """

    key_type = HiddenInput
    value_type = Dictionary
    suffix = 'stsubdict'

    def decompress(self, value):
        value = super(StaticSubDictionary, self).decompress(value)
        self.key_value = value[0]
        return value

    def format_output(self, rendered_widgets, name):
        params = {
            "html_class": self.sub_attrs.get('key', {}).get('class', ''),
            "key": self.key_value,
            "widgets": ''.join(rendered_widgets)
        }
        return """
<li><span class="static_key %(html_class)s">%(key)s</span> :  %(widgets)s</li>
""" % params

########NEW FILE########
__FILENAME__ = sessions
from datetime import datetime

from django.conf import settings
from django.contrib.sessions.backends.base import SessionBase, CreateError
from django.core.exceptions import SuspiciousOperation
from django.utils.encoding import force_unicode

from mongoengine.document import Document
from mongoengine import fields
from mongoengine.queryset import OperationError
from mongoengine.connection import DEFAULT_CONNECTION_NAME


MONGOENGINE_SESSION_DB_ALIAS = getattr(
    settings, 'MONGOENGINE_SESSION_DB_ALIAS',
    DEFAULT_CONNECTION_NAME)


class MongoSession(Document):
    session_key = fields.StringField(primary_key=True, max_length=40)
    session_data = fields.StringField()
    expire_date = fields.DateTimeField()

    meta = {'collection': 'django_session',
            'db_alias': MONGOENGINE_SESSION_DB_ALIAS,
            'allow_inheritance': False}


class SessionStore(SessionBase):
    """A MongoEngine-based session store for Django.
    """

    def load(self):
        try:
            s = MongoSession.objects(session_key=self.session_key,
                                     expire_date__gt=datetime.now())[0]
            return self.decode(force_unicode(s.session_data))
        except (IndexError, SuspiciousOperation):
            self.create()
            return {}

    def exists(self, session_key):
        return bool(MongoSession.objects(session_key=session_key).first())

    def create(self):
        while True:
            self._session_key = self._get_new_session_key()
            try:
                self.save(must_create=True)
            except CreateError:
                continue
            self.modified = True
            self._session_cache = {}
            return

    def save(self, must_create=False):
        if self.session_key is None:
            self._session_key = self._get_new_session_key()
        s = MongoSession(session_key=self.session_key)
        s.session_data = self.encode(self._get_session(no_load=must_create))
        s.expire_date = self.get_expiry_date()
        try:
            s.save(force_insert=must_create, safe=True)
        except OperationError:
            if must_create:
                raise CreateError
            raise

    def delete(self, session_key=None):
        if session_key is None:
            if self.session_key is None:
                return
            session_key = self.session_key
        MongoSession.objects(session_key=session_key).delete()

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.conf import settings

from django_mongoengine import connect
from django_mongoengine import DEFAULT_CONNECTION_NAME

class MongoTestCase(TestCase):
    """
    TestCase class that clear the collection between the tests.
    """

    def __init__(self, methodName='runtest'):
        db_name = 'test_%s' % settings.MONGODB_DATABASES.get(
                DEFAULT_CONNECTION_NAME).get('name')
        self.conn = connect(db_name)
        super(MongoTestCase, self).__init__(methodName)

    def _post_teardown(self):
        super(MongoTestCase, self)._post_teardown()
        for collection in self.conn.db.collection_names():
            if collection == 'system.indexes':
                continue
            self.db.drop_collection(collection)

    def _fixture_setup(self):
        return

    def _fixture_teardown(self):
        return

########NEW FILE########
__FILENAME__ = module
from __future__ import absolute_import
import mongoengine

import math

from django.http import Http404
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from mongoengine.queryset import MultipleObjectsReturned, DoesNotExist, QuerySet
from mongoengine.base import ValidationError, TopLevelDocumentMetaclass


class MongoEngine(object):

    def __init__(self):

        for key in mongoengine.__all__:
            setattr(self, key, getattr(mongoengine, key))

        self.__all__ = mongoengine.__all__
        self.connection = mongoengine.connection
        self.document = mongoengine.document
        self.fields = mongoengine.fields
        self.queryset = mongoengine.queryset
        self.signals = mongoengine.signals

        self.Document = Document
        self.DynamicDocument = DynamicDocument

        if not hasattr(settings, 'MONGODB_DATABASES'):
            raise ImproperlyConfigured("Missing `MONGODB_DATABASES` in settings.py")

        for alias, conn_settings in settings.MONGODB_DATABASES.items():
            self.connection.register_connection(alias, **conn_settings)


class BaseQuerySet(QuerySet):
    """
    A base queryset with handy extras
    """

    def get_or_404(self, *args, **kwargs):
        try:
            return self.get(*args, **kwargs)
        except (MultipleObjectsReturned, DoesNotExist, ValidationError):
            raise Http404('No %s matches the given query.' %
                            self._document.__name__)

    def first_or_404(self, *args, **kwargs):
        obj = self.first(*args, **kwargs)
        if obj is None:
            raise Http404('No %s matches the given query.' %
                            self._document.__name__)
        return obj

    def get_list_or_404(self, *args, **kwargs):
        obj_list = list(self.filter(*args, **kwargs))
        if not obj_list:
            raise Http404('No %s matches the given query.' %
                            self._document.__name__)
        return obj_list

    def paginate(self, page, per_page, error_out=True):
        return Pagination(self, page, per_page)

    def paginate_field(self, field_name, doc_id, page, per_page,
            total=None):
        item = self.get(id=doc_id)
        count = getattr(item, field_name + "_count", '')
        total = total or count or len(getattr(item, field_name))
        return ListFieldPagination(self, field_name, doc_id, page, per_page,
            total=total)


class Document(mongoengine.Document):
    """Abstract document with extra helpers in the queryset class"""
    meta = {'abstract': True,
                'queryset_class': BaseQuerySet}



class DynamicDocument(mongoengine.DynamicDocument):
    """Abstract Dynamic document with extra helpers in the queryset class"""
    meta = {'abstract': True,
                'queryset_class': BaseQuerySet}


class Pagination(object):

    def __init__(self, iterable, page, per_page):

        if page < 1:
            raise Http404

        self.iterable = iterable
        self.page = page
        self.per_page = per_page
        self.total = len(iterable)

        start_index = (page - 1) * per_page
        end_index = page * per_page

        self.items = iterable[start_index:end_index]
        if isinstance(self.items, QuerySet):
            self.items = self.items.select_related()
        if not self.items and page != 1:
            raise Http404

    @property
    def pages(self):
        """The total number of pages"""
        return int(math.ceil(self.total / float(self.per_page)))

    def prev(self, error_out=False):
        """Returns a :class:`Pagination` object for the previous page."""
        assert self.iterable is not None, 'an object is required ' \
                                       'for this method to work'
        iterable = self.iterable
        if isinstance(iterable, QuerySet):
            iterable._skip = None
            iterable._limit = None
            iterable = iterable.clone()
        return self.__class__(iterable, self.page - 1, self.per_page)

    @property
    def prev_num(self):
        """Number of the previous page."""
        return self.page - 1

    @property
    def has_prev(self):
        """True if a previous page exists"""
        return self.page > 1

    def next(self, error_out=False):
        """Returns a :class:`Pagination` object for the next page."""
        assert self.iterable is not None, 'an object is required ' \
                                       'for this method to work'
        iterable = self.iterable
        if isinstance(iterable, QuerySet):
            iterable._skip = None
            iterable._limit = None
            iterable = iterable.clone()
        return self.__class__(iterable, self.page + 1, self.per_page)

    @property
    def has_next(self):
        """True if a next page exists."""
        return self.page < self.pages

    @property
    def next_num(self):
        """Number of the next page"""
        return self.page + 1

    def iter_pages(self, left_edge=2, left_current=2,
                   right_current=5, right_edge=2):
        """Iterates over the page numbers in the pagination.  The four
        parameters control the thresholds how many numbers should be produced
        from the sides.  Skipped page numbers are represented as `None`.
        This is how you could render such a pagination in the templates:

        .. sourcecode:: html+jinja

            {% macro render_pagination(pagination, endpoint) %}
              <div class=pagination>
              {%- for page in pagination.iter_pages() %}
                {% if page %}
                  {% if page != pagination.page %}
                    <a href="{{ url_for(endpoint, page=page) }}">{{ page }}</a>
                  {% else %}
                    <strong>{{ page }}</strong>
                  {% endif %}
                {% else %}
                  <span class=ellipsis>...</span>
                {% endif %}
              {%- endfor %}
              </div>
            {% endmacro %}
        """
        last = 0
        for num in xrange(1, self.pages + 1):
            if num <= left_edge or \
               (num > self.page - left_current - 1 and
                num < self.page + right_current) or \
               num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num


class ListFieldPagination(Pagination):

    def __init__(self, queryset, field_name, doc_id, page, per_page,
                 total=None):
        """Allows an array within a document to be paginated.

        Queryset must contain the document which has the array we're
        paginating, and doc_id should be it's _id.
        Field name is the name of the array we're paginating.
        Page and per_page work just like in Pagination.
        Total is an argument because it can be computed more efficiently
        elsewhere, but we still use array.length as a fallback.
        """
        if page < 1:
            raise Http404

        self.page = page
        self.per_page = per_page

        self.queryset = queryset
        self.doc_id = doc_id
        self.field_name = field_name

        start_index = (page - 1) * per_page

        field_attrs = {field_name: {"$slice": [start_index, per_page]}}

        self.items = getattr(queryset().fields(**field_attrs
            ).first(), field_name)

        self.total = total or len(self.items)

        if not self.items and page != 1:
            raise Http404

    def prev(self, error_out=False):
        """Returns a :class:`Pagination` object for the previous page."""
        assert self.items is not None, 'a query object is required ' \
                                       'for this method to work'
        return self.__class__(self.queryset, self.doc_id, self.field_name,
            self.page - 1, self.per_page, self.total)

    def next(self, error_out=False):
        """Returns a :class:`Pagination` object for the next page."""
        assert self.iterable is not None, 'a query object is required ' \
                                       'for this method to work'
        return self.__class__(self.queryset, self.doc_id, self.field_name,
            self.page + 1, self.per_page, self.total)

########NEW FILE########
__FILENAME__ = detail
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.utils.encoding import smart_str
from django.utils.translation import ugettext as _
from django.views.generic.base import TemplateResponseMixin, View

from django_mongoengine.forms.utils import get_document_options

from mongoengine.queryset import DoesNotExist


class SingleDocumentMixin(object):
    """
    Provides the ability to retrieve a single object for further manipulation.
    """
    document = None
    queryset = None
    slug_field = 'slug'
    context_object_name = None
    slug_url_kwarg = 'slug'
    pk_url_kwarg = 'pk'

    def get_object(self, queryset=None):
        """
        Returns the object the view is displaying.

        By default this requires `self.queryset` and a `pk` or `slug` argument
        in the URLconf, but subclasses can override this to return any object.
        """
        # Use a custom queryset if provided; this is required for subclasses
        # like DateDetailView
        if queryset is None:
            queryset = self.get_queryset()

        # Next, try looking up by primary key.
        pk = self.kwargs.get(self.pk_url_kwarg, None)
        slug = self.kwargs.get(self.slug_url_kwarg, None)
        if pk is not None:
            queryset = queryset.filter(pk=pk)

        # Next, try looking up by slug.
        elif slug is not None:
            slug_field = self.get_slug_field()
            queryset = queryset.filter(**{slug_field: slug})

        # If none of those are defined, it's an error.
        else:
            raise AttributeError(u"Generic detail view %s must be called with "
                                 u"either an object pk or a slug."
                                 % self.__class__.__name__)

        try:
            obj = queryset.get()
        except DoesNotExist:
            opts = get_document_options(queryset._document)
            raise Http404(_(u"No %(verbose_name)s found matching the query") %
                          {'verbose_name': opts.verbose_name})
        return obj

    def get_queryset(self):
        """
        Get the queryset to look an object up against. May not be called if
        `get_object` is overridden.
        """
        if self.queryset is None:
            if self.document:
                return self.document.objects()
            else:
                raise ImproperlyConfigured(u"%(cls)s is missing a queryset. Define "
                                           u"%(cls)s.document, %(cls)s.queryset, or override "
                                           u"%(cls)s.get_queryset()." % {
                                                'cls': self.__class__.__name__
                                                })
        return self.queryset.clone()

    def get_slug_field(self):
        """
        Get the name of a slug field to be used to look up by slug.
        """
        return self.slug_field

    def get_context_object_name(self, obj):
        """
        Get the name to use for the object.
        """
        if self.context_object_name:
            return self.context_object_name
        elif hasattr(obj, '_meta'):
            opts = get_document_options(obj)
            return smart_str(opts.object_name.lower())
        else:
            return None

    def get_context_data(self, **kwargs):
        context = kwargs
        context_object_name = self.get_context_object_name(self.object)
        if context_object_name:
            context[context_object_name] = self.object
        return context


class BaseDetailView(SingleDocumentMixin, View):
    def get(self, request, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)


class SingleDocumentTemplateResponseMixin(TemplateResponseMixin):
    template_name_field = None
    template_name_suffix = '_detail'

    def get_template_names(self):
        """
        Return a list of template names to be used for the request. Must return
        a list. May not be called if get_template is overridden.
        """
        try:
            names = super(SingleDocumentTemplateResponseMixin, self).get_template_names()
        except ImproperlyConfigured:
            # If template_name isn't specified, it's not a problem --
            # we just start with an empty list.
            names = []

        # If self.template_name_field is set, grab the value of the field
        # of that name from the object; this is the most specific template
        # name, if given.
        if self.object and self.template_name_field:
            name = getattr(self.object, self.template_name_field, None)
            if name:
                names.insert(0, name)

        # The least-specific option is the default <app>/<document>_detail.html;
        # only use this if the object in question is a document.
        if hasattr(self.object, '_meta'):
            doc_cls = self.object.__class__
        elif hasattr(self, 'document') and hasattr(self.document, '_meta'):
            doc_cls = self.document
        else:
            if names:
                return names
            raise ImproperlyConfigured("No object or document class associated with this view")

        # Get any superclasses if needed
        doc_classes = [doc_cls]
        for doc_cls in doc_classes:
            opts = get_document_options(doc_cls)
            name = "%s/%s%s.html" % (
                opts.app_label,
                opts.object_name.lower(),
                self.template_name_suffix
            )
            if name not in names:
                names.append(name)

        # Basic template form: templates/_types.html
        names.append("{}s.html".format(self.template_name_suffix))
        return names


class DetailView(SingleDocumentTemplateResponseMixin, BaseDetailView):
    """
    Render a "detail" view of an object.

    By default this is a document instance looked up from `self.queryset`, but the
    view will support display of *any* object by overriding `self.get_object()`.
    """

########NEW FILE########
__FILENAME__ = edit
from django.core.exceptions import ImproperlyConfigured

from django.contrib import messages
from django.utils.translation import ugettext_lazy as _, ugettext
from django.views.generic.edit import FormMixin, ProcessFormView, DeletionMixin, FormView

from django_mongoengine.forms.documents import documentform_factory
from django_mongoengine.views.detail import (SingleDocumentMixin, DetailView,
                         SingleDocumentTemplateResponseMixin, BaseDetailView)


class DocumentFormMixin(FormMixin, SingleDocumentMixin):
    """
    A mixin that provides a way to show and handle a documentform in a request.
    """

    success_message = None

    def get_form_class(self):
        """
        Returns the form class to use in this view
        """
        if self.form_class:
            return self.form_class
        else:
            if hasattr(self, 'object') and self.object is not None:
                # If this view is operating on a single object, use
                # the class of that object
                document = self.object.__class__
            elif self.document is not None:
                # If a document has been explicitly provided, use it
                document = self.document
            else:
                # Try to get a queryset and extract the document class
                # from that
                document = self.get_queryset()._document

            exclude = getattr(self, 'form_exclude', ())
            return documentform_factory(document, exclude=exclude)

    def get_form_kwargs(self):
        """
        Returns the keyword arguments for instanciating the form.
        """
        kwargs = super(DocumentFormMixin, self).get_form_kwargs()
        kwargs.update({'instance': self.object})
        return kwargs

    def get_success_url(self):
        if self.success_url:
            url = self.success_url % self.object._data
        else:
            try:
                url = self.object.get_absolute_url()
            except AttributeError:
                raise ImproperlyConfigured(
                    "No URL to redirect to.  Either provide a url or define"
                    " a get_absolute_url method on the document.")
        return url

    def form_valid(self, form):
        self.object = form.save()
        document = self.document or form.Meta.document
        msg = _("The %(verbose_name)s was updated successfully.") % {
                "verbose_name": document._meta.verbose_name}
        msg = self.success_message if self.success_message else msg
        messages.add_message(self.request, messages.SUCCESS, msg, fail_silently=True)
        return super(DocumentFormMixin, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = kwargs
        if self.object:
            context['object'] = self.object
            context_object_name = self.get_context_object_name(self.object)
            if context_object_name:
                context[context_object_name] = self.object
        return context


class EmbeddedFormMixin(FormMixin):
    """
    A mixin that provides a way to show and handle a documentform in a request.
    """
    embedded_form_class = None
    embedded_context_name = 'embedded_form'

    def get_form_class(self):
        """
        Returns the form class to use in this view
        """
        if self.embedded_form_class:
            return self.embedded_form_class
        else:
            raise ImproperlyConfigured(
                    "No embedded form class provided. An embedded form class must be provided.")

    def get_form(self, form_class):
        """
        Returns an instance of the form to be used in this view.
        """
        object = getattr(self, 'object', self.get_object())
        return form_class(object, **self.get_form_kwargs())

    def get_embedded_object(self):
        """
        Returns an instance of the embedded object. By default this is a freshly created
        instance. Override for something cooler.
        """
        if hasattr(self, 'embedded_object'):
            return self.embedded_object()
        else:
            klass = self.get_form_class()
            return klass.Meta.document()

    def get_form_kwargs(self):
        """
        Returns the keyword arguments for instantiating the form.
        """
        kwargs = super(EmbeddedFormMixin, self).get_form_kwargs()
        object = self.get_embedded_object()
        kwargs.update({'instance': object})
        if not 'initial' in kwargs:
            kwargs['initial'] = {}
        return kwargs

    def get_success_url(self):
        object = getattr(self, 'object', self.get_object())
        if self.success_url:
            url = self.success_url % object.__dict__
        else:
            try:
                url = object.get_absolute_url()
            except AttributeError:
                raise ImproperlyConfigured(
                    "No URL to redirect to.  Either provide a url or define"
                    " a get_absolute_url method on the document.")
        return url

    def form_valid(self, form):
        self.embedded_object = form.save()
        return super(EmbeddedFormMixin, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(EmbeddedFormMixin, self).get_context_data(**kwargs)

        object = getattr(self, 'object', self.get_object())
        if 'form' in kwargs:
            form = kwargs['form']
        else:
            form = self.get_form(self.get_form_class())
        context[self.embedded_context_name] = form

        return context


class ProcessEmbeddedFormMixin(object):
    """
    A mixin that processes an embedded form on POST.
    Does not implement any GET handling.
    """
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)
        super(ProcessEmbeddedFormMixin, self).post(request, *args, **kwargs)


class BaseEmbeddedFormMixin(EmbeddedFormMixin, ProcessEmbeddedFormMixin):
    """
    A Mixin that handles an embedded form on POST and
    adds the form into the template context.
    """


class BaseCreateView(DocumentFormMixin, ProcessFormView):
    """
    Base view for creating an new object instance.

    Using this base class requires subclassing to provide a response mixin.
    """
    def get(self, request, *args, **kwargs):
        self.object = None
        return super(BaseCreateView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = None
        return super(BaseCreateView, self).post(request, *args, **kwargs)


class CreateView(SingleDocumentTemplateResponseMixin, BaseCreateView):
    """
    View for creating an new object instance,
    with a response rendered by template.
    """
    template_name_suffix = '_form'


class BaseUpdateView(DocumentFormMixin, ProcessFormView):
    """
    Base view for updating an existing object.

    Using this base class requires subclassing to provide a response mixin.
    """
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(BaseUpdateView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(BaseUpdateView, self).post(request, *args, **kwargs)


class UpdateView(SingleDocumentTemplateResponseMixin, BaseUpdateView):
    """
    View for updating an object,
    with a response rendered by template..
    """
    template_name_suffix = '_form'


class BaseDeleteView(DeletionMixin, BaseDetailView):
    """
    Base view for deleting an object.

    Using this base class requires subclassing to provide a response mixin.
    """


class DeleteView(SingleDocumentTemplateResponseMixin, BaseDeleteView):
    """
    View for deleting an object retrieved with `self.get_object()`,
    with a response rendered by template.
    """
    template_name_suffix = '_confirm_delete'


class EmbeddedDetailView(BaseEmbeddedFormMixin, DetailView):
    """
    Renders the detail view of a document and and adds a
    form for an embedded object into the template.

    See BaseEmbeddedFormMixin for details on the form.
    """
    def get_context_data(self, **kwargs):
        # manually call parents get_context_data without super
        # currently django messes up the super mro chain
        # and for multiple inheritance only one tree is followed
        context = BaseEmbeddedFormMixin.get_context_data(self, **kwargs)
        context.update(DetailView.get_context_data(self, **kwargs))
        return context

########NEW FILE########
__FILENAME__ = list
from django.core.paginator import Paginator, InvalidPage
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.utils.encoding import smart_str
from django.utils.translation import ugettext as _
from django.views.generic.base import TemplateResponseMixin, View

from mongoengine.queryset import QuerySet
from django_mongoengine.forms.utils import get_document_options


class MultipleDocumentMixin(object):
    allow_empty = True
    queryset = None
    document = None
    paginate_by = None
    context_object_name = None
    paginator_class = Paginator

    def get_queryset(self):
        """
        Get the list of items for this view. This must be an interable, and may
        be a queryset (in which qs-specific behavior will be enabled).
        """
        if self.queryset is not None:
            if isinstance(self.queryset, QuerySet):
                queryset = self.queryset.clone()
            else:
                queryset = self.queryset
        elif self.document is not None:
            queryset = self.document.objects()
        else:
            raise ImproperlyConfigured(u"'%s' must define 'queryset' or 'document'"
                                       % self.__class__.__name__)
        return queryset

    def paginate_queryset(self, queryset, page_size):
        """
        Paginate the queryset, if needed.
        """
        paginator = self.get_paginator(queryset, page_size, allow_empty_first_page=self.get_allow_empty())
        page = self.kwargs.get('page') or self.request.GET.get('page') or 1
        try:
            page_number = int(page)
        except ValueError:
            if page == 'last':
                page_number = paginator.num_pages
            else:
                raise Http404(_(u"Page is not 'last', nor can it be converted to an int."))
        try:
            page = paginator.page(page_number)
            page.object_list = [x for x in page.object_list]  # convert to list
            return (paginator, page, page.object_list, page.has_other_pages())
        except InvalidPage:
            raise Http404(_(u'Invalid page (%(page_number)s)') % {
                                'page_number': page_number
            })

    def get_paginate_by(self, queryset):
        """
        Get the number of items to paginate by, or ``None`` for no pagination.
        """
        return self.paginate_by

    def get_paginator(self, queryset, per_page, orphans=0, allow_empty_first_page=True):
        """
        Return an instance of the paginator for this view.
        """
        return self.paginator_class(queryset, per_page, orphans=orphans, allow_empty_first_page=allow_empty_first_page)

    def get_allow_empty(self):
        """
        Returns ``True`` if the view should display empty lists, and ``False``
        if a 404 should be raised instead.
        """
        return self.allow_empty

    def get_context_object_name(self, object_list):
        """
        Get the name of the item to be used in the context.
        """
        if self.context_object_name:
            return self.context_object_name
        elif hasattr(object_list, '_document'):
            opts = get_document_options(object_list._document)
            return smart_str('%s_list' % opts.object_name.lower())
        else:
            return None

    def get_context_data(self, **kwargs):
        """
        Get the context for this view.
        """
        queryset = kwargs.pop('object_list')
        page_size = self.get_paginate_by(queryset)
        context_object_name = self.get_context_object_name(queryset)
        if page_size:
            paginator, page, queryset, is_paginated = self.paginate_queryset(queryset, page_size)
            context = {
                'paginator': paginator,
                'page_obj': page,
                'is_paginated': is_paginated,
                'object_list': queryset
            }
        else:
            queryset = [x for x in queryset] # convert to list
            context = {
                'paginator': None,
                'page_obj': None,
                'is_paginated': False,
                'object_list': queryset
            }
        context.update(kwargs)
        if context_object_name is not None:
            context[context_object_name] = queryset
        return context


class BaseListView(MultipleDocumentMixin, View):
    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        allow_empty = self.get_allow_empty()
        if not allow_empty and len(self.object_list) == 0:
            raise Http404(_(u"Empty list and '%(class_name)s.allow_empty' is False.")
                          % {'class_name': self.__class__.__name__})
        context = self.get_context_data(object_list=self.object_list)
        return self.render_to_response(context)


class MultipleDocumentTemplateResponseMixin(TemplateResponseMixin):
    template_name_suffix = '_list'

    def get_template_names(self):
        """
        Return a list of template names to be used for the request. Must return
        a list. May not be called if get_template is overridden.
        """
        try:
            names = super(MultipleDocumentTemplateResponseMixin, self).get_template_names()
        except ImproperlyConfigured:
            # If template_name isn't specified, it's not a problem --
            # we just start with an empty list.
            names = []

        # If the list is a queryset, we'll invent a template name based on the
        # app and document name. This name gets put at the end of the template
        # name list so that user-supplied names override the automatically-
        # generated ones.
        if hasattr(self.object_list, '_document'):
            opts = get_document_options(self.object_list._document)
            names.append("%s/%s%s.html" % (opts.app_label, opts.object_name.lower(), self.template_name_suffix))

        names.append("{}s.html".format(self.template_name_suffix))
        return names


class ListView(MultipleDocumentTemplateResponseMixin, BaseListView):
    """
    Render some list of objects, set by `self.document` or `self.queryset`.
    `self.queryset` can actually be any iterable of items, not just a queryset.
    """

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
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
sys.path.append(os.path.abspath('_themes'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Django-MongoEngine'
copyright = u'2011-2013, MongoEngine'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1'
# The full version, including alpha/beta/rc tags.
release = '0.1'

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
#pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'flask_small'

html_theme_options = {
     'index_logo': '',
     'github_fork': None
}
# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['_themes']

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

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'django-mongoenginedoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-mongoengine.tex', u'Django-MongoEngine Documentation',
   u'Ross Lawley', 'manual'),
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
    ('index', 'django-mongoengine', u'Django-MongoEngine Documentation',
     ['Ross Lawley'], 1)
]

########NEW FILE########
__FILENAME__ = flask_theme_support
# flasky extensions.  flasky pygments style based on tango style
from pygments.style import Style
from pygments.token import Keyword, Name, Comment, String, Error, \
     Number, Operator, Generic, Whitespace, Punctuation, Other, Literal


class FlaskyStyle(Style):
    background_color = "#f8f8f8"
    default_style = ""

    styles = {
        # No corresponding class for the following:
        #Text:                     "", # class:  ''
        Whitespace:                "underline #f8f8f8",      # class: 'w'
        Error:                     "#a40000 border:#ef2929", # class: 'err'
        Other:                     "#000000",                # class 'x'

        Comment:                   "italic #8f5902", # class: 'c'
        Comment.Preproc:           "noitalic",       # class: 'cp'

        Keyword:                   "bold #004461",   # class: 'k'
        Keyword.Constant:          "bold #004461",   # class: 'kc'
        Keyword.Declaration:       "bold #004461",   # class: 'kd'
        Keyword.Namespace:         "bold #004461",   # class: 'kn'
        Keyword.Pseudo:            "bold #004461",   # class: 'kp'
        Keyword.Reserved:          "bold #004461",   # class: 'kr'
        Keyword.Type:              "bold #004461",   # class: 'kt'

        Operator:                  "#582800",   # class: 'o'
        Operator.Word:             "bold #004461",   # class: 'ow' - like keywords

        Punctuation:               "bold #000000",   # class: 'p'

        # because special names such as Name.Class, Name.Function, etc.
        # are not recognized as such later in the parsing, we choose them
        # to look the same as ordinary variables.
        Name:                      "#000000",        # class: 'n'
        Name.Attribute:            "#c4a000",        # class: 'na' - to be revised
        Name.Builtin:              "#004461",        # class: 'nb'
        Name.Builtin.Pseudo:       "#3465a4",        # class: 'bp'
        Name.Class:                "#000000",        # class: 'nc' - to be revised
        Name.Constant:             "#000000",        # class: 'no' - to be revised
        Name.Decorator:            "#888",           # class: 'nd' - to be revised
        Name.Entity:               "#ce5c00",        # class: 'ni'
        Name.Exception:            "bold #cc0000",   # class: 'ne'
        Name.Function:             "#000000",        # class: 'nf'
        Name.Property:             "#000000",        # class: 'py'
        Name.Label:                "#f57900",        # class: 'nl'
        Name.Namespace:            "#000000",        # class: 'nn' - to be revised
        Name.Other:                "#000000",        # class: 'nx'
        Name.Tag:                  "bold #004461",   # class: 'nt' - like a keyword
        Name.Variable:             "#000000",        # class: 'nv' - to be revised
        Name.Variable.Class:       "#000000",        # class: 'vc' - to be revised
        Name.Variable.Global:      "#000000",        # class: 'vg' - to be revised
        Name.Variable.Instance:    "#000000",        # class: 'vi' - to be revised

        Number:                    "#990000",        # class: 'm'

        Literal:                   "#000000",        # class: 'l'
        Literal.Date:              "#000000",        # class: 'ld'

        String:                    "#4e9a06",        # class: 's'
        String.Backtick:           "#4e9a06",        # class: 'sb'
        String.Char:               "#4e9a06",        # class: 'sc'
        String.Doc:                "italic #8f5902", # class: 'sd' - like a comment
        String.Double:             "#4e9a06",        # class: 's2'
        String.Escape:             "#4e9a06",        # class: 'se'
        String.Heredoc:            "#4e9a06",        # class: 'sh'
        String.Interpol:           "#4e9a06",        # class: 'si'
        String.Other:              "#4e9a06",        # class: 'sx'
        String.Regex:              "#4e9a06",        # class: 'sr'
        String.Single:             "#4e9a06",        # class: 's1'
        String.Symbol:             "#4e9a06",        # class: 'ss'

        Generic:                   "#000000",        # class: 'g'
        Generic.Deleted:           "#a40000",        # class: 'gd'
        Generic.Emph:              "italic #000000", # class: 'ge'
        Generic.Error:             "#ef2929",        # class: 'gr'
        Generic.Heading:           "bold #000080",   # class: 'gh'
        Generic.Inserted:          "#00A000",        # class: 'gi'
        Generic.Output:            "#888",           # class: 'go'
        Generic.Prompt:            "#745334",        # class: 'gp'
        Generic.Strong:            "bold #000000",   # class: 'gs'
        Generic.Subheading:        "bold #800080",   # class: 'gu'
        Generic.Traceback:         "bold #a40000",   # class: 'gt'
    }

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tumblelog.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = admin
from django_mongoengine import admin

from tumblelog.models import BlogPost, Image, Quote, Video, Music


class BlogPostAdmin(admin.DocumentAdmin):
    pass


class ImageAdmin(admin.DocumentAdmin):
    pass


class MusicAdmin(admin.DocumentAdmin):
    pass


class QuoteAdmin(admin.DocumentAdmin):
    pass


class VideoAdmin(admin.DocumentAdmin):
    pass


admin.site.register(BlogPost, BlogPostAdmin)
admin.site.register(Image, ImageAdmin)
admin.site.register(Quote, QuoteAdmin)
admin.site.register(Video, VideoAdmin)
admin.site.register(Music, MusicAdmin)

########NEW FILE########
__FILENAME__ = forms
from django_mongoengine.forms import EmbeddedDocumentForm

from tumblelog.models import BlogPost, Comment


class CommentForm(EmbeddedDocumentForm):

    class Meta:
        document = Comment
        embedded_field_name = 'comments'
        exclude = ('created_at',)

########NEW FILE########
__FILENAME__ = models
from django.core.urlresolvers import reverse

from django_mongoengine import Document
from django_mongoengine import fields

import datetime


class Post(Document):
    created_at = fields.DateTimeField(default=datetime.datetime.now, required=True)
    title = fields.StringField(max_length=255, required=True)
    slug = fields.StringField(max_length=255, required=True, primary_key=True)
    comments = fields.ListField(fields.EmbeddedDocumentField('Comment'))

    def get_absolute_url(self):
        return reverse('post', kwargs={"slug": self.slug})

    def __unicode__(self):
        return self.title

    @property
    def post_type(self):
        return self.__class__.__name__

    meta = {
        'indexes': ['-created_at', 'slug'],
        'ordering': ['-created_at'],
        'allow_inheritance': True
    }


class BlogPost(Post):
    body = fields.StringField(required=True)


class Video(Post):
    embed_code = fields.StringField(required=True)


class Image(Post):
    image = fields.ImageField(required=True)


class Quote(Post):
    body = fields.StringField(required=True)
    author = fields.StringField(verbose_name="Author Name", required=True, max_length=255)


class Music(Post):
    url = fields.StringField(max_length=100, verbose_name="Music Url", required=True)
    music_parameters = fields.DictField(verbose_name="Music Parameters", required=True)


class Comment(fields.EmbeddedDocument):
    created_at = fields.DateTimeField(default=datetime.datetime.now, required=True)
    author = fields.StringField(verbose_name="Name", max_length=255, required=True)
    body = fields.StringField(verbose_name="Comment", required=True)

########NEW FILE########
__FILENAME__ = settings
# Django settings for tumblelog project.
import sys
import os

PROJECT_ROOT = os.path.dirname(__file__)
sys.path.insert(0, os.path.realpath(os.path.join(PROJECT_ROOT, '../../../')))


DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

# MongoDB settings
MONGODB_DATABASES = {
    'default': {'name': 'django_mongoengine'}
}
DJANGO_MONGOENGINE_OVERRIDE_ADMIN = True


DATABASES = {
    'default': {'ENGINE': 'django.db.backends.dummy'}
}

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
LANGUAGE_CODE = 'en-gb'

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
SECRET_KEY = 'd2h8yt+x2g0$+e#9$z5z$auy%v0axov(wt3o*bj1#h^1+x^n(!'

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
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'tumblelog.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'tumblelog.wsgi.application'

TEMPLATE_DIRS = (
    os.path.join(os.path.realpath(os.path.dirname(__file__)), '../templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'debug_toolbar',
    'django_mongoengine.debug_toolbar',
    'django_mongoengine.auth',
    'django_mongoengine.admin.sites',
    'django_mongoengine.admin',
    'django.contrib.admin',
    'tumblelog'
)

AUTHENTICATION_BACKENDS = (
    'django_mongoengine.auth.backends.MongoEngineBackend',
)

SESSION_ENGINE = 'django_mongoengine.sessions'

DEBUG_TOOLBAR_PANELS = (
    'debug_toolbar.panels.version.VersionDebugPanel',
    'debug_toolbar.panels.timer.TimerDebugPanel',
    'debug_toolbar.panels.settings_vars.SettingsVarsDebugPanel',
    'debug_toolbar.panels.headers.HeaderDebugPanel',
    'debug_toolbar.panels.template.TemplateDebugPanel',
    'debug_toolbar.panels.signals.SignalDebugPanel',
    'debug_toolbar.panels.logger.LoggingPanel',
    'django_mongoengine.debug_toolbar.panel.MongoDebugPanel',
)

DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False
}

INTERNAL_IPS = ('127.0.0.1', '10.0.2.2',)


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

from tumblelog.views import (PostIndexView, AddPostView, PostDetailView,
                             UpdatePostView, DeletePostView, ImageFileView)

# # Enable admin
from django.contrib import admin
admin.autodiscover()

from django_mongoengine.admin import site

post_patterns = patterns('',
    url(r'^$', PostDetailView.as_view(), name="post"),
    url(r'^edit/$', UpdatePostView.as_view(), name="post_update"),
    url(r'^delete/$', DeletePostView.as_view(), name="post_delete")
)


urlpatterns = patterns('',
    url(r'^$', PostIndexView.as_view(), name="post_index"),
    url(r'^new/$', AddPostView.as_view(), name="post_new"),
    url(r'^new/(?P<post_type>(post|video|image|quote|music))/$',
            AddPostView.as_view(), name="post_new"),
    url(r'^admin/', include(site.urls)),
    url(r'^image-file/(?P<slug>[a-zA-Z0-9-]+)/', ImageFileView.as_view(),
            name="image_file"),
    url(r'^(?P<slug>[a-zA-Z0-9-]+)/', include(post_patterns))
)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse

from django_mongoengine.forms.fields import DictField
from django_mongoengine.views import (CreateView, UpdateView,
                                      DeleteView, ListView,
                                      EmbeddedDetailView, View)

from tumblelog.models import Post, BlogPost, Video, Image, Quote, Music
from tumblelog.forms import CommentForm


class PostIndexView(ListView):
    document = Post
    context_object_name = 'posts_list'


class PostDetailView(EmbeddedDetailView):
    document = Post
    context_object_name = 'post'
    embedded_context_name = 'form'
    embedded_form_class = CommentForm
    success_message = "Comment Posted!"


class AddPostView(CreateView):
    success_url = '/'
    doc_map = {'post': BlogPost, 'video': Video, 'image': Image, 'quote': Quote, 'music': Music}
    success_message = "Post Added!"
    form_exclude = ('created_at', 'comments')

    @property
    def document(self):
        post_type = self.kwargs.get('post_type', 'post')
        return self.doc_map.get(post_type)

    def get_form(self, form_class):
        form = super(AddPostView, self).get_form(form_class)
        music_parameters = form.fields.get('music_parameters', None)
        if music_parameters is not None:
            schema = {
                'Artist': '',
                'Title': '',
                'Album': '',
                'Genre': '',
                'Label': '',
                'Release dates': {
                    'UK': '',
                    'US': '',
                    'FR': ''
                }
            }
            music_parameters = DictField(initial=schema, flags=['FORCE_SCHEMA'])
            form.fields['music_parameters'] = music_parameters
        return form


class DeletePostView(DeleteView):
    document = Post
    success_url = '/'


class UpdatePostView(UpdateView):
    document = Post
    form_exclude = ('created_at', 'comments',)


class ImageFileView(View):

    def get(self, request, slug, *args, **kwargs):
        image_doc = Image.objects.get_or_404(slug=slug)
        image = image_doc.image
        return HttpResponse(image.read(),
                            mimetype='image/%s' % image.format.lower())

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for tumblelog project.

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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tumblelog.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = tests
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

from django import test
test.utils.setup_test_environment()
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.forms.fields import TextInput

from django_mongoengine.tests import MongoTestCase
from django_mongoengine.forms.fields import DictField
from django_mongoengine.forms.widgets import Dictionary, SubDictionary, Pair

#TODO : test for max_depth


class DictFieldTest(MongoTestCase):
    """
    TestCase class that tests a DictField object
    """
    def __init__(self, methodName='rundict'):
        super(DictFieldTest, self).__init__(methodName)

    def test_ouput(self):
        """
        Test the output of a DictField
        """
        self._init_field()
        max_depth_test = 2
        #valid input/outpout
        valid_input = {
            '[[key1,value1],[key2,value2],[key3,value3]]':
                [['key1', 'value1'], ['key2', 'value2'], ['key3', 'value3']],
            '[[key1,value1],[skey,[[skey1,svalue1],[skey2,svalue2],[skey3,svalue3]]],[key2,value2],[key3,value3]]':
                [['key1', 'value1'], ['skey', [['skey1', 'svalue1'], ['skey2', 'svalue2'], ['skey3', 'svalue3']]], ['key2', 'value2'], ['key3', 'value3']],
            '[[a,[[b,[[c,[[d,[[e,[[f,g]]]]]]]]]]]]':
                [['a', [['b', [['c', [['d', [['e', [['f', 'g']]]]]]]]]]]],
        }
        valid_output = {
            '[[key1,value1],[key2,value2],[key3,value3]]': {
                'key1': 'value1',
                'key2': 'value2',
                'key3': 'value3'
            },
            '[[key1,value1],[skey,[[skey1,svalue1],[skey2,svalue2],[skey3,svalue3]]],[key2,value2],[key3,value3]]': {
                'key1': 'value1',
                'skey': {
                        'skey1': 'svalue1',
                        'skey2': 'svalue2',
                        'skey3': 'svalue3'
                    },
                'key2': 'value2',
                'key3': 'value3'
            },
            '[[a,[[b,[[c,[[d,[[e,[[f,g]]]]]]]]]]]]': {
                'a': {
                    'b': {
                        'c': {
                            'd': {
                                'e': {
                                    'f': 'g'
                                }
                            }
                        }
                    }
                }
            },
        }
        #invalid input/message
        invalid_input = {
            '[[key1,value1],[$key2,value2]]': [['key1', 'value1'], ['$key2', 'value2']],
            '[[key1,value1],[_key2,value2]]': [['key1', 'value1'], ['_key2', 'value2']],
            '[[key1,value1],[k.ey2,value2]]': [['key1', 'value1'], ['k.ey2', 'value2']],
            '[[keykeykeykeykeykeykeykeykeykeykey,value1],[key2,value2]]': [['keykeykeykeykeykeykeykeykeykeykey', 'value1'], ['key2', 'value2']],
            '[[err,value1],[key2,value2]]': [['err', 'value1'], ['key2', 'value2']],
            '[[errmsg,value1],[key2,value2]]': [['errmsg', 'value1'], ['key2', 'value2']],
            '[[key1,[key2,[key3,[key4,value4]]]]]': [['key1', [['key2', [['key3', [['key4', 'value4']]]]]]]],
        }
        invalid_message = {
            '[[key1,value1],[$key2,value2]]': [u'Ensure the keys do not begin with : ["$","_"].'],
            '[[key1,value1],[_key2,value2]]': [u'Ensure the keys do not begin with : ["$","_"].'],
            '[[key1,value1],[k.ey2,value2]]': [self.field.error_messages['illegal'] % self.field.illegal_characters],
            '[[keykeykeykeykeykeykeykeykeykeykey,value1],[key2,value2]]': [self.field.error_messages['length'] % self.field.key_limit],
            '[[err,value1],[key2,value2]]': [self.field.error_messages['invalid_key'] % self.field.invalid_keys],
            '[[errmsg,value1],[key2,value2]]': [self.field.error_messages['invalid_key'] % self.field.invalid_keys],
            '[[key1,[key2,[key3,[key4,value4]]]]]': [self.field.error_messages['depth'] % max_depth_test],
        }

        # test valid inputs
        for input, output in valid_output.items():
            out = self.field.clean(valid_input[input])
            assert isinstance(out, dict), 'output should be a dictionary'
            self.assertDictEqual(out, output)
        # test invalid inputs
        self._init_field(depth=max_depth_test)
        for input, input_list in invalid_input.items():
            with self.assertRaises(ValidationError) as context_manager:
                self.field.clean(input_list)
            self.assertEqual(context_manager.exception.messages, invalid_message[input])

    def test_rendering(self):
        """
        Test the structure of a widget, after having passed a data dictionary
        """
        self._init_field()
        #contains the POST data dicts
        data_inputs = {
            'data1': {
                u'widget_name_0_subdict_0': [u'a'],
                u'widget_name_0_subdict_1_0_subdict_0': [u'b'],
                u'widget_name_0_subdict_1_0_subdict_1_0_pair_0': [u'f'],
                u'widget_name_0_subdict_1_0_subdict_1_0_pair_1': [u'g'],
            }
        }
        #contains the data dicts
        data_dicts = {
            'data1': {
                u'a': {
                    u'b': {
                        u'f': u'g'
                    }
                }
            }
        }
        #contains structures of output
        output_structures = {
            'data1': {
                'type': 'Dictionary',
                'widgets': [{'type': 'SubDictionary',
                      'widgets': [{'type': 'TextInput'}, {'type': 'Dictionary',
                                                    'widgets': [{'type': 'SubDictionary',
                                                          'widgets': [{'type': 'TextInput'}, {'type': 'Dictionary',
                                                                                        'widgets': [{'type': 'Pair', 'widgets':[{'type': 'TextInput'}, {'type': 'TextInput'}]}]
                                                                    }]
                                                            }]
                                }]
                        }]
            }
        }

        for data, datadict in data_inputs.items():
            self.field.widget.render('widget_name', self.field.widget.value_from_datadict(datadict, {}, 'widget_name'))
            self._check_structure(self.field.widget, output_structures[data])
            self.field.widget.render('widget_name', data_dicts[data])
            self._check_structure(self.field.widget, output_structures[data])

    def test_static(self):
        self._init_field(force=True)
        structure = {
            'type': 'Dictionary',
            'widgets': [{'type': 'StaticPair', 'widgets': [{'type': 'HiddenInput'}, {'type': 'TextInput'}]
                },
                {'type': 'StaticSubDictionary',
                    'widgets': [{'type': 'StaticPair', 'widgets': [{'type': 'HiddenInput'}, {'type': 'TextInput'}]}]
                },
                {'type': 'StaticSubDictionary',
                    'widgets': [{'type': 'StaticPair',
                                'widgets': [{'type': 'HiddenInput'}, {'type': 'TextInput'}]},
                                {'type': 'StaticPair',
                                'widgets': [{'type': 'HiddenInput'}, {'type': 'TextInput'}]}]
                }]
        }
        self._check_structure(self.field.widget, structure)

    def _init_field(self, depth=None, force=False):
        validate = [RegexValidator(regex='^[^$_]', message=u'Ensure the keys do not begin with : ["$","_"].', code='invalid_start')]
        if force:
            self.field = DictField(**{
                'required': False,
                'initial': {
                    'k': 'v',
                    'k2': {'k3': 'v2'},
                    'k4': {'k5': 'v3', 'k6': 'v4'}
                },
                'validators': validate,
                'flags': ['FORCE_SCHEMA'],
                'max_depth': depth,
            })
        else:
            self.field = DictField(**{
                'required': False,
                'initial': {
                    'k': 'v',
                    'k2': {'k3': 'v2'}
                },
                'validators': validate,
                'max_depth': depth,
            })

    def _check_structure(self, widget, structure):
        assert isinstance(structure, dict), 'error, the comparative structure should be a dictionary'
        assert isinstance(widget, eval(structure['type'])), 'widget should be a %s' % structure['type']
        if 'widgets' in structure.keys():
            assert isinstance(structure['widgets'], list), 'structure field "widgets" should be a list'
            assert isinstance(widget.widgets, list), 'widget.widgets should be a list'
            for i, w in enumerate(widget.widgets):
                self._check_structure(w, structure['widgets'][i])

########NEW FILE########
__FILENAME__ = settings
# Django settings for tumblelog project.
import sys
import os

PROJECT_ROOT = os.path.dirname(__file__)
sys.path.append(os.path.join(PROJECT_ROOT, '../../../'))


DEBUG = True
TEMPLATE_DEBUG = False

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

# MongoDB Databases
MONGODB_DATABASES = {
    'default': {'name': 'django_mongoengine_test'}
}

DATABASES = {
    'default': {
    }
}

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
LANGUAGE_CODE = 'en-gb'

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
SECRET_KEY = 'd2h8yt+x2g0$+e#9$z5z$auy%v0axov(wt3o*bj1#h^1+x^n(!'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.common.CommonMiddleware'
)

ROOT_URLCONF = ''

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'tumblelog.wsgi.application'

TEMPLATE_DIRS = ()

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tests.views'
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
__FILENAME__ = base
import time

from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.test import TestCase, RequestFactory
from django.utils import unittest
from django.views.generic import View, TemplateView, RedirectView

from django_mongoengine.tests import MongoTestCase as TestCase


class SimpleView(View):
    """
    A simple view with a docstring.
    """
    def get(self, request):
        return HttpResponse('This is a simple view')


class SimplePostView(SimpleView):
    post = SimpleView.get


class PostOnlyView(View):
    def post(self, request):
        return HttpResponse('This view only accepts POST')


class CustomizableView(SimpleView):
    parameter = {}


def decorator(view):
    view.is_decorated = True
    return view


class DecoratedDispatchView(SimpleView):

    @decorator
    def dispatch(self, request, *args, **kwargs):
        return super(DecoratedDispatchView, self).dispatch(request, *args, **kwargs)


class AboutTemplateView(TemplateView):
    def get(self, request):
        return self.render_to_response({})

    def get_template_names(self):
        return ['views/about.html']


class AboutTemplateAttributeView(TemplateView):
    template_name = 'views/about.html'

    def get(self, request):
        return self.render_to_response(context={})


class InstanceView(View):

    def get(self, request):
        return self


class ViewTest(unittest.TestCase):
    rf = RequestFactory()

    def _assert_simple(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'This is a simple view')

    def test_no_init_kwargs(self):
        """
        Test that a view can't be accidentally instantiated before deployment
        """
        try:
            view = SimpleView(key='value').as_view()
            self.fail('Should not be able to instantiate a view')
        except AttributeError:
            pass

    def test_no_init_args(self):
        """
        Test that a view can't be accidentally instantiated before deployment
        """
        try:
            view = SimpleView.as_view('value')
            self.fail('Should not be able to use non-keyword arguments instantiating a view')
        except TypeError:
            pass

    def test_pathological_http_method(self):
        """
        The edge case of a http request that spoofs an existing method name is caught.
        """
        self.assertEqual(SimpleView.as_view()(
            self.rf.get('/', REQUEST_METHOD='DISPATCH')
        ).status_code, 405)

    def test_get_only(self):
        """
        Test a view which only allows GET doesn't allow other methods.
        """
        self._assert_simple(SimpleView.as_view()(self.rf.get('/')))
        self.assertEqual(SimpleView.as_view()(self.rf.post('/')).status_code, 405)
        self.assertEqual(SimpleView.as_view()(
            self.rf.get('/', REQUEST_METHOD='FAKE')
        ).status_code, 405)

    def test_get_and_head(self):
        """
        Test a view which supplies a GET method also responds correctly to HEAD.
        """
        self._assert_simple(SimpleView.as_view()(self.rf.get('/')))
        response = SimpleView.as_view()(self.rf.head('/'))
        self.assertEqual(response.status_code, 200)

    def test_head_no_get(self):
        """
        Test a view which supplies no GET method responds to HEAD with HTTP 405.
        """
        response = PostOnlyView.as_view()(self.rf.head('/'))
        self.assertEqual(response.status_code, 405)

    def test_get_and_post(self):
        """
        Test a view which only allows both GET and POST.
        """
        self._assert_simple(SimplePostView.as_view()(self.rf.get('/')))
        self._assert_simple(SimplePostView.as_view()(self.rf.post('/')))
        self.assertEqual(SimplePostView.as_view()(
            self.rf.get('/', REQUEST_METHOD='FAKE')
        ).status_code, 405)

    def test_invalid_keyword_argument(self):
        """
        Test that view arguments must be predefined on the class and can't
        be named like a HTTP method.
        """
        # Check each of the allowed method names
        for method in SimpleView.http_method_names:
            kwargs = dict(((method, "value"),))
            self.assertRaises(TypeError, SimpleView.as_view, **kwargs)

        # Check the case view argument is ok if predefined on the class...
        CustomizableView.as_view(parameter="value")
        # ...but raises errors otherwise.
        self.assertRaises(TypeError, CustomizableView.as_view, foobar="value")

    def test_calling_more_than_once(self):
        """
        Test a view can only be called once.
        """
        request = self.rf.get('/')
        view = InstanceView.as_view()
        self.assertNotEqual(view(request), view(request))

    def test_class_attributes(self):
        """
        Test that the callable returned from as_view() has proper
        docstring, name and module.
        """
        self.assertEqual(SimpleView.__doc__, SimpleView.as_view().__doc__)
        self.assertEqual(SimpleView.__name__, SimpleView.as_view().__name__)
        self.assertEqual(SimpleView.__module__, SimpleView.as_view().__module__)

    def test_dispatch_decoration(self):
        """
        Test that attributes set by decorators on the dispatch method
        are also present on the closure.
        """
        self.assertTrue(DecoratedDispatchView.as_view().is_decorated)


class TemplateViewTest(TestCase):
    urls = 'tests.views.urls'

    rf = RequestFactory()

    def _assert_about(self, response):
        response.render()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<h1>About</h1>')

    def test_get(self):
        """
        Test a view that simply renders a template on GET
        """
        self._assert_about(AboutTemplateView.as_view()(self.rf.get('/about/')))

    def test_head(self):
        """
        Test a TemplateView responds correctly to HEAD
        """
        response = AboutTemplateView.as_view()(self.rf.head('/about/'))
        self.assertEqual(response.status_code, 200)

    def test_get_template_attribute(self):
        """
        Test a view that renders a template on GET with the template name as
        an attribute on the class.
        """
        self._assert_about(AboutTemplateAttributeView.as_view()(self.rf.get('/about/')))

    def test_get_generic_template(self):
        """
        Test a completely generic view that renders a template on GET
        with the template name as an argument at instantiation.
        """
        self._assert_about(TemplateView.as_view(template_name='views/about.html')(self.rf.get('/about/')))

    def test_template_name_required(self):
        """
        A template view must provide a template name
        """
        self.assertRaises(ImproperlyConfigured, self.client.get, '/template/no_template/')

    def test_template_params(self):
        """
        A generic template view passes kwargs as context.
        """
        response = self.client.get('/template/simple/bar/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['params'], {'foo': 'bar'})

    def test_extra_template_params(self):
        """
        A template view can be customized to return extra context.
        """
        response = self.client.get('/template/custom/bar/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['params'], {'foo': 'bar'})
        self.assertEqual(response.context['key'], 'value')

    def test_cached_views(self):
        """
        A template view can be cached
        """
        response = self.client.get('/template/cached/bar/')
        self.assertEqual(response.status_code, 200)

        time.sleep(1.0)

        response2 = self.client.get('/template/cached/bar/')
        self.assertEqual(response2.status_code, 200)

        self.assertEqual(response.content, response2.content)

        time.sleep(2.0)

        # Let the cache expire and test again
        response2 = self.client.get('/template/cached/bar/')
        self.assertEqual(response2.status_code, 200)

        self.assertNotEqual(response.content, response2.content)

class RedirectViewTest(unittest.TestCase):
    rf = RequestFactory()

    def test_no_url(self):
        "Without any configuration, returns HTTP 410 GONE"
        response = RedirectView.as_view()(self.rf.get('/foo/'))
        self.assertEqual(response.status_code, 410)

    def test_permanent_redirect(self):
        "Default is a permanent redirect"
        response = RedirectView.as_view(url='/bar/')(self.rf.get('/foo/'))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/bar/')

    def test_temporary_redirect(self):
        "Permanent redirects are an option"
        response = RedirectView.as_view(url='/bar/', permanent=False)(self.rf.get('/foo/'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/bar/')

    def test_include_args(self):
        "GET arguments can be included in the redirected URL"
        response = RedirectView.as_view(url='/bar/')(self.rf.get('/foo/'))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/bar/')

        response = RedirectView.as_view(url='/bar/', query_string=True)(self.rf.get('/foo/?pork=spam'))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/bar/?pork=spam')

    def test_include_urlencoded_args(self):
        "GET arguments can be URL-encoded when included in the redirected URL"
        response = RedirectView.as_view(url='/bar/', query_string=True)(
            self.rf.get('/foo/?unicode=%E2%9C%93'))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/bar/?unicode=%E2%9C%93')

    def test_parameter_substitution(self):
        "Redirection URLs can be parameterized"
        response = RedirectView.as_view(url='/bar/%(object_id)d/')(self.rf.get('/foo/42/'), object_id=42)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/bar/42/')

    def test_redirect_POST(self):
        "Default is a permanent redirect"
        response = RedirectView.as_view(url='/bar/')(self.rf.post('/foo/'))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/bar/')

    def test_redirect_HEAD(self):
        "Default is a permanent redirect"
        response = RedirectView.as_view(url='/bar/')(self.rf.head('/foo/'))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/bar/')

    def test_redirect_OPTIONS(self):
        "Default is a permanent redirect"
        response = RedirectView.as_view(url='/bar/')(self.rf.options('/foo/'))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/bar/')

    def test_redirect_PUT(self):
        "Default is a permanent redirect"
        response = RedirectView.as_view(url='/bar/')(self.rf.put('/foo/'))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/bar/')

    def test_redirect_DELETE(self):
        "Default is a permanent redirect"
        response = RedirectView.as_view(url='/bar/')(self.rf.delete('/foo/'))
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/bar/')

    def test_redirect_when_meta_contains_no_query_string(self):
        "regression for #16705"
        # we can't use self.rf.get because it always sets QUERY_STRING
        response = RedirectView.as_view(url='/bar/')(self.rf.request(PATH_INFO='/foo/'))
        self.assertEqual(response.status_code, 301)

########NEW FILE########
__FILENAME__ = detail
from __future__ import absolute_import

from django.core.exceptions import ImproperlyConfigured
from .tests import TestCase

from .models import Artist, Author, Page


class DetailViewTest(TestCase):
    urls = 'tests.views.urls'

    def test_simple_object(self):
        res = self.client.get('/detail/obj/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], {'foo': 'bar'})
        self.assertTemplateUsed(res, 'views/detail.html')

    def test_detail_by_pk(self):
        res = self.client.get('/detail/author/1/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], Author.objects.get(pk='1'))
        self.assertEqual(res.context['author'], Author.objects.get(pk='1'))
        self.assertTemplateUsed(res, 'views/author_detail.html')

    def test_detail_by_custom_pk(self):
        res = self.client.get('/detail/author/bycustompk/1/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], Author.objects.get(pk='1'))
        self.assertEqual(res.context['author'], Author.objects.get(pk='1'))
        self.assertTemplateUsed(res, 'views/author_detail.html')

    def test_detail_by_slug(self):
        res = self.client.get('/detail/author/byslug/scott-rosenberg/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], Author.objects.get(slug='scott-rosenberg'))
        self.assertEqual(res.context['author'], Author.objects.get(slug='scott-rosenberg'))
        self.assertTemplateUsed(res, 'views/author_detail.html')

    def test_detail_by_custom_slug(self):
        res = self.client.get('/detail/author/bycustomslug/scott-rosenberg/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], Author.objects.get(slug='scott-rosenberg'))
        self.assertEqual(res.context['author'], Author.objects.get(slug='scott-rosenberg'))
        self.assertTemplateUsed(res, 'views/author_detail.html')

    def test_verbose_name(self):
        res = self.client.get('/detail/artist/1/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], Artist.objects.get(pk='1'))
        self.assertEqual(res.context['artist'], Artist.objects.get(pk='1'))
        self.assertTemplateUsed(res, 'views/artist_detail.html')

    def test_template_name(self):
        res = self.client.get('/detail/author/1/template_name/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], Author.objects.get(pk='1'))
        self.assertEqual(res.context['author'], Author.objects.get(pk='1'))
        self.assertTemplateUsed(res, 'views/about.html')

    def test_template_name_suffix(self):
        res = self.client.get('/detail/author/1/template_name_suffix/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], Author.objects.get(pk='1'))
        self.assertEqual(res.context['author'], Author.objects.get(pk='1'))
        self.assertTemplateUsed(res, 'views/author_view.html')

    def test_template_name_field(self):
        res = self.client.get('/detail/page/1/field/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], Page.objects.get(pk='1'))
        self.assertEqual(res.context['page'], Page.objects.get(pk='1'))
        self.assertTemplateUsed(res, 'views/page_template.html')

    def test_context_object_name(self):
        res = self.client.get('/detail/author/1/context_object_name/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], Author.objects.get(pk='1'))
        self.assertEqual(res.context['thingy'], Author.objects.get(pk='1'))
        self.assertFalse('author' in res.context)
        self.assertTemplateUsed(res, 'views/author_detail.html')

    def test_duplicated_context_object_name(self):
        res = self.client.get('/detail/author/1/dupe_context_object_name/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], Author.objects.get(pk='1'))
        self.assertFalse('author' in res.context)
        self.assertTemplateUsed(res, 'views/author_detail.html')

    def test_invalid_url(self):
        self.assertRaises(AttributeError, self.client.get, '/detail/author/invalid/url/')

    def test_invalid_queryset(self):
        self.assertRaises(ImproperlyConfigured, self.client.get, '/detail/author/invalid/qs/')

########NEW FILE########
__FILENAME__ = edit
from __future__ import absolute_import

from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django import forms
from django.utils.unittest import expectedFailure
from django.views.generic.edit import FormMixin

from django_mongoengine import forms

from .tests import TestCase
from .models import Artist, Author

from . import views


class FormMixinTests(TestCase):

    def test_initial_data(self):
        """ Test instance independence of initial data dict (see #16138) """
        initial_1 = FormMixin().get_initial()
        initial_1['foo'] = 'bar'
        initial_2 = FormMixin().get_initial()
        self.assertNotEqual(initial_1, initial_2)


class ModelFormMixinTests(TestCase):
    def test_get_form(self):
        form_class = views.AuthorGetQuerySetFormView().get_form_class()
        self.assertEqual(form_class._meta.model, Author)


class CreateViewTests(TestCase):
    urls = 'tests.views.urls'

    def setUp(self):
        Author.drop_collection()

    def test_create(self):
        res = self.client.get('/edit/authors/create/')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(isinstance(res.context['form'], forms.DocumentForm))
        self.assertFalse('object' in res.context)
        self.assertFalse('author' in res.context)
        self.assertTemplateUsed(res, 'views/author_form.html')

        res = self.client.post('/edit/authors/create/',
                        {'id': 1, 'name': 'Randall Munroe', 'slug': 'randall-munroe'})
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, 'http://testserver/list/authors/')
        self.assertQuerysetEqual(Author.objects.all(), ['<Author: Randall Munroe>'])

    def test_create_invalid(self):
        res = self.client.post('/edit/authors/create/',
                        {'id': 1, 'name': 'A' * 101, 'slug': 'randall-munroe'})
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'views/author_form.html')
        self.assertEqual(len(res.context['form'].errors), 1)
        self.assertEqual(Author.objects.count(), 0)

    def test_create_with_object_url(self):
        res = self.client.post('/edit/artists/create/',
                        {'id': 1, 'name': 'Rene Magritte'})
        self.assertEqual(res.status_code, 302)
        artist = Artist.objects.get(name='Rene Magritte')
        self.assertRedirects(res, 'http://testserver/detail/artist/%s/' % artist.pk)
        self.assertQuerysetEqual(Artist.objects.all(), ['<Artist: Rene Magritte>'])

    def test_create_with_redirect(self):
        res = self.client.post('/edit/authors/create/redirect/',
                            {'id': 1, 'name': 'Randall Munroe', 'slug': 'randall-munroe'})
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, 'http://testserver/edit/authors/create/')
        self.assertQuerysetEqual(Author.objects.all(), ['<Author: Randall Munroe>'])

    def test_create_with_interpolated_redirect(self):
        res = self.client.post('/edit/authors/create/interpolate_redirect/',
                            {'id': 1, 'name': 'Randall Munroe', 'slug': 'randall-munroe'})
        self.assertQuerysetEqual(Author.objects.all(), ['<Author: Randall Munroe>'])
        self.assertEqual(res.status_code, 302)
        pk = Author.objects.all()[0].pk
        self.assertRedirects(res, 'http://testserver/edit/author/%s/update/' % pk)

    def test_create_with_special_properties(self):
        res = self.client.get('/edit/authors/create/special/')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(isinstance(res.context['form'], views.AuthorForm))
        self.assertFalse('object' in res.context)
        self.assertFalse('author' in res.context)
        self.assertTemplateUsed(res, 'views/form.html')

        res = self.client.post('/edit/authors/create/special/',
                            {'id': 1, 'name': 'Randall Munroe', 'slug': 'randall-munroe'})
        self.assertEqual(res.status_code, 302)
        obj = Author.objects.get(slug='randall-munroe')
        self.assertRedirects(res, reverse('author_detail', kwargs={'pk': obj.pk}))
        self.assertQuerysetEqual(Author.objects.all(), ['<Author: Randall Munroe>'])

    def test_create_without_redirect(self):
        try:
            res = self.client.post('/edit/authors/create/naive/',
                            {'id': 1, 'name': 'Randall Munroe', 'slug': 'randall-munroe'})
            self.fail('Should raise exception -- No redirect URL provided, and no get_absolute_url provided')
        except ImproperlyConfigured:
            pass


class UpdateViewTests(TestCase):
    urls = 'tests.views.urls'

    def setUp(self):
        Author.drop_collection()

    def test_update_post(self):
        a = Author.objects.create(
            id='1',
            name='Randall Munroe',
            slug='randall-munroe',
        )
        res = self.client.get('/edit/author/%s/update/' % a.pk)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(isinstance(res.context['form'], forms.DocumentForm))
        self.assertEqual(res.context['object'], Author.objects.get(pk=a.pk))
        self.assertEqual(res.context['author'], Author.objects.get(pk=a.pk))
        self.assertTemplateUsed(res, 'views/author_form.html')

        # Modification with both POST and PUT (browser compatible)
        res = self.client.post('/edit/author/%s/update/' % a.pk,
                        {'id': '1', 'name': 'Randall Munroe (xkcd)', 'slug': 'randall-munroe'})
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, 'http://testserver/list/authors/')
        self.assertQuerysetEqual(Author.objects.all(), ['<Author: Randall Munroe (xkcd)>'])

    @expectedFailure
    def test_update_put(self):
        a = Author.objects.create(
            id='1',
            name='Randall Munroe',
            slug='randall-munroe',
        )
        res = self.client.get('/edit/author/%s/update/' % a.pk)
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'views/author_form.html')

        res = self.client.put('/edit/author/%s/update/' % a.pk,
                        {'name': 'Randall Munroe (author of xkcd)', 'slug': 'randall-munroe'})
        # Here is the expected failure. PUT data are not processed in any special
        # way by django. So the request will equal to a POST without data, hence
        # the form will be invalid and redisplayed with errors (status code 200).
        # See also #12635
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, 'http://testserver/list/authors/')
        self.assertQuerysetEqual(Author.objects.all(), ['<Author: Randall Munroe (author of xkcd)>'])

    def test_update_invalid(self):
        a = Author.objects.create(
            id='1',
            name='Randall Munroe',
            slug='randall-munroe',
        )
        res = self.client.post('/edit/author/%s/update/' % a.pk,
                        {'id': '1', 'name': 'A' * 101, 'slug': 'randall-munroe'})
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'views/author_form.html')
        self.assertEqual(len(res.context['form'].errors), 1)
        self.assertQuerysetEqual(Author.objects.all(), ['<Author: Randall Munroe>'])

    def test_update_with_object_url(self):
        a = Artist.objects.create(id='1', name='Rene Magritte')
        res = self.client.post('/edit/artists/%s/update/' % a.pk,
                        {'id': '1', 'name': 'Rene Magritte'})
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, 'http://testserver/detail/artist/%s/' % a.pk)
        self.assertQuerysetEqual(Artist.objects.all(), ['<Artist: Rene Magritte>'])

    def test_update_with_redirect(self):
        a = Author.objects.create(
            id='1',
            name='Randall Munroe',
            slug='randall-munroe',
        )
        res = self.client.post('/edit/author/%s/update/redirect/' % a.pk,
                        {'id': '1', 'name': 'Randall Munroe (author of xkcd)', 'slug': 'randall-munroe'})
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, 'http://testserver/edit/authors/create/')
        self.assertQuerysetEqual(Author.objects.all(), ['<Author: Randall Munroe (author of xkcd)>'])

    def test_update_with_interpolated_redirect(self):
        a = Author.objects.create(
            id='1',
            name='Randall Munroe',
            slug='randall-munroe',
        )
        res = self.client.post('/edit/author/%s/update/interpolate_redirect/' % a.pk,
                        {'id': '1', 'name': 'Randall Munroe (author of xkcd)', 'slug': 'randall-munroe'})
        self.assertQuerysetEqual(Author.objects.all(), ['<Author: Randall Munroe (author of xkcd)>'])
        self.assertEqual(res.status_code, 302)
        pk = Author.objects.all()[0].pk
        self.assertRedirects(res, 'http://testserver/edit/author/%s/update/' % pk)

    def test_update_with_special_properties(self):
        a = Author.objects.create(
            id='1',
            name='Randall Munroe',
            slug='randall-munroe',
        )
        res = self.client.get('/edit/author/%s/update/special/' % a.pk)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(isinstance(res.context['form'], views.AuthorForm))
        self.assertEqual(res.context['object'], Author.objects.get(pk=a.pk))
        self.assertEqual(res.context['thingy'], Author.objects.get(pk=a.pk))
        self.assertFalse('author' in res.context)
        self.assertTemplateUsed(res, 'views/form.html')

        res = self.client.post('/edit/author/%s/update/special/' % a.pk,
                        {'id': '1', 'name': 'Randall Munroe (author of xkcd)', 'slug': 'randall-munroe'})
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, 'http://testserver/detail/author/%s/' % a.pk)
        self.assertQuerysetEqual(Author.objects.all(), ['<Author: Randall Munroe (author of xkcd)>'])

    def test_update_without_redirect(self):
        try:
            a = Author.objects.create(
                id='1',
                name='Randall Munroe',
                slug='randall-munroe',
            )
            res = self.client.post('/edit/author/%s/update/naive/' % a.pk,
                            {'id': '1', 'name': 'Randall Munroe (author of xkcd)', 'slug': 'randall-munroe'})
            self.fail('Should raise exception -- No redirect URL provided, and no get_absolute_url provided')
        except ImproperlyConfigured:
            pass

    def test_update_get_object(self):
        a = Author.objects.create(
            pk='1',
            name='Randall Munroe',
            slug='randall-munroe',
        )
        res = self.client.get('/edit/author/update/')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(isinstance(res.context['form'], forms.DocumentForm))
        self.assertEqual(res.context['object'], Author.objects.get(pk=a.pk))
        self.assertEqual(res.context['author'], Author.objects.get(pk=a.pk))
        self.assertTemplateUsed(res, 'views/author_form.html')

        # Modification with both POST and PUT (browser compatible)
        res = self.client.post('/edit/author/update/',
                        {'id': '1', 'name': 'Randall Munroe (xkcd)', 'slug': 'randall-munroe'})
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, 'http://testserver/list/authors/')
        self.assertQuerysetEqual(Author.objects.all(), ['<Author: Randall Munroe (xkcd)>'])


class DeleteViewTests(TestCase):
    urls = 'tests.views.urls'

    def setUp(self):
        Author.drop_collection()

    def test_delete_by_post(self):
        a = Author.objects.create(**{'id': '1', 'name': 'Randall Munroe', 'slug': 'randall-munroe'})
        res = self.client.get('/edit/author/%s/delete/' % a.pk)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], Author.objects.get(pk=a.pk))
        self.assertEqual(res.context['author'], Author.objects.get(pk=a.pk))
        self.assertTemplateUsed(res, 'views/author_confirm_delete.html')

        # Deletion with POST
        res = self.client.post('/edit/author/%s/delete/' % a.pk)
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, 'http://testserver/list/authors/')
        self.assertQuerysetEqual(Author.objects.all(), [])

    def test_delete_by_delete(self):
        # Deletion with browser compatible DELETE method
        a = Author.objects.create(**{'id': '1', 'name': 'Randall Munroe', 'slug': 'randall-munroe'})
        res = self.client.delete('/edit/author/%s/delete/' % a.pk)
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, 'http://testserver/list/authors/')
        self.assertQuerysetEqual(Author.objects.all(), [])

    def test_delete_with_redirect(self):
        a = Author.objects.create(**{'id': '1', 'name': 'Randall Munroe', 'slug': 'randall-munroe'})
        res = self.client.post('/edit/author/%s/delete/redirect/' % a.pk)
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, 'http://testserver/edit/authors/create/')
        self.assertQuerysetEqual(Author.objects.all(), [])

    def test_delete_with_special_properties(self):
        a = Author.objects.create(**{'id': '1', 'name': 'Randall Munroe', 'slug': 'randall-munroe'})
        res = self.client.get('/edit/author/%s/delete/special/' % a.pk)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['object'], Author.objects.get(pk=a.pk))
        self.assertEqual(res.context['thingy'], Author.objects.get(pk=a.pk))
        self.assertFalse('author' in res.context)
        self.assertTemplateUsed(res, 'views/confirm_delete.html')

        res = self.client.post('/edit/author/%s/delete/special/' % a.pk)
        self.assertEqual(res.status_code, 302)
        self.assertRedirects(res, 'http://testserver/list/authors/')
        self.assertQuerysetEqual(Author.objects.all(), [])

    def test_delete_without_redirect(self):
        try:
            a = Author.objects.create(
                id='1',
                name='Randall Munroe',
                slug='randall-munroe',
            )
            res = self.client.post('/edit/author/%s/delete/naive/' % a.pk)
            self.fail('Should raise exception -- No redirect URL provided, and no get_absolute_url provided')
        except ImproperlyConfigured:
            pass


########NEW FILE########
__FILENAME__ = forms
from __future__ import absolute_import

from django_mongoengine import forms

from .models import Author


class AuthorForm(forms.DocumentForm):
    name = forms.CharField()
    slug = forms.SlugField()

    class Meta:
        document = Author

########NEW FILE########
__FILENAME__ = list
from __future__ import absolute_import

from django.core.exceptions import ImproperlyConfigured

from .tests import TestCase
from .models import Author, Artist


class ListViewTests(TestCase):
    urls = 'tests.views.urls'

    def test_items(self):
        res = self.client.get('/list/dict/')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'views/list.html')
        self.assertEqual(res.context['object_list'][0]['first'], 'John')

    def test_queryset(self):
        res = self.client.get('/list/authors/')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'views/author_list.html')
        self.assertEqual(list(res.context['object_list']), list(Author.objects.all()))
        self.assertIs(res.context['author_list'], res.context['object_list'])
        self.assertIsNone(res.context['paginator'])
        self.assertIsNone(res.context['page_obj'])
        self.assertFalse(res.context['is_paginated'])

    def test_paginated_queryset(self):
        self._make_authors(100)
        res = self.client.get('/list/authors/paginated/')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'views/author_list.html')
        self.assertEqual(len(res.context['object_list']), 30)
        self.assertIs(res.context['author_list'], res.context['object_list'])
        self.assertTrue(res.context['is_paginated'])
        self.assertEqual(res.context['page_obj'].number, 1)
        self.assertEqual(res.context['paginator'].num_pages, 4)
        self.assertEqual(res.context['author_list'][0].name, 'Author 00')
        self.assertEqual(list(res.context['author_list'])[-1].name, 'Author 29')

    def test_paginated_queryset_shortdata(self):
        # Test that short datasets ALSO result in a paginated view.
        res = self.client.get('/list/authors/paginated/')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'views/author_list.html')
        self.assertEqual(list(res.context['object_list']), list(Author.objects.all()))
        self.assertIs(res.context['author_list'], res.context['object_list'])
        self.assertEqual(res.context['page_obj'].number, 1)
        self.assertEqual(res.context['paginator'].num_pages, 1)
        self.assertFalse(res.context['is_paginated'])

    def test_paginated_get_page_by_query_string(self):
        self._make_authors(100)
        res = self.client.get('/list/authors/paginated/', {'page': '2'})
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'views/author_list.html')
        self.assertEqual(len(res.context['object_list']), 30)
        self.assertIs(res.context['author_list'], res.context['object_list'])
        self.assertEqual(res.context['author_list'][0].name, 'Author 30')
        self.assertEqual(res.context['page_obj'].number, 2)

    def test_paginated_get_last_page_by_query_string(self):
        self._make_authors(100)
        res = self.client.get('/list/authors/paginated/', {'page': 'last'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.context['object_list']), 10)
        self.assertIs(res.context['author_list'], res.context['object_list'])
        self.assertEqual(res.context['author_list'][0].name, 'Author 90')
        self.assertEqual(res.context['page_obj'].number, 4)

    def test_paginated_get_page_by_urlvar(self):
        self._make_authors(100)
        res = self.client.get('/list/authors/paginated/3/')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'views/author_list.html')
        self.assertEqual(len(res.context['object_list']), 30)
        self.assertIs(res.context['author_list'], res.context['object_list'])
        self.assertEqual(res.context['author_list'][0].name, 'Author 60')
        self.assertEqual(res.context['page_obj'].number, 3)

    def test_paginated_page_out_of_range(self):
        self._make_authors(100)
        res = self.client.get('/list/authors/paginated/42/')
        self.assertEqual(res.status_code, 404)

    def test_paginated_invalid_page(self):
        self._make_authors(100)
        res = self.client.get('/list/authors/paginated/?page=frog')
        self.assertEqual(res.status_code, 404)

    def test_paginated_custom_paginator_class(self):
        self._make_authors(7)
        res = self.client.get('/list/authors/paginated/custom_class/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['paginator'].num_pages, 1)
        # Custom pagination allows for 2 orphans on a page size of 5
        self.assertEqual(len(res.context['object_list']), 7)

    def test_paginated_custom_paginator_constructor(self):
        self._make_authors(7)
        res = self.client.get('/list/authors/paginated/custom_constructor/')
        self.assertEqual(res.status_code, 200)
        # Custom pagination allows for 2 orphans on a page size of 5
        self.assertEqual(len(res.context['object_list']), 7)

    def test_paginated_non_queryset(self):
        res = self.client.get('/list/dict/paginated/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.context['object_list']), 1)

    def test_verbose_name(self):
        res = self.client.get('/list/artists/')
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'views/list.html')
        self.assertEqual(list(res.context['object_list']), list(Artist.objects.all()))
        self.assertIs(res.context['artist_list'], res.context['object_list'])
        self.assertIsNone(res.context['paginator'])
        self.assertIsNone(res.context['page_obj'])
        self.assertFalse(res.context['is_paginated'])

    def test_allow_empty_false(self):
        res = self.client.get('/list/authors/notempty/')
        self.assertEqual(res.status_code, 200)
        Author.objects.all().delete()
        res = self.client.get('/list/authors/notempty/')
        self.assertEqual(res.status_code, 404)

    def test_template_name(self):
        res = self.client.get('/list/authors/template_name/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['object_list']), list(Author.objects.all()))
        self.assertIs(res.context['author_list'], res.context['object_list'])
        self.assertTemplateUsed(res, 'views/list.html')

    def test_template_name_suffix(self):
        res = self.client.get('/list/authors/template_name_suffix/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['object_list']), list(Author.objects.all()))
        self.assertIs(res.context['author_list'], res.context['object_list'])
        self.assertTemplateUsed(res, 'views/author_objects.html')

    def test_context_object_name(self):
        res = self.client.get('/list/authors/context_object_name/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['object_list']), list(Author.objects.all()))
        self.assertNotIn('authors', res.context)
        self.assertIs(res.context['author_list'], res.context['object_list'])
        self.assertTemplateUsed(res, 'views/author_list.html')

    def test_duplicate_context_object_name(self):
        res = self.client.get('/list/authors/dupe_context_object_name/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(list(res.context['object_list']), list(Author.objects.all()))
        self.assertNotIn('authors', res.context)
        self.assertNotIn('author_list', res.context)
        self.assertTemplateUsed(res, 'views/author_list.html')

    def test_missing_items(self):
        self.assertRaises(ImproperlyConfigured, self.client.get, '/list/authors/invalid/')

    def _make_authors(self, n):
        Author.objects.all().delete()
        for i in range(n):
            Author.objects.create(id='%s' % i, name='Author %02i' % i, slug='a%s' % i)


########NEW FILE########
__FILENAME__ = models
from bson import ObjectId
from django.db.models import permalink

from django_mongoengine import Document
from django_mongoengine import fields


class Artist(Document):
    id = fields.StringField(primary_key=True, default=ObjectId)
    name = fields.StringField(max_length=100)

    class Meta:
        ordering = ['name'],
        verbose_name = 'professional artist',
        verbose_name_plural = 'professional artists'

    def __unicode__(self):
        return self.name

    @permalink
    def get_absolute_url(self):
        return ('artist_detail', (), {'pk': self.id})


class Author(Document):
    id = fields.StringField(primary_key=True, default=ObjectId)
    name = fields.StringField(max_length=100)
    slug = fields.StringField()

    _meta = {
        "ordering": ['name'],
        "exclude": 'id'
    }

    def __unicode__(self):
        return self.name


class Book(Document):
    id = fields.StringField(primary_key=True, default=ObjectId)
    name = fields.StringField(max_length=300)
    slug = fields.StringField()
    pages = fields.IntField()
    authors = fields.ListField(fields.ReferenceField(Author))
    pubdate = fields.DateTimeField()

    _meta = {
        "ordering": ['-pubdate']
    }

    def __unicode__(self):
        return self.name


class Page(Document):
    id = fields.StringField(primary_key=True, default=ObjectId)
    content = fields.StringField()
    template = fields.StringField(max_length=300)

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from __future__ import absolute_import

import datetime
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

from django import test
test.utils.setup_test_environment()

from django_mongoengine.tests import MongoTestCase

from .models import Artist, Author, Book, Page


class TestCase(MongoTestCase):

    def _fixture_setup(self):
        Artist.drop_collection()
        Author.drop_collection()
        Book.drop_collection()
        Page.drop_collection()

        Artist(id="1", name="Rene Magritte").save()

        Author(id="1", name=u"Roberto Bolaño", slug="roberto-bolano").save()
        scott = Author(id="2", name="Scott Rosenberg", slug="scott-rosenberg").save()

        Book(**{
            "id": "1",
            "name": "2066",
            "slug": "2066",
            "pages": "800",
            "authors": [scott],
            "pubdate": datetime.datetime(2008, 10, 01)
        }).save()

        Book(**{
            "id": "2",
            "name": "Dreaming in Code",
            "slug": "dreaming-in-code",
            "pages": "300",
            "pubdate": datetime.datetime(2006, 05, 01)
        }).save()

        Page(**{
            "id": "1",
            "template": "views/page_template.html",
            "content": "I was once bitten by a moose."
        }).save()


from .base import ViewTest, TemplateViewTest, RedirectViewTest
from .detail import DetailViewTest
from .edit import (FormMixinTests, ModelFormMixinTests, CreateViewTests,
    UpdateViewTests, DeleteViewTests)
from .list import ListViewTests

########NEW FILE########
__FILENAME__ = urls
from __future__ import absolute_import

from django.conf.urls import patterns, url
from django.views.decorators.cache import cache_page

from django_mongoengine.views import TemplateView

from . import views

urlpatterns = patterns('',

    # TemplateView
    (r'^template/no_template/$',
        TemplateView.as_view()),
    (r'^template/simple/(?P<foo>\w+)/$',
        TemplateView.as_view(template_name='views/about.html')),
    (r'^template/custom/(?P<foo>\w+)/$',
        views.CustomTemplateView.as_view(template_name='views/about.html')),

    (r'^template/cached/(?P<foo>\w+)/$',
        cache_page(2.0)(TemplateView.as_view(template_name='views/about.html'))),

    # DetailView
    (r'^detail/obj/$',
        views.ObjectDetail.as_view()),
    url(r'^detail/artist/(?P<pk>\d+)/$',
        views.ArtistDetail.as_view(),
        name="artist_detail"),
    url(r'^detail/author/(?P<pk>\d+)/$',
        views.AuthorDetail.as_view(),
        name="author_detail"),
    (r'^detail/author/bycustompk/(?P<foo>\d+)/$',
        views.AuthorDetail.as_view(pk_url_kwarg='foo')),
    (r'^detail/author/byslug/(?P<slug>[\w-]+)/$',
        views.AuthorDetail.as_view()),
    (r'^detail/author/bycustomslug/(?P<foo>[\w-]+)/$',
        views.AuthorDetail.as_view(slug_url_kwarg='foo')),
    (r'^detail/author/(?P<pk>\d+)/template_name_suffix/$',
        views.AuthorDetail.as_view(template_name_suffix='_view')),
    (r'^detail/author/(?P<pk>\d+)/template_name/$',
        views.AuthorDetail.as_view(template_name='views/about.html')),
    (r'^detail/author/(?P<pk>\d+)/context_object_name/$',
        views.AuthorDetail.as_view(context_object_name='thingy')),
    (r'^detail/author/(?P<pk>\d+)/dupe_context_object_name/$',
        views.AuthorDetail.as_view(context_object_name='object')),
    (r'^detail/page/(?P<pk>\d+)/field/$',
        views.PageDetail.as_view()),
    (r'^detail/author/invalid/url/$',
        views.AuthorDetail.as_view()),
    (r'^detail/author/invalid/qs/$',
        views.AuthorDetail.as_view(queryset=None)),

    # Create/UpdateView
    (r'^edit/artists/create/$',
        views.ArtistCreate.as_view()),
    (r'^edit/artists/(?P<pk>\d+)/update/$',
        views.ArtistUpdate.as_view()),

    (r'^edit/authors/create/naive/$',
        views.NaiveAuthorCreate.as_view()),
    (r'^edit/authors/create/redirect/$',
        views.NaiveAuthorCreate.as_view(success_url='/edit/authors/create/')),
    (r'^edit/authors/create/interpolate_redirect/$',
        views.NaiveAuthorCreate.as_view(success_url='/edit/author/%(id)s/update/')),
    (r'^edit/authors/create/$',
        views.AuthorCreate.as_view()),
    (r'^edit/authors/create/special/$',
        views.SpecializedAuthorCreate.as_view()),

    (r'^edit/author/(?P<pk>\d+)/update/naive/$',
        views.NaiveAuthorUpdate.as_view()),
    (r'^edit/author/(?P<pk>\d+)/update/redirect/$',
        views.NaiveAuthorUpdate.as_view(success_url='/edit/authors/create/')),
    (r'^edit/author/(?P<pk>\d+)/update/interpolate_redirect/$',
        views.NaiveAuthorUpdate.as_view(success_url='/edit/author/%(id)s/update/')),
    (r'^edit/author/(?P<pk>\d+)/update/$',
        views.AuthorUpdate.as_view()),
    (r'^edit/author/update/$',
        views.OneAuthorUpdate.as_view()),
    (r'^edit/author/(?P<pk>\d+)/update/special/$',
        views.SpecializedAuthorUpdate.as_view()),
    (r'^edit/author/(?P<pk>\d+)/delete/naive/$',
        views.NaiveAuthorDelete.as_view()),
    (r'^edit/author/(?P<pk>\d+)/delete/redirect/$',
        views.NaiveAuthorDelete.as_view(success_url='/edit/authors/create/')),
    (r'^edit/author/(?P<pk>\d+)/delete/$',
        views.AuthorDelete.as_view()),
    (r'^edit/author/(?P<pk>\d+)/delete/special/$',
        views.SpecializedAuthorDelete.as_view()),

    # ListView
    (r'^list/dict/$',
        views.DictList.as_view()),
    (r'^list/dict/paginated/$',
        views.DictList.as_view(paginate_by=1)),
    url(r'^list/artists/$',
        views.ArtistList.as_view(),
        name="artists_list"),
    url(r'^list/authors/$',
        views.AuthorList.as_view(),
        name="authors_list"),
    (r'^list/authors/paginated/$',
        views.AuthorList.as_view(paginate_by=30)),
    (r'^list/authors/paginated/(?P<page>\d+)/$',
        views.AuthorList.as_view(paginate_by=30)),
    (r'^list/authors/notempty/$',
        views.AuthorList.as_view(allow_empty=False)),
    (r'^list/authors/template_name/$',
        views.AuthorList.as_view(template_name='views/list.html')),
    (r'^list/authors/template_name_suffix/$',
        views.AuthorList.as_view(template_name_suffix='_objects')),
    (r'^list/authors/context_object_name/$',
        views.AuthorList.as_view(context_object_name='author_list')),
    (r'^list/authors/dupe_context_object_name/$',
        views.AuthorList.as_view(context_object_name='object_list')),
    (r'^list/authors/invalid/$',
        views.AuthorList.as_view(queryset=None)),
    (r'^list/authors/paginated/custom_class/$',
        views.AuthorList.as_view(paginate_by=5, paginator_class=views.CustomPaginator)),
    (r'^list/authors/paginated/custom_constructor/$',
        views.AuthorListCustomPaginator.as_view()),

)

########NEW FILE########
__FILENAME__ = views
from __future__ import absolute_import

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.utils.decorators import method_decorator

from django_mongoengine import views

from .forms import AuthorForm
from .models import Artist, Author, Book, Page


class CustomTemplateView(views.TemplateView):
    template_name = 'views/about.html'

    def get_context_data(self, **kwargs):
        return {
            'params': kwargs,
            'key': 'value'
        }


class ObjectDetail(views.DetailView):
    template_name = 'views/detail.html'

    def get_object(self):
        return {'foo': 'bar'}


class ArtistDetail(views.DetailView):
    queryset = Artist.objects.all()


class AuthorDetail(views.DetailView):
    queryset = Author.objects.all()


class PageDetail(views.DetailView):
    queryset = Page.objects.all()
    template_name_field = 'template'


class DictList(views.ListView):
    """A ListView that doesn't use a model."""
    queryset = [
        {'first': 'John', 'last': 'Lennon'},
        {'first': 'Yoko',  'last': 'Ono'}
    ]
    template_name = 'views/list.html'


class ArtistList(views.ListView):
    template_name = 'views/list.html'
    queryset = Artist.objects.all()


class AuthorList(views.ListView):
    queryset = Author.objects.all().order_by('name')


class CustomPaginator(Paginator):
    def __init__(self, queryset, page_size, orphans=0, allow_empty_first_page=True):
        super(CustomPaginator, self).__init__(
            queryset,
            page_size,
            orphans=2,
            allow_empty_first_page=allow_empty_first_page)

class AuthorListCustomPaginator(AuthorList):
    paginate_by = 5

    def get_paginator(self, queryset, page_size, orphans=0, allow_empty_first_page=True):
        return super(AuthorListCustomPaginator, self).get_paginator(
            queryset,
            page_size,
            orphans=2,
            allow_empty_first_page=allow_empty_first_page)

class ArtistCreate(views.CreateView):
    document = Artist


class NaiveAuthorCreate(views.CreateView):
    queryset = Author.objects.all()


class AuthorCreate(views.CreateView):
    document = Author
    success_url = '/list/authors/'


class SpecializedAuthorCreate(views.CreateView):
    document = Author
    form_class = AuthorForm
    template_name = 'views/form.html'
    context_object_name = 'thingy'

    def get_success_url(self):
        return reverse('author_detail', args=[self.object.id,])


class AuthorCreateRestricted(AuthorCreate):
    post = method_decorator(login_required)(AuthorCreate.post)


class ArtistUpdate(views.UpdateView):
    document = Artist


class NaiveAuthorUpdate(views.UpdateView):
    queryset = Author.objects.all()


class AuthorUpdate(views.UpdateView):
    document = Author
    success_url = '/list/authors/'


class OneAuthorUpdate(views.UpdateView):
    success_url = '/list/authors/'

    def get_object(self):
        return Author.objects.get(pk='1')


class SpecializedAuthorUpdate(views.UpdateView):
    document = Author
    form_class = AuthorForm
    template_name = 'views/form.html'
    context_object_name = 'thingy'

    def get_success_url(self):
        return reverse('author_detail', args=[self.object.id])


class NaiveAuthorDelete(views.DeleteView):
    queryset = Author.objects.all()


class AuthorDelete(views.DeleteView):
    document = Author
    success_url = '/list/authors/'


class SpecializedAuthorDelete(views.DeleteView):
    queryset = Author.objects.all()
    template_name = 'views/confirm_delete.html'
    context_object_name = 'thingy'

    def get_success_url(self):
        return reverse('authors_list')


class AuthorGetQuerySetFormView(views.edit.DocumentFormMixin):
    def get_queryset(self):
        return Author.objects.all()

########NEW FILE########
