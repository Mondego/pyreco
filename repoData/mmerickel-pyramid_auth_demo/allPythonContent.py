__FILENAME__ = demo
import urllib

from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.config import Configurator
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPNotFound
from pyramid.security import authenticated_userid
from pyramid.security import forget
from pyramid.security import remember
from pyramid.view import forbidden_view_config
from pyramid.view import view_config

### DEFINE MODEL
class User(object):
    def __init__(self, login, password, groups=None):
        self.login = login
        self.password = password
        self.groups = groups or []

    def check_password(self, passwd):
        return self.password == passwd

class Page(object):
    def __init__(self, title, uri, body, owner):
        self.title = title
        self.uri = uri
        self.body = body
        self.owner = owner

def websafe_uri(txt):
    uri = txt.replace(' ', '-')
    return urllib.quote(uri)

### INITIALIZE MODEL
USERS = {}
PAGES = {}

def _make_demo_user(login, **kw):
    kw.setdefault('password', login)
    USERS[login] = User(login, **kw)
    return USERS[login]

_make_demo_user('luser')
_make_demo_user('editor', groups=['editors'])
_make_demo_user('admin', groups=['admin'])

def _make_demo_page(title, **kw):
    uri = kw.setdefault('uri', websafe_uri(title))
    PAGES[uri] = Page(title, **kw)
    return PAGES[uri]

_make_demo_page('hello', owner='luser',
                body='''
<h3>Hello World!</h3><p>I'm the body text</p>''')

### DEFINE VIEWS
@forbidden_view_config()
def forbidden_view(request):
    # do not allow a user to login if they are already logged in
    if authenticated_userid(request):
        return HTTPForbidden()

    loc = request.route_url('login', _query=(('next', request.path),))
    return HTTPFound(location=loc)

@view_config(
    route_name='home',
    renderer='home.mako',
)
def home_view(request):
    login = authenticated_userid(request)
    user = USERS.get(login)

    return {
        'user': user,
        'user_pages': [p for (t, p) in PAGES.iteritems() if p.owner == login],
    }

@view_config(
    route_name='login',
    renderer='login.mako',
)
def login_view(request):
    next = request.params.get('next') or request.route_url('home')
    login = ''
    did_fail = False
    if 'submit' in request.POST:
        login = request.POST.get('login', '')
        passwd = request.POST.get('passwd', '')

        user = USERS.get(login, None)
        if user and user.check_password(passwd):
            headers = remember(request, login)
            return HTTPFound(location=next, headers=headers)
        did_fail = True

    return {
        'login': login,
        'next': next,
        'failed_attempt': did_fail,
        'users': USERS,
    }

@view_config(
    route_name='logout',
)
def logout_view(request):
    headers = forget(request)
    loc = request.route_url('home')
    return HTTPFound(location=loc, headers=headers)

@view_config(
    route_name='users',
    renderer='users.mako',
)
def users_view(request):
    return {
        'users': sorted(USERS.keys()),
    }

@view_config(
    route_name='user',
    renderer='user.mako',
)
def user_view(request):
    login = request.matchdict['login']
    user = USERS.get(login)
    if not user:
        raise HTTPNotFound()

    pages = [p for (t, p) in PAGES.iteritems() if p.owner == login]

    return {
        'user': user,
        'pages': pages,
    }

@view_config(
    route_name='pages',
    renderer='pages.mako',
)
def pages_view(request):
    return {
        'pages': PAGES.values(),
    }

@view_config(
    route_name='page',
    renderer='page.mako',
)
def page_view(request):
    uri = request.matchdict['title']
    page = PAGES.get(uri)
    if not page:
        raise HTTPNotFound()

    return {
        'page': page,
    }

def validate_page(title, body):
    errors = []

    title = title.strip()
    if not title:
        errors.append('Title may not be empty')
    elif len(title) > 32:
        errors.append('Title may not be longer than 32 characters')

    body = body.strip()
    if not body:
        errors.append('Body may not be empty')

    return {
        'title': title,
        'body': body,
        'errors': errors,
    }

