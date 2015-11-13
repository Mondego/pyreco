__FILENAME__ = code
# -- coding: utf8 --
import sys
if sys.getdefaultencoding() != 'utf-8':
    reload(sys)
    sys.setdefaultencoding('utf-8')
import web
from config.config import *
from config.urls import *
from libraries import helper
from libraries import widget
from models.site_model import *
from models.user_model import *
from models.notify_model import *

#web.template.Template.globals['render'] = render
#web.template.Template.globals['admin_render'] = admin_render
#web.template.Template.globals['site_title'] = site_title
web.template.Template.globals['helper'] = helper
web.template.Template.globals['widget'] = widget
web.template.Template.globals['site_options'] = site_model().get_options()

app = web.application(urls, globals())

if web.config.get('_session') is None:
    session = web.session.Session(app, web.session.DiskStore('sessions'), initializer={'user_id': None})
    web.config._session = session
else:
    session = web.config._session

#user_model.auth_cookie()
app.add_processor(user_model().auth_cookie)
app.add_processor(notify_model().check)

# 如果这里不 不将 session 赋值给模板全局变量， 模板中将不能得到此变量
web.template.Template.globals['session'] = session
#web.template.Template.globals['site_url'] = 'http://127.0.0.1:8080'
if __name__ == "__main__":
    app.run()
########NEW FILE########
__FILENAME__ = urls
# -- coding: utf8 --
pre_fix = 'controllers.'
urls = (
    # 首页
    '/index', pre_fix + 'index.index',
    # 关于
    '/about', pre_fix + 'index.about',
    # 最近的主题
    '/recent', pre_fix + 'index.recent',
    # 浏览主题
    '/post/(\d+)', pre_fix + 'post.view',
    # 创建主题
    '/create/([a-z\-]*)', pre_fix + 'post.create',
    # 感谢主题
    '/post/thanks', pre_fix + 'post.thanks',
    # 节点主题列表
    '/node/([a-z\-]*)', pre_fix + 'node.index',
    # 评论主题
    '/comment/(\d+)', pre_fix + 'comment.create',
    # 感谢评论
    '/comment/thanks', pre_fix + 'comment.thanks',
    # 注册
    '/signup', pre_fix + 'user.signup',
    # 登录
    '/login', pre_fix + 'user.login',
    # 注销
    '/logout', pre_fix + 'user.logout',
    # 提醒
    '/notifications', pre_fix + 'notifications.index',
    # 提醒检查
    '/notifications/check', pre_fix + 'notifications.check',
    # 删除提醒
    '/notifications/delete/(\w+)', pre_fix + 'notifications.delete',
    # 设置
    '/settings', pre_fix + 'user.settings',
    # 上传头像
    '/settings/avatar', pre_fix + 'user.avatar',
    # 设置密码
    '/settings/password', pre_fix + 'user.password',
    # 用户中心
    '/profile/(\w+)', pre_fix + 'user.profile',
    # 财富中心
    '/balance', pre_fix + 'user.balance',
    # 关注用户
    '/follow/(\w+)', pre_fix + 'user.follow',
    # 取消关注
    '/unfollow/(\w+)', pre_fix + 'user.unfollow',
    # 来自关注人的帖子
    '/my/following', pre_fix +'user.following',
    # 收藏帖子
    '/post/fav/(\d+)', pre_fix + 'post.fav',
    # 取消收藏帖子
    '/post/unfav/(\d+)', pre_fix + 'post.unfav',
    # 收藏的主题
    '/my/posts', pre_fix + 'user.post_favs',
    # 用户创建的主题
    '/profile/(\w+)/posts', pre_fix + 'user.posts',
    # 用户创建的回复
    '/profile/(\w+)/comments', pre_fix + 'user.comments',
    # 收藏节点
    '/node/fav/([a-z\-]*)', pre_fix + 'node.fav',
    # 收藏节点的主题
    '/my/nodes', pre_fix + 'user.node_favs',
    # 取消收藏节点
    '/node/unfav/([a-z\-]*)', pre_fix + 'node.unfav',
    # 后台管理
    '/admin', pre_fix + 'admin.index',
    # 站点设置
    '/admin/site', pre_fix + 'admin.site',
    # 分类编辑
    '/admin/cat/([a-z\-]*)', pre_fix + 'admin.cat',
    # 添加分类
    '/admin/create_cat', pre_fix + 'admin.create_cat',
    # 添加节点
    '/admin/create_node/([a-z\-]*)', pre_fix + 'admin.create_node',
    # 编辑节点
    '/admin/node/([a-z\-]*)', pre_fix + 'admin.node',
    # 设置节点图标
    '/admin/node/icon/([a-z\-]*)', pre_fix + 'admin.set_node_icon',
    # 其他
    '/.*', pre_fix + 'index.index'
)
########NEW FILE########
__FILENAME__ = admin
# -- coding: utf8 --
__metaclass__ = type
import web
session = web.config._session
from config.config import *
from models.node_model import *
from models.cat_model import *
from models.post_model import *
from models.user_model import *
from models.comment_model import *
from models.site_model import *
from libraries.crumb import Crumb

class admin:
    def __init__(self):
        if session.user_id != 1:
            raise web.SeeOther('/')
        self.crumb = Crumb()
        self.crumb.append('后台', '/admin')

class index(admin):
    
    def GET(self):
        cat_result = cat_model().get_all()
        cats = []
        for cat in cat_result:
            node_total = node_model().count_table({'category_id':cat.id})
            cats.append({'cat':cat, 'node_total':node_total})
        return admin_render.index('后台', cats, self.crumb.output())

class site(admin):

    def __init__(self):
        super(site, self).__init__()
        self.form = site_model().form
        self.site = site_model().get_options()
        self.form.title.set_value(self.site['title'])
        self.form.description.set_value(self.site['description'])
        self.form.site_url.set_value(self.site['site_url'])
        self.form.cookie_expires.set_value(self.site['cookie_expires'])

    def GET(self):
        self.crumb.append('站点设置')
        return admin_render.site('站点设置', self.crumb.output(), self.form)

    def POST(self):
        if self.form.validates():
            site_model().update({'key':'title'}, {'value':self.form.d.title})
            site_model().update({'key':'description'}, {'value':self.form.d.description})
            site_model().update({'key':'site_url'}, {'value':self.form.d.site_url})
            site_model().update({'key':'cookie_expires'}, {'value':self.form.d.cookie_expires})
            # 不知道这里为什么还要clear一次才能保证crumb的干净
            
            raise web.SeeOther('/admin/site')
        else:
            self.crumb.append('站点设置')
            return admin_render.site('站点设置', self.crumb.output(), self.form)


class cat(admin):

    def __init__(self):
        super(cat, self).__init__()
        self.form = cat_model().modify_form

    def GET(self, cat_name):
        cat = cat_model().get_one({'name':cat_name})
        if cat is None:
            self.crumb.append('分类不存在')
            return admin_render.cat_nf('分类不存在', self.crumb.output())
        else:
            self.crumb.append(cat.display_name)
            nodes = node_model().get_all({'category_id':cat.id})
            self.form.name.set_value(cat.name)
            self.form.display_name.set_value(cat.display_name)
            self.form.description.set_value(cat.description)
            return admin_render.cat_view(cat.display_name, self.crumb.output(), cat, self.form, nodes)

    def POST(self, cat_name):
        cat = cat_model().get_one({'name':cat_name})
        if cat is None:
            self.crumb.append('分类不存在')
            return admin_render.cat_nf('分类不存在', self.crumb.output())
        else:
            if self.form.validates():
                cat_model().update({'name':cat.name}, {'display_name':self.form.d.display_name, 'description':self.form.d.description})
                
                web.SeeOther('/admin/cat/'+cat.name)
            else:
                self.form.name.set_value(cat.name)
                self.form.display_name.set_value(cat.display_name)
                self.form.description.set_value(cat.description)
                
                web.SeeOther('/admin/cat/'+cat.name)

class create_cat(admin):

    def __init__(self):
        super(create_cat, self).__init__()
        self.form = cat_model().create_form

    def GET(self):
        self.crumb.append('添加新分类')
        return admin_render.create_cat('添加新分类', self.crumb.output(), self.form)
    def POST(self):
        if self.form.validates():
            if cat_model().unique_insert({'name':self.form.d.name}):
                # 为了保证不插入空的display_name的分类，故此
                try:
                    cat_model().update({'name':self.form.d.name}, {'display_name':self.form.d.display_name, 'description':self.form.d.description})
                except:
                    cat_model().delete({'name':self.form.d.name})
                
                web.SeeOther('/admin/cat/'+self.form.d.name)
            else:
                return admin_render.create_cat('分类名已存在', self.crumb.output(), self.form)

class node(admin):

    def __init__(self):
        super(node, self).__init__()
        self.form = node_model().modify_form

    def GET(self, node_name):
        node = node_model().get_one({'name':node_name})
        if node is None:
            return admin_render.node_nf('节点不存在', self.crumb.output())
        ##return node
        cat = cat_model().get_one({'id':node.category_id})
        self.form.name.set_value(node.name)
        self.form.display_name.set_value(node.display_name)
        self.form.description.set_value(node.description)
        self.crumb.append(cat.display_name, '/admin/cat/'+cat.name)
        self.crumb.append(node.display_name)
        return admin_render.node_view(node.display_name, self.crumb.output(), node, self.form)

    def POST(self, node_name):
        node = node_model().get_one({'name':node_name})
        if node is None:
            return admin_render.node_nf('节点不存在', self.crumb.output())
        if self.form.validates():
            node_model().update({'name':node.name}, {'display_name':self.form.d.display_name, 'description':self.form.d.description})
            raise web.SeeOther('/admin/node/'+node.name)

