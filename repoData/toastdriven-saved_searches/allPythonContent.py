__FILENAME__ = admin
from django.contrib import admin
from saved_searches.models import SavedSearch


class SavedSearchAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    list_display = ('user_query', 'search_key', 'user', 'result_count', 'created')
    list_filter = ('search_key',)
    raw_id_fields = ('user',)
    search_fields = ('user_query', 'search_key')


admin.site.register(SavedSearch, SavedSearchAdmin)

########NEW FILE########
__FILENAME__ = models
import datetime
from django.contrib.auth.models import User
from django.db import models


class SavedSearchManager(models.Manager):
    def most_recent(self, user=None, search_key=None, collapsed=True, threshold=1):
        """
        Returns the most recently seen queries.
        
        By default, only shows collapsed queries. This means that if the same
        query was executed several times in a row, only the most recent is
        shown and a count of ``times_seen`` is additionally provided.
        
        If you want to saw all queries (regardless of duplicates), pass
        ``collapsed=False``. Note that the ``times_seen`` will always be 1 if
        this behavior is used.
        
        Can filter by ``user`` and/or ``search_key`` if provided.
        
        Can provide a ``threshold`` (minimum number required to be included) as
        an integer. Defaults to 1.
        """
        qs = self.get_query_set()
        
        if user is not None:
            qs = qs.filter(user=user)
        
        if search_key is not None:
            qs = qs.filter(search_key=search_key)
        
        if collapsed is True:
            initial_list_qs = qs.values('user_query').order_by().annotate(times_seen=models.Count('user_query'))
            return initial_list_qs.values('user_query', 'times_seen').annotate(most_recent=models.Max('created')).order_by('-most_recent').filter(times_seen__gte=threshold)
        else:
            return qs.values('user_query', 'created').order_by('-created').annotate(times_seen=models.Count('user_query')).filter(times_seen__gte=threshold)
    
    def most_popular(self, user=None, search_key=None, threshold=1):
        """
        Returns the most popular (frequently seen) queries.
        
        Can filter by ``user`` and/or ``search_key`` if provided.
        
        Can provide a ``threshold`` (minimum number required to be included) as
        an integer. Defaults to 1.
        """
        qs = self.get_query_set()
        
        if user is not None:
            qs = qs.filter(user=user)
        
        if search_key is not None:
            qs = qs.filter(search_key=search_key)
        
        return qs.values('user_query').order_by().annotate(times_seen=models.Count('user_query')).order_by('-times_seen').filter(times_seen__gte=threshold)


class SavedSearch(models.Model):
    search_key = models.SlugField(max_length=100, help_text="A way to arbitrarily group queries. Should be a single word. Example: all-products")
    user_query = models.CharField(max_length=1000, help_text="The text the user searched on. Useful for display.")
    full_query = models.CharField(max_length=1000, default='', blank=True, help_text="The full query Haystack generated. Useful for searching again.")
    result_count = models.PositiveIntegerField(default=0, blank=True)
    user = models.ForeignKey(User, blank=True, null=True, related_name='saved_searches')
    created = models.DateTimeField(blank=True, default=datetime.datetime.now)
    
    objects = SavedSearchManager()
    
    class Meta:
        verbose_name_plural = 'Saved Searches'
    
    def __unicode__(self):
        if self.user:
            return u"'%s...' by %s:%s" % (self.user_query[:50], self.user.username, self.search_key)
        
        return u"'%s...' by Anonymous:%s" % (self.user_query[:50], self.search_key)

########NEW FILE########
__FILENAME__ = saved_searches_tags
from django import template
from saved_searches.models import SavedSearch


register = template.Library()


class MostRecentNode(template.Node):
    def __init__(self, varname, user=None, search_key=None, limit=10):
        self.varname = varname
        self.user = user
        self.search_key = search_key
        self.limit = int(limit)
    
    def render(self, context):
        user = None
        search_key = None
        
        if self.user is not None:
            temp_user = template.Variable(self.user)
            user = temp_user.resolve(context)
        
        if self.search_key is not None:
            temp_search_key = template.Variable(self.search_key)
            search_key = temp_search_key.resolve(context)
        
        context[self.varname] = SavedSearch.objects.most_recent(user=user, search_key=search_key)[:self.limit]
        return ''


