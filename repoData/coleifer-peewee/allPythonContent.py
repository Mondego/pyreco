__FILENAME__ = bench
import datetime
import os

from models import Blog
from models import Entry
from models import User


def initialize():
    from django.core.management import call_command
    call_command('syncdb')

def teardown():
    from django.db import connection
    curs = connection.cursor()
    curs.execute('DROP TABLE django_bench_entry;')
    curs.execute('DROP TABLE django_bench_blog;')
    curs.execute('DROP TABLE django_bench_user;')

def create_user(username, active=True):
    return User.objects.create(username=username, active=active)

def create_blog(user, name):
    return Blog.objects.create(user=user, name=name)

def create_entry(blog, title, content, pub_date=None):
    return Entry.objects.create(blog=blog, title=title, content=content,
                                pub_date=pub_date or datetime.datetime.now())

def list_users(ordered=False):
    if ordered:
        qs = User.objects.all().order_by('username')
    else:
        qs = User.objects.all()
    return list(qs)

def list_blogs_select_related():
    qs = Blog.objects.all().select_related('user')
    return list(qs)

def list_blogs_for_user(user):
    return list(user.blog_set.all())

def list_entries_by_user(user):
    return list(Entry.objects.filter(blog__user=user))

def get_user_count():
    return User.objects.all().count()

def list_entries_subquery(user):
    return list(Entry.objects.filter(blog__in=Blog.objects.filter(user=user)))

def get_user(username):
    return User.objects.get(username=username)

def get_or_create_user(username):
    return User.objects.get_or_create(username=username)

########NEW FILE########
__FILENAME__ = models
from django.conf import settings

settings.configure(
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': 'test_dj.db',
        }
    },
    INSTALLED_APPS = ('django_bench',)
)

from django.db import models


class User(models.Model):
    username = models.CharField(max_length=255)
    active = models.BooleanField(default=True)


class Blog(models.Model):
    user = models.ForeignKey(User)
    name = models.CharField(max_length=255)


class Entry(models.Model):
    blog = models.ForeignKey(Blog)
    title = models.CharField(max_length=255)
    content = models.TextField()
    pub_date = models.DateTimeField()

########NEW FILE########
__FILENAME__ = bench
import datetime

from models import Blog
from models import Entry
from models import User
from models import create_tables
from models import drop_tables


def initialize():
    try:
        create_tables()
    except:
        pass

def teardown():
    drop_tables()

def create_user(username, active=True):
    return User.create(username=username, active=active)

def create_blog(user, name):
    return Blog.create(user=user, name=name)

def create_entry(blog, title, content, pub_date=None):
    return Entry.create(blog=blog, title=title, content=content,
                        pub_date=pub_date or datetime.datetime.now())

def list_users(ordered=False):
    if ordered:
        sq = User.select().order_by(User.username.asc())
    else:
        sq = User.select()
    return list(sq)

def list_blogs_select_related():
    qs = Blog.select(Blog, User).join(User)
    return list(qs)

def list_blogs_for_user(user):
    return list(user.blog_set)

def list_entries_by_user(user):
    return list(Entry.select().join(Blog).where(Blog.user == user))

def get_user_count():
    return User.select().count()

def list_entries_subquery(user):
    return list(Entry.select().where(Entry.blog << Blog.select().where(Blog.user == user)))

def get_user(username):
    return User.get(username=username)

def get_or_create_user(username):
    try:
        User.get(User.username == username)
    except User.DoesNotExist:
        User.create(username=username)

########NEW FILE########
__FILENAME__ = models
import peewee


test_db = peewee.SqliteDatabase('test_pw.db')

class User(peewee.Model):
    username = peewee.CharField()
    active = peewee.BooleanField(default=False)

    class Meta:
        database = test_db


class Blog(peewee.Model):
    user = peewee.ForeignKeyField(User)
    name = peewee.CharField()

    class Meta:
        database = test_db


class Entry(peewee.Model):
    blog = peewee.ForeignKeyField(Blog)
    title = peewee.CharField()
    content = peewee.TextField(default='')
    pub_date = peewee.DateTimeField(null=True)

    class Meta:
        database = test_db


def create_tables():
    test_db.connect()
    User.create_table()
    Blog.create_table()
    Entry.create_table()


def drop_tables():
    test_db.connect()
    Entry.drop_table(fail_silently=True)
    Blog.drop_table(fail_silently=True)
    User.drop_table(fail_silently=True)

########NEW FILE########
__FILENAME__ = run_bench
#!/usr/bin/env python

import os
import sys
import time

sys.path.insert(0, '..')


benchmarks = [dirname for dirname in os.listdir('.') if not os.path.isfile(dirname)]
results = {}

bench_modules = map(__import__, ('%s.bench' % b for b in benchmarks))

def run(func, do_cleanup=False, no_time=False):
    if not no_time:
        results[func.__name__] = {}
    for i, m in enumerate(bench_modules):
        try:
            m.bench.initialize()
            start = time.time()
            func(m.bench)
            end = time.time()
            if not no_time:
                results[func.__name__][benchmarks[i]] = end - start
        finally:
            if do_cleanup:
                m.bench.teardown()

def test_creation(m):
    for i in xrange(1000):
        u = m.create_user('user%d' % i)
        b = m.create_blog(u, 'blog%d' % i)
        e = m.create_entry(b, 'entry%d' % i, '')

def test_list_users(m):
    for i in xrange(100):
        users = m.list_users()

def test_list_users_ordered(m):
    for i in xrange(100):
        users = m.list_users(True)

def test_list_blogs_select_related(m):
    for i in xrange(100):
        m.list_blogs_select_related()

def test_get_user_count(m):
    for i in xrange(100):
        m.get_user_count()

def test_get_user(m):
    for i in xrange(100):
        m.get_user('user%d' % i)

    for i in xrange(1000, 1100):
        try:
            m.get_user('user%d' % i)
        except:
            pass

def test_get_or_create_pass(m):
    for i in xrange(100):
        m.get_or_create_user('user%d' % i)

def test_get_or_create_fail(m):
    for i in xrange(1000, 1100):
        m.get_or_create_user('user%d' % i)

def test_prep_lb4u(m):
    for i in xrange(10):
        u = m.create_user('user%d' % i)
        for j in xrange(10):
            m.create_blog(u, 'blog%d' % j)

def test_list_blogs_for_user(m):
    for user in m.list_users():
        for i in xrange(100):
            blogs = m.list_blogs_for_user(user)

def test_prep_le4u(m):
    for i in xrange(10):
        u = m.create_user('user%d' % i)
        b = m.create_blog(u, 'blog%d' % i)
        for j in xrange(10):
            e = m.create_entry(b, 'entry%d' % i, '')

def test_list_entries_for_user(m):
    for user in m.list_users():
        for i in xrange(100):
            entries = m.list_entries_by_user(user)

def test_list_entries_subquery(m):
    for user in m.list_users():
        for i in xrange(100):
            entries = m.list_entries_subquery(user)

def run_all_benches():
    run(test_creation)
    run(test_list_users)
    run(test_list_users_ordered)
    run(test_list_blogs_select_related)
    run(test_get_user)
    run(test_get_or_create_pass)
    run(test_get_or_create_fail)
    run(test_get_user_count, True) # test_list_blogs creates objects
    run(test_prep_lb4u, False, True) # prep "list blogs for user"
    run(test_list_blogs_for_user, True)
    run(test_prep_le4u, False, True)
    run(test_list_entries_for_user)
    run(test_list_entries_subquery, True)


if __name__ == '__main__':
    print 'Running benchmarks for %s' % (', '.join(b for b in benchmarks))
    run_all_benches()

    pw_k = 'peewee_bench'
    non_pw = [b for b in benchmarks if b != pw_k]

    print '%30s |' % (' '),
    for b in benchmarks:
        print '%16s |' % b,
    for b in non_pw:
        print '%s diff |' % (b[:5]),
    print

    for func, result_dict in results.iteritems():
        print '%30s |' % func,
        for b in benchmarks:
            print '%16f |' % result_dict[b],
        pw_res = result_dict[pw_k]
        for b in non_pw:
            print '%9f%% |' % (100 - 100 * (result_dict[pw_k] / result_dict[b])),
        print

########NEW FILE########
__FILENAME__ = bench
import datetime
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import sessionmaker

from models import Blog
from models import Entry
from models import User

db_file = os.path.join(os.getcwd(), 'test_sa.db')
engine = create_engine('sqlite:///%s' % db_file)

Session = sessionmaker(bind=engine)
session = Session()

User.metadata.bind = engine

def initialize():
    User.metadata.create_all()

def teardown():
    User.metadata.drop_all()

def create_user(username, active=True):
    u = User(username=username, active=active)
    session.add(u)
    session.commit()
    return u

def create_blog(user, name):
    b = Blog(user=user, name=name)
    session.add(b)
    session.commit()
    return b

def create_entry(blog, title, content, pub_date=None):
    e = Entry(blog=blog, title=title, content=content,
              pub_date=pub_date or datetime.datetime.now())
    session.add(e)
    session.commit()
    return e

def list_users(ordered=False):
    if ordered:
        return list(session.query(User).order_by(User.username))
    else:
        return list(session.query(User))

def list_blogs_for_user(user):
    return list(user.blog_set)

def list_blogs_select_related():
    return list(session.query(Blog).options(joinedload(Blog.user)))

def list_entries_by_user(user):
    return list(session.query(Entry).join(Blog).filter(Blog.user_id==user.id))

def get_user_count():
    return session.query(User).count()

def list_entries_subquery(user):
    pass

def get_user(username):
    return session.query(User).filter_by(username=username).first()

def get_or_create_user(username):
    try:
        user = session.query(User).filter_by(username=username).one()
    except:
        user = User(username=username, active=False)
        session.add(user)
        session.commit()
    return user

########NEW FILE########
__FILENAME__ = models
import os

from sqlalchemy import Table
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref
from sqlalchemy.orm import relationship


Base = declarative_base()

class User(Base):
    __tablename__ = 'sqlalc_users'

    id = Column(Integer, primary_key=True)
    username = Column(String)
    active = Column(Boolean)


class Blog(Base):
    __tablename__ = 'sqlalc_blogs'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('sqlalc_users.id'), index=True)
    name = Column(String)

    user = relationship(User, backref=backref('blog_set'))


class Entry(Base):
    __tablename__ = 'sqlalc_entries'

    id = Column(Integer, primary_key=True)
    blog_id = Column(Integer, ForeignKey('sqlalc_blogs.id'), index=True)
    title = Column(String)
    content = Column(String)
    pub_date = Column(DateTime)

    blog = relationship(Blog, backref=backref('entry_set'))

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# peewee documentation build configuration file, created by
# sphinx-quickstart on Fri Nov 26 11:05:15 2010.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

#RTD_NEW_THEME = True

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'peewee'
copyright = u'charles leifer'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '2.2.4'
# The full version, including alpha/beta/rc tags.
release = '2.2.4'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

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
pygments_style = 'pastie'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {
#    'index_logo': 'peewee-white.png'
#}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = ['_themes']

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

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
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'peeweedoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'peewee.tex', u'peewee Documentation',
   u'charles leifer', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'peewee', u'peewee Documentation',
     [u'charles leifer'], 1)
]

########NEW FILE########
__FILENAME__ = app
"""
Example "Analytics" app. To start using this on your site, do the following:

* Create a postgresql database with HStore support:

    createdb analytics
    psql analytics -c "create extension hstore;"

* Create an account for each domain you intend to collect analytics for, e.g.

    Account.create(domain='charlesleifer.com')

* Update configuration values marked "TODO", e.g. DOMAIN.

* Run this app using the WSGI server of your choice.

* Using the appropriate account id, add a `<script>` tag to each site you want
  to collect analytics data from. I place mine at the bottom of the <body>:

    <script src="http://yourdomain.com/a.js?id=<your account id>"></script>

Take a look at `reports.py` for some interesting queries you can perform
on your pageview data.
"""
import datetime
import os
from urlparse import parse_qsl, urlparse

from flask import Flask, Response, abort, request
from peewee import create_model_tables
from peewee import *
from playhouse.postgres_ext import HStoreField
from playhouse.postgres_ext import PostgresqlExtDatabase


# Analytics settings.
BEACON = '47494638396101000100800000dbdfef00000021f90401000000002c00000000010001000002024401003b'.decode('hex')  # 1px gif.
DATABASE_NAME = 'analytics'
DOMAIN = 'http://analytics.yourdomain.com'  # TODO: change me.
JAVASCRIPT = """(function(id){
    var d=document,i=new Image,e=encodeURIComponent;
    i.src='%s/a.gif?id='+id+'&url='+e(d.location.href)+'&ref='+e(d.referrer)+'&t='+e(d.title);
    })(%s)""".replace('\n', '')

# Flask settings.
DEBUG = bool(os.environ.get('DEBUG'))
SECRET_KEY = 'secret - change me'  # TODO: change me.

app = Flask(__name__)
app.config.from_object(__name__)

database = PostgresqlExtDatabase(
    DATABASE_NAME,
    user='postgres',
    threadlocals=True)

class BaseModel(Model):
    class Meta:
        database = database

class Account(BaseModel):
    domain = CharField()

    def verify_url(self, url):
        netloc = urlparse(url).netloc
        url_domain = '.'.join(netloc.split('.')[-2:])  # Ignore subdomains.
        return self.domain == url_domain

class PageView(BaseModel):
    account = ForeignKeyField(Account, related_name='pageviews')
    url = TextField()
    timestamp = DateTimeField(default=datetime.datetime.now)
    title = TextField(default='')
    ip = CharField(default='')
    referrer = TextField(default='')
    headers = HStoreField()
    params = HStoreField()

    @classmethod
    def create_from_request(cls, account, request):
        parsed = urlparse(request.args['url'])
        params = dict(parse_qsl(parsed.query))

        return PageView.create(
            account=account,
            url=parsed.path,
            title=request.args.get('t') or '',
            ip=request.headers.get('x-forwarded-for', request.remote_addr),
            referrer=request.args.get('ref') or '',
            headers=dict(request.headers),
            params=params)

@app.route('/a.gif')
def analyze():
    # Make sure an account id and url were specified.
    if not request.args.get('id') or not request.args.get('url'):
        abort(404)

    # Ensure the account id is valid.
    try:
        account = Account.get(Account.id == request.args['id'])
    except Account.DoesNotExist:
        abort(404)

    # Ensure the account id matches the domain of the URL we wish to record.
    if not account.verify_url(request.args['url']):
        abort(403)

    # Store the page-view data in the database.
    PageView.create_from_request(account, request)

    # Return a 1px gif.
    response = Response(app.config['BEACON'], mimetype='image/gif')
    response.headers['Cache-Control'] = 'private, no-cache'
    return response

@app.route('/a.js')
def script():
    account_id = request.args.get('id')
    if account_id:
        return Response(
            app.config['JAVASCRIPT'] % (app.config['DOMAIN'], account_id),
            mimetype='text/javascript')
    return Response('', mimetype='text/javascript')

@app.errorhandler(404)
def not_found(e):
    return Response('<h3>Not found.</h3>')


if __name__ == '__main__':
    create_model_tables([Account, PageView], fail_silently=True)
    app.run(debug=True)

########NEW FILE########
__FILENAME__ = reports
from peewee import *

from app import Account, PageView


DEFAULT_ACCOUNT_ID = 1

class Report(object):
    def __init__(self, account_id=DEFAULT_ACCOUNT_ID):
        self.account = Account.get(Account.id == account_id)
        self.date_range = None

    def get_query(self):
        query = PageView.select().where(PageView.account == self.account)
        if self.date_range:
            query = query.where(PageView.timestamp.between(*self.date_range))
        return query

    def top_pages_by_time_period(self, interval='day'):
        """
        Get a breakdown of top pages per interval, i.e.

        day         url     count
        2014-01-01  /blog/  11
        2014-01-02  /blog/  14
        2014-01-03  /blog/  9
        """
        date_trunc = fn.date_trunc(interval, PageView.timestamp)
        return (self.get_query()
                .select(
                    PageView.url,
                    date_trunc.alias(interval),
                    fn.Count(PageView.id).alias('count'))
                .group_by(PageView.url, date_trunc)
                .order_by(
                    SQL(interval),
                    SQL('count').desc(),
                    PageView.url))

    def cookies(self):
        """
        Retrieve the cookies header from all the users who visited.
        """
        return (self.get_query()
                .select(PageView.ip, PageView.headers['Cookie'])
                .where(~(PageView.headers['Cookie'] >> None))
                .tuples())

    def user_agents(self):
        """
        Retrieve user-agents, sorted by most common to least common.
        """
        return (self.get_query()
                .select(
                    PageView.headers['User-Agent'],
                    fn.Count(PageView.id))
                .group_by(PageView.headers['User-Agent'])
                .order_by(fn.Count(PageView.id).desc())
                .tuples())

    def languages(self):
        """
        Retrieve languages, sorted by most common to least common. The
        Accept-Languages header sometimes looks weird, i.e.
        "en-US,en;q=0.8,is;q=0.6,da;q=0.4" We will split on the first semi-
        colon.
        """
        language = PageView.headers['Accept-Language']
        first_language = fn.SubStr(
            language,  # String to slice.
            1,  # Left index.
            fn.StrPos(language, ';'))
        return (self.get_query()
                .select(first_language, fn.Count(PageView.id))
                .group_by(first_language)
                .order_by(fn.Count(PageView.id).desc())
                .tuples())

    def trail(self):
        """
        Get all visitors by IP and then list the pages they visited in order.
        """
        inner = (self.get_query()
                 .select(PageView.ip, PageView.url)
                 .order_by(PageView.timestamp))
        return (PageView
                .select(
                    PageView.ip,
                    fn.array_agg(PageView.url).coerce(False).alias('urls'))
                .from_(inner.alias('t1'))
                .group_by(PageView.ip))

    def _referrer_clause(self, domain_only=True):
        if domain_only:
            return fn.SubString(Clause(
                PageView.referrer, SQL('FROM'), '.*://([^/]*)'))
        return PageView.referrer

    def top_referrers(self, domain_only=True):
        """
        What domains send us the most traffic?
        """
        referrer = self._referrer_clause(domain_only)
        return (self.get_query()
                .select(referrer, fn.Count(PageView.id))
                .group_by(referrer)
                .order_by(fn.Count(PageView.id).desc())
                .tuples())

    def referrers_for_url(self, domain_only=True):
        referrer = self._referrer_clause(domain_only)
        return (self.get_query()
                .select(PageView.url, referrer, fn.Count(PageView.id))
                .group_by(PageView.url, referrer)
                .order_by(PageView.url, fn.Count(PageView.id).desc())
                .tuples())

    def referrers_to_url(self, domain_only=True):
        referrer = self._referrer_clause(domain_only)
        return (self.get_query()
                .select(referrer, PageView.url, fn.Count(PageView.id))
                .group_by(referrer, PageView.url)
                .order_by(referrer, fn.Count(PageView.id).desc())
                .tuples())

########NEW FILE########
__FILENAME__ = run_example
#!/usr/bin/env python

import sys
sys.path.insert(0, '../..')

from app import app
app.run(debug=True)

########NEW FILE########
__FILENAME__ = app
import datetime

from flask import Flask
from flask import g
from flask import redirect
from flask import request
from flask import session
from flask import url_for, abort, render_template, flash
from functools import wraps
from hashlib import md5
from peewee import *

# config - aside from our database, the rest is for use by Flask
DATABASE = 'tweepee.db'
DEBUG = True
SECRET_KEY = 'hin6bab8ge25*r=x&amp;+5$0kn=-#log$pt^#@vrqjld!^2ci@g*b'

# create a flask application - this ``app`` object will be used to handle
# inbound requests, routing them to the proper 'view' functions, etc
app = Flask(__name__)
app.config.from_object(__name__)

# create a peewee database instance -- our models will use this database to
# persist information
database = SqliteDatabase(DATABASE)

# model definitions -- the standard "pattern" is to define a base model class
# that specifies which database to use.  then, any subclasses will automatically
# use the correct storage. for more information, see:
# http://charlesleifer.com/docs/peewee/peewee/models.html#model-api-smells-like-django
class BaseModel(Model):
    class Meta:
        database = database

# the user model specifies its fields (or columns) declaratively, like django
class User(BaseModel):
    username = CharField(unique=True)
    password = CharField()
    email = CharField()
    join_date = DateTimeField()

    class Meta:
        order_by = ('username',)

    # it often makes sense to put convenience methods on model instances, for
    # example, "give me all the users this user is following":
    def following(self):
        # query other users through the "relationship" table
        return User.select().join(
            Relationship, on=Relationship.to_user,
        ).where(Relationship.from_user == self)

    def followers(self):
        return User.select().join(
            Relationship, on=Relationship.from_user,
        ).where(Relationship.to_user == self)

    def is_following(self, user):
        return Relationship.select().where(
            (Relationship.from_user == self) &
            (Relationship.to_user == user)
        ).count() > 0

    def gravatar_url(self, size=80):
        return 'http://www.gravatar.com/avatar/%s?d=identicon&s=%d' % \
            (md5(self.email.strip().lower().encode('utf-8')).hexdigest(), size)


# this model contains two foreign keys to user -- it essentially allows us to
# model a "many-to-many" relationship between users.  by querying and joining
# on different columns we can expose who a user is "related to" and who is
# "related to" a given user
class Relationship(BaseModel):
    from_user = ForeignKeyField(User, related_name='relationships')
    to_user = ForeignKeyField(User, related_name='related_to')


# a dead simple one-to-many relationship: one user has 0..n messages, exposed by
# the foreign key.  because we didn't specify, a users messages will be accessible
# as a special attribute, User.message_set
class Message(BaseModel):
    user = ForeignKeyField(User)
    content = TextField()
    pub_date = DateTimeField()

    class Meta:
        order_by = ('-pub_date',)


# simple utility function to create tables
def create_tables():
    database.connect()
    User.create_table()
    Relationship.create_table()
    Message.create_table()

# flask provides a "session" object, which allows us to store information across
# requests (stored by default in a secure cookie).  this function allows us to
# mark a user as being logged-in by setting some values in the session data:
def auth_user(user):
    session['logged_in'] = True
    session['user_id'] = user.id
    session['username'] = user.username
    flash('You are logged in as %s' % (user.username))

# get the user from the session
def get_current_user():
    if session.get('logged_in'):
        return User.get(User.id == session['user_id'])

# view decorator which indicates that the requesting user must be authenticated
# before they can access the view.  it checks the session to see if they're
# logged in, and if not redirects them to the login view.
def login_required(f):
    @wraps(f)
    def inner(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return inner

# given a template and a SelectQuery instance, render a paginated list of
# objects from the query inside the template
def object_list(template_name, qr, var_name='object_list', **kwargs):
    kwargs.update(
        page=int(request.args.get('page', 1)),
        pages=qr.count() / 20 + 1
    )
    kwargs[var_name] = qr.paginate(kwargs['page'])
    return render_template(template_name, **kwargs)

# retrieve a single object matching the specified query or 404 -- this uses the
# shortcut "get" method on model, which retrieves a single object or raises a
# DoesNotExist exception if no matching object exists
# http://charlesleifer.com/docs/peewee/peewee/models.html#Model.get)
def get_object_or_404(model, **kwargs):
    try:
        return model.get(**kwargs)
    except model.DoesNotExist:
        abort(404)

# custom template filter -- flask allows you to define these functions and then
# they are accessible in the template -- this one returns a boolean whether the
# given user is following another user.
@app.template_filter('is_following')
def is_following(from_user, to_user):
    return from_user.is_following(to_user)

# request handlers -- these two hooks are provided by flask and we will use them
# to create and tear down a database connection on each request.  peewee will do
# this for us, but its generally a good idea to be explicit.
@app.before_request
def before_request():
    g.db = database
    g.db.connect()

@app.after_request
def after_request(response):
    g.db.close()
    return response

# views -- these are the actual mappings of url to view function
@app.route('/')
def homepage():
    # depending on whether the requesting user is logged in or not, show them
    # either the public timeline or their own private timeline
    if session.get('logged_in'):
        return private_timeline()
    else:
        return public_timeline()

@app.route('/private/')
def private_timeline():
    # the private timeline exemplifies the use of a subquery -- we are asking for
    # messages where the person who created the message is someone the current
    # user is following.  these messages are then ordered newest-first.
    user = get_current_user()
    messages = Message.select().where(
        Message.user << user.following()
    )
    return object_list('private_messages.html', messages, 'message_list')

@app.route('/public/')
def public_timeline():
    # simply display all messages, newest first
    messages = Message.select()
    return object_list('public_messages.html', messages, 'message_list')

@app.route('/join/', methods=['GET', 'POST'])
def join():
    if request.method == 'POST' and request.form['username']:
        try:
            with database.transaction():
                # if not, create the user and store the form data on the new model
                user = User.create(
                    username=request.form['username'],
                    password=md5(request.form['password']).hexdigest(),
                    email=request.form['email'],
                    join_date=datetime.datetime.now()
                )

            # mark the user as being 'authenticated' by setting the session vars
            auth_user(user)
            return redirect(url_for('homepage'))

        except IntegrityError:
            # use the .get() method to quickly see if a user with that name exists
            user = User.get(username=request.form['username'])
            flash('That username is already taken')

    return render_template('join.html')

@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST' and request.form['username']:
        try:
            user = User.get(
                username=request.form['username'],
                password=md5(request.form['password']).hexdigest()
            )
        except User.DoesNotExist:
            flash('The password entered is incorrect')
        else:
            auth_user(user)
            return redirect(url_for('homepage'))

    return render_template('login.html')

@app.route('/logout/')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('homepage'))

@app.route('/following/')
@login_required
def following():
    user = get_current_user()
    return object_list('user_following.html', user.following(), 'user_list')

@app.route('/followers/')
@login_required
def followers():
    user = get_current_user()
    return object_list('user_followers.html', user.followers(), 'user_list')

@app.route('/users/')
def user_list():
    users = User.select()
    return object_list('user_list.html', users, 'user_list')

@app.route('/users/<username>/')
def user_detail(username):
    # using the "get_object_or_404" shortcut here to get a user with a valid
    # username or short-circuit and display a 404 if no user exists in the db
    user = get_object_or_404(User, username=username)

    # get all the users messages ordered newest-first -- note how we're accessing
    # the messages -- user.message_set.  could also have written it as:
    # Message.select().where(user=user).order_by(('pub_date', 'desc'))
    messages = user.message_set
    return object_list('user_detail.html', messages, 'message_list', user=user)

@app.route('/users/<username>/follow/', methods=['POST'])
@login_required
def user_follow(username):
    user = get_object_or_404(User, username=username)
    Relationship.get_or_create(
        from_user=get_current_user(),
        to_user=user,
    )
    flash('You are now following %s' % user.username)
    return redirect(url_for('user_detail', username=user.username))

@app.route('/users/<username>/unfollow/', methods=['POST'])
@login_required
def user_unfollow(username):
    user = get_object_or_404(User, username=username)
    Relationship.delete().where(
        (Relationship.from_user == get_current_user()) &
        (Relationship.to_user == user)
    ).execute()
    flash('You are no longer following %s' % user.username)
    return redirect(url_for('user_detail', username=user.username))

@app.route('/create/', methods=['GET', 'POST'])
@login_required
def create():
    user = get_current_user()
    if request.method == 'POST' and request.form['content']:
        message = Message.create(
            user=user,
            content=request.form['content'],
            pub_date=datetime.datetime.now()
        )
        flash('Your message has been created')
        return redirect(url_for('user_detail', username=user.username))

    return render_template('create.html')

@app.context_processor
def _inject_user():
    return {'current_user': get_current_user()}

# allow running from the command line
if __name__ == '__main__':
    app.run()

########NEW FILE########
__FILENAME__ = run_example
#!/usr/bin/env python

import sys
sys.path.insert(0, '../..')

from app import app
app.run()

########NEW FILE########
__FILENAME__ = peewee
#     (\
#     (  \  /(o)\     caw!
#     (   \/  ()/ /)
#      (   `;.))'".)
#       `(/////.-'
#    =====))=))===()
#      ///'
#     //
#    '
import datetime
import decimal
import hashlib
import logging
import operator
import re
import sys
import threading
import uuid
from collections import deque
from collections import namedtuple
from copy import deepcopy
from functools import wraps
from inspect import isclass

__version__ = '2.2.4'
__all__ = [
    'BareField',
    'BigIntegerField',
    'BlobField',
    'BooleanField',
    'CharField',
    'Check',
    'Clause',
    'CompositeKey',
    'DatabaseError',
    'DataError',
    'DateField',
    'DateTimeField',
    'DecimalField',
    'DoesNotExist',
    'DoubleField',
    'DQ',
    'Field',
    'FloatField',
    'fn',
    'ForeignKeyField',
    'ImproperlyConfigured',
    'IntegerField',
    'IntegrityError',
    'InterfaceError',
    'InternalError',
    'JOIN_FULL',
    'JOIN_INNER',
    'JOIN_LEFT_OUTER',
    'Model',
    'MySQLDatabase',
    'NotSupportedError',
    'OperationalError',
    'Param',
    'PostgresqlDatabase',
    'prefetch',
    'PrimaryKeyField',
    'ProgrammingError',
    'Proxy',
    'R',
    'SqliteDatabase',
    'SQL',
    'TextField',
    'TimeField',
]

# Set default logging handler to avoid "No handlers could be found for logger
# "peewee"" warnings.
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

# All peewee-generated logs are logged to this namespace.
logger = logging.getLogger('peewee')
logger.addHandler(NullHandler())

# Python 2/3 compatibility helpers. These helpers are used internally and are
# not exported.
def with_metaclass(meta, base=object):
    return meta("NewBase", (base,), {})

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3
if PY3:
    import builtins
    from collections import Callable
    from functools import reduce
    callable = lambda c: isinstance(c, Callable)
    unicode_type = str
    string_type = bytes
    basestring = str
    print_ = getattr(builtins, 'print')
    binary_construct = lambda s: bytes(s.encode('raw_unicode_escape'))
    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value
elif PY2:
    unicode_type = unicode
    string_type = basestring
    binary_construct = buffer
    def print_(s):
        sys.stdout.write(s)
        sys.stdout.write('\n')
    exec('def reraise(tp, value, tb=None): raise tp, value, tb')
else:
    raise RuntimeError('Unsupported python version.')

# By default, peewee supports Sqlite, MySQL and Postgresql.
import sqlite3
try:
    import psycopg2
    from psycopg2 import extensions as pg_extensions
except ImportError:
    psycopg2 = None
try:
    import MySQLdb as mysql  # prefer the C module.
except ImportError:
    try:
        import pymysql as mysql
    except ImportError:
        mysql = None

sqlite3.register_adapter(decimal.Decimal, str)
sqlite3.register_adapter(datetime.date, str)
sqlite3.register_adapter(datetime.time, str)

DATETIME_PARTS = ['year', 'month', 'day', 'hour', 'minute', 'second']
DATETIME_LOOKUPS = set(DATETIME_PARTS)

# Sqlite does not support the `date_part` SQL function, so we will define an
# implementation in python.
SQLITE_DATETIME_FORMATS = (
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M:%S.%f',
    '%Y-%m-%d',
    '%H:%M:%S',
    '%H:%M:%S.%f',
    '%H:%M')

def _sqlite_date_part(lookup_type, datetime_string):
    assert lookup_type in DATETIME_LOOKUPS
    dt = format_date_time(datetime_string, SQLITE_DATETIME_FORMATS)
    return getattr(dt, lookup_type)

SQLITE_DATE_TRUNC_MAPPING = {
    'year': '%Y',
    'month': '%Y-%m',
    'day': '%Y-%m-%d',
    'hour': '%Y-%m-%d %H',
    'minute': '%Y-%m-%d %H:%M',
    'second': '%Y-%m-%d %H:%M:%S'}
MYSQL_DATE_TRUNC_MAPPING = SQLITE_DATE_TRUNC_MAPPING.copy()
MYSQL_DATE_TRUNC_MAPPING['minute'] = '%Y-%m-%d %H:%i'
MYSQL_DATE_TRUNC_MAPPING['second'] = '%Y-%m-%d %H:%i:%S'

def _sqlite_date_trunc(lookup_type, datetime_string):
    assert lookup_type in SQLITE_DATE_TRUNC_MAPPING
    dt = format_date_time(datetime_string, SQLITE_DATETIME_FORMATS)
    return dt.strftime(SQLITE_DATE_TRUNC_MAPPING[lookup_type])

def _sqlite_regexp(regex, value):
    return re.search(regex, value, re.I) is not None

# Operators used in binary expressions.
OP_AND = 'and'
OP_OR = 'or'

OP_ADD = '+'
OP_SUB = '-'
OP_MUL = '*'
OP_DIV = '/'
OP_BIN_AND = '&'
OP_BIN_OR = '|'
OP_XOR = '^'
OP_MOD = '%'

OP_EQ = '='
OP_LT = '<'
OP_LTE = '<='
OP_GT = '>'
OP_GTE = '>='
OP_NE = '!='
OP_IN = 'in'
OP_IS = 'is'
OP_LIKE = 'like'
OP_ILIKE = 'ilike'
OP_BETWEEN = 'between'
OP_REGEXP = 'regexp'

# To support "django-style" double-underscore filters, create a mapping between
# operation name and operation code, e.g. "__eq" == OP_EQ.
DJANGO_MAP = {
    'eq': OP_EQ,
    'lt': OP_LT,
    'lte': OP_LTE,
    'gt': OP_GT,
    'gte': OP_GTE,
    'ne': OP_NE,
    'in': OP_IN,
    'is': OP_IS,
    'like': OP_LIKE,
    'ilike': OP_ILIKE,
    'regexp': OP_REGEXP,
}

JOIN_INNER = 'inner'
JOIN_LEFT_OUTER = 'left outer'
JOIN_FULL = 'full'

# Helper functions that are used in various parts of the codebase.
def merge_dict(source, overrides):
    merged = source.copy()
    merged.update(overrides)
    return merged

def returns_clone(func):
    """
    Method decorator that will "clone" the object before applying the given
    method.  This ensures that state is mutated in a more predictable fashion,
    and promotes the use of method-chaining.
    """
    def inner(self, *args, **kwargs):
        clone = self.clone()  # Assumes object implements `clone`.
        func(clone, *args, **kwargs)
        return clone
    inner.call_local = func  # Provide a way to call without cloning.
    return inner

def not_allowed(func):
    """
    Method decorator to indicate a method is not allowed to be called.  Will
    raise a `NotImplementedError`.
    """
    def inner(self, *args, **kwargs):
        raise NotImplementedError('%s is not allowed on %s instances' % (
            func, type(self).__name__))
    return inner

class Proxy(object):
    """
    Proxy class useful for situations when you wish to defer the initialization
    of an object.
    """
    __slots__ = ['obj', '_callbacks']

    def __init__(self):
        self._callbacks = []
        self.initialize(None)

    def initialize(self, obj):
        self.obj = obj
        for callback in self._callbacks:
            callback(obj)

    def attach_callback(self, callback):
        self._callbacks.append(callback)

    def __getattr__(self, attr):
        if self.obj is None:
            raise AttributeError('Cannot use uninitialized Proxy.')
        return getattr(self.obj, attr)

    def __setattr__(self, attr, value):
        if attr not in self.__slots__:
            raise AttributeError('Cannot set attribute on proxy.')
        return super(Proxy, self).__setattr__(attr, value)

# Classes representing the query tree.

class Node(object):
    """Base-class for any part of a query which shall be composable."""
    def __init__(self):
        self._negated = False
        self._alias = None
        self._ordering = None  # ASC or DESC.

    def clone_base(self):
        return type(self)()

    def clone(self):
        inst = self.clone_base()
        inst._negated = self._negated
        inst._alias = self._alias
        inst._ordering = self._ordering
        return inst

    @returns_clone
    def __invert__(self):
        self._negated = not self._negated

    @returns_clone
    def alias(self, a=None):
        self._alias = a

    @returns_clone
    def asc(self):
        self._ordering = 'ASC'

    @returns_clone
    def desc(self):
        self._ordering = 'DESC'

    def _e(op, inv=False):
        """
        Lightweight factory which returns a method that builds an Expression
        consisting of the left-hand and right-hand operands, using `op`.
        """
        def inner(self, rhs):
            if inv:
                return Expression(rhs, op, self)
            return Expression(self, op, rhs)
        return inner
    __and__ = _e(OP_AND)
    __or__ = _e(OP_OR)

    __add__ = _e(OP_ADD)
    __sub__ = _e(OP_SUB)
    __mul__ = _e(OP_MUL)
    __div__ = _e(OP_DIV)
    __xor__ = _e(OP_XOR)
    __radd__ = _e(OP_ADD, inv=True)
    __rsub__ = _e(OP_SUB, inv=True)
    __rmul__ = _e(OP_MUL, inv=True)
    __rdiv__ = _e(OP_DIV, inv=True)
    __rand__ = _e(OP_AND, inv=True)
    __ror__ = _e(OP_OR, inv=True)
    __rxor__ = _e(OP_XOR, inv=True)

    def __eq__(self, rhs):
        if rhs is None:
            return Expression(self, OP_IS, None)
        return Expression(self, OP_EQ, rhs)
    def __ne__(self, rhs):
        if rhs is None:
            return ~Expression(self, OP_IS, None)
        return Expression(self, OP_NE, rhs)

    __lt__ = _e(OP_LT)
    __le__ = _e(OP_LTE)
    __gt__ = _e(OP_GT)
    __ge__ = _e(OP_GTE)
    __lshift__ = _e(OP_IN)
    __rshift__ = _e(OP_IS)
    __mod__ = _e(OP_LIKE)
    __pow__ = _e(OP_ILIKE)

    bin_and = _e(OP_BIN_AND)
    bin_or = _e(OP_BIN_OR)

    # Special expressions.
    def in_(self, *rhs):
        return Expression(self, OP_IN, rhs)
    def contains(self, rhs):
        return Expression(self, OP_ILIKE, '%%%s%%' % rhs)
    def startswith(self, rhs):
        return Expression(self, OP_ILIKE, '%s%%' % rhs)
    def endswith(self, rhs):
        return Expression(self, OP_ILIKE, '%%%s' % rhs)
    def between(self, low, high):
        return Expression(self, OP_BETWEEN, Clause(low, R('AND'), high))
    def regexp(self, expression):
        return Expression(self, OP_REGEXP, expression)

class Expression(Node):
    """A binary expression, e.g `foo + 1` or `bar < 7`."""
    def __init__(self, lhs, op, rhs, flat=False):
        super(Expression, self).__init__()
        self.lhs = lhs
        self.op = op
        self.rhs = rhs
        self.flat = flat

    def clone_base(self):
        return Expression(self.lhs, self.op, self.rhs, self.flat)

class DQ(Node):
    """A "django-style" filter expression, e.g. {'foo__eq': 'x'}."""
    def __init__(self, **query):
        super(DQ, self).__init__()
        self.query = query

    def clone_base(self):
        return DQ(**self.query)

class Param(Node):
    """
    Arbitrary parameter passed into a query. Instructs the query compiler to
    specifically treat this value as a parameter, useful for `list` which is
    special-cased for `IN` lookups.
    """
    def __init__(self, value, conv=None):
        self.value = value
        self.conv = conv
        super(Param, self).__init__()

    def clone_base(self):
        return Param(self.value, self.conv)

class SQL(Node):
    """An unescaped SQL string, with optional parameters."""
    def __init__(self, value, *params):
        self.value = value
        self.params = params
        super(SQL, self).__init__()

    def clone_base(self):
        return SQL(self.value, *self.params)
R = SQL  # backwards-compat.

class Func(Node):
    """An arbitrary SQL function call."""
    def __init__(self, name, *arguments):
        self.name = name
        self.arguments = arguments
        self._coerce = True
        super(Func, self).__init__()

    @returns_clone
    def coerce(self, coerce=True):
        self._coerce = coerce

    def clone_base(self):
        res = Func(self.name, *self.arguments)
        res._coerce = self._coerce
        return res

    def over(self, partition_by=None, order_by=None):
        # Basic window function support.
        over_clauses = []
        if partition_by:
            over_clauses.append(Clause(
                SQL('PARTITION BY'),
                CommaClause(*partition_by)))
        if order_by:
            over_clauses.append(Clause(
                SQL('ORDER BY'),
                CommaClause(*order_by)))
        return Clause(self, SQL('OVER'), EnclosedClause(Clause(*over_clauses)))

    def __getattr__(self, attr):
        def dec(*args, **kwargs):
            return Func(attr, *args, **kwargs)
        return dec

# fn is a factory for creating `Func` objects and supports a more friendly
# API.  So instead of `Func("LOWER", param)`, `fn.LOWER(param)`.
fn = Func(None)

class Clause(Node):
    """A SQL clause, one or more Node objects joined by spaces."""
    glue = ' '
    parens = False

    def __init__(self, *nodes):
        super(Clause, self).__init__()
        self.nodes = list(nodes)

    def clone_base(self):
        clone = Clause(*self.nodes)
        clone.glue = self.glue
        clone.parens = self.parens
        return clone

class CommaClause(Clause):
    """One or more Node objects joined by commas, no parens."""
    glue = ', '

class EnclosedClause(CommaClause):
    """One or more Node objects joined by commas and enclosed in parens."""
    parens = True

class Entity(Node):
    """A quoted-name or entity, e.g. "table"."column"."""
    def __init__(self, *path):
        super(Entity, self).__init__()
        self.path = path

    def clone_base(self):
        return Entity(*self.path)

    def __getattr__(self, attr):
        return Entity(*self.path + (attr,))

class Check(SQL):
    """Check constraint, usage: `Check('price > 10')`."""
    def __init__(self, value):
        super(Check, self).__init__('CHECK (%s)' % value)

Join = namedtuple('Join', ('dest', 'join_type', 'on'))

class FieldDescriptor(object):
    # Fields are exposed as descriptors in order to control access to the
    # underlying "raw" data.
    def __init__(self, field):
        self.field = field
        self.att_name = self.field.name

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            return instance._data.get(self.att_name)
        return self.field

    def __set__(self, instance, value):
        instance._data[self.att_name] = value
        instance._dirty.add(self.att_name)

class Field(Node):
    """A column on a table."""
    _field_counter = 0
    _order = 0
    db_field = 'unknown'

    def __init__(self, null=False, index=False, unique=False,
                 verbose_name=None, help_text=None, db_column=None,
                 default=None, choices=None, primary_key=False, sequence=None,
                 constraints=None, schema=None):
        self.null = null
        self.index = index
        self.unique = unique
        self.verbose_name = verbose_name
        self.help_text = help_text
        self.db_column = db_column
        self.default = default
        self.choices = choices  # Used for metadata purposes, not enforced.
        self.primary_key = primary_key
        self.sequence = sequence  # Name of sequence, e.g. foo_id_seq.
        self.constraints = constraints  # List of column constraints.
        self.schema = schema  # Name of schema, e.g. 'public'.

        # Used internally for recovering the order in which Fields were defined
        # on the Model class.
        Field._field_counter += 1
        self._order = Field._field_counter
        self._sort_key = (self.primary_key and 1 or 2), self._order

        self._is_bound = False  # Whether the Field is "bound" to a Model.
        super(Field, self).__init__()

    def clone_base(self, **kwargs):
        inst = type(self)(
            null=self.null,
            index=self.index,
            unique=self.unique,
            verbose_name=self.verbose_name,
            help_text=self.help_text,
            db_column=self.db_column,
            default=self.default,
            choices=self.choices,
            primary_key=self.primary_key,
            sequence=self.sequence,
            constraints=self.constraints,
            schema=self.schema,
            **kwargs)
        if self._is_bound:
            inst.name = self.name
            inst.model_class = self.model_class
            return inst

    def add_to_class(self, model_class, name):
        """
        Hook that replaces the `Field` attribute on a class with a named
        `FieldDescriptor`. Called by the metaclass during construction of the
        `Model`.
        """
        self.name = name
        self.model_class = model_class
        self.db_column = self.db_column or self.name
        if not self.verbose_name:
            self.verbose_name = re.sub('_+', ' ', name).title()

        model_class._meta.fields[self.name] = self
        model_class._meta.columns[self.db_column] = self

        setattr(model_class, name, FieldDescriptor(self))
        self._is_bound = True

    def get_database(self):
        return self.model_class._meta.database

    def get_column_type(self):
        field_type = self.get_db_field()
        return self.get_database().compiler().get_column_type(field_type)

    def get_db_field(self):
        return self.db_field

    def get_modifiers(self):
        return None

    def coerce(self, value):
        return value

    def db_value(self, value):
        """Convert the python value for storage in the database."""
        return value if value is None else self.coerce(value)

    def python_value(self, value):
        """Convert the database value to a pythonic value."""
        return value if value is None else self.coerce(value)

    def _as_entity(self, with_table=False):
        if with_table:
            return Entity(self.model_class._meta.db_table, self.db_column)
        return Entity(self.db_column)

    def __ddl_column__(self, column_type):
        """Return the column type, e.g. VARCHAR(255) or REAL."""
        modifiers = self.get_modifiers()
        if modifiers:
            return SQL(
                '%s(%s)' % (column_type, ', '.join(map(str, modifiers))))
        return SQL(column_type)

    def __ddl__(self, column_type):
        """Return a list of Node instances that defines the column."""
        ddl = [self._as_entity(), self.__ddl_column__(column_type)]
        if not self.null:
            ddl.append(SQL('NOT NULL'))
        if self.primary_key:
            ddl.append(SQL('PRIMARY KEY'))
        if self.sequence:
            ddl.append(SQL("DEFAULT NEXTVAL('%s')" % self.sequence))
        if self.constraints:
            ddl.extend(self.constraints)
        return ddl

    def __hash__(self):
        return hash(self.name + '.' + self.model_class.__name__)

class BareField(Field):
    db_field = 'bare'

class IntegerField(Field):
    db_field = 'int'
    coerce = int

class BigIntegerField(IntegerField):
    db_field = 'bigint'

class PrimaryKeyField(IntegerField):
    db_field = 'primary_key'

    def __init__(self, *args, **kwargs):
        kwargs['primary_key'] = True
        super(PrimaryKeyField, self).__init__(*args, **kwargs)

class FloatField(Field):
    db_field = 'float'
    coerce = float

class DoubleField(FloatField):
    db_field = 'double'

class DecimalField(Field):
    db_field = 'decimal'

    def __init__(self, max_digits=10, decimal_places=5, auto_round=False,
                 rounding=None, *args, **kwargs):
        self.max_digits = max_digits
        self.decimal_places = decimal_places
        self.auto_round = auto_round
        self.rounding = rounding or decimal.DefaultContext.rounding
        super(DecimalField, self).__init__(*args, **kwargs)

    def clone_base(self, **kwargs):
        return super(DecimalField, self).clone_base(
            max_digits=self.max_digits,
            decimal_places=self.decimal_places,
            auto_round=self.auto_round,
            rounding=self.rounding,
            **kwargs)

    def get_modifiers(self):
        return [self.max_digits, self.decimal_places]

    def db_value(self, value):
        D = decimal.Decimal
        if not value:
            return value if value is None else D(0)
        if self.auto_round:
            exp = D(10) ** (-self.decimal_places)
            rounding = self.rounding
            return D(str(value)).quantize(exp, rounding=rounding)
        return value

    def python_value(self, value):
        if value is not None:
            if isinstance(value, decimal.Decimal):
                return value
            return decimal.Decimal(str(value))

def coerce_to_unicode(s, encoding='utf-8'):
    if isinstance(s, unicode_type):
        return s
    elif isinstance(s, string_type):
        return s.decode(encoding)
    return unicode_type(s)

class CharField(Field):
    db_field = 'string'

    def __init__(self, max_length=255, *args, **kwargs):
        self.max_length = max_length
        super(CharField, self).__init__(*args, **kwargs)

    def clone_base(self, **kwargs):
        return super(CharField, self).clone_base(
            max_length=self.max_length,
            **kwargs)

    def get_modifiers(self):
        return self.max_length and [self.max_length] or None

    def coerce(self, value):
        return coerce_to_unicode(value or '')

class TextField(Field):
    db_field = 'text'

    def coerce(self, value):
        return coerce_to_unicode(value or '')

class BlobField(Field):
    db_field = 'blob'

    def db_value(self, value):
        if isinstance(value, basestring):
            return binary_construct(value)
        return value

def format_date_time(value, formats, post_process=None):
    post_process = post_process or (lambda x: x)
    for fmt in formats:
        try:
            return post_process(datetime.datetime.strptime(value, fmt))
        except ValueError:
            pass
    return value

def _date_part(date_part):
    def dec(self):
        return self.model_class._meta.database.extract_date(date_part, self)
    return dec

class _BaseFormattedField(Field):
    formats = None
    def __init__(self, formats=None, *args, **kwargs):
        if formats is not None:
            self.formats = formats
        super(_BaseFormattedField, self).__init__(*args, **kwargs)

    def clone_base(self, **kwargs):
        return super(_BaseFormattedField, self).clone_base(
            formats=self.formats,
            **kwargs)

class DateTimeField(_BaseFormattedField):
    db_field = 'datetime'
    formats = [
        '%Y-%m-%d %H:%M:%S.%f',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
    ]

    def python_value(self, value):
        if value and isinstance(value, basestring):
            return format_date_time(value, self.formats)
        return value

    year = property(_date_part('year'))
    month = property(_date_part('month'))
    day = property(_date_part('day'))
    hour = property(_date_part('hour'))
    minute = property(_date_part('minute'))
    second = property(_date_part('second'))

class DateField(_BaseFormattedField):
    db_field = 'date'
    formats = [
        '%Y-%m-%d',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M:%S.%f',
    ]

    def python_value(self, value):
        if value and isinstance(value, basestring):
            pp = lambda x: x.date()
            return format_date_time(value, self.formats, pp)
        elif value and isinstance(value, datetime.datetime):
            return value.date()
        return value

    year = property(_date_part('year'))
    month = property(_date_part('month'))
    day = property(_date_part('day'))

class TimeField(_BaseFormattedField):
    db_field = 'time'
    formats = [
        '%H:%M:%S.%f',
        '%H:%M:%S',
        '%H:%M',
        '%Y-%m-%d %H:%M:%S.%f',
        '%Y-%m-%d %H:%M:%S',
    ]

    def python_value(self, value):
        if value and isinstance(value, basestring):
            pp = lambda x: x.time()
            return format_date_time(value, self.formats, pp)
        elif value and isinstance(value, datetime.datetime):
            return value.time()
        return value

    hour = property(_date_part('hour'))
    minute = property(_date_part('minute'))
    second = property(_date_part('second'))

class BooleanField(Field):
    db_field = 'bool'
    coerce = bool

class RelationDescriptor(FieldDescriptor):
    """Foreign-key abstraction to replace a related PK with a related model."""
    def __init__(self, field, rel_model):
        self.rel_model = rel_model
        super(RelationDescriptor, self).__init__(field)

    def get_object_or_id(self, instance):
        rel_id = instance._data.get(self.att_name)
        if rel_id is not None or self.att_name in instance._obj_cache:
            if self.att_name not in instance._obj_cache:
                obj = self.rel_model.get(self.field.to_field == rel_id)
                instance._obj_cache[self.att_name] = obj
            return instance._obj_cache[self.att_name]
        elif not self.field.null:
            raise self.rel_model.DoesNotExist
        return rel_id

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            return self.get_object_or_id(instance)
        return self.field

    def __set__(self, instance, value):
        if isinstance(value, self.rel_model):
            instance._data[self.att_name] = getattr(
                value, self.field.to_field.name)
            instance._obj_cache[self.att_name] = value
        else:
            orig_value = instance._data.get(self.att_name)
            instance._data[self.att_name] = value
            if orig_value != value and self.att_name in instance._obj_cache:
                del instance._obj_cache[self.att_name]

class ReverseRelationDescriptor(object):
    """Back-reference to expose related objects as a `SelectQuery`."""
    def __init__(self, field):
        self.field = field
        self.rel_model = field.model_class

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            return self.rel_model.select().where(
                self.field == getattr(instance, self.field.to_field.name))
        return self

class ForeignKeyField(IntegerField):
    def __init__(self, rel_model, related_name=None, on_delete=None,
                 on_update=None, extra=None, to_field=None, *args, **kwargs):
        if rel_model != 'self' and not isinstance(rel_model, Proxy) and not \
                issubclass(rel_model, Model):
            raise TypeError('Unexpected value for `rel_model`.  Expected '
                            '`Model`, `Proxy` or "self"')
        self.rel_model = rel_model
        self._related_name = related_name
        self.deferred = isinstance(rel_model, Proxy)
        self.on_delete = on_delete
        self.on_update = on_update
        self.extra = extra
        self.to_field = to_field
        super(ForeignKeyField, self).__init__(*args, **kwargs)

    def clone_base(self, **kwargs):
        return super(ForeignKeyField, self).clone_base(
            rel_model=self.rel_model,
            related_name=self.related_name,
            on_delete=self.on_delete,
            on_update=self.on_update,
            extra=self.extra,
            to_field=self.to_field,
            **kwargs)

    def add_to_class(self, model_class, name):
        if isinstance(self.rel_model, Proxy):
            def callback(rel_model):
                self.rel_model = rel_model
                self.add_to_class(model_class, name)
            self.rel_model.attach_callback(callback)
            return

        self.name = name
        self.model_class = model_class
        self.db_column = self.db_column or '%s_id' % self.name
        if not self.verbose_name:
            self.verbose_name = re.sub('_+', ' ', name).title()

        model_class._meta.fields[self.name] = self
        model_class._meta.columns[self.db_column] = self

        model_name = model_class._meta.name
        self.related_name = self._related_name or '%s_set' % (model_name)

        if self.rel_model == 'self':
            self.rel_model = self.model_class

        if self.to_field is not None:
            if not isinstance(self.to_field, Field):
                self.to_field = getattr(self.rel_model, self.to_field)
        else:
            self.to_field = self.rel_model._meta.primary_key

        if self.related_name in self.rel_model._meta.fields:
            error = ('Foreign key: %s.%s related name "%s" collision with '
                     'model field of the same name.')
            params = self.model_class._meta.name, self.name, self.related_name
            raise AttributeError(error % params)
        if self.related_name in self.rel_model._meta.reverse_rel:
            error = ('Foreign key: %s.%s related name "%s" collision with '
                     'foreign key using same related_name.')
            params = self.model_class._meta.name, self.name, self.related_name
            raise AttributeError(error % params)

        fk_descriptor = RelationDescriptor(self, self.rel_model)
        backref_descriptor = ReverseRelationDescriptor(self)
        setattr(model_class, name, fk_descriptor)
        setattr(self.rel_model, self.related_name, backref_descriptor)
        self._is_bound = True

        model_class._meta.rel[self.name] = self
        self.rel_model._meta.reverse_rel[self.related_name] = self

    def get_db_field(self):
        """
        Overridden to ensure Foreign Keys use same column type as the primary
        key they point to.
        """
        if not isinstance(self.to_field, PrimaryKeyField):
            return self.to_field.get_db_field()
        return super(ForeignKeyField, self).get_db_field()

    def get_modifiers(self):
        if not isinstance(self.to_field, PrimaryKeyField):
            return self.to_field.get_modifiers()
        return super(ForeignKeyField, self).get_modifiers()

    def coerce(self, value):
        return self.to_field.coerce(value)

    def db_value(self, value):
        if isinstance(value, self.rel_model):
            value = value.get_id()
        return self.to_field.db_value(value)


class CompositeKey(object):
    """A primary key composed of multiple columns."""
    sequence = None

    def __init__(self, *field_names):
        self.field_names = field_names

    def add_to_class(self, model_class, name):
        self.name = name
        self.model_class = model_class
        setattr(model_class, name, self)

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            return [getattr(instance, field_name)
                    for field_name in self.field_names]
        return self

    def __set__(self, instance, value):
        pass

    def __eq__(self, other):
        expressions = [(self.model_class._meta.fields[field] == value)
                       for field, value in zip(self.field_names, other)]
        return reduce(operator.and_, expressions)


class QueryCompiler(object):
    # Mapping of `db_type` to actual column type used by database driver.
    # Database classes may provide additional column types or overrides.
    field_map = {
        'bare': '',
        'bigint': 'BIGINT',
        'blob': 'BLOB',
        'bool': 'SMALLINT',
        'date': 'DATE',
        'datetime': 'DATETIME',
        'decimal': 'DECIMAL',
        'double': 'REAL',
        'float': 'REAL',
        'int': 'INTEGER',
        'primary_key': 'INTEGER',
        'string': 'VARCHAR',
        'text': 'TEXT',
        'time': 'TIME',
    }

    # Mapping of OP_ to actual SQL operation.  For most databases this will be
    # the same, but some column types or databases may support additional ops.
    # Like `field_map`, Database classes may extend or override these.
    op_map = {
        OP_EQ: '=',
        OP_LT: '<',
        OP_LTE: '<=',
        OP_GT: '>',
        OP_GTE: '>=',
        OP_NE: '!=',
        OP_IN: 'IN',
        OP_IS: 'IS',
        OP_BIN_AND: '&',
        OP_BIN_OR: '|',
        OP_LIKE: 'LIKE',
        OP_ILIKE: 'ILIKE',
        OP_BETWEEN: 'BETWEEN',
        OP_ADD: '+',
        OP_SUB: '-',
        OP_MUL: '*',
        OP_DIV: '/',
        OP_XOR: '#',
        OP_AND: 'AND',
        OP_OR: 'OR',
        OP_MOD: '%',
        OP_REGEXP: 'REGEXP',
    }

    join_map = {
        JOIN_INNER: 'INNER',
        JOIN_LEFT_OUTER: 'LEFT OUTER',
        JOIN_FULL: 'FULL',
    }

    def __init__(self, quote_char='"', interpolation='?', field_overrides=None,
                 op_overrides=None):
        self.quote_char = quote_char
        self.interpolation = interpolation
        self._field_map = merge_dict(self.field_map, field_overrides or {})
        self._op_map = merge_dict(self.op_map, op_overrides or {})

    def quote(self, s):
        return '%s%s%s' % (self.quote_char, s, self.quote_char)

    def get_column_type(self, f):
        return self._field_map[f]

    def get_op(self, q):
        return self._op_map[q]

    def _sorted_fields(self, field_dict):
        return sorted(field_dict.items(), key=lambda i: i[0]._sort_key)

    def _max_alias(self, alias_map):
        max_alias = 0
        if alias_map:
            for alias in alias_map.values():
                try:
                    alias_number = int(alias.lstrip('t'))
                except ValueError:
                    alias_number = 0
                if alias_number > max_alias:
                    max_alias = alias_number
        return max_alias + 1

    def _ensure_alias_set(self, model, alias_map):
        if model not in alias_map:
            max_alias = self._max_alias(alias_map)
            alias_map[model] = 't%d' % max_alias

    def _parse(self, node, alias_map, conv):
        # By default treat the incoming node as a raw value that should be
        # parameterized.
        sql = self.interpolation
        params = [node]
        unknown = False
        if isinstance(node, Expression):
            if isinstance(node.lhs, Field):
                conv = node.lhs
            lhs, lparams = self.parse_node(node.lhs, alias_map, conv)
            rhs, rparams = self.parse_node(node.rhs, alias_map, conv)
            template = '%s %s %s' if node.flat else '(%s %s %s)'
            sql = template % (lhs, self.get_op(node.op), rhs)
            params = lparams + rparams
        elif isinstance(node, Field):
            sql = self.quote(node.db_column)
            if alias_map and node.model_class in alias_map:
                sql = '.'.join((alias_map[node.model_class], sql))
            params = []
        elif isinstance(node, Func):
            conv = node._coerce and conv or None
            sql, params = self.parse_node_list(node.arguments, alias_map, conv)
            sql = '%s(%s)' % (node.name, sql)
        elif isinstance(node, Clause):
            sql, params = self.parse_node_list(
                node.nodes, alias_map, conv, node.glue)
            if node.parens:
                sql = '(%s)' % sql
        elif isinstance(node, Param):
            if node.conv:
                params = [node.conv(node.value)]
            else:
                params = [node.value]
            unknown = True
        elif isinstance(node, SQL):
            sql = node.value
            params = list(node.params)
        elif isinstance(node, CompoundSelect):
            l, lp = self.generate_select(
                node.lhs, self._max_alias(alias_map), alias_map)
            r, rp = self.generate_select(
                node.rhs, self._max_alias(alias_map), alias_map)
            sql = '%s %s %s' % (l, node.operator, r)
            params = lp + rp
        elif isinstance(node, SelectQuery):
            max_alias = self._max_alias(alias_map)
            alias_copy = alias_map and alias_map.copy() or None
            clone = node.clone()
            if not node._explicit_selection:
                if conv and isinstance(conv, ForeignKeyField):
                    select_field = conv.to_field
                else:
                    select_field = clone.model_class._meta.primary_key
                clone._select = (select_field,)
            sub, params = self.generate_select(clone, max_alias, alias_copy)
            sql = '(%s)' % sub
        elif isinstance(node, (list, tuple)):
            # If you're wondering how to pass a list into your query, simply
            # wrap it in Param().
            sql, params = self.parse_node_list(node, alias_map, conv)
            sql = '(%s)' % sql
        elif isinstance(node, Entity):
            sql = '.'.join(map(self.quote, node.path))
            params = []
        elif isinstance(node, Model):
            sql = self.interpolation
            if conv and isinstance(conv, ForeignKeyField):
                params = [getattr(node, conv.to_field.name)]
            else:
                params = [node.get_id()]
        elif isclass(node) and issubclass(node, Model):
            self._ensure_alias_set(node, alias_map)
            entity = node._as_entity().alias(alias_map[node])
            sql, params = self.parse_node(entity, alias_map, conv)
        else:
            unknown = True
        return sql, params, unknown

    def parse_node(self, node, alias_map=None, conv=None):
        sql, params, unknown = self._parse(node, alias_map, conv)
        if unknown and conv and params:
            params = [conv.db_value(i) for i in params]

        if isinstance(node, Node):
            if node._negated:
                sql = 'NOT %s' % sql
            if node._alias:
                sql = ' '.join((sql, 'AS', node._alias))
            if node._ordering:
                sql = ' '.join((sql, node._ordering))
        return sql, params

    def parse_node_list(self, nodes, alias_map, conv=None, glue=', '):
        sql = []
        params = []
        for node in nodes:
            node_sql, node_params = self.parse_node(node, alias_map, conv)
            sql.append(node_sql)
            params.extend(node_params)
        return glue.join(sql), params

    def calculate_alias_map(self, query, start=1):
        make_alias = lambda model: model._meta.table_alias or 't%s' % start
        alias_map = {query.model_class: make_alias(query.model_class)}
        for dest, joins in query._joins.items():
            if dest not in alias_map:
                start += 1
                alias_map[dest] = make_alias(dest)
            for join in joins:
                if join.dest not in alias_map:
                    start += 1
                    alias_map[join.dest] = make_alias(join.dest)
        return alias_map

    def build_query(self, clauses, alias_map=None):
        return self.parse_node(Clause(*clauses), alias_map)

    def generate_joins(self, joins, model_class, alias_map):
        clauses = []
        seen = set()
        q = [model_class]
        while q:
            curr = q.pop()
            if curr not in joins or curr in seen:
                continue
            seen.add(curr)
            for join in joins[curr]:
                src = curr
                dest = join.dest
                if isinstance(join.on, Expression):
                    # Clear any alias on the join expression.
                    constraint = join.on.clone().alias()
                else:
                    field = src._meta.rel_for_model(dest, join.on)
                    if field:
                        left_field = field
                        right_field = field.to_field
                    else:
                        field = dest._meta.rel_for_model(src, join.on)
                        left_field = field.to_field
                        right_field = field
                    constraint = (left_field == right_field)

                if isinstance(dest, Node):
                    # TODO: ensure alias?
                    dest_n = dest
                else:
                    q.append(dest)
                    dest_n = dest._as_entity().alias(alias_map[dest])

                join_type = self.join_map[join.join_type or JOIN_INNER]
                join_stmt = SQL('%s JOIN' % (join_type))
                clauses.append(
                    Clause(join_stmt, dest_n, SQL('ON'), constraint))

        return clauses

    def generate_select(self, query, start=1, alias_map=None):
        model = query.model_class
        db = model._meta.database

        alias_map = alias_map or {}
        alias_map.update(self.calculate_alias_map(query, start))

        if isinstance(query, CompoundSelect):
            clauses = [query]
        else:
            stmt = 'SELECT DISTINCT' if query._distinct else 'SELECT'
            select_clause = Clause(*query._select)
            select_clause.glue = ', '

            clauses = [SQL(stmt), select_clause, SQL('FROM')]
            if query._from is None:
                clauses.append(model._as_entity().alias(alias_map[model]))
            else:
                clauses.append(CommaClause(*query._from))

        join_clauses = self.generate_joins(query._joins, model, alias_map)
        if join_clauses:
            clauses.extend(join_clauses)

        if query._where is not None:
            clauses.extend([SQL('WHERE'), query._where])

        if query._group_by:
            clauses.extend([SQL('GROUP BY'), CommaClause(*query._group_by)])

        if query._having:
            clauses.extend([SQL('HAVING'), query._having])

        if query._order_by:
            clauses.extend([SQL('ORDER BY'), CommaClause(*query._order_by)])

        if query._limit or (query._offset and db.limit_max):
            limit = query._limit or db.limit_max
            clauses.append(SQL('LIMIT %s' % limit))
        if query._offset:
            clauses.append(SQL('OFFSET %s' % query._offset))

        for_update, no_wait = query._for_update
        if for_update:
            stmt = 'FOR UPDATE NOWAIT' if no_wait else 'FOR UPDATE'
            clauses.append(SQL(stmt))

        return self.build_query(clauses, alias_map)

    def generate_update(self, query):
        model = query.model_class
        clauses = [SQL('UPDATE'), model._as_entity(), SQL('SET')]

        update = []
        for field, value in self._sorted_fields(query._update):
            if not isinstance(value, (Node, Model)):
                value = Param(value)
            update.append(Expression(field, OP_EQ, value, flat=True))
        clauses.append(CommaClause(*update))

        if query._where:
            clauses.extend([SQL('WHERE'), query._where])

        return self.build_query(clauses)

    def generate_insert(self, query):
        model = query.model_class
        statement = query._upsert and 'INSERT OR REPLACE INTO' or 'INSERT INTO'
        clauses = [SQL(statement), model._as_entity()]

        if query._rows is not None:
            fields, value_clauses = [], []
            have_fields = False

            for row_dict in query._iter_rows():
                if not have_fields:
                    fields = sorted(
                        row_dict.keys(), key=operator.attrgetter('_sort_key'))
                    have_fields = True

                values = []
                for field in fields:
                    value = row_dict[field]
                    if not isinstance(value, (Node, Model)):
                        value = Param(value, conv=field.db_value)
                    values.append(value)

                value_clauses.append(EnclosedClause(*values))

            if fields:
                clauses.extend([
                    EnclosedClause(*fields),
                    SQL('VALUES'),
                    CommaClause(*value_clauses)])

        return self.build_query(clauses)

    def generate_delete(self, query):
        model = query.model_class
        clauses = [SQL('DELETE FROM'), model._as_entity()]
        if query._where:
            clauses.extend([SQL('WHERE'), query._where])
        return self.build_query(clauses)

    def field_definition(self, field):
        column_type = self.get_column_type(field.get_db_field())
        ddl = field.__ddl__(column_type)
        return Clause(*ddl)

    def foreign_key_constraint(self, field):
        ddl = [
            SQL('FOREIGN KEY'),
            EnclosedClause(field._as_entity()),
            SQL('REFERENCES'),
            field.rel_model._as_entity(),
            EnclosedClause(field.to_field._as_entity())]
        if field.on_delete:
            ddl.append(SQL('ON DELETE %s' % field.on_delete))
        if field.on_update:
            ddl.append(SQL('ON UPDATE %s' % field.on_update))
        return Clause(*ddl)

    def return_parsed_node(function_name):
        # TODO: treat all `generate_` functions as returning clauses, instead
        # of SQL/params.
        def inner(self, *args, **kwargs):
            fn = getattr(self, function_name)
            return self.parse_node(fn(*args, **kwargs))
        return inner

    def _create_foreign_key(self, model_class, field, constraint=None):
        constraint = constraint or 'fk_%s_%s_refs_%s' % (
            model_class._meta.db_table,
            field.db_column,
            field.rel_model._meta.db_table)
        fk_clause = self.foreign_key_constraint(field)
        return Clause(
            SQL('ALTER TABLE'),
            model_class._as_entity(),
            SQL('ADD CONSTRAINT'),
            Entity(constraint),
            *fk_clause.nodes)
    create_foreign_key = return_parsed_node('_create_foreign_key')

    def _create_table(self, model_class, safe=False):
        statement = 'CREATE TABLE IF NOT EXISTS' if safe else 'CREATE TABLE'
        meta = model_class._meta

        columns, constraints = [], []
        if isinstance(meta.primary_key, CompositeKey):
            pk_cols = [meta.fields[f]._as_entity()
                       for f in meta.primary_key.field_names]
            constraints.append(Clause(
                SQL('PRIMARY KEY'), EnclosedClause(*pk_cols)))
        for field in meta.get_fields():
            columns.append(self.field_definition(field))
            if isinstance(field, ForeignKeyField) and not field.deferred:
                constraints.append(self.foreign_key_constraint(field))

        return Clause(
            SQL(statement),
            model_class._as_entity(),
            EnclosedClause(*(columns + constraints)))
    create_table = return_parsed_node('_create_table')

    def _drop_table(self, model_class, fail_silently=False, cascade=False):
        statement = 'DROP TABLE IF EXISTS' if fail_silently else 'DROP TABLE'
        ddl = [SQL(statement), model_class._as_entity()]
        if cascade:
            ddl.append(SQL('CASCADE'))
        return Clause(*ddl)
    drop_table = return_parsed_node('_drop_table')

    def index_name(self, table, columns):
        index = '%s_%s' % (table, '_'.join(columns))
        if len(index) > 64:
            index_hash = hashlib.md5(index.encode('utf-8')).hexdigest()
            index = '%s_%s' % (table, index_hash)
        return index

    def _create_index(self, model_class, fields, unique, *extra):
        tbl_name = model_class._meta.db_table
        statement = 'CREATE UNIQUE INDEX' if unique else 'CREATE INDEX'
        index_name = self.index_name(tbl_name, [f.db_column for f in fields])
        return Clause(
            SQL(statement),
            Entity(index_name),
            SQL('ON'),
            model_class._as_entity(),
            EnclosedClause(*[field._as_entity() for field in fields]),
            *extra)
    create_index = return_parsed_node('_create_index')

    def _create_sequence(self, sequence_name):
        return Clause(SQL('CREATE SEQUENCE'), Entity(sequence_name))
    create_sequence = return_parsed_node('_create_sequence')

    def _drop_sequence(self, sequence_name):
        return Clause(SQL('DROP SEQUENCE'), Entity(sequence_name))
    drop_sequence = return_parsed_node('_drop_sequence')


class QueryResultWrapper(object):
    """
    Provides an iterator over the results of a raw Query, additionally doing
    two things:
    - converts rows from the database into python representations
    - ensures that multiple iterations do not result in multiple queries
    """
    def __init__(self, model, cursor, meta=None):
        self.model = model
        self.cursor = cursor

        self.__ct = 0
        self.__idx = 0

        self._result_cache = []
        self._populated = False
        self._initialized = False

        if meta is not None:
            self.column_meta, self.join_meta = meta
        else:
            self.column_meta = self.join_meta = None

    def __iter__(self):
        self.__idx = 0

        if not self._populated:
            return self
        else:
            return iter(self._result_cache)

    def process_row(self, row):
        return row

    def iterate(self):
        row = self.cursor.fetchone()
        if not row:
            self._populated = True
            raise StopIteration
        elif not self._initialized:
            self.initialize(self.cursor.description)
            self._initialized = True
        return self.process_row(row)

    def iterator(self):
        while True:
            yield self.iterate()

    def next(self):
        if self.__idx < self.__ct:
            inst = self._result_cache[self.__idx]
            self.__idx += 1
            return inst

        obj = self.iterate()
        self._result_cache.append(obj)
        self.__ct += 1
        self.__idx += 1
        return obj
    __next__ = next

    def fill_cache(self, n=None):
        n = n or float('Inf')
        if n < 0:
            raise ValueError('Negative values are not supported.')
        self.__idx = self.__ct
        while not self._populated and (n > self.__ct):
            try:
                self.next()
            except StopIteration:
                break

class ExtQueryResultWrapper(QueryResultWrapper):
    def initialize(self, description):
        model = self.model
        conv = []
        identity = lambda x: x
        for i in range(len(description)):
            func = identity
            column = description[i][0]
            found = False
            if self.column_meta is not None:
                select_column = self.column_meta[i]
                if isinstance(select_column, Field):
                    func = select_column.python_value
                    column = select_column._alias or select_column.name
                    found = True
                elif (isinstance(select_column, Func) and
                        isinstance(select_column.arguments[0], Field)):
                    if select_column._coerce:
                        # Special-case handling aggregations.
                        func = select_column.arguments[0].python_value
                    found = True

            if not found and column in model._meta.columns:
                field_obj = model._meta.columns[column]
                column = field_obj.name
                func = field_obj.python_value

            conv.append((i, column, func))
        self.conv = conv

class TuplesQueryResultWrapper(ExtQueryResultWrapper):
    def process_row(self, row):
        return tuple([self.conv[i][2](col) for i, col in enumerate(row)])

class NaiveQueryResultWrapper(ExtQueryResultWrapper):
    def process_row(self, row):
        instance = self.model()
        for i, column, func in self.conv:
            setattr(instance, column, func(row[i]))
        instance.prepared()
        return instance

class DictQueryResultWrapper(ExtQueryResultWrapper):
    def process_row(self, row):
        res = {}
        for i, column, func in self.conv:
            res[column] = func(row[i])
        return res

class ModelQueryResultWrapper(QueryResultWrapper):
    def initialize(self, description):
        column_map = []
        join_map = []
        models = set([self.model])
        for i, node in enumerate(self.column_meta):
            attr = conv = None
            if isinstance(node, Field):
                if isinstance(node, FieldProxy):
                    key = node._model_alias
                    constructor = node.model
                else:
                    key = constructor = node.model_class
                attr = node.name
                conv = node.python_value
            else:
                key = constructor = self.model
                if isinstance(node, Expression) and node._alias:
                    attr = node._alias
            column_map.append((key, constructor, attr, conv))
            models.add(key)

        joins = self.join_meta
        stack = [self.model]
        while stack:
            current = stack.pop()
            if current not in joins:
                continue

            for join in joins[current]:
                join_model = join.dest
                if join_model in models:
                    fk_field = current._meta.rel_for_model(join_model)
                    to_field = None
                    if not fk_field:
                        if isinstance(join.on, Expression):
                            fk_name = join.on._alias or join.on.lhs.name
                        else:
                            # Patch the joined model using the name of the
                            # database table.
                            fk_name = join_model._meta.db_table
                    else:
                        fk_name = fk_field.name
                        to_field = fk_field.to_field.name

                    stack.append(join_model)
                    join_map.append((current, fk_name, join_model, to_field))

        self.column_map, self.join_map = column_map, join_map

    def process_row(self, row):
        collected = self.construct_instance(row)
        instances = self.follow_joins(collected)
        for i in instances:
            i.prepared()
        return instances[0]

    def construct_instance(self, row):
        collected_models = {}
        for i, (key, constructor, attr, conv) in enumerate(self.column_map):
            value = row[i]
            if key not in collected_models:
                collected_models[key] = constructor()
            instance = collected_models[key]
            if attr is None:
                attr = self.cursor.description[i][0]
            if conv is not None:
                value = conv(value)
            setattr(instance, attr, value)

        return collected_models

    def follow_joins(self, collected):
        prepared = [collected[self.model]]
        for (lhs, attr, rhs, to_field) in self.join_map:
            inst = collected[lhs]
            joined_inst = collected[rhs]

            # Can we populate a value on the joined instance using the current?
            if to_field is not None and attr in inst._data:
                if getattr(joined_inst, to_field) is None:
                    setattr(joined_inst, to_field, inst._data[attr])

            setattr(inst, attr, joined_inst)
            prepared.append(joined_inst)

        return prepared


class Query(Node):
    """Base class representing a database query on one or more tables."""
    require_commit = True

    def __init__(self, model_class):
        super(Query, self).__init__()

        self.model_class = model_class
        self.database = model_class._meta.database

        self._dirty = True
        self._query_ctx = model_class
        self._joins = {self.model_class: []}  # Join graph as adjacency list.
        self._where = None

    def __repr__(self):
        sql, params = self.sql()
        return '%s %s %s' % (self.model_class, sql, params)

    def clone(self):
        query = type(self)(self.model_class)
        query.database = self.database
        return self._clone_attributes(query)

    def _clone_attributes(self, query):
        if self._where is not None:
            query._where = self._where.clone()
        query._joins = self._clone_joins()
        query._query_ctx = self._query_ctx
        return query

    def _clone_joins(self):
        return dict(
            (mc, list(j)) for mc, j in self._joins.items())

    def _add_query_clauses(self, initial, expressions):
        reduced = reduce(operator.and_, expressions)
        if initial is None:
            return reduced
        return initial & reduced

    @returns_clone
    def where(self, *expressions):
        self._where = self._add_query_clauses(self._where, expressions)

    @returns_clone
    def join(self, model_class, join_type=None, on=None):
        if not self._query_ctx._meta.rel_exists(model_class) and on is None:
            raise ValueError('No foreign key between %s and %s' % (
                self._query_ctx, model_class))
        if on and isinstance(on, basestring):
            on = self._query_ctx._meta.fields[on]
        self._joins.setdefault(self._query_ctx, [])
        self._joins[self._query_ctx].append(Join(model_class, join_type, on))
        self._query_ctx = model_class

    @returns_clone
    def switch(self, model_class=None):
        """Change or reset the query context."""
        self._query_ctx = model_class or self.model_class

    def ensure_join(self, lm, rm, on=None):
        ctx = self._query_ctx
        for join in self._joins.get(lm, []):
            if join.dest == rm:
                return self
        return self.switch(lm).join(rm, on=on).switch(ctx)

    def convert_dict_to_node(self, qdict):
        accum = []
        joins = []
        relationship = (ForeignKeyField, ReverseRelationDescriptor)
        for key, value in sorted(qdict.items()):
            curr = self.model_class
            if '__' in key and key.rsplit('__', 1)[1] in DJANGO_MAP:
                key, op = key.rsplit('__', 1)
                op = DJANGO_MAP[op]
            else:
                op = OP_EQ
            for piece in key.split('__'):
                model_attr = getattr(curr, piece)
                if isinstance(model_attr, relationship):
                    curr = model_attr.rel_model
                    joins.append(model_attr)
            accum.append(Expression(model_attr, op, value))
        return accum, joins

    def filter(self, *args, **kwargs):
        # normalize args and kwargs into a new expression
        dq_node = Node()
        if args:
            dq_node &= reduce(operator.and_, [a.clone() for a in args])
        if kwargs:
            dq_node &= DQ(**kwargs)

        # dq_node should now be an Expression, lhs = Node(), rhs = ...
        q = deque([dq_node])
        dq_joins = set()
        while q:
            curr = q.popleft()
            if not isinstance(curr, Expression):
                continue
            for side, piece in (('lhs', curr.lhs), ('rhs', curr.rhs)):
                if isinstance(piece, DQ):
                    query, joins = self.convert_dict_to_node(piece.query)
                    dq_joins.update(joins)
                    expression = reduce(operator.and_, query)
                    # Apply values from the DQ object.
                    expression._negated = piece._negated
                    expression._alias = piece._alias
                    setattr(curr, side, expression)
                else:
                    q.append(piece)

        dq_node = dq_node.rhs

        query = self.clone()
        for field in dq_joins:
            if isinstance(field, ForeignKeyField):
                lm, rm = field.model_class, field.rel_model
                field_obj = field
            elif isinstance(field, ReverseRelationDescriptor):
                lm, rm = field.field.rel_model, field.rel_model
                field_obj = field.field
            query = query.ensure_join(lm, rm, field_obj)
        return query.where(dq_node)

    def compiler(self):
        return self.database.compiler()

    def sql(self):
        raise NotImplementedError

    def _execute(self):
        sql, params = self.sql()
        return self.database.execute_sql(sql, params, self.require_commit)

    def execute(self):
        raise NotImplementedError

    def scalar(self, as_tuple=False, convert=False):
        if convert:
            row = self.tuples().first()
        else:
            row = self._execute().fetchone()
        if row and not as_tuple:
            return row[0]
        else:
            return row

class RawQuery(Query):
    """
    Execute a SQL query, returning a standard iterable interface that returns
    model instances.
    """
    def __init__(self, model, query, *params):
        self._sql = query
        self._params = list(params)
        self._qr = None
        self._tuples = False
        self._dicts = False
        super(RawQuery, self).__init__(model)

    def clone(self):
        query = RawQuery(self.model_class, self._sql, *self._params)
        query._tuples = self._tuples
        query._dicts = self._dicts
        return query

    join = not_allowed('joining')
    where = not_allowed('where')
    switch = not_allowed('switch')

    @returns_clone
    def tuples(self, tuples=True):
        self._tuples = tuples

    @returns_clone
    def dicts(self, dicts=True):
        self._dicts = dicts

    def sql(self):
        return self._sql, self._params

    def execute(self):
        if self._qr is None:
            if self._tuples:
                ResultWrapper = TuplesQueryResultWrapper
            elif self._dicts:
                ResultWrapper = DictQueryResultWrapper
            else:
                ResultWrapper = NaiveQueryResultWrapper
            self._qr = ResultWrapper(self.model_class, self._execute(), None)
        return self._qr

    def __iter__(self):
        return iter(self.execute())

class SelectQuery(Query):
    def __init__(self, model_class, *selection):
        super(SelectQuery, self).__init__(model_class)
        self.require_commit = self.database.commit_select
        self.__select(*selection)
        self._from = None
        self._group_by = None
        self._having = None
        self._order_by = None
        self._limit = None
        self._offset = None
        self._distinct = False
        self._for_update = (False, False)
        self._naive = False
        self._tuples = False
        self._dicts = False
        self._alias = None
        self._qr = None

    def _clone_attributes(self, query):
        query = super(SelectQuery, self)._clone_attributes(query)
        query._explicit_selection = self._explicit_selection
        query._select = list(self._select)
        if self._from is not None:
            query._from = []
            for f in self._from:
                if isinstance(f, Node):
                    query._from.append(f.clone())
                else:
                    query._from.append(f)
        if self._group_by is not None:
            query._group_by = list(self._group_by)
        if self._having:
            query._having = self._having.clone()
        if self._order_by is not None:
            query._order_by = list(self._order_by)
        query._limit = self._limit
        query._offset = self._offset
        query._distinct = self._distinct
        query._for_update = self._for_update
        query._naive = self._naive
        query._tuples = self._tuples
        query._dicts = self._dicts
        query._alias = self._alias
        return query

    def _model_shorthand(self, args):
        accum = []
        for arg in args:
            if isinstance(arg, Node):
                accum.append(arg)
            elif isinstance(arg, Query):
                accum.append(arg)
            elif isinstance(arg, ModelAlias):
                accum.extend(arg.get_proxy_fields())
            elif isclass(arg) and issubclass(arg, Model):
                accum.extend(arg._meta.get_fields())
        return accum

    def compound_op(operator):
        def inner(self, other):
            supported_ops = self.model_class._meta.database.compound_operations
            if operator not in supported_ops:
                raise ValueError(
                    'Your database does not support %s' % operator)
            return CompoundSelect(self.model_class, self, operator, other)
        return inner
    __or__ = compound_op('UNION')
    __and__ = compound_op('INTERSECT')
    __sub__ = compound_op('EXCEPT')

    def __xor__(self, rhs):
        # Symmetric difference, should just be (self | rhs) - (self & rhs)...
        wrapped_rhs = self.model_class.select(SQL('*')).from_(
            EnclosedClause((self & rhs)).alias('_')).order_by()
        return (self | rhs) - wrapped_rhs

    def __select(self, *selection):
        self._explicit_selection = len(selection) > 0
        selection = selection or self.model_class._meta.get_fields()
        self._select = self._model_shorthand(selection)
    select = returns_clone(__select)

    @returns_clone
    def from_(self, *args):
        self._from = None
        if args:
            self._from = list(args)

    @returns_clone
    def group_by(self, *args):
        self._group_by = self._model_shorthand(args)

    @returns_clone
    def having(self, *expressions):
        self._having = self._add_query_clauses(self._having, expressions)

    @returns_clone
    def order_by(self, *args):
        self._order_by = list(args)

    @returns_clone
    def limit(self, lim):
        self._limit = lim

    @returns_clone
    def offset(self, off):
        self._offset = off

    @returns_clone
    def paginate(self, page, paginate_by=20):
        if page > 0:
            page -= 1
        self._limit = paginate_by
        self._offset = page * paginate_by

    @returns_clone
    def distinct(self, is_distinct=True):
        self._distinct = is_distinct

    @returns_clone
    def for_update(self, for_update=True, nowait=False):
        self._for_update = (for_update, nowait)

    @returns_clone
    def naive(self, naive=True):
        self._naive = naive

    @returns_clone
    def tuples(self, tuples=True):
        self._tuples = tuples

    @returns_clone
    def dicts(self, dicts=True):
        self._dicts = dicts

    @returns_clone
    def alias(self, alias=None):
        self._alias = alias

    def annotate(self, rel_model, annotation=None):
        if annotation is None:
            annotation = fn.Count(rel_model._meta.primary_key).alias('count')
        query = self.clone()
        query = query.ensure_join(query._query_ctx, rel_model)
        if not query._group_by:
            query._group_by = [x.alias() for x in query._select]
        query._select = tuple(query._select) + (annotation,)
        return query

    def _aggregate(self, aggregation=None):
        if aggregation is None:
            aggregation = fn.Count(self.model_class._meta.primary_key)
        query = self.order_by()
        query._select = [aggregation]
        return query

    def aggregate(self, aggregation=None, convert=True):
        return self._aggregate(aggregation).scalar(convert=convert)

    def count(self):
        if self._distinct or self._group_by:
            return self.wrapped_count()

        # defaults to a count() of the primary key
        return self.aggregate(convert=False) or 0

    def wrapped_count(self, clear_limit=True):
        clone = self.order_by()
        if clear_limit:
            clone._limit = clone._offset = None

        sql, params = clone.sql()
        wrapped = 'SELECT COUNT(1) FROM (%s) AS wrapped_select' % sql
        rq = self.model_class.raw(wrapped, *params)
        return rq.scalar() or 0

    def exists(self):
        clone = self.paginate(1, 1)
        clone._select = [SQL('1')]
        return bool(clone.scalar())

    def get(self):
        clone = self.paginate(1, 1)
        try:
            return clone.execute().next()
        except StopIteration:
            raise self.model_class.DoesNotExist(
                'Instance matching query does not exist:\nSQL: %s\nPARAMS: %s'
                % self.sql())

    def first(self):
        res = self.execute()
        res.fill_cache(1)
        try:
            return res._result_cache[0]
        except IndexError:
            pass

    def sql(self):
        return self.compiler().generate_select(self)

    def verify_naive(self):
        model_class = self.model_class
        for node in self._select:
            if isinstance(node, Field) and node.model_class != model_class:
                return False
        return True

    def get_query_meta(self):
        return (self._select, self._joins)

    def execute(self):
        if self._dirty or not self._qr:
            model_class = self.model_class
            query_meta = self.get_query_meta()
            if self._tuples:
                ResultWrapper = TuplesQueryResultWrapper
            elif self._dicts:
                ResultWrapper = DictQueryResultWrapper
            elif self._naive or not self._joins or self.verify_naive():
                ResultWrapper = NaiveQueryResultWrapper
            else:
                ResultWrapper = ModelQueryResultWrapper
            self._qr = ResultWrapper(model_class, self._execute(), query_meta)
            self._dirty = False
            return self._qr
        else:
            return self._qr

    def __iter__(self):
        return iter(self.execute())

    def iterator(self):
        return iter(self.execute().iterator())

    def __getitem__(self, value):
        res = self.execute()
        if isinstance(value, slice):
            index = value.stop
        else:
            index = value
        if index is not None and index >= 0:
            index += 1
        res.fill_cache(index)
        return res._result_cache[value]

class CompoundSelect(SelectQuery):
    def __init__(self, model_class, lhs=None, operator=None, rhs=None):
        self.lhs = lhs
        self.operator = operator
        self.rhs = rhs
        super(CompoundSelect, self).__init__(model_class, [])

    def _clone_attributes(self, query):
        query = super(CompoundSelect, self)._clone_attributes(query)
        query.lhs = self.lhs
        query.operator = self.operator
        query.rhs = self.rhs
        return query

    def get_query_meta(self):
        return self.lhs.get_query_meta()


class UpdateQuery(Query):
    def __init__(self, model_class, update=None):
        self._update = update
        super(UpdateQuery, self).__init__(model_class)

    def _clone_attributes(self, query):
        query = super(UpdateQuery, self)._clone_attributes(query)
        query._update = dict(self._update)
        return query

    join = not_allowed('joining')

    def sql(self):
        return self.compiler().generate_update(self)

    def execute(self):
        return self.database.rows_affected(self._execute())

class InsertQuery(Query):
    def __init__(self, model_class, field_dict=None, rows=None):
        super(InsertQuery, self).__init__(model_class)
        self._is_multi_row_insert = rows is not None
        if rows is not None:
            self._rows = rows
        else:
            self._rows = [field_dict or {}]
        self._defaults = self._get_default_values()
        self._upsert = False
        self._valid_fields = (set(model_class._meta.fields.keys()) |
                              set(model_class._meta.fields.values()))

    def _get_default_values(self):
        defaults = self.model_class._meta.get_default_dict()
        return dict(
            (self.model_class._meta.fields[f], v) for f, v in defaults.items())

    def _iter_rows(self):
        # Convert {'field_name': value} to {FieldName: value} / apply defaults.
        for row_dict in self._rows:
            field_row = {}
            field_row.update(self._defaults)
            for key in row_dict:
                if key not in self._valid_fields:
                    raise KeyError('"%s" is not a recognized field.' % key)
                elif key in self.model_class._meta.fields:
                    field = self.model_class._meta.fields[key]
                else:
                    field = key
                field_row[field] = row_dict[key]
            yield field_row

    def _clone_attributes(self, query):
        query = super(InsertQuery, self)._clone_attributes(query)
        query._rows = self._rows
        query._upsert = self._upsert
        query._is_multi_row_insert = self._is_multi_row_insert
        return query

    join = not_allowed('joining')
    where = not_allowed('where clause')

    @returns_clone
    def upsert(self, upsert=True):
        self._upsert = upsert

    def sql(self):
        return self.compiler().generate_insert(self)

    def execute(self):
        if not self.database.insert_many and self._is_multi_row_insert:
            last_id = None
            for row in self._rows:
                last_id = InsertQuery(self.model_class, row).execute()
            return last_id
        return self.database.last_insert_id(self._execute(), self.model_class)

class DeleteQuery(Query):
    join = not_allowed('joining')

    def sql(self):
        return self.compiler().generate_delete(self)

    def execute(self):
        return self.database.rows_affected(self._execute())


class PeeweeException(Exception): pass
class ImproperlyConfigured(PeeweeException): pass
class DatabaseError(PeeweeException): pass
class DataError(DatabaseError): pass
class IntegrityError(DatabaseError): pass
class InterfaceError(PeeweeException): pass
class InternalError(DatabaseError): pass
class NotSupportedError(DatabaseError): pass
class OperationalError(DatabaseError): pass
class ProgrammingError(DatabaseError): pass


class ExceptionWrapper(object):
    __slots__ = ['exceptions']

    def __init__(self, exceptions):
        self.exceptions = exceptions

    def __enter__(self): pass
    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            return
        if exc_type.__name__ in self.exceptions:
            new_type = self.exceptions[exc_type.__name__]
            reraise(new_type, new_type(*exc_value.args), traceback)


class Database(object):
    commit_select = False
    compiler_class = QueryCompiler
    compound_operations = ['UNION', 'INTERSECT', 'EXCEPT']
    drop_cascade = True
    field_overrides = {}
    foreign_keys = True
    for_update = False
    for_update_nowait = False
    insert_many = True
    interpolation = '?'
    limit_max = None
    op_overrides = {}
    quote_char = '"'
    reserved_tables = []
    savepoints = True
    sequences = False
    subquery_delete_same_table = True
    window_functions = False

    exceptions = {
        'DatabaseError': DatabaseError,
        'DataError': DataError,
        'IntegrityError': IntegrityError,
        'InterfaceError': InterfaceError,
        'InternalError': InternalError,
        'NotSupportedError': NotSupportedError,
        'OperationalError': OperationalError,
        'ProgrammingError': ProgrammingError}

    def __init__(self, database, threadlocals=False, autocommit=True,
                 fields=None, ops=None, autorollback=False, **connect_kwargs):
        self.init(database, **connect_kwargs)

        if threadlocals:
            self.__local = threading.local()
        else:
            self.__local = type('DummyLocal', (object,), {})

        self._conn_lock = threading.Lock()
        self.autocommit = autocommit
        self.autorollback = autorollback

        self.field_overrides = merge_dict(self.field_overrides, fields or {})
        self.op_overrides = merge_dict(self.op_overrides, ops or {})

    def init(self, database, **connect_kwargs):
        self.deferred = database is None
        self.database = database
        self.connect_kwargs = connect_kwargs

    def exception_wrapper(self):
        return ExceptionWrapper(self.exceptions)

    def connect(self):
        with self._conn_lock:
            if self.deferred:
                raise Exception('Error, database not properly initialized '
                                'before opening connection')
            with self.exception_wrapper():
                self.__local.conn = self._connect(
                    self.database,
                    **self.connect_kwargs)
                self.__local.closed = False

    def close(self):
        with self._conn_lock:
            if self.deferred:
                raise Exception('Error, database not properly initialized '
                                'before closing connection')
            with self.exception_wrapper():
                self._close(self.__local.conn)
                self.__local.closed = True

    def get_conn(self):
        if not hasattr(self.__local, 'closed') or self.__local.closed:
            self.connect()
        return self.__local.conn

    def is_closed(self):
        return getattr(self.__local, 'closed', True)

    def get_cursor(self):
        return self.get_conn().cursor()

    def _close(self, conn):
        conn.close()

    def _connect(self, database, **kwargs):
        raise NotImplementedError

    @classmethod
    def register_fields(cls, fields):
        cls.field_overrides = merge_dict(cls.field_overrides, fields)

    @classmethod
    def register_ops(cls, ops):
        cls.op_overrides = merge_dict(cls.op_overrides, ops)

    def last_insert_id(self, cursor, model):
        if model._meta.auto_increment:
            return cursor.lastrowid

    def rows_affected(self, cursor):
        return cursor.rowcount

    def sql_error_handler(self, exception, sql, params, require_commit):
        return True

    def compiler(self):
        return self.compiler_class(
            self.quote_char, self.interpolation, self.field_overrides,
            self.op_overrides)

    def execute_sql(self, sql, params=None, require_commit=True):
        logger.debug((sql, params))
        with self.exception_wrapper():
            cursor = self.get_cursor()
            try:
                cursor.execute(sql, params or ())
            except Exception as exc:
                if self.get_autocommit() and self.autorollback:
                    self.rollback()
                if self.sql_error_handler(exc, sql, params, require_commit):
                    raise
            else:
                if require_commit and self.get_autocommit():
                    self.commit()
        return cursor

    def begin(self):
        pass

    def commit(self):
        self.get_conn().commit()

    def rollback(self):
        self.get_conn().rollback()

    def set_autocommit(self, autocommit):
        self.__local.autocommit = autocommit

    def get_autocommit(self):
        if not hasattr(self.__local, 'autocommit'):
            self.set_autocommit(self.autocommit)
        return self.__local.autocommit

    def push_transaction(self, transaction):
        if not hasattr(self.__local, 'transactions'):
            self.__local.transactions = []
        self.__local.transactions.append(transaction)

    def pop_transaction(self):
        self.__local.transactions.pop()

    def transaction_depth(self):
        return len(getattr(self.__local, 'transactions', ()))

    def transaction(self):
        return transaction(self)

    def commit_on_success(self, func):
        @wraps(func)
        def inner(*args, **kwargs):
            with self.transaction():
                return func(*args, **kwargs)
        return inner

    def savepoint(self, sid=None):
        if not self.savepoints:
            raise NotImplementedError
        return savepoint(self, sid)

    def get_tables(self):
        raise NotImplementedError

    def get_indexes_for_table(self, table):
        raise NotImplementedError

    def sequence_exists(self, seq):
        raise NotImplementedError

    def create_table(self, model_class, safe=False):
        qc = self.compiler()
        return self.execute_sql(*qc.create_table(model_class, safe))

    def create_index(self, model_class, fields, unique=False):
        qc = self.compiler()
        if not isinstance(fields, (list, tuple)):
            raise ValueError('Fields passed to "create_index" must be a list '
                             'or tuple: "%s"' % fields)
        fobjs = [
            model_class._meta.fields[f] if isinstance(f, basestring) else f
            for f in fields]
        return self.execute_sql(*qc.create_index(model_class, fobjs, unique))

    def create_foreign_key(self, model_class, field, constraint=None):
        qc = self.compiler()
        return self.execute_sql(*qc.create_foreign_key(
            model_class, field, constraint))

    def create_sequence(self, seq):
        if self.sequences:
            qc = self.compiler()
            return self.execute_sql(*qc.create_sequence(seq))

    def drop_table(self, model_class, fail_silently=False, cascade=False):
        qc = self.compiler()
        return self.execute_sql(*qc.drop_table(
            model_class, fail_silently, cascade))

    def drop_sequence(self, seq):
        if self.sequences:
            qc = self.compiler()
            return self.execute_sql(*qc.drop_sequence(seq))

    def extract_date(self, date_part, date_field):
        return fn.EXTRACT(Clause(date_part, R('FROM'), date_field))

    def truncate_date(self, date_part, date_field):
        return fn.DATE_TRUNC(SQL(date_part), date_field)

class SqliteDatabase(Database):
    drop_cascade = False
    foreign_keys = False
    insert_many = sqlite3.sqlite_version_info >= (3, 7, 11, 0)
    limit_max = -1
    op_overrides = {
        OP_LIKE: 'GLOB',
        OP_ILIKE: 'LIKE',
    }

    def _connect(self, database, **kwargs):
        conn = sqlite3.connect(database, **kwargs)
        self._add_conn_hooks(conn)
        return conn

    def _add_conn_hooks(self, conn):
        conn.create_function('date_part', 2, _sqlite_date_part)
        conn.create_function('date_trunc', 2, _sqlite_date_trunc)
        conn.create_function('regexp', 2, _sqlite_regexp)

    def get_indexes_for_table(self, table):
        res = self.execute_sql('PRAGMA index_list(%s);' % self.quote(table))
        rows = sorted([(r[1], r[2] == 1) for r in res.fetchall()])
        return rows

    def get_tables(self):
        res = self.execute_sql('select name from sqlite_master where '
                               'type="table" order by name;')
        return [r[0] for r in res.fetchall()]

    def savepoint(self, sid=None):
        return savepoint_sqlite(self, sid)

    def extract_date(self, date_part, date_field):
        return fn.date_part(date_part, date_field)

    def truncate_date(self, date_part, date_field):
        return fn.strftime(SQLITE_DATE_TRUNC_MAPPING[date_part], date_field)

class PostgresqlDatabase(Database):
    commit_select = True
    field_overrides = {
        'blob': 'BYTEA',
        'bool': 'BOOLEAN',
        'datetime': 'TIMESTAMP',
        'decimal': 'NUMERIC',
        'double': 'DOUBLE PRECISION',
        'primary_key': 'SERIAL',
    }
    for_update = True
    for_update_nowait = True
    interpolation = '%s'
    op_overrides = {
        OP_REGEXP: '~',
    }
    reserved_tables = ['user']
    sequences = True
    window_functions = True

    register_unicode = True

    def _connect(self, database, **kwargs):
        if not psycopg2:
            raise ImproperlyConfigured('psycopg2 must be installed.')
        conn = psycopg2.connect(database=database, **kwargs)
        if self.register_unicode:
            pg_extensions.register_type(pg_extensions.UNICODE, conn)
            pg_extensions.register_type(pg_extensions.UNICODEARRAY, conn)
        return conn

    def last_insert_id(self, cursor, model):
        meta = model._meta
        schema = ''
        if meta.schema:
            schema = '%s.' % meta.schema

        if meta.primary_key.sequence:
            seq = meta.primary_key.sequence
        elif meta.auto_increment:
            seq = '%s_%s_seq' % (meta.db_table, meta.primary_key.db_column)
        else:
            seq = None

        if seq:
            cursor.execute("SELECT CURRVAL('%s\"%s\"')" % (schema, seq))
            result = cursor.fetchone()[0]
            if self.get_autocommit():
                self.commit()
            return result

    def get_indexes_for_table(self, table):
        res = self.execute_sql("""
            SELECT c2.relname, i.indisprimary, i.indisunique
            FROM
            pg_catalog.pg_class c,
            pg_catalog.pg_class c2,
            pg_catalog.pg_index i
            WHERE
            c.relname = %s AND c.oid = i.indrelid AND i.indexrelid = c2.oid
            ORDER BY i.indisprimary DESC, i.indisunique DESC, c2.relname""",
            (table,))
        return sorted([(r[0], r[1]) for r in res.fetchall()])

    def get_tables(self):
        res = self.execute_sql("""
            SELECT c.relname
            FROM pg_catalog.pg_class c
            LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind IN ('r', 'v', '')
                AND n.nspname NOT IN ('pg_catalog', 'pg_toast')
                AND pg_catalog.pg_table_is_visible(c.oid)
            ORDER BY c.relname""")
        return [row[0] for row in res.fetchall()]

    def sequence_exists(self, sequence):
        res = self.execute_sql("""
            SELECT COUNT(*)
            FROM pg_class, pg_namespace
            WHERE relkind='S'
                AND pg_class.relnamespace = pg_namespace.oid
                AND relname=%s""", (sequence,))
        return bool(res.fetchone()[0])

    def set_search_path(self, *search_path):
        path_params = ','.join(['%s'] * len(search_path))
        self.execute_sql('SET search_path TO %s' % path_params, search_path)

class MySQLDatabase(Database):
    commit_select = True
    compound_operations = ['UNION']
    drop_cascade = False
    field_overrides = {
        'bool': 'BOOL',
        'decimal': 'NUMERIC',
        'double': 'DOUBLE PRECISION',
        'float': 'FLOAT',
        'primary_key': 'INTEGER AUTO_INCREMENT',
        'text': 'LONGTEXT',
    }
    for_update = True
    for_update_nowait = False
    interpolation = '%s'
    limit_max = 2 ** 64 - 1  # MySQL quirk
    op_overrides = {
        OP_LIKE: 'LIKE BINARY',
        OP_ILIKE: 'LIKE',
        OP_XOR: 'XOR',
    }
    quote_char = '`'
    subquery_delete_same_table = False

    def _connect(self, database, **kwargs):
        if not mysql:
            raise ImproperlyConfigured('MySQLdb must be installed.')
        conn_kwargs = {
            'charset': 'utf8',
            'use_unicode': True,
        }
        conn_kwargs.update(kwargs)
        if 'password' in conn_kwargs:
            conn_kwargs['passwd'] = conn_kwargs.pop('password')
        return mysql.connect(db=database, **conn_kwargs)

    def get_indexes_for_table(self, table):
        res = self.execute_sql('SHOW INDEXES IN `%s`;' % table)
        rows = sorted([(r[2], r[1] == 0) for r in res.fetchall()])
        return rows

    def get_tables(self):
        res = self.execute_sql('SHOW TABLES;')
        return [r[0] for r in res.fetchall()]

    def extract_date(self, date_part, date_field):
        return fn.EXTRACT(Clause(R(date_part), R('FROM'), date_field))

    def truncate_date(self, date_part, date_field):
        return fn.DATE_FORMAT(date_field, MYSQL_DATE_TRUNC_MAPPING[date_part])


class transaction(object):
    def __init__(self, db):
        self.db = db

    def _begin(self):
        self.db.begin()

    def commit(self):
        self.db.commit()

    def rollback(self):
        self.db.rollback()

    def __enter__(self):
        self._orig = self.db.get_autocommit()
        self.db.set_autocommit(False)
        if self.db.transaction_depth() == 0:
            self._begin()
        self.db.push_transaction(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type:
                self.rollback()
            elif self.db.transaction_depth() == 1:
                try:
                    self.commit()
                except:
                    self.rollback()
                    raise
        finally:
            self.db.set_autocommit(self._orig)
            self.db.pop_transaction()


class savepoint(object):
    def __init__(self, db, sid=None):
        self.db = db
        _compiler = db.compiler()
        self.sid = sid or 's' + uuid.uuid4().hex
        self.quoted_sid = _compiler.quote(self.sid)

    def _execute(self, query):
        self.db.execute_sql(query, require_commit=False)

    def commit(self):
        self._execute('RELEASE SAVEPOINT %s;' % self.quoted_sid)

    def rollback(self):
        self._execute('ROLLBACK TO SAVEPOINT %s;' % self.quoted_sid)

    def __enter__(self):
        self._orig_autocommit = self.db.get_autocommit()
        self.db.set_autocommit(False)
        self._execute('SAVEPOINT %s;' % self.quoted_sid)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type:
                self.rollback()
            else:
                try:
                    self.commit()
                except:
                    self.rollback()
                    raise
        finally:
            self.db.set_autocommit(self._orig_autocommit)

class savepoint_sqlite(savepoint):
    def __enter__(self):
        conn = self.db.get_conn()
        # For sqlite, the connection's isolation_level *must* be set to None.
        # The act of setting it, though, will break any existing savepoints,
        # so only write to it if necessary.
        if conn.isolation_level is not None:
            self._orig_isolation_level = conn.isolation_level
            conn.isolation_level = None
        else:
            self._orig_isolation_level = None
        super(savepoint_sqlite, self).__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            return super(savepoint_sqlite, self).__exit__(
                exc_type, exc_val, exc_tb)
        finally:
            if self._orig_isolation_level is not None:
                self.db.get_conn().isolation_level = self._orig_isolation_level

class FieldProxy(Field):
    def __init__(self, alias, field_instance):
        self._model_alias = alias
        self.model = self._model_alias.model_class
        self.field_instance = field_instance

    def clone_base(self):
        return FieldProxy(self._model_alias, self.field_instance)

    def __getattr__(self, attr):
        if attr == 'model_class':
            return self._model_alias
        return getattr(self.field_instance, attr)

class ModelAlias(object):
    def __init__(self, model_class):
        self.__dict__['model_class'] = model_class

    def __getattr__(self, attr):
        model_attr = getattr(self.model_class, attr)
        if isinstance(model_attr, Field):
            return FieldProxy(self, model_attr)
        return model_attr

    def __setattr__(self, attr, value):
        raise AttributeError('Cannot set attributes on ModelAlias instances')

    def get_proxy_fields(self):
        return [
            FieldProxy(self, f) for f in self.model_class._meta.get_fields()]

    def select(self, *selection):
        query = SelectQuery(self, *selection)
        if self._meta.order_by:
            query = query.order_by(*self._meta.order_by)
        return query


class DoesNotExist(Exception): pass

default_database = SqliteDatabase('peewee.db')

class ModelOptions(object):
    def __init__(self, cls, database=None, db_table=None, indexes=None,
                 order_by=None, primary_key=None, table_alias=None,
                 constraints=None, schema=None, **kwargs):
        self.model_class = cls
        self.name = cls.__name__.lower()
        self.fields = {}
        self.columns = {}
        self.defaults = {}

        self.database = database or default_database
        self.db_table = db_table
        self.indexes = list(indexes or [])
        self.order_by = order_by
        self.primary_key = primary_key
        self.table_alias = table_alias
        self.constraints = constraints
        self.schema = schema

        self.auto_increment = None
        self.rel = {}
        self.reverse_rel = {}

        for key, value in kwargs.items():
            setattr(self, key, value)
        self._additional_keys = set(kwargs.keys())

    def prepared(self):
        for field in self.fields.values():
            if field.default is not None:
                self.defaults[field] = field.default

        if self.order_by:
            norm_order_by = []
            for clause in self.order_by:
                field = self.fields[clause.lstrip('-')]
                if clause.startswith('-'):
                    norm_order_by.append(field.desc())
                else:
                    norm_order_by.append(field.asc())
            self.order_by = norm_order_by

    def get_default_dict(self):
        dd = {}
        for field, default in self.defaults.items():
            if callable(default):
                dd[field.name] = default()
            else:
                dd[field.name] = default
        return dd

    def get_sorted_fields(self):
        key = lambda i: i[1]._sort_key
        return sorted(self.fields.items(), key=key)

    def get_field_names(self):
        return [f[0] for f in self.get_sorted_fields()]

    def get_fields(self):
        return [f[1] for f in self.get_sorted_fields()]

    def get_field_index(self, field):
        for i, (field_name, field_obj) in enumerate(self.get_sorted_fields()):
            if field_name == field.name:
                return i
        return -1

    def rel_for_model(self, model, field_obj=None):
        for field in self.get_fields():
            if isinstance(field, ForeignKeyField) and field.rel_model == model:
                if field_obj is None or field_obj.name == field.name:
                    return field

    def reverse_rel_for_model(self, model):
        return model._meta.rel_for_model(self.model_class)

    def rel_exists(self, model):
        return self.rel_for_model(model) or self.reverse_rel_for_model(model)


class BaseModel(type):
    inheritable = set(['constraints', 'database', 'indexes', 'order_by',
                       'primary_key', 'schema'])

    def __new__(cls, name, bases, attrs):
        if not bases:
            return super(BaseModel, cls).__new__(cls, name, bases, attrs)

        meta_options = {}
        meta = attrs.pop('Meta', None)
        if meta:
            for k, v in meta.__dict__.items():
                if not k.startswith('_'):
                    meta_options[k] = v

        model_pk = getattr(meta, 'primary_key', None)
        parent_pk = None

        # inherit any field descriptors by deep copying the underlying field
        # into the attrs of the new model, additionally see if the bases define
        # inheritable model options and swipe them
        for b in bases:
            if not hasattr(b, '_meta'):
                continue

            base_meta = getattr(b, '_meta')
            if parent_pk is None:
                parent_pk = deepcopy(base_meta.primary_key)
            all_inheritable = cls.inheritable | base_meta._additional_keys
            for (k, v) in base_meta.__dict__.items():
                if k in all_inheritable and k not in meta_options:
                    meta_options[k] = v

            for (k, v) in b.__dict__.items():
                if k in attrs:
                    continue
                if isinstance(v, FieldDescriptor):
                    if not v.field.primary_key:
                        attrs[k] = deepcopy(v.field)

        # initialize the new class and set the magic attributes
        cls = super(BaseModel, cls).__new__(cls, name, bases, attrs)
        cls._meta = ModelOptions(cls, **meta_options)
        cls._data = None
        cls._meta.indexes = list(cls._meta.indexes)

        # replace fields with field descriptors, calling the add_to_class hook
        fields = []
        for name, attr in cls.__dict__.items():
            if isinstance(attr, Field):
                if attr.primary_key and model_pk:
                    raise ValueError('primary key is overdetermined.')
                elif attr.primary_key:
                    model_pk, pk_name = attr, name
                else:
                    fields.append((attr, name))

        if model_pk is None:
            if parent_pk:
                model_pk, pk_name = parent_pk, parent_pk.name
            else:
                model_pk, pk_name = PrimaryKeyField(primary_key=True), 'id'
        elif isinstance(model_pk, CompositeKey):
            pk_name = '_composite_key'

        model_pk.add_to_class(cls, pk_name)
        cls._meta.primary_key = model_pk
        cls._meta.auto_increment = (
            isinstance(model_pk, PrimaryKeyField) or bool(model_pk.sequence))

        for field, name in fields:
            field.add_to_class(cls, name)

        if not cls._meta.db_table:
            cls._meta.db_table = re.sub('[^\w]+', '_', cls.__name__.lower())

        # create a repr and error class before finalizing
        if hasattr(cls, '__unicode__'):
            setattr(cls, '__repr__', lambda self: '<%s: %r>' % (
                cls.__name__, self.__unicode__()))

        exc_name = '%sDoesNotExist' % cls.__name__
        exception_class = type(exc_name, (DoesNotExist,), {})
        cls.DoesNotExist = exception_class
        cls._meta.prepared()

        return cls

class Model(with_metaclass(BaseModel)):
    def __init__(self, *args, **kwargs):
        self._data = self._meta.get_default_dict()
        self._dirty = set()
        self._obj_cache = {} # cache of related objects

        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def alias(cls):
        return ModelAlias(cls)

    @classmethod
    def select(cls, *selection):
        query = SelectQuery(cls, *selection)
        if cls._meta.order_by:
            query = query.order_by(*cls._meta.order_by)
        return query

    @classmethod
    def update(cls, **update):
        fdict = dict((cls._meta.fields[f], v) for f, v in update.items())
        return UpdateQuery(cls, fdict)

    @classmethod
    def insert(cls, **insert):
        return InsertQuery(cls, insert)

    @classmethod
    def insert_many(cls, rows):
        return InsertQuery(cls, rows=rows)

    @classmethod
    def delete(cls):
        return DeleteQuery(cls)

    @classmethod
    def raw(cls, sql, *params):
        return RawQuery(cls, sql, *params)

    @classmethod
    def create(cls, **query):
        inst = cls(**query)
        inst.save(force_insert=True)
        inst.prepared()
        return inst

    @classmethod
    def get(cls, *query, **kwargs):
        sq = cls.select().naive()
        if query:
            sq = sq.where(*query)
        if kwargs:
            sq = sq.filter(**kwargs)
        return sq.get()

    @classmethod
    def get_or_create(cls, **kwargs):
        sq = cls.select().filter(**kwargs)
        try:
            return sq.get()
        except cls.DoesNotExist:
            return cls.create(**kwargs)

    @classmethod
    def filter(cls, *dq, **query):
        return cls.select().filter(*dq, **query)

    @classmethod
    def table_exists(cls):
        return cls._meta.db_table in cls._meta.database.get_tables()

    @classmethod
    def create_table(cls, fail_silently=False):
        if fail_silently and cls.table_exists():
            return

        db = cls._meta.database
        pk = cls._meta.primary_key
        if db.sequences and pk.sequence:
            if not db.sequence_exists(pk.sequence):
                db.create_sequence(pk.sequence)

        db.create_table(cls)
        cls._create_indexes()

    @classmethod
    def _fields_to_index(cls):
        fields = []
        for field in cls._meta.fields.values():
            if field.primary_key:
                continue
            requires_index = any((
                field.index,
                field.unique,
                isinstance(field, ForeignKeyField)))
            if requires_index:
                fields.append(field)
        return fields

    @classmethod
    def _create_indexes(cls):
        db = cls._meta.database
        for field in cls._fields_to_index():
            db.create_index(cls, [field], field.unique)

        if cls._meta.indexes:
            for fields, unique in cls._meta.indexes:
                db.create_index(cls, fields, unique)

    @classmethod
    def sqlall(cls):
        queries = []
        compiler = cls._meta.database.compiler()
        pk = cls._meta.primary_key
        if cls._meta.database.sequences and pk.sequence:
            queries.append(compiler.create_sequence(pk.sequence))
        queries.append(compiler.create_table(cls))
        for field in cls._fields_to_index():
            queries.append(compiler.create_index(cls, [field], field.unique))
        if cls._meta.indexes:
            for field_names, unique in cls._meta.indexes:
                fields = [cls._meta.fields[f] for f in field_names]
                queries.append(compiler.create_index(cls, fields, unique))
        return [sql for sql, _ in queries]

    @classmethod
    def drop_table(cls, fail_silently=False, cascade=False):
        cls._meta.database.drop_table(cls, fail_silently, cascade)

    @classmethod
    def _as_entity(cls):
        if cls._meta.schema:
            return Entity(cls._meta.schema, cls._meta.db_table)
        return Entity(cls._meta.db_table)

    def get_id(self):
        return getattr(self, self._meta.primary_key.name)

    def set_id(self, id):
        setattr(self, self._meta.primary_key.name, id)

    def pk_expr(self):
        return self._meta.primary_key == self.get_id()

    def prepared(self):
        pass

    def _prune_fields(self, field_dict, only):
        new_data = {}
        for field in only:
            if field.name in field_dict:
                new_data[field.name] = field_dict[field.name]
        return new_data

    def save(self, force_insert=False, only=None):
        field_dict = dict(self._data)
        pk_field = self._meta.primary_key
        if only:
            field_dict = self._prune_fields(field_dict, only)
        if self.get_id() is not None and not force_insert:
            if not isinstance(pk_field, CompositeKey):
                field_dict.pop(pk_field.name, None)
            else:
                field_dict = self._prune_fields(field_dict, self.dirty_fields)
            rows = self.update(**field_dict).where(self.pk_expr()).execute()
        else:
            pk = self.get_id()
            pk_from_cursor = self.insert(**field_dict).execute()
            if pk_from_cursor is not None:
                pk = pk_from_cursor
            self.set_id(pk)  # Do not overwrite current ID with a None value.
            rows = 1
        self._dirty.clear()
        return rows

    def is_dirty(self):
        return bool(self._dirty)

    @property
    def dirty_fields(self):
        return [f for f in self._meta.get_fields() if f.name in self._dirty]

    def dependencies(self, search_nullable=False):
        query = self.select().where(self.pk_expr())
        stack = [(type(self), query)]
        seen = set()

        while stack:
            klass, query = stack.pop()
            if klass in seen:
                continue
            seen.add(klass)
            for rel_name, fk in klass._meta.reverse_rel.items():
                rel_model = fk.model_class
                node = fk << query
                if not fk.null or search_nullable:
                    stack.append((rel_model, rel_model.select().where(node)))
                yield (node, fk)

    def delete_instance(self, recursive=False, delete_nullable=False):
        if recursive:
            dependencies = self.dependencies(delete_nullable)
            for query, fk in reversed(list(dependencies)):
                model = fk.model_class
                if fk.null and not delete_nullable:
                    model.update(**{fk.name: None}).where(query).execute()
                else:
                    model.delete().where(query).execute()
        return self.delete().where(self.pk_expr()).execute()

    def __eq__(self, other):
        return (
            other.__class__ == self.__class__ and
            self.get_id() is not None and
            other.get_id() == self.get_id())

    def __ne__(self, other):
        return not self == other


def prefetch_add_subquery(sq, subqueries):
    fixed_queries = [(sq, None)]
    for i, subquery in enumerate(subqueries):
        if not isinstance(subquery, Query) and issubclass(subquery, Model):
            subquery = subquery.select()
        subquery_model = subquery.model_class
        fkf = None
        for j in reversed(range(i + 1)):
            last_query = fixed_queries[j][0]
            fkf = subquery_model._meta.rel_for_model(last_query.model_class)
            if fkf:
                break
        if not fkf:
            raise AttributeError('Error: unable to find foreign key for '
                                 'query: %s' % subquery)
        inner_query = last_query.select(fkf.to_field)
        fixed_queries.append((subquery.where(fkf << inner_query), fkf))

    return fixed_queries

def prefetch(sq, *subqueries):
    if not subqueries:
        return sq
    fixed_queries = prefetch_add_subquery(sq, subqueries)

    deps = {}
    rel_map = {}
    for query, foreign_key_field in reversed(fixed_queries):
        query_model = query.model_class
        deps[query_model] = {}
        id_map = deps[query_model]
        has_relations = bool(rel_map.get(query_model))

        for result in query:
            if foreign_key_field:
                fk_val = result._data[foreign_key_field.name]
                id_map.setdefault(fk_val, [])
                id_map[fk_val].append(result)
            if has_relations:
                for rel_model, rel_fk in rel_map[query_model]:
                    rel_name = '%s_prefetch' % rel_fk.related_name
                    identifier = getattr(result, rel_fk.to_field.name)
                    rel_instances = deps[rel_model].get(identifier, [])
                    for inst in rel_instances:
                        setattr(inst, rel_fk.name, result)
                    setattr(result, rel_name, rel_instances)
        if foreign_key_field:
            rel_model = foreign_key_field.rel_model
            rel_map.setdefault(rel_model, [])
            rel_map[rel_model].append((query_model, foreign_key_field))

    return query

def create_model_tables(models, **create_table_kwargs):
    """Create tables for all given models (in the right order)."""
    for m in sort_models_topologically(models):
        m.create_table(**create_table_kwargs)

def drop_model_tables(models, **drop_table_kwargs):
    """Drop tables for all given models (in the right order)."""
    for m in reversed(sort_models_topologically(models)):
        m.drop_table(**drop_table_kwargs)

def sort_models_topologically(models):
    """Sort models topologically so that parents will precede children."""
    models = set(models)
    seen = set()
    ordering = []
    def dfs(model):
        if model in models and model not in seen:
            seen.add(model)
            for foreign_key in model._meta.reverse_rel.values():
                dfs(foreign_key.model_class)
            ordering.append(model)  # parent will follow descendants
    # order models by name and table initially to guarantee a total ordering
    names = lambda m: (m._meta.name, m._meta.db_table)
    for m in sorted(models, key=names, reverse=True):
        dfs(m)
    return list(reversed(ordering))  # want parents first in output ordering

########NEW FILE########
__FILENAME__ = apsw_ext
"""
Peewee integration with APSW, "another python sqlite wrapper".

Project page: https://code.google.com/p/apsw/

APSW is a really neat library that provides a thin wrapper on top of SQLite's
C interface.

Here are just a few reasons to use APSW, taken from the documentation:

* APSW gives all functionality of SQLite, including virtual tables, virtual
  file system, blob i/o, backups and file control.
* Connections can be shared across threads without any additional locking.
* Transactions are managed explicitly by your code.
* APSW can handle nested transactions.
* Unicode is handled correctly.
* APSW is faster.
"""
import apsw
from peewee import *
from peewee import _sqlite_date_part
from peewee import _sqlite_date_trunc
from peewee import BooleanField as _BooleanField
from peewee import DateField as _DateField
from peewee import DateTimeField as _DateTimeField
from peewee import DecimalField as _DecimalField
from peewee import logger
from peewee import PY3
from peewee import TimeField as _TimeField
from peewee import transaction as _transaction


class ConnectionWrapper(apsw.Connection):
    def cursor(self):
        base_cursor = super(ConnectionWrapper, self).cursor()
        return CursorProxy(base_cursor)


class CursorProxy(object):
    def __init__(self, cursor_obj):
        self.cursor_obj = cursor_obj
        self.implements = set(['description', 'fetchone'])

    def __getattr__(self, attr):
        if attr in self.implements:
            return self.__getattribute__(attr)
        return getattr(self.cursor_obj, attr)

    @property
    def description(self):
        try:
            return self.cursor_obj.getdescription()
        except apsw.ExecutionCompleteError:
            return []

    if PY3:
        def fetchone(self):
            try:
                return next(self.cursor_obj)
            except StopIteration:
                pass
    else:
        def fetchone(self):
            try:
                return self.cursor_obj.next()
            except StopIteration:
                pass


class transaction(_transaction):
    def __init__(self, db, lock_type='deferred'):
        self.db = db
        self.lock_type = lock_type

    def _begin(self):
        self.db.begin(self.lock_type)


class APSWDatabase(SqliteDatabase):
    def __init__(self, database, timeout=None, **kwargs):
        self.timeout = timeout
        self._modules = {}
        super(APSWDatabase, self).__init__(database, **kwargs)

    def register_module(self, mod_name, mod_inst):
        self._modules[mod_name] = mod_inst

    def unregister_module(self, mod_name):
        del(self._modules[mod_name])

    def _connect(self, database, **kwargs):
        conn = ConnectionWrapper(database, **kwargs)
        if self.timeout is not None:
            conn.setbusytimeout(self.timeout)
        conn.createscalarfunction('date_part', _sqlite_date_part, 2)
        conn.createscalarfunction('date_trunc', _sqlite_date_trunc, 2)
        for mod_name, mod_inst in self._modules.items():
            conn.createmodule(mod_name, mod_inst)
        return conn

    def _execute_sql(self, cursor, sql, params):
        cursor.execute(sql, params or ())
        return cursor

    def execute_sql(self, sql, params=None, require_commit=True):
        cursor = self.get_cursor()
        wrap_transaction = require_commit and self.get_autocommit()
        if wrap_transaction:
            cursor.execute('begin;')
            try:
                self._execute_sql(cursor, sql, params)
            except:
                cursor.execute('rollback;')
                raise
            else:
                cursor.execute('commit;')
        else:
            cursor = self._execute_sql(cursor, sql, params)
        logger.debug((sql, params))
        return cursor

    def last_insert_id(self, cursor, model):
        return cursor.getconnection().last_insert_rowid()

    def rows_affected(self, cursor):
        return cursor.getconnection().changes()

    def begin(self, lock_type='deferred'):
        self.get_cursor().execute('begin %s;' % lock_type)

    def commit(self):
        self.get_cursor().execute('commit;')

    def rollback(self):
        self.get_cursor().execute('rollback;')

    def transaction(self, lock_type='deferred'):
        return transaction(self, lock_type)


def nh(s, v):
    if v is not None:
        return str(v)

class BooleanField(_BooleanField):
    def db_value(self, v):
        v = super(BooleanField, self).db_value(v)
        if v is not None:
            return v and 1 or 0

class DateField(_DateField):
    db_value = nh

class TimeField(_TimeField):
    db_value = nh

class DateTimeField(_DateTimeField):
    db_value = nh

class DecimalField(_DecimalField):
    db_value = nh

########NEW FILE########
__FILENAME__ = berkeleydb
import datetime
import decimal

from playhouse.sqlite_ext import *
from pysqlite2 import dbapi2 as berkeleydb

berkeleydb.register_adapter(decimal.Decimal, str)
berkeleydb.register_adapter(datetime.date, str)
berkeleydb.register_adapter(datetime.time, str)


class BerkeleyDatabase(SqliteExtDatabase):
    def _connect(self, database, **kwargs):
        conn = berkeleydb.connect(database, **kwargs)
        self._add_conn_hooks(conn)
        return conn

########NEW FILE########
__FILENAME__ = csv_loader
"""
Peewee helper for loading CSV data into a database.

Load the users CSV file into the database and return a Model for accessing
the data:

    from playhouse.csv_loader import load_csv
    db = SqliteDatabase(':memory:')
    User = load_csv(db, 'users.csv')

Provide explicit field types and/or field names:

    fields = [IntegerField(), IntegerField(), DateTimeField(), DecimalField()]
    field_names = ['from_acct', 'to_acct', 'timestamp', 'amount']
    Payments = load_csv(db, 'payments.csv', fields, field_names)
"""
import csv
import datetime
import os
import re
from contextlib import contextmanager

from peewee import *
from peewee import Database
from peewee import PY3

if PY3:
    basestring = str
    decode_value = False
else:
    decode_value = True

class _CSVReader(object):
    @contextmanager
    def get_reader(self, file_or_name, **reader_kwargs):
        if isinstance(file_or_name, basestring):
            fh = open(file_or_name, 'r')
        else:
            fh = file_or_name
            fh.seek(0)
        reader = csv.reader(fh, **reader_kwargs)
        yield reader
        fh.close()

class RowConverter(_CSVReader):
    """
    Simple introspection utility to convert a CSV file into a list of headers
    and column types.

    :param database: a peewee Database object.
    :param bool has_header: whether the first row of CSV is a header row.
    :param int sample_size: number of rows to introspect
    """
    date_formats = [
        '%Y-%m-%d',
        '%m/%d/%Y']

    datetime_formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M:%S.%f']

    def __init__(self, database, has_header=True, sample_size=10):
        self.database = database
        self.has_header = has_header
        self.sample_size = sample_size

    def matches_date(self, value, formats):
        for fmt in formats:
            try:
                datetime.datetime.strptime(value, fmt)
            except ValueError:
                pass
            else:
                return True

    def field(field_class, **field_kwargs):
        def decorator(fn):
            fn.field = lambda: field_class(**field_kwargs)
            return fn
        return decorator

    @field(IntegerField, default=0)
    def is_integer(self, value):
        return value.isdigit()

    @field(FloatField, default=0)
    def is_float(self, value):
        try:
            float(value)
        except (ValueError, TypeError):
            pass
        else:
            return True

    @field(DateTimeField, null=True)
    def is_datetime(self, value):
        return self.matches_date(value, self.datetime_formats)

    @field(DateField, null=True)
    def is_date(self, value):
        return self.matches_date(value, self.date_formats)

    @field(BareField, default='')
    def default(self, value):
        return True

    def extract_rows(self, file_or_name, **reader_kwargs):
        """
        Extract `self.sample_size` rows from the CSV file and analyze their
        data-types.

        :param str file_or_name: A string filename or a file handle.
        :param reader_kwargs: Arbitrary parameters to pass to the CSV reader.
        :returns: A 2-tuple containing a list of headers and list of rows
                  read from the CSV file.
        """
        rows = []
        rows_to_read = self.sample_size
        with self.get_reader(file_or_name, **reader_kwargs) as reader:
            if self.has_header:
                rows_to_read += 1
            for i, row in enumerate(reader):
                rows.append(row)
                if i == self.sample_size:
                    break
        if self.has_header:
            header, rows = rows[0], rows[1:]
        else:
            header = ['field_%d' % i for i in range(len(rows[0]))]
        return header, rows

    def get_checks(self):
        """Return a list of functions to use when testing values."""
        return [
            self.is_date,
            self.is_datetime,
            self.is_integer,
            self.is_float,
            self.default]

    def analyze(self, rows):
        """
        Analyze the given rows and try to determine the type of value stored.

        :param list rows: A list-of-lists containing one or more rows from a
                          csv file.
        :returns: A list of peewee Field objects for each column in the CSV.
        """
        transposed = zip(*rows)
        checks = self.get_checks()
        column_types = []
        for i, column in enumerate(transposed):
            # Remove any empty values.
            col_vals = [val for val in column if val != '']
            for check in checks:
                results = set(check(val) for val in col_vals)
                if all(results):
                    column_types.append(check.field())
                    break

        return column_types


class Loader(_CSVReader):
    """
    Load the contents of a CSV file into a database and return a model class
    suitable for working with the CSV data.

    :param db_or_model: a peewee Database instance or a Model class.
    :param file_or_name: the filename of the CSV file *or* a file handle.
    :param list fields: A list of peewee Field() instances appropriate to
        the values in the CSV file.
    :param list field_names: A list of names to use for the fields.
    :param bool has_header: Whether the first row of the CSV file is a header.
    :param int sample_size: Number of rows to introspect if fields are not
        defined.
    :param converter: A RowConverter instance to use.
    :param str db_table: Name of table to store data in (if not specified, the
        table name will be derived from the CSV filename).
    :param reader_kwargs: Arbitrary arguments to pass to the CSV reader.
    """
    def __init__(self, db_or_model, file_or_name, fields=None, field_names=None,
                 has_header=True, sample_size=10, converter=None,
                 db_table=None, **reader_kwargs):
        self.file_or_name = file_or_name
        self.fields = fields
        self.field_names = field_names
        self.has_header = has_header
        self.sample_size = sample_size
        self.converter = converter
        self.reader_kwargs = reader_kwargs

        if isinstance(file_or_name, basestring):
            self.filename = file_or_name
        else:
            self.filename = file_or_name.name

        if isinstance(db_or_model, Database):
            self.database = db_or_model
            self.model = None
            self.db_table = (
                db_table or
                os.path.splitext(os.path.basename(self.filename))[0])
        else:
            self.model = db_or_model
            self.database = self.model._meta.database
            self.db_table = self.model._meta.db_table
            self.fields = self.model._meta.get_fields()
            self.field_names = self.model._meta.get_field_names()
            # If using an auto-incrementing primary key, ignore it.
            if self.model._meta.auto_increment:
                self.fields = self.fields[1:]
                self.field_names = self.field_names[1:]

    def clean_field_name(self, s):
        return re.sub('[^a-z0-9]+', '_', s.lower())

    def get_converter(self):
        return self.converter or RowConverter(
            self.database,
            has_header=self.has_header,
            sample_size=self.sample_size)

    def analyze_csv(self):
        converter = self.get_converter()
        header, rows = converter.extract_rows(
            self.file_or_name,
            **self.reader_kwargs)
        if rows:
            self.fields = converter.analyze(rows)
        else:
            self.fields = [converter.default.field() for _ in header]
        if not self.field_names:
            self.field_names = [self.clean_field_name(col) for col in  header]

    def get_model_class(self, field_names, fields):
        if self.model:
            return self.model
        attrs = dict(zip(field_names, fields))
        attrs['_auto_pk'] = PrimaryKeyField()
        klass = type(self.db_table.title(), (Model,), attrs)
        klass._meta.database = self.database
        klass._meta.db_table = self.db_table
        return klass

    def load(self):
        if not self.fields:
            self.analyze_csv()
        if not self.field_names and not self.has_header:
            self.field_names = [
                'field_%d' % i for i in range(len(self.fields))]

        with self.get_reader(self.file_or_name, **self.reader_kwargs) as reader:
            if not self.field_names:
                row = next(reader)
                self.field_names = [self.clean_field_name(col) for col in row]
            elif self.has_header:
                next(reader)

            ModelClass = self.get_model_class(self.field_names, self.fields)

            with self.database.transaction():
                ModelClass.create_table(True)
                for row in reader:
                    insert = {}
                    for field_name, value in zip(self.field_names, row):
                        if value:
                            if decode_value:
                                value = value.decode('utf-8')
                            insert[field_name] = value
                    if insert:
                        ModelClass.insert(**insert).execute()

        return ModelClass

def load_csv(db_or_model, file_or_name, fields=None, field_names=None,
             has_header=True, sample_size=10, converter=None,
             db_table=None, **reader_kwargs):
    loader = Loader(db_or_model, file_or_name, fields, field_names, has_header,
                    sample_size, converter, db_table, **reader_kwargs)
    return loader.load()
load_csv.__doc__ = Loader.__doc__

########NEW FILE########
__FILENAME__ = djpeewee
"""
Simple translation of Django model classes to peewee model classes.
"""
from functools import partial
import logging

from peewee import *

logger = logging.getLogger('peewee.playhouse.djpeewee')

class AttrDict(dict):
    def __getattr__(self, attr):
        return self[attr]

class DjangoTranslator(object):
    def __init__(self):
        self._field_map = self.get_django_field_map()

    def get_django_field_map(self):
        from django.db.models import fields as djf
        return [
            (djf.AutoField, PrimaryKeyField),
            (djf.BigIntegerField, BigIntegerField),
            #(djf.BinaryField, BlobField),
            (djf.BooleanField, BooleanField),
            (djf.CharField, CharField),
            (djf.DateTimeField, DateTimeField),  # Extends DateField.
            (djf.DateField, DateField),
            (djf.DecimalField, DecimalField),
            (djf.FilePathField, CharField),
            (djf.FloatField, FloatField),
            (djf.IntegerField, IntegerField),
            (djf.NullBooleanField, partial(BooleanField, null=True)),
            (djf.TextField, TextField),
            (djf.TimeField, TimeField),
            (djf.related.ForeignKey, ForeignKeyField),
        ]

    def convert_field(self, field):
        converted = None
        for django_field, peewee_field in self._field_map:
            if isinstance(field, django_field):
                converted = peewee_field
                break
        return converted

    def _translate_model(self,
                         model,
                         mapping,
                         max_depth=None,
                         backrefs=False,
                         exclude=None):
        if exclude and model in exclude:
            return

        if max_depth is None:
            max_depth = -1

        from django.db.models import fields as djf
        options = model._meta
        if mapping.get(options.object_name):
            return
        mapping[options.object_name] = None

        attrs = {}
        # Sort fields such that nullable fields appear last.
        field_key = lambda field: (field.null and 1 or 0, field)
        for model_field in sorted(options.fields, key=field_key):
            # Get peewee equivalent for this field type.
            converted = self.convert_field(model_field)

            # Special-case ForeignKey fields.
            if converted is ForeignKeyField:
                if max_depth != 0:
                    related_model = model_field.rel.to
                    model_name = related_model._meta.object_name
                    # If we haven't processed the related model yet, do so now.
                    if model_name not in mapping:
                        mapping[model_name] = None  # Avoid endless recursion.
                        self._translate_model(
                            related_model,
                            mapping,
                            max_depth=max_depth - 1,
                            backrefs=backrefs,
                            exclude=exclude)
                    if mapping[model_name] is None:
                        # Cycle detected, put an integer field here.
                        logger.warn('Cycle detected: %s: %s',
                                    model_field.name, model_name)
                        attrs[model_field.name] = IntegerField(
                            db_column=model_field.get_attname())
                    else:
                        related_name = (model_field.rel.related_name or
                                        model_field.related_query_name())
                        if related_name.endswith('+'):
                            related_name = '__%s:%s:%s' % (
                                options,
                                model_field.name,
                                related_name.strip('+'))

                        attrs[model_field.name] = ForeignKeyField(
                            mapping[model_name],
                            related_name=related_name)

                else:
                    attrs[model_field.name] = IntegerField(
                        db_column=model_field.get_attname())

            elif converted:
                attrs[model_field.name] = converted()

        klass = type(options.object_name, (Model,), attrs)
        klass._meta.db_table = options.db_table
        klass._meta.database.interpolation = '%s'
        mapping[options.object_name] = klass

        if backrefs:
            # Follow back-references for foreign keys.
            for rel_obj in options.get_all_related_objects():
                if rel_obj.model._meta.object_name in mapping:
                    continue
                self._translate_model(
                    rel_obj.model,
                    mapping,
                    max_depth=max_depth - 1,
                    backrefs=backrefs,
                    exclude=exclude)

        # Load up many-to-many relationships.
        for many_to_many in options.many_to_many:
            if not isinstance(many_to_many, djf.related.ManyToManyField):
                continue
            self._translate_model(
                many_to_many.rel.through,
                mapping,
                max_depth=max_depth,  # Do not decrement.
                backrefs=backrefs,
                exclude=exclude)


    def translate_models(self, *models, **options):
        """
        Generate a group of peewee models analagous to the provided Django models
        for the purposes of creating queries.

        :param model: A Django model class.
        :param options: A dictionary of options, see note below.
        :returns: A dictionary mapping model names to peewee model classes.
        :rtype: dict

        Recognized options:
            `recurse`: Follow foreign keys (default: True)
            `max_depth`: Max depth to recurse (default: None, unlimited)
            `backrefs`: Follow backrefs (default: False)
            `exclude`: A list of models to exclude

        Example::

            # Map Django models to peewee models. Foreign keys and M2M will be
            # traversed as well.
            peewee = translate(Account)

            # Generate query using peewee.
            PUser = peewee['User']
            PAccount = peewee['Account']
            query = PUser.select().join(PAccount).where(PAccount.acct_type == 'foo')

            # Django raw query.
            users = User.objects.raw(*query.sql())
        """
        mapping = AttrDict()
        recurse = options.get('recurse', True)
        max_depth = options.get('max_depth', None)
        backrefs = options.get('backrefs', False)
        exclude = options.get('exclude', None)
        if not recurse and max_depth:
            raise ValueError('Error, you cannot specify a max_depth when '
                             'recurse=False.')
        elif not recurse:
            max_depth = 0
        elif recurse and max_depth is None:
            max_depth = -1

        for model in models:
            self._translate_model(
                model,
                mapping,
                max_depth=max_depth,
                backrefs=backrefs,
                exclude=exclude)
        return mapping

try:
    import django
    translate = DjangoTranslator().translate_models
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = gfk
"""
Provide a "Generic ForeignKey", similar to Django.  A "GFK" is composed of two
columns: an object ID and an object type identifier.  The object types are
collected in a global registry (all_models), so all you need to do is subclass
``gfk.Model`` and your model will be added to the registry.

Example:

class Tag(Model):
    tag = CharField()
    object_type = CharField(null=True)
    object_id = IntegerField(null=True)
    object = GFKField('object_type', 'object_id')

class Blog(Model):
    tags = ReverseGFK(Tag, 'object_type', 'object_id')

class Photo(Model):
    tags = ReverseGFK(Tag, 'object_type', 'object_id')

tag.object -> a blog or photo
blog.tags -> select query of tags for ``blog`` instance
Blog.tags -> select query of all tags for Blog instances
"""

from peewee import *
from peewee import BaseModel as _BaseModel
from peewee import FieldDescriptor
from peewee import Model as _Model
from peewee import SelectQuery
from peewee import UpdateQuery
from peewee import with_metaclass


all_models = set()
table_cache = {}


class BaseModel(_BaseModel):
    def __new__(cls, name, bases, attrs):
        cls = super(BaseModel, cls).__new__(cls, name, bases, attrs)
        all_models.add(cls)
        return cls

class Model(with_metaclass(BaseModel, _Model)):
    pass

def get_model(tbl_name):
    if tbl_name not in table_cache:
        for model in all_models:
            if model._meta.db_table == tbl_name:
                table_cache[tbl_name] = model
                break
    return table_cache.get(tbl_name)

class GFKField(object):
    def __init__(self, model_type_field='object_type',
                 model_id_field='object_id'):
        self.model_type_field = model_type_field
        self.model_id_field = model_id_field
        self.att_name = '.'.join((self.model_type_field, self.model_id_field))

    def get_obj(self, instance):
        data = instance._data
        if data.get(self.model_type_field) and data.get(self.model_id_field):
            tbl_name = data[self.model_type_field]
            model_class = get_model(tbl_name)
            if not model_class:
                raise AttributeError('Model for table "%s" not found in GFK '
                                     'lookup.' % tbl_name)
            query = model_class.select().where(
                model_class._meta.primary_key == data[self.model_id_field])
            return query.get()

    def __get__(self, instance, instance_type=None):
        if instance:
            if self.att_name not in instance._obj_cache:
                rel_obj = self.get_obj(instance)
                if rel_obj:
                    instance._obj_cache[self.att_name] = rel_obj
            return instance._obj_cache.get(self.att_name)
        return self

    def __set__(self, instance, value):
        instance._obj_cache[self.att_name] = value
        instance._data[self.model_type_field] = value._meta.db_table
        instance._data[self.model_id_field] = value.get_id()

class ReverseGFK(object):
    def __init__(self, model, model_type_field='object_type',
                 model_id_field='object_id'):
        self.model_class = model
        self.model_type_field = model._meta.fields[model_type_field]
        self.model_id_field = model._meta.fields[model_id_field]

    def __get__(self, instance, instance_type=None):
        if instance:
            return self.model_class.select().where(
                (self.model_type_field == instance._meta.db_table) &
                (self.model_id_field == instance.get_id())
            )
        else:
            return self.model_class.select().where(
                self.model_type_field == instance_type._meta.db_table
            )

    def __set__(self, instance, value):
        mtv = instance._meta.db_table
        miv = instance.get_id()
        if (isinstance(value, SelectQuery) and
                value.model_class == self.model_class):
            uq = UpdateQuery(self.model_class, {
                self.model_type_field: mtv,
                self.model_id_field: miv,
            }).where(value._where).execute()
        elif all(map(lambda i: isinstance(i, self.model_class), value)):
            for obj in value:
                setattr(obj, self.model_type_field.name, mtv)
                setattr(obj, self.model_id_field.name, miv)
                obj.save()
        else:
            raise ValueError('ReverseGFK field unable to handle "%s"' % value)

########NEW FILE########
__FILENAME__ = kv
from base64 import b64decode
from base64 import b64encode
import itertools
import operator
import pickle
from peewee import *
from peewee import Node

try:
    from playhouse.apsw_ext import APSWDatabase
    def KeyValueDatabase(db_name):
        return APSWDatabase(db_name)
except ImportError:
    def KeyValueDatabase(db_name):
        return SqliteDatabase(db_name, check_same_thread=False)

Sentinel = type('Sentinel', (object,), {})

key_value_db = KeyValueDatabase(':memory:')

class PickleField(BlobField):
    def db_value(self, value):
        return b64encode(pickle.dumps(value))

    def python_value(self, value):
        return pickle.loads(b64decode(value))

class KeyStore(object):
    """
    Rich dictionary with support for storing a wide variety of data types.

    :param peewee.Field value_type: Field type to use for values.
    :param boolean ordered: Whether keys should be returned in sorted order.
    :param peewee.Model model: Model class to use for Keys/Values.
    """
    def __init__(self, value_field, ordered=False, database=None):
        self._value_field = value_field
        self._ordered = ordered

        self._database = database or key_value_db
        self._compiler = self._database.compiler()

        self.model = self.create_model()
        self.key = self.model.key
        self.value = self.model.value

        self._database.create_table(self.model, True)
        self._native_upsert = isinstance(self._database, SqliteDatabase)

    def create_model(self):
        class KVModel(Model):
            key = CharField(max_length=255, primary_key=True)
            value = self._value_field

            class Meta:
                database = self._database

        return KVModel

    def query(self, *select):
        query = self.model.select(*select).tuples()
        if self._ordered:
            query = query.order_by(self.key)
        return query

    def convert_node(self, node):
        if not isinstance(node, Node):
            return (self.key == node), True
        return node, False

    def __contains__(self, key):
        node, _ = self.convert_node(key)
        return self.model.select().where(node).exists()

    def __len__(self):
        return self.model.select().count()

    def __getitem__(self, node):
        converted, is_single = self.convert_node(node)
        result = self.query(self.value).where(converted)
        item_getter = operator.itemgetter(0)
        result = [item_getter(val) for val in result]
        if len(result) == 0 and is_single:
            raise KeyError(node)
        elif is_single:
            return result[0]
        return result

    def _upsert(self, key, value):
        self.model.insert(**{
            self.key.name: key,
            self.value.name: value}).upsert().execute()

    def __setitem__(self, node, value):
        if isinstance(node, Node):
            update = {self.value.name: value}
            self.model.update(**update).where(node).execute()
        elif self._native_upsert:
            self._upsert(node, value)
        else:
            try:
                self.model.create(key=node, value=value)
            except:
                self._database.rollback()
                (self.model
                 .update(**{self.value.name: value})
                 .where(self.key == node)
                 .execute())

    def __delitem__(self, node):
        converted, _ = self.convert_node(node)
        self.model.delete().where(converted).execute()

    def __iter__(self):
        return self.query().execute()

    def keys(self):
        return map(operator.itemgetter(0), self.query(self.key))

    def values(self):
        return map(operator.itemgetter(0), self.query(self.value))

    def items(self):
        return iter(self)

    def get(self, k, default=None):
        try:
            return self[k]
        except KeyError:
            return default

    def pop(self, k, default=Sentinel):
        with self._database.transaction():
            node, is_single = self.convert_node(k)
            try:
                res = self[k]
            except KeyError:
                if default is Sentinel:
                    raise
                return default
            del(self[node])
        return res

    def clear(self):
        self.model.delete().execute()


class PickledKeyStore(KeyStore):
    def __init__(self, ordered=False, database=None):
        super(PickledKeyStore, self).__init__(PickleField(), ordered, database)

########NEW FILE########
__FILENAME__ = migrate
"""
Lightweight schema migrations.

NOTE: Currently tested with SQLite and Postgresql. MySQL may be missing some
features.

Example Usage
-------------

Instantiate a migrator:

    # Postgres example:
    my_db = PostgresqlDatabase(...)
    migrator = PostgresqlMigrator(my_db)

    # SQLite example:
    my_db = SqliteDatabase('my_database.db')
    migrator = SqliteMigrator(my_db)

Then you will use the `migrate` function to run various `Operation`s which
are generated by the migrator:

    migrate(
        migrator.add_column('some_table', 'column_name', CharField(default=''))
    )

Migrations are not run inside a transaction, so if you wish the migration to
run in a transaction you will need to wrap the call to `migrate` in a
transaction block, e.g.:

    with my_db.transaction():
        migrate(...)

Supported Operations
--------------------

Add new field(s) to an existing model:

    # Create your field instances. For non-null fields you must specify a
    # default value.
    pubdate_field = DateTimeField(null=True)
    comment_field = TextField(default='')

    # Run the migration, specifying the database table, field name and field.
    migrate(
        migrator.add_column('comment_tbl', 'pub_date', pubdate_field),
        migrator.add_column('comment_tbl', 'comment', comment_field),
    )

Renaming a field:

    # Specify the table, original name of the column, and its new name.
    migrate(
        migrator.rename_column('story', 'pub_date', 'publish_date'),
        migrator.rename_column('story', 'mod_date', 'modified_date'),
    )

Dropping a field:

    migrate(
        migrator.drop_column('story', 'some_old_field'),
    )

Making a field nullable or not nullable:

    # Note that when making a field not null that field must not have any
    # NULL values present.
    migrate(
        # Make `pub_date` allow NULL values.
        migrator.drop_not_null('story', 'pub_date'),

        # Prevent `modified_date` from containing NULL values.
        migrator.add_not_null('story', 'modified_date'),
    )

Renaming a table:

    migrate(
        migrator.rename_table('story', 'stories_tbl'),
    )

Adding an index:

    # Specify the table, column names, and whether the index should be
    # UNIQUE or not.
    migrate(
        # Create an index on the `pub_date` column.
        migrator.add_index('story', ('pub_date',), False),

        # Create a multi-column index on the `pub_date` and `status` fields.
        migrator.add_index('story', ('pub_date', 'status'), False),

        # Create a unique index on the category and title fields.
        migrator.add_index('story', ('category_id', 'title'), True),
    )

Dropping an index:

    # Specify the index name.
    migrate(migrator.drop_index('story_pub_date_status'))
"""
from collections import namedtuple
import functools
import re

from peewee import *
from peewee import CommaClause
from peewee import EnclosedClause
from peewee import Entity
from peewee import Expression
from peewee import Node
from peewee import OP_EQ


class Operation(object):
    """Encapsulate a single schema altering operation."""
    def __init__(self, migrator, method, *args, **kwargs):
        self.migrator = migrator
        self.method = method
        self.args = args
        self.kwargs = kwargs

    def _parse_node(self, node):
        compiler = self.migrator.database.compiler()
        return compiler.parse_node(node)

    def execute(self, node):
        sql, params = self._parse_node(node)
        self.migrator.database.execute_sql(sql, params)

    def _handle_result(self, result):
        if isinstance(result, Node):
            self.execute(result)
        elif isinstance(result, Operation):
            result.run()
        elif isinstance(result, (list, tuple)):
            for item in result:
                self._handle_result(item)

    def run(self):
        kwargs = self.kwargs.copy()
        kwargs['generate'] = True
        self._handle_result(
            getattr(self.migrator, self.method)(*self.args, **kwargs))


def operation(fn):
    @functools.wraps(fn)
    def inner(self, *args, **kwargs):
        generate = kwargs.pop('generate', False)
        if generate:
            return fn(self, *args, **kwargs)
        return Operation(self, fn.__name__, *args, **kwargs)
    return inner

class SchemaMigrator(object):
    def __init__(self, database):
        self.database = database

    @operation
    def apply_default(self, table, column_name, field):
        default = field.default
        if callable(default):
            default = default()

        return Clause(
            SQL('UPDATE'),
            Entity(table),
            SQL('SET'),
            Expression(
                Entity(column_name),
                OP_EQ,
                Param(field.db_value(default)),
                flat=True))

    @operation
    def alter_add_column(self, table, column_name, field):
        # Make field null at first.
        field_null, field.null = field.null, True
        field.name = field.db_column = column_name
        field_clause = self.database.compiler().field_definition(field)
        field.null = field_null
        return Clause(
            SQL('ALTER TABLE'),
            Entity(table),
            SQL('ADD COLUMN'),
            field_clause)

    @operation
    def add_column(self, table, column_name, field):
        # Adding a column is complicated by the fact that if there are rows
        # present and the field is non-null, then we need to first add the
        # column as a nullable field, then set the value, then add a not null
        # constraint.
        if not field.null and field.default is None:
            raise ValueError('%s is not null but has no default' % column_name)

        # Foreign key fields must explicitly specify a `to_field`.
        if isinstance(field, ForeignKeyField) and not field.to_field:
            raise ValueError('Foreign keys must specify a `to_field`.')

        operations = [self.alter_add_column(table, column_name, field)]

        # In the event the field is *not* nullable, update with the default
        # value and set not null.
        if not field.null:
            operations.extend([
                self.apply_default(table, column_name, field),
                self.add_not_null(table, column_name)])

        return operations

    @operation
    def drop_column(self, table, column_name, cascade=True):
        nodes = [
            SQL('ALTER TABLE'),
            Entity(table),
            SQL('DROP COLUMN'),
            Entity(column_name)]
        if cascade:
            nodes.append(SQL('CASCADE'))
        return Clause(*nodes)

    @operation
    def rename_column(self, table, old_name, new_name):
        return Clause(
            SQL('ALTER TABLE'),
            Entity(table),
            SQL('RENAME COLUMN'),
            Entity(old_name),
            SQL('TO'),
            Entity(new_name))

    def _alter_column(self, table, column):
        return [
            SQL('ALTER TABLE'),
            Entity(table),
            SQL('ALTER COLUMN'),
            Entity(column)]

    @operation
    def add_not_null(self, table, column):
        nodes = self._alter_column(table, column)
        nodes.append(SQL('SET NOT NULL'))
        return Clause(*nodes)

    @operation
    def drop_not_null(self, table, column):
        nodes = self._alter_column(table, column)
        nodes.append(SQL('DROP NOT NULL'))
        return Clause(*nodes)

    @operation
    def rename_table(self, old_name, new_name):
        return Clause(
            SQL('ALTER TABLE'),
            Entity(old_name),
            SQL('RENAME TO'),
            Entity(new_name))

    @operation
    def add_index(self, table, columns, unique=False):
        compiler = self.database.compiler()
        statement = 'CREATE UNIQUE INDEX' if unique else 'CREATE INDEX'
        return Clause(
            SQL(statement),
            Entity(compiler.index_name(table, columns)),
            SQL('ON'),
            Entity(table),
            EnclosedClause(*[Entity(column) for column in columns]))

    @operation
    def drop_index(self, table, index_name):
        return Clause(
            SQL('DROP INDEX'),
            Entity(index_name))


class PostgresqlMigrator(SchemaMigrator):
    def _primary_key_columns(self, tbl):
        query = """
            SELECT pg_attribute.attname
            FROM pg_index, pg_class, pg_attribute
            WHERE
                pg_class.oid = '%s'::regclass AND
                indrelid = pg_class.oid AND
                pg_attribute.attrelid = pg_class.oid AND
                pg_attribute.attnum = any(pg_index.indkey) AND
                indisprimary;
        """
        cursor = self.database.execute_sql(query % tbl)
        return [row[0] for row in cursor.fetchall()]

    @operation
    def rename_table(self, old_name, new_name):
        pk_names = self._primary_key_columns(old_name)
        ParentClass = super(PostgresqlMigrator, self)

        operations = [
            ParentClass.rename_table(old_name, new_name, generate=True)]

        if len(pk_names) == 1:
            # Check for existence of primary key sequence.
            seq_name = '%s_%s_seq' % (old_name, pk_names[0])
            query = """
                SELECT 1
                FROM information_schema.sequences
                WHERE sequence_name = %s
            """
            cursor = self.database.execute_sql(query, (seq_name,))
            if bool(cursor.fetchone()):
                new_seq_name = '%s_%s_seq' % (new_name, pk_names[0])
                operations.append(ParentClass.rename_table(
                    seq_name, new_seq_name, generate=True))

        return operations

_column_attributes = ('name', 'definition', 'null', 'pk', 'default', 'extra')

class MySQLColumn(namedtuple('_Column', _column_attributes)):
    @property
    def is_pk(self):
        return self.pk == 'PRI'

    @property
    def is_unique(self):
        return self.pk == 'UNI'

    @property
    def is_null(self):
        return self.null == 'YES'

    def sql(self, column_name=None, is_null=None):
        if is_null is None:
            is_null = self.is_null
        if column_name is None:
            column_name = self.name
        parts = [
            Entity(column_name),
            SQL(self.definition)]
        if self.is_unique:
            parts.append(SQL('UNIQUE'))
        if not is_null:
            parts.append(SQL('NOT NULL'))
        if self.is_pk:
            parts.append(SQL('PRIMARY KEY'))
        if self.extra:
            parts.append(SQL(extra))
        return Clause(*parts)


class MySQLMigrator(SchemaMigrator):
    def _get_column_definition(self, table, column_name):
        cursor = self.database.execute_sql('DESCRIBE %s;' % table)
        rows = cursor.fetchall()
        for row in rows:
            column = MySQLColumn(*row)
            if column.name == column_name:
                return column
        return False

    @operation
    def add_not_null(self, table, column):
        column = self._get_column_definition(table, column)
        return Clause(
            SQL('ALTER TABLE'),
            Entity(table),
            SQL('MODIFY'),
            column.sql(is_null=False))

    @operation
    def drop_not_null(self, table, column):
        column = self._get_column_definition(table, column)
        return Clause(
            SQL('ALTER TABLE'),
            Entity(table),
            SQL('MODIFY'),
            column.sql(is_null=True))

    @operation
    def rename_column(self, table, old_name, new_name):
        column = self._get_column_definition(table, old_name)
        return Clause(
            SQL('ALTER TABLE'),
            Entity(table),
            SQL('CHANGE'),
            Entity(old_name),
            column.sql(column_name=new_name))

    @operation
    def drop_index(self, table, index_name):
        return Clause(
            SQL('DROP INDEX'),
            Entity(index_name),
            SQL('ON'),
            Entity(table))


class SqliteMigrator(SchemaMigrator):
    """
    SQLite supports a subset of ALTER TABLE queries, view the docs for the
    full details http://sqlite.org/lang_altertable.html
    """
    column_re = re.compile('(.+?)\((.+)\)')
    column_split_re = re.compile(r'(?:[^,(]|\([^)]*\))+')
    column_name_re = re.compile('"?([\w]+)')

    def _get_column_names(self, table):
        res = self.database.execute_sql('select * from "%s" limit 1' % table)
        return [item[0] for item in res.description]

    def _get_create_table(self, table):
        res = self.database.execute_sql(
            'select sql from sqlite_master where type=? and name=? limit 1',
            ['table', table])
        return res.fetchone()[0]

    @operation
    def _update_column(self, table, column_to_update, fn):
        # Get the SQL used to create the given table.
        create_table = self._get_create_table(table)

        # Parse out the `CREATE TABLE` and column list portions of the query.
        raw_create, raw_columns = self.column_re.search(create_table).groups()

        # Clean up the individual column definitions.
        column_defs = [
            col.strip() for col in self.column_split_re.findall(raw_columns)]

        new_column_defs = []
        new_column_names = []
        original_column_names = []

        for column_def in column_defs:
            column_name, = self.column_name_re.match(column_def).groups()

            if column_name == column_to_update:
                new_column_def = fn(column_name, column_def)
                if new_column_def:
                    new_column_defs.append(new_column_def)
                    original_column_names.append(column_name)
                    column_name, = self.column_name_re.match(
                        new_column_def).groups()
                    new_column_names.append(column_name)
            else:
                new_column_defs.append(column_def)
                new_column_names.append(column_name)
                original_column_names.append(column_name)

        # Update the name of the new CREATE TABLE query.
        temp_table = table + '__tmp__'
        create = re.sub(
            '("?)%s("?)' % table,
            '\\1%s\\2' % temp_table,
            raw_create)

        # Create the new table.
        columns = ', '.join(new_column_defs)
        queries = [
            Clause(SQL('DROP TABLE IF EXISTS'), Entity(temp_table)),
            SQL('%s (%s)' % (create.strip(), columns))]

        # Populate new table.
        populate_table = Clause(
            SQL('INSERT INTO'),
            Entity(temp_table),
            EnclosedClause(*[Entity(col) for col in new_column_names]),
            SQL('SELECT'),
            CommaClause(*[Entity(col) for col in original_column_names]),
            SQL('FROM'),
            Entity(table))
        queries.append(populate_table)

        # Drop existing table and rename temp table.
        queries.append(Clause(
            SQL('DROP TABLE'),
            Entity(table)))
        queries.append(self.rename_table(temp_table, table))

        return queries

    @operation
    def drop_column(self, table, column_name, cascade=True):
        return self._update_column(table, column_name, lambda a, b: None)

    @operation
    def rename_column(self, table, old_name, new_name):
        def _rename(column_name, column_def):
            return column_def.replace(column_name, new_name)
        return self._update_column(table, old_name, _rename)

    @operation
    def add_not_null(self, table, column):
        def _add_not_null(column_name, column_def):
            return column_def + ' NOT NULL'
        return self._update_column(table, column, _add_not_null)

    @operation
    def drop_not_null(self, table, column):
        def _drop_not_null(column_name, column_def):
            return column_def.replace('NOT NULL', '')
        return self._update_column(table, column, _drop_not_null)


def migrate(*operations, **kwargs):
    for operation in operations:
        operation.run()

########NEW FILE########
__FILENAME__ = pool
"""
EXPERIMENTAL
============

Lightweight connection pooling for peewee.

In a single-threaded application, only one connection will be created. It will
be continually recycled until either it exceeds the stale timeout or is closed
explicitly (using `.manual_close()`).

In a multi-threaded application, up to `max_connections` will be opened.
"""
import heapq
import logging
import threading
import time

from peewee import MySQLDatabase
from peewee import PostgresqlDatabase

logger = logging.getLogger('peewee.pool')

class PooledDatabase(object):
    def __init__(self, database, max_connections=20, stale_timeout=None,
                 **kwargs):
        self.max_connections = max_connections
        self.stale_timeout = stale_timeout
        self._connections = []
        self._in_use = {}
        self._closed = set()
        self.conn_key = id

        super(PooledDatabase, self).__init__(database, **kwargs)

    def _connect(self, *args, **kwargs):
        while True:
            try:
                ts, conn = heapq.heappop(self._connections)
                key = self.conn_key(conn)
            except IndexError:
                ts = conn = None
                logger.debug('No connection available in pool.')
                break
            else:
                if self.stale_timeout and self._is_stale(ts):
                    logger.debug('Connection %s was stale, closing.', key)
                    self._close(conn, True)
                    ts = conn = None
                elif key in self._closed:
                    logger.debug('Connection %s was closed.', key)
                    ts = conn = None
                    self._closed.remove(key)
                else:
                    break

        if conn is None:
            if self.max_connections and (
                    len(self._in_use) >= self.max_connections):
                raise ValueError('Exceeded maximum connections.')
            conn = super(PooledDatabase, self)._connect(*args, **kwargs)
            ts = time.time()
            key = self.conn_key(conn)
            logger.debug('Created new connection %s.', key)

        self._in_use[key] = ts
        return conn

    def _is_stale(self, timestamp):
        return (time.time() - timestamp) > self.stale_timeout

    def _close(self, conn, close_conn=False):
        key = self.conn_key(conn)
        if close_conn:
            self._closed.add(key)
            super(PooledDatabase, self)._close(conn)
        elif key in self._in_use:
            logger.debug('Returning %s to pool.', key)
            ts = self._in_use[key]
            del self._in_use[key]
            heapq.heappush(self._connections, (ts, conn))

    def manual_close(self):
        """
        Close the underlying connection without returning it to the pool.
        """
        conn = self.get_conn()
        self.close()
        self._close(conn, close_conn=True)

    def close_all(self):
        """
        Close all connections managed by the pool.
        """
        for _, conn in self._connections:
            self._close(conn, close_conn=True)
        for conn in self._in_use:
            self._close(conn, close_conn=True)

class PooledMySQLDatabase(PooledDatabase, MySQLDatabase):
    pass

class PooledPostgresqlDatabase(PooledDatabase, PostgresqlDatabase):
    pass

########NEW FILE########
__FILENAME__ = postgres_ext
"""
Collection of postgres-specific extensions, currently including:

* Support for hstore, a key/value type storage
* Support for UUID field
"""
import uuid

from peewee import *
from peewee import Expression
from peewee import logger
from peewee import Node
from peewee import Param
from peewee import QueryCompiler
from peewee import SelectQuery

from psycopg2 import extensions
from psycopg2.extensions import adapt
from psycopg2.extensions import AsIs
from psycopg2.extensions import register_adapter
from psycopg2.extras import register_hstore
try:
    from psycopg2.extras import Json
except:
    Json = None


class _LookupNode(Node):
    def __init__(self, node, parts):
        self.node = node
        self.parts = parts
        super(_LookupNode, self).__init__()

    def clone_base(self):
        return type(self)(self.node, list(self.parts))

class JsonLookup(_LookupNode):
    def __getitem__(self, value):
        return JsonLookup(self.node, self.parts + [value])

class ObjectSlice(_LookupNode):
    @classmethod
    def create(cls, node, value):
        if isinstance(value, slice):
            parts = [value.start or 0, value.stop or 0]
        elif isinstance(value, int):
            parts = [value]
        else:
            parts = map(int, value.split(':'))
        return cls(node, parts)

    def __getitem__(self, value):
        return ObjectSlice.create(self, value)

class _Array(Node):
    def __init__(self, field, items):
        self.field = field
        self.items = items
        super(_Array, self).__init__()

def adapt_array(arr):
    conn = arr.field.model_class._meta.database.get_conn()
    items = adapt(arr.items)
    items.prepare(conn)
    return AsIs('%s::%s%s' % (
        items,
        arr.field.get_column_type(),
        '[]'* arr.field.dimensions))
register_adapter(_Array, adapt_array)


class IndexedField(Field):
    def __init__(self, index_type='GiST', *args, **kwargs):
        kwargs.setdefault('index', True)  # By default, use an index.
        super(IndexedField, self).__init__(*args, **kwargs)
        self.index_type = index_type


class ArrayField(IndexedField):
    def __init__(self, field_class=IntegerField, dimensions=1,
                 index_type='GIN', *args, **kwargs):
        self.__field = field_class(*args, **kwargs)
        self.dimensions = dimensions
        self.db_field = self.__field.get_db_field()
        super(ArrayField, self).__init__(
            index_type=index_type, *args, **kwargs)

    def __ddl_column__(self, column_type):
        sql = self.__field.__ddl_column__(column_type)
        sql.value += '[]' * self.dimensions
        return sql

    def __getitem__(self, value):
        return ObjectSlice.create(self, value)

    def contains(self, *items):
        return Expression(self, OP_ACONTAINS, _Array(self, list(items)))

    def contains_any(self, *items):
        return Expression(self, OP_ACONTAINS_ANY, _Array(self, list(items)))


class DateTimeTZField(DateTimeField):
    db_field = 'datetime_tz'


class HStoreField(IndexedField):
    db_field = 'hash'

    def __init__(self, *args, **kwargs):
        super(HStoreField, self).__init__(*args, **kwargs)

    def __getitem__(self, key):
        return Expression(self, OP_HKEY, Param(key))

    def keys(self):
        return fn.akeys(self)

    def values(self):
        return fn.avals(self)

    def items(self):
        return fn.hstore_to_matrix(self)

    def slice(self, *args):
        return fn.slice(self, Param(list(args)))

    def exists(self, key):
        return fn.exist(self, key)

    def defined(self, key):
        return fn.defined(self, key)

    def update(self, **data):
        return Expression(self, OP_HUPDATE, data)

    def delete(self, *keys):
        return fn.delete(self, Param(list(keys)))

    def contains(self, value):
        if isinstance(value, dict):
            return Expression(self, OP_HCONTAINS_DICT, Param(value))
        elif isinstance(value, (list, tuple)):
            return Expression(self, OP_HCONTAINS_KEYS, Param(value))
        return Expression(self, OP_HCONTAINS_KEY, value)

    def contains_any(self, *keys):
        return Expression(self, OP_HCONTAINS_ANY_KEY, Param(value))


class JSONField(Field):
    db_field = 'json'

    def __init__(self, *args, **kwargs):
        if Json is None:
            raise Exception('Your version of psycopg2 does not support JSON.')
        super(JSONField, self).__init__(*args, **kwargs)

    def db_value(self, value):
        return Json(value)

    def __getitem__(self, value):
        return JsonLookup(self, [value])


class UUIDField(Field):
    db_field = 'uuid'

    def db_value(self, value):
        return str(value)

    def python_value(self, value):
        return uuid.UUID(value)


OP_HKEY = 'key'
OP_HUPDATE = 'H@>'
OP_HCONTAINS_DICT = 'H?&'
OP_HCONTAINS_KEYS = 'H?'
OP_HCONTAINS_KEY = 'H?|'
OP_HCONTAINS_ANY_KEY = 'H||'
OP_ACONTAINS = 'A@>'
OP_ACONTAINS_ANY = 'A||'


class PostgresqlExtCompiler(QueryCompiler):
    def _create_index(self, model_class, fields, unique=False):
        clause = super(PostgresqlExtCompiler, self)._create_index(
            model_class, fields, unique)
        # Allow fields to specify a type of index.  HStore and Array fields
        # may want to use GiST indexes, for example.
        index_type = None
        for field in fields:
            if isinstance(field, IndexedField):
                index_type = field.index_type
        if index_type:
            clause.nodes.insert(-1, SQL('USING %s' % index_type))
        return clause

    def _parse(self, node, alias_map, conv):
        sql, params, unknown = super(PostgresqlExtCompiler, self)._parse(
            node, alias_map, conv)
        if unknown:
            if isinstance(node, ObjectSlice):
                unknown = False
                sql, params = self.parse_node(node.node, alias_map, conv)
                # Postgresql uses 1-based indexes.
                parts = [str(part + 1) for part in node.parts]
                sql = '%s[%s]' % (sql, ':'.join(parts))
            if isinstance(node, JsonLookup):
                unknown = False
                sql, params = self.parse_node(node.node, alias_map, conv)
                lookups = [sql]
                for part in node.parts:
                    part_sql, part_params = self.parse_node(
                        part, alias_map, conv)
                    lookups.append(part_sql)
                    params.extend(part_params)
                # The last lookup should be converted to text.
                head, tail = lookups[:-1], lookups[-1]
                sql = '->>'.join(('->'.join(head), tail))
        return sql, params, unknown


class PostgresqlExtDatabase(PostgresqlDatabase):
    compiler_class = PostgresqlExtCompiler

    def __init__(self, *args, **kwargs):
        self.server_side_cursors = kwargs.pop('server_side_cursors', False)
        super(PostgresqlExtDatabase, self).__init__(*args, **kwargs)

    def get_cursor(self, name=None):
        return self.get_conn().cursor(name=name)

    def execute_sql(self, sql, params=None, require_commit=True,
                    named_cursor=False):
        logger.debug((sql, params))
        use_named_cursor = (named_cursor or (
                            self.server_side_cursors and
                            sql.lower().startswith('select')))
        with self.exception_wrapper():
            if use_named_cursor:
                cursor = self.get_cursor(name=str(uuid.uuid1()))
                require_commit = False
            else:
                cursor = self.get_cursor()
            try:
                res = cursor.execute(sql, params or ())
            except Exception as exc:
                logger.exception('%s %s', sql, params)
                if self.sql_error_handler(exc, sql, params, require_commit):
                    raise
            else:
                if require_commit and self.get_autocommit():
                    self.commit()
        return cursor

    def _connect(self, database, **kwargs):
        conn = super(PostgresqlExtDatabase, self)._connect(database, **kwargs)
        register_hstore(conn, globally=True)
        return conn


class ServerSideSelectQuery(SelectQuery):
    @classmethod
    def clone_from_query(cls, query):
        clone = ServerSideSelectQuery(query.model_class)
        return query._clone_attributes(clone)

    def _execute(self):
        sql, params = self.sql()
        return self.database.execute_sql(
            sql, params, require_commit=False, named_cursor=True)


PostgresqlExtDatabase.register_fields({
    'datetime_tz': 'timestamp with time zone',
    'hash': 'hstore',
    'json': 'json',
    'uuid': 'uuid',
})
PostgresqlExtDatabase.register_ops({
    OP_HCONTAINS_DICT: '@>',
    OP_HCONTAINS_KEYS: '?&',
    OP_HCONTAINS_KEY: '?',
    OP_HCONTAINS_ANY_KEY: '?|',
    OP_HKEY: '->',
    OP_HUPDATE: '||',
    OP_ACONTAINS: '@>',
    OP_ACONTAINS_ANY: '&&',
})

def ServerSide(select_query):
    # Flag query for execution using server-side cursors.
    clone = ServerSideSelectQuery.clone_from_query(select_query)
    with clone.database.transaction():
        # Execute the query.
        query_result = clone.execute()

        # Patch QueryResultWrapper onto original query.
        select_query._qr = query_result

        # Expose generator for iterating over query.
        for obj in query_result.iterator():
            yield obj

########NEW FILE########
__FILENAME__ = proxy
"""
Proxy class useful for situations when you wish to defer the initialization of
an object.

Example:

    from peewee import *
    from playhouse.proxy import Proxy

    database_proxy = Proxy()  # Create a proxy for our db.

    class BaseModel(Model):
        class Meta:
            database = database_proxy  # Use proxy for our DB.

    class User(BaseModel):
        username = CharField()

    # Based on configuration, use a different database.
    if app.config['DEBUG']:
        database = SqliteDatabase('local.db')
    elif app.config['TESTING']:
        database = SqliteDatabase(':memory:')
    else:
        database = PostgresqlDatabase('mega_production_db')

    # Configure our proxy to use the db we specified in config.
    database_proxy.initialize(database)
"""

from peewee import Proxy  # Moved into peewee, here for backwards-compat.

########NEW FILE########
__FILENAME__ = read_slave
"""
Support for using a dedicated read-slave. The read database is specified as a
Model.Meta option, and will be used for SELECT statements:


master = PostgresqlDatabase('master')
read_slave = PostgresqlDatabase('read_slave')

class BaseModel(ReadSlaveModel):
    class Meta:
        database = master
        read_slaves = [read_slave]  # This database will be used for SELECTs.


# Now define your models as you would normally.
class User(BaseModel):
    username = CharField()

# To force a SELECT on the master database, you can instantiate the SelectQuery
# by hand:
master_select = SelectQuery(User).where(...)
"""
from peewee import *


class ReadSlaveModel(Model):
    @classmethod
    def _get_read_database(cls):
        if not getattr(cls._meta, 'read_slaves', None):
            return cls._meta.database
        current_idx = getattr(cls, '_read_slave_idx', -1)
        cls._read_slave_idx = (current_idx + 1) % len(cls._meta.read_slaves)
        return cls._meta.read_slaves[cls._read_slave_idx]

    @classmethod
    def select(cls, *args, **kwargs):
        query = super(ReadSlaveModel, cls).select(*args, **kwargs)
        query.database = cls._get_read_database()
        return query

    @classmethod
    def raw(cls, *args, **kwargs):
        query = super(ReadSlaveModel, cls).raw(*args, **kwargs)
        if query._sql.lower().startswith('select'):
            query.database = cls._get_read_database()
        return query

########NEW FILE########
__FILENAME__ = shortcuts
from peewee import *


def case(predicate, expression_tuples, default=None):
    """
    CASE statement builder.

    Example CASE statements:

        SELECT foo,
            CASE
                WHEN foo = 1 THEN "one"
                WHEN foo = 2 THEN "two"
                ELSE "?"
            END -- will be in column named "case" in postgres --
        FROM bar;

        -- equivalent to above --
        SELECT foo,
            CASE foo
                WHEN 1 THEN "one"
                WHEN 2 THEN "two"
                ELSE "?"
            END

    Corresponding peewee:

        # No predicate, use expressions.
        Bar.select(Bar.foo, case(None, (
            (Bar.foo == 1, "one"),
            (Bar.foo == 2, "two")), "?"))

        # Predicate, will test for equality.
        Bar.select(Bar.foo, case(Bar.foo, (
            (1, "one"),
            (2, "two")), "?"))
    """
    clauses = [SQL('CASE')]
    simple_case = predicate is not None
    if simple_case:
        clauses.append(predicate)
    for expr, value in expression_tuples:
        # If this is a simple case, each tuple will contain (value, value) pair
        # since the DB will be performing an equality check automatically.
        # Otherwise, we will have (expression, value) pairs.
        clauses.extend((SQL('WHEN'), expr, SQL('THEN'), value))
    if default is not None:
        clauses.extend((SQL('ELSE'), default))
    clauses.append(SQL('END'))
    return Clause(*clauses)

########NEW FILE########
__FILENAME__ = signals
"""
Provide django-style hooks for model events.
"""
from peewee import Model as _Model


class Signal(object):
    def __init__(self):
        self._flush()

    def connect(self, receiver, name=None, sender=None):
        name = name or receiver.__name__
        if name not in self._receivers:
            self._receivers[name] = (receiver, sender)
            self._receiver_list.append(name)
        else:
            raise ValueError('receiver named %s already connected' % name)

    def disconnect(self, receiver=None, name=None):
        if receiver:
            name = receiver.__name__
        if name:
            del self._receivers[name]
            self._receiver_list.remove(name)
        else:
            raise ValueError('a receiver or a name must be provided')

    def __call__(self, name=None, sender=None):
        def decorator(fn):
            self.connect(fn, name, sender)
            return fn
        return decorator

    def send(self, instance, *args, **kwargs):
        sender = type(instance)
        responses = []
        for name in self._receiver_list:
            r, s = self._receivers[name]
            if s is None or isinstance(instance, s):
                responses.append((r, r(sender, instance, *args, **kwargs)))
        return responses

    def _flush(self):
        self._receivers = {}
        self._receiver_list = []


pre_save = Signal()
post_save = Signal()
pre_delete = Signal()
post_delete = Signal()
pre_init = Signal()
post_init = Signal()


class Model(_Model):
    def __init__(self, *args, **kwargs):
        super(Model, self).__init__(*args, **kwargs)
        pre_init.send(self)

    def prepared(self):
        super(Model, self).prepared()
        post_init.send(self)

    def save(self, *args, **kwargs):
        created = not bool(self.get_id())
        pre_save.send(self, created=created)
        super(Model, self).save(*args, **kwargs)
        post_save.send(self, created=created)

    def delete_instance(self, *args, **kwargs):
        pre_delete.send(self)
        super(Model, self).delete_instance(*args, **kwargs)
        post_delete.send(self)

########NEW FILE########
__FILENAME__ = sqlcipher_ext
"""
Peewee integration with pysqlcipher.

Project page: https://github.com/leapcode/pysqlcipher/

**WARNING!!! EXPERIMENTAL!!!**

* Although this extention's code is short, it has not been propery
  peer-reviewed yet and may have introduced vulnerabilities.
* The code contains minimum values for `passphrase` length and
  `kdf_iter`, as well as a default value for the later.
  **Do not** regard these numbers as advice. Consult the docs at
  http://sqlcipher.net/sqlcipher-api/ and security experts.

Also note that this code relies on pysqlcipher and sqlcipher, and
the code there might have vulnerabilities as well, but since these
are widely used crypto modules, we can expect "short zero days" there.

Example usage:

     from peewee.playground.ciphersql_ext import SqlCipherDatabase
     db = SqlCipherDatabase('/path/to/my.db', passphrase="don'tuseme4real",
                            kdf_iter=1000000)

* `passphrase`: should be "long enough".
  Note that *length beats vocabulary* (much exponential), and even
  a lowercase-only passphrase like easytorememberyethardforotherstoguess
  packs more noise than 8 random printable chatacters and *can* be memorized.
* `kdf_iter`: Should be "as much as the weakest target machine can afford".

When opening an existing database, passphrase and kdf_iter should be identical
to the ones used when creating it.  If they're wrong, an exception will only be
raised **when you access the database**.

If you need to ask for an interactive passphrase, here's example code you can
put after the `db = ...` line:

    try:  # Just access the database so that it checks the encryption.
        db.get_tables()
    # We're looking for a DatabaseError with a specific error message.
    except peewee.DatabaseError as e:
        # Check whether the message *means* "passphrase is wrong"
        if e.message == 'file is encrypted or is not a database':
            raise Exception('Developer should Prompt user for passphrase again.')
        else:
            # A different DatabaseError. Raise it.
            raise e

See a more elaborate example with this code at
https://gist.github.com/thedod/11048875
"""
import datetime
import decimal

from peewee import *
from pysqlcipher import dbapi2 as sqlcipher

sqlcipher.register_adapter(decimal.Decimal, str)
sqlcipher.register_adapter(datetime.date, str)
sqlcipher.register_adapter(datetime.time, str)


class SqlCipherDatabase(SqliteDatabase):
    def _connect(self, database, **kwargs):
        passphrase = kwargs.pop('passphrase', '')
        kdf_iter = kwargs.pop('kdf_iter', 64000)

        if len(passphrase) < 8:
            raise ImproperlyConfigured(
                'SqlCipherDatabase passphrase should be at least eight '
                'character long.')

        if kdf_iter and kdf_iter < 10000:
            raise ImproperlyConfigured(
                 'SqlCipherDatabase kdf_iter should be at least 10000.')

        conn = sqlcipher.connect(database, **kwargs)
        self._add_conn_hooks(conn)
        conn.execute('PRAGMA key=\'{0}\''.format(passphrase.replace("'", "''")))
        conn.execute('PRAGMA kdf_iter={0:d}'.format(kdf_iter))
        return conn

########NEW FILE########
__FILENAME__ = sqlite_ext
"""
Sqlite3 extensions
==================

* Define custom aggregates, collations and functions
* Basic support for virtual tables
* Basic support for FTS3/4
* Specify isolation level in transactions

Example usage of the Full-text search:

class Document(FTSModel):
    title = TextField()  # type affinities are ignored in FTS
    content = TextField()

Document.create_table(tokenize='porter')  # use the porter stemmer

# populate the documents using normal operations.
for doc in documents:
    Document.create(title=doc['title'], content=doc['content'])

# use the "match" operation for FTS queries.
matching_docs = Document.select().where(match(Document.title, 'some query'))

# to sort by best match, use the custom "rank" function.
best_docs = (Document
             .select(Document, Document.rank('score'))
             .where(match(Document.title, 'some query'))
             .order_by(SQL('score').desc()))

# or use the shortcut method.
best_docs = Document.match('some phrase')
"""
import inspect
import math
import sqlite3
import struct

from peewee import *
from peewee import Expression
from peewee import QueryCompiler
from peewee import transaction


FTS_VER = sqlite3.sqlite_version_info[:3] >= (3, 7, 4) and 'FTS4' or 'FTS3'


class PrimaryKeyAutoIncrementField(PrimaryKeyField):
    def __ddl__(self, column_type):
        ddl = super(PrimaryKeyAutoIncrementField, self).__ddl__(column_type)
        return ddl + [SQL('AUTOINCREMENT')]

class SqliteQueryCompiler(QueryCompiler):
    """
    Subclass of QueryCompiler that can be used to construct virtual tables.
    """
    def _create_table(self, model_class, safe=False, options=None):
        clause = super(SqliteQueryCompiler, self)._create_table(
            model_class, safe=safe)

        if issubclass(model_class, VirtualModel):
            statement = 'CREATE VIRTUAL TABLE'
            # If we are using a special extension, need to insert that after the
            # table name node.
            clause.nodes.insert(2, SQL('USING %s' % model_class._extension))
        else:
            statement = 'CREATE TABLE'
        if safe:
            statement += 'IF NOT EXISTS'
        clause.nodes[0] = SQL(statement)  # Overwrite the statement.

        if options:
            columns_constraints = clause.nodes[-1]
            for k, v in options.items():
                if isinstance(v, Field):
                    value = v._as_entity(with_table=True)
                elif inspect.isclass(v) and issubclass(v, Model):
                    value = v._as_entity()
                else:
                    value = SQL(v)
                option = Clause(SQL(k), value)
                option.glue = '='
                columns_constraints.nodes.append(option)

        return clause

    def create_table(self, model_class, safe=False, options=None):
        return self.parse_node(self._create_table(model_class, safe, options))

class VirtualModel(Model):
    """Model class stored using a Sqlite virtual table."""
    _extension = ''

class FTSModel(VirtualModel):
    _extension = FTS_VER

    @classmethod
    def create_table(cls, fail_silently=False, **options):
        if fail_silently and cls.table_exists():
            return

        cls._meta.database.create_table(cls, options=options)
        cls._create_indexes()

    @classmethod
    def _fts_cmd(cls, cmd):
        tbl = cls._meta.db_table
        res = cls._meta.database.execute_sql(
            "INSERT INTO %s(%s) VALUES('%s');" % (tbl, tbl, cmd))
        return res.fetchone()

    @classmethod
    def optimize(cls):
        return cls._fts_cmd('optimize')

    @classmethod
    def rebuild(cls):
        return cls._fts_cmd('rebuild')

    @classmethod
    def integrity_check(cls):
        return cls._fts_cmd('integrity-check')

    @classmethod
    def merge(cls, blocks=200, segments=8):
        return cls._fts_cmd('merge=%s,%s' % (blocks, segments))

    @classmethod
    def automerge(cls, state=True):
        return cls._fts_cmd('automerge=%s' % (state and '1' or '0'))

    @classmethod
    def match(cls, term):
        """
        Generate a `MATCH` expression appropriate for searching this table.
        """
        return match(cls._as_entity(), term)

    @classmethod
    def rank(cls):
        return Rank(cls)

    @classmethod
    def bm25(cls, field=None, k=1.2, b=0.75):
        if field is None:
            field = find_best_search_field(cls)
        field_idx = cls._meta.get_field_index(field)
        match_info = fn.matchinfo(cls._as_entity(), 'pcxnal')
        return fn.bm25(match_info, field_idx, k, b)

    @classmethod
    def search(cls, term, alias='score'):
        """Full-text search using selected `term`."""
        return (cls
                .select(cls, cls.rank().alias(alias))
                .where(cls.match(term))
                .order_by(SQL(alias).desc()))

    @classmethod
    def search_bm25(cls, term, field=None, k=1.2, b=0.75, alias='score'):
        """Full-text search for selected `term` using BM25 algorithm."""
        if field is None:
            field = find_best_search_field(cls)
        return (cls
                .select(cls, cls.bm25(field, k, b).alias(alias))
                .where(cls.match(term))
                .order_by(SQL(alias).desc()))


class SqliteExtDatabase(SqliteDatabase):
    """
    Database class which provides additional Sqlite-specific functionality:

    * Register custom aggregates, collations and functions
    * Specify a row factory
    * Advanced transactions (specify isolation level)
    """
    compiler_class = SqliteQueryCompiler

    def __init__(self, *args, **kwargs):
        super(SqliteExtDatabase, self).__init__(*args, **kwargs)
        self._aggregates = {}
        self._collations = {}
        self._functions = {}
        self._row_factory = None
        self.register_function(rank, 'rank', 1)
        self.register_function(bm25, 'bm25', -1)

    def _connect(self, database, **kwargs):
        conn = super(SqliteExtDatabase, self)._connect(database, **kwargs)
        for name, (klass, num_params) in self._aggregates.items():
            conn.create_aggregate(name, num_params, klass)
        for name, fn in self._collations.items():
            conn.create_collation(name, fn)
        for name, (fn, num_params) in self._functions.items():
            conn.create_function(name, num_params, fn)
        if self._row_factory:
            conn.row_factory = self._row_factory
        return conn

    def _argc(self, fn):
        return len(inspect.getargspec(fn).args)

    def register_aggregate(self, klass, num_params, name=None):
        self._aggregates[name or klass.__name__.lower()] = (klass, num_params)

    def aggregate(self, num_params, name=None):
        def decorator(klass):
            self.register_aggregate(klass, num_params, name)
            return klass
        return decorator

    def register_collation(self, fn, name=None):
        name = name or fn.__name__
        def _collation(*args):
            expressions = args + (SQL('collate %s' % name),)
            return Clause(*expressions)
        fn.collation = _collation
        self._collations[name] = fn

    def collation(self, name=None):
        def decorator(fn):
            self.register_collation(fn, name)
            return fn
        return decorator

    def register_function(self, fn, name=None, num_params=None):
        if num_params is None:
            num_params = self._argc(fn)
        self._functions[name or fn.__name__] = (fn, num_params)

    def func(self, name=None, num_params=None):
        def decorator(fn):
            self.register_function(fn, name, num_params)
            return fn
        return decorator

    def unregister_aggregate(self, name):
        del(self._aggregates[name])

    def unregister_collation(self, name):
        del(self._collations[name])

    def unregister_function(self, name):
        del(self._functions[name])

    def row_factory(self, fn):
        self._row_factory = fn

    def create_table(self, model_class, safe=False, options=None):
        sql, params = self.compiler().create_table(model_class, safe, options)
        return self.execute_sql(sql, params)

    def create_index(self, model_class, field_name, unique=False):
        if issubclass(model_class, FTSModel):
            return
        return super(SqliteExtDatabase, self).create_index(
            model_class, field_name, unique)

    def granular_transaction(self, lock_type='deferred'):
        assert lock_type.lower() in ('deferred', 'immediate', 'exclusive')
        return granular_transaction(self, lock_type)


class granular_transaction(transaction):
    def __init__(self, db, lock_type='deferred'):
        self.db = db
        self.conn = self.db.get_conn()
        self.lock_type = lock_type

    def __enter__(self):
        self._orig_isolation = self.conn.isolation_level
        self.conn.isolation_level = self.lock_type
        return super(granular_transaction, self).__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            super(granular_transaction, self).__exit__(
                exc_type, exc_val, exc_tb)
        finally:
            self.conn.isolation_level = self._orig_isolation


OP_MATCH = 'match'
SqliteExtDatabase.register_ops({
    OP_MATCH: 'MATCH',
})

def match(lhs, rhs):
    return Expression(lhs, OP_MATCH, rhs)

# Shortcut for calculating ranks.
Rank = lambda model: fn.rank(fn.matchinfo(model._as_entity()))
BM25 = lambda mc, idx: fn.bm25(fn.matchinfo(mc._as_entity(), 'pcxnal'), idx)

def find_best_search_field(model_class):
    for field_class in [TextField, CharField]:
        for model_field in model_class._meta.get_fields():
            if isinstance(model_field, field_class):
                return model_field
    return model_class._meta.get_fields()[-1]

def _parse_match_info(buf):
    # see http://sqlite.org/fts3.html#matchinfo
    bufsize = len(buf) # length in bytes
    return [struct.unpack('@I', buf[i:i+4])[0] for i in range(0, bufsize, 4)]

# Ranking implementation, which parse matchinfo.
def rank(raw_match_info):
    # handle match_info called w/default args 'pcx' - based on the example rank
    # function http://sqlite.org/fts3.html#appendix_a
    match_info = _parse_match_info(raw_match_info)
    score = 0.0
    p, c = match_info[:2]
    for phrase_num in range(p):
        phrase_info_idx = 2 + (phrase_num * c * 3)
        for col_num in range(c):
            col_idx = phrase_info_idx + (col_num * 3)
            x1, x2 = match_info[col_idx:col_idx + 2]
            if x1 > 0:
                score += float(x1) / x2
    return score

# Okapi BM25 ranking implementation (FTS4 only).
def bm25(raw_match_info, column_index, k1=1.2, b=0.75):
    """
    Usage:

        # Format string *must* be pcxnal
        # Second parameter to bm25 specifies the index of the column, on
        # the table being queries.
        bm25(matchinfo(document_tbl, 'pcxnal'), 1) AS rank
    """
    match_info = _parse_match_info(raw_match_info)
    score = 0.0
    # p, 1 --> num terms
    # c, 1 --> num cols
    # x, (3 * p * c) --> for each phrase/column,
    #     term_freq for this column
    #     term_freq for all columns
    #     total documents containing this term
    # n, 1 --> total rows in table
    # a, c --> for each column, avg number of tokens in this column
    # l, c --> for each column, length of value for this column (in this row)
    # s, c --> ignore
    p, c = match_info[:2]
    n_idx = 2 + (3 * p * c)
    a_idx = n_idx + 1
    l_idx = a_idx + c
    n = match_info[n_idx]
    a = match_info[a_idx: a_idx + c]
    l = match_info[l_idx: l_idx + c]

    total_docs = n
    avg_length = float(a[column_index])
    doc_length = float(l[column_index])
    if avg_length == 0:
        D = 0
    else:
        D = 1 - b + (b * (doc_length / avg_length))

    for phrase in range(p):
        # p, c, p0c01, p0c02, p0c03, p0c11, p0c12, p0c13, p1c01, p1c02, p1c03..
        # So if we're interested in column <i>, the counts will be at indexes
        x_idx = 2 + (3 * column_index * (phrase + 1))
        term_freq = float(match_info[x_idx])
        term_matches = float(match_info[x_idx + 2])

        # The `max` check here is based on a suggestion in the Wikipedia
        # article. For terms that are common to a majority of documents, the
        # idf function can return negative values. Applying the max() here
        # weeds out those values.
        idf = max(
            math.log(
                (total_docs - term_matches + 0.5) /
                (term_matches + 0.5)),
            0)

        denom = term_freq + (k1 * D)
        if denom == 0:
            rhs = 0
        else:
            rhs = (term_freq * (k1 + 1)) / denom

        score += (idf * rhs)

    return score

########NEW FILE########
__FILENAME__ = tests_apsw
import apsw
import datetime
import unittest

from playhouse.apsw_ext import *


db = APSWDatabase(':memory:')

class BaseModel(Model):
    class Meta:
        database = db

class User(BaseModel):
    username = CharField()

class Message(BaseModel):
    user = ForeignKeyField(User)
    message = TextField()
    pub_date = DateTimeField()
    published = BooleanField()


class APSWTestCase(unittest.TestCase):
    def setUp(self):
        Message.drop_table(True)
        User.drop_table(True)
        User.create_table()
        Message.create_table()

    def test_select_insert(self):
        users = ('u1', 'u2', 'u3')
        for user in users:
            User.create(username=user)

        self.assertEqual([x.username for x in User.select()], ['u1', 'u2', 'u3'])
        self.assertEqual([x.username for x in User.select().filter(username='x')], [])
        self.assertEqual([x.username for x in User.select().filter(username__in=['u1', 'u3'])], ['u1', 'u3'])

        dt = datetime.datetime(2012, 1, 1, 11, 11, 11)
        Message.create(user=User.get(username='u1'), message='herps', pub_date=dt, published=True)
        Message.create(user=User.get(username='u2'), message='derps', pub_date=dt, published=False)

        m1 = Message.get(message='herps')
        self.assertEqual(m1.user.username, 'u1')
        self.assertEqual(m1.pub_date, dt)
        self.assertEqual(m1.published, True)

        m2 = Message.get(message='derps')
        self.assertEqual(m2.user.username, 'u2')
        self.assertEqual(m2.pub_date, dt)
        self.assertEqual(m2.published, False)

    def test_update_delete(self):
        u1 = User.create(username='u1')
        u2 = User.create(username='u2')

        u1.username = 'u1-modified'
        u1.save()

        self.assertEqual(User.select().count(), 2)
        self.assertEqual(User.get(username='u1-modified').id, u1.id)

        u1.delete_instance()
        self.assertEqual(User.select().count(), 1)

    def test_transaction_handling(self):
        dt = datetime.datetime(2012, 1, 1, 11, 11, 11)

        def do_ctx_mgr_error():
            with db.transaction():
                User.create(username='u1')
                raise ValueError

        self.assertRaises(ValueError, do_ctx_mgr_error)
        self.assertEqual(User.select().count(), 0)

        def do_ctx_mgr_success():
            with db.transaction():
                u = User.create(username='test')
                Message.create(message='testing', user=u, pub_date=dt, published=1)

        do_ctx_mgr_success()
        self.assertEqual(User.select().count(), 1)
        self.assertEqual(Message.select().count(), 1)

        @db.commit_on_success
        def create_error():
            u = User.create(username='test')
            Message.create(message='testing', user=u, pub_date=dt, published=1)
            raise ValueError

        self.assertRaises(ValueError, create_error)
        self.assertEqual(User.select().count(), 1)

        @db.commit_on_success
        def create_success():
            u = User.create(username='test')
            Message.create(message='testing', user=u, pub_date=dt, published=1)

        create_success()
        self.assertEqual(User.select().count(), 2)
        self.assertEqual(Message.select().count(), 2)

########NEW FILE########
__FILENAME__ = tests_berkeleydb
import os
import shutil
import unittest

from peewee import IntegrityError
from peewee import sort_models_topologically
from playhouse.berkeleydb import *

DATABASE_FILE = 'tmp.bdb.db'
database = BerkeleyDatabase(DATABASE_FILE)

class BaseModel(Model):
    class Meta:
        database = database

class Person(BaseModel):
    name = CharField(unique=True)

class Message(BaseModel):
    person = ForeignKeyField(Person, related_name='messages')
    body = TextField()


MODELS = [
    Person,
    Message,
]
CREATE = sort_models_topologically(MODELS)
DROP = reversed(CREATE)


class TestBerkeleyDatabase(unittest.TestCase):
    def setUp(self):
        with database.transaction():
            for model_class in DROP:
                model_class.drop_table(True)
            for model_class in CREATE:
                model_class.create_table(True)

    def tearDown(self):
        database.close()
        os.unlink(DATABASE_FILE)
        shutil.rmtree('%s-journal' % DATABASE_FILE)

    def test_storage_retrieval(self):
        pc = Person.create(name='charlie')
        ph = Person.create(name='huey')

        for i in range(3):
            Message.create(person=pc, body='message-%s' % i)

        self.assertEqual(Message.select().count(), 3)
        self.assertEqual(Person.select().count(), 2)
        self.assertEqual(
            [msg.body for msg in pc.messages.order_by(Message.id)],
            ['message-0', 'message-1', 'message-2'])
        self.assertEqual(list(ph.messages), [])

    def test_transaction(self):
        with database.transaction():
            Person.create(name='charlie')

        self.assertEqual(Person.select().count(), 1)

        @database.commit_on_success
        def rollback():
            Person.create(name='charlie')

        self.assertRaises(IntegrityError, rollback)
        self.assertEqual(Person.select().count(), 1)

########NEW FILE########
__FILENAME__ = tests_csv_loader
import csv
import unittest
from contextlib import contextmanager
from datetime import date
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
from textwrap import dedent

from playhouse.csv_loader import *


class TestRowConverter(RowConverter):
    @contextmanager
    def get_reader(self, csv_data, **reader_kwargs):
        reader = csv.reader(StringIO(csv_data), **reader_kwargs)
        yield reader

class TestLoader(Loader):
    @contextmanager
    def get_reader(self, csv_data, **reader_kwargs):
        reader = csv.reader(StringIO(csv_data), **reader_kwargs)
        yield reader

    def get_converter(self):
        return self.converter or TestRowConverter(
            self.database,
            has_header=self.has_header,
            sample_size=self.sample_size)

db = SqliteDatabase(':memory:')

class TestCSVConversion(unittest.TestCase):
    header = 'id,name,dob,salary,is_admin'
    simple = '10,"F1 L1",1983-01-01,10000,t'
    float_sal = '20,"F2 L2",1983-01-02,20000.5,f'
    only_name = ',"F3 L3",,,'
    mismatch = 'foo,F4 L4,dob,sal,x'

    def setUp(self):
        db.execute_sql('drop table if exists csv_test;')

    def build_csv(self, *lines):
        return '\r\n'.join(lines)

    def load(self, *lines, **loader_kwargs):
        csv = self.build_csv(*lines)
        loader_kwargs['file_or_name'] = csv
        loader_kwargs.setdefault('db_table', 'csv_test')
        loader_kwargs.setdefault('db_or_model', db)
        return TestLoader(**loader_kwargs).load()

    def assertData(self, ModelClass, expected):
        name_field = ModelClass._meta.get_fields()[2]
        query = ModelClass.select().order_by(name_field).tuples()
        self.assertEqual([row[1:] for row in query], expected)

    def test_defaults(self):
        ModelClass = self.load(
            self.header,
            self.simple,
            self.float_sal,
            self.only_name)
        self.assertData(ModelClass, [
            (10, 'F1 L1', date(1983, 1, 1), 10000., 't'),
            (20, 'F2 L2', date(1983, 1, 2), 20000.5, 'f'),
            (0, 'F3 L3', None, 0., ''),
        ])

    def test_no_header(self):
        ModelClass = self.load(
            self.simple,
            self.float_sal,
            field_names=['f1', 'f2', 'f3', 'f4', 'f5'],
            has_header=False)
        self.assertEqual(ModelClass._meta.get_field_names(), [
            '_auto_pk', 'f1', 'f2', 'f3', 'f4', 'f5'])
        self.assertData(ModelClass, [
            (10, 'F1 L1', date(1983, 1, 1), 10000., 't'),
            (20, 'F2 L2', date(1983, 1, 2), 20000.5, 'f')])

    def test_no_header_no_fieldnames(self):
        ModelClass = self.load(
            self.simple,
            self.float_sal,
            has_header=False)
        self.assertEqual(ModelClass._meta.get_field_names(), [
            '_auto_pk', 'field_0', 'field_1', 'field_2', 'field_3', 'field_4'])

    def test_mismatch_types(self):
        ModelClass = self.load(
            self.header,
            self.simple,
            self.mismatch)
        self.assertData(ModelClass, [
            ('10', 'F1 L1', '1983-01-01', '10000', 't'),
            ('foo', 'F4 L4', 'dob', 'sal', 'x')])

    def test_fields(self):
        fields = [
            IntegerField(),
            CharField(),
            DateField(),
            FloatField(),
            CharField()]
        ModelClass = self.load(
            self.header,
            self.simple,
            self.float_sal,
            fields=fields)
        self.assertEqual(
            list(map(type, fields)),
            list(map(type, ModelClass._meta.get_fields()[1:])))
        self.assertData(ModelClass, [
            (10, 'F1 L1', date(1983, 1, 1), 10000., 't'),
            (20, 'F2 L2', date(1983, 1, 2), 20000.5, 'f')])

########NEW FILE########
__FILENAME__ = tests_djpeewee
from datetime import timedelta
import unittest

from peewee import *
from peewee import print_
try:
    import django
except ImportError:
    django = None


if django is not None:
    from django.conf import settings
    settings.configure(
        DATABASES={
            'default': {
                'engine': 'django.db.backends.sqlite3',
                'name': ':memory:'}},
    )
    from django.db import models
    from playhouse.djpeewee import translate

    # Django model definitions.
    class Simple(models.Model):
        char_field = models.CharField(max_length=1)
        int_field = models.IntegerField()

    class User(models.Model):
        username = models.CharField(max_length=255)

        class Meta:
            db_table = 'user_tbl'

    class Post(models.Model):
        author = models.ForeignKey(User, related_name='posts')
        content = models.TextField()

    class Comment(models.Model):
        post = models.ForeignKey(Post, related_name='comments')
        commenter = models.ForeignKey(User, related_name='comments')
        comment = models.TextField()

    class Tag(models.Model):
        tag = models.CharField()
        posts = models.ManyToManyField(Post)

    class Event(models.Model):
        start_time = models.DateTimeField()
        end_time = models.DateTimeField()
        title = models.CharField()

        class Meta:
            db_table = 'events_tbl'

    class Category(models.Model):
        parent = models.ForeignKey('self', null=True)

    class A(models.Model):
        a_field = models.IntegerField()
        b = models.ForeignKey('B', null=True, related_name='as')

    class B(models.Model):
        a = models.ForeignKey(A, related_name='bs')

    class C(models.Model):
        b = models.ForeignKey(B, related_name='cs')

    class Parent(models.Model):
        pass

    class Child(Parent):
        pass


    class TestDjPeewee(unittest.TestCase):
        def assertFields(self, model, expected):
            self.assertEqual(len(model._meta.fields), len(expected))
            zipped = zip(model._meta.get_fields(), expected)
            for (model_field, (name, field_type)) in zipped:
                self.assertEqual(model_field.name, name)
                self.assertTrue(type(model_field) is field_type)

        def test_simple(self):
            P = translate(Simple)
            self.assertEqual(list(P.keys()), ['Simple'])
            self.assertFields(P['Simple'], [
                ('id', PrimaryKeyField),
                ('char_field', CharField),
                ('int_field', IntegerField),
            ])

        def test_graph(self):
            P = translate(User, Tag, Comment)
            self.assertEqual(sorted(P.keys()), [
                'Comment',
                'Post',
                'Tag',
                'Tag_posts',
                'User'])

            # Test the models that were found.
            user = P['User']
            self.assertFields(user, [
                ('id', PrimaryKeyField),
                ('username', CharField)])
            self.assertEqual(user.posts.rel_model, P['Post'])
            self.assertEqual(user.comments.rel_model, P['Comment'])

            post = P['Post']
            self.assertFields(post, [
                ('id', PrimaryKeyField),
                ('author', ForeignKeyField),
                ('content', TextField)])
            self.assertEqual(post.comments.rel_model, P['Comment'])

            comment = P['Comment']
            self.assertFields(comment, [
                ('id', PrimaryKeyField),
                ('post', ForeignKeyField),
                ('commenter', ForeignKeyField),
                ('comment', TextField)])

            tag = P['Tag']
            self.assertFields(tag, [
                ('id', PrimaryKeyField),
                ('tag', CharField)])

            thru = P['Tag_posts']
            self.assertFields(thru, [
                ('id', PrimaryKeyField),
                ('tag', ForeignKeyField),
                ('post', ForeignKeyField)])

        def test_fk_query(self):
            trans = translate(User, Post, Comment, Tag)
            U = trans['User']
            P = trans['Post']
            C = trans['Comment']

            query = (U.select()
                     .join(P)
                     .join(C)
                     .where(C.comment == 'test'))
            sql, params = query.sql()
            self.assertEqual(
                sql,
                'SELECT t1."id", t1."username" FROM "user_tbl" AS t1 '
                'INNER JOIN "playhouse_post" AS t2 '
                'ON (t1."id" = t2."author_id") '
                'INNER JOIN "playhouse_comment" AS t3 '
                'ON (t2."id" = t3."post_id") WHERE (t3."comment" = %s)')
            self.assertEqual(params, ['test'])

        def test_m2m_query(self):
            trans = translate(Post, Tag)
            P = trans['Post']
            U = trans['User']
            T = trans['Tag']
            TP = trans['Tag_posts']

            query = (P.select()
                     .join(TP)
                     .join(T)
                     .where(T.tag == 'test'))
            sql, params = query.sql()
            self.assertEqual(
                sql,
                'SELECT t1."id", t1."author_id", t1."content" '
                'FROM "playhouse_post" AS t1 '
                'INNER JOIN "playhouse_tag_posts" AS t2 '
                'ON (t1."id" = t2."post_id") '
                'INNER JOIN "playhouse_tag" AS t3 '
                'ON (t2."tag_id" = t3."id") WHERE (t3."tag" = %s)')
            self.assertEqual(params, ['test'])

        def test_docs_example(self):
            # The docs don't lie.
            PEvent = translate(Event)['Event']
            hour = timedelta(hours=1)
            query = (PEvent
                     .select()
                     .where(
                         (PEvent.end_time - PEvent.start_time) > hour))
            sql, params = query.sql()
            self.assertEqual(
                sql,
                'SELECT t1."id", t1."start_time", t1."end_time", t1."title" '
                'FROM "events_tbl" AS t1 '
                'WHERE ((t1."end_time" - t1."start_time") > %s)')
            self.assertEqual(params, [hour])

        def test_self_referential(self):
            trans = translate(Category)
            self.assertFields(trans['Category'], [
                ('id', PrimaryKeyField),
                ('parent', IntegerField)])

        def test_cycle(self):
            trans = translate(A)
            self.assertFields(trans['A'], [
                ('id', PrimaryKeyField),
                ('a_field', IntegerField),
                ('b', ForeignKeyField)])
            self.assertFields(trans['B'], [
                ('id', PrimaryKeyField),
                ('a', IntegerField)])

            trans = translate(B)
            self.assertFields(trans['A'], [
                ('id', PrimaryKeyField),
                ('a_field', IntegerField),
                ('b', IntegerField)])
            self.assertFields(trans['B'], [
                ('id', PrimaryKeyField),
                ('a', ForeignKeyField)])

        def test_max_depth(self):
            trans = translate(C, max_depth=1)
            self.assertFields(trans['C'], [
                ('id', PrimaryKeyField),
                ('b', ForeignKeyField)])
            self.assertFields(trans['B'], [
                ('id', PrimaryKeyField),
                ('a', IntegerField)])

        def test_exclude(self):
            trans = translate(Comment, exclude=(User,))
            self.assertFields(trans['Post'], [
                ('id', PrimaryKeyField),
                ('author', IntegerField),
                ('content', TextField)])
            self.assertEqual(
                trans['Post'].comments.rel_model,
                trans['Comment'])

            self.assertFields(trans['Comment'], [
                ('id', PrimaryKeyField),
                ('post', ForeignKeyField),
                ('commenter', IntegerField),
                ('comment', TextField)])

        def test_backrefs(self):
            trans = translate(User, backrefs=True)
            self.assertEqual(sorted(trans.keys()), [
                'Comment',
                'Post',
                'User'])

        def test_inheritance(self):
            trans = translate(Parent)
            self.assertEqual(list(trans.keys()), ['Parent'])
            self.assertFields(trans['Parent'], [
                ('id', PrimaryKeyField),])

            trans = translate(Child)
            self.assertEqual(sorted(trans.keys()), ['Child', 'Parent'])
            self.assertFields(trans['Child'], [
                ('id', PrimaryKeyField),
                ('parent_ptr', ForeignKeyField)])


else:
    print_('Skipping djpeewee tests, Django not found.')

########NEW FILE########
__FILENAME__ = tests_gfk
import unittest

from peewee import *
from playhouse.gfk import *


db = SqliteDatabase(':memory:')

class BaseModel(Model):
    class Meta:
        database = db

    def add_tag(self, tag):
        t = Tag(tag=tag)
        t.object = self
        t.save()
        return t

class Tag(BaseModel):
    tag = CharField()

    object_type = CharField(null=True)
    object_id = IntegerField(null=True)
    object = GFKField()

    class Meta:
        order_by = ('tag',)


class Appetizer(BaseModel):
    name = CharField()
    tags = ReverseGFK(Tag)

class Entree(BaseModel):
    name = CharField()
    tags = ReverseGFK(Tag)

class Dessert(BaseModel):
    name = CharField()
    tags = ReverseGFK(Tag)



class GFKTestCase(unittest.TestCase):
    data = {
        Appetizer: (
            ('wings', ('fried', 'spicy')),
            ('mozzarella sticks', ('fried', 'sweet')),
            ('potstickers', ('fried',)),
            ('edamame', ('salty',)),
        ),
        Entree: (
            ('phad thai', ('spicy',)),
            ('fried chicken', ('fried', 'salty')),
            ('tacos', ('fried', 'spicy')),
        ),
        Dessert: (
            ('sundae', ('sweet',)),
            ('churro', ('fried', 'sweet')),
        )
    }
    def setUp(self):
        Tag.create_table(True)
        Appetizer.create_table(True)
        Entree.create_table(True)
        Dessert.create_table(True)

    def tearDown(self):
        Tag.drop_table()
        Appetizer.drop_table()
        Entree.drop_table()
        Dessert.drop_table()

    def create(self):
        for model, foods in self.data.items():
            for name, tags in foods:
                inst = model.create(name=name)
                for tag in tags:
                    inst.add_tag(tag)

    def test_creation(self):
        t = Tag.create(tag='a tag')
        t.object = t
        t.save()

        t_db = Tag.get(Tag.id == t.id)
        self.assertEqual(t_db.object_id, t_db.get_id())
        self.assertEqual(t_db.object_type, 'tag')
        self.assertEqual(t_db.object, t_db)

    def test_gfk_api(self):
        self.create()

        # test instance api
        for model, foods in self.data.items():
            for food, tags in foods:
                inst = model.get(model.name == food)
                self.assertEqual([t.tag for t in inst.tags], list(tags))

        # test class api and ``object`` api
        apps_tags = [(t.tag, t.object.name) for t in Appetizer.tags.order_by(Tag.id)]
        data_tags = []
        for food, tags in self.data[Appetizer]:
            for t in tags:
                data_tags.append((t, food))

        self.assertEqual(apps_tags, data_tags)

    def test_missing(self):
        t = Tag.create(tag='sour')
        self.assertEqual(t.object, None)

        t.object_type = 'appetizer'
        t.object_id = 1
        # accessing the descriptor will raise a DoesNotExist
        self.assertRaises(Appetizer.DoesNotExist, getattr, t, 'object')

        t.object_type = 'unknown'
        t.object_id = 1
        self.assertRaises(AttributeError, getattr, t, 'object')

    def test_set_reverse(self):
        # assign query
        e = Entree.create(name='phad thai')
        s = Tag.create(tag='spicy')
        p = Tag.create(tag='peanuts')
        t = Tag.create(tag='thai')
        b = Tag.create(tag='beverage')

        e.tags = Tag.select().where(Tag.tag != 'beverage')
        self.assertEqual([t.tag for t in e.tags], ['peanuts', 'spicy', 'thai'])

        e = Entree.create(name='panang curry')
        c = Tag.create(tag='coconut')

        e.tags = [p, t, c, s]
        self.assertEqual([t.tag for t in e.tags], ['coconut', 'peanuts', 'spicy', 'thai'])

########NEW FILE########
__FILENAME__ = tests_kv
import threading
import unittest

from peewee import *
from playhouse.kv import PickledKeyStore
from playhouse.kv import KeyStore


class KeyStoreTestCase(unittest.TestCase):
    def setUp(self):
        self.kv = KeyStore(CharField())
        self.ordered_kv = KeyStore(CharField(), ordered=True)
        self.pickled_kv = PickledKeyStore(ordered=True)
        self.kv.clear()

    def test_storage(self):
        self.kv['a'] = 'A'
        self.kv['b'] = 1
        self.assertEqual(self.kv['a'], 'A')
        self.assertEqual(self.kv['b'], '1')
        self.assertRaises(KeyError, self.kv.__getitem__, 'c')

        del(self.kv['a'])
        self.assertRaises(KeyError, self.kv.__getitem__, 'a')

        self.kv['a'] = 'A'
        self.kv['c'] = 'C'
        self.assertEqual(self.kv[self.kv.key << ('a', 'c')], ['A', 'C'])

        self.kv[self.kv.key << ('a', 'c')] = 'X'
        self.assertEqual(self.kv['a'], 'X')
        self.assertEqual(self.kv['b'], '1')
        self.assertEqual(self.kv['c'], 'X')

        del(self.kv[self.kv.key << ('a', 'c')])
        self.assertRaises(KeyError, self.kv.__getitem__, 'a')
        self.assertRaises(KeyError, self.kv.__getitem__, 'c')
        self.assertEqual(self.kv['b'], '1')

        self.pickled_kv['a'] = 'A'
        self.pickled_kv['b'] = 1.1
        self.assertEqual(self.pickled_kv['a'], 'A')
        self.assertEqual(self.pickled_kv['b'], 1.1)

    def test_container_properties(self):
        self.kv['x'] = 'X'
        self.kv['y'] = 'Y'
        self.assertEqual(len(self.kv), 2)
        self.assertTrue('x' in self.kv)
        self.assertFalse('a' in self.kv)

    def test_dict_methods(self):
        for kv in (self.ordered_kv, self.pickled_kv):
            kv['a'] = 'A'
            kv['c'] = 'C'
            kv['b'] = 'B'
            self.assertEqual(list(kv.keys()), ['a', 'b', 'c'])
            self.assertEqual(list(kv.values()), ['A', 'B', 'C'])
            self.assertEqual(list(kv.items()), [
                ('a', 'A'),
                ('b', 'B'),
                ('c', 'C'),
            ])

    def test_iteration(self):
        for kv in (self.ordered_kv, self.pickled_kv):
            kv['a'] = 'A'
            kv['c'] = 'C'
            kv['b'] = 'B'

            items = list(kv)
            self.assertEqual(items, [
                ('a', 'A'),
                ('b', 'B'),
                ('c', 'C'),
            ])

    def test_shared_mem(self):
        self.kv['a'] = 'xxx'
        self.assertEqual(self.ordered_kv['a'], 'xxx')

        def set_k():
            kv_t = KeyStore(CharField())
            kv_t['b'] = 'yyy'
        t = threading.Thread(target=set_k)
        t.start()
        t.join()

        self.assertEqual(self.kv['b'], 'yyy')

    def test_get(self):
        self.kv['a'] = 'A'
        self.kv['b'] = 'B'
        self.assertEqual(self.kv.get('a'), 'A')
        self.assertEqual(self.kv.get('x'), None)
        self.assertEqual(self.kv.get('x', 'y'), 'y')

        self.assertEqual(
            list(self.kv.get(self.kv.key << ('a', 'b'))),
            ['A', 'B'])
        self.assertEqual(
            list(self.kv.get(self.kv.key << ('x', 'y'))),
            [])

    def test_pop(self):
        self.ordered_kv['a'] = 'A'
        self.ordered_kv['b'] = 'B'
        self.ordered_kv['c'] = 'C'

        self.assertEqual(self.ordered_kv.pop('a'), 'A')
        self.assertEqual(list(self.ordered_kv.keys()), ['b', 'c'])

        self.assertRaises(KeyError, self.ordered_kv.pop, 'x')
        self.assertEqual(self.ordered_kv.pop('x', 'y'), 'y')

        self.assertEqual(
            list(self.ordered_kv.pop(self.ordered_kv.key << ['b', 'c'])),
            ['B', 'C'])

        self.assertEqual(list(self.ordered_kv.keys()), [])

try:
    import psycopg2
except ImportError:
    psycopg2 = None

if psycopg2 is not None:
    db = PostgresqlDatabase('peewee_test')

    class PostgresqlKeyStoreTestCase(unittest.TestCase):
        def setUp(self):
            self.kv = KeyStore(CharField(), ordered=True, database=db)
            self.kv.clear()

        def test_non_native_upsert(self):
            self.kv['a'] = 'A'
            self.kv['b'] = 'B'
            self.assertEqual(self.kv['a'], 'A')

            self.kv['a'] = 'C'
            self.assertEqual(self.kv['a'], 'C')

########NEW FILE########
__FILENAME__ = tests_migrate
import datetime
import os
import unittest

from peewee import *
from peewee import print_
from playhouse.migrate import *

try:
    import psycopg2
except ImportError:
    psycopg2 = None

try:
    import MySQLdb as mysql
except ImportError:
    try:
        import pymysql as mysql
    except ImportError:
        mysql = None

sqlite_db = SqliteDatabase(':memory:')

TEST_VERBOSITY = int(os.environ.get('PEEWEE_TEST_VERBOSITY') or 1)

class Tag(Model):
    tag = CharField()

class Person(Model):
    first_name = CharField()
    last_name = CharField()
    dob = DateField(null=True)

MODELS = [
    Person,
    Tag,
]

class BaseMigrationTestCase(object):
    database = None
    migrator_class = None

    # Each database behaves slightly differently.
    _exception_add_not_null = True

    _person_data = [
        ('Charlie', 'Leifer', None),
        ('Huey', 'Kitty', datetime.date(2011, 5, 1)),
        ('Mickey', 'Dog', datetime.date(2008, 6, 1)),
    ]

    def setUp(self):
        for model_class in MODELS:
            model_class._meta.database = self.database
            model_class.drop_table(True)
            model_class.create_table()

        self.migrator = self.migrator_class(self.database)

    def test_add_column(self):
        # Create some fields with a variety of NULL / default values.
        df = DateTimeField(null=True)
        df_def = DateTimeField(default=datetime.datetime(2012, 1, 1))
        cf = CharField(max_length=200, default='')
        bf = BooleanField(default=True)
        ff = FloatField(default=0)

        # Create two rows in the Tag table to test the handling of adding
        # non-null fields.
        t1 = Tag.create(tag='t1')
        t2 = Tag.create(tag='t2')

        # Convenience function for generating `add_column` migrations.
        def add_column(field_name, field_obj):
            return self.migrator.add_column('tag', field_name, field_obj)

        # Run the migration.
        migrate(
            add_column('pub_date', df),
            add_column('modified_date', df_def),
            add_column('comment', cf),
            add_column('is_public', bf),
            add_column('popularity', ff))

        # Create a new tag model to represent the fields we added.
        class NewTag(Model):
            tag = CharField()
            pub_date = df
            modified_date = df_def
            comment = cf
            is_public = bf
            popularity = ff

            class Meta:
                database = self.database
                db_table = Tag._meta.db_table

        query = (NewTag
                 .select(
                     NewTag.id,
                     NewTag.tag,
                     NewTag.pub_date,
                     NewTag.modified_date,
                     NewTag.comment,
                     NewTag.is_public,
                     NewTag.popularity)
                 .order_by(NewTag.tag.asc()))

        # Verify the resulting rows are correct.
        self.assertEqual(list(query.tuples()), [
            (t1.id, 't1', None, datetime.datetime(2012, 1, 1), '', True, 0.0),
            (t2.id, 't2', None, datetime.datetime(2012, 1, 1), '', True, 0.0),
        ])

    def _create_people(self):
        for first, last, dob in self._person_data:
            Person.create(first_name=first, last_name=last, dob=dob)

    def get_column_names(self, tbl):
        cursor = self.database.execute_sql('select * from %s limit 1' % tbl)
        return set([col[0] for col in cursor.description])

    def test_drop_column(self):
        self._create_people()
        migrate(
            self.migrator.drop_column('person', 'last_name'),
            self.migrator.drop_column('person', 'dob'))

        column_names = self.get_column_names('person')
        self.assertEqual(column_names, set(['id', 'first_name']))

    def test_rename_column(self):
        self._create_people()
        migrate(
            self.migrator.rename_column('person', 'first_name', 'first'),
            self.migrator.rename_column('person', 'last_name', 'last'))

        column_names = self.get_column_names('person')
        self.assertEqual(column_names, set(['id', 'first', 'last', 'dob']))

        class NewPerson(Model):
            first = CharField()
            last = CharField()
            dob = DateField()

            class Meta:
                database = self.database
                db_table = Person._meta.db_table

        query = (NewPerson
                 .select(
                     NewPerson.first,
                     NewPerson.last,
                     NewPerson.dob)
                 .order_by(NewPerson.first))
        self.assertEqual(list(query.tuples()), self._person_data)

    def test_add_not_null(self):
        self._create_people()

        def addNotNull():
            with self.database.transaction():
                migrate(self.migrator.add_not_null('person', 'dob'))

        # We cannot make the `dob` field not null because there is currently
        # a null value there.
        if self._exception_add_not_null:
            self.assertRaises(IntegrityError, addNotNull)

        (Person
         .update(dob=datetime.date(2000, 1, 2))
         .where(Person.dob >> None)
         .execute())

        # Now we can make the column not null.
        addNotNull()

        # And attempting to insert a null value results in an integrity error.
        with self.database.transaction():
            self.assertRaises(
                IntegrityError,
                Person.create,
                first_name='Kirby',
                last_name='Snazebrauer',
                dob=None)

    def test_drop_not_null(self):
        self._create_people()
        migrate(
            self.migrator.drop_not_null('person', 'first_name'),
            self.migrator.drop_not_null('person', 'last_name'))

        p = Person.create(first_name=None, last_name=None)
        query = (Person
                 .select()
                 .where(
                     (Person.first_name >> None) &
                     (Person.last_name >> None)))
        self.assertEqual(query.count(), 1)

    def test_rename_table(self):
        t1 = Tag.create(tag='t1')
        t2 = Tag.create(tag='t2')

        # Move the tag data into a new model/table.
        class Tag_asdf(Tag):
            pass
        self.assertEqual(Tag_asdf._meta.db_table, 'tag_asdf')

        # Drop the new table just to be safe.
        Tag_asdf.drop_table(True)

        # Rename the tag table.
        migrate(self.migrator.rename_table('tag', 'tag_asdf'))

        # Verify the data was moved.
        query = (Tag_asdf
                 .select()
                 .order_by(Tag_asdf.tag))
        self.assertEqual([t.tag for t in query], ['t1', 't2'])

        # Verify the old table is gone.
        with self.database.transaction():
            self.assertRaises(
                DatabaseError,
                Tag.create,
                tag='t3')

    def test_add_index(self):
        # Create a unique index on first and last names.
        columns = ('first_name', 'last_name')
        migrate(self.migrator.add_index('person', columns, True))

        Person.create(first_name='first', last_name='last')
        with self.database.transaction():
            self.assertRaises(
                IntegrityError,
                Person.create,
                first_name='first',
                last_name='last')

    def test_drop_index(self):
        # Create a unique index.
        self.test_add_index()

        # Now drop the unique index.
        migrate(
            self.migrator.drop_index('person', 'person_first_name_last_name'))

        Person.create(first_name='first', last_name='last')
        query = (Person
                 .select()
                 .where(
                     (Person.first_name == 'first') &
                     (Person.last_name == 'last')))
        self.assertEqual(query.count(), 2)

    def test_add_and_remove(self):
        operations = []
        field = CharField(default='foo')
        for i in range(10):
            operations.append(self.migrator.add_column('tag', 'foo', field))
            operations.append(self.migrator.drop_column('tag', 'foo'))

        migrate(*operations)
        col_names = self.get_column_names('tag')
        self.assertEqual(col_names, set(['id', 'tag']))

    def test_multiple_operations(self):
        self.database.execute_sql('drop table if exists person_baze;')
        self.database.execute_sql('drop table if exists person_nugg;')
        self._create_people()

        field_n = CharField(null=True)
        field_d = CharField(default='test')
        operations = [
            self.migrator.add_column('person', 'field_null', field_n),
            self.migrator.drop_column('person', 'first_name'),
            self.migrator.add_column('person', 'field_default', field_d),
            self.migrator.rename_table('person', 'person_baze'),
            self.migrator.rename_table('person_baze', 'person_nugg'),
            self.migrator.rename_column('person_nugg', 'last_name', 'last'),
            self.migrator.add_index('person_nugg', ('last',), True),
        ]
        migrate(*operations)

        class PersonNugg(Model):
            field_null = field_n
            field_default = field_d
            last = CharField()
            dob = DateField(null=True)

            class Meta:
                database = self.database
                db_table = 'person_nugg'

        people = (PersonNugg
                  .select(
                      PersonNugg.field_null,
                      PersonNugg.field_default,
                      PersonNugg.last,
                      PersonNugg.dob)
                  .order_by(PersonNugg.last)
                  .tuples())
        expected = [
            (None, 'test', 'Dog', datetime.date(2008, 6, 1)),
            (None, 'test', 'Kitty', datetime.date(2011, 5, 1)),
            (None, 'test', 'Leifer', None),
        ]
        self.assertEqual(list(people), expected)

        with self.database.transaction():
            self.assertRaises(
                IntegrityError,
                PersonNugg.create,
                last='Leifer',
                field_default='bazer')

    def test_add_foreign_key(self):
        if hasattr(Person, 'newtag_set'):
            delattr(Person, 'newtag_set')
            del Person._meta.reverse_rel['newtag_set']

        field = ForeignKeyField(Person, null=True, to_field=Person.id)
        migrate(self.migrator.add_column('tag', 'person_id', field))

        class NewTag(Tag):
            person = field

            class Meta:
                db_table = 'tag'

        p = Person.create(first_name='First', last_name='Last')
        t1 = NewTag.create(tag='t1', person=p)
        t2 = NewTag.create(tag='t2')

        t1_db = NewTag.get(NewTag.tag == 't1')
        self.assertEqual(t1_db.person, p)

        t2_db = NewTag.get(NewTag.tag == 't2')
        self.assertEqual(t2_db.person, None)


class SqliteMigrationTestCase(BaseMigrationTestCase, unittest.TestCase):
    database = sqlite_db
    migrator_class = SqliteMigrator


if psycopg2:
    pg_db = PostgresqlDatabase('peewee_test')

    class PostgresqlMigrationTestCase(BaseMigrationTestCase, unittest.TestCase):
        database = pg_db
        migrator_class = PostgresqlMigrator
elif TEST_VERBOSITY > 0:
    print_('Skipping postgres migrations, driver not found.')

if mysql:
    mysql_db = MySQLDatabase('peewee_test')

    class MySQLMigrationTestCase(BaseMigrationTestCase, unittest.TestCase):
        database = mysql_db
        migrator_class = MySQLMigrator

        # MySQL does not raise an exception when adding a not null constraint
        # to a column that contains NULL values.
        _exception_add_not_null = False
elif TEST_VERBOSITY > 0:
    print_('Skipping mysql migrations, driver not found.')

########NEW FILE########
__FILENAME__ = tests_pool
import heapq
import psycopg2  # Trigger import error if not installed.
import threading
import time
from unittest import TestCase

from peewee import *
from playhouse.pool import *

class FakeDatabase(SqliteDatabase):
    def __init__(self, *args, **kwargs):
        self.counter = 0
        self.closed_counter = 0
        super(FakeDatabase, self).__init__(*args, **kwargs)

    def _connect(self, *args, **kwargs):
        """
        Return increasing integers instead of actual database connections.
        """
        self.counter += 1
        return self.counter

    def _close(self, conn):
        self.closed_counter += 1

class TestDB(PooledDatabase, FakeDatabase):
    def __init__(self, *args, **kwargs):
        super(TestDB, self).__init__(*args, **kwargs)
        self.conn_key = lambda conn: conn

pooled_db = PooledPostgresqlDatabase('peewee_test')
normal_db = PostgresqlDatabase('peewee_test')

class Number(Model):
    value = IntegerField()

    class Meta:
        database = pooled_db

class TestPooledDatabase(TestCase):
    def setUp(self):
        self.db = TestDB('testing')

    def test_connection_pool(self):
        # Ensure that a connection is created and accessible.
        self.assertEqual(self.db.get_conn(), 1)
        self.assertEqual(self.db.get_conn(), 1)

        # Ensure that closing and reopening will return the same connection.
        self.db.close()
        self.db.connect()
        self.assertEqual(self.db.get_conn(), 1)

    def test_concurrent_connections(self):
        db = TestDB('testing', threadlocals=True)
        signal = threading.Event()

        def open_conn():
            db.connect()
            signal.wait()
            db.close()

        # Simulate 5 concurrent connections.
        threads = [threading.Thread(target=open_conn) for i in range(5)]
        for thread in threads:
            thread.start()

        # Wait for all connections to be opened.
        while db.counter < 5:
            time.sleep(.01)

        # Signal threads to close connections and join threads.
        signal.set()
        [t.join() for t in threads]

        self.assertEqual(db.counter, 5)
        self.assertEqual(db._in_use, {})

    def test_max_conns(self):
        for i in range(self.db.max_connections):
            self.db.connect()
            self.assertEqual(self.db.get_conn(), i + 1)
        self.assertRaises(ValueError, self.db.connect)

    def test_stale_timeout(self):
        # Create a test database with a very short stale timeout.
        db = TestDB('testing', stale_timeout=.01)
        self.assertEqual(db.get_conn(), 1)

        # Return the connection to the pool.
        db.close()

        # Sleep long enough for the connection to be considered stale.
        time.sleep(.01)

        # A new connection will be returned.
        self.assertEqual(db.get_conn(), 2)

    def test_manual_close(self):
        conn = self.db.get_conn()
        self.assertEqual(conn, 1)

        self.db.manual_close()
        conn = self.db.get_conn()
        self.assertEqual(conn, 2)

        self.db.close()
        conn = self.db.get_conn()
        self.assertEqual(conn, 2)

    def test_stale_timeout_cascade(self):
        now = time.time()
        db = TestDB('testing', stale_timeout=10)
        conns = [
            (now - 20, 1),
            (now - 15, 2),
            (now - 5, 3),
            (now, 4),
        ]
        for ts_conn in conns:
            heapq.heappush(db._connections, ts_conn)

        self.assertEqual(db.get_conn(), 3)
        self.assertEqual(db._in_use, {3: now - 5})
        self.assertEqual(db._connections, [(now, 4)])

    def test_connect_cascade(self):
        now = time.time()
        db = TestDB('testing', stale_timeout=10)

        conns = [
            (now - 15, 1),  # Skipped due to being stale.
            (now - 5, 2),  # In the 'closed' set.
            (now - 3, 3),
            (now, 4),  # In the 'closed' set.
        ]
        db._closed.add(2)
        db._closed.add(4)
        db.counter = 4  # The next connection we create will have id=5.
        for ts_conn in conns:
            heapq.heappush(db._connections, ts_conn)

        # Conn 3 is not stale or closed, so we will get it.
        self.assertEqual(db.get_conn(), 3)
        self.assertEqual(db._in_use, {3: now - 3})
        self.assertEqual(db._connections, [(now, 4)])

        # Since conn 4 is closed, we will open a new conn.
        db.connect()
        self.assertEqual(db.get_conn(), 5)
        self.assertEqual(sorted(db._in_use.keys()), [3, 5])
        self.assertEqual(db._connections, [])


class TestConnectionPool(TestCase):
    def setUp(self):
        # Use an un-pooled database to drop/create the table.
        if Number._meta.db_table in normal_db.get_tables():
            normal_db.drop_table(Number)
        normal_db.create_table(Number)

    def test_reuse_connection(self):
        for i in range(5):
            Number.create(value=i)
        conn_id = id(pooled_db.get_conn())
        pooled_db.close()

        for i in range(5, 10):
            Number.create(value=i)
        self.assertEqual(id(pooled_db.get_conn()), conn_id)

        self.assertEqual(
            [x.value for x in Number.select().order_by(Number.id)],
            list(range(10)))

########NEW FILE########
__FILENAME__ = tests_postgres
#coding:utf-8
import datetime
import json
import os
import unittest
import uuid

import psycopg2

from peewee import print_
from playhouse.postgres_ext import *


TEST_VERBOSITY = int(os.environ.get('PEEWEE_TEST_VERBOSITY') or 1)
test_db = PostgresqlExtDatabase('peewee_test', user='postgres')
test_ss_db = PostgresqlExtDatabase(
    'peewee_test',
    server_side_cursors=True,
    user='postgres')


class BaseModel(Model):
    class Meta:
        database = test_db

class Testing(BaseModel):
    name = CharField()
    data = HStoreField()

    class Meta:
        order_by = ('name',)

try:
    class TestingJson(BaseModel):
        data = JSONField()
except:
    TestingJson = None

class TestingID(BaseModel):
    uniq = UUIDField()

class TZModel(BaseModel):
    dt = DateTimeTZField()

class ArrayModel(BaseModel):
    tags = ArrayField(CharField)
    ints = ArrayField(IntegerField, dimensions=2)

class SSCursorModel(Model):
    data = CharField()

    class Meta:
        database = test_ss_db

class NormalModel(BaseModel):
    data = CharField()

class PostgresExtTestCase(unittest.TestCase):
    def setUp(self):
        Testing.drop_table(True)
        Testing.create_table()
        TestingID.drop_table(True)
        TestingID.create_table()
        ArrayModel.drop_table(True)
        ArrayModel.create_table(True)
        self.t1 = None
        self.t2 = None

    def test_uuid(self):
        uuid_str = 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'
        uuid_obj = uuid.UUID(uuid_str)

        t1 = TestingID.create(uniq=uuid_obj)
        t1_db = TestingID.get(TestingID.uniq == uuid_str)
        self.assertEqual(t1, t1_db)

        t2 = TestingID.get(TestingID.uniq == uuid_obj)
        self.assertEqual(t1, t2)

    def test_tz_field(self):
        TZModel.drop_table(True)
        TZModel.create_table()

        test_db.execute_sql('set time zone "us/central";')

        dt = datetime.datetime.now()
        tz = TZModel.create(dt=dt)
        self.assertTrue(tz.dt.tzinfo is None)

        tz = TZModel.get(TZModel.id == tz.id)
        self.assertFalse(tz.dt.tzinfo is None)

    def create(self):
        self.t1 = Testing.create(name='t1', data={'k1': 'v1', 'k2': 'v2'})
        self.t2 = Testing.create(name='t2', data={'k2': 'v2', 'k3': 'v3'})

    def test_storage(self):
        self.create()
        self.assertEqual(Testing.get(name='t1').data, {'k1': 'v1', 'k2': 'v2'})
        self.assertEqual(Testing.get(name='t2').data, {'k2': 'v2', 'k3': 'v3'})

        self.t1.data = {'k4': 'v4'}
        self.t1.save()
        self.assertEqual(Testing.get(name='t1').data, {'k4': 'v4'})

        t = Testing.create(name='t3', data={})
        self.assertEqual(Testing.get(name='t3').data, {})

    def test_selecting(self):
        self.create()

        sq = Testing.select(Testing.name, Testing.data.keys().alias('keys'))
        self.assertEqual([(x.name, sorted(x.keys)) for x in sq], [
            ('t1', ['k1', 'k2']), ('t2', ['k2', 'k3'])
        ])

        sq = Testing.select(Testing.name, Testing.data.values().alias('vals'))
        self.assertEqual([(x.name, sorted(x.vals)) for x in sq], [
            ('t1', ['v1', 'v2']), ('t2', ['v2', 'v3'])
        ])

        sq = Testing.select(Testing.name, Testing.data.items().alias('mtx'))
        self.assertEqual([(x.name, sorted(x.mtx)) for x in sq], [
            ('t1', [['k1', 'v1'], ['k2', 'v2']]),
            ('t2', [['k2', 'v2'], ['k3', 'v3']]),
        ])

        sq = Testing.select(Testing.name, Testing.data.slice('k2', 'k3').alias('kz'))
        self.assertEqual([(x.name, x.kz) for x in sq], [
            ('t1', {'k2': 'v2'}),
            ('t2', {'k2': 'v2', 'k3': 'v3'}),
        ])

        sq = Testing.select(Testing.name, Testing.data.slice('k4').alias('kz'))
        self.assertEqual([(x.name, x.kz) for x in sq], [
            ('t1', {}),
            ('t2', {}),
        ])

        sq = Testing.select(Testing.name, Testing.data.exists('k3').alias('ke'))
        self.assertEqual([(x.name, x.ke) for x in sq], [
            ('t1', False),
            ('t2', True),
        ])

        sq = Testing.select(Testing.name, Testing.data.defined('k3').alias('ke'))
        self.assertEqual([(x.name, x.ke) for x in sq], [
            ('t1', False),
            ('t2', True),
        ])

        sq = Testing.select(Testing.name, Testing.data['k1'].alias('k1'))
        self.assertEqual([(x.name, x.k1) for x in sq], [
            ('t1', 'v1'),
            ('t2', None),
        ])

        sq = Testing.select(Testing.name).where(Testing.data['k1'] == 'v1')
        self.assertEqual([x.name for x in sq], ['t1'])

    def test_filtering(self):
        self.create()

        sq = Testing.select().where(Testing.data == {'k1': 'v1', 'k2': 'v2'})
        self.assertEqual([x.name for x in sq], ['t1'])

        sq = Testing.select().where(Testing.data == {'k2': 'v2'})
        self.assertEqual([x.name for x in sq], [])

        # test single key
        sq = Testing.select().where(Testing.data.contains('k3'))
        self.assertEqual([x.name for x in sq], ['t2'])

        # test list of keys
        sq = Testing.select().where(Testing.data.contains(['k2', 'k3']))
        self.assertEqual([x.name for x in sq], ['t2'])

        sq = Testing.select().where(Testing.data.contains(['k2']))
        self.assertEqual([x.name for x in sq], ['t1', 't2'])

        # test dict
        sq = Testing.select().where(Testing.data.contains({'k2': 'v2', 'k3': 'v3'}))
        self.assertEqual([x.name for x in sq], ['t2'])

        sq = Testing.select().where(Testing.data.contains({'k2': 'v2'}))
        self.assertEqual([x.name for x in sq], ['t1', 't2'])

        sq = Testing.select().where(Testing.data.contains({'k2': 'v3'}))
        self.assertEqual([x.name for x in sq], [])

    def test_filter_functions(self):
        self.create()

        sq = Testing.select().where(Testing.data.exists('k2') == True)
        self.assertEqual([x.name for x in sq], ['t1', 't2'])

        sq = Testing.select().where(Testing.data.exists('k3') == True)
        self.assertEqual([x.name for x in sq], ['t2'])

        sq = Testing.select().where(Testing.data.defined('k2') == True)
        self.assertEqual([x.name for x in sq], ['t1', 't2'])

        sq = Testing.select().where(Testing.data.defined('k3') == True)
        self.assertEqual([x.name for x in sq], ['t2'])

    def test_update_functions(self):
        self.create()

        rc = Testing.update(data=Testing.data.update(k4='v4')).where(
            Testing.name == 't1'
        ).execute()
        self.assertEqual(rc, 1)
        self.assertEqual(Testing.get(name='t1').data, {'k1': 'v1', 'k2': 'v2', 'k4': 'v4'})

        rc = Testing.update(data=Testing.data.update(k5='v5', k6='v6')).where(
            Testing.name == 't2'
        ).execute()
        self.assertEqual(rc, 1)
        self.assertEqual(Testing.get(name='t2').data, {'k2': 'v2', 'k3': 'v3', 'k5': 'v5', 'k6': 'v6'})

        rc = Testing.update(data=Testing.data.update(k2='vxxx')).execute()
        self.assertEqual(rc, 2)
        self.assertEqual([x.data for x in Testing.select()], [
            {'k1': 'v1', 'k2': 'vxxx', 'k4': 'v4'},
            {'k2': 'vxxx', 'k3': 'v3', 'k5': 'v5', 'k6': 'v6'}
        ])

        rc = Testing.update(data=Testing.data.delete('k4')).where(
            Testing.name == 't1'
        ).execute()
        self.assertEqual(rc, 1)
        self.assertEqual(Testing.get(name='t1').data, {'k1': 'v1', 'k2': 'vxxx'})

        rc = Testing.update(data=Testing.data.delete('k5')).execute()
        self.assertEqual(rc, 2)
        self.assertEqual([x.data for x in Testing.select()], [
            {'k1': 'v1', 'k2': 'vxxx'},
            {'k2': 'vxxx', 'k3': 'v3', 'k6': 'v6'}
        ])

        rc = Testing.update(data=Testing.data.delete('k1', 'k2')).execute()
        self.assertEqual(rc, 2)
        self.assertEqual([x.data for x in Testing.select()], [
            {},
            {'k3': 'v3', 'k6': 'v6'}
        ])

    def _create_am(self):
        return ArrayModel.create(
            tags=['alpha', 'beta', 'gamma', 'delta'],
            ints=[[1, 2], [3, 4], [5, 6]])

    def test_array_storage_retrieval(self):
        am = self._create_am()
        am_db = ArrayModel.get(ArrayModel.id == am.id)
        self.assertEqual(am_db.tags, ['alpha', 'beta', 'gamma', 'delta'])
        self.assertEqual(am_db.ints, [[1, 2], [3, 4], [5, 6]])

    def test_array_search(self):
        def assertAM(where, *instances):
            query = (ArrayModel
                     .select()
                     .where(where)
                     .order_by(ArrayModel.id))
            self.assertEqual([x.id for x in query], [x.id for x in instances])

        am = self._create_am()
        am2 = ArrayModel.create(tags=['alpha', 'beta'], ints=[[1, 1]])
        am3 = ArrayModel.create(tags=['delta'], ints=[[3, 4]])
        am4 = ArrayModel.create(tags=['中文'], ints=[[3, 4]])
        am5 = ArrayModel.create(tags=['中文', '汉语'], ints=[[3, 4]])

        assertAM((Param('beta') == fn.Any(ArrayModel.tags)), am, am2)
        assertAM((Param('delta') == fn.Any(ArrayModel.tags)), am, am3)
        assertAM((Param('omega') == fn.Any(ArrayModel.tags)))

        # Check the contains operator.
        assertAM(SQL("tags @> ARRAY['beta']::varchar[]"), am, am2)

        # Use the nicer API.
        assertAM(ArrayModel.tags.contains('beta'), am, am2)
        assertAM(ArrayModel.tags.contains('omega', 'delta'))
        assertAM(ArrayModel.tags.contains('汉语'), am5)
        assertAM(ArrayModel.tags.contains('alpha', 'delta'), am)

        # Check for any.
        assertAM(ArrayModel.tags.contains_any('beta'), am, am2)
        assertAM(ArrayModel.tags.contains_any('中文'), am4, am5)
        assertAM(ArrayModel.tags.contains_any('omega', 'delta'), am, am3)
        assertAM(ArrayModel.tags.contains_any('alpha', 'delta'), am, am2, am3)

    def test_array_index_slice(self):
        self._create_am()
        res = (ArrayModel
               .select(ArrayModel.tags[1].alias('arrtags'))
               .dicts()
               .get())
        self.assertEqual(res['arrtags'], 'beta')

        res = (ArrayModel
               .select(ArrayModel.tags[2:4].alias('foo'))
               .dicts()
               .get())
        self.assertEqual(res['foo'], ['gamma', 'delta'])

        res = (ArrayModel
               .select(ArrayModel.ints[1][1].alias('ints'))
               .dicts()
               .get())
        self.assertEqual(res['ints'], 4)

        res = (ArrayModel
               .select(ArrayModel.ints[1:2][0].alias('ints'))
               .dicts()
               .get())
        self.assertEqual(res['ints'], [[3], [5]])


class SSCursorTestCase(unittest.TestCase):
    counter = 0

    def setUp(self):
        self.close_conn()  # Close open connection.
        SSCursorModel.drop_table(True)
        NormalModel.drop_table(True)
        SSCursorModel.create_table()
        NormalModel.create_table()
        self.counter = 0
        for i in range(3):
            self.create()

    def create(self):
        self.counter += 1
        SSCursorModel.create(data=self.counter)
        NormalModel.create(data=self.counter)

    def close_conn(self):
        if not test_ss_db.is_closed():
            test_ss_db.close()

    def assertList(self, iterable):
        self.assertEqual(
            [x.data for x in iterable],
            [str(i) for i in range(1, self.counter + 1)])

    def test_model_interaction(self):
        query = SSCursorModel.select().order_by(SSCursorModel.data)
        self.assertList(query)

        query2 = query.clone()
        qr = query2.execute()
        self.assertList(qr)

        # The cursor is named and is still "alive" because we can still try
        # to fetch results.
        self.assertTrue(qr.cursor.name is not None)
        self.assertEqual(qr.cursor.fetchone(), None)

        # Execute the query in a transaction.
        with test_ss_db.transaction():
            query3 = query.clone()
            qr2 = query3.execute()

            # Different named cursor
            self.assertFalse(qr2.cursor.name == qr.cursor.name)
            self.assertList(qr2)

        # After the transaction we cannot fetch a result because the cursor
        # is dead.
        self.assertRaises(psycopg2.ProgrammingError, qr2.cursor.fetchone)

        # Try using the helper.
        query4 = query.clone()
        self.assertList(ServerSide(query4))

        # Named cursor is dead.
        self.assertRaises(
            psycopg2.ProgrammingError, query4._qr.cursor.fetchone)

    def test_serverside_normal_model(self):
        query = NormalModel.select().order_by(NormalModel.data)
        self.assertList(query)

        # We can ask for more results from a normal query.
        self.assertEqual(query._qr.cursor.fetchone(), None)

        clone = query.clone()
        self.assertList(ServerSide(clone))

        # Named cursor is dead.
        self.assertRaises(psycopg2.ProgrammingError, clone._qr.cursor.fetchone)

        # Ensure where clause is preserved.
        query = query.where(NormalModel.data == '2')
        data = [x.data for x in ServerSide(query)]
        self.assertEqual(data, ['2'])

    def test_ss_cursor(self):
        tbl = SSCursorModel._meta.db_table
        name = str(uuid.uuid1())

        # Get a named cursor and execute a select query.
        cursor = test_ss_db.get_cursor(name=name)
        cursor.execute('select data from %s order by id' % tbl)

        # Ensure the cursor attributes are as we expect.
        self.assertEqual(cursor.description, None)
        self.assertEqual(cursor.name, name)
        self.assertFalse(cursor.withhold)  # Close cursor after commit.

        # Cursor works and populates description after fetching one row.
        self.assertEqual(cursor.fetchone(), ('1',))
        self.assertEqual(cursor.description[0].name, 'data')

        # Explicitly close the cursor.
        test_ss_db.commit()
        self.assertRaises(psycopg2.ProgrammingError, cursor.fetchone)

        # This would not work is the named cursor was still holding a ref to
        # the table.
        test_ss_db.execute_sql('truncate table %s;' % tbl)
        test_ss_db.commit()

def json_ok():
    if TestingJson is None:
        return False
    conn = test_db.get_conn()
    return conn.server_version >= 90300

if json_ok():
    from psycopg2.extras import Json

    class TestJsonField(unittest.TestCase):
        def setUp(self):
            TestingJson.drop_table(True)
            TestingJson.create_table()

        def test_json_field(self):
            data = {'k1': ['a1', 'a2'], 'k2': {'k3': 'v3'}}
            tj = TestingJson.create(data=data)
            tj_db = TestingJson.get(tj.pk_expr())
            self.assertEqual(tj_db.data, data)

        def test_json_field_sql(self):
            tj = TestingJson.select().where(TestingJson.data == {'foo': 'bar'})
            sql, params = tj.sql()
            self.assertEqual(sql, (
                'SELECT t1."id", t1."data" '
                'FROM "testingjson" AS t1 WHERE (t1."data" = %s)'))
            self.assertEqual(params[0].adapted, {'foo': 'bar'})

            tj = TestingJson.select().where(TestingJson.data['foo'] == 'bar')
            sql, params = tj.sql()
            self.assertEqual(sql, (
                'SELECT t1."id", t1."data" '
                'FROM "testingjson" AS t1 WHERE (t1."data"->>%s = %s)'))
            self.assertEqual(params, ['foo', 'bar'])

        def assertItems(self, where, *items):
            query = TestingJson.select().where(where).order_by(TestingJson.id)
            self.assertEqual(
                [item.id for item in query],
                [item.id for item in items])

        def test_lookup(self):
            t1 = TestingJson.create(data={'k1': 'v1', 'k2': {'k3': 'v3'}})
            t2 = TestingJson.create(data={'k1': 'x1', 'k2': {'k3': 'x3'}})
            t3 = TestingJson.create(data={'k1': 'v1', 'j2': {'j3': 'v3'}})
            self.assertItems((TestingJson.data['k2']['k3'] == 'v3'), t1)
            self.assertItems((TestingJson.data['k1'] == 'v1'), t1, t3)

            # Valid key, no matching value.
            self.assertItems((TestingJson.data['k2'] == 'v1'))

            # Non-existent key.
            self.assertItems((TestingJson.data['not-here'] == 'v1'))

            # Non-existent nested key.
            self.assertItems((TestingJson.data['not-here']['xxx'] == 'v1'))

            self.assertItems((TestingJson.data['k2']['xxx'] == 'v1'))

elif TEST_VERBOSITY > 0:
    print_('Skipping postgres "Json" tests, unsupported version.')

########NEW FILE########
__FILENAME__ = tests_pwiz
import os
import re
import unittest

from peewee import *
from peewee import create_model_tables
from peewee import drop_model_tables
from peewee import mysql
from pwiz import *
from peewee import print_


TEST_VERBOSITY = int(os.environ.get('PEEWEE_TEST_VERBOSITY') or 1)

# test databases
sqlite_db = SqliteDatabase('tmp.db')
if mysql:
    mysql_db = MySQLDatabase('peewee_test')
else:
    mysql_db = None
try:
    import psycopg2
    postgres_db = PostgresqlDatabase('peewee_test')
except ImportError:
    postgres_db = None

class BaseModel(Model):
    class Meta:
        database = sqlite_db

class ColTypes(BaseModel):
    f1 = BigIntegerField()
    f2 = BlobField()
    f3 = BooleanField()
    f4 = CharField(max_length=50)
    f5 = DateField()
    f6 = DateTimeField()
    f7 = DecimalField()
    f8 = DoubleField()
    f9 = FloatField()
    f10 = IntegerField()
    f11 = PrimaryKeyField()
    f12 = TextField()
    f13 = TimeField()

class Nullable(BaseModel):
    nullable_cf = CharField(null=True)
    nullable_if = IntegerField(null=True)

class RelModel(BaseModel):
    col_types = ForeignKeyField(ColTypes, related_name='foo')
    col_types_nullable = ForeignKeyField(ColTypes, null=True)

class FKPK(BaseModel):
    col_types = ForeignKeyField(ColTypes, primary_key=True)

class Underscores(BaseModel):
    _id = PrimaryKeyField()
    _name = CharField()

class Category(BaseModel):
    name = CharField(max_length=10)
    parent = ForeignKeyField('self', null=True)


DATABASES = (
    ('sqlite', sqlite_db),
    ('mysql', mysql_db),
    ('postgres', postgres_db))

MODELS = (
    ColTypes,
    Nullable,
    RelModel,
    FKPK,
    Underscores,
    Category)

class TestPwiz(unittest.TestCase):
    def test_sqlite_fk_re(self):
        user_id_tests = [
            'FOREIGN KEY("user_id") REFERENCES "users"("id")',
            'FOREIGN KEY(user_id) REFERENCES users(id)',
            'FOREIGN KEY  ([user_id])  REFERENCES  [users]  ([id])',
            '"user_id" NOT NULL REFERENCES "users" ("id")',
            'user_id not null references users (id)',
        ]
        fk_pk_tests = [
            ('"col_types_id" INTEGER NOT NULL PRIMARY KEY REFERENCES '
             '"coltypes" ("f11")'),
            'FOREIGN KEY ("col_types_id") REFERENCES "coltypes" ("f11")',
        ]
        regex = SqliteMetadata.re_foreign_key

        for test in user_id_tests:
            match = re.search(regex, test, re.I)
            self.assertEqual(match.groups(), (
                'user_id', 'users', 'id',
            ))

        for test in fk_pk_tests:
            match = re.search(regex, test, re.I)
            self.assertEqual(match.groups(), (
                'col_types_id', 'coltypes', 'f11',
            ))

    def get_introspector(self):
        return Introspector(SqliteMetadata(sqlite_db))

    def test_make_column_name(self):
        introspector = self.get_introspector()
        tests = (
            ('Column', 'column'),
            ('Foo_iD', 'foo'),
            ('foo_id', 'foo'),
            ('foo_id_id', 'foo_id'),
            ('foo', 'foo'),
            ('_id', '_id'),
            ('a123', 'a123'),
            ('and', 'and_'),
            ('Class', 'class_'),
            ('Class_ID', 'class_'),
        )
        for col_name, expected in tests:
            self.assertEqual(
                introspector.make_column_name(col_name), expected)

    def test_make_model_name(self):
        introspector = self.get_introspector()
        tests = (
            ('Table', 'Table'),
            ('table', 'Table'),
            ('table_baz', 'TableBaz'),
            ('foo__bar__baz2', 'FooBarBaz2'),
            ('foo12_3', 'Foo123'),
        )
        for table_name, expected in tests:
            self.assertEqual(
                introspector.make_model_name(table_name), expected)

    def create_tables(self, db):
        for model in MODELS:
            model._meta.database = db

        drop_model_tables(MODELS, fail_silently=True)
        create_model_tables(MODELS)

    def generative_test(fn):
        def inner(self):
            for database_type, database in DATABASES:
                if database:
                    introspector = make_introspector(
                        database_type,
                        database.database)
                    self.create_tables(database)
                    fn(self, introspector)
                elif TEST_VERBOSITY > 0:
                    print_('Skipping %s, driver not found' % database_type)
        return inner

    @generative_test
    def test_col_types(self, introspector):
        columns, foreign_keys, model_names = introspector.introspect()
        expected = (
            ('coltypes', (
                ('f1', BigIntegerField, False),
                ('f2', (BlobField, TextField), False),
                ('f3', (BooleanField, IntegerField), False),
                ('f4', CharField, False),
                ('f5', DateField, False),
                ('f6', DateTimeField, False),
                ('f7', DecimalField, False),
                ('f8', (DoubleField, FloatField), False),
                ('f9', FloatField, False),
                ('f10', IntegerField, False),
                ('f11', PrimaryKeyField, False),
                ('f12', TextField, False),
                ('f13', TimeField, False))),
            ('relmodel', (
                ('col_types_id', ForeignKeyField, False),
                ('col_types_nullable_id', ForeignKeyField, True))),
            ('nullable', (
                ('nullable_cf', CharField, True),
                ('nullable_if', IntegerField, True))),
            ('fkpk', (
                ('col_types_id', ForeignKeyField, False),)),
            ('underscores', (
                ('_id', PrimaryKeyField, False),
                ('_name', CharField, False))),
            ('category', (
                ('name', CharField, False),
                ('parent_id', ForeignKeyField, True))),
        )

        for table_name, expected_columns in expected:
            introspected_columns = columns[table_name]

            for field_name, field_class, is_null in expected_columns:
                if not isinstance(field_class, (list, tuple)):
                    field_class = (field_class,)
                column = introspected_columns[field_name]
                self.assertTrue(column.field_class in field_class)
                self.assertEqual(column.nullable, is_null)

    @generative_test
    def test_foreign_keys(self, introspector):
        columns, foreign_keys, model_names = introspector.introspect()
        self.assertEqual(foreign_keys['coltypes'], [])

        rel_model = foreign_keys['relmodel']
        self.assertEqual(len(rel_model), 2)

        fkpk = foreign_keys['fkpk']
        self.assertEqual(len(fkpk), 1)

        fkpk_fk = fkpk[0]
        self.assertEqual(fkpk_fk.table, 'fkpk')
        self.assertEqual(fkpk_fk.column, 'col_types_id')
        self.assertEqual(fkpk_fk.dest_table, 'coltypes')
        self.assertEqual(fkpk_fk.dest_column, 'f11')

        category = foreign_keys['category']
        self.assertEqual(len(category), 1)

        category_fk = category[0]
        self.assertEqual(category_fk.table, 'category')
        self.assertEqual(category_fk.column, 'parent_id')
        self.assertEqual(category_fk.dest_table, 'category')
        self.assertEqual(category_fk.dest_column, 'id')

    @generative_test
    def test_table_names(self, introspector):
        columns, foreign_keys, model_names = introspector.introspect()
        names = (
            ('coltypes', 'Coltypes'),
            ('nullable', 'Nullable'),
            ('relmodel', 'Relmodel'),
            ('fkpk', 'Fkpk'))
        for k, v in names:
            self.assertEqual(model_names[k], v)

    @generative_test
    def test_column_meta(self, introspector):
        columns, foreign_keys, model_names = introspector.introspect()
        rel_model = columns['relmodel']

        col_types_id = rel_model['col_types_id']
        self.assertEqual(col_types_id.get_field_parameters(), {
            'db_column': "'col_types_id'",
            'rel_model': 'Coltypes',
        })

        col_types_nullable_id = rel_model['col_types_nullable_id']
        self.assertEqual(col_types_nullable_id.get_field_parameters(), {
            'db_column': "'col_types_nullable_id'",
            'null': True,
            'rel_model': 'Coltypes',
        })

        fkpk = columns['fkpk']
        self.assertEqual(fkpk['col_types_id'].get_field_parameters(), {
            'db_column': "'col_types_id'",
            'rel_model': 'Coltypes',
            'primary_key': True})

    @generative_test
    def test_get_field(self, introspector):
        columns, foreign_keys, model_names = introspector.introspect()
        expected = (
            ('coltypes', (
                ('f1', 'f1 = BigIntegerField()'),
                #('f2', 'f2 = BlobField()'),
                ('f4', 'f4 = CharField(max_length=50)'),
                ('f5', 'f5 = DateField()'),
                ('f6', 'f6 = DateTimeField()'),
                ('f7', 'f7 = DecimalField()'),
                ('f10', 'f10 = IntegerField()'),
                ('f11', 'f11 = PrimaryKeyField()'),
                ('f12', 'f12 = TextField()'),
                ('f13', 'f13 = TimeField()'),
            )),
            ('nullable', (
                ('nullable_cf', 'nullable_cf = '
                 'CharField(max_length=255, null=True)'),
                ('nullable_if', 'nullable_if = IntegerField(null=True)'),
            )),
            ('fkpk', (
                ('col_types_id', 'col_types = ForeignKeyField('
                 'db_column=\'col_types_id\', primary_key=True, '
                 'rel_model=Coltypes)'),
            )),
            ('relmodel', (
                ('col_types_id', 'col_types = ForeignKeyField('
                 'db_column=\'col_types_id\', rel_model=Coltypes)'),
                ('col_types_nullable_id', 'col_types_nullable = '
                 'ForeignKeyField(db_column=\'col_types_nullable_id\', '
                 'null=True, rel_model=Coltypes)'),
            )),
            ('underscores', (
                ('_id', '_id = PrimaryKeyField()'),
                ('_name', '_name = CharField(max_length=255)'),
            )),
            ('category', (
                ('name', 'name = CharField(max_length=10)'),
                ('parent_id', 'parent = ForeignKeyField('
                 'db_column=\'parent_id\', null=True, rel_model=\'self\')'),
            )),
        )

        for table, field_data in expected:
            for field_name, field_str in field_data:
                self.assertEqual(
                    columns[table][field_name].get_field(),
                    field_str)

########NEW FILE########
__FILENAME__ = tests_read_slave
import unittest

from peewee import *
from playhouse.read_slave import ReadSlaveModel


queries = []

def reset():
    global queries
    queries = []

class QueryLogDatabase(SqliteDatabase):
    name = ''

    def execute_sql(self, query, *args, **kwargs):
        queries.append((self.name, query))
        return super(QueryLogDatabase, self).execute_sql(
            query, *args, **kwargs)

class Master(QueryLogDatabase):
    name = 'master'

class Slave1(QueryLogDatabase):
    name = 'slave1'

class Slave2(QueryLogDatabase):
    name = 'slave2'

master = Master('tmp.db')
slave1 = Slave1('tmp.db')
slave2 = Slave2('tmp.db')

class BaseModel(ReadSlaveModel):
    class Meta:
        database = master
        read_slaves = [slave1, slave2]

class User(BaseModel):
    username = CharField()

class Thing(BaseModel):
    name = CharField()

    class Meta:
        read_slaves = [slave2]

class TestMasterSlave(unittest.TestCase):
    def setUp(self):
        User.drop_table(True)
        User.create_table()
        Thing.drop_table(True)
        Thing.create_table()
        User.create(username='peewee')
        Thing.create(name='something')
        reset()

    def tearDown(self):
        User.drop_table(True)
        Thing.drop_table(True)

    def assertQueries(self, databases):
        self.assertEqual([q[0] for q in queries], databases)

    def test_balance_pair(self):
        for i in range(6):
            User.get()
        self.assertQueries([
            'slave1',
            'slave2',
            'slave1',
            'slave2',
            'slave1',
            'slave2'])

    def test_balance_single(self):
        for i in range(3):
            Thing.get()
        self.assertQueries(['slave2', 'slave2', 'slave2'])

    def test_query_types(self):
        u = User.create(username='charlie')
        User.select().where(User.username == 'charlie').get()
        self.assertQueries(['master', 'slave1'])

        User.get(User.username == 'charlie')
        self.assertQueries(['master', 'slave1', 'slave2'])

        u.username = 'edited'
        u.save()  # Update.
        self.assertQueries(['master', 'slave1', 'slave2', 'master'])

        u.delete_instance()
        self.assertQueries(['master', 'slave1', 'slave2', 'master', 'master'])

    def test_raw_queries(self):
        User.raw('insert into user (username) values (?)', 'charlie').execute()
        rq = list(User.raw('select * from user where username = ?', 'charlie'))
        self.assertEqual(rq[0].username, 'charlie')

        self.assertQueries(['master', 'slave1'])

########NEW FILE########
__FILENAME__ = tests_shortcuts
import unittest

from peewee import *
from playhouse.shortcuts import case


db = SqliteDatabase(':memory:')


class TestModel(Model):
    name = CharField()
    number = IntegerField()

    class Meta:
        database = db


class CaseShortcutTestCase(unittest.TestCase):
    values = (
        ('alpha', 1),
        ('beta', 2),
        ('gamma', 3))

    expected = [
        {'name': 'alpha', 'number_string': 'one'},
        {'name': 'beta', 'number_string': 'two'},
        {'name': 'gamma', 'number_string': '?'},
    ]

    def setUp(self):
        TestModel.drop_table(True)
        TestModel.create_table()

        for name, number in self.values:
            TestModel.create(name=name, number=number)

    def test_predicate(self):
        query = (TestModel
                 .select(TestModel.name, case(TestModel.number, (
                     (1, "one"),
                     (2, "two")), "?").alias('number_string'))
                 .order_by(TestModel.id))
        self.assertEqual(list(query.dicts()), self.expected)

    def test_no_predicate(self):
        query = (TestModel
                 .select(TestModel.name, case(None, (
                     (TestModel.number == 1, "one"),
                     (TestModel.number == 2, "two")), "?").alias('number_string'))
                 .order_by(TestModel.id))
        self.assertEqual(list(query.dicts()), self.expected)

########NEW FILE########
__FILENAME__ = tests_signals
import unittest

from peewee import *
from playhouse import signals


db = SqliteDatabase(':memory:')

class BaseSignalModel(signals.Model):
    class Meta:
        database = db

class ModelA(BaseSignalModel):
    a = CharField(default='')

class ModelB(BaseSignalModel):
    b = CharField(default='')

class SubclassOfModelB(ModelB):
    pass

class SignalsTestCase(unittest.TestCase):
    def setUp(self):
        ModelA.create_table(True)
        ModelB.create_table(True)
        SubclassOfModelB.create_table(True)

    def tearDown(self):
        ModelA.drop_table()
        ModelB.drop_table()
        SubclassOfModelB.drop_table()
        signals.pre_save._flush()
        signals.post_save._flush()
        signals.pre_delete._flush()
        signals.post_delete._flush()
        signals.pre_init._flush()
        signals.post_init._flush()

    def test_pre_save(self):
        state = []

        @signals.pre_save()
        def pre_save(sender, instance, created):
            state.append((sender, instance, instance.get_id(), created))
        m = ModelA()
        m.save()
        self.assertEqual(state, [(ModelA, m, None, True)])

        m.save()
        self.assertTrue(m.id is not None)
        self.assertEqual(state[-1], (ModelA, m, m.id, False))

    def test_post_save(self):
        state = []

        @signals.post_save()
        def post_save(sender, instance, created):
            state.append((sender, instance, instance.get_id(), created))
        m = ModelA()
        m.save()

        self.assertTrue(m.id is not None)
        self.assertEqual(state, [(ModelA, m, m.id, True)])

        m.save()
        self.assertEqual(state[-1], (ModelA, m, m.id, False))

    def test_pre_delete(self):
        state = []

        m = ModelA()
        m.save()

        @signals.pre_delete()
        def pre_delete(sender, instance):
            state.append((sender, instance, ModelA.select().count()))
        m.delete_instance()
        self.assertEqual(state, [(ModelA, m, 1)])

    def test_post_delete(self):
        state = []

        m = ModelA()
        m.save()

        @signals.post_delete()
        def post_delete(sender, instance):
            state.append((sender, instance, ModelA.select().count()))
        m.delete_instance()
        self.assertEqual(state, [(ModelA, m, 0)])

    def test_pre_init(self):
        state = []

        m = ModelA(a='a')
        m.save()

        @signals.pre_init()
        def pre_init(sender, instance):
            state.append((sender, instance.a))

        ModelA.get()
        self.assertEqual(state, [(ModelA, '')])

    def test_post_init(self):
        state = []

        m = ModelA(a='a')
        m.save()

        @signals.post_init()
        def post_init(sender, instance):
            state.append((sender, instance.a))

        ModelA.get()
        self.assertEqual(state, [(ModelA, 'a')])

    def test_sender(self):
        state = []

        @signals.post_save(sender=ModelA)
        def post_save(sender, instance, created):
            state.append(instance)

        m = ModelA.create()
        self.assertEqual(state, [m])

        m2 = ModelB.create()
        self.assertEqual(state, [m])

    def test_connect_disconnect(self):
        state = []

        @signals.post_save(sender=ModelA)
        def post_save(sender, instance, created):
            state.append(instance)

        m = ModelA.create()
        self.assertEqual(state, [m])

        signals.post_save.disconnect(post_save)
        m2 = ModelA.create()
        self.assertEqual(state, [m])

    def test_subclass_instance_receive_signals(self):
        state = []

        @signals.post_save(sender=ModelB)
        def post_save(sender, instance, created):
            state.append(instance)

        m = SubclassOfModelB.create()
        assert m in state

########NEW FILE########
__FILENAME__ = tests_sqlcipher_ext
import unittest

from playhouse.sqlcipher_ext import *

DB_FILE = 'test_sqlcipher.db'
PASSPHRASE = 'test1234'
db = SqlCipherDatabase(DB_FILE, passphrase=PASSPHRASE)


class BaseModel(Model):
    class Meta:
        database = db

class Thing(BaseModel):
    name = CharField()

class SqlCipherTestCase(unittest.TestCase):
    def setUp(self):
        Thing.drop_table(True)
        Thing.create_table()

    def test_good_and_bad_passphrases(self):
        things = ('t1', 't2', 't3')
        for thing in things:
            Thing.create(name=thing)

        # Try to open db with wrong passphrase
        secure = False
        bad_db = SqlCipherDatabase(DB_FILE, passphrase=PASSPHRASE + 'x')

        self.assertRaises(DatabaseError, bad_db.get_tables)

        # Assert that we can still access the data with the good passphrase.
        query = Thing.select().order_by(Thing.name)
        self.assertEqual([t.name for t in query], ['t1', 't2', 't3'])

    def test_passphrase_length(self):
        db = SqlCipherDatabase(DB_FILE, passphrase='x')
        self.assertRaises(ImproperlyConfigured, db.connect)

    def test_kdf_iter(self):
        db = SqlCipherDatabase(DB_FILE, passphrase=PASSPHRASE, kdf_iter=9999)
        self.assertRaises(ImproperlyConfigured, db.connect)

########NEW FILE########
__FILENAME__ = tests_sqlite_ext
import sqlite3; sqlite3.enable_callback_tracebacks(True)
import unittest

from peewee import *
from playhouse import sqlite_ext as sqe

# use a disk-backed db since memory dbs only exist for a single connection and
# we need to share the db w/2 for the locking tests.  additionally, set the
# sqlite_busy_timeout to 100ms so when we test locking it doesn't take forever
ext_db = sqe.SqliteExtDatabase('tmp.db', timeout=.1)

# test aggregate.
class WeightedAverage(object):
    def __init__(self):
        self.total_weight = 0.0
        self.total_ct = 0.0

    def step(self, value, wt=None):
        wt = wt or 1.0
        self.total_weight += wt
        self.total_ct += wt * value

    def finalize(self):
        if self.total_weight != 0.0:
            return self.total_ct / self.total_weight
        return 0.0

# test collations
def _cmp(l, r):
    if l < r:
        return -1
    elif r < l:
        return 1
    return 0

def collate_reverse(s1, s2):
    return -_cmp(s1, s2)

@ext_db.collation()
def collate_case_insensitive(s1, s2):
    return _cmp(s1.lower(), s2.lower())

# test function
def title_case(s):
    return s.title()

@ext_db.func()
def rstrip(s, n):
    return s.rstrip(n)

# register test aggregates / collations / functions
ext_db.register_aggregate(WeightedAverage, 1, 'weighted_avg')
ext_db.register_aggregate(WeightedAverage, 2, 'weighted_avg2')
ext_db.register_collation(collate_reverse)
ext_db.register_function(title_case)


class BaseExtModel(sqe.Model):
    class Meta:
        database = ext_db

class Post(BaseExtModel):
    message = TextField()

class FTSPost(Post, sqe.FTSModel):
    """Automatically managed and populated via the Post model."""
    pass

class FTSDoc(sqe.FTSModel):
    """Manually managed and populated using queries."""
    message = TextField()
    class Meta:
        database = ext_db

class ManagedDoc(sqe.FTSModel):
    message = TextField()
    class Meta:
        database = ext_db

class MultiColumn(sqe.FTSModel):
    c1 = CharField(default='')
    c2 = CharField(default='')
    c3 = CharField(default='')
    c4 = IntegerField()

    class Meta:
        database = ext_db

class Values(BaseExtModel):
    klass = IntegerField()
    value = FloatField()
    weight = FloatField()



class SqliteExtTestCase(unittest.TestCase):
    messages = [
        'A faith is a necessity to a man. Woe to him who believes in nothing.',
        'All who call on God in true faith, earnestly from the heart, will '
        'certainly be heard, and will receive what they have asked and desired.',
        'Be faithful in small things because it is in them that your strength lies.',
        'Faith consists in believing when it is beyond the power of reason to believe.',
        'Faith has to do with things that are not seen and hope with things that are not at hand.',
    ]
    values = [
        ('aaaaa bbbbb ccccc ddddd', 'aaaaa ccccc', 'zzzzz zzzzz', 1),
        ('bbbbb ccccc ddddd eeeee', 'bbbbb', 'zzzzz', 2),
        ('ccccc ccccc ddddd fffff', 'ccccc', 'yyyyy', 3),
        ('ddddd', 'ccccc', 'xxxxx', 4),
    ]

    def setUp(self):
        FTSDoc.drop_table(True)
        ManagedDoc.drop_table(True)
        FTSPost.drop_table(True)
        Post.drop_table(True)
        MultiColumn.drop_table(True)
        Values.drop_table(True)
        Values.create_table()
        MultiColumn.create_table(tokenize='porter')
        Post.create_table()
        FTSPost.create_table(tokenize='porter', content=Post)
        ManagedDoc.create_table(tokenize='porter', content=Post.message)
        FTSDoc.create_table(tokenize='porter')

    def test_pk_autoincrement(self):
        class AutoInc(Model):
            id = sqe.PrimaryKeyAutoIncrementField()
            foo = CharField()

        compiler = ext_db.compiler()
        sql, params = compiler.create_table(AutoInc)
        self.assertEqual(
            sql,
            'CREATE TABLE "autoinc" '
            '("id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, '
            '"foo" VARCHAR(255) NOT NULL)')

    def assertMessages(self, query, indices):
        self.assertEqual([x.message for x in query], [
            self.messages[i] for i in indices])

    def test_fts_manual(self):
        messages = [FTSDoc.create(message=msg) for msg in self.messages]

        q = FTSDoc.select().where(FTSDoc.match('believe')).order_by(FTSDoc.id)
        self.assertMessages(q, [0, 3])

        q = FTSDoc.search('believe')
        self.assertMessages(q, [3, 0])

        q = FTSDoc.search('things')
        self.assertEqual([(x.message, x.score) for x in q], [
            (self.messages[4], 2.0 / 3),
            (self.messages[2], 1.0 / 3),
        ])

    def _create_multi_column(self):
        for c1, c2, c3, c4 in self.values:
            MultiColumn.create(c1=c1, c2=c2, c3=c3, c4=c4)

    def test_fts_multi_column(self):
        def assertResults(term, expected):
            results = [
                (x.c4, round(x.score, 2))
                for x in MultiColumn.search(term)]
            self.assertEqual(results, expected)

        self._create_multi_column()

        # `bbbbb` appears two times in `c1`, one time in `c2`.
        assertResults('bbbbb', [
            (2, 1.5),  # 1/2 + 1/1
            (1, 0.5),  # 1/2
        ])

        # `ccccc` appears four times in `c1`, three times in `c2`.
        assertResults('ccccc', [
            (3, .83),  # 2/4 + 1/3
            (1, .58), # 1/4 + 1/3
            (4, .33), # 1/3
            (2, .25), # 1/4
        ])

        # `zzzzz` appears three times in c3.
        assertResults('zzzzz', [
            (1, .67),
            (2, .33),
        ])

        self.assertEqual(
            [x.score for x in MultiColumn.search('ddddd')],
            [.25, .25, .25, .25])

    def test_bm25(self):
        def assertResults(term, col_idx, expected):
            query = MultiColumn.search_bm25(term, MultiColumn.c1)
            self.assertEqual(
                [(mc.c4, round(mc.score, 2)) for mc in query],
                expected)

        self._create_multi_column()
        MultiColumn.create(c1='aaaaa fffff', c4=5)

        assertResults('aaaaa', 1, [
            (5, 0.39),
            (1, 0.3),
        ])
        assertResults('fffff', 1, [
            (5, 0.39),
            (3, 0.3),
        ])
        assertResults('eeeee', 1, [
            (2, 0.97),
        ])

        # No column specified, use the first text field.
        query = MultiColumn.search_bm25('fffff')
        self.assertEqual([(mc.c4, round(mc.score, 2)) for mc in query], [
            (5, 0.39),
            (3, 0.3),
        ])

        # Use helpers.
        query = (MultiColumn
                 .select(
                     MultiColumn.c4,
                     MultiColumn.bm25(MultiColumn.c1).alias('score'))
                 .where(MultiColumn.match('aaaaa'))
                 .order_by(SQL('score').desc()))
        self.assertEqual([(mc.c4, round(mc.score, 2)) for mc in query], [
            (5, 0.39),
            (1, 0.3),
        ])

    def test_bm25_alt_corpus(self):
        for message in self.messages:
            FTSDoc.create(message=message)

        def assertResults(term, expected):
            query = FTSDoc.search_bm25(term)
            cleaned = [
                (round(doc.score, 2), ' '.join(doc.message.split()[:2]))
                for doc in query]
            self.assertEqual(cleaned, expected)

        assertResults('things', [
            (0.45, 'Faith has'),
            (0.36, 'Be faithful'),
        ])

        # Indeterminate order since all are 0.0. All phrases contain the word
        # faith, so there is no meaningful score.
        results = [x.score for x in FTSDoc.search_bm25('faith')]
        self.assertEqual(results, [0., 0., 0., 0., 0.])

    def _test_fts_auto(self, ModelClass):
        posts = []
        for message in self.messages:
            posts.append(Post.create(message=message))

        # Nothing matches, index is not built.
        pq = ModelClass.select().where(ModelClass.match('faith'))
        self.assertEqual(list(pq), [])

        ModelClass.rebuild()
        ModelClass.optimize()

        # it will stem faithful -> faith b/c we use the porter tokenizer
        pq = (ModelClass
              .select()
              .where(ModelClass.match('faith'))
              .order_by(ModelClass.id))
        self.assertMessages(pq, range(len(self.messages)))

        pq = (ModelClass
              .select()
              .where(ModelClass.match('believe'))
              .order_by(ModelClass.id))
        self.assertMessages(pq, [0, 3])

        pq = (ModelClass
              .select()
              .where(ModelClass.match('thin*'))
              .order_by(ModelClass.id))
        self.assertMessages(pq, [2, 4])

        pq = (ModelClass
              .select()
              .where(ModelClass.match('"it is"'))
              .order_by(ModelClass.id))
        self.assertMessages(pq, [2, 3])

        pq = ModelClass.search('things')
        self.assertEqual([(x.message, x.score) for x in pq], [
            (self.messages[4], 2.0 / 3),
            (self.messages[2], 1.0 / 3),
        ])

        pq = (ModelClass
              .select(sqe.Rank(ModelClass))
              .where(ModelClass.match('faithful'))
              .tuples())
        self.assertEqual([x[0] for x in pq], [.2] * 5)

        pq = (ModelClass
              .search('faithful')
              .dicts())
        self.assertEqual([x['score'] for x in pq], [.2] * 5)

    def test_fts_auto_model(self):
        self._test_fts_auto(FTSPost)

    def test_fts_auto_field(self):
        self._test_fts_auto(ManagedDoc)

    def test_custom_agg(self):
        data = (
            (1, 3.4, 1.0),
            (1, 6.4, 2.3),
            (1, 4.3, 0.9),
            (2, 3.4, 1.4),
            (3, 2.7, 1.1),
            (3, 2.5, 1.1),
        )
        for klass, value, wt in data:
            Values.create(klass=klass, value=value, weight=wt)

        vq = (Values
              .select(
                  Values.klass,
                  fn.weighted_avg(Values.value).alias('wtavg'),
                  fn.avg(Values.value).alias('avg'))
              .group_by(Values.klass))
        q_data = [(v.klass, v.wtavg, v.avg) for v in vq]
        self.assertEqual(q_data, [
            (1, 4.7, 4.7),
            (2, 3.4, 3.4),
            (3, 2.6, 2.6),
        ])

        vq = (Values
              .select(
                  Values.klass,
                  fn.weighted_avg2(Values.value, Values.weight).alias('wtavg'),
                  fn.avg(Values.value).alias('avg'))
              .group_by(Values.klass))
        q_data = [(v.klass, str(v.wtavg)[:4], v.avg) for v in vq]
        self.assertEqual(q_data, [
            (1, '5.23', 4.7),
            (2, '3.4', 3.4),
            (3, '2.6', 2.6),
        ])

    def test_custom_collation(self):
        for i in [1, 4, 3, 5, 2]:
            Post.create(message='p%d' % i)

        pq = Post.select().order_by(Clause(Post.message, SQL('collate collate_reverse')))
        self.assertEqual([p.message for p in pq], ['p5', 'p4', 'p3', 'p2', 'p1'])

    def test_collation_decorator(self):
        posts = [Post.create(message=m) for m in ['aaa', 'Aab', 'ccc', 'Bba', 'BbB']]
        pq = Post.select().order_by(collate_case_insensitive.collation(Post.message))
        self.assertEqual([p.message for p in pq], [
            'aaa',
            'Aab',
            'Bba',
            'BbB',
            'ccc',
        ])

    def test_custom_function(self):
        p1 = Post.create(message='this is a test')
        p2 = Post.create(message='another TEST')

        sq = Post.select().where(fn.title_case(Post.message) == 'This Is A Test')
        self.assertEqual(list(sq), [p1])

        sq = Post.select(fn.title_case(Post.message)).tuples()
        self.assertEqual([x[0] for x in sq], [
            'This Is A Test',
            'Another Test',
        ])

    def test_function_decorator(self):
        [Post.create(message=m) for m in ['testing', 'chatting  ', '  foo']]
        pq = Post.select(fn.rstrip(Post.message, 'ing')).order_by(Post.id)
        self.assertEqual([x[0] for x in pq.tuples()], [
            'test', 'chatting  ', '  foo'])

        pq = Post.select(fn.rstrip(Post.message, ' ')).order_by(Post.id)
        self.assertEqual([x[0] for x in pq.tuples()], [
            'testing', 'chatting', '  foo'])

    def test_granular_transaction(self):
        conn = ext_db.get_conn()

        def test_locked_dbw(isolation_level):
            with ext_db.granular_transaction(isolation_level):
                Post.create(message='p1')  # Will not be saved.
                conn2 = ext_db._connect(ext_db.database, **ext_db.connect_kwargs)
                conn2.execute('insert into post (message) values (?);', ('x1',))
        self.assertRaises(sqlite3.OperationalError, test_locked_dbw, 'exclusive')
        self.assertRaises(sqlite3.OperationalError, test_locked_dbw, 'immediate')
        self.assertRaises(sqlite3.OperationalError, test_locked_dbw, 'deferred')

        def test_locked_dbr(isolation_level):
            with ext_db.granular_transaction(isolation_level):
                Post.create(message='p2')
                conn2 = ext_db._connect(ext_db.database, **ext_db.connect_kwargs)
                res = conn2.execute('select message from post')
                return res.fetchall()

        # no read-only stuff with exclusive locks
        self.assertRaises(sqlite3.OperationalError, test_locked_dbr, 'exclusive')

        # ok to do readonly w/immediate and deferred (p2 is saved twice)
        self.assertEqual(test_locked_dbr('immediate'), [])
        self.assertEqual(test_locked_dbr('deferred'), [('p2',)])

        # test everything by hand, by setting the default connection to
        # 'exclusive' and turning off autocommit behavior
        ext_db.set_autocommit(False)
        conn.isolation_level = 'exclusive'
        Post.create(message='p3')  # uncommitted

        # now, open a second connection w/exclusive and try to read, it will
        # be locked
        conn2 = ext_db._connect(ext_db.database, **ext_db.connect_kwargs)
        conn2.isolation_level = 'exclusive'
        self.assertRaises(sqlite3.OperationalError, conn2.execute, 'select * from post')

        # rollback the first connection's transaction, releasing the exclusive lock
        conn.rollback()
        ext_db.set_autocommit(True)

        with ext_db.granular_transaction('deferred'):
            Post.create(message='p4')

        res = conn2.execute('select message from post order by message;')
        self.assertEqual([x[0] for x in res.fetchall()], [
            'p2', 'p2', 'p4'])

########NEW FILE########
__FILENAME__ = tests_test_utils
import functools
import unittest

from peewee import *
from playhouse.test_utils import test_database


db1 = SqliteDatabase(':memory:')
db1._flag = 'db1'
db2 = SqliteDatabase(':memory:')
db2._flag = 'db2'

class BaseModel(Model):
    class Meta:
        database = db1

class Data(BaseModel):
    key = CharField()

    class Meta:
        order_by = ('key',)

class DataItem(BaseModel):
    data = ForeignKeyField(Data, related_name='items')
    value = CharField()

    class Meta:
        order_by = ('value',)

class TestTestDatabaseCtxMgr(unittest.TestCase):
    def setUp(self):
        Data.create_table()
        DataItem.create_table()
        a = Data.create(key='a')
        b = Data.create(key='b')
        DataItem.create(data=a, value='a1')
        DataItem.create(data=a, value='a2')
        DataItem.create(data=b, value='b1')

    def tearDown(self):
        # Drop tables from db1.
        DataItem.drop_table()
        Data.drop_table()

        # Drop tables from db2.
        db2.execute_sql('drop table if exists dataitem;')
        db2.execute_sql('drop table if exists data;')

    def assertUsing(self, db):
        self.assertEqual(Data._meta.database._flag, db)
        self.assertEqual(DataItem._meta.database._flag, db)

    def case_wrapper(fn):
        @functools.wraps(fn)
        def inner(self):
            self.assertUsing('db1')
            return fn(self)
        return inner

    @case_wrapper
    def test_no_options(self):
        with test_database(db2, (Data, DataItem), create_tables=True):
            self.assertUsing('db2')

            # Tables were created automatically.
            self.assertTrue(Data.table_exists())
            self.assertTrue(DataItem.table_exists())

            # There are no rows in the db.
            self.assertEqual(Data.select().count(), 0)
            self.assertEqual(DataItem.select().count(), 0)

            # Verify we can create items in the db.
            d = Data.create(key='c')
            self.assertEqual(Data.select().count(), 1)

        self.assertUsing('db1')
        # Ensure that no changes were made to db1.
        self.assertEqual([x.key for x in Data.select()], ['a', 'b'])

        # Ensure the tables were dropped.
        res = db2.execute_sql('select * from sqlite_master')
        self.assertEqual(res.fetchall(), [])

    @case_wrapper
    def test_explicit_create_tables(self):
        # Retrieve a reference to a model in db1 and verify that it
        # has the correct items.
        a = Data.get(Data.key == 'a')
        self.assertEqual([x.value for x in a.items], ['a1', 'a2'])

        with test_database(db2, (Data, DataItem), create_tables=False):
            self.assertUsing('db2')

            # Table hasn't been created.
            self.assertFalse(Data.table_exists())
            self.assertFalse(DataItem.table_exists())

        self.assertUsing('db1')

        # We can still fetch the related items for object 'a'.
        self.assertEqual([x.value for x in a.items], ['a1', 'a2'])

    @case_wrapper
    def test_exception_handling(self):
        def raise_exc():
            with test_database(db2, (Data, DataItem)):
                self.assertUsing('db2')
                c = Data.create(key='c')
                # This will raise Data.DoesNotExist.
                Data.get(Data.key == 'a')

        # Ensure the exception is raised by the ctx mgr.
        self.assertRaises(Data.DoesNotExist, raise_exc)
        self.assertUsing('db1')

        # Ensure that the tables in db2 are removed.
        res = db2.execute_sql('select * from sqlite_master')
        self.assertEqual(res.fetchall(), [])

        # Ensure the data in db1 is intact.
        self.assertEqual([x.key for x in Data.select()], ['a', 'b'])

    @case_wrapper
    def test_exception_handling_explicit_cd(self):
        def raise_exc():
            with test_database(db2, (Data, DataItem), create_tables=False):
                self.assertUsing('db2')
                Data.create_table()
                c = Data.create(key='c')
                # This will raise Data.DoesNotExist.
                Data.get(Data.key == 'a')

        self.assertRaises(Data.DoesNotExist, raise_exc)
        self.assertUsing('db1')

        # Ensure that the tables in db2 are still present.
        res = db2.execute_sql('select key from data;')
        self.assertEqual(res.fetchall(), [('c',)])

        # Ensure the data in db1 is intact.
        self.assertEqual([x.key for x in Data.select()], ['a', 'b'])

    @case_wrapper
    def test_mismatch_models(self):
        a = Data.get(Data.key == 'a')
        with test_database(db2, (Data,)):
            d2_id = Data.insert(id=a.id, key='c').execute()
            c = Data.get(Data.id == d2_id)

            # Mismatches work and the queries are handled at the class
            # level, so the Data returned from the DataItems will
            # be from db2.
            self.assertEqual([x.value for x in c.items], ['a1', 'a2'])
            for item in c.items:
                self.assertEqual(item.data.key, 'c')

########NEW FILE########
__FILENAME__ = test_utils
from peewee import create_model_tables
from peewee import drop_model_tables


class test_database(object):
    def __init__(self, db, models, create_tables=True, drop_tables=True,
                 fail_silently=False):
        self.db = db
        self.models = models
        self.create_tables = create_tables
        self.drop_tables = drop_tables
        self.fail_silently = fail_silently

    def __enter__(self):
        self.orig = []
        for m in self.models:
            self.orig.append(m._meta.database)
            m._meta.database = self.db
        if self.create_tables:
            create_model_tables(self.models, fail_silently=self.fail_silently)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.create_tables and self.drop_tables:
            drop_model_tables(self.models, fail_silently=self.fail_silently)
        for i, m in enumerate(self.models):
            m._meta.database = self.orig[i]

########NEW FILE########
__FILENAME__ = pwiz
#!/usr/bin/env python

from optparse import OptionParser
import re
import sys

from peewee import *
from peewee import print_

try:
    from MySQLdb.constants import FIELD_TYPE
except ImportError:
    try:
        from pymysql.constants import FIELD_TYPE
    except ImportError:
        FIELD_TYPE = None


RESERVED_WORDS = set([
    'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del', 'elif',
    'else', 'except', 'exec', 'finally', 'for', 'from', 'global', 'if', 'import',
    'in', 'is', 'lambda', 'not', 'or', 'pass', 'print', 'raise', 'return', 'try',
    'while', 'with', 'yield',
])

TEMPLATE = """from peewee import *

database = %s('%s', **%s)

class UnknownField(object):
    pass

class BaseModel(Model):
    class Meta:
        database = database
"""

class UnknownField(object):
    pass


class Column(object):
    """
    Store metadata about a database column.
    """
    primary_key_types = (IntegerField, PrimaryKeyField)

    def __init__(self, name, field_class, raw_column_type, nullable,
                 primary_key=False, max_length=None, db_column=None):
        self.name = name
        self.field_class = field_class
        self.raw_column_type = raw_column_type
        self.nullable = nullable
        self.primary_key = primary_key
        self.max_length = max_length
        self.db_column = db_column

    def __repr__(self):
        attrs = [
            'field_class',
            'raw_column_type',
            'nullable',
            'primary_key',
            'max_length',
            'db_column']
        keyword_args = ', '.join(
            '%s=%s' % (attr, getattr(self, attr))
            for attr in attrs)
        return 'Column(%s, %s)' % (self.name, keyword_args)

    def get_field_parameters(self):
        params = {}

        # Set up default attributes.
        if self.nullable:
            params['null'] = True
        if self.field_class is CharField and self.max_length:
            params['max_length'] = self.max_length
        if self.field_class is ForeignKeyField or self.name != self.db_column:
            params['db_column'] = "'%s'" % self.db_column
        if self.primary_key and not self.field_class is PrimaryKeyField:
            params['primary_key'] = True

        # Handle ForeignKeyField-specific attributes.
        if self.field_class is ForeignKeyField:
            params['rel_model'] = self.rel_model

        return params

    def is_primary_key(self):
        return self.field_class is PrimaryKeyField or self.primary_key

    def set_foreign_key(self, foreign_key, model_names):
        self.field_class = ForeignKeyField
        if foreign_key.dest_table == foreign_key.table:
            self.rel_model = "'self'"
        else:
            self.rel_model = model_names[foreign_key.dest_table]
        self.to_field = foreign_key.dest_column

    def get_field(self):
        # Generate the field definition for this column.
        field_params = self.get_field_parameters()
        param_str = ', '.join('%s=%s' % (k, v)
                              for k, v in sorted(field_params.items()))
        field = '%s = %s(%s)' % (
            self.name,
            self.field_class.__name__,
            param_str)

        if self.field_class is UnknownField:
            field = '%s  # %s' % (field, self.raw_column_type)

        return field


class ForeignKeyMapping(object):
    def __init__(self, table, column, dest_table, dest_column):
        self.table = table
        self.column = column
        self.dest_table = dest_table
        self.dest_column = dest_column

    def __repr__(self):
        return 'ForeignKeyMapping(%s.%s -> %s.%s)' % (
            self.table,
            self.column,
            self.dest_table,
            self.dest_column)


class Metadata(object):
    column_map = {}
    database_class = None

    def __init__(self, database, **kwargs):
        self._conn = self.connect(database, **kwargs)
        self.database = database
        self.database_kwargs = kwargs

    def execute(self, sql, *params):
        return self._conn.execute_sql(sql, params)

    def set_search_path(self, *path):
        self._conn.set_search_path(*path)

    def connect(self, database, **kwargs):
        return self.database_class(database, **kwargs)

    def get_tables(self):
        """Returns a list of table names."""
        return self._conn.get_tables()

    def get_columns(self, table):
        pass

    def get_foreign_keys(self, table, schema=None):
        pass


class PostgresqlMetadata(Metadata):
    # select oid, typname from pg_type;
    column_map = {
        16: BooleanField,
        17: BlobField,
        20: BigIntegerField,
        21: IntegerField,
        23: IntegerField,
        25: TextField,
        700: FloatField,
        701: FloatField,
        1042: CharField, # blank-padded CHAR
        1043: CharField,
        1082: DateField,
        1114: DateTimeField,
        1184: DateTimeField,
        1083: TimeField,
        1266: TimeField,
        1700: DecimalField,
        2950: TextField, # UUID
    }
    database_class = PostgresqlDatabase

    def get_columns(self, table):
        # Get basic metadata about columns.
        cursor = self.execute("""
            SELECT
                column_name, is_nullable, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name=%s""", table)
        name_to_info = {}
        for row in cursor.fetchall():
            name_to_info[row[0]] = {
                'db_column': row[0],
                'nullable': row[1] == 'YES',
                'raw_column_type': row[2],
                'max_length': row[3],
                'primary_key': False,
            }

        # Look up the actual column type for each column.
        cursor = self.execute('SELECT * FROM "%s" LIMIT 1' % table)

        # Store column metadata in dictionary keyed by column name.
        for column_description in cursor.description:
            field_class = self.column_map.get(
                column_description.type_code,
                UnknownField)
            column = column_description.name
            name_to_info[column]['field_class'] = field_class

        # Look up the primary keys.
        cursor = self.execute("""
            SELECT pg_attribute.attname
            FROM pg_index, pg_class, pg_attribute
            WHERE
              pg_class.oid = '%s'::regclass AND
              indrelid = pg_class.oid AND
              pg_attribute.attrelid = pg_class.oid AND
              pg_attribute.attnum = any(pg_index.indkey)
              AND indisprimary;""" % table)
        pk_names = [row[0] for row in cursor.fetchall()]
        for pk_name in pk_names:
            name_to_info[pk_name]['primary_key'] = True
            if name_to_info[pk_name]['field_class'] is IntegerField:
                name_to_info[pk_name]['field_class'] = PrimaryKeyField

        columns = {}
        for name, column_info in name_to_info.items():
            columns[name] = Column(
                name,
                field_class=column_info['field_class'],
                raw_column_type=column_info['raw_column_type'],
                nullable=column_info['nullable'],
                primary_key=column_info['primary_key'],
                max_length=column_info['max_length'],
                db_column=name)

        return columns

    def get_foreign_keys(self, table, schema=None):
        schema = schema or 'public'
        sql = """
            SELECT
                kcu.column_name, ccu.table_name, ccu.column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON (tc.constraint_name = kcu.constraint_name AND
                    tc.constraint_schema = kcu.constraint_schema)
            JOIN information_schema.constraint_column_usage AS ccu
                ON (ccu.constraint_name = tc.constraint_name AND
                    ccu.constraint_schema = tc.constraint_schema)
            WHERE
                tc.constraint_type = 'FOREIGN KEY' AND
                tc.table_name = %s AND
                tc.table_schema = %s"""
        cursor = self.execute(sql, table, schema)
        return [
            ForeignKeyMapping(table, column, dest_table, dest_column)
            for column, dest_table, dest_column in cursor]


class MySQLMetadata(Metadata):
    if FIELD_TYPE is None:
        column_map = {}
    else:
        column_map = {
            FIELD_TYPE.BLOB: TextField,
            FIELD_TYPE.CHAR: CharField,
            FIELD_TYPE.DATE: DateField,
            FIELD_TYPE.DATETIME: DateTimeField,
            FIELD_TYPE.DECIMAL: DecimalField,
            FIELD_TYPE.DOUBLE: FloatField,
            FIELD_TYPE.FLOAT: FloatField,
            FIELD_TYPE.INT24: IntegerField,
            FIELD_TYPE.LONG_BLOB: TextField,
            FIELD_TYPE.LONG: IntegerField,
            FIELD_TYPE.LONGLONG: BigIntegerField,
            FIELD_TYPE.MEDIUM_BLOB: TextField,
            FIELD_TYPE.NEWDECIMAL: DecimalField,
            FIELD_TYPE.SHORT: IntegerField,
            FIELD_TYPE.STRING: CharField,
            FIELD_TYPE.TIMESTAMP: DateTimeField,
            FIELD_TYPE.TIME: TimeField,
            FIELD_TYPE.TINY_BLOB: TextField,
            FIELD_TYPE.TINY: IntegerField,
            FIELD_TYPE.VAR_STRING: CharField,
        }
    database_class = MySQLDatabase

    def __init__(self, database, **kwargs):
        if 'password' in kwargs:
            kwargs['passwd'] = kwargs.pop('password')
        super(MySQLMetadata, self).__init__(database, **kwargs)

    def get_columns(self, table):
        pk_name = self.get_primary_key(table)

        # Get basic metadata about columns.
        cursor = self.execute("""
            SELECT
                column_name, is_nullable, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name=%s AND table_schema=DATABASE()""", table)
        name_to_info = {}
        for row in cursor.fetchall():
            name_to_info[row[0]] = {
                'db_column': row[0],
                'nullable': row[1] == 'YES',
                'raw_column_type': row[2],
                'max_length': row[3],
                'primary_key': False,
            }

        # Look up the actual column type for each column.
        cursor = self.execute('SELECT * FROM `%s` LIMIT 1' % table)

        # Store column metadata in dictionary keyed by column name.
        for column_description in cursor.description:
            name, type_code = column_description[:2]
            field_class = self.column_map.get(type_code, UnknownField)

            if name == pk_name:
                name_to_info[name]['primary_key'] = True
                if field_class is IntegerField:
                    field_class = PrimaryKeyField

            name_to_info[name]['field_class'] = field_class

        columns = {}
        for name, column_info in name_to_info.items():
            columns[name] = Column(
                name,
                field_class=column_info['field_class'],
                raw_column_type=column_info['raw_column_type'],
                nullable=column_info['nullable'],
                primary_key=column_info['primary_key'],
                max_length=column_info['max_length'],
                db_column=name)

        return columns

    def get_primary_key(self, table):
        cursor = self.execute('SHOW INDEX FROM `%s`' % table)
        for row in cursor.fetchall():
            if row[2] == 'PRIMARY':
                return row[4]

    def get_foreign_keys(self, table, schema=None):
        framing = """
            SELECT column_name, referenced_table_name, referenced_column_name
            FROM information_schema.key_column_usage
            WHERE table_name = %s
                AND table_schema = DATABASE()
                AND referenced_table_name IS NOT NULL
                AND referenced_column_name IS NOT NULL
        """
        cursor = self.execute(framing, table)
        return [
            ForeignKeyMapping(table, column, dest_table, dest_column)
            for column, dest_table, dest_column in cursor]


class SqliteMetadata(Metadata):
    column_map = {
        'bigint': BigIntegerField,
        'blob': BlobField,
        'bool': BooleanField,
        'boolean': BooleanField,
        'char': CharField,
        'date': DateField,
        'datetime': DateTimeField,
        'decimal': DecimalField,
        'integer': IntegerField,
        'integer unsigned': IntegerField,
        'int': IntegerField,
        'long': BigIntegerField,
        'real': FloatField,
        'smallinteger': IntegerField,
        'smallint': IntegerField,
        'smallint unsigned': IntegerField,
        'text': TextField,
        'time': TimeField,
    }
    database_class = SqliteDatabase

    begin = '(?:["\[\(]+)?'
    end = '(?:["\]\)]+)?'
    re_foreign_key = (
        '(?:FOREIGN KEY\s*)?'
        '{begin}(.+?){end}\s+(?:.+\s+)?'
        'references\s+{begin}(.+?){end}'
        '\s*\(["|\[]?(.+?)["|\]]?\)').format(begin=begin, end=end)
    re_varchar = r'^\s*(?:var)?char\s*\(\s*(\d+)\s*\)\s*$'

    def _map_col(self, column_type):
        raw_column_type = column_type.lower()
        if raw_column_type in self.column_map:
            field_class = self.column_map[raw_column_type]
        elif re.search(self.re_varchar, raw_column_type):
            field_class = CharField
        else:
            column_type = re.sub('\(.+\)', '', raw_column_type)
            field_class = self.column_map.get(column_type, UnknownField)
        return field_class, raw_column_type

    def get_columns(self, table):
        columns = {}

        # Column ID, Name, Column Type, Not Null?, Default, Is Primary Key?
        cursor = self.execute('PRAGMA table_info("%s")' % table)

        for (_, name, column_type, not_null, _, is_pk) in cursor.fetchall():
            field_class, raw_column_type = self._map_col(column_type)

            if is_pk and field_class == IntegerField:
                field_class = PrimaryKeyField

            max_length = None
            if field_class is CharField:
                match = re.match('\w+\((\d+)\)', column_type)
                if match:
                    max_length, = match.groups()

            columns[name] = Column(
                name,
                field_class=field_class,
                raw_column_type=raw_column_type,
                nullable=not not_null,
                primary_key=is_pk,
                max_length=max_length,
                db_column=name)

        return columns

    def get_foreign_keys(self, table, schema=None):
        query = """
            SELECT sql
            FROM sqlite_master
            WHERE (tbl_name = ? AND type = ?)"""
        cursor = self.execute(query, table, 'table')
        table_definition = cursor.fetchone()[0].strip()

        try:
            columns = re.search('\((.+)\)', table_definition).groups()[0]
        except AttributeError:
            print_('Unable to read table definition for "%s"' % table)
            return []

        fks = []
        for column_def in columns.split(','):
            column_def = column_def.strip()
            match = re.search(self.re_foreign_key, column_def, re.I)
            if not match:
                continue

            column, dest_table, dest_column = [
                s.strip('"') for s in match.groups()]
            fks.append(ForeignKeyMapping(
                table=table,
                column=column,
                dest_table=dest_table,
                dest_column=dest_column))

        return fks


DATABASE_ALIASES = {
    SqliteMetadata: ['sqlite', 'sqlite3'],
    MySQLMetadata: ['mysql', 'mysqldb'],
    PostgresqlMetadata: ['postgres', 'postgresql'],
}
DATABASE_MAP = dict((value, key)
                    for key in DATABASE_ALIASES
                    for value in DATABASE_ALIASES[key])


def make_introspector(database_type, database, **kwargs):
    if database_type not in DATABASE_MAP:
        err('Unrecognized database, must be one of: %s' %
            ', '.join(DATABASE_MAP.keys()))
        sys.exit(1)

    schema = kwargs.pop('schema', None)
    metadata = DATABASE_MAP[database_type](database, **kwargs)

    if schema:
        metadata.set_search_path(*schema.split(','))

    return Introspector(metadata, schema=schema)


class Introspector(object):
    pk_classes = [PrimaryKeyField, IntegerField]

    def __init__(self, metadata, schema=None):
        self.metadata = metadata
        self.schema = schema

    def make_model_name(self, table):
        model = re.sub('[^\w]+', '', table)
        return ''.join(sub.title() for sub in model.split('_'))

    def make_column_name(self, column):
        column = re.sub('_id$', '', column.lower()) or column.lower()
        if column in RESERVED_WORDS:
            column += '_'
        return column

    def introspect(self):
        # Retrieve all the tables in the database.
        tables = self.metadata.get_tables()

        # Store a mapping of table name -> dictionary of columns.
        columns = {}

        # Store a mapping of table -> foreign keys.
        foreign_keys = {}

        # Store a mapping of table name -> model name.
        model_names = {}

        # Gather the columns for each table.
        for table in tables:
            columns[table] = self.metadata.get_columns(table)
            foreign_keys[table] = self.metadata.get_foreign_keys(
                table, self.schema)
            model_names[table] = self.make_model_name(table)

        # On the second pass convert all foreign keys.
        for table in tables:
            for foreign_key in foreign_keys[table]:
                src = columns[foreign_key.table][foreign_key.column]
                src.set_foreign_key(foreign_key, model_names)

            for column_name, column in columns[table].items():
                column.name = self.make_column_name(column_name)

        return columns, foreign_keys, model_names

    def print_models(self, tables=None):
        columns, foreign_keys, model_names = self.introspect()
        print_(TEMPLATE % (
            self.metadata.database_class.__name__,
            self.metadata.database,
            repr(self.metadata.database_kwargs)))

        def _print_table(table, seen, accum=None):
            accum = accum or []
            for foreign_key in foreign_keys[table]:
                dest = foreign_key.dest_table

                # In the event the destination table has already been pushed
                # for printing, then we have a reference cycle.
                if dest in accum and table not in accum:
                    print_('# Possible reference cycle: %s' % foreign_key)

                # If this is not a self-referential foreign key, and we have
                # not already processed the destination table, do so now.
                if dest not in seen and dest not in accum:
                    seen.add(dest)
                    if dest != table:
                        _print_table(dest, seen, accum + [table])

            print_('class %s(BaseModel):' % model_names[table])
            for name, column in sorted(columns[table].items()):
                if name == 'id' and column.field_class in self.pk_classes:
                    continue

                print_('    %s' % column.get_field())

            print_('')
            print_('    class Meta:')
            print_('        db_table = \'%s\'' % table)
            print_('')

            seen.add(table)

        seen = set()
        for table in sorted(model_names.keys()):
            if table not in seen:
                if not tables or table in tables:
                    _print_table(table, seen)


def err(msg):
    sys.stderr.write('\033[91m%s\033[0m\n' % msg)
    sys.stderr.flush()


if __name__ == '__main__':
    parser = OptionParser(usage='usage: %prog [options] database_name')
    ao = parser.add_option
    ao('-H', '--host', dest='host')
    ao('-p', '--port', dest='port', type='int')
    ao('-u', '--user', dest='user')
    ao('-P', '--password', dest='password')
    ao('-e', '--engine', dest='engine', default='postgresql')
    ao('-s', '--schema', dest='schema')
    ao('-t', '--tables', dest='tables')

    options, args = parser.parse_args()
    ops = ('host', 'port', 'user', 'password', 'schema')
    connect = dict((o, getattr(options, o)) for o in ops if getattr(options, o))

    if len(args) < 1:
        err('Missing required parameter "database"')
        parser.print_help()
        sys.exit(1)

    database = args[-1]

    tables = None
    if options.tables:
        tables = [x for x in options.tables.split(',') if x]

    introspector = make_introspector(options.engine, database, **connect)
    introspector.print_models(tables)

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import optparse
import os
import shutil
import sys
import unittest


def collect():
    import tests
    runtests(tests, 1)

def runtests(suite, verbosity):
    results = unittest.TextTestRunner(verbosity=verbosity).run(suite)
    return results.failures, results.errors

def get_option_parser():
    parser = optparse.OptionParser()
    basic = optparse.OptionGroup(parser, 'Basic test options')
    basic.add_option(
        '-e',
        '--engine',
        dest='engine',
        help=('Database engine to test, one of '
              '[sqlite, postgres, mysql, apsw, sqlcipher, berkeleydb]'))
    basic.add_option('-v', '--verbosity', dest='verbosity', default=1, type='int', help='Verbosity of output')

    suite = optparse.OptionGroup(parser, 'Simple test suite options')
    suite.add_option('-a', '--all', dest='all', default=False, action='store_true', help='Run all tests, including extras')
    suite.add_option('-x', '--extra', dest='extra', default=False, action='store_true', help='Run only extras tests')

    cases = optparse.OptionGroup(parser, 'Individual test module options')
    cases.add_option('--apsw', dest='apsw', default=False, action='store_true', help='apsw tests (requires apsw)')
    cases.add_option('--berkeleydb', dest='berkeleydb', default=False, action='store_true', help='berkeleydb tests (requires pysqlite compiled against berkeleydb)')
    cases.add_option('--csv', dest='csv', default=False, action='store_true', help='csv tests')
    cases.add_option('--djpeewee', dest='djpeewee', default=False, action='store_true', help='djpeewee tests')
    cases.add_option('--gfk', dest='gfk', default=False, action='store_true', help='gfk tests')
    cases.add_option('--kv', dest='kv', default=False, action='store_true', help='key/value store tests')
    cases.add_option('--migrations', dest='migrations', default=False, action='store_true', help='migration helper tests (requires psycopg2)')
    cases.add_option('--pool', dest='pool', default=False, action='store_true', help='connection pool tests')
    cases.add_option('--postgres-ext', dest='postgres_ext', default=False, action='store_true', help='postgres_ext tests (requires psycopg2)')
    cases.add_option('--pwiz', dest='pwiz', default=False, action='store_true', help='pwiz, schema introspector and model generator')
    cases.add_option('--read-slave', dest='read_slave', default=False, action='store_true', help='read_slave tests')
    cases.add_option('--signals', dest='signals', default=False, action='store_true', help='signals tests')
    cases.add_option('--shortcuts', dest='shortcuts', default=False, action='store_true', help='shortcuts tests')
    cases.add_option('--sqlcipher-ext', dest='sqlcipher', default=False, action='store_true', help='sqlcipher_ext tests (requires pysqlcipher)')
    cases.add_option('--sqlite-ext', dest='sqlite_ext', default=False, action='store_true', help='sqlite_ext tests')
    cases.add_option('--test-utils', dest='test_utils', default=False, action='store_true', help='test_utils tests')

    parser.add_option_group(basic)
    parser.add_option_group(suite)
    parser.add_option_group(cases)
    return parser

def collect_modules(options):
    modules = []
    xtra = lambda op: op or options.extra or options.all
    if xtra(options.apsw):
        try:
            from playhouse import tests_apsw
            modules.append(tests_apsw)
        except ImportError:
            print_('Unable to import apsw tests, skipping')
    if xtra(options.berkeleydb):
        try:
            from playhouse import tests_berkeleydb
            modules.append(tests_berkeleydb)
        except ImportError:
            print_('Unable to import berkeleydb tests, skipping')
    if xtra(options.csv):
        from playhouse import tests_csv_loader
        modules.append(tests_csv_loader)
    if xtra(options.djpeewee):
        from playhouse import tests_djpeewee
        modules.append(tests_djpeewee)
    if xtra(options.gfk):
        from playhouse import tests_gfk
        modules.append(tests_gfk)
    if xtra(options.kv):
        from playhouse import tests_kv
        modules.append(tests_kv)
    if xtra(options.migrations):
        try:
            from playhouse import tests_migrate
            modules.append(tests_migrate)
        except ImportError:
            print_('Unable to import migration tests, skipping')
    if xtra(options.pool):
        try:
            from playhouse import tests_pool
            modules.append(tests_pool)
        except ImportError:
            print_('Unable to import connection pool tests, skipping')
    if xtra(options.postgres_ext):
        try:
            from playhouse import tests_postgres
            modules.append(tests_postgres)
        except ImportError:
            print_('Unable to import postgres-ext tests, skipping')
    if xtra(options.pwiz):
        from playhouse import tests_pwiz
        modules.append(tests_pwiz)
    if xtra(options.read_slave):
        from playhouse import tests_read_slave
        modules.append(tests_read_slave)
    if xtra(options.signals):
        from playhouse import tests_signals
        modules.append(tests_signals)
    if xtra(options.shortcuts):
        from playhouse import tests_shortcuts
        modules.append(tests_shortcuts)
    if xtra(options.sqlcipher):
        try:
            from playhouse import tests_sqlcipher_ext
            modules.append(tests_sqlcipher_ext)
        except ImportError:
            print_('Unable to import pysqlcipher tests, skipping')
    if xtra(options.sqlite_ext):
        from playhouse import tests_sqlite_ext
        modules.append(tests_sqlite_ext)
    if xtra(options.test_utils):
        from playhouse import tests_test_utils
        modules.append(tests_test_utils)

    if not modules or options.all:
        import tests
        modules.insert(0, tests)
    return modules

if __name__ == '__main__':
    parser = get_option_parser()
    options, args = parser.parse_args()

    if options.engine:
        os.environ['PEEWEE_TEST_BACKEND'] = options.engine
    os.environ['PEEWEE_TEST_VERBOSITY'] = str(options.verbosity)

    from peewee import print_

    suite = unittest.TestSuite()
    for module in collect_modules(options):
        print_('Adding tests for "%s"' % module.__name__)
        module_suite = unittest.TestLoader().loadTestsFromModule(module)
        suite.addTest(module_suite)

    failures, errors = runtests(suite, options.verbosity)
    if errors:
        sys.exit(2)
    elif failures:
        sys.exit(1)

    files_to_delete = ['tmp.db', 'tmp.bdb.db']
    paths_to_delete = ['tmp.bdb.db-journal']
    for filename in files_to_delete:
        if os.path.exists(filename):
            os.unlink(filename)
    for path in paths_to_delete:
        if os.path.exists(path):
            shutil.rmtree(path)

    sys.exit(0)

########NEW FILE########
__FILENAME__ = tests
# encoding=utf-8

import datetime
import decimal
import itertools
import logging
import operator
import os
import threading
import unittest
import sys
try:
    from Queue import Queue
except ImportError:
    from queue import Queue
from functools import wraps

from peewee import *
from peewee import DeleteQuery
from peewee import InsertQuery
from peewee import logger
from peewee import ModelQueryResultWrapper
from peewee import NaiveQueryResultWrapper
from peewee import prefetch_add_subquery
from peewee import print_
from peewee import QueryCompiler
from peewee import R
from peewee import RawQuery
from peewee import SelectQuery
from peewee import sort_models_topologically
from peewee import transaction
from peewee import UpdateQuery

class QueryLogHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        self.queries = []
        logging.Handler.__init__(self, *args, **kwargs)

    def emit(self, record):
        self.queries.append(record)

if sys.version_info[0] < 3:
    import codecs
    ulit = lambda s: codecs.unicode_escape_decode(s)[0]
    binary_construct = buffer
    binary_types = buffer
else:
    ulit = lambda s: s
    binary_construct = lambda s: bytes(s.encode('raw_unicode_escape'))
    binary_types = (bytes, memoryview)

#
# JUNK TO ALLOW TESTING OF MULTIPLE DATABASE BACKENDS
#

BACKEND = os.environ.get('PEEWEE_TEST_BACKEND', 'sqlite')
TEST_VERBOSITY = int(os.environ.get('PEEWEE_TEST_VERBOSITY') or 1)

if TEST_VERBOSITY > 1:
    handler = logging.StreamHandler()
    handler.setLevel(logging.ERROR)
    logger.addHandler(handler)

database_params = {}

print_('TESTING USING PYTHON %s' % sys.version)

BerkeleyDatabase = None
if BACKEND in ('postgresql', 'postgres', 'pg'):
    database_class = PostgresqlDatabase
    database_name = 'peewee_test'
    import psycopg2
elif BACKEND == 'mysql':
    database_class = MySQLDatabase
    database_name = 'peewee_test'
    try:
        import MySQLdb as mysql
    except ImportError:
        import pymysql as mysql
elif BACKEND == 'apsw':
    from playhouse.apsw_ext import *
    database_class = APSWDatabase
    database_name = 'tmp.db'
    database_params['timeout'] = 1000
elif BACKEND in ('berkeleydb', 'berkeley', 'bdb'):
    from playhouse.berkeleydb import *
    database_class = BerkeleyDatabase
    database_name = 'tmp.bdb.db'
    database_params['timeout'] = 1000
elif BACKEND == 'sqlcipher':
    from playhouse.sqlcipher_ext import *
    database_class = SqlCipherDatabase
    database_name = 'tmp-snakeoilpassphrase.db'
    database_params['passphrase'] = 'snakeoilpassphrase'
    from pysqlcipher import dbapi2 as sqlcipher
    print_('PYSQLCIPHER VERSION: %s' % sqlcipher.version)
else:
    database_class = SqliteDatabase
    database_name = 'tmp.db'
    import sqlite3
    print_('SQLITE VERSION: %s' % sqlite3.version)

#
# TEST-ONLY QUERY COMPILER USED TO CREATE "predictable" QUERIES
#

class TestQueryCompiler(QueryCompiler):
    def _max_alias(self, alias_map):
        return 't0'

    def _ensure_alias_set(self, model, alias_map):
        if model not in alias_map:
            alias_map[model] = model._meta.db_table

    def calculate_alias_map(self, query, start=1):
        alias_map = {query.model_class: query.model_class._meta.db_table}
        for model, joins in query._joins.items():
            if model not in alias_map:
                alias_map[model] = model._meta.db_table
            for join in joins:
                if join.dest not in alias_map:
                    alias_map[join.dest] = join.dest._meta.db_table
        return alias_map

class TestDatabase(database_class):
    compiler_class = TestQueryCompiler
    field_overrides = {}
    interpolation = '?'
    op_overrides = {}
    quote_char = '"'

    def sql_error_handler(self, exception, sql, params, require_commit):
        self.last_error = (sql, params)
        return super(TestDatabase, self).sql_error_handler(
            exception, sql, params, require_commit)

test_db = database_class(database_name, **database_params)
query_db = TestDatabase(database_name, **database_params)
compiler = query_db.compiler()

# create a compiler we can use to test that will generate increasing aliases
# this is used to test self-referential joins
normal_compiler = QueryCompiler('"', '?', {}, {})

#
# BASE MODEL CLASS
#

class TestModel(Model):
    class Meta:
        database = test_db

#
# MODEL CLASSES USED BY TEST CASES
#

class User(TestModel):
    username = CharField()

    class Meta:
        db_table = 'users'

    def prepared(self):
        self.foo = self.username

class Blog(TestModel):
    user = ForeignKeyField(User)
    title = CharField(max_length=25)
    content = TextField(default='')
    pub_date = DateTimeField(null=True)
    pk = PrimaryKeyField()

    def __unicode__(self):
        return '%s: %s' % (self.user.username, self.title)

    def prepared(self):
        self.foo = self.title

class Comment(TestModel):
    blog = ForeignKeyField(Blog, related_name='comments')
    comment = CharField()

class Relationship(TestModel):
    from_user = ForeignKeyField(User, related_name='relationships')
    to_user = ForeignKeyField(User, related_name='related_to')

class NullModel(TestModel):
    char_field = CharField(null=True)
    text_field = TextField(null=True)
    datetime_field = DateTimeField(null=True)
    int_field = IntegerField(null=True)
    float_field = FloatField(null=True)
    decimal_field1 = DecimalField(null=True)
    decimal_field2 = DecimalField(decimal_places=2, null=True)
    double_field = DoubleField(null=True)
    bigint_field = BigIntegerField(null=True)
    date_field = DateField(null=True)
    time_field = TimeField(null=True)
    boolean_field = BooleanField(null=True)

class UniqueModel(TestModel):
    name = CharField(unique=True)

class OrderedModel(TestModel):
    title = CharField()
    created = DateTimeField(default=datetime.datetime.now)

    class Meta:
        order_by = ('-created',)

class Category(TestModel):
    parent = ForeignKeyField('self', related_name='children', null=True)
    name = CharField()

class UserCategory(TestModel):
    user = ForeignKeyField(User)
    category = ForeignKeyField(Category)

class NonIntModel(TestModel):
    pk = CharField(primary_key=True)
    data = CharField()

class NonIntRelModel(TestModel):
    non_int_model = ForeignKeyField(NonIntModel, related_name='nr')

class DBUser(TestModel):
    user_id = PrimaryKeyField(db_column='db_user_id')
    username = CharField(db_column='db_username')

class DBBlog(TestModel):
    blog_id = PrimaryKeyField(db_column='db_blog_id')
    title = CharField(db_column='db_title')
    user = ForeignKeyField(DBUser, db_column='db_user')

class SeqModelA(TestModel):
    id = IntegerField(primary_key=True, sequence='just_testing_seq')
    num = IntegerField()

class SeqModelB(TestModel):
    id = IntegerField(primary_key=True, sequence='just_testing_seq')
    other_num = IntegerField()

class MultiIndexModel(TestModel):
    f1 = CharField()
    f2 = CharField()
    f3 = CharField()

    class Meta:
        indexes = (
            (('f1', 'f2'), True),
            (('f2', 'f3'), False),
        )

class BlogTwo(Blog):
    title = TextField()
    extra_field = CharField()


class Parent(TestModel):
    data = CharField()

class Child(TestModel):
    parent = ForeignKeyField(Parent)
    data = CharField(default='')

class Orphan(TestModel):
    parent = ForeignKeyField(Parent, null=True)
    data = CharField(default='')

class ChildPet(TestModel):
    child = ForeignKeyField(Child)
    data = CharField(default='')

class OrphanPet(TestModel):
    orphan = ForeignKeyField(Orphan)
    data = CharField(default='')

class CSVField(TextField):
    def db_value(self, value):
        if value:
            return ','.join(value)
        return value or ''

    def python_value(self, value):
        return value.split(',') if value else []

class CSVRow(TestModel):
    data = CSVField()

class BlobModel(TestModel):
    data = BlobField()

class Job(TestModel):
    """A job that can be queued for later execution."""
    name = CharField()

class JobExecutionRecord(TestModel):
    """Record of a job having been executed."""
    # the foreign key is also the primary key to enforce the
    # constraint that a job can be executed once and only once
    job = ForeignKeyField(Job, primary_key=True)
    status = CharField()

class TestModelA(TestModel):
    field = CharField(primary_key=True)
    data = CharField()

class TestModelB(TestModel):
    field = CharField(primary_key=True)
    data = CharField()

class TestModelC(TestModel):
    field = CharField(primary_key=True)
    data = CharField()

class Post(TestModel):
    title = CharField()

class Tag(TestModel):
    tag = CharField()

class TagPostThrough(TestModel):
    tag = ForeignKeyField(Tag, related_name='posts')
    post = ForeignKeyField(Post, related_name='tags')

    class Meta:
        primary_key = CompositeKey('tag', 'post')

class Manufacturer(TestModel):
    name = CharField()

class CompositeKeyModel(TestModel):
    f1 = CharField()
    f2 = IntegerField()
    f3 = FloatField()

    class Meta:
        primary_key = CompositeKey('f1', 'f2')

class UserThing(TestModel):
    thing = CharField()
    user = ForeignKeyField(User, related_name='things')

    class Meta:
        primary_key = CompositeKey('thing', 'user')

class Component(TestModel):
    name = CharField()
    manufacturer = ForeignKeyField(Manufacturer, null=True)

class Computer(TestModel):
    hard_drive = ForeignKeyField(Component, related_name='c1')
    memory = ForeignKeyField(Component, related_name='c2')
    processor = ForeignKeyField(Component, related_name='c3')

class CheckModel(TestModel):
    value = IntegerField(constraints=[Check('value > 0')])

# Deferred foreign keys.
SnippetProxy = Proxy()

class Language(TestModel):
    name = CharField()
    selected_snippet = ForeignKeyField(SnippetProxy, null=True)

class Snippet(TestModel):
    code = TextField()
    language = ForeignKeyField(Language, related_name='snippets')

SnippetProxy.initialize(Snippet)

class _UpperField(CharField):
    def python_value(self, value):
        return value.upper() if value else value

class UpperUser(TestModel):
    username = _UpperField()
    class Meta:
        db_table = User._meta.db_table

class Package(TestModel):
    barcode = CharField(unique=True)

class PackageItem(TestModel):
    title = CharField()
    package = ForeignKeyField(
        Package,
        related_name='items',
        to_field=Package.barcode)


MODELS = [
    User,
    Blog,
    Comment,
    Relationship,
    NullModel,
    UniqueModel,
    OrderedModel,
    Category,
    UserCategory,
    NonIntModel,
    NonIntRelModel,
    DBUser,
    DBBlog,
    SeqModelA,
    SeqModelB,
    MultiIndexModel,
    BlogTwo,
    Parent,
    Child,
    Orphan,
    ChildPet,
    OrphanPet,
    BlobModel,
    Job,
    JobExecutionRecord,
    TestModelA,
    TestModelB,
    TestModelC,
    Tag,
    Post,
    TagPostThrough,
    Language,
    Snippet,
    Manufacturer,
    CompositeKeyModel,
    UserThing,
    Component,
    Computer,
    CheckModel,
    Package,
    PackageItem,
]
INT = test_db.interpolation

def drop_tables(only=None):
    for model in reversed(MODELS):
        if only is None or model in only:
            model.drop_table(True)

def create_tables(only=None):
    for model in MODELS:
        if only is None or model in only:
            model.create_table()
#
# BASE TEST CASE USED BY ALL TESTS
#

class BasePeeweeTestCase(unittest.TestCase):
    def setUp(self):
        self.qh = QueryLogHandler()
        logger.setLevel(logging.DEBUG)
        logger.addHandler(self.qh)

    def tearDown(self):
        logger.removeHandler(self.qh)

    def queries(self):
        return [x.msg for x in self.qh.queries]

    def parse_node(self, query, expr_list, compiler=compiler):
        am = compiler.calculate_alias_map(query)
        return compiler.parse_node_list(expr_list, am)

    def parse_query(self, query, node, compiler=compiler):
        am = compiler.calculate_alias_map(query)
        if node is not None:
            return compiler.parse_node(node, am)
        return '', []

    def make_fn(fn_name, attr_name):
        def inner(self, query, expected, expected_params, compiler=compiler):
            fn = getattr(self, fn_name)
            att = getattr(query, attr_name)
            sql, params = fn(query, att, compiler=compiler)
            self.assertEqual(sql, expected)
            self.assertEqual(params, expected_params)
        return inner

    assertSelect = make_fn('parse_node', '_select')
    assertWhere = make_fn('parse_query', '_where')
    assertGroupBy = make_fn('parse_node', '_group_by')
    assertHaving = make_fn('parse_query', '_having')
    assertOrderBy = make_fn('parse_node', '_order_by')

    def assertJoins(self, sq, exp_joins, compiler=compiler):
        am = compiler.calculate_alias_map(sq)
        clauses = compiler.generate_joins(sq._joins, sq.model_class, am)
        joins = [compiler.parse_node(clause, am)[0] for clause in clauses]
        self.assertEqual(sorted(joins), sorted(exp_joins))

#
# BASIC TESTS OF QUERY TYPES AND INTERNAL DATA STRUCTURES
#

class SelectTestCase(BasePeeweeTestCase):
    def test_selection(self):
        sq = SelectQuery(User)
        self.assertSelect(sq, 'users."id", users."username"', [])

        sq = SelectQuery(Blog, Blog.pk, Blog.title, Blog.user, User.username).join(User)
        self.assertSelect(sq, 'blog."pk", blog."title", blog."user_id", users."username"', [])

        sq = SelectQuery(User, fn.Lower(fn.Substr(User.username, 0, 1)).alias('lu'), fn.Count(Blog.pk)).join(Blog)
        self.assertSelect(sq, 'Lower(Substr(users."username", ?, ?)) AS lu, Count(blog."pk")', [0, 1])

        sq = SelectQuery(User, User.username, fn.Count(Blog.select().where(Blog.user == User.id)))
        self.assertSelect(sq, 'users."username", Count((SELECT blog."pk" FROM "blog" AS blog WHERE (blog."user_id" = users."id")))', [])

        sq = SelectQuery(Package, Package, fn.Count(PackageItem.id)).join(PackageItem)
        self.assertSelect(sq, 'package."id", package."barcode", Count(packageitem."id")', [])

    def test_reselect(self):
        sq = SelectQuery(User, User.username)
        self.assertSelect(sq, 'users."username"', [])

        sq2 = sq.select()
        self.assertSelect(sq2, 'users."id", users."username"', [])
        self.assertTrue(id(sq) != id(sq2))

        sq3 = sq2.select(User.id)
        self.assertSelect(sq3, 'users."id"', [])
        self.assertTrue(id(sq2) != id(sq3))

    def test_select_subquery(self):
        subquery = SelectQuery(Child, fn.Count(Child.id)).where(Child.parent == Parent.id).group_by(Child.parent)
        sq = SelectQuery(Parent, Parent, subquery.alias('count'))

        sql = compiler.generate_select(sq)
        self.assertEqual(sql, (
            'SELECT parent."id", parent."data", ' + \
            '(SELECT Count(child."id") FROM "child" AS child ' + \
            'WHERE (child."parent_id" = parent."id") GROUP BY child."parent_id") ' + \
            'AS count FROM "parent" AS parent', []
        ))

    def test_select_subquery_ordering(self):
        sq = Comment.select().join(Blog).where(Blog.pk == 1)
        sq1 = Comment.select().where(
            (Comment.id << sq) |
            (Comment.comment == '*')
        )
        sq2 = Comment.select().where(
            (Comment.comment == '*') |
            (Comment.id << sq)
        )

        sql1, params1 = normal_compiler.generate_select(sq1)
        self.assertEqual(sql1, (
            'SELECT t1."id", t1."blog_id", t1."comment" FROM "comment" AS t1 '
            'WHERE ((t1."id" IN ('
            'SELECT t2."id" FROM "comment" AS t2 '
            'INNER JOIN "blog" AS t3 ON (t2."blog_id" = t3."pk") '
            'WHERE (t3."pk" = ?))) OR (t1."comment" = ?))'))
        self.assertEqual(params1, [1, '*'])

        sql2, params2 = normal_compiler.generate_select(sq2)
        self.assertEqual(sql2, (
            'SELECT t1."id", t1."blog_id", t1."comment" FROM "comment" AS t1 '
            'WHERE ((t1."comment" = ?) OR (t1."id" IN ('
            'SELECT t2."id" FROM "comment" AS t2 '
            'INNER JOIN "blog" AS t3 ON (t2."blog_id" = t3."pk") '
            'WHERE (t3."pk" = ?))))'))
        self.assertEqual(params2, ['*', 1])

    def test_multiple_subquery(self):
        sq2 = Comment.select().where(Comment.comment == '2').join(Blog)
        sq1 = Comment.select().where(
            (Comment.comment == '1') &
            (Comment.id << sq2)
        ).join(Blog)
        sq = Comment.select().where(
            Comment.id << sq1
        )
        sql, params = normal_compiler.generate_select(sq)
        self.assertEqual(sql, (
            'SELECT t1."id", t1."blog_id", t1."comment" '
            'FROM "comment" AS t1 '
            'WHERE (t1."id" IN ('
            'SELECT t2."id" FROM "comment" AS t2 '
            'INNER JOIN "blog" AS t3 ON (t2."blog_id" = t3."pk") '
            'WHERE ((t2."comment" = ?) AND (t2."id" IN ('
            'SELECT t4."id" FROM "comment" AS t4 '
            'INNER JOIN "blog" AS t5 ON (t4."blog_id" = t5."pk") '
            'WHERE (t4."comment" = ?)'
            ')))))'))
        self.assertEqual(params, ['1', '2'])

    def test_select_cloning(self):
        ct = fn.Count(Blog.pk)
        sq = SelectQuery(User, User, User.id.alias('extra_id'), ct.alias('blog_ct')).join(
            Blog, JOIN_LEFT_OUTER).group_by(User).order_by(ct.desc())
        sql = compiler.generate_select(sq)
        self.assertEqual(sql, (
            'SELECT users."id", users."username", users."id" AS extra_id, Count(blog."pk") AS blog_ct ' + \
            'FROM "users" AS users LEFT OUTER JOIN "blog" AS blog ON (users."id" = blog."user_id") ' + \
            'GROUP BY users."id", users."username" ' + \
            'ORDER BY Count(blog."pk") DESC', []
        ))
        self.assertEqual(User.id._alias, None)

    def test_joins(self):
        sq = SelectQuery(User).join(Blog)
        self.assertJoins(sq, ['INNER JOIN "blog" AS blog ON (users."id" = blog."user_id")'])

        sq = SelectQuery(Blog).join(User, JOIN_LEFT_OUTER)
        self.assertJoins(sq, ['LEFT OUTER JOIN "users" AS users ON (blog."user_id" = users."id")'])

        sq = SelectQuery(User).join(Relationship)
        self.assertJoins(sq, ['INNER JOIN "relationship" AS relationship ON (users."id" = relationship."from_user_id")'])

        sq = SelectQuery(User).join(Relationship, on=Relationship.to_user)
        self.assertJoins(sq, ['INNER JOIN "relationship" AS relationship ON (users."id" = relationship."to_user_id")'])

        sq = SelectQuery(User).join(Relationship, JOIN_LEFT_OUTER, Relationship.to_user)
        self.assertJoins(sq, ['LEFT OUTER JOIN "relationship" AS relationship ON (users."id" = relationship."to_user_id")'])

        sq = SelectQuery(Package).join(PackageItem)
        self.assertJoins(sq, ['INNER JOIN "packageitem" AS packageitem ON (package."barcode" = packageitem."package_id")'])

        sq = SelectQuery(PackageItem).join(Package)
        self.assertJoins(sq, ['INNER JOIN "package" AS package ON (packageitem."package_id" = package."barcode")'])

    def test_join_self_referential(self):
        sq = SelectQuery(Category).join(Category)
        self.assertJoins(sq, ['INNER JOIN "category" AS category ON (category."parent_id" = category."id")'])

    def test_join_self_referential_alias(self):
        Parent = Category.alias()
        sq = SelectQuery(Category, Category, Parent).join(Parent, on=(Category.parent == Parent.id)).where(
            Parent.name == 'parent name'
        ).order_by(Parent.name)
        self.assertSelect(sq, 't1."id", t1."parent_id", t1."name", t2."id", t2."parent_id", t2."name"', [], normal_compiler)
        self.assertJoins(sq, [
            'INNER JOIN "category" AS t2 ON (t1."parent_id" = t2."id")',
        ], normal_compiler)
        self.assertWhere(sq, '(t2."name" = ?)', ['parent name'], normal_compiler)
        self.assertOrderBy(sq, 't2."name"', [], normal_compiler)

        Grandparent = Category.alias()
        sq = SelectQuery(Category, Category, Parent, Grandparent).join(
            Parent, on=(Category.parent == Parent.id)
        ).join(
            Grandparent, on=(Parent.parent == Grandparent.id)
        ).where(Grandparent.name == 'g1')
        self.assertSelect(sq, 't1."id", t1."parent_id", t1."name", t2."id", t2."parent_id", t2."name", t3."id", t3."parent_id", t3."name"', [], normal_compiler)
        self.assertJoins(sq, [
            'INNER JOIN "category" AS t2 ON (t1."parent_id" = t2."id")',
            'INNER JOIN "category" AS t3 ON (t2."parent_id" = t3."id")',
        ], normal_compiler)
        self.assertWhere(sq, '(t3."name" = ?)', ['g1'], normal_compiler)

    def test_join_both_sides(self):
        sq = SelectQuery(Blog).join(Comment).switch(Blog).join(User)
        self.assertJoins(sq, [
            'INNER JOIN "comment" AS comment ON (blog."pk" = comment."blog_id")',
            'INNER JOIN "users" AS users ON (blog."user_id" = users."id")',
        ])

        sq = SelectQuery(Blog).join(User).switch(Blog).join(Comment)
        self.assertJoins(sq, [
            'INNER JOIN "users" AS users ON (blog."user_id" = users."id")',
            'INNER JOIN "comment" AS comment ON (blog."pk" = comment."blog_id")',
        ])

    def test_join_switching(self):
        class Artist(TestModel):
            pass

        class Track(TestModel):
            artist = ForeignKeyField(Artist)

        class Release(TestModel):
            artist = ForeignKeyField(Artist)

        class ReleaseTrack(TestModel):
            track = ForeignKeyField(Track)
            release = ForeignKeyField(Release)

        class Genre(TestModel):
            pass

        class TrackGenre(TestModel):
            genre = ForeignKeyField(Genre)
            track = ForeignKeyField(Track)

        multiple_first = Track.select().join(ReleaseTrack).join(Release).switch(Track).join(Artist).switch(Track).join(TrackGenre).join(Genre)
        self.assertSelect(multiple_first, 'track."id", track."artist_id"', [])
        self.assertJoins(multiple_first, [
            'INNER JOIN "artist" AS artist ON (track."artist_id" = artist."id")',
            'INNER JOIN "genre" AS genre ON (trackgenre."genre_id" = genre."id")',
            'INNER JOIN "release" AS release ON (releasetrack."release_id" = release."id")',
            'INNER JOIN "releasetrack" AS releasetrack ON (track."id" = releasetrack."track_id")',
            'INNER JOIN "trackgenre" AS trackgenre ON (track."id" = trackgenre."track_id")',
        ])

        single_first = Track.select().join(Artist).switch(Track).join(ReleaseTrack).join(Release).switch(Track).join(TrackGenre).join(Genre)
        self.assertSelect(single_first, 'track."id", track."artist_id"', [])
        self.assertJoins(single_first, [
            'INNER JOIN "artist" AS artist ON (track."artist_id" = artist."id")',
            'INNER JOIN "genre" AS genre ON (trackgenre."genre_id" = genre."id")',
            'INNER JOIN "release" AS release ON (releasetrack."release_id" = release."id")',
            'INNER JOIN "releasetrack" AS releasetrack ON (track."id" = releasetrack."track_id")',
            'INNER JOIN "trackgenre" AS trackgenre ON (track."id" = trackgenre."track_id")',
        ])

    def test_joining_expr(self):
        class A(TestModel):
            uniq_a = CharField(primary_key=True)
        class B(TestModel):
            uniq_ab = CharField(primary_key=True)
            uniq_b = CharField()
        class C(TestModel):
            uniq_bc = CharField(primary_key=True)
        sq = A.select(A, B, C).join(
            B, on=(A.uniq_a == B.uniq_ab)
        ).join(
            C, on=(B.uniq_b == C.uniq_bc)
        )
        self.assertSelect(sq, 'a."uniq_a", b."uniq_ab", b."uniq_b", c."uniq_bc"', [])
        self.assertJoins(sq, [
            'INNER JOIN "b" AS b ON (a."uniq_a" = b."uniq_ab")',
            'INNER JOIN "c" AS c ON (b."uniq_b" = c."uniq_bc")',
        ])

    def test_where(self):
        sq = SelectQuery(User).where(User.id < 5)
        self.assertWhere(sq, '(users."id" < ?)', [5])

        sq = SelectQuery(Blog).where(Blog.user << sq)
        self.assertWhere(sq, '(blog."user_id" IN (SELECT users."id" FROM "users" AS users WHERE (users."id" < ?)))', [5])

        p = SelectQuery(Package).where(Package.id == 2)
        sq = SelectQuery(PackageItem).where(PackageItem.package << p)
        self.assertWhere(sq, '(packageitem."package_id" IN (SELECT package."barcode" FROM "package" AS package WHERE (package."id" = ?)))', [2])

    def test_fix_null(self):
        sq = SelectQuery(Blog).where(Blog.user == None)
        self.assertWhere(sq, '(blog."user_id" IS ?)', [None])

        sq = SelectQuery(Blog).where(Blog.user != None)
        self.assertWhere(sq, 'NOT (blog."user_id" IS ?)', [None])

    def test_where_coercion(self):
        sq = SelectQuery(User).where(User.id < '5')
        self.assertWhere(sq, '(users."id" < ?)', [5])

        sq = SelectQuery(User).where(User.id < (User.id - '5'))
        self.assertWhere(sq, '(users."id" < (users."id" - ?))', [5])

    def test_where_lists(self):
        sq = SelectQuery(User).where(User.username << ['u1', 'u2'])
        self.assertWhere(sq, '(users."username" IN (?, ?))', ['u1', 'u2'])

        sq = SelectQuery(User).where((User.username << ['u1', 'u2']) | (User.username << ['u3', 'u4']))
        self.assertWhere(sq, '((users."username" IN (?, ?)) OR (users."username" IN (?, ?)))', ['u1', 'u2', 'u3', 'u4'])

    def test_where_joins(self):
        sq = SelectQuery(User).where(
            ((User.id == 1) | (User.id == 2)) &
            ((Blog.pk == 3) | (Blog.pk == 4))
        ).where(User.id == 5).join(Blog)
        self.assertWhere(sq, '((((users."id" = ?) OR (users."id" = ?)) AND ((blog."pk" = ?) OR (blog."pk" = ?))) AND (users."id" = ?))', [1, 2, 3, 4, 5])

    def test_where_join_non_pk_fk(self):
        sq = (SelectQuery(Package)
              .join(PackageItem)
              .where(PackageItem.title == 'p1'))
        self.assertWhere(sq, '(packageitem."title" = ?)', ['p1'])

        sq = (SelectQuery(PackageItem)
              .join(Package)
              .where(Package.barcode == 'b1'))
        self.assertWhere(sq, '(package."barcode" = ?)', ['b1'])

    def test_where_functions(self):
        sq = SelectQuery(User).where(fn.Lower(fn.Substr(User.username, 0, 1)) == 'a')
        self.assertWhere(sq, '(Lower(Substr(users."username", ?, ?)) = ?)', [0, 1, 'a'])

    def test_where_conversion(self):
        sq = SelectQuery(CSVRow).where(CSVRow.data == Param(['foo', 'bar']))
        self.assertWhere(sq, '(csvrow."data" = ?)', ['foo,bar'])

        sq = SelectQuery(CSVRow).where(
            CSVRow.data == fn.FOO(Param(['foo', 'bar'])))
        self.assertWhere(sq, '(csvrow."data" = FOO(?))', ['foo,bar'])

        sq = SelectQuery(CSVRow).where(
            CSVRow.data == fn.FOO(Param(['foo', 'bar'])).coerce(False))
        self.assertWhere(sq, '(csvrow."data" = FOO(?))', [['foo', 'bar']])

    def test_where_clauses(self):
        sq = SelectQuery(Blog).where(
            Blog.pub_date < (fn.NOW() - SQL('INTERVAL 1 HOUR')))
        self.assertWhere(sq, '(blog."pub_date" < (NOW() - INTERVAL 1 HOUR))', [])

    def test_where_r(self):
        sq = SelectQuery(Blog).where(Blog.pub_date < R('NOW() - INTERVAL 1 HOUR'))
        self.assertWhere(sq, '(blog."pub_date" < NOW() - INTERVAL 1 HOUR)', [])

        sq = SelectQuery(Blog).where(Blog.pub_date < (fn.Now() - R('INTERVAL 1 HOUR')))
        self.assertWhere(sq, '(blog."pub_date" < (Now() - INTERVAL 1 HOUR))', [])

    def test_where_subqueries(self):
        sq = SelectQuery(User).where(User.id << User.select().where(User.username=='u1'))
        self.assertWhere(sq, '(users."id" IN (SELECT users."id" FROM "users" AS users WHERE (users."username" = ?)))', ['u1'])

        sq = SelectQuery(User).where(User.username << User.select(User.username).where(User.username=='u1'))
        self.assertWhere(sq, '(users."username" IN (SELECT users."username" FROM "users" AS users WHERE (users."username" = ?)))', ['u1'])

        sq = SelectQuery(Blog).where((Blog.pk == 3) | (Blog.user << User.select().where(User.username << ['u1', 'u2'])))
        self.assertWhere(sq, '((blog."pk" = ?) OR (blog."user_id" IN (SELECT users."id" FROM "users" AS users WHERE (users."username" IN (?, ?)))))', [3, 'u1', 'u2'])

    def test_where_fk(self):
        sq = SelectQuery(Blog).where(Blog.user == User(id=100))
        self.assertWhere(sq, '(blog."user_id" = ?)', [100])

        sq = SelectQuery(Blog).where(Blog.user << [User(id=100), User(id=101)])
        self.assertWhere(sq, '(blog."user_id" IN (?, ?))', [100, 101])

        sq = SelectQuery(PackageItem).where(PackageItem.package == Package(barcode='b1'))
        self.assertWhere(sq, '(packageitem."package_id" = ?)', ['b1'])

    def test_where_negation(self):
        sq = SelectQuery(Blog).where(~(Blog.title == 'foo'))
        self.assertWhere(sq, 'NOT (blog."title" = ?)', ['foo'])

        sq = SelectQuery(Blog).where(~((Blog.title == 'foo') | (Blog.title == 'bar')))
        self.assertWhere(sq, 'NOT ((blog."title" = ?) OR (blog."title" = ?))', ['foo', 'bar'])

        sq = SelectQuery(Blog).where(~((Blog.title == 'foo') & (Blog.title == 'bar')) & (Blog.title == 'baz'))
        self.assertWhere(sq, '(NOT ((blog."title" = ?) AND (blog."title" = ?)) AND (blog."title" = ?))', ['foo', 'bar', 'baz'])

        sq = SelectQuery(Blog).where(~((Blog.title == 'foo') & (Blog.title == 'bar')) & ((Blog.title == 'baz') & (Blog.title == 'fizz')))
        self.assertWhere(sq, '(NOT ((blog."title" = ?) AND (blog."title" = ?)) AND ((blog."title" = ?) AND (blog."title" = ?)))', ['foo', 'bar', 'baz', 'fizz'])

    def test_where_chaining_collapsing(self):
        sq = SelectQuery(User).where(User.id == 1).where(User.id == 2).where(User.id == 3)
        self.assertWhere(sq, '(((users."id" = ?) AND (users."id" = ?)) AND (users."id" = ?))', [1, 2, 3])

        sq = SelectQuery(User).where((User.id == 1) & (User.id == 2)).where(User.id == 3)
        self.assertWhere(sq, '(((users."id" = ?) AND (users."id" = ?)) AND (users."id" = ?))', [1, 2, 3])

        sq = SelectQuery(User).where((User.id == 1) | (User.id == 2)).where(User.id == 3)
        self.assertWhere(sq, '(((users."id" = ?) OR (users."id" = ?)) AND (users."id" = ?))', [1, 2, 3])

        sq = SelectQuery(User).where(User.id == 1).where((User.id == 2) & (User.id == 3))
        self.assertWhere(sq, '((users."id" = ?) AND ((users."id" = ?) AND (users."id" = ?)))', [1, 2, 3])

        sq = SelectQuery(User).where(User.id == 1).where((User.id == 2) | (User.id == 3))
        self.assertWhere(sq, '((users."id" = ?) AND ((users."id" = ?) OR (users."id" = ?)))', [1, 2, 3])

        sq = SelectQuery(User).where(~(User.id == 1)).where(User.id == 2).where(~(User.id == 3))
        self.assertWhere(sq, '((NOT (users."id" = ?) AND (users."id" = ?)) AND NOT (users."id" = ?))', [1, 2, 3])

    def test_grouping(self):
        sq = SelectQuery(User).group_by(User.id)
        self.assertGroupBy(sq, 'users."id"', [])

        sq = SelectQuery(User).group_by(User)
        self.assertGroupBy(sq, 'users."id", users."username"', [])

    def test_having(self):
        sq = SelectQuery(User, fn.Count(Blog.pk)).join(Blog).group_by(User).having(
            fn.Count(Blog.pk) > 2
        )
        self.assertHaving(sq, '(Count(blog."pk") > ?)', [2])

        sq = SelectQuery(User, fn.Count(Blog.pk)).join(Blog).group_by(User).having(
            (fn.Count(Blog.pk) > 10) | (fn.Count(Blog.pk) < 2)
        )
        self.assertHaving(sq, '((Count(blog."pk") > ?) OR (Count(blog."pk") < ?))', [10, 2])

    def test_ordering(self):
        sq = SelectQuery(User).join(Blog).order_by(Blog.title)
        self.assertOrderBy(sq, 'blog."title"', [])

        sq = SelectQuery(User).join(Blog).order_by(Blog.title.asc())
        self.assertOrderBy(sq, 'blog."title" ASC', [])

        sq = SelectQuery(User).join(Blog).order_by(Blog.title.desc())
        self.assertOrderBy(sq, 'blog."title" DESC', [])

        sq = SelectQuery(User).join(Blog).order_by(User.username.desc(), Blog.title.asc())
        self.assertOrderBy(sq, 'users."username" DESC, blog."title" ASC', [])

        base_sq = SelectQuery(User, User.username, fn.Count(Blog.pk).alias('count')).join(Blog).group_by(User.username)
        sq = base_sq.order_by(fn.Count(Blog.pk).desc())
        self.assertOrderBy(sq, 'Count(blog."pk") DESC', [])

        sq = base_sq.order_by(R('count'))
        self.assertOrderBy(sq, 'count', [])

        sq = OrderedModel.select()
        self.assertOrderBy(sq, 'orderedmodel."created" DESC', [])

        sq = OrderedModel.select().order_by(OrderedModel.id.asc())
        self.assertOrderBy(sq, 'orderedmodel."id" ASC', [])

        sq = User.select().order_by(User.id * 5)
        self.assertOrderBy(sq, '(users."id" * ?)', [5])
        sql = compiler.generate_select(sq)
        self.assertEqual(sql, (
            'SELECT users."id", users."username" '
            'FROM "users" AS users ORDER BY (users."id" * ?)',
            [5]))

    def test_from_subquery(self):
        # e.g. annotate the number of blogs per user, then annotate the number
        # of users with that number of blogs.
        inner = (Blog
                 .select(fn.COUNT(Blog.id).alias('blog_ct'))
                 .group_by(Blog.user))
        blog_ct = SQL('blog_ct')
        outer = (Blog
                 .select(blog_ct, fn.COUNT(blog_ct).alias('blog_ct_n'))
                 .from_(inner)
                 .group_by(blog_ct))
        sql, params = compiler.generate_select(outer)
        self.assertEqual(sql, (
            'SELECT blog_ct, COUNT(blog_ct) AS blog_ct_n '
            'FROM ('
            'SELECT COUNT("id") AS blog_ct FROM "blog" AS blog '
            'GROUP BY blog."user_id") '
            'GROUP BY blog_ct'))

    def test_from_multiple(self):
        q = (User
             .select()
             .from_(User, Blog)
             .where(Blog.user == User.id))

        sql, params = compiler.generate_select(q)
        self.assertEqual(sql, (
            'SELECT users."id", users."username" '
            'FROM "users" AS users, "blog" AS blog '
            'WHERE (blog."user_id" = users."id")'))

        q = (User
             .select()
             .from_(User, Blog, Comment)
             .where(
                 (Blog.user == User.id) &
                 (Comment.blog == Blog.pk)))

        sql, params = compiler.generate_select(q)
        self.assertEqual(sql, (
            'SELECT users."id", users."username" '
            'FROM "users" AS users, "blog" AS blog, "comment" AS comment '
            'WHERE ((blog."user_id" = users."id") AND '
            '(comment."blog_id" = blog."pk"))'))

    def test_paginate(self):
        sq = SelectQuery(User).paginate(1, 20)
        self.assertEqual(sq._limit, 20)
        self.assertEqual(sq._offset, 0)

        sq = SelectQuery(User).paginate(3, 30)
        self.assertEqual(sq._limit, 30)
        self.assertEqual(sq._offset, 60)

    def test_prefetch_subquery(self):
        sq = SelectQuery(User).where(User.username == 'foo')
        sq2 = SelectQuery(Blog).where(Blog.title == 'bar')
        sq3 = SelectQuery(Comment).where(Comment.comment == 'baz')
        fixed = prefetch_add_subquery(sq, (sq2, sq3))
        fixed_sql = [
            ('SELECT t1."id", t1."username" FROM "users" AS t1 WHERE (t1."username" = ?)', ['foo']),
            ('SELECT t1."pk", t1."user_id", t1."title", t1."content", t1."pub_date" FROM "blog" AS t1 WHERE ((t1."title" = ?) AND (t1."user_id" IN (SELECT t2."id" FROM "users" AS t2 WHERE (t2."username" = ?))))', ['bar', 'foo']),
            ('SELECT t1."id", t1."blog_id", t1."comment" FROM "comment" AS t1 WHERE ((t1."comment" = ?) AND (t1."blog_id" IN (SELECT t2."pk" FROM "blog" AS t2 WHERE ((t2."title" = ?) AND (t2."user_id" IN (SELECT t3."id" FROM "users" AS t3 WHERE (t3."username" = ?)))))))', ['baz', 'bar', 'foo']),
        ]
        for (query, fkf), expected in zip(fixed, fixed_sql):
            self.assertEqual(normal_compiler.generate_select(query), expected)

        fixed = prefetch_add_subquery(sq, (Blog,))
        fixed_sql = [
            ('SELECT t1."id", t1."username" FROM "users" AS t1 WHERE (t1."username" = ?)', ['foo']),
            ('SELECT t1."pk", t1."user_id", t1."title", t1."content", t1."pub_date" FROM "blog" AS t1 WHERE (t1."user_id" IN (SELECT t2."id" FROM "users" AS t2 WHERE (t2."username" = ?)))', ['foo']),
        ]
        for (query, fkf), expected in zip(fixed, fixed_sql):
            self.assertEqual(normal_compiler.generate_select(query), expected)

    def test_prefetch_non_pk_fk(self):
        sq = SelectQuery(Package).where(Package.barcode % 'b%')
        sq2 = SelectQuery(PackageItem).where(PackageItem.title % 'n%')
        fixed = prefetch_add_subquery(sq, (sq2,))
        fixed_sq = (
            'SELECT t1."id", t1."barcode" FROM "package" AS t1 '
            'WHERE (t1."barcode" LIKE ?)',
            ['b%'])
        fixed_sq2 = (
            'SELECT t1."id", t1."title", t1."package_id" '
            'FROM "packageitem" AS t1 '
            'WHERE ('
            '(t1."title" LIKE ?) AND '
            '(t1."package_id" IN ('
            'SELECT t2."barcode" FROM "package" AS t2 '
            'WHERE (t2."barcode" LIKE ?))))',
            ['n%', 'b%'])
        fixed_sql = [fixed_sq, fixed_sq2]

        for (query, fkf), expected in zip(fixed, fixed_sql):
            self.assertEqual(normal_compiler.generate_select(query), expected)

    def test_prefetch_subquery_same_depth(self):
        sq = Parent.select()
        sq2 = Child.select()
        sq3 = Orphan.select()
        sq4 = ChildPet.select()
        sq5 = OrphanPet.select()
        fixed = prefetch_add_subquery(sq, (sq2, sq3, sq4, sq5))
        fixed_sql = [
            ('SELECT t1."id", t1."data" FROM "parent" AS t1', []),
            ('SELECT t1."id", t1."parent_id", t1."data" FROM "child" AS t1 WHERE (t1."parent_id" IN (SELECT t2."id" FROM "parent" AS t2))', []),
            ('SELECT t1."id", t1."parent_id", t1."data" FROM "orphan" AS t1 WHERE (t1."parent_id" IN (SELECT t2."id" FROM "parent" AS t2))', []),
            ('SELECT t1."id", t1."child_id", t1."data" FROM "childpet" AS t1 WHERE (t1."child_id" IN (SELECT t2."id" FROM "child" AS t2 WHERE (t2."parent_id" IN (SELECT t3."id" FROM "parent" AS t3))))', []),
            ('SELECT t1."id", t1."orphan_id", t1."data" FROM "orphanpet" AS t1 WHERE (t1."orphan_id" IN (SELECT t2."id" FROM "orphan" AS t2 WHERE (t2."parent_id" IN (SELECT t3."id" FROM "parent" AS t3))))', []),
        ]
        for (query, fkf), expected in zip(fixed, fixed_sql):
            self.assertEqual(normal_compiler.generate_select(query), expected)

    def test_outer_inner_alias(self):
        expected = 'SELECT t1."id", t1."username", (SELECT Sum(t2."id") FROM "users" AS t2 WHERE (t2."id" = t1."id")) AS xxx FROM "users" AS t1'
        UA = User.alias()
        inner = SelectQuery(UA, fn.Sum(UA.id)).where(UA.id == User.id)
        query = User.select(User, inner.alias('xxx'))
        sql, _ = normal_compiler.generate_select(query)
        self.assertEqual(sql, expected)

        # Ensure that ModelAlias.select() does the right thing.
        inner = UA.select(fn.Sum(UA.id)).where(UA.id == User.id)
        query = User.select(User, inner.alias('xxx'))
        sql, _ = normal_compiler.generate_select(query)
        self.assertEqual(sql, expected)

class UpdateTestCase(BasePeeweeTestCase):
    def test_update(self):
        uq = UpdateQuery(User, {User.username: 'updated'})
        self.assertEqual(compiler.generate_update(uq), (
            'UPDATE "users" SET "username" = ?',
            ['updated']))

        uq = UpdateQuery(Blog, {Blog.user: User(id=100, username='foo')})
        self.assertEqual(compiler.generate_update(uq), (
            'UPDATE "blog" SET "user_id" = ?',
            [100]))

        uq = UpdateQuery(User, {User.id: User.id + 5})
        self.assertEqual(compiler.generate_update(uq), (
            'UPDATE "users" SET "id" = ("id" + ?)',
            [5]))

        uq = UpdateQuery(User, {User.id: 5 * (3 + User.id)})
        self.assertEqual(compiler.generate_update(uq), (
            'UPDATE "users" SET "id" = (? * (? + "id"))',
            [5, 3]))

        # set username to the maximum id of all users -- silly, yes, but lets see what happens
        uq = UpdateQuery(User, {User.username: User.select(fn.Max(User.id).alias('maxid'))})
        self.assertEqual(compiler.generate_update(uq), (
            'UPDATE "users" SET "username" = (SELECT Max(users."id") AS maxid '
            'FROM "users" AS users)',
            []))

        uq = UpdateQuery(Blog, {Blog.title: 'foo', Blog.content: 'bar'})
        self.assertEqual(compiler.generate_update(uq), (
            'UPDATE "blog" SET "title" = ?, "content" = ?',
            ['foo', 'bar']))

        pub_date = datetime.datetime(2014, 1, 2, 3, 4)
        uq = UpdateQuery(Blog, {
            Blog.title: 'foo',
            Blog.pub_date: pub_date,
            Blog.user: User(id=15),
            Blog.content: 'bar'})
        self.assertEqual(compiler.generate_update(uq), (
            'UPDATE "blog" SET '
            '"user_id" = ?, "title" = ?, "content" = ?, "pub_date" = ?',
            [15, 'foo', 'bar', pub_date]))

    def test_update_special(self):
        uq = UpdateQuery(CSVRow, {CSVRow.data: ['foo', 'bar', 'baz']})
        self.assertEqual(compiler.generate_update(uq), (
            'UPDATE "csvrow" SET "data" = ?',
            ['foo,bar,baz']))

        uq = UpdateQuery(CSVRow, {CSVRow.data: []})
        self.assertEqual(compiler.generate_update(uq), (
            'UPDATE "csvrow" SET "data" = ?',
            ['']))

    def test_where(self):
        uq = UpdateQuery(User, {User.username: 'updated'}).where(User.id == 2)
        self.assertWhere(uq, '(users."id" = ?)', [2])

        uq = (UpdateQuery(User, {User.username: 'updated'})
              .where(User.id == 2)
              .where(User.username == 'old'))
        self.assertWhere(uq, '((users."id" = ?) AND (users."username" = ?))', [2, 'old'])

class InsertTestCase(BasePeeweeTestCase):
    def test_insert(self):
        iq = InsertQuery(User, {User.username: 'inserted'})
        self.assertEqual(compiler.generate_insert(iq), (
            'INSERT INTO "users" ("username") VALUES (?)',
            ['inserted']))

        iq = InsertQuery(User, {'username': 'inserted'})
        self.assertEqual(compiler.generate_insert(iq), (
            'INSERT INTO "users" ("username") VALUES (?)',
            ['inserted']))

        pub_date = datetime.datetime(2014, 1, 2, 3, 4)
        iq = InsertQuery(Blog, {
            Blog.title: 'foo',
            Blog.content: 'bar',
            Blog.pub_date: pub_date,
            Blog.user: User(id=10)})
        self.assertEqual(compiler.generate_insert(iq), (
            'INSERT INTO "blog" ("user_id", "title", "content", "pub_date") '
            'VALUES (?, ?, ?, ?)',
            [10, 'foo', 'bar', pub_date]))

    def test_insert_default_vals(self):
        class DM(TestModel):
            name = CharField(default='peewee')
            value = IntegerField(default=1, null=True)
            other = FloatField()

        iq = InsertQuery(DM)
        self.assertEqual(compiler.generate_insert(iq), (
            'INSERT INTO "dm" ("name", "value") VALUES (?, ?)',
            ['peewee', 1]))

        iq = InsertQuery(DM, {'name': 'herman'})
        self.assertEqual(compiler.generate_insert(iq), (
            'INSERT INTO "dm" ("name", "value") VALUES (?, ?)',
            ['herman', 1]))

        iq = InsertQuery(DM, {'value': None})
        self.assertEqual(compiler.generate_insert(iq), (
            'INSERT INTO "dm" ("name", "value") VALUES (?, ?)',
            ['peewee', None]))

        iq = InsertQuery(DM, {DM.name: 'huey', 'other': 2.0})
        self.assertEqual(compiler.generate_insert(iq), (
            'INSERT INTO "dm" ("name", "value", "other") VALUES (?, ?, ?)',
            ['huey', 1, 2.0]))

    def test_insert_many(self):
        iq = InsertQuery(User, rows=[
            {'username': 'u1'},
            {User.username: 'u2'},
            {'username': 'u3'},
        ])
        self.assertEqual(compiler.generate_insert(iq), (
            'INSERT INTO "users" ("username") VALUES (?), (?), (?)',
            ['u1', 'u2', 'u3']))

        iq = InsertQuery(User, rows=[{'username': 'u1'}])
        self.assertEqual(compiler.generate_insert(iq), (
            'INSERT INTO "users" ("username") VALUES (?)',
            ['u1']))

        iq = InsertQuery(User, rows=[])
        self.assertEqual(compiler.generate_insert(iq), (
            'INSERT INTO "users"', []))

    def test_insert_many_gen(self):
        def row_generator():
            for i in range(3):
                yield {'username': 'u%s' % i}

        iq = InsertQuery(User, rows=row_generator())
        self.assertEqual(compiler.generate_insert(iq), (
            'INSERT INTO "users" ("username") VALUES (?), (?), (?)',
            ['u0', 'u1', 'u2']))

    def test_insert_special(self):
        iq = InsertQuery(CSVRow, {CSVRow.data: ['foo', 'bar', 'baz']})
        self.assertEqual(compiler.generate_insert(iq), (
            'INSERT INTO "csvrow" ("data") VALUES (?)',
            ['foo,bar,baz']))

        iq = InsertQuery(CSVRow, {CSVRow.data: []})
        self.assertEqual(compiler.generate_insert(iq), (
            'INSERT INTO "csvrow" ("data") VALUES (?)',
            ['']))

        iq = InsertQuery(CSVRow, rows=[
            {CSVRow.data: ['foo', 'bar', 'baz']},
            {CSVRow.data: ['a', 'b']},
            {CSVRow.data: ['b']},
            {CSVRow.data: []}])
        self.assertEqual(compiler.generate_insert(iq), (
            'INSERT INTO "csvrow" ("data") VALUES (?), (?), (?), (?)',
            ['foo,bar,baz', 'a,b', 'b', '']))

    def test_empty_insert(self):
        class EmptyModel(TestModel):
            pass
        iq = InsertQuery(EmptyModel, {})
        sql, params = compiler.generate_insert(iq)
        self.assertEqual(sql, 'INSERT INTO "emptymodel"')

class DeleteTestCase(BasePeeweeTestCase):
    def test_where(self):
        dq = DeleteQuery(User).where(User.id == 2)
        self.assertWhere(dq, '(users."id" = ?)', [2])

        dq = (DeleteQuery(User)
              .where(User.id == 2)
              .where(User.username == 'old'))
        self.assertWhere(dq, '((users."id" = ?) AND (users."username" = ?))', [2, 'old'])

class RawTestCase(BasePeeweeTestCase):
    def test_raw(self):
        q = 'SELECT * FROM "users" WHERE id=?'
        rq = RawQuery(User, q, 100)
        self.assertEqual(rq.sql(), (q, [100]))

class SugarTestCase(BasePeeweeTestCase):
    # test things like filter, annotate, aggregate
    def test_filter(self):
        sq = User.filter(username='u1')
        self.assertJoins(sq, [])
        self.assertWhere(sq, '(users."username" = ?)', ['u1'])

        sq = Blog.filter(user__username='u1')
        self.assertJoins(sq, ['INNER JOIN "users" AS users ON (blog."user_id" = users."id")'])
        self.assertWhere(sq, '(users."username" = ?)', ['u1'])

        sq = Blog.filter(user__username__in=['u1', 'u2'], comments__comment='hurp')
        self.assertJoins(sq, [
            'INNER JOIN "comment" AS comment ON (blog."pk" = comment."blog_id")',
            'INNER JOIN "users" AS users ON (blog."user_id" = users."id")',
        ])
        self.assertWhere(sq, '((comment."comment" = ?) AND (users."username" IN (?, ?)))', ['hurp', 'u1', 'u2'])

        sq = Blog.filter(user__username__in=['u1', 'u2']).filter(comments__comment='hurp')
        self.assertJoins(sq, [
            'INNER JOIN "users" AS users ON (blog."user_id" = users."id")',
            'INNER JOIN "comment" AS comment ON (blog."pk" = comment."blog_id")',
        ])
        self.assertWhere(sq, '((users."username" IN (?, ?)) AND (comment."comment" = ?))', ['u1', 'u2', 'hurp'])

    def test_filter_dq(self):
        sq = User.filter(DQ(username='u1') | DQ(username='u2'))
        self.assertJoins(sq, [])
        self.assertWhere(sq, '((users."username" = ?) OR (users."username" = ?))', ['u1', 'u2'])

        sq = Comment.filter(DQ(blog__user__username='u1') | DQ(blog__title='b1'), DQ(comment='c1'))
        self.assertJoins(sq, [
            'INNER JOIN "blog" AS blog ON (comment."blog_id" = blog."pk")',
            'INNER JOIN "users" AS users ON (blog."user_id" = users."id")',
        ])
        self.assertWhere(sq, '(((users."username" = ?) OR (blog."title" = ?)) AND (comment."comment" = ?))', ['u1', 'b1', 'c1'])

        sq = Blog.filter(DQ(user__username='u1') | DQ(comments__comment='c1'))
        self.assertJoins(sq, [
            'INNER JOIN "comment" AS comment ON (blog."pk" = comment."blog_id")',
            'INNER JOIN "users" AS users ON (blog."user_id" = users."id")',
        ])
        self.assertWhere(sq, '((users."username" = ?) OR (comment."comment" = ?))', ['u1', 'c1'])

        sq = Blog.filter(~DQ(user__username='u1') | DQ(user__username='b2'))
        self.assertJoins(sq, [
            'INNER JOIN "users" AS users ON (blog."user_id" = users."id")',
        ])
        self.assertWhere(sq, '(NOT (users."username" = ?) OR (users."username" = ?))', ['u1', 'b2'])

        sq = Blog.filter(~(
            DQ(user__username='u1') |
            ~DQ(title='b1', pk=3)))
        self.assertJoins(sq, [
            'INNER JOIN "users" AS users ON (blog."user_id" = users."id")',
        ])
        self.assertWhere(sq, 'NOT ((users."username" = ?) OR NOT ((blog."pk" = ?) AND (blog."title" = ?)))', ['u1', 3, 'b1'])

    def test_annotate(self):
        sq = User.select().annotate(Blog)
        self.assertSelect(sq, 'users."id", users."username", Count(blog."pk") AS count', [])
        self.assertJoins(sq, ['INNER JOIN "blog" AS blog ON (users."id" = blog."user_id")'])
        self.assertWhere(sq, '', [])
        self.assertGroupBy(sq, 'users."id", users."username"', [])

        sq = User.select(User.username).annotate(Blog, fn.Sum(Blog.pk).alias('sum')).where(User.username == 'foo')
        self.assertSelect(sq, 'users."username", Sum(blog."pk") AS sum', [])
        self.assertJoins(sq, ['INNER JOIN "blog" AS blog ON (users."id" = blog."user_id")'])
        self.assertWhere(sq, '(users."username" = ?)', ['foo'])
        self.assertGroupBy(sq, 'users."username"', [])

        sq = User.select(User.username).annotate(Blog).annotate(Blog, fn.Max(Blog.pk).alias('mx'))
        self.assertSelect(sq, 'users."username", Count(blog."pk") AS count, Max(blog."pk") AS mx', [])
        self.assertJoins(sq, ['INNER JOIN "blog" AS blog ON (users."id" = blog."user_id")'])
        self.assertWhere(sq, '', [])
        self.assertGroupBy(sq, 'users."username"', [])

        sq = User.select().annotate(Blog).order_by(R('count DESC'))
        self.assertSelect(sq, 'users."id", users."username", Count(blog."pk") AS count', [])
        self.assertOrderBy(sq, 'count DESC', [])

        sq = User.select().join(Blog, JOIN_LEFT_OUTER).switch(User).annotate(Blog)
        self.assertSelect(sq, 'users."id", users."username", Count(blog."pk") AS count', [])
        self.assertJoins(sq, ['LEFT OUTER JOIN "blog" AS blog ON (users."id" = blog."user_id")'])
        self.assertWhere(sq, '', [])
        self.assertGroupBy(sq, 'users."id", users."username"', [])

    def test_aggregate(self):
        sq = User.select().where(User.id < 10)._aggregate()
        self.assertSelect(sq, 'Count(users."id")', [])
        self.assertWhere(sq, '(users."id" < ?)', [10])

        sq = User.select()._aggregate(fn.Sum(User.id).alias('baz'))
        self.assertSelect(sq, 'Sum(users."id") AS baz', [])


class CompilerTestCase(BasePeeweeTestCase):
    def test_clause(self):
        expr = fn.extract(Clause('year', R('FROM'), Blog.pub_date))
        sql, params = compiler.parse_node(expr)
        self.assertEqual(sql, 'extract(? FROM "pub_date")')
        self.assertEqual(params, ['year'])

    def test_custom_alias(self):
        class Person(TestModel):
            name = CharField()

            class Meta:
                table_alias = 'person_tbl'

        class Pet(TestModel):
            name = CharField()
            owner = ForeignKeyField(Person)

            class Meta:
                table_alias = 'pet_tbl'

        sq = Person.select().where(Person.name == 'peewee')
        sql = normal_compiler.generate_select(sq)
        self.assertEqual(
            sql[0],
            'SELECT person_tbl."id", person_tbl."name" FROM "person" AS '
            'person_tbl WHERE (person_tbl."name" = ?)')

        sq = Pet.select(Pet, Person.name).join(Person)
        sql = normal_compiler.generate_select(sq)
        self.assertEqual(
            sql[0],
            'SELECT pet_tbl."id", pet_tbl."name", pet_tbl."owner_id", '
            'person_tbl."name" '
            'FROM "pet" AS pet_tbl '
            'INNER JOIN "person" AS person_tbl '
            'ON (pet_tbl."owner_id" = person_tbl."id")')

    def test_alias_map(self):
        class A(TestModel):
            a = CharField()
            class Meta:
                table_alias = 'a_tbl'
        class B(TestModel):
            b = CharField()
            a_link = ForeignKeyField(A)
        class C(TestModel):
            c = CharField()
            b_link = ForeignKeyField(B)
        class D(TestModel):
            d = CharField()
            c_link = ForeignKeyField(C)
            class Meta:
                table_alias = 'd_tbl'

        sq = (D
              .select(D.d, C.c)
              .join(C)
              .where(C.b_link << (
                  B.select(B.id).join(A).where(A.a == 'a'))))
        sql, params = normal_compiler.generate_select(sq)
        self.assertEqual(sql, (
            'SELECT d_tbl."d", t2."c" '
            'FROM "d" AS d_tbl '
            'INNER JOIN "c" AS t2 ON (d_tbl."c_link_id" = t2."id") '
            'WHERE (t2."b_link_id" IN ('
            'SELECT t3."id" FROM "b" AS t3 '
            'INNER JOIN "a" AS a_tbl ON (t3."a_link_id" = a_tbl."id") '
            'WHERE (a_tbl."a" = ?)))'))

    def test_fn_no_coerce(self):
        class A(TestModel):
            i = IntegerField()
            d = DateTimeField()

        query = A.select(A.id).where(A.d == '2013-01-02')
        sql, params = compiler.generate_select(query)
        self.assertEqual(sql, (
            'SELECT a."id" FROM "a" AS a WHERE (a."d" = ?)'))
        self.assertEqual(params, ['2013-01-02'])

        query = A.select(A.id).where(A.i == fn.Foo('test'))
        self.assertRaises(ValueError, query.sql)

        query = A.select(A.id).where(A.i == fn.Foo('test').coerce(False))
        sql, params = compiler.generate_select(query)
        self.assertEqual(sql, (
            'SELECT a."id" FROM "a" AS a WHERE (a."i" = Foo(?))'))
        self.assertEqual(params, ['test'])


class ValidationTestCase(BasePeeweeTestCase):
    def test_foreign_key_validation(self):
        def declare_bad(val):
            class Bad(TestModel):
                name = ForeignKeyField(val)

        vals_to_try = [
            ForeignKeyField(User),
            'Self',
            object,
            object()]

        for val in vals_to_try:
            self.assertRaises(TypeError, declare_bad, val)


class ProxyTestCase(BasePeeweeTestCase):
    def test_proxy(self):
        class A(object):
            def foo(self):
                return 'foo'

        a = Proxy()
        def raise_error():
            a.foo()
        self.assertRaises(AttributeError, raise_error)

        a.initialize(A())
        self.assertEqual(a.foo(), 'foo')

    def test_proxy_database(self):
        database_proxy = Proxy()

        class DummyModel(TestModel):
            test_field = CharField()
            class Meta:
                database = database_proxy

        # Un-initialized will raise an AttributeError.
        self.assertRaises(AttributeError, DummyModel.create_table)

        # Initialize the object.
        database_proxy.initialize(SqliteDatabase(':memory:'))

        # Do some queries, verify it is working.
        DummyModel.create_table()
        DummyModel.create(test_field='foo')
        self.assertEqual(DummyModel.get().test_field, 'foo')
        DummyModel.drop_table()

#
# TEST CASE USED TO PROVIDE ACCESS TO DATABASE
# FOR EXECUTION OF "LIVE" QUERIES
#

class ModelTestCase(BasePeeweeTestCase):
    requires = None

    def setUp(self):
        super(ModelTestCase, self).setUp()
        drop_tables(self.requires)
        create_tables(self.requires)

    def tearDown(self):
        drop_tables(self.requires)

    def create_user(self, username):
        return User.create(username=username)

    def create_users(self, n):
        for i in range(n):
            self.create_user('u%d' % (i + 1))


class QueryResultWrapperTestCase(ModelTestCase):
    requires = [User, Blog, Comment]

    def test_iteration(self):
        self.create_users(10)
        query_start = len(self.queries())
        sq = User.select()
        qr = sq.execute()

        first_five = []
        for i, u in enumerate(qr):
            first_five.append(u.username)
            if i == 4:
                break
        self.assertEqual(first_five, ['u1', 'u2', 'u3', 'u4', 'u5'])

        another_iter = [u.username for u in qr]
        self.assertEqual(another_iter, ['u%d' % i for i in range(1, 11)])

        another_iter = [u.username for u in qr]
        self.assertEqual(another_iter, ['u%d' % i for i in range(1, 11)])

        # only 1 query for these iterations
        self.assertEqual(len(self.queries()) - query_start, 1)

    def test_iterator(self):
        self.create_users(10)
        qc = len(self.queries())

        qr = User.select().execute()
        usernames = [u.username for u in qr.iterator()]
        self.assertEqual(usernames, ['u%d' % i for i in range(1, 11)])

        qc1 = len(self.queries())
        self.assertEqual(qc1 - qc, 1)

        self.assertTrue(qr._populated)
        self.assertEqual(qr._result_cache, [])

        again = [u.username for u in qr]
        self.assertEqual(again, [])
        qc2 = len(self.queries())
        self.assertEqual(qc2 - qc1, 0)

        qr = User.select().where(User.username == 'xxx').execute()
        usernames = [u.username for u in qr.iterator()]
        self.assertEqual(usernames, [])

    def test_iterator_query_method(self):
        self.create_users(10)
        qc = len(self.queries())

        qr = User.select()
        usernames = [u.username for u in qr.iterator()]
        self.assertEqual(usernames, ['u%d' % i for i in range(1, 11)])

        qc1 = len(self.queries())
        self.assertEqual(qc1 - qc, 1)

        again = [u.username for u in qr]
        self.assertEqual(again, [])
        qc2 = len(self.queries())
        self.assertEqual(qc2 - qc1, 0)

    def test_iterator_extended(self):
        self.create_users(10)
        for i in range(1, 4):
            for j in range(i):
                Blog.create(
                    title='blog-%s-%s' % (i, j),
                    user=User.get(User.username == 'u%s' % i))

        qc = len(self.queries())

        qr = (User
              .select(
                  User.username,
                  fn.Count(Blog.pk).alias('ct'))
              .join(Blog)
              .where(User.username << ['u1', 'u2', 'u3'])
              .group_by(User)
              .order_by(User.id)
              .naive())

        accum = []
        for user in qr.iterator():
            accum.append((user.username, user.ct))

        self.assertEqual(accum, [
            ('u1', 1),
            ('u2', 2),
            ('u3', 3)])

        qr = (User
              .select(fn.Count(User.id).alias('ct'))
              .group_by(User.username << ['u1', 'u2', 'u3'])
              .order_by(fn.Count(User.id).desc()))
        accum = []
        for ct, in qr.tuples().iterator():
            accum.append(ct)
        self.assertEqual(accum, [7, 3])

    def test_fill_cache(self):
        def assertUsernames(qr, n):
            self.assertEqual([u.username for u in qr._result_cache], ['u%d' % i for i in range(1, n+1)])

        self.create_users(20)
        qc = len(self.queries())

        qr = User.select().execute()

        qr.fill_cache(5)
        self.assertFalse(qr._populated)
        assertUsernames(qr, 5)

        # a subsequent call will not "over-fill"
        qr.fill_cache(5)
        self.assertFalse(qr._populated)
        assertUsernames(qr, 5)

        # ask for one more and ye shall receive
        qr.fill_cache(6)
        self.assertFalse(qr._populated)
        assertUsernames(qr, 6)

        qr.fill_cache(21)
        self.assertTrue(qr._populated)
        assertUsernames(qr, 20)

        qc2 = len(self.queries())
        self.assertEqual(qc2 - qc, 1)

    def test_select_related(self):
        u1 = User.create(username='u1')
        u2 = User.create(username='u2')
        b1 = Blog.create(user=u1, title='b1')
        b2 = Blog.create(user=u2, title='b2')
        c11 = Comment.create(blog=b1, comment='c11')
        c12 = Comment.create(blog=b1, comment='c12')
        c21 = Comment.create(blog=b2, comment='c21')
        c22 = Comment.create(blog=b2, comment='c22')

        # missing comment.blog_id
        qc = len(self.queries())
        comments = Comment.select(Comment.id, Comment.comment, Blog.pk, Blog.title).join(Blog).where(Blog.title == 'b1').order_by(Comment.id)
        self.assertEqual([c.blog.title for c in comments], ['b1', 'b1'])
        self.assertEqual(len(self.queries()) - qc, 1)

        # missing blog.pk
        qc = len(self.queries())
        comments = Comment.select(Comment.id, Comment.comment, Comment.blog, Blog.title).join(Blog).where(Blog.title == 'b2').order_by(Comment.id)
        self.assertEqual([c.blog.title for c in comments], ['b2', 'b2'])
        self.assertEqual(len(self.queries()) - qc, 1)

        # both but going up 2 levels
        qc = len(self.queries())
        comments = Comment.select(Comment, Blog, User).join(Blog).join(User).where(User.username == 'u1').order_by(Comment.id)
        self.assertEqual([c.comment for c in comments], ['c11', 'c12'])
        self.assertEqual([c.blog.title for c in comments], ['b1', 'b1'])
        self.assertEqual([c.blog.user.username for c in comments], ['u1', 'u1'])
        self.assertEqual(len(self.queries()) - qc, 1)

        self.assertTrue(isinstance(comments._qr, ModelQueryResultWrapper))

        qc = len(self.queries())
        comments = Comment.select().join(Blog).join(User).where(User.username == 'u1').order_by(Comment.id)
        self.assertEqual([c.blog.user.username for c in comments], ['u1', 'u1'])
        self.assertEqual(len(self.queries()) - qc, 5)

        self.assertTrue(isinstance(comments._qr, NaiveQueryResultWrapper))

    def test_naive(self):
        u1 = User.create(username='u1')
        u2 = User.create(username='u2')
        b1 = Blog.create(user=u1, title='b1')
        b2 = Blog.create(user=u2, title='b2')

        users = User.select().naive()
        self.assertEqual([u.username for u in users], ['u1', 'u2'])
        self.assertTrue(isinstance(users._qr, NaiveQueryResultWrapper))

        users = User.select(User, Blog).join(Blog).naive()
        self.assertEqual([u.username for u in users], ['u1', 'u2'])
        self.assertEqual([u.title for u in users], ['b1', 'b2'])

        query = Blog.select(Blog, User).join(User).order_by(Blog.title).naive()
        self.assertEqual(query.get().user, User.get(User.username == 'u1'))

    def test_tuples_dicts(self):
        u1 = User.create(username='u1')
        u2 = User.create(username='u2')
        b1 = Blog.create(user=u1, title='b1')
        b2 = Blog.create(user=u2, title='b2')
        users = User.select().tuples().order_by(User.id)
        self.assertEqual([r for r in users], [
            (u1.id, 'u1'),
            (u2.id, 'u2'),
        ])

        users = User.select().dicts()
        self.assertEqual([r for r in users], [
            {'id': u1.id, 'username': 'u1'},
            {'id': u2.id, 'username': 'u2'},
        ])

        users = User.select(User, Blog).join(Blog).order_by(User.id).tuples()
        self.assertEqual([r for r in users], [
            (u1.id, 'u1', b1.pk, u1.id, 'b1', '', None),
            (u2.id, 'u2', b2.pk, u2.id, 'b2', '', None),
        ])

        users = User.select(User, Blog).join(Blog).order_by(User.id).dicts()
        self.assertEqual([r for r in users], [
            {'id': u1.id, 'username': 'u1', 'pk': b1.pk, 'user': u1.id, 'title': 'b1', 'content': '', 'pub_date': None},
            {'id': u2.id, 'username': 'u2', 'pk': b2.pk, 'user': u2.id, 'title': 'b2', 'content': '', 'pub_date': None},
        ])

    def test_slicing_dicing(self):
        def assertUsernames(users, nums):
            self.assertEqual([u.username for u in users], ['u%d' % i for i in nums])

        self.create_users(10)
        qc = len(self.queries())

        uq = User.select().order_by(User.id)

        for i in range(2):
            res = uq[0]
            self.assertEqual(res.username, 'u1')

        qc2 = len(self.queries())
        self.assertEqual(qc2 - qc, 1)

        for i in range(2):
            res = uq[1]
            self.assertEqual(res.username, 'u2')

        qc2 = len(self.queries())
        self.assertEqual(qc2 - qc, 1)

        for i in range(2):
            res = uq[:3]
            assertUsernames(res, [1, 2, 3])

        qc2 = len(self.queries())
        self.assertEqual(qc2 - qc, 1)

        for i in range(2):
            res = uq[2:5]
            assertUsernames(res, [3, 4, 5])

        qc2 = len(self.queries())
        self.assertEqual(qc2 - qc, 1)

        for i in range(2):
            res = uq[5:]
            assertUsernames(res, [6, 7, 8, 9, 10])

        qc2 = len(self.queries())
        self.assertEqual(qc2 - qc, 1)

        self.assertRaises(IndexError, uq.__getitem__, 10)
        self.assertRaises(ValueError, uq.__getitem__, -1)

        res = uq[10:]
        self.assertEqual(res, [])

    def test_indexing_fill_cache(self):
        def assertUser(query_or_qr, idx):
            self.assertEqual(query_or_qr[idx].username, 'u%d' % (idx + 1))

        self.create_users(10)
        uq = User.select().order_by(User.id)
        qc = len(self.queries())

        # Ensure we can grab the first 5 users and that it only costs 1 query.
        for i in range(5):
            assertUser(uq, i)
        self.assertEqual(len(self.queries()) - qc, 1)

        # Iterate in reverse and ensure only costs 1 query.
        uq = User.select().order_by(User.id)
        for i in reversed(range(10)):
            assertUser(uq, i)
        self.assertEqual(len(self.queries()) - qc, 2)

        # Execute the query and get reference to result wrapper.
        query = User.select().order_by(User.id)
        query.execute()
        qr = query._qr

        # Getting the first user will populate the result cache with 1 obj.
        assertUser(query, 0)
        self.assertEqual(len(qr._result_cache), 1)

        # Getting the last user will fill the cache.
        assertUser(query, 9)
        self.assertEqual(len(qr._result_cache), 10)

    def test_prepared(self):
        for i in range(2):
            u = User.create(username='u%d' % i)
            for j in range(2):
                Blog.create(title='b%d-%d' % (i, j), user=u, content='')

        for u in User.select():
            # check prepared was called
            self.assertEqual(u.foo, u.username)

        for b in Blog.select(Blog, User).join(User):
            # prepared is called for select-related instances
            self.assertEqual(b.foo, b.title)
            self.assertEqual(b.user.foo, b.user.username)


class QueryResultCoerceTestCase(ModelTestCase):
    requires = [User]

    def setUp(self):
        super(QueryResultCoerceTestCase, self).setUp()
        for i in range(3):
            User.create(username='u%d' % i)

    def assertNames(self, query, expected, attr='username'):
        id_field = query.model_class.id
        self.assertEqual(
            [getattr(item, attr) for item in query.order_by(id_field)],
            expected)

    def test_simple_select(self):
        query = UpperUser.select()
        self.assertNames(query, ['U0', 'U1', 'U2'])

        query = User.select()
        self.assertNames(query, ['u0', 'u1', 'u2'])

    def test_with_alias(self):
        # Even when aliased to a different attr, the column is coerced.
        query = UpperUser.select(UpperUser.username.alias('foo'))
        self.assertNames(query, ['U0', 'U1', 'U2'], 'foo')

    def test_scalar(self):
        max_username = (UpperUser
                        .select(fn.Max(UpperUser.username))
                        .scalar(convert=True))
        self.assertEqual(max_username, 'U2')

        max_username = (UpperUser
                        .select(fn.Max(UpperUser.username))
                        .scalar())
        self.assertEqual(max_username, 'u2')

    def test_function(self):
        substr = fn.SubStr(UpperUser.username, 1, 3)

        # Being the first parameter of the function, it meets the special-case
        # criteria.
        query = UpperUser.select(substr.alias('foo'))
        self.assertNames(query, ['U0', 'U1', 'U2'], 'foo')

        query = UpperUser.select(substr.coerce(False).alias('foo'))
        self.assertNames(query, ['u0', 'u1', 'u2'], 'foo')

        query = UpperUser.select(substr.coerce(False).alias('username'))
        self.assertNames(query, ['u0', 'u1', 'u2'])

        query = UpperUser.select(fn.Lower(UpperUser.username).alias('username'))
        self.assertNames(query, ['U0', 'U1', 'U2'])

        query = UpperUser.select(
            fn.Lower(UpperUser.username).alias('username').coerce(False))
        self.assertNames(query, ['u0', 'u1', 'u2'])

        # Since it is aliased to an existing column, we will use that column's
        # coerce.
        query = UpperUser.select(
            fn.SubStr(fn.Lower(UpperUser.username), 1, 3).alias('username'))
        self.assertNames(query, ['U0', 'U1', 'U2'])

        query = UpperUser.select(
            fn.SubStr(fn.Lower(UpperUser.username), 1, 3).alias('foo'))
        self.assertNames(query, ['u0', 'u1', 'u2'], 'foo')

class ModelQueryResultWrapperTestCase(ModelTestCase):
    requires = [TestModelA, TestModelB, TestModelC, User, Blog]

    data = (
        (TestModelA, (
            ('pk1', 'a1'),
            ('pk2', 'a2'),
            ('pk3', 'a3'))),
        (TestModelB, (
            ('pk1', 'b1'),
            ('pk2', 'b2'),
            ('pk3', 'b3'))),
        (TestModelC, (
            ('pk1', 'c1'),
            ('pk2', 'c2'))),
    )

    def setUp(self):
        super(ModelQueryResultWrapperTestCase, self).setUp()
        for model_class, model_data in self.data:
            for pk, data in model_data:
                model_class.create(field=pk, data=data)

    def test_join_expr(self):
        def get_query(join_type=JOIN_INNER):
            sq = (TestModelA
                  .select(TestModelA, TestModelB, TestModelC)
                  .join(
                      TestModelB,
                      on=(TestModelA.field == TestModelB.field).alias('rel_b'))
                  .join(
                      TestModelC,
                      join_type=join_type,
                      on=(TestModelB.field == TestModelC.field))
                  .order_by(TestModelA.field))
            return sq

        sq = get_query()
        self.assertEqual(sq.count(), 2)

        results = list(sq)
        expected = (('b1', 'c1'), ('b2', 'c2'))
        for i, (b_data, c_data) in enumerate(expected):
            self.assertEqual(results[i].rel_b.data, b_data)
            self.assertEqual(results[i].rel_b.field.data, c_data)

        sq = get_query(JOIN_LEFT_OUTER)
        self.assertEqual(sq.count(), 3)

        results = list(sq)
        expected = (('b1', 'c1'), ('b2', 'c2'), ('b3', None))
        for i, (b_data, c_data) in enumerate(expected):
            self.assertEqual(results[i].rel_b.data, b_data)
            self.assertEqual(results[i].rel_b.field.data, c_data)

    def test_backward_join(self):
        u1 = User.create(username='u1')
        u2 = User.create(username='u2')
        for user in (u1, u2):
            Blog.create(title='b-%s' % user.username, user=user)

        # Create an additional blog for user 2.
        Blog.create(title='b-u2-2', user=u2)

        res = (User
               .select(User.username, Blog.title)
               .join(Blog)
               .order_by(User.username.asc(), Blog.title.asc()))
        self.assertEqual([(u.username, u.blog.title) for u in res], [
            ('u1', 'b-u1'),
            ('u2', 'b-u2'),
            ('u2', 'b-u2-2')])

class SelectRelatedNonPKFKTestCase(ModelTestCase):
    requires = [Package, PackageItem]

    def test_select_related(self):
        p1 = Package.create(barcode='101')
        p2 = Package.create(barcode='102')
        pi11 = PackageItem.create(title='p11', package='101')
        pi12 = PackageItem.create(title='p12', package='101')
        pi21 = PackageItem.create(title='p21', package='102')
        pi22 = PackageItem.create(title='p22', package='102')

        # missing PackageItem.package_id.
        qc = len(self.queries())
        items = (PackageItem
                 .select(PackageItem.id, PackageItem.title, Package.barcode)
                 .join(Package)
                 .where(Package.barcode == '101')
                 .order_by(PackageItem.id))
        self.assertEqual([i.package.barcode for i in items], ['101', '101'])
        self.assertEqual(len(self.queries()) - qc, 1)

        qc = len(self.queries())
        items = (PackageItem
                 .select(PackageItem.id, PackageItem.title, PackageItem.package, Package.id)
                 .join(Package)
                 .where(Package.barcode == '101')
                 .order_by(PackageItem.id))
        self.assertEqual([i.package.id for i in items], [p1.id, p1.id])
        self.assertEqual(len(self.queries()) - qc, 1)

class NonPKFKBasicTestCase(ModelTestCase):
    requires = [Package, PackageItem]

    def setUp(self):
        super(NonPKFKBasicTestCase, self).setUp()

        for barcode in ['101', '102']:
            Package.create(barcode=barcode)
            for i in range(2):
                PackageItem.create(
                    package=barcode,
                    title='%s-%s' % (barcode, i))

    def test_fk_resolution(self):
        pi = PackageItem.get(PackageItem.title == '101-0')
        self.assertEqual(pi._data['package'], '101')
        self.assertEqual(pi.package, Package.get(Package.barcode == '101'))

    def test_select_generation(self):
        p = Package.get(Package.barcode == '101')
        self.assertEqual(
            [item.title for item in p.items.order_by(PackageItem.id)],
            ['101-0', '101-1'])

class ModelQueryTestCase(ModelTestCase):
    requires = [User, Blog]

    def setUp(self):
        super(ModelQueryTestCase, self).setUp()
        self._orig_db_insert_many = test_db.insert_many

    def tearDown(self):
        super(ModelQueryTestCase, self).tearDown()
        test_db.insert_many = self._orig_db_insert_many

    def create_users_blogs(self, n=10, nb=5):
        for i in range(n):
            u = User.create(username='u%d' % i)
            for j in range(nb):
                b = Blog.create(title='b-%d-%d' % (i, j), content=str(j), user=u)

    def test_select(self):
        self.create_users_blogs()

        users = User.select().where(User.username << ['u0', 'u5']).order_by(User.username)
        self.assertEqual([u.username for u in users], ['u0', 'u5'])

        blogs = Blog.select().join(User).where(
            (User.username << ['u0', 'u3']) &
            (Blog.content == '4')
        ).order_by(Blog.title)
        self.assertEqual([b.title for b in blogs], ['b-0-4', 'b-3-4'])

        users = User.select().paginate(2, 3)
        self.assertEqual([u.username for u in users], ['u3', 'u4', 'u5'])

    def test_select_subquery(self):
        # 10 users, 5 blogs each
        self.create_users_blogs(5, 3)

        # delete user 2's 2nd blog
        Blog.delete().where(Blog.title == 'b-2-2').execute()

        subquery = Blog.select(fn.Count(Blog.pk)).where(Blog.user == User.id).group_by(Blog.user)
        users = User.select(User, subquery.alias('ct')).order_by(R('ct'), User.id)

        self.assertEqual([(x.username, x.ct) for x in users], [
            ('u2', 2),
            ('u0', 3),
            ('u1', 3),
            ('u3', 3),
            ('u4', 3),
        ])

    def test_scalar(self):
        self.create_users(5)

        users = User.select(fn.Count(User.id)).scalar()
        self.assertEqual(users, 5)

        users = User.select(fn.Count(User.id)).where(User.username << ['u1', 'u2'])
        self.assertEqual(users.scalar(), 2)
        self.assertEqual(users.scalar(True), (2,))

        users = User.select(fn.Count(User.id)).where(User.username == 'not-here')
        self.assertEqual(users.scalar(), 0)
        self.assertEqual(users.scalar(True), (0,))

        users = User.select(fn.Count(User.id), fn.Count(User.username))
        self.assertEqual(users.scalar(), 5)
        self.assertEqual(users.scalar(True), (5, 5))

        User.create(username='u1')
        User.create(username='u2')
        User.create(username='u3')
        User.create(username='u99')
        users = User.select(fn.Count(fn.Distinct(User.username))).scalar()
        self.assertEqual(users, 6)

    def test_update(self):
        self.create_users(5)
        uq = User.update(username='u-edited').where(User.username << ['u1', 'u2', 'u3'])
        self.assertEqual([u.username for u in User.select().order_by(User.id)], ['u1', 'u2', 'u3', 'u4', 'u5'])

        uq.execute()
        self.assertEqual([u.username for u in User.select().order_by(User.id)], ['u-edited', 'u-edited', 'u-edited', 'u4', 'u5'])

        self.assertRaises(KeyError, User.update, doesnotexist='invalid')

    def test_insert(self):
        iq = User.insert(username='u1')
        self.assertEqual(User.select().count(), 0)
        uid = iq.execute()
        self.assertTrue(uid > 0)
        self.assertEqual(User.select().count(), 1)
        u = User.get(User.id==uid)
        self.assertEqual(u.username, 'u1')

        iq = User.insert(doesnotexist='invalid')
        self.assertRaises(KeyError, iq.execute)

    def test_insert_many(self):
        qc = len(self.queries())
        iq = User.insert_many([
            {'username': 'u1'},
            {'username': 'u2'},
            {'username': 'u3'},
            {'username': 'u4'}])
        self.assertTrue(iq.execute())

        qc2 = len(self.queries())
        if test_db.insert_many:
            self.assertEqual(qc2 - qc, 1)
        else:
            self.assertEqual(qc2 - qc, 4)
        self.assertEqual(User.select().count(), 4)

        sq = User.select(User.username).order_by(User.username)
        self.assertEqual([u.username for u in sq], ['u1', 'u2', 'u3', 'u4'])

        iq = User.insert_many([{'username': 'u5'}])
        self.assertTrue(iq.execute())
        self.assertEqual(User.select().count(), 5)

        iq = User.insert_many([
            {User.username: 'u6'},
            {User.username: 'u7'},
            {'username': 'u8'}]).execute()

        sq = User.select(User.username).order_by(User.username)
        self.assertEqual([u.username for u in sq],
                         ['u1', 'u2', 'u3', 'u4', 'u5', 'u6', 'u7', 'u8'])

    def test_insert_many_fallback(self):
        # Simulate database not supporting multiple insert (older versions of
        # sqlite).
        test_db.insert_many = False
        qc = len(self.queries())
        iq = User.insert_many([
            {'username': 'u1'},
            {'username': 'u2'},
            {'username': 'u3'},
            {'username': 'u4'}])
        self.assertTrue(iq.execute())
        qc2 = len(self.queries())
        self.assertEqual(qc2 - qc, 4)
        self.assertEqual(User.select().count(), 4)

    def test_delete(self):
        self.create_users(5)
        dq = User.delete().where(User.username << ['u1', 'u2', 'u3'])
        self.assertEqual(User.select().count(), 5)
        nr = dq.execute()
        self.assertEqual(nr, 3)
        self.assertEqual([u.username for u in User.select()], ['u4', 'u5'])

    def test_raw(self):
        self.create_users(3)

        qc = len(self.queries())
        rq = User.raw('select * from users where username IN (%s,%s)' % (INT,INT), 'u1', 'u3')
        self.assertEqual([u.username for u in rq], ['u1', 'u3'])

        # iterate again
        self.assertEqual([u.username for u in rq], ['u1', 'u3'])
        self.assertEqual(len(self.queries()) - qc, 1)

        rq = User.raw('select id, username, %s as secret from users where username = %s' % (INT,INT), 'sh', 'u2')
        self.assertEqual([u.secret for u in rq], ['sh'])
        self.assertEqual([u.username for u in rq], ['u2'])

        rq = User.raw('select count(id) from users')
        self.assertEqual(rq.scalar(), 3)

        rq = User.raw('select username from users').tuples()
        self.assertEqual([r for r in rq], [
            ('u1',), ('u2',), ('u3',),
        ])

    def test_limits_offsets(self):
        for i in range(10):
            self.create_user(username='u%d' % i)
        sq = User.select().order_by(User.id)

        offset_no_lim = sq.offset(3)
        self.assertEqual(
            [u.username for u in offset_no_lim],
            ['u%d' % i for i in range(3, 10)]
        )

        offset_with_lim = sq.offset(5).limit(3)
        self.assertEqual(
            [u.username for u in offset_with_lim],
            ['u%d' % i for i in range(5, 8)]
        )

    def test_raw_fn(self):
        self.create_users_blogs(3, 2)  # 3 users, 2 blogs each.
        query = User.raw('select count(1) as ct from blog group by user_id')
        results = [x.ct for x in query]
        self.assertEqual(results, [2, 2, 2])


class ModelAPITestCase(ModelTestCase):
    requires = [User, Blog, Category, UserCategory]

    def test_related_name(self):
        u1 = self.create_user('u1')
        u2 = self.create_user('u2')
        b11 = Blog.create(user=u1, title='b11')
        b12 = Blog.create(user=u1, title='b12')
        b2 = Blog.create(user=u2, title='b2')

        self.assertEqual([b.title for b in u1.blog_set], ['b11', 'b12'])
        self.assertEqual([b.title for b in u2.blog_set], ['b2'])

    def test_related_name_collision(self):
        class Foo(TestModel):
            f1 = CharField()

        def make_klass():
            class FooRel(TestModel):
                foo = ForeignKeyField(Foo, related_name='f1')

        self.assertRaises(AttributeError, make_klass)

    def test_fk_exceptions(self):
        c1 = Category.create(name='c1')
        c2 = Category.create(parent=c1, name='c2')
        self.assertEqual(c1.parent, None)
        self.assertEqual(c2.parent, c1)

        c2_db = Category.get(Category.id == c2.id)
        self.assertEqual(c2_db.parent, c1)

        u = self.create_user('u1')
        b = Blog.create(user=u, title='b')
        b2 = Blog(title='b2')

        self.assertEqual(b.user, u)
        self.assertRaises(User.DoesNotExist, getattr, b2, 'user')

    def test_fk_cache_invalidated(self):
        u1 = self.create_user('u1')
        u2 = self.create_user('u2')
        b = Blog.create(user=u1, title='b')

        blog = Blog.get(Blog.pk == b)
        qc = len(self.queries())
        self.assertEqual(blog.user.id, u1.id)
        self.assertEqual(len(self.queries()), qc + 1)

        blog.user = u2.id
        self.assertEqual(blog.user.id, u2.id)
        self.assertEqual(len(self.queries()), qc + 2)

        # No additional query.
        blog.user = u2.id
        self.assertEqual(blog.user.id, u2.id)
        self.assertEqual(len(self.queries()), qc + 2)

    def test_fk_ints(self):
        c1 = Category.create(name='c1')
        c2 = Category.create(name='c2', parent=c1.id)
        c2_db = Category.get(Category.id == c2.id)
        self.assertEqual(c2_db.parent, c1)

    def test_fk_caching(self):
        c1 = Category.create(name='c1')
        c2 = Category.create(name='c2', parent=c1)
        c2_db = Category.get(Category.id == c2.id)
        qc = len(self.queries())

        parent = c2_db.parent
        self.assertEqual(parent, c1)

        parent = c2_db.parent
        self.assertEqual(len(self.queries()) - qc, 1)

    def test_category_select_related_alias(self):
        g1 = Category.create(name='g1')
        g2 = Category.create(name='g2')

        p1 = Category.create(name='p1', parent=g1)
        p2 = Category.create(name='p2', parent=g2)

        c1 = Category.create(name='c1', parent=p1)
        c11 = Category.create(name='c11', parent=p1)
        c2 = Category.create(name='c2', parent=p2)

        qc = len(self.queries())

        Grandparent = Category.alias()
        Parent = Category.alias()
        sq = Category.select(Category, Parent, Grandparent).join(
            Parent, on=(Category.parent == Parent.id)
        ).join(
            Grandparent, on=(Parent.parent == Grandparent.id)
        ).where(
            Grandparent.name == 'g1'
        ).order_by(Category.name)

        self.assertEqual([(c.name, c.parent.name, c.parent.parent.name) for c in sq], [
            ('c1', 'p1', 'g1'),
            ('c11', 'p1', 'g1'),
        ])

        qc2 = len(self.queries())
        self.assertEqual(qc2 - qc, 1)

    def test_creation(self):
        self.create_users(10)
        self.assertEqual(User.select().count(), 10)

    def test_saving(self):
        self.assertEqual(User.select().count(), 0)

        u = User(username='u1')
        self.assertEqual(u.save(), 1)
        u.username = 'u2'
        self.assertEqual(u.save(), 1)

        self.assertEqual(User.select().count(), 1)

        self.assertEqual(u.delete_instance(), 1)
        self.assertEqual(u.save(), 0)

    def test_modify_model_cause_it_dirty(self):
        u = User(username='u1')
        u.save()
        self.assertFalse(u.is_dirty())

        u.username = 'u2'
        self.assertTrue(u.is_dirty())
        self.assertEqual(u.dirty_fields, [User.username])

        u.save()
        self.assertFalse(u.is_dirty())


    def test_save_only(self):
        u = User.create(username='u')
        b = Blog.create(user=u, title='b1', content='ct')
        b.title = 'b1-edit'
        b.content = 'ct-edit'

        b.save(only=[Blog.title])

        b_db = Blog.get(Blog.pk == b.pk)
        self.assertEqual(b_db.title, 'b1-edit')
        self.assertEqual(b_db.content, 'ct')

        b = Blog(user=u, title='b2', content='foo')
        b.save(only=[Blog.user, Blog.title])

        b_db = Blog.get(Blog.pk == b.pk)

        self.assertEqual(b_db.title, 'b2')
        self.assertEqual(b_db.content, '')

    def test_zero_id(self):
        if isinstance(test_db, MySQLDatabase):
            # Need to explicitly tell MySQL it's OK to use zero.
            test_db.execute_sql("SET SESSION sql_mode='NO_AUTO_VALUE_ON_ZERO'")
        query = 'insert into users (id, username) values (%s, %s)' % (
            test_db.interpolation, test_db.interpolation)
        test_db.execute_sql(query, (0, 'foo'))
        Blog.insert(title='foo2', user=0).execute()

        u = User.get(User.id == 0)
        b = Blog.get(Blog.user == u)

        self.assertTrue(u == u)
        self.assertTrue(u == b.user)

    def test_saving_via_create_gh111(self):
        u = User.create(username='u')
        b = Blog.create(title='foo', user=u)
        last_sql, _ = self.queries()[-1]
        self.assertFalse('pub_date' in last_sql)
        self.assertEqual(b.pub_date, None)

        b2 = Blog(title='foo2', user=u)
        b2.save()
        last_sql, _ = self.queries()[-1]
        self.assertFalse('pub_date' in last_sql)
        self.assertEqual(b2.pub_date, None)

    def test_reading(self):
        u1 = self.create_user('u1')
        u2 = self.create_user('u2')

        self.assertEqual(u1, User.get(username='u1'))
        self.assertEqual(u2, User.get(username='u2'))
        self.assertFalse(u1 == u2)

        self.assertEqual(u1, User.get(User.username == 'u1'))
        self.assertEqual(u2, User.get(User.username == 'u2'))

    def test_get_or_create(self):
        u1 = User.get_or_create(username='u1')
        u1_x = User.get_or_create(username='u1')
        self.assertEqual(u1.id, u1_x.id)
        self.assertEqual(User.select().count(), 1)

    def test_first(self):
        users = self.create_users(5)
        qc = len(self.queries())

        sq = User.select().order_by(User.username)
        qr = sq.execute()

        # call it once
        first = sq.first()
        self.assertEqual(first.username, 'u1')

        # check the result cache
        self.assertEqual(len(qr._result_cache), 1)

        # call it again and we get the same result, but not an
        # extra query
        self.assertEqual(sq.first().username, 'u1')

        qc2 = len(self.queries())
        self.assertEqual(qc2 - qc, 1)

        usernames = [u.username for u in sq]
        self.assertEqual(usernames, ['u1', 'u2', 'u3', 'u4', 'u5'])

        qc3 = len(self.queries())
        self.assertEqual(qc3, qc2)

        # call after iterating
        self.assertEqual(sq.first().username, 'u1')

        usernames = [u.username for u in sq]
        self.assertEqual(usernames, ['u1', 'u2', 'u3', 'u4', 'u5'])

        qc3 = len(self.queries())
        self.assertEqual(qc3, qc2)

        # call it with an empty result
        sq = User.select().where(User.username == 'not-here')
        self.assertEqual(sq.first(), None)

    def test_deleting(self):
        u1 = self.create_user('u1')
        u2 = self.create_user('u2')

        self.assertEqual(User.select().count(), 2)
        u1.delete_instance()
        self.assertEqual(User.select().count(), 1)

        self.assertEqual(u2, User.get(User.username=='u2'))

    def test_counting(self):
        u1 = User.create(username='u1')
        u2 = User.create(username='u2')

        for u in [u1, u2]:
            for i in range(5):
                Blog.create(title='b-%s-%s' % (u.username, i), user=u)

        uc = User.select().where(User.username == 'u1').join(Blog).count()
        self.assertEqual(uc, 5)

        uc = User.select().where(User.username == 'u1').join(Blog).distinct().count()
        self.assertEqual(uc, 1)

        self.assertEqual(
            User.select().limit(1).wrapped_count(clear_limit=False), 1)

    def test_ordering(self):
        u1 = User.create(username='u1')
        u2 = User.create(username='u2')
        u3 = User.create(username='u2')
        users = User.select().order_by(User.username.desc(), User.id.desc())
        self.assertEqual([u.get_id() for u in users], [u3.id, u2.id, u1.id])

    def test_count_transaction(self):
        for i in range(10):
            self.create_user(username='u%d' % i)

        with transaction(test_db):
            for user in SelectQuery(User):
                for i in range(20):
                    Blog.create(user=user, title='b-%d-%d' % (user.id, i))

        count = SelectQuery(Blog).count()
        self.assertEqual(count, 200)

    def test_exists(self):
        u1 = User.create(username='u1')
        self.assertTrue(User.select().where(User.username == 'u1').exists())
        self.assertFalse(User.select().where(User.username == 'u2').exists())

    def test_unicode(self):
        # create a unicode literal
        ustr = ulit('Lýðveldið Ísland')
        u = self.create_user(username=ustr)

        # query using the unicode literal
        u_db = User.get(User.username == ustr)

        # the db returns a unicode literal
        self.assertEqual(u_db.username, ustr)

        # delete the user
        self.assertEqual(u.delete_instance(), 1)

        # convert the unicode to a utf8 string
        utf8_str = ustr.encode('utf-8')

        # create using the utf8 string
        u2 = self.create_user(username=utf8_str)

        # query using unicode literal
        u2_db = User.get(User.username == ustr)

        # we get unicode back
        self.assertEqual(u2_db.username, ustr)

    def test_unicode_issue202(self):
        ustr = ulit('M\u00f6rk')
        user = User.create(username=ustr)
        self.assertEqual(user.username, ustr)


class TestMultipleForeignKey(ModelTestCase):
    requires = [Manufacturer, Component, Computer]
    test_values = [
        ['3TB', '16GB', 'i7'],
        ['128GB', '1GB', 'ARM'],
    ]

    def setUp(self):
        super(TestMultipleForeignKey, self).setUp()
        intel = Manufacturer.create(name='Intel')
        amd = Manufacturer.create(name='AMD')
        kingston = Manufacturer.create(name='Kingston')
        for hard_drive, memory, processor in self.test_values:
            c = Computer.create(
                hard_drive=Component.create(name=hard_drive),
                memory=Component.create(name=memory, manufacturer=kingston),
                processor=Component.create(name=processor, manufacturer=intel))

        # The 2nd computer has an AMD processor.
        c.processor.manufacturer = amd
        c.processor.save()

    def test_multi_join(self):
        query_start = len(self.queries())
        HDD = Component.alias()
        HDDMf = Manufacturer.alias()
        Memory = Component.alias()
        MemoryMf = Manufacturer.alias()
        Processor = Component.alias()
        ProcessorMf = Manufacturer.alias()
        query = (Computer
                 .select(
                     Computer,
                     HDD,
                     Memory,
                     Processor,
                     HDDMf,
                     MemoryMf,
                     ProcessorMf)
                 .join(HDD, on=(Computer.hard_drive == HDD.id))
                 .join(
                     HDDMf,
                     JOIN_LEFT_OUTER,
                     on=(HDD.manufacturer == HDDMf.id))
                 .switch(Computer)
                 .join(Memory, on=(Computer.memory == Memory.id))
                 .join(
                     MemoryMf,
                     JOIN_LEFT_OUTER,
                     on=(Memory.manufacturer == MemoryMf.id))
                 .switch(Computer)
                 .join(Processor, on=(Computer.processor == Processor.id))
                 .join(
                     ProcessorMf,
                     JOIN_LEFT_OUTER,
                     on=(Processor.manufacturer == ProcessorMf.id))
                 .order_by(Computer.id))

        vals = []
        manufacturers = []
        for computer in query:
            components = [
                computer.hard_drive,
                computer.memory,
                computer.processor]
            vals.append([component.name for component in components])
            for component in components:
                if component.manufacturer:
                    manufacturers.append(component.manufacturer.name)
                else:
                    manufacturers.append(None)

        self.assertEqual(vals, self.test_values)
        self.assertEqual(manufacturers, [
            None, 'Kingston', 'Intel',
            None, 'Kingston', 'AMD',
        ])
        self.assertEqual(len(self.queries()), query_start + 1)


class ModelAggregateTestCase(ModelTestCase):
    requires = [OrderedModel, User, Blog]

    def create_ordered_models(self):
        return [
            OrderedModel.create(
                title=i, created=datetime.datetime(2013, 1, i + 1))
            for i in range(3)]

    def create_user_blogs(self):
        users = []
        ct = 0
        for i in range(2):
            user = User.create(username='u-%d' % i)
            for j in range(2):
                ct += 1
                Blog.create(
                    user=user,
                    title='b-%d-%d' % (i, j),
                    pub_date=datetime.datetime(2013, 1, ct))
            users.append(user)
        return users

    def test_annotate_int(self):
        users = self.create_user_blogs()
        annotated = User.select().annotate(Blog, fn.Count(Blog.id).alias('ct'))
        for i, user in enumerate(annotated):
            self.assertEqual(user.ct, 2)
            self.assertEqual(user.username, 'u-%d' % i)

    def test_annotate_datetime(self):
        users = self.create_user_blogs()
        annotated = (User
                     .select()
                     .annotate(Blog, fn.Max(Blog.pub_date).alias('max_pub')))
        user_0, user_1 = annotated
        self.assertEqual(user_0.max_pub, datetime.datetime(2013, 1, 2))
        self.assertEqual(user_1.max_pub, datetime.datetime(2013, 1, 4))

    def test_aggregate_int(self):
        models = self.create_ordered_models()
        max_id = OrderedModel.select().aggregate(fn.Max(OrderedModel.id))
        self.assertEqual(max_id, models[-1].id)

    def test_aggregate_datetime(self):
        models = self.create_ordered_models()
        max_created = (OrderedModel
                       .select()
                       .aggregate(fn.Max(OrderedModel.created)))
        self.assertEqual(max_created, models[-1].created)


class FromMultiTableTestCase(ModelTestCase):
    requires = [Blog, Comment, User]

    def setUp(self):
        super(FromMultiTableTestCase, self).setUp()

        for u in range(2):
            user = User.create(username='u%s' % u)
            for i in range(3):
                b = Blog.create(user=user, title='b%s-%s' % (u, i))
                for j in range(i):
                    Comment.create(blog=b, comment='c%s-%s' % (i, j))

    def test_from_multi_table(self):
        q = (Blog
             .select(Blog, User)
             .from_(Blog, User)
             .where(
                 (Blog.user == User.id) &
                 (User.username == 'u0'))
             .order_by(Blog.pk)
             .naive())

        qc = len(self.queries())
        blogs = [b.title for b in q]
        self.assertEqual(blogs, ['b0-0', 'b0-1', 'b0-2'])

        usernames = [b.username for b in q]
        self.assertEqual(usernames, ['u0', 'u0', 'u0'])
        self.assertEqual(len(self.queries()) - qc, 1)

    def test_subselect(self):
        inner = User.select(User.username)
        self.assertEqual(
            [u.username for u in inner.order_by(User.username)], ['u0', 'u1'])

        # Have to manually specify the alias as "t1" because the outer query
        # will expect that.
        outer = (User
                 .select(User.username)
                 .from_(inner.alias('t1')))
        sql, params = compiler.generate_select(outer)
        self.assertEqual(sql, (
            'SELECT users."username" FROM '
            '(SELECT users."username" FROM "users" AS users) AS t1'))

        self.assertEqual(
            [u.username for u in outer.order_by(User.username)], ['u0', 'u1'])


class PrefetchTestCase(ModelTestCase):
    requires = [User, Blog, Comment, Parent, Child, Orphan, ChildPet, OrphanPet, Category]
    user_data = [
        ('u1', (('b1', ('b1-c1', 'b1-c2')), ('b2', ('b2-c1',)))),
        ('u2', ()),
        ('u3', (('b3', ('b3-c1', 'b3-c2')), ('b4', ()))),
        ('u4', (('b5', ('b5-c1', 'b5-c2')), ('b6', ('b6-c1',)))),
    ]
    parent_data = [
        ('p1', (
            # children
            (
                ('c1', ('c1-p1', 'c1-p2')),
                ('c2', ('c2-p1',)),
                ('c3', ('c3-p1',)),
                ('c4', ()),
            ),
            # orphans
            (
                ('o1', ('o1-p1', 'o1-p2')),
                ('o2', ('o2-p1',)),
                ('o3', ('o3-p1',)),
                ('o4', ()),
            ),
        )),
        ('p2', ((), ())),
        ('p3', (
            # children
            (
                ('c6', ()),
                ('c7', ('c7-p1',)),
            ),
            # orphans
            (
                ('o6', ('o6-p1', 'o6-p2')),
                ('o7', ('o7-p1',)),
            ),
        )),
    ]

    def setUp(self):
        super(PrefetchTestCase, self).setUp()
        for parent, (children, orphans) in self.parent_data:
            p = Parent.create(data=parent)
            for child_pets in children:
                child, pets = child_pets
                c = Child.create(parent=p, data=child)
                for pet in pets:
                    ChildPet.create(child=c, data=pet)
            for orphan_pets in orphans:
                orphan, pets = orphan_pets
                o = Orphan.create(parent=p, data=orphan)
                for pet in pets:
                    OrphanPet.create(orphan=o, data=pet)

        for user, blog_comments in self.user_data:
            u = User.create(username=user)
            for blog, comments in blog_comments:
                b = Blog.create(user=u, title=blog, content='')
                for c in comments:
                    Comment.create(blog=b, comment=c)

    def test_prefetch_simple(self):
        sq = User.select().where(User.username != 'u3')
        sq2 = Blog.select().where(Blog.title != 'b2')
        sq3 = Comment.select()
        qc = len(self.queries())

        prefetch_sq = prefetch(sq, sq2, sq3)
        results = []
        for user in prefetch_sq:
            results.append(user.username)
            for blog in user.blog_set_prefetch:
                results.append(blog.title)
                for comment in blog.comments_prefetch:
                    results.append(comment.comment)

        self.assertEqual(results, [
            'u1', 'b1', 'b1-c1', 'b1-c2',
            'u2',
            'u4', 'b5', 'b5-c1', 'b5-c2', 'b6', 'b6-c1',
        ])
        qc2 = len(self.queries())
        self.assertEqual(qc2 - qc, 3)

        results = []
        for user in prefetch_sq:
            for blog in user.blog_set_prefetch:
                results.append(blog.user.username)
                for comment in blog.comments_prefetch:
                    results.append(comment.blog.title)
        self.assertEqual(results, [
            'u1', 'b1', 'b1', 'u4', 'b5', 'b5', 'u4', 'b6',
        ])
        qc3 = len(self.queries())
        self.assertEqual(qc3, qc2)

    def test_prefetch_multi_depth(self):
        sq = Parent.select()
        sq2 = Child.select()
        sq3 = Orphan.select()
        sq4 = ChildPet.select()
        sq5 = OrphanPet.select()
        qc = len(self.queries())

        prefetch_sq = prefetch(sq, sq2, sq3, sq4, sq5)
        results = []
        for parent in prefetch_sq:
            results.append(parent.data)
            for child in parent.child_set_prefetch:
                results.append(child.data)
                for pet in child.childpet_set_prefetch:
                    results.append(pet.data)

            for orphan in parent.orphan_set_prefetch:
                results.append(orphan.data)
                for pet in orphan.orphanpet_set_prefetch:
                    results.append(pet.data)

        self.assertEqual(results, [
            'p1', 'c1', 'c1-p1', 'c1-p2', 'c2', 'c2-p1', 'c3', 'c3-p1', 'c4',
                  'o1', 'o1-p1', 'o1-p2', 'o2', 'o2-p1', 'o3', 'o3-p1', 'o4',
            'p2',
            'p3', 'c6', 'c7', 'c7-p1', 'o6', 'o6-p1', 'o6-p2', 'o7', 'o7-p1',
        ])
        self.assertEqual(len(self.queries()) - qc, 5)

class TestPrefetchNonPKFK(ModelTestCase):
    requires = [Package, PackageItem]
    data = {
        '101': ['a', 'b'],
        '102': ['c'],
        '103': [],
        '104': ['a', 'b', 'c', 'd', 'e'],
    }

    def setUp(self):
        super(TestPrefetchNonPKFK, self).setUp()
        for barcode, titles in self.data.items():
            Package.create(barcode=barcode)
            for title in titles:
                PackageItem.create(package=barcode, title=title)

    def test_prefetch(self):
        packages = Package.select().order_by(Package.barcode)
        items = PackageItem.select().order_by(PackageItem.id)
        query = prefetch(packages, items)

        for package, (barcode, titles) in zip(query, sorted(self.data.items())):
            self.assertEqual(package.barcode, barcode)
            self.assertEqual(
                [item.title for item in package.items_prefetch],
                titles)

        packages = (Package
                    .select()
                    .where(Package.barcode << ['101', '104'])
                    .order_by(Package.id))
        items = items.where(PackageItem.title << ['a', 'c', 'e'])
        query = prefetch(packages, items)
        accum = {}
        for package in query:
            accum[package.barcode] = [
                item.title for item in package.items_prefetch]

        self.assertEqual(accum, {
            '101': ['a'],
            '104': ['a', 'c','e'],
        })

class RecursiveDeleteTestCase(ModelTestCase):
    requires = [
        Parent, Child, Orphan, ChildPet, OrphanPet, Package, PackageItem]

    def setUp(self):
        super(RecursiveDeleteTestCase, self).setUp()
        p1 = Parent.create(data='p1')
        p2 = Parent.create(data='p2')
        c11 = Child.create(parent=p1)
        c12 = Child.create(parent=p1)
        c21 = Child.create(parent=p2)
        c22 = Child.create(parent=p2)
        o11 = Orphan.create(parent=p1)
        o12 = Orphan.create(parent=p1)
        o21 = Orphan.create(parent=p2)
        o22 = Orphan.create(parent=p2)
        ChildPet.create(child=c11)
        ChildPet.create(child=c12)
        ChildPet.create(child=c21)
        ChildPet.create(child=c22)
        OrphanPet.create(orphan=o11)
        OrphanPet.create(orphan=o12)
        OrphanPet.create(orphan=o21)
        OrphanPet.create(orphan=o22)
        self.p1 = p1
        self.p2 = p2

    def test_recursive_update(self):
        self.p1.delete_instance(recursive=True)
        counts = (
            #query,fk,p1,p2,tot
            (Child.select(), Child.parent, 0, 2, 2),
            (Orphan.select(), Orphan.parent, 0, 2, 4),
            (ChildPet.select().join(Child), Child.parent, 0, 2, 2),
            (OrphanPet.select().join(Orphan), Orphan.parent, 0, 2, 4),
        )

        for query, fk, p1_ct, p2_ct, tot in counts:
            self.assertEqual(query.where(fk == self.p1).count(), p1_ct)
            self.assertEqual(query.where(fk == self.p2).count(), p2_ct)
            self.assertEqual(query.count(), tot)

    def test_recursive_delete(self):
        self.p1.delete_instance(recursive=True, delete_nullable=True)
        counts = (
            #query,fk,p1,p2,tot
            (Child.select(), Child.parent, 0, 2, 2),
            (Orphan.select(), Orphan.parent, 0, 2, 2),
            (ChildPet.select().join(Child), Child.parent, 0, 2, 2),
            (OrphanPet.select().join(Orphan), Orphan.parent, 0, 2, 2),
        )

        for query, fk, p1_ct, p2_ct, tot in counts:
            self.assertEqual(query.where(fk == self.p1).count(), p1_ct)
            self.assertEqual(query.where(fk == self.p2).count(), p2_ct)
            self.assertEqual(query.count(), tot)

    def test_recursive_non_pk_fk(self):
        for i in range(3):
            Package.create(barcode=str(i))
            for j in range(4):
                PackageItem.create(package=str(i), title='%s-%s' % (i, j))

        self.assertEqual(Package.select().count(), 3)
        self.assertEqual(PackageItem.select().count(), 12)

        Package.get(Package.barcode == '1').delete_instance(recursive=True)

        self.assertEqual(Package.select().count(), 2)
        self.assertEqual(PackageItem.select().count(), 8)

        items = (PackageItem
                 .select(PackageItem.title)
                 .order_by(PackageItem.id)
                 .tuples())
        self.assertEqual([i[0] for i in items], [
            '0-0', '0-1', '0-2', '0-3',
            '2-0', '2-1', '2-2', '2-3',
        ])


class MultipleFKTestCase(ModelTestCase):
    requires = [User, Relationship]

    def test_multiple_fks(self):
        a = User.create(username='a')
        b = User.create(username='b')
        c = User.create(username='c')

        self.assertEqual(list(a.relationships), [])
        self.assertEqual(list(a.related_to), [])

        r_ab = Relationship.create(from_user=a, to_user=b)
        self.assertEqual(list(a.relationships), [r_ab])
        self.assertEqual(list(a.related_to), [])
        self.assertEqual(list(b.relationships), [])
        self.assertEqual(list(b.related_to), [r_ab])

        r_bc = Relationship.create(from_user=b, to_user=c)

        following = User.select().join(
            Relationship, on=Relationship.to_user
        ).where(Relationship.from_user == a)
        self.assertEqual(list(following), [b])

        followers = User.select().join(
            Relationship, on=Relationship.from_user
        ).where(Relationship.to_user == a.id)
        self.assertEqual(list(followers), [])

        following = User.select().join(
            Relationship, on=Relationship.to_user
        ).where(Relationship.from_user == b.id)
        self.assertEqual(list(following), [c])

        followers = User.select().join(
            Relationship, on=Relationship.from_user
        ).where(Relationship.to_user == b.id)
        self.assertEqual(list(followers), [a])

        following = User.select().join(
            Relationship, on=Relationship.to_user
        ).where(Relationship.from_user == c.id)
        self.assertEqual(list(following), [])

        followers = User.select().join(
            Relationship, on=Relationship.from_user
        ).where(Relationship.to_user == c.id)
        self.assertEqual(list(followers), [b])


class CompositeKeyTestCase(ModelTestCase):
    requires = [Tag, Post, TagPostThrough, CompositeKeyModel, User, UserThing]

    def setUp(self):
        super(CompositeKeyTestCase, self).setUp()
        tags = [Tag.create(tag='t%d' % i) for i in range(1, 4)]
        posts = [Post.create(title='p%d' % i) for i in range(1, 4)]
        p12 = Post.create(title='p12')
        for t, p in zip(tags, posts):
            TagPostThrough.create(tag=t, post=p)
        TagPostThrough.create(tag=tags[0], post=p12)
        TagPostThrough.create(tag=tags[1], post=p12)

    def test_create_table_query(self):
        query, params = compiler.create_table(TagPostThrough)
        self.assertEqual(
            query,
            'CREATE TABLE "tagpostthrough" '
            '("tag_id" INTEGER NOT NULL, '
            '"post_id" INTEGER NOT NULL, '
            'PRIMARY KEY ("tag_id", "post_id"), '
            'FOREIGN KEY ("tag_id") REFERENCES "tag" ("id"), '
            'FOREIGN KEY ("post_id") REFERENCES "post" ("id")'
            ')')

    def test_get_set_id(self):
        tpt = (TagPostThrough
               .select()
               .join(Tag)
               .switch(TagPostThrough)
               .join(Post)
               .order_by(Tag.tag, Post.title)).get()
        # Sanity check.
        self.assertEqual(tpt.tag.tag, 't1')
        self.assertEqual(tpt.post.title, 'p1')

        tag = Tag.select().where(Tag.tag == 't1').get()
        post = Post.select().where(Post.title == 'p1').get()
        self.assertEqual(tpt.get_id(), [tag, post])

        # set_id is a no-op.
        tpt.set_id(None)
        self.assertEqual(tpt.get_id(), [tag, post])

    def test_querying(self):
        posts = (Post.select()
                 .join(TagPostThrough)
                 .join(Tag)
                 .where(Tag.tag == 't1')
                 .order_by(Post.title))
        self.assertEqual([p.title for p in posts], ['p1', 'p12'])

        tags = (Tag.select()
                .join(TagPostThrough)
                .join(Post)
                .where(Post.title == 'p12')
                .order_by(Tag.tag))
        self.assertEqual([t.tag for t in tags], ['t1', 't2'])

    def test_composite_key_model(self):
        CKM = CompositeKeyModel
        values = [
            ('a', 1, 1.0),
            ('a', 2, 2.0),
            ('b', 1, 1.0),
            ('b', 2, 2.0)]
        c1, c2, c3, c4 = [
            CKM.create(f1=f1, f2=f2, f3=f3) for f1, f2, f3 in values]

        # Update a single row, giving it a new value for `f3`.
        CKM.update(f3=3.0).where((CKM.f1 == 'a') & (CKM.f2 == 2)).execute()

        c = CKM.get((CKM.f1 == 'a') & (CKM.f2 == 2))
        self.assertEqual(c.f3, 3.0)

        # Update the `f3` value and call `save()`, triggering an update.
        c3.f3 = 4.0
        c3.save()

        c = CKM.get((CKM.f1 == 'b') & (CKM.f2 == 1))
        self.assertEqual(c.f3, 4.0)

        # Only 1 row updated.
        query = CKM.select().where(CKM.f3 == 4.0)
        self.assertEqual(query.wrapped_count(), 1)

        # Unfortunately this does not work since the original value of the
        # PK is lost (and hence cannot be used to update).
        c4.f1 = 'c'
        c4.save()
        self.assertRaises(
            CKM.DoesNotExist, CKM.get, (CKM.f1 == 'c') & (CKM.f2 == 2))

    def test_count_composite_key(self):
        CKM = CompositeKeyModel
        values = [
            ('a', 1, 1.0),
            ('a', 2, 2.0),
            ('b', 1, 1.0),
            ('b', 2, 1.0)]
        for f1, f2, f3 in values:
            CKM.create(f1=f1, f2=f2, f3=f3)

        self.assertEqual(CKM.select().wrapped_count(), 4)
        self.assertTrue(CKM.select().where(
            (CKM.f1 == 'a') &
            (CKM.f2 == 1)).exists())
        self.assertFalse(CKM.select().where(
            (CKM.f1 == 'a') &
            (CKM.f2 == 3)).exists())

    def test_delete_instance(self):
        u1, u2 = [User.create(username='u%s' % i) for i in range(2)]
        ut1 = UserThing.create(thing='t1', user=u1)
        ut2 = UserThing.create(thing='t2', user=u1)
        ut3 = UserThing.create(thing='t1', user=u2)
        ut4 = UserThing.create(thing='t3', user=u2)

        res = ut1.delete_instance()
        self.assertEqual(res, 1)
        self.assertEqual(
            [x.thing for x in UserThing.select().order_by(UserThing.thing)],
            ['t1', 't2', 't3'])


class ManyToManyTestCase(ModelTestCase):
    requires = [User, Category, UserCategory]

    def test_m2m(self):
        u1 = User.create(username='u1')
        u2 = User.create(username='u2')
        u3 = User.create(username='u3')

        c1 = Category.create(name='c1')
        c2 = Category.create(name='c2')
        c3 = Category.create(name='c3')

        # extras
        c12 = Category.create(name='c12')
        c23 = Category.create(name='c23')

        umap = (
            (u1, c1),
            (u2, c2),
            (u1, c12),
            (u2, c12),
            (u2, c23),
        )

        for u, c in umap:
            UserCategory.create(user=u, category=c)

        def aU(q, exp):
            self.assertEqual([u.username for u in q.order_by(User.username)], exp)
        def aC(q, exp):
            self.assertEqual([c.name for c in q.order_by(Category.name)], exp)

        users = User.select().join(UserCategory).join(Category).where(Category.name == 'c1')
        aU(users, ['u1'])

        users = User.select().join(UserCategory).join(Category).where(Category.name == 'c3')
        aU(users, [])

        cats = Category.select().join(UserCategory).join(User).where(User.username == 'u1')
        aC(cats, ['c1', 'c12'])

        cats = Category.select().join(UserCategory).join(User).where(User.username == 'u2')
        aC(cats, ['c12', 'c2', 'c23'])

        cats = Category.select().join(UserCategory).join(User).where(User.username == 'u3')
        aC(cats, [])

        cats = Category.select().join(UserCategory).join(User).where(
            Category.name << ['c1', 'c2', 'c3']
        )
        aC(cats, ['c1', 'c2'])

        cats = Category.select().join(UserCategory, JOIN_LEFT_OUTER).join(User, JOIN_LEFT_OUTER).where(
            Category.name << ['c1', 'c2', 'c3']
        )
        aC(cats, ['c1', 'c2', 'c3'])


class FieldTypeTestCase(ModelTestCase):
    requires = [NullModel, BlobModel]

    _dt = datetime.datetime
    _d = datetime.date
    _t = datetime.time

    _data = (
        ('char_field', 'text_field', 'int_field', 'float_field', 'decimal_field1', 'datetime_field', 'date_field', 'time_field'),
        ('c1',         't1',         1,           1.0,           "1.0",            _dt(2010, 1, 1),  _d(2010, 1, 1), _t(1, 0)),
        ('c2',         't2',         2,           2.0,           "2.0",            _dt(2010, 1, 2),  _d(2010, 1, 2), _t(2, 0)),
        ('c3',         't3',         3,           3.0,           "3.0",            _dt(2010, 1, 3),  _d(2010, 1, 3), _t(3, 0)),
    )

    def setUp(self):
        super(FieldTypeTestCase, self).setUp()
        self.field_data = {}

        headers = self._data[0]
        for row in self._data[1:]:
            nm = NullModel()
            for i, col in enumerate(row):
                attr = headers[i]
                self.field_data.setdefault(attr, [])
                self.field_data[attr].append(col)
                setattr(nm, attr, col)
            nm.save()

    def assertNM(self, q, exp):
        query = NullModel.select().where(q).order_by(NullModel.id)
        self.assertEqual([nm.char_field for nm in query], exp)

    def test_null_query(self):
        NullModel.delete().execute()
        nm1 = NullModel.create(char_field='nm1')
        nm2 = NullModel.create(char_field='nm2', int_field=1)
        nm3 = NullModel.create(char_field='nm3', int_field=2, float_field=3.0)

        q = ~(NullModel.int_field >> None)
        self.assertNM(q, ['nm2', 'nm3'])

    def test_field_types(self):
        for field, values in self.field_data.items():
            field_obj = getattr(NullModel, field)
            self.assertNM(field_obj < values[2], ['c1', 'c2'])
            self.assertNM(field_obj <= values[1], ['c1', 'c2'])
            self.assertNM(field_obj > values[0], ['c2', 'c3'])
            self.assertNM(field_obj >= values[1], ['c2', 'c3'])
            self.assertNM(field_obj == values[1], ['c2'])
            self.assertNM(field_obj != values[1], ['c1', 'c3'])
            self.assertNM(field_obj << [values[0], values[2]], ['c1', 'c3'])
            self.assertNM(field_obj << [values[1]], ['c2'])

    def test_charfield(self):
        NM = NullModel
        nm = NM.create(char_field=4)
        nm_db = NM.get(NM.id==nm.id)
        self.assertEqual(nm_db.char_field, '4')

        nm_alpha = NM.create(char_field='Alpha')
        nm_bravo = NM.create(char_field='Bravo')

        if isinstance(test_db, SqliteDatabase):
            # Sqlite's sql-dialect uses "*" as case-sensitive lookup wildcard,
            # and pysqlcipher is simply a wrapper around sqlite's engine.
            like_wildcard = '*'
        else:
            like_wildcard = '%'
        like_str = '%sA%s' % (like_wildcard, like_wildcard)
        ilike_str = '%A%'

        case_sens = NM.select(NM.char_field).where(NM.char_field % like_str)
        self.assertEqual([x[0] for x in case_sens.tuples()], ['Alpha'])

        case_insens = NM.select(NM.char_field).where(NM.char_field ** ilike_str)
        self.assertEqual([x[0] for x in case_insens.tuples()], ['Alpha', 'Bravo'])

    def test_intfield(self):
        nm = NullModel.create(int_field='4')
        nm_db = NullModel.get(NullModel.id==nm.id)
        self.assertEqual(nm_db.int_field, 4)

    def test_floatfield(self):
        nm = NullModel.create(float_field='4.2')
        nm_db = NullModel.get(NullModel.id==nm.id)
        self.assertEqual(nm_db.float_field, 4.2)

    def test_decimalfield(self):
        D = decimal.Decimal
        nm = NullModel()
        nm.decimal_field1 = D("3.14159265358979323")
        nm.decimal_field2 = D("100.33")
        nm.save()

        nm_from_db = NullModel.get(NullModel.id==nm.id)
        # sqlite doesn't enforce these constraints properly
        #self.assertEqual(nm_from_db.decimal_field1, decimal.Decimal("3.14159"))
        self.assertEqual(nm_from_db.decimal_field2, D("100.33"))

        class TestDecimalModel(TestModel):
            df1 = DecimalField(decimal_places=2, auto_round=True)
            df2 = DecimalField(decimal_places=2, auto_round=True, rounding=decimal.ROUND_UP)

        f1 = TestDecimalModel.df1.db_value
        f2 = TestDecimalModel.df2.db_value

        self.assertEqual(f1(D('1.2345')), D('1.23'))
        self.assertEqual(f2(D('1.2345')), D('1.24'))

    def test_boolfield(self):
        NullModel.delete().execute()

        nmt = NullModel.create(boolean_field=True, char_field='t')
        nmf = NullModel.create(boolean_field=False, char_field='f')
        nmn = NullModel.create(boolean_field=None, char_field='n')

        self.assertNM(NullModel.boolean_field == True, ['t'])
        self.assertNM(NullModel.boolean_field == False, ['f'])
        self.assertNM(NullModel.boolean_field >> None, ['n'])

    def _time_to_delta(self, t):
        micro = t.microsecond / 1000000.
        return datetime.timedelta(
            seconds=(3600 * t.hour) + (60 * t.minute) + t.second + micro)

    def test_date_and_time_fields(self):
        dt1 = datetime.datetime(2011, 1, 2, 11, 12, 13, 54321)
        dt2 = datetime.datetime(2011, 1, 2, 11, 12, 13)
        d1 = datetime.date(2011, 1, 3)
        t1 = datetime.time(11, 12, 13, 54321)
        t2 = datetime.time(11, 12, 13)
        td1 = self._time_to_delta(t1)
        td2 = self._time_to_delta(t2)

        nm1 = NullModel.create(datetime_field=dt1, date_field=d1, time_field=t1)
        nm2 = NullModel.create(datetime_field=dt2, time_field=t2)

        nmf1 = NullModel.get(NullModel.id==nm1.id)
        self.assertEqual(nmf1.date_field, d1)
        if isinstance(test_db, MySQLDatabase):
            # mysql doesn't store microseconds
            self.assertEqual(nmf1.datetime_field, dt2)
            self.assertEqual(nmf1.time_field, td2)
        else:
            self.assertEqual(nmf1.datetime_field, dt1)
            self.assertEqual(nmf1.time_field, t1)

        nmf2 = NullModel.get(NullModel.id==nm2.id)
        self.assertEqual(nmf2.datetime_field, dt2)
        if isinstance(test_db, MySQLDatabase):
            self.assertEqual(nmf2.time_field, td2)
        else:
            self.assertEqual(nmf2.time_field, t2)

    def test_various_formats(self):
        class FormatModel(Model):
            dtf = DateTimeField()
            df = DateField()
            tf = TimeField()

        dtf = FormatModel._meta.fields['dtf']
        df = FormatModel._meta.fields['df']
        tf = FormatModel._meta.fields['tf']

        d = datetime.datetime
        self.assertEqual(dtf.python_value('2012-01-01 11:11:11.123456'), d(
            2012, 1, 1, 11, 11, 11, 123456
        ))
        self.assertEqual(dtf.python_value('2012-01-01 11:11:11'), d(
            2012, 1, 1, 11, 11, 11
        ))
        self.assertEqual(dtf.python_value('2012-01-01'), d(
            2012, 1, 1,
        ))
        self.assertEqual(dtf.python_value('2012 01 01'), '2012 01 01')

        d = datetime.date
        self.assertEqual(df.python_value('2012-01-01 11:11:11.123456'), d(
            2012, 1, 1,
        ))
        self.assertEqual(df.python_value('2012-01-01 11:11:11'), d(
            2012, 1, 1,
        ))
        self.assertEqual(df.python_value('2012-01-01'), d(
            2012, 1, 1,
        ))
        self.assertEqual(df.python_value('2012 01 01'), '2012 01 01')

        t = datetime.time
        self.assertEqual(tf.python_value('2012-01-01 11:11:11.123456'), t(
            11, 11, 11, 123456
        ))
        self.assertEqual(tf.python_value('2012-01-01 11:11:11'), t(
            11, 11, 11
        ))
        self.assertEqual(tf.python_value('11:11:11.123456'), t(
            11, 11, 11, 123456
        ))
        self.assertEqual(tf.python_value('11:11:11'), t(
            11, 11, 11
        ))
        self.assertEqual(tf.python_value('11:11'), t(
            11, 11,
        ))
        self.assertEqual(tf.python_value('11:11 AM'), '11:11 AM')

        class CustomFormatsModel(Model):
            dtf = DateTimeField(formats=['%b %d, %Y %I:%M:%S %p'])
            df = DateField(formats=['%b %d, %Y'])
            tf = TimeField(formats=['%I:%M %p'])

        dtf = CustomFormatsModel._meta.fields['dtf']
        df = CustomFormatsModel._meta.fields['df']
        tf = CustomFormatsModel._meta.fields['tf']

        d = datetime.datetime
        self.assertEqual(dtf.python_value('2012-01-01 11:11:11.123456'), '2012-01-01 11:11:11.123456')
        self.assertEqual(dtf.python_value('Jan 1, 2012 11:11:11 PM'), d(
            2012, 1, 1, 23, 11, 11,
        ))

        d = datetime.date
        self.assertEqual(df.python_value('2012-01-01'), '2012-01-01')
        self.assertEqual(df.python_value('Jan 1, 2012'), d(
            2012, 1, 1,
        ))

        t = datetime.time
        self.assertEqual(tf.python_value('11:11:11'), '11:11:11')
        self.assertEqual(tf.python_value('11:11 PM'), t(
            23, 11
        ))

    def test_blob_field(self):
        byte_count = 256
        data = ''.join(chr(i) for i in range(256))
        blob = BlobModel.create(data=data)

        # pull from db and check binary data
        res = BlobModel.get(BlobModel.id == blob.id)
        self.assertTrue(isinstance(res.data, binary_types))

        self.assertEqual(len(res.data), byte_count)
        db_data = res.data
        binary_data = binary_construct(data)

        if db_data != binary_data and sys.version_info[:3] >= (3, 3, 3):
            db_data = db_data.tobytes()

        self.assertEqual(db_data, binary_data)

        # try querying the blob field
        binary_data = res.data

        # use the string representation
        res = BlobModel.get(BlobModel.data == data)
        self.assertEqual(res.id, blob.id)

        # use the binary representation
        res = BlobModel.get(BlobModel.data == binary_data)
        self.assertEqual(res.id, blob.id)

    def test_between(self):
        field = NullModel.int_field
        self.assertNM(field.between(1, 2), ['c1', 'c2'])
        self.assertNM(field.between(2, 3), ['c2', 'c3'])
        self.assertNM(field.between(5, 300), [])

    def test_in_(self):
        self.assertNM(NullModel.int_field.in_(1, 3), ['c1', 'c3'])
        self.assertNM(NullModel.int_field.in_(2, 5), ['c2'])

    def test_contains(self):
        self.assertNM(NullModel.char_field.contains('c2'), ['c2'])
        self.assertNM(NullModel.char_field.contains('c'), ['c1', 'c2', 'c3'])
        self.assertNM(NullModel.char_field.contains('1'), ['c1'])

    def test_startswith(self):
        NullModel.create(char_field='ch1')
        self.assertNM(NullModel.char_field.startswith('c'), ['c1', 'c2', 'c3', 'ch1'])
        self.assertNM(NullModel.char_field.startswith('ch'), ['ch1'])
        self.assertNM(NullModel.char_field.startswith('a'), [])

    def test_endswith(self):
        NullModel.create(char_field='ch1')
        self.assertNM(NullModel.char_field.endswith('1'), ['c1', 'ch1'])
        self.assertNM(NullModel.char_field.endswith('4'), [])

    def test_regexp(self):
        values = [
            'abcdefg',
            'abcd',
            'defg',
            'gij',
            'xx',
        ]
        for value in values:
            NullModel.create(char_field=value)

        def assertValues(regexp, *expected):
            query = NullModel.select().where(
                NullModel.char_field.regexp(regexp)).order_by(NullModel.id)
            values = [nm.char_field for nm in query]
            self.assertEqual(values, list(expected))

        assertValues('^ab', 'abcdefg', 'abcd')
        assertValues('d', 'abcdefg', 'abcd', 'defg')
        assertValues('efg$', 'abcdefg', 'defg')
        assertValues('a.+d', 'abcdefg', 'abcd')

class DateTimeExtractTestCase(ModelTestCase):
    requires = [NullModel]

    test_datetimes = [
        datetime.datetime(2001, 1, 2, 3, 4, 5),
        datetime.datetime(2002, 2, 3, 4, 5, 6),
        # overlap on year and hour with previous
        datetime.datetime(2002, 3, 4, 4, 6, 7),
    ]
    datetime_parts = ['year', 'month', 'day', 'hour', 'minute', 'second']
    date_parts = datetime_parts[:3]
    time_parts = datetime_parts[3:]

    def setUp(self):
        super(DateTimeExtractTestCase, self).setUp()

        self.nms = []
        for dt in self.test_datetimes:
            self.nms.append(NullModel.create(
                datetime_field=dt,
                date_field=dt.date(),
                time_field=dt.time()))

    def assertDates(self, sq, expected):
        sq = sq.tuples().order_by(NullModel.id)
        self.assertEqual(list(sq), [(e,) for e in expected])

    def assertPKs(self, sq, idxs):
        sq = sq.tuples().order_by(NullModel.id)
        self.assertEqual(list(sq), [(self.nms[i].id,) for i in idxs])

    def test_extract_datetime(self):
        self.test_extract_date(NullModel.datetime_field)
        self.test_extract_time(NullModel.datetime_field)

    def test_extract_date(self, f=None):
        if f is None:
            f = NullModel.date_field

        self.assertDates(NullModel.select(f.year), [2001, 2002, 2002])
        self.assertDates(NullModel.select(f.month), [1, 2, 3])
        self.assertDates(NullModel.select(f.day), [2, 3, 4])

    def test_extract_time(self, f=None):
        if f is None:
            f = NullModel.time_field

        self.assertDates(NullModel.select(f.hour), [3, 4, 4])
        self.assertDates(NullModel.select(f.minute), [4, 5, 6])
        self.assertDates(NullModel.select(f.second), [5, 6, 7])

    def test_extract_datetime_where(self):
        f = NullModel.datetime_field
        self.test_extract_date_where(f)
        self.test_extract_time_where(f)

        sq = NullModel.select(NullModel.id)
        self.assertPKs(sq.where((f.year == 2002) & (f.month == 2)), [1])
        self.assertPKs(sq.where((f.year == 2002) & (f.hour == 4)), [1, 2])
        self.assertPKs(sq.where((f.year == 2002) & (f.minute == 5)), [1])

    def test_extract_date_where(self, f=None):
        if f is None:
            f = NullModel.date_field

        sq = NullModel.select(NullModel.id)
        self.assertPKs(sq.where(f.year == 2001), [0])
        self.assertPKs(sq.where(f.year == 2002), [1, 2])
        self.assertPKs(sq.where(f.year == 2003), [])

        self.assertPKs(sq.where(f.month == 1), [0])
        self.assertPKs(sq.where(f.month > 1), [1, 2])
        self.assertPKs(sq.where(f.month == 4), [])

        self.assertPKs(sq.where(f.day == 2), [0])
        self.assertPKs(sq.where(f.day > 2), [1, 2])
        self.assertPKs(sq.where(f.day == 5), [])

    def test_extract_time_where(self, f=None):
        if f is None:
            f = NullModel.time_field

        sq = NullModel.select(NullModel.id)
        self.assertPKs(sq.where(f.hour == 3), [0])
        self.assertPKs(sq.where(f.hour == 4), [1, 2])
        self.assertPKs(sq.where(f.hour == 5), [])

        self.assertPKs(sq.where(f.minute == 4), [0])
        self.assertPKs(sq.where(f.minute > 4), [1, 2])
        self.assertPKs(sq.where(f.minute == 7), [])

        self.assertPKs(sq.where(f.second == 5), [0])
        self.assertPKs(sq.where(f.second > 5), [1, 2])
        self.assertPKs(sq.where(f.second == 8), [])


class UniqueTestCase(ModelTestCase):
    requires = [UniqueModel, MultiIndexModel]

    def test_unique(self):
        uniq1 = UniqueModel.create(name='a')
        uniq2 = UniqueModel.create(name='b')
        self.assertRaises(Exception, UniqueModel.create, name='a')
        test_db.rollback()

    def test_multi_index(self):
        mi1 = MultiIndexModel.create(f1='a', f2='a', f3='a')
        mi2 = MultiIndexModel.create(f1='b', f2='b', f3='b')
        self.assertRaises(Exception, MultiIndexModel.create, f1='a', f2='a', f3='b')
        test_db.rollback()
        self.assertRaises(Exception, MultiIndexModel.create, f1='b', f2='b', f3='a')
        test_db.rollback()

        mi3 = MultiIndexModel.create(f1='a', f2='b', f3='b')

class NonIntPKTestCase(ModelTestCase):
    requires = [NonIntModel, NonIntRelModel]

    def test_non_int_pk(self):
        ni1 = NonIntModel.create(pk='a1', data='ni1')
        self.assertEqual(ni1.pk, 'a1')

        ni2 = NonIntModel(pk='a2', data='ni2')
        ni2.save(force_insert=True)
        self.assertEqual(ni2.pk, 'a2')

        ni2.save()
        self.assertEqual(ni2.pk, 'a2')

        self.assertEqual(NonIntModel.select().count(), 2)

        ni1_db = NonIntModel.get(NonIntModel.pk=='a1')
        self.assertEqual(ni1_db.data, ni1.data)

        self.assertEqual([(x.pk, x.data) for x in NonIntModel.select().order_by(NonIntModel.pk)], [
            ('a1', 'ni1'), ('a2', 'ni2'),
        ])

    def test_non_int_fk(self):
        ni1 = NonIntModel.create(pk='a1', data='ni1')
        ni2 = NonIntModel.create(pk='a2', data='ni2')

        rni11 = NonIntRelModel(non_int_model=ni1)
        rni12 = NonIntRelModel(non_int_model=ni1)
        rni11.save()
        rni12.save()

        self.assertEqual([r.id for r in ni1.nr.order_by(NonIntRelModel.id)], [rni11.id, rni12.id])
        self.assertEqual([r.id for r in ni2.nr.order_by(NonIntRelModel.id)], [])

        rni21 = NonIntRelModel.create(non_int_model=ni2)
        self.assertEqual([r.id for r in ni2.nr.order_by(NonIntRelModel.id)], [rni21.id])

        sq = NonIntRelModel.select().join(NonIntModel).where(NonIntModel.data == 'ni2')
        self.assertEqual([r.id for r in sq], [rni21.id])


class PrimaryForeignKeyTestCase(ModelTestCase):
    requires = [Job, JobExecutionRecord]

    def test_primary_foreign_key(self):
        # we have one job, unexecuted, and therefore no executed jobs
        job = Job.create(name='Job One')
        executed_jobs = Job.select().join(JobExecutionRecord)
        self.assertEqual([], list(executed_jobs))

        # after execution, we must have one executed job
        exec_record = JobExecutionRecord.create(job=job, status='success')
        executed_jobs = Job.select().join(JobExecutionRecord)
        self.assertEqual([job], list(executed_jobs))

        # we must not be able to create another execution record for the job
        self.assertRaises(Exception, JobExecutionRecord.create, job=job, status='success')
        test_db.rollback()


class NonPKFKCreateTableTestCase(BasePeeweeTestCase):
    def test_create_table(self):
        class A(TestModel):
            cf = CharField(max_length=100, unique=True)
            df = DecimalField(
                max_digits=4,
                decimal_places=2,
                auto_round=True,
                unique=True)

        class CF(TestModel):
            a = ForeignKeyField(A, to_field='cf')

        class DF(TestModel):
            a = ForeignKeyField(A, to_field='df')

        cf_create, _ = compiler.create_table(CF)
        self.assertEqual(
            cf_create,
            'CREATE TABLE "cf" ('
            '"id" INTEGER NOT NULL PRIMARY KEY, '
            '"a_id" VARCHAR(100) NOT NULL, '
            'FOREIGN KEY ("a_id") REFERENCES "a" ("cf"))')

        df_create, _ = compiler.create_table(DF)
        self.assertEqual(
            df_create,
            'CREATE TABLE "df" ('
            '"id" INTEGER NOT NULL PRIMARY KEY, '
            '"a_id" DECIMAL(4, 2) NOT NULL, '
            'FOREIGN KEY ("a_id") REFERENCES "a" ("df"))')

class DeferredForeignKeyTestCase(ModelTestCase):
    requires = [Snippet, Language]

    def test_field_definitions(self):
        self.assertEqual(Snippet._meta.fields['language'].rel_model, Language)
        self.assertEqual(Language._meta.fields['selected_snippet'].rel_model,
                         Snippet)

    def test_create_table_query(self):
        query, params = compiler.create_table(Snippet)
        self.assertEqual(
            query,
            'CREATE TABLE "snippet" '
            '("id" INTEGER NOT NULL PRIMARY KEY, '
            '"code" TEXT NOT NULL, '
            '"language_id" INTEGER NOT NULL, '
            'FOREIGN KEY ("language_id") REFERENCES "language" ("id")'
            ')')

        query, params = compiler.create_table(Language)
        self.assertEqual(
            query,
            'CREATE TABLE "language" '
            '("id" INTEGER NOT NULL PRIMARY KEY, '
            '"name" VARCHAR(255) NOT NULL, '
            '"selected_snippet_id" INTEGER)')

    def test_storage_retrieval(self):
        python = Language.create(name='python')
        javascript = Language.create(name='javascript')
        p1 = Snippet.create(code="print 'Hello world'", language=python)
        p2 = Snippet.create(code="print 'Goodbye world'", language=python)
        j1 = Snippet.create(code="alert('Hello world')", language=javascript)

        self.assertEqual(Snippet.get(Snippet.id == p1.id).language, python)
        self.assertEqual(Snippet.get(Snippet.id == j1.id).language, javascript)

        python.selected_snippet = p2
        python.save()

        self.assertEqual(
            Language.get(Language.id == python.id).selected_snippet, p2)
        self.assertEqual(
            Language.get(Language.id == javascript.id).selected_snippet, None)


class DBColumnTestCase(ModelTestCase):
    requires = [DBUser, DBBlog]

    def test_select(self):
        sq = DBUser.select().where(DBUser.username == 'u1')
        self.assertSelect(sq, 'dbuser."db_user_id", dbuser."db_username"', [])
        self.assertWhere(sq, '(dbuser."db_username" = ?)', ['u1'])

        sq = DBUser.select(DBUser.user_id).join(DBBlog).where(DBBlog.title == 'b1')
        self.assertSelect(sq, 'dbuser."db_user_id"', [])
        self.assertJoins(sq, ['INNER JOIN "dbblog" AS dbblog ON (dbuser."db_user_id" = dbblog."db_user")'])
        self.assertWhere(sq, '(dbblog."db_title" = ?)', ['b1'])

    def test_db_column(self):
        u1 = DBUser.create(username='u1')
        u2 = DBUser.create(username='u2')
        u2_db = DBUser.get(DBUser.user_id==u2.get_id())
        self.assertEqual(u2_db.username, 'u2')

        b1 = DBBlog.create(user=u1, title='b1')
        b2 = DBBlog.create(user=u2, title='b2')
        b2_db = DBBlog.get(DBBlog.blog_id==b2.get_id())
        self.assertEqual(b2_db.user.user_id, u2.user_id)
        self.assertEqual(b2_db.title, 'b2')

        self.assertEqual([b.title for b in u2.dbblog_set], ['b2'])


class TransactionTestCase(ModelTestCase):
    requires = [User, Blog]

    def tearDown(self):
        super(TransactionTestCase, self).tearDown()
        test_db.set_autocommit(True)

    def test_autocommit(self):
        if database_class is BerkeleyDatabase:
            if TEST_VERBOSITY > 0:
                print_('Skipping `test_autocommit` for berkeleydb.')
            return

        test_db.set_autocommit(False)

        u1 = User.create(username='u1')
        u2 = User.create(username='u2')

        # open up a new connection to the database, it won't register any blogs
        # as being created
        new_db = database_class(database_name, **database_params)
        res = new_db.execute_sql('select count(*) from users;')
        self.assertEqual(res.fetchone()[0], 0)

        # commit our blog inserts
        test_db.commit()

        # now the blogs are query-able from another connection
        res = new_db.execute_sql('select count(*) from users;')
        self.assertEqual(res.fetchone()[0], 2)

    def test_commit_on_success(self):
        self.assertTrue(test_db.get_autocommit())

        @test_db.commit_on_success
        def will_fail():
            User.create(username='u1')
            Blog.create() # no blog, will raise an error

        self.assertRaises(IntegrityError, will_fail)
        self.assertEqual(User.select().count(), 0)
        self.assertEqual(Blog.select().count(), 0)

        @test_db.commit_on_success
        def will_succeed():
            u = User.create(username='u1')
            Blog.create(title='b1', user=u)

        will_succeed()
        self.assertEqual(User.select().count(), 1)
        self.assertEqual(Blog.select().count(), 1)

    def test_context_mgr(self):
        def do_will_fail():
            with test_db.transaction():
                User.create(username='u1')
                Blog.create() # no blog, will raise an error

        self.assertRaises(IntegrityError, do_will_fail)
        self.assertEqual(Blog.select().count(), 0)

        def do_will_succeed():
            with transaction(test_db):
                u = User.create(username='u1')
                Blog.create(title='b1', user=u)

        do_will_succeed()
        self.assertEqual(User.select().count(), 1)
        self.assertEqual(Blog.select().count(), 1)

    def test_nesting_transactions(self):
        @test_db.commit_on_success
        def outer(should_fail=False):
            self.assertEqual(test_db.transaction_depth(), 1)
            User.create(username='outer')
            inner(should_fail)
            self.assertEqual(test_db.transaction_depth(), 1)

        @test_db.commit_on_success
        def inner(should_fail):
            self.assertEqual(test_db.transaction_depth(), 2)
            User.create(username='inner')
            if should_fail:
                raise ValueError('failing')

        self.assertRaises(ValueError, outer, should_fail=True)
        self.assertEqual(User.select().count(), 0)
        self.assertEqual(test_db.transaction_depth(), 0)

        outer(should_fail=False)
        self.assertEqual(User.select().count(), 2)
        self.assertEqual(test_db.transaction_depth(), 0)


class ConcurrencyTestCase(ModelTestCase):
    requires = [User]
    threads = 4

    def setUp(self):
        self._orig_db = test_db
        kwargs = {'threadlocals': True}
        try:  # Some engines need the extra kwargs.
            kwargs.update(test_db.connect_kwargs)
        except:
            pass
        if isinstance(test_db, SqliteDatabase):
            # Put a very large timeout in place to avoid `database is locked`
            # when using SQLite (default is 5).
            kwargs['timeout'] = 30

        User._meta.database = database_class(database_name, **kwargs)
        super(ConcurrencyTestCase, self).setUp()

    def tearDown(self):
        User._meta.database = self._orig_db
        super(ConcurrencyTestCase, self).tearDown()

    def test_multiple_writers(self):
        def create_user_thread(low, hi):
            for i in range(low, hi):
                User.create(username='u%d' % i)
            User._meta.database.close()

        threads = []

        for i in range(self.threads):
            threads.append(threading.Thread(target=create_user_thread, args=(i*10, i * 10 + 10)))

        [t.start() for t in threads]
        [t.join() for t in threads]

        self.assertEqual(User.select().count(), self.threads * 10)

    def test_multiple_readers(self):
        data_queue = Queue()

        def reader_thread(q, num):
            for i in range(num):
                data_queue.put(User.select().count())

        threads = []

        for i in range(self.threads):
            threads.append(threading.Thread(target=reader_thread, args=(data_queue, 20)))

        [t.start() for t in threads]
        [t.join() for t in threads]

        self.assertEqual(data_queue.qsize(), self.threads * 20)


class CompoundSelectTestCase(ModelTestCase):
    requires = [User, UniqueModel, OrderedModel]
    # User -> username, UniqueModel -> name, OrderedModel -> title
    test_values = {
        User.username: ['a', 'b', 'c', 'd'],
        UniqueModel.name: ['b', 'd', 'e'],
        OrderedModel.title: ['a', 'c', 'e'],
    }

    def setUp(self):
        super(CompoundSelectTestCase, self).setUp()
        for field, values in self.test_values.items():
            for value in values:
                field.model_class.create(**{field.name: value})

    def requires_op(op):
        def decorator(fn):
            @wraps(fn)
            def inner(self):
                if op in test_db.compound_operations:
                    return fn(self)
                elif TEST_VERBOSITY > 0:
                    print_('"%s" not supported, skipping %s' %
                           (op, fn.__name__))
            return inner
        return decorator

    def assertValues(self, query, expected):
        self.assertEqual(sorted(query.tuples()),
                         [(x,) for x in sorted(expected)])

    def assertPermutations(self, op, expected):
        fields = {
            User: User.username,
            UniqueModel: UniqueModel.name,
            OrderedModel: OrderedModel.title,
        }
        for key in itertools.permutations(fields.keys(), 2):
            if key in expected:
                left, right = key
                query = op(left.select(fields[left]).order_by(),
                           right.select(fields[right]).order_by())
                # Ensure the sorted tuples returned from the query are equal
                # to the sorted values we expected for this combination.
                self.assertValues(query, expected[key])

    @requires_op('UNION')
    def test_union(self):
        all_letters = ['a', 'b', 'c', 'd', 'e']
        self.assertPermutations(operator.or_, {
            (User, UniqueModel): all_letters,
            (User, OrderedModel): all_letters,
            (UniqueModel, User): all_letters,
            (UniqueModel, OrderedModel): all_letters,
            (OrderedModel, User): all_letters,
            (OrderedModel, UniqueModel): all_letters,
        })

    @requires_op('INTERSECT')
    def test_intersect(self):
        self.assertPermutations(operator.and_, {
            (User, UniqueModel): ['b', 'd'],
            (User, OrderedModel): ['a', 'c'],
            (UniqueModel, User): ['b', 'd'],
            (UniqueModel, OrderedModel): ['e'],
            (OrderedModel, User): ['a', 'c'],
            (OrderedModel, UniqueModel): ['e'],
        })

    @requires_op('EXCEPT')
    def test_except(self):
        self.assertPermutations(operator.sub, {
            (User, UniqueModel): ['a', 'c'],
            (User, OrderedModel): ['b', 'd'],
            (UniqueModel, User): ['e'],
            (UniqueModel, OrderedModel): ['b', 'd'],
            (OrderedModel, User): ['e'],
            (OrderedModel, UniqueModel): ['a', 'c'],
        })

    @requires_op('INTERSECT')
    @requires_op('EXCEPT')
    def test_symmetric_difference(self):
        self.assertPermutations(operator.xor, {
            (User, UniqueModel): ['a', 'c', 'e'],
            (User, OrderedModel): ['b', 'd', 'e'],
            (UniqueModel, User): ['a', 'c', 'e'],
            (UniqueModel, OrderedModel): ['a', 'b', 'c', 'd'],
            (OrderedModel, User): ['b', 'd', 'e'],
            (OrderedModel, UniqueModel): ['a', 'b', 'c', 'd'],
        })

    def test_model_instances(self):
        union = (User.select(User.username) |
                 UniqueModel.select(UniqueModel.name))
        query = union.order_by(SQL('username').desc()).limit(3)
        self.assertEqual([user.username for user in query],
                         ['e', 'd', 'c'])

    @requires_op('UNION')
    @requires_op('INTERSECT')
    def test_complex(self):
        left = User.select(User.username).where(User.username << ['a', 'b'])
        right = UniqueModel.select(UniqueModel.name).where(
            UniqueModel.name << ['b', 'd', 'e'])

        query = (left & right).order_by(SQL('1'))
        self.assertEqual(list(query.dicts()), [{'username': 'b'}])

        query = (left | right).order_by(SQL('1'))
        self.assertEqual(list(query.dicts()), [
            {'username': 'a'},
            {'username': 'b'},
            {'username': 'd'},
            {'username': 'e'}])

class ModelOptionInheritanceTestCase(BasePeeweeTestCase):
    def test_db_table(self):
        self.assertEqual(User._meta.db_table, 'users')

        class Foo(TestModel):
            pass
        self.assertEqual(Foo._meta.db_table, 'foo')

        class Foo2(TestModel):
            pass
        self.assertEqual(Foo2._meta.db_table, 'foo2')

        class Foo_3(TestModel):
            pass
        self.assertEqual(Foo_3._meta.db_table, 'foo_3')

    def test_custom_options(self):
        class A(Model):
            class Meta:
                a = 'a'

        class B1(A):
            class Meta:
                b = 1

        class B2(A):
            class Meta:
                b = 2

        self.assertEqual(A._meta.a, 'a')
        self.assertEqual(B1._meta.a, 'a')
        self.assertEqual(B2._meta.a, 'a')
        self.assertEqual(B1._meta.b, 1)
        self.assertEqual(B2._meta.b, 2)

    def test_option_inheritance(self):
        x_test_db = SqliteDatabase('testing.db')
        child2_db = SqliteDatabase('child2.db')

        class FakeUser(Model):
            pass

        class ParentModel(Model):
            title = CharField()
            user = ForeignKeyField(FakeUser)

            class Meta:
                database = x_test_db

        class ChildModel(ParentModel):
            pass

        class ChildModel2(ParentModel):
            special_field = CharField()

            class Meta:
                database = child2_db

        class GrandChildModel(ChildModel):
            pass

        class GrandChildModel2(ChildModel2):
            special_field = TextField()

        self.assertEqual(ParentModel._meta.database.database, 'testing.db')
        self.assertEqual(ParentModel._meta.model_class, ParentModel)

        self.assertEqual(ChildModel._meta.database.database, 'testing.db')
        self.assertEqual(ChildModel._meta.model_class, ChildModel)
        self.assertEqual(sorted(ChildModel._meta.fields.keys()), [
            'id', 'title', 'user'
        ])

        self.assertEqual(ChildModel2._meta.database.database, 'child2.db')
        self.assertEqual(ChildModel2._meta.model_class, ChildModel2)
        self.assertEqual(sorted(ChildModel2._meta.fields.keys()), [
            'id', 'special_field', 'title', 'user'
        ])

        self.assertEqual(GrandChildModel._meta.database.database, 'testing.db')
        self.assertEqual(GrandChildModel._meta.model_class, GrandChildModel)
        self.assertEqual(sorted(GrandChildModel._meta.fields.keys()), [
            'id', 'title', 'user'
        ])

        self.assertEqual(GrandChildModel2._meta.database.database, 'child2.db')
        self.assertEqual(GrandChildModel2._meta.model_class, GrandChildModel2)
        self.assertEqual(sorted(GrandChildModel2._meta.fields.keys()), [
            'id', 'special_field', 'title', 'user'
        ])
        self.assertTrue(isinstance(GrandChildModel2._meta.fields['special_field'], TextField))


class ModelInheritanceTestCase(ModelTestCase):
    requires = [Blog, BlogTwo, User]

    def test_model_inheritance_attrs(self):
        self.assertEqual(Blog._meta.get_field_names(), ['pk', 'user', 'title', 'content', 'pub_date'])
        self.assertEqual(BlogTwo._meta.get_field_names(), ['pk', 'user', 'content', 'pub_date', 'title', 'extra_field'])

        self.assertEqual(Blog._meta.primary_key.name, 'pk')
        self.assertEqual(BlogTwo._meta.primary_key.name, 'pk')

        self.assertEqual(Blog.user.related_name, 'blog_set')
        self.assertEqual(BlogTwo.user.related_name, 'blogtwo_set')

        self.assertEqual(User.blog_set.rel_model, Blog)
        self.assertEqual(User.blogtwo_set.rel_model, BlogTwo)

        self.assertFalse(BlogTwo._meta.db_table == Blog._meta.db_table)

    def test_model_inheritance_flow(self):
        u = User.create(username='u')

        b = Blog.create(title='b', user=u)
        b2 = BlogTwo.create(title='b2', extra_field='foo', user=u)

        self.assertEqual(list(u.blog_set), [b])
        self.assertEqual(list(u.blogtwo_set), [b2])

        self.assertEqual(Blog.select().count(), 1)
        self.assertEqual(BlogTwo.select().count(), 1)

        b_from_db = Blog.get(Blog.pk==b.pk)
        b2_from_db = BlogTwo.get(BlogTwo.pk==b2.pk)

        self.assertEqual(b_from_db.user, u)
        self.assertEqual(b2_from_db.user, u)
        self.assertEqual(b2_from_db.extra_field, 'foo')


class DatabaseTestCase(BasePeeweeTestCase):
    def test_deferred_database(self):
        deferred_db = SqliteDatabase(None)
        self.assertTrue(deferred_db.deferred)

        class DeferredModel(Model):
            class Meta:
                database = deferred_db

        self.assertRaises(Exception, deferred_db.connect)
        sq = DeferredModel.select()
        self.assertRaises(Exception, sq.execute)

        deferred_db.init(':memory:')
        self.assertFalse(deferred_db.deferred)

        # connecting works
        conn = deferred_db.connect()
        DeferredModel.create_table()
        sq = DeferredModel.select()
        self.assertEqual(list(sq), [])

        deferred_db.init(None)
        self.assertTrue(deferred_db.deferred)

    def test_sql_error(self):
        bad_sql = 'select asdf from -1;'
        self.assertRaises(Exception, query_db.execute_sql, bad_sql)
        self.assertEqual(query_db.last_error, (bad_sql, None))

class _SqliteDateTestHelper(BasePeeweeTestCase):
    datetimes = [
        datetime.datetime(2000, 1, 2, 3, 4, 5),
        datetime.datetime(2000, 2, 3, 4, 5, 6),
    ]

    def create_date_model(self, date_fn):
        dp_db = SqliteDatabase(':memory:')
        class SqDp(Model):
            datetime_field = DateTimeField()
            date_field = DateField()
            time_field = TimeField()

            class Meta:
                database = dp_db

            @classmethod
            def date_query(cls, field, part):
                return (SqDp
                        .select(date_fn(field, part))
                        .tuples()
                        .order_by(SqDp.id))

        SqDp.create_table()

        for d in self.datetimes:
            SqDp.create(datetime_field=d, date_field=d.date(),
                        time_field=d.time())

        return SqDp

class SqliteDatePartTestCase(_SqliteDateTestHelper):
    def test_sqlite_date_part(self):
        date_fn = lambda field, part: fn.date_part(part, field)
        SqDp = self.create_date_model(date_fn)

        for part in ('year', 'month', 'day', 'hour', 'minute', 'second'):
            for i, dp in enumerate(SqDp.date_query(SqDp.datetime_field, part)):
                self.assertEqual(dp[0], getattr(self.datetimes[i], part))

        for part in ('year', 'month', 'day'):
            for i, dp in enumerate(SqDp.date_query(SqDp.date_field, part)):
                self.assertEqual(dp[0], getattr(self.datetimes[i], part))

        for part in ('hour', 'minute', 'second'):
            for i, dp in enumerate(SqDp.date_query(SqDp.time_field, part)):
                self.assertEqual(dp[0], getattr(self.datetimes[i], part))

        # ensure that the where clause works
        query = SqDp.select().where(fn.date_part('year', SqDp.datetime_field) == 2000)
        self.assertEqual(query.count(), 2)

        query = SqDp.select().where(fn.date_part('month', SqDp.datetime_field) == 1)
        self.assertEqual(query.count(), 1)
        query = SqDp.select().where(fn.date_part('month', SqDp.datetime_field) == 3)
        self.assertEqual(query.count(), 0)


class SqliteDateTruncTestCase(_SqliteDateTestHelper):
    def test_sqlite_date_trunc(self):
        date_fn = lambda field, part: fn.date_trunc(part, field)
        SqDp = self.create_date_model(date_fn)

        def assertQuery(field, part, expected):
            values = SqDp.date_query(field, part)
            self.assertEqual([r[0] for r in values], expected)

        assertQuery(SqDp.datetime_field, 'year', ['2000', '2000'])
        assertQuery(SqDp.datetime_field, 'month', ['2000-01', '2000-02'])
        assertQuery(SqDp.datetime_field, 'day', ['2000-01-02', '2000-02-03'])
        assertQuery(SqDp.datetime_field, 'hour', [
            '2000-01-02 03', '2000-02-03 04'])
        assertQuery(SqDp.datetime_field, 'minute', [
            '2000-01-02 03:04', '2000-02-03 04:05'])
        assertQuery(SqDp.datetime_field, 'second', [
            '2000-01-02 03:04:05', '2000-02-03 04:05:06'])


class AutoRollbackTestCase(ModelTestCase):
    requires = [User, Blog]

    def setUp(self):
        test_db.autorollback = True
        super(AutoRollbackTestCase, self).setUp()

    def tearDown(self):
        test_db.autorollback = False
        test_db.set_autocommit(True)
        super(AutoRollbackTestCase, self).tearDown()

    def test_auto_rollback(self):
        # Exceptions are still raised.
        self.assertRaises(IntegrityError, Blog.create)

        # The transaction should have been automatically rolled-back, allowing
        # us to create new objects (in a new transaction).
        u = User.create(username='u')
        self.assertTrue(u.id)

        # No-op, the previous INSERT was already committed.
        test_db.rollback()

        # Ensure we can get our user back.
        u_db = User.get(User.username == 'u')
        self.assertEqual(u.id, u_db.id)

    def test_transaction_ctx_mgr(self):
        'Only auto-rollback when autocommit is enabled.'
        def create_error():
            self.assertRaises(IntegrityError, Blog.create)

        # autocommit is disabled in a transaction ctx manager.
        with test_db.transaction():
            # Error occurs, but exception is caught, leaving the current txn
            # in a bad state.
            create_error()

            try:
                create_error()
            except Exception as exc:
                # Subsequent call will raise an InternalError with postgres.
                self.assertTrue(isinstance(exc, InternalError))
            else:
                self.assertFalse(database_class is PostgresqlDatabase)

        # New transactions are not affected.
        self.test_auto_rollback()

    def test_manual(self):
        test_db.set_autocommit(False)

        # Will not be rolled back.
        self.assertRaises(IntegrityError, Blog.create)

        if database_class is PostgresqlDatabase:
            self.assertRaises(InternalError, User.create, username='u')

        test_db.rollback()
        u = User.create(username='u')
        test_db.commit()
        u_db = User.get(User.username == 'u')
        self.assertEqual(u.id, u_db.id)


class CheckConstraintTestCase(ModelTestCase):
    requires = [CheckModel]

    def test_check_constraint(self):
        CheckModel.create(value=1)
        if isinstance(test_db, MySQLDatabase):
            # MySQL silently ignores all check constraints.
            CheckModel.create(value=0)
        else:
            with test_db.transaction() as txn:
                self.assertRaises(IntegrityError, CheckModel.create, value=0)
                txn.rollback()


class SQLAllTestCase(BasePeeweeTestCase):
    def setUp(self):
        super(SQLAllTestCase, self).setUp()
        fake_db = SqliteDatabase(':memory:')
        UniqueModel._meta.database = fake_db
        SeqModelA._meta.database = fake_db
        MultiIndexModel._meta.database = fake_db

    def tearDown(self):
        super(SQLAllTestCase, self).tearDown()
        UniqueModel._meta.database = test_db
        SeqModelA._meta.database = test_db
        MultiIndexModel._meta.database = test_db

    def test_sqlall(self):
        sql = UniqueModel.sqlall()
        self.assertEqual(sql, [
            ('CREATE TABLE "uniquemodel" ("id" INTEGER NOT NULL PRIMARY KEY, '
             '"name" VARCHAR(255) NOT NULL)'),
            'CREATE UNIQUE INDEX "uniquemodel_name" ON "uniquemodel" ("name")',
        ])

        sql = MultiIndexModel.sqlall()
        self.assertEqual(sql, [
            ('CREATE TABLE "multiindexmodel" ("id" INTEGER NOT NULL PRIMARY '
             'KEY, "f1" VARCHAR(255) NOT NULL, "f2" VARCHAR(255) NOT NULL, '
             '"f3" VARCHAR(255) NOT NULL)'),
            ('CREATE UNIQUE INDEX "multiindexmodel_f1_f2" ON "multiindexmodel"'
             ' ("f1", "f2")'),
            ('CREATE INDEX "multiindexmodel_f2_f3" ON "multiindexmodel" '
             '("f2", "f3")'),
        ])

        sql = SeqModelA.sqlall()
        self.assertEqual(sql, [
            ('CREATE TABLE "seqmodela" ("id" INTEGER NOT NULL PRIMARY KEY '
             'DEFAULT NEXTVAL(\'just_testing_seq\'), "num" INTEGER NOT NULL)'),
        ])


class LongIndexTestCase(BasePeeweeTestCase):
    def test_long_index(self):
        class LongIndexModel(TestModel):
            a123456789012345678901234567890 = CharField()
            b123456789012345678901234567890 = CharField()
            c123456789012345678901234567890 = CharField()

        fields = LongIndexModel._meta.get_fields()[1:]
        self.assertEqual(len(fields), 3)

        sql, params = compiler.create_index(LongIndexModel, fields, False)
        self.assertEqual(sql, (
            'CREATE INDEX "longindexmodel_85c2f7db5319d3c0c124a1594087a1cb" '
            'ON "longindexmodel" ('
            '"a123456789012345678901234567890", '
            '"b123456789012345678901234567890", '
            '"c123456789012345678901234567890")'
        ))


class ConnectionStateTestCase(BasePeeweeTestCase):
    def test_connection_state(self):
        conn = test_db.get_conn()
        self.assertFalse(test_db.is_closed())
        test_db.close()
        self.assertTrue(test_db.is_closed())
        conn = test_db.get_conn()
        self.assertFalse(test_db.is_closed())


class TopologicalSortTestCase(unittest.TestCase):
    def test_topological_sort_fundamentals(self):
        FKF = ForeignKeyField
        # we will be topo-sorting the following models
        class A(Model): pass
        class B(Model): a = FKF(A)              # must follow A
        class C(Model): a, b = FKF(A), FKF(B)   # must follow A and B
        class D(Model): c = FKF(C)              # must follow A and B and C
        class E(Model): e = FKF('self')
        # but excluding this model, which is a child of E
        class Excluded(Model): e = FKF(E)

        # property 1: output ordering must not depend upon input order
        repeatable_ordering = None
        for input_ordering in permutations([A, B, C, D, E]):
            output_ordering = sort_models_topologically(input_ordering)
            repeatable_ordering = repeatable_ordering or output_ordering
            self.assertEqual(repeatable_ordering, output_ordering)

        # property 2: output ordering must have same models as input
        self.assertEqual(len(output_ordering), 5)
        self.assertFalse(Excluded in output_ordering)

        # property 3: parents must precede children
        def assert_precedes(X, Y):
            lhs, rhs = map(output_ordering.index, [X, Y])
            self.assertTrue(lhs < rhs)
        assert_precedes(A, B)
        assert_precedes(B, C)  # if true, C follows A by transitivity
        assert_precedes(C, D)  # if true, D follows A and B by transitivity

        # property 4: independent model hierarchies must be in name order
        assert_precedes(A, E)

def permutations(xs):
    if not xs:
        yield []
    else:
        for y, ys in selections(xs):
            for pys in permutations(ys):
                yield [y] + pys

def selections(xs):
    for i in range(len(xs)):
        yield (xs[i], xs[:i] + xs[i + 1:])


if test_db.for_update:
    class ForUpdateTestCase(ModelTestCase):
        requires = [User]

        def tearDown(self):
            test_db.set_autocommit(True)

        def test_for_update(self):
            u1 = self.create_user('u1')
            u2 = self.create_user('u2')
            u3 = self.create_user('u3')

            test_db.set_autocommit(False)

            # select a user for update
            users = User.select().where(User.username == 'u1').for_update()
            updated = User.update(username='u1_edited').where(User.username == 'u1').execute()
            self.assertEqual(updated, 1)

            # open up a new connection to the database
            new_db = database_class(database_name, **database_params)

            # select the username, it will not register as being updated
            res = new_db.execute_sql('select username from users where id = %s;' % u1.id)
            username = res.fetchone()[0]
            self.assertEqual(username, 'u1')

            # committing will cause the lock to be released
            test_db.commit()

            # now we get the update
            res = new_db.execute_sql('select username from users where id = %s;' % u1.id)
            username = res.fetchone()[0]
            self.assertEqual(username, 'u1_edited')


elif TEST_VERBOSITY > 0:
    print_('Skipping "for update" tests')

if test_db.for_update_nowait:
    class ForUpdateNoWaitTestCase(ModelTestCase):
        requires = [User]

        def tearDown(self):
            test_db.set_autocommit(True)

        def test_for_update_exc(self):
            u1 = self.create_user('u1')
            test_db.set_autocommit(False)

            user = (User
                    .select()
                    .where(User.username == 'u1')
                    .for_update(nowait=True)
                    .execute())

            # Open up a second conn.
            new_db = database_class(database_name, **database_params)

            class User2(User):
                class Meta:
                    database = new_db
                    db_table = User._meta.db_table

            # Select the username -- it will raise an error.
            def try_lock():
                user2 = (User2
                         .select()
                         .where(User.username == 'u1')
                         .for_update(nowait=True)
                         .execute())
            self.assertRaises(OperationalError, try_lock)
            test_db.rollback()


elif TEST_VERBOSITY > 0:
    print_('Skipping "for update + nowait" tests')

if test_db.sequences:
    class SequenceTestCase(ModelTestCase):
        requires = [SeqModelA, SeqModelB]

        def test_sequence_shared(self):
            a1 = SeqModelA.create(num=1)
            a2 = SeqModelA.create(num=2)
            b1 = SeqModelB.create(other_num=101)
            b2 = SeqModelB.create(other_num=102)
            a3 = SeqModelA.create(num=3)

            self.assertEqual(a1.id, a2.id - 1)
            self.assertEqual(a2.id, b1.id - 1)
            self.assertEqual(b1.id, b2.id - 1)
            self.assertEqual(b2.id, a3.id - 1)

elif TEST_VERBOSITY > 0:
    print_('Skipping "sequence" tests')

if database_class is PostgresqlDatabase:
    class TestUnicodeConversion(ModelTestCase):
        requires = [User]

        def setUp(self):
            super(TestUnicodeConversion, self).setUp()

            # Create a user object with UTF-8 encoded username.
            ustr = ulit('Ísland')
            self.user = User.create(username=ustr)

        def tearDown(self):
            super(TestUnicodeConversion, self).tearDown()
            test_db.register_unicode = True
            test_db.close()

        def reset_encoding(self, encoding):
            test_db.close()
            conn = test_db.get_conn()
            conn.set_client_encoding(encoding)

        def test_unicode_conversion(self):
            # Per psycopg2's documentation, in Python2, strings are returned as
            # 8-bit str objects encoded in the client encoding. In python3,
            # the strings are automatically decoded in the connection encoding.

            # Turn off unicode conversion on a per-connection basis.
            test_db.register_unicode = False
            self.reset_encoding('LATIN1')

            u = User.get(User.id == self.user.id)
            if sys.version_info[0] < 3:
                self.assertFalse(u.username == self.user.username)
            else:
                self.assertTrue(u.username == self.user.username)

            test_db.register_unicode = True
            self.reset_encoding('LATIN1')

            u = User.get(User.id == self.user.id)
            self.assertEqual(u.username, self.user.username)

if test_db.savepoints:
    class TestSavepoints(ModelTestCase):
        requires = [User]

        def _outer(self, fail_outer=False, fail_inner=False):
            with test_db.savepoint():
                User.create(username='outer')
                try:
                    self._inner(fail_inner)
                except ValueError:
                    pass
                if fail_outer:
                    raise ValueError

        def _inner(self, fail_inner):
            with test_db.savepoint():
                User.create(username='inner')
                if fail_inner:
                    raise ValueError('failing')

        def assertNames(self, expected):
            query = User.select().order_by(User.username)
            self.assertEqual([u.username for u in query], expected)

        def test_success(self):
            with test_db.transaction():
                self._outer()
                self.assertEqual(User.select().count(), 2)
            self.assertNames(['inner', 'outer'])

        def test_inner_failure(self):
            with test_db.transaction():
                self._outer(fail_inner=True)
                self.assertEqual(User.select().count(), 1)
            self.assertNames(['outer'])

        def test_outer_failure(self):
            # Because the outer savepoint is rolled back, we'll lose the
            # inner savepoint as well.
            with test_db.transaction():
                self.assertRaises(ValueError, self._outer, fail_outer=True)
                self.assertEqual(User.select().count(), 0)

        def test_failure(self):
            with test_db.transaction():
                self.assertRaises(
                    ValueError, self._outer, fail_outer=True, fail_inner=True)
                self.assertEqual(User.select().count(), 0)


elif TEST_VERBOSITY > 0:
    print_('Skipping "savepoint" tests')

if test_db.foreign_keys:
    class ForeignKeyConstraintTestCase(ModelTestCase):
        requires = [User, Blog]

        def test_constraint_exists(self):
            # IntegrityError is raised when we specify a non-existent user_id.
            max_id = User.select(fn.Max(User.id)).scalar() or 0

            def will_fail():
                with test_db.transaction() as txn:
                    Blog.create(user=max_id + 1, title='testing')

            self.assertRaises(IntegrityError, will_fail)

        def test_constraint_creation(self):
            class FKC_a(TestModel):
                name = CharField()

            fkc_proxy = Proxy()

            class FKC_b(TestModel):
                fkc_a = ForeignKeyField(fkc_proxy)

            fkc_proxy.initialize(FKC_a)

            with test_db.transaction() as txn:
                FKC_b.drop_table(True)
                FKC_a.drop_table(True)
                FKC_a.create_table()
                FKC_b.create_table()

                # Foreign key constraint is not enforced.
                fb = FKC_b.create(fkc_a=-1000)
                fb.delete_instance()

                # Add constraint.
                test_db.create_foreign_key(FKC_b, FKC_b.fkc_a)

                def _trigger_exc():
                    with test_db.savepoint() as s1:
                        fb = FKC_b.create(fkc_a=-1000)

                self.assertRaises(IntegrityError, _trigger_exc)

                fa = FKC_a.create(name='fa')
                fb = FKC_b.create(fkc_a=fa)
                txn.rollback()


elif TEST_VERBOSITY > 0:
    print_('Skipping "foreign key" tests')

if test_db.drop_cascade:
    class DropCascadeTestCase(ModelTestCase):
        requires = [User, Blog]

        def test_drop_cascade(self):
            u1 = User.create(username='u1')
            b1 = Blog.create(user=u1, title='b1')

            User.drop_table(cascade=True)
            self.assertFalse(User.table_exists())

            # The constraint is dropped, we can create a blog for a non-
            # existant user.
            Blog.create(user=-1, title='b2')


elif TEST_VERBOSITY > 0:
    print_('Skipping "drop/cascade" tests')


if test_db.window_functions:
    class WindowFunctionTestCase(ModelTestCase):
        """Use int_field & float_field to test window queries."""
        requires = [NullModel]
        data = (
            # int / float -- we'll use int for grouping.
            (1, 10),
            (1, 20),
            (2, 1),
            (2, 3),
            (3, 100),
        )

        def setUp(self):
            super(WindowFunctionTestCase, self).setUp()
            for int_v, float_v in self.data:
                NullModel.create(int_field=int_v, float_field=float_v)

        def test_partition_unordered(self):
            query = (NullModel
                     .select(
                         NullModel.int_field,
                         NullModel.float_field,
                         fn.Avg(NullModel.float_field).over(
                             partition_by=[NullModel.int_field]))
                     .order_by(NullModel.id))

            self.assertEqual(list(query.tuples()), [
                (1, 10.0, 15.0),
                (1, 20.0, 15.0),
                (2, 1.0, 2.0),
                (2, 3.0, 2.0),
                (3, 100.0, 100.0),
            ])

        def test_ordered_unpartitioned(self):
            query = (NullModel
                     .select(
                         NullModel.int_field,
                         NullModel.float_field,
                         fn.rank().over(
                             order_by=[NullModel.float_field]))
                     .order_by(NullModel.id))

            self.assertEqual(list(query.tuples()), [
                (1, 10.0, 3),
                (1, 20.0, 4),
                (2, 1.0, 1),
                (2, 3.0, 2),
                (3, 100.0, 5),
            ])

        def test_ordered_partitioned(self):
            query = (NullModel
                     .select(
                         NullModel.int_field,
                         NullModel.float_field,
                         fn.rank().over(
                             partition_by=[NullModel.int_field],
                             order_by=[NullModel.float_field.desc()]))
                     .order_by(NullModel.id))

            self.assertEqual(list(query.tuples()), [
                (1, 10.0, 2),
                (1, 20.0, 1),
                (2, 1.0, 2),
                (2, 3.0, 1),
                (3, 100.0, 1),
            ])

        def test_empty_over(self):
            query = (NullModel
                     .select(
                         NullModel.int_field,
                         NullModel.float_field,
                         fn.lag(NullModel.int_field, 1).over())
                     .order_by(NullModel.id))

            self.assertEqual(list(query.tuples()), [
                (1, 10.0, None),
                (1, 20.0, 1),
                (2, 1.0, 1),
                (2, 3.0, 2),
                (3, 100.0, 2),
            ])

        def test_docs_example(self):
            NullModel.delete().execute()  # Clear out the table.

            curr_dt = datetime.datetime(2014, 1, 1)
            one_day = datetime.timedelta(days=1)
            for i in range(3):
                for j in range(i + 1):
                    NullModel.create(int_field=i, datetime_field=curr_dt)
                curr_dt += one_day

            query = (NullModel
                     .select(
                         NullModel.int_field,
                         NullModel.datetime_field,
                         fn.Count(NullModel.id).over(
                             partition_by=[fn.date_trunc(
                                 'day', NullModel.datetime_field)]))
                     .order_by(NullModel.id))

            self.assertEqual(list(query.tuples()), [
                (0, datetime.datetime(2014, 1, 1), 1),
                (1, datetime.datetime(2014, 1, 2), 2),
                (1, datetime.datetime(2014, 1, 2), 2),
                (2, datetime.datetime(2014, 1, 3), 3),
                (2, datetime.datetime(2014, 1, 3), 3),
                (2, datetime.datetime(2014, 1, 3), 3),
            ])


elif TEST_VERBOSITY > 0:
    print_('Skipping "window function" tests')

########NEW FILE########
