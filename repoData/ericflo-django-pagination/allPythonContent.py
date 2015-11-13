__FILENAME__ = middleware
def get_page(self):
    """
    A function which will be monkeypatched onto the request to get the current
    integer representing the current page.
    """
    try:
        return int(self.REQUEST['page'])
    except (KeyError, ValueError, TypeError):
        return 1

class PaginationMiddleware(object):
    """
    Inserts a variable representing the current page onto the request object if
    it exists in either **GET** or **POST** portions of the request.
    """
    def process_request(self, request):
        request.__class__.page = property(get_page)
########NEW FILE########
__FILENAME__ = models


########NEW FILE########
__FILENAME__ = paginator
from django.core.paginator import Paginator, Page, PageNotAnInteger, EmptyPage

class InfinitePaginator(Paginator):
    """
    Paginator designed for cases when it's not important to know how many total
    pages.  This is useful for any object_list that has no count() method or can
    be used to improve performance for MySQL by removing counts.

    The orphans parameter has been removed for simplicity and there's a link
    template string for creating the links to the next and previous pages.
    """

    def __init__(self, object_list, per_page, allow_empty_first_page=True,
        link_template='/page/%d/'):
        orphans = 0 # no orphans
        super(InfinitePaginator, self).__init__(object_list, per_page, orphans,
            allow_empty_first_page)
        # no count or num pages
        del self._num_pages, self._count
        # bonus links
        self.link_template = link_template

    def validate_number(self, number):
        """
        Validates the given 1-based page number.
        """
        try:
            number = int(number)
        except ValueError:
            raise PageNotAnInteger('That page number is not an integer')
        if number < 1:
            raise EmptyPage('That page number is less than 1')
        return number

    def page(self, number):
        """
        Returns a Page object for the given 1-based page number.
        """
        number = self.validate_number(number)
        bottom = (number - 1) * self.per_page
        top = bottom + self.per_page
        page_items = self.object_list[bottom:top]
        # check moved from validate_number
        if not page_items:
            if number == 1 and self.allow_empty_first_page:
                pass
            else:
                raise EmptyPage('That page contains no results')
        return InfinitePage(page_items, number, self)

    def _get_count(self):
        """
        Returns the total number of objects, across all pages.
        """
        raise NotImplementedError
    count = property(_get_count)

    def _get_num_pages(self):
        """
        Returns the total number of pages.
        """
        raise NotImplementedError
    num_pages = property(_get_num_pages)

    def _get_page_range(self):
        """
        Returns a 1-based range of pages for iterating through within
        a template for loop.
        """
        raise NotImplementedError
    page_range = property(_get_page_range)


class InfinitePage(Page):

    def __repr__(self):
        return '<Page %s>' % self.number

    def has_next(self):
        """
        Checks for one more item than last on this page.
        """
        try:
            next_item = self.paginator.object_list[
                self.number * self.paginator.per_page]
        except IndexError:
            return False
        return True

    def end_index(self):
        """
        Returns the 1-based index of the last object on this page,
        relative to total objects found (hits).
        """
        return ((self.number - 1) * self.paginator.per_page +
            len(self.object_list))

    #Bonus methods for creating links

    def next_link(self):
        if self.has_next():
            return self.paginator.link_template % (self.number + 1)
        return None

    def previous_link(self):
        if self.has_previous():
            return self.paginator.link_template % (self.number - 1)
        return None

