__FILENAME__ = base
def from_iterable(iterables):
    """
    Backport of `itertools.chain.from_iterable` compatible with Python 2.5
    """
    for it in iterables:
        for element in it:
            if isinstance(element, dict):
                for key in element:
                    yield key
            else:
                yield element


class KeepContext(object):
    """
    Context manager that receives a `django.template.Context` instance and a list of keys

    Once the context manager is exited, it removes `keys` from the context, to avoid
    side effects in later layout objects that may use the same context variables.

    Layout objects should use `extra_context` to introduce context variables, never
    touch context object themselves, that could introduce side effects.
    """
    def __init__(self, context, keys):
        self.context = context
        self.keys = keys

    def __enter__(self):
        pass

    def __exit__(self, type, value, traceback):
        for key in list(self.keys):
            del self.context[key]

########NEW FILE########
__FILENAME__ = bootstrap
from random import randint

from django.template import Context, Template
from django.template.loader import render_to_string
from django.template.defaultfilters import slugify

from .compatibility import text_type
from .layout import LayoutObject, Field, Div
from .utils import render_field, flatatt, TEMPLATE_PACK



class PrependedAppendedText(Field):
    template = "%s/layout/prepended_appended_text.html"

    def __init__(self, field, prepended_text=None, appended_text=None, *args, **kwargs):
        self.field = field
        self.appended_text = appended_text
        self.prepended_text = prepended_text
        if 'active' in kwargs:
            self.active = kwargs.pop('active')

        self.input_size = None
        css_class = kwargs.get('css_class', '')
        if css_class.find('input-lg') != -1: self.input_size = 'input-lg'
        if css_class.find('input-sm') != -1: self.input_size = 'input-sm'

        super(PrependedAppendedText, self).__init__(field, *args, **kwargs)

    def render(self, form, form_style, context, template_pack=TEMPLATE_PACK, extra_context=None, **kwargs):
        extra_context = {
            'crispy_appended_text': self.appended_text,
            'crispy_prepended_text': self.prepended_text,
            'input_size' : self.input_size,
            'active': getattr(self, "active", False)
        }
        template = self.template % template_pack
        return render_field(
            self.field, form, form_style, context,
            template=template, attrs=self.attrs,
            template_pack=template_pack, extra_context=extra_context, **kwargs
        )


class AppendedText(PrependedAppendedText):
    def __init__(self, field, text, *args, **kwargs):
        kwargs.pop('appended_text', None)
        kwargs.pop('prepended_text', None)
        self.text = text
        super(AppendedText, self).__init__(field, appended_text=text, **kwargs)


class PrependedText(PrependedAppendedText):
    def __init__(self, field, text, *args, **kwargs):
        kwargs.pop('appended_text', None)
        kwargs.pop('prepended_text', None)
        self.text = text
        super(PrependedText, self).__init__(field, prepended_text=text, **kwargs)


class FormActions(LayoutObject):
    """
    Bootstrap layout object. It wraps fields in a <div class="form-actions">

    Example::

        FormActions(
            HTML(<span style="display: hidden;">Information Saved</span>),
            Submit('Save', 'Save', css_class='btn-primary')
        )
    """
    template = "%s/layout/formactions.html"

    def __init__(self, *fields, **kwargs):
        self.fields = list(fields)
        self.template = kwargs.pop('template', self.template)
        self.attrs = kwargs
        if 'css_class' in self.attrs:
            self.attrs['class'] = self.attrs.pop('css_class')

    def render(self, form, form_style, context, template_pack=TEMPLATE_PACK, **kwargs):
        html = u''
        for field in self.fields:
            html += render_field(field, form, form_style, context, template_pack=template_pack, **kwargs)
        extra_context = {
            'formactions': self,
            'fields_output': html
        }
        template = self.template % template_pack
        return render_to_string(template, extra_context, context)

    def flat_attrs(self):
        return flatatt(self.attrs)


class InlineCheckboxes(Field):
    """
    Layout object for rendering checkboxes inline::

        InlineCheckboxes('field_name')
    """
    template = "%s/layout/checkboxselectmultiple_inline.html"

    def render(self, form, form_style, context, template_pack=TEMPLATE_PACK, **kwargs):
        return super(InlineCheckboxes, self).render(
            form, form_style, context, template_pack=template_pack,
            extra_context={'inline_class': 'inline'}
        )


class InlineRadios(Field):
    """
    Layout object for rendering radiobuttons inline::

        InlineRadios('field_name')
    """
    template = "%s/layout/radioselect_inline.html"

    def render(self, form, form_style, context, template_pack=TEMPLATE_PACK, **kwargs):
        return super(InlineRadios, self).render(
            form, form_style, context, template_pack=template_pack,
            extra_context={'inline_class': 'inline'}
        )


class FieldWithButtons(Div):
    template = '%s/layout/field_with_buttons.html'
    field_template = '%s/layout/field.html'

    def render(self, form, form_style, context, template_pack=TEMPLATE_PACK, extra_context=None, **kwargs):
        # We first render the buttons
        buttons = ''
        field_template = self.field_template % template_pack
        for field in self.fields[1:]:
            buttons += render_field(
                field, form, form_style, context,
                field_template, layout_object=self,
                template_pack=template_pack, **kwargs
            )

        extra_context = {'div': self, 'buttons': buttons}
        template = self.template % template_pack

        if isinstance(self.fields[0], Field):
            # FieldWithButtons(Field('field_name'), StrictButton("go"))
            # We render the field passing its name and attributes
            return render_field(
                self.fields[0][0], form, form_style, context,
                template, attrs=self.fields[0].attrs,
                template_pack=template_pack, extra_context=extra_context, **kwargs
            )
        else:
            return render_field(
                self.fields[0], form, form_style, context, template,
                extra_context=extra_context, **kwargs
            )


class StrictButton(object):
    """
    Layout oject for rendering an HTML button::

        Button("button content", css_class="extra")
    """
    template = '%s/layout/button.html'
    field_classes = 'btn'

    def __init__(self, content, **kwargs):
        self.content = content
        self.template = kwargs.pop('template', self.template)

        kwargs.setdefault('type', 'button')

        # We turn css_id and css_class into id and class
        if 'css_id' in kwargs:
            kwargs['id'] = kwargs.pop('css_id')
        kwargs['class'] = self.field_classes
        if 'css_class' in kwargs:
            kwargs['class'] += " %s" % kwargs.pop('css_class')

        self.flat_attrs = flatatt(kwargs)

    def render(self, form, form_style, context, template_pack=TEMPLATE_PACK, **kwargs):
        self.content = Template(text_type(self.content)).render(context)
        template = self.template % template_pack
        return render_to_string(template, {'button': self}, context)


class Container(Div):
    """
    Base class used for `Tab` and `AccordionGroup`, represents a basic container concept
    """
    css_class = ""

    def __init__(self, name, *fields, **kwargs):
        super(Container, self).__init__(*fields, **kwargs)
        self.template = kwargs.pop('template', self.template)
        self.name = name
        self._active_originally_included = "active" in kwargs
        self.active = kwargs.pop("active", False)
        if not self.css_id:
            self.css_id = slugify(self.name)

    def __contains__(self, field_name):
        """
        check if field_name is contained within tab.
        """
        return field_name in map(lambda pointer: pointer[1], self.get_field_names())

    def render(self, form, form_style, context, template_pack=TEMPLATE_PACK, **kwargs):
        if self.active:
            if not 'active' in self.css_class:
                self.css_class += ' active'
        else:
            self.css_class = self.css_class.replace('active', '')
        return super(Container, self).render(form, form_style, context, template_pack)


class ContainerHolder(Div):
    """
    Base class used for `TabHolder` and `Accordion`, groups containers
    """
    def first_container_with_errors(self, errors):
        """
        Returns the first container with errors, otherwise returns None.
        """
        for tab in self.fields:
            errors_here = any(error in tab for error in errors)
            if errors_here:
                return tab
        return None

    def open_target_group_for_form(self, form):
        """
        Makes sure that the first group that should be open is open.
        This is either the first group with errors or the first group
        in the container, unless that first group was originally set to
        active=False.
        """
        target = self.first_container_with_errors(form.errors.keys())
        if target is None:
            target = self.fields[0]
            if not target._active_originally_included:
                target.active = True
            return target

        target.active = True
        return target


class Tab(Container):
    """
    Tab object. It wraps fields in a div whose default class is "tab-pane" and
    takes a name as first argument. Example::

        Tab('tab_name', 'form_field_1', 'form_field_2', 'form_field_3')
    """
    css_class = 'tab-pane'
    link_template = '%s/layout/tab-link.html'

    def render_link(self, template_pack=TEMPLATE_PACK, **kwargs):
        """
        Render the link for the tab-pane. It must be called after render so css_class is updated
        with active if needed.
        """
        link_template = self.link_template % template_pack
        return render_to_string(link_template, {'link': self})


class TabHolder(ContainerHolder):
    """
    TabHolder object. It wraps Tab objects in a container. Requires bootstrap-tab.js::

        TabHolder(
            Tab('form_field_1', 'form_field_2'),
            Tab('form_field_3')
        )
    """
    template = '%s/layout/tab.html'

    def render(self, form, form_style, context, template_pack=TEMPLATE_PACK, **kwargs):
        links, content = '', ''
        for tab in self.fields:
            tab.active = False

        # Open the group that should be open.
        self.open_target_group_for_form(form)

        for tab in self.fields:
            content += render_field(
                tab, form, form_style, context, template_pack=template_pack, **kwargs
            )
            links += tab.render_link(template_pack)

        extra_context = {
            'tabs': self,
            'links': links,
            'content': content
        }
        template = self.template % template_pack
        return render_to_string(template, extra_context, context)


class AccordionGroup(Container):
    """
    Accordion Group (pane) object. It wraps given fields inside an accordion
    tab. It takes accordion tab name as first argument::

        AccordionGroup("group name", "form_field_1", "form_field_2")
    """
    template = "%s/accordion-group.html"
    data_parent = ""  # accordion parent div id.


class Accordion(ContainerHolder):
    """
    Accordion menu object. It wraps `AccordionGroup` objects in a container::

        Accordion(
            AccordionGroup("group name", "form_field_1", "form_field_2"),
            AccordionGroup("another group name", "form_field")
        )
    """
    template = "%s/accordion.html"

    def render(self, form, form_style, context, template_pack=TEMPLATE_PACK, **kwargs):
        content = ''

        # accordion group needs the parent div id to set `data-parent` (I don't
        # know why). This needs to be a unique id
        if not self.css_id:
            self.css_id = "-".join(["accordion", text_type(randint(1000, 9999))])

        # Open the group that should be open.
        self.open_target_group_for_form(form)

        for group in self.fields:
            group.data_parent = self.css_id
            content += render_field(
                group, form, form_style, context, template_pack=template_pack, **kwargs
            )

        template = self.template % template_pack
        return render_to_string(
            template,
            {'accordion': self, 'content': content},
            context
        )


class Alert(Div):
    """
    `Alert` generates markup in the form of an alert dialog

        Alert(content='<strong>Warning!</strong> Best check yo self, you're not looking too good.')
    """
    template = "%s/layout/alert.html"
    css_class = "alert"

    def __init__(self, content, dismiss=True, block=False, **kwargs):
        fields = []
        if block:
            self.css_class += ' alert-block'
        Div.__init__(self, *fields, **kwargs)
        self.template = kwargs.pop('template', self.template)
        self.content = content
        self.dismiss = dismiss

    def render(self, form, form_style, context, template_pack=TEMPLATE_PACK, **kwargs):
        template = self.template % template_pack
        return render_to_string(
            template,
            {'alert': self, 'content': self.content, 'dismiss': self.dismiss},
            context
        )


class UneditableField(Field):
    """
    Layout object for rendering fields as uneditable in bootstrap

    Example::

        UneditableField('field_name', css_class="input-xlarge")
    """
    template = "%s/layout/uneditable_input.html"

    def __init__(self, field, *args, **kwargs):
        self.attrs = {'class': 'uneditable-input'}
        super(UneditableField, self).__init__(field, *args, **kwargs)


class InlineField(Field):
    template = "%s/layout/inline_field.html"

########NEW FILE########
__FILENAME__ = compatibility
import sys


PY2 = sys.version_info[0] == 2
if not PY2:
    text_type = str
    binary_type = bytes
    string_types = (str,)
    integer_types = (int,)
else:
    text_type = unicode
    binary_type = str
    string_types = basestring
    integer_types = (int, long)

########NEW FILE########
__FILENAME__ = exceptions
class CrispyError(Exception):
    pass


class FormHelpersException(CrispyError):
    """
    This is raised when building a form via helpers throws an error.
    We want to catch form helper errors as soon as possible because
    debugging templatetags is never fun.
    """
    pass


class DynamicError(CrispyError):
    pass

########NEW FILE########
__FILENAME__ = helper
# -*- coding: utf-8 -*-
import re

from django.core.urlresolvers import reverse, NoReverseMatch
from django.utils.safestring import mark_safe

from crispy_forms.compatibility import string_types
from crispy_forms.layout import Layout
from crispy_forms.layout_slice import LayoutSlice
from crispy_forms.utils import render_field, flatatt, TEMPLATE_PACK
from crispy_forms.exceptions import FormHelpersException


class DynamicLayoutHandler(object):
    def _check_layout(self):
        if self.layout is None:
            raise FormHelpersException("You need to set a layout in your FormHelper")

    def _check_layout_and_form(self):
        self._check_layout()
        if self.form is None:
            raise FormHelpersException("You need to pass a form instance to your FormHelper")

    def all(self):
        """
        Returns all layout objects of first level of depth
        """
        self._check_layout()
        return LayoutSlice(self.layout, slice(0, len(self.layout.fields), 1))

    def filter(self, *LayoutClasses, **kwargs):
        """
        Returns a LayoutSlice pointing to layout objects of type `LayoutClass`
        """
        self._check_layout()
        max_level = kwargs.pop('max_level', 0)
        greedy = kwargs.pop('greedy', False)
        filtered_layout_objects = self.layout.get_layout_objects(LayoutClasses, max_level=max_level, greedy=greedy)

        return LayoutSlice(self.layout, filtered_layout_objects)

    def filter_by_widget(self, widget_type):
        """
        Returns a LayoutSlice pointing to fields with widgets of `widget_type`
        """
        self._check_layout_and_form()
        layout_field_names = self.layout.get_field_names()

        # Let's filter all fields with widgets like widget_type
        filtered_fields = []
        for pointer in layout_field_names:
            if isinstance(self.form.fields[pointer[1]].widget, widget_type):
                filtered_fields.append(pointer)

        return LayoutSlice(self.layout, filtered_fields)

    def exclude_by_widget(self, widget_type):
        """
        Returns a LayoutSlice pointing to fields with widgets NOT matching `widget_type`
        """
        self._check_layout_and_form()
        layout_field_names = self.layout.get_field_names()

        # Let's exclude all fields with widgets like widget_type
        filtered_fields = []
        for pointer in layout_field_names:
            if not isinstance(self.form.fields[pointer[1]].widget, widget_type):
                filtered_fields.append(pointer)

        return LayoutSlice(self.layout, filtered_fields)

    def __getitem__(self, key):
        """
        Return a LayoutSlice that makes changes affect the current instance of the layout
        and not a copy.
        """
        # when key is a string containing the field name
        if isinstance(key, string_types):
            # Django templates access FormHelper attributes using dictionary [] operator
            # This could be a helper['form_id'] access, not looking for a field
            if hasattr(self, key):
                return getattr(self, key)

            self._check_layout()
            layout_field_names = self.layout.get_field_names()

            filtered_field = []
            for pointer in layout_field_names:
                # There can be an empty pointer
                if len(pointer) == 2 and pointer[1] == key:
                    filtered_field.append(pointer)

            return LayoutSlice(self.layout, filtered_field)

        return LayoutSlice(self.layout, key)

    def __setitem__(self, key, value):
        self.layout[key] = value

    def __delitem__(self, key):
        del self.layout.fields[key]

    def __len__(self):
        if self.layout is not None:
            return len(self.layout.fields)
        else:
            return 0


