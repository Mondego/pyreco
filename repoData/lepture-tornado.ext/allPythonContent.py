__FILENAME__ = database
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.orm import Query
from sqlalchemy.ext.declarative import declarative_base, declared_attr

from sqlalchemy.orm import joinedload, joinedload_all
from sqlalchemy.orm.util import _entity_descriptor
from sqlalchemy.util import to_list
from sqlalchemy.sql import operators, extract
from tornado.ioloop import PeriodicCallback

"""
DjangoQuery From
https://github.com/mitsuhiko/sqlalchemy-django-query
"""


class DjangoQuery(Query):
    """Can be mixed into any Query class of SQLAlchemy and extends it to
    implements more Django like behavior:

    -   `filter_by` supports implicit joining and subitem accessing with
        double underscores.
    -   `exclude_by` works like `filter_by` just that every expression is
        automatically negated.
    -   `order_by` supports ordering by field name with an optional `-`
        in front.
    """
    _underscore_operators = {
        'gt': operators.gt,
        'lt': operators.lt,
        'gte': operators.ge,
        'lte': operators.le,
        'contains': operators.contains_op,
        'in': operators.in_op,
        'exact': operators.eq,
        'iexact': operators.ilike_op,
        'startswith': operators.startswith_op,
        'istartswith': lambda c, x: c.ilike(x.replace('%', '%%') + '%'),
        'iendswith': lambda c, x: c.ilike('%' + x.replace('%', '%%')),
        'endswith': operators.endswith_op,
        'isnull': lambda c, x: x and c != None or c == None,
        'range': operators.between_op,
        'year': lambda c, x: extract('year', c) == x,
        'month': lambda c, x: extract('month', c) == x,
        'day': lambda c, x: extract('day', c) == x
    }

    def filter_by(self, **kwargs):
        return self._filter_or_exclude(False, kwargs)

    def exclude_by(self, **kwargs):
        return self._filter_or_exclude(True, kwargs)

    def select_related(self, *columns, **options):
        depth = options.pop('depth', None)
        if options:
            raise TypeError('Unexpected argument %r' % iter(options).next())
        if depth not in (None, 1):
            raise TypeError('Depth can only be 1 or None currently')
        need_all = depth is None
        columns = list(columns)
        for idx, column in enumerate(columns):
            column = column.replace('__', '.')
            if '.' in column:
                need_all = True
            columns[idx] = column
        func = (need_all and joinedload_all or joinedload)
        return self.options(func(*columns))

    def order_by(self, *args):
        args = list(args)
        joins_needed = []
        for idx, arg in enumerate(args):
            q = self
            if not isinstance(arg, basestring):
                continue
            if arg[0] in '+-':
                desc = arg[0] == '-'
                arg = arg[1:]
            else:
                desc = False
            q = self
            column = None
            for token in arg.split('__'):
                column = _entity_descriptor(q._joinpoint_zero(), token)
                if column.impl.uses_objects:
                    q = q.join(column)
                    joins_needed.append(column)
                    column = None
            if column is None:
                raise ValueError('Tried to order by table, column expected')
            if desc:
                column = column.desc()
            args[idx] = column

        q = super(DjangoQuery, self).order_by(*args)
        for join in joins_needed:
            q = q.join(join)
        return q

    def _filter_or_exclude(self, negate, kwargs):
        q = self
        negate_if = lambda expr: expr if not negate else ~expr
        column = None

        for arg, value in kwargs.iteritems():
            for token in arg.split('__'):
                if column is None:
                    column = _entity_descriptor(q._joinpoint_zero(), token)
                    if column.impl.uses_objects:
                        q = q.join(column)
                        column = None
                elif token in self._underscore_operators:
                    op = self._underscore_operators[token]
                    q = q.filter(negate_if(op(column, *to_list(value))))
                    column = None
                else:
                    raise ValueError('No idea what to do with %r' % token)
            if column is not None:
                q = q.filter(negate_if(column == value))
                column = None
            q = q.reset_joinpoint()
        return q


class Model(object):
    id = Column(Integer, primary_key=True)  # primary key
    query = None

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    @declared_attr
    def __table_args__(cls):
        return {'mysql_engine': 'InnoDB'}

    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)


def create_session(engine):
    if not engine:
        return None
    session = sessionmaker(bind=engine, query_cls=DjangoQuery)
    return scoped_session(session)


