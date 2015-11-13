__FILENAME__ = admin
# -*- coding: utf-8 -*-

import logging
import re

try:
    import json
except:
    import simplejson as json

from hashlib import md5
from time import time
from datetime import datetime,timedelta
from urllib import urlencode

from common import BaseHandler, authorized, safe_encode, cnnow, clear_cache_by_pathlist, quoted_string, clear_all_cache

from setting import *
from model import Article, Comment, Link, Category, Tag, User, MyData

if not debug:
    import sae.mail
    from sae.taskqueue import add_task
    from sae.storage import Bucket

######
def put_obj2storage(file_name = '', data = '', expires='365', type=None, encoding= None, domain_name = STORAGE_DOMAIN_NAME):
    bucket = Bucket(domain_name)
    bucket.put_object(file_name, data, content_type=type, content_encoding= encoding)
    return bucket.generate_url(file_name)

def upload_qiniu(savename="test.txt", filedata=None):
    if QN_BUCKET and savename and filedata:
        import qiniu.conf
        qiniu.conf.ACCESS_KEY = QN_AK
        qiniu.conf.SECRET_KEY = QN_SK

        import qiniu.rs
        policy = qiniu.rs.PutPolicy(QN_BUCKET)
        uptoken = policy.token()

        import qiniu.io

        key = savename
        if key[0] == "/":
            key = key[1:]
        ret, err = qiniu.io.put(uptoken, key, filedata)
        if err is not None:
            return False
        ###下面返回的网址有可能不同，有的是 xxxx.u.qiniudn.com 请改为自己的
        return "http://%s.qiniudn.com/%s" % (QN_BUCKET, key)
    else:
        return False

######
class HomePage(BaseHandler):
    @authorized()
    def get(self):
        output = self.render('admin_index.html', {
            'title': "%s - %s"%(SITE_TITLE,SITE_SUB_TITLE),
            'keywords':KEYWORDS,
            'description':SITE_DECR,
            'test': '',
        },layout='_layout_admin.html')
        self.write(output)
        return output

class Login(BaseHandler):
    def get(self):
        self.echo('admin_login.html', {
            'title': "管理员登录",
            'has_user': User.check_has_user()
        },layout='_layout_admin.html')

    def post(self):
        try:
            name = self.get_argument("name")
            password = self.get_argument("password")
        except:
            self.redirect('%s/admin/login'% BASE_URL)
            return

        if name and password:
            has_user = User.check_has_user()
            if has_user:
                #check user
                password = md5(password.encode('utf-8')).hexdigest()
                user = User.check_user( name, password)
                if user:
                    #logging.error('user ok')
                    self.set_cookie('username', name, path="/", expires_days = 365 )
                    self.set_cookie('userpw', password, path="/", expires_days = 365 )
                    self.redirect('%s/admin/'% BASE_URL)
                    return
                else:
                    #logging.error('user not ok')
                    self.redirect('%s/admin/login'% BASE_URL)
                    return
            else:
                #add new user
                newuser = User.add_new_user( name, password)
                if newuser:
                    self.set_cookie('username', name, path="/", expires_days = 365 )
                    self.set_cookie('userpw', md5(password.encode('utf-8')).hexdigest(), path="/", expires_days = 365 )
                    self.redirect('%s/admin/'% BASE_URL)
                    return
                else:
                    self.redirect('%s/admin/login'% BASE_URL)
                    return
        else:
            self.redirect('%s/admin/login'% BASE_URL)

class Logout(BaseHandler):
    def get(self):
        self.clear_all_cookies()
        self.redirect('%s/admin/login'% BASE_URL)

class AddUser(BaseHandler):
    @authorized()
    def get(self):
        pass

class Forbidden(BaseHandler):
    def get(self):
        self.write('Forbidden page')

class FileUpload(BaseHandler):
    @authorized()
    def post(self):
        self.set_header('Content-Type','text/html')
        rspd = {'status': 201, 'msg':'ok'}

        filetoupload = self.request.files['filetoupload']
        if filetoupload:
            myfile = filetoupload[0]
            try:
                file_type = myfile['filename'].split('.')[-1].lower()
                new_file_name = "%s.%s"% (str(int(time())), file_type)
            except:
                file_type = ''
                new_file_name = str(int(time()))
            ##
            mime_type = myfile['content_type']
            encoding = None
            ###

            try:
                if STORAGE_DOMAIN_NAME:
                    attachment_url = put_obj2storage(file_name = str(new_file_name), data = myfile['body'], expires='365', type= mime_type, encoding= encoding)
                elif QN_AK and QN_SK and QN_BUCKET:
                    attachment_url = upload_qiniu(str(new_file_name), myfile['body'])
            except:
                attachment_url = ''

            if attachment_url:
                rspd['status'] = 200
                rspd['filename'] = myfile['filename']
                rspd['msg'] = attachment_url
            else:
                rspd['status'] = 500
                rspd['msg'] = 'put_obj2storage erro, try it again.'
        else:
            rspd['msg'] = 'No file uploaded'
        self.write(json.dumps(rspd))
        return

class AddPost(BaseHandler):
    @authorized()
    def get(self):
        self.echo('admin_addpost.html', {
            'title': "添加文章",
            'cats': Category.get_all_cat_name(),
            'tags': Tag.get_all_tag_name(),
        },layout='_layout_admin.html')

    @authorized()
    def post(self):
        self.set_header('Content-Type','application/json')
        rspd = {'status': 201, 'msg':'ok'}

        try:
            tf = {'true':1,'false':0}
            timestamp = int(time())
            post_dic = {
                'category': self.get_argument("cat"),
                'title': self.get_argument("tit"),
                'content': self.get_argument("con"),
                'tags': self.get_argument("tag",'').replace(u'，',','),
                'closecomment': self.get_argument("clo",'0'),
                'password': self.get_argument("password",''),
                'add_time': timestamp,
                'edit_time': timestamp,
            }
            if post_dic['tags']:
                tagslist = set([x.strip() for x in post_dic['tags'].split(',')])
                try:
                    tagslist.remove('')
                except:
                    pass
                if tagslist:
                    post_dic['tags'] = ','.join(tagslist)
            post_dic['closecomment'] = tf[post_dic['closecomment'].lower()]
        except:
            rspd['status'] = 500
            rspd['msg'] = '错误： 注意必填的三项'
            self.write(json.dumps(rspd))
            return

        postid = Article.add_new_article(post_dic)
        if postid:
            Category.add_postid_to_cat(post_dic['category'], str(postid))
            if post_dic['tags']:
                Tag.add_postid_to_tags(post_dic['tags'].split(','), str(postid))

            rspd['status'] = 200
            rspd['msg'] = '完成： 你已经成功添加了一篇文章 <a href="/t/%s" target="_blank">查看</a>' % str(postid)
            clear_cache_by_pathlist(['/', 'cat:%s' % quoted_string(post_dic['category'])])

            if not debug:
                add_task('default', '/task/pingrpctask')

            self.write(json.dumps(rspd))
            return
        else:
            rspd['status'] = 500
            rspd['msg'] = '错误： 未知错误，请尝试重新提交'
            self.write(json.dumps(rspd))
            return

class EditPost(BaseHandler):
    @authorized()
    def get(self, id = ''):
        obj = None
        if id:
            obj = Article.get_article_by_id_edit(id)
        self.echo('admin_editpost.html', {
            'title': "编辑文章",
            'cats': Category.get_all_cat_name(),
            'tags': Tag.get_all_tag_name(),
            'obj': obj
        },layout='_layout_admin.html')

    @authorized()
    def post(self, id = ''):
        act = self.get_argument("act",'')
        if act == 'findid':
            eid = self.get_argument("id",'')
            self.redirect('%s/admin/edit_post/%s'% (BASE_URL, eid))
            return

        self.set_header('Content-Type','application/json')
        rspd = {'status': 201, 'msg':'ok'}
        oldobj = Article.get_article_by_id_edit(id)

        try:
            tf = {'true':1,'false':0}
            timestamp = int(time())
            post_dic = {
                'category': self.get_argument("cat"),
                'title': self.get_argument("tit"),
                'content': self.get_argument("con"),
                'tags': self.get_argument("tag",'').replace(u'，',','),
                'closecomment': self.get_argument("clo",'0'),
                'password': self.get_argument("password",''),
                'edit_time': timestamp,
                'id': id
            }

            if post_dic['tags']:
                tagslist = set([x.strip() for x in post_dic['tags'].split(',')])
                try:
                    tagslist.remove('')
                except:
                    pass
                if tagslist:
                    post_dic['tags'] = ','.join(tagslist)
            post_dic['closecomment'] = tf[post_dic['closecomment'].lower()]
        except:
            rspd['status'] = 500
            rspd['msg'] = '错误： 注意必填的三项'
            self.write(json.dumps(rspd))
            return

        postid = Article.update_post_edit(post_dic)
        if postid:
            cache_key_list = ['/', 'post:%s'% id, 'cat:%s' % quoted_string(oldobj.category)]
            if oldobj.category != post_dic['category']:
                #cat changed
                Category.add_postid_to_cat(post_dic['category'], str(postid))
                Category.remove_postid_from_cat(post_dic['category'], str(postid))
                cache_key_list.append('cat:%s' % quoted_string(post_dic['category']))

            if oldobj.tags != post_dic['tags']:
                #tag changed
                old_tags = set(oldobj.tags.split(','))
                new_tags = set(post_dic['tags'].split(','))

                removed_tags = old_tags - new_tags
                added_tags = new_tags - old_tags

                if added_tags:
                    Tag.add_postid_to_tags(added_tags, str(postid))

                if removed_tags:
                    Tag.remove_postid_from_tags(removed_tags, str(postid))

            clear_cache_by_pathlist(cache_key_list)
            rspd['status'] = 200
            rspd['msg'] = '完成： 你已经成功编辑了一篇文章 <a href="/t/%s" target="_blank">查看编辑后的文章</a>' % str(postid)
            self.write(json.dumps(rspd))
            return
        else:
            rspd['status'] = 500
            rspd['msg'] = '错误： 未知错误，请尝试重新提交'
            self.write(json.dumps(rspd))
            return

class DelPost(BaseHandler):
    @authorized()
    def get(self, id = ''):
        Article.del_post_by_id(id)
        clear_cache_by_pathlist(['post:%s'%id])
        self.redirect('%s/admin/edit_post/'% (BASE_URL))

class EditComment(BaseHandler):
    @authorized()
    def get(self, id = ''):
        obj = None
        if id:
            obj = Comment.get_comment_by_id(id)
            if obj:
                act = self.get_argument("act",'')
                if act == 'del':
                    Comment.del_comment_by_id(id)
                    clear_cache_by_pathlist(['post:%d'%obj.postid])
                    self.redirect('%s/admin/comment/'% (BASE_URL))
                    return
        self.echo('admin_comment.html', {
            'title': "管理评论",
            'cats': Category.get_all_cat_name(),
            'tags': Tag.get_all_tag_name(),
            'obj': obj,
            'comments': Comment.get_recent_comments(),
        },layout='_layout_admin.html')

    @authorized()
    def post(self, id = ''):
        act = self.get_argument("act",'')
        if act == 'findid':
            eid = self.get_argument("id",'')
            self.redirect('%s/admin/comment/%s'% (BASE_URL, eid))
            return

        tf = {'true':1,'false':0}
        post_dic = {
            'author': self.get_argument("author"),
            'email': self.get_argument("email"),
            'content': safe_encode(self.get_argument("content").replace('\r','\n')),
            'url': self.get_argument("url",''),
            'visible': self.get_argument("visible",'false'),
            'id': id
        }
        post_dic['visible'] = tf[post_dic['visible'].lower()]

        Comment.update_comment_edit(post_dic)
        clear_cache_by_pathlist(['post:%s'%id])
        self.redirect('%s/admin/comment/%s'% (BASE_URL, id))
        return

class LinkBroll(BaseHandler):
    @authorized()
    def get(self):
        act = self.get_argument("act",'')
        id = self.get_argument("id",'')

        obj = None
        if act == 'del':
            if id:
                Link.del_link_by_id(id)
                clear_cache_by_pathlist(['/'])
            self.redirect('%s/admin/links'% (BASE_URL))
            return
        elif act == 'edit':
            if id:
                obj = Link.get_link_by_id(id)
                clear_cache_by_pathlist(['/'])
        self.echo('admin_link.html', {
            'title': "管理友情链接",
            'objs': Link.get_all_links(),
            'obj': obj,
        },layout='_layout_admin.html')

    @authorized()
    def post(self):
        act = self.get_argument("act",'')
        id = self.get_argument("id",'')
        name = self.get_argument("name",'')
        sort = self.get_argument("sort",'0')
        url = self.get_argument("url",'')

        if name and url:
            params = {'id': id, 'name': name, 'url': url, 'displayorder': sort}
            if act == 'add':
                Link.add_new_link(params)

            if act == 'edit':
                Link.update_link_edit(params)

            clear_cache_by_pathlist(['/'])

        self.redirect('%s/admin/links'% (BASE_URL))
        return

class FlushData(BaseHandler):
    @authorized()
    def get(self):
        act = self.get_argument("act",'')
        if act == 'flush':
            MyData.flush_all_data()
            clear_all_cache()
            self.redirect('/admin/flushdata')
            return
        elif act == 'flushcache':
            clear_all_cache()
            self.redirect('/admin/flushdata')
            return

        self.echo('admin_flushdata.html', {
            'title': "清空缓存/数据",
        },layout='_layout_admin.html')

class PingRPCTask(BaseHandler):
    def get(self):
        for n in range(len(XML_RPC_ENDPOINTS)):
            add_task('default', '%s/task/pingrpc/%d' % (BASE_URL, n))
        self.write(str(time()))

    post = get

class PingRPC(BaseHandler):
    def get(self, n = 0):
        import urllib2

        pingstr = self.render('rpc.xml', {'article_id':Article.get_max_id()})

        headers = {
            'User-Agent':'request',
            'Content-Type' : 'text/xml',
            'Content-length' : str(len(pingstr))
        }

        req = urllib2.Request(
            url = XML_RPC_ENDPOINTS[int(n)],
            headers = headers,
            data = pingstr,
        )
        try:
            content = urllib2.urlopen(req).read()
            tip = 'Ping ok' + content
        except:
            tip = 'ping erro'

        self.write(str(time()) + ": " + tip)
        #add_task('default', '%s/task/sendmail'%BASE_URL, urlencode({'subject': tip, 'content': tip + " " + str(n)}))

    post = get

class SendMail(BaseHandler):
    def post(self):
        subject = self.get_argument("subject",'')
        content = self.get_argument("content",'')

        if subject and content:
            sae.mail.send_mail(NOTICE_MAIL, subject, content,(MAIL_SMTP, int(MAIL_PORT), MAIL_FROM, MAIL_PASSWORD, True))

class Install(BaseHandler):
    def get(self):
        try:
            self.write('如果出现错误请尝试刷新本页。')
            has_user = User.check_has_user()
            if has_user:
                self.write('博客已经成功安装了，你可以直接 <a href="/admin/flushdata">清空网站数据</a>')
            else:
                self.write('博客数据库已经建立，现在就去 <a href="/admin/">设置一个管理员帐号</a>')
        except:
            MyData.creat_table()
            self.write('博客已经成功安装了，现在就去 <a href="/admin/">设置一个管理员帐号</a>')

class NotFoundPage(BaseHandler):
    def get(self):
        self.set_status(404)
        self.echo('error.html', {
            'page': '404',
            'title': "Can't find out this URL",
            'h2': 'Oh, my god!',
            'msg': 'Something seems to be lost...'
        })

#####
urls = [
    (r"/admin/", HomePage),
    (r"/admin/login", Login),
    (r"/admin/logout", Logout),
    (r"/admin/403", Forbidden),
    (r"/admin/add_post", AddPost),
    (r"/admin/edit_post/(\d*)", EditPost),
    (r"/admin/del_post/(\d+)", DelPost),
    (r"/admin/comment/(\d*)", EditComment),
    (r"/admin/flushdata", FlushData),
    (r"/task/pingrpctask", PingRPCTask),
    (r"/task/pingrpc/(\d+)", PingRPC),
    (r"/task/sendmail", SendMail),
    (r"/install", Install),
    (r"/admin/fileupload", FileUpload),
    (r"/admin/links", LinkBroll),
    (r".*", NotFoundPage)
]

########NEW FILE########
__FILENAME__ = blog
# -*- coding: utf-8 -*-

import logging

import json
    
from hashlib import md5
from time import time

from setting import *

from common import BaseHandler, unquoted_unicode, quoted_string, safe_encode, slugfy, pagecache, clear_cache_by_pathlist, client_cache

from model import Article, Comment, Link, Category, Tag

###############
class HomePage(BaseHandler):
    @pagecache()
    def get(self):
        try:
            objs = Article.get_post_for_homepage()
        except:
            self.redirect('/install')
            return
        if objs:
            fromid = objs[0].id
            endid = objs[-1].id
        else:
            fromid = endid = ''
        
        allpost =  Article.count_all_post()
        allpage = allpost/EACH_PAGE_POST_NUM
        if allpost%EACH_PAGE_POST_NUM:
            allpage += 1
        
        output = self.render('index.html', {
            'title': "%s - %s"%(SITE_TITLE,SITE_SUB_TITLE),
            'keywords':KEYWORDS,
            'description':SITE_DECR,
            'objs': objs,
            'cats': Category.get_all_cat_name(),
            'tags': Tag.get_hot_tag_name(),
            'page': 1,
            'allpage': allpage,
            'listtype': 'index',
            'fromid': fromid,
            'endid': endid,
            'comments': Comment.get_recent_comments(),
            'links':Link.get_all_links(),
        },layout='_layout.html')
        self.write(output)
        return output

class IndexPage(BaseHandler):
    @pagecache('post_list_index', PAGE_CACHE_TIME, lambda self,direction,page,base_id: page)
    def get(self, direction = 'next', page = '2', base_id = '1'):
        if page == '1':
            self.redirect(BASE_URL)
            return
        objs = Article.get_page_posts(direction, page, base_id)
        if objs:
            if direction == 'prev':
                objs.reverse()            
            fromid = objs[0].id
            endid = objs[-1].id
        else:
            fromid = endid = ''
        
        allpost =  Article.count_all_post()
        allpage = allpost/EACH_PAGE_POST_NUM
        if allpost%EACH_PAGE_POST_NUM:
            allpage += 1
        output = self.render('index.html', {
            'title': "%s - %s | Part %s"%(SITE_TITLE,SITE_SUB_TITLE, page),
            'keywords':KEYWORDS,
            'description':SITE_DECR,
            'objs': objs,
            'cats': Category.get_all_cat_name(),
            'tags': Tag.get_hot_tag_name(),
            'page': int(page),
            'allpage': allpage,
            'listtype': 'index',
            'fromid': fromid,
            'endid': endid,
            'comments': Comment.get_recent_comments(),
            'links':Link.get_all_links(),
        },layout='_layout.html')
        self.write(output)
        return output
        
class PostDetailShort(BaseHandler):
    @client_cache(600, 'public')
    def get(self, id = ''):
        obj = Article.get_article_by_id_simple(id)
        if obj:
            self.redirect('%s/topic/%d/%s'% (BASE_URL, obj.id, obj.title), 301)
            return
        else:
            self.redirect(BASE_URL)

