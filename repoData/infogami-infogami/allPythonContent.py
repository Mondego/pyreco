__FILENAME__ = config
"""
Infogami configuration.
"""

import web

def get(name, default=None):
    return globals().get(name, default)

middleware = []

cache_templates = True
db_printing = False
db_kind = 'SQL'

db_parameters = None
infobase_host = None
site = "infogami.org"

plugins = ['links']

plugin_path = ['infogami.plugins']

# key for encrypting password
encryption_key = "ofu889e4i5kfem" 

# salt added to password before encrypting
password_salt = "zxps#2s4g@z"

from_address = "noreply@infogami.org"
smtp_server = "localhost"

login_cookie_name = "infogami_session"

infobase_parameters = dict(type='local')
bugfixer = None

admin_password = "admin123"


########NEW FILE########
__FILENAME__ = conftest

pytest_plugins = ["pytest_unittest"]

collect_ignore = ['failing']

def pytest_addoption(parser):
    parser.addoption("--runall", action="store_true", default=False)

def pytest_configure(config):
    if config.getvalue("runall"):
        collect_ignore[:] = []


########NEW FILE########
__FILENAME__ = code
import web
import os

import infogami
from infogami import utils, config
from infogami.utils import delegate, types
from infogami.utils.context import context
from infogami.utils.template import render
from infogami.utils.view import login_redirect, require_login, safeint, add_flash_message

import db
import forms
import helpers

from infogami.infobase.client import ClientException

def notfound(path):
    web.ctx.status = '404 Not Found'
    return render.notfound(path)

class view (delegate.mode):
    def GET(self, path):
        i = web.input(v=None)

        if i.v is not None and safeint(i.v, None) is None:
            raise web.seeother(web.changequery(v=None))

        p = db.get_version(path, i.v)
        if p is None:
            return notfound(path)
        elif p.type.key == '/type/delete':
            web.ctx.status = '404 Not Found'
            return render.viewpage(p)
        elif p.type.key == "/type/redirect" and p.location \
                and not p.location.startswith('http://') \
                and not p.location.startswith('://'):
            web.redirect(p.location)
        else:
            return render.viewpage(p)

class edit (delegate.mode):
    def GET(self, path):
        i = web.input(v=None, t=None)
        
        if not web.ctx.site.can_write(path):
            return render.permission_denied(web.ctx.fullpath, "Permission denied to edit " + path + ".")

        if i.v is not None and safeint(i.v, None) is None:
            raise web.seeother(web.changequery(v=None))
		        
        p = db.get_version(path, i.v) or db.new_version(path, types.guess_type(path))
        
        if i.t:
            type = db.get_type(i.t)
            if type is None:
                add_flash_message('error', 'Unknown type: ' + i.t)
            else:
                p.type = type 

        return render.editpage(p)


    def trim(self, d):
        """Trims empty value from d. 
        
        >>> trim = edit().trim

        >>> trim("hello ")
        'hello'
        >>> trim(['hello ', '', ' foo'])
        ['hello', 'foo']
        >>> trim({'x': '', 'y': 'foo'})
        {'y': 'foo'}
        >>> trim({'x': '', 'unique': 'foo'})
        >>> trim([{'x': '', 'y': 'foo'}, {'x': ''}])
        [{'y': 'foo'}]
        """
        if d is None:
            return d
        elif isinstance(d, list):
            d = [self.trim(x) for x in d]
            d = [x for x in d if x]
            return d
        elif isinstance(d, dict):
            for k, v in d.items():
                d[k] = self.trim(v)
                if d[k] is None or d[k] == '' or d[k] == []:
                    del d[k]

            # hack to stop saving empty properties
            if d.keys() == [] or d.keys() == ['unique']:
                return None
            else:
                return d
        else:
            return d.strip()
        
    def POST(self, path):
        i = web.input(_method='post')
        i = web.storage(helpers.unflatten(i))
        i.key = path
        
        _ = web.storage((k, i.pop(k)) for k in i.keys() if k.startswith('_'))
        action = self.get_action(_)
        comment = _.get('_comment', None)
        
        for k, v in i.items():
            i[k] = self.trim(v)
            
        p = web.ctx.site.get(path) or web.ctx.site.new(path, {})
        p.update(i)
        
        if action == 'preview':
            p['comment_'] = comment
            return render.editpage(p, preview=True)
        elif action == 'save':
            try:
                p._save(comment)
                path = web.input(_method='GET', redirect=None).redirect or web.changequery(query={})
                raise web.seeother(path)
            except (ClientException, db.ValidationException), e:            
                add_flash_message('error', str(e))
                p['comment_'] = comment                
                return render.editpage(p)
        elif action == 'delete':
            q = dict(key=i['key'], type=dict(key='/type/delete'))
            
            try:
                web.ctx.site.save(q, comment)
            except (ClientException, db.ValidationException), e:            
                add_flash_message('error', str(e))
                p['comment_'] = comment                
                return render.editpage(p)
            
            raise web.seeother(web.changequery(query={}))
    
    def get_action(self, i):
        """Finds the action from input."""
        if '_save' in i: return 'save'
        elif '_preview' in i: return 'preview'
        elif '_delete' in i: return 'delete'
        else: return None

class permission(delegate.mode):
    def GET(self, path):
        p = db.get_version(path)
        if not p:
            raise web.seeother(path)
        return render.permission(p)
        
    def POST(self, path):
        p = db.get_version(path)
        if not p:
            raise web.seeother(path)
            
        i = web.input('permission.key', 'child_permission.key')
        q = {
            'key': path,
            'permission': {
                'connect': 'update',
                'key': i['permission.key'] or None,
            },
            'child_permission': {
                'connect': 'update',
                'key': i['child_permission.key'] or None,
            }
        }
        
        try:
            web.ctx.site.write(q)
        except Exception, e:
            import traceback
            traceback.print_exc(e)
            add_flash_message('error', str(e))
            return render.permission(p)
    
        raise web.seeother(web.changequery({}, m='permission'))
            
class history (delegate.mode):
    def GET(self, path):
        page = web.ctx.site.get(path)
        if not page:
            raise web.seeother(path)
        i = web.input(page=0)
        offset = 20 * safeint(i.page)
        limit = 20
        history = db.get_recent_changes(key=path, limit=limit, offset=offset)
        return render.history(page, history)
        
class recentchanges(delegate.page):
    def GET(self):
        return render.recentchanges()
                
class diff (delegate.mode):
    def GET(self, path):  
        i = web.input(b=None, a=None)
        # default value of b is latest revision and default value of a is b-1
        
        def get(path, revision):
            if revision == 0:
                page = web.ctx.site.new(path, {'revision': 0, 'type': {'key': '/type/object'}, 'key': path})
            else:
                page = web.ctx.site.get(path, revision)
            return page
        
        def is_int(n):
            return n is None or safeint(n, None) is not None
            
        # if either or i.a or i.b is bad, then redirect to latest diff
        if not is_int(i.b) or not is_int(i.a):
            return web.redirect(web.changequery(b=None, a=None))

        b = get(path, safeint(i.b, None))

        # if the page is not there go to view page
        if b is None:
            raise web.seeother(web.changequery(query={}))
        
        a = get(path, max(1, safeint(i.a, b.revision-1)))
        return render.diff(a, b)

class login(delegate.page):
    path = "/account/login"
    
    def GET(self):
        referer = web.ctx.env.get('HTTP_REFERER', '/')
        i = web.input(redirect=referer)
        f = forms.login()
        f['redirect'].value = i.redirect 
        return render.login(f)

    def POST(self):
        i = web.input(remember=False, redirect='/')
        try:
            web.ctx.site.login(i.username, i.password, i.remember)
        except Exception, e:
            f = forms.login()
            f.fill(i)
            f.note = str(e)
            return render.login(f)

        if i.redirect == "/account/login" or i.redirect == "":
            i.redirect = "/"

        expires = (i.remember and 3600*24*7) or ""
        web.setcookie(config.login_cookie_name, web.ctx.conn.get_auth_token(), expires=expires)
        raise web.seeother(i.redirect)
        
class register(delegate.page):
    path = "/account/register"
    
    def GET(self):
        return render.register(forms.register())
        
    def POST(self):
        i = web.input(remember=False, redirect='/')
        f = forms.register()
        if not f.validates(i):
            return render.register(f)
        else:
            from infogami.infobase.client import ClientException
            try:
                web.ctx.site.register(i.username, i.displayname, i.email, i.password)
            except ClientException, e:
                f.note = str(e)
                return render.register(f)
            web.setcookie(config.login_cookie_name, web.ctx.conn.get_auth_token())
            raise web.seeother(i.redirect)

class logout(delegate.page):
    path = "/account/logout"
    
    def POST(self):
        web.setcookie(config.login_cookie_name, "", expires=-1)
        referer = web.ctx.env.get('HTTP_REFERER', '/')
        raise web.seeother(referer)

class forgot_password(delegate.page):
    path = "/account/forgot_password"

    def GET(self):
        f = forms.forgot_password()
        return render.forgot_password(f)
        
    def POST(self):
        i = web.input()
        f = forms.forgot_password()
        if not f.validates(i):
            return render.forgot_password(f)
        else:
            from infogami.infobase.client import ClientException
            try:
                delegate.admin_login()
                d = web.ctx.site.get_reset_code(i.email)
            except ClientException, e:
                f.note = str(e)
                web.ctx.headers = []
                return render.forgot_password(f)
            else:
                # clear the cookie set by delegate.admin_login
                # Otherwise user will be able to work as admin user.
                web.ctx.headers = []
                
            msg = render.password_mailer(web.ctx.home, d.username, d.code)            
            web.sendmail(config.from_address, i.email, msg.subject.strip(), str(msg))
            return render.passwordsent(i.email)

class reset_password(delegate.page):
    path = "/account/reset_password"
    def GET(self):
        f = forms.reset_password()
        return render.reset_password(f)
        
    def POST(self):
        i = web.input("code", "username")
        f = forms.reset_password()
        if not f.validates(i):
            return render.reset_password(f)
        else:
            try:
                web.ctx.site.reset_password(i.username, i.code, i.password)
                web.ctx.site.login(i.username, i.password, False)
                raise web.seeother('/')
            except Exception, e:
                return "Failed to reset password.<br/><br/> Reason: "  + str(e)
        
_preferences = []
def register_preferences(cls):
    _preferences.append((cls.title, cls.path))

class preferences(delegate.page):
    path = "/account/preferences"
    
    @require_login
    def GET(self):
        return render.preferences(_preferences)

class change_password(delegate.page):
    path = "/account/preferences/change_password"
    title = "Change Password"
    
    @require_login
    def GET(self):
        f = forms.login_preferences()
        return render.login_preferences(f)
        
    @require_login
    def POST(self):
        i = web.input("oldpassword", "password", "password2")
        f = forms.login_preferences()
        if not f.validates(i):
            return render.login_preferences(f)
        else:
            try:
                user = web.ctx.site.update_user(i.oldpassword, i.password, None)
            except ClientException, e:
                f.note = str(e)
                return render.login_preferences(f)
            add_flash_message('info', 'Password updated successfully.')
            raise web.seeother("/account/preferences")

register_preferences(change_password)

class getthings(delegate.page):
    """Lists all pages with name path/*"""
    def GET(self):
        i = web.input("type", property="key")
        q = {
            i.property + '~': i.q + '*',
            'type': i.type,
            'limit': int(i.limit)
        }
        things = [web.ctx.site.get(t, lazy=True) for t in web.ctx.site.things(q)]
        data = "\n".join("%s|%s" % (t[i.property], t.key) for t in things)
        raise web.HTTPError('200 OK', {}, data)
    
class favicon(delegate.page):
    path = "/favicon.ico"
    def GET(self):
        return web.redirect('/static/favicon.ico')

class feed(delegate.page):
    def _format_date(self, dt):
        """convert a datetime into an RFC 822 formatted date
        Input date must be in GMT.
        
        Source: PyRSS2Gen.py
        """
        # Looks like:
        #   Sat, 07 Sep 2002 00:00:01 GMT
        # Can't use strftime because that's locale dependent
        #
        # Isn't there a standard way to do this for Python?  The
        # rfc822 and email.Utils modules assume a timestamp.  The
        # following is based on the rfc822 module.
        return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (
                ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()],
                dt.day,
                ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                 "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][dt.month-1],
                dt.year, dt.hour, dt.minute, dt.second)
    
    def GET(self):
        i = web.input(key=None)
        changes = db.get_recent_changes(key=i.key, limit=50)
        site =  web.ctx.home

        def diff(key, revision):
            b = db.get_version(key, revision)

            rev_a = revision -1
            if rev_a is 0:
                a = web.ctx.site.new(key, {})
                a.revision = 0
            else: 
                a = db.get_version(key, revision=rev_a)
                
            diff = render.diff(a, b)

            #@@ dirty hack to extract diff table from diff
            import re
            rx = re.compile(r"^.*(<table.*<\/table>).*$", re.S)
            return rx.sub(r'\1', str(diff))
            
        web.header('Content-Type', 'application/rss+xml')

        for c in changes:
            c.diff = diff(c.key, c.revision)
            c.created = self._format_date(c.created)
        return delegate.RawText(render.feed(site, changes))

########NEW FILE########
__FILENAME__ = db
import web
import pickle

import infogami
from infogami.utils.view import public

def get_version(path, revision=None):
    return web.ctx.site.get(path, revision)

@public
def get_type(path):
    return get_version(path)
    
@public
def get_expected_type(page, property_name):
    """Returns the expected type of a property."""
    defaults = {
        "key": "/type/key",
        "type": "/type/type",
        "permission": "/type/permission",
        "child_permission": "/type/permission"
    }
    
    if property_name in defaults:
        return defaults[property_name]
    
    for p in page.type.properties:
        if p.name == property_name:
            return p.expected_type

    return "/type/string"
    
def new_version(path, type):
    if isinstance(type, basestring):
        type = get_type(type)
    
    assert type is not None
    return web.ctx.site.new(path, {'key': path, 'type': type})
    
@public
def get_i18n_page(page):
    key = page.key
    if key == '/':
	key = '/index'
    def get(lang):
       return lang and get_version(key + '.' + lang)
    return get(web.ctx.lang) or get('en') or None

class ValidationException(Exception): pass
    
def get_user_preferences(user):
    return get_version(user.key + '/preferences')
    
@public
def get_recent_changes(key=None, author=None, ip=None, type=None, bot=None, limit=None, offset=None):
    q = {'sort': '-created'}
    if key is not None:
        q['key'] = key

    if author:
        q['author'] = author.key

    if type:
        q['type'] = type

    if ip:
        q['ip'] = ip
        
    if bot is not None:
        q['bot'] = bot
    
    q['limit'] = limit or 100
    q['offset'] = offset or 0
    result = web.ctx.site.versions(q)
    for r in result:
        r.thing = web.ctx.site.get(r.key, r.revision, lazy=True)
    return result

@public
def list_pages(path, limit=100, offset=0):
    """Lists all pages with name path/*"""
    return _list_pages(path, limit=limit, offset=offset)
    
def _list_pages(path, limit, offset):
    q = {}
    if path != '/':
        q['key~'] = path + '/*'
    
    # don't show /type/delete and /type/redirect
    q['a:type!='] = '/type/delete'
    q['b:type!='] = '/type/redirect'
    
    q['sort'] = 'key'
    q['limit'] = limit
    q['offset'] = offset
    # queries are very slow with != conditions
    # q['type'] != '/type/delete'
    return [web.ctx.site.get(key, lazy=True) for key in web.ctx.site.things(q)]
                   
def get_things(typename, prefix, limit):
    """Lists all things whose names start with typename"""	
    q = {
        'key~': prefix + '*',
        'type': typename,
        'sort': 'key',
        'limit': limit
    }
    return [web.ctx.site.get(key, lazy=True) for key in web.ctx.site.things(q)]    
    

########NEW FILE########
__FILENAME__ = dbupgrade
"""
module for doing database upgrades when code changes. 
"""
import infogami
from infogami import tdb

from infogami.core import db
from infogami.utils.context import context as ctx

import web

def get_db_version():
    return tdb.root.d.get('__version__', 0)

upgrades = []
    
def upgrade(f):
    upgrades.append(f)
    return f

def apply_upgrades():
    from infogami import tdb
    tdb.transact()
    try:
        v = get_db_version()
        for u in upgrades[v:]:
            print >> web.debug, 'applying upgrade:', u.__name__
            u()
        
        mark_upgrades()
        tdb.commit()
        print >> web.debug, 'upgrade successful.'
    except:
        print >> web.debug, 'upgrade failed'
        import traceback
        traceback.print_exc()
        tdb.rollback()
        
@infogami.action        
def dbupgrade():
    apply_upgrades()
    
def mark_upgrades():
    tdb.root.__version__ = len(upgrades)
    tdb.root.save()

@upgrade    
def hash_passwords():
    from infogami.core import auth
    
    tuser = db.get_type(ctx.site, 'type/user')
    users = tdb.Things(parent=ctx.site, type=tuser).list()
    
    for u in users:
        try:
            preferences = u._c('preferences')
        except:
            # setup preferences for broken accounts, so that they can use forgot password.
            preferences = db.new_version(u, 'preferences', db.get_type(ctx.site,'type/thing'), dict(password=''))
            preferences.save()
        
        if preferences.password:
            auth.set_password(u, preferences.password)
    
@upgrade
def upgrade_types():
    from infogami.core.db import _create_type, tdbsetup
    
    tdbsetup()
    type = db.get_type(ctx.site, "type/type")
    types = tdb.Things(parent=ctx.site, type=type)
    types = [t for t in types if 'properties' not in t.d and 'is_primitive' not in t.d]
    primitives = dict(int='type/int', integer='type/int', string='type/string', text='type/text')

    newtypes = {}
    for t in types:
        properties = []
        backreferences = []
        print >> web.debug, t, t.d
        if t.name == 'type/site':
            continue
        for name, value in t.d.items():
            p = web.storage(name=name)
            typename = web.lstrips(value, "thing ")

            if typename.startswith('#'):
                typename, property_name = typename.lstrip('#').split('.')
                p.type = db.get_type(ctx.site, typename)
                p.property_name = property_name
                backreferences.append(p)
                continue
                
            if typename.endswith('*'):
                typename = typename[:-1]
                p.unique = False
            else:
                p.unique = True
            if typename in primitives:
                typename = primitives[typename]
            p.type = db.get_type(ctx.site, typename)
            properties.append(p)
        _create_type(ctx.site, t.name, properties, backreferences)

########NEW FILE########
__FILENAME__ = diff
import web
from difflib import SequenceMatcher

def better_diff(a, b):
    labels = dict(equal="", insert='add', replace='mod', delete='rem')

    map = []
    for tag, i1, i2, j1, j2 in SequenceMatcher(a=a, b=b).get_opcodes():
        n = (j2-j1) - (i2-i1)

        x = a[i1:i2]
        xn = range(i1, i2)
        y = b[j1:j2]
        yn = range(j1, j2)

        if tag == 'insert':
            x += [''] * n
            xn += [''] * n
        elif tag == 'delete':
            y += [''] * -n
            yn += [''] * -n
        elif tag == 'equal':
            if i2-i1 > 5:
                x = y = [a[i1], '', a[i2-1]]
                xn = yn = [i1, '...', i2-1]
        elif tag == 'replace':
            isize = i2-i1
            jsize = j2-j1

            if isize < jsize:
                x += [''] * (jsize-isize)
                xn += [''] * (jsize-isize)
            else:
                y += [''] * (isize-jsize)
                yn += [''] * (isize-jsize)

        map += zip([labels[tag]] * len(x), xn, x, yn, y)

    return map

def simple_diff(a, b):
    a = a or ''
    b = b or ''
    if a is None: a = ''
    if b is None: b = ''
    a = web.utf8(a).split(' ')
    b = web.utf8(b).split(' ')
    out = []
    for (tag, i1, i2, j1, j2) in SequenceMatcher(a=a, b=b).get_opcodes():
        out.append(web.storage(tag=tag, left=' '.join(a[i1:i2]), right=' '.join(b[j1:j2])))
    return out

########NEW FILE########
__FILENAME__ = forms
from web.form import *
import db
from infogami.utils import i18n
from infogami.utils.context import context

class BetterButton(Button):
    def render(self):
        label = self.attrs.get('label', self.name)
        safename = net.websafe(self.name)
        x = '<button name="%s"%s>%s</button>' % (safename, self.addatts(), label)
        return x

_ = i18n.strings.get_namespace('/account/login')

login = Form(
    Hidden('redirect'),
    Textbox('username', notnull, description=_.username),
    Password('password', notnull, description=_.password),
    Checkbox('remember', description=_.remember_me)
)

vlogin = regexp(r"^[A-Za-z0-9-_]{3,20}$", 'must be between 3 and 20 letters and numbers') 
vpass = regexp(r".{3,20}", 'must be between 3 and 20 characters')
vemail = regexp(r".*@.*", "must be a valid email address")
not_already_used = Validator('This email is already used', lambda email: db.get_user_by_email(context.site, email) is None)

_ = i18n.strings.get_namespace('/account/register')

register = Form(
    Textbox('username', 
            vlogin,
            description=_.username),
    Textbox('displayname', notnull, description=_.display_name),
    Textbox('email', notnull, vemail, description=_.email),
    Password('password', notnull, vpass, description=_.password),
    Password('password2', notnull, description=_.confirm_password),
    validators = [
        Validator(_.passwords_did_not_match, lambda i: i.password == i.password2)]    
)

_ = i18n.strings.get_namespace('/account/preferences')

login_preferences = Form(
    Password("oldpassword", notnull, description=_.current_password),
    Password("password", notnull, vpass, description=_.new_password),
    Password("password2", notnull, description=_.confirm_password),
    BetterButton("save", label=_.save),
    validators = [
        Validator(_.passwords_did_not_match, lambda i: i.password == i.password2)]
)

_ = i18n.strings.get_namespace('/account/forgot_password')

validemail = Validator(_.email_not_registered, 
                        lambda email: db.get_user_by_email(context.site, email))
forgot_password = Form(
    Textbox('email', notnull, vemail, description=_.email),
)

_register = i18n.strings.get_namespace('/account/register')
_preferences = i18n.strings.get_namespace('/account/preferences')

reset_password = Form(
    Password('password', notnull, vpass, description=_register.password),
    Password('password2', notnull, description=_register.confirm_password),
    BetterButton("save", label=_preferences.save),
    validators = [
        Validator(_register.passwords_did_not_match, lambda i: i.password == i.password2)]
)

########NEW FILE########
__FILENAME__ = helpers
"""
Generic Utilities.
"""
class xdict:
    """Dictionary wrapper to give sorted repr.
    Used for doctest.
    """
    def __init__(self, d):
        self.d = d

    def __repr__(self):
        def f(d):
            if isinstance(d, dict): return xdict(d)
            else: return d
        return '{' + ", ".join(["'%s': %s" % (k, f(v)) for k, v in sorted(self.d.items())]) + '}'

def flatten(d):
    """Make a dictionary flat.
    
    >>> d = {'a': 1, 'b': [2, 3], 'c': {'x': 4, 'y': 5}}
    >>> xdict(flatten(d))
    {'a': 1, 'b#0': 2, 'b#1': 3, 'c.x': 4, 'c.y': 5}
    """
    def traverse(d, prefix, delim, visit):
        for k, v in d.iteritems():
            k = str(k)
            if isinstance(v, dict):
                traverse(v, prefix + delim + k, '.', visit)
            elif isinstance(v, list):
                traverse(betterlist(v), prefix + delim + k, '#', visit)
            else:
                visit(prefix + delim + k, v)

    def visit(k, v):
        d2[k] = v

    d2 = {}
    traverse(d, "", "", visit)
    return d2
    
def unflatten(d):
    """Inverse of flatten.
    
    >>> xdict(unflatten({'a': 1, 'b#0': 2, 'b#1': 3, 'c.x': 4, 'c.y': 5}))
    {'a': 1, 'b': [2, 3], 'c': {'x': 4, 'y': 5}}
    >>> unflatten({'a#1#2.b': 1})
    {'a': [None, [None, None, {'b': 1}]]}
    """
    def setdefault(d, k, v):
        # error check: This can happen when d has both foo.x and foo as keys
        if not isinstance(d, (dict, betterlist)):
            return
            
        if '.' in k:
            a, b = k.split('.', 1)
            return setdefault(setdefault(d, a, {}), b, v)
        elif '#' in k:
            a, b = k.split('#', 1)
            return setdefault(setdefault(d, a, betterlist()), b, v)
        else: 
            return d.setdefault(k, v)

    d2 = {}
    for k, v in d.iteritems():
        setdefault(d2, k, v)
    return d2

class betterlist(list):
    """List with dict like setdefault method."""
    def fill(self, size):
        while len(self) < size:
            self.append(None)

    def setdefault(self, index, value):
        index = int(index)
        self.fill(index+1)
        if self[index] == None:
            self[index] = value
        return self[index]

    def iteritems(self):
        return enumerate(self)

    def items(self):
        return list(self.iteritems())

def trim(x):
    """Remove empty elements from a list or dictionary.
        
    >>> trim([2, 3, None, None, '', 42])
    [2, 3, 42]
    >>> trim([{'x': 1}, {'x': ''}, {'x': 3}])
    [{'x': 1}, {'x': 3}]
    >>> trim({'x': 1, 'y': '', 'z': ['a', '', 'b']})
    {'x': 1, 'z': ['a', 'b']}
    >>> trim(unflatten({'a#1#2.b': 1}))
    {'a': [[{'b': 1}]]}
    >>> trim(flatten(unflatten({'a#1#2.b': 1})))
    {'a#1#2.b': 1}
    """
    def trimlist(x):
        y = []
        for v in x:
            if isinstance(v, list): v = trimlist(v)
            elif isinstance(v, dict): v = trimdict(v)
            if v: y.append(v)
        return y
        
    def trimdict(x):
        y = {}
        for k, v in x.iteritems():
            if isinstance(v, list): v = trimlist(v)
            elif isinstance(v, dict): v = trimdict(v)
            if v: y[k] = v
        return y
    
    if isinstance(x, list): return trimlist(x)
    elif isinstance(x, dict): return trimdict(x)
    else: return x

def subdict(d, keys):
    """Subset like operation on dictionary.
    
    >>> subdict({'a': 1, 'b': 2, 'c': 3}, ['a', 'c'])
    {'a': 1, 'c': 3}
    >>> subdict({'a': 1, 'b': 2, 'c': 3}, ['a', 'c', 'd'])
    {'a': 1, 'c': 3}
    """
    return dict((k, d[k]) for k in keys if k in d)

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = account
import hmac
import random
import datetime
import time
import web
import logging
import simplejson

import common
import config

logger = logging.getLogger("infobase.account")

def get_user_root():
    user_root = config.get("user_root", "/user")
    return user_root.rstrip("/") + "/"

def make_query(user):
    q = [dict(user, permission={'key': user.key + '/permission'}),
    {
        'key': user.key + '/usergroup',
        'type': {'key': '/type/usergroup'},
        'members': [{'key': user.key}]
    }, 
    {
        'key': user.key + '/permission',
        'type': {'key': '/type/permission'},
        'readers': [{'key': '/usergroup/everyone'}],
        'writers': [{'key': user.key + '/usergroup'}],
        'admins': [{'key': user.key + '/usergroup'}]
    }]
    return q

def admin_only(f):
    """Decorator to limit a function to admin user only."""
    def g(self, *a, **kw):
        user = self.get_user()
        if user is None or user.key != get_user_root() + 'admin':
            raise common.PermissionDenied(message='Permission Denied')
        return f(self, *a, **kw)
    return g

class AccountManager:
    def __init__(self, site, secret_key):
        self.site = site
        self.secret_key = secret_key
        
    def register(self, username, email, password, data, _activate=False):
        logger.info("new account registration username=%s", username)
        enc_password = self._generate_salted_hash(self.secret_key, password)

        try:
            self.store_account_info(username, email, enc_password, data)
            if _activate:
                self.activate(username)
        except:
            logger.error("Failed to store registration info. username=%s", username, exc_info=True)
            raise

    def store_account_info(self, username, email, enc_password, data):
        """Store account info in the store so that the account can be created after verifying the email.
        """
        store = self.site.store.store
        
        account_key = "account/" + username
        email_key = "account-email/" + email
        
        if store.get(account_key):
            raise common.BadData(message="User already exists: %s" % username)

        if store.get(email_key):
            raise common.BadData(message='Email is already used: ' + email)

        now = datetime.datetime.utcnow()
        expires_on = now + datetime.timedelta(days=14) # 2 weeks

        account_doc = {
            "_key": account_key,
            "type": "account",
            "status": "pending",            
            "created_on": now.isoformat(),

            "username": username,
            "lusername": username.lower(), # lowercase username

            "email": email,
            "enc_password": enc_password,
            "data": data
        }
        email_doc = {
            "_key": email_key,
            "type": "account-email",
            "username": username
        }
        store.put_many([account_doc, email_doc])
    
    def activate(self, username):
        store = self.site.store.store
        account_key = "account/" + username

        doc = store.get(account_key)
        if doc:
            logger.info("activated account: %s", username)
            
            # update the status
            doc['status'] = 'active'
            store.put(account_key, doc)
            
            self._create_profile(username, doc.get('data', {}))
            return "ok"
        else:
            return "account_not_found"
            
    def _create_profile(self, username, data):
        key = get_user_root() + username
        
        if self.site.get(key):
            logger.warn("profile already created: %s", key)
            return
        else:
            web.ctx.disable_permission_check = True

            user_doc = web.storage({"key": key, "type": {"key": "/type/user"}})
            user_doc.update(data)

            q = make_query(user_doc)
            self.site.save_many(q, author=user_doc, action='new-account', comment="Created new account.")

    def login(self, username, password):
        """Returns "ok" on success and an error code on failure.

        Error code can be one of:
            * account_bad_password
            * account_not_found
            * account_not_verified
            * account_not_active
        """
        if username == 'admin':
            self.assert_trusted_machine()

        doc = self.site.store.store.get("account/" + username)
        return self._verify_login(doc, password)

    def _verify_login(self, doc, password):
        if not doc:
            return "account_not_found"

        if not self.verify_password(password, doc['enc_password']):
            return "account_bad_password"
        elif doc.get("status") == "pending":
            return "account_not_verified"
        else:
            return "ok"
    
    def update(self, username, **kw):
        account_key = "account/" + username
        store = self.site.store.store
        
        account = store.get(account_key)
        if not account:
            return "account_not_found"
        
        docs = []
        if 'email' in kw and kw['email'] != account['email']:
            email_doc = store.get("account-email/" + account['email'])
            email_doc['_delete'] = True
            docs.append(email_doc)
            
            new_email_doc = {
                "_key": "account-email/" + kw['email'],
                "type": "account-email",
                "username": username
            }
            docs.append(new_email_doc)
        
        if "password" in kw:
            raw_password = kw.pop("password")
            kw['enc_password'] = self.generate_hash(raw_password)
        
        account.update(kw)
        docs.append(account)
        store.put_many(docs)
        return "ok"
    
    def find_account(self, email=None, username=None):
        store = self.site.store.store
        
        if email:
            rows = store.query(type="account", name="email", value=email, include_docs=True)
            return rows and rows[0]['doc'] or None
        elif username:
            account_key = "account/" + username
            return store.get(account_key)
    
    def set_auth_token(self, user_key):
        t = datetime.datetime(*time.gmtime()[:6]).isoformat()
        text = "%s,%s" % (user_key, t)
        text += "," + self._generate_salted_hash(self.secret_key, text)
        web.ctx.infobase_auth_token = text

    #### Utilities
    
    def _generate_salted_hash(self, key, text, salt=None):
        salt = salt or hmac.HMAC(key, str(random.random())).hexdigest()[:5]
        hash = hmac.HMAC(key, web.utf8(salt) + web.utf8(text)).hexdigest()
        return '%s$%s' % (salt, hash)
        
    def _check_salted_hash(self, key, text, salted_hash):
        salt, hash = salted_hash.split('$', 1)
        return self._generate_salted_hash(key, text, salt) == salted_hash

    def checkpassword(self, username, raw_password):
        details = self.site.store.get_user_details(username)
        if details is None or details.get('active', True) == False:
            return False
        else:
            return self._check_salted_hash(self.secret_key, raw_password, details.password)
            
    def verify_password(self, raw_password, enc_password):
        """Verifies if the raw_password and encrypted password match."""
        return self._check_salted_hash(self.secret_key, raw_password, enc_password)
        
    def generate_hash(self, raw_password):
        return self._generate_salted_hash(self.secret_key, raw_password)

    #### Lagacy
    
    def find_user_by_email(self, email):
        """Returns key of the user with given email."""
        account = self.find_account(email=email)
        if account:
            return get_user_root() + account['_key'].split("/")[-1]
    
    def get_user(self):
        """Returns the current user from the session."""
        #@@ TODO: call assert_trusted_machine when user is admin.
        auth_token = web.ctx.get('infobase_auth_token')
        if auth_token:
            try:
                user_key, login_time, digest = auth_token.split(',')
            except ValueError:
                return
            if self._check_salted_hash(self.secret_key, user_key + "," + login_time, digest):
                return self.site._get_thing(user_key)
    
    #### Old, may be unused        

    def register1(self, username, email, enc_password, data, ip=None, timestamp=None):
        ip = ip or web.ctx.ip
        key = get_user_root() + username
        if self.site.get(key):
            raise common.BadData(message="User already exists: " + username)

        if self.site.store.find_user(email):
            raise common.BadData(message='Email is already used: ' + email)

        def f():
            web.ctx.disable_permission_check = True

            d = web.storage({"key": key, "type": {"key": "/type/user"}})
            d.update(data)
            self.site.save(key, d, timestamp=timestamp, author=d, comment="Created new account")

            q = make_query(d)
            account_bot = config.get('account_bot')
            account_bot = account_bot and web.storage({"key": account_bot, "type": {"key": "/type/user"}})
            self.site.save_many(q, ip=ip, timestamp=timestamp, author=account_bot, action='register', comment="Setup new account")
            self.site.store.register(key, email, enc_password)
            self.update_user_details(username, verified=True, active=True)

            # Add account doc to store
            olddoc = self.site.store.store.get("account/" + username) or {}
            
            doc = {
                "_key": "account/" + username,
                "_rev": olddoc.get("_rev"),
                "type": "account",
                "registered_on": olddoc['registered_on'],
                "activated_on": timestamp.isoformat(),
                "last_login": timestamp.isoformat(),
            }
            self.site.store.store.put("account/" + username, doc)

        timestamp = timestamp or datetime.datetime.utcnow()
        self.site.store.transact(f)

        event_data = dict(data, username=username, email=email, password=enc_password)
        self.site._fire_event("register", timestamp=timestamp, ip=ip or web.ctx.ip, username=None, data=event_data)

        self.set_auth_token(key)
        return username

    def _update(self, username, **kw):
        key = get_user_root() + username
        details = self.site.store.get_user_details(key)
        
        if not details:
            return "account_not_found"
        else:
            self.site.store.update_user_details(key, **kw)
            return "ok"
                        
    def update_user(self, old_password, new_password, email):
        user = self.get_user()
        if user is None:
            raise common.PermissionDenied(message="Not logged in")

        if not self.checkpassword(user.key, old_password):
            raise common.BadData(message='Invalid Password')
        
        new_password and self.assert_password(new_password)
        email and self.assert_email(email)
        
        enc_password = new_password and self._generate_salted_hash(self.secret_key, new_password)
        self.update_user1(user, enc_password, email)
        
    def update_user1(self, user, enc_password, email, ip=None, timestamp=None):
        self.site.store.update_user_details(user.key, email=email, password=enc_password)
        
        timestamp = timestamp or datetime.datetime.utcnow()
        event_data = dict(username=user.key, email=email, password=enc_password)
        self.site._fire_event("update_user", timestamp=timestamp, ip=ip or web.ctx.ip, username=None, data=event_data)
        
    def update_user_details(self, username, **params):
        """Update user details like email, active, bot, verified.
        """
        key = get_user_root() + username
        self.site.store.update_user_details(key, **params)
        
    def assert_password(self, password):
        pass
        
    def assert_email(self, email):
        pass

    def assert_trusted_machine(self):
        if web.ctx.ip not in config.trusted_machines:
            raise common.PermissionDenied(message='Permission denied to login as admin from ' + web.ctx.ip)
            
    @admin_only
    def get_user_email(self, username):
        logger.debug("get_user_email", username)
        
        if username.startswith("/"):
            # this is user key
            userkey = username
            username = username.split("/")[-1]
        else:
            userkey = get_user_root() + username
        
        details = self.site.store.get_user_details(username)
        
        logger.debug("get_user_email details %s %s", username, details)
        
        if details:
            return details.email
        
        doc = self.site.store.store.get("account/" + username)
        logger.debug("get_user_email doc %s", doc)
        
        if doc and doc.get("type") == "pending-account":
            return doc['email']
        
        raise common.BadData(message='No user registered with username: ' + username, error="account_not_found")
            
    def get_email(self, user):
        """Used internally by server."""
        details = self.site.store.get_user_details(user.key)
        return details.email

    @admin_only
    def get_user_code(self, email):
        """Returns a code for resetting password of a user."""
        
        key = self.site.store.find_user(email)
        if not key:
            raise common.UserNotFound(email=email)
            
        username = web.lstrips(key, get_user_root())
        details = self.site.store.get_user_details(key)

        # generate code by combining encrypt password and timestamp. 
        # encrypted_password for verification and timestamp for expriry check.
        timestamp = str(int(time.time()))
        text = details.password + '$' + timestamp
        return username, timestamp + '$' + self._generate_salted_hash(self.secret_key, text)
    
    def reset_password(self, username, code, password):
        self.check_reset_code(username, code)
        enc_password = self._generate_salted_hash(self.secret_key, password)
        self.site.store.update_user_details(get_user_root() + username, password=enc_password, verified=True)
            
    def check_reset_code(self, username, code):
        SEC_PER_WEEK = 7 * 24 * 3600
        timestamp, code = code.split('$', 1)
        
        # code is valid only for a week
        if int(timestamp) + SEC_PER_WEEK < int(time.time()):
            raise common.BadData(message='Password Reset code expired')

        username = get_user_root() + username 
        details = self.site.store.get_user_details(username)
        
        if not details:
            raise common.BadData(message="Invalid username")
        
        text = details.password + '$' + timestamp
        
        if not self._check_salted_hash(self.secret_key, text, code):
            raise common.BadData(message="Invaid password reset code")

########NEW FILE########
__FILENAME__ = bootstrap
"""Write query to create initial system objects including type system.
"""

# The bootstrap query will contain the following subqueries.
# 
# * create type/type without any properties
# * create all primitive types
# * create type/property and type/backreference
# * update type/type with its properties.
# * create type/user, type/usergroup and type/permission
# * create required usergroup and permission objects.

def _type(key, name, desc, properties=[], backreferences=[], kind='regular'):
    return dict(key=key, type={'key': '/type/type'}, name=name, desc=desc, kind=kind, properties=properties, backreferences=backreferences)

def _property(name, expected_type, unique=True, description='', **kw):
    return dict(kw, name=name, type={'key': '/type/property'}, expected_type={"key": expected_type}, unique={'type': '/type/boolean', 'value': unique}, description=description)
    
def _backreference(name, expected_type, property_name):
    pass

def primitive_types():
    """Subqueries to create all primitive types."""
    def f(key, name, description):
        return _type(key, name, description, kind='primitive')
    
    return [
        f('/type/key', 'Key', 'Type to store keys. A key is a string constrained to the regular expression [a-z][a-z/_]*.'),
        f('/type/string', 'String', 'Type to store unicode strings up to a maximum length of 2048.'),
        f('/type/text', 'Text', 'Type to store arbitrary long unicode text. Values of this type are not indexed.'),
        f('/type/int', 'Integer', 'Type to store 32-bit integers. This can store integers in the range [-2**32, 2**31-1].'),
        f('/type/boolean', 'Boolean', 'Type to store boolean values true and false.'),
        f('/type/float', 'Floating Point Number', 'Type to store 32-bit floating point numbers'),
        f('/type/datetime', 'Datetime', 'Type to store datetimes from 4713 BC to 5874897 AD with 1 millisecond resolution.'),
    ]
    
def system_types():
    return [
        _type('/type/property', 'Property', '', kind="embeddable",
            properties=[
                _property("name", "/type/string"),
                _property("expected_type", "/type/type"),
                _property("unique", "/type/boolean")
            ]
        ),
        _type('/type/backreference', 'Back-reference', '', kind='embeddable',
            properties=[
                _property("name", "/type/string"),
                _property("expected_type", "/type/type"),
                _property("property_name", "/type/string"),
                _property("query", "/type/string"),
            ]
        ),
        _type('/type/type', 'Type', 'Metatype.\nThis is the type of all types including it self.',
            properties=[
                _property("name", "/type/string"),
                _property("description", "/type/text"),
                _property("properties", "/type/property", unique=False),
                _property("backreference", "/type/backreference", unique=False),
                _property("kind", "/type/string", options=["primitive", "regular", "embeddable"]),
            ]
        ),
        _type('/type/user', 'User', '',
            properties=[
                _property('displayname', '/type/string'),
                _property('website', '/type/string'),
                _property('description', '/type/text'),
            ]
        ),
        _type('/type/usergroup', 'Usergroup', '',
            properties = [
                _property('description', '/type/text'),
                _property('members', '/type/user', unique=False)
            ]
        ),
        _type('/type/permission', 'Permission', '',
            properties = [
                _property('description', '/type/text'),
                _property('readers', '/type/usergroup', unique=False),
                _property('writers', '/type/usergroup', unique=False),
                _property('admins', '/type/usergroup', unique=False),
            ]
        ),
        _type('/type/object', 'Object', 'placeholder type for storing arbitrary objects'),
        _type('/type/dict', 'Dict', 'placeholder type for storing arbitrary dictionaties', kind='embeddable'),
        _type('/type/delete', 'Deleted object', 'Type to mark an object as deleted.'),
        _type('/type/redirect', 'Redirect', 'Type to specify redirects.',
            properties = [
                _property('location', '/type/string'),
            ],        
        ),
    ]

def usergroup(key, description, members=[]):
    return {
        'key': key,
        'type': {'key': '/type/usergroup'},
        'description': description, 
        'members': members
    }
    
def permission(key, readers, writers, admins):
    return {
        'key': key,
        'type': {'key': '/type/permission'},
        'readers': readers,
        'writers': writers,
        'admins': admins
    }

def system_objects():        
    def t(key):
        return {'key': key}
    
    return [
        usergroup('/usergroup/everyone', 'Group of all users including anonymous users.'),
        usergroup('/usergroup/allusers', 'Group of all registred users.'),
        usergroup('/usergroup/admin', 'Group of admin users.'),
        permission('/permission/open', [t('/usergroup/everyone')], [t('/usergroup/everyone')], [t('/usergroup/admin')]),
        permission('/permission/restricted', [t('/usergroup/everyone')], [t('/usergroup/admin')], [t('/usergroup/admin')]),
        permission('/permission/secret', [t('/usergroup/admin')], [t('/usergroup/admin')], [t('/usergroup/admin')]),
    ]
    
def make_query():
    return primitive_types() + system_types() + system_objects()

def bootstrap(site, admin_password):
    """Creates system types and objects for a newly created site.
    """
    import cache
    cache.loadhook()
    
    import web
    web.ctx.infobase_bootstrap = True
    
    query = make_query()
    site.save_many(query)
    
    from infogami.infobase import config
    import random
    import string
    
    def random_password(length=20):
        chars = string.letters + string.digits
        return "".join(random.choice(chars) for i in range(length))

    # Account Bot is not created till now. Set account_bot to None in config until he is created.
    account_bot = config.get("account_bot")
    config.account_bot = None

    a = site.get_account_manager()
    a.register(username="admin", email="admin@example.com", password=admin_password, data=dict(displayname="Administrator"), _activate=True)
    a.update_user_details("admin", verified=True)

    if account_bot:
        username = account_bot.split("/")[-1]
        a.register(username=username, email="userbot@example.com", password=random_password(), data=dict(displayname=username), _activate=True)
        a.update_user_details(username, verified=True)

    # add admin user to admin usergroup
    import account
    q = [usergroup('/usergroup/admin', 'Group of admin users.', [{"key": account.get_user_root() + "admin"}])]
    site.save_many(q)

    config.account_bot = account_bot

    web.ctx.infobase_bootstrap = False

########NEW FILE########
__FILENAME__ = bulkupload
"""
bulkupload script to upload multiple objects at once. 
All the inserts are merged to give better performance.
"""
import web
from infobase import TYPES, DATATYPE_REFERENCE
import datetime
import re
import tempfile

def sqlin(name, values):
    """
        >>> sqlin('id', [1, 2, 3, 4])
        <sql: 'id IN (1, 2, 3, 4)'>
        >>> sqlin('id', [])
        <sql: '1 = 2'>
    """
    def sqljoin(queries, sep):
        result = ""
        for q in queries:
            if result:
                result = result + sep
            result = result + q
        return result
    
    if not values:
        return web.reparam('1 = 2', {})
    else:
        values = [web.reparam('$v', locals()) for v in values]
        return name + ' IN ('+ sqljoin(values, ", ") + ')'

@web.memoize        
def get_table_columns(table):
    # Postgres query to get all column names. 
    # Got by runing sqlalchemy with echo=True.
    q = """
    SELECT a.attname,
      pg_catalog.format_type(a.atttypid, a.atttypmod),
      (SELECT substring(d.adsrc for 128) FROM pg_catalog.pg_attrdef d
       WHERE d.adrelid = a.attrelid AND d.adnum = a.attnum AND a.atthasdef)
      AS DEFAULT,
      a.attnotnull, a.attnum, a.attrelid as table_oid
    FROM pg_catalog.pg_attribute a
    WHERE a.attrelid = (
        SELECT c.oid
        FROM pg_catalog.pg_class c
             LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
             WHERE (pg_catalog.pg_table_is_visible(c.oid))
             AND c.relname = $table AND c.relkind in ('r','v')
    ) AND a.attnum > 0 AND NOT a.attisdropped
    ORDER BY a.attnum;
    """ 
    return [r.attname for r in web.query(q, locals())]
    
def multiple_insert(table, values, seqname=None):
    """Inserts multiple rows into a table using sql copy."""
    def escape(value):
        if value is None:
            return "\N"
        elif isinstance(value, basestring): 
            value = value.replace('\\', r'\\') # this must be the first one
            value = value.replace('\t', r'\t')
            value = value.replace('\r', r'\r')
            value = value.replace('\n', r'\n')
            return value
        elif isinstance(value, bool):
            return value and 't' or 'f'
        else:
            return str(value)
            
    def increment_sequence(seqname, n):
        """Increments a sequence by the given amount."""
        d = web.query(
            "SELECT setval('%s', $n + (SELECT last_value FROM %s), true) + 1 - $n AS START" % (seqname, seqname), 
            locals())
        return d[0].start
        
    def write(path, data):
        f = open(path, 'w')
        f.write(web.utf8(data))
        f.close()
        
    if not values:
        return []
        
    if seqname is None:
        seqname = table + "_id_seq"
        
    #print "inserting %d rows into %s" % (len(values), table)
        
    columns = get_table_columns(table)
    if seqname:
        n = len(values)
        start = increment_sequence(seqname, n)
        ids = range(start, start+n)
        for v, id in zip(values, ids):
            v['id'] = id
    else:
        ids = None
        
    data = []
    for v in values:
        assert set(v.keys()) == set(columns)
        data.append("\t".join([escape(v[c]) for c in columns]))
        
    filename = tempfile.mktemp(suffix='.copy', prefix=table)
    write(filename, "\n".join(data))
    web.query("COPY %s FROM '%s'" % (table, filename))
    return ids
    
def get_key2id():
    """Return key to id mapping for all things in the database."""
    key2id = {}
    offset = 0
    limit = 100000
    web.transact()
    # declare a cursor to read all the keys
    web.query("DECLARE key2id CURSOR FOR SELECT id, key FROM thing")
    while True:
        result = web.query('FETCH FORWARD $limit FROM key2id', vars=locals())
        if not result:
            break
        for row in result:
            key2id[row.key] = row.id

    web.query("CLOSE key2id");
    web.rollback();
    return key2id

key2id = None
        
class BulkUpload:
    def __init__(self, site, author=None):
        self.site = site
        self.author_id = author and author.id
        self.comment = {}
        self.machine_comment = {}
        self.created = []
        self.now = datetime.datetime.utcnow().isoformat()

        # initialize key2id, if it is not initialzed already.
        global key2id
        key2id = key2id or get_key2id()
        
    def upload(self, query):
        """Inserts"""
        assert isinstance(query, list)
        web.transact()
        try:
            self.process_creates(query)
            self.process_inserts(query)
        except:
            web.rollback()
            raise
        else:
            web.commit()
            
    def process_creates(self, query):
        keys = set(self.find_keys(query))
        tobe_created = set(self.find_creates(query))
        tobe_created = [k for k in tobe_created if k not in key2id] 
        
        # insert things
        d = dict(site_id=self.site.id, created=self.now, last_modified=self.now, latest_revision=1, deleted=False)
        values = [dict(d, key=k) for k in tobe_created]
        ids = multiple_insert('thing', values)
        for v, id in zip(values, ids):
            key2id[v['key']] = id
        
        # insert versions
        d = dict(created=self.now, revision=1, author_id=self.author_id, ip=None, comment=self.comment, machine_comment=self.machine_comment)    
        multiple_insert('version', [dict(d, thing_id=key2id[k], comment=self.comment[k], machine_comment=self.machine_comment[k]) for k in tobe_created])
        self.created = set(tobe_created)
        
    def find_keys(self, query, result=None):
        if result is None:
            result = []
            
        if isinstance(query, list):
            for q in query: 
                self.find_keys(q, result)
        elif isinstance(query, dict) and 'key' in query:
            assert re.match('^/[^ \t\n]*$', query['key']), 'Bad key: ' + repr(query['key'])
            result.append(query['key'])
            for k, v in query.items():
                self.find_keys(v, result)
        return result
    
    def find_creates(self, query, result=None):
        """Find keys of all queries which have 'create' key.
        """
        if result is None: 
            result = []
            
        if isinstance(query, list):
            for q in query:
                self.find_creates(q, result)
        elif isinstance(query, dict):
            if 'create' in query:
                result.append(query['key'])
                self.find_creates(query.values(), result)
                #@@ side-effect
                self.comment[query['key']] = query.pop('comment', None)
                self.machine_comment[query['key']] = query.pop('machine_comment', None) 
        return result
        
    def process_inserts(self, query):
        values = []
        for q in query:
            self.prepare_datum(q, values)
        multiple_insert('datum', values, seqname=False)
        
    def prepare_datum(self, query, result, path=""):
        """This is a funtion with side effect. 
        It append values to be inserted to datum table into result and return (value, datatype) for that query.
        """
        max_rev = 2 ** 31 - 1
        def append(thing_id, key, value, datatype, ordering):
            result.append(dict(
                thing_id=thing_id, 
                begin_revision=1,
                end_revision = max_rev, 
                key=key, 
                value=value, 
                datatype=datatype, 
                ordering=ordering))
        
        if isinstance(query, dict):
            if 'value' in query:
                return (query['value'], TYPES[query['type']])
            else:
                thing_id = key2id[query['key']]
                if query['key'] in self.created:
                    self.created.remove(query['key'])
                    for key, value in query.items():
                        if key == 'create': 
                            continue
                        if isinstance(value, list):
                            for i, v in enumerate(value):
                                _value, datatype = self.prepare_datum(v, result, "%s/%s#%d" % (path, key, i))
                                append(thing_id, key, _value, datatype, i)
                        else:
                            _value, datatype = self.prepare_datum(value, result, "%s/%s" % (path, key))
                            if key == 'key':
                                datatype = 1
                            append(thing_id, key, _value, datatype, None)
                return (thing_id, DATATYPE_REFERENCE)
        elif isinstance(query, basestring):
            return (query, TYPES['/type/string'])
        elif isinstance(query, int):
            return (query, TYPES['/type/int'])
        elif isinstance(query, float):
            return (query, TYPES['/type/float'])
        elif isinstance(query, bool):
            return (int(query), TYPES['/type/boolean'])
        else:
            raise Exception, '%s: invalid value: %s' (path, repr(query))

if __name__ == "__main__":
    import sys
    
    web.config.db_parameters = dict(dbn='postgres', host='pharosdb', db='infobase_data2', user='anand', pw='') 
    web.config.db_printing = True
    web.load()
    from infobase import Infobase
    site = Infobase().get_site('infogami.org')
    BulkUpload(site)

########NEW FILE########
__FILENAME__ = cache
"""
Infobase cache.

Infobase cache contains multiple layers.

new_objects (thread-local)
special_cache
local_cache (thread-local)
global_cache

new_objects is a thread-local dictionary containing objects created in the
current request. It is stored at web.ctx.new_objects. new_objects are added
to the global cache at the end of every request. It is the responsibility of
the DBStore to populate this on write and it should also make sure that this
is cleared on write failures.

special_cache is an optional cache provided to cache most frequently accessed
objects (like types and properties) and the application is responsible to keep
it in sync.

local_cache is a thread-local cache maintained to avoid repeated requests to
global cache. This is stored at web.ctx.local_cache.

global_cache is typically expensive to access, so its access is minimized.
Typical examples of global_cache are LRU cache and memcached cache.

Any elements added to the infobase cache during a request are cached locally until the end
of that request and then they are added to the global cache.
"""

import web
import lru
import logging

logger = logging.getLogger("infobase.cache")

class NoneDict:
    def __getitem__(self, key):
        raise KeyError, key
        
    def __setitem__(self, key, value):
        pass
        
    def update(self, d):
        pass

class MemcachedDict:
    def __init__(self, memcache_client=None, servers=[]):
        if memcache_client is None:
            import memcache
            memcache_client = memcache.Client(servers)
        self.memcache_client = memcache_client
        
    def __getitem__(self, key):
        key = web.safestr(key)
        value = self.memcache_client.get(key)
        if value is None:
            raise KeyError, key
        return value
        
    def __setitem__(self, key, value):
        key = web.safestr(key)
        logger.debug("MemcachedDict.set: %s", key)
        self.memcache_client.set(key, value)
        
    def update(self, d):
        d = dict((web.safestr(k), v) for k, v in d.items())
        logger.debug("MemcachedDict.update: %s", d.keys())
        self.memcache_client.set_multi(d)
        
    def clear(self):
        self.memcache_client.flush_all()

_cache_classes = {}
def register_cache(type, klass):
    _cache_classes[type] = klass
    
register_cache('lru', lru.LRU)
register_cache('memcache', MemcachedDict)

def create_cache(type, **kw):
    klass = _cache_classes.get(type) or NoneDict
    return klass(**kw)

special_cache = {}
global_cache = lru.LRU(200)

def loadhook():
    web.ctx.new_objects = {}
    web.ctx.local_cache = {}
    web.ctx.locally_added = {}
    
def unloadhook():
    """Called at the end of every request."""
    d = {}
    d.update(web.ctx.locally_added)
    d.update(web.ctx.new_objects)

    if d:
        global_cache.update(d)
    
class Cache:
    def __getitem__(self, key):
        ctx = web.ctx
        obj = ctx.new_objects.get(key) \
            or special_cache.get(key)  \
            or ctx.local_cache.get(key) \
        
        if not obj:    
            obj = global_cache[key]
            ctx.local_cache[key] = obj
            
        return obj
        
    def get(self, key, default=None):
        try:
            return self[key]
        except:
            return default
    
    def __contains__(self, key):
        """Tests whether an element is present in the cache.
        This function call is expensive. Provided for the sake of completeness.
        
        Use:
            obj = cache.get(key)
            if obj is None:
                do_something()
        
        instead of:
            if key in cache:
                obj = cache[key]
            else:
                do_something()
        """
        try:
            self[key]
            return True
        except KeyError:
            return False
        
    def __setitem__(self, key, value):
        web.ctx.local_cache[key] = value
        web.ctx.locally_added[key] = value

    def clear(self, local=False):
        """Clears the cache. 
        When local=True, only the local cache is cleared.
        """
        web.ctx.locally_added.clear()
        web.ctx.local_cache.clear()
        web.ctx.new_objects.clear()
        if not local:
            global_cache.clear()

########NEW FILE########
__FILENAME__ = client
"""Infobase client."""

import common
import httplib, urllib
import _json as simplejson
import web
import socket
import datetime
import time
import logging

from infogami import config
from infogami.utils import stats

logger = logging.getLogger("infobase.client")

DEBUG = False

def storify(d):
    if isinstance(d, dict):
        for k, v in d.items():
            d[k] = storify(v)
        return web.storage(d)
    elif isinstance(d, list):
        return [storify(x) for x in d]
    else:
        return d

def unstorify(d):
    if isinstance(d, dict):
        return dict((k, unstorify(v)) for k, v in d.iteritems())
    elif isinstance(d, list):
        return [unstorify(x) for x in d]
    else:
        return d

class ClientException(Exception):
    def __init__(self, status, msg, json=None):
        self.status = status
        self.json = json
        Exception.__init__(self, msg)

    def get_data(self):
        if self.json:
            return simplejson.loads(self.json)
        else:
            return {}

class NotFound(ClientException):
    def __init__(self, msg):
        ClientException.__init__(self, "404 Not Found", msg)
    
def connect(type, **params):
    """Connect to infobase server using the given params.
    """
    for t in _connection_types:
        if type == t:
            return _connection_types[t](**params)
    raise Exception('Invalid connection type: ' + type)
                
class Connection:
    def __init__(self):
        self.auth_token = None
        
    def set_auth_token(self, token):
        self.auth_token = token

    def get_auth_token(self):
        return self.auth_token

    def request(self, path, method='GET', data=None):
        raise NotImplementedError
        
    def handle_error(self, status, error):
        try:
            data = simplejson.loads(error)
            message = data.get('message', '')
            json = error
        except:
            message = error
            json = None
            
        raise ClientException(status, message, json)
        
class LocalConnection(Connection):
    """LocalConnection assumes that db_parameters are set in web.config."""
    def __init__(self, **params):
        Connection.__init__(self)
        pass
        
    def request(self, sitename, path, method='GET', data=None):
        import server
        path = "/" + sitename + path
        web.ctx.infobase_auth_token = self.get_auth_token()
        try:
            stats.begin("infobase", path=path, method=method, data=data)                
            out = server.request(path, method, data)
            stats.end()
            if 'infobase_auth_token' in web.ctx:
                self.set_auth_token(web.ctx.infobase_auth_token)
        except common.InfobaseException, e:
            stats.end(error=True)
            self.handle_error(e.status, str(e))
        return out
        
class RemoteConnection(Connection):
    """Connection to remote Infobase server."""
    def __init__(self, base_url):
        Connection.__init__(self)
        self.base_url = base_url

    def request(self, sitename, path, method='GET', data=None):
        url = self.base_url + '/' + sitename + path
        path = '/' + sitename + path
        if isinstance(data, dict):
            for k in data.keys():
                if data[k] is None: del data[k]
        
        if web.config.debug:
            web.ctx.infobase_req_count = 1 + web.ctx.get('infobase_req_count', 0)
            a = time.time()
            _path = path
            _data = data
        
        if data:
            if isinstance(data, dict):
                data = dict((web.safestr(k), web.safestr(v)) for k, v in data.items())
                data = urllib.urlencode(data)
            if method == 'GET':
                path += '?' + data
                data = None
        
        stats.begin("infobase", path=path, method=method, data=data)                
        conn = httplib.HTTPConnection(self.base_url)
        env = web.ctx.get('env') or {}
        
        if self.auth_token:
            import Cookie
            c = Cookie.SimpleCookie()
            c['infobase_auth_token'] = self.auth_token
            cookie = c.output(header='').strip()
            headers = {'Cookie': cookie}
        else:
            headers = {}
            
        # pass the remote ip to the infobase server
        headers['X-REMOTE-IP'] = web.ctx.get('ip')
        
        try:
            conn.request(method, path, data, headers=headers)
            response = conn.getresponse()
            stats.end()
        except socket.error:
            stats.end(error=True)
            logger.error("Unable to connect to infobase server", exc_info=True)
            raise ClientException("503 Service Unavailable", "Unable to connect to infobase server")

        cookie = response.getheader('Set-Cookie')
        if cookie:
            import Cookie
            c = Cookie.SimpleCookie()
            c.load(cookie)
            if 'infobase_auth_token' in c:
                self.set_auth_token(c['infobase_auth_token'].value)                
                
        if web.config.debug:
            b = time.time()
            print >> web.debug, "%.02f (%s):" % (round(b-a, 2), web.ctx.infobase_req_count), response.status, method, _path, _data
                
        if response.status == 200:
            return response.read()
        else:
            self.handle_error("%d %s" % (response.status, response.reason), response.read())

_connection_types = {
    'local': LocalConnection,
    'remote': RemoteConnection
}
        
class LazyObject:
    """LazyObject which creates the required object on demand.
        >>> o = LazyObject(lambda: [1, 2, 3])
        >>> o
        [1, 2, 3]
    """
    def __init__(self, creator):
        self.__dict__['_creator'] = creator
        self.__dict__['_o'] = None
        
    def _get(self):
        if self._o is None:
            self._o = self._creator()
        return self._o
        
    def __getattr__(self, key):
        return getattr(self._get(), key)
            
class Site:
    def __init__(self, conn, sitename):
        self._conn = conn
        self.name = sitename
        # cache for storing pages requested in this HTTP request
        self._cache = {}
        
        self.store = Store(conn, sitename)
        self.seq = Sequence(conn, sitename)
        
    def _request(self, path, method='GET', data=None):
        out = self._conn.request(self.name, path, method, data)
        out = simplejson.loads(out)
        return storify(out)
        
    def _get(self, key, revision=None):
        """Returns properties of the thing with the specified key."""
        revision = revision and int(revision)
        
        if (key, revision) not in self._cache:
            data = dict(key=key, revision=revision)
            try:
                result = self._request('/get', data=data)
            except ClientException, e:
                if e.status.startswith('404'):
                    raise NotFound, key
                else:
                    raise
            self._cache[key, revision] = web.storage(common.parse_query(result))
            
        return self._cache[key, revision]
        
    def _process(self, value):
        if isinstance(value, list):
            return [self._process(v) for v in value]
        elif isinstance(value, dict):
            d = {}
            for k, v in value.items():
                d[k] = self._process(v)
            return create_thing(self, None, d)
        elif isinstance(value, common.Reference):
            return create_thing(self, unicode(value), None)
        else:
            return value
            
    def _process_dict(self, data):
        d = {}
        for k, v in data.items():
            d[k] = self._process(v)
        return d
            
    def _load(self, key, revision=None):
        data = self._get(key, revision)
        data = self._process_dict(data)
        return data
        
    def _get_backreferences(self, thing):
        def safeint(x):
            try: return int(x)
            except ValueError: return 0
            
        if 'env' in web.ctx:
            i = web.input(_method='GET')
        else:
            i = web.storage()
        page_size = 20
        backreferences = {}
        
        for p in thing.type._getdata().get('backreferences', []):
            offset = page_size * safeint(i.get(p.name + '_page') or '0')
            q = {
                p.property_name: thing.key, 
                'offset': offset,
                'limit': page_size
            }
            if p.expected_type:
                q['type'] = p.expected_type.key
            backreferences[p.name] = LazyObject(lambda q=q: self.get_many(self.things(q)))
        return backreferences

    def exists(self):
        """Returns true if this site exists.
        """
        try:
            self._request(path="", method="GET")
            return True
        except ClientException, e:
            if e.status.startswith("404"):
                return False
            else:
                raise

    def create(self):
        """Creates this site if not exists."""
        if not self.exists():
            self._request(path="", method="PUT")
    
    def get(self, key, revision=None, lazy=False):
        assert key.startswith('/')
        
        if lazy:
            data = None
        else:
            try:
                data = self._load(key, revision)
            except NotFound:
                return None        
        return create_thing(self, key, data, revision=revision)

    def get_many(self, keys):
        if not keys:
            return []
        
        # simple hack to avoid crossing URL length limit.
        if len(keys) > 100:
            things = []
            while keys:
                things += self.get_many(keys[:100])
                keys = keys[100:]
            return things

        data = dict(keys=simplejson.dumps(keys))
        result = self._request('/get_many', data=data)
        things = []
        
        for key in keys:
            #@@ what if key is not there?
            if key in result:
                data = result[key]
                data = web.storage(common.parse_query(data))
                self._cache[key, None] = data
                things.append(create_thing(self, key, self._process_dict(data)))
        return things
        
    def new_key(self, type):
        data = {'type': type}
        result = self._request('/new_key', data=data)
        return result

    def things(self, query, details=False):
        query = simplejson.dumps(query)
        return self._request('/things', 'GET', {'query': query, "details": str(details)})
                
    def versions(self, query):
        def process(v):
            v = web.storage(v)
            v.created = parse_datetime(v.created)
            v.author = v.author and self.get(v.author, lazy=True)
            return v
        query = simplejson.dumps(query)
        versions =  self._request('/versions', 'GET', {'query': query})
        return [process(v) for v in versions]
        
    def recentchanges(self, query):
        query = simplejson.dumps(query)
        changes = self._request('/_recentchanges', 'GET', {'query': query})
        return [Changeset.create(self, c) for c in changes]
        
    def get_change(self, id):
        data = self._request('/_recentchanges/%s' % id, 'GET')
        return data and Changeset.create(self, data)

    def write(self, query, comment=None, action=None):
        self._run_hooks('before_new_version', query)
        _query = simplejson.dumps(query)
        result = self._request('/write', 'POST', dict(query=_query, comment=comment, action=action))
        self._run_hooks('on_new_version', query)
        self._invalidate_cache(result.created + result.updated)
        return result
    
    def save(self, query, comment=None, action=None, data=None):
        query = dict(query)
        self._run_hooks('before_new_version', query)
        
        query['_comment'] = comment
        query['_action'] = action
        query['_data'] = data
        key = query['key']
        
        #@@ save sends payload of application/json instead of form data
        data = simplejson.dumps(query)
        result = self._request('/save' + key, 'POST', data)
        if result:
            self._invalidate_cache([result['key']])
            self._run_hooks('on_new_version', query)
        return result
        
    def save_many(self, query, comment=None, data=None, action=None):
        _query = simplejson.dumps(query)
        #for q in query:
        #    self._run_hooks('before_new_version', q)
        data = data or {}
        result = self._request('/save_many', 'POST', dict(query=_query, comment=comment, action=action, data=simplejson.dumps(data)))
        self._invalidate_cache([r['key'] for r in result])
        for q in query:
            self._run_hooks('on_new_version', q)
        return result
    
    def _invalidate_cache(self, keys):
        for k in keys:
            try:
                del self._cache[k, None]
            except KeyError:
                pass
    
    def can_write(self, key):
        perms = self._request('/permission', 'GET', dict(key=key))
        return perms['write']

    def _run_hooks(self, name, query):
        if isinstance(query, dict) and 'key' in query:
            key = query['key']
            type = query.get('type')
            # type is none when saving permission
            if type is not None:
                if isinstance(type, dict):
                    type = type['key']
                type = self.get(type)
                data = query.copy()
                data['type'] = type
                t = self.new(key, data)
                # call the global _run_hooks function
                _run_hooks(name, t)
        
    def login(self, username, password, remember=False):
        return self._request('/account/login', 'POST', dict(username=username, password=password))
        
    def register(self, username, displayname, email, password):
        data = dict(username=username, displayname=displayname, email=email, password=password)
        _run_hooks("before_register", data)
        return self._request('/account/register', 'POST', data)

    def activate_account(self, username):
        data = dict(username=username)
        return self._request('/account/activate', 'POST', data)
        
    def update_account(self, username, **kw):
        """Updates an account.
        """
        data = dict(kw, username=username)
        return self._request('/account/update', 'POST', data)
        
    def find_account(self, username=None, email=None):
        """Finds account by username or email."""
        if username is None and email is None:
            return None
        data = dict(username=username, email=email)
        return self._request("/account/find", "GET", data)    

    def update_user(self, old_password, new_password, email):
        return self._request('/account/update_user', 'POST', 
            dict(old_password=old_password, new_password=new_password, email=email))
            
    def update_user_details(self, username, **kw):
        params = dict(kw, username=username)
        return self._request('/account/update_user_details', 'POST', params)
        
    def find_user_by_email(self, email):
        return self._request('/account/find_user_by_email', 'GET', {'email': email})
            
    def get_reset_code(self, email):
        """Returns the reset code for user specified by the email.
        This called to send forgot password email. 
        This should be called after logging in as admin.
        """
        return self._request('/account/get_reset_code', 'GET', dict(email=email))
        
    def check_reset_code(self, username, code):
        return self._request('/account/check_reset_code', 'GET', dict(username=username, code=code))
        
    def get_user_email(self, username):
        return self._request('/account/get_user_email', 'GET', dict(username=username))
        
    def reset_password(self, username, code, password):
        return self._request('/account/reset_password', 'POST', dict(username=username, code=code, password=password))
    
    def get_user(self):
        # avoid hitting infobase when there is no cookie.
        if web.cookies().get(config.login_cookie_name) is None:
            return None
        try:
            data = self._request('/account/get_user')
        except ClientException:
            return None
            
        user = data and create_thing(self, data['key'], self._process_dict(common.parse_query(data)))
        return user

    def new(self, key, data=None):
        """Creates a new thing in memory.
        """
        data = common.parse_query(data)
        data = self._process_dict(data or {})
        return create_thing(self, key, data)
        
class Store:
    """Store to store any arbitrary data.
    
    This provides a dictionary like interface for storing documents. 
    Each document can have an optional type (default is "") and all the (type, name, value) triples are indexed.
    """
    def __init__(self, conn, sitename):
        self.conn = conn
        self.name = sitename
        
    def _request(self, path, method='GET', data=None):
        out = self.conn.request(self.name, "/_store/" + path, method, data)
        return simplejson.loads(out)
    
    def delete(self, key):
        return self._request(key, method='DELETE')
        
    def update(self, d={}, **kw):
        d2 = dict(d, **kw)
        docs = [dict(doc, _key=key) for key, doc in d2.items()]
        self._request("_save_many", method="POST", data=simplejson.dumps(docs))
            
    def clear(self):
        """Removes all keys from the store. Use this with caution!"""
        for k in self.keys(limit=-1):
            del self[k]

    def query(self, type=None, name=None, value=None, limit=100, offset=0, include_docs=False):
        """Returns the  a list of keys matching the given query.        
        Sample result:
            [{"key": "a"}, {"key": "b"}, {"key": "c"}]
        """
        if limit == -1:
            return self.unlimited_query(type, name, value, offset=offset)
            
        params = dict(type=type, name=name, value=value, limit=limit, offset=offset, include_docs=str(include_docs))
        params = dict((k, v) for k, v in params.items() if v is not None)
        return self._request("_query", method="GET", data=params)
        
    def unlimited_query(self, type, name, value, offset=0):
        while True:
            result = self.query(type, name, value, limit=1000, offset=offset)
            if not result:
                break
                
            offset += len(result)
            for k in result:
                yield k
    
    def __getitem__(self, key):
        try:
            return self._request(key)
        except ClientException, e:
            if e.status.startswith("404"):
                raise KeyError, key
            else:
                raise
    
    def __setitem__(self, key, data):
        return self._request(key, method='PUT', data=simplejson.dumps(data))
        
    def __delitem__(self, key):
        self.delete(key)
        
    def __contains__(self, key):
        return bool(self.get(key))
        
    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default
            
    def iterkeys(self, **kw):
        result = self.query(**kw)
        return (d['key'] for d in result)
        
    def keys(self, **kw):
        return list(self.iterkeys(**kw))
        
    def itervalues(self, **kw):
        rows = self.query(include_docs=True, **kw)
        return (row['doc'] for row in rows)
    
    def values(self, **kw):
        return list(self.itervalues(**kw))
        rows = self.query(**kw)
        
    def iteritems(self, **kw):
        rows = self.query(include_docs=True, **kw)
        return ((row['key'], row['doc']) for row in rows)
        
    def items(self, **kw):
        return list(self.iteritems(**kw))
        
class Sequence:
    """Dynamic sequences. 
    Quite similar to sequences in postgres, but there is no need of define anything upfront..
    
        seq = web.ctx.site.seq
        for i in range(10):
            print seq.next_value("foo")
    """
    def __init__(self, conn, sitename):
        self.conn = conn
        self.name = sitename
        
    def _request(self, path, method='GET', data=None):
        out = self.conn.request(self.name, "/_seq/" + path, method, data)
        return simplejson.loads(out)        
        
    def get_value(self, name):
        return self._request(name, method="GET")['value']
        
    def next_value(self, name):
        return self._request(name, method="POST", data=" ")['value']
        
def parse_datetime(datestring):
    """Parses from isoformat.
    Is there any way to do this in stdlib?
    """
    import re, datetime
    tokens = re.split('-|T|:|\.| ', datestring)
    return datetime.datetime(*map(int, tokens))

class Nothing:
    """For representing missing values.
    
    >>> n = Nothing()
    >>> str(n)
    ''
    >>> web.utf8(n)
    ''
    """
    def __getattr__(self, name):
        if name.startswith('__') or name == 'next':
            raise AttributeError, name
        else:
            return self

    def __getitem__(self, name):
        return self

    def __call__(self, *a, **kw):
        return self

    def __add__(self, a):
        return a 

    __radd__ = __add__
    __mul__ = __rmul__ = __add__

    def __iter__(self):
        return iter([])

    def __hash__(self):
        return id(self)

    def __len__(self):
        return 0
        
    def __bool__(self):
        return False
        
    def __eq__(self, other):
        return isinstance(other, Nothing)
    
    def __ne__(self, other):
        return not (self == other)

    def __str__(self): return ""
    def __repr__(self): return ""

nothing = Nothing()

_thing_class_registry = {}
def register_thing_class(type, klass):
    _thing_class_registry[type] = klass
    
def create_thing(site, key, data, revision=None):
    type = None
    try:
        if data is not None and data.get('type'):
            type = data.get('type')
            
            #@@@ Fix this!
            if isinstance(type, Thing):
                type = type.key
            elif isinstance(type, dict):
                type = type['key']
                
            # just to be safe
            if not isinstance(type, basestring):
                type = None
    except Exception, e:
        # just for extra safety
        print >> web.debug, 'ERROR:', str(e)
        type = None

    return _thing_class_registry.get(type, Thing)(site, key, data, revision)
    
class Thing:
    def __init__(self, site, key, data=None, revision=None):
        self._site = site
        self.key = key
        self._revision = revision
        
        assert data is None or isinstance(data, dict)
        
        self._data = data
        self._backreferences = None
        
        # no back-references for embeddable objects
        if self.key is None:
            self._backreferences = {}
        
    def _getdata(self):
        if self._data is None:
            self._data = self._site._load(self.key, self._revision)
            
            # @@ Hack: change class based on type
            self.__class__ = _thing_class_registry.get(self._data.get('type').key, Thing)
            
        return self._data
        
    def _get_backreferences(self):
        if self._backreferences is None:
            self._backreferences = self._site._get_backreferences(self)
        return self._backreferences
        
    def _get_defaults(self):
        return {}
    
    def keys(self):
        special = ['id', 'revision', 'latest_revision', 'last_modified', 'created']
        return [k for k in self._getdata() if k not in special]
        
    def get(self, key, default=None):
        try:
            return self._getdata()[key]
        except KeyError:
            # try default-value
            d = self._get_defaults()
            try:
                return d[key]
            except KeyError:
                if 'type' not in self._data:
                    return default
                return self._get_backreferences().get(key, default) 

    def __getitem__(self, key):
        return self.get(key, nothing)
    
    def __setitem__(self, key, value):
        self._getdata()[key] = value
    
    def __setattr__(self, key, value):
        if key in ['key', 'revision', 'latest_revision', 'last_modified', 'created'] or key.startswith('_'):
            self.__dict__[key] = value
        else:
            self._getdata()[key] = value

    def __iter__(self):
        return iter(self._data)
        
    def _save(self, comment=None, action=None, data=None):
        d = self.dict()
        return self._site.save(d, comment, action=action, data=data)
        
    def _format(self, d):
        if isinstance(d, dict):
            return dict((k, self._format(v)) for k, v in d.iteritems())
        elif isinstance(d, list):
            return [self._format(v) for v in d]
        elif isinstance(d, common.Text):
            return {'type': '/type/text', 'value': web.safeunicode(d)}
        elif isinstance(d, Thing):
            return d._dictrepr()
        elif isinstance(d, datetime.datetime):
            return {'type': '/type/datetime', 'value': d.isoformat()}
        else:
            return d
    
    def dict(self):
        return self._format(self._getdata())
    
    def _dictrepr(self):
        if self.key is None:
            return self.dict()
        else:
            return {'key': self.key}
    
    def update(self, data):
        data = common.parse_query(data)
        data = self._site._process_dict(data)
        self._getdata().update(data)

    def __getattr__(self, key):
        if key.startswith('__'):
            raise AttributeError, key
        
        # Hack: __class__ of this object can change in _getdata method.
        #
        # Lets say __class__ is changed to A in _getdata and A has method foo.
        # When obj.foo() is called before initializing, foo won't be found becase 
        # __class__ is not yet set to A. Initialize and call getattr again to get 
        # the expected behaviour.
        # 
        # @@ Can this ever lead to infinite-recursion?
        if self._data is None:
            self._getdata() # initialize self._data
            return getattr(self, key)

        return self[key]
    
    def __eq__(self, other):
        return isinstance(other, Thing) and other.key == self.key
        
    def __ne__(self, other):
        return not self.__eq__(other)
    
    def __str__(self):
        return web.utf8(self.key)
    
    def __repr__(self):
        if self.key:
            return "<Thing: %s>" % repr(self.key)
        else:
            return "<Thing: %s>" % repr(self._data)
            
class Type(Thing):
    def _get_defaults(self):
        return {"kind": "regular"}
        
    def get_property(self, name):
        for p in self.properties:
            if p.name == name:
                return p
                
    def get_backreference(self, name):
        for p in self.backreferences:
            if p.name == name:
                return p
                
class Changeset:
    def __init__(self, site, data):
        self._site = site
        self._data = data
        
        self.id = data['id']
        self.kind = data['kind']
        self.timestamp = parse_datetime(data['timestamp'])
        self.comment = data['comment']
        
        if data['author']:
            self.author = self._site.get(data['author']['key'], lazy=True)
        else:
            self.author = None
        self.ip = data['ip']
        self.changes = data.get('changes') or []
        self.data = web.storage(data['data'])
        self.init()
        
    def get_comment(self):
        return self.comment
        
    def get_changes(self):
        return [self._site.get(c['key'], c['revision'], lazy=True) for c in self.changes]
            
    def dict(self):
        return unstorify(self._data)
        
    def init(self):
        pass
        
    def url(self):
        kwargs = {
            "year": self.timestamp.year,
            "month": self.timestamp.month,
            "day": self.timestamp.day,
            "kind": self.kind,
            "id": self.id
        }
        default_format = "/recentchanges/%(year)s/%(month)02d/%(day)02d/%(kind)s/%(id)s"
        format = config.get("recentchanges_view_link_format", default_format)
        return format % kwargs
    
    def __repr__(self):
        return "<Changeset@%s of kind %s>" % (self.id, self.kind)
        
    @staticmethod
    def create(site, data):
        kind = data['kind']
        klass = _changeset_class_register.get(kind) or _changeset_class_register.get(None)
        return klass(site, data)

_changeset_class_register = {}
def register_changeset_class(kind, klass):
    _changeset_class_register[kind] = klass
    
register_changeset_class(None, Changeset)
register_thing_class('/type/type', Type)

# hooks can be registered by extending the hook class
hooks = []
class metahook(type):
    def __init__(self, name, bases, attrs):
        hooks.append(self())
        type.__init__(self, name, bases, attrs)

class hook:
    __metaclass__ = metahook

#remove hook from hooks    
hooks.pop()

def _run_hooks(name, thing):
    for h in hooks:
        m = getattr(h, name, None)
        if m:
            m(thing)

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = common
import config
import web

from core import *
from utils import *

# Primitive types and corresponding python types
primitive_types = {
    '/type/key': str,
    '/type/int': int,
    '/type/float': float,
    '/type/boolean': parse_boolean,
    '/type/string': str,
    '/type/text': Text,
    '/type/datetime': parse_datetime,
}

# properties present for every type of object.
COMMON_PROPERTIES = ['key', 'type', 'created', 'last_modified', 'permission', 'child_permission']
READ_ONLY_PROPERTIES = ["id", "created", "last_modified", "revision", "latest_revision"]

def find_type(value):
    if isinstance(value, Thing):
        return thing.type.key
    elif isinstance(value, Reference):
        return '/type/object'
    elif isinstance(value, Text):
        return '/type/text'
    elif isinstance(value, datetime.datetime):
        return '/type/datetime'
    elif isinstance(value, bool):
        return '/type/boolean'
    elif isinstance(value, int):
        return '/type/int'
    elif isinstance(value, float):
        return '/type/float'
    elif isinstance(value, dict):
        return '/type/dict'
    else:
        return '/type/string'

def parse_query(d):
    return parse_data(d, level=0)

def parse_data(d, level=0):
    """
        >>> parse_data(1)
        1
        >>> text = {'type': '/type/text', 'value': 'foo'}
        >>> date= {'type': '/type/datetime', 'value': '2009-01-02T03:04:05'}
        >>> true = {'type': '/type/boolean', 'value': 'true'}
        
        >>> parse_data(text)
        <text: u'foo'>
        >>> parse_data(date)
        datetime.datetime(2009, 1, 2, 3, 4, 5)
        >>> parse_data(true)
        True
        >>> parse_data({'key': '/type/type'})
        <Storage {'key': '/type/type'}>
        >>> parse_data({'key': '/type/type'}, level=1)
        <ref: u'/type/type'>
        >>> parse_data([text, date, true])
        [<text: u'foo'>, datetime.datetime(2009, 1, 2, 3, 4, 5), True]
        >>> parse_data({'a': text, 'b': date})
        <Storage {'a': <text: u'foo'>, 'b': datetime.datetime(2009, 1, 2, 3, 4, 5)}>

        >>> parse_query({'works': {'connect': 'update_list', 'value': [{'key': '/w/OL1W'}]}, 'key': '/b/OL1M'})
        <Storage {'works': <Storage {'connect': 'update_list', 'value': [<ref: u'/w/OL1W'>]}>, 'key': '/b/OL1M'}>
    """
    if isinstance(d, dict):
        if 'value' in d and 'type' in d and d['type'] in primitive_types:
            type = d['type']
            value = parse_data(d['value'], level=None)
            return primitive_types[type](value)
        elif level != 0 and 'key' in d and len(d) == 1:
            return Reference(d['key'])
        else:
            return web.storage((k, parse_data(v, level+1)) for k, v in d.iteritems())
    elif isinstance(d, list):
        return [parse_data(v, level+1) for v in d]
    else:
        return d

def format_data(d):
    """Convert a data to a representation that can be saved.
    
        >>> format_data(1)
        1
        >>> format_data('hello')
        'hello'
        >>> format_data(Text('hello'))
        {'type': '/type/text', 'value': u'hello'}
        >>> format_data(datetime.datetime(2009, 1, 2, 3, 4, 5))
        {'type': '/type/datetime', 'value': '2009-01-02T03:04:05'}
        >>> format_data(Reference('/type/type'))
        {'key': u'/type/type'}
    """
    if isinstance(d, dict):
        return dict((k, format_data(v)) for k, v in d.iteritems())
    elif isinstance(d, list):
        return [format_data(v) for v in d]
    elif isinstance(d, Text):
        return {'type': '/type/text', 'value': unicode(d)}
    elif isinstance(d, Reference):
        return {'key': unicode(d)}
    elif isinstance(d, datetime.datetime):
        return {'type': '/type/datetime', 'value': d.isoformat()}
    else:
        return d

def record_exception():
    """This function is called whenever there is any exception in Infobase.
    
    Overwrite this function if some action (like logging the exception) needs to be taken on exceptions.
    """
    import traceback
    traceback.print_exc()

def create_test_store():
    """Creates a test implementation for using in doctests.
    
    >>> store = create_test_store()
    >>> json = store.get('/type/type')
    >>> t = Thing.from_json(store, u'/type/type', json)
    >>> t
    <thing: u'/type/type'>
    >>> t.properties[0]
    <Storage {'expected_type': <thing: u'/type/string'>, 'unique': True, 'name': 'name'}>
    >>> t.properties[0].expected_type.key
    u'/type/string'
    """
    import _json as simplejson
    class Store(web.storage):
        def get(self, key, revision=None):
            return simplejson.dumps(self[key].format_data())
            
    store = Store()
    
    def add_primitive_type(key):
        add_object({
            'key': key,
            'type': {'key': '/type/type'},
            'king': 'primitive'
        })
        
    def add_object(data):
        key = data.pop('key')
        store[key] = Thing(store, key, parse_data(data))
        return store[key]
    
    add_object({
        'key': '/type/type',
        'type': {'key': '/type/type'},
        'kind': 'regular',
        'properties': [{
            'name': 'name',
            'expected_type': {'key': '/type/string'},
            'unique': True
        }, {
            'name': 'kind',
            'expected_type': {'key': '/type/string'},
            'options': ['primitive', 'regular', 'embeddable'],
            'unique': True
        }, {
            'name': 'properties',
            'expected_type': {'key': '/type/property'},
            'unique': False
        }]
    })
    
    add_object({
        'key': '/type/property',
        'type': '/type/type',
        'kind': 'embeddable',
        'properties': [{
            'name': 'name',
            'expected_type': {'key': '/type/string'},
            'unique': True
        }, {
            'name': 'expected_type',
            'expected_type': {'key': '/type/type'},
            'unique': True
        }, {
            'name': 'unique',
            'expected_type': {'key': '/type/boolean'},
            'unique': True
        }]    
    })
    
    add_primitive_type('/type/string')
    add_primitive_type('/type/int')
    add_primitive_type('/type/float')
    add_primitive_type('/type/boolean')
    add_primitive_type('/type/text')
    add_primitive_type('/type/datetime')
    
    add_object({
        'key': '/type/page',
        'type': '/type/page',
        'kind': 'regular',
        'properties': [{
            'name': 'title',
            'expected_type': {'key': '/type/string'},
            'unique': True
        }]
    })
    return store

class LazyThing:
    def __init__(self, store, key, json):
        self.__dict__['_key'] = key
        self.__dict__['_store'] = store
        self.__dict__['_json'] = json
        self.__dict__['_thing'] = None
        
    def _get(self):
        if self._thing is None:
            self._thing = Thing.from_json(self._store, self._key, self._json)
        return self._thing
        
    def __getattr__(self, key):
        return getattr(self._get(), key)
        
    def __json__(self):
        return self._json
        
    def __repr__(self):
        return "<LazyThing: %s>" % repr(self._key)

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = config
"""Infobase configuration."""

# IP address of machines which can be trusted for doing admin tasks
trusted_machines = ["127.0.0.1"]

# default size of cache
cache_size = 1000

secret_key = "bzuim9ws8u"

# set this to log dir to enable logging
logroot = None
compress_log = False

# query_timeout in milli seconds.
query_timeout = "60000"

user_root = "/user/"

#@@ Hack to execute some code when infobase is created. 
#@@ This will be replaced with a better method soon.
startup_hook = None

bind_address = None
port = 5964
fastcgi = False

# earlier there used to be a machine_comment column in version table. 
# Set this flag to True to continue to use that field in earlier installations.
use_machine_comment = False

# bot column is added transaction table to mark edits by bot. Flag to enable/disable this feature.
use_bot_column = True

verify_user_email = False

def get(key, default=None):
    return globals().get(key, default)


########NEW FILE########
__FILENAME__ = core
"""Core datastructures for Infogami.
"""
import web
import _json as simplejson
import copy

class InfobaseException(Exception):
    status = "500 Internal Server Error"
    def __init__(self, **kw):
        self.status = kw.pop('status', self.status)
        kw.setdefault('error', 'unknown')
        self.d = kw
        Exception.__init__(self)
        
    def __str__(self):
        return simplejson.dumps(self.d)
        
    def dict(self):
        return dict(self.d)
    
class NotFound(InfobaseException):
    status = "404 Not Found"
    def __init__(self, **kw):
        error = kw.pop('error', 'notfound')
        InfobaseException.__init__(self, error=error, **kw)

class UserNotFound(InfobaseException):
    status = "404 Not Found"
    def __init__(self, **kw):
        InfobaseException.__init__(self, error='user_notfound', **kw)
                
class PermissionDenied(InfobaseException):
    status = "403 Forbidden"
    def __init__(self, **kw):
        InfobaseException.__init__(self, error='permission_denied', **kw)

class BadData(InfobaseException):
    status = "400 Bad Request"
    
    def __init__(self, **kw):
        InfobaseException.__init__(self, error='bad_data', **kw)
        
class Conflict(InfobaseException):
    status = "409 Conflict"
    
    def __init__(self, **kw):
        InfobaseException.__init__(self, error="conflict", **kw)
    
class TypeMismatch(BadData):
    def __init__(self, type_expected, type_found, **kw):
        BadData.__init__(self, message="expected %s, found %s" % (type_expected, type_found), **kw)

class Text(unicode):
    """Python type for /type/text."""
    def __repr__(self):
        return "<text: %s>" % unicode.__repr__(self)
        
class Reference(unicode):
    """Python type for reference type."""
    def __repr__(self):
        return "<ref: %s>" % unicode.__repr__(self)

class Thing:
    def __init__(self, store, key, data):
        self._store = store
        self.key = key
        self._data = data

    def _process(self, value):
        if isinstance(value, list):
            return [self._process(v) for v in value]
        elif isinstance(value, dict):
            return web.storage((k, self._process(v)) for k, v in value.iteritems())
        elif isinstance(value, Reference):
            json = self._store.get(value)
            return Thing.from_json(self._store, unicode(value), json)
        else:
            return value

    def __contains__(self, key):
        return key in self._data

    def __getitem__(self, key):
        return self._process(self._data[key])
        
    def __setitem__(self, key, value):
        self._data[key] = value

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError, key
            
    def __eq__(self, other):
        return getattr(other, 'key', None) == self.key and getattr(other, '_data', None) == self._data
            
    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default
            
    def __repr__(self):
        return "<thing: %s>" % repr(self.key)
        
    def copy(self):
        return Thing(self._store, self.key, self._data.copy())
        
    def _get_data(self):
        return copy.deepcopy(self._data)

    def format_data(self):
        import common
        return common.format_data(self._get_data())

    def get_property(self, name):
        for p in self.get('properties', []):
            if p.get('name') == name:
                return p
        
    @staticmethod
    def from_json(store, key, data):
        return Thing.from_dict(store, key, simplejson.loads(data))
        
    @staticmethod
    def from_dict(store, key, data):
        import common
        data = common.parse_query(data)        
        return Thing(store, key, data)

class Store:
    """Storage for Infobase.
    
    Store manages one or many SiteStores. 
    """
    def create(self, sitename):
        """Creates a new site with the given name and returns store for it."""
        raise NotImplementedError
        
    def get(self, sitename):
        """Returns store object for the given sitename."""
        raise NotImplementedError
    
    def delete(self, sitename):
        """Deletes the store for the specified sitename."""
        raise NotImplementedError

class SiteStore:
    """Interface for Infobase data storage"""
    def get(self, key, revision=None):
        raise NotImplementedError
        
    def new_key(self, type, kw):
        """Generates a new key to create a object of specified type. 
        The store guarentees that it never returns the same key again.
        Optional keyword arguments can be specified to give more hints 
        to the store in generating the new key.
        """
        import uuid
        return '/' + str(uuid.uuid1())
        
    def get_many(self, keys):
        return [self.get(key) for key in keys]
    
    def write(self, query, timestamp=None, comment=None, machine_comment=None, ip=None, author=None):
        raise NotImplementedError
        
    def things(self, query):
        raise NotImplementedError
        
    def versions(self, query):
        raise NotImplementedError
        
    def get_user_details(self, key):
        """Returns a storage object with user email and encrypted password."""
        raise NotImplementedError
        
    def update_user_details(self, key, email, enc_password):
        """Update user's email and/or encrypted password.
        """
        raise NotImplementedError
            
    def find_user(self, email):
        """Returns the key of the user with the specified email."""
        raise NotImplementedError
        
    def register(self, key, email, encrypted):
        """Registers a new user.
        """
        raise NotImplementedError
        
    def transact(self, f):
        """Executes function f in a transaction."""
        raise NotImplementedError
        
    def initialze(self):
        """Initialzes the store for the first time.
        This is called before doing the bootstrap.
        """
        pass
        
    def set_cache(self, cache):
        pass

class Event:
    """Infobase Event.
    
    Events are fired when something important happens (write, new account etc.).
    Some code can listen to the events and do some action (like logging, updating external cache etc.).
    """
    def __init__(self, sitename, name, timestamp, ip, username, data):
        """Creates a new event.
        
        sitename - name of the site where the event is triggered.
        name - name of the event
        timestamp - timestamp of the event
        ip - client's ip address
        username - current user
        data - additional data of the event
        """
        self.sitename = sitename
        self.name = name
        self.timestamp = timestamp
        self.ip = ip
        self.username = username
        self.data = data

########NEW FILE########
__FILENAME__ = dbstore
"""Infobase Implementation based on database.
"""
import common
import config
import web
import _json as simplejson
import datetime, time
from collections import defaultdict
import logging

from _dbstore import store, sequence
from _dbstore.schema import Schema, INDEXED_DATATYPES
from _dbstore.indexer import Indexer
from _dbstore.save import SaveImpl, PropertyManager
from _dbstore.read import RecentChanges, get_bot_users

default_schema = None

logger = logging.getLogger("infobase")

def process_json(key, json):
    """Hook to process json.
    """
    return json

class DBSiteStore(common.SiteStore):
    """
    """
    def __init__(self, db, schema):
        self.db = db
        self.schema = schema
        self.sitename = None
        self.indexer = Indexer()
        self.store = store.Store(self.db)
        self.seq = sequence.SequenceImpl(self.db)
        
        self.cache = None
        self.property_manager = PropertyManager(self.db)
                
    def get_store(self):
        return self.store
        
    def set_cache(self, cache):
        self.cache = cache

    def get_metadata(self, key, for_update=False):
        # postgres doesn't seem to like Reference objects even though Referece extends from unicode.
        if isinstance(key, common.Reference):
            key = unicode(key)

        if for_update:
            d = self.db.query('SELECT * FROM thing WHERE key=$key FOR UPDATE NOWAIT', vars=locals())
        else:
            d = self.db.query('SELECT * FROM thing WHERE key=$key', vars=locals())
        return d and d[0] or None
        
    def get_metadata_list(self, keys):
        if not keys:
            return {}
            
        result = self.db.select('thing', what='*', where="key IN $keys", vars=locals()).list()
        d = dict((r.key, r) for r in result)
        return d
        
    def new_thing(self, **kw):
        return self.db.insert('thing', **kw)
        
    def get_metadata_from_id(self, id):
        d = self.db.query('SELECT * FROM thing WHERE id=$id', vars=locals())
        return d and d[0] or None

    def get_metadata_list_from_ids(self, ids):
        if not ids:
            return {}
            
        result = self.db.select('thing', what='*', where="id IN $ids", vars=locals()).list()
        d = dict((r.id, r) for r in result)
        return d
        
    def new_key(self, type, kw):
        seq = self.schema.get_seq(type)
        if seq:
            # repeat until a non-existing key is found.
            # This is required to prevent error in cases where an object with the next key is already created.
            while True:
                value = self.db.query("SELECT NEXTVAL($seq.name) as value", vars=locals())[0].value
                key = seq.pattern % value
                if self.get_metadata(key) is None:
                    return key
        else:
            return common.SiteStore.new_key(self, type, kw)
    
    def get(self, key, revision=None):
        if self.cache is None or revision is not None:
            json = self._get(key, revision)
        else:
            json = self.cache.get(key)
            if json is None:
                json = self._get(key, revision)
                if json:
                    self.cache[key] = json
        return process_json(key, json)
    
    def _get(self, key, revision):    
        metadata = self.get_metadata(key)
        if not metadata: 
            return None
        revision = revision or metadata.latest_revision
        d = self.db.query('SELECT data FROM data WHERE thing_id=$metadata.id AND revision=$revision', vars=locals())
        json = d and d[0].data or None
        return json
        
    def get_many_as_dict(self, keys):
        if not keys:
            return {}
            
        query = 'SELECT thing.key, data.data from thing, data' \
            + ' WHERE data.revision = thing.latest_revision and data.thing_id=thing.id' \
            + ' AND thing.key IN $keys'
            
        return dict((row.key, row.data) for row in self.db.query(query, vars=locals()))
        
    def get_many(self, keys):
        if not keys:
            return '{}'

        xkeys = [web.reparam('$k', dict(k=k)) for k in keys]
        query = 'SELECT thing.key, data.data from thing, data ' \
            + 'WHERE data.revision = thing.latest_revision and data.thing_id=thing.id ' \
            + ' AND thing.key IN (' + self.sqljoin(xkeys, ', ') + ')'
            
        def process(query):
            yield '{\n'
            for i, r in enumerate(self.db.query(query)):
                if i:
                    yield ',\n'
                yield simplejson.dumps(r.key)
                yield ": "
                yield process_json(r.key, r.data)
            yield '}'
        return "".join(process(query))
                    
    def save_many(self, docs, timestamp, comment, data, ip, author, action=None):
        docs = list(docs)
        action = action or "bulk_update"
        logger.debug("saving %d docs - %s", len(docs), dict(timestamp=timestamp, comment=comment, data=data, ip=ip, author=author, action=action))

        s = SaveImpl(self.db, self.schema, self.indexer, self.property_manager)
        
        # Hack to allow processing of json before using. Required for OL legacy.
        s.process_json = process_json
        
        docs = common.format_data(docs)
        changeset = s.save(docs, timestamp=timestamp, comment=comment, ip=ip, author=author, action=action, data=data)
        
        # update cache. 
        # Use the docs from result as they contain the updated revision and last_modified fields.
        for doc in changeset.get('docs', []):
            web.ctx.new_objects[doc['key']] = simplejson.dumps(doc)
            
        return changeset
        
    def save(self, key, doc, timestamp=None, comment=None, data=None, ip=None, author=None, transaction_id=None, action=None):
        logger.debug("saving %s", key)
        timestamp = timestamp or datetime.datetime.utcnow
        return self.save_many([doc], timestamp, comment, data, ip, author, action=action or "update")
        
    def reindex(self, keys):
        s = SaveImpl(self.db, self.schema, self.indexer, self.property_manager)
        # Hack to allow processing of json before using. Required for OL legacy.
        s.process_json = process_json        
        return s.reindex(keys)
        
    def get_property_id(self, type, name):
        return self.property_manager.get_property_id(type, name)

    def things(self, query):
        type = query.get_type()
        if type:
            type_metedata = self.get_metadata(type)
            if type_metedata:
                type_id = type_metedata.id
            else:
                # Return empty result when type not found
                return []
        else:
            type_id = None
        
        # type is required if there are conditions/sort on keys other than [key, type, created, last_modified]
        common_properties = ['key', 'type', 'created', 'last_modified'] 
        _sort = query.sort and query.sort.key
        if _sort and _sort.startswith('-'):
            _sort = _sort[1:]
        type_required = bool([c for c in query.conditions if c.key not in common_properties]) or (_sort and _sort not in common_properties)
        
        if type_required and type is None:
            raise common.BadData("Type Required")
        
        class DBTable:
            def __init__(self, name, label=None):
                self.name = name
                self.label = label or name
                
            def sql(self):
                if self.label != self.name:
                    return "%s as %s" % (self.name, self.label)
                else:
                    return self.name
                    
            def __repr__(self):
                return self.label
                
        class Literal:
            def __init__(self, value):
                self.value = value
                
            def __repr__(self):
                return self.value

        tables = {}
        
        def get_table(datatype, key):
            if key not in tables:
                assert type is not None, "Missing type"            
                table = self.schema.find_table(type, datatype, key)
                label = 'd%d' % len(tables)
                tables[key] = DBTable(table, label)
            return tables[key]
            
        wheres = []
        
        def process(c, ordering_func=None):
            # ordering_func is used when the query contains emebbabdle objects
            #
            # example: {'links': {'title: 'foo', 'url': 'http://example.com/foo'}}
            if c.datatype == 'ref':
                metadata = self.get_metadata(c.value)
                if metadata is None:
                    # required object is not found so the query result wil be empty. 
                    # Raise StopIteration to indicate empty result.
                    raise StopIteration
                c.value = metadata.id
            if c.op == '~':
                op = Literal('LIKE')
                c.value = c.value.replace('*', '%')
            else:
                op = Literal(c.op)
                
            if c.key in ['key', 'type', 'created', 'last_modified']:
                #@@ special optimization to avoid join with thing.type when there are non-common properties in the query.
                #@@ Since type information is already present in property table, 
                #@@ getting property id is equivalent to join with type.
                if c.key == 'type' and type_required:
                    return
                    
                if isinstance(c.value, list):
                    q = web.sqlors('thing.%s %s ' % (c.key, op), c.value)
                else:
                    q = web.reparam('thing.%s %s $c.value' % (c.key, op), locals())
                xwheres = [q]
                
                # Add thing table explicitly because get_table is not called
                tables['_thing'] = DBTable("thing")
            else:
                table = get_table(c.datatype, c.key)
                key_id = self.get_property_id(type, c.key)
                if not key_id:
                    raise StopIteration
                    
                q1 = web.reparam('%(table)s.key_id=$key_id' % {'table': table}, locals())
                
                if isinstance(c.value, list):
                    q2 = web.sqlors('%s.value %s ' % (table, op), c.value)
                else:
                    q2 = web.reparam('%s.value %s $c.value' % (table, op), locals())
                
                xwheres = [q1, q2]
                if ordering_func:
                    xwheres.append(ordering_func(table))
            wheres.extend(xwheres)
            
        def make_ordering_func():
            d = web.storage(table=None)
            def f(table):
                d.table = d.table or table
                if d.table == table:
                    # avoid a comparsion when both tables are same. it fails when ordering is None
                    return "1 = 1"
                else:
                    return '%s.ordering = %s.ordering' % (table, d.table)
            return f
            
        import readquery
        def process_query(q, ordering_func=None):
            for c in q.conditions:
                if isinstance(c, readquery.Query):
                    process_query(c, ordering_func or make_ordering_func())
                else:
                    process(c, ordering_func)
                    
        def process_sort(query):
            """Process sort field in the query and returns the db column to order by."""
            if query.sort:
                sort_key = query.sort.key
                if sort_key.startswith('-'):
                    ascending = " desc"
                    sort_key = sort_key[1:]
                else:
                    ascending = ""
                    
                if sort_key in ['key', 'type', 'created', 'last_modified']:
                    order = 'thing.' + sort_key # make sure c.key is valid
                    # Add thing table explicitly because get_table is not called
                    tables['_thing'] = DBTable("thing")                
                else:   
                    table = get_table(query.sort.datatype, sort_key)
                    key_id = self.get_property_id(type, sort_key)
                    if key_id is None:
                        raise StopIteration
                    q = '%(table)s.key_id=$key_id' % {'table': table}
                    wheres.append(web.reparam(q, locals()))
                    order = table.label + '.value'
                return order + ascending
            else:
                return None
        
        try:
            process_query(query)
            # special care for case where query {}.
            if not tables:
                tables['_thing'] = DBTable('thing')
            order = process_sort(query)
        except StopIteration:
            return []
            
        def add_joins():
            labels = [t.label for t in tables.values()]
            def get_column(table):
                if table == 'thing': return 'thing.id'
                else: return table + '.thing_id'
                
            if len(labels) > 1:
                x = labels[0]
                xwheres = [get_column(x) + ' = ' + get_column(y) for y in labels[1:]]
                wheres.extend(xwheres)
        
        add_joins()
        wheres = wheres or ['1 = 1']
        table_names = [t.sql() for t in tables.values()]

        t = self.db.transaction()
        if config.query_timeout:
            self.db.query("SELECT set_config('statement_timeout', $query_timeout, false)", dict(query_timeout=config.query_timeout))
            
        if 'thing' in table_names:
            result = self.db.select(
                what='thing.key', 
                tables=table_names, 
                where=self.sqljoin(wheres, ' AND '), 
                order=order,
                limit=query.limit, 
                offset=query.offset,
                )
            keys = [r.key for r in result]
        else:
            result = self.db.select(
                what='d0.thing_id', 
                tables=table_names, 
                where=self.sqljoin(wheres, ' AND '), 
                order=order,
                limit=query.limit, 
                offset=query.offset,
            )
            ids = [r.thing_id for r in result]
            rows = ids and self.db.query('SELECT id, key FROM thing where id in $ids', vars={"ids": ids})
            d = dict((r.id, r.key) for r in rows)
            keys = [d[id] for id in ids]
        t.commit()
        return keys
        
    def sqljoin(self, queries, delim):
        return web.SQLQuery.join(queries, delim)
        
    def recentchanges(self, query):
        """Returns the list of changes matching the given query.
        
        Sample Queries:
            {"limit": 10, "offset": 100}
            {"limit": 10, "offset": 100, "key": "/authors/OL1A"}
            {"limit": 10, "offset": 100, "author": "/people/foo"}
        """
        engine = RecentChanges(self.db)
        
        limit = query.pop("limit", 1000)
        offset = query.pop("offset", 0)
        
        keys = "key", "author", "ip", "kind", "bot", "begin_date", "end_date", "data"
        kwargs = dict((k, query[k]) for k in keys if k in query)
        
        return engine.recentchanges(limit=limit, offset=offset, **kwargs)
        
    def get_change(self, id):
        """Return the info about the requrested change.
        """
        engine = RecentChanges(self.db)
        return engine.get_change(id)
        
    def versions(self, query):
        what = 'thing.key, version.revision, transaction.*'
        where = 'version.thing_id = thing.id AND version.transaction_id = transaction.id'

        if config.get('use_machine_comment'):
            what += ", version.machine_comment"
            
        def get_id(key):
            meta = self.get_metadata(key)
            if meta:
                return meta.id
            else:
                raise StopIteration
        
        for c in query.conditions:
            key, value = c.key, c.value
            assert key in ['key', 'type', 'author', 'ip', 'comment', 'created', 'bot', 'revision']
            
            try:
                if key == 'key':
                    key = 'thing_id'
                    value = get_id(value)
                elif key == 'revision':
                    key = 'version.revision'
                elif key == 'type':
                    key = 'thing.type'
                    value = get_id(value)
                elif key == 'author':
                    key = 'transaction.author_id'
                    value = get_id(value)
                else:
                    # 'bot' column is not enabled
                    if key == 'bot' and not config.use_bot_column:
                        bots = get_bot_users(self.db)
                        if value == True or str(value).lower() == "true":
                            where += web.reparam(" AND transaction.author_id IN $bots", {"bots": bots})
                        else:
                            where += web.reparam(" AND (transaction.author_id NOT IN $bots OR transaction.author_id IS NULL)", {"bots": bots})
                        continue
                    else:
                        key = 'transaction.' + key
            except StopIteration:
                # StopIteration is raised when a non-existing object is referred in the query
                return []
                
            where += web.reparam(' AND %s=$value' % key, locals())
            
        sort = query.sort
        if sort and sort.startswith('-'):
            sort = sort[1:] + ' desc'

        sort = 'transaction.' + sort
        
        t = self.db.transaction()
        if config.query_timeout:
            self.db.query("SELECT set_config('statement_timeout', $query_timeout, false)", dict(query_timeout=config.query_timeout))
                
        result = self.db.select(['thing','version', 'transaction'], what=what, where=where, offset=query.offset, limit=query.limit, order=sort)
        result = result.list()
        author_ids = list(set(r.author_id for r in result if r.author_id))
        authors = self.get_metadata_list_from_ids(author_ids)
        
        t.commit()
        
        for r in result:
            r.author = r.author_id and authors[r.author_id].key
        return result
    
    def get_user_details(self, key):
        """Returns a storage object with user email and encrypted password."""
        metadata = self.get_metadata(key)
        if metadata is None:
            return None
            
        d = self.db.query("SELECT * FROM account WHERE thing_id=$metadata.id", vars=locals())
        return d and d[0] or None
        
    def update_user_details(self, key, **params):
        """Update user's email and/or encrypted password."""
        metadata = self.get_metadata(key)
        if metadata is None:
            return None
            
        for k, v in params.items():
            assert k in ['bot', 'active', 'verified', 'email', 'password']
            if v is None:
                del params[k]
        
        self.db.update('account', where='thing_id=$metadata.id', vars=locals(), **params)
            
    def register(self, key, email, enc_password):
        metadata = self.get_metadata(key)
        self.db.insert('account', False, email=email, password=enc_password, thing_id=metadata.id)
        
    def transact(self, f):
        t = self.db.transaction()
        try:
            f()
        except:
            t.rollback()
            raise
        else:
            t.commit()
    
    def find_user(self, email):
        """Returns the key of the user with the specified email."""
        d = self.db.select('account', where='email=$email', vars=locals())
        thing_id = d and d[0].thing_id or None
        return thing_id and self.get_metadata_from_id(thing_id).key
    
    def initialize(self):
        if not self.initialized():
            t = self.db.transaction()
            
            id = self.new_thing(key='/type/type')
            last_modified = datetime.datetime.utcnow()
            
            data = dict(
                key='/type/type',
                type={'key': '/type/type'},
                last_modified={'type': '/type/datetime', 'value': last_modified},
                created={'type': '/type/datetime', 'value': last_modified},
                revision=1,
                latest_revision=1,
                id=id
            )
            
            self.db.update('thing', type=id, where='id=$id', vars=locals())
            self.db.insert('version', False, thing_id=id, revision=1)
            self.db.insert('data', False, thing_id=id, revision=1, data=simplejson.dumps(data))
            t.commit()
            
    def initialized(self):
        return self.get_metadata('/type/type') is not None
        
    def delete(self):
        t = self.db.transaction()
        self.db.delete('data', where='1=1')
        self.db.delete('version', where='1=1')
        self.db.delete('transaction', where='1=1')
        self.db.delete('account', where='1=1')
        
        for table in self.schema.list_tables():
            self.db.delete(table, where='1=1')
            
        self.db.delete('property', where='1=1')
        self.db.delete('thing', where='1=1')
        t.commit()
        self.cache.clear()

class DBStore(common.Store):
    """StoreFactory that works with single site. 
    It always returns a the same site irrespective of the sitename.
    """
    def __init__(self, schema):
        self.schema = schema
        self.sitestore = None
        self.db = create_database(**web.config.db_parameters)
        
    def has_initialized(self):
        try:
            self.db.select('thing', limit=1)
            return True
        except:
            return False
        
    def create(self, sitename):
        if self.sitestore is None:
            self.sitestore = DBSiteStore(self.db, self.schema)
            if not self.has_initialized():
                q = str(self.schema.sql())
                self.db.query(web.SQLQuery([q]))
        self.sitestore.initialize()
        return self.sitestore
        
    def get(self, sitename):
        if self.sitestore is None:
            sitestore = DBSiteStore(self.db, self.schema)
            if not self.has_initialized():
                return None
            self.sitestore = sitestore
            
        if not self.sitestore.initialized():
            return None            
        return self.sitestore

    def delete(self, sitename):
        if not self.has_initialized():
            return
        d = self.get(sitename)
        d and d.delete()
            
class MultiDBStore(DBStore):
    """DBStore that works with multiple sites.
    """
    def __init__(self, schema):
        self.schema = schema
        self.sitestores = {}
        self.db = create_database(**web.config.db_parameters)
        
    def create(self, sitename):
        t = self.db.transaction()
        try:
            site_id = self.db.insert('site', name=sitename)
            sitestore = MultiDBSiteStore(self.db, self.schema, sitename, site_id)
            sitestore.initialize()
            self.sitestores[sitename] = sitestore
        except:
            t.rollback()
            raise
        else:
            t.commit()
            return self.sitestores[sitename]
            
    def get(self, sitename):
        if sitename not in self.sitestores:
            site_id = self.get_site_id(sitename)
            if site_id is None:
                return None
            else:
                self.sitestores[sitename] = MultiDBSiteStore(self.schema, sitename, site_id)
        return self.sitestores[sitename]
        
    def get_site_id(self, sitename):
        d = self.db.query('SELECT * FROM site WHERE name=$sitename', vars=locals())
        return d and d[0].id or None
        
    def delete(self, sitename):
        pass
            
class MultiDBSiteStore(DBSiteStore):
    def __init__(self, db, schema, sitename, site_id):
        DBStore.__init__(self, db, schema)
        self.sitename = sitename
        self.site_id = site_id
        
    def get_metadata(self, key):
        d = self.db.query('SELECT * FROM thing WHERE site_id=self.site_id AND key=$key', vars=locals())
        return d and d[0] or None
        
    def get_metadata_list(self, keys):
        where = web.reparam('site_id=$self.site_id', locals()) + web.sqlors('key=', keys)
        result = self.db.select('thing', what='*', where=where).list()
        d = dict((r.key, r) for r in result)
        return d
        
    def new_thing(self, **kw):
        kw['site_id'] = self.site_id
        return self.db.insert('thing', **kw)
        
    def new_account(self, thing_id, email, enc_password):
        return self.db.insert('account', False, site_id=self.site_id, thing_id=thing_id, email=email, password=enc_password)

    def find_user(self, email):
        """Returns the key of the user with the specified email."""
        d = self.db.select('account', where='site_id=$self.site_id, $email=email', vars=locals())
        thing_id = d and d[0].thing_id or None
        return thing_id and self.get_metadata_from_id(thing_id).key
    
    def delete(self):
        pass

def create_database(**params):
    db = web.database(**params)
    
    # monkey-patch query method to collect stats
    _query = db.query
    def query(*a, **kw):
        t_start = time.time()
        result = _query(*a, **kw)
        t_end = time.time()
        
        web.ctx.querytime = web.ctx.get("querytime", 0.0) + t_end - t_start
        web.ctx.queries = web.ctx.get("queries", 0) + 1
        
        return result
        
    db.query = query
    return db
    
if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = infobase
"""
Infobase: structured database.

Infobase is a structured database which contains multiple sites.
Each site is an independent collection of objects. 
"""
import web
import datetime
import simplejson

import common
import config
import readquery
import writequery

# important: this is required here to setup _loadhooks and unloadhooks
import cache

class Infobase:
    """Infobase contains multiple sites."""
    def __init__(self, store, secret_key):
        self.store = store
        self.secret_key = secret_key
        self.sites = {}
        self.event_listeners = []
        
        if config.startup_hook:
            config.startup_hook(self)
        
    def create(self, sitename):
        """Creates a new site with the sitename."""
        site = Site(self, sitename, self.store.create(sitename), self.secret_key)
        site.bootstrap()
        self.sites[sitename] = site
        return site
    
    def get(self, sitename):
        """Returns the site with the given name."""
        if sitename in self.sites:
            site = self.sites[sitename]
        else:
            store = self.store.get(sitename)
            if store is None:
                return None
            site = Site(self, sitename, self.store.get(sitename), self.secret_key)
            self.sites[sitename] = site
        return site
        
    def delete(self, sitename):
        """Deletes the site with the given name."""
        if sitename in self.sites:
            del self.sites[sitename]
        return self.store.delete(sitename)
        
    def add_event_listener(self, listener):
        self.event_listeners.append(listener)
    
    def remove_event_listener(self, listener):
        try:
            self.event_listeners.remove(listener)
        except ValueError:
            pass

    def fire_event(self, event):
        for listener in self.event_listeners:
            try:
                listener(event)
            except:
                common.record_exception()
                pass

class Site:
    """A site of infobase."""
    def __init__(self, _infobase, sitename, store, secret_key):
        self._infobase = _infobase
        self.sitename = sitename
        self.store = store
        self.cache = cache.Cache()
        self.store.set_cache(self.cache)
        import account
        self.account_manager = account.AccountManager(self, secret_key)
        
        self._triggers = {}
        store.store.set_listener(self._log_store_action)
        store.seq.set_listener(self._log_store_action)
        
    def _log_store_action(self, name, data):
        event = web.storage(name=name, ip=web.ctx.ip, author=None, data=data, sitename=self.sitename, timestamp=None)
        self._infobase.fire_event(event)
        
    def get_account_manager(self):
        return self.account_manager
        
    def get_store(self):
        return self.store.get_store()
        
    def get_seq(self):
        return self.store.seq
        
    def delete(self):
        return self._infobase.delete(self.sitename)
    
    def get(self, key, revision=None):
        return self.store.get(key, revision)
        
    withKey = get
    
    def _get_thing(self, key, revision=None):
        json = self.get(key, revision)
        return json and common.Thing.from_json(self.store, key, json)
        
    def _get_many_things(self, keys):
        json = self.get_many(keys)
        d = simplejson.loads(json)
        return dict((k, common.Thing.from_dict(self.store, k, doc)) for k, doc in d.items())

    def get_many(self, keys):
        return self.store.get_many(keys)
        
    def new_key(self, type, kw=None):
        return self.store.new_key(type, kw or {})
        
    def write(self, query, timestamp=None, comment=None, data=None, ip=None, author=None, action=None, _internal=False):
        timestamp = timestamp or datetime.datetime.utcnow()
        
        author = author or self.get_account_manager().get_user()
        p = writequery.WriteQueryProcessor(self.store, author)
        
        items = p.process(query)
        items = (item for item in items if item)
        changeset = self.store.save_many(items, timestamp, comment, data, ip, author and author.key, action=action)
        result = changeset.get('docs', [])

        created = [r['key'] for r in result if r and r['revision'] == 1]
        updated = [r['key'] for r in result if r and r['revision'] != 1]

        result2 = web.storage(created=created, updated=updated)
        
        if not _internal:
            event_data = dict(comment=comment, data=data, query=query, result=result2, changeset=changeset)
            self._fire_event("write", timestamp, ip, author and author.key, event_data)
            
        self._fire_triggers(result)

        return result2
    
    def save(self, key, doc, timestamp=None, comment=None, data=None, ip=None, author=None, action=None):
        timestamp = timestamp or datetime.datetime.utcnow()
        author = author or self.get_account_manager().get_user()
        ip = ip or web.ctx.get('ip', '127.0.0.1')
        
        #@@ why to have key argument at all?
        doc['key'] = key
        
        p = writequery.SaveProcessor(self.store, author)
        doc = p.process(key, doc)
        
        if not doc:
            return {}
        else:
            changeset = self.store.save(key, doc, timestamp, comment, data, ip, author and author.key, action=action)
            saved_docs = changeset.get("docs")
            saved_doc = saved_docs[0] 
            result={"key": saved_doc['key'], "revision": saved_doc['revision']}
            
            event_data = dict(comment=comment, key=key, query=doc, result=result, changeset=changeset)
            self._fire_event("save", timestamp, ip, author and author.key, event_data)
            self._fire_triggers([saved_doc])
            return result
    
    def save_many(self, query, timestamp=None, comment=None, data=None, ip=None, author=None, action=None):
        timestamp = timestamp or datetime.datetime.utcnow()
        author = author or self.get_account_manager().get_user()
        ip = ip or web.ctx.get('ip', '127.0.0.1')
        
        p = writequery.SaveProcessor(self.store, author)

        items = p.process_many(query)
        if not items:
            return []
            
        changeset = self.store.save_many(items, timestamp, comment, data, ip, author and author.key, action=action)
        saved_docs = changeset.get('docs')
        
        result = [{"key": doc["key"], "revision": doc['revision']} for doc in saved_docs]
        event_data = dict(comment=comment, query=query, result=result, changeset=changeset)
        self._fire_event("save_many", timestamp, ip, author and author.key, event_data)

        self._fire_triggers(saved_docs)
        return result

    def _fire_event(self, name, timestamp, ip, username, data):
        event = common.Event(self.sitename, name, timestamp, ip, username, data)
        self._infobase.fire_event(event)
        
    def things(self, query):
        return readquery.run_things_query(self.store, query)
        
    def versions(self, query):
        try:
            q = readquery.make_versions_query(self.store, query)
        except ValueError:
            # ValueError is raised if unknown keys are used in the query. 
            # Invalid keys shouldn't make the query fail, instead the it should result in no match.
            return []
            
        return self.store.versions(q)
        
    def recentchanges(self, query):
        return self.store.recentchanges(query)
        
    def get_change(self, id):
        return self.store.get_change(id)
        
    def get_permissions(self, key):
        author = self.get_account_manager().get_user()
        engine = writequery.PermissionEngine(self.store)
        perm = engine.has_permission(author, key)
        return web.storage(write=perm, admin=perm)
        
    def bootstrap(self, admin_password='admin123'):
        import bootstrap
        web.ctx.ip = '127.0.0.1'
        
        import cache
        cache.loadhook()
        
        bootstrap.bootstrap(self, admin_password)
        
    def add_trigger(self, type, func):
        """Registers a trigger to call func when object of specified type is modified. 
        If type=None is specified then the trigger is called for every modification.
        func is called with old object and new object as arguments. old object will be None if the object is newly created.
        """
        self._triggers.setdefault(type, []).append(func)
                
    def _fire_triggers(self, result):
        """Executes all required triggers on write."""
        def fire_trigger(type, old, new):
            triggers = self._triggers.get(type['key'], []) + self._triggers.get(None, [])
            for t in triggers:
                try:
                    t(self, old, new)
                except:
                    print >> web.debug, 'Failed to execute trigger', t
                    import traceback
                    traceback.print_exc()
        
        if not self._triggers:
            return
        
        created = [doc['key'] for doc in result if doc and doc['revision'] == 1]
        updated = [doc['key'] for doc in result if doc and doc['revision'] != 1]
        
        things = dict((doc['key'], doc) for doc in result)
        
        for key in created:
            thing = things[key]
            fire_trigger(thing['type'], None, thing)
        
        for key in updated:
            thing = things[key]
            
            # old_data (the second argument) is not used anymore. 
            # TODO: Remove the old_data argument.
            fire_trigger(thing['type'], None, thing)
            
            #old = self._get_thing(key, thing.revision-1)
            #if old.type.key == thing.type.key:
            #    fire_trigger(thing.type, old, thing)
            #else:
            #    fire_trigger(old.type, old, thing)
            #    fire_trigger(thing.type, old, thing)
########NEW FILE########
__FILENAME__ = logger
"""
Infobase Logger module.

Infogami log file is a stream of events where each event is a dictionary represented in JSON format having keys [`action`, `site`, `data`].

   * action: Name of action being logged. Possible values are write, new_account and update_object.
   * site: Name of site
   * data: data associated with the event. This data is used for replaying that action.

Log files are circulated on daily basis. Default log file format is $logroot/yyyy/mm/dd.log.
"""

import datetime, time
import _json as simplejson
import os
import threading

def synchronize(f):
    """decorator to synchronize a method."""
    def g(self, *a, **kw):
        if not getattr(self, '_lock'):
            self._lock = threading.Lock()
            
        self._lock.acquire()
        try:
            return f(self, *a, **kw)
        finally:
            self._lock.release()
            
    return f

def to_timestamp(iso_date_string):
    """
        >>> t = '2008-01-01T01:01:01.010101'
        >>> to_timestamp(t).isoformat()
        '2008-01-01T01:01:01.010101'
    """
    #@@ python datetime module is ugly. 
    #@@ It takes so much of work to create datetime from isoformat.
    date, time = iso_date_string.split('T', 1)
    y, m, d = date.split('-')
    H, M, S = time.split(':')
    S, ms = S.split('.')
    return datetime.datetime(*map(int, [y, m, d, H, M, S, ms]))
            
class DummyLogger:
    def __init__(self, *a, **kw):
        pass
    
    def on_write(self, *a, **kw):
        pass
        
    def on_new_account(self, *a, **kw):
        pass
        
    def on_update_account(self, *a, **kw):
        pass
        
    def __call__(self, event):
        pass
    
class Logger:
    def __init__(self, root, compress=False):
        self.root = root
        if compress:
            import gzip
            self.extn = ".log.gz"
            self._open = gzip.open
        else:
            self.extn = ".log"
            self._open = open
        
    def get_path(self, timestamp=None):
        timestamp = timestamp or datetime.datetime.utcnow()
        date = timestamp.date()
        return os.path.join(self.root, "%02d" % date.year, "%02d" % date.month, "%02d" % date.day) + self.extn
            
    def __call__(self, event):
        import web
        data = event.data.copy()
        event.timestamp = event.timestamp or datetime.datetime.utcnow()
        if event.name in ['write', 'save', 'save_many']:
            name = event.name
            data['ip'] = event.ip
            data['author'] = event.username
        elif event.name == 'register':
            # data will already contain username, password, email and displayname
            name = "new_account"
            data['ip'] = event.ip
        elif event.name == 'update_user':
            name = "update_account"
            data['ip'] = event.ip
        elif event.name.startswith("store."):
            name = event.name
        else:
            return
            
        self.write(name, event.sitename, event.timestamp, data)
        
    @synchronize
    def write(self, action, sitename, timestamp, data):
        path = self.get_path(timestamp)
        dir = os.path.dirname(path)
        if not os.path.exists(dir):
            os.makedirs(dir)
        f = self._open(path, 'a')
        f.write(simplejson.dumps(dict(action=action, site=sitename, timestamp=timestamp.isoformat(), data=data)))
        f.write('\n')
        f.flush()
        #@@ optimize: call fsync after all modifications are written instead of calling for every modification
        os.fsync(f.fileno())
        f.close()

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = logreader
"""
Log file reader.
"""
import os
import itertools
import datetime
import time
import web
import glob

try:
    import _json as simplejson
except ImportError:
    # make sure this module can be used indepent of infobase.
    import simplejson

def nextday(date):
    return date + datetime.timedelta(1)
    
def daterange(begin, end=None):
    """Return an iterator over dates from begin to end (inclusive). 
    If end is not specified, end is taken as utcnow."""
    end = end or datetime.datetime.utcnow().date()

    if isinstance(begin, datetime.datetime):
        begin = begin.date()
    if isinstance(end, datetime.datetime):
        end = end.date()

    while begin <= end:
        yield begin
        begin = nextday(begin)
        
def ijoin(iters):
    """Joins given list of iterators as a single iterator.
    
        >>> list(ijoin([xrange(0, 5), xrange(10, 15)]))
        [0, 1, 2, 3, 4, 10, 11, 12, 13, 14]
    """
    return (x for it in iters for x in it)
    
def to_timestamp(iso_date_string):
    """
        >>> t = '2008-01-01T01:01:01.010101'
        >>> to_timestamp(t).isoformat()
        '2008-01-01T01:01:01.010101'
    """
    #@@ python datetime module is ugly. 
    #@@ It takes so much of work to create datetime from isoformat.
    date, time = iso_date_string.split('T', 1)
    y, m, d = date.split('-')
    H, M, S = time.split(':')
    S, ms = S.split('.')
    return datetime.datetime(*map(int, [y, m, d, H, M, S, ms]))
    
class LogReader:
    """
    Reads log file line by line and converts each line to python dict using simplejson.loads.
    """
    def __init__(self, logfile):
        self.logfile = logfile
        
    def skip_till(self, timestamp):
        """Skips the log file till the specified timestamp.
        """
        self.logfile.skip_till(timestamp.date())
        
        offset = self.logfile.tell()
        for entry in self:
            if entry.timestamp > timestamp:
                # timestamp of this entry is more than the required timestamp.
                # so it must be put back.
                self.logfile.seek(offset)
                break
            offset = self.logfile.tell()
                
    def read_entry(self):
        """Reads one entry from the log.
        None is returned when there are no more enties.
        """
        line = self.logfile.read()
        if line:
            return self._loads(line)
        else:
            return None
            
    def read_entries(self, n=1000000):
        """"Reads multiple enties from the log. The maximum entries to be read is specified as argument.
        """
        return [self._loads(line) for line in self.logfile.readlines(n)]
        
    def __iter__(self):
        for line in self.logfile:
            yield self._loads(line)

    def _loads(self, line):
        entry = simplejson.loads(line)
        entry = web.storage(entry)
        entry.timestamp = to_timestamp(entry.timestamp)
        return entry

class LogFile:
    """A file like interface over log files.
    
    Infobase log files are ordered by date. The presence of multiple files
    makes it difficult to read the them. This class provides a file like
    interface to make reading easier.
    
    Read all enties from a given timestamp::
    
        log = LogFile("log")
        log.skip_till(datetime.datetime(2008, 01, 01))
        
        for line in log:
            print log

    Read log entries in chunks::
    
        log = LogFile("log")
        while True:
            # read upto a maximum of 1000 lines
            lines = log.readlines(1000)
            if lines:
                do_something(lines)
            else:
                break

    Read log entries infinitely::

        log = LogFile("log")
        while True:
            # read upto a maximum of 1000 lines
            lines = log.readlines(1000)
            if lines:
                do_something(lines)
            else:
                time.sleep(10) # wait for more data to come
                
    Remember the offset and set the offset::
    
        offset = log.tell()
        log.seek(offset)
    """
    def __init__(self, root):
        self.root = root
        self.extn = ".log"
        
        self.file = None
        self.filelist = None
        self.current_filename = None
        
    def skip_till(self, date):
        """Skips till file with the specified date.
        """
        self.filelist = self.find_filelist(date)
        self.advance()
        
    def update(self):
        self.update_filelist(self.current_filename)
        
        if self.current_filename is None and self.filelist:
            self.advance()
            
    def update_filelist(self, current_filename=None):
        if current_filename:
            current_date = self.file2date(current_filename)
            self.filelist = self.find_filelist(nextday(current_date))
        else:
            self.filelist = self.find_filelist()
        
    def file2date(self, file):
        file, ext = os.path.splitext(file)
        _, year, month, day = file.rsplit('/', 3)
        return datetime.date(int(year), int(month), int(day))
        
    def date2file(self, date):
        return "%s/%04d/%02d/%02d.log" % (self.root, date.year, date.month, date.day)
        
    def advance(self):
        """Move to next file."""
        if self.filelist:
            self.current_filename = self.filelist.pop(0)
            self.file = open(self.current_filename)
            return True
        else:
            return False
        
    def find_filelist(self, from_date=None):
        if from_date is None:
            filelist = glob.glob('%s/[0-9][0-9][0-9][0-9]/[0-9][0-9]/[0-9][0-9].log' % self.root)
            filelist.sort()
        else:
            filelist = [self.date2file(date) for date in daterange(from_date)]
            filelist = [f for f in filelist if os.path.exists(f)]

        return filelist
        
    def readline(self, do_update=True):
        line = self.file and self.file.readline()
        if line:
            return line
        elif self.filelist:
            self.advance()
            return self.readline()
        else:
            if do_update:
                self.update()
                return self.readline(do_update=False)
            else:
                return ""
                
    def __iter__(self):
        while True:
            line = self.readline()
            if line:
                yield line
            else:
                break
    
    def readlines(self, n=1000000):
        """Reads multiple lines from the log file."""
        lines = self._readlines()
        if not lines:
            self.update()
            lines = self._readlines()
        return lines
        
    def _readlines(self, n):
        lines = []
        for i in range(n):
            line = self.readline(do_update=False)
            if not line:
                break
            lines.append(line)
        return lines
        
    def seek(self, offset):
        date, offset = offset.split(':')
        year, month, day = date.split("-")
        year, month, day, offset = int(year), int(month), int(day), int(offset)
        
        d = datetime.date(year, month, day)
        self.filelist = self.find_filelist(d)
        self.advance()
        
        if self.current_filename and self.file2date(self.current_filename) == d:
            self.file.seek(offset)
        
    def tell(self):
        if self.current_filename is None:
            return datetime.date.fromtimestamp(0).isoformat() + ":0"
            
        date = self.file2date(self.current_filename)
        offset = self.file.tell()
        return "%04d-%02d-%02d:%d" % (date.year, date.month, date.day, offset)

class RsyncLogFile(LogFile):
    """File interface to Remote log files. rsync is used for data transfer.
    
        log = RsyncLogFile("machine::module_name/path", "log")
        
        for line in log:
            print line
    """
    def __init__(self, rsync_root, root):
        LogFile.__init__(self, root)
        self.rsync_root = rsync_root
        if not self.rsync_root.endswith('/'):
            self.rsync_root += "/"
        self.rsync()

    def update(self):
        self.rsync()
        LogFile.update(self)

        if self.file:
            # if the current file is updated, it will be overwritten and possibly with a different inode.
            # Solving the problem by opening the file again and jumping to the current location
            file = open(self.file.name)
            file.seek(self.file.tell())
            self.file = file
        
    def rsync(self):
        cmd = "rsync -r %s %s" % (self.rsync_root, self.root)
        print cmd
        os.system(cmd)

class LogPlayback:
    """Playback log"""
    def __init__(self, infobase):
        self.infobase = infobase
        
    def playback_stream(self, entries):
        """Playback all entries from the specified log stream."""
        for entry in entries:
            self.playback(entry)
            
    def playback(self, entry):
        """Playback one log entry."""
        web.ctx.infobase_auth_token = None
        #@@ hack to disable permission check
        web.ctx.disable_permission_check = True
        site = self.infobase.get(entry.site)
        return getattr(self, entry.action)(site, entry.timestamp, entry.data)
    
    def write(self, site, timestamp, data):
        d = web.storage(data)
        author = d.author and site.withKey(d.author)
        return site.write(d.query, comment=d.comment, machine_comment=d.machine_comment, ip=d.ip, author=author, timestamp=timestamp)
        
    def save(self, site, timestamp, data):
        d = web.storage(data)
        author = d.author and site.withKey(d.author)
        return site.save(d.key, d.query, comment=d.comment, machine_comment=d.machine_comment, ip=d.ip, author=author, timestamp=timestamp)
                
    def new_account(self, site, timestamp, data):
        d = web.storage(data)
        a = site.get_account_manager()
        return a.register1(username=d.username, email=d.email, enc_password=d.password, data=dict(displayname=d.displayname), ip=d.ip, timestamp=timestamp)
        
    def update_account(self, site, timestamp, data):
        d = web.storage(data)
        user = site.withKey(d.username)
        a = site.get_account_manager()
        return a.update_user1(user, 
            enc_password=d.get('password'), 
            email=d.get('email'),
            ip = d.ip,
            timestamp=timestamp)
    
if __name__ == "__main__":
    import doctest
    doctest.testmod()
    
########NEW FILE########
__FILENAME__ = lru
"""Infobase cache.
"""
                    
class Node(object):
    """Queue Node."""
    __slots__ = ["key", "value", "next", "prev"]
    def __init__(self, key):
        self.key = key
        self.value = None
        self.next = None
        self.prev = None
        
    def __str__(self):
        return str(self.key)
        
    __repr__ = __str__
    
class Queue:
    """Classic Queue Datastructure with O(1) inserts and deletes.
    
        >>> q = Queue()
        >>> q
        []
        >>> a, b, c = Node(1), Node(2), Node(3)
        >>> q.insert(a)
        >>> q.insert(b)
        >>> q.insert(c)
        >>> q
        [1, 2, 3]
        >>> q.peek()
        1
        >>> q.remove(b)
        2
        >>> q
        [1, 3]
        >>> q.remove()
        1
        >>> q.remove()
        3
        >>> q.remove()
        Traceback (most recent call last):
            ... 
        Exception: Queue is empty
    """
    def __init__(self):
        # circular linked-list implementation with 
        # sentinel node to eliminate boundary checks
        head = self.head = Node("head")
        head.next = head.prev = head
        
    def clear(self):
        self.head.next = self.head.prev = self.head

    def insert(self, node):
        """Inserts a node at the end of the queue."""
        node.next = self.head
        node.prev = self.head.prev        
        node.next.prev = node
        node.prev.next = node
        
    def peek(self):
        """Returns the element at the begining of the queue."""
        if self.head.next is self.head:
            raise Exception, "Queue is empty"
        return self.head.next
        
    def remove(self, node=None):
        """Removes a node from the linked list. If node is None, head of the queue is removed."""
        if node is None:
            node = self.peek()
              
        node.prev.next = node.next
        node.next.prev = node.prev
        return node
        
    def __str__(self):
        return str(list(self._list()))
        
    __repr__ = __str__
        
    def _list(self):
        node = self.head.next
        while node != self.head:
            yield node
            node = node.next

def synchronized(f):
    """Decorator to synchronize a method.
    Behavior of this is same as Java synchronized keyword.
    """
    def g(self, *a, **kw):
        # allocate the lock when the function is called for the first time.
        lock = getattr(self, '__lock__', None)
        if lock is None:
            import threading
            lock = threading.RLock()
            setattr(self, '__lock__', lock)
            
        try:
            lock.acquire()
            return f(self, *a, **kw)
        finally:
            lock.release()
    return g

class LRU:
    """Dictionary which discards least recently used items when size 
    exceeds the specified capacity.
    
        >>> d = LRU(3)
        >>> d[1], d[2], d[3] = 1, 2, 3
        >>> d[1], d[2], d[3]
        (1, 2, 3)
        >>> d[2] and d
        [1, 3, 2]
        >>> d[1] and d
        [3, 2, 1]
        >>> d[4] = 4
        >>> d
        [2, 1, 4]
        >>> del d[1]
        >>> d
        [2, 4]
        >>> d[2] = 2
        >>> d
        [4, 2]
    """
    def __init__(self, capacity, d=None):
        self.capacity = capacity
        self.d = d or {}
        self.queue = Queue()

    @synchronized
    def getnode(self, key, touch=True):
        if key not in self.d:
            self.d[key] = Node(key)
        node = self.d[key]
        if touch:
            self.touch(node)
        return node

    @synchronized
    def touch(self, node):
        # don't call remove for newly created nodes 
        node.next and self.queue.remove(node)
        self.queue.insert(node)
    
    @synchronized
    def prune(self):
        """Remove least recently used items if required."""
        while len(self.d) > self.capacity:
            self.remove_node()
            
    @synchronized
    def __contains__(self, key):
        return key in self.d
        
    @synchronized
    def __getitem__(self, key):
        node = self.d[key]
        self.touch(node)
        return node.value
        
    @synchronized
    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    @synchronized
    def __setitem__(self, key, value):
        self.getnode(key).value = value
        self.prune()
    
    @synchronized
    def __delitem__(self, key):
        if key not in self.d:
            raise KeyError, key
        node = self.getnode(key, touch=False)
        self.remove_node(node)
        
    @synchronized
    def delete(self, key):
        try:
            del self[key]
        except KeyError:
            pass
            
    @synchronized
    def delete_many(self, keys):
        for k in keys:
            if k in self.d:
                del self[k]
        
    @synchronized
    def update(self, d):
        for k, v in d.items():
            self[k] = v
        
    @synchronized
    def keys(self):
        return self.d.keys()
        
    @synchronized
    def items(self):
        return [(k, node.value) for k, node in self.d.items()]
    
    @synchronized    
    def clear(self):
        self.d.clear()
        self.queue.clear()
        
    @synchronized
    def remove_node(self, node=None):
        node = self.queue.remove(node)
        del self.d[node.key]
        return node
                
    @synchronized
    def __str__(self):
        return str(self.queue)
    __repr__ = __str__
    
def lrumemoize(n):
    def decorator(f):
        cache = LRU(n)
        def g(*a, **kw):
            key = a, tuple(kw.items())
            if key not in cache:
                cache[key] = f(*a, **kw)
            return cache[key]
        return g
    return decorator

class ThingCache(LRU):
    """LRU Cache for storing things. Key can be either id or (site_id, key)."""
    def __init__(self, capacity):
        LRU.__init__(self, capacity)
        self.key2id = {}

    def __contains__(self, key):
        if isinstance(key, tuple):
            return key in self.key2id
        else:
            return LRU.__contains__(self, key)

    def __getitem__(self, key):
        if isinstance(key, tuple):
            key = self.key2id[key]
        return LRU.__getitem__(self, key)

    def get(self, key, default=None):
        if key in self:
            return self[key]
        else:
            return None

    def __setitem__(self, key, value):
        key = value.id
        LRU.__setitem__(self, key, value)
        # key2id mapping must be updated whenever a thing is added to the cache
        self.key2id[value._site.id, value.key] = value.id
        
    def __delitem__(self, key):
        if isinstance(key, tuple):
            key = self.key2id[key]
        return LRU.__delitem__(self, key)

    def remove_node(self, node=None):
        node = LRU.remove_node(self, node)
        thing = node.value
        # when a node is removed, its corresponding entry 
        # from the key2id map must also be removed 
        del self.key2id[thing._site.id, thing.key]
        return node
        
    def clear(self):
        LRU.clear(self)
        self.key2id.clear()

if __name__ == "__main__":
    import doctest
    doctest.testmod()
    
########NEW FILE########
__FILENAME__ = multiple_insert
"""Support for multiple inserts"""

import web

def join(items, sep):
    q = web.SQLQuery('')
    for i, item in enumerate(items):
        if i: q += sep
        q += item
    return q

_pg_version = None

def get_postgres_version():    
    global _pg_version
    if _pg_version is None:
        version = web.query('SELECT version();')[0].version
        # convert "PostgreSQL 8.2.4 on ..." in to (8, 2, 4)
        tokens = version.split()[1].split('.')
        _pg_version = tuple([int(t) for t in tokens])
    return _pg_version

def multiple_insert(tablename, values, seqname=None, _test=False):
    # multiple inserts are supported only in version 8.2+
    if get_postgres_version() < (8, 2):
        result = [web.insert(tablename, seqname=seqname, **v) for v in values]
        if seqname:
            return result
        else:
            return None
        
    if not values:
        return []

    keys = values[0].keys()

    #@@ make sure all keys are valid

    # make sure all rows have same keys.
    for v in values:
        if v.keys() != keys:
            raise Exception, 'Bad data'

    q = web.SQLQuery('INSERT INTO %s (%s) VALUES ' % (tablename, ', '.join(keys))) 

    data = []

    for row in values:
        d = join([web.SQLQuery(web.aparam(), [row[k]]) for k in keys], ', ')
        data.append('(' + d + ')')
         
    q += join(data, ',')
    
    if seqname is not False:
        if seqname is None:
            seqname = tablename + "_id_seq"
        q += "; SELECT currval('%s')" % seqname

    if _test:
        return q

    db_cursor = web.ctx.db_cursor()
    web.ctx.db_execute(db_cursor, q)

    try:
        out = db_cursor.fetchone()[0]
        out = range(out-len(values)+1, out+1)
    except Exception:
        out = None

    if not web.ctx.db_transaction: web.ctx.db.commit()
    return out

if __name__ == "__main__":
    web.config.db_parameters = dict(dbn='postgres', db='coverthing_test', user='anand', pw='')
    web.config.db_printing = True
    web.load()
    def data(id):
        return [
            dict(thing_id=id, key='isbn', value=1, datatype=1),
            dict(thing_id=id, key='source', value='amazon', datatype=1),
            dict(thing_id=id, key='image', value='foo', datatype=10)]

    ids =  multiple_insert('thing', [dict(dummy=1)] * 10)
    values = []
    for id in ids:
        values += data(id)
    multiple_insert('datum', values, seqname=False)

########NEW FILE########
__FILENAME__ = readquery
import common
from common import all, any
import web
import re
import _json as simplejson

def get_thing(store, key, revision=None):
    json = key and store.get(key, revision)
    return json and common.Thing.from_json(store, key, json)

def run_things_query(store, query):
    query = make_query(store, query)
    keys = store.things(query)
        
    xthings = {}
    def load_things(keys, query):
        _things = simplejson.loads(store.get_many(keys))
        xthings.update(_things)
        
        for k, v in query.requested.items():
            k = web.lstrips(k, query.prefix)
            if isinstance(v, Query):
                keys2 = common.flatten([d.get(k) for d in _things.values() if d.get(k)])
                keys2 = [k['key'] for k in keys2]
                load_things(set(keys2), v)
    
    def get_nested_data(value, query):
        if isinstance(value, list):
            return [get_nested_data(v, query) for v in value]
        elif isinstance(value, dict) and 'key' in value:
            thingdata = xthings[value['key']]
            return get_data(thingdata, query)
        else:
            return value
    
    def get_data(thingdata, query):
        fields = dict((web.lstrips(k, query.prefix), v) for k, v in query.requested.items())
        
        # special care for '*'
        if '*' in fields:
            f = dict((k, None) for k in thingdata.keys())
            fields.pop('*')
            f.update(fields)
            fields = f
        
        d = {}
        for k, v in fields.items():
            value = thingdata.get(k)
            if isinstance(v, Query):
                d[k] = get_nested_data(value, v)
            else:
                d[k] = value
        return d
    
    data = [{'key': key} for key in keys]
    if query.requested.keys() == ['key']:
        return data
    else:
        load_things(keys, query)
        
        # @@@ Sometimes thing.latest_revision is not same as max(data.revision) due to some data error.
        # @@@ Temporary work-around to handle that case.
        data = [d for d in data if d['key'] in xthings]
        return get_nested_data(data, query)

class Query:
    """Query is a list of conditions.
    Each condition is a storage object with ("key", "op", "datatype", "value") as keys.
    
        >>> q = Query()
        >>> q
        <query: []>
        >>> q.add_condition("name", "=", "str", "foo")
        >>> q
        <query: ['name = str:foo']>
        >>> q.add_condition('type', '=', 'ref', '/type/page')
        >>> q.get_type()
        '/type/page'
        >>> q
        <query: ['name = str:foo', 'type = ref:/type/page']>
    """
    def __init__(self, conditions=None):
        self.conditions = conditions or []
        self.sort = None
        self.limit = None
        self.offset = None
        self.prefix = None
        self.requested = {"key": None}
        
    def get_type(self):
        """Returns the value of the condition for type if there is any.
        """
        for c in self.conditions:
            #@@ also make sure op is =
            if c.key == 'type':
                return c.value
                
    def assert_type_required(self):
        type_required = any(c.key not in common.COMMON_PROPERTIES for c in self.conditions if not isinstance(c, Query))
        if type_required and self.get_type() is None:
            raise common.BadData(message="missing 'type' in query")

    def add_condition(self, key, op, datatype, value):
        self.conditions.append(web.storage(key=key, op=op, datatype=datatype, value=value))
        
    def __repr__(self):
        def f(c):
            if isinstance(c, Query):
                return repr(c)
            else:
                return "%s %s %s:%s" % (c.key, c.op, c.datatype, c.value)
        conditions = [f(c) for c in self.conditions]
        return "<query: %s>" % repr(conditions)

def make_query(store, query, prefix=""):
    """Creates a query object from query dict.
        >>> store = common.create_test_store()
        >>> make_query(store, {'type': '/type/page'})
        <query: ['type = ref:/type/page']>
        >>> make_query(store, {'type': '/type/page', 'title~': 'foo', 'life': 42})
        <query: ['life = int:42', 'type = ref:/type/page', 'title ~ str:foo']>
        >>> make_query(store, {'type': '/type/page', 'title~': 'foo', 'a:life<': 42, "b:life>": 420})        
        <query: ['life < int:42', 'type = ref:/type/page', 'title ~ str:foo', 'life > int:420']>
    """
    query = common.parse_query(query)
    q = Query()
    q.prefix = prefix
    q.offset = common.safeint(query.pop('offset', None), 0)
    q.limit = common.safeint(query.pop('limit', 20), 20)
    if q.limit > 1000:
        q.limit = 1000
    sort = query.pop('sort', None)
    
    nested = (prefix != "")
    
    for k, v in query.items():
        # key foo can also be written as label:foo
        k = k.split(':')[-1]
        if v is None:
            q.requested[k] = v
        elif isinstance(v, dict):
            # make sure op is ==
            v = dict((k + '.' + key, value) for key, value in v.items())
            q2 = make_query(store, v, prefix=prefix + k + ".")
            #@@ Anand: Quick-fix
            # dbstore.things looks for key to find whether type is required or not. 
            q2.key = k 
            if q2.conditions:
                q.conditions.append(q2)
            else:
                q.requested[k] = q2
        else:
            k, op = parse_key(k)
            q.add_condition(k, op, None, v)
             
    if not nested:
        q.assert_type_required()
        
    type = get_thing(store, q.get_type())
    #assert type is not None, 'Not found: ' + q.get_type()
    for c in q.conditions:
        if not isinstance(c, Query):
            c.datatype = find_datatype(type, c.key, c.value)
            
    if sort:
        parse_key(sort) # to validate key
        q.sort = web.storage(key=sort, datatype=find_datatype(type, sort, None))
    else:
        q.sort = None
            
    return q
    
def find_datatype(type, key, value):
    """
        >>> find_datatype(None, "foo", 1)
        'int'
        >>> find_datatype(None, "foo", True)
        'boolean'
        >>> find_datatype(None, "foo", "hello")
        'str'
    """
    # special properties
    d = dict(
        key="key", 
        type="ref", 
        permission="ref",
        child_permission="ref",
        created="datetime", 
        last_modified="datetime")
    
    if key in d:
        return d[key]
    
    if isinstance(value, bool):
        return "boolean"
    elif isinstance(value, int):
        return "int"
    elif isinstance(value, float):
        return "float"
    elif isinstance(value, common.Reference):
        return 'ref'

    type2datatype = {
        '/type/string': 'str',
        '/type/int': 'int',
        '/type/float': 'float',
        '/type/boolean': 'boolean',
        '/type/datetime': 'datetime'
    }
    
    # if possible, get the datatype from the type schema
    p = type and type.get_property(key)
    return (p and type2datatype.get(p.expected_type.key, 'ref')) or "str"
    
def parse_key(key):
    """Parses key and returns key and operator.
        >>> parse_key('foo')
        ('foo', '=')
        >>> parse_key('foo=')
        ('foo', '=')
        >>> parse_key('foo<')
        ('foo', '<')
        >>> parse_key('foo~')
        ('foo', '~')
        >>> parse_key('foo!=')
        ('foo', '!=')
    """
    operators = ["!=", "=", "<", "<=", ">=", ">", "~"]
    operator = "="
    for op in operators:
        if key.endswith(op):
            key = key[:-len(op)]
            operator = op
            break

    return key, operator
    
def make_versions_query(store, query):
    """Creates a versions query object from query dict.
    """
    q = Query()
    
    q.offset = common.safeint(query.pop('offset', None), 0)
    q.limit = common.safeint(query.pop('limit', 20), 20)
    if q.limit > 1000:
        q.limit = 1000
    q.sort = query.pop('sort', '-created')
    
    columns = ['key', 'type', 'revision', 'author', 'comment', 'machine_comment', 'ip', 'created', 'bot']
    
    for k, v in query.items():
        if k not in columns:
            raise ValueError, k
        q.add_condition(k, '=', None, v)
        
    return q

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = server
"""Infobase server to expose the API.
"""
__version__ = "0.5dev"

import sys
import web
import infobase
import _json as simplejson
import time
import time
import os
import logging

from infobase import config
import common
import cache
import logreader

from account import get_user_root

logger = logging.getLogger("infobase")

def setup_remoteip():
    web.ctx.ip = web.ctx.env.get('HTTP_X_REMOTE_IP', web.ctx.ip)

urls = (
    "/", "server",
    "/_echo", "echo",
    "/([^_/][^/]*)", "db",
    "/([^/]*)/get", "withkey",
    "/([^/]*)/get_many", "get_many",
    '/([^/]*)/save(/.*)', 'save',
    '/([^/]*)/save_many', 'save_many',
    "/([^/]*)/reindex", "reindex",    
    "/([^/]*)/new_key", "new_key",
    "/([^/]*)/things", "things",
    "/([^/]*)/versions", "versions",
    "/([^/]*)/write", "write",
    "/([^/]*)/account/(.*)", "account",
    "/([^/]*)/permission", "permission",
    "/([^/]*)/log/(\d\d\d\d-\d\d-\d\d:\d+)", "readlog",
    "/([^/]*)/_store/(_.*)", "store_special",
    "/([^/]*)/_store/(.*)", "store",
    "/([^/]*)/_seq/(.*)", "seq",
    "/([^/]*)/_recentchanges", "recentchanges",
    "/([^/]*)/_recentchanges/(\d+)", "change",
    "/_invalidate", "invalidate"
)

app = web.application(urls, globals(), autoreload=False)

app.add_processor(web.loadhook(setup_remoteip))
app.add_processor(web.loadhook(cache.loadhook))
app.add_processor(web.unloadhook(cache.unloadhook))

def process_exception(e):
    if isinstance(e, common.InfobaseException):
        status = e.status
    else:
        status = "500 Internal Server Error"

    msg = str(e)
    raise web.HTTPError(status, {}, msg)
    
class JSON:
    """JSON marker. instances of this class not escaped by jsonify.
    """
    def __init__(self, json):
        self.json = json

def jsonify(f):
    def g(self, *a, **kw):
        t_start = time.time()
        web.ctx.setdefault("headers", [])
                
        if not web.ctx.get('infobase_localmode'):
            cookies = web.cookies(infobase_auth_token=None)
            web.ctx.infobase_auth_token = cookies.infobase_auth_token
                        
        try:
            d = f(self, *a, **kw)
        except common.InfobaseException, e:
            if web.ctx.get('infobase_localmode'):
                raise
            
            process_exception(e)
        except Exception, e:
            logger.error("Error in processing request %s %s", web.ctx.get("method", "-"), web.ctx.get("path","-"), exc_info=True)

            common.record_exception()
            # call web.internalerror to send email when web.internalerror is set to web.emailerrors
            process_exception(common.InfobaseException(error="internal_error", message=str(e)))
            
            if web.ctx.get('infobase_localmode'):
                raise common.InfobaseException(message=str(e))
            else:
                process_exception(e)
        
        if isinstance(d, JSON):
            result = d.json
        else:
            result = simplejson.dumps(d)
            
        t_end = time.time()
        totaltime = t_end - t_start
        querytime = web.ctx.pop('querytime', 0.0)
        queries = web.ctx.pop('queries', 0)
        
        if config.get("enabled_stats"):
            web.header("X-STATS", "tt: %0.3f, tq: %0.3f, nq: %d" % (totaltime, querytime, queries))

        if web.ctx.get('infobase_localmode'):
            return result
        else:
            # set auth-token as cookie for remote connection.
            if web.ctx.get('infobase_auth_token'):
                web.setcookie('infobase_auth_token', web.ctx.infobase_auth_token)
            return result
        
    return g
    
def get_data():
    if 'infobase_input' in web.ctx:
        return web.ctx.infobase_input
    else:
        return web.data()
    
def input(*required, **defaults):
    if 'infobase_input' in web.ctx:
        d = web.ctx.infobase_input
    else:
        d = web.input()
        
    for k in required:
        if k not in d:
            raise common.BadData(message="Missing argument: " + repr(k))
            
    result = web.storage(defaults)
    result.update(d)
    return result
    
def to_int(value, key):
    try:
        return int(value)
    except:
        raise common.BadData(message="Bad integer value for %s: %s" % (repr(key), repr(value)))
        
def from_json(s):
    try:
        return simplejson.loads(s)
    except ValueError, e:
        raise common.BadData(message="Bad JSON: " + str(e))
        
_infobase = None
def get_site(sitename):
    import config
    global _infobase
    if not _infobase:
        import dbstore
        schema = dbstore.default_schema or dbstore.Schema()
        store = dbstore.DBStore(schema)
        _infobase = infobase.Infobase(store, config.secret_key)
    return _infobase.get(sitename)
    
class server:
    @jsonify
    def GET(self):
        return {"infobase": "welcome", "version": __version__}
        
class db:
    @jsonify
    def GET(self, name):
        site = get_site(name)
        if site is None:
            raise common.NotFound(error="db_notfound", name=name)
        else:
            return {"name": site.sitename}
        
    @jsonify
    def PUT(self, name):
        site = get_site(name)
        if site is not None:
            raise web.HTTPError("412 Precondition Failed", {}, "")
        else:
            site = _infobase.create(name)
            return {"ok": "true"}
            
    @jsonify
    def DELETE(self, name):
        site = get_site(name)
        if site is None:
            raise common.NotFound(error="db_notfound", name=name)
        else:
            site.delete()
            return {"ok": True}

class echo:
    @jsonify
    def POST(self):
        print >> web.debug, web.data()
        return {'ok': True}

class write:
    @jsonify
    def POST(self, sitename):
        site = get_site(sitename)
        i = input('query', comment=None, action=None)
        query = from_json(i.query)
        result = site.write(query, comment=i.comment, action=i.action)
        return result

class withkey:
    @jsonify
    def GET(self, sitename):
        i = input("key", revision=None, expand=False)
        site = get_site(sitename)
        revision = i.revision and to_int(i.revision, "revision")
        json = site.get(i.key, revision=revision)
        if not json:
            raise common.NotFound(key=i.key)
        return JSON(json)

class get_many:
    @jsonify
    def GET(self, sitename):
        i = input("keys")
        keys = from_json(i['keys'])
        site = get_site(sitename)
        return JSON(site.get_many(keys))

class save:
    @jsonify
    def POST(self, sitename, key):
        #@@ This takes payload of json instead of form encoded data.
        json = get_data()
        data = from_json(json)

        comment = data.pop('_comment', None)
        action = data.pop('_action', None)
        _data = data.pop('_data', None)
        
        site = get_site(sitename)
        return site.save(key, data, comment=comment, action=action, data=_data)

class save_many:
    @jsonify
    def POST(self, sitename):
        i = input('query', comment=None, data=None, action=None)
        docs = from_json(i.query)
        data = i.data and from_json(i.data)
        site = get_site(sitename)
        return site.save_many(docs, comment=i.comment, data=data, action=i.action)

class reindex:
    @jsonify
    def POST(self, sitename):
        i = input("keys")
        keys = simplejson.loads(i['keys'])
        site = get_site(sitename)
        site.store.reindex(keys)
        return {"status": "ok"}
        
class new_key:
    @jsonify
    def GET(self, sitename):
        i = input('type')
        site = get_site(sitename)
        return site.new_key(i.type)

class things:
    @jsonify
    def GET(self, sitename):
        site = get_site(sitename)
        i = input('query', details="false")
        q = from_json(i.query)
        result = site.things(q)
        
        if i.details.lower() == "false":
            return [r['key'] for r in result]
        else:
            return result

class versions:
    @jsonify
    def GET(self, sitename):
        site = get_site(sitename)
        i = input('query')
        q = from_json(i.query)
        return site.versions(q)
        
class recentchanges:
    @jsonify
    def GET(self, sitename):
        site = get_site(sitename)
        i = input('query')
        q = from_json(i.query)
        return site.recentchanges(q)
        
class change:
    @jsonify
    def GET(self, sitename, id):
        site = get_site(sitename)
        return site.get_change(int(id))
        
class permission:
    @jsonify
    def GET(self, sitename):
        site = get_site(sitename)
        i = input('key')
        return site.get_permissions(i.key)
        
class store_special:
    def GET(self, sitename, path):
        if path == '_query':
            return self.GET_query(sitename)
        else:
            raise web.notfound("")
            
    def POST(self, sitename, path):
        if path == '_save_many':
            return self.POST_save_many(sitename)
        else:
            raise web.notfound("")
            
    @jsonify
    def POST_save_many(self, sitename):
        store = get_site(sitename).get_store()
        json = get_data()
        docs = simplejson.loads(json)
        store.put_many(docs)
        
    @jsonify
    def GET_query(self, sitename):
        i = input(type=None, name=None, value=None, limit=100, offset=0, include_docs="false")
        
        i.limit = common.safeint(i.limit, 100)
        i.offset = common.safeint(i.offset, 0)
        
        store = get_site(sitename).get_store()
        return store.query(
            type=i.type, 
            name=i.name, 
            value=i.value, 
            limit=i.limit, 
            offset=i.offset, 
            include_docs=i.include_docs.lower()=="true")

class store:
    @jsonify
    def GET(self, sitename, path):
        store = get_site(sitename).get_store()
        json = store.get_json(path)
        if not json:
            raise common.NotFound(error="notfound", key=path)
        return JSON(store.get_json(path))

    @jsonify
    def PUT(self, sitename, path):
        store = get_site(sitename).get_store()
        json = get_data()
        doc = simplejson.loads(json)
        store.put(path, doc)
        return JSON('{"ok": true}')
        
    @jsonify
    def DELETE(self, sitename, path):
        store = get_site(sitename).get_store()
        store.delete(path)
        return JSON('{"ok": true}')
        
class seq:
    @jsonify
    def GET(self, sitename, name):
        seq = get_site(sitename).get_seq()
        return {"name": name, "value": seq.get_value(name)}

    @jsonify
    def POST(self, sitename, name):
        seq = get_site(sitename).get_seq()
        return {"name": name, "value": seq.next_value(name)}
        
class account:
    """Code for handling /account/.*"""
    def get_method(self):
        if web.ctx.get('infobase_localmode'):
            return web.ctx.infobase_method
        else:
            return web.ctx.method
    
    @jsonify
    def delegate(self, sitename, method):
        site = get_site(sitename)
        methodname = "%s_%s" % (self.get_method(), method)
        
        m = getattr(self, methodname, None)
        if m:
            return m(site)
        else:
            raise web.notfound()
        
    GET = POST = delegate

    def POST_login(self, site):
        i = input('username', 'password')
        a = site.get_account_manager()
        status = a.login(i.username, i.password)
        
        if status == "ok":
            a.set_auth_token(get_user_root() + i.username)
            return {"ok": True}
        else:
            raise common.BadData(code=status, message="Login failed")
        
    def POST_register(self, site):
        i = input('username', 'password', 'email')
        a = site.get_account_manager()
        username = i.pop('username')
        password = i.pop('password')
        email = i.pop('email')
        
        activation_code = a.register(username=username, email=email, password=password, data=i)
        return {"activation_code": activation_code, "email": email}

    def POST_activate(self, site):
        i = input('username')

        a = site.get_account_manager()
        status = a.activate(i.username)
        if status == "ok":
            return {"ok": "true"}
        else:
            raise common.BadData(error_code=status, message="Account activation failed.")
            
    def POST_update(self, site):
        i = input('username')
        username = i.pop("username")
        
        a = site.get_account_manager()
        status = a.update(username, **i)
        
        if status == "ok":
            return {"ok": "true"}
        else:
            raise common.BadData(error_code=status, message="Account activation failed.")
        
    def GET_find(self, site):
        i = input(email=None, username=None)
        a = site.get_account_manager()
        return a.find_account(email=i.email, username=i.username)

    def GET_get_user(self, site):
        a = site.get_account_manager()
        user = a.get_user()
        if user:
            d = user.format_data()
            username = d['key'].split("/")[-1]
            d['email'] = a.find_account(username=username)['email']
            return d

    def GET_get_reset_code(self, site):
        # TODO: remove this
        i = input('email')
        a = site.get_account_manager()
        username, code = a.get_user_code(i.email)
        return dict(username=username, code=code)
        
    def GET_check_reset_code(self, site):
        # TODO: remove this
        i = input('username', 'code')
        a = site.get_account_manager()
        a.check_reset_code(i.username, i.code)
        return {'ok': True}
        
    def GET_get_user_email(self, site):
        i = input('username')
        a = site.get_account_manager()
        return a.find_account(username=i.username)
        
    def GET_find_user_by_email(self, site):
        i = input("email")
        a = site.get_account_manager()
        account = a.find_account(email=i.email)
        return account and account['key'].split("/")[-1]

    def POST_reset_password(self, site):
        # TODO: remove this
        i = input('username', 'code', 'password')
        a = site.get_account_manager()
        return a.reset_password(i.username, i.code, i.password)
    
    def POST_update_user(self, site):
        i = input('old_password', new_password=None, email=None)
        a = site.get_account_manager()
        
        user = a.get_user()
        username = user.key.split("/")[-1]
        
        status = a.login(username, i.old_password)
        if status == "ok":
            kw = {}
            if i.new_password:
                kw['password'] = i.new_password
            if i.email:
                kw['email'] = i.email 
            a.update(username, **kw)
        else:
            raise common.BadData(code=status, message="Invalid password")
        
    def POST_update_user_details(self, site):
        i = input('username')
        username = i.pop('username')
        
        a = site.get_account_manager()
        return a.update(username, **i)

class readlog:
    def get_log(self, offset, i):
        log = logreader.LogFile(config.writelog)
        log.seek(offset)
        
        # when the offset is not known, skip_till parameter can be used to query.
        if i.timestamp:
            try:
                timestamp = common.parse_datetime(i.timestamp)
                logreader.LogReader(log).skip_till(timestamp)
            except Exception, e:
                raise web.internalerror(str(e))
        
        return log
        
    def assert_valid_json(self, line):
        try:
            simplejson.loads(line)
        except ValueError:
            raise web.BadRequest()
            
    def valid_json(self, line):
        try:
            simplejson.loads(line)
            return True
        except ValueError:
            return False
        
    def GET(self, sitename, offset):
        i = web.input(timestamp=None, limit=1000)
        
        if not config.writelog:
            raise web.notfound("")
        else:
            log = self.get_log(offset, i)
            limit = min(1000, common.safeint(i.limit, 1000))
            
            try:                
                web.header('Content-Type', 'application/json')
                yield '{"data": [\n'
                
                sep = ""
                for i in range(limit):
                    line = log.readline().strip()
                    if line:
                        if self.valid_json(line):
                            yield sep + line.strip()
                            sep = ",\n"
                        else:
                            print >> sys.stderr, "ERROR: found invalid json before %s" % log.tell()
                    else:
                        break
                yield '], \n'
                yield '"offset": ' + simplejson.dumps(log.tell()) + "\n}\n"
            except Exception, e:
                print 'ERROR:', str(e)
                
def request(path, method, data):
    """Fakes the web request.
    Useful when infobase is not run as a separate process.
    """
    web.ctx.infobase_localmode = True
    web.ctx.infobase_input = data or {}
    web.ctx.infobase_method = method
    
    def get_class(classname):
        if '.' in classname:
            modname, classname = classname.rsplit('.', 1)
            mod = __import__(modname, None, None, ['x'])
            fvars = mod.__dict__
        else:
            fvars = globals()
        return fvars[classname]

    try:
        # hack to make cache work for local infobase connections
        cache.loadhook()

        mapping = app.mapping

        # Before web.py<0.36, the mapping is a list and need to be grouped. 
        # From web.py 0.36 onwards, the mapping is already grouped.
        # Checking the type to see if we need to group them here.
        if mapping and not isinstance(mapping[0], (list, tuple)):
            mapping = web.group(mapping, 2)

        for pattern, classname in mapping:
            m = web.re_compile('^' + pattern + '$').match(path)
            if m:
                args = m.groups()
                cls = get_class(classname)
                tocall = getattr(cls(), method)
                return tocall(*args)
        raise web.notfound()
    finally:
        # hack to make cache work for local infobase connections
        cache.unloadhook()
            
def run():
    app.run()
    
def parse_db_parameters(d):
    if d is None:
        return None
        
    # support both <engine, database, username, password> and <dbn, db, user, pw>.
    if 'database' in d:
        dbn, db, user, pw = d.get('engine', 'postgres'), d['database'], d.get('username'), d.get('password') or ''
    else:
        dbn, db, user, pw = d.get('dbn', 'postgres'), d['db'], d.get('user'), d.get('pw') or ''
        
    if user is None:
        user = os.getenv("USER")
     
    result = dict(dbn=dbn, db=db, user=user, pw=pw)
    if 'host' in d:
        result['host'] = d['host']
    return result
    
def start(config_file, *args):
    load_config(config_file)
    # start running the server
    sys.argv = [sys.argv[0]] + list(args)
    run()

def load_config(config_file):
    # load config
    import yaml
    runtime_config = yaml.load(open(config_file)) or {}

    # update config
    for k, v in runtime_config.items():
        setattr(config, k, v)
        
    # import plugins
    plugins = []
    for p in config.get('plugins') or []:
        plugins.append(__import__(p, None, None, ["x"]))
        logger.info("loading plugin %s", p)
        
    web.config.db_parameters = parse_db_parameters(config.db_parameters)    

    # initialize cache
    cache_params = config.get('cache', {'type': 'none'})
    cache.global_cache = cache.create_cache(**cache_params)
    
    # init plugins
    for p in plugins:
        m = getattr(p, 'init_plugin', None)
        m and m()
########NEW FILE########
__FILENAME__ = conftest

from pytest_wildcard import *

########NEW FILE########
__FILENAME__ = pytest_wildcard
"""py.test wildcard plugin.
"""

class Wildcard:
    """Wildcard object is equal to anything.
    
    Useful to compare datastructures which contain some random numbers or db sequences.
    
        >>> import random
        >>> asseert [random.random(), 1, 2] == [wildcard, 1, 2]
    """
    def __eq__(self, other):
        return True
    
    def __ne__(self, other):
        return False
        
    def __repr__(self):
        return '<?>'

wildcard = Wildcard()

def test_wildcard():
    assert wildcard == 1
    assert wildcard == [1, 2, 3]
    assert 1 == wildcard
    assert ["foo", 1, 2] == [wildcard, 1, 2]

def pytest_funcarg__wildcard(request):
    """Returns the wildcard object.
    
    Wildcard object is equal to anything. It is useful in testing datastuctures with some random parts. 
    
        >>> import random
        >>> asseert [random.random(), 1, 2] == [wildcard, 1, 2]
    """
    return wildcard
########NEW FILE########
__FILENAME__ = test_account
import utils
import web

from infogami.infobase import server, account, bootstrap, common

import pytest

def setup_module(mod):
    utils.setup_site(mod)

def teardown_module(mod):
    site.cache.clear()
    utils.teardown_site(mod)

class TestAccount:
    def setup_method(self, method):
        self.tx = db.transaction()
    
    def teardown_method(self, method):
        self.tx.rollback()
        site.cache.clear()

    def test_register(self):
        a = site.account_manager
        a.register(username="joe", email="joe@example.com", password="secret", data={})
        
        # login should fail before activation 
        assert a.login('joe', 'secret') == "account_not_verified"
        assert a.login('joe', 'wrong-password') == "account_bad_password"

        a.activate(username="joe")

        assert a.login('joe', 'secret') == "ok"
        assert a.login('joe', 'wrong-password') == "account_bad_password"
        
    def test_register_failures(self, _activate=True):
        a = site.account_manager
        a.register(username="joe", email="joe@example.com", password="secret", data={}, _activate=_activate)
        
        try:
            a.register(username="joe", email="joe2@example.com", password="secret", data={})
            assert False
        except common.BadData, e:
            assert e.d['message'] == "User already exists: joe"
            
        try:
            a.register(username="joe2", email="joe@example.com", password="secret", data={})
            assert False
        except common.BadData, e:
            assert e.d['message'] == "Email is already used: joe@example.com"
            
    def test_register_failures2(self):
        # test registeration without activation + registration with same username/email
        self.test_register_failures(_activate=False)
        
    def encrypt(self, password):
        """Generates encrypted password from raw password."""
        a = site.account_manager
        return a._generate_salted_hash(a.secret_key, password)
        
    def test_login_account(self):
        f = site.account_manager._verify_login
        enc_password = self.encrypt("secret")
        
        assert f(dict(enc_password=enc_password, status="active"), "secret") == "ok"
        assert f(dict(enc_password=enc_password, status="active"), "bad-password") == "account_bad_password"

        # pending accounts should return "account_not_verified" if the password is correct
        assert f(dict(enc_password=enc_password, status="pending"), "secret") == "account_not_verified"
        assert f(dict(enc_password=enc_password, status="pending"), "bad-password") == "account_bad_password"

    def test_update(self):
        a = site.account_manager
        a.register(username="foo", email="foo@example.com", password="secret", data={})
        a.activate("foo")
        assert a.login("foo", "secret") == "ok"

        # test update password
        assert a.update("foo", password="more-secret") == "ok"
        assert a.login("foo", "secret") == "account_bad_password"
        assert a.login("foo", "more-secret") == "ok"

        ## test update email
        
        # registering with the same email should fail.
        assert pytest.raises(common.BadData, a.register, username="bar", email="foo@example.com", password="secret", data={})
        
        assert a.update("foo", email="foo2@example.com") == "ok"
        
        # someone else should be able to register with the old email
        a.register(username="bar", email="foo@example.com", password="secret", data={})
        
        # and no one should be allowed to register with new email
        assert pytest.raises(common.BadData, a.register, username="bar", email="foo2@example.com", password="secret", data={})
        
        

########NEW FILE########
__FILENAME__ = test_client
import simplejson

from infogami.infobase import client, server

import utils

def setup_module(mod):
    utils.setup_conn(mod)
    utils.setup_server(mod)
    
    mod.site = client.Site(mod.conn, "test")
    mod.s = mod.site.store
    mod.seq = mod.site.seq
    
def teardown_module(mod):
    utils.teardown_server(mod)
    utils.teardown_conn(mod)
    
class TestRecentChanges:
    def save_doc(self, key, **kw):
        doc = {"key": key, "type": {"key": "/type/object"}}
        return site.save(doc, **kw)
        
    def recentchanges(self, **query):
        return [c.dict() for c in site.recentchanges(query)]
        
    def test_all(self, wildcard):
        self.save_doc("/foo", comment="test recentchanges")
                
        changes = self.recentchanges(limit=1)
        assert changes == [{
            "id": wildcard,
            "kind": "update",
            "author": None,
            "ip": wildcard,
            "timestamp": wildcard,
            "changes": [{"key": "/foo", "revision": 1}],
            "comment": "test recentchanges",
            "data": {}
        }]
                        
        assert site.get_change(changes[0]["id"]).dict() == {
            "id": wildcard,
            "kind": "update",
            "author": None,
            "ip": wildcard,
            "timestamp": wildcard,
            "comment": "test recentchanges",
            "changes": [{"key": "/foo", "revision": 1}],
            "data": {}
        }
    
    def test_key(self, wildcard):
        self.save_doc("/foo")
        self.save_doc("/bar")
    
        changes = self.recentchanges(key="/foo")
        assert len(changes) == 1
        
    def test_query_by_data(self):
        self.save_doc("/one", data={"x": "one"}, comment="one")
        self.save_doc("/two", data={"x": "two"}, comment="two")

        changes = self.recentchanges(data={"x": "one"})
        assert [c['data'] for c in changes] == [{"x": "one"}]

        changes = self.recentchanges(data={"x": "two"})
        assert [c['data'] for c in changes] == [{"x": "two"}]
    
class TestStore:
    def setup_method(self, method):
        s.clear()
        
    def test_getitem(self, wildcard):
        try:
            s["x"]
        except KeyError:
            pass
        else:
            assert False, "should raise KeyError"
        
        s["x"] = {"name": "x"}
        assert s["x"] == {"name": "x", "_key": "x", "_rev": wildcard}
        
        s["x"] = {"name": "xx", "_rev": None}
        assert s["x"] == {"name": "xx", "_key": "x", "_rev": wildcard}
        
    def test_contains(self):
        assert "x" not in s
        
        s["x"] = {"name": "x"}
        assert "x" in s

        del s["x"]
        assert "x" not in s
        
    def test_keys(self):
        assert s.keys() == []
        
        s["x"] = {"name": "x"}
        assert s.keys() == ["x"]

        s["y"] = {"name": "y"}
        assert s.keys() == ["y", "x"]
        
        del s["x"]
        assert s.keys() == ["y"]
        
    def test_keys_unlimited(self):
        for i in range(200):
            s[str(i)] = {"value": i}
            
        def srange(*args):
            return [str(i) for i in range(*args)]
            
        assert s.keys() == srange(100, 200)[::-1]
        assert list(s.keys(limit=-1)) == srange(200)[::-1]
        
    def test_key_value_items(self, wildcard):
        s["x"] = {"type": "foo", "name": "x"}
        s["y"] = {"type": "bar", "name": "y"}
        s["z"] = {"type": "bar", "name": "z"}
        
        assert s.keys() == ["z", "y", "x"]
        assert s.keys(type='bar') == ["z", "y"]
        assert s.keys(type='bar', name="name", value="y") == ["y"]

        assert s.values() == [
            {"type": "bar", "name": "z", "_key": "z", "_rev": wildcard},
            {"type": "bar", "name": "y", "_key": "y", "_rev": wildcard},
            {"type": "foo", "name": "x", "_key": "x", "_rev": wildcard}
        ]
        assert s.values(type='bar') == [
            {"type": "bar", "name": "z", "_key": "z", "_rev": wildcard},
            {"type": "bar", "name": "y", "_key": "y", "_rev": wildcard}
        ]
        assert s.values(type='bar', name="name", value="y") == [
            {"type": "bar", "name": "y", "_key": "y", "_rev": wildcard}
        ]

        assert s.items() == [
            ("z", {"type": "bar", "name": "z", "_key": "z", "_rev": wildcard}),
            ("y", {"type": "bar", "name": "y", "_key": "y", "_rev": wildcard}),
            ("x", {"type": "foo", "name": "x", "_key": "x", "_rev": wildcard})
        ]
        assert s.items(type='bar') == [
            ("z", {"type": "bar", "name": "z", "_key": "z", "_rev": wildcard}),
            ("y", {"type": "bar", "name": "y", "_key": "y", "_rev": wildcard}),
        ]
        assert s.items(type='bar', name="name", value="y") == [
            ("y", {"type": "bar", "name": "y", "_key": "y", "_rev": wildcard}),
        ]
        
    def test_update(self):
        docs = {
            "x": {"type": "foo", "name": "x"},
            "y": {"type": "bar", "name": "y"},
            "z": {"type": "bar", "name": "z"},
        }
        s.update(docs)
        assert sorted(s.keys()) == (["x", "y", "z"])
        
class TestSeq:
    def test_seq(self):
        seq.get_value("foo") == 0
        seq.get_value("bar") == 0
        
        for i in range(10):
            seq.next_value("foo") == i+1
            
class TestSanity:
    """Simple tests to make sure that queries are working fine via all these layers."""
    def test_reindex(self):
        keys = ['/type/page']
        site._request("/reindex", method="POST", data={"keys": simplejson.dumps(keys)})

class TestAccount:
    """Test account creation, forgot password etc."""
    def test_register(self):
        email = "joe@example.com"
        response = site.register(username="joe", displayname="Joe", email=email, password="secret")

        assert site.activate_account(username="joe") == {'ok': 'true'}

        # login should succed
        site.login("joe", "secret")

        try:
            site.login("joe", "secret2")
        except client.ClientException:
            pass
        else:
            assert False, "Login should fail when used with wrong password"
########NEW FILE########
__FILENAME__ = test_doctests
import doctest
import py.test

def test_doctest():
    modules = [
        "infogami.infobase.account",
        "infogami.infobase.bootstrap",
        "infogami.infobase.cache",
        "infogami.infobase.client",
        "infogami.infobase.common",
        "infogami.infobase.core",
        "infogami.infobase.dbstore",
        "infogami.infobase.infobase",
        "infogami.infobase.logger",
        "infogami.infobase.logreader",
        "infogami.infobase.lru",
        "infogami.infobase.readquery",
        "infogami.infobase.utils",
        "infogami.infobase.writequery",
    ]
    for test in find_doctests(modules):
        yield run_doctest, test

def find_doctests(modules):
    finder = doctest.DocTestFinder()
    for m in modules:
        mod = __import__(m, None, None, ['x'])
        for t in finder.find(mod, mod.__name__):
            yield t
        
def run_doctest(test):
    runner = doctest.DocTestRunner(verbose=True)
    failures, tries = runner.run(test)
    if failures:
        py.test.fail("doctest failed: " + test.name)

########NEW FILE########
__FILENAME__ = test_infobase
import os
import simplejson
import urllib

import py.test

import web
from infogami.infobase import config, dbstore, infobase, server

import utils

def setup_module(mod):
    utils.setup_site(mod)
    mod.app = server.app
    
    # overwrite _cleanup to make it possible to have transactions spanning multiple requests.
    mod.app.do_cleanup = mod.app._cleanup
    mod.app._cleanup = lambda: None
    
def reset():
    site.cache.clear()
    
def teardown_module(mod):
    utils.teardown_site(mod)
        
def subdict(d, keys):
    """Returns a subset of a dictionary.
        >>> subdict({'a': 1, 'b': 2}, ['a'])
        {'a': 1}
    """
    return dict((k, d[k]) for k in keys)
    
import unittest
class DBTest(unittest.TestCase):
    def setUp(self):
        self.t = db.transaction()
        # important to clear the caches
        site.store.cache.clear()
        site.store.property_manager.reset()
        
        web.ctx.pop("infobase_auth_token", None)

    def tearDown(self):
        self.t.rollback()        
        
    def create_user(self, username, email, password, bot=False, data={}):
        site.account_manager.register(username, email, password, data, _activate=True)
        site.account_manager.update(username, bot=bot)
        
    def login(self, username, password):
        user = site.account_manager.login(username, password)
        # don't pollute global state
        web.ctx.infobase_auth_token = None
        return bool(user)
        
class TestInfobase(DBTest):
    def test_save(self):
        import sys

        # save an object and make sure revision==1
        d = site.save('/foo', {'key': '/foo', 'type': '/type/object', 'n': 1, 'p': 'q'})
        assert d['revision'] == 1

        # save again without any change in data and make sure new revision is not added.
        reset()
        d = site.save('/foo', {'key': '/foo', 'type': '/type/object', 'n': 1, 'p': 'q'})
        assert d == {}

        # now save with some change and make sure new revision is created
        reset()
        d = site.save('/foo', {'key': '/foo', 'type': '/type/object', 'n': 1, 'p': 'qq'})
        assert d['revision'] == 2
                
    def test_versions(self):
        site.save('/foo', {'key': '/foo', 'type': '/type/object'}, comment='test 1')
        site.save('/bar', {'key': '/bar', 'type': '/type/object'}, comment='test 2')
        site.save('/foo', {'key': '/foo', 'type': '/type/object', 'x': 1}, comment='test 3')
                
        def versions(q):
            return [subdict(v, ['key', 'revision', 'comment']) for v in site.versions(q)]
            
        assert versions({'limit': 3}) == [
            {'key': '/foo', 'revision': 2, 'comment': 'test 3'},
            {'key': '/bar', 'revision': 1, 'comment': 'test 2'},
            {'key': '/foo', 'revision': 1, 'comment': 'test 1'},
        ]
        
        print self.create_user('test', 'testt@example.com', 'test123', data={'displayname': 'Test'})
        print site._get_thing('/user/test')
        site.save('/foo', {'key': '/foo', 'type': '/type/object', 'x': 2}, comment='test 4', ip='1.2.3.4', author=site._get_thing('/user/test'))
        
        assert versions({'author': '/user/test'})[:-3] == [
            {'key': '/foo', 'revision': 3, 'comment': 'test 4'}
        ]

        assert versions({'ip': '1.2.3.4'}) == [
            {'key': '/foo', 'revision': 3, 'comment': 'test 4'}
        ]
        
        # should return empty result for bad queries
        assert versions({'bad': 1}) == []

        assert versions({'author': '/user/noone'}) == []
        
    def test_versions_by_bot(self):
        # create user TestBot and mark him as bot
        self.create_user('TestBot', 'testbot@example.com', 'test123', bot=True, data={'displayname': 'Test Bot'})
        
        site.save('/a', {'key': '/a', 'type': '/type/object'}, ip='1.2.3.4', comment='notbot')
        site.save('/b', {'key': '/b', 'type': '/type/object'}, ip='1.2.3.4', comment='bot', author=site._get_thing('/user/TestBot'))
        
        def f(q):
            return [v['key'] for v in site.versions(q)]
        
        assert f({'ip': '1.2.3.4'}) == ['/b', '/a']
        assert f({'ip': '1.2.3.4', 'bot': False}) == ['/a']
        assert f({'ip': '1.2.3.4', 'bot': True}) == ['/b']
            
    def test_property_cache(self):
        # Make sure a failed save_many query doesn't pollute property cache
        q = [
            {'key': '/a', 'type': '/type/object', 'a': 1},
            {'key': '/b', 'type': '/type/object', 'bad property': 1}
        ]
        try:
            site.save_many(q)
        except Exception:
            pass

        q = [
            {'key': '/a', 'type': '/type/object', 'a': 1},
        ]
        site.save_many(q)
        
    def test_things(self):
        print >> web.debug, "save /a"
        site.save('/a', {'key': '/a', 'type': '/type/object', 'x': 1, 'name': 'a'})

        print >> web.debug, "save /b"
        site.save('/b', {'key': '/b', 'type': '/type/object', 'x': 2, 'name': 'b'})
        
        assert site.things({'type': '/type/object'}) == [{'key': '/a'}, {'key': '/b'}]
        assert site.things({'type': {'key': '/type/object'}}) == [{'key': '/a'}, {'key': '/b'}]
        
        assert site.things({'type': '/type/object', 'sort': 'created'}) == [{'key': '/a'}, {'key': '/b'}]
        assert site.things({'type': '/type/object', 'sort': '-created'}) == [{'key': '/b'}, {'key': '/a'}]
        
        assert site.things({'type': '/type/object', 'x': 1}) == [{'key': '/a'}]
        assert site.things({'type': '/type/object', 'x': '1'}) == []
        
        assert site.things({'type': '/type/object', 'name': 'a'}) == [{'key': '/a'}]

        # should return empty result when queried with non-existing or bad property
        assert site.things({'type': '/type/object', 'foo': 'bar'}) == []
        assert site.things({'type': '/type/object', 'bad property': 'bar'}) == []

        # should return empty result when queried for non-existing objects
        assert site.things({'type': '/type/object', 'foo': {'key': '/foo'}}) == []
        assert site.things({'type': '/type/bad'}) == []
        
    def test_nested_things(self):
        site.save('/a', {
            'key': '/a', 
            'type': '/type/object',
            'links': [{
                'name': 'x',
                'url': 'http://example.com/x'
            },
            {
                'name': 'y',
                'url': 'http://example.com/y1'
            }]
        })

        site.save('/b', {
            'key': '/b', 
            'type': '/type/object',
            'links': [{
                'name': 'y',
                'url': 'http://example.com/y2'
            },
            {
                'name': 'z',
                'url': 'http://example.com/z'
            }]
        })
        
        site.things({'type': '/type/object', 'links.name': 'x'}) == [{'key': '/a'}]
        site.things({'type': '/type/object', 'links.name': 'y'}) == [{'key': '/a'}, {'key': '/b'}]
        site.things({'type': '/type/object', 'links.name': 'z'}) == [{'key': '/b'}]

        site.things({'type': '/type/object', 'links': {'name': 'x', 'url': 'http://example.com/y1'}}) == [{'key': '/a'}]

        site.things({'type': '/type/object', 'links': {'name': 'x'}}) == [{'key': '/a'}]
        site.things({'type': '/type/object', 'links': {'name': 'y'}}) == [{'key': '/a'}, {'key': '/b'}]
        site.things({'type': '/type/object', 'links': {'name': 'z'}}) == [{'key': '/b'}]

########NEW FILE########
__FILENAME__ = test_logreader
import datetime
from infogami.infobase import logreader

def test_nextday():
    assert logreader.nextday(datetime.date(2010, 10, 20)) == datetime.date(2010, 10, 21)
    assert logreader.nextday(datetime.date(2010, 10, 31)) == datetime.date(2010, 11, 1)    
    
def test_daterange():
    def f(begin, end):
        return list(logreader.daterange(begin, end))
        
    oct10 = datetime.date(2010, 10, 10)
    oct11 = datetime.date(2010, 10, 11)
    assert f(oct10, oct10) == [oct10]
    assert f(oct10, oct11) == [oct10, oct11]
    assert f(oct11, oct10) == []
    
def test_to_timestamp():
    assert logreader.to_timestamp('2010-01-02T03:04:05.678900') == datetime.datetime(2010, 1, 2, 3, 4, 5, 678900)

class TestLogFile:
    def test_file2date(self):
        logfile = logreader.LogFile("foo")
        assert logfile.file2date("foo/2010/10/20.log") == datetime.date(2010, 10, 20)


    def test_date2file(self):
        logfile = logreader.LogFile("foo")
        assert logfile.date2file(datetime.date(2010, 10, 20)) == "foo/2010/10/20.log"

    def test_tell(self, tmpdir):
        root = tmpdir.mkdir("log")
        logfile = logreader.LogFile(root.strpath)
        
        # when there are no files, it must tell the epoch time
        assert logfile.tell() == datetime.date.fromtimestamp(0).isoformat() + ":0"
        
    def test_find_filelist(self, tmpdir):
        root = tmpdir.mkdir("log")
        logfile = logreader.LogFile(root.strpath)
        
        # when there are no files, it should return empty list.
        assert logfile.find_filelist() == []
        assert logfile.find_filelist(from_date=datetime.date(2010, 10, 10)) == []
        
        # create empty log file and check if it returns them
        d = root.mkdir("2010").mkdir("10")
        f1 = d.join("01.log")
        f1.write("")
        f2 = d.join("02.log")
        f2.write("")
        assert logfile.find_filelist() == [f1.strpath, f2.strpath]
        assert logfile.find_filelist(from_date=datetime.date(2010, 10, 2)) == [f2.strpath]

        # create a bad file and make it behaves correctly
        d.join("foo.log").write("")
        assert logfile.find_filelist() == [f1.strpath, f2.strpath]

    def test_readline(self, tmpdir):
        root = tmpdir.mkdir("log")
        logfile = logreader.LogFile(root.strpath)
        assert logfile.readline() == ''
        
        root.mkdir("2010").mkdir("10")
        f = root.join("2010/10/01.log")
        f.write("helloworld\n")
        assert logfile.readline() == 'helloworld\n'
        
        f.write("hello 1\n", mode='a')
        f.write("hello 2\n", mode='a')
        assert logfile.readline() == 'hello 1\n'
        assert logfile.readline() == 'hello 2\n'
        assert logfile.readline() == ''

    def test_seek(self, tmpdir):
        root = tmpdir.mkdir("log")
        logfile = logreader.LogFile(root.strpath)
        
        # seek should not have any effect when there are no log files.
        pos = logfile.tell()
        logfile.seek("2010-10-10:0")
        pos2 = logfile.tell()
        assert pos == pos2
        
        # when the requested file is not found, offset should go to the next available file.
        root.mkdir("2010").mkdir("10")
        f = root.join("2010/10/20.log")
        f.write("")
        
        logfile.seek("2010-10-10:0")
        assert logfile.tell() == "2010-10-20:0"
        
########NEW FILE########
__FILENAME__ = test_read
from infogami.infobase import dbstore
from infogami.infobase._dbstore.save import SaveImpl
from infogami.infobase._dbstore.store import Store
from infogami.infobase._dbstore.read import RecentChanges

import utils

import datetime

def setup_module(mod):
    utils.setup_db(mod)
    
def teardown_module(mod):
    utils.teardown_db(mod)

class DBTest:
    def setup_method(self, method):
        self.tx = db.transaction()
        db.insert("thing", key='/type/object')

    def teardown_method(self, method):
        self.tx.rollback()

class TestRecentChanges(DBTest):
    def _save(self, docs, author=None, ip="1.2.3.4", comment="testing", kind="test_save", timestamp=None, data=None):
        timestamp = timestamp=timestamp or datetime.datetime(2010, 01, 02, 03, 04, 05)
        s = SaveImpl(db)
        s.save(docs, 
            timestamp=timestamp,
            comment=comment, 
            ip=ip, 
            author=author,
            action=kind,
            data=data
        )
        
    def recentchanges(self, **kw):
        return RecentChanges(db).recentchanges(**kw)
        
    def doc(self, key, **kw):
        doc = {
            "key": key,
            "type": {"key": "/type/object"}
        }
        doc.update(kw)
        return doc

    def save_doc(self, key, **kw):
        docs = [self.doc(key)]
        return self._save(docs, **kw)
        
    def test_all(self, wildcard):
        docs = [
            {"key": "/foo", "type": {"key": "/type/object"}, "title": "foo"},
            {"key": "/bar", "type": {"key": "/type/object"}, "title": "bar"}
        ]
        timestamp = datetime.datetime(2010, 01, 02, 03, 04, 05)
        self._save(docs, comment="testing recentchanges", timestamp=timestamp)

        engine = RecentChanges(db)
        changes = engine.recentchanges(limit=1)
        
        assert changes == [{
            "id": wildcard,
            "kind": "test_save",
            "timestamp": timestamp.isoformat(), 
            "comment": "testing recentchanges",
            "ip": "1.2.3.4",
            "author": None,
            "changes": [
                {"key": "/foo", "revision": 1},
                {"key": "/bar", "revision": 1},
            ],
            "data": {}
        }]
        
        engine.get_change(changes[0]['id']) == {
            "id": wildcard,
            "kind": "test_save",
            "timestamp": timestamp.isoformat(), 
            "comment": "testing recentchanges",
            "ip": "1.2.3.4",
            "author": None,
            "changes": [
                {"key": "/foo", "revision": 1},
                {"key": "/bar", "revision": 1},
            ],
            "data": {}
        }     
        
    def test_author(self):
        db.insert("thing", key='/user/one')
        db.insert("thing", key='/user/two')
        
        self.save_doc('/zero')
        self.save_doc("/one", author="/user/one")
        self.save_doc("/two", author="/user/two")
                
        assert len(self.recentchanges(author="/user/one")) == 1
        assert len(self.recentchanges(author="/user/two")) == 1
        
    def test_ip(self):
        db.insert("thing", key='/user/foo')
        
        self.save_doc("/zero")
        self.save_doc("/one", ip="1.1.1.1")
        self.save_doc("/two", ip="2.2.2.2")
            
        assert len(self.recentchanges(ip="1.1.1.1")) == 1
        assert len(self.recentchanges(ip="2.2.2.2")) == 1        
        
        self.save_doc("/three", author="/user/foo", ip="1.1.1.1")

        # srecentchanges by logged in users should be ignored in ip queries
        assert len(self.recentchanges(ip="1.1.1.1")) == 1
        
        # query with bad ip should not fail.
        assert len(self.recentchanges(ip="bad.ip")) == 0
        assert len(self.recentchanges(ip="1.1.1.345")) == 0
        assert len(self.recentchanges(ip="1.1.1.-1")) == 0
        assert len(self.recentchanges(ip="1.2.3.4.5")) == 0
        assert len(self.recentchanges(ip="1.2.3")) == 0
        
    def new_account(self, username, **kw):
        # backdoor to create new account
        
        db.insert("thing", key='/user/' + username)
        
        store = Store(db)
        store.put("account/" + username, dict(kw,
            type="account",
            status="active"
        ))
        
    def test_bot(self):        
        self.new_account("one", bot=False)
        self.new_account("two", bot=True)
                
        self.save_doc("/zero")
        self.save_doc("/one", author="/user/one")
        self.save_doc("/two", author="/user/two")
        
        assert len(self.recentchanges(bot=True)) == 1
        assert len(self.recentchanges(bot=False)) == 2
        assert len(self.recentchanges(bot=None)) == 3
                
    def test_key(self):
        assert self.recentchanges(key='/foo') == []
        
        self.save_doc("/foo")
        self.save_doc("/bar")
        
        assert len(self.recentchanges(key='/foo')) == 1
        
    def test_data(self):
        self.save_doc("/zero", data={"foo": "bar"})
        assert self.recentchanges(limit=1)[0]['data'] == {"foo": "bar"}

    def test_query_by_data(self):
        self.save_doc("/one", data={"x": "one"})
        self.save_doc("/two", data={"x": "two"})

        assert self.recentchanges(limit=1, data={"x": "one"})[0]['changes'] == [{"key": "/one", "revision": 1}]
        assert self.recentchanges(limit=1, data={"x": "two"})[0]['changes'] == [{"key": "/two", "revision": 1}]        
                
    def test_kind(self):
        self.save_doc("/zero", kind="foo")
        self.save_doc("/one", kind="bar")

        assert len(self.recentchanges(kind=None)) == 2
        assert len(self.recentchanges(kind="foo")) == 1
        assert len(self.recentchanges(kind="bar")) == 1
        
    def test_query_by_date(self):
        def doc(key):
            return {"key": key, "type": {"key": "/type/object"}}
            
        def date(datestr):
            y, m, d = datestr.split("-")
            return datetime.datetime(int(y), int(m), int(d))
        
        self.save_doc("/a", kind="foo", timestamp=date("2010-01-02"), comment="a")
        self.save_doc("/b", kind="bar", timestamp=date("2010-01-03"), comment="b")
        
        def changes(**kw):
            return [c['comment'] for c in RecentChanges(db).recentchanges(**kw)]

        # begin_date is included in the interval, but end_date is not included.
        assert changes(begin_date=date("2010-01-01")) == ['b', 'a']
        assert changes(begin_date=date("2010-01-02")) == ['b', 'a']
        assert changes(begin_date=date("2010-01-03")) == ['b']
        assert changes(begin_date=date("2010-01-04")) == []

        assert changes(end_date=date("2010-01-01")) == []
        assert changes(end_date=date("2010-01-02")) == []
        assert changes(end_date=date("2010-01-03")) == ['a']
        assert changes(end_date=date("2010-01-04")) == ['b', 'a']
        
        assert changes(begin_date=date("2010-01-01"), end_date=date("2010-01-03")) == ['a']
        assert changes(begin_date=date("2010-01-01"), end_date=date("2010-01-04")) == ['b', 'a']

########NEW FILE########
__FILENAME__ = test_save
from infogami.infobase import dbstore
from infogami.infobase._dbstore.save import SaveImpl, IndexUtil, PropertyManager

import utils

import web
import simplejson
import os
import datetime
import unittest

def setup_module(mod):
    utils.setup_db(mod)
    
def teardown_module(mod):
    utils.teardown_db(mod)

class DBTest:
    def setup_method(self, method):
        self.tx = db.transaction()
        db.insert("thing", key='/type/type')
        db.insert("thing", key='/type/object')
        
    def teardown_method(self, method):
        self.tx.rollback()
        
def update_doc(doc, revision, created, last_modified):
    """Add revision, latest_revision, created and latest_revision properties to the given doc.
    """    
    last_modified_repr = {"type": "/type/datetime", "value": last_modified.isoformat()}
    created_repr = {"type": "/type/datetime", "value": created.isoformat()}
    
    return dict(doc, 
        revision=revision,
        latest_revision=revision,
        created=created_repr,
        last_modified=last_modified_repr)

def assert_record(record, doc, revision, created, timestamp):
    d = update_doc(doc, revision, created, timestamp)
    assert record.data == d
    
    assert record.key == doc['key']
    assert record.created == created
    assert record.last_modified == timestamp
    assert record.revision == revision
    
    if revision == 1:
        assert record.id is None
        assert record.prev.data is None
    else:
        assert record.id is not None
        assert record.prev.data is not None

class Test_get_records_for_save(DBTest):
    """Tests for _dbstore_save._get_records_for_save.
    """
    def test_new(self):
        s = SaveImpl(db)
        timestamp = datetime.datetime(2010, 01, 01, 01, 01, 01)

        a = {"key": "/a", "type": {"key": "/type/object"}, "title": "a"}
        b = {"key": "/b", "type": {"key": "/type/object"}, "title": "b"}
        
        docs = [a, b]
        records = s._get_records_for_save(docs, timestamp)
        
        assert len(records) == 2
        assert_record(records[0], docs[0], 1, timestamp, timestamp)
        assert_record(records[1], docs[1], 1, timestamp, timestamp)
        
    def test_existing(self):
        def insert(doc, revision, created, last_modified):
            id =  db.insert('thing', key=doc['key'], latest_revision=revision, created=created, last_modified=last_modified)
            db.insert('data', seqname=False, thing_id=id, revision=revision, data=simplejson.dumps(doc))
        
        created = datetime.datetime(2010, 01, 01, 01, 01, 01)            
        a = {"key": "/a", "type": {"key": "/type/object"}, "title": "a"}
        insert(a, 1, created, created)

        s = SaveImpl(db)
        timestamp = datetime.datetime(2010, 02, 02, 02, 02, 02)            
        records = s._get_records_for_save([a], timestamp)
        
        assert_record(records[0], a, 2, created, timestamp)
        
class Test_save(DBTest):        
    def get_json(self, key):
        d = db.query("SELECT data.data FROM thing, data WHERE data.thing_id=thing.id AND data.revision = thing.latest_revision AND thing.key = '/a'")
        return simplejson.loads(d[0].data)
        
    def test_save(self):
        s = SaveImpl(db)
        timestamp = datetime.datetime(2010, 01, 01, 01, 01, 01)
        a = {"key": "/a", "type": {"key": "/type/object"}, "title": "a"}
        
        status = s.save([a], 
                    timestamp=timestamp, 
                    ip="1.2.3.4",
                    author=None, 
                    comment="Testing create.", 
                    action="save")
                    
        assert status['changes'][0]['revision'] == 1
        assert self.get_json('/a') == update_doc(a, 1, timestamp, timestamp) 
        
        a['title'] = 'b'
        timestamp2 = datetime.datetime(2010, 02, 02, 02, 02, 02) 
        status = s.save([a], 
                    timestamp=timestamp2, 
                    ip="1.2.3.4", 
                    author=None, 
                    comment="Testing update.", 
                    action="save")
        assert status['changes'][0]['revision'] == 2
        assert self.get_json('/a') == update_doc(a, 2, timestamp, timestamp2) 
        
    def test_type_change(self):
        s = SaveImpl(db)
        timestamp = datetime.datetime(2010, 01, 01, 01, 01, 01)
        a = {"key": "/a", "type": {"key": "/type/object"}, "title": "a"}
        status = s.save([a], 
                    timestamp=timestamp, 
                    ip="1.2.3.4",
                    author=None, 
                    comment="Testing create.", 
                    action="save")
                    
        # insert new type
        type_delete_id = db.insert("thing", key='/type/delete')
        a['type']['key'] = '/type/delete'

        timestamp2 = datetime.datetime(2010, 02, 02, 02, 02, 02) 
        status = s.save([a], 
                    timestamp=timestamp2, 
                    ip="1.2.3.4", 
                    author=None, 
                    comment="Testing type change.", 
                    action="save")
        
        assert status['changes'][0]['revision'] == 2
        assert self.get_json('/a') == update_doc(a, 2, timestamp, timestamp2) 
        
        thing = db.select("thing", where="key='/a'")[0]
        assert thing.type == type_delete_id

    def test_with_author(self):
        pass
        
    def test_versions(self):
        pass
        
    def _get_book_author(self, n):
        author = {
            "key": "/author/%d" % n,
            "type": {"key": "/type/object"},
            "name": "author %d" % n
        }
        book = {
            "key": "/book/%d" % n,
            "type": {"key": "/type/object"},
            "author": {"key": "/author/%d" % n}
        }
        return author, book
        
    def test_save_with_cross_refs(self):
        author, book = self._get_book_author(1)
        self._save([author, book])

        author, book = self._get_book_author(2)  
        self._save([book, author])
        
    def _save(self, docs):
        s = SaveImpl(db)
        timestamp = datetime.datetime(2010, 01, 01, 01, 01, 01)
        return s.save(docs, timestamp=timestamp, comment="foo", ip="1.2.3.4", author=None, action="save")
    
    def test_save_with_new_type(self):
        docs = [{
            "key": "/type/foo",
            "type": {"key": "/type/type"}
        }, {
            "key": "/foo",
            "type": {"key": "/type/foo"}
        }]
        s = SaveImpl(db)
        timestamp = datetime.datetime(2010, 01, 01, 01, 01, 01)
        
        s.save(docs, timestamp=timestamp, comment="foo", ip="1.2.3.4", author=None, action="save")
        
        type = db.query("SELECT * FROM thing where key='/type/foo'")[0]
        thing = db.query("SELECT * FROM thing where key='/foo'")[0]
        assert thing.type == type.id
        
    def test_save_with_all_datatypes(self):
        doc = {
            "key": "/foo",
            "type": {"key": "/type/object"},
            "xtype": {"key": "/type/object"},
            "int": 1,
            "str": "foo",
            "text": {"type": "/type/text", "value": "foo"},
            "date": {"type": "/type/datetime", "value": "2010-01-02T03:04:05"},
        }
        self._save([doc])
        
    def test_save_with_long_string(self):
        docs = [{
            "key": "/type/foo",
            "type": {"key": "/type/type"},
            "title": "a" * 4000
        }]
        s = SaveImpl(db)
        timestamp = datetime.datetime(2010, 01, 01, 01, 01, 01)
        s.save(docs, timestamp=timestamp, comment="foo", ip="1.2.3.4", author=None, action="save")
        
    def test_transaction(self, wildcard):
        docs = [{
            "key": "/foo",
            "type": {"key": "/type/object"},
        }]
        s = SaveImpl(db)
        timestamp = datetime.datetime(2010, 01, 01, 01, 01, 01)
        changeset = s.save(docs, timestamp=timestamp, comment="foo", ip="1.2.3.4", author=None, action="save")
        changeset.pop("docs")
        changeset.pop("old_docs")
        
        assert changeset == {
            "id": wildcard,
            "kind": "save",
            "timestamp": timestamp.isoformat(),
            "bot": False,
            "comment": "foo",
            "ip": "1.2.3.4",
            "author": None,
            "changes": [{"key": "/foo", "revision": 1}],
            "data": {}
        }
        
class MockDB:
    def __init__(self):
        self.reset()
        
    def delete(self, table, vars={}, **kw):
        self.deletes.append(dict(kw, table=table))
        
    def insert(self, table, **kw):
        self.inserts.append(dict(kw, table=table))
        
    def reset(self):
        self.inserts = []
        self.deletes = []
        
class MockSchema:
    def find_table(self, type, datatype, name):
        return "datum_" + datatype
        
def pytest_funcarg__testdata(request):        
    return {
        "doc1": {
            "key": "/doc1",
            "type": {"key": "/type/object"},
            "xtype": {"key": "/type/object"},
            "x": "x0",
            "y": ["y1", "y2"],
            "z": {"a": "za", "b": "zb"},
            "n": 5,
            "text": {
                "type": "/type/text",
                "value": "foo"
            }
        },
        "doc1.index": {
            ("/type/object", "/doc1", "int", "n"): [5],
            ("/type/object", "/doc1", "ref", "xtype"): ['/type/object'],
            ("/type/object", "/doc1", "str", "x"): ["x0"],
            ("/type/object", "/doc1", "str", "y"): ["y1", "y2"],
            ("/type/object", "/doc1", "str", "z.a"): ["za"],
            ("/type/object", "/doc1", "str", "z.b"): ["zb"],
        },
    }

class TestIndex:
    def setup_method(self, method):
        self.indexer = IndexUtil(MockDB(), MockSchema())
        
    def monkeypatch_indexer(self):
        self.indexer.get_thing_ids = lambda keys: dict((k, "id:" + k) for k in keys)
        self.indexer.get_property_id = lambda type, name: "p:%s-%s" % (type.split("/")[-1], name)
        self.indexer.get_table = lambda type, datatype, name: "%s_%s" % (type.split("/")[-1], datatype)
        
    def test_monkeypatch(self):
        self.monkeypatch_indexer()
        assert self.indexer.get_thing_ids(["a", "b"]) == {"a": "id:a", "b": "id:b"}
        assert self.indexer.get_property_id("/type/book", "title") == "p:book-title"
        assert self.indexer.get_table("/type/book", "foo", "bar") == "book_foo"
        
    def process_index(self, index):
        """Process index to remove order in the values, so that it is easier to compare."""
        return dict((k, set(v)) for k, v in index.iteritems())
                
    def test_compute_index(self, testdata):
        index = self.indexer.compute_index(testdata['doc1'])
        assert self.process_index(index) == self.process_index(testdata['doc1.index'])
        
    def test_dict_difference(self):
        f = self.indexer._dict_difference
        d1 = {"w": 1, "x": 2, "y": 3}
        d2 = {"x": 2, "y": 4, "z": 5}
        
        assert f(d1, d2) == {"w": 1, "y": 3}
        assert f(d2, d1) == {"y": 4, "z": 5}
    
    def test_diff_index(self):
        doc1 = {
            "key": "/books/1",
            "type": {"key": "/type/book"},
            "title": "foo",
            "author": {"key": "/authors/1"}
        }
        doc2 = dict(doc1, title='bar')
        
        deletes, inserts = self.indexer.diff_index(doc1, doc2)
        assert deletes == {
            ("/type/book", "/books/1", "str", "title"): ["foo"]
        }
        assert inserts == {
            ("/type/book", "/books/1", "str", "title"): ["bar"]
        }

        deletes, inserts = self.indexer.diff_index(None, doc1)
        assert deletes == {}
        assert inserts == {
            ("/type/book", "/books/1", "ref", "author"): ["/authors/1"],
            ("/type/book", "/books/1", "str", "title"): ["foo"]
        }
        
        # when type is changed all the old properties must be deleted
        doc2 = dict(doc1, type={"key": "/type/object"})
        deletes, inserts = self.indexer.diff_index(doc1, doc2)
        assert deletes == {
            ("/type/book", "/books/1", "ref", None): [],
            ("/type/book", "/books/1", "str", None): [],
            ("/type/book", "/books/1", "int", None): [],
        }
        
    def test_diff_records(self):
        doc1 = {
            "key": "/books/1",
            "type": {"key": "/type/book"},
            "title": "foo",
            "author": {"key": "/authors/1"}
        }
        doc2 = dict(doc1, title='bar')
        record = web.storage(key='/books/1', data=doc2, prev=web.storage(data=doc1))

        deletes, inserts = self.indexer.diff_records([record])
        assert deletes == {
            ("/type/book", "/books/1", "str", "title"): ["foo"]
        }
        assert inserts == {
            ("/type/book", "/books/1", "str", "title"): ["bar"]
        }
        
    def test_compile_index(self):
        self.monkeypatch_indexer()
        
        index = {
            ("/type/book", "/books/1", "str", "name"): ["Getting started with py.test"],
            ("/type/book", "/books/2", "ref", "author"): ["/authors/1"],
        }
        self.indexer.compile_index(index) == {
            ("book_str", "id:/books/1", "p:book-name"): ["Getting started with py.test"],
            ("book_ref", "id:/books/2", "p:book-author"): ["id:/authors/1"],
        }
        
        # When the type is changed, property_name will be None to indicate that all the properties are to be removed.
        index = {
            ("/type/books", "/books/1", "str", None): []
        }
        self.indexer.compile_index(index) == {
            ("book_str", "id:/books/1", None): []
        }
        
    def test_too_long(self):
        assert self.indexer._is_too_long("a" * 10000) == True
        assert self.indexer._is_too_long("a" * 2047) == False
        c = u'\u20AC' # 3 bytes in utf-8
        assert self.indexer._is_too_long(c * 1000) == True
        
class TestIndexWithDB(DBTest):
    def _save(self, docs):
        s = SaveImpl(db)
        timestamp = datetime.datetime(2010, 01, 01, 01, 01, 01)
        return s.save(docs, timestamp=timestamp, comment="foo", ip="1.2.3.4", author=None, action="save")
    
    def test_reindex(self):
        a = {"key": "/a", "type": {"key": "/type/object"}, "title": "a"}
        self._save([a])
        
        thing = db.query("SELECT * FROM thing WHERE key='/a'")[0]
        key_id = db.query("SELECT * FROM property WHERE type=$thing.type AND name='title'", vars=locals())[0].id

        # there should be only one entry in the index
        d = db.query("SELECT * FROM datum_str WHERE thing_id=$thing.id AND key_id=$key_id",vars=locals())        
        assert len(d) == 1
        
        # corrupt the index table by adding bad entries
        for i in range(10):
            db.insert("datum_str", thing_id=thing.id, key_id=key_id, value="foo %d" % i)
            
        # verify that the bad enties are added
        d = db.query("SELECT * FROM datum_str WHERE thing_id=$thing.id AND key_id=$key_id",vars=locals())        
        assert len(d) == 11
        
        # reindex now and verify again that there is only one entry
        SaveImpl(db).reindex(["/a"])
        d = db.query("SELECT * FROM datum_str WHERE thing_id=$thing.id AND key_id=$key_id",vars=locals())        
        assert len(d) == 1
            
        
class TestPropertyManager(DBTest):
    def test_get_property_id(self):
        p = PropertyManager(db)
        assert p.get_property_id("/type/object", "title") == None
        
        pid = p.get_property_id("/type/object", "title", create=True)
        assert pid is not None
        
        assert p.get_property_id("/type/object", "title") == pid
        assert p.get_property_id("/type/object", "title", create=True) == pid
        
    def test_rollback(self):
        # cache is not invalidated on rollback. This test confirms that behavior.

        tx = db.transaction()
        p = PropertyManager(db)
        pid = p.get_property_id("/type/object", "title", create=True)
        tx.rollback()

        assert p.get_property_id("/type/object", "title") == pid
                        
    def test_copy(self):
        p = PropertyManager(db)
        pid = p.get_property_id("/type/object", "title", create=True)
        
        # copy should inherit the cache
        p2 = p.copy()
        assert p2.get_property_id("/type/object", "title") == pid
        
        # changes to the cache of the copy shouldn't effect the source.
        tx = db.transaction()
        p2.get_property_id("/type/object", "title2", create=True)
        tx.rollback()        
        assert p.get_property_id("/type/object", "title2") is None

########NEW FILE########
__FILENAME__ = test_seq
from infogami.infobase._dbstore.sequence import SequenceImpl
import utils

import unittest
import simplejson

def setup_module(mod):
    utils.setup_db(mod)
    mod.seq = SequenceImpl(db)
    
def teardown_module(mod):
    utils.teardown_db(mod)
    mod.seq = None

class TestSeq:
    def setup_method(self, method):
        db.delete("seq", where="1=1")
            
    def test_seq(self):
        seq.get_value("foo") == 0
        seq.next_value("foo") == 1
        seq.get_value("foo") == 1

        seq.next_value("foo") == 2
        seq.next_value("foo") == 3
        
########NEW FILE########
__FILENAME__ = test_server

########NEW FILE########
__FILENAME__ = test_store
from infogami.infobase._dbstore.store import Store, TypewiseIndexer
from infogami.infobase import common

import utils

import simplejson
import py.test

def setup_module(mod):
    utils.setup_db(mod)
    mod.store = Store(db)
    
def teardown_module(mod):
    utils.teardown_db(mod)
    mod.store = None

class DBTest:
    def setup_method(self, method):
        self.tx = db.transaction()
        db.insert("thing", key='/type/object')
        
    def teardown_method(self, method):
        self.tx.rollback()

class TestStore(DBTest):
    def test_insert(self, wildcard):
        for i in range(10):
            d = {"name": str(i), "value": i}
            store.put(str(i), d)
            
        for i in range(10):
            d = {"name": str(i), "value": i, "_key": str(i), "_rev": wildcard}
            assert store.get(str(i)) == d

    def test_update(self, wildcard):
        store.put("foo", {"name": "foo"})
        assert store.get("foo") == dict(name="foo", _key="foo", _rev=wildcard)

        store.put("foo", {"name": "bar", "_rev": None})
        assert store.get("foo") == dict(name="bar", _key="foo", _rev=wildcard)
        
    def test_conflicts(self):
        foo = store.put("foo", {"name": "foo"})
        
        # calling without _rev should fail
        assert py.test.raises(common.Conflict, store.put, "foo", {"name": "bar"}) 
        
        # Calling with _rev should update foo
        foo2 = store.put("foo", {"name": "foo2", "_rev": foo['_rev']})
        assert foo2['_key'] == foo['_key']
        assert foo2['_rev'] != foo['_rev']

        # calling with _rev=None should also pass
        foo3 = store.put("foo", {"name": "foo3", "_rev": None})
        
        # calling with bad/stale _rev should fail
        assert py.test.raises(common.Conflict, store.put, "foo", {"name": "foo4", "_rev": foo['_rev']})        
        
    def test_notfound(self):
        assert store.get("xxx") is None
        assert store.get_json("xxx") is None
        assert store.get_row("xxx") is None
        
    def test_delete(self, wildcard):
        d = {"name": "foo"}
        store.put("foo", d)        
        assert store.get("foo") == dict(d, _key="foo", _rev=wildcard)
        
        store.delete("foo")
        assert store.get("foo") is None
        
        store.put("foo", {"name": "bar"})    
        assert store.get("foo") == {"name": "bar", "_key": "foo", "_rev": wildcard}
                
    def test_query(self):
        store.put("one", {"type": "digit", "name": "one", "value": 1})
        store.put("two", {"type": "digit", "name": "two", "value": 2})
        
        store.put("a", {"type": "char", "name": "a"})
        store.put("b", {"type": "char", "name": "b"})

        # regular query
        assert store.query("digit", "name", "one") == [{'key': "one"}]
        
        # query for type
        assert store.query("digit", None, None) == [{"key": "two"}, {"key": "one"}]
        assert store.query("char", None, None) == [{"key": "b"}, {"key": "a"}]
        
        # query for all
        assert store.query(None, None, None) == [{"key": "b"}, {"key": "a"}, {"key": "two"}, {"key": "one"}]

    def test_query_order(self):
        store.put("one", {"type": "digit", "name": "one", "value": 1})
        store.put("two", {"type": "digit", "name": "two", "value": 2})

        assert store.query("digit", None, None) == [{"key": "two"}, {"key": "one"}]

        # after updating "one", it should show up first in the query results
        store.put("one", {"type": "digit", "name": "one", "value": 1, "x": 1, "_rev": None})
        assert store.query("digit", None, None) == [{"key": "one"}, {"key": "two"}]

    def test_query_include_docs(self, wildcard):
        assert store.query(None, None, None, include_docs=True) == []
        
        store.put("one", {"type": "digit", "name": "one", "value": 1})
        store.put("two", {"type": "digit", "name": "two", "value": 2})
        
        assert store.query("digit", "name", "one", include_docs=True) == [
            {'key': "one", "doc": {"type": "digit", "name": "one", "value": 1, "_key": "one", "_rev": wildcard}}
        ]
        assert store.query(None, None, None, include_docs=True) == [
            {'key': "two", "doc": {"type": "digit", "name": "two", "value": 2, "_key": "two", "_rev": wildcard}},
            {'key': "one", "doc": {"type": "digit", "name": "one", "value": 1, "_key": "one", "_rev": wildcard}},
        ]
        
    def test_indexer(self):
        s = Store(db)
        s.put("foo", {"type": "account", "name": "foo", "bot": False, "age": 42, "d": {"x": 1}})
        rows = db.query("SELECT name, value from store_index")
        d = dict((row.name, row.value) for row in rows)

        assert d == {
            "_key": "foo",
            "name": "foo",
            "bot": "false",
            "age": "42",
            "d.x": "1"
        }

    def test_indexer2(self):
        s = Store(db)
        s.indexer = BookIndexer()
        
        s.put("book", {"title": "The lord of the rings", "lang": "en"})
        assert store.query("", "lang", "en") == []
        assert store.query("", "title,lang", "The lord of the rings--en") == [{'key': 'book'}]

    def test_typewise_indexer(self):                
        t = TypewiseIndexer()
        t.set_indexer("book", BookIndexer())
        
        def f(doc):
            return sorted(t.index(doc))

        assert f({"type": "book", "title": "foo", "lang": "en", "name": "foo"}) == [("title,lang", "foo--en")]
        assert f({"name": "foo"}) == [("name", "foo")]
                        
    def test_typewise_indexer2(self):
        s = Store(db)
        s.indexer = TypewiseIndexer()
        s.indexer.set_indexer("book", BookIndexer())
        
        s.put("book", {"type": "book", "title": "The lord of the rings", "lang": "en"})
        s.put("one", {"type": "digit", "name": "one"})
        s.put("foo", {"name": "foo"})
        
        assert store.query("", "lang", "en") == []
        assert store.query("book", "title,lang", "The lord of the rings--en") == [{"key": "book"}]
        
        assert store.query("digit", "name", "one") == [{"key": "one"}]
        assert store.query("", "name", "foo") == [{"key": "foo"}]
        
    def test_multiput(self):
        store.put("x", {"name": "foo"})
        store.put("x", {"name": "foo", "_rev": None})
        store.put("x", {"name": "foo", "_rev": None})
                
        assert store.query(None, None, None) == [{"key": "x"}]
        assert store.query("", None, None) == [{"key": "x"}]
        assert store.query("", "name", "foo") == [{"key": "x"}]
        
class BookIndexer:
    def index(self, doc):
        yield "title,lang", doc['title'] + "--" + doc['lang']
        
########NEW FILE########
__FILENAME__ = test_writequery
import web

import utils
from .. import common, writequery

def setup_module(mod):
    utils.setup_site(mod)
    
    type_book = {
        "key": "/type/book",
        "kind": "regular",
        "type": {"key": "/type/type"},
        "properties": [{
            "name": "title",
            "expected_type": {"key": "/type/string"},
            "unique": True
        }, {
            "name": "authors",
            "expected_type": {"key": "/type/author"},
            "unique": False
        }, {
            "name": "publish_year",
            "expected_type": {"key": "/type/int"},
            "unique": True
        }, {
            "name": "links",
            "expected_type": {"key": "/type/link"},
            "unique": False
        }]
    }
    type_author = {
        "key": "/type/author",
        "kind": "regular",
        "type": {"key": "/type/type"},
        "properties": [{
            "name": "name",
            "expected_type": {"key": "/type/string"},
            "unique": True
        }]
    }
    type_link = {
        "key": "/type/link",
        "kind": "embeddable",
        "type": {"key": "/type/type"},
        "properties": [{
            "name": "title",
            "expected_type": {"key": "/type/string"},
            "unique": True
        }, {
            "name": "url",
            "expected_type": {"key": "/type/string"},
            "unique": True
        }]
    }
    mod.site.save_many([type_book, type_author, type_link])
    
def teardown_module(mod):
    utils.teardown_site(mod)

class DBTest:
    def setup_method(self, method):
        self.tx = db.transaction()

    def teardown_method(self, method):
        self.tx.rollback()

class TestSaveProcessor(DBTest):
    def test_errors(self):
        def save_many(query):
            try:
                site.save_many(query)
            except common.InfobaseException, e:
                return e.dict()

        q = {
            "key": "/authors/1",
        }
        assert save_many([q]) == {'error': 'bad_data', 'message': 'missing type', 'at': {'key': '/authors/1'}}
        
        q = {
            "key": "/authors/1",
            "type": "/type/author",
            "name": ["a", "b"]
        }
        assert save_many([q]) == {
            'error': 'bad_data', 
            'message': 'expected atom, found list', 
            'at': {'key': '/authors/1', 'property': 'name'},
            'value': ['a', 'b']
        }

        q = {
            "key": "/authors/1",
            "type": "/type/author",
            "name": 123
        }
        assert save_many([q]) == {
            'error': 'bad_data', 
            'message': 'expected /type/string, found /type/int', 
            'at': {'key': '/authors/1', 'property': 'name'},
            "value": 123
        }

        q = {
            "key": "/books/1",
            "type": "/type/book",
            "authors": [{"key": "/authors/1"}]
        }
        assert save_many([q]) == {'error': 'notfound', 'key': '/authors/1', 'at': {'key': '/books/1', 'property': 'authors'}}

        q = {
            "key": "/books/1",
            "type": "/type/book",
            "publish_year": "not-int"
        }
        assert save_many([q]) == {'error': 'bad_data', 
            'message': "invalid literal for int() with base 10: 'not-int'", 
            'at': {
                'key': '/books/1', 
                'property': 'publish_year'
            },
            "value": "not-int"
        }

        q = {
            "key": "/books/1",
            "type": "/type/book",
            "links": ["foo"]
        }
        assert save_many([q]) == {
            'error': 'bad_data', 
            'message': 'expected /type/link, found /type/string', 
            'at': {
                'key': '/books/1', 
                'property': 'links'
            },
            'value': 'foo'
        }
        
        q = {
            "key": "/books/1",
            "type": "/type/book",
            "links": [{"title": 1}]
        }
        assert save_many([q]) == {
            'error': 'bad_data', 
            'message': 'expected /type/string, found /type/int',
            'at': {
                'key': '/books/1', 
                'property': 'links.title'
            },
            'value': 1
        }
        
    def test_process_value(self):
        def property(expected_type, unique=True, name='foo'):
            return web.storage(expected_type=web.storage(key=expected_type, kind='regular'), unique=unique, name=name)

        p = writequery.SaveProcessor(site.store, None)
        assert p.process_value(1, property('/type/int')) == 1
        assert p.process_value('1', property('/type/int')) == 1
        assert p.process_value(['1', '2'], property('/type/int', unique=False)) == [1, 2]

########NEW FILE########
__FILENAME__ = utils
from infogami.infobase import dbstore, client, server

import os
import web

db_parameters = dict(dbn='postgres', db='infobase_test', user=os.getenv('USER'), pw='', pooling=False)

@web.memoize
def recreate_database():
    """drop and create infobase_test database.
    
    This function is memoized to recreate the db only once per test session.
    """
    assert os.system('dropdb infobase_test; createdb infobase_test') == 0
    
    db = web.database(**db_parameters)
    
    schema = dbstore.default_schema or dbstore.Schema()
    sql = str(schema.sql())
    db.query(sql)

def setup_db(mod):
    recreate_database()

    mod.db_parameters = db_parameters.copy()
    web.config.db_parameters = db_parameters.copy()
    mod.db = web.database(**db_parameters)
    
    mod._create_database = dbstore.create_database
    dbstore.create_database = lambda *a, **kw: mod.db
    
    mod._tx = mod.db.transaction()
    
def teardown_db(mod):
    dbstore.create_database = mod._create_database
    
    mod._tx.rollback()
    
    mod.db.ctx.clear()
    try:
        del mod.db
    except:
        pass
    
def setup_conn(mod):
    setup_db(mod)
    web.config.db_parameters = mod.db_parameters
    web.config.debug = False
    mod.conn = client.LocalConnection()

def teardown_conn(mod):
    teardown_db(mod)
    try:
        del mod.conn 
    except:
        pass
    
def setup_server(mod):
    # clear unwanted state
    web.ctx.clear()
    
    server._infobase = None # clear earlier reference, if any.
    server.get_site("test") # initialize server._infobase
    mod.site = server._infobase.create("test") # create a new site

def teardown_server(mod):
    server._infobase = None
            
    try:
        del mod.site
    except:
        pass

def setup_site(mod):
    web.config.db_parameters = db_parameters.copy()
    setup_db(mod)
    setup_server(mod)
    
def teardown_site(mod):
    teardown_server(mod)
    teardown_db(mod)

########NEW FILE########
__FILENAME__ = utils
"""Generic utilities.
"""
import datetime
import re
import web

try:
    from __builtin__ import any, all
except ImportError:
    def any(seq):
        for x in seq:
            if x:
                return True
                
    def all(seq):
        for x in seq:
            if not x:
                return False
        return True

def parse_datetime(value):
    """Creates datetime object from isoformat.
    
        >>> t = '2008-01-01T01:01:01.010101'
        >>> parse_datetime(t).isoformat()
        '2008-01-01T01:01:01.010101'
    """
    if isinstance(value, datetime.datetime):
        return value
    else:
        tokens = re.split('-|T|:|\.| ', value)
        return datetime.datetime(*map(int, tokens))
    
def parse_boolean(value):
    return web.safeunicode(value).lower() in ["1", "true"]

def dict_diff(d1, d2):
    """Compares 2 dictionaries and returns the following.
    
        * all keys in d1 whose values are changed in d2
        * all keys in d1 which have same values in d2
        * all keys in d2 whose values are changed in d1
    
        >>> a, b, c = dict_diff({'x': 1, 'y': 2, 'z': 3}, {'x': 11, 'z': 3, 'w': 23})
        >>> sorted(a), sorted(b), sorted(c)
        (['x', 'y'], ['z'], ['w', 'x'])
    """
    same = set(k for k in d1 if d1[k] == d2.get(k))
    left = set(d1.keys()).difference(same)
    right = set(d2.keys()).difference(same)
    return left, same, right
                        
def pprint(obj):
    """Pretty prints given object.
    >>> pprint(1)
    1
    >>> pprint("hello")
    'hello'
    >>> pprint([1, 2, 3])
    [1, 2, 3]
    >>> pprint({'x': 1, 'y': 2})
    {
        'x': 1,
        'y': 2
    }
    >>> pprint([dict(x=1, y=2), dict(c=1, a=2)])
    [{
        'x': 1,
        'y': 2
    }, {
        'a': 2,
        'c': 1
    }]
    >>> pprint({'x': 1, 'y': {'a': 1, 'b': 2}, 'z': 3})
    {
        'x': 1,
        'y': {
            'a': 1,
            'b': 2
        },
        'z': 3
    }
    >>> pprint({})
    {
    }
    """
    print prepr(obj)
    
def prepr(obj, indent=""):
    """Pretty representaion."""
    if isinstance(obj, list):
        return "[" + ", ".join(prepr(x, indent) for x in obj) + "]"
    elif isinstance(obj, tuple):
        return "(" + ", ".join(prepr(x, indent) for x in obj) + ")"
    elif isinstance(obj, dict):
        if hasattr(obj, '__prepr__'):
            return obj.__prepr__()
        else:
            indent = indent + "    "
            items = ["\n" + indent + prepr(k) + ": " + prepr(obj[k], indent) for k in sorted(obj.keys())]
            return '{' + ",".join(items) + "\n" + indent[4:] + "}"
    else:
        return repr(obj)

def flatten(nested_list, result=None):
    """Flattens a nested list.::
    
        >>> flatten([1, [2, 3], [4, [5, 6]]])
        [1, 2, 3, 4, 5, 6]
    """
    if result is None:
        result = []
        
    for x in nested_list:
        if isinstance(x, list):
            flatten(x, result)
        else:
            result.append(x)
    return result
    
def flatten_dict(d):
    """Flattens a dictionary.::
    
        >>> flatten_dict({"key": "/books/foo", "type": {"key": "/type/book"}, "authors": [{"key": "/authors/a1"}, {"key": "/authors/a2"}]})
        [('type.key', '/type/book'), ('key', '/books/foo'), ('authors.key', '/authors/a1'), ('authors.key', '/authors/a2')]
    """
    def f(key, value):
        if isinstance(value, dict):
            for k, v in value.items():
                f(key + "." + k, v)
        elif isinstance(value, list):
            for v in value:
                f(key, v)
        else:
            key = web.lstrips(key, ".")
            items.append((key, value))
    items = []
    f("", d)
    return items

def safeint(value, default):
    """Converts a string to integer. Returns the specified default value on error.::
     
        >>> safeint("1", 0)
        1
        >>> safeint("foo", 0)
        0
        >>> safeint(None, 0)
        0
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

if __name__ == "__main__":
    import doctest
    doctest.testmod()
########NEW FILE########
__FILENAME__ = writequery
"""
"""
import common
from common import pprint, any, all
import web
import simplejson
import account

def get_thing(store, key, revision=None):
    if isinstance(key, common.Reference):
        key = unicode(key)
    json = store.get(key, revision)
    return json and common.Thing.from_json(store, key, json)
    
class PermissionEngine:
    """Engine to check if a user has permission to modify a document.
    """
    def __init__(self, store):
        self.store = store
        self.things = {}
        
    def get_thing(self, key):
        try:
            return self.things[key]
        except KeyError:
            t = get_thing(self.store, key)
            self.things[key] = t
            return t
            
    def has_permission(self, author, key):
        # admin user can modify everything
        if author and author.key == account.get_user_root() + 'admin':
            return True

        permission = self.get_permission(key)
        if permission is None:
            return True
        else:
            groups = permission.get('writers') or [] 
            # admin users can edit anything
            groups = groups + [self.get_thing('/usergroup/admin')]
            for group in groups:
                if group.key == '/usergroup/everyone':
                    return True
                elif author is not None:
                    members = [m.key for m in group.get('members', [])]
                    if group.key == '/usergroup/allusers' or author.key in members:
                        return True
                else:
                    return False        

    def get_permission(self, key):
        """Returns permission for the specified key."""
        def parent(key):
            if key == "/":
                return None
            else:
                return key.rsplit('/', 1)[0] or "/"

        def _get_permission(key, child_permission=False):
            if key is None:
                return None
            thing = self.get_thing(key)
            if child_permission:
                permission = thing and (thing.get("child_permission") or thing.get("permission"))
            else:
                permission = thing and thing.get("permission")
            return permission or _get_permission(parent(key), child_permission=True)

        return _get_permission(key)

class SaveProcessor:
    def __init__(self, store, author):
        self.store = store
        self.author = author
        self.permission_engine = PermissionEngine(self.store)
        
        self.things = {}
        
        self.types = {}
        
        self.key = None
        
    def process_many(self, docs):
        keys = [doc['key'] for doc in docs]
        self.things = dict((doc['key'], common.Thing.from_dict(self.store, doc['key'], doc)) for doc in docs)
        
        def parse_type(value):
            if isinstance(value, basestring):
                return value
            elif isinstance(value, dict) and 'key' in value:
                return value['key']
            else:
                return None

        # for verifying expected_type, type of the referenced objects is required. 
        # Finding the the types in one shot instead of querying each one separately.
        for doc in docs:
            self.types[doc['key']] = parse_type(doc.get('type'))
        refs = list(k for k in self.find_references(docs) if k not in self.types)
        self.types.update(self.find_types(refs))
        
        prev_data = self.get_many(keys)
        docs = [self._process(doc['key'], doc, prev_data.get(doc['key'])) for doc in docs]
        
        return [doc for doc in docs if doc]
        
    def find_types(self, keys):
        types = {}
        
        if keys:
            d = self.store.get_metadata_list(keys)
            type_ids = list(set(row.type for row in d.values())) 
            typedict = self.store.get_metadata_list_from_ids(type_ids)
            
            for k, row in d.items():
                types[k] = typedict[row.type].key
        return types
        
    def find_references(self, d, result=None):
        if result is None:
            result = set()
            
        if isinstance(d, dict):
            if len(d) == 1 and d.keys() == ["key"]:
                result.add(d['key'])
            else:
                for k, v in d.iteritems():
                    if k != "type":
                        self.find_references(v, result)
        elif isinstance(d, list):
            for v in d:
                self.find_references(v, result)
        return result
            
    def get_thing(self, key):
        try:
            return self.things[key]
        except KeyError:
            t = get_thing(self.store, key)
            self.things[key] = t
            return t
            
    def get_type(self, key):
        try:
            return self.types[key]
        except KeyError:
            t = get_thing(self.store, key)
            return t and t.type.key
            
    def get_many(self, keys):
        d = self.store.get_many_as_dict(keys)
        return dict((k, simplejson.loads(json)) for k, json in d.items())

    def process(self, key, data):
        prev_data = self.get_many([key])
        return self._process(key, data, prev_data.get(key))
        
    def _process(self, key, data, prev_data=None):
        self.key = key # hack to make key available when raising exceptions.
        
        
        if 'key' not in data:
            data['key'] = key
            
        if web.ctx.get('infobase_bootstrap', False):
            return data

        assert data['key'] == key

        data = common.parse_query(data)
        self.validate_properties(data)
        prev_data = prev_data and common.parse_query(prev_data)
        
        if not web.ctx.get('disable_permission_check', False) and not self.has_permission(self.author, key):
            raise common.PermissionDenied(message='Permission denied to modify %s' % repr(key))
        
        type = data.get('type')
        if type is None:
            raise common.BadData(message="missing type", at=dict(key=key))
        type = self.process_value(type, self.get_property(None, 'type'))
        type = self.get_thing(type)
        
        # when type is changed, consider as all object is modified and don't compare with prev data.
        if prev_data and prev_data.get('type') != type.key:
            prev_data = None

        data = self.process_data(data, type, prev_data)

        for k in common.READ_ONLY_PROPERTIES:
            data.pop(k, None)
            prev_data and prev_data.pop(k, None)
            
        if data == prev_data:
            return None
        else:
            return data
    
    def has_permission(self, author, key):
        return self.permission_engine.has_permission(author, key)

    def get_property(self, type, name):
        if name == 'type':
            return web.storage(name='type', expected_type=web.storage(key='/type/type', kind="regular"), unique=True)
        elif name in ['permission', 'child_permission']:
            return web.storage(name=name, expected_type=web.storage(key='/type/permission', kind="regular"), unique=True)
        else:
            for p in type.get('properties', []):
                if p.get('name') == name:
                    return p
                    
    def validate_properties(self, data):
        rx = web.re_compile('^[a-z][a-z0-9_]*$')
        for key in data:
            if not rx.match(key):
                raise common.BadData(message="Bad Property: %s" % repr(key), at=dict(key=self.key))

    def process_data(self, d, type, old_data=None, prefix=""):
        for k, v in d.items():
            if v is None or v == [] or web.safeunicode(v).strip() == '':
                del d[k]
            else:
                if old_data and old_data.get(k) == v:
                    continue
                p = self.get_property(type, k)
                if p:
                    d[k] = self.process_value(v, p, prefix=prefix)
                else:
                    d[k] = v
        if type:
            d['type'] = common.Reference(type.key)
            
        return d

    def process_value(self, value, property, prefix=""):
        unique = property.get('unique', True)
        expected_type = property.expected_type.key
        
        at = {"key": self.key, "property": prefix + property.name}

        if isinstance(value, list):
            if unique is True:
                raise common.BadData(message='expected atom, found list', at=at, value=value)
            
            p = web.storage(property.copy())
            p.unique = True
            return [self.process_value(v, p) for v in value]
    
        if unique is False:    
            raise common.BadData(message='expected list, found atom', at=at, value=value)

        type_found = common.find_type(value)
    
        if expected_type in common.primitive_types:
            # string can be converted to any type and int can be converted to float
            try:
                if type_found == '/type/string' and expected_type != '/type/string':
                    value = common.primitive_types[expected_type](value)
                elif type_found == '/type/int' and expected_type == '/type/float':
                    value = float(value)
            except ValueError, e:
                raise common.BadData(message=str(e), at=at, value=value)
        elif property.expected_type.kind == 'embeddable':
            if isinstance(value, dict):
                return self.process_data(value, property.expected_type, prefix=at['property'] + ".")
            else:
                raise common.TypeMismatch(expected_type, type_found, at=at, value=value)
        else:
            if type_found == '/type/string':
                value = common.Reference(value)
    
        type_found = common.find_type(value)
    
        if type_found == '/type/object':
            type_found = self.get_type(value)
            
            # type is not found only when the thing id not found.
            if type_found is None:
                raise common.NotFound(key=unicode(value), at=at)

        if expected_type != type_found:
            raise common.BadData(message='expected %s, found %s' % (property.expected_type.key, type_found), at=at, value=value)
        return value
        

class WriteQueryProcessor:
    def __init__(self, store, author):
        self.store = store
        self.author = author
        
    def process(self, query):
        p = SaveProcessor(self.store, self.author)
        
        for q in serialize(query):
            q = common.parse_query(q)
            
            if not isinstance(q, dict) or q.get('key') is None:
                continue

            key = q['key']                
            thing = get_thing(self.store, key)
            create = q.pop('create', None)
            
            if thing is None:
                if create:
                    q = self.remove_connects(q)
                else:
                    raise common.NotFound(key=key)
            else:
                q = self.connect_all(thing._data, q)
            
            yield p.process(key, q)
    
    def remove_connects(self, query):
        for k, v in query.items():
            if isinstance(v, dict) and 'connect' in v:
                if 'key' in v:
                    value = v['key'] and common.Reference(v['key'])
                else:
                    value = v['value']
                query[k] = value
        return query
            
    def connect_all(self, data, query):
        """Applys all connects specified in the query to data.
        
            >>> p = WriteQueryProcessor(None, None)
            >>> data = {'a': 'foo', 'b': ['foo', 'bar']}
            
            >>> query = {'a': {'connect': 'update', 'value': 'bar'}, 'b': {'connect': 'insert', 'value': 'foobar'}}
            >>> p.connect_all(data, query)
            {'a': 'bar', 'b': ['foo', 'bar', 'foobar']}
            
            >>> query = {'a': {'connect': 'update', 'value': 'bar'}, 'b': {'connect': 'delete', 'value': 'foo'}}
            >>> p.connect_all(data, query)
            {'a': 'bar', 'b': ['bar']}

            >>> query = {'a': {'connect': 'update', 'value': 'bar'}, 'b': {'connect': 'update_list', 'value': ['foo', 'foobar']}}
            >>> p.connect_all(data, query)
            {'a': 'bar', 'b': ['foo', 'foobar']}
        """
        import copy
        data = copy.deepcopy(data)
        
        for k, v in query.items():
            if isinstance(v, dict):
                if 'connect' in v:
                    if 'key' in v:
                        value = v['key'] and common.Reference(v['key'])
                    else:
                        value = v['value']            
                    self.connect(data, k, v['connect'], value)
        return data
        
    def connect(self, data, name, connect, value):
        """Modifies the data dict by performing the specified connect.
        
            >>> getdata = lambda: {'a': 'foo', 'b': ['foo', 'bar']}
            >>> p = WriteQueryProcessor(None, None)
            
            >>> p.connect(getdata(), 'a', 'update', 'bar')
            {'a': 'bar', 'b': ['foo', 'bar']}
            >>> p.connect(getdata(), 'b', 'update_list', ['foobar'])
            {'a': 'foo', 'b': ['foobar']}
            >>> p.connect(getdata(), 'b', 'insert', 'foobar')
            {'a': 'foo', 'b': ['foo', 'bar', 'foobar']}
            >>> p.connect(getdata(), 'b', 'insert', 'foo')
            {'a': 'foo', 'b': ['foo', 'bar']}
            >>> p.connect(getdata(), 'b', 'delete', 'foobar')
            {'a': 'foo', 'b': ['foo', 'bar']}
        """
        if connect == 'update' or connect == 'update_list':
            data[name] = value
        elif connect == 'insert':
            if value not in data[name]:
                data[name].append(value)
        elif connect == 'delete':
            if value in data[name]:
                data[name].remove(value)
        return data
            
def serialize(query):
    ""
    r"""Serializes a nested query such that each subquery acts on a single object.

        >>> q = {
        ...     'create': 'unless_exists',
        ...     'key': '/foo',
        ...     'type': '/type/book',
        ...     'author': {
        ...        'create': 'unless_exists',
        ...        'key': '/bar',
        ...     },
        ...     'descption': {'value': 'foo', 'type': '/type/text'}
        ... }
        >>> serialize(q)
        [{
            'create': 'unless_exists',
            'key': '/bar'
        }, {
            'author': {
                'key': '/bar'
            },
            'create': 'unless_exists',
            'descption': {
                'type': '/type/text',
                'value': 'foo'
            },
            'key': '/foo',
            'type': '/type/book'
        }]
        >>> q = {
        ...     'create': 'unless_exists',
        ...     'key': '/foo',
        ...     'authors': {
        ...         'connect': 'update_list',
        ...         'value': [{
        ...             'create': 'unless_exists',
        ...             'key': '/a/1'
        ...         }, {
        ...             'create': 'unless_exists',
        ...             'key': 'a/2'
        ...         }]
        ...     }
        ... }
        >>> serialize(q)
        [{
            'create': 'unless_exists',
            'key': '/a/1'
        }, {
            'create': 'unless_exists',
            'key': 'a/2'
        }, {
            'authors': {
                'connect': 'update_list',
                'value': [{
                    'key': '/a/1'
                }, {
                    'key': 'a/2'
                }]
            },
            'create': 'unless_exists',
            'key': '/foo'
        }]
    """
    def flatten(query, result, path=[], from_list=False):
        """This does two things. 
	    1. It flattens the query and appends it to result.
        2. It returns its minimal value to use in parent query.
        """
        if isinstance(query, list):
            data = [flatten(q, result, path + [str(i)], from_list=True) for i, q in enumerate(query)]
            return data
        elif isinstance(query, dict):
            #@@ FIX ME
            q = query.copy()
            for k, v in q.items():
                q[k] = flatten(v, result, path + [k])
                
            if 'key' in q:
                result.append(q)
                
            if from_list:
                #@@ quick fix
                if 'key' in q:
                    data = {'key': q['key']}
                else:
                    # take keys (connect, key, type, value) from q
                    data = dict((k, v) for k, v in q.items() if k in ("connect", "key", "type", "value"))
            else:
                # take keys (connect, key, type, value) from q
                data = dict((k, v) for k, v in q.items() if k in ("connect", "key", "type", "value"))
            return data
        else:
            return query
            
    result = []
    flatten(query, result)                         
    return result

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = indexer
from infogami.infobase import common
import web

class Indexer:
    """Indexer computes the values to be indexed.
    
        >>> indexer = Indexer()
        >>> sorted(indexer.compute_index({"key": "/books/foo", "title": "The Foo Book", "authors": [{"key": "/authors/a1"}, {"key": "/authors/a2"}]}))
        [('ref', 'authors', '/authors/a1'), ('ref', 'authors', '/authors/a2'), ('str', 'title', 'The Foo Book')]
    """
    def compute_index(self, doc):
        """Returns an iterator with (datatype, key, value) for each value be indexed.
        """
        index = common.flatten_dict(doc)
        
        # skip special values and /type/text
        skip = ["id", "key", "type.key", "revision", "latest_revison", "last_modified", "created"]
        index = set((k, v) for k, v in index if k not in skip and not k.endswith(".value") and not k.endswith(".type"))
        
        for k, v in index:
            if k.endswith(".key"):
                yield 'ref', web.rstrips(k, ".key"), v
            elif isinstance(v, basestring):
                yield 'str', k, v
            elif isinstance(v, int):
                yield 'int', k, v
    
    def diff_index(self, old_doc, new_doc):
        """Compute the difference between the index of old doc and new doc.
        Returns the indexes to be deleted and indexes to be inserted.
        
        >>> i = Indexer()
        >>> r1 = {"key": "/books/foo", "title": "The Foo Book", "authors": [{"key": "/authors/a1"}, {"key": "/authors/a2"}]}
        >>> r2 = {"key": "/books/foo", "title": "The Bar Book", "authors": [{"key": "/authors/a2"}]}
        >>> deletes, inserts = i.diff_index(r1, r2)
        >>> list(deletes)
        [('str', 'title', 'The Foo Book'), ('ref', 'authors', '/authors/a1')]
        >>> list(inserts)
        [('str', 'title', 'The Bar Book')]
        """
        def get_type(doc):
            return doc.get('type', {}).get('key', None)

        new_index = set(self.compute_index(new_doc))
        
        # nothing to delete when the old doc is not specified
        if not old_doc:
            return [], new_index
            
        old_index = set(self.compute_index(old_doc))
        if get_type(old_doc) != get_type(new_doc):
            return old_index, new_index
        else:
            return old_index.difference(new_index), new_index.difference(old_index)
        

########NEW FILE########
__FILENAME__ = read
"""Implementation of all read queries."""

from collections import defaultdict
import simplejson
import web
from infogami.infobase import config

def get_user_root():
    user_root = config.get("user_root", "/user")
    return user_root.rstrip("/") + "/"

def get_bot_users(db):
    """Returns thing_id of all bot users.
    """
    rows = db.query("SELECT store.key FROM store, store_index WHERE store.id=store_index.store_id AND type='account' AND name='bot' and value='true'")
    bots = [get_user_root() + row.key.split("/")[-1] for row in rows]
    if bots:
        bot_ids = [row.id for row in db.query("SELECT id FROM thing WHERE key in $bots", vars=locals())]
        return bot_ids or [-1]
    else:
        return [-1]

class RecentChanges:
    def __init__(self, db):
        self.db = db
        
    def get_keys(self, ids):
        ids = list(set(id for id in ids if id is not None))
        if ids:
            rows = self.db.query("SELECT id, key FROM thing WHERE id in $ids", vars=locals())
            return dict((row.id, row.key) for row in rows)
        else:
            return {}
            
    def get_thing_id(self, key):
        try:
            return self.db.where("thing", key=key)[0].id
        except IndexError:
            return None
            
    def get_change(self, id):
        try:
            change = self.db.select("transaction", where="id=$id", vars=locals())[0]
        except IndexError:
            return None
        
        authors = self.get_keys([change.author_id])
        return self._process_transaction(change, authors=authors)
    
    def recentchanges(self, limit=100, offset=0, **kwargs):
        tables = ['transaction t']
        what = 't.*'
        order = 't.created DESC'
        wheres = ["1 = 1"]
        
        if offset < 0:
            offset = 0
        
        key = kwargs.pop('key', None)
        if key is not None:
            thing_id = self.get_thing_id(key)
            if thing_id is None:
                return []
            else:
                tables.append('version v')
                wheres.append('v.transaction_id = t.id AND v.thing_id = $thing_id')
        
        bot = kwargs.pop('bot', None)
        if bot is not None:
            bot_ids = get_bot_users(self.db)
            if bot is True or str(bot).lower() == "true":
                wheres.append("t.author_id IN $bot_ids")
            else:
                wheres.append("(t.author_id NOT in $bot_ids OR t.author_id IS NULL)")

        author = kwargs.pop('author', None)
        if author is not None:
            author_id = self.get_thing_id(author)
            if not author_id:
                # Unknown author. Implies no changes by him.
                return []
            else:
                wheres.append("t.author_id=$author_id")
                
        ip = kwargs.pop("ip", None)
        if ip is not None:
            if not self._is_valid_ipv4(ip):
                return []
            else:
                # Don't include edits by logged in users when queried by ip. 
                wheres.append("t.ip = $ip AND t.author_id is NULL")
            
        kind = kwargs.pop('kind', None)
        if kind is not None:
            wheres.append('t.action = $kind')
            
        begin_date = kwargs.pop('begin_date', None)
        if begin_date is not None:
            wheres.append("t.created >= $begin_date")
        
        end_date = kwargs.pop('end_date', None)
        if end_date is not None:
            # end_date is not included in the interval.
            wheres.append("t.created < $end_date")
            
        data = kwargs.pop('data', None)
        if data:
            for i, (k, v) in enumerate(data.items()):
                t = 'ti%d' % i
                tables.append('transaction_index ' + t)
                q = '%s.tx_id = t.id AND %s.key=$k AND %s.value=$v' % (t, t, t)
                # k, v are going to change in the next iter of the loop.
                # bind the current values by calling reparam.
                wheres.append(web.reparam(q, locals())) 
        
        
        wheres = list(self._process_wheres(wheres, locals()))
        where = web.SQLQuery.join(wheres, " AND ")
        
        rows = self.db.select(tables, what=what, where=where, limit=limit, offset=offset, order=order, vars=locals()).list()

        authors = self.get_keys(row.author_id for row in rows)        
        
        return [self._process_transaction(row, authors) for row in rows]
        
    def _process_wheres(self, wheres, vars):
        for w in wheres:
            if isinstance(w, basestring):
                yield web.reparam(w, vars)
            else:
                yield w
        
    def _process_transaction(self, tx, authors):
        d = {
            "id": str(tx.id),
            "kind": tx.action or "edit",
            "timestamp": tx.created.isoformat(),
            "comment": tx.comment,
        }
        
        d['changes'] = tx.changes and simplejson.loads(tx.changes)

        if tx.author_id:
            d['author'] = {"key": authors[tx.author_id]}
            d['ip'] = None
        else:
            d['author'] = None
            d['ip'] = tx.ip

        # The new db schema has a data column in transaction table. 
        # In old installations, machine_comment column is used as data
        if tx.get('data'):
            d['data'] = simplejson.loads(tx.data)
        elif tx.get('machine_comment') and tx.machine_comment.startswith("{"):
            d['data'] = simplejson.loads(tx.machine_comment)
        else:
            d['data'] = {}
            
        return d
        
    def _is_valid_ipv4(self, ip):
        tokens = ip.split(".")
        try:
            return len(tokens) == 4 and all(0 <= int(t) < 256 for t in tokens)
        except ValueError:
            return False

########NEW FILE########
__FILENAME__ = save
"""Implementation of save for dbstore.
"""
import web
import simplejson
from collections import defaultdict

from indexer import Indexer
from schema import INDEXED_DATATYPES, Schema

from infogami.infobase import config, common

__all__ = ["SaveImpl"]

class SaveImpl:
    """Save implementaion."""
    def __init__(self, db, schema=None, indexer=None, property_manager=None):
        self.db = db
        self.indexUtil = IndexUtil(db, schema, indexer, property_manager and property_manager.copy())
        self.thing_ids = {}
        
    def process_json(self, key, json):
        """Hack to allow processing of json before using. Required for OL legacy."""
        return json
    
    def save(self, docs, timestamp, comment, ip, author, action, data=None):
        docs = list(docs)
        docs = common.format_data(docs)
        
        if not docs:
            return {}
            
        dbtx = self.db.transaction()
        try:
            records = self._get_records_for_save(docs, timestamp)
            self._update_thing_table(records)

            changes = [dict(key=r.key, revision=r.revision) for r in records]
            bot = bool(author and (self.get_user_details(author) or {}).get('bot', False))
            
            # add transaction
            changeset = dict(
                kind=action,
                author=author and {"key": author},
                ip=ip,
                comment=comment, 
                timestamp=timestamp.isoformat(), 
                bot=bot,
                changes=changes,
                data=data or {},
            )
            tx_id = self._add_transaction(changeset)
            changeset['id'] = str(tx_id)
                
            # add versions
            versions = [dict(thing_id=r.id, revision=r.revision, transaction_id=tx_id) for r in records]
            self.db.multiple_insert('version', versions, seqname=False)

            # add data
            data = [dict(thing_id=r.id, revision=r.revision, data=simplejson.dumps(r.data)) for r in records]
            self.db.multiple_insert('data', data, seqname=False)
            
            self._update_index(records)
        except:
            dbtx.rollback()
            raise
        else:
            dbtx.commit()
        changeset['docs'] = [r.data for r in records]
        changeset['old_docs'] = [r.prev.data for r in records]
        return changeset
        
    def _add_transaction(self, changeset):
        tx = {
            "action": changeset['kind'],
            "author_id": changeset['author'] and self.get_thing_id(changeset['author']['key']),
            "ip": changeset['ip'],
            "comment": changeset['comment'],
            "created": changeset['timestamp'],
            "changes": simplejson.dumps(changeset['changes']),
            "data": simplejson.dumps(changeset['data']),
        }
        if config.use_bot_column:
            tx['bot'] = changeset['bot']
            
        tx_id = self.db.insert("transaction", **tx)
        self._index_transaction_data(tx_id, changeset['data'])
        return tx_id
        
    def _index_transaction_data(self, tx_id, data):
        d = []
        def index(key, value):
            if isinstance(value, (basestring, int)):
                d.append({"tx_id": tx_id, "key": key, "value": value})
            elif isinstance(value, list):
                for v in value:
                    index(key, v)

        for k, v in data.iteritems():
            index(k, v)
                
        if d:
            self.db.multiple_insert("transaction_index", d, seqname=False)
        
    def reindex(self, keys):
        records = self._load_records(keys).values()
        
        for r in records:
            # Force reindex
            old_doc = {"key": r.key, "type": r.data['type'], "_force_reindex": True}
            r.prev = web.storage(r, data=old_doc)

        tx = self.db.transaction()
        try:
            self.indexUtil.update_index(records)
        except:
            tx.rollback()
            raise
        else:
            tx.commit()
        
    def _update_index(self, records):
        self.indexUtil.update_index(records)
        
    def dedup(self, docs):
        x = set()
        docs2 = []
        for doc in docs[::-1]:
            key = doc['key']
            if key in x:
                continue
            x.add(key)
            docs2.append(doc)
        return docs2[::-1]
            
    def _get_records_for_save(self, docs, timestamp):
        docs = self.dedup(docs)
        keys = [doc['key'] for doc in docs]        
        type_ids = self.get_thing_ids(doc['type']['key'] for doc in docs)
                
        records = self._load_records(keys)
        
        def make_record(doc):
            doc = dict(doc) # make a copy to avoid modifying the original.
            
            key = doc['key']
            r = records.get(key) or web.storage(id=None, key=key, revision=0, type=None, data=None, created=timestamp)
                        
            r.prev = web.storage(r)

            r.type = type_ids.get(doc['type']['key'])
            r.revision = r.prev.revision + 1
            r.data = doc
            r.last_modified = timestamp
            
            doc['latest_revision'] = r.revision
            doc['revision'] = r.revision
            doc['created'] = {"type": "/type/datetime", "value": r.created.isoformat()}
            doc['last_modified'] = {"type": "/type/datetime", "value": r.last_modified.isoformat()}
            return r
        
        return [make_record(doc) for doc in docs]
    
    def _load_records(self, keys):
        """Returns a dictionary of records for the given keys.
        
        The records are queried FOR UPDATE to lock those rows from concurrent updates.
        Each record is a storage object with (id, key, type, revision, last_modified, data) keys.
        """
        try:
            rows = self.db.query("SELECT thing.*, data.data FROM thing, data" + 
                " WHERE thing.key in $keys" + 
                " AND data.thing_id=thing.id AND data.revision = thing.latest_revision" + 
                " FOR UPDATE NOWAIT",
                vars=locals())
        except:
            raise common.Conflict(keys=keys, reason="Edit conflict detected.")
        
        records = dict((r.key, r) for r in rows)        
        for r in records.values():
            r.revision = r.latest_revision
            json = r.data and self.process_json(r.key, r.data)
            r.data = simplejson.loads(json)            
        return records
    
    def _fill_types(self, records):
        type_ids = self.get_thing_ids(r.data['type']['key'] for r in records)
        for r in records:
            r.type = type_ids[r.data['type']['key']]
            
    def _update_thing_table(self, records):
        """Insert/update entries in the thing table for the given records."""
        d = dict((r.key, r) for r in records)
        timestamp = records[0].last_modified
                
        # insert new records
        new = [dict(key=r.key, type=r.type, latest_revision=1, created=r.created, last_modified=r.last_modified) 
                for r in records if r.revision == 1]
                
        if new:
            ids = self.db.multiple_insert('thing', new)
            # assign id to the new records
            for r, id in zip(new, ids):
                d[r['key']].id = id

        # type must be filled after entries for new docs is added to thing table. 
        # Otherwise this function will fail when type is also created in the same query.
        self._fill_types(records)
        if any(r['type'] is None for r in new):
            for r in new:
                if r['type'] is None:
                    self.db.update("thing", type=d[r['key']]['type'], where="key=$key", vars={"key": r['key']})
                
        # update records with type change
        type_changed = [r for r in records if r.type != r.prev.type and r.revision != 1]
        for r in type_changed:
            self.db.update('thing', where='id=$r.id', vars=locals(),
                last_modified=timestamp, latest_revision=r.revision, type=r.type)

        # update the remaining records
        rest = [r.id for r in records if r.type == r.prev.type and r.revision > 1]
        if rest:
            self.db.query("UPDATE thing SET latest_revision=latest_revision+1, last_modified=$timestamp WHERE id in $rest", vars=locals())

    def get_thing_ids(self, keys):
        keys = list(set(keys))

        thing_ids = dict((key, self.thing_ids[key]) for key in keys if key in self.thing_ids)
        notfound = [key for key in keys if key not in thing_ids]

        if notfound:
            rows = self.db.query("SELECT id, key FROM thing WHERE key in $notfound", vars=locals())
            d = dict((r.key, r.id) for r in rows)
            thing_ids.update(d)
            self.thing_ids.update(d)

        return thing_ids
        
    def get_thing_id(self, key):
        return self.get_thing_ids([key])[key]

    def get_user_details(self, key):
        """Returns a storage object with user email and encrypted password."""
        account_key = "account/" + key.split("/")[-1]
        rows = self.db.query("SELECT * FROM store WHERE key=$account_key", vars=locals())
        if rows:
            return simplejson.loads(rows[0].json)
        else:
            return None

class IndexUtil:
    """
    
    There are 3 types of indexes that are used here. 
    
    1. triples
    
    Triples are indexeble (property, datatype, value) triples for a given document.
    
    2. document index

    Dictionary of (type, key, property, datatype) -> [values] for a set of documents. 
    This is generated by processing the triples.
    
    3. db index
    
    Dictionary of (table, thing_id, property_id) -> [values] for a set of documents.
    This is generated by compling the document index.
    """
    def __init__(self, db, schema=None, indexer=None, property_manager=None):
        self.db = db
        self.schema = schema or Schema()
        self._indexer = indexer or Indexer()
        self.property_manager = property_manager or PropertyManager(db)
        self.thing_ids = {}
        
    def compute_index(self, doc):
        """Computes the doc-index for given doc.        
        """
        type = doc['type']['key']
        key = doc['key']
        
        special = ["id", "type", "revision", "latest_revision", "created", "last_modified"]
        
        def ignorable(name, value):
            # ignore special properties
            # boolen values are not supported. 
            # ignore empty strings and Nones
            return name in special or isinstance(value, bool) or value is None or value == ""
        
        index = defaultdict(list)
        for datatype, name, value in self._indexer.compute_index(doc):
            if not ignorable(name, value):
                index[type, key, datatype, name].append(value)
        return index
        
    def diff_index(self, old_doc, new_doc):
        """Takes old and new docs and returns the indexes to be deleted and inserted."""
        def get_type(doc):
            return doc and doc.get('type', {}).get('key', None)
                
        new_index = self.compute_index(new_doc)
        
        # nothing to delete when there is no old doc
        if not old_doc:
            return {}, new_index
            
        if get_type(old_doc) != get_type(new_doc) or old_doc.get("_force_reindex"):
            key = new_doc['key']

            old_index = {}
            old_type = get_type(old_doc)
            for datatype in INDEXED_DATATYPES:
                # name is None means all the names need be deleted. 
                old_index[old_type, key, datatype, None] = []
                
            return old_index, new_index
        else:
            old_index = self.compute_index(old_doc)
            
            # comparision between the lists must be done without considering the order.
            # Converting the value to set before comparision is the simplest option.
            xset = lambda a: a and set(a)
            xeq = lambda a, b: xset(a) == xset(b)
            
            deletes = self._dict_difference(old_index, new_index, xeq)
            inserts = self._dict_difference(new_index, old_index, xeq)
            return deletes, inserts

    def _dict_difference(self, d1, d2, eq=None):
        """Returns set equivalant of d1.difference(d2) for dictionaries.
        """
        eq = eq or (lambda a, b: a == b)
        return dict((k, v) for k, v in d1.iteritems() if not eq(v, d2.get(k)))
    
    def diff_records(self, records):
        """Takes a list of records and returns the index to be deleted and index to be inserted.
        """
        deletes = {}
        inserts = {}
        
        for r in records:
            old_doc, new_doc = r.prev.data, r.data
            _deletes, _inserts = self.diff_index(old_doc, new_doc)
            deletes.update(_deletes)
            inserts.update(_inserts)
        return deletes, inserts
                
    def update_index(self, records):
        """Takes a list of records, computes the index to be deleted/inserted
        and updates the index tables in the database.
        """
        # update thing_ids to save some queries
        for r in records:
            self.thing_ids[r.key] = r.id
        
        deletes, inserts = self.diff_records(records)        
        deletes = self.compile_index(deletes)
        inserts = self.compile_index(inserts)
        
        self.delete_index(deletes)
        self.insert_index(inserts)
        
    def compile_index(self, index):
        """Compiles doc-index into db-index.
        """
        keys = set(key for type, key, datatype, name in index)
        for (type, key, datatype, name), values in index.iteritems():
            if datatype == 'ref':
                keys.update(values)
                
        thing_ids = self.get_thing_ids(keys)
        
        def get_value(value, datatype):
            if datatype == 'ref':
                return value and thing_ids[value]
            else:
                return value
                
        def get_values(values, datatype):
            return [get_value(v, datatype) for v in values]
        
        def get_pid(type, name):
            return name and self.get_property_id(type, name)
            
        dbindex = {}
        
        for (type, key, datatype, name), values in index.iteritems():
            table = self.find_table(type, datatype, name)
            thing_id = thing_ids[key]
            pid = get_pid(type, name)
            
            dbindex[table, thing_id, pid] = get_values(values, datatype)
            
        return dbindex
            
    def group_index(self, index):
        """Groups the index based on table.
        """
        groups = defaultdict(dict)
        for (table, thing_id, property_id), values in index.iteritems():
            groups[table][thing_id, property_id] = values
        return groups
        
    def ignore_long_values(self, index):
        """The DB schema has a limit of 2048 chars on string values. This function ignores values which are longer than that.
        """
        is_too_long = self._is_too_long
        return dict((k, [v for v in values if not is_too_long(v)]) for k, values in index.iteritems())
        
    def _is_too_long(self, v, limit=2048):
        return (
            isinstance(v, basestring) 
            # unicode string can be as long as 4 bytes in utf-8. 
            # This check avoid UTF-8 conversion for small strings.
            and len(v) > limit/4 
            and len(web.safestr(v)) > limit
        )
            
    def insert_index(self, index):
        """Inserts the given index into database."""
        for table, group in self.group_index(index).iteritems():
            # ignore values longer than 2048, the limit specified by the db schema.
            group = self.ignore_long_values(group)
            data = [dict(thing_id=thing_id, key_id=property_id, value=v) 
                for (thing_id, property_id), values in group.iteritems()
                for v in values]
            self.db.multiple_insert(table, data, seqname=False)
            
    def delete_index(self, index):
        """Deletes the given index from database."""
        for table, group in self.group_index(index).iteritems():
            
            thing_ids = [] # thing_ids to delete all
            
            # group all deletes for a thing_id
            d = defaultdict(list)
            for thing_id, property_id in group:
                if property_id:
                    d[thing_id].append(property_id)
                else:
                    thing_ids.append(thing_id)
                    
            if thing_ids:    
                self.db.delete(table, where='thing_id IN $thing_ids', vars=locals())
            
            for thing_id, pids in d.iteritems():
                self.db.delete(table, where="thing_id=$thing_id AND key_id IN $pids", vars=locals())
            
    def get_thing_ids(self, keys):
        ### TODO: same function is there is SaveImpl too. Get rid of this duplication.
        keys = list(set(keys))
        if not keys:
            return {}

        thing_ids = dict((key, self.thing_ids[key]) for key in keys if key in self.thing_ids)
        notfound = [key for key in keys if key not in thing_ids]

        if notfound:
            rows = self.db.query("SELECT id, key FROM thing WHERE key in $notfound", vars=locals())
            d = dict((r.key, r.id) for r in rows)
            thing_ids.update(d)
            self.thing_ids.update(d)

        return thing_ids
        
    def get_property_id(self, type, name):
        return self.property_manager.get_property_id(type, name, create=True)
        
    def find_table(self, type, datatype, name):
        return self.schema.find_table(type, datatype, name)
    
class PropertyManager:
    """Class to manage property ids.
    """
    def __init__(self, db):
        self.db = db
        self._cache = None
        self.thing_ids = {}
        
    def reset(self):
        self._cache = None
        self.thing_ids = {}
        
    def get_cache(self):
        if self._cache is None:
            self._cache = {}
            
            rows = self.db.select('property').list()
            type_ids = list(set(r.type for r in rows)) or [-1]
            types = dict((r.id, r.key) for r in self.db.select("thing", where='id IN $type_ids', vars=locals()))
            for r in rows:
                self._cache[types[r.type], r.name] = r.id
                
        return self._cache
        
    def get_property_id(self, type, name, create=False):
        """Returns the id of (type, name) property. 
        When create=True, a new property is created if not already exists.
        """
        try:
            return self.get_cache()[type, name]
        except KeyError:
            type_id = self.get_thing_id(type)
            d = self.db.query("SELECT * FROM property WHERE type=$type_id AND name=$name", vars=locals())

            if d:
                pid = d[0].id
            elif create:
                pid = self.db.insert('property', type=type_id, name=name)
            else:
                return None
                
            self.get_cache()[type, name] = pid
            return pid
    
    def get_thing_id(self, key):
        try:
            id = self.thing_ids[key]
        except KeyError:
            id = self.db.query("SELECT id FROM thing WHERE key=$key", vars=locals())[0].id
            self.thing_ids[key] = id
        return id
        
    def copy(self):
        """Returns a copy of this PropertyManager.
        Used in write transactions to avoid corrupting the global state in case of rollbacks.
        """
        p = PropertyManager(self.db)
        p._cache = self.get_cache().copy()
        p.thing_ids = self.thing_ids.copy()
        return p

########NEW FILE########
__FILENAME__ = schema
import web
import os

INDEXED_DATATYPES = ["str", "int", "ref"]

class Schema:
    """Schema to map <type, datatype, key> to database table.
    
        >>> schema = Schema()
        >>> schema.add_entry('page_str', '/type/page', 'str', None)
        >>> schema.find_table('/type/page', 'str', 'title')
        'page_str'
        >>> schema.find_table('/type/article', 'str', 'title')
        'datum_str'
    """
    def __init__(self, multisite=False):
        self.entries = []
        self.sequences = {}
        self.prefixes = set()
        self.multisite = multisite
        self._table_cache = {}
        
    def add_entry(self, table, type, datatype, name):
        entry = web.storage(table=table, type=type, datatype=datatype, name=name)
        self.entries.append(entry)
        
    def add_seq(self, type, pattern='/%d'):
        self.sequences[type] = pattern
        
    def get_seq(self, type):
        if type in self.sequences:
            # name is 'type_page_seq' for type='/type/page'
            name = type[1:].replace('/', '_') + '_seq'
            return web.storage(type=type, pattern=self.sequences[type], name=name)
        
    def add_table_group(self, prefix, type, datatypes=None):
        datatypes = datatypes or INDEXED_DATATYPES
        for d in datatypes:
            self.add_entry(prefix + "_" + d, type, d, None)
            
        self.prefixes.add(prefix)
        
    def find_table(self, type, datatype, name):
        if datatype not in INDEXED_DATATYPES:
            return None
            
        def f():
            def match(a, b):
                return a is None or a == b
            for e in self.entries:
                if match(e.type, type) and match(e.datatype, datatype) and match(e.name, name):
                    return e.table
            return 'datum_' + datatype
        
        key = type, datatype, name
        if key not in self._table_cache:
            self._table_cache[key] = f()
        return self._table_cache[key]
        
    def find_tables(self, type):
        return [self.find_table(type, d, None) for d in INDEXED_DATATYPES]
        
    def sql(self):
        prefixes = sorted(list(self.prefixes) + ['datum'])
        sequences = [self.get_seq(type).name for type in self.sequences]
        
        path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        t = web.template.frender(path)

        self.add_table_group("datum", None)
        
        tables = sorted(set([(e.table, e.datatype) for e in self.entries]))
        web.template.Template.globals['dict'] = dict
        web.template.Template.globals['enumerate'] = enumerate
        return t(tables, sequences, self.multisite)
        
    def list_tables(self):
        self.add_table_group("datum", None)
        tables = sorted(set([e.table for e in self.entries]))
        return tables
        
    def __str__(self):
        lines = ["%s\t%s\t%s\t%s" % (e.table, e.type, e.datatype, e.name) for e in self.entries]
        return "\n".join(lines)
########NEW FILE########
__FILENAME__ = sequence
"""High-level sequence API.
"""

class SequenceImpl:
    def __init__(self, db):
        self.db = db
        self.listener = None
        
    def set_listener(self, f):
        self.listener = f
        
    def fire_event(self, event_name, name, value):
        self.listener and self.listener("seq.set", {"name": name, "value": value})
        
    def get_value(self, name):
        try:
            return self.db.query("SELECT * FROM seq WHERE name=$name", vars=locals())[0].value
        except IndexError:
            return 0
        
    def next_value(self, name, increment=1):
        try:
            tx = self.db.transaction()
            d = self.db.query("SELECT * FROM seq WHERE name=$name FOR UPDATE", vars=locals())
            if d:
                value = d[0].value+1
                self.db.update("seq", value=value, where="name=$name", vars=locals())
            else:
                value = 1
                self.db.insert("seq", name=name, value=value)
        except:
            tx.rollback()
            raise
        else:
            tx.commit()
        return value
                
    def set_value(self, name, value):
        try:
            tx = self.db.transaction()
            d = self.db.query("SELECT * FROM seq WHERE name=$name FOR UPDATE", vars=locals())
            if d:
                self.db.update("seq", value=value, where="name=$name", vars=locals())
            else:
                self.db.insert("seq", name=name, value=value)
        except:
            tx.rollback()
            raise
        else:
            tx.commit()
        return value

########NEW FILE########
__FILENAME__ = store
"""JSON store for storing any unstructured data different from documents stored in the versioned database.

This provides a simple and limited interface for storing, retriving, querying documents.

    - get(key) -> data
    - put(key, data)
    - delete(key)
    
    - get_json(key) -> json
    - set_json(key, json)

    - list(limit=100, offset=0) -> keys
    - query(type, name, value, limit=100, offset=0) -> keys
    
Each doument can have an optional type property that can be used while querying.
The query interface is limited to only one name, value. No joins are possible and 
the result is always ordered by the internal id.

To overcome the limitation of joins, the store provides a pluggable indexer interface. 
The indexer decides the list of (name, value) pairs to index. 

The following indexer allows querying for books using lowercase titles and books written by the given author in the given language.

    class BookIndexer:
        def index(self, doc):
            yield "title.lower", doc.title.lower()
            
            for a in doc.authors:
                yield "author,lang", simplejson.dumps([a, doc.lang])
            
"""

from __future__ import with_statement

import simplejson
import web

from infogami.infobase import common

class Store:
    """JSON Store.
    """
    def __init__(self, db):
        self.db = db
        self.indexer = StoreIndexer()
        self.listener = None
        
    def get_row(self, key, for_update=False):
        q = "SELECT * FROM store WHERE key=$key"
        if for_update:
            q += " FOR UPDATE NOWAIT"
        rows = self.db.query(q, vars=locals())
        if rows:
            return rows[0]
            
    def set_listener(self, f):
        self.listener = f
            
    def fire_event(self, name, data):
        self.listener and self.listener(name, data)

    def get_json(self, key):
        d = self.get(key)
        return d and simplejson.dumps(d)
    
    def get(self, key):
        row = self.get_row(key)
        return row and self._get_doc(row)
            
    def _get_doc(self, row):
        doc = simplejson.loads(row.json)
        doc['_key'] = row.key
        doc['_rev'] = str(row.id)
        return doc
    
    def put(self, key, doc):
        if doc.get("_delete") == True:
            return self.delete(key, doc.get("_rev"))
        
        # conflict check is enabled by default. It can be disabled by passing _rev=None in the document.
        if "_rev" in doc and doc["_rev"] is None:
            enable_conflict_check = False
        else:
            enable_conflict_check = True
            
        doc.pop("_key", None)
        rev = doc.pop("_rev", None)
        
        json = simplejson.dumps(doc)
        
        tx = self.db.transaction()
        try:
            row = self.get_row(key, for_update=True)
            if row:
                if enable_conflict_check and str(row.id) != str(rev):
                    raise common.Conflict(key=key, message="Document update conflict")
                
                self.delete_index(row.id)
                
                # store query results are always order by id column.
                # It is important to update the id so that the newly modified
                # records show up first in the results.
                self.db.query("UPDATE store SET json=$json, id=nextval('store_id_seq') WHERE key=$key", vars=locals())
                
                id = self.get_row(key=key).id
            else:
                id = self.db.insert("store", key=key, json=json)

            self.add_index(id, key, doc)
            
            doc['_key'] = key
            doc['_rev'] = str(id)
        except:
            tx.rollback()
            raise
        else:
            tx.commit()
            self.fire_event("store.put", {"key": key, "data": doc})
            
        return doc

    def put_many(self, docs):
        """Stores multiple docs in a single transaction.
        """
        with self.db.transaction():
            for doc in docs:
                key = doc['_key']
                self.put(key, doc)
    
    def put_json(self, key, json):
        self.put(key, simplejson.loads(json))
    
    def delete(self, key, rev=None):
        tx = self.db.transaction()
        try:
            row = self.get_row(key, for_update=True)
            if row:
                if rev is not None and str(row.id) != str(rev):
                    raise common.Conflict(key=key, message="Document update conflict")
                self.delete_row(row.id)
        except:
            tx.rollback()
            raise
        else:
            tx.commit()
            self.fire_event("store.delete", {"key": key})
            
    def delete_row(self, id):
        """Deletes a row. This must be called in a transaction."""
        self.db.delete("store_index", where="store_id=$id", vars=locals())
        self.db.delete("store", where="id=$id", vars=locals())
        
    def query(self, type, name, value, limit=100, offset=0, include_docs=False):
        """Query the json store.
        
        Returns keys of all documents of the given type which have (name, value) in the index.
        All the documents of the given type are returned when the name is None.
        All the documents are returned when the type is None.
        """
        if type is None:
            rows = self.db.select("store", what="store.*", limit=limit, offset=offset, order="store.id desc", vars=locals())
        else:
            tables = ["store", "store_index"]
            wheres = ["store.id = store_index.store_id", "type = $type"]
            
            if name is None:
                wheres.append("name='_key'")
            else:
                wheres.append("name=$name AND value=$value")
            rows = self.db.select(tables, what='store.*', where=" AND ".join(wheres), limit=limit, offset=offset, order="store.id desc", vars=locals())
            
        def process_row(row):
            if include_docs:
                return {"key": row.key, "doc": self._get_doc(row)}
            else:
                return {"key": row.key}
                
        return [process_row(row) for row in rows]
    
    def delete_index(self, id):
        self.db.delete("store_index", where="store_id=$id", vars=locals())
        
    def add_index(self, id, key, data):
        if isinstance(data, dict):
            type = data.get("type", "")
        else:
            type = ""
        d = [web.storage(store_id=id, type=type, name="_key", value=key)]
        ignored = ["type"]
        for name, value in set(self.indexer.index(data)):
            if not name.startswith("_") and name not in ignored:
                if isinstance(value, bool):
                    value = str(value).lower()
                d.append(web.storage(store_id=id, type=type, name=name, value=value))
        if d:
            self.db.multiple_insert('store_index', d)
            
class StoreIndexer:
    """Default indexer for store.
    
    Indexes all properties of the given document.
    """
    def index(self, doc):
        return common.flatten_dict(doc)

class TypewiseIndexer:
    """An indexer that delegates the indexing to sub-indexers based on the docuemnt type.
    """
    def __init__(self):
        self.indexers = {}
        self.default_indexer = StoreIndexer()
        
    def set_indexer(self, type, indexer):
        """Installs indexer for the given type of documents.
        """
        self.indexers[type] = indexer

    def get_indexer(self, type):
        """Returns the indexer for the given type. The default indexer is returned when none available."""
        return self.indexers.get(type, self.default_indexer)
        
    def index(self, doc):
        """Delegates the call to the indexer installed for the doc type."""
        type = doc.get("type", "")
        return self.get_indexer(type).index(doc)
########NEW FILE########
__FILENAME__ = _json
r"""
Wrapper to simplejson to fix unicode/utf-8 issues in python 2.4.

See Bug#231831 for details.


    >>> loads(dumps(u'\u1234'))
    u'\u1234'
    >>> loads(dumps(u'\u1234'.encode('utf-8')))
    u'\u1234'
    >>> loads(dumps({'x': u'\u1234'.encode('utf-8')}))
    {u'x': u'\u1234'}
"""
import simplejson
import datetime

def unicodify(d):
    """Converts all utf-8 encoded strings to unicode recursively."""
    if isinstance(d, dict):
        return dict((k, unicodify(v)) for k, v in d.iteritems())
    elif isinstance(d, list):
        return [unicodify(x) for x in d]
    elif isinstance(d, str):
        return d.decode('utf-8')
    elif isinstance(d, datetime.datetime):
        return d.isoformat()
    else:
        return d
        
class JSONEncoder(simplejson.JSONEncoder):
    def default(self, o):
        if hasattr(o, '__json__'):
            return simplejson.loads(o.__json__())
        else:
            return simplejson.JSONEncoder.default(self, o)

def dumps(obj, **kw):
    """
        >>> class Foo:
        ...     def __json__(self): return 'foo'
        ...
        >>> a = [Foo(), Foo()]
        >>> dumps(a)
        '[foo, foo]'
    """
    return simplejson.dumps(unicodify(obj), cls=JSONEncoder, **kw)

def loads(s, **kw):
    return simplejson.loads(s, **kw)

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = code
"""
Infogami read/write API.
"""
import web
import infogami
from infogami.utils import delegate, features
from infogami.utils.view import safeint
from infogami.infobase import client
import simplejson

hooks = {}        
def add_hook(name, cls):
    hooks[name] = cls

class api(delegate.page):
    path = "/api/(.*)"
    
    def delegate(self, suffix):
        # Have an option of setting content-type to text/plain
        i = web.input(_method='GET', text="false")
        if i.text.lower() == "false":
            web.header('Content-type', 'application/json')
        else:
            web.header('Content-type', 'text/plain')

        if suffix in hooks:
            method = web.ctx.method
            cls = hooks[suffix]
            m = getattr(cls(), method, None)
            if m:
                raise web.HTTPError('200 OK', {}, m())
            else:
                web.ctx.status = '405 Method Not Allowed'
        else:
            web.ctx.status = '404 Not Found'
            
    GET = POST = delegate

def get_custom_headers():
    opt = web.ctx.env.get('HTTP_OPT')
    if opt is None:
        return {}
        
    import re
    rx = web.re_compile(r'"(.*)"; ns=(\d\d)')
    m = rx.match(opt.strip())
    
    if m:
        decl_uri, ns = m.groups()
        expected_decl_uri = infogami.config.get('http_ext_header_uri', 'http://infogami.org/api')
        if expected_decl_uri == decl_uri:
            prefix = 'HTTP_%s_' % ns
            return dict((web.lstrips(k, prefix).lower(), v) for k, v in web.ctx.env.items() if k.startswith(prefix))
    else:
        return {}

class infobase_request:
    def delegate(self):
        sitename = web.ctx.site.name
        path = web.lstrips(web.ctx.path, "/api")
        method = web.ctx.method
        data = web.input()
        
        conn = self.create_connection()
        
        try:
            out = conn.request(sitename, path, method, data)
            return '{"status": "ok", "result": %s}' % out
        except client.ClientException, e:
            return '{"status": "fail", "message": "%s"}' % str(e)
    
    GET = delegate
    
    def create_connection(self):
        conn = client.connect(**infogami.config.infobase_parameters)
        auth_token = web.cookies().get(infogami.config.login_cookie_name)
        conn.set_auth_token(auth_token)
        return conn
    
    def POST(self):
        """RESTful write API."""
        if not can_write():
            raise Forbidden("Permission Denied")
        
        sitename = web.ctx.site.name
        path = web.lstrips(web.ctx.path, "/api")
        method = "POST"
            
        query = web.data()
        h = get_custom_headers()
        comment = h.get('comment')
        action = h.get('action')
        data = dict(query=query, comment=comment, action=action)
        
        conn = self.create_connection()
        
        try:
            out = conn.request(sitename, path, method, data)
        except client.ClientException, e:
            raise BadRequest(e.json or str(e))
            
        #@@ this should be done in the connection.
        try:
            if path == "/save_many":
                for q in simplejson.loads(query):
                    web.ctx.site._run_hooks("on_new_version", q)
            elif path == "/write":
                result = simplejson.loads(out)
                for k in result.get('created', []) + result.get('updated', []):
                    web.ctx.site._run_hooks("on_new_version", request("/get", data=dict(key=k)))
        except Exception, e:
            import traceback
            traceback.print_exc()
        return out

# Earlier read API, for backward-compatability
add_hook("get", infobase_request)
add_hook("things", infobase_request)
add_hook("versions", infobase_request)
add_hook("get_many", infobase_request)

# RESTful write API.
add_hook("write", infobase_request)
add_hook("save_many", infobase_request)

def jsonapi(f):
    def g(*a, **kw):
        try:
            out = f(*a, **kw)
        except client.ClientException, e:
            raise web.HTTPError(e.status, {}, e.json or str(e))
        
        i = web.input(_method='GET', callback=None)
        
        if i.callback:
            out = '%s(%s);' % (i.callback, out)
            
        if web.input(_method="GET", text="false").text.lower() == "true":
            content_type = "text/plain"
        else:
            content_type = "application/json"
        
        return delegate.RawText(out, content_type=content_type)
    return g

def request(path, method='GET', data=None):
    return web.ctx.site._conn.request(web.ctx.site.name, path, method=method, data=data)
    
class Forbidden(web.HTTPError):
    def __init__(self, msg=""):
        web.HTTPError.__init__(self, "403 Forbidden", {}, msg)
            
class BadRequest(web.HTTPError):
    def __init__(self, msg=""):
        web.HTTPError.__init__(self, "400 Bad Request", {}, msg)
        
def can_write():
    user = delegate.context.user and delegate.context.user.key
    usergroup = web.ctx.site.get('/usergroup/api') or {}
    usergroup_admin = web.ctx.site.get('/usergroup/admin') or {}
    api_users = usergroup.get('members', []) + usergroup_admin.get('members', [])
    return user in [u.key for u in api_users]
    
class view(delegate.mode):
    encoding = "json"
    
    @jsonapi
    def GET(self, path):
        i = web.input(v=None)
        v = safeint(i.v, None)        
        data = dict(key=path, revision=v)
        return request('/get', data=data)
        
    @jsonapi
    def PUT(self, path):
        if not can_write():
            raise Forbidden("Permission Denied.")
            
        data = web.data()
        h = get_custom_headers()
        comment = h.get('comment')
        if comment:
            data = simplejson.loads(data)
            data['_comment'] = comment
            data = simplejson.dumps(data)
            
        result = request('/save' + path, 'POST', data)
        
        #@@ this should be done in the connection.
        web.ctx.site._run_hooks("on_new_version", data)
        return result
        
def make_query(i, required_keys=None):
    """Removes keys starting with _ and limits the keys to required_keys, if it is specified.
    
    >>> make_query(dict(a=1, _b=2))
    {'a': 1}
    >>> make_query(dict(a=1, _b=2, c=3), required_keys=['a'])
    {'a': 1}
    """
    query = {}
    for k, v in i.items():
        if k.startswith('_'):
            continue
        if required_keys and k not in required_keys:
            continue
        if v == '':
            v = None
        query[k] = v
    return query
        
class history(delegate.mode):
    encoding = "json"

    @jsonapi
    def GET(self, path):
        query = make_query(web.input(), required_keys=['author', 'ip', 'offset', 'limit'])
        query['key'] = path
        query['sort'] = '-created'
        return request('/versions', data=dict(query=simplejson.dumps(query)))
        
class recentchanges(delegate.page):
    encoding = "json"
    
    @jsonapi
    def GET(self):
        i = web.input(query=None)
        query = i.pop('query')
        if not query:
            query = simplejson.dumps(make_query(i, required_keys=["key", "type", "author", "ip", "offset", "limit", "bot"]))

        if features.is_enabled("recentchanges_v2"):
            return request('/_recentchanges', data=dict(query=query))
        else:
            return request('/versions', data=dict(query=query))

class query(delegate.page):
    encoding = "json"
    
    @jsonapi
    def GET(self):
        i = web.input(query=None)
        i.pop("callback", None)
        query = i.pop('query')
        if not query:
            query = simplejson.dumps(make_query(i))
        return request('/things', data=dict(query=query, details="true"))

class login(delegate.page):
    encoding = "json"
    path = "/account/login"
    
    def POST(self):
        try:
            d = simplejson.loads(web.data())
            web.ctx.site.login(d['username'], d['password'])
            web.setcookie(infogami.config.login_cookie_name, web.ctx.conn.get_auth_token())
        except Exception, e:
            raise BadRequest(str(e))

########NEW FILE########
__FILENAME__ = code
"""
i18n: allow keeping i18n strings in wiki
"""

import web

import infogami
from infogami import config
from infogami.utils import delegate, i18n
from infogami.utils.context import context
from infogami.utils.view import public
from infogami.utils.template import render
from infogami.infobase import client
import db

re_i18n = web.re_compile(r'^/i18n(/.*)?/strings\.([^/]*)$')

class hook(client.hook):
    def on_new_version(self, page):
        """Update i18n strings when a i18n wiki page is changed."""
        if page.type.key == '/type/i18n':
            data = page._getdata()            
            load(page.key, data)

def load_strings(site):
    """Load strings from wiki."""
    pages = db.get_all_strings(site)
    for page in pages:
        load(page.key, page._getdata())
            
def load(key, data):
    result = re_i18n.match(key)
    if result:
        namespace, lang = result.groups()
        namespace = namespace or '/'
        i18n.strings._set_strings(namespace, lang, unstringify(data))

def setup():
    delegate.fakeload()    
    from infogami.utils import types
    types.register_type('/i18n(/.*)?/strings.[^/]*', '/type/i18n')
    
    for site in db.get_all_sites():
        load_strings(site)
        
def stringify(d):
    """Prefix string_ for every key in a dictionary.
    
        >>> stringify({'a': 1, 'b': 2})
        {'string_a': 1, 'string_b': 2}
    """
    return dict([('string_' + k, v) for k, v in d.items()])
    
def unstringify(d):
    """Removes string_ prefix from every key in a dictionary.
    
        >>> unstringify({'string_a': 1, 'string_b': 2})
        {'a': 1, 'b': 2}    
    """
    return dict([(web.lstrips(k, 'string_'), v) for k, v in d.items() if k.startswith('string_')])

def pathjoin(a, *p):
    """Join two or more pathname components, inserting '/' as needed.
    
        >>> pathjoin('/i18n', '/type/type', 'strings.en')
        '/i18n/type/type/strings.en'
    """
    path = a
    for b in p:
        if b.startswith('/'):
            b = b[1:] # strip /
        if path == '' or path.endswith('/'):
            path +=  b
        else:
            path += '/' + b
    return path
    
@infogami.install_hook
@infogami.action
def movestrings():
    """Moves i18n strings to wiki."""
    query = []
    for (namespace, lang), d in i18n.strings._data.iteritems():
        q = stringify(d)
        q['create'] = 'unless_exists'
        q['key'] = pathjoin('/i18n', namespace, '/strings.' + lang)
        q['type'] = '/type/i18n'
        query.append(q)
    web.ctx.site.write(query)

setup()

########NEW FILE########
__FILENAME__ = db
import web
from infogami.infobase import client

def get_all_strings(site):
    t = site.get('/type/i18n')
    if t is None:
        return []
    else:
        q = {'type': '/type/i18n', 'limit': 1000}
        return site.get_many(site.things(q))

def get_all_sites():
    if web.ctx.site.exists():
        return [web.ctx.site]
    else:
        return []

########NEW FILE########
__FILENAME__ = code
"""
links: allow interwiki links

Adds a markdown preprocessor to catch `[[foo]]` style links.
Creates a new set of database tables to keep track of them.
Creates a new `m=backlinks` to display the results.
"""

import web

from infogami.core import db
from infogami.utils import delegate
from infogami.utils.template import render

import view

class backlinks (delegate.mode):
    def GET(self, site, path):
        #@@ fix later
        return []
        
        links = tdb.Things(type=db.get_type(site, 'type/page'), parent=site, links=path)
        return render.backlinks(links)


########NEW FILE########
__FILENAME__ = db
from infogami.core import db
from infogami import tdb

def get_links_type():
    linkstype = db.get_type('links') or db.new_type('links')
    linkstype.save()
    return linkstype
    
def new_links(page, links):
    # for links thing: parent=page, type=linkstype
    site = page.parent
    path = page.name
    d = {'site': site, 'path': path, 'links': list(links)}
    
    try:
        backlinks = tdb.withName("links", page)
        backlinks.setdata(d)
        backlinks.save()
    except tdb.NotFound:
        backlinks = tdb.new("links", page, get_links_type(), d)
        backlinks.save()

def get_links(site, path):
    return tdb.Things(type=get_links_type(), site=site, links=path)
########NEW FILE########
__FILENAME__ = view
from infogami.utils import view

import re
import web

def keyencode(value):
    return key.replace(' ', '_')

def get_links(text):
    """Returns all distinct links in the text."""
    doc = view.get_doc(text)
    def is_link(e):
        return e.type == 'element'      \
            and e.nodeName == 'a'       \
            and e.attribute_values.get('class', '') == 'internal'

    links = set()
    for a in doc.find(is_link):
        links.add(keyencode(a.attribute_values['href']))
    
    return links

link_re = web.re_compile(r'(?<!\\)\[\[(.*?)(?:\|(.*?))?\]\]')
class wikilinks:
    """markdown postprocessor for [[wikilink]] support."""
    def process_links(self, node):
        doc = node.doc
        text = node.value
        new_nodes = []
        position = [0]

        def mangle(match):
            start, end = position[0], match.start()
            position[0] = match.end()
            text_node = doc.createTextNode(text[start:end])

            matches = match.groups()
            link = matches[0]
            anchor = matches[1] or link
            #link = keyencode(link)

            link_node = doc.createElement('a')
            link_node.setAttribute('href', link)
            link_node.setAttribute('class', 'internal')
            link_node.appendChild(doc.createTextNode(anchor))

            new_nodes.append(text_node)
            new_nodes.append(link_node)

            return ''

        re.sub(link_re, mangle, text)

        start = position[0]
        end = len(text)
        text_node = doc.createTextNode(text[start:end])

        new_nodes.append(text_node)

        return new_nodes

    def replace_node(self, node, new_nodes):
        """Removes the node from its parent and inserts new_nodes at that position."""
        parent = node.parent
        position = parent.childNodes.index(node)
        parent.removeChild(node)

        for n in new_nodes:
            parent.insertChild(position, n)
            position += 1

    def run(self, doc):
        def test(e):
            return e.type == 'text' and link_re.search(e.value)

        for node in doc.find(test):
            new_nodes = self.process_links(node)
            self.replace_node(node, new_nodes)

view.register_wiki_processor(wikilinks())


########NEW FILE########
__FILENAME__ = code
"""
Plugin to move pages between wiki and disk.

This plugin provides 2 actions: push and pull.
push moves pages from disk to wiki and pull moves pages from wiki to disk.

TODOs:
* As of now pages are stored as python dict. Replace it with a human-readable format.
"""

import web
import os

import infogami
from infogami import tdb
from infogami.core import db
from infogami.utils import delegate
from infogami.utils.context import context

def listfiles(root, filter=None):
    """Returns an iterator over all the files in a directory recursively.
    If filter is specified only those files matching the filter are returned.
    Returned paths will be relative to root.
    """
    if not root.endswith(os.sep):
        root += os.sep
        
    for dirname, dirnames, filenames in os.walk(root):
        for f in filenames:
            path = os.path.join(dirname, f)
            path = path[len(root):]
            if filter is None or filter(path):
                yield path

def storify(d):
    """Recursively converts dict to web.storage object.
    
        >>> d = storify({'x: 1, y={'z': 2}})
        >>> d.x
        1
        >>> d.y.z
        2
    """
    if isinstance(d, dict):
        return web.storage([(k, storify(v)) for k, v in d.items()])
    elif isinstance(d, list):
        return [storify(x) for x in d]
    else:
        return d
            
def _readpages(root):
    """Reads and parses all root/*.page files and returns results as a dict."""
    def read(root, path):
        path = path or "__root__"    
        text = open(os.path.join(root, path + ".page")).read()
        d = eval(text)
        return storify(d)

    pages = {}
    for path in listfiles(root, filter=lambda path: path.endswith('.page')):
        path = path[:-len(".page")]
        if path == "__root__":
            name = ""
        else:
            name = path
        pages[name] = read(root, path)
    return pages

def _savepage(page, create_dependents=True, comment=None):
    """Saves a page from dict."""
    def getthing(name, create=False):
        if isinstance(name, tdb.Thing):
            return name
        try:
            return db.get_version(context.site, name)
        except:
            if create and create_dependents:
                thing = db.new_version(context.site, name, getthing("type/thing"), {})
                thing.save()
                return thing
            else:
                raise

    def thingify(data, getparent):
        """Converts data into thing or primitive value.
        """
        if isinstance(data, list):
            return [thingify(x, getparent) for x in data]
        elif isinstance(data, dict):
            name = data.name
            if data.get('child'):
                d = dict([(k, thingify(v, getparent)) for k, v in data.d.items()])
                type = thingify(data.type, getparent)
                thing = db.new_version(getparent(), name, type, d)
                thing.save()
                return thing
            else:
                return getthing(name, create=True)
        else:
            return data

    name = page.name
    type = getthing(page.type.name, create=True)
    d = {}
    
    getself = lambda: getthing(name, create=True)
    for k, v in page.d.items():
        d[k] = thingify(v, getself)
            
    _page = db.new_version(context.site, name, type, d)
    _page.save(author=context.user, comment=comment, ip=web.ctx.ip)
    return _page

def thing2dict(page):
    """Converts thing to dict.    
    """
    def simplify(x, page):
        if isinstance(x, tdb.Thing):
            # for type/property-like values
            if x.parent.id == page.id:
                t = thing2dict(x)
                t['child'] = True
                return t
            else:
                return dict(name=x.name)
        elif isinstance(x, list):
            return [simplify(a, page) for a in x]
        else:
            return x
            
    data = dict(name=page.name, type={'name': page.type.name})
    d = data['d'] = {}
    for k, v in page.d.iteritems():
        d[k] = simplify(v, page)
    return data

@infogami.action
def pull(root, paths_files):
    """Move specified pages from wiki to disk."""
    def write(path, data):
        dir = os.path.dirname(filepath)
        if not os.path.exists(dir):
            os.makedirs(dir)
        f = open(filepath, 'w')
        f.write(repr(data))
        f.close()

    pages = {}
    paths = [line.strip() for line in open(paths_files).readlines()]
    paths2 = []

    for path in paths:
        if path.endswith('/*'):
            path = path[:-2] # strip trailing /*
            paths2 += [p.name for p in db._list_pages(context.site, path)]
        else:
            paths2.append(path)

    for path in paths2:
        print >> web.debug, "pulling page", path
        page = db.get_version(context.site, path)
        name = page.name or '__root__'
        data = thing2dict(page)
        filepath = os.path.join(root, name + ".page") 
        write(filepath, data)

@infogami.action        
def push(root):
    """Move pages from disk to wiki."""
    pages = _readpages(root)
    _pushpages(pages)
    
def _pushpages(pages):
    tdb.transact()
    try:
        for p in pages.values(): 
            print 'saving', p.name
            _savepage(p)    
    except:
        tdb.rollback()
        raise
    else:
        tdb.commit()

@infogami.install_hook
@infogami.action
def moveallpages():
    """Move pages from all plugins."""
    pages = {}
    for plugin in delegate.plugins:
        path = os.path.join(plugin.path, 'pages')
        pages.update(_readpages(path))
    _pushpages(pages)
    
@infogami.action
def tdbdump(filename, created_after=None, created_before=None):
    """Creates tdb log of entire database."""
    from infogami.tdb import logger
    f = open(filename, 'w')
    logger.set_logfile(f)
    
    # get in chunks of 10000 to limit the load on db.
    N = 10000
    offset = 0
    while True:
        versions = tdb.Versions(offset=offset, limit=N, orderby='version.id', 
                        created_after=created_after, created_before=created_before).list()
        offset += N
        if not versions:
            break
            
        # fill the cache with things corresponding to the versions. 
        # otherwise, every thing must be queried separately.
        tdb.withIDs([v.thing_id for v in versions])            
        for v in versions:
            t = v.thing
            logger.transact()
            if v.revision == 1:
                logger.log('thing', t.id, name=t.name, parent_id=t.parent.id)
                
            logger.log('version', v.id, thing_id=t.id, author_id=v.author_id, ip=v.ip, 
                    comment=v.comment, revision=v.revision, created=v.created.isoformat())           
            logger.log('data', v.id, __type__=t.type, **t.d)
            logger.commit()
    f.close()

@infogami.action
def datadump(filename):
    """Writes dump of latest versions of all pages in the system.
    User info is excluded.
    """
    def dump(predicate=None):
        things = {}
        # get in chunks of 10000 to limit the load on db.
        N = 10000
        offset = 0

        while True:
            things = tdb.Things(parent=context.site, offset=offset, limit=N, orderby='thing.id')
            offset += N
            if not things:
                break
            for t in things:
                if predicate and not predicate(t):
                    continue
                data = thing2dict(t)
                f.write(str(data))
                f.write('\n')
    
    f = open(filename, 'w')
    # dump the everything except users
    dump(lambda t: t.type.name != 'type/user')
    f.close()
    
@infogami.action
def dataload(filename):
    """"Loads data dumped using datadump action into the database."""
    lines = open(filename).xreadlines()
    tdb.transact()
    try:
        for line in lines:
            data = storify(eval(line))
            _savepage(data)
    except:
        tdb.rollback()
        raise
    else:
        tdb.commit()

########NEW FILE########
__FILENAME__ = code
"""
review: allow user reviews

Creates a new set of database tables to keep track of user reviews.
Creates '/changes' page for displaying modifications since last review.
"""

from infogami.utils import delegate, view
from infogami.utils.template import render
from infogami import core
from infogami.core.auth import require_login

import db
import web

class changes (delegate.page):
    @require_login
    def GET(self, site):
        user = core.auth.get_user()
        d = db.get_modified_pages(site, user.id)
        return render.changes(web.ctx.homepath, d)

def input():
	i = web.input("a", "b", "c")
	i.a = (i.a and int(i.a) or 0)
	i.b = int(i.b)
	i.c = int(i.c)
	return i

class review (delegate.mode):
    @require_login
    def GET(self, site, path):
        user = core.auth.get_user()
        i = input()

        if i.a == 0:
            alines = []
            xa = web.storage(created="", revision=0)
        else:
            xa = core.db.get_version(site, path, revision=i.a)
            alines = xa.data.body.splitlines()

        xb = core.db.get_version(site, path, revision=i.b)
        blines = xb.data.body.splitlines()
        map = core.diff.better_diff(alines, blines)

        view.add_stylesheet('core', 'diff.css')
        diff = render.diff(map, xa, xb)
        
        return render.review(path, diff, i.a, i.b, i.c)
        
class approve (delegate.mode):
    @require_login
    def POST(self, site, path):
        i = input()

        if i.c != core.db.get_version(site, path).revision:
            return render.parallel_modification()

        user = core.auth.get_user()

        if i.b != i.c: # user requested for some reverts before approving this
            db.revert(site, path, user.id, i.b)
            revision = i.c + 1 # one new version has been added by revert
        else:
            revision = i.b

        db.approve(site, user.id, path, revision)
        web.seeother(web.changequery(m=None, a=None, b=None, c=None))

class revert (delegate.mode):
    @require_login
    def POST(self, site, path):
        i = input()

        if i.c != core.db.get_version(site, path).revision:
            return render.parallel_modification()
   
        if i.a == i.b:
	        return approve().POST(site, path)
        else:
            web.seeother(web.changequery(m='review', b=i.b-1))

########NEW FILE########
__FILENAME__ = db
from infogami import core
import web

class SQL:
    def get_modified_pages(self, url, user_id):
        site_id = core.db.get_site_id(url)

        #@@ improve later
        d = web.query("""
            SELECT 
                page.id as id,
                page.path as path,
                MAX(version.revision) as revision, 
                MAX(review.revision) as reviewed_revision
            FROM page
            JOIN version ON page.id = version.page_id
            LEFT OUTER JOIN review 
                ON page.id = review.page_id
                AND review.user_id=$user_id
            GROUP BY page.id, page.path
            """, vars=locals())

        d = [p for p in d if not p.reviewed_revision or p.revision > p.reviewed_revision]
        return d

    def approve(self, url, user_id, path, revision):
        site_id = core.db.get_site_id(url)
        page_id = core.db.get_page_id(url, path)

        #@@ is there any better way?
        web.transact()
        try:
            web.delete('review', where="site_id=$site_id AND page_id=$page_id AND user_id=$user_id", vars=locals())
            web.insert('review', site_id=site_id, page_id=page_id, user_id=user_id, revision=revision)
        except:
            web.rollback()
            raise
        else:
            web.commit()

    def revert(self, url, path, author_id, revision):
	    """Reverts a page to an older version."""
	    data = core.db.get_version(url, path, revision).data
	    core.db.new_version(url, path, author_id, data)

from infogami.utils.delegate import pickdb
pickdb(globals())

########NEW FILE########
__FILENAME__ = view
import re
import web
from utils import view

#Anand: fix later
from utils.delegate import _keyencode as keyencode

def get_links(text):
    """Returns all distinct links in the text."""
    doc = view.get_doc(text)
    def is_link(e):
        return e.type == 'element'      \
            and e.nodeName == 'a'       \
            and e.attribute_values.get('class', '') == 'internal'

    links = set()
    for a in doc.find(is_link):
        links.add(keyencode(a.attribute_values['href']))
    
    return links

link_re = web.re_compile(r'(?<!\\)\[\[(.*?)(?:\|(.*?))?\]\]')
class wikilinks:
    """markdown postprocessor for [[wikilink]] support."""
    def process_links(self, node):
        doc = node.doc
        text = node.value
        new_nodes = []
        position = [0]

        def mangle(match):
            start, end = position[0], match.start()
            position[0] = match.end()
            text_node = doc.createTextNode(text[start:end])

            matches = match.groups()
            link = matches[0]
            anchor = matches[1] or link
            #link = keyencode(link)

            link_node = doc.createElement('a')
            link_node.setAttribute('href', link)
            link_node.setAttribute('class', 'internal')
            link_node.appendChild(doc.createTextNode(anchor))

            new_nodes.append(text_node)
            new_nodes.append(link_node)

            return ''

        re.sub(link_re, mangle, text)

        start = position[0]
        end = len(text)
        text_node = doc.createTextNode(text[start:end])

        new_nodes.append(text_node)

        return new_nodes

    def replace_node(self, node, new_nodes):
        """Removes the node from its parent and inserts new_nodes at that position."""
        parent = node.parent
        position = parent.childNodes.index(node)
        parent.removeChild(node)

        for n in new_nodes:
            parent.insertChild(position, n)
            position += 1

    def run(self, doc):
        def test(e):
            return e.type == 'text' and link_re.search(e.value)

        for node in doc.find(test):
            new_nodes = self.process_links(node)
            self.replace_node(node, new_nodes)

view.register_wiki_processor(wikilinks())

########NEW FILE########
__FILENAME__ = code
"""
wikitemplates: allow keeping templates and macros in wiki
"""

import web
import os
from UserDict import DictMixin

import infogami
from infogami import core, config
from infogami.core.db import ValidationException
from infogami.utils import delegate, macro, template, storage, view
from infogami.utils.context import context
from infogami.utils.template import render
from infogami.utils.view import require_login

from infogami.infobase import client

import db

LazyTemplate = template.LazyTemplate

class WikiSource(DictMixin):
    """Template source for templates in the wiki"""
    def __init__(self, templates):
        self.templates = templates
        
    def getroot(self):
        return config.get("default_template_root", "/")
        
    def __getitem__(self, key):
        key = self.process_key(key)
        root = self.getroot()
        if root is None or context.get('rescue_mode'):
            raise KeyError, key
        
        root = web.rstrips(root or "", "/")
        value = self.templates[root + key]    
        if isinstance(value, LazyTemplate):
            value = value.func()
                    
        return value
        
    def keys(self):
        return [self.unprocess_key(k) for k in self.templates.keys()]
        
    def process_key(self, key):
        return '/templates/%s.tmpl' % key
            
    def unprocess_key(self, key):
        key = web.lstrips(key, '/templates/')
        key = web.rstrips(key, '.tmpl')
        return key
    
class MacroSource(WikiSource):
    def process_key(self, key):
        # macro foo is availble at path macros/foo
        return '/macros/' + key
        
    def unprocess_key(self, key):
        return web.lstrips(key, '/macros/')

def get_user_preferences():
    #@ quick hack to avoid querying for user_preferences again and again
    if 'user_preferences' not in web.ctx:
        web.ctx.user_preferences = context.get('user') and web.ctx.site.get(context.user.key + "/preferences")
    return web.ctx.user_preferences

def get_user_root():
    i = web.input(_method='GET')
    if 'template_root' in i:
        return i.template_root.strip()
    preferences = get_user_preferences()
    return preferences and preferences.get("template_root", None)
    
class UserSource(WikiSource):
    """Template source for user templates."""
    def getroot(self):
        return get_user_root()

class UserMacroSource(MacroSource):
    """Template source for user macros."""
    def getroot(self):
        return get_user_root()

wikitemplates = storage.SiteLocalDict()
template.render.add_source(WikiSource(wikitemplates))
template.render.add_source(UserSource(wikitemplates))

wikimacros = storage.SiteLocalDict()
macro.macrostore.add_dict(MacroSource(wikimacros))
macro.macrostore.add_dict(UserMacroSource(wikimacros))

class hooks(client.hook):
    def on_new_version(self, page):
        """Updates the template/macro cache, when a new version is saved or deleted."""
        if page.type.key == '/type/template':
            _load_template(page)            
        elif page.type.key == '/type/macro':
            _load_macro(page)
        elif page.type.key == '/type/delete':
            if page.name in wikitemplates:
                del wikitemplates[page.key]
            if page.name in wikimacros:
                del wikimacros[page.key]
    
    def before_new_version(self, page):
        """Validates template/macro, before it is saved, by compiling it."""
        if page.type.key == '/type/template':
            _compile_template(page.key, page.body)
        elif page.type.key == '/type/macro':
            _compile_template(page.key, page.macro)
            
            
def _stringify(value):
    if isinstance(value, dict):
        return value['value']
    else:
        return value

def _compile_template(name, text):
    text = web.utf8(_stringify(text))
            
    try:
        return web.template.Template(text, filter=web.websafe, filename=name)
    except (web.template.ParseError, SyntaxError), e:
        print >> web.debug, 'Template parsing failed for ', name
        import traceback
        traceback.print_exc()
        raise ValidationException("Template parsing failed: " + str(e))

def _load_template(page, lazy=False):
    """load template from a wiki page."""
    if lazy:
        page = web.storage(key=page.key, body=web.utf8(_stringify(page.body)))
        wikitemplates[page.key] = LazyTemplate(lambda: _load_template(page))
    else:
        wikitemplates[page.key] = _compile_template(page.key, page.body)
    
def _load_macro(page, lazy=False):
    if lazy:
        page = web.storage(key=page.key, macro=web.utf8(_stringify(page.macro)), description=page.description or "")
        wikimacros[page.key] = LazyTemplate(lambda: _load_macro(page))
    else:
        t = _compile_template(page.key, page.macro)
        t.__doc__ = page.description or ''
        wikimacros[page.key] = t
        
def load_all():
    def load_macros(site): 
        for m in db.get_all_macros(site):
            _load_macro(m, lazy=True)
    
    def load_templates(site):
        for t in db.get_all_templates(site):
            _load_template(t, lazy=True)
    
    for site in db.get_all_sites():
        context.site = site
        load_macros(site)
        load_templates(site)
    
def setup():
    delegate.fakeload()
    
    load_all()
    
    from infogami.utils import types
    types.register_type('/templates/.*\.tmpl$', '/type/template')
    types.register_type('^/type/[^/]*$', '/type/type')
    types.register_type('/macros/.*$', '/type/macro')
    
def reload():
    """Reload all templates and macros."""
    load_all()
    
@infogami.install_hook
@infogami.action
def movetemplates(prefix_pattern=None):
    """Move templates to wiki."""
    def get_title(name):
        if name.startswith('/type/'):
            type, name = name.rsplit('/', 1)
            title = '%s template for %s' % (name, type)
        else:
            title = '%s template' % (name)
        return title
    
    templates = []

    for name, t in template.disktemplates.items():
        if isinstance(t, LazyTemplate):
            try:
                t.func()
            except:
                print >> web.debug, 'unable to load template', t.name
                raise
    
    for name, t in template.disktemplates.items():
        prefix = '/templates/'
        wikipath = _wikiname(name, prefix, '.tmpl')
        if prefix_pattern is None or wikipath.startswith(prefix_pattern):
            title = get_title(name)
            body = open(t.filepath).read()
            d = web.storage(create='unless_exists', key=wikipath, type={"key": '/type/template'}, title=title, body=dict(connect='update', value=body))
            templates.append(d)
            
    delegate.admin_login()
    result = web.ctx.site.write(templates)
    for p in result.created:
        print "created", p
    for p in result.updated:
        print "updated", p
        
@infogami.install_hook
@infogami.action
def movemacros():
    """Move macros to wiki."""
    macros = []

    for name, t in macro.diskmacros.items():
        if isinstance(t, LazyTemplate):
            t.func()
    
    for name, m in macro.diskmacros.items():
        key = _wikiname(name, '/macros/', '')
        body = open(m.filepath).read()
        d = web.storage(create='unless_exists', key=key, type={'key': '/type/macro'}, description='', macro=body)
        macros.append(d)
    delegate.admin_login()
    result = web.ctx.site.write(macros)
    for p in result.created:
        print "created", p
    for p in result.updated:
        print "updated", p

def _wikiname(name, prefix, suffix):
    base, extn = os.path.splitext(name)
    return prefix + base + suffix
        
def _new_version(name, typename, d):
    from infogami.core import db
    type = db.get_type(context.site, typename)
    db.new_version(context.site, name, type, d).save()

class template_preferences(delegate.page):
    """Preferences to choose template root."""
    path = "/account/preferences/template_preferences"
    title = "Change Template Root"
    
    @require_login
    def GET(self):
        import forms
        prefs = web.ctx.site.get(context.user.key + "/preferences")
        path = (prefs and prefs.get('template_root')) or "/"
        f = forms.template_preferences()
        f.fill(dict(path=path))
        return render.template_preferences(f)

    @require_login
    def POST(self):
        i = web.input()
        q = {
            "create": "unless_exists",
            "type": "/type/object",
            "key": context.user.key + "/preferences",
            "template_root": {
                "connect": "update",
                "value": i.path
            }
        }
        web.ctx.site.write(q)
        raise web.seeother('/account/preferences')
        
def monkey_patch_debugerror():
    """Monkey patch web.debug error to display template code."""
    def xopen(filename):
        if filename.endswith('.tmpl') or filename.startswith('/macros/'):
            page = web.ctx.site.get(filename)
            if page is None:
                raise IOError("not found: " + filename)
            from StringIO import StringIO
            return StringIO(page.body + "\n" * 100)
        else:
            return open(filename)
            
    web.debugerror.func_globals['open'] = xopen

from infogami.core.code import register_preferences
register_preferences(template_preferences)

# load templates and macros from all sites.
setup()

monkey_patch_debugerror()

########NEW FILE########
__FILENAME__ = db
import web

def get_all_templates(site):
    t = site.get('/type/template')
    if t is None:
        return []
    q = {'type': '/type/template', 'limit': 1000}
    #return [site.get(key) for key in site.things(q)]
    return site.get_many([key for key in site.things(q)])

def get_all_macros(site):
    t = site.get('/type/macro')
    if t is None:
        return []
    q = {'type': '/type/macro', 'limit': 1000}
    #return [site.get(key) for key in site.things(q)]
    return site.get_many([key for key in site.things(q)])
    
def get_all_sites():
    if web.ctx.site.exists():
        return [web.ctx.site]
    else:
        return []

########NEW FILE########
__FILENAME__ = forms
import web
from web.form import *
from infogami.utils import i18n

class BetterButton(Button):
    def render(self):
        label = self.attrs.get('label', self.name)
        safename = net.websafe(self.name)
        x = '<button name="%s"%s>%s</button>' % (safename, self.addatts(), label)
        return x
    
_ = i18n.strings.get_namespace('/account/preferences')
    
template_preferences = Form(
    Textbox("path", description=_.template_root),
    BetterButton('save', label=_.save)
)

if __name__ == "__main__":
    print template_preferences().render()
########NEW FILE########
__FILENAME__ = app

"""Infogami application.
"""
import web
import os
import re

import flash

urls = ("/.*", "item")
app = web.application(urls, globals(), autoreload=False)

# magical metaclasses for registering special paths and modes.
# Whenever any class extends from page/mode, an entry is added to pages/modes.
modes = {}
pages = {}

encodings = set()
media_types = {"application/json": "json"}

class metapage(type):
    def __init__(self, *a, **kw):
        type.__init__(self, *a, **kw)
        
        enc = getattr(self, 'encoding', None)        
        path = getattr(self, 'path', '/' + self.__name__)
        
        encodings.add(enc)
        pages.setdefault(path, {})
        pages[path][enc] = self

class metamode (type):
    def __init__(self, *a, **kw):
        type.__init__(self, *a, **kw)

        enc = getattr(self, 'encoding', None)        
        name = getattr(self, 'name', self.__name__)
        
        encodings.add(enc)
        modes.setdefault(name, {})
        modes[name][enc] = self

class mode:
    __metaclass__ = metamode
    
    def HEAD(self, *a):
        return self.GET(*a)
        
    def GET(self, *a):
        return web.nomethod(web.ctx.method)        

class page:
    __metaclass__ = metapage

    def HEAD(self, *a):
        return self.GET(*a)
        
    def GET(self, *a):
        return web.nomethod(web.ctx.method)
        
def find_page():
    path = web.ctx.path
    encoding = web.ctx.get('encoding')
    
    # I don't about this mode.
    if encoding not in encodings:
        raise web.HTTPError("406 Not Acceptable", {})

    # encoding can be specified as part of path, strip the encoding part of path.
    if encoding:
        path = web.rstrips(path, "." + encoding)
        
    def sort_paths(paths):
        """Sort path such that wildcards go at the end."""
        return sorted(paths, key=lambda path: ('.*' in path, path))
        
    for p in sort_paths(pages):
        m = re.match('^' + p + '$', path)
        if m:
            cls = pages[p].get(encoding) or pages[p].get(None)
            args = m.groups()
            
            # FeatureFlags support. 
            # A handler can be enabled only if a feature is active.
            if hasattr(cls, "is_enabled") and bool(cls().is_enabled()) is False:
               continue 
                
            return cls, args
    return None, None

def find_mode():
    what = web.input(_method='GET').get('m', 'view')
    
    path = web.ctx.path
    encoding = web.ctx.get('encoding')
    
    # I don't about this mode.
    if encoding not in encodings:
        raise web.HTTPError("406 Not Acceptable", {})
    
    # encoding can be specified as part of path, strip the encoding part of path.
    if encoding:
        path = web.rstrips(path, "." + encoding)
        
    if what in modes:
        cls = modes[what].get(encoding)
        
        # mode is available, but not for the requested encoding
        if cls is None:
            raise web.HTTPError("406 Not Acceptable", {})
            
        args = [path]
        return cls, args
    else:
        return None, None

# mode and page are just base classes.
del modes['mode']
del pages['/page']

class item:
    HEAD = GET = POST = PUT = DELETE = lambda self: delegate()

def delegate():
    """Delegate the request to appropriate class."""
    path = web.ctx.path
    method = web.ctx.method

    # look for special pages
    cls, args = find_page()
    if cls is None:
        cls, args = find_mode()
        
    if cls is None:
        raise web.seeother(web.changequery(m=None))
    elif not hasattr(cls, method):
        raise web.nomethod(method)
    else:
        return getattr(cls(), method)(*args)

##  processors

def normpath(path):
    """Normalized path.
    
        >>> normpath("/a b")
        '/a_b'
        >>> normpath("/a//b")
        '/a/b'
        >>> normpath("//a/b/")
        '/a/b'
    """
    try:
        # take care of bad unicode values in urls
        path.encode('utf-8')
    except UnicodeEncodeError:
        return '/'
        
    # path is taken as empty by web.py dev server when given path starts with //
    if path == '':
        return '/'
        
    # correct trailing / and ..s in the path
    path = os.path.normpath(path)
    # os.path.normpath doesn't remove double/triple /'s at the begining    
    path = path.replace("///", "/").replace("//", "/")
    path = path.replace(' ', '_') # replace space with underscore
    path = path.replace('\n', '_').replace('\r', '_')
    return path
    
def path_processor(handler):
    """Processor to make sure path is normalized."""
    npath = normpath(web.ctx.path)
    if npath != web.ctx.path:
        if web.ctx.method in ['GET' or 'HEAD']:
            # give absolute url for redirect. There is a bug in web.py 
            # that causes infinite redicts when web.ctx.path startswith "//" 
            raise web.seeother(web.ctx.home + npath + web.ctx.query)
        else:
            raise web.notfound()
    else:
        return handler()

# setup load and unload hooks for legacy code
web._loadhooks = {}
web.unloadhooks = {}
web.load = lambda: None

def hook_processor(handler):
    for h in web._loadhooks.values():
        h()
    try:
        return handler()
    finally:
        for h in web.unloadhooks.values():
            h()
            
def parse_accept(header):
    """Parses Accept: header.
    
        >>> parse_accept("text/plain; q=0.5, text/html")
        [{'media_type': 'text/html'}, {'q': 0.5, 'media_type': 'text/plain'}]
    """
    result= []
    for media_range in header.split(','):
        parts = media_range.split(';')
        media_type = parts.pop(0).strip()
        d = {'media_type': media_type}
        for part in parts:
            try:
                k, v = part.split('=')
                d[k.strip()] = v.strip()
            except (IndexError, ValueError):
                pass

        try:
            if 'q' in d:
                d['q'] = float(d['q'])
        except ValueError:
            del d['q']

        result.append(d)
    result.sort(key=lambda m: m.get('q', 1.0), reverse=True)
    return result
            
def find_encoding():
    def find_from_extension():
        for enc in encodings:
            if enc is None: continue
            if web.ctx.path.endswith('.' + enc):
                return enc
                
    if web.ctx.method == 'GET':
        if 'HTTP_ACCEPT' in web.ctx.environ:
            accept = parse_accept(web.ctx.environ['HTTP_ACCEPT'])
            media_type = accept[0]['media_type']
        else:
            media_type = None

        if media_type in media_types:
            return media_types[media_type]
        else:
            return find_from_extension()
    else:
        content_type = web.ctx.env.get('CONTENT_TYPE')
        return media_types.get(content_type) or find_from_extension()

def encoding_processor(handler):
    web.ctx.encoding = find_encoding()
    return handler()

app.add_processor(hook_processor)
app.add_processor(path_processor)
app.add_processor(encoding_processor)
app.add_processor(flash.flash_processor)

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = context
"""
Threaded context for infogami.
"""
import web

class InfogamiContext(web.ThreadedDict):
    """
    Threaded context for infogami.
    Uses web.ctx for providing a thread-specific context for infogami.
    """
    def load(self):
        pass
    '''
    def __getattr__(self, key):
        return getattr(web.ctx.infogami_ctx, key)

    def __setattr__(self, key, value):
        setattr(web.ctx.infogami_ctx, key, value)
    
    def load(self):
        """Initializes context for the calling thread."""
        web.ctx.infogami_ctx = web.storage()
    '''
    
context = InfogamiContext()

########NEW FILE########
__FILENAME__ = delegate
import os.path
import re
import web
from infogami import config

import template
import macro
from context import context
import features

from app import *

import view
import i18n

def create_site():
    from infogami.infobase import client
    
    if config.site is None:
        site = web.ctx.host.split(':')[0] # strip port
    else:
        site = config.site
    
    web.ctx.conn = client.connect(**config.infobase_parameters)
    
    # set auto token in the connection
    if web.ctx.get('env'): # do this only if web.load is already called
        auth_token = web.cookies().get(config.login_cookie_name)
        web.ctx.conn.set_auth_token(auth_token)
    
    return client.Site(web.ctx.conn, site)

def fakeload():
    from infogami.core import db
    #web.load()
    app.load(dict(REQUEST_METHOD="GET", PATH_INFO="/install"))
    web.ctx.ip = None
    context.load()
    context.error = None
    context.stylesheets = []
    context.javascripts = []
    context.site = config.site
    context.path = '/'
    
    # hack to disable permissions
    web.ctx.disable_permisson_check = True
    
    context.user = None
    web.ctx.site = create_site()

def initialize_context():
    web.ctx.site = create_site()
    context.load()
    context.error = None
    context.stylesheets = []
    context.javascripts = []
    context.user = web.ctx.site.get_user()
    context.site = config.site
    context.path = web.ctx.path
    
    i = web.input(_method='GET', rescue="false")
    context.rescue_mode = (i.rescue.lower() == 'true')
        
def layout_processor(handler):
    """Processor to wrap the output in site template."""
    out = handler()
    
    path = web.ctx.path[1:]
    
    if out is None:
        out = RawText("")
    
    if isinstance(out, basestring):
        out = web.template.TemplateResult(__body__=out)
     
    if 'title' not in out:
        out.title = path

    # overwrite the content_type of content_type is specified in the template
    if 'content_type' in out:
        web.ctx.headers = [h for h in web.ctx.headers if h[0].lower() != 'content-type']
        web.header('Content-Type', out.content_type)
        
    if hasattr(out, 'rawtext'):
        html = out.rawtext
    else:
        html = view.render_site(config.site, out)
        
    # cleanup references to avoid memory leaks
    web.ctx.site._cache.clear()
    web.ctx.pop('site', None)
    web.ctx.env = {}
    context.clear()

    return html

app.add_processor(web.loadhook(initialize_context))
app.add_processor(layout_processor)
app.add_processor(web.loadhook(features.loadhook))

class RawText(web.storage):
    def __init__(self, text, **kw):
        web.storage.__init__(self, rawtext=text, **kw)

plugins = []
@view.public
def get_plugins():
    """Return names of all the plugins."""
    return [p.name for p in plugins]

def _make_plugin(name):
    # plugin can be present in infogami/plugins directory or <pwd>/plugins directory.    
    if name == 'core':
        path = infogami_root() + '/core'
        module = 'infogami.core'
    else:
        for p in config.plugin_path:
            if p:
                m = __import__(p, globals(), locals(), ['plugins'])
                path = os.path.dirname(m.__file__) + '/' + name
                module = p + '.' + name
            else:
                path = name
                module = name
            if os.path.isdir(path):
                break
        else:
            raise Exception, 'Plugin not found: ' + name
            
    return web.storage(name=name, path=path, module=module)

def _list_plugins(dir):
    if os.path.isdir(dir):
        return [_make_plugin(name) for name in os.listdir(dir) if os.path.isdir(dir + '/' + name)]
    else:
        return []
    
def infogami_root():
    import infogami
    return os.path.dirname(infogami.__file__)
        
def _load():
    """Imports the files from the plugins directories and loads templates."""
    global plugins
    
    plugins = [_make_plugin('core')]
    
    if config.plugins is not None:
        plugins += [_make_plugin(p) for p in config.plugins]
    else:        
        for p in config.plugin_path:
            m = __import__(p)
            root = os.path.dirname(m)
            plugins += _list_plugins(root)
            
    for plugin in plugins:
        template.load_templates(plugin.path, lazy=True)
        macro.load_macros(plugin.path, lazy=True)
        i18n.load_strings(plugin.path)
        __import__(plugin.module + '.code', globals(), locals(), ['plugins'])
        
    features.set_feature_flags(config.get("features", {}))

def admin_login(site=None):
    site = site or web.ctx.site
    web.ctx.admin_mode = True
    web.ctx.ip = '127.0.0.1'
    web.ctx.site.login('admin', config.admin_password)

exception_hooks = []
def add_exception_hook(hook):
    exception_hooks.append(hook)

def register_exception():
    """Called to on exceptions to log exception or send exception mail."""
    for h in exception_hooks:
        h()
        
def email_excetpions():
    if config.bugfixer:
        web.emailerrors(config.bugfixer, lambda: None)()
add_exception_hook(email_excetpions)

########NEW FILE########
__FILENAME__ = features
"""Feature flags support for Infogami.
"""
import web

from context import context

feature_flags = {}

def set_feature_flags(flags):
    global feature_flags
    
    # sanity check
    if isinstance(flags, dict):
        feature_flags = flags

filters = {}
def register_filter(name, method):
    filters[name] = method
    
def call_filter(spec):
    if isinstance(spec, list):
        return any(call_filter(x) for x in spec)
    elif isinstance(spec, dict):
        spec = spec.copy()
        filter_name = spec.pop('filter', None)
        kwargs = spec
    else:
        filter_name = spec
        kwargs = {}
        
    if filter_name in filters:
        return filters[filter_name](**kwargs)
    else:
        return False
    
def find_enabled_features():
    return set(f for f, spec in feature_flags.iteritems() if call_filter(spec))
    
def loadhook():
    features = find_enabled_features()
    web.ctx.features = features
    context.features = features
    
def is_enabled(flag):
    """Tests whether the given feature flag is enabled for this request.
    """
    return flag in web.ctx.features

def filter_disabled():
    return False

def filter_enabled():
    return True
    
def filter_loggedin():
    return context.user is not None
    
def filter_admin():
    return filter_usergroup("/usergroup/admin")
    
def filter_usergroup(usergroup):
    """Returns true if the current user is member of the given usergroup."""
    def get_members():
        return [m.key for m in web.ctx.site.get(usergroup).members]
    
    return context.user and context.user.key in get_members()
    
def filter_queryparam(name, value):
    """Returns true if the current request has a queryparam with given name and value."""
    i = web.input(_method="GET")
    return i.get(name) == value
    
register_filter("disabled", filter_disabled)
register_filter("enabled", filter_enabled)
register_filter("admin", filter_admin)
register_filter("loggedin", filter_loggedin)
register_filter("usergroup", filter_usergroup)
register_filter("queryparam", filter_queryparam)

########NEW FILE########
__FILENAME__ = flash
"""Utility to display flash messages.

To add a flash message:

    add_flash_message('info', 'Login successful!')

To display flash messages in a template:
    
    $ for flash in get_flash_messages():
        <div class="$flash.type">$flash.message</div>
"""

import simplejson
import web

def get_flash_messages():
    flash = web.ctx.get('flash', [])
    web.ctx.flash = []
    return flash

def add_flash_message(type, message):
    flash = web.ctx.setdefault('flash', [])
    flash.append(web.storage(type=type, message=message))
    
def flash_processor(handler):
    flash = web.cookies(flash="[]").flash
    try:
        flash = [web.storage(d) for d in simplejson.loads(flash) if isinstance(d, dict) and 'type' in d and 'message' in d]
    except ValueError:
        flash = []
    
    web.ctx.flash = list(flash)
    
    try:
        return handler()
    finally:
        # Flash changed. Need to save it.
        if flash != web.ctx.flash:
            if web.ctx.flash:
                web.setcookie('flash', simplejson.dumps(web.ctx.flash))
            else:
                web.setcookie('flash', '', expires=-1)

########NEW FILE########
__FILENAME__ = i18n
"""
Support for Internationalization.
"""

import web

DEFAULT_LANG = 'en'

def find_i18n_namespace(path):
    """Finds i18n namespace from the path.
    
        >>> find_i18n_namespace('/i18n/type/type/strings.en')
        '/type/type'
        >>> find_i18n_namespace('/i18n/strings.en')
        '/'
    """
    import os.path
    return os.path.dirname(web.lstrips(path, '/i18n'))

class i18n:
    def __init__(self):
        self._data = {}
        
    def get_locale(self):
        return web.ctx.lang
        
    def get_namespaces(self):
        return sorted(set(k[0] for k in self._data))
        
    def get_languages(self):
        return sorted(set(k[1] for k in self._data))
    
    def get_count(self, namespace, lang=None):
        lang = lang or DEFAULT_LANG
        return len(self._data.get((namespace, lang)) or {})
                
    def get_namespace(self, namespace):
        return i18n_namespace(self, namespace)
        
    def getkeys(self, namespace, lang=None):
        namespace = web.utf8(namespace)
        lang = web.utf8(lang)
        
        # making a simplified assumption here.
        # Keys for a language are all the strings defined for that language and 
        # all the strings defined for default language. By doing this, once a key is 
        # added to default lang, then it will automatically appear in all other languages.
        keys = set(self._data.get((namespace, lang), {}).keys() + self._data.get((namespace, DEFAULT_LANG), {}).keys())
        return sorted(keys)
        
    def _set_strings(self, namespace, lang, data):
        namespace = web.utf8(namespace)
        lang = web.utf8(lang)
        self._data[namespace, lang] = dict(data)
        
    def _update_strings(self, namespace, lang, data):
        namespace = web.utf8(namespace)
        lang = web.utf8(lang)
        self._data.setdefault((namespace, lang), {}).update(data)
        
    def get(self, namespace, key):
        namespace = web.utf8(namespace)
        key = web.utf8(key)
        return i18n_string(self, namespace, key)
        
    def __getattr__(self, key):
        if not key.startswith('__'):
            return self[key]
        else:
            raise AttributeError, key
            
    def __getitem__(self, key):
        namespace = web.ctx.get('i18n_namespace', '/')
        key = web.utf8(key)
        return i18n_string(self, namespace, key)
        
class i18n_namespace:
    def __init__(self, i18n, namespace):
        self._i18n = i18n
        self._namespace = namespace
        
    def __getattr__(self, key):
        if not key.startswith('__'):
            return self[key]
        else:
            raise AttributeError, key
            
    def __getitem__(self, key):
        return self._i18n.get(self._namespace, key)
            
class i18n_string:
    def __init__(self, i18n, namespace, key):
        self._i18n = i18n
        self._namespace = namespace
        self._key = key
        
    def __str__(self):
        def get(lang): 
            return self._i18n._data.get((self._namespace, lang))
        default_data = get(DEFAULT_LANG) or {}
        data = get(web.ctx.lang) or default_data
        text = data.get(self._key) or default_data.get(self._key) or self._key
        return web.utf8(text)
    
    def __call__(self, *a):
        try:
            a = [x or "" for x in a]
            return str(self) % tuple(web.utf8(x) for x in a)
        except:
            print >> web.debug, 'failed to substitute (%s/%s) in language %s' % (self._namespace, self._key, web.ctx.lang)
        return str(self)

def i18n_loadhook():
    """Load hook to set web.ctx.lang bases on HTTP_ACCEPT_LANGUAGE header."""
    def parse_lang_header():
        """Parses HTTP_ACCEPT_LANGUAGE header."""
        accept_language = web.ctx.get('env', {}).get('HTTP_ACCEPT_LANGUAGE', '')

        re_accept_language = web.re_compile(', *')
        tokens = re_accept_language.split(accept_language)

        # take just the language part. ignore other details.
        # for example `en-gb;q=0.8` will be treated just as `en`.
        langs = [t[:2] for t in tokens]
        return langs and langs[0]
        
    def parse_lang_cookie():
        """Parses HTTP_LANG cookie."""
        cookies = web.cookies()
        return cookies.get('HTTP_LANG')

    def parse_query_string():
        i = web.input(lang=None, _method="GET")
        return i.lang
    
    try:    
        web.ctx.lang = parse_query_string() or parse_lang_cookie() or parse_lang_header() or ''
    except:
        import traceback
        traceback.print_exc()
        web.ctx.lang = None

def find(path, pattern):
    """Find all files matching the given pattern in the file hierarchy rooted at path.
    """
    import os
    import re
    for dirname, dirs, files in os.walk(path):
        for f in files:
            if re.match(pattern, f):
                yield os.path.join(dirname, f)
                
def dirstrip(f, dir):
    """Strips dir from f.
        >>> dirstrip('a/b/c/d', 'a/b/')
        'c/d'
    """
    f = web.lstrips(f, dir)
    return web.lstrips(f, '/')
    
def load_strings(plugin_path):
    """Load string.xx files from plugin/i18n/string.* files."""
    import os.path
    import glob
    
    def parse_path(path):
        """Find namespace and lang from path."""
        namespace = os.path.dirname(path)
        _, extn = os.path.splitext(p)
        return '/' + namespace, extn[1:] # strip dot
        
    def read_strings(path):
        env = {}
        execfile(path, env)
        # __builtins__ gets added by execfile
        del env['__builtins__']
        return env

    root = os.path.join(plugin_path, 'i18n')
    for p in find(root, 'strings\..*'):
        try:
            namespace, lang = parse_path(dirstrip(p, root))
            data = read_strings(p)
            strings._update_strings(namespace, lang, data)
        except:
            import traceback
            traceback.print_exc()
            print >> web.debug, "failed to load strings from", p

# global state
strings = i18n()
if hasattr(web, "_loadhooks"):
    web._loadhooks['i18n'] = i18n_loadhook

########NEW FILE########
__FILENAME__ = macro
"""
Macro extension to markdown.

Macros take argument string as input and returns result as markdown text.
"""
from markdown import markdown
import web
import os

import template
import storage

# macros loaded from disk
diskmacros = template.DiskTemplateSource()
# macros specified in the code
codemacros = web.storage()  
      
macrostore = storage.DictPile()
macrostore.add_dict(diskmacros)
macrostore.add_dict(codemacros)

def macro(f):
    """Decorator to register a markdown macro.
    Macro is a function that takes argument string and returns result as markdown string.
    """
    codemacros[f.__name__] = f
    return f

def load_macros(plugin_root, lazy=False):
    """Adds $plugin_root/macros to macro search path."""
    path = os.path.join(plugin_root, 'macros')
    if os.path.isdir(path):
        diskmacros.load_templates(path, lazy=lazy)

#-- macro execution 

def safeeval_args(args):
    """Evalues the args string safely using templator."""
    result = [None]
    def f(*args, **kwargs):
        result[0] = args, kwargs
    code = "$def with (f)\n$f(%s)" % args
    web.template.Template(web.utf8(code))(f)
    return result[0]
    
def call_macro(name, args):
    if name in macrostore:
        try:
            macro = macrostore[name]
            args, kwargs = safeeval_args(args)
            result = macro(*args, **kwargs)
        except Exception, e:
            i = web.input(_method="GET", debug="false")
            if i.debug.lower() == "true":
                raise
            result = "%s failed with error: <pre>%s</pre>" % (name, web.websafe(str(e)))
            import traceback
            traceback.print_exc()
        return str(result).decode('utf-8')
    else:
        return "Unknown macro: <pre>%s</pre>" % name

MACRO_PLACEHOLDER = "asdfghjjkl%sqwertyuiop"

class MacroPattern(markdown.BasePattern):
    """Inline pattern to replace macros."""
    def __init__(self, md):
        pattern = r'{{([a-zA-Z0-9_]*)\((.*)\)}}'
        markdown.BasePattern.__init__(self, pattern)
        self.markdown = md

    def handleMatch(self, m, doc):
        name, args = m.group(2), m.group(3)

        # markdown uses place-holders to replace html blocks. 
        # markdown.HtmlStash stores the html blocks to be replaced
        placeholder = self.store(self.markdown, (name, args))
        return doc.createTextNode(placeholder)
        
    def store(self, md, macro_info):
        placeholder = MACRO_PLACEHOLDER % md.macro_count
        md.macro_count += 1
        md.macros[placeholder] = macro_info
        return placeholder
        
def replace_macros(html, macros):
    """Replaces the macro place holders with real macro output."""    
    for placeholder, macro_info in macros.items():
        name, args = macro_info
        html = html.replace("<p>%s\n</p>" % placeholder, web.utf8(call_macro(name, args)))
        
    return html

class MacroExtension(markdown.Extension):
    def extendMarkdown(self, md, md_globals):
        md.inlinePatterns.append(MacroPattern(md))
        md.macro_count = 0
        md.macros = {}

def makeExtension(configs={}): 
    return MacroExtension(configs=configs)

#-- sample macros 

@macro
def HelloWorld():
    """Hello world macro."""
    return "<b>Hello, world</b>."

@macro
def ListOfMacros():
    """Lists all available macros."""
    out = ""
    out += "<ul>"
    for name, macro in macrostore.items():
        out += '  <li><b>%s</b>: %s</li>\n' % (name, macro.__doc__ or "")
    out += "</ul>"
    return out

if __name__ == "__main__":
    text = "{{HelloWorld()}}"
    md = markdown.Markdown(source=text, safe_mode=False)
    MacroExtension().extendMarkdown(md, {})
    html = md.convert()
    print replace_macros(html, md.macros)

########NEW FILE########
__FILENAME__ = markdown
#!/usr/bin/env python

version = "1.6b"
version_info = (1,6,2,"rc-2")
__revision__ = "$Rev$"

"""
Python-Markdown
===============

Converts Markdown to HTML.  Basic usage as a module:

    import markdown
    md = Markdown()
    html = markdown.convert(your_text_string)

See http://www.freewisdom.org/projects/python-markdown/ for more
information and instructions on how to extend the functionality of the
script.  (You might want to read that before you try modifying this
file.)

Started by [Manfred Stienstra](http://www.dwerg.net/).  Continued and
maintained  by [Yuri Takhteyev](http://www.freewisdom.org).

Contact: yuri [at] freewisdom.org

License: GPL 2 (http://www.gnu.org/copyleft/gpl.html) or BSD

"""


import re, sys, os, random, codecs

# Set debug level: 3 none, 2 critical, 1 informative, 0 all
(VERBOSE, INFO, CRITICAL, NONE) = range(4)

MESSAGE_THRESHOLD = CRITICAL

def message(level, text) :
    if level >= MESSAGE_THRESHOLD :
        print text


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

BOMS = { 'utf-8' : (unicode(codecs.BOM_UTF8, "utf-8"), ),
         'utf-16' : (unicode(codecs.BOM_UTF16_LE, "utf-16"),
                     unicode(codecs.BOM_UTF16_BE, "utf-16")),
         #'utf-32' : (unicode(codecs.BOM_UTF32_LE, "utf-32"),
         #            unicode(codecs.BOM_UTF32_BE, "utf-32")),
         }

def removeBOM(text, encoding):
    for bom in BOMS[encoding]:
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

def is_block_level (tag) :
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


def getBidiType(text) :

    if not text : return None

    ch = text[0]

    if not isinstance(ch, unicode) or not ch.isalpha():
        return None

    else :

        for min, max in RTL_BIDI_RANGES :
            if ( ch >= min and ch <= max ) :
                return "rtl"
        else :
            return "ltr"


class Document :

    def __init__ (self) :
        self.bidi = "ltr"

    def appendChild(self, child) :
        self.documentElement = child
        child.isDocumentElement = True
        child.parent = self
        self.entities = {}

    def setBidi(self, bidi) :
        if bidi :
            self.bidi = bidi

    def createElement(self, tag, textNode=None) :
        el = Element(tag)
        el.doc = self
        if textNode :
            el.appendChild(self.createTextNode(textNode))
        return el

    def createTextNode(self, text) :
        node = TextNode(text)
        node.doc = self
        return node

    def createEntityReference(self, entity):
        if entity not in self.entities:
            self.entities[entity] = EntityReference(entity)
        return self.entities[entity]

    def createCDATA(self, text) :
        node = CDATA(text)
        node.doc = self
        return node

    def toxml (self) :
        return self.documentElement.toxml()

    def normalizeEntities(self, text, avoidDoubleNormalizing=False) :

        if avoidDoubleNormalizing :
            regexps = ENTITY_NORMALIZATION_EXPRESSIONS_SOFT
        else :
            regexps = ENTITY_NORMALIZATION_EXPRESSIONS

        for regexp, substitution in regexps :
            text = regexp.sub(substitution, text)
        return text

    def find(self, test) :
        return self.documentElement.find(test)

    def unlink(self) :
        self.documentElement.unlink()
        self.documentElement = None


class CDATA :

    type = "cdata"

    def __init__ (self, text) :
        self.text = text

    def handleAttributes(self) :
        pass

    def toxml (self) :
        return "<![CDATA[" + self.text + "]]>"

class Element :

    type = "element"

    def __init__ (self, tag) :

        self.nodeName = tag
        self.attributes = []
        self.attribute_values = {}
        self.childNodes = []
        self.bidi = None
        self.isDocumentElement = False

    def setBidi(self, bidi) :

        if bidi :

            orig_bidi = self.bidi

            if not self.bidi or self.isDocumentElement:
                # Once the bidi is set don't change it (except for doc element)
                self.bidi = bidi
                self.parent.setBidi(bidi)


    def unlink(self) :
        for child in self.childNodes :
            if child.type == "element" :
                child.unlink()
        self.childNodes = None

    def setAttribute(self, attr, value) :
        if not attr in self.attributes :
            self.attributes.append(attr)

        self.attribute_values[attr] = value

    def insertChild(self, position, child) :
        self.childNodes.insert(position, child)
        child.parent = self

    def removeChild(self, child) :
        self.childNodes.remove(child)

    def replaceChild(self, oldChild, newChild) :
        position = self.childNodes.index(oldChild)
        self.removeChild(oldChild)
        self.insertChild(position, newChild)

    def appendChild(self, child) :
        self.childNodes.append(child)
        child.parent = self

    def handleAttributes(self) :
        pass

    def find(self, test, depth=0) :
        """ Returns a list of descendants that pass the test function """
        matched_nodes = []
        for child in self.childNodes :
            if test(child) :
                matched_nodes.append(child)
            if child.type == "element" :
                matched_nodes += child.find(test, depth+1)
        return matched_nodes

    def toxml(self):
        if ENABLE_ATTRIBUTES :
            for child in self.childNodes:
                child.handleAttributes()

        buffer = ""
        if self.nodeName in ['h1', 'h2', 'h3', 'h4'] :
            buffer += "\n"
        elif self.nodeName in ['li'] :
            buffer += "\n "

        # Process children FIRST, then do the attributes

        childBuffer = ""

        if self.childNodes or self.nodeName in ['blockquote']:
            childBuffer += ">"
            for child in self.childNodes :
                childBuffer += child.toxml()
            if self.nodeName == 'p' :
                childBuffer += "\n"
            elif self.nodeName == 'li' :
                childBuffer += "\n "
            childBuffer += "</%s>" % self.nodeName
        else :
            childBuffer += "/>"


            
        buffer += "<" + self.nodeName

        if self.nodeName in ['p', 'li', 'ul', 'ol',
                             'h1', 'h2', 'h3', 'h4', 'h5', 'h6'] :

            if not self.attribute_values.has_key("dir"):
                if self.bidi :
                    bidi = self.bidi
                else :
                    bidi = self.doc.bidi
                    
                if bidi=="rtl" :
                    self.setAttribute("dir", "rtl")
        
        for attr in self.attributes :
            value = self.attribute_values[attr]
            value = self.doc.normalizeEntities(value,
                                               avoidDoubleNormalizing=True)
            buffer += ' %s="%s"' % (attr, value)


        # Now let's actually append the children

        buffer += childBuffer

        if self.nodeName in ['p', 'li', 'ul', 'ol',
                             'h1', 'h2', 'h3', 'h4'] :
            buffer += "\n"

        return buffer


class TextNode :

    type = "text"
    attrRegExp = re.compile(r'\{@([^\}]*)=([^\}]*)}') # {@id=123}

    def __init__ (self, text) :
        self.value = text        

    def attributeCallback(self, match) :

        self.parent.setAttribute(match.group(1), match.group(2))

    def handleAttributes(self) :
        self.value = self.attrRegExp.sub(self.attributeCallback, self.value)

    def toxml(self) :

        text = self.value

        self.parent.setBidi(getBidiType(text))
        
        if not text.startswith(HTML_PLACEHOLDER_PREFIX):
            if self.parent.nodeName == "p" :
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


class Preprocessor :
    pass


class HeaderPreprocessor (Preprocessor):

    """
       Replaces underlined headers with hashed headers to avoid
       the nead for lookahead later.
    """

    def run (self, lines) :

        i = -1
        while i+1 < len(lines) :
            i = i+1
            if not lines[i].strip() :
                continue

            if lines[i].startswith("#") :
                lines.insert(i+1, "\n")

            if (i+1 <= len(lines)
                  and lines[i+1]
                  and lines[i+1][0] in ['-', '=']) :

                underline = lines[i+1].strip()

                if underline == "="*len(underline) :
                    lines[i] = "# " + lines[i].strip()
                    lines[i+1] = ""
                elif underline == "-"*len(underline) :
                    lines[i] = "## " + lines[i].strip()
                    lines[i+1] = ""

        return lines

HEADER_PREPROCESSOR = HeaderPreprocessor()

class LinePreprocessor (Preprocessor):
    """Deals with HR lines (needs to be done before processing lists)"""

    def run (self, lines) :
        for i in range(len(lines)) :
            if self._isLine(lines[i]) :
                lines[i] = "<hr />"
        return lines

    def _isLine(self, block) :
        """Determines if a block should be replaced with an <HR>"""
        if block.startswith("    ") : return 0  # a code block
        text = "".join([x for x in block if not x.isspace()])
        if len(text) <= 2 :
            return 0
        for pattern in ['isline1', 'isline2', 'isline3'] :
            m = RE.regExp[pattern].match(text)
            if (m and m.group(1)) :
                return 1
        else:
            return 0

LINE_PREPROCESSOR = LinePreprocessor()


class LineBreaksPreprocessor (Preprocessor):
    """Replaces double spaces at the end of the lines with <br/ >."""

    def run (self, lines) :
        for i in range(len(lines)) :
            if (lines[i].endswith("  ")
                and not RE.regExp['tabbed'].match(lines[i]) ):
                lines[i] += "<br />"
        return lines

LINE_BREAKS_PREPROCESSOR = LineBreaksPreprocessor()


class HtmlBlockPreprocessor (Preprocessor):
    """Removes html blocks from self.lines"""
    
    def _get_left_tag(self, block):
        return block[1:].replace(">", " ", 1).split()[0].lower()


    def _get_right_tag(self, left_tag, block):
        return block.rstrip()[-len(left_tag)-2:-1].lower()

    def _equal_tags(self, left_tag, right_tag):
        
        if left_tag in ['?', '?php', 'div'] : # handle PHP, etc.
            return True
        if ("/" + left_tag) == right_tag:
            return True
        if (right_tag == "--" and left_tag == "--") :
            return True
        elif left_tag == right_tag[1:] \
            and right_tag[0] != "<":
            return True
        else:
            return False

    def _is_oneliner(self, tag):
        return (tag in ['hr', 'hr/'])

    
    def run (self, lines) :

        new_blocks = []
        text = "\n".join(lines)
        text = text.split("\n\n")
        
        items = []
        left_tag = ''
        right_tag = ''
        in_tag = False # flag
        
        for block in text:
            if block.startswith("\n") :
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

        if items :
            new_blocks.append(self.stash.store('\n\n'.join(items)))
            new_blocks.append('\n')
            
        return "\n\n".join(new_blocks).split("\n")

HTML_BLOCK_PREPROCESSOR = HtmlBlockPreprocessor()


class ReferencePreprocessor (Preprocessor):

    def run (self, lines) :

        new_text = [];
        for line in lines:
            m = RE.regExp['reference-def'].match(line)
            if m:
                id = m.group(2).strip().lower()
                t = m.group(4).strip()  # potential title
                if not t :
                    self.references[id] = (m.group(3), t)
                elif (len(t) >= 2
                      and (t[0] == t[-1] == "\""
                           or t[0] == t[-1] == "\'"
                           or (t[0] == "(" and t[-1] == ")") ) ) :
                    self.references[id] = (m.group(3), t[1:-1])
                else :
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

#@@ Yuri Takhteyev suggested to change BRK like this to break the infinite recursion.

#BRK = ( r'\[('
#        + (NOBRACKET + r'(\['+NOBRACKET)*6
#        + (NOBRACKET+ r'\])*'+NOBRACKET)*6
#        + NOBRACKET + r')\]' )

BRK = ( r'\[('
        + (NOBRACKET + r'(\[')*6
        + (NOBRACKET+ r'\])*')*6
        + NOBRACKET + r')\]' )

BACKTICK_RE = r'\`([^\`]*)\`'                    # `e= m*c^2`
DOUBLE_BACKTICK_RE =  r'\`\`(.*)\`\`'            # ``e=f("`")``
ESCAPE_RE = r'\\(.)'                             # \<
EMPHASIS_RE = r'\*([^\*]*)\*'                    # *emphasis*
STRONG_RE = r'\*\*(.*)\*\*'                      # **strong**
STRONG_EM_RE = r'\*\*\*([^_]*)\*\*\*'            # ***strong***

if SMART_EMPHASIS:
    EMPHASIS_2_RE = r'(?<!\S)_(\S[^_]*)_'        # _emphasis_
else :
    EMPHASIS_2_RE = r'_([^_]*)_'                 # _emphasis_

STRONG_2_RE = r'__([^_]*)__'                     # __strong__
STRONG_EM_2_RE = r'___([^_]*)___'                # ___strong___

LINK_RE = BRK + r'\s*\(([^\)]*)\)'               # [text](url)
LINK_ANGLED_RE = BRK + r'\s*\(<([^\)]*)>\)'      # [text](<url>)
IMAGE_LINK_RE = r'\!' + BRK + r'\s*\(([^\)]*)\)' # ![alttxt](http://x.com/)
REFERENCE_RE = BRK+ r'\s*\[([^\]]*)\]'           # [Google][3]
IMAGE_REFERENCE_RE = r'\!' + BRK + '\s*\[([^\]]*)\]' # ![alt text][2]
NOT_STRONG_RE = r'( \* )'                        # stand-alone * or _
AUTOLINK_RE = r'<(http://[^>]*)>'                # <http://www.123.com>
AUTOMAIL_RE = r'<([^> \!]*@[^> ]*)>'               # <me@example.com>
#HTML_RE = r'(\<[^\>]*\>)'                        # <...>
HTML_RE = r'(\<[a-zA-Z/][^\>]*\>)'               # <...>
ENTITY_RE = r'(&[\#a-zA-Z0-9]*;)'                # &amp;

class Pattern:

    def __init__ (self, pattern) :
        self.pattern = pattern
        self.compiled_re = re.compile("^(.*)%s(.*)$" % pattern, re.DOTALL)

    def getCompiledRegExp (self) :
        return self.compiled_re

BasePattern = Pattern # for backward compatibility

class SimpleTextPattern (Pattern) :

    def handleMatch(self, m, doc) :
        return doc.createTextNode(m.group(2))

class SimpleTagPattern (Pattern):

    def __init__ (self, pattern, tag) :
        Pattern.__init__(self, pattern)
        self.tag = tag

    def handleMatch(self, m, doc) :
        el = doc.createElement(self.tag)
        el.appendChild(doc.createTextNode(m.group(2)))
        return el

class BacktickPattern (Pattern):

    def __init__ (self, pattern):
        Pattern.__init__(self, pattern)
        self.tag = "code"

    def handleMatch(self, m, doc) :
        el = doc.createElement(self.tag)
        text = m.group(2).strip()
        #text = text.replace("&", "&amp;")
        el.appendChild(doc.createTextNode(text))
        return el


class DoubleTagPattern (SimpleTagPattern) :

    def handleMatch(self, m, doc) :
        tag1, tag2 = self.tag.split(",")
        el1 = doc.createElement(tag1)
        el2 = doc.createElement(tag2)
        el1.appendChild(el2)
        el2.appendChild(doc.createTextNode(m.group(2)))
        return el1


class HtmlPattern (Pattern):

    def handleMatch (self, m, doc) :
        place_holder = self.stash.store(m.group(2))
        return doc.createTextNode(place_holder)


class LinkPattern (Pattern):

    def handleMatch(self, m, doc) :
        el = doc.createElement('a')
        el.appendChild(doc.createTextNode(m.group(2)))
        parts = m.group(9).split('"')
        # We should now have [], [href], or [href, title]
        if parts :
            el.setAttribute('href', parts[0].strip())
        else :
            el.setAttribute('href', "")
        if len(parts) > 1 :
            # we also got a title
            title = '"' + '"'.join(parts[1:]).strip()
            title = dequote(title) #.replace('"', "&quot;")
            el.setAttribute('title', title)
        return el


class ImagePattern (Pattern):

    def handleMatch(self, m, doc):
        el = doc.createElement('img')
        src_parts = m.group(9).split()
        el.setAttribute('src', src_parts[0])
        if len(src_parts) > 1 :
            el.setAttribute('title', dequote(" ".join(src_parts[1:])))
        if ENABLE_ATTRIBUTES :
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

        if m.group(9) :
            id = m.group(9).lower()
        else :
            # if we got something like "[Google][]"
            # we'll use "google" as the id
            id = m.group(2).lower()

        if not self.references.has_key(id) : # ignore undefined refs
            return None
        href, title = self.references[id]
        text = m.group(2)
        return self.makeTag(href, title, text, doc)

    def makeTag(self, href, title, text, doc):
        el = doc.createElement('a')
        el.setAttribute('href', href)
        if title :
            el.setAttribute('title', title)
        el.appendChild(doc.createTextNode(text))
        return el


class ImageReferencePattern (ReferencePattern):

    def makeTag(self, href, title, text, doc):
        el = doc.createElement('img')
        el.setAttribute('src', href)
        if title :
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

    def handleMatch(self, m, doc) :
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

class Postprocessor :
    pass


"""
======================================================================
========================== MISC AUXILIARY CLASSES ====================
======================================================================
"""

class HtmlStash :
    """This class is used for stashing HTML objects that we extract
        in the beginning and replace with place-holders."""

    def __init__ (self) :
        self.html_counter = 0 # for counting inline html segments
        self.rawHtmlBlocks=[]

    def store(self, html) :
        """Saves an HTML segment for later reinsertion.  Returns a
           placeholder string that needs to be inserted into the
           document.

           @param html: an html segment
           @returns : a placeholder string """
        self.rawHtmlBlocks.append(html)
        placeholder = HTML_PLACEHOLDER % self.html_counter
        self.html_counter += 1
        return placeholder


class BlockGuru :

    def _findHead(self, lines, fn, allowBlank=0) :

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

        for line in lines :

            if not line.strip() and not allowBlank:
                return items, lines[i:]

            if not line.strip() and allowBlank:
                # If we see a blank line, this _might_ be the end
                i += 1

                # Find the next non-blank line
                for j in range(i, len(lines)) :
                    if lines[j].strip() :
                        next = lines[j]
                        break
                else :
                    # There is no more text => this is the end
                    break

                # Check if the next non-blank line is still a part of the list

                part = fn(next)

                if part :
                    items.append("")
                    continue
                else :
                    break # found end of the list

            part = fn(line)

            if part :
                items.append(part)
                i += 1
                continue
            else :
                return items, lines[i:]
        else :
            i += 1

        return items, lines[i:]


    def detabbed_fn(self, line) :
        """ An auxiliary method to be passed to _findHead """
        m = RE.regExp['tabbed'].match(line)
        if m:
            return m.group(4)
        else :
            return None


    def detectTabbed(self, lines) :

        return self._findHead(lines, self.detabbed_fn,
                              allowBlank = 1)


def print_error(string):
    """Print an error string to stderr"""
    sys.stderr.write(string +'\n')


def dequote(string) :
    """ Removes quotes from around a string """
    if ( ( string.startswith('"') and string.endswith('"'))
         or (string.startswith("'") and string.endswith("'")) ) :
        return string[1:-1]
    else :
        return string

"""
======================================================================
========================== CORE MARKDOWN =============================
======================================================================

This stuff is ugly, so if you are thinking of extending the syntax,
see first if you can do it via pre-processors, post-processors,
inline patterns or a combination of the three.
"""

class CorePatterns :
    """This class is scheduled for removal as part of a refactoring
        effort."""

    patterns = {
        'header':          r'(#*)([^#]*)(#*)', # # A title
        'reference-def' :  r'(\ ?\ ?\ ?)\[([^\]]*)\]:\s*([^ ]*)(.*)',
                           # [Google]: http://www.google.com/
        'containsline':    r'([-]*)$|^([=]*)', # -----, =====, etc.
        'ol':              r'[ ]{0,3}[\d]*\.\s+(.*)', # 1. text
        'ul':              r'[ ]{0,3}[*+-]\s+(.*)', # "* text"
        'isline1':         r'(\**)', # ***
        'isline2':         r'(\-*)', # ---
        'isline3':         r'(\_*)', # ___
        'tabbed':          r'((\t)|(    ))(.*)', # an indented line
        'quoted' :         r'> ?(.*)', # a quoted block ("> ...")
    }

    def __init__ (self) :

        self.regExp = {}
        for key in self.patterns.keys() :
            self.regExp[key] = re.compile("^%s$" % self.patterns[key],
                                          re.DOTALL)

        self.regExp['containsline'] = re.compile(r'^([-]*)$|^([=]*)$', re.M)

RE = CorePatterns()


class Markdown:
    """ Markdown formatter class for creating an html document from
        Markdown text """


    def __init__(self, source=None,  # deprecated
                 extensions=[],
                 extension_configs=None,
                 encoding="utf-8",
                 safe_mode = False):
        """Creates a new Markdown instance.

           @param source: The text in Markdown format.
           @param encoding: The character encoding of <text>. """

        self.safeMode = safe_mode
        self.encoding = encoding
        self.source = source
        self.blockGuru = BlockGuru()
        self.registeredExtensions = []
        self.stripTopLevelTags = 1
        self.docType = ""

        self.preprocessors = [ HTML_BLOCK_PREPROCESSOR,
                               HEADER_PREPROCESSOR,
                               LINE_PREPROCESSOR,
                               LINE_BREAKS_PREPROCESSOR,
                               # A footnote preprocessor will
                               # get inserted here
                               REFERENCE_PREPROCESSOR ]


        self.postprocessors = [] # a footnote postprocessor will get
                                 # inserted later

        self.textPostprocessors = [] # a footnote postprocessor will get
                                     # inserted later                                 

        self.prePatterns = []
        

        self.inlinePatterns = [ DOUBLE_BACKTICK_PATTERN,
                                BACKTICK_PATTERN,
                                ESCAPE_PATTERN,
                                IMAGE_LINK_PATTERN,
                                IMAGE_REFERENCE_PATTERN,
                                REFERENCE_PATTERN,
                                LINK_ANGLED_PATTERN,
                                LINK_PATTERN,
                                AUTOLINK_PATTERN,
                                AUTOMAIL_PATTERN,
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


    def registerExtensions(self, extensions, configs) :

        if not configs :
            configs = {}

        for ext in extensions :

            extension_module_name = "mdx_" + ext

            try :
                module = __import__(extension_module_name)

            except :
                message(CRITICAL,
                        "couldn't load extension %s (looking for %s module)"
                        % (ext, extension_module_name) )
            else :

                if configs.has_key(ext) :
                    configs_for_ext = configs[ext]
                else :
                    configs_for_ext = []
                extension = module.makeExtension(configs_for_ext)    
                extension.extendMarkdown(self, globals())




    def registerExtension(self, extension) :
        """ This gets called by the extension """
        self.registeredExtensions.append(extension)

    def reset(self) :
        """Resets all state variables so that we can start
            with a new text."""
        self.references={}
        self.htmlStash = HtmlStash()

        HTML_BLOCK_PREPROCESSOR.stash = self.htmlStash
        REFERENCE_PREPROCESSOR.references = self.references
        HTML_PATTERN.stash = self.htmlStash
        ENTITY_PATTERN.stash = self.htmlStash
        REFERENCE_PATTERN.references = self.references
        IMAGE_REFERENCE_PATTERN.references = self.references

        for extension in self.registeredExtensions :
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
        text = self.source.strip()
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
        for line in self.lines :
            if line.startswith("#") :
                self._processSection(self.top_element, buffer)
                buffer = [line]
            else :
                buffer.append(line)
        self._processSection(self.top_element, buffer)
        
        #self._processSection(self.top_element, self.lines)

        # Not sure why I put this in but let's leave it for now.
        self.top_element.appendChild(self.doc.createTextNode('\n'))

        # Run the post-processors
        for postprocessor in self.postprocessors :
            postprocessor.run(self.doc)

        return self.doc


    def _processSection(self, parent_elem, lines,
                        inList = 0, looseList = 0) :

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

        if not lines :
            return

        # Check if this section starts with a list, a blockquote or
        # a code block

        processFn = { 'ul' :     self._processUList,
                      'ol' :     self._processOList,
                      'quoted' : self._processQuote,
                      'tabbed' : self._processCodeBlock }

        for regexp in ['ul', 'ol', 'quoted', 'tabbed'] :
            m = RE.regExp[regexp].match(lines[0])
            if m :
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

        if inList :

            start, theRest = self._linesUntil(lines, (lambda line:
                             RE.regExp['ul'].match(line)
                             or RE.regExp['ol'].match(line)
                                              or not line.strip()))

            self._processSection(parent_elem, start,
                                 inList - 1, looseList = looseList)
            self._processSection(parent_elem, theRest,
                                 inList - 1, looseList = looseList)


        else : # Ok, so it's just a simple block

            paragraph, theRest = self._linesUntil(lines, lambda line:
                                                 not line.strip())

            if len(paragraph) and paragraph[0].startswith('#') :
                m = RE.regExp['header'].match(paragraph[0])
                if m :
                    level = len(m.group(1))
                    h = self.doc.createElement("h%d" % level)
                    parent_elem.appendChild(h)
                    for item in self._handleInlineWrapper(m.group(2).strip()) :
                        h.appendChild(item)
                else :
                    message(CRITICAL, "We've got a problem header!")

            elif paragraph :

                list = self._handleInlineWrapper("\n".join(paragraph))

                if ( parent_elem.nodeName == 'li'
                     and not (looseList or parent_elem.childNodes)):

                    #and not parent_elem.childNodes) :
                    # If this is the first paragraph inside "li", don't
                    # put <p> around it - append the paragraph bits directly
                    # onto parent_elem
                    el = parent_elem
                else :
                    # Otherwise make a "p" element
                    el = self.doc.createElement("p")
                    parent_elem.appendChild(el)

                for item in list :
                    el.appendChild(item)

            if theRest :
                theRest = theRest[1:]  # skip the first (blank) line

            self._processSection(parent_elem, theRest, inList)



    def _processUList(self, parent_elem, lines, inList) :
        self._processList(parent_elem, lines, inList,
                         listexpr='ul', tag = 'ul')

    def _processOList(self, parent_elem, lines, inList) :
        self._processList(parent_elem, lines, inList,
                         listexpr='ol', tag = 'ol')


    def _processList(self, parent_elem, lines, inList, listexpr, tag) :
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

        for line in lines :

            loose = 0
            if not line.strip() :
                # If we see a blank line, this _might_ be the end of the list
                i += 1
                loose = 1

                # Find the next non-blank line
                for j in range(i, len(lines)) :
                    if lines[j].strip() :
                        next = lines[j]
                        break
                else :
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
                else :
                    break # found end of the list

            # Now we need to detect list items (at the current level)
            # while also detabing child elements if necessary

            for expr in ['ul', 'ol', 'tabbed']:

                m = RE.regExp[expr].match(line)
                if m :
                    if expr in ['ul', 'ol'] :  # We are looking at a new item
                        #if m.group(1) :
                        # Removed the check to allow for a blank line
                        # at the beginning of the list item
                        items.append([m.group(1)])
                        item += 1
                    elif expr == 'tabbed' :  # This line needs to be detabbed
                        items[item].append(m.group(4)) #after the 'tab'

                    i += 1
                    break
            else :
                items[item].append(line)  # Just regular continuation
                i += 1 # added on 2006.02.25
        else :
            i += 1

        # Add the dom elements
        for item in items :
            li = self.doc.createElement("li")
            ul.appendChild(li)

            self._processSection(li, item, inList + 1, looseList = looseList)

        # Process the remaining part of the section

        self._processSection(parent_elem, lines[i:], inList)


    def _linesUntil(self, lines, condition) :
        """ A utility function to break a list of lines upon the
            first line that satisfied a condition.  The condition
            argument should be a predicate function.
            """

        i = -1
        for line in lines :
            i += 1
            if condition(line) : break
        else :
            i += 1
        return lines[:i], lines[i:]

    def _processQuote(self, parent_elem, lines, inList) :
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
        for line in lines :
            m = RE.regExp['quoted'].match(line)
            if m :
                dequoted.append(m.group(1))
                i += 1
            else :
                break
        else :
            i += 1

        blockquote = self.doc.createElement('blockquote')
        parent_elem.appendChild(blockquote)

        self._processSection(blockquote, dequoted, inList)
        self._processSection(parent_elem, lines[i:], inList)




    def _processCodeBlock(self, parent_elem, lines, inList) :
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



    def _handleInlineWrapper (self, line) :

        parts = [line]

        for pattern in self.inlinePatterns :

            i = 0

            while i < len(parts) :
                
                x = parts[i]

                if isinstance(x, (str, unicode)) :
                    result = self._applyPattern(x, pattern)

                    if result :
                        i -= 1
                        parts.remove(x)
                        for y in result :
                            parts.insert(i+1,y)

                i += 1

        for i in range(len(parts)) :
            x = parts[i]
            if isinstance(x, (str, unicode)) :
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

        for pattern in self.inlinePatterns :
            list = self._applyPattern( line, pattern)
            if list: return list

        return [self.doc.createTextNode(line)]

    def _applyPattern(self, line, pattern) :

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
        if not m :
            return None

        # if we got a match let the pattern make us a NanoDom node
        # if it doesn't, move on
        node = pattern.handleMatch(m, self.doc)

        # check if any of this nodes have children that need processing

        if isinstance(node, Element):

            if not node.nodeName in ["code", "pre"] :
                for child in node.childNodes :
                    if isinstance(child, TextNode):
                        
                        result = self._handleInlineWrapper(child.value)
                        
                        if result:

                            if result == [child] :
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
                



        if node :
            # Those are in the reverse order!
            return ( m.groups()[-1], # the string to the left
                     node,           # the new node
                     m.group(1))     # the string to the right of the match

        else :
            return None

    def convert (self, source = None):
        """Return the document in XHTML format.

        @returns: A serialized XHTML body."""
        #try :

        if source :
            self.source = source

        if not self.source :
            return ""

        self.source = removeBOM(self.source, self.encoding)

        
        doc = self._transform()
        xml = doc.toxml()

        #finally:
        #    doc.unlink()

        # Let's stick in all the raw html pieces

        for i in range(self.htmlStash.html_counter) :
            html = self.htmlStash.rawHtmlBlocks[i]
            if self.safeMode :
                html = HTML_REMOVED_TEXT
                
            xml = xml.replace("<p>%s\n</p>" % (HTML_PLACEHOLDER % i),
                              html + "\n")
            xml = xml.replace(HTML_PLACEHOLDER % i,
                              html)

        # And return everything but the top level tag

        if self.stripTopLevelTags :
            xml = xml.strip()[23:-7] + "\n"

        for pp in self.textPostprocessors :
            xml = pp.run(xml)

        return self.docType + xml


    __str__ = convert   # deprecated - will be changed in 1.7 to report
                        # information about the MD instance
    
    toString = __str__  # toString() method is deprecated


    def __unicode__(self):
        """Return the document in XHTML format as a Unicode object.
        """
        return str(self)#.decode(self.encoding)


    toUnicode = __unicode__  # deprecated - will be removed in 1.7




# ====================================================================

def markdownFromFile(input = None,
                     output = None,
                     extensions = [],
                     encoding = None,
                     message_threshold = CRITICAL,
                     safe = False) :

    global MESSAGE_THRESHOLD
    MESSAGE_THRESHOLD = message_threshold

    message(VERBOSE, "input file: %s" % input)


    if not encoding :
        encoding = "utf-8"

    input_file = codecs.open(input, mode="r", encoding=encoding)
    text = input_file.read()
    input_file.close()

    new_text = markdown(text, extensions, encoding, safe_mode = safe)

    if output :
        output_file = codecs.open(output, "w", encoding=encoding)
        output_file.write(new_text)
        output_file.close()

    else :
        sys.stdout.write(new_text.encode(encoding))

def markdown(text,
             extensions = [],
             encoding = None,
             safe_mode = False) :
    
    message(VERBOSE, "in markdown.markdown(), received text:\n%s" % text)

    extension_names = []
    extension_configs = {}
    
    for ext in extensions :
        pos = ext.find("(") 
        if pos == -1 :
            extension_names.append(ext)
        else :
            name = ext[:pos]
            extension_names.append(name)
            pairs = [x.split("=") for x in ext[pos+1:-1].split(",")]
            configs = [(x.strip(), y.strip()) for (x, y) in pairs]
            extension_configs[name] = configs

    md = Markdown(extensions=extension_names,
                  extension_configs=extension_configs,
                  safe_mode = safe_mode)

    return md.convert(text)
        

class Extension :

    def __init__(self, configs = {}) :
        self.config = configs

    def getConfig(self, key) :
        if self.config.has_key(key) :
            return self.config[key][0]
        else :
            return ""

    def getConfigInfo(self) :
        return [(key, self.config[key][1]) for key in self.config.keys()]

    def setConfig(self, key, value) :
        self.config[key][0] = value


OPTPARSE_WARNING = """
Python 2.3 or higher required for advanced command line options.
For lower versions of Python use:

      %s INPUT_FILE > OUTPUT_FILE
    
""" % EXECUTABLE_NAME_FOR_USAGE

def parse_options() :

    try :
        optparse = __import__("optparse")
    except :
        if len(sys.argv) == 2 :
            return {'input' : sys.argv[1],
                    'output' : None,
                    'message_threshold' : CRITICAL,
                    'safe' : False,
                    'extensions' : [],
                    'encoding' : None }

        else :
            print OPTPARSE_WARNING
            return None

    parser = optparse.OptionParser(usage="%prog INPUTFILE [options]")

    parser.add_option("-f", "--file", dest="filename",
                      help="write output to OUTPUT_FILE",
                      metavar="OUTPUT_FILE")
    parser.add_option("-e", "--encoding", dest="encoding",
                      help="encoding for input and output files",)
    parser.add_option("-q", "--quiet", default = CRITICAL,
                      action="store_const", const=NONE, dest="verbose",
                      help="suppress all messages")
    parser.add_option("-v", "--verbose",
                      action="store_const", const=INFO, dest="verbose",
                      help="print info messages")
    parser.add_option("-s", "--safe",
                      action="store_const", const=True, dest="safe",
                      help="same mode (strip user's HTML tag)")
    
    parser.add_option("--noisy",
                      action="store_const", const=VERBOSE, dest="verbose",
                      help="print debug messages")
    parser.add_option("-x", "--extension", action="append", dest="extensions",
                      help = "load extension EXTENSION", metavar="EXTENSION")

    (options, args) = parser.parse_args()

    if not len(args) == 1 :
        parser.print_help()
        return None
    else :
        input_file = args[0]

    if not options.extensions :
        options.extensions = []

    return {'input' : input_file,
            'output' : options.filename,
            'message_threshold' : options.verbose,
            'safe' : options.safe,
            'extensions' : options.extensions,
            'encoding' : options.encoding }

if __name__ == '__main__':
    """ Run Markdown from the command line. """

    options = parse_options()

    #if os.access(inFile, os.R_OK):

    if not options :
        sys.exit(0)
    
    markdownFromFile(**options)











########NEW FILE########
__FILENAME__ = mdx_footnotes
"""
## To see this file as plain text go to
## http://freewisdom.org/projects/python-markdown/mdx_footnotes.raw_content

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


import re, markdown, random

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

            self.md._processSection(li, self.footnotes[id].split("\n"))

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
                    node = li
                node.appendChild(backlink)

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
__FILENAME__ = stats
"""Library to collect count and timings of various part of code.

Here is an example usage:

    stats.begin("memcache", method="get", key="foo")
    memcache_client.get("foo")
    stats.end()

Currently this doesn't support nesting.    
"""
import web
import time
from context import context

def _get_stats():
    if "stats" not in web.ctx:
        context.stats = web.ctx.stats = []
    return web.ctx.stats
    
def begin(name, **kw):
    stats = _get_stats()
    stats.append(web.storage(name=name, data=kw, t_start=time.time(), time=0.0))
    
def end(**kw):
    stats = _get_stats()
    s = stats[-1]
    
    s.data.update(kw)
    s.t_end = time.time()
    s.time = s.t_end - s.t_start
    
def stats_summary():
    d = web.storage()

    if not web.ctx.get("stats"):
        return d
        
    total_measured = 0.0
    
    for s in web.ctx.stats:
        if s.name not in d:
            d[s.name] = web.storage(count=0, time=0.0)
        d[s.name].count += 1
        d[s.name].time += s.time
        total_measured += s.time
    
    # consider the start time of first stat as start of the request
    total_time = time.time() - web.ctx.stats[0].t_start
    d['total'] = web.storage(count=0, time=total_time, unaccounted=total_time-total_measured)
    
    return d

########NEW FILE########
__FILENAME__ = storage
"""
Useful datastructures.
"""

import web
import copy
from UserDict import DictMixin

class OrderedDict(dict):
    """
    A dictionary in which the insertion order of items is preserved.
    """
    _reserved = ['_keys']

    def __init__(self, d={}, **kw):
        self._keys = d.keys() + kw.keys()
        dict.__init__(self, d, **kw)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self._keys.remove(key)

    def __setitem__(self, key, item):
        # a peculiar sharp edge from copy.deepcopy
        # we'll have our set item called without __init__
        if not hasattr(self, '_keys'):
            self._keys = [key,]
        if key not in self:
            self._keys.append(key)
        dict.__setitem__(self, key, item)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError, key

    def __setattr__(self, key, value):
        # special care special methods
        if key in self._reserved:
            self.__dict__[key] = value
        else:
            self[key] = value
    
    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError:
            raise AttributeError, key

    def clear(self):
        dict.clear(self)
        self._keys = []

    def popitem(self):
        if len(self._keys) == 0:
            raise KeyError('dictionary is empty')
        else:
            key = self._keys[-1]
            val = self[key]
            del self[key]
            return key, val

    def setdefault(self, key, failobj = None):
        if key not in self:
            self._keys.append(key)
        dict.setdefault(self, key, failobj)

    def update(self, d):
        for key in d.keys():
            if not self.has_key(key):
                self._keys.append(key)
        dict.update(self, d)

    def iterkeys(self):
        return iter(self._keys)

    def keys(self):
        return self._keys[:]

    def itervalues(self):
        for k in self._keys:
            yield self[k]

    def values(self):
        return list(self.itervalues())

    def iteritems(self):
        for k in self._keys:
            yield k, self[k]

    def items(self):
        return list(self.iteritems())

    def __iter__(self):
        return self.iterkeys()

    def index(self, key):
        if not self.has_key(key):
            raise KeyError(key)
        return self._keys.index(key)

class DefaultDict(dict):
    """Dictionary with a default value for unknown keys.
    Source: http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/389639
        >>> a = DefaultDict(0)
        >>> a.foo
        0
        >>> a['bar']
        0
        >>> a.x = 1
        >>> a.x
        1
    """
    def __init__(self, default):
        self.default = default

    def __getitem__(self, key):
        if key in self: 
            return self.get(key)
        else:
            ## Need copy in case self.default is something like []
            return self.setdefault(key, copy.deepcopy(self.default))
    
    def __getattr__(self, key):
        # special care special methods
        if key.startswith('__'):
            return dict.__getattr__(self, key)
        else:
            return self[key]
            
    __setattr__ = dict.__setitem__

    def __copy__(self):
        copy = DefaultDict(self.default)
        copy.update(self)
        return copy

storage = DefaultDict(OrderedDict())    

class SiteLocalDict:
    """
    Takes a dictionary that maps sites to objects.
    When somebody tries to get or set an attribute or item 
    of the SiteLocalDict, it passes it on to the object 
    for the active site in dictionary.
    Active site is found from `context.site`.
    see infogami.utils.context.context
    """    
    def __init__(self):
        self.__dict__['_SiteLocalDict__d'] = {}
        
    def __getattr__(self, name):
        return getattr(self._getd(), name)
        
    def __setattr__(self, name, value):
        setattr(self._getd(), name, value)

    def __delattr__(self, name):
        delattr(self._getd(), name)
        
    def _getd(self):
        from context import context
        site = web.ctx.get('site')
        key = site and site.name
        if key not in self.__d:
            self.__d[key] = web.storage()
        return self.__d[key]

class ReadOnlyDict:
    """Dictionary wrapper to provide read-only access to a dictionary."""
    def __init__(self, d):
        self._d = d
    
    def __getitem__(self, key):
        return self._d[key]
    
    def __getattr__(self, key):
        try:
            return self._d[key]
        except KeyError:
            raise AttributeError, key

class DictPile(DictMixin):
    """Pile of ditionaries. 
    A key in top dictionary covers the key with the same name in the bottom dictionary.
    
        >>> a = {'x': 1, 'y': 2}
        >>> b = {'y': 5, 'z': 6}
        >>> d = DictPile([a, b])
        >>> d['x'], d['y'], d['z'] 
        (1, 5, 6)
        >>> b['x'] = 4
        >>> d['x'], d['y'], d['z'] 
        (4, 5, 6)
        >>> c = {'x':0, 'y':1}
        >>> d.add_dict(c)
        >>> d['x'], d['y'], d['z']
        (0, 1, 6)
    """
    def __init__(self, dicts=[]):
        self.dicts = dicts[:]
        
    def add_dict(self, d):
        """Adds d to the pile of dicts at the top.
        """
        self.dicts.append(d)
        
    def __getitem__(self, key):
        for d in self.dicts[::-1]:
            if key in d:
                return d[key]
        else:
            raise KeyError, key
    
    def keys(self):
        keys = set()
        for d in self.dicts:
            keys.update(d.keys())
        return list(keys)
            
if __name__ == "__main__":
    import doctest
    doctest.testmod()
########NEW FILE########
__FILENAME__ = template
"""
Template Management.

In Infogami, templates are provided by multiple plugins. This module takes 
templates from each module and makes them available under single namespace.

There could also be multiple sources of templates. For example, from plugins 
and from the wiki. The `Render` class takes care of providing the correct 
template from multiple template sources and error handling.
"""
import web
import os

import storage

# There are some backward-incompatible changes in web.py 0.34 which makes Infogami fail. 
# Monkey-patching web.py to fix that issue.
if web.__version__ == "0.34":
    from UserDict import DictMixin
    web.template.TemplateResult.__bases__ = (DictMixin, web.storage)
    web.template.StatementNode.emit = lambda self, indent, text_indent="": indent + self.stmt
    
web_render = web.template.render

class TemplateRender(web_render):
    def _lookup(self, name):
        path = os.path.join(self._loc, name)
        filepath = self._findfile(path)
        if filepath:
            return 'file', filepath
        elif os.path.isdir(path):
            return 'dir', path
        else:
            return 'none', None
            
    def __repr__(self):
        return "<TemplateRender: %s>" % repr(self._loc)

web.template.Render = web.template.render = TemplateRender

class LazyTemplate:
    def __init__(self, func, name=None, **kw):
        self.func = func
        self.name = name
        self.__dict__.update(kw)
        
    def __repr__(self):
        return "<LazyTemplate: %s>" % repr(self.name)

class DiskTemplateSource(web.storage):
    """Template source of templates on disk.
    Supports loading of templates from a search path instead of single dir.
    """
    def load_templates(self, path, lazy=False):
        def get_template(render, name):
            tokens = name.split(os.path.sep)
            render = getattr(render, name)
            render.filepath = '%s/%s.html' % (path, name)
            return render
            
        def set_template(render, name):
            t = get_template(render, name)
            # disable caching in debug mode
            if not web.config.debug:
                self[name] = t
            return t
            
        render = web.template.render(path)
        # assuming all templates have .html extension
        names = [web.rstrips(p, '.html') for p in find(path) if p.endswith('.html')]
        for name in names:
            if lazy:
                def load(render=render, name=name):
                    return set_template(render, name)
                    
                self[name] = LazyTemplate(load, name=path + '/' + name, filepath=path + '/' + name + '.html')
            else:
                self[name] = get_template(render, name)
            
    def __getitem__(self, name):
        value = dict.__getitem__(self, name)
        if isinstance(value, LazyTemplate):
            value = value.func()
            
        return value
           
    def __repr__(self):
        return "<DiskTemplateSource at %d>" % id(self)
            
def find(path):
    """Find all files in the file hierarchy rooted at path.
        >> find('..../web')
        ['db.py', 'http.py', 'wsgiserver/__init__.py', ....]
    """
    for dirname, dirs, files in os.walk(path):
        dirname = web.lstrips(dirname, path)
        dirname = web.lstrips(dirname, '/')
        for f in files:
            yield os.path.join(dirname, f)

#@@ Find a better name
class Render(storage.DictPile):
    add_source = storage.DictPile.add_dict        
        
    def __getitem__(self, key):
        # take templates from all sources
        templates = [s[key] for s in self.dicts[::-1] if key in s]
        if templates:
            return lambda *a, **kw: saferender(templates, *a, **kw)
        else:
            raise KeyError, key
            
    def __getattr__(self, key):
        if key.startswith('__'):
            raise AttributeError, key
    
        try:
            return self[key]
        except KeyError:
            raise AttributeError, key

def usermode(f):
    """Returns a function that calls f after switching to user mode of tdb.
    In user mode, saving of things will be disabled to protect user written 
    templates from modifying things.
    """
    def g(*a, **kw):
        try:
            web.ctx.tdb_mode = 'user'
            return f(*a, **kw)
        finally:
            web.ctx.tdb_mode = 'system'

    g.__name__ = f.__name__
    return g

class Stowage(web.storage):
    def __str__(self):
        return self._str

@usermode
def saferender(templates, *a, **kw):
    """Renders using the first successful template from the list of templates."""
    for t in templates:
        try:
            result = t(*a, **kw)
            content_type = getattr(result, 'ContentType', 'text/html; charset=utf-8').strip()
            web.header('Content-Type', content_type, unique=True)
            return result
        except Exception, e:
            # help to debug template errors.
            # when called with debug=true, the debug error is displayed.
            i = web.input(_method='GET', debug="false")
            if i.debug.lower() == "true":
                raise
            
            import delegate
            delegate.register_exception()
            
            import traceback
            traceback.print_exc()
            
            import view            
            message = str(t.filename) + ': error in processing template: ' + e.__class__.__name__ + ': ' + str(e) + ' (falling back to default template)'
            view.add_flash_message('error', message)

    return Stowage(_str="Unable to render this page.", title='Error')

def typetemplate(name):
    """explain later"""
    def template(page, *a, **kw):
        default_template = getattr(render, 'default_' + name, None)
        key = page.type.key[1:] + '/' + name
        t = getattr(render, web.utf8(key), default_template)
        return t(page, *a, **kw)
    return template
    
def load_templates(plugin_root, lazy=True):
    """Adds $plugin_root/templates to template search path"""
    path = os.path.join(plugin_root, 'templates')
    if os.path.exists(path):
        disktemplates.load_templates(path, lazy=lazy)

disktemplates = DiskTemplateSource()
render = Render()
render.add_source(disktemplates)

# setup type templates
render.view = typetemplate('view')
render.edit = typetemplate('edit')
render.repr = typetemplate('repr')
render.input = typetemplate('input')
render.xdiff = typetemplate('diff')

def render_template(name, *a, **kw):
    return get_template(name)(*a, **kw)

def get_template(name):
    # strip extension
    if "." in name:
        name = name.rsplit(".", 1)[0]
    return render.get(name)

########NEW FILE########
__FILENAME__ = test_app
from infogami.utils import app

def test_parse_accept():

    # testing examples from http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html
    assert app.parse_accept("audio/*; q=0.2, audio/basic") == [
        {"media_type": "audio/basic"},
        {"media_type": "audio/*", "q": 0.2}
    ]

    assert app.parse_accept("text/plain; q=0.5, text/html, text/x-dvi; q=0.8, text/x-c") == [
        {"media_type": "text/html"},
        {"media_type": "text/x-c"},
        {"media_type": "text/x-dvi", "q": 0.8},
        {"media_type": "text/plain", "q": 0.5}
    ]

    # try empty
    assert app.parse_accept("") == [
        {'media_type': ''}
    ]
    assert app.parse_accept(" ") == [
        {'media_type': ''}
    ]
    assert app.parse_accept(",") == [
        {'media_type': ''},
        {'media_type': ''}
    ]

    # try some bad ones
    assert app.parse_accept("hc/url;*/*") == [
        {"media_type": "hc/url"}
    ]
    assert app.parse_accept("text/plain;q=bad") == [
        {"media_type": "text/plain"}
    ]

    assert app.parse_accept(";q=1") == [
        {"media_type": "", "q": 1.0}
    ]
########NEW FILE########
__FILENAME__ = types
"""Maintains a registry of path pattern vs type names to guess type from path when a page is newly created.
"""
import re
import storage

default_type = '/type/page'
type_patterns = storage.OrderedDict()

def register_type(pattern, typename):
    type_patterns[pattern] = typename
    
def guess_type(path):
    import web
    for pattern, typename in type_patterns.items():
        if re.search(pattern, path):
            return typename
            
    return default_type

########NEW FILE########
__FILENAME__ = view

import web
import os
import urllib
import re

import infogami
from infogami.core.diff import simple_diff, better_diff
from infogami.utils import i18n
from infogami.utils.markdown import markdown, mdx_footnotes

from context import context
from template import render, render_template, get_template

import macro
import storage
from flash import get_flash_messages, add_flash_message
import stats

wiki_processors = []
def register_wiki_processor(p):
    wiki_processors.append(p)
    
def _register_mdx_extensions(md):
    """Register required markdown extensions."""
    # markdown's interface to specifying extensions is really painful.
    mdx_footnotes.makeExtension({}).extendMarkdown(md, markdown.__dict__)
    macro.makeExtension({}).extendMarkdown(md, markdown.__dict__)
    
def get_markdown(text, safe_mode=False):
    md = markdown.Markdown(source=text, safe_mode=safe_mode)
    _register_mdx_extensions(md)
    md.postprocessors += wiki_processors
    return md

def get_doc(text):
    return get_markdown(text)._transform()

web.template.Template.globals.update(dict(
  changequery = web.changequery,
  url = web.url,
  numify = web.numify,
  ctx = context,
  _ = i18n.strings,
  i18n = i18n.strings,
  macros = storage.ReadOnlyDict(macro.macrostore),
  diff = simple_diff,
  better_diff = better_diff,
  find_i18n_namespace = i18n.find_i18n_namespace,
    
  # common utilities
  int = int,
  str = str,
  basestring=basestring,
  unicode=unicode,
  bool=bool,
  list = list,
  set = set,
  dict = dict,
  min = min,
  max = max,
  range = range,
  len = len,
  repr=repr,
  zip=zip,
  isinstance=isinstance,
  enumerate=enumerate,
  hasattr = hasattr,
  utf8=web.utf8,
  Dropdown = web.form.Dropdown,
  slice = slice,
  urlencode = urllib.urlencode,
  debug = web.debug,
  get_flash_messages=get_flash_messages,
  render_template=render_template,
  get_template=get_template,
  stats_summary=stats.stats_summary
))

def public(f):
    """Exposes a funtion in templates."""
    web.template.Template.globals[f.__name__] = f
    return f

@public    
def safeint(value, default=0):
    """Convers the value to integer. Returns 0, if the conversion fails."""
    try:
        return int(value)
    except Exception:
        return default

@public
def safeadd(*items):
    s = ''
    for i in items:
        s += (i and web.utf8(i)) or ''
    return s

@public
def query_param(name, default=None):
    i = web.input(_m='GET')
    return i.get(name, default)

@public
def http_status(status):
    """Function to set http status from templates. 
    Useful to implement notfound and redirect.
    """
    web.ctx.status = status
    
@public
def join(sep, items):
    items = [web.utf8(item or "") for item in items]
    return web.utf8(sep).join(items)
    
@public
def format(text, safe_mode=False):
    html, macros = _format(text, safe_mode=safe_mode)
    return macro.replace_macros(html, macros)
    
def _format(text, safe_mode=False):
    text = web.safeunicode(text)
    md = get_markdown(text, safe_mode=safe_mode)
    html = web.safestr(md.convert())
    return html, md.macros

@public
def link(path, text=None):
    return '<a href="%s">%s</a>' % (web.ctx.homepath + path, text or path)

@public
def homepath():
    return web.ctx.homepath        

@public
def add_stylesheet(path):
    if web.url(path) not in context.stylesheets:
        context.stylesheets.append(web.url(path))
    return ""
    
@public
def add_javascript(path):
    if web.url(path) not in context.javascripts:
        context.javascripts.append(web.url(path))
    return ""

@public
def spacesafe(text):
    text = web.websafe(text)
    #@@ TODO: should take care of space at the begining of line also
    text = text.replace('  ', ' &nbsp;');
    return text

def value_to_thing(value, type):
    if value is None: value = ""
    return web.storage(value=value, is_primitive=True, type=type)
    
def set_error(msg):
    if not context.error: context.error = ''
    context.error += '\n' + msg

def render_site(url, page):
    return render.site(page)

@public
def thingrepr(value, type=None):
    if isinstance(value, list):
        return ', '.join(thingrepr(t, type).strip() for t in value)
        
    from infogami.infobase import client        
    if type is None and value is client.nothing:
        return ""
    
    if isinstance(value, client.Thing):
        type = value.type
        
    return unicode(render.repr(thingify(type, value)))
        
#@public
#def thinginput(type, name, value, **attrs):
#    """Renders html input field of given type."""
#    return unicode(render.input(thingify(type, value), name))
    
@public
def thinginput(value, property=None, **kw):
    if property is None:
        if 'expected_type' in kw:
            if isinstance(kw['expected_type'], basestring):
                from infogami.core import db        
                kw['expected_type'] = db.get_version(kw['expected_type'])
        else:
            raise ValueError, "missing expected_type"
        property = web.storage(kw)
    return unicode(render.input(thingify(property.expected_type, value), property))

def thingify(type, value):
    # if type is given as string then get the type from db
    if type is None:
        type = '/type/string'
        
    if isinstance(type, basestring):
        from infogami.core import db
        type = db.get_version(type)
        
    PRIMITIVE_TYPES = "/type/key", "/type/string", "/type/text", "/type/int", "/type/float", "/type/boolean", "/type/uri"    
    from infogami.infobase import client
        
    if type.key not in PRIMITIVE_TYPES and isinstance(value, basestring) and not value.strip():
        value = web.ctx.site.new('', {'type': type})

    if type.key not in PRIMITIVE_TYPES and (value is None or isinstance(value, client.Nothing)):
        value = web.ctx.site.new('', {'type': type})
    
    # primitive values
    if not isinstance(value, client.Thing):
        value = web.storage(value=value, is_primitive=True, type=type, key=value)
    else:
        value.type = type # value.type might be string, make it Thing object
    
    return value

@public
def thingdiff(type, name, v1, v2):
    if isinstance(v1, list) or isinstance(v2, list):
        v1 = v1 or []
        v2 = v2 or []
        v1 += [""] * (len(v2) - len(v1))
        v2 += [""] * (len(v1) - len(v2))
        return "".join(thingdiff(type, name, a, b) for a, b in zip(v1, v2))
    
    if v1 == v2:
        return ""
    else:
        return unicode(render.xdiff(thingify(type, v1), thingify(type, v2), name))
        
@public
def thingview(page):
    return render.view(page)

@public    
def thingedit(page):
    return render.edit(page)

@infogami.install_hook
@infogami.action
def movefiles():
    """Move files from every plugin into static directory."""    
    import delegate
    import shutil
    def cp_r(src, dest):
        if not os.path.exists(src):
            return
            
        if os.path.isdir(src):
            if not os.path.exists(dest):
                os.mkdir(dest)
            for f in os.listdir(src):
                frm = os.path.join(src, f)
                to = os.path.join(dest, f)
                cp_r(frm, to)
        else:
            print 'copying %s to %s' % (src, dest)
            shutil.copy(src, dest)
    
    static_dir = os.path.join(os.getcwd(), "static")
    for plugin in delegate.plugins:
        src = os.path.join(plugin.path, "files")
        cp_r(src, static_dir)

@infogami.install_hook
def movetypes():
    def property(name, expected_type, unique=True, **kw):
        q = {
            'name': name,
            'type': {'key': '/type/property'},
            'expected_type': {'key': expected_type},
            'unique': unique
        }
        q.update(kw)
        return q
        
    def backreference(name, expected_type, property_name, **kw):
        q = {
            'name': name,
            'type': {'key': '/type/backreference'},
            'expected_type': {'key': expected_type},
            'property_name': property_name
        }
        q.update(kw)
        return q
        
    def readfile(filename):
        text = open(filename).read()
        return eval(text, {
            'property': property, 
            'backreference': backreference,
            'true': True,
            'false': False
        })

    import delegate
    extension = ".type"
    pages = []
    for plugin in delegate.plugins:
        path = os.path.join(plugin.path, 'types')
        if os.path.exists(path) and os.path.isdir(path):
            files = [os.path.join(path, f) for f in sorted(os.listdir(path)) if f.endswith(extension)]
            for f in files:
                print >> web.debug, 'moving types from ', f
                d = readfile(f)
                if isinstance(d, list):
                    pages.extend(d)
                else:
                    pages.append(d)
    web.ctx.site.save_many(pages, 'install')

@infogami.install_hook
def movepages():
    move('pages', '.page', recursive=False)

def move(dir, extension, recursive=False, readfunc=None):
    import delegate
        
    readfunc = readfunc or eval
    pages = []    
    for p in delegate.plugins:
        path = os.path.join(p.path, dir)
        if os.path.exists(path) and os.path.isdir(path):
            files = [os.path.join(path, f) for f in os.listdir(path) if f.endswith(extension)]
            for f in files:
                type = readfunc(open(f).read())
                pages.append(type)

    delegate.admin_login()
    result = web.ctx.site.save_many(pages, "install")
    for r in result:
        print r

@infogami.action
def write(filename):
    q = open(filename).read()
    print web.ctx.site.write(q)
    
# this is not really the right place to move this, but couldn't find a better place than this.     
def require_login(f):
    def g(*a, **kw):
        if not web.ctx.site.get_user():
            return login_redirect()
        return f(*a, **kw)

    return g

def login_redirect(path=None):
    if path is None:
        path = web.ctx.fullpath

    query = urllib.urlencode({"redirect":path})
    raise web.seeother("/account/login?" + query)

def permission_denied(error):
    return render.permission_denied(web.ctx.fullpath, error)
    
@public
def datestr(then, now=None):
    """Internationalized version of web.datestr"""
    
    # Examples:
    # 2 seconds from now
    # 2 microseconds ago
    # 2 milliseconds ago
    # 2 seconds ago
    # 2 minutes ago
    # 2 hours ago
    # 2 days ago
    # January 21
    # Jaunary 21, 2003
    
    result = web.datestr(then, now)
    _ = i18n.strings.get_namespace('/utils/date')
    
    import string
    if result[0] in string.digits: # eg: 2 milliseconds ago
        t, unit, ago = result.split(' ', 2)
        return "%s %s %s" % (t, _[unit], _[ago.replace(' ', '_')])
    else:
        month, rest = result.split(' ', 1)
        return "%s %s" % (_[month.lower()], rest)

@public
def get_types(regular=True):
    q = {'type': "/type/type", "sort": "key", "limit": 1000}
    if regular:
        q['kind'] = 'regular'
    return sorted(web.ctx.site.things(q))

def parse_db_url(dburl):
    """Parses db url and returns db parameters dictionary.

    >>> parse_db_url("sqlite:///test.db")
    {'dbn': 'sqlite', 'db': 'test.db'}
    >>> parse_db_url("postgres://joe:secret@dbhost:1234/test")
    {'pw': 'secret', 'dbn': 'postgres', 'db': 'test', 'host': 'dbhost', 'user': 'joe', 'port': '1234'}
    >>> parse_db_url("postgres://joe@/test")
    {'pw': '', 'dbn': 'postgres', 'db': 'test', 'user': 'joe'}

    Note: this should be part of web.py
    """
    rx = web.re_compile("""
        (?P<dbn>\w+)://
        (?:
            (?P<user>\w+)
            (?::(?P<pw>\w+))?
            @
        )?
        (?:
            (?P<host>\w+)
            (?::(?P<port>\w+))?
        )?
        /(?P<db>.*)
    """, re.X)
    m = rx.match(dburl)
    if m:
        d = m.groupdict()

        if d['host'] is None:
            del d['host']

        if d['port'] is None:
            del d['port']

        if d['pw'] is None:
            d['pw'] = ''

        if d['user'] is None:
            del d['user']
            del d['pw']

        return d
    else:
        raise ValueError("Invalid database url: %s" % repr(dburl))
    

########NEW FILE########
__FILENAME__ = migrate-0.4-0.5
"""Script to migrate data from 0.4 to 0.5
"""
from optparse import OptionParser
import os, sys
import web

DATATYPES = ["str", "int", "float", "boolean", "ref"]

def parse_args():
    parser = OptionParser("Usage: %s [options] db" % sys.argv[0])

    user = os.getenv('USER')
    parser.add_option("-u", "--user", dest="user", default=user, help="database username (default: %default)")
    parser.add_option("-H", "--host", dest="host", default='localhost', help="database host (default: %default)")
    parser.add_option("-p", "--password", dest="pw", default='', help="database password (default: %default)")

    (options, args) = parser.parse_args()
    
    if len(args) != 1:
        parser.error("incorrect number of arguments")

    web.config.db_parameters = dict(dbn='postgres', db=args[0], user=options.user, pw=options.pw, host=options.host)

db = None

PROPERTY_TABLE = """
create table property (
    id serial primary key,
    type int references thing,
    name text,
    unique(type, name)
);
"""

TRANSACTION_TABLE = """
create table transaction (
    id serial primary key,
    action varchar(256),
    author_id int references thing,
    ip inet,
    comment text,
    created timestamp default (current_timestamp at time zone 'utc')    
);
"""

TRANSACTION_INDEXES = """
create index transaction_author_id_idx ON transaction(author_id);
create index transaction_ip_idx ON transaction(ip);
create index transaction_created_idx ON transaction(created);
"""

#@@ type to table prefix mappings. 
#@@ If there are any special tables in your schema, this should be updated.
type2table = {

}

# exclusive properties. They are some property names, which can't occur with any other type.
exclusive_properties = {
    '/type/type': ['properties.name', 'properties.expected_type', 'properties.unique', 'properties.description', 'kind'],
    '/type/user': ['displayname'],
    '/type/usergroup': ['members'],
    '/type/permission': ['readers', 'writers', 'admins']
}

def get_table_prefix(type):
    """Returns table prefix for that type and a boolean flag to specify whether the table has more than one type.
    When the table as values only from a single type, then some of the queries can be optimized.
    """
    table = type2table.get(type, 'datum')
    multiple = (table == 'datum') or type2table.values().count(table) > 1    
    return table, multiple

def fix_property_keys():
    """In 0.4, property keys are stored in $prefix_keys table where as in 0.5
    they are stored in a single `property` which also has type column.
    
    for t in types:
        prefix = table_prefix(t)
        copy_
    """
    def fix_type(type, type_id):
        print >> web.debug, 'fixing type', type
        prefix, multiple_types = get_table_prefix(type)
        keys_table = prefix + "_keys"
        keys = dict((r.key, r.id) for r in db.query('SELECT * FROM ' + keys_table))
        newkeys = {}
        
        #@@ There is a chance that we may overwrite one update with another when new id is in the same range of old ids.
        #@@ Example:
        #@@     UPDATE datum_str SET key_id=4 FROM thing WHERE thing.id = property.type AND key_id=1;
        #@@     UPDATE datum_str SET key_id=6 FROM thing WHERE thing.id = property.type AND key_id=4;
        #@@ In the above example, the second query overwrites the result of first query.
        #@@ Making id of property table more than max_id of datum_keys makes sure that this case never happen.
        id1 = db.query('SELECT max(id) as x FROM ' + keys_table)[0].x
        id2 = db.query('SELECT max(id) as x FROM property')[0].x
        print >> web.debug, 'max ids', id1, id2
        if id1 > id2:
            db.query("SELECT setval('property_id_seq', $id1)", vars=locals())
        
        for key in keys:
            newkeys[key] = db.insert('property', type=type_id, name=key)
        
        total_updated = {}
        
        for d in ['str', 'int', 'float', 'boolean', 'ref']:
            table = prefix + '_' + d            
            print >> web.debug, 'fixing', type, table
            for key in keys:
                old_key_id = keys[key]
                new_key_id = newkeys[key]
                if multiple_types:
                    updated = db.query('UPDATE %s SET key_id=$new_key_id FROM thing WHERE thing.id = %s.thing_id AND thing.type=$type_id AND key_id=$old_key_id' % (table, table), vars=locals())
                else:
                    updated = db.update(table, key_id=new_key_id, where='key_id=$old_key_id', vars=locals())
                
                total_updated[key] = total_updated.get(key, 0) + updated
                print >> web.debug, 'updated', updated
                
        unused = [k for k in total_updated if total_updated[k] == 0]
        print >> web.debug, 'unused', unused
        db.delete('property', where=web.sqlors('id =', [newkeys[k] for k in unused]))
                
    primitive = ['/type/key', '/type/int', '/type/float', '/type/boolean', '/type/string', '/type/datetime']
    # add embeddable types too
    primitive += ['/type/property', '/type/backreference', '/type/link']
    types = dict((r.key, r.id) for r in db.query("SELECT * FROM thing WHERE type=1") if r.key not in primitive)
    
    for type in types:
        fix_type(type, types[type])
        
def drop_key_id_foreign_key():
    table_prefixes = set(type2table.values() + ['datum'])
    for prefix in table_prefixes:
        for d in DATATYPES:
            table = prefix + '_' + d
            db.query('ALTER TABLE %s DROP CONSTRAINT %s_key_id_fkey' % (table, table))

def add_key_id_foreign_key():
    table_prefixes = ['datum']
    for prefix in table_prefixes:
        for d in DATATYPES:
            table = prefix + '_' + d
            db.query('ALTER TABLE %s ADD CONSTRAINT %s_key_id_fkey FOREIGN KEY (key_id) REFERENCES property(id)'  % (table, table)) 
        
def get_datum_tables():
    prefixes = ["datum"]
    datatypes = ["str", "int", "float", "boolean", "ref"]
    return [p + "_" + d for p in prefixes for d in datatypes]
    
def process_keys(table):
    prefix = table.rsplit("_", 1)[0]
    keys_table = prefix + "_keys"
    
    result = db.query("SELECT type, key_id"
        + " FROM thing, %s as datum" % table
        + " WHERE thing.id=datum.thing_id"
        + " GROUP BY type, key_id")
        
    for r in result:
        print r
        
def fix_version_table():
    """Add transaction table and move columns from version table to transaction table."""
    filename = '/tmp/version.%d.txt' % os.getpid()
    new_filename = filename + ".new"
    db.query('copy version to $filename', vars=locals());
    cmd = """awk -F'\t' 'BEGIN {OFS="\t"}{if ($3 == 1) action = "create"; else action="update"; print $1,action, $4,$5,$6,$8; }' < %s > %s""" % (filename, new_filename)
    os.system(cmd)
    db.query(TRANSACTION_TABLE)
    db.query("copy transaction from $new_filename", vars=locals())
    db.query("SELECT setval('transaction_id_seq', (SELECT max(id) FROM transaction))")
    db.query('ALTER TABLE version add column transaction_id int references transaction')
    db.query('UPDATE version set transaction_id=id')
    db.query(TRANSACTION_INDEXES)
    os.system('rm %s %s' % (filename, new_filename))

def main():
    parse_args()
    global db
    db = web.database(**web.config.db_parameters)
    db.printing = True
    
    t = db.transaction()
    db.query(PROPERTY_TABLE)
    fix_version_table()
    
    drop_key_id_foreign_key()
    fix_property_keys()
    add_key_id_foreign_key()
    t.commit()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = sample_run
"""
Sample run.py
"""
import infogami

## your db parameters
infogami.config.db_parameters = dict(dbn='postgres', db="infogami", user='yourname', pw='')

## site name 
infogami.config.site = 'infogami.org'
infogami.config.admin_password = "admin123"

## add additional plugins and plugin path
#infogami.config.plugin_path += ['plugins']
#infogami.config.plugins += ['search']

def createsite():
    import web
    from infogami.infobase import dbstore, infobase, config, server
    web.config.db_parameters = infogami.config.db_parameters
    web.config.db_printing = True
    web.ctx.ip = '127.0.0.1'

    server.app.request('/')
    schema = dbstore.Schema()
    store = dbstore.DBStore(schema)
    ib = infobase.Infobase(store, config.secret_key)
    ib.create(infogami.config.site)

if __name__ == "__main__":
    import sys

    if '--schema' in sys.argv:
        from infogami.infobase.dbstore import Schema
        print Schema().sql()
    elif '--createsite' in sys.argv:
        createsite()
    else:
        infogami.run()


########NEW FILE########
__FILENAME__ = _init_path
"""Utility to setup sys.path.
"""

from os.path import abspath, dirname, pardir, join
import sys

INFOGAMI_PATH = abspath(join(dirname(__file__), pardir))
sys.path.insert(0, INFOGAMI_PATH)


########NEW FILE########
__FILENAME__ = bug_239238
"""Bug#239238

https://bugs.launchpad.net/infogami/+bug/239238

Change author of a book from a1 to a2.
That book is not listed in a2.books.
"""

import webtest
from test_infobase import InfobaseTestCase
from infogami.infobase import infobase, client

class Test(InfobaseTestCase):
    def create_site(self, name='test'):
        conn = client.connect(type='local')
        return client.Site(conn, 'test')

    def testBug(self):
        self.create_book_author_types()

        self.new('/a/a1', '/type/author')
        self.new('/a/a2', '/type/author')
        self.new('/b/b1', '/type/book', author='/a/a1')

        site = self.create_site()
        a1 = site.get('/a/a1')
        a2 = site.get('/a/a2')

        def keys(things):
            return [t.key for t in things]

        assert keys(a1.books) == ['/b/b1']
        assert keys(a2.books) == []

        site.write({
            'key': '/b/b1',
            'author': {
                'connect': 'update',
                'key': '/a/a2',
            }
        })

        site = self.create_site()
        a1 = site.get('/a/a1')
        a2 = site.get('/a/a2')
            
        assert keys(a1.books) == []
        assert keys(a2.books) == ['/b/b1']

if __name__ == "__main__":
    webtest.main()

########NEW FILE########
__FILENAME__ = test_all
import webtest

def suite():
    modules = ["test_doctests", "test_dbstore", "test_infobase"]
    return webtest.suite(modules)

if __name__ == "__main__":
    webtest.main()


########NEW FILE########
__FILENAME__ = test_dbstore
import sys
sys.path.insert(0, '.')

import unittest as webtest
import web
import os

from infogami.infobase import dbstore, infobase, common

class InfobaseTestCase(webtest.TestCase):
    def setUp(self):
        user = os.getenv('USER')


        web.config.db_parameters = dict(dbn='postgres', db='infobase_test', user=user, pw='')
        store = dbstore.DBStore(dbstore.Schema())
        self.t = store.db.transaction()
        store.db.printing = False

        self.ib = infobase.Infobase(store, 'secret')
        self.site = self.ib.create('test')

    def tearDown(self):
        self.t.rollback()

    def get_site_store(self):
        return self.ib.get('test')

class DBStoreTest(InfobaseTestCase):
    def testAdd(self):
        self.assertEquals(1+1, 2)

    def _test_save(self):
        store = self.get_site_store()

        d = dict(key='/x', type={'key': '/type/type'}, title='foo', x={'x': 1, 'y': 'foo'})
        store.save('/x', d)

        d = store.get('/x')._get_data()
        print d

        del d['title']
        d['body'] = 'bar'
        store.save('/x', d)

        print store.get('/x')._get_data()

class SaveTest(InfobaseTestCase):
    def testSave(self):
        d = dict(key='/foo', type='/type/object')
        assert self.site.save('/foo', d) == {'key': '/foo', 'revision': 1}

        d = dict(key='/foo', type='/type/object', x=1)
        assert self.site.save('/foo', d) == {'key': '/foo', 'revision': 2}
    
    def new(self, error=None, **d):
        try:
            key = d['key']
            self.assertEquals(self.site.save(key, d), {'key': key, 'revision': 1})
        except common.InfobaseException, e:
            self.assertEquals(str(e), error)
    
    def test_type(self):
        self.new(key='/a', type='/type/object')
        self.new(key='/b', type={'key': '/type/object'})
        self.new(key='/c', type='/type/noobject', error="Not Found: '/type/noobject'")
            
    def test_expected_type(self):
        def p(name, expected_type, unique=True):
            return locals()
        self.new(key='/type/test', type='/type/type', properties=[p('i', '/type/int'), p('s', '/type/string'), p('f', '/type/float'), p('t', '/type/type')])

        self.new(key='/a', type='/type/test', i='1', f='1.2', t='/type/test')
        self.new(key='/b', type='/type/test', i={'type': '/type/int', 'value': '1'}, f='1.2', t={'key': '/type/test'})
        self.new(key='/e1', type='/type/test', i='bad integer', error="invalid literal for int() with base 10: 'bad integer'")
        
    def test_embeddable_types(self):
        def test(key, type):
            self.new(key=key, type=type, link=dict(title='foo', link='http://infogami.org'))
            d = self.site.get('/a')._get_data()
            self.assertEquals(d['link']['title'], 'foo')
            self.assertEquals(d['link']['link'], 'http://infogami.org')
            
        def p(name, expected_type, unique=True, **d):
            return locals()                    
        self.new(key='/type/link', type='/type/type', properties=[p('title', '/type/string'), p('link', '/type/string')], kind='embeddable')
        self.new(key='/type/book', type='/type/type', properties=[p('link', '/type/link')])
        
        test('/a', '/type/object')
        test('/b', '/type/book')

    def test_things_with_embeddable_types(self):
        def link(title, url):
            return dict(title=title, url='http://example.com/' + url)
        self.new(key='/x', type='/type/object', links=[link('a', 'a'), link('b', 'b')])
        self.new(key='/y', type='/type/object', links=[link('a', 'b'), link('b', 'a')])

        def things(query, result):
            x = self.site.things(query)
            self.assertEquals(sorted(x), sorted(result))
        
        things({'type': '/type/object', 'links': {'title': 'a', 'url': 'http://example.com/a'}}, ['/x'])
        things({'type': '/type/object', 'links': {'title': 'a', 'url': 'http://example.com/b'}}, ['/y'])
        things({'type': '/type/object', 'links': {'title': 'a'}}, ['/x', '/y'])
        things({'type': '/type/object', 'links': {'url': 'http://example.com/a'}}, ['/x', '/y'])

if __name__ == "__main__":
    webtest.main()

########NEW FILE########
__FILENAME__ = test_doctests
"""Run all doctests in infogami.
"""
import webtest

def suite():
    modules = [
        "infogami.infobase.common",
        "infogami.infobase.readquery",
        "infogami.infobase.writequery",
        "infogami.infobase.dbstore",
    ]
    return webtest.doctest_suite(modules)
    
if __name__ == "__main__":
    webtest.main()

########NEW FILE########
__FILENAME__ = test_infobase
from infogami.infobase import server
import web

import unittest
import urllib, urllib2
import simplejson

def browser():
    if web.config.get('test_url'):
        b = web.browser.Browser()
        b.open('http://0.0.0.0:8080')
        return b
    else:
        return server.app.browser()

b = browser()

def request(path, method="GET", data=None, headers={}):
    if method == 'GET' and data is not None:
        path = path + '?' + urllib.urlencode(data)
        data = None
    if isinstance(data, dict):
        data = simplejson.dumps(data)
    url = urllib.basejoin(b.url, path)
    req = urllib2.Request(url, data, headers)
    req.get_method = lambda: method
    b.do_request(req)
    if b.status == 200:
        return b.data and simplejson.loads(b.data)
    else:
        return None

def get(key):
    d = request('/test/get?key=' + key)
    return d

def echo(msg):
    request('/_echo', method='POST', data=msg)

def save(query):
    return request('/test/save' + query['key'], method='POST', data=query)

def save_many(query, comment=''):
    return request('/test/save_many', method='POST', data=urllib.urlencode({'query': simplejson.dumps(query), 'comment': comment}))
        
class DatabaseTest(unittest.TestCase):
    pass
    
class InfobaseTestCase(unittest.TestCase):
    def clear_threadlocal(self):
        import threading
        t = threading.currentThread()
        if hasattr(t, '_d'):
            del t._d

    def setUp(self):
        self.clear_threadlocal()

        global b
        b = browser()
        try:
            # create new database with name "test"
            self.assertEquals2(request("/test", method="PUT"), {"ok": True})
        except Exception:
            self.tearDown()
            raise

        # reset browser cookies
        b.reset()

    def tearDown(self):
        self.clear_threadlocal()
        # delete test database
        request('/test', method="DELETE")

    def assertEquals2(self, a, b):
        """Asserts two objects are same.
        """
        # special case to say don't worry about this value.
        if b == '*':
            return True
        elif isinstance(a, dict):
            self.assertTrue(isinstance(b, dict))
            # key '*' means skip additional keys.
            skip_additional = b.pop('*', False)
            if not skip_additional:
                self.assertEquals(a.keys(), b.keys())
            for k in b.keys():
                self.assertEquals2(a[k], b[k])
        elif isinstance(a, list):
            self.assertEquals(len(a), len(b))
            for x, y in zip(a, b):
                self.assertEquals2(x, y)
        else:
            self.assertEquals(a, b)

class DocumentTest(InfobaseTestCase):
    def test_simple(self):
        self.assertEquals2(request('/'), {'infobase': 'welcome', 'version': '*'})
        self.assertEquals2(request('/test'), {'name': 'test'})
        self.assertEquals2(request('/test/get?key=/type/type'), {'key': '/type/type', 'type': {'key': '/type/type'}, '*': True})
        
        request('/test/get?key=/not-there')
        self.assertEquals(b.status, 404)
        
    def test_save(self):
        x = {'key': '/new_page', 'type': {'key': '/type/object'}, 'x': 1, 's': 'hello'}
        d = request('/test/save/new_page', method="POST", data=x)
        self.assertEquals(b.status, 200)
        self.assertEquals(d, {'key': '/new_page', 'revision': 1})
        
        # verify data
        d = request('/test/get?key=/new_page')
        expected = dict({'latest_revision': 1, 'revision': 1, '*': True}, **d)
        self.assertEquals2(d, expected)

        # nothing should be modified when saved with the same data.
        d = request('/test/save/new_page', method="POST", data=x)
        self.assertEquals(b.status, 200)
        self.assertEquals(d, {})

    def test_versions(self):
        x = {'key': '/new_page', 'type': {'key': '/type/object'}, 'x': 1, 's': 'hello'}
        d = request('/test/save/new_page', method="POST", data=x)

        # verify revisions
        q = {'key': '/new_page'}
        d = request('/test/versions', method='GET', data={'query': simplejson.dumps({'key': '/new_page'})}) 
        self.assertEquals2(d, [{'key': '/new_page', 'revision': 1, '*': True}])

        d = request('/test/versions', method='GET', data={'query': simplejson.dumps({'limit': 1})}) 
        self.assertEquals2(d, [{'key': '/new_page', 'revision': 1, '*': True}])
        
        # try a failed save and make sure new revisions are not created
        request('/test/save/new_page', method='POST', data={'key': '/new_page', 'type': '/type/no-such-type'})
        self.assertNotEquals(b.status, 200)

        q = {'key': '/new_page'}
        d = request('/test/versions', method='GET', data={'query': simplejson.dumps({'key': '/new_page'})}) 
        self.assertEquals2(d, [{'key': '/new_page', 'revision': 1, '*': True}])

        d = request('/test/versions', method='GET', data={'query': simplejson.dumps({'limit': 1})}) 
        self.assertEquals2(d, [{'key': '/new_page', 'revision': 1, '*': True}])

        # save the page and make sure new revision is created.
        d = request('/test/save/new_page', method='POST', data=dict(x, title='foo'))
        self.assertEquals(d, {'key': '/new_page', 'revision': 2})

        d = request('/test/versions', method='GET', data={'query': simplejson.dumps({'key': '/new_page'})}) 
        self.assertEquals2(d, [{'key': '/new_page', 'revision': 2, '*': True}, {'key': '/new_page', 'revision': 1, '*': True}])

    def test_save_many(self):
        q = [
            {'key': '/one', 'type': {'key': '/type/object'}, 'n': 1},
            {'key': '/two', 'type': {'key': '/type/object'}, 'n': 2}
        ]
        d = request('/test/save_many', method='POST', data=urllib.urlencode({'query': simplejson.dumps(q)}))
        self.assertEquals(d, [{'key': '/one', 'revision': 1}, {'key': '/two', 'revision': 1}])

        self.assertEquals2(get('/one'), {'key': '/one', 'type': {'key': '/type/object'}, 'n': 1, 'revision': 1,'*': True})
        self.assertEquals2(get('/two'), {'key': '/two', 'type': {'key': '/type/object'}, 'n': 2, 'revision': 1, '*': True})

        # saving with same data should not create new revisions
        d = request('/test/save_many', method='POST', data=urllib.urlencode({'query': simplejson.dumps(q)}))
        self.assertEquals(d, [])

        # try bad query
        q = [
            {'key': '/zero', 'type': {'key': '/type/object'}, 'n': 0},
            {'key': '/one', 'type': {'key': '/type/object'}, 'n': 11},
            {'key': '/two', 'type': {'key': '/type/no-such-type'}, 'n': 2}
        ]
        d = request('/test/save_many', method='POST', data=urllib.urlencode({'query': simplejson.dumps(q)}))
        self.assertNotEquals(b.status, 200)

        d = get('/zero')
        self.assertEquals(b.status, 404)

# create author, book and collection types to test validations
types = [{
    "key": "/type/author",
    "type": "/type/type",
    "kind": "regular",
    "properties": [{
        "name": "name",
        "expected_type": {"key": "/type/string"},
        "unique": True
    }, {
        "name": "bio",
        "expected_type": {"key": "/type/text"},
        "unique": True
    }]
}, {
    "key": "/type/book",
    "type": "/type/type",
    "kind": "regular",
    "properties": [{
        "name": "title",
        "expected_type": {"key": "/type/string"},
        "unique": True
    }, {
        "name": "authors",
        "expected_type": {"key": "/type/author"},
        "unique": False
    }, {
        "name": "publisher",
        "expected_type": {"key": "/type/string"},
        "unique": True
    }, {
        "name": "description",
        "expected_type": {"key": "/type/text"},
        "unique": True
    }]
}, {
    "key": "/type/collection",
    "type": "/type/type",
    "kind": "regular",
    "properties": [{
        "name": "name",
        "expected_type": {"key": "/type/string"},
        "unique": True
    }, {
        "name": "books",
        "expected_type": {"key": "/type/book"},
        "unique": False
    }]
}]

class MoreDocumentTest(DocumentTest):
    def setUp(self):
        DocumentTest.setUp(self)
        save_many(types)

    def test_save_validation(self):
        # ok: name is string
        d = save({'key': '/author/x', 'type': '/type/author', 'name': 'x'})
        self.assertEquals(b.status, 200)
        self.assertEquals(d, {"key": "/author/x", "revision": 1})
        
        # error: name is int instead of string
        d = save({'key': '/author/x', 'type': '/type/author', 'name': 42})
        self.assertEquals(b.status, 400)

        # error: name is list instead of single value
        d = save({'key': '/author/x', 'type': '/type/author', 'name': ['x', 'y']})
        self.assertEquals(b.status, 400)

    def test_validation_when_type_changes(self):
        # create an author and a book
        save({'key': '/author/x', 'type': '/type/author', 'name': 'x'})
        save({'key': '/book/x', 'type': '/type/book', 'title': 'x', 'authors': [{'key': '/author/x'}], 'publisher': 'publisher_x'})

        # change schema of "/type/book" and make expected_type of "publisher" as "/type/publisher"
        save({
            "key": "/type/publisher",
            "type": "/type/type",
            "kind": "regular",
            "properties": [{
                "name": "name",
                "expected_type": "/type/string",
                "unique": True
             }]
        })

        d = get('/type/book')
        assert d['properties'][2]['name'] == "publisher"
        d['properties'][2]['expected_type'] = {"key": "/type/publisher"}
        save(d)

        # now changing just the title of the book should not fail.
        d = get('/book/x')
        d['title'] = 'xx'
        save(d)
        self.assertEquals(b.status, 200)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = webtest
"""webtest: test utilities.
"""
import sys, os
# adding current directory to path to make sure local copy of web module is used.
sys.path.insert(0, '.')

import unittest

from infogami.utils import delegate
import web
import infogami
from web.browser import Browser

web.config.debug = False
infogami.config.site = 'infogami.org'

class TestCase(unittest.TestCase):
    def setUp(self):
        from infogami.infobase import server
        db = server.get_site('infogami.org').store.db
        
        self._t = db.transaction()

    def tearDown(self):
        self._t.rollback()
        
    def browser(self):
        return Browser(delegate.app)

def runTests(suite):
    runner = unittest.TextTestRunner()
    return runner.run(suite)
    
def main(suite=None):
    user = os.getenv('USER')
    web.config.db_parameters = dict(dbn='postgres', db='infogami_test', user=user, pw='')
    web.load()

    delegate.app.request('/')
    delegate._load()
    
    if not suite:
        main_module = __import__('__main__')
        suite = module_suite(main_module, sys.argv[1:] or None)
    
    result = runTests(suite)    
    sys.exit(not result.wasSuccessful())

def suite(module_names):
    """Creates a suite from multiple modules."""
    suite = unittest.TestSuite()
    for mod in load_modules(module_names):
        suite.addTest(module_suite(mod))
    return suite
    
def doctest_suite(module_names):
    """Makes a test suite from doctests."""
    import doctest
    suite = unittest.TestSuite()
    for mod in load_modules(module_names):
        suite.addTest(doctest.DocTestSuite(mod))
    return suite

def load_modules(names):
    return [__import__(name, None, None, "x") for name in names]

def module_suite(module, classnames=None):
    """Makes a suite from a module."""
    if hasattr(module, 'suite'):
        return module.suite()
    elif classnames:
        return unittest.TestLoader().loadTestsFromNames(classnames, module)
    else:
        return unittest.TestLoader().loadTestsFromModule(module)

def with_debug(f):
    """Decorator to enable debug prints."""
    def g(*a, **kw):
        db_printing = web.config.get('db_printing')
        web.config.db_printing = True
        
        try:
            return f(*a, **kw)
        finally:
            web.config.db_printing = db_printing
    return g

########NEW FILE########
__FILENAME__ = test_doctests
import web
import doctest, unittest

def add_doctests(suite):
    """create one test_xx function in globals for each doctest in the given module.
    """
    suite = web.test.make_doctest_suite()

    add_test(make_suite(module))

def add_test(test):
    if isinstance(test, unittest.TestSuite):
        for t in test._tests:
            add_test(t)
    elif isinstance(test, unittest.TestCase):
        test_method = getattr(test, test._testMethodName)
        def do_test(test_method=test_method):
            test_method()
        name = "test_" + test.id().replace(".", "_")
        globals()[name] = do_test
    else:
        doom

modules = [
    "infogami.core.code",
    "infogami.core.helpers",
    "infogami.utils.app",
    "infogami.utils.i18n",
    "infogami.utils.storage",
    "infogami.infobase.common",
    "infogami.infobase.client",
    "infogami.infobase.dbstore",
    "infogami.infobase.lru",
    "infogami.infobase.readquery",
    "infogami.infobase.utils",
    "infogami.infobase.writequery",
]
suite = web.test.doctest_suite(modules)
add_test(suite)

########NEW FILE########
__FILENAME__ = test_account
from infogami.utils.delegate import app
import web

b = app.browser()

def test_login():
    # try with bad account
    b.open('/account/login')   
    b.select_form(name="login")
    b['username'] = 'joe'
    b['password'] = 'secret'

    try:
        b.submit() 
    except web.BrowserError, e:
        assert str(e) == 'Invalid username or password'
    else:
        assert False, 'Expected exception'

    # follow register link
    b.follow_link(text='create a new account')
    assert b.path == '/account/register'

    b.select_form('register')
    b['username'] = 'joe'
    b['displayname'] = 'Joe'
    b['password'] = 'secret'
    b['password2'] = 'secret'
    b['email'] = 'joe@example.com'
    b.submit()
    assert b.path == '/'


########NEW FILE########
__FILENAME__ = test_pages
import web
import simplejson
import urllib

from infogami.utils.delegate import app

b = app.browser()

def test_home():
    b.open('/')
    b.status == 200

def test_write():
    b.open('/sandbox/test?m=edit')
    b.select_form(name="edit")
    b['title'] = 'Foo'
    b['body'] = 'Bar'
    b.submit()
    assert b.path == '/sandbox/test'

    b.open('/sandbox/test')
    assert 'Foo' in b.data
    assert 'Bar' in b.data

def test_delete():
    b.open('/sandbox/delete?m=edit')
    b.select_form(name="edit")
    b['title'] = 'Foo'
    b['body'] = 'Bar'
    b.submit()
    assert b.path == '/sandbox/delete'

    b.open('/sandbox/delete?m=edit')
    b.select_form(name="edit")
    try:
        b.submit(name="_delete")
    except web.BrowserError, e:
        pass
    else:
        assert False, "expected 404"

def test_notfound():
    try:
        b.open('/notthere')
    except web.BrowserError:
        assert b.status == 404

def test_recent_changes():
    b.open('/recentchanges')

def save(key, **data):
    b.open(key + '?m=edit')
    b.select_form(name="edit")
    
    if "type" in data:
        data['type.key'] = [data.pop('type')]
        
    for k, v in data.items():
        b[k] = v
    b.submit()
    
def query(**kw):
    url = '/query.json?' + urllib.urlencode(kw)
    return [d['key'] for d in simplejson.loads(b.open(url).read())]

def test_query():
    save('/test_query_1', title="title 1", body="body 1", type="/type/page")
    assert query(type='/type/page', title='title 1') == ['/test_query_1']
    
    save('/test_query_1', title="title 2", body="body 1", type="/type/page")
    assert query(type='/type/page', title='title 1') == []
    
########NEW FILE########