class SQLAlchemy(object):
    """
    Example::

        db = SQLAlchemy("mysql://user:pass@host:port/db", pool_recycle=3600)

        from sqlalchemy import Column, String

        class User(db.Model):
            username = Column(String(16), unique=True, nullable=False)
            password = Column(String(30), nullable=False)

        >>> User.query.filter_by(username='yourname')

    """
    def __init__(self, master, slaves=[], **kwargs):
        self.engine = create_engine(master, **kwargs)
        self.session = create_session(self.engine)
        self.slaves = []
        for slave in  slaves:
            slave = create_engine(slave, **kwargs)
            self.slaves.append(create_session(slave))

        if 'pool_recycle' in kwargs:
            # ping db, so that mysql won't goaway
            PeriodicCallback(self._ping_db,
                             kwargs['pool_recycle'] * 1000).start()

    @property
    def Model(self):
        if hasattr(self, '_base'):
            base = self._base
        else:
            base = declarative_base(cls=Model, name='Model')
            self._base = base
        if self.slaves:
            slave = random.choice(self.slaves)
            base.query = slave.query_property()
        else:
            base.query = self.session.query_property()
        return base

    def _ping_db(self):
        self.session.execute('show variables')
        for slave in self.slaves:
            slave.execute('show variables')

    def create_db(self):
        self.Model.metadata.create_all(self.engine)

########NEW FILE########
__FILENAME__ = demo
#!/usr/bin/env python

import os

import tornado.options
from tornado.options import options
from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer
from tornado import web
from tornado import gen

from third import DoubanMixin
from third import RenrenGraphMixin, RenrenRestMixin
from third import WeiboMixin

_app_cache = {}

host = 'http://dev.example.com'

class InstanceCache(object):
    def clear(self):
        global _app_cache

        for key, value in _app_cache.iteritems():
            expiry = value[1]
            if expiry and time() > expiry:
                del _app_cache[key]

    def flush_all(self):
        global _app_cache

        _app_cache = {}

    def set(self, key, value, seconds=0):
        global _app_cache

        if seconds < 0:
            seconds = 0

        _app_cache[key] = (value, time() + seconds if seconds else 0)

    def get(self, key):
        global _app_cache

        value = _app_cache.get(key, None)
        if value:
            expiry = value[1]
            if expiry and time() > expiry:
                del _app_cache[key]
                return None
            else:
                return value[0]
        return None

    def delete(self, key):
        global _app_cache
    
        if _app_cache.has_key(key):
            del _app_cache[key]
        return None

class BaseHandler(web.RequestHandler):
    @property
    def cache(self):
        return self.application.cache

