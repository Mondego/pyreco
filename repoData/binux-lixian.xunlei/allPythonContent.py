__FILENAME__ = check_file
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# binux<17175297.hk@gmail.com>

import os
import time
import urllib
import logging
from sys import argv
from libs import lixian_api, tools
from pprint import pprint

#logging.getLogger().setLevel(logging.DEBUG)
tid_dic = {}
if os.path.exists("tid.dict"):
    for line in open("tid.dict", "r"):
        line = line.strip()
        size, tid = line.split(" ", 1)
        tid_dic[int(size)] = tid

if len(argv) != 2:
    print "usage:", __file__, "filepath"
    exit()

cid = tools.cid_hash_file(argv[1])
gcid = tools.gcid_hash_file(argv[1])
size = os.path.getsize(argv[1])
fid = tools.gen_fid(cid, size, gcid)
fake_url = "http://sendfile.vip.xunlei.com/download?fid=%s&mid=666&threshold=150&tid=%s" % (fid, tid_dic.get(size, 0))
print "cid: %s" % cid
print "gcid: %s" % gcid
print "size: %s" % size
print "fid: %s" % fid
print "fake_url: %s" % fake_url
print "thunder_url: %s" % tools.encode_thunder(fake_url)

lx = lixian_api.LiXianAPI()
print "checking file exist...",
ret = lx.webfilemail_url_analysis(fake_url)
if ret['result'] != 0:
    print "no"
    exit()
else:
    print "yes!"

########NEW FILE########
__FILENAME__ = model
# -*- encoding: utf-8 -*-

import sqlalchemy.types as types
from sqlalchemy import *
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class MySQLSettings(object):
    __table_args__ = {
        #'mysql_engine'    : 'InnoDB',
        'mysql_engine'    : 'MyISAM',
        'mysql_charset'   : 'utf8',
        }

class Set(types.TypeDecorator):
    """
    自定义类型模板：set
    基础类型：text
    保存格式：|key1|key2|key3|
    """
    impl = types.Text

    def process_bind_param(self, value, dialect):
        if isinstance(value, basestring):
            return value
        return "|%s|" % u"|".join(set(value))

    def process_result_value(self, value, dialect):
        return set((x for x in value.split("|") if x))

class Task(Base, MySQLSettings):
    __tablename__ = "task"

    id = Column(BigInteger, primary_key=True) #same as xunlei task id
    createtime = Column(DateTime, default=func.now(), index=True)
    updatetime = Column(DateTime, default=func.now(), server_onupdate=text("NOW()"))
    create_uid = Column(BigInteger)
    creator = Column(String(512))
    tags = Column(Set, default=[])
    invalid = Column(Boolean, default=False)

    cid = Column(String(256), index=True)
    url = Column(String(1024))
    lixian_url = Column(String(1024))
    taskname = Column(String(512), default="", index=True) #
    task_type = Column(String(56))
    status = Column(String(56), index=True)
    process = Column(Float)
    size = Column(BigInteger)
    format = Column(String(56))

    files = relationship("File", cascade="merge", backref=backref("task", cascade="merge"))

class File(Base, MySQLSettings):
    __tablename__ = "file"

    id = Column(BigInteger, primary_key=True) #same as xunlei task id
    task_id = Column(BigInteger, ForeignKey("task.id"))
    createtime = Column(DateTime, default=func.now())
    updatetime = Column(DateTime, default=func.now(), server_onupdate=text("NOW()"))

    cid = Column(String(256))
    url = Column(String(1024))
    _lixian_url = Column("lixian_url", String(1024))
    lixian_url = ""
    title = Column(String(1024), default="") #
    dirtitle = Column(String(1024), default="") #
    status = Column(String(56))
    process = Column(Float)
    size = Column(BigInteger)
    format = Column(String(56))

class User(Base, MySQLSettings):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    email = Column(String(512), index=True)
    name = Column(String(256))
    group = Column(String(64))
    permission = Column(Integer)

########NEW FILE########
__FILENAME__ = util
# -*- encoding: utf8 -*-
# author: binux<17175297.hk@gmail.com>

import db
from threading import RLock

__all__ = ("sqlite_fix", "sqlalchemy_rollback")

sqlite_lock = RLock()
def sqlite_fix(func):
    if db.engine.name == "sqlite":
        def wrap(self, *args, **kwargs):
            with sqlite_lock:
                self.session.close()
                result = func(self, *args, **kwargs)
            return result
        return wrap
    else:
        return func