class set_node_icon(admin):

    def GET(self, node_name):
        node = node_model().get_one({'name':node_name})
        if node is None:
            return admin_render.node_nf('节点不存在', self.crumb.output())
        cat = cat_model().get_one({'id':node.category_id})
        self.crumb.append(cat.display_name, '/admin/cat/'+cat.name)
        self.crumb.append(node.display_name, '/admin/node/'+node.name)
        self.crumb.append('设置节点图标')
        return admin_render.set_node_icon('设置节点图标', self.crumb.output(), node)

    def POST(self, node_name):
        node = node_model().get_one({'name':node_name})
        if node is None:
            return admin_render.node_nf('节点不存在', self.crumb.output())
        cat = cat_model().get_one({'id':node.category_id})
        self.crumb.append(cat.display_name, '/admin/cat/'+cat.name)
        self.crumb.append(node.display_name, '/admin/node/'+node.name)
        self.crumb.append('设置节点图标')
        import cgi
        import os
        cgi.maxlen = 2 * 1024 * 1024 # 2MB
        try:
            x = web.input(icon={})
        except ValueError:
            return admin_render.set_node_icon('设置节点图标', self.crumb.output(), node, ' <<超过大小限制')
        if 'icon' in x:
            #客户端为windows时注意
            filepath=x.icon.filename.replace('\\','/')
            #获取文件名
            filename=filepath.split('/')[-1]
            #获取后缀
            ext = filename.split('.', 1)[1].lower()
            ext_allow = ('jpg', 'png', 'gif', 'jpeg')
            #判断文件后缀名 
            if ext in ext_allow:
                #要上传的路径
                filedir = 'static/icons/tmp/'
                try:
                    os.makedirs('static/icons/tmp')
                except:
                    pass
                filename = str(node.id) +'.'+ext
                if os.path.exists(filedir+filename):
                    os.remove(filedir+filename)
                fout = open(filedir + filename, 'wb')
                fout.write(x.icon.file.read())
                fout.close()
                node_model().set_icon(filename, node.id)
                error = False
            else:
                message = ' <<请上传指定格式文件'
                error = True
        if error:
            return admin_render.set_node_icon('设置节点图标', self.crumb.output(), node, message)
        else:
            
            raise web.SeeOther('/admin/node/icon/'+node.name)

class create_node(admin):
    
    def __init__(self):
        super(create_node, self).__init__()
        self.form = node_model().create_form

    def GET(self, cat_name):
        cat = cat_model().get_one({'name':cat_name})
        if cat is None:
            self.crumb.append('分类不存在')
            return admin_render.cat_nf('分类不存在', self.crumb.output())
        self.crumb.append(cat.name, '/admin/cat/'+cat.name)
        self.crumb.append('添加新节点')
        return admin_render.create_node('添加新节点', self.crumb.output(), cat, self.form)

    def POST(self, cat_name):
        cat = cat_model().get_one({'name':cat_name})
        if cat is None:
            self.crumb.append('分类不存在')
            return admin_render.cat_nf('分类不存在', self.crumb.output())
        if self.form.validates():
            if node_model().unique_insert({'name':self.form.d.name}):
                # 为了保证不插入空的display_name的节点，故此
                try:
                    node_model().update({'name':self.form.d.name}, {'category_id':cat.id, 'display_name':self.form.d.display_name, 'description':self.form.d.description})                
                except:
                    node_model().delete({'name':self.form.d.name})
                
                web.SeeOther('/admin/node/'+self.form.d.name)
            else:
                return admin_render.create_cat('节点名已存在', self.crumb.output(), self.form)
        else:
            return admin_render.create_node('添加新节点', self.crumb.output(), cat, self.form)

########NEW FILE########
__FILENAME__ = comment
# -- coding: utf8 --
import web
session = web.config._session
import time
from config.config import render
from models.comment_model import *
from models.comment_thanks_model import *
from models.post_model import *
from models.money_model import *
from models.money_type_model import *
from models.user_model import *
from models.notify_model import *
from models.notify_type_model import *
from libraries.helper import *

class create:
    
    def __init__(self):
        self.form = comment_model().form
    
    def GET(self, post_id):
        raise web.SeeOther('/post/' + post_id)
    
    def POST(self, post_id):
        if session.user_id is None:
            raise web.SeeOther('/login')
        post = post_model().get_one({'id':post_id})
        if post is not None:
            if not self.form.validates():
                raise web.SeeOther('/post/' + post_id)
            else:
                user_model().update_session(session.user_id)
                length, cost = money_model().cal_comment(self.form.d.content)
                if session.money < cost:
                    self.crumb.append('财富不够')
                    return render.no_money('财富不够', '你的财富值不够，不能创建改主题 :(', self.crumb.output())
                content = html2db(self.form.d.content)
                content, receiver_list = notify_model().convert_content(content)
                create_time = time.time()
                comment_id = comment_model().insert({'user_id' : session.user_id, 'post_id' : post_id, 'content' : content, 'time' : create_time})
                money_type_id = money_type_model().get_one({'name':'comment'})['id']
                money_model().insert({'user_id':session.user_id, 'money_type_id':money_type_id, 'amount':-cost, 'length':length, 'balance':user_model().update_money(session.user_id, -cost), 'foreign_id':comment_id})
                if session.user_id != post.user_id:
                    money_model().insert({'user_id':post.user_id, 'money_type_id':money_type_id, 'amount':cost, 'length':length, 'foreign_id':comment_id, 'balance':user_model().update_money(post.user_id, cost)})
                    # notify
                    notify_model().insert({'user_id':session.user_id, 'receiver':post.user_id, 'type_id':notify_type_model().get_one({'name':'comment'}).id, 'foreign_id':comment_id})
                # notify
                receiver_list = list_diff(receiver_list, [session.name, user_model().get_one({'id':post.user_id}).name])
                notify_model().insert_notify(session.user_id, receiver_list, 'comment_at', comment_id)
                user_model().update_session(session.user_id)
                post_model().update({'id':post_id}, {'last_update':create_time})
                post_model().count_comment(post_id)
                raise web.SeeOther('/post/' + post_id)
        else:
             raise web.SeeOther('/post/' + post_id)

class thanks:
    def POST(self):
        import json
        json_dict = {'success':0, 'msg':'', 'script':''}
        comment_id = web.input(comment_id=None)['comment_id']
        comment = comment_model().get_one({'id':comment_id})
        if comment_id and comment:
            if session.user_id is None:
                post = post_model().get_one({'id':comment.post_id})
                json_dict['msg'] = '你要先登录的亲'
                json_dict['script'] = 'location.href=\'/login?next=/post/'+str(post.id)+'#reply-'+str(comment_id)+'\''
            elif comment.user_id != session.user_id:
                comment_thanks_id = comment_thanks_model().unique_insert({'user_id':session.user_id, 'comment_id':comment_id})
                if comment_thanks_id:
                    comment_thanks_model().update({'id':comment_thanks_id}, {'time':int(time.time())})
                    cost = money_model().cal_thanks()
                    money_type_id = money_type_model().get_one({'name':'comment_thanks'})['id']
                    money_model().insert({'user_id':session.user_id, 'money_type_id':money_type_id, 'amount':-cost, 'balance':user_model().update_money(session.user_id, -cost), 'foreign_id':comment_thanks_id})
                    money_model().insert({'user_id':comment.user_id, 'money_type_id':money_type_id, 'amount':cost, 'foreign_id':comment_thanks_id, 'balance':user_model().update_money(comment.user_id, cost)})
                    comment_model().count_thanks(comment_id)
                    user_model().update_session(session.user_id)
                    json_dict['success'] = 1
                else:
                    json_dict['msg'] = '你已经感谢过了不是吗？'
            else:
                json_dict['msg'] = '你不能感谢你自己不是吗？'
        else:
            json_dict['message'] = '评论不存在'
        return json.dumps(json_dict)
########NEW FILE########
__FILENAME__ = index
# -- coding: utf8 --
import web
session = web.config._session 
from config.config import render
from models.post_model import *
from models.node_model import *
from models.user_model import *
from models.comment_model import *
from models.cat_model import *
from libraries.crumb import Crumb
from libraries.pagination import *

class index:
    def GET(self):
        title = '首页'
        #sql = 'SELECT post_id FROM comment GROUP BY post_id ORDER BY MAX(time) DESC LIMIT 20'
        #post_ids = post_model().query_result(sql)
        posts = post_model().trends()

        cats_result = cat_model().get_all()
        cats = []
        for cat_result in cats_result:
            cat = {'cat':cat_result}
            node = node_model().get_all({'category_id':cat_result.id})
            cat['node'] = node
            cats.append(cat)
        return render.index(cats, posts, title)

class recent:
    def GET(self):
        #sql = 'SELECT post_id FROM comment GROUP BY post_id ORDER BY MAX(time) DESC LIMIT 20'
        #post_ids = post_model().query_result(sql)
        crumb = Crumb()
        limit = 50
        total = post_model().count_table()
        pagination = Pagination('/recent', total, limit = limit)
        page = pagination.true_page(web.input(p=1)['p'])
        posts = post_model().trends(limit, (page-1) * limit)
        crumb.append('最近的主题')
        return render.recent('最近的主题', total, crumb.output(), posts, pagination.output())

class about:
    def GET(self):
        crumb = Crumb()
        crumb.append('关于')
        return render.about('关于', crumb.output())

########NEW FILE########
__FILENAME__ = node
# -- coding: utf8 --
import web
session = web.config._session
from config.config import render
from models.post_model import *
from models.node_model import *
from models.user_model import *
from models.user_meta_model import *
from models.comment_model import *
from libraries.crumb import Crumb
from libraries.pagination import Pagination

# 显示某节点的文章
class index:
    
    def __init__(self):
        self.crumb = Crumb()
    
    def GET(self, node_name):
        limit = 10
        node = node_model().get_one({'name': node_name})
        if node is None:
            self.crumb.append('节点未找到')
            return render.node_nf('节点未找到', self.crumb.output())
        else:
            self.crumb.append(node.display_name)
            node_fav = False
            if session.user_id:
                if user_meta_model().get_one({'user_id':session.user_id, 'meta_key':'node_fav', 'meta_value':node.id}):
                    node_fav = True
            total_rows = post_model().count_table({'node_id':node.id})
            pagination = Pagination('/node/'+node_name, total_rows, limit = limit)
            page = pagination.true_page(web.input(p=1)['p'])
            posts = post_model().trends(limit, (page-1) * limit, node.id)
            return render.node_posts(posts, node, total_rows, node_fav, self.crumb.output(), pagination.output())