class FormHelper(DynamicLayoutHandler):
    """
    This class controls the form rendering behavior of the form passed to
    the `{% crispy %}` tag. For doing so you will need to set its attributes
    and pass the corresponding helper object to the tag::

        {% crispy form form.helper %}

    Let's see what attributes you can set and what form behaviors they apply to:

        **form_method**: Specifies form method attribute.
            You can see it to 'POST' or 'GET'. Defaults to 'POST'

        **form_action**: Applied to the form action attribute:
            - Can be a named url in your URLconf that can be executed via the `{% url %}` template tag. \
            Example: 'show_my_profile'. In your URLconf you could have something like::

                url(r'^show/profile/$', 'show_my_profile_view', name = 'show_my_profile')

            - It can simply point to a URL '/whatever/blabla/'.

        **form_id**: Generates a form id for dom identification.
            If no id provided then no id attribute is created on the form.

        **form_class**: String containing separated CSS clases to be applied
            to form class attribute. The form will always have by default
            'uniForm' class.

        **form_tag**: It specifies if <form></form> tags should be rendered when using a Layout.
            If set to False it renders the form without the <form></form> tags. Defaults to True.

        **form_error_title**: If a form has `non_field_errors` to display, they
            are rendered in a div. You can set title's div with this attribute.
            Example: "Oooops!" or "Form Errors"

        **formset_error_title**: If a formset has `non_form_errors` to display, they
            are rendered in a div. You can set title's div with this attribute.

        **form_style**: Uni-form has two built in different form styles. You can choose
            your favorite. This can be set to "default" or "inline". Defaults to "default".

    Public Methods:

        **add_input(input)**: You can add input buttons using this method. Inputs
            added using this method will be rendered at the end of the form/formset.

        **add_layout(layout)**: You can add a `Layout` object to `FormHelper`. The Layout
            specifies in a simple, clean and DRY way how the form fields should be rendered.
            You can wrap fields, order them, customize pretty much anything in the form.

    Best way to add a helper to a form is adding a property named helper to the form
    that returns customized `FormHelper` object::

        from crispy_forms.helper import FormHelper
        from crispy_forms.layout import Submit

        class MyForm(forms.Form):
            title = forms.CharField(_("Title"))

            @property
            def helper(self):
                helper = FormHelper()
                helper.form_id = 'this-form-rocks'
                helper.form_class = 'search'
                helper.add_input(Submit('save', 'save'))
                [...]
                return helper

    You can use it in a template doing::

        {% load crispy_forms_tags %}
        {% crispy form %}
    """
    _form_method = 'post'
    _form_action = ''
    _form_style = 'default'
    form = None
    form_id = ''
    form_class = ''
    layout = None
    form_tag = True
    form_error_title = None
    formset_error_title = None
    form_show_errors = True
    render_unmentioned_fields = False
    render_hidden_fields = False
    render_required_fields = False
    _help_text_inline = False
    _error_text_inline = True
    html5_required = False
    form_show_labels = True
    template = None
    field_template = None
    disable_csrf = False
    label_class = ''
    field_class = ''

    def __init__(self, form=None):
        self.attrs = {}
        self.inputs = []

        if form is not None:
            self.form = form
            self.layout = self.build_default_layout(form)

    def build_default_layout(self, form):
        return Layout(*form.fields.keys())

    def get_form_method(self):
        return self._form_method

    def set_form_method(self, method):
        if method.lower() not in ('get', 'post'):
            raise FormHelpersException('Only GET and POST are valid in the \
                    form_method helper attribute')

        self._form_method = method.lower()

    # we set properties the old way because we want to support pre-2.6 python
    form_method = property(get_form_method, set_form_method)

    def get_form_action(self):
        try:
            return reverse(self._form_action)
        except NoReverseMatch:
            return self._form_action

    def set_form_action(self, action):
        self._form_action = action

    # we set properties the old way because we want to support pre-2.6 python
    form_action = property(get_form_action, set_form_action)

    def get_form_style(self):
        if self._form_style == "default":
            return ''

        if self._form_style == "inline":
            return 'inlineLabels'

    def set_form_style(self, style):
        if style.lower() not in ('default', 'inline'):
            raise FormHelpersException('Only default and inline are valid in the \
                    form_style helper attribute')

        self._form_style = style.lower()

    form_style = property(get_form_style, set_form_style)

    def get_help_text_inline(self):
        return self._help_text_inline

    def set_help_text_inline(self, flag):
        self._help_text_inline = flag
        self._error_text_inline = not flag

    help_text_inline = property(get_help_text_inline, set_help_text_inline)

    def get_error_text_inline(self):
        return self._error_text_inline

    def set_error_text_inline(self, flag):
        self._error_text_inline = flag
        self._help_text_inline = not flag

    error_text_inline = property(get_error_text_inline, set_error_text_inline)

    def add_input(self, input_object):
        self.inputs.append(input_object)

    def add_layout(self, layout):
        self.layout = layout

    def render_layout(self, form, context, template_pack=TEMPLATE_PACK):
        """
        Returns safe html of the rendering of the layout
        """
        form.rendered_fields = set()
        form.crispy_field_template = self.field_template

        # This renders the specifed Layout strictly
        html = self.layout.render(
            form,
            self.form_style,
            context,
            template_pack=template_pack
        )

        # Rendering some extra fields if specified
        if self.render_unmentioned_fields or self.render_hidden_fields or self.render_required_fields:
            fields = set(form.fields.keys())
            left_fields_to_render = fields - form.rendered_fields
            for field in left_fields_to_render:
                if (
                    self.render_unmentioned_fields or
                    self.render_hidden_fields and form.fields[field].widget.is_hidden or
                    self.render_required_fields and form.fields[field].widget.is_required
                ):
                    html += render_field(
                        field,
                        form,
                        self.form_style,
                        context,
                        template_pack=template_pack
                    )

        # If the user has Meta.fields defined, not included in the layout,
        # we suppose they need to be rendered
        if hasattr(form, 'Meta'):
            if hasattr(form.Meta, 'fields'):
                current_fields = set(getattr(form, 'fields', []))
                meta_fields = set(getattr(form.Meta, 'fields'))

                fields_to_render = current_fields & meta_fields
                left_fields_to_render = fields_to_render - form.rendered_fields

                for field in left_fields_to_render:
                    html += render_field(field, form, self.form_style, context)

        return mark_safe(html)

    def get_attributes(self, template_pack=TEMPLATE_PACK):
        """
        Used by crispy_forms_tags to get helper attributes
        """
        items = {}
        items['form_method'] = self.form_method.strip()
        items['form_tag'] = self.form_tag
        items['form_style'] = self.form_style.strip()
        items['form_show_errors'] = self.form_show_errors
        items['help_text_inline'] = self.help_text_inline
        items['error_text_inline'] = self.error_text_inline
        items['html5_required'] = self.html5_required
        items['form_show_labels'] = self.form_show_labels
        items['disable_csrf'] = self.disable_csrf
        items['label_class'] = self.label_class
        items['field_class'] = self.field_class
        # col-[lg|md|sm|xs]-<number>
        label_size_match = re.search('(\d+)', self.label_class)
        device_type_match = re.search('(lg|md|sm|xs)', self.label_class)
        if label_size_match and device_type_match:
            try:
                items['label_size'] = int(label_size_match.groups()[0])
                items['bootstrap_device_type'] = device_type_match.groups()[0]
            except:
                pass

        items['attrs'] = {}
        if self.attrs:
            items['attrs'] = self.attrs.copy()
        if self.form_action:
            items['attrs']['action'] = self.form_action.strip()
        if self.form_id:
            items['attrs']['id'] = self.form_id.strip()
        if self.form_class:
            # uni_form TEMPLATE PACK has a uniForm class by default
            if template_pack == 'uni_form':
                items['attrs']['class'] = "uniForm %s" % self.form_class.strip()
            else:
                items['attrs']['class'] = self.form_class.strip()
        else:
            if template_pack == 'uni_form':
                items['attrs']['class'] = self.attrs.get('class', '') + " uniForm"

        items['flat_attrs'] = flatatt(items['attrs'])

        if self.inputs:
            items['inputs'] = self.inputs
        if self.form_error_title:
            items['form_error_title'] = self.form_error_title.strip()
        if self.formset_error_title:
            items['formset_error_title'] = self.formset_error_title.strip()

        for attribute_name, value in self.__dict__.items():
            if attribute_name not in items and attribute_name not in ['layout', 'inputs'] and not attribute_name.startswith('_'):
                items[attribute_name] = value

        return items

########NEW FILE########
__FILENAME__ = layout
import warnings

from django.conf import settings
from django.template import Context, Template
from django.template.loader import render_to_string
from django.utils.html import conditional_escape

from crispy_forms.compatibility import string_types, text_type
from crispy_forms.utils import render_field, flatatt

TEMPLATE_PACK = getattr(settings, 'CRISPY_TEMPLATE_PACK', 'bootstrap')


class LayoutObject(object):
    def __getitem__(self, slice):
        return self.fields[slice]

    def __setitem__(self, slice, value):
        self.fields[slice] = value

    def __delitem__(self, slice):
        del self.fields[slice]

    def __len__(self):
        return len(self.fields)

    def __getattr__(self, name):
        """
        This allows us to access self.fields list methods like append or insert, without
        having to declaee them one by one
        """
        # Check necessary for unpickling, see #107
        if 'fields' in self.__dict__ and hasattr(self.fields, name):
            return getattr(self.fields, name)
        else:
            return object.__getattribute__(self, name)

    def get_field_names(self, index=None):
        """
        Returns a list of lists, those lists are named pointers. First parameter
        is the location of the field, second one the name of the field. Example::

            [
               [[0,1,2], 'field_name1'],
               [[0,3], 'field_name2']
            ]
        """
        return self.get_layout_objects(string_types, greedy=True)

    def get_layout_objects(self, *LayoutClasses, **kwargs):
        """
        Returns a list of lists pointing to layout objects of any type matching
        `LayoutClasses`::

            [
               [[0,1,2], 'div'],
               [[0,3], 'field_name']
            ]

        :param max_level: An integer that indicates max level depth to reach when
        traversing a layout.
        :param greedy: Boolean that indicates whether to be greedy. If set, max_level
        is skipped.
        """
        index = kwargs.pop('index', None)
        max_level = kwargs.pop('max_level', 0)
        greedy = kwargs.pop('greedy', False)

        pointers = []

        if index is not None and not isinstance(index, list):
            index = [index]
        elif index is None:
            index = []

        for i, layout_object in enumerate(self.fields):
            if isinstance(layout_object, LayoutClasses):
                if len(LayoutClasses) == 1 and LayoutClasses[0] == string_types:
                    pointers.append([index + [i], layout_object])
                else:
                    pointers.append([index + [i], layout_object.__class__.__name__.lower()])

            # If it's a layout object and we haven't reached the max depth limit or greedy
            # we recursive call
            if hasattr(layout_object, 'get_field_names') and (len(index) < max_level or greedy):
                new_kwargs = {'index': index + [i], 'max_level': max_level, 'greedy': greedy}
                pointers = pointers + layout_object.get_layout_objects(*LayoutClasses, **new_kwargs)

        return pointers


class Layout(LayoutObject):
    """
    Form Layout. It is conformed by Layout objects: `Fieldset`, `Row`, `Column`, `MultiField`,
    `HTML`, `ButtonHolder`, `Button`, `Hidden`, `Reset`, `Submit` and fields. Form fields
    have to be strings.
    Layout objects `Fieldset`, `Row`, `Column`, `MultiField` and `ButtonHolder` can hold other
    Layout objects within. Though `ButtonHolder` should only hold `HTML` and BaseInput
    inherited classes: `Button`, `Hidden`, `Reset` and `Submit`.

    Example::

        helper.layout = Layout(
            Fieldset('Company data',
                'is_company'
            ),
            Fieldset(_('Contact details'),
                'email',
                Row('password1', 'password2'),
                'first_name',
                'last_name',
                HTML('<img src="/media/somepicture.jpg"/>'),
                'company'
            ),
            ButtonHolder(
                Submit('Save', 'Save', css_class='button white'),
            ),
        )
    """
    def __init__(self, *fields):
        self.fields = list(fields)

    def render(self, form, form_style, context, template_pack=TEMPLATE_PACK, **kwargs):
        html = ""
        for field in self.fields:
            html += render_field(
                field,
                form,
                form_style,
                context,
                template_pack=template_pack,
                **kwargs
            )
        return html


class ButtonHolder(LayoutObject):
    """
    Layout object. It wraps fields in a <div class="buttonHolder">

    This is where you should put Layout objects that render to form buttons like Submit.
    It should only hold `HTML` and `BaseInput` inherited objects.

    Example::

        ButtonHolder(
            HTML(<span style="display: hidden;">Information Saved</span>),
            Submit('Save', 'Save')
        )
    """
    template = "%s/layout/buttonholder.html"

    def __init__(self, *fields, **kwargs):
        self.fields = list(fields)
        self.css_class = kwargs.get('css_class', None)
        self.css_id = kwargs.get('css_id', None)
        self.template = kwargs.get('template', self.template)

    def render(self, form, form_style, context, template_pack=TEMPLATE_PACK, **kwargs):
        html = u''
        for field in self.fields:
            html += render_field(
                field, form, form_style, context, template_pack=template_pack, **kwargs
            )

        template = self.template % template_pack
        return render_to_string(
            template,
            {'buttonholder': self, 'fields_output': html},
            context
        )


class BaseInput(object):
    """
    A base class to reduce the amount of code in the Input classes.
    """
    template = "%s/layout/baseinput.html"

    def __init__(self, name, value, **kwargs):
        self.name = name
        self.value = value
        self.id = kwargs.pop('css_id', '')
        self.attrs = {}

        if 'css_class' in kwargs:
            self.field_classes += ' %s' % kwargs.pop('css_class')

        self.template = kwargs.pop('template', self.template)
        self.flat_attrs = flatatt(kwargs)

    def render(self, form, form_style, context, template_pack=TEMPLATE_PACK, **kwargs):
        """
        Renders an `<input />` if container is used as a Layout object.
        Input button value can be a variable in context.
        """
        self.value = Template(text_type(self.value)).render(context)
        template = self.template % template_pack
        return render_to_string(template, {'input': self}, context)


class Submit(BaseInput):
    """
    Used to create a Submit button descriptor for the {% crispy %} template tag::

        submit = Submit('Search the Site', 'search this site')

    .. note:: The first argument is also slugified and turned into the id for the submit button.
    """
    input_type = 'submit'
    field_classes = 'submit submitButton' if TEMPLATE_PACK == 'uni_form' else 'btn btn-primary'


class Button(BaseInput):
    """
    Used to create a Submit input descriptor for the {% crispy %} template tag::

        button = Button('Button 1', 'Press Me!')

    .. note:: The first argument is also slugified and turned into the id for the button.
    """
    input_type = 'button'
    field_classes = 'button' if TEMPLATE_PACK == 'uni_form' else 'btn'


class Hidden(BaseInput):
    """
    Used to create a Hidden input descriptor for the {% crispy %} template tag.
    """
    input_type = 'hidden'
    field_classes = 'hidden'


class Reset(BaseInput):
    """
    Used to create a Reset button input descriptor for the {% crispy %} template tag::

        reset = Reset('Reset This Form', 'Revert Me!')

    .. note:: The first argument is also slugified and turned into the id for the reset.
    """
    input_type = 'reset'
    field_classes = 'reset resetButton' if TEMPLATE_PACK == 'uni_form' else 'btn btn-inverse'


class Fieldset(LayoutObject):
    """
    Layout object. It wraps fields in a <fieldset>

    Example::

        Fieldset("Text for the legend",
            'form_field_1',
            'form_field_2'
        )

    The first parameter is the text for the fieldset legend. This text is context aware,
    so you can do things like::

        Fieldset("Data for {{ user.username }}",
            'form_field_1',
            'form_field_2'
        )
    """
    template = "%s/layout/fieldset.html"

    def __init__(self, legend, *fields, **kwargs):
        self.fields = list(fields)
        self.legend = legend
        self.css_class = kwargs.pop('css_class', '')
        self.css_id = kwargs.pop('css_id', None)
        self.template = kwargs.pop('template', self.template)
        self.flat_attrs = flatatt(kwargs)

    def render(self, form, form_style, context, template_pack=TEMPLATE_PACK, **kwargs):
        fields = ''
        for field in self.fields:
            fields += render_field(
                field, form, form_style, context, template_pack=template_pack, **kwargs
            )

        legend = ''
        if self.legend:
            legend = u'%s' % Template(text_type(self.legend)).render(context)

        template = self.template % template_pack
        return render_to_string(
            template,
            {'fieldset': self, 'legend': legend, 'fields': fields, 'form_style': form_style}
        )


class MultiField(LayoutObject):
    """ MultiField container. Renders to a MultiField <div> """
    template = "%s/layout/multifield.html"
    field_template = "%s/multifield.html"

    def __init__(self, label, *fields, **kwargs):
        self.fields = list(fields)
        self.label_html = label
        self.label_class = kwargs.pop('label_class', u'blockLabel')
        self.css_class = kwargs.pop('css_class', u'ctrlHolder')
        self.css_id = kwargs.pop('css_id', None)
        self.template = kwargs.pop('template', self.template)
        self.field_template = kwargs.pop('field_template', self.field_template)
        self.flat_attrs = flatatt(kwargs)

    def render(self, form, form_style, context, template_pack=TEMPLATE_PACK, **kwargs):
        # If a field within MultiField contains errors
        if context['form_show_errors']:
            for field in map(lambda pointer: pointer[1], self.get_field_names()):
                if field in form.errors:
                    self.css_class += " error"

        fields_output = u''
        field_template = self.field_template % template_pack
        for field in self.fields:
            fields_output += render_field(
                field, form, form_style, context,
                field_template, self.label_class, layout_object=self,
                template_pack=template_pack, **kwargs
            )

        extra_context = {
            'multifield': self,
            'fields_output': fields_output
        }
        template = self.template % template_pack
        return render_to_string(template, extra_context, context)


class Div(LayoutObject):
    """
    Layout object. It wraps fields in a <div>

    You can set `css_id` for a DOM id and `css_class` for a DOM class. Example::

        Div('form_field_1', 'form_field_2', css_id='div-example', css_class='divs')
    """
    template = "%s/layout/div.html"

    def __init__(self, *fields, **kwargs):
        self.fields = list(fields)

        if hasattr(self, 'css_class') and 'css_class' in kwargs:
            self.css_class += ' %s' % kwargs.pop('css_class')
        if not hasattr(self, 'css_class'):
            self.css_class = kwargs.pop('css_class', None)

        self.css_id = kwargs.pop('css_id', '')
        self.template = kwargs.pop('template', self.template)
        self.flat_attrs = flatatt(kwargs)

    def render(self, form, form_style, context, template_pack=TEMPLATE_PACK, **kwargs):
        fields = ''
        for field in self.fields:
            fields += render_field(
                field, form, form_style, context, template_pack=template_pack, **kwargs
            )

        template = self.template % template_pack
        return render_to_string(template, {'div': self, 'fields': fields})


class Row(Div):
    """
    Layout object. It wraps fields in a div whose default class is "formRow". Example::

        Row('form_field_1', 'form_field_2', 'form_field_3')
    """
    css_class = 'formRow' if TEMPLATE_PACK == 'uni_form' else 'row'


class Column(Div):
    """
    Layout object. It wraps fields in a div whose default class is "formColumn". Example::

        Column('form_field_1', 'form_field_2')
    """
    css_class = 'formColumn'


class HTML(object):
    """
    Layout object. It can contain pure HTML and it has access to the whole
    context of the page where the form is being rendered.

    Examples::

        HTML("{% if saved %}Data saved{% endif %}")
        HTML('<input type="hidden" name="{{ step_field }}" value="{{ step0 }}" />')
    """

    def __init__(self, html):
        self.html = html

    def render(self, form, form_style, context, template_pack=TEMPLATE_PACK, **kwargs):
        return Template(text_type(self.html)).render(context)


class Field(LayoutObject):
    """
    Layout object, It contains one field name, and you can add attributes to it easily.
    For setting class attributes, you need to use `css_class`, as `class` is a Python keyword.

    Example::

        Field('field_name', style="color: #333;", css_class="whatever", id="field_name")
    """
    template = "%s/field.html"

    def __init__(self, *args, **kwargs):
        self.fields = list(args)

        if not hasattr(self, 'attrs'):
            self.attrs = {}

        if 'css_class' in kwargs:
            if 'class' in self.attrs:
                self.attrs['class'] += " %s" % kwargs.pop('css_class')
            else:
                self.attrs['class'] = kwargs.pop('css_class')

        self.wrapper_class = kwargs.pop('wrapper_class', None)
        self.template = kwargs.pop('template', self.template)

        # We use kwargs as HTML attributes, turning data_id='test' into data-id='test'
        self.attrs.update(dict([(k.replace('_', '-'), conditional_escape(v)) for k, v in kwargs.items()]))

    def render(self, form, form_style, context, template_pack=TEMPLATE_PACK, extra_context=None, **kwargs):
        if extra_context is None:
            extra_context = {}
        if hasattr(self, 'wrapper_class'):
            extra_context['wrapper_class'] = self.wrapper_class

        html = ''
        template = self.template % template_pack
        for field in self.fields:
            html += render_field(
                field, form, form_style, context,
                template=template, attrs=self.attrs, template_pack=template_pack,
                extra_context=extra_context, **kwargs
            )
        return html


class MultiWidgetField(Field):
    """
    Layout object. For fields with :class:`~django.forms.MultiWidget` as `widget`, you can pass
    additional attributes to each widget.

    Example::

        MultiWidgetField(
            'multiwidget_field_name',
            attrs=(
                {'style': 'width: 30px;'},
                {'class': 'second_widget_class'}
            ),
        )

    .. note:: To override widget's css class use ``class`` not ``css_class``.
    """
    def __init__(self, *args, **kwargs):
        self.fields = list(args)
        self.attrs = kwargs.pop('attrs', {})
        self.template = kwargs.pop('template', self.template)

########NEW FILE########
__FILENAME__ = layout_slice
# -*- coding: utf-8 -*-
from crispy_forms.compatibility import integer_types, string_types
from crispy_forms.exceptions import DynamicError
from crispy_forms.layout import Fieldset, MultiField
from crispy_forms.bootstrap import Container


