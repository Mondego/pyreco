__FILENAME__ = commands
# Copyright 2013 django-htmlmin authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import argparse
import os
from htmlmin.minify import html_minify

my_dir = os.getcwd()


def main():
    parser = argparse.ArgumentParser(
        description=u'Minify content of HTML files',
    )
    parser.add_argument('filename', metavar='filename', type=str, nargs=1)
    parser.add_argument('--keep-comments', action='store_true')
    args = parser.parse_args()

    content = ""
    with open(os.path.join(my_dir, args.filename[0])) as html_file:
        content = html_file.read()

    print html_minify(content, ignore_comments=not args.keep_comments)

########NEW FILE########
__FILENAME__ = decorators
# Copyright 2013 django-htmlmin authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

from functools import wraps
from htmlmin.minify import html_minify


def minified_response(f):
    @wraps(f)
    def minify(*args, **kwargs):
        response = f(*args, **kwargs)
        minifiable_status = response.status_code == 200
        minifiable_content = 'text/html' in response['Content-Type']
        if minifiable_status and minifiable_content:
            response.content = html_minify(response.content)
        return response

    return minify


def not_minified_response(f):
    @wraps(f)
    def not_minify(*args, **kwargs):
        response = f(*args, **kwargs)
        response.minify_response = False
        return response

    return not_minify

########NEW FILE########
__FILENAME__ = middleware
# Copyright 2013 django-htmlmin authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import re
from htmlmin.minify import html_minify
from django.conf import settings


class MarkRequestMiddleware(object):
    
    def process_request(self, request):
        request._hit_htmlmin = True


class HtmlMinifyMiddleware(object):

    def can_minify_response(self, request, response):
        try:
            req_ok = request._hit_htmlmin
        except AttributeError:
            return False

        if hasattr(settings, 'EXCLUDE_FROM_MINIFYING'):
            for url_pattern in settings.EXCLUDE_FROM_MINIFYING:
                regex = re.compile(url_pattern)
                if regex.match(request.path.lstrip('/')):
                    req_ok = False
                    break

        resp_ok = response.status_code == 200
        resp_ok = resp_ok and 'text/html' in response['Content-Type']
        if hasattr(response, 'minify_response'):
            resp_ok = resp_ok and response.minify_response
        return req_ok and resp_ok

    def process_response(self, request, response):
        minify = getattr(settings, "HTML_MINIFY", not settings.DEBUG)
        keep_comments = getattr(settings, 'KEEP_COMMENTS_ON_MINIFYING', False)
        parser = getattr(settings, 'HTML_MIN_PARSER', 'html5lib')
        if minify and self.can_minify_response(request, response):
            response.content = html_minify(response.content,
                                           ignore_comments=not keep_comments,
                                           parser=parser)
        return response

########NEW FILE########
__FILENAME__ = minify
# -*- coding: utf-8 -*-

# Copyright 2013 django-htmlmin authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import re

import bs4

from .util import force_decode

EXCLUDE_TAGS = set(["pre", "script", "textarea"])
# element list coming from
# https://developer.mozilla.org/en-US/docs/Web/Guide/HTML/HTML5/HTML5_element_list
# combining text-level semantics & edits
TEXT_FLOW = set(["a", "em", "strong", "small", "s", "cite", "q", "dfn", "abbr", "data", "time", "code", "var", "samp", "kbd", "sub", "i", "b", "u", "mark", "ruby", "rt", "rp", "bdi", "bdo", "span", "br", "wbr", "ins", "del"])

# fold the doctype element, if True then no newline is added after the
# doctype element. If False, a newline will be insterted
FOLD_DOCTYPE = True
re_multi_space = re.compile(r'\s+', re.MULTILINE|re.UNICODE)
re_single_nl = re.compile(r'^\n$', re.MULTILINE|re.UNICODE)
re_only_space = re.compile(r'^\s+$', re.MULTILINE|re.UNICODE)
re_start_space = re.compile(r'^\s+', re.MULTILINE|re.UNICODE)
re_end_space = re.compile(r'\s+$', re.MULTILINE|re.UNICODE)
# see http://en.wikipedia.org/wiki/Conditional_comment
re_cond_comment = re.compile(r'\[if .*\]>.*<!\[endif\]',
                             re.MULTILINE|re.DOTALL|re.UNICODE)
