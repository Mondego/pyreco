__FILENAME__ = admin
from django.contrib import admin
from lifeflow.models import *


class CommentAdmin(admin.ModelAdmin):
    list_display = ('entry', 'name', 'email', 'webpage', 'date')
    search_fields = ['name', 'email','body']
    
admin.site.register(Comment, CommentAdmin)

class AuthorAdmin(admin.ModelAdmin):
    list_display = ('name', 'link')
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    
admin.site.register(Author, AuthorAdmin)

class EntryAdmin(admin.ModelAdmin):
    list_display = ('title', 'pub_date')
    search_fields = ['title', 'summary', 'body']
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('flows','tags','series','resources','authors')
    fieldsets = (
        (None, {'fields' : ('title', 'slug', 'pub_date',)}),
        ('Content', {'fields': ('summary', 'body',)}),
        ('Options', {'fields': ('use_markdown', 'is_translation', 'send_ping', 'allow_comments', ), 'classes': 'collapse'}),
        ('Authors', {'fields' : ('authors',), 'classes': 'collapse'}),
        ('Resources', {'fields' : ('resources',), 'classes': 'collapse'}),
        ('Series', {'fields': ('series',), 'classes': 'collapse'}),
        ('Organization', {'fields': ('flows', 'tags',),}),
        )
        
admin.site.register(Entry, EntryAdmin)


class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'language', 'license', 'size',)
    search_fields = ['title', 'summary', 'body']
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('resources',)
    fieldsets = (
        (None, {'fields' : ('title', 'slug', 'size', 'language', 'license', 'use_markdown',)} ),
        ('Content', {'fields': ('summary', 'body', 'resources')} ),
        )

admin.site.register(Project, ProjectAdmin)

# Custom admins required due to slug field
class SeriesAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
admin.site.register(Series, SeriesAdmin)

class TagAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
admin.site.register(Tag, TagAdmin)

class FlowAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)} 
admin.site.register(Flow, FlowAdmin)

class LanguageAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
admin.site.register(Language, LanguageAdmin)

# Simple admin interfaces
admin.site.register(Resource)
admin.site.register(RecommendedSite)
admin.site.register(SiteToNotify)
admin.site.register(Translation)
########NEW FILE########
__FILENAME__ = akismet
#!/usr/bin/python

__version__ = "0.3"
__date__ = "2005-12-01"
__author__ = "David Lynch (kemayo AT Google's mail service DOT com)"
__copyright__ = "Copyright 2005, David Lynch"
__license__ = "Python"
__history__ = """
0.3 - 20051205 - Cleaned up __post.
0.2 - 20051201 - Added documentation, and tweaked the circumstances where an error
    will be thrown.
0.1 - 20051201 - Initial release.  Everything pretty much works.  Probably.
"""

import httplib
from urllib import urlencode

USERAGENT = ""
AKISMET_URL = "rest.akismet.com"
AKISMET_PORT = 80

class AkismetError(Exception):
    def __init__(self, response, statuscode):
        self.response = response
        self.statuscode = statuscode
    def __str__(self):
         return repr(self.value)

def __post(request, host, path, port = 80):
    connection = httplib.HTTPConnection(host, port)
    connection.request("POST", path, request,
        {"User-Agent":"%s | %s/%s" % (USERAGENT,"Akistmet.py", __version__),
        "Content-type":"application/x-www-form-urlencoded"})
    response = connection.getresponse()
    
    return response.read(), response.status

def verify_key(key, blog):
    """Find out whether a given WordPress.com API key is valid.
    Required parameters:
        key: A WordPress.com API key.
        blog: URL of the front page of the site comments will be submitted to.
    Returns True if a valid key, False if invalid.
    """
    response, status = __post("key=%s&blog=%s" % (key,blog), AKISMET_URL, "/1.1/verify-key", AKISMET_PORT)
    
    if response == "valid":
        return True
    elif response == "invalid":
        return False
    else:
        raise AkismetError(response, status)

def comment_check(key, blog, user_ip, user_agent, **other):
    """Submit a comment to find out whether Akismet thinks that it's spam.
    Required parameters:
        key: A valid WordPress.com API key, as tested with verify_key().
        blog: URL of the front page of the site the comment will appear on.
        user_ip: IP address of the being which submitted the comment.
        user_agent: User agent reported by said being.
    Suggested "other" keys: "permalink", "referrer", "comment_type", "comment_author",
    "comment_author_email", "comment_author_url", "comment_content", and any other HTTP
    headers sent from the client.
    More detail on what should be submitted is available at:
    http://akismet.com/development/api/
    
    Returns True if spam, False if ham.  Throws an AkismetError if the server says
    anything unexpected.
    """
    
    request = {'blog': blog, 'user_ip': user_ip, 'user_agent': user_agent}
    request.update(other)
    response, status = __post(urlencode(request), "%s.%s" % (key,AKISMET_URL), "/1.1/comment-check", AKISMET_PORT)
    
    if response == "true":
        return True
    elif response == "false":
        return False
    else:
        raise AkismetError(response, status)

def submit_spam(key, blog, user_ip, user_agent, **other):
    """Report a false negative to Akismet.
    Same arguments as comment_check.
    Doesn't return anything.  Throws an AkismetError if the server says anything.
    """
    request = {'blog': blog, 'user_ip': user_ip, 'user_agent': user_agent}
    request.update(other)
    response, status = __post(urlencode(request), "%s.%s" % (key,AKISMET_URL), "/1.1/submit-spam", AKISMET_PORT)
    if status != 200 or response != "":
        raise AkismetError(response, status)

def submit_ham(key, blog, user_ip, user_agent, **other):
    """Report a false positive to Akismet.
    Same arguments as comment_check.
    Doesn't return anything.  Throws an AkismetError if the server says anything.
    """
    request = {'blog': blog, 'user_ip': user_ip, 'user_agent': user_agent}
    request.update(other)
    response, status = __post(urlencode(request), "%s.%s" % (key,AKISMET_URL), "/1.1/submit-ham", AKISMET_PORT)
    if status != 200 or response != "":
        raise AkismetError(response, status)

########NEW FILE########
__FILENAME__ = captcha
__license__ = """Copyright (c) 2007 Will R Larson

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE."""


__author__ = "Will R Larson"
__email__ = "lethain at google's email service"
__description__ = "A library for generating simple text-only captchas."
__api__ = """

The API for a captcha is two methods:

check(answer) --> True or False
question --> either a human or html formatted string
             that represents the question being asked
"""

__todo__ = """
MissingColorCaptcha

Optionally encode questions using HTML character entitites

"""



import random


class BaseMathCaptcha(object):
    def __init__(self, qty=2, min=10, max=30, str_ops=False):
        self._str_ops = str_ops
        self._answer = None
        self._question = None
        self.numbers = []
        for i in xrange(qty):
            num = random.randint(min, max)
            self.numbers.append(num)


    def check(self, answer):
        if self._answer is None:
            self._calculate_answer()
        if int(answer) == self._answer:
            return True
        else:
            return False


    def _calculate_answer(self):
        op = self._operation()
        self._answer = reduce(op, self.numbers)


    def question(self):
        if self._question is None:
            str_numbers = []
            for number in self.numbers:
                str_numbers.append(str(number))
            op_string = self._op_string()
            self._question = op_string.join(str_numbers)
        return self._question


class AdditionCaptcha(BaseMathCaptcha):
    'Captcha for addition problems.'

    def _operation(self):
        return lambda a, b: a + b

    def _op_string(self):
        if self._str_ops is True:
            return " plus "
        else:
            return " + "


class SubtractionCaptcha(BaseMathCaptcha):
    'Captcha for subtraction problems.'

    def _operation(self):
        return lambda a, b: a - b

    def _op_string(self):
        if self._str_ops is True:
            return " minus "
        else:
            return " - "


class MultiplicationCaptcha(BaseMathCaptcha):
    'Captcha for multiplication problems.'

    def _operation(self):
        return lambda a, b: a * b

    def _op_string(self):
        if self._str_ops is True:
            return " times "
        else:
            return " * "



class MissingNumberCaptcha(object):
    def __init__(self, min=1, max=4):
        if min == max:
            self._question = ""
            self.missing = min
        else:
            self.missing = random.randint(min, max)
            numbers = range(min-1, max+2)
            if len(numbers) > 0:
                numbers.remove(self.missing)
                numbers = map(lambda x : str(x), numbers)
                self._question = " ".join(numbers)
            else:
                self._question = ""

    def check(self, answer):
        if int(answer) == self.missing:
            return True
        else:
            return False

    def question(self):
        return self._question

    def __str__(self):
        return self.question()

########NEW FILE########
__FILENAME__ = tests
# tests for captcha.py

import unittest, sys
from captcha import *


class TestCaptcha(unittest.TestCase):

    def test_AdditionCaptcha(self):
        c = AdditionCaptcha(qty=5, min=5, max=5)
        self.assertEqual(c.check(25), True)
        self.assertEqual(c.check(24), False)
        self.assertEqual(c.check(26), False)
        qst = "5 + 5 + 5 + 5 + 5"
        self.assertEqual(c.question(), qst)

        c = AdditionCaptcha(qty=20, min=10, max=1000)
        answer = reduce(lambda a,b : a + b, c.numbers)
        self.assertEqual(c.check(answer), True)

        c = AdditionCaptcha(qty=2, min=10, max=10, str_ops=True)
        self.assertEqual(c.check(20), True)
        self.assertEqual(c.question(), "10 plus 10")


    def test_SubtractionCaptcha(self):
        c = SubtractionCaptcha(qty=2, min=5, max=5)
        self.assertEqual(c.check(0), True)
        self.assertEqual(c.question(), "5 - 5")

        c = SubtractionCaptcha(qty=10, min=10, max=1000)
        answer = reduce(lambda a,b: a - b, c.numbers)
        self.assertEqual(c.check(answer), True)

        c = SubtractionCaptcha(qty=2, min=10, max=10, str_ops=True)
        self.assertEqual(c.check(0), True)
        self.assertEqual(c.question(), "10 minus 10")


    def test_MultiplicationCaptcha(self):
        c = MultiplicationCaptcha(qty=3, min=10, max=10)
        self.assertEqual(c.check(1000), True)
        self.assertEqual(c.question(), "10 * 10 * 10")
        
        c = MultiplicationCaptcha(qty=10, min=10, max=1000)
        answer = reduce(lambda a,b : a * b , c.numbers)
        self.assertEqual(c.check(answer), True)

        c = MultiplicationCaptcha(qty=2, min=10, max=10, str_ops=True)
        self.assertEqual(c.check(100), True)
        self.assertEqual(c.question(), "10 times 10")


    def test_MissingNumberCaptcha(self):
        c = MissingNumberCaptcha(min=5,max=5)
        self.assertEqual(c.check(5), True)
        



def main(argv=None):
    if argv is None: argv = sys.argv
    unittest.main(argv=["tests.py"])


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = context
from lifeflow.models import Entry, Flow, RecommendedSite, Author, Flow, Language
from django.contrib.sites.models import Site
from django.conf import settings


def blog(request):
    def make_slug(str):
        return str.lower().replace(" ","-")
    recent = Entry.current.all()[:5]
    random = Entry.current.all().order_by('?')[:5]
    blog_roll = RecommendedSite.objects.all()
    flows = Flow.objects.all()
    site = Site.objects.get(pk=settings.SITE_ID)
    analytics_id = getattr(settings, 'LIFEFLOW_GOOGLE_ANALYTICS_ID', None)
    use_projects = getattr(settings, 'LIFEFLOW_USE_PROJECTS', True)
    keywords = getattr(settings, 'LIFEFLOW_KEYWORDS', "blog")
    description = getattr(settings, 'LIFEFLOW_DESCRIPTION', "blog")
    author = getattr(settings, 'LIFEFLOW_AUTHOR_NAME', None)
    template_author = getattr(settings, 'LIFEFLOW_TEMPLATE_AUTHOR', "Will Larson")
    template_author_url = getattr(settings, 'LIFEFLOW_TEMPLATE_AUTHOR_URL', "http://www.lethain.com/")
    if author is None:
        try:
            author = Author.objects.get(pk=1).name
        except:
            author = "Anonymous"

    author_slug = make_slug(author)
    blog_name = getattr(settings, 'LIFEFLOW_BLOG_NAME', "Unconfigured LifeFlow")
    custom_css = getattr(settings, 'LIFEFLOW_CUSTOM_CSS', None)
    custom_js_header = getattr(settings, 'LIFEFLOW_CUSTOM_JS_HEADER', None)
    custom_js_footer = getattr(settings, 'LIFEFLOW_CUSTOM_JS_FOOTER', None)
    return {
        'blog_roll' : blog_roll,
        'lifeflow_google_analytics_id':analytics_id,
        'lifeflow_blog_name':blog_name,
        'lifeflow_custom_css':custom_css,
        'lifeflow_custom_js_header':custom_js_header,
        'lifeflow_custom_js_footer':custom_js_footer,
        'lifeflow_flows':flows,
        'lifeflow_keywords':keywords,
        'lifeflow_description':description,
        'lifeflow_author':author,
        'lifeflow_author_slug':author_slug,
        'lifeflow_use_projects':use_projects,
        'lifeflow_template_author':template_author,
        'lifeflow_template_author_url':template_author_url,
        'recent_entries' : recent, 
        'random_entries' : random,
        'site' : site,
        }

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from lifeflow.models import *

urlpatterns = patterns('lifeflow.editor.views',
    (r'^$', 'overview'),
    (r'^comments/$', 'comments'),
    (r'^files/$', 'files'),

    (r'^admin/blogroll/$', 'blogroll'),
    (r'^admin/sites_to_ping/$', 'sites_to_notify'),
    (r'^admin/site_config/$', 'site_config'),
    

    (r'^authors/$', 'authors'),
    (r'^authors/create/$', 'create_author'),
    (r'^authors/(?P<id>\d+)/$', 'author_edit'),
    (r'^authors/(?P<id>\d+)/create/$', 'create_author'),

    (r'^projects/$', 'projects'),
    (r'^projects/create/$', 'create_project'),
    (r'^projects/(?P<id>\d+)/details/$','project_details'),
    (r'^projects/(?P<id>\d+)/body/$','project_body'),

    (r'^login/$', 'login'),
    (r'^logout/$', 'logout'),

    (r'^create/$', 'create'),
    (r'^update/$', 'update'),
    (r'^display_resource/(?P<id>\d+)/$', 'display_resource'),
    (r'^add_resource/', 'add_resource'),
    (r'^display_author/(?P<id>\d+)/$', 'display_author'),
    (r'^add_author_picture/', 'add_author_picture'),
    (r'^create_model/', 'create_model'),
    (r'^delete_model/', 'delete_model'),

    (r'^edit/(?P<category>\w+)/(?P<id>\d+)/title/$', 'article_title'),
    (r'^edit/(?P<category>\w+)/(?P<id>\d+)/body/$', 'article_body'),
    (r'^edit/(?P<category>\w+)/(?P<id>\d+)/flows/$', 'article_flows'),
    (r'^edit/(?P<category>\w+)/(?P<id>\d+)/tags/$', 'article_tags'),
    (r'^edit/(?P<category>\w+)/(?P<id>\d+)/series/$', 'article_series'),
    (r'^edit/(?P<category>\w+)/(?P<id>\d+)/options/$', 'article_options'),
    (r'^edit/(?P<category>\w+)/(?P<id>\d+)/authors/$', 'article_authors'),
    (r'^rough_to_edited/(?P<id>\d+)/$', 'rough_to_edited'),
    (r'^edited_to_rough/(?P<id>\d+)/$', 'edited_to_rough'),
    (r'^edited_to_published/(?P<id>\d+)/$', 'edited_to_published'),
    (r'^published_to_edited/(?P<id>\d+)/$', 'published_to_edited'),
    (r'^render/(?P<model>\w+)/(?P<id>\d+)/$', 'render'),
    (r'^render/$', 'render'),
)

########NEW FILE########
__FILENAME__ = views
"""


TODO

- write function to check a Draft for missing requirements before
  transformation into an Entry, and report that data when the
  transformation fails, instead of just "It failed" msg
- File upload functionality
- Setting datetime
- display list of files in zipfile resources
- display code for code resources


"""


import datetime, os.path, time, re
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.http import Http404, HttpResponseRedirect, HttpResponseServerError
from lifeflow.models import *
from lifeflow.text_filters import entry_markup
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import login as auth_login
from django.contrib.auth import views, authenticate
from django.core.paginator import QuerySetPaginator
from django.contrib.sites.models import Site

from pygments import highlight
from pygments.util import ClassNotFound
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_for_filename

from zipfile import ZipFile

CHARACTERS_TO_STRIP = re.compile(r"[ \.,\!\?'\";:/\\+=#]+")
def sluggify(str):
    return CHARACTERS_TO_STRIP.subn(u"-", str.lower())[0].strip("-")


def login(request):
    error_msg = u""
    if request.method == "POST":
        POST = request.POST.copy()
        username = POST.get('username',"")
        password = POST.get('password',"")

        if username == "" or password == "":
            error_msg = u"Your username AND password, si vous plait."
        else:
            user = authenticate(username=username, password=password)
            if user is not None:
                if user.is_active:
                    auth_login(request, user)
                    return HttpResponseRedirect("/editor/")
            else:
                error_msg = u"It works better when the username and password match."
    return render_to_response("lifeflow/editor/login.html",
                              
                              {"login_screen":True,
                               'error_message':error_msg})

def logout(request):
    auth_logout(request)
    return HttpResponseRedirect("/")

@login_required
def overview(request):
    rough = Draft.objects.filter(edited=False)
    edited = Draft.objects.filter(edited=True)
    published = Entry.objects.all()
    return render_to_response('lifeflow/editor/overview.html',
                              {'rough':rough,
                               'edited':edited,
                               'published':published},
                              RequestContext(request, {}))

@login_required
def comments(request):
    try:
        page = int(request.GET["page"])
    except:
        page = 1
    page = QuerySetPaginator(Comment.objects.all(), 5).page(page)
    return render_to_response('lifeflow/editor/comments.html',
                              {'page':page},
                              RequestContext(request,{}))

@login_required
def blogroll(request):
    blogroll = RecommendedSite.objects.all()
    return render_to_response('lifeflow/editor/blogroll.html',
                              {'blogroll':blogroll},
                              RequestContext(request,{}))

@login_required
def sites_to_notify(request):
    sites = SiteToNotify.objects.all()
    return render_to_response('lifeflow/editor/sites_to_ping.html',
                              {'sites_to_notify':sites},
                              RequestContext(request,{}))

@login_required
def site_config(request):
    site = Site.objects.get_current()
    return render_to_response('lifeflow/editor/site.html',
                              {'sites_to_notify':site},
                              RequestContext(request,{}))

@login_required
def files(request):
    resources = Resource.objects.all()
    return render_to_response('lifeflow/editor/files.html',
                              {'resources':resources},
                              RequestContext(request,{}))

@login_required
def projects(request):
    projects = Project.objects.all()
    return render_to_response('lifeflow/editor/projects.html',
                              {'projects':projects},
                              RequestContext(request,{}))

@login_required
def project_details(request, id):
    project = Project.objects.get(pk=id)
    return render_to_response('lifeflow/editor/project_details.html',
                              {'object':project},
                              RequestContext(request,{}))

@login_required
def project_body(request, id):
    project = Project.objects.get(pk=id)
    resources = Resource.objects.all()
    return render_to_response('lifeflow/editor/project_body.html',
                              {'object':project,
                               'resources':resources},
                              RequestContext(request,{}))