class LayoutSlice(object):
    # List of layout objects that need args passed first before fields
    args_first = (Fieldset, MultiField, Container)

    def __init__(self, layout, key):
        self.layout = layout
        if isinstance(key, integer_types):
            self.slice = slice(key, key+1, 1)
        else:
            self.slice = key

    def wrapped_object(self, LayoutClass, fields, *args, **kwargs):
        """
        Returns a layout object of type `LayoutClass` with `args` and `kwargs` that
        wraps `fields` inside.
        """
        if args:
            if isinstance(fields, list):
                fields= tuple(fields)
            else:
                fields = (fields,)

            if LayoutClass in self.args_first:
                arguments = args + fields
            else:
                arguments = fields + args

            return LayoutClass(*arguments, **kwargs)
        else:
            if isinstance(fields, list):
                return LayoutClass(*fields, **kwargs)
            else:
                return LayoutClass(fields, **kwargs)

    def pre_map(self, function):
        """
        Iterates over layout objects pointed in `self.slice` executing `function` on them.
        It passes `function` penultimate layout object and the position where to find last one
        """
        if isinstance(self.slice, slice):
            for i in range(*self.slice.indices(len(self.layout.fields))):
                function(self.layout, i)

        elif isinstance(self.slice, list):
            # A list of pointers  Ex: [[[0, 0], 'div'], [[0, 2, 3], 'field_name']]
            for pointer in self.slice:
                position = pointer[0]

                # If it's pointing first level
                if len(position) == 1:
                    function(self.layout, position[-1])
                else:
                    layout_object = self.layout.fields[position[0]]
                    for i in position[1:-1]:
                        layout_object = layout_object.fields[i]

                    try:
                        function(layout_object, position[-1])
                    except IndexError:
                        # We could avoid this exception, recalculating pointers.
                        # However this case is most of the time an undesired behavior
                        raise DynamicError("Trying to wrap a field within an already wrapped field, \
                            recheck your filter or layout")

    def wrap(self, LayoutClass, *args, **kwargs):
        """
        Wraps every layout object pointed in `self.slice` under a `LayoutClass` instance with
        `args` and `kwargs` passed.
        """
        def wrap_object(layout_object, j):
            layout_object.fields[j] = self.wrapped_object(
                LayoutClass, layout_object.fields[j], *args, **kwargs
            )

        self.pre_map(wrap_object)

    def wrap_once(self, LayoutClass, *args, **kwargs):
        """
        Wraps every layout object pointed in `self.slice` under a `LayoutClass` instance with
        `args` and `kwargs` passed, unless layout object's parent is already a subclass of
        `LayoutClass`.
        """
        def wrap_object_once(layout_object, j):
            if not isinstance(layout_object, LayoutClass):
                layout_object.fields[j] = self.wrapped_object(
                    LayoutClass, layout_object.fields[j], *args, **kwargs
                )

        self.pre_map(wrap_object_once)

    def wrap_together(self, LayoutClass, *args, **kwargs):
        """
        Wraps all layout objects pointed in `self.slice` together under a `LayoutClass`
        instance with `args` and `kwargs` passed.
        """
        if isinstance(self.slice, slice):
            # The start of the slice is replaced
            start = self.slice.start if self.slice.start is not None else 0
            self.layout.fields[start] = self.wrapped_object(
                LayoutClass, self.layout.fields[self.slice], *args, **kwargs
            )

            # The rest of places of the slice are removed, as they are included in the previous
            for i in reversed(range(*self.slice.indices(len(self.layout.fields)))):
                if i != start:
                    del self.layout.fields[i]

        elif isinstance(self.slice, list):
            raise DynamicError("wrap_together doesn't work with filter, only with [] operator")

    def map(self, function):
        """
        Iterates over layout objects pointed in `self.slice` executing `function` on them
        It passes `function` last layout object
        """
        if isinstance(self.slice, slice):
            for i in range(*self.slice.indices(len(self.layout.fields))):
                function(self.layout.fields[i])

        elif isinstance(self.slice, list):
            # A list of pointers  Ex: [[[0, 0], 'div'], [[0, 2, 3], 'field_name']]
            for pointer in self.slice:
                position = pointer[0]

                layout_object = self.layout.fields[position[0]]
                for i in position[1:]:
                    previous_layout_object = layout_object
                    layout_object = layout_object.fields[i]

                # If update_attrs is applied to a string, we call to its wrapping layout object
                if (
                    function.__name__ == 'update_attrs'
                    and isinstance(layout_object, string_types)
                ):
                    function(previous_layout_object)
                else:
                    function(layout_object)

    def update_attributes(self, **kwargs):
        """
        Updates attributes of every layout object pointed in `self.slice` using kwargs
        """
        def update_attrs(layout_object):
            if hasattr(layout_object, 'attrs'):
                layout_object.attrs.update(kwargs)

        self.map(update_attrs)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = crispy_forms_field
try:
    from itertools import izip
except ImportError:
    izip = zip

from django import forms
from django import template
from django.template import loader, Context
from django.conf import settings

from crispy_forms.utils import TEMPLATE_PACK

register = template.Library()

class_converter = {
    "textinput": "textinput textInput",
    "fileinput": "fileinput fileUpload",
    "passwordinput": "textinput textInput",
}
class_converter.update(getattr(settings, 'CRISPY_CLASS_CONVERTERS', {}))


@register.filter
def is_checkbox(field):
    return isinstance(field.field.widget, forms.CheckboxInput)


@register.filter
def is_password(field):
    return isinstance(field.field.widget, forms.PasswordInput)


@register.filter
def is_radioselect(field):
    return isinstance(field.field.widget, forms.RadioSelect)


@register.filter
def is_select(field):
    return isinstance(field.field.widget, forms.Select)


@register.filter
def is_checkboxselectmultiple(field):
    return isinstance(field.field.widget, forms.CheckboxSelectMultiple)


@register.filter
def is_file(field):
    return isinstance(field.field.widget, forms.ClearableFileInput)


@register.filter
def classes(field):
    """
    Returns CSS classes of a field
    """
    return field.widget.attrs.get('class', None)


@register.filter
def css_class(field):
    """
    Returns widgets class name in lowercase
    """
    return field.field.widget.__class__.__name__.lower()


def pairwise(iterable):
    "s -> (s0,s1), (s2,s3), (s4, s5), ..."
    a = iter(iterable)
    return izip(a, a)


class CrispyFieldNode(template.Node):
    def __init__(self, field, attrs):
        self.field = field
        self.attrs = attrs
        self.html5_required = 'html5_required'

    def render(self, context):
        # Nodes are not threadsafe so we must store and look up our instance
        # variables in the current rendering context first
        if self not in context.render_context:
            context.render_context[self] = (
                template.Variable(self.field),
                self.attrs,
                template.Variable(self.html5_required)
            )

        field, attrs, html5_required = context.render_context[self]
        field = field.resolve(context)
        try:
            html5_required = html5_required.resolve(context)
        except template.VariableDoesNotExist:
            html5_required = False

        # If template pack has been overriden in FormHelper we can pick it from context
        template_pack = context.get('template_pack', TEMPLATE_PACK)

        widgets = getattr(field.field.widget, 'widgets', [field.field.widget])

        if isinstance(attrs, dict):
            attrs = [attrs] * len(widgets)

        for widget, attr in zip(widgets, attrs):
            class_name = widget.__class__.__name__.lower()
            class_name = class_converter.get(class_name, class_name)
            css_class = widget.attrs.get('class', '')
            if css_class:
                if css_class.find(class_name) == -1:
                    css_class += " %s" % class_name
            else:
                css_class = class_name

            if (
                template_pack == 'bootstrap3'
                and not is_checkbox(field)
                and not is_file(field)
            ):
                css_class += ' form-control'

            widget.attrs['class'] = css_class

            # HTML5 required attribute
            if html5_required and field.field.required and 'required' not in widget.attrs:
                if field.field.widget.__class__.__name__ is not 'RadioSelect':
                    widget.attrs['required'] = 'required'

            for attribute_name, attribute in attr.items():
                attribute_name = template.Variable(attribute_name).resolve(context)

                if attribute_name in widget.attrs:
                    widget.attrs[attribute_name] += " " + template.Variable(attribute).resolve(context)
                else:
                    widget.attrs[attribute_name] = template.Variable(attribute).resolve(context)

        return field


@register.tag(name="crispy_field")
def crispy_field(parser, token):
    """
    {% crispy_field field attrs %}
    """
    token = token.split_contents()
    field = token.pop(1)
    attrs = {}

    # We need to pop tag name, or pairwise would fail
    token.pop(0)
    for attribute_name, value in pairwise(token):
        attrs[attribute_name] = value

    return CrispyFieldNode(field, attrs)


@register.simple_tag()
def crispy_addon(field, append="", prepend="", form_show_labels=True):
    """
    Renders a form field using bootstrap's prepended or appended text::

        {% crispy_addon form.my_field prepend="$" append=".00" %}

    You can also just prepend or append like so

        {% crispy_addon form.my_field prepend="$" %}
        {% crispy_addon form.my_field append=".00" %}
    """
    if (field):
        context = Context({
            'field': field,
            'form_show_errors': True,
            'form_show_labels': form_show_labels,
        })
        template = loader.get_template('%s/layout/prepended_appended_text.html' % TEMPLATE_PACK)
        context['crispy_prepended_text'] = prepend
        context['crispy_appended_text'] = append

        if not prepend and not append:
            raise TypeError("Expected a prepend and/or append argument")

    return template.render(context)


########NEW FILE########
__FILENAME__ = crispy_forms_filters
# -*- coding: utf-8 -*-
from django.conf import settings
from django.forms import forms
from django.forms.formsets import BaseFormSet
from django.template import Context
from django.template.loader import get_template
from django.utils.functional import memoize
from django.utils.safestring import mark_safe
from django import template

from crispy_forms.exceptions import CrispyError
from crispy_forms.utils import flatatt

TEMPLATE_PACK = getattr(settings, 'CRISPY_TEMPLATE_PACK', 'bootstrap')
DEBUG = getattr(settings, 'DEBUG', False)


def uni_formset_template(template_pack=TEMPLATE_PACK):
    return get_template('%s/uni_formset.html' % template_pack)
uni_formset_template = memoize(uni_formset_template, {}, 1)


def uni_form_template(template_pack=TEMPLATE_PACK):
    return get_template('%s/uni_form.html' % template_pack)
uni_form_template = memoize(uni_form_template, {}, 1)

register = template.Library()


@register.filter(name='crispy')
def as_crispy_form(form, template_pack=TEMPLATE_PACK, label_class="", field_class=""):
    """
    The original and still very useful way to generate a div elegant form/formset::

        {% load crispy_forms_tags %}

        <form class="uniForm" method="post">
            {% csrf_token %}
            {{ myform|crispy }}
        </form>

    or, if you want to explicitly set the template pack::

        {{ myform|crispy:"bootstrap" }}

    In ``bootstrap3`` for horizontal forms you can do::

        {{ myform|label_class:"col-lg-2",field_class:"col-lg-8" }}
    """
    if isinstance(form, BaseFormSet):
        template = uni_formset_template(template_pack)
        c = Context({
            'formset': form,
            'form_show_errors': True,
            'form_show_labels': True,
            'label_class': label_class,
            'field_class': field_class,
        })
    else:
        template = uni_form_template(template_pack)
        c = Context({
            'form': form,
            'form_show_errors': True,
            'form_show_labels': True,
            'label_class': label_class,
            'field_class': field_class,
        })
    return template.render(c)


@register.filter(name='as_crispy_errors')
def as_crispy_errors(form, template_pack=TEMPLATE_PACK):
    """
    Renders only form errors the same way as django-crispy-forms::

        {% load crispy_forms_tags %}
        {{ form|as_crispy_errors }}

    or::

        {{ form|as_crispy_errors:"bootstrap" }}
    """
    if isinstance(form, BaseFormSet):
        template = get_template('%s/errors_formset.html' % template_pack)
        c = Context({'formset': form})
    else:
        template = get_template('%s/errors.html' % template_pack)
        c = Context({'form': form})
    return template.render(c)


@register.filter(name='as_crispy_field')
def as_crispy_field(field, template_pack=TEMPLATE_PACK):
    """
    Renders a form field like a django-crispy-forms field::

        {% load crispy_forms_tags %}
        {{ form.field|as_crispy_field }}

    or::

        {{ form.field|as_crispy_field:"bootstrap" }}
    """
    if not isinstance(field, forms.BoundField) and DEBUG:
        raise CrispyError('|as_crispy_field got passed an invalid or inexistent field')

    template = get_template('%s/field.html' % template_pack)
    c = Context({'field': field, 'form_show_errors': True, 'form_show_labels': True})
    return template.render(c)


@register.filter(name='flatatt')
def flatatt_filter(attrs):
    return mark_safe(flatatt(attrs))

########NEW FILE########
__FILENAME__ = crispy_forms_tags
# -*- coding: utf-8 -*-
from copy import copy

from django.conf import settings
from django.forms.formsets import BaseFormSet
from django.template import Context
from django.template.loader import get_template
from django.utils.functional import memoize
from django import template

from crispy_forms.helper import FormHelper

register = template.Library()
# We import the filters, so they are available when doing load crispy_forms_tags
from crispy_forms.templatetags.crispy_forms_filters import *

TEMPLATE_PACK = getattr(settings, 'CRISPY_TEMPLATE_PACK', 'bootstrap')
ALLOWED_TEMPLATE_PACKS = getattr(
    settings,
    'CRISPY_ALLOWED_TEMPLATE_PACKS',
    ('bootstrap', 'uni_form', 'bootstrap3')
)


class ForLoopSimulator(object):
    """
    Simulates a forloop tag, precisely::

        {% for form in formset.forms %}

    If `{% crispy %}` is rendering a formset with a helper, We inject a `ForLoopSimulator` object
    in the context as `forloop` so that formset forms can do things like::

        Fieldset("Item {{ forloop.counter }}", [...])
        HTML("{% if forloop.first %}First form text{% endif %}"
    """
    def __init__(self, formset):
        self.len_values = len(formset.forms)

        # Shortcuts for current loop iteration number.
        self.counter = 1
        self.counter0 = 0
        # Reverse counter iteration numbers.
        self.revcounter = self.len_values
        self.revcounter0 = self.len_values - 1
        # Boolean values designating first and last times through loop.
        self.first = True
        self.last = (0 == self.len_values - 1)

    def iterate(self):
        """
        Updates values as if we had iterated over the for
        """
        self.counter += 1
        self.counter0 += 1
        self.revcounter -= 1
        self.revcounter0 -= 1
        self.first = False
        self.last = (self.revcounter0 == self.len_values - 1)


def copy_context(context):
    """
    Copies a `Context` variable. It uses `Context.__copy__` if available
    (introduced in Django 1.3) or copy otherwise.
    """
    if hasattr(context, "__copy__"):
        return context.__copy__()

    duplicate = copy(context)
    duplicate.dicts = context.dicts[:]
    return duplicate


class BasicNode(template.Node):
    """
    Basic Node object that we can rely on for Node objects in normal
    template tags. I created this because most of the tags we'll be using
    will need both the form object and the helper string. This handles
    both the form object and parses out the helper string into attributes
    that templates can easily handle.
    """
    def __init__(self, form, helper, template_pack=TEMPLATE_PACK):
        self.form = form
        if helper is not None:
            self.helper = helper
        else:
            self.helper = None
        self.template_pack = template_pack

    def get_render(self, context):
        """
        Returns a `Context` object with all the necessary stuff for rendering the form

        :param context: `django.template.Context` variable holding the context for the node

        `self.form` and `self.helper` are resolved into real Python objects resolving them
        from the `context`. The `actual_form` can be a form or a formset. If it's a formset
        `is_formset` is set to True. If the helper has a layout we use it, for rendering the
        form or the formset's forms.
        """
        # Nodes are not thread safe in multithreaded environments
        # https://docs.djangoproject.com/en/dev/howto/custom-template-tags/#thread-safety-considerations
        if self not in context.render_context:
            context.render_context[self] = (
                template.Variable(self.form),
                template.Variable(self.helper) if self.helper else None
            )
        form, helper = context.render_context[self]

        actual_form = form.resolve(context)
        if self.helper is not None:
            helper = helper.resolve(context)
        else:
            # If the user names the helper within the form `helper` (standard), we use it
            # This allows us to have simplified tag syntax: {% crispy form %}
            helper = FormHelper() if not hasattr(actual_form, 'helper') else actual_form.helper

        # use template_pack from helper, if defined
        try:
            if helper.template_pack:
                self.template_pack = helper.template_pack
        except AttributeError:
            pass

        self.actual_helper = helper

        # We get the response dictionary
        is_formset = isinstance(actual_form, BaseFormSet)
        response_dict = self.get_response_dict(helper, context, is_formset)
        node_context = copy_context(context)
        node_context.update(response_dict)

        # If we have a helper's layout we use it, for the form or the formset's forms
        if helper and helper.layout:
            if not is_formset:
                actual_form.form_html = helper.render_layout(actual_form, node_context, template_pack=self.template_pack)
            else:
                forloop = ForLoopSimulator(actual_form)
                helper.render_hidden_fields = True
                for form in actual_form:
                    node_context.update({'forloop': forloop})
                    form.form_html = helper.render_layout(form, node_context, template_pack=self.template_pack)
                    forloop.iterate()

        if is_formset:
            response_dict.update({'formset': actual_form})
        else:
            response_dict.update({'form': actual_form})

        return Context(response_dict)

    def get_response_dict(self, helper, context, is_formset):
        """
        Returns a dictionary with all the parameters necessary to render the form/formset in a template.

        :param attrs: Dictionary with the helper's attributes used for rendering the form/formset
        :param context: `django.template.Context` for the node
        :param is_formset: Boolean value. If set to True, indicates we are working with a formset.
        """
        if not isinstance(helper, FormHelper):
            raise TypeError('helper object provided to {% crispy %} tag must be a crispy.helper.FormHelper object.')

        attrs = helper.get_attributes(template_pack=self.template_pack)
        form_type = "form"
        if is_formset:
            form_type = "formset"

        # We take form/formset parameters from attrs if they are set, otherwise we use defaults
        response_dict = {
            'template_pack': self.template_pack,
            '%s_action' % form_type: attrs['attrs'].get("action", ''),
            '%s_method' % form_type: attrs.get("form_method", 'post'),
            '%s_tag' % form_type: attrs.get("form_tag", True),
            '%s_class' % form_type: attrs['attrs'].get("class", ''),
            '%s_id' % form_type: attrs['attrs'].get("id", ""),
            '%s_style' % form_type: attrs.get("form_style", None),
            'form_error_title': attrs.get("form_error_title", None),
            'formset_error_title': attrs.get("formset_error_title", None),
            'form_show_errors': attrs.get("form_show_errors", True),
            'help_text_inline': attrs.get("help_text_inline", False),
            'html5_required': attrs.get("html5_required", False),
            'form_show_labels': attrs.get("form_show_labels", True),
            'disable_csrf': attrs.get("disable_csrf", False),
            'inputs': attrs.get('inputs', []),
            'is_formset': is_formset,
            '%s_attrs' % form_type: attrs.get('attrs', ''),
            'flat_attrs': attrs.get('flat_attrs', ''),
            'error_text_inline': attrs.get('error_text_inline', True),
            'label_class': attrs.get('label_class', ''),
            'label_size': attrs.get('label_size', 0),
            'field_class': attrs.get('field_class', ''),
        }

        # Handles custom attributes added to helpers
        for attribute_name, value in attrs.items():
            if attribute_name not in response_dict:
                response_dict[attribute_name] = value

        if 'csrf_token' in context:
            response_dict['csrf_token'] = context['csrf_token']

        return response_dict


