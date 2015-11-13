__FILENAME__ = base
# coding: utf-8
from __future__ import absolute_import, unicode_literals
from django.db.models.fields import FieldDoesNotExist
from django.utils.datastructures import SortedDict
from django_tables2.templatetags.django_tables2 import title
from django_tables2.utils import A, AttributeDict, OrderBy, OrderByTuple
from itertools import islice
import six
import warnings


class Library(object):
    """
    A collection of columns.
    """
    def __init__(self):
        self.columns = []

    def register(self, column):
        self.columns.append(column)
        return column

    def column_for_field(self, field):
        """
        Return a column object suitable for model field.

        :returns: column object of `None`
        """
        # iterate in reverse order as columns are registered in order
        # of least to most specialised (i.e. Column is registered
        # first). This also allows user-registered columns to be
        # favoured.
        for candidate in reversed(self.columns):
            if not hasattr(candidate, "from_field"):
                continue
            column = candidate.from_field(field)
            if column is None:
                continue
            return column


# The library is a mechanism for announcing what columns are available. Its
# current use is to allow the table metaclass to ask columns if they're a
# suitable match for a model field, and if so to return an approach instance.
library = Library()


@library.register
class Column(object):  # pylint: disable=R0902
    """
    Represents a single column of a table.

    `.Column` objects control the way a column (including the cells that
    fall within it) are rendered.


    .. attribute:: attrs

        HTML attributes for elements that make up the column.

        :type: `dict`

        This API is extended by subclasses to allow arbitrary HTML attributes
        to be added to the output.

        By default `.Column` supports:

        - *th* -- ``table/thead/th`` elements
        - *td* -- ``table/tbody/tr/td`` elements
        - *cell* -- fallback if *th* or *td* isn't defined


    .. attribute:: accessor

        An accessor that describes how to extract values for this column from
        the :term:`table data`.

        :type: string or `~.Accessor`


    .. attribute:: default

        The default value for the column. This can be a value or a callable
        object [1]_. If an object in the data provides `None` for a column, the
        default will be used instead.

        The default value may affect ordering, depending on the type of data
        the table is using. The only case where ordering is not affected is
        when a `.QuerySet` is used as the table data (since sorting is
        performed by the database).

        .. [1] The provided callable object must not expect to receive any
               arguments.


    .. attribute:: order_by

        Allows one or more accessors to be used for ordering rather than
        *accessor*.

        :type: `unicode`, `tuple`, `~.Accessor`


    .. attribute:: orderable

        If `False`, this column will not be allowed to influence row
        ordering/sorting.

        :type: `bool`


    .. attribute:: verbose_name

        A human readable version of the column name.

        :type: `unicode`


    .. attribute:: visible

        If `True`, this column will be included in the HTML output.

        :type: `bool`


    .. attribute:: localize

        This attribute doesn't work in Django 1.2

        *   If `True`, cells of this column will be localized in the HTML output
            by the localize filter.

        *   If `False`, cells of this column will be unlocalized in the HTML output
            by the unlocalize filter.

        *   If `None` (the default), cell will be rendered as is and localization will depend
            on ``USE_L10N`` setting.

        :type: `bool`
    """
    #: Tracks each time a Column instance is created. Used to retain order.
    creation_counter = 0
    empty_values = (None, '')

    def __init__(self, verbose_name=None, accessor=None, default=None,
                 visible=True, orderable=None, attrs=None, order_by=None,
                 sortable=None, empty_values=None, localize=None):
        if not (accessor is None or isinstance(accessor, six.string_types) or
                callable(accessor)):
            raise TypeError('accessor must be a string or callable, not %s' %
                            type(accessor).__name__)
        if callable(accessor) and default is not None:
            raise TypeError('accessor must be string when default is used, not callable')
        self.accessor = A(accessor) if accessor else None
        self._default = default
        self.verbose_name = verbose_name
        self.visible = visible
        if sortable is not None:
            warnings.warn('`sortable` is deprecated, use `orderable` instead.',
                          DeprecationWarning)
            # if orderable hasn't been specified, we'll use sortable's value
            if orderable is None:
                orderable = sortable
        self.orderable = orderable
        self.attrs = attrs or {}
        # massage order_by into an OrderByTuple or None
        order_by = (order_by, ) if isinstance(order_by, six.string_types) else order_by
        self.order_by = OrderByTuple(order_by) if order_by is not None else None
        if empty_values is not None:
            self.empty_values = empty_values

        self.localize = localize

        self.creation_counter = Column.creation_counter
        Column.creation_counter += 1

    @property
    def default(self):
        # handle callables
        return self._default() if callable(self._default) else self._default

    @property
    def header(self):
        """
        The value used for the column heading (e.g. inside the ``<th>`` tag).

        By default this returns `~.Column.verbose_name`.

        :returns: `unicode` or `None`

        .. note::

            This property typically isn't accessed directly when a table is
            rendered. Instead, `.BoundColumn.header` is accessed which in turn
            accesses this property. This allows the header to fallback to the
            column name (it's only available on a `.BoundColumn` object hence
            accessing that first) when this property doesn't return something
            useful.
        """
        return self.verbose_name

    def render(self, value):
        """
        Returns the content for a specific cell.

        This method can be overridden by :ref:`table.render_FOO` methods on the
        table or by subclassing `.Column`.

        :returns: `unicode`

        If the value for this cell is in `.empty_values`, this method is
        skipped and an appropriate default value is rendered instead.
        Subclasses should set `.empty_values` to ``()`` if they want to handle
        all values in `.render`.
        """
        return value

    @property
    def sortable(self):
        """
        *deprecated* -- use `.orderable` instead.
        """
        warnings.warn('`sortable` is deprecated, use `orderable` instead.',
                      DeprecationWarning)
        return self.orderable

    @classmethod
    def from_field(cls, field):
        """
        Return a specialised column for the model field or `None`.

        :param field: the field that needs a suitable column
        :type  field: model field instance
        :returns: `.Column` object or `None`

        If the column isn't specialised for the given model field, it should
        return `None`. This gives other columns the opportunity to do better.

        If the column is specialised, it should return an instance of itself
        that's configured appropriately for the field.
        """
        # Since this method is inherited by every subclass, only provide a
        # column if this class was asked directly.
        if cls is Column:
            return cls(verbose_name=field.verbose_name)


class BoundColumn(object):
    """
    A *run-time* version of `.Column`. The difference between
    `.BoundColumn` and `.Column`, is that `.BoundColumn` objects include the
    relationship between a `.Column` and a `.Table`. In practice, this
    means that a `.BoundColumn` knows the *"variable name"* given to the
    `.Column` when it was declared on the `.Table`.

    For convenience, all `.Column` properties are available from thisclass.

    :type   table: `.Table` object
    :param  table: the table in which this column exists
    :type  column: `.Column` object
    :param column: the type of column
    :type    name: string object
    :param   name: the variable name of the column used to when defining the
                   `.Table`. In this example the name is ``age``:

                       .. code-block:: python

                           class SimpleTable(tables.Table):
                               age = tables.Column()

    """
    def __init__(self, table, column, name):
        self.table = table
        self.column = column
        self.name = name

    def __unicode__(self):
        return six.text_type(self.header)

    @property
    def accessor(self):
        """
        Returns the string used to access data for this column out of the data
        source.
        """
        return self.column.accessor or A(self.name)

    @property
    def attrs(self):
        """
        Proxy to `.Column.attrs` but injects some values of our own.

        A ``th`` and ``td`` are guaranteed to be defined (irrespective of
        what's actually defined in the column attrs. This makes writing
        templates easier.
        """
        # Work on a copy of the attrs object since we're tweaking stuff
        attrs = dict(self.column.attrs)

        # Find the relevant th attributes (fall back to cell if th isn't
        # explicitly specified).
        attrs["td"] = td = AttributeDict(attrs.get('td', attrs.get('cell', {})))
        attrs["th"] = th = AttributeDict(attrs.get("th", attrs.get("cell", {})))
        # make set of existing classes.
        th_class = set((c for c in th.get("class", "").split(" ") if c))  # pylint: disable=C0103
        td_class = set((c for c in td.get("class", "").split(" ") if c))  # pylint: disable=C0103
        # add classes for ordering
        if self.orderable:
            th_class.add("orderable")
            th_class.add("sortable")  # backwards compatible
        if self.is_ordered:
            th_class.add("desc" if self.order_by_alias.is_descending else "asc")
        # Always add the column name as a class
        th_class.add(self.name)
        td_class.add(self.name)
        if th_class:
            th['class'] = " ".join(sorted(th_class))
        if td_class:
            td['class'] = " ".join(sorted(td_class))
        return attrs

    @property
    def default(self):
        """
        Returns the default value for this column.
        """
        value = self.column.default
        if value is None:
            value = self.table.default
        return value

    @property
    def header(self):
        """
        The value that should be used in the header cell for this column.
        """
        # favour Column.header
        column_header = self.column.header
        if column_header:
            return column_header
        # fall back to automatic best guess
        return self.verbose_name

    @property
    def order_by(self):
        """
        Returns an `.OrderByTuple` of appropriately prefixed data source
        keys used to sort this column.

        See `.order_by_alias` for details.
        """
        if self.column.order_by is not None:
            order_by = self.column.order_by
        else:
            # default to using column accessor as data source sort key
            order_by = OrderByTuple((self.accessor, ))
        return order_by.opposite if self.order_by_alias.is_descending else order_by

    @property
    def order_by_alias(self):
        """
        Returns an `OrderBy` describing the current state of ordering for this
        column.

        The following attempts to explain the difference between `order_by`
        and `.order_by_alias`.

        `.order_by_alias` returns and `.OrderBy` instance that's based on
        the *name* of the column, rather than the keys used to order the table
        data. Understanding the difference is essential.

        Having an alias *and* a keys version is necessary because an N-tuple
        (of data source keys) can be used by the column to order the data, and
        it's ambiguous when mapping from N-tuple to column (since multiple
        columns could use the same N-tuple).

        The solution is to use order by *aliases* (which are really just
        prefixed column names) that describe the ordering *state* of the
        column, rather than the specific keys in the data source should be
        ordered.

        e.g.::

            >>> class SimpleTable(tables.Table):
            ...     name = tables.Column(order_by=("firstname", "last_name"))
            ...
            >>> table = SimpleTable([], order_by=("-name", ))
            >>> table.columns["name"].order_by_alias
            "-name"
            >>> table.columns["name"].order_by
            ("-first_name", "-last_name")

        The `OrderBy` returned has been patched to include an extra attribute
        ``next``, which returns a version of the alias that would be
        transitioned to if the user toggles sorting on this column, e.g.::

            not sorted -> ascending
            ascending  -> descending
            descending -> ascending

        This is useful otherwise in templates you'd need something like:

            {% if column.is_ordered %}
            {% querystring table.prefixed_order_by_field=column.order_by_alias.opposite %}
            {% else %}
            {% querystring table.prefixed_order_by_field=column.order_by_alias %}
            {% endif %}

        """
        order_by = OrderBy((self.table.order_by or {}).get(self.name, self.name))
        order_by.next = order_by.opposite if self.is_ordered else order_by
        return order_by

    @property
    def is_ordered(self):
        return self.name in (self.table.order_by or ())

    @property
    def sortable(self):
        """
        *deprecated* -- use `orderable` instead.
        """
        warnings.warn('`%s.sortable` is deprecated, use `orderable`'
                      % type(self).__name__, DeprecationWarning)
        return self.orderable

    @property
    def orderable(self):
        """
        Return a `bool` depending on whether this column supports ordering.
        """
        if self.column.orderable is not None:
            return self.column.orderable
        return self.table.orderable

    @property
    def verbose_name(self):
        """
        Return the verbose name for this column, or fallback to the titlised
        column name.

        If the table is using queryset data, then use the corresponding model
        field's `~.db.Field.verbose_name`. If it's traversing a relationship,
        then get the last field in the accessor (i.e. stop when the
        relationship turns from ORM relationships to object attributes [e.g.
        person.upper should stop at person]).
        """
        # Favor an explicit defined verbose_name
        if self.column.verbose_name:
            return self.column.verbose_name

        # This is our reasonable fallback, should the next section not result
        # in anything useful.
        name = title(self.name.replace('_', ' '))

        # Try to use a tmodel field's verbose_name
        if hasattr(self.table.data, 'queryset'):
            model = self.table.data.queryset.model
            parts = self.accessor.split('.')
            field = None
            for part in parts:
                try:
                    field = model._meta.get_field(part)
                except FieldDoesNotExist:
                    break
                if hasattr(field, 'rel') and hasattr(field.rel, 'to'):
                    model = field.rel.to
                    continue
                break
            if field:
                name = field.verbose_name
        return name

    @property
    def visible(self):
        """
        Returns a `bool` depending on whether this column is visible.
        """
        return self.column.visible

    @property
    def localize(self):
        '''
        Returns `True`, `False` or `None` as described in ``Column.localize``
        '''
        return self.column.localize


class BoundColumns(object):
    """
    Container for spawning `.BoundColumn` objects.

    This is bound to a table and provides its `.Table.columns` property.
    It provides access to those columns in different ways (iterator,
    item-based, filtered and unfiltered etc), stuff that would not be possible
    with a simple iterator in the table class.

    A `BoundColumns` object is a container for holding `BoundColumn` objects.
    It provides methods that make accessing columns easier than if they were
    stored in a `list` or `dict`. `Columns` has a similar API to a `dict` (it
    actually uses a `~django.utils.datastructures.SortedDict` interally).

    At the moment you'll only come across this class when you access a
    `.Table.columns` property.

    :type  table: `.Table` object
    :param table: the table containing the columns
    """
    def __init__(self, table):
        self.table = table
        self.columns = SortedDict()
        for name, column in six.iteritems(table.base_columns):
            self.columns[name] = bc = BoundColumn(table, column, name)
            bc.render = getattr(table, 'render_' + name, column.render)

    def iternames(self):
        return (name for name, column in self.iteritems())

    def names(self):
        return list(self.iternames())

    def iterall(self):
        """
        Return an iterator that exposes all `.BoundColumn` objects,
        regardless of visiblity or sortability.
        """
        return (column for name, column in self.iteritems())

    def all(self):
        return list(self.iterall())

    def iteritems(self):
        """
        Return an iterator of ``(name, column)`` pairs (where ``column`` is a
        `BoundColumn`).

        This method is the mechanism for retrieving columns that takes into
        consideration all of the ordering and filtering modifiers that a table
        supports (e.g. `~Table.Meta.exclude` and `~Table.Meta.sequence`).
        """
        for name in self.table.sequence:
            if name not in self.table.exclude:
                yield (name, self.columns[name])

    def items(self):
        return list(self.iteritems())

    def iterorderable(self):
        """
        Same as `BoundColumns.all` but only returns orderable columns.

        This is useful in templates, where iterating over the full
        set and checking ``{% if column.sortable %}`` can be problematic in
        conjunction with e.g. ``{{ forloop.last }}`` (the last column might not
        be the actual last that is rendered).
        """
        return (x for x in self.iterall() if x.orderable)

    def itersortable(self):
        warnings.warn('`itersortable` is deprecated, use `iterorderable` instead.',
                      DeprecationWarning)
        return self.iterorderable()

    def orderable(self):
        return list(self.iterorderable())

    def sortable(self):
        warnings.warn("`sortable` is deprecated, use `orderable` instead.",
                      DeprecationWarning)
        return self.orderable

    def itervisible(self):
        """
        Same as `.iterorderable` but only returns visible `.BoundColumn`
        objects.

        This is geared towards table rendering.
        """
        return (x for x in self.iterall() if x.visible)

    def visible(self):
        return list(self.itervisible())

    def __iter__(self):
        """
        Convenience API, alias of `.itervisible`.
        """
        return self.itervisible()

    def __contains__(self, item):
        """
        Check if a column is contained within a `Columns` object.

        *item* can either be a `BoundColumn` object, or the name of a column.
        """
        if isinstance(item, six.string_types):
            return item in self.iternames()
        else:
            # let's assume we were given a column
            return item in self.iterall()

    def __len__(self):
        """
        Return how many :class:`BoundColumn` objects are contained (and
        visible).
        """
        return len(self.visible())

    def __getitem__(self, index):
        """
        Retrieve a specific `BoundColumn` object.

        *index* can either be 0-indexed or the name of a column

        .. code-block:: python

            columns['speed']  # returns a bound column with name 'speed'
            columns[0]        # returns the first column
        """
        if isinstance(index, int):
            try:
                return next(islice(self.iterall(), index, index + 1))
            except StopIteration:
                raise IndexError
        elif isinstance(index, six.string_types):
            for column in self.iterall():
                if column.name == index:
                    return column
            raise KeyError("Column with name '%s' does not exist; "
                           "choices are: %s" % (index, self.names()))
        else:
            raise TypeError('row indices must be integers or str, not %s'
                            % type(index).__name__)

########NEW FILE########
__FILENAME__ = booleancolumn
# coding: utf-8
from __future__ import absolute_import, unicode_literals
from .base import Column, library
from django.db import models
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django_tables2.utils import AttributeDict
import six


@library.register
class BooleanColumn(Column):
    """
    A column suitable for rendering boolean data.

    :param  null: is `None` different from `False`?
    :type   null: `bool`
    :param yesno: text to display for True/False values, comma separated
    :type  yesno: iterable or string

    Rendered values are wrapped in a ``<span>`` to allow customisation by
    themes. By default the span is given the class ``true``, ``false``.

    In addition to *attrs* keys supported by `.Column`, the following are
    available:

    - *span* -- adds attributes to the <span> tag
    """
    def __init__(self, null=False, yesno="✔,✘", **kwargs):
        self.yesno = (yesno.split(',') if isinstance(yesno, six.string_types)
                      else tuple(yesno))
        if null:
            kwargs["empty_values"] = ()
        super(BooleanColumn, self).__init__(**kwargs)

    def render(self, value):
        value = bool(value)
        text = self.yesno[int(not value)]
        html = '<span %s>%s</span>'
        attrs = {"class": six.text_type(value).lower()}
        attrs.update(self.attrs.get("span", {}))
        return mark_safe(html % (AttributeDict(attrs).as_html(), escape(text)))

    @classmethod
    def from_field(cls, field):
        if isinstance(field, models.BooleanField):
            return cls(verbose_name=field.verbose_name, null=False)
        if isinstance(field, models.NullBooleanField):
            return cls(verbose_name=field.verbose_name, null=True)

########NEW FILE########
__FILENAME__ = checkboxcolumn
# coding: utf-8
from __future__ import absolute_import, unicode_literals
from django.utils.safestring import mark_safe
from django_tables2.utils import AttributeDict
import warnings
from .base import Column, library


@library.register
class CheckBoxColumn(Column):
    """
    A subclass of `.Column` that renders as a checkbox form input.

    This column allows a user to *select* a set of rows. The selection
    information can then be used to apply some operation (e.g. "delete") onto
    the set of objects that correspond to the selected rows.

    The value that is extracted from the :term:`table data` for this column is
    used as the value for the checkbox, i.e. ``<input type="checkbox"
    value="..." />``

    This class implements some sensible defaults:

    - HTML input's ``name`` attribute is the :term:`column name` (can override
      via *attrs* argument).
    - *orderable* defaults to `False`.

    .. note::

        You'd expect that you could select multiple checkboxes in the rendered
        table and then *do something* with that. This functionality isn't
        implemented. If you want something to actually happen, you'll need to
        implement that yourself.

    In addition to *attrs* keys supported by `.Column`, the following are
    available:

    - *input*     -- ``<input>`` elements in both ``<td>`` and ``<th>``.
    - *th__input* -- Replaces *input* attrs in header cells.
    - *td__input* -- Replaces *input* attrs in body cells.
    """
    def __init__(self, attrs=None, **extra):
        # For backwards compatibility, passing in a normal dict effectively
        # should assign attributes to the `<input>` tag.
        valid = set(("input", "th__input", "td__input", "th", "td", "cell"))
        if attrs and not set(attrs) & set(valid):
            # if none of the keys in attrs are actually valid, assume it's some
            # old code that should be be interpreted as {"td__input": ...}
            warnings.warn('attrs keys must be one of %s, interpreting as {"td__input": %s}'
                          % (', '.join(valid), attrs), DeprecationWarning)
            attrs = {"td__input": attrs}
        # This is done for backwards compatible too, there used to be a
        # ``header_attrs`` argument, but this has been deprecated. We'll
        # maintain it for a while by translating it into ``head.checkbox``.
        if "header_attrs" in extra:
            warnings.warn('header_attrs argument is deprecated, '
                          'use attrs={"th__input": ...} instead',
                          DeprecationWarning)
            attrs.setdefault('th__input', {}).update(extra.pop('header_attrs'))

        kwargs = {'orderable': False, 'attrs': attrs}
        kwargs.update(extra)
        super(CheckBoxColumn, self).__init__(**kwargs)

    @property
    def header(self):
        default = {'type': 'checkbox'}
        general = self.attrs.get('input')
        specific = self.attrs.get('th__input')
        attrs = AttributeDict(default, **(specific or general or {}))
        return mark_safe('<input %s/>' % attrs.as_html())

    def render(self, value, bound_column):  # pylint: disable=W0221
        default = {
            'type': 'checkbox',
            'name': bound_column.name,
            'value': value
        }
        general = self.attrs.get('input')
        specific = self.attrs.get('td__input')
        attrs = AttributeDict(default, **(specific or general or {}))
        return mark_safe('<input %s/>' % attrs.as_html())