@login_required
def authors(request):
    authors = Author.objects.all()
    selected = len(authors)-1
    author = authors[selected]
    return render_to_response('lifeflow/editor/authors.html',
                              {'author':author,
                               'authors':authors,
                               'selected':selected},
                              RequestContext(request,{}))

@login_required
def author_edit(request,id):
    author = Author.objects.get(pk=id)
    return render_to_response('lifeflow/editor/author.html',
                              {'author':author},
                              RequestContext(request,{}))

    
    


BOOLEAN_FIELDS = ["send_ping", "allow_comments", "use_markdown"]
MANY_TO_MANY_FIELDS = ["flows", "tags", "series", "authors"]
SLUG_FIELDS = ["slug"]
DATETIME_FIELDS = ["pub_date"]

@login_required
def update(request):
    dict = request.POST.copy()
    id = dict.pop('pk')[0]
    model = dict.pop('model')[0]
    object = get_class(model).objects.get(pk=id)
    obj_dict = object.__dict__
    for key in dict.keys():
        if obj_dict.has_key(key):
            val = dict[key]
            if key in BOOLEAN_FIELDS:
                if val == u"true":
                    val = True
                elif val == u"false":
                    val = False
            elif key in SLUG_FIELDS:
                val = sluggify(val)
            elif key in DATETIME_FIELDS:
                t = time.mktime(time.strptime(val, "%Y-%m-%d %H:%M:%S"))
                val = datetime.datetime.fromtimestamp(t)
            obj_dict[key] = val
        elif key in MANY_TO_MANY_FIELDS:
            vals = dict.getlist(key)
            manager = getattr(object, key)
            manager.clear()
            if not (len(vals) == 1 and int(vals[0]) == -1):
                manager.add(*vals)
    object.save()
    return HttpResponse("success")


API_CLASSES = {"comment":Comment, "project":Project, "flow":Flow, "tag":Tag, "series":Series, "draft":Draft, "entry":Entry, "author":Author, "resource":Resource, "recommendedsite":RecommendedSite,'site_to_notify':SiteToNotify,'site':Site,"language":Language}

def get_class(str):
    return API_CLASSES[str]

@login_required
def delete_model(request):
    cls = get_class(request.POST['model'])
    pk = request.POST['pk']
    try:
        cls.objects.get(pk=pk).delete()
        return HttpResponse("success")
    except:
        return HttpResponseServerError(u"fail")
        

@login_required
def create_model(request):
    def unique(slug, model):
        if model.objects.filter(slug=slug).count() == 0:
            return True
        return False
    toReturn = HttpResponseRedirect(request.META['HTTP_REFERER'])
    model = request.POST['model']
    if model in [u"flow", u"tag", u"series"]:
        cls = get_class(model)
        title = request.POST[u'title']
        slug = sluggify(title)
        if unique(slug, cls):
            f = cls(title=title, slug=slug)
            f.save()
    elif model == u"language":
        title = request.POST[u'title']
        slug = sluggify(title)
        l = Language(title=title,slug=slug)
        l.save()
    elif model == u"site_to_notify":
        title = request.POST[u'title']
        url_to_ping = request.POST[u'url_to_ping']
        blog_title = request.POST[u'blog_title']
        blog_url = request.POST[u'blog_url']
        s = SiteToNotify(title=title,url_to_ping=url_to_ping,blog_title=blog_title,blog_url=blog_url)
        s.save()
    elif model == u"translation":
        translated_pk = int(request.POST[u'pk'])
        translated = Entry.objects.get(pk=translated_pk)
        original_pk = int(request.POST[u'original'])
        language_pk = int(request.POST[u'language'])
        if original_pk == -1 or language_pk == -1:
            [ x.delete() for x in Translation.objects.filter(original=translated)]
            [ x.delete() for x in Translation.objects.filter(translated=translated)]
        else:
            original = Entry.objects.get(pk=original_pk)
            language = Language.objects.get(pk=language_pk)
            
            t = Translation(language=language,original=original,translated=translated)
            t.save()
        # update toReturn to return rendered template of translations
        translations = Translation.objects.filter(translated=translated)
        toReturn = render_to_response('lifeflow/editor/translations.html',
                                      {'translations':translations},
                                      RequestContext(request, {}))

    elif model == u"recommendedsite":
        title = request.POST[u'title']
        url = request.POST[u'url']
        f = RecommendedSite(title=title, url=url)
        f.save()

    return toReturn

@login_required
def add_author_picture(request):
    id = request.POST['pk']
    file = request.FILES['file']
    filename = file.name
    filebase = '%s/lifeflow/author/' % settings.MEDIA_ROOT
    filepath = "%s%s" % (filebase, filename)
    while (os.path.isfile(filepath)):
        filename = "_%s" % filename
        filepath = "%s%s" % (filebase, filename)
    fd = open(filepath, 'wb')
    fd.write(file.read())
    fd.close()
    
    author = Author.objects.get(pk=id)
    author.picture = "lifeflow/author/%s" % filename
    author.save()

    return HttpResponseRedirect(request.META['HTTP_REFERER'])

@login_required
def display_author(request, id):
    pass

@login_required
def add_resource(request):
    file = request.FILES['file']
    title = request.POST['title']
    markdown_id = request.POST['markdown_id']
    filename = file.name
    filebase = '%s/lifeflow/resource/' % settings.MEDIA_ROOT
    filepath = "%s%s" % (filebase, filename)
    while (os.path.isfile(filepath)):
        filename = "_%s" % filename
        filepath = "%s%s" % (filebase, filename)
    fd = open(filepath, 'wb')

    fd.write(file.read())
    fd.close()
    rec = Resource(title=title, markdown_id=markdown_id, content="lifeflow/resource/%s" % filename)
    rec.save()
    id = request.POST['pk']
    model = request.POST['model']
    return HttpResponseRedirect(request.META['HTTP_REFERER'])
    #return HttpResponseRedirect("/editor/edit/%s/%s/2/" % (model, id))


IMAGE_EXTS = ["jpg", "jpeg", "png", "gif"]
ZIP_EXTS = ["zip"]
CODE_EXTS = ["css", "html", "htm", "c", "o", "py", "lisp", "js", "xml",
             "java", "rb"]

@login_required
def display_resource(request, id):
    res = Resource.objects.get(pk=id)
    file = res.content.path.split("/")[-1]
    opts = {'object':res,'file':file}
    ext = opts['file'].split(".")[-1]
    opts['type'] = 'file'
    if ext in IMAGE_EXTS:
        opts['type'] = "image"
    elif ext in ZIP_EXTS:
        try:
            opts['type'] = "zip"
            zf = ZipFile(res.content.path,'r')
            opts['files_list'] = zf.namelist()
            zf.close()
        except IOError:
            opts['type'] = "file"
    else:
        try:
            lexer = get_lexer_for_filename(file)
            f = open(res.content.path,'r')
            data = f.read()
            f.close()
            opts['highlighted_code'] = highlight(data,lexer,HtmlFormatter())
            opts['type'] = "code"
        except ClassNotFound:
            opts['type'] = "file"
        except IOError:
            opts['type'] = "file"

    return render_to_response('lifeflow/editor/resource.html',opts,RequestContext(request, {}))


@login_required
def article_title(request, category, id):
    if category == "entry":
        obj = Entry.objects.get(pk=id)
    else:
        obj = Draft.objects.get(pk=id)
    return render_to_response('lifeflow/editor/article_title.html',
                              {'object':obj,
                               'model':category},
                              RequestContext(request, {}))

@login_required
def article_body(request, category, id):
    resources = Resource.objects.all()
    if category == "entry":
        obj = Entry.objects.get(pk=id)
    else:
        obj = Draft.objects.get(pk=id)
    return render_to_response('lifeflow/editor/article_body.html',
                              {'object':obj,
                               'resources':resources,
                               'model':category},
                              RequestContext(request, {}))

@login_required
def article_flows(request, category, id):
    if category == "entry":
        obj = Entry.objects.get(pk=id)
    else:
        obj = Draft.objects.get(pk=id)
    obj_flows = obj.flows.all()
    flows = [ (x, x in obj_flows) for x in Flow.objects.all()] 
    return render_to_response('lifeflow/editor/article_flows.html',
                              {'object':obj,
                               'flows':flows,
                               'model':category},
                              RequestContext(request, {}))

@login_required
def article_tags(request, category, id):
    if category == "entry":
        obj = Entry.objects.get(pk=id)
    else:
        obj = Draft.objects.get(pk=id)
    obj_tags = obj.tags.all()
    tags = [ (x, x in obj_tags) for x in Tag.objects.all()]
    return render_to_response('lifeflow/editor/article_tags.html',
                              {'object':obj,
                               'tags':tags,
                               'model':category},
                              RequestContext(request, {}))

@login_required
def article_series(request, category, id):
    if category == "entry":
        obj = Entry.objects.get(pk=id)
    else:
        obj = Draft.objects.get(pk=id)
    obj_series = obj.series.all()
    series = [ (x, x in obj_series) for x in Series.objects.all()]
    return render_to_response('lifeflow/editor/article_series.html',
                              {'object':obj,
                               'series':series,
                               'model':category},
                              RequestContext(request, {}))


@login_required
def article_options(request, category, id):
    if category == "entry":
        obj = Entry.objects.get(pk=id)
    else:
        obj = Draft.objects.get(pk=id)
    return render_to_response('lifeflow/editor/article_options.html',
                              {'object':obj,
                               'model':category},
                              RequestContext(request, {}))


@login_required
def article_authors(request, category, id):
    if category == "entry":
        obj = Entry.objects.get(pk=id)
    else:
        obj = Draft.objects.get(pk=id)
    obj_authors = obj.authors.all()
    authors = [ (x, x in obj_authors) for x in Author.objects.all()]
    langs = Language.objects.all()
    entries = Entry.objects.all()
    translations = Translation.objects.filter(translated=obj)
    return render_to_response('lifeflow/editor/article_authors.html',
                              {'object':obj,
                               'authors':authors,
                               'langs':langs,
                               'entries':entries,
                               'translations':translations,
                               'model':category},
                              RequestContext(request, {}))



@login_required
def rough_to_edited(request, id):
    try:
        obj = Draft.objects.get(pk=id)
        obj.edited = True
        obj.save()
        return HttpResponse(u"%s" % obj.pk)
    except:
        return HttpResponseServerError(u"Failed.")

@login_required
def edited_to_rough(request, id):
    try:
        obj = Draft.objects.get(pk=id)
        obj.edited = False
        obj.save()
        return HttpResponse(u"%s" % obj.pk)
    except:
        return HttpResponseServerError(u"Failed.")

@login_required
def edited_to_published(request, id):
    def check(dict):
        complaints = []
        if dict[u"title"] in [None, u""]:
            complaints.append("You need to give the entry a title first.")
        if dict[u"body"] in [None, u""]:
            complaints.append("You'll need to fill out the article a bit before publishing it.")          
        if complaints == []:
            return True
        else:
            return "\n<br>\n".join(complaints)

    def transform(draft):
        dict = draft.__dict__.copy()
        del dict['id']
        if dict['pub_date'] is None:
            dict['pub_date'] = datetime.datetime.now()
        del dict['edited']
        if dict['slug'] is None and dict['title'] is not None:
            dict['slug'] = sluggify(dict['title'])
        entry = Entry(**dict)
        valid = check(entry.__dict__)
        if valid != True:
            return None, valid
        else:
            entry.save()
            for field in MANY_TO_MANY_FIELDS:
                getattr(entry, field).add(*getattr(draft, field).all())
            return entry, True

    try:
        draft = Draft.objects.get(pk=id)
        entry, result = transform(draft)
        if result == True:
            draft.delete()
            return HttpResponse(u"%s" % entry.pk)
        else:
            return HttpResponseServerError(result)
    except TypeError:
        return HttpResponseServerError(u"The draft is missing required fields.")
    except:
        return HttpResponseServerError(u"The update made it to the server, but failed for unknown reasons.")

@login_required
def published_to_edited(request, id):
    def transform(entry):
        dict = entry.__dict__.copy()
        dict['edited'] = True
        del dict['body_html']
        del dict['id']
        draft = Draft(**dict)
        draft.save()
        for field in MANY_TO_MANY_FIELDS:
                getattr(draft, field).add(*getattr(entry, field).all())
        return draft
    try:
        entry = Entry.objects.get(pk=id)
        draft = transform(entry)
        entry.delete()
        return HttpResponse(u"%s" % draft.pk)
    except:
        return HttpResponseServerError(u"Update failed.")


@login_required
def create(request):
    obj = Draft()
    obj.save()
    return HttpResponseRedirect("../edit/draft/%s/title/" % obj.pk)

@login_required
def create_project(request):
    obj = Project()
    obj.save()
    return HttpResponseRedirect("/editor/projects/%s/details/" % obj.pk)

@login_required
def create_author(request,id=None):
    obj = Author()
    obj.save()
    return HttpResponseRedirect("/editor/authors/")
    

@login_required
def render(request, model=None, id=None):
    if id is None and request.POST.has_key('pk'):
        id = request.POST['pk']

    if id is None:
        txt = entry_markup(request.POST['txt'])
    else:
        if model == u"draft":
            obj = Draft.objects.get(pk=id)
        elif model ==u"entry":
            obj = Entry.objects.get(pk=id)
        elif model == u"project":
            obj = Project.objects.get(pk=id)
        if obj.use_markdown:
            txt = entry_markup(obj.body, obj)
        else:
            txt = obj.body
    return HttpResponse(txt)

########NEW FILE########
__FILENAME__ = feeds
from django.contrib.syndication.feeds import Feed
from django.conf import settings
from lifeflow.models import *


 
class AllFeed(Feed):
    title = u"%s" % settings.LIFEFLOW_BLOG_NAME 
    link = u"/"
    description = u"The full feed of all entries! Piping hot and ready for consumption."
    copyright = u'Creative Commons License'


    def items(self):
        return Entry.current.all().order_by('-pub_date')[:25]
    
    def item_pubdate(self, item):
        return item.pub_date



class FlowFeed(Feed):
    def get_object(self, bits):
        slug = bits[0]
        return Flow.objects.get(slug=slug)


    def title(self, obj):
        return u"%s: %s" % (settings.LIFEFLOW_BLOG_NAME,
                                              obj.title)


    def link(self, obj):
        return obj.get_absolute_url()


    def description(self, obj):
        return u"The piping hot feed for all entries in the %s flow." % obj.title


    def items(self, obj):
        return obj.latest(qty=25)
    
    def item_pubdate(self, item):
        return item.pub_date



class TagFeed(Feed):
    def get_object(self, bits):
        slug = bits[0]
        return Tag.objects.get(slug=slug)

    
    def title(self, obj):
        return u"%s: the %s tag" % (settings.LIFEFLOW_BLOG_NAME,
                                              obj.title)


    def link(self, obj):
        return obj.get_absolute_url()


    def description(self, obj):
        return u"All entries tagged with %s." % obj.title

    
    def items(self, obj):
        return obj.latest()


    def item_pubdate(self, item):
        return item.pub_date


class AuthorFeed(Feed):
    def get_object(self, bits):
        slug = bits[0]
        return Author.objects.get(slug=slug)


    def title(self, obj):
        return u"%s: %s" % (settings.LIFEFLOW_BLOG_NAME,
                                              obj.name)
    
    def title(self, obj):
        return u"Feed for stuff by %s." % obj.name


    def link(self, obj):
        return obj.get_absolute_url()


    def description(self, obj):
        return u"Recent entries written by %s." % obj.name

    
    def items(self, obj):
        return obj.latest()


    def item_pubdate(self, item):
        return item.pub_date


class LanguageFeed(Feed):
    def get_object(self, bits):
        slug = bits[0]
        return Language.objects.get(slug=slug)


    def title(self, obj):
        return u"%s: %s" % (settings.LIFEFLOW_BLOG_NAME,
                                              obj.title)
    
    def title(self, obj):
        return u"Feed for stuff translated into %s." % obj.title


    def link(self, obj):
        return obj.get_absolute_url()


    def description(self, obj):
        return u"Recent entries translated into %s." % obj.title

    
    def items(self, obj):
        return obj.latest()
    
    
    def item_pubdate(self, item):
        return item.pub_date



class SeriesFeed(Feed):
    def get_object(self, bits):
        slug = bits[0]
        return Series.objects.get(slug=slug)

    
    def title(self, obj):
        return u"%s: %s" % (settings.LIFEFLOW_BLOG_NAME,
                                              obj.title)


    def link(self, obj):
        return obj.get_absolute_url()


    def description(self, obj):
        return u"Entries in the %s series." % obj.title

    
    def items(self, obj):
        return obj.latest()
        
        
    def item_pubdate(self, item):
        return item.pub_date



class TranslationFeed(Feed):
    title = u"%s: Translations" % settings.LIFEFLOW_BLOG_NAME
    link = u"/"
    description = u"Recent translationed entries."
    copyright = u'Creative Commons License'


    def items(self):
        return Entry.objects.all().filter(**{'pub_date__lte': datetime.datetime.now()}).filter(**{'is_translation':True})
    
    
    def item_pubdate(self, item):
        return item.pub_date



class ProjectFeed(Feed):
    title = u"%s: Projects" % settings.LIFEFLOW_BLOG_NAME
    link = u"/"
    description = u"Latest projects on %s." % settings.LIFEFLOW_BLOG_NAME
    copyright = u'Creative Commons License'


    def items(self):
        return Project.objects.all().order_by('-id')



class CommentFeed(Feed):
    title = u"%s: Comments" % settings.LIFEFLOW_BLOG_NAME
    link = "/"
    description = u"Latest comments on %s." % settings.LIFEFLOW_BLOG_NAME
    copyright = u'Creative Commons License'
    

    def items(self):
        return Comment.objects.all().order_by('-date',)[:20]
        
    
    def item_pubdate(self, item):
        return item.date



class EntryCommentFeed(Feed):
    def get_object(self, bits):
        year = bits[0]
        month = bits[1]
        day = bits[2]
        slug = bits[3]
        return Entry.objects.get(pub_date__year=year,
                                 pub_date__month=month,
                                 pub_date__day=day,
                                 slug=slug)

    
    def title(self, obj):
        return u"%s: Comments for %s" % (settings.LIFEFLOW_BLOG_NAME,
                                              obj.title)


    def link(self, obj):
        return obj.get_absolute_url()


    def description(self, obj):
        return u"Comments for %s." % obj.title

    
    def items(self, obj):
        return obj.comment_set.all().order_by('-date')
        
    
    def item_pubdate(self, item):
        return item.date
    

########NEW FILE########
__FILENAME__ = forms
import cgi
from django import  forms
from lifeflow.text_filters import comment_markup


class CommentForm(forms.Form):
    name = forms.CharField(required=False)
    email = forms.CharField(required=False)
    webpage = forms.CharField(required=False)
    body = forms.CharField(widget=forms.Textarea, required=False)


    def clean_name(self):
        name = self.cleaned_data['name']
        if name == u"":
            name = u"name"
        else:
            name = cgi.escape(name)
        return name
        

    def clean_email(self):
        email = self.cleaned_data['email']
        if email == u"":
            email = u"email"
        else:
            email = cgi.escape(email)
        return email


    def clean_webpage(self):
        webpage = self.cleaned_data['webpage']
        if webpage == u"":
            webpage = u"webpage"
        else:
            webpage = cgi.escape(webpage)
        if webpage.find('://') == -1: webpage = "http://%s" % webpage
        return webpage
        

    def clean_body(self):
        body = self.cleaned_data['body']
        self.cleaned_data['html'] = unicode(comment_markup(body))
        return body
        

########NEW FILE########
__FILENAME__ = markdown
#!/usr/bin/env python