class FinitePaginator(InfinitePaginator):
    """
    Paginator for cases when the list of items is already finite.

    A good example is a list generated from an API call. This is a subclass
    of InfinitePaginator because we have no idea how many items exist in the
    full collection.

    To accurately determine if the next page exists, a FinitePaginator MUST be
    created with an object_list_plus that may contain more items than the
    per_page count.  Typically, you'll have an object_list_plus with one extra
    item (if there's a next page).  You'll also need to supply the offset from
    the full collection in order to get the page start_index.

    This is a very silly class but useful if you love the Django pagination
    conventions.
    """

    def __init__(self, object_list_plus, per_page, offset=None,
        allow_empty_first_page=True, link_template='/page/%d/'):
        super(FinitePaginator, self).__init__(object_list_plus, per_page,
            allow_empty_first_page, link_template)
        self.offset = offset

    def validate_number(self, number):
        super(FinitePaginator, self).validate_number(number)
        # check for an empty list to see if the page exists
        if not self.object_list:
            if number == 1 and self.allow_empty_first_page:
                pass
            else:
                raise EmptyPage('That page contains no results')
        return number

    def page(self, number):
        """
        Returns a Page object for the given 1-based page number.
        """
        number = self.validate_number(number)
        # remove the extra item(s) when creating the page
        page_items = self.object_list[:self.per_page]
        return FinitePage(page_items, number, self)

class FinitePage(InfinitePage):

    def has_next(self):
        """
        Checks for one more item than last on this page.
        """
        try:
            next_item = self.paginator.object_list[self.paginator.per_page]
        except IndexError:
            return False
        return True

    def start_index(self):
        """
        Returns the 1-based index of the first object on this page,
        relative to total objects in the paginator.
        """
        ## TODO should this holler if you haven't defined the offset?
        return self.paginator.offset
########NEW FILE########
__FILENAME__ = pagination_tags
try:
    set
except NameError:
    from sets import Set as set

from django import template
from django.http import Http404
from django.core.paginator import Paginator, InvalidPage
from django.conf import settings

register = template.Library()

DEFAULT_PAGINATION = getattr(settings, 'PAGINATION_DEFAULT_PAGINATION', 20)
DEFAULT_WINDOW = getattr(settings, 'PAGINATION_DEFAULT_WINDOW', 4)
DEFAULT_ORPHANS = getattr(settings, 'PAGINATION_DEFAULT_ORPHANS', 0)
INVALID_PAGE_RAISES_404 = getattr(settings,
    'PAGINATION_INVALID_PAGE_RAISES_404', False)

def do_autopaginate(parser, token):
    """
    Splits the arguments to the autopaginate tag and formats them correctly.
    """
    split = token.split_contents()
    as_index = None
    context_var = None
    for i, bit in enumerate(split):
        if bit == 'as':
            as_index = i
            break
    if as_index is not None:
        try:
            context_var = split[as_index + 1]
        except IndexError:
            raise template.TemplateSyntaxError("Context variable assignment " +
                "must take the form of {%% %r object.example_set.all ... as " +
                "context_var_name %%}" % split[0])
        del split[as_index:as_index + 2]
    if len(split) == 2:
        return AutoPaginateNode(split[1])
    elif len(split) == 3:
        return AutoPaginateNode(split[1], paginate_by=split[2], 
            context_var=context_var)
    elif len(split) == 4:
        try:
            orphans = int(split[3])
        except ValueError:
            raise template.TemplateSyntaxError(u'Got %s, but expected integer.'
                % split[3])
        return AutoPaginateNode(split[1], paginate_by=split[2], orphans=orphans,
            context_var=context_var)
    else:
        raise template.TemplateSyntaxError('%r tag takes one required ' +
            'argument and one optional argument' % split[0])