class DoubanHandler(BaseHandler, DoubanMixin):
    @web.asynchronous
    def get(self):
        if self.cache.get('douban'):
            return self._write_html()

        if self.get_argument("oauth_token", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        self.authorize_redirect(host + '/douban')
    
    @web.asynchronous
    def post(self):
        user = self.cache.get('douban')
        if not user:
            return self.authorize_redirect(host + '/douban')

        content = self.get_argument('content')
        self.douban_saying(self.async_callback(self._on_saying),
                access_token=user["access_token"], content=content)

    def _on_auth(self, user):
        if not user:
            raise web.HTTPError(500, "Douban auth failed")
        self.cache.set('douban', user)
        self._write_html()

    def _on_saying(self, xml):
        if not xml:
            raise tornado.web.HTTPError(500, 'Douban saying failed')
        self.write(xml)
        self.finish()

    def _write_html(self):
        html = '''
        <form method="post">
        <textarea name="content"></textarea><input type="submit" />
        </form>
        '''
        self.write(html)
        self.finish()


class RenrenHandler(BaseHandler, RenrenGraphMixin):
    @web.asynchronous
    @gen.engine
    def get(self):
        renren = self.cache.get('renren')
        if renren:
            self.write(renren)
            self.finish()
            return

        self.get_authenticated_user(
            redirect_uri=host+'/renren',
            callback=(yield gen.Callback('RenrenHandler.get')))
        user = yield gen.Wait('RenrenHandler.get')
        if not user:
            raise web.HTTPError(500, "Renren auth failed")
        self.cache.set('renren', user)
        self.write(user)
        self.finish()


class WeiboHandler(BaseHandler, WeiboMixin):
    @tornado.web.asynchronous
    def get(self):
        if self.get_argument("code", False):
            self.get_authenticated_user(
                redirect_uri=host + '/weibo',
                client_id=self.settings["weibo_client_id"],
                client_secret=self.settings["weibo_client_secret"],
                code=self.get_argument("code"),
                callback=self.async_callback(self._on_login))
            return
        self.authorize_redirect(redirect_uri=host + '/weibo',
                                client_id=self.settings["weibo_client_id"],
                                extra_params={"response_type": "code"})

    def _on_login(self, user):
        for k, v in user.iteritems():
            self.write("%s : %s<br/>" % (k, v))
        self.finish()


class Application(web.Application):
    def __init__(self):
        handlers = [
            ('/douban', DoubanHandler),
            ('/renren', RenrenHandler),
            ('/weibo', WeiboHandler),
        ]
        settings = dict(
            debug = True,
            autoescape = None,
            cookie_secret = 'secret',
            xsrf_cookies = False,

            douban_consumer_key = '',
            douban_consumer_secret = '',
            renren_client_id = 'fee11992a4ac4caabfca7800d233f814',
            renren_client_secret = 'a617e78710454b12aab68576382e8e14',
            weibo_client_id = '',
            weibo_client_secret = '',
        )
        web.Application.__init__(self, handlers, **settings)
        Application.cache = InstanceCache()


def run_server():
    tornado.options.parse_command_line()
    server = HTTPServer(Application(), xheaders=True)
    server.bind(8000)
    server.start(1)
    IOLoop.instance().start()

if __name__ == "__main__":
    run_server()

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-

import re
import tornado.locale
from tornado.escape import to_unicode
from wtforms import Form as wtForm

class Form(wtForm):
    """
    Using this Form instead of wtforms.Form

    Example::

        class SigninForm(Form):
            email = EmailField('email')
            password = PasswordField('password')

        class SigninHandler(RequestHandler):
            def get(self):
                form = SigninForm(self.request.arguments, locale_code=self.locale.code)

    """
    def __init__(self, formdata=None, obj=None, prefix='', locale_code='en_US', **kwargs):
        self._locale_code = locale_code
        super(Form, self).__init__(formdata, obj, prefix, **kwargs)

    def process(self, formdata=None, obj=None, **kwargs):
        if formdata is not None and not hasattr(formdata, 'getlist'):
            formdata = TornadoArgumentsWrapper(formdata)
        super(Form, self).process(formdata, obj, **kwargs)

    def _get_translations(self):
        if not hasattr(self, '_locale_code'):
            self._locale_code = 'en_US'
        return TornadoLocaleWrapper(self._locale_code)


class TornadoArgumentsWrapper(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError:
            raise AttributeError

    def getlist(self, key):
        try:
            values = []
            for v in self[key]:
                v = to_unicode(v)
                if isinstance(v, unicode):
                    v = re.sub(r"[\x00-\x08\x0e-\x1f]", " ", v)
                values.append(v)
            return values
        except KeyError:
            raise AttributeError


class TornadoLocaleWrapper(object):
    def __init__(self, code):
        self.locale = tornado.locale.get(code)

    def gettext(self, message):
        return self.locale.translate(message)

    def ngettext(self, message, plural_message, count):
        return self.locale.translate(message, plural_message, count)

########NEW FILE########
__FILENAME__ = mail
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import logging
import smtplib
from email.MIMEText import MIMEText
from email.utils import formatdate, parseaddr
from tornado.escape import utf8

from tornado.options import options
SMTP_USER = options.smtp_user
SMTP_PASSWORD = options.smtp_password
SMTP_HOST = options.smtp_host
SMTP_DURATION = int(options.smtp_duration)

_session = None

def send_mail(user, subject, body, **kwargs):
    """
    class MailHandler(BaseHandler):
        def post(self):
            #do something
            with tornado.stack_context.NullContext():
                ioloop = tornado.ioloop.IOLoop.instance()
                ioloop.add_callback(
                    self.async_callback(send_mail, user, subject, body, **kwargs)
                )
                # this will not block your current instance
            #do something else
            self.render(template)
    """
    message = Message(user, subject, body, **kwargs)
    msg = message.as_msg()
    msg['From'] = SMTP_USER

    fr = parseaddr(SMTP_USER)[1]

    global _session
    if _session is None:
        _session = _SMTPSession(
            SMTP_HOST, fr, SMTP_PASSWORD, SMTP_DURATION
        )

    _session.send_mail(fr, message.email, msg.as_string())

class Message(object):
    def __init__(self, user, subject, body, **kwargs):
        self.user = user # lepture <sopheryoung@gmail.com>
        self.name, self.email = parseaddr(user)
        self.subject = subject
        self.body = body
        self.subtype = kwargs.pop('subtype', 'plain')
        self.date = kwargs.pop('date', None)

    def as_msg(self):
        msg = MIMEText(utf8(self.body), self.subtype)
        msg.set_charset('utf-8')
        msg['To'] = utf8(self.email)
        msg['Subject'] = utf8(self.subject)
        if self.date:
            msg['Date'] = self.date
        else:
            msg['Date'] = formatedate()
        return msg

class _SMTPSession(object):
    def __init__(self, host, user='', password='', duration=30, ssl=True):
        self.host = host
        self.user = user
        self.password = password
        self.duration = duration
        self.ssl = ssl

        self.renew()

    def send_mail(self, fr, to, message):
        if self.timeout:
            self.renew()

        try:
            self.session.sendmail(fr, to, message)
        except Exception, e:
            err = "Send email from %s to %s failed!\n Exception: %s!" \
                % (fr, to, e)
            logging.error(err)

    @property
    def timeout(self):
        if datetime.utcnow() < self.deadline:
            return False
        else:
            return True

    def renew(self):
        try:
            self.session.quit()
        except Exception:
            pass

        if self.ssl:
            self.session = smtplib.SMTP_SSL(self.host)
        else:
            self.session = smtplib.SMTP(self.host)
        if self.user and self.password:
            self.session.login(self.user, self.password)

        self.deadline = datetime.utcnow() + timedelta(seconds=self.duration * 60)

########NEW FILE########