@register.tag
def most_recent_searches(parser, token):
    """
    Returns the most recent queries seen. By default, returns the top 10.
    
    Usage::
    
        {% most_recent_searches as <varname> [for_user user] [for_search_key search_key] [limit n] %}
    
    Example::
    
        {% most_recent_searches as recent %}
        {% most_recent_searches as recent for_user request.user %}
        {% most_recent_searches as recent for_search_key "general" %}
        {% most_recent_searches as recent limit 5 %}
        {% most_recent_searches as recent for_user request.user for_search_key "general" limit 15 %}
    """
    bits = token.split_contents()
    tagname = bits[0]
    bits = bits[1:]
    
    if len(bits) < 2:
        raise template.TemplateSyntaxError("%r tag requires at least two arguments." % tagname)
    
    varname = bits[1]
    bits = iter(bits[2:])
    user = None
    search_key = None
    limit = 10
    
    for bit in bits:
        if bit == 'for_user':
            user = bits.next()
        if bit == 'for_search_key':
            search_key = bits.next()
        if bit == 'limit':
            limit = bits.next()
    
    return MostRecentNode(varname, user, search_key, limit)


class MostPopularNode(template.Node):
    def __init__(self, varname, user=None, search_key=None, limit=10):
        self.varname = varname
        self.user = user
        self.search_key = search_key
        self.limit = int(limit)
    
    def render(self, context):
        user = None
        search_key = None
        
        if self.user is not None:
            temp_user = template.Variable(self.user)
            user = temp_user.resolve(context)
        
        if self.search_key is not None:
            temp_search_key = template.Variable(self.search_key)
            search_key = temp_search_key.resolve(context)
        
        context[self.varname] = SavedSearch.objects.most_popular(user=user, search_key=search_key)[:self.limit]
        return ''


@register.tag
def most_popular_searches(parser, token):
    """
    Returns the most popular queries seen. By default, returns the top 10.
    
    Usage::
    
        {% most_popular_searches as <varname> [for_user user] [for_search_key search_key] [limit n] %}
    
    Example::
    
        {% most_popular_searches as popular %}
        {% most_popular_searches as popular for_user request.user %}
        {% most_popular_searches as popular for_search_key "general" %}
        {% most_popular_searches as popular limit 5 %}
        {% most_popular_searches as popular for_user request.user for_search_key "general" limit 15 %}
    """
    bits = token.split_contents()
    tagname = bits[0]
    bits = bits[1:]
    
    if len(bits) < 2:
        raise template.TemplateSyntaxError("%r tag requires at least two arguments." % tagname)
    
    varname = bits[1]
    bits = iter(bits[2:])
    user = None
    search_key = None
    limit = 10
    
    for bit in bits:
        if bit == 'for_user':
            user = bits.next()
        if bit == 'for_search_key':
            search_key = bits.next()
        if bit == 'limit':
            limit = bits.next()
    
    return MostPopularNode(varname, user, search_key, limit)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *


urlpatterns = patterns('saved_searches.views',
    url(r'^most_recent/$', 'most_recent', name='saved_searches_most_recent'),
    url(r'^most_recent/username/(?P<username>[\w\d._-]+)/$', 'most_recent', name='saved_searches_most_recent_by_user'),
    url(r'^most_recent/area/(?P<search_key>[\w\d._-]*)/$', 'most_recent', name='saved_searches_most_recent_by_search_key'),
    url(r'^most_recent/area/(?P<search_key>[\w\d._-]*)/username/(?P<username>[\w\d._-]+)/$', 'most_recent', name='saved_searches_most_recent_by_user_search_key'),
    
    url(r'^most_popular/$', 'most_popular', name='saved_searches_most_popular'),
    url(r'^most_popular/username/(?P<username>[\w\d._-]+)/$', 'most_popular', name='saved_searches_most_popular_by_user'),
    url(r'^most_popular/area/(?P<search_key>[\w\d._-]*)/$', 'most_popular', name='saved_searches_most_popular_by_search_key'),
    url(r'^most_popular/area/(?P<search_key>[\w\d._-]*)/username/(?P<username>[\w\d._-]+)/$', 'most_popular', name='saved_searches_most_popular_by_user_search_key'),
)