def whole_uni_formset_template(template_pack=TEMPLATE_PACK):
    return get_template('%s/whole_uni_formset.html' % template_pack)
whole_uni_formset_template = memoize(whole_uni_formset_template, {}, 1)


def whole_uni_form_template(template_pack=TEMPLATE_PACK):
    return get_template('%s/whole_uni_form.html' % template_pack)
whole_uni_form_template = memoize(whole_uni_form_template, {}, 1)


class CrispyFormNode(BasicNode):
    def render(self, context):
        c = self.get_render(context)

        if self.actual_helper is not None and getattr(self.actual_helper, 'template', False):
            template = get_template(self.actual_helper.template)
        else:
            if c['is_formset']:
                template = whole_uni_formset_template(self.template_pack)
            else:
                template = whole_uni_form_template(self.template_pack)

        return template.render(c)


# {% crispy %} tag
@register.tag(name="crispy")
def do_uni_form(parser, token):
    """
    You need to pass in at least the form/formset object, and can also pass in the
    optional `crispy_forms.helpers.FormHelper` object.

    helper (optional): A `crispy_forms.helper.FormHelper` object.

    Usage::

        {% include crispy_tags %}
        {% crispy form form.helper %}

    You can also provide the template pack as the third argument::

        {% crispy form form.helper 'bootstrap' %}

    If the `FormHelper` attribute is named `helper` you can simply do::

        {% crispy form %}
        {% crispy form 'bootstrap' %}
    """
    token = token.split_contents()
    form = token.pop(1)

    helper = None
    template_pack = "'%s'" % TEMPLATE_PACK

    # {% crispy form helper %}
    try:
        helper = token.pop(1)
    except IndexError:
        pass

    # {% crispy form helper 'bootstrap' %}
    try:
        template_pack = token.pop(1)
    except IndexError:
        pass

    # {% crispy form 'bootstrap' %}
    if (
        helper is not None and
        isinstance(helper, basestring) and
        ("'" in helper or '"' in helper)
    ):
        template_pack = helper
        helper = None

    if template_pack is not None:
        template_pack = template_pack[1:-1]
        if template_pack not in ALLOWED_TEMPLATE_PACKS:
            raise template.TemplateSyntaxError(
                "crispy tag's template_pack argument should be in %s" %
                str(ALLOWED_TEMPLATE_PACKS)
            )

    return CrispyFormNode(form, helper, template_pack=template_pack)

########NEW FILE########
__FILENAME__ = crispy_forms_utils
# -*- coding: utf-8 -*-
import re

from django import template
from django.conf import settings
try:  # Django < 1.4
    from django.utils.encoding import force_unicode as force_text
except ImportError:
    from django.utils.encoding import force_text
from django.utils.functional import allow_lazy

from crispy_forms.compatibility import text_type

register = template.Library()
TEMPLATE_PACK = getattr(settings, 'CRISPY_TEMPLATE_PACK', 'bootstrap')


def selectively_remove_spaces_between_tags(value, template_pack, form_class):
    if (
        'bootstrap' in template_pack
        and 'form-inline' in form_class
    ):
        # More than 3 strict whitespaces, see issue #250
        html = re.sub(r'>\s{3,}<', '> <', force_text(value))
        return re.sub(r'/><', r'/> <', force_text(html))
    else:
        html = re.sub(r'>\s{3,}<', '> <', force_text(value))
        return re.sub(r'/><', r'/> <', force_text(html))
    return value
selectively_remove_spaces_between_tags = allow_lazy(
    selectively_remove_spaces_between_tags, text_type
)


class SpecialSpacelessNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        try:
            template_pack = template.Variable('template_pack').resolve(context)
        except:
            template_pack = TEMPLATE_PACK

        try:
            form_attrs = template.Variable('form_attrs').resolve(context)
        except:
            form_attrs = {}

        return selectively_remove_spaces_between_tags(
            self.nodelist.render(context).strip(),
            template_pack,
            form_attrs.get('class', ''),
        )


@register.tag
def specialspaceless(parser, token):
    """
    Removes whitespace between HTML tags, and introduces a whitespace
    after buttons an inputs, necessary for Bootstrap to place them
    correctly in the layout.
    """
    nodelist = parser.parse(('endspecialspaceless',))
    parser.delete_first_token()

    return SpecialSpacelessNode(nodelist)

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-
import os

from django.conf import settings
from django.template import loader
from django.test import TestCase

from crispy_forms.tests.utils import override_settings


class CrispyTestCase(TestCase):
    def setUp(self):
        template_dirs = [os.path.join(os.path.dirname(__file__), 'templates')]
        template_dirs = template_dirs + list(settings.TEMPLATE_DIRS)
        template_loaders = ['django.template.loaders.filesystem.Loader']
        template_loaders = template_loaders + list(settings.TEMPLATE_LOADERS)

        # ensuring test templates directory is loaded first
        self.__overriden_settings = override_settings(**{
            'TEMPLATE_LOADERS': template_loaders,
            'TEMPLATE_DIRS': template_dirs,
        })
        self.__overriden_settings.enable()

        # resetting template loaders cache
        self.__template_source_loaders = loader.template_source_loaders
        loader.template_source_loaders = None

    def tearDown(self):
        loader.template_source_loaders = self.__template_source_loaders
        self.__overriden_settings.disable()

    @property
    def current_template_pack(self):
        return getattr(settings, 'CRISPY_TEMPLATE_PACK', 'bootstrap')

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.db import models

from crispy_forms.helper import FormHelper


class TestForm(forms.Form):
    is_company = forms.CharField(label="company", required=False, widget=forms.CheckboxInput())
    email = forms.EmailField(label="email", max_length=30, required=True, widget=forms.TextInput(), help_text="Insert your email")
    password1 = forms.CharField(label="password", max_length=30, required=True, widget=forms.PasswordInput())
    password2 = forms.CharField(label="re-enter password", max_length=30, required=True, widget=forms.PasswordInput())
    first_name = forms.CharField(label="first name", max_length=5, required=True, widget=forms.TextInput())
    last_name = forms.CharField(label="last name", max_length=5, required=True, widget=forms.TextInput())
    datetime_field = forms.DateTimeField(label="date time", widget=forms.SplitDateTimeWidget())

    def clean(self):
        super(TestForm, self).clean()
        password1 = self.cleaned_data.get('password1', None)
        password2 = self.cleaned_data.get('password2', None)
        if not password1 and not password2 or password1 != password2:
            raise forms.ValidationError("Passwords dont match")

        return self.cleaned_data


class TestForm2(TestForm):
    def __init__(self, *args, **kwargs):
        super(TestForm2, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)


class CheckboxesTestForm(forms.Form):
    checkboxes = forms.MultipleChoiceField(
        choices = (
            (1, "Option one"),
            (2, "Option two"),
            (3, "Option three")
        ),
        initial = (1,),
        widget = forms.CheckboxSelectMultiple,
    )

    alphacheckboxes = forms.MultipleChoiceField(
        choices = (
            ('option_one', "Option one"),
            ('option_two', "Option two"),
            ('option_three', "Option three")
        ),
        initial = ('option_two', 'option_three'),
        widget = forms.CheckboxSelectMultiple,
    )

    numeric_multiple_checkboxes = forms.MultipleChoiceField(
        choices = (
            (1, "Option one"),
            (2, "Option two"),
            (3, "Option three")
        ),
        initial = (1, 2),
        widget = forms.CheckboxSelectMultiple,
    )

    inline_radios = forms.ChoiceField(
        choices = (
            ('option_one', "Option one"),
            ('option_two', "Option two"),
        ),
        widget = forms.RadioSelect,
        initial = 'option_two',
    )


class CrispyTestModel(models.Model):
    email = models.CharField(max_length=20)
    password = models.CharField(max_length=20)


class TestForm3(forms.ModelForm):
    class Meta:
        model = CrispyTestModel
        fields = ['email', 'password']
        exclude = ['password']

    def __init__(self, *args, **kwargs):
        super(TestForm3, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)


class TestForm4(forms.ModelForm):
    class Meta:
        model = CrispyTestModel


class TestForm5(forms.Form):
    choices = [
        (1, 1),
        (2, 2),
        (1000, 1000),
    ]
    checkbox_select_multiple = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        choices=choices
    )
    radio_select = forms.ChoiceField(
        widget=forms.RadioSelect,
        choices=choices
    )
    pk = forms.IntegerField()

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python

import os
import sys

cmds = [
    'python runtests_bootstrap.py',
    'python runtests_bootstrap3.py',
    'python runtests_uniform.py',
]

for cmd in cmds:
    retval = os.system(cmd)
    if retval:
        sys.exit(1)

########NEW FILE########
__FILENAME__ = runtests_bootstrap
#!/usr/bin/env python

import os, sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'test_settings'
parent = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))))

sys.path.insert(0, parent)

from django.test.simple import DjangoTestSuiteRunner
from django.conf import settings

settings.CRISPY_TEMPLATE_PACK = 'bootstrap'


def runtests():
    return DjangoTestSuiteRunner(failfast=False).run_tests([
        'crispy_forms.TestBasicFunctionalityTags',
        'crispy_forms.TestFormHelper',
        'crispy_forms.TestBootstrapFormHelper',
        'crispy_forms.TestFormLayout',
        'crispy_forms.TestBootstrapFormLayout',
        'crispy_forms.TestLayoutObjects',
        'crispy_forms.TestBootstrapLayoutObjects',
        'crispy_forms.TestDynamicLayouts',
    ], verbosity=1, interactive=True)


if __name__ == '__main__':
    if runtests():
        sys.exit(1)

########NEW FILE########
__FILENAME__ = runtests_bootstrap3
#!/usr/bin/env python

import os, sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'test_settings'
parent = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))))

sys.path.insert(0, parent)

from django.test.simple import DjangoTestSuiteRunner
from django.conf import settings

settings.CRISPY_TEMPLATE_PACK = 'bootstrap3'


def runtests():
    return DjangoTestSuiteRunner(failfast=False).run_tests([
        'crispy_forms.TestBasicFunctionalityTags',
        'crispy_forms.TestFormHelper',
        'crispy_forms.TestBootstrapFormHelper',
        'crispy_forms.TestBootstrap3FormHelper',
        'crispy_forms.TestFormLayout',
        'crispy_forms.TestBootstrapFormLayout',
        'crispy_forms.TestBootstrap3FormLayout',
        'crispy_forms.TestLayoutObjects',
        'crispy_forms.TestBootstrapLayoutObjects',
        'crispy_forms.TestDynamicLayouts',
    ], verbosity=1, interactive=True)


if __name__ == '__main__':
    if runtests():
        sys.exit(1)

########NEW FILE########
__FILENAME__ = runtests_uniform
#!/usr/bin/env python

import os, sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'test_settings'
parent = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))))

sys.path.insert(0, parent)

from django.test.simple import DjangoTestSuiteRunner
from django.conf import settings

settings.CRISPY_TEMPLATE_PACK = 'uni_form'


def runtests():
    return DjangoTestSuiteRunner(failfast=False).run_tests([
        'crispy_forms.TestBasicFunctionalityTags',
        'crispy_forms.TestFormHelper',
        'crispy_forms.TestUniformFormHelper',
        'crispy_forms.TestFormLayout',
        'crispy_forms.TestUniformFormLayout',
        'crispy_forms.TestLayoutObjects',
        'crispy_forms.TestDynamicLayouts',
        'crispy_forms.TestUniformDynamicLayouts',
    ], verbosity=1, interactive=True)


if __name__ == '__main__':
    if runtests():
        sys.exit(1)

########NEW FILE########
__FILENAME__ = test_dynamic_api
# -*- coding: utf-8 -*-
from django import forms

from .base import CrispyTestCase
from crispy_forms.compatibility import string_types
from crispy_forms.exceptions import DynamicError
from crispy_forms.helper import FormHelper, FormHelpersException
from crispy_forms.layout import Submit
from crispy_forms.layout import (
    Layout, Fieldset, MultiField, HTML, Div, Field
)
from crispy_forms.bootstrap import AppendedText
from crispy_forms.tests.forms import TestForm


