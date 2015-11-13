__FILENAME__ = conf
"""Django Endless Pagination documentation build configuration file."""

from __future__ import unicode_literals


AUTHOR = 'Francesco Banconi'
APP = 'Django Endless Pagination'
TITLE = APP + ' Documentation'
VERSION = '2.0'


# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = APP
copyright = '2009-2013, ' + AUTHOR

# The short X.Y version.
version = release = VERSION

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Output file base name for HTML help builder.
htmlhelp_basename = 'DjangoEndlessPaginationdoc'

# Grouping the document tree into LaTeX files. List of tuples (source start
# file, target name, title, author, documentclass [howto/manual]).
latex_documents = [(
    'index', 'DjangoEndlessPagination.tex', TITLE, AUTHOR, 'manual')]

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [('index', 'djangoendlesspagination', TITLE, [AUTHOR], 1)]

########NEW FILE########
__FILENAME__ = decorators
"""View decorators for Ajax powered pagination."""

from __future__ import unicode_literals
from functools import wraps

from endless_pagination.settings import (
    PAGE_LABEL,
    TEMPLATE_VARNAME,
)


def page_template(template, key=PAGE_LABEL):
    """Return a view dynamically switching template if the request is Ajax.

    Decorate a view that takes a *template* and *extra_context* keyword
    arguments (like generic views).
    The template is switched to *page_template* if request is ajax and
    if *querystring_key* variable passed by the request equals to *key*.
    This allows multiple Ajax paginations in the same page.
    The name of the page template is given as *page_template* in the
    extra context.
    """
    def decorator(view):
        @wraps(view)
        def decorated(request, *args, **kwargs):
            # Trust the developer: he wrote ``context.update(extra_context)``
            # in his view.
            extra_context = kwargs.setdefault('extra_context', {})
            extra_context['page_template'] = template
            # Switch the template when the request is Ajax.
            querystring_key = request.REQUEST.get(
                'querystring_key', PAGE_LABEL)
            if request.is_ajax() and querystring_key == key:
                kwargs[TEMPLATE_VARNAME] = template
            return view(request, *args, **kwargs)
        return decorated

    return decorator


def _get_template(querystring_key, mapping):
    """Return the template corresponding to the given ``querystring_key``."""
    default = None
    try:
        template_and_keys = mapping.items()
    except AttributeError:
        template_and_keys = mapping
    for template, key in template_and_keys:
        if key is None:
            key = PAGE_LABEL
            default = template
        if key == querystring_key:
            return template
    return default


def page_templates(mapping):
    """Like the *page_template* decorator but manage multiple paginations.

    You can map multiple templates to *querystring_keys* using the *mapping*
    dict, e.g.::

        @page_templates({
            'page_contents1.html': None,
            'page_contents2.html': 'go_to_page',
        })
        def myview(request):
            ...

    When the value of the dict is None then the default *querystring_key*
    (defined in settings) is used. You can use this decorator instead of
    chaining multiple *page_template* calls.
    """
    def decorator(view):
        @wraps(view)
        def decorated(request, *args, **kwargs):
            # Trust the developer: he wrote ``context.update(extra_context)``
            # in his view.
            extra_context = kwargs.setdefault('extra_context', {})
            querystring_key = request.REQUEST.get(
                'querystring_key', PAGE_LABEL)
            template = _get_template(querystring_key, mapping)
            extra_context['page_template'] = template
            # Switch the template when the request is Ajax.
            if request.is_ajax() and template:
                kwargs[TEMPLATE_VARNAME] = template
            return view(request, *args, **kwargs)
        return decorated

    return decorator

########NEW FILE########
__FILENAME__ = exceptions
"""Pagination exceptions."""

from __future__ import unicode_literals


class PaginationError(Exception):
    """Error in the pagination process."""

########NEW FILE########
__FILENAME__ = loaders
"""Django Endless Pagination object loaders."""

from __future__ import unicode_literals

from django.core.exceptions import ImproperlyConfigured
from django.utils.importlib import import_module


def load_object(path):
    """Return the Python object represented by dotted *path*."""
    i = path.rfind('.')
    module_name, object_name = path[:i], path[i + 1:]
    # Load module.
    try:
        module = import_module(module_name)
    except ImportError:
        raise ImproperlyConfigured('Module %r not found' % module_name)
    except ValueError:
        raise ImproperlyConfigured('Invalid module %r' % module_name)
    # Load object.
    try:
        return getattr(module, object_name)
    except AttributeError:
        msg = 'Module %r does not define an object named %r'
        raise ImproperlyConfigured(msg % (module_name, object_name))

########NEW FILE########
__FILENAME__ = models
"""Ephemeral models used to represent a page and a list of pages."""

from __future__ import unicode_literals

from django.template import (
    loader,
    RequestContext,
)
from django.utils.encoding import iri_to_uri

from endless_pagination import (
    loaders,
    settings,
    utils,
)


# Page templates cache.
_template_cache = {}


class EndlessPage(utils.UnicodeMixin):
    """A page link representation.

    Interesting attributes:

        - *self.number*: the page number;
        - *self.label*: the label of the link
          (usually the page number as string);
        - *self.url*: the url of the page (strting with "?");
        - *self.path*: the path of the page;
        - *self.is_current*: return True if page is the current page displayed;
        - *self.is_first*: return True if page is the first page;
        - *self.is_last*:  return True if page is the last page.
    """

    def __init__(
            self, request, number, current_number, total_number,
            querystring_key, label=None, default_number=1, override_path=None):
        self._request = request
        self.number = number
        self.label = utils.text(number) if label is None else label
        self.querystring_key = querystring_key

        self.is_current = number == current_number
        self.is_first = number == 1
        self.is_last = number == total_number

        self.url = utils.get_querystring_for_page(
            request, number, self.querystring_key,
            default_number=default_number)
        path = iri_to_uri(override_path or request.path)
        self.path = '{0}{1}'.format(path, self.url)

    def __unicode__(self):
        """Render the page as a link."""
        context = {
            'add_nofollow': settings.ADD_NOFOLLOW,
            'page': self,
            'querystring_key': self.querystring_key,
        }
        if self.is_current:
            template_name = 'endless/current_link.html'
        else:
            template_name = 'endless/page_link.html'
        template = _template_cache.setdefault(
            template_name, loader.get_template(template_name))
        return template.render(RequestContext(self._request, context))


class PageList(utils.UnicodeMixin):
    """A sequence of endless pages."""

    def __init__(
            self, request, page, querystring_key,
            default_number=None, override_path=None):
        self._request = request
        self._page = page
        if default_number is None:
            self._default_number = 1
        else:
            self._default_number = int(default_number)
        self._querystring_key = querystring_key
        self._override_path = override_path

    def _endless_page(self, number, label=None):
        """Factory function that returns a *EndlessPage* instance.

        This method works just like a partial constructor.
        """
        return EndlessPage(
            self._request,
            number,
            self._page.number,
            len(self),
            self._querystring_key,
            label=label,
            default_number=self._default_number,
            override_path=self._override_path,
        )

    def __getitem__(self, value):
        # The type conversion is required here because in templates Django
        # performs a dictionary lookup before the attribute lokups
        # (when a dot is encountered).
        try:
            value = int(value)
        except (TypeError, ValueError):
            # A TypeError says to django to continue with an attribute lookup.
            raise TypeError
        if 1 <= value <= len(self):
            return self._endless_page(value)
        raise IndexError('page list index out of range')

    def __len__(self):
        """The length of the sequence is the total number of pages."""
        return self._page.paginator.num_pages

    def __iter__(self):
        """Iterate over all the endless pages (from first to last)."""
        for i in range(len(self)):
            yield self[i + 1]

    def __unicode__(self):
        """Return a rendered Digg-style pagination (by default).

        The callable *settings.PAGE_LIST_CALLABLE* can be used to customize
        how the pages are displayed. The callable takes the current page number
        and the total number of pages, and must return a sequence of page
        numbers that will be displayed. The sequence can contain other values:

            - *'previous'*: will display the previous page in that position;
            - *'next'*: will display the next page in that position;
            - *'first'*: will display the first page as an arrow;
            - *'last'*: will display the last page as an arrow;
            - *None*: a separator will be displayed in that position.

        Here is an example of custom calable that displays the previous page,
        then the first page, then a separator, then the current page, and
        finally the last page::

            def get_page_numbers(current_page, num_pages):
                return ('previous', 1, None, current_page, 'last')

        If *settings.PAGE_LIST_CALLABLE* is None an internal callable is used,
        generating a Digg-style pagination. The value of
        *settings.PAGE_LIST_CALLABLE* can also be a dotted path to a callable.
        """
        if len(self) > 1:
            callable_or_path = settings.PAGE_LIST_CALLABLE
            if callable_or_path:
                if callable(callable_or_path):
                    pages_callable = callable_or_path
                else:
                    pages_callable = loaders.load_object(callable_or_path)
            else:
                pages_callable = utils.get_page_numbers
            pages = []
            for item in pages_callable(self._page.number, len(self)):
                if item is None:
                    pages.append(None)
                elif item == 'previous':
                    pages.append(self.previous())
                elif item == 'next':
                    pages.append(self.next())
                elif item == 'first':
                    pages.append(self.first_as_arrow())
                elif item == 'last':
                    pages.append(self.last_as_arrow())
                else:
                    pages.append(self[item])
            context = RequestContext(self._request, {'pages': pages})
            return loader.render_to_string('endless/show_pages.html', context)
        return ''

    def current(self):
        """Return the current page."""
        return self._endless_page(self._page.number)

    def current_start_index(self):
        """Return the 1-based index of the first item on the current page."""
        return self._page.start_index()

    def current_end_index(self):
        """Return the 1-based index of the last item on the current page."""
        return self._page.end_index()

    def total_count(self):
        """Return the total number of objects, across all pages."""
        return self._page.paginator.count

    def first(self, label=None):
        """Return the first page."""
        return self._endless_page(1, label=label)

    def last(self, label=None):
        """Return the last page."""
        return self._endless_page(len(self), label=label)

    def first_as_arrow(self):
        """Return the first page as an arrow.

        The page label (arrow) is defined in ``settings.FIRST_LABEL``.
        """
        return self.first(label=settings.FIRST_LABEL)

    def last_as_arrow(self):
        """Return the last page as an arrow.

        The page label (arrow) is defined in ``settings.LAST_LABEL``.
        """
        return self.last(label=settings.LAST_LABEL)

    def previous(self):
        """Return the previous page.

        The page label is defined in ``settings.PREVIOUS_LABEL``.
        Return an empty string if current page is the first.
        """
        if self._page.has_previous():
            return self._endless_page(
                self._page.previous_page_number(),
                label=settings.PREVIOUS_LABEL)
        return ''

    def next(self):
        """Return the next page.

        The page label is defined in ``settings.NEXT_LABEL``.
        Return an empty string if current page is the last.
        """
        if self._page.has_next():
            return self._endless_page(
                self._page.next_page_number(),
                label=settings.NEXT_LABEL)
        return ''

    def paginated(self):
        """Return True if this page list contains more than one page."""
        return len(self) > 1

########NEW FILE########
__FILENAME__ = paginators
"""Customized Django paginators."""

from __future__ import unicode_literals
from math import ceil

from django.core.paginator import (
    EmptyPage,
    Page,
    PageNotAnInteger,
    Paginator,
)


class CustomPage(Page):
    """Handle different number of items on the first page."""

    def start_index(self):
        """Return the 1-based index of the first item on this page."""
        paginator = self.paginator
        # Special case, return zero if no items.
        if paginator.count == 0:
            return 0
        elif self.number == 1:
            return 1
        return (
            (self.number - 2) * paginator.per_page + paginator.first_page + 1)

    def end_index(self):
        """Return the 1-based index of the last item on this page."""
        paginator = self.paginator
        # Special case for the last page because there can be orphans.
        if self.number == paginator.num_pages:
            return paginator.count
        return (self.number - 1) * paginator.per_page + paginator.first_page


class BasePaginator(Paginator):
    """A base paginator class subclassed by the other real paginators.

    Handle different number of items on the first page.
    """

    def __init__(self, object_list, per_page, **kwargs):
        if 'first_page' in kwargs:
            self.first_page = kwargs.pop('first_page')
        else:
            self.first_page = per_page
        super(BasePaginator, self).__init__(object_list, per_page, **kwargs)

    def get_current_per_page(self, number):
        return self.first_page if number == 1 else self.per_page


class DefaultPaginator(BasePaginator):
    """The default paginator used by this application."""

    def page(self, number):
        number = self.validate_number(number)
        if number == 1:
            bottom = 0
        else:
            bottom = ((number - 2) * self.per_page + self.first_page)
        top = bottom + self.get_current_per_page(number)
        if top + self.orphans >= self.count:
            top = self.count
        return CustomPage(self.object_list[bottom:top], number, self)

    def _get_num_pages(self):
        if self._num_pages is None:
            if self.count == 0 and not self.allow_empty_first_page:
                self._num_pages = 0
            else:
                hits = max(0, self.count - self.orphans - self.first_page)
                self._num_pages = int(ceil(hits / float(self.per_page))) + 1
        return self._num_pages
    num_pages = property(_get_num_pages)


class LazyPaginator(BasePaginator):
    """Implement lazy pagination."""

    def validate_number(self, number):
        try:
            number = int(number)
        except ValueError:
            raise PageNotAnInteger('That page number is not an integer')
        if number < 1:
            raise EmptyPage('That page number is less than 1')
        return number

    def page(self, number):
        number = self.validate_number(number)
        current_per_page = self.get_current_per_page(number)
        if number == 1:
            bottom = 0
        else:
            bottom = ((number - 2) * self.per_page + self.first_page)
        top = bottom + current_per_page
        # Retrieve more objects to check if there is a next page.
        objects = list(self.object_list[bottom:top + self.orphans + 1])
        objects_count = len(objects)
        if objects_count > (current_per_page + self.orphans):
            # If another page is found, increase the total number of pages.
            self._num_pages = number + 1
            # In any case,  return only objects for this page.
            objects = objects[:current_per_page]
        elif (number != 1) and (objects_count <= self.orphans):
            raise EmptyPage('That page contains no results')
        else:
            # This is the last page.
            self._num_pages = number
        return CustomPage(objects, number, self)

    def _get_count(self):
        raise NotImplementedError

    count = property(_get_count)

    def _get_num_pages(self):
        return self._num_pages

    num_pages = property(_get_num_pages)

    def _get_page_range(self):
        raise NotImplementedError

    page_range = property(_get_page_range)

########NEW FILE########
__FILENAME__ = settings
# """Django Endless Pagination settings file."""

from __future__ import unicode_literals

from django.conf import settings


# How many objects are normally displayed in a page
# (overwriteable by templatetag).
PER_PAGE = getattr(settings, 'ENDLESS_PAGINATION_PER_PAGE', 10)
# The querystring key of the page number.
PAGE_LABEL = getattr(settings, 'ENDLESS_PAGINATION_PAGE_LABEL', 'page')
# See django *Paginator* definition of orphans.
ORPHANS = getattr(settings, 'ENDLESS_PAGINATION_ORPHANS', 0)

# If you use the default *show_more* template, here you can customize
# the content of the loader hidden element.
# Html is safe here, e.g. you can show your pretty animated gif:
#    ENDLESS_PAGINATION_LOADING = """
#        <img src="/static/img/loader.gif" alt="loading" />
#    """
LOADING = getattr(
    settings, 'ENDLESS_PAGINATION_LOADING', 'loading')

# Labels for previous and next page links.
PREVIOUS_LABEL = getattr(
    settings, 'ENDLESS_PAGINATION_PREVIOUS_LABEL', '&lt;')
NEXT_LABEL = getattr(settings, 'ENDLESS_PAGINATION_NEXT_LABEL', '&gt;')

# Labels for first and last page links.
FIRST_LABEL = getattr(
    settings, 'ENDLESS_PAGINATION_FIRST_LABEL', '&lt;&lt;')