class PostDetail(BaseHandler):
    @pagecache('post', PAGE_CACHE_TIME, lambda self,id,title: id)
    def get(self, id = '', title = ''):
        tmpl = ''
        obj = Article.get_article_by_id_detail(id)
        if not obj:
            self.redirect(BASE_URL)
            return
        #redirect to right title
        try:
            title = unquote(title).decode('utf-8')
        except:
            pass
        if title != obj.slug:
            self.redirect(obj.absolute_url, 301)
            return        
        #
        if obj.password and THEME == 'default':
            rp = self.get_cookie("rp%s" % id, '')
            if rp != obj.password:
                tmpl = '_pw'
        
        self.set_header("Last-Modified", obj.last_modified)
            
        output = self.render('page%s.html'%tmpl, {
            'title': "%s - %s"%(obj.title, SITE_TITLE),
            'keywords':obj.keywords,
            'description':obj.description,
            'obj': obj,
            'cobjs': obj.coms,
            'postdetail': 'postdetail',
            'cats': Category.get_all_cat_name(),
            'tags': Tag.get_hot_tag_name(),
            'page': 1,
            'allpage': 10,
            'comments': Comment.get_recent_comments(),
            'links':Link.get_all_links(),
        },layout='_layout.html')
        self.write(output)
        
        if obj.password and THEME == 'default':
            return
        else:
            return output
        
    def post(self, id = '', title = ''):
        action = self.get_argument("act")
        
        if action == 'inputpw':
            wrn = self.get_cookie("wrpw", '0')
            if int(wrn)>=10:
                self.write('403')
                return
            
            pw = self.get_argument("pw",'')
            pobj = Article.get_article_by_id_simple(id)
            wr = False
            if pw:             
                if pobj.password == pw:
                    self.set_cookie("rp%s" % id, pobj.password, path = "/", expires_days =1)
                else:
                    wr = True
            else:
                wr = True
            if wr:
                wrn = self.get_cookie("wrpw", '0')
                self.set_cookie("wrpw", str(int(wrn)+1), path = "/", expires_days = 1 )
            
            self.redirect('%s/topic/%d/%s'% (BASE_URL, pobj.id, pobj.title))
            return
        
        self.set_header('Content-Type','application/json')
        rspd = {'status': 201, 'msg':'ok'}
        
        if action == 'readmorecomment':
            fromid = self.get_argument("fromid",'')
            allnum = int(self.get_argument("allnum",0))
            showednum = int(self.get_argument("showednum", EACH_PAGE_COMMENT_NUM))
            if fromid:
                rspd['status'] = 200
                if (allnum - showednum) >= EACH_PAGE_COMMENT_NUM:
                    limit = EACH_PAGE_COMMENT_NUM
                else:
                    limit = allnum - showednum
                cobjs = Comment.get_post_page_comments_by_id( id, fromid, limit )
                rspd['commentstr'] = self.render('comments.html', {'cobjs': cobjs})
                rspd['lavenum'] = allnum - showednum - limit
                self.write(json.dumps(rspd))
            return
        
        #
        usercomnum = self.get_cookie('usercomnum','0')
        if int(usercomnum) > MAX_COMMENT_NUM_A_DAY:
            rspd = {'status': 403, 'msg':'403: Forbidden'}
            self.write(json.dumps(rspd))
            return
        
        try:
            timestamp = int(time())
            post_dic = {
                'author': self.get_argument("author"),
                'email': self.get_argument("email"),
                'content': safe_encode(self.get_argument("con").replace('\r','\n')),
                'url': self.get_argument("url",''),
                'postid': self.get_argument("postid"),
                'add_time': timestamp,
                'toid': self.get_argument("toid",''),
                'visible': COMMENT_DEFAULT_VISIBLE
            }
        except:
            rspd['status'] = 500
            rspd['msg'] = '错误： 注意必填的三项'
            self.write(json.dumps(rspd))
            return
        
        pobj = Article.get_article_by_id_simple(id)
        if pobj and not pobj.closecomment:
            cobjid = Comment.add_new_comment(post_dic)
            if cobjid:
                Article.update_post_comment( pobj.comment_num+1, id)
                rspd['status'] = 200
                #rspd['msg'] = '恭喜： 已成功提交评论'
                
                rspd['msg'] = self.render('comment.html', {
                        'cobjid': cobjid,
                        'gravatar': 'http://www.gravatar.com/avatar/%s'%md5(post_dic['email']).hexdigest(),
                        'url': post_dic['url'],
                        'author': post_dic['author'],
                        'visible': post_dic['visible'],
                        'content': post_dic['content'],
                    })
                
                clear_cache_by_pathlist(['/','post:%s'%id])
                #send mail
                if not debug:
                    try:
                        if NOTICE_MAIL:
                            tolist = [NOTICE_MAIL]
                        else:
                            tolist = []
                        if post_dic['toid']:
                            tcomment = Comment.get_comment_by_id(toid)
                            if tcomment and tcomment.email:
                                tolist.append(tcomment.email)
                        commenturl = "%s/t/%s#r%s" % (BASE_URL, str(pobj.id), str(cobjid))
                        m_subject = u'有人回复您在 《%s》 里的评论 %s' % ( pobj.title,str(cobjid))
                        m_html = u'这是一封提醒邮件（请勿直接回复）： %s ，请尽快处理： %s' % (m_subject, commenturl)
                        
                        if tolist:
                            import sae.mail
                            sae.mail.send_mail(','.join(tolist), m_subject, m_html,(MAIL_SMTP, int(MAIL_PORT), MAIL_FROM, MAIL_PASSWORD, True))          
                        
                    except:
                        pass
            else:
                rspd['msg'] = '错误： 未知错误'
        else:
            rspd['msg'] = '错误： 未知错误'
        self.write(json.dumps(rspd))

class CategoryDetailShort(BaseHandler):
    @client_cache(3600, 'public')
    def get(self, id = ''):
        obj = Category.get_cat_by_id(id)
        if obj:
            self.redirect('%s/category/%s'% (BASE_URL, obj.name), 301)
            return
        else:
            self.redirect(BASE_URL)

class CategoryDetail(BaseHandler):
    @pagecache('cat', PAGE_CACHE_TIME, lambda self,name: name)
    def get(self, name = ''):
        objs = Category.get_cat_page_posts(name, 1)
        
        catobj = Category.get_cat_by_name(name)
        if catobj:
            pass
        else:
            self.redirect(BASE_URL)
            return
        
        allpost =  catobj.id_num
        allpage = allpost/EACH_PAGE_POST_NUM
        if allpost%EACH_PAGE_POST_NUM:
            allpage += 1
            
        output = self.render('index.html', {
            'title': "%s - %s"%( catobj.name, SITE_TITLE),
            'keywords':catobj.name,
            'description':SITE_DECR,
            'objs': objs,
            'cats': Category.get_all_cat_name(),
            'tags': Tag.get_hot_tag_name(),
            'page': 1,
            'allpage': allpage,
            'listtype': 'cat',
            'name': name,
            'namemd5': md5(name.encode('utf-8')).hexdigest(),
            'comments': Comment.get_recent_comments(),
            'links':Link.get_all_links(),
        },layout='_layout.html')
        self.write(output)
        return output

class TagDetail(BaseHandler):
    @pagecache()
    def get(self, name = ''):
        objs = Tag.get_tag_page_posts(name, 1)
        
        catobj = Tag.get_tag_by_name(name)
        if catobj:
            pass
        else:
            self.redirect(BASE_URL)
            return
        
        allpost =  catobj.id_num
        allpage = allpost/EACH_PAGE_POST_NUM
        if allpost%EACH_PAGE_POST_NUM:
            allpage += 1
            
        output = self.render('index.html', {
            'title': "%s - %s"%( catobj.name, SITE_TITLE),
            'keywords':catobj.name,
            'description':SITE_DECR,
            'objs': objs,
            'cats': Category.get_all_cat_name(),
            'tags': Tag.get_hot_tag_name(),
            'page': 1,
            'allpage': allpage,
            'listtype': 'tag',
            'name': name,
            'namemd5': md5(name.encode('utf-8')).hexdigest(),
            'comments': Comment.get_recent_comments(),
            'links':Link.get_all_links(),
        },layout='_layout.html')
        self.write(output)
        return output
        

class ArticleList(BaseHandler):
    @pagecache('post_list_tag', PAGE_CACHE_TIME, lambda self,listtype,direction,page,name: "%s_%s"%(name,page))
    def get(self, listtype = '', direction = 'next', page = '1', name = ''):
        if listtype == 'cat':
            objs = Category.get_cat_page_posts(name, page)
            catobj = Category.get_cat_by_name(name)
        else:
            objs = Tag.get_tag_page_posts(name, page)
            catobj = Tag.get_tag_by_name(name)
        
        #
        if catobj:
            pass
        else:
            self.redirect(BASE_URL)
            return
        
        allpost =  catobj.id_num
        allpage = allpost/EACH_PAGE_POST_NUM
        if allpost%EACH_PAGE_POST_NUM:
            allpage += 1
            
        output = self.render('index.html', {
            'title': "%s - %s | Part %s"%( catobj.name, SITE_TITLE, page),
            'keywords':catobj.name,
            'description':SITE_DECR,
            'objs': objs,
            'cats': Category.get_all_cat_name(),
            'tags': Tag.get_hot_tag_name(),
            'page': int(page),
            'allpage': allpage,
            'listtype': listtype,
            'name': name,
            'namemd5': md5(name.encode('utf-8')).hexdigest(),
            'comments': Comment.get_recent_comments(),
            'links':Link.get_all_links(),
        },layout='_layout.html')
        self.write(output)
        return output
        
        
class Robots(BaseHandler):
    def get(self):
        self.echo('robots.txt',{'cats':Category.get_all_cat_id()})

class Feed(BaseHandler):
    def get(self):
        posts = Article.get_post_for_homepage()
        output = self.render('index.xml', {
                    'posts':posts,
                    'site_updated':Article.get_last_post_add_time(),
                })
        self.set_header('Content-Type','application/atom+xml')
        self.write(output)        

class Sitemap(BaseHandler):
    def get(self, id = ''):
        self.set_header('Content-Type','text/xml')
        self.echo('sitemap.html', {'sitemapstr':Category.get_sitemap_by_id(id), 'id': id})

class Attachment(BaseHandler):
    def get(self, name):
        self.redirect('http://%s-%s.stor.sinaapp.com/%s'% (APP_NAME, STORAGE_DOMAIN_NAME, unquoted_unicode(name)), 301)
        return
        
########
urls = [
    (r"/", HomePage),
    (r"/robots.txt", Robots),
    (r"/feed", Feed),
    (r"/index.xml", Feed),
    (r"/t/(\d+)$", PostDetailShort),
    (r"/topic/(\d+)/(.*)$", PostDetail),
    (r"/index_(prev|next)_page/(\d+)/(\d+)/$", IndexPage),
    (r"/c/(\d+)$", CategoryDetailShort),
    (r"/category/(.+)/$", CategoryDetail),
    (r"/tag/(.+)/$", TagDetail),
    (r"/(cat|tag)_(prev|next)_page/(\d+)/(.+)/$", ArticleList),
    (r"/sitemap_(\d+)\.xml$", Sitemap),
    (r"/attachment/(.+)$", Attachment),
]

########NEW FILE########
__FILENAME__ = common
# -*- coding: utf-8 -*-
#import logging
import re
import os.path
from traceback import format_exc
from urllib import unquote, quote, urlencode
from urlparse import urljoin, urlunsplit

from datetime import datetime, timedelta

import tenjin
from tenjin.helpers import *

from setting import *

import tornado.web


#Memcache 是否可用、用户是否在后台初始化Memcache
MC_Available = False
if PAGE_CACHE:
    import pylibmc
    mc = pylibmc.Client() #只需初始化一次？
    try:
        MC_Available = mc.set('mc_available', '1', 3600)
    except:
        pass

#####
def slugfy(text, separator='-'):
    text = text.lower()
    text = re.sub("[¿_\-　，。：；‘“’”【】『』§！－——＋◎＃￥％……※×（）《》？、÷]+", ' ', text)
    ret_list = []
    for c in text:
        ordnum = ord(c)
        if 47<ordnum<58 or 96<ordnum<123:
            ret_list.append(c)
        else:
            if re.search(u"[\u4e00-\u9fa5]", c):
                ret_list.append(c)
            else:
                ret_list.append(' ')
    ret = ''.join(ret_list)
    ret = re.sub(r"\ba\b|\ban\b|\bthe\b", '', ret)
    ret = ret.strip()
    ret = re.sub("[\s]+", separator, ret)
    return ret

def safe_encode(con):
    return con.replace("<","&lt;").replace(">","&gt;")

def safe_decode(con):
    return con.replace("&lt;","<").replace("&gt;",">")

def unquoted_unicode(string, coding='utf-8'):
    return unquote(string).decode(coding)

def quoted_string(unicode, coding='utf-8'):
    return quote(unicode.encode(coding))

def cnnow():
    return datetime.utcnow() + timedelta(hours =+ 8)

# get time_from_now
def timestamp_to_datetime(timestamp):
    return datetime.fromtimestamp(timestamp)

def time_from_now(time):
    if isinstance(time, int):
        time = timestamp_to_datetime(time)
    #time_diff = datetime.utcnow() - time
    time_diff = cnnow() - time
    days = time_diff.days
    if days:
        if days > 730:
            return '%s years ago' % (days / 365)
        if days > 365:
            return '1 year ago'
        if days > 60:
            return '%s months ago' % (days / 30)
        if days > 30:
            return '1 month ago'
        if days > 14:
            return '%s weeks ago' % (days / 7)
        if days > 7:
            return '1 week ago'
        if days > 1:
            return '%s days ago' % days
        return '1 day ago'
    seconds = time_diff.seconds
    if seconds > 7200:
        return '%s hours ago' % (seconds / 3600)
    if seconds > 3600:
        return '1 hour ago'
    if seconds > 120:
        return '%s minutes ago' % (seconds / 60)
    if seconds > 60:
        return '1 minute ago'
    if seconds > 1:
        return '%s seconds ago' %seconds
    return '%s second ago' % seconds

def clear_cache_by_pathlist(pathlist = []):
    if pathlist and MC_Available:
        try:
            mc = pylibmc.Client()
            mc.delete_multi([str(p) for p in pathlist])
        except:
            pass

def clear_all_cache():
    if PAGE_CACHE:
        try:
            mc = pylibmc.Client()
            mc.flush_all()
        except:
            pass
    else:
        pass
    
def format_date(dt):
    return dt.strftime('%a, %d %b %Y %H:%M:%S GMT')


def memcached(key, cache_time=0, key_suffix_calc_func=None):
    def wrap(func):
        def cached_func(*args, **kw):
            if not MC_Available:
                return func(*args, **kw)
            
            key_with_suffix = key
            if key_suffix_calc_func:
                key_suffix = key_suffix_calc_func(*args, **kw)
                if key_suffix is not None:
                    key_with_suffix = '%s:%s' % (key, key_suffix)
            
            mc = pylibmc.Client()
            value = mc.get(key_with_suffix)
            if value is None:
                value = func(*args, **kw)
                try:
                    mc.set(key_with_suffix, value, cache_time)
                except:
                    pass
            return value
        return cached_func
    return wrap

RQT_RE = re.compile('<span id="requesttime">\d*</span>', re.I)
def pagecache(key="", time=PAGE_CACHE_TIME, key_suffix_calc_func=None):
    def _decorate(method):
        def _wrapper(*args, **kwargs):
            if not MC_Available:
                method(*args, **kwargs)
                return
            
            req = args[0]
            
            key_with_suffix = key
            if key_suffix_calc_func:
                key_suffix = key_suffix_calc_func(*args, **kwargs)
                if key_suffix:
                    key_with_suffix = '%s:%s' % (key, quoted_string(key_suffix)) 
            
            if key_with_suffix:
                key_with_suffix = str(key_with_suffix)
            else:
                key_with_suffix = req.request.path
                
            mc = pylibmc.Client()
            html = mc.get(key_with_suffix)
            request_time = int(req.request.request_time()*1000)
            if html:
                req.write(html)
                #req.write(RQT_RE.sub('<span id="requesttime">%d</span>'%request_time, html))
            else:
                result = method(*args, **kwargs)
                mc.set(key_with_suffix, result, time)
        return _wrapper
    return _decorate

###
engine = tenjin.Engine(path=[os.path.join('templates', theme) for theme in [THEME,'admin']] + ['templates'], cache=tenjin.MemoryCacheStorage(), preprocess=True)
class BaseHandler(tornado.web.RequestHandler):
    
    def render(self, template, context=None, globals=None, layout=False):
        if context is None:
            context = {}
        context.update({
            'request':self.request,
        })
        return engine.render(template, context, globals, layout)

    def echo(self, template, context=None, globals=None, layout=False):
        self.write(self.render(template, context, globals, layout))
    
    def set_cache(self, seconds, is_privacy=None):
        if seconds <= 0:
            self.set_header('Cache-Control', 'no-cache')
            #self.set_header('Expires', 'Fri, 01 Jan 1990 00:00:00 GMT')
        else:
            if is_privacy:
                privacy = 'public, '
            elif is_privacy is None:
                privacy = ''
            else:
                privacy = 'private, '
            self.set_header('Cache-Control', '%smax-age=%s' % (privacy, seconds))
    
def authorized(url='/admin/login'):
    def wrap(handler):
        def authorized_handler(self, *args, **kw):
            request = self.request
            user_name_cookie = self.get_cookie('username','')
            user_pw_cookie = self.get_cookie('userpw','')
            if user_name_cookie and user_pw_cookie:
                from model import User
                user = User.check_user(user_name_cookie, user_pw_cookie)
            else:
                user = False
            if request.method == 'GET':
                if not user:
                    self.redirect(url)
                    return False
                else:
                    handler(self, *args, **kw)
            else:
                if not user:
                    self.error(403)
                else:
                    handler(self, *args, **kw)
        return authorized_handler
    return wrap

def client_cache(seconds, privacy=None):
    def wrap(handler):
        def cache_handler(self, *args, **kw):
            self.set_cache(seconds, privacy)
            return handler(self, *args, **kw)
        return cache_handler
    return wrap

########NEW FILE########
__FILENAME__ = model
# -*- coding: utf-8 -*-
import logging
import re
from hashlib import md5

from time import time
from datetime import datetime

from common import slugfy, time_from_now, cnnow, memcached, timestamp_to_datetime, safe_encode
from setting import *

try:
    from tornado import database
except:
    pass

##
##数据库配置信息
if debug:
    #已经在setting里设置了
    pass
else:
    import sae.const
    MYSQL_DB = sae.const.MYSQL_DB
    MYSQL_USER = sae.const.MYSQL_USER
    MYSQL_PASS = sae.const.MYSQL_PASS
    MYSQL_HOST_M = sae.const.MYSQL_HOST
    MYSQL_HOST_S = sae.const.MYSQL_HOST_S
    MYSQL_PORT = sae.const.MYSQL_PORT
    
#主数据库 进行Create,Update,Delete 操作
#从数据库 读取

##
HTML_REG = re.compile(r"""<[^>]+>""", re.I|re.M|re.S)

mdb = database.Connection("%s:%s"%(MYSQL_HOST_M,str(MYSQL_PORT)), MYSQL_DB,MYSQL_USER, MYSQL_PASS, max_idle_time = MAX_IDLE_TIME)
sdb = database.Connection("%s:%s"%(MYSQL_HOST_S,str(MYSQL_PORT)), MYSQL_DB,MYSQL_USER, MYSQL_PASS, max_idle_time = MAX_IDLE_TIME)

###
CODE_RE = re.compile(r"""\[code\](.+?)\[/code\]""",re.I|re.M|re.S)

def n2br(text):
    con = text.replace('>\n\n','>').replace('>\n','>')
    con = "<p>%s</p>"%('</p><p>'.join(con.split('\n\n')))
    return '<br/>'.join(con.split("\n"))    
    
def tran_content(text, code = False):
    if code:
        codetag = '[mycodeplace]'
        codes = CODE_RE.findall(text)
        for i in range(len(codes)):
            text = text.replace(codes[i],codetag)
        text = text.replace("[code]","").replace("[/code]","")
        
        text = n2br(text)
        
        a = text.split(codetag)
        b = []
        for i in range(len(a)):
            b.append(a[i])
            try:
                b.append('<pre><code>' + safe_encode(codes[i]) + '</code></pre>')
            except:
                pass
                        
        return ''.join(b)
    else:
        return n2br(text)

def post_list_format(posts):
    for obj in posts:
        obj.absolute_url = '%s/topic/%d/%s' % (BASE_URL, obj.id, slugfy(obj.title))
        obj.taglist = ', '.join(["""<a href="%s/tag/%s/" rel="tag">%s</a>"""%(BASE_URL, tag, tag) for tag in obj.tags.split(',')])
        
        if '<!--more-->' in obj.content:
            obj.shorten_content = obj.content.split('<!--more-->')[0]
        else:
            obj.shorten_content = HTML_REG.sub('',obj.content[:SHORTEN_CONTENT_WORDS])
        
        obj.add_time_fn = time_from_now(int(obj.add_time))
    return posts

def post_detail_formate(obj):
    if obj:
        slug = slugfy(obj.title)
        obj.slug = slug
        obj.absolute_url = '%s/topic/%d/%s' % (BASE_URL, obj.id, slug)
        obj.shorten_url = '%s/t/%s' % (BASE_URL, obj.id)
        if '[/code]' in obj.content:
            obj.highlight = True
        else:
            obj.highlight = False        
        obj.content = tran_content(obj.content, obj.highlight)
        obj.taglist = ', '.join(["""<a href="%s/tag/%s/" rel="tag">%s</a>"""%(BASE_URL, tag, tag) for tag in obj.tags.split(',')])
        obj.add_time_fn = time_from_now(int(obj.add_time))
        obj.last_modified = timestamp_to_datetime(obj.edit_time)
        obj.keywords = obj.tags
        obj.description = HTML_REG.sub('',obj.content[:DESCRIPTION_CUT_WORDS])
        #get prev and next obj
        obj.prev_obj = sdb.get('SELECT `id`,`title` FROM `sp_posts` WHERE `id` > %s LIMIT 1' % str(obj.id))
        if obj.prev_obj:
            obj.prev_obj.slug = slugfy(obj.prev_obj.title)
        obj.next_obj = sdb.get('SELECT `id`,`title` FROM `sp_posts` WHERE `id` < %s ORDER BY `id` DESC LIMIT 1' % str(obj.id))
        if obj.next_obj:
            obj.next_obj.slug = slugfy(obj.next_obj.title)
        #get relative obj base tags
        obj.relative = []
        if obj.tags:
            idlist = []
            getit = False
            for tag in obj.tags.split(','):
                tagobj = Tag.get_tag_by_name(tag)
                if tagobj and tagobj.content:
                    pids = tagobj.content.split(',')
                    for pid in pids:
                        if pid != str(obj.id) and pid not in idlist:
                            idlist.append(pid)
                            if len(idlist) >= RELATIVE_POST_NUM:
                                getit = True
                                break
                if getit:
                    break
            #
            if idlist:
                obj.relative = sdb.query('SELECT `id`,`title` FROM `sp_posts` WHERE `id` in(%s) LIMIT %s' % (','.join(idlist), str(len(idlist))))
                if obj.relative:
                    for robj in obj.relative:
                        robj.slug = slugfy(robj.title)
        #get comment
        obj.coms = []
        if obj.comment_num >0:
            if obj.comment_num >= EACH_PAGE_COMMENT_NUM:
                first_limit = EACH_PAGE_COMMENT_NUM
            else:
                first_limit = obj.comment_num
            obj.coms = Comment.get_post_page_comments_by_id( obj.id, 0, first_limit )
    return obj

def comment_format(objs):
    for obj in objs:
        obj.gravatar = 'http://www.gravatar.com/avatar/%s'%md5(obj.email).hexdigest()
        obj.add_time = time_from_now(int(obj.add_time))
        
        if obj.visible:
            obj.short_content = HTML_REG.sub('',obj.content[:RECENT_COMMENT_CUT_WORDS])
        else:
            obj.short_content = 'Your comment is awaiting moderation.'[:RECENT_COMMENT_CUT_WORDS]
        
        obj.content = obj.content.replace('\n','<br/>')
    return objs

