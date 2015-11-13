__FILENAME__ = admin
from django.contrib.admin import ModelAdmin
from django.db.models import FieldDoesNotExist, ForeignKey, URLField
from django.conf import settings

from adminbrowse.related import link_to_change
from adminbrowse.columns import link_to_url


class AutoBrowseModelAdmin(ModelAdmin):
    """
    Subclass this to automatically enable a subset of adminbrowse features:

    - Linking to the change form for `ForeignKey` fields.
    - Linking to the URL for `URLField` fields.

    This will also include the adminbrowse media definition.
    
    """
    def __init__(self, model, admin_site):
        super(AutoBrowseModelAdmin, self).__init__(model, admin_site)
        for i, name in enumerate(self.list_display):
            if isinstance(name, basestring):
                try:
                    field, model_, direct, m2m = \
                        self.opts.get_field_by_name(name)
                except FieldDoesNotExist:
                    pass
                else:
                    column = self._get_changelist_column(field)
                    if column is not None:
                        self.list_display[i] = column

    def _get_changelist_column(self, field):
        if isinstance(field, ForeignKey):
            return link_to_change(self.model, field.name)
        elif isinstance(field, URLField):
            return link_to_url(self.model, field.name)

    class Media:
        css = {'all': (settings.ADMINBROWSE_MEDIA_URL +
                       'css/adminbrowse.css',)}


########NEW FILE########
__FILENAME__ = base
from django.contrib import admin
from django.template.loader import render_to_string
from django.db.models import FieldDoesNotExist
from django.utils.text import force_unicode


class ChangeListColumn(object):
    """Base class for changelist columns. Must be subclassed.

    Subclasses should initialize this class with the desired
    `short_description` and `admin_order_field`, if applicable.

    The only method that must be implemented is `__call__()`,
    which takes the object for which a changelist row is being rendered.
    If `__call__()` returns HTML content intended to be rendered, the
    class or instance should set `allow_tags` to True.

    """
    allow_tags = False

    def __init__(self, short_description, admin_order_field=None):
        self.short_description = short_description
        self.admin_order_field = admin_order_field

    def __call__(self, obj):
        raise NotImplementedError

class ChangeListTemplateColumn(ChangeListColumn):
    """Class for rendering changelist column content from a template.

    Instances should set `short_description` and `template_name`. If
    `template_name` is not provided in the constructor, it will be taken from
    the class member.
    
    The default template context contains two variables: `column` (the
    `ChangeListColumn` instance), and `object` (the object for which a
    changelist row is being rendered). Additional context variables may be
    added by setting `extra_context`.

    This class is aliased as `adminbrowse.template_column` for better
    readability in `ModelAdmin` code.

    """
    allow_tags = True
    extra_context = {}

    def __init__(self, short_description, template_name=None,
                 extra_context=None, admin_order_field=None):
        ChangeListColumn.__init__(self, short_description, admin_order_field)
        self.template_name = template_name or self.template_name
        self.extra_context = extra_context or self.extra_context

    def __call__(self, obj):
        context = self.get_context(obj)
        return render_to_string(self.template_name, context)

    def get_context(self, obj):
        context = {'column': self, 'object': obj}
        context.update(self.extra_context)
        return context

class ChangeListModelFieldColumn(ChangeListColumn):
    def __init__(self, model, name, short_description=None, default=""):
        ChangeListColumn.__init__(self, short_description, None)
        self.field_name = name
        try:
            field, model_, self.direct, self.m2m = \
                model._meta.get_field_by_name(name)
        except FieldDoesNotExist:
            descriptor = getattr(model, name)
            field = descriptor.related
            self.direct = False
            self.m2m = True
        if self.direct:
            self.field = field
            self.model = field.model
            self.opts = self.model._meta
            if not self.m2m:
                self.admin_order_field = name
        else:
            self.field = field.field
            self.model = field.parent_model
            self.opts = field.parent_model._meta
        if self.short_description is None:
            if self.direct:
                self.short_description = force_unicode(field.verbose_name)
            else:
                self.short_description = force_unicode(name.replace('_', ' '))
        self.default = default

    def __call__(self, obj):
        value = getattr(obj, self.field_name)
        if value is not None:
            return force_unicode(value)
        else:
            return self.default

template_column = ChangeListTemplateColumn
model_field = ChangeListModelFieldColumn


