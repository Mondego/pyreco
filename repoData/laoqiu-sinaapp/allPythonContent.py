__FILENAME__ = fcgi
#!/usr/bin/env python
from webapp import create_app

app = create_app('config.cfg')

from flup.server.fcgi import WSGIServer
WSGIServer(app,bindAddress='/tmp/webapp.sock').run()

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
#coding=utf-8

from flask import Flask, current_app
from flaskext.script import Server, Shell, Manager, Command

from webapp import create_app
from webapp.extensions import db

manager = Manager(create_app('config.cfg'))

manager.add_command("runserver", Server('0.0.0.0',port=80))

def _make_context():
    return dict(db=db)
manager.add_command("shell", Shell(make_context=_make_context))

@manager.command
def createall():
    "Creates database tables"
    db.create_all()

@manager.command
def dropall():
    "Drops all database tables"
    
    if prompt_bool("Are you sure ? You will lose all your data !"):
        db.drop_all()

if __name__ == "__main__":
    manager.run()

########NEW FILE########
__FILENAME__ = extensions
#!/usr/bin/env python
#coding=utf-8

from flaskext.mail import Mail
from flaskext.sqlalchemy import SQLAlchemy
from flaskext.cache import Cache
from flaskext.uploads import UploadSet, IMAGES

__all__ = ['mail', 'db', 'cache', 'photos']

mail = Mail()
db = SQLAlchemy()
cache = Cache()
photos = UploadSet('photos', IMAGES)

sina_api = {'taoke':('1899693215',
                     '4a72b1939c0f674257a618b8174e7dda',
                     'http://viimii.li/auth/sina/taoke/callback'),
            }

#qq_api = ('782500852',
#          '16b76b86be7f5975afbbbeb9a66a9cc3',
#          'http://localhost:8080/auth/qq/callback')


# appkey = (key, secret, nick)
appkey = ('12360***', '8cbafd956c0fb4a59b2127c3db87***', u"老秋")
          
myappkey = ('1235***', 'f07159fbf91f4585ea6b93a2bd40***', u"老秋")
          


########NEW FILE########
__FILENAME__ = taoke
#!/usr/bin/env python
#coding=utf-8

"""
    forms/tweets.py
    ~~~~~~~~~~~~~
    :license: BSD, see LICENSE for more details.
"""

from flask import g

from flaskext.wtf import Form, TextField, PasswordField, HiddenField, \
    BooleanField, RadioField, RecaptchaField, TextAreaField, SubmitField, \
    DateField, DateTimeField, FileField, SelectField, ValidationError,\
    required, email, equal_to, url, optional, regexp, length, validators

is_num = regexp(r'^\d{0,12}$', message=u"请填写整数")

class CashForm(Form):
    
    alipay = TextField(u"支付宝账户",validators=[
                required(message=u"请填写支付宝邮箱地址"), 
                email(message=u"邮箱格式错误")])

    money = TextField(u"提现金额", validators=[
                required(message=u"请填写您要提现的金额"),
                is_num])

    submit = SubmitField(u"提交")
    
    hidden = HiddenField()


########NEW FILE########
__FILENAME__ = tweets
#!/usr/bin/env python
#coding=utf-8

"""
    forms/tweets.py
    ~~~~~~~~~~~~~
    :license: BSD, see LICENSE for more details.
"""

from flask import g

from flaskext.wtf import Form, TextField, PasswordField, HiddenField, \
    BooleanField, RadioField, RecaptchaField, TextAreaField, SubmitField, \
    DateField, DateTimeField, FileField, SelectField, ValidationError,\
    required, email, equal_to, url, optional, regexp, length, validators

is_num = regexp(r'^\d{0,12}$', message=u"请填写数字")

class CashForm(Form):
    
    alipay = TextField(u"支付宝账户",validators=[
                required(message=u"请填写支付宝邮箱地址"), 
                email(message=u"邮箱格式错误")])

    money = TextField(u"提现金额", validators=[
                required(message=u"请填写您要提现的金额"),
                is_num])

    submit = SubmitField()
    
    hidden = HiddenField()


########NEW FILE########
__FILENAME__ = helpers
#!/usr/bin/env python
#coding=utf-8
"""
    helpers.py
    ~~~~~~~~~~~~~
    :license: BSD, see LICENSE for more details.
"""

import re
import markdown
import urlparse
import functools
import hashlib
import string

from datetime import datetime

from flask import current_app, g
from flaskext.babel import gettext, ngettext, format_date, format_datetime

from webapp.extensions import cache

class Storage(dict):
    """
    A Storage object is like a dictionary except `obj.foo` can be used
    in addition to `obj['foo']`.
    >>> o = storage(a=1)
    >>> o.a
    1
    >>> o['a']
    1
    >>> o.a = 2
    >>> o['a']
    2
    >>> del o.a
    >>> o.a
    Traceback (most recent call last):
    ...
    AttributeError: 'a'
    """
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError, k:
            raise AttributeError, k
    
    def __setattr__(self, key, value):
        self[key] = value
    
    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError, k:
            raise AttributeError, k
    
    def __repr__(self):
        return '<Storage ' + dict.__repr__(self) + '>'

storage = Storage

_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')

def slugify(text, delim=u'-'):
    """Generates an ASCII-only slug. From http://flask.pocoo.org/snippets/5/"""
    result = []
    for word in _punct_re.split(text.lower()):
        #word = word.encode('translit/long')
        if word:
            result.append(word)
    return unicode(delim.join(result))

markdown = functools.partial(markdown.markdown,
                             safe_mode='remove',
                             output_format="html")

cached = functools.partial(cache.cached,
                           unless= lambda: g.user is not None)

def request_wants_json(request):
    # we only accept json if the quality of json is greater than the
    # quality of text/html because text/html is preferred to support
    # browsers that accept on */*
    best = request.accept_mimetypes \
        .best_match(['application/json', 'text/html'])
    return best == 'application/json' and \
       request.accept_mimetypes[best] > request.accept_mimetypes['text/html']

def timesince(dt, default=None):
    """
    Returns string representing "time since" e.g.
    3 days ago, 5 hours ago etc.
    """
    
    if default is None:
        default = gettext("just now")

    now = datetime.utcnow()
    diff = now - dt

    years = diff.days / 365
    months = diff.days / 30
    weeks = diff.days / 7
    days = diff.days
    hours = diff.seconds / 3600
    minutes = diff.seconds / 60
    seconds = diff.seconds 

    periods = (
        (years, ngettext("%(num)s year", "%(num)s years", num=years)),
        (months, ngettext("%(num)s month", "%(num)s months", num=months)),
        (weeks, ngettext("%(num)s week", "%(num)s weeks", num=weeks)),
        (days, ngettext("%(num)s day", "%(num)s days", num=days)),
        (hours, ngettext("%(num)s hour", "%(num)s hours", num=hours)),
        (minutes, ngettext("%(num)s minute", "%(num)s minutes", num=minutes)),
        (seconds, ngettext("%(num)s second", "%(num)s seconds", num=seconds)),
    )

    for period, trans in periods:
        if period:
            return gettext("%(period)s ago", period=trans)

    return default

def domain(url):
    """
    Returns the domain of a URL e.g. http://reddit.com/ > reddit.com
    """
    rv = urlparse.urlparse(url).netloc
    if rv.startswith("www."):
        rv = rv[4:]
    return rv

def shorten(origin):
    """ 加密转成短地址 """
    chars = list(string.letters + string.digits)
    hex = hashlib.md5(origin).hexdigest() 
  
    #把加密字符的16进制与0x3FFFFFFF进行位与运算  
    hexint = 0x3FFFFFFF & int("0x" + hex, 16)  
    outChars = ""
    for j in range(6):
        #把得到的值与0x0000003D进行位与运算，取得字符数组chars索引  
        index = 0x0000003D & hexint
        #把取得的字符相加  
        outChars += chars[index]
        #每次循环按位右移5位
        hexint = hexint >> 5
    
    return outChars



########NEW FILE########
__FILENAME__ = taoke
#!/usr/bin/env python
#coding=utf-8
"""
    taoke.py
    ~~~~~~~~~~~~~
    :copyright: (c) 2011 by Laoqiu(laoqiu.com@gmail.com).
    :license: BSD, see LICENSE for more details.
"""

import hashlib

from datetime import datetime

from werkzeug import cached_property

from flask import abort, current_app

from flaskext.sqlalchemy import BaseQuery
#from flaskext.principal import RoleNeed, UserNeed, Permission

#from types import DenormalizedText

from webapp.extensions import db
from webapp.permissions import moderator_permission, admin_permission


class TaokeReport(db.Model):
    
    __tablename__ = "taoke_reports"
    
    PER_PAGE = 20
    
    id = db.Column(db.Integer, primary_key=True)
    outer_code = db.Column(db.String(12), index=True)   # 6位一个用户shorten
    trade_id = db.Column(db.String(20))
    num_iid = db.Column(db.String(50))
    item_title = db.Column(db.String(200))
    item_num = db.Column(db.Integer)
    shop_title = db.Column(db.String(50))
    seller_nick = db.Column(db.String(50))
    pay_time = db.Column(db.DateTime)
    pay_price = db.Column(db.Numeric(9,2))
    real_pay_fee = db.Column(db.Numeric(9,2))           # 实际支付金额
    commission = db.Column(db.Numeric(9,2))             # 用户获得拥金
    commission_rate = db.Column(db.String(10))          # 拥金比率
    
    __mapper_args__ = {'order_by': id.desc()}
    
    def __init__(self, *args, **kwargs):
        super(TaokeReport, self).__init__(*args, **kwargs)

    def __str__(self):
        return u"%s: %s" % (self.trand_id, self.item_title)

    def __repr__(self):
        return "<%s>" % self


class FinanceRecord(db.Model):
    
    __tablename__ = "finance_records"

    PER_PAGE = 20

    BUY = 100       # 购买
    COMM = 200      # 推荐成功
    EXTRACT = 300   # 提取

    WAIT = 100
    SUCCESS = 200
    
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.Integer(3), nullable=False) #BUY, COMM, EXTRACT
    money = db.Column(db.Numeric(9,2)) # 支出(EXTRACT)为负数
    status = db.Column(db.Integer(3), default=WAIT) # WAIT, SUCCESS
    created_date = db.Column(db.DateTime, default=datetime.now)
    
    report_id = db.Column(db.Integer,
                          db.ForeignKey('taoke_reports.id', ondelete='CASCADE'))
    
    report = db.relation('TaokeReport', backref='finance_records')

    user_id = db.Column(db.Integer,
                        db.ForeignKey('users.id', ondelete='CASCADE'))

    user = db.relation('User', backref='finance_records')

    def __init__(self, *args, **kwargs):
        super(FinanceRecord, self).__init__(*args, **kwargs)

    def __str__(self):
        return u"%s: %s" % (self.user_id, self.money)
    
    def __repr__(self):
        return "<%s>" % self
    
    @cached_property
    def name(self):
        data = {100: u"购买商品",
                200: u"推荐分成",
                300: u"提现"}
        return data.get(self.source, u'未知方式')
     
    @cached_property
    def get_status(self):
        data = {100: u"等待处理",
                200: u"成功"}
        return data.get(self.status, u'无状态')


########NEW FILE########
__FILENAME__ = types
#!/usr/bin/env python
#coding=utf-8
"""
    types.py
    ~~~~~~~~~~~~~
    :license: BSD, see LICENSE for more details.
"""

from sqlalchemy import types

class DenormalizedText(types.MutableType, types.TypeDecorator):
    """
    Stores denormalized primary keys that can be 
    accessed as a set. 

    :param coerce: coercion function that ensures correct
                   type is returned

    :param separator: separator character
    """

    impl = types.Text

    def __init__(self, coerce=int, separator=" ", **kwargs):

        self.coerce = coerce
        self.separator = separator
        
        super(DenormalizedText, self).__init__(**kwargs)

    def process_bind_param(self, value, dialect):
        if value is not None:
            items = [str(item).strip() for item in value]
            value = self.separator.join(item for item in items if item)
        return value

    def process_result_value(self, value, dialect):
         if not value:
            return set()
         return set(self.coerce(item) \
                   for item in value.split(self.separator))
        
    def copy_value(self, value):
        return set(value)


########NEW FILE########
__FILENAME__ = users
#!/usr/bin/env python
#coding=utf-8
"""
    users.py
    ~~~~~~~~~~~~~
    :copyright: (c) 2011 by Laoqiu(laoqiu.com@gmail.com).
    :license: BSD, see LICENSE for more details.
"""

import hashlib

from datetime import datetime

from werkzeug import cached_property

from flask import abort, current_app

from flaskext.sqlalchemy import BaseQuery
from flaskext.principal import RoleNeed, UserNeed, Permission

#from types import DenormalizedText

from webapp.extensions import db

from webapp.permissions import moderator_permission, admin_permission


class UserQuery(BaseQuery):

    def from_identity(self, identity):
        """
        Loads user from flaskext.principal.Identity instance and
        assigns permissions from user.

        A "user" instance is monkeypatched to the identity instance.

        If no user found then None is returned.
        """

        try:
            user = self.get(int(identity.name))
        except ValueError:
            user = None

        if user:
            identity.provides.update(user.provides)

        identity.user = user

        return user
    
    def authenticate(self, login, password):        
        user = self.filter(db.or_(User.nickname==login,User.email==login))\
                   .filter(User.blocked==False).first()
        if user:
            authenticated = user.check_password(password)
        else:
            authenticated = False
        return user, authenticated   
     
    def search(self, key):
        query = self.filter(db.or_(User.email==key,
                                   User.nickname.ilike('%'+key+'%'),
                                   User.username.ilike('%'+key+'%'))) \
                    .filter(User.blocked==False)
        return query


class User(db.Model):

    __tablename__ = 'users'
    
    query_class = UserQuery
    
    MEMBER = 100
    MODERATOR = 200
    ADMIN = 300
    
    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    alipay = db.Column(db.String(100))
    shorten = db.Column(db.String(6), unique=True)
    _password = db.Column("password", db.String(40), nullable=False)
    money = db.Column(db.Numeric(9,2), default=0.0) # 返利余额
    role = db.Column(db.Integer, default=MEMBER)
    receive_email = db.Column(db.Boolean, default=False)
    email_alerts = db.Column(db.Boolean, default=False)
    activation_key = db.Column(db.String(40))
    created_date = db.Column(db.DateTime, default=datetime.now)
    last_login = db.Column(db.DateTime, default=datetime.now)
    blocked = db.Column(db.Boolean, default=False)
    
    profile = db.relation('UserProfile', backref='user', uselist=False)

    class Permissions(object):
        
        def __init__(self, obj):
            self.obj = obj
    
        @cached_property
        def send_message(self):
            if not self.receive_email:
                return null

            return admin_permission & moderator_permission
        
        @cached_property
        def edit(self):
            return Permission(UserNeed(self.obj.id)) & admin_permission
  
    def __init__(self, *args, **kwargs):
        super(User, self).__init__(*args, **kwargs)

    def __str__(self):
        return u"%s" % self.nickname
    
    def __repr__(self):
        return "<%s>" % self
    
    @cached_property
    def permissions(self):
        return self.Permissions(self)
  
    def _get_password(self):
        return self._password
    
    def _set_password(self, password):
        self._password = hashlib.md5(password).hexdigest()
    
    password = db.synonym("_password", 
                          descriptor=property(_get_password,
                                              _set_password))

    def check_password(self,password):
        if self.password is None:
            return False        
        return self.password == hashlib.md5(password).hexdigest()
    
    @cached_property
    def provides(self):
        needs = [RoleNeed('authenticated'),
                 UserNeed(self.id)]

        if self.is_moderator:
            needs.append(RoleNeed('moderator'))

        if self.is_admin:
            needs.append(RoleNeed('admin'))

        return needs
    
    @property
    def is_moderator(self):
        return self.role >= self.MODERATOR

    @property
    def is_admin(self):
        return self.role >= self.ADMIN


class UserProfile(db.Model):
    
    __tablename__ = 'user_profiles'

    PER_PAGE = 20
    
    user_id = db.Column(db.Integer, 
                        db.ForeignKey('users.id', ondelete='CASCADE'),
                        primary_key=True) 
    
    gender = db.Column(db.String(1), default='n') #n, m, f
    description = db.Column(db.String(100))
    image_url = db.Column(db.String(100))
    url = db.Column(db.String(100))
    followers_count = db.Column(db.Integer)
    verified = db.Column(db.Boolean, default=False)
    location = db.Column(db.String(20))
    updatetime = db.Column(db.DateTime, default=datetime.now, 
                                        onupdate=datetime.now)
    
    def __init__(self, *args, **kwargs):
        super(UserProfile, self).__init__(*args, **kwargs)
    
    def __str__(self):
        return self.user_id
    
    def __repr__(self):
        return "<%s>" % self

    @property
    def get_city(self):
        r = self.city if self.city else self.province
        return r if r else ''


class UserMapper(db.Model):
    """ 微博用户授权信息
        source: sina, qq
        app: 我们下面将会有多个app
    """
    
    __tablename__ = "user_mappers"
    
    id = db.Column(db.Integer, primary_key=True)
    access_token = db.Column(db.String(255))
    access_secret = db.Column(db.String(255))
    source = db.Column(db.String(50))
    app = db.Column(db.String(10)) # taoke, 
    
    user_id = db.Column(db.Integer,
                        db.ForeignKey('users.id', ondelete='CASCADE'))

    user = db.relation('User', backref='mappers')
    
    def __init__(self, *args, **kwargs):
        super(UserMapper, self).__init__(*args, **kwargs)

    def __str__(self):
        return u"%s - %s(%s)" % (self.user_id, self.app, self.source)
    
    def __repr__(self):
        return "<%s>" % self
    
    
def bind(self, source, app, token, secret):
    
    mapper = UserMapper.query.filter(db.and_(UserMapper.user_id==self.id,
                                             UserMapper.source==source,
                                             UserMapper.app==app)) \
                             .first()
    if mapper is None:
        mapper = UserMapper(user_id=self.id, 
                            source=source,
                            app=app)

    mapper.access_token = token
    mapper.access_secret = secret

    self.mappers.append(mapper)

    db.session.commit()


def unbind(self, source, app):
    mapper = UserMapper.query.filter(db.and_(UserMapper.user_id==self.id,
                                             UserMapper.source==source,
                                             UserMapper.app==app)).first()

    if mapper:
        db.session.delete(mapper)
        db.session.commit()


User.bind = bind
User.unbind = unbind


########NEW FILE########
__FILENAME__ = permissions
#! /usr/bin/env python
#coding=utf-8
from flaskext.principal import RoleNeed, Permission

admin_permission = Permission(RoleNeed('admin'))
moderator_permission = Permission(RoleNeed('moderator'))
auth_permission = Permission(RoleNeed('authenticated'))

# this is assigned when you want to block a permission to all
# never assign this role to anyone !
null_permission = Permission(RoleNeed('null'))

########NEW FILE########
__FILENAME__ = gzipSupport
#!/usr/bin/env python
#coding=utf-8

"""
    yoryu member update
    ~~~~~~~~~~~~~

    :copyright: (c) 2010 by Laoqiu.
    :license: BSD, see LICENSE for more details.
"""

import urllib2
import zlib

from gzip import GzipFile
from StringIO import StringIO

class ContentEncodingProcessor(urllib2.BaseHandler):
    """A handler to add gzip capabilities to urllib2 requests """
 
    # add headers to requests
    def http_request(self, req):
        req.add_header("Accept-Encoding", "gzip, deflate")
        return req
 
    # decode
    def http_response(self, req, resp):
        old_resp = resp
        # gzip
        if resp.headers.get("content-encoding") == "gzip":
            gz = GzipFile(
                    fileobj=StringIO(resp.read()),
                    mode="r"
                    )
            resp = urllib2.addinfourl(gz, old_resp.headers, old_resp.url, old_resp.code)
            resp.msg = old_resp.msg
        # deflate
        if resp.headers.get("content-encoding") == "deflate":
            gz = StringIO(deflate(resp.read()))
            resp = urllib2.addinfourl(gz, old_resp.headers, old_resp.url, old_resp.code) 
            resp.msg = old_resp.msg
        return resp
 
# deflate support

def deflate(data): 
    try:
        return zlib.decompress(data, -zlib.MAX_WBITS)
    except zlib.error:
        return zlib.decompress(data)

########NEW FILE########
__FILENAME__ = models
#!/usr/bin/env python
#coding=utf-8
"""
    models.py
    ~~~~~~~~~~~~~
    :license: BSD, see LICENSE for more details.
"""

import hashlib
from datetime import datetime
from mydb import SQLAlchemy, BaseQuery, DenormalizedText

db = SQLAlchemy('mysql://root@localhost/yoro_dev?charset=utf8')


class User(db.Model):

    __tablename__ = 'users'
    
    #query_class = UserQuery
    
    MEMBER = 100
    MODERATOR = 200
    ADMIN = 300
    
    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    alipay = db.Column(db.String(100))
    shorten = db.Column(db.String(6), unique=True)
    _password = db.Column("password", db.String(40), nullable=False)
    money = db.Column(db.Numeric(9,2), default=0.0) # 返利余额
    role = db.Column(db.Integer, default=MEMBER)
    receive_email = db.Column(db.Boolean, default=False)
    email_alerts = db.Column(db.Boolean, default=False)
    activation_key = db.Column(db.String(40))
    created_date = db.Column(db.DateTime, default=datetime.now)
    last_login = db.Column(db.DateTime, default=datetime.now)
    blocked = db.Column(db.Boolean, default=False)
    
    #profile = db.relation('UserProfile', backref='user', uselist=False)

    def __init__(self, *args, **kwargs):
        super(User, self).__init__(*args, **kwargs)

    def __str__(self):
        return u"%s" % self.nickname
    
    def __repr__(self):
        return "<%s>" % self
  
    def _get_password(self):
        return self._password
    
    def _set_password(self, password):
        self._password = hashlib.md5(password).hexdigest()
    
    password = db.synonym("_password", 
                          descriptor=property(_get_password,
                                              _set_password))

    def check_password(self,password):
        if self.password is None:
            return False        
        return self.password == hashlib.md5(password).hexdigest()


class TaokeReport(db.Model):
    
    __tablename__ = "taoke_reports"
    
    PER_PAGE = 20
    
    id = db.Column(db.Integer, primary_key=True)
    outer_code = db.Column(db.String(12), index=True)   # 6位一个用户shorten
    trade_id = db.Column(db.String(20))
    num_iid = db.Column(db.String(50))
    item_title = db.Column(db.String(200))
    item_num = db.Column(db.Integer)
    shop_title = db.Column(db.String(50))
    seller_nick = db.Column(db.String(50))
    pay_time = db.Column(db.DateTime)
    pay_price = db.Column(db.Numeric(9,2))
    real_pay_fee = db.Column(db.Numeric(9,2))           # 实际支付金额
    commission = db.Column(db.Numeric(9,2))             # 用户获得拥金
    commission_rate = db.Column(db.String(10))        # 拥金比率
    
    __mapper_args__ = {'order_by': id.desc()}
    
    def __init__(self, *args, **kwargs):
        super(TaokeReport, self).__init__(*args, **kwargs)

    def __str__(self):
        return u"%s: %s" % (self.trand_id, self.item_title)

    def __repr__(self):
        return "<%s>" % self


class FinanceRecord(db.Model):
    
    __tablename__ = "finance_records"

    PER_PAGE = 20

    BUY = 100       # 购买
    COMM = 200      # 推荐成功
    EXTRACT = 300   # 提取
    
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.Integer(3), nullable=False) #BUY, COMM, EXTRACT
    money = db.Column(db.Numeric(9,2)) # 支出(EXTRACT)为负数
    created_date = db.Column(db.DateTime, default=datetime.now)
    
    report_id = db.Column(db.Integer,
                          db.ForeignKey('taoke_reports.id', ondelete='CASCADE'))
    
    report = db.relation('TaokeReport', backref='finance_records')

    user_id = db.Column(db.Integer,
                        db.ForeignKey('users.id', ondelete='CASCADE'))

    user = db.relation('User', backref='finance_records')

    def __init__(self, *args, **kwargs):
        super(FinanceRecord, self).__init__(*args, **kwargs)

    def __str__(self):
        return u"%s: %s" % (self.user_id, self.money)
    
    def __repr__(self):
        return "<%s>" % self
    


########NEW FILE########
__FILENAME__ = mydb
#!/usr/bin/env python
#coding=utf-8

"""
    mydb.py
    ~~~~~~~~~~~~~

    Database connect class, from flask-sqlalchemy

    :license: BSD, see LICENSE for more details.
"""
import re
from functools import partial
import sqlalchemy
from sqlalchemy import orm, types
from sqlalchemy.orm.mapper import Mapper
from sqlalchemy.orm.session import Session
from sqlalchemy.orm.interfaces import MapperExtension, SessionExtension, \
     EXT_CONTINUE
from sqlalchemy.orm.exc import UnmappedClassError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.util import to_list

_camelcase_re = re.compile(r'([A-Z]+)(?=[a-z0-9])')

def _create_scoped_session(db, options):
    if options is None:
        options = {}
    return orm.scoped_session(partial(_SignallingSession, db, **options))


def _make_table(db):
    def _make_table(*args, **kwargs):
        if len(args) > 1 and isinstance(args[1], db.Column):
            args = (args[0], db.metadata) + args[1:]
        return sqlalchemy.Table(*args, **kwargs)
    return _make_table


def _include_sqlalchemy(obj):
    for module in sqlalchemy, sqlalchemy.orm:
        for key in module.__all__:
            if not hasattr(obj, key):
                setattr(obj, key, getattr(module, key))
    obj.Table = _make_table(obj)


class _SignallingSession(Session):

    def __init__(self, db, autocommit=False, autoflush=False, **options):
        Session.__init__(self, autocommit=autocommit, autoflush=autoflush,
                         bind=db.engine, **options)


class _QueryProperty(object):

    def __init__(self, sa):
        self.sa = sa

    def __get__(self, obj, type):
        try:
            mapper = orm.class_mapper(type)
            if mapper:
                return type.query_class(mapper, session=self.sa.session())
        except UnmappedClassError:
            return None


class _SignalTrackingMapper(Mapper):
    def __init__(self, *args, **kwargs):
        extensions = to_list(kwargs.pop('extension', None), [])
        kwargs['extension'] = extensions
        Mapper.__init__(self, *args, **kwargs)


class _ModelTableNameDescriptor(object):

    def __get__(self, obj, type):
        tablename = type.__dict__.get('__tablename__')
        if not tablename:
            def _join(match):
                word = match.group()
                if len(word) > 1:
                    return ('_%s_%s' % (word[:-1], word[-1])).lower()
                return '_' + word.lower()
            tablename = _camelcase_re.sub(_join, type.__name__).lstrip('_')
            setattr(type, '__tablename__', tablename)
        return tablename


