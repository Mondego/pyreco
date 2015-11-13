__FILENAME__ = base
# Copyright (c) 2010 Mark Sandstrom
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from functools import partial

from django.conf.urls.defaults import patterns as django_patterns
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import RegexURLPattern, RegexURLResolver

# Django 1.3 compatibility
try:
    from django.core.urlresolvers import ResolverMatch
except ImportError:
    ResolverMatch = None

from utils import rollup

class RerouteRegexURLPattern(RegexURLPattern):
    _configured = False
    
    def reroute_config(self, wrappers, patterns_id):
        self.wrappers = wrappers
        self._configured = True
        
    def reroute_callback(self, request, *args, **kwargs):
        callback = rollup(self.callback, self.wrappers)
        return callback(request, *args, **kwargs)
                  
    def resolve(self, path):
        # Lifted from django.core.urlresolvers.RegexURLPattern.resolve
        if not self._configured:
            raise ImproperlyConfigured('RerouteRegexURLPattern patterns must be used within reroute.patterns or reroute_patterns (for pattern %r)' % self.regex.pattern)
        
        match = self.regex.search(path)
        if match:
            # If there are any named groups, use those as kwargs, ignoring
            # non-named groups. Otherwise, pass all non-named arguments as
            # positional arguments.
            kwargs = match.groupdict()
            if kwargs:
                args = ()
            else:
                args = match.groups()
            # In both cases, pass any extra_kwargs as **kwargs.
            kwargs.update(self.default_args)

            # We unfortunately need another wrapper here since arbitrary attributes can't be set
            # on an instancemethod
            callback = lambda request, *args, **kwargs: self.reroute_callback(request, *args, **kwargs)
            
            if hasattr(self.callback, 'csrf_exempt'):
                callback.csrf_exempt = self.callback.csrf_exempt

            # Django 1.3 compatibility
            if ResolverMatch:
                return ResolverMatch(callback, args, kwargs, self.name)
            else:
                return callback, args, kwargs

def reroute_patterns(wrappers, prefix, *args):
    # TODO(dnerdy) Require that all patterns be instances of RerouteRegexURLPattern
    # TODO(dnerdy) Remove additional patterns with identical regexes, if present (occurs
    #   when using verb_url)
    
    patterns_id = object()
    pattern_list = django_patterns(prefix, *args)
    
    for pattern in pattern_list:
        if isinstance(pattern, RerouteRegexURLPattern):            
            pattern.reroute_config(wrappers, patterns_id)
        
    return pattern_list
    
patterns = partial(reroute_patterns, [])

def url_with_pattern_class(pattern_class, regex, view, kwargs=None, name=None, prefix=''):
    # Lifted from django.conf.urls.defaults
    
    if isinstance(view, (list,tuple)):
        # For include(...) processing.
        urlconf_module, app_name, namespace = view
        return RegexURLResolver(regex, urlconf_module, kwargs, app_name=app_name, namespace=namespace)
    else:
        if isinstance(view, basestring):
            if not view:
                raise ImproperlyConfigured('Empty URL pattern view name not permitted (for pattern %r)' % regex)
            if prefix:
                view = prefix + '.' + view
        return pattern_class(regex, view, kwargs, name)
        
url = partial(url_with_pattern_class, RerouteRegexURLPattern)

########NEW FILE########
__FILENAME__ = decorators
# Copyright (c) 2011 Mark Sandstrom

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is 
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in 
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN 
# THE SOFTWARE.

from functools import wraps

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

CONFLICTING_CONTEXTS = 'The view {module}.{view} and @render define conflicting contexts. These keys collide: {keys}'

def render(template, **extra_context):
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            response = func(request, *args, **kwargs)
            if isinstance(response, dict):
                common_keys = set(response) & set(extra_context)
                if common_keys:
                    raise ValueError(CONFLICTING_CONTEXTS.format(
                        module = func.__module__,
                        view = func.__name__,
                        keys = ', '.join(common_keys)
                    ))
                response.update(extra_context)
                response = render_to_response(template, response, context_instance=RequestContext(request))
                return response
            else:
                return response
        return wrapper
    return decorator

def redirect(reverse_viewname):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            response = func(*args, **kwargs)
            if isinstance(response, dict):
                return HttpResponseRedirect(reverse(reverse_viewname, kwargs=response))
            else:
                return response
        return wrapper
    return decorator

########NEW FILE########
__FILENAME__ = utils
# Copyright (c) 2010 Mark Sandstrom
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from functools import partial

def rollup(function, wrappers):            
    for wrapper in reversed(wrappers):
        function = partial(wrapper, function)
    return function
########NEW FILE########
__FILENAME__ = verbs
# Copyright (c) 2010 Mark Sandstrom
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from functools import partial

from django.http import HttpResponse

from base import RerouteRegexURLPattern, url_with_pattern_class
from utils import rollup

__all__ = ['verb_url', 'request_method']