@view_config(
    route_name='create_page',
    renderer='edit_page.mako',
)
def create_page_view(request):
    owner = authenticated_userid(request)
    if owner is None:
        raise HTTPForbidden()

    errors = []
    body = title = ''
    if request.method == 'POST':
        title = request.POST.get('title', '')
        body = request.POST.get('body', '')

        v = validate_page(title, body)
        title = v['title']
        body = v['body']
        errors += v['errors']

        if not errors:
            page = _make_demo_page(title, owner=owner, body=body)
            url = request.route_url('page', title=page.uri)
            return HTTPFound(location=url)

    return {
        'title': title,
        'owner': owner,
        'body': body,
        'errors': errors,
    }

@view_config(
    route_name='edit_page',
    renderer='edit_page.mako',
)
def edit_page_view(request):
    uri = request.matchdict['title']
    page = PAGES.get(uri)
    if not page:
        raise HTTPNotFound()

    errors = []
    title = page.title
    body = page.body
    if request.method == 'POST':
        title = request.POST.get('title', '')
        body = request.POST.get('body', '')

        v = validate_page(title, body)
        title = v['title']
        body = v['body']
        errors += v['errors']

        if not errors:
            del PAGES[uri]
            page.title = title
            page.body = body
            page.uri = websafe_uri(title)
            PAGES[page.uri] = page
            url = request.route_url('page', title=page.uri)
            return HTTPFound(location=url)

    return {
        'title': title,
        'owner': page.owner,
        'body': body,
        'errors': errors,
    }

### CONFIGURE PYRAMID
def main(global_settings, **settings):
    authn_policy = AuthTktAuthenticationPolicy(
        settings['auth.secret'],
    )
    authz_policy = ACLAuthorizationPolicy()

    config = Configurator(
        settings=settings,
        authentication_policy=authn_policy,
        authorization_policy=authz_policy,
    )

    config.add_route('home', '/')
    config.add_route('login', '/login')
    config.add_route('logout', '/logout')

    config.add_route('users', '/users')
    config.add_route('user', '/user/{login}')

    config.add_route('pages', '/pages')
    config.add_route('create_page', '/create_page')
    config.add_route('page', '/page/{title}')
    config.add_route('edit_page', '/page/{title}/edit')

    config.scan(__name__)
    return config.make_wsgi_app()

### SIMPLE STARTUP
if __name__ == '__main__':
    settings = {
        'auth.secret': 'seekrit',
        'mako.directories': '%s:templates' % __name__,
    }
    app = main({}, **settings)

    from wsgiref.simple_server import make_server
    server = make_server('0.0.0.0', 5000, app)
    server.serve_forever()

########NEW FILE########
__FILENAME__ = demo
import urllib

from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.config import Configurator
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPNotFound
from pyramid.security import ALL_PERMISSIONS
from pyramid.security import Allow
from pyramid.security import Authenticated
from pyramid.security import authenticated_userid
from pyramid.security import forget
from pyramid.security import remember
from pyramid.view import forbidden_view_config
from pyramid.view import view_config

### DEFINE MODEL
class User(object):
    def __init__(self, login, password, groups=None):
        self.login = login
        self.password = password
        self.groups = groups or []

    def check_password(self, passwd):
        return self.password == passwd

class Page(object):
    def __init__(self, title, uri, body, owner):
        self.title = title
        self.uri = uri
        self.body = body
        self.owner = owner

def websafe_uri(txt):
    uri = txt.replace(' ', '-')
    return urllib.quote(uri)

### INITIALIZE MODEL
USERS = {}
PAGES = {}

def _make_demo_user(login, **kw):
    kw.setdefault('password', login)
    USERS[login] = User(login, **kw)
    return USERS[login]

_make_demo_user('luser')
_make_demo_user('editor', groups=['editor'])
_make_demo_user('admin', groups=['admin'])

def _make_demo_page(title, **kw):
    uri = kw.setdefault('uri', websafe_uri(title))
    PAGES[uri] = Page(title, **kw)
    return PAGES[uri]

_make_demo_page('hello', owner='luser',
                body='''
<h3>Hello World!</h3><p>I'm the body text</p>''')

### MAP GROUPS TO PERMISSIONS
class Root(object):
    __acl__ = [
        (Allow, Authenticated, 'create'),
        (Allow, 'g:editor', 'edit'),
        (Allow, 'g:admin', ALL_PERMISSIONS),
    ]

    def __init__(self, request):
        self.request = request