class fav:
    
    def __init__(self):
        self.crumb = Crumb()
    
    def GET(self, node_name):
        node = node_model().get_one({'name': node_name})
        if node is None:
            self.crumb.append('节点未找到')
            return render.node_nf('节点未找到', self.crumb.output())
        if session.user_id is None:
            raise web.SeeOther('/login?next=/node/'+node_name)
        user_meta_model().unique_insert({'user_id':session.user_id, 'meta_key':'node_fav', 'meta_value':node.id})
        user_model().update({'id':session.user_id}, {'node_favs':user_meta_model().count_meta({'user_id':session.user_id, 'meta_key':'node_fav'})})
        user_model().update_session(session.user_id)
        raise web.SeeOther('/node/'+node_name)

class unfav:
    
    def __init__(self):
        self.crumb = Crumb()
    
    def GET(self, node_name):
        node = node_model().get_one({'name': node_name})
        if node is None:
            self.crumb.append('节点未找到')
            return render.node_nf('节点未找到', self.crumb.output())
        if session.user_id is None:
            raise web.SeeOther('/login?next=/node/'+node_name)
        user_meta_model().delete({'user_id':session.user_id, 'meta_key':'node_fav', 'meta_value':node.id})
        user_model().update({'id':session.user_id}, {'node_favs':user_meta_model().count_meta({'user_id':session.user_id, 'meta_key':'node_fav'})})
        user_model().update_session(session.user_id)
        raise web.SeeOther('/node/'+node_name)
########NEW FILE########
__FILENAME__ = notifications
# -- coding: utf8 --
import web
session = web.config._session
from config.config import render
from models.post_model import *
from models.node_model import *
from models.user_model import *
from models.user_meta_model import *
from models.comment_model import *
from models.notify_model import *
from models.notify_type_model import *
from libraries.crumb import Crumb
from libraries.pagination import Pagination

class index:

    def __init__(self):
        if session.user_id is None:
            raise web.SeeOther('/login?next=/notifications')
    def GET(self):
        crumb = Crumb()
        condition = {'receiver':session.user_id}
        total = notify_model().count_table(condition)
        limit = 10
        pagination = Pagination('/notifications', total, limit = limit)
        page = pagination.true_page(web.input(p=1)['p'])
        notify_result = notify_model().get_all(condition, order = 'id DESC', limit = limit, offset = (page-1)*limit)
        notifications = []
        if notify_result is not None:
            for notify in notify_result:
                post = None
                user = None
                comment = None
                notify_type = notify_type_model().get_one({'id':notify.type_id}).name
                user = user_model().get_one({'id':notify.user_id})
                if notify_type == 'post_at':
                    post = post_model().get_one({'id':notify.foreign_id})
                elif notify_type == 'comment' or notify_type == 'comment_at':
                    comment = comment_model().get_one({'id':notify.foreign_id})
                    post = post_model().get_one({'id':comment.post_id})
                notifications.append({'notify':notify, 'post':post, 'user':user, 'comment':comment, 'type':notify_type})
        notify_model().mark_as_read(session.user_id)
        crumb.append('提醒系统')
        return render.notify('提醒系统', crumb.output(), total, notifications, pagination.output())

class check:

    def __init__(self):
        if session.user_id is None:
            return 0
    def POST(self):
        if web.input(ajax = None):
            return notify_model().count_table({'receiver':session.user_id, 'unread':'1'})
        else:
            return '0'

class delete:

    def __init__(self):
        if session.user_id is None:
            raise web.SeeOther('/login?next=/notifications')
    def GET(self, id):
        notify = notify_model().get_one({'id':id})
        if notify is not None and notify.receiver == session.user_id:
            notify_model().delete({'id':id})
        raise web.SeeOther('/notifications')
########NEW FILE########
__FILENAME__ = post
# -- coding: utf8 --
import web
session = web.config._session
import time
from config.config import render
from models.post_model import *
from models.post_thanks_model import *
from models.node_model import *
from models.user_model import *
from models.user_meta_model import *
from models.comment_model import *
from models.comment_thanks_model import *
from models.money_model import *
from models.money_type_model import *
from models.notify_model import *
from models.notify_type_model import *
from libraries.crumb import Crumb
from libraries.helper import *
from libraries.pagination import *

# 查看单个帖子
class view:
    
    def __init__(self):
        self.crumb = Crumb()
    
    def POST(self, id):
        raise web.SeeOther('/post/' + str(id))
    
    def GET(self, id):
        limit = 10
        post_model().add_view(id)
        post = post_model().get_one({'id':id})
        if post is None:
            self.crumb.append('主题未找到')
            return render.post_nf('主题未找到', self.crumb.output())
        else:
            post_fav = False
            if session.user_id:
                if user_meta_model().get_one({'user_id':session.user_id, 'meta_key':'post_fav', 'meta_value':post.id}):
                    post_fav = True
            favs = user_meta_model().count_meta({'meta_key':'post_fav','meta_value':id})
            node = node_model().get_one({'id':post.node_id})
            user = user_model().get_one({'id':post.user_id})
            #return user.name
            self.crumb.append(node.display_name, '/node/'+node.name)
            thanks = False
            if session.user_id is not None:
                if post_thanks_model().get_one({'user_id':session.user_id, 'post_id':post.id}):
                    thanks = True
            condition = {'post_id' : post.id}
            # Pagination
            total = comment_model().count_table(condition)
            pagination = Pagination('/post/'+str(post.id), total, limit = 100)
            page = pagination.true_page(web.input(p=1)['p'])
            comments_result = comment_model().get_all(condition, order = 'time ASC', limit = 100, offset = (page-1)*100)
            comments = []
            if comments_result is not None:
                for comment_result in comments_result:
                    comment_user = user_model().get_one({'id':comment_result.user_id})
                    comment_thanks = False
                    if session.user_id is not None:
                        if comment_thanks_model().get_one({'user_id':session.user_id, 'comment_id':comment_result.id}):
                            comment_thanks = True
                    comments.append({'comment':comment_result, 'user':comment_user, 'thanks':comment_thanks})
            form = comment_model().form
            return render.post_view(post, user, comments, form, post_fav, favs, thanks, self.crumb.output(), pagination)

# 创建帖子
class create:
    
    def __init__(self):
        self.crumb = Crumb()
        self.form = post_model().form
    
    def GET(self, node_name):
        if session.user_id is None:
            raise web.SeeOther('/login?next=/post/create/' + node_name)
        conditions = {'name' : node_name}
        node = node_model().get_one(conditions)
        self.crumb.append(node.display_name, '/node/'+node.name)
        self.crumb.append('创建新主题')
        if node is None:
            self.crumb.claer()
            return render.not_found('节点未找到', '节点未找到')
        title = '创建主题'
        return render.create_post(self.form, title, self.crumb.output())
        
    def POST(self, node_name):
        if session.user_id is None:
            raise web.SeeOther('/login?next=/post/create' + node_name)
        conditions = {'name' : node_name}
        node = node_model().get_one(conditions)
        if node is None:
            return render.not_found('节点未找到', '节点未找到')
        if not self.form.validates():
            return render.create_post(self.form, '创建失败， 请重创:D', self.crumb.output())
        user_model().update_session(session.user_id)
        length, cost = money_model().cal_post(self.form.d.content)
        if session.money < cost:
            self.crumb.append('财富不够')
            return render.no_money('财富不够', '你的财富值不够，不能创建改主题 :(', self.crumb.output())
        title = strip_tags(self.form.d.title)
        content = html2db(self.form.d.content)
        content, receiver_list = notify_model().convert_content(content)
        create_time = time.time()
        post_id = post_model().insert({'title' : title, 'content' : content, 'node_id' : node.id, 'time' : create_time, 'last_update':create_time, 'user_id' : session.user_id})
        # money
        money_type_id = money_type_model().get_one({'name':'post'})['id']
        money_model().insert({'user_id':session.user_id, 'money_type_id':money_type_id, 'amount':-cost, 'length':length, 'balance':user_model().update_money(session.user_id, -cost), 'foreign_id':post_id})
        # notify
        receiver_list = list_diff(receiver_list, [session.name])
        notify_model().insert_notify(session.user_id, receiver_list, 'post_at', post_id)
        user_model().update_session(session.user_id)
        raise web.seeother('/post/' + str(post_id))

# 收藏帖子
class fav:
    
    def __init__(self):
        self.crumb = Crumb()
    
    def GET(self, post_id):
        post = post_model().get_one({'id':post_id})
        if post is None:
            self.crumb.append('主题未找到')
            return render.post_nf('主题未找到', self.crumb.output())
        if session.user_id is None:
            raise web.SeeOther('/login?next=/post/fav/'+post_id)
        user_meta_model().unique_insert({'user_id':session.user_id, 'meta_key':'post_fav', 'meta_value':post_id})
        user_model().update({'id':session.user_id}, {'post_favs':user_meta_model().count_meta({'user_id':session.user_id, 'meta_key':'post_fav'})})
        user_model().update_session(session.user_id)
        raise web.SeeOther('/post/' + post_id)

class unfav:
    
    def GET(self, post_id):
        if session.user_id is None:
                raise web.SeeOther('/login?next=/post/unfav/'+post_id)
        user_meta_model().delete({'user_id':session.user_id, 'meta_key':'post_fav','meta_value':post_id})
        user_model().update({'id':session.user_id}, {'post_favs':user_meta_model().count_meta({'user_id':session.user_id, 'meta_key':'post_fav'})})
        user_model().update_session(session.user_id)
        raise web.SeeOther('/post/'+post_id)