########NEW FILE########
__FILENAME__ = datecolumn
# coding: utf-8
from __future__ import absolute_import, unicode_literals
from django.db import models
from .base import library
from .templatecolumn import TemplateColumn


@library.register
class DateColumn(TemplateColumn):
    """
    A column that renders dates in the local timezone.

    :param format: format string in same format as Django's ``date`` template
                   filter (optional)
    :type  format: `unicode`
    :param  short: if *format* is not specified, use Django's
                   ``SHORT_DATE_FORMAT`` setting, otherwise use ``DATE_FORMAT``
    :type   short: `bool`
    """
    def __init__(self, format=None, short=True, *args, **kwargs):  # pylint: disable=W0622
        if format is None:
            format = 'SHORT_DATE_FORMAT' if short else 'DATE_FORMAT'
        template = '{{ value|date:"%s"|default:default }}' % format
        super(DateColumn, self).__init__(template_code=template, *args, **kwargs)

    @classmethod
    def from_field(cls, field):
        if isinstance(field, models.DateField):
            return cls(verbose_name=field.verbose_name)

########NEW FILE########
__FILENAME__ = datetimecolumn
# coding: utf-8
from __future__ import absolute_import, unicode_literals
from django.db import models
from .base import library
from .templatecolumn import TemplateColumn


@library.register
class DateTimeColumn(TemplateColumn):
    """
    A column that renders datetimes in the local timezone.

    :param format: format string for datetime (optional)
    :type  format: `unicode`
    :param  short: if *format* is not specifid, use Django's
                   ``SHORT_DATETIME_FORMAT``, else ``DATETIME_FORMAT``
    :type   short: `bool`
    """
    def __init__(self, format=None, short=True, *args, **kwargs):  # pylint: disable=W0622
        if format is None:
            format = 'SHORT_DATETIME_FORMAT' if short else 'DATETIME_FORMAT'
        template = '{{ value|date:"%s"|default:default }}' % format
        super(DateTimeColumn, self).__init__(template_code=template, *args, **kwargs)

    @classmethod
    def from_field(cls, field):
        if isinstance(field, models.DateTimeField):
            return cls(verbose_name=field.verbose_name)

########NEW FILE########
__FILENAME__ = emailcolumn
# coding: utf-8
from __future__ import absolute_import, unicode_literals
from django.db import models
from .base import library
from .linkcolumn import BaseLinkColumn


@library.register
class EmailColumn(BaseLinkColumn):
    """
    A subclass of `.BaseLinkColumn` that renders the cell value as a hyperlink.

    It's common to have a email value in a row hyperlinked to other page.

    :param  attrs: a `dict` of HTML attributes that are added to
                   the rendered ``<a href="...">...</a>`` tag

    Example:

    .. code-block:: python

        # models.py
        class Person(models.Model):
            name = models.CharField(max_length=200)
            email =  models.EmailField()

        # tables.py
        class PeopleTable(tables.Table):
            name = tables.Column()
            email = tables.EmailColumn()

    """
    def render(self, value):
        return self.render_link("mailto:%s" % value, text=value)

    @classmethod
    def from_field(cls, field):
        if isinstance(field, models.EmailField):
            return cls(verbose_name=field.verbose_name)

########NEW FILE########
__FILENAME__ = filecolumn
# coding: utf-8
from __future__ import absolute_import, unicode_literals
from django.db import models
from django.utils.safestring import mark_safe
from django_tables2.utils import AttributeDict
import os
from .base import Column, library


@library.register
class FileColumn(Column):
    """
    Attempts to render `.FieldFile` (or other storage backend `.File`) as a
    hyperlink.

    When the file is accessible via a URL, the file is rendered as a
    hyperlink. The `.basename` is used as the text::

        <a href="/media/path/to/receipt.pdf" title="path/to/receipt.pdf">receipt.pdf</a>

    When unable to determine the URL, a ``span`` is used instead::

        <span title="path/to/receipt.pdf">receipt.pdf</span>

    `.Column.attrs` keys ``a`` and ``span`` can be used to add additional attributes.

    :type  verify_exists: bool
    :param verify_exists: attempt to determine if the file exists

    If *verify_exists*, the HTML class ``exists`` or ``missing`` is added to
    the element to indicate the integrity of the storage.
    """
    def __init__(self, verify_exists=True, **kwargs):
        self.verify_exists = True
        super(FileColumn, self).__init__(**kwargs)

    def render(self, value):
        storage = getattr(value, "storage", None)
        exists = None
        url = None
        if storage:
            # we'll assume value is a `django.db.models.fields.files.FieldFile`
            if self.verify_exists:
                exists = storage.exists(value.name)
            url = storage.url(value.name)

        else:
            if self.verify_exists and hasattr(value, "name"):
                # ignore negatives, perhaps the file has a name but it doesn't
                # represent a local path... better to stay neutral than give a
                # false negative.
                exists = os.path.exists(value.name) or exists

        tag = 'a' if url else 'span'
        attrs = AttributeDict(self.attrs.get(tag, {}))
        attrs['title'] = value.name
        if url:
            attrs['href'] = url

        # add "exists" or "missing" to the class list
        classes = [c for c in attrs.get('class', '').split(' ') if c]
        if exists is True:
            classes.append("exists")
        elif exists is False:
            classes.append("missing")
        attrs['class'] = " ".join(classes)

        html = '<{tag} {attrs}>{text}</{tag}>'.format(
            tag=tag,
            attrs=attrs.as_html(),
            text=os.path.basename(value.name))
        return mark_safe(html)

    @classmethod
    def from_field(cls, field):
        if isinstance(field, models.FileField):
            return cls(verbose_name=field.verbose_name)

########NEW FILE########
__FILENAME__ = linkcolumn
# coding: utf-8
from __future__ import absolute_import, unicode_literals
from django.core.urlresolvers import reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe
import warnings
from .base import Column, library
from django_tables2.utils import A, AttributeDict


class BaseLinkColumn(Column):
    """
    The base for other columns that render links.

    Adds support for an ``a`` key in *attrs** which is added to the rendered
    ``<a href="...">`` tag.
    """
    def __init__(self, attrs=None, *args, **kwargs):
        valid = set(("a", "th", "td", "cell"))
        if attrs and not set(attrs) & set(valid):
            # if none of the keys in attrs are actually valid, assume it's some
            # old code that should be be interpreted as {"a": ...}
            warnings.warn('attrs keys must be one of %s, interpreting as {"a": %s}'
                          % (', '.join(valid), attrs), DeprecationWarning)
            attrs = {"a": attrs}
        kwargs['attrs'] = attrs
        super(BaseLinkColumn, self).__init__(*args, **kwargs)

    def render_link(self, uri, text, attrs=None):
        """
        Render a hyperlink.

        :param   uri: URI for the hyperlink
        :param  text: value wrapped in ``<a></a>``
        :param attrs: ``<a>`` tag attributes
        """
        attrs = AttributeDict(attrs if attrs is not None else
                              self.attrs.get('a', {}))
        attrs['href'] = uri
        html = '<a {attrs}>{text}</a>'.format(
            attrs=attrs.as_html(),
            text=escape(text)
        )
        return mark_safe(html)


@library.register
class LinkColumn(BaseLinkColumn):
    """
    Renders a normal value as an internal hyperlink to another page.

    It's common to have the primary value in a row hyperlinked to the page
    dedicated to that record.

    The first arguments are identical to that of
    `~django.core.urlresolvers.reverse` and allows an internal URL to be
    described. The last argument *attrs* allows custom HTML attributes to
    be added to the rendered ``<a href="...">`` tag.

    :param    viewname: See `~django.core.urlresolvers.reverse`.
    :param     urlconf: See `~django.core.urlresolvers.reverse`.
    :param        args: See `~django.core.urlresolvers.reverse`. **
    :param      kwargs: See `~django.core.urlresolvers.reverse`. **
    :param current_app: See `~django.core.urlresolvers.reverse`.
    :param       attrs: a `dict` of HTML attributes that are added to
                        the rendered ``<input type="checkbox" .../>`` tag

    ** In order to create a link to a URL that relies on information in the
    current row, `.Accessor` objects can be used in the *args* or
    *kwargs* arguments. The accessor will be resolved using the row's record
    before `~django.core.urlresolvers.reverse` is called.

    Example:

    .. code-block:: python

        # models.py
        class Person(models.Model):
            name = models.CharField(max_length=200)

        # urls.py
        urlpatterns = patterns('',
            url('people/(\d+)/', views.people_detail, name='people_detail')
        )

        # tables.py
        from django_tables2.utils import A  # alias for Accessor

        class PeopleTable(tables.Table):
            name = tables.LinkColumn('people_detail', args=[A('pk')])

    In addition to *attrs* keys supported by `.Column`, the following are
    available:

    - *a* -- ``<a>`` elements in ``<td>``.
    """
    def __init__(self, viewname, urlconf=None, args=None, kwargs=None,
                 current_app=None, attrs=None, **extra):
        super(LinkColumn, self).__init__(attrs, **extra)
        self.viewname = viewname
        self.urlconf = urlconf
        self.args = args
        self.kwargs = kwargs
        self.current_app = current_app

    def render(self, value, record, bound_column):  # pylint: disable=W0221
        viewname = (self.viewname.resolve(record)
                    if isinstance(self.viewname, A)
                    else self.viewname)

        # The following params + if statements create optional arguments to
        # pass to Django's reverse() function.
        params = {}
        if self.urlconf:
            params['urlconf'] = (self.urlconf.resolve(record)
                                 if isinstance(self.urlconf, A)
                                 else self.urlconf)
        if self.args:
            params['args'] = [a.resolve(record) if isinstance(a, A) else a
                              for a in self.args]
        if self.kwargs:
            params['kwargs'] = {}
            for key, val in self.kwargs.items():
                # If we're dealing with an Accessor (A), resolve it, otherwise
                # use the value verbatim.
                params['kwargs'][str(key)] = (val.resolve(record)
                                              if isinstance(val, A) else val)
        if self.current_app:
            params['current_app'] = (self.current_app.resolve(record)
                                     if isinstance(self.current_app, A)
                                     else self.current_app)
        return self.render_link(reverse(viewname, **params), text=value)

########NEW FILE########
__FILENAME__ = templatecolumn
# coding: utf-8
from __future__ import absolute_import, unicode_literals
from django.template import Context, Template
from django.template.loader import render_to_string
from .base import Column, library


@library.register
class TemplateColumn(Column):
    """
    A subclass of `.Column` that renders some template code to use as
    the cell value.

    :type  template_code: `unicode`
    :param template_code: the template code to render
    :type  template_name: `unicode`
    :param template_name: the name of the template to render

    A `~django.template.Template` object is created from the
    *template_code* or *template_name* and rendered with a context containing:

    - *record* -- data record for the current row
    - *value* -- value from `record` that corresponds to the current column
    - *default* -- appropriate default value to use as fallback

    Example:

    .. code-block:: python

        class ExampleTable(tables.Table):
            foo = tables.TemplateColumn('{{ record.bar }}')
            # contents of `myapp/bar_column.html` is `{{ value }}`
            bar = tables.TemplateColumn(template_name='myapp/name2_column.html')

    Both columns will have the same output.

    .. important::

        In order to use template tags or filters that require a
        `~django.template.RequestContext`, the table **must** be rendered via
        :ref:`{% render_table %} <template-tags.render_table>`.
    """
    empty_values = ()

    def __init__(self, template_code=None, template_name=None, **extra):
        super(TemplateColumn, self).__init__(**extra)
        self.template_code = template_code
        self.template_name = template_name
        if not self.template_code and not self.template_name:
            raise ValueError('A template must be provided')

    def render(self, record, table, value, bound_column, **kwargs):
        # If the table is being rendered using `render_table`, it hackily
        # attaches the context to the table as a gift to `TemplateColumn`. If
        # the table is being rendered via `Table.as_html`, this won't exist.
        context = getattr(table, 'context', Context())
        context.update({'default': bound_column.default,
                        'record': record, 'value': value})
        try:
            if self.template_code:
                return Template(self.template_code).render(context)
            else:
                return render_to_string(self.template_name, context)
        finally:
            context.pop()

########NEW FILE########
__FILENAME__ = timecolumn
# coding: utf-8
from __future__ import absolute_import, unicode_literals
from django.db import models
from .base import library
from .templatecolumn import TemplateColumn
from django.conf import settings

@library.register
class TimeColumn(TemplateColumn):
    """
    A column that renders times in the local timezone.

    :param format: format string in same format as Django's ``time`` template
                   filter (optional)
    :type  format: `unicode`
    :param  short: if *format* is not specified, use Django's ``TIME_FORMAT`` setting
    """
    def __init__(self, format=None, *args, **kwargs):
        if format is None:
            format = settings.TIME_FORMAT
        template = '{{ value|date:"%s"|default:default }}' % format
        super(TimeColumn, self).__init__(template_code=template, *args, **kwargs)

    @classmethod
    def from_field(cls, field):
        if isinstance(field, models.TimeField):
            return cls(verbose_name=field.verbose_name)

########NEW FILE########
__FILENAME__ = urlcolumn
# coding: utf-8
from __future__ import absolute_import, unicode_literals
from django.db import models
from .base import library
from .linkcolumn import BaseLinkColumn


@library.register
class URLColumn(BaseLinkColumn):
    """
    Renders URL values as hyperlinks.

    Example::

        >>> class CompaniesTable(tables.Table):
        ...     www = tables.URLColumn()
        ...
        >>> table = CompaniesTable([{"www": "http://google.com"}])
        >>> table.rows[0]["www"]
        u'<a href="http://google.com">http://google.com</a>'

    Additional attributes for the ``<a>`` tag can be specified via
    ``attrs['a']``.

    """
    def render(self, value):
        return self.render_link(value, value)

    @classmethod
    def from_field(cls, field):
        if isinstance(field, models.URLField):
            return cls(verbose_name=field.verbose_name)

########NEW FILE########
__FILENAME__ = config
# coding: utf-8
from __future__ import unicode_literals
from django.core.paginator import EmptyPage, PageNotAnInteger


class RequestConfig(object):
    """
    A configurator that uses request data to setup a table.

    :type  paginate: `dict` or `bool`
    :param paginate: indicates whether to paginate, and if so, what default
                     values to use. If the value evaluates to `False`,
                     pagination will be disabled. A `dict` can be used to
                     specify default values for the call to
                     `~.tables.Table.paginate` (e.g. to define a default
                     *per_page* value).

                     A special *silent* item can be used to enable automatic
                     handling of pagination exceptions using the following
                     algorithm:

                     - If `~django.core.paginator.PageNotAnInteger`` is raised,
                       show the first page.
                     - If `~django.core.paginator.EmptyPage` is raised, show
                       the last page.

    """
    def __init__(self, request, paginate=True):
        self.request = request
        self.paginate = paginate

    def configure(self, table):
        """
        Configure a table using information from the request.
        """
        order_by = self.request.GET.getlist(table.prefixed_order_by_field)
        if order_by:
            table.order_by = order_by
        if self.paginate:
            if hasattr(self.paginate, "items"):
                kwargs = dict(self.paginate)
            else:
                kwargs = {}
            # extract some options from the request
            for arg in ("page", "per_page"):
                name = getattr(table, "prefixed_%s_field" % arg)
                try:
                    kwargs[arg] = int(self.request.GET[name])
                except (ValueError, KeyError):
                    pass

            silent = kwargs.pop('silent', True)
            if not silent:
                table.paginate(**kwargs)
            else:
                try:
                    table.paginate(**kwargs)
                except PageNotAnInteger:
                    table.page = table.paginator.page(1)
                except EmptyPage:
                    table.page = table.paginator.page(table.paginator.num_pages)

########NEW FILE########
__FILENAME__ = models
# coding: utf-8
"""Needed to make this package a Django app"""

########NEW FILE########
__FILENAME__ = rows
# coding: utf-8
from .utils import A, getargspec
from django.db import models
from django.db.models.fields import FieldDoesNotExist
import six


class BoundRow(object):
    """
    Represents a *specific* row in a table.

    `.BoundRow` objects are a container that make it easy to access the
    final 'rendered' values for cells in a row. You can simply iterate over a
    `.BoundRow` object and it will take care to return values rendered
    using the correct method (e.g. :ref:`table.render_FOO`)

    To access the rendered value of each cell in a row, just iterate over it:

    .. code-block:: python

        >>> import django_tables2 as tables
        >>> class SimpleTable(tables.Table):
        ...     a = tables.Column()
        ...     b = tables.CheckBoxColumn(attrs={'name': 'my_chkbox'})
        ...
        >>> table = SimpleTable([{'a': 1, 'b': 2}])
        >>> row = table.rows[0]  # we only have one row, so let's use it
        >>> for cell in row:
        ...     print cell
        ...
        1
        <input type="checkbox" name="my_chkbox" value="2" />

    Alternatively you can treat it like a list and use indexing to retrieve a
    specific cell. It should be noted that this will raise an IndexError on
    failure.

    .. code-block:: python

        >>> row[0]
        1
        >>> row[1]
        u'<input type="checkbox" name="my_chkbox" value="2" />'
        >>> row[2]
        ...
        IndexError: list index out of range

    Finally you can also treat it like a dictionary and use column names as the
    keys. This will raise KeyError on failure (unlike the above indexing using
    integers).

    .. code-block:: python

        >>> row['a']
        1
        >>> row['b']
        u'<input type="checkbox" name="my_chkbox" value="2" />'
        >>> row['c']
        ...
        KeyError: 'c'

    :param  table: is the `.Table` in which this row exists.
    :param record: a single record from the :term:`table data` that is used to
                   populate the row. A record could be a `~django.db.Model`
                   object, a `dict`, or something else.

    """
    def __init__(self, record, table):
        self._record = record
        self._table = table

    @property
    def table(self):
        """The associated `.Table` object."""
        return self._table

    @property
    def record(self):
        """
        The data record from the data source which is used to populate this row
        with data.
        """
        return self._record

    def __iter__(self):
        """
        Iterate over the rendered values for cells in the row.

        Under the hood this method just makes a call to
        `.BoundRow.__getitem__` for each cell.
        """
        for column, value in self.items():
            # this uses __getitem__, using the name (rather than the accessor)
            # is correct – it's what __getitem__ expects.
            yield value

    def __getitem__(self, name):
        """
        Returns the final rendered value for a cell in the row, given the name
        of a column.
        """
        bound_column = self.table.columns[name]

        value = None
        # We need to take special care here to allow get_FOO_display()
        # methods on a model to be used if available. See issue #30.
        path, _, remainder = bound_column.accessor.rpartition('.')
        penultimate = A(path).resolve(self.record, quiet=True)
        # If the penultimate is a model and the remainder is a field
        # using choices, use get_FOO_display().
        if isinstance(penultimate, models.Model):
            try:
                field = penultimate._meta.get_field(remainder)
                display = getattr(penultimate, 'get_%s_display' % remainder, None)
                if field.choices and display:
                    value = display()
                    remainder = None
            except FieldDoesNotExist:
                pass
        # Fall back to just using the original accessor (we just need
        # to follow the remainder).
        if remainder:
            value = A(remainder).resolve(penultimate, quiet=True)

        if value in bound_column.column.empty_values:
            return bound_column.default

        available = {
            'value':        value,
            'record':       self.record,
            'column':       bound_column.column,
            'bound_column': bound_column,
            'bound_row':    self,
            'table':        self._table,
        }
        expected = {}

        # provide only the arguments expected by `render`
        argspec = getargspec(bound_column.render)
        args, varkw = argspec[0], argspec[2]
        if varkw:
            expected = available
        else:
            for key, value in available.items():
                if key in args[1:]:
                    expected[key] = value

        return bound_column.render(**expected)

    def __contains__(self, item):
        """Check by both row object and column name."""
        if isinstance(item, six.string_types):
            return item in self.table._columns
        else:
            return item in self

    def items(self):
        """
        Returns iterator yielding ``(bound_column, cell)`` pairs.

        *cell* is ``row[name]`` -- the rendered unicode value that should be
        ``rendered within ``<td>``.
        """
        for column in self.table.columns:
            yield (column, self[column.name])


class BoundRows(object):
    """
    Container for spawning `.BoundRow` objects.

    :param  data: iterable of records
    :param table: the table in which the rows exist

    This is used for `.Table.rows`.
    """
    def __init__(self, data, table):
        self.data = data
        self.table = table

    def __iter__(self):
        for record in self.data:
            yield BoundRow(record, table=self.table)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, key):
        """
        Slicing returns a new `.BoundRows` instance, indexing returns a single
        `.BoundRow` instance.
        """
        container = BoundRows if isinstance(key, slice) else BoundRow
        return container(self.data[key], table=self.table)

########NEW FILE########
__FILENAME__ = tables
# coding: utf-8
from __future__ import unicode_literals
from . import columns
from .config import RequestConfig
from .rows import BoundRows
from .utils import (Accessor, AttributeDict, build_request, cached_property,
                    computed_values, OrderBy, OrderByTuple, segment, Sequence)
import copy
import sys
from django.core.paginator       import Paginator
from django.db.models.fields     import FieldDoesNotExist
from django.utils.datastructures import SortedDict
from django.template             import RequestContext
from django.template.loader      import get_template
import six
import warnings