def sqlalchemy_rollback(func):
    def wrap(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except db.SQLAlchemyError, e:
            db.Session().rollback()
            raise
    return wrap

########NEW FILE########
__FILENAME__ = add_task
# -*- encoding: utf-8 -*-
# author: binux<17175297.hk@gmail.com>

import re

from tornado import gen
from tornado.web import HTTPError, UIModule, asynchronous, authenticated
from tornado.options import options
from functools import partial

from base import BaseHandler
from libs.util import AsyncProcessMixin

add_task_info_map = {
     0: u"添加任务失败",
    -1: u"获取任务信息失败",
    -2: u"服务器尚未索引该资源!",
    -3: u"未知的链接类型",
    -4: u"任务已存在",
    -5: u"添加任务失败",
    -99: u"与迅雷服务器通信失败，请稍候再试...",
}
_split_re = re.compile(u"[,|，, ]")
class AddTaskHandler(BaseHandler, AsyncProcessMixin):
    def get(self, anonymous):
        render_path = "add_task_anonymous.html" if anonymous else "add_task.html"
        if not self.current_user:
            message = u"please login first"
        elif anonymous and not self.has_permission("add_anonymous_task"):
            message = u"您没有添加任务的权限"
        elif not anonymous and not self.has_permission("add_task"):
            message = u"您没有发布资源的权限"
        elif self.user_manager.get_add_task_limit(self.current_user["email"]) <= 0:
            message = u"您今天添加的任务太多了！请重新登录以激活配额或联系足兆叉虫。"
        else:
            message = u""
        self.render(render_path, message=message)

    @authenticated
    @asynchronous
    @gen.engine
    def post(self, anonymous):
        if options.using_xsrf:
            self.check_xsrf_cookie()
        url = self.get_argument("url", None)
        btfile = self.request.files.get("btfile")
        btfile = btfile[0] if btfile else None
        title = self.get_argument("title", None)
        tags = self.get_argument("tags", "")
        anonymous = True if anonymous else False
        render_path = "add_task_anonymous.html" if anonymous else "add_task.html"
        email = self.current_user['email']

        if anonymous and not self.has_permission("add_anonymous_task"):
            raise HTTPError(403, "You might not have permission to add anonymous task.")
        elif not anonymous and not self.has_permission("add_task"):
            raise HTTPError(403, "You might not have permission to add task.")
        elif self.user_manager.get_add_task_limit(self.current_user["email"]) <= 0:
            raise HTTPError(403, "You had reach the limit of adding tasks.")

        if not url and not btfile:
            self.render(render_path, message=u"任务下载地址不能为空")
            return
        if btfile and len(btfile['body']) > 500*1024:
            self.render(render_path, message=u"种子文件过大")
            return

        if tags:
            tags = set([x.strip() for x in _split_re.split(tags)])
        result, task = yield gen.Task(self.call_subprocess,
                partial(self.task_manager.add_task, btfile or url, title, tags, email, anonymous,
                                                    self.has_permission("need_miaoxia")))

        if result == 1:
            if task:
                self.write("""<script>
    parent.$('#fancybox-content').css({height: "350px"});
	parent.$.fancybox.resize();
    location='/get_lixian_url?task_id=%d'
</script>""" % task.id)
            else:
                self.write("<script>top.location='/'</script>")
            self.user_manager.incr_add_task_limit(self.current_user["email"])
            self.finish()
        else:
            if anonymous:
                self.render("add_task_anonymous.html", message=add_task_info_map.get(result, u"未知错误"))
            else:
                self.render("add_task.html", message=add_task_info_map.get(result, u"未知错误"))

handlers = [
        (r"/add_task(_anonymous)?", AddTaskHandler),
]
ui_modules = {
}

########NEW FILE########
__FILENAME__ = base
# -*- encoding: utf-8 -*-
# author: binux<17175297.hk@gmail.com>

from time import time
from tornado.web import RequestHandler
from tornado.options import options

class BaseHandler(RequestHandler):
    @property
    def task_manager(self):
        return self.application.task_manager

    @property
    def user_manager(self):
        return self.application.user_manager

    @property
    def vip_pool(self):
        return self.application.vip_pool

    def get_vip(self):
        return self.vip_pool.get_vip(self.get_cookie("xss", None)) or self.task_manager.get_vip()

    def render_string(self, template_name, **kwargs):
        kwargs["options"] = options
        return super(BaseHandler, self).render_string(template_name, **kwargs)

    def get_current_user(self):
        # fix cookie
        if self.request.cookies is None:
            return None
        email = self.get_secure_cookie("email")
        name = self.get_secure_cookie("name")
        if email and name:
            return {
                    "id": self.user_manager.get_id(email),
                    "email": email,
                    "name": name,
                    "group": self.user_manager.get_group(email),
                    "permission": self.user_manager.get_permission(email),
                   }
        elif self.request.remote_ip in ("localhost", "127.0.0.1"):
            return {
                    "id": 0,
                    "email": "bot@localhost",
                    "name": "bot",
                    "group": "bot",
                    "permission": 999,
                    }
        else:
            return None

    def installed_userjs(self):
        if options.using_xss:
            return True
        cookie = self.get_cookie("cross-cookie")
        if cookie == options.cross_cookie_version or cookie == "disabled":
            return True

    def disabled_userjs(self):
        if options.using_xss:
            return False
        return self.get_cookie("cross-cookie") == "disabled"

    def has_permission(self, permission):
        email = self.current_user and self.current_user["email"] or None
        return self.user_manager.check_permission(email, permission)

########NEW FILE########
__FILENAME__ = edit_task
# -*- encoding: utf-8 -*-
# author: binux<17175297.hk@gmail.com>

import re

from tornado.web import HTTPError, UIModule, authenticated
from functools import partial

from base import BaseHandler

_split_re = re.compile(u"[,|，, ]")
class EditTaskHandler(BaseHandler):
    @authenticated
    def get(self, message=""):
        task_id = self.get_argument("task_id")
        task = self.task_manager.get_task(int(task_id))
        if self.current_user['email'] != task.creator and\
           not self.has_permission("admin"):
               raise HTTPError(403, "You might not have permission")
        if not self.has_permission("mod_task"):
            message = u"您没有修改权限"
        self.render("edit.html", task=task, message=message)

    @authenticated
    def post(self):
        task_id = self.get_argument("task_id")
        task = self.task_manager.get_task(int(task_id))
        title = self.get_argument("title", None)
        tags = self.get_argument("tags", "")
        public = self.get_argument("public", False)

        if not title:
            return self.get(u"标题不能为空")

        tags = set([x.strip() for x in _split_re.split(tags)])
        if self.current_user['email'] != task.creator and\
           not self.has_permission("admin"):
               raise HTTPError(403, "You might not have permission")
        if not self.has_permission("mod_task"):
            raise HTTPError(403, "You might not have permission")

        task.taskname = title
        task.tags = tags
        task.invalid = not public
        self.task_manager.merge_task(task)

        return self.get("修改成功")

handlers = [
        (r"/edit", EditTaskHandler),
]
ui_modules = {
}

########NEW FILE########
__FILENAME__ = files
# -*- encoding: utf-8 -*-
# author: binux<17175297.hk@gmail.com>

from tornado.web import HTTPError
from tornado.options import options
from .base import BaseHandler

import re
from urllib import quote_plus
from libs.tools import thunder_filename_encode

class GetLiXianURLHandler(BaseHandler):
    def get(self):
        if not self.has_permission("view_tasklist"):
            self.set_status(403)
            self.render("view_tasklist.html")
            return

        task_id = int(self.get_argument("task_id"))
        referer = self.request.headers.get("referer")
        if referer and not self.request.host in referer[4:10+len(self.request.host)]:
            self.redirect("/share/"+str(task_id))
            return
        
        task = self.task_manager.get_task(task_id)
        if task is None:
            raise HTTPError(404, "task is not exists.")

        vip_info = self.get_vip()
        files = self.task_manager.get_file_list(task_id, vip_info)
        if files is None:
            raise HTTPError(500, "Error when getting file list.")

        cookie = options.cookie_str % vip_info["gdriveid"]
        self.render("lixian.html", task=task, files=files, cookie=cookie, gdriveid=vip_info["gdriveid"])

class ShareHandler(BaseHandler):
    def get(self, task_id):
        task_id = int(task_id)

        if not options.enable_share:
            raise HTTPError(404, "share is not enabled")

        task = self.task_manager.get_task(task_id)
        if task is None:
            raise HTTPError(404, "Task not exists.")

        vip_info = self.get_vip()
        files = self.task_manager.get_file_list(task_id, vip_info)
        if files is None:
            raise HTTPError(500, "Error when getting file list.")

        cookie = options.cookie_str % vip_info["gdriveid"]
        self.render("share.html", task=task, files=files, cookie=cookie, gdriveid=vip_info["gdriveid"])

class XSSDoneHandler(BaseHandler):
    def get(self):
        gdriveid = self.get_argument("gdriveid")
        cookie = options.cookie_str % gdriveid
        self.write('document.cookie="%s"' % cookie)
        self.set_cookie("xss", gdriveid)

class XSSJSHandler(BaseHandler):
    def get(self):
        render_tpl = "xss.js"

        gdriveid = self.get_vip()["gdriveid"]
        cookie = options.cookie_str % gdriveid
        self.render(render_tpl, cookie=cookie, gdriveid=gdriveid)

class XSSCheckHandler(BaseHandler):
    def get(self):
        gdriveid = self.get_argument("gdriveid")
        self.render("xss_check.js", gdriveid=gdriveid)

lixian_n_re = re.compile(r"&n=\w+")
class IDMExportHandler(BaseHandler):
    def get(self, task_id):
        index = self.get_argument("i", None)
        if index:
            try:
                index = set((int(x) for x in index.split(",")))
            except:
                raise HTTPError(403, "Request format error.")

        def rewrite_url(url, filename):
            return lixian_n_re.sub("&n="+thunder_filename_encode(filename), url)

        vip_info = self.get_vip()
        template = "<\r\n%s\r\ncookie: gdriveid=%s\r\n>\r\n"
        files = self.task_manager.get_file_list(task_id, vip_info)
        if files is None:
            raise HTTPError(500, "Error when getting file list.")
        if files == []:
            raise HTTPError(404, "Task not exists.")

        gdriveid = vip_info["gdriveid"]
        self.set_header("Content-Type", "application/octet-stream")
        if index:
            files = (x for i, x in enumerate(files) if i in index)
        for f in files:
            if not f.lixian_url:
                continue
            self.write(template % (rewrite_url(f.lixian_url, f.dirtitle), gdriveid))

class aria2cExportHandler(BaseHandler):
    def get(self, task_id):
        index = self.get_argument("i", None)
        if index:
            try:
                index = set((int(x) for x in index.split(",")))
            except:
                raise HTTPError(403, "Request format error.")

        template = "%s\r\n  out=%s\r\n  header=Cookie: gdriveid=%s\r\n  continue=true\r\n  max-connection-per-server=5\r\n  split=10\r\n  parameterized-uri=true\r\n\r\n"
        vip_info = self.get_vip()
        files = self.task_manager.get_file_list(task_id, vip_info)
        if files is None:
            raise HTTPError(500, "Error when getting file list.")
        if files == []:
            raise HTTPError(404, "Task not exists.")

        gdriveid = vip_info["gdriveid"]
        self.set_header("Content-Type", "application/octet-stream")
        if index:
            files = (x for i, x in enumerate(files) if i in index)
        for f in files:
            if not f.lixian_url:
                continue
            self.write(template % (f.lixian_url.replace("gdl", "{gdl,dl.f,dl.g,dl.h,dl.i,dl.twin}"), f.dirtitle, gdriveid))

class orbitExportHandler(BaseHandler):
    def get(self, task_id):
        index = self.get_argument("i", None)
        if index:
            try:
                index = set((int(x) for x in index.split(",")))
            except:
                raise HTTPError(403, "Request format error.")
                
        def rewrite_url(url, filename):
            return lixian_n_re.sub("&n="+thunder_filename_encode(filename), url)

        template = "%s|%s||gdriveid=%s\r\n"
        vip_info = self.get_vip()
        files = self.task_manager.get_file_list(task_id, vip_info)
        if files is None:
            raise HTTPError(500, "Error when getting file list.")
        if files == []:
            raise HTTPError(404, "Task not exists.")

        gdriveid = vip_info["gdriveid"]
        self.set_header("Content-Type", "application/octet-stream")
        if index:
            files = (x for i, x in enumerate(files) if i in index)
        for f in files:
            if not f.lixian_url:
                continue
            self.write(template % (rewrite_url(f.lixian_url, f.dirtitle), f.dirtitle.replace("|", "_"), gdriveid))

handlers = [
        (r"/get_lixian_url", GetLiXianURLHandler),
        (r"/export/"+options.site_name+"_idm_(\d+).*?\.ef2", IDMExportHandler),
        (r"/export/"+options.site_name+"_aria2c_(\d+).*?\.down", aria2cExportHandler),
        (r"/export/"+options.site_name+"_orbit_(\d+).*?\.olt", orbitExportHandler),
        (r"/share/(\d+)", ShareHandler),
        (r"/xss", XSSDoneHandler),
        (r"/xssjs", XSSJSHandler),
        (r"/xss_check.js", XSSCheckHandler),
]
ui_modules = {
}

########NEW FILE########
__FILENAME__ = index
# -*- encoding: utf-8 -*-
# author: binux<17175297.hk@gmail.com>

from tornado.web import HTTPError, UIModule
from tornado.options import options
from .base import BaseHandler
from libs.cache import mem_cache

TASK_LIMIT = 30

class IndexHandler(BaseHandler):
    def get(self):
        if not self.has_permission("view_tasklist"):
            self.set_status(403)
            self.render("view_tasklist.html")
            return

        q = self.get_argument("q", "")
        feed = self.get_argument("feed", None)
        view_all = self.has_permission("view_invalid")
        tasks = self.task_manager.get_task_list(q=q, limit=TASK_LIMIT, all=view_all)
        if feed:
            self.set_header("Content-Type", "application/atom+xml")
            self.render("feed.xml", tasks=tasks)
        else:
            self.render("index.html", tasks=tasks, query={"q": q})

class FeedHandler(BaseHandler):
    def get(self):
        self.redirect("/?feed=rss", True)

class SitemapHandler(BaseHandler):
    def get(self):
        taskids = self.task_manager.get_task_ids()
        tags = self.task_manager.get_tag_list()
        self.render("sitemap.xml", taskids=taskids, tags=tags)

class TagHandler(BaseHandler):
    def get(self, tag):
        if not self.has_permission("view_tasklist"):
            self.set_status(403)
            self.render("view_tasklist.html")
            return

        feed = self.get_argument("feed", None)
        tasks = self.task_manager.get_task_list(t=tag, limit=TASK_LIMIT)
        if feed:
            self.set_header("Content-Type", "application/atom+xml")
            self.render("feed.xml", tasks=tasks)
        else:
            self.render("index.html", tasks=tasks, query={"t": tag})

class UploadHandler(BaseHandler):
    def get(self, creator_id):
        if not self.has_permission("view_tasklist"):
            self.set_status(403)
            self.render("view_tasklist.html")
            return

        feed = self.get_argument("feed", None)
        creator = self.user_manager.get_user_email_by_id(int(creator_id)) or "no such user"
        if self.current_user and self.current_user["email"] == creator:
            all = True
        elif self.has_permission("view_invalid"):
            all = True
        else:
            all = False
        tasks = self.task_manager.get_task_list(a=creator, limit=TASK_LIMIT, all=all)
        if feed:
            self.set_header("Content-Type", "application/atom+xml")
            self.render("feed.xml", tasks=tasks)
        else:
            self.render("index.html", tasks=tasks, query={"a": creator_id, "creator": creator})

class GetNextTasks(BaseHandler):
    def get(self):
        if not self.has_permission("view_tasklist"):
            raise HTTPError(403)

        start_task_id = int(self.get_argument("s"))
        q = self.get_argument("q", "")
        t = self.get_argument("t", "")
        a = self.get_argument("a", "")
        creator = ""
        if a:
            creator = self.user_manager.get_user_email_by_id(int(a)) or "no such user"
        if self.current_user and self.current_user["email"] == creator:
            all = True
        elif self.has_permission("view_invalid"):
            all = True
        else:
            all = False
        tasks = self.task_manager.get_task_list(start_task_id,
                q=q, t=t, a=creator, limit = TASK_LIMIT, all=all)
        self.render("task_list.html", tasks=tasks)

class NoIEHandler(BaseHandler):
    def get(self):
        self.render("no-ie.html")

class TaskItemsModule(UIModule):
    def render(self, tasks):
        return self.render_string("task_list.html", tasks=tasks)

class TagsModule(UIModule):
    def render(self, tags):
        if not tags:
            return u"无"
        result = []
        for tag in tags:
            result.append("""<a href="/tag/%s">%s</a>""" % (tag, tag))
        return u", ".join(result)

class TagListModule(UIModule):
    @mem_cache(60*60)
    def render(self):
        def size_type(count):
            if count < 10:
                return 1
            elif count < 100:
                return 2
            else:
                return 3

        tags = self.handler.task_manager.get_tag_list()
        return self.render_string("tag_list.html", tags=tags, size_type=size_type)

handlers = [
        (r"/", IndexHandler),
        (r"/noie", NoIEHandler),
        (r"/feed", FeedHandler),
        #(r"/sitemap\.xml", SitemapHandler),
        (r"/tag/(.+)", TagHandler),
        (r"/uploader/(\d+)", UploadHandler),
        (r"/next", GetNextTasks),
]
ui_modules = {
        "TaskItems": TaskItemsModule,
        "TagsModule": TagsModule,
        "TagList": TagListModule,
}

########NEW FILE########
__FILENAME__ = login
# -*- encoding: utf-8 -*-
# author: binux<17175297.hk@gmail.com>

from tornado.web import HTTPError, asynchronous
from tornado.auth import GoogleMixin
from tornado.options import options
from .base import BaseHandler

class LoginHandler(BaseHandler, GoogleMixin):
    @asynchronous
    def get(self):
       if self.get_argument("openid.mode", None):
           self.get_authenticated_user(self.async_callback(self._on_auth))
           return
       if self.get_argument("logout", None):
           self.clear_cookie("name")
           self.clear_cookie("email")
           self.redirect("/")
           return
       reg_key = self.get_argument("key", None)
       if reg_key:
           self.set_secure_cookie("reg_key", reg_key, expires_days=1)
       self.authenticate_redirect()

    def _on_auth(self, user):
        import logging
        if not user:
            raise HTTPError(500, "Google auth failed.")
        if "zh" in user.get("locale", ""):
            chinese = False
            for word in user.get("name", ""):
                if ord(word) > 128:
                    chinese = True
                    break
            if chinese:
                user["name"] = user.get("last_name", "")+user.get("first_name", "")
        if options.reg_key:
            _user = self.user_manager.get_user(user["email"])
            reg_key = self.get_secure_cookie("reg_key", max_age_days=1)
            if not _user and reg_key != options.reg_key:
                self.set_status(403)
                self.write("Registry is Disabled by Administrator.")
                self.finish()
                return
        self.user_manager.update_user(user["email"], user["name"])
        self.set_secure_cookie("name", user["name"])
        self.set_secure_cookie("email", user["email"])
        self.redirect("/")

handlers = [
        (r"/login", LoginHandler),
]
ui_modules = {
}

########NEW FILE########
__FILENAME__ = manager
# -*- encoding: utf-8 -*-
# author: binux<17175297.hk@gmail.com>

from tornado.web import HTTPError, UIModule, authenticated
from tornado.options import options
from .base import BaseHandler

class ManagerIndexHandler(BaseHandler):
    @authenticated
    def get(self, option):
        if not self.has_permission("admin"):
            raise HTTPError(403, "You might not have permissiont to do that.")
        message = self.get_argument("msg", "DANGER!")
        if option:
            if not hasattr(self, option) or not callable(getattr(self, option)):
                raise HTTPError(404, "option not exists.")
            message = getattr(self, option)()
            if self.request.method == "GET":
                self.render("manager.html", message=message)
            else:
                self.redirect("/manager?msg=%s" % message)
            return

        self.render("manager.html", message=message)

    post = get

    def flush_mem_cache(self):
        from libs.cache import _mem_caches
        _mem_caches.clear()
        return "清除缓存成功"

    def refetch_finished_tasks(self):
        self.task_manager._last_update_task = 0
        self.task_manager.async_update()
        return "已启动refetch任务"

    def refetch_downloading_tasks(self):
        self.task_manager._last_update_downloading_task = 0
        self.task_manager.async_update()
        return "已启动refetch任务"

    def recheck_login(self):
        self.task_manager._last_check_login = 0
        _ = self.task_manager.xunlei
        return ""

    def set_uid(self):
        uid = int(self.get_argument("uid"))
        gdriveid = self.get_argument("gdriveid")
        tid = int(self.get_argument("tid"))
        self.task_manager._uid = uid
        self.task_manager._gdriveid = gdriveid
        self.task_manager.last_task_id = tid
        return "uid=%s, gdriveid=%s, tid=%s" % (
                self.task_manager.uid,
                self.task_manager.gdriveid,
                self.task_manager.last_task_id)

    def set_vip_pool(self):
        pool_lines = self.get_argument("pool", "")
        self.vip_pool.pool = {}
        self.vip_pool.parser_mline(pool_lines)

    def set_tid(self):
        tid = int(self.get_argument("tid"))
        self.task_manager.last_task_id = tid
        return "tid被设置为 %d" % tid

    def clear_tid_sample(self):
        self.task_manager.task_id_sample.clear()
        return ""

    def change_user_group(self):
        user_id = int(self.get_argument("user_id"))
        group = int(self.getargument("group"))
        user = self.user_manager.get_user_by_id(user_id)
        if not user:
            raise HTTPError(404, "User not found.")
        user.group = group
        self.user_manager.session.add(user)
        self.user_manager.session.commit()
        return "OK"

    def block_user(self):
        user_id = int(self.get_argument("user_id"))
        user = self.user_manager.get_user_by_id(user_id)
        if not user:
            return "No such user"
        user.group = "block"
        self.user_manager.session.add(user)
        self.user_manager.session.commit()
        return "OK"

    def get_user_email(self):
        user_id = int(self.get_argument("user_id"))
        return self.user_manager.get_user_email_by_id(user_id)

    @property
    def logging_level(self):
        import logging
        return logging.getLevelName(logging.getLogger().level)

    def switch_level(self):
        import logging
        root_logging = logging.getLogger()
        if root_logging.level == logging.DEBUG:
            root_logging.setLevel(logging.INFO)
        else:
            root_logging.level = logging.DEBUG
        return ""

    def get_add_task_limit(self):
        return "%r" % self.user_manager.add_task_limit_used

    def get_reload_limit(self):
        return "%r" % self.user_manager.reload_limit

    def reset_limit(self):
        return self.user_manager.reset_all_add_task_limit()

handlers = [
        (r"/manager/?(\w*)", ManagerIndexHandler),
]
ui_modules = {
}

########NEW FILE########
__FILENAME__ = cache
# -*- coding: utf-8 -*-
#
# Copyright(c) 2010 poweredsites.org
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import hashlib
from time import time
from tornado.options import options

_mem_caches = {}

def mem_cache(expire=7200, key=""):
    """Mem cache to python dict by key"""
    def wrapper(func):
        def new_func(self, *args, **kwargs):
            now = time()
            if key:
                c = key
            else:
                c = self.__class__.__name__ + func.__name__ + repr(func)
            k = key_gen(self, c, *args, **kwargs)

            value = _mem_caches.get(k, None)
            if _valid_cache(value, now):
                return value["value"]
            else:
                val = func(self, *args, **kwargs)
                _mem_caches[k] = {"value":val, "expire":now+expire}

                return val

        if options.cache_enabled:
            return new_func
        else:
            return func
    return wrapper

def key_gen(self, key, *args, **kwargs):
    code = hashlib.md5()

    code.update(str(key))

    # copy args to avoid sort original args
    c = list(args[:])
    # sort c to avoid generate different key when args is the same
    # but sequence is different
    c.sort()
    c = [str(v) for v in c]
    code.update("".join(c))

    c = ["%s=%s" % (k, v) for k, v in kwargs]
    c.sort()
    code.update("".join(c))

    return code.hexdigest()

def _valid_cache(value, now):
    if value:
        if value["expire"] > now:
            return True
        else:
            return False
    else:
        return False

########NEW FILE########
__FILENAME__ = db_task_manager
# -*- encoding: utf-8 -*-
# author: binux<17175297.hk@gmail.com>

import logging
import thread
import random
import socket
import re

import db
from StringIO import StringIO
from threading import Lock
from db import Session
from time import time
from db.util import *
from libs.tools import url_unmask
from libs.lixian_api import LiXianAPI, determin_url_type
from libs.cache import mem_cache
from tornado.options import options
from requests import RequestException

TASK_ID_SAMPLE_SIZE = 10

ui_re = re.compile(r"ui=\d+")
ti_re = re.compile(r"ti=\d+")
def fix_lixian_url(url):
    url = ui_re.sub("ui=%(uid)d", url)
    url = ti_re.sub("ti=%(tid)d", url)
    return url

lixian_co_re = re.compile(r"&co=\w+")
def fix_lixian_co(url):
    return lixian_co_re.sub("", url)

def catch_connect_error(default_return):
    def warp(func):
        def new_func(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except RequestException, e:
                logging.error(repr(e))
                return default_return
            except socket.timeout, e:
                logging.error(repr(e))
                return default_return
            except AssertionError, e:
                logging.error(repr(e))
                return default_return
        new_func.__name__ = func.__name__
        return new_func
    return warp

class DBTaskManager(object):
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self._last_check_login = 0
        self._last_update_all_task = 0
        self._last_update_downloading_task = 0
        self._last_get_task_list = 0
        #fix for _last_get_task_list
        self.time = time

        self._last_update_task = 0
        self._last_update_task_size = 0
        self._last_update_task_lock = Lock()

        self._xunlei = LiXianAPI()
        verifycode = self._xunlei._get_verifycode(self.username)
        if not verifycode:
            with open('verifycode.jpg', 'w') as verifycode_fp:
                verifycode_fp.write(self._xunlei.verifycode())
            verifycode = raw_input('Please open ./verifycode.jpg and enter the verifycode: ')
        self.islogin = self._xunlei.login(self.username, self.password, verifycode)
        self._last_check_login = time()

    @property
    def xunlei(self):
        if self._last_check_login + options.check_interval < time():
            if not self._xunlei.check_login():
                self._xunlei.logout()
                self.islogin = self._xunlei.login(self.username, self.password)
            self._last_check_login = time()
        return self._xunlei

    @property
    def gdriveid(self):
        return self._xunlei.gdriveid

    @property
    def uid(self):
        return self._xunlei.uid

    def get_vip(self):
        return {"uid": self.uid,
                "gdriveid": self.gdriveid,
                "tid": 1
               }

    @sqlalchemy_rollback
    def _update_tasks(self, tasks):
        session = Session()
        while tasks:
            nm_list = []
            bt_list = []
            for task in tasks[:100]:
                if task.task_type in ("bt", "magnet"):
                    bt_list.append(task.id)
                else:
                    nm_list.append(task.id)

            for res in self.xunlei.get_task_process(nm_list, bt_list):
                task = self.get_task(res['task_id'])
                if not task: continue
                task.status = res['status']
                task.process = res['process']
                if task.status == "failed":
                    task.invalid = True
                if res['cid'] and res['lixian_url']:
                    task.cid = res['cid']
                    task.lixian_url = res['lixian_url']

                if task.status in ("downloading", "finished"):
                    if not self._update_file_list(task):
                        task.status = "downloading"
                session.add(task)

            tasks = tasks[100:]
        session.commit()
        session.close()

    @sqlalchemy_rollback
    def _update_task_list(self, limit=10, st=0, ignore=False):
        now = self.time()
        with self._last_update_task_lock:
            if now <= self._last_update_task and limit <= self._last_update_task_size:
                return
            self._last_update_task = self.time()
            self._last_update_task_size = limit

            session = Session()
            tasks = self.xunlei.get_task_list(limit, st)
            for task in tasks[::-1]:
                db_task_status = session.query(db.Task.status).filter(
                        db.Task.id == task['task_id']).first()
                if db_task_status and db_task_status[0] == "finished":
                    continue

                db_task = self.get_task(int(task['task_id']))
                changed = False
                if not db_task:
                    changed = True
                    db_task = db.Task()
                    db_task.id = task['task_id']
                    db_task.create_uid = self.uid
                    db_task.cid = task['cid']
                    db_task.url = task['url']
                    db_task.lixian_url = task['lixian_url']
                    db_task.taskname = task['taskname'] or "NULL"
                    db_task.task_type = task['task_type']
                    db_task.status = task['status']
                    db_task.invalid = True
                    db_task.process = task['process']
                    db_task.size = task['size']
                    db_task.format = task['format']
                else:
                    db_task.lixian_url = task['lixian_url']
                    if db_task.status != task['status']:
                        changed = True
                        db_task.status = task['status']
                    if db_task.status == "failed":
                        db_task.invalid = True
                    if db_task.process != task['process']:
                        changed = True
                        db_task.process = task['process']

                session.add(db_task)
                if changed and not self._update_file_list(db_task, session):
                    db_task.status = "failed"
                    db_task.invalid = True
                    session.add(db_task)
                
            session.commit()
            session.close()

    @sqlalchemy_rollback
    def _update_file_list(self, task, session=None):
        if session is None:
            session = Session()
        if task.task_type == "normal":
            tmp_file = dict(
                    task_id = task.id,
                    cid = task.cid,
                    url = task.url,
                    lixian_url = task.lixian_url,
                    title = task.taskname,
                    status = task.status,
                    dirtitle = task.taskname,
                    process = task.process,
                    size = task.size,
                    format = task.format
                    )
            files = [tmp_file, ]
        elif task.task_type in ("bt", "magnet"):
            try:
                files = self.xunlei.get_bt_list(task.id, task.cid)
            except Exception, e:
                logging.error(repr(e))
                return False

        for file in files:
            db_file = session.query(db.File).get(int(file['task_id']))
            if not db_file:
                db_file = db.File()
                db_file.id = file['task_id']
                db_file.task_id = task.id
                db_file.cid = file['cid']
                db_file.url = file['url']
                db_file._lixian_url = file['lixian_url'] #fix_lixian_url(file['lixian_url'])
                db_file.title = file['title']
                db_file.dirtitle = file['dirtitle']
                db_file.status = file['status']
                db_file.process = file['process']
                db_file.size = file['size']
                db_file.format = file['format']
            else:
                db_file._lixian_url = file['lixian_url'] #fix_lixian_url(file['lixian_url'])
                db_file.status = file['status']
                db_file.process = file['process']

            session.add(db_file)
        return True

    def _restart_all_paused_task(self):
        task_ids = []
        for task in self.xunlei.get_task_list(options.task_list_limit, st=1):
            if task['status'] == "paused":
                task_ids.append(task['task_id'])
        if task_ids:
            self.xunlei.redownload(task_ids)

    def _task_scheduling(self):
        # as we can't get real status of a task when it's status is waiting, stop the task with lowest
        # speed. when all task is stoped, restart them.
        tasks = self.xunlei.get_task_list(options.task_list_limit, 1)
        downloading_tasks = []
        waiting_tasks = []
        paused_tasks = []
        for task in tasks:
            if task['status'] == "downloading":
                downloading_tasks.append(task)
            elif task['status'] == "waiting":
                waiting_tasks.append(task)
            elif task['status'] == "paused":
                paused_tasks.append(task)
        if downloading_tasks:
            self.xunlei.task_pause([x['task_id'] for x in downloading_tasks])
        if not waiting_tasks:
            self.xunlei.redownload([x['task_id'] for x in paused_tasks])

    @sqlalchemy_rollback
    def get_task(self, task_id):
        return Session().query(db.Task).get(task_id)

    @sqlalchemy_rollback
    def merge_task(self, task):
        session = Session()
        ret = session.merge(task)
        session.commit()
        session.close()
        return ret

    @sqlalchemy_rollback
    def get_task_by_cid(self, cid):
        return Session().query(db.Task).filter(db.Task.cid == cid).filter(db.Task.status != "failed")

    @sqlalchemy_rollback
    def get_task_by_title(self, title):
        return Session().query(db.Task).filter(db.Task.taskname == title)
    
    @sqlalchemy_rollback
    def get_task_list(self, start_task_id=0, offset=0, limit=30, q="", t="", a="", order=db.Task.createtime, dis=db.desc, all=False):
        session = Session()
        self._last_get_task_list = self.time()
        # base query
        query = session.query(db.Task)
        # query or tags
        if q:
            query = query.filter(db.or_(db.Task.taskname.like("%%%s%%" % q),
                db.Task.tags.like("%%%s%%" % q)))
        elif t:
            query = query.filter(db.Task.tags.like("%%|%s|%%" % t));
        # author query
        if a:
            query = query.filter(db.Task.creator == a)
        # next page offset
        if start_task_id:
            value = session.query(order).filter(db.Task.id == start_task_id).first()
            if not value:
                return []
            if dis == db.desc:
                query = query.filter(order < value[0])
            else:
                query = query.filter(order > value[0])
        # order or limit
        if not all:
            query = query.filter(db.Task.invalid == False)
        query = query.order_by(dis(order), dis(db.Task.id)).offset(offset).limit(limit)

        result = query.all()
        if result and start_task_id:
            for i, each in enumerate(result):
                if each.id == start_task_id:
                    result = result[i+1:]
                    if not result:
                        return self.get_task_list(start_task_id=start_task_id, offset=offset+i+1, limit=limit, q=q, t=t, a=a, order=order, dis=dis, all=all)
                    else:
                        return result
        session.close()
        return result

    @sqlalchemy_rollback
    def get_file_list(self, task_id, vip_info=None):
        task = self.get_task(task_id)
        if not task: return []

        if vip_info is None:
            vip_info = self.get_vip()

        #fix lixian url
        if not vip_info["tid"]:
            return []
        for file in task.files:
            file.lixian_url = file._lixian_url
            #file.lixian_url = fix_lixian_co(file.lixian_url)
        return task.files
    
    @mem_cache(2*60*60)
    @sqlalchemy_rollback
    def get_tag_list(self):
        from collections import defaultdict
        tags_count = defaultdict(lambda: defaultdict(int))
        for tags, in Session().query(db.Task.tags).filter(db.Task.invalid == False):
            for tag in tags:
                tags_count[tag.lower()][tag] += 1
        result = dict()
        for key, value in tags_count.iteritems():
            items = value.items()
            key = max(items, key=lambda x: x[1])[0]
            result[key] = sum([x[1] for x in items])
        return sorted(result.iteritems(), key=lambda x: x[1], reverse=True)

    @mem_cache(expire=5*60*60)
    @sqlalchemy_rollback
    def get_task_ids(self):
        result = []
        for taskid, in Session().query(db.Task.id):
            result.append(taskid)
        return result

    @catch_connect_error((-99, "connection error"))
    def add_task(self, url, title=None, tags=set(), creator="", anonymous=False, need_miaoxia=True):
        session = Session()
        def update_task(task, title=title, tags=tags, creator=creator, anonymous=anonymous):
            if not task:
                return task
            if task.invalid and not anonymous:
                if title: task.taskname = title or "NULL"
                if tags: task.tags = tags
                task.creator = creator
                task.invalid = False
                session.add(task)
                session.commit()
                _ = task.id
            return task

        def _random():
            return random.randint(100, 999)

        # step 1: determin type
        if isinstance(url, basestring):
            url_unmasked = url_unmask(url)
            if not isinstance(url_unmasked, unicode):
                for each in ("utf8", "gbk", "shift_jis", ):
                    try:
                        url = url_unmasked.decode(each)
                        break
                    except:
                        continue
            task = session.query(db.Task).filter(db.Task.url == url).first()
            if task:
                return (1, update_task(task))

            url_type = determin_url_type(url)
            if url_type in ("bt", "magnet"):
                check = self.xunlei.bt_task_check
                add_task_with_info = self.xunlei.add_bt_task_with_dict
            elif url_type in ("normal", "ed2k", "thunder"):
                check = self.xunlei.task_check
                add_task_with_info = self.xunlei.add_task_with_dict
            else:
                return (-3, "space error")
                #result = self.xunlei.add_batch_task([url, ])
        else:
            url_type = "torrent"
            check = self.xunlei.torrent_upload
            add_task_with_info = self.xunlei.add_bt_task_with_dict
            url = (url['filename'], StringIO(url['body']))
         
        # get info
        if url_type in ("bt", "torrent", "magnet"):
            if isinstance(url, tuple):
                info = check(*url)
            else:
                info = check(url)
            if not info: return (-1, "check task error")
            if need_miaoxia and not info.get('cid'):
                return (-2, "need miaoxia")
            if need_miaoxia and not self.xunlei.is_miaoxia(info['cid'],
                    [x['index'] for x in info['filelist'] if x['valid']][-20:]):
                return (-2, "need miaoxia")
        else:
            if need_miaoxia and not self.xunlei.is_miaoxia(url):
                return (-2, "need miaoxia")
            info = check(url)
            if not info:
                return (-3, "space error")

        # step 3: check info
        # for bt
        if 'filelist' in info:
            for each in info['filelist']:
                each['valid'] = 1
        # check cid
        if info.get('cid'):
            task = self.get_task_by_cid(info['cid'])
            if task.count() > 0:
                return (1, update_task(task[0]))

        # check title
        if title:
            info['title'] = title
        else:
            title = info.get('title', 'None')
        if not info['cid'] and \
                self.get_task_by_title(info['title']).count() > 0:
            info['title'] = "%s#%s@%s %s" % (options.site_name, _random(), self.time(), info['title'])

        # step 4: commit & fetch result
        result = add_task_with_info(url, info)
        if not result:
            return (0, "error")
        self._update_task_list(5)

        # step 5: checkout task&fix
        task = None
        if info.get('cid') and not task:
            task = self.get_task_by_cid(info['cid']).first()
        if info.get('title') and not task:
            task = self.get_task_by_title(info['title']).first()
        if url and isinstance(url, basestring) and not task:
            task = session.query(db.Task).filter(db.Task.url == url).first()
        if not task:
            return (-5, "match task error")

        if task:
            if title: task.taskname = title
            if tags: task.tags = tags
            task.creator = creator
            task.invalid = anonymous
            if task.taskname is None:
                task.taskname = "None"
            session.add(task)
            session.commit()
            _ = task.id
        session.close()
        return (1, task)

    @sqlalchemy_rollback
    def update(self):
        if self._last_update_all_task + options.finished_task_check_interval < time():
            self._last_update_all_task = time()
            self._update_task_list(options.task_list_limit)

        if self._last_update_downloading_task + \
                options.downloading_task_check_interval < self._last_get_task_list or \
           self._last_update_downloading_task + \
                options.finished_task_check_interval < time():
            self._last_update_downloading_task = time()
            need_update = Session().query(db.Task).filter(db.or_(db.Task.status == "waiting", db.Task.status == "downloading", db.Task.status == "paused")).all()
                                                  #.order_by(desc(db.Task.id)).limit(100).all()
            if need_update:
                self._update_tasks(need_update)

            self._task_scheduling()

    def async_update(self):
        thread.start_new_thread(DBTaskManager.update, (self, ))

########NEW FILE########
__FILENAME__ = jsfunctionParser
# jsonParser.py
#
# Implementation of a simple JSON parser, returning a hierarchical
# ParseResults object support both list- and dict-style data access.
#
# Copyright 2006, by Paul McGuire
#
# Updated 8 Jan 2007 - fixed dict grouping bug, and made elements and
#   members optional in array and object collections
#
json_bnf = """
object 
    { members } 
    {} 
members 
    string : value 
    members , string : value 
array 
    [ elements ]
    [] 
elements 
    value 
    elements , value 
value 
    string
    number
    object
    array
    true
    false
    null
"""

import json
from pyparsing import *

TRUE = Keyword("true").setParseAction( replaceWith(True) )
FALSE = Keyword("false").setParseAction( replaceWith(False) )
NULL = Keyword("null").setParseAction( replaceWith(None) )

def string_parse(toks):
    result = []
    for t in toks:
        if t.startswith('"'):
            result.append(json.loads(t))
        else:
            result.append(json.loads('"%s"' % t[1:-1].replace("\\'", "'")))
    return result

jsonString = quotedString.setParseAction( string_parse )
jsonNumber = Combine( Optional('-') + ( '0' | Word('123456789',nums) ) +
                    Optional( '.' + Word(nums) ) +
                    Optional( Word('eE',exact=1) + Word(nums+'+-',nums) ) )

jsonObject = Forward()
jsonArray = Forward()
jsonValue = Forward()
jsonElements = delimitedList( jsonValue )
jsonArray1 = Group(Suppress('[') + Optional(jsonElements) + Suppress(']') )
jsonArray2 = Group(Suppress(CaselessLiteral('new'))+Suppress(White())+Suppress(CaselessLiteral('array(')) + Optional(jsonElements) + Suppress(')') )
jsonArray << ( jsonArray1 | jsonArray2 )
jsonValue << ( jsonString | jsonNumber | jsonObject | jsonArray | TRUE | FALSE | NULL )
memberDef = Group( jsonString + Suppress(':') + jsonValue )
jsonMembers = delimitedList( memberDef )
jsonObject << Dict( Suppress('{') + Optional(jsonMembers) + Suppress('}') )
jsFunctionName = Word(alphas + "_.",  alphanums + "_.")
jsFunctionCall = Suppress(Optional(CaselessLiteral("<script>"))) + \
                    Optional(jsFunctionName, Empty()) + Suppress(Optional("(")) + \
                        Group(Optional(jsonElements)) + \
                    Suppress(Optional(")"+";")) + \
                 Suppress(Optional(CaselessLiteral("</script>")))

def convertNumbers(s,l,toks):
    n = toks[0]
    try:
        return int(n)
    except ValueError, ve:
        return float(n)

def convertDict(toks):
    result = {}
    for each in toks:
        result[each[0]] = each[1]
    return result

def convertList(toks):
    result = []
    for each in toks:
        result.append(each.asList())
    return result

def call_json(toks):
    return map(json.loads, toks)

jsonNumber.setParseAction( convertNumbers )
jsonObject.setParseAction( convertDict )
jsonArray.setParseAction( convertList )

def parser_js_function_call(string):
    return jsFunctionCall.parseString(string.lstrip('\xef\xbf\xbb')).asList()
    
if __name__ == "__main__":
    testdata = """queryUrl(1,'3BC3BEC436094736BF19350711D4A5556F4B7536','123806924','[Dymy][Nurarihyon_no_Mago_Sennen_Makyou][18v2][BIG5][RV10][848x480].rmvb','0',new Array('[Dymy][Nurarihyon_no_Mago_Sennen_Makyou][18v2][BIG5][RV10][848x480].rmvb'),new Array('118M'),new Array('123806924'),new Array('1'),new Array('RMVB'),new Array('0'),'13206731991951250210.5123566347')"""
    testdata1 = """ queryCid("bt:\/\/3547930B96AFA7B0A1CFCC80D516ADE97A34DAE0\/0", '4E1FA9C76605CA8E77DD35DA08D817617403BF26', '87B9431F2F5606721BD761FAA5638A809DAF3080', '8055706', 'hbzz.rar', 0, 0, 0,'13206731991951250210.5123566347','rar')"""
    testdata2 = """ parent.begin_task_batch_resp()"""
    testdata3 = """fill_bt_list({"Result":{"Tid":"33684635655","Infoid":"3547930B96AFA7B0A1CFCC80D516ADE97A34DAE0","Record":[{"id":0,"title":"[AngelSub][Guilty Crown][04][FULLHD][BIG5][x264_AC3].mkv","download_status":"1","cid":"DCA5280E5072F48A2D0059F9BD00077395542202","size":"610M","percent":85.8,"taskid":"33684635975","icon":"RMVB","livetime":"7\u5929","downurl":"","vod":"0","cdn":[],"format_img":"video","filesize":"640205218","verify":"","url":"bt:\/\/3547930B96AFA7B0A1CFCC80D516ADE97A34DAE0\/0","openformat":"movie","ext":"mkv","dirtitle":"[AngelSub][Guilty Crown][04][FULLHD][BIG5][x264_AC3].mkv"}]}})"""
    failed_testdata4 = "queryUrl(-1,'F7E1170B7E18E23EDCB89DA7E97E2A8EBCB99532','252805207','[\xe5\xa4\xa9\xe4\xbd\xbf\xe5\x8a\xa8\xe6\xbc\xab][111111]\xe5\x88\x9d\xe9\x9f\xb3\xe3\x83\x9f\xe3\x82\xaf2011 - 39\\'s LIVE IN SINGAPORE[320K].rar','0',new Array('[\xe5\xa4\xa9\xe4\xbd\xbf\xe5\x8a\xa8\xe6\xbc\xab][111111]\xe5\x88\x9d\xe9\x9f\xb3\xe3\x83\x9f\xe3\x82\xaf2011 - 39\\'s LIVE IN SINGAPORE[320K].rar'),new Array('241M'),new Array('252805207'),new Array('1'),new Array('RAR'),new Array('0'),'13211232980911486034.96672')"    
    testdata5 = """{"Result":{"Tid":"33684635655","Infoid":"3547930B96AFA7B0A1CFCC80D516ADE97A34DAE0","Record":[{"id":0,"title":"[AngelSub][Guilty Crown][04][FULLHD][BIG5][x264_AC3].mkv","download_status":"1","cid":"DCA5280E5072F48A2D0059F9BD00077395542202","size":"610M","percent":85.8,"taskid":"33684635975","icon":"RMVB","livetime":"7\u5929","downurl":"","vod":"0","cdn":[],"format_img":"video","filesize":"640205218","verify":"","url":"bt:\/\/3547930B96AFA7B0A1CFCC80D516ADE97A34DAE0\/0","openformat":"movie","ext":"mkv","dirtitle":"[AngelSub][Guilty Crown][04][FULLHD][BIG5][x264_AC3].mkv"}]}}"""
    import pprint
    pprint.pprint( parser_js_function_call(testdata) )
    pprint.pprint( parser_js_function_call(testdata1) )
    pprint.pprint( parser_js_function_call(testdata2) )
    pprint.pprint( parser_js_function_call(testdata3) )
    pprint.pprint( parser_js_function_call(failed_testdata4) )
    pprint.pprint( parser_js_function_call(testdata5) )

########NEW FILE########
__FILENAME__ = lixian_api
#/bin/usr/env python
#encoding: utf8
#author: binux<17175297.hk@gmail.com>

import re
import time
import json
import logging
import requests
import xml.sax.saxutils
from hashlib import md5
from random import random, sample
from urlparse import urlparse
from pprint import pformat
from jsfunctionParser import parser_js_function_call

DEBUG = logging.debug

class LiXianAPIException(Exception): pass
class NotLogin(LiXianAPIException): pass
class HTTPFetchError(LiXianAPIException): pass

def hex_md5(string):
    return md5(string).hexdigest()

def parse_url(url):
    url = urlparse(url)
    return dict([part.split("=") for part in url[4].split("&")])

def is_bt_task(task):
    return task.get("f_url", "").startswith("bt:")

def determin_url_type(url):
    url_lower = url.lower()
    if url_lower.startswith("file://"):
        return "local_file"
    elif url_lower.startswith("ed2k"):
        return "ed2k"
    elif url_lower.startswith("thunder"):
        return "thunder"
    elif url_lower.startswith("magnet"):
        return "magnet"
    elif url_lower.endswith(".torrent"):
        return "bt"
    else:
        return "normal"

title_fix_re = re.compile(r"\\([\\\"\'])")
def title_fix(title):
    return title_fix_re.sub(r"\1", title)

def unescape_html(html):
    return xml.sax.saxutils.unescape(html)

class LiXianAPI(object):
    DEFAULT_USER_AGENT = 'User-Agent:Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.2 (KHTML, like Gecko) Chrome/15.0.874.106 Safari/535.2'
    DEFAULT_REFERER = 'http://lixian.vip.xunlei.com/'
    def __init__(self, user_agent = DEFAULT_USER_AGENT, referer = DEFAULT_REFERER):
        self.session = requests.session()
        self.session.headers['User-Agent'] = user_agent
        self.session.headers['Referer'] = referer

        self.islogin = False
        self.task_url = None
        self.uid = 0
        self.username = ""

    LOGIN_URL = 'http://login.xunlei.com/sec2login/'
    def login(self, username, password, verifycode=None):
        self.username = username
        verifycode = verifycode or self._get_verifycode(username)
        login_data = dict(
                u = username,
                p = hex_md5(hex_md5(hex_md5(password))+verifycode.upper()),
                verifycode = verifycode,
                login_enable = 1,
                login_hour = 720)
        r = self.session.post(self.LOGIN_URL, login_data)
        r.raise_for_status()
        DEBUG(pformat(r.content))

        self.islogin = self._redirect_to_user_task() and self.check_login()
        return self.islogin

    @property
    def _now(self):
        return int(time.time()*1000)

    @property
    def _random(self):
        return str(self._now)+str(random()*(2000000-10)+10)

    CHECK_URL = 'http://login.xunlei.com/check?u=%(username)s&cachetime=%(cachetime)d'
    def _get_verifycode(self, username):
        r = self.session.get(self.CHECK_URL %
                {"username": username, "cachetime": self._now})
        r.raise_for_status()
        #DEBUG(pformat(r.content))

        verifycode_tmp = r.cookies['check_result'].split(":", 1)
        assert 2 >= len(verifycode_tmp) > 0, verifycode_tmp
        if verifycode_tmp[0] == '0':
            return verifycode_tmp[1]
        else:
            return None

    VERIFY_CODE = 'http://verify2.xunlei.com/image?cachetime=%s'
    def verifycode(self):
        r = self.session.get(self.VERIFY_CODE % self._now)
        return r.content

    REDIRECT_URL = "http://dynamic.lixian.vip.xunlei.com/login"
    def _redirect_to_user_task(self):
        r = self.session.get(self.REDIRECT_URL)
        r.raise_for_status()
        gdriveid = re.search(r'id="cok" value="([^"]+)"', r.content).group(1)
        if not gdriveid:
            return False
        self.gdriveid = gdriveid
        return True

    SHOWTASK_UNFRSH_URL = "http://dynamic.cloud.vip.xunlei.com/interface/showtask_unfresh"
    def _get_showtask(self, pagenum, st):
        self.session.cookies["pagenum"] = str(pagenum)
        r = self.session.get(self.SHOWTASK_UNFRSH_URL, params={
                                                "callback": "json1234567890",
                                                "t": self._now,
                                                "type_id": st,
                                                "page": 1,
                                                "tasknum": pagenum,
                                                "p": 1,
                                                "interfrom": "task"})
        r.raise_for_status()
        function, args = parser_js_function_call(r.content)
        DEBUG(pformat(args))
        assert args
        return args[0] if args else {}

    d_status = { 0: "waiting", 1: "downloading", 2: "finished", 3: "failed", 5: "paused" }
    d_tasktype = {0: "bt", 1: "normal", 2: "ed2k", 3: "thunder", 4: "magnet" }
    st_dict = {"unknow": 0, "downloading": 1, "finished": 2, "unknow": 3, "all": 4}
    def get_task_list(self, pagenum=10, st=4):
        st = 4 if (st==0) else st
        if isinstance(st, basestring):
            st = self.st_dict[st]
        raw_data = self._get_showtask(pagenum, st)['info']['tasks']
        for r in raw_data:
            r["task_id"] = int(r["id"])
            r["cid"] = r["cid"]
            r["url"] = r["url"]
            r["taskname"] = r["taskname"]
            r["task_type"] = self.d_tasktype.get(int(r["tasktype"]), 1)
            r["status"] = self.d_status.get(int(r["download_status"]), "waiting")
            r["process"] = r["progress"]
            r["size"] = int(r["ysfilesize"])
            r["format"]=r["openformat"]
        return raw_data

    QUERY_URL = "http://dynamic.cloud.vip.xunlei.com/interface/url_query"
    def bt_task_check(self, url):
        r = self.session.get(self.QUERY_URL, params={
                                  "callback": "queryUrl",
                                  "u": url,
                                  "random": self._random,
                                  "tcache": self._now})
        r.raise_for_status()
        #queryUrl(flag,infohash,fsize,bt_title,is_full,subtitle,subformatsize,size_list,valid_list,file_icon,findex,random)
        function, args = parser_js_function_call(r.content)
        DEBUG(pformat(args))
        if len(args) < 12:
            return {}
        if not args[2]:
            return {}
        result = dict(
                flag = args[0],
                cid = args[1],
                size = args[2],
                title = title_fix(args[3]),
                is_full = args[4],
                random = args[11])
        filelist = []
        for subtitle, subformatsize, size, valid, file_icon, findex in zip(*args[5:11]):
            tmp_file = dict(
                    title = subtitle,
                    formatsize = subformatsize,
                    size=size,
                    file_icon = file_icon,
                    ext = "",
                    index = findex,
                    valid = int(valid),
                    )
            filelist.append(tmp_file)
        result['filelist'] = filelist
        return result

    BT_TASK_COMMIT_URL = "http://dynamic.cloud.vip.xunlei.com/interface/bt_task_commit?callback=jsonp1234567890"
    def add_bt_task_with_dict(self, url, info):
        if not info: return False
        if info['flag'] == 0: return False
        data = dict(
                uid = self.uid,
                btname = info["title"],
                cid = info["cid"],
                goldbean = 0,
                silverbean = 0,
                tsize = info["size"],
                findex = "_".join(_file['index'] for _file in info["filelist"] if _file["valid"]),
                size = "_".join(_file['size'] for _file in info["filelist"] if _file["valid"]),
                #name = "undefined",
                o_taskid = 0,
                o_page = "task",
                class_id = 0)
        data["from"] = 0
        r = self.session.post(self.BT_TASK_COMMIT_URL, data)
        r.raise_for_status()
        DEBUG(pformat(r.content))
        if "jsonp1234567890" in r.content:
            return True
        return False

    def add_bt_task(self, url, add_all=True, title=None):
        info = self.bt_task_check(url)
        if not info: return False
        if title is not None:
            info['title'] = title
        if add_all:
            for _file in info['filelist']:
                _file['valid'] = 1
        return self.add_bt_task_with_dict(url, info)

    TASK_CHECK_URL = "http://dynamic.cloud.vip.xunlei.com/interface/task_check"
    def task_check(self, url):
        r = self.session.get(self.TASK_CHECK_URL, params={
                                   "callback": "queryCid",
                                   "url": url,
                                   "random": self._random,
                                   "tcache": self._now})
        r.raise_for_status()
        #queryCid(cid,gcid,file_size,avail_space,tname,goldbean_need,silverbean_need,is_full,random)
        function, args = parser_js_function_call(r.content)
        DEBUG(pformat(args))
        if len(args) < 8:
            return {}
        result = dict(
            cid = args[0],
            gcid = args[1],
            size = args[2],
            title = title_fix(args[4]),
            goldbean_need = args[5],
            silverbean_need = args[6],
            is_full = args[7],
            random = args[8])
        return result

    #TASK_COMMIT_URL = "http://dynamic.cloud.vip.xunlei.com/interface/task_commit?callback=ret_task&uid=%(uid)s&cid=%(cid)s&gcid=%(gcid)s&size=%(file_size)s&goldbean=%(goldbean_need)s&silverbean=%(silverbean_need)s&t=%(tname)s&url=%(url)s&type=%(task_type)s&o_page=task&o_taskid=0"
    TASK_COMMIT_URL = "http://dynamic.cloud.vip.xunlei.com/interface/task_commit"
    def add_task_with_dict(self, url, info):
        params = dict(
            callback="ret_task",
            uid=self.uid,
            cid=info['cid'],
            gcid=info['gcid'],
            size=info['size'],
            goldbean=0,
            silverbean=0,
            t=info['title'],
            url=url,
            type=0,
            o_page="task",
            o_taskid=0,
            class_id=0,
            database="undefined",
            time="Wed May 30 2012 14:22:01 GMT 0800 (CST)",
            noCacheIE=self._now)
        r = self.session.get(self.TASK_COMMIT_URL, params=params)
        r.raise_for_status()
        DEBUG(pformat(r.content))
        if "ret_task" in r.content:
            return True
        return False

    def add_task(self, url, title=None):
        info = self.task_check(url)
        if not info: return False
        if title is not None:
            info['title'] = title
        return self.add_task_with_dict(url, info)

    BATCH_TASK_CHECK_URL = "http://dynamic.cloud.vip.xunlei.com/interface/batch_task_check"
    def batch_task_check(self, url_list):
        data = dict(url="\r\n".join(url_list), random=self._random)
        r = self.session.post(self.BATCH_TASK_CHECK_URL, data=data)
        r.raise_for_status()
        DEBUG(pformat(r.content))
        m = re.search("""(parent.begin_task_batch_resp.*?)</script>""",
                      r.content)
        assert m
        function, args = parser_js_function_call(m.group(1))
        DEBUG(pformat(args))
        assert args
        return args[0] if args else {}

    BATCH_TASK_COMMIT_URL = "http://dynamic.cloud.vip.xunlei.com/interface/batch_task_commit?callback=jsonp1234567890"
    def add_batch_task_with_dict(self, info):
        data = dict(
                batch_old_taskid=",".join([0, ]*len(info)),
                batch_old_database=",".join([0, ]*len(info)),
                class_id=0,
                )
        data["cid[]"] = []
        data["url[]"] = []
        for i, task in enumerate(info):
            data["cid[]"].append(task.get("cid", ""))
            data["url[]"].append(task["url"])
        r = self.session.post(self.BATCH_TASK_COMMIT_URL, data=data)
        DEBUG(pformat(r.content))
        r.raise_for_status()
        if "jsonp1234567890" in r.content:
            return True
        return False

    def add_batch_task(self, url_list):
        # will failed of space limited
        info = self.batch_task_check(url_list)
        if not info: return False
        return self.add_batch_task_with_dict(info)

    TORRENT_UPDATE_URL = "http://dynamic.cloud.vip.xunlei.com/interface/torrent_upload"
    def _torrent_upload(self, filename, fp):
        files = {'filepath': (filename, fp)}
        r = self.session.post(self.TORRENT_UPDATE_URL, data={"random": self._random}, files=files)
        DEBUG(pformat(r.content))
        r.raise_for_status()
        m = re.search("""btResult =(.+);</script> btRtcode =""",
                      r.content)
        if not m:
            m = re.search(r"""(parent\.edit_bt_list.*?);\s*</script>""", r.content)
        if not m:
            return {}
        function, args = parser_js_function_call(m.group(1))
        DEBUG(pformat(args))
        assert args
        return args[0] if (args and args[0]['ret_value']) else {}

    def torrent_upload(self, filename, fp):
        info = self._torrent_upload(filename, fp)
        if not info: return {}
        result = dict(
                flag = info['ret_value'],
                cid = info['infoid'],
                is_full = info['is_full'],
                random = info.get('random', 0),
                title = info['ftitle'],
                size = info['btsize'],
                )
        filelist = []
        for _file in info['filelist']:
            tmp_file = dict(
                    title = _file['subtitle'],
                    formatsize = _file['subformatsize'],
                    size = _file['subsize'],
                    file_icon = _file['file_icon'],
                    ext = _file['ext'],
                    index = _file['findex'],
                    valid = _file['valid'],
                    )
            filelist.append(tmp_file)
        result['filelist'] = filelist

        return result

    def torrent_upload_by_path(self, path):
        import os.path
        with open(path, "rb") as fp:
            return self.torrent_upload(os.path.split(path)[1], fp)

    def add_bt_task_by_path(self, path, add_all=True, title=None):
        path = path.strip()
        if not path.lower().endswith(".torrent"):
            return False
        info = self.torrent_upload_by_path(path)
        if not info: return False
        if title is not None:
            info['title'] = title
        if add_all:
            for _file in info['filelist']:
                _file['valid'] = 1
        return self.add_bt_task_with_dict("", info)

    def add(self, url, title=None):
        url_type = determin_url_type(url)
        if url_type in ("bt", "magnet"):
            return self.add_bt_task(url, title=title)
        elif url_type in ("normal", "ed2k", "thunder"):
            return self.add_task(url, title=title)
        elif url_type == "local_file":
            return self.add_bt_task_by_path(url[7:])
        else:
            return self.add_batch_task([url, ])

    FILL_BT_LIST = "http://dynamic.cloud.vip.xunlei.com/interface/fill_bt_list"
    def _get_bt_list(self, tid, cid):
        self.session.cookies["pagenum"] = str(2000)
        r = self.session.get(self.FILL_BT_LIST, params=dict(
                                                    callback="fill_bt_list",
                                                    tid = tid,
                                                    infoid = cid,
                                                    g_net = 1,
                                                    p = 1,
                                                    uid = self.uid,
                                                    noCacheIE = self._now))
        r.raise_for_status()
        # content starts with \xef\xbb\xbf, what's that?
        function, args = parser_js_function_call(r.content[3:])
        DEBUG(pformat(args))
        if not args:
            return {}
        if isinstance(args[0], basestring):
            raise LiXianAPIException, args[0]
        return args[0].get("Result", {})

    def get_bt_list(self, tid, cid):
        raw_data = self._get_bt_list(tid, cid)
        assert cid == raw_data.get("Infoid")
        result = []
        for r in raw_data.get("Record", []):
            tmp = dict(
                    task_id=int(r['taskid']),
                    url=r['url'],
                    lixian_url=r['downurl'],
                    cid=r['cid'],
                    title=r['title'],
                    status=self.d_status.get(int(r['download_status'])),
                    dirtitle=r['dirtitle'],
                    process=r['percent'],
                    size=int(r['filesize']),
                    format=r['openformat'],
                )
            result.append(tmp)
        return result

    TASK_DELAY_URL = "http://dynamic.cloud.vip.xunlei.com/interface/task_delay?taskids=%(ids)s&noCacheIE=%(cachetime)d"
    def delay_task(self, task_ids):
        tmp_ids = [str(x)+"_1" for x in task_ids]
        r = self.session.get(self.TASK_DELAY_URL % dict(
                            ids = ",".join(tmp_ids),
                            cachetime = self._now))
        r.raise_for_status()
        function, args = parser_js_function_call(r.content)
        DEBUG(pformat(args))
        assert args
        if args and args[0].get("result") == 1:
            return True
        return False

    TASK_DELETE_URL = "http://dynamic.cloud.vip.xunlei.com/interface/task_delete"
    def delete_task(self, task_ids):
        r = self.session.post(self.TASK_DELETE_URL, params = {
                                                      "type": "0",
                                                      "t": self._now}
                                                  , data = {
                                                      "databases": "0",
                                                      "taskids": ",".join(map(str, task_ids))})
        r.raise_for_status()
        function, args = parser_js_function_call(r.content)
        DEBUG(pformat(args))
        assert args
        if args and args[0].get("result") == 1:
            return True
        return False

    TASK_PAUSE_URL = "http://dynamic.cloud.vip.xunlei.com/interface/task_pause"
    def task_pause(self, task_ids):
        r = self.session.get(self.TASK_PAUSE_URL, params = {
                                                    "tid": ",".join(map(str, task_ids)),
                                                    "uid": self.uid,
                                                    "noCacheIE": self._now
                                                    })
        r.raise_for_status()
        DEBUG(pformat(r.content))
        if "pause_task_resp" in r.content:
            return True
        return False

    REDOWNLOAD_URL = "http://dynamic.cloud.vip.xunlei.com/interface/redownload?callback=jsonp1234567890"
    def redownload(self, task_ids):
        r = self.session.post(self.REDOWNLOAD_URL, data = {
                                         "id[]": task_ids,
                                         "cid[]": ["",]*len(task_ids),
                                         "url[]": ["",]*len(task_ids),
                                         "taskname[]": ["",]*len(task_ids),
                                         "download_status[]": [5,]*len(task_ids),
                                         "type": 1,
                                         })
        r.raise_for_status()
        DEBUG(pformat(r.content))
        if "jsonp1234567890(1)" in r.content:
            return True
        return False


    GET_WAIT_TIME_URL = "http://dynamic.cloud.vip.xunlei.com/interface/get_wait_time"
    def get_wait_time(self, task_id, key=None):
        params = dict(
            callback = "download_check_respo",
            t = self._now,
            taskid = task_id)
        if key:
            params["key"] = key
        r = self.session.get(self.GET_WAIT_TIME_URL, params=params)
        r.raise_for_status()
        function, args = parser_js_function_call(r.content)
        DEBUG(pformat(args))
        assert args
        return args[0] if args else {}

    GET_FREE_URL = "http://dynamic.cloud.vip.xunlei.com/interface/free_get_url"
    def get_free_url(self, nm_list=[], bt_list=[]):
        #info = self.get_wait_time(task_id)
        #if info.get("result") != 0:
        #    return {}
        info = {}
        params = dict(
             key=info.get("key", ""),
             list=",".join((str(x) for x in nm_list+bt_list)),
             nm_list=",".join((str(x) for x in nm_list)),
             bt_list=",".join((str(x) for x in bt_list)),
             uid=self.uid,
             t=self._now)
        r = self.session.get(self.GET_FREE_URL, params=params)
        r.raise_for_status()
        function, args = parser_js_function_call(r.content)
        DEBUG(pformat(args))
        assert args
        return args[0] if args else {}

    GET_TASK_PROCESS = "http://dynamic.cloud.vip.xunlei.com/interface/task_process"
    def get_task_process(self, nm_list=[], bt_list=[], with_summary=False):
        params = dict(
             callback="rebuild",
             list=",".join((str(x) for x in nm_list+bt_list)),
             nm_list=",".join((str(x) for x in nm_list)),
             bt_list=",".join((str(x) for x in bt_list)),
             uid=self.uid,
             noCacheIE=self._now,
             )
        r = self.session.get(self.GET_TASK_PROCESS, params=params)
        r.raise_for_status()
        function, args = parser_js_function_call(r.content)
        DEBUG(pformat(args))
        assert args
        args = args[0]

        result = []
        for task in args.get("Process", {}).get("Record", []) if args else []:
            status = None
            if task.get('fsize', u'0B') == u'0B':
                # it's a task own by other account
                status = 'failed'
            tmp = dict(
                    task_id = int(task['tid']),
                    cid = task.get('cid', None),
                    status = status or self.d_status.get(int(task['download_status']), "waiting"),
                    process = task['percent'],
                    leave_time = task['leave_time'],
                    speed = int(task['speed']),
                    lixian_url = task.get('lixian_url', None),
                  )
            result.append(tmp)
        if with_summary:
            return result, args.get("Process", {}).get("Task", {})
        else:
            return result

    SHARE_URL = "http://dynamic.sendfile.vip.xunlei.com/interface/lixian_forwarding"
    def share(self, emails, tasks, msg="", task_list=None):
        if task_list is None:
            task_list = self.get_task_list()
        payload = []
        i = 0
        for task in task_list:
            if task["task_id"] in tasks:
                if task["task_type"] == "bt":
                    #TODO
                    pass
                else:
                    if not task["lixian_url"]: continue
                    url_params = parse_url(task['lixian_url'])
                    tmp = {
                        "cid_%d" % i : task["cid"],
                        "file_size_%d" % i : task["size"],
                        "gcid_%d" % i : url_params.get("g", ""),
                        "url_%d" % i : task["url"],
                        "title_%d" % i : task["taskname"],
                        "section_%d" % i : url_params.get("scn", "")}
                    i += 1
                    payload.append(tmp)
        data = dict(
                uid = self.uid,
                sessionid = self.get_cookie("sessionid"),
                msg = msg,
                resv_email = ";".join(emails),
                data = json.dumps(payload))
        r = self.session.post(self.SHARE_URL, data)
        r.raise_for_status()
        #forward_res(1,"ok",649513164808429);
        function, args = parser_js_function_call(r.content)
        DEBUG(pformat(args))
        assert args
        if args and args[0] == 1:
            return True
        return False

    CHECK_LOGIN_URL = "http://dynamic.cloud.vip.xunlei.com/interface/verify_login"
    TASK_URL = "http://dynamic.cloud.vip.xunlei.com/user_task?userid=%s"
    def check_login(self):
        r = self.session.get(self.CHECK_LOGIN_URL)
        r.raise_for_status()
        function, args = parser_js_function_call(r.content)
        DEBUG(pformat(args))
        assert args
        if args and args[0].get("result") == 1:
            self.uid = int(args[0]["data"].get("userid"))
            self.isvip = args[0]["data"].get("vipstate")
            self.nickname = args[0]["data"].get("nickname")
            self.username = args[0]["data"].get("usrname")
            self.task_url = self.TASK_URL % self.uid
            return True
        return False

    def get_cookie(self, attr=""):
        cookies = self.session.cookies
        if attr:
            return cookies[attr]
        return cookies

    LOGOUT_URL = "http://login.xunlei.com/unregister?sessionid=%(sessionid)s"
    def logout(self):
        sessionid = self.get_cookie("sessionid")
        if sessionid:
            self.session.get(self.LOGOUT_URL % {"sessionid": sessionid})
        self.session.cookies.clear()
        self.islogin = False
        self.task_url = None

# functions for vod.lixian.xunlei.com

    VOD_REDIRECT_PLAY_URL = "http://dynamic.vod.lixian.xunlei.com/play"
    def vod_redirect_play(self, url, fp=None):
        params = {
                "action": "http_sec",
                "location": "list",
                "from": "vlist",
                "go": "check",
                "furl": url,
                }
        if fp:
            files = {'filepath': (url, fp)}
        else:
            files = None
        r = self.session.post(self.VOD_REDIRECT_PLAY_URL, params=params, files=files)
        r.raise_for_status()
        DEBUG(pformat(r.content))
        m = re.search("""top.location.href="(.*?)";""",
                      r.content)
        assert m
        return m.group(1)

    VOD_GET_PLAY_URL = "http://dynamic.vod.lixian.xunlei.com/interface/get_play_url"
    def vod_get_play_url(self, url, bindex=-1):
        params = {
                "callback": "jsonp1234567890",
                "t": self._now,
                "check": 0,
                "url": url,
                "format": 225536,  #225536:g, 282880:p
                "bindex": bindex,
                "isipad": 0,
                }
        r = self.session.get(self.VOD_GET_PLAY_URL, params=params, headers={'referer': 'http://222.141.53.5/iplay.html'})
        r.raise_for_status()
        function, args = parser_js_function_call(r.content)
        DEBUG(pformat(args))
        assert args
        return args[0]

    VOD_CHECK_VIP = "http://dynamic.vod.lixian.xunlei.com/interface/check_vip"
    def vod_check_vip(self):
        pass

    VOD_GET_BT_LIST = "http://dynamic.vod.lixian.xunlei.com/interface/get_bt_list"
    def vod_get_bt_list(self, cid):
        pass

    VOD_GET_LIST_PIC = "http://dynamic.vod.lixian.xunlei.com/interface/get_list_pic"
    def vod_get_list_pic(self, gcids):
        params = {
                "callback": "jsonp1234567890",
                "t": self._now,
                "ids": "", # urlhash
                "gcid": ",".join(gcids),
                "rate": 0
                }
        r = self.session.get(self.VOD_GET_LIST_PIC, params=params)
        r.raise_for_status()
        function, args = parser_js_function_call(r.content)
        DEBUG(pformat(args))
        assert args
        return args[0]

    VOD_GET_BT_PIC = "http://i.vod.xunlei.com/req_screenshot?jsonp=%(jsonp)s&info_hash=%(info_hash)s&req_list=%(req_list)s&t=%(t)s"
    def vod_get_bt_pic(self, cid, bindex=[]):
        """
        get gcid and shotcut of movice of bt task
        * max length of bindex is 18
        """
        params = {
                "jsonp" : "jsonp1234567890",
                "t" : self._now,
                "info_hash" : cid,
                "req_list" : "/".join(map(str, bindex)),
                }
        r = self.session.get(self.VOD_GET_BT_PIC % params)
        r.raise_for_status()
        function, args = parser_js_function_call(r.content)
        DEBUG(pformat(args))
        assert args
        return args[0].get("resp", {})

    VOD_GET_PROCESS = "http://dynamic.vod.lixian.xunlei.com/interface/get_progress/"
    def vod_get_process(self, url_list):
        params = {
                "callback": "jsonp1234567890",
                "t": self._now,
                "url_list": "####".join(url_list),
                "id_list": "####".join(["list_bt_%d" % x for x in range(len(url_list))]),
                "palform": 0,
                }
        r = self.session.get(self.VOD_GET_PROCESS, params=params)
        r.raise_for_status()
        function, args = parser_js_function_call(r.content)
        DEBUG(pformat(args))
        assert args
        return args[0]


# functions for kuai.xunlei.com

    WEBFILEMAIL_INTERFACE_URL = "http://kuai.xunlei.com/webfilemail_interface"
    def webfilemail_url_analysis(self, url):
        params = {
                "action": "webfilemail_url_analysis",
                "url": url,
                "cachetime": self._now,
                }
        r = self.session.get(self.WEBFILEMAIL_INTERFACE_URL, params=params)
        r.raise_for_status()
        function, args = parser_js_function_call(r.content)
        DEBUG(pformat(args))
        assert args
        return args[0]

    def is_miaoxia(self, url, bindex=[]):
        if bindex:
            bindex = sample(bindex, 15) if len(bindex) > 15 else bindex
            ret = self.vod_get_bt_pic(url, bindex)
            if not ret.get("screenshot_list"):
                return False
            for each in ret["screenshot_list"]:
                if not each.get("gcid"):
                    return False
            return True
        else:
            info = self.webfilemail_url_analysis(url)
            if info['result'] == '0':
                return True
            return False

    VIP_INFO_URL = "http://dynamic.vip.xunlei.com/login/asynlogin_contr/asynProxy/"
    def get_vip_info(self):
        params = {
                "cachetime": self._now,
                "callback": "jsonp1234567890"
                }
        r = self.session.get(self.VIP_INFO_URL, params=params)
        r.raise_for_status()
        function, args = parser_js_function_call(r.content)
        DEBUG(pformat(args))
        assert args
        return args[0]

########NEW FILE########
__FILENAME__ = plugin_task_bot
# -*- encoding: utf-8 -*-
# author: binux<17175297.hk@gmail.com>

import logging
import requests
import HTMLParser
from flexget.plugin import register_plugin, PluginError
from flexget import validator

log = logging.getLogger("task_bot")
unescape = HTMLParser.HTMLParser().unescape

class PluginTaskBot(object):
    def __init__(self):
        pass

    def validator(self):
        root = validator.factory()
        advanced = root.accept("dict")
        advanced.accept("text", key="host")
        advanced.accept("text", key="tags")
        return root

    def prepare_config(self, config):
        if "host" not in config:
            config['host'] = "localhost:8880"
        if "tags" not in config:
            config['tags'] = ""
        return config

    def on_feed_output(self, feed, config):
        for entry in feed.accepted:
            if feed.manager.options.test:
                log.info("Would add %s to %s" % (entry['url'], config['host']))
                continue
            data = dict(
                    url = entry['url'],
                    title = unescape(entry['title']),
                    tags = config['tags'],
                    _xsrf = "1234567890"
                    )
            try:
                r = requests.post(config['host'], data=data, cookies={"_xsrf": "1234567890"})
            except Exception, e:
                feed.fail(entry, "Add task error: %s" % e)
                return
            log.info('"%s" added to %s' % (entry['title'], config['host']))

register_plugin(PluginTaskBot, "task_bot", api_ver=2)

########NEW FILE########
__FILENAME__ = plugin_xunlei_lixian
# -*- encoding: utf-8 -*-
# author: binux<17175297.hk@gmail.com>

import logging
from flexget.plugin import register_plugin, PluginError
from flexget import validator
from flexget.entry import Entry
from lixian_api import LiXianAPI

log = logging.getLogger("transmission")

class XunleiLixianBase(object):
    def __init__(self):
        self.xunlei_client_cache = dict()

    def gen_cache_key(self, config):
        return "username:%(username)s\npassword:%(password)s" % config

    def create_xunlei_client(self, config):
        client = LiXianAPI()
        if client.login(config['username'], config['password']):
            self.xunlei_client_cache[self.gen_cache_key(config)] = client
        else:
            raise PluginError("Cannot login to lixian.xunlei.com. Please check you username and password")
        return client

    def get_xunlei_client(self, config):
        cache_key = self.gen_cache_key(config)
        if cache_key in self.xunlei_client_cache:
            return self.xunlei_client_cache[cache_key]
        else:
            return self.create_xunlei_client(config)

class PluginFromXunleiLixian(XunleiLixianBase):
    def validator(self):
        root = validator.factory()
        advanced = root.accept("dict")
        advanced.accept("text", key="username")
        advanced.accept("text", key="password")
        advanced.accept("integer", key="limit")
        advanced.accept("any", key="fields")
        return root

    def prepare_config(self, config):
        if "username" not in config:
            raise PluginError("username is expected in PluginXunleiLixian")
        if "password" not in config:
            raise PluginError("password is expected in PluginXunleiLixian")
        if "limit" not in config:
            config['limit'] = 30
        if "fields" not in config:
            config['fields'] = {}
        return config

    def on_feed_input(self, feed, config):
        entries = []
        client = self.get_xunlei_client(config)
        tasks = client.get_task_list(config['limit'], 2)
        for task in tasks:
            if task['status'] != "finished":
                continue
            elif task['lixian_url']:
                entry = Entry(title=task['taskname'],
                              url=task['lixian_url'],
                              cookie="gdriveid=%s;" % client.gdriveid,
                              taskname=".",
                              size=task['size'],
                              format=task['format'],
                              fields=config['fields'],
                              )
                entries.append(entry)
            elif task['task_type'] in ("bt", "magnet"):
                files = client.get_bt_list(task['task_id'], task['cid'])
                for file in files:
                    if not file['lixian_url']:
                        continue
                    entry = Entry(title=file['dirtitle'],
                                  url=file['lixian_url'],
                                  cookie="gdriveid=%s;" % client.gdriveid,
                                  taskname=task['taskname'],
                                  size=file['size'],
                                  format=file['format'],
                                  fields=config['fields'],
                                  )
                    entries.append(entry)
        return entries

class PluginXunleiLixian(XunleiLixianBase):
    def validator(self):
        root = validator.factory()
        advanced = root.accept("dict")
        advanced.accept("text", key="username")
        advanced.accept("text", key="password")
        return root

    def prepare_config(self, config):
        if "username" not in config:
            raise PluginError("username is expected in PluginXunleiLixian")
        if "password" not in config:
            raise PluginError("password is expected in PluginXunleiLixian")
        return config

    def on_pocess_end(self, feed, config):
        for key, client in self.xunlei_client_cache.iteritem():
            client.logout()

    def on_feed_output(self, feed, config):
        if not feed.manager.options.test:
            client = self.get_xunlei_client(config)
        for entry in feed.accepted:
            if feed.manager.options.test:
                log.info("Would add %s to lixian.xunlei.com" % entry['url'])
                continue
            if not client.add(entry['url'], entry['title']):
                feed.fail(entry, "Add task error")
            else:
                log.info('"%s" added to lixian.xunlei.com' % entry['title'])

register_plugin(PluginFromXunleiLixian, "from_xunlei_lixian", api_ver=2)
register_plugin(PluginXunleiLixian, "xunlei_lixian", api_ver=2)

########NEW FILE########
__FILENAME__ = task_manager
# -*- encoding: utf-8 -*-
# author: binux<17175297.hk@gmail.com>

from time import time
from datetime import datetime
from collections import deque
from libs.lixian_api import LiXianAPI, determin_url_type
from tornado.options import options

class TaskManager(object):
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self._last_check_login = 0

        self._tasks = dict()
        self._task_list = deque()
        self._task_urls = set()
        self._last_update_task_list = 0

        self._file_list = dict()

        self._xunlei = LiXianAPI()
        self.islogin = self._xunlei.login(self.username, self.password)
        self._last_check_login = time()

    @property
    def xunlei(self):
        if self._last_check_login + options.check_interval < time():
            if not self._xunlei.check_login():
                self._xunlei.logout()
                self.islogin = self._xunlei.login(self.username, self.password)
            self._last_check_login = time()
        return self._xunlei

    @property
    def gdriveid(self):
        return self.xunlei.gdriveid

    def _update_task_list(self, limit=10, st=0, ignore=False):
        tasks = self.xunlei.get_task_list(limit, st)
        for task in tasks[::-1]:
            task['last_update_time'] = datetime.now()
            if task['task_id'] not in self._tasks:
                if ignore: continue
                task['first_seen'] = datetime.now()
                self._task_list.appendleft(task)
                self._tasks[task['task_id']] = task
                self._task_urls.add(task['url'])
            else:
                self._tasks[task['task_id']].update(task)

    def get_task(self, task_id):
        if task_id in self._tasks:
            return self._tasks[task_id]
        else:
            return None

    def get_task_list(self, start_task_id=0, limit=30):
        if self._last_update_task_list + options.finished_task_check_interval < time():
            self._update_task_list(options.task_list_limit)
            self._last_update_task_list = time()

        # skip
        pos = iter(self._task_list)
        if start_task_id:
            for task in pos:
                if task['task_id'] == start_task_id:
                    break

        result = []
        count = 0
        need_update = set()
        for task in pos:
            if count >= limit: break
            result.append(task)
            count += 1

            if task['status'] != "finished" and task['last_update_time'] \
                    + options.downloading_task_check_interval < datetime.now():
                need_update.add(task['task_id'])

        if need_update:
            self._update_task_list(options.task_list_limit, "downloading")

        # if updated downloading list and hadn't find task which is
        # needed to update, maybe it's finished.
        # FIXME: try to get info of a specified task
        for task_id in need_update:
            task = self.get_task(task_id)
            if task['last_update_time'] + options.downloading_task_check_interval < datetime.now():
                task['status'] = "finished"
                task['process'] = 100
                if task['task_id'] in self._file_list:
                    del self._file_list[task['task_id']]

        return result

    def get_file_list(self, task_id):
        task = self.get_task(task_id)
        if not task: return {}

        if task_id in self._file_list:
            file_list = self._file_list[task_id]
            if file_list["last_update_time"] \
                    + self._get_check_interval(task['status']) > datetime.now():
                return file_list["files"]

        if task['task_type'] == "normal":
            files = []
            tmp_file = dict(
                    task_id = task['task_id'],
                    url = task['url'],
                    lixian_url = task['lixian_url'],
                    title = task['taskname'],
                    status = task['status'],
                    dirtitle = task['taskname'],
                    process = task['process'],
                    size = task['size'],
                    format = task['format']
                    )
            files.append(tmp_file)
        elif task['task_type'] in ("bt", "magnet"):
            files = self.xunlei.get_bt_list(task['task_id'], task['cid'])

        self._file_list[task_id] = {"last_update_time": datetime.now(), "files": files}
        return files

    def add_task(self, url):
        if url in self._task_urls:
            return False
        url_type = determin_url_type(url)

        if url_type in ("bt", "magnet"):
            result = self.xunlei.add_bt_task(url)
        elif url_type in ("normal", "ed2k", "thunder"):
            result = self.xunlei.add_task(url)
        else:
            result = self.xunlei.add_batch_task([url, ])

        if result:
            self._update_task_list(5)
        return result

    def _get_check_interval(self, status):
        if status == "finished":
            return options.finished_task_check_interval
        else:
            return options.downloading_task_check_interval

########NEW FILE########
__FILENAME__ = tools
# -*- encoding: utf-8 -*-
# binux<17175297.hk@gmail.com>

import os
import struct
import hashlib

def parse_fid(fid):
    cid, size, gcid = struct.unpack("<20sq20s", fid.decode("base64"))
    return cid.encode("hex").upper(), size, gcid.encode("hex").upper()

def gen_fid(cid, size, gcid):
    return struct.pack("<20sq20s", cid.decode("hex"), size, gcid.decode("hex")).encode("base64").replace("\n", "")

def gcid_hash_file(path):
    h = hashlib.sha1()
    size = os.path.getsize(path)
    psize = 0x40000
    while size / psize > 0x200:
        psize = psize << 1
    with open(path, 'rb') as stream:
        data = stream.read(psize)
        while data:
            h.update(hashlib.sha1(data).digest())
            data = stream.read(psize)
    return h.hexdigest().upper()

def cid_hash_file(path):
    h = hashlib.sha1()
    size = os.path.getsize(path)
    with open(path, 'rb') as stream:
        if size < 0xF000:
            h.update(stream.read())
        else:
            h.update(stream.read(0x5000))
            stream.seek(size/3)
            h.update(stream.read(0x5000))
            stream.seek(size-0x5000)
            h.update(stream.read(0x5000))
    return h.hexdigest().upper()

thunder_filename_mask = "6131E45F00000000".decode("hex")
def thunder_filename_encode(filename, encoding="gbk"):
    if isinstance(filename, unicode):
        filename = filename.encode(encoding)
    result = ["01", ]
    for i, word in enumerate(filename):
        mask = thunder_filename_mask[i%len(thunder_filename_mask)]
        result.append("%02X" % (ord(word)^ord(mask)))
    while len(result) % 8 != 1:
        mask = thunder_filename_mask[len(result)%len(thunder_filename_mask)-1]
        result.append("%02X" % ord(mask))
    return "".join(result)

def thunder_filename_decode(code, encoding="gbk"):
    assert code.startswith("01")
    result = []
    for i, word in enumerate(code[2:].decode("hex")):
        mask = thunder_filename_mask[i%len(thunder_filename_mask)]
        result.append(chr(ord(word)^ord(mask)))
    result = "".join(result).rstrip("\0")
    return result.decode(encoding)

def encode_thunder(url):
    return "thunder://"+("AA"+url+"ZZ").encode("base64").replace("\n", "")

def decode_thunder(url):
    assert url.lower().startswith("thunder://"), "should startswith 'thunder://'"
    url = url[10:].decode("base64")
    assert url.startswith("AA") and url.endswith("ZZ"), "unknow format"
    return url[2:-2]

def encode_flashget(url):
    return "Flashget://"+("[FLASHGET]"+url+"[FLASHGET]").encode("base64").replace("\n", "")

def decode_flashget(url):
    assert url.lower().startswith("flashget://"), "should startswith 'Flashget://'"
    url = url[11:].decode("base64")
    assert url.startswith("[FLASHGET]") and url.endswith("[FLASHGET]"), "unknow format"
    return url[10:-10]

def encode_qqdl(url):
    return "qqdl://"+url.encode("base64").replace("\n", "")

def decode_qqdl(url):
    assert url.lower().startswith("qqdl://"), "should startswith 'qqdl://'"
    return url[7:].decode("base64")

def url_unmask(url):
    url_lower = url.lower()
    try:
        if url_lower.startswith("thunder://"):
            return decode_thunder(url)
        elif url_lower.startswith("flashget://"):
            return decode_flashget(url)
        elif url_lower.startswith("qqdl://"):
            return decode_qqdl(url)
        else:
            return url
    except:
        return url

########NEW FILE########
__FILENAME__ = user_manager
# -*- encoding: utf8 -*-

import db
from db.util import *
from libs.cache import mem_cache

default_group_permission = {
        "add_task": True,
        "add_anonymous_task": True,
        "add_task_limit_size": 20,
        "add_task_limit": True,
        "mod_task": True,
        "view_tasklist": True,
        "view_invalid": False,
        "need_miaoxia": True,
        "admin": False,
}
not_login_permission = {
        "add_task": False,
        "add_anonymous_task": False,
        "add_task_limit_size": 0,
        "add_task_limit": True,
        "mod_task": False,
        "view_tasklist": True,
        "view_invalid": False,
        "need_miaoxia": True,
        "admin": False,
}
group_permission = {
        None: {
        },
        "": {
        },
        "user": {
        },
        "admin": {
            "add_task_limit": False,
            "view_invalid": True,
            "need_miaoxia": False,
            "admin": True,
        },
        "block": {
            "add_task": False,
            "add_anonymous_task": True,
            "add_task_limit_size": 10,
            "mod_task": False,
        },
}
permission_mark = {
        "add_task": 1,
        "add_anonymous_task": 2,
        "add_task_limit": 64,
        "mod_task": 4,
        "view_invalid": 8,
        "need_miaoxia": 16,
        "admin": 32,
        }

for group, permission_dict in group_permission.iteritems():
    tmp = dict(default_group_permission)
    tmp.update(permission_dict)
    group_permission[group] = tmp

class UserManager(object):
    def __init__(self):
        self.session = db.Session()
        self.add_task_limit_used = {}
        self.reload_limit = {}

    @sqlalchemy_rollback
    def get_user_by_id(self, _id):
        return self.session.query(db.User).get(_id)

    @sqlalchemy_rollback
    def get_user_email_by_id(self, _id):
        if _id == 0:
            return "bot@localhost"
        return self.session.query(db.User.email).filter(db.User.id==_id).scalar()

    @sqlalchemy_rollback
    def get_user(self, email):
        if not email: return None
        return self.session.query(db.User).filter(db.User.email==email).scalar()

    @sqlalchemy_rollback
    def update_user(self, email, name):
        self.reset_add_task_limit(email)
        user = self.get_user(email) or db.User()
        user.email = email
        user.name = name
        self.session.add(user)
        self.session.commit()

    @mem_cache(expire=60*60)
    def get_id(self, email):
        if email == "bot@localhost":
            return 0
        user = self.get_user(email)
        if user:
            return user.id
        return None

    @mem_cache(expire=60*60)
    def get_name(self, email):
        if email == "bot@localhost":
            return "bot"
        user = self.get_user(email)
        if user:
            return user.name
        return None

    @mem_cache(expire=30*60)
    def get_group(self, email):
        if email == "bot@localhost":
            return "admin"
        user = self.get_user(email)
        if user:
            return user.group
        return None

    def get_add_task_limit(self, email):
        if not self.check_permission(email, "add_task_limit"):
            return 1
        limit = group_permission.get(self.get_group(email), default_group_permission)["add_task_limit_size"]
        used = self.add_task_limit_used.get(email, 0)
        return limit - used

    def incr_add_task_limit(self, email):
        self.add_task_limit_used[email] = self.add_task_limit_used.setdefault(email, 0) + 1

    def reset_add_task_limit(self, email):
        if email in self.add_task_limit_used:
            if self.add_task_limit_used[email] > self.reload_limit.get(email, 0):
                self.reload_limit[email] = self.reload_limit.setdefault(email, 0) + 1
            self.add_task_limit_used[email] = self.reload_limit.get(email, 0)

    def reset_all_add_task_limit(self):
        self.add_task_limit_used = {}
        self.reload_limit = {}

    @mem_cache(expire=30*60)
    def get_permission(self, email):
        user = self.get_user(email)
        if user:
            return user.permission or 0
        return 0

    @mem_cache(expire=60)
    def check_permission(self, email, permission):
        if email is None:
            return not_login_permission[permission]
        return group_permission.get(self.get_group(email), default_group_permission)[permission] or (self.get_permission(email) & permission_mark[permission])

########NEW FILE########
__FILENAME__ = util
# -*- encoding: utf-8 -*-
# author: binux<17175297.hk@gmail.com>

import logging
import traceback
import thread
import tornado
from multiprocessing import Pipe

units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
def format_size(request, size):
    i = 0
    while size > 1024:
        size /= 1024
        i += 1
    return "%d%s" % (size, units[i])

d_status = {
        "finished": u"完成",
        "downloading": u"下载中",
        "waiting": u"队列中",
        "failed": u"下载失败",
        "paused": u"暂停中",
}
def format_download_status(request, status):
    return d_status.get(status, u"未知状态")

def email2name(request, email):
    return request.user_manager.get_name(email)

def email2id(request, email):
    return request.user_manager.get_id(email)

ui_methods = {
        "format_size": format_size,
        "format_status": format_download_status,
        "email2name": email2name,
        "email2id": email2id,
}

class AsyncProcessMixin(object):
    def call_subprocess(self, func, callback=None, args=[], kwargs={}):
        self.ioloop = tornado.ioloop.IOLoop.instance()
        self.pipe, child_conn = Pipe()

        def wrap(func, pipe, args, kwargs):
            try:
                pipe.send(func(*args, **kwargs))
            except Exception, e:
                logging.error(traceback.format_exc())
                pipe.send(e)
        
        self.ioloop.add_handler(self.pipe.fileno(),
                  self.async_callback(self.on_pipe_result, callback),
                  self.ioloop.READ)
        thread.start_new_thread(wrap, (func, child_conn, args, kwargs))

    def on_pipe_result(self, callback, fd, result):
        try:
            ret = self.pipe.recv()
            if isinstance(ret, Exception):
                raise ret

            if callback:
                callback(ret)
        finally:
            self.ioloop.remove_handler(fd)

########NEW FILE########
__FILENAME__ = vip_pool
# -*- encoding: utf-8 -*-
# author: binux<17175297.hk@gmail.com>

import logging
import random

class VIPool:
    def __init__(self):
        self.pool = {}

    def parser(self, line):
        try:
            uid, gdriveid, tid = line.split(":", 2)
            return {"uid": int(uid),
                    "gdriveid": gdriveid,
                    "tid": int(tid)
                   }
        except:
            logging.error("unknow vip format: %s" % line)
        return {}

    def parser_line(self, line):
        ret = self.parser(line)
        if ret:
            self.pool[ret["gdriveid"]] = ret

    def parser_mline(self, lines):
        for line in lines.split("\n"):
            line = line.strip()
            self.parser_line(line)

    def get_vip(self, gdriveid=None):
        if not self.pool:
            return None

        if not gdriveid:
            gdriveid = random.choice(self.pool.keys())
        elif ":" in gdriveid:
            ret = self.parser(gdriveid)
            if ret:
                return ret
        elif gdriveid not in self.pool:
            gdriveid = random.choice(self.pool.keys())

        return self.pool[gdriveid]

    def serialize(self):
        result = []
        for each in self.pool.values():
            result.append("%(uid)s:%(gdriveid)s:%(tid)s" % each)
        return "\n".join(result)

########NEW FILE########
__FILENAME__ = main
#/usr/bin/env python
# -*- encoding: utf8 -*-
# author: binux<17175297.hk@gmail.com>

import os
import tornado
import logging
from time import time
from tornado import web
from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.options import define, options
from tornado.httpserver import HTTPServer

define("f", default="", help="config file path")
define("debug", default=True, help="debug mode")
define("port", default=8880, help="the port tornado listen to")
define("bind_ip", default="0.0.0.0", help="the bind ip")
define("username", help="xunlei vip login name")
define("password", help="xunlei vip password")
define("ga_account", default="", help="account of google analytics")
define("site_name", default="LOLI.LU", help="site name used in description")
define("cookie_secret", default="61oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o",
        help="key for HMAC")
define("check_interval", default=60*60,
        help="the interval of checking login status")
define("cache_enabled", default=True,
        help="enable mem cache")
define("cross_userscript", default="http://userscripts.org/scripts/show/117745",
        help="the web url of cross cookie userscirpt")
define("cross_cookie_version", default="0.35",
        help="cross cookie user script version")
define("cross_userscript_local", default="/static/cross-cookie.user.js",
        help="the local path of cross cookie userscirpt")
define("cross_cookie_url", default="http://vip.xunlei.com/gen/yuanxun/gennew/newyx.html",
        help="the url to insert to")
define("cookie_str", default="gdriveid=%s; path=/; domain=.vip.xunlei.com",
        help="the cookie insert to cross path")
define("finished_task_check_interval", default=60*60,
        help="the interval of getting the task list")
define("downloading_task_check_interval", default=5*60,
        help="the interval of getting the downloading task list")
define("task_list_limit", default=500,
        help="the max limit of get task list each time")
define("always_update_lixian_url", default=False,
        help="always update lixian url")
define("database_echo", default=False,
        help="sqlalchemy database engine echo switch")
define("database_engine", default="sqlite:///task_files.db",
        help="the database connect string for sqlalchemy")
define("task_title_prefix", default="[loli.lu] ",
        help="prefix of task")
define("using_xss", default=False,
        help="use xss or cross-cookie")
define("using_xsrf", default=False,
        help="using xsrf to prevent cross-site request forgery")
define("reg_key", default=None,
        help="if setted new user is not allowed except login with '/login?key=<reg_key>'.")
define("enable_share", default=True, help="enable share task")

class Application(web.Application):
    def __init__(self):
        from handlers import handlers, ui_modules
        from libs.util import ui_methods
        from libs.db_task_manager import DBTaskManager
        from libs.user_manager import UserManager
        from libs.vip_pool import VIPool
        settings = dict(
            debug=options.debug,
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            cookie_secret=options.cookie_secret,
            login_url="/login",

            ui_modules=ui_modules,
            ui_methods=ui_methods,
        )
        super(Application, self).__init__(handlers, **settings)

        self.user_manager = UserManager()
        self.task_manager = DBTaskManager(
                    username = options.username,
                    password = options.password
                )
        self.vip_pool = VIPool()
        if not self.task_manager.islogin:
            raise Exception, "xunlei login error"
        self.task_manager.async_update()
        PeriodicCallback(self.task_manager.async_update,
                options.downloading_task_check_interval * 1000).start()
        PeriodicCallback(self.user_manager.reset_all_add_task_limit, 86400 * 1000).start()

        logging.info("load finished! listening on %s:%s" % (options.bind_ip, options.port))

def main():
    tornado.options.parse_command_line()
    if options.f:
        tornado.options.parse_config_file(options.f)
    tornado.options.parse_command_line()

    http_server = HTTPServer(Application(), xheaders=True)
    http_server.bind(options.port, options.bind_ip)
    http_server.start()

    IOLoop.instance().start()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = vip_checker
# -*- encoding: utf-8 -*-
# author: binux<17175297.hk@gmail.com>

import time
from sys import argv, stderr
from libs.lixian_api import LiXianAPI

CID = "9AD622F6EE572E367A37A166D7BD5AA8279A68D4"
URL = "magnet:?xt=urn:btih:9ad622f6ee572e367a37a166d7bd5aa8279a68d4"

if len(argv) != 2:
    print "usage: vip_check.py user_list"

fp = open(argv[1], "r")
for line in fp:
  try:
    line = line.strip()
    if not line:
        continue
    username, password = line.split()
    xunlei = LiXianAPI()
    if not xunlei.login(username, password):
        print >> stderr, username, "login error"
        continue
    else:
        info = xunlei.get_vip_info()
        print >> stderr, username, "expiredate:", info.get("expiredate", "unknow"), "level:", info.get("level", "0")
    tasks = xunlei.get_task_list(10, 2)
    tid = 0
    lixian_url = ""
    for task in tasks:
        if task['cid'] == CID:
            for file in xunlei.get_bt_list(task['task_id'], task['cid']):
                tid = file['task_id']
                lixian_url = file['lixian_url']
    if not tid:
        xunlei.add(URL)
        tasks = xunlei.get_task_list(10, 2)
        #time.sleep(1)
        for task in tasks:
            if task['cid'] == CID:
                for file in xunlei.get_bt_list(task['task_id'], task['cid']):
                    tid = file['task_id']
                    lixian_url = file['lixian_url']
    if not tid:
        print >> stderr, username, "add task error"
        continue
    r = xunlei.session.get(lixian_url, cookies={"gdriveid": xunlei.gdriveid})
    print "%s|%s|%s|%s" % (xunlei.uid, xunlei.gdriveid, tid, lixian_url)
  except Exception, e:
    print e
    continue

########NEW FILE########