class thanks:
    def POST(self):
        import json
        json_dict = {'success':0, 'msg':'', 'script':''}
        post_id = web.input(post_id=None)['post_id']
        post = post_model().get_one({'id':post_id})
        if post_id and post:
            if session.user_id is None:
                json_dict['msg'] = '你要先登录的亲'
                json_dict['script'] = 'location.href=\'/login?next=/post/'+post.id+'\''
            elif post.user_id != session.user_id:
                post_thanks_id = post_thanks_model().unique_insert({'user_id':session.user_id, 'post_id':post_id})
                if post_thanks_id:
                    post_thanks_model().update({'id':post_thanks_id}, {'time':int(time.time())})
                    cost = money_model().cal_thanks()
                    money_type_id = money_type_model().get_one({'name':'post_thanks'})['id']
                    money_model().insert({'user_id':session.user_id, 'money_type_id':money_type_id, 'amount':-cost, 'balance':user_model().update_money(session.user_id, -cost), 'foreign_id':post_thanks_id})
                    money_model().insert({'user_id':post.user_id, 'money_type_id':money_type_id, 'amount':cost, 'foreign_id':post_thanks_id, 'balance':user_model().update_money(post.user_id, cost)})
                    post_model().count_thanks(post_id)
                    user_model().update_session(session.user_id)
                    json_dict['success'] = 1
                else:
                    json_dict['msg'] = '你已经感谢过了不是吗？'
            else:
                json_dict['msg'] = '你不能感谢你自己不是吗？'
        else:
            json_dict['message'] = '评论不存在'
        return json.dumps(json_dict)
########NEW FILE########
__FILENAME__ = user
# -- coding: utf8 --
import web
session = web.config._session
import hashlib
import time
import random
import string
from config.config import render
from models.user_model import *
from models.user_meta_model import *
from models.post_model import *
from models.post_thanks_model import *
from models.comment_thanks_model import *
from models.node_model import *
from models.comment_model import *
from models.money_model import *
from models.money_type_model import *
from libraries.error import *
from libraries.crumb import *
from libraries.pagination import *

class login:
    
    def __init__(self):
        if session.user_id:
            raise web.SeeOther('/')
        self.title = '登录'
        self.crumb = Crumb()
        self.crumb.append('登录')
        self.form = user_model().login_form

    def GET(self):
        return render.login(self.form, self.title, self.crumb.output())
    
    def POST(self):
        if not self.form.validates():
            return render.login(self.form, '登录失败，请重登', self.crumb.output())
        condition = {'name' : self.form.d.name}
        # MD5加密 密码
        #condition['password'] = hashlib.md5(condition['password']).hexdigest()
        user = user_model().get_one(condition)
        if user is None:
            return render.login(self.form, '用户名不存在', self.crumb.output())
        auth_from_form = hashlib.md5(hashlib.md5(self.form.d.password).hexdigest() + user.auth).hexdigest()
        if auth_from_form != user.password:
            return render.login(self.form, '密码错误', self.crumb.output())
        user_model().update_session(user.id)
        user_model().set_cookie(user.id)
        data = web.input();
        try:
            if data['next'] is not None:
                raise web.SeeOther(data['next'])
            else:
                raise web.SeeOther('/')
        except KeyError:
            raise web.SeeOther('/')

class signup:

    def __init__(self):
        self.form = user_model().signup_form
        self.crumb = Crumb()
        self.crumb.append('注册')
    
    def GET(self):
        title = '注册'
        return render.signup(self.form, title, self.crumb.output())
    
    def POST(self):
        if not self.form.validates():
            return render.signup(self.form, '注册失败，请重注', self.crumb.output())
        try:
            condition = {'name':self.form.d.name}
            user = user_model().get_one(condition)
            # 对密码进行 md5 加密
            auth = string.join(random.sample(['z','y','x','w','v','u','t','s','r','q','p','o','n','m','l','k','j','i','h','g','f','e','d','c','b','a'], 5)).replace(' ','')
            password = hashlib.md5(hashlib.md5(self.form.d.password).hexdigest() + auth).hexdigest()
            #password = hashlib.md5(self.form.d.password).hexdigest()
            if user is not None:
                raise ValueExistsError('用户名已经存在')
            condition = {'email' : self.form.d.email}
            user = user_model().get_one(condition)
            if user is not None:
                raise ValueExistsError('邮箱已经存在')
            user_model().insert({'name' : self.form.d.name, 'email' : self.form.d.email, 'password' : password, 'regist_time' : time.time(), 'auth' : auth})
        except ValueExistsError, x:
            return render.signup(self.form, x.message, self.crumb.output())
        raise web.SeeOther('/')

# 注销
class logout:
    
    def GET(self):
        session.kill()
        web.setcookie('auth', '', -1)
        raise web.SeeOther('/')

# 设置
class settings:

    def __init__(self):
        if session.user_id is None:
            raise web.SeeOther('/login?next=/settings')
        self.setting_form = user_model().setting_form
        self.pass_form = user_model().pass_form
        self.crumb = Crumb()
    
    def GET(self):
        self.crumb.append('设置')
        user = user_model().get_one({'id':session.user_id})
        self.setting_form.name.set_value(user.name)
        self.setting_form.email.set_value(user.email)
        self.setting_form.signature.set_value(user.signature)
        self.setting_form.outsite_link.set_value(user.outsite_link)
        return render.settings('设置', user, self.setting_form, self.pass_form, self.crumb.output())
    def POST(self):
        self.crumb.append('设置')
        user = user_model().get_one({'id':session.user_id})
        self.setting_form.name.set_value(user.name)
        if not self.setting_form.validates():
            self.setting_form.name.set_value(user.name)
            self.setting_form.email.set_value(user.email)
            self.setting_form.email.set_value(user.signature)
            self.setting_form.email.set_value(user.outsite_link)
            return render.settings('设置', user, self.setting_form, self.pass_form, self.crumb.output())
        else:
            user_model().update({'id':user.id}, {'email':self.setting_form.d.email, 'signature':self.setting_form.d.signature, 'outsite_link':self.setting_form.d.outsite_link.replace('http://', '').replace('https://', '')})
            
            raise web.SeeOther('/settings')

class password:

    def __init__(self):
        if session.user_id is None:
            raise web.SeeOther('/login?next=/settings/password')
        self.form = user_model().pass_form
        self.crumb = Crumb()
    def GET(self):
        self.crumb.append('设置', '/settings')
        self.crumb.append('修改密码')
        return render.password('修改密码', self.crumb.output(), self.form)
    def POST(self):
        self.crumb.append('设置', '/settings')
        self.crumb.append('修改密码')
        user = user_model().get_one({'id':session.user_id})
        if self.form.validates():
            password = hashlib.md5(hashlib.md5(self.form.d.origin_password).hexdigest() + user.auth).hexdigest()
            if user.password == password:
                auth = string.join(random.sample(['z','y','x','w','v','u','t','s','r','q','p','o','n','m','l','k','j','i','h','g','f','e','d','c','b','a'], 5)).replace(' ','')
                new_password = hashlib.md5(hashlib.md5(self.form.d.new_password).hexdigest() + auth).hexdigest()
                user_model().update({'id':user.id}, {'password':new_password, 'auth':auth})
                raise web.SeeOther('/settings')
            else:
                return render.password('原密码不正确', self.crumb.output(), self.form)
        else:
            return render.password('修改密码', self.crumb.output(), self.form)


class profile:
    
    def GET(self, name):
        limit = 10
        user = user_model().get_one({'name':name})
        if user is None:
            crumb = Crumb()
            crumb.append('会员未找到')
            return render.user_nf('会员未找到', crumb.output())
        else:
            posts_result = post_model().get_all({'user_id':user.id}, limit = limit, order = 'time DESC')
            if len(posts_result) > 0:
                posts = []
                for post_result in posts_result:
                    post = {'post':post_result}
                    node = node_model().get_one({'id':post_result.node_id})
                    post['node'] = node
                    comment = comment_model().get_one({'post_id':post_result.id}, order='time DESC')
                    if comment:
                        comment_user = user_model().get_one({'id':comment.user_id})
                        post['comment_user'] = comment_user
                    else:
                        post['comment_user'] = None
                    posts.append(post)
            else:
                posts = None
            comments_result = comment_model().get_all({'user_id':user.id}, limit = limit, order = 'time DESC')
            if len(comments_result) > 0:
                comments = []
                for comment_result in comments_result:
                    post = post_model().get_one({'id':comment_result.post_id})
                    post_user = user_model().get_one({'id':post.user_id})
                    comment = {'post':post, 'comment':comment_result, 'post_user':post_user}
                    comments.append(comment)
            else:
                comments = None
            following = False
            if session.user_id:
                if user_meta_model().get_one({'user_id':session.user_id, 'meta_key':'follow', 'meta_value':user.id}):
                    following = True
            return render.profile(user.name, user, posts, comments, following)

class avatar:
    
    def __init__(self):
        if session.user_id is None:
            raise web.SeeOther('/login?next=/settings/avatar')
        self.crumb = Crumb()
        self.user = user_model().get_one({'id':session.user_id})
    
    def GET(self):
        self.crumb.append('设置', '/settings')
        self.crumb.append('上传头像')
        return render.avatar('上传头像', self.user, self.crumb.output())
    def POST(self):
        import cgi
        import os
        cgi.maxlen = 2 * 1024 * 1024 # 2MB
        try:
            x = web.input(avatar={})
        except ValueError:
            return render.avatar('上传头像', self.user, self.crumb.output(), ' <<超过大小限制')
        if 'avatar' in x:
            #客户端为windows时注意
            filepath=x.avatar.filename.replace('\\','/')
            #获取文件名
            filename=filepath.split('/')[-1]
            #获取后缀
            ext = filename.split('.', 1)[1].lower()
            ext_allow = ('jpg', 'png', 'gif', 'jpeg')
            #判断文件后缀名 
            if ext in ext_allow:
                #要上传的路径
                filedir = 'static/avatar/tmp/'
                try:
                    os.makedirs('static/avatar/tmp')
                except:
                    pass
                filename = str(session.user_id) +'.'+ext
                if os.path.exists(filedir+filename):
                    os.remove(filedir+filename)
                fout = open(filedir + filename, 'wb')
                fout.write(x.avatar.file.read())
                fout.close()
                user_model().set_avatar(filename, self.user.id)
                error = False
            else:
                message = ' <<请上传指定格式文件'
                error = True
        if error:
            return render.avatar('上传头像', self.user, self.crumb.output(), message)
        else:
            raise web.SeeOther('/settings/avatar')

