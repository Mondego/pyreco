__FILENAME__ = blogconfig
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

# 用于 cookie 加密，请换一个随机的，足够长，足够复杂的字符串
# !!! 不要使用现在这个
COOKIE_SECRET = "11oETzKXQAGaYdkL5gEmGeJJ-(g7EQnp2XdTP1o/Vo="

# 数据库文件路径，默认是和配置文件同目录
# eg. DATABASE = "/home/myblog/mydb.db"
DATABASE = os.path.join(os.path.dirname(__file__), "newblog.db")

# 你的博客名
SITE_NAME = u"I'm SErHo"

# Picky 目录路径，默认和配置文件同目录
PICKY_DIR = os.path.join(os.path.dirname(__file__), "picky")


# 如果在生成环境下，可以关闭 Debug 选项，这样将缓存编译好的模板，加快模板渲染速度
# 不过修改模板或代码后，需要重新启动博客，这样才有效果
#DEBUG = True
DEBUG = False

del os

########NEW FILE########
__FILENAME__ = blog
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from tornado.web import removeslash
from tornado.log import access_log
from .libs.handler import BaseHandler
from .libs.crypto import PasswordCrypto, get_random_string
from .libs.models import PostMixin, TagMixin
from .libs.markdown import RenderMarkdownPost
from .libs.utils import authenticated, signer_code
from .libs.utils import unsigner_code, archives_list
from blogconfig import PICKY_DIR


class EntryHandler(BaseHandler, PostMixin):

    @removeslash
    def get(self, slug):
        post = self.get_post_by_slug(slug.lower())
        if not post:
            self.abort(404)
        tags = [tag.strip() for tag in post.tags.split(",")]
        next_prev = self.get_next_prev_post(post.published)
        signer = signer_code(str(post.id))
        self.render("post.html", post=post, tags=tags, next_prev=next_prev,
                                    signer=signer)


class TagsHandler(BaseHandler, PostMixin):

    @removeslash
    def get(self, name):
        posts = self.get_posts_by_tag(name)
        if not posts:
            self.abort(404)
        count = len(posts)
        self.render("archive.html", posts=posts, type="tag", name=name,
            count=count)


class CategoryHandler(BaseHandler, PostMixin):

    @removeslash
    def get(self, category):
        posts = self.get_posts_by_category(category)
        if not posts:
            self.abort(404)
        count = len(posts)
        self.render("archive.html", posts=posts, type="category",
                                    name=category, count=count)


class FeedHandler(BaseHandler, PostMixin):

    def get(self):
        posts = self.get_count_posts(10)
        self.set_header("Content-Type", "application/atom+xml")
        self.render("feed.xml", posts=posts)


class SearchHandler(BaseHandler):

    def get(self):
        self.render("search.html")


class HomeHandler(BaseHandler, PostMixin):

    def get(self):
        if self._context.is_mobile:
            posts = self.get_count_posts(5)
            self.render("index.html", posts=posts)
        else:
            posts = self.get_count_posts(8)
            self.render("home.html", posts=posts)
            

class ArchiveHandler(BaseHandler, PostMixin, TagMixin):

    def get(self):
        posts = self.get_count_posts()
        count = len(posts)
        self.render('archives.html', posts=posts, count=count,
            archives_list=archives_list)


class TagListHandler(BaseHandler, TagMixin):

    def get(self):
        tags = self.get_all_tag_count()
        count = len(tags)
        self.render('taglist.html', tags=tags, count=count)
      

class NewPostHandler(BaseHandler, PostMixin):

    @authenticated
    def get(self):
        self.render("admin/post.html")

    @authenticated
    def post(self):
        markdown = self.get_argument("markdown", None)
        comment = self.get_argument("comment", 1)
        if not markdown:
            self.redirect("/post/new")

        render = RenderMarkdownPost(markdown)
        post = render.get_render_post()
        if comment == '0':
            comment = 0
        post.update({"comment": comment})
        self.create_new_post(**post)
        self.redirect("/%s" % post["slug"])
        return