QUERYSET_ACCESSOR_SEPARATOR = '__'


class TableData(object):
    """
    Exposes a consistent API for :term:`table data`.

    :param  data: iterable containing data for each row
    :type   data: `~django.db.query.QuerySet` or `list` of `dict`
    :param table: `.Table` object
    """
    def __init__(self, data, table):
        self.table = table
        # data may be a QuerySet-like objects with count() and order_by()
        if (hasattr(data, 'count') and callable(data.count) and
            hasattr(data, 'order_by') and callable(data.order_by)):
            self.queryset = data
        # otherwise it must be convertable to a list
        else:
            # do some light validation
            if hasattr(data, '__iter__') or (hasattr(data, '__len__') and hasattr(data, '__getitem__')):
                self.list = list(data)
            else:
                raise ValueError(
                    'data must be QuerySet-like (have count and '
                    'order_by) or support list(data) -- %s has '
                    'neither' % type(data).__name__
                )

    def __len__(self):
        if not hasattr(self, "_length"):
            # Use the queryset count() method to get the length, instead of
            # loading all results into memory. This allows, for example,
            # smart paginators that use len() to perform better.
            self._length = (self.queryset.count() if hasattr(self, 'queryset')
                                                  else len(self.list))
        return self._length

    @property
    def data(self):
        return self.queryset if hasattr(self, "queryset") else self.list

    @property
    def ordering(self):
        """
        Returns the list of order by aliases that are enforcing ordering on the
        data.

        If the data is unordered, an empty sequence is returned. If the
        ordering can not be determined, `None` is returned.

        This works by inspecting the actual underlying data. As such it's only
        supported for querysets.
        """
        if hasattr(self, "queryset"):
            aliases = {}
            for bound_column in self.table.columns:
                aliases[bound_column.order_by_alias] = bound_column.order_by
            try:
                return next(segment(self.queryset.query.order_by, aliases))
            except StopIteration:
                pass

    def order_by(self, aliases):
        """
        Order the data based on order by aliases (prefixed column names) in the
        table.

        :param aliases: optionally prefixed names of columns ('-' indicates
                        descending order) in order of significance with
                        regard to data ordering.
        :type  aliases: `~.utils.OrderByTuple`
        """
        accessors = []
        for alias in aliases:
            bound_column = self.table.columns[OrderBy(alias).bare]
            # bound_column.order_by reflects the current ordering applied to
            # the table. As such we need to check the current ordering on the
            # column and use the opposite if it doesn't match the alias prefix.
            if alias[0] != bound_column.order_by_alias[0]:
                accessors += bound_column.order_by.opposite
            else:
                accessors += bound_column.order_by
        if hasattr(self, "queryset"):
            translate = lambda accessor: accessor.replace(Accessor.SEPARATOR, QUERYSET_ACCESSOR_SEPARATOR)
            self.queryset = self.queryset.order_by(*(translate(a) for a in accessors))
        else:
            self.list.sort(key=OrderByTuple(accessors).key)

    def __iter__(self):
        """
        for ... in ... default to using this. There's a bug in Django 1.3
        with indexing into querysets, so this side-steps that problem (as well
        as just being a better way to iterate).
        """
        return iter(self.data)

    def __getitem__(self, key):
        """
        Slicing returns a new `.TableData` instance, indexing returns a
        single record.
        """
        return self.data[key]

    @cached_property
    def verbose_name(self):
        """
        The full (singular) name for the data.

        Queryset data has its model's `~django.db.Model.Meta.verbose_name`
        honored. List data is checked for a ``verbose_name`` attribute, and
        falls back to using ``"item"``.
        """
        if hasattr(self, "queryset"):
            return self.queryset.model._meta.verbose_name
        return getattr(self.list, "verbose_name", "item")

    @cached_property
    def verbose_name_plural(self):
        """
        The full (plural) name of the data.

        This uses the same approach as `.verbose_name`.
        """
        if hasattr(self, "queryset"):
            return self.queryset.model._meta.verbose_name_plural
        return getattr(self.list, "verbose_name_plural", "items")


class DeclarativeColumnsMetaclass(type):
    """
    Metaclass that converts `.Column` objects defined on a class to the
    dictionary `.Table.base_columns`, taking into account parent class
    ``base_columns`` as well.
    """
    def __new__(mcs, name, bases, attrs):
        attrs["_meta"] = opts = TableOptions(attrs.get("Meta", None))
        # extract declared columns
        cols, remainder = [], {}
        for attr_name, attr in attrs.items():
            if isinstance(attr, columns.Column):
                cols.append((attr_name, attr))
            else:
                remainder[attr_name] = attr
        attrs = remainder

        cols.sort(key=lambda x: x[1].creation_counter)

        # If this class is subclassing other tables, add their fields as
        # well. Note that we loop over the bases in *reverse* - this is
        # necessary to preserve the correct order of columns.
        parent_columns = []
        for base in bases[::-1]:
            if hasattr(base, "base_columns"):
                parent_columns = list(base.base_columns.items()) + parent_columns
        # Start with the parent columns
        attrs["base_columns"] = SortedDict(parent_columns)
        # Possibly add some generated columns based on a model
        if opts.model:
            extra = SortedDict()
            # honor Table.Meta.fields, fallback to model._meta.fields
            if opts.fields:
                # Each item in opts.fields is the name of a model field or a
                # normal attribute on the model
                for field_name in opts.fields:
                    try:
                        field = opts.model._meta.get_field(field_name)
                    except FieldDoesNotExist:
                        extra[field_name] = columns.Column()
                    else:
                        extra[field_name] = columns.library.column_for_field(field)

            else:
                for field in opts.model._meta.fields:
                    extra[field.name] = columns.library.column_for_field(field)
            attrs["base_columns"].update(extra)

        # Explicit columns override both parent and generated columns
        attrs["base_columns"].update(SortedDict(cols))
        # Apply any explicit exclude setting
        for exclusion in opts.exclude:
            if exclusion in attrs["base_columns"]:
                attrs["base_columns"].pop(exclusion)
        # Now reorder the columns based on explicit sequence
        if opts.sequence:
            opts.sequence.expand(attrs["base_columns"].keys())
            # Table's sequence defaults to sequence declared in Meta
            #attrs['_sequence'] = opts.sequence
            attrs["base_columns"] = SortedDict(((x, attrs["base_columns"][x]) for x in opts.sequence))

        # set localize on columns
        for col_name in attrs["base_columns"].keys():
            localize_column = None
            if col_name in opts.localize:
                localize_column = True
            # unlocalize gets higher precedence
            if col_name in opts.unlocalize:
                localize_column = False

            if localize_column is not None:
                attrs["base_columns"][col_name].localize = localize_column

        return super(DeclarativeColumnsMetaclass, mcs).__new__(mcs, name, bases, attrs)


class TableOptions(object):
    """
    Extracts and exposes options for a `.Table` from a `.Table.Meta`
    when the table is defined. See `.Table` for documentation on the impact of
    variables in this class.

    :param options: options for a table
    :type  options: `.Table.Meta` on a `.Table`
    """
    # pylint: disable=R0902
    def __init__(self, options=None):
        super(TableOptions, self).__init__()
        self.attrs = AttributeDict(getattr(options, "attrs", {}))
        self.default = getattr(options, "default", "—")
        self.empty_text = getattr(options, "empty_text", None)
        self.fields = getattr(options, "fields", ())
        self.exclude = getattr(options, "exclude", ())
        order_by = getattr(options, "order_by", None)
        if isinstance(order_by, six.string_types):
            order_by = (order_by, )
        self.order_by = OrderByTuple(order_by) if order_by is not None else None
        self.order_by_field = getattr(options, "order_by_field", "sort")
        self.page_field = getattr(options, "page_field", "page")
        self.per_page = getattr(options, "per_page", 25)
        self.per_page_field = getattr(options, "per_page_field", "per_page")
        self.prefix = getattr(options, "prefix", "")
        self.sequence = Sequence(getattr(options, "sequence", ()))
        if hasattr(options, "sortable"):
            warnings.warn("`Table.Meta.sortable` is deprecated, use `orderable` instead",
                          DeprecationWarning)
        self.orderable = self.sortable = getattr(options, "orderable", getattr(options, "sortable", True))
        self.model = getattr(options, "model", None)
        self.template = getattr(options, "template", "django_tables2/table.html")
        self.localize = getattr(options, "localize", ())
        self.unlocalize = getattr(options, "unlocalize", ())


class TableBase(object):
    """
    A representation of a table.


    .. attribute:: attrs

        HTML attributes to add to the ``<table>`` tag.

        :type: `dict`

        When accessing the attribute, the value is always returned as an
        `.AttributeDict` to allow easily conversion to HTML.


    .. attribute:: columns

        The columns in the table.

        :type: `.BoundColumns`


    .. attribute:: default

        Text to render in empty cells (determined by `.Column.empty_values`,
        default `.Table.Meta.default`)

        :type: `unicode`


    .. attribute:: empty_text

        Empty text to render when the table has no data. (default
        `.Table.Meta.empty_text`)

        :type: `unicode`


    .. attribute:: exclude

        The names of columns that shouldn't be included in the table.

        :type: iterable of `unicode`


    .. attribute:: order_by_field

        If not `None`, defines the name of the *order by* querystring field.

        :type: `unicode`


    .. attribute:: page

        The current page in the context of pagination.

        Added during the call to `.Table.paginate`.


    .. attribute:: page_field

        If not `None`, defines the name of the *current page* querystring
        field.

        :type: `unicode`


    .. attribute:: paginator

        The current paginator for the table.

        Added during the call to `.Table.paginate`.


    .. attribute:: per_page_field

        If not `None`, defines the name of the *per page* querystring field.

        :type: `unicode`


    .. attribute:: prefix

        A prefix for querystring fields to avoid name-clashes when using
        multiple tables on a single page.

        :type: `unicode`


    .. attribute:: rows

        The rows of the table (ignoring pagination).

        :type: `.BoundRows`


    .. attribute:: sequence

        The sequence/order of columns the columns (from left to right).

        :type: iterable

        Items in the sequence must be :term:`column names <column name>`, or
        ``"..."`` (string containing three periods). ``...`` can be used as a
        catch-all for columns that aren't specified.


    .. attribute:: orderable

        Enable/disable column ordering on this table

        :type: `bool`


    .. attribute:: template

        The template to render when using ``{% render_table %}`` (default
        ``"django_tables2/table.html"``)

        :type: `unicode`

    """
    TableDataClass = TableData

    def __init__(self, data, order_by=None, orderable=None, empty_text=None,
                 exclude=None, attrs=None, sequence=None, prefix=None,
                 order_by_field=None, page_field=None, per_page_field=None,
                 template=None, sortable=None, default=None, request=None):
        super(TableBase, self).__init__()
        self.exclude = exclude or ()
        self.sequence = sequence
        self.data = self.TableDataClass(data=data, table=self)
        if default is None:
            default = self._meta.default
        self.default = default
        self.rows = BoundRows(data=self.data, table=self)
        self.attrs = AttributeDict(computed_values(attrs if attrs is not None
                                                         else self._meta.attrs))
        self.empty_text = empty_text if empty_text is not None else self._meta.empty_text
        if sortable is not None:
            warnings.warn("`sortable` is deprecated, use `orderable` instead.",
                          DeprecationWarning)
            if orderable is None:
                orderable = sortable
        self.orderable = orderable
        self.prefix = prefix
        self.order_by_field = order_by_field
        self.page_field = page_field
        self.per_page_field = per_page_field
        # Make a copy so that modifying this will not touch the class
        # definition. Note that this is different from forms, where the
        # copy is made available in a ``fields`` attribute.
        self.base_columns = copy.deepcopy(type(self).base_columns)
        # Keep fully expanded ``sequence`` at _sequence so it's easily accessible
        # during render. The priority is as follows:
        # 1. sequence passed in as an argument
        # 2. sequence declared in ``Meta``
        # 3. sequence defaults to '...'
        if sequence is not None:
            self._sequence = Sequence(sequence)
            self._sequence.expand(self.base_columns.keys())
        elif self._meta.sequence:
            self._sequence = self._meta.sequence
        else:
            self._sequence = Sequence(self._meta.fields + ('...',))
            self._sequence.expand(self.base_columns.keys())
        self.columns = columns.BoundColumns(self)
        # `None` value for order_by means no order is specified. This means we
        # `shouldn't touch our data's ordering in any way. *However*
        # `table.order_by = None` means "remove any ordering from the data"
        # (it's equivalent to `table.order_by = ()`).
        if order_by is None and self._meta.order_by is not None:
            order_by = self._meta.order_by
        if order_by is None:
            self._order_by = None
            # If possible inspect the ordering on the data we were given and
            # update the table to reflect that.
            order_by = self.data.ordering
            if order_by is not None:
                self.order_by = order_by
        else:
            self.order_by = order_by
        self.template = template
        # If a request is passed, configure for request
        if request:
            RequestConfig(request).configure(self)

    def as_html(self):
        """
        Render the table to a simple HTML table.

        If this method is used in the request/response cycle, any links
        generated will clobber the querystring of the request. Use the
        ``{% render_table %}`` template tag instead.
        """
        template = get_template(self.template)
        request = build_request()
        return template.render(RequestContext(request, {'table': self}))

    @property
    def attrs(self):
        return self._attrs

    @attrs.setter
    def attrs(self, value):
        self._attrs = value

    @property
    def empty_text(self):
        return self._empty_text

    @empty_text.setter
    def empty_text(self, value):
        self._empty_text = value

    @property
    def order_by(self):
        return self._order_by

    @order_by.setter
    def order_by(self, value):
        """
        Order the rows of the table based on columns.

        :param value: iterable of order by aliases.
        """
        # collapse empty values to ()
        order_by = () if not value else value
        # accept string
        order_by = order_by.split(',') if isinstance(order_by, six.string_types) else order_by
        valid = []
        # everything's been converted to a iterable, accept iterable!
        for alias in order_by:
            name = OrderBy(alias).bare
            if name in self.columns and self.columns[name].orderable:
                valid.append(alias)
        self._order_by = OrderByTuple(valid)
        self.data.order_by(self._order_by)

    @property
    def order_by_field(self):
        return (self._order_by_field if self._order_by_field is not None
                else self._meta.order_by_field)

    @order_by_field.setter
    def order_by_field(self, value):
        self._order_by_field = value

    @property
    def page_field(self):
        return (self._page_field if self._page_field is not None
                else self._meta.page_field)

    @page_field.setter
    def page_field(self, value):
        self._page_field = value

    def paginate(self, klass=Paginator, per_page=None, page=1, *args, **kwargs):
        """
        Paginates the table using a paginator and creates a ``page`` property
        containing information for the current page.

        :type     klass: Paginator class
        :param    klass: a paginator class to paginate the results
        :type  per_page: `int`
        :param per_page: how many records are displayed on each page
        :type      page: `int`
        :param     page: which page should be displayed.

        Extra arguments are passed to the paginator.

        Pagination exceptions (`~django.core.paginator.EmptyPage` and
        `~django.core.paginator.PageNotAnInteger`) may be raised from this
        method and should be handled by the caller.
        """
        per_page = per_page or self._meta.per_page
        self.paginator = klass(self.rows, per_page, *args, **kwargs)
        self.page = self.paginator.page(page)

    @property
    def per_page_field(self):
        return (self._per_page_field if self._per_page_field is not None
                else self._meta.per_page_field)

    @per_page_field.setter
    def per_page_field(self, value):
        self._per_page_field = value

    @property
    def prefix(self):
        return (self._prefix if self._prefix is not None
                else self._meta.prefix)

    @prefix.setter
    def prefix(self, value):
        self._prefix = value

    @property
    def prefixed_order_by_field(self):
        return "%s%s" % (self.prefix, self.order_by_field)

    @property
    def prefixed_page_field(self):
        return "%s%s" % (self.prefix, self.page_field)

    @property
    def prefixed_per_page_field(self):
        return "%s%s" % (self.prefix, self.per_page_field)

    @property
    def sequence(self):
        return self._sequence

    @sequence.setter
    def sequence(self, value):
        if value:
            value = Sequence(value)
            value.expand(self.base_columns.keys())
        self._sequence = value

    @property
    def orderable(self):
        return (self._orderable if self._orderable is not None
                                else self._meta.orderable)

    @orderable.setter
    def orderable(self, value):
        self._orderable = value

    @property
    def sortable(self):
        warnings.warn("`sortable` is deprecated, use `orderable` instead.",
                      DeprecationWarning)
        return self.orderable

    @sortable.setter
    def sortable(self, value):
        warnings.warn("`sortable` is deprecated, use `orderable` instead.",
                      DeprecationWarning)
        self.orderable = value

    @property
    def template(self):
        return (self._template if self._template is not None
                               else self._meta.template)

    @template.setter
    def template(self, value):
        self._template = value

# Python 2/3 compatible way to enable the metaclass
Table = DeclarativeColumnsMetaclass(str('Table'), (TableBase, ), {})

########NEW FILE########
__FILENAME__ = django_tables2
# coding: utf-8
from __future__ import absolute_import, unicode_literals
from django import template
from django.core.exceptions import ImproperlyConfigured
from django.template import TemplateSyntaxError, Variable, Node
from django.template.loader import get_template, select_template
from django.template.defaultfilters import stringfilter, title as old_title
from django.utils.datastructures import SortedDict
from django.utils.http import urlencode
from django.utils.html import escape
from django.utils.safestring import mark_safe
import django_tables2 as tables
from django_tables2.config import RequestConfig
import re
import six
import tokenize


register = template.Library()
kwarg_re = re.compile(r"(?:(.+)=)?(.+)")
context_processor_error_msg = (
    "{%% %s %%} requires django.core.context_processors.request "
    "to be in your settings.TEMPLATE_CONTEXT_PROCESSORS in order for "
    "the included template tags to function correctly."
)


def token_kwargs(bits, parser):
    """
    Based on Django's `~django.template.defaulttags.token_kwargs`, but with a
    few changes:

    - No legacy mode.
    - Both keys and values are compiled as a filter
    """
    if not bits:
        return {}
    kwargs = SortedDict()
    while bits:
        match = kwarg_re.match(bits[0])
        if not match or not match.group(1):
            return kwargs
        key, value = match.groups()
        del bits[:1]
        kwargs[parser.compile_filter(key)] = parser.compile_filter(value)
    return kwargs


class SetUrlParamNode(Node):
    def __init__(self, changes):
        super(SetUrlParamNode, self).__init__()
        self.changes = changes

    def render(self, context):
        if not 'request' in context:
            raise ImproperlyConfigured(context_processor_error_msg
                                       % 'set_url_param')
        params = dict(context['request'].GET)
        for key, newvalue in self.changes.items():
            newvalue = newvalue.resolve(context)
            if newvalue == '' or newvalue is None:
                params.pop(key, False)
            else:
                params[key] = six.text_type(newvalue)
        return "?" + urlencode(params, doseq=True)


@register.tag
def set_url_param(parser, token):
    """
    Creates a URL (containing only the querystring [including "?"]) based on
    the current URL, but updated with the provided keyword arguments.

    Example::

        {% set_url_param name="help" age=20 %}
        ?name=help&age=20

    **Deprecated** as of 0.7.0, use `querystring`.
    """
    bits = token.contents.split()
    qschanges = {}
    for i in bits[1:]:
        try:
            key, value = i.split('=', 1)
            key = key.strip()
            value = value.strip()
            key_line_iter = six.StringIO(key).readline
            keys = list(tokenize.generate_tokens(key_line_iter))
            if keys[0][0] == tokenize.NAME:
                # workaround bug #5270
                value = Variable(value) if value == '""' else parser.compile_filter(value)
                qschanges[str(key)] = value
            else:
                raise ValueError
        except ValueError:
            raise TemplateSyntaxError("Argument syntax wrong: should be"
                                      "key=value")
    return SetUrlParamNode(qschanges)


class QuerystringNode(Node):
    def __init__(self, updates, removals):
        super(QuerystringNode, self).__init__()
        self.updates = updates
        self.removals = removals

    def render(self, context):
        if not 'request' in context:
            raise ImproperlyConfigured(context_processor_error_msg
                                       % 'querystring')
        params = dict(context['request'].GET)
        for key, value in self.updates.items():
            key = key.resolve(context)
            value = value.resolve(context)
            if key not in ("", None):
                params[key] = value
        for removal in self.removals:
            params.pop(removal.resolve(context), None)
        return escape("?" + urlencode(params, doseq=True))


# {% querystring "name"="abc" "age"=15 %}
@register.tag
def querystring(parser, token):
    """
    Creates a URL (containing only the querystring [including "?"]) derived
    from the current URL's querystring, by updating it with the provided
    keyword arguments.

    Example (imagine URL is ``/abc/?gender=male&name=Brad``)::

        {% querystring "name"="Ayers" "age"=20 %}
        ?name=Ayers&gender=male&age=20
        {% querystring "name"="Ayers" without "gender" %}
        ?name=Ayers

    """
    bits = token.split_contents()
    tag = bits.pop(0)
    updates = token_kwargs(bits, parser)
    # ``bits`` should now be empty of a=b pairs, it should either be empty, or
    # have ``without`` arguments.
    if bits and bits.pop(0) != "without":
        raise TemplateSyntaxError("Malformed arguments to '%s'" % tag)
    removals = [parser.compile_filter(bit) for bit in bits]
    return QuerystringNode(updates, removals)


