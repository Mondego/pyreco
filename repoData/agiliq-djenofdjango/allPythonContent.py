__FILENAME__ = forms_1d155f
from django import forms

from models import Post, Comment

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        exclude = ['author', 'slug']

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        exclude = ['post']


########NEW FILE########
__FILENAME__ = models_5db3e5f
from django.db import models
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify

# Create your models here.

class PublishedArticlesManager(models.Manager):
    
    def get_query_set(self):
        return super(PublishedArticlesManager, self).get_query_set().filter(is_published=True)

class Article(models.Model):
    """Represents a wiki article"""
    
    title = models.CharField(max_length=100)
    slug = models.SlugField(max_length=50, unique=True)
    text = models.TextField(help_text="Formatted using ReST")
    author = models.ForeignKey(User)
    is_published = models.BooleanField(default=False, verbose_name="Publish?")
    created_on = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()
    published = PublishedArticlesManager()

    def __unicode__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super(Article, self).save(*args, **kwargs)

    @models.permalink
    def get_absolute_url(self):
        return ('wiki_article_detail', (), { 'slug': self.slug })

class Edit(models.Model):
    """Stores an edit session"""
    
    article = models.ForeignKey(Article)
    editor = models.ForeignKey(User)
    edited_on = models.DateTimeField(auto_now_add=True)
    summary = models.CharField(max_length=100)

    class Meta:
        ordering = ['-edited_on']

    def __unicode__(self):
        return "%s - %s - %s" %(self.summary, self.editor, self.edited_on)
    
    @models.permalink
    def get_absolute_url(self):
        return ('wiki_edit_detail', self.id)


########NEW FILE########
__FILENAME__ = models_a9ffd8
from django.db import models

# Create your models here.


