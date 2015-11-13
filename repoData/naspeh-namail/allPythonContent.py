__FILENAME__ = app
import json

from jinja2 import Environment, FileSystemLoader
from jinja2.ext import with_
from werkzeug.contrib.securecookie import SecureCookie
from werkzeug.exceptions import HTTPException, abort
from werkzeug.utils import cached_property, redirect
from werkzeug.wrappers import Request as _Request, Response

from . import conf, views, filters


class Request(_Request):
    @cached_property
    def json(self):
        return json.loads(self.data.decode())


def create_app():
    @Request.application
    def app(request):
        env = Env(request)
        try:
            response = env.run()
        except HTTPException as e:
            response = e
        env.session.save_cookie(response)
        return response
    return app


class Env:
    def __init__(self, request):
        self.url_map = views.url_map
        self.request = request
        self.adapter = self.url_map.bind_to_environ(request.environ)

        self.jinja = jinja = Environment(
            loader=FileSystemLoader(conf.theme_dir),
            extensions=[with_],
            lstrip_blocks=True, trim_blocks=True
        )
        jinja.globals.update(url_for=self.url_for, conf=conf, env=self)
        jinja.filters.update(**filters.get_all())

    def run(self):
        endpoint, values = self.adapter.match()
        response = getattr(views, endpoint)(self, **values)
        if isinstance(response, str):
            return self.make_response(response)
        return response

    def render(self, template_name, context):
        t = self.jinja.get_template(template_name)
        context.setdefault('request', self.request)
        return t.render(context)

    def make_response(self, response, **kw):
        kw.setdefault('content_type', 'text/html')
        return Response(response, **kw)

    def url_for(self, endpoint, _external=False, **values):
        return self.adapter.build(endpoint, values, force_external=_external)

    def redirect(self, location, code=302):
        return redirect(location, code)

    def redirect_for(self, endpoint, _code=302, **values):
        return redirect(self.url_for(endpoint, **values), code=_code)

    def abort(self, code, *a, **kw):
        abort(code, *a, **kw)

    @cached_property
    def session(self):
        return SecureCookie.load_cookie(
            self.request, secret_key=conf('cookie_secret').encode()
        )

    def login(self):
        self.session['logined'] = True

    @property
    def is_logined(self):
        return self.session.get('logined')

########NEW FILE########
__FILENAME__ = async_tasks
from .db import session, Task, Email, Label


def sync():
    prev = (
        session.query(Task)
        .filter(Task.name == Task.N_SYNC)
        .filter(Task.is_new)
    )
    if prev.count():
        return
    else:
        session.add(Task(name='sync'))


def mark(name, uids, add_task=False):
    emails = session.query(Email).filter(Email.uid.in_(uids))
    l_inbox = str(Label.get_by_alias(Label.A_INBOX).id)
    l_star = str(Label.get_by_alias(Label.A_STARRED).id)
    l_all = str(Label.get_by_alias(Label.A_ALL).id)
    l_trash = str(Label.get_by_alias(Label.A_TRASH).id)
    if name == 'starred':
        emails.update({
            Email.labels: Email.labels + {l_star: ''},
            Email.flags: Email.flags + {Email.STARRED: ''}
        }, synchronize_session=False)

    elif name == 'unstarred':
        emails.update({
            Email.labels: Email.labels.delete(l_star),
            Email.flags: Email.flags.delete(Email.STARRED)
        }, synchronize_session=False)

    elif name == 'unread':
        emails.update({
            Email.flags: Email.flags.delete(Email.SEEN)
        }, synchronize_session=False)

    elif name == 'read':
        emails.update({
            Email.flags: Email.flags + {Email.SEEN: ''}
        }, synchronize_session=False)

    elif name == 'inboxed':
        emails.update({
            Email.labels: (
                Email.labels.delete(l_trash) + {l_all: '', l_inbox: ''}
            )
        }, synchronize_session=False)

    elif name == 'archived':
        emails.update({
            Email.labels: (
                Email.labels - {l_inbox: '', l_trash: ''} + {l_all: ''}
            )
        }, synchronize_session=False)

    elif name == 'deleted':
        emails.update({
            Email.labels: {l_trash: ''}
        }, synchronize_session=False)

    else:
        raise ValueError('Unknown name')

    if add_task:
        session.add(Task(name='mark_' + name, uids=uids))

########NEW FILE########
__FILENAME__ = db
import os
import re
import uuid

from psycopg2.extras import register_hstore
from sqlalchemy import (
    create_engine, func, Column, ForeignKey, Index,
    DateTime, String, Integer, BigInteger, SmallInteger,
    Boolean, LargeBinary, Float
)
from sqlalchemy.dialects.postgresql import ARRAY, HSTORE
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import sessionmaker, relationship

from . import conf, filters, base_dir
from .parser import hide_quote
from .imap_utf7 import decode

engine = create_engine(
    'postgresql+psycopg2://{pg_username}:{pg_password}@/{pg_database}'
    .format(**conf.data), echo=False
)
register_hstore(engine.raw_connection(), True)

Base = declarative_base()
Session = sessionmaker(bind=engine, autocommit=True)
session = Session()


def init():
    Base.metadata.create_all(engine)
    with open(os.path.join(base_dir, 'db-init.sql')) as f:
        sql = f.read()
    engine.execute(sql)


def clear():
    with open(os.path.join(base_dir, 'db-clear.sql')) as f:
        sql = f.read()
    engine.execute(sql)
    Base.metadata.drop_all(engine)