class RenderTableNode(Node):
    """
    :param    table: the table to render
    :type     table: Table object
    :param template: Name[s] of template to render
    :type  template: unicode or list
    """
    def __init__(self, table, template=None):
        super(RenderTableNode, self).__init__()
        self.table = table
        self.template = template

    def render(self, context):
        table = self.table.resolve(context)

        if isinstance(table, tables.Table):
            pass
        elif hasattr(table, "model"):
            queryset = table

            # We've been given a queryset, create a table using its model and
            # render that.
            class OnTheFlyTable(tables.Table):
                class Meta:
                    model = queryset.model
                    attrs = {"class": "paleblue"}
            table = OnTheFlyTable(queryset)
            request = context.get('request')
            if request:
                RequestConfig(request).configure(table)
        else:
            raise ValueError("Expected table or queryset, not '%s'." %
                             type(table).__name__)

        if self.template:
            template = self.template.resolve(context)
        else:
            template = table.template

        if isinstance(template, six.string_types):
            template = get_template(template)
        else:
            # assume some iterable was given
            template = select_template(template)

        # Contexts are basically a `MergeDict`, when you `update()`, it
        # internally just adds a dict to the list to attempt lookups from. This
        # is why we're able to `pop()` later.
        context.update({"table": table})
        try:
            # HACK:
            # TemplateColumn benefits from being able to use the context
            # that the table is rendered in. The current way this is
            # achieved is to temporarily attach the context to the table,
            # which TemplateColumn then looks for and uses.
            table.context = context
            return template.render(context)
        finally:
            del table.context
            context.pop()

@register.tag
def render_table(parser, token):
    """
    Render a HTML table.

    The tag can be given either a `.Table` object, or a queryset. An optional
    second argument can specify the template to use.

    Example::

        {% render_table table %}
        {% render_table table "custom.html" %}
        {% render_table user_queryset %}

    When given a queryset, a `.Table` class is generated dynamically as
    follows::

        class OnTheFlyTable(tables.Table):
            class Meta:
                model = queryset.model
                attrs = {"class": "paleblue"}

    For configuration beyond this, a `.Table` class must be manually defined,
    instantiated, and passed to this tag.

    The context should include a *request* variable containing the current
    request. This allows pagination URLs to be created without clobbering the
    existing querystring.
    """
    bits = token.split_contents()
    try:
        tag, table = bits.pop(0), parser.compile_filter(bits.pop(0))
    except ValueError:
        raise TemplateSyntaxError("'%s' must be given a table or queryset."
                                  % bits[0])
    template = parser.compile_filter(bits.pop(0)) if bits else None
    return RenderTableNode(table, template)


class NoSpacelessNode(Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist
        super(NoSpacelessNode, self).__init__()

    def render(self, context):
        return mark_safe(re.sub(r'>\s+<', '>&#32;<',
                                self.nodelist.render(context)))

@register.tag
def nospaceless(parser, token):
    nodelist = parser.parse(('endnospaceless',))
    parser.delete_first_token()
    return NoSpacelessNode(nodelist)


RE_UPPERCASE = re.compile('[A-Z]')


@register.filter
@stringfilter
def title(value):
    """
    A slightly better title template filter.

    Same as Django's builtin `~django.template.defaultfilters.title` filter,
    but operates on individual words and leaves words unchanged if they already
    have a capital letter.
    """
    title_word = lambda w: w if RE_UPPERCASE.search(w) else old_title(w)
    return re.sub('(\S+)', lambda m: title_word(m.group(0)), value)
title.is_safe = True


# Django 1.2 doesn't include the l10n template tag library (and it's non-
# trivial to implement) so for Django 1.2 the localize functionality is
# disabled.
try:
    from django.templatetags.l10n import register as l10n_register
except ImportError:
    localize = unlocalize = lambda x: x  # no-op
else:
    localize = l10n_register.filters['localize']
    unlocalize = l10n_register.filters['unlocalize']

register.filter('localize', localize)
register.filter('unlocalize', unlocalize)

########NEW FILE########
__FILENAME__ = utils
# coding: utf-8
from __future__ import absolute_import, unicode_literals
from django.core.handlers.wsgi import WSGIRequest
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.test.client import FakePayload
from itertools import chain
import inspect
import six
import warnings


def python_2_unicode_compatible(klass):
    """
    A decorator that defines __unicode__ and __str__ methods under Python 2.
    Under Python 3 it does nothing.

    To support Python 2 and 3 with a single code base, define a __str__ method
    returning text and apply this decorator to the class.

    Taken directly from Django.
    """
    if not six.PY3:
        klass.__unicode__ = klass.__str__
        klass.__str__ = lambda self: self.__unicode__().encode('utf-8')
    return klass


class Sequence(list):
    """
    Represents a column sequence, e.g. ``("first_name", "...", "last_name")``

    This is used to represent `.Table.Meta.sequence` or the `.Table`
    constructors's *sequence* keyword argument.

    The sequence must be a list of column names and is used to specify the
    order of the columns on a table. Optionally a "..." item can be inserted,
    which is treated as a *catch-all* for column names that aren't explicitly
    specified.
    """
    def expand(self, columns):
        """
        Expands the ``"..."`` item in the sequence into the appropriate column
        names that should be placed there.

        :raises: `ValueError` if the sequence is invalid for the columns.
        """
        ellipses = self.count("...")
        if ellipses > 1:
            raise ValueError("'...' must be used at most once in a sequence.")
        elif ellipses == 0:
            self.append("...")

        # everything looks good, let's expand the "..." item
        columns = list(columns)  # take a copy and exhaust the generator
        head = []
        tail = []
        target = head  # start by adding things to the head
        for name in self:
            if name == "...":
                # now we'll start adding elements to the tail
                target = tail
                continue
            target.append(name)
            if name in columns:
                columns.pop(columns.index(name))
        self[:] = chain(head, columns, tail)


class OrderBy(six.text_type):
    """
    A single item in an `.OrderByTuple` object. This class is
    essentially just a `str` with some extra properties.
    """
    @property
    def bare(self):
        """
        Return the bare form.

        The *bare form* is the non-prefixed form. Typically the bare form is
        just the ascending form.

        Example: ``age`` is the bare form of ``-age``

        :rtype: `.OrderBy` object
        """
        return OrderBy(self[1:]) if self[:1] == '-' else self

    @property
    def opposite(self):
        """
        Return an `.OrderBy` object with an opposite sort influence.

        Example:

        .. code-block:: python

            >>> order_by = OrderBy('name')
            >>> order_by.opposite
            '-name'

        :rtype: `.OrderBy` object
        """
        return OrderBy(self[1:]) if self.is_descending else OrderBy('-' + self)

    @property
    def is_descending(self):
        """
        Return `True` if this object induces *descending* ordering

        :rtype: `bool`
        """
        return self.startswith('-')

    @property
    def is_ascending(self):
        """
        Return `True` if this object induces *ascending* ordering.

        :returns: `bool`
        """
        return not self.is_descending


@python_2_unicode_compatible
class OrderByTuple(tuple):
    """Stores ordering as (as `.OrderBy` objects). The
    `~django_tables2.tables.Table.order_by` property is always converted
    to an `.OrderByTuple` object.

    This class is essentially just a `tuple` with some useful extras.

    Example:

    .. code-block:: python

        >>> x = OrderByTuple(('name', '-age'))
        >>> x['age']
        '-age'
        >>> x['age'].is_descending
        True
        >>> x['age'].opposite
        'age'

    """
    def __new__(cls, iterable):
        transformed = []
        for item in iterable:
            if not isinstance(item, OrderBy):
                item = OrderBy(item)
            transformed.append(item)
        return super(OrderByTuple, cls).__new__(cls, transformed)

    def __unicode__(self):
        return ','.join(self)

    def __contains__(self, name):
        """
        Determine if a column has an influence on ordering.

        Example:

        .. code-block:: python

            >>> ordering =
            >>> x = OrderByTuple(('name', ))
            >>> 'name' in  x
            True
            >>> '-name' in x
            True

        :param name: The name of a column. (optionally prefixed)
        :returns: `bool`
        """
        name = OrderBy(name).bare
        for order_by in self:
            if order_by.bare == name:
                return True
        return False

    def __getitem__(self, index):
        """
        Allows an `.OrderBy` object to be extracted via named or integer
        based indexing.

        When using named based indexing, it's fine to used a prefixed named.

        .. code-block:: python

            >>> x = OrderByTuple(('name', '-age'))
            >>> x[0]
            'name'
            >>> x['age']
            '-age'
            >>> x['-age']
            '-age'

        :rtype: `.OrderBy` object
        """
        if isinstance(index, six.string_types):
            for order_by in self:
                if order_by == index or order_by.bare == index:
                    return order_by
            raise KeyError
        return super(OrderByTuple, self).__getitem__(index)

    @property
    def key(self):
        accessors = []
        reversing = []
        for order_by in self:
            accessors.append(Accessor(order_by.bare))
            reversing.append(order_by.is_descending)

        @total_ordering
        class Comparator(object):
            def __init__(self, obj):
                self.obj = obj

            def __eq__(self, other):
                for accessor in accessors:
                    a = accessor.resolve(self.obj, quiet=True)
                    b = accessor.resolve(other.obj, quiet=True)
                    if not a == b:
                        return False
                return True

            def __lt__(self, other):
                for accessor, reverse in six.moves.zip(accessors, reversing):
                    a = accessor.resolve(self.obj, quiet=True)
                    b = accessor.resolve(other.obj, quiet=True)
                    if a == b:
                        continue
                    if reverse:
                        a, b = b, a
                    # The rest of this should be refactored out into a util
                    # function 'compare' that handles different types.
                    try:
                        return a < b
                    except TypeError:
                        # If the truth values differ, it's a good way to
                        # determine ordering.
                        if bool(a) is not bool(b):
                            return bool(a) < bool(b)
                        # Handle comparing different types, by falling back to
                        # the string and id of the type. This at least groups
                        # different types together.
                        a_type = type(a)
                        b_type = type(b)
                        return (repr(a_type), id(a_type)) < (repr(b_type), id(b_type))
                return False
        return Comparator

    @property
    def cmp(self):
        """
        Return a function for use with `list.sort` that implements this
        object's ordering. This is used to sort non-`.QuerySet` based
        :term:`table data`.

        :rtype: function
        """
        warnings.warn('`cmp` is deprecated, use `key` instead.',
                      DeprecationWarning)

        # pylint: disable=C0103
        def _cmp(a, b):
            for accessor, reverse in instructions:
                x = accessor.resolve(a)
                y = accessor.resolve(b)
                try:
                    res = cmp(x, y)
                except TypeError:
                    res = cmp((repr(type(x)), id(type(x)), x),
                              (repr(type(y)), id(type(y)), y))
                if res != 0:
                    return -res if reverse else res
            return 0
        instructions = []
        for order_by in self:
            if order_by.startswith('-'):
                instructions.append((Accessor(order_by[1:]), True))
            else:
                instructions.append((Accessor(order_by), False))
        return _cmp

    def get(self, key, fallback):
        """
        Identical to __getitem__, but supports fallback value.
        """
        try:
            return self[key]
        except (KeyError, IndexError):
            return fallback

    @property
    def opposite(self):
        """
        Return version with each `.OrderBy` prefix toggled.

        Example:

        .. code-block:: python

            >>> order_by = OrderByTuple(('name', '-age'))
            >>> order_by.opposite
            ('-name', 'age')
        """
        return type(self)((o.opposite for o in self))


class Accessor(str):
    """
    A string describing a path from one object to another via attribute/index
    accesses. For convenience, the class has an alias `.A` to allow for more concise code.

    Relations are separated by a ``.`` character.
    """
    SEPARATOR = '.'

    def resolve(self, context, safe=True, quiet=False):
        """
        Return an object described by the accessor by traversing the attributes
        of *context*.

        Example:

        .. code-block:: python

            >>> x = Accessor('__len__')
            >>> x.resolve('brad')
            4
            >>> x = Accessor('0.upper')
            >>> x.resolve('brad')
            'B'

        :type  context: `object`
        :param context: The root/first object to traverse.
        :type     safe: `bool`
        :param    safe: Don't call anything with ``alters_data = True``
        :type    quiet: bool
        :param   quiet: Smother all exceptions and instead return `None`
        :returns: target object
        :raises: anything ``getattr(a, "b")`` raises, e.g. `TypeError`,
                 `AttributeError`, `KeyError`, `ValueError` (unless *quiet* ==
                 `True`)

        `~.Accessor.resolve` attempts lookups in the following order:

        - dictionary (e.g. ``obj[related]``)
        - attribute (e.g. ``obj.related``)
        - list-index lookup (e.g. ``obj[int(related)]``)

        Callable objects are called, and their result is used, before
        proceeding with the resolving.
        """
        try:
            current = context
            for bit in self.bits:
                try:  # dictionary lookup
                    current = current[bit]
                except (TypeError, AttributeError, KeyError):
                    try:  # attribute lookup
                        current = getattr(current, bit)
                    except (TypeError, AttributeError):
                        try:  # list-index lookup
                            current = current[int(bit)]
                        except (IndexError,  # list index out of range
                                ValueError,  # invalid literal for int()
                                KeyError,    # dict without `int(bit)` key
                                TypeError,   # unsubscriptable object
                                ):
                            raise ValueError('Failed lookup for key [%s] in %r'
                                             ', when resolving the accessor %s'
                                              % (bit, current, self))
                if callable(current):
                    if safe and getattr(current, 'alters_data', False):
                        raise ValueError('refusing to call %s() because `.alters_data = True`'
                                         % repr(current))
                    current = current()
                # important that we break in None case, or a relationship
                # spanning across a null-key will raise an exception in the
                # next iteration, instead of defaulting.
                if current is None:
                    break
            return current
        except:
            if not quiet:
                raise

    @property
    def bits(self):
        if self == '':
            return ()
        return self.split(self.SEPARATOR)


A = Accessor  # alias

class AttributeDict(dict):
    """
    A wrapper around `dict` that knows how to render itself as HTML
    style tag attributes.

    The returned string is marked safe, so it can be used safely in a template.
    See `.as_html` for a usage example.
    """
    def as_html(self):
        """
        Render to HTML tag attributes.

        Example:

        .. code-block:: python

            >>> from django_tables2.utils import AttributeDict
            >>> attrs = AttributeDict({'class': 'mytable', 'id': 'someid'})
            >>> attrs.as_html()
            'class="mytable" id="someid"'

        :rtype: `~django.utils.safestring.SafeUnicode` object

        """
        return mark_safe(' '.join(['%s="%s"' % (k, escape(v if not callable(v) else v()))
                                   for k, v in six.iteritems(self)]))


class Attrs(dict):
    """
    Backwards compatibility, deprecated.
    """
    def __init__(self, *args, **kwargs):
        super(Attrs, self).__init__(*args, **kwargs)
        warnings.warn("Attrs class is deprecated, use dict instead.",
                      DeprecationWarning)


def segment(sequence, aliases):
    """
    Translates a flat sequence of items into a set of prefixed aliases.

    This allows the value set by `.QuerySet.order_by` to be translated into
    a list of columns that would have the same result. These are called
    "order by aliases" which are optionally prefixed column names.

    e.g.

        >>> list(segment(("a", "-b", "c"),
        ...              {"x": ("a"),
        ...               "y": ("b", "-c"),
        ...               "z": ("-b", "c")}))
        [("x", "-y"), ("x", "z")]

    """
    if not (sequence or aliases):
        return
    for alias, parts in aliases.items():
        variants = {
            # alias: order by tuple
            alias:  OrderByTuple(parts),
            OrderBy(alias).opposite: OrderByTuple(parts).opposite,
        }
        for valias, vparts in variants.items():
            if list(sequence[:len(vparts)]) == list(vparts):
                tail_aliases = dict(aliases)
                del tail_aliases[alias]
                tail_sequence = sequence[len(vparts):]
                if tail_sequence:
                    for tail in segment(tail_sequence, tail_aliases):
                        yield tuple(chain([valias], tail))
                    else:
                        continue
                else:
                    yield tuple([valias])


class cached_property(object):  # pylint: disable=C0103
    """
    Decorator that creates converts a method with a single
    self argument into a property cached on the instance.

    Taken directly from Django 1.4.
    """
    def __init__(self, func):
        from functools import wraps
        wraps(func)(self)
        self.func = func

    def __get__(self, instance, cls):
        res = instance.__dict__[self.func.__name__] = self.func(instance)
        return res


funcs = (name for name in ('getfullargspec', 'getargspec')
                       if hasattr(inspect, name))
getargspec = getattr(inspect, next(funcs))
del funcs


def build_request(uri='/'):
    """
    Return a fresh HTTP GET / request.

    This is essentially a heavily cutdown version of Django 1.3's
    `~django.test.client.RequestFactory`.
    """
    path, _, querystring = uri.partition('?')
    return WSGIRequest({
        'CONTENT_TYPE':      'text/html; charset=utf-8',
        'PATH_INFO':         path,
        'QUERY_STRING':      querystring,
        'REMOTE_ADDR':       '127.0.0.1',
        'REQUEST_METHOD':    'GET',
        'SCRIPT_NAME':       '',
        'SERVER_NAME':       'testserver',
        'SERVER_PORT':       '80',
        'SERVER_PROTOCOL':   'HTTP/1.1',
        'wsgi.version':      (1, 0),
        'wsgi.url_scheme':   'http',
        'wsgi.input':        FakePayload(b''),
        'wsgi.errors':       six.StringIO(),
        'wsgi.multiprocess': True,
        'wsgi.multithread':  False,
        'wsgi.run_once':     False,
    })


def total_ordering(cls):
    """Class decorator that fills in missing ordering methods"""
    convert = {
        '__lt__': [('__gt__', lambda self, other: not (self < other or self == other)),
                   ('__le__', lambda self, other: self < other or self == other),
                   ('__ge__', lambda self, other: not self < other)],
        '__le__': [('__ge__', lambda self, other: not self <= other or self == other),
                   ('__lt__', lambda self, other: self <= other and not self == other),
                   ('__gt__', lambda self, other: not self <= other)],
        '__gt__': [('__lt__', lambda self, other: not (self > other or self == other)),
                   ('__ge__', lambda self, other: self > other or self == other),
                   ('__le__', lambda self, other: not self > other)],
        '__ge__': [('__le__', lambda self, other: (not self >= other) or self == other),
                   ('__gt__', lambda self, other: self >= other and not self == other),
                   ('__lt__', lambda self, other: not self >= other)]
    }
    roots = set(dir(cls)) & set(convert)
    if not roots:
        raise ValueError('must define at least one ordering operation: < > <= >=')
    root = max(roots)       # prefer __lt__ to __le__ to __gt__ to __ge__
    for opname, opfunc in convert[root]:
        if opname not in roots:
            opfunc.__name__ = str(opname)  # Py2 requires non-unicode, Py3 requires unicode.
            opfunc.__doc__ = getattr(int, opname).__doc__
            setattr(cls, opname, opfunc)
    return cls


def computed_values(d):
    """
    Computes a new `dict` that has callable values replaced with the return values.

    Simple example:

        >>> compute_values({"foo": lambda: "bar"})
        {"foo": "bar"}

    Arbitrarily deep structures are supported. The logic is as follows:

    1. If the value is callable, call it and make that the new value.
    2. If the value is an instance of dict, use ComputableDict to compute its keys.

    Example:

        >>> def parents():
        ...     return {
        ...         "father": lambda: "Foo",
        ...         "mother": "Bar"
        ...      }
        ...
        >>> a = {
        ...     "name": "Brad",
        ...     "parents": parents
        ... }
        ...
        >>> computed_values(a)
        {"name": "Brad", "parents": {"father": "Foo", "mother": "Bar"}}

    :rtype: dict
    """
    result = {}
    for k, v in six.iteritems(d):
        if callable(v):
            v = v()
        if isinstance(v, dict):
            v = computed_values(v)
        result[k] = v
    return result

########NEW FILE########
__FILENAME__ = views
# coding: utf-8
from __future__ import unicode_literals
from django.core.exceptions import ImproperlyConfigured
from django.views.generic.list import ListView
from .config import RequestConfig


class SingleTableMixin(object):
    """
    Adds a Table object to the context. Typically used with
    `.TemplateResponseMixin`.

    :param        table_class: table class
    :type         table_class: subclass of `.Table`
    :param         table_data: data used to populate the table
    :type          table_data: any compatible data source
    :param context_table_name: name of the table's template variable (default:
                               "table")
    :type  context_table_name: `unicode`
    :param   table_pagination: controls table pagination. If a `dict`, passed as
                               the *paginate* keyword argument to
                               `.RequestConfig`. As such, any non-`False`
                               value enables pagination.

    This mixin plays nice with the Django's`.MultipleObjectMixin` by using
    `.get_queryset`` as a fallback for the table data source.

    """
    table_class = None
    table_data = None
    context_table_name = None
    table_pagination = None

    def get_table(self, **kwargs):
        """
        Return a table object to use. The table has automatic support for
        sorting and pagination.
        """
        options = {}
        table_class = self.get_table_class()
        table = table_class(self.get_table_data(), **kwargs)
        paginate = self.get_table_pagination()  # pylint: disable=E1102
        if paginate is not None:
            options['paginate'] = paginate
        RequestConfig(self.request, **options).configure(table)
        return table

    def get_table_class(self):
        """
        Return the class to use for the table.
        """
        if self.table_class:
            return self.table_class
        raise ImproperlyConfigured("A table class was not specified. Define "
                                   "%(cls)s.table_class"
                                   % {"cls": type(self).__name__})

    def get_context_table_name(self, table):
        """
        Get the name to use for the table's template variable.
        """
        return self.context_table_name or "table"

    def get_table_data(self):
        """
        Return the table data that should be used to populate the rows.
        """
        if self.table_data:
            return self.table_data
        elif hasattr(self, "get_queryset"):
            return self.get_queryset()
        raise ImproperlyConfigured("Table data was not specified. Define "
                                   "%(cls)s.table_data"
                                   % {"cls": type(self).__name__})

    def get_table_pagination(self):
        """
        Returns pagination options: True for standard pagination (default),
        False for no pagination, and a dictionary for custom pagination.
        """
        return self.table_pagination

    def get_context_data(self, **kwargs):
        """
        Overriden version of `.TemplateResponseMixin` to inject the table into
        the template's context.
        """
        context = super(SingleTableMixin, self).get_context_data(**kwargs)
        table = self.get_table()
        context[self.get_context_table_name(table)] = table
        return context


class SingleTableView(SingleTableMixin, ListView):
    """
    Generic view that renders a template and passes in a `.Table` object.
    """

########NEW FILE########
__FILENAME__ = conf
# coding: utf-8
import os
from os.path import abspath, dirname, join
import re
import sys

os.environ["DJANGO_SETTINGS_MODULE"] = "example.settings"

# import project
sys.path.insert(0, abspath('..'))
import example
import django_tables2
sys.path.pop(0)


project = 'django-tables2'
with open('../django_tables2/__init__.py', 'rb') as f:
    release = re.search('__version__ = "(.+?)"', f.read()).group(1)
version = release.rpartition('.')[0]


default_role = "py:obj"


extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
    'sphinx.ext.doctest',
]