# 收藏的主题
class post_favs():

    def __init__(self):
        if session.user_id is None:
            raise web.SeeOther('/login?next=/my/posts')
        self.crumb = Crumb()
    
    def GET(self):
        limit = 10
        self.crumb.append('我收藏的主题')
        user = user_model().get_one({'id':session.user_id})
        pagination = Pagination('/my/posts', user.post_favs, limit = limit)
        if user.post_favs > 0:
            page = pagination.true_page(web.input(p=1)['p'])
            post_favs = user_meta_model().get_all({'user_id':user.id, 'meta_key':'post_fav'}, limit = limit, offset = (page-1)*limit, order = 'id DESC')
            posts = []
            for post_fav in post_favs:
                post_result = post_model().get_one({'id':post_fav.meta_value})
                post = {'post':post_result}
                user = user_model().get_one({'id':post_result.user_id})
                post['user'] = user
                node = node_model().get_one({'id':post_result.node_id})
                post['node'] = node
                comment = comment_model().get_one({'post_id':post_result.id}, order='time DESC')
                if comment:
                    comment_user = user_model().get_one({'id':comment.user_id})
                    post['comment_user'] = comment_user
                else:
                    post['comment_user'] = None
                posts.append(post)
        else:
            posts = None
        return render.post_favs('我收藏的主题', user, posts, self.crumb.output(), pagination.output())

# 来自收藏节点的主题
class node_favs:

    def __init__(self):
        if session.user_id is None:
            raise web.SeeOther('/login?next=/my/nodes')
        self.crumb = Crumb()
    
    def GET(self):
        limit = 10
        self.crumb.append('来自我收藏的节点的最新主题')
        # 取出收藏的节点id
        node_favs = user_meta_model().get_all({'user_id':session.user_id, 'meta_key':'node_fav'})
        if len(node_favs) > 0 :
            nodes = []
            for node_fav in node_favs:
                nodes.append(node_fav.meta_value)
            total_rows = post_model().count_table({'node_id':nodes})
            pagination = Pagination('/my/nodes', total_rows, limit = limit)
            page = pagination.true_page(web.input(p=1)['p'])
            posts_result = post_model().get_all(conditions = {'node_id': nodes}, order = 'time DESC', limit = limit, offset = (page-1)*limit)
            posts = []
            for post_result in posts_result:
                post = {'post':post_result}
                user = user_model().get_one({'id':post_result.user_id})
                post['user'] = user
                node = node_model().get_one({'id':post_result.node_id})
                post['node'] = node
                comment = comment_model().get_one({'post_id':post_result.id}, order='time DESC')
                if comment:
                    comment_user = user_model().get_one({'id':comment.user_id})
                    post['comment_user'] = comment_user
                else:
                    post['comment_user'] = None
                posts.append(post)
        else:
            posts = None
            total_rows = 0
            pagination = Pagination('/my/nodes', total_rows)
            page = pagination.true_page(web.input(p=1)['p'])
        return render.node_favs('来自我收藏的节点的最新主题', posts, total_rows, self.crumb.output(), pagination.output())

# 用户创建的主题
class posts:
    
    def GET(self, name):
        limit = 10
        user = user_model().get_one({'name':name})
        crumb = Crumb()
        if user:
            crumb.append(name, '/profile/'+name)
            crumb.append('全部主题')
            total_rows = post_model().count_table({'user_id':user.id})
            pagination = Pagination('/profile/'+name+'/posts', total_rows, limit = limit)
            page = pagination.true_page(web.input(p=1)['p'])
            posts_result = post_model().get_all({'user_id':user.id}, limit = limit, offset = (page-1) * limit, order = 'time DESC')
            posts = []
            for post_result in posts_result:
                post = {'post':post_result}
                node = node_model().get_one({'id':post_result.node_id})
                post['node'] = node
                comment = comment_model().get_one({'post_id':post_result.id}, order='time DESC')
                if comment:
                    comment_user = user_model().get_one({'id':comment.user_id})
                    post['comment_user'] = comment_user
                else:
                    post['comment_user'] = None
                posts.append(post)
            return render.user_posts('全部主题', user,  posts, total_rows, crumb.output(), pagination.output())
        else:
            crumb.append('会员未找到')
            return render.user_nf('会员未找到', crumb.output())

# 用户创建的回复
class comments:
    
    def GET(self, name):
        limit = 10
        user = user_model().get_one({'name':name})
        crumb = Crumb()
        if user:
            crumb.append(name, '/profile/'+name)
            crumb.append('全部回复')
            total = comment_model().count_table({'user_id':user.id})
            pagination = Pagination('/profile/'+name+'/comments', total, limit = limit)
            page = pagination.true_page(web.input(p=1)['p'])
            comments_result = comment_model().get_all({'user_id':user.id}, limit = limit, offset = (page-1)*limit, order = 'time DESC')
            if len(comments_result) > 0:
                comments = []
                for comment_result in comments_result:
                    post = post_model().get_one({'id':comment_result.post_id})
                    post_user = user_model().get_one({'id':post.user_id})
                    comment = {'post':post, 'comment':comment_result, 'post_user':post_user}
                    comments.append(comment)
            else:
                comments = None
            return render.user_comments('全部回复', comments, total, crumb.output(), pagination.output())
        else:
            crumb.append('会员未找到')
            return render.user_nf('会员未找到', crumb.output())

# 关注用户
class follow:
    
    def GET(self, name):
        user = user_model().get_one({'name':name})
        if user is None:
            crumb = Crumb()
            crumb.append('会员未找到')
            return render.user_nf('会员未找到', crumb.output())
        else:
            if session.user_id is None:
                raise web.SeeOther('/login?next=/profile/'+name)
            user_meta_model().unique_insert({'user_id':session.user_id, 'meta_key':'follow', 'meta_value':user.id})
            user_model().update({'id':session.user_id}, {'user_favs':user_meta_model().count_meta({'user_id':session.user_id, 'meta_key':'follow'})})
            user_model().update_session(session.user_id)
            raise web.SeeOther('/profile/'+name)

# 取消关注用户
class unfollow:
    
    def GET(self, name):
        user = user_model().get_one({'name':name})
        if user is None:
            crumb = Crumb()
            crumb.append('会员未找到')
            return render.user_nf('会员未找到', crumb.output())
        else:
            if session.user_id is None:
                raise web.SeeOther('/login?next=/profile/'+name)
            user_meta_model().delete({'user_id':session.user_id, 'meta_key':'follow', 'meta_value':user.id})
            user_model().update({'id':session.user_id}, {'user_favs':user_meta_model().count_meta({'user_id':session.user_id, 'meta_key':'follow'})})
            user_model().update_session(session.user_id)
            raise web.SeeOther('/profile/'+name)

# 来自关注用户的帖子
class following:
    
    def __init__(self):
        if session.user_id is None:
            raise web.SeeOther('/login?next=/user/nodes')
        self.crumb = Crumb()
    
    def GET(self):
        limit = 10
        self.crumb.append('我关注的人的最新主题')
        # 取出收藏的节点id
        followings = user_meta_model().get_all({'user_id':session.user_id, 'meta_key':'follow'})
        if len(followings) > 0 :
           user_favs = []
           for following in followings:
               user_favs.append(following.meta_value)
           total_rows = post_model().count_table({'user_id':user_favs})
           pagination = Pagination('/my/following', total_rows, limit = limit)
           page = pagination.true_page(web.input(p=1)['p'])
           posts_result = post_model().get_all(conditions = {'user_id': user_favs}, order = 'time DESC', limit = limit, offset = (page-1)*limit)
           posts = []
           for post_result in posts_result:
               post = {'post':post_result}
               user = user_model().get_one({'id':post_result.user_id})
               post['user'] = user
               node = node_model().get_one({'id':post_result.node_id})
               post['node'] = node
               comment = comment_model().get_one({'post_id':post_result.id}, order='time DESC')
               if comment:
                   comment_user = user_model().get_one({'id':comment.user_id})
                   post['comment_user'] = comment_user
               else:
                   post['comment_user'] = None
               posts.append(post)
        else:
           posts = None
           total_rows = 0
           pagination = Pagination('/my/nodes', total_rows)
           page = pagination.true_page(web.input(p=1)['p'])
        return render.following_posts('来自我收藏的节点的最新主题', posts, total_rows, self.crumb.output(), pagination.output())

class balance:
    
    def __init__(self):
        if session.user_id is None:
            raise web.SeeOther('/login?next=/balance')
        self.crumb = Crumb()
        
    def GET(self):
        limit = 20
        total = money_model().count_table({'user_id':session.user_id})
        pagination = Pagination('/balance', total, limit = limit)
        page = pagination.true_page(web.input(p=1)['p'])
        records_result = money_model().get_all({'user_id':session.user_id}, limit = limit, offset = (page-1)*limit, order = 'id DESC')
        money_types_result = money_type_model().get_all()
        money_type = {}
        for money_type_result in money_types_result:
            money_type[money_type_result.id] = money_type_result.name
        records = []
        for record_result in records_result:
            # 发布的帖子或者是评论的帖子
            post = None
            # 发布或者收到的评论
            post_user = None
            post_thanks = None
            comment_thanks = None
            sender = None
            comment = None
            # 评论的用户
            comment_user = None
            try:
                type = money_type[record_result.money_type_id]
                if type == 'post':
                    post = post_model().get_one({'id':record_result.foreign_id})
                if type == 'comment':
                    comment = comment_model().get_one({'id':record_result.foreign_id})
                    comment_user = user_model().get_one({'id':comment.user_id})
                    post = post_model().get_one({'id':comment.post_id})
                if type == 'post_thanks':
                    post_thanks = post_thanks_model().get_one({'id':record_result.foreign_id})
                    post = post_model().get_one({'id':post_thanks.post_id})
                    sender = user_model().get_one({'id':post_thanks.user_id})
                    post_user = user_model().get_one({'id':post.user_id})
                if type == 'comment_thanks':
                    comment_thanks = comment_thanks_model().get_one({'id':record_result.foreign_id})
                    comment = comment_model().get_one({'id':comment_thanks.comment_id})
                    post = post_model().get_one({'id':comment.post_id})
                    comment_user = user_model().get_one({'id':comment.user_id})
                    sender = user_model().get_one({'id':comment_thanks.user_id})
            # 如果数据错误将不把这条记录输出到视图
            except AttributeError:
                continue
            else:
                record = {'record':record_result, 'type':type, 'comment':comment, 'post':post, 'post_user':post_user, 'sender':sender, 'comment_user':comment_user, 'post_thanks':post_thanks, 'comment_thanks':comment_thanks}
                records.append(record)
        self.crumb.append('账户余额')
        return render.money_record('账户余额', records, self.crumb.output(), pagination.output())