re_cond_comment_start_space = re.compile(r'(\[if .*\]>)\s+',
    re.MULTILINE|re.DOTALL|re.UNICODE)
re_cond_comment_end_space = re.compile(r'\s+(<!\[endif\])',
    re.MULTILINE|re.DOTALL|re.UNICODE)


def html_minify(html_code, ignore_comments=True, parser="html5lib"):
    html_code = force_decode(html_code)
    soup = bs4.BeautifulSoup(html_code, parser)
    mini_soup = space_minify(soup, ignore_comments)
    if FOLD_DOCTYPE is True:
        # monkey patching to remove new line after doctype
        bs4.element.Doctype.SUFFIX = u'>'
    return unicode(mini_soup)

def space_minify(soup, ignore_comments=True):
    """recursive function to reduce space characters in html code.

    :param soup: a BeautifulSoup of the code to reduce
    :type soup: bs4.BeautifulSoup
    :param ignore_comments: whether or not to keep comments in the
                            result
    :type ignore_comments: bool
    """
    # if tag excluded from minification, just pass
    if str(soup.name) in EXCLUDE_TAGS:
        return

    # loop through childrens of this element
    if hasattr(soup, 'children'):
        for child in soup.children:
            space_minify(child, ignore_comments)

    # if the element is a string ...
    if is_navstr(soup):
        # ... but not a comment, CData, Doctype or others (see
        # bs4/element.py for list).
        if not is_prestr(soup):
            # reduce multiple space characters
            new_string = re_multi_space.sub(' ', soup.string)
            (prev_flow, next_flow) = is_inflow(soup)
            # if the string is in a flow of text, don't remove lone
            # spaces
            if prev_flow and next_flow:
                new_string = re_only_space.sub(' ', new_string)
            # else, remove spaces, they are between grouping, section,
            # metadata or other types of block
            else:
                new_string = re_only_space.sub('', new_string)
            # if the previous element is not text then remove leading
            # spaces
            if prev_flow:
                new_string = re_start_space.sub(' ', new_string)
            else:
                new_string = re_start_space.sub('', new_string)
            # if the previous element is not text then remove leading
            # spaces
            if next_flow:
                new_string = re_end_space.sub(' ', new_string)
            else:
                new_string = re_end_space.sub('', new_string)
            # bs4 sometimes add a lone newline in the body
            new_string = re_single_nl.sub('', new_string)
            soup.string.replace_with(new_string)
        # Conditional comment content is HTML code so it should be
        # minified
        elif is_cond_comment(soup):
            new_string = re_multi_space.sub(' ', soup.string)
            new_string = re_cond_comment_start_space.sub(r'\1',
                                                         new_string)
            new_string = re_cond_comment_end_space.sub(r'\1', new_string)
            new_comment = bs4.element.Comment(new_string)
            soup.string.replace_with(new_comment)
        # if ignore_comments is True and this is a comment but not a
        # conditional comment and
        elif ignore_comments == True and is_comment(soup):
            # remove the element
            soup.string.replace_with(u'')
    return soup

def is_navstr(soup):
    """test whether an element is a NavigableString or not, return a
    boolean.

    :param soup: a BeautifulSoup of the code to reduce
    :type soup: bs4.BeautifulSoup
    """
    return isinstance(soup, bs4.element.NavigableString)

def is_prestr(soup):
    """test whether an element is a PreformattedString or not, return a
    boolean.

    :param soup: a BeautifulSoup of the code to reduce
    :type soup: bs4.BeautifulSoup
    """
    return isinstance(soup, bs4.element.PreformattedString)