intersphinx_mapping = {
    'python': ('http://docs.python.org/dev/', None),
    'django': ('http://docs.djangoproject.com/en/dev/', 'http://docs.djangoproject.com/en/dev/_objects/'),
}


master_doc = 'index'


html_theme = 'default'
html_static_path = ['_static']

########NEW FILE########
__FILENAME__ = admin
# coding: utf-8
from django.contrib import admin
from .models import Country


class CountryAdmin(admin.ModelAdmin):
    list_per_page = 2
admin.site.register(Country, CountryAdmin)

########NEW FILE########
__FILENAME__ = models
# coding: utf-8
from __future__ import unicode_literals
from django.db import models
from django.utils.translation import ugettext_lazy as _


class Country(models.Model):
    """Represents a geographical Country"""
    name = models.CharField(max_length=100)
    population = models.PositiveIntegerField(verbose_name="población")
    tz = models.CharField(max_length=50)
    visits = models.PositiveIntegerField()
    commonwealth = models.NullBooleanField()
    flag = models.FileField(upload_to="country/flags/")

    class Meta:
        verbose_name_plural = _("countries")

    def __unicode__(self):
        return self.name

    @property
    def summary(self):
        return "%s (pop. %s)" % (self.name, self.population)


class Person(models.Model):
    name = models.CharField(max_length=200, verbose_name="full name")

    class Meta:
        verbose_name_plural = "people"

    def __unicode__(self):
        return self.name

########NEW FILE########
__FILENAME__ = tables
# coding: utf-8
import django_tables2 as tables
from .models import Country


class CountryTable(tables.Table):
    name = tables.Column()
    population = tables.Column()
    tz = tables.Column(verbose_name='time zone')
    visits = tables.Column()
    summary = tables.Column(order_by=("name", "population"))

    class Meta:
        model = Country


class ThemedCountryTable(CountryTable):
    class Meta:
        attrs = {'class': 'paleblue'}

########NEW FILE########
__FILENAME__ = tests
# coding: utf-8
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = views
# coding: utf-8
from django.shortcuts import render
from django_tables2   import RequestConfig, SingleTableView
from .tables import CountryTable, ThemedCountryTable
from .models import Country, Person


def multiple(request):
    qs = Country.objects.all()

    example1 = CountryTable(qs, prefix="1-")
    RequestConfig(request, paginate=False).configure(example1)

    example2 = CountryTable(qs, prefix="2-")
    RequestConfig(request, paginate={"per_page": 2}).configure(example2)

    example3 = ThemedCountryTable(qs, prefix="3-")
    RequestConfig(request, paginate={"per_page": 3}).configure(example3)

    example4 = ThemedCountryTable(qs, prefix="4-")
    RequestConfig(request, paginate={"per_page": 3}).configure(example4)

    example5 = ThemedCountryTable(qs, prefix="5-")
    example5.template = "extended_table.html"
    RequestConfig(request, paginate={"per_page": 3}).configure(example5)

    return render(request, 'multiple.html', {
        'example1': example1,
        'example2': example2,
        'example3': example3,
        'example4': example4,
        'example5': example5,
    })


class ClassBased(SingleTableView):
    table_class = ThemedCountryTable
    queryset = Country.objects.all()
    template_name = "class_based.html"

class_based = ClassBased.as_view()


def tutorial(request):
    return render(request, "tutorial.html", {"people": Person.objects.all()})

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys
from django.core.management import execute_from_command_line

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
# coding: utf-8
# import django_tables2
from os.path import dirname, join, abspath
import sys

ROOT = dirname(abspath(__file__))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': join(ROOT, 'database.sqlite'),  # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = join(ROOT, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

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
SECRET_KEY = '=nzw@mkqk)tz+_#vf%li&8sn7yn8z7!2-4njuyf1rxs*^muhvh'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.contrib.messages.context_processors.messages",
    "django.core.context_processors.request",
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    "debug_toolbar.middleware.DebugToolbarMiddleware",
)

ROOT_URLCONF = 'example.urls'

TEMPLATE_DIRS = (
    join(ROOT, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'example.app',
    'django_tables2',
    'debug_toolbar',
)

INTERNAL_IPS = (
    "127.0.0.1",
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
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
# coding: utf-8
from django.conf import settings
from django.conf.urls import patterns, include, url


from django.contrib import admin
admin.autodiscover()


urlpatterns = patterns('example.app.views',
    url(r'^$',             'multiple'),
    url(r'^class-based/$', 'class_based'),
    url(r'^tutorial/$',    'tutorial'),

    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
) + patterns('',
    url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {
        'document_root': settings.MEDIA_ROOT,
    }),
)

########NEW FILE########
__FILENAME__ = models
# coding: utf-8
from __future__ import unicode_literals
from django.db import models
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy
from django.utils.translation import ugettext
import six


class Person(models.Model):
    first_name = models.CharField(max_length=200)

    last_name = models.CharField(max_length=200, verbose_name='surname')

    occupation = models.ForeignKey(
            'Occupation', related_name='people',
            null=True, verbose_name='occupation')

    trans_test = models.CharField(
            max_length=200, blank=True,
            verbose_name=ugettext("translation test"))

    trans_test_lazy = models.CharField(
            max_length=200, blank=True,
            verbose_name=ugettext_lazy("translation test lazy"))

    safe = models.CharField(
            max_length=200, blank=True, verbose_name=mark_safe("<b>Safe</b>"))

    class Meta:
        verbose_name = "person"
        verbose_name_plural = "people"

    def __unicode__(self):
        return self.first_name

    @property
    def name(self):
        return "%s %s" % (self.first_name, self.last_name)


class Occupation(models.Model):
    name = models.CharField(max_length=200)
    region = models.ForeignKey('Region', null=True)

    def __unicode__(self):
        return self.name


class Region(models.Model):
    name = models.CharField(max_length=200)
    mayor = models.OneToOneField(Person, null=True)

    def __unicode__(self):
        return self.name


# -- haystack -----------------------------------------------------------------

if not six.PY3:  # Haystack isn't compatible with Python 3
    from haystack import indexes

    class PersonIndex(indexes.SearchIndex, indexes.Indexable):
        first_name = indexes.CharField(document=True)

        def get_model(self):
            return Person

        def index_queryset(self, using=None):
            return self.get_model().objects.all()

########NEW FILE########
__FILENAME__ = settings
from django.conf import global_settings
import six


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

INSTALLED_APPS = [
    'tests.app',
    'django_tables2',
]

ROOT_URLCONF = 'tests.app.urls'

SECRET_KEY = "this is super secret"

TEMPLATE_CONTEXT_PROCESSORS = [
    'django.core.context_processors.request'
] + list(global_settings.TEMPLATE_CONTEXT_PROCESSORS)

TIME_ZONE = "Australia/Brisbane"

USE_TZ = True

if not six.PY3:  # Haystack isn't compatible with Python 3
    INSTALLED_APPS += [
        'haystack',
    ]
    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'haystack.backends.simple_backend.SimpleEngine',
        }
    }
########NEW FILE########
__FILENAME__ = urls
# coding: utf-8
try:
    from django.conf.urls import patterns, url
except ImportError:
    from django.conf.urls.defaults import patterns, url
from . import views


urlpatterns = patterns('',
    url(r'^people/(?P<pk>\d+)/$',      views.person,     name='person'),
    url(r'^occupations/(?P<pk>\d+)/$', views.occupation, name='occupation'),
    url(r'^&\'"/(?P<pk>\d+)/$',        lambda req: None, name='escaping'),
)

########NEW FILE########
__FILENAME__ = views
# coding: utf-8
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from .models import Person, Occupation


def person(request, pk):
    """A really simple view to provide an endpoint for the 'person' URL."""
    person = get_object_or_404(Person, pk=pk)
    return HttpResponse('Person: %s' % person)


def occupation(request, pk):
    """
    Another really simple view to provide an endpoint for the 'occupation' URL.
    """
    occupation = get_object_or_404(Occupation, pk=pk)
    return HttpResponse('Occupation: %s' % occupation)

########NEW FILE########
__FILENAME__ = columns
# coding: utf-8
# pylint: disable=R0912,E0102
from __future__ import unicode_literals
from attest import assert_hook, Tests, warns  # pylint: disable=W0611
from datetime import date, datetime
from django_attest import settings, TestContext
import django_tables2 as tables
from django_tables2.utils import build_request
from django_tables2 import A, Attrs
from django.db import models
from django.db.models.fields.files import FieldFile
from django.core.urlresolvers import reverse
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.template import Context, Template
from django.utils.translation import ugettext
from django.utils.safestring import mark_safe, SafeData
try:
    from django.utils import timezone
except ImportError:
    timezone = None
from os.path import dirname, join
import pytz
from .app.models import Person
from .templates import attrs, parse


booleancolumn = Tests()


@booleancolumn.test
def should_be_used_for_booleanfield():
    class BoolModel(models.Model):
        field = models.BooleanField()

    class Table(tables.Table):
        class Meta:
            model = BoolModel

    column = Table.base_columns["field"]
    assert type(column) == tables.BooleanColumn
    assert column.empty_values != ()


@booleancolumn.test
def should_be_used_for_nullbooleanfield():
    class NullBoolModel(models.Model):
        field = models.NullBooleanField()

    class Table(tables.Table):
        class Meta:
            model = NullBoolModel

    column = Table.base_columns["field"]
    assert type(column) == tables.BooleanColumn
    assert column.empty_values == ()


@booleancolumn.test
def treat_none_different_from_false():
    class Table(tables.Table):
        col = tables.BooleanColumn(null=False, default="---")

    table = Table([{"col": None}])
    assert table.rows[0]["col"] == "---"


@booleancolumn.test
def treat_none_as_false():
    class Table(tables.Table):
        col = tables.BooleanColumn(null=True)

    table = Table([{"col": None}])
    assert table.rows[0]["col"] == '<span class="false">✘</span>'


@booleancolumn.test
def span_attrs():
    class Table(tables.Table):
        col = tables.BooleanColumn(attrs={"span": {"key": "value"}})

    table = Table([{"col": True}])
    assert attrs(table.rows[0]["col"]) == {"class": "true", "key": "value"}


checkboxcolumn = Tests()


@checkboxcolumn.test
def attrs_should_be_translated_for_backwards_compatibility():
    with warns(DeprecationWarning):
        class TestTable(tables.Table):
            col = tables.CheckBoxColumn(header_attrs={"th_key": "th_value"},
                                        attrs={"td_key": "td_value"})

    table = TestTable([{"col": "data"}])
    assert attrs(table.columns["col"].header) == {"type": "checkbox", "th_key": "th_value"}
    assert attrs(table.rows[0]["col"])        == {"type": "checkbox", "td_key": "td_value", "value": "data", "name": "col"}


@checkboxcolumn.test
def new_attrs_should_be_supported():
    with warns(DeprecationWarning):
        class TestTable(tables.Table):
            col1 = tables.CheckBoxColumn(attrs=Attrs(th__input={"th_key": "th_value"},
                                                     td__input={"td_key": "td_value"}))
            col2 = tables.CheckBoxColumn(attrs=Attrs(input={"key": "value"}))

    table = TestTable([{"col1": "data", "col2": "data"}])
    assert attrs(table.columns["col1"].header) == {"type": "checkbox", "th_key": "th_value"}
    assert attrs(table.rows[0]["col1"])        == {"type": "checkbox", "td_key": "td_value", "value": "data", "name": "col1"}
    assert attrs(table.columns["col2"].header) == {"type": "checkbox", "key": "value"}
    assert attrs(table.rows[0]["col2"])        == {"type": "checkbox", "key": "value", "value": "data", "name": "col2"}


general = Tests()


@general.test
def column_render_supports_kwargs():
    class TestColumn(tables.Column):
        def render(self, **kwargs):
            expected = set(("record", "value", "column", "bound_column",
                           "bound_row", "table"))
            actual = set(kwargs.keys())
            assert actual == expected
            return "success"

    class TestTable(tables.Table):
        foo = TestColumn()

    table = TestTable([{"foo": "bar"}])
    assert table.rows[0]["foo"] == "success"


@general.test
def column_header_should_use_titlised_verbose_name_unless_given_explicitly():
    class SimpleTable(tables.Table):
        basic = tables.Column()
        acronym = tables.Column(verbose_name="has FBI help")

    table = SimpleTable([])
    assert table.columns["basic"].header == "Basic"
    assert table.columns["acronym"].header == "has FBI help"


@general.test
def should_support_safe_verbose_name():
    class SimpleTable(tables.Table):
        safe = tables.Column(verbose_name=mark_safe("<b>Safe</b>"))

    table = SimpleTable([])
    assert isinstance(table.columns["safe"].header, SafeData)


@general.test
def should_support_safe_verbose_name_via_model():
    class PersonTable(tables.Table):
        safe = tables.Column()

    table = PersonTable(Person.objects.all())
    assert isinstance(table.columns["safe"].header, SafeData)


@general.test
def sortable_backwards_compatibility():
    # Table.Meta.sortable (not set)
    class SimpleTable(tables.Table):
        name = tables.Column()
    table = SimpleTable([])
    with warns(DeprecationWarning):
        assert table.columns['name'].sortable is True

    # Table.Meta.sortable = False
    with warns(DeprecationWarning):
        class SimpleTable(tables.Table):
            name = tables.Column()

            class Meta:
                sortable = False
    table = SimpleTable([])
    with warns(DeprecationWarning):
        assert table.columns['name'].sortable is False  # backwards compatible
    assert table.columns['name'].orderable is False

    # Table.Meta.sortable = True
    with warns(DeprecationWarning):
        class SimpleTable(tables.Table):
            name = tables.Column()

            class Meta:
                sortable = True
    table = SimpleTable([])
    with warns(DeprecationWarning):
        assert table.columns['name'].sortable is True  # backwards compatible
    assert table.columns['name'].orderable is True


@general.test
def orderable():
    # Table.Meta.orderable = False
    class SimpleTable(tables.Table):
        name = tables.Column()
    table = SimpleTable([])
    assert table.columns['name'].orderable is True

    # Table.Meta.orderable = False
    class SimpleTable(tables.Table):
        name = tables.Column()

        class Meta:
            orderable = False
    table = SimpleTable([])
    assert table.columns['name'].orderable is False
    with warns(DeprecationWarning):
        assert table.columns['name'].sortable is False  # backwards compatible

    # Table.Meta.orderable = True
    class SimpleTable(tables.Table):
        name = tables.Column()

        class Meta:
            orderable = True
    table = SimpleTable([])
    with warns(DeprecationWarning):
        assert table.columns['name'].sortable is True  # backwards compatible
    assert table.columns['name'].orderable is True


@general.test
def order_by_defaults_to_accessor():
    class SimpleTable(tables.Table):
        foo = tables.Column(accessor="bar")

    table = SimpleTable([])
    assert table.columns["foo"].order_by == ("bar", )


@general.test
def supports_order_by():
    class SimpleTable(tables.Table):
        name = tables.Column(order_by=("last_name", "-first_name"))
        age = tables.Column()

    table = SimpleTable([], order_by=("-age", ))
    # alias
    assert table.columns["name"].order_by_alias == "name"
    assert table.columns["age"].order_by_alias == "-age"
    # order by
    assert table.columns["name"].order_by == ("last_name", "-first_name")
    assert table.columns["age"].order_by == ("-age", )

    # now try with name ordered
    table = SimpleTable([], order_by=("-name", ))
    # alias
    assert table.columns["name"].order_by_alias == "-name"
    assert table.columns["age"].order_by_alias == "age"
    # alias next
    assert table.columns["name"].order_by_alias.next == "name"
    assert table.columns["age"].order_by_alias.next == "age"
    # order by
    assert table.columns["name"].order_by == ("-last_name", "first_name")
    assert table.columns["age"].order_by == ("age", )


@general.test
def supports_is_ordered():
    class SimpleTable(tables.Table):
        name = tables.Column()

    # sorted
    table = SimpleTable([], order_by='name')
    assert table.columns["name"].is_ordered
    # unsorted
    table = SimpleTable([])
    assert not table.columns["name"].is_ordered


@general.test
def translation():
    """
    Tests different types of values for the ``verbose_name`` property of a
    column.
    """
    class TranslationTable(tables.Table):
        normal = tables.Column(verbose_name=ugettext("Normal"))
        lazy = tables.Column(verbose_name=ugettext("Lazy"))

    table = TranslationTable([])
    assert "Normal" == table.columns["normal"].header
    assert "Lazy" == table.columns["lazy"].header


@general.test
def sequence():
    """
    Ensures that the sequence of columns is configurable.
    """
    class TestTable(tables.Table):
        a = tables.Column()
        b = tables.Column()
        c = tables.Column()
    assert ["a", "b", "c"] == TestTable([]).columns.names()
    assert ["b", "a", "c"] == TestTable([], sequence=("b", "a", "c")).columns.names()

    class TestTable2(TestTable):
        class Meta:
            sequence = ("b", "a", "c")
    assert ["b", "a", "c"] == TestTable2([]).columns.names()
    assert ["a", "b", "c"] == TestTable2([], sequence=("a", "b", "c")).columns.names()

    class TestTable3(TestTable):
        class Meta:
            sequence = ("c", )
    assert ["c", "a", "b"] == TestTable3([]).columns.names()
    assert ["c", "a", "b"] == TestTable([], sequence=("c", )).columns.names()

    class TestTable4(TestTable):
        class Meta:
            sequence = ("...", )
    assert ["a", "b", "c"] == TestTable4([]).columns.names()
    assert ["a", "b", "c"] == TestTable([], sequence=("...", )).columns.names()

    class TestTable5(TestTable):
        class Meta:
            sequence = ("b", "...")
    assert ["b", "a", "c"] == TestTable5([]).columns.names()
    assert ["b", "a", "c"] == TestTable([], sequence=("b", "...")).columns.names()

    class TestTable6(TestTable):
        class Meta:
            sequence = ("...", "b")
    assert ["a", "c", "b"] == TestTable6([]).columns.names()
    assert ["a", "c", "b"] == TestTable([], sequence=("...", "b")).columns.names()

    class TestTable7(TestTable):
        class Meta:
            sequence = ("b", "...", "a")
    assert ["b", "c", "a"] == TestTable7([]).columns.names()
    assert ["b", "c", "a"] == TestTable([], sequence=("b", "...", "a")).columns.names()

    # Let's test inheritence
    class TestTable8(TestTable):
        d = tables.Column()
        e = tables.Column()
        f = tables.Column()

        class Meta:
            sequence = ("d", "...")

    class TestTable9(TestTable):
        d = tables.Column()
        e = tables.Column()
        f = tables.Column()

    assert ["d", "a", "b", "c", "e", "f"] == TestTable8([]).columns.names()
    assert ["d", "a", "b", "c", "e", "f"] == TestTable9([], sequence=("d", "...")).columns.names()


@general.test
def should_support_both_meta_sequence_and_constructor_exclude():
    """
    Issue #32 describes a problem when both ``Meta.sequence`` and
    ``Table(..., exclude=...)`` are used on a single table. The bug caused an
    exception to be raised when the table was iterated.
    """
    class SequencedTable(tables.Table):
        a = tables.Column()
        b = tables.Column()
        c = tables.Column()

        class Meta:
            sequence = ('a', '...')

    table = SequencedTable([], exclude=('c', ))
    table.as_html()


@general.test
def bound_columns_should_support_indexing():
    class SimpleTable(tables.Table):
        a = tables.Column()
        b = tables.Column()

    table = SimpleTable([])
    assert 'b' == table.columns[1].name
    assert 'b' == table.columns['b'].name