########NEW FILE########
__FILENAME__ = crumb
# -- coding: utf8 --

# 面包屑导航类
from models.site_model import *
class Crumb:
    
    def __init__(self):
        self.separator = '<span class="chevron">&nbsp;›&nbsp;</span>'

        self.content = [[site_model().get_option('title'), '/']]
    
    def set_separator(self, separator):
        self.separator = separator
    
    def append(self, name, url = None):
        self.content.append([name, url])
    
    def output(self):
        str = ''
        i = 0
        for item in self.content:
            i += 1
            if item[1] is None:
                str += item[0]
            else:
                str += '<a href="' + item[1] + '">' + item[0] + '</a>'
            if i < len(self.content):
                str += self.separator
        self.clear()
        return str
    
    def clear(self):
        self.__init__()
########NEW FILE########
__FILENAME__ = db
# -- coding: utf8 --
# 放弃使用该类
from config.config import db
from libraries.helper import *

# 自定义join查询方法
# join dict {'join_talbe': ['cur_field', 'target_field']}
# return dict [{'table' : data, 'table_joined' : data}, {'table' : data, 'table_joined' : data}]

def fetch_join(tb = None, condition = None, join = None, limit = 10, offset = 0):
    if tb is None:
        return None
    where = dict2where(condition)
    result = db.select(tb, where = where, limit = limit, offset = offset)
    if join is None:
        return result
    # 返回的结果列表
    result_joined = []
    for row in result:
        # 遍历出的每一行为一个字典，默认添加{主表：主表该行结果}
        row_joined = {tb : row}
        for join_table, join_fields in join.items():
            condition = {join_fields[1] : getattr(row, join_fields[0])}
            where = dict2where(condition)
            join_table_result = db.select(join_table, where = where)
            # join 查到的结果字典来更新行结果字典
            row_joined.update({join_table : join_table_result})
        #最终将包含join行的结果字典追加到返回的结果列表中
        result_joined.append(row_joined)
    return result_joined
########NEW FILE########
__FILENAME__ = error
# -- coding: utf8 --

# 自定义错误类

# 自定义值已经存在错误
class ValueExistsError(Exception):
    def __init__(self, message):
        Exception.__init__(self)
        self.message = message
########NEW FILE########
__FILENAME__ = helper
# -- coding: utf8 --
# 辅助函数库

# 将字典转换成sql where字符串
def dict2where(dict):
    if dict is not None:
        where_str = ''
        for key, value in dict.items():
            if isinstance(value, list):
                where_str += '`'+str(key)+'`' + ' in (' + ', '.join('\''+str(_value)+'\'' for _value in value) + ') AND'
            else:
                where_str += '`'+str(key)+'`' + '=\'' + str(value) + '\' AND '
        where_len = len(where_str)
        where = where_str[0 : where_len-4]
        return where
    else:
        return None

# 将字典转换成sql update语句
def dict2update(dict):
    if dict is not None:
        update_str = ''
        for key,value in dict.items():
            update_str += '`'+str(key)+'`' + '=\'' + str(value) + '\','
        update_len = len(update_str)
        update = update_str[0:update_len-1]
        return update

# 时间戳转为到现在的时间差
def stamp2during(stamp = 0):
    import time
    from math import ceil
    # 对当前时间向上取整，防止出现负数~
    cur_time = int(ceil(time.time()))
    during = cur_time-stamp
    if during < 30:
        return str(during) + ' 秒前'
    if during < 60:
        return '半分钟前'
    if during < 3600:
        return str(int(during/60)) + ' 分钟前'
    if during < 24*3600:
        return str(int(during/3600)) + ' 小时前'
    if during < 365*24*3600:
        return str(int(during/(24*3600))) + ' 天前'
    #return str(int(during/(24*3600))) + '天前'
    ltime=time.localtime(stamp)
    return time.strftime("%Y-%m-%d %H:%m:%S %p", ltime)

# 将时间戳转为合适格式时间
def stamp2time(stamp = 0):
    import time
    ltime=time.localtime(stamp)
    return time.strftime("%Y-%m-%d %H:%m:%S %p", ltime)

# 时间戳转为时间
def cur_date(format = "%Y-%m-%d %H:%m:%S %p"):
    import time
    import datetime
    return datetime.datetime.now().strftime(format)

def avatar_url(avatar, mode = 'normal'):
    import os
    avatar = str(avatar)
    path = 'static/avatar/'+mode+'/'
    if os.path.exists(path+avatar) and avatar != '':
        return '/'+path+avatar
    else:
        return '/'+path+'default.jpg'

def icon_url(icon, mode = 'normal'):
    import os
    icon = str(icon)
    path = 'static/icons/'+mode+'/'
    if os.path.exists(path+icon) and icon != '':
        return '/'+path+icon
    else:
        return '/'+path+'default.jpg'

def display_money(money):
    money = int(money)
    string = ''
    gold = 0
    silver = 0
    bronze = 0
    if money >= 10000:
        gold = money // 10000
        money = money % 10000
        string += str(gold) + ' '
        string += '<img src="/static/img/gold.png" alt="G" align="absmiddle" border="0" style="padding-bottom: 2px;">'
    if money >= 100:
        silver = money // 100
        money = money % 100
        if gold:
            string += ' '
        string += str(silver) + ' '
        string += '<img src="/static/img/silver.png" alt="S" align="absmiddle" border="0" style="padding-bottom: 2px;">'
    bronze = money
    if silver:
        string += ' '
    if bronze <= 0 and (gold or silver):
        pass
    else:
        string += str(bronze) + ' '
        string += '<img src="/static/img/bronze.png" alt="B" align="absmiddle" border="0">'
    return string

#转成html实体
def str2entity(str):
    import htmlentitydefs
    str = unicode(str)
    to = u''
    for i in str:
        if ord(i) in htmlentitydefs.codepoint2name:
            name = htmlentitydefs.codepoint2name.get(ord(i))
            to += "&" + name + ";"
    else:
        to += i
    return to

def html2db(str):
    #str = str.encode()
    str = str.replace("'", "\\'").replace('"', '\\"').replace('$', '\\$').replace('<', '&lt;').replace('>', '&gt;')
    return str 

def unique_list(list_):
    u_list = []
    for item in list_:
        if item not in u_list:
            u_list.append(item)
    return u_list

def list_diff(list_1, list_2):
    list_ = []
    for item in list_1:
        if item not in list_2:
            list_.append(item)
    return list_

def strip_tags(html):
    from HTMLParser import HTMLParser
    html=html.strip()
    html=html.strip("\n")
    result=[]
    parse=HTMLParser()
    parse.handle_data=result.append
    parse.feed(html)
    parse.close()
    return "".join(result)
########NEW FILE########
__FILENAME__ = pagination
# -- coding: utf8 --

import math

class Pagination:
    
    def __init__(self, base_url, total, limit = 10):
        self.base_url = base_url
        self.total = int(math.ceil(float(total)/float(limit)))
        if self.total == 0:
            self.total = 1
        self.limit = limit
        self.cur_page = 1
    
    def output(self):
        prev = ''
        next = ''
        page = '<strong class="fade">' + str(self.cur_page) + '/' + str(self.total) + '</strong>'
        if self.cur_page > 1:
            prev = '<input type="button" onclick="location.href=\'' + self.base_url + '?p=' + str(self.cur_page-1) + '\';" value="‹ 上一页" class="super normal button">'
        if self.cur_page < self.total:
            next = '<input type="button" onclick="location.href=\'' + self.base_url + '?p=' + str(self.cur_page+1)  + '\';" value="下一页 ›" class="super normal button">'
        string = '<table cellpadding="0" cellspacing="0" border="0" width="100%"><tbody><tr>'
        string += '<td width="120" align="left">' + prev + '</td>'
        string += '<td width="auto" align="center">' + page + '</td>'
        string += '<td width="120" align="right">' + next + '</td>'
        string += '</tr></tbody></table>'
        return string
    
    def true_page(self, page):
        page = int(page)
        # 加上等于避免 total=0 时出错
        if page <= 1:
            self.cur_page = 1
        elif page > self.total:
            self.cur_page = self.total
        else:
            self.cur_page = page
        return self.cur_page
########NEW FILE########
__FILENAME__ = widget
# -- coding: utf8 --
__metaclass__ = type

import os
import web
import time
import datetime
from models.node_model import *
from models.cat_model import *
from models.post_model import *
from models.user_model import *
from models.comment_model import *
render = web.template.render(os.path.abspath(os.path.dirname(__file__)) + '/../tpl/widget/')

def generator(widget_name):
    return eval(widget_name+'().run()')
    
class widget:
    
    def run(self):
        pass

# 站点统计小组件
class site_statics_widget(widget):
    def run(self):
        site_count = {}
        site_count['user'] = user_model().count_table()
        site_count['post'] = post_model().count_table()
        site_count['comment'] = comment_model().count_table()
        return render.site_statics(site_count)