class AutoPaginateNode(template.Node):
    """
    Emits the required objects to allow for Digg-style pagination.
    
    First, it looks in the current context for the variable specified, and using
    that object, it emits a simple ``Paginator`` and the current page object 
    into the context names ``paginator`` and ``page_obj``, respectively.
    
    It will then replace the variable specified with only the objects for the
    current page.
    
    .. note::
        
        It is recommended to use *{% paginate %}* after using the autopaginate
        tag.  If you choose not to use *{% paginate %}*, make sure to display the
        list of available pages, or else the application may seem to be buggy.
    """
    def __init__(self, queryset_var, paginate_by=DEFAULT_PAGINATION,
        orphans=DEFAULT_ORPHANS, context_var=None):
        self.queryset_var = template.Variable(queryset_var)
        if isinstance(paginate_by, int):
            self.paginate_by = paginate_by
        else:
            self.paginate_by = template.Variable(paginate_by)
        self.orphans = orphans
        self.context_var = context_var

    def render(self, context):
        key = self.queryset_var.var
        value = self.queryset_var.resolve(context)
        if isinstance(self.paginate_by, int):
            paginate_by = self.paginate_by
        else:
            paginate_by = self.paginate_by.resolve(context)
        paginator = Paginator(value, paginate_by, self.orphans)
        try:
            page_obj = paginator.page(context['request'].page)
        except InvalidPage:
            if INVALID_PAGE_RAISES_404:
                raise Http404('Invalid page requested.  If DEBUG were set to ' +
                    'False, an HTTP 404 page would have been shown instead.')
            context[key] = []
            context['invalid_page'] = True
            return u''
        if self.context_var is not None:
            context[self.context_var] = page_obj.object_list
        else:
            context[key] = page_obj.object_list
        context['paginator'] = paginator
        context['page_obj'] = page_obj
        return u''


def paginate(context, window=DEFAULT_WINDOW, hashtag=''):
    """
    Renders the ``pagination/pagination.html`` template, resulting in a
    Digg-like display of the available pages, given the current page.  If there
    are too many pages to be displayed before and after the current page, then
    elipses will be used to indicate the undisplayed gap between page numbers.
    
    Requires one argument, ``context``, which should be a dictionary-like data
    structure and must contain the following keys:
    
    ``paginator``
        A ``Paginator`` or ``QuerySetPaginator`` object.
    
    ``page_obj``
        This should be the result of calling the page method on the 
        aforementioned ``Paginator`` or ``QuerySetPaginator`` object, given
        the current page.
    
    This same ``context`` dictionary-like data structure may also include:
    
    ``getvars``
        A dictionary of all of the **GET** parameters in the current request.
        This is useful to maintain certain types of state, even when requesting
        a different page.
        """
    try:
        paginator = context['paginator']
        page_obj = context['page_obj']
        page_range = paginator.page_range
        # Calculate the record range in the current page for display.
        records = {'first': 1 + (page_obj.number - 1) * paginator.per_page}
        records['last'] = records['first'] + paginator.per_page - 1
        if records['last'] + paginator.orphans >= paginator.count:
            records['last'] = paginator.count
        # First and last are simply the first *n* pages and the last *n* pages,
        # where *n* is the current window size.
        first = set(page_range[:window])
        last = set(page_range[-window:])
        # Now we look around our current page, making sure that we don't wrap
        # around.
        current_start = page_obj.number-1-window
        if current_start < 0:
            current_start = 0
        current_end = page_obj.number-1+window
        if current_end < 0:
            current_end = 0
        current = set(page_range[current_start:current_end])
        pages = []
        # If there's no overlap between the first set of pages and the current
        # set of pages, then there's a possible need for elusion.
        if len(first.intersection(current)) == 0:
            first_list = list(first)
            first_list.sort()
            second_list = list(current)
            second_list.sort()
            pages.extend(first_list)
            diff = second_list[0] - first_list[-1]
            # If there is a gap of two, between the last page of the first
            # set and the first page of the current set, then we're missing a
            # page.
            if diff == 2:
                pages.append(second_list[0] - 1)
            # If the difference is just one, then there's nothing to be done,
            # as the pages need no elusion and are correct.
            elif diff == 1:
                pass
            # Otherwise, there's a bigger gap which needs to be signaled for
            # elusion, by pushing a None value to the page list.
            else:
                pages.append(None)
            pages.extend(second_list)
        else:
            unioned = list(first.union(current))
            unioned.sort()
            pages.extend(unioned)
        # If there's no overlap between the current set of pages and the last
        # set of pages, then there's a possible need for elusion.
        if len(current.intersection(last)) == 0:
            second_list = list(last)
            second_list.sort()
            diff = second_list[0] - pages[-1]
            # If there is a gap of two, between the last page of the current
            # set and the first page of the last set, then we're missing a 
            # page.
            if diff == 2:
                pages.append(second_list[0] - 1)
            # If the difference is just one, then there's nothing to be done,
            # as the pages need no elusion and are correct.
            elif diff == 1:
                pass
            # Otherwise, there's a bigger gap which needs to be signaled for
            # elusion, by pushing a None value to the page list.
            else:
                pages.append(None)
            pages.extend(second_list)
        else:
            differenced = list(last.difference(current))
            differenced.sort()
            pages.extend(differenced)
        to_return = {
            'MEDIA_URL': settings.MEDIA_URL,
            'pages': pages,
            'records': records,
            'page_obj': page_obj,
            'paginator': paginator,
            'hashtag': hashtag,
            'is_paginated': paginator.count > paginator.per_page,
        }
        if 'request' in context:
            getvars = context['request'].GET.copy()
            if 'page' in getvars:
                del getvars['page']
            if len(getvars.keys()) > 0:
                to_return['getvars'] = "&%s" % getvars.urlencode()
            else:
                to_return['getvars'] = ''
        return to_return
    except KeyError, AttributeError:
        return {}