def groupfinder(userid, request):
    user = USERS.get(userid)
    if user:
        return ['g:%s' % g for g in user.groups]

### DEFINE VIEWS
@forbidden_view_config()
def forbidden_view(request):
    # do not allow a user to login if they are already logged in
    if authenticated_userid(request):
        return HTTPForbidden()

    loc = request.route_url('login', _query=(('next', request.path),))
    return HTTPFound(location=loc)

@view_config(
    route_name='home',
    renderer='home.mako',
)
def home_view(request):
    login = authenticated_userid(request)
    user = USERS.get(login)

    return {
        'user': user,
        'user_pages': [p for (t, p) in PAGES.iteritems() if p.owner == login],
    }

@view_config(
    route_name='login',
    renderer='login.mako',
)
def login_view(request):
    next = request.params.get('next') or request.route_url('home')
    login = ''
    did_fail = False
    if 'submit' in request.POST:
        login = request.POST.get('login', '')
        passwd = request.POST.get('passwd', '')

        user = USERS.get(login, None)
        if user and user.check_password(passwd):
            headers = remember(request, login)
            return HTTPFound(location=next, headers=headers)
        did_fail = True

    return {
        'login': login,
        'next': next,
        'failed_attempt': did_fail,
        'users': USERS,
    }

@view_config(
    route_name='logout',
)
def logout_view(request):
    headers = forget(request)
    loc = request.route_url('home')
    return HTTPFound(location=loc, headers=headers)

@view_config(
    route_name='users',
    permission='admin',
    renderer='users.mako',
)
def users_view(request):
    return {
        'users': sorted(USERS.keys()),
    }

@view_config(
    route_name='user',
    permission='admin',
    renderer='user.mako',
)
def user_view(request):
    login = request.matchdict['login']
    user = USERS.get(login)
    if not user:
        raise HTTPNotFound()

    pages = [p for (t, p) in PAGES.iteritems() if p.owner == login]

    return {
        'user': user,
        'pages': pages,
    }

@view_config(
    route_name='pages',
    renderer='pages.mako',
)
def pages_view(request):
    return {
        'pages': PAGES.values(),
    }

@view_config(
    route_name='page',
    renderer='page.mako',
)
def page_view(request):
    uri = request.matchdict['title']
    page = PAGES.get(uri)
    if not page:
        raise HTTPNotFound()

    return {
        'page': page,
    }

def validate_page(title, body):
    errors = []

    title = title.strip()
    if not title:
        errors.append('Title may not be empty')
    elif len(title) > 32:
        errors.append('Title may not be longer than 32 characters')

    body = body.strip()
    if not body:
        errors.append('Body may not be empty')

    return {
        'title': title,
        'body': body,
        'errors': errors,
    }

@view_config(
    route_name='create_page',
    permission='create',
    renderer='edit_page.mako',
)
def create_page_view(request):
    owner = authenticated_userid(request)

    errors = []
    body = title = ''
    if request.method == 'POST':
        title = request.POST.get('title', '')
        body = request.POST.get('body', '')

        v = validate_page(title, body)
        title = v['title']
        body = v['body']
        errors += v['errors']

        if not errors:
            page = _make_demo_page(title, owner=owner, body=body)
            url = request.route_url('page', title=page.uri)
            return HTTPFound(location=url)

    return {
        'title': title,
        'owner': owner,
        'body': body,
        'errors': errors,
    }

@view_config(
    route_name='edit_page',
    permission='edit',
    renderer='edit_page.mako',
)
def edit_page_view(request):
    uri = request.matchdict['title']
    page = PAGES.get(uri)
    if not page:
        raise HTTPNotFound()

    errors = []
    title = page.title
    body = page.body
    if request.method == 'POST':
        title = request.POST.get('title', '')
        body = request.POST.get('body', '')

        v = validate_page(title, body)
        title = v['title']
        body = v['body']
        errors += v['errors']

        if not errors:
            del PAGES[uri]
            page.title = title
            page.body = body
            page.uri = websafe_uri(title)
            PAGES[page.uri] = page
            url = request.route_url('page', title=page.uri)
            return HTTPFound(location=url)

    return {
        'title': title,
        'owner': page.owner,
        'body': body,
        'errors': errors,
    }