########NEW FILE########
__FILENAME__ = columns
# -*- coding: utf-8 -*-
from django.utils.text import force_unicode
from django.utils.translation import ugettext as _

from adminbrowse.base import ChangeListModelFieldColumn


class URLColumn(ChangeListModelFieldColumn):
    """Changelist column that links to the URL from the specified field.

    `model` is the model class for which a changelist is being rendered,
    and `name` is the name of the field containing a URL. If not provided,
    `short_description` will be set to the field's `verbose_name`.

    If an instance's URL field is empty, the column will display the value
    of `default`, which defaults to the empty string.

    The rendered link will have class="..." and target="..." attributes
    defined by the `target` and `classes` arguments, which default to
    '_blank' and 'external', respectively. Include the `adminbrowse`
    CSS file in the ModelAdmin's `Media` definition to style this default
    class with an "external link" icon.

    This class is aliased as `adminbrowse.link_to_url` for better readability
    in `ModelAdmin` code.

    """
    allow_tags = True

    def __init__(self, model, name, short_description=None, default="",
                 target='_blank', classes='external'):
        ChangeListModelFieldColumn.__init__(self, model, name,
                                            short_description, default)
        self.target = target
        if isinstance(classes, basestring):
            classes = classes.split()
        self.classes = list(classes)

    def __call__(self, obj):
        value = getattr(obj, self.field_name)
        if value:
            title = self.get_title(obj, value)
            classes = " ".join(self.classes)
            html = '<a href="%s" target="%s" class="%s" title="%s">%s</a>'
            return html % (value, self.target, classes, title, value)
        else:
            return self.default

    def get_title(self, obj, value):
        if self.target == '_blank':
            return _("Open URL in a new window")
        else:
            return _("Open URL")

class TruncatedFieldColumn(ChangeListModelFieldColumn):
    """
    Changelist column that truncates the value of a field to the specified
    length.

    `model` is the model class for which a changelist is being rendered,
    and `name` is the name of the field to render. The string value of the
    field will be truncated to the length given by `max_length` (required).
    If not provided, `short_description` will be set to the field's
    `verbose_name`.

    If an instance's field is empty, the column will display the value of
    `default`, which defaults to the empty string.

    The `tail` argument specifies the final truncation string, and defaults to
    an ellipsis.

    This class is aliased as `adminbrowse.truncated_field` for better
    readability in `ModelAdmin` code.

    """
    def __init__(self, model, name, max_length, short_description=None,
                 default="", tail=u"…"):
        ChangeListModelFieldColumn.__init__(self, model, name,
                                            short_description, default)
        self.max_length = max_length
        self.tail = tail

    def __call__(self, obj):
        value = getattr(obj, self.field_name)
        if value:
            text = force_unicode(value)
            if len(text) > self.max_length:
                text = text[:self.max_length] + self.tail
            return text
        else:
            return self.default

link_to_url = URLColumn
truncated_field = TruncatedFieldColumn


########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = related
from django.contrib import admin
from django.utils.text import force_unicode
from django.utils.translation import ugettext as _
from django.db.models import FieldDoesNotExist
from django.core.urlresolvers import reverse

from adminbrowse.base import (ChangeListModelFieldColumn,
                              ChangeListTemplateColumn)


def admin_view_name(model_or_instance, short_name, site=admin.site):
    """
    Return the full name of the admin view given by `short_name` for
    the model given by `model_or_instance`. For example:

    >>> from django.contrib.auth.models import User
    >>> admin_view_name(User, 'changelist')
    'admin:auth_user_changelist'

    >>> from django.contrib.admin import AdminSite
    >>> test_site = AdminSite('test')
    >>> admin_view_name(User, 'change', site=test_site)
    'test:auth_user_change'

    """
    opts = model_or_instance._meta
    app_label, module_name = opts.app_label, opts.module_name
    return '%s:%s_%s_%s' % (site.name, app_label, module_name, short_name)