class BaseQuery(orm.Query):
    """The default query object used for models.  This can be subclassed and
    replaced for individual models by setting the :attr:`~Model.query_class`
    attribute.  This is a subclass of a standard SQLAlchemy
    :class:`~sqlalchemy.orm.query.Query` class and has all the methods of a
    standard query as well.
    """

    def get_or_404(self, ident):
        """Like :meth:`get` but aborts with 404 if not found instead of
        returning `None`.
        """
        rv = self.get(ident)
        if rv is None:
            abort(404)
        return rv

    def first_or_404(self):
        """Like :meth:`first` but aborts with 404 if not found instead of
        returning `None`.
        """
        rv = self.first()
        if rv is None:
            abort(404)
        return rv

    def paginate(self, page, per_page=20, error_out=True):
        """Returns `per_page` items from page `page`.  By default it will
        abort with 404 if no items were found and the page was larger than
        1.  This behavor can be disabled by setting `error_out` to `False`.

        Returns an :class:`Pagination` object.
        """
        if error_out and page < 1:
            abort(404)
        items = self.limit(per_page).offset((page - 1) * per_page).all()
        if not items and page != 1 and error_out:
            abort(404)
        return Pagination(self, page, per_page, self.count(), items)


class Model(object):
    """Baseclass for custom user models."""

    #: the query class used.  The :attr:`query` attribute is an instance
    #: of this class.  By default a :class:`BaseQuery` is used.
    query_class = BaseQuery

    #: an instance of :attr:`query_class`.  Can be used to query the
    #: database for instances of this model.
    query = None

    #: arguments for the mapper
    __mapper_cls__ = _SignalTrackingMapper

    __tablename__ = _ModelTableNameDescriptor()


class SQLAlchemy(object):
    """
        sqlalchemy
    """
    def __init__(self, engine_url, echo=False,
                 session_extensions=None, session_options=None):
        """Init""" 
        self.session = _create_scoped_session(self, session_options)
        self.Model = declarative_base(cls=Model, name='Model')
        self.Model.query = _QueryProperty(self)
        self.engine = sqlalchemy.create_engine(engine_url, echo=echo)
        _include_sqlalchemy(self)

    def create_all(self):
        """Creates all tables."""
        self.Model.metadata.create_all(bind=self.engine)

    def drop_all(self):
        """Drops all tables."""
        self.Model.metadata.drop_all(bind=self.engine)


class DenormalizedText(types.MutableType, types.TypeDecorator):
    """
    Stores denormalized primary keys that can be 
    accessed as a set. 

    :param coerce: coercion function that ensures correct
                   type is returned

    :param separator: separator character
    """

    impl = types.Text

    def __init__(self, coerce=int, separator=",", **kwargs):

        self.coerce = coerce
        self.separator = separator
        
        super(DenormalizedText, self).__init__(**kwargs)

    def process_bind_param(self, value, dialect):
        if value is not None:
            items = [str(item).strip() for item in value]
            value = self.separator.join(item for item in items if item)
        return value

    def process_result_value(self, value, dialect):
         if not value:
            return set()
         return set(self.coerce(item) \
                   for item in value.split(self.separator))
        
    def copy_value(self, value):
        return set(value)

########NEW FILE########
__FILENAME__ = mytimer
#!/usr/bin/env python
#coding=utf-8

import threading
import urllib2
import datetime
from taobao_func import order_from_taobao

class RepeatableTimer(object):
    def __init__(self, interval, function, args=[], kwargs={}):
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs

    def start(self):
        self.stop()
        self._timer = threading.Timer(self.interval, self._run)
        self._timer.start()

    def restart(self):
        self.start()

    def stop(self):
        if self.__dict__.has_key("_timer"):
            self._timer.cancel()
            del self._timer
    def _run(self):
        try:
            self.function(*self.args, **self.kwargs)
        except:
            pass
        self.restart()

def getreport():
    now = datetime.datetime.now()
    prev = now + datetime.timedelta(days=-1)
    order_from_taobao(prev)
    print now


if __name__ == "__main__":
    print 'start timer........'
    a = RepeatableTimer(43200,getreport) # 12 hours one time
    a.start()

########NEW FILE########
__FILENAME__ = taobaoapi
#!/usr/bin/env python
#coding=utf-8

"""
    taobaoapi.py
    ~~~~~~~~~~~~~

    Taobao API simple class
    
    :copyright: (c) 2011 by Laoqiu.
    :license: BSD, see LICENSE for more details.
"""

import hashlib, json
import re
import urllib, urllib2
from datetime import datetime
import time

from webapp.extensions import appkey, myappkey

class TaobaoAPI(object):
    """
    client = TaobaoAPI(appkey, appsecret)
    req = TaobaoRequest(method)
    req.setParams(fields,product_id)
    product = client.execute(req)
    """

    def __init__(self, appkey, appsecret, debug=False):
        self.key = appkey
        self.secret = appsecret
        if debug:
            self.apiurl = "http://gw.api.tbsandbox.com/router/rest"
        else:
            self.apiurl = "http://gw.api.taobao.com/router/rest"

    def _sign(self, params):
        src = self.secret + ''.join(["%s%s" % (k,v) for k,v in sorted(params.items())]) \
                          + self.secret
        return hashlib.md5(src).hexdigest().upper()
    
    def getParams(self, params):
        params['app_key'] = self.key
        params['v'] = '2.0'
        params['format'] = 'json'
        params['timestamp'] = datetime.now().strftime('%Y-%m-%d %X')
        params['sign_method'] = 'md5'
        params['sign'] = self._sign(params)
        return urllib.urlencode(params)
        
    def execute(self, request):
        try:
            params = self.getParams(request.params)
        except BadParamsError:
            return
        
        while True:
            source = urllib2.urlopen(self.apiurl, params).read()
            data = json.loads(source)
            if data.get('code',0)==7:
                time.sleep(10)
                print 'error 7: api get times overflow'
            else:
                break
        return data.values()[0]


class BadParamsError(Exception): pass


class TaobaoRequest(object):
    """
    make a request
    req = TaobaoRequest(method, fileds='num_iid,title,price', product_id=1)
    """

    def __init__(self, *args, **kwargs):
        self.params = {'method':args[0]}
        self.setParams(**kwargs)
    
    def setParams(self, *args, **kwargs):
        for key in kwargs.keys():
            self.params[key] = kwargs[key]



########NEW FILE########
__FILENAME__ = taobao_func
#!/usr/bin/env python
#coding=utf-8

"""
    taobao_func.py
    ~~~~~~~~~~~~~
    :copyright: (c) 2011 by Laoqiu.
    :license: BSD, see LICENSE for more details.
"""

import urllib, urllib2
import re
import datetime, time
import hashlib
import json

from decimal import Decimal

from taobaoapi import myappkey, appkey, TaobaoAPI, TaobaoRequest
from models import db, User, TaokeReport, FinanceRecord

from gzipSupport import ContentEncodingProcessor

# gzip support
gzip_support = ContentEncodingProcessor

opener = urllib2.build_opener(gzip_support)
urllib2.install_opener(opener)


def get_headers(gzip=True):
    headers = {
        "User-Agent":"Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.9.2.13) Gecko/20101203 Firefox/3.6.13",
        # "User-Agent": "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.13) Gecko/20101206 Ubuntu/10.10 (maverick) Firefox/3.6.13"
        "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language":"zh-cn,zh;q=0.5",
        # "Accept-Encoding":"gzip,deflate",
        "Accept-Charset":"GB2312,utf-8;q=0.7,*;q=0.7",
        "Keep-Alive":"115",
        "Connection":"keep-alive",
        # "Host":"",
        # "Referer":"",
    }
    if gzip:
        headers["Accept-Encoding"] = "gzip,deflate"
    return headers


def request(url, headers=None, data=dict()):
    if headers is None:
        headers = get_headers()
    
    data = urllib.urlencode(data) if data else None
    req = urllib2.Request(
            url = url,
            data = data,
            headers = headers
            )
    try:
        request = urllib2.urlopen(req)
        source = request.read()
        # print url
        # print request.code,request.msg
        request.close()
    except:
        source = None
        print "connect timeout"

    return source



##############################
#                            #
#     function for taobao    #
#                            #
##############################


def get_taobao_items(q):
    key, secret, nick = myappkey
    client = TaobaoAPI(key, secret)
    method = 'taobao.items.get'
    fields = 'num_iid,title,pic_url,price,nick,score,volume,location,post_fee,delist_time'
    q = q.encode('utf-8')
    order_by = 'price:asc'
    start_score = '8'

    req = TaobaoRequest(method,
                        fields=fields,
                        q=q,
                        order_by=order_by,
                        start_score=start_score,
                        page_size=200)

    source = client.execute(req)

    items = source.get('items',{'item':[]}).get('item',[])
    data = [{'title': g['title'],
             'nick': g['nick'],
             'pic_url': g['pic_url'],
             'num_iid': g['num_iid'],
             'detail_url': "http://item.taobao.com/item.htm?id=%s" % g['num_iid'],
             'price': float(g['price']),
             'volume': int(g['volume']),
             'score': int(g['score']),
             'post_fee': g['post_fee'],
             'delist_time': datetime.datetime.strptime(g['delist_time'],'%Y-%m-%d %H:%S:%M'),
             'location': g['location']['city'],
             'source': 'taobao'} for g in items]
    return data


def get_taobao_item(num_iid):
    
    key, secret, nick = myappkey
    client = TaobaoAPI(key, secret)
    method = 'taobao.item.get'
    fields = 'num_iid,detail_url,title,pic_url,price,nick,score,volume,location,post_fee,delist_time'

    req = TaobaoRequest(method, fields=fields, num_iid=num_iid)

    source = client.execute(req)
    print source

    item = source.get('item', None)

    return item


def get_taobao_taoke(q):
    key, secret, nick = myappkey
    client = TaobaoAPI(key, secret)
    method = 'taobao.taobaoke.items.get'
    fields = 'num_iid,title,price,nick,click_url,commission,commission_rate,commission_num,commission_volume,shop_click_url,seller_credit_score,item_location,volume'
    q = q.encode('utf-8')
    order_by = "price_asc"

    req = TaobaoRequest(method,
                        fields=fields,
                        keywords=q,
                        sort=order_by,
                        start_credit='3diamond',
                        page_size=200)

    source = client.execute(req)

    items = source.get('taobaoke_items',{'taobaoke_item':[]}).get('taobaoke_item',[])
    data = [{'title': g['title'],
             'nick': g['nick'],
             'num_iid': g['num_iid'],
             'detail_url': g['click_url'],
             'price': float(g['price']),
             'volume': int(g['volume']),
             'score': int(g['seller_credit_score']),
             'post_fee': None,
             'delist_time': None,
             'location': g['item_location'],
             'source': 'taobao'} for g in items]
    return data


def taoke_items_convert(num_iids):
    key, secret, nick = myappkey
    client = TaobaoAPI(key, secret)
    
    method = 'taobao.taobaoke.items.convert'
    fields = 'num_iid,title,nick,pic_url,price,click_url,commission,ommission_rate,commission_num,commission_volume,shop_click_url,seller_credit_score,item_location,volume'

    data = []
    # 每次转换最大输入40个num_iid
    n = len(num_iids)/40 + (len(num_iids) % 40 and 1 or 0)
    for i in range(n):
        ids = ','.join([str(i) for i in num_iids[i*40:(i+1)*40]])
        req = TaobaoRequest(method, 
                            fields=fields,
                            num_iids=ids,
                            nick=nick.encode('utf8'))
        
        source = client.execute(req)
        
        items = source.get('taobaoke_items',{'taobaoke_item':[]}).get('taobaoke_item',[])
        data.extend([{'num_iid': g['num_iid'],
                 'click_url': g['click_url'],
                 'pic_url': g['pic_url'],
                 'title': g['title'],
                 'nick': g['nick'],
                 'price': float(g['price']),
                 'commission': float(g['commission']),
                 'seller_credit_score': int(g['seller_credit_score']),
                 'source': 'taobao'} for g in items])

    return data


def get_taobao_shop(nick):
    
    key, secret, mynick = appkey
    #key, secret, mynick = myappkey
    client = TaobaoAPI(key, secret)
    
    method = 'taobao.user.get'
    fields = 'user_id,uid,nick,sex,buyer_credit,seller_credit,location'
    req = TaobaoRequest(method, fields=fields, nick=nick.encode('utf8'))

    source = client.execute(req)

    shop = source.get('user', None)

    return shop
    

def goods_from_url(url):
     
    re_ids = re.findall(r'id=(\d+)', url)
    
    num_iid = re_ids[0] if re_ids else None

    item = get_taobao_item(num_iid) if num_iid else None
    taoke_items = taoke_items_convert([num_iid])
    if taoke_items:
        item.update(taoke_items[0])

    return item


def order_from_taobao(date):

    key, secret, nick = myappkey
    
    client = TaobaoAPI(key, secret)
    method = 'taobao.taobaoke.report.get'
    fields = 'trade_id,num_iid,item_title,item_num,seller_nick,pay_price,pay_time,shop_title,commission,outer_code'

    page = 1
    items = []
    while page>0:
        req = TaobaoRequest(method,
                            fields=fields,
                            date=date.strftime('%Y%m%d'),
                            page_no=page,
                            page_size=40)

        source = client.execute(req)

        items.extend(source.get('taobaoke_report',{}).get('taobaoke_report_members',{}).get('taobaoke_report_member',[]))
        total = source.get('total_results',40)
        if total - page*40 > 0:
            page += 1
        else:
            page = -1

    if items:
        
        for r in items:
            trade_id = str(r['trade_id'])
            report = TaokeReport.query.filter_by(trade_id=trade_id).first()

            if report is None:
                report = TaokeReport(trade_id=trade_id)
                db.session.add(report)
                
                report.num_iid = r['num_iid']
                report.pay_time = datetime.datetime.strptime(r['pay_time'], '%Y-%m-%d %H:%S:%M')
                report.pay_price = r['pay_price']
                report.item_title = r['item_title']
                report.item_num = r['item_num']
                report.shop_title = r['shop_title']
                report.seller_nick = r['seller_nick']
                report.real_pay_fee = r['real_pay_fee']
                
                report.commission = Decimal(str(r['commission']))
                report.commission_rate = r['commission_rate']
                report.outer_code = r['outer_code']

                db.session.flush()
                
                # 给用户返利
                outer_code = r.get('outer_code','')
                shorten = [outer_code[:6], outer_code[6:]]

                for i,s in enumerate(shorten):
                    user = User.query.filter_by(shorten=s).first()

                    # 前面为购买者(50%)，后面为推荐者(20%返利)
                    rate = 0.5 if i==0 else 0.2

                    if user:
                        record = FinanceRecord()
                        record.money = Decimal(str(float(report.commission) * rate))
                        record.source = record.BUY if i==0 else record.COMM
                        record.report = report
                        record.user = user

                        user.money += record.money

                        db.session.add(record)

                db.session.commit()

    return items



########NEW FILE########
__FILENAME__ = signals
#!/usr/bin/env python
#coding=utf-8

from blinker import Namespace

signals = Namespace()



########NEW FILE########
__FILENAME__ = imageProcess
#! /usr/bin/env python
#coding=utf-8
"""
    imageProcess.py
    ~~~~~~~~~~~~~
    Recaptcha and Thumbnail

    :copyright: (c) 2010 by Laoqiu.
    :license: BSD, see LICENSE for more details.
"""

import sys, os, hashlib, datetime, random

import Image, ImageFont, ImageDraw, ImageEnhance

import StringIO

root_path = os.path.dirname(__file__)

def Recaptcha(text):
    img = Image.new('RGB',size=(110,26),color=(255,255,255))
    
    # set font
    font = ImageFont.truetype(os.path.join(os.path.dirname(__file__),'FacesAndCaps.ttf'),25)
    draw = ImageDraw.Draw(img)
    colors = [(250,125,30),(15,65,150),(210,30,90),(64,25,90),(10,120,40),(95,0,16)]
    
    # write text
    for i,s in enumerate(text):
        position = (i*25+4,0)
        draw.text(position, s, fill=random.choice(colors),font=font)
    
    # set border
    #draw.line([(0,0),(99,0),(99,29),(0,29),(0,0)], fill=(180,180,180))
    del draw
    
    # push data
    strIO = StringIO.StringIO()
    img.save(strIO,'PNG')
    strIO.seek(0)
    return strIO

def reduce_opacity(im, opacity):
    """Returns an image with reduced opacity."""
    assert opacity >= 0 and opacity <= 1
    if im.mode != 'RGBA':
        im = im.convert('RGBA')
    else:
        im = im.copy()
    alpha = im.split()[3]
    alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
    im.putalpha(alpha)
    return im

class Thumbnail(object):
    """
        t = Thumbnail(path)
        t.thumb(size=(100,100),outfile='file/to/name.xx',bg=False,watermark=None)
    """
    def __init__(self, path):
        self.path = path
        try:
            self.img = Image.open(self.path)
        except IOError:
            self.img = None
            print "%s not images" % path

    def thumb(self, size=(100,100), outfile=None, bg=False, watermark=None):
        """
            outfile: 'file/to/outfile.xxx'  
            crop: True|False
            watermark: 'file/to/watermark.xxx'
        """
        if not self.img:
            print 'must be have a image to process'
            return

        if not outfile:
            outfile = self.path

        #原图复制
        part = self.img
        part.thumbnail(size, Image.ANTIALIAS) # 按比例缩略
        
        size = size if bg else part.size # 如果没有白底则正常缩放
        w,h = size
        
        layer = Image.new('RGBA',size,(255,255,255)) # 白色底图

        # 计算粘贴的位置
        pw,ph = part.size
        left = (h-ph)/2
        upper = (w-pw)/2
        layer.paste(part,(upper,left)) # 粘贴原图

        # 如果有watermark参数则加水印
        if watermark:
            logo = Image.open(watermark)
            logo = reduce_opacity(logo, 0.3)
            # 粘贴到右下角
            lw,lh = logo.size
            position = (w-lw,h-lh)
            if layer.mode != 'RGBA':
                layer.convert('RGBA')
            mark = Image.new('RGBA', layer.size, (0,0,0,0))
            mark.paste(logo, position)
            layer = Image.composite(mark, layer, mark)

        layer.save(outfile, quality=100) # 保存
        return outfile
    
    def get_font(self, fontname, fontsize):
        return ImageFont.truetype(os.path.join(root_path, fontname), fontsize)

    def thumb_taoke(self, price, commission, outfile=None):
        """
            pic add price and commission
        """
        if not self.img:
            print 'must be have a image to process'
            return
        
        if not outfile:
            outfile = self.path

        #原图复制
        #layer = Image.new('RGBA', self.img.size, (255,255,255))
        layer = self.img
        w,h = self.img.size
        if layer.mode != 'RGBA':
            layer.convert('RGBA')
        
        # 创建字体
        price = u'%s' % price
        commission = u"%s" % commission
        unit = u"¥"
        label = u"返利"

        # 创建背景
        price_bg = Image.open(os.path.join(root_path, 'price_bg_big.png'))
        price_bg = reduce_opacity(price_bg, 0.8)
        p_w, p_h = price_bg.size
        
        comm_bg = Image.open(os.path.join(root_path, 'price_bg_small.png'))
        comm_bg = reduce_opacity(comm_bg, 0.7)
        c_w, c_h = comm_bg.size

        price_left = w - p_w - 10
        price_upper = h / 2 + 10
        comm_left = w - c_w - 10
        comm_upper = price_upper + p_h + 10

        # 粘贴
        mark = Image.new('RGBA', layer.size, (0,0,0,0))
        mark.paste(price_bg, (price_left, price_upper))
        mark.paste(comm_bg, (comm_left, comm_upper))
        layer = Image.composite(mark, layer, mark)
        
        # 写价格
        font_u_b = self.get_font('AndaleMono.ttf', 22)
        font_u_s = self.get_font('AndaleMono.ttf', 15)
        font_zh = self.get_font('yahei_mono.ttf',12)

        draw = ImageDraw.Draw(layer)

        # ¥
        draw.text((price_left+10, price_upper+4), unit, (255,255,255), font=font_u_b)
        
        # price
        space = 72
        fs = 22
        while True:
            font_temp = self.get_font('AndaleMono.ttf', fs)
            ft_w, ft_h = font_temp.getsize(price)
            if ft_w < space:
                break
            fs -= 1
        position = (price_left + 22 + (space - ft_w)/2, price_upper + (p_h - ft_h)/2)
        draw.text(position, price, (255,255,255), font=font_temp)
        
        # 返利
        draw.text((comm_left+8, comm_upper+4), label, (255,224,0), font=font_zh)

        # ¥
        draw.text((comm_left+38, comm_upper+4), unit, (255,224,0), font=font_u_s)
        
        # commission
        space = 48
        fs = 15
        while True:
            font_temp = self.get_font('AndaleMono.ttf', fs)
            ft_w, ft_h = font_temp.getsize(commission)
            if ft_w < space:
                break
            fs -= 1
        position = (comm_left + 45 + (space - ft_w)/2, comm_upper + (c_h - ft_h)/2)
        draw.text(position, commission, (255,224,0), font=font_temp)

        del draw
        layer.save(outfile, quality=100) # 保存
        return outfile

    

if __name__=='__main__':
    t = Thumbnail('pic.jpg')
    t.thumb_taoke(219.6, 18.6, 'pic1.jpg')

########NEW FILE########
__FILENAME__ = admin
#! /usr/bin/env python
#coding=utf-8

import os
import datetime

from werkzeug import FileStorage

from flask import Module, Response, request, flash, json, g, current_app,\
    abort, redirect, url_for, session, render_template, send_file, send_from_directory

from flaskext.principal import identity_changed, Identity, AnonymousIdentity

from webapp.permissions import auth_permission, admin_permission 

from webapp.extensions import db, sina_api#, qq_api

from webapp.models import User, FinanceRecord


admin = Module(__name__)

@admin.route("/")
@admin_permission.require(404)
def index():
    return redirect(url_for('admin.cash_logs'))


@admin.route("/cash_logs")
@admin.route("/cash_logs/page/<int:page>")
@admin_permission.require(404)
def cash_logs(page=1):

    page_obj = FinanceRecord.query.filter(FinanceRecord.source==FinanceRecord.EXTRACT) \
                            .paginate(page, per_page=FinanceRecord.PER_PAGE)

    page_url = lambda page: url_for('admin.cash_logs', page=page)

    return render_template("admin/cash_logs.html", 
                            page_obj=page_obj,
                            paeg_url=page_url)


@admin.route("/cashed/<int:record_id>")
@admin_permission.require(404)
def cashed(record_id):
    
    record = FinanceRecord.query.get_or_404(record_id)

    record.status = FinanceRecord.SUCCESS
    db.session.commit()
    
    next_url = request.args.get('next','')
    if not next_url:
        next_url = url_for('admin.cash_logs')

    return redirect(next_url)
    




########NEW FILE########
__FILENAME__ = auth
#! /usr/bin/env python
#coding=utf-8

import os
from datetime import datetime, timedelta

from flask import Module, Response, request, flash, json, g, current_app,\
    abort, redirect, url_for, session, render_template, send_file, send_from_directory

from flaskext.principal import identity_changed, Identity, AnonymousIdentity

from webapp.extensions import db, sina_api#, qq_api

from webapp.helpers import shorten

from webapp.models import User, UserMapper, UserProfile

from weibo import sina, qq

auth = Module(__name__)


@auth.route('/<source>/<app>/authorize')
def authorize(source, app):
    
    if source=='sina':
        try:
            key, token, callback = sina_api[app]
        except:
            abort(404)
        auth = sina.OAuthHandler(key, token, callback)
    
    #elif source=='qq':
    #    key, token, callback = qq_api
    #    auth = qq.OAuthHandler(key, token, callback)

    else:
        abort(404)

    authorize_url, request_token = auth.get_auth_url()
    session['oauth_token'] = str(request_token)
    
    return redirect(authorize_url)


@auth.route('/<source>/<app>/callback')
def callback(source, app):
    
    verifier = request.args.get('oauth_verifier','')
    #oauth_token = request.args.get('oauth_token','')

    if source=='sina':
        try:
            api_key, api_secret, callback = sina_api[app]
        except:
            abort(404)
        auth = sina.OAuthHandler(api_key, api_secret, callback)
        token_string = sina.oauth.OAuthToken.from_string(session['oauth_token'])
    
    #elif source=='qq':
    #    api_key, api_secret, callback = qq_api
    #    auth = qq.OAuthHandler(api_key, api_secret, callback)
    #    token_string = qq.oauth.OAuthToken.from_string(session['oauth_token']) 
    
    auth.set_req_token(token_string)
    token = auth.get_access_token(verifier)
    
    session['oauth_token'] = token.key
    session['oauth_token_secret'] = token.secret
    
    auth.setToken(token.key, token.secret)

    if source=='sina':
        username = auth.get_username()
    #elif source=='qq':
    #    username = auth.get_username()
    else:
        username = ''

    session['source'] = source
    session['app'] = app
    session['username'] = username

    if not g.user:
        mapper = UserMapper.query.filter(db.and_(UserMapper.source==source,
                                                 UserMapper.app==app,
                                                 UserMapper.access_token==token.key))\
                                 .first()
        if mapper:
            # login
            identity_changed.send(current_app._get_current_object(),
                                              identity=Identity(mapper.user.id))
        else:
            return redirect(url_for('auth.register'))

    g.user.bind(source, app, token.key, token.secret)

    # update profile
    update_profile(source, g.user, auth)

    return redirect(url_for('%s.index' % app))


@auth.route('/register')
def register():

    if g.user:
        return 'is logined'

    source = session.get('source')
    app = session.get('app')
    username = session.get('username')

    if source and username and app:
    
        token = session['oauth_token']
        secret = session['oauth_token_secret']

        if source=='sina':

            api_key, api_secret, callback = sina_api[app]
            auth = sina.OAuthHandler(api_key, api_secret, callback)
            auth.setToken(token, secret)
        
        #elif source=='qq':
        #    api_key, api_secret, callback = qq_api
        #    auth = qq.OAuthHandler(api_key, api_secret, callback)
        #    auth.setToken(token, secret)
        
        # 创建shorten
        while True:
            code = shorten(str(datetime.now()))
            if User.query.filter_by(shorten=code).count()==0:
                break

        email = '%s@openid.com' % code

        user = User(nickname=username,
                    email=email,
                    shorten=code)

        user.password = email

        user.profile = UserProfile()

        update_profile(source, user, auth)

        db.session.add(user)
        db.session.commit()

        # login
        identity_changed.send(current_app._get_current_object(),
                                          identity=Identity(user.id))

        user.bind(source, app, token, secret)

        return redirect(url_for('%s.post' % app))

    else:
        return redirect(url_for('frontend.login'))
    

def update_profile(source, user, auth):

    if source=='sina':
        api = sina.API(auth)

        username = auth.get_username()
        
        try:
            profile = api.get_user(screen_name=username)
        except:
            profile = None

        user.nickname = username
        user.profile.description = profile.description
        user.profile.image_url = profile.profile_image_url
        user.profile.gender = profile.gender
        user.profile.url = profile.url
        user.profile.followers_count = profile.followers_count
        user.profile.location = profile.location
        user.profile.verified = profile.verified
    
    #elif source=='qq':
    #    api = qq.API(auth)
    #    try:
    #        profile = api.user.info()
    #    except:
    #        profile = None

    return 