def is_comment(soup):
    """test whether an element is a Comment, return a boolean.

    :param soup: a BeautifulSoup of the code to reduce
    :type soup: bs4.BeautifulSoup
    """
    return isinstance(soup, bs4.element.Comment) \
        and not re_cond_comment.search(soup.string)

def is_cond_comment(soup):
    """test whether an element is a conditional comment, return a
    boolean.

    :param soup: a BeautifulSoup of the code to reduce
    :type soup: bs4.BeautifulSoup
    """
    return isinstance(soup, bs4.element.Comment) \
        and re_cond_comment.search(soup.string)

def is_inflow(soup):
    """test whether an element belongs to a text flow, returns a tuple
    of two booleans describing the flow around the element. The first
    boolean represents the flow before the element, the second boolean
    represents the flow after the element.

    :param soup: a BeautifulSoup of the code to reduce
    :type soup: bs4.BeautifulSoup
    """
    if soup.previous_sibling is not None and \
        soup.previous_sibling.name in TEXT_FLOW:
        prev_flow = True
    else:
        prev_flow = False
    if soup.next_sibling is not None and \
        soup.next_sibling.name in TEXT_FLOW:
        next_flow = True
    else:
        next_flow = False

    return (prev_flow, next_flow)

########NEW FILE########
__FILENAME__ = mocks
# Copyright 2013 django-htmlmin authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.


class RequestMock(object):

    def __init__(self, path="/"):
        self.path = path
        self._hit_htmlmin = True


class RequestBareMock(object):

    def __init__(self, path="/"):
        self.path = path


class ResponseMock(dict):

    def __init__(self, *args, **kwargs):
        super(ResponseMock, self).__init__(*args, **kwargs)
        self['Content-Type'] = 'text/html'

    status_code = 200
    content = "<html>   <body>some text here</body>    </html>"


class ResponseWithCommentMock(ResponseMock):
    content = "<html>   <!-- some comment --><body>some " + \
              "text here</body>    </html>"

########NEW FILE########
__FILENAME__ = mock_settings
# Copyright 2012 django-htmlmin authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

EXCLUDE_FROM_MINIFYING = ('^raw',)

DATABASE_NAME = 'htmlmin.db'
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DATABASE_NAME,
    },
}
DEBUG = True
HTML_MINIFY = True
ROOT_URLCONF = 'htmlmin.tests.pico_django'
KEEP_COMMENTS_ON_MINIFYING = True
SECRET_KEY = "sosecret"
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
   }
}

########NEW FILE########
__FILENAME__ = mock_settings_without_exclude
# Copyright 2012 django-htmlmin authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

########NEW FILE########
__FILENAME__ = pico_django
# -*- coding: utf-8 -*-

# Copyright 2013 django-htmlmin authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

'''
File: pico_django.py
Description: Code based on snippet available in the link below.
    https://github.com/readevalprint/mini-django/blob/master/pico_django.py
'''

from django.http import HttpResponse
from django.conf.urls.defaults import patterns
from htmlmin.decorators import minified_response, not_minified_response

CONTENT = '''
<html>
    <body>
        <p>Hello world! :D</p>
        <div>Copyright 3000</div>
    </body>
</html>
    '''


@minified_response
def minified(request):
    return HttpResponse(CONTENT)


@not_minified_response
def not_minified(request):
    return HttpResponse(CONTENT)


def raw(request):
    return HttpResponse(CONTENT)

urlpatterns = patterns('',
                       (r'^min$', minified),
                       (r'^raw$', raw),
                       (r'^not_min$', not_minified))

########NEW FILE########
__FILENAME__ = test_decorator
# Copyright 2013 django-htmlmin authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import unittest
from django.test.client import Client
from nose.tools import assert_equals