########NEW FILE########
__FILENAME__ = views
import datetime
from django.conf import settings
from django.contrib.auth.models import User
from django.core.paginator import Paginator, InvalidPage
from django.http import Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from haystack.views import SearchView
from saved_searches.models import SavedSearch


SAVED_SEARCHES_PER_PAGE = getattr(settings, 'SAVED_SEARCHES_PER_PAGE', 50)
SAVED_SEARCHES_THRESHOLD = getattr(settings, 'SAVED_SEARCHES_THRESHOLD', 1)


class SavedSearchView(SearchView):
    """
    Automatically handles saving the queries when they are run.
    """
    search_key = 'general'

    def __init__(self, *args, **kwargs):
        if 'search_key' in kwargs:
            self.search_key = kwargs['search_key']
            del(kwargs['search_key'])

        super(SavedSearchView, self).__init__(*args, **kwargs)

    def save_search(self, page):
        """
        Only save the search if we're on the first page.
        This will prevent an excessive number of duplicates for what is
        essentially the same search.
        """
        if self.query and page.number == 1:
            # Save the search.
            saved_search = SavedSearch(
                search_key=self.search_key,
                user_query=self.query,
                result_count=len(self.results)
            )

            if hasattr(self.results, 'query'):
                query_seen = self.results.query.build_query()

                if isinstance(query_seen, basestring):
                    saved_search.full_query = query_seen

            if self.request.user.is_authenticated():
                saved_search.user = self.request.user

            saved_search.save()

    def create_response(self):
        """
        Saves the details of a user's search and then generates the actual
        ``HttpResponse`` to send back to the user.
        """
        (paginator, page) = self.build_page()
        self.save_search(page)

        context = {
            'query': self.query,
            'form': self.form,
            'page': page,
            'paginator': paginator,
        }
        context.update(self.extra_context())

        return render_to_response(self.template, context, context_instance=self.context_class(self.request))


def most_recent(request, username=None, search_key=None):
    """
    Shows the most recent search results.

    The ``username`` kwarg should be the ``username`` field of
    ``django.contrib.auth.models.User``. The ``search_key`` can be any string.

    Template::
        ``saved_searches/most_recent.html``
    Context::
        ``by_user``
            The ``User`` object corresponding to the username, if provided.
        ``by_search_key``
            The search_key, if provided.
        ``page``
            The request page of recent results (a dict of ``user_query`` + ``created``).
        ``paginator``
            The paginator object for the full result set.
    """
    if username is not None:
        user = get_object_or_404(User, username=username)
    else:
        user = None

    most_recent = SavedSearch.objects.most_recent(user=user, search_key=search_key, threshold=SAVED_SEARCHES_THRESHOLD)
    paginator = Paginator(most_recent, SAVED_SEARCHES_PER_PAGE)

    try:
        page = paginator.page(int(request.GET.get('page', 1)))
    except InvalidPage:
        raise Http404("Invalid page.")

    return render_to_response('saved_searches/most_recent.html', {
        'by_user': user,
        'by_search_key': search_key,
        'page': page,
        'paginator': paginator,
    }, context_instance=RequestContext(request))


def most_popular(request, username=None, search_key=None):
    """
    Shows the most popular search results.

    The ``username`` kwarg should be the ``username`` field of
    ``django.contrib.auth.models.User``. The ``search_key`` can be any string.

    Template::
        ``saved_searches/most_popular.html``
    Context::
        ``by_user``
            The ``User`` object corresponding to the username, if provided.
        ``by_search_key``
            The search_key, if provided.
        ``page``
            The request page of popular results (a dict of ``user_query`` + ``times_seen``).
        ``paginator``
            The paginator object for the full result set.
    """
    if username is not None:
        user = get_object_or_404(User, username=username)
    else:
        user = None

    most_recent = SavedSearch.objects.most_popular(user=user, search_key=search_key, threshold=SAVED_SEARCHES_THRESHOLD)
    paginator = Paginator(most_recent, SAVED_SEARCHES_PER_PAGE)

    try:
        page = paginator.page(int(request.GET.get('page', 1)))
    except InvalidPage:
        raise Http404("Invalid page.")

    return render_to_response('saved_searches/most_popular.html', {
        'by_user': user,
        'by_search_key': search_key,
        'page': page,
        'paginator': paginator,
    }, context_instance=RequestContext(request))


########NEW FILE########
__FILENAME__ = models
import datetime
from django.db import models