class Paste(models.Model):
    text = models.TextField()
    name = models.CharField(max_length=40, null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.name or str(self.id)


########NEW FILE########
__FILENAME__ = models_c0c759
from django.db import models

# Create your models here.


class Paste(models.Model):
    text = models.TextField()
    name = models.CharField(max_length=40, null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.name or str(self.id)

    @models.permalink
    def get_absolute_url(self):
        return ('pastebin_paste_detail', [self.id])


########NEW FILE########
__FILENAME__ = models_c95309
from django.db import models
from django.template.defaultfilters import slugify

from django.contrib.auth.models import User

# Create your models here.

class Post(models.Model):
    title = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    text = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(User)

    def __unicode__(self):
        return self.title

    @models.permalink
    def get_absolute_url(self):
        return ('blog_post_detail', (), 
                {
                    'slug' :self.slug,
                })

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super(Post, self).save(*args, **kwargs)

class Comment(models.Model):
    name = models.CharField(max_length=42)
    email = models.EmailField(max_length=75)
    website = models.URLField(max_length=200, null=True, blank=True)
    text = models.TextField()
    post = models.ForeignKey(Post)
    created_on = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return self.text


########NEW FILE########
__FILENAME__ = urls_087f567
from django.conf.urls.defaults import *

from models import Post

urlpatterns = patterns('',
    url(r'^post/(?P<slug>[-\w]+)$', 
        'blog.views.view_post',
        name='blog_post_detail'),
    url(r'^add/post$', 
        'blog.views.add_post', 
        name='blog_add_post'),
    url(r'^archive/month/(?P<year>\d+)/(?P<month>\w+)$',
        'django.views.generic.date_based.archive_month',
        {
            'queryset': Post.objects.all(), 
            'date_field': 'created_on',
        },
        name='blog_archive_month',
       ),
    url(r'^archive/week/(?P<year>\d+)/(?P<week>\d+)$',
        'django.views.generic.date_based.archive_week',
        {
            'queryset': Post.objects.all(), 
            'date_field': 'created_on',
        },
        name='blog_archive_week',
       ),
)


########NEW FILE########
__FILENAME__ = urls_17c506
from django.conf.urls.defaults import *
#from django.core.urlresolvers import reverse

from models import Paste

urlpatterns = patterns('',
    url(r'^$', 'django.views.generic.create_update.create_object', { 'model': Paste }, name='pastebin_paste_create'),
    url(r'^paste/edit/(?P<object_id>\d+)$', 'django.views.generic.create_update.update_object', { 'model': Paste }, name='pastebin_paste_edit'),
    url(r'^paste/delete/(?P<object_id>\d+)$', 'django.views.generic.create_update.delete_object', { 'model': Paste, 'post_delete_redirect': '/pastebin/pastes' }, name='pastebin_paste_delete'),
    url(r'^paste/(?P<object_id>\d+)$', 'django.views.generic.list_detail.object_detail', { 'queryset': Paste.objects.all() }, name='pastebin_paste_detail'),
    url(r'^pastes/$', 'django.views.generic.list_detail.object_list', { 'queryset': Paste.objects.all() }, name='pastebin_paste_list'),
)


########NEW FILE########
__FILENAME__ = urls_2bb5e33
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^djen_project/', include('djen_project.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^accounts/', include('registration.backends.default.urls')),
    (r'^admin/', include(admin.site.urls)),
    (r'^pastebin/', include('pastebin.urls')),
    (r'^blog/', include('blog.urls')),
)

########NEW FILE########
__FILENAME__ = urls_5013af
from django.conf.urls.defaults import *

from models import Paste

urlpatterns = patterns('',
    (r'^$', 'django.views.generic.create_update.create_object', { 'model': Paste }),
    url(r'^paste/(?P<object_id>\d+)$', 'django.views.generic.list_detail.object_detail', { 'queryset': Paste.objects.all() }, name='pastebin_paste_detail'),
)


########NEW FILE########
__FILENAME__ = urls_5db3e5f
from django.conf.urls.defaults import *

from models import Article

urlpatterns = patterns('',
    url(r'^$', 
        'django.views.generic.list_detail.object_list',
        {
            'queryset': Article.published.all(),
        },
        name='wiki_article_index'),
    url(r'^article/(?P<slug>[-\w]+)$', 
        'django.views.generic.list_detail.object_detail',
        {
            'queryset': Article.objects.all(),
        },
        name='wiki_article_detail'),
    url(r'^history/(?P<slug>[-\w]+)$',
        'wiki.views.article_history',
        name='wiki_article_history'),
    url(r'^add/article$',
        'wiki.views.add_article',
        name='wiki_article_add'),
    url(r'^edit/article/(?P<slug>[-\w]+)$',
        'wiki.views.edit_article',
        name='wiki_article_edit'),
)


########NEW FILE########
__FILENAME__ = urls_693145
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^djen_project/', include('djen_project.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^accounts/login/$', 'django.contrib.auth.views.login'),
    (r'^admin/', include(admin.site.urls)),
    (r'^pastebin/', include('pastebin.urls')),
    (r'^blog/', include('blog.urls')),
)

########NEW FILE########
__FILENAME__ = urls_749380
from django.conf.urls.defaults import *

from models import Paste

urlpatterns = patterns('',
    (r'$', 'django.views.generic.create_update.create_object', { 'model': Paste }),
)


########NEW FILE########
__FILENAME__ = urls_dee14b
from django.conf.urls.defaults import *

from models import Paste

urlpatterns = patterns('',
    (r'^$', 'django.views.generic.create_update.create_object', { 'model': Paste }),
    url(r'^paste/(?P<object_id>\d+)$', 'django.views.generic.list_detail.object_detail', { 'queryset': Paste.objects.all() }, name='pastebin_paste_detail'),
    url(r'^pastes/$', 'django.views.generic.list_detail.object_list', { 'queryset': Paste.objects.all() }),
)


########NEW FILE########
__FILENAME__ = views_134bb6
# Create your views here.

from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect, render_to_response, get_object_or_404
from django.template import RequestContext

from models import Post
from forms import PostForm, CommentForm