LAST_LABEL = getattr(settings, 'ENDLESS_PAGINATION_LAST_LABEL', '&gt;&gt;')

# Set to True if your SEO alchemist wants all the links in Digg-style
# pagination to be ``nofollow``.
ADD_NOFOLLOW = getattr(settings, 'ENDLESS_PAGINATION_ADD_NOFOLLOW', False)

# Callable (or dotted path to a callable) returning pages to be displayed.
# If None, a default callable is used (which produces Digg-style pagination).
PAGE_LIST_CALLABLE = getattr(
    settings, 'ENDLESS_PAGINATION_PAGE_LIST_CALLABLE', None)

# The default callable returns a sequence of pages producing Digg-style
# pagination, and depending on the settings below.
DEFAULT_CALLABLE_EXTREMES = getattr(
    settings, 'ENDLESS_PAGINATION_DEFAULT_CALLABLE_EXTREMES', 3)
DEFAULT_CALLABLE_AROUNDS = getattr(
    settings, 'ENDLESS_PAGINATION_DEFAULT_CALLABLE_AROUNDS', 2)
# Whether or not the first and last pages arrows are displayed.
DEFAULT_CALLABLE_ARROWS = getattr(
    settings, 'ENDLESS_PAGINATION_DEFAULT_CALLABLE_ARROWS', False)

# Template variable name for *page_template* decorator.
TEMPLATE_VARNAME = getattr(
    settings, 'ENDLESS_PAGINATION_TEMPLATE_VARNAME', 'template')

########NEW FILE########
__FILENAME__ = endless
"""Django Endless Pagination template tags."""

from __future__ import unicode_literals
import re

from django import template
from django.utils.encoding import iri_to_uri

from endless_pagination import (
    models,
    settings,
    utils,
)
from endless_pagination.paginators import (
    DefaultPaginator,
    EmptyPage,
    LazyPaginator,
)


PAGINATE_EXPRESSION = re.compile(r"""
    ^   # Beginning of line.
    (((?P<first_page>\w+)\,)?(?P<per_page>\w+)\s+)?  # First page, per page.
    (?P<objects>[\.\w]+)  # Objects / queryset.
    (\s+starting\s+from\s+page\s+(?P<number>[\-]?\d+|\w+))?  # Page start.
    (\s+using\s+(?P<key>[\"\'\-\w]+))?  # Querystring key.
    (\s+with\s+(?P<override_path>[\"\'\/\w]+))?  # Override path.
    (\s+as\s+(?P<var_name>\w+))?  # Context variable name.
    $   # End of line.
""", re.VERBOSE)
SHOW_CURRENT_NUMBER_EXPRESSION = re.compile(r"""
    ^   # Beginning of line.
    (starting\s+from\s+page\s+(?P<number>\w+))?\s*  # Page start.
    (using\s+(?P<key>[\"\'\-\w]+))?\s*  # Querystring key.
    (as\s+(?P<var_name>\w+))?  # Context variable name.
    $   # End of line.
""", re.VERBOSE)


register = template.Library()


@register.tag
def paginate(parser, token, paginator_class=None):
    """Paginate objects.

    Usage:

    .. code-block:: html+django

        {% paginate entries %}

    After this call, the *entries* variable in the template context is replaced
    by only the entries of the current page.

    You can also keep your *entries* original variable (usually a queryset)
    and add to the context another name that refers to entries of the current
    page, e.g.:

    .. code-block:: html+django

        {% paginate entries as page_entries %}

    The *as* argument is also useful when a nested context variable is provided
    as queryset. In this case, and only in this case, the resulting variable
    name is mandatory, e.g.:

    .. code-block:: html+django

        {% paginate entries.all as entries %}

    The number of paginated entries is taken from settings, but you can
    override the default locally, e.g.:

    .. code-block:: html+django

        {% paginate 20 entries %}

    Of course you can mix it all:

    .. code-block:: html+django

        {% paginate 20 entries as paginated_entries %}

    By default, the first page is displayed the first time you load the page,
    but you can change this, e.g.:

    .. code-block:: html+django

        {% paginate entries starting from page 3 %}

    When changing the default page, it is also possible to reference the last
    page (or the second last page, and so on) by using negative indexes, e.g:

    .. code-block:: html+django

        {% paginate entries starting from page -1 %}

    This can be also achieved using a template variable that was passed to the
    context, e.g.:

    .. code-block:: html+django

        {% paginate entries starting from page page_number %}

    If the passed page number does not exist, the first page is displayed.

    If you have multiple paginations in the same page, you can change the
    querydict key for the single pagination, e.g.:

    .. code-block:: html+django

        {% paginate entries using article_page %}

    In this case *article_page* is intended to be a context variable, but you
    can hardcode the key using quotes, e.g.:

    .. code-block:: html+django

        {% paginate entries using 'articles_at_page' %}

    Again, you can mix it all (the order of arguments is important):

    .. code-block:: html+django

        {% paginate 20 entries
            starting from page 3 using page_key as paginated_entries %}

    Additionally you can pass a path to be used for the pagination:

    .. code-block:: html+django

        {% paginate 20 entries
            using page_key with pagination_url as paginated_entries %}

    This way you can easily create views acting as API endpoints, and point
    your Ajax calls to that API. In this case *pagination_url* is considered a
    context variable, but it is also possible to hardcode the URL, e.g.:

    .. code-block:: html+django

        {% paginate 20 entries with "/mypage/" %}

    If you want the first page to contain a different number of items than
    subsequent pages, you can separate the two values with a comma, e.g. if
    you want 3 items on the first page and 10 on other pages:

    .. code-block:: html+django

    {% paginate 3,10 entries %}

    You must use this tag before calling the {% show_more %} one.
    """
    # Validate arguments.
    try:
        tag_name, tag_args = token.contents.split(None, 1)
    except ValueError:
        msg = '%r tag requires arguments' % token.contents.split()[0]
        raise template.TemplateSyntaxError(msg)

    # Use a regexp to catch args.
    match = PAGINATE_EXPRESSION.match(tag_args)
    if match is None:
        msg = 'Invalid arguments for %r tag' % tag_name
        raise template.TemplateSyntaxError(msg)

    # Retrieve objects.
    kwargs = match.groupdict()
    objects = kwargs.pop('objects')

    # The variable name must be present if a nested context variable is passed.
    if '.' in objects and kwargs['var_name'] is None:
        msg = (
            '%(tag)r tag requires a variable name `as` argumnent if the '
            'queryset is provided as a nested context variable (%(objects)s). '
            'You must either pass a direct queryset (e.g. taking advantage '
            'of the `with` template tag) or provide a new variable name to '
            'store the resulting queryset (e.g. `%(tag)s %(objects)s as '
            'objects`).'
        ) % {'tag': tag_name, 'objects': objects}
        raise template.TemplateSyntaxError(msg)

    # Call the node.
    return PaginateNode(paginator_class, objects, **kwargs)


@register.tag
def lazy_paginate(parser, token):
    """Lazy paginate objects.

    Paginate objects without hitting the database with a *select count* query.

    Use this the same way as *paginate* tag when you are not interested
    in the total number of pages.
    """
    return paginate(parser, token, paginator_class=LazyPaginator)


class PaginateNode(template.Node):
    """Add to context the objects of the current page.

    Also add the Django paginator's *page* object.
    """

    def __init__(
            self, paginator_class, objects, first_page=None, per_page=None,
            var_name=None, number=None, key=None, override_path=None):
        self.paginator = paginator_class or DefaultPaginator
        self.objects = template.Variable(objects)

        # If *var_name* is not passed, then the queryset name will be used.
        self.var_name = objects if var_name is None else var_name

        # If *per_page* is not passed then the default value form settings
        # will be used.
        self.per_page_variable = None
        if per_page is None:
            self.per_page = settings.PER_PAGE
        elif per_page.isdigit():
            self.per_page = int(per_page)
        else:
            self.per_page_variable = template.Variable(per_page)

        # Handle first page: if it is not passed then *per_page* is used.
        self.first_page_variable = None
        if first_page is None:
            self.first_page = None
        elif first_page.isdigit():
            self.first_page = int(first_page)
        else:
            self.first_page_variable = template.Variable(first_page)

        # Handle page number when it is not specified in querystring.
        self.page_number_variable = None
        if number is None:
            self.page_number = 1
        else:
            try:
                self.page_number = int(number)
            except ValueError:
                self.page_number_variable = template.Variable(number)

        # Set the querystring key attribute.
        self.querystring_key_variable = None
        if key is None:
            self.querystring_key = settings.PAGE_LABEL
        elif key[0] in ('"', "'") and key[-1] == key[0]:
            self.querystring_key = key[1:-1]
        else:
            self.querystring_key_variable = template.Variable(key)

        # Handle *override_path*.
        self.override_path_variable = None
        if override_path is None:
            self.override_path = None
        elif (
                override_path[0] in ('"', "'") and
                override_path[-1] == override_path[0]):
            self.override_path = override_path[1:-1]
        else:
            self.override_path_variable = template.Variable(override_path)

    def render(self, context):
        # Handle page number when it is not specified in querystring.
        if self.page_number_variable is None:
            default_number = self.page_number
        else:
            default_number = int(self.page_number_variable.resolve(context))

        # Calculate the number of items to show on each page.
        if self.per_page_variable is None:
            per_page = self.per_page
        else:
            per_page = int(self.per_page_variable.resolve(context))

        # Calculate the number of items to show in the first page.
        if self.first_page_variable is None:
            first_page = self.first_page or per_page
        else:
            first_page = int(self.first_page_variable.resolve(context))

        # User can override the querystring key to use in the template.
        # The default value is defined in the settings file.
        if self.querystring_key_variable is None:
            querystring_key = self.querystring_key
        else:
            querystring_key = self.querystring_key_variable.resolve(context)

        # Retrieve the override path if used.
        if self.override_path_variable is None:
            override_path = self.override_path
        else:
            override_path = self.override_path_variable.resolve(context)

        # Retrieve the queryset and create the paginator object.
        objects = self.objects.resolve(context)
        paginator = self.paginator(
            objects, per_page, first_page=first_page, orphans=settings.ORPHANS)

        # Normalize the default page number if a negative one is provided.
        if default_number < 0:
            default_number = utils.normalize_page_number(
                default_number, paginator.page_range)

        # The current request is used to get the requested page number.
        page_number = utils.get_page_number_from_request(
            context['request'], querystring_key, default=default_number)

        # Get the page.
        try:
            page = paginator.page(page_number)
        except EmptyPage:
            page = paginator.page(1)

        # Populate the context with required data.
        data = {
            'default_number': default_number,
            'override_path': override_path,
            'page': page,
            'querystring_key': querystring_key,
        }
        context.update({'endless': data, self.var_name: page.object_list})
        return ''


@register.inclusion_tag('endless/show_more.html', takes_context=True)
def show_more(context, label=None, loading=settings.LOADING):
    """Show the link to get the next page in a Twitter-like pagination.

    Usage::

        {% show_more %}

    Alternatively you can override the label passed to the default template::

        {% show_more "even more" %}

    You can override the loading text too::

        {% show_more "even more" "working" %}

    Must be called after ``{% paginate objects %}``.
    """
    # This template tag could raise a PaginationError: you have to call
    # *paginate* or *lazy_paginate* before including the showmore template.
    data = utils.get_data_from_context(context)
    page = data['page']
    # show the template only if there is a next page
    if page.has_next():
        request = context['request']
        page_number = page.next_page_number()
        # Generate the querystring.
        querystring_key = data['querystring_key']
        querystring = utils.get_querystring_for_page(
            request, page_number, querystring_key,
            default_number=data['default_number'])
        return {
            'label': label,
            'loading': loading,
            'path': iri_to_uri(data['override_path'] or request.path),
            'querystring': querystring,
            'querystring_key': querystring_key,
            'request': request,
        }
    # No next page, nothing to see.
    return {}


@register.tag
def get_pages(parser, token):
    """Add to context the list of page links.

    Usage:

    .. code-block:: html+django

        {% get_pages %}

    This is mostly used for Digg-style pagination.
    This call inserts in the template context a *pages* variable, as a sequence
    of page links. You can use *pages* in different ways:

    - just print *pages* and you will get Digg-style pagination displayed:

    .. code-block:: html+django

        {{ pages }}

    - display pages count:

    .. code-block:: html+django

        {{ pages|length }}

    - check if the page list contains more than one page:

    .. code-block:: html+django

        {{ pages.paginated }}
        {# the following is equivalent #}
        {{ pages|length > 1 }}

    - get a specific page:

    .. code-block:: html+django

        {# the current selected page #}
        {{ pages.current }}

        {# the first page #}
        {{ pages.first }}

        {# the last page #}
        {{ pages.last }}

        {# the previous page (or nothing if you are on first page) #}
        {{ pages.previous }}

        {# the next page (or nothing if you are in last page) #}
        {{ pages.next }}

        {# the third page #}
        {{ pages.3 }}
        {# this means page.1 is the same as page.first #}

        {# the 1-based index of the first item on the current page #}
        {{ pages.current_start_index }}

        {# the 1-based index of the last item on the current page #}
        {{ pages.current_end_index }}

        {# the total number of objects, across all pages #}
        {{ pages.total_count }}

        {# the first page represented as an arrow #}
        {{ pages.first_as_arrow }}

        {# the last page represented as an arrow #}
        {{ pages.last_as_arrow }}

    - iterate over *pages* to get all pages:

    .. code-block:: html+django

        {% for page in pages %}
            {# display page link #}
            {{ page }}

            {# the page url (beginning with "?") #}
            {{ page.url }}

            {# the page path #}
            {{ page.path }}

            {# the page number #}
            {{ page.number }}

            {# a string representing the page (commonly the page number) #}
            {{ page.label }}

            {# check if the page is the current one #}
            {{ page.is_current }}

            {# check if the page is the first one #}
            {{ page.is_first }}

            {# check if the page is the last one #}
            {{ page.is_last }}
        {% endfor %}

    You can change the variable name, e.g.:

    .. code-block:: html+django

        {% get_pages as page_links %}

    Must be called after ``{% paginate objects %}``.
    """
    # Validate args.
    try:
        tag_name, args = token.contents.split(None, 1)
    except ValueError:
        var_name = 'pages'
    else:
        args = args.split()
        if len(args) == 2 and args[0] == 'as':
            var_name = args[1]
        else:
            msg = 'Invalid arguments for %r tag' % tag_name
            raise template.TemplateSyntaxError(msg)
    # Call the node.
    return GetPagesNode(var_name)


class GetPagesNode(template.Node):
    """Add the page list to context."""

    def __init__(self, var_name):
        self.var_name = var_name

    def render(self, context):
        # This template tag could raise a PaginationError: you have to call
        # *paginate* or *lazy_paginate* before including the getpages template.
        data = utils.get_data_from_context(context)
        # Add the PageList instance to the context.
        context[self.var_name] = models.PageList(
            context['request'],
            data['page'],
            data['querystring_key'],
            default_number=data['default_number'],
            override_path=data['override_path'],
        )
        return ''


@register.tag
def show_pages(parser, token):
    """Show page links.

    Usage:

    .. code-block:: html+django

        {% show_pages %}

    It is just a shortcut for:

    .. code-block:: html+django

        {% get_pages %}
        {{ pages }}

    You can set ``ENDLESS_PAGINATION_PAGE_LIST_CALLABLE`` in your *settings.py*
    to a callable, or to a dotted path representing a callable, used to
    customize the pages that are displayed.

    See the *__unicode__* method of ``endless_pagination.models.PageList`` for
    a detailed explanation of how the callable can be used.

    Must be called after ``{% paginate objects %}``.
    """
    # Validate args.
    if len(token.contents.split()) != 1:
        msg = '%r tag takes no arguments' % token.contents.split()[0]
        raise template.TemplateSyntaxError(msg)
    # Call the node.
    return ShowPagesNode()