register.inclusion_tag('pagination/pagination.html', takes_context=True)(
    paginate)
register.tag('autopaginate', do_autopaginate)

########NEW FILE########
__FILENAME__ = tests
"""
>>> from django.core.paginator import Paginator
>>> from pagination.templatetags.pagination_tags import paginate
>>> from django.template import Template, Context

>>> p = Paginator(range(15), 2)
>>> pg = paginate({'paginator': p, 'page_obj': p.page(1)})
>>> pg['pages']
[1, 2, 3, 4, 5, 6, 7, 8]
>>> pg['records']['first']
1
>>> pg['records']['last']
2

>>> p = Paginator(range(15), 2)
>>> pg = paginate({'paginator': p, 'page_obj': p.page(8)})
>>> pg['pages']
[1, 2, 3, 4, 5, 6, 7, 8]
>>> pg['records']['first']
15
>>> pg['records']['last']
15

>>> p = Paginator(range(17), 2)
>>> paginate({'paginator': p, 'page_obj': p.page(1)})['pages']
[1, 2, 3, 4, 5, 6, 7, 8, 9]

>>> p = Paginator(range(19), 2)
>>> paginate({'paginator': p, 'page_obj': p.page(1)})['pages']
[1, 2, 3, 4, None, 7, 8, 9, 10]

>>> p = Paginator(range(21), 2)
>>> paginate({'paginator': p, 'page_obj': p.page(1)})['pages']
[1, 2, 3, 4, None, 8, 9, 10, 11]

# Testing orphans
>>> p = Paginator(range(5), 2, 1)
>>> paginate({'paginator': p, 'page_obj': p.page(1)})['pages']
[1, 2]

>>> p = Paginator(range(21), 2, 1)
>>> pg = paginate({'paginator': p, 'page_obj': p.page(1)})
>>> pg['pages']
[1, 2, 3, 4, None, 7, 8, 9, 10]
>>> pg['records']['first']
1
>>> pg['records']['last']
2

>>> p = Paginator(range(21), 2, 1)
>>> pg = paginate({'paginator': p, 'page_obj': p.page(10)})
>>> pg['pages']
[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
>>> pg['records']['first']
19
>>> pg['records']['last']
21

>>> t = Template("{% load pagination_tags %}{% autopaginate var 2 %}{% paginate %}")

>>> from django.http import HttpRequest as DjangoHttpRequest
>>> class HttpRequest(DjangoHttpRequest):
...     page = 1

>>> t.render(Context({'var': range(21), 'request': HttpRequest()}))
u'\\n\\n<div class="pagination">...
>>>
>>> t = Template("{% load pagination_tags %}{% autopaginate var %}{% paginate %}")
>>> t.render(Context({'var': range(21), 'request': HttpRequest()}))
u'\\n\\n<div class="pagination">...
>>> t = Template("{% load pagination_tags %}{% autopaginate var 20 %}{% paginate %}")
>>> t.render(Context({'var': range(21), 'request': HttpRequest()}))
u'\\n\\n<div class="pagination">...
>>> t = Template("{% load pagination_tags %}{% autopaginate var by %}{% paginate %}")
>>> t.render(Context({'var': range(21), 'by': 20, 'request': HttpRequest()}))
u'\\n\\n<div class="pagination">...
>>> t = Template("{% load pagination_tags %}{% autopaginate var by as foo %}{{ foo }}")
>>> t.render(Context({'var': range(21), 'by': 20, 'request': HttpRequest()}))
u'[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]'
>>>

# Testing InfinitePaginator

>>> from paginator import InfinitePaginator

>>> InfinitePaginator
<class 'pagination.paginator.InfinitePaginator'>
>>> p = InfinitePaginator(range(20), 2, link_template='/bacon/page/%d')
>>> p.validate_number(2)
2
>>> p.orphans
0
>>> p3 = p.page(3)
>>> p3
<Page 3>
>>> p3.end_index()
6
>>> p3.has_next()
True
>>> p3.has_previous()
True
>>> p.page(10).has_next()
False
>>> p.page(1).has_previous()
False
>>> p3.next_link()
'/bacon/page/4'
>>> p3.previous_link()
'/bacon/page/2'

# Testing FinitePaginator

>>> from paginator import FinitePaginator

>>> FinitePaginator
<class 'pagination.paginator.FinitePaginator'>
>>> p = FinitePaginator(range(20), 2, offset=10, link_template='/bacon/page/%d')
>>> p.validate_number(2)
2
>>> p.orphans
0
>>> p3 = p.page(3)
>>> p3
<Page 3>
>>> p3.start_index()
10
>>> p3.end_index()
6
>>> p3.has_next()
True
>>> p3.has_previous()
True
>>> p3.next_link()
'/bacon/page/4'
>>> p3.previous_link()
'/bacon/page/2'

>>> p = FinitePaginator(range(20), 20, offset=10, link_template='/bacon/page/%d')
>>> p2 = p.page(2)
>>> p2
<Page 2>
>>> p2.has_next()
False
>>> p3.has_previous()
True
>>> p2.next_link()

>>> p2.previous_link()
'/bacon/page/1'

>>> from pagination.middleware import PaginationMiddleware
>>> from django.core.handlers.wsgi import WSGIRequest
>>> from StringIO import StringIO
>>> middleware = PaginationMiddleware()
>>> request = WSGIRequest({'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': 'multipart', 'wsgi.input': StringIO()})
>>> middleware.process_request(request)
>>> request.upload_handlers.append('asdf')
"""

########NEW FILE########
__FILENAME__ = runtests
import sys
sys.path.append('..')

import os
# Make a backup of DJANGO_SETTINGS_MODULE environment variable to restore later.
backup = os.environ.get('DJANGO_SETTINGS_MODULE', '')
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from django.test.simple import run_tests

if __name__ == "__main__":
    failures = run_tests(['pagination',], verbosity=9)
    if failures:
        sys.exit(failures)
    # Reset the DJANGO_SETTINGS_MODULE to what it was before running tests.
    os.environ['DJANGO_SETTINGS_MODULE'] = backup

########NEW FILE########
__FILENAME__ = settings
DATABASE_ENGINE = 'sqlite3'
ROOT_URLCONF = ''
SITE_ID = 1
INSTALLED_APPS = (
    'pagination',
)

########NEW FILE########
