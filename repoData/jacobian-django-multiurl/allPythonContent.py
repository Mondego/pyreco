__FILENAME__ = multiurl
from __future__ import unicode_literals

from django.core import urlresolvers

class ContinueResolving(Exception):
    pass

def multiurl(*urls, **kwargs):
    exceptions = kwargs.get('catch', (ContinueResolving,))
    return MultiRegexURLResolver(urls, exceptions)

class MultiRegexURLResolver(urlresolvers.RegexURLResolver):
    def __init__(self, urls, exceptions):
        super(MultiRegexURLResolver, self).__init__('', None)
        self._urls = urls
        self._exceptions = exceptions

    @property
    def url_patterns(self):
        return self._urls

    def resolve(self, path):
        tried = []
        matched = []
        patterns_matched = []

        # This is a simplified version of RegexURLResolver. It doesn't
        # support a regex prefix, and it doesn't need to handle include(),
        # so it's simplier, but otherwise this is mostly a copy/paste.
        for pattern in self.url_patterns:
            sub_match = pattern.resolve(path)
            if sub_match:
                # Here's the part that's different: instead of returning the
                # first match, build up a list of all matches.
                rm = urlresolvers.ResolverMatch(sub_match.func, sub_match.args, sub_match.kwargs, sub_match.url_name)
                matched.append(rm)
                patterns_matched.append([pattern])
            tried.append([pattern])
        if matched:
            return MultiResolverMatch(matched, self._exceptions, patterns_matched, path)
        raise urlresolvers.Resolver404({'tried': tried, 'path': path})

class MultiResolverMatch(object):
    def __init__(self, matches, exceptions, patterns_matched, path):
        self.matches = matches
        self.exceptions = exceptions
        self.patterns_matched = patterns_matched
        self.path = path

        # Attributes to emulate ResolverMatch
        self.kwargs = {}
        self.args = []
        self.url_name = None
        self.app_name = None
        self.namespaces = []

    @property
    def func(self):
        def multiview(request):
            for i, match in enumerate(self.matches):
                try:
                    return match.func(request, *match.args, **match.kwargs)
                except self.exceptions:
                    continue
            raise urlresolvers.Resolver404({'tried': self.patterns_matched, 'path': self.path})
        multiview.multi_resolver_match = self
        return multiview

########NEW FILE########
__FILENAME__ = tests
from __future__ import unicode_literals

from django.conf import settings
from django.conf.urls import patterns, url
from django.core.urlresolvers import RegexURLResolver, Resolver404, NoReverseMatch
from django.http import HttpResponse
from django.utils import unittest
from multiurl import multiurl, ContinueResolving

class MultiviewTests(unittest.TestCase):
    def setUp(self):
        # Patterns with a "catch all" view (thing) at the end.
        self.patterns_catchall = RegexURLResolver('^/', patterns('',
            multiurl(
                url(r'^(\w+)/$', person, name='person'),
                url(r'^(\w+)/$', place, name='place'),
                url(r'^(\w+)/$', thing, name='thing'),
            )
        ))

        # Patterns with no "catch all" - last view could still raise ContinueResolving.
        self.patterns_no_fallthrough = RegexURLResolver('^/', patterns('',
            multiurl(
                url(r'^(\w+)/$', person, name='person'),
                url(r'^(\w+)/$', place, name='place'),
            )
        ))

    def test_resolve_match_first(self):
        m = self.patterns_catchall.resolve('/jane/')
        response = m.func(request=None, *m.args, **m.kwargs)
        self.assertEqual(response.content, b"Person: Jane Doe")

    def test_resolve_match_middle(self):
        m = self.patterns_catchall.resolve('/sf/')
        response = m.func(request=None, *m.args, **m.kwargs)
        self.assertEqual(response.content, b"Place: San Francisco")

    def test_resolve_match_last(self):
        m = self.patterns_catchall.resolve('/bacon/')
        response = m.func(request=None, *m.args, **m.kwargs)
        self.assertEqual(response.content, b"Thing: Bacon")

    def test_resolve_match_faillthrough(self):
        m = self.patterns_no_fallthrough.resolve('/bacon/')
        with self.assertRaises(Resolver404):
            m.func(request=None, *m.args, **m.kwargs)

    def test_no_match(self):
        with self.assertRaises(Resolver404):
            self.patterns_catchall.resolve('/eggs/and/bacon/')

    def test_reverse(self):
        self.assertEqual('joe/', self.patterns_catchall.reverse('person', 'joe'))
        self.assertEqual('joe/', self.patterns_catchall.reverse('place', 'joe'))
        self.assertEqual('joe/', self.patterns_catchall.reverse('thing', 'joe'))
        with self.assertRaises(NoReverseMatch):
            self.patterns_catchall.reverse('person')
        with self.assertRaises(NoReverseMatch):
            self.patterns_catchall.reverse('argh', 'xyz')

#
# Some "views" to test against.
#

def person(request, name):
    people = {
        'john': 'John Smith',
        'jane': 'Jane Doe',
    }
    if name in people:
        return HttpResponse("Person: " + people[name])
    raise ContinueResolving

def place(request, name):
    places = {
        'sf': 'San Francisco',
        'nyc': 'New York City',
    }
    if name in places:
        return HttpResponse("Place: " + places[name])
    raise ContinueResolving

def thing(request, name):
    return HttpResponse("Thing: " + name.title())

if __name__ == '__main__':
    settings.configure()
    unittest.main()

########NEW FILE########