class ShowPagesNode(template.Node):
    """Show the pagination."""

    def render(self, context):
        # This template tag could raise a PaginationError: you have to call
        # *paginate* or *lazy_paginate* before including the getpages template.
        data = utils.get_data_from_context(context)
        # Return the string representation of the sequence of pages.
        pages = models.PageList(
            context['request'],
            data['page'],
            data['querystring_key'],
            default_number=data['default_number'],
            override_path=data['override_path'],
        )
        return utils.text(pages)


@register.tag
def show_current_number(parser, token):
    """Show the current page number, or insert it in the context.

    This tag can for example be useful to change the page title according to
    the current page number.

    To just show current page number:

    .. code-block:: html+django

        {% show_current_number %}

    If you use multiple paginations in the same page, you can get the page
    number for a specific pagination using the querystring key, e.g.:

    .. code-block:: html+django

        {% show_current_number using mykey %}

    The default page when no querystring is specified is 1. If you changed it
    in the `paginate`_ template tag, you have to call  ``show_current_number``
    according to your choice, e.g.:

    .. code-block:: html+django

        {% show_current_number starting from page 3 %}

    This can be also achieved using a template variable you passed to the
    context, e.g.:

    .. code-block:: html+django

        {% show_current_number starting from page page_number %}

    You can of course mix it all (the order of arguments is important):

    .. code-block:: html+django

        {% show_current_number starting from page 3 using mykey %}

    If you want to insert the current page number in the context, without
    actually displaying it in the template, use the *as* argument, i.e.:

    .. code-block:: html+django

        {% show_current_number as page_number %}
        {% show_current_number
            starting from page 3 using mykey as page_number %}

    """
    # Validate args.
    try:
        tag_name, args = token.contents.split(None, 1)
    except ValueError:
        key = None
        number = None
        tag_name = token.contents[0]
        var_name = None
    else:
        # Use a regexp to catch args.
        match = SHOW_CURRENT_NUMBER_EXPRESSION.match(args)
        if match is None:
            msg = 'Invalid arguments for %r tag' % tag_name
            raise template.TemplateSyntaxError(msg)
        # Retrieve objects.
        groupdict = match.groupdict()
        key = groupdict['key']
        number = groupdict['number']
        var_name = groupdict['var_name']
    # Call the node.
    return ShowCurrentNumberNode(number, key, var_name)


class ShowCurrentNumberNode(template.Node):
    """Show the page number taken from context."""

    def __init__(self, number, key, var_name):
        # Retrieve the page number.
        self.page_number_variable = None
        if number is None:
            self.page_number = 1
        elif number.isdigit():
            self.page_number = int(number)
        else:
            self.page_number_variable = template.Variable(number)

        # Get the queystring key.
        self.querystring_key_variable = None
        if key is None:
            self.querystring_key = settings.PAGE_LABEL
        elif key[0] in ('"', "'") and key[-1] == key[0]:
            self.querystring_key = key[1:-1]
        else:
            self.querystring_key_variable = template.Variable(key)

        # Get the template variable name.
        self.var_name = var_name

    def render(self, context):
        # Get the page number to use if it is not specified in querystring.
        if self.page_number_variable is None:
            default_number = self.page_number
        else:
            default_number = int(self.page_number_variable.resolve(context))

        # User can override the querystring key to use in the template.
        # The default value is defined in the settings file.
        if self.querystring_key_variable is None:
            querystring_key = self.querystring_key
        else:
            querystring_key = self.querystring_key_variable.resolve(context)

        # The request object is used to retrieve the current page number.
        page_number = utils.get_page_number_from_request(
            context['request'], querystring_key, default=default_number)

        if self.var_name is None:
            return utils.text(page_number)
        context[self.var_name] = page_number
        return ''

########NEW FILE########
__FILENAME__ = test_callbacks
"""Javascript callbacks integration tests."""

from __future__ import unicode_literals

from endless_pagination.tests.integration import SeleniumTestCase


class CallbacksTest(SeleniumTestCase):

    view_name = 'callbacks'

    def notifications_loaded(self, driver):
        return driver.find_elements_by_id('fragment')

    def assertNotificationsEqual(self, notifications):
        """Assert the given *notifications* equal the ones in the DOM."""
        self.wait_ajax().until(self.notifications_loaded)
        find = self.selenium.find_element_by_id
        for key, value in notifications.items():
            self.assertEqual(value, find(key).text)

    def test_on_click(self):
        # Ensure the onClick callback is correctly called.
        self.get()
        self.click_link(2)
        self.assertNotificationsEqual({
            'onclick': 'Object 1',
            'onclick-label': '2',
            'onclick-url': '/callbacks/?page=2',
            'onclick-key': 'page',
        })

    def test_on_completed(self):
        # Ensure the onCompleted callback is correctly called.
        self.get(page=10)
        self.click_link(1)
        self.assertNotificationsEqual({
            'oncompleted': 'Object 1',
            'oncompleted-label': '1',
            'oncompleted-url': '/callbacks/',
            'oncompleted-key': 'page',
            'fragment': 'Object 3',
        })

########NEW FILE########
__FILENAME__ = test_chunks
"""On scroll chunks integration tests."""

from __future__ import unicode_literals

from endless_pagination.tests.integration import SeleniumTestCase


class ChunksPaginationTest(SeleniumTestCase):

    view_name = 'chunks'

    def test_new_elements_loaded(self):
        # Ensure new pages are loaded on scroll.
        self.get()
        with self.assertNewElements('object', range(1, 11)):
            with self.assertNewElements('item', range(1, 11)):
                self.scroll_down()

    def test_url_not_changed(self):
        # Ensure the request is done using Ajax (the page does not refresh).
        self.get()
        with self.assertSameURL():
            self.scroll_down()

    def test_direct_link(self):
        # Ensure direct links work.
        self.get(data={'page': 2, 'items-page': 3})
        current_url = self.selenium.current_url
        self.assertElements('object', range(6, 11))
        self.assertElements('item', range(11, 16))
        self.assertIn('page=2', current_url)
        self.assertIn('items-page=3', current_url)

    def test_subsequent_page(self):
        # Ensure next page is correctly loaded in a subsequent page, even if
        # normally it is the last page of the chunk.
        self.get(page=3)
        with self.assertNewElements('object', range(11, 21)):
            self.scroll_down()

    def test_chunks(self):
        # Ensure new items are not loaded on scroll if the chunk is complete.
        self.get()
        for i in range(5):
            self.scroll_down()
            self.wait_ajax()
        self.assertElements('object', range(1, 16))
        self.assertElements('item', range(1, 21))

########NEW FILE########
__FILENAME__ = test_digg
"""Digg-style pagination integration tests."""

from __future__ import unicode_literals

from endless_pagination.tests.integration import SeleniumTestCase


class DiggPaginationTest(SeleniumTestCase):

    view_name = 'digg'

    def test_new_elements_loaded(self):
        # Ensure a new page is loaded on click.
        self.get()
        with self.assertNewElements('object', range(6, 11)):
            self.click_link(2)

    def test_url_not_changed(self):
        # Ensure the request is done using Ajax (the page does not refresh).
        self.get()
        with self.assertSameURL():
            self.click_link(2)

    def test_direct_link(self):
        # Ensure direct links work.
        self.get(page=4)
        self.assertElements('object', range(16, 21))
        self.assertIn('page=4', self.selenium.current_url)

    def test_next(self):
        # Ensure next page is correctly loaded.
        self.get()
        with self.assertSameURL():
            with self.assertNewElements('object', range(6, 11)):
                self.click_link(self.NEXT)

    def test_previous(self):
        # Ensure previous page is correctly loaded.
        self.get(page=4)
        with self.assertSameURL():
            with self.assertNewElements('object', range(11, 16)):
                self.click_link(self.PREVIOUS)

    def test_no_previous_link_in_first_page(self):
        # Ensure there is no previous link on the first page.
        self.get()
        self.asserLinksEqual(0, self.PREVIOUS)

    def test_no_next_link_in_last_page(self):
        # Ensure there is no forward link on the last page.
        self.get(page=10)
        self.asserLinksEqual(0, self.NEXT)

########NEW FILE########
__FILENAME__ = test_multiple
"""Multiple pagination integration tests."""

from __future__ import unicode_literals

from endless_pagination.tests.integration import SeleniumTestCase


class MultiplePaginationTest(SeleniumTestCase):

    view_name = 'multiple'

    def test_new_elements_loaded(self):
        # Ensure a new page is loaded on click for each paginated elements.
        self.get()
        with self.assertNewElements('object', range(4, 7)):
            with self.assertNewElements('item', range(7, 10)):
                with self.assertNewElements('entry', range(1, 5)):
                    self.click_link(2, 0)
                    self.click_link(3, 1)
                    self.click_link(self.MORE)

    def test_url_not_changed(self):
        # Ensure the requests are done using Ajax (the page does not refresh).
        self.get()
        with self.assertSameURL():
            self.click_link(2, 0)
            self.click_link(3, 1)
            self.click_link(self.MORE)

    def test_direct_link(self):
        # Ensure direct links work.
        self.get(data={'objects-page': 3, 'items-page': 4, 'entries-page': 5})
        self.assertElements('object', range(7, 10))
        self.assertElements('item', range(10, 13))
        self.assertElements('entry', range(11, 14))
        self.assertIn('objects-page=3', self.selenium.current_url)
        self.assertIn('items-page=4', self.selenium.current_url)
        self.assertIn('entries-page=5', self.selenium.current_url)

    def test_subsequent_pages(self):
        # Ensure elements are correctly loaded starting from a subsequent page.
        self.get(data={'objects-page': 2, 'items-page': 2, 'entries-page': 2})
        with self.assertNewElements('object', range(1, 4)):
            with self.assertNewElements('item', range(7, 10)):
                with self.assertNewElements('entry', range(2, 8)):
                    self.click_link(self.PREVIOUS, 0)
                    self.click_link(self.NEXT, 1)
                    self.click_link(self.MORE)

    def test_no_more_link_in_last_page(self):
        # Ensure there is no more or forward links on the last pages.
        self.get(data={'objects-page': 7, 'items-page': 7, 'entries-page': 8})
        self.asserLinksEqual(0, self.NEXT)
        self.asserLinksEqual(0, self.MORE)

########NEW FILE########
__FILENAME__ = test_onscroll
"""On scroll pagination integration tests."""

from __future__ import unicode_literals

from endless_pagination.tests.integration import SeleniumTestCase


class OnScrollPaginationTest(SeleniumTestCase):

    view_name = 'onscroll'

    def test_new_elements_loaded(self):
        # Ensure a new page is loaded on scroll.
        self.get()
        with self.assertNewElements('object', range(1, 21)):
            self.scroll_down()

    def test_url_not_changed(self):
        # Ensure the request is done using Ajax (the page does not refresh).
        self.get()
        with self.assertSameURL():
            self.scroll_down()

    def test_direct_link(self):
        # Ensure direct links work.
        self.get(page=3)
        self.assertElements('object', range(21, 31))
        self.assertIn('page=3', self.selenium.current_url)

    def test_subsequent_page(self):
        # Ensure next page is correctly loaded in a subsequent page.
        self.get(page=2)
        with self.assertNewElements('object', range(11, 31)):
            self.scroll_down()

    def test_multiple_show_more(self):
        # Ensure new pages are loaded again and again.
        self.get()
        for page in range(2, 5):
            expected_range = range(1, 10 * page + 1)
            with self.assertSameURL():
                with self.assertNewElements('object', expected_range):
                    self.scroll_down()

    def test_scrolling_last_page(self):
        # Ensure scrolling on the last page is a no-op.
        self.get(page=5)
        with self.assertNewElements('object', range(41, 51)):
            self.scroll_down()

########NEW FILE########
__FILENAME__ = test_twitter
"""Twitter-style pagination integration tests."""

from __future__ import unicode_literals

from endless_pagination.tests.integration import SeleniumTestCase


class TwitterPaginationTest(SeleniumTestCase):

    view_name = 'twitter'

    def test_new_elements_loaded(self):
        # Ensure a new page is loaded on click.
        self.get()
        with self.assertNewElements('object', range(1, 11)):
            self.click_link(self.MORE)

    def test_url_not_changed(self):
        # Ensure the request is done using Ajax (the page does not refresh).
        self.get()
        with self.assertSameURL():
            self.click_link(self.MORE)

    def test_direct_link(self):
        # Ensure direct links work.
        self.get(page=4)
        self.assertElements('object', range(16, 21))
        self.assertIn('page=4', self.selenium.current_url)

    def test_subsequent_page(self):
        # Ensure next page is correctly loaded in a subsequent page.
        self.get(page=2)
        with self.assertNewElements('object', range(6, 16)):
            self.click_link(self.MORE)

    def test_multiple_show_more(self):
        # Ensure new pages are loaded again and again.
        self.get()
        for page in range(2, 5):
            expected_range = range(1, 5 * page + 1)
            with self.assertSameURL():
                with self.assertNewElements('object', expected_range):
                    self.click_link(self.MORE)

    def test_no_more_link_in_last_page(self):
        # Ensure there is no more link on the last page.
        self.get(page=10)
        self.asserLinksEqual(0, self.MORE)

########NEW FILE########
__FILENAME__ = test_endless
"""Endless template tags tests."""

from __future__ import unicode_literals
import string
import sys
import xml.etree.ElementTree as etree

from django.template import (
    Context,
    Template,
    TemplateSyntaxError,
)
from django.test import TestCase
from django.test.client import RequestFactory
from django.utils import unittest

from endless_pagination.exceptions import PaginationError
from endless_pagination.models import PageList
from endless_pagination.settings import (
    PAGE_LABEL,
    PER_PAGE,
)
from endless_pagination.tests import make_model_instances


skip_if_old_etree = unittest.skipIf(
    sys.version_info < (2, 7), 'XPath not supported by this Python version.')


class TemplateTagsTestMixin(object):
    """Base test mixin for template tags."""

    def setUp(self):
        self.factory = RequestFactory()

    def render(self, request, contents, **kwargs):
        """Render *contents* using given *request*.

        The context data is represented by keyword arguments.
        Is no keyword arguments are provided, a default context will be used.

        Return the generated HTML and the modified context.
        """
        template = Template('{% load endless %}' + contents)
        context_data = kwargs.copy() if kwargs else {'objects': range(47)}
        context_data['request'] = request
        context = Context(context_data)
        html = template.render(context)
        return html.strip(), context

    def request(self, url='/', page=None, data=None, **kwargs):
        """Return a Django request for the given *page*."""
        querydict = {} if data is None else data
        querydict.update(kwargs)
        if page is not None:
            querydict[PAGE_LABEL] = page
        return self.factory.get(url, querydict)


class EtreeTemplateTagsTestMixin(TemplateTagsTestMixin):
    """Mixin for template tags returning a rendered HTML."""

    def render(self, request, contents, **kwargs):
        """Return the etree root node of the HTML output.

        Does not return the context.
        """
        html, _ = super(EtreeTemplateTagsTestMixin, self).render(
            request, contents, **kwargs)
        if html:
            return etree.fromstring('<html>{0}</html>'.format(html))