class TestDynamicLayouts(CrispyTestCase):
    def setUp(self):
        super(TestDynamicLayouts, self).setUp()

        self.advanced_layout = Layout(
            Div(
                Div(Div('email')),
                Div(Field('password1')),
                Submit("save", "save"),
                Fieldset(
                    "legend",
                    'first_name',
                    HTML("extra text"),
                ),
                Layout(
                    "password2",
                ),
            ),
            'last_name',
        )

    def test_wrap_all_fields(self):
        helper = FormHelper()
        layout = Layout(
            'email',
            'password1',
            'password2',
        )
        helper.layout = layout

        helper.all().wrap(Field, css_class="test-class")
        for field in layout.fields:
            self.assertTrue(isinstance(field, Field))
            self.assertEqual(field.attrs['class'], "test-class")

        self.assertEqual(layout[0][0], 'email')
        self.assertEqual(layout[1][0], 'password1')
        self.assertEqual(layout[2][0], 'password2')

    def test_wrap_selected_fields(self):
        helper = FormHelper()
        layout = Layout(
            'email',
            'password1',
            'password2',
        )
        helper.layout = layout

        helper[1:3].wrap(Field, css_class="test-class")
        self.assertFalse(isinstance(layout.fields[0], Field))
        self.assertTrue(isinstance(layout.fields[1], Field))
        self.assertTrue(isinstance(layout.fields[2], Field))

        helper[0].wrap(Fieldset, 'legend', css_class="test-class")
        self.assertTrue(isinstance(layout[0], Fieldset))
        self.assertEqual(layout[0].legend, 'legend')
        self.assertEqual(layout[0][0], 'email')

    def test_wrap_together_with_slices(self):
        helper = FormHelper()
        layout = Layout(
            'email',
            'password1',
            'password2',
        )
        helper.layout = layout
        helper[1:3].wrap_together(Field, css_class="test-class")
        self.assertEqual(layout.fields[0], 'email')
        self.assertTrue(isinstance(layout.fields[1], Field))
        self.assertEqual(layout.fields[1][0], 'password1')
        self.assertEqual(layout.fields[1][1], 'password2')

        layout = Layout(
            Div('email'),
            'password1',
            'password2',
        )
        helper.layout = layout
        helper[0:3].wrap_together(Field, css_class="test-class")
        self.assertTrue(isinstance(layout.fields[0], Field))
        self.assertTrue(isinstance(layout.fields[0][0], Div))
        self.assertEqual(layout.fields[0][0][0], 'email')
        self.assertEqual(layout.fields[0][1], 'password1')
        self.assertEqual(layout.fields[0][2], 'password2')

        layout = Layout(
            'email',
            'password1',
            'password2',
        )
        helper.layout = layout
        helper[0].wrap_together(Field, css_class="test-class")
        self.assertTrue(isinstance(layout.fields[0], Field))
        self.assertEqual(layout.fields[1], 'password1')
        self.assertEqual(layout.fields[2], 'password2')

        layout = Layout(
            'email',
            'password1',
            'password2',
        )
        helper.layout = layout
        helper[0].wrap_together(Fieldset, "legend", css_class="test-class")
        self.assertTrue(isinstance(layout.fields[0], Fieldset))
        self.assertEqual(layout.fields[0].legend, 'legend')
        self.assertEqual(layout.fields[1], 'password1')
        self.assertEqual(layout.fields[2], 'password2')

    def test_wrap_together_partial_slices(self):
        helper = FormHelper()
        layout = Layout(
            'email',
            'password1',
            'password2',
        )
        helper.layout = layout

        helper[:2].wrap_together(Field, css_class="test-class")
        self.assertTrue(isinstance(layout.fields[0], Field))
        self.assertEqual(layout.fields[1], 'password2')
        self.assertEqual(layout.fields[0][0], 'email')
        self.assertEqual(layout.fields[0][1], 'password1')

        helper = FormHelper()
        layout = Layout(
            'email',
            'password1',
            'password2',
        )
        helper.layout = layout

        helper[1:].wrap_together(Field, css_class="test-class")
        self.assertEqual(layout.fields[0], 'email')
        self.assertTrue(isinstance(layout.fields[1], Field))
        self.assertEqual(layout.fields[1][0], 'password1')
        self.assertEqual(layout.fields[1][1], 'password2')

    def test_update_attributes(self):
        helper = FormHelper()
        helper.layout = Layout(
            'email',
            Field('password1'),
            'password2',
        )
        helper['password1'].update_attributes(readonly=True)
        self.assertTrue('readonly' in helper.layout[1].attrs)

    def test_update_attributes_and_wrap_once(self):
        helper = FormHelper()
        layout = Layout(
            'email',
            Field('password1'),
            'password2',
        )
        helper.layout = layout
        helper.filter(Field).update_attributes(readonly=True)
        self.assertTrue(isinstance(layout[1], Field))
        self.assertEqual(layout[1].attrs, {'readonly': True})

        layout = Layout(
            'email',
            Div(Field('password1')),
            'password2',
        )
        helper.layout = layout
        helper.filter(Field, max_level=2).update_attributes(readonly=True)
        self.assertTrue(isinstance(layout[1][0], Field))
        self.assertEqual(layout[1][0].attrs, {'readonly': True})

        layout = Layout(
            'email',
            Div(Field('password1')),
            'password2',
        )
        helper.layout = layout

        helper.filter(string_types, greedy=True).wrap_once(Field)
        helper.filter(Field, greedy=True).update_attributes(readonly=True)

        self.assertTrue(isinstance(layout[0], Field))
        self.assertTrue(isinstance(layout[1][0], Field))
        self.assertTrue(isinstance(layout[1][0][0], string_types))
        self.assertTrue(isinstance(layout[2], Field))
        self.assertEqual(layout[1][0].attrs, {'readonly': True})
        self.assertEqual(layout[0].attrs, {'readonly': True})
        self.assertEqual(layout[2].attrs, {'readonly': True})

    def test_get_layout_objects(self):
        layout_1 = Layout(
            Div()
        )
        self.assertEqual(layout_1.get_layout_objects(Div), [
            [[0], 'div']
        ])

        layout_2 = Layout(
            Div(
                Div(
                    Div('email')
                ),
                Div('password1'),
                'password2'
            )
        )
        self.assertEqual(layout_2.get_layout_objects(Div), [
            [[0], 'div']
        ])
        self.assertEqual(layout_2.get_layout_objects(Div, max_level=1), [
            [[0], 'div'],
            [[0, 0], 'div'],
            [[0, 1], 'div']
        ])
        self.assertEqual(layout_2.get_layout_objects(Div, max_level=2), [
            [[0], 'div'],
            [[0, 0], 'div'],
            [[0, 0, 0], 'div'],
            [[0, 1], 'div']
        ])

        layout_3 = Layout(
            'email',
            Div('password1'),
            'password2',
        )
        self.assertEqual(layout_3.get_layout_objects(string_types, max_level=2), [
            [[0], 'email'],
            [[1, 0], 'password1'],
            [[2], 'password2']
        ])

        layout_4 = Layout(
            Div(
                Div('field_name'),
                'field_name2',
            ),
            Div('password'),
            'extra_field'
        )
        self.assertEqual(layout_4.get_layout_objects(Div), [
            [[0], 'div'],
            [[1], 'div']
        ])
        self.assertEqual(layout_4.get_layout_objects(Div, max_level=1), [
            [[0], 'div'],
            [[0, 0], 'div'],
            [[1], 'div']
        ])

    def test_filter_and_wrap(self):
        helper = FormHelper()
        layout = Layout(
            'email',
            Div('password1'),
            'password2',
        )
        helper.layout = layout

        helper.filter(string_types).wrap(Field, css_class="test-class")
        self.assertTrue(isinstance(layout.fields[0], Field))
        self.assertTrue(isinstance(layout.fields[1], Div))
        self.assertTrue(isinstance(layout.fields[2], Field))
        self.assertEqual(layout[2][0], 'password2')

        # Wrapping a div in a div
        helper.filter(Div).wrap(Div, css_class="test-class")
        self.assertTrue(isinstance(layout.fields[1], Div))
        self.assertTrue(isinstance(layout.fields[1].fields[0], Div))
        self.assertEqual(layout[1][0][0], 'password1')

    def test_filter_and_wrap_side_effects(self):
        helper = FormHelper()
        layout = Layout(
            Div(
                'extra_field',
                Div('password1'),
            ),
        )
        helper.layout = layout
        self.assertRaises(DynamicError, lambda: helper.filter(Div, max_level=2).wrap(Div, css_class="test-class"))

    def test_get_field_names(self):
        layout_1 = Div(
            'field_name'
        )
        self.assertEqual(layout_1.get_field_names(), [
            [[0], 'field_name']
        ])

        layout_2 = Div(
            Div('field_name')
        )
        self.assertEqual(layout_2.get_field_names(), [
            [[0, 0], 'field_name']
        ])

        layout_3 = Div(
            Div('field_name'),
            'password'
        )
        self.assertEqual(layout_3.get_field_names(), [
            [[0, 0], 'field_name'],
            [[1], 'password']
        ])

        layout_4 = Div(
            Div(
                Div('field_name'),
                'field_name2',
            ),
            Div('password'),
            'extra_field'
        )
        self.assertEqual(layout_4.get_field_names(), [
            [[0, 0, 0], 'field_name'],
            [[0, 1], 'field_name2'],
            [[1, 0], 'password'],
            [[2], 'extra_field']
        ])

        layout_5 = Div(
            Div(
                'field_name',
                'field_name2',
            ),
            'extra_field'
        )
        self.assertEqual(layout_5.get_field_names(), [
            [[0, 0], 'field_name'],
            [[0, 1], 'field_name2'],
            [[1], 'extra_field'],
        ])

    def test_layout_get_field_names(self):
        layout_1 = Layout(
            Div('field_name'),
            'password'
        )
        self.assertEqual(layout_1.get_field_names(), [
            [[0, 0], 'field_name'],
            [[1], 'password'],
        ])

        layout_2 = Layout(
            Div('field_name'),
            'password',
            Fieldset('legend', 'extra_field')
        )
        self.assertEqual(layout_2.get_field_names(), [
            [[0, 0], 'field_name'],
            [[1], 'password'],
            [[2, 0], 'extra_field'],
        ])

        layout_3 = Layout(
            Div(
                Div(
                    Div('email')
                ),
                Div('password1'),
                'password2'
            )
        )
        self.assertEqual(layout_3.get_field_names(), [
            [[0, 0, 0, 0], 'email'],
            [[0, 1, 0], 'password1'],
            [[0, 2], 'password2'],
        ])

    def test_filter_by_widget(self):
        form = TestForm()
        form.helper = FormHelper(form)
        form.helper.layout = self.advanced_layout
        self.assertEqual(form.helper.filter_by_widget(forms.PasswordInput).slice, [
            [[0, 1, 0, 0], 'password1'],
            [[0, 4, 0], 'password2'],
        ])

    def test_exclude_by_widget(self):
        form = TestForm()
        form.helper = FormHelper(form)
        form.helper.layout = self.advanced_layout
        self.assertEqual(form.helper.exclude_by_widget(forms.PasswordInput).slice, [
            [[0, 0, 0, 0], 'email'],
            [[0, 3, 0], 'first_name'],
            [[1], 'last_name'],
        ])

    def test_exclude_by_widget_and_wrap(self):
        form = TestForm()
        form.helper = FormHelper(form)
        form.helper.layout = self.advanced_layout
        form.helper.exclude_by_widget(forms.PasswordInput).wrap(Field, css_class='hero')
        # Check wrapped fields
        self.assertTrue(isinstance(form.helper.layout[0][0][0][0], Field))
        self.assertTrue(isinstance(form.helper.layout[0][3][0], Field))
        self.assertTrue(isinstance(form.helper.layout[1], Field))
        # Check others stay the same
        self.assertTrue(isinstance(form.helper.layout[0][3][1], HTML))
        self.assertTrue(isinstance(form.helper.layout[0][1][0][0], string_types))
        self.assertTrue(isinstance(form.helper.layout[0][4][0], string_types))

    def test_all_without_layout(self):
        form = TestForm()
        form.helper = FormHelper()
        self.assertRaises(FormHelpersException, lambda: form.helper.all().wrap(Div))

    def test_filter_by_widget_without_form(self):
        form = TestForm()
        form.helper = FormHelper()
        form.helper.layout = self.advanced_layout
        self.assertRaises(FormHelpersException, lambda: form.helper.filter_by_widget(forms.PasswordInput))

    def test_formhelper__getitem__(self):
        helper = FormHelper()
        layout = Layout(
            Div('email'),
            'password1',
        )
        helper.layout = layout
        helper['email'].wrap(Field, css_class='hero')
        self.assertTrue(isinstance(layout[0][0], Field))
        self.assertEqual(layout[0][0][0], 'email')

        helper = FormHelper()
        helper.layout = Layout('password1')
        helper['password1'].wrap(AppendedText, "extra")
        self.assertTrue(isinstance(helper.layout[0], AppendedText))
        self.assertEqual(helper.layout[0][0], 'password1')
        self.assertEqual(helper.layout[0].text, 'extra')

    def test_formhelper__setitem__(self):
        helper = FormHelper()
        layout = Layout(
            'first_field',
            Div('email')
        )
        helper.layout = layout
        helper[0] = 'replaced'
        self.assertEqual(layout[0], 'replaced')

    def test_formhelper__delitem__and__len__(self):
        helper = FormHelper()
        layout = Layout(
            'first_field',
            Div('email')
        )
        helper.layout = layout
        del helper[0]
        self.assertEqual(len(helper), 1)

    def test__delitem__and__len__layout_object(self):
        layout = Layout(
            'first_field',
            Div('email')
        )
        del layout[0]
        self.assertEqual(len(layout), 1)

    def test__getitem__layout_object(self):
        layout = Layout(
            Div(
                Div(
                    Div('email')
                ),
                Div('password1'),
                'password2'
            )
        )
        self.assertTrue(isinstance(layout[0], Div))
        self.assertTrue(isinstance(layout[0][0], Div))
        self.assertTrue(isinstance(layout[0][0][0], Div))
        self.assertTrue(isinstance(layout[0][1], Div))
        self.assertTrue(isinstance(layout[0][1][0], string_types))
        self.assertTrue(isinstance(layout[0][2], string_types))

    def test__getattr__append_layout_object(self):
        layout = Layout(
            Div('email')
        )
        layout.append('password1')
        self.assertTrue(isinstance(layout[0], Div))
        self.assertTrue(isinstance(layout[0][0], string_types))
        self.assertTrue(isinstance(layout[1], string_types))

    def test__setitem__layout_object(self):
        layout = Layout(
            Div('email')
        )
        layout[0][0] = 'password1'
        self.assertTrue(isinstance(layout[0], Div))
        self.assertEqual(layout[0][0], 'password1')


class TestUniformDynamicLayouts(TestDynamicLayouts):
    def test_filter(self):
        helper = FormHelper()
        helper.layout = Layout(
            Div(
                MultiField('field_name'),
                'field_name2',
            ),
            Div('password'),
            'extra_field'
        )
        self.assertEqual(helper.filter(Div, MultiField).slice, [
            [[0], 'div'],
            [[1], 'div']
        ])
        self.assertEqual(helper.filter(Div, MultiField, max_level=1).slice, [
            [[0], 'div'],
            [[0, 0], 'multifield'],
            [[1], 'div']
        ])
        self.assertEqual(helper.filter(MultiField, max_level=1).slice, [
            [[0, 0], 'multifield']
        ])
########NEW FILE########
__FILENAME__ = test_form_helper
# -*- coding: utf-8 -*-
import re

import django
from django import forms
from django.conf import settings
from django.core.urlresolvers import reverse
from django.forms.models import formset_factory
from django.middleware.csrf import _get_new_csrf_key
from django.template import (
    loader, TemplateSyntaxError, Context
)
from django.utils.translation import ugettext_lazy as _

from .base import CrispyTestCase
from .forms import TestForm
from crispy_forms.bootstrap import (
    FieldWithButtons, PrependedAppendedText, AppendedText, PrependedText,
    StrictButton
)
from crispy_forms.compatibility import text_type
from crispy_forms.helper import FormHelper, FormHelpersException
from crispy_forms.layout import (
    Layout, Submit, Reset, Hidden, Button, MultiField, Field
)
from crispy_forms.utils import render_crispy_form
from crispy_forms.templatetags.crispy_forms_tags import CrispyFormNode


class TestFormHelper(CrispyTestCase):
    urls = 'crispy_forms.tests.urls'

    def test_inputs(self):
        form_helper = FormHelper()
        form_helper.add_input(Submit('my-submit', 'Submit', css_class="button white"))
        form_helper.add_input(Reset('my-reset', 'Reset'))
        form_helper.add_input(Hidden('my-hidden', 'Hidden'))
        form_helper.add_input(Button('my-button', 'Button'))

        template = loader.get_template_from_string(u"""
            {% load crispy_forms_tags %}
            {% crispy form form_helper %}
        """)
        c = Context({'form': TestForm(), 'form_helper': form_helper})
        html = template.render(c)

        self.assertTrue('button white' in html)
        self.assertTrue('id="submit-id-my-submit"' in html)
        self.assertTrue('id="reset-id-my-reset"' in html)
        self.assertTrue('name="my-hidden"' in html)
        self.assertTrue('id="button-id-my-button"' in html)

        if self.current_template_pack == 'uni_form':
            self.assertTrue('submit submitButton' in html)
            self.assertTrue('reset resetButton' in html)
            self.assertTrue('class="button"' in html)
        else:
            self.assertTrue('class="btn"' in html)
            self.assertTrue('btn btn-primary' in html)
            self.assertTrue('btn btn-inverse' in html)
            self.assertEqual(len(re.findall(r'<input[^>]+> <', html)), 8)

    def test_invalid_form_method(self):
        form_helper = FormHelper()
        try:
            form_helper.form_method = "superPost"
            self.fail("Setting an invalid form_method within the helper should raise an Exception")
        except FormHelpersException:
            pass

    def test_form_with_helper_without_layout(self):
        form_helper = FormHelper()
        form_helper.form_id = 'this-form-rocks'
        form_helper.form_class = 'forms-that-rock'
        form_helper.form_method = 'GET'
        form_helper.form_action = 'simpleAction'
        form_helper.form_error_title = 'ERRORS'

        template = loader.get_template_from_string(u"""
            {% load crispy_forms_tags %}
            {% crispy testForm form_helper %}
        """)

        # now we render it, with errors
        form = TestForm({'password1': 'wargame','password2': 'god'})
        form.is_valid()
        c = Context({'testForm': form, 'form_helper': form_helper})
        html = template.render(c)

        # Lets make sure everything loads right
        self.assertTrue(html.count('<form'), 1)
        self.assertTrue('forms-that-rock' in html)
        self.assertTrue('method="get"' in html)
        self.assertTrue('id="this-form-rocks"' in html)
        self.assertTrue('action="%s"' % reverse('simpleAction') in html)

        if (self.current_template_pack == 'uni_form'):
            self.assertTrue('class="uniForm' in html)

        self.assertTrue("ERRORS" in html)
        self.assertTrue("<li>Passwords dont match</li>" in html)

        # now lets remove the form tag and render it again. All the True items above
        # should now be false because the form tag is removed.
        form_helper.form_tag = False
        html = template.render(c)
        self.assertFalse('<form' in html)
        self.assertFalse('forms-that-rock' in html)
        self.assertFalse('method="get"' in html)
        self.assertFalse('id="this-form-rocks"' in html)

    def test_form_show_errors_non_field_errors(self):
        form = TestForm({'password1': 'wargame', 'password2': 'god'})
        form.helper = FormHelper()
        form.helper.form_show_errors = True
        form.is_valid()

        template = loader.get_template_from_string(u"""
            {% load crispy_forms_tags %}
            {% crispy testForm %}
        """)

        # First we render with errors
        c = Context({'testForm': form})
        html = template.render(c)

        # Ensure those errors were rendered
        self.assertTrue('<li>Passwords dont match</li>' in html)
        self.assertTrue(text_type(_('This field is required.')) in html)
        self.assertTrue('error' in html)

        # Now we render without errors
        form.helper.form_show_errors = False
        c = Context({'testForm': form})
        html = template.render(c)

        # Ensure errors were not rendered
        self.assertFalse('<li>Passwords dont match</li>' in html)
        self.assertFalse(text_type(_('This field is required.')) in html)
        self.assertFalse('error' in html)

    def test_html5_required(self):
        form = TestForm()
        form.helper = FormHelper()
        form.helper.html5_required = True
        html = render_crispy_form(form)
        # 6 out of 7 fields are required and an extra one for the SplitDateTimeWidget makes 7.
        self.assertEqual(html.count('required="required"'), 7)

        form = TestForm()
        form.helper = FormHelper()
        form.helper.html5_required = False
        html = render_crispy_form(form)

    def test_attrs(self):
        form = TestForm()
        form.helper = FormHelper()
        form.helper.attrs = {'id': 'TestIdForm', 'autocomplete': "off"}
        html = render_crispy_form(form)

        self.assertTrue('autocomplete="off"' in html)
        self.assertTrue('id="TestIdForm"' in html)

    def test_template_context(self):
        helper = FormHelper()
        helper.attrs = {
            'id': 'test-form',
            'class': 'test-forms',
            'action': 'submit/test/form',
            'autocomplete': 'off',
        }
        node = CrispyFormNode('form', 'helper')
        context = node.get_response_dict(helper, {}, False)

        self.assertEqual(context['form_id'], "test-form")
        self.assertEqual(context['form_attrs']['id'], "test-form")
        self.assertTrue("test-forms" in context['form_class'])
        self.assertTrue("test-forms" in context['form_attrs']['class'])
        self.assertEqual(context['form_action'], "submit/test/form")
        self.assertEqual(context['form_attrs']['action'], "submit/test/form")
        self.assertEqual(context['form_attrs']['autocomplete'], "off")

    def test_template_context_using_form_attrs(self):
        helper = FormHelper()
        helper.form_id = 'test-form'
        helper.form_class = 'test-forms'
        helper.form_action = 'submit/test/form'
        node = CrispyFormNode('form', 'helper')
        context = node.get_response_dict(helper, {}, False)

        self.assertEqual(context['form_id'], "test-form")
        self.assertEqual(context['form_attrs']['id'], "test-form")
        self.assertTrue("test-forms" in context['form_class'])
        self.assertTrue("test-forms" in context['form_attrs']['class'])
        self.assertEqual(context['form_action'], "submit/test/form")
        self.assertEqual(context['form_attrs']['action'], "submit/test/form")

    def test_template_helper_access(self):
        helper = FormHelper()
        helper.form_id = 'test-form'

        self.assertEqual(helper['form_id'], 'test-form')

    def test_without_helper(self):
        template = loader.get_template_from_string(u"""
            {% load crispy_forms_tags %}
            {% crispy form %}
        """)
        c = Context({'form': TestForm()})
        html = template.render(c)

        # Lets make sure everything loads right
        self.assertTrue('<form' in html)
        self.assertTrue('method="post"' in html)
        self.assertFalse('action' in html)
        if (self.current_template_pack == 'uni_form'):
            self.assertTrue('uniForm' in html)

    def test_template_pack_override_compact(self):
        current_pack = self.current_template_pack
        override_pack = current_pack == 'uni_form' and 'bootstrap' or 'uni_form'

        # {% crispy form 'template_pack_name' %}
        template = loader.get_template_from_string(u"""
            {%% load crispy_forms_tags %%}
            {%% crispy form "%s" %%}
        """ % override_pack)
        c = Context({'form': TestForm()})
        html = template.render(c)

        if (current_pack == 'uni_form'):
            self.assertTrue('control-group' in html)
        else:
            self.assertTrue('uniForm' in html)

    def test_template_pack_override_verbose(self):
        current_pack = self.current_template_pack
        override_pack = current_pack == 'uni_form' and 'bootstrap' or 'uni_form'

        # {% crispy form helper 'template_pack_name' %}
        template = loader.get_template_from_string(u"""
            {%% load crispy_forms_tags %%}
            {%% crispy form form_helper "%s" %%}
        """ % override_pack)
        c = Context({'form': TestForm(), 'form_helper': FormHelper()})
        html = template.render(c)

        if (current_pack == 'uni_form'):
            self.assertTrue('control-group' in html)
        else:
            self.assertTrue('uniForm' in html)

    def test_template_pack_override_wrong(self):
        try:
            loader.get_template_from_string(u"""
                {% load crispy_forms_tags %}
                {% crispy form 'foo' %}
            """)
        except TemplateSyntaxError:
            pass

    def test_invalid_helper(self):
        template = loader.get_template_from_string(u"""
            {% load crispy_forms_tags %}
            {% crispy form form_helper %}
        """)
        c = Context({'form': TestForm(), 'form_helper': "invalid"})

        settings.CRISPY_FAIL_SILENTLY = False
        # Django >= 1.4 is not wrapping exceptions in TEMPLATE_DEBUG mode
        if settings.TEMPLATE_DEBUG and django.get_version() < '1.4':
            self.assertRaises(TemplateSyntaxError, lambda:template.render(c))
        else:
            self.assertRaises(TypeError, lambda:template.render(c))
        del settings.CRISPY_FAIL_SILENTLY

    def test_formset_with_helper_without_layout(self):
        template = loader.get_template_from_string(u"""
            {% load crispy_forms_tags %}
            {% crispy testFormSet formset_helper %}
        """)

        form_helper = FormHelper()
        form_helper.form_id = 'thisFormsetRocks'
        form_helper.form_class = 'formsets-that-rock'
        form_helper.form_method = 'POST'
        form_helper.form_action = 'simpleAction'

        TestFormSet = formset_factory(TestForm, extra = 3)
        testFormSet = TestFormSet()

        c = Context({'testFormSet': testFormSet, 'formset_helper': form_helper, 'csrf_token': _get_new_csrf_key()})
        html = template.render(c)

        self.assertEqual(html.count('<form'), 1)
        self.assertEqual(html.count("<input type='hidden' name='csrfmiddlewaretoken'"), 1)

        # Check formset management form
        self.assertTrue('form-TOTAL_FORMS' in html)
        self.assertTrue('form-INITIAL_FORMS' in html)
        self.assertTrue('form-MAX_NUM_FORMS' in html)

        self.assertTrue('formsets-that-rock' in html)
        self.assertTrue('method="post"' in html)
        self.assertTrue('id="thisFormsetRocks"' in html)
        self.assertTrue('action="%s"' % reverse('simpleAction') in html)
        if (self.current_template_pack == 'uni_form'):
            self.assertTrue('class="uniForm' in html)

    def test_CSRF_token_POST_form(self):
        form_helper = FormHelper()
        template = loader.get_template_from_string(u"""
            {% load crispy_forms_tags %}
            {% crispy form form_helper %}
        """)

        # The middleware only initializes the CSRF token when processing a real request
        # So using RequestContext or csrf(request) here does not work.
        # Instead I set the key `csrf_token` to a CSRF token manually, which `csrf_token` tag uses
        c = Context({'form': TestForm(), 'form_helper': form_helper, 'csrf_token': _get_new_csrf_key()})
        html = template.render(c)

        self.assertTrue("<input type='hidden' name='csrfmiddlewaretoken'" in html)

    def test_CSRF_token_GET_form(self):
        form_helper = FormHelper()
        form_helper.form_method = 'GET'
        template = loader.get_template_from_string(u"""
            {% load crispy_forms_tags %}
            {% crispy form form_helper %}
        """)

        c = Context({'form': TestForm(), 'form_helper': form_helper, 'csrf_token': _get_new_csrf_key()})
        html = template.render(c)

        self.assertFalse("<input type='hidden' name='csrfmiddlewaretoken'" in html)

    def test_disable_csrf(self):
        form = TestForm()
        helper = FormHelper()
        helper.disable_csrf = True
        html = render_crispy_form(form, helper, {'csrf_token': _get_new_csrf_key()})
        self.assertFalse('csrf' in html)

    def test_render_hidden_fields(self):
        test_form = TestForm()
        test_form.helper = FormHelper()
        test_form.helper.layout = Layout(
            'email'
        )
        test_form.helper.render_hidden_fields = True

        html = render_crispy_form(test_form)
        self.assertEqual(html.count('<input'), 1)

        # Now hide a couple of fields
        for field in ('password1', 'password2'):
            test_form.fields[field].widget = forms.HiddenInput()

        html = render_crispy_form(test_form)
        self.assertEqual(html.count('<input'), 3)
        self.assertEqual(html.count('hidden'), 2)

        if django.get_version() < '1.5':
            self.assertEqual(html.count('type="hidden" name="password1"'), 1)
            self.assertEqual(html.count('type="hidden" name="password2"'), 1)
        else:
            self.assertEqual(html.count('name="password1" type="hidden"'), 1)
            self.assertEqual(html.count('name="password2" type="hidden"'), 1)

    def test_render_required_fields(self):
        test_form = TestForm()
        test_form.helper = FormHelper()
        test_form.helper.layout = Layout(
            'email'
        )
        test_form.helper.render_required_fields = True

        html = render_crispy_form(test_form)
        self.assertEqual(html.count('<input'), 7)

    def test_helper_custom_template(self):
        form = TestForm()
        form.helper = FormHelper()
        form.helper.template = 'custom_form_template.html'

        html = render_crispy_form(form)
        self.assertTrue("<h1>Special custom form</h1>" in html)

    def test_helper_custom_field_template(self):
        form = TestForm()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            'password1',
            'password2',
        )
        form.helper.field_template = 'custom_field_template.html'

        html = render_crispy_form(form)
        self.assertEqual(html.count("<h1>Special custom field</h1>"), 2)