@general.test
def cell_attrs_applies_to_td_and_th():
    class SimpleTable(tables.Table):
        a = tables.Column(attrs={"cell": {"key": "value"}})

    # providing data ensures 1 row is rendered
    table = SimpleTable([{"a": "value"}])
    root = parse(table.as_html())

    assert root.findall('.//thead/tr/th')[0].attrib == {"key": "value", "class": "a orderable sortable"}
    assert root.findall('.//tbody/tr/td')[0].attrib == {"key": "value", "class": "a"}


@general.test
def cells_are_automatically_given_column_name_as_class():
    class SimpleTable(tables.Table):
        a = tables.Column()

    table = SimpleTable([{"a": "value"}])
    root = parse(table.as_html())
    assert root.findall('.//thead/tr/th')[0].attrib == {"class": "a orderable sortable"}
    assert root.findall('.//tbody/tr/td')[0].attrib == {"class": "a"}


@general.test
def th_are_given_sortable_class_if_column_is_orderable():
    class SimpleTable(tables.Table):
        a = tables.Column()
        b = tables.Column(orderable=False)

    table = SimpleTable([{"a": "value"}])
    root = parse(table.as_html())
    # return classes of an element as a set
    classes = lambda x: set(x.attrib["class"].split())
    assert "sortable" in classes(root.findall('.//thead/tr/th')[0])
    assert "sortable" not in classes(root.findall('.//thead/tr/th')[1])

    # Now try with an ordered table
    table = SimpleTable([], order_by="a")
    root = parse(table.as_html())
    # return classes of an element as a set
    assert "sortable" in classes(root.findall('.//thead/tr/th')[0])
    assert "asc" in classes(root.findall('.//thead/tr/th')[0])
    assert "sortable" not in classes(root.findall('.//thead/tr/th')[1])


@general.test
def empty_values_triggers_default():
    class Table(tables.Table):
        a = tables.Column(empty_values=(1, 2), default="--")

    table = Table([{"a": 1}, {"a": 2}, {"a": 3}, {"a": 4}])
    assert [x["a"] for x in table.rows] == ["--", "--", 3, 4]


linkcolumn = Tests()
linkcolumn.context(TestContext())

@linkcolumn.test
def unicode():
    """Test LinkColumn"""
    # test unicode values + headings
    class UnicodeTable(tables.Table):
        first_name = tables.LinkColumn('person', args=[A('pk')])
        last_name = tables.LinkColumn('person', args=[A('pk')], verbose_name='äÚ¨´ˆÁ˜¨ˆ˜˘Ú…Ò˚ˆπ∆ˆ´')

    dataset = [
        {'pk': 1, 'first_name': 'Brädley', 'last_name': '∆yers'},
        {'pk': 2, 'first_name': 'Chr…s', 'last_name': 'DÒble'},
    ]

    table = UnicodeTable(dataset)
    request = build_request('/some-url/')
    template = Template('{% load django_tables2 %}{% render_table table %}')
    html = template.render(Context({'request': request, 'table': table}))

    assert 'Brädley' in html
    assert '∆yers' in html
    assert 'Chr…s' in html
    assert 'DÒble' in html


@linkcolumn.test
def null_foreign_key():
    class PersonTable(tables.Table):
        first_name = tables.Column()
        last_name = tables.Column()
        occupation = tables.LinkColumn('occupation', args=[A('occupation.pk')])

    Person.objects.create(first_name='bradley', last_name='ayers')

    table = PersonTable(Person.objects.all())
    table.as_html()


@linkcolumn.test
def kwargs():
    class PersonTable(tables.Table):
        a = tables.LinkColumn('occupation', kwargs={"pk": A('a')})

    html = PersonTable([{"a": 0}, {"a": 1}]).as_html()
    assert reverse("occupation", kwargs={"pk": 0}) in html
    assert reverse("occupation", kwargs={"pk": 1}) in html


@linkcolumn.test
def html_escape_value():
    class PersonTable(tables.Table):
        name = tables.LinkColumn("escaping", kwargs={"pk": A("pk")})

    table = PersonTable([{"name": "<brad>", "pk": 1}])
    assert table.rows[0]["name"] == '<a href="/&amp;&#39;%22/1/">&lt;brad&gt;</a>'


@linkcolumn.test
def old_style_attrs_should_still_work():
    with warns(DeprecationWarning):
        class TestTable(tables.Table):
            col = tables.LinkColumn('occupation', kwargs={"pk": A('col')},
                                    attrs={"title": "Occupation Title"})

    table = TestTable([{"col": 0}])
    assert attrs(table.rows[0]["col"]) == {"href": reverse("occupation", kwargs={"pk": 0}),
                                           "title": "Occupation Title"}


@linkcolumn.test
def a_attrs_should_be_supported():
    class TestTable(tables.Table):
        col = tables.LinkColumn('occupation', kwargs={"pk": A('col')},
                                attrs={"a": {"title": "Occupation Title"}})

    table = TestTable([{"col": 0}])
    assert attrs(table.rows[0]["col"]) == {"href": reverse("occupation", kwargs={"pk": 0}),
                                           "title": "Occupation Title"}


@linkcolumn.test
def defaults():
    class Table(tables.Table):
        link = tables.LinkColumn('occupation', kwargs={"pk": 1}, default="xyz")

    table = Table([{}])
    assert table.rows[0]['link'] == 'xyz'


templatecolumn = Tests()


@templatecolumn.test
def should_handle_context_on_table():
    class TestTable(tables.Table):
        col_code = tables.TemplateColumn(template_code="code:{{ record.col }}{{ STATIC_URL }}")
        col_name = tables.TemplateColumn(template_name="test_template_column.html")

    table = TestTable([{"col": "brad"}])
    assert table.rows[0]["col_code"] == "code:brad"
    assert table.rows[0]["col_name"] == "name:brad"
    table.context = Context({"STATIC_URL": "/static/"})
    assert table.rows[0]["col_code"] == "code:brad/static/"
    assert table.rows[0]["col_name"] == "name:brad/static/"


@templatecolumn.test
def should_support_default():
    class Table(tables.Table):
        foo = tables.TemplateColumn("default={{ default }}", default="bar")

    table = Table([{}])
    assert table.rows[0]["foo"] == "default=bar"


@templatecolumn.test
def should_support_value():
    class Table(tables.Table):
        foo = tables.TemplateColumn("value={{ value }}")

    table = Table([{"foo": "bar"}])
    assert table.rows[0]["foo"] == "value=bar"


urlcolumn = Tests()


@urlcolumn.test
def should_turn_url_into_hyperlink():
    class TestTable(tables.Table):
        url = tables.URLColumn()

    table = TestTable([{"url": "http://example.com"}])
    assert table.rows[0]["url"] == '<a href="http://example.com">http://example.com</a>'


@urlcolumn.test
def should_be_used_for_urlfields():
    class URLModel(models.Model):
        field = models.URLField()

    class Table(tables.Table):
        class Meta:
            model = URLModel

    assert type(Table.base_columns["field"]) == tables.URLColumn


emailcolumn = Tests()


@emailcolumn.test
def should_turn_email_address_into_hyperlink():
    class Table(tables.Table):
        email = tables.EmailColumn()

    table = Table([{"email": "test@example.com"}])
    assert table.rows[0]["email"] == '<a href="mailto:test@example.com">test@example.com</a>'


@emailcolumn.test
def should_render_default_for_blank():
    class Table(tables.Table):
        email = tables.EmailColumn(default="---")

    table = Table([{"email": ""}])
    assert table.rows[0]["email"] == '---'


@emailcolumn.test
def should_be_used_for_datetimefields():
    class EmailModel(models.Model):
        field = models.EmailField()

    class Table(tables.Table):
        class Meta:
            model = EmailModel

    assert type(Table.base_columns["field"]) == tables.EmailColumn


datecolumn = Tests()

# Format string: https://docs.djangoproject.com/en/1.4/ref/templates/builtins/#date
# D -- Day of the week, textual, 3 letters  -- 'Fri'
# b -- Month, textual, 3 letters, lowercase -- 'jan'
# Y -- Year, 4 digits.                      -- '1999'

@datecolumn.test
def should_handle_explicit_format():
    class TestTable(tables.Table):
        date = tables.DateColumn(format="D b Y")

        class Meta:
            default = "—"

    table = TestTable([{"date": date(2012, 9, 11)},
                       {"date": None}])
    assert table.rows[0]["date"] == "Tue sep 2012"
    assert table.rows[1]["date"] == "—"


@datecolumn.test
def should_handle_long_format():
    with settings(DATE_FORMAT="D Y b"):
        class TestTable(tables.Table):
            date = tables.DateColumn(short=False)

            class Meta:
                default = "—"

        table = TestTable([{"date": date(2012, 9, 11)},
                           {"date": None}])
        assert table.rows[0]["date"] == "Tue 2012 sep"
        assert table.rows[1]["date"] == "—"


@datecolumn.test
def should_handle_short_format():
    with settings(SHORT_DATE_FORMAT="b Y D"):
        class TestTable(tables.Table):
            date = tables.DateColumn(short=True)

            class Meta:
                default = "—"

        table = TestTable([{"date": date(2012, 9, 11)},
                           {"date": None}])
        assert table.rows[0]["date"] == "sep 2012 Tue"
        assert table.rows[1]["date"] == "—"


@datecolumn.test
def should_be_used_for_datefields():
    class DateModel(models.Model):
        field = models.DateField()

    class Table(tables.Table):
        class Meta:
            model = DateModel

    assert type(Table.base_columns["field"]) == tables.DateColumn


datetimecolumn = Tests()

# Format string: https://docs.djangoproject.com/en/1.4/ref/templates/builtins/#date
# D -- Day of the week, textual, 3 letters  -- 'Fri'
# b -- Month, textual, 3 letters, lowercase -- 'jan'
# Y -- Year, 4 digits.                      -- '1999'
# A -- 'AM' or 'PM'.                        -- 'AM'
# f -- Time, in 12-hour hours[:minutes]     -- '1', '1:30'


@datetimecolumn.context
def dt():
    dt = datetime(2012, 9, 11, 12, 30)
    if timezone:
        # If the version of Django has timezone support, convert from naive to
        # UTC, the test project uses Australia/Brisbane so regardless the
        # output from the column should be the same.
        dt = (dt.replace(tzinfo=pytz.timezone("Australia/Brisbane"))
                .astimezone(pytz.UTC))
    yield dt


@datetimecolumn.test
def should_handle_explicit_format(dt):
    class TestTable(tables.Table):
        date = tables.DateTimeColumn(format="D b Y")

        class Meta:
            default = "—"

    table = TestTable([{"date": dt}, {"date": None}])
    assert table.rows[0]["date"] == "Tue sep 2012"
    assert table.rows[1]["date"] == "—"


@datetimecolumn.test
def should_handle_long_format(dt):
    class TestTable(tables.Table):
        date = tables.DateTimeColumn(short=False)

        class Meta:
            default = "—"

    with settings(DATETIME_FORMAT="D Y b A f"):
        table = TestTable([{"date": dt}, {"date": None}])
        assert table.rows[0]["date"] == "Tue 2012 sep PM 12:30"
        assert table.rows[1]["date"] == "—"


@datetimecolumn.test
def should_handle_short_format(dt):
    class TestTable(tables.Table):
        date = tables.DateTimeColumn(short=True)

        class Meta:
            default = "—"

    with settings(SHORT_DATETIME_FORMAT="b Y D A f"):
        table = TestTable([{"date": dt}, {"date": None}])
        assert table.rows[0]["date"] == "sep 2012 Tue PM 12:30"
        assert table.rows[1]["date"] == "—"


@datetimecolumn.test
def should_be_used_for_datetimefields():
    class DateTimeModel(models.Model):
        field = models.DateTimeField()

    class Table(tables.Table):
        class Meta:
            model = DateTimeModel

    assert type(Table.base_columns["field"]) == tables.DateTimeColumn


filecolumn = Tests()


@filecolumn.context
def template_storage_and_column():
    """Provide a storage that exposes the test templates"""
    root = join(dirname(__file__), "app", "templates")
    storage = FileSystemStorage(location=root, base_url="/baseurl/")
    column = tables.FileColumn(attrs={"span": {"class": "span"},
                                      "a":    {"class": "a"}})
    yield column, storage


@filecolumn.test
def should_be_used_for_filefields():
    class FileModel(models.Model):
        field = models.FileField()

    class Table(tables.Table):
        class Meta:
            model = FileModel

    assert type(Table.base_columns["field"]) == tables.FileColumn


@filecolumn.test
def filecolumn_supports_storage_file(column, storage):
    file_ = storage.open("child/foo.html")
    try:
        root = parse(column.render(value=file_))
    finally:
        file_.close()
    path = file_.name
    assert root.tag == "span"
    assert root.attrib == {"class": "span exists", "title": path}
    assert root.text == "foo.html"


@filecolumn.test
def filecolumn_supports_contentfile(column):
    name = "foobar.html"
    file_ = ContentFile('')
    file_.name = name  # Django <1.4 compatible
    root = parse(column.render(value=file_))
    assert root.tag == "span"
    assert root.attrib == {"title": name, "class": "span"}
    assert root.text == "foobar.html"


@filecolumn.test
def filecolumn_supports_fieldfile(column, storage):
    field = models.FileField(storage=storage)
    name = "child/foo.html"
    fieldfile = FieldFile(instance=None, field=field, name=name)
    root = parse(column.render(value=fieldfile))
    assert root.tag == "a"
    assert root.attrib == {"class": "a exists", "title": name,
                           "href": "/baseurl/child/foo.html"}
    assert root.text == "foo.html"

    # Now try a file that doesn't exist
    name = "child/does_not_exist.html"
    fieldfile = FieldFile(instance=None, field=field, name=name)
    html = column.render(value=fieldfile)
    root = parse(html)
    assert root.tag == "a"
    assert root.attrib == {"class": "a missing", "title": name,
                           "href": "/baseurl/child/does_not_exist.html"}
    assert root.text == "does_not_exist.html"


columns = Tests([booleancolumn, checkboxcolumn, datecolumn, datetimecolumn,
                 emailcolumn, filecolumn, general, linkcolumn, templatecolumn,
                 urlcolumn])

########NEW FILE########
__FILENAME__ = config
# coding: utf-8
from attest import Tests
from django_tables2 import RequestConfig
from django_tables2.utils import build_request
from django.core.paginator import EmptyPage, PageNotAnInteger
from fudge import Fake


NOTSET = object()  # unique value
requestconfig = Tests()


@requestconfig.context
def faketable():
    yield (Fake("Table")
           .has_attr(prefixed_page_field="page",
                     prefixed_per_page_field="per_page",
                     prefixed_order_by_field="sort"))


@requestconfig.test
def no_querystring(table):
    request = build_request("/")
    table = table.has_attr(order_by=NOTSET).expects("paginate")
    RequestConfig(request).configure(table)
    assert table.order_by is NOTSET


@requestconfig.test
def full_querystring(table):
    request = build_request("/?page=1&per_page=5&sort=abc")
    table = (table
             .expects("paginate").with_args(page=1, per_page=5)
             .expects("order_by").with_args("abc"))
    RequestConfig(request).configure(table)


@requestconfig.test
def partial_querystring(table):
    request = build_request("/?page=1&sort=abc")
    table = (table
             .expects("paginate").with_args(page=1, per_page=5)
             .expects("order_by").with_args("abc"))
    RequestConfig(request, paginate={"per_page": 5}).configure(table)


@requestconfig.test
def silent_page_not_an_integer_error(table):
    request = build_request("/")
    paginator = (Fake("Paginator")
                 .expects("page").with_args(1))
    table = (table
             .has_attr(paginator=paginator)
             .expects("paginate").with_args(page="abc")
             .raises(PageNotAnInteger))

    RequestConfig(request, paginate={"page": "abc",
                                     "silent": True}).configure(table)


@requestconfig.test
def silent_empty_page_error(table):
    request = build_request("/")
    paginator = (Fake("Paginator")
                 .has_attr(num_pages=987)
                 .expects("page").with_args(987))
    table = (table
             .has_attr(paginator=paginator)
             .expects("paginate").with_args(page=123)
             .raises(EmptyPage))

    RequestConfig(request, paginate={"page": 123,
                                     "silent": True}).configure(table)


config = Tests([requestconfig])

########NEW FILE########
__FILENAME__ = core
# coding: utf-8
"""Test the core table functionality."""
from __future__ import absolute_import, unicode_literals
from attest import assert_hook, raises, Tests, warns
import copy
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
import django_tables2 as tables
from django_tables2.tables import DeclarativeColumnsMetaclass
import six
import itertools


core = Tests()


class UnorderedTable(tables.Table):
    i = tables.Column()
    alpha = tables.Column()
    beta = tables.Column()


class OrderedTable(UnorderedTable):
    class Meta:
        order_by = 'alpha'


MEMORY_DATA = [
    {'i': 2, 'alpha': 'b', 'beta': 'b'},
    {'i': 1, 'alpha': 'a', 'beta': 'c'},
    {'i': 3, 'alpha': 'c', 'beta': 'a'},
]


@core.test
def declarations():
    """Test defining tables by declaration."""
    class GeoAreaTable(tables.Table):
        name = tables.Column()
        population = tables.Column()

    assert len(GeoAreaTable.base_columns) == 2
    assert 'name' in GeoAreaTable.base_columns
    assert not hasattr(GeoAreaTable, 'name')

    class CountryTable(GeoAreaTable):
        capital = tables.Column()

    assert len(CountryTable.base_columns) == 3
    assert 'capital' in CountryTable.base_columns

    # multiple inheritance
    class AddedMixin(tables.Table):
        added = tables.Column()

    class CityTable(GeoAreaTable, AddedMixin):
        mayor = tables.Column()

    assert len(CityTable.base_columns) == 4
    assert 'added' in CityTable.base_columns


@core.test
def metaclass_inheritance():
    class Tweaker(type):
        """Adds an attribute "tweaked" to all classes"""
        def __new__(cls, name, bases, attrs):
            attrs['tweaked'] = True
            return super(Tweaker, cls).__new__(cls, name, bases, attrs)

    class Meta(Tweaker, DeclarativeColumnsMetaclass):
        pass

    class TweakedTableBase(tables.Table):
        __metaclass__ = Meta
        name = tables.Column()

    # Python 2/3 compatible way to enable the metaclass
    TweakedTable = Meta(str('TweakedTable'), (TweakedTableBase, ), {})

    table = TweakedTable([])
    assert 'name' in table.columns
    assert table.tweaked

    # now flip the order
    class FlippedMeta(DeclarativeColumnsMetaclass, Tweaker):
        pass

    class FlippedTweakedTableBase(tables.Table):
        name = tables.Column()

    # Python 2/3 compatible way to enable the metaclass
    FlippedTweakedTable = FlippedMeta(str('FlippedTweakedTable'), (FlippedTweakedTableBase, ), {})

    table = FlippedTweakedTable([])
    assert 'name' in table.columns
    assert table.tweaked


@core.test
def attrs():
    class TestTable(tables.Table):
        class Meta:
            attrs = {}
    assert {} == TestTable([]).attrs

    class TestTable2(tables.Table):
        class Meta:
            attrs = {"a": "b"}
    assert {"a": "b"} == TestTable2([]).attrs

    class TestTable3(tables.Table):
        pass
    assert {} == TestTable3([]).attrs
    assert {"a": "b"} == TestTable3([], attrs={"a": "b"}).attrs

    class TestTable4(tables.Table):
        class Meta:
            attrs = {"a": "b"}
    assert {"c": "d"} == TestTable4([], attrs={"c": "d"}).attrs


@core.test
def attrs_support_computed_values():
    counter = itertools.count()

    class TestTable(tables.Table):
        class Meta:
            attrs = {"id": lambda: "test_table_%d" % next(counter)}

    assert {"id": "test_table_0"} == TestTable([]).attrs
    assert {"id": "test_table_1"} == TestTable([]).attrs


@core.test
def data_knows_its_name():
    table = tables.Table([{}])
    assert table.data.verbose_name == "item"
    assert table.data.verbose_name_plural == "items"


@core.test
def datasource_untouched():
    """Ensure that data that is provided to the table (the datasource) is not
    modified by table operations.
    """
    original_data = copy.deepcopy(MEMORY_DATA)

    table = UnorderedTable(MEMORY_DATA)
    table.order_by = 'i'
    list(table.rows)
    assert MEMORY_DATA == original_data

    table = UnorderedTable(MEMORY_DATA)
    table.order_by = 'beta'
    list(table.rows)
    assert MEMORY_DATA == original_data


@core.test
def should_support_tuple_data_source():
    class SimpleTable(tables.Table):
        name = tables.Column()

    table = SimpleTable((
        {'name': 'brad'},
        {'name': 'stevie'},
    ))

    assert len(table.rows) == 2


@core.test_if(not six.PY3)  # Haystack isn't compatible with Python 3
def should_support_haystack_data_source():
    from haystack.query import SearchQuerySet

    class PersonTable(tables.Table):
        first_name = tables.Column()

    table = PersonTable(SearchQuerySet().all())
    table.as_html()