########NEW FILE########
__FILENAME__ = frontend
#! /usr/bin/env python
#coding=utf-8

import os
import datetime

from werkzeug import FileStorage

from flask import Module, Response, request, flash, json, g, current_app,\
    abort, redirect, url_for, session, render_template, send_file, send_from_directory

from flaskext.principal import identity_changed, Identity, AnonymousIdentity

from webapp.permissions import auth_permission, admin_permission 

from webapp.extensions import db, sina_api#, qq_api

from webapp.models import User

from weibo import sina, qq

frontend = Module(__name__)


@frontend.route("/")
def index():
    return redirect(url_for('taoke.index', _external=True))


@frontend.route('/logout')
def logout():
    
    next_url = request.args.get('next','')
    session.pop('oauth_token')
    session.pop('oauth_token_secret')

    identity_changed.send(current_app._get_current_object(),
                              identity=AnonymousIdentity())  
    if not next_url:
        next_url = url_for('frontend.index')
    
    return redirect(next_url)


@frontend.route("/favicon.ico")
def favicon():
    return send_from_directory(os.path.join(current_app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')



########NEW FILE########
__FILENAME__ = taoke
#! /usr/bin/env python
#coding=utf-8

import os
import time
from datetime import datetime, timedelta

from werkzeug import FileStorage

from flask import Module, Response, request, flash, json, g, current_app,\
    abort, redirect, url_for, session, render_template, send_file, send_from_directory

from flaskext.principal import identity_changed, Identity, AnonymousIdentity

from webapp.permissions import auth_permission, admin_permission 

from webapp.extensions import db, sina_api#, qq_api

from webapp.models import User, FinanceRecord
from webapp.forms import CashForm

from webapp.scripts.taobao_func import goods_from_url, taoke_items_convert, \
    get_taobao_item, get_taobao_shop, request as req

from webapp.utils.imageProcess import Thumbnail

from weibo import sina, qq

taoke = Module(__name__, subdomain='tuibei')


@taoke.route("/")
def index():
    
    next_url = session.get('next')
    if next_url:
        session.pop('next')
        return redirect(next_url)
    
    return render_template("taoke/index.html")


@taoke.route("/post")
@auth_permission.require(401)
def post():
    
    return render_template('taoke/post.html')


@taoke.route("/taobao", methods=('POST',))
@auth_permission.require(401)
def taobao():
    
    url = request.form.get('url','')

    item = goods_from_url(url)
    #print item

    if item:
        item['buyer_get'] = round(item.get('commission',0) * 0.5, 1)
        item['author_get'] = round(item.get('commission',0) * 0.2, 1)
        item['click_url'] = url_for('taoke.buy', 
                                    num_iid=item['num_iid'], 
                                    au=g.user.shorten, 
                                    _external=True)
        
        text_temp = u'现在购买<<<%(title)s>>> 只需要 %(price)s 元，还能得到 %(buyer_get)s 元返利，点击这里购买 >>>>>>>> '
        text = text_temp % item

        html_temp = u"""
            <div class="txt">
                <h3>%(title)s</h3>
                <p>价格: <span class="price">%(price)s</span> 元，购买返利: <span class="price">%(buyer_get)s</span> 元</p>
                <p>分享到微博，每个用户购买一件这个商品，您都将获取推荐返利: <strong class="price">%(author_get)s</strong> 元</p>
            </div>
            <div class="pic">
                <ul>
                    <li><img src="%(pic_url)s" alt="%(title)s" /></li>
                    <li><img src="%(pic_default)s" alt="%(title)s" /></li>
                </ul>
            </div>
            """
        
        item['pic_default'] = url_for('.static', filename='styles/taoke/images/bg-img.png')
        html = html_temp % item

        return json.dumps({'success':True,'html':html,'text':text,'item':item})

    return json.dumps({'error':u"没有找到商品,请检查url是否正确"})


@taoke.route("/buy/<int:num_iid>")
def buy(num_iid):
     
    items = taoke_items_convert([num_iid])
    #print items
    if items:
        item = items[0]

        item['click_url'] = url_for('taoke.click_url', 
                                    url=item['click_url'], 
                                    au=request.args.get('au',''),
                                    _external=True)

        item['score'] = item['seller_credit_score']
    else:
        item = get_taobao_item(num_iid)
        shop = get_taobao_shop(item['nick'])
        item['click_url'] = item['detail_url']
        item['score'] = shop['seller_credit']['level']
    
    return render_template("taoke/buy.html", item=item)


@taoke.route("/click")
@auth_permission.require(401)
def click_url():
    
    click_url = request.args.get('url','')
    author = request.args.get('au','')

    click_url += '%s%s' % (g.user.shorten, author)

    return redirect(click_url)


@taoke.route("/markpic", methods=('POST',))
@auth_permission.require(401)
def markpic():
    
    url = request.form.get('url')
    price = request.form.get('price', type=float)
    commission = request.form.get('commission', 0.0, type=float)

    if url and price:

        path, url = download_img(url)
        t = Thumbnail(path)
        w,h = t.img.size
        if w>420 or h>420:
            t.thumb(size=(420,420))
            time.sleep(0.1)
        t.thumb_taoke(price, commission)

        return json.dumps({'success':True,'pic':url})

    return json.dumps({'error':u'参数错误'})


def download_img(url):
    now = datetime.now()
    data = req(url)
    filename = now.strftime("%s") + '.jpg'
    folder =  now.strftime('upload/%Y/%m/%d')
    filedir = os.path.join(current_app.config['UPLOADS_DEFAULT_DEST'], folder)
    
    if not os.path.isdir(filedir):
        os.makedirs(filedir)

    filepath = os.path.join(filedir, filename)
    try:
        f = open(filepath, 'w')
        f.write(data)
        f.close()
    except:
        return None

    url = os.path.join(current_app.config['UPLOADS_DEFAULT_URL'], folder, filename)
    return filepath, url


@taoke.route("/finance")
@taoke.route("/finance/page/<int:page>")
@auth_permission.require(401)
def finance_records(page=1):

    page_obj = FinanceRecord.query.filter(User.id==g.user.id) \
                            .order_by(FinanceRecord.created_date.desc()) \
                            .paginate(page, per_page=FinanceRecord.PER_PAGE)

    page_url = lambda page: url_for('taoke.cash', page=page)
    
    return render_template('taoke/finance_records.html',
                            page_obj=page_obj,
                            page_url=page_url)


@taoke.route("/cash", methods=("GET","POST"))
@auth_permission.require(401)
def cash():
    
    form = CashForm(alipay=g.user.alipay)

    if form.validate_on_submit():

        money = request.form.get('money',0,type=int)
        print money

        if money > g.user.money:
            form.money.errors.append(u"对不起，可用金额不足提现金额")
        elif money<=0:
            form.money.errors.append(u"请输入正确的提现金额")
        else:
            money = -money
            record = FinanceRecord(money=money,
                                   user_id=g.user.id,
                                   source=FinanceRecord.EXTRACT,
                                   status=FinanceRecord.WAIT)
            db.session.add(record)
            g.user.money += money

            if g.user.alipay is None:
                g.user.alipay = form.alipay.data

            db.session.commit()
            return redirect(url_for('taoke.finance_records'))
            
    
    return render_template('taoke/cash.html', form=form)



@taoke.route('/login')
def login():
    
    session['next'] = request.args.get('next')

    return redirect(url_for('auth.authorize', source='sina', app='taoke'))
    

@taoke.route('/logout')
def logout():
    
    return redirect(url_for('frontend.logout'))


@taoke.route("/favicon.ico")
def favicon():
    return send_from_directory(os.path.join(current_app.root_path, 'static'),
                               'taoke.ico', mimetype='image/vnd.microsoft.icon')



########NEW FILE########
__FILENAME__ = api
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2011 andelf <andelf@gmail.com>
# See LICENSE for details.
# Time-stamp: <2011-06-08 19:24:04 andelf>

import os
import mimetypes

from binder import bind_api
from error import QWeiboError
from parsers import ModelParser
from utils import convert_to_utf8_bytes


class API(object):
    """Weibo API"""
    # TODO: remove unsupported params
    def __init__(self, auth_handler=None, retry_count=0,
                 host='open.t.qq.com', api_root='/api', cache=None,
                 secure=False, retry_delay=0, retry_errors=None,
                 source=None, parser=None, log=None):
        self.auth = auth_handler
        self.host = host
        self.api_root = api_root
        self.cache = cache
        self.secure = secure
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.retry_errors = retry_errors
        self.parser = parser or ModelParser()
        self.log = log

        self._build_api_path()
    ## 时间线 ##

    """ 1.Statuses/home_timeline 主页时间线 """
    # BUG: type, contenttype, accesslevel is useless
    _statuses_home_timeline = bind_api(
        path = '/statuses/home_timeline',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['reqnum', 'pageflag', 'pagetime',
                         'type', 'contenttype'],
        require_auth = True
    )

    """ 2.Statuses/public_timeline 广播大厅时间线"""
    _statuses_public_timeline = bind_api(
        path = '/statuses/public_timeline',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['reqnum', 'pos'],
        require_auth = True
    )

    """ 3.Statuses/user_timeline 其他用户发表时间线"""
    _statuses_user_timeline = bind_api(
        path = '/statuses/user_timeline',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['name', 'reqnum', 'pageflag', 'pagetime',
                         'lastid', 'type', 'contenttype'],
        require_auth = True
    )

    """ 4.Statuses/mentions_timeline @提到我的时间线 """
    _statuses_mentions_timeline = bind_api(
        path = '/statuses/mentions_timeline',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['reqnum', 'pageflag', 'pagetime', 'lastid',
                         'type', 'contenttype', 'accesslevel'],
        require_auth = True
    )

    """ 5.Statuses/ht_timeline 话题时间线 """
    _statuses_ht_timeline = bind_api(
        path = '/statuses/ht_timeline',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['httext', 'reqnum', 'pageflag', 'pageinfo'],
        require_auth = True
    )

    """ 6.Statuses/broadcast_timeline 我发表时间线 """
    _statuses_broadcast_timeline = bind_api(
        path = '/statuses/broadcast_timeline',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['reqnum', 'pageflag', 'pagetime',
                         'lastid', 'type', 'contenttype'],
        require_auth = True
    )

    """ 7.Statuses/special_timeline 特别收听的人发表时间线 """
    _statuses_special_timeline = bind_api(
        path = '/statuses/special_timeline',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['reqnum', 'pageflag', 'pagetime'],
        require_auth = True
    )

    """ 8.Statuses/area_timeline 地区发表时间线 """
    # required: country, province, city
    _statuses_area_timeline = bind_api(
        path = '/statuses/area_timeline',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['country', 'province', 'city', 'reqnum', 'pos'],
        require_auth = True
    )

    """ 9.Statuses/home_timeline_ids 主页时间线索引 """
    _statuses_home_timeline_ids = bind_api(
        path = '/statuses/home_timeline_ids',
        payload_type = 'retid', payload_list = True,
        allowed_param = ['reqnum', 'pageflag', 'pagetime', 'type',
                         'contenttype'],
        require_auth = True
    )

    """ 10.Statuses/user_timeline_ids 其他用户发表时间线索引 """
    # required: name
    _statuses_user_timeline_ids = bind_api(
        path = '/statuses/user_timeline_ids',
        payload_type = 'retid', payload_list = True,
        allowed_param = ['name', 'reqnum', 'pageflag', 'pagetime', 'type',
                         'contenttype'],
        require_auth = True
    )

    """ 11.Statuses/broadcast_timeline_ids 我发表时间线索引 """
    _statuses_broadcast_timeline_ids = bind_api(
        path = '/statuses/broadcast_timeline_ids',
        payload_type = 'retid', payload_list = True,
        allowed_param = ['reqnum', 'pageflag', 'pagetime', 'lastid', 'type',
                         'contenttype'],
        require_auth = True
    )

    """ 12.Statuses/mentions_timeline_ids 用户提及时间线索引 """
    _statuses_mentions_timeline_ids = bind_api(
        path = '/statuses/mentions_timeline_ids',
        payload_type = 'retid', payload_list = True,
        allowed_param = ['reqnum', 'pageflag', 'pagetime', 'lastid', 'type',
                         'contenttype'],
        require_auth = True
    )

    """ 13.Statuses/users_timeline 多用户发表时间线 """
    _statuses_users_timeline = bind_api(
        path = '/statuses/users_timeline',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['names', 'reqnum', 'pageflag', 'pagetime',
                         'lastid', 'type', 'contenttype'],
        require_auth = True
    )

    """ 14.Statuses/users_timeline_ids 多用户发表时间线索引 """
    _statuses_users_timeline_ids = bind_api(
        path = '/statuses/users_timeline_ids',
        payload_type = 'retid', payload_list = True,
        allowed_param = ['names', 'reqnum', 'pageflag', 'pagetime',
                         'lastid', 'type', 'contenttype'],
        require_auth = True
    )

    ## 微博相关 ##
    """ 1.t/show 获取一条微博数据 """
    _t_show = bind_api(
        path = '/t/show',
        payload_type = 'tweet',
        allowed_param = ['id'],
        require_auth = True
    )

    """ 2.t/add 发表一条微博 """
    _t_add = bind_api(
        path = '/t/add',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['content', 'clientip', 'jing', 'wei'],
        require_auth = True
    )

    """ 3.t/del 删除一条微博 """
    _t_del = bind_api(
        path = '/t/del',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['id'],
        require_auth = True
    )

    """ 4.t/re_add 转播一条微博 """
    _t_re_add = bind_api(
        path = '/t/re_add',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['reid', 'content', 'clientip', 'jing', 'wei'],
        require_auth = True
    )

    """ 5.t/reply 回复一条微博 """
    _t_reply = bind_api(
        path = '/t/reply',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['reid', 'content', 'clientip', 'jing', 'wei'],
        require_auth = True
    )

    """ 6.t/add_pic 发表一条带图片的微博 """
    def _t_add_pic(self, filename, content, clientip='127.0.0.1',
                   jing=None, wei=None):
        headers, post_data = API._pack_image(filename, contentname="pic",
            content=content, clientip=clientip, jing=jing, wei=wei, )
        args = [content, clientip]
        allowed_param = ['content', 'clientip']

        if jing is not None:
            args.append(jing)
            allowed_param.append('jing')

        if wei is not None:
            args.append(wei)
            allowed_param.append('wei')

        return bind_api(
            path = '/t/add_pic',
            method = 'POST',
            payload_type = 'retid',
            require_auth = True,
            allowed_param = allowed_param
            )(self, *args, post_data=post_data, headers=headers)

    """ 7.t/re_count 转播数或点评数 """
    _t_re_count = bind_api(
        path = '/t/re_count',
        payload_type = 'json',
        allowed_param = ['ids', 'flag'],
        require_auth = True
    )

    """ 8.t/re_list 获取单条微博的转发或点评列表 """
    _t_re_list = bind_api(
        path = '/t/re_list',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['rootid', 'reqnum', 'flag', 'pageflag', 'pagetime',
                         'twitterid'],
        require_auth = True
    )

    """ 9.t/comment 点评一条微博 """
    _t_comment = bind_api(
        path = '/t/comment',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['reid', 'content', 'clientip', 'jing', 'wei'],
        require_auth = True
    )

    """ 10.t/add_music发表音乐微博 """
    _t_add_music = bind_api(
        path = '/t/add_music',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['url', 'title', 'author', 'content',
                         'clientip', 'jing', 'wei'],
        require_auth = True
    )

    """ 11.t/add_video发表视频微博 """
    _t_add_video = bind_api(
        path = '/t/add_video',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['url', 'content', 'clientip', 'jing', 'wei'],
        require_auth = True
    )

    """ 12.t/getvideoinfo 获取视频信息 """
    _t_getvideoinfo = bind_api(
        path = '/t/getvideoinfo',
        method = 'POST',
        payload_type = 'video',
        allowed_param = ['url'],
        require_auth = True
    )

    """ 13.t/list 根据微博ID批量获取微博内容（与索引合起来用） """
    _t_list = bind_api(
        path = '/t/list',
        method = 'GET',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['ids'],
        require_auth = True
    )

    ## 帐户相关 ##
    """ 1.User/info获取自己的详细资料 """
    _user_info = bind_api(
        path = '/user/info',
        payload_type = 'user',
        allowed_param = [],
        require_auth = True
    )

    """ 2.user/update 更新用户信息 """
    _user_update = bind_api(
        path = '/user/update',
        method = 'POST',
        allowed_param = ['nick', 'sex', 'year', 'month',
                         'day', 'countrycode', 'provincecode',
                         'citycode', 'introduction'],
        require_auth = True
    )

    """ 3.user/update_head 更新用户头像信息 """
    def _user_update_head(self, filename):
        headers, post_data = API._pack_image(filename, "pic")
        args = []
        allowed_param = []

        return bind_api(
            path = '/user/update_head',
            method = 'POST',
            require_auth = True,
            allowed_param = allowed_param
            )(self, *args, post_data=post_data, headers=headers)

    """ 4.user/other_info 获取其他人资料 """
    _user_other_info = bind_api(
        path = '/user/other_info',
        payload_type = 'user',
        allowed_param = ['name'],
        require_auth = True
    )

    ## 关系链相关 ##
    """ 1.friends/fanslist 我的听众列表 """
    _friends_fanslist = bind_api(
        path = '/friends/fanslist',
        payload_type = 'user', payload_list = True,
        allowed_param = ['reqnum', 'startindex'],
        require_auth = True
    )

    """ 2.friends/idollist 我收听的人列表 """
    _friends_idollist = bind_api(
        path = '/friends/idollist',
        payload_type = 'user', payload_list = True,
        allowed_param = ['reqnum', 'startindex'],
        require_auth = True
    )

    """ 3.Friends/blacklist 黑名单列表 """
    _friends_blacklist = bind_api(
        path = '/friends/blacklist',
        payload_type = 'user', payload_list = True,
        allowed_param = ['reqnum', 'startindex'],
        require_auth = True
    )

    """ 4.Friends/speciallist 特别收听列表 """
    _friends_speciallist = bind_api(
        path = '/friends/speciallist',
        payload_type = 'user', payload_list = True,
        allowed_param = ['reqnum', 'startindex'],
        require_auth = True
    )

    """ 5.friends/add 收听某个用户 """
    _friends_add = bind_api(
        path = '/friends/add',
        method = 'POST',
        allowed_param = ['name'],
        require_auth = True
    )

    """ 6.friends/del取消收听某个用户 """
    _friends_del = bind_api(          # fix confilicts with del
        path = '/friends/del',
        method = 'POST',
        allowed_param = ['name'],
        require_auth = True
    )

    """ 7.friends/addspecial 特别收听某个用户 """
    _friends_addspecial = bind_api(
        path = '/friends/addspecial',
        method = 'POST',
        allowed_param = ['name'],
        require_auth = True
    )

    """ 8.friends/delspecial 取消特别收听某个用户 """
    _friends_delspecial = bind_api(
        path = '/friends/delspecial',
        method = 'POST',
        allowed_param = ['name'],
        require_auth = True
    )

    """ 9.friends/addblacklist 添加某个用户到黑名单 """
    _friends_addblacklist = bind_api(
        path = '/friends/addblacklist',
        method = 'POST',
        allowed_param = ['name'],
        require_auth = True
    )

    """ 10.friends/delblacklist 从黑名单中删除某个用户 """
    _friends_delblacklist = bind_api(
        path = '/friends/delblacklist',
        method = 'POST',
        allowed_param = ['name'],
        require_auth = True
    )

    """ 11.friends/check 检测是否我的听众或收听的人 """
    _friends_check = bind_api(
        path = '/friends/check',
        payload_type = 'json',
        allowed_param = ['names', 'flag'],
        require_auth = True
    )

    """ 12.friends/user_fanslist 其他帐户听众列表 """
    _friends_user_fanslist = bind_api(
        path = '/friends/user_fanslist',
        payload_type = 'user', payload_list = True,
        allowed_param = ['name', 'reqnum', 'startindex'],
        require_auth = True
    )

    """ 13.friends/user_idollist 其他帐户收听的人列表 """
    _friends_user_idollist = bind_api(
        path = '/friends/user_idollist',
        payload_type = 'user', payload_list = True,
        allowed_param = ['name', 'reqnum', 'startindex'],
        require_auth = True
    )

    """ 14.friends/user_speciallist 其他帐户特别收听的人列表 """
    _friends_user_speciallist = bind_api(
        path = '/friends/user_speciallist',
        payload_type = 'user', payload_list = True,
        allowed_param = ['name', 'reqnum', 'startindex'],
        require_auth = True
    )

    ## 私信相关 ##
    """ 1.private/add 发私信 """
    _private_add = bind_api(
        path = '/private/add',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['name', 'content', 'clientip', 'jing', 'wei'],
        require_auth = True
    )

    """ 2.private/del 删除一条私信 """
    _private_del = bind_api(
        path = '/private/del',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['id'],
        require_auth = True
    )

    """ 3.private/recv 收件箱 """
    _private_recv = bind_api(
        path = '/private/recv',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['reqnum', 'pageflag', 'pagetime', 'lastid'],
        require_auth = True
    )

    """ 4.private/send 发件箱 """
    _private_send = bind_api(
        path = '/private/send',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['reqnum', 'pageflag', 'pagetime', 'lastid'],
        require_auth = True
    )

    ## 搜索相关 ##
    """ 1.Search/user 搜索用户 """
    _search_user = bind_api(
        path = '/search/user',
        payload_type = 'user', payload_list = True,
        allowed_param = ['keyword', 'pagesize', 'page'],
        require_auth = True
    )

    """ 2.Search/t 搜索微博 """
    _search_t = bind_api(
        path = '/search/t',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['keyword', 'pagesize', 'page'],
        require_auth = True
    )

    """ 3.Search/userbytag 通过标签搜索用户 """
    _search_userbytag = bind_api(
        path = '/search/userbytag',
        payload_type = 'user', payload_list = True,
        allowed_param = ['keyword', 'pagesize', 'page'],
        require_auth = True
    )

    # TODO: model parser
    ## 热度，趋势 ##
    """ 1.trends/ht 话题热榜 """
    _trends_ht = bind_api(
        path = '/trends/ht',
        payload_type = 'json',
        allowed_param = ['reqnum', 'type', 'pos'],
        require_auth = True
    )

    """ 2.Trends/t 转播热榜 """
    _trends_t = bind_api(
        path = '/trends/t',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['reqnum', 'type', 'pos'],
        require_auth = True
    )

    ## 数据更新相关 ##
    """ 1.info/update 查看数据更新条数 """
    _info_update = bind_api(
        path = '/info/update',
        payload_type = 'json',
        allowed_param = ['op', 'type'],
        require_auth = True
    )

    ## 数据收藏 ##
    """ 1.fav/addt 收藏一条微博 """
    _fav_addt = bind_api(
        path = '/fav/addt',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['id'],
        require_auth = True
    )

    """ 2.fav/delt 从收藏删除一条微博 """
    _fav_delt = bind_api(
        path = '/fav/delt',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['id'],
        require_auth = True
    )

    """ 3.fav/list_t 收藏的微博列表 """
    _fav_list_t = bind_api(
        path = '/fav/list_t',
        payload_type = 'tweet', payload_list = True,
        allowed_param = ['reqnum', 'pageflag', 'nexttime', 'prevtime',
                         'lastid'],
        require_auth = True
    )

    """ 4.fav/addht 订阅话题 """
    _fav_addht = bind_api(
        path = '/fav/addht',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['id'],
        require_auth = True
    )

    """ 5.fav/delht 从收藏删除话题 """
    _fav_delht = bind_api(
        path = '/fav/delht',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['id'],
        require_auth = True
    )

    """ 6.fav/list_ht 获取已订阅话题列表 """
    _fav_list_ht = bind_api(
        path = '/fav/list_ht',
        payload_type = 'json', payload_list = True,
        allowed_param = ['reqnum', 'pageflag', 'pagetime', 'lastid'],
        require_auth = True
    )

    ## 话题相关 ##
    """ 1.ht/ids 根据话题名称查询话题ID """
    _ht_ids = bind_api(
        path = '/ht/ids',
        payload_type = 'json', payload_list = True,
        allowed_param = ['httexts'],
        require_auth = True
    )

    """ 2.ht/info 根据话题ID获取话题相关微博 """
    _ht_info = bind_api(
        path = '/ht/info',
        payload_type = 'json', payload_list = True,
        allowed_param = ['ids'],
        require_auth = True
    )

    ## 标签相关 ##
    """ 1.tag/add 添加标签 """
    _tag_add = bind_api(
        path = '/tag/add',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['tag'],
        require_auth = True
    )

    """ 2.tag/del 删除标签 """
    _tag_del = bind_api(
        path = '/tag/del',
        method = 'POST',
        payload_type = 'retid',
        allowed_param = ['tagid'],
        require_auth = True
    )

    ## 其他 ##
    """ 1.other/kownperson 我可能认识的人 """
    _other_kownperson = bind_api(
        path = '/other/kownperson',
        payload_type = 'user', payload_list = True,
        allowed_param = [],
        require_auth = True
    )

    """ 2.other/shorturl短URL变长URL """
    _other_shorturl = bind_api(
        path = '/other/shorturl',
        payload_type = 'json',
        allowed_param = ['url'],
        require_auth = True
    )

    """ 3.other/videokey 获取视频上传的KEY """
    _other_videokey = bind_api(
        path = '/other/videokey',
        payload_type = 'json',
        allowed_param = [],
        require_auth = True
    )

    """ Get the authenticated user """
    def me(self):
        return self.user.info()

    """ Internal use only """
    def _build_api_path(self):
        """bind all api function to its namespace"""
        self._bind_api_namespace('timeline',
                                 home=self._statuses_home_timeline,
                                 public=self._statuses_public_timeline,
                                 user=self._statuses_user_timeline,
                                 users=self._statuses_users_timeline,
                                 mentions=self._statuses_mentions_timeline,
                                 topic=self._statuses_ht_timeline,
                                 broadcast=self._statuses_broadcast_timeline,
                                 special=self._statuses_special_timeline,
                                 area=self._statuses_area_timeline,
                                 # ids
                                 homeids=self._statuses_home_timeline_ids,
                                 userids=self._statuses_user_timeline_ids,
                                 usersids=self._statuses_users_timeline_ids,
                                 broadcastids=self._statuses_broadcast_timeline_ids,
                                 mentionsids=self._statuses_mentions_timeline_ids)
        self._bind_api_namespace('tweet',
                                 show=self._t_show,
                                 add=self._t_add,
                                 delete=self._t_del,
                                 retweet=self._t_re_add,
                                 reply=self._t_reply,
                                 addpic=self._t_add_pic,
                                 retweetcount=self._t_re_count,
                                 retweetlist=self._t_re_list,
                                 comment=self._t_comment,
                                 addmusic=self._t_add_music,
                                 addvideo=self._t_add_video,
                                 list=self._t_list)
        self._bind_api_namespace('user',
                                 info=self._user_info,
                                 update=self._user_update,
                                 updatehead=self._user_update_head,
                                 userinfo=self._user_other_info,
                                 )
        self._bind_api_namespace('friends',
                                 fanslist=self._friends_fanslist,
                                 idollist=self._friends_idollist,
                                 blacklist=self._friends_blacklist,
                                 speciallist=self._friends_speciallist,
                                 add=self._friends_add,
                                 delete=self._friends_del,
                                 addspecial=self._friends_addspecial,
                                 deletespecial=self._friends_delspecial,
                                 addblacklist=self._friends_addblacklist,
                                 deleteblacklist=self._friends_delblacklist,
                                 check=self._friends_check,
                                 userfanslist=self._friends_user_fanslist,
                                 useridollist=self._friends_user_idollist,
                                 userspeciallist=self._friends_user_speciallist,
                                 )
        self._bind_api_namespace('private',
                                 add=self._private_add,
                                 delete=self._private_del,
                                 inbox=self._private_recv,
                                 outbox=self._private_send,
                                 )
        self._bind_api_namespace('search',
                                 user=self._search_user,
                                 tweet=self._search_t,
                                 userbytag=self._search_userbytag,
                                 )
        self._bind_api_namespace('trends',
                                 topic=self._trends_ht,
                                 tweet=self._trends_t
                                 )
        self._bind_api_namespace('info',
                                 update=self._info_update,
                                 )
        self._bind_api_namespace('fav',
                                 addtweet=self._fav_addt,
                                 deletetweet=self._fav_delt,
                                 listtweet=self._fav_list_t,
                                 addtopic=self._fav_addht,
                                 deletetopic=self._fav_delht,
                                 listtopic=self._fav_list_ht,
                                 )
        self._bind_api_namespace('topic',
                                 ids=self._ht_ids,
                                 info=self._ht_info,
                                 )
        self._bind_api_namespace('tag',
                                 add=self._tag_add,
                                 delete=self._tag_del,
                                 )
        self._bind_api_namespace('other',
                                 kownperson=self._other_kownperson,
                                 shorturl=self._other_shorturl,
                                 videokey=self._other_videokey,
                                 videoinfo=self._t_getvideoinfo,
                                 )
        self.t = self.tweet
        self.statuses = self.timeline   # fix 时间线 相关

    def _bind_api_namespace(self, base, **func_map):
        """ bind api to its path"""
        if base == '':
            for fname in func_map:
                setattr(self, fname, func_map[fname])
        else:
            if callable(getattr(self, base, None)):
                func_map['__call__'] = getattr(self, base)
            mapper = type('ApiPathMapper', (object,), func_map)()
            setattr(self, base, mapper)

    # TODO: more general method
    @staticmethod
    def _pack_image(filename, contentname, max_size=1024, **params):
        """Pack image from file into multipart-formdata post body"""
        # image must be less than 700kb in size
        try:
            if os.path.getsize(filename) > (max_size * 1024):
                raise QWeiboError('File is too big, must be less than 700kb.')
        except os.error:
            raise QWeiboError('Unable to access file')

        # image must be gif, jpeg, or png
        file_type = mimetypes.guess_type(filename)
        if file_type is None:
            raise QWeiboError('Could not determine file type')
        file_type = file_type[0]
        if file_type.split('/')[0] != 'image':
            raise QWeiboError('Invalid file type for image: %s' % file_type)

        # build the mulitpart-formdata body
        BOUNDARY = 'QqWeIbObYaNdElF----'  # qqweibo by andelf
        body = []
        for key, val in params.items():
            if val is not None:
                body.append('--' + BOUNDARY)
                body.append('Content-Disposition: form-data; name="%s"' % key)
                body.append('Content-Type: text/plain; charset=UTF-8')
                body.append('Content-Transfer-Encoding: 8bit')
                body.append('')
                val = convert_to_utf8_bytes(val)
                body.append(val)
        fp = open(filename, 'rb')
        body.append('--' + BOUNDARY)
        body.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (contentname, filename.encode('utf-8')))
        body.append('Content-Type: %s' % file_type)
        body.append('Content-Transfer-Encoding: binary')
        body.append('')
        body.append(fp.read())
        body.append('--%s--' % BOUNDARY)
        body.append('')
        fp.close()
        body.append('--%s--' % BOUNDARY)
        body.append('')
        # fix py3k
        for i in range(len(body)):
            body[i] = convert_to_utf8_bytes(body[i])
        body = b'\r\n'.join(body)
        # build headers
        headers = {
            'Content-Type': 'multipart/form-data; boundary=%s' % BOUNDARY,
            'Content-Length': len(body)
        }

        return headers, body


########NEW FILE########
__FILENAME__ = auth
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2009-2010 Joshua Roesslein
# Copyright 2011 andelf <andelf@gmail.com>
# See LICENSE for details.
# Time-stamp: <2011-06-04 08:14:39 andelf>

from compat import Request, urlopen
import oauth
from error import QWeiboError
from api import API


class AuthHandler(object):

    def apply_auth_headers(self, url, method, headers, parameters):
        """Apply authentication headers to request"""
        raise NotImplementedError

    def get_username(self):
        """Return the username of the authenticated user"""
        raise NotImplementedError

    def get_signed_url(self, url, method, headers, parameters):
        raise NotImplementedError


class OAuthHandler(AuthHandler):
    """OAuth authentication handler"""

    OAUTH_HOST = 'open.t.qq.com'
    OAUTH_ROOT = '/cgi-bin/'

    def __init__(self, consumer_key, consumer_secret, callback=None):
        self._consumer = oauth.OAuthConsumer(consumer_key, consumer_secret)
        self._sigmethod = oauth.OAuthSignatureMethod_HMAC_SHA1()
        self.request_token = None
        self.access_token = None
        self.callback = callback or 'null'  # fixed
        self.username = None

    def _get_oauth_url(self, endpoint):
        if endpoint in ('request_token', 'access_token'):
            prefix = 'https://'
        else:
            prefix = 'http://'
        return prefix + self.OAUTH_HOST + self.OAUTH_ROOT + endpoint

    def apply_auth_headers(self, url, method, headers, parameters):
        """applay auth to request headers
        QQ weibo doesn't support it.
        """
        request = oauth.OAuthRequest.from_consumer_and_token(
            self._consumer, http_url=url, http_method=method,
            token=self.access_token, parameters=parameters
        )
        request.sign_request(self._sigmethod, self._consumer, self.access_token)
        headers.update(request.to_header())

    def get_signed_url(self, url, method, headers, parameters):
        """only sign url, no authentication"""
        # OAuthRequest(http_method, http_url, parameters)
        request = oauth.OAuthRequest(http_method=method, http_url=url, parameters=parameters)
        request.sign_request(self._sigmethod, self._consumer, self.access_token)
        return request.to_url()

    def get_authed_url(self, url, method, headers, parameters):
        """auth + sign"""
        request = oauth.OAuthRequest.from_consumer_and_token(
            self._consumer, http_url=url, http_method=method,
            token=self.access_token, parameters=parameters
        )
        request.sign_request(self._sigmethod, self._consumer, self.access_token)
        return request.to_url()

    def _get_request_token(self):
        try:
            url = self._get_oauth_url('request_token')
            request = oauth.OAuthRequest.from_consumer_and_token(
                self._consumer, http_url=url, callback=self.callback
            )
            request.sign_request(self._sigmethod, self._consumer, None)
            resp = urlopen(Request(request.to_url()))

            return oauth.OAuthToken.from_string(resp.read().decode('ascii'))
        except RuntimeError as e:
            raise QWeiboError(e)

    def set_request_token(self, key, secret):
        self.request_token = oauth.OAuthToken(key, secret)
    ###
    def set_req_token(self, token):
        self.request_token = token

    def set_access_token(self, key, secret):
        self.access_token = oauth.OAuthToken(key, secret)

    def get_authorization_url(self, signin_with_weibo=False):
        """Get the authorization URL to redirect the user"""
        try:
            # get the request token
            self.request_token = self._get_request_token()

            # build auth request and return as url
            if signin_with_weibo:
                url = self._get_oauth_url('authenticate')
            else:
                url = self._get_oauth_url('authorize')
            request = oauth.OAuthRequest.from_token_and_callback(
                token=self.request_token, http_url=url, callback=self.callback
            )

            return request.to_url()
        except RuntimeError as e:
            raise QWeiboError(e)
    ###
    def get_auth_url(self):
        return self.get_authorization_url(), self.request_token

    def get_access_token(self, verifier=None):
        """
        After user has authorized the request token, get access token
        with user supplied verifier.
        """
        try:
            url = self._get_oauth_url('access_token')
            # build request
            request = oauth.OAuthRequest.from_consumer_and_token(
                self._consumer,
                token=self.request_token, http_url=url,
                verifier=str(verifier)
            )
            request.sign_request(self._sigmethod, self._consumer, self.request_token)
            # send request
            resp = urlopen(Request(request.to_url()))  # must
            self.access_token = oauth.OAuthToken.from_string(resp.read().decode('ascii'))

            #print ('Access token key: ' + str(self.access_token.key))
            #print ('Access token secret: ' + str(self.access_token.secret))

            return self.access_token
        except Exception as e:
            raise QWeiboError(e)

    def setToken(self, token, tokenSecret):
        self.access_token = oauth.OAuthToken(token, tokenSecret)

    def get_username(self):
        if self.username is None:
            api = API(self)
            user = api.user.info()
            if user:
                self.username = user.name
            else:
                raise QWeiboError("Unable to get username, invalid oauth token!")
        return self.username

########NEW FILE########
__FILENAME__ = binder
#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2009-2010 Joshua Roesslein
# Copyright 2011 andelf <andelf@gmail.com>
# See LICENSE for details.
# Time-stamp: <2011-06-08 23:21:45 andelf>

import time
import re

from compat import Request, urlopen, quote, urlencode
from error import QWeiboError
from utils import convert_to_utf8_str


re_path_template = re.compile('{\w+}')


def bind_api(**config):

    class APIMethod(object):

        path = config['path']
        payload_type = config.get('payload_type', None)
        payload_list = config.get('payload_list', False)
        allowed_param = config.get('allowed_param', [])
        method = config.get('method', 'GET')
        require_auth = config.get('require_auth', False)

        def __init__(self, api, args, kargs):
            # If authentication is required and no credentials
            # are provided, throw an error.
            if self.require_auth and not api.auth:
                raise QWeiboError('Authentication required!')

            self.api = api
            self.payload_format = api.parser.payload_format
            self.post_data = kargs.pop('post_data', None)
            self.retry_count = kargs.pop('retry_count', api.retry_count)
            self.retry_delay = kargs.pop('retry_delay', api.retry_delay)
            self.retry_errors = kargs.pop('retry_errors', api.retry_errors)
            self.headers = kargs.pop('headers', {})
            self.build_parameters(args, kargs)
            self.api_root = api.api_root

            # Perform any path variable substitution
            self.build_path()

            self.scheme = 'http://'

            self.host = api.host

            # Manually set Host header to fix an issue in python 2.5
            # or older where Host is set including the 443 port.
            # This causes Twitter to issue 301 redirect.
            # See Issue http://github.com/joshthecoder/tweepy/issues/#issue/12
            self.headers['Host'] = self.host

        def build_parameters(self, args, kargs):
            # bind here, as default
            self.parameters = {'format': self.payload_format}
            for idx, arg in enumerate(args):
                try:
                    self.parameters[self.allowed_param[idx]] = convert_to_utf8_str(arg)
                except IndexError:
                    raise QWeiboError('Too many parameters supplied!')

            for k, arg in kargs.items():
                if bool(arg) == False:
                    continue
                if k in self.parameters:
                    raise QWeiboError('Multiple values for parameter `%s` supplied!' % k)
                #if k not in self.allowed_param:
                #    raise QWeiboError('`%s` is not allowd in this API function.' % k)
                self.parameters[k] = convert_to_utf8_str(arg)

        def build_path(self):
            for variable in re_path_template.findall(self.path):
                name = variable.strip('{}')

                if name == 'user' and self.api.auth:
                    value = self.api.auth.get_username()
                else:
                    try:
                        value = quote(self.parameters[name])
                    except KeyError:
                        raise QWeiboError('No parameter value found for path variable: %s' % name)
                    del self.parameters[name]

                self.path = self.path.replace(variable, value)

        def execute(self):
            # Build the request URL
            url = self.api_root + self.path
            #if self.api.source is not None:
            #    self.parameters.setdefault('source',self.api.source)

            if len(self.parameters):
                if self.method == 'GET':
                    url = '%s?%s' % (url, urlencode(self.parameters))
                else:
                    self.headers.setdefault("User-Agent", "pyqqweibo")
                    if self.post_data is None:
                        self.headers.setdefault("Accept", "text/html")
                        self.headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
                        # asure in bytes format
                        self.post_data = urlencode(self.parameters).encode('ascii')
            # Query the cache if one is available
            # and this request uses a GET method.
            if self.api.cache and self.method == 'GET':
                cache_result = self.api.cache.get(url)
                # if cache result found and not expired, return it
                if cache_result:
                    # must restore api reference
                    if isinstance(cache_result, list):
                        for result in cache_result:
                            result._api = self.api
                    else:
                        cache_result._api = self.api
                    return cache_result
                #urllib.urlencode(self.parameters)
            # Continue attempting request until successful
            # or maximum number of retries is reached.
            sTime = time.time()
            retries_performed = 0
            while retries_performed < self.retry_count + 1:
                # Open connection
                # FIXME: add timeout
                # Apply authentication
                if self.require_auth and self.api.auth:
                    url_full = self.api.auth.get_authed_url(
                        self.scheme + self.host + url,
                        self.method, self.headers, self.parameters
                    )
                else:                   # this brunch is never accoured
                    url_full = self.api.auth.get_signed_url(
                        self.scheme + self.host + url,
                        self.method, self.headers, self.parameters
                    )
                try:
                    if self.method == 'POST':
                        req = Request(url_full, data=self.post_data, headers=self.headers)
                    else:
                        req = Request(url_full)
                    resp = urlopen(req)
                except Exception as e:
                    raise QWeiboError("Failed to request %s headers=%s %s" % \
                                      (url, self.headers, e))

                # Exit request loop if non-retry error code
                if self.retry_errors:
                    if resp.code not in self.retry_errors:
                        break
                else:
                    if resp.code == 200:
                        break

                # Sleep before retrying request again
                time.sleep(self.retry_delay)
                retries_performed += 1

            # If an error was returned, throw an exception
            body = resp.read()
            self.api.last_response = resp
            if self.api.log is not None:
                requestUrl = "URL:http://" + self.host + url
                eTime = '%.0f' % ((time.time() - sTime) * 1000)
                postData = ""
                if self.post_data is not None:
                    postData = ",post:" + self.post_data[:500]
                self.api.log.debug("%s, time: %s, %s result: %s" % (requestUrl, eTime, postData, body))

            retcode = 0
            errcode = 0
            # for py3k, ^_^
            if not hasattr(body, 'encode'):
                body = str(body, 'utf-8')
            if self.api.parser.payload_format == 'json':
                try:
                    # BUG: API BUG, refer api.doc.rst
                    if body.endswith('out of memery'):
                        body = body[:body.rfind('}')+1]
                    json = self.api.parser.parse_error(self, body)
                    retcode = json.get('ret', 0)
                    msg = json.get('msg', '')
                    # only in some post request
                    errcode = json.get('errcode', 0)
                except ValueError as e:
                    retcode = -1
                    msg = "Bad json format (%s)" % e
                finally:
                    if retcode + errcode != 0:
                        raise QWeiboError("Response error: %s. (ret=%s, errcode=%s)" % \
                                          (msg, retcode, errcode))

            # Parse the response payload
            result = self.api.parser.parse(self, body)

            # Store result into cache if one is available.
            if self.api.cache and self.method == 'GET' and result:
                self.api.cache.store(url, result)
            return result

    def _call(api, *args, **kargs):
        method = APIMethod(api, args, kargs)
        return method.execute()

    # make doc string
    if config.get('payload_list', False):
        rettype = '[%s]' % config.get('payload_type', None)
    else:
        rettype = str(config.get('payload_type', None))

    return _call


########NEW FILE########
__FILENAME__ = cache
# Tweepy
# Copyright 2009-2010 Joshua Roesslein
# Copyright 2011 andelf <andelf@gmail.com>
# See LICENSE for details.
# Time-stamp: <2011-06-08 15:08:40 andelf>

import time
import threading
import os
import hashlib

from compat import pickle
try:
    import fcntl
except ImportError:
    # Probably on a windows system
    # TODO: use win32file
    pass


class Cache(object):
    """Cache interface"""

    def __init__(self, timeout=60):
        """Initialize the cache
            timeout: number of seconds to keep a cached entry
        """
        self.timeout = timeout

    def store(self, key, value):
        """Add new record to cache
            key: entry key
            value: data of entry
        """
        raise NotImplementedError

    def get(self, key, timeout=None):
        """Get cached entry if exists and not expired
            key: which entry to get
            timeout: override timeout with this value [optional]
        """
        raise NotImplementedError

    def count(self):
        """Get count of entries currently stored in cache"""
        raise NotImplementedError

    def cleanup(self):
        """Delete any expired entries in cache."""
        raise NotImplementedError

    def flush(self):
        """Delete all cached entries"""
        raise NotImplementedError


class MemoryCache(Cache):
    """In-memory cache"""

    def __init__(self, timeout=60):
        Cache.__init__(self, timeout)
        self._entries = {}
        self.lock = threading.Lock()

    def __getstate__(self):
        # pickle
        return {'entries': self._entries, 'timeout': self.timeout}

    def __setstate__(self, state):
        # unpickle
        self.lock = threading.Lock()
        self._entries = state['entries']
        self.timeout = state['timeout']

    def _is_expired(self, entry, timeout):
        return timeout > 0 and (time.time() - entry[0]) >= timeout

    def store(self, key, value):
        self.lock.acquire()
        self._entries[key] = (time.time(), value)
        self.lock.release()

    def get(self, key, timeout=None):
        self.lock.acquire()
        try:
            # check to see if we have this key
            entry = self._entries.get(key)
            if not entry:
                # no hit, return nothing
                return None

            # use provided timeout in arguments if provided
            # otherwise use the one provided during init.
            if timeout is None:
                timeout = self.timeout

            # make sure entry is not expired
            if self._is_expired(entry, timeout):
                # entry expired, delete and return nothing
                del self._entries[key]
                return None

            # entry found and not expired, return it
            return entry[1]
        finally:
            self.lock.release()

    def count(self):
        return len(self._entries)

    def cleanup(self):
        self.lock.acquire()
        try:
            for k, v in self._entries.items():
                if self._is_expired(v, self.timeout):
                    del self._entries[k]
        finally:
            self.lock.release()

    def flush(self):
        self.lock.acquire()
        self._entries.clear()
        self.lock.release()


class FileCache(Cache):
    """File-based cache"""

    # locks used to make cache thread-safe
    cache_locks = {}

    def __init__(self, cache_dir, timeout=60):
        Cache.__init__(self, timeout)
        if os.path.exists(cache_dir) is False:
            os.mkdir(cache_dir)
        self.cache_dir = cache_dir
        if cache_dir in FileCache.cache_locks:
            self.lock = FileCache.cache_locks[cache_dir]
        else:
            self.lock = threading.Lock()
            FileCache.cache_locks[cache_dir] = self.lock

        if os.name == 'posix':
            self._lock_file = self._lock_file_posix
            self._unlock_file = self._unlock_file_posix
        elif os.name == 'nt':
            self._lock_file = self._lock_file_win32
            self._unlock_file = self._unlock_file_win32
        else:
            print ('Warning! FileCache locking not supported on this system!')
            self._lock_file = self._lock_file_dummy
            self._unlock_file = self._unlock_file_dummy

    def _get_path(self, key):
        md5 = hashlib.md5()
        # fixed for py3.x
        md5.update(key.encode('utf-8'))
        return os.path.join(self.cache_dir, md5.hexdigest())

    def _lock_file_dummy(self, path, exclusive=True):
        return None

    def _unlock_file_dummy(self, lock):
        return

    def _lock_file_posix(self, path, exclusive=True):
        lock_path = path + '.lock'
        if exclusive is True:
            f_lock = open(lock_path, 'w')
            fcntl.lockf(f_lock, fcntl.LOCK_EX)
        else:
            f_lock = open(lock_path, 'r')
            fcntl.lockf(f_lock, fcntl.LOCK_SH)
        if os.path.exists(lock_path) is False:
            f_lock.close()
            return None
        return f_lock

    def _unlock_file_posix(self, lock):
        lock.close()

    def _lock_file_win32(self, path, exclusive=True):
        # TODO: implement
        return None

    def _unlock_file_win32(self, lock):
        # TODO: implement
        return

    def _delete_file(self, path):
        os.remove(path)
        if os.path.exists(path + '.lock'):
            os.remove(path + '.lock')

    def store(self, key, value):
        path = self._get_path(key)
        self.lock.acquire()
        try:
            # acquire lock and open file
            f_lock = self._lock_file(path)
            datafile = open(path, 'wb')

            # write data
            pickle.dump((time.time(), value), datafile)

            # close and unlock file
            datafile.close()
            self._unlock_file(f_lock)
        finally:
            self.lock.release()

    def get(self, key, timeout=None):
        return self._get(self._get_path(key), timeout)

    def _get(self, path, timeout):
        if os.path.exists(path) is False:
            # no record
            return None
        self.lock.acquire()
        try:
            # acquire lock and open
            f_lock = self._lock_file(path, False)
            datafile = open(path, 'rb')

            # read pickled object
            created_time, value = pickle.load(datafile)
            datafile.close()

            # check if value is expired
            if timeout is None:
                timeout = self.timeout
            if timeout > 0 and (time.time() - created_time) >= timeout:
                # expired! delete from cache
                value = None
                self._delete_file(path)

            # unlock and return result
            self._unlock_file(f_lock)
            return value
        finally:
            self.lock.release()

    def count(self):
        c = 0
        for entry in os.listdir(self.cache_dir):
            if entry.endswith('.lock'):
                continue
            c += 1
        return c

    def cleanup(self):
        for entry in os.listdir(self.cache_dir):
            if entry.endswith('.lock'):
                continue
            self._get(os.path.join(self.cache_dir, entry), None)

    def flush(self):
        for entry in os.listdir(self.cache_dir):
            if entry.endswith('.lock'):
                continue
            self._delete_file(os.path.join(self.cache_dir, entry))


########NEW FILE########
__FILENAME__ = compat
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2011 andelf <andelf@gmail.com>
# See LICENSE for details.
# Time-stamp: <2011-06-04 01:55:58 andelf>

try:
    from urllib2 import Request, urlopen
    import urlparse
    from urllib import quote, unquote, urlencode
    import htmlentitydefs
    from cgi import parse_qs
except ImportError:
    from urllib.request import Request, urlopen
    import urllib.parse as urlparse
    from urllib.parse import quote, unquote, urlencode, parse_qs
    import html.entities as htmlentitydefs

try:
    import cPickle as pickle
except ImportError:
    import pickle


def import_simplejson():
    try:
        import simplejson as json
    except ImportError:
        try:
            import json  # Python 2.6+
        except ImportError:
            try:
                from django.utils import simplejson as json  # Google App Engine
            except ImportError:
                raise ImportError("Can't load a json library")

    return json

json = import_simplejson()


########NEW FILE########
__FILENAME__ = error
#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2010 andelf <andelf@gmail.com>
# See LICENSE for details.
# Time-stamp: <2011-06-08 15:15:00 andelf>

class QWeiboError(Exception):
    """basic weibo error class"""
    pass


def assertion(condition, msg):
    try:
        assert condition, msg
    except AssertionError as e:
        raise QWeiboError(e.message)


########NEW FILE########
__FILENAME__ = models
#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2009-2010 Joshua Roesslein
# Copyright 2011 andelf <andelf@gmail.com>
# See LICENSE for details.
# Time-stamp: <2011-06-07 12:05:46 andelf>

from utils import (parse_datetime, parse_html_value, parse_a_href,
                           parse_search_datetime, unescape_html)
from error import assertion, QWeiboError


class ResultSet(list):
    """A list like object that holds results from a Twitter API query."""


class Model(object):

    def __init__(self, api=None):
        self._api = api

    def __getstate__(self):
        # pickle
        pickle = dict(self.__dict__)
        del pickle['_api']  # do not pickle the API reference
        return pickle

    def as_dict(self):
        ret = dict(self.__dict__)
        # py3k fixed, in py3k, .keys() will be a dict_keys obj
        for k in list(ret.keys()):
            if k.startswith('_'):
                del ret[k]
            elif k == 'as_dict':
                del ret[k]
        return ret

    @classmethod
    def parse(cls, api, json):
        """Parse a JSON object into a model instance."""
        raise NotImplementedError

    @classmethod
    def parse_list(cls, api, json_list):
        """Parse a list of JSON objects into a result set of
        model instances."""
        results = ResultSet()
        if json_list:                   # or return empty ResultSet
            for obj in json_list:
                results.append(cls.parse(api, obj))
        return results


class Tweet(Model):

    def __repr__(self):
        return '<Tweet object #%s>' % (self.id or 'unkownID')

    @classmethod
    def parse(cls, api, json):
        if not json:
            return None
        tweet = cls(api)
        for k, v in json.items():
            if k == 'source':
                source = Tweet.parse(api, v)
                setattr(tweet, 'source', source)
            elif k == 'video':
                video = Video.parse(api, v) if v else None
                setattr(tweet, 'video', video)
            elif k in ('isvip', 'self'):
                setattr(tweet, k, bool(v))
            elif k == 'from':
                setattr(tweet, 'from_', v)  # avoid keyword
            elif k == 'tweetid':
                #setattr(tweet, k, v)
                setattr(tweet, 'id', v)
            elif '_' in k:
                # avoid xxxx_xxxx
                setattr(tweet, k.replace('_', ''), v)
            else:
                setattr(tweet, k, v)
        return tweet

    def delete(self):
        if self.self:
            return self._api.t.delete(self.id)
        else:
            raise QWeiboError("You can't delete others' tweet")

    def retweet(self, content, clientip='127.0.0.1', jing=None, wei=None):
        return self._api.t.retweet(content=content, clientip=clientip,
                                   jing=jing, wei=wei, reid=self.id)

    def reply(self, content, clientip='127.0.0.1', jing=None, wei=None):
        return self._api.t.reply(content=content, clientip=clientip, jing=jing,
                                 wei=wei, reid=self.id)

    def comment(self, content, clientip='127.0.0.1', jing=None, wei=None):
        return self._api.t.comment(content=content, clientip=clientip,
                                   jing=jing, wei=wei, reid=self.id)

    def retweetlist(self, *args, **kwargs):
        return self._api.t.retweetlist(self.id, *args, **kwargs)

    def retweetcount(self, *args, **kwargs):
        return self._api.t.retweetcount(self.id, *args, **kwargs)[str(self.id)]

    def favorite(self, fav=True):
        if fav:
            return self._api.fav.addtweet(self.id)
        else:
            return self.unfavorite()

    def unfavorite(self):
        return self._api.fav.deletetweet(self.id)


class Geo(Model):
    """ current useless"""
    @classmethod
    def parse(cls, api, json):
        geo = cls(api)
        if json:
            for k, v in json.items():
                setattr(geo, k, v)
        return geo


class User(Model):

    def __repr__(self):
        return '<User object #%s>' % self.name

    @classmethod
    def parse(cls, api, json):
        user = cls(api)
        for k, v in json.items():
            if k in ('isvip', 'isent',):
                setattr(user, k, bool(v))
            elif k == 'tag':
                tags = TagModel.parse_list(api, v)
                setattr(user, k, tags)
            elif k in ('Ismyblack', 'Ismyfans', 'Ismyidol'):
                # fix name bug
                setattr(user, k.lower(), bool(v))
            elif k == 'isidol':
                setattr(user, 'ismyidol', bool(v))
            elif '_' in k:
                # avoid xxxx_xxxx
                setattr(user, k.replace('_', ''), v)
            elif k == 'tweet':
                tweet = Tweet.parse_list(api, v)  # only 1 item
                setattr(user, k, tweet[0] if tweet else tweet)
            else:
                setattr(user, k, v)

        # FIXME, need better way
        if hasattr(user, 'ismyidol'):
            setattr(user, 'self', False)  # is this myself?
        else:
            setattr(user, 'self', True)

        return user

    def update(self, **kwargs):
        assertion(self.self, "you can only update youself's profile")

        nick = self.nick = kwargs.get('nick', self.nick)
        sex = self.sex = kwargs.get('sex', self.sex)
        year = self.birthyear = kwargs.get('year', self.birthyear)
        month = self.birthmonth = kwargs.get('month', self.birthmonth)
        day = self.birthday = kwargs.get('day', self.birthday)
        countrycode = self.countrycode = kwargs.get('countrycode',
                                                    self.countrycode)
        provincecode = self.provincecode = kwargs.get('provincecode',
                                                      self.provincecode)
        citycode = self.citycode = kwargs.get('citycode', self.citycode)
        introduction = self.introduction = kwargs.get('introduction',
                                                      self.introduction)
        self._api.user.update(nick, sex, year, month, day, countrycode,
                              provincecode, citycode, introduction)

    def timeline(self, **kargs):
        return self._api.timeline.user(name=self.name, **kargs)

    def add(self):
        """收听某个用户"""
        assertion(not bool(self.self), "you can't follow your self")
        if self.ismyidol:
            return                      # already flollowed
        else:
            self._api.friends.add(name=self.name)
    follow = add

    def delete(self):
        """取消收听某个用户"""
        assertion(not bool(self.self), "you can't unfollow your self")
        if self.ismyidol:
            self._api.friends.delete(name=self.name)
        else:
            pass
    unfollow = delete

    def addspecial(self):
        """特别收听某个用户"""
        assertion(not bool(self.self), "you can't follow yourself")
        self._api.friends.addspecial(name=self.name)

    def deletespecial(self):
        """取消特别收听某个用户"""
        assertion(not bool(self.self), "you can't follow yourself")
        self._api.friends.deletespecial(name=self.name)

    def addblacklist(self):
        """添加某个用户到黑名单"""
        assertion(not bool(self.self), "you can't block yourself")
        self._api.friends.addblacklist(name=self.name)
    block = addblacklist

    def deleteblacklist(self):
        """从黑名单中删除某个用户"""
        assertion(not bool(self.self), "you can't block yourself")
        self._api.friends.deleteblacklist(name=self.name)
    unblock = deleteblacklist

    def fanslist(self, *args, **kwargs):
        """帐户听众列表, 自己或者别人"""
        if self.self:
            return self._api.friends.fanslist(*args, **kwargs)
        else:
            return self._api.friends.userfanslist(self.name, *args, **kwargs)
    followers = fanslist

    def idollist(self, *args, **kwargs):
        """帐户收听的人列表, 自己或者别人"""
        if self.self:
            return self._api.friends.idollist(*args, **kwargs)
        else:
            return self._api.friends.useridollist(self.name, *args, **kwargs)
    followees = idollist

    def speciallist(self, *args, **kwargs):
        """帐户特别收听的人列表, 自己或者别人"""
        if self.self:
            return self._api.friends.speciallist(*args, **kwargs)
        else:
            return self._api.friends.userspeciallist(self.name, *args, **kwargs)

    def pm(self, content, clientip='127.0.0.1', jing=None, wei=None):
        """发私信"""
        assertion(not bool(self.self), "you can't pm yourself")
        return self._api.private.add(self.name, content, clientip, jing, wei)

    def headimg(self, size=100):
        assertion(size in [20, 30, 40, 50, 100],
                  'size must be one of 20 30 40 50 100')
        return '%s/%s' % (self.head, size)


class JSON(Model):

    def __repr__(self):
        if 'id' in self.__dict__:
            return "<%s object #%s>" % (type(self).__name__, self.id)
        else:
            return object.__repr__(self)

    @classmethod
    def parse(cls, api, json):
        lst = JSON(api)
        for k, v in json.items():
            if k == 'tweetid':
                setattr(lst, k, v)
                setattr(lst, 'id', v)   # make `id` always useable
            else:
                setattr(lst, k, v)
        return lst


class RetId(Model):
    def __repr__(self):
        return "<RetId id:%s>" % self.id

    @classmethod
    def parse(cls, api, json):
        lst = RetId(api)
        for k, v in json.items():
            if k == 'tweetid':
                setattr(lst, k, v)
                setattr(lst, 'id', v)   # make `id` always useable
            elif k == 'time':
                setattr(lst, k, v)
                setattr(lst, 'timestamp', v)
            else:
                setattr(lst, k, v)
        return lst

    def as_tweet(self):
        return self._api.tweet.show(self.id)


class Video(Model):
    def __repr__(self):
        return "<Video object #%s>" % self.realurl

    @classmethod
    def parse(cls, api, json):
        lst = Video(api)
        for k, v in json.items():
            # FIX bug names
            if k == 'real':
                k = 'realurl'
            elif k == 'short':
                k = 'shorturl'
            elif k == 'minipic':
                k = 'picurl'
            setattr(lst, k, v)
        return lst


class TagModel(JSON):
    def __repr__(self):
        return '<Tag object #%s>' % self.id

    @classmethod
    def parse(cls, api, json):
        tag = TagModel(api)
        for k, v in json.items():
                setattr(tag, k, v)
        return tag

    def add(self):
        return self._api.tag.add(self.id)

    def delete(self):
        return self._api.tag.delete(self.id)


class Topic(JSON):
    def __repr__(self):
        return '<Topic object #%s>' % self.id

    @classmethod
    def parse(cls, api, json):
        tag = Topic(api)
        for k, v in json.items():
                setattr(tag, k, v)
        return tag


class ModelFactory(object):
    """
    Used by parsers for creating instances
    of models. You may subclass this factory
    to add your own extended models.
    """

    tweet = Tweet
    user = User
    video = Video
    json = JSON
    retid = RetId

########NEW FILE########
__FILENAME__ = oauth
# Copyright 2007 Leah Culver
# Copyright 2011 andelf <andelf@gmail.com>
# Time-stamp: <2011-06-04 10:08:18 andelf>
"""
The MIT License

Copyright (c) 2007 Leah Culver

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
THE SOFTWARE.
"""


import time
import random
import hmac
import binascii
# drop support for py2.5-
import hashlib

from compat import (urlparse, quote, unquote, urlencode, parse_qs)
from utils import convert_to_utf8_str


VERSION = '1.0'  # Hi Blaine!
HTTP_METHOD = 'GET'
SIGNATURE_METHOD = 'PLAINTEXT'


class OAuthError(RuntimeError):
    """Generic exception class."""
    def __init__(self, message='OAuth error occured.'):
        self.message = message


def build_authenticate_header(realm=''):
    """Optional WWW-Authenticate header (401 error)"""
    return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}


