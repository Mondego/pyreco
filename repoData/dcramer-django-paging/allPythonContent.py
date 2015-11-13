__FILENAME__ = helpers
from paging.paginators import *

def paginate(request, queryset_or_list, per_page=25, endless=True):
    if endless:
        paginator_class = EndlessPaginator
    else:
        paginator_class = BetterPaginator
    
    paginator = paginator_class(queryset_or_list, per_page)
    
    query_dict = request.GET.copy()
    if 'p' in query_dict:
        del query_dict['p']

    try:
        page = int(request.GET.get('p', 1))
    except (ValueError, TypeError):
        page = 1
    if page < 1:
        page = 1

    context = {
        'query_string': query_dict.urlencode(),
        'paginator': paginator.get_context(page),
    }
    return context
########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = paginators
from django.core.paginator import Paginator, InvalidPage, Page, PageNotAnInteger, EmptyPage

__all__ = ('BetterPaginator', 'InvalidPage', 'PageNotAnInteger', 'EmptyPage', 'EndlessPaginator')

class BetterPaginator(Paginator):
    """
    An enhanced version of the QuerySetPaginator.
    
    >>> my_objects = BetterPaginator(queryset, 25)
    >>> page = 1
    >>> context = {
    >>>     'my_objects': my_objects.get_context(page),
    >>> }
    """
    def get_context(self, page, range_gap=5):
        try:
            page = int(page)
        except (ValueError, TypeError), exc:
            raise InvalidPage, exc
        
        try:
            paginator = self.page(page)
        except EmptyPage:
            return {
                'EMPTY_PAGE': True,
            }
        
        if page > 5:
            start = page-range_gap
        else:
            start = 1

        if page < self.num_pages-range_gap:
            end = page+range_gap+1
        else:
            end = self.num_pages+1

        context = {
            'page_range': range(start, end),
            'objects': paginator.object_list,
            'num_pages': self.num_pages,
            'page': page,
            'has_pages': self.num_pages > 1,
            'has_previous': paginator.has_previous(),
            'has_next': paginator.has_next(),
            'previous_page': paginator.previous_page_number() if paginator.has_previous() else None,
            'next_page': paginator.next_page_number() if paginator.has_next() else None,
            'is_first': page == 1,
            'is_last': page == self.num_pages,
        }
        
        return context

class EndlessPage(Page):
    def __init__(self, *args, **kwargs):
        super(EndlessPage, self).__init__(*args, **kwargs)
        self._has_next = self.paginator.per_page < len(self.object_list)
        self.object_list = self.object_list[:self.paginator.per_page]
    
    def has_next(self):
        return self._has_next
    
class EndlessPaginator(BetterPaginator):
    def page(self, number):
        "Returns a Page object for the given 1-based page number."
        try:
            number = int(number)
        except ValueError:
            raise PageNotAnInteger('That page number is not an integer')
        bottom = (number - 1) * self.per_page
        top = bottom + self.per_page + 5
        try:
            _page = EndlessPage(list(self.object_list[bottom:top]), number, self)
        except AssertionError:
            top = top - 5
            _page = EndlessPage(list(self.object_list[bottom:top]), number, self)

        if not _page.object_list:
            if number == 1 and self.allow_empty_first_page:
                pass
            else:
                raise EmptyPage('That page contains no results')
        return _page

    def get_context(self, page):
        try:
            paginator = self.page(page)
        except (PageNotAnInteger, EmptyPage), exc:
            return {'EMPTY_PAGE': True}

        context = {
            'objects': paginator.object_list,
            'page': page,
            'has_previous': paginator.has_previous(),
            'has_next': paginator.has_next(),
            'previous_page': paginator.previous_page_number() if paginator.has_previous() else None,
            'next_page': paginator.next_page_number() if paginator.has_next() else None,
            'is_first': page == 1,
            'has_pages': paginator.has_next() or paginator.has_previous(),
            'is_last': not paginator.has_next(),
        }
        
        return context

########NEW FILE########
__FILENAME__ = paging_extras
from paging.helpers import paginate as paginate_func

from django import template
from django.utils.safestring import mark_safe
from django.template import RequestContext

try:
    from coffin import template
    from coffin.shortcuts import render_to_string
    from jinja2 import Markup
    is_coffin = True
except ImportError:
    is_coffin = False

from templatetag_sugar.register import tag
from templatetag_sugar.parser import Name, Variable, Constant, Optional, Model

register = template.Library()

if is_coffin:
    def paginate(request, queryset_or_list, per_page=25):
        context_instance = RequestContext(request)
        context = paginate_func(request, queryset_or_list, per_page)
        paging = Markup(render_to_string('paging/pager.html', context, context_instance))
        return dict(objects=context['paginator'].get('objects', []), paging=paging)
    register.object(paginate)

@tag(register, [Variable('queryset_or_list'),
                Constant('from'), Variable('request'),
                Optional([Constant('as'), Name('asvar')]),
                Optional([Constant('per_page'), Variable('per_page')]),
                Optional([Variable('is_endless')])])
def paginate(context, queryset_or_list, request, asvar, per_page=25, is_endless=True):
    """{% paginate queryset_or_list from request as foo[ per_page 25][ is_endless False %}"""

    from django.template.loader import render_to_string

    context_instance = RequestContext(request)
    paging_context = paginate_func(request, queryset_or_list, per_page, endless=is_endless)
    paging = mark_safe(render_to_string('paging/pager.html', paging_context, context_instance))

    result = dict(objects=paging_context['paginator'].get('objects', []),
				  paging=paging, paginator=paging_context['paginator'])
    if asvar:
        context[asvar] = result
        return ''
    return result
########NEW FILE########
__FILENAME__ = tests
import unittest2

from paging.helpers import paginate
from paging.paginators import *

from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASE_ENGINE='sqlite3',
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'paging',
        ]
    )

class PagingUnitTest(unittest2.TestCase):
    def test_better_paginator(self):
        objects = range(1, 100)
        
        paginator = BetterPaginator(objects, 1)
        for num in objects:
            page = paginator.get_context(num)
            self.assertEquals(page['objects'], [num])
            self.assertEquals(page['has_next'], num < 99)
            self.assertEquals(page['has_previous'], num > 1)
            self.assertEquals(page['is_first'], num == 1)
            self.assertEquals(page['is_last'], num == 99)
            self.assertEquals(page['previous_page'], num - 1 if num else False)
            self.assertEquals(page['next_page'], num + 1)
            self.assertEquals(page['page'], num)
            self.assertEquals(page['num_pages'], 99)
            # XXX: this test could be improved
            self.assertTrue(page['page_range'])

    def test_endless_paginator(self):
        objects = range(1, 100)
        
        paginator = EndlessPaginator(objects, 1)
        for num in objects:
            page = paginator.get_context(num)
            self.assertEquals(page['objects'], [num])
            self.assertEquals(page['has_next'], num < 99)
            self.assertEquals(page['has_previous'], num > 1)
            self.assertEquals(page['is_first'], num == 1)
            self.assertEquals(page['is_last'], num == 99)
            self.assertEquals(page['previous_page'], num - 1 if num else False)
            self.assertEquals(page['next_page'], num + 1)
            self.assertEquals(page['page'], num)

########NEW FILE########
