__FILENAME__ = main
#!/usr/bin/env python
#
# The MIT License
# 
# Copyright (c) 2009 William T. Katz
# Website/Contact: http://www.billkatz.com
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to 
# deal in the Software without restriction, including without limitation 
# the rights to use, copy, modify, merge, publish, distribute, sublicense, 
# and/or sell copies of the Software, and to permit persons to whom the 
# Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
# DEALINGS IN THE SOFTWARE.

"""A super simple Google App Engine text posting app.

Logged in visitors can add some test and search for keywords across all 
added pages.  It demos a simple full text search module.
"""
__author__ = 'William T. Katz'

import cgi
import logging

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

# The following are necessary for full-text search demo
import search
INDEXING_URL = '/tasks/searchindexing'

class Page(search.Searchable, db.Model):
    user = db.UserProperty()
    title = db.StringProperty()
    content = db.TextProperty()
    created = db.DateTimeProperty(auto_now=True)
    INDEX_TITLE_FROM_PROP = 'title'
    # INDEX_USES_MULTI_ENTITIES = False

class SimplePage(webapp.RequestHandler):
    def render(self, html):
        user = users.get_current_user()
        page = '<html><body><div style="display:inline"><a href="/">Add Page</a> | '
        if user:
            page += 'Logged in as %s ' % (user.nickname())
            logout_url = users.create_logout_url(self.request.uri)
            page += '| <a href="%s">Logout</a>' % (logout_url)
        else:
            login_url = users.create_login_url(self.request.uri)
            page += '<a href="%s">Google login</a>' % (login_url)
        page += """</div>
        <hr>
        <h3>Full Text Search Test</h3>
        <p>This app tests a full text search module for Google App Engine.
        Once you are logged in, you can add text pages that will be indexed via
        Task Queue API tasks.  The search indices are efficiently stored using
        "Relation Index" entities as described in 
        <a href="http://code.google.com/events/io/sessions/BuildingScalableComplexApps.html">
        this Google I/O talk.</a></p>
        <p>My blog has an
        <a href="http://www.billkatz.com/2009/6/Simple-Full-Text-Search-for-App-Engine">
        article on this appengine-search module</a>.  You can download the code from the
        <a href="http://github.com/DocSavage/appengine-search">appengine-search
        github repository</a> under a liberal open source (MIT) license.</p>
        <form action="/search" method="get">
            Search for phrase (e.g., 'lorem ipsum'):
        """
        page += '<input name="phrase"'
        phrase = self.request.get('phrase')
        if phrase:
            page += ' value="%s">' % (phrase)
        page += '<input type="submit" name="submitbtn" value="Return Pages">'
        page += '<input type="submit" name="submitbtn" value="Return Keys Only">'
        page += """
        <p><strong>Return Pages</strong> retrieves the entire Page entities.<br />
           <strong>Return Keys Only</strong> retrieves just the keys but uses
           intelligent key naming to transmit "Title" data via the key names.</p>
        """
        page += '</form>'
        page += html
        page += '</body></html>'
        self.response.out.write(page)

class MainPage(SimplePage):
    def get(self):
        user = users.get_current_user()
        if not user:
            html = '<h4>Please login to add a page.</h4>'
        else:
            import time
            time_string = time.strftime('Page submitted %X on %x')
            html = """
            <h4>Add a text page below:</h4>
            <form action="/" method="post">
                <div>Title: <input type="text" size="40" name="title" 
            """
            html += 'value="' + time_string + '" />'
            html += """
                <em>This data will be encoded in the key names of index entities.</em></div>
                <div><textarea name="content" rows="10" cols="60"></textarea></div>
                <div><input type="submit" value="Add Page" /></div>
            </form>
            """
        self.render(html)

    def post(self):
        user = users.get_current_user()
        content = self.request.get('content')
        title = self.request.get('title')
        if not user:
            self.redirect('/?msg=You+must+be+logged+in')
        elif not content:
            self.redirect('/')
        else:
            page = Page(content=content, title=title, user=user)
            page.put()
            page.enqueue_indexing(url=INDEXING_URL)
            html = "<div>Thanks for entering the following text:</div>"
            html += "<pre>%s</pre>" % (cgi.escape(content))
            self.render(html)

class SearchPage(SimplePage):
    def get(self):
        submitbtn = self.request.get('submitbtn')
        phrase = self.request.get('phrase')
        html = "<h4>'" + phrase + "' was found on these pages:</h4>"
        if submitbtn == 'Return Keys Only':
            key_list = Page.search(phrase, keys_only=True)
            for key_and_title in key_list:
                html += "<div><p>Title: %s</p></div>" % key_and_title[1]
        else:
            pages = Page.search(phrase)
            for page in pages:
                html += "<div><p>Title: %s</p><p>User: %s, Created: %s</p><pre>%s</pre></div>" \
                        % (page.title, str(page.user), str(page.created), cgi.escape(page.content))
        self.render(html)

application = webapp.WSGIApplication([
        ('/', MainPage),
        ('/search', SearchPage),
        (INDEXING_URL, search.SearchIndexing)], debug=True)