class TestUniformFormHelper(TestFormHelper):
    def test_form_show_errors(self):
        form = TestForm({
            'email': 'invalidemail',
            'first_name': 'first_name_too_long',
            'last_name': 'last_name_too_long',
            'password1': 'yes',
            'password2': 'yes',
            })
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('email'),
            Field('first_name'),
            Field('last_name'),
            Field('password1'),
            Field('password2'),
        )
        form.is_valid()

        form.helper.form_show_errors = True
        html = render_crispy_form(form)
        self.assertEqual(html.count('error'), 9)

        form.helper.form_show_errors = False
        html = render_crispy_form(form)
        self.assertEqual(html.count('error'), 0)

    def test_multifield_errors(self):
        form = TestForm({
            'email': 'invalidemail',
            'password1': 'yes',
            'password2': 'yes',
            })
        form.helper = FormHelper()
        form.helper.layout = Layout(
            MultiField('legend', 'email')
        )
        form.is_valid()

        form.helper.form_show_errors = True
        html = render_crispy_form(form)
        self.assertEqual(html.count('error'), 3)

        # Reset layout for avoiding side effects
        form.helper.layout = Layout(
            MultiField('legend', 'email')
        )
        form.helper.form_show_errors = False
        html = render_crispy_form(form)
        self.assertEqual(html.count('error'), 0)


class TestBootstrapFormHelper(TestFormHelper):
    def test_form_show_errors(self):
        form = TestForm({
                'email': 'invalidemail',
                'first_name': 'first_name_too_long',
                'last_name': 'last_name_too_long',
                'password1': 'yes',
                'password2': 'yes',
                })
        form.helper = FormHelper()
        form.helper.layout = Layout(
            AppendedText('email', 'whatever'),
            PrependedText('first_name', 'blabla'),
            PrependedAppendedText('last_name', 'foo', 'bar'),
            AppendedText('password1', 'whatever'),
            PrependedText('password2', 'blabla'),
        )
        form.is_valid()

        form.helper.form_show_errors = True
        html = render_crispy_form(form)
        self.assertEqual(html.count('error'), 6)

        form.helper.form_show_errors = False
        html = render_crispy_form(form)
        self.assertEqual(html.count('error'), 0)

    def test_error_text_inline(self):
        form = TestForm({'email': 'invalidemail'})
        form.helper = FormHelper()
        layout = Layout(
            AppendedText('first_name', 'wat'),
            PrependedText('email', '@'),
            PrependedAppendedText('last_name', '@', 'wat'),
        )
        form.helper.layout = layout
        form.is_valid()
        html = render_crispy_form(form)

        help_class = 'help-inline'
        if self.current_template_pack == 'bootstrap3':
            help_class = 'help-block'

        matches = re.findall(
            '<span id="error_\d_\w*" class="%s"' % help_class, html, re.MULTILINE
        )
        self.assertEqual(len(matches), 3)

        form = TestForm({'email': 'invalidemail'})
        form.helper = FormHelper()
        form.helper.layout = layout
        form.helper.error_text_inline = False
        html = render_crispy_form(form)

        matches = re.findall('<p id="error_\d_\w*" class="help-block"', html, re.MULTILINE)
        self.assertEqual(len(matches), 3)

    def test_error_and_help_inline(self):
        form = TestForm({'email': 'invalidemail'})
        form.helper = FormHelper()
        form.helper.error_text_inline = False
        form.helper.help_text_inline = True
        form.helper.layout = Layout('email')
        form.is_valid()
        html = render_crispy_form(form)

        # Check that help goes before error, otherwise CSS won't work
        help_position = html.find('<span id="hint_id_email" class="help-inline">')
        error_position = html.find('<p id="error_1_id_email" class="help-block">')
        self.assertTrue(help_position < error_position)

        # Viceversa
        form = TestForm({'email': 'invalidemail'})
        form.helper = FormHelper()
        form.helper.error_text_inline = True
        form.helper.help_text_inline = False
        form.helper.layout = Layout('email')
        form.is_valid()
        html = render_crispy_form(form)

        # Check that error goes before help, otherwise CSS won't work
        error_position = html.find('<span id="error_1_id_email" class="help-inline">')
        help_position = html.find('<p id="hint_id_email" class="help-block">')
        self.assertTrue(error_position < help_position)

    def test_form_show_labels(self):
        form = TestForm()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            'password1',
            FieldWithButtons(
                'password2',
                StrictButton("Confirm")
            ),
            PrependedText(
                'first_name',
                'Mr.'
            ),
            AppendedText(
                'last_name',
                '@'
            ),
            PrependedAppendedText(
                'datetime_field',
                'on',
                'secs'
            )
        )
        form.helper.form_show_labels = False

        html = render_crispy_form(form)
        self.assertEqual(html.count("<label"), 0)


class TestBootstrap3FormHelper(TestFormHelper):
    def test_label_class_and_field_class(self):
        form = TestForm()
        form.helper = FormHelper()
        form.helper.label_class = 'col-lg-2'
        form.helper.field_class = 'col-lg-8'
        html = render_crispy_form(form)

        self.assertTrue('<div class="form-group"> <div class="controls col-lg-offset-2 col-lg-8"> <div id="div_id_is_company" class="checkbox"> <label for="id_is_company" class=""> <input class="checkboxinput checkbox" id="id_is_company" name="is_company" type="checkbox" />')
        self.assertEqual(html.count('col-lg-8'), 7)

        form.helper.label_class = 'col-sm-3'
        form.helper.field_class = 'col-sm-8'
        html = render_crispy_form(form)

        self.assertTrue('<div class="form-group"> <div class="controls col-sm-offset-3 col-sm-8"> <div id="div_id_is_company" class="checkbox"> <label for="id_is_company" class=""> <input class="checkboxinput checkbox" id="id_is_company" name="is_company" type="checkbox" />')
        self.assertEqual(html.count('col-sm-8'), 7)

    def test_template_pack(self):
        form = TestForm()
        form.helper = FormHelper()
        form.helper.template_pack = 'uni_form'
        html = render_crispy_form(form)
        self.assertFalse('form-control' in html)
        self.assertTrue('ctrlHolder' in html)

########NEW FILE########
__FILENAME__ = test_layout
# -*- coding: utf-8 -*-
import re

import django
from django import forms
from django.conf import settings
from django.core.urlresolvers import reverse
from django.forms.models import formset_factory, modelformset_factory
from django.middleware.csrf import _get_new_csrf_key
from django.shortcuts import render_to_response
from django.template import (
    Context, RequestContext, loader
)
from django.test import RequestFactory
from django.utils.translation import ugettext_lazy as _

from .base import CrispyTestCase
from .forms import (
    TestForm, TestForm2, TestForm3, CheckboxesTestForm,
    TestForm4, CrispyTestModel, TestForm5
)
from .utils import override_settings
from crispy_forms.bootstrap import InlineCheckboxes
from crispy_forms.compatibility import PY2
from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
    Layout, Fieldset, MultiField, Row, Column, HTML, ButtonHolder,
    Div, Submit
)
from crispy_forms.utils import render_crispy_form


class TestFormLayout(CrispyTestCase):
    urls = 'crispy_forms.tests.urls'

    def test_invalid_unicode_characters(self):
        # Adds a BooleanField that uses non valid unicode characters "ñ"
        form_helper = FormHelper()
        form_helper.add_layout(
            Layout(
                'españa'
            )
        )

        template = loader.get_template_from_string(u"""
            {% load crispy_forms_tags %}
            {% crispy form form_helper %}
        """)
        c = Context({'form': TestForm(), 'form_helper': form_helper})
        settings.CRISPY_FAIL_SILENTLY = False
        self.assertRaises(Exception, lambda: template.render(c))
        del settings.CRISPY_FAIL_SILENTLY

    def test_unicode_form_field(self):
        class UnicodeForm(forms.Form):
            def __init__(self, *args, **kwargs):
                super(UnicodeForm, self).__init__(*args, **kwargs)
                self.fields['contraseña'] = forms.CharField()

            helper = FormHelper()
            helper.layout = Layout(u'contraseña')

        if PY2:
            self.assertRaises(Exception, lambda: render_crispy_form(UnicodeForm()))
        else:
            html = render_crispy_form(UnicodeForm())
            self.assertTrue('id="id_contraseña"' in html)

    def test_meta_extra_fields_with_missing_fields(self):
        class FormWithMeta(TestForm):
            class Meta:
                fields = ('email', 'first_name', 'last_name')

        form = FormWithMeta()
        # We remove email field on the go
        del form.fields['email']

        form_helper = FormHelper()
        form_helper.layout = Layout(
            'first_name',
        )

        template = loader.get_template_from_string(u"""
            {% load crispy_forms_tags %}
            {% crispy form form_helper %}
        """)
        c = Context({'form': form, 'form_helper': form_helper})
        html = template.render(c)
        self.assertFalse('email' in html)

    def test_layout_unresolved_field(self):
        form_helper = FormHelper()
        form_helper.add_layout(
            Layout(
                'typo'
            )
        )

        template = loader.get_template_from_string(u"""
            {% load crispy_forms_tags %}
            {% crispy form form_helper %}
        """)
        c = Context({'form': TestForm(), 'form_helper': form_helper})
        settings.CRISPY_FAIL_SILENTLY = False
        self.assertRaises(Exception, lambda:template.render(c))
        del settings.CRISPY_FAIL_SILENTLY

    def test_double_rendered_field(self):
        form_helper = FormHelper()
        form_helper.add_layout(
            Layout(
                'is_company',
                'is_company',
            )
        )

        template = loader.get_template_from_string(u"""
            {% load crispy_forms_tags %}
            {% crispy form form_helper %}
        """)
        c = Context({'form': TestForm(), 'form_helper': form_helper})
        settings.CRISPY_FAIL_SILENTLY = False
        self.assertRaises(Exception, lambda:template.render(c))
        del settings.CRISPY_FAIL_SILENTLY

    def test_context_pollution(self):
        class ExampleForm(forms.Form):
            comment = forms.CharField()

        form = ExampleForm()
        form2 = TestForm()

        template = loader.get_template_from_string(u"""
            {% load crispy_forms_tags %}
            {{ form.as_ul }}
            {% crispy form2 %}
            {{ form.as_ul }}
        """)
        c = Context({'form': form, 'form2': form2})
        html = template.render(c)

        self.assertEqual(html.count('name="comment"'), 2)
        self.assertEqual(html.count('name="is_company"'), 1)

    def test_layout_fieldset_row_html_with_unicode_fieldnames(self):
        form_helper = FormHelper()
        form_helper.add_layout(
            Layout(
                Fieldset(
                    u'Company Data',
                    u'is_company',
                    css_id = "fieldset_company_data",
                    css_class = "fieldsets",
                    title = "fieldset_title",
                    test_fieldset = "123"
                ),
                Fieldset(
                    u'User Data',
                    u'email',
                    Row(
                        u'password1',
                        u'password2',
                        css_id = "row_passwords",
                        css_class = "rows",
                    ),
                    HTML('<a href="#" id="testLink">test link</a>'),
                    HTML(u"""
                        {% if flag %}{{ message }}{% endif %}
                    """),
                    u'first_name',
                    u'last_name',
                )
            )
        )

        template = loader.get_template_from_string(u"""
            {% load crispy_forms_tags %}
            {% crispy form form_helper %}
        """)
        c = Context({
            'form': TestForm(),
            'form_helper': form_helper,
            'flag': True,
            'message': "Hello!",
        })
        html = template.render(c)

        self.assertTrue('id="fieldset_company_data"' in html)
        self.assertTrue('class="fieldsets' in html)
        self.assertTrue('title="fieldset_title"' in html)
        self.assertTrue('test-fieldset="123"' in html)
        self.assertTrue('id="row_passwords"' in html)
        self.assertEqual(html.count('<label'), 6)

        if self.current_template_pack == 'uni_form':
            self.assertTrue('class="formRow rows"' in html)
        else:
            self.assertTrue('class="row rows"' in html)
        self.assertTrue('Hello!' in html)
        self.assertTrue('testLink' in html)

    def test_change_layout_dynamically_delete_field(self):
        template = loader.get_template_from_string(u"""
            {% load crispy_forms_tags %}
            {% crispy form form_helper %}
        """)

        form = TestForm()
        form_helper = FormHelper()
        form_helper.add_layout(
            Layout(
                Fieldset(
                    u'Company Data',
                    'is_company',
                    'email',
                    'password1',
                    'password2',
                    css_id = "multifield_info",
                ),
                Column(
                    'first_name',
                    'last_name',
                    css_id = "column_name",
                )
            )
        )

        # We remove email field on the go
        # Layout needs to be adapted for the new form fields
        del form.fields['email']
        del form_helper.layout.fields[0].fields[1]

        c = Context({'form': form, 'form_helper': form_helper})
        html = template.render(c)
        self.assertFalse('email' in html)

    def test_formset_layout(self):
        TestFormSet = formset_factory(TestForm, extra=3)
        formset = TestFormSet()
        helper = FormHelper()
        helper.form_id = 'thisFormsetRocks'
        helper.form_class = 'formsets-that-rock'
        helper.form_method = 'POST'
        helper.form_action = 'simpleAction'
        helper.layout = Layout(
            Fieldset("Item {{ forloop.counter }}",
                'is_company',
                'email',
            ),
            HTML("{% if forloop.first %}Note for first form only{% endif %}"),
            Row('password1', 'password2'),
            Fieldset("",
                'first_name',
                'last_name'
            )
        )

        html = render_crispy_form(
            form=formset, helper=helper, context={'csrf_token': _get_new_csrf_key()}
        )

        # Check formset fields
        django_version = django.get_version()
        if django_version < '1.5':
            self.assertEqual(html.count(
                'type="hidden" name="form-TOTAL_FORMS" value="3" id="id_form-TOTAL_FORMS"'
            ), 1)
            self.assertEqual(html.count(
                'type="hidden" name="form-INITIAL_FORMS" value="0" id="id_form-INITIAL_FORMS"'
            ), 1)
            if (django_version >= '1.4' and django_version < '1.4.4') or django_version < '1.3.6':
                self.assertEqual(html.count(
                    'type="hidden" name="form-MAX_NUM_FORMS" id="id_form-MAX_NUM_FORMS"'
                ), 1)
            else:
                self.assertEqual(html.count(
                    'type="hidden" name="form-MAX_NUM_FORMS" value="1000" id="id_form-MAX_NUM_FORMS"'
                ), 1)
        else:
            self.assertEqual(html.count(
                'id="id_form-TOTAL_FORMS" name="form-TOTAL_FORMS" type="hidden" value="3"'
            ), 1)
            self.assertEqual(html.count(
                'id="id_form-INITIAL_FORMS" name="form-INITIAL_FORMS" type="hidden" value="0"'
            ), 1)
            self.assertEqual(html.count(
                'id="id_form-MAX_NUM_FORMS" name="form-MAX_NUM_FORMS" type="hidden" value="1000"'
            ), 1)
        self.assertEqual(html.count("hidden"), 4)

        # Check form structure
        self.assertEqual(html.count('<form'), 1)
        self.assertEqual(html.count("<input type='hidden' name='csrfmiddlewaretoken'"), 1)
        self.assertTrue('formsets-that-rock' in html)
        self.assertTrue('method="post"' in html)
        self.assertTrue('id="thisFormsetRocks"' in html)
        self.assertTrue('action="%s"' % reverse('simpleAction') in html)

        # Check form layout
        self.assertTrue('Item 1' in html)
        self.assertTrue('Item 2' in html)
        self.assertTrue('Item 3' in html)
        self.assertEqual(html.count('Note for first form only'), 1)
        if self.current_template_pack == 'uni_form':
            self.assertEqual(html.count('formRow'), 3)
        else:
            self.assertEqual(html.count('row'), 3)

    def test_modelformset_layout(self):
        CrispyModelFormSet = modelformset_factory(CrispyTestModel, form=TestForm4, extra=3)
        formset = CrispyModelFormSet(queryset=CrispyTestModel.objects.none())
        helper = FormHelper()
        helper.layout = Layout(
            'email'
        )

        html = render_crispy_form(form=formset, helper=helper)
        self.assertEqual(html.count("id_form-0-id"), 1)
        self.assertEqual(html.count("id_form-1-id"), 1)
        self.assertEqual(html.count("id_form-2-id"), 1)

        django_version = django.get_version()
        if django_version < '1.5':
            self.assertEqual(html.count(
                'type="hidden" name="form-TOTAL_FORMS" value="3" id="id_form-TOTAL_FORMS"'
            ), 1)
            self.assertEqual(html.count(
                'type="hidden" name="form-INITIAL_FORMS" value="0" id="id_form-INITIAL_FORMS"'
            ), 1)
            if (django_version >= '1.4' and django_version < '1.4.4') or django_version < '1.3.6':
                self.assertEqual(html.count(
                    'type="hidden" name="form-MAX_NUM_FORMS" id="id_form-MAX_NUM_FORMS"'
                ), 1)
            else:
                self.assertEqual(html.count(
                    'type="hidden" name="form-MAX_NUM_FORMS" value="1000" id="id_form-MAX_NUM_FORMS"'
                ), 1)
        else:
            self.assertEqual(html.count(
                'id="id_form-TOTAL_FORMS" name="form-TOTAL_FORMS" type="hidden" value="3"'
            ), 1)
            self.assertEqual(html.count(
                'id="id_form-INITIAL_FORMS" name="form-INITIAL_FORMS" type="hidden" value="0"'
            ), 1)
            self.assertEqual(html.count(
                'id="id_form-MAX_NUM_FORMS" name="form-MAX_NUM_FORMS" type="hidden" value="1000"'
            ), 1)

        self.assertEqual(html.count('name="form-0-email"'), 1)
        self.assertEqual(html.count('name="form-1-email"'), 1)
        self.assertEqual(html.count('name="form-2-email"'), 1)
        self.assertEqual(html.count('name="form-3-email"'), 0)
        self.assertEqual(html.count('password'), 0)

    def test_i18n(self):
        template = loader.get_template_from_string(u"""
            {% load crispy_forms_tags %}
            {% crispy form form.helper %}
        """)
        form = TestForm()
        form_helper = FormHelper()
        form_helper.layout = Layout(
            HTML(_("i18n text")),
            Fieldset(
                _("i18n legend"),
                'first_name',
                'last_name',
            )
        )
        form.helper = form_helper

        html = template.render(Context({'form': form}))
        self.assertEqual(html.count('i18n legend'), 1)

    @override_settings(USE_L10N=True, USE_THOUSAND_SEPARATOR=True)
    def test_l10n(self):
        form = TestForm5(data={'pk': 1000})
        html = render_crispy_form(form)

        # Make sure values are unlocalized
        self.assertTrue('value="1,000"' not in html)

        # Make sure label values are NOT localized
        self.assertTrue(html.count('1000'), 2)

    def test_default_layout(self):
        test_form = TestForm2()
        self.assertEqual(test_form.helper.layout.fields, [
            'is_company', 'email', 'password1', 'password2',
            'first_name', 'last_name', 'datetime_field',
        ])

    def test_default_layout_two(self):
        test_form = TestForm3()
        self.assertEqual(test_form.helper.layout.fields, ['email'])

    def test_modelform_layout_without_meta(self):
        test_form = TestForm4()
        test_form.helper = FormHelper()
        test_form.helper.layout = Layout('email')
        html = render_crispy_form(test_form)

        self.assertTrue('email' in html)
        self.assertFalse('password' in html)

    def test_specialspaceless_not_screwing_intended_spaces(self):
        # see issue #250
        test_form = TestForm()
        test_form.fields['email'].widget = forms.Textarea()
        test_form.helper = FormHelper()
        test_form.helper.layout = Layout(
            'email',
            HTML("<span>first span</span> <span>second span</span>")
        )
        html = render_crispy_form(test_form)
        self.assertTrue('<span>first span</span> <span>second span</span>' in html)