class UpdatePostHandler(BaseHandler, PostMixin):

    @authenticated
    def get(self, id):
        post = self.get_post_by_id(int(id))
        if not post:
            self.redirect('/')
        self.render("admin/update.html", id=id)

    @authenticated
    def post(self, id):
        markdown = self.get_argument("markdown", None)
        comment = self.get_argument("comment", 1)
        print comment
        if not markdown:
            self.redirect("/post/update/%s" % str(id))

        render = RenderMarkdownPost(markdown)
        post = render.get_render_post()

        if comment == '0':
            comment = 0

        post.update({"comment": comment})
        self.update_post_by_id(int(id), **post)
        self.redirect("/%s" % post["slug"])
        return


class DeletePostHandler(BaseHandler, PostMixin):

    @authenticated
    def get(self, id):
        signer = self.get_argument("check", None)
        print signer
        if unsigner_code(signer) == id:
            self.delete_post_by_id(int(id))
        self.redirect("/")
        return


class PickyHandler(BaseHandler):

    def get(self, slug):
        mdfile = PICKY_DIR + "/" + str(slug) + ".md"
        try:
            md = open(mdfile)
        except IOError:
            self.abort(404)
        markdown = md.read()
        md.close()
        render = RenderMarkdownPost(markdown)
        post = render.get_render_post()
        self.render("picky.html", post=post, slug=slug)


class PickyDownHandler(BaseHandler):

    def get(self, slug):
        mdfile = PICKY_DIR + "/" + str(slug)
        try:
            md = open(mdfile)
        except IOError:
            self.abort(404)
        markdown = md.read()
        md.close()
        self.set_header("Content-Type", "text/x-markdown")
        self.write(markdown)


class NewPickyHandler(BaseHandler):

    @authenticated
    def get(self):
        self.render("admin/picky.html")

    @authenticated
    def post(self):
        try:
            files = self.request.files['picky'][0]
        except KeyError:
            self.redirect('/post/picky')
            return
        
        if files['body'] and (files['filename'].split(".").pop().lower()=='md'):
            f = open(PICKY_DIR + '/' + files['filename'], 'w')
            f.write(files['body'])
            f.close()
            slug = files['filename'].split('.')[0]
            self.redirect("/picky/%s" % slug)
        self.redirect('/post/picky')


class SigninHandler(BaseHandler):

    def get(self):
        if self.current_user:
            self.redirect(self.get_argument("next", "/"))
            return
        self.render("admin/signin.html")

    def post(self):
        email = self.get_argument("email", None)
        password = self.get_argument("password", None)
        if (not email) or (not password):
            self.redirect("/auth/signin")
            return
        pattern = r'^.+@[^.].*\.[a-z]{2,10}$'
        if isinstance(pattern, basestring):
            pattern = re.compile(pattern, flags=0)

        if not pattern.match(email):
            self.redirect("/auth/signin")
            return

        user = self.get_user_by_email(email)
        if not user:
            access_log.error("Login Error for email: %s" % email)
            self.redirect("/")
            return
        encryped_pass = user.password
        if PasswordCrypto.authenticate(password, encryped_pass):
            token = user.salt + "/" + str(user.id)
            self.set_secure_cookie("token", str(token))
            self.redirect(self.get_argument("next", "/post/new"))
            return
        else:
            access_log.error("Login Error for password: %s!" % password)
            self.redirect("/")
        return


class SignoutHandler(BaseHandler):

    def get(self):
        user = self.current_user
        if not user:
            self.redirect("/")
        salt = get_random_string()
        self.update_user_salt(user.id, salt)
        self.clear_cookie("token")
        self.redirect("/")


class PageNotFound(BaseHandler):
    def get(self):
        self.abort(404)