# 今日热议主题小组件
class hot_posts_today_widget(widget):
    def run(self):
        ltime = time.localtime(time.time())
        time_start = int(time.mktime(datetime.datetime(ltime.tm_year, ltime.tm_mon, ltime.tm_mday).timetuple()))
        time_end = time_start + 24 * 60 * 60
        sql = 'SELECT `post_id` FROM comment WHERE `time` >= '+str(time_start)+' AND `time` <= '+str(time_end)+' GROUP BY post_id ORDER BY count(post_id) DESC LIMIT 10'
        post_ids = comment_model().query_result(sql)
        posts = []
        for row in post_ids:
            post = post_model().get_one({'id':row.post_id})
            user = user_model().get_one({'id':post.user_id})
            posts.append({'post':post, 'user':user})
        return render.hot_posts_tody(posts)

class user_panel_widget(widget):
    def run(self):
        return render.user_panel()

class ga_widget(widget):
    def run(self):
        return render.ga()
########NEW FILE########
__FILENAME__ = cat_model
# -- coding: utf8 --
__metaclass__ = type
import web
from models.model import *
from config.config import *

class cat_model(model):
    
    def __init__(self):
        super(cat_model, self).__init__('category')
        self.create_form = web.form.Form(
            web.form.Textbox('name', notnull, size=45, description="分类名，用于url，english please", class_='sl'),
            web.form.Textbox('display_name', notnull, size=45, description="显示名", class_='sl'),
            web.form.Textarea('description', notnull, class_='mle tall', description='分类描述'),
            web.form.Button('创建', class_='super normal button')
        )
        self.modify_form = web.form.Form(
            web.form.Textbox('name', size=45, description="cat name", class_='sl', disabled="disabled"),
            web.form.Textbox('display_name', notnull, size=45, description="display name", class_='sl'),
            web.form.Textarea('description', notnull, class_='mle tall', description='分类描述'),
            web.form.Button('修改', class_='super normal button')
        )
########NEW FILE########
__FILENAME__ = comment_model
# -- coding: utf8 --
__metaclass__ = type
import web
from models.model import *
from models.comment_thanks_model import *
from config.config import *

class comment_model(model):
     
    def __init__(self):
        super(comment_model, self).__init__('comment')
        self.form = web.form.Form(
            web.form.Textarea('content',
                notnull,
                rows=5,
                cols=80,
                description='',
                post='<div class="sep10"></div>',
                class_='mll'
            ),
            web.form.Button('回复',class_='super normal button')
        )
    
    def count_thanks(self, comment_id):
        super(comment_model, self).query('update ' + self._tb + ' set thanks = (select count(*) from ' + comment_thanks_model().table_name() + ' where ' + comment_thanks_model().table_name() + '.comment_id = ' + str(comment_id) + ') where id = ' + str(comment_id))
########NEW FILE########
__FILENAME__ = comment_thanks_model
# -- coding: utf8 --
__metaclass__ = type
import web
from models.model import *
from config.config import *

class comment_thanks_model(model):
    
    def __init__(self):
        super(comment_thanks_model, self).__init__('comment_thanks')
########NEW FILE########
__FILENAME__ = model
# -- coding: utf8 --
__metaclass__ = type
import web
from config.config import db
from libraries.helper import *

class model:
    _tb = None
    def __init__(self, tb = None):
        self._tb = tb
        self.db = db
    
    def get_one(self, conditions = None, what = '*', order = None):
        where = dict2where(conditions)
        try:
            return db.select(self._tb, where = where, order = order, limit = 1)[0]
        except IndexError:
            return None
    
    def get_all(self, conditions = None, order = None, limit = None, offset = None):
        where = dict2where(conditions)
        return db.select(self._tb, where = where, order = order, limit = limit, offset = offset)
    
    def insert(self, values = None):
        def q(x): return "(" + x + ")"
        if values:
            sql_query = 'INSERT INTO '+ self._tb + q(', '.join(values.keys())) + ' VALUES' + q(', '.join('\''+str(_value)+'\'' for _value in values.values()))
            db.query(sql_query)
            return self.last_insert_id()
        else:
           return None
    
    def unique_insert(self, values = None):
        if self.get_one(values) is None:
            return self.insert(values)
        else:
            return None
    
    def update(self, condition, values = None):
        where = dict2where(condition)
        update = dict2update(values)
        if values is not None:
            sql_query = 'UPDATE ' + self._tb + ' SET ' + update + ' WHERE ' + where
            db.query(sql_query)
        return True
    
    def delete(self, condition, limit = 1):
        where = dict2where(condition)
        if where is not None:
            sql_query = 'DELETE FROM ' + self._tb + ' WHERE ' + where + ' LIMIT 1'
            db.query(sql_query)
        else:
            return None
            
    def query(self, sql):
        db.query(sql)
        return True
    
    def query_result(self, sql):
        return db.query(sql)

    def last_insert_id(self):
        return db.query('select last_insert_id() as id')[0].id
    
    def table_name(self):
        return self._tb
    
    def count_table(self, conditions = None):
        sql = 'SELECT count(*) as rows FROM ' + self._tb
        where = ''
        if conditions is not None:
            where = dict2where(conditions)
            sql += ' WHERE ' + where
        return db.query(sql)[0].rows
########NEW FILE########
__FILENAME__ = money_model
#  coding: utf8 
__metaclass__ = type
from models.model import *
from models.money_option_model import *

class money_model(model):
    def __init__(self):
        super(money_model, self).__init__('money')
        # 将财富配置表数据取出
        self.ruler = {}
        options = money_option_model().get_all()
        for option in options:
            # 转成浮点进行下面的保留小数运算
            self.ruler[option.key] = float(option.value)
    
    def cal_post(self, content):
        if not isinstance(content, unicode):
            content = unicode(content)
        length = len_ = float(len(content))
        cost = self.ruler['post_cost']
        len_ -= self.ruler['post_length']
        if len_ > 0:
            cost += self.ruler['post_cost_add'] * (len_ / 100)
        return length, cost
    
    def cal_comment(self, content):
        if not isinstance(content, unicode):
            content = unicode(content)
        length = len_ = float(len(content))
        cost = self.ruler['comment_cost']
        len_ -= self.ruler['comment_length']
        if len_ > 0:
            cost += self.ruler['post_cost_add'] * (len_ / 100)
        return length, cost
    
    def cal_thanks(self):
        return self.ruler['thanks_cost']
########NEW FILE########
__FILENAME__ = money_option_model
# -- coding: utf8 --
__metaclass__ = type
from models.model import *

class money_option_model(model):
    
    def __init__(self):
        super(money_option_model, self).__init__('money_option')
########NEW FILE########
__FILENAME__ = money_type_model
# -- coding: utf8 --
__metaclass__ = type
from models.model import *

class money_type_model(model):
    
    def __init__(self):
        super(money_type_model, self).__init__('money_type')
########NEW FILE########
__FILENAME__ = node_model
# -- coding: utf8 --
__metaclass__ = type
from models.model import *
from config.config import *

class node_model(model):

    def __init__(self):
        super(node_model, self).__init__('node')
        self.create_form = web.form.Form(
            web.form.Textbox('name', notnull, size=45, description="节点名，用于url，english please", class_='sl'),
            web.form.Textbox('display_name', notnull, size=45, description="显示名", class_='sl'),
            web.form.Textarea('description', notnull, class_='mle tall', description='分类描述'),
            web.form.Button('创建', class_='super normal button')
        )
        self.modify_form = web.form.Form(
            web.form.Textbox('name', size=45, description="node name", class_='sl', disabled="disabled"),
            web.form.Textbox('display_name', notnull, size=45, description="display name", class_='sl'),
            web.form.Textarea('description', notnull, class_='mle tall', description='分类描述'),
            web.form.Button('修改', class_='super normal button')
        )
    
    def set_icon(self, filename, node_id):
        import Image
        import os
        path = 'static/icons/'
        im = Image.open(path+'tmp/'+filename)
        size = im.size
        if size[0] > size[1]:
            crop_size = size[1]
            left = (size[0]-size[1])/2
            right = size[1] + left
            upper = 0
            lower = size[1]
        else:
            crop_size = size[0]
            left = 0
            right = size[0]
            upper = (size[1]-size[0])/2
            lower = size[0] + upper
        box = (left, upper, right, lower)
        region = im.crop(box)
        region.save(path+'tmp/'+filename)
        im = Image.open(path+'tmp/'+filename)
        im.thumbnail((73, 73), Image.ANTIALIAS)
        im.save(path+'big/'+filename)
        im.thumbnail((48, 48), Image.ANTIALIAS)
        im.save(path+'normal/'+filename)
        im.thumbnail((24, 24), Image.ANTIALIAS)
        im.save(path+'tiny/'+filename)
        del im, region
        os.remove(path+'tmp/'+filename)
        self.update({'id':node_id}, {'icon':filename})
########NEW FILE########
__FILENAME__ = notify_model
#  coding: utf8 
__metaclass__ = type
import web
import re
from models.model import *
from models.user_model import *
from models.notify_type_model import *
from libraries.helper import *
class notify_model(model):

    ruler = re.compile('@[a-z0-9]+')

    def __init__(self):
        super(notify_model, self).__init__('notify')
        self.types = {}
        types = notify_type_model().get_all()
        for type_ in types:
            self.types[type_.name] = type_.id

    def convert_content(self, content):
        user_list = unique_list(self.ruler.findall(content))
        user_list_ = []
        for user_name in user_list:
            content = content.replace(user_name, '@<a href="/profile/'+user_name[1:]+'">'+user_name[1:]+'</a>')
            user_list_.append(user_name[1:])
        return content, user_list_

    def insert_notify(self, user_id, user_list, notify_type, foreign_id):
        if isinstance(user_list, list):
            for receiver in user_list:
                user = user_model().get_one({'name':receiver})
                if user is not None:
                    self.insert({'user_id':user_id, 'receiver':user.id, 'type_id':self.types[notify_type], 'foreign_id':foreign_id})
        else:
            user = user_model().get_one({'name':user_list})
            if user is not None:
                self.insert({'user_id':user_id, 'receiver':user.id, 'type_id':self.types[notify_type], 'foreign_id':foreign_id})

    def mark_as_read(self, receiver):
        return self.update({'receiver':receiver}, {'unread':0})

    def check(self, handler):
        if web.config._session.user_id is None:
            web.config._session.notifications = 0
        else:
            web.config._session.notifications = self.count_table({'receiver':web.config._session.user_id, 'unread':'1'})
        return handler()