class ChangeLink(ChangeListTemplateColumn, ChangeListModelFieldColumn):
    """
    Changelist column that adds a link to the change view of the object in the
    specified foreign key field.

    If an instance's foreign key field is empty, the column will display the
    value of `default`, which defaults to the empty string.

    Include the `adminbrowse` CSS file in the ModelAdmin's `Media` definition
    to apply default styles to the link.

    This class is aliased as `adminbrowse.link_to_change` for better
    readability in `ModelAdmin` code.

    """
    template_name = "adminbrowse/link_to_change.html"

    def __init__(self, model, name, short_description=None, default="",
                 template_name=None, extra_context=None):
        ChangeListTemplateColumn.__init__(self, short_description,
                                          template_name or self.template_name,
                                          extra_context, name)
        ChangeListModelFieldColumn.__init__(self, model, name,
                                            short_description, default)
        self.to_model = self.field.rel.to
        self.to_opts = self.to_model._meta
        self.to_field = self.field.rel.field_name

    def get_context(self, obj):
        value  = getattr(obj, self.field_name)
        if value is not None:
            url = self.get_change_url(obj, value)
            title = self.get_title(obj, value)
        else:
            url = title = None
        context = {'column': self, 'object': obj, 'value': value, 'url': url,
                   'title': title}
        context.update(self.extra_context)
        return context

    def get_change_url(self, obj, value):
        view_name = admin_view_name(value, 'change')
        return reverse(view_name, args=[value.pk])

    def get_title(self, obj, value):
        strings = {'field_verbose_name': self.field.verbose_name}
        return _("Go to %(field_verbose_name)s") % strings

class RelatedList(ChangeListModelFieldColumn):
    """
    Changelist column that displays a textual list of the related objects
    in the specified many-to-many or one-to-many field.

    If an instance's has no related objects for the given field, the column
    will display the value of `default`, which defaults to the empty string.

    The `sep` argument specifies the separator to place between the string
    representation of each object.

    This class is aliased as `adminbrowse.related_list` for better
    readability in `ModelAdmin` code.

    """

    def __init__(self, model, name, short_description=None, default="",
                 sep=", "):
        ChangeListModelFieldColumn.__init__(self, model, name,
                                            short_description, default)
        if self.direct:
            self.to_model = self.field.related.parent_model
            self.to_opts = self.to_model._meta
            self.reverse_name = self.field.rel.related_name
            self.rel_name = self.opts.pk.name
        else:
            self.to_model = self.field.model
            self.to_opts = self.field.opts
            self.reverse_name = self.field.name
            if self.m2m:
                self.rel_name = self.field.rel.get_related_field().name
            else:
                self.rel_name = self.field.rel.field_name
        self.sep = sep

    def __call__(self, obj):
        related = getattr(obj, self.field_name).all()
        if related:
            return self.sep.join(map(force_unicode, related))
        else:
            return self.default

class ChangeListLink(ChangeListTemplateColumn, ChangeListModelFieldColumn):
    """
    Changelist column that adds a link to a changelist view containing only
    the related objects in the specified many-to-many or one-to-many field.

    The `text` argument sets the link text. If `text` is a callabe, it will
    be called with the (unevaluated) `QuerySet` for the related objects. If
    `text` is False in a boolean context ("", 0, etc.), the value of `default`
    will be rendered instead of the link. The default `text` returns the
    number of items in the `QuerySet`, so no link will be displayed if there
    are no related objects.

    Include the `adminbrowse` CSS file in the ModelAdmin's `Media` definition
    to apply default styles to the link.

    This class is aliased as `adminbrowse.link_to_changelist` for better
    readability in `ModelAdmin` code.

    """
    template_name = "adminbrowse/link_to_changelist.html"

    def __init__(self, model, name, short_description=None, text=len,
                 default="", template_name=None, extra_context=None):
        ChangeListTemplateColumn.__init__(self, short_description,
                                          template_name or self.template_name,
                                          extra_context)
        ChangeListModelFieldColumn.__init__(self, model, name,
                                            short_description, default)
        if self.direct:
            self.to_model = self.field.related.parent_model
            self.to_opts = self.to_model._meta
            self.reverse_name = self.field.rel.related_name
            self.rel_name = self.opts.pk.name
        else:
            self.to_model = self.field.model
            self.to_opts = self.field.opts
            self.reverse_name = self.field.name
            if self.m2m:
                self.rel_name = self.field.rel.get_related_field().name
            else:
                self.rel_name = self.field.rel.field_name
        self.text = text

    def get_context(self, obj):
        value  = getattr(obj, self.field_name).all()
        text = self.text
        if callable(text):
            text = text(value)
        if text:
            url = self.get_changelist_url(obj, value)
            title = self.get_title(obj, value)
        else:
            url = title = None
        context = {'column': self, 'object': obj, 'value': value,
                   'text': text, 'url': url, 'title': title}
        context.update(self.extra_context)
        return context

    def get_changelist_url(self, obj, value):
        view_name = admin_view_name(self.to_model, 'changelist')
        lookup_kwarg = '%s__%s__exact' % (self.reverse_name, self.rel_name)
        lookup_id = getattr(obj, self.rel_name)
        return reverse(view_name) + '?%s=%s' % (lookup_kwarg, lookup_id)

    def get_title(self, obj, value):
        strings = {
            'related_verbose_name_plural': self.to_opts.verbose_name_plural,
            'object_verbose_name': self.opts.verbose_name if self.m2m else
                                   self.field.verbose_name}
        return _("List %(related_verbose_name_plural)s with this "
                 "%(object_verbose_name)s") % strings