class TestUniformFormLayout(TestFormLayout):

    def test_layout_composition(self):
        form_helper = FormHelper()
        form_helper.add_layout(
            Layout(
                Layout(
                    MultiField("Some company data",
                        'is_company',
                        'email',
                        css_id = "multifield_info",
                    ),
                ),
                Column(
                    'first_name',
                    # 'last_name', Missing a field on purpose
                    css_id = "column_name",
                    css_class = "columns",
                ),
                ButtonHolder(
                    Submit('Save', 'Save', css_class='button white'),
                ),
                Div(
                    'password1',
                    'password2',
                    css_id="custom-div",
                    css_class="customdivs",
                )
            )
        )

        template = loader.get_template_from_string(u"""
                {% load crispy_forms_tags %}
                {% crispy form form_helper %}
            """)
        c = Context({'form': TestForm(), 'form_helper': form_helper})
        html = template.render(c)

        self.assertTrue('multiField' in html)
        self.assertTrue('formColumn' in html)
        self.assertTrue('id="multifield_info"' in html)
        self.assertTrue('id="column_name"' in html)
        self.assertTrue('class="formColumn columns"' in html)
        self.assertTrue('class="buttonHolder">' in html)
        self.assertTrue('input type="submit"' in html)
        self.assertTrue('name="Save"' in html)
        self.assertTrue('id="custom-div"' in html)
        self.assertTrue('class="customdivs"' in html)
        self.assertFalse('last_name' in html)

    def test_second_layout_multifield_column_buttonholder_submit_div(self):
        form_helper = FormHelper()
        form_helper.add_layout(
            Layout(
                MultiField("Some company data",
                    'is_company',
                    'email',
                    css_id = "multifield_info",
                    title = "multifield_title",
                    multifield_test = "123"
                ),
                Column(
                    'first_name',
                    'last_name',
                    css_id = "column_name",
                    css_class = "columns",
                ),
                ButtonHolder(
                    Submit('Save the world', '{{ value_var }}', css_class='button white', data_id='test', data_name='test'),
                    Submit('store', 'Store results')
                ),
                Div(
                    'password1',
                    'password2',
                    css_id="custom-div",
                    css_class="customdivs",
                    test_markup="123"
                )
            )
        )

        template = loader.get_template_from_string(u"""
                {% load crispy_forms_tags %}
                {% crispy form form_helper %}
            """)
        c = Context({'form': TestForm(), 'form_helper': form_helper, 'value_var': "Save"})
        html = template.render(c)

        self.assertTrue('multiField' in html)
        self.assertTrue('formColumn' in html)
        self.assertTrue('id="multifield_info"' in html)
        self.assertTrue('title="multifield_title"' in html)
        self.assertTrue('multifield-test="123"' in html)
        self.assertTrue('id="column_name"' in html)
        self.assertTrue('class="formColumn columns"' in html)
        self.assertTrue('class="buttonHolder">' in html)
        self.assertTrue('input type="submit"' in html)
        self.assertTrue('button white' in html)
        self.assertTrue('data-id="test"' in html)
        self.assertTrue('data-name="test"' in html)
        self.assertTrue('name="save-the-world"' in html)
        self.assertTrue('value="Save"' in html)
        self.assertTrue('name="store"' in html)
        self.assertTrue('value="Store results"' in html)
        self.assertTrue('id="custom-div"' in html)
        self.assertTrue('class="customdivs"' in html)
        self.assertTrue('test-markup="123"' in html)


class TestBootstrapFormLayout(TestFormLayout):

    def test_keepcontext_context_manager(self):
        # Test case for issue #180
        # Apparently it only manifest when using render_to_response this exact way
        form = CheckboxesTestForm()
        form.helper = FormHelper()
        # We use here InlineCheckboxes as it updates context in an unsafe way
        form.helper.layout = Layout(
            'checkboxes',
            InlineCheckboxes('alphacheckboxes'),
            'numeric_multiple_checkboxes'
        )
        request_factory = RequestFactory()
        request = request_factory.get('/')
        context = RequestContext(request, {'form': form})

        response = render_to_response('crispy_render_template.html', context)

        if self.current_template_pack == 'bootstrap':
            self.assertEqual(response.content.count(b'checkbox inline'), 3)
        elif self.current_template_pack == 'bootstrap3':
            self.assertEqual(response.content.count(b'checkbox-inline'), 3)


class TestBootstrap3FormLayout(TestFormLayout):

    def test_form_inline(self):
        form = TestForm()
        form.helper = FormHelper()
        form.helper.form_class = 'form-inline'
        form.helper.field_template = 'bootstrap3/layout/inline_field.html'
        form.helper.layout = Layout(
            'email',
            'password1',
            'last_name',
        )

        html = render_crispy_form(form)
        self.assertEqual(html.count('class="form-inline"'), 1)
        self.assertEqual(html.count('class="form-group"'), 3)
        self.assertEqual(html.count('<label for="id_email" class="sr-only'), 1)
        self.assertEqual(html.count('id="div_id_email" class="form-group"'), 1)
        self.assertEqual(html.count('placeholder="email"'), 1)
        self.assertEqual(html.count('</label> <input'), 3)

########NEW FILE########
__FILENAME__ = test_layout_objects
# -*- coding: utf-8 -*-
import re

from django import forms
from django.template import loader, Context
from django.utils.translation import ugettext as _
from django.utils.translation import activate, deactivate

from .base import CrispyTestCase
from .forms import CheckboxesTestForm, TestForm
from crispy_forms.bootstrap import (
    PrependedAppendedText, AppendedText, PrependedText, InlineRadios,
    Tab, TabHolder, AccordionGroup, Accordion, Alert, InlineCheckboxes,
    FieldWithButtons, StrictButton
)
from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
    Layout, HTML, Field, MultiWidgetField
)
from crispy_forms.utils import render_crispy_form


class TestLayoutObjects(CrispyTestCase):

    def test_multiwidget_field(self):
        template = loader.get_template_from_string(u"""
            {% load crispy_forms_tags %}
            {% crispy form %}
        """)

        test_form = TestForm()
        test_form.helper = FormHelper()
        test_form.helper.layout = Layout(
            MultiWidgetField(
                'datetime_field',
                attrs=(
                    {'rel': 'test_dateinput'},
                    {'rel': 'test_timeinput', 'style': 'width: 30px;', 'type': "hidden"}
                )
            )
        )

        c = Context({'form': test_form})

        html = template.render(c)

        self.assertEqual(html.count('class="dateinput'), 1)
        self.assertEqual(html.count('rel="test_dateinput"'), 1)
        self.assertEqual(html.count('rel="test_timeinput"'), 1)
        self.assertEqual(html.count('style="width: 30px;"'), 1)
        self.assertEqual(html.count('type="hidden"'), 1)

    def test_field_type_hidden(self):
        template = loader.get_template_from_string(u"""
            {% load crispy_forms_tags %}
            {% crispy test_form %}
        """)

        test_form = TestForm()
        test_form.helper = FormHelper()
        test_form.helper.layout = Layout(
            Field('email', type="hidden", data_test=12),
            Field('datetime_field'),
        )

        c = Context({
            'test_form': test_form,
        })
        html = template.render(c)

        # Check form parameters
        self.assertEqual(html.count('data-test="12"'), 1)
        self.assertEqual(html.count('name="email"'), 1)
        self.assertEqual(html.count('class="dateinput'), 1)
        self.assertEqual(html.count('class="timeinput'), 1)

    def test_field_wrapper_class(self):
        form = TestForm()
        form.helper = FormHelper()
        form.helper.layout = Layout(Field('email', wrapper_class="testing"))

        html = render_crispy_form(form)
        if self.current_template_pack == 'bootstrap':
            self.assertEqual(html.count('class="control-group testing"'), 1)
        elif self.current_template_pack == 'bootstrap3':
            self.assertEqual(html.count('class="form-group testing"'), 1)

    def test_html_with_carriage_returns(self):
        test_form = TestForm()
        test_form.helper = FormHelper()
        test_form.helper.layout = Layout(
            HTML("""
                if (a==b){
                    // some comment
                    a+1;
                    foo();
                }
            """)
        )
        html = render_crispy_form(test_form)

        if self.current_template_pack == 'uni_form':
            self.assertEqual(html.count('\n'), 23)
        elif self.current_template_pack == 'bootstrap':
            self.assertEqual(html.count('\n'), 25)
        else:
            self.assertEqual(html.count('\n'), 27)

    def test_i18n(self):
        activate('es')
        form = TestForm()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            HTML(_("Enter a valid value."))
        )
        html = render_crispy_form(form)
        self.assertTrue(u"Introduzca un valor correcto" in html)
        deactivate()


class TestBootstrapLayoutObjects(TestLayoutObjects):

    def test_custom_django_widget(self):
        class CustomRadioSelect(forms.RadioSelect):
            pass

        class CustomCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
            pass

        # Make sure an inherited RadioSelect gets rendered as it
        form = CheckboxesTestForm()
        form.fields['inline_radios'].widget = CustomRadioSelect()
        form.helper = FormHelper()
        form.helper.layout = Layout('inline_radios')

        html = render_crispy_form(form)
        self.assertTrue('class="radio"' in html)

        # Make sure an inherited CheckboxSelectMultiple gets rendered as it
        form.fields['checkboxes'].widget = CustomCheckboxSelectMultiple()
        form.helper.layout = Layout('checkboxes')
        html = render_crispy_form(form)
        self.assertTrue('class="checkbox"' in html)

    def test_prepended_appended_text(self):
        test_form = TestForm()
        test_form.helper = FormHelper()
        test_form.helper.layout = Layout(
            PrependedAppendedText('email', '@', 'gmail.com'),
            AppendedText('password1', '#'),
            PrependedText('password2', '$'),
        )
        html = render_crispy_form(test_form)

        # Check form parameters
        if self.current_template_pack == 'bootstrap':
            self.assertEqual(html.count('<span class="add-on">@</span>'), 1)
            self.assertEqual(html.count('<span class="add-on">gmail.com</span>'), 1)
            self.assertEqual(html.count('<span class="add-on">#</span>'), 1)
            self.assertEqual(html.count('<span class="add-on">$</span>'), 1)

        if self.current_template_pack == 'bootstrap3':
            self.assertEqual(html.count('<span class="input-group-addon">@</span>'), 1)
            self.assertEqual(html.count('<span class="input-group-addon">gmail.com</span>'), 1)
            self.assertEqual(html.count('<span class="input-group-addon">#</span>'), 1)
            self.assertEqual(html.count('<span class="input-group-addon">$</span>'), 1)

    def test_inline_radios(self):
        test_form = CheckboxesTestForm()
        test_form.helper = FormHelper()
        test_form.helper.layout = Layout(
            InlineRadios('inline_radios')
        )
        html = render_crispy_form(test_form)

        if self.current_template_pack == 'bootstrap':
            self.assertEqual(html.count('radio inline"'), 2)
        elif self.current_template_pack == 'bootstrap3':
            self.assertEqual(html.count('radio-inline"'), 2)

    def test_accordion_and_accordiongroup(self):
        test_form = TestForm()
        test_form.helper = FormHelper()
        test_form.helper.layout = Layout(
            Accordion(
                AccordionGroup(
                    'one',
                    'first_name'
                ),
                AccordionGroup(
                    'two',
                    'password1',
                    'password2'
                )
            )
        )
        html = render_crispy_form(test_form)

        if self.current_template_pack == 'bootstrap':
            self.assertEqual(html.count('<div class="accordion"'), 1)
            self.assertEqual(html.count('<div class="accordion-group">'), 2)
            self.assertEqual(html.count('<div class="accordion-heading">'), 2)
        else:
            self.assertEqual(html.count('<div class="panel panel-default"'), 2)
            self.assertEqual(html.count('<div class="panel-group"'), 1)
            self.assertEqual(html.count('<div class="panel-heading">'), 2)

        self.assertEqual(html.count('<div id="one"'), 1)
        self.assertEqual(html.count('<div id="two"'), 1)
        self.assertEqual(html.count('name="first_name"'), 1)
        self.assertEqual(html.count('name="password1"'), 1)
        self.assertEqual(html.count('name="password2"'), 1)

    def test_accordion_active_false_not_rendered(self):
        test_form = TestForm()
        test_form.helper = FormHelper()
        test_form.helper.layout = Layout(
            Accordion(
                AccordionGroup(
                    'one',
                    'first_name',
                ),
                # there is no ``active`` kwarg here.
            )
        )

        # The first time, there should be one of them there.
        html = render_crispy_form(test_form)

        if self.current_template_pack == 'bootstrap':
            accordion_class = "accordion-body"
        else:
            accordion_class = "panel-collapse"

        self.assertEqual(html.count('<div id="one" class="%s collapse in"' % accordion_class), 1)

        test_form.helper.layout = Layout(
            Accordion(
                AccordionGroup(
                    'one',
                    'first_name',
                    active=False,  # now ``active`` manually set as False
                ),
            )
        )

        # This time, it shouldn't be there at all.
        html = render_crispy_form(test_form)
        self.assertEqual(html.count('<div id="one" class="%s collapse in"' % accordion_class), 0)

    def test_alert(self):
        test_form = TestForm()
        test_form.helper = FormHelper()
        test_form.helper.layout = Layout(
            Alert(content='Testing...')
        )
        html = render_crispy_form(test_form)

        self.assertEqual(html.count('<div class="alert"'), 1)
        self.assertEqual(html.count('<button type="button" class="close"'), 1)
        self.assertEqual(html.count('Testing...'), 1)

    def test_alert_block(self):
        test_form = TestForm()
        test_form.helper = FormHelper()
        test_form.helper.layout = Layout(
            Alert(content='Testing...', block=True)
        )
        html = render_crispy_form(test_form)

        self.assertEqual(html.count('<div class="alert alert-block"'), 1)
        self.assertEqual(html.count('Testing...'), 1)

    def test_tab_and_tab_holder(self):
        test_form = TestForm()
        test_form.helper = FormHelper()
        test_form.helper.layout = Layout(
            TabHolder(
                Tab('one',
                    'first_name',
                    css_id="custom-name",
                    css_class="first-tab-class"
                ),
                Tab('two',
                    'password1',
                    'password2'
                )
            )
        )
        html = render_crispy_form(test_form)

        self.assertEqual(
            html.count(
                '<li class="tab-pane active"><a href="#custom-name" data-toggle="tab">One</a></li>'
            ),
            1
        )
        self.assertEqual(html.count('class="tab-pane first-tab-class active"'), 1)
        self.assertEqual(html.count('<li class="tab-pane'), 2)
        self.assertEqual(html.count('tab-pane'), 4)
        self.assertEqual(html.count('<div id="custom-name"'), 1)
        self.assertEqual(html.count('<div id="two"'), 1)
        self.assertEqual(html.count('name="first_name"'), 1)
        self.assertEqual(html.count('name="password1"'), 1)
        self.assertEqual(html.count('name="password2"'), 1)

    def test_tab_helper_reuse(self):
        # this is a proper form, according to the docs.
        # note that the helper is a class property here,
        # shared between all instances
        class TestForm(forms.Form):
            val1 = forms.CharField(required=False)
            val2 = forms.CharField(required=True)
            helper = FormHelper()
            helper.layout = Layout(
                TabHolder(
                    Tab('one', 'val1',),
                    Tab('two', 'val2',)
                )
            )

        # first render of form => everything is fine
        test_form = TestForm()
        html = render_crispy_form(test_form)

        # second render of form => first tab should be active,
        # but not duplicate class
        test_form = TestForm()
        html = render_crispy_form(test_form)
        self.assertEqual(html.count('class="tab-pane active active"'), 0)

        # render a new form, now with errors
        test_form = TestForm(data={'val1': 'foo'})
        html = render_crispy_form(test_form)
        # tab 1 should not be active
        self.assertEqual(html.count('<div id="one" \n    class="tab-pane active'), 0)
        # tab 2 should be active
        self.assertEqual(html.count('<div id="two" \n    class="tab-pane active'), 1)

    def test_radio_attrs(self):
        form = CheckboxesTestForm()
        form.fields['inline_radios'].widget.attrs = {'class': "first"}
        form.fields['checkboxes'].widget.attrs = {'class': "second"}
        html = render_crispy_form(form)
        self.assertTrue('class="first"' in html)
        self.assertTrue('class="second"' in html)

    def test_field_with_buttons(self):
        form = TestForm()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            FieldWithButtons(
                Field('password1', css_class="span4"),
                StrictButton("Go!", css_id="go-button"),
                StrictButton("No!", css_class="extra"),
                StrictButton("Test", type="submit", name="whatever", value="something"),
                css_class="extra",
                autocomplete="off"
            )
        )
        html = render_crispy_form(form)

        form_group_class = 'control-group'
        if self.current_template_pack == 'bootstrap3':
            form_group_class = 'form-group'

        self.assertEqual(html.count('class="%s extra"' % form_group_class), 1)
        self.assertEqual(html.count('autocomplete="off"'), 1)
        self.assertEqual(html.count('class="span4'), 1)
        self.assertEqual(html.count('id="go-button"'), 1)
        self.assertEqual(html.count("Go!"), 1)
        self.assertEqual(html.count("No!"), 1)
        self.assertEqual(html.count('class="btn"'), 2)
        self.assertEqual(html.count('class="btn extra"'), 1)
        self.assertEqual(html.count('type="submit"'), 1)
        self.assertEqual(html.count('name="whatever"'), 1)
        self.assertEqual(html.count('value="something"'), 1)

        if self.current_template_pack == 'bootstrap':
            self.assertEqual(html.count('class="input-append"'), 1)
        elif self.current_template_pack == 'bootstrap3':
            self.assertEqual(html.count('class="input-group-btn'), 1)

    def test_hidden_fields(self):
        form = TestForm()
        # All fields hidden
        for field in form.fields:
            form.fields[field].widget = forms.HiddenInput()

        form.helper = FormHelper()
        form.helper.layout = Layout(
            AppendedText('password1', 'foo'),
            PrependedText('password2', 'bar'),
            PrependedAppendedText('email', 'bar'),
            InlineCheckboxes('first_name'),
            InlineRadios('last_name'),
        )
        html = render_crispy_form(form)
        self.assertEqual(html.count("<input"), 5)
        self.assertEqual(html.count('type="hidden"'), 5)
        self.assertEqual(html.count('<label'), 0)

    def test_multiplecheckboxes(self):
        test_form = CheckboxesTestForm()
        html = render_crispy_form(test_form)

        self.assertEqual(html.count('checked="checked"'), 6)

        test_form.helper = FormHelper(test_form)
        test_form.helper[1].wrap(InlineCheckboxes, inline=True)
        html = render_crispy_form(test_form)

        if self.current_template_pack == 'bootstrap':
            self.assertEqual(html.count('checkbox inline"'), 3)
            self.assertEqual(html.count('inline"'), 3)
        elif self.current_template_pack == 'bootstrap3':
            self.assertEqual(html.count('checkbox-inline"'), 3)
            self.assertEqual(html.count('inline="True"'), 4)