### CONFIGURE PYRAMID
def main(global_settings, **settings):
    authn_policy = AuthTktAuthenticationPolicy(
        settings['auth.secret'],
        callback=groupfinder,
    )
    authz_policy = ACLAuthorizationPolicy()

    config = Configurator(
        settings=settings,
        authentication_policy=authn_policy,
        authorization_policy=authz_policy,
        root_factory=Root,
    )

    config.add_route('home', '/')
    config.add_route('login', '/login')
    config.add_route('logout', '/logout')

    config.add_route('users', '/users')
    config.add_route('user', '/user/{login}')

    config.add_route('pages', '/pages')
    config.add_route('create_page', '/create_page')
    config.add_route('page', '/page/{title}')
    config.add_route('edit_page', '/page/{title}/edit')

    config.scan(__name__)
    return config.make_wsgi_app()

### SIMPLE STARTUP
if __name__ == '__main__':
    settings = {
        'auth.secret': 'seekrit',
        'mako.directories': '%s:templates' % __name__,
    }
    app = main({}, **settings)

    from wsgiref.simple_server import make_server
    server = make_server('0.0.0.0', 5000, app)
    server.serve_forever()

########NEW FILE########
__FILENAME__ = demo
import urllib

from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.config import Configurator
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPFound
from pyramid.security import ALL_PERMISSIONS
from pyramid.security import Allow
from pyramid.security import Authenticated
from pyramid.security import authenticated_userid
from pyramid.security import Everyone
from pyramid.security import forget
from pyramid.security import remember
from pyramid.view import forbidden_view_config
from pyramid.view import view_config

### DEFINE MODEL
class User(object):
    @property
    def __acl__(self):
        return [
            (Allow, self.login, 'view'),
        ]

    def __init__(self, login, password, groups=None):
        self.login = login
        self.password = password
        self.groups = groups or []

    def check_password(self, passwd):
        return self.password == passwd

class Page(object):
    @property
    def __acl__(self):
        return [
            (Allow, self.owner, 'edit'),
            (Allow, 'g:editor', 'edit'),
        ]

    def __init__(self, title, uri, body, owner):
        self.title = title
        self.uri = uri
        self.body = body
        self.owner = owner

def websafe_uri(txt):
    uri = txt.replace(' ', '-')
    return urllib.quote(uri)

### INITIALIZE MODEL
USERS = {}
PAGES = {}

def _make_demo_user(login, **kw):
    kw.setdefault('password', login)
    USERS[login] = User(login, **kw)
    return USERS[login]

_make_demo_user('luser')
_make_demo_user('editor', groups=['editor'])
_make_demo_user('admin', groups=['admin'])

def _make_demo_page(title, **kw):
    uri = kw.setdefault('uri', websafe_uri(title))
    PAGES[uri] = Page(title, **kw)
    return PAGES[uri]

_make_demo_page('hello', owner='luser',
                body='''
<h3>Hello World!</h3><p>I'm the body text</p>''')

### MAP GROUPS TO PERMISSIONS
class RootFactory(object):
    __acl__ = [
        (Allow, 'g:admin', ALL_PERMISSIONS),
    ]

    def __init__(self, request):
        self.request = request

class UserFactory(object):
    __acl__ = [
        (Allow, 'g:admin', ALL_PERMISSIONS),
    ]

    def __init__(self, request):
        self.request = request

    def __getitem__(self, key):
        user = USERS[key]
        user.__parent__ = self
        user.__name__ = key
        return user

class PageFactory(object):
    __acl__ = [
        (Allow, Everyone, 'view'),
        (Allow, Authenticated, 'create'),
    ]

    def __init__(self, request):
        self.request = request

    def __getitem__(self, key):
        page = PAGES[key]
        page.__parent__ = self
        page.__name__ = key
        return page

def groupfinder(userid, request):
    user = USERS.get(userid)
    if user:
        return ['g:%s' % g for g in user.groups]