version = "1.7"
version_info = (1,7,0,"rc-1")
__revision__ = "$Rev: 66 $"

"""
Python-Markdown
===============

Converts Markdown to HTML.  Basic usage as a module:

    import markdown
    md = Markdown()
    html = md.convert(your_text_string)

See http://www.freewisdom.org/projects/python-markdown/ for more
information and instructions on how to extend the functionality of the
script.  (You might want to read that before you try modifying this
file.)

Started by [Manfred Stienstra](http://www.dwerg.net/).  Continued and
maintained  by [Yuri Takhteyev](http://www.freewisdom.org) and [Waylan
Limberg](http://achinghead.com/).

Contact: yuri [at] freewisdom.org
         waylan [at] gmail.com

License: GPL 2 (http://www.gnu.org/copyleft/gpl.html) or BSD

"""


import re, sys, os, random, codecs

from logging import getLogger, StreamHandler, Formatter, \
                    DEBUG, INFO, WARN, ERROR, CRITICAL


MESSAGE_THRESHOLD = CRITICAL


# Configure debug message logger (the hard way - to support python 2.3)
logger = getLogger('MARKDOWN')
logger.setLevel(DEBUG) # This is restricted by handlers later
console_hndlr = StreamHandler()
formatter = Formatter('%(name)s-%(levelname)s: "%(message)s"')
console_hndlr.setFormatter(formatter)
console_hndlr.setLevel(MESSAGE_THRESHOLD)
logger.addHandler(console_hndlr)


def message(level, text):
    ''' A wrapper method for logging debug messages. '''
    logger.log(level, text)


# --------------- CONSTANTS YOU MIGHT WANT TO MODIFY -----------------

TAB_LENGTH = 4            # expand tabs to this many spaces
ENABLE_ATTRIBUTES = True  # @id = xyz -> <... id="xyz">
SMART_EMPHASIS = 1        # this_or_that does not become this<i>or</i>that
HTML_REMOVED_TEXT = "[HTML_REMOVED]" # text used instead of HTML in safe mode

RTL_BIDI_RANGES = ( (u'\u0590', u'\u07FF'),
                    # from Hebrew to Nko (includes Arabic, Syriac and Thaana)
                    (u'\u2D30', u'\u2D7F'),
                    # Tifinagh
                    )

# Unicode Reference Table:
# 0590-05FF - Hebrew
# 0600-06FF - Arabic
# 0700-074F - Syriac
# 0750-077F - Arabic Supplement
# 0780-07BF - Thaana
# 07C0-07FF - Nko

BOMS = { 'utf-8': (codecs.BOM_UTF8, ),
         'utf-16': (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE),
         #'utf-32': (codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)
         }

def removeBOM(text, encoding):
    convert = isinstance(text, unicode)
    for bom in BOMS[encoding]:
        bom = convert and bom.decode(encoding) or bom
        if text.startswith(bom):
            return text.lstrip(bom)
    return text

# The following constant specifies the name used in the usage
# statement displayed for python versions lower than 2.3.  (With
# python2.3 and higher the usage statement is generated by optparse
# and uses the actual name of the executable called.)

EXECUTABLE_NAME_FOR_USAGE = "python markdown.py"
                    

# --------------- CONSTANTS YOU _SHOULD NOT_ HAVE TO CHANGE ----------

# a template for html placeholders
HTML_PLACEHOLDER_PREFIX = "qaodmasdkwaspemas"
HTML_PLACEHOLDER = HTML_PLACEHOLDER_PREFIX + "%dajkqlsmdqpakldnzsdfls"

BLOCK_LEVEL_ELEMENTS = ['p', 'div', 'blockquote', 'pre', 'table',
                        'dl', 'ol', 'ul', 'script', 'noscript',
                        'form', 'fieldset', 'iframe', 'math', 'ins',
                        'del', 'hr', 'hr/', 'style']

def is_block_level (tag):
    return ( (tag in BLOCK_LEVEL_ELEMENTS) or
             (tag[0] == 'h' and tag[1] in "0123456789") )

"""
======================================================================
========================== NANODOM ===================================
======================================================================

The three classes below implement some of the most basic DOM
methods.  I use this instead of minidom because I need a simpler
functionality and do not want to require additional libraries.

Importantly, NanoDom does not do normalization, which is what we
want. It also adds extra white space when converting DOM to string
"""

ENTITY_NORMALIZATION_EXPRESSIONS = [ (re.compile("&"), "&amp;"),
                                     (re.compile("<"), "&lt;"),
                                     (re.compile(">"), "&gt;"),
                                     (re.compile("\""), "&quot;")]

ENTITY_NORMALIZATION_EXPRESSIONS_SOFT = [ (re.compile("&(?!\#)"), "&amp;"),
                                     (re.compile("<"), "&lt;"),
                                     (re.compile(">"), "&gt;"),
                                     (re.compile("\""), "&quot;")]


def getBidiType(text):

    if not text: return None

    ch = text[0]

    if not isinstance(ch, unicode) or not ch.isalpha():
        return None

    else:

        for min, max in RTL_BIDI_RANGES:
            if ( ch >= min and ch <= max ):
                return "rtl"
        else:
            return "ltr"


class Document:

    def __init__ (self):
        self.bidi = "ltr"

    def appendChild(self, child):
        self.documentElement = child
        child.isDocumentElement = True
        child.parent = self
        self.entities = {}

    def setBidi(self, bidi):
        if bidi:
            self.bidi = bidi

    def createElement(self, tag, textNode=None):
        el = Element(tag)
        el.doc = self
        if textNode:
            el.appendChild(self.createTextNode(textNode))
        return el

    def createTextNode(self, text):
        node = TextNode(text)
        node.doc = self
        return node

    def createEntityReference(self, entity):
        if entity not in self.entities:
            self.entities[entity] = EntityReference(entity)
        return self.entities[entity]

    def createCDATA(self, text):
        node = CDATA(text)
        node.doc = self
        return node

    def toxml (self):
        return self.documentElement.toxml()

    def normalizeEntities(self, text, avoidDoubleNormalizing=False):

        if avoidDoubleNormalizing:
            regexps = ENTITY_NORMALIZATION_EXPRESSIONS_SOFT
        else:
            regexps = ENTITY_NORMALIZATION_EXPRESSIONS

        for regexp, substitution in regexps:
            text = regexp.sub(substitution, text)
        return text

    def find(self, test):
        return self.documentElement.find(test)

    def unlink(self):
        self.documentElement.unlink()
        self.documentElement = None


class CDATA:

    type = "cdata"

    def __init__ (self, text):
        self.text = text

    def handleAttributes(self):
        pass

    def toxml (self):
        return "<![CDATA[" + self.text + "]]>"