def main():
    run_wsgi_app(application)

if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = test_app
from webtest import TestApp
from main import application

app = TestApp(application)

def test_index():
    response = app.get('/')
    assert 'Full Text Search Test' in str(response)

########NEW FILE########
__FILENAME__ = test_search
#!/usr/bin/env python
#
# The MIT License
# 
# Copyright (c) 2009 William T. Katz
# Website/Contact: http://www.billkatz.com
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to 
# deal in the Software without restriction, including without limitation 
# the rights to use, copy, modify, merge, publish, distribute, sublicense, 
# and/or sell copies of the Software, and to permit persons to whom the 
# Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
# DEALINGS IN THE SOFTWARE.

import re
import os

LOREM_IPSUM = """
Lorem ipsum dolor sit amet, consectetur adipisicing elit, 
sed do eiusmod tempor incididunt ut labore et dolore magna 
aliqua. Ut enim ad minim veniam, quis nostrud exercitation 
ullamco laboris nisi ut aliquip ex ea commodo consequat. 
Duis aute irure dolor in reprehenderit in voluptate velit 
esse cillum dolore eu fugiat nulla pariatur. Excepteur sint 
occaecat cupidatat non proident, sunt in culpa qui officia 
deserunt mollit anim id est laborum.  Encrusted.
"""

INFLECTION_TEST = """
Guido ran up slippery ruby-encrusted monoliths in search of
the serpentine mascot.  The pythonic creatures skulked away.
How quickly did they forget their master?  Guido was
challenged by the excessively poor storyline in this fictional
tale, but alas, what could he do?  He was one of many fixtures
in ornately narrated prose doomed to be read only by
computerized algorithms implementing text processing!
"""

from google.appengine.ext import db
import search

from google.appengine.api import apiproxy_stub_map
from google.appengine.api import datastore_file_stub

def clear_datastore():
    """Clear datastore.  Can be used between tests to insure empty datastore.
    
    See code.google.com/p/nose-gae/issues/detail?id=16
    Note: the appid passed to DatastoreFileStub should match the app id in your app.yaml.
    """
    apiproxy_stub_map.apiproxy = apiproxy_stub_map.APIProxyStubMap()
    stub = datastore_file_stub.DatastoreFileStub('billkatz-test', '/dev/null', '/dev/null')
    apiproxy_stub_map.apiproxy.RegisterStub('datastore_v3', stub)

class Page(search.Searchable, db.Model):
    author_name = db.StringProperty()
    title = db.StringProperty()
    content = db.TextProperty()
    INDEX_TITLE_FROM_PROP = 'title'

class NoninflectedPage(search.Searchable, db.Model):
    """Used to test search without stemming, e.g. for precise, non-inflected words"""
    author_name = db.StringProperty()
    content = db.TextProperty()
    INDEX_STEMMING = False
    INDEX_ONLY = ['content']

class TestMisc:
    def setup(self):
        clear_datastore()

    def test_appostrophed_key(self):
        page = Page(key_name="Show Don't Tell", author_name="Pro Author",
                    content="You should always show and not tell through dialogue or narration.")
        key = page.put()
        assert str(key.name()) == "Show Don't Tell"

class TestLoremIpsum:
    def setup(self):
        clear_datastore()
        page = NoninflectedPage(author_name='John Doe', content=LOREM_IPSUM)
        page.put()
        page.index()
        assert search.LiteralIndex.all().count() == 1
        page = NoninflectedPage(author_name='Jon Favreau', 
                                content='A director that works well with writers.')
        page.put()
        page.index()
        assert search.LiteralIndex.all().count() == 2

    def teardown(self):
        pass

    def test_only_index(self):
        returned_pages = NoninflectedPage.search('John')  # Only 'content' is indexed.
        assert not returned_pages
        returned_pages = NoninflectedPage.search('lorem ipsum')
        assert returned_pages

    def test_two_word_search(self):
        returned_pages = NoninflectedPage.search('LoReM IpSuM')
        assert returned_pages and len(returned_pages) == 1
        lmatch = re.search(r'lorem', returned_pages[0].content, re.IGNORECASE)
        imatch = re.search(r'ipsum', returned_pages[0].content, re.IGNORECASE)
        assert lmatch and imatch

    def test_key_only_search(self):
        key_list = NoninflectedPage.search('LoReM ipsum', keys_only=True)
        assert isinstance(key_list, list) and len(key_list) == 1
        assert isinstance(key_list[0][0], db.Key)
        assert isinstance(key_list[0][1], basestring)

    def test_search_miss(self):
        returned_pages = NoninflectedPage.search('NowhereInDoc')
        assert not returned_pages
        returned_pages = NoninflectedPage.search('director')
        assert returned_pages
        lmatch = re.search(r'lorem', returned_pages[0].content, re.IGNORECASE)
        imatch = re.search(r'ipsum', returned_pages[0].content, re.IGNORECASE)
        assert not lmatch and not imatch

    def test_not_inflected(self):
        returned_pages = NoninflectedPage.search('encrust')
        assert not returned_pages
        returned_pages = NoninflectedPage.search('encrusted')
        assert returned_pages