class PaginateTestMixin(TemplateTagsTestMixin):
    """Test mixin for *paginate* and *lazy_paginate* tags.

    Subclasses must define *tagname*.
    """

    def assertPaginationNumQueries(self, num_queries, template, queryset=None):
        """Assert the expected *num_queries* are actually executed.

        The given *queryset* is paginated using *template*. If the *queryset*
        is not given, a default queryset containing 47 model instances is used.
        In the *template*, the queryset must be referenced as ``objects``.

        Return the resulting list of objects for the current page.
        """
        if queryset is None:
            queryset = make_model_instances(47)
        request = self.request()
        with self.assertNumQueries(num_queries):
            _, context = self.render(request, template, objects=queryset)
            objects = list(context['objects'])
        return objects

    def assertRangeEqual(self, expected, actual):
        """Assert the *expected* range equals the *actual* one."""
        self.assertListEqual(list(expected), list(actual))

    def render(self, request, contents, **kwargs):
        text = string.Template(contents).substitute(tagname=self.tagname)
        return super(PaginateTestMixin, self).render(request, text, **kwargs)

    def test_object_list(self):
        # Ensure the queryset is correctly updated.
        template = '{% $tagname objects %}'
        html, context = self.render(self.request(), template)
        self.assertRangeEqual(range(PER_PAGE), context['objects'])
        self.assertEqual('', html)

    def test_per_page_argument(self):
        # Ensure the queryset reflects the given ``per_page`` argument.
        template = '{% $tagname 20 objects %}'
        _, context = self.render(self.request(), template)
        self.assertRangeEqual(range(20), context['objects'])

    def test_per_page_argument_as_variable(self):
        # Ensure the queryset reflects the given ``per_page`` argument.
        # In this case, the argument is provided as context variable.
        template = '{% $tagname per_page entries %}'
        _, context = self.render(
            self.request(), template, entries=range(47), per_page=5)
        self.assertRangeEqual(range(5), context['entries'])

    def test_first_page_argument(self):
        # Ensure the queryset reflects the given ``first_page`` argument.
        template = '{% $tagname 10,20 objects %}'
        _, context = self.render(self.request(), template)
        self.assertRangeEqual(range(10), context['objects'])
        # Check the second page.
        _, context = self.render(self.request(page=2), template)
        self.assertRangeEqual(range(10, 30), context['objects'])

    def test_first_page_argument_as_variable(self):
        # Ensure the queryset reflects the given ``first_page`` argument.
        # In this case, the argument is provided as context variable.
        template = '{% $tagname first_page,subsequent_pages entries %}'
        context_data = {
            'entries': range(47),
            'first_page': 1,
            'subsequent_pages': 40,
        }
        _, context = self.render(self.request(), template, **context_data)
        self.assertSequenceEqual([0], context['entries'])
        # Check the second page.
        _, context = self.render(
            self.request(page=2), template, **context_data)
        self.assertRangeEqual(range(1, 41), context['entries'])

    def test_starting_from_page_argument(self):
        # Ensure the queryset reflects the given ``starting_from_page`` arg.
        template = '{% $tagname 10 objects starting from page 3 %}'
        _, context = self.render(self.request(), template)
        self.assertRangeEqual(range(20, 30), context['objects'])

    def test_starting_from_page_argument_as_variable(self):
        # Ensure the queryset reflects the given ``starting_from_page`` arg.
        # In this case, the argument is provided as context variable.
        template = '{% $tagname 10 entries starting from page mypage %}'
        _, context = self.render(
            self.request(), template, entries=range(47), mypage=2)
        self.assertRangeEqual(range(10, 20), context['entries'])

    def test_using_argument(self):
        # Ensure the template tag uses the given querystring key.
        template = '{% $tagname 20 objects using "my-page" %}'
        _, context = self.render(
            self.request(data={'my-page': 2}), template)
        self.assertRangeEqual(range(20, 40), context['objects'])

    def test_using_argument_as_variable(self):
        # Ensure the template tag uses the given querystring key.
        # In this case, the argument is provided as context variable.
        template = '{% $tagname 20 entries using qskey %}'
        _, context = self.render(
            self.request(p=3), template, entries=range(47), qskey='p')
        self.assertRangeEqual(range(40, 47), context['entries'])

    def test_with_argument(self):
        # Ensure the context contains the correct override path.
        template = '{% $tagname 10 objects with "/mypath/" %}'
        _, context = self.render(self.request(), template)
        self.assertEqual('/mypath/', context['endless']['override_path'])

    def test_with_argument_as_variable(self):
        # Ensure the context contains the correct override path.
        # In this case, the argument is provided as context variable.
        path = '/my/path/'
        template = '{% $tagname 10 entries with path %}'
        _, context = self.render(
            self.request(), template, entries=range(47), path=path)
        self.assertEqual(path, context['endless']['override_path'])

    def test_as_argument(self):
        # Ensure it is possible to change the resulting context variable.
        template = '{% $tagname 20 objects as object_list %}'
        _, context = self.render(self.request(), template)
        self.assertRangeEqual(range(20), context['object_list'])
        # The input queryset has not been changed.
        self.assertRangeEqual(range(47), context['objects'])

    def test_complete_argument_list(self):
        # Ensure the tag works providing all the arguments.
        template = (
            '{% $tagname 5,10 objects '
            'starting from page 2 '
            'using mypage '
            'with path '
            'as paginated %}'
        )
        _, context = self.render(
            self.request(), template, objects=range(47), mypage='page-number',
            path='mypath')
        self.assertRangeEqual(range(5, 15), context['paginated'])
        self.assertEqual('mypath', context['endless']['override_path'])

    def test_invalid_arguments(self):
        # An error is raised if invalid arguments are provided.
        templates = (
            '{% $tagname %}',
            '{% $tagname foo bar spam eggs %}',
            '{% $tagname 20 objects as object_list using "mykey" %}',
        )
        request = self.request()
        for template in templates:
            with self.assertRaises(TemplateSyntaxError):
                self.render(request, template)

    def test_invalid_page(self):
        # The first page is displayed if an invalid page is provided.
        template = '{% $tagname 5 objects %}'
        _, context = self.render(self.request(page=0), template)
        self.assertRangeEqual(range(5), context['objects'])

    def test_nested_context_variable(self):
        # Ensure nested context variables are correctly handled.
        manager = {'all': range(47)}
        template = '{% $tagname 5 manager.all as objects %}'
        _, context = self.render(self.request(), template, manager=manager)
        self.assertRangeEqual(range(5), context['objects'])

    def test_failing_nested_context_variable(self):
        # An error is raised if a nested context variable is used but no
        # alias is provided.
        manager = {'all': range(47)}
        template = '{% $tagname 5 manager.all %}'
        with self.assertRaises(TemplateSyntaxError) as cm:
            self.render(self.request(), template, manager=manager)
        self.assertIn('manager.all', str(cm.exception))

    def test_multiple_pagination(self):
        # Ensure multiple pagination works correctly.
        letters = string.ascii_letters
        template = (
            '{% $tagname 10,20 objects %}'
            '{% $tagname 1 items using items_page %}'
            '{% $tagname 5 entries.all using "entries" as myentries %}'
        )
        _, context = self.render(
            self.request(page=2, entries=3), template,
            objects=range(47), entries={'all': letters},
            items=['foo', 'bar'], items_page='p')
        self.assertRangeEqual(range(10, 30), context['objects'])
        self.assertSequenceEqual(['foo'], context['items'])
        self.assertSequenceEqual(letters[10:15], context['myentries'])
        self.assertSequenceEqual(letters, context['entries']['all'])


class PaginateTest(PaginateTestMixin, TestCase):

    tagname = 'paginate'

    def test_starting_from_last_page_argument(self):
        # Ensure the queryset reflects the given ``starting_from_page``
        # argument when the last page is requested.
        template = '{% $tagname 10 objects starting from page -1 %}'
        _, context = self.render(self.request(), template)
        self.assertRangeEqual(range(40, 47), context['objects'])

    def test_starting_from_negative_page_argument(self):
        # Ensure the queryset reflects the given ``starting_from_page``
        # argument when a negative number is passed as value.
        template = '{% $tagname 10 objects starting from page -3 %}'
        _, context = self.render(self.request(), template)
        self.assertRangeEqual(range(20, 30), context['objects'])

    def test_starting_from_negative_page_argument_as_variable(self):
        # Ensure the queryset reflects the given ``starting_from_page``
        # argument when a negative number is passed as value.
        # In this case, the argument is provided as context variable.
        template = '{% $tagname 10 objects starting from page mypage %}'
        _, context = self.render(
            self.request(), template, objects=range(47), mypage=-2)
        self.assertRangeEqual(range(30, 40), context['objects'])

    def test_starting_from_negative_page_out_of_range(self):
        # Ensure the last page is returned when the ``starting_from_page``
        # argument, given a negative value, produces an out of range error.
        template = '{% $tagname 10 objects starting from page -5 %}'
        _, context = self.render(self.request(), template)
        self.assertRangeEqual(range(10), context['objects'])

    def test_num_queries(self):
        # Ensure paginating objects hits the database for the correct number
        # of times.
        template = '{% $tagname 10 objects %}'
        objects = self.assertPaginationNumQueries(2, template)
        self.assertEqual(10, len(objects))

    def test_num_queries_starting_from_another_page(self):
        # Ensure paginating objects hits the database for the correct number
        # of times if pagination is performed starting from another page.
        template = '{% $tagname 10 objects starting from page 3 %}'
        self.assertPaginationNumQueries(2, template)

    def test_num_queries_starting_from_last_page(self):
        # Ensure paginating objects hits the database for the correct number
        # of times if pagination is performed starting from last page.
        template = '{% $tagname 10 objects starting from page -1 %}'
        self.assertPaginationNumQueries(2, template)


class LazyPaginateTest(PaginateTestMixin, TestCase):

    tagname = 'lazy_paginate'

    def test_starting_from_negative_page_raises_error(self):
        # A *NotImplementedError* is raised if a negative value is given to
        # the ``starting_from_page`` argument of ``lazy_paginate``.
        template = '{% $tagname 10 objects starting from page -1 %}'
        with self.assertRaises(NotImplementedError):
            self.render(self.request(), template)

    def test_num_queries(self):
        # Ensure paginating objects hits the database for the correct number
        # of times. If lazy pagination is used, the ``SELECT COUNT`` query
        # should be avoided.
        template = '{% $tagname 10 objects %}'
        objects = self.assertPaginationNumQueries(1, template)
        self.assertEqual(10, len(objects))

    def test_num_queries_starting_from_another_page(self):
        # Ensure paginating objects hits the database for the correct number
        # of times if pagination is performed starting from another page.
        template = '{% $tagname 10 objects starting from page 3 %}'
        self.assertPaginationNumQueries(1, template)


@skip_if_old_etree
class ShowMoreTest(EtreeTemplateTagsTestMixin, TestCase):

    def test_first_page_next_url(self):
        # Ensure the link to the next page is correctly generated
        # in the first page.
        template = '{% paginate objects %}{% show_more %}'
        tree = self.render(self.request(), template)
        link = tree.find('.//a[@class="endless_more"]')
        expected = '/?{0}={1}'.format(PAGE_LABEL, 2)
        self.assertEqual(expected, link.attrib['href'])

    def test_page_next_url(self):
        # Ensure the link to the next page is correctly generated.
        template = '{% paginate objects %}{% show_more %}'
        tree = self.render(self.request(page=3), template)
        link = tree.find('.//a[@class="endless_more"]')
        expected = '/?{0}={1}'.format(PAGE_LABEL, 4)
        self.assertEqual(expected, link.attrib['href'])

    def test_last_page(self):
        # Ensure the output for the last page is empty.
        template = '{% paginate 40 objects %}{% show_more %}'
        tree = self.render(self.request(page=2), template)
        self.assertIsNone(tree)

    def test_customized_label(self):
        # Ensure the link to the next page is correctly generated.
        template = '{% paginate objects %}{% show_more "again and again" %}'
        tree = self.render(self.request(), template)
        link = tree.find('.//a[@class="endless_more"]')
        self.assertEqual('again and again', link.text)

    def test_customized_loading(self):
        # Ensure the link to the next page is correctly generated.
        template = '{% paginate objects %}{% show_more "more" "working" %}'
        tree = self.render(self.request(), template)
        loading = tree.find('.//*[@class="endless_loading"]')
        self.assertEqual('working', loading.text)


class GetPagesTest(TemplateTagsTestMixin, TestCase):

    def test_page_list(self):
        # Ensure the page list is correctly included in the context.
        template = '{% paginate objects %}{% get_pages %}'
        html, context = self.render(self.request(), template)
        self.assertEqual('', html)
        self.assertIn('pages', context)
        self.assertIsInstance(context['pages'], PageList)

    def test_different_varname(self):
        # Ensure the page list is correctly included in the context when
        # using a different variable name.
        template = '{% paginate objects %}{% get_pages as page_list %}'
        _, context = self.render(self.request(), template)
        self.assertIn('page_list', context)
        self.assertIsInstance(context['page_list'], PageList)

    def test_page_numbers(self):
        # Ensure the current page in the page list reflects the current
        # page number.
        template = '{% lazy_paginate objects %}{% get_pages %}'
        for page_number in range(1, 5):
            _, context = self.render(self.request(page=page_number), template)
            page = context['pages'].current()
            self.assertEqual(page_number, page.number)

    def test_without_paginate_tag(self):
        # An error is raised if this tag is used before the paginate one.
        template = '{% get_pages %}'
        with self.assertRaises(PaginationError):
            self.render(self.request(), template)

    def test_invalid_arguments(self):
        # An error is raised if invalid arguments are provided.
        template = '{% lazy_paginate objects %}{% get_pages foo bar %}'
        request = self.request()
        with self.assertRaises(TemplateSyntaxError):
            self.render(request, template)

    def test_starting_from_negative_page_in_another_page(self):
        # Ensure the default page is missing the querystring when another
        # page is displayed.
        template = (
            '{% paginate 10 objects starting from page -1 %}'
            '{% get_pages %}'
        )
        _, context = self.render(
            self.request(), template, objects=range(47), page=1)
        page = context['pages'].last()
        self.assertEqual('', page.url)

    def test_pages_length(self):
        # Ensure the pages length returns the correct number of pages.
        template = '{% paginate 10 objects %}{% get_pages %}{{ pages|length }}'
        html, context = self.render(self.request(), template)
        self.assertEqual('5', html)


@skip_if_old_etree
class ShowPagesTest(EtreeTemplateTagsTestMixin, TestCase):

    def test_current_page(self):
        # Ensure the current page in the page list reflects the current
        # page number.
        template = '{% paginate objects %}{% show_pages %}'
        for page_number in range(1, 6):
            tree = self.render(self.request(page=page_number), template)
            current = tree.find('.//*[@class="endless_page_current"]')
            text = ''.join(element.text for element in current)
            self.assertEqual(str(page_number), text)

    def test_links(self):
        # Ensure the correct number of links is always displayed.
        template = '{% paginate objects %}{% show_pages %}'
        for page_number in range(1, 6):
            tree = self.render(self.request(page=page_number), template)
            links = tree.findall('.//a')
            expected = 5 if page_number == 1 or page_number == 5 else 6
            self.assertEqual(expected, len(links))

    def test_without_paginate_tag(self):
        # An error is raised if this tag is used before the paginate one.
        template = '{% show_pages %}'
        with self.assertRaises(PaginationError):
            self.render(self.request(), template)

    def test_invalid_arguments(self):
        # An error is raised if invalid arguments are provided.
        template = '{% lazy_paginate objects %}{% show_pages foo bar %}'
        request = self.request()
        with self.assertRaises(TemplateSyntaxError):
            self.render(request, template)