class TestDecorator(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = Client()

    def test_should_minify_the_content_of_a_view_decorated(self):
        response = self.client.get('/min')
        minified = '<html><head></head><body><p>Hello world! :D' + \
                   '</p><div>Copyright 3000</div></body></html>'
        assert_equals(minified, response.content)

    def should_not_touch_the_content_of_an_undecorated_view(self):
        expected = '''
<html>
    <body>
        <p>Hello world! :D</p>
        <div>Copyright 3000</div>
    </body>
</html>
    '''
        response = self.client.get('/raw')
        assert_equals(expected, response.content)

    def test_minify_response_should_be_false_in_not_minified_views(self):
        response = self.client.get('/not_min')
        assert_equals(False, response.minify_response)

########NEW FILE########
__FILENAME__ = test_middleware
# Copyright 2013 django-htmlmin authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import os
import sys
import unittest
from django.conf import settings
from htmlmin.middleware import HtmlMinifyMiddleware, MarkRequestMiddleware
from htmlmin.tests import TESTS_DIR
from mocks import RequestMock, RequestBareMock, ResponseMock, ResponseWithCommentMock


class TestMiddleware(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, TESTS_DIR)
        os.environ['DJANGO_SETTINGS_MODULE'] = 'mock_settings'

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(TESTS_DIR)
        del os.environ['DJANGO_SETTINGS_MODULE']

    def test_should_minify_only_when_status_code_is_200(self):
        response_mock = ResponseMock()
        response_mock.status_code = 301
        response = HtmlMinifyMiddleware().process_response(
            RequestMock(), response_mock,
        )

        html_not_minified = "<html>   <body>some text here</body>    </html>"
        self.assertEqual(html_not_minified, response.content)

    def test_should_minify_response_when_mime_type_is_html(self):
        response_mock = ResponseMock()
        response = HtmlMinifyMiddleware().process_response(
            RequestMock(), response_mock,
        )

        minified = "<html><head></head><body>some text here</body></html>"
        self.assertEqual(minified, response.content)

    def test_should_minify_with_any_charset(self):
        response_mock = ResponseMock()
        response_mock['Content-Type'] = 'text/html; charset=utf-8'
        response = HtmlMinifyMiddleware().process_response(
            RequestMock(), response_mock,
        )

        minified = "<html><head></head><body>some text here</body></html>"
        self.assertEqual(minified, response.content)

    def test_should_not_minify_not_html_content(self):
        response_mock = ResponseMock()
        response_mock['Content-Type'] = 'application/json'
        response = HtmlMinifyMiddleware().process_response(
            RequestMock(), response_mock,
        )

        html_not_minified = "<html>   <body>some text here</body>    </html>"
        self.assertEqual(html_not_minified, response.content)

    def test_should_not_minify_url_marked_as_not_minifiable(self):
        html_not_minified = "<html>   <body>some text here</body>    </html>"
        response_mock = ResponseMock()
        response = HtmlMinifyMiddleware().process_response(
            RequestMock('/raw/'), response_mock,
        )
        self.assertEqual(html_not_minified, response.content)

    def test_should_minify_if_exclude_from_minifying_is_unset(self):
        old = settings.EXCLUDE_FROM_MINIFYING
        del settings.EXCLUDE_FROM_MINIFYING

        minified = "<html><head></head><body>some text here</body></html>"
        response = HtmlMinifyMiddleware().process_response(
            RequestMock(), ResponseMock(),
        )
        self.assertEqual(minified, response.content)

        settings.EXCLUDE_FROM_MINIFYING = old

    def test_should_not_minify_response_with_minify_response_false(self):
        html_not_minified = "<html>   <body>some text here</body>    </html>"
        response_mock = ResponseMock()
        response_mock.minify_response = False
        response = HtmlMinifyMiddleware().process_response(
            RequestMock(), response_mock,
        )
        self.assertEqual(html_not_minified, response.content)

    def test_should_minify_response_with_minify_response_true(self):
        minified = "<html><head></head><body>some text here</body></html>"
        response_mock = ResponseMock()
        response_mock.minify_response = True
        response = HtmlMinifyMiddleware().process_response(
            RequestMock(), response_mock,
        )
        self.assertEqual(minified, response.content)

    def test_should_keep_comments_when_they_are_enabled(self):
        old = settings.KEEP_COMMENTS_ON_MINIFYING
        settings.KEEP_COMMENTS_ON_MINIFYING = True

        minified = "<html><!-- some comment --><head></head><body>" + \
                   "some text here</body></html>"
        response_mock = ResponseWithCommentMock()
        response = HtmlMinifyMiddleware().process_response(
            RequestMock(), response_mock,
        )
        self.assertEqual(minified, response.content)

        settings.KEEP_COMMENTS_ON_MINIFYING = old

    def test_should_remove_comments_they_are_disabled(self):
        old = settings.KEEP_COMMENTS_ON_MINIFYING
        settings.KEEP_COMMENTS_ON_MINIFYING = False

        minified = "<html><head></head><body>some text here</body></html>"
        response_mock = ResponseWithCommentMock()
        response = HtmlMinifyMiddleware().process_response(
            RequestMock(), response_mock,
        )
        self.assertEqual(minified, response.content)

        settings.KEEP_COMMENTS_ON_MINIFYING = old

    def test_should_remove_comments_when_the_setting_is_not_specified(self):
        old = settings.KEEP_COMMENTS_ON_MINIFYING
        del settings.KEEP_COMMENTS_ON_MINIFYING

        minified = "<html><head></head><body>some text here</body></html>"
        response_mock = ResponseWithCommentMock()
        response = HtmlMinifyMiddleware().process_response(
            RequestMock(), response_mock,
        )
        self.assertEqual(minified, response.content)

        settings.KEEP_COMMENTS_ON_MINIFYING = old

    def test_should_not_minify_if_the_HTML_MINIFY_setting_is_false(self):
        old = settings.HTML_MINIFY
        settings.HTML_MINIFY = False
        expected_output = "<html>   <body>some text here</body>    </html>"

        response = HtmlMinifyMiddleware().process_response(
            RequestMock(), ResponseMock(),
        )
        self.assertEqual(expected_output, response.content)

        settings.HTML_MINIFY = old

    def test_should_not_minify_when_DEBUG_is_enabled(self):
        old = settings.HTML_MINIFY
        old_debug = settings.DEBUG
        del settings.HTML_MINIFY
        settings.DEBUG = True

        expected_output = "<html>   <body>some text here</body>    </html>"

        response = HtmlMinifyMiddleware().process_response(
            RequestMock(), ResponseMock(),
        )
        self.assertEqual(expected_output, response.content)

        settings.DEBUG = old_debug
        settings.HTML_MINIFY = old

    def test_should_minify_when_DEBUG_is_false_and_MINIFY_is_unset(self):
        old = settings.HTML_MINIFY
        old_debug = settings.DEBUG
        del settings.HTML_MINIFY
        settings.DEBUG = False

        minified = "<html><head></head><body>some text here</body></html>"

        response = HtmlMinifyMiddleware().process_response(
            RequestMock(), ResponseMock(),
        )
        self.assertEqual(minified, response.content)

        settings.DEBUG = old_debug
        settings.HTML_MINIFY = old

    def test_should_set_flag_when_request_hits_middleware(self):
        request_mock = RequestBareMock()
        MarkRequestMiddleware().process_request(request_mock)
        self.assertTrue(request_mock._hit_htmlmin)

    def test_should_not_minify_when_request_did_not_hit_middleware(self):
        expected_output = "<html>   <body>some text here</body>    </html>"

        request_mock = RequestBareMock()
        response = HtmlMinifyMiddleware().process_response(
            request_mock, ResponseMock(),
        )
        self.assertEqual(expected_output, response.content)

########NEW FILE########
__FILENAME__ = test_minify
# -*- coding: utf-8 -*-

# Copyright 2013 django-htmlmin authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import codecs
import unittest

from htmlmin.minify import html_minify
from os.path import abspath, dirname, join

resources_path = lambda *paths: abspath(join(dirname(__file__),
                                             'resources', *paths))


class TestMinify(unittest.TestCase):

    def _normal_and_minified(self, filename):
        html_file = resources_path('%s.html' % filename)
        html_file_minified = resources_path('%s_minified.html' % filename)

        html = open(html_file).read()
        f_minified = codecs.open(html_file_minified, encoding='utf-8')

        return html, f_minified.read().strip('\n')

    def test_complete_html_should_be_minified(self):
        html, minified = self._normal_and_minified('with_menu')
        self.assertEqual(minified, html_minify(html))

    def test_html_with_blank_lines_should_be_minify(self):
        html, minified = self._normal_and_minified('with_blank_lines')
        self.assertEqual(minified, html_minify(html))

    def test_should_not_minify_content_from_script_tag(self):
        html, minified = self._normal_and_minified('with_javascript')
        self.assertEqual(minified, html_minify(html))

    def test_should_not_convert_entity_the_content_of_script_tag(self):
        html, minified = self._normal_and_minified('with_html_content_in_javascript')
        self.assertEqual(minified, html_minify(html))

    def test_should_not_minify_content_from_pre_tag(self):
        html, minified = self._normal_and_minified('with_pre')
        self.assertEqual(minified, html_minify(html))

    def test_should_not_convert_entity_the_content_of_pre_tag(self):
        html, minified = self._normal_and_minified('with_html_content_in_pre')
        self.assertEqual(minified, html_minify(html))

    def test_should_not_minify_content_from_textarea(self):
        html, minified = self._normal_and_minified('with_textarea')
        result = html_minify(html)
        self.assertEqual(minified, result)

    def test_should_convert_to_entities_the_content_of_textarea_tag(self):
        html, minified = self._normal_and_minified('with_html_content_in_textarea')
        result = html_minify(html)
        self.assertEqual(minified, result)

    def test_should_not_convert_entities_within_textarea_tag(self):
        html, minified = self._normal_and_minified('with_entities_in_textarea')
        result = html_minify(html)
        self.assertEqual(minified, result)

    def test_should_not_drop_blank_lines_from_the_begin_of_a_textarea(self):
        t = 'with_textarea_with_blank_lines'
        html, minified = self._normal_and_minified(t)
        result = html_minify(html)
        self.assertEqual(minified, result)

    def test_html_should_be_minified(self):
        html = "<html>   <body>some text here</body>    </html>"
        minified = "<html><head></head><body>some text here</body></html>"
        self.assertEqual(minified, html_minify(html))

    def test_minify_function_should_return_a_unicode_object(self):
        html = "<html>   <body>some text here</body>    </html>"
        minified = html_minify(html)
        self.assertEqual(unicode, type(minified))

    def test_minify_should_respect_encoding(self):
        html, minified = self._normal_and_minified('blogpost')
        self.assertEqual(minified, html_minify(html))

    def test_minify_should_not_prepend_doctype_when_its_not_present(self):
        html, minified = self._normal_and_minified('without_doctype')
        self.assertEqual(minified, html_minify(html))

    def test_minify_should_keep_doctype_when_its_present(self):
        html, minified = self._normal_and_minified('with_old_doctype')
        self.assertEqual(minified, html_minify(html))

    def test_should_exclude_comments_by_default(self):
        html, minified = self._normal_and_minified('with_comments_to_exclude')
        self.assertEqual(minified, html_minify(html))

    def test_should_be_able_to_not_exclude_comments(self):
        html, minified = self._normal_and_minified('with_comments')
        self.assertEqual(minified, html_minify(html, ignore_comments=False))

    def test_should_be_able_to_exclude_multiline_comments(self):
        t = 'with_multiple_line_comments'
        html, minified = self._normal_and_minified(t)
        self.assertEqual(minified, html_minify(html))

    def test_should_be_able_to_exclude_multiple_comments_on_a_page(self):
        html, minified = self._normal_and_minified('with_multiple_comments')
        self.assertEqual(minified, html_minify(html))

    def test_should_not_exclude_conditional_comments(self):
        html, minified = self._normal_and_minified('with_conditional_comments')
        self.assertEqual(minified, html_minify(html))

    def test_should_not_rm_multiline_conditional_comments(self):
        html, minified = self._normal_and_minified('with_multiple_line_conditional_comments')
        self.assertEqual(minified, html_minify(html))

    def test_should_touch_attributes_only_on_tags(self):
        html = '<html>\n    <body>I selected you!</body>\n    </html>'
        minified = '<html><head></head><body>I selected you!</body></html>'
        self.assertEqual(minified, html_minify(html))

    def test_should_be_able_to_minify_html5_tags(self):
        html, minified = self._normal_and_minified('html5')
        self.assertEqual(minified, html_minify(html))

    def test_should_transform_multiple_spaces_in_one(self):
        html, minified = self._normal_and_minified('multiple_spaces')
        self.assertEqual(minified, html_minify(html))

    def test_should_convert_line_break_to_whitespace(self):
        html, minified = self._normal_and_minified('line_break')
        self.assertEqual(minified, html_minify(html))

    def test_should_keep_new_line_as_space_when_minifying(self):
        html = '<html><body>Click <a href="#">here</a>\nto see ' +\
               'more</body></html>'
        minified = '<html><head></head><body>Click <a href="#">here</a> to ' +\
                   'see more</body></html>'
        got_html = html_minify(html)
        self.assertEqual(minified, got_html)

    def test_should_not_produce_two_spaces_in_new_line(self):
        html = '<html><body>Click <a href="#">here</a> \nto see more' +\
               '</body></html>'
        minified = '<html><head></head><body>Click <a href="#">here' + \
                   '</a> to see more</body></html>'
        got_html = html_minify(html)
        self.assertEqual(minified, got_html)

    def test_non_ascii(self):
        html, minified = self._normal_and_minified('non_ascii')
        self.assertEqual(minified, html_minify(html))

    def test_non_ascii_in_excluded_element(self):
        html, minified = self._normal_and_minified(
            'non_ascii_in_excluded_element'
        )
        self.assertEqual(minified, html_minify(html))


########NEW FILE########
__FILENAME__ = test_util
# -*- coding: utf-8 -*-

# Copyright 2013 django-htmlmin authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import unittest
from htmlmin.util import force_decode, between_two_tags


class TestUtil(unittest.TestCase):

    def test_should_decode_a_utf8_string(self):
        string = "Blá blá"
        self.assertEqual(u"Blá blá", force_decode(string))

    def test_shoulde_decode_a_latin_string(self):
        unicode_object = "Blá blá".decode("utf-8").encode("latin-1")
        string = str(unicode_object)
        self.assertEqual(u"Blá blá", force_decode(string))

    def test_should_be_able_to_chose_the_encoding(self):
        ENCODING = 'IBM857'
        unicode_object = "Blá blá".decode("utf-8").encode(ENCODING)
        string = str(unicode_object)
        self.assertEqual(u"Blá blá", force_decode(string, encoding=ENCODING))

    def test_should_be_between_two_tags(self):
        all_lines = [
            '<script type="text/javascript">',
            'alert("Hello World!");',
            '</script>',
            '<p>Hello ',
            'World!</p>'
            ]
        self.assertTrue(between_two_tags(all_lines[1], all_lines, 1))

    def test_should_not_be_between_two_tags(self):
        all_lines = [
            '<script type="text/javascript">',
            'alert("Hello World!");',
            '</script>',
            '<p>Hello ',
            'World!</p>'
            ]
        self.assertFalse(between_two_tags(all_lines[4], all_lines, 4))

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-
# Copyright 2013 django-htmlmin authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.


def force_decode(string, encoding="utf-8"):
    for c in (encoding, "utf-8", "latin-1"):
        try:
            return string.decode(c)
        except (UnicodeDecodeError, UnicodeEncodeError):
            pass


def between_two_tags(current_line, all_lines, index):
    st = current_line and not current_line.startswith('<')
    if st and not all_lines[index - 1].endswith('>'):
        return False
    return True

########NEW FILE########