###以下是各个数据表的操作

###########

class Article():
    def get_max_id(self):
        sdb._ensure_connected()
        maxobj = sdb.query("select max(id) as maxid from `sp_posts`")
        return str(maxobj[0]['maxid'])
    
    def get_last_post_add_time(self):
        sdb._ensure_connected()
        obj = sdb.get('SELECT `add_time` FROM `sp_posts` ORDER BY `id` DESC LIMIT 1')
        if obj:
            return datetime.fromtimestamp(obj.add_time)
        else:
            return datetime.utcnow() + timedelta(hours =+ 8)
    
    def count_all_post(self):
        sdb._ensure_connected()
        return sdb.query('SELECT COUNT(*) AS postnum FROM `sp_posts`')[0]['postnum']
    
    def get_all_article(self):
        sdb._ensure_connected()
        return post_list_format(sdb.query("SELECT * FROM `sp_posts` ORDER BY `id` DESC"))
    
    def get_post_for_homepage(self):
        sdb._ensure_connected()
        return post_list_format(sdb.query("SELECT * FROM `sp_posts` ORDER BY `id` DESC LIMIT %s" % str(EACH_PAGE_POST_NUM)))
    
    def get_page_posts(self, direction = 'next', page = 1 , base_id = '', limit = EACH_PAGE_POST_NUM):
        sdb._ensure_connected()
        if direction == 'next':
            return post_list_format(sdb.query("SELECT * FROM `sp_posts` WHERE `id` < %s ORDER BY `id` DESC LIMIT %s" % (str(base_id), str(EACH_PAGE_POST_NUM))))
        else:
            return post_list_format(sdb.query("SELECT * FROM `sp_posts` WHERE `id` > %s ORDER BY `id` ASC LIMIT %s" % (str(base_id), str(EACH_PAGE_POST_NUM))))
    
    def get_article_by_id_detail(self, id):
        sdb._ensure_connected()
        return post_detail_formate(sdb.get('SELECT * FROM `sp_posts` WHERE `id` = %s LIMIT 1' % str(id)))
    
    def get_article_by_id_simple(self, id):
        sdb._ensure_connected()
        return sdb.get('SELECT `id`,`title`,`comment_num`,`closecomment`,`password` FROM `sp_posts` WHERE `id` = %s LIMIT 1' % str(id))
    
    def get_article_by_id_edit(self, id):
        sdb._ensure_connected()
        return sdb.get('SELECT * FROM `sp_posts` WHERE `id` = %s LIMIT 1' % str(id))
    
    def add_new_article(self, params):
        query = "INSERT INTO `sp_posts` (`category`,`title`,`content`,`closecomment`,`tags`,`password`,`add_time`,`edit_time`) values(%s,%s,%s,%s,%s,%s,%s,%s)"
        mdb._ensure_connected()
        return mdb.execute(query, params['category'], params['title'], params['content'], params['closecomment'], params['tags'], params['password'], params['add_time'], params['edit_time'])
    
    def update_post_edit(self, params):
        query = "UPDATE `sp_posts` SET `category` = %s, `title` = %s, `content` = %s, `closecomment` = %s, `tags` = %s, `password` = %s, `edit_time` = %s WHERE `id` = %s LIMIT 1"
        mdb._ensure_connected()
        mdb.execute(query, params['category'], params['title'], params['content'], params['closecomment'], params['tags'], params['password'], params['edit_time'], params['id'])
        ### update 返回不了 lastrowid，直接返回 post id
        return params['id']
            
    def update_post_comment(self, num = 1,id = ''):
        query = "UPDATE `sp_posts` SET `comment_num` = %s WHERE `id` = %s LIMIT 1"
        mdb._ensure_connected()
        return mdb.execute(query, num, id)
    
    def get_post_for_sitemap(self, ids=[]):
        sdb._ensure_connected()
        return sdb.query("SELECT `id`,`edit_time` FROM `sp_posts` WHERE `id` in(%s) ORDER BY `id` DESC LIMIT %s" % (','.join(ids), str(len(ids))))
    
    def del_post_by_id(self, id = ''):
        if id:
            obj = self.get_article_by_id_simple(id)
            if obj:
                limit = obj.comment_num
                mdb._ensure_connected()
                mdb.execute("DELETE FROM `sp_posts` WHERE `id` = %s LIMIT 1", id)
                mdb.execute("DELETE FROM `sp_comments` WHERE `postid` = %s LIMIT %s", id, limit)
                

Article = Article()

class Comment():
    def del_comment_by_id(self, id):
        cobj = self.get_comment_by_id(id)
        postid = cobj.postid
        pobj = Article.get_article_by_id_edit(postid)
        
        mdb._ensure_connected()
        mdb.execute("DELETE FROM `sp_comments` WHERE `id` = %s LIMIT 1", id)
        if pobj:
            Article.update_post_comment( pobj.comment_num-1, postid)
        return
    
    def get_comment_by_id(self, id):
        sdb._ensure_connected()
        return sdb.get('SELECT * FROM `sp_comments` WHERE `id` = %s LIMIT 1' % str(id))
        
    def get_recent_comments(self, limit = RECENT_COMMENT_NUM):
        sdb._ensure_connected()
        return comment_format(sdb.query('SELECT * FROM `sp_comments` ORDER BY `id` DESC LIMIT %s' % str(limit)))
    
    def get_post_page_comments_by_id(self, postid = 0, min_comment_id = 0, limit = EACH_PAGE_COMMENT_NUM):
        
        if min_comment_id == 0:
            sdb._ensure_connected()
            return comment_format(sdb.query('SELECT * FROM `sp_comments` WHERE `postid`= %s ORDER BY `id` DESC LIMIT %s' % (str(postid), str(limit))))
        else:
            sdb._ensure_connected()
            return comment_format(sdb.query('SELECT * FROM `sp_comments` WHERE `postid`= %s AND `id` < %s ORDER BY `id` DESC LIMIT %s' % (str(postid), str(min_comment_id), str(limit))))
        
    def add_new_comment(self, params):
        query = "INSERT INTO `sp_comments` (`postid`,`author`,`email`,`url`,`visible`,`add_time`,`content`) values(%s,%s,%s,%s,%s,%s,%s)"
        mdb._ensure_connected()
        return mdb.execute(query, params['postid'], params['author'], params['email'], params['url'], params['visible'], params['add_time'], params['content'])
        
    def update_comment_edit(self, params):
        query = "UPDATE `sp_comments` SET `author` = %s, `email` = %s, `url` = %s, `visible` = %s, `content` = %s WHERE `id` = %s LIMIT 1"
        mdb._ensure_connected()
        mdb.execute(query, params['author'], params['email'], params['url'], params['visible'], params['content'], params['id'])
        ### update 返回不了 lastrowid，直接返回 id
        return params['id']
    

Comment = Comment()

class Link():
    def get_all_links(self, limit = LINK_NUM):
        sdb._ensure_connected()
        return sdb.query('SELECT * FROM `sp_links` ORDER BY `displayorder` DESC LIMIT %s' % str(limit))
    
    def add_new_link(self, params):
        query = "INSERT INTO `sp_links` (`displayorder`,`name`,`url`) values(%s,%s,%s)"
        mdb._ensure_connected()
        return mdb.execute(query, params['displayorder'], params['name'], params['url'])
    
    def update_link_edit(self, params):
        query = "UPDATE `sp_links` SET `displayorder` = %s, `name` = %s, `url` = %s WHERE `id` = %s LIMIT 1"
        mdb._ensure_connected()
        mdb.execute(query, params['displayorder'], params['name'], params['url'], params['id'])
    
    def del_link_by_id(self, id):
        mdb._ensure_connected()
        mdb.execute("DELETE FROM `sp_links` WHERE `id` = %s LIMIT 1", id)
        
    def get_link_by_id(self, id):
        sdb._ensure_connected()
        return sdb.get('SELECT * FROM `sp_links` WHERE `id` = %s LIMIT 1' % str(id))    

Link = Link()

class Category():
    def get_all_cat_name(self):
        sdb._ensure_connected()
        return sdb.query('SELECT `name`,`id_num` FROM `sp_category` ORDER BY `id` DESC')
        
    def get_all_cat(self):
        sdb._ensure_connected()
        return sdb.query('SELECT * FROM `sp_category` ORDER BY `id` DESC')
    
    def get_all_cat_id(self):
        sdb._ensure_connected()
        return sdb.query('SELECT `id` FROM `sp_category` ORDER BY `id` DESC')
    
    def get_cat_by_name(self, name = ''):
        sdb._ensure_connected()
        return sdb.get('SELECT * FROM `sp_category` WHERE `name` = \'%s\' LIMIT 1' % name)
            
    def get_all_post_num(self, name = ''):
        obj = self.get_cat_by_name(name)
        if obj and obj.content:
            return len(obj.content.split(','))
        else:
            return 0
        
    def get_cat_page_posts(self, name = '', page = 1, limit = EACH_PAGE_POST_NUM):
        obj = self.get_cat_by_name(name)
        if obj:
            page = int(page)
            idlist = obj.content.split(',')
            getids = idlist[limit*(page-1):limit*page]
            sdb._ensure_connected()
            return post_list_format(sdb.query("SELECT * FROM `sp_posts` WHERE `id` in(%s) ORDER BY `id` DESC LIMIT %s" % (','.join(getids), str(len(getids)))))
        else:
            return []
            
    def add_postid_to_cat(self, name = '', postid = ''):
        mdb._ensure_connected()
        #因为 UPDATE 时无论有没有影响行数，都返回0，所以这里要多读一次（从主数据库读）
        obj = mdb.get('SELECT * FROM `sp_category` WHERE `name` = \'%s\' LIMIT 1' % name)        
        
        if obj:
            query = "UPDATE `sp_category` SET `id_num` = `id_num` + 1, `content` =  concat(%s, `content`) WHERE `id` = %s LIMIT 1"
            mdb.execute(query, "%s,"%postid, obj.id)
        else:
            query = "INSERT INTO `sp_category` (`name`,`id_num`,`content`) values(%s,1,%s)"
            mdb.execute(query, name, postid)
    
    def remove_postid_from_cat(self, name = '', postid = ''):
        mdb._ensure_connected()
        obj = mdb.get('SELECT * FROM `sp_category` WHERE `name` = \'%s\' LIMIT 1' % name)        
        if obj:
            idlist = obj.content.split(',')
            if postid in idlist:
                idlist.remove(postid)
                try:
                    idlist.remove('')
                except:
                    pass
                if len(idlist) == 0:
                    mdb.execute("DELETE FROM `sp_category` WHERE `id` = %s LIMIT 1", obj.id)
                else:
                    query = "UPDATE `sp_category` SET `id_num` = %s, `content` =  %s WHERE `id` = %s LIMIT 1"
                    mdb.execute(query, len(idlist), ','.join(idlist), obj.id)                
            else:
                pass
    
    def get_cat_by_id(self, id = ''):
        sdb._ensure_connected()
        return sdb.get('SELECT * FROM `sp_category` WHERE `id` = %s LIMIT 1' % str(id))
    
    def get_sitemap_by_id(self, id=''):
        
        obj = self.get_cat_by_id(id)
        if not obj:
            return ''
        if not obj.content:
            return ''
        
        urlstr = """<url><loc>%s</loc><lastmod>%s</lastmod><changefreq>%s</changefreq><priority>%s</priority></url>\n """        
        urllist = []
        urllist.append('<?xml version="1.0" encoding="UTF-8"?>\n')
        urllist.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        
        urllist.append(urlstr%( "%s/c/%s" % (BASE_URL, str(obj.id)), cnnow().strftime("%Y-%m-%dT%H:%M:%SZ"), 'daily', '0.8'))
        
        objs = Article.get_post_for_sitemap(obj.content.split(','))
        for p in objs:
            if p:
                urllist.append(urlstr%("%s/t/%s" % (BASE_URL, str(p.id)), timestamp_to_datetime(p.edit_time).strftime("%Y-%m-%dT%H:%M:%SZ"), 'weekly', '0.6'))
        
        urllist.append('</urlset>')
        return ''.join(urllist)

Category = Category()

class Tag():
    def get_all_tag_name(self):
        #for add/edit post
        sdb._ensure_connected()
        return sdb.query('SELECT `name` FROM `sp_tags` ORDER BY `id` DESC LIMIT %d' % HOT_TAGS_NUM)

    def get_all_tag(self):
        sdb._ensure_connected()
        return sdb.query('SELECT * FROM `sp_tags` ORDER BY `id` DESC LIMIT %d' % HOT_TAGS_NUM)
    
    def get_hot_tag_name(self):
        #for sider
        sdb._ensure_connected()
        return sdb.query('SELECT `name`,`id_num` FROM `sp_tags` ORDER BY `id_num` DESC LIMIT %d' % HOT_TAGS_NUM)
    
    def get_tag_by_name(self, name = ''):
        sdb._ensure_connected()
        return sdb.get('SELECT * FROM `sp_tags` WHERE `name` = \'%s\' LIMIT 1' % name)

    def get_all_post_num(self, name = ''):
        obj = self.get_tag_by_name(name)
        if obj and obj.content:
            return len(obj.content.split(','))
        else:
            return 0
        
    def get_tag_page_posts(self, name = '', page = 1, limit = EACH_PAGE_POST_NUM):
        obj = self.get_tag_by_name(name)
        if obj and obj.content:
            page = int(page)
            idlist = obj.content.split(',')
            getids = idlist[limit*(page-1):limit*page]
            sdb._ensure_connected()
            return post_list_format(sdb.query("SELECT * FROM `sp_posts` WHERE `id` in(%s) ORDER BY `id` DESC LIMIT %s" % (','.join(getids), len(getids))))
        else:
            return []
            
    def add_postid_to_tags(self, tags = [], postid = ''):
        mdb._ensure_connected()
        for tag in tags:
            obj = mdb.get('SELECT * FROM `sp_tags` WHERE `name` = \'%s\' LIMIT 1' % tag)
            
            if obj:
                query = "UPDATE `sp_tags` SET `id_num` = `id_num` + 1, `content` =  concat(%s, `content`) WHERE `id` = %s LIMIT 1"
                mdb.execute(query, "%s,"%postid, obj.id)
            else:
                query = "INSERT INTO `sp_tags` (`name`,`id_num`,`content`) values(%s,1,%s)"
                mdb.execute(query, tag, postid)
        
    def remove_postid_from_tags(self, tags = [], postid = ''):
        mdb._ensure_connected()
        for tag in tags:
            obj = mdb.get('SELECT * FROM `sp_tags` WHERE `name` = \'%s\' LIMIT 1' % tag)
            
            if obj:
                idlist = obj.content.split(',')
                if postid in idlist:
                    idlist.remove(postid)
                    try:
                        idlist.remove('')
                    except:
                        pass
                    if len(idlist) == 0:
                        mdb.execute("DELETE FROM `sp_tags` WHERE `id` = %s LIMIT 1", obj.id)
                    else:
                        query = "UPDATE `sp_tags` SET `id_num` = %s, `content` =  %s WHERE `id` = %s LIMIT 1"
                        mdb.execute(query, len(idlist), ','.join(idlist), obj.id)                
                else:
                    pass            

Tag = Tag()

class User():
    def check_has_user(self):
        sdb._ensure_connected()
        return sdb.get('SELECT `id` FROM `sp_user` LIMIT 1')

    def get_all_user(self):
        sdb._ensure_connected()
        return sdb.query('SELECT * FROM `sp_user`')

    def get_user_by_name(self, name):
        sdb._ensure_connected()
        return sdb.get('SELECT * FROM `sp_user` WHERE `name` = \'%s\' LIMIT 1' % str(name))

    def add_new_user(self, name = '', pw = ''):
        if name and pw:
            query = "insert into `sp_user` (`name`,`password`) values(%s,%s)"
            mdb._ensure_connected()
            return mdb.execute(query, name, md5(pw.encode('utf-8')).hexdigest())
        else:
            return None
        
    def check_user(self, name = '', pw = ''):
        if name and pw:
            user = self.get_user_by_name(name)
            if user and user.name == name and user.password == pw:
                return True
            else:
                return False
        else:
            return False

User = User()

class MyData():
    def flush_all_data(self):
        sql = """
        TRUNCATE TABLE `sp_category`;
        TRUNCATE TABLE `sp_comments`;
        TRUNCATE TABLE `sp_links`;
        TRUNCATE TABLE `sp_posts`;
        TRUNCATE TABLE `sp_tags`;
        TRUNCATE TABLE `sp_user`;
        """
        mdb._ensure_connected()
        mdb.execute(sql)
        
    def creat_table(self):
        sql = """
DROP TABLE IF EXISTS `sp_category`;
CREATE TABLE IF NOT EXISTS `sp_category` (
  `id` smallint(6) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(17) NOT NULL DEFAULT '',
  `id_num` mediumint(8) unsigned NOT NULL DEFAULT '0',
  `content` mediumtext NOT NULL,
  PRIMARY KEY (`id`),
  KEY `name` (`name`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 AUTO_INCREMENT=1 ;

DROP TABLE IF EXISTS `sp_comments`;
CREATE TABLE IF NOT EXISTS `sp_comments` (
  `id` int(8) unsigned NOT NULL AUTO_INCREMENT,
  `postid` mediumint(8) unsigned NOT NULL DEFAULT '0',
  `author` varchar(20) NOT NULL,
  `email` varchar(30) NOT NULL,
  `url` varchar(75) NOT NULL,
  `visible` tinyint(1) NOT NULL DEFAULT '1',
  `add_time` int(10) unsigned NOT NULL DEFAULT '0',
  `content` mediumtext NOT NULL,
  PRIMARY KEY (`id`),
  KEY `postid` (`postid`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 AUTO_INCREMENT=1 ;

DROP TABLE IF EXISTS `sp_links`;
CREATE TABLE IF NOT EXISTS `sp_links` (
  `id` smallint(6) unsigned NOT NULL AUTO_INCREMENT,
  `displayorder` tinyint(3) NOT NULL DEFAULT '0',
  `name` varchar(100) NOT NULL DEFAULT '',
  `url` varchar(200) NOT NULL DEFAULT '',
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 AUTO_INCREMENT=1 ;

DROP TABLE IF EXISTS `sp_posts`;
CREATE TABLE IF NOT EXISTS `sp_posts` (
  `id` mediumint(8) unsigned NOT NULL AUTO_INCREMENT,
  `category` varchar(17) NOT NULL DEFAULT '',
  `title` varchar(100) NOT NULL DEFAULT '',
  `content` mediumtext NOT NULL,
  `comment_num` mediumint(8) unsigned NOT NULL DEFAULT '0',
  `closecomment` tinyint(1) NOT NULL DEFAULT '0',
  `tags` varchar(100) NOT NULL,
  `password` varchar(8) NOT NULL DEFAULT '',
  `add_time` int(10) unsigned NOT NULL DEFAULT '0',
  `edit_time` int(10) unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `category` (`category`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 AUTO_INCREMENT=1 ;

DROP TABLE IF EXISTS `sp_tags`;
CREATE TABLE IF NOT EXISTS `sp_tags` (
  `id` smallint(6) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(17) NOT NULL DEFAULT '',
  `id_num` mediumint(8) unsigned NOT NULL DEFAULT '0',
  `content` mediumtext NOT NULL,
  PRIMARY KEY (`id`),
  KEY `name` (`name`),
  KEY `id_num` (`id_num`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 AUTO_INCREMENT=1 ;

DROP TABLE IF EXISTS `sp_user`;
CREATE TABLE IF NOT EXISTS `sp_user` (
  `id` smallint(6) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(20) NOT NULL DEFAULT '',
  `password` varchar(32) NOT NULL DEFAULT '',
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8 AUTO_INCREMENT=1 ;

"""
        mdb._ensure_connected()
        mdb.execute(sql)
        
MyData = MyData()

########NEW FILE########
__FILENAME__ = digest
# -*- coding: utf-8 -*-
from urlparse import urlparse
import hmac
from hashlib import sha1
from base64 import urlsafe_b64encode

from .. import rpc
from .. import conf

class Mac(object):
	access = None
	secret = None
	def __init__(self, access=None, secret=None):
		if access is None and secret is None:
			access, secret = conf.ACCESS_KEY, conf.SECRET_KEY
		self.access, self.secret = access, secret

	def __sign(self, data):
		hashed = hmac.new(self.secret, data, sha1)
		return urlsafe_b64encode(hashed.digest())

	def sign(self, data):
		return '%s:%s' % (self.access, self.__sign(data))

	def sign_with_data(self, b):
		data = urlsafe_b64encode(b)
		return '%s:%s:%s' % (self.access, self.__sign(data), data)

	def sign_request(self, path, body, content_type):
		parsedurl = urlparse(path)
		p_query = parsedurl.query
		p_path = parsedurl.path
		data = p_path
		if p_query != "":
			data = ''.join([data, '?', p_query])
		data = ''.join([data, "\n"])

		if body:
			incBody = [
				"application/x-www-form-urlencoded",
			]
			if content_type in incBody:
				data += body

		return '%s:%s' % (self.access, self.__sign(data))


class Client(rpc.Client):
	def __init__(self, host, mac=None):
		if mac is None:
			mac = Mac()
		super(Client, self).__init__(host)
		self.mac = mac

	def round_tripper(self, method, path, body):
		token = self.mac.sign_request(path, body, self._header.get("Content-Type"))
		self.set_header("Authorization", "QBox %s" % token)
		return super(Client, self).round_tripper(method, path, body)

########NEW FILE########
__FILENAME__ = up
# -*- coding: utf-8 -*-
from .. import conf
from .. import rpc