### DEFINE VIEWS
@forbidden_view_config()
def forbidden_view(request):
    # do not allow a user to login if they are already logged in
    if authenticated_userid(request):
        return HTTPForbidden()

    loc = request.route_url('login', _query=(('next', request.path),))
    return HTTPFound(location=loc)

@view_config(
    route_name='home',
    renderer='home.mako',
)
def home_view(request):
    login = authenticated_userid(request)
    user = USERS.get(login)

    return {
        'user': user,
        'user_pages': [p for (t, p) in PAGES.iteritems() if p.owner == login],
    }

@view_config(
    route_name='login',
    renderer='login.mako',
)
def login_view(request):
    next = request.params.get('next') or request.route_url('home')
    login = ''
    did_fail = False
    if 'submit' in request.POST:
        login = request.POST.get('login', '')
        passwd = request.POST.get('passwd', '')

        user = USERS.get(login, None)
        if user and user.check_password(passwd):
            headers = remember(request, login)
            return HTTPFound(location=next, headers=headers)
        did_fail = True

    return {
        'login': login,
        'next': next,
        'failed_attempt': did_fail,
        'users': USERS,
    }

@view_config(
    route_name='logout',
)
def logout_view(request):
    headers = forget(request)
    loc = request.route_url('home')
    return HTTPFound(location=loc, headers=headers)

@view_config(
    route_name='users',
    permission='view',
    renderer='users.mako',
)
def users_view(request):
    return {
        'users': sorted(USERS.keys()),
    }

@view_config(
    route_name='user',
    permission='view',
    renderer='user.mako',
)
def user_view(request):
    user = request.context
    pages = [p for (t, p) in PAGES.iteritems() if p.owner == user.login]

    return {
        'user': user,
        'pages': pages,
    }

@view_config(
    route_name='pages',
    permission='view',
    renderer='pages.mako',
)
def pages_view(request):
    return {
        'pages': PAGES.values(),
    }

@view_config(
    route_name='page',
    permission='view',
    renderer='page.mako',
)
def page_view(request):
    page = request.context

    return {
        'page': page,
    }

def validate_page(title, body):
    errors = []

    title = title.strip()
    if not title:
        errors.append('Title may not be empty')
    elif len(title) > 32:
        errors.append('Title may not be longer than 32 characters')

    body = body.strip()
    if not body:
        errors.append('Body may not be empty')

    return {
        'title': title,
        'body': body,
        'errors': errors,
    }

@view_config(
    route_name='create_page',
    permission='create',
    renderer='edit_page.mako',
)
def create_page_view(request):
    owner = authenticated_userid(request)

    errors = []
    body = title = ''
    if request.method == 'POST':
        title = request.POST.get('title', '')
        body = request.POST.get('body', '')

        v = validate_page(title, body)
        title = v['title']
        body = v['body']
        errors += v['errors']

        if not errors:
            page = _make_demo_page(title, owner=owner, body=body)
            url = request.route_url('page', title=page.uri)
            return HTTPFound(location=url)

    return {
        'title': title,
        'owner': owner,
        'body': body,
        'errors': errors,
    }

@view_config(
    route_name='edit_page',
    permission='edit',
    renderer='edit_page.mako',
)
def edit_page_view(request):
    uri = request.matchdict['title']
    page = request.context

    errors = []
    title = page.title
    body = page.body
    if request.method == 'POST':
        title = request.POST.get('title', '')
        body = request.POST.get('body', '')

        v = validate_page(title, body)
        title = v['title']
        body = v['body']
        errors += v['errors']

        if not errors:
            del PAGES[uri]
            page.title = title
            page.body = body
            page.uri = websafe_uri(title)
            PAGES[page.uri] = page
            url = request.route_url('page', title=page.uri)
            return HTTPFound(location=url)

    return {
        'title': title,
        'owner': page.owner,
        'body': body,
        'errors': errors,
    }