########NEW FILE########
__FILENAME__ = notify_type_model
#  coding: utf8 
__metaclass__ = type

from models.model import *
class notify_type_model(model):
	
    def __init__(self):
        super(notify_type_model, self).__init__('notify_type')
########NEW FILE########
__FILENAME__ = post_model
#  coding: utf8
__metaclass__ = type
import web
from models.model import *
from models.comment_model import *
from models.post_thanks_model import *
from config.config import *

class post_model(model):
    
    def __init__(self):
        super(post_model, self).__init__('post')
        self.form = web.form.Form(
            web.form.Textarea('title', notnull, class_='mle', description=''),
            web.form.Textarea('content', notnull, class_='mle tall', description=''),
            web.form.Button('创建', class_='super normal button')
        )
    
    def add_view(self, post_id):
        super(post_model, self).query('UPDATE ' + self._tb + ' SET views = views + 1 WHERE id=' + str(post_id))
        
    def count_comment(self, post_id):
        super(post_model, self).query('update ' + self._tb + ' set comments = (select count(*) from ' + comment_model().table_name() + ' where ' + comment_model().table_name() + '.post_id = ' + str(post_id) + ') where id = ' + str(post_id))
    
    def count_thanks(self, post_id):
        super(post_model, self).query('update ' + self._tb + ' set thanks = (select count(*) from ' + post_thanks_model().table_name() + ' where ' + post_thanks_model().table_name() + '.post_id = ' + str(post_id) + ') where id = ' + str(post_id))

    def trends(self, limit = 20, offset = 0, node_id = None):
        select = [
            'p.id',
            'p.title',
            'p.last_update',
            'p.comments',
            'u.id AS post_user_id',
            'u.name AS post_user_name',
            'u.avatar AS post_user_avatar',
            'c.time',
            'c.content',
            'cu.name AS comment_user_name'
        ]

        from_ = [
            'post p',
            'JOIN user u ON p.user_id = u.id',
            'LEFT JOIN comment c ON c.post_id = p.id',
            'LEFT JOIN comment c1 ON c1.post_id = c.post_id AND c1.`time` > c.`time`'
            'LEFT JOIN user cu ON cu.id = c.user_id'
        ]

        where = [
            'c1.time IS NULL'
        ]

        if node_id is not None:
            where.append('p.node_id = $node_id')
        else:
            select.append('n.name AS node_name')
            select.append('n.display_name AS node_display_name')
            from_.append('JOIN node n ON n.id = p.node_id')
        sql = 'SELECT '
        sql += ', '.join(select)
        sql += ' FROM '
        sql += '\n'.join(from_)
        sql += '\n WHERE '
        sql += ' AND '.join(where)
        sql += '''
            GROUP  BY p.id
            ORDER  BY p.last_update DESC
            LIMIT  $offset, $limit
        '''
        return self.db.query(sql, vars = {'limit': limit, 'offset':offset, 'node_id': node_id})
########NEW FILE########
__FILENAME__ = post_thanks_model
# -- coding: utf8 --
__metaclass__ = type
import web
from models.model import *
from config.config import *

class post_thanks_model(model):
    
    def __init__(self):
        super(post_thanks_model, self).__init__('post_thanks')
########NEW FILE########
__FILENAME__ = site_model
# -- coding: utf8 --
__metaclass__ = type
import web
from models.model import *
from config.config import *

class site_model(model):

    def __init__(self):
        super(site_model, self).__init__('site')
        self.form = web.form.Form(
            web.form.Textbox('title', notnull, size=45, description="站点标题", class_='sl'),
            web.form.Textbox('site_url', notnull, size=45, description="站点url", class_='sl',post='<div class="sep5"></div><span class="fade">不需要加http://</span>'),
            web.form.Textbox('cookie_expires', notnull, size=45, description="cookie 过期时间（秒）", class_='sl'),
            web.form.Textarea('description', notnull, class_='mle tall', description='站点描述'),
            web.form.Button('保存', class_='super normal button')
        )

    def get_options(self):
        site = {}
        for site_option in self.get_all():
            site[site_option.key] = site_option.value
        return site

    def get_option(self, key):
        return self.get_one({'key':key}).value
########NEW FILE########
__FILENAME__ = user_meta_model
#  coding: utf8 
__metaclass__ = type
from models.model import *
from config.config import *

class user_meta_model(model):
    
    def __init__(self):
        super(user_meta_model, self).__init__('user_meta')
    
    def count_meta(self, condition):
        if condition is not None:
            return len(self.get_all(condition))
        else:
            return 0
########NEW FILE########
__FILENAME__ = user_model
#  coding: utf8 
__metaclass__ = type
import web
import base64
from models.model import *
from models.site_model import *
from config.config import *

class user_model(model):
    
    def __init__(self):
        super(user_model, self).__init__('user')
        self.login_form = web.form.Form(
            web.form.Textbox('name', notnull, size=30, description="用户名", class_='sl'),
            web.form.Password('password', notnull, size=30, description="密码", class_='sl'),
            web.form.Button('登录', class_='super normal button')
        )
        
        self.signup_form = web.form.Form(
            web.form.Textbox('name', web.form.regexp('^[a-z0-9]+$', ' 请使用小写和数字的组合'), vname, size=30, description="用户名", class_='sl', post='<div class="sep5"></div><span class="fade">请使用半角的 a-z 和数字 0-9 的组合，长度至少为3个字符</span>'),
            web.form.Textbox('email', vemail, size=30, description="邮箱", class_='sl', post='<div class="sep5"></div><span class="fade">请使用真实电子邮箱注册，我们不会将你的邮箱地址分享给任何人</span>'),
            web.form.Password('password', vpass, size=30, description="密码", class_='sl'),
            web.form.Button('注册', class_='super normal button')
        )
        
        self.setting_form = web.form.Form(
             web.form.Textbox('name', size=30, description="用户名", class_='sl', disabled='disabled'),
             web.form.Textbox('email', vemail, size=30, description="邮箱", class_='sl'),
             web.form.Textbox('signature', web.form.regexp(r".{0,100}$", ' 请不要超过100个字符'), size=30, description="签名", class_='sl'),
             web.form.Textbox('outsite_link', web.form.regexp(r".{0,200}$", ' 请不要超过200个字符'), size=30, description="主页", class_='sl'),
             web.form.Button('保存设置', class_='super normal button')
         )
        
        self.pass_form = web.form.Form(
            web.form.Password('origin_password', notnull, size=30, description="原密码", class_='sl'),
            web.form.Password('new_password', vpass, size=30, description="新密码", class_='sl'),
            web.form.Password('check_password', vpass, size=30, description="确认密码", class_='sl'),
            web.form.Button('修改密码', class_='super normal button'),
            validators = [web.form.Validator(" 新密码不一致", lambda i: i.new_password == i.check_password)]
        )
    
    def update_session(self, user_id):
        user = self.get_one({'id':user_id})
        web.config._session.user_id = user.id
        web.config._session.name = user.name
        web.config._session.avatar = user.avatar
        web.config._session.signature = user.signature
        web.config._session.node_favs = user.node_favs
        web.config._session.money = user.money
        web.config._session.posts = user.posts
        web.config._session.post_favs = user.post_favs
        web.config._session.user_favs = user.user_favs
    
    def set_avatar(self, filename, user_id):
        import Image
        import os
        path = 'static/avatar/'
        im = Image.open(path+'tmp/'+filename)
        size = im.size
        if size[0] > size[1]:
            crop_size = size[1]
            left = (size[0]-size[1])/2
            right = size[1] + left
            upper = 0
            lower = size[1]
        else:
            crop_size = size[0]
            left = 0
            right = size[0]
            upper = (size[1]-size[0])/2
            lower = size[0] + upper
        box = (left, upper, right, lower)
        region = im.crop(box)
        region.save(path+'tmp/'+filename)
        user = self.get_one({'id':user_id})
        try:
            os.makedirs(path+'big')
            os.makedirs(path+'normal')
            os.makedirs(path+'tiny')
            os.remove(path+'big/'+user.avatar)
            os.remove(path+'normal/'+user.avatar)
            os.remove(path+'tiny/'+user.avatar)
        except:
            pass
        im = Image.open(path+'tmp/'+filename)
        im.thumbnail((73, 73), Image.ANTIALIAS)
        im.save(path+'big/'+filename, quality = 100)
        im.thumbnail((48, 48), Image.ANTIALIAS)
        im.save(path+'normal/'+filename, quality = 100)
        im.thumbnail((24, 24), Image.ANTIALIAS)
        im.save(path+'tiny/'+filename, quality = 100)
        del im, region
        os.remove(path+'tmp/'+filename)
        self.update({'id':user_id}, {'avatar':filename})
        self.update_session(user_id)
    
    # cost 要带上符号
    def update_money(self, user_id, cost):
        sql = 'UPDATE ' + self._tb + ' SET money = money + ' + str(cost) +' WHERE id=' + str(user_id)
        super(user_model, self).query(sql)
        return self.get_one({'id':user_id}).money

    def auth_cookie(self, handler):
        try:
            if web.config._session.user_id is None:
                auth = web.cookies().get('auth')
                auth_list = base64.decodestring(auth).split('|')
                user = self.get_one({'id':auth_list[1], 'password':auth_list[0]})
                if user is None:
                    web.setcookie('auth', auth, -1)
                else:
                    self.update_session(user.id)
        except:
            pass
        return handler()

    def set_cookie(self, user_id):
        user = self.get_one({'id':user_id})
        auth = base64.encodestring(user.password+'|'+str(user.id))
        web.setcookie('auth', auth, int(site_model().get_option('cookie_expires')))

########NEW FILE########