class Client(rpc.Client):
	up_token = None
	
	def __init__(self, up_token, host=None):
		if host is None:
			host = conf.UP_HOST
		self.up_token = up_token
		super(Client, self).__init__(host)

	def round_tripper(self, method, path, body):
		self.set_header("Authorization", "UpToken %s" % self.up_token)
		return super(Client, self).round_tripper(method, path, body)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-

ACCESS_KEY = ""
SECRET_KEY = ""

RS_HOST = "rs.qbox.me"
RSF_HOST = "rsf.qbox.me"
UP_HOST = "up.qiniu.com"

from . import __version__
USER_AGENT = "qiniu python-sdk v%s" % __version__

########NEW FILE########
__FILENAME__ = fop
# -*- coding:utf-8 -*-
import json

class Exif(object):
	def make_request(self, url):
		return '%s?exif' % url


class ImageView(object):
	mode = 1 # 1或2
	width = None # width 默认为0，表示不限定宽度
	height = None
	quality = None # 图片质量, 1-100
	format = None # 输出格式, jpg, gif, png, tif 等图片格式

	def make_request(self, url):
		target = []
		target.append('%s' % self.mode)
		
		if self.width is not None:
			target.append("w/%s" % self.width)

		if self.height is not None:
			target.append("h/%s" % self.height)

		if self.quality is not None:
			target.append("q/%s" % self.quality)

		if self.format is not None:
			target.append("format/%s" % self.format)

		return "%s?imageView/%s" % (url, '/'.join(target))


class ImageInfo(object):
	def make_request(self, url):
		return '%s?imageInfo' % url

########NEW FILE########
__FILENAME__ = httplib_chunk
"""
Modified from standard httplib

1. HTTPConnection can send trunked data.
2. Remove httplib's automatic Content-Length insertion when data is a file-like object.
"""

# -*- coding: utf-8 -*-

import httplib
from httplib import _CS_REQ_STARTED, _CS_REQ_SENT
import string
import os
from array import array

class HTTPConnection(httplib.HTTPConnection):

	def send(self, data, is_chunked=False):
		"""Send `data' to the server."""
		if self.sock is None:
			if self.auto_open:
				self.connect()
			else:
				raise NotConnected()

		if self.debuglevel > 0:
			print "send:", repr(data)
		blocksize = 8192
		if hasattr(data,'read') and not isinstance(data, array):
			if self.debuglevel > 0: print "sendIng a read()able"
			datablock = data.read(blocksize)
			while datablock:
				if self.debuglevel > 0:
					print 'chunked:', is_chunked
				if is_chunked:
					if self.debuglevel > 0: print 'send: with trunked data'
					lenstr = string.upper(hex(len(datablock))[2:])
					self.sock.sendall('%s\r\n%s\r\n' % (lenstr, datablock))
				else:
					self.sock.sendall(datablock)
				datablock = data.read(blocksize)
			if is_chunked:
				self.sock.sendall('0\r\n\r\n')
		else:
			self.sock.sendall(data)


	def _set_content_length(self, body):
		# Set the content-length based on the body.
		thelen = None
		try:
			thelen = str(len(body))
		except (TypeError, AttributeError), te:
			# Don't send a length if this failed
			if self.debuglevel > 0: print "Cannot stat!!"

		if thelen is not None:
			self.putheader('Content-Length', thelen)
			return True
		return False


	def _send_request(self, method, url, body, headers):
		# Honor explicitly requested Host: and Accept-Encoding: headers.
		header_names = dict.fromkeys([k.lower() for k in headers])
		skips = {}
		if 'host' in header_names:
			skips['skip_host'] = 1
		if 'accept-encoding' in header_names:
			skips['skip_accept_encoding'] = 1

		self.putrequest(method, url, **skips)

		is_chunked = False
		if body and header_names.get('Transfer-Encoding') == 'chunked':
			is_chunked = True
		elif body and ('content-length' not in header_names):
			is_chunked = not self._set_content_length(body)
			if is_chunked:
				self.putheader('Transfer-Encoding', 'chunked')
		for hdr, value in headers.iteritems():
			self.putheader(hdr, value)

		self.endheaders(body, is_chunked=is_chunked)


	def endheaders(self, message_body=None, is_chunked=False):
		"""Indicate that the last header line has been sent to the server.

		This method sends the request to the server.  The optional
		message_body argument can be used to pass a message body
		associated with the request.  The message body will be sent in
		the same packet as the message headers if it is string, otherwise it is
		sent as a separate packet.
		"""
		if self.__state == _CS_REQ_STARTED:
			self.__state = _CS_REQ_SENT
		else:
			raise CannotSendHeader()
		self._send_output(message_body, is_chunked=is_chunked)


	def _send_output(self, message_body=None, is_chunked=False):
		"""Send the currently buffered request and clear the buffer.

		Appends an extra \\r\\n to the buffer.
		A message_body may be specified, to be appended to the request.
		"""
		self._buffer.extend(("", ""))
		msg = "\r\n".join(self._buffer)
		del self._buffer[:]
		# If msg and message_body are sent in a single send() call,
		# it will avoid performance problems caused by the interaction
		# between delayed ack and the Nagle algorithm.
		if isinstance(message_body, str):
			msg += message_body
			message_body = None
		self.send(msg)
		if message_body is not None:
			#message_body was not a string (i.e. it is a file) and
			#we must run the risk of Nagle
			self.send(message_body, is_chunked=is_chunked)


########NEW FILE########
__FILENAME__ = io
# -*- coding: utf-8 -*-
from base64 import urlsafe_b64encode
import rpc
import conf
import random
import string
try:
	import zlib as binascii
except ImportError:
	import binascii


# @gist PutExtra
class PutExtra(object):
	params = {}
	mime_type = 'application/octet-stream'
	crc32 = ""
	check_crc = 0
# @endgist


def put(uptoken, key, data, extra=None):
	""" put your data to Qiniu

	If key is None, the server will generate one.
	data may be str or read()able object.
	"""
	fields = {
	}

	if not extra:
		extra = PutExtra()

	if extra.params:
		for k in extra.params:
			fields[k] = str(extra.params[k])

	if extra.check_crc:
		fields["crc32"] = str(extra.crc32)

	if key is not None:
		fields['key'] = key

	fields["token"] = uptoken

	fname = key
	if fname is None:
		fname = _random_str(9)
	elif fname is '':
		fname = 'index.html'
	files = [
		{'filename': fname, 'data': data, 'mime_type': extra.mime_type},
	]
	return rpc.Client(conf.UP_HOST).call_with_multipart("/", fields, files)


def put_file(uptoken, key, localfile, extra=None):
	""" put a file to Qiniu

	If key is None, the server will generate one.
	"""
	if extra is not None and extra.check_crc == 1:
		extra.crc32 = _get_file_crc32(localfile)
	with open(localfile, 'rb') as f:
		return put(uptoken, key, f, extra)


_BLOCK_SIZE = 1024 * 1024 * 4

def _get_file_crc32(filepath):
	with open(filepath, 'rb') as f:
		block = f.read(_BLOCK_SIZE)
		crc = 0
		while len(block) != 0:
			crc = binascii.crc32(block, crc) & 0xFFFFFFFF
			block = f.read(_BLOCK_SIZE)
	return crc


def _random_str(length):
	lib = string.ascii_lowercase
	return ''.join([random.choice(lib) for i in range(0, length)])

########NEW FILE########
__FILENAME__ = resumable_io
# -*- coding: utf-8 -*-
import os
try:
	import zlib as binascii
except ImportError:
	import binascii
from base64 import urlsafe_b64encode

import auth.up
import conf

_workers = 1
_task_queue_size = _workers * 4
_chunk_size = 256 * 1024
_try_times = 3
_block_size = 4 * 1024 * 1024

class Error(Exception):
	value = None
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return self.value

err_invalid_put_progress = Error("invalid put progress")
err_put_failed = Error("resumable put failed")
err_unmatched_checksum = Error("unmatched checksum")

def setup(chunk_size=0, try_times=0):
	"""
	 * chunk_size      => 默认的Chunk大小，不设定则为256k
	 * try_times       => 默认的尝试次数，不设定则为3
	"""
	global _chunk_size, _try_times

	if chunk_size == 0:
		chunk_size = 1 << 18

	if try_times == 0:
		try_times = 3

	_chunk_size, _try_times = chunk_size, try_times

# ----------------------------------------------------------
def gen_crc32(data):
	return binascii.crc32(data) & 0xffffffff

class PutExtra(object):
	callback_params = None # 当 uptoken 指定了 CallbackUrl，则 CallbackParams 必须非空
	bucket = None          # 当前是必选项，但未来会去掉
	custom_meta = None     # 可选。用户自定义 Meta，不能超过 256 字节
	mimetype = None        # 可选。在 uptoken 没有指定 DetectMime 时，用户客户端可自己指定 MimeType
	chunk_size = None      # 可选。每次上传的Chunk大小
	try_times = None       # 可选。尝试次数
	progresses = None      # 可选。上传进度
	notify = lambda self, idx, size, ret: None # 可选。进度提示
	notify_err = lambda self, idx, size, err: None

	def __init__(self, bucket):
		self.bucket = bucket

def put_file(uptoken, key, localfile, extra):
	""" 上传文件 """
	f = open(localfile, "rb")
	statinfo = os.stat(localfile)
	ret = put(uptoken, key, f, statinfo.st_size, extra)
	f.close()
	return ret

def put(uptoken, key, f, fsize, extra):
	""" 上传二进制流, 通过将data "切片" 分段上传 """
	if not isinstance(extra, PutExtra):
		print("extra must the instance of PutExtra")
		return

	block_cnt = block_count(fsize)
	if extra.progresses is None:
		extra.progresses = [None for i in xrange(0, block_cnt)]
	else:
		if not len(extra.progresses) == block_cnt:
			return None, err_invalid_put_progress

	if extra.try_times is None:
		extra.try_times = _try_times

	if extra.chunk_size is None:
		extra.chunk_size = _chunk_size

	client = auth.up.Client(uptoken)
	for i in xrange(0, block_cnt):
		try_time = extra.try_times
		read_length = _block_size
		if (i+1)*_block_size > fsize:
			read_length = fsize - i*_block_size
		data_slice = f.read(read_length)
		while True:
			err = resumable_block_put(client, data_slice, i, extra)
			if err is None:
				break

			try_time -= 1
			if try_time <= 0:
				return None, err_put_failed
			print err, ".. retry"

	return mkfile(client, key, fsize, extra)

# ----------------------------------------------------------

def resumable_block_put(client, block, index, extra):
	block_size = len(block)

	if extra.progresses[index] is None or "ctx" not in extra.progresses[index]:
		end_pos = extra.chunk_size-1
		if block_size < extra.chunk_size:
			end_pos = block_size-1
		chunk = block[: end_pos]
		crc32 = gen_crc32(chunk)
		chunk = bytearray(chunk)
		extra.progresses[index], err = mkblock(client, block_size, chunk)
		if not extra.progresses[index]["crc32"] == crc32:
			return err_unmatched_checksum
		if err is not None:
			extra.notify_err(index, end_pos + 1, err)
			return err
		extra.notify(index, end_pos + 1, extra.progresses[index])

	while extra.progresses[index]["offset"] < block_size:
		offset = extra.progresses[index]["offset"]
		chunk = block[offset: offset+extra.chunk_size-1]
		crc32 = gen_crc32(chunk)
		chunk = bytearray(chunk)
		extra.progresses[index], err = putblock(client, extra.progresses[index], chunk)
		if not extra.progresses[index]["crc32"] == crc32:
			return err_unmatched_checksum
		if err is not None:
			extra.notify_err(index, len(chunk), err)
			return err
		extra.notify(index, len(chunk), extra.progresses[index])

def block_count(size):
	global _block_size
	return size / _block_size + 1

def mkblock(client, block_size, first_chunk):
	url = "http://%s/mkblk/%s" % (conf.UP_HOST, block_size)
	content_type = "application/octet-stream"
	return client.call_with(url, first_chunk, content_type, len(first_chunk))

def putblock(client, block_ret, chunk):
	url = "%s/bput/%s/%s" % (block_ret["host"], block_ret["ctx"], block_ret["offset"])
	content_type = "application/octet-stream"
	return client.call_with(url, chunk, content_type, len(chunk))

def mkfile(client, key, fsize, extra):
	encoded_entry = urlsafe_b64encode("%s:%s" % (extra.bucket, key))
	url = ["http://%s/rs-mkfile/%s/fsize/%s" % (conf.UP_HOST, encoded_entry, fsize)]

	if extra.mimetype:
		url.append("mimeType/%s" % urlsafe_b64encode(extra.mimetype))

	if extra.custom_meta:
		url.append("meta/%s" % urlsafe_b64encode(extra.custom_meta))

	if extra.callback_params:
		url.append("params/%s" % urlsafe_b64encode(extra.callback_params))

	url = "/".join(url)
	body = ",".join([i["ctx"] for i in extra.progresses])
	return client.call_with(url, body, "text/plain", len(body))

########NEW FILE########
__FILENAME__ = rpc
# -*- coding: utf-8 -*-
import httplib_chunk as httplib
import json
import cStringIO
import conf


class Client(object):
	_conn = None
	_header = None

	def __init__(self, host):
		self._conn = httplib.HTTPConnection(host)
		self._header = {}

	def round_tripper(self, method, path, body):
		self._conn.request(method, path, body, self._header)
		resp = self._conn.getresponse()
		return resp

	def call(self, path):
		return self.call_with(path, None)

	def call_with(self, path, body, content_type=None, content_length=None):
		ret = None

		self.set_header("User-Agent", conf.USER_AGENT)
		if content_type is not None:
			self.set_header("Content-Type", content_type)

		if content_length is not None:
			self.set_header("Content-Length", content_length)

		resp = self.round_tripper("POST", path, body)
		try:
			ret = resp.read()
			ret = json.loads(ret)
		except IOError, e:
			return None, e
		except ValueError:
			pass

		if resp.status / 100 != 2:
			err_msg = ret if "error" not in ret else ret["error"]
			detail = resp.getheader("x-log", None)
			if detail is not None:
				err_msg += ", detail:%s" % detail

			return None, err_msg

		return ret, None

	def call_with_multipart(self, path, fields=None, files=None):
		"""
		 *  fields => {key}
		 *  files => [{filename, data, content_type}]
		"""
		content_type, mr = self.encode_multipart_formdata(fields, files)
		return self.call_with(path, mr, content_type, mr.length())

	def call_with_form(self, path, ops):
		"""
		 * ops => {"key": value/list()}
		"""

		body = []
		for i in ops:
			if isinstance(ops[i], (list, tuple)):
				data = ('&%s=' % i).join(ops[i])
			else:
				data = ops[i]

			body.append('%s=%s' % (i, data))
		body = '&'.join(body)

		content_type = "application/x-www-form-urlencoded"
		return self.call_with(path, body, content_type, len(body))

	def set_header(self, field, value):
		self._header[field] = value

	def set_headers(self, headers):
		self._header.update(headers)

	def encode_multipart_formdata(self, fields, files):
		"""
		 *  fields => {key}
		 *  files => [{filename, data, content_type}]
		 *  return content_type, content_length, body
		"""
		if files is None:
			files = []
		if fields is None:
			fields = {}

		readers = []
		BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
		CRLF = '\r\n'
		L1 = []
		for key in fields:
			L1.append('--' + BOUNDARY)
			L1.append('Content-Disposition: form-data; name="%s"' % key)
			L1.append('')
			L1.append(fields[key])
		b1 = CRLF.join(L1)
		readers.append(b1)

		for file_info in files:
			L = []
			L.append('')
			L.append('--' + BOUNDARY)
			disposition = "Content-Disposition: form-data;"
			filename = _qiniu_escape(file_info.get('filename'))
			L.append('%s name="file"; filename="%s"' % (disposition, filename))
			L.append('Content-Type: %s' % file_info.get('content_type', 'application/octet-stream'))
			L.append('')
			L.append('')
			b2 = CRLF.join(L)
			readers.append(b2)

			data = file_info.get('data')
			readers.append(data)

		L3 = ['', '--' + BOUNDARY + '--', '']
		b3 = CRLF.join(L3)
		readers.append(b3)

		content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
		return content_type, MultiReader(readers)

def _qiniu_escape(s):
	edits = [('\\', '\\\\'), ('\"', '\\\"')]
	for (search, replace) in edits:
		s = s.replace(search, replace)
	return s


class MultiReader(object):
	""" class MultiReader([readers...])

	MultiReader returns a read()able object that's the logical concatenation of
	the provided input readers.  They're read sequentially.
	"""

	def __init__(self, readers):
		self.readers = []
		self.content_length = 0
		self.valid_content_length = True
		for r in readers:
			if hasattr(r, 'read'):
				if self.valid_content_length:
					length = self._get_content_length(r)
					if length is not None:
						self.content_length += length
					else:
						self.valid_content_length = False
			else:
				buf = r
				if not isinstance(buf, basestring):
					buf = str(buf)
				buf = encode_unicode(buf)
				r = cStringIO.StringIO(buf)
				self.content_length += len(buf)
			self.readers.append(r)


	# don't name it __len__, because the length of MultiReader is not alway valid.
	def length(self):
		return self.content_length if self.valid_content_length else None


	def _get_content_length(self, reader):
		data_len = None
		if hasattr(reader, 'seek') and hasattr(reader, 'tell'):
			try:
				reader.seek(0, 2)
				data_len= reader.tell()
				reader.seek(0, 0)
			except OSError:
				# Don't send a length if this failed
				data_len = None
		return data_len

	def read(self, n=-1):
		if n is None or n == -1:
			return ''.join([encode_unicode(r.read()) for r in self.readers])
		else:
			L = []
			while len(self.readers) > 0 and n > 0:
				b = self.readers[0].read(n)
				if len(b) == 0:
					self.readers = self.readers[1:]
				else:
					L.append(encode_unicode(b))
					n -= len(b)
			return ''.join(L)


def encode_unicode(u):
	if isinstance(u, unicode):
		u = u.encode('utf8')
	return u

########NEW FILE########
__FILENAME__ = rs
# -*- coding: utf-8 -*-
from base64 import urlsafe_b64encode

from ..auth import digest
from .. import conf

class Client(object):
	conn = None
	def __init__(self, mac=None):
		if mac is None:
			mac = digest.Mac()
		self.conn = digest.Client(host=conf.RS_HOST, mac=mac)

	def stat(self, bucket, key):
		return self.conn.call(uri_stat(bucket, key))

	def delete(self, bucket, key):
		return self.conn.call(uri_delete(bucket, key))

	def move(self, bucket_src, key_src, bucket_dest, key_dest):
		return self.conn.call(uri_move(bucket_src, key_src, bucket_dest, key_dest))

	def copy(self, bucket_src, key_src, bucket_dest, key_dest):
		return self.conn.call(uri_copy(bucket_src, key_src, bucket_dest, key_dest))

	def batch(self, ops):
		return self.conn.call_with_form("/batch", dict(op=ops))

	def batch_stat(self, entries):
		ops = []
		for entry in entries:
			ops.append(uri_stat(entry.bucket, entry.key))
		return self.batch(ops)

	def batch_delete(self, entries):
		ops = []
		for entry in entries:
			ops.append(uri_delete(entry.bucket, entry.key))
		return self.batch(ops)

	def batch_move(self, entries):
		ops = []
		for entry in entries:
			ops.append(uri_move(entry.src.bucket, entry.src.key, 
				entry.dest.bucket, entry.dest.key))
		return self.batch(ops)

	def batch_copy(self, entries):
		ops = []
		for entry in entries:
			ops.append(uri_copy(entry.src.bucket, entry.src.key, 
				entry.dest.bucket, entry.dest.key))
		return self.batch(ops)

class EntryPath(object):
	bucket = None
	key = None
	def __init__(self, bucket, key):
		self.bucket = bucket
		self.key = key

class EntryPathPair:
	src = None
	dest = None
	def __init__(self, src, dest):
		self.src = src
		self.dest = dest

def uri_stat(bucket, key):
	return "/stat/%s" % urlsafe_b64encode("%s:%s" % (bucket, key))

def uri_delete(bucket, key):
	return "/delete/%s" % urlsafe_b64encode("%s:%s" % (bucket, key))

def uri_move(bucket_src, key_src, bucket_dest, key_dest):
	src = urlsafe_b64encode("%s:%s" % (bucket_src, key_src))
	dest = urlsafe_b64encode("%s:%s" % (bucket_dest, key_dest))
	return "/move/%s/%s" % (src, dest)

def uri_copy(bucket_src, key_src, bucket_dest, key_dest):
	src = urlsafe_b64encode("%s:%s" % (bucket_src, key_src))
	dest = urlsafe_b64encode("%s:%s" % (bucket_dest, key_dest))
	return "/copy/%s/%s" % (src, dest)

########NEW FILE########
__FILENAME__ = rs_token
# -*- coding: utf-8 -*-
import json
import time
import urllib

from ..auth import digest
from ..import rpc

# @gist PutPolicy
class PutPolicy(object):
	scope = None             # 可以是 bucketName 或者 bucketName:key
	expires = 3600           # 默认是 3600 秒
	callbackUrl = None
	callbackBody = None
	returnUrl = None
	returnBody = None
	endUser = None
	asyncOps = None

	def __init__(self, scope):
		self.scope = scope
# @endgist

	def token(self, mac=None):
		if mac is None:
			mac = digest.Mac()
		token = dict(
			scope = self.scope,
			deadline = int(time.time()) + self.expires,
		)

		if self.callbackUrl is not None:
			token["callbackUrl"] = self.callbackUrl

		if self.callbackBody is not None:
			token["callbackBody"] = self.callbackBody

		if self.returnUrl is not None:
			token["returnUrl"] = self.returnUrl

		if self.returnBody is not None:
			token["returnBody"] = self.returnBody

		if self.endUser is not None:
			token["endUser"] = self.endUser

		if self.asyncOps is not None:
			token["asyncOps"] = self.asyncOps
		
		b = json.dumps(token, separators=(',',':'))
		return mac.sign_with_data(b)