class ShowCurrentNumberTest(TemplateTagsTestMixin, TestCase):

    def test_current_number(self):
        # Ensure the current number is correctly returned.
        template = '{% show_current_number %}'
        for page_number in range(1, 6):
            html, _ = self.render(self.request(page=page_number), template)
            self.assertEqual(page_number, int(html))

    def test_starting_from_page_argument(self):
        # Ensure the number reflects the given ``starting_from_page`` arg.
        template = '{% show_current_number starting from page 3 %}'
        html, _ = self.render(self.request(), template)
        self.assertEqual(3, int(html))

    def test_starting_from_page_argument_as_variable(self):
        # Ensure the number reflects the given ``starting_from_page`` arg.
        # In this case, the argument is provided as context variable.
        template = '{% show_current_number starting from page mypage %}'
        html, _ = self.render(
            self.request(), template, entries=range(47), mypage=2)
        self.assertEqual(2, int(html))

    def test_using_argument(self):
        # Ensure the template tag uses the given querystring key.
        template = '{% show_current_number using "mypage" %}'
        html, _ = self.render(
            self.request(mypage=2), template)
        self.assertEqual(2, int(html))

    def test_using_argument_as_variable(self):
        # Ensure the template tag uses the given querystring key.
        # In this case, the argument is provided as context variable.
        template = '{% show_current_number using qskey %}'
        html, _ = self.render(
            self.request(p=5), template, entries=range(47), qskey='p')
        self.assertEqual(5, int(html))

    def test_as_argument(self):
        # Ensure it is possible add the page number to context.
        template = '{% show_current_number as page_number %}'
        html, context = self.render(self.request(page=4), template)
        self.assertEqual('', html)
        self.assertIn('page_number', context)
        self.assertEqual(4, context['page_number'])

    def test_complete_argument_list(self):
        # Ensure the tag works providing all the arguments.
        template = (
            '{% show_current_number '
            'starting from page 2 '
            'using mypage '
            'as number %}'
        )
        html, context = self.render(
            self.request(), template, objects=range(47), mypage='page-number')
        self.assertEqual(2, context['number'])

    def test_invalid_arguments(self):
        # An error is raised if invalid arguments are provided.
        templates = (
            '{% show_current_number starting from page %}',
            '{% show_current_number foo bar spam eggs %}',
            '{% show_current_number as number using key %}',
        )
        request = self.request()
        for template in templates:
            with self.assertRaises(TemplateSyntaxError):
                self.render(request, template)

########NEW FILE########
__FILENAME__ = test_decorators
"""Decorator tests."""

from __future__ import unicode_literals

from django.test import TestCase
from django.test.client import RequestFactory

from endless_pagination import decorators