@core.test
def data_validation():
    with raises(ValueError):
        table = OrderedTable(None)
    
    class Bad:
        def __len__(self):
            pass
      
    with raises(ValueError):
        table = OrderedTable(Bad())

    class Ok:
        def __len__(self):
            return 1
        def __getitem__(self, pos):
            if pos != 0:
                raise IndexError()
            return {'a': 1}
    
    table = OrderedTable(Ok())
    assert len(table.rows) == 1

@core.test
def ordering():
    # fallback to Table.Meta
    assert ('alpha', ) == OrderedTable([], order_by=None).order_by == OrderedTable([]).order_by

    # values of order_by are wrapped in tuples before being returned
    assert OrderedTable([], order_by='alpha').order_by   == ('alpha', )
    assert OrderedTable([], order_by=('beta',)).order_by == ('beta', )

    table = OrderedTable([])
    table.order_by = []
    assert () == table.order_by == OrderedTable([], order_by=[]).order_by

    table = OrderedTable([])
    table.order_by = ()
    assert () == table.order_by == OrderedTable([], order_by=()).order_by

    table = OrderedTable([])
    table.order_by = ''
    assert () == table.order_by == OrderedTable([], order_by='').order_by

    # apply an ordering
    table = UnorderedTable([])
    table.order_by = 'alpha'
    assert ('alpha', ) == UnorderedTable([], order_by='alpha').order_by == table.order_by

    table = OrderedTable([])
    table.order_by = 'alpha'
    assert ('alpha', ) == OrderedTable([], order_by='alpha').order_by  == table.order_by

    # let's check the data
    table = OrderedTable(MEMORY_DATA, order_by='beta')
    assert 3 == table.rows[0]['i']

    table = OrderedTable(MEMORY_DATA, order_by='-beta')
    assert 1 == table.rows[0]['i']

    # allow fallback to Table.Meta.order_by
    table = OrderedTable(MEMORY_DATA)
    assert 1 == table.rows[0]['i']

    # column's can't be ordered if they're not allowed to be
    class TestTable2(tables.Table):
        a = tables.Column(orderable=False)
        b = tables.Column()

    table = TestTable2([], order_by='a')
    assert table.order_by == ()

    table = TestTable2([], order_by='b')
    assert table.order_by == ('b', )

    # ordering disabled by default
    class TestTable3(tables.Table):
        a = tables.Column(orderable=True)
        b = tables.Column()

        class Meta:
            orderable = False

    table = TestTable3([], order_by='a')
    assert table.order_by == ('a', )

    table = TestTable3([], order_by='b')
    assert table.order_by == ()

    table = TestTable3([], orderable=True, order_by='b')
    assert table.order_by == ('b', )

    with warns(DeprecationWarning) as captured:
        tables.Column(sortable=True)
        tables.Column(sortable=False)

        class TestTable4(tables.Table):
            class Meta:
                sortable = True

        class TestTable4(tables.Table):
            class Meta:
                sortable = False

    assert len(captured) == 4


@core.test
def ordering_different_types():
    from datetime import datetime

    data = [
        {'i': 1, 'alpha': datetime.now(), 'beta': [1]},
        {'i': {}, 'alpha': None, 'beta': ''},
        {'i': 2, 'alpha': None, 'beta': []},
    ]

    table = OrderedTable(data)
    assert "—" == table.rows[0]['alpha']

    table = OrderedTable(data, order_by='i')
    if six.PY3:
        assert {} == table.rows[0]['i']
    else:
        assert 1 == table.rows[0]['i']


    table = OrderedTable(data, order_by='beta')
    assert [] == table.rows[0]['beta']


@core.test
def multi_column_ordering():
    brad   = {"first_name": "Bradley", "last_name": "Ayers"}
    brad2  = {"first_name": "Bradley", "last_name": "Fake"}
    chris  = {"first_name": "Chris",   "last_name": "Doble"}
    stevie = {"first_name": "Stevie",  "last_name": "Armstrong"}
    ross   = {"first_name": "Ross",    "last_name": "Ayers"}

    people = [brad, brad2, chris, stevie, ross]

    class PersonTable(tables.Table):
        first_name = tables.Column()
        last_name = tables.Column()

    table = PersonTable(people, order_by=("first_name", "last_name"))
    assert [brad, brad2, chris, ross, stevie] == [r.record for r in table.rows]

    table = PersonTable(people, order_by=("first_name", "-last_name"))
    assert [brad2, brad, chris, ross, stevie] == [r.record for r in table.rows]

    # let's try column order_by using multiple keys
    class PersonTable(tables.Table):
        name = tables.Column(order_by=("first_name", "last_name"))

    # add 'name' key for each person.
    for person in people:
        person['name'] = "{p[first_name]} {p[last_name]}".format(p=person)
    assert brad['name'] == "Bradley Ayers"

    table = PersonTable(people, order_by="name")
    assert [brad, brad2, chris, ross, stevie] == [r.record for r in table.rows]

    table = PersonTable(people, order_by="-name")
    assert [stevie, ross, chris, brad2, brad] == [r.record for r in table.rows]


@core.test
def column_count():
    class SimpleTable(tables.Table):
        visible = tables.Column(visible=True)
        hidden = tables.Column(visible=False)

    # The columns container supports the len() builtin
    assert len(SimpleTable([]).columns) == 1


@core.test
def column_accessor():
    class SimpleTable(UnorderedTable):
        col1 = tables.Column(accessor='alpha.upper.isupper')
        col2 = tables.Column(accessor='alpha.upper')
    table = SimpleTable(MEMORY_DATA)
    row = table.rows[0]
    assert row['col1'] is True
    assert row['col2'] == 'B'


@core.test
def exclude_columns():
    """
    Defining ``Table.Meta.exclude`` or providing an ``exclude`` argument when
    instantiating a table should have the same effect -- exclude those columns
    from the table. It should have the same effect as not defining the
    columns originally.
    """
    # Table(..., exclude=...)
    table = UnorderedTable([], exclude=("i"))
    assert [c.name for c in table.columns] == ["alpha", "beta"]

    # Table.Meta: exclude=...
    class PartialTable(UnorderedTable):
        class Meta:
            exclude = ("alpha", )
    table = PartialTable([])
    assert [c.name for c in table.columns] == ["i", "beta"]

    # Inheritence -- exclude in parent, add in child
    class AddonTable(PartialTable):
        added = tables.Column()
    table = AddonTable([])
    assert [c.name for c in table.columns] == ["i", "beta", "added"]

    # Inheritence -- exclude in child
    class ExcludeTable(UnorderedTable):
        added = tables.Column()
        class Meta:
            exclude = ("beta", )
    table = ExcludeTable([])
    assert [c.name for c in table.columns] == ["i", "alpha", "added"]


@core.test
def table_exclude_property_should_override_constructor_argument():
    class SimpleTable(tables.Table):
        a = tables.Column()
        b = tables.Column()

    table = SimpleTable([], exclude=('b', ))
    assert [c.name for c in table.columns] == ['a']
    table.exclude = ('a', )
    assert [c.name for c in table.columns] == ['b']


@core.test
def pagination():
    class BookTable(tables.Table):
        name = tables.Column()

    # create some sample data
    data = []
    for i in range(100):
        data.append({"name": "Book No. %d" % i})
    books = BookTable(data)

    # external paginator
    paginator = Paginator(books.rows, 10)
    assert paginator.num_pages == 10
    page = paginator.page(1)
    assert page.has_previous() is False
    assert page.has_next() is True

    # integrated paginator
    books.paginate(page=1)
    assert hasattr(books, "page") is True

    books.paginate(page=1, per_page=10)
    assert len(list(books.page.object_list)) == 10

    # new attributes
    assert books.paginator.num_pages == 10
    assert books.page.has_previous() is False
    assert books.page.has_next() is True

    # accessing a non-existant page raises 404
    with raises(EmptyPage):
        books.paginate(Paginator, page=9999, per_page=10)

    with raises(PageNotAnInteger):
        books.paginate(Paginator, page='abc', per_page=10)


@core.test
def pagination_shouldnt_prevent_multiple_rendering():
    class SimpleTable(tables.Table):
        name = tables.Column()

    table = SimpleTable([{'name': 'brad'}])
    table.paginate()

    assert table.as_html() == table.as_html()


@core.test
def empty_text():
    class TestTable(tables.Table):
        a = tables.Column()

    table = TestTable([])
    assert table.empty_text is None

    class TestTable2(tables.Table):
        a = tables.Column()

        class Meta:
            empty_text = 'nothing here'

    table = TestTable2([])
    assert table.empty_text == 'nothing here'

    table = TestTable2([], empty_text='still nothing')
    assert table.empty_text == 'still nothing'


@core.test
def prefix():
    """Test that table prefixes affect the names of querystring parameters"""
    class TableA(tables.Table):
        name = tables.Column()

        class Meta:
            prefix = "x"

    assert "x" == TableA([]).prefix

    class TableB(tables.Table):
        name = tables.Column()

    assert "" == TableB([]).prefix
    assert "x" == TableB([], prefix="x").prefix

    table = TableB([])
    table.prefix = "x"
    assert "x" == table.prefix


@core.test
def field_names():
    class TableA(tables.Table):
        class Meta:
            order_by_field = "abc"
            page_field = "def"
            per_page_field = "ghi"

    table = TableA([])
    assert "abc" == table.order_by_field
    assert "def" == table.page_field
    assert "ghi" == table.per_page_field


@core.test
def field_names_with_prefix():
    class TableA(tables.Table):
        class Meta:
            order_by_field = "sort"
            page_field = "page"
            per_page_field = "per_page"
            prefix = "1-"

    table = TableA([])
    assert "1-sort" == table.prefixed_order_by_field
    assert "1-page" == table.prefixed_page_field
    assert "1-per_page" == table.prefixed_per_page_field

    class TableB(tables.Table):
        class Meta:
            order_by_field = "sort"
            page_field = "page"
            per_page_field = "per_page"

    table = TableB([], prefix="1-")
    assert "1-sort" == table.prefixed_order_by_field
    assert "1-page" == table.prefixed_page_field
    assert "1-per_page" == table.prefixed_per_page_field

    table = TableB([])
    table.prefix = "1-"
    assert "1-sort" == table.prefixed_order_by_field
    assert "1-page" == table.prefixed_page_field
    assert "1-per_page" == table.prefixed_per_page_field


@core.test
def should_support_a_template_to_be_specified():
    class MetaDeclarationSpecifiedTemplateTable(tables.Table):
        name = tables.Column()

        class Meta:
            template = "dummy.html"

    table = MetaDeclarationSpecifiedTemplateTable([])
    assert table.template == "dummy.html"

    class ConstructorSpecifiedTemplateTable(tables.Table):
        name = tables.Column()

    table = ConstructorSpecifiedTemplateTable([], template="dummy.html")
    assert table.template == "dummy.html"

    class PropertySpecifiedTemplateTable(tables.Table):
        name = tables.Column()

    table = PropertySpecifiedTemplateTable([])
    table.template = "dummy.html"
    assert table.template == "dummy.html"

    class DefaultTable(tables.Table):
        pass

    table = DefaultTable([])
    assert table.template == "django_tables2/table.html"


@core.test
def should_support_rendering_multiple_times():
    class MultiRenderTable(tables.Table):
        name = tables.Column()

    # test list data
    table = MultiRenderTable([{'name': 'brad'}])
    assert table.as_html() == table.as_html()


@core.test
def column_defaults_are_honored():
    class Table(tables.Table):
        name = tables.Column(default="abcd")

        class Meta:
            default = "efgh"

    table = Table([{}], default="ijkl")
    assert table.rows[0]['name'] == "abcd"


@core.test
def table_meta_defaults_are_honored():
    class Table(tables.Table):
        name = tables.Column()

        class Meta:
            default = "abcd"

    table = Table([{}])
    assert table.rows[0]['name'] == "abcd"


@core.test
def table_defaults_are_honored():
    class Table(tables.Table):
        name = tables.Column()

    table = Table([{}], default="abcd")
    assert table.rows[0]['name'] == "abcd"

    table = Table([{}], default="abcd")
    table.default = "efgh"
    assert table.rows[0]['name'] == "efgh"


@core.test
def list_table_data_supports_ordering():
    class Table(tables.Table):
        name = tables.Column()

    data = [
        {"name": "Bradley"},
        {"name": "Stevie"},
    ]

    table = Table(data)
    assert table.rows[0]["name"] == "Bradley"
    table.order_by = "-name"
    assert table.rows[0]["name"] == "Stevie"

########NEW FILE########
__FILENAME__ = models
# coding: utf-8
from .app.models import Person, Occupation
from attest import assert_hook, Tests  # pylint: disable=W0611
import itertools
from django_attest import TestContext
import django_tables2 as tables
import six


models = Tests()
models.context(TestContext())


class PersonTable(tables.Table):
    first_name = tables.Column()
    last_name = tables.Column()
    occupation = tables.Column()


@models.test
def boundrows_iteration():
    occupation = Occupation.objects.create(name='Programmer')
    Person.objects.create(first_name='Bradley', last_name='Ayers', occupation=occupation)
    Person.objects.create(first_name='Chris',   last_name='Doble', occupation=occupation)

    table = PersonTable(Person.objects.all())
    records = [row.record for row in table.rows]
    expecteds = Person.objects.all()
    for expected, actual in six.moves.zip(expecteds, records):
        assert expected == actual


@models.test
def model_table():
    """
    The ``model`` option on a table causes the table to dynamically add columns
    based on the fields.
    """
    class OccupationTable(tables.Table):
        class Meta:
            model = Occupation
    assert ["id", "name", "region"] == list(OccupationTable.base_columns.keys())

    class OccupationTable2(tables.Table):
        extra = tables.Column()

        class Meta:
            model = Occupation
    assert ["id", "name", "region", "extra"] == list(OccupationTable2.base_columns.keys())

    # be aware here, we already have *models* variable, but we're importing
    # over the top
    from django.db import models

    class ComplexModel(models.Model):
        char = models.CharField(max_length=200)
        fk = models.ForeignKey("self")
        m2m = models.ManyToManyField("self")

    class ComplexTable(tables.Table):
        class Meta:
            model = ComplexModel
    assert ["id", "char", "fk"] == list(ComplexTable.base_columns.keys())


@models.test
def mixins():
    class TableMixin(tables.Table):
        extra = tables.Column()

    class OccupationTable(TableMixin, tables.Table):
        extra2 = tables.Column()

        class Meta:
            model = Occupation
    assert ["extra", "id", "name", "region", "extra2"] == list(OccupationTable.base_columns.keys())


@models.test
def column_verbose_name():
    """
    When using queryset data as input for a table, default to using model field
    verbose names rather than an autogenerated string based on the column name.

    However if a column does explicitly describe a verbose name, it should be
    used.
    """
    class PersonTable(tables.Table):
        """
        The test_colX columns are to test that the accessor is used to
        determine the field on the model, rather than the column name.
        """
        first_name = tables.Column()
        fn1 = tables.Column(accessor='first_name')
        fn2 = tables.Column(accessor='first_name.upper')
        fn3 = tables.Column(accessor='last_name', verbose_name='OVERRIDE')
        last_name = tables.Column()
        ln1 = tables.Column(accessor='last_name')
        ln2 = tables.Column(accessor='last_name.upper')
        ln3 = tables.Column(accessor='last_name', verbose_name='OVERRIDE')
        region = tables.Column(accessor='occupation.region.name')
        r1 = tables.Column(accessor='occupation.region.name')
        r2 = tables.Column(accessor='occupation.region.name.upper')
        r3 = tables.Column(accessor='occupation.region.name', verbose_name='OVERRIDE')
        trans_test = tables.Column()
        trans_test_lazy = tables.Column()

    # The Person model has a ``first_name`` and ``last_name`` field, but only
    # the ``last_name`` field has an explicit ``verbose_name`` set. This means
    # that we should expect that the two columns that use the ``last_name``
    # field should both use the model's ``last_name`` field's ``verbose_name``,
    # however both fields that use the ``first_name`` field should just use a
    # capitalized version of the column name as the column header.
    table = PersonTable(Person.objects.all())
    # Should be generated (capitalized column name)
    assert 'first name' == table.columns['first_name'].verbose_name
    assert 'first name' == table.columns['fn1'].verbose_name
    assert 'first name' == table.columns['fn2'].verbose_name
    assert 'OVERRIDE' == table.columns['fn3'].verbose_name
    # Should use the model field's verbose_name
    assert 'surname' == table.columns['last_name'].verbose_name
    assert 'surname' == table.columns['ln1'].verbose_name
    assert 'surname' == table.columns['ln2'].verbose_name
    assert 'OVERRIDE' == table.columns['ln3'].verbose_name
    assert 'name' == table.columns['region'].verbose_name
    assert 'name' == table.columns['r1'].verbose_name
    assert 'name' == table.columns['r2'].verbose_name
    assert 'OVERRIDE' == table.columns['r3'].verbose_name
    assert "translation test" == table.columns["trans_test"].verbose_name
    assert "translation test lazy" == table.columns["trans_test_lazy"].verbose_name

    # -------------------------------------------------------------------------

    # Now we'll try using a table with Meta.model
    class PersonTable(tables.Table):
        class Meta:
            model = Person
    # Issue #16
    table = PersonTable([])
    assert "translation test" == table.columns["trans_test"].verbose_name
    assert "translation test lazy" == table.columns["trans_test_lazy"].verbose_name


@models.test
def data_verbose_name():
    table = tables.Table(Person.objects.all())
    assert table.data.verbose_name == "person"
    assert table.data.verbose_name_plural == "people"


@models.test
def field_choices_used_to_translated_value():
    """
    When a model field uses the ``choices`` option, a table should render the
    "pretty" value rather than the database value.

    See issue #30 for details.
    """
    LANGUAGES = (
        ('en', 'English'),
        ('ru', 'Russian'),
    )

    from django.db import models

    class Article(models.Model):
        name = models.CharField(max_length=200)
        language = models.CharField(max_length=200, choices=LANGUAGES)

        def __unicode__(self):
            return self.name

    class ArticleTable(tables.Table):
        class Meta:
            model = Article

    table = ArticleTable([Article(name='English article', language='en'),
                          Article(name='Russian article', language='ru')])

    assert 'English' == table.rows[0]['language']
    assert 'Russian' == table.rows[1]['language']


@models.test
def column_mapped_to_nonexistant_field():
    """
    Issue #9 describes how if a Table has a column that has an accessor that
    targets a non-existent field, a FieldDoesNotExist error is raised.
    """
    class FaultyPersonTable(PersonTable):
        missing = tables.Column()

    table = FaultyPersonTable(Person.objects.all())
    table.as_html()  # the bug would cause this to raise FieldDoesNotExist


@models.test
def should_support_rendering_multiple_times():
    class MultiRenderTable(tables.Table):
        name = tables.Column()

    # test queryset data
    table = MultiRenderTable(Person.objects.all())
    assert table.as_html() == table.as_html()


@models.test
def ordering():
    class SimpleTable(tables.Table):
        name = tables.Column(order_by=("first_name", "last_name"))

    table = SimpleTable(Person.objects.all(), order_by="name")
    assert table.as_html()


@models.test
def fields_should_implicitly_set_sequence():
    class PersonTable(tables.Table):
        extra = tables.Column()

        class Meta:
            model = Person
            fields = ('last_name', 'first_name')
    table = PersonTable(Person.objects.all())
    assert table.columns.names() == ['last_name', 'first_name', 'extra']


@models.test
def model_properties_should_be_useable_for_columns():
    class PersonTable(tables.Table):
        class Meta:
            model = Person
            fields = ('name', 'first_name')

    Person.objects.create(first_name='Bradley', last_name='Ayers')
    table = PersonTable(Person.objects.all())
    assert list(table.rows[0]) == ['Bradley Ayers', 'Bradley']


@models.test
def column_with_delete_accessor_shouldnt_delete_records():
    class PersonTable(tables.Table):
        delete = tables.Column()

    Person.objects.create(first_name='Bradley', last_name='Ayers')
    table = PersonTable(Person.objects.all())
    table.as_html()
    assert Person.objects.get(first_name='Bradley')


@models.test
def order_by_derived_from_queryset():
    queryset = Person.objects.order_by("first_name", "last_name", "-occupation__name")

    class PersonTable(tables.Table):
        name = tables.Column(order_by=("first_name", "last_name"))
        occupation = tables.Column(order_by=("occupation__name",))

    assert PersonTable(queryset.order_by("first_name", "last_name", "-occupation__name")).order_by == ("name", "-occupation")

    class PersonTable(PersonTable):
        class Meta:
            order_by = ("occupation", )

    assert PersonTable(queryset.all()).order_by == ("occupation", )


@models.test
def queryset_table_data_supports_ordering():
    class Table(tables.Table):
        class Meta:
            model = Person

    for name in ("Bradley Ayers", "Stevie Armstrong"):
        first_name, last_name = name.split()
        Person.objects.create(first_name=first_name, last_name=last_name)

    table = Table(Person.objects.all())
    assert table.rows[0]["first_name"] == "Bradley"
    table.order_by = "-first_name"
    assert table.rows[0]["first_name"] == "Stevie"


@models.test
def doesnotexist_from_accessor_should_use_default():
    class Table(tables.Table):
        class Meta:
            model = Person
            default = "abc"
            fields = ("first_name", "last_name", "region")

    Person.objects.create(first_name="Brad", last_name="Ayers")

    table = Table(Person.objects.all())
    assert table.rows[0]["first_name"] == "Brad"
    assert table.rows[0]["region"] == "abc"