link_to_change = ChangeLink
link_to_changelist = ChangeListLink
related_list = RelatedList


########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
from django.test import TestCase
from django.db import models
from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.admin.models import LogEntry
from django.conf.urls.defaults import *
from django.core.management import call_command

from adminbrowse import (link_to_change, link_to_changelist, related_list,
                         link_to_url, truncated_field, AutoBrowseModelAdmin)


# Test models that will give the functionality under test good coverage.

class Person(models.Model):
    pid = models.AutoField(primary_key=True)
    name = models.CharField(max_length=75)
    website = models.URLField("home page", blank=True)

    class Meta:
        app_label = 'adminbrowse'

    def __unicode__(self):
        return self.name

class Genre(models.Model):
    gid = models.AutoField(primary_key=True)
    label = models.CharField(max_length=75)

    class Meta:
        app_label = 'adminbrowse'

    def __unicode__(self):
        return self.label

class Book(models.Model):
    bid = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Person, null=True, related_name='bibliography')
    categories = models.ManyToManyField(Genre, related_name='collection')
    loc_url = models.URLField("Library of Congress URL", blank=True)

    class Meta:
        app_label = 'adminbrowse'

    def __unicode__(self):
        return self.title

test_site = admin.AdminSite('test')
test_site.register(Person)
test_site.register(Genre)
test_site.register(Book)
test_site.register(User)
test_site.register(Group)
test_site.register(LogEntry)
# An atypical admin path for the test site.
urlpatterns = patterns('', (r'^foo/admin/bar/', include(test_site.urls)))

def setup_test_models(sender, **kwargs):
    import adminbrowse.models
    if sender is adminbrowse.models and not setup_test_models.done:
        setup_test_models.done = True
        for model in [Person, Genre, Book]:
            setattr(adminbrowse.models, model.__name__, model)
        call_command('syncdb')
setup_test_models.done = False
models.signals.post_syncdb.connect(setup_test_models)

class TestChangeLink(TestCase):
    urls = 'adminbrowse.tests'
    fixtures = ['test_adminbrowse.json']

    def setUp(self):
        self.people = Person.objects.all()
        self.books = Book.objects.all()
        self.link = link_to_change(Book, 'author')

    def test_allow_tags_is_true(self):
        self.assertEqual(self.link.allow_tags, True)

    def test_admin_order_field_is_field_name(self):
        self.assertEqual(self.link.admin_order_field, 'author')

    def test_call_returns_html(self):
        url = "/foo/admin/bar/adminbrowse/person/2/"
        self.assertEqual(self.link(self.books[1]).strip(),
            '<span class="change-link"><a href="%s" title="Go to author"></a>'
            ' Ernest Hemingway</span>' % url)
        url = "/foo/admin/bar/adminbrowse/person/3/"
        self.assertEqual(self.link(self.books[3]).strip(),
            '<span class="change-link"><a href="%s" title="Go to author"></a>'
            ' Kurt Vonnegut</span>' % url)

    def test_short_description_defaults_to_verbose_name(self):
        self.assertEqual(self.link.short_description, u"author")

    def test_short_description_sets_short_description(self):
        link = link_to_change(Book, 'author', short_description="written by")
        self.assertEqual(link.short_description, "written by")

    def test_default_sets_html_for_empty_field(self):
        link = link_to_change(Book, 'author', default="Unknown author")
        self.assertEqual(link(self.books[5]).strip(), "Unknown author")

    def test_default_defaults_to_empty_string(self):
        self.assertEqual(self.link(self.books[5]).strip(), "")