class DecoratorsTestMixin(object):
    """Base test mixin for decorators.

    Subclasses (actual test cases) must implement the ``get_decorator`` method
    and the ``arg`` attribute to be used as argument for the decorator.
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.ajax_headers = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        self.default = 'default.html'
        self.page = 'page.html'
        self.page_url = '/?page=2&mypage=10&querystring_key=page'
        self.mypage = 'mypage.html'
        self.mypage_url = '/?page=2&mypage=10&querystring_key=mypage'

    def get_decorator(self):
        """Return the decorator that must be exercised."""
        raise NotImplementedError

    def assertTemplatesEqual(self, expected_active, expected_page, templates):
        """Assert active template and page template are the ones given."""
        self.assertSequenceEqual([expected_active, expected_page], templates)

    def decorate(self, *args, **kwargs):
        """Return a view decorated with ``self.decorator(*args, **kwargs)``."""

        def view(request, extra_context=None, template=self.default):
            """Test view that will be decorated in tests."""
            context = {}
            if extra_context is not None:
                context.update(extra_context)
            return template, context['page_template']

        decorator = self.get_decorator()
        return decorator(*args, **kwargs)(view)

    def test_decorated(self):
        # Ensure the view is correctly decorated.
        view = self.decorate(self.arg)
        templates = view(self.factory.get('/'))
        self.assertTemplatesEqual(self.default, self.page, templates)

    def test_request_with_querystring_key(self):
        # If the querystring key refers to the handled template,
        # the view still uses the default tempate if the request is not Ajax.
        view = self.decorate(self.arg)
        templates = view(self.factory.get(self.page_url))
        self.assertTemplatesEqual(self.default, self.page, templates)

    def test_ajax_request(self):
        # Ensure the view serves the template fragment if the request is Ajax.
        view = self.decorate(self.arg)
        templates = view(self.factory.get('/', **self.ajax_headers))
        self.assertTemplatesEqual(self.page, self.page, templates)

    def test_ajax_request_with_querystring_key(self):
        # If the querystring key refers to the handled template,
        # the view switches the template if the request is Ajax.
        view = self.decorate(self.arg)
        templates = view(self.factory.get(self.page_url, **self.ajax_headers))
        self.assertTemplatesEqual(self.page, self.page, templates)

    def test_unexistent_page(self):
        # Ensure the default page and is returned if the querystring points
        # to a page that is not defined.
        view = self.decorate(self.arg)
        templates = view(self.factory.get('/?querystring_key=does-not-exist'))
        self.assertTemplatesEqual(self.default, self.page, templates)


class PageTemplateTest(DecoratorsTestMixin, TestCase):

    arg = 'page.html'

    def get_decorator(self):
        return decorators.page_template

    def test_request_with_querystring_key_to_mypage(self):
        # If the querystring key refers to another template,
        # the view still uses the default tempate if the request is not Ajax.
        view = self.decorate(self.arg)
        templates = view(self.factory.get(self.mypage_url))
        self.assertTemplatesEqual(self.default, self.page, templates)

    def test_ajax_request_with_querystring_key_to_mypage(self):
        # If the querystring key refers to another template,
        # the view still uses the default tempate even if the request is Ajax.
        view = self.decorate(self.arg)
        templates = view(
            self.factory.get(self.mypage_url, **self.ajax_headers))
        self.assertTemplatesEqual(self.default, self.page, templates)

    def test_ajax_request_to_mypage(self):
        # Ensure the view serves the template fragment if the request is Ajax
        # and another template fragment is requested.
        view = self.decorate(self.mypage, key='mypage')
        templates = view(
            self.factory.get(self.mypage_url, **self.ajax_headers))
        self.assertTemplatesEqual(self.mypage, self.mypage, templates)


class PageTemplatesTest(DecoratorsTestMixin, TestCase):

    arg = {'page.html': None, 'mypage.html': 'mypage'}

    def get_decorator(self):
        return decorators.page_templates

    def test_request_with_querystring_key_to_mypage(self):
        # If the querystring key refers to another template,
        # the view still uses the default tempate if the request is not Ajax.
        view = self.decorate(self.arg)
        templates = view(self.factory.get(self.mypage_url))
        self.assertTemplatesEqual(self.default, self.mypage, templates)

    def test_ajax_request_with_querystring_key_to_mypage(self):
        # If the querystring key refers to another template,
        # the view switches to the givent template if the request is Ajax.
        view = self.decorate(self.arg)
        templates = view(
            self.factory.get(self.mypage_url, **self.ajax_headers))
        self.assertTemplatesEqual(self.mypage, self.mypage, templates)


class PageTemplatesWithTupleTest(PageTemplatesTest):

    arg = (('page.html', None), ('mypage.html', 'mypage'))

########NEW FILE########
__FILENAME__ = test_loaders
"""Loader tests."""

from __future__ import unicode_literals
from contextlib import contextmanager

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase

from endless_pagination import loaders


test_object = 'test object'


class ImproperlyConfiguredTestMixin(object):
    """Include an ImproperlyConfigured assertion."""

    @contextmanager
    def assertImproperlyConfigured(self, message):
        """Assert the code in the context manager block raises an error.

        The error must be ImproperlyConfigured, and the error message must
        include the given *message*.
        """
        try:
            yield
        except ImproperlyConfigured as err:
            self.assertIn(message, str(err).lower())
        else:
            self.fail('ImproperlyConfigured not raised')


class AssertImproperlyConfiguredTest(ImproperlyConfiguredTestMixin, TestCase):

    def test_assertion(self):
        # Ensure the assertion does not fail if ImproperlyConfigured is raised
        # with the given error message.
        with self.assertImproperlyConfigured('error'):
            raise ImproperlyConfigured('Example error text')

    def test_case_insensitive(self):
        # Ensure the error message test is case insensitive.
        with self.assertImproperlyConfigured('error'):
            raise ImproperlyConfigured('Example ERROR text')

    def test_assertion_fails_different_message(self):
        # Ensure the assertion fails if ImproperlyConfigured is raised with
        # a different message.
        with self.assertRaises(AssertionError):
            with self.assertImproperlyConfigured('failure'):
                raise ImproperlyConfigured('Example error text')

    def test_assertion_fails_no_exception(self):
        # Ensure the assertion fails if ImproperlyConfigured is not raised.
        with self.assertRaises(AssertionError) as cm:
            with self.assertImproperlyConfigured('error'):
                pass
        self.assertEqual('ImproperlyConfigured not raised', str(cm.exception))

    def test_assertion_fails_different_exception(self):
        # Ensure other exceptions are not swallowed.
        with self.assertRaises(TypeError):
            with self.assertImproperlyConfigured('error'):
                raise TypeError


class LoadObjectTest(ImproperlyConfiguredTestMixin, TestCase):

    def setUp(self):
        self.module = self.__class__.__module__

    def test_valid_path(self):
        # Ensure the object is correctly loaded if the provided path is valid.
        path = '.'.join((self.module, 'test_object'))
        self.assertIs(test_object, loaders.load_object(path))

    def test_module_not_found(self):
        # An error is raised if the module cannot be found.
        with self.assertImproperlyConfigured('not found'):
            loaders.load_object('__invalid__.module')

    def test_invalid_module(self):
        # An error is raised if the provided path is not a valid dotted string.
        with self.assertImproperlyConfigured('invalid'):
            loaders.load_object('')

    def test_object_not_found(self):
        # An error is raised if the object cannot be found in the module.
        path = '.'.join((self.module, '__does_not_exist__'))
        with self.assertImproperlyConfigured('object'):
            loaders.load_object(path)

########NEW FILE########
__FILENAME__ = test_models
"""Model tests."""

from __future__ import unicode_literals
from contextlib import contextmanager

from django.test import TestCase
from django.test.client import RequestFactory

from endless_pagination import (
    models,
    settings,
    utils,
)
from endless_pagination.paginators import DefaultPaginator


@contextmanager
def local_settings(**kwargs):
    """Override local Django Endless Pagination settings.

    This context manager can be used in a way similar to Django own
    ``TestCase.settings()``.
    """
    original_values = []
    for key, value in kwargs.items():
        original_values.append([key, getattr(settings, key)])
        setattr(settings, key, value)
    try:
        yield
    finally:
        for key, value in original_values:
            setattr(settings, key, value)


class LocalSettingsTest(TestCase):

    def setUp(self):
        settings._LOCAL_SETTINGS_TEST = 'original'

    def tearDown(self):
        del settings._LOCAL_SETTINGS_TEST

    def test_settings_changed(self):
        # Check that local settings are changed.
        with local_settings(_LOCAL_SETTINGS_TEST='changed'):
            self.assertEqual('changed', settings._LOCAL_SETTINGS_TEST)

    def test_settings_restored(self):
        # Check that local settings are restored.
        with local_settings(_LOCAL_SETTINGS_TEST='changed'):
            pass
        self.assertEqual('original', settings._LOCAL_SETTINGS_TEST)

    def test_restored_after_exception(self):
        # Check that local settings are restored after an exception.
        with self.assertRaises(RuntimeError):
            with local_settings(_LOCAL_SETTINGS_TEST='changed'):
                raise RuntimeError()
            self.assertEqual('original', settings._LOCAL_SETTINGS_TEST)


def page_list_callable_arrows(number, num_pages):
    """Wrap ``endless_pagination.utils.get_page_numbers``.

    Set first / last page arrows to True.
    """
    return utils.get_page_numbers(number, num_pages, arrows=True)


page_list_callable_dummy = lambda number, num_pages: [None]


class PageListTest(TestCase):

    def setUp(self):
        self.paginator = DefaultPaginator(range(30), 7, orphans=2)
        self.current_number = 2
        self.page_label = 'page'
        self.factory = RequestFactory()
        self.request = self.factory.get(
            self.get_path_for_page(self.current_number))
        self.pages = models.PageList(
            self.request, self.paginator.page(self.current_number),
            self.page_label)

    def get_url_for_page(self, number):
        """Return a url for the given page ``number``."""
        return '?{0}={1}'.format(self.page_label, number)

    def get_path_for_page(self, number):
        """Return a path for the given page ``number``."""
        return '/' + self.get_url_for_page(number)

    def check_page(
            self, page, number, is_first, is_last, is_current, label=None):
        """Perform several assertions on the given page attrs."""
        if label is None:
            label = utils.text(page.number)
        self.assertEqual(label, page.label)
        self.assertEqual(number, page.number)
        self.assertEqual(is_first, page.is_first)
        self.assertEqual(is_last, page.is_last)
        self.assertEqual(is_current, page.is_current)

    def check_page_list_callable(self, callable_or_path):
        """Check the provided *page_list_callable* is actually used."""
        with local_settings(PAGE_LIST_CALLABLE=callable_or_path):
            rendered = utils.text(self.pages).strip()
        expected = '<span class="endless_separator">...</span>'
        self.assertEqual(expected, rendered)

    def test_length(self):
        # Ensure the length of the page list equals the number of pages.
        self.assertEqual(self.paginator.num_pages, len(self.pages))

    def test_paginated(self):
        # Ensure the *paginated* method returns True if the page list contains
        # more than one page, False otherwise.
        page = DefaultPaginator(range(10), 10).page(1)
        pages = models.PageList(self.request, page, self.page_label)
        self.assertFalse(pages.paginated())
        self.assertTrue(self.pages.paginated())

    def test_first_page(self):
        # Ensure the attrs of the first page are correctly defined.
        page = self.pages.first()
        self.assertEqual('/', page.path)
        self.assertEqual('', page.url)
        self.check_page(page, 1, True, False, False)

    def test_last_page(self):
        # Ensure the attrs of the last page are correctly defined.
        page = self.pages.last()
        self.check_page(page, len(self.pages), False, True, False)

    def test_first_page_as_arrow(self):
        # Ensure the attrs of the first page are correctly defined when the
        # page is represented as an arrow.
        page = self.pages.first_as_arrow()
        self.assertEqual('/', page.path)
        self.assertEqual('', page.url)
        self.check_page(
            page, 1, True, False, False, label=settings.FIRST_LABEL)

    def test_last_page_as_arrow(self):
        # Ensure the attrs of the last page are correctly defined when the
        # page is represented as an arrow.
        page = self.pages.last_as_arrow()
        self.check_page(
            page, len(self.pages), False, True, False,
            label=settings.LAST_LABEL)

    def test_current_page(self):
        # Ensure the attrs of the current page are correctly defined.
        page = self.pages.current()
        self.check_page(page, self.current_number, False, False, True)

    def test_path(self):
        # Ensure the path of each page is correctly generated.
        for num, page in enumerate(list(self.pages)[1:]):
            expected = self.get_path_for_page(num + 2)
            self.assertEqual(expected, page.path)

    def test_url(self):
        # Ensure the path of each page is correctly generated.
        for num, page in enumerate(list(self.pages)[1:]):
            expected = self.get_url_for_page(num + 2)
            self.assertEqual(expected, page.url)

    def test_current_indexes(self):
        # Ensure the 1-based indexes of the first and last items on the current
        # page are correctly returned.
        self.assertEqual(8, self.pages.current_start_index())
        self.assertEqual(14, self.pages.current_end_index())

    def test_total_count(self):
        # Ensure the total number of objects is correctly returned.
        self.assertEqual(30, self.pages.total_count())

    def test_page_render(self):
        # Ensure the page is correctly rendered.
        page = self.pages.first()
        rendered_page = utils.text(page)
        self.assertIn('href="/"', rendered_page)
        self.assertIn(page.label, rendered_page)

    def test_current_page_render(self):
        # Ensure the page is correctly rendered.
        page = self.pages.current()
        rendered_page = utils.text(page)
        self.assertNotIn('href', rendered_page)
        self.assertIn(page.label, rendered_page)

    def test_page_list_render(self):
        # Ensure the page list is correctly rendered.
        rendered = utils.text(self.pages)
        self.assertEqual(5, rendered.count('<a href'))
        self.assertIn(settings.PREVIOUS_LABEL, rendered)
        self.assertIn(settings.NEXT_LABEL, rendered)

    def test_page_list_render_using_arrows(self):
        # Ensure the page list is correctly rendered when using first / last
        # page arrows.
        page_list_callable = (
            'endless_pagination.tests.test_models.page_list_callable_arrows')
        with local_settings(PAGE_LIST_CALLABLE=page_list_callable):
            rendered = utils.text(self.pages)
        self.assertEqual(7, rendered.count('<a href'))
        self.assertIn(settings.FIRST_LABEL, rendered)
        self.assertIn(settings.LAST_LABEL, rendered)

    def test_page_list_render_just_one_page(self):
        # Ensure nothing is rendered if the page list contains only one page.
        page = DefaultPaginator(range(10), 10).page(1)
        pages = models.PageList(self.request, page, self.page_label)
        self.assertEqual('', utils.text(pages))

    def test_different_default_number(self):
        # Ensure the page path is generated based on the default number.
        pages = models.PageList(
            self.request, self.paginator.page(2), self.page_label,
            default_number=2)
        self.assertEqual('/', pages.current().path)
        self.assertEqual(self.get_path_for_page(1), pages.first().path)

    def test_index_error(self):
        # Ensure an error if raised if a non existent page is requested.
        with self.assertRaises(IndexError):
            self.pages[len(self.pages) + 1]

    def test_previous(self):
        # Ensure the correct previous page is returned.
        previous_page = self.pages.previous()
        self.assertEqual(self.current_number - 1, previous_page.number)

    def test_next(self):
        # Ensure the correct next page is returned.
        next_page = self.pages.next()
        self.assertEqual(self.current_number + 1, next_page.number)

    def test_no_previous(self):
        # An empty string is returned if the previous page cannot be found.
        pages = models.PageList(
            self.request, self.paginator.page(1), self.page_label)
        self.assertEqual('', pages.previous())

    def test_no_next(self):
        # An empty string is returned if the next page cannot be found.
        num_pages = self.paginator.num_pages
        pages = models.PageList(
            self.request, self.paginator.page(num_pages), self.page_label)
        self.assertEqual('', pages.next())

    def test_customized_page_list_callable(self):
        # The page list is rendered based on ``settings.PAGE_LIST_CALLABLE``.
        self.check_page_list_callable(page_list_callable_dummy)

    def test_customized_page_list_dotted_path(self):
        # The option ``settings.PAGE_LIST_CALLABLE`` can be provided as a
        # dotted path, e.g.: 'path.to.my.callable'.
        self.check_page_list_callable(
            'endless_pagination.tests.test_models.page_list_callable_dummy')

    def test_whitespace_in_path(self):
        # Ensure white spaces in paths are correctly handled.
        path = '/a path/containing spaces/'
        request = self.factory.get(path)
        next = models.PageList(
            request, self.paginator.page(self.current_number),
            self.page_label).next()
        self.assertEqual(path.replace(' ', '%20') + next.url, next.path)

    def test_lookup(self):
        # Ensure the page list correctly handles lookups.
        pages = self.pages
        self.assertEqual(pages.first().number, pages[1].number)

    def test_invalid_lookup(self):
        # A TypeError is raised if the lookup is not valid.
        with self.assertRaises(TypeError):
            self.pages['invalid']

########NEW FILE########
__FILENAME__ = test_paginators
"""Paginator tests."""

from __future__ import unicode_literals

from django.test import TestCase

from endless_pagination import paginators


class PaginatorTestMixin(object):
    """Base test mixin for paginators.

    Subclasses (actual test cases) must define the ``paginator_class`` name.
    """

    def setUp(self):
        self.items = list(range(30))
        self.per_page = 7
        self.paginator = self.paginator_class(
            self.items, self.per_page, orphans=2)

    def test_object_list(self):
        # Ensure the paginator correctly returns objects for each page.
        first_page = self.paginator.first_page
        expected = self.items[first_page:first_page + self.per_page]
        object_list = self.paginator.page(2).object_list
        self.assertSequenceEqual(expected, object_list)

    def test_orphans(self):
        # Ensure orphans are included in the last page.
        object_list = self.paginator.page(4).object_list
        self.assertSequenceEqual(self.items[-9:], object_list)

    def test_no_orphans(self):
        # Ensure exceeding orphans generate a new page.
        paginator = self.paginator_class(range(11), 8, orphans=2)
        object_list = paginator.page(2).object_list
        self.assertEqual(3, len(object_list))

    def test_empty_page(self):
        # En error if raised if the requested page does not exist.
        with self.assertRaises(paginators.EmptyPage):
            self.paginator.page(5)

    def test_invalid_page(self):
        # En error is raised if the requested page is not valid.
        with self.assertRaises(paginators.PageNotAnInteger):
            self.paginator.page('__not_valid__')
        with self.assertRaises(paginators.EmptyPage):
            self.paginator.page(0)


class DifferentFirstPagePaginatorTestMixin(PaginatorTestMixin):
    """Base test mixin for paginators.

    This time the paginator defined in ``setUp`` has different number of
    items on the first page.
    Subclasses (actual test cases) must define the ``paginator_class`` name.
    """

    def setUp(self):
        self.items = list(range(26))
        self.per_page = 7
        self.paginator = self.paginator_class(
            self.items, self.per_page, first_page=3, orphans=2)

    def test_no_orphans(self):
        # Ensure exceeding orphans generate a new page.
        paginator = self.paginator_class(range(11), 5, first_page=3, orphans=2)
        object_list = paginator.page(3).object_list
        self.assertEqual(3, len(object_list))


class DefaultPaginatorTest(PaginatorTestMixin, TestCase):

    paginator_class = paginators.DefaultPaginator

    def test_indexes(self):
        # Ensure start and end indexes are correct.
        page = self.paginator.page(2)
        self.assertEqual(self.per_page + 1, page.start_index())
        self.assertEqual(self.per_page * 2, page.end_index())

    def test_items_count(self):
        # Ensure the paginator reflects the number of items.
        self.assertEqual(len(self.items), self.paginator.count)

    def test_num_pages(self):
        # Ensure the number of pages is correctly calculated.
        self.assertEqual(4, self.paginator.num_pages)

    def test_page_range(self):
        # Ensure the page range is correctly calculated.
        self.assertSequenceEqual([1, 2, 3, 4], self.paginator.page_range)

    def test_no_items(self):
        # Ensure the right values are returned if the page contains no items.
        paginator = self.paginator_class([], 10)
        page = paginator.page(1)
        self.assertEqual(0, paginator.count)
        self.assertEqual(0, page.start_index())

    def test_single_page_indexes(self):
        # Ensure the returned indexes are correct for a single page pagination.
        paginator = self.paginator_class(range(6), 5, orphans=2)
        page = paginator.page(1)
        self.assertEqual(1, page.start_index())
        self.assertEqual(6, page.end_index())


class LazyPaginatorTest(PaginatorTestMixin, TestCase):

    paginator_class = paginators.LazyPaginator

    def test_items_count(self):
        # The lazy paginator does not implement items count.
        with self.assertRaises(NotImplementedError):
            self.paginator.count

    def test_num_pages(self):
        # The number of pages depends on the current page.
        self.paginator.page(2)
        self.assertEqual(3, self.paginator.num_pages)

    def test_page_range(self):
        # The lazy paginator does not implement page range.
        with self.assertRaises(NotImplementedError):
            self.paginator.page_range


class DifferentFirstPageDefaultPaginatorTest(
        DifferentFirstPagePaginatorTestMixin, TestCase):

    paginator_class = paginators.DefaultPaginator


class DifferentFirstPageLazyPaginatorTest(
        DifferentFirstPagePaginatorTestMixin, TestCase):

    paginator_class = paginators.LazyPaginator

########NEW FILE########
__FILENAME__ = test_utils
"""Utilities tests."""

from __future__ import unicode_literals

from django.test import TestCase
from django.test.client import RequestFactory

from endless_pagination import utils
from endless_pagination.settings import PAGE_LABEL
from endless_pagination.exceptions import PaginationError


class GetDataFromContextTest(TestCase):

    def test_valid_context(self):
        # Ensure the endless data is correctly retrieved from context.
        context = {'endless': 'test-data'}
        self.assertEqual('test-data', utils.get_data_from_context(context))

    def test_invalid_context(self):
        # A ``PaginationError`` is raised if the data cannot be found
        # in the context.
        self.assertRaises(PaginationError, utils.get_data_from_context, {})


class GetPageNumberFromRequestTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_no_querystring_key(self):
        # Ensure the first page is returned if page info cannot be
        # retrieved from the querystring.
        request = self.factory.get('/')
        self.assertEqual(1, utils.get_page_number_from_request(request))

    def test_default_querystring_key(self):
        # Ensure the default page label is used if ``querystring_key``
        # is not provided.
        request = self.factory.get('?{0}=2'.format(PAGE_LABEL))
        self.assertEqual(2, utils.get_page_number_from_request(request))

    def test_default(self):
        # Ensure the default page number is returned if page info cannot be
        # retrieved from the querystring.
        request = self.factory.get('/')
        page_number = utils.get_page_number_from_request(request, default=3)
        self.assertEqual(3, page_number)

    def test_custom_querystring_key(self):
        # Ensure the page returned correctly reflects the ``querystring_key``.
        request = self.factory.get('?mypage=4'.format(PAGE_LABEL))
        page_number = utils.get_page_number_from_request(
            request, querystring_key='mypage')
        self.assertEqual(4, page_number)

    def test_post_data(self):
        # The page number can also be present in POST data.
        request = self.factory.post('/', {PAGE_LABEL: 5})
        self.assertEqual(5, utils.get_page_number_from_request(request))


class GetPageNumbersTest(TestCase):

    def test_defaults(self):
        # Ensure the pages are returned correctly using the default values.
        pages = utils.get_page_numbers(10, 20)
        expected = [
            'previous', 1, 2, 3, None, 8, 9, 10, 11, 12,
            None, 18, 19, 20, 'next']
        self.assertSequenceEqual(expected, pages)

    def test_first_page(self):
        # Ensure the correct pages are returned if the first page is requested.
        pages = utils.get_page_numbers(1, 10)
        expected = [1, 2, 3, None, 8, 9, 10, 'next']
        self.assertSequenceEqual(expected, pages)

    def test_last_page(self):
        # Ensure the correct pages are returned if the last page is requested.
        pages = utils.get_page_numbers(10, 10)
        expected = ['previous', 1, 2, 3, None, 8, 9, 10]
        self.assertSequenceEqual(expected, pages)

    def test_no_extremes(self):
        # Ensure the correct pages are returned with no extremes.
        pages = utils.get_page_numbers(10, 20, extremes=0)
        expected = ['previous', 8, 9, 10, 11, 12, 'next']
        self.assertSequenceEqual(expected, pages)

    def test_no_arounds(self):
        # Ensure the correct pages are returned with no arounds.
        pages = utils.get_page_numbers(10, 20, arounds=0)
        expected = ['previous', 1, 2, 3, None, 10, None, 18, 19, 20, 'next']
        self.assertSequenceEqual(expected, pages)

    def test_no_extremes_arounds(self):
        # Ensure the correct pages are returned with no extremes and arounds.
        pages = utils.get_page_numbers(10, 20, extremes=0, arounds=0)
        expected = ['previous', 10, 'next']
        self.assertSequenceEqual(expected, pages)

    def test_one_page(self):
        # Ensure the correct pages are returned if there is only one page.
        pages = utils.get_page_numbers(1, 1)
        expected = [1]
        self.assertSequenceEqual(expected, pages)

    def test_arrows(self):
        # Ensure the pages are returned correctly adding first / last arrows.
        pages = utils.get_page_numbers(5, 10, arrows=True)
        expected = [
            'first', 'previous', 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 'next', 'last']
        self.assertSequenceEqual(expected, pages)

    def test_arrows_first_page(self):
        # Ensure the correct pages are returned if the first page is requested
        # adding first / last arrows.
        pages = utils.get_page_numbers(1, 5, arrows=True)
        expected = [1, 2, 3, 4, 5, 'next', 'last']
        self.assertSequenceEqual(expected, pages)

    def test_arrows_last_page(self):
        # Ensure the correct pages are returned if the last page is requested
        # adding first / last arrows.
        pages = utils.get_page_numbers(5, 5, arrows=True)
        expected = ['first', 'previous', 1, 2, 3, 4, 5]
        self.assertSequenceEqual(expected, pages)


class IterFactorsTest(TestCase):

    def _run_tests(self, test_data):
        for starting_factor, num_factors, expected in test_data:
            factor = utils._iter_factors(starting_factor)
            factors = [next(factor) for idx in range(num_factors)]
            self.assertEqual(expected, factors)

    def test__iter_factors(self):
        # Ensure the correct values are progressively generated.
        test_data = (
            (1, 10, [1, 3, 10, 30, 100, 300, 1000, 3000, 10000, 30000]),
            (5, 10, [5, 15, 50, 150, 500, 1500, 5000, 15000, 50000, 150000]),
            (10, 10, [
                10, 30, 100, 300, 1000, 3000, 10000, 30000, 100000, 300000]),
        )
        self._run_tests(test_data)


class MakeElasticRangeTest(TestCase):

    def _run_tests(self, test_data):
        for begin, end, expected in test_data:
            elastic_range = utils._make_elastic_range(begin, end)
            self.assertEqual(expected, elastic_range)

    def test___make_elastic_range_units(self):
        # Ensure an S-curved range of pages is correctly generated for units.
        test_data = (
            (1, 1, [1]),
            (1, 2, [1, 2]),
            (2, 2, [2]),
            (1, 3, [1, 2, 3]),
            (2, 3, [2, 3]),
            (3, 3, [3]),
            (1, 4, [1, 2, 3, 4]),
            (2, 4, [2, 3, 4]),
            (3, 4, [3, 4]),
            (4, 4, [4]),
            (1, 5, [1, 2, 4, 5]),
            (2, 5, [2, 3, 4, 5]),
            (3, 5, [3, 4, 5]),
            (4, 5, [4, 5]),
            (5, 5, [5]),
            (1, 6, [1, 2, 5, 6]),
            (2, 6, [2, 3, 5, 6]),
            (3, 6, [3, 4, 5, 6]),
            (4, 6, [4, 5, 6]),
            (5, 6, [5, 6]),
            (6, 6, [6]),
            (1, 7, [1, 2, 4, 6, 7]),
            (2, 7, [2, 3, 6, 7]),
            (3, 7, [3, 4, 6, 7]),
            (4, 7, [4, 5, 6, 7]),
            (5, 7, [5, 6, 7]),
            (6, 7, [6, 7]),
            (7, 7, [7]),
            (1, 8, [1, 2, 4, 5, 7, 8]),
            (2, 8, [2, 3, 5, 7, 8]),
            (3, 8, [3, 4, 7, 8]),
            (4, 8, [4, 5, 7, 8]),
            (5, 8, [5, 6, 7, 8]),
            (6, 8, [6, 7, 8]),
            (7, 8, [7, 8]),
            (8, 8, [8]),
            (1, 9, [1, 2, 4, 6, 8, 9]),
            (2, 9, [2, 3, 5, 6, 8, 9]),
            (3, 9, [3, 4, 6, 8, 9]),
            (4, 9, [4, 5, 8, 9]),
            (5, 9, [5, 6, 8, 9]),
            (6, 9, [6, 7, 8, 9]),
            (7, 9, [7, 8, 9]),
            (8, 9, [8, 9]),
            (9, 9, [9]),
            (1, 10, [1, 2, 4, 7, 9, 10]),
            (2, 10, [2, 3, 5, 7, 9, 10]),
            (3, 10, [3, 4, 6, 7, 9, 10]),
            (4, 10, [4, 5, 7, 9, 10]),
            (5, 10, [5, 6, 9, 10]),
            (6, 10, [6, 7, 9, 10]),
            (7, 10, [7, 8, 9, 10]),
            (8, 10, [8, 9, 10]),
            (9, 10, [9, 10]),
            (10, 10, [10]),
        )
        self._run_tests(test_data)

    def test___make_elastic_range_tens(self):
        # Ensure an S-curved range of pages is correctly generated for tens.
        test_data = (
            (1, 20, [1, 2, 4, 17, 19, 20]),
            (5, 20, [5, 6, 8, 17, 19, 20]),
            (10, 20, [10, 11, 13, 17, 19, 20]),
            (11, 20, [11, 12, 14, 17, 19, 20]),
            (1, 50, [1, 2, 4, 11, 40, 47, 49, 50]),
            (10, 50, [10, 11, 13, 20, 40, 47, 49, 50]),
            (25, 50, [25, 26, 28, 35, 40, 47, 49, 50]),
            (1, 100, [1, 2, 4, 11, 31, 70, 90, 97, 99, 100]),
            (25, 100, [25, 26, 28, 35, 55, 70, 90, 97, 99, 100]),
            (50, 100, [50, 51, 53, 60, 90, 97, 99, 100]),
            (75, 100, [75, 76, 78, 85, 90, 97, 99, 100]),
        )
        self._run_tests(test_data)

    def test___make_elastic_range_more(self):
        # An S-curved range of pages is correctly generated for larger numbers.
        test_data = (
            (1, 500, [1, 5, 13, 41, 121, 380, 460, 488, 496, 500]),
            (1, 1000, [1, 10, 28, 91, 271, 730, 910, 973, 991, 1000]),
            (1, 10000, [
                1, 100, 298, 991, 2971, 7030, 9010, 9703, 9901, 10000]),
            (1, 100000, [
                1, 1000, 2998, 9991, 29971, 70030, 90010, 97003, 99001,
                100000]),
            (1, 1000000, [
                1, 10000, 29998, 99991, 299971, 700030, 900010, 970003,
                990001, 1000000]),
        )
        self._run_tests(test_data)


class GetElasticPageNumbersTest(TestCase):

    def _run_tests(self, test_data):
        for current_page, num_pages, expected in test_data:
            pages = utils.get_elastic_page_numbers(current_page, num_pages)
            self.assertSequenceEqual(expected, pages)

    def test_get_elastic_page_numbers_units(self):
        # Ensure the callable returns the expected values for units.
        test_data = (
            (1, 1, [1]),
            (1, 2, [1, 2]),
            (2, 2, [1, 2]),
            (1, 3, [1, 2, 3]),
            (3, 3, [1, 2, 3]),
            (1, 4, [1, 2, 3, 4]),
            (4, 4, [1, 2, 3, 4]),
            (1, 5, [1, 2, 3, 4, 5]),
            (5, 5, [1, 2, 3, 4, 5]),
            (1, 6, [1, 2, 3, 4, 5, 6]),
            (6, 6, [1, 2, 3, 4, 5, 6]),
            (1, 7, [1, 2, 3, 4, 5, 6, 7]),
            (7, 7, [1, 2, 3, 4, 5, 6, 7]),
            (1, 8, [1, 2, 3, 4, 5, 6, 7, 8]),
            (8, 8, [1, 2, 3, 4, 5, 6, 7, 8]),
            (1, 9, [1, 2, 3, 4, 5, 6, 7, 8, 9]),
            (9, 9, [1, 2, 3, 4, 5, 6, 7, 8, 9]),
            (1, 10, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]),
            (6, 10, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]),
            (10, 10, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]),
        )
        self._run_tests(test_data)

    def test_get_elastic_page_numbers_tens(self):
        # Ensure the callable returns the expected values for tens.
        test_data = (
            (1, 11, [
                1, 2, 4, 8, 10, 11, 'next', 'last']),
            (2, 11, [
                'first', 'previous', 1, 2, 3, 5, 8, 10, 11, 'next', 'last']),
            (3, 11, [
                'first', 'previous', 1, 2, 3, 4, 6, 8, 10, 11, 'next',
                'last']),
            (4, 11, [
                'first', 'previous', 1, 2, 3, 4, 5, 7, 8, 10, 11, 'next',
                'last']),
            (5, 11, [
                'first', 'previous', 1, 2, 4, 5, 6, 8, 10, 11, 'next',
                'last']),
            (6, 11, [
                'first', 'previous', 1, 2, 5, 6, 7, 10, 11, 'next', 'last']),
            (7, 11, [
                'first', 'previous', 1, 2, 4, 6, 7, 8, 10, 11, 'next',
                'last']),
            (8, 11, [
                'first', 'previous', 1, 2, 4, 5, 7, 8, 9, 10, 11, 'next',
                'last']),
            (9, 11, [
                'first', 'previous', 1, 2, 4, 6, 8, 9, 10, 11, 'next',
                'last']),
            (10, 11, [
                'first', 'previous', 1, 2, 4, 7, 9, 10, 11, 'next', 'last']),
            (11, 11, ['first', 'previous', 1, 2, 4, 8, 10, 11]),
            (1, 12, [1, 2, 4, 9, 11, 12, 'next', 'last']),
            (2, 12, [
                'first', 'previous', 1, 2, 3, 5, 9, 11, 12, 'next', 'last']),
            (6, 12, [
                'first', 'previous', 1, 2, 5, 6, 7, 9, 11, 12, 'next',
                'last']),
            (7, 12, [
                'first', 'previous', 1, 2, 4, 6, 7, 8, 11, 12, 'next',
                'last']),
            (11, 12, [
                'first', 'previous', 1, 2, 4, 8, 10, 11, 12, 'next', 'last']),
            (12, 12, ['first', 'previous', 1, 2, 4, 9, 11, 12]),
            (1, 15, [1, 2, 4, 12, 14, 15, 'next', 'last']),
            (5, 15, [
                'first', 'previous', 1, 2, 4, 5, 6, 8, 12, 14, 15, 'next',
                'last']),
            (10, 15, [
                'first', 'previous', 1, 2, 4, 7, 9, 10, 11, 14, 15, 'next',
                'last']),
            (15, 15, ['first', 'previous', 1, 2, 4, 12, 14, 15]),
            (1, 100, [1, 2, 4, 11, 31, 70, 90, 97, 99, 100, 'next', 'last']),
            (25, 100, [
                'first', 'previous', 1, 2, 4, 11, 15, 22, 24, 25, 26, 28, 35,
                55, 70, 90, 97, 99, 100, 'next', 'last']),
            (75, 100, [
                'first', 'previous', 1, 2, 4, 11, 31, 45, 65, 72, 74, 75, 76,
                78, 85, 90, 97, 99, 100, 'next', 'last']),
            (100, 100, [
                'first', 'previous', 1, 2, 4, 11, 31, 70, 90, 97, 99, 100]),
        )
        self._run_tests(test_data)

    def test_get_elastic_page_numbers_more(self):
        # Ensure the callable returns the expected values for larger numbers.
        test_data = (
            (1, 500, [
                1, 5, 13, 41, 121, 380, 460, 488, 496, 500, 'next', 'last']),
            (150, 500, [
                'first', 'previous', 1, 2, 4, 11, 31, 120, 140, 147, 149, 150,
                153, 159, 180, 240, 410, 470, 491, 497, 500, 'next', 'last']),
            (350, 500, [
                'first', 'previous', 1, 4, 10, 31, 91, 260, 320, 341, 347, 350,
                351, 353, 360, 380, 470, 490, 497, 499, 500, 'next', 'last']),
            (500, 500, [
                'first', 'previous', 1, 5, 13, 41, 121, 380, 460, 488, 496,
                500]),
            (100, 1000, [
                'first', 'previous', 1, 2, 4, 11, 31, 70, 90, 97, 99, 100, 109,
                127, 190, 370, 730, 910, 973, 991, 1000, 'next', 'last']),
            (1000, 10000, [
                'first', 'previous', 1, 10, 28, 91, 271, 730, 910, 973, 991,
                1000, 1090, 1270, 1900, 3700, 7300, 9100, 9730, 9910, 10000,
                'next', 'last']),
            (10000, 100000, [
                'first', 'previous', 1, 100, 298, 991, 2971, 7030, 9010, 9703,
                9901, 10000, 10900, 12700, 19000, 37000, 73000, 91000, 97300,
                99100, 100000, 'next', 'last']),
            (100000, 1000000, [
                'first', 'previous', 1, 1000, 2998, 9991, 29971, 70030, 90010,
                97003, 99001, 100000, 109000, 127000, 190000, 370000, 730000,
                910000, 973000, 991000, 1000000, 'next', 'last']),
        )
        self._run_tests(test_data)


class GetQuerystringForPageTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def test_querystring(self):
        # Ensure the querystring is correctly generated from request.
        request = self.factory.get('/')
        querystring = utils.get_querystring_for_page(request, 2, 'mypage')
        self.assertEqual('?mypage=2', querystring)

    def test_default_page(self):
        # Ensure the querystring is empty for the default page.
        request = self.factory.get('/')
        querystring = utils.get_querystring_for_page(
            request, 3, 'mypage', default_number=3)
        self.assertEqual('', querystring)

    def test_composition(self):
        # Ensure existing querystring is correctly preserved.
        request = self.factory.get('/?mypage=1&foo=bar')
        querystring = utils.get_querystring_for_page(request, 4, 'mypage')
        self.assertIn('mypage=4', querystring)
        self.assertIn('foo=bar', querystring)

    def test_querystring_key(self):
        # The querystring key is deleted from the querystring if present.
        request = self.factory.get('/?querystring_key=mykey')
        querystring = utils.get_querystring_for_page(request, 5, 'mypage')
        self.assertEqual('?mypage=5', querystring)


class NormalizePageNumberTest(TestCase):

    page_range = [1, 2, 3, 4]

    def test_in_range(self):
        # Ensure the correct page number is returned when the requested
        # negative index is in range.
        page_numbers = [-1, -2, -3, -4]
        expected_results = reversed(self.page_range)
        for page_number, expected in zip(page_numbers, expected_results):
            result = utils.normalize_page_number(page_number, self.page_range)
            self.assertEqual(expected, result)

    def test_out_of_range(self):
        # Ensure the page number 1 returned when the requested negative index
        # is out of range.
        result = utils.normalize_page_number(-5, self.page_range)
        self.assertEqual(self.page_range[0], result)

########NEW FILE########
__FILENAME__ = test_views
"""View tests."""

from __future__ import unicode_literals

from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.test import TestCase
from django.test.client import RequestFactory

from endless_pagination import views
from endless_pagination.tests import (
    make_model_instances,
    TestModel,
)


class CustomizedListView(views.AjaxListView):
    """An AjaxListView subclass overriding the *get* method."""

    def get(self, request, *args, **kwargs):
        self.object_list = self.queryset
        context = self.get_context_data(object_list=self.object_list)
        return self.render_to_response(context)


class AjaxListViewTest(TestCase):

    model_page_template = 'endless_pagination/testmodel_list_page.html'
    model_template_name = 'endless_pagination/testmodel_list.html'
    page_template = 'page_template.html'
    template_name = 'template.html'
    url = '/?page=2'

    def setUp(self):
        factory = RequestFactory()
        self.request = factory.get(self.url)
        self.ajax_request = factory.get(
            self.url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def check_response(self, response, template_name, object_list):
        """Execute several assertions on the response.

        Check that the response has a successful status code,
        uses ``template_name`` and contains ``object_list``.
        """
        self.assertEqual(200, response.status_code)
        self.assertSequenceEqual([template_name], response.template_name)
        self.assertSequenceEqual(
            list(object_list), response.context_data['object_list'])

    def make_view(self, *args, **kwargs):
        """Return an instance of AjaxListView."""
        return views.AjaxListView.as_view(*args, **kwargs)

    def test_list(self):
        # Ensure the view correctly adds the list to context.
        view = self.make_view(
            queryset=range(30),
            template_name=self.template_name,
            page_template=self.page_template,
        )
        response = view(self.request)
        self.check_response(response, self.template_name, range(30))

    def test_list_ajax(self):
        # Ensure the list view switches templates when the request is Ajax.
        view = self.make_view(
            queryset=range(30),
            template_name=self.template_name,
            page_template=self.page_template,
        )
        response = view(self.ajax_request)
        self.check_response(response, self.page_template, range(30))

    def test_queryset(self):
        # Ensure the view correctly adds the queryset to context.
        queryset = make_model_instances(30)
        view = self.make_view(queryset=queryset)
        response = view(self.request)
        self.check_response(response, self.model_template_name, queryset)

    def test_queryset_ajax(self):
        # Ensure the queryset view switches templates when the request is Ajax.
        queryset = make_model_instances(30)
        view = self.make_view(queryset=queryset)
        response = view(self.ajax_request)
        self.check_response(response, self.model_page_template, queryset)

    def test_model(self):
        # Ensure the view correctly uses the model to generate the template.
        queryset = make_model_instances(30)
        view = self.make_view(model=TestModel)
        response = view(self.request)
        self.check_response(response, self.model_template_name, queryset)

    def test_model_ajax(self):
        # Ensure the model view switches templates when the request is Ajax.
        queryset = make_model_instances(30)
        view = self.make_view(model=TestModel)
        response = view(self.ajax_request)
        self.check_response(response, self.model_page_template, queryset)

    def test_missing_queryset_or_model(self):
        # An error is raised if both queryset and model are not provided.
        view = self.make_view()
        with self.assertRaises(ImproperlyConfigured) as cm:
            view(self.request)
        self.assertIn('queryset', str(cm.exception))
        self.assertIn('model', str(cm.exception))

    def test_missing_page_template(self):
        # An error is raised if the ``page_template`` name is not provided.
        view = self.make_view(queryset=range(30))
        with self.assertRaises(ImproperlyConfigured) as cm:
            view(self.request)
        self.assertIn('page_template', str(cm.exception))

    def test_do_not_allow_empty(self):
        # An error is raised if the list is empty and ``allow_empty`` is
        # set to False.
        view = self.make_view(model=TestModel, allow_empty=False)
        with self.assertRaises(Http404) as cm:
            view(self.request)
        self.assertIn('allow_empty', str(cm.exception))

    def test_view_in_context(self):
        # Ensure the view is included in the template context.
        view = self.make_view(
            queryset=range(30),
            page_template=self.page_template,
        )
        response = view(self.request)
        view_instance = response.context_data['view']
        self.assertIsInstance(view_instance, views.AjaxListView)

    def test_customized_view(self):
        # Ensure the customized view correctly adds the queryset to context.
        queryset = make_model_instances(30)
        view = CustomizedListView.as_view(queryset=queryset)
        response = view(self.request)
        self.check_response(response, self.model_template_name, queryset)

########NEW FILE########
__FILENAME__ = utils
"""Django Endless Pagination utility functions."""

from __future__ import unicode_literals
import sys

from endless_pagination import exceptions
from endless_pagination.settings import (
    DEFAULT_CALLABLE_AROUNDS,
    DEFAULT_CALLABLE_ARROWS,
    DEFAULT_CALLABLE_EXTREMES,
    PAGE_LABEL,
)


# Handle the Python 2 to 3 migration.
if sys.version_info[0] >= 3:
    PYTHON3 = True
    text = str
else:
    PYTHON3 = False
    # Avoid lint errors under Python 3.
    text = unicode  # NOQA


def get_data_from_context(context):
    """Get the django paginator data object from the given *context*.

    The context is a dict-like object. If the context key ``endless``
    is not found, a *PaginationError* is raised.
    """
    try:
        return context['endless']
    except KeyError:
        raise exceptions.PaginationError(
            'Cannot find endless data in context.')


def get_page_number_from_request(
        request, querystring_key=PAGE_LABEL, default=1):
    """Retrieve the current page number from *GET* or *POST* data.

    If the page does not exists in *request*, or is not a number,
    then *default* number is returned.
    """
    try:
        return int(request.REQUEST[querystring_key])
    except (KeyError, TypeError, ValueError):
        return default


def get_page_numbers(
        current_page, num_pages, extremes=DEFAULT_CALLABLE_EXTREMES,
        arounds=DEFAULT_CALLABLE_AROUNDS, arrows=DEFAULT_CALLABLE_ARROWS):
    """Default callable for page listing.

    Produce a Digg-style pagination.
    """
    page_range = range(1, num_pages + 1)
    pages = []
    if current_page != 1:
        if arrows:
            pages.append('first')
        pages.append('previous')

    # Get first and last pages (extremes).
    first = page_range[:extremes]
    pages.extend(first)
    last = page_range[-extremes:]

    # Get the current pages (arounds).
    current_start = current_page - 1 - arounds
    if current_start < 0:
        current_start = 0
    current_end = current_page + arounds
    if current_end > num_pages:
        current_end = num_pages
    current = page_range[current_start:current_end]

    # Mix first with current pages.
    to_add = current
    if extremes:
        diff = current[0] - first[-1]
        if diff > 1:
            pages.append(None)
        elif diff < 1:
            to_add = current[abs(diff) + 1:]
    pages.extend(to_add)

    # Mix current with last pages.
    if extremes:
        diff = last[0] - current[-1]
        to_add = last
        if diff > 1:
            pages.append(None)
        elif diff < 1:
            to_add = last[abs(diff) + 1:]
        pages.extend(to_add)

    if current_page != num_pages:
        pages.append('next')
        if arrows:
            pages.append('last')
    return pages


def _iter_factors(starting_factor=1):
    """Generator yielding something like 1, 3, 10, 30, 100, 300 etc.

    The series starts from starting_factor.
    """
    while True:
        yield starting_factor
        yield starting_factor * 3
        starting_factor *= 10


def _make_elastic_range(begin, end):
    """Generate an S-curved range of pages.

    Start from both left and right, adding exponentially growing indexes,
    until the two trends collide.
    """
    # Limit growth for huge numbers of pages.
    starting_factor = max(1, (end - begin) // 100)
    factor = _iter_factors(starting_factor)
    left_half, right_half = [], []
    left_val, right_val = begin, end
    right_val = end
    while left_val < right_val:
        left_half.append(left_val)
        right_half.append(right_val)
        next_factor = next(factor)
        left_val = begin + next_factor
        right_val = end - next_factor
    # If the trends happen to meet exactly at one point, retain it.
    if left_val == right_val:
        left_half.append(left_val)
    right_half.reverse()
    return left_half + right_half


def get_elastic_page_numbers(current_page, num_pages):
    """Alternative callable for page listing.

    Produce an adaptive pagination, useful for big numbers of pages, by
    splitting the num_pages ranges in two parts at current_page. Each part
    will have its own S-curve.
    """
    if num_pages <= 10:
        return list(range(1, num_pages + 1))
    if current_page == 1:
        pages = [1]
    else:
        pages = ['first', 'previous']
        pages.extend(_make_elastic_range(1, current_page))
    if current_page != num_pages:
        pages.extend(_make_elastic_range(current_page, num_pages)[1:])
        pages.extend(['next', 'last'])
    return pages


def get_querystring_for_page(
        request, page_number, querystring_key, default_number=1):
    """Return a querystring pointing to *page_number*."""
    querydict = request.GET.copy()
    querydict[querystring_key] = page_number
    # For the default page number (usually 1) the querystring is not required.
    if page_number == default_number:
        del querydict[querystring_key]
    if 'querystring_key' in querydict:
        del querydict['querystring_key']
    if querydict:
        return '?' + querydict.urlencode()
    return ''


def normalize_page_number(page_number, page_range):
    """Handle a negative *page_number*.

    Return a positive page number contained in *page_range*.
    If the negative index is out of range, return the page number 1.
    """
    try:
        return page_range[page_number]
    except IndexError:
        return page_range[0]


class UnicodeMixin(object):
    """Mixin class to handle defining the proper unicode and string methods."""

    if PYTHON3:
        def __str__(self):
            return self.__unicode__()

########NEW FILE########
__FILENAME__ = views
"""Django Endless Pagination class-based views."""

from __future__ import unicode_literals

from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.utils.encoding import smart_str
from django.utils.translation import ugettext as _
from django.views.generic.base import View
from django.views.generic.list import MultipleObjectTemplateResponseMixin

from endless_pagination.settings import PAGE_LABEL


class MultipleObjectMixin(object):

    allow_empty = True
    context_object_name = None
    model = None
    queryset = None

    def get_queryset(self):
        """Get the list of items for this view.

        This must be an interable, and may be a queryset
        (in which qs-specific behavior will be enabled).

        See original in ``django.views.generic.list.MultipleObjectMixin``.
        """
        if self.queryset is not None:
            queryset = self.queryset
            if hasattr(queryset, '_clone'):
                queryset = queryset._clone()
        elif self.model is not None:
            queryset = self.model._default_manager.all()
        else:
            msg = '{0} must define ``queryset`` or ``model``'
            raise ImproperlyConfigured(msg.format(self.__class__.__name__))
        return queryset

    def get_allow_empty(self):
        """Returns True if the view should display empty lists.

        Return False if a 404 should be raised instead.

        See original in ``django.views.generic.list.MultipleObjectMixin``.
        """
        return self.allow_empty

    def get_context_object_name(self, object_list):
        """Get the name of the item to be used in the context.

        See original in ``django.views.generic.list.MultipleObjectMixin``.
        """
        if self.context_object_name:
            return self.context_object_name
        elif hasattr(object_list, 'model'):
            object_name = object_list.model._meta.object_name.lower()
            return smart_str('{0}_list'.format(object_name))
        else:
            return None

    def get_context_data(self, **kwargs):
        """Get the context for this view.

        Also adds the *page_template* variable in the context.

        If the *page_template* is not given as a kwarg of the *as_view*
        method then it is generated using app label, model name
        (obviously if the list is a queryset), *self.template_name_suffix*
        and *self.page_template_suffix*.

        For instance, if the list is a queryset of *blog.Entry*,
        the template will be ``blog/entry_list_page.html``.
        """
        queryset = kwargs.pop('object_list')
        page_template = kwargs.pop('page_template', None)

        context_object_name = self.get_context_object_name(queryset)
        context = {'object_list': queryset, 'view': self}
        context.update(kwargs)
        if context_object_name is not None:
            context[context_object_name] = queryset

        if page_template is None:
            if hasattr(queryset, 'model'):
                page_template = self.get_page_template(**kwargs)
            else:
                raise ImproperlyConfigured(
                    'AjaxListView requires a page_template')
        context['page_template'] = self.page_template = page_template

        return context


class BaseListView(MultipleObjectMixin, View):

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        allow_empty = self.get_allow_empty()
        if not allow_empty and len(self.object_list) == 0:
            msg = _('Empty list and ``%(class_name)s.allow_empty`` is False.')
            raise Http404(msg % {'class_name': self.__class__.__name__})
        context = self.get_context_data(
            object_list=self.object_list, page_template=self.page_template)
        return self.render_to_response(context)


class AjaxMultipleObjectTemplateResponseMixin(
        MultipleObjectTemplateResponseMixin):

    key = PAGE_LABEL
    page_template = None
    page_template_suffix = '_page'
    template_name_suffix = '_list'

    def get_page_template(self, **kwargs):
        """Return the template name used for this request.

        Only called if *page_template* is not given as a kwarg of
        *self.as_view*.
        """
        opts = self.object_list.model._meta
        return '{0}/{1}{2}{3}.html'.format(
            opts.app_label,
            opts.object_name.lower(),
            self.template_name_suffix,
            self.page_template_suffix,
        )

    def get_template_names(self):
        """Switch the templates for Ajax requests."""
        request = self.request
        querystring_key = request.REQUEST.get('querystring_key', PAGE_LABEL)
        if request.is_ajax() and querystring_key == self.key:
            return [self.page_template]
        return super(
            AjaxMultipleObjectTemplateResponseMixin, self).get_template_names()


class AjaxListView(AjaxMultipleObjectTemplateResponseMixin, BaseListView):
    """Allows Ajax pagination of a list of objects.

    You can use this class-based view in place of *ListView* in order to
    recreate the behaviour of the *page_template* decorator.

    For instance, assume you have this code (taken from Django docs)::

        from django.conf.urls import patterns
        from django.views.generic import ListView

        from books.models import Publisher

        urlpatterns = patterns('',
            (r'^publishers/$', ListView.as_view(model=Publisher)),
        )

    You want to Ajax paginate publishers, so, as seen, you need to switch
    the template if the request is Ajax and put the page template
    into the context as a variable named *page_template*.

    This is straightforward, you only need to replace the view class, e.g.::

        from django.conf.urls import patterns

        from books.models import Publisher

        from endless_pagination.views import AjaxListView

        urlpatterns = patterns('',
            (r'^publishers/$', AjaxListView.as_view(model=Publisher)),
        )

    NOTE: Django >= 1.3 is required to use this view.
    """

########NEW FILE########
__FILENAME__ = develop
"""Create a development and testing environment using a virtualenv."""

from __future__ import unicode_literals
import os
import subprocess
import sys


if sys.version_info[0] >= 3:
    VENV_NAME = '.venv3'
    # FIXME: running 2to3 on django-nose will no longer be required once
    # the project supports Python 3 (bug #16).
    PATCH_DJANGO_NOSE = True
else:
    VENV_NAME = '.venv'
    PATCH_DJANGO_NOSE = False


TESTS = os.path.abspath(os.path.dirname(__file__))
REQUIREMENTS = os.path.join(TESTS, 'requirements.pip')
WITH_VENV = os.path.join(TESTS, 'with_venv.sh')
VENV = os.path.abspath(os.path.join(TESTS, '..', VENV_NAME))


def call(*args):
    """Simple ``subprocess.call`` wrapper."""
    if subprocess.call(args):
        raise SystemExit('Error running {0}.'.format(args))


def pip_install(*args):
    """Install packages using pip inside the virtualenv."""
    call(WITH_VENV, VENV_NAME, 'pip', 'install', '--use-mirrors', *args)


def patch_django_nose():
    """Run 2to3 on django-nose and remove ``import new`` from its runner."""
    # FIXME: delete once django-nose supports Python 3 (bug #16).
    python = 'python' + '.'.join(map(str, sys.version_info[:2]))
    django_nose = os.path.join(
        VENV, 'lib', python, 'site-packages', 'django_nose')
    call('2to3', '-w', '--no-diffs', django_nose)
    with open(os.path.join(django_nose, 'runner.py'), 'r+') as f:
        lines = [line for line in f.readlines() if 'import new' not in line]
        f.seek(0)
        f.truncate()
        f.writelines(lines)


if __name__ == '__main__':
    call('virtualenv', '--distribute', '-p', sys.executable, VENV)
    pip_install('-r', REQUIREMENTS)
    # FIXME: delete from now on once django-nose supports Python 3  (bug #16).
    if PATCH_DJANGO_NOSE:
        patch_django_nose()

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python

from __future__ import unicode_literals
import os
import sys

from django.core.management import execute_from_command_line


if __name__ == '__main__':
    root = os.path.join(os.path.dirname(__file__), '..')
    sys.path.append(os.path.abspath(root))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = context_processors
"""Navigation bar context processor."""

from __future__ import unicode_literals
import platform

import django
from django.core.urlresolvers import reverse

import endless_pagination


VOICES = (
    # Name and label pairs.
    ('complete', 'Complete example'),
    ('digg', 'Digg-style'),
    ('twitter', 'Twitter-style'),
    ('onscroll', 'On scroll'),
    ('multiple', 'Multiple'),
    ('callbacks', 'Callbacks'),
    ('chunks', 'On scroll/chunks'),
)


def navbar(request):
    """Generate a list of voices for the navigation bar."""
    voice_list = []
    current_path = request.path
    for name, label in VOICES:
        path = reverse(name)
        voice_list.append({
            'label': label,
            'path': path,
            'is_active': path == current_path,
        })
    return {'navbar': voice_list}


def versions(request):
    """Add to context the version numbers of relevant apps."""
    values = (
        ('Python', platform.python_version()),
        ('Django', django.get_version()),
        ('Endless Pagination', endless_pagination.get_version()),
    )
    return {'versions': values}

########NEW FILE########
__FILENAME__ = urls
"""Test project URL patterns."""

from __future__ import unicode_literals

from django.conf.urls import patterns, url
from django.views.generic import TemplateView

from endless_pagination.decorators import (
    page_template,
    page_templates,
)

from project.views import generic


# Avoid lint errors for the following Django idiom: flake8: noqa.
urlpatterns = patterns('',
    url(r'^$',
        TemplateView.as_view(template_name="home.html"),
        name='home'),
    url(r'^complete/$',
        page_templates({
            'complete/objects_page.html': 'objects-page',
            'complete/items_page.html': 'items-page',
            'complete/entries_page.html': 'entries-page',
            'complete/articles_page.html': 'articles-page',
        })(generic),
        {'template': 'complete/index.html', 'number': 21},
        name='complete'),
    url(r'^digg/$',
        page_template('digg/page.html')(generic),
        {'template': 'digg/index.html'},
        name='digg'),
    url(r'^twitter/$',
        page_template('twitter/page.html')(generic),
        {'template': 'twitter/index.html'},
        name='twitter'),
    url(r'^onscroll/$',
        page_template('onscroll/page.html')(generic),
        {'template': 'onscroll/index.html'},
        name='onscroll'),
    url(r'^chunks/$',
        page_templates({
            'chunks/objects_page.html': None,
            'chunks/items_page.html': 'items-page',
        })(generic),
        {'template': 'chunks/index.html', 'number': 50},
        name='chunks'),
    url(r'^multiple/$',
        page_templates({
            'multiple/objects_page.html': 'objects-page',
            'multiple/items_page.html': 'items-page',
            'multiple/entries_page.html': 'entries-page',
        })(generic),
        {'template': 'multiple/index.html', 'number': 21},
        name='multiple'),
    url(r'^callbacks/$',
        page_template('callbacks/page.html')(generic),
        {'template': 'callbacks/index.html'},
        name='callbacks'),
)

########NEW FILE########
__FILENAME__ = views
"""Test project views."""

from __future__ import unicode_literals

from django.shortcuts import render


LOREM = """Lorem ipsum dolor sit amet, consectetur adipisicing elit,
    sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
    Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris
    nisi ut aliquip ex ea commodo consequat.