class Element:

    type = "element"

    def __init__ (self, tag):

        self.nodeName = tag
        self.attributes = []
        self.attribute_values = {}
        self.childNodes = []
        self.bidi = None
        self.isDocumentElement = False

    def setBidi(self, bidi):

        if bidi:

            orig_bidi = self.bidi

            if not self.bidi or self.isDocumentElement:
                # Once the bidi is set don't change it (except for doc element)
                self.bidi = bidi
                self.parent.setBidi(bidi)


    def unlink(self):
        for child in self.childNodes:
            if child.type == "element":
                child.unlink()
        self.childNodes = None

    def setAttribute(self, attr, value):
        if not attr in self.attributes:
            self.attributes.append(attr)

        self.attribute_values[attr] = value

    def insertChild(self, position, child):
        self.childNodes.insert(position, child)
        child.parent = self

    def removeChild(self, child):
        self.childNodes.remove(child)

    def replaceChild(self, oldChild, newChild):
        position = self.childNodes.index(oldChild)
        self.removeChild(oldChild)
        self.insertChild(position, newChild)

    def appendChild(self, child):
        self.childNodes.append(child)
        child.parent = self

    def handleAttributes(self):
        pass

    def find(self, test, depth=0):
        """ Returns a list of descendants that pass the test function """
        matched_nodes = []
        for child in self.childNodes:
            if test(child):
                matched_nodes.append(child)
            if child.type == "element":
                matched_nodes += child.find(test, depth+1)
        return matched_nodes

    def toxml(self):
        if ENABLE_ATTRIBUTES:
            for child in self.childNodes:
                child.handleAttributes()

        buffer = ""
        if self.nodeName in ['h1', 'h2', 'h3', 'h4']:
            buffer += "\n"
        elif self.nodeName in ['li']:
            buffer += "\n "

        # Process children FIRST, then do the attributes

        childBuffer = ""

        if self.childNodes or self.nodeName in ['blockquote']:
            childBuffer += ">"
            for child in self.childNodes:
                childBuffer += child.toxml()
            if self.nodeName == 'p':
                childBuffer += "\n"
            elif self.nodeName == 'li':
                childBuffer += "\n "
            childBuffer += "</%s>" % self.nodeName
        else:
            childBuffer += "/>"


            
        buffer += "<" + self.nodeName

        if self.nodeName in ['p', 'li', 'ul', 'ol',
                             'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:

            if not self.attribute_values.has_key("dir"):
                if self.bidi:
                    bidi = self.bidi
                else:
                    bidi = self.doc.bidi
                    
                if bidi=="rtl":
                    self.setAttribute("dir", "rtl")
        
        for attr in self.attributes:
            value = self.attribute_values[attr]
            value = self.doc.normalizeEntities(value,
                                               avoidDoubleNormalizing=True)
            buffer += ' %s="%s"' % (attr, value)


        # Now let's actually append the children

        buffer += childBuffer

        if self.nodeName in ['p', 'br ', 'li', 'ul', 'ol',
                             'h1', 'h2', 'h3', 'h4'] :
            buffer += "\n"

        return buffer


class TextNode:

    type = "text"
    attrRegExp = re.compile(r'\{@([^\}]*)=([^\}]*)}') # {@id=123}

    def __init__ (self, text):
        self.value = text        

    def attributeCallback(self, match):

        self.parent.setAttribute(match.group(1), match.group(2))

    def handleAttributes(self):
        self.value = self.attrRegExp.sub(self.attributeCallback, self.value)

    def toxml(self):

        text = self.value

        self.parent.setBidi(getBidiType(text))
        
        if not text.startswith(HTML_PLACEHOLDER_PREFIX):
            if self.parent.nodeName == "p":
                text = text.replace("\n", "\n   ")
            elif (self.parent.nodeName == "li"
                  and self.parent.childNodes[0]==self):
                text = "\n     " + text.replace("\n", "\n     ")
        text = self.doc.normalizeEntities(text)
        return text


class EntityReference:

    type = "entity_ref"

    def __init__(self, entity):
        self.entity = entity

    def handleAttributes(self):
        pass

    def toxml(self):
        return "&" + self.entity + ";"


"""
======================================================================
========================== PRE-PROCESSORS ============================
======================================================================

Preprocessors munge source text before we start doing anything too
complicated.

Each preprocessor implements a "run" method that takes a pointer to a
list of lines of the document, modifies it as necessary and returns
either the same pointer or a pointer to a new list.  Preprocessors
must extend markdown.Preprocessor.

"""


class Preprocessor:
    pass


class HeaderPreprocessor (Preprocessor):

    """
       Replaces underlined headers with hashed headers to avoid
       the nead for lookahead later.
    """

    def run (self, lines):

        i = -1
        while i+1 < len(lines):
            i = i+1
            if not lines[i].strip():
                continue

            if lines[i].startswith("#"):
                lines.insert(i+1, "\n")

            if (i+1 <= len(lines)
                  and lines[i+1]
                  and lines[i+1][0] in ['-', '=']):

                underline = lines[i+1].strip()

                if underline == "="*len(underline):
                    lines[i] = "# " + lines[i].strip()
                    lines[i+1] = ""
                elif underline == "-"*len(underline):
                    lines[i] = "## " + lines[i].strip()
                    lines[i+1] = ""

        return lines

HEADER_PREPROCESSOR = HeaderPreprocessor()

class LinePreprocessor (Preprocessor):
    """Deals with HR lines (needs to be done before processing lists)"""

    blockquote_re = re.compile(r'^(> )+')

    def run (self, lines):
        for i in range(len(lines)):
            prefix = ''
            m = self.blockquote_re.search(lines[i])
            if m : prefix = m.group(0)
            if self._isLine(lines[i][len(prefix):]):
                lines[i] = prefix + self.stash.store("<hr />", safe=True)
        return lines

    def _isLine(self, block):
        """Determines if a block should be replaced with an <:wHR>"""
        if block.startswith("    "): return 0  # a code block
        text = "".join([x for x in block if not x.isspace()])
        if len(text) <= 2:
            return 0
        for pattern in ['isline1', 'isline2', 'isline3']:
            m = RE.regExp[pattern].match(text)
            if (m and m.group(1)):
                return 1
        else:
            return 0

LINE_PREPROCESSOR = LinePreprocessor()


class HtmlBlockPreprocessor (Preprocessor):
    """Removes html blocks from self.lines"""
    
    def _get_left_tag(self, block):
        return block[1:].replace(">", " ", 1).split()[0].lower()


    def _get_right_tag(self, left_tag, block):
        return block.rstrip()[-len(left_tag)-2:-1].lower()

    def _equal_tags(self, left_tag, right_tag):
        
        if left_tag in ['?', '?php', 'div']: # handle PHP, etc.
            return True
        if ("/" + left_tag) == right_tag:
            return True
        if (right_tag == "--" and left_tag == "--"):
            return True
        elif left_tag == right_tag[1:] \
            and right_tag[0] != "<":
            return True
        else:
            return False

    def _is_oneliner(self, tag):
        return (tag in ['hr', 'hr/'])

    
    def run (self, text):

        new_blocks = []
        text = text.split("\n\n")
        
        items = []
        left_tag = ''
        right_tag = ''
        in_tag = False # flag
        
        for block in text:
            if block.startswith("\n"):
                block = block[1:]

            if not in_tag:

                if block.startswith("<"):
                    
                    left_tag = self._get_left_tag(block)
                    right_tag = self._get_right_tag(left_tag, block)

                    if not (is_block_level(left_tag) \
                        or block[1] in ["!", "?", "@", "%"]):
                        new_blocks.append(block)
                        continue

                    if self._is_oneliner(left_tag):
                        new_blocks.append(block.strip())
                        continue
                        
                    if block[1] == "!":
                        # is a comment block
                        left_tag = "--"
                        right_tag = self._get_right_tag(left_tag, block)
                        # keep checking conditions below and maybe just append
                        
                    if block.rstrip().endswith(">") \
                        and self._equal_tags(left_tag, right_tag):
                        new_blocks.append(
                            self.stash.store(block.strip()))
                        continue
                    else: #if not block[1] == "!":
                        # if is block level tag and is not complete
                        items.append(block.strip())
                        in_tag = True
                        continue

                new_blocks.append(block)

            else:
                items.append(block.strip())
                
                right_tag = self._get_right_tag(left_tag, block)
                
                if self._equal_tags(left_tag, right_tag):
                    # if find closing tag
                    in_tag = False
                    new_blocks.append(
                        self.stash.store('\n\n'.join(items)))
                    items = []

        if items:
            new_blocks.append(self.stash.store('\n\n'.join(items)))
            new_blocks.append('\n')
            
        return "\n\n".join(new_blocks)

HTML_BLOCK_PREPROCESSOR = HtmlBlockPreprocessor()


class ReferencePreprocessor (Preprocessor):

    def run (self, lines):

        new_text = [];
        for line in lines:
            m = RE.regExp['reference-def'].match(line)
            if m:
                id = m.group(2).strip().lower()
                t = m.group(4).strip()  # potential title
                if not t:
                    self.references[id] = (m.group(3), t)
                elif (len(t) >= 2
                      and (t[0] == t[-1] == "\""
                           or t[0] == t[-1] == "\'"
                           or (t[0] == "(" and t[-1] == ")") ) ):
                    self.references[id] = (m.group(3), t[1:-1])
                else:
                    new_text.append(line)
            else:
                new_text.append(line)

        return new_text #+ "\n"

REFERENCE_PREPROCESSOR = ReferencePreprocessor()

"""
======================================================================
========================== INLINE PATTERNS ===========================
======================================================================

Inline patterns such as *emphasis* are handled by means of auxiliary
objects, one per pattern.  Pattern objects must be instances of classes
that extend markdown.Pattern.  Each pattern object uses a single regular
expression and needs support the following methods:

  pattern.getCompiledRegExp() - returns a regular expression

  pattern.handleMatch(m, doc) - takes a match object and returns
                                a NanoDom node (as a part of the provided
                                doc) or None

All of python markdown's built-in patterns subclass from Patter,
but you can add additional patterns that don't.

Also note that all the regular expressions used by inline must
capture the whole block.  For this reason, they all start with
'^(.*)' and end with '(.*)!'.  In case with built-in expression
Pattern takes care of adding the "^(.*)" and "(.*)!".

Finally, the order in which regular expressions are applied is very
important - e.g. if we first replace http://.../ links with <a> tags
and _then_ try to replace inline html, we would end up with a mess.
So, we apply the expressions in the following order:

       * escape and backticks have to go before everything else, so
         that we can preempt any markdown patterns by escaping them.

       * then we handle auto-links (must be done before inline html)

       * then we handle inline HTML.  At this point we will simply
         replace all inline HTML strings with a placeholder and add
         the actual HTML to a hash.

       * then inline images (must be done before links)

       * then bracketed links, first regular then reference-style

       * finally we apply strong and emphasis
"""

NOBRACKET = r'[^\]\[]*'
BRK = ( r'\[('
        + (NOBRACKET + r'(\[')*6
        + (NOBRACKET+ r'\])*')*6
        + NOBRACKET + r')\]' )
NOIMG = r'(?<!\!)'

BACKTICK_RE = r'\`([^\`]*)\`'                    # `e= m*c^2`
DOUBLE_BACKTICK_RE =  r'\`\`(.*)\`\`'            # ``e=f("`")``
ESCAPE_RE = r'\\(.)'                             # \<
EMPHASIS_RE = r'\*([^\*]*)\*'                    # *emphasis*
STRONG_RE = r'\*\*(.*)\*\*'                      # **strong**
STRONG_EM_RE = r'\*\*\*([^_]*)\*\*\*'            # ***strong***

if SMART_EMPHASIS:
    EMPHASIS_2_RE = r'(?<!\S)_(\S[^_]*)_'        # _emphasis_
else:
    EMPHASIS_2_RE = r'_([^_]*)_'                 # _emphasis_

STRONG_2_RE = r'__([^_]*)__'                     # __strong__
STRONG_EM_2_RE = r'___([^_]*)___'                # ___strong___

LINK_RE = NOIMG + BRK + r'\s*\(([^\)]*)\)'               # [text](url)
LINK_ANGLED_RE = NOIMG + BRK + r'\s*\(<([^\)]*)>\)'      # [text](<url>)
IMAGE_LINK_RE = r'\!' + BRK + r'\s*\(([^\)]*)\)' # ![alttxt](http://x.com/)
REFERENCE_RE = NOIMG + BRK+ r'\s*\[([^\]]*)\]'           # [Google][3]
IMAGE_REFERENCE_RE = r'\!' + BRK + '\s*\[([^\]]*)\]' # ![alt text][2]
NOT_STRONG_RE = r'( \* )'                        # stand-alone * or _
AUTOLINK_RE = r'<(http://[^>]*)>'                # <http://www.123.com>
AUTOMAIL_RE = r'<([^> \!]*@[^> ]*)>'               # <me@example.com>
#HTML_RE = r'(\<[^\>]*\>)'                        # <...>
HTML_RE = r'(\<[a-zA-Z/][^\>]*\>)'               # <...>
ENTITY_RE = r'(&[\#a-zA-Z0-9]*;)'                # &amp;
LINE_BREAK_RE = r'  \n'                     # two spaces at end of line
LINE_BREAK_2_RE = r'  $'                    # two spaces at end of text

class Pattern:

    def __init__ (self, pattern):
        self.pattern = pattern
        self.compiled_re = re.compile("^(.*)%s(.*)$" % pattern, re.DOTALL)

    def getCompiledRegExp (self):
        return self.compiled_re

BasePattern = Pattern # for backward compatibility

class SimpleTextPattern (Pattern):

    def handleMatch(self, m, doc):
        return doc.createTextNode(m.group(2))

class SimpleTagPattern (Pattern):

    def __init__ (self, pattern, tag):
        Pattern.__init__(self, pattern)
        self.tag = tag

    def handleMatch(self, m, doc):
        el = doc.createElement(self.tag)
        el.appendChild(doc.createTextNode(m.group(2)))
        return el

class SubstituteTagPattern (SimpleTagPattern):

    def handleMatch (self, m, doc):
        return doc.createElement(self.tag)

class BacktickPattern (Pattern):

    def __init__ (self, pattern):
        Pattern.__init__(self, pattern)
        self.tag = "code"

    def handleMatch(self, m, doc):
        el = doc.createElement(self.tag)
        text = m.group(2).strip()
        #text = text.replace("&", "&amp;")
        el.appendChild(doc.createTextNode(text))
        return el


class DoubleTagPattern (SimpleTagPattern): 

    def handleMatch(self, m, doc):
        tag1, tag2 = self.tag.split(",")
        el1 = doc.createElement(tag1)
        el2 = doc.createElement(tag2)
        el1.appendChild(el2)
        el2.appendChild(doc.createTextNode(m.group(2)))
        return el1


class HtmlPattern (Pattern):

    def handleMatch (self, m, doc):
        rawhtml = m.group(2)
        inline = True
        place_holder = self.stash.store(rawhtml)
        return doc.createTextNode(place_holder)


class LinkPattern (Pattern):

    def handleMatch(self, m, doc):
        el = doc.createElement('a')
        el.appendChild(doc.createTextNode(m.group(2)))
        parts = m.group(9).split('"')
        # We should now have [], [href], or [href, title]
        if parts:
            el.setAttribute('href', parts[0].strip())
        else:
            el.setAttribute('href', "")
        if len(parts) > 1:
            # we also got a title
            title = '"' + '"'.join(parts[1:]).strip()
            title = dequote(title) #.replace('"', "&quot;")
            el.setAttribute('title', title)
        return el


class ImagePattern (Pattern):

    def handleMatch(self, m, doc):
        el = doc.createElement('img')
        src_parts = m.group(9).split()
        if src_parts:
            el.setAttribute('src', src_parts[0])
        else:
            el.setAttribute('src', "")
        if len(src_parts) > 1:
            el.setAttribute('title', dequote(" ".join(src_parts[1:])))
        if ENABLE_ATTRIBUTES:
            text = doc.createTextNode(m.group(2))
            el.appendChild(text)
            text.handleAttributes()
            truealt = text.value
            el.childNodes.remove(text)
        else:
            truealt = m.group(2)
        el.setAttribute('alt', truealt)
        return el

class ReferencePattern (Pattern):

    def handleMatch(self, m, doc):

        if m.group(9):
            id = m.group(9).lower()
        else:
            # if we got something like "[Google][]"
            # we'll use "google" as the id
            id = m.group(2).lower()

        if not self.references.has_key(id): # ignore undefined refs
            return None
        href, title = self.references[id]
        text = m.group(2)
        return self.makeTag(href, title, text, doc)

    def makeTag(self, href, title, text, doc):
        el = doc.createElement('a')
        el.setAttribute('href', href)
        if title:
            el.setAttribute('title', title)
        el.appendChild(doc.createTextNode(text))
        return el


class ImageReferencePattern (ReferencePattern):

    def makeTag(self, href, title, text, doc):
        el = doc.createElement('img')
        el.setAttribute('src', href)
        if title:
            el.setAttribute('title', title)
        el.setAttribute('alt', text)
        return el


class AutolinkPattern (Pattern):

    def handleMatch(self, m, doc):
        el = doc.createElement('a')
        el.setAttribute('href', m.group(2))
        el.appendChild(doc.createTextNode(m.group(2)))
        return el

class AutomailPattern (Pattern):

    def handleMatch(self, m, doc):
        el = doc.createElement('a')
        email = m.group(2)
        if email.startswith("mailto:"):
            email = email[len("mailto:"):]
        for letter in email:
            entity = doc.createEntityReference("#%d" % ord(letter))
            el.appendChild(entity)
        mailto = "mailto:" + email
        mailto = "".join(['&#%d;' % ord(letter) for letter in mailto])
        el.setAttribute('href', mailto)
        return el

ESCAPE_PATTERN          = SimpleTextPattern(ESCAPE_RE)
NOT_STRONG_PATTERN      = SimpleTextPattern(NOT_STRONG_RE)

BACKTICK_PATTERN        = BacktickPattern(BACKTICK_RE)
DOUBLE_BACKTICK_PATTERN = BacktickPattern(DOUBLE_BACKTICK_RE)
STRONG_PATTERN          = SimpleTagPattern(STRONG_RE, 'strong')
STRONG_PATTERN_2        = SimpleTagPattern(STRONG_2_RE, 'strong')
EMPHASIS_PATTERN        = SimpleTagPattern(EMPHASIS_RE, 'em')
EMPHASIS_PATTERN_2      = SimpleTagPattern(EMPHASIS_2_RE, 'em')

STRONG_EM_PATTERN       = DoubleTagPattern(STRONG_EM_RE, 'strong,em')
STRONG_EM_PATTERN_2     = DoubleTagPattern(STRONG_EM_2_RE, 'strong,em')

LINE_BREAK_PATTERN      = SubstituteTagPattern(LINE_BREAK_RE, 'br ')
LINE_BREAK_PATTERN_2    = SubstituteTagPattern(LINE_BREAK_2_RE, 'br ')

LINK_PATTERN            = LinkPattern(LINK_RE)
LINK_ANGLED_PATTERN     = LinkPattern(LINK_ANGLED_RE)
IMAGE_LINK_PATTERN      = ImagePattern(IMAGE_LINK_RE)
IMAGE_REFERENCE_PATTERN = ImageReferencePattern(IMAGE_REFERENCE_RE)
REFERENCE_PATTERN       = ReferencePattern(REFERENCE_RE)

HTML_PATTERN            = HtmlPattern(HTML_RE)
ENTITY_PATTERN          = HtmlPattern(ENTITY_RE)

AUTOLINK_PATTERN        = AutolinkPattern(AUTOLINK_RE)
AUTOMAIL_PATTERN        = AutomailPattern(AUTOMAIL_RE)


"""
======================================================================
========================== POST-PROCESSORS ===========================
======================================================================

Markdown also allows post-processors, which are similar to
preprocessors in that they need to implement a "run" method.  Unlike
pre-processors, they take a NanoDom document as a parameter and work
with that.

Post-Processor should extend markdown.Postprocessor.

There are currently no standard post-processors, but the footnote
extension below uses one.
"""

class Postprocessor:
    pass


"""
======================================================================
======================== TEXT-POST-PROCESSORS ========================
======================================================================

Markdown also allows text-post-processors, which are similar to
textpreprocessors in that they need to implement a "run" method.  
Unlike post-processors, they take a text string as a parameter and 
should return a string.

Text-Post-Processors should extend markdown.Postprocessor.

"""


class RawHtmlTextPostprocessor(Postprocessor):

    def __init__(self):
        pass

    def run(self, text):
        for i in range(self.stash.html_counter):
            html, safe  = self.stash.rawHtmlBlocks[i]
            if self.safeMode and not safe:
                if str(self.safeMode).lower() == 'escape':
                    html = self.escape(html)
                elif str(self.safeMode).lower() == 'remove':
                    html = ''
                else:
                    html = HTML_REMOVED_TEXT
                                   
            text = text.replace("<p>%s\n</p>" % (HTML_PLACEHOLDER % i),
                              html + "\n")
            text =  text.replace(HTML_PLACEHOLDER % i, html)
        return text

    def escape(self, html):
        ''' Basic html escaping '''
        html = html.replace('&', '&amp;')
        html = html.replace('<', '&lt;')
        html = html.replace('>', '&gt;')
        return html.replace('"', '&quot;')

RAWHTMLTEXTPOSTPROCESSOR = RawHtmlTextPostprocessor()

"""
======================================================================
========================== MISC AUXILIARY CLASSES ====================
======================================================================
"""

class HtmlStash:
    """This class is used for stashing HTML objects that we extract
        in the beginning and replace with place-holders."""

    def __init__ (self):
        self.html_counter = 0 # for counting inline html segments
        self.rawHtmlBlocks=[]

    def store(self, html, safe=False):
        """Saves an HTML segment for later reinsertion.  Returns a
           placeholder string that needs to be inserted into the
           document.

           @param html: an html segment
           @param safe: label an html segment as safe for safemode
           @param inline: label a segmant as inline html
           @returns : a placeholder string """
        self.rawHtmlBlocks.append((html, safe))
        placeholder = HTML_PLACEHOLDER % self.html_counter
        self.html_counter += 1
        return placeholder


class BlockGuru:

    def _findHead(self, lines, fn, allowBlank=0):

        """Functional magic to help determine boundaries of indented
           blocks.

           @param lines: an array of strings
           @param fn: a function that returns a substring of a string
                      if the string matches the necessary criteria
           @param allowBlank: specifies whether it's ok to have blank
                      lines between matching functions
           @returns: a list of post processes items and the unused
                      remainder of the original list"""

        items = []
        item = -1

        i = 0 # to keep track of where we are

        for line in lines:

            if not line.strip() and not allowBlank:
                return items, lines[i:]

            if not line.strip() and allowBlank:
                # If we see a blank line, this _might_ be the end
                i += 1

                # Find the next non-blank line
                for j in range(i, len(lines)):
                    if lines[j].strip():
                        next = lines[j]
                        break
                else:
                    # There is no more text => this is the end
                    break

                # Check if the next non-blank line is still a part of the list

                part = fn(next)

                if part:
                    items.append("")
                    continue
                else:
                    break # found end of the list

            part = fn(line)

            if part:
                items.append(part)
                i += 1
                continue
            else:
                return items, lines[i:]
        else:
            i += 1

        return items, lines[i:]


    def detabbed_fn(self, line):
        """ An auxiliary method to be passed to _findHead """
        m = RE.regExp['tabbed'].match(line)
        if m:
            return m.group(4)
        else:
            return None


    def detectTabbed(self, lines):

        return self._findHead(lines, self.detabbed_fn,
                              allowBlank = 1)


def print_error(string):
    """Print an error string to stderr"""
    sys.stderr.write(string +'\n')


def dequote(string):
    """ Removes quotes from around a string """
    if ( ( string.startswith('"') and string.endswith('"'))
         or (string.startswith("'") and string.endswith("'")) ):
        return string[1:-1]
    else:
        return string

"""
======================================================================
========================== CORE MARKDOWN =============================
======================================================================

This stuff is ugly, so if you are thinking of extending the syntax,
see first if you can do it via pre-processors, post-processors,
inline patterns or a combination of the three.
"""

class CorePatterns:
    """This class is scheduled for removal as part of a refactoring
        effort."""

    patterns = {
        'header':          r'(#*)([^#]*)(#*)', # # A title
        'reference-def':   r'(\ ?\ ?\ ?)\[([^\]]*)\]:\s*([^ ]*)(.*)',
                           # [Google]: http://www.google.com/
        'containsline':    r'([-]*)$|^([=]*)', # -----, =====, etc.
        'ol':              r'[ ]{0,3}[\d]*\.\s+(.*)', # 1. text
        'ul':              r'[ ]{0,3}[*+-]\s+(.*)', # "* text"
        'isline1':         r'(\**)', # ***
        'isline2':         r'(\-*)', # ---
        'isline3':         r'(\_*)', # ___
        'tabbed':          r'((\t)|(    ))(.*)', # an indented line
        'quoted':          r'> ?(.*)', # a quoted block ("> ...")
    }

    def __init__ (self):

        self.regExp = {}
        for key in self.patterns.keys():
            self.regExp[key] = re.compile("^%s$" % self.patterns[key],
                                          re.DOTALL)

        self.regExp['containsline'] = re.compile(r'^([-]*)$|^([=]*)$', re.M)

RE = CorePatterns()


class Markdown:
    """ Markdown formatter class for creating an html document from
        Markdown text """


    def __init__(self, source=None,  # depreciated
                 extensions=[],
                 extension_configs=None,
                 safe_mode = False):
        """Creates a new Markdown instance.

           @param source: The text in Markdown format. Depreciated!
           @param extensions: A list if extensions.
           @param extension-configs: Configuration setting for extensions.
           @param safe_mode: Disallow raw html. """

        self.source = source
        if source is not None:
            message(WARN, "The `source` arg of Markdown.__init__() is depreciated and will be removed in the future. Use `instance.convert(source)` instead.")
        self.safeMode = safe_mode
        self.blockGuru = BlockGuru()
        self.registeredExtensions = []
        self.stripTopLevelTags = 1
        self.docType = ""

        self.textPreprocessors = [HTML_BLOCK_PREPROCESSOR]

        self.preprocessors = [HEADER_PREPROCESSOR,
                              LINE_PREPROCESSOR,
                              # A footnote preprocessor will
                              # get inserted here
                              REFERENCE_PREPROCESSOR]


        self.postprocessors = [] # a footnote postprocessor will get
                                 # inserted later

        self.textPostprocessors = [# a footnote postprocessor will get
                                   # inserted here
                                   RAWHTMLTEXTPOSTPROCESSOR]

        self.prePatterns = []
        

        self.inlinePatterns = [DOUBLE_BACKTICK_PATTERN,
                               BACKTICK_PATTERN,
                               ESCAPE_PATTERN,
                               REFERENCE_PATTERN,
                               LINK_ANGLED_PATTERN,
                               LINK_PATTERN,
                               IMAGE_LINK_PATTERN,
			                   IMAGE_REFERENCE_PATTERN,
			                   AUTOLINK_PATTERN,
                               AUTOMAIL_PATTERN,
                               LINE_BREAK_PATTERN_2,
                               LINE_BREAK_PATTERN,
                               HTML_PATTERN,
                               ENTITY_PATTERN,
                               NOT_STRONG_PATTERN,
                               STRONG_EM_PATTERN,
                               STRONG_EM_PATTERN_2,
                               STRONG_PATTERN,
                               STRONG_PATTERN_2,
                               EMPHASIS_PATTERN,
                               EMPHASIS_PATTERN_2
                               # The order of the handlers matters!!!
                               ]

        self.registerExtensions(extensions = extensions,
                                configs = extension_configs)

        self.reset()


    def registerExtensions(self, extensions, configs):
        if not configs:
            configs = {}
        for module in extensions:
            ext = module.__name__.split("_")[1]
            if configs.has_key(ext):
                configs_for_ext = configs[ext]
            else:
                configs_for_ext = []
            extension = module.makeExtension(configs_for_ext)    
            extension.extendMarkdown(self, globals())




    def registerExtension(self, extension):
        """ This gets called by the extension """
        self.registeredExtensions.append(extension)

    def reset(self):
        """Resets all state variables so that we can start
            with a new text."""
        self.references={}
        self.htmlStash = HtmlStash()

        HTML_BLOCK_PREPROCESSOR.stash = self.htmlStash
        LINE_PREPROCESSOR.stash = self.htmlStash
        REFERENCE_PREPROCESSOR.references = self.references
        HTML_PATTERN.stash = self.htmlStash
        ENTITY_PATTERN.stash = self.htmlStash
        REFERENCE_PATTERN.references = self.references
        IMAGE_REFERENCE_PATTERN.references = self.references
        RAWHTMLTEXTPOSTPROCESSOR.stash = self.htmlStash
        RAWHTMLTEXTPOSTPROCESSOR.safeMode = self.safeMode

        for extension in self.registeredExtensions:
            extension.reset()


    def _transform(self):
        """Transforms the Markdown text into a XHTML body document

           @returns: A NanoDom Document """

        # Setup the document

        self.doc = Document()
        self.top_element = self.doc.createElement("span")
        self.top_element.appendChild(self.doc.createTextNode('\n'))
        self.top_element.setAttribute('class', 'markdown')
        self.doc.appendChild(self.top_element)

        # Fixup the source text
        text = self.source
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text += "\n\n"
        text = text.expandtabs(TAB_LENGTH)

        # Split into lines and run the preprocessors that will work with
        # self.lines

        self.lines = text.split("\n")

        # Run the pre-processors on the lines
        for prep in self.preprocessors :
            self.lines = prep.run(self.lines)

        # Create a NanoDom tree from the lines and attach it to Document


        buffer = []
        for line in self.lines:
            if line.startswith("#"):
                self._processSection(self.top_element, buffer)
                buffer = [line]
            else:
                buffer.append(line)
        self._processSection(self.top_element, buffer)
        
        #self._processSection(self.top_element, self.lines)

        # Not sure why I put this in but let's leave it for now.
        self.top_element.appendChild(self.doc.createTextNode('\n'))

        # Run the post-processors
        for postprocessor in self.postprocessors:
            postprocessor.run(self.doc)

        return self.doc


    def _processSection(self, parent_elem, lines,
                        inList = 0, looseList = 0):

        """Process a section of a source document, looking for high
           level structural elements like lists, block quotes, code
           segments, html blocks, etc.  Some those then get stripped
           of their high level markup (e.g. get unindented) and the
           lower-level markup is processed recursively.

           @param parent_elem: A NanoDom element to which the content
                               will be added
           @param lines: a list of lines
           @param inList: a level
           @returns: None"""

        # Loop through lines until none left.
        while lines:

            # Check if this section starts with a list, a blockquote or
            # a code block

            processFn = { 'ul':     self._processUList,
                          'ol':     self._processOList,
                          'quoted': self._processQuote,
                          'tabbed': self._processCodeBlock}

            for regexp in ['ul', 'ol', 'quoted', 'tabbed']:
                m = RE.regExp[regexp].match(lines[0])
                if m:
                    processFn[regexp](parent_elem, lines, inList)
                    return

            # We are NOT looking at one of the high-level structures like
            # lists or blockquotes.  So, it's just a regular paragraph
            # (though perhaps nested inside a list or something else).  If
            # we are NOT inside a list, we just need to look for a blank
            # line to find the end of the block.  If we ARE inside a
            # list, however, we need to consider that a sublist does not
            # need to be separated by a blank line.  Rather, the following
            # markup is legal:
            #
            # * The top level list item
            #
            #     Another paragraph of the list.  This is where we are now.
            #     * Underneath we might have a sublist.
            #

            if inList:

                start, lines  = self._linesUntil(lines, (lambda line:
                                 RE.regExp['ul'].match(line)
                                 or RE.regExp['ol'].match(line)
                                                  or not line.strip()))

                self._processSection(parent_elem, start,
                                     inList - 1, looseList = looseList)
                inList = inList-1

            else: # Ok, so it's just a simple block

                paragraph, lines = self._linesUntil(lines, lambda line:
                                                     not line.strip())

                if len(paragraph) and paragraph[0].startswith('#'):
                    self._processHeader(parent_elem, paragraph)

                elif paragraph:
                    self._processParagraph(parent_elem, paragraph,
                                          inList, looseList)

            if lines and not lines[0].strip():
                lines = lines[1:]  # skip the first (blank) line


    def _processHeader(self, parent_elem, paragraph):
        m = RE.regExp['header'].match(paragraph[0])
        if m:
            level = len(m.group(1))
            h = self.doc.createElement("h%d" % level)
            parent_elem.appendChild(h)
            for item in self._handleInlineWrapper(m.group(2).strip()):
                h.appendChild(item)
        else:
            message(CRITICAL, "We've got a problem header!")


    def _processParagraph(self, parent_elem, paragraph, inList, looseList):
        list = self._handleInlineWrapper("\n".join(paragraph))

        if ( parent_elem.nodeName == 'li'
                and not (looseList or parent_elem.childNodes)):

            # If this is the first paragraph inside "li", don't
            # put <p> around it - append the paragraph bits directly
            # onto parent_elem
            el = parent_elem
        else:
            # Otherwise make a "p" element
            el = self.doc.createElement("p")
            parent_elem.appendChild(el)

        for item in list:
            el.appendChild(item)
 

    def _processUList(self, parent_elem, lines, inList):
        self._processList(parent_elem, lines, inList,
                         listexpr='ul', tag = 'ul')

    def _processOList(self, parent_elem, lines, inList):
        self._processList(parent_elem, lines, inList,
                         listexpr='ol', tag = 'ol')


    def _processList(self, parent_elem, lines, inList, listexpr, tag):
        """Given a list of document lines starting with a list item,
           finds the end of the list, breaks it up, and recursively
           processes each list item and the remainder of the text file.

           @param parent_elem: A dom element to which the content will be added
           @param lines: a list of lines
           @param inList: a level
           @returns: None"""

        ul = self.doc.createElement(tag)  # ul might actually be '<ol>'
        parent_elem.appendChild(ul)

        looseList = 0

        # Make a list of list items
        items = []
        item = -1

        i = 0  # a counter to keep track of where we are

        for line in lines: 

            loose = 0
            if not line.strip():
                # If we see a blank line, this _might_ be the end of the list
                i += 1
                loose = 1

                # Find the next non-blank line
                for j in range(i, len(lines)):
                    if lines[j].strip():
                        next = lines[j]
                        break
                else:
                    # There is no more text => end of the list
                    break

                # Check if the next non-blank line is still a part of the list
                if ( RE.regExp['ul'].match(next) or
                     RE.regExp['ol'].match(next) or 
                     RE.regExp['tabbed'].match(next) ):
                    # get rid of any white space in the line
                    items[item].append(line.strip())
                    looseList = loose or looseList
                    continue
                else:
                    break # found end of the list

            # Now we need to detect list items (at the current level)
            # while also detabing child elements if necessary

            for expr in ['ul', 'ol', 'tabbed']:

                m = RE.regExp[expr].match(line)
                if m:
                    if expr in ['ul', 'ol']:  # We are looking at a new item
                        #if m.group(1) :
                        # Removed the check to allow for a blank line
                        # at the beginning of the list item
                        items.append([m.group(1)])
                        item += 1
                    elif expr == 'tabbed':  # This line needs to be detabbed
                        items[item].append(m.group(4)) #after the 'tab'

                    i += 1
                    break
            else:
                items[item].append(line)  # Just regular continuation
                i += 1 # added on 2006.02.25
        else:
            i += 1

        # Add the dom elements
        for item in items:
            li = self.doc.createElement("li")
            ul.appendChild(li)

            self._processSection(li, item, inList + 1, looseList = looseList)

        # Process the remaining part of the section

        self._processSection(parent_elem, lines[i:], inList)


    def _linesUntil(self, lines, condition):
        """ A utility function to break a list of lines upon the
            first line that satisfied a condition.  The condition
            argument should be a predicate function.
            """

        i = -1
        for line in lines:
            i += 1
            if condition(line): break
        else:
            i += 1
        return lines[:i], lines[i:]

    def _processQuote(self, parent_elem, lines, inList):
        """Given a list of document lines starting with a quote finds
           the end of the quote, unindents it and recursively
           processes the body of the quote and the remainder of the
           text file.

           @param parent_elem: DOM element to which the content will be added
           @param lines: a list of lines
           @param inList: a level
           @returns: None """

        dequoted = []
        i = 0
        blank_line = False # allow one blank line between paragraphs
        for line in lines:
            m = RE.regExp['quoted'].match(line)
            if m:
                dequoted.append(m.group(1))
                i += 1
                blank_line = False
            elif not blank_line and line.strip() != '':
                dequoted.append(line)
                i += 1
            elif not blank_line and line.strip() == '':
                dequoted.append(line)
                i += 1
                blank_line = True
            else:
                break

        blockquote = self.doc.createElement('blockquote')
        parent_elem.appendChild(blockquote)

        self._processSection(blockquote, dequoted, inList)
        self._processSection(parent_elem, lines[i:], inList)




    def _processCodeBlock(self, parent_elem, lines, inList):
        """Given a list of document lines starting with a code block
           finds the end of the block, puts it into the dom verbatim
           wrapped in ("<pre><code>") and recursively processes the
           the remainder of the text file.

           @param parent_elem: DOM element to which the content will be added
           @param lines: a list of lines
           @param inList: a level
           @returns: None"""

        detabbed, theRest = self.blockGuru.detectTabbed(lines)

        pre = self.doc.createElement('pre')
        code = self.doc.createElement('code')
        parent_elem.appendChild(pre)
        pre.appendChild(code)
        text = "\n".join(detabbed).rstrip()+"\n"
        #text = text.replace("&", "&amp;")
        code.appendChild(self.doc.createTextNode(text))
        self._processSection(parent_elem, theRest, inList)



    def _handleInlineWrapper (self, line, patternIndex=0):

        parts = [line]

        while patternIndex < len(self.inlinePatterns):

            i = 0

            while i < len(parts):
                
                x = parts[i]

                if isinstance(x, (str, unicode)):
                    result = self._applyPattern(x, \
                                self.inlinePatterns[patternIndex], \
                                patternIndex)

                    if result:
                        i -= 1
                        parts.remove(x)
                        for y in result:
                            parts.insert(i+1,y)

                i += 1
            patternIndex += 1

        for i in range(len(parts)):
            x = parts[i]
            if isinstance(x, (str, unicode)):
                parts[i] = self.doc.createTextNode(x)

        return parts
        

    def _handleInline(self,  line):
        """Transform a Markdown line with inline elements to an XHTML
        fragment.

        This function uses auxiliary objects called inline patterns.
        See notes on inline patterns above.

        @param item: A block of Markdown text
        @return: A list of NanoDom nodes """

        if not(line):
            return [self.doc.createTextNode(' ')]

        for pattern in self.inlinePatterns:
            list = self._applyPattern( line, pattern)
            if list: return list

        return [self.doc.createTextNode(line)]

    def _applyPattern(self, line, pattern, patternIndex):

        """ Given a pattern name, this function checks if the line
        fits the pattern, creates the necessary elements, and returns
        back a list consisting of NanoDom elements and/or strings.
        
        @param line: the text to be processed
        @param pattern: the pattern to be checked

        @returns: the appropriate newly created NanoDom element if the
                  pattern matches, None otherwise.
        """

        # match the line to pattern's pre-compiled reg exp.
        # if no match, move on.



        m = pattern.getCompiledRegExp().match(line)
        if not m:
            return None

        # if we got a match let the pattern make us a NanoDom node
        # if it doesn't, move on
        node = pattern.handleMatch(m, self.doc)

        # check if any of this nodes have children that need processing

        if isinstance(node, Element):

            if not node.nodeName in ["code", "pre"]:
                for child in node.childNodes:
                    if isinstance(child, TextNode):
                        
                        result = self._handleInlineWrapper(child.value, patternIndex+1)
                        
                        if result:

                            if result == [child]:
                                continue
                                
                            result.reverse()
                            #to make insertion easier

                            position = node.childNodes.index(child)
                            
                            node.removeChild(child)

                            for item in result:

                                if isinstance(item, (str, unicode)):
                                    if len(item) > 0:
                                        node.insertChild(position,
                                             self.doc.createTextNode(item))
                                else:
                                    node.insertChild(position, item)
                



        if node:
            # Those are in the reverse order!
            return ( m.groups()[-1], # the string to the left
                     node,           # the new node
                     m.group(1))     # the string to the right of the match

        else:
            return None

    def convert (self, source = None):
        """Return the document in XHTML format.

        @returns: A serialized XHTML body."""

        if source is not None: #Allow blank string
            self.source = source

        if not self.source:
            return u""

        try:
            self.source = unicode(self.source)
        except UnicodeDecodeError:
            message(CRITICAL, 'UnicodeDecodeError: Markdown only accepts unicode or ascii  input.')
            return u""

        for pp in self.textPreprocessors:
            self.source = pp.run(self.source)

        doc = self._transform()
        xml = doc.toxml()


        # Return everything but the top level tag

        if self.stripTopLevelTags:
            xml = xml.strip()[23:-7] + "\n"

        for pp in self.textPostprocessors:
            xml = pp.run(xml)

        return (self.docType + xml).strip()


    def __str__(self):
        ''' Report info about instance. Markdown always returns unicode. '''
        if self.source is None:
            status = 'in which no source text has been assinged.'
        else:
            status = 'which contains %d chars and %d line(s) of source.'%\
                     (len(self.source), self.source.count('\n')+1)
        return 'An instance of "%s" %s'% (self.__class__, status)

    __unicode__ = convert # markdown should always return a unicode string





# ====================================================================

def markdownFromFile(input = None,
                     output = None,
                     extensions = [],
                     encoding = None,
                     message_threshold = CRITICAL,
                     safe = False):

    global console_hndlr
    console_hndlr.setLevel(message_threshold)

    message(DEBUG, "input file: %s" % input)

    if not encoding:
        encoding = "utf-8"

    input_file = codecs.open(input, mode="r", encoding=encoding)
    text = input_file.read()
    input_file.close()

    text = removeBOM(text, encoding)

    new_text = markdown(text, extensions, safe_mode = safe)

    if output:
        output_file = codecs.open(output, "w", encoding=encoding)
        output_file.write(new_text)
        output_file.close()

    else:
        sys.stdout.write(new_text.encode(encoding))

def markdown(text,
             extensions = [],
             safe_mode = False):
    
    message(DEBUG, "in markdown.markdown(), received text:\n%s" % text)

    extension_names = []
    extension_configs = {}
    
    for ext in extensions:
        pos = ext.find("(") 
        if pos == -1:
            extension_names.append(ext)
        else:
            name = ext[:pos]
            extension_names.append(name)
            pairs = [x.split("=") for x in ext[pos+1:-1].split(",")]
            configs = [(x.strip(), y.strip()) for (x, y) in pairs]
            extension_configs[name] = configs

    md = Markdown(extensions=extension_names,
                  extension_configs=extension_configs,
                  safe_mode = safe_mode)

    return md.convert(text)
        

class Extension:

    def __init__(self, configs = {}):
        self.config = configs

    def getConfig(self, key):
        if self.config.has_key(key):
            return self.config[key][0]
        else:
            return ""

    def getConfigInfo(self):
        return [(key, self.config[key][1]) for key in self.config.keys()]

    def setConfig(self, key, value):
        self.config[key][0] = value


OPTPARSE_WARNING = """
Python 2.3 or higher required for advanced command line options.
For lower versions of Python use:

      %s INPUT_FILE > OUTPUT_FILE
    
""" % EXECUTABLE_NAME_FOR_USAGE

def parse_options():

    try:
        optparse = __import__("optparse")
    except:
        if len(sys.argv) == 2:
            return {'input': sys.argv[1],
                    'output': None,
                    'message_threshold': CRITICAL,
                    'safe': False,
                    'extensions': [],
                    'encoding': None }

        else:
            print OPTPARSE_WARNING
            return None

    parser = optparse.OptionParser(usage="%prog INPUTFILE [options]")

    parser.add_option("-f", "--file", dest="filename",
                      help="write output to OUTPUT_FILE",
                      metavar="OUTPUT_FILE")
    parser.add_option("-e", "--encoding", dest="encoding",
                      help="encoding for input and output files",)
    parser.add_option("-q", "--quiet", default = CRITICAL,
                      action="store_const", const=60, dest="verbose",
                      help="suppress all messages")
    parser.add_option("-v", "--verbose",
                      action="store_const", const=INFO, dest="verbose",
                      help="print info messages")
    parser.add_option("-s", "--safe", dest="safe", default=False,
                      metavar="SAFE_MODE",
                      help="same mode ('replace', 'remove' or 'escape'  user's HTML tag)")
    
    parser.add_option("--noisy",
                      action="store_const", const=DEBUG, dest="verbose",
                      help="print debug messages")
    parser.add_option("-x", "--extension", action="append", dest="extensions",
                      help = "load extension EXTENSION", metavar="EXTENSION")

    (options, args) = parser.parse_args()

    if not len(args) == 1:
        parser.print_help()
        return None
    else:
        input_file = args[0]

    if not options.extensions:
        options.extensions = []

    return {'input': input_file,
            'output': options.filename,
            'message_threshold': options.verbose,
            'safe': options.safe,
            'extensions': options.extensions,
            'encoding': options.encoding }

if __name__ == '__main__':
    """ Run Markdown from the command line. """

    options = parse_options()

    #if os.access(inFile, os.R_OK):

    if not options:
        sys.exit(0)
    
    markdownFromFile(**options)











########NEW FILE########
__FILENAME__ = mdx_code
import re
from lifeflow.markdown import markdown
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name


class CodeExtension (markdown.Extension):

    def __name__(self):
        return u"code"

    def extendMarkdown(self, md, md_global):
        preprocessor = CodeBlockPreprocessor()
        preprocessor.md = md
        md.textPreprocessors.insert(0, preprocessor)


CODE_BLOCK_REGEX = re.compile(r"\r?\n(?P<spaces>[ ]*)(?P<fence>@{2,})[[ ]*(?P<syntax>[a-zA-Z0-9_+-]+)[ ]*(?P<linenos>[a-zA-Z]*)[ ]*\r?\n(?P<code>.*?)(?P=fence)[ ]*\r?\n?$", re.DOTALL | re.MULTILINE)

class CodeBlockPreprocessor :
    def run (self, text):
        while  1:
            m = CODE_BLOCK_REGEX.search(text)
            if not m: break;
            spaces = len(m.group('spaces'))
            lexer = get_lexer_by_name(m.group('syntax'))
            linenos = m.group('linenos')
            unspaced = [x[spaces:] for x in re.split('\r?\n', m.group('code'))]
            color = highlight("\n".join(unspaced), lexer, HtmlFormatter(linenos=linenos))
            placeholder = self.md.htmlStash.store(color, safe=True)
            text = '%s\n%s\n%s'% (text[:m.start()], (' '*spaces)+placeholder, text[m.end():])
        return text


def makeExtension(configs=None) :
    return CodeExtension(configs=configs)


########NEW FILE########
__FILENAME__ = mdx_footnotes
"""
========================= FOOTNOTES =================================

This section adds footnote handling to markdown.  It can be used as
an example for extending python-markdown with relatively complex
functionality.  While in this case the extension is included inside
the module itself, it could just as easily be added from outside the
module.  Not that all markdown classes above are ignorant about
footnotes.  All footnote functionality is provided separately and
then added to the markdown instance at the run time.

Footnote functionality is attached by calling extendMarkdown()
method of FootnoteExtension.  The method also registers the
extension to allow it's state to be reset by a call to reset()
method.
"""

FN_BACKLINK_TEXT = "zz1337820767766393qq"

from lifeflow.markdown import markdown
import re, random

class FootnoteExtension (markdown.Extension):

    DEF_RE = re.compile(r'(\ ?\ ?\ ?)\[\^([^\]]*)\]:\s*(.*)')
    SHORT_USE_RE = re.compile(r'\[\^([^\]]*)\]', re.M) # [^a]

    def __init__ (self, configs) :

        self.config = {'PLACE_MARKER' :
                       ["///Footnotes Go Here///",
                        "The text string that marks where the footnotes go"]}

        for key, value in configs :
            self.config[key][0] = value
            
        self.reset()


    def __name__(self):
        return u"footnotes"

    def extendMarkdown(self, md, md_globals) :

        self.md = md

        # Stateless extensions do not need to be registered
        md.registerExtension(self)

        # Insert a preprocessor before ReferencePreprocessor
        index = md.preprocessors.index(md_globals['REFERENCE_PREPROCESSOR'])
        preprocessor = FootnotePreprocessor(self)
        preprocessor.md = md
        md.preprocessors.insert(index, preprocessor)

        # Insert an inline pattern before ImageReferencePattern
        FOOTNOTE_RE = r'\[\^([^\]]*)\]' # blah blah [^1] blah
        index = md.inlinePatterns.index(md_globals['IMAGE_REFERENCE_PATTERN'])
        md.inlinePatterns.insert(index, FootnotePattern(FOOTNOTE_RE, self))

        # Insert a post-processor that would actually add the footnote div
        postprocessor = FootnotePostprocessor(self)
        postprocessor.extension = self

        md.postprocessors.append(postprocessor)
        
        textPostprocessor = FootnoteTextPostprocessor(self)

        md.textPostprocessors.append(textPostprocessor)


    def reset(self) :
        # May be called by Markdown is state reset is desired

        self.footnote_suffix = "-" + str(int(random.random()*1000000000))
        self.used_footnotes={}
        self.footnotes = {}

    def findFootnotesPlaceholder(self, doc) :
        def findFootnotePlaceholderFn(node=None, indent=0):
            if node.type == 'text':
                if node.value.find(self.getConfig("PLACE_MARKER")) > -1 :
                    return True

        fn_div_list = doc.find(findFootnotePlaceholderFn)
        if fn_div_list :
            return fn_div_list[0]


    def setFootnote(self, id, text) :
        self.footnotes[id] = text

    def makeFootnoteId(self, num) :
        return 'fn%d%s' % (num, self.footnote_suffix)

    def makeFootnoteRefId(self, num) :
        return 'fnr%d%s' % (num, self.footnote_suffix)

    def makeFootnotesDiv (self, doc) :
        """Creates the div with class='footnote' and populates it with
           the text of the footnotes.

           @returns: the footnote div as a dom element """

        if not self.footnotes.keys() :
            return None

        div = doc.createElement("div")
        div.setAttribute('class', 'footnote')
        hr = doc.createElement("hr")
        div.appendChild(hr)
        ol = doc.createElement("ol")
        div.appendChild(ol)

        footnotes = [(self.used_footnotes[id], id)
                     for id in self.footnotes.keys()]
        footnotes.sort()

        for i, id in footnotes :
            li = doc.createElement('li')
            li.setAttribute('id', self.makeFootnoteId(i))

            self.md._processSection(li, self.footnotes[id].split("\n"), looseList=1)

            #li.appendChild(doc.createTextNode(self.footnotes[id]))

            backlink = doc.createElement('a')
            backlink.setAttribute('href', '#' + self.makeFootnoteRefId(i))
            backlink.setAttribute('class', 'footnoteBackLink')
            backlink.setAttribute('title',
                                  'Jump back to footnote %d in the text' % 1)
            backlink.appendChild(doc.createTextNode(FN_BACKLINK_TEXT))

            if li.childNodes :
                node = li.childNodes[-1]
                if node.type == "text" :
		    li.appendChild(backlink)
		elif node.nodeName == "p":
                    node.appendChild(backlink)
		else:
		    p = doc.createElement('p')
		    p.appendChild(backlink)
		    li.appendChild(p)

            ol.appendChild(li)

        return div


class FootnotePreprocessor :

    def __init__ (self, footnotes) :
        self.footnotes = footnotes

    def run(self, lines) :

        self.blockGuru = markdown.BlockGuru()
        lines = self._handleFootnoteDefinitions (lines)

        # Make a hash of all footnote marks in the text so that we
        # know in what order they are supposed to appear.  (This
        # function call doesn't really substitute anything - it's just
        # a way to get a callback for each occurence.

        text = "\n".join(lines)
        self.footnotes.SHORT_USE_RE.sub(self.recordFootnoteUse, text)

        return text.split("\n")


    def recordFootnoteUse(self, match) :

        id = match.group(1)
        id = id.strip()
        nextNum = len(self.footnotes.used_footnotes.keys()) + 1
        self.footnotes.used_footnotes[id] = nextNum


    def _handleFootnoteDefinitions(self, lines) :
        """Recursively finds all footnote definitions in the lines.

            @param lines: a list of lines of text
            @returns: a string representing the text with footnote
                      definitions removed """

        i, id, footnote = self._findFootnoteDefinition(lines)

        if id :

            plain = lines[:i]

            detabbed, theRest = self.blockGuru.detectTabbed(lines[i+1:])

            self.footnotes.setFootnote(id,
                                       footnote + "\n"
                                       + "\n".join(detabbed))

            more_plain = self._handleFootnoteDefinitions(theRest)
            return plain + [""] + more_plain

        else :
            return lines

    def _findFootnoteDefinition(self, lines) :
        """Finds the first line of a footnote definition.

            @param lines: a list of lines of text
            @returns: the index of the line containing a footnote definition """

        counter = 0
        for line in lines :
            m = self.footnotes.DEF_RE.match(line)
            if m :
                return counter, m.group(2), m.group(3)
            counter += 1
        return counter, None, None


class FootnotePattern (markdown.Pattern) :

    def __init__ (self, pattern, footnotes) :

        markdown.Pattern.__init__(self, pattern)
        self.footnotes = footnotes

    def handleMatch(self, m, doc) :
        sup = doc.createElement('sup')
        a = doc.createElement('a')
        sup.appendChild(a)
        id = m.group(2)
        num = self.footnotes.used_footnotes[id]
        sup.setAttribute('id', self.footnotes.makeFootnoteRefId(num))
        a.setAttribute('href', '#' + self.footnotes.makeFootnoteId(num))
        a.appendChild(doc.createTextNode(str(num)))
        return sup

class FootnotePostprocessor (markdown.Postprocessor):

    def __init__ (self, footnotes) :
        self.footnotes = footnotes

    def run(self, doc) :
        footnotesDiv = self.footnotes.makeFootnotesDiv(doc)
        if footnotesDiv :
            fnPlaceholder = self.extension.findFootnotesPlaceholder(doc)
            if fnPlaceholder :
                fnPlaceholder.parent.replaceChild(fnPlaceholder, footnotesDiv)
            else :
                doc.documentElement.appendChild(footnotesDiv)

class FootnoteTextPostprocessor (markdown.Postprocessor):

    def __init__ (self, footnotes) :
        self.footnotes = footnotes

    def run(self, text) :
        return text.replace(FN_BACKLINK_TEXT, "&#8617;")

def makeExtension(configs=None) :
    return FootnoteExtension(configs=configs)


########NEW FILE########
__FILENAME__ = mdx_foreign_formats
import re
from lifeflow.markdown import markdown

def smart_str(s, encoding='utf-8', errors='strict'):
    """
    Returns a bytestring version of 's', encoded as specified in 'encoding'.
    Borrowed and simplified for this purpose from `django.utils.encoding`.
    """
    if not isinstance(s, basestring):
        try:
            return str(s)
        except UnicodeEncodeError:
            return unicode(s).encode(encoding, errors)
    elif isinstance(s, unicode):
        return s.encode(encoding, errors)
    elif s and encoding != 'utf-8':
        return s.decode('utf-8', errors).encode(encoding, errors)
    else:
        return s

class ForeignFormatsExtension (markdown.Extension):

    def __name__(self):
        return u"foreign formats"

    def extendMarkdown(self, md, md_global):
        preprocessor = ForeignFormatsBlockPreprocessor()
        preprocessor.md = md
        md.textPreprocessors.insert(0, preprocessor)


FORMATTERS = {}

# Attempt to import textile formatter.
try:
    # http://dealmeida.net/projects/textile/
    import textile
    def func(x):
        return textile.textile(smart_str(x), encoding='utf-8', output='utf-8')

    FORMATTERS["textile"] = func
except ImportError:
    pass

# Attempt to import docutiles (ReST) formatter.
try:
    # http://docutils.sf.net/
    from docutils.core import publish_parts
    def func(x):
        return publish_parts(source=x,writer_name="html4css1")["fragment"]

    FORMATTERS["rest"] = func
except ImportError:
    pass


FOREIGN_FORMAT_BLOCK_REGEX = re.compile(r"^~~~(?P<format>\w*)\r?\n(?P<txt>.*?)^~~~$", re.DOTALL|re.MULTILINE)


class ForeignFormatsBlockPreprocessor :
    def run (self, text):
        while  1:
            m = FOREIGN_FORMAT_BLOCK_REGEX.search(text)
            if not m: break;
            format = m.group('format').lower()
            txt = m.group('txt')
            if FORMATTERS.has_key(format):
                func = FORMATTERS[format]
                txt = func(txt)
            placeholder = self.md.htmlStash.store(txt, safe=True)
            text = '%s\n%s\n%s'% (text[:m.start()], placeholder, text[m.end():])
        return text


def makeExtension(configs=None) :
    return ForeignFormatsExtension(configs=configs)


########NEW FILE########
__FILENAME__ = mdx_lifeflow
import re
from lifeflow.markdown import markdown
import lifeflow.models

class LifeflowExtension (markdown.Extension):
    
    def __init__(self, entry):
        self.entry = entry

    def extendMarkdown(self, md, md_globals):
        preprocessor = LifeflowPreprocessor(self.entry)
        preprocessor.md = md
        md.preprocessors.insert(0, preprocessor)

    def reset(self):
        pass


def make_syntax():
    # note that the key is a tuple of the number of arguments,
    # and the name of the reference before the first space.
    # for example [refer year name] would be (2, u"refer")
    # and [absurd] would be (0, u"absurd")
    # the value is a function that accepts
    # entry, str, and then N additional parameters where
    # N is equal to the number of args specified in the
    # tuple

    # [this is my author bio][author]
    def author(entry, str):
        authors = entry.authors.all()
        if len(authors) == 1:
            return str % authors[0].get_absolute_url()
        else:
            return str % u"/author/"

    # [this is the lifeflow tag ][tag lifeflow]
    def tag(entry, str, slug):
        t = lifeflow.models.Tag.objects.get(slug=slug)
        return str % t.get_absolute_url()

    # [this is the comment with primary key 123][comment 123]
    def comment(entry, str, pk):
        c = lifeflow.models.Comment.objects.get(pk=int(pk))
        return str % c.get_absolute_url()

    # [this is the project with slug magic-wand][project magic-wand]
    def project(entry, str, slug):
        p = lifeflow.models.Project.objects.get(slug=slug)
        return str % p.get_absolute_url()


    # [remember my previous entry?][previous]
    def previous(entry, str):
        if entry.__class__.__name__ == "Entry":
            prev = entry.get_previous_article()
            if prev is None:
                return None
            return str % prev.get_absolute_url()


    # [Update: I clarified this in the next entry!][next]
    def next(entry, str):
        if entry.__class__.__name__ == "Entry":
            nxt = entry.get_next_article()
            if nxt is None:
                return None
            return str % nxt.get_absolute_url()


    # [Check out the first entry in this series][series 1]
    # [or the second entry!][series 2]
    def series_number(entry, str, nth):
        try:
            nth = int(nth)
            if nth > 0:
                nth = nth - 1
        except ValueError:
            return None
        series = entry.series.all()[0]
        if series:
            try:
                e = series.entry_set.all().order_by('pub_date')[nth]
                return str % e.get_absolute_url() 
            except IndexError:
                return None


    # [Remember the Two-Faced Django series?][series two_faced 1]
    # [Well, I wrote that too! Go me.][series jet-survival 3]
    def series_slug_number(entry, str, slug, nth):
        try:
            nth = int(nth)
            if nth > 0:
                nth = nth - 1
        except ValueError:
            return None
        try:
            series = lifeflow.models.Series.objects.get(slug=slug)
        except lifeflow.models.Series.DoesNotExist:
            return None
        try:
            e = series.entry_set.all()[nth]
            return str % e.get_absolute_url() 
        except IndexError:
            return None


    # [and check out this code!][file the_name]
    # ![ a picture that I really like][file my_pic]
    # ![ and you can abreviate it][f my_pic]
    # [this way too][f my_code]
    def file(entry, str, name):
        try:
            resource = lifeflow.models.Resource.objects.get(markdown_id=name)
            return str % resource.get_relative_url()
        except lifeflow.models.Resource.DoesNotExist:
            return None


    # [I like markdown][history md]
    # [and talk about why the lucky stiff occasionally][history why]
    # [but history is long... so...][h why]
    # [and a link to my svn][h svn_lethain]
    def history(entry, str, name):
        pass

    syntax = {}
    syntax[(0, u"previous")] = previous
    syntax[(0, u"next")] = next
    syntax[(0, u"author")] = author
    syntax[(1, u"file")] = file
    syntax[(1, u"f")] = file
    syntax[(1, u"tag")] = tag
    syntax[(1, u"comment")] = comment
    syntax[(1, u"project")] = project
    syntax[(1, u"series")] = series_number
    syntax[(2, u"series")] = series_slug_number

    return syntax



class LifeflowPreprocessor :
    
    def __init__(self, entry):
        NOBRACKET = r'[^\]\[]*'
        BRK = ( r'\[('
                + (NOBRACKET + r'(\[')*6
                + (NOBRACKET+ r'\])*')*6
                + NOBRACKET + r')\]' )
        LIFEFLOW_RE = BRK + r'\s*\[([^\]]*)\]'
        

        self.LIFEFLOW_RE = re.compile(LIFEFLOW_RE)
        self.entry = entry
        self.tags = {}
        self.syntax = make_syntax()


    def process_dynamic(self, ref):
        # if tag has already been built, ignore
        if self.tags.has_key(ref):
            return None
        parts = ref.split(u" ")
        name = parts[0]
        args = parts[1:]
        length = len(args)
        format = u"[%s]: %s" % (ref, u"%s")
        try:
            func = self.syntax[(length, name)]
            result = func(self.entry, format, *args)
            self.tags[ref] = True
            return result
        except KeyError:
            self.tags[ref] = False
            to_return = None


    def build_static_references(self):
        raw_refs = ((u'comments', u"#comments", u"Comments"),
                    (u'projects', u"/projects/", "Projects"),
                    (u'series', u"/articles/", "Series"),
                    (u'tags', u"/tags/", "Tags"))
        refs = [ u'[%s]: %s "%s"' % (x[0], x[1], x[2]) for x in raw_refs ]
        return refs


    def run (self, lines):
        def clean(match):
            return match[-1]
        text = u"\n".join(lines)
        refs = self.LIFEFLOW_RE.findall(text)
        
        cleaned = [ clean(x) for x in refs ]
        processed = [ self.process_dynamic(x) for x in cleaned]
        dynamic_refs = [ x for x in processed if x is not None ]
        static_refs = self.build_static_references()
        return static_refs + dynamic_refs + lines



def makeExtension(configs=None) :
    return LifeflowExtension(configs)
    

########NEW FILE########
__FILENAME__ = mdx_rss
import markdown

DEFAULT_URL = "http://www.freewisdom.org/projects/python-markdown/"
DEFAULT_CREATOR = "Yuri Takhteyev"
DEFAULT_TITLE = "Markdown in Python"
GENERATOR = "http://www.freewisdom.org/projects/python-markdown/markdown2rss"

month_map = { "Jan" : "01",
              "Feb" : "02",
              "March" : "03",
              "April" : "04",
              "May" : "05",
              "June" : "06",
              "July" : "07",
              "August" : "08",
              "September" : "09",
              "October" : "10",
              "November" : "11",
              "December" : "12" }

def get_time(heading) :

    heading = heading.split("-")[0]
    heading = heading.strip().replace(",", " ").replace(".", " ")

    month, date, year = heading.split()
    month = month_map[month]

    return rdftime(" ".join((month, date, year, "12:00:00 AM")))

def rdftime(time) :

    time = time.replace(":", " ")
    time = time.replace("/", " ")
    time = time.split()
    return "%s-%s-%sT%s:%s:%s-08:00" % (time[0], time[1], time[2],
                                        time[3], time[4], time[5])


def get_date(text) :
    return "date"

class RssExtension (markdown.Extension):

    def extendMarkdown(self, md, md_globals) :

        self.config = { 'URL' : [DEFAULT_URL, "Main URL"],
                        'CREATOR' : [DEFAULT_CREATOR, "Feed creator's name"],
                        'TITLE' : [DEFAULT_TITLE, "Feed title"] }

        md.xml_mode = True
        
        # Insert a post-processor that would actually add the title tag
        postprocessor = RssPostProcessor(self)
        postprocessor.ext = self
        md.postprocessors.append(postprocessor)
        md.stripTopLevelTags = 0
        md.docType = '<?xml version="1.0" encoding="utf-8"?>\n'

class RssPostProcessor (markdown.Postprocessor):

    def __init__(self, md) :
        
        pass

    def run (self, doc) :

        oldDocElement = doc.documentElement
        rss = doc.createElement("rss")
        rss.setAttribute('version', '2.0')

        doc.appendChild(rss)

        channel = doc.createElement("channel")
        rss.appendChild(channel)
        for tag, text in (("title", self.ext.getConfig("TITLE")),
                          ("link", self.ext.getConfig("URL")),
                          ("description", None)):
            channel.appendChild(doc.createElement(tag, textNode = text))

        for child in oldDocElement.childNodes :

            if child.type == "element" :

                if child.nodeName in ["h1", "h2", "h3", "h4", "h5"] :

                    heading = child.childNodes[0].value.strip()
                    
                    item = doc.createElement("item")
                    channel.appendChild(item)
                    item.appendChild(doc.createElement("link",
                                                       self.ext.getConfig("URL")))

                    item.appendChild(doc.createElement("title", heading))

                    guid = ''.join([x for x in heading if x.isalnum()])

                    guidElem = doc.createElement("guid", guid)
                    guidElem.setAttribute("isPermaLink", "false")
                    item.appendChild(guidElem)

                elif child.nodeName in ["p"] :

                    description = doc.createElement("description")

                    
                    content = "\n".join([node.toxml()
                                         for node in child.childNodes])

                    cdata = doc.createCDATA(content)

                    description.appendChild(cdata)

                    if item :
                        item.appendChild(description)


def makeExtension(configs) :

    return RssExtension(configs)

########NEW FILE########
__FILENAME__ = odt2txt
"""
ODT2TXT
=======

ODT2TXT convers files in Open Document Text format (ODT) into
Markdown-formatted plain text.

Writteby by [Yuri Takhteyev](http://www.freewisdom.org).

Project website: http://www.freewisdom.org/projects/python-markdown/odt2txt.php
Contact: yuri [at] freewisdom.org

License: GPL 2 (http://www.gnu.org/copyleft/gpl.html) or BSD

Version: 0.1 (April 7, 2006)

"""



import sys, zipfile, xml.dom.minidom

IGNORED_TAGS = ["office:annotation"]

FOOTNOTE_STYLES = ["Footnote"]


class TextProps :
    """ Holds properties for a text style. """

    def __init__ (self):
        
        self.italic = False
        self.bold = False
        self.fixed = False

    def setItalic (self, value) :
        if value == "italic" :
            self.italic = True

    def setBold (self, value) :
        if value == "bold" :
            self.bold = True

    def setFixed (self, value) :
        self.fixed = value

    def __str__ (self) :

        return "[i=%s, h=i%s, fixed=%s]" % (str(self.italic),
                                          str(self.bold),
                                          str(self.fixed))

class ParagraphProps :
    """ Holds properties of a paragraph style. """

    def __init__ (self):

        self.blockquote = False
        self.headingLevel = 0
        self.code = False
        self.title = False
        self.indented = 0

    def setIndented (self, value) :
        self.indented = value

    def setHeading (self, level) :
        self.headingLevel = level

    def setTitle (self, value):
        self.title = value

    def setCode (self, value) :
        self.code = value


    def __str__ (self) :

        return "[bq=%s, h=%d, code=%s]" % (str(self.blockquote),
                                           self.headingLevel,
                                           str(self.code))


class ListProperties :
    """ Holds properties for a list style. """

    def __init__ (self):
        self.ordered = False
 
    def setOrdered (self, value) :
        self.ordered = value


    
class OpenDocumentTextFile :


    def __init__ (self, filepath) :
        self.footnotes = []
        self.footnoteCounter = 0
        self.textStyles = {"Standard" : TextProps()}
        self.paragraphStyles = {"Standard" : ParagraphProps()}
        self.listStyles = {}
        self.fixedFonts = []
        self.hasTitle = 0

        self.load(filepath)
        

    def processFontDeclarations (self, fontDecl) :
        """ Extracts necessary font information from a font-declaration
            element.
            """
        for fontFace in fontDecl.getElementsByTagName("style:font-face") :
            if fontFace.getAttribute("style:font-pitch") == "fixed" :
                self.fixedFonts.append(fontFace.getAttribute("style:name"))
        


    def extractTextProperties (self, style, parent=None) :
        """ Extracts text properties from a style element. """
        
        textProps = TextProps()
        
        if parent :
            parentProp = self.textStyles.get(parent, None)
            if parentProp :
                textProp = parentProp
            
        textPropEl = style.getElementsByTagName("style:text-properties")
        if not textPropEl : return textProps
        
        textPropEl = textPropEl[0]

        italic = textPropEl.getAttribute("fo:font-style")
        bold = textPropEl.getAttribute("fo:font-weight")

        textProps.setItalic(italic)
        textProps.setBold(bold)

        if textPropEl.getAttribute("style:font-name") in self.fixedFonts :
            textProps.setFixed(True)

        return textProps

    def extractParagraphProperties (self, style, parent=None) :
        """ Extracts paragraph properties from a style element. """

        paraProps = ParagraphProps()

        name = style.getAttribute("style:name")

        if name.startswith("Heading_20_") :
            level = name[11:]
            try :
                level = int(level)
                paraProps.setHeading(level)
            except :
                level = 0

        if name == "Title" :
            paraProps.setTitle(True)
        
        paraPropEl = style.getElementsByTagName("style:paragraph-properties")
        if paraPropEl :
            paraPropEl = paraPropEl[0]
            leftMargin = paraPropEl.getAttribute("fo:margin-left")
            if leftMargin :
                try :
                    leftMargin = float(leftMargin[:-2])
                    if leftMargin > 0.01 :
                        paraProps.setIndented(True)
                except :
                    pass

        textProps = self.extractTextProperties(style)
        if textProps.fixed :
            paraProps.setCode(True)

        return paraProps
    

    def processStyles(self, styleElements) :
        """ Runs through "style" elements extracting necessary information.
            """

        for style in styleElements :

            name = style.getAttribute("style:name")

            if name == "Standard" : continue

            family = style.getAttribute("style:family")
            parent = style.getAttribute("style:parent-style-name")

            if family == "text" : 
                self.textStyles[name] = self.extractTextProperties(style,
                                                                   parent)

            elif family == "paragraph":
                self.paragraphStyles[name] = (
                                 self.extractParagraphProperties(style,
                                                                 parent))
    def processListStyles (self, listStyleElements) :

        for style in listStyleElements :
            name = style.getAttribute("style:name")

            prop = ListProperties()
            if style.childNodes :
                if ( style.childNodes[0].tagName
                     == "text:list-level-style-number" ) :
                    prop.setOrdered(True)

            self.listStyles[name] = prop
        

    def load(self, filepath) :
        """ Loads an ODT file. """
        
        zip = zipfile.ZipFile(filepath)

        styles_doc = xml.dom.minidom.parseString(zip.read("styles.xml"))
        self.processFontDeclarations(styles_doc.getElementsByTagName(
            "office:font-face-decls")[0])
        self.processStyles(styles_doc.getElementsByTagName("style:style"))
        self.processListStyles(styles_doc.getElementsByTagName(
            "text:list-style"))
        
        self.content = xml.dom.minidom.parseString(zip.read("content.xml"))
        self.processFontDeclarations(self.content.getElementsByTagName(
            "office:font-face-decls")[0])
        self.processStyles(self.content.getElementsByTagName("style:style"))
        self.processListStyles(self.content.getElementsByTagName(
            "text:list-style"))

    def compressCodeBlocks(self, text) :
        """ Removes extra blank lines from code blocks. """

        lines = text.split("\n")
        buffer = ""
        numLines = len(lines)
        for i in range(numLines) :
            
            if (lines[i].strip() or i == numLines-1  or i == 0 or
                not ( lines[i-1].startswith("    ")
                      and lines[i+1].startswith("    ") ) ):
                buffer += "\n" + lines[i]

        return buffer



    def listToString (self, listElement) :

        buffer = ""

        styleName = listElement.getAttribute("text:style-name")
        props = self.listStyles.get(styleName, ListProperties())

        
            
        i = 0
        for item in listElement.childNodes :
            i += 1
            if props.ordered :
                number = str(i)
                number = number + "." + " "*(2-len(number))
                buffer += number + self.paragraphToString(item.childNodes[0],
                                                        indent=3)
            else :
                buffer += "* " + self.paragraphToString(item.childNodes[0],
                                                        indent=2)
            buffer += "\n\n"
            
        return buffer

    def toString (self) :
        """ Converts the document to a string. """
        body = self.content.getElementsByTagName("office:body")[0]
        text = self.content.getElementsByTagName("office:text")[0]

        buffer = u""


        paragraphs = [el for el in text.childNodes
                      if el.tagName in ["text:p", "text:h",
                                        "text:list"]]

        for paragraph in paragraphs :
            if paragraph.tagName == "text:list" :
                text = self.listToString(paragraph)
            else :
                text = self.paragraphToString(paragraph)
            if text :
                buffer += text + "\n\n"

        if self.footnotes :

            buffer += "--------\n\n"
            for cite, body in self.footnotes :
                buffer += "[^%s]: %s\n\n" % (cite, body)


        return self.compressCodeBlocks(buffer)


    def textToString(self, element) :

        buffer = u""

        for node in element.childNodes :

            if node.nodeType == xml.dom.Node.TEXT_NODE :
                buffer += node.nodeValue

            elif node.nodeType == xml.dom.Node.ELEMENT_NODE :
                tag = node.tagName

                if tag == "text:span" :

                    text = self.textToString(node) 

                    if not text.strip() :
                        return ""  # don't apply styles to white space

                    styleName = node.getAttribute("text:style-name")
                    style = self.textStyles.get(styleName, None)

                    #print styleName, str(style)

                    if style.fixed :
                        buffer += "`" + text + "`"
                        continue
                    
                    if style :
                        if style.italic and style.bold :
                            mark = "***"
                        elif style.italic :
                            mark = "_"
                        elif style.bold :
                            mark = "**"
                        else :
                            mark = ""
                    else :
                        mark = "<" + styleName + ">"

                    buffer += "%s%s%s" % (mark, text, mark)
                    
                elif tag == "text:note" :
                    cite = (node.getElementsByTagName("text:note-citation")[0]
                                .childNodes[0].nodeValue)
                               
                    body = (node.getElementsByTagName("text:note-body")[0]
                                .childNodes[0])

                    self.footnotes.append((cite, self.textToString(body)))

                    buffer += "[^%s]" % cite

                elif tag in IGNORED_TAGS :
                    pass

                elif tag == "text:s" :
                    try :
                        num = int(node.getAttribute("text:c"))
                        buffer += " "*num
                    except :
                        buffer += " "

                elif tag == "text:tab" :
                    buffer += "    "


                elif tag == "text:a" :

                    text = self.textToString(node)
                    link = node.getAttribute("xlink:href")
                    buffer += "[%s](%s)" % (text, link)
                    
                else :
                    buffer += " {" + tag + "} "

        return buffer

    def paragraphToString(self, paragraph, indent = 0) :


        style_name = paragraph.getAttribute("text:style-name")
        paraProps = self.paragraphStyles.get(style_name) #, None)
        text = self.textToString(paragraph)

        #print style_name

        if paraProps and not paraProps.code :
            text = text.strip()

        if paraProps.title :
            self.hasTitle = 1
            return text + "\n" + ("=" * len(text))

        if paraProps.headingLevel :

            level = paraProps.headingLevel
            if self.hasTitle : level += 1

            if level == 1 :
                return text + "\n" + ("=" * len(text))
            elif level == 2 :
                return text + "\n" + ("-" * len(text))
            else :
                return "#" * level + " " + text

        elif paraProps.code :
            lines = ["    %s" % line for line in text.split("\n")]
            return "\n".join(lines)

        if paraProps.indented :
            return self.wrapParagraph(text, indent = indent, blockquote = True)

        else :
            return self.wrapParagraph(text, indent = indent)
        

    def wrapParagraph(self, text, indent = 0, blockquote=False) :

        counter = 0
        buffer = ""
        LIMIT = 50

        if blockquote :
            buffer += "> "
        
        for token in text.split() :

            if counter > LIMIT - indent :
                buffer += "\n" + " "*indent
                if blockquote :
                    buffer += "> "
                counter = 0

            buffer += token + " "
            counter += len(token)

        return buffer
        


if __name__ == "__main__" :


    odt = OpenDocumentTextFile(sys.argv[1])

    #print odt.fixedFonts

    #sys.exit(0)
    #out = open("out.txt", "wb")

    unicode = odt.toString()
    out_utf8 = unicode.encode("utf-8")

    sys.stdout.write(out_utf8)

    #out.write(

########NEW FILE########
__FILENAME__ = models
import datetime, copy, xmlrpclib, thread, time
from django.db import models
from django.core.cache import cache
from django.contrib.sitemaps import ping_google
from django.contrib.sites.models import Site
from django.dispatch import Signal
from django.db.models import signals
from django.core.mail import mail_admins
from lifeflow.text_filters import entry_markup


class Author(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(
        help_text="Automatically built from author's name.",
        )
    link = models.CharField(
        max_length=200,
        help_text="Link to author's website.")
    bio = models.TextField(
        blank=True, null=True,
        help_text="Bio of author, written in markdown format."
        )
    picture = models.FileField(
        upload_to="lifeflow/author", blank=True, null=True,
        help_text="Picture of author. For best visual appearance should be relatively small (200px by 200px or so)."
        )
    use_markdown = models.BooleanField(
        default=True,
        help_text="If true body is filtered using MarkDown, otherwise html is expected.",
        )

    class Meta:
        ordering = ('id',)

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return u"/author/%s/" % self.slug

    def latest(self, qty=10):
        return self.entry_set.all().filter(**{'pub_date__lte': datetime.datetime.now()})[:qty]
    
    def name_with_link(self):
        return u'<a href="%s">%s</a>' % (self.get_absolute_url(), self.name)


class Comment(models.Model):
    entry = models.ForeignKey('Entry')
    parent = models.ForeignKey('Comment', blank=True, null=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    email = models.CharField(max_length=100, blank=True, null=True)
    webpage = models.CharField(max_length=100, blank=True, null=True)
    body = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    html = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ('-date',)

    def save(self):
        if self.name == u"name" or self.name == u"":
            self.name = u"anonymous"
        if self.webpage == u"http://webpage" or self.webpage == u"http://":
            # better to check for valid URL
            self.webpage = None
        if self.email == u"email":
            # better to check for valid email address
            self.email = None

        title = self.entry.title
        subject = u"[Comment] %s on %s" % (self.name, self.entry.title)
        body = u"Comment by %s [%s][%s] on %s\n\n%s" % (self.name, self.email, self.webpage, title, self.html) 
        mail_admins(subject, body, fail_silently=True)
        super(Comment,self).save()

    def get_absolute_url(self):
        return u"%s#comment_%s" % (self.entry.get_absolute_url(), self.pk)

    def __unicode__(self):
        name = self.name or "Unnamed Poster"
        title = self.entry.title or "Unnamed Entry"
        return u": ".join((name, title))


class Draft(models.Model):
    title = models.CharField(max_length=200, blank=True, null=True)
    slug = models.SlugField(unique_for_date='pub_date',
                            blank=True, null=True)
    summary = models.TextField(blank=True, null=True)
    body = models.TextField(blank=True, null=True)
    pub_date = models.DateTimeField(blank=True, null=True)
    edited = models.BooleanField(default=False)
    use_markdown = models.BooleanField(default=True)
    is_translation = models.BooleanField(default=False)
    send_ping = models.BooleanField(default=False)
    allow_comments = models.BooleanField(default=True)
    flows = models.ManyToManyField('Flow', blank=True, null=True)
    tags = models.ManyToManyField('Tag', blank=True, null=True)
    series = models.ManyToManyField('Series', blank=True, null=True)
    authors = models.ManyToManyField('Author', blank=True, null=True)

    def __unicode__(self):
        if self.title:
            return self.title
        else:
            return "Untitled Draft"


class CurrentEntryManager(models.Manager):
    def get_query_set(self):
        return super(CurrentEntryManager, self).get_query_set().filter(**{'pub_date__lte': datetime.datetime.now()}).filter(**{'is_translation':False})


class Entry(models.Model):
    title = models.CharField(
        max_length=200,
        help_text='Name of this entry.'
        )
    slug = models.SlugField(
        unique_for_date='pub_date',
        help_text='Automatically built from the title.'
        )
    summary = models.TextField(help_text="One paragraph. Don't add &lt;p&gt; tag.")
    body = models.TextField(
        help_text='Use <a href="http://daringfireball.net/projects/markdown/syntax">Markdown-syntax</a>'
        )
    body_html = models.TextField(blank=True, null=True)
    pub_date = models.DateTimeField(
        help_text='If the date and time combination is in the future, the entry will not be visible until after that moment has passed.'
        )
    use_markdown = models.BooleanField(
        default=True,
        help_text="If true body is filtered using MarkDown++, otherwise no filtering is applied.",
        )
    is_translation = models.BooleanField(
        default=False,
        help_text="Only used to add articles to the translation feed.",
        )
    send_ping = models.BooleanField(
        default=False,
        help_text="If true will ping Google and any sites you have specified on saves."
        )
    allow_comments = models.BooleanField(
        default=True,
        help_text="If true users may add comments on this entry.",
        )
    flows = models.ManyToManyField(
        'Flow', blank=True, null=True,
        help_text="Determine which pages and feeds to show entry on.",
        )
    tags = models.ManyToManyField(
        'Tag', blank=True, null=True,
        help_text="Select tags to associate with this entry.",
        )
    series = models.ManyToManyField(
        'Series', blank=True, null=True,
        help_text='Used to associated groups of entries together under one theme.',
        )
    resources = models.ManyToManyField(
        'Resource', blank=True, null=True,
        help_text='Files or images used in entries. MarkDown links are automatically generated.',
        )
    authors = models.ManyToManyField(
        'Author', blank=True, null=True,
        help_text='The authors associated with this entry.',
        )
    # main manager, allows access to all entries, required primarily for admin functionality
    objects = models.Manager()
    # current manager, does not allow access entries published to future dates
    current = CurrentEntryManager()

    class Meta:
        ordering = ('-pub_date',)
        get_latest_by = 'pub_date'
        verbose_name_plural = "entries"

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return u"/entry/%s/%s/" % (
            self.pub_date.strftime("%Y/%b/%d").lower(),
            self.slug,
            )

    def save(self):
        if self.use_markdown:
            self.body_html = entry_markup(self.body, self)
        else:
            self.body_html = self.body
        if self.send_ping is True: self.ping()
        super(Entry,self).save()

    def ping(self):
        # ping all sites to ping (Ping-O-Matic, etc)
        for site in SiteToNotify.objects.all():
            site.ping()

        # inform Google sitemap has changed
        try:
            ping_google()
        except Exception:
            pass
    
    def get_next_article(self):
        next =  Entry.current.filter(**{'pub_date__gt': self.pub_date}).order_by('pub_date')
        try:
            return next[0]
        except IndexError:
            return None

    def get_previous_article(self):
        previous =  Entry.current.filter(**{'pub_date__lt': self.pub_date}).order_by('-pub_date')
        try:
            return previous[0]
        except IndexError:
            return None

    def get_random_entries(self):
        return Entry.current.order_by('?')[:3]

    def get_recent_comments(self, qty=3):
        return Comment.objects.all().filter(entry=self)[:qty]

    def organize_comments(self):
        """
        Used to create a list of threaded comments. 

        This is a bit tricky since we only know the parent for
        each comment, as opposed to knowing each parent's children.
        """
        def build_relations(dict, comment=None, depth=-1):
            if comment is None: id = None
            else: id = comment.id
            try:
                children = dict[id]
                children.reverse()
                return [(comment, depth), [build_relations(dict, x, depth+1) for x in children]]
            except:
                return (comment, depth)

        def flatten(l, ltypes=(list, tuple)):
            i = 0
            while i < len(l):
                while isinstance(l[i], ltypes):
                    if not l[i]:
                        l.pop(i)
                        if not len(l):
                            break
                    else:
                        l[i:i+1] = list(l[i])
                i += 1
            return l

        def group(seq, length):
            """
            Taken from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/496784
            """
            return [seq[i:i+length] for i in range(0, len(seq), length)]

        dict = {None:[]}
        all = Comment.objects.select_related().filter(entry=self)
        for comment in all:
            if comment.parent: id = comment.parent.id
            else: id = None
            try:
                dict[id].append(comment)
            except KeyError:
                dict[id] = [comment]
        relations = build_relations(dict)
        # If there are no comments, return None
        if len(relations) == 1:
            return None
        # Otherwise, throw away the None node, flatten
        # the returned list, and regroup the list into
        # 2-lists that look like
        #   [CommentInstance, 4]
        # where CommentInstance is an instance of the
        # Comment class, and 4 is the depth of the
        # comment in the layering
        else:
            return group(flatten(relations[1]), 2)


class Flow(models.Model):
    """
    A genre of entries. Like things about Cooking, or Japan.
    Broader than a tag, and gets its own nav link and is available
    at /slug/ instead of /tags/slug/
    """
    title = models.CharField(max_length=100)
    slug = models.SlugField()

    def __unicode__(self):
        return self.title

    def latest(self, qty=None):
        if qty is None:
            return self.entry_set.all().filter(**{'pub_date__lte': datetime.datetime.now()}).filter(**{'is_translation':False})
        else:
            return self.entry_set.all().filter(**{'pub_date__lte': datetime.datetime.now()}).filter(**{'is_translation':False})[:qty]

    def get_absolute_url(self):
        return u"/%s/" % self.slug


class Language(models.Model):
    title = models.CharField(max_length=50)
    slug = models.SlugField()

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return u"/language/%s/" % self.slug

    def latest(self, qty=None):
        translations = self.translation_set.all().filter(**{'translated__pub_date__lte': datetime.datetime.now()})
        return [ x.translated for x in translations ]


class Project(models.Model):
    """
    A project of any kind. Think of it as a piece in a portfolio.
    """
    title = models.CharField(max_length=50)
    slug = models.SlugField(
        help_text='Automatically built from the title.'
        )
    summary = models.TextField(help_text="One paragraph. Don't add &lt;p&gt; tag.")
    body = models.TextField(
        help_text='Use <a href="http://daringfireball.net/projects/markdown/syntax">Markdown-syntax</a>')
    body_html = models.TextField(blank=True, null=True)
    use_markdown = models.BooleanField(default=True)
    language = models.CharField(
        max_length=50,
        help_text="The programming language the project is written in.",
        )
    license = models.CharField(
        max_length=50,
        help_text="The license under which the project is released.",
        )
    resources = models.ManyToManyField('Resource', blank=True, null=True)
    SIZE_CHOICES = (
        ('0', 'Script'),
        ('1', 'Small'),
        ('2', 'Medium'),
        ('3', 'Large'),
        )
    size = models.CharField(
        max_length=1, choices=SIZE_CHOICES,
        help_text="Used for deciding order projects will be displayed in.",
        )

    class Meta:
        ordering = ('-size',)

   
    def __unicode__(self):
        return self.title

    def size_string(self):
        if self.size == str(0): return "Script"
        if self.size == str(1): return "Small"
        elif self.size == str(2): return "Medium"
        elif self.size == str(3): return "Large"

    def get_absolute_url(self):
        return u"/projects/%s/" % self.slug

    def save(self):
        if self.use_markdown:
            self.body_html = entry_markup(self.body, self)
        else:
            self.body_html = self.body
        super(Project,self).save()


class Resource(models.Model):
    """
    A wrapper for files (image or otherwise, the model is unaware of the
    distinction) that are used in blog entries.
    """
    title = models.CharField(max_length=50)
    markdown_id = models.CharField(max_length=50)
    content = models.FileField(upload_to="lifeflow/resource")


    def get_relative_url(self):
        # figure out why I named this relative instead of absolute
        # because... it sure as hell isn't relative
        return self.content.url

    def __unicode__(self):
        return u"[%s] %s" % (self.markdown_id, self.title,)


class RecommendedSite(models.Model):
    """
    A site that is displayed under the 'Blogs-To-See' entry
    on each page of the website. Akin to entries in a blog roll
    on a WordPress blog.
    """
    title = models.CharField(max_length=50)
    url = models.URLField()


    def __unicode__(self):
        return u"%s ==> %s" % (self.title, self.url)


class Series(models.Model):
    """
    A series is a collection of Entry instances on the same theme.
    """
    title = models.CharField(max_length=200)
    slug= models.SlugField()

    class Meta:
        ordering = ('-id',)
        verbose_name_plural = "Series"


    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return u"/articles/%s/" % ( unicode(self.slug), )

    def latest(self, qty=10):
        return self.entry_set.all().filter(**{'pub_date__lte': datetime.datetime.now()})[:qty]

    def in_order(self):
        return self.entry_set.filter(**{'pub_date__lte': datetime.datetime.now()}).order_by('id')

    def num_articles(self):
        return self.entry_set.all().count()


class SiteToNotify(models.Model):
    """
    SiteToNotify instances are pinged by Entries where
    someEntry.ping_sites is True.

    Sites such as 'Ping-O-Matic' are easiest to use here.
    Manually creating the Ping-O-Matic instance looks
    something like this:

    stn = SiteToNotify(title="Ping-O-Matic",
                       url_to_ping="http://rpc.pingomatic.com/",
                       blog_title="My Blog's Title",
                       blog_url="http://www.myblog.com")
    stn.save()
    """
    title = models.CharField(max_length=100)
    url_to_ping = models.CharField(max_length=200)
    blog_title = models.CharField(max_length=100)
    blog_url = models.CharField(max_length=200)


    class Meta:
        verbose_name_plural = "Sites to Notify"


    def __unicode__(self):
        return self.title

    def ping(self):
        def do_ping():
            remote_server = xmlrpclib.Server(self.url_to_ping)
            remote_server.weblogUpdates.ping(self.blog_title, self.blog_url)
        thread.start_new_thread(do_ping, ())

class Tag(models.Model):
    "Tags are associated with Entry instances to describe their contents."
    title = models.CharField(max_length=50)
    slug = models.SlugField()

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return u"/tags/%s/" % self.slug

    def random(self):
        return self.entry_set.filter(**{'pub_date__lte': datetime.datetime.now()}).order_by('?')

    def latest(self, qty=None):
        if qty is None:
            return self.entry_set.all().filter(**{'pub_date__lte': datetime.datetime.now()})
        else:
            return self.entry_set.all().filter(**{'pub_date__lte': datetime.datetime.now()})[:qty]

    def get_max_tags(self):
        max = cache.get('lifeflow_tags_max')
        if max == None:
            tags = Tag.objects.all()
            max = 0
            for tag in tags:
                count = tag.entry_set.count()
                if count > max: max = count
            cache.set('lifeflow_tags_max', max)
        return max

    def tag_size(self):
        max = self.get_max_tags()
        count = self.entry_set.count()
        ratio = (count * 1.0) / max
        tag_name = "size"
        if ratio < .2: return tag_name + "1"
        elif ratio < .4: return tag_name + "2"
        elif ratio < .6: return tag_name + "3"
        elif ratio < .8: return tag_name + "4"
        else: return tag_name + "5"


class Translation(models.Model):
    """
    Link together two entries, where @translated is a translation of
    @original in the language @language.
    """
    language = models.ForeignKey('Language')
    original = models.ForeignKey('Entry')
    translated = models.ForeignKey('Entry', related_name="translated")
    

    def __unicode__(self):
        return u"Translation of %s into %s" % (self.original, self.language,)


    def get_link(self):
        url = self.translated.get_absolute_url()
        return u'<a href="%s">%s</a>' % (url, self.language,)

    def get_absolute_url(self):
        return self.translated.get_absolute_url()


def resave_object(sender, instance, signal, *args, **kwargs):
    """
    This is called to save objects a second time after required
    manyTomany relationships have been established.

    There must be a better way of handling this.
    """
    def do_save():
        time.sleep(3)
        try:
            instance.save()
        except:
            pass

    id = u"%s%s" % (unicode(instance), unicode(instance.id))
    try:
        should_resave = resave_hist[id]
    except KeyError:
        resave_hist[id] = True
        should_resave = True

    if should_resave is True:
        resave_hist[id] = False
        thread.start_new_thread(do_save, ())
    else:
        resave_hist[id] = True


resave_hist = {}
signals.post_save.connect(resave_object, sender=Project)
signals.post_save.connect(resave_object, sender=Entry)

########NEW FILE########
__FILENAME__ = search
import solango
from lifeflow.models import Comment, Entry

class EntryDocument(solango.SearchDocument):
    date = solango.fields.DateField()
    summary = solango.fields.TextField(copy=True)
    title = solango.fields.CharField(copy=True)
    tags = solango.fields.CharField(copy=True)
    content = solango.fields.TextField(copy=True)

    def transform_summary(self, instance):
        return instance.summary

    def transform_tags(self, instance):
        tags = list(instance.tags.all())
        texts = [ tag.title for tag in tags ]
        return ",".join(texts)
    
    def transform_date(self, instance):
        return instance.pub_date

    def transform_content(self, instance):
        return instance.body

solango.register(Entry, EntryDocument)

########NEW FILE########
__FILENAME__ = sitemaps
from django.contrib.sitemaps import Sitemap
from lifeflow.models import Project, Entry

class ProjectSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.9
    
    def items(self):
        return Project.objects.all()

########NEW FILE########
__FILENAME__ = lifeflow
from django import template
register = template.Library()

def boundary(value, arg):
    """Defines a boundary for an integer. If the value of the integer
    is higher than the boundary, then the boundary is returned instead.

    Example:  {{ comment.depth|:"4" }} will return 4 if the value of
    comment.depth is 4 or higher, but will return 1, 2 or 3 if the
    value of comment.depth is 1, 2 or 3 respectively.
    """
    value = int(value)
    boundary = int(arg)
    if value > boundary:
        return boundary
    else:
        return value

register.filter('boundary', boundary)

def nearby(lst, obj, count=5):
    lst = list(lst)
    l = len(lst)
    try:
        pos = lst.index(obj)
    except ValueError:
        pos = 0
    dist = count / 2
    if pos <= dist:
        return lst[:count]
    if pos >= l - dist:
        return lst[l-count:]
    else:
        return lst[pos-dist:pos+dist+1]

register.filter('nearby', nearby)

def human(lst, field):
    lst = list(lst)
    lst.sort(lambda a,b : cmp(getattr(a,field).lower(),
                              getattr(b,field).lower()))
    return lst

register.filter('human', human)

########NEW FILE########
__FILENAME__ = tests
import unittest
from django.test.client import Client
from lifeflow.models import *
import datetime
import pygments.lexers as lexers



#response = self.client.get('/api/case/retrieve/', {})
#self.assertEquals(response.content, 'etc')

class commentTest(unittest.TestCase):
    def setUp(self):
        self.client = Client()

    def test_organize_comments(self):
        "models.py: test organize_comments method for Entry"
        e = Entry(title="My Entry",
                  pub_date=datetime.datetime.now(),
                  summary="A summary",
                  body="Some text")
        e.save()
        c1 = Comment(entry=e, body="Some comment one.")
        c1.save()
        self.assertEquals([[c1, 0]], e.organize_comments())
        c2 = Comment(entry=e, name="Two", body="Some comment two.")
        c2.save()
        self.assertEquals([[c2,0],[c1,0]], e.organize_comments())
        c3 = Comment(entry=e, name="Three", parent=c1, body="Three")
        c3.save()
        self.assertEquals([[c2, 0], [c1,0], [c3,1]],
                          e.organize_comments())
        c4 = Comment(entry=e, name="Four", parent=c2, body="Four")
        c4.save()
        self.assertEquals([[c2,0], [c4, 1], [c1,0], [c3,1]],
                          e.organize_comments())


class codeMarkupTest(unittest.TestCase):
    def test_markup(self):
        "markup/markdown.py: test markdown"
        txt = "this is some text"
        expected = u"<p>this is some text\n</p>"
        rendered = dbc_markup(txt).strip("\n")
        self.assertEqual(expected, rendered)
        
    def test_code_markup(self):
        "markup/code.py: test code markup"

        txt = u"    some code in a code block\n    is nice\n"
        expected = u'<pre><code>some code in a code block\nis nice\n</code></pre>'
        self.assertEqual(expected, dbc_markup(txt))

        txt = u"<pre>this is some stuff\nthat I am concerned about</pre>"
        self.assertEqual(txt, dbc_markup(txt))

        txt = u"@@ python\nx = 10 * 5\n@@\n"
        expected = u'<div class="highlight"><pre><span class="n">x</span> <span class="o">=</span> <span class="mi">10</span> <span class="o">*</span> <span class="mi">5</span>\n</pre></div>'
        self.assertEqual(expected, dbc_markup(txt))


        txt = u"@@ python\ndef test(a,b):\n    return x + y\n@@\n"
        expected = u'<div class="highlight"><pre><span class="k">def</span> <span class="nf">test</span><span class="p">(</span><span class="n">a</span><span class="p">,</span><span class="n">b</span><span class="p">):</span>\n    <span class="k">return</span> <span class="n">x</span> <span class="o">+</span> <span class="n">y</span>\n</pre></div>'
        self.assertEqual(expected, dbc_markup(txt))

        


    def test_using_non_existant_language(self):
        "markup/code.py: test improperly formed code markup"
        cases = (
            u"@@\ndef test(a,b):\n@@\n",
            u"@@ fake-language\n(+ 1 2 3)\n@@\n",
            )
        for case in cases:     
            self.assertRaises(lexers.ClassNotFound, 
                              lambda : dbc_markup(case))
         

    def test_lfmu(self):
        "markup/lifeflowmarkdown.py: test lifeflow markup"
        e = Entry(title="My Entry",
                  pub_date=datetime.datetime.now(),
                  summary="A summary",
                  body="Some text")
        e.save()

        a = Author(name="Will Larson",
                   slug="will-larson",
                   link="a")
        a.save()

        e2= Entry(title="My Entry",
                  pub_date=datetime.datetime.now(),
                  summary="A summary",
                  body="Some text",
                  )
        e2.save()
        e2.authors.add(a)
        e2.save()

        t = Tag(title="LifeFlow", slug="lifeflow")
        t.save()

        c1 = Comment(entry=e, body="Some comment one.")
        c1.save()

        p = Project(title="Lifeflow",
                    slug="lifeflow",
                  summary="A summary",
                  body="Some text")
        p.save()

        
        self.assertEqual(dbc_markup("[trying out a tag][tag lifeflow]", e),
                         u'<p><a href="/tags/lifeflow/">trying out a tag</a>\n</p>')
        self.assertEqual(dbc_markup("[and the author][author]", e),
                         u'<p><a href="/author/">and the author</a>\n</p>')
        self.assertEqual(dbc_markup("[about will][author]", e2),
                      u'<p><a href="/author/will-larson/">about will</a>\n</p>')
        #self.assertEqual(dbc_markup("[the first comment][comment 1]", e),
        #                 u'<p><a href="/entry/2008/jan/12//#comment_1">the first comment</a>\n</p>')
        self.assertEqual(dbc_markup("[lf proj][project lifeflow]", e),
                         u'<p><a href="/projects/lifeflow/">lf proj</a>\n</p>')

        # test for [file name]
        # test for [f name]

########NEW FILE########
__FILENAME__ = text_filters
"""
    This file contains filters which are used for pre and post
    processing various kinds of text within LifeFlow.

    Which values are applied is controlled by a number of global
    variables within the project's settings.py file. These vars
    are:

    LIFEFLOW_ENTRY_FILTERS
    LIFEFLOW_COMMENT_FILTERS

    If you wish to add your own filters, you don't
    have to add them to this file, they can exist anywhere, and
    simply import them into the settings.py file and add them
    to the appropriate global variable.

    The API for these processing functions is very simple:
    they accept two parameters, a string to process,
    and optionally a related model.
"""

from django.conf import settings
from lifeflow.markdown.markdown import Markdown
from lifeflow.markdown import mdx_lifeflow
from lifeflow.markdown import mdx_code
from lifeflow.markdown import mdx_footnotes
from lifeflow.markdown import mdx_foreign_formats


def convert_string(str):
    if LOCALS.has_key(str):
        return LOCALS[str]
    else:
        return str

def comment_markup(txt,obj=None):
    filters = getattr(settings,'LIFEFLOW_COMMENT_FILTERS', DEFAULT_COMMENT_FILTERS)
    filters = [convert_string(filter) for filter in filters]
    for filter in filters:
        txt = filter(txt)
    return txt

def entry_markup(txt,obj=None):
    filters = getattr(settings,'LIFEFLOW_ENTRY_FILTERS', DEFAULT_ENTRY_FILTERS)
    for filter in filters:
        txt = filter(txt)
    return txt


def comment_markdown(txt,obj=None):
    exts = (mdx_code,)
    md = Markdown(txt,extensions=exts,safe_mode="escape")
    return md.convert()


def entry_markdown(txt,obj=None):
    exts = (mdx_code, mdx_footnotes,mdx_foreign_formats, mdx_lifeflow)
    md = Markdown(txt,extensions=exts,extension_configs={'lifeflow':obj})
    return md.convert()
    
LOCALS = locals()
DEFAULT_COMMENT_FILTERS = (comment_markdown,)
DEFAULT_ENTRY_FILTERS = (entry_markdown,)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from lifeflow.feeds import *
from lifeflow.models import *
from lifeflow.sitemaps import ProjectSitemap
from django.contrib.sitemaps import GenericSitemap
from django.views.decorators.cache import cache_page
from django.contrib.syndication.views import feed

# Cache
def cache(type):
    return cache_page(type, 60*30)


handler500 = 'lifeflow.views.server_error'

flows = Flow.objects.all()
projects = Project.objects.all()
tags = Tag.objects.all()
languages = Language.objects.all()
authors = Author.objects.all()

feeds = {
    'author': AuthorFeed,
    'all' : AllFeed,
    'flow' : FlowFeed,
    'tag' : TagFeed,
    'series' : SeriesFeed,
    'translations' : TranslationFeed,
    'projects' : ProjectFeed,
    'comment' : CommentFeed,
    'entry_comment' : EntryCommentFeed,
    'language' : LanguageFeed,
}

all_dict = {
    'queryset' : Entry.objects.all(),
    'date_field' : 'pub_date',
}

sitemaps = {
    'projects' : ProjectSitemap,
    'entries' : GenericSitemap(all_dict, priority=0.6),
}

urlpatterns = patterns(
    '',
    url(r'^$', 'lifeflow.views.front'),
    url(r'^sitemap.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': sitemaps}),

    # comments
    url(r'^comments/create/$', 'lifeflow.views.comments'),
    url(r'^comments/create/(?P<entry_id>\d+)/$', 'lifeflow.views.comments'),
    url(r'^comments/create/(?P<entry_id>\d+)/(?P<parent_id>\d+)/$', 'lifeflow.views.comments'),

    # feeds and rss views
    url(r'^feeds/(?P<url>.*)/$', cache(feed), {'feed_dict': feeds}),
    url(r'^meta/rss/$', 'lifeflow.views.rss'),

    # date based generic views
    url(r'^entry/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\w{1,2})/(?P<slug>[-\w]+)/$', 'django.views.generic.date_based.object_detail', dict(all_dict, slug_field='slug')),
    url(r'^entry/(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\w{1,2})/$', 'django.views.generic.date_based.archive_day',   all_dict),
    url(r'^entry/(?P<year>\d{4})/(?P<month>[a-z]{3})/$', 'django.views.generic.date_based.archive_month', all_dict),
    url(r'^entry/(?P<year>\d{4})/$', 'django.views.generic.date_based.archive_year',  all_dict),
    url(r'^entry/$', 'django.views.generic.date_based.archive_index', all_dict),

    # tag generic views
    url(r'^tags/$', 'django.views.generic.list_detail.object_list', dict(queryset=tags)),
    url(r'^tags/(?P<slug>[-\w]+)/$', 'django.views.generic.list_detail.object_detail', dict(queryset=tags, slug_field='slug')),

    # language generic views
    url(r'^language/$', 'django.views.generic.list_detail.object_list', dict(queryset=languages)),
    url(r'^language/(?P<slug>[-\w]+)/$', 'django.views.generic.list_detail.object_detail', dict(queryset=languages, slug_field='slug')),

    # author generic views
    url(r'^author/(?P<slug>[-\w]+)/$', 'django.views.generic.list_detail.object_detail', dict(queryset=authors, slug_field='slug')),
    url(r'^author/$', 'django.views.generic.list_detail.object_list', dict(queryset=authors)),

    # articles views (custom view)
    url(r'^articles/$', 'lifeflow.views.articles'),

    # projects views
    url(r'^projects/$', 'django.views.generic.list_detail.object_list', dict(queryset=projects)),
    url(r'^projects/(?P<slug>[-\w]+)/$', 'django.views.generic.list_detail.object_detail', dict(queryset=projects, slug_field='slug')),

    # editor
    url(r'^editor/', include('lifeflow.editor.urls')),

    # flows
    url(r'^(?P<slug>[-\w]+)/$', 'lifeflow.views.flow'),
)

########NEW FILE########
__FILENAME__ = views
"""
Views.py

Author: Will Larson
Contact: lethain@gmail.com


Contains one custom view for displaying articles.
Mostly necessary to presort the articles in order
of descending size.

"""
import datetime, time, random, cgi, md5
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.http import Http404, HttpResponseRedirect
from django.conf import settings
from django.core.paginator import QuerySetPaginator
from lifeflow.models import Series, Flow, Entry, Comment
from lifeflow.forms import CommentForm
from django.core.cache import cache
from django.http import HttpRequest
from django.utils.cache import get_cache_key

def expire_page(path):
    'http://www.djangosnippets.org/snippets/936/'
    request = HttpRequest()
    request.path = path
    key = get_cache_key(request)
    if cache.has_key(key):
        cache.delete(key)


def server_error(request):
    return render_to_response('500.html',{},RequestContext(request,{}))


def articles(request):       
    object_list = Series.objects.all()
    return render_to_response('lifeflow/articles.html', {'object_list' : object_list},RequestContext(request, {}))


def comments(request, entry_id=None, parent_id=None):
    def make_identifier(id, time):
        secret = getattr(settings, 'SECRET_KEY')
        time = time[:-4]
        data = "%s%s%s%s" % ("lifeflow", id, time, secret)
        return md5.md5(data).hexdigest()

    # if an entry ID has been posted, use that
    if request.POST.has_key('entry_id'):
        id = int(request.POST['entry_id'])
    # otherwise use the parameter
    elif entry_id is None:
        return render_to_response('lifeflow/invalid_comment.html',{},RequestContext(request, {}))
    else:
        id = int(entry_id)
    # TODO: validate ID, throw 500 otherwise
    entry = Entry.objects.get(pk=id)
    
    if request.POST.has_key('parent_id') and request.POST['parent_id'] != u"":
        parent_id = int(request.POST['parent_id'])
        parent = Comment.objects.get(pk=parent_id)
    elif parent_id is None:
        parent = None
    else:
        parent_id = int(parent_id)
        parent = Comment.objects.get(pk=parent_id)

    # add an identifier to the post, part of the
    # anti-spam implementation
    if request.POST.has_key('identifier') is False:
        now = unicode(time.time()).split('.')[0]
        identifier = make_identifier(id, now)
    # or make a new identifier
    else:
        identifier = request.POST['identifier']
        now = request.POST['time']
        
    form = CommentForm(request.POST)
    form.is_valid()

    # Initial submission from entry_detail.html
    if request.POST.has_key('submit'):
        for i in xrange(5,8):
            name = u"honey%s" % i 
            value = request.POST[name]
            if value != u"":
                raise Http404
        if time.time() - int(now) > 3600:
            raise Http404
        if identifier != make_identifier(id, now):
            raise Http404

        name = form.cleaned_data['name']
        email = form.cleaned_data['email']
        webpage = form.cleaned_data['webpage']
        html = form.cleaned_data['html']
        body = form.cleaned_data['body']
        c = Comment(entry=entry,parent=parent,name=name,email=email,
                    webpage=webpage,body=body,html=html)
        c.save()
        url = u"%s#comment_%s" % (entry.get_absolute_url(), c.pk)
        expire_page(entry.get_absolute_url())
        return HttpResponseRedirect(url)

    return render_to_response(
        'lifeflow/comment.html',
        {'object':entry,'parent':parent,'identifier':identifier,'time':now,'form':form},
        RequestContext(request, {}))


def flow(request, slug):
    try:
        flow = Flow.objects.get(slug=slug)
    except Flow.DoesNotExist:
        raise Http404
    try:
        page = int(request.GET["page"])
    except:
        page = 1
    page = QuerySetPaginator(Flow.objects.get(slug=slug).latest(), 5).page(page)
    return render_to_response('lifeflow/flow_detail.html', 
                              {'object' : flow, 'page' : page,},
                              RequestContext(request, {}))


def front(request):
    try:
        page = int(request.GET["page"])
    except:
        page = 1
    page = QuerySetPaginator(Entry.current.all(), 5).page(page)
    return render_to_response('lifeflow/front.html', {'page':page}, RequestContext(request, {}))


def rss(request):
    flows = Flow.objects.all()
    return render_to_response('lifeflow/meta_rss.html', {'flows' : flows }, RequestContext(request, {}))

########NEW FILE########