handlers = [('/', HomeHandler),
            ('/([a-zA-Z0-9-]+)/*', EntryHandler),
            ('/picky/([a-zA-Z0-9-]+)/*', PickyHandler),
            ('/picky/([a-zA-Z0-9-]+.md)', PickyDownHandler),
            ('/tag/([^/]+)/*', TagsHandler),
            ('/category/([^/]+)/*', CategoryHandler),
            ('/post/new', NewPostHandler),
            ('/post/delete/([0-9]+)', DeletePostHandler),
            ('/post/update/([0-9]+)', UpdatePostHandler),
            ('/post/picky', NewPickyHandler),
            ('/auth/signin', SigninHandler),
            ('/auth/signout', SignoutHandler),
            ('/blog/feed', FeedHandler),
            ('/search/all', SearchHandler),
            ('/blog/all', ArchiveHandler),
            ('/blog/tags', TagListHandler),
            (r'.*', PageNotFound),
]

########NEW FILE########
__FILENAME__ = crypto
"""
Django's standard crypto functions and utilities.
"""

import struct
import hashlib
import binascii
import operator


trans_5c = "".join([chr(x ^ 0x5C) for x in xrange(256)])
trans_36 = "".join([chr(x ^ 0x36) for x in xrange(256)])


def get_random_string(length=12,
                      allowed_chars='abcdefghijklmnopqrstuvwxyz'
                                    'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'):
    """
    Returns a random string of length characters from the set of a-z, A-Z, 0-9
    for use as a salt.

    The default length of 12 with the a-z, A-Z, 0-9 character set returns
    a 71-bit salt. log_2((26+26+10)^12) =~ 71 bits
    """
    import random
    try:
        random = random.SystemRandom()
    except NotImplementedError:
        pass
    return ''.join([random.choice(allowed_chars) for i in range(length)])


def constant_time_compare(val1, val2):
    """
    Returns True if the two strings are equal, False otherwise.

    The time taken is independent of the number of characters that match.
    """
    if len(val1) != len(val2):
        return False
    result = 0
    for x, y in zip(val1, val2):
        result |= ord(x) ^ ord(y)
    return result == 0


def bin_to_long(x):
    """
    Convert a binary string into a long integer

    This is a clever optimization for fast xor vector math
    """
    return long(x.encode('hex'), 16)


def long_to_bin(x):
    """
    Convert a long integer into a binary string
    """
    hex = "%x" % (x)
    if len(hex) % 2 == 1:
        hex = '0' + hex
    return binascii.unhexlify(hex)


def fast_hmac(key, msg, digest):
    """
    A trimmed down version of Python's HMAC implementation
    """
    dig1, dig2 = digest(), digest()
    if len(key) > dig1.block_size:
        key = digest(key).digest()
    key += chr(0) * (dig1.block_size - len(key))
    dig1.update(key.translate(trans_36))
    dig1.update(msg)
    dig2.update(key.translate(trans_5c))
    dig2.update(dig1.digest())
    return dig2