"""


def _make(title, number):
    """Make a *number* of items."""
    return [
        {'title': '{0} {1}'.format(title, i + 1), 'contents': LOREM}
        for i in range(number)
    ]


def generic(request, extra_context=None, template=None, number=50):
    context = {
        'objects': _make('Object', number),
        'items': _make('Item', number),
        'entries': _make('Entry', number),
        'articles': _make('Article', number),
    }
    if extra_context is not None:
        context.update(extra_context)
    return render(request, template, context)

########NEW FILE########
__FILENAME__ = settings
"""Settings file for the Django project used for tests."""

import os

from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS


PROJECT_NAME = 'project'

# Base paths.
ROOT = os.path.abspath(os.path.dirname(__file__))
PROJECT = os.path.join(ROOT, PROJECT_NAME)

# Django configuration.
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3'}}
DEBUG = TEMPLATE_DEBUG = True
INSTALLED_APPS = (
    'django.contrib.staticfiles',
    'endless_pagination',
    PROJECT_NAME,
)
LANGUAGE_CODE = os.getenv('ENDLESS_PAGINATION_LANGUAGE_CODE', 'en-us')
ROOT_URLCONF = PROJECT_NAME + '.urls'
SECRET_KEY = os.getenv('ENDLESS_PAGINATION_SECRET_KEY', 'secret')
SITE_ID = 1
STATIC_ROOT = os.path.join(PROJECT, 'static')
STATIC_URL = '/static/'
TEMPLATE_CONTEXT_PROCESSORS += (
    'django.core.context_processors.request',
    PROJECT_NAME + '.context_processors.navbar',
    PROJECT_NAME + '.context_processors.versions',
)
TEMPLATE_DIRS = os.path.join(PROJECT, 'templates')

# Testing.
NOSE_ARGS = (
    '--verbosity=2',
    '--with-coverage',
    '--cover-package=endless_pagination',
)
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

########NEW FILE########