class GetPolicy(object):
	expires = 3600
	def __init__(self):
		pass
	
	def make_request(self, base_url, mac=None):
		'''
		 *  return private_url
		'''
		if mac is None:
			mac = digest.Mac()

		deadline = int(time.time()) + self.expires
		if '?' in base_url:
			base_url += '&'
		else:
			base_url += '?'
		base_url = '%se=%s' % (base_url, str(deadline))

		token = mac.sign(base_url)
		return '%s&token=%s' % (base_url, token)


def make_base_url(domain, key):
	'''
	 * domain => str
	 * key => str
	 * return base_url
	'''
	key = rpc.encode_unicode(key)
	return 'http://%s/%s' % (domain, urllib.quote(key))

########NEW FILE########
__FILENAME__ = rs_test
# -*- coding: utf-8 -*-
import unittest
import os
import random
import string

from qiniu import rs
from qiniu import conf

def r(length):
	lib = string.ascii_uppercase
	return ''.join([random.choice(lib) for i in range(0, length)])

conf.ACCESS_KEY = os.getenv("QINIU_ACCESS_KEY")
conf.SECRET_KEY = os.getenv("QINIU_SECRET_KEY")
key = 'QINIU_UNIT_TEST_PIC'
bucket_name = os.getenv("QINIU_TEST_BUCKET")
noexist_key = 'QINIU_UNIT_TEST_NOEXIST' + r(30)
key2 = "rs_demo_test_key_1_" + r(5)
key3 = "rs_demo_test_key_2_" + r(5)
key4 = "rs_demo_test_key_3_" + r(5)

class TestRs(unittest.TestCase):
	def test_stat(self):
		r = rs.Client()
		ret, err = r.stat(bucket_name, key)
		assert err is None
		assert ret is not None
		
		# error
		_, err = r.stat(bucket_name, noexist_key)
		assert err is not None
	
	def test_delete_move_copy(self):
		r = rs.Client()
		r.delete(bucket_name, key2)
		r.delete(bucket_name, key3)
		
		ret, err = r.copy(bucket_name, key, bucket_name, key2)
		assert err is None, err
		
		ret, err = r.move(bucket_name, key2, bucket_name, key3)
		assert err is None, err
		
		ret, err = r.delete(bucket_name, key3)
		assert err is None, err
		
		# error
		_, err = r.delete(bucket_name, key2)
		assert err is not None
		
		_, err = r.delete(bucket_name, key3)
		assert err is not None

	def test_batch_stat(self):
		r = rs.Client()
		entries = [
			rs.EntryPath(bucket_name, key),
			rs.EntryPath(bucket_name, key2),
		]
		ret, err = r.batch_stat(entries)
		assert err is None
		self.assertEqual(ret[0]["code"], 200)
		self.assertEqual(ret[1]["code"], 612)

	def test_batch_delete_move_copy(self):
		r = rs.Client()
		e1 = rs.EntryPath(bucket_name, key)
		e2 = rs.EntryPath(bucket_name, key2)
		e3 = rs.EntryPath(bucket_name, key3)
		e4 = rs.EntryPath(bucket_name, key4)
		r.batch_delete([e2, e3, e4])
		
		# copy
		entries = [
			rs.EntryPathPair(e1, e2),
			rs.EntryPathPair(e1, e3),
		]
		ret, err = r.batch_copy(entries)
		assert err is None
		self.assertEqual(ret[0]["code"], 200)
		self.assertEqual(ret[1]["code"], 200)
		
		ret, err = r.batch_move([rs.EntryPathPair(e2, e4)])
		assert err is None
		self.assertEqual(ret[0]["code"], 200)
		
		ret, err = r.batch_delete([e3, e4])
		assert err is None
		self.assertEqual(ret[0]["code"], 200)
		
		r.batch_delete([e2, e3, e4])

if __name__ == "__main__":
	unittest.main()

########NEW FILE########
__FILENAME__ = rs_token_test
# -*- coding: utf-8 -*-
import unittest
import os
import json
from base64 import urlsafe_b64decode as decode
from base64 import urlsafe_b64encode as encode
from hashlib import sha1
import hmac
import urllib

from qiniu import conf
from qiniu import rpc
from qiniu import rs

conf.ACCESS_KEY = os.getenv("QINIU_ACCESS_KEY")
conf.SECRET_KEY = os.getenv("QINIU_SECRET_KEY")
bucket_name = os.getenv("QINIU_TEST_BUCKET")
domain = os.getenv("QINIU_TEST_DOMAIN")
key = 'QINIU_UNIT_TEST_PIC'

class TestToken(unittest.TestCase):
	def test_put_policy(self):
		policy = rs.PutPolicy(bucket_name)
		policy.endUser = "hello!"
		tokens = policy.token().split(':')
		self.assertEqual(conf.ACCESS_KEY, tokens[0])
		data = json.loads(decode(tokens[2]))
		self.assertEqual(data["scope"], bucket_name)
		self.assertEqual(data["endUser"], policy.endUser)

		new_hmac = encode(hmac.new(conf.SECRET_KEY, tokens[2], sha1).digest())
		self.assertEqual(new_hmac, tokens[1])

	def test_get_policy(self):
		base_url = rs.make_base_url(domain, key)
		policy = rs.GetPolicy()
		private_url = policy.make_request(base_url)

		f = urllib.urlopen(private_url)
		body = f.read()
		f.close()
		self.assertEqual(len(body)>100, True)


class Test_make_base_url(unittest.TestCase):
	def test_unicode(self):
		url1 = rs.make_base_url('1.com', '你好')
		url2 = rs.make_base_url('1.com', u'你好')
		assert url1 == url2

if __name__ == "__main__":
	unittest.main()

########NEW FILE########
__FILENAME__ = rsf
# -*- coding: utf-8 -*-
import auth.digest
import conf
import urllib

EOF = 'EOF'


class Client(object):
	conn = None
	def __init__(self, mac=None):
		if mac is None:
			mac = auth.digest.Mac()
		self.conn = auth.digest.Client(host=conf.RSF_HOST, mac=mac)
		
	def list_prefix(self, bucket, prefix=None, marker=None, limit=None):
		'''前缀查询:
		 * bucket => str
		 * prefix => str
		 * marker => str
		 * limit => int
		 * return ret => {'items': items, 'marker': markerOut}, err => str

		1. 首次请求 marker = None
		2. 无论 err 值如何，均应该先看 ret.get('items') 是否有内容
		3. 如果后续没有更多数据，err 返回 EOF，markerOut 返回 None（但不通过该特征来判断是否结束） 
		'''
		ops = {
			'bucket': bucket,
		}
		if marker is not None:
			ops['marker'] = marker
		if limit is not None:
			ops['limit'] = limit
		if prefix is not None:
			ops['prefix'] = prefix
		url = '%s?%s' % ('/list', urllib.urlencode(ops))
		ret, err = self.conn.call_with(url, body=None, content_type='application/x-www-form-urlencoded')
		if not ret.get('marker'):
			err = EOF
		return ret, err

########NEW FILE########
__FILENAME__ = conf_test
# -*- coding: utf-8 -*-
import unittest
from qiniu import conf

class TestConfig(unittest.TestCase):
	def test_USER_AGENT(self):
		assert len(conf.USER_AGENT) >= len('qiniu python-sdk')
	
if __name__ == '__main__':
	unittest.main()

########NEW FILE########
__FILENAME__ = fop_test
# -*- coding:utf-8 -*-
import unittest
import os
from qiniu import fop

pic = "http://cheneya.qiniudn.com/hello_jpg"

class TestFop(unittest.TestCase):
	def test_exif(self):
		ie = fop.Exif()
		ret = ie.make_request(pic)
		self.assertEqual(ret, "%s?exif" % pic)

	def test_imageView(self):
		iv = fop.ImageView()
		iv.height = 100
		ret = iv.make_request(pic)
		self.assertEqual(ret, "%s?imageView/1/h/100" % pic)
		
		iv.quality = 20
		iv.format = "png"
		ret = iv.make_request(pic)
		self.assertEqual(ret, "%s?imageView/1/h/100/q/20/format/png" % pic)

	def test_imageInfo(self):
		ii = fop.ImageInfo()
		ret = ii.make_request(pic)
		self.assertEqual(ret, "%s?imageInfo" % pic)


if __name__ == '__main__':
	unittest.main()

########NEW FILE########
__FILENAME__ = io_test
# -*- coding: utf-8 -*-
import os
import unittest
import string
import random
import urllib
try:
	import zlib as binascii
except ImportError:
	import binascii
import cStringIO

from qiniu import conf
from qiniu import rs
from qiniu import io

conf.ACCESS_KEY = os.getenv("QINIU_ACCESS_KEY")
conf.SECRET_KEY = os.getenv("QINIU_SECRET_KEY")
bucket_name = os.getenv("QINIU_TEST_BUCKET")

policy = rs.PutPolicy(bucket_name)
extra = io.PutExtra()
extra.mime_type = "text/plain"
extra.params = {'x:a':'a'}

def r(length):
	lib = string.ascii_uppercase
	return ''.join([random.choice(lib) for i in range(0, length)])

class TestUp(unittest.TestCase):
	def test(self):
		def test_put():
			key = "test_%s" % r(9)
			params = "op=3"
			data = "hello bubby!"
			extra.check_crc = 2
			extra.crc32 = binascii.crc32(data) & 0xFFFFFFFF
			ret, err = io.put(policy.token(), key, data, extra)
			assert err is None
			assert ret['key'] == key

		def test_put_same_crc():
			key = "test_%s" % r(9)
			data = "hello bubby!"
			extra.check_crc = 2
			ret, err = io.put(policy.token(), key, data, extra)
			assert err is None
			assert ret['key'] == key

		def test_put_no_key():
			data = r(100)
			extra.check_crc = 0
			ret, err = io.put(policy.token(), key=None, data=data, extra=extra)
			assert err is None
			assert ret['hash'] == ret['key']

		def test_put_quote_key():
			data = r(100)
			key = 'a\\b\\c"你好' + r(9)
			ret, err = io.put(policy.token(), key, data)
			print err
			assert err is None
			assert ret['key'].encode('utf8') == key

			data = r(100)
			key = u'a\\b\\c"你好' + r(9)
			ret, err = io.put(policy.token(), key, data)
			assert err is None
			assert ret['key'] == key

		def test_put_unicode1():
			key = "test_%s" % r(9) + '你好'
			data = key
			ret, err = io.put(policy.token(), key, data, extra)
			assert err is None
			assert ret[u'key'].endswith(u'你好')

		def test_put_unicode2():
			key = "test_%s" % r(9) + '你好'
			data = key
			data = data.decode('utf8')
			ret, err = io.put(policy.token(), key, data)
			assert err is None
			assert ret[u'key'].endswith(u'你好')

		def test_put_unicode3():
			key = "test_%s" % r(9) + '你好'
			data = key
			key = key.decode('utf8')
			ret, err = io.put(policy.token(), key, data)
			assert err is None
			assert ret[u'key'].endswith(u'你好')

		def test_put_unicode4():
			key = "test_%s" % r(9) + '你好'
			data = key
			key = key.decode('utf8')
			data = data.decode('utf8')
			ret, err = io.put(policy.token(), key, data)
			assert err is None
			assert ret[u'key'].endswith(u'你好')

		def test_put_StringIO():
			key = "test_%s" % r(9)
			data = cStringIO.StringIO('hello buddy!')
			ret, err = io.put(policy.token(), key, data)
			assert err is None
			assert ret['key'] == key

		def test_put_urlopen():
			key = "test_%s" % r(9)
			data = urllib.urlopen('http://cheneya.qiniudn.com/hello_jpg')
			ret, err = io.put(policy.token(), key, data)
			assert err is None
			assert ret['key'] == key

		def test_put_no_length():
			class test_reader(object):
				def __init__(self):
					self.data = 'abc'
					self.pos = 0
				def read(self, n=None):
					if n is None or n < 0:
						newpos = len(self.data)
					else:
						newpos = min(self.pos+n, len(self.data))
					r = self.data[self.pos: newpos]
					self.pos = newpos
					return r
			key = "test_%s" % r(9)
			data = test_reader()

			extra.check_crc = 2
			extra.crc32 = binascii.crc32('abc') & 0xFFFFFFFF
			ret, err = io.put(policy.token(), key, data, extra)
			assert err is None
			assert ret['key'] == key

		test_put()
		test_put_same_crc()
		test_put_no_key()
		test_put_quote_key()
		test_put_unicode1()
		test_put_unicode2()
		test_put_unicode3()
		test_put_unicode4()
		test_put_StringIO()
		test_put_urlopen()
		test_put_no_length()

	def test_put_file(self):
		localfile = "%s" % __file__
		key = "test_%s" % r(9)

		extra.check_crc = 1
		ret, err = io.put_file(policy.token(), key, localfile, extra)
		assert err is None
		assert ret['key'] == key

	def test_put_crc_fail(self):
		key = "test_%s" % r(9)
		data = "hello bubby!"
		extra.check_crc = 2
		extra.crc32 = "wrong crc32"
		ret, err = io.put(policy.token(), key, data, extra)
		assert err is not None


class Test_get_file_crc32(unittest.TestCase):
	def test_get_file_crc32(self):
		file_path = '%s' % __file__

		data = None
		with open(file_path, 'rb') as f:
			data = f.read()
		io._BLOCK_SIZE = 4
		assert binascii.crc32(data) & 0xFFFFFFFF == io._get_file_crc32(file_path)


if __name__ == "__main__":
	unittest.main()

########NEW FILE########
__FILENAME__ = resumable_io_test
# -*- coding: utf-8 -*-
import os
import unittest
import string
import random
import platform
try:
	import zlib as binascii
except ImportError:
	import binascii
import urllib
import tempfile
import shutil

from qiniu import conf
from qiniu.auth import up
from qiniu import resumable_io
from qiniu import rs

bucket = os.getenv("QINIU_TEST_BUCKET")
conf.ACCESS_KEY = os.getenv("QINIU_ACCESS_KEY")
conf.SECRET_KEY = os.getenv("QINIU_SECRET_KEY")


def r(length):
	lib = string.ascii_uppercase
	return ''.join([random.choice(lib) for i in range(0, length)])

class TestBlock(unittest.TestCase):
	def test_block(self):
		policy = rs.PutPolicy(bucket)
		uptoken = policy.token()
		client = up.Client(uptoken)

		rets = [0, 0]
		data_slice_2 = "\nbye!"
		ret, err = resumable_io.mkblock(client, len(data_slice_2), data_slice_2)
		assert err is None, err
		self.assertEqual(ret["crc32"], binascii.crc32(data_slice_2))

		extra = resumable_io.PutExtra(bucket)
		extra.mimetype = "text/plain"
		extra.progresses = [ret]
		lens = 0
		for i in xrange(0, len(extra.progresses)):
			lens += extra.progresses[i]["offset"]

		key = u"sdk_py_resumable_block_4_%s" % r(9)
		ret, err = resumable_io.mkfile(client, key, lens, extra)
		assert err is None, err
		self.assertEqual(ret["hash"], "FtCFo0mQugW98uaPYgr54Vb1QsO0", "hash not match")
		rs.Client().delete(bucket, key)

	def test_put(self):
		src = urllib.urlopen("http://cheneya.qiniudn.com/hello_jpg")
		ostype = platform.system()
		if ostype.lower().find("windows") != -1:
			tmpf = "".join([os.getcwd(), os.tmpnam()])
		else:
			tmpf = os.tmpnam()
		dst = open(tmpf, 'wb')
		shutil.copyfileobj(src, dst)
		src.close()

		policy = rs.PutPolicy(bucket)
		extra = resumable_io.PutExtra(bucket)
		extra.bucket = bucket
		key = "sdk_py_resumable_block_5_%s" % r(9)
		localfile = dst.name
		ret, err = resumable_io.put_file(policy.token(), key, localfile, extra)
		dst.close()
		os.remove(tmpf)

		assert err is None, err
		self.assertEqual(ret["hash"], "FnyTMUqPNRTdk1Wou7oLqDHkBm_p", "hash not match")
		rs.Client().delete(bucket, key)


if __name__ == "__main__":
	unittest.main()

########NEW FILE########
__FILENAME__ = rpc_test
# -*- coding: utf-8 -*-
import StringIO
import unittest

from qiniu import rpc
from qiniu import conf

def round_tripper(client, method, path, body):
	pass

class ClsTestClient(rpc.Client):
	def round_tripper(self, method, path, body):
		round_tripper(self, method, path, body)
		return super(ClsTestClient, self).round_tripper(method, path, body)

client = ClsTestClient(conf.RS_HOST)

class TestClient(unittest.TestCase):
	def test_call(self):
		global round_tripper

		def tripper(client, method, path, body):
			self.assertEqual(path, "/hello")
			assert body is None

		round_tripper = tripper
		client.call("/hello")

	def test_call_with(self):
		global round_tripper
		def tripper(client, method, path, body):
			self.assertEqual(body, "body")

		round_tripper = tripper
		client.call_with("/hello", "body")

	def test_call_with_multipart(self):
		global round_tripper
		def tripper(client, method, path, body):
			target_type = "multipart/form-data"
			self.assertTrue(client._header["Content-Type"].startswith(target_type))
			start_index = client._header["Content-Type"].find("boundary")
			boundary = client._header["Content-Type"][start_index + 9: ]
			dispostion = 'Content-Disposition: form-data; name="auth"'
			tpl = "--%s\r\n%s\r\n\r\n%s\r\n--%s--\r\n" % (boundary, dispostion,
					"auth_string", boundary)
			self.assertEqual(len(tpl), client._header["Content-Length"])
			self.assertEqual(len(tpl), body.length())

		round_tripper = tripper
		client.call_with_multipart("/hello", fields={"auth": "auth_string"})

	def test_call_with_form(self):
		global round_tripper
		def tripper(client, method, path, body):
			self.assertEqual(body, "action=a&op=a&op=b")
			target_type = "application/x-www-form-urlencoded"
			self.assertEqual(client._header["Content-Type"], target_type)
			self.assertEqual(client._header["Content-Length"], len(body))

		round_tripper = tripper
		client.call_with_form("/hello", dict(op=["a", "b"], action="a"))


class TestMultiReader(unittest.TestCase):
	def test_multi_reader1(self):
		a = StringIO.StringIO('你好')
		b = StringIO.StringIO('abcdefg')
		c = StringIO.StringIO(u'悲剧')
		mr = rpc.MultiReader([a, b, c])
		data = mr.read()
		assert data.index('悲剧') > data.index('abcdefg')

	def test_multi_reader2(self):
		a = StringIO.StringIO('你好')
		b = StringIO.StringIO('abcdefg')
		c = StringIO.StringIO(u'悲剧')
		mr = rpc.MultiReader([a, b, c])
		data = mr.read(8)
		assert len(data) is 8


def encode_multipart_formdata2(fields, files):
	if files is None:
		files = []
	if fields is None:
		fields = []

	BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
	CRLF = '\r\n'
	L = []
	for (key, value) in fields:
		L.append('--' + BOUNDARY)
		L.append('Content-Disposition: form-data; name="%s"' % key)
		L.append('')
		L.append(value)
	for (key, filename, value) in files:
		L.append('--' + BOUNDARY)
		disposition = "Content-Disposition: form-data;"
		L.append('%s name="%s"; filename="%s"' % (disposition, key, filename))
		L.append('Content-Type: application/octet-stream')
		L.append('')
		L.append(value)
	L.append('--' + BOUNDARY + '--')
	L.append('')
	body = CRLF.join(L)
	content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
	return content_type, body


class TestEncodeMultipartFormdata(unittest.TestCase):
	def test_encode(self):
		fields = {'a': '1', 'b': '2'}
		files = [
			{
				'filename': 'key1',
				'data': 'data1',
				'mime_type': 'application/octet-stream',
			},
			{
				'filename': 'key2',
				'data': 'data2',
				'mime_type': 'application/octet-stream',
			}
		]
		content_type, mr = rpc.Client('localhost').encode_multipart_formdata(fields, files)
		t, b = encode_multipart_formdata2(
			[('a', '1'), ('b', '2')],
			[('file', 'key1', 'data1'), ('file', 'key2', 'data2')]
		)
		assert t == content_type
		assert len(b) == mr.length()

	def test_unicode(self):
		def test1():
			files = [{'filename': '你好', 'data': '你好', 'mime_type': ''}]
			_, body = rpc.Client('localhost').encode_multipart_formdata(None, files)
			return len(body.read())
		def test2():
			files = [{'filename': u'你好', 'data': '你好', 'mime_type': ''}]
			_, body = rpc.Client('localhost').encode_multipart_formdata(None, files)
			return len(body.read())
		def test3():
			files = [{'filename': '你好', 'data': u'你好', 'mime_type': ''}]
			_, body = rpc.Client('localhost').encode_multipart_formdata(None, files)
			return len(body.read())
		def test4():
			files = [{'filename': u'你好', 'data': u'你好', 'mime_type': ''}]
			_, body = rpc.Client('localhost').encode_multipart_formdata(None, files)
			return len(body.read())

		assert test1() == test2()
		assert test2() == test3()
		assert test3() == test4()


if __name__ == "__main__":
	unittest.main()

########NEW FILE########
__FILENAME__ = rsf_test
# -*- coding: utf-8 -*-
import unittest
from qiniu import rsf
from qiniu import conf

import os
conf.ACCESS_KEY = os.getenv("QINIU_ACCESS_KEY")
conf.SECRET_KEY = os.getenv("QINIU_SECRET_KEY")
bucket_name = os.getenv("QINIU_TEST_BUCKET")