class TestInflection:
    def setup(self):
        clear_datastore()
        page = Page(author_name='John Doe', content=INFLECTION_TEST)
        page.put()
        page.index()
        assert search.StemmedIndex.all().count() == 1
        page = Page(author_name='Jon Favreau', content='A director that works well with writers.')
        page.put()
        page.index()
        assert search.StemmedIndex.all().count() == 2

    def test_inflections(self):
        def check_inflection(word1, word2):
            returned_pages = Page.search(word1)
            assert returned_pages
            assert re.search(word2, returned_pages[0].content, re.IGNORECASE)
        check_inflection('algorithm', 'algorithms')
        check_inflection('python', 'pythonic')
        check_inflection('rubies', 'ruby')
        check_inflection('encrust', 'encrusted')

class TestBigIndex:
    def setup(self):
        clear_datastore()

    def test_multientity_index(self):
        curdir = os.path.abspath(os.path.dirname(__file__))
        bigtextfile = os.path.join(curdir, 'roget.txt')
        import codecs
        bigfile = codecs.open(bigtextfile, 'r', 'utf-8')
        bigtext = bigfile.read()
        words_to_use = 4 * search.MAX_ENTITY_SEARCH_PHRASES
        words = bigtext.split()
        Page.INDEX_USES_MULTI_ENTITIES = True
        page = Page(key_name="Foo", content=' '.join(words[0:words_to_use]))
        page.put()
        page.index()
        assert search.StemmedIndex.all().count() > 1
        page = Page(key_name="Foo", content=INFLECTION_TEST)
        page.put()
        page.index()
        assert search.StemmedIndex.all().count() == 1

class TestKeyOnlySearch:
    def setup(self):
        clear_datastore()
        self.pages = [{
            'key_name': 'test1',
            'content': 'This post has no title at all.'
        }, {
            'key_name': 'test2',
            'title': 'Second Post',
            'content': 'This is some text for the second post.'
        }, {
            'key_name': 'test3',
            'title': 'Third Post',
            'content': 'This is some text for the third post.  The last post.'
        }]
        for page_dict in self.pages:
            page = Page(**page_dict)
            page.put()
            page.index()
        assert search.StemmedIndex.all().count() == 3

    def test_default_titling(self):
        page_list = Page.search('no title', keys_only=True)
        assert len(page_list) == 1
        assert page_list[0][0].name() == 'test1'
        assert page_list[0][1] == 'Page test1'  # Default titling

    def test_title_from_parent(self):
        page_list = Page.search('last', keys_only=True)
        assert len(page_list) == 1
        assert page_list[0][0].name() == 'test3'
        assert page_list[0][1] == 'Third Post'

    def test_title_change(self):
        pages = Page.search('second post')
        assert len(pages) == 1
        page = pages[0]
        page.title = 'My Great New Title'
        old_key = page.put()
        page.indexed_title_changed()
        assert search.StemmedIndex.all().count() == 3
        page_list = Page.search('second post', keys_only=True)
        assert len(page_list) == 1
        assert page_list[0][1] == 'My Great New Title'
        assert page_list[0][0].id_or_name() == old_key.id_or_name()

class TestMultiWordSearch:
    def setup(self):
        clear_datastore()
        page = Page(key_name='doetext', author_name='John Doe', 
                    content=INFLECTION_TEST)
        page.put()
        page.index()
        assert search.StemmedIndex.all().count() == 1
        page = Page(key_name="statuetext", 
                    author_name='Other Guy', content="""
        This is the time for all good python programmers to check,
        to test, to go forward and throw junk at the code, and in
        so doing, try to find errors.
          -- Unheralded inscription at base of Statue of Liberty
        """)
        page.put()
        page.index()
        assert search.StemmedIndex.all().count() == 2
        page = Page(key_name="statuetext2", 
                    author_name='Another Guy', content="""
        I have seen a statue and it declares there should be
        liberty in the world.
        """)
        page.put()
        page.index()
        assert search.StemmedIndex.all().count() == 3

    def test_multiword_search_order(self):
        returned_pages = Page.search('statue of liberty')
        assert len(returned_pages) == 2
        print "Returned pages: %s" % [page.key().name() for page in returned_pages]
        assert returned_pages[0].key().name() == u'statuetext'
        assert returned_pages[1].key().name() == u'statuetext2'

    def test_multiword_search_fail(self):
        returned_pages = Page.search('statue of liberty biggy word')
        assert not returned_pages
        
    def test_multiword_search_and(self):
        returned_pages = Page.search('statue of liberty python')
        assert len(returned_pages) == 1
        assert returned_pages[0].key().name() == u'statuetext'

    def test_two_word_search(self):
        returned_pages = Page.search('ornately narrated')
        assert len(returned_pages) == 1
        assert returned_pages[0].key().name() == u'doetext'

     
########NEW FILE########