def escape(s):
    """Escape a URL including any /.
    return py2str py3str
    """
    # py3k
    if hasattr(str, 'decode') and type(s) != str:
        # FIXME assume py2unicode
        s = s.encode('utf-8')
    ret = quote(s, safe='~')
    if type(ret) != str:
        return str(ret)
    return ret


def _utf8_str(s):
    """Convert unicode to utf-8."""
    if not hasattr(__builtins__, 'unicode'):
        # py3k
        return str(s)
    elif type(s) == getattr(__builtins__, 'unicode'):
        return s.encode("utf-8")
    return str(s)


def generate_timestamp():
    """Get seconds since epoch (UTC)."""
    return int(time.time())


def generate_nonce(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


def generate_verifier(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


class OAuthConsumer(object):
    """Consumer of OAuth authentication.

    OAuthConsumer is a data type that represents the identity of the Consumer
    via its shared secret with the Service Provider.

    """
    key = None
    secret = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret


class OAuthToken(object):
    """OAuthToken is a data type that represents an End User via either
    an access or request token.

    key -- the token
    secret -- the token secret

    """
    key = None
    secret = None
    callback = None
    callback_confirmed = None
    verifier = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret

    def set_callback(self, callback):
        self.callback = callback
        self.callback_confirmed = 'true'

    def set_verifier(self, verifier=None):
        if verifier is not None:
            self.verifier = verifier
        else:
            self.verifier = generate_verifier()

    def get_callback_url(self):
        if self.callback and self.verifier:
            # Append the oauth_verifier.
            parts = urlparse.urlparse(self.callback)
            scheme, netloc, path, params, query, fragment = parts[:6]
            if query:
                query = '%s&oauth_verifier=%s' % (query, self.verifier)
            else:
                query = 'oauth_verifier=%s' % self.verifier
            return urlparse.urlunparse((scheme, netloc, path, params,
                query, fragment))
        return self.callback

    def to_string(self):
        data = {
            'oauth_token': self.key,
            'oauth_token_secret': self.secret,
        }
        if self.callback_confirmed is not None:
            data['oauth_callback_confirmed'] = self.callback_confirmed
        return urlencode(data)

    def from_string(s):
        """ Returns a token from something like:
        oauth_token_secret=xxx&oauth_token=xxx
        """
        params = parse_qs(s, keep_blank_values=False)
        key = params['oauth_token'][0]
        secret = params['oauth_token_secret'][0]
        token = OAuthToken(key, secret)
        try:
            token.callback_confirmed = params[b'oauth_callback_confirmed'][0]
        except KeyError:
            pass  # 1.0, no callback confirmed.
        return token
    from_string = staticmethod(from_string)

    def __str__(self):
        return self.to_string()


class OAuthRequest(object):
    """OAuthRequest represents the request and can be serialized.

    OAuth parameters:
        - oauth_consumer_key
        - oauth_token
        - oauth_signature_method
        - oauth_signature
        - oauth_timestamp
        - oauth_nonce
        - oauth_version
        - oauth_verifier
        ... any additional parameters, as defined by the Service Provider.
    """
    parameters = None  # OAuth parameters.
    http_method = HTTP_METHOD
    http_url = None
    version = VERSION

    def __init__(self, http_method=HTTP_METHOD, http_url=None, parameters=None):
        self.http_method = http_method
        self.http_url = http_url
        self.parameters = parameters or {}

    def set_parameter(self, parameter, value):
        self.parameters[parameter] = value

    def get_parameter(self, parameter):
        try:
            return self.parameters[parameter]
        except:
            raise OAuthError('Parameter not found: %s' % parameter)

    def _get_timestamp_nonce(self):
        return self.get_parameter('oauth_timestamp'), self.get_parameter(
            'oauth_nonce')

    def get_nonoauth_parameters(self):
        """Get any non-OAuth parameters."""
        parameters = {}
        for k, v in self.parameters.items():
            # Ignore oauth parameters.
            if k.find('oauth_') < 0:
                parameters[k] = v
        return parameters

    def to_header(self, realm=''):
        """Serialize as a header for an HTTPAuth request."""
        auth_header = 'OAuth realm="%s"' % realm
        # Add the oauth parameters.
        if self.parameters:
            for k, v in self.parameters.items():
                if k[:6] == 'oauth_':
                    auth_header += ', %s="%s"' % (k, escape(str(v)))
        return {'Authorization': auth_header}

    def to_postdata(self):
        """Serialize as post data for a POST request."""
        return '&'.join(['%s=%s' % (escape(convert_to_utf8_str(k)),
                                    escape(convert_to_utf8_str(v))) \
            for k, v in self.parameters.items()])

    def to_url(self):
        """Serialize as a URL for a GET request."""
        return '%s?%s' % (self.get_normalized_http_url(), self.to_postdata())

    def get_normalized_parameters(self):
        """Return a string that contains the parameters that must be signed."""
        params = self.parameters
        try:
            # Exclude the signature if it exists.
            del params['oauth_signature']
        except:
            pass
        # Escape key values before sorting.
        key_values = [(escape(convert_to_utf8_str(k)),
                       escape(convert_to_utf8_str(v))) \
            for k, v in params.items()]
        # Sort lexicographically, first after key, then after value.
        key_values.sort()
        # Combine key value pairs into a string.
        return '&'.join(['%s=%s' % (k, v) for k, v in key_values])

    def get_normalized_http_method(self):
        """Uppercases the http method."""
        return self.http_method.upper()

    def get_normalized_http_url(self):
        """Parses the URL and rebuilds it to be scheme://host/path."""
        parts = urlparse.urlparse(self.http_url)
        scheme, netloc, path = parts[:3]
        # Exclude default port numbers.
        if scheme == 'http' and netloc[-3:] == ':80':
            netloc = netloc[:-3]
        elif scheme == 'https' and netloc[-4:] == ':443':
            netloc = netloc[:-4]
        return '%s://%s%s' % (scheme, netloc, path)

    def sign_request(self, signature_method, consumer, token):
        """Set the signature parameter to the result of build_signature."""
        # Set the signature method.
        self.set_parameter('oauth_signature_method',
            signature_method.get_name())
        # Set the signature.
        self.set_parameter('oauth_signature',
            self.build_signature(signature_method, consumer, token))

    def build_signature(self, signature_method, consumer, token):
        """Calls the build signature method within the signature method."""
        return signature_method.build_signature(self, consumer, token)

    def from_request(http_method, http_url, headers=None, parameters=None,
            query_string=None):
        """Combines multiple parameter sources."""
        if parameters is None:
            parameters = {}

        # Headers
        if headers and 'Authorization' in headers:
            auth_header = headers['Authorization']
            # Check that the authorization header is OAuth.
            if auth_header[:6] == 'OAuth ':
                auth_header = auth_header[6:]
                try:
                    # Get the parameters from the header.
                    header_params = OAuthRequest._split_header(auth_header)
                    parameters.update(header_params)
                except:
                    raise OAuthError('Unable to parse OAuth parameters from '
                        'Authorization header.')

        # GET or POST query string.
        if query_string:
            query_params = OAuthRequest._split_url_string(query_string)
            parameters.update(query_params)

        # URL parameters.
        param_str = urlparse.urlparse(http_url)[4]  # query
        url_params = OAuthRequest._split_url_string(param_str)
        parameters.update(url_params)

        if parameters:
            return OAuthRequest(http_method, http_url, parameters)

        return None
    from_request = staticmethod(from_request)

    def from_consumer_and_token(oauth_consumer, token=None,
            callback=None, verifier=None, http_method=HTTP_METHOD,
            http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        defaults = {
            'oauth_consumer_key': oauth_consumer.key,
            'oauth_timestamp': generate_timestamp(),
            'oauth_nonce': generate_nonce(),
            'oauth_version': OAuthRequest.version,
        }

        defaults.update(parameters)
        parameters = defaults

        if token:
            parameters['oauth_token'] = token.key
            if token.callback:
                parameters['oauth_callback'] = token.callback
            # 1.0a support for verifier.
            if verifier:
                parameters['oauth_verifier'] = verifier
        elif callback:
            # 1.0a support for callback in the request token request.
            parameters['oauth_callback'] = callback

        return OAuthRequest(http_method, http_url, parameters)
    from_consumer_and_token = staticmethod(from_consumer_and_token)

    def from_token_and_callback(token, callback=None, http_method=HTTP_METHOD,
            http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        parameters['oauth_token'] = token.key

        if callback:
            parameters['oauth_callback'] = callback

        return OAuthRequest(http_method, http_url, parameters)
    from_token_and_callback = staticmethod(from_token_and_callback)

    def _split_header(header):
        """Turn Authorization: header into parameters."""
        params = {}
        parts = header.split(',')
        for param in parts:
            # Ignore realm parameter.
            if param.find('realm') > -1:
                continue
            # Remove whitespace.
            param = param.strip()
            # Split key-value.
            param_parts = param.split('=', 1)
            # Remove quotes and unescape the value.
            params[param_parts[0]] = unquote(param_parts[1].strip('\"'))
        return params
    _split_header = staticmethod(_split_header)

    def _split_url_string(param_str):
        """Turn URL string into parameters."""
        parameters = parse_qs(param_str, keep_blank_values=False)
        for k, v in parameters.items():
            parameters[k] = unquote(v[0])
        return parameters
    _split_url_string = staticmethod(_split_url_string)


class OAuthServer(object):
    """A worker to check the validity of a request against a data store."""
    timestamp_threshold = 300  # In seconds, five minutes.
    version = VERSION
    signature_methods = None
    data_store = None

    def __init__(self, data_store=None, signature_methods=None):
        self.data_store = data_store
        self.signature_methods = signature_methods or {}

    def set_data_store(self, data_store):
        self.data_store = data_store

    def get_data_store(self):
        return self.data_store

    def add_signature_method(self, signature_method):
        self.signature_methods[signature_method.get_name()] = signature_method
        return self.signature_methods

    def fetch_request_token(self, oauth_request):
        """Processes a request_token request and returns the
        request token on success.
        """
        try:
            # Get the request token for authorization.
            token = self._get_token(oauth_request, 'request')
        except OAuthError:
            # No token required for the initial token request.
            consumer = self._get_consumer(oauth_request)
            try:
                callback = self.get_callback(oauth_request)
            except OAuthError:
                callback = None  # 1.0, no callback specified.
            self._check_signature(oauth_request, consumer, None)
            # Fetch a new token.
            token = self.data_store.fetch_request_token(consumer, callback)
        return token

    def fetch_access_token(self, oauth_request):
        """Processes an access_token request and returns the
        access token on success.
        """
        consumer = self._get_consumer(oauth_request)
        try:
            verifier = self._get_verifier(oauth_request)
        except OAuthError:
            verifier = None
        # Get the request token.
        token = self._get_token(oauth_request, 'request')
        self._check_signature(oauth_request, consumer, token)
        new_token = self.data_store.fetch_access_token(consumer, token, verifier)
        return new_token

    def verify_request(self, oauth_request):
        """Verifies an api call and checks all the parameters."""
        # -> consumer and token
        consumer = self._get_consumer(oauth_request)
        # Get the access token.
        token = self._get_token(oauth_request, 'access')
        self._check_signature(oauth_request, consumer, token)
        parameters = oauth_request.get_nonoauth_parameters()
        return consumer, token, parameters

    def authorize_token(self, token, user):
        """Authorize a request token."""
        return self.data_store.authorize_request_token(token, user)

    def get_callback(self, oauth_request):
        """Get the callback URL."""
        return oauth_request.get_parameter('oauth_callback')

    def build_authenticate_header(self, realm=''):
        """Optional support for the authenticate header."""
        return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

    def _get_version(self, oauth_request):
        """Verify the correct version request for this server."""
        try:
            version = oauth_request.get_parameter('oauth_version')
        except:
            version = VERSION
        if version and version != self.version:
            raise OAuthError('OAuth version %s not supported.' % str(version))
        return version

    def _get_signature_method(self, oauth_request):
        """Figure out the signature with some defaults."""
        try:
            signature_method = oauth_request.get_parameter(
                'oauth_signature_method')
        except:
            signature_method = SIGNATURE_METHOD
        try:
            # Get the signature method object.
            signature_method = self.signature_methods[signature_method]
        except:
            signature_method_names = ', '.join(self.signature_methods.keys())
            raise OAuthError('Signature method %s not supported try one of the '
                'following: %s' % (signature_method, signature_method_names))

        return signature_method

    def _get_consumer(self, oauth_request):
        consumer_key = oauth_request.get_parameter('oauth_consumer_key')
        consumer = self.data_store.lookup_consumer(consumer_key)
        if not consumer:
            raise OAuthError('Invalid consumer.')
        return consumer

    def _get_token(self, oauth_request, token_type='access'):
        """Try to find the token for the provided request token key."""
        token_field = oauth_request.get_parameter('oauth_token')
        token = self.data_store.lookup_token(token_type, token_field)
        if not token:
            raise OAuthError('Invalid %s token: %s' % (token_type, token_field))
        return token

    def _get_verifier(self, oauth_request):
        return oauth_request.get_parameter('oauth_verifier')

    def _check_signature(self, oauth_request, consumer, token):
        timestamp, nonce = oauth_request._get_timestamp_nonce()
        self._check_timestamp(timestamp)
        self._check_nonce(consumer, token, nonce)
        signature_method = self._get_signature_method(oauth_request)
        try:
            signature = oauth_request.get_parameter('oauth_signature')
        except:
            raise OAuthError('Missing signature.')
        # Validate the signature.
        valid_sig = signature_method.check_signature(oauth_request, consumer,
            token, signature)
        if not valid_sig:
            key, base = signature_method.build_signature_base_string(
                oauth_request, consumer, token)
            raise OAuthError('Invalid signature. Expected signature base '
                'string: %s' % base)
        signature_method.build_signature(oauth_request, consumer, token)

    def _check_timestamp(self, timestamp):
        """Verify that timestamp is recentish."""
        timestamp = int(timestamp)
        now = int(time.time())
        lapsed = abs(now - timestamp)
        if lapsed > self.timestamp_threshold:
            raise OAuthError('Expired timestamp: given %d and now %s has a '
                'greater difference than threshold %d' %
                (timestamp, now, self.timestamp_threshold))

    def _check_nonce(self, consumer, token, nonce):
        """Verify that the nonce is uniqueish."""
        nonce = self.data_store.lookup_nonce(consumer, token, nonce)
        if nonce:
            raise OAuthError('Nonce already used: %s' % str(nonce))


class OAuthClient(object):
    """OAuthClient is a worker to attempt to execute a request."""
    consumer = None
    token = None

    def __init__(self, oauth_consumer, oauth_token):
        self.consumer = oauth_consumer
        self.token = oauth_token

    def get_consumer(self):
        return self.consumer

    def get_token(self):
        return self.token

    def fetch_request_token(self, oauth_request):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_access_token(self, oauth_request):
        """-> OAuthToken."""
        raise NotImplementedError

    def access_resource(self, oauth_request):
        """-> Some protected resource."""
        raise NotImplementedError


class OAuthDataStore(object):
    """A database abstraction used to lookup consumers and tokens."""

    def lookup_consumer(self, key):
        """-> OAuthConsumer."""
        raise NotImplementedError

    def lookup_token(self, oauth_consumer, token_type, token_token):
        """-> OAuthToken."""
        raise NotImplementedError

    def lookup_nonce(self, oauth_consumer, oauth_token, nonce):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_request_token(self, oauth_consumer, oauth_callback):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_access_token(self, oauth_consumer, oauth_token, oauth_verifier):
        """-> OAuthToken."""
        raise NotImplementedError

    def authorize_request_token(self, oauth_token, user):
        """-> OAuthToken."""
        raise NotImplementedError


class OAuthSignatureMethod(object):
    """A strategy class that implements a signature method."""
    def get_name(self):
        """-> str."""
        raise NotImplementedError

    def build_signature_base_string(self, oauth_request, oauth_consumer, oauth_token):
        """-> str key, str raw."""
        raise NotImplementedError

    def build_signature(self, oauth_request, oauth_consumer, oauth_token):
        """-> str."""
        raise NotImplementedError

    def check_signature(self, oauth_request, consumer, token, signature):
        built = self.build_signature(oauth_request, consumer, token)
        return built == signature


class OAuthSignatureMethod_HMAC_SHA1(OAuthSignatureMethod):

    def get_name(self):
        return 'HMAC-SHA1'

    def build_signature_base_string(self, oauth_request, consumer, token):
        sig = (
            escape(oauth_request.get_normalized_http_method()),
            escape(oauth_request.get_normalized_http_url()),
            escape(oauth_request.get_normalized_parameters()),
        )
        key = '%s&' % escape(consumer.secret)
        if token:
            key += escape(token.secret)
        raw = '&'.join(sig)
        return key, raw

    def build_signature(self, oauth_request, consumer, token):
        """Builds the base signature string."""
        key, raw = self.build_signature_base_string(oauth_request, consumer,
            token)
        # HMAC object.
        hashed = hmac.new(key.encode('ascii'), raw.encode('ascii'), hashlib.sha1)
        # Calculate the digest base 64.
        #return binascii.b2a_base64(hashed.digest())[:-1]
        # fix py3k, str() on a bytes obj will be a "b'...'"
        ret = binascii.b2a_base64(hashed.digest())[:-1]
        return ret.decode('ascii')


class OAuthSignatureMethod_PLAINTEXT(OAuthSignatureMethod):

    def get_name(self):
        return 'PLAINTEXT'

    def build_signature_base_string(self, oauth_request, consumer, token):
        """Concatenates the consumer key and secret."""
        sig = '%s&' % escape(consumer.secret)
        if token:
            sig = sig + escape(token.secret)
        return sig, sig

    def build_signature(self, oauth_request, consumer, token):
        key, raw = self.build_signature_base_string(oauth_request, consumer,
            token)
        return key

########NEW FILE########
__FILENAME__ = parsers
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2009-2010 Joshua Roesslein
# Copyright 2011 andelf <andelf@gmail.com>
# See LICENSE for details.
# Time-stamp: <2011-06-08 23:25:48 andelf>

import xml.dom.minidom as dom
import xml.etree.ElementTree as ET

from compat import json
from models import ModelFactory
from error import QWeiboError


class Parser(object):

    def parse(self, method, payload):
        """
        Parse the response payload and return the result.
        Returns a tuple that contains the result data and the cursors
        (or None if not present).
        """
        raise NotImplementedError

    def parse_error(self, method, payload):
        """
        Parse the error message from payload.
        If unable to parse the message, throw an exception
        and default error message will be used.
        """
        raise NotImplementedError


class XMLRawParser(Parser):
    """return string of xml"""
    payload_format = 'xml'

    def parse(self, method, payload):
        return payload

    def parse_error(self, method, payload):
        return payload

class XMLDomParser(XMLRawParser):
    """return xml.dom.minidom object"""
    def parse(self, method, payload):
        return dom.parseString(payload)


class XMLETreeParser(XMLRawParser):
    """return elementtree object"""
    def parse(self, method, payload):
        return ET.fromstring(payload)


class JSONParser(Parser):

    payload_format = 'json'

    def __init__(self):
        self.json_lib = json

    def parse(self, method, payload):
        try:
            json = self.json_lib.loads(payload, encoding='utf-8')
        except Exception as e:
            print ("Failed to parse JSON payload:" + repr(payload))
            raise QWeiboError('Failed to parse JSON payload: %s' % e)

        return json

    def parse_error(self, method, payload):
        return self.json_lib.loads(payload, encoding='utf-8')


class ModelParser(JSONParser):

    def __init__(self, model_factory=None):
        JSONParser.__init__(self)
        self.model_factory = model_factory or ModelFactory

    def parse(self, method, payload):
        try:
            if method.payload_type is None:
                return
            model = getattr(self.model_factory, method.payload_type)
        except AttributeError:
            raise QWeiboError('No model for this payload type: %s' % method.payload_type)

        json = JSONParser.parse(self, method, payload)
        data = json['data']

        # TODO: add pager
        if 'pagetime' in method.allowed_param:
            pass

        if method.payload_list:
            # sometimes data will be a None
            if data:
                if 'hasnext' in data:
                    # need pager here
                    hasnext = data['hasnext'] in [0, 2]
                    # hasNext:2表示不能往上翻 1 表示不能往下翻，
                    # 0表示两边都可以翻 3表示两边都不能翻了
                else:
                    hasnext = False
                if 'info' in data:
                    data = data['info']
            else:
                hasnext = False
            result = model.parse_list(method.api, data)
            result.hasnext = hasnext
        else:
            result = model.parse(method.api, data)
        return result


########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2010 Joshua Roesslein
# Copyright 2011 andelf <andelf@gmail.com>
# See LICENSE for details.
# Time-stamp: <2011-06-08 19:22:59 andelf>

from datetime import datetime
import time
import re
import sys

from compat import htmlentitydefs


def parse_datetime(str):
    # We must parse datetime this way to work in python 2.4
    return datetime(*(time.strptime(str, '%a %b %d %H:%M:%S +0800 %Y')[0:6]))


def parse_html_value(html):
    return html[html.find('>') + 1:html.rfind('<')]


def parse_a_href(atag):
    start = atag.find('"') + 1
    end = atag.find('"', start)
    return atag[start:end]


def parse_search_datetime(str):
    # python 2.4
    return datetime(*(time.strptime(str, '%a, %d %b %Y %H:%M:%S +0000')[0:6]))


def unescape_html(text):
    """Created by Fredrik Lundh
    (http://effbot.org/zone/re-sub.htm#unescape-html)"""
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text  # leave as is
    return re.sub("&#?\w+;", fixup, text)


def convert_to_utf8_unicode(arg):
    """TODO: currently useless"""
    pass


def convert_to_utf8_str(arg):
    # written by andelf ^_^
    # return py2str py3str
    # fix py26
    MAJOR_VERSION = sys.version_info[0]
    if MAJOR_VERSION == 3:
        unicodeType = str
        if type(arg) == unicodeType:
            return arg
        elif type(arg) == bytes:
            return arg.decode('utf-8')
    else:
        unicodeType = __builtins__['unicode']
        if type(arg) == unicodeType:
            return arg.encode('utf-8')
        elif type(arg) == str:
            return arg
    # assume list
    if hasattr(arg, '__iter__'):
        arg = ','.join(map(convert_to_utf8_str, arg))
    return str(arg)


def convert_to_utf8_bytes(arg):
    # return py2str py3bytes
    if type(arg) == bytes:
        return arg
    ret = convert_to_utf8_str(arg)
    return ret.encode('utf-8')


def timestamp_to_str(tm):
    return time.ctime(tm)

########NEW FILE########
__FILENAME__ = api
#coding=utf-8

# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

import os
import mimetypes

from binder import bind_api
from error import WeibopError
from parsers import ModelParser


class API(object):
    """Mblog API"""

    def __init__(self, auth_handler=None,
            host='api.t.sina.com.cn', search_host='api.t.sina.com.cn',
             cache=None, secure=False, api_root='', search_root='',
            retry_count=0, retry_delay=0, retry_errors=None,source=None,
            parser=None, log = None):
        self.auth = auth_handler
        self.host = host
        if source == None:
            if auth_handler != None:
                self.source = self.auth._consumer.key
        else:
            self.source = source
        self.search_host = search_host
        self.api_root = api_root
        self.search_root = search_root
        self.cache = cache
        self.secure = secure
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.retry_errors = retry_errors
        self.parser = parser or ModelParser()
        self.log = log

    """ statuses/public_timeline """
    public_timeline = bind_api(
        path = '/statuses/public_timeline.json',
        payload_type = 'status', payload_list = True,
        allowed_param = []
    )

    """ statuses/home_timeline """
    home_timeline = bind_api(
        path = '/statuses/home_timeline.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """ statuses/friends_timeline """
    friends_timeline = bind_api(
        path = '/statuses/friends_timeline.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )
    """ statuses/comment """
    comment = bind_api(
        path = '/statuses/comment.json',
        method = 'POST',
        payload_type = 'comments',
        allowed_param = ['id', 'cid', 'comment'],
        require_auth = True
    )
    
    """ statuses/comment_destroy """
    comment_destroy  = bind_api(
        path = '/statuses/comment_destroy/{id}.json',
        method = 'DELETE',
        payload_type = 'comments',
        allowed_param = ['id'],
        require_auth = True
    )
    
    """ statuses/comments_timeline """
    comments = bind_api(
        path = '/statuses/comments.json',
        payload_type = 'comments', payload_list = True,
        allowed_param = ['id', 'count', 'page'],
        require_auth = True
    )
    
    """ statuses/comments_timeline """
    comments_timeline = bind_api(
        path = '/statuses/comments_timeline.json',
        payload_type = 'comments', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )
    
    """ statuses/comments_by_me """
    comments_by_me = bind_api(
        path = '/statuses/comments_by_me.json',
        payload_type = 'comments', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )
    
    """ statuses/user_timeline """
    user_timeline = bind_api(
        path = '/statuses/user_timeline.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['id', 'user_id', 'screen_name', 'since_id',
                          'max_id', 'count', 'page']
    )

    """ statuses/mentions """
    mentions = bind_api(
        path = '/statuses/mentions.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """ statuses/counts """
    counts = bind_api(
        path = '/statuses/counts.json',
        payload_type = 'counts', payload_list = True,
        allowed_param = ['ids'],
        require_auth = True
    )
    
    """ statuses/unread """
    unread = bind_api(
        path = '/statuses/unread.json',
        payload_type = 'counts'
    )
    
    """ statuses/retweeted_by_me """
    retweeted_by_me = bind_api(
        path = '/statuses/retweeted_by_me.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """ statuses/retweeted_to_me """
    retweeted_to_me = bind_api(
        path = '/statuses/retweeted_to_me.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """ statuses/retweets_of_me """
    retweets_of_me = bind_api(
        path = '/statuses/retweets_of_me.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """ statuses/show """
    get_status = bind_api(
        path = '/statuses/show.json',
        payload_type = 'status',
        allowed_param = ['id']
    )

    """ statuses/update """
    update_status = bind_api(
        path = '/statuses/update.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['status', 'lat', 'long', 'source'],
        require_auth = True
    )
    """ statuses/upload """
    def upload(self, filename, status, lat=None, long=None, source=None):
        if source is None:
            source=self.source
        headers, post_data = API._pack_image(filename, 1024, source=source, status=status, lat=lat, long=long, contentname="pic")
        args = [status]
        allowed_param = ['status']
        
        if lat is not None:
            args.append(lat)
            allowed_param.append('lat')
        
        if long is not None:
            args.append(long)
            allowed_param.append('long')
        
        if source is not None:
            args.append(source)
            allowed_param.append('source')

        return bind_api(
                    path = '/statuses/upload.json',
                    method = 'POST',
                    payload_type = 'status',
                    require_auth = True,
                    allowed_param = allowed_param
                )(self, *args, post_data=post_data, headers=headers)
        
    """ statuses/reply """
    reply = bind_api(
        path = '/statuses/reply.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['id', 'cid','comment'],
        require_auth = True
    )
    
    """ statuses/repost """
    repost = bind_api(
        path = '/statuses/repost.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['id', 'status'],
        require_auth = True
    )
    
    """ statuses/destroy """
    destroy_status = bind_api(
        path = '/statuses/destroy/{id}.json',
        method = 'DELETE',
        payload_type = 'status',
        allowed_param = ['id'],
        require_auth = True
    )

    """ statuses/retweet """
    retweet = bind_api(
        path = '/statuses/retweet/{id}.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['id'],
        require_auth = True
    )

    """ statuses/retweets """
    retweets = bind_api(
        path = '/statuses/retweets/{id}.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['id', 'count'],
        require_auth = True
    )

    """ users/show """
    get_user = bind_api(
        path = '/users/show.json',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name']
    )
    
    """ Get the authenticated user """
    def get_user_info(self):
        return self.get_user(screen_name=self.auth.get_username())

    """ users/search """
    search_users = bind_api(
        path = '/users/search.json',
        payload_type = 'user', payload_list = True,
        require_auth = True,
        allowed_param = ['q', 'per_page', 'page']
    )

    """ statuses/friends """
    friends = bind_api(
        path = '/statuses/friends.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['id', 'user_id', 'screen_name', 'page', 'cursor']
    )

    """ statuses/followers """
    followers = bind_api(
        path = '/statuses/followers.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['id', 'user_id', 'screen_name', 'page', 'cursor']
    )

    """ direct_messages """
    direct_messages = bind_api(
        path = '/direct_messages.json',
        payload_type = 'direct_message', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """ direct_messages/sent """
    sent_direct_messages = bind_api(
        path = '/direct_messages/sent.json',
        payload_type = 'direct_message', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )
    """ direct_messages/new """
    new_direct_message = bind_api(
        path = '/direct_messages/new.json',
        method = 'POST',
        payload_type = 'direct_message',
        allowed_param = ['id', 'screen_name', 'user_id', 'text'],
        require_auth = True
    )
    
    """ direct_messages/destroy """
    destroy_direct_message = bind_api(
        path = '/direct_messages/destroy/{id}.json',
        method = 'POST',
        payload_type = 'direct_message',
        allowed_param = ['id'],
        require_auth = True
    )

    """ friendships/create """
    create_friendship = bind_api(
        path = '/friendships/create.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name', 'follow'],
        require_auth = True
    )

    """ friendships/destroy """
    destroy_friendship = bind_api(
        path = '/friendships/destroy.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ friendships/exists """
    exists_friendship = bind_api(
        path = '/friendships/exists.json',
        payload_type = 'json',
        allowed_param = ['user_a', 'user_b']
    )

    """ friendships/show """
    show_friendship = bind_api(
        path = '/friendships/show.json',
        payload_type = 'friendship',
        allowed_param = ['source_id', 'source_screen_name',
                          'target_id', 'target_screen_name']
    )

    """ friends/ids """
    friends_ids = bind_api(
        path = '/friends/ids.json',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name', 'cursor', 'count'],
        require_auth = True
    )

    """ followers/ids """
    followers_ids = bind_api(        
        path = '/followers/ids.json',
        payload_type = 'json',
        allowed_param = ['id', 'page'],
    )

    """ account/verify_credentials """
    def verify_credentials(self):
        try:
            return bind_api(
                path = '/account/verify_credentials.json',
                payload_type = 'user',
                require_auth = True
            )(self)
        except WeibopError:
            return False

    """ account/rate_limit_status """
    rate_limit_status = bind_api(
        path = '/account/rate_limit_status.json',
        payload_type = 'json'
    )

    """ account/update_delivery_device """
    set_delivery_device = bind_api(
        path = '/account/update_delivery_device.json',
        method = 'POST',
        allowed_param = ['device'],
        payload_type = 'user',
        require_auth = True
    )
    """account/get_privacy"""
    get_privacy = bind_api(
        path = '/account/get_privacy.json',
        payload_type = 'json'                  
     )
    """account/update_privacy"""
    update_privacy = bind_api(
        path = '/account/update_privacy.json',
        payload_type = 'json',
        method = 'POST',
        allow_param = ['comment','message','realname','geo','badge'],
        require_auth = True                      
     )
    """ account/update_profile_colors """
    update_profile_colors = bind_api(
        path = '/account/update_profile_colors.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['profile_background_color', 'profile_text_color',
                          'profile_link_color', 'profile_sidebar_fill_color',
                          'profile_sidebar_border_color'],
        require_auth = True
    )
        
    """ account/update_profile_image """
    def update_profile_image(self, filename):
        headers, post_data = API._pack_image(filename=filename, max_size=700, source=self.source)
        return bind_api(
            path = '/account/update_profile_image.json',
            method = 'POST',
            payload_type = 'user',
            require_auth = True
        )(self, post_data=post_data, headers=headers)

    """ account/update_profile_background_image """
    def update_profile_background_image(self, filename, *args, **kargs):
        headers, post_data = API._pack_image(filename, 800)
        bind_api(
            path = '/account/update_profile_background_image.json',
            method = 'POST',
            payload_type = 'user',
            allowed_param = ['tile'],
            require_auth = True
        )(self, post_data=post_data, headers=headers)

    """ account/update_profile """
    update_profile = bind_api(
        path = '/account/update_profile.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['name', 'url', 'location', 'description'],
        require_auth = True
    )

    """ favorites """
    favorites = bind_api(
        path = '/favorites/{id}.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['id', 'page']
    )

    """ favorites/create """
    create_favorite = bind_api(
        path = '/favorites/create/{id}.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['id'],
        require_auth = True
    )

    """ favorites/destroy """
    destroy_favorite = bind_api(
        path = '/favorites/destroy/{id}.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['id'],
        require_auth = True
    )

    """ notifications/follow """
    enable_notifications = bind_api(
        path = '/notifications/follow.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ notifications/leave """
    disable_notifications = bind_api(
        path = '/notifications/leave.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ blocks/create """
    create_block = bind_api(
        path = '/blocks/create.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ blocks/destroy """
    destroy_block = bind_api(
        path = '/blocks/destroy.json',
        method = 'DELETE',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ blocks/exists """
    def exists_block(self, *args, **kargs):
        try:
            bind_api(
                path = '/blocks/exists.json',
                allowed_param = ['id', 'user_id', 'screen_name'],
                require_auth = True
            )(self, *args, **kargs)
        except WeibopError:
            return False
        return True

    """ blocks/blocking """
    blocks = bind_api(
        path = '/blocks/blocking.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['page'],
        require_auth = True
    )

    """ blocks/blocking/ids """
    blocks_ids = bind_api(
        path = '/blocks/blocking/ids.json',
        payload_type = 'json',
        require_auth = True
    )

    """ statuses/repost """
    report_spam = bind_api(
        path = '/report_spam.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ saved_searches """
    saved_searches = bind_api(
        path = '/saved_searches.json',
        payload_type = 'saved_search', payload_list = True,
        require_auth = True
    )

    """ saved_searches/show """
    get_saved_search = bind_api(
        path = '/saved_searches/show/{id}.json',
        payload_type = 'saved_search',
        allowed_param = ['id'],
        require_auth = True
    )

    """ saved_searches/create """
    create_saved_search = bind_api(
        path = '/saved_searches/create.json',
        method = 'POST',
        payload_type = 'saved_search',
        allowed_param = ['query'],
        require_auth = True
    )

    """ saved_searches/destroy """
    destroy_saved_search = bind_api(
        path = '/saved_searches/destroy/{id}.json',
        method = 'DELETE',
        payload_type = 'saved_search',
        allowed_param = ['id'],
        require_auth = True
    )

    """ help/test """
    def test(self):
        try:
            bind_api(
                path = '/help/test.json',
            )(self)
        except WeibopError:
            return False
        return True

    def create_list(self, *args, **kargs):
        return bind_api(
            path = '/%s/lists.json' % self.auth.get_username(),
            method = 'POST',
            payload_type = 'list',
            allowed_param = ['name', 'mode', 'description'],
            require_auth = True
        )(self, *args, **kargs)

    def destroy_list(self, slug):
        return bind_api(
            path = '/%s/lists/%s.json' % (self.auth.get_username(), slug),
            method = 'DELETE',
            payload_type = 'list',
            require_auth = True
        )(self)

    def update_list(self, slug, *args, **kargs):
        return bind_api(
            path = '/%s/lists/%s.json' % (self.auth.get_username(), slug),
            method = 'POST',
            payload_type = 'list',
            allowed_param = ['name', 'mode', 'description'],
            require_auth = True
        )(self, *args, **kargs)

    lists = bind_api(
        path = '/{user}/lists.json',
        payload_type = 'list', payload_list = True,
        allowed_param = ['user', 'cursor'],
        require_auth = True
    )

    lists_memberships = bind_api(
        path = '/{user}/lists/memberships.json',
        payload_type = 'list', payload_list = True,
        allowed_param = ['user', 'cursor'],
        require_auth = True
    )

    lists_subscriptions = bind_api(
        path = '/{user}/lists/subscriptions.json',
        payload_type = 'list', payload_list = True,
        allowed_param = ['user', 'cursor'],
        require_auth = True
    )

    list_timeline = bind_api(
        path = '/{owner}/lists/{slug}/statuses.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['owner', 'slug', 'since_id', 'max_id', 'count', 'page']
    )

    get_list = bind_api(
        path = '/{owner}/lists/{slug}.json',
        payload_type = 'list',
        allowed_param = ['owner', 'slug']
    )

    def add_list_member(self, slug, *args, **kargs):
        return bind_api(
            path = '/%s/%s/members.json' % (self.auth.get_username(), slug),
            method = 'POST',
            payload_type = 'list',
            allowed_param = ['id'],
            require_auth = True
        )(self, *args, **kargs)

    def remove_list_member(self, slug, *args, **kargs):
        return bind_api(
            path = '/%s/%s/members.json' % (self.auth.get_username(), slug),
            method = 'DELETE',
            payload_type = 'list',
            allowed_param = ['id'],
            require_auth = True
        )(self, *args, **kargs)

    list_members = bind_api(
        path = '/{owner}/{slug}/members.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['owner', 'slug', 'cursor']
    )

    def is_list_member(self, owner, slug, user_id):
        try:
            return bind_api(
                path = '/%s/%s/members/%s.json' % (owner, slug, user_id),
                payload_type = 'user'
            )(self)
        except WeibopError:
            return False

    subscribe_list = bind_api(
        path = '/{owner}/{slug}/subscribers.json',
        method = 'POST',
        payload_type = 'list',
        allowed_param = ['owner', 'slug'],
        require_auth = True
    )

    unsubscribe_list = bind_api(
        path = '/{owner}/{slug}/subscribers.json',
        method = 'DELETE',
        payload_type = 'list',
        allowed_param = ['owner', 'slug'],
        require_auth = True
    )

    list_subscribers = bind_api(
        path = '/{owner}/{slug}/subscribers.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['owner', 'slug', 'cursor']
    )

    def is_subscribed_list(self, owner, slug, user_id):
        try:
            return bind_api(
                path = '/%s/%s/subscribers/%s.json' % (owner, slug, user_id),
                payload_type = 'user'
            )(self)
        except WeibopError:
            return False

    """ trends/available """
    trends_available = bind_api(
        path = '/trends/available.json',
        payload_type = 'json',
        allowed_param = ['lat', 'long']
    )

    """ trends/location """
    trends_location = bind_api(
        path = '/trends/{woeid}.json',
        payload_type = 'json',
        allowed_param = ['woeid']
    )

    """ search """
    search = bind_api(
        search_api = True,
        path = '/search.json',
        payload_type = 'search_result', payload_list = True,
        allowed_param = ['q', 'lang', 'locale', 'rpp', 'page', 'since_id', 'geocode', 'show_user']
    )
    search.pagination_mode = 'page'

    """ trends """
    trends = bind_api(
        path = '/trends.json',
        payload_type = 'trends', payload_list = True,
        allowed_param = ['user_id','count','page'],
        require_auth= True
        )
    """trends/statuses"""
    trends_statuses = bind_api(
        path = '/trends/statuses.json', 
        payload_type = 'status', payload_list = True,
        allowed_param = ['trend_name'],
        require_auth = True
        
        )       
    """trends/follow"""
    trends_follow = bind_api(
        path = '/trends/follow.json',
        method = 'POST',
        allowed_param = ['trend_name'],
        require_auth = True
        )                     
    """trends/destroy"""
    trends_destroy = bind_api(
        path = '/trends/destroy.json',
        method = 'DELETE',
        allowed_param = ['trend_id'],
        require_auth = True
        )                                                                   
    """ trends/current """
    trends_current = bind_api(
        search_api = True,
        path = '/trends/current.json',
        payload_type = 'json',
        allowed_param = ['exclude']
    )
    """ trends/hourly"""
    trends_hourly = bind_api(
        search_api = True,
        path = '/trends/hourly.json',
        payload_type = 'trends',
        allowed_param = []
    )                      
    """ trends/daily """
    trends_daily = bind_api(
        search_api = True,
        path = '/trends/daily.json',
        payload_type = 'trends',
        allowed_param = []
    )

    """ trends/weekly """
    trends_weekly = bind_api(
        search_api = True,
        path = '/trends/weekly.json',
        payload_type = 'json',
        allowed_param = []
    )
    """ Tags """
    tags = bind_api(
        path = '/tags.json',
        payload_type = 'tags', payload_list = True,
        allowed_param = ['user_id'],
        require_auth= True,
        )          
    tag_create = bind_api(
        path = '/tags/create.json',
        payload_type = 'tags',
        method = 'POST',
        allowed_param = ['tags'],
        payload_list = True, 
        require_auth = True,
        )                                
    tag_suggestions = bind_api(
        path = '/tags/suggestions.json',
        payload_type = 'tags',
        require_auth = True,
        payload_list = True,
        )
    tag_destroy = bind_api(
        path = '/tags/destroy.json',
        payload_type = 'json',
        method='POST',   
        require_auth = True,
        allowed_param = ['tag_id'],
        ) 
    tag_destroy_batch = bind_api(
        path = '/tags/destroy_batch.json',
        payload_type = 'json',
        method='DELETE',   
        require_auth = True,
        payload_list = True,
        allowed_param = ['ids'],
        )                                                                              
    """ Internal use only """
    @staticmethod
    def _pack_image(filename, max_size, source=None, status=None, lat=None, long=None, contentname="image"):
        """Pack image from file into multipart-formdata post body"""
        # image must be less than 700kb in size
        try:
            if os.path.getsize(filename) > (max_size * 1024):
                raise WeibopError('File is too big, must be less than 700kb.')
        #except os.error, e:
        except os.error:
            raise WeibopError('Unable to access file')

        # image must be gif, jpeg, or png
        file_type = mimetypes.guess_type(filename)
        if file_type is None:
            raise WeibopError('Could not determine file type')
        file_type = file_type[0]
        if file_type not in ['image/gif', 'image/jpeg', 'image/png']:
            raise WeibopError('Invalid file type for image: %s' % file_type)
        
        # build the mulitpart-formdata body
        fp = open(filename, 'rb')
        BOUNDARY = 'Tw3ePy'
        body = ''
        if status is not None:            
            body = body + '--' + BOUNDARY + '\r\n'
            body = body + 'Content-Disposition: form-data; name="status"' + '\r\n'
            body = body + 'Content-Type: text/plain; charset=US-ASCII' + '\r\n'
            body = body + 'Content-Transfer-Encoding: 8bit' + '\r\n'
            body = body + '' + '\r\n'
            body = body + status + '\r\n'
        if source is not None:            
            body = body + '--' + BOUNDARY + '\r\n'
            body = body + 'Content-Disposition: form-data; name="source"' + '\r\n'
            body = body + 'Content-Type: text/plain; charset=US-ASCII' + '\r\n'
            body = body + 'Content-Transfer-Encoding: 8bit' + '\r\n'
            body = body + '' + '\r\n'
            body = body + source + '\r\n'
        if lat is not None:            
            body = body + '--' + BOUNDARY + '\r\n'
            body = body + 'Content-Disposition: form-data; name="lat"' + '\r\n'
            body = body + 'Content-Type: text/plain; charset=US-ASCII' + '\r\n'
            body = body + 'Content-Transfer-Encoding: 8bit' + '\r\n'
            body = body + '' + '\r\n'
            body = body + lat + '\r\n'
        if long is not None:            
            body = body + '--' + BOUNDARY + '\r\n'
            body = body + 'Content-Disposition: form-data; name="long"' + '\r\n'
            body = body + 'Content-Type: text/plain; charset=US-ASCII' + '\r\n'
            body = body + 'Content-Transfer-Encoding: 8bit' + '\r\n'
            body = body + '' + '\r\n'
            body = body + long + '\r\n'

        body = body + '--' + BOUNDARY + '\r\n'
        body = body + unicode('Content-Disposition: form-data; name="' + contentname + '"; filename="' + filename + '"\r\n').encode('utf-8')
        body = body + 'Content-Type: ' + file_type + '\r\n'
        body = body + 'Content-Transfer-Encoding: binary' + '\r\n'
        body = body + '' + '\r\n'
        body = body + fp.read() + '\r\n'
        body = body + '--' + BOUNDARY + '--' + '\r\n'
        body = body + '' + '\r\n'
        fp.close()
        body = body + '--' + BOUNDARY + '--' + '\r\n'
        body = body + ''
        # build headers
        headers = {
            'Content-Type': 'multipart/form-data; boundary=Tw3ePy',
            'Content-Length': len(body)
        }
        
        return headers, body


########NEW FILE########
__FILENAME__ = auth
#coding=utf-8
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

from urllib2 import Request, urlopen
import base64

import oauth
from error import WeibopError
from api import API


class AuthHandler(object):

    def apply_auth(self, url, method, headers, parameters):
        """Apply authentication headers to request"""
        raise NotImplementedError

    def get_username(self):
        """Return the username of the authenticated user"""
        raise NotImplementedError


class BasicAuthHandler(AuthHandler):

    def __init__(self, username, password):
        self.username = username
        self._b64up = base64.b64encode('%s:%s' % (username, password))

    def apply_auth(self, url, method, headers, parameters):
        headers['Authorization'] = 'Basic %s' % self._b64up
        
    def get_username(self):
        return self.username


class OAuthHandler(AuthHandler):
    """OAuth authentication handler"""

    OAUTH_HOST = 'api.t.sina.com.cn'
    OAUTH_ROOT = '/oauth/'

    def __init__(self, consumer_key, consumer_secret, callback=None, secure=False):
        self._consumer = oauth.OAuthConsumer(consumer_key, consumer_secret)
        self._sigmethod = oauth.OAuthSignatureMethod_HMAC_SHA1()
        self.request_token = None
        self.access_token = None
        self.callback = callback
        self.username = None
        self.secure = secure

    def _get_oauth_url(self, endpoint):
        if self.secure:
            prefix = 'https://'
        else:
            prefix = 'http://'

        return prefix + self.OAUTH_HOST + self.OAUTH_ROOT + endpoint

    def apply_auth(self, url, method, headers, parameters):
        request = oauth.OAuthRequest.from_consumer_and_token(
            self._consumer, http_url=url, http_method=method,
            token=self.access_token, parameters=parameters
        )
        request.sign_request(self._sigmethod, self._consumer, self.access_token)
        headers.update(request.to_header())

    def _get_request_token(self):
        try:
            url = self._get_oauth_url('request_token')
            request = oauth.OAuthRequest.from_consumer_and_token(
                self._consumer, http_url=url, callback=self.callback
            )
            request.sign_request(self._sigmethod, self._consumer, None)
            resp = urlopen(Request(url, headers=request.to_header()))
            return oauth.OAuthToken.from_string(resp.read())
        except Exception, e:
            raise WeibopError(e)

    def set_request_token(self, key, secret):
        self.request_token = oauth.OAuthToken(key, secret)

    ###
    def set_req_token(self, token):
        self.request_token = token

    ###
    def get_auth_url(self, signin_with_weibo=False):
        return self.get_authorization_url(), self.request_token
    
    def set_access_token(self, key, secret):
        self.access_token = oauth.OAuthToken(key, secret)

    def get_authorization_url(self, signin_with_twitter=False):
        """Get the authorization URL to redirect the user"""
        try:
            # get the request token
            self.request_token = self._get_request_token()

            # build auth request and return as url
            if signin_with_twitter:
                url = self._get_oauth_url('authenticate')
            else:
                url = self._get_oauth_url('authorize')
            request = oauth.OAuthRequest.from_token_and_callback(
                token=self.request_token, http_url=url, callback=self.callback
            )

            return request.to_url()
        except Exception, e:
            raise WeibopError(e)

    def get_access_token(self, verifier=None):
        """
        After user has authorized the request token, get access token
        with user supplied verifier.
        """
        try:
            url = self._get_oauth_url('access_token')

            # build request
            request = oauth.OAuthRequest.from_consumer_and_token(
                self._consumer,
                token=self.request_token, http_url=url,
                verifier=str(verifier)
            )
            request.sign_request(self._sigmethod, self._consumer, self.request_token)

            # send request                        
            resp = urlopen(Request(url, headers=request.to_header()))
            self.access_token = oauth.OAuthToken.from_string(resp.read())

            return self.access_token
        except Exception, e:
            raise WeibopError(e)
        
    def setToken(self, token, tokenSecret):
        self.access_token = oauth.OAuthToken(token, tokenSecret)
        
    def get_username(self):
        if self.username is None:
            api = API(self)
            user = api.verify_credentials()
            if user:
                self.username = user.screen_name
            else:
                raise WeibopError("Unable to get username, invalid oauth token!")
        return self.username

########NEW FILE########
__FILENAME__ = binder
#coding=utf-8
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

import httplib
import urllib
import time
import re
from error import WeibopError
from utils import convert_to_utf8_str

re_path_template = re.compile('{\w+}')


def bind_api(**config):

    class APIMethod(object):
        
        path = config['path']
        payload_type = config.get('payload_type', None)
        payload_list = config.get('payload_list', False)
        allowed_param = config.get('allowed_param', [])
        method = config.get('method', 'GET')
        require_auth = config.get('require_auth', False)
        search_api = config.get('search_api', False)
                
        def __init__(self, api, args, kargs):
            # If authentication is required and no credentials
            # are provided, throw an error.
            if self.require_auth and not api.auth:
                raise WeibopError('Authentication required!')

            self.api = api
            self.post_data = kargs.pop('post_data', None)
            self.retry_count = kargs.pop('retry_count', api.retry_count)
            self.retry_delay = kargs.pop('retry_delay', api.retry_delay)
            self.retry_errors = kargs.pop('retry_errors', api.retry_errors)
            self.headers = kargs.pop('headers', {})
            self.build_parameters(args, kargs)
            # Pick correct URL root to use
            if self.search_api:
                self.api_root = api.search_root
            else:
                self.api_root = api.api_root
            
            # Perform any path variable substitution
            self.build_path()

            if api.secure:
                self.scheme = 'https://'
            else:
                self.scheme = 'http://'

            if self.search_api:
                self.host = api.search_host
            else:
                self.host = api.host

            # Manually set Host header to fix an issue in python 2.5
            # or older where Host is set including the 443 port.
            # This causes Twitter to issue 301 redirect.
            # See Issue http://github.com/joshthecoder/tweepy/issues/#issue/12
            self.headers['Host'] = self.host

        def build_parameters(self, args, kargs):
            self.parameters = {}
            for idx, arg in enumerate(args):
                try:
                    self.parameters[self.allowed_param[idx]] = convert_to_utf8_str(arg)
                except IndexError:
                    raise WeibopError('Too many parameters supplied!')

            for k, arg in kargs.items():
                if arg is None:
                    continue
                if k in self.parameters:
                    raise WeibopError('Multiple values for parameter %s supplied!' % k)

                self.parameters[k] = convert_to_utf8_str(arg)

        def build_path(self):
            for variable in re_path_template.findall(self.path):
                name = variable.strip('{}')

                if name == 'user' and self.api.auth:
                    value = self.api.auth.get_username()
                else:
                    try:
                        value = urllib.quote(self.parameters[name])
                    except KeyError:
                        raise WeibopError('No parameter value found for path variable: %s' % name)
                    del self.parameters[name]

                self.path = self.path.replace(variable, value)

        def execute(self):
            # Build the request URL
            url = self.api_root + self.path
            if self.api.source is not None:
                self.parameters.setdefault('source',self.api.source)
            
            if len(self.parameters):
                if self.method == 'GET' or self.method == 'DELETE':
                    url = '%s?%s' % (url, urllib.urlencode(self.parameters))  
                else:
                    self.headers.setdefault("User-Agent","python")
                    if self.post_data is None:
                        self.headers.setdefault("Accept","text/html")                        
                        self.headers.setdefault("Content-Type","application/x-www-form-urlencoded")
                        self.post_data = urllib.urlencode(self.parameters)           
            # Query the cache if one is available
            # and this request uses a GET method.
            if self.api.cache and self.method == 'GET':
                cache_result = self.api.cache.get(url)
                # if cache result found and not expired, return it
                if cache_result:
                    # must restore api reference
                    if isinstance(cache_result, list):
                        for result in cache_result:
                            result._api = self.api
                    else:
                        cache_result._api = self.api
                    return cache_result
                #urllib.urlencode(self.parameters)
            # Continue attempting request until successful
            # or maximum number of retries is reached.
            sTime = time.time()
            retries_performed = 0
            while retries_performed < self.retry_count + 1:
                # Open connection
                # FIXME: add timeout
                if self.api.secure:
                    conn = httplib.HTTPSConnection(self.host)
                else:
                    conn = httplib.HTTPConnection(self.host)
                # Apply authentication
                if self.api.auth:
                    self.api.auth.apply_auth(
                            self.scheme + self.host + url,
                            self.method, self.headers, self.parameters
                    )
                # Execute request
                try:
                    conn.request(self.method, url, headers=self.headers, body=self.post_data)
                    resp = conn.getresponse()
                except Exception, e:
                    raise WeibopError('Failed to send request: %s' % e + "url=" + str(url) +",self.headers="+ str(self.headers))

                # Exit request loop if non-retry error code
                if self.retry_errors:
                    if resp.status not in self.retry_errors: break
                else:
                    if resp.status == 200: break

                # Sleep before retrying request again
                time.sleep(self.retry_delay)
                retries_performed += 1

            # If an error was returned, throw an exception
            body = resp.read()
            self.api.last_response = resp
            if self.api.log is not None:
                requestUrl = "URL:http://"+ self.host + url
                eTime = '%.0f' % ((time.time() - sTime) * 1000)
                postData = ""
                if self.post_data is not None:
                    postData = ",post:"+ self.post_data[0:500]
                self.api.log.debug(requestUrl +",time:"+ str(eTime)+ postData+",result:"+ body )
            if resp.status != 200:
                try:
                    json = self.api.parser.parse_error(self, body)
                    error_code =  json['error_code']
                    error =  json['error']
                    error_msg = 'error_code:' + error_code +','+ error
                except Exception:
                    error_msg = "Weibo error response: status code = %s" % resp.status
                raise WeibopError(error_msg)
            
            # Parse the response payload
            result = self.api.parser.parse(self, body)
            conn.close()

            # Store result into cache if one is available.
            if self.api.cache and self.method == 'GET' and result:
                self.api.cache.store(url, result)
            return result

    def _call(api, *args, **kargs):

        method = APIMethod(api, args, kargs)
        return method.execute()


    # Set pagination mode
    if 'cursor' in APIMethod.allowed_param:
        _call.pagination_mode = 'cursor'
    elif 'page' in APIMethod.allowed_param:
        _call.pagination_mode = 'page'

    return _call


########NEW FILE########
__FILENAME__ = cache
#coding=utf-8
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

import time
import threading
import os
import cPickle as pickle

try:
    import hashlib
except ImportError:
    # python 2.4
    import md5 as hashlib

try:
    import fcntl
except ImportError:
    # Probably on a windows system
    # TODO: use win32file
    pass


class Cache(object):
    """Cache interface"""

    def __init__(self, timeout=60):
        """Initialize the cache
            timeout: number of seconds to keep a cached entry
        """
        self.timeout = timeout

    def store(self, key, value):
        """Add new record to cache
            key: entry key
            value: data of entry
        """
        raise NotImplementedError

    def get(self, key, timeout=None):
        """Get cached entry if exists and not expired
            key: which entry to get
            timeout: override timeout with this value [optional]
        """
        raise NotImplementedError

    def count(self):
        """Get count of entries currently stored in cache"""
        raise NotImplementedError

    def cleanup(self):
        """Delete any expired entries in cache."""
        raise NotImplementedError

    def flush(self):
        """Delete all cached entries"""
        raise NotImplementedError


class MemoryCache(Cache):
    """In-memory cache"""

    def __init__(self, timeout=60):
        Cache.__init__(self, timeout)
        self._entries = {}
        self.lock = threading.Lock()

    def __getstate__(self):
        # pickle
        return {'entries': self._entries, 'timeout': self.timeout}

    def __setstate__(self, state):
        # unpickle
        self.lock = threading.Lock()
        self._entries = state['entries']
        self.timeout = state['timeout']

    def _is_expired(self, entry, timeout):
        return timeout > 0 and (time.time() - entry[0]) >= timeout

    def store(self, key, value):
        self.lock.acquire()
        self._entries[key] = (time.time(), value)
        self.lock.release()

    def get(self, key, timeout=None):
        self.lock.acquire()
        try:
            # check to see if we have this key
            entry = self._entries.get(key)
            if not entry:
                # no hit, return nothing
                return None

            # use provided timeout in arguments if provided
            # otherwise use the one provided during init.
            if timeout is None:
                timeout = self.timeout

            # make sure entry is not expired
            if self._is_expired(entry, timeout):
                # entry expired, delete and return nothing
                del self._entries[key]
                return None

            # entry found and not expired, return it
            return entry[1]
        finally:
            self.lock.release()

    def count(self):
        return len(self._entries)

    def cleanup(self):
        self.lock.acquire()
        try:
            for k, v in self._entries.items():
                if self._is_expired(v, self.timeout):
                    del self._entries[k]
        finally:
            self.lock.release()

    def flush(self):
        self.lock.acquire()
        self._entries.clear()
        self.lock.release()


class FileCache(Cache):
    """File-based cache"""

    # locks used to make cache thread-safe
    cache_locks = {}

    def __init__(self, cache_dir, timeout=60):
        Cache.__init__(self, timeout)
        if os.path.exists(cache_dir) is False:
            os.mkdir(cache_dir)
        self.cache_dir = cache_dir
        if cache_dir in FileCache.cache_locks:
            self.lock = FileCache.cache_locks[cache_dir]
        else:
            self.lock = threading.Lock()
            FileCache.cache_locks[cache_dir] = self.lock

        if os.name == 'posix':
            self._lock_file = self._lock_file_posix
            self._unlock_file = self._unlock_file_posix
        elif os.name == 'nt':
            self._lock_file = self._lock_file_win32
            self._unlock_file = self._unlock_file_win32
        else:
            print 'Warning! FileCache locking not supported on this system!'
            self._lock_file = self._lock_file_dummy
            self._unlock_file = self._unlock_file_dummy

    def _get_path(self, key):
        md5 = hashlib.md5()
        md5.update(key)
        return os.path.join(self.cache_dir, md5.hexdigest())

    def _lock_file_dummy(self, path, exclusive=True):
        return None

    def _unlock_file_dummy(self, lock):
        return

    def _lock_file_posix(self, path, exclusive=True):
        lock_path = path + '.lock'
        if exclusive is True:
            f_lock = open(lock_path, 'w')
            fcntl.lockf(f_lock, fcntl.LOCK_EX)
        else:
            f_lock = open(lock_path, 'r')
            fcntl.lockf(f_lock, fcntl.LOCK_SH)
        if os.path.exists(lock_path) is False:
            f_lock.close()
            return None
        return f_lock

    def _unlock_file_posix(self, lock):
        lock.close()

    def _lock_file_win32(self, path, exclusive=True):
        # TODO: implement
        return None

    def _unlock_file_win32(self, lock):
        # TODO: implement
        return

    def _delete_file(self, path):
        os.remove(path)
        if os.path.exists(path + '.lock'):
            os.remove(path + '.lock')

    def store(self, key, value):
        path = self._get_path(key)
        self.lock.acquire()
        try:
            # acquire lock and open file
            f_lock = self._lock_file(path)
            datafile = open(path, 'wb')

            # write data
            pickle.dump((time.time(), value), datafile)

            # close and unlock file
            datafile.close()
            self._unlock_file(f_lock)
        finally:
            self.lock.release()

    def get(self, key, timeout=None):
        return self._get(self._get_path(key), timeout)

    def _get(self, path, timeout):
        if os.path.exists(path) is False:
            # no record
            return None
        self.lock.acquire()
        try:
            # acquire lock and open
            f_lock = self._lock_file(path, False)
            datafile = open(path, 'rb')

            # read pickled object
            created_time, value = pickle.load(datafile)
            datafile.close()

            # check if value is expired
            if timeout is None:
                timeout = self.timeout
            if timeout > 0 and (time.time() - created_time) >= timeout:
                # expired! delete from cache
                value = None
                self._delete_file(path)

            # unlock and return result
            self._unlock_file(f_lock)
            return value
        finally:
            self.lock.release()

    def count(self):
        c = 0
        for entry in os.listdir(self.cache_dir):
            if entry.endswith('.lock'):
                continue
            c += 1
        return c

    def cleanup(self):
        for entry in os.listdir(self.cache_dir):
            if entry.endswith('.lock'):
                continue
            self._get(os.path.join(self.cache_dir, entry), None)

    def flush(self):
        for entry in os.listdir(self.cache_dir):
            if entry.endswith('.lock'):
                continue
            self._delete_file(os.path.join(self.cache_dir, entry))


########NEW FILE########
__FILENAME__ = cursor
#coding=utf-8
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

from error import WeibopError

class Cursor(object):
    """Pagination helper class"""

    def __init__(self, method, *args, **kargs):
        if hasattr(method, 'pagination_mode'):
            if method.pagination_mode == 'cursor':
                self.iterator = CursorIterator(method, args, kargs)
            else:
                self.iterator = PageIterator(method, args, kargs)
        else:
            raise WeibopError('This method does not perform pagination')

    def pages(self, limit=0):
        """Return iterator for pages"""
        if limit > 0:
            self.iterator.limit = limit
        return self.iterator

    def items(self, limit=0):
        """Return iterator for items in each page"""
        i = ItemIterator(self.iterator)
        i.limit = limit
        return i

class BaseIterator(object):

    def __init__(self, method, args, kargs):
        self.method = method
        self.args = args
        self.kargs = kargs
        self.limit = 0

    def next(self):
        raise NotImplementedError

    def prev(self):
        raise NotImplementedError

    def __iter__(self):
        return self

class CursorIterator(BaseIterator):

    def __init__(self, method, args, kargs):
        BaseIterator.__init__(self, method, args, kargs)
        self.next_cursor = -1
        self.prev_cursor = 0
        self.count = 0

    def next(self):
        if self.next_cursor == 0 or (self.limit and self.count == self.limit):
            raise StopIteration
        data, cursors = self.method(
                cursor=self.next_cursor, *self.args, **self.kargs
        )
        self.prev_cursor, self.next_cursor = cursors
        if len(data) == 0:
            raise StopIteration
        self.count += 1
        return data

    def prev(self):
        if self.prev_cursor == 0:
            raise WeibopError('Can not page back more, at first page')
        data, self.next_cursor, self.prev_cursor = self.method(
                cursor=self.prev_cursor, *self.args, **self.kargs
        )
        self.count -= 1
        return data

class PageIterator(BaseIterator):

    def __init__(self, method, args, kargs):
        BaseIterator.__init__(self, method, args, kargs)
        self.current_page = 0

    def next(self):
        self.current_page += 1
        items = self.method(page=self.current_page, *self.args, **self.kargs)
        if len(items) == 0 or (self.limit > 0 and self.current_page > self.limit):
            raise StopIteration
        return items

    def prev(self):
        if (self.current_page == 1):
            raise WeibopError('Can not page back more, at first page')
        self.current_page -= 1
        return self.method(page=self.current_page, *self.args, **self.kargs)

class ItemIterator(BaseIterator):

    def __init__(self, page_iterator):
        self.page_iterator = page_iterator
        self.limit = 0
        self.current_page = None
        self.page_index = -1
        self.count = 0

    def next(self):
        if self.limit > 0 and self.count == self.limit:
            raise StopIteration
        if self.current_page is None or self.page_index == len(self.current_page) - 1:
            # Reached end of current page, get the next page...
            self.current_page = self.page_iterator.next()
            self.page_index = -1
        self.page_index += 1
        self.count += 1
        return self.current_page[self.page_index]

    def prev(self):
        if self.current_page is None:
            raise WeibopError('Can not go back more, at first page')
        if self.page_index == 0:
            # At the beginning of the current page, move to next...
            self.current_page = self.page_iterator.prev()
            self.page_index = len(self.current_page)
            if self.page_index == 0:
                raise WeibopError('No more items')
        self.page_index -= 1
        self.count -= 1
        return self.current_page[self.page_index]


########NEW FILE########
__FILENAME__ = error
#coding=utf-8
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

class WeibopError(Exception):
    """Weibopy exception"""

    def __init__(self, reason):
        self.reason = reason.encode('utf-8')

    def __str__(self):
        return self.reason


########NEW FILE########
__FILENAME__ = models
#coding=utf-8
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

from utils import parse_datetime, parse_html_value, parse_a_href, \
        parse_search_datetime, unescape_html

class ResultSet(list):
    """A list like object that holds results from a Twitter API query."""


class Model(object):

    def __init__(self, api=None):
        self._api = api

    def __getstate__(self):
        # pickle
        pickle = dict(self.__dict__)
        del pickle['_api']  # do not pickle the API reference
        return pickle

    @classmethod
    def parse(cls, api, json):
        """Parse a JSON object into a model instance."""
        raise NotImplementedError

    @classmethod
    def parse_list(cls, api, json_list):
        """Parse a list of JSON objects into a result set of model instances."""
        results = ResultSet()
        for obj in json_list:
            results.append(cls.parse(api, obj))
        return results


class Status(Model):

    @classmethod
    def parse(cls, api, json):
        status = cls(api)
        for k, v in json.items():
            if k == 'user':
                user = User.parse(api, v)
                setattr(status, 'author', user)
                setattr(status, 'user', user)  # DEPRECIATED
            elif k == 'screen_name':
                setattr(status, k, v)
            elif k == 'created_at':
                setattr(status, k, parse_datetime(v))
            elif k == 'source':
                if '<' in v:
                    setattr(status, k, parse_html_value(v))
                    setattr(status, 'source_url', parse_a_href(v))
                else:
                    setattr(status, k, v)
            elif k == 'retweeted_status':
                setattr(status, k, Status.parse(api, v))
            elif k == 'geo':
                setattr(status, k, Geo.parse(api, v))
            else:
                setattr(status, k, v)
        return status

    def destroy(self):
        return self._api.destroy_status(self.id)

    def retweet(self):
        return self._api.retweet(self.id)

    def retweets(self):
        return self._api.retweets(self.id)

    def favorite(self):
        return self._api.create_favorite(self.id)
class Geo(Model):

    @classmethod
    def parse(cls, api, json):
        geo = cls(api)
        if json is not None:
            for k, v in json.items():
                setattr(geo, k, v)
        return geo
    
class Comments(Model):

    @classmethod
    def parse(cls, api, json):
        comments = cls(api)
        for k, v in json.items():
            if k == 'user':
                user = User.parse(api, v)
                setattr(comments, 'author', user)
                setattr(comments, 'user', user)
            elif k == 'status':
                status = Status.parse(api, v)
                setattr(comments, 'user', status)
            elif k == 'created_at':
                setattr(comments, k, parse_datetime(v))
            elif k == 'reply_comment':
                setattr(comments, k, User.parse(api, v))
            else:
                setattr(comments, k, v)
        return comments

    def destroy(self):
        return self._api.destroy_status(self.id)

    def retweet(self):
        return self._api.retweet(self.id)

    def retweets(self):
        return self._api.retweets(self.id)

    def favorite(self):
        return self._api.create_favorite(self.id)

class User(Model):

    @classmethod
    def parse(cls, api, json):
        user = cls(api)
        for k, v in json.items():
            if k == 'created_at':
                setattr(user, k, parse_datetime(v))
            elif k == 'status':
                setattr(user, k, Status.parse(api, v))
            elif k == 'screen_name':
                setattr(user, k, v)
            elif k == 'following':
                # twitter sets this to null if it is false
                if v is True:
                    setattr(user, k, True)
                else:
                    setattr(user, k, False)
            else:
                setattr(user, k, v)
        return user

    @classmethod
    def parse_list(cls, api, json_list):
        if isinstance(json_list, list):
            item_list = json_list
        else:
            item_list = json_list['users']

        results = ResultSet()
        for obj in item_list:
            results.append(cls.parse(api, obj))
        return results

    def timeline(self, **kargs):
        return self._api.user_timeline(user_id=self.id, **kargs)

    def friends(self, **kargs):
        return self._api.friends(user_id=self.id, **kargs)

    def followers(self, **kargs):
        return self._api.followers(user_id=self.id, **kargs)

    def follow(self):
        self._api.create_friendship(user_id=self.id)
        self.following = True

    def unfollow(self):
        self._api.destroy_friendship(user_id=self.id)
        self.following = False

    def lists_memberships(self, *args, **kargs):
        return self._api.lists_memberships(user=self.screen_name, *args, **kargs)

    def lists_subscriptions(self, *args, **kargs):
        return self._api.lists_subscriptions(user=self.screen_name, *args, **kargs)

    def lists(self, *args, **kargs):
        return self._api.lists(user=self.screen_name, *args, **kargs)

    def followers_ids(self, *args, **kargs):
        return self._api.followers_ids(user_id=self.id, *args, **kargs)




class DirectMessage(Model):
    @classmethod
    def parse(cls, api, json):
        dm = cls(api)
        for k, v in json.items():
            if k == 'sender' or k == 'recipient':
                setattr(dm, k, User.parse(api, v))
            elif k == 'created_at':
                setattr(dm, k, parse_datetime(v))
            else:
                setattr(dm, k, v)
        return dm

class Friendship(Model):

    @classmethod
    def parse(cls, api, json):
       
        source = cls(api)
        for k, v in json['source'].items():
            setattr(source, k, v)

        # parse target
        target = cls(api)
        for k, v in json['target'].items():
            setattr(target, k, v)

        return source, target


class SavedSearch(Model):

    @classmethod
    def parse(cls, api, json):
        ss = cls(api)
        for k, v in json.items():
            if k == 'created_at':
                setattr(ss, k, parse_datetime(v))
            else:
                setattr(ss, k, v)
        return ss

    def destroy(self):
        return self._api.destroy_saved_search(self.id)


class SearchResult(Model):

    @classmethod
    def parse(cls, api, json):
        result = cls()
        for k, v in json.items():
            if k == 'created_at':
                setattr(result, k, parse_search_datetime(v))
            elif k == 'source':
                setattr(result, k, parse_html_value(unescape_html(v)))
            else:
                setattr(result, k, v)
        return result

    @classmethod
    def parse_list(cls, api, json_list, result_set=None):
        results = ResultSet()
        results.max_id = json_list.get('max_id')
        results.since_id = json_list.get('since_id')
        results.refresh_url = json_list.get('refresh_url')
        results.next_page = json_list.get('next_page')
        results.results_per_page = json_list.get('results_per_page')
        results.page = json_list.get('page')
        results.completed_in = json_list.get('completed_in')
        results.query = json_list.get('query')

        for obj in json_list['results']:
            results.append(cls.parse(api, obj))
        return results

class List(Model):

    @classmethod
    def parse(cls, api, json):
        lst = List(api)
        for k,v in json.items():
            if k == 'user':
                setattr(lst, k, User.parse(api, v))
            else:
                setattr(lst, k, v)
        return lst

    @classmethod
    def parse_list(cls, api, json_list, result_set=None):
        results = ResultSet()
        for obj in json_list['lists']:
            results.append(cls.parse(api, obj))
        return results

    def update(self, **kargs):
        return self._api.update_list(self.slug, **kargs)

    def destroy(self):
        return self._api.destroy_list(self.slug)

    def timeline(self, **kargs):
        return self._api.list_timeline(self.user.screen_name, self.slug, **kargs)

    def add_member(self, id):
        return self._api.add_list_member(self.slug, id)

    def remove_member(self, id):
        return self._api.remove_list_member(self.slug, id)

    def members(self, **kargs):
        return self._api.list_members(self.user.screen_name, self.slug, **kargs)

    def is_member(self, id):
        return self._api.is_list_member(self.user.screen_name, self.slug, id)

    def subscribe(self):
        return self._api.subscribe_list(self.user.screen_name, self.slug)

    def unsubscribe(self):
        return self._api.unsubscribe_list(self.user.screen_name, self.slug)

    def subscribers(self, **kargs):
        return self._api.list_subscribers(self.user.screen_name, self.slug, **kargs)

    def is_subscribed(self, id):
        return self._api.is_subscribed_list(self.user.screen_name, self.slug, id)

class JSONModel(Model):

    @classmethod
    def parse(cls, api, json):
        lst = JSONModel(api)
        for k,v in json.items():
            setattr(lst, k, v)
        return lst

class IDSModel(Model):
    @classmethod
    def parse(cls, api, json):
        ids = IDSModel(api)
        for k, v in json.items():            
            setattr(ids, k, v)
        return ids
    
class Counts(Model):
    @classmethod
    def parse(cls, api, json):
        ids = Counts(api)
        for k, v in json.items():            
            setattr(ids, k, v)
        return ids
class Trends(Model):
    @classmethod
    def parse(cls, api, json):
        ids = Trends(api)
        for k,v in json.items():
            setattr(ids, k , v)
        return ids
class Tags(Model):
    @classmethod
    def parse(cls, api, json):
        ts = Tags(api)
        for k,v in json.items():
            setattr(ts, k , v)
            setattr(ts,"id",k)
        return ts   
                         
    
class ModelFactory(object):
    """
    Used by parsers for creating instances
    of models. You may subclass this factory
    to add your own extended models.
    """

    status = Status
    comments = Comments
    user = User
    direct_message = DirectMessage
    friendship = Friendship
    saved_search = SavedSearch
    search_result = SearchResult
    list = List
    json = JSONModel
    ids_list = IDSModel
    counts = Counts
    trends = Trends
    tags = Tags

########NEW FILE########
__FILENAME__ = oauth
#coding=utf-8
"""
The MIT License

Copyright (c) 2007 Leah Culver

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
THE SOFTWARE.
"""

import cgi
import urllib
import time
import random
import urlparse
import hmac
import binascii


VERSION = '1.0' # Hi Blaine!
HTTP_METHOD = 'GET'
SIGNATURE_METHOD = 'PLAINTEXT'


class OAuthError(RuntimeError):
    """Generic exception class."""
    def __init__(self, message='OAuth error occured.'):
        self.message = message

def build_authenticate_header(realm=''):
    """Optional WWW-Authenticate header (401 error)"""
    return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

def escape(s):
    """Escape a URL including any /."""
    return urllib.quote(s, safe='~')

def _utf8_str(s):
    """Convert unicode to utf-8."""
    if isinstance(s, unicode):
        return s.encode("utf-8")
    else:
        return str(s)

def generate_timestamp():
    """Get seconds since epoch (UTC)."""
    return int(time.time())

def generate_nonce(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])

def generate_verifier(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


class OAuthConsumer(object):
    """Consumer of OAuth authentication.

    OAuthConsumer is a data type that represents the identity of the Consumer
    via its shared secret with the Service Provider.

    """
    key = None
    secret = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret


class OAuthToken(object):
    """OAuthToken is a data type that represents an End User via either an access
    or request token.
    
    key -- the token
    secret -- the token secret

    """
    key = None
    secret = None
    callback = None
    callback_confirmed = None
    verifier = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret

    def set_callback(self, callback):
        self.callback = callback
        self.callback_confirmed = 'true'

    def set_verifier(self, verifier=None):
        if verifier is not None:
            self.verifier = verifier
        else:
            self.verifier = generate_verifier()

    def get_callback_url(self):
        if self.callback and self.verifier:
            # Append the oauth_verifier.
            parts = urlparse.urlparse(self.callback)
            scheme, netloc, path, params, query, fragment = parts[:6]
            if query:
                query = '%s&oauth_verifier=%s' % (query, self.verifier)
            else:
                query = 'oauth_verifier=%s' % self.verifier
            return urlparse.urlunparse((scheme, netloc, path, params,
                query, fragment))
        return self.callback

    def to_string(self):
        data = {
            'oauth_token': self.key,
            'oauth_token_secret': self.secret,
        }
        if self.callback_confirmed is not None:
            data['oauth_callback_confirmed'] = self.callback_confirmed
        return urllib.urlencode(data)
 
    def from_string(s):
        """ Returns a token from something like:
        oauth_token_secret=xxx&oauth_token=xxx
        """
        params = cgi.parse_qs(s, keep_blank_values=False)
        key = params['oauth_token'][0]
        secret = params['oauth_token_secret'][0]
        token = OAuthToken(key, secret)
        try:
            token.callback_confirmed = params['oauth_callback_confirmed'][0]
        except KeyError:
            pass # 1.0, no callback confirmed.
        return token
    from_string = staticmethod(from_string)

    def __str__(self):
        return self.to_string()


class OAuthRequest(object):
    """OAuthRequest represents the request and can be serialized.

    OAuth parameters:
        - oauth_consumer_key 
        - oauth_token
        - oauth_signature_method
        - oauth_signature 
        - oauth_timestamp 
        - oauth_nonce
        - oauth_version
        - oauth_verifier
        ... any additional parameters, as defined by the Service Provider.
    """
    parameters = None # OAuth parameters.
    http_method = HTTP_METHOD
    http_url = None
    version = VERSION

    def __init__(self, http_method=HTTP_METHOD, http_url=None, parameters=None):
        self.http_method = http_method
        self.http_url = http_url
        self.parameters = parameters or {}
    def set_parameter(self, parameter, value):
        self.parameters[parameter] = value

    def get_parameter(self, parameter):
        try:
            return self.parameters[parameter]
        except:
            raise OAuthError('Parameter not found: %s' % parameter)

    def _get_timestamp_nonce(self):
        return self.get_parameter('oauth_timestamp'), self.get_parameter(
            'oauth_nonce')

    def get_nonoauth_parameters(self):
        """Get any non-OAuth parameters."""
        parameters = {}
        for k, v in self.parameters.iteritems():
            # Ignore oauth parameters.
            if k.find('oauth_') < 0:
                parameters[k] = v
        return parameters

    def to_header(self, realm=''):
        """Serialize as a header for an HTTPAuth request."""
        auth_header = 'OAuth realm="%s"' % realm
        # Add the oauth parameters.
        if self.parameters:
            for k, v in self.parameters.iteritems():
                if k[:6] == 'oauth_':
                    auth_header += ', %s="%s"' % (k, escape(str(v)))
        return {'Authorization': auth_header}

    def to_postdata(self):
        """Serialize as post data for a POST request."""
        return '&'.join(['%s=%s' % (escape(str(k)), escape(str(v))) \
            for k, v in self.parameters.iteritems()])

    def to_url(self):
        """Serialize as a URL for a GET request."""
        return '%s?%s' % (self.get_normalized_http_url(), self.to_postdata())

    def get_normalized_parameters(self):
        """Return a string that contains the parameters that must be signed."""
        params = self.parameters
        try:
            # Exclude the signature if it exists.
            del params['oauth_signature']
        except:
            pass
        # Escape key values before sorting.
        key_values = [(escape(_utf8_str(k)), escape(_utf8_str(v))) \
            for k,v in params.items()]
        # Sort lexicographically, first after key, then after value.
        key_values.sort()
        # Combine key value pairs into a string.
        return '&'.join(['%s=%s' % (k, v) for k, v in key_values])

    def get_normalized_http_method(self):
        """Uppercases the http method."""
        return self.http_method.upper()

    def get_normalized_http_url(self):
        """Parses the URL and rebuilds it to be scheme://host/path."""
        parts = urlparse.urlparse(self.http_url)
        scheme, netloc, path = parts[:3]
        # Exclude default port numbers.
        if scheme == 'http' and netloc[-3:] == ':80':
            netloc = netloc[:-3]
        elif scheme == 'https' and netloc[-4:] == ':443':
            netloc = netloc[:-4]
        return '%s://%s%s' % (scheme, netloc, path)

    def sign_request(self, signature_method, consumer, token):
        """Set the signature parameter to the result of build_signature."""
        # Set the signature method.
        self.set_parameter('oauth_signature_method',
            signature_method.get_name())
        # Set the signature.
        self.set_parameter('oauth_signature',self.build_signature(signature_method, consumer, token))

    def build_signature(self, signature_method, consumer, token):
        """Calls the build signature method within the signature method."""
        return signature_method.build_signature(self, consumer, token)

    def from_request(http_method, http_url, headers=None, parameters=None,
            query_string=None):
        """Combines multiple parameter sources."""
        if parameters is None:
            parameters = {}

        # Headers
        if headers and 'Authorization' in headers:
            auth_header = headers['Authorization']
            # Check that the authorization header is OAuth.
            if auth_header[:6] == 'OAuth ':
                auth_header = auth_header[6:]
                try:
                    # Get the parameters from the header.
                    header_params = OAuthRequest._split_header(auth_header)
                    parameters.update(header_params)
                except:
                    raise OAuthError('Unable to parse OAuth parameters from '
                        'Authorization header.')

        # GET or POST query string.
        if query_string:
            query_params = OAuthRequest._split_url_string(query_string)
            parameters.update(query_params)

        # URL parameters.
        param_str = urlparse.urlparse(http_url)[4] # query
        url_params = OAuthRequest._split_url_string(param_str)
        parameters.update(url_params)

        if parameters:
            return OAuthRequest(http_method, http_url, parameters)

        return None
    from_request = staticmethod(from_request)

    def from_consumer_and_token(oauth_consumer, token=None,
            callback=None, verifier=None, http_method=HTTP_METHOD,
            http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        defaults = {
            'oauth_consumer_key': oauth_consumer.key,
            'oauth_timestamp': generate_timestamp(),
            'oauth_nonce': generate_nonce(),
            'oauth_version': OAuthRequest.version,
        }

        defaults.update(parameters)
        parameters = defaults

        if token:
            parameters['oauth_token'] = token.key
            if token.callback:
                parameters['oauth_callback'] = token.callback
            # 1.0a support for verifier.
            if verifier:
                parameters['oauth_verifier'] = verifier
        elif callback:
            # 1.0a support for callback in the request token request.
            parameters['oauth_callback'] = callback

        return OAuthRequest(http_method, http_url, parameters)
    from_consumer_and_token = staticmethod(from_consumer_and_token)

    def from_token_and_callback(token, callback=None, http_method=HTTP_METHOD,
            http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        parameters['oauth_token'] = token.key

        if callback:
            parameters['oauth_callback'] = callback

        return OAuthRequest(http_method, http_url, parameters)
    from_token_and_callback = staticmethod(from_token_and_callback)

    def _split_header(header):
        """Turn Authorization: header into parameters."""
        params = {}
        parts = header.split(',')
        for param in parts:
            # Ignore realm parameter.
            if param.find('realm') > -1:
                continue
            # Remove whitespace.
            param = param.strip()
            # Split key-value.
            param_parts = param.split('=', 1)
            # Remove quotes and unescape the value.
            params[param_parts[0]] = urllib.unquote(param_parts[1].strip('\"'))
        return params
    _split_header = staticmethod(_split_header)

    def _split_url_string(param_str):
        """Turn URL string into parameters."""
        parameters = cgi.parse_qs(param_str, keep_blank_values=False)
        for k, v in parameters.iteritems():
            parameters[k] = urllib.unquote(v[0])
        return parameters
    _split_url_string = staticmethod(_split_url_string)

class OAuthServer(object):
    """A worker to check the validity of a request against a data store."""
    timestamp_threshold = 300 # In seconds, five minutes.
    version = VERSION
    signature_methods = None
    data_store = None

    def __init__(self, data_store=None, signature_methods=None):
        self.data_store = data_store
        self.signature_methods = signature_methods or {}

    def set_data_store(self, data_store):
        self.data_store = data_store

    def get_data_store(self):
        return self.data_store

    def add_signature_method(self, signature_method):
        self.signature_methods[signature_method.get_name()] = signature_method
        return self.signature_methods

    def fetch_request_token(self, oauth_request):
        """Processes a request_token request and returns the
        request token on success.
        """
        try:
            # Get the request token for authorization.
            token = self._get_token(oauth_request, 'request')
        except OAuthError:
            # No token required for the initial token request.
            version = self._get_version(oauth_request)
            consumer = self._get_consumer(oauth_request)
            try:
                callback = self.get_callback(oauth_request)
            except OAuthError:
                callback = None # 1.0, no callback specified.
            self._check_signature(oauth_request, consumer, None)
            # Fetch a new token.
            token = self.data_store.fetch_request_token(consumer, callback)
        return token

    def fetch_access_token(self, oauth_request):
        """Processes an access_token request and returns the
        access token on success.
        """
        version = self._get_version(oauth_request)
        consumer = self._get_consumer(oauth_request)
        try:
            verifier = self._get_verifier(oauth_request)
        except OAuthError:
            verifier = None
        # Get the request token.
        token = self._get_token(oauth_request, 'request')
        self._check_signature(oauth_request, consumer, token)
        new_token = self.data_store.fetch_access_token(consumer, token, verifier)
        return new_token

    def verify_request(self, oauth_request):
        """Verifies an api call and checks all the parameters."""
        # -> consumer and token
        version = self._get_version(oauth_request)
        consumer = self._get_consumer(oauth_request)
        # Get the access token.
        token = self._get_token(oauth_request, 'access')
        self._check_signature(oauth_request, consumer, token)
        parameters = oauth_request.get_nonoauth_parameters()
        return consumer, token, parameters

    def authorize_token(self, token, user):
        """Authorize a request token."""
        return self.data_store.authorize_request_token(token, user)

    def get_callback(self, oauth_request):
        """Get the callback URL."""
        return oauth_request.get_parameter('oauth_callback')
 
    def build_authenticate_header(self, realm=''):
        """Optional support for the authenticate header."""
        return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

    def _get_version(self, oauth_request):
        """Verify the correct version request for this server."""
        try:
            version = oauth_request.get_parameter('oauth_version')
        except:
            version = VERSION
        if version and version != self.version:
            raise OAuthError('OAuth version %s not supported.' % str(version))
        return version

    def _get_signature_method(self, oauth_request):
        """Figure out the signature with some defaults."""
        try:
            signature_method = oauth_request.get_parameter(
                'oauth_signature_method')
        except:
            signature_method = SIGNATURE_METHOD
        try:
            # Get the signature method object.
            signature_method = self.signature_methods[signature_method]
        except:
            signature_method_names = ', '.join(self.signature_methods.keys())
            raise OAuthError('Signature method %s not supported try one of the '
                'following: %s' % (signature_method, signature_method_names))

        return signature_method

    def _get_consumer(self, oauth_request):
        consumer_key = oauth_request.get_parameter('oauth_consumer_key')
        consumer = self.data_store.lookup_consumer(consumer_key)
        if not consumer:
            raise OAuthError('Invalid consumer.')
        return consumer

    def _get_token(self, oauth_request, token_type='access'):
        """Try to find the token for the provided request token key."""
        token_field = oauth_request.get_parameter('oauth_token')
        token = self.data_store.lookup_token(token_type, token_field)
        if not token:
            raise OAuthError('Invalid %s token: %s' % (token_type, token_field))
        return token
    
    def _get_verifier(self, oauth_request):
        return oauth_request.get_parameter('oauth_verifier')

    def _check_signature(self, oauth_request, consumer, token):
        timestamp, nonce = oauth_request._get_timestamp_nonce()
        self._check_timestamp(timestamp)
        self._check_nonce(consumer, token, nonce)
        signature_method = self._get_signature_method(oauth_request)
        try:
            signature = oauth_request.get_parameter('oauth_signature')
        except:
            raise OAuthError('Missing signature.')
        # Validate the signature.
        valid_sig = signature_method.check_signature(oauth_request, consumer,
            token, signature)
        if not valid_sig:
            key, base = signature_method.build_signature_base_string(
                oauth_request, consumer, token)
            raise OAuthError('Invalid signature. Expected signature base '
                'string: %s' % base)
        built = signature_method.build_signature(oauth_request, consumer, token)

    def _check_timestamp(self, timestamp):
        """Verify that timestamp is recentish."""
        timestamp = int(timestamp)
        now = int(time.time())
        lapsed = abs(now - timestamp)
        if lapsed > self.timestamp_threshold:
            raise OAuthError('Expired timestamp: given %d and now %s has a '
                'greater difference than threshold %d' %
                (timestamp, now, self.timestamp_threshold))

    def _check_nonce(self, consumer, token, nonce):
        """Verify that the nonce is uniqueish."""
        nonce = self.data_store.lookup_nonce(consumer, token, nonce)
        if nonce:
            raise OAuthError('Nonce already used: %s' % str(nonce))


class OAuthClient(object):
    """OAuthClient is a worker to attempt to execute a request."""
    consumer = None
    token = None

    def __init__(self, oauth_consumer, oauth_token):
        self.consumer = oauth_consumer
        self.token = oauth_token

    def get_consumer(self):
        return self.consumer

    def get_token(self):
        return self.token

    def fetch_request_token(self, oauth_request):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_access_token(self, oauth_request):
        """-> OAuthToken."""
        raise NotImplementedError

    def access_resource(self, oauth_request):
        """-> Some protected resource."""
        raise NotImplementedError


class OAuthDataStore(object):
    """A database abstraction used to lookup consumers and tokens."""

    def lookup_consumer(self, key):
        """-> OAuthConsumer."""
        raise NotImplementedError

    def lookup_token(self, oauth_consumer, token_type, token_token):
        """-> OAuthToken."""
        raise NotImplementedError

    def lookup_nonce(self, oauth_consumer, oauth_token, nonce):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_request_token(self, oauth_consumer, oauth_callback):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_access_token(self, oauth_consumer, oauth_token, oauth_verifier):
        """-> OAuthToken."""
        raise NotImplementedError

    def authorize_request_token(self, oauth_token, user):
        """-> OAuthToken."""
        raise NotImplementedError


class OAuthSignatureMethod(object):
    """A strategy class that implements a signature method."""
    def get_name(self):
        """-> str."""
        raise NotImplementedError

    def build_signature_base_string(self, oauth_request, oauth_consumer, oauth_token):
        """-> str key, str raw."""
        raise NotImplementedError

    def build_signature(self, oauth_request, oauth_consumer, oauth_token):
        """-> str."""
        raise NotImplementedError

    def check_signature(self, oauth_request, consumer, token, signature):
        built = self.build_signature(oauth_request, consumer, token)
        return built == signature


class OAuthSignatureMethod_HMAC_SHA1(OAuthSignatureMethod):

    def get_name(self):
        return 'HMAC-SHA1'
        
    def build_signature_base_string(self, oauth_request, consumer, token):
        sig = (
            escape(oauth_request.get_normalized_http_method()),
            escape(oauth_request.get_normalized_http_url()),
            escape(oauth_request.get_normalized_parameters()),
        )

        key = '%s&' % escape(consumer.secret)
        if token:
            key += escape(token.secret)
        #print "OAuth base string:" + str(sig)
        raw = '&'.join(sig)
        return key, raw

    def build_signature(self, oauth_request, consumer, token):
        """Builds the base signature string."""
        key, raw = self.build_signature_base_string(oauth_request, consumer,
            token)

        # HMAC object.
        try:
            import hashlib # 2.5
            hashed = hmac.new(key, raw, hashlib.sha1)
        except:
            import sha # Deprecated
            hashed = hmac.new(key, raw, sha)

        # Calculate the digest base 64.
        return binascii.b2a_base64(hashed.digest())[:-1]


class OAuthSignatureMethod_PLAINTEXT(OAuthSignatureMethod):

    def get_name(self):
        return 'PLAINTEXT'

    def build_signature_base_string(self, oauth_request, consumer, token):
        """Concatenates the consumer key and secret."""
        sig = '%s&' % escape(consumer.secret)
        if token:
            sig = sig + escape(token.secret)
        return sig, sig

    def build_signature(self, oauth_request, consumer, token):
        key, raw = self.build_signature_base_string(oauth_request, consumer,
            token)
        return key

########NEW FILE########
__FILENAME__ = parsers
#coding=utf-8
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

from models import ModelFactory
from utils import import_simplejson
from error import WeibopError

class Parser(object):

    def parse(self, method, payload):
        """
        Parse the response payload and return the result.
        Returns a tuple that contains the result data and the cursors
        (or None if not present).
        """
        raise NotImplementedError

    def parse_error(self, method, payload):
        """
        Parse the error message from payload.
        If unable to parse the message, throw an exception
        and default error message will be used.
        """
        raise NotImplementedError


class JSONParser(Parser):

    payload_format = 'json'

    def __init__(self):
        self.json_lib = import_simplejson()

    def parse(self, method, payload):
        try:
            json = self.json_lib.loads(payload)
        except Exception, e:
            print "Failed to parse JSON payload:"+ str(payload)
            raise WeibopError('Failed to parse JSON payload: %s' % e)

        #if isinstance(json, dict) and 'previous_cursor' in json and 'next_cursor' in json:
        #    cursors = json['previous_cursor'], json['next_cursor']
        #    return json, cursors
        #else:
        return json

    def parse_error(self, method, payload):
        return self.json_lib.loads(payload)


class ModelParser(JSONParser):

    def __init__(self, model_factory=None):
        JSONParser.__init__(self)
        self.model_factory = model_factory or ModelFactory

    def parse(self, method, payload):
        try:
            if method.payload_type is None: return
            model = getattr(self.model_factory, method.payload_type)
        except AttributeError:
            raise WeibopError('No model for this payload type: %s' % method.payload_type)

        json = JSONParser.parse(self, method, payload)
        if isinstance(json, tuple):
            json, cursors = json
        else:
            cursors = None

        if method.payload_list:
            result = model.parse_list(method.api, json)
        else:
            result = model.parse(method.api, json)
        if cursors:
            return result, cursors
        else:
            return result


########NEW FILE########
__FILENAME__ = streaming
#coding=utf-8
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

import httplib
from socket import timeout
from threading import Thread
from time import sleep
import urllib

from auth import BasicAuthHandler
from models import Status
from api import API
from error import WeibopError

from utils import import_simplejson
json = import_simplejson()

STREAM_VERSION = 1


class StreamListener(object):

    def __init__(self, api=None):
        self.api = api or API()

    def on_data(self, data):
        """Called when raw data is received from connection.

        Override this method if you wish to manually handle
        the stream data. Return False to stop stream and close connection.
        """

        if 'in_reply_to_status_id' in data:
            status = Status.parse(self.api, json.loads(data))
            if self.on_status(status) is False:
                return False
        elif 'delete' in data:
            delete = json.loads(data)['delete']['status']
            if self.on_delete(delete['id'], delete['user_id']) is False:
                return False
        elif 'limit' in data:
            if self.on_limit(json.loads(data)['limit']['track']) is False:
                return False

    def on_status(self, status):
        """Called when a new status arrives"""
        return

    def on_delete(self, status_id, user_id):
        """Called when a delete notice arrives for a status"""
        return

    def on_limit(self, track):
        """Called when a limitation notice arrvies"""
        return

    def on_error(self, status_code):
        """Called when a non-200 status code is returned"""
        return False

    def on_timeout(self):
        """Called when stream connection times out"""
        return


class Stream(object):

    host = 'stream.twitter.com'

    def __init__(self, username, password, listener, timeout=5.0, retry_count = None,
                    retry_time = 10.0, snooze_time = 5.0, buffer_size=1500, headers=None):
        self.auth = BasicAuthHandler(username, password)
        self.running = False
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_time = retry_time
        self.snooze_time = snooze_time
        self.buffer_size = buffer_size
        self.listener = listener
        self.api = API()
        self.headers = headers or {}
        self.body = None

    def _run(self):
        # setup
        self.auth.apply_auth(None, None, self.headers, None)

        # enter loop
        error_counter = 0
        conn = None
        while self.running:
            if self.retry_count and error_counter > self.retry_count:
                # quit if error count greater than retry count
                break
            try:
                conn = httplib.HTTPConnection(self.host)
                conn.connect()
                conn.sock.settimeout(self.timeout)
                conn.request('POST', self.url, self.body, headers=self.headers)
                resp = conn.getresponse()
                if resp.status != 200:
                    if self.listener.on_error(resp.status) is False:
                        break
                    error_counter += 1
                    sleep(self.retry_time)
                else:
                    error_counter = 0
                    self._read_loop(resp)
            except timeout:
                if self.listener.on_timeout() == False:
                    break
                if self.running is False:
                    break
                conn.close()
                sleep(self.snooze_time)
            except Exception:
                # any other exception is fatal, so kill loop
                break

        # cleanup
        self.running = False
        if conn:
            conn.close()

    def _read_loop(self, resp):
        data = ''
        while self.running:
            if resp.isclosed():
                break

            # read length
            length = ''
            while True:
                c = resp.read(1)
                if c == '\n':
                    break
                length += c
            length = length.strip()
            if length.isdigit():
                length = int(length)
            else:
                continue

            # read data and pass into listener
            data = resp.read(length)
            if self.listener.on_data(data) is False:
                self.running = False

    def _start(self, async):
        self.running = True
        if async:
            Thread(target=self._run).start()
        else:
            self._run()

    def firehose(self, count=None, async=False):
        if self.running:
            raise WeibopError('Stream object already connected!')
        self.url = '/%i/statuses/firehose.json?delimited=length' % STREAM_VERSION
        if count:
            self.url += '&count=%s' % count
        self._start(async)

    def retweet(self, async=False):
        if self.running:
            raise WeibopError('Stream object already connected!')
        self.url = '/%i/statuses/retweet.json?delimited=length' % STREAM_VERSION
        self._start(async)

    def sample(self, count=None, async=False):
        if self.running:
            raise WeibopError('Stream object already connected!')
        self.url = '/%i/statuses/sample.json?delimited=length' % STREAM_VERSION
        if count:
            self.url += '&count=%s' % count
        self._start(async)

    def filter(self, follow=None, track=None, async=False):
        params = {}
        self.headers['Content-type'] = "application/x-www-form-urlencoded"
        if self.running:
            raise WeibopError('Stream object already connected!')
        self.url = '/%i/statuses/filter.json?delimited=length' % STREAM_VERSION
        if follow:
            params['follow'] = ','.join(map(str, follow))
        if track:
            params['track'] = ','.join(map(str, track))
        self.body = urllib.urlencode(params)
        self._start(async)

    def disconnect(self):
        if self.running is False:
            return
        self.running = False


########NEW FILE########
__FILENAME__ = utils
#coding=utf-8
# Copyright 2010 Joshua Roesslein
# See LICENSE for details.

from datetime import datetime
import time
import htmlentitydefs
import re


def parse_datetime(str):

    # We must parse datetime this way to work in python 2.4
    return datetime(*(time.strptime(str, '%a %b %d %H:%M:%S +0800 %Y')[0:6]))


def parse_html_value(html):

    return html[html.find('>')+1:html.rfind('<')]


def parse_a_href(atag):

    start = atag.find('"') + 1
    end = atag.find('"', start)
    return atag[start:end]


def parse_search_datetime(str):

    # python 2.4
    return datetime(*(time.strptime(str, '%a, %d %b %Y %H:%M:%S +0000')[0:6]))


def unescape_html(text):
    """Created by Fredrik Lundh (http://effbot.org/zone/re-sub.htm#unescape-html)"""
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)


def convert_to_utf8_str(arg):
    # written by Michael Norton (http://docondev.blogspot.com/)
    if isinstance(arg, unicode):
        arg = arg.encode('utf-8')
    elif not isinstance(arg, str):
        arg = str(arg)
    return arg



def import_simplejson():
    try:
        import simplejson as json
    except ImportError:
        try:
            import json  # Python 2.6+
        except ImportError:
            try:
                from django.utils import simplejson as json  # Google App Engine
            except ImportError:
                raise ImportError, "Can't load a json library"

    return json


########NEW FILE########