class TestOneToManyChangeListLink(TestCase):
    urls = 'adminbrowse.tests'
    fixtures = ['test_adminbrowse.json']

    def setUp(self):
        self.people = Person.objects.all()
        self.books = Book.objects.all()
        self.link = link_to_changelist(Person, 'bibliography')

    def test_allow_tags_is_true(self):
        self.assertEqual(self.link.allow_tags, True)

    def test_admin_order_field_is_none(self):
        self.assertEqual(self.link.admin_order_field, None)

    def test_call_returns_html(self):
        url = "/foo/admin/bar/adminbrowse/book/?author__pid__exact=2"
        title = "List books with this author"
        self.assertEqual(self.link(self.people[1]).strip(),
            '<span class="changelist-link"><a href="%s" title="%s">3</a>'
            '</span>' % (url, title))
        url = "/foo/admin/bar/adminbrowse/book/?author__pid__exact=3"
        title = "List books with this author"
        self.assertEqual(self.link(self.people[2]).strip(),
            '<span class="changelist-link"><a href="%s" title="%s">2</a>'
            '</span>' % (url, title))

    def test_short_description_defaults_to_field_name(self):
        self.assertEqual(self.link.short_description, u"bibliography")

    def test_short_description_sets_short_description(self):
        link = link_to_changelist(Person, 'bibliography', "novels")
        self.assertEqual(link.short_description, "novels")

    def test_text_sets_rendered_link_text(self):
        link = link_to_changelist(Person, 'bibliography',
                                  text="List bibliography")
        url = "/foo/admin/bar/adminbrowse/book/?author__pid__exact=3"
        title = "List books with this author"
        self.assertEqual(link(self.people[2]).strip(),
            '<span class="changelist-link"><a href="%s" title="%s">List'
            ' bibliography</a></span>' % (url, title))

    def test_callable_text_gets_called_with_value(self):
        link = link_to_changelist(Person, 'bibliography',
                                  text=lambda x: "List books (%s)" % len(x))
        url = "/foo/admin/bar/adminbrowse/book/?author__pid__exact=3"
        title = "List books with this author"
        self.assertEqual(link(self.people[2]).strip(),
            '<span class="changelist-link"><a href="%s" title="%s">List'
            ' books (2)</a></span>' % (url, title))

    def test_default_sets_html_for_empty_text(self):
        link = link_to_changelist(Person, 'bibliography', default="No books")
        self.assertEqual(link(self.people[0]).strip(), "No books")

    def test_html_for_empty_set_defaults_to_empty_string(self):
        self.assertEqual(self.link(self.people[0]).strip(), "")

    def test_html_for_empty_text_defauls_to_empty_string(self):
        link = link_to_changelist(Person, 'bibliography', text="")
        self.assertEqual(link(self.people[2]).strip(), "")

class TestIndirectManyToManyChangeListLink(TestCase):
    urls = 'adminbrowse.tests'
    fixtures = ['test_adminbrowse.json']

    def setUp(self):
        self.genres = Genre.objects.all()
        self.books = Book.objects.all()
        self.link = link_to_changelist(Genre, 'collection')

    def test_allow_tags_is_true(self):
        self.assertEqual(self.link.allow_tags, True)

    def test_admin_order_field_is_none(self):
        self.assertEqual(self.link.admin_order_field, None)

    def test_call_returns_html(self):
        url = "/foo/admin/bar/adminbrowse/book/?categories__gid__exact=1"
        title = "List books with this genre"
        self.assertEqual(self.link(self.genres[0]).strip(),
            '<span class="changelist-link"><a href="%s" title="%s">3</a>'
            '</span>' % (url, title))

    def test_short_description_defaults_to_field_name(self):
        self.assertEqual(self.link.short_description, u"collection")

    def test_short_description_sets_short_description(self):
        link = link_to_changelist(Genre, 'collection', "novels")
        self.assertEqual(link.short_description, "novels")

    def test_html_for_empty_set_defaults_to_empty_string(self):
        self.assertEqual(self.link(self.genres[4]).strip(), "")

    def test_default_sets_html_for_empty_set(self):
        link = link_to_changelist(Genre, 'collection', default="No books")
        self.assertEqual(link(self.genres[4]).strip(), "No books")

    def test_default_defaults_to_empty_string(self):
        self.assertEqual(self.link(self.genres[4]).strip(), "")