class Task(Base):
    __tablename__ = 'tasks'
    N_SYNC = 'sync'

    id = Column(String, primary_key=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    uids = Column(ARRAY(BigInteger), default=[])
    name = Column(String)
    params = Column(HSTORE)
    is_new = Column(Boolean, default=True)
    duration = Column(Float)

    __mapper_args__ = {
        'version_id_col': id,
        'version_id_generator': lambda v: uuid.uuid4().hex
    }


class Label(Base):
    __tablename__ = 'labels'
    NOSELECT = '\\Noselect'
    A_INBOX = 'inbox'
    A_STARRED = 'starred'
    A_SENT = 'sent'
    A_DRAFTS = 'drafts'
    A_ALL = 'all'
    A_SPAM = 'spam'
    A_TRASH = 'trash'
    A_IMPORTANT = 'important'

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    attrs = Column(ARRAY(String))
    delim = Column(String)
    name = Column(String, unique=True)

    alias = Column(String, unique=True)
    hidden = Column(Boolean, default=False)
    index = Column(SmallInteger, default=0)
    weight = Column(SmallInteger, default=0)
    unread = Column(SmallInteger, default=0)
    exists = Column(SmallInteger, default=0)

    @property
    def human_name(self):
        name = self.name.replace('[Gmail]/', '')
        return decode(name)

    @property
    def url(self):
        return '/emails/?label=%s' % self.id

    @classmethod
    def get_all(cls):
        if not hasattr(cls, '_labels'):
            cls._labels = list(
                session.query(Label)
                .order_by(Label.weight.desc())
            )
        return cls._labels

    @classmethod
    def get(cls, func_or_id):
        if isinstance(func_or_id, (int, str)):
            func = lambda l: l.id == int(func_or_id)
        else:
            func = func_or_id

        label = [l for l in cls.get_all() if func(l)]
        if label:
            if len(label) > 1:
                raise ValueError('Must be one row, but %r' % label)
            return label[0]
        return None

    @classmethod
    def get_by_alias(cls, alias):
        return cls.get(lambda l: l.alias == alias)


class EmailBody(Base):
    __tablename__ = 'email_bodies'

    uid = Column(BigInteger, ForeignKey('emails.uid'), primary_key=True)
    body = Column(LargeBinary)


class Email(Base):
    __tablename__ = 'emails'
    __table_args__ = (
        Index('ix_labels', 'labels', postgresql_using='gin'),
        Index('ix_flags', 'flags', postgresql_using='gin'),
    )
    SEEN = '\\Seen'
    STARRED = '\\Flagged'

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    uid = Column(BigInteger, unique=True)
    labels = Column(MutableDict.as_mutable(HSTORE))
    gm_msgid = Column(BigInteger, unique=True)
    gm_thrid = Column(BigInteger, index=True)

    flags = Column(MutableDict.as_mutable(HSTORE))
    internaldate = Column(DateTime)
    size = Column(Integer, index=True)

    date = Column(DateTime)
    subject = Column(String, default='')
    from_ = Column(ARRAY(String), name='from', default=[])
    sender = Column(ARRAY(String), default=[])
    reply_to = Column(ARRAY(String), default=[])
    to = Column(ARRAY(String), default=[])
    cc = Column(ARRAY(String), default=[])
    bcc = Column(ARRAY(String), default=[])
    in_reply_to = Column(String, index=True)
    message_id = Column(String, index=True)

    text = Column(String, default='')
    html = Column(String, default='')
    embedded = Column(MutableDict.as_mutable(HSTORE))
    attachments = Column(ARRAY(String))

    raw = relationship('EmailBody', backref='email', uselist=False)

    @property
    def full_labels(self):
        return [Label.get(l) for l in self.labels]

    @property
    def unread(self):
        return self.SEEN not in self.flags

    @property
    def starred(self):
        return self.STARRED in self.flags

    @property
    def text_line(self):
        text = self.text or self.html or ''
        text = re.sub('<[^>]*?>', '', text)
        return self.human_subject(), text[:200].strip()

    def str_from(self, delimiter=', ', full=False):
        if full:
            filter = lambda v: v
        else:
            filter = 'get_addr_name' if conf('ui_use_names') else 'get_addr'
            filter = getattr(filters, filter)
        return delimiter.join([filter(f) for f in self.from_])

    @property
    def clean_subject(self):
        return re.sub(r'(?i)^(.{2,10}:\ ?)+', '', self.subject or '')

    def human_subject(self, strip=True):
        subj = self.subject or ''
        if strip and subj:
            subj = self.clean_subject

        subj = subj.strip() or '(no subject)'
        return subj

    @property
    def parent(self):
        if not hasattr(self, '_parent'):
            self._parent = None
            if self.in_reply_to:
                p = (
                    session.query(Email)
                    .filter(Email.message_id == self.in_reply_to)
                    .first()
                )
                self._parent = p if p and p.id != self.id else None
        return self._parent

    def human_html(self, class_='email-quote'):
        htm = re.sub(r'(<br[/]?>\s*)$', '', self.html).strip()
        if htm and self.parent:
            parent_html = self.parent.html or self.parent.human_html()
            htm = hide_quote(htm, parent_html, class_)
        return htm

########NEW FILE########
__FILENAME__ = filters
import datetime as dt
from email.utils import getaddresses
from hashlib import md5
from urllib.parse import urlencode

from jinja2 import contextfilter


__all__ = [
    'get_all', 'get_addr', 'get_addr_name', 'get_gravatar',
    'localize_dt', 'humanize_dt', 'format_dt'
]


def get_all():
    return dict((n, globals()[n]) for n in __all__)


def get_addr(addr):
    addr = [addr] if isinstance(addr, str) else addr
    return addr and getaddresses(addr)[0][1]


def get_addr_name(addr):
    return addr and getaddresses([addr])[0][0]


def get_gravatar(addr, size=16, default='identicon'):
    params = urlencode({'s': size, 'd': default})
    gen_hash = lambda e: md5(e.strip().lower().encode()).hexdigest()
    gen_url = lambda h: '//www.gravatar.com/avatar/%s?%s' % (h, params)
    return addr and gen_url(gen_hash(get_addr(addr)))


@contextfilter
def localize_dt(ctx, value):
    tz_offset = ctx.get('env').session.get('tz_offset')
    return value + dt.timedelta(hours=-(tz_offset or 0))


@contextfilter
def humanize_dt(ctx, val):
    val = localize_dt(ctx, val)
    now = localize_dt(ctx, dt.datetime.utcnow())
    if (now - val).total_seconds() < 12 * 60 * 60:
        fmt = '%H:%M'
    elif now.year == val.year:
        fmt = '%b %d'
    else:
        fmt = '%b %d, %Y'
    return val.strftime(fmt)


@contextfilter
def format_dt(ctx, value, fmt='%a, %d %b, %Y at %H:%M'):
    return localize_dt(ctx, value).strftime(fmt)

########NEW FILE########
__FILENAME__ = imap
import imaplib
import re
from collections import OrderedDict
from urllib.parse import urlencode

import requests

from . import log, conf, Timer

OAUTH_URL = 'https://accounts.google.com/o/oauth2/auth'
OAUTH_URL_TOKEN = 'https://accounts.google.com/o/oauth2/token'

re_noesc = r'(?:(?:(?<=[^\\][\\])(?:\\\\)*")|[^"])*'


class AuthError(Exception):
    pass


def auth_url(redirect_uri):
    params = {
        'client_id': conf('google_id'),
        'scope': 'https://mail.google.com/',
        'login_hint': conf('email'),
        'redirect_uri': redirect_uri,
        'access_type': 'offline',
        'response_type': 'code',
        'approval_prompt': 'force',
    }
    return '?'.join([OAUTH_URL, urlencode(params)])


def auth_callback(redirect_uri, code):
    res = requests.post(OAUTH_URL_TOKEN, data={
        'code': code,
        'client_id': conf('google_id'),
        'client_secret': conf('google_secret'),
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code'
    })
    if res.ok:
        conf.update(google_response=res.json())
        return
    raise AuthError('%s: %s' % (res.reason, res.text))


def auth_refresh():
    refresh_token = conf('google_response', {}).get('refresh_token')
    if not refresh_token:
        raise AuthError('refresh_token is empty')

    res = requests.post(OAUTH_URL_TOKEN, data={
        'client_id': conf('google_id'),
        'client_secret': conf('google_secret'),
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token',
    })
    if res.ok:
        new = dict(conf('google_response'), **res.json())
        conf.update(google_response=new)
        return
    raise AuthError('%s: %s' % (res.reason, res.text))


def client():
    if conf('password'):
        def login(im):
            im.login(conf('email'), conf('password'))

    elif conf('google_response', {}).get('access_token'):
        def login(im, retry=False):
            access_token = conf('google_response', {}).get('access_token')
            try:
                im.authenticate('XOAUTH2', lambda x: (
                    'user=%s\1auth=Bearer %s\1\1'
                    % (conf('email'), access_token)
                ))
            except im.error as e:
                if retry:
                    raise AuthError(e)

                auth_refresh()
                login(im, True)
    else:
        raise AuthError('Fill access_token or password in config')

    try:
        client = imaplib.IMAP4_SSL
        im = client('imap.gmail.com')
        # im.debug = 4
        login(im)
    except IOError as e:
        raise AuthError(e)
    return im


def store(im, uids, key, value):
    for uid in uids:
        _, data = im.uid('SEARCH', None, '(X-GM-MSGID %s)' % uid)
        uid_ = data[0].decode().split(' ')[0]
        if not uid_:
            log.warn('%s is not found' % uid)
            continue
        res = im.uid('STORE', uid_, key, value)
        log.info('imap.store(%r, %r): %s', key, value, res)
    return


def list_(im):
    _, data = im.list()

    re_line = r'^[(]([^)]+)[)] "([^"]+)" "(%s)"$' % re_noesc
    lexer_line = re.compile(re_line)
    rows = []
    for line in data:
        matches = lexer_line.match(line.decode())
        row = matches.groups()
        row = tuple(row[0].split()), row[1], row[2]
        rows.append(row)
    return rows


def status(im, name, readonly=True):
    name = '"%s"' % name
    im.select(name, readonly=readonly)

    uid_next = 'UIDNEXT'
    _, data = im.status(name, '(%s)' % uid_next)
    lexer_uid = re.compile(r'[(]%s (\d+)[)]' % uid_next)
    matches = lexer_uid.search(data[0].decode())
    uid = int(matches.groups()[0])
    return uid


def search(im, name):
    uid_next = status(im, name)
    uids, step = [], conf('imap_batch_size')
    for i in range(1, uid_next, step):
        _, data = im.uid('SEARCH', None, '(UID %d:%d)' % (i, i + step - 1))
        if data[0]:
            uids += data[0].decode().split(' ')
    return uids


def fetch(im, uids, query, label='some updates', quiet=False):
    '''Fetch data from IMAP server

    Args:
        im: IMAP instance
        uids: a sequence of UID, it uses BATCH_SIZE for spliting to steps
              or sequence of (UID, BODY.SIZE), it uses BODY_MAXSIZE
        query: fetch query

    Kargs:
        label: label for logging
        quiet: without info logging logging

    Return:
        generator of batch data
    '''
    if not uids:
        return

    batch_size = conf('imap_batch_size')
    if isinstance(uids[0], (tuple, list)):
        step_size, group_size = 0, conf('imap_body_maxsize')
        step_uids, group_uids = [], []
        for uid, size in uids:
            if step_uids and step_size + size > group_size:
                group_uids.append(step_uids)
                step_uids, step_size = [], 0
            else:
                step_uids.append(uid)
                step_size += size
        if step_uids:
            group_uids.append(step_uids)
        steps = group_uids
    else:
        steps = range(0, len(uids), batch_size)
        steps = [uids[i: i + batch_size] for i in steps]

    log_ = (lambda *a, **kw: None) if quiet else log.info
    log_('  * Fetch (%d) %d ones with %s...', len(steps), len(uids), query)

    timer = Timer()
    for num, uids_ in enumerate(steps, 1):
        if not uids_:
            continue
        data_ = _fetch(im, uids_, query)
        log_('  - (%d) %d ones for %.2fs', num, len(uids_), timer.time())
        yield data_
        log_('  - %s for %.2fs', label, timer.time())


def fetch_all(*args, **kwargs):
    data = OrderedDict()
    for data_ in fetch(*args, **kwargs):
        data.update(data_)
    return data


def _fetch(im, ids, query):
    if not isinstance(query, str):
        keys = list(query)
        query = ' '.join(query)
    else:
        keys = query.split()

    status, data_ = im.uid('fetch', ','.join(ids), '(%s)' % query)

    data = iter(data_)
    if 'UID' not in keys:
        keys.append('UID')

    re_keys = r'|'.join([re.escape(k) for k in keys])
    re_list = r'("(%s)"|[^ )"]+)' % re_noesc
    lexer_list = re.compile(re_list)
    lexer_line = re.compile(
        r'(%s) ((\d+)|({\d+})|"([^"]+)"|([(]( ?%s ?)*[)]))'
        % (re_keys, re_list)
    )

    def parse(item, row):
        if isinstance(item, tuple):
            line = item[0]
        else:
            line = item
        matches = lexer_line.findall(line.decode())
        if matches:
            for match in matches:
                key, value = match[0:2]
                if match[2]:
                    row[key] = int(value)
                elif match[3]:
                    row[key] = item[1]
                    row = parse(next(data), row)
                elif match[4]:
                    row[key] = value
                elif match[5]:
                    unesc = lambda v: re.sub(r'\\(.)', r'\1', v)
                    value_ = value[1:-1]
                    value_ = lexer_list.findall(value_)
                    value_ = [unesc(v[1]) if v[1] else v[0] for v in value_]
                    row[key] = value_
        return row

    rows = OrderedDict()
    for i in range(len(ids)):
        row = parse(next(data), {})
        rows[str(row['UID'])] = row
    return rows

########NEW FILE########
__FILENAME__ = imap_utf7
# Borrowed from http://imapclient.freshfoo.com/

# The contents of this file has been derived code from the Twisted project
# (http://twistedmatrix.com/). The original author is Jp Calderone.

# Twisted project license follows:

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

PRINTABLE = set(range(0x20, 0x26)) | set(range(0x27, 0x7f))


def encode(s):
    """Encode a folder name using IMAP modified UTF-7 encoding.

    Despite the function's name, the output is still a unicode string.
    """
    assert isinstance(s, str)

    r = []
    _in = []

    def extend_result_if_chars_buffered():
        if _in:
            r.extend(['&', modified_utf7(''.join(_in)), '-'])
            del _in[:]

    for c in s:
        if ord(c) in PRINTABLE:
            extend_result_if_chars_buffered()
            r.append(c)
        elif c == '&':
            extend_result_if_chars_buffered()
            r.append('&-')
        else:
            _in.append(c)

    extend_result_if_chars_buffered()

    return ''.join(r)


def decode(s):
    """Decode a folder name from IMAP modified UTF-7 encoding to unicode.

    Despite the function's name, the input may still be a unicode
    string. If the input is bytes, it's first decoded to unicode.
    """
    if isinstance(s, bytes):
        s = s.decode('latin-1')
    assert isinstance(s, str)

    r = []
    _in = []
    for c in s:
        if c == '&' and not _in:
            _in.append('&')
        elif c == '-' and _in:
            if len(_in) == 1:
                r.append('&')
            else:
                r.append(modified_deutf7(''.join(_in[1:])))
            _in = []
        elif _in:
            _in.append(c)
        else:
            r.append(c)
    if _in:
        r.append(modified_deutf7(''.join(_in[1:])))

    return ''.join(r)


def modified_utf7(s):
    # encode to utf-7: '\xff' => b'+AP8-', decode from latin-1 => '+AP8-'
    s_utf7 = s.encode('utf-7').decode('latin-1')
    return s_utf7[1:-1].replace('/', ',')


def modified_deutf7(s):
    s_utf7 = '+' + s.replace(',', '/') + '-'
    # encode to latin-1: '+AP8-' => b'+AP8-', decode from utf-7 => '\xff'
    return s_utf7.encode('latin-1').decode('utf-7')

########NEW FILE########
__FILENAME__ = parser
import datetime as dt
import email
import os
import re
from collections import OrderedDict
from html import escape as html_escape

import chardet
from lxml import html as lhtml
from lxml.html.clean import Cleaner
from werkzeug.utils import secure_filename

from . import log, conf


def decode_str(text, charset=None, msg_id=None):
    charset = charset if charset else 'utf8'
    try:
        part = text.decode(charset)
    except LookupError:
        charset_ = chardet.detect(text)['encoding']
        part = text.decode(charset_, 'ignore')
    except UnicodeDecodeError:
        log.warn('DecodeError(%s) -- %s', charset, msg_id or text[:200])
        part = text.decode(charset, 'ignore')
    return part


def decode_header(text, default='utf-8', msg_id=None):
    if not text:
        return ''

    parts_ = email.header.decode_header(text)
    parts = []
    for text, charset in parts_:
        if isinstance(text, str):
            part = text
        else:
            part = decode_str(text, charset or default, msg_id)
        parts += [part]

    header = ''.join(parts)
    header = re.sub('\s+', ' ', header)
    return header


def decode_addresses(text):
    if not isinstance(text, str):
        text = str(text)
    res = []
    for name, addr in email.utils.getaddresses([text]):
        name, addr = [decode_header(r) for r in [name, addr]]
        if addr:
            res += ['"%s" <%s>' % (name if name else addr.split('@')[0], addr)]
    return res


def decode_date(text):
    tm_array = email.utils.parsedate_tz(text)
    tm = dt.datetime(*tm_array[:6]) - dt.timedelta(seconds=tm_array[-1])
    return tm


def parse_part(part, msg_id, inner=False):
    msg_id = str(msg_id)
    content = OrderedDict([
        ('files', []),
        ('attachments', []),
        ('embedded', {}),
        ('html', '')
    ])

    ctype = part.get_content_type()
    mtype = part.get_content_maintype()
    stype = part.get_content_subtype()
    if part.is_multipart():
        for m in part.get_payload():
            child = parse_part(m, msg_id, inner=True)
            child_html = child.pop('html', '')
            content.setdefault('html', '')
            if stype != 'alternative':
                content['html'] += child_html
            elif child_html:
                content['html'] = child_html
            content['files'] += child.pop('files')
            content.update(child)
    elif mtype == 'multipart':
        text = part.get_payload(decode=True)
        text = decode_str(text, part.get_content_charset(), msg_id)
        content['html'] = text
    elif part.get_filename() or mtype == 'image':
        payload = part.get_payload(decode=True)
        attachment = {
            'maintype': mtype,
            'type': ctype,
            'id': part.get('Content-ID'),
            'filename': decode_header(part.get_filename(), msg_id=msg_id),
            'payload': payload,
            'size': len(payload) if payload else None
        }
        content['files'] += [attachment]
    elif ctype in ['text/html', 'text/plain']:
        text = part.get_payload(decode=True)
        text = decode_str(text, part.get_content_charset(), msg_id)
        if ctype == 'text/plain':
            text = text2html(text)
        content['html'] = text
    elif ctype == 'message/rfc822':
        pass
    else:
        log.warn('UnknownType(%s) -- %s', ctype, msg_id)

    if inner:
        return content

    content.update(attachments=[], embedded={})
    for index, item in enumerate(content['files']):
        if item['payload']:
            name = secure_filename(item['filename'] or item['id'])
            url = '/'.join([secure_filename(msg_id), str(index), name])
            if item['id'] and item['maintype'] == 'image':
                content['embedded'][item['id']] = url
            elif item['filename']:
                content['attachments'] += [url]
            else:
                log.warn('UnknownAttachment(%s)', msg_id)
                continue
            path = os.path.join(conf.attachments_dir, url)
            if not os.path.exists(path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'bw') as f:
                    f.write(item['payload'])

    if content['html']:
        htm = re.sub(r'^\s*<\?xml.*?\?>', '', content['html']).strip()
        if not htm:
            content['html'] = htm
            return content

        cleaner = Cleaner(links=False, safe_attrs_only=False)
        htm = cleaner.clean_html(htm)
        embedded = content['embedded']
        if embedded:
            root = lhtml.fromstring(htm)
            for img in root.findall('.//img'):
                src = img.attrib.get('src')
                if not src or not src.startswith('cid:'):
                    continue
                cid = '<%s>' % img.attrib.get('src')[4:]
                if cid in embedded:
                    img.attrib['src'] = '/attachments/' + embedded[cid]
                else:
                    log.warn('No embedded %s in %s', cid, msg_id)
            htm = lhtml.tostring(root, encoding='utf8').decode()
        content['html'] = htm
        if 'text' not in content or not content['text']:
            content['text'] = lhtml.fromstring(htm).text_content()
    return content


key_map = {
    'date': ('date', decode_date),
    'subject': ('subject', decode_header),
    'from': ('from', decode_addresses),
    'sender': ('sender', decode_addresses),
    'reply-to': ('reply_to', decode_addresses),
    'to': ('to', decode_addresses),
    'cc': ('cc', decode_addresses),
    'bcc': ('bcc', decode_addresses),
    'in-reply-to': ('in_reply_to', str),
    'message-id': ('message_id', str)
}


def parse(text, msg_id=None):
    msg = email.message_from_bytes(text)

    data = {}
    for key in key_map:
        field, decode = key_map[key]
        value = msg.get(key)
        data[field] = decode(value) if value else None

    data.update(parse_part(msg, msg_id or data['message_id']))
    return data


link_regexes = [
    (
        r'(https?://|www\.)[a-z0-9._-]+'
        r'(?:/[/\-_.,a-z0-9%&?;=~#]*)?'
        r'(?:\([/\-_.,a-z0-9%&?;=~#]*\))?'
    ),
    r'mailto:([a-z0-9._-]+@[a-z0-9_._]+[a-z])',
]
link_re = re.compile('(?i)(%s)' % '|'.join(link_regexes))


def text2html(txt):
    txt = txt.strip()
    if not txt:
        return ''

    def fill_link(match):
        return '<a href="{0}" target_="_blank">{0}</a>'.format(match.group())

    htm = html_escape(txt)
    htm = link_re.sub(fill_link, htm)
    htm = '<pre>%s</pre>' % htm
    return htm


def t2h_repl(match):
    groups = match.groupdict()
    blockquote = groups.get('blockquote')
    if blockquote is not None:
        inner = re.sub(r'(?m)^ *> ?', '', blockquote)
        inner = text2html(inner)
        return '<blockquote>%s</blockquote>' % inner
    elif groups.get('p') is not None:
        inner = groups.get('p').strip()
        inner = text2html(inner)
        return '<p>%s</p>' % inner
    elif groups.get('br') is not None:
        return '<br/>'
    else:
        raise ValueError(groups)


def hide_quote(mail1, mail0, class_):
    if not mail0 or not mail1:
        return mail1

    def clean(v):
        v = re.sub('[\s]+', '', v.text_content())
        return v.rstrip()

    t0 = clean(lhtml.fromstring(mail0))
    root1 = lhtml.fromstring(mail1)
    for block in root1.xpath('//blockquote'):
        t1 = clean(block)
        if t0 and t1 and (t0.startswith(t1) or t0.endswith(t1) or t0 in t1):
            block.attrib['class'] = class_
            parent = block.getparent()
            switch = lhtml.fromstring('<div class="%s-switch"/>' % class_)
            block.attrib['class'] = class_
            parent.insert(parent.index(block), switch)
            return lhtml.tostring(root1, encoding='utf8').decode()
    return mail1

########NEW FILE########
__FILENAME__ = syncer
from collections import OrderedDict, defaultdict
from itertools import groupby

from sqlalchemy import func

from . import log, Timer, imap, parser, async_tasks, with_lock
from .db import Email, EmailBody, Label, Task, session


@with_lock
def sync_gmail(with_bodies=True):
    im = imap.client()

    opts = {
        'INBOX': (-100, False, Label.A_INBOX),
        '\\Flagged': (-90, True, Label.A_STARRED),
        '\\Sent': (-80, True, Label.A_SENT),
        '\\Drafts': (-70, True, Label.A_DRAFTS),
        '\\All': (-60, True, Label.A_ALL),
        '\\Junk': (-50, True, Label.A_SPAM),
        '\\Trash': (-40, True, Label.A_TRASH),
        '\\Important': (-30, True, Label.A_IMPORTANT)
    }
    session.query(Email).update({Email.updated_at: None})
    folders_ = imap.list_(im)
    for index, value in enumerate(folders_):
        attrs, delim, name = value
        lookup = lambda k: name == k if k == 'INBOX' else k in attrs
        folder = [v for k, v in opts.items() if lookup(k)]
        weight, hidden, alias = (
            folder[0] if folder else (0, Label.NOSELECT in attrs, None)
        )
        label = session.query(Label).filter(Label.name == name).first()
        if not label:
            label = Label(attrs=attrs, delim=delim, name=name)
            session.add(label)

        session.query(Label).filter(Label.name == name).update({
            Label.hidden: hidden,
            Label.index: index,
            Label.weight: weight,
            Label.alias: alias
        })

        if Label.NOSELECT in attrs:
            continue
        fetch_emails(im, label, with_bodies)

    # Cleanup labels
    for label in session.query(Label).filter(Label.updated_at == None):
        updated = (
            session.query(Email.id)
            .filter(Email.labels.has_key(str(label.id)))
            .update(
                {Email.labels: Email.labels.delete(str(label.id))},
                synchronize_session=False
            )
        )
        log.info('Cleanup %s emails from label %s', updated, label.id)
        session.delete(label)

    # Restore state
    tasks = (
        session.query(Task)
        .filter(Task.is_new)
        .filter(Task.name.like('mark_%'))
    )
    if tasks.count():
        log.info('Restore state from %s tasks', tasks.count())
        for task in tasks:
            async_tasks.mark(task.name[5:], task.uids)

        update_labels()

    # Refresh search index
    session.execute('REFRESH MATERIALIZED VIEW emails_search')


def fetch_emails(im, label, with_bodies=True):
    timer = Timer()
    msgids, flags = OrderedDict(), defaultdict(list)
    uids = imap.search(im, label.name)
    data = imap.fetch_all(im, uids, 'X-GM-MSGID FLAGS', quiet=True)
    for k, v in data.items():
        msgid = v['X-GM-MSGID']
        msgids[msgid] = k
        for f in v['FLAGS']:
            flags[f].append(msgid)
    uids_map = {v: k for k, v in msgids.items()}
    flags = OrderedDict(sorted(flags.items()))

    log.info('%s|%d uids|%.2fs', label.name, len(msgids), timer.time())
    if not msgids:
        updated = (
            session.query(Email.id)
            .filter(Email.labels.has_key(str(label.id)))
            .update(
                {Email.labels: Email.labels.delete(str(label.id))},
                synchronize_session=False
            )
        )
        log.info('  * Clean %s label', label.name)
        update_label(label)
        return

    # Fetch properties
    emails = session.query(Email.uid).filter(Email.uid.in_(msgids.keys()))

    # Cleanup flags
    emails.update({Email.flags: {}}, synchronize_session=False)

    msgids_ = sum([[r.uid] for r in emails.all()], [])
    msgids_ = list(set(msgids.keys()) - set(msgids_))
    uids = [v for k, v in msgids.items() if k in msgids_]
    if uids:
        query = OrderedDict([
            ('internaldate', 'INTERNALDATE'),
            ('flags', 'FLAGS'),
            ('size', 'RFC822.SIZE'),
            ('uid', 'X-GM-MSGID'),
            ('gm_msgid', 'X-GM-MSGID'),
            ('gm_thrid', 'X-GM-THRID'),
            ('header', 'BODY[HEADER]'),
        ])
        q = list(query.values())
        for data in imap.fetch(im, uids, q, 'add emails'):
            emails = []
            for row in data.values():
                header = row.pop(query['header'])
                fields = {k: row[v] for k, v in query.items() if v in row}
                fields['labels'] = {str(label.id): ''}
                fields['flags'] = {str(r): '' for r in fields['flags']}
                if not with_bodies:
                    fields.update(parser.parse(header, fields['uid']))
                emails.append(fields)
            session.execute(Email.__table__.insert(), emails)

    # Update labels
    uids = [k for k, v in msgids.items() if k not in msgids_]
    log.info('  * Update labels for %d emails...', len(uids))
    timer, updated = Timer(), 0
    emails = session.query(Email)
    updated += (
        emails.filter(Email.uid.in_(msgids.keys()))
        .filter(~Email.labels.has_key(str(label.id)))
        .update(
            {Email.labels: Email.labels + {str(label.id): ''}},
            synchronize_session=False
        )
    )
    updated += (
        emails.filter(~Email.uid.in_(msgids.keys()))
        .filter(Email.labels.has_key(str(label.id)))
        .update(
            {Email.labels: Email.labels.delete(str(label.id))},
            synchronize_session=False
        )
    )
    log.info('  - %d ones for %.2fs', updated, timer.time())

    # Update flags
    uids = [k for k, v in msgids.items() if k not in msgids_]
    if uids:
        log.info('  * Update flags for %d emails...', len(uids))
        timer, updated = Timer(), 0
        emails = session.query(Email)
        for flag, uids_ in flags.items():
            updated += (
                emails.filter(Email.uid.in_(uids_))
                .update(
                    {Email.flags: Email.flags + {flag: ''}},
                    synchronize_session=False
                )
            )
        log.info('  - %d ones for %.2fs', updated, timer.time())

    update_label(label)
    if not with_bodies:
        return

    # Fetch bodies
    emails = (
        session.query(Email.uid, Email.size)
        .outerjoin(EmailBody)
        .filter(EmailBody.body == None)
        .filter(Email.uid.in_(msgids.keys()))
        .order_by(Email.uid.desc())
    )
    uids = [(msgids[r.uid], r.size) for r in emails.all()]
    if uids:
        for data in imap.fetch(im, uids, 'RFC822', 'update bodies'):
            with session.begin(subtransactions=True):
                for uid, row in data.items():
                    update_email(uids_map[uid], row['RFC822'])


def update_labels():
    for label in session.query(Label):
        update_label(label)


def update_label(label):
    emails = (
        session.query(Email.gm_thrid.distinct())
        .filter(Email.labels.has_key(str(label.id)))
    )
    session.query(Label).filter(Label.id == label.id).update({
        'unread': emails.filter(~Email.flags.has_key(Email.SEEN)).count(),
        'exists': emails.count(),
    })
    log.info('  * Updated label %r', label.name)


def update_email(uid, raw):
    fields = parser.parse(raw, uid)

    fields.pop('files', None)

    session.query(Email).filter(Email.uid == uid)\
        .update(fields, synchronize_session=False)

    updated = session.query(EmailBody).filter(EmailBody.uid == uid)\
        .update({'body': raw}, synchronize_session=False)
    if not updated:
        session.add(EmailBody(uid=uid, body=raw))


def mark_emails(name, uids):
    label_all = Label.get_by_alias(Label.A_ALL)
    store = {
        'starred': ('+FLAGS', Email.STARRED),
        'unstarred': ('-FLAGS', Email.STARRED),
        'read': ('+FLAGS', Email.SEEN),
        'unread': ('-FLAGS', Email.SEEN),
    }
    im = imap.client()
    if name in store:
        key, value = store[name]
        im.select('"%s"' % label_all.name, readonly=False)
        imap.store(im, uids, key, value)
        return

    label_in = Label.get_by_alias(Label.A_INBOX)
    label_trash = Label.get_by_alias(Label.A_TRASH)
    emails = session.query(Email.uid, Email.labels).filter(Email.uid.in_(uids))
    emails = {m.uid: m for m in emails}
    if name == 'inboxed':
        for label in [label_all, label_trash]:
            im.select('"%s"' % label.name, readonly=False)
            for uid in uids:
                _, data = im.uid('SEARCH', None, '(X-GM-MSGID %s)' % uid)
                if not data[0]:
                    continue
                uid_ = data[0].decode().split(' ')[0]
                res = im.uid('COPY', uid_, '"%s"' % label_in.name)
                log.info(
                    'Copy(%s from %s to %s): %s',
                    uid, label.name, label_in.name, res
                )

    elif name == 'archived':
        im.select('"%s"' % label_in.name, readonly=False)
        for uid in uids:
            _, data = im.uid('SEARCH', None, '(X-GM-MSGID %s)' % uid)
            if not data[0]:
                continue
            uid_ = data[0].decode().split(' ')[0]
            res = im.uid('STORE', uid_, '+FLAGS', '\\Deleted')
            log.info('Archive(%s): %s', uid, res)

        im.select('"%s"' % label_trash.name, readonly=False)
        for uid in uids:
            _, data = im.uid('SEARCH', None, '(X-GM-MSGID %s)' % uid)
            if not data[0]:
                continue
            uid_ = data[0].decode().split(' ')[0]
            res = im.uid('COPY', uid_, '"%s"' % label_all.name)
            log.info('Archive(%s): %s', uid, res)

    elif name == 'deleted':
        im.select('"%s"' % label_all.name, readonly=False)
        for uid in uids:
            _, data = im.uid('SEARCH', None, '(X-GM-MSGID %s)' % uid)
            if not data[0]:
                continue
            uid_ = data[0].decode().split(' ')[0]
            res = im.uid('COPY', uid_, '"%s"' % label_trash.name)
            log.info('Delete(%s): %s', uid, res)

    else:
        raise ValueError('Wrong name for "mark" task: %s' % name)


@with_lock
def process_tasks(just_sync=False, clear=False):
    tasks = (
        session.query(Task)
        .with_for_update(nowait=True, of=Task)
        .filter(Task.is_new)
        .order_by(Task.created_at)
    )
    groups = [(k, list(v)) for k, v in groupby(tasks, lambda v: v.name)]
    sync = [(k, v) for k, v in groups if k == Task.N_SYNC]
    other = [(k, v) for k, v in groups if k != Task.N_SYNC]
    if sync:
        with session.begin(subtransactions=True):
            process_task(*sync[0])

    if clear:
        # TODO: It needs for demo, will be removed one day
        tasks = session.query(Task).filter(Task.is_new)
        log.info('Delete %s tasks', tasks.count())
        tasks.delete()
        return

    if just_sync or not other:
        return

    with session.begin(subtransactions=True):
        for task in other:
            process_task(*task)

        sync_gmail()


def process_task(name, group):
    timer = Timer()
    log.info('### Process %s tasks %r...' % (name, [t.id for t in group]))
    if name == Task.N_SYNC:
        sync_gmail()
    elif name.startswith('mark_'):
        uids = set(sum([t.uids for t in group], []))
        mark_emails(name[5:], uids)

    duration = timer.time()
    for task in group:
        task.is_new = False
        task.duration = duration
        session.merge(task)
        log.info('# Task %s is done for %.2f', task.id, duration)


def parse_emails(new=True, limit=500, last=None):
    emails = session.query(Email)
    if new:
        emails = emails.filter(Email.text == None).filter(Email.html == None)

    if not last:
        last = session.query(func.max(Email.updated_at)).scalar()

    emails = emails.filter(Email.updated_at <= last)
    log.info('* Parse %s emails (%s)...', emails.count(), last)
    i = 0
    timer = Timer()
    while emails.count():
        for email in emails.limit(limit):
            update_email(email.uid, email.raw.body)
            i += 1
        log.info('  - parsed %s ones for %.2f', i, timer.time(reset=False))

########NEW FILE########
__FILENAME__ = views
import re
from functools import wraps
from itertools import groupby

import trafaret as t
from sqlalchemy import func
from werkzeug.routing import Map, Rule, BaseConverter, ValidationError

from . import conf, cache, imap, async_tasks
from .db import Email, Label, session

rules = [
    Rule('/auth/', endpoint='auth'),
    Rule('/auth-callback/', endpoint='auth_callback'),
    Rule('/auth-refresh/', endpoint='auth_refresh'),

    Rule('/', endpoint='index'),
    Rule('/init/', endpoint='init'),
    Rule('/compose/', endpoint='compose'),
    Rule('/labels/', endpoint='labels'),
    Rule('/emails/', endpoint='emails'),
    Rule('/gm-thread/<int:id>/', endpoint='gm_thread'),
    Rule('/raw/<email:email>/', endpoint='raw'),
    Rule('/mark/<name>/', methods=['POST'], endpoint='mark'),
    Rule('/sync/', endpoint='sync'),
]


def model_converter(model, pk='id'):
    class Converter(BaseConverter):
        def to_python(self, value):
            row = session.query(model)\
                .filter(getattr(model, pk) == value).first()
            if not row:
                raise ValidationError
            return row

        def to_url(self, value):
            return str(value)
    return Converter

converters = {
    'label': model_converter(Label),
    'email': model_converter(Email, pk='uid')
}
url_map = Map(rules, converters=converters)


def auth(env):
    redirect_uri = env.url_for('auth_callback', _external=True)
    return env.redirect(imap.auth_url(redirect_uri))


def auth_callback(env):
    redirect_uri = env.url_for('auth_callback', _external=True)
    try:
        imap.auth_callback(redirect_uri, env.request.args['code'])
        env.login()
        return env.redirect_for('index')
    except imap.AuthError as e:
        return str(e)


def login_required(func):
    @wraps(func)
    def inner(env, *a, **kw):
        if not conf('ui_is_public') and not env.is_logined:
            return env.redirect_for('auth')
        return func(env, *a, **kw)
    return inner


def cached_view(timeout=conf('cached_view_timeout', 1)):
    def wrapper(func):
        @wraps(func)
        def inner(env, *a, **kw):
            key = env.request.full_path
            value = cache.get(key)
            if value is None:
                value = func(env, *a, **kw)
                cache.set(key, value, timeout=timeout)
            return value
        return inner
    return wrapper


@login_required
def index(env):
    ctx = {
        l.alias: l for l in Label.get_all()
        if l.alias in [Label.A_INBOX, Label.A_STARRED, Label.A_TRASH]
    }
    return env.render('index.tpl', ctx)


@login_required
def init(env):
    env.session['tz_offset'] = env.request.args.get('offset', type=int) or 0
    return 'OK'


@login_required
def compose(env):
    return env.render('compose.tpl')


def get_labels():
    labels = (
        session.query(Label)
        .filter(~Label.attrs.any(Label.NOSELECT))
        .order_by(Label.weight, Label.index)
    )
    return labels


@login_required
@cached_view()
def emails(env):
    label = None
    emails = (
        session.query(Email.gm_thrid)
        .order_by(Email.gm_thrid, Email.date.desc())
    )
    if 'label' in env.request.args:
        label_id = env.request.args['label']
        label = session.query(Label).filter(Label.id == label_id).one()
        emails = emails.filter(Email.labels.has_key(label_id)).all()
    elif 'email' in env.request.args:
        email = env.request.args['email']
        emails = emails.filter(
            func.array_to_string(Email.from_ + Email.to, ',')
            .contains('<%s>' % email)
        ).all()
    elif 'subj' in env.request.args:
        subj = env.request.args['subj']
        subj = re.sub(r'([()\[\]{}_*|+?])', r'\\\1', subj)
        emails = emails.filter(
            Email.subject.op('SIMILAR TO')('(_{2,10}:)*\ ?' + subj)
        ).all()
    elif 'q' in env.request.args and env.request.args['q']:
        query = env.request.args['q']
        query = query.replace(' ', '\ ')
        emails = session.execute(
            '''
            SELECT id, gm_thrid
            FROM emails_search
            WHERE document @@ to_tsquery('simple', :query)
            ORDER BY ts_rank(document, to_tsquery('simple', :query)) DESC
            ''',
            {'query': query}
        ).fetchall()
    else:
        env.abort(404)

    if len(emails):
        threads = list(
            session.query(
                Email.gm_thrid,
                func.count('*').label('count'),
                func.max(Email.uid).label('uid')
            )
            .filter(Email.gm_thrid.in_([m.gm_thrid for m in emails]))
            .group_by(Email.gm_thrid)
        )
        emails = (
            session.query(Email)
            .filter(Email.uid.in_([m.uid for m in threads]))
            .order_by(Email.date.desc())
        ).all()
        counts = {t.gm_thrid: t.count for t in threads}
    else:
        emails, counts = [], {}

    return env.render('emails.tpl', {
        'emails': emails,
        'emails_count': len(emails),
        'counts': counts,
        'label': label,
        'labels': get_labels()
    })


@login_required
@cached_view()
def gm_thread(env, id):
    emails = list(
        session.query(Email)
        .filter(Email.gm_thrid == id)
        .order_by(Email.date)
    )
    few_showed = 2
    groups = []
    if emails:
        groups = groupby(emails[:-1], lambda v: (v.unread or v.starred))
        groups = [(k, list(v)) for k, v in groups]
        if groups:
            # Show title of few last messages
            latest = groups[-1]
            if not latest[0] and len(latest[1]) > few_showed:
                group_latest = (False, latest[1][-few_showed:])
                groups[-1] = (False, latest[1][:-few_showed])
                groups.append(group_latest)
            # Show title of first message
            first = groups[0]
            if not first[0] and len(first[1]) > few_showed:
                group_1st = (False, [first[1][0]])
                groups[0] = (False, first[1][1:])
                groups.insert(0, group_1st)
        # Show last message
        groups += [(True, [emails[-1]])]

    thread = {
        'subject': emails[-1].human_subject(),
        'labels': set(sum([e.full_labels for e in emails], []))
    }
    return env.render('thread.tpl', {
        'thread': thread,
        'groups': groups,
        'few_showed': few_showed,
        'labels': get_labels()
    })


@login_required
def mark(env, name):
    schema = t.Dict({
        t.Key('use_threads', False): t.Bool,
        'ids': t.List(t.Int)
    })
    try:
        data = schema.check(env.request.json)
    except t.DataError as e:
        return env.abort(400, e)
    uids = data['ids']
    if data['use_threads']:
        uids = session.query(Email.uid).filter(Email.gm_thrid.in_(uids))
        uids = [r.uid for r in uids]
    async_tasks.mark(name, uids, add_task=True)
    return 'OK'


@login_required
def sync(env):
    async_tasks.sync()
    return 'OK'


@login_required
def raw(env, email):
    from tests import open_file

    desc = env.request.args.get('desc')
    if env.is_logined and desc:
        name = '%s--%s.txt' % (email.uid, desc)
        with open_file('files_parser', name, mode='bw') as f:
            f.write(email.raw.body)
    return env.make_response(email.raw.body, content_type='text/plain')

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import argparse
import glob
import os
import subprocess

from werkzeug.serving import run_simple
from werkzeug.wsgi import SharedDataMiddleware

from mailur import conf, db, app, syncer, log

sh = lambda cmd: log.info(cmd) or subprocess.call(cmd, shell=True)
ssh = lambda cmd: sh('ssh %s "%s"' % (
    conf('server_host'), cmd.replace('"', '\"').replace('$', '\$')
))


def run(args):
    if not args.only_wsgi and os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        main(['lessc'])

    extra_files = [
        glob.glob(os.path.join(conf.theme_dir, fmask)) +
        glob.glob(os.path.join(conf.theme_dir, '*', fmask))
        for fmask in ['*.less', '*.css', '*.js']
    ]
    extra_files = sum(extra_files, [])

    wsgi_app = SharedDataMiddleware(app.create_app(), {
        '/theme': conf.theme_dir, '/attachments': conf.attachments_dir
    })
    run_simple(
        '0.0.0.0', 5000, wsgi_app,
        use_debugger=True, use_reloader=True,
        extra_files=extra_files
    )


def main(argv=None):
    parser = argparse.ArgumentParser('mail')
    cmds = parser.add_subparsers(help='commands')

    def cmd(name, **kw):
        p = cmds.add_parser(name, **kw)
        p.set_defaults(cmd=name)
        p.arg = lambda *a, **kw: p.add_argument(*a, **kw) and p
        p.exe = lambda f: p.set_defaults(exe=f) and p
        return p

    cmd('sync')\
        .arg('-b', '--with-bodies', action='store_true')\
        .exe(lambda a: (syncer.sync_gmail(a.with_bodies)))

    cmd('tasks')\
        .arg('-s', '--just-sync', action='store_true')\
        .arg('-c', '--clear', action='store_true')\
        .exe(lambda a: syncer.process_tasks(a.just_sync, a.clear))

    cmd('parse')\
        .arg('-n', '--new', action='store_true')\
        .arg('-l', '--limit', type=int, default=500)\
        .arg('-t', '--last')\
        .exe(lambda a: syncer.parse_emails(a.new, a.limit, a.last))

    cmd('db-init').exe(lambda a: db.init())
    cmd('db-clear').exe(lambda a: db.clear() or db.init())

    cmd('test').exe(lambda a: (
        sh('MAILR_CONF=conf_test.json py.test %s' % ' '.join(a))
    ))

    cmd('run')\
        .arg('-w', '--only-wsgi', action='store_true')\
        .exe(run)

    cmd('lessc').exe(lambda a: sh(
        'lessc {0}styles.less {0}styles.css && '
        'autoprefixer {0}styles.css {0}styles.css && '
        'csso {0}styles.css {0}styles.css'.format('mailur/theme/')
    ))

    cmd('deploy', help='deploy to server')\
        .arg('-t', '--target', default='origin/master', help='checkout it')\
        .exe(lambda a: ssh(
            'cd /home/mailr/src'
            '&& git fetch origin' +
            '&& git checkout {}'.format(a.target) +
            '&& touch ../reload'
        ))

    args, extra = parser.parse_known_args(argv)
    if getattr(args, 'cmd', None) == 'test':
        args.exe(extra)
    elif not hasattr(args, 'exe'):
        parser.print_usage()
    else:
        args.exe(args)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit(1)

########NEW FILE########
__FILENAME__ = test_async
from unittest.mock import patch

from sqlalchemy import event

from mailur import syncer, async_tasks
from mailur.db import engine, session, init, clear, Task

trans = None


def setup():
    global trans
    init()
    trans = engine.begin()

    @event.listens_for(session, 'after_transaction_end')
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.begin_nested()


def teardown():
    global trans
    trans.transaction.rollback()
    clear()


def test_sync():
    tasks = session.query(Task).filter(Task.name == Task.N_SYNC)
    assert tasks.count() == 0
    async_tasks.sync()
    assert tasks.count() == 1
    async_tasks.sync()
    assert tasks.count() == 1

    task = tasks.first()
    assert task.is_new

    with patch('mailur.syncer.sync_gmail') as mok:
        syncer.process_tasks()
        assert mok.called

    task = tasks.first()
    assert not task.is_new
    assert task.duration

########NEW FILE########
__FILENAME__ = test_imap
from collections import namedtuple

from pytest import mark

from . import read_file
from mailur import imap, imap_utf7


def gen_response(filename, query):
    import imaplib
    import pickle
    from conf import username, password
    from tests import open_file

    im = imaplib.IMAP4_SSL('imap.gmail.com')
    im.login(username, password)
    im.select('&BEIENQRBBEI-')

    ids = im.uid('search', None, 'all')[1][0].decode().split()
    res = im.uid('fetch', ','.join(ids), '(%s)' % query)
    with open_file(filename, mode='bw') as f:
        f.write(pickle.dumps((ids, res)))


def test_fetch_header_and_other():
    filename = 'files_imap/fetch-header-and-other.pickle'
    query = 'UID X-GM-MSGID FLAGS X-GM-LABELS RFC822.HEADER RFC822.HEADER'
    #gen_response(filename, query)

    ids, data = read_file(filename)

    im = namedtuple('_', 'uid')(lambda *a, **kw: data)
    rows = imap.fetch_all(im, ids, query)
    assert len(ids) == len(rows)
    assert ids == list(str(k) for k in rows.keys())
    for id in ids:
        value = rows[id]
        for key in query.split():
            assert key in value


def test_fetch_body():
    filename = 'files_imap/fetch-header.pickle'
    query = 'RFC822.HEADER INTERNALDATE'
    #gen_response(filename, query)

    ids, data = read_file(filename)

    im = namedtuple('_', 'uid')(lambda *a, **kw: data)
    rows = imap.fetch_all(im, ids, query)
    assert len(ids) == len(rows)
    assert ids == list(str(k) for k in rows.keys())


@mark.parametrize('query, line, expected', [
    ('FLAGS', [b'UID 1 FLAGS (\\Seen)'], {
        '1': {'FLAGS': ['\\Seen'], 'UID': 1}
    }),
    ('FLAGS', [b'UID 1 FLAGS (\\Seen))'], {
        '1': {'FLAGS': ['\\Seen'], 'UID': 1}
    }),
    ('FLAGS', [b'UID 1 FLAGS (\\FLAGS FLAGS))'], {
        '1': {'FLAGS': ['\\FLAGS', 'FLAGS'], 'UID': 1}
    }),
    ('FLAGS', [b'1 (FLAGS ("ABC\\"" UID) UID 1'], {
        '1': {'FLAGS': ['ABC"', 'UID'], 'UID': 1}
    }),
    ('FLAGS', [b'1 (FLAGS ("ABC \\\\\\"" UID) UID 1'], {
        '1': {'FLAGS': ['ABC \\"', 'UID'], 'UID': 1}
    }),
    ('FLAGS', [b'1 (FLAGS ("ABC \\")\\\\" UID) UID 1'], {
        '1': {'FLAGS': ['ABC ")\\', 'UID'], 'UID': 1}
    }),
    ('FLAGS', [b'1 (FLAGS (")ABC)\\"" UID) UID 1'], {
        '1': {'FLAGS': [')ABC)"', 'UID'], 'UID': 1}
    }),
    (
        ['FLAGS', 'BODY[HEADER.FIELDS (TO)]'],
        [(b'FLAGS (AB) UID 1 BODY[HEADER.FIELDS (TO)] {48}', b'1'), b')'],
        {'1': {'FLAGS': ['AB'], 'BODY[HEADER.FIELDS (TO)]': b'1', 'UID': 1}}
    )
])
def test_lexer(query, line, expected):
    im = namedtuple('_', 'uid')(lambda *a, **kw: ('OK', line))
    rows = imap.fetch_all(im, '1', query)
    assert rows == expected


def test_imap_utf7():
    orig, expect = '&BEIENQRBBEI-', 'тест'
    assert imap_utf7.decode(orig) == expect
    assert imap_utf7.encode(expect) == orig


def test_list():
    data = [
        b'(\\HasNoChildren) "/" "-job proposals"',
        b'(\\HasNoChildren) "/" "-social"',
        b'(\\HasNoChildren) "/" "FLAGS \\")\\\\"',
        b'(\\HasNoChildren) "/" "INBOX"',
        b'(\\HasNoChildren) "/" "UID"',
        b'(\\Noselect \\HasChildren) "/" "[Gmail]"',
        b'(\\HasNoChildren \\All) "/" "[Gmail]/All Mail"',
        b'(\\HasNoChildren \\Drafts) "/" "[Gmail]/Drafts"',
        b'(\\HasNoChildren \\Important) "/" "[Gmail]/Important"',
        b'(\\HasNoChildren \\Sent) "/" "[Gmail]/Sent Mail"',
        b'(\\HasNoChildren \\Junk) "/" "[Gmail]/Spam"',
        b'(\\HasNoChildren \\Flagged) "/" "[Gmail]/Starred"',
        b'(\\HasNoChildren \\Trash) "/" "[Gmail]/Trash"',
        b'(\\HasNoChildren) "/" "work: 42cc"',
        b'(\\HasNoChildren) "/" "work: odesk"',
        b'(\\HasNoChildren) "/" "work: odeskps"',
        b'(\\HasNoChildren) "/" "&BEIENQRBBEI-"'
    ]

    im = namedtuple('_', 'list')(lambda *a, **kw: ('OK', data))
    rows = imap.list_(im)
    assert rows[0] == (('\\HasNoChildren',), '/', '-job proposals')
    assert rows[3] == (('\\HasNoChildren',), '/', 'INBOX')
    assert rows[5] == (('\\Noselect', '\\HasChildren'), '/', '[Gmail]')
    assert rows[-1] == (('\\HasNoChildren',), '/', '&BEIENQRBBEI-')

########NEW FILE########
__FILENAME__ = test_parser
from pytest import mark

from . import read_file
from mailur import parser

emails = read_file('files_parser', 'expected.json').items()


@mark.parametrize('path, expected', emails)
def test_emails(path, expected):
    raw = read_file('files_parser', path)
    result = parser.parse(raw, 'test')
    assert expected['subject'] == result['subject']

    for type_ in ['html']:
        if expected.get(type_):
            assert type_ in result
            assert expected[type_] in result[type_]
            assert result[type_].count(expected[type_]) == 1

    if expected.get('attachments'):
        assert 'attachments' in result
        assert len(expected['attachments']) == len(result['attachments'])
        assert expected['attachments'] == result['attachments']

########NEW FILE########
__FILENAME__ = test_quote
from lxml import etree
from pytest import mark

from . import open_file
from mailur.parser import hide_quote


@mark.parametrize('id', [1457489417718057053, 1456781505677497494])
def test_thread_with_quotes(id):
    with open_file('files_quote', '%s.html' % id) as f:
        thread = etree.fromstring(f.read().decode())

    mails = []
    for mail in thread.xpath('mail'):
        subj_ = mail.xpath('subject')[0].text
        text_ = mail.xpath('text')[0].text
        html_ = mail.xpath('html')[0].text
        mails.append({'subj': subj_, 'html': html_, 'text': text_})

    class_ = 'email_quote'
    for i in range(1, len(mails)):
        res = hide_quote(mails[i]['html'], mails[i - 1]['html'], class_)
        assert 'class="%s"' % class_ in res

########NEW FILE########
__FILENAME__ = wsgi
from mailur import app

application = app.create_app()

########NEW FILE########