def request_method(request):
    '''Returns the effective HTTP method of a request. To support the entire range of HTTP methods
    from HTML forms (which only support GET and POST), an HTTP method may be emulated by
    setting a POST parameter named "_method" to the name of the HTTP method to be emulated.
    
    Example HTML:
        <!-- Submits a form using the PUT method -->
        
        <form>
            <input type="text" name="name" value="value" />
            <button type="submit" name="_method" value="put">Update</button>
        </form>
    
    Args:
        request: an HttpRequest
    
    Returns:
        An upper-case string naming the HTTP method (like django.http.HttpRequest.method)
    '''
    
    # For security reasons POST is the only method that supports HTTP method emulation.
    # For example, if POST requires csrf_token, we don't want POST methods to be called via
    # GET (thereby bypassing CSRF protection). POST has the most limited semantics, and it
    # is therefore safe to emulate HTTP methods with less-limited semantics. See
    # http://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html ("Safe and Idempotent Methods")
    # for details.

    if request.method == 'POST' and '_method' in request.POST:
        method = request.POST['_method'].upper()
    else:
        method = request.method
        
    return method        

class VerbRegexURLPattern(RerouteRegexURLPattern):
    patterns_index = {}
    
    def __init__(self, method, *args, **kwargs):
        super(VerbRegexURLPattern, self).__init__(*args, **kwargs)
        self.method = method.upper() 
    
    def reroute_callback(self, request, *args, **kwargs):
        record = self.method_callbacks.get(request_method(request))
        
        if not record:
            return HttpResponse(status=405)
            
        callback = record['callback']
        kwargs.update(record['default_args'])
           
        callback = rollup(callback, self.wrappers)
        return callback(request, *args, **kwargs)
    
    def reroute_config(self, wrappers, patterns_id):
        super(VerbRegexURLPattern, self).reroute_config(wrappers, patterns_id)
        
        # Let patterns with identical regexes that are defined within the same call
        # to reroute_patterns be called a pattern group. Each pattern in a pattern group
        # has a reference to shared dict (shared by the group) which maps http methods
        # to pattern callbacks. Only one pattern from a group will ever be resolved (remember
        # that the patterns all have identical regexes), so this shared dict is used to route
        # to the correct callback for a given http method. All this hoopla is necessary since
        # patterns are resolved outside the context of a request.
        
        method_callbacks_by_regex = self.patterns_index.setdefault(patterns_id, {})
        method_callbacks = method_callbacks_by_regex.setdefault(self.regex.pattern, {})
        
        if self.method not in method_callbacks:
            method_callbacks[self.method] = {'callback': self.callback, 'default_args': self.default_args}
            self.default_args = {}
        
        # Borg-like
        self.method_callbacks = method_callbacks       

def verb_url(method, regex, view, kwargs=None, name=None, prefix=''):
    pattern_class = partial(VerbRegexURLPattern, method)
    return url_with_pattern_class(pattern_class, regex, view, kwargs, name, prefix)

########NEW FILE########
__FILENAME__ = settings

########NEW FILE########
__FILENAME__ = tests
# Copyright (c) 2010 Mark Sandstrom
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from functools import partial
import unittest

from django.conf.urls.defaults import patterns as django_patterns
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import resolve, reverse
from django.http import HttpRequest, HttpResponse

try:
    from django.views.decorators.csrf import csrf_exempt  # django >= 1.2
except ImportError:
    from django.contrib.csrf.middleware import csrf_exempt  # django < 1.2

import reroute
from reroute import patterns, url, include, reroute_patterns
from reroute.verbs import verb_url

class URLConf():
    def __init__(self, urlpatterns):
        self.urlpatterns = urlpatterns
    
def request_with_method(method, path, urlconf):
    callback, callback_args, callback_kwargs = resolve(path, urlconf)
    request = HttpRequest()
    request.method = method
    response = callback(request, *callback_args, **callback_kwargs)
    return response
    
def content_with_method(method, path, urlconf):
    response = request_with_method(method, path, urlconf)
    return response.content
    
content = partial(content_with_method, 'GET')
    
# Test views

def view_one(request):
    return HttpResponse('ONE')

def view_two(request):
    return HttpResponse('TWO')
    
def view_three(request):
    return HttpResponse('THREE')
    
def kwarg_view(request, key):
    return HttpResponse(key)
    
def generic_view(request):
    return HttpResponse('OK')
        
def method_view(request):
    return HttpResponse(request.method)
    
def wrapper_view(request):
    return HttpResponse('wrapper ' + request.WRAPPER_TEST)

@csrf_exempt
def csrf_exempt_view(request):
    return HttpResponse('OK')
    
class HandlerExistenceTestCase(unittest.TestCase):
    def test(self):
        self.assertTrue(hasattr(reroute, 'handler404'))
        self.assertTrue(hasattr(reroute, 'handler500'))
        