@models.test
def unicode_field_names():
    class Table(tables.Table):
        class Meta:
            model = Person
            fields = (six.text_type("first_name"),)

    Person.objects.create(first_name="Brad")

    table = Table(Person.objects.all())
    assert table.rows[0]["first_name"] == "Brad"

########NEW FILE########
__FILENAME__ = rows
# coding: utf-8
from attest import assert_hook, raises, Tests
import django_tables2 as tables


rows = Tests()


@rows.test
def bound_rows():
    class SimpleTable(tables.Table):
        name = tables.Column()

    data = [
        {'name': 'Bradley'},
        {'name': 'Chris'},
        {'name': 'Peter'},
    ]

    table = SimpleTable(data)

    # iteration
    records = []
    for row in table.rows:
        records.append(row.record)
    assert records == data


@rows.test
def bound_row():
    class SimpleTable(tables.Table):
        name = tables.Column()
        occupation = tables.Column()
        age = tables.Column()

    record = {'name': 'Bradley', 'age': 20, 'occupation': 'programmer'}

    table = SimpleTable([record])
    row = table.rows[0]

    # integer indexing into a row
    assert row[0] == record['name']
    assert row[1] == record['occupation']
    assert row[2] == record['age']

    with raises(IndexError):
        row[3]

    # column name indexing into a row
    assert row['name']       == record['name']
    assert row['occupation'] == record['occupation']
    assert row['age']        == record['age']

    with raises(KeyError):
        row['gamma']

########NEW FILE########
__FILENAME__ = templates
# coding: utf-8
from __future__ import unicode_literals
from .app.models import Person, Region
from attest import assert_hook, raises, Tests  # pylint: disable=W0611
from contextlib import contextmanager
from django_attest import queries, settings, TestContext, translation
import django_tables2 as tables
from django_tables2.config import RequestConfig
from django_tables2.utils import build_request
import django
from django.core.exceptions import ImproperlyConfigured
from django.template import Template, RequestContext, Context
from django.utils.translation import ugettext_lazy
from django.utils.safestring import mark_safe
try:
    from urlparse import parse_qs
except ImportError:
    from urllib.parse import parse_qs
import lxml.etree
import lxml.html
import six


def parse(html):
    return lxml.etree.fromstring(html)


def attrs(xml):
    """
    Helper function that returns a dict of XML attributes, given an element.
    """
    return lxml.html.fromstring(xml).attrib


database = contextmanager(TestContext())
templates = Tests()


class CountryTable(tables.Table):
    name = tables.Column()
    capital = tables.Column(orderable=False,
                            verbose_name=ugettext_lazy("Capital"))
    population = tables.Column(verbose_name='Population Size')
    currency = tables.Column(visible=False)
    tld = tables.Column(visible=False, verbose_name='Domain')
    calling_code = tables.Column(accessor='cc',
                                 verbose_name='Phone Ext.')


MEMORY_DATA = [
    {'name': 'Germany', 'capital': 'Berlin', 'population': 83,
     'currency': 'Euro (€)', 'tld': 'de', 'cc': 49},
    {'name': 'France', 'population': 64, 'currency': 'Euro (€)',
     'tld': 'fr', 'cc': 33},
    {'name': 'Netherlands', 'capital': 'Amsterdam', 'cc': '31'},
    {'name': 'Austria', 'cc': 43, 'currency': 'Euro (€)',
     'population': 8}
]


@templates.test
def as_html():
    table = CountryTable(MEMORY_DATA)
    root = parse(table.as_html())
    assert len(root.findall('.//thead/tr')) == 1
    assert len(root.findall('.//thead/tr/th')) == 4
    assert len(root.findall('.//tbody/tr')) == 4
    assert len(root.findall('.//tbody/tr/td')) == 16

    # no data with no empty_text
    table = CountryTable([])
    root = parse(table.as_html())
    assert 1 == len(root.findall('.//thead/tr'))
    assert 4 == len(root.findall('.//thead/tr/th'))
    assert 0 == len(root.findall('.//tbody/tr'))

    # no data WITH empty_text
    table = CountryTable([], empty_text='this table is empty')
    root = parse(table.as_html())
    assert 1 == len(root.findall('.//thead/tr'))
    assert 4 == len(root.findall('.//thead/tr/th'))
    assert 1 == len(root.findall('.//tbody/tr'))
    assert 1 == len(root.findall('.//tbody/tr/td'))
    assert int(root.find('.//tbody/tr/td').attrib['colspan']) == len(root.findall('.//thead/tr/th'))
    assert root.find('.//tbody/tr/td').text == 'this table is empty'

    # with custom template
    table = CountryTable([], template="django_tables2/table.html")
    table.as_html()


@templates.test
def custom_rendering():
    """For good measure, render some actual templates."""
    countries = CountryTable(MEMORY_DATA)
    context = Context({'countries': countries})

    # automatic and manual column verbose names
    template = Template('{% for column in countries.columns %}{{ column }}/'
                        '{{ column.name }} {% endfor %}')
    result = ('Name/name Capital/capital Population Size/population '
              'Phone Ext./calling_code ')
    assert result == template.render(context)

    # row values
    template = Template('{% for row in countries.rows %}{% for value in row %}'
                        '{{ value }} {% endfor %}{% endfor %}')
    result = ('Germany Berlin 83 49 France — 64 33 Netherlands Amsterdam '
              '— 31 Austria — 8 43 ')
    assert result == template.render(context)


@templates.test
def render_table_templatetag():
    # ensure it works with a multi-order-by
    request = build_request('/')
    table = CountryTable(MEMORY_DATA, order_by=('name', 'population'))
    RequestConfig(request).configure(table)
    template = Template('{% load django_tables2 %}{% render_table table %}')
    html = template.render(Context({'request': request, 'table': table}))

    root = parse(html)
    assert len(root.findall('.//thead/tr')) == 1
    assert len(root.findall('.//thead/tr/th')) == 4
    assert len(root.findall('.//tbody/tr')) == 4
    assert len(root.findall('.//tbody/tr/td')) == 16
    assert root.find('ul[@class="pagination"]/li[@class="cardinality"]').text == '4 items'

    # no data with no empty_text
    table = CountryTable([])
    template = Template('{% load django_tables2 %}{% render_table table %}')
    html = template.render(Context({'request': build_request('/'), 'table': table}))
    root = parse(html)
    assert len(root.findall('.//thead/tr')) == 1
    assert len(root.findall('.//thead/tr/th')) == 4
    assert len(root.findall('.//tbody/tr')) == 0

    # no data WITH empty_text
    request = build_request('/')
    table = CountryTable([], empty_text='this table is empty')
    RequestConfig(request).configure(table)
    template = Template('{% load django_tables2 %}{% render_table table %}')
    html = template.render(Context({'request': request, 'table': table}))
    root = parse(html)
    assert len(root.findall('.//thead/tr')) == 1
    assert len(root.findall('.//thead/tr/th')) == 4
    assert len(root.findall('.//tbody/tr')) == 1
    assert len(root.findall('.//tbody/tr/td')) == 1
    assert int(root.find('.//tbody/tr/td').attrib['colspan']) == len(root.findall('.//thead/tr/th'))
    assert root.find('.//tbody/tr/td').text == 'this table is empty'

    # variable that doesn't exist (issue #8)
    template = Template('{% load django_tables2 %}'
                        '{% render_table this_doesnt_exist %}')
    with raises(ValueError):
        with settings(DEBUG=True):
            template.render(Context())

    # Should still be noisy with debug off
    with raises(ValueError):
        with settings(DEBUG=False):
            template.render(Context())


@templates.test
def render_table_should_support_template_argument():
    table = CountryTable(MEMORY_DATA, order_by=('name', 'population'))
    template = Template('{% load django_tables2 %}'
                        '{% render_table table "dummy.html" %}')
    request = build_request('/')
    context = RequestContext(request, {'table': table})
    assert template.render(context) == 'dummy template contents\n'


@templates.test
def render_table_supports_queryset():
    with database():
        for name in ("Mackay", "Brisbane", "Maryborough"):
            Region.objects.create(name=name)
        template = Template('{% load django_tables2 %}{% render_table qs %}')
        html = template.render(Context({'qs': Region.objects.all(),
                                        'request': build_request('/')}))

        root = parse(html)
        assert [e.text for e in root.findall('.//thead/tr/th/a')] == ["ID", "name", "mayor"]
        td = [[td.text for td in tr.findall('td')] for tr in root.findall('.//tbody/tr')]
        db = []
        for region in Region.objects.all():
            db.append([six.text_type(region.id), region.name, "—"])
        assert td == db


@templates.test
def querystring_templatetag():
    template = Template('{% load django_tables2 %}'
                        '<b>{% querystring "name"="Brad" foo.bar=value %}</b>')

    # Should be something like: <root>?name=Brad&amp;a=b&amp;c=5&amp;age=21</root>
    xml = template.render(Context({
        "request": build_request('/?a=b&name=dog&c=5'),
        "foo": {"bar": "age"},
        "value": 21,
    }))

    # Ensure it's valid XML, retrieve the URL
    url = parse(xml).text

    qs = parse_qs(url[1:])  # everything after the ? pylint: disable=C0103
    assert qs["name"] == ["Brad"]
    assert qs["age"] == ["21"]
    assert qs["a"] == ["b"]
    assert qs["c"] == ["5"]


@templates.test
def querystring_templatetag_requires_request():
    with raises(ImproperlyConfigured):
        (Template('{% load django_tables2 %}{% querystring "name"="Brad" %}')
         .render(Context()))


@templates.test
def querystring_templatetag_supports_without():
    context = Context({
        "request": build_request('/?a=b&name=dog&c=5'),
        "a_var": "a",
    })

    template = Template('{% load django_tables2 %}'
                        '<b>{% querystring "name"="Brad" without a_var %}</b>')
    url = parse(template.render(context)).text
    qs = parse_qs(url[1:])  # trim the ? pylint: disable=C0103
    assert set(qs.keys()) == set(["name", "c"])

    # Try with only exclusions
    template = Template('{% load django_tables2 %}'
                        '<b>{% querystring without "a" "name" %}</b>')
    url = parse(template.render(context)).text
    qs = parse_qs(url[1:])  # trim the ? pylint: disable=C0103
    assert set(qs.keys()) == set(["c"])


@templates.test
def title_should_only_apply_to_words_without_uppercase_letters():
    expectations = {
        "a brown fox": "A Brown Fox",
        "a brown foX": "A Brown foX",
        "black FBI": "Black FBI",
        "f.b.i": "F.B.I",
        "start 6pm": "Start 6pm",
    }

    for raw, expected in expectations.items():
        template = Template("{% load django_tables2 %}{{ x|title }}")
        assert template.render(Context({"x": raw})) == expected


@templates.test
def nospaceless_works():
    template = Template("{% load django_tables2 %}"
                        "{% spaceless %}<b>a</b> <i>b {% nospaceless %}<b>c</b>  <b>d</b> {% endnospaceless %}lic</i>{% endspaceless %}")
    assert template.render(Context()) == "<b>a</b><i>b <b>c</b>&#32;<b>d</b> lic</i>"


@templates.test
def whitespace_is_preserved():
    class TestTable(tables.Table):
        name = tables.Column(verbose_name=mark_safe("<b>foo</b> <i>bar</i>"))

    html = TestTable([{"name": mark_safe("<b>foo</b> <i>bar</i>")}]).as_html()

    tree = parse(html)

    assert "<b>foo</b> <i>bar</i>" in lxml.etree.tostring(tree.findall('.//thead/tr/th')[0], encoding='unicode')
    assert "<b>foo</b> <i>bar</i>" in lxml.etree.tostring(tree.findall('.//tbody/tr/td')[0], encoding='unicode')


@templates.test
def as_html_db_queries():
    with database():
        class PersonTable(tables.Table):
            class Meta:
                model = Person

        with queries(count=1):
            PersonTable(Person.objects.all()).as_html()


@templates.test
def render_table_db_queries():
    with database():
        Person.objects.create(first_name="brad", last_name="ayers")
        Person.objects.create(first_name="stevie", last_name="armstrong")

        class PersonTable(tables.Table):
            class Meta:
                model = Person
                per_page = 1

        with queries(count=2):
            # one query for pagination: .count()
            # one query for page records: .all()[start:end]
            request = build_request('/')
            table = PersonTable(Person.objects.all())
            RequestConfig(request).configure(table)
            # render
            (Template('{% load django_tables2 %}{% render_table table %}')
             .render(Context({'table': table, 'request': request})))


@templates.test_if(django.VERSION >= (1, 3))
def localization_check():
    def get_cond_localized_table(localizeit=None):
        '''
        helper function for defining Table class conditionally
        '''
        class TestTable(tables.Table):
            name = tables.Column(verbose_name="my column", localize=localizeit)
        return TestTable

    simple_test_data = [{'name': 1234.5}]
    expected_reults = {
        None: '1234.5',
        False: '1234.5',
        True:  '1 234,5'  # non-breaking space
    }

    # no localization
    html = get_cond_localized_table(None)(simple_test_data).as_html()
    assert '<td class="name">{0}</td>'.format(expected_reults[None]) in html

    # unlocalize
    html = get_cond_localized_table(False)(simple_test_data).as_html()
    assert '<td class="name">{0}</td>'.format(expected_reults[False]) in html

    with settings(USE_L10N=True, USE_THOUSAND_SEPARATOR=True):
        with translation("pl"):
            # with default polish locales and enabled thousand separator
            # 1234.5 is formatted as "1 234,5" with nbsp
            html = get_cond_localized_table(True)(simple_test_data).as_html()
            assert '<td class="name">{0}</td>'.format(expected_reults[True]) in html

            # with localize = False there should be no formatting
            html = get_cond_localized_table(False)(simple_test_data).as_html()
            assert '<td class="name">{0}</td>'.format(expected_reults[False]) in html

            # with localize = None and USE_L10N = True
            # there should be the same formatting as with localize = True
            html = get_cond_localized_table(None)(simple_test_data).as_html()
            assert '<td class="name">{0}</td>'.format(expected_reults[True]) in html


@templates.test_if(django.VERSION >= (1, 3))
def localization_check_in_meta():
    class TableNoLocalize(tables.Table):
        name = tables.Column(verbose_name="my column")

        class Meta:
            default = "---"

    class TableLocalize(tables.Table):
        name = tables.Column(verbose_name="my column")

        class Meta:
            default = "---"
            localize = ('name',)

    class TableUnlocalize(tables.Table):
        name = tables.Column(verbose_name="my column")

        class Meta:
            default = "---"
            unlocalize = ('name',)

    class TableLocalizePrecedence(tables.Table):
        name = tables.Column(verbose_name="my column")

        class Meta:
            default = "---"
            unlocalize = ('name',)
            localize = ('name',)

    simple_test_data = [{'name': 1234.5}]
    expected_reults = {
        None: '1234.5',
        False: '1234.5',
        True:  '1{0}234,5'.format(' ')  # non-breaking space
    }

    # No localize
    html = TableNoLocalize(simple_test_data).as_html()
    assert '<td class="name">{0}</td>'.format(expected_reults[None]) in html

    with settings(USE_L10N=True, USE_THOUSAND_SEPARATOR=True):
        with translation("pl"):
            # the same as in localization_check.
            # with localization and polish locale we get formatted output
            html = TableNoLocalize(simple_test_data).as_html()
            assert '<td class="name">{0}</td>'.format(expected_reults[True]) in html

            # localize
            html = TableLocalize(simple_test_data).as_html()
            assert '<td class="name">{0}</td>'.format(expected_reults[True]) in html

            # unlocalize
            html = TableUnlocalize(simple_test_data).as_html()
            assert '<td class="name">{0}</td>'.format(expected_reults[False]) in html

            # test unlocalize higher precedence
            html = TableLocalizePrecedence(simple_test_data).as_html()
            assert '<td class="name">{0}</td>'.format(expected_reults[False]) in html

########NEW FILE########
__FILENAME__ = utils
# coding: utf-8
from attest import assert_hook, raises, Tests
from django_tables2.utils import (Accessor, AttributeDict, computed_values,
                                  OrderByTuple, OrderBy, segment)
import itertools
import six


utils = Tests()


@utils.test
def orderbytuple():
    obt = OrderByTuple(('a', 'b', 'c'))
    assert obt == (OrderBy('a'), OrderBy('b'), OrderBy('c'))

    # indexing
    assert obt[0] == OrderBy('a')
    assert obt['b'] == OrderBy('b')
    with raises(KeyError):
        obt['d']
    with raises(TypeError):
        obt[('tuple', )]

    # .get
    sentinel = object()
    assert obt.get('b', sentinel) is obt['b']  # keying
    assert obt.get('-', sentinel) is sentinel
    assert obt.get(0,   sentinel) is obt['a']  # indexing
    assert obt.get(3,   sentinel) is sentinel

    # .opposite
    assert OrderByTuple(('a', '-b', 'c')).opposite == ('-a', 'b', '-c')

    # in
    assert 'a' in obt and '-a' in obt


@utils.test
def orderbytuple_sort_key_multiple():
    obt = OrderByTuple(('a', '-b'))
    items = [
        {"a": 1, "b": 2},
        {"a": 1, "b": 3},
    ]
    assert sorted(items, key=obt.key) == [
        {"a": 1, "b": 3},
        {"a": 1, "b": 2},
    ]


@utils.test
def orderbytuple_sort_key_empty_comes_first():
    obt = OrderByTuple(('a'))
    items = [
        {"a": 1},
        {"a": ""},
        {"a": 2},
    ]
    if six.PY3:
        assert sorted(items, key=obt.key) == [
            {"a": ""},
            {"a": 1},
            {"a": 2},
        ]
    else:
        assert sorted(items, key=obt.key) == [
            {"a": 1},
            {"a": 2},
            {"a": ""},
        ]

@utils.test
def orderby():
    a = OrderBy('a')
    assert 'a' == a
    assert 'a' == a.bare
    assert '-a' == a.opposite
    assert True == a.is_ascending
    assert False == a.is_descending

    b = OrderBy('-b')
    assert '-b' == b
    assert 'b' == b.bare
    assert 'b' == b.opposite
    assert True == b.is_descending
    assert False == b.is_ascending


@utils.test
def accessor():
    x = Accessor('0')
    assert 'B' == x.resolve('Brad')

    x = Accessor('1')
    assert 'r' == x.resolve('Brad')

    x = Accessor('2.upper')
    assert 'A' == x.resolve('Brad')

    x = Accessor('2.upper.__len__')
    assert 1 == x.resolve('Brad')

    x = Accessor('')
    assert 'Brad' == x.resolve('Brad')


@utils.test
def accessor_wont_honors_alters_data():
    class Foo(object):
        deleted = False

        def delete(self):
            self.deleted = True
        delete.alters_data = True

    foo = Foo()
    with raises(ValueError):
        Accessor('delete').resolve(foo)
    assert foo.deleted is False


@utils.test
def accessor_can_be_quiet():
    foo = {}
    assert Accessor("bar").resolve(foo, quiet=True) is None


@utils.test
def attribute_dict_handles_escaping():
    x = AttributeDict({"x": '"\'x&'})
    assert x.as_html() == 'x="&quot;&#39;x&amp;"'


@utils.test
def compute_values_supports_shallow_structures():
    x = computed_values({"foo": lambda: "bar"})
    assert x == {"foo": "bar"}


@utils.test
def compute_values_supports_shallow_structures():
    x = computed_values({"foo": lambda: {"bar": lambda: "baz"}})
    assert x == {"foo": {"bar": "baz"}}


@utils.test
def segment_should_return_all_candidates():
    assert set(segment(("a", "-b", "c"), {
        "x": ("a"),
        "y": ("b", "-c"),
        "-z": ("b", "-c"),
    })) == set((
        ("x", "-y"),
        ("x", "z"),
    ))

########NEW FILE########
__FILENAME__ = views
# coding: utf-8
from .app.models import Region
from attest import assert_hook, Tests
from django_attest import TestContext
import django_tables2 as tables
from django_tables2.utils import build_request


views = Tests()
views.context(TestContext())
USING_CBV = hasattr(tables, "SingleTableView")


class DispatchHookMixin(object):
    """
    Returns a response *and* reference to the view.
    """
    def dispatch(self, *args, **kwargs):
        return super(DispatchHookMixin, self).dispatch(*args, **kwargs), self


class SimpleTable(tables.Table):
    class Meta:
        model = Region


@views.test_if(USING_CBV)
def view_should_support_pagination_options():
    for name in ("Queensland", "New South Wales", "Victoria", "Tasmania"):
        Region.objects.create(name=name)

    class SimpleView(DispatchHookMixin, tables.SingleTableView):
        table_class = SimpleTable
        table_pagination = {"per_page": 1}
        model = Region  # needed for ListView

    request = build_request('/')
    response, view = SimpleView.as_view()(request)
    assert view.get_table().paginator.num_pages == 4


@views.test_if(USING_CBV)
def should_support_explicit_table_data():
    class SimpleView(DispatchHookMixin, tables.SingleTableView):
        table_class = SimpleTable
        table_data = [
            {"name": "Queensland"},
            {"name": "New South Wales"},
            {"name": "Victoria"},
        ]
        table_pagination = {"per_page": 1}
        model = Region  # needed for ListView

    request = build_request('/')
    response, view = SimpleView.as_view()(request)
    assert view.get_table().paginator.num_pages == 3

########NEW FILE########