class TestRsf(unittest.TestCase):
	def test_list_prefix(self):
		c = rsf.Client()
		ret, err = c.list_prefix(bucket_name, limit = 1)
		self.assertEqual(err is rsf.EOF or err is None, True)
		assert len(ret.get('items')) == 1


if __name__ == "__main__":
	unittest.main()

########NEW FILE########
__FILENAME__ = setting
# -*- coding: utf-8 -*-
from os import environ

SAEPY_LOG_VERSION = '0.0.2' # 当前SAEpy-log版本
APP_NAME = environ.get("APP_NAME", "")
debug = not APP_NAME

##下面需要修改
SITE_TITLE = u"博客标题" #博客标题
SITE_TITLE2 = u"博客标题2" #显示在边栏上头（有些模板用不到）
SITE_SUB_TITLE = u"一个简单的运行在SAE上的blog" #副标题
KEYWORDS = u"起床,吃饭,工作,睡觉" #博客关键字
SITE_DECR = u"这是运行在SAE上的个人博客，记录生活，记录工作。" #博客描述，给搜索引擎看
ADMIN_NAME = u"admin" #发博文的作者
NOTICE_MAIL = u"" #常用的，容易看到的接收提醒邮件，如QQ 邮箱，仅作收件用

###配置邮件发送信息，提醒邮件用的，必须正确填写，建议用Gmail
MAIL_FROM = '' #xxx@gmail.com
MAIL_SMTP = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_PASSWORD = 'xxx' #你的邮箱登录密码，用以发提醒邮件

#放在网页底部的统计代码
ANALYTICS_CODE = """
<script type="text/javascript">
var _bdhmProtocol = (("https:" == document.location.protocol) ? " https://" : " http://");
document.write(unescape("%3Cscript src='" + _bdhmProtocol + "hm.baidu.com/h.js%3F4feb6150395fa48b6494812f2e7a724d' type='text/javascript'%3E%3C/script%3E"));
</script>
""" 

##### 存放附件的地方 可选SAE Storage 或 七牛
## 1） 使用SAE Storage 服务（保存上传的附件），需在SAE管理面板创建，
## 注意，优先使用 SAE Storage，若用七牛下面值请留空值
STORAGE_DOMAIN_NAME = ""  #attachment

## 2) 七牛 注册可获永久10G空间和每月10G流量，注册地址 http://t.cn/z8h5lsg
QN_AK = "" #七牛 ACCESS_KEY
QN_SK = "" #七牛 SECRET_KEY
QN_BUCKET = "" #空间名称 , 如 upload

###设置容易调用的jquery 文件
JQUERY = "http://lib.sinaapp.com/js/jquery/1.6.2/jquery.min.js"
#JQUERY = "http://code.jquery.com/jquery-1.6.2.min.js"
#JQUERY = "/static/jquery-plugin/jquery-1.6.4.js"

COPY_YEAR = '2012' #页脚的 © 2011 

MAJOR_DOMAIN = '%s.sinaapp.com' % APP_NAME #主域名，默认是SAE 的二级域名
#MAJOR_DOMAIN = 'www.yourdomain.com'

##博客使用的主题，目前可选 default/octopress/octopress-disqus
##你也可以把自己喜欢的wp主题移植过来，
#制作方法参见 http://saepy.sinaapp.com/t/49
THEME = 'octopress'

#使用disqus 评论系统，如果你使用就填 website shortname，
#申请地址 http://disqus.com/
DISQUS_WEBSITE_SHORTNAME = ''

####友情链接列表，在管理后台也实现了管理，下面的链接列表仍然有效并排在前面
LINK_BROLL = [
    {"text": 'SAEpy blog', "url": 'http://saepy.sinaapp.com'},
    {"text": 'Sina App Engine', "url": 'http://sae.sina.com.cn/'},    
]

#当发表新博文时自动ping RPC服务，中文的下面三个差不多了
XML_RPC_ENDPOINTS = [
    'http://blogsearch.google.com/ping/RPC2', 
    'http://rpc.pingomatic.com/', 
    'http://ping.baidu.com/ping/RPC2'
]

##如果要在本地测试则需要配置Mysql 数据库信息
if debug:
    MYSQL_DB = 'app_saepy'
    MYSQL_USER = 'root'
    MYSQL_PASS = '123'
    MYSQL_HOST_M = '127.0.0.1'
    MYSQL_HOST_S = '127.0.0.1'
    MYSQL_PORT = '3306'

####除了修改上面的设置，你还需在SAE 后台开通下面几项服务：
# 1 初始化 Mysql
# 2 建立一个名为 attachment 的 Storage
# 3 启用Memcache，初始化大小为1M的 mc，大小可以调，日后文章多了，PV多了可增加
# 4 创建一个 名为 default 的 Task Queue
# 详见 http://saepy.sinaapp.com/t/50 详细安装指南
############## 下面不建议修改 ###########################
if debug:
    BASE_URL = 'http://127.0.0.1:8080'
else:
    BASE_URL = 'http://%s'%MAJOR_DOMAIN

LANGUAGE = 'zh-CN'
COMMENT_DEFAULT_VISIBLE = 1 #0/1 #发表评论时是否显示 设为0时则需要审核才显示
EACH_PAGE_POST_NUM = 7 #每页显示文章数
EACH_PAGE_COMMENT_NUM = 10 #每页评论数
RELATIVE_POST_NUM = 5 #显示相关文章数
SHORTEN_CONTENT_WORDS = 150 #文章列表截取的字符数
DESCRIPTION_CUT_WORDS = 100 #meta description 显示的字符数
RECENT_COMMENT_NUM = 5 #边栏显示最近评论数
RECENT_COMMENT_CUT_WORDS = 20 #边栏评论显示字符数
LINK_NUM = 30 #边栏显示的友情链接数
MAX_COMMENT_NUM_A_DAY = 10 #客户端设置Cookie 限制每天发的评论数

PAGE_CACHE = not debug #本地没有Memcache 服务
PAGE_CACHE_TIME = 3600*24 #默认页面缓存时间 

HOT_TAGS_NUM = 100 #右侧热门标签显示数

MAX_IDLE_TIME = 5 #数据库最大空闲时间 SAE文档说是30 其实更小，设为5，没问题就不要改了

########NEW FILE########
__FILENAME__ = tenjin
##
## $Release: 1.0.1 $
## $Copyright: copyright(c) 2007-2011 kuwata-lab.com all rights reserved. $
## $License: MIT License $
##
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the
## "Software"), to deal in the Software without restriction, including
## without limitation the rights to use, copy, modify, merge, publish,
## distribute, sublicense, and/or sell copies of the Software, and to
## permit persons to whom the Software is furnished to do so, subject to
## the following conditions:
##
## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.
##
## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
## MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
## LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
## OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
## WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
##

"""Very fast and light-weight template engine based embedded Python.
   See User's Guide and examples for details.
   http://www.kuwata-lab.com/tenjin/pytenjin-users-guide.html
   http://www.kuwata-lab.com/tenjin/pytenjin-examples.html
"""

__version__  = "$Release: 1.0.1 $"[10:-2]
__license__  = "$License: MIT License $"[10:-2]
__all__      = ('Template', 'Engine', )


import sys, os, re, time, marshal
from time import time as _time
from os.path import getmtime as _getmtime
from os.path import isfile as _isfile
random = pickle = unquote = None   # lazy import
python3 = sys.version_info[0] == 3
python2 = sys.version_info[0] == 2

logger = None


##
## utilities
##

def _write_binary_file(filename, content):
    global random
    if random is None: from random import random
    tmpfile = filename + str(random())[1:]
    f = open(tmpfile, 'w+b')     # on windows, 'w+b' is preffered than 'wb'
    try:
        f.write(content)
    finally:
        f.close()
    if os.path.exists(tmpfile):
        try:
            os.rename(tmpfile, filename)
        except:
            os.remove(filename)  # on windows, existing file should be removed before renaming
            os.rename(tmpfile, filename)

def _read_binary_file(filename):
    f = open(filename, 'rb')
    try:
        return f.read()
    finally:
        f.close()

codecs = None    # lazy import

def _read_text_file(filename, encoding=None):
    global codecs
    if not codecs: import codecs
    f = codecs.open(filename, encoding=(encoding or 'utf-8'))
    try:
        return f.read()
    finally:
        f.close()

def _read_template_file(filename, encoding=None):
    s = _read_binary_file(filename)          ## binary(=str)
    if encoding: s = s.decode(encoding)      ## binary(=str) to unicode
    return s

_basestring = basestring
_unicode    = unicode
_bytes      = str

def _ignore_not_found_error(f, default=None):
    try:
        return f()
    except OSError, ex:
        if ex.errno == 2:   # error: No such file or directory
            return default
        raise

def create_module(module_name, dummy_func=None, **kwargs):
    """ex. mod = create_module('tenjin.util')"""
    mod = type(sys)(module_name)
    mod.__file__ = __file__
    mod.__dict__.update(kwargs)
    sys.modules[module_name] = mod
    if dummy_func:
        exec(dummy_func.func_code, mod.__dict__)
    return mod

def _raise(exception_class, *args):
    raise exception_class(*args)


##
## helper method's module
##

def _dummy():
    global unquote
    unquote = None
    global to_str, escape, echo, new_cycle, generate_tostrfunc
    global start_capture, stop_capture, capture_as, captured_as, CaptureContext
    global _p, _P, _decode_params

    def generate_tostrfunc(encode=None, decode=None):
        """Generate 'to_str' function with encode or decode encoding.
           ex. generate to_str() function which encodes unicode into binary(=str).
              to_str = tenjin.generate_tostrfunc(encode='utf-8')
              repr(to_str(u'hoge'))  #=> 'hoge' (str)
           ex. generate to_str() function which decodes binary(=str) into unicode.
              to_str = tenjin.generate_tostrfunc(decode='utf-8')
              repr(to_str('hoge'))   #=> u'hoge' (unicode)
        """
        if encode:
            if decode:
                raise ValueError("can't specify both encode and decode encoding.")
            else:
                def to_str(val,   _str=str, _unicode=unicode, _isa=isinstance, _encode=encode):
                    """Convert val into string or return '' if None. Unicode will be encoded into binary(=str)."""
                    if _isa(val, _str):     return val
                    if val is None:         return ''
                    #if _isa(val, _unicode): return val.encode(_encode)  # unicode to binary(=str)
                    if _isa(val, _unicode):
                        return val.encode(_encode)  # unicode to binary(=str)
                    return _str(val)
        else:
            if decode:
                def to_str(val,   _str=str, _unicode=unicode, _isa=isinstance, _decode=decode):
                    """Convert val into string or return '' if None. Binary(=str) will be decoded into unicode."""
                    #if _isa(val, _str):     return val.decode(_decode)  # binary(=str) to unicode
                    if _isa(val, _str):
                        return val.decode(_decode)
                    if val is None:         return ''
                    if _isa(val, _unicode): return val
                    return _unicode(val)
            else:
                def to_str(val,   _str=str, _unicode=unicode, _isa=isinstance):
                    """Convert val into string or return '' if None. Both binary(=str) and unicode will be retruned as-is."""
                    if _isa(val, _str):     return val
                    if val is None:         return ''
                    if _isa(val, _unicode): return val
                    return _str(val)
        return to_str

    to_str = generate_tostrfunc(encode='utf-8')  # or encode=None?

    def echo(string):
        """add string value into _buf. this is equivarent to '#{string}'."""
        lvars = sys._getframe(1).f_locals   # local variables
        lvars['_buf'].append(string)

    def new_cycle(*values):
        """Generate cycle object.
           ex.
             cycle = new_cycle('odd', 'even')
             print(cycle())   #=> 'odd'
             print(cycle())   #=> 'even'
             print(cycle())   #=> 'odd'
             print(cycle())   #=> 'even'
        """
        def gen(values):
            i, n = 0, len(values)
            while True:
                yield values[i]
                i = (i + 1) % n
        return gen(values).next

    class CaptureContext(object):

        def __init__(self, name, store_to_context=True, lvars=None):
            self.name  = name
            self.store_to_context = store_to_context
            self.lvars = lvars or sys._getframe(1).f_locals

        def __enter__(self):
            lvars = self.lvars
            self._buf_orig = lvars['_buf']
            lvars['_buf']    = _buf = []
            lvars['_extend'] = _buf.extend
            return self

        def __exit__(self, *args):
            lvars = self.lvars
            _buf = lvars['_buf']
            lvars['_buf']    = self._buf_orig
            lvars['_extend'] = self._buf_orig.extend
            lvars[self.name] = self.captured = ''.join(_buf)
            if self.store_to_context and '_context' in lvars:
                lvars['_context'][self.name] = self.captured

        def __iter__(self):
            self.__enter__()
            yield self
            self.__exit__()

    def start_capture(varname=None, _depth=1):
        """(obsolete) start capturing with name."""
        lvars = sys._getframe(_depth).f_locals
        capture_context = CaptureContext(varname, None, lvars)
        lvars['_capture_context'] = capture_context
        capture_context.__enter__()

    def stop_capture(store_to_context=True, _depth=1):
        """(obsolete) stop capturing and return the result of capturing.
           if store_to_context is True then the result is stored into _context[varname].
        """
        lvars = sys._getframe(_depth).f_locals
        capture_context = lvars.pop('_capture_context', None)
        if not capture_context:
            raise Exception('stop_capture(): start_capture() is not called before.')
        capture_context.store_to_context = store_to_context
        capture_context.__exit__()
        return capture_context.captured

    def capture_as(name, store_to_context=True):
        """capture partial of template."""
        return CaptureContext(name, store_to_context, sys._getframe(1).f_locals)

    def captured_as(name, _depth=1):
        """helper method for layout template.
           if captured string is found then append it to _buf and return True,
           else return False.
        """
        lvars = sys._getframe(_depth).f_locals   # local variables
        if name in lvars:
            _buf = lvars['_buf']
            _buf.append(lvars[name])
            return True
        return False

    def _p(arg):
        """ex. '/show/'+_p("item['id']") => "/show/#{item['id']}" """
        return '<`#%s#`>' % arg    # decoded into #{...} by preprocessor

    def _P(arg):
        """ex. '<b>%s</b>' % _P("item['id']") => "<b>${item['id']}</b>" """
        return '<`$%s$`>' % arg    # decoded into ${...} by preprocessor

    def _decode_params(s):
        """decode <`#...#`> and <`$...$`> into #{...} and ${...}"""
        global unquote
        if unquote is None:
            from urllib import unquote
        dct = { 'lt':'<', 'gt':'>', 'amp':'&', 'quot':'"', '#039':"'", }
        def unescape(s):
            #return s.replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&#039;', "'").replace('&amp;',  '&')
            return re.sub(r'&(lt|gt|quot|amp|#039);',  lambda m: dct[m.group(1)],  s)
        s = to_str(s)
        s = re.sub(r'%3C%60%23(.*?)%23%60%3E', lambda m: '#{%s}' % unquote(m.group(1)), s)
        s = re.sub(r'%3C%60%24(.*?)%24%60%3E', lambda m: '${%s}' % unquote(m.group(1)), s)
        s = re.sub(r'&lt;`#(.*?)#`&gt;',   lambda m: '#{%s}' % unescape(m.group(1)), s)
        s = re.sub(r'&lt;`\$(.*?)\$`&gt;', lambda m: '${%s}' % unescape(m.group(1)), s)
        s = re.sub(r'<`#(.*?)#`>', r'#{\1}', s)
        s = re.sub(r'<`\$(.*?)\$`>', r'${\1}', s)
        return s

helpers = create_module('tenjin.helpers', _dummy, sys=sys, re=re)
helpers.__all__ = ['to_str', 'escape', 'echo', 'new_cycle', 'generate_tostrfunc',
                   'start_capture', 'stop_capture', 'capture_as', 'captured_as',
                   'not_cached', 'echo_cached', 'cache_as',
                   '_p', '_P', '_decode_params',
                   ]
generate_tostrfunc = helpers.generate_tostrfunc


##
## escaped module
##
def _dummy():
    global is_escaped, as_escaped, to_escaped
    global Escaped, EscapedStr, EscapedUnicode
    global __all__
    __all__ = ('is_escaped', 'as_escaped', 'to_escaped', ) #'Escaped', 'EscapedStr',

    class Escaped(object):
        """marking class that object is already escaped."""
        pass

    def is_escaped(value):
        """return True if value is marked as escaped, else return False."""
        return isinstance(value, Escaped)

    class EscapedStr(str, Escaped):
        """string class which is marked as escaped."""
        pass

    class EscapedUnicode(unicode, Escaped):
        """unicode class which is marked as escaped."""
        pass

    def as_escaped(s):
        """mark string as escaped, without escaping."""
        if isinstance(s, str):     return EscapedStr(s)
        if isinstance(s, unicode): return EscapedUnicode(s)
        raise TypeError("as_escaped(%r): expected str or unicode." % (s, ))

    def to_escaped(value):
        """convert any value into string and escape it.
           if value is already marked as escaped, don't escape it."""
        if hasattr(value, '__html__'):
            value = value.__html__()
        if is_escaped(value):
            #return value     # EscapedUnicode should be convered into EscapedStr
            return as_escaped(_helpers.to_str(value))
        #if isinstance(value, _basestring):
        #    return as_escaped(_helpers.escape(value))
        return as_escaped(_helpers.escape(_helpers.to_str(value)))

escaped = create_module('tenjin.escaped', _dummy, _helpers=helpers)


##
## module for html
##
def _dummy():
    global escape_html, escape_xml, escape, tagattr, tagattrs, _normalize_attrs
    global checked, selected, disabled, nl2br, text2html, nv, js_link

    #_escape_table = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }
    #_escape_pattern = re.compile(r'[&<>"]')
    ##_escape_callable = lambda m: _escape_table[m.group(0)]
    ##_escape_callable = lambda m: _escape_table.__get__(m.group(0))
    #_escape_get     = _escape_table.__getitem__
    #_escape_callable = lambda m: _escape_get(m.group(0))
    #_escape_sub     = _escape_pattern.sub

    #def escape_html(s):
    #    return s                                          # 3.02

    #def escape_html(s):
    #    return _escape_pattern.sub(_escape_callable, s)   # 6.31

    #def escape_html(s):
    #    return _escape_sub(_escape_callable, s)           # 6.01

    #def escape_html(s, _p=_escape_pattern, _f=_escape_callable):
    #    return _p.sub(_f, s)                              # 6.27

    #def escape_html(s, _sub=_escape_pattern.sub, _callable=_escape_callable):
    #    return _sub(_callable, s)                         # 6.04

    #def escape_html(s):
    #    s = s.replace('&', '&amp;')
    #    s = s.replace('<', '&lt;')
    #    s = s.replace('>', '&gt;')
    #    s = s.replace('"', '&quot;')
    #    return s                                          # 5.83

    def escape_html(s):
        """Escape '&', '<', '>', '"' into '&amp;', '&lt;', '&gt;', '&quot;'."""
        return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;')   # 5.72

    escape_xml = escape_html   # for backward compatibility

    def tagattr(name, expr, value=None, escape=True):
        """(experimental) Return ' name="value"' if expr is true value, else '' (empty string).
           If value is not specified, expr is used as value instead."""
        if not expr and expr != 0: return _escaped.as_escaped('')
        if value is None: value = expr
        if escape: value = _escaped.to_escaped(value)
        return _escaped.as_escaped(' %s="%s"' % (name, value))

    def tagattrs(**kwargs):
        """(experimental) built html tag attribtes.
           ex.
           >>> tagattrs(klass='main', size=20)
           ' class="main" size="20"'
           >>> tagattrs(klass='', size=0)
           ''
        """
        kwargs = _normalize_attrs(kwargs)
        esc = _escaped.to_escaped
        s = ''.join([ ' %s="%s"' % (k, esc(v)) for k, v in kwargs.iteritems() if v or v == 0 ])
        return _escaped.as_escaped(s)

    def _normalize_attrs(kwargs):
        if 'klass'    in kwargs: kwargs['class']    = kwargs.pop('klass')
        if 'checked'  in kwargs: kwargs['checked']  = kwargs.pop('checked')  and 'checked'  or None
        if 'selected' in kwargs: kwargs['selected'] = kwargs.pop('selected') and 'selected' or None
        if 'disabled' in kwargs: kwargs['disabled'] = kwargs.pop('disabled') and 'disabled' or None
        return kwargs

    def checked(expr):
        """return ' checked="checked"' if expr is true."""
        return _escaped.as_escaped(expr and ' checked="checked"' or '')

    def selected(expr):
        """return ' selected="selected"' if expr is true."""
        return _escaped.as_escaped(expr and ' selected="selected"' or '')

    def disabled(expr):
        """return ' disabled="disabled"' if expr is true."""
        return _escaped.as_escaped(expr and ' disabled="disabled"' or '')

    def nl2br(text):
        """replace "\n" to "<br />\n" and return it."""
        if not text:
            return _escaped.as_escaped('')
        return _escaped.as_escaped(text.replace('\n', '<br />\n'))

    def text2html(text, use_nbsp=True):
        """(experimental) escape xml characters, replace "\n" to "<br />\n", and return it."""
        if not text:
            return _escaped.as_escaped('')
        s = _escaped.to_escaped(text)
        if use_nbsp: s = s.replace('  ', ' &nbsp;')
        #return nl2br(s)
        s = s.replace('\n', '<br />\n')
        return _escaped.as_escaped(s)

    def nv(name, value, sep=None, **kwargs):
        """(experimental) Build name and value attributes.
           ex.
           >>> nv('rank', 'A')
           'name="rank" value="A"'
           >>> nv('rank', 'A', '.')
           'name="rank" value="A" id="rank.A"'
           >>> nv('rank', 'A', '.', checked=True)
           'name="rank" value="A" id="rank.A" checked="checked"'
           >>> nv('rank', 'A', '.', klass='error', style='color:red')
           'name="rank" value="A" id="rank.A" class="error" style="color:red"'
        """
        name  = _escaped.to_escaped(name)
        value = _escaped.to_escaped(value)
        s = sep and 'name="%s" value="%s" id="%s"' % (name, value, name+sep+value) \
                or  'name="%s" value="%s"'         % (name, value)
        html = kwargs and s + tagattrs(**kwargs) or s
        return _escaped.as_escaped(html)

    def js_link(label, onclick, **kwargs):
        s = kwargs and tagattrs(**kwargs) or ''
        html = '<a href="javascript:undefined" onclick="%s;return false"%s>%s</a>' % \
                  (_escaped.to_escaped(onclick), s, _escaped.to_escaped(label))
        return _escaped.as_escaped(html)