class DjangoCompatibilityTestCase(unittest.TestCase):
    def setUp(self):
        included_urlpatterns = patterns('tests',
            url('^included_view$', 'generic_view')
        )
        
        urlpatterns = patterns('tests',
            ('^tuple$', 'generic_view'),
            url('^url$', 'generic_view'),
            url('^non_string_view$', generic_view),
            url('^view_with_name$', 'generic_view', name='view_with_name'),
            url('^kwargs$', 'kwarg_view', kwargs={'key': 'value'}),
            url('^url_reverse$', 'view_one'),
            url('^non_string_view_reverse$', view_two),
            url('^view_with_name_reverse$', 'view_three', name='view_with_name_reverse'),
            url('^include/', include(included_urlpatterns)),
            url('^csrf_exempt_view$', csrf_exempt_view),
        )
        
        urlpatterns += patterns('',
            url('^prefix' , 'generic_view', prefix='tests'),
        )
        
        self.urlconf = URLConf(urlpatterns)
    
    def testTuple(self):
        self.assertEqual(content('/tuple', self.urlconf), 'OK')
        
    def testURL(self):
        self.assertEqual(content('/url', self.urlconf), 'OK')
        
    def testNonStringView(self):
        self.assertEqual(content('/non_string_view', self.urlconf), 'OK')
        
    def testViewWithName(self):
        self.assertEqual(content('/view_with_name', self.urlconf), 'OK')
        
    def testKwargs(self):
        self.assertEqual(content('/kwargs', self.urlconf), 'value')
        
    def testPrefix(self):
        self.assertEqual(content('/prefix', self.urlconf), 'OK')
        
    def testUrlReverse(self):
        self.assertEqual(reverse('tests.view_one', self.urlconf), '/url_reverse')
    
    def testNonStringViewReverse(self):
        self.assertEqual(reverse('tests.view_two', self.urlconf), '/non_string_view_reverse')
        
    def testNonStringViewReverse(self):
        self.assertEqual(reverse('view_with_name_reverse', self.urlconf), '/view_with_name_reverse')
        
    def testIncludedView(self):
        self.assertEqual(content('/include/included_view', self.urlconf), 'OK')

    def testCsrfExemptView(self):
        callback, callback_args, callback_kwargs = resolve('/csrf_exempt_view', self.urlconf)
        self.assertTrue(hasattr(callback, 'csrf_exempt'))
        self.assertTrue(callback.csrf_exempt, True)
        
# Wrappers

def wrapper1(view, request, *args, **kwargs):
    request.WRAPPER_TEST = '1'
    return view(request, *args, **kwargs)
    
def wrapper2(view, request, *args, **kwargs):
    request.WRAPPER_TEST += ' 2'
    return view(request, *args, **kwargs)

class ReroutePatternsTestCase(unittest.TestCase):
    def testReroutePatterns(self): 
        urlconf = URLConf(reroute_patterns([wrapper1], 'tests',
            url('^test$', 'wrapper_view')
        ))
           
        self.assertEqual(content('/test', urlconf), 'wrapper 1')
        
    def testWrapperOrder(self):       
        urlconf = URLConf(reroute_patterns([wrapper1, wrapper2], 'tests',
            url('^test$', 'wrapper_view')
        ))
        
        self.assertEqual(content('/test', urlconf), 'wrapper 1 2')
        
    def testURLWithDjangoPatternsShouldFail(self):
        urlconf = URLConf(django_patterns('tests',
            url('^test$', 'wrapper_view')
        ))
        
        self.assertRaises(ImproperlyConfigured, content, '/test', urlconf)
        
class VerbURLTestCase(unittest.TestCase):
    def setUp(self):
        included_urlpatterns = patterns('tests',
            verb_url('GET',     '^test$', 'method_view'),
            verb_url('POST',    '^test$', 'method_view')
        )
        
        self.urlconf = URLConf(patterns('tests',
            verb_url('GET',     '^test$', 'method_view'),
            verb_url('POST',    '^test$', 'method_view'),
            verb_url('PUT',     '^test$', 'method_view'),
            verb_url('DELETE',  '^test$', 'method_view'),
            verb_url('GET',     '^kwarg', 'kwarg_view', {'key': 'get view'}),
            verb_url('POST',    '^kwarg', 'kwarg_view', {'key': 'post view'}),
            url('^include/', include(included_urlpatterns))
        ))
                
    def testGet(self):
        self.assertEqual(content_with_method('GET', '/test', self.urlconf), 'GET')
        
    def testPost(self):
        self.assertEqual(content_with_method('POST', '/test', self.urlconf), 'POST')
        
    def testPut(self):
        self.assertEqual(content_with_method('PUT', '/test', self.urlconf), 'PUT')
        
    def testDelete(self):
        self.assertEqual(content_with_method('DELETE', '/test', self.urlconf), 'DELETE')
        
    def testKwargs(self):
        self.assertEqual(content_with_method('GET', '/kwarg', self.urlconf), 'get view')
        self.assertEqual(content_with_method('POST', '/kwarg', self.urlconf), 'post view')
        
    def testIncludeGet(self):
        self.assertEqual(content_with_method('GET', '/include/test', self.urlconf), 'GET')
        
    def testIncludePost(self):
        self.assertEqual(content_with_method('POST', '/include/test', self.urlconf), 'POST')
        
    def testMethodNotAllowed(self):
        response = request_with_method('PUT', '/include/test', self.urlconf)
        self.assertEqual(response.status_code, 405)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