class TestDefaultRelatedNameChangeListLink(TestCase):
    def setUp(self):
        self.one_to_many = link_to_changelist(User, 'logentry_set')
        self.many_to_many = link_to_changelist(Group, 'user_set')

    def test_short_description_is_accessor_with_spaces(self):
        self.assertEqual(self.one_to_many.short_description, u"logentry set")
        self.assertEqual(self.many_to_many.short_description, u"user set")

class TestDirectManyToManyChangeListLink(TestCase):
    urls = 'adminbrowse.tests'
    fixtures = ['test_adminbrowse.json']

    def setUp(self):
        self.genres = Genre.objects.all()
        self.books = Book.objects.all()
        self.link = link_to_changelist(Book, 'categories')

    def test_allow_tags_is_true(self):
        self.assertEqual(self.link.allow_tags, True)

    def test_admin_order_field_is_none(self):
        self.assertEqual(self.link.admin_order_field, None)

    def test_call_returns_html(self):
        url = "/foo/admin/bar/adminbrowse/genre/?collection__bid__exact=5"
        title = "List genres with this book"
        self.assertEqual(self.link(self.books[4]).strip(),
            '<span class="changelist-link"><a href="%s" title="%s">2</a>'
            '</span>' % (url, title))

    def test_short_description_defaults_to_verbose_name(self):
        self.assertEqual(self.link.short_description, u"categories")

    def test_short_description_sets_short_description(self):
        link = link_to_changelist(Book, 'categories', "genres")
        self.assertEqual(link.short_description, "genres")

    def test_html_for_empty_set_defaults_to_empty_string(self):
        self.assertEqual(self.link(self.books[5]).strip(), "")

    def test_default_sets_html_for_empty_set(self):
        link = link_to_changelist(Book, 'categories', default="No genres")
        self.assertEqual(link(self.books[5]).strip(), "No genres")

class TestOneToManyRelatedList(TestCase):
    urls = 'adminbrowse.tests'
    fixtures = ['test_adminbrowse.json']

    def setUp(self):
        self.people = Person.objects.all()
        self.books = Book.objects.all()
        self.column = related_list(Person, 'bibliography')

    def test_allow_tags_is_false(self):
        self.assertEqual(self.column.allow_tags, False)

    def test_admin_order_field_is_none(self):
        self.assertEqual(self.column.admin_order_field, None)

    def test_short_description_defaults_to_field_name(self):
        self.assertEqual(self.column.short_description, u"bibliography")

    def test_call_returns_comma_separated_list(self):
        self.assertEqual(self.column(self.people[2]),
            "Cat's Cradle, Slaughterhouse-Five")

    def test_default_sets_text_for_empty_set(self):
        column = related_list(Person, 'bibliography', default="No books")
        self.assertEqual(column(self.people[0]), "No books")

    def test_sep_sets_string_separator(self):
        column = related_list(Person, 'bibliography', sep=" ~ ")
        self.assertEqual(column(self.people[2]),
            "Cat's Cradle ~ Slaughterhouse-Five")

class TestDirectManyToManyRelatedList(TestCase):
    urls = 'adminbrowse.tests'
    fixtures = ['test_adminbrowse.json']

    def setUp(self):
        self.genres = Genre.objects.all()
        self.books = Book.objects.all()
        self.column = related_list(Book, 'categories')

    def test_allow_tags_is_false(self):
        self.assertEqual(self.column.allow_tags, False)

    def test_admin_order_field_is_none(self):
        self.assertEqual(self.column.admin_order_field, None)

    def test_call_returns_comma_separated_list(self):
        self.assertEqual(self.column(self.books[4]), "War, Science Fiction")

class TestIndirectManyToManyRelatedList(TestCase):
    urls = 'adminbrowse.tests'
    fixtures = ['test_adminbrowse.json']

    def setUp(self):
        self.genres = Genre.objects.all()
        self.books = Book.objects.all()
        self.column = related_list(Genre, 'collection')

    def test_allow_tags_is_false(self):
        self.assertEqual(self.column.allow_tags, False)

    def test_admin_order_field_is_none(self):
        self.assertEqual(self.column.admin_order_field, None)

    def test_call_returns_comma_separated_list(self):
        self.assertEqual(self.column(self.genres[1]),
            "The Old Man and the Sea")