html = create_module('tenjin.html', _dummy, helpers=helpers, _escaped=escaped)
helpers.escape = html.escape_html
helpers.html = html   # for backward compatibility


##
## utility function to set default encoding of template files
##
_template_encoding = (None, 'utf-8')    # encodings for decode and encode

def set_template_encoding(decode=None, encode=None):
    """Set default encoding of template files.
       This should be called before importing helper functions.
       ex.
          ## I like template files to be unicode-base like Django.
          import tenjin
          tenjin.set_template_encoding('utf-8')  # should be called before importing helpers
          from tenjin.helpers import *
    """
    global _template_encoding
    if _template_encoding == (decode, encode):
        return
    if decode and encode:
        raise ValueError("set_template_encoding(): cannot specify both decode and encode.")
    if not decode and not encode:
        raise ValueError("set_template_encoding(): decode or encode should be specified.")
    if decode:
        Template.encoding = decode    # unicode base template
        helpers.to_str = helpers.generate_tostrfunc(decode=decode)
    else:
        Template.encoding = None      # binary base template
        helpers.to_str = helpers.generate_tostrfunc(encode=encode)
    _template_encoding = (decode, encode)


##
## Template class
##

class TemplateSyntaxError(SyntaxError):

    def build_error_message(self):
        ex = self
        if not ex.text:
            return self.args[0]
        return ''.join([
            "%s:%s:%s: %s\n" % (ex.filename, ex.lineno, ex.offset, ex.msg, ),
            "%4d: %s\n"      % (ex.lineno, ex.text.rstrip(), ),
            "     %s^\n"     % (' ' * ex.offset, ),
        ])


class Template(object):
    """Convert and evaluate embedded python string.
       See User's Guide and examples for details.
       http://www.kuwata-lab.com/tenjin/pytenjin-users-guide.html
       http://www.kuwata-lab.com/tenjin/pytenjin-examples.html
    """

    ## default value of attributes
    filename   = None
    encoding   = None
    escapefunc = 'escape'
    tostrfunc  = 'to_str'
    indent     = 8
    preamble   = None    # "_buf = []; _expand = _buf.expand; _to_str = to_str; _escape = escape"
    postamble  = None    # "print ''.join(_buf)"
    smarttrim  = None
    args       = None
    timestamp  = None
    trace      = False   # if True then '<!-- begin: file -->' and '<!-- end: file -->' are printed

    def __init__(self, filename=None, encoding=None, input=None, escapefunc=None, tostrfunc=None,
                       indent=None, preamble=None, postamble=None, smarttrim=None, trace=None):
        """Initailizer of Template class.

           filename:str (=None)
             Filename to convert (optional). If None, no convert.
           encoding:str (=None)
             Encoding name. If specified, template string is converted into
             unicode object internally.
             Template.render() returns str object if encoding is None,
             else returns unicode object if encoding name is specified.
           input:str (=None)
             Input string. In other words, content of template file.
             Template file will not be read if this argument is specified.
           escapefunc:str (='escape')
             Escape function name.
           tostrfunc:str (='to_str')
             'to_str' function name.
           indent:int (=8)
             Indent width.
           preamble:str or bool (=None)
             Preamble string which is inserted into python code.
             If true, '_buf = []; ' is used insated.
           postamble:str or bool (=None)
             Postamble string which is appended to python code.
             If true, 'print("".join(_buf))' is used instead.
           smarttrim:bool (=None)
             If True then "<div>\\n#{_context}\\n</div>" is parsed as
             "<div>\\n#{_context}</div>".
        """
        if encoding   is not None:  self.encoding   = encoding
        if escapefunc is not None:  self.escapefunc = escapefunc
        if tostrfunc  is not None:  self.tostrfunc  = tostrfunc
        if indent     is not None:  self.indent     = indent
        if preamble   is not None:  self.preamble   = preamble
        if postamble  is not None:  self.postamble  = postamble
        if smarttrim  is not None:  self.smarttrim  = smarttrim
        if trace      is not None:  self.trace      = trace
        #
        if preamble  is True:  self.preamble  = "_buf = []"
        if postamble is True:  self.postamble = "print(''.join(_buf))"
        if input:
            self.convert(input, filename)
            self.timestamp = False      # False means 'file not exist' (= Engine should not check timestamp of file)
        elif filename:
            self.convert_file(filename)
        else:
            self._reset()

    def _reset(self, input=None, filename=None):
        self.script   = None
        self.bytecode = None
        self.input    = input
        self.filename = filename
        if input != None:
            i = input.find("\n")
            if i < 0:
                self.newline = "\n"   # or None
            elif len(input) >= 2 and input[i-1] == "\r":
                self.newline = "\r\n"
            else:
                self.newline = "\n"
        self._localvars_assignments_added = False

    def _localvars_assignments(self):
        return "_extend=_buf.extend;_to_str=%s;_escape=%s; " % (self.tostrfunc, self.escapefunc)

    def before_convert(self, buf):
        if self.preamble:
            eol = self.input.startswith('<?py') and "\n" or "; "
            buf.append(self.preamble + eol)

    def after_convert(self, buf):
        if self.postamble:
            if buf and not buf[-1].endswith("\n"):
                buf.append("\n")
            buf.append(self.postamble + "\n")

    def convert_file(self, filename):
        """Convert file into python script and return it.
           This is equivarent to convert(open(filename).read(), filename).
        """
        input = _read_template_file(filename)
        return self.convert(input, filename)

    def convert(self, input, filename=None):
        """Convert string in which python code is embedded into python script and return it.

           input:str
             Input string to convert into python code.
           filename:str (=None)
             Filename of input. this is optional but recommended to report errors.
        """
        if self.encoding and isinstance(input, str):
            input = input.decode(self.encoding)
        self._reset(input, filename)
        buf = []
        self.before_convert(buf)
        self.parse_stmts(buf, input)
        self.after_convert(buf)
        script = ''.join(buf)
        self.script = script
        return script

    STMT_PATTERN = (r'<\?py( |\t|\r?\n)(.*?) ?\?>([ \t]*\r?\n)?', re.S)

    def stmt_pattern(self):
        pat = self.STMT_PATTERN
        if isinstance(pat, tuple):
            pat = self.__class__.STMT_PATTERN = re.compile(*pat)
        return pat

    def parse_stmts(self, buf, input):
        if not input: return
        rexp = self.stmt_pattern()
        is_bol = True
        index = 0
        for m in rexp.finditer(input):
            mspace, code, rspace = m.groups()
            #mspace, close, rspace = m.groups()
            #code = input[m.start()+4+len(mspace):m.end()-len(close)-(rspace and len(rspace) or 0)]
            text = input[index:m.start()]
            index = m.end()
            ## detect spaces at beginning of line
            lspace = None
            if text == '':
                if is_bol:
                    lspace = ''
            elif text[-1] == '\n':
                lspace = ''
            else:
                rindex = text.rfind('\n')
                if rindex < 0:
                    if is_bol and text.isspace():
                        lspace, text = text, ''
                else:
                    s = text[rindex+1:]
                    if s.isspace():
                        lspace, text = s, text[:rindex+1]
            #is_bol = rspace is not None
            ## add text, spaces, and statement
            self.parse_exprs(buf, text, is_bol)
            is_bol = rspace is not None
            #if mspace == "\n":
            if mspace and mspace.endswith("\n"):
                code = "\n" + (code or "")
            #if rspace == "\n":
            if rspace and rspace.endswith("\n"):
                code = (code or "") + "\n"
            if code:
                code = self.statement_hook(code)
                m = self._match_to_args_declaration(code)
                if m:
                    self._add_args_declaration(buf, m)
                else:
                    self.add_stmt(buf, code)
        rest = input[index:]
        if rest:
            self.parse_exprs(buf, rest)
        self._arrange_indent(buf)

    def statement_hook(self, stmt):
        """expand macros and parse '#@ARGS' in a statement."""
        return stmt.replace("\r\n", "\n")   # Python can't handle "\r\n" in code

    def _match_to_args_declaration(self, stmt):
        if self.args is not None:
            return None
        args_pattern = r'^ *#@ARGS(?:[ \t]+(.*?))?$'
        return re.match(args_pattern, stmt)

    def _add_args_declaration(self, buf, m):
        arr = (m.group(1) or '').split(',')
        args = [];  declares = []
        for s in arr:
            arg = s.strip()
            if not s: continue
            if not re.match('^[a-zA-Z_]\w*$', arg):
                raise ValueError("%r: invalid template argument." % arg)
            args.append(arg)
            declares.append("%s = _context.get('%s'); " % (arg, arg))
        self.args = args
        #nl = stmt[m.end():]
        #if nl: declares.append(nl)
        buf.append(''.join(declares) + "\n")

    EXPR_PATTERN = (r'#\{(.*?)\}|\$\{(.*?)\}|\{=(?:=(.*?)=|(.*?))=\}', re.S)

    def expr_pattern(self):
        pat = self.EXPR_PATTERN
        if isinstance(pat, tuple):
            self.__class__.EXPR_PATTERN = pat = re.compile(*pat)
        return pat

    def get_expr_and_flags(self, match):
        expr1, expr2, expr3, expr4 = match.groups()
        if expr1 is not None: return expr1, (False, True)   # not escape,  call to_str
        if expr2 is not None: return expr2, (True,  True)   # call escape, call to_str
        if expr3 is not None: return expr3, (False, True)   # not escape,  call to_str
        if expr4 is not None: return expr4, (True,  True)   # call escape, call to_str

    def parse_exprs(self, buf, input, is_bol=False):
        buf2 = []
        self._parse_exprs(buf2, input, is_bol)
        if buf2:
            buf.append(''.join(buf2))

    def _parse_exprs(self, buf, input, is_bol=False):
        if not input: return
        self.start_text_part(buf)
        rexp = self.expr_pattern()
        smarttrim = self.smarttrim
        nl = self.newline
        nl_len  = len(nl)
        pos = 0
        for m in rexp.finditer(input):
            start = m.start()
            text  = input[pos:start]
            pos   = m.end()
            expr, flags = self.get_expr_and_flags(m)
            #
            if text:
                self.add_text(buf, text)
            self.add_expr(buf, expr, *flags)
            #
            if smarttrim:
                flag_bol = text.endswith(nl) or not text and (start > 0  or is_bol)
                if flag_bol and not flags[0] and input[pos:pos+nl_len] == nl:
                    pos += nl_len
                    buf.append("\n")
        if smarttrim:
            if buf and buf[-1] == "\n":
                buf.pop()
        rest = input[pos:]
        if rest:
            self.add_text(buf, rest, True)
        self.stop_text_part(buf)
        if input[-1] == '\n':
            buf.append("\n")

    def start_text_part(self, buf):
        self._add_localvars_assignments_to_text(buf)
        #buf.append("_buf.extend((")
        buf.append("_extend((")

    def _add_localvars_assignments_to_text(self, buf):
        if not self._localvars_assignments_added:
            self._localvars_assignments_added = True
            buf.append(self._localvars_assignments())

    def stop_text_part(self, buf):
        buf.append("));")

    def _quote_text(self, text):
        return re.sub(r"(['\\\\])", r"\\\1", text)

    def add_text(self, buf, text, encode_newline=False):
        if not text: return
        use_unicode = self.encoding and python2
        buf.append(use_unicode and "u'''" or "'''")
        text = self._quote_text(text)
        if   not encode_newline:    buf.extend((text,       "''', "))
        elif text.endswith("\r\n"): buf.extend((text[0:-2], "\\r\\n''', "))
        elif text.endswith("\n"):   buf.extend((text[0:-1], "\\n''', "))
        else:                       buf.extend((text,       "''', "))

    _add_text = add_text

    def add_expr(self, buf, code, *flags):
        if not code or code.isspace(): return
        flag_escape, flag_tostr = flags
        if not self.tostrfunc:  flag_tostr  = False
        if not self.escapefunc: flag_escape = False
        if flag_tostr and flag_escape: s1, s2 = "_escape(_to_str(", ")), "
        elif flag_tostr:               s1, s2 = "_to_str(", "), "
        elif flag_escape:              s1, s2 = "_escape(", "), "
        else:                          s1, s2 = "(", "), "
        buf.extend((s1, code, s2, ))

    def add_stmt(self, buf, code):
        if not code: return
        lines = code.splitlines(True)   # keep "\n"
        if lines[-1][-1] != "\n":
            lines[-1] = lines[-1] + "\n"
        buf.extend(lines)
        self._add_localvars_assignments_to_stmts(buf)

    def _add_localvars_assignments_to_stmts(self, buf):
        if self._localvars_assignments_added:
            return
        for index, stmt in enumerate(buf):
            if not re.match(r'^[ \t]*(?:\#|_buf ?= ?\[\]|from __future__)', stmt):
                break
        else:
            return
        self._localvars_assignments_added = True
        if re.match(r'^[ \t]*(if|for|while|def|with|class)\b', stmt):
            buf.insert(index, self._localvars_assignments() + "\n")
        else:
            buf[index] = self._localvars_assignments() + buf[index]


    _START_WORDS = dict.fromkeys(('for', 'if', 'while', 'def', 'try:', 'with', 'class'), True)
    _END_WORDS   = dict.fromkeys(('#end', '#endfor', '#endif', '#endwhile', '#enddef', '#endtry', '#endwith', '#endclass'), True)
    _CONT_WORDS  = dict.fromkeys(('elif', 'else:', 'except', 'except:', 'finally:'), True)
    _WORD_REXP   = re.compile(r'\S+')

    depth = -1

    ##
    ## ex.
    ##   input = r"""
    ##   if items:
    ##   _buf.extend(('<ul>\n', ))
    ##   i = 0
    ##   for item in items:
    ##   i += 1
    ##   _buf.extend(('<li>', to_str(item), '</li>\n', ))
    ##   #endfor
    ##   _buf.extend(('</ul>\n', ))
    ##   #endif
    ##   """[1:]
    ##   lines = input.splitlines(True)
    ##   block = self.parse_lines(lines)
    ##      #=>  [ "if items:\n",
    ##             [ "_buf.extend(('<ul>\n', ))\n",
    ##               "i = 0\n",
    ##               "for item in items:\n",
    ##               [ "i += 1\n",
    ##                 "_buf.extend(('<li>', to_str(item), '</li>\n', ))\n",
    ##               ],
    ##               "#endfor\n",
    ##               "_buf.extend(('</ul>\n', ))\n",
    ##             ],
    ##             "#endif\n",
    ##           ]
    def parse_lines(self, lines):
        block = []
        try:
            self._parse_lines(lines.__iter__(), False, block, 0)
        except StopIteration:
            if self.depth > 0:
                fname, linenum, colnum, linetext = self.filename, len(lines), None, None
                raise TemplateSyntaxError("unexpected EOF.", (fname, linenum, colnum, linetext))
        else:
            pass
        return block

    def _parse_lines(self, lines_iter, end_block, block, linenum):
        if block is None: block = []
        _START_WORDS = self._START_WORDS
        _END_WORDS   = self._END_WORDS
        _CONT_WORDS  = self._CONT_WORDS
        _WORD_REXP   = self._WORD_REXP
        get_line = lines_iter.next
        while True:
            line = get_line()
            linenum += line.count("\n")
            m = _WORD_REXP.search(line)
            if not m:
                block.append(line)
                continue
            word = m.group(0)
            if word in _END_WORDS:
                if word != end_block and word != '#end':
                    if end_block is False:
                        msg = "'%s' found but corresponding statement is missing." % (word, )
                    else:
                        msg = "'%s' expected but got '%s'." % (end_block, word)
                    colnum = m.start() + 1
                    raise TemplateSyntaxError(msg, (self.filename, linenum, colnum, line))
                return block, line, None, linenum
            elif line.endswith(':\n') or line.endswith(':\r\n'):
                if word in _CONT_WORDS:
                    return block, line, word, linenum
                elif word in _START_WORDS:
                    block.append(line)
                    self.depth += 1
                    cont_word = None
                    try:
                        child_block, line, cont_word, linenum = \
                            self._parse_lines(lines_iter, '#end'+word, [], linenum)
                        block.extend((child_block, line, ))
                        while cont_word:   # 'elif' or 'else:'
                            child_block, line, cont_word, linenum = \
                                self._parse_lines(lines_iter, '#end'+word, [], linenum)
                            block.extend((child_block, line, ))
                    except StopIteration:
                        msg = "'%s' is not closed." % (cont_word or word)
                        colnum = m.start() + 1
                        raise TemplateSyntaxError(msg, (self.filename, linenum, colnum, line))
                    self.depth -= 1
                else:
                    block.append(line)
            else:
                block.append(line)
        assert "unreachable"

    def _join_block(self, block, buf, depth):
        indent = ' ' * (self.indent * depth)
        for line in block:
            if isinstance(line, list):
                self._join_block(line, buf, depth+1)
            elif line.isspace():
                buf.append(line)
            else:
                buf.append(indent + line.lstrip())

    def _arrange_indent(self, buf):
        """arrange indentation of statements in buf"""
        block = self.parse_lines(buf)
        buf[:] = []
        self._join_block(block, buf, 0)


    def render(self, context=None, globals=None, _buf=None):
        """Evaluate python code with context dictionary.
           If _buf is None then return the result of evaluation as str,
           else return None.

           context:dict (=None)
             Context object to evaluate. If None then new dict is created.
           globals:dict (=None)
             Global object. If None then globals() is used.
           _buf:list (=None)
             If None then new list is created.
        """
        if context is None:
            locals = context = {}
        elif self.args is None:
            locals = context.copy()
        else:
            locals = {}
            if '_engine' in context:
                context.get('_engine').hook_context(locals)
        locals['_context'] = context
        if globals is None:
            globals = sys._getframe(1).f_globals
        bufarg = _buf
        if _buf is None:
            _buf = []
        locals['_buf'] = _buf
        if not self.bytecode:
            self.compile()
        if self.trace:
            _buf.append("<!-- ***** begin: %s ***** -->\n" % self.filename)
            exec(self.bytecode, globals, locals)
            _buf.append("<!-- ***** end: %s ***** -->\n" % self.filename)
        else:
            exec(self.bytecode, globals, locals)
        if bufarg is not None:
            return bufarg
        elif not logger:
            return ''.join(_buf)
        else:
            try:
                return ''.join(_buf)
            except UnicodeDecodeError, ex:
                logger.error("[tenjin.Template] " + str(ex))
                logger.error("[tenjin.Template] (_buf=%r)" % (_buf, ))
                raise

    def compile(self):
        """compile self.script into self.bytecode"""
        self.bytecode = compile(self.script, self.filename or '(tenjin)', 'exec')


##
## preprocessor class
##

class Preprocessor(Template):
    """Template class for preprocessing."""

    STMT_PATTERN = (r'<\?PY( |\t|\r?\n)(.*?) ?\?>([ \t]*\r?\n)?', re.S)

    EXPR_PATTERN = (r'#\{\{(.*?)\}\}|\$\{\{(.*?)\}\}|\{#=(?:=(.*?)=|(.*?))=#\}', re.S)

    def add_expr(self, buf, code, *flags):
        if not code or code.isspace():
            return
        code = "_decode_params(%s)" % code
        Template.add_expr(self, buf, code, *flags)


##
## cache storages
##

class CacheStorage(object):
    """[abstract] Template object cache class (in memory and/or file)"""

    def __init__(self):
        self.items = {}    # key: full path, value: template object

    def get(self, cachepath, create_template):
        """get template object. if not found, load attributes from cache file and restore  template object."""
        template = self.items.get(cachepath)
        if not template:
            dct = self._load(cachepath)
            if dct:
                template = create_template()
                for k in dct:
                    setattr(template, k, dct[k])
                self.items[cachepath] = template
        return template

    def set(self, cachepath, template):
        """set template object and save template attributes into cache file."""
        self.items[cachepath] = template
        dct = self._save_data_of(template)
        return self._store(cachepath, dct)

    def _save_data_of(self, template):
        return { 'args'  : template.args,   'bytecode' : template.bytecode,
                 'script': template.script, 'timestamp': template.timestamp }

    def unset(self, cachepath):
        """remove template object from dict and cache file."""
        self.items.pop(cachepath, None)
        return self._delete(cachepath)

    def clear(self):
        """remove all template objects and attributes from dict and cache file."""
        d, self.items = self.items, {}
        for k in d.iterkeys():
            self._delete(k)
        d.clear()

    def _load(self, cachepath):
        """(abstract) load dict object which represents template object attributes from cache file."""
        raise NotImplementedError.new("%s#_load(): not implemented yet." % self.__class__.__name__)

    def _store(self, cachepath, template):
        """(abstract) load dict object which represents template object attributes from cache file."""
        raise NotImplementedError.new("%s#_store(): not implemented yet." % self.__class__.__name__)

    def _delete(self, cachepath):
        """(abstract) remove template object from cache file."""
        raise NotImplementedError.new("%s#_delete(): not implemented yet." % self.__class__.__name__)


class MemoryCacheStorage(CacheStorage):

    def _load(self, cachepath):
        return None

    def _store(self, cachepath, template):
        pass

    def _delete(self, cachepath):
        pass