########NEW FILE########
__FILENAME__ = test_settings
import os

from crispy_forms.compatibility import text_type


BASE_DIR = os.path.dirname(__file__)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.contenttypes',
    'django.contrib.admin',
    'crispy_forms',
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
)

ROOT_URLCONF = 'urls'
CRISPY_CLASS_CONVERTERS = {"textinput": "textinput textInput inputtext"}
SECRET_KEY = 'secretkey'
SITE_ROOT = os.path.dirname(os.path.abspath(__file__))


# http://djangosnippets.org/snippets/646/
class InvalidVarException(object):
    def __mod__(self, missing):
        try:
            missing_str = text_type(missing)
        except:
            missing_str = 'Failed to create string representation'
        raise Exception('Unknown template variable %r %s' % (missing, missing_str))

    def __contains__(self, search):
        if search == '%s':
            return True
        return False


TEMPLATE_DEBUG = True
TEMPLATE_STRING_IF_INVALID = InvalidVarException()

########NEW FILE########
__FILENAME__ = test_tags
# -*- coding: utf-8 -*-
from django.conf import settings
from django.forms.forms import BoundField
from django.forms.models import formset_factory
from django.template import loader, Context

from .base import CrispyTestCase
from .forms import TestForm
from crispy_forms.templatetags.crispy_forms_field import crispy_addon



class TestBasicFunctionalityTags(CrispyTestCase):
    def test_as_crispy_errors_form_without_non_field_errors(self):
        template = loader.get_template_from_string(u"""
            {% load crispy_forms_tags %}
            {{ form|as_crispy_errors }}
        """)
        form = TestForm({'password1': "god", 'password2': "god"})
        form.is_valid()

        c = Context({'form': form})
        html = template.render(c)
        self.assertFalse("errorMsg" in html or "alert" in html)

    def test_as_crispy_errors_form_with_non_field_errors(self):
        template = loader.get_template_from_string(u"""
            {% load crispy_forms_tags %}
            {{ form|as_crispy_errors }}
        """)
        form = TestForm({'password1': "god", 'password2': "wargame"})
        form.is_valid()

        c = Context({'form': form})
        html = template.render(c)
        self.assertTrue("errorMsg" in html or "alert" in html)
        self.assertTrue("<li>Passwords dont match</li>" in html)
        self.assertFalse("<h3>" in html)

    def test_crispy_filter_with_form(self):
        template = loader.get_template_from_string(u"""
            {% load crispy_forms_tags %}
            {{ form|crispy }}
        """)
        c = Context({'form': TestForm()})
        html = template.render(c)

        self.assertTrue("<td>" not in html)
        self.assertTrue("id_is_company" in html)
        self.assertEqual(html.count('<label'), 7)

    def test_crispy_filter_with_formset(self):
        template = loader.get_template_from_string(u"""
            {% load crispy_forms_tags %}
            {{ testFormset|crispy }}
        """)

        TestFormset = formset_factory(TestForm, extra=4)
        testFormset = TestFormset()

        c = Context({'testFormset': testFormset})
        html = template.render(c)

        self.assertEqual(html.count('<form'), 0)
        # Check formset management form
        self.assertTrue('form-TOTAL_FORMS' in html)
        self.assertTrue('form-INITIAL_FORMS' in html)
        self.assertTrue('form-MAX_NUM_FORMS' in html)

    def test_classes_filter(self):
        template = loader.get_template_from_string(u"""
            {% load crispy_forms_field %}
            {{ testField|classes }}
        """)

        test_form = TestForm()
        test_form.fields['email'].widget.attrs.update({'class': 'email-fields'})
        c = Context({'testField': test_form.fields['email']})
        html = template.render(c)
        self.assertTrue('email-fields' in html)

    def test_crispy_field_and_class_converters(self):
        if hasattr(settings, 'CRISPY_CLASS_CONVERTERS'):
            template = loader.get_template_from_string(u"""
                {% load crispy_forms_field %}
                {% crispy_field testField 'class' 'error' %}
            """)
            test_form = TestForm()
            field_instance = test_form.fields['email']
            bound_field = BoundField(test_form, field_instance, 'email')

            c = Context({'testField': bound_field})
            html = template.render(c)
            self.assertTrue('error' in html)
            self.assertTrue('inputtext' in html)

    def test_crispy_addon(self):
        test_form = TestForm()
        field_instance = test_form.fields['email']
        bound_field = BoundField(test_form, field_instance, 'email')

        if self.current_template_pack == 'bootstrap':
            # prepend tests
            self.assertIn("input-prepend", crispy_addon(bound_field, prepend="Work"))
            self.assertNotIn("input-append", crispy_addon(bound_field, prepend="Work"))
            # append tests
            self.assertNotIn("input-prepend", crispy_addon(bound_field, append="Primary"))
            self.assertIn("input-append", crispy_addon(bound_field, append="Secondary"))
            # prepend and append tests
            self.assertIn("input-append", crispy_addon(bound_field, prepend="Work", append="Primary"))
            self.assertIn("input-prepend", crispy_addon(bound_field, prepend="Work", append="Secondary"))
        elif self.current_template_pack == 'bootsrap3':
            self.assertIn("input-group-addon", crispy_addon(bound_field, prepend="Work", append="Primary"))
            self.assertIn("input-group-addon", crispy_addon(bound_field, prepend="Work", append="Secondary"))

        # errors
        with self.assertRaises(TypeError):
            crispy_addon()
            crispy_addon(bound_field)

########NEW FILE########
__FILENAME__ = urls
import django

if django.get_version() >= '1.5':
    from django.conf.urls import patterns, url
else:
    from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
    url(r'^simple/action/$', 'simpleAction', name = 'simpleAction'),
)

########NEW FILE########
__FILENAME__ = utils
__all__ = ('override_settings',)


try:
    from django.test.utils import override_settings
except ImportError:
    # we are in Django 1.3
    from django.conf import settings, UserSettingsHolder
    from django.utils.functional import wraps

    class override_settings(object):
        """
        Acts as either a decorator, or a context manager. If it's a decorator
        it takes a function and returns a wrapped function. If it's a
        contextmanager it's used with the ``with`` statement. In either event
        entering/exiting are called before and after, respectively,
        the function/block is executed.

        This class was backported from Django 1.5

        As django.test.signals.setting_changed is not supported in 1.3,
        it's not sent on changing settings.
        """
        def __init__(self, **kwargs):
            self.options = kwargs
            self.wrapped = settings._wrapped

        def __enter__(self):
            self.enable()

        def __exit__(self, exc_type, exc_value, traceback):
            self.disable()

        def __call__(self, test_func):
            from django.test import TransactionTestCase
            if isinstance(test_func, type):
                if not issubclass(test_func, TransactionTestCase):
                    raise Exception(
                        "Only subclasses of Django SimpleTestCase "
                        "can be decorated with override_settings")
                original_pre_setup = test_func._pre_setup
                original_post_teardown = test_func._post_teardown

                def _pre_setup(innerself):
                    self.enable()
                    original_pre_setup(innerself)

                def _post_teardown(innerself):
                    original_post_teardown(innerself)
                    self.disable()
                test_func._pre_setup = _pre_setup
                test_func._post_teardown = _post_teardown
                return test_func
            else:
                @wraps(test_func)
                def inner(*args, **kwargs):
                    with self:
                        return test_func(*args, **kwargs)
            return inner

        def enable(self):
            override = UserSettingsHolder(settings._wrapped)
            for key, new_value in self.options.items():
                setattr(override, key, new_value)
            settings._wrapped = override

        def disable(self):
            settings._wrapped = self.wrapped

########NEW FILE########
__FILENAME__ = utils
from __future__ import with_statement
import inspect
import logging
import sys

from django.conf import settings
from django.forms.forms import BoundField
from django.template import Context
from django.template.loader import get_template
from django.utils.html import conditional_escape
from django.utils.functional import memoize

from .base import KeepContext
from .compatibility import text_type, PY2

# Global field template, default template used for rendering a field.

TEMPLATE_PACK = getattr(settings, 'CRISPY_TEMPLATE_PACK', 'bootstrap')


# By memoizeing we avoid loading the template every time render_field
# is called without a template
def default_field_template(template_pack=TEMPLATE_PACK):
    return get_template("%s/field.html" % template_pack)
default_field_template = memoize(default_field_template, {}, 1)


def render_field(
    field, form, form_style, context, template=None, labelclass=None,
    layout_object=None, attrs=None, template_pack=TEMPLATE_PACK,
    extra_context=None, **kwargs
):
    """
    Renders a django-crispy-forms field

    :param field: Can be a string or a Layout object like `Row`. If it's a layout
        object, we call its render method, otherwise we instantiate a BoundField
        and render it using default template 'CRISPY_TEMPLATE_PACK/field.html'
        The field is added to a list that the form holds called `rendered_fields`
        to avoid double rendering fields.
    :param form: The form/formset to which that field belongs to.
    :param form_style: A way to pass style name to the CSS framework used.
    :template: Template used for rendering the field.
    :layout_object: If passed, it points to the Layout object that is being rendered.
        We use it to store its bound fields in a list called `layout_object.bound_fields`
    :attrs: Attributes for the field's widget
    :template_pack: Name of the template pack to be used for rendering `field`
    :extra_context: Dictionary to be added to context, added variables by the layout object
    """
    added_keys = [] if extra_context is None else extra_context.keys()
    with KeepContext(context, added_keys):
        if field is None:
            return ''

        FAIL_SILENTLY = getattr(settings, 'CRISPY_FAIL_SILENTLY', True)

        if hasattr(field, 'render'):
            return field.render(
                form, form_style, context, template_pack=template_pack,
            )
        else:
            # In Python 2 form field names cannot contain unicode characters without ASCII mapping
            if PY2:
                # This allows fields to be unicode strings, always they don't use non ASCII
                try:
                    if isinstance(field, text_type):
                        field = field.encode('ascii').decode()
                    # If `field` is not unicode then we turn it into a unicode string, otherwise doing
                    # str(field) would give no error and the field would not be resolved, causing confusion
                    else:
                        field = text_type(field)

                except (UnicodeEncodeError, UnicodeDecodeError):
                    raise Exception("Field '%s' is using forbidden unicode characters" % field)

        try:
            # Injecting HTML attributes into field's widget, Django handles rendering these
            field_instance = form.fields[field]
            if attrs is not None:
                widgets = getattr(field_instance.widget, 'widgets', [field_instance.widget])

                # We use attrs as a dictionary later, so here we make a copy
                list_attrs = attrs
                if isinstance(attrs, dict):
                    list_attrs = [attrs] * len(widgets)

                for index, (widget, attr) in enumerate(zip(widgets, list_attrs)):
                    if hasattr(field_instance.widget, 'widgets'):
                        if 'type' in attr and attr['type'] == "hidden":
                            field_instance.widget.widgets[index].is_hidden = True
                            field_instance.widget.widgets[index] = field_instance.hidden_widget()

                        field_instance.widget.widgets[index].attrs.update(attr)
                    else:
                        if 'type' in attr and attr['type'] == "hidden":
                            field_instance.widget.is_hidden = True
                            field_instance.widget = field_instance.hidden_widget()

                        field_instance.widget.attrs.update(attr)

        except KeyError:
            if not FAIL_SILENTLY:
                raise Exception("Could not resolve form field '%s'." % field)
            else:
                field_instance = None
                logging.warning("Could not resolve form field '%s'." % field, exc_info=sys.exc_info())

        if hasattr(form, 'rendered_fields'):
            if not field in form.rendered_fields:
                form.rendered_fields.add(field)
            else:
                if not FAIL_SILENTLY:
                    raise Exception("A field should only be rendered once: %s" % field)
                else:
                    logging.warning("A field should only be rendered once: %s" % field, exc_info=sys.exc_info())

        if field_instance is None:
            html = ''
        else:
            bound_field = BoundField(form, field_instance, field)

            if template is None:
                if form.crispy_field_template is None:
                    template = default_field_template(template_pack)
                else:   # FormHelper.field_template set
                    template = get_template(form.crispy_field_template)
            else:
                template = get_template(template)

            # We save the Layout object's bound fields in the layout object's `bound_fields` list
            if layout_object is not None:
                if hasattr(layout_object, 'bound_fields') and isinstance(layout_object.bound_fields, list):
                    layout_object.bound_fields.append(bound_field)
                else:
                    layout_object.bound_fields = [bound_field]

            context.update({
                'field': bound_field,
                'labelclass': labelclass,
                'flat_attrs': flatatt(attrs if isinstance(attrs, dict) else {}),
            })
            if extra_context is not None:
                context.update(extra_context)
            html = template.render(context)

        return html


def flatatt(attrs):
    """
    Taken from django.core.utils
    Convert a dictionary of attributes to a single string.
    The returned string will contain a leading space followed by key="value",
    XML-style pairs.  It is assumed that the keys do not need to be XML-escaped.
    If the passed dictionary is empty, then return an empty string.
    """
    return u''.join([u' %s="%s"' % (k.replace('_', '-'), conditional_escape(v)) for k, v in attrs.items()])


def render_crispy_form(form, helper=None, context=None):
    """
    Renders a form and returns its HTML output.

    This function wraps the template logic in a function easy to use in a Django view.
    """
    from crispy_forms.templatetags.crispy_forms_tags import CrispyFormNode

    if helper is not None:
        node = CrispyFormNode('form', 'helper')
    else:
        node = CrispyFormNode('form', None)

    node_context = Context(context)
    node_context.update({
        'form': form,
        'helper': helper
    })

    return node.render(node_context)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-crispy-forms documentation build configuration file, created by
# sphinx-quickstart on Mon Mar  8 22:42:02 2010.
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
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath('../crispy_forms'))
sys.path.insert(0, os.path.abspath('../crispy_forms/templatetags'))
sys.path.append(os.path.abspath('_themes'))

from django.conf import settings
settings.configure()


# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-crispy-forms'
copyright = u'2009-2013, Miguel Araujo and Daniel Greenfeld'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.0'
# The full version, including alpha/beta/rc tags.
release = '1.0.0'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

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

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'kr'

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
html_sidebars = {
    'index':    ['sidebarintro.html', 'sourcelink.html', 'searchbox.html'],
    '**':       ['sidebarintro.html', 'localtoc.html', 'relations.html',
                 'sourcelink.html', 'searchbox.html']
}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'django-crispy-formdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-crispy-forms.tex', u'django-crispy-forms Documentation',
   u'Miguel Araujo', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = settings
import os

SITE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)))

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATE_DIRS = (os.path.join(SITE_ROOT, 'templates'))

INSTALLED_APPS = (
    'crispy_forms'
)
SECRET_KEY = "secretkey"

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