# Ghetto app!
class Note(models.Model):
    title = models.CharField(max_length=128)
    content = models.TextField()
    author = models.CharField(max_length=64)
    created = models.DateTimeField(default=datetime.datetime.now)
    
    def __unicode__(self):
        return self.title

########NEW FILE########
__FILENAME__ = search_indexes
from haystack import indexes
from notes.models import Note


class NoteIndex(indexes.RealTimeSearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, model_attr='content')
    
    def get_model(self):
        return Note

########NEW FILE########
__FILENAME__ = search_sites
import haystack
haystack.autodiscover()

########NEW FILE########
__FILENAME__ = tests
from django.contrib.auth.models import User
from django.template import Template, Context
from django.test import TestCase
from saved_searches.models import SavedSearch
from notes.models import Note


class SavedSearchTestCase(TestCase):
    def setUp(self):
        super(SavedSearchTestCase, self).setUp()
        self.user1 = User.objects.create_user('testy', 'test@example.com', 'test')
        # self.user1.is_active = True
        # self.user1.save()
        self.note1 = Note.objects.create(
            title='A test note',
            content='Because everyone loves test data.',
            author='Daniel'
        )
        self.note2 = Note.objects.create(
            title='Another test note',
            content='Something to test with.',
            author='John'
        )
        self.note3 = Note.objects.create(
            title='NEVER GOING TO GIVE YOU UP',
            content='NEVER GOING TO LET YOU DOWN.',
            author='Rick'
        )
    
    def test_usage(self):
        # Check the stat pages first.
        resp = self.client.get('/search_stats/most_recent/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['by_user'], None)
        self.assertEqual(resp.context['by_search_key'], None)
        self.assertEqual(len(resp.context['page'].object_list), 0)
        self.assertEqual(resp.context['paginator'].num_pages, 1)
        
        resp = self.client.get('/search_stats/most_popular/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['by_user'], None)
        self.assertEqual(resp.context['by_search_key'], None)
        self.assertEqual(len(resp.context['page'].object_list), 0)
        self.assertEqual(resp.context['paginator'].num_pages, 1)
        
        
        # Sanity check.
        resp = self.client.get('/search/')
        self.assertEqual(resp.status_code, 200)
        
        # Run a couple searches.
        resp = self.client.get('/search/', data={'q': 'test'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['paginator'].count, 2)
        self.assertEqual(SavedSearch.objects.all().count(), 1)
        
        resp = self.client.get('/search/', data={'q': 'everyone'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['paginator'].count, 1)
        self.assertEqual(SavedSearch.objects.all().count(), 2)
        
        resp = self.client.get('/search/', data={'q': 'test data'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['paginator'].count, 1)
        self.assertEqual(SavedSearch.objects.all().count(), 3)
        
        resp = self.client.get('/search/', data={'q': 'test'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['paginator'].count, 2)
        self.assertEqual(SavedSearch.objects.all().count(), 4)
        
        # This shouldn't get logged.
        resp = self.client.get('/search/', data={'q': 'test', 'page': 2})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['paginator'].count, 2)
        self.assertEqual(len(resp.context['page'].object_list), 1)
        self.assertEqual(SavedSearch.objects.all().count(), 4)
        
        # Run a couple user searches.
        self.assertEqual(self.client.login(username='testy', password='test'), True)
        
        resp = self.client.get('/search/', data={'q': 'test'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['paginator'].count, 2)
        self.assertEqual(SavedSearch.objects.all().count(), 5)
        self.assertEqual(SavedSearch.objects.filter(user=self.user1).count(), 1)
        
        resp = self.client.get('/search/', data={'q': 'everyone'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['paginator'].count, 1)
        self.assertEqual(SavedSearch.objects.all().count(), 6)
        self.assertEqual(SavedSearch.objects.filter(user=self.user1).count(), 2)
        
        resp = self.client.get('/search/', data={'q': 'test'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['paginator'].count, 2)
        self.assertEqual(SavedSearch.objects.all().count(), 7)
        self.assertEqual(SavedSearch.objects.filter(user=self.user1).count(), 3)
        
        self.client.logout()
        
        # Verify the lists.
        self.assertEqual([ss['user_query'] for ss in SavedSearch.objects.most_recent()], [u'test', u'everyone', u'test data'])
        self.assertEqual([ss['times_seen'] for ss in SavedSearch.objects.most_recent()], [4, 2, 1])
        self.assertEqual([ss['times_seen'] for ss in SavedSearch.objects.most_recent(threshold=2)], [4, 2])
        self.assertEqual([ss['user_query'] for ss in SavedSearch.objects.most_recent(collapsed=False)], [u'test', u'everyone', u'test', u'test', u'test data', u'everyone', u'test'])
        self.assertEqual([ss['times_seen'] for ss in SavedSearch.objects.most_recent(collapsed=False)], [1, 1, 1, 1, 1, 1, 1])
        self.assertEqual([ss['user_query'] for ss in SavedSearch.objects.most_popular()], [u'test', u'everyone', u'test data'])
        self.assertEqual([ss['times_seen'] for ss in SavedSearch.objects.most_popular()], [4, 2, 1])
        self.assertEqual([ss['times_seen'] for ss in SavedSearch.objects.most_popular(threshold=2)], [4, 2])
        
        
        # Check to see if stats updated.
        resp = self.client.get('/search_stats/most_recent/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['by_user'], None)
        self.assertEqual(resp.context['by_search_key'], None)
        self.assertEqual([ss['user_query'] for ss in resp.context['page'].object_list], [u'test', u'everyone', u'test data'])
        self.assertEqual(resp.context['paginator'].num_pages, 1)
        
        resp = self.client.get('/search_stats/most_recent/username/testy/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['by_user'].username, 'testy')
        self.assertEqual(resp.context['by_search_key'], None)
        self.assertEqual([ss['user_query'] for ss in resp.context['page'].object_list], [u'test', u'everyone'])
        self.assertEqual(resp.context['paginator'].num_pages, 1)
        
        resp = self.client.get('/search_stats/most_recent/area/general/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['by_user'], None)
        self.assertEqual(resp.context['by_search_key'], u'general')
        self.assertEqual([ss['user_query'] for ss in resp.context['page'].object_list], [u'test', u'everyone', u'test data'])
        self.assertEqual(resp.context['paginator'].num_pages, 1)
        
        resp = self.client.get('/search_stats/most_popular/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['by_user'], None)
        self.assertEqual(resp.context['by_search_key'], None)
        self.assertEqual([ss['user_query'] for ss in resp.context['page'].object_list], [u'test', u'everyone', u'test data'])
        self.assertEqual([ss['times_seen'] for ss in resp.context['page'].object_list], [4, 2, 1])
        self.assertEqual(resp.context['paginator'].num_pages, 1)
        
        resp = self.client.get('/search_stats/most_popular/username/testy/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['by_user'].username, 'testy')
        self.assertEqual(resp.context['by_search_key'], None)
        self.assertEqual([ss['user_query'] for ss in resp.context['page'].object_list], [u'test', u'everyone'])
        self.assertEqual([ss['times_seen'] for ss in resp.context['page'].object_list], [2, 1])
        self.assertEqual(resp.context['paginator'].num_pages, 1)
        
        resp = self.client.get('/search_stats/most_popular/area/general/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['by_user'], None)
        self.assertEqual(resp.context['by_search_key'], u'general')
        self.assertEqual([ss['user_query'] for ss in resp.context['page'].object_list], [u'test', u'everyone', u'test data'])
        self.assertEqual([ss['times_seen'] for ss in resp.context['page'].object_list], [4, 2, 1])
        self.assertEqual(resp.context['paginator'].num_pages, 1)


class TemplateTagTestCase(TestCase):
    def render(self, template_string, context={}):
        t = Template(template_string)
        c = Context(context)
        return t.render(c)


class MostRecentSearchesTestCase(TemplateTagTestCase):
    def setUp(self):
        super(MostRecentSearchesTestCase, self).setUp()
        self.saved1 = SavedSearch.objects.create(
            search_key='general',
            user_query='test'
        )
        self.saved2 = SavedSearch.objects.create(
            search_key='general',
            user_query='everyone'
        )
        self.saved3 = SavedSearch.objects.create(
            search_key='general',
            user_query='test data'
        )
        self.saved4 = SavedSearch.objects.create(
            search_key='events',
            user_query='test'
        )
        self.saved5 = SavedSearch.objects.create(
            search_key='general',
            user_query='test'
        )
        self.saved6 = SavedSearch.objects.create(
            search_key='general',
            user_query='everyone'
        )
    
    def test_correct_usage(self):
        temp = """{% load saved_searches_tags %}{% most_recent_searches as recent %}{% for search in recent %}'{{ search.user_query }}' {% endfor %}"""
        context = {}
        output = self.render(temp, context)
        self.assertEqual(output, u"'everyone' 'test' 'test data' ")
        
        temp = """{% load saved_searches_tags %}{% most_recent_searches as recent for_search_key "general" %}{% for search in recent %}'{{ search.user_query }}' {% endfor %}"""
        context = {}
        output = self.render(temp, context)
        self.assertEqual(output, u"'everyone' 'test' 'test data' ")
        
        temp = """{% load saved_searches_tags %}{% most_recent_searches as recent for_search_key "events" %}{% for search in recent %}'{{ search.user_query }}' {% endfor %}"""
        context = {}
        output = self.render(temp, context)
        self.assertEqual(output, u"'test' ")
        
        temp = """{% load saved_searches_tags %}{% most_recent_searches as recent limit 1 %}{% for search in recent %}'{{ search.user_query }}' {% endfor %}"""
        context = {}
        output = self.render(temp, context)
        self.assertEqual(output, u"'everyone' ")


class MostPopularSearchesTestCase(TemplateTagTestCase):
    def setUp(self):
        super(MostPopularSearchesTestCase, self).setUp()
        self.saved1 = SavedSearch.objects.create(
            search_key='general',
            user_query='test'
        )
        self.saved2 = SavedSearch.objects.create(
            search_key='general',
            user_query='everyone'
        )
        self.saved3 = SavedSearch.objects.create(
            search_key='general',
            user_query='test data'
        )
        self.saved4 = SavedSearch.objects.create(
            search_key='events',
            user_query='test'
        )
        self.saved5 = SavedSearch.objects.create(
            search_key='general',
            user_query='test'
        )
        self.saved6 = SavedSearch.objects.create(
            search_key='general',
            user_query='everyone'
        )
    
    def test_correct_usage(self):
        temp = """{% load saved_searches_tags %}{% most_popular_searches as popular %}{% for search in popular %}'{{ search.user_query }}' ({{ search.times_seen }}x) {% endfor %}"""
        context = {}
        output = self.render(temp, context)
        self.assertEqual(output, u"'test' (3x) 'everyone' (2x) 'test data' (1x) ")
        
        temp = """{% load saved_searches_tags %}{% most_popular_searches as popular for_search_key "general" %}{% for search in popular %}'{{ search.user_query }}' ({{ search.times_seen }}x) {% endfor %}"""
        context = {}
        output = self.render(temp, context)
        self.assertEqual(output, u"'everyone' (2x) 'test' (2x) 'test data' (1x) ")
        
        temp = """{% load saved_searches_tags %}{% most_popular_searches as popular for_search_key "events" %}{% for search in popular %}'{{ search.user_query }}' ({{ search.times_seen }}x) {% endfor %}"""
        context = {}
        output = self.render(temp, context)
        self.assertEqual(output, u"'test' (1x) ")
        
        temp = """{% load saved_searches_tags %}{% most_popular_searches as popular limit 1 %}{% for search in popular %}'{{ search.user_query }}' ({{ search.times_seen }}x) {% endfor %}"""
        context = {}
        output = self.render(temp, context)
        self.assertEqual(output, u"'test' (3x) ")

########NEW FILE########
__FILENAME__ = settings
import os

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = 'notes.db'

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'haystack',
    'saved_searches',
    'notes',
]

ROOT_URLCONF = 'test_urls'

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.auth",
    "django.core.context_processors.request",
)

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'PATH': os.path.join(os.path.dirname(__file__), 'whoosh_index'),
    }
}
# Set this low to simulate multiple pages.
HAYSTACK_SEARCH_RESULTS_PER_PAGE = 1

########NEW FILE########
__FILENAME__ = test_urls
from django.conf.urls.defaults import *
from saved_searches.views import SavedSearchView


urlpatterns = patterns('',
    url(r'^search/$', SavedSearchView(), name='search'),
    url(r'^search_stats/', include('saved_searches.urls')),
)

########NEW FILE########