class FileCacheStorage(CacheStorage):

    def _load(self, cachepath):
        if not _isfile(cachepath): return None
        if logger: logger.info("[tenjin.%s] load cache (file=%r)" % (self.__class__.__name__, cachepath))
        data = _read_binary_file(cachepath)
        return self._restore(data)

    def _store(self, cachepath, dct):
        if logger: logger.info("[tenjin.%s] store cache (file=%r)" % (self.__class__.__name__, cachepath))
        data = self._dump(dct)
        _write_binary_file(cachepath, data)

    def _restore(self, data):
        raise NotImplementedError("%s._restore(): not implemented yet." % self.__class__.__name__)

    def _dump(self, dct):
        raise NotImplementedError("%s._dump(): not implemented yet." % self.__class__.__name__)

    def _delete(self, cachepath):
        _ignore_not_found_error(lambda: os.unlink(cachepath))


class MarshalCacheStorage(FileCacheStorage):

    def _restore(self, data):
        return marshal.loads(data)

    def _dump(self, dct):
        return marshal.dumps(dct)


class PickleCacheStorage(FileCacheStorage):

    def __init__(self, *args, **kwargs):
        global pickle
        if pickle is None:
            import cPickle as pickle
        FileCacheStorage.__init__(self, *args, **kwargs)

    def _restore(self, data):
        return pickle.loads(data)

    def _dump(self, dct):
        dct.pop('bytecode', None)
        return pickle.dumps(dct)


class TextCacheStorage(FileCacheStorage):

    def _restore(self, data):
        header, script = data.split("\n\n", 1)
        timestamp = encoding = args = None
        for line in header.split("\n"):
            key, val = line.split(": ", 1)
            if   key == 'timestamp':  timestamp = float(val)
            elif key == 'encoding':   encoding  = val
            elif key == 'args':       args      = val.split(', ')
        if encoding: script = script.decode(encoding)   ## binary(=str) to unicode
        return {'args': args, 'script': script, 'timestamp': timestamp}

    def _dump(self, dct):
        s = dct['script']
        if dct.get('encoding') and isinstance(s, unicode):
            s = s.encode(dct['encoding'])           ## unicode to binary(=str)
        sb = []
        sb.append("timestamp: %s\n" % dct['timestamp'])
        if dct.get('encoding'):
            sb.append("encoding: %s\n" % dct['encoding'])
        if dct.get('args') is not None:
            sb.append("args: %s\n" % ', '.join(dct['args']))
        sb.append("\n")
        sb.append(s)
        s = ''.join(sb)
        if python3:
            if isinstance(s, str):
                s = s.encode(dct.get('encoding') or 'utf-8')   ## unicode(=str) to binary
        return s

    def _save_data_of(self, template):
        dct = FileCacheStorage._save_data_of(self, template)
        dct['encoding'] = template.encoding
        return dct



##
## abstract class for data cache
##
class KeyValueStore(object):

    def get(self, key, *options):
        raise NotImplementedError("%s.get(): not implemented yet." % self.__class__.__name__)

    def set(self, key, value, *options):
        raise NotImplementedError("%s.set(): not implemented yet." % self.__class__.__name__)

    def delete(self, key, *options):
        raise NotImplementedError("%s.del(): not implemented yet." % self.__class__.__name__)

    def has(self, key, *options):
        raise NotImplementedError("%s.has(): not implemented yet." % self.__class__.__name__)


##
## memory base data cache
##
class MemoryBaseStore(KeyValueStore):

    def __init__(self):
        self.values = {}

    def get(self, key, original_timestamp=None):
        tupl = self.values.get(key)
        if not tupl:
            return None
        value, created_at, expires_at = tupl
        if original_timestamp is not None and created_at < original_timestamp:
            self.delete(key)
            return None
        if expires_at < _time():
            self.delete(key)
            return None
        return value

    def set(self, key, value, lifetime=0):
        created_at = _time()
        expires_at = lifetime and created_at + lifetime or 0
        self.values[key] = (value, created_at, expires_at)
        return True

    def delete(self, key):
        try:
            del self.values[key]
            return True
        except KeyError:
            return False

    def has(self, key):
        pair = self.values.get(key)
        if not pair:
            return False
        value, created_at, expires_at = pair
        if expires_at and expires_at < _time():
            self.delete(key)
            return False
        return True


##
## file base data cache
##
class FileBaseStore(KeyValueStore):

    lifetime = 604800   # = 60*60*24*7

    def __init__(self, root_path, encoding=None):
        if not os.path.isdir(root_path):
            raise ValueError("%r: directory not found." % (root_path, ))
        self.root_path = root_path
        if encoding is None and python3:
            encoding = 'utf-8'
        self.encoding = encoding

    _pat = re.compile(r'[^-.\/\w]')

    def filepath(self, key, _pat1=_pat):
        return os.path.join(self.root_path, _pat1.sub('_', key))

    def get(self, key, original_timestamp=None):
        fpath = self.filepath(key)
        #if not _isfile(fpath): return None
        stat = _ignore_not_found_error(lambda: os.stat(fpath), None)
        if stat is None:
            return None
        created_at = stat.st_ctime
        expires_at = stat.st_mtime
        if original_timestamp is not None and created_at < original_timestamp:
            self.delete(key)
            return None
        if expires_at < _time():
            self.delete(key)
            return None
        if self.encoding:
            f = lambda: _read_text_file(fpath, self.encoding)
        else:
            f = lambda: _read_binary_file(fpath)
        return _ignore_not_found_error(f, None)

    def set(self, key, value, lifetime=0):
        fpath = self.filepath(key)
        dirname = os.path.dirname(fpath)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        now = _time()
        if isinstance(value, _unicode):
            value = value.encode(self.encoding or 'utf-8')
        _write_binary_file(fpath, value)
        expires_at = now + (lifetime or self.lifetime)  # timestamp
        os.utime(fpath, (expires_at, expires_at))
        return True

    def delete(self, key):
        fpath = self.filepath(key)
        ret = _ignore_not_found_error(lambda: os.unlink(fpath), False)
        return ret != False

    def has(self, key):
        fpath = self.filepath(key)
        if not _isfile(fpath):
            return False
        if _getmtime(fpath) < _time():
            self.delete(key)
            return False
        return True



##
## html fragment cache helper class
##
class FragmentCacheHelper(object):
    """html fragment cache helper class."""

    lifetime = 60   # 1 minute
    prefix   = None

    def __init__(self, store, lifetime=None, prefix=None):
        self.store = store
        if lifetime is not None:  self.lifetime = lifetime
        if prefix   is not None:  self.prefix   = prefix

    def not_cached(self, cache_key, lifetime=None):
        """(obsolete. use cache_as() instead of this.)
           html fragment cache helper. see document of FragmentCacheHelper class."""
        context = sys._getframe(1).f_locals['_context']
        context['_cache_key'] = cache_key
        key = self.prefix and self.prefix + cache_key or cache_key
        value = self.store.get(key)
        if value:    ## cached
            if logger: logger.debug('[tenjin.not_cached] %r: cached.' % (cache_key, ))
            context[key] = value
            return False
        else:        ## not cached
            if logger: logger.debug('[tenjin.not_cached]: %r: not cached.' % (cache_key, ))
            if key in context: del context[key]
            if lifetime is None:  lifetime = self.lifetime
            context['_cache_lifetime'] = lifetime
            helpers.start_capture(cache_key, _depth=2)
            return True

    def echo_cached(self):
        """(obsolete. use cache_as() instead of this.)
           html fragment cache helper. see document of FragmentCacheHelper class."""
        f_locals = sys._getframe(1).f_locals
        context = f_locals['_context']
        cache_key = context.pop('_cache_key')
        key = self.prefix and self.prefix + cache_key or cache_key
        if key in context:    ## cached
            value = context.pop(key)
        else:                 ## not cached
            value = helpers.stop_capture(False, _depth=2)
            lifetime = context.pop('_cache_lifetime')
            self.store.set(key, value, lifetime)
        f_locals['_buf'].append(value)

    def functions(self):
        """(obsolete. use cache_as() instead of this.)"""
        return (self.not_cached, self.echo_cached)

    def cache_as(self, cache_key, lifetime=None):
        key = self.prefix and self.prefix + cache_key or cache_key
        _buf = sys._getframe(1).f_locals['_buf']
        value = self.store.get(key)
        if value:
            if logger: logger.debug('[tenjin.cache_as] %r: cache found.' % (cache_key, ))
            _buf.append(value)
        else:
            if logger: logger.debug('[tenjin.cache_as] %r: expired or not cached yet.' % (cache_key, ))
            _buf_len = len(_buf)
            yield None
            value = ''.join(_buf[_buf_len:])
            self.store.set(key, value, lifetime)

## you can change default store by 'tenjin.helpers.fragment_cache.store = ...'
helpers.fragment_cache = FragmentCacheHelper(MemoryBaseStore())
helpers.not_cached  = helpers.fragment_cache.not_cached
helpers.echo_cached = helpers.fragment_cache.echo_cached
helpers.cache_as    = helpers.fragment_cache.cache_as
helpers.__all__.extend(('not_cached', 'echo_cached', 'cache_as'))



##
## helper class to find and read template
##
class Loader(object):

    def exists(self, filepath):
        raise NotImplementedError("%s.exists(): not implemented yet." % self.__class__.__name__)

    def find(self, filename, dirs=None):
        #: if dirs provided then search template file from it.
        if dirs:
            for dirname in dirs:
                filepath = os.path.join(dirname, filename)
                if self.exists(filepath):
                    return filepath
        #: if dirs not provided then just return filename if file exists.
        else:
            if self.exists(filename):
                return filename
        #: if file not found then return None.
        return None

    def abspath(self, filename):
        raise NotImplementedError("%s.abspath(): not implemented yet." % self.__class__.__name__)

    def timestamp(self, filepath):
        raise NotImplementedError("%s.timestamp(): not implemented yet." % self.__class__.__name__)

    def load(self, filepath):
        raise NotImplementedError("%s.timestamp(): not implemented yet." % self.__class__.__name__)



##
## helper class to find and read files
##
class FileSystemLoader(Loader):

    def exists(self, filepath):
        #: return True if filepath exists as a file.
        return os.path.isfile(filepath)

    def abspath(self, filepath):
        #: return full-path of filepath
        return os.path.abspath(filepath)

    def timestamp(self, filepath):
        #: return mtime of file
        return _getmtime(filepath)

    def load(self, filepath):
        #: if file exists, return file content and mtime
        def f():
            mtime = _getmtime(filepath)
            input = _read_template_file(filepath)
            mtime2 = _getmtime(filepath)
            if mtime != mtime2:
                mtime = mtime2
                input = _read_template_file(filepath)
                mtime2 = _getmtime(filepath)
                if mtime != mtime2:
                    if logger:
                        logger.warn("[tenjin] %s.load(): timestamp is changed while reading file." % self.__class__.__name__)
            return input, mtime
        #: if file not exist, return None
        return _ignore_not_found_error(f)


##
##
##
class TemplateNotFoundError(Exception):
    pass



##
## template engine class
##

class Engine(object):
    """Template Engine class.
       See User's Guide and examples for details.
       http://www.kuwata-lab.com/tenjin/pytenjin-users-guide.html
       http://www.kuwata-lab.com/tenjin/pytenjin-examples.html
    """

    ## default value of attributes
    prefix     = ''
    postfix    = ''
    layout     = None
    templateclass = Template
    path       = None
    cache      = MarshalCacheStorage()  # save converted Python code into file by marshal-format
    lang       = None
    loader     = FileSystemLoader()
    preprocess = False
    preprocessorclass = Preprocessor
    timestamp_interval = 1  # seconds

    def __init__(self, prefix=None, postfix=None, layout=None, path=None, cache=True, preprocess=None, templateclass=None, preprocessorclass=None, lang=None, loader=None, **kwargs):
        """Initializer of Engine class.

           prefix:str (='')
             Prefix string used to convert template short name to template filename.
           postfix:str (='')
             Postfix string used to convert template short name to template filename.
           layout:str (=None)
             Default layout template name.
           path:list of str(=None)
             List of directory names which contain template files.
           cache:bool or CacheStorage instance (=True)
             Cache storage object to store converted python code.
             If True, default cache storage (=Engine.cache) is used (if it is None
             then create MarshalCacheStorage object for each engine object).
             If False, no cache storage is used nor no cache files are created.
           preprocess:bool(=False)
             Activate preprocessing or not.
           templateclass:class (=Template)
             Template class which engine creates automatically.
           lang:str (=None)
             Language name such as 'en', 'fr', 'ja', and so on. If you specify
             this, cache file path will be 'inex.html.en.cache' for example.
           kwargs:dict
             Options for Template class constructor.
             See document of Template.__init__() for details.
        """
        if prefix:  self.prefix  = prefix
        if postfix: self.postfix = postfix
        if layout:  self.layout  = layout
        if templateclass: self.templateclass = templateclass
        if preprocessorclass: self.preprocessorclass = preprocessorclass
        if path is not None:  self.path = path
        if lang is not None:  self.lang = lang
        if loader is not None: self.loader = loader
        if preprocess is not None: self.preprocess = preprocess
        self.kwargs = kwargs
        self.encoding = kwargs.get('encoding')
        self._filepaths = {}   # template_name => relative path and absolute path
        self._added_templates = {}   # templates added by add_template()
        #self.cache = cache
        self._set_cache_storage(cache)

    def _set_cache_storage(self, cache):
        if cache is True:
            if not self.cache:
                self.cache = MarshalCacheStorage()
        elif cache is None:
            pass
        elif cache is False:
            self.cache = None
        elif isinstance(cache, CacheStorage):
            self.cache = cache
        else:
            raise ValueError("%r: invalid cache object." % (cache, ))

    def cachename(self, filepath):
        #: if lang is provided then add it to cache filename.
        if self.lang:
            return '%s.%s.cache' % (filepath, self.lang)
        #: return cache file name.
        else:
            return filepath + '.cache'

    def to_filename(self, template_name):
        """Convert template short name into filename.
           ex.
             >>> engine = tenjin.Engine(prefix='user_', postfix='.pyhtml')
             >>> engine.to_filename(':list')
             'user_list.pyhtml'
             >>> engine.to_filename('list')
             'list'
        """
        #: if template_name starts with ':', add prefix and postfix to it.
        if template_name[0] == ':' :
            return self.prefix + template_name[1:] + self.postfix
        #: if template_name doesn't start with ':', just return it.
        return template_name

    def _create_template(self, input=None, filepath=None, _context=None, _globals=None):
        #: if input is not specified then just create empty template object.
        template = self.templateclass(None, **self.kwargs)
        #: if input is specified then create template object and return it.
        if input:
            template.convert(input, filepath)
        return template

    def _preprocess(self, input, filepath, _context, _globals):
        #if _context is None: _context = {}
        #if _globals is None: _globals = sys._getframe(3).f_globals
        #: preprocess template and return result
        if '_engine' not in _context:
            self.hook_context(_context)
        preprocessor = self.preprocessorclass(filepath, input=input)
        return preprocessor.render(_context, globals=_globals)

    def add_template(self, template):
        self._added_templates[template.filename] = template

    def _get_template_from_cache(self, cachepath, filepath):
        #: if template not found in cache, return None
        template = self.cache.get(cachepath, self.templateclass)
        if not template:
            return None
        assert template.timestamp is not None
        #: if checked within a sec, skip timestamp check.
        now = _time()
        last_checked = getattr(template, '_last_checked_at', None)
        if last_checked and now < last_checked + self.timestamp_interval:
            #if logger: logger.trace('[tenjin.%s] timestamp check skipped (%f < %f + %f)' % \
            #                        (self.__class__.__name__, now, template._last_checked_at, self.timestamp_interval))
            return template
        #: if timestamp of template objectis same as file, return it.
        if template.timestamp == self.loader.timestamp(filepath):
            template._last_checked_at = now
            return template
        #: if timestamp of template object is different from file, clear it
        #cache._delete(cachepath)
        if logger: logger.info("[tenjin.%s] cache expired (filepath=%r)" % \
                                   (self.__class__.__name__, filepath))
        return None

    def get_template(self, template_name, _context=None, _globals=None):
        """Return template object.
           If template object has not registered, template engine creates
           and registers template object automatically.
        """
        #: accept template_name such as ':index'.
        filename = self.to_filename(template_name)
        #: if template object is added by add_template(), return it.
        if filename in self._added_templates:
            return self._added_templates[filename]
        #: get filepath and fullpath of template
        pair = self._filepaths.get(filename)
        if pair:
            filepath, fullpath = pair
        else:
            #: if template file is not found then raise TemplateNotFoundError.
            filepath = self.loader.find(filename, self.path)
            if not filepath:
                raise TemplateNotFoundError('%s: filename not found (path=%r).' % (filename, self.path))
            #
            fullpath = self.loader.abspath(filepath)
            self._filepaths[filename] = (filepath, fullpath)
        #: use full path as base of cache file path
        cachepath = self.cachename(fullpath)
        #: get template object from cache
        cache = self.cache
        template = cache and self._get_template_from_cache(cachepath, filepath) or None
        #: if template object is not found in cache or is expired...
        if not template:
            ret = self.loader.load(filepath)
            if not ret:
                raise TemplateNotFoundError("%r: template not found." % filepath)
            input, timestamp = ret
            if self.preprocess:   ## required for preprocessing
                if _context is None: _context = {}
                if _globals is None: _globals = sys._getframe(1).f_globals
                input = self._preprocess(input, filepath, _context, _globals)
            #: create template object.
            template = self._create_template(input, filepath, _context, _globals)
            #: set timestamp and filename of template object.
            template.timestamp = timestamp
            template._last_checked_at = _time()
            #: save template object into cache.
            if cache:
                if not template.bytecode: template.compile()
                cache.set(cachepath, template)
        #else:
        #    template.compile()
        #:
        template.filename = filepath
        return template

    def include(self, template_name, append_to_buf=True, **kwargs):
        """Evaluate template using current local variables as context.

           template_name:str
             Filename (ex. 'user_list.pyhtml') or short name (ex. ':list') of template.
           append_to_buf:boolean (=True)
             If True then append output into _buf and return None,
             else return stirng output.

           ex.
             <?py include('file.pyhtml') ?>
             #{include('file.pyhtml', False)}
             <?py val = include('file.pyhtml', False) ?>
        """
        #: get local and global vars of caller.
        frame = sys._getframe(1)
        locals  = frame.f_locals
        globals = frame.f_globals
        #: get _context from caller's local vars.
        assert '_context' in locals
        context = locals['_context']
        #: if kwargs specified then add them into context.
        if kwargs:
            context.update(kwargs)
        #: get template object with context data and global vars.
        ## (context and globals are passed to get_template() only for preprocessing.)
        template = self.get_template(template_name, context, globals)
        #: if append_to_buf is true then add output to _buf.
        #: if append_to_buf is false then don't add output to _buf.
        if append_to_buf:  _buf = locals['_buf']
        else:              _buf = None
        #: render template and return output.
        s = template.render(context, globals, _buf=_buf)
        #: kwargs are removed from context data.
        if kwargs:
            for k in kwargs:
                del context[k]
        return s

    def render(self, template_name, context=None, globals=None, layout=True):
        """Evaluate template with layout file and return result of evaluation.

           template_name:str
             Filename (ex. 'user_list.pyhtml') or short name (ex. ':list') of template.
           context:dict (=None)
             Context object to evaluate. If None then new dict is used.
           globals:dict (=None)
             Global context to evaluate. If None then globals() is used.
           layout:str or Bool(=True)
             If True, the default layout name specified in constructor is used.
             If False, no layout template is used.
             If str, it is regarded as layout template name.

           If temlate object related with the 'template_name' argument is not exist,
           engine generates a template object and register it automatically.
        """
        if context is None:
            context = {}
        if globals is None:
            globals = sys._getframe(1).f_globals
        self.hook_context(context)
        while True:
            ## context and globals are passed to get_template() only for preprocessing
            template = self.get_template(template_name, context, globals)
            content  = template.render(context, globals)
            layout   = context.pop('_layout', layout)
            if layout is True or layout is None:
                layout = self.layout
            if not layout:
                break
            template_name = layout
            layout = False
            context['_content'] = content
        context.pop('_content', None)
        return content

    def hook_context(self, context):
        #: add engine itself into context data.
        context['_engine'] = self
        #context['render'] = self.render
        #: add include() method into context data.
        context['include'] = self.include


##
## safe template and engine
##

class SafeTemplate(Template):
    """Uses 'to_escaped()' instead of 'escape()'.
       '#{...}' is not allowed with this class. Use '[==...==]' instead.
    """

    tostrfunc  = 'to_str'
    escapefunc = 'to_escaped'

    def get_expr_and_flags(self, match):
        return _get_expr_and_flags(match, "#{%s}: '#{}' is not allowed with SafeTemplate.")


class SafePreprocessor(Preprocessor):

    tostrfunc  = 'to_str'
    escapefunc = 'to_escaped'

    def get_expr_and_flags(self, match):
        return _get_expr_and_flags(match, "#{{%s}}: '#{{}}' is not allowed with SafePreprocessor.")


def _get_expr_and_flags(match, errmsg):
    expr1, expr2, expr3, expr4 = match.groups()
    if expr1 is not None:
        raise TemplateSyntaxError(errmsg % match.group(1))
    if expr2 is not None: return expr2, (True, False)   # #{...}    : call escape, not to_str
    if expr3 is not None: return expr3, (False, True)   # [==...==] : not escape, call to_str
    if expr4 is not None: return expr4, (True, False)   # [=...=]   : call escape, not to_str


class SafeEngine(Engine):

    templateclass     = SafeTemplate
    preprocessorclass = SafePreprocessor


del _dummy

########NEW FILE########