### CONFIGURE PYRAMID
def main(global_settings, **settings):
    authn_policy = AuthTktAuthenticationPolicy(
        settings['auth.secret'],
        callback=groupfinder,
    )
    authz_policy = ACLAuthorizationPolicy()

    config = Configurator(
        settings=settings,
        authentication_policy=authn_policy,
        authorization_policy=authz_policy,
        root_factory=RootFactory,
    )

    config.add_route('home', '/')
    config.add_route('login', '/login')
    config.add_route('logout', '/logout')

    config.add_route('users', '/users', factory=UserFactory)
    config.add_route('user', '/user/{login}', factory=UserFactory,
                     traverse='/{login}')

    config.add_route('pages', '/pages', factory=PageFactory)
    config.add_route('create_page', '/create_page', factory=PageFactory)
    config.add_route('page', '/page/{title}', factory=PageFactory,
                     traverse='/{title}')
    config.add_route('edit_page', '/page/{title}/edit', factory=PageFactory,
                     traverse='/{title}')

    config.scan(__name__)
    return config.make_wsgi_app()

### SIMPLE STARTUP
if __name__ == '__main__':
    settings = {
        'auth.secret': 'seekrit',
        'mako.directories': '%s:templates' % __name__,
    }
    app = main({}, **settings)

    from wsgiref.simple_server import make_server
    server = make_server('0.0.0.0', 5000, app)
    server.serve_forever()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# pyramid_auth_demo documentation build configuration file
#
# This file is execfile()d with the current directory set to its containing
# dir.
#
# The contents of this file are pickled, so don't put values in the
# namespace that aren't pickleable (module imports are okay, they're
# removed automatically).
#
# All configuration values have a default value; values that are commented
# out serve to show the default value.

# If your extensions are in another directory, add it here. If the
# directory is relative to the documentation root, use os.path.abspath to
# make it absolute, like shown here.
#sys.path.append(os.path.abspath('some/directory'))

import sys
import os

# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['.templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'pyramid_auth_demo'
copyright = '2011, Michael Merickel'

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = '1.0'
# The full version, including alpha/beta/rc tags.
release = version

# There are two options for replacing |today|: either, you set today to
# some non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_themes/README.rst',]

# List of directories, relative to source directories, that shouldn't be
# searched for source files.
#exclude_dirs = []

# The reST default role (used for this markup: `text`) to use for all
# documents.
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
#pygments_style = 'sphinx'


# Options for HTML output
# -----------------------

# Add and use Pylons theme
if 'sphinx-build' in ' '.join(sys.argv): # protect against dumb importers
    from subprocess import call, Popen, PIPE

    p = Popen('which git', shell=True, stdout=PIPE)
    git = p.stdout.read().strip()
    cwd = os.getcwd()
    _themes = os.path.join(cwd, '_themes')

    if not os.path.isdir(_themes):
        call([git, 'clone', 'git://github.com/Pylons/pylons_sphinx_theme.git',
                '_themes'])
    else:
        os.chdir(_themes)
        call([git, 'checkout', 'master'])
        call([git, 'pull'])
        os.chdir(cwd)

# Add and use Pylons theme
sys.path.append(os.path.abspath('_themes'))
html_theme_path = ['_themes']
html_theme = 'pyramid'

html_theme_options = {
    'github_url': 'https://github.com/mmerickel/pyramid_auth_demo',
}

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
# html_style = 'repoze.css'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as
# html_title.
#html_short_title = None

# The name of an image file (within the static path) to place at the top of
# the sidebar.
# html_logo = '.static/logo_hi.gif'

# The name of an image file (within the static path) to use as favicon of
# the docs.  This file should be a Windows icon file (.ico) being 16x16 or
# 32x32 pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets)
# here, relative to this directory. They are copied after the builtin
# static files, so a file named "default.css" will overwrite the builtin
# "default.css".
#html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page
# bottom, using the given strftime format.
html_last_updated_fmt = '%b %d, %Y'

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

# If true, the reST sources are included in the HTML build as
# _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages
# will contain a <link> tag referring to it.  The value of this option must
# be the base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'atemplatedoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, document class [howto/manual]).
latex_documents = [
  ('index', 'pyramid_auth_demo.tex', 'pyramid_auth_demo Documentation',
   'Michael Merickel', 'manual'),
]

# The name of an image file (relative to this directory) to place at the
# top of the title page.
latex_logo = '.static/logo_hi.gif'

# For "manual" documents, if this is true, then toplevel headings are
# parts, not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