@user_passes_test(lambda u: u.is_superuser)
def add_post(request):
    form = PostForm(request.POST or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect(post)
    return render_to_response('blog/add_post.html', 
                              { 'form': form },
                              context_instance=RequestContext(request))

def view_post(request, slug):
    post = get_object_or_404(Post, slug=slug)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.save()
        request.session["name"] = comment.name
        request.session["email"] = comment.email
        request.session["website"] = comment.website
        return redirect(request.path)
    form.initial['name'] = request.session.get('name')
    form.initial['email'] = request.session.get('email')
    form.initial['website'] = request.session.get('website')
    return render_to_response('blog/blog_post.html',
                              {
                                  'post': post,
                                  'form': form,
                              },
                              context_instance=RequestContext(request))


########NEW FILE########
__FILENAME__ = views_abd13c
# Create your views here.

from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect, render_to_response, get_object_or_404
from django.template import RequestContext

from models import Post
from forms import PostForm, CommentForm

@user_passes_test(lambda u: u.is_superuser)
def add_post(request):
    form = PostForm(request.POST or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect(post)
    return render_to_response('blog/add_post.html', 
                              { 'form': form },
                              context_instance=RequestContext(request))

def view_post(request, slug):
    post = get_object_or_404(Post, slug=slug)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.save()
        return redirect(request.path)
    return render_to_response('blog/blog_post.html',
                              {
                                  'post': post,
                                  'form': form,
                              },
                              context_instance=RequestContext(request))


########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# djenofdjango documentation build configuration file, created by
# sphinx-quickstart on Tue Jul 27 18:14:49 2010.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.todo']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'djenofdjango'
copyright = u'2010, Agiliq'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1'
# The full version, including alpha/beta/rc tags.
release = '0.1'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = []

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = "agiliq"
html_theme_path = ["../themes/", "../../../themes/"]

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = "Djen of Django"

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
html_logo = "../../../themes/agiliq/static/logo.png"

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'djenofdjangodoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'djenofdjango.tex', u'djenofdjango Documentation',
   u'Agiliq', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = forms
from django import forms

from models import Post, Comment

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        exclude = ['author', 'slug']

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        exclude = ['post']


########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.template.defaultfilters import slugify

from django.contrib.auth.models import User

# Create your models here.

class Post(models.Model):
    title = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    text = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(User)

    def __unicode__(self):
        return self.title

    @models.permalink
    def get_absolute_url(self):
        return ('blog_post_detail', (), 
                {
                    'slug' :self.slug,
                })

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super(Post, self).save(*args, **kwargs)

class Comment(models.Model):
    name = models.CharField(max_length=42)
    email = models.EmailField(max_length=75)
    website = models.URLField(max_length=200, null=True, blank=True)
    text = models.TextField()
    post = models.ForeignKey(Post)
    created_on = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return self.text


########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from models import Post

urlpatterns = patterns('',
    url(r'^post/(?P<slug>[-\w]+)$', 
        'blog.views.view_post',
        name='blog_post_detail'),
    url(r'^add/post$', 
        'blog.views.add_post', 
        name='blog_add_post'),
    url(r'^archive/month/(?P<year>\d+)/(?P<month>\w+)$',
        'django.views.generic.date_based.archive_month',
        {
            'queryset': Post.objects.all(), 
            'date_field': 'created_on',
        },
        name='blog_archive_month',
       ),
    url(r'^archive/week/(?P<year>\d+)/(?P<week>\d+)$',
        'django.views.generic.date_based.archive_week',
        {
            'queryset': Post.objects.all(), 
            'date_field': 'created_on',
        },
        name='blog_archive_week',
       ),
)


########NEW FILE########
__FILENAME__ = views
# Create your views here.

from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect, render_to_response, get_object_or_404
from django.template import RequestContext

from models import Post
from forms import PostForm, CommentForm

@user_passes_test(lambda u: u.is_superuser)
def add_post(request):
    form = PostForm(request.POST or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect(post)
    return render_to_response('blog/add_post.html', 
                              { 'form': form },
                              context_instance=RequestContext(request))

def view_post(request, slug):
    post = get_object_or_404(Post, slug=slug)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.save()
        request.session["name"] = comment.name
        request.session["email"] = comment.email
        request.session["website"] = comment.website
        return redirect(request.path)
    form.initial['name'] = request.session.get('name')
    form.initial['email'] = request.session.get('email')
    form.initial['website'] = request.session.get('website')
    return render_to_response('blog/blog_post.html',
                              {
                                  'post': post,
                                  'form': form,
                              },
                              context_instance=RequestContext(request))


########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from models import CD

admin.site.register(CD)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.


GENRE_CHOICES = (
                    ('R', 'Rock'), 
                    ('B', 'Blues'),
                    ('J', 'Jazz'),
                    ('P', 'Pop'),
                )

class CD(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    artist = models.CharField(max_length=40)
    date = models.DateField()
    genre = models.CharField(max_length=1, choices=GENRE_CHOICES)

    def __unicode__(self):
        return "%s by %s, %s" %(self.title, self.artist, self.date.year)


########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = delete_old
import datetime

from django.core.management.base import NoArgsCommand

from pastebin.models import Paste

class Command(NoArgsCommand):
    help = """
            deletes pastes not updated in last 24 hrs

            Use this subcommand in a cron job
            to clear older pastes
           """

    def handle_noargs(self, **options):
        now = datetime.datetime.now()
        yesterday = now - datetime.timedelta(1)
        old_pastes = Paste.objects.filter(updated_on__lte=yesterday)
        old_pastes.delete()


########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.


class Paste(models.Model):
    text = models.TextField()
    name = models.CharField(max_length=40, null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.name or str(self.id)

    @models.permalink
    def get_absolute_url(self):
        return ('pastebin_paste_detail', [self.id])


########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
#from django.core.urlresolvers import reverse

from models import Paste

urlpatterns = patterns('',
    url(r'^$', 'django.views.generic.create_update.create_object', { 'model': Paste }, name='pastebin_paste_create'),
    url(r'^paste/edit/(?P<object_id>\d+)$', 'django.views.generic.create_update.update_object', { 'model': Paste }, name='pastebin_paste_edit'),
    url(r'^paste/delete/(?P<object_id>\d+)$', 'django.views.generic.create_update.delete_object', { 'model': Paste, 'post_delete_redirect': '/pastebin/pastes' }, name='pastebin_paste_delete'),
    url(r'^paste/(?P<object_id>\d+)$', 'django.views.generic.list_detail.object_detail', { 'queryset': Paste.objects.all() }, name='pastebin_paste_detail'),
    url(r'^pastes/$', 'django.views.generic.list_detail.object_list', { 'queryset': Paste.objects.all() }, name='pastebin_paste_list'),
)


########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = settings
# Django settings for djen_project project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'djen_database_test',                      # Or path to database file if using sqlite3.
        'USER': 'root',                      # Not used with sqlite3.
        'PASSWORD': 'agiliq',                  # Not used with sqlite3.
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

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '18+j03afl5&6j5fxlt++1e&^x%)2lwskc^62e$(=elhetrw+fs'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'djen_project.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.markup',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    'cd_library',
    'pastebin',
    'blog',
    'registration',
    'wiki',
)

from local_settings import *


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^djen_project/', include('djen_project.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^accounts/', include('registration.backends.default.urls')),
    (r'^admin/', include(admin.site.urls)),
    (r'^pastebin/', include('pastebin.urls')),
    (r'^blog/', include('blog.urls')),
    (r'^wiki/', include('wiki.urls')),
)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from models import Article, Edit

class EditInline(admin.StackedInline):
    model = Edit
    extra = 1
    exclude = ['editor']

class ArticleAdmin(admin.ModelAdmin):
    inlines = (EditInline,)


admin.site.register(Article, ArticleAdmin)


########NEW FILE########
__FILENAME__ = forms
from django import forms

from models import Article, Edit

class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        exclude = ['author', 'slug']


class EditForm(forms.ModelForm):
    class Meta:
        model = Edit
        fields = ['summary']


########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify

# Create your models here.

class PublishedArticlesManager(models.Manager):
    
    def get_query_set(self):
        return super(PublishedArticlesManager, self).get_query_set().filter(is_published=True)

class Article(models.Model):
    """Represents a wiki article"""
    
    title = models.CharField(max_length=100)
    slug = models.SlugField(max_length=50, unique=True)
    text = models.TextField(help_text="Formatted using ReST")
    author = models.ForeignKey(User)
    is_published = models.BooleanField(default=False, verbose_name="Publish?")
    created_on = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()
    published = PublishedArticlesManager()

    def __unicode__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super(Article, self).save(*args, **kwargs)

    @models.permalink
    def get_absolute_url(self):
        return ('wiki_article_detail', (), { 'slug': self.slug })

class Edit(models.Model):
    """Stores an edit session"""
    
    article = models.ForeignKey(Article)
    editor = models.ForeignKey(User)
    edited_on = models.DateTimeField(auto_now_add=True)
    summary = models.CharField(max_length=100)

    class Meta:
        ordering = ['-edited_on']

    def __unicode__(self):
        return "%s - %s - %s" %(self.summary, self.editor, self.edited_on)
    
    @models.permalink
    def get_absolute_url(self):
        return ('wiki_edit_detail', self.id)


########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from models import Article

urlpatterns = patterns('',
    url(r'^$', 
        'django.views.generic.list_detail.object_list',
        {
            'queryset': Article.published.all(),
        },
        name='wiki_article_index'),
    url(r'^article/(?P<slug>[-\w]+)$', 
        'django.views.generic.list_detail.object_detail',
        {
            'queryset': Article.objects.all(),
        },
        name='wiki_article_detail'),
    url(r'^history/(?P<slug>[-\w]+)$',
        'wiki.views.article_history',
        name='wiki_article_history'),
    url(r'^add/article$',
        'wiki.views.add_article',
        name='wiki_article_add'),
    url(r'^edit/article/(?P<slug>[-\w]+)$',
        'wiki.views.edit_article',
        name='wiki_article_edit'),
)


########NEW FILE########
__FILENAME__ = views
# Create your views here.

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, render_to_response, get_object_or_404
from django.template import RequestContext
from django.views.generic.list_detail import object_list

from models import Article, Edit
from forms import ArticleForm, EditForm

@login_required
def add_article(request):
    form = ArticleForm(request.POST or None)
    if form.is_valid():
        article = form.save(commit=False)
        article.author = request.user
        article.save()
        msg = "Article saved successfully"
        messages.success(request, msg, fail_silently=True)
        return redirect(article)
    return render_to_response('wiki/article_form.html', 
                              { 'form': form },
                              context_instance=RequestContext(request))

@login_required
def edit_article(request, slug):
    article = get_object_or_404(Article, slug=slug)
    form = ArticleForm(request.POST or None, instance=article)
    edit_form = EditForm(request.POST or None)
    if form.is_valid():
        article = form.save()
        if edit_form.is_valid():
            edit = edit_form.save(commit=False)
            edit.article = article
            edit.editor = request.user
            edit.save()
            msg = "Article updated successfully"
            messages.success(request, msg, fail_silently=True)
            return redirect(article)
    return render_to_response('wiki/article_form.html', 
                              { 
                                  'form': form,
                                  'edit_form': edit_form,
                                  'article': article,
                              },
                              context_instance=RequestContext(request))

def article_history(request, slug):
    article = get_object_or_404(Article, slug=slug)
    return  object_list(request, 
                        queryset=Edit.objects.filter(article__slug=slug),
                        extra_context={'article': article})


########NEW FILE########