class TestURLColumn(TestCase):
    urls = 'adminbrowse.tests'
    fixtures = ['test_adminbrowse.json']

    def setUp(self):
        self.people = Person.objects.all()
        self.column = link_to_url(Person, 'website')

    def test_allow_tags_is_true(self):
        self.assertEqual(self.column.allow_tags, True)

    def test_short_description_defaults_to_verbose_name(self):
        self.assertEqual(self.column.short_description, "home page")

    def test_short_description_sets_short_description(self):
        column = link_to_url(Person, 'website', "homepage URL")
        self.assertEqual(column.short_description, "homepage URL")

    def test_admin_order_field_is_field_name(self):
        self.assertEqual(self.column.admin_order_field, 'website')

    def test_call_returns_link_html(self):
        self.assertEqual(self.column(self.people[0]),
            '<a href="http://example.com/twain" target="_blank"'
            ' class="external" title="Open URL in a new window">'
            'http://example.com/twain</a>')
    
    def test_target_sets_link_target(self):
        column = link_to_url(Person, 'website', target="test")
        self.assertEqual(column(self.people[0]),
            '<a href="http://example.com/twain" target="test"'
            ' class="external" title="Open URL">http://example.com/twain</a>')

    def test_classes_sets_link_class(self):
        column = link_to_url(Person, 'website', classes=['one', 'two'])
        self.assertEqual(column(self.people[0]),
            '<a href="http://example.com/twain" target="_blank"'
            ' class="one two" title="Open URL in a new window">'
            'http://example.com/twain</a>')

    def test_default_sets_html_for_empty_field(self):
        column = link_to_url(Person, 'website', default="No website")
        self.assertEqual(column(self.people[1]), "No website")

    def test_default_defaults_to_empty_string(self):
        self.assertEqual(self.column(self.people[1]), "")

class TestTruncatedTextColumn(TestCase):
    urls = 'adminbrowse.tests'
    fixtures = ['test_adminbrowse.json']

    def setUp(self):
        self.people = Person.objects.all()
        self.column = truncated_field(Person, 'website', 24)

    def test_allow_tags_is_false(self):
        self.assertEqual(self.column.allow_tags, False)

    def test_short_description_defaults_to_verbose_name(self):
        self.assertEqual(self.column.short_description, "home page")

    def test_call_returns_text_truncated_to_max_length(self):
        self.assertEqual(self.column(self.people[2]),
            u"http://example.com/vonne…")
        self.assertEqual(self.column(self.people[0]),
            u"http://example.com/twain")

    def test_max_length_sets_length_before_truncation(self):
        column = truncated_field(Person, 'website', 8)
        self.assertEqual(column(self.people[0]), u"http://e…")

    def test_default_sets_text_for_empty_field(self):
        column = truncated_field(Person, 'website', 80, default="No website")
        self.assertEqual(column(self.people[1]), "No website")
    
    def test_default_defaults_to_empty_string(self):
        self.assertEqual(self.column(self.people[1]), "")

class TestAutoBrowseModelAdmin(TestCase):
    urls = 'adminbrowse.tests'
    fixtures = ['test_adminbrowse.json']

    def setUp(self):
        from django.conf import settings

        class BookAdmin(AutoBrowseModelAdmin):
            list_display = ['title', 'author', 'categories', 'loc_url']

            class Media:
                css = {'all': ['test.css']}

        self.model_admin = BookAdmin(Book, test_site)
        self.media_url = settings.ADMINBROWSE_MEDIA_URL

    def test_has_css_media(self):
        css_media = self.model_admin.media['css']._css['all']
        self.assertTrue(self.media_url + 'css/adminbrowse.css' in css_media)

    def test_does_not_clobber_existing_media(self):
        css_media = self.model_admin.media['css']._css['all']
        self.assertTrue('test.css' in css_media)

    def test_foreign_key_is_replaced_with_link_to_change(self):
        field = self.model_admin.list_display[2]
        self.assertTrue(isinstance(field, link_to_change))
        self.assertEqual(field.model, Book)
        self.assertEqual(field.field_name, 'author')

    def test_url_field_is_replaced_with_link_to_url(self):
        field = self.model_admin.list_display[4]
        self.assertTrue(isinstance(field, link_to_url))
        self.assertEqual(field.model, Book)
        self.assertEqual(field.field_name, 'loc_url')


########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