def pbkdf2(password, salt, iterations, dklen=0, digest=None):
    """
    Implements PBKDF2 as defined in RFC 2898, section 5.2

    HMAC+SHA256 is used as the default pseudo random function.

    Right now 10,000 iterations is the recommended default which takes
    100ms on a 2.2Ghz Core 2 Duo.  This is probably the bare minimum
    for security given 1000 iterations was recommended in 2001. This
    code is very well optimized for CPython and is only four times
    slower than openssl's implementation.
    """
    assert iterations > 0
    if not digest:
        digest = hashlib.sha256
    hlen = digest().digest_size
    if not dklen:
        dklen = hlen
    if dklen > (2 ** 32 - 1) * hlen:
        raise OverflowError('dklen too big')
    l = -(-dklen // hlen)
    r = dklen - (l - 1) * hlen

    def F(i):
        def U():
            u = salt + struct.pack('>I', i)
            for j in xrange(int(iterations)):
                u = fast_hmac(password, u, digest).digest()
                yield bin_to_long(u)
        return long_to_bin(reduce(operator.xor, U()))

    T = [F(x) for x in range(1, l + 1)]
    return ''.join(T[:-1]) + T[-1][:r]


class PasswordCrypto(object):

    ALGORITHM = "pbkdf2_sha256"
    ITERATIONS = 5000
    DIGEST = hashlib.sha256

    @classmethod
    def get_encrypted(cls, password, salt=None, iterations=None):
        if not password:
            return None
        if (not salt) or ('$' in salt):
            salt = get_random_string()
        if not iterations:
            iterations = cls.ITERATIONS
        password = str(password)
        encrypted = pbkdf2(password, salt, iterations, digest=cls.DIGEST)
        encrypted = encrypted.encode('base64').strip()
        return "%s$%d$%s$%s" % (cls.ALGORITHM, cls.ITERATIONS, salt, encrypted)
    
    @classmethod
    def authenticate(cls, password, encrypted):
        algorithm, iterations, salt, encrypt = encrypted.split('$', 3)
        if algorithm != cls.ALGORITHM:
            return False
        encrypted_new = cls.get_encrypted(password, salt, int(iterations))
        return constant_time_compare(encrypted, encrypted_new)

########NEW FILE########
__FILENAME__ = handler
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    扩展 `tornado.web.BaseHandler` 以方便添加模板 filter 和 全局变量，
    并对默认的错误页进行修改。
"""

import traceback
import tornado.web

from .utils import ObjectDict
from .utils import get_home_time, format_time, get_show_time
from .utils import is_mobile, strip_tags
from .models import UserMixin
from blogconfig import SITE_NAME


class BaseHandler(tornado.web.RequestHandler, UserMixin):

    @property
    def db(self):
        return self.application.db

    def prepare(self):
        self._prepare_context()
        self._prepare_filters()

    def render_string(self, template_name, **kwargs):
        """
        重写 `render_string` 方法，以便加入自定义 filter 和自定义模板全局变量
        """
        kwargs.update(self._filters)
        assert "context" not in kwargs, "context is a reserved keyword."
        kwargs["context"] = self._context
        return super(BaseHandler, self).render_string(template_name, **kwargs)

    def get_current_user(self):
        token = self.get_secure_cookie("token")
        if not token:
            return None
        salt = token.split("/")[0]
        user_id = token.split("/")[1]
        if not user_id:
            return None
        user = self.get_user_by_id(int(user_id))
        if user.salt != salt.strip():
            return None
        return user

    def get_error_html(self, status_code, **kwargs):
        """
        请求错误处理：
            1. 404 错误：将使用 `templates/e404.html` 作为 404 页面
            2. 其它错误，如果在 `app.py` 中设置 `debug = True` 将会显示错误信息，否则
               输出简单的提示。
        """
        if status_code == 404:
            return self.render_string("e404.html")
        else:
            try:
                exception = "%s\n\n%s" % (kwargs["exception"],
                    traceback.format_exc())
                if self.settings.get("debug"):
                    self.set_header('Content-Type', 'text/plain')
                    for line in exception:
                        self.write(line)
                else:
                    self.write("oOps...! I made ​​a mistake... ")
            except Exception:
                return super(BaseHandler, self).get_error_html(status_code,
                    **kwargs)

    def _prepare_context(self):
        """
        将自定义变量传入模板，作为全局变量，引用时使用 `context.var` 的形式
        """
        self._context = ObjectDict()
        self._context.sitename = SITE_NAME
        self._context.is_mobile = is_mobile(self.request.headers['User-Agent'])

    def _prepare_filters(self):
        """
        将自定义 filter 传入模板
        """
        self._filters = ObjectDict()
        self._filters.get_home_time = get_home_time
        self._filters.get_show_time = get_show_time
        self._filters.time = format_time
        self._filters.strip_tags = strip_tags

    def abort(self, code):
        raise tornado.web.HTTPError(code)

########NEW FILE########
__FILENAME__ = markdown
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from StringIO import StringIO
import misaka as m

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

from tornado.escape import to_unicode
from tornado.escape import xhtml_escape


class AkioRender(m.HtmlRenderer, m.SmartyPants):

    def block_code(self, text, lang):
        if lang:
            lexer = get_lexer_by_name(lang, stripall=True)
        else:
            return '<pre><code>%s</code></pre>' % xhtml_escape(text.strip())

        formatter = HtmlFormatter(
            noclasses=False,
            linenos=True,
        )

        return '<div class="highlight-pre">%s</div>' % \
                        highlight(text, lexer, formatter)

    def autolink(self, link, is_email):
        if is_email:
            mailto = "".join(['&#%d;' % ord(letter) for letter in "mailto:"])
            email = "".join(['&#%d;' % ord(letter) for letter in link])
            url = mailto + email
            return '<a href="%(url)s">%(link)s</a>' % {'url': url, 'link': email}

        title = link.replace('http://', '').replace('https://', '')
        if len(title) > 30:
            title = title[:24] + "..."

        pattern = r'http://v.youku.com/v_show/id_([a-zA-Z0-9\=]+).html'
        match = re.match(pattern, link)
        if not match:
            pattern = r'http://v.youku.com/v_show/id_([a-zA-Z0-9\=]+).html'
            match = re.match(pattern, link)
        if match:
            value = (
                r'<div><embed src='
                r'"http://player.youku.com/player.php/sid/%(id)s/v.swf" '
                r'quality="high" width="480" height="400" '
                r'type="application/x-shockwave-flash" /></div>'
            ) % {'id': match.group(1)}
            return value

        return '<a href="%s">%s</a>' % (link, title)


def markdown(text):
    text = to_unicode(text)
    render = AkioRender(flags=m.HTML_USE_XHTML)
    md = m.Markdown(
        render,
        extensions=m.EXT_FENCED_CODE | m.EXT_AUTOLINK,
    )
    return md.render(text)


class RenderMarkdownPost(object):

    def __init__(self, markdown=None):
        self.markdown = markdown

    def get_render_post(self):
        if not self.markdown:
            return None
        f = StringIO(self.markdown)
        header = ''
        body = None
        for line in f:
            if line.startswith('---'):
                body = ''
            elif body is not None:
                body += line
            else:
                header += line

        meta = self.__get_post_meta(header)
        content = markdown(body)
        meta.update({"content": content})
        return meta

    def __get_post_meta(self, header):
        header = markdown(header)
        title = re.findall(r'<h1>(.*)</h1>', header)[0]

        meta = {'title': title}
        items = re.findall(r'<li>(.*?)</li>', header, re.S)
        for item in items:
            index = item.find(':')
            key = item[:index].rstrip()
            value = item[index + 1:].lstrip()
            meta[key] = value

        return meta

########NEW FILE########
__FILENAME__ = models
#!/usr/bin/env python
# -*- coding: utf-8 -*-


class UserMixin(object):

    def get_user_by_id(self, id):
        user = self.db.get("SELECT * FROM users WHERE id = ?", int(id))
        return user

    def get_user_by_email(self, email):
        user = self.db.get("SELECT * FROM users WHERE email = ?", email)
        return user

    def update_user_salt(self, id, salt):
        user = self.get_user_by_id(id)
        if not user:
            return False
        self.db.execute("UPDATE users SET salt=? WHERE id=?;", salt, id)
        return True


class PostMixin(object):

    def get_post_by_id(self, id):
        post = self.db.get("SELECT * FROM posts WHERE id = ?", id)
        return post

    def get_post_by_slug(self, slug):
        post = self.db.get("SELECT * FROM posts WHERE slug = ?", slug)
        return post

    def get_posts_by_tag(self, tag):
        sql = """SELECT p.slug, p.title, p.published FROM posts AS p 
                   INNER JOIN tags AS t 
                   ON p.id = t.post_id 
                   WHERE t.name = ? 
                   ORDER BY p.published desc;
              """
        posts = self.db.query(sql, tag)
        return posts

    def get_posts_by_category(self, category):
        sql = """SELECT slug, title, published FROM posts
                 WHERE category = ?
                 ORDER BY published desc;
              """
        posts = self.db.query(sql, category)
        return posts

    def get_count_posts(self, count=None):
        if count:
            posts = self.db.query("SELECT * FROM posts ORDER BY published "
                                "DESC LIMIT ?;",count)
        else:
            posts = self.db.query("SELECT slug,title,published FROM posts ORDER BY published DESC;")
        return posts

    def create_new_post(self, **post):
        while 1:
            p = self.get_post_by_slug(post["slug"])
            if not p: break
            post["slug"] += "-2"

        sql = """INSERT INTO posts (title,slug,content,tags,category,published,comment)
                 VALUES (?,?,?,?,?,?,?);
              """
        post_id = self.db.execute(sql, post["title"], post["slug"], post["content"],
                              post["tags"], post["category"], post["published"], post['comment'])
        if post_id:
            tags = [tag.strip() for tag in post["tags"].split(",")]
            for tag in tags:
                self.db.execute("INSERT INTO tags (name,post_id) VALUES (?,?);", tag, post_id)
        return post_id

    def update_post_by_id(self, id, **post):
        sql = """UPDATE posts SET title=?,slug=?,content=?,tags=?,category=?,
                 published=?,comment=? WHERE id=?;
              """
        p = self.get_post_by_id(id)
        if p.tags != post["tags"]:
            has_new_tag = True
        else:
            has_new_tag = False
        self.db.execute(sql, post["title"], post["slug"], post["content"],
                     post["tags"], post["category"], post["published"],
                     post['comment'], id)
        if has_new_tag:
            new_tags = [tag.strip() for tag in post["tags"].split(",")]
            self.db.execute("DELETE FROM tags WHERE post_id=?;", id)
            for tag in new_tags:
                self.db.execute("INSERT INTO tags (name,post_id) VALUES (?,?);", tag, id)
        return True

    def delete_post_by_id(self, id):
        self.db.execute("DELETE FROM posts WHERE id=?;", id)
        self.db.execute("DELETE FROM tags WHERE post_id=?;", id)
        return True


    def get_next_prev_post(self, published):
        next_post = self.db.get(
          "SELECT slug,title FROM posts WHERE published > ? ORDER BY published ASC LIMIT 1;",
          published)

        prev_post = self.db.get(
          "SELECT slug,title FROM posts WHERE published < ? ORDER BY published DESC LIMIT 1;",
          published)

        return {"next": next_post, "prev": prev_post}


class TagMixin(object):

    def get_all_tag_count(self, number=None):
        if number:
            sql = """SELECT name, COUNT(name) AS num FROM tags
                     GROUP BY name ORDER BY num DESC LIMIT ?;
                  """
            tags = self.db.query(sql, number)
        else:
            sql = """SELECT name, COUNT(name) AS num FROM tags
                     GROUP BY name ORDER BY num DESC;
                  """
            tags = self.db.query(sql)
        
        return tags

########NEW FILE########
__FILENAME__ = sqlite3lib
#!/usr/bin/env python

import sqlite3
import itertools


class Connection(object):
    """
    A lightweight wrapper around sqlite3; based on tornado.database
    
    db = sqlite.Connection("filename")
    for article in db.query("SELECT * FROM articles")
        print article.title
      
    Cursors are hidden by the implementation.
    """
  
    def __init__(self, filename, isolation_level=None):
        self.filename = filename
        self.isolation_level = isolation_level  # None = autocommit
        self._db = None
        try:
            self.reconnect()
        except:
            # log error @@@
            raise
      
    def close(self):
        """Close database connection"""
        if getattr(self, "_db", None) is not None:
            self._db.close()
        self._db = None
      
    def reconnect(self):
        """Closes the existing database connection and re-opens it."""
        self.close()
        self._db = sqlite3.connect(self.filename)
        self._db.isolation_level = self.isolation_level
    
    def _cursor(self):
        """Returns the cursor; reconnects if disconnected."""
        if self._db is None:
            self.reconnect()
        return self._db.cursor()
    
    def __del__(self):
        self.close()
    
    def execute(self, query, *parameters):
        """Executes the given query, returning the lastrowid from the query."""
        cursor = self._cursor()
        try:
            self._execute(cursor, query, parameters)
            return cursor.lastrowid
        finally:
            cursor.close()
      
    def executemany(self, query, parameters):
        """Executes the given query against all the given param sequences"""
        cursor = self._cursor()
        try:
            cursor.executemany(query, parameters)
            return cursor.lastrowid
        finally:
            cursor.close()
      
    def _execute(self, cursor, query, parameters):
        try:
            return cursor.execute(query, parameters)
        except OperationalError:
            # log error @@@
            self.close()
            raise
      
    def query(self, query, *parameters):
        """Returns a row list for the given query and parameters."""
        cursor = self._cursor()
        try:
            self._execute(cursor, query, parameters)
            column_names = [d[0] for d in cursor.description]
            return [Row(itertools.izip(column_names, row)) for row in cursor]
        finally:
            # cursor.close()
            pass
      
    def get(self, query, *parameters):
        """Returns the first row returned for the given query."""
        rows = self.query(query, *parameters)
        if not rows:
            return None
        elif len(rows) > 1:
            raise Exception("Multiple rows returned from sqlite.get() query")
        else:
            return rows[0]
      

class Row(dict):
    """A dict that allows for object-like property access syntax."""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)
      
OperationalError = sqlite3.OperationalError

########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import hmac
import base64
import datetime
import functools
from HTMLParser import HTMLParser

from hashlib import sha1
from blogconfig import COOKIE_SECRET


class ObjectDict(dict):
    def __getattr__(self, key):
        if key in self:
            return self[key]
        return None

    def __setattr__(self, key, value):
        self[key] = value


# 所有日期采用 `YYYY-MM-DD HH:MM` 格式字符串存储，
# 下面的三个函数用于获取年月日、年和将字符串转换为时间对象

def get_home_time(time):
    time = time.split(" ")[0].strip()
    return time


def get_time_year(time):
    t = get_home_time(time)
    year = t.split("-")[0].strip()
    return year


def format_time(time):
    t = [int(tt) for tt in re.findall(r"[0-9]+", time)]
    t.append(0)
    d = datetime.datetime(*t)
    return d


def get_show_time(time):
    t = [int(tt) for tt in re.findall(r"[0-9]+", time)]
    t.append(0)
    d = datetime.datetime(*t)
    return d.strftime("%d %b")


def archives_list(posts):
    """
    生成文章存档，按年分类
    """
    years = list(set([get_time_year(post.published) for post in posts]))
    years.sort(reverse=True)
    for year in years:
        year_posts = [post for post in posts
                      if get_time_year(post.published) == year]
        yield (year, year_posts)


def authenticated(method):
    """Decorate methods with this to require that the user be logged in."""
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.current_user:
            if self.request.method in ("GET", "HEAD"):
                self.redirect("/")
                return
            self.abort(403)
        return method(self, *args, **kwargs)
    return wrapper


# 因为删除文章链接使用的是 GET 而非 POST，所以无法使用 Tornado 自带的 xsrf
# 预防方法，因此这里使用简单的加密方法，构造文章删除链接
def base64_encode(string):
    """
    base64 encodes a single string. The resulting string is safe for
    putting into URLs.
    """
    return base64.urlsafe_b64encode(string).strip('=')


def signer_code(id):
    mac = hmac.new(COOKIE_SECRET, digestmod=sha1)
    mac.update(id)
    s = mac.digest()
    signer = id + '.' + base64_encode(s)
    return signer


def unsigner_code(signer):
    id, base64_s = signer.split('.')
    mac = hmac.new(COOKIE_SECRET, digestmod=sha1)
    mac.update(id)
    s = mac.digest()
    if base64_s == base64_encode(s):
        return id
    else:
        return None


#Mobile Detect
def is_mobile(user_agent):
    detects = "iPod|iPhone|Android|Opera Mini|BlackBerry| \
               webOS|UCWEB|Blazer|PSP|IEMobile"
    return re.search(detects, user_agent)


#去除文章description中的html标签
class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)


def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

########NEW FILE########
__FILENAME__ = run
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import tornado.ioloop
import tornado.options
import tornado.httpserver
from tornado.options import define, options
from miniakio import Application

#开发调试时使用
define("port", default=8888, help="run on the given port for develop", type=int)

def start():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    start()

########NEW FILE########
__FILENAME__ = tools
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# 用于创建数据库，请按照下面的要求填写相关的信息，再运行`python create_db.py`，
# 并将生成的数据库拷贝到 blog 目录下
import os
import sys
import getopt
import sqlite3
from miniakio.libs import crypto

# 编辑下面的信息

USERNAME = "SErHo"                  # 用户名
EMAIL = "serholiu@gmail.com"        # 邮箱，登陆的时候使用
PASSWORD = "123456"                 # 登陆密码
DBFILE = "example/newblog.db"               # 数据库名称，请保持和 blog/config.py 中设置的名称相同

# 请不要改动下面的内容


def create_db(conn):
    c = conn.cursor()
    c.execute("""
        CREATE TABLE users (id INTEGER NOT NULL PRIMARY KEY,
        salt VARCHAR(12) NOT NULL, username VARCHAR(50) NOT NULL,
        password VARCHAR(255) NOT NULL, email VARCHAR(255) NOT NULL);
        """)
    c.execute("""
        CREATE TABLE posts (id INTEGER NOT NULL PRIMARY KEY,
        title VARCHAR(100) NOT NULL, slug VARCHAR(100) NOT NULL,
        content TEXT NOT NULL, tags VARCHAR(255) NOT NULL,
        category VARCHAR(30) NOT NULL, published VARCHAR(30) NOT NULL,
        comment INTEGER NOT NULL);
        """)
    c.execute("""
        CREATE TABLE tags (id INTEGER NOT NULL PRIMARY KEY,
        name VARCHAR(50) NOT NULL, post_id INTEGER NOT NULL);
        """)

    c.execute("CREATE UNIQUE INDEX users_id ON users(id);")
    c.execute("CREATE UNIQUE INDEX posts_id ON posts(id);")
    c.execute("CREATE INDEX posts_slug ON posts(slug);")
    c.execute("CREATE INDEX tags_name ON tags(name);")
    c.execute("CREATE UNIQUE INDEX tags_id ON tags(id);")
    conn.commit()


def create_user(conn):
    c = conn.cursor()
    salt = crypto.get_random_string()
    enpass = crypto.PasswordCrypto.get_encrypted(PASSWORD)
    c.execute("""
        INSERT INTO users ( salt, username, password, email) VALUES (?,?,?,?)
        """, (salt, USERNAME, enpass, EMAIL))
    conn.commit()


def get_secret():
    return os.urandom(32).encode("base64")


def main(argv):
    help = """
Usage: python tools -o <opt>
    
    opt list:
    createdb      创建数据库并添加用户信息(请先填写相关信息)
    getsecret     随机生成一个 Cookie Secret
    """ 
    opt = ""
    try:
        opts, args = getopt.getopt(argv,"ho:",["opt="])
    except getopt.GetoptError:
        print help
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print help
            sys.exit()
        elif opt in ("-o", "--opt"):
            opt = arg
    
    if opt == "createdb":
        conn = sqlite3.connect(DBFILE)
        print "开始创建数据库..."
        create_db(conn)
        print "数据库创建完毕，开始创建用户账户..."
        create_user(conn)
        conn.close()
        print "用户创建成功，请务必将生成的数据库文件拷贝到 blogconfig 中设置的目录里！！！"
    elif opt == "getsecret":
        print get_secret() 


if __name__ == '__main__':
    main(sys.argv[1:])

########NEW FILE########
