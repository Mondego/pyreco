__FILENAME__ = bind_wordpress
#-*- coding:utf-8 -*-

import sys
sys.path.append("../")

from past.store import mc
from past.model.user import UserAlias, User
from past.model.status import SyncTask, TaskQueue
from past import config


def bind(uid, feed_uri):
    user = User.get(uid)
    if not user:
        print 'no user'
        return
    ua = UserAlias.bind_to_exists_user(user, 
            config.OPENID_TYPE_DICT[config.OPENID_WORDPRESS], feed_uri)
    if not ua:
        print "no user alias"
    else:
        ##添加同步任务
        t = SyncTask.add(config.CATE_WORDPRESS_POST, user.id)
        t and TaskQueue.add(t.id, t.kind)
        ##删除confiration记录
        mc.delete("wordpress_bind:%s" %user.id)

if __name__ == "__main__":
    print sys.argv
    if len(sys.argv) == 3:
        bind(sys.argv[1], sys.argv[2])
    else:
        print "bind uid feed"
        

########NEW FILE########
__FILENAME__ = first_sync_timeline
#-*- coding:utf-8 -*-

import sys
sys.path.append("../")

import os
import time
import datetime
import commands

activate_this = '../env/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

import past
import jobs
from past.model.status import TaskQueue, SyncTask, Status
from past import config

if __name__ == "__main__":

    try:
        queue_ids = TaskQueue.get_all_ids()
        print '%s queue length: %s' %(datetime.datetime.now(),len(queue_ids)) 
        for qid in queue_ids:
            queue = TaskQueue.get(qid)
            if queue and queue.task_kind == config.K_SYNCTASK:
                print 'syncing task id:', queue.task_id
                sync_task = SyncTask.get(queue.task_id)
                if not sync_task:
                    continue

                ## 现在不同步豆瓣日记
                if str(sync_task.category) == str(config.CATE_DOUBAN_NOTE):
                    continue

                ## 同步wordpress rss
                if str(sync_task.category) == str(config.CATE_WORDPRESS_POST):
                    jobs.sync_wordpress(sync_task)
                    queue.remove()
                    continue

                max_sync_times = 0
                min_id = Status.get_min_origin_id(sync_task.category, sync_task.user_id)
                if sync_task:
                    while True:
                        if max_sync_times >= 20:
                            break
                        r = jobs.sync(sync_task, old=True)
                        new_min_id = Status.get_min_origin_id(sync_task.category, sync_task.user_id)
                        if r == 0 or new_min_id == min_id:
                            break
                        min_id = new_min_id
                        max_sync_times += 1
            queue.remove()
            time.sleep(1)
        time.sleep(1)
    except Exception, e:
        print e

########NEW FILE########
__FILENAME__ = generate_pdf
#-*- coding:utf-8 -*-

import sys
sys.path.append("../")

import time
import datetime
import calendar
import commands

activate_this = '../env/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

from past.utils.pdf import generate_pdf, get_pdf_filename, is_pdf_file_exists, get_pdf_full_filename
from past.model.user import User, UserAlias, PdfSettings
from past.model.status import Status
from past import config


def generate(user_id, date, order='asc'):
    try:
        uas = UserAlias.gets_by_user_id(user_id)
        if not uas:
            return

        start_date = datetime.datetime(date.year, date.month, 1)
        end_date = datetime.datetime(date.year, date.month,
                calendar.monthrange(date.year, date.month)[1], 23, 59, 59)

        pdf_filename = get_pdf_filename(user_id, date.strftime("%Y%m"), "")
        pdf_filename_compressed = get_pdf_filename(user_id, date.strftime("%Y%m"))
        print '----generate pdf:', start_date, ' to ', end_date, ' file is', pdf_filename

        if is_pdf_file_exists(pdf_filename_compressed):
            print '---- %s exists, so ignore...' % pdf_filename_compressed
            return

        status_ids = Status.get_ids_by_date(user_id, start_date, end_date)[:900]
        if order == 'asc':
            status_ids = status_ids[::-1]
        if not status_ids:
            print '----- status ids is none', status_ids
            return
        generate_pdf(pdf_filename, user_id, status_ids)

        if not is_pdf_file_exists(pdf_filename):
            print '----%s generate pdf for user:%s fail' % (datetime.datetime.now(), user_id)
        else:
            commands.getoutput("cd %s && tar -zcf %s %s && rm %s" %(config.PDF_FILE_DOWNLOAD_DIR, 
                    pdf_filename_compressed, pdf_filename, pdf_filename))
            print '----%s generate pdf for user:%s succ' % (datetime.datetime.now(), user_id)
    except Exception, e:
        import traceback
        print '%s %s' % (datetime.datetime.now(), traceback.format_exc())

def generate_pdf_by_user(user_id):
    user = User.get(user_id)
    if not user:
        return

    #XXX:暂时只生成2012年的(uid从98开始的用户)
    #XXX:暂时只生成2012年3月份的(uid从166开始的用户)
    start_date = Status.get_oldest_create_time(None, user_id)
    if not start_date:
        return
    now = datetime.datetime.now()
    now = datetime.datetime(now.year, now.month, now.day) - datetime.timedelta(days = calendar.monthrange(now.year, now.month)[1])

    d = start_date
    while d <= now:
        generate(user_id, d)

        days = calendar.monthrange(d.year, d.month)[1]
        d += datetime.timedelta(days=days)
        d = datetime.datetime(d.year, d.month, 1)


if __name__ == "__main__":
    for uid in PdfSettings.get_all_user_ids():
        #print '------begin generate pdf of user:', uid
        #generate_pdf_by_user(uid)

        now = datetime.datetime.now()
        last_mongth = datetime.datetime(now.year, now.month, now.day) \
                - datetime.timedelta(days = calendar.monthrange(now.year, now.month)[1])
        print '----- generate last month pdf of user:', last_mongth, uid
        generate(uid, last_mongth)

########NEW FILE########
__FILENAME__ = send_refresh_token_mail
#-*- coding:utf-8 -*-

import sys
sys.path.append("../")

activate_this = '../env/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

import time
from past.store import db_conn
from send_reminding import send_reconnect

if __name__ == "__main__":
    cursor = db_conn.execute("select max(id) from user")
    row = cursor.fetchone()
    cursor and cursor.close()
    max_uid = row and row[0]
    max_uid = int(max_uid)
    t = 0
    for uid in xrange(4,max_uid + 1):
    #for uid in xrange(4, 5):
        if t >= 100:
            t = 0
            time.sleep(5)
        send_reconnect(uid)
        time.sleep(1)
        t += 1
        sys.stdout.flush()


########NEW FILE########
__FILENAME__ = send_reminding
#-*- coding:utf-8 -*-

import sys
sys.path.append("../")

activate_this = '../env/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

import datetime
import time
import traceback

from past.utils import wrap_long_line, filters 
from past.utils.escape import clear_html_element
from past.utils.sendmail import send_mail
from past.model.status import get_status_ids_today_in_history, \
        get_status_ids_yesterday, Status
from past.model.user import User
from past.store import db_conn
from past import config
from past.api.error import OAuthTokenExpiredError

def send_today_in_history(user_id, now=None, include_yestorday=False):
    if not now:
        now = datetime.datetime.now()

    u = User.get(user_id)
    if not u:
        return

    setting = u.get_profile_item("email_remind_today_in_history")
    if setting == 'N':
        print '---user %s does not like to receive remind mail' % u.id
        return

    email = u.get_email()
    if not email:
        print '---- user %s no email' % u.id
        return
    
    history_ids = get_status_ids_today_in_history(u.id, now)
    status_of_today_in_history = Status.gets(history_ids)
    
    if include_yestorday:
        yesterday_ids = get_status_ids_yesterday(u.id, now) 
        status_of_yesterday = Status.gets(yesterday_ids)
    else:
        status_of_yesterday = None

    intros = [u.get_thirdparty_profile(x).get("intro") for x in config.OPENID_TYPE_DICT.values()]
    intros = filter(None, intros)
    
    d = {}
    for s in Status.gets(history_ids):
        t = s.create_time.strftime("%Y-%m-%d")
        if d.has_key(t):
            d[t].append(s)
        else:
            d[t] = [s]
    status_of_today_in_history = d
    from past.consts import YESTERDAY

    if not (status_of_today_in_history or (include_yestorday and status_of_yesterday)):
        print '--- user %s has no status in history' % u.id
        return

    from jinja2 import Environment, PackageLoader
    env = Environment(loader=PackageLoader('past', 'templates'))
    env.filters['wrap_long_line'] = wrap_long_line
    env.filters['nl2br'] = filters.nl2br
    env.filters['stream_time'] = filters.stream_time
    env.filters['clear_html_element'] = clear_html_element
    env.filters['isstr'] = lambda x: isinstance(x, basestring)
    t = env.get_template('mail.html')
    m = t.module


    if now:
        y = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        y = YESTERDAY
    html = m.status_in_past(status_of_yesterday, status_of_today_in_history, y, config, intros)
    html = html.encode("utf8")

    subject = '''thepast.me|整理自己的故事 %s''' % now.strftime("%Y-%m-%d")
    text = ''
    
    print '--- send reminding to %s %s' %(user_id, email)
    send_mail(["%s" % email], "thepast<help@thepast.me>", subject, text, html)

def send_yesterday(user_id, now=None):
    if not now:
        now = datetime.datetime.now()

    u = User.get(user_id)
    if not u:
        return

    setting = u.get_profile_item("email_remind_today_in_history")
    if setting == 'N':
        print '---user %s does not like to receive remind mail' % u.id
        return

    email = u.get_email()
    if not email:
        print '---- user %s no email' % u.id
        return
    
    yesterday_ids = get_status_ids_yesterday(u.id, now) 
    status_of_yesterday = Status.gets(yesterday_ids)

    intros = [u.get_thirdparty_profile(x).get("intro") for x in config.OPENID_TYPE_DICT.values()]
    intros = filter(None, intros)

    from past.consts import YESTERDAY

    if not status_of_yesterday:
        print '--- user %s has no status in yesterday' % u.id
        return

    from jinja2 import Environment, PackageLoader
    env = Environment(loader=PackageLoader('past', 'templates'))
    env.filters['wrap_long_line'] = wrap_long_line
    env.filters['nl2br'] = filters.nl2br
    env.filters['stream_time'] = filters.stream_time
    env.filters['clear_html_element'] = clear_html_element
    t = env.get_template('mail.html')
    m = t.module


    if now:
        y = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        y = YESTERDAY
    html = m.status_in_past(status_of_yesterday, None, y, config, intros)
    html = html.encode("utf8")

    subject = '''thepast.me|整理自己的故事 %s''' % now.strftime("%Y-%m-%d")
    text = ''
    
    print '--- send reminding to %s %s' %(user_id, email)
    send_mail(["%s" % email], "thepast<help@thepast.me>", subject, text, html)

def send_pdf(user_id):
    u = User.get(user_id)

    if not u:
        return

    setting = u.get_profile_item("email_remind_today_in_history")
    if setting == 'N':
        print '---user %s does not like to receive remind mail' % u.id
        return

    email = u.get_email()
    if not email:
        print '---- user %s no email' % u.id
        return

    subject = '''你在thepast.me上的timeline PDF版本'''
    text = '''Hi，感谢你使用thepast.me来聚合、管理、备份自己的timeline.

离线PDF版本现在可以下载了，请猛击 http://thepast.me/%s/pdf

http://thepast.me | 个人杂志计划
thanks''' % user_id
    
    print '--- send pdf file to %s %s' %(user_id, email)
    send_mail(["%s" % email], "thepast<help@thepast.me>", subject, text, "")

def send_reconnect(user_id):
    u = User.get(user_id)

    if not u:
        return

    setting = u.get_profile_item("email_remind_today_in_history")
    if setting == 'N':
        print '---user %s does not like to receive remind mail' % u.id
        return

    excps = [OAuthTokenExpiredError(user_id, x) for x in config.OPENID_TYPE_DICT.values()]
    expires_site = {}
    for e in excps:
        t = e.is_exception_exists()
        if t:
            expires_site[e.openid_type] = t

    if not expires_site:
        print '--- user %s has no expired connection' % u.id
        return
    else:
        print '--- user %s expired connection: %s' %(u.id, expires_site)

    email = u.get_email()
    if not email:
        print '---- user %s no email' % u.id
        return

    names = []
    reconnect_urls = []
    for x in expires_site.keys():
        names.append(config.OPENID_TYPE_NAME_DICT.get(x, ""))
        reconnect_urls.append("http://thepast.me/connect/%s" % config.OPENID_TYPE_DICT_REVERSE.get(x))

    subject = '''thepast.me授权过期提醒'''
    text = '''Hi，亲爱的%s，
    
感谢你使用thepast.me来整理自己的互联网印迹.
    
你在 %s 对thepast的授权过期了，影响到您的个人历史数据同步，

请依次访问下面的链接，重新授权：）

%s



如果你不愿意接收此类邮件，那么请到 http://thepast.me/settings 设置：）
---
http://thepast.me 
thanks''' % (u.name.encode("utf8"), ", ".join(names).encode("utf8"), "\n".join(reconnect_urls))

    print '--- send reconnections to %s %s' %(user_id, email)
    send_mail(["%s" % email], "thepast<help@thepast.me>", subject, text, "")


if __name__ == '__main__':
    cursor = db_conn.execute("select max(id) from user")
    row = cursor.fetchone()
    cursor and cursor.close()
    max_uid = row and row[0]
    max_uid = int(max_uid)
    t = 0
    for uid in xrange(4,max_uid + 1):
        if t >= 100:
            t = 0
            time.sleep(5)
        try:
            send_today_in_history(uid)
        except:
            print traceback.format_exc()
        time.sleep(1)
        t += 1


########NEW FILE########
__FILENAME__ = sync_timeline
#-*- coding:utf-8 -*-

import sys
sys.path.append("../")

import os
import time
import commands

activate_this = '../env/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

if __name__ == "__main__":
    for c in [100, 200, 300, 400, 500, 700, 702, 703, 704, 800,]:
        for t in ['old', 'new']:
            print commands.getoutput("../env/bin/python ../jobs.py -t %s -c %s -n 1" %(t, c))

########NEW FILE########
__FILENAME__ = jobs
#-*- coding:utf-8 -*-

import datetime
import time
from optparse import OptionParser

from past import config
from past.utils.escape import json_encode, json_decode
from past.utils.logger import logging
from past.utils import datetime2timestamp

from past.api.douban import Douban
from past.api.sina import SinaWeibo
from past.api.qqweibo import QQWeibo
from past.api.renren import Renren
from past.api.instagram import Instagram
from past.api.twitter import TwitterOAuth1
from past.api.wordpress import Wordpress

from past.corelib import category2provider
from past.model.status import Status, SyncTask
from past.model.user import User, UserAlias, OAuth2Token

log = logging.getLogger(__file__)

def sync(t, old=False):
    if not t:
        print 'no such task'
        return 0
    log.info("the sync task is :%s" % t)
    try:
        alias = None
        provider = category2provider(t.category)

        alias = UserAlias.get_by_user_and_type(t.user_id,
                config.OPENID_TYPE_DICT[provider])
        if not alias:
            log.warn("no alias...")
            return 0

        token = OAuth2Token.get(alias.id)
        if not token:
            log.warn("no access token, break...")
            return 0
        
        client = None
        if provider == config.OPENID_DOUBAN:
            client = Douban.get_client(alias.user_id)
        elif provider == config.OPENID_SINA:
            client = SinaWeibo.get_client(alias.user_id)
        elif provider == config.OPENID_TWITTER:
            client = TwitterOAuth1.get_client(alias.user_id)
        elif provider == config.OPENID_QQ:
            client = QQWeibo.get_client(alias.user_id)
        elif provider == config.OPENID_RENREN:
            client = Renren.get_client(alias.user_id)
        elif provider == config.OPENID_INSTAGRAM:
            client = Instagram.get_client(alias.user_id)
        if not client:
            log.warn("get client fail, break...")
            return 0

        if t.category == config.CATE_DOUBAN_NOTE:
            if old:
                start = Status.get_count_by_cate(t.category, t.user_id)
            else:
                start = 0
            note_list = client.get_notes(start, 50)
            if note_list:
                for x in note_list:
                    Status.add_from_obj(t.user_id, x, json_encode(x.get_data()))
                return len(note_list)
        elif t.category == config.CATE_DOUBAN_MINIBLOG:
            if old:
                start = Status.get_count_by_cate(t.category, t.user_id)
            else:
                start = 0
            miniblog_list = client.get_miniblogs(start, 50)
            if miniblog_list:
                for x in miniblog_list:
                    Status.add_from_obj(t.user_id, x, json_encode(x.get_data()))
                return len(miniblog_list)
        elif t.category == config.CATE_DOUBAN_STATUS:
            origin_min_id = Status.get_min_origin_id(t.category, t.user_id)
            if old:
                log.info("will get douban status order than %s..." % origin_min_id)
                status_list = client.get_timeline(until_id=origin_min_id)
            else:
                log.info("will get douban status newer than %s..." % origin_min_id)
                status_list = client.get_timeline(since_id=origin_min_id, count=20)
            if status_list:
                log.info("get douban status succ, len is %s" % len(status_list))
                for x in status_list:
                    Status.add_from_obj(t.user_id, x, json_encode(x.get_data()))
                
        elif t.category == config.CATE_SINA_STATUS:
            origin_min_id = Status.get_min_origin_id(t.category, t.user_id) #means the earliest id
            origin_max_id = Status.get_max_origin_id(t.category, t.user_id) #meas the latest id
            if old:
                log.info("will get sinaweibo order than %s..." % origin_min_id)
                status_list = client.get_timeline(until_id=origin_min_id)
                ## 如果根据max_id拿不到数据，那么根据page再fetch一次或者until_id - 1
                if status_list and len(status_list) < 20 and origin_min_id is not None:
                    log.info("again will get sinaweibo order than %s..." % (int(origin_min_id)-1))
                    status_list = client.get_timeline(until_id=int(origin_min_id)-1)
            else:
                log.info("will get sinaweibo newer than %s..." % origin_max_id)
                status_list = client.get_timeline(since_id=origin_max_id, count=50)
            if status_list:
                log.info("get sinaweibo succ, len is %s" % len(status_list))
                for x in status_list:
                    Status.add_from_obj(t.user_id, x, json_encode(x.get_data()))
                return len(status_list)
        elif t.category == config.CATE_TWITTER_STATUS:
            origin_min_id = Status.get_min_origin_id(t.category, t.user_id)
            origin_max_id = Status.get_max_origin_id(t.category, t.user_id)
            if old:
                log.info("will get tweets order than %s..." % origin_min_id)
                status_list = client.get_timeline(max_id=origin_min_id)
            else:
                log.info("will get tweets newer than %s..." % origin_max_id)
                status_list = client.get_timeline(since_id=origin_max_id, count=50)
            if status_list:
                log.info("get tweets succ, len is %s" % len(status_list))
                for x in status_list:
                    Status.add_from_obj(t.user_id, x, json_encode(x.get_data()))
                return len(status_list)
        elif t.category == config.CATE_QQWEIBO_STATUS:
            if old:
                oldest_create_time = Status.get_oldest_create_time(t.category, t.user_id)
                log.info("will get qqweibo order than %s" % oldest_create_time)
                if oldest_create_time is not None:
                    oldest_create_time = datetime2timestamp(oldest_create_time)
                status_list = client.get_old_timeline(oldest_create_time, reqnum=200)
            else:
                log.info("will get qqweibo new timeline")
                status_list = client.get_new_timeline(reqnum=20)
            if status_list:
                log.info("get qqweibo succ, result length is:%s" % len(status_list))
                for x in status_list:
                    Status.add_from_obj(t.user_id, x, json_encode(x.get_data()))
                return len(status_list)
        elif t.category == config.CATE_RENREN_STATUS:
            if old:
                count = 100
                total_count = Status.get_count_by_cate(t.category, t.user_id)
                page = int(total_count / count) + 1
                log.info("will get older renren status, page=%s, count=%s" %(page, count))
                status_list = client.get_timeline(page, count)
            else:
                count = 20
                page = 1
                log.info("will get newest renren status, page=%s, count=%s" %(page, count))
                status_list = client.get_timeline(page, count)
            if status_list:
                log.info("get renren status succ, result length is:%s" % len(status_list))
                for x in status_list:
                    Status.add_from_obj(t.user_id, x, json_encode(x.get_data()))
                return len(status_list)
        elif t.category == config.CATE_RENREN_BLOG:
            if old:
                count = 50
                total_count = Status.get_count_by_cate(t.category, t.user_id)
                page = int(total_count / count) + 1
                log.info("will get older renren blog, page=%s, count=%s" %(page, count))
                blogs = client.get_blogs(page, count)
            else:
                count = 20
                page = 1
                log.info("will get newest renren blog, page=%s, count=%s" %(page, count))
                blogs = client.get_blogs(page, count)
            if blogs:
                uid = blogs.get("uid")
                blog_ids = filter(None, [v.get("id") for v in blogs.get("blogs", [])])
                log.info("get renren blog ids succ, result length is:%s" % len(blog_ids))
                for blog_id in blog_ids:
                    blog = client.get_blog(blog_id, uid)
                    if blog:
                        Status.add_from_obj(t.user_id, blog, json_encode(blog.get_data()))
                return len(blog_ids)
        elif t.category == config.CATE_RENREN_ALBUM:
            status_list = client.get_albums()
            if status_list:
                log.info("get renren album succ, result length is:%s" % len(status_list))
                for x in status_list:
                    Status.add_from_obj(t.user_id, x, json_encode(x.get_data()))
                return len(status_list)
        elif t.category == config.CATE_RENREN_PHOTO:
            albums_ids = Status.get_ids(user_id=t.user_id, limit=1000, cate=config.CATE_RENREN_ALBUM)
            albums = Status.gets(albums_ids)
            if not albums:
                return 0
            for x in albums:
                d = x.get_data()
                if not d:
                    continue
                aid = d.get_origin_id()
                size = int(d.get_size())
                count = 50
                for i in xrange(1, size/count + 2):
                    status_list = client.get_photos(aid, i, count)
                    if status_list:
                        log.info("get renren photo of album %s succ, result length is:%s" \
                                % (aid, len(status_list)))
                        for x in status_list:
                            Status.add_from_obj(t.user_id, x, json_encode(x.get_data()))

        elif t.category == config.CATE_INSTAGRAM_STATUS:
            origin_min_id = Status.get_min_origin_id(t.category, t.user_id) #means the earliest id
            origin_max_id = Status.get_max_origin_id(t.category, t.user_id) #means the latest id
            if old:
                log.info("will get instagram earlier than %s..." % origin_min_id)
                status_list = client.get_timeline(max_id=origin_min_id)
            else:
                log.info("will get instagram later than %s..." % origin_max_id)
                status_list = client.get_timeline(min_id=origin_max_id, count=50)
            if status_list:
                log.info("get instagram succ, len is %s" % len(status_list))
                for x in status_list:
                    Status.add_from_obj(t.user_id, x, json_encode(x.get_data()))
                return len(status_list)
    except Exception, e:
        print "---sync_exception_catched:", e
    return 0

def sync_wordpress(t, refresh=True):
    if not t:
        log.warning('no_wordpress_sync_task')
        return

    #一个人可以有多个wordpress的rss源地址
    rs = UserAlias.gets_by_user_id(t.user_id)
    uas = []
    for x in rs:
        if x.type == config.OPENID_TYPE_DICT[config.OPENID_WORDPRESS]:
            uas.append(x)
    if not uas:
        log.warning('no_wordpress_alias')
        return
    for ua in uas:
        try:
            client = Wordpress(ua.alias)
            rs = client.get_feeds(refresh)
            if rs:
                log.info("get wordpress succ, result length is:%s" % len(rs))
                for x in rs:
                    Status.add_from_obj(t.user_id, x, json_encode(x.get_data()))
                return 
        except Exception, e:
            print "---sync_exception_catched:", e

def sync_helper(cate,old=False):
    log.info("%s syncing old %s... cate=%s" % (datetime.datetime.now(), old, cate))
    ids = SyncTask.get_ids()
    task_list = SyncTask.gets(ids)
    if cate:
        task_list = [x for x in task_list if x.category==cate]
    if not task_list:
        log.warn("no task list, so sleep 10s and continue...")
        return 
    
    log.info("task_list length is %s" % len(task_list))
    for t in task_list:
        try:
            if t.category == config.CATE_WORDPRESS_POST:
                sync_wordpress(t)
            else:
                sync(t, old)
        except Exception, e:
            import traceback
            print "%s %s" % (datetime.datetime.now(), traceback.format_exc())

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-t", "--time", dest="time", help="sync old or new msg")
    parser.add_option("-c", "--cate", type="int", dest="cate", help="category")
    parser.add_option("-n", "--num", type="int", dest="num", help="run how many times")
    (options, args) = parser.parse_args()
    
    if not options.time:
        options.time = 'new'
    if options.time not in ['new', 'old']:
        options.time = 'new'
    
    old = True if options.time=='old' else False
    cate = options.cate if options.cate else None
    num = options.num if options.num else 1
    for i in xrange(num):
        sync_helper(cate, old)


##python jobs.py -t old -c 200 -n 2

########NEW FILE########
__FILENAME__ = douban
# -*- coding: utf-8 -*-

import urllib
import urlparse
from past import config
from past.utils.logger import logging
from past.utils.escape import json_decode
from past.utils import httplib2_request

from past.model.user import User, UserAlias, OAuth2Token
from past.model.data import DoubanUser
from past.model.data import DoubanNoteData, DoubanStatusData, DoubanMiniBlogData

from .oauth2 import OAuth2
from .error import OAuthError, OAuthLoginError, OAuthTokenExpiredError

log = logging.getLogger(__file__)

class Douban(OAuth2):

    authorize_uri = 'https://www.douban.com/service/auth2/auth'
    access_token_uri = 'https://www.douban.com/service/auth2/token' 
    api_host = "https://api.douban.com"

    def __init__(self, alias=None, access_token=None, refresh_token=None):
        d = config.APIKEY_DICT[config.OPENID_DOUBAN]
        super(Douban, self).__init__(provider = config.OPENID_DOUBAN, 
                apikey = d["key"], 
                apikey_secret = d["secret"], 
                redirect_uri = d["redirect_uri"],
                alias=alias, 
                access_token=access_token, 
                refresh_token=refresh_token)

    @classmethod
    def get_client(cls, user_id):
        alias = UserAlias.get_by_user_and_type(user_id, 
                config.OPENID_TYPE_DICT[config.OPENID_DOUBAN])
        if not alias:
            return None

        token = OAuth2Token.get(alias.id)
        if not token:
            return None

        return cls(alias.alias, token.access_token, token.refresh_token)

    def check_result(self, uri, resp, content):
        user_id = self.user_alias and self.user_alias.user_id or None
        excp = OAuthTokenExpiredError(user_id,
                config.OPENID_TYPE_DICT[config.OPENID_DOUBAN], content)
        jdata = json_decode(content) if content else None
        if str(resp.status) == "200":
            excp.clear_the_profile()
            return jdata

        log.warning("get %s fail, status code=%s, msg=%s. go to refresh token" \
            % (uri, resp.status, content))
        if jdata and isinstance(jdata, dict):
            error_code = jdata.get("code") 
            if str(error_code) == "103" or str(error_code) == "123":
                excp.set_the_profile()
                raise excp
            elif str(error_code) == "106" and self.user_alias:
                try:
                    new_tokens = super(Douban, self).refresh_tokens()
                    if new_tokens and isinstance(new_tokens, dict):
                        OAuth2Token.add(self.user_alias.id, 
                                new_tokens.get("access_token"), 
                                new_tokens.get("refresh_token"))
                        excp.clear_the_profile()
                except OAuthError, e:
                    log.warn("refresh token fail: %s" % e)
                    excp.set_the_profile()
                    raise e

    def get(self, url, extra_dict=None):
        uri = urlparse.urljoin(self.api_host, url)
        if extra_dict is None:
            extra_dict = {}
        extra_dict["alt"] = "json"

        if extra_dict:
            qs = urllib.urlencode(extra_dict)
            if "?" in uri:
                uri = "%s&%s" % (uri, qs)
            else:
                uri = "%s?%s" % (uri, qs)
        headers = {"Authorization": "Bearer %s" % self.access_token}     
        log.info('getting %s...' % uri)

        resp, content = httplib2_request(uri, "GET", headers=headers)
        return self.check_result(uri, resp, content)

    def post(self, url, body, headers=None):
        uri = urlparse.urljoin(self.api_host, url)
        if headers is not None:
            headers.update({"Authorization": "Bearer %s" % self.access_token})
        else:
            headers = {"Authorization": "Bearer %s" % self.access_token}     

        resp, content = httplib2_request(uri, "POST", body=body, headers=headers)
        return self.check_result(uri, resp, content)


    def get_user_info(self, uid="@me"):
        uid = uid or "@me"
        api = "/people/%s" % uid
        jdata = self.get(api)
        if jdata and isinstance(jdata, dict):
            return DoubanUser(jdata)

    def get_me2(self):
        return self.get("/shuo/users/%s" % self.alias)

    def get_note(self, note_id):
        return self.get("/note/%s" % note_id)

    def get_timeline(self, since_id=None, until_id=None, count=200, user_id=None):
        user_id = user_id or self.alias
        qs = {}
        qs['count'] = count
        if since_id is not None:
            qs['since_id'] = since_id
        if until_id is not None:
            qs['until_id'] = until_id
        qs = urllib.urlencode(qs)
        jdata = self.get("/shuo/v2/statuses/user_timeline/%s?%s" % (user_id, qs))
        if jdata and isinstance(jdata, list):
            return [DoubanStatusData(c) for c in jdata]

    def get_home_timeline(self, since_id=None, until_id=None, count=200):
        qs = {}
        qs['count'] = count
        if since_id is not None:
            qs['since_id'] = since_id
        if until_id is not None:
            qs['until_id'] = until_id
        qs = urllib.urlencode(qs)
        jdata = self.get("/shuo/v2/statuses/home_timeline?%s" % qs)
        if jdata and isinstance(jdata, list):
            return [DoubanStatusData(c) for c in jdata]

    # 发广播，只限文本
    def post_status(self, text, attach=None):
        qs = {}
        qs["text"] = text
        if attach is not None:
            qs["attachments"] = attach
        qs = urllib.urlencode(qs)
        return self.post("/shuo/statuses/", body=qs)

    def post_status_with_image(self, text, image_file):
        from past.utils import encode_multipart_data
        d = {"text": text}
        f = {"image" : image_file}
        body, headers = encode_multipart_data(d, f)
        return self.post("/shuo/statuses/", body=body, headers=headers)
        
    #FIXED
    def get_notes(self, start, count):
        jdata = self.get("/people/%s/notes" % self.alias, 
                {"start-index": start, "max-results": count})
        if jdata and isinstance(jdata, dict):
            contents = jdata.get("entry", [])
            if contents:
                print '------get douban note,len is:', len(contents)
                return [DoubanNoteData(c) for c in contents]
    
    #FIXED
    def get_miniblogs(self, start, count):
        jdata = self.get("/people/%s/miniblog" % self.alias,
                {"start-index": start, "max-results": count})
        if jdata and isinstance(jdata, dict):
            contents = jdata.get("entry",[])
            if contents:
                print '------get douban miniblog,len is:', len(contents)
                return [DoubanMiniBlogData(c) for c in contents]

    def get_albums(self, start, count):
        return self.get("/people/%s/albums" % self.alias, 
                {"start-index": start, "max-results": count})
        
    def get_album(self, album_id):
        return self.get("/album/%s" % album_id)

    def get_album_photos(self, album_id):
        return self.get("/album/%s/photos" % album_id)

    def get_photo(self, photo_id):
        return self.get("/photo/%s" % photo_id)
    

########NEW FILE########
__FILENAME__ = error
# -*- coding: utf-8 -*-
import datetime
from tweepy.error import TweepError
from past.model.user import User

class OAuthError(Exception):
    def __init__(self, msg_type, user_id, openid_type, msg):
        self.msg_type = msg_type
        self.user_id = user_id
        self.openid_type = openid_type
        self.msg = msg

    def __str__(self):
        return "OAuthError: user:%s, openid_type:%s, %s, %s" % \
            (self.user_id, self.openid_type, self.msg_type, self.msg)
    __repr__ = __str__

    def set_the_profile(self, flush=False):
        if self.user_id:
            u = User.get(self.user_id)
            if u:
                if flush:
                    u.set_thirdparty_profile_item(self.openid_type, self.msg_type, datetime.datetime.now())
                else:
                    p = u.get_thirdparty_profile(self.openid_type)
                    t = p and p.get(self.msg_type)
                    u.set_thirdparty_profile_item(self.openid_type, self.msg_type, t or datetime.datetime.now())

    def clear_the_profile(self):
        if self.user_id:
            u = User.get(self.user_id)
            if u:
                u.set_thirdparty_profile_item(self.openid_type, self.msg_type, "")
    
    def is_exception_exists(self):
        if self.user_id:
            u = User.get(self.user_id)
            p = u and u.get_thirdparty_profile(self.openid_type)
            return p and p.get(self.msg_type)


class OAuthTokenExpiredError(OAuthError):
    TYPE = "expired"
    def __init__(self, user_id=None, openid_type=None, msg=""):
        super(OAuthTokenExpiredError, self).__init__(
            OAuthTokenExpiredError.TYPE, user_id, openid_type, msg)

class OAuthAccessError(OAuthError):
    TYPE = "access_error"
    def __init__(self, user_id=None, openid_type=None, msg=""):
        super(OAuthAccessError, self).__init__(
            OAuthTokenExpiredError.TYPE, user_id, openid_type, msg)


class OAuthLoginError(OAuthError):
    TYPE = "login"
    def __init__(self, user_id=None, openid_type=None, msg=""):
        if isinstance(msg, TweepError):
            msg = "%s:%s" %(msg.reason, msg.response) 
        super(OAuthLoginError, self).__init__(
            OAuthLoginError.TYPE, user_id, openid_type, msg)


########NEW FILE########
__FILENAME__ = instagram
# -*- coding: utf-8 -*-

import urllib
import urlparse
from past import config
from past.utils.logger import logging
from past.utils.escape import json_decode
from past.utils import httplib2_request

from past.model.user import User, UserAlias, OAuth2Token
from past.model.data import InstagramUser
from past.model.data import InstagramStatusData 

from .oauth2 import OAuth2
from .error import OAuthLoginError, OAuthTokenExpiredError

log = logging.getLogger(__file__)

class Instagram(OAuth2):

    authorize_uri = 'https://api.instagram.com/oauth/authorize/'
    access_token_uri = 'https://api.instagram.com/oauth/access_token' 
    api_host = 'https://api.instagram.com'

    def __init__(self, alias=None, access_token=None, refresh_token=None, api_version="v1"):
        self.api_version = api_version
        d = config.APIKEY_DICT[config.OPENID_INSTAGRAM]
        super(Instagram, self).__init__(provider = config.OPENID_INSTAGRAM, 
                apikey = d["key"], 
                apikey_secret = d["secret"], 
                redirect_uri = d["redirect_uri"],
                scope = "basic likes comments relationships",
                alias=alias, 
                access_token=access_token, 
                refresh_token=refresh_token)

    @classmethod
    def get_client(cls, user_id):
        alias = UserAlias.get_by_user_and_type(user_id, 
                config.OPENID_TYPE_DICT[config.OPENID_INSTAGRAM])
        if not alias:
            return None

        token = OAuth2Token.get(alias.id)
        if not token:
            return None

        return cls(alias.alias, token.access_token, token.refresh_token)

    def _request(self, api, method="GET", extra_dict=None):
        uri = urlparse.urljoin(self.api_host, api)
        if extra_dict is None:
            extra_dict = {}

        params = {
            "access_token": self.access_token,
        }
        params.update(extra_dict)
        qs = urllib.urlencode(params)
        uri = "%s?%s" % (uri, qs)

        log.info('getting %s...' % uri)
        resp, content = httplib2_request(uri, method)
        if resp.status == 200:
            return json_decode(content) if content else None
        else:
            log.warn("get %s fail, status code=%s, msg=%s" \
                    % (uri, resp.status, content))

    def get_user_info(self, uid=None):
        uid = uid or self.user_alias.alias or "self"
        jdata = self._request("/v1/users/%s" % uid, "GET")
        if jdata and isinstance(jdata, dict):
            return InstagramUser(jdata.get("data"))

    def get_timeline(self, uid=None, min_id=None, max_id=None, count=100):
        d = {}
        d["count"] = count
        if min_id:
            d["min_id"] = min_id
        if max_id:
            d["max_id"] = max_id
        uid = uid or self.alias or "self"

        contents = self._request("/v1/users/%s/media/recent" %uid, "GET", d)
        ##debug
        if contents and isinstance(contents, dict):
            code = str(contents.get("meta", {}).get("code", ""))
            if code == "200":
                data = contents.get("data", [])
                print '---get instagram feed succ, result length is:', len(data)
                return [InstagramStatusData(c) for c in data]

    def get_home_timeline(self, uid=None, min_id=None, max_id=None, count=100):
        d = {}
        d["count"] = count
        if min_id:
            d["min_id"] = min_id
        if max_id:
            d["max_id"] = max_id
        uid = uid or self.alias or "self"

        contents = self._request("/v1/users/%s/feed" %uid, "GET", d)
        ##debug
        if contents and isinstance(contents, dict):
            code = str(contents.get("meta", {}).get("code", ""))
            if code == "200":
                data = contents.get("data", [])
                print '---get instagram home_timeline succ, result length is:', len(data)
                return [InstagramStatusData(c) for c in data]

########NEW FILE########
__FILENAME__ = oauth2
# -*- coding: utf-8 -*-

import urllib
from past import config
from past.model.user import UserAlias
from past.utils.escape import json_decode
from past.utils import httplib2_request

from .error import OAuthLoginError

class OAuth2(object):

    authorize_uri = ''
    access_token_uri = ''
    api_host = ''
    
    def __init__(self, provider=None, apikey=None, apikey_secret=None, redirect_uri=None, 
            scope=None, state=None, display=None, 
            alias=None, access_token=None, refresh_token=None):

        self.provider = provider
        self.apikey = apikey
        self.apikey_secret = apikey_secret
        self.redirect_uri = redirect_uri

        self.scope = scope
        self.state = state
        self.display = display

        self.alias = alias
        if alias:
            self.user_alias = UserAlias.get(
                    config.OPENID_TYPE_DICT[provider], alias)
        else:
            self.user_alias = None
        self.access_token = access_token
        self.refresh_token = refresh_token

    def __repr__(self):
        return '<provider=%s, alias=%s, access_token=%s, refresh_token=%s, \
                api_host=%s>' % (self.provider, self.alias, self.access_token, 
                self.refresh_token, self.api_host)
    __str__ = __repr__

    def login(self):
        qs = {
            'client_id'     : self.apikey,
            'response_type' : 'code',
            'redirect_uri'  : self.redirect_uri,
        }
        if self.display:
            qs['display'] = self.display
        if self.scope:
            qs['scope'] = self.scope
        if self.state:
            qs['state'] = self.state
            
        qs = urllib.urlencode(qs)
        uri = '%s?%s' %(self.authorize_uri, qs)

        return uri

    def get_access_token(self, authorization_code):
        qs = {
            "client_id": self.apikey,
            "client_secret": self.apikey_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
            "code": authorization_code,
        }
        qs = urllib.urlencode(qs)
        resp, content = httplib2_request(self.access_token_uri, "POST", body=qs)
        excp = OAuthLoginError(msg='get_access_token, status=%s,reason=%s,content=%s' \
                %(resp.status, resp.reason, content))
        if resp.status != 200:
            raise excp

        jdata = json_decode(content) if content else None
        return jdata
        

    def refresh_tokens(self):
        qs = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.apikey,
            "client_secret": self.apikey_secret,
            "redirect_uri": self.redirect_uri,
        }
        resp, content = httplib2_request(self.access_token_uri, "POST", 
            body=urllib.urlencode(qs))
        excp = OAuthLoginError(self.user_alias.user_id, self.provider, 
                'refresh_tokens, status=%s,reason=%s,content=%s' \
                %(resp.status, resp.reason, content))
        if resp.status != 200:
            raise excp

        jdata = json_decode(content) if content else None
        return jdata

    def set_token(self, access_token, refresh_token):
        self.access_token = access_token
        self.refresh_token = refresh_token

    def get_user_info(self, uid):
        raise NotImplementedError


########NEW FILE########
__FILENAME__ = qqweibo
# -*- coding: utf-8 -*-
import time
import hashlib
import urllib
import hmac
import binascii
import urlparse
from past import config
from past.utils import randbytes
from past.utils.logger import logging
from past.utils.escape import json_decode, json_encode
from past.utils import httplib2_request

from past.model.user import User, UserAlias, OAuth2Token
from past.model.data import QQWeiboUser
from past.model.data import QQWeiboStatusData

from .error import OAuthError, OAuthLoginError, OAuthTokenExpiredError

log = logging.getLogger(__file__)

##腾讯微博使用的是Oauth1.0授权
class QQWeibo(object):
    provider = config.OPENID_QQ

    request_token_uri = "https://open.t.qq.com/cgi-bin/request_token"
    authorize_uri = "https://open.t.qq.com/cgi-bin/authorize"
    access_token_uri = "https://open.t.qq.com/cgi-bin/access_token"
    api_uri = "http://open.t.qq.com/api"

    def __init__(self, alias=None, 
            apikey=None, apikey_secret=None, redirect_uri=None, 
            token=None, token_secret=None, openid=None, openkey=None):

        self.consumer_key = apikey or config.APIKEY_DICT[config.OPENID_QQ]['key']
        self.consumer_secret = apikey_secret or config.APIKEY_DICT[config.OPENID_QQ]['secret']
        self.callback = redirect_uri or config.APIKEY_DICT[config.OPENID_QQ]['redirect_uri']

        self.token = token
        self.token_secret = token_secret
        #XXX:no use?
        self.openid = openid
        self.openkey = openkey

        self.alias=alias
        if alias:
            self.user_alias = UserAlias.get(
                    config.OPENID_TYPE_DICT[config.OPENID_QQ], alias)
        else:
            self.user_alias = None

    def __repr__(self):
        return "<QQWeibo consumer_key=%s, consumer_secret=%s, token=%s, token_secret=%s>" \
            % (self.consumer_key, self.consumer_secret, self.token, self.token_secret)
    __str__ = __repr__

    def save_request_token_to_session(self, session_):
        t = {"key": self.token,
            "secret": self.token_secret,}
        session_['request_token'] = json_encode(t)

    def get_request_token_from_session(self, session_, delete=True):
        t = session_.get("request_token")
        token = json_decode(t) if t else {}
        if delete:
            self.delete_request_token_from_session(session_)
        return token

    def delete_request_token_from_session(self, session_):
        session_.pop("request_token", None)

    def set_token(self, token, token_secret):
        self.token = token
        self.token_secret = token_secret

    ##get unauthorized request_token
    def get_request_token(self):
        ##返回结果
        ##oauth_token=9bae21d3bbe2407da94a4c4e4355cfcb&oauth_token_secret=128b87904122d43cde6b02962d8eeea6&oauth_callback_confirmed=true
        uri = self.__class__.request_token_uri
        try:
            r = self.GET(uri, {'oauth_callback':self.callback})
            qs = urlparse.parse_qs(r)
            self.set_token(qs.get('oauth_token')[0], qs.get('oauth_token_secret')[0])

            return (self.token, self.token_secret)
        except OAuthError, e:
            print e
        except AttributeError, e:
            print e
            
    ##authorize the request_token
    def authorize_token(self):
        ##用户授权之后会返回如下结果
        ##http://thepast.me/connect/qq/callback
        ##?oauth_token=xxx&oauth_verifier=468092&openid=xxx&openkey=xxx
        uri = "%s?oauth_token=%s" % (self.__class__.authorize_uri, self.token)
        return uri
    
    ## 为了和其他几个接口保持一致
    def login(self):
        self.get_request_token()
        return self.authorize_token()
    
    ##get access_token use authorized_code
    def get_access_token(self, oauth_verifier):
        uri = self.__class__.access_token_uri
        qs = {
            "oauth_token": self.token,
            "oauth_verifier": oauth_verifier,
        }
        
        r = self.GET(uri, qs)
        d = urlparse.parse_qs(r)
        self.token = d['oauth_token'][0]
        self.token_secret = d['oauth_token_secret'][0]

        return (self.token, self.token_secret)

    @classmethod                                                                   
    def get_client(cls, user_id):                                                  
        alias = UserAlias.get_by_user_and_type(user_id,                            
                config.OPENID_TYPE_DICT[config.OPENID_QQ])                       
        if not alias:                                                              
            return None                                                            

        token = OAuth2Token.get(alias.id)
        if not token:
            return None
                                                                                   
        return cls(alias=alias.alias, token=token.access_token, token_secret=token.refresh_token)
    
    def get_user_info(self):
        jdata = self.access_resource2("GET", "/user/info", {"format":"json"})
        if jdata and isinstance(jdata, dict):
            return QQWeiboUser(jdata)

    ##使用access_token访问受保护资源，该方法中会自动传递oauth_token参数
    ##params为dict，是需要传递的参数, body 和 headers不加入签名
    def access_resource(self, method, api, params, file_params=None):
        uri = self.__class__.api_uri + api

        if params:
            params['oauth_token'] = self.token
        else:
            params = {'oauth2_token':self.token,}
        log.info("accesss qq resource: %s, %s" %(uri, params))
        if method == "GET":
            return self.GET(uri, params)
        if method == "POST":
            return self.POST(uri, params, file_params)

    def GET(self, uri, params):
        return self._request("GET", uri, params, None)

    def POST(self, uri, params, file_params):
        return self._request("POST", uri, params, file_params)

    def _request(self, method, uri, kw, file_params):
        raw_qs, qs = QQWeibo.sign(method, uri, self.consumer_key, 
                self.consumer_secret, self.token_secret, **kw)
        if method == "GET":
            full_uri = "%s?%s" % (uri, qs)
            resp, content = httplib2_request(full_uri, method)
        else:
            if file_params:
                from past.utils import encode_multipart_data
                body, headers = encode_multipart_data(raw_qs, file_params)
            else:
                body = qs
                headers = None
            resp, content = httplib2_request(uri, method, body, headers=headers)
            
        log.debug("---qq check result, status: %s, resp: %s, content: %s" %(resp.status, resp, content))
        if resp.status != 200:
            raise OAuthLoginError(msg='get_unauthorized_request_token fail, status=%s:reason=%s:content=%s' \
                    %(resp.status, resp.reason, content))
        return content
        
    @classmethod
    def sign(cls, method, uri, consumer_key, consumer_secret, token_secret, **kw):
        
        part1 = method.upper()
        part2 = urllib.quote(uri.lower(), safe="")
        part3 = ""
        
        d = {}
        for k, v in kw.items():
            d[k] = v

        d['oauth_consumer_key'] = consumer_key

        if 'oauth_timestamp' not in d or not d['oauth_timestamp']:
            d['oauth_timestamp'] = str(int(time.time()))

        if 'oauth_nonce' not in d or not d['oauth_nonce']:
            d['oauth_nonce'] = randbytes(32)

        if 'oauth_signature_method' not in d or not d['oauth_signature_method']:
            d['oauth_signature_method'] = 'HMAC-SHA1'

        if 'oauth_version' not in d or not d['oauth_version']:
            d['oauth_version'] = '1.0'

        d_ = sorted(d.items(), key=lambda x:x[0])

        dd_ = [urllib.urlencode([x]).replace("+", "%20") for x in d_]
        part3 = urllib.quote("&".join(dd_))
        
        key = consumer_secret + "&"
        if token_secret:
            key += token_secret

        raw = "%s&%s&%s" % (part1, part2, part3)
        
        if d['oauth_signature_method'] != "HMAC-SHA1":
            raise

        hashed = hmac.new(key, raw, hashlib.sha1)
        hashed = binascii.b2a_base64(hashed.digest())[:-1]
        d["oauth_signature"] = hashed
        
        qs = urllib.urlencode(d_).replace("+", "%20")
        qs += "&" + urllib.urlencode({"oauth_signature":hashed})

        return (d, qs)

    def access_resource2(self, method, api, params, file_params=None):
        r = self.access_resource(method, api, params, file_params)
        if not r:
            return None
        try:
            jdata = json_decode(r)
        except:
            ##XXX:因为腾讯的json数据很2，导致有时候decode的时候会失败，一般都是因为双引号没有转义的问题
            import re
            r_ = re.sub('=\\"[^ >]*"( |>)', '', r)
            try:
                jdata = json_decode(r_)
            except Exception, e:
                log.warning("json_decode qqweibo data fail, %s" % e)
                return None
        if jdata and isinstance(jdata, dict):
            ret_code = jdata.get("ret")
            msg = jdata.get("msg")
            user_id = self.user_alias and self.user_alias.user_id or None
            excp = OAuthTokenExpiredError(user_id,
                    config.OPENID_TYPE_DICT[config.OPENID_QQ], msg)
            if str(ret_code) == "0":
                excp.clear_the_profile()
                data = jdata.get("data")
                return data
            elif str(ret_code) == "3":
                excp.set_the_profile()
                raise excp
            else:
                log.warning("access qqweibo resource %s fail, ret_code=%s, msg=%s" %(api, ret_code, msg))

    def get_old_timeline(self, pagetime, reqnum=200):
        return self.get_timeline(reqnum=reqnum, pageflag=1, pagetime=pagetime)

    def get_new_timeline(self, reqnum=20):
        return self.get_timeline(reqnum=reqnum)

    def get_timeline(self, format_="json", reqnum=200, type_=0, contenttype=0, pagetime=0, pageflag=0):
        qs = {}
        qs['format'] = format_
        qs['reqnum'] = reqnum
        qs['type'] = type_
        qs['contenttype'] = contenttype

        #pageflag: 分页标识（0：第一页，1：向下翻页，2：向上翻页）
        #lastid: 和pagetime配合使用（第一页：填0，向上翻页：填上一次请求返回的第一条记录id，向下翻页：填上一次请求返回的最后一条记录id）
        #pagetime 本页起始时间（第一页：填0，向上翻页：填上一次请求返回的第一条记录时间，向下翻页：填上一次请求返回的最后一条记录时间）
        qs['pageflag'] = pageflag
        qs['pagetime'] = pagetime if pagetime is not None else 0

        jdata = self.access_resource2("GET", "/statuses/broadcast_timeline", qs)
        if jdata and isinstance(jdata, dict):
            info = jdata.get("info") or []
            print '---status from qqweibo, len is: %s' % len(info)
            return [QQWeiboStatusData(c) for c in info]

    def post_status(self, text):
        from flask import request
        qs = {"content": text, "format": "json", "clientip": request.remote_addr,}
        return self.access_resource2("POST", "/t/add", qs)

    def post_status_with_image(self, text, image_file):
        from flask import request
        qs = {"content": text, "format": "json", "clientip": request.remote_addr,}
        f = {"pic" : image_file}
        return self.access_resource2("POST", "/t/add_pic", qs, f)


########NEW FILE########
__FILENAME__ = renren
# -*- coding: utf-8 -*-

import hashlib
import urllib
import urlparse
from past import config
from past.utils.logger import logging
from past.utils.escape import json_decode
from past.utils import httplib2_request

from past.model.user import User, UserAlias, OAuth2Token
from past.model.data import RenrenUser
from past.model.data import (RenrenStatusData, RenrenFeedData, RenrenBlogData, 
    RenrenAlbumData, RenrenPhotoData)

from .oauth2 import OAuth2
from .error import OAuthError, OAuthLoginError, OAuthTokenExpiredError

log = logging.getLogger(__file__)

class Renren(OAuth2):

    authorize_uri = 'https://graph.renren.com/oauth/authorize'
    access_token_uri = 'https://graph.renren.com/oauth/token' 
    api_host = 'http://api.renren.com/restserver.do'

    def __init__(self, alias=None, access_token=None, refresh_token=None):
        d = config.APIKEY_DICT[config.OPENID_RENREN]
        super(Renren, self).__init__(provider = config.OPENID_RENREN,
            apikey = d["key"], 
            apikey_secret = d["secret"], 
            redirect_uri = d["redirect_uri"],
            scope = "read_user_status status_update read_user_feed publish_feed read_user_blog publish_blog read_user_photo photo_upload read_user_album",
            alias=alias, 
            access_token=access_token, 
            refresh_token=refresh_token)

    @classmethod                                                                   
    def get_client(cls, user_id):                                                  
        alias = UserAlias.get_by_user_and_type(user_id,                            
                config.OPENID_TYPE_DICT[config.OPENID_RENREN])                       
        if not alias:                                                              
            return None                                                            
                                                                                   
        token = OAuth2Token.get(alias.id)                                          
        if not token:                                                              
            return None                                                            
                                                                                   
        return cls(alias.alias, token.access_token, token.refresh_token)

    def _request(self, api, method="POST", extra_dict=None):
        if extra_dict is None:
            extra_dict = {}

        params = {
            "method": api,
            "v": "1.0",
            "access_token": self.access_token,
            "format": "json",
        }
        params.update(extra_dict)
        _, qs = Renren.sign(self.apikey_secret, **params)
        uri = "%s?%s" % (self.api_host, qs)

        log.info('getting %s...' % uri)
        resp, content = httplib2_request(uri, method)
        if resp.status == 200:
            user_id = self.user_alias and self.user_alias.user_id or None
            excp = OAuthTokenExpiredError(user_id=None,
                    openid_type=config.OPENID_TYPE_DICT[config.OPENID_RENREN], 
                    msg=content)
            jdata = json_decode(content) if content else None
            if jdata and isinstance(jdata, dict):
                error_code = jdata.get("error_code")
                error_msg = jdata.get("error_msg")
                if error_code:
                    if str(error_code) == "105":
                        ## 无效的token
                        excp.set_the_profile()
                        raise excp
                    elif str(error_code) == "106" and self.user_alias:
                        ## FIXME: 过期的token, 是不是106?
                        try:
                            new_tokens = super(Renren, self).refresh_tokens()
                            if new_tokens and isinstance(new_tokens, dict):
                                OAuth2Token.add(self.user_alias.id, 
                                        new_tokens.get("access_token"), 
                                        new_tokens.get("refresh_token"))
                                excp.clear_the_profile()
                        except OAuthError, e:
                            log.warn("refresh token fail: %s" % e)
                            excp.set_the_profile()
                            raise e
            return jdata

    def get_user_info(self, uid=None):
        qs = {
            "uid": uid or "",
            "fields": "uid,name,sex,star,zidou,vip,birthday,tinyurl,headurl,mainurl,hometown_location,work_history,university_history",
        }

        jdata = self._request("users.getInfo", "POST", qs)
        if jdata and isinstance(jdata, list) and len(jdata) >= 1:
            return RenrenUser(jdata[0])

    def get_timeline(self, page=1, count=100):
        d = {}
        d["count"] = count
        d["page"] = page

        contents = self._request("status.gets", "POST", d)
        ##debug
        if contents and isinstance(contents, list):
            print '---get renren status succ, result length is:', len(contents)
            return [RenrenStatusData(c) for c in contents]

    def get_feed(self, type_="10,20,30,40", page=1, count=50):
        d = {}
        d["count"] = count
        d["page"] = page
        d["type"] = type_

        contents = self._request("feed.get", "POST", d)
        ##debug
        if contents and isinstance(contents, list):
            print '---get renren feed succ, result length is:', len(contents)
            return [RenrenFeedData(c) for c in contents]

    def get_blogs(self, page=1, count=50):
        d = {}
        d["count"] = count
        d["page"] = page
        d["uid"] = self.alias

        contents = self._request("blog.gets", "POST", d)
        print '---get renren blog succ'
        if contents:
            return contents

    def get_blog(self, blog_id, uid):
        d = {}
        d["uid"] = uid or self.alias
        d["id"] = blog_id
        d["comment"] = 50

        contents = self._request("blog.get", "POST", d)
        if contents and isinstance(contents, dict):
            return RenrenBlogData(contents)

    def get_photos(self, aid, page=1, count=100):
        d = {}
        d["count"] = count
        d["page"] = page
        d["uid"] = self.alias
        d["aid"] = aid

        contents = self._request("photos.get", "POST", d)
        if contents and isinstance(contents, list):
            print '---get renren photos succ, result length is:', len(contents)
            return [RenrenPhotoData(c) for c in contents]
            
    def get_albums(self, page=1, count=1000):
        d = {}
        d["count"] = count
        d["page"] = page
        d["uid"] = self.alias

        contents = self._request("photos.getAlbums", "POST", d)
        if contents and isinstance(contents, list):
            print '---get renren album succ, result length is:', len(contents)
            return [RenrenAlbumData(c) for c in contents]

    @classmethod
    def sign(cls, token_secret, **kw):
        
        d = {}
        for k, v in kw.items():
            d[k] = v
        d_ = sorted(d.items(), key=lambda x:x[0])

        dd_ = ["%s=%s" %(x[0], x[1]) for x in d_]
        raw = "%s%s" %("".join(dd_), token_secret)
        hashed = hashlib.md5(raw).hexdigest()

        d["sig"] = hashed
        
        qs = urllib.urlencode(d_).replace("+", "%20")
        qs += "&" + urllib.urlencode({"sig":hashed})

        return (d, qs)

########NEW FILE########
__FILENAME__ = sina
# -*- coding: utf-8 -*-

import urllib
import urlparse
from past import config
from past.utils.logger import logging
from past.utils.escape import json_decode
from past.utils import httplib2_request

from past.model.user import User, UserAlias, OAuth2Token
from past.model.data import SinaWeiboUser 
from past.model.data import SinaWeiboStatusData

from .oauth2 import OAuth2
from .error import OAuthLoginError, OAuthTokenExpiredError

log = logging.getLogger(__file__)

class SinaWeibo(OAuth2):

    authorize_uri = 'https://api.weibo.com/oauth2/authorize'
    access_token_uri = 'https://api.weibo.com/oauth2/access_token' 
    api_host = "https://api.weibo.com"

    def __init__(self, alias=None, access_token=None, refresh_token=None, 
            api_version="2"):

        self.api_version = api_version
        d = config.APIKEY_DICT[config.OPENID_SINA]
        super(SinaWeibo, self).__init__(provider = config.OPENID_SINA, 
                apikey = d["key"], 
                apikey_secret = d["secret"], 
                redirect_uri = d["redirect_uri"],
                alias=alias, 
                access_token=access_token, 
                refresh_token=refresh_token)

    @classmethod
    def get_client(cls, user_id):
        alias = UserAlias.get_by_user_and_type(user_id, 
                config.OPENID_TYPE_DICT[config.OPENID_SINA])
        if not alias:
            return None

        token = OAuth2Token.get(alias.id)
        if not token:
            return None

        return cls(alias.alias, token.access_token, token.refresh_token)

    def check_result(self, uri, resp, content):
        #{"error":"expired_token","error_code":21327,"request":"/2/statuses/update.json"}
        #log.debug("---sina check result, status: %s, resp: %s, content: %s" %(resp.status, resp, content))
        jdata = json_decode(content) if content else None
        if jdata and isinstance(jdata, dict):
            error_code = jdata.get("error_code")
            error = jdata.get("error")
            request_api = jdata.get("request")
            user_id = self.user_alias and self.user_alias.user_id or None
            excp = OAuthTokenExpiredError(user_id,
                    config.OPENID_TYPE_DICT[config.OPENID_SINA], 
                    "%s:%s:%s" %(error_code, error, request_api))
            if error_code and isinstance(error_code, int):
                error_code = int(error_code)
                if error_code >= 21301 and error_code <= 21399:
                    excp.set_the_profile()
                    raise excp
                else:
                    log.warning("get %s fail, error_code=%s, error_msg=%s" \
                        % (uri, error_code, error))
            else:
                excp.clear_the_profile()
                return jdata

    def get(self, url, extra_dict=None):
        uri = urlparse.urljoin(self.api_host, self.api_version)
        uri = urlparse.urljoin(uri, url)
        if extra_dict is None:
            extra_dict = {}
        if not "access_token" in extra_dict:
            extra_dict["access_token"] = self.access_token
        if not "source" in extra_dict:
            extra_dict["source"] = self.apikey

        if extra_dict:
            qs = urllib.urlencode(extra_dict)
            if "?" in uri:
                uri = "%s&%s" % (uri, qs)
            else:
                uri = "%s?%s" % (uri, qs)
        log.info('getting %s...' % uri)

        resp, content = httplib2_request(uri, "GET")
        content_json = self.check_result(uri, resp, content)
        return content_json

    def post(self, url, body, headers=None):
        uri = urlparse.urljoin(self.api_host, self.api_version)
        uri = urlparse.urljoin(uri, url)

        log.info("posting %s" %url)
        resp, content = httplib2_request(uri, "POST", body=body, headers=headers)
        content_json = self.check_result(uri, resp, content)
        log.info("post to sina return:%s" % content_json)
        return content_json

    def get_user_info(self, uid=None):
        d = {}
        d["uid"] = uid or ""
        jdata = self.get("/users/show.json", d)
        if jdata and isinstance(jdata, dict):
            return SinaWeiboUser(jdata)

    def get_timeline(self, since_id=None, until_id=None, count=100):
        d = {}
        d["uid"] = self.alias
        d["trim_user"] = 0
        d["count"] = count
        if since_id is not None:
            d["since_id"] = since_id 
        if until_id is not None:
            d["max_id"] = until_id

        r = self.get("/statuses/user_timeline.json", d)
        contents = r and r.get("statuses", [])
        if contents and isinstance(contents, list):
            print '---get sinawebo succ, result length is:', len(contents)
            return [SinaWeiboStatusData(c) for c in contents]

    ## 新浪微博也很2，通过page可以拿到过往的所有微博
    def get_timeline_by_page(self, page=1, count=100):
        d = {}
        d["uid"] = self.alias
        d["trim_user"] = 0
        d["count"] = count
        d["page"] = page

        r = self.get("/statuses/user_timeline.json", d)
        contents = r and r.get("statuses", [])
        if contents and isinstance(contents, list):
            print '---get sinawebo page %s succ, result length is: %s' %(page, len(contents))
            return [SinaWeiboStatusData(c) for c in contents]

    def post_status(self, text):
        qs = {}
        qs["status"] = text
        qs["access_token"] = self.access_token
        body = urllib.urlencode(qs)
        contents = self.post("/statuses/update.json", body=body)

    def post_status_with_image(self, text, image_file):
        from past.utils import encode_multipart_data
        d = {"status": text, "access_token": self.access_token}
        f = {"pic" : image_file}
        body, headers = encode_multipart_data(d, f)
        contents = self.post("/statuses/upload.json", body=body, headers=headers)


########NEW FILE########
__FILENAME__ = twitter
# -*- coding: utf-8 -*-

import tweepy
from tweepy.error import TweepError

from past import config
from past.utils.escape import json_encode, json_decode
from past.utils import httplib2_request

from past.model.user import User, UserAlias, OAuth2Token
from past.model.user import OAuth2Token
from past.model.data import TwitterUser
from past.model.data import TwitterStatusData

from .error import OAuthTokenExpiredError

class TwitterOAuth1(object):
    provider = config.OPENID_TWITTER

    def __init__(self, alias=None, 
            apikey=None, apikey_secret=None, redirect_uri=None,
            token=None, token_secret=None):

        d = config.APIKEY_DICT[config.OPENID_TWITTER]

        self.consumer_key = apikey or d['key']
        self.consumer_secret = apikey_secret or d['secret']
        self.callback = redirect_uri or d['redirect_uri']

        self.token = token
        self.token_secret = token_secret

        self.alias = alias
        if alias:
            self.user_alias = UserAlias.get(
                    config.OPENID_TYPE_DICT[config.OPENID_TWITTER], alias)
        else:
            self.user_alias = None

        self.auth = tweepy.OAuthHandler(self.consumer_key, self.consumer_secret, self.callback)
        if self.token and self.token_secret and self.auth:
            self.auth.set_access_token(self.token, self.token_secret)

    def __repr__(self):
        return "<TwitterOAuth1 consumer_key=%s, consumer_secret=%s, token=%s, token_secret=%s>" \
            % (self.consumer_key, self.consumer_secret, self.token, self.token_secret)
    __str__ = __repr__

    def login(self):
        return self.auth.get_authorization_url()

    def get_access_token(self, verifier=None):
        self.auth.get_access_token(verifier)
        t = {"access_token":self.auth.access_token.key, 
            "access_token_secret": self.auth.access_token.secret,}
        return t
    
    def save_request_token_to_session(self, session_):
        t = {"key": self.auth.request_token.key,
            "secret": self.auth.request_token.secret,}
        session_['request_token'] = json_encode(t)

    def get_request_token_from_session(self, session_, delete=True):
        t = session_.get("request_token")
        token = json_decode(t) if t else {}
        if delete:
            self.delete_request_token_from_session(session_)
        return token

    def delete_request_token_from_session(self, session_):
        session_.pop("request_token", None)

    @classmethod                                                                   
    def get_client(cls, user_id):                                                  
        alias = UserAlias.get_by_user_and_type(user_id,                            
                config.OPENID_TYPE_DICT[config.OPENID_TWITTER])                       
        if not alias:                                                              
            return None                                                            

        token = OAuth2Token.get(alias.id)
        if not token:
            return None
                                                                                   
        return cls(alias=alias.alias, token=token.access_token, token_secret=token.refresh_token)
    
    def api(self):
        return tweepy.API(self.auth, parser=tweepy.parsers.JSONParser())

    def get_user_info(self):
        user = self.api().me()
        return TwitterUser(user)

    def get_timeline(self, since_id=None, max_id=None, count=200):
        user_id = self.user_alias and self.user_alias.user_id or None
        try:
            contents = self.api().user_timeline(since_id=since_id, max_id=max_id, count=count)
            excp = OAuthTokenExpiredError(user_id,
                    config.OPENID_TYPE_DICT[config.OPENID_TWITTER], "")
            excp.clear_the_profile()
            return [TwitterStatusData(c) for c in contents]
        except TweepError, e:
            excp = OAuthTokenExpiredError(user_id,
                    config.OPENID_TYPE_DICT[config.OPENID_TWITTER], 
                    "%s:%s" %(e.reason, e.response))
            excp.set_the_profile()
            raise excp

    def post_status(self, text):
        user_id = self.user_alias and self.user_alias.user_id or None
        try:
            self.api().update_status(status=text)
            excp = OAuthTokenExpiredError(user_id,
                    config.OPENID_TYPE_DICT[config.OPENID_TWITTER], "")
            excp.clear_the_profile()
        except TweepError, e:
            excp = OAuthTokenExpiredError(user_id,
                    config.OPENID_TYPE_DICT[config.OPENID_TWITTER], 
                    "%s:%s" %(e.reason, e.response))
            excp.set_the_profile()
            raise excp


########NEW FILE########
__FILENAME__ = wordpress
# -*- coding: utf-8 -*-

from past.store import mc
from past.model.data import WordpressData
from past.utils.logger import logging

log = logging.getLogger(__file__)

class Wordpress(object):
    
    WORDPRESS_ETAG_KEY = "wordpress:etag:%s"

    ## 同步wordpress rss
    def __init__(self, alias):
        ## alias means wordpress feed uri
        self.alias = alias

    def __repr__(self):
        return "<Wordpress alias=%s>" %(self.alias)
    __str__ = __repr__

    def get_etag(self):
        r = str(Wordpress.WORDPRESS_ETAG_KEY % self.alias)
        return mc.get(r)

    def set_etag(self, etag):
        r = str(Wordpress.WORDPRESS_ETAG_KEY % self.alias)
        mc.set(r, etag)

    def get_feeds(self, refresh=True):
        import feedparser
        etag = self.get_etag()
        if refresh:
            d = feedparser.parse(self.alias)
        else:
            d = feedparser.parse(self.alias, etag=etag)
        if not d:
            return []
        if not (d.status == 200 or d.status == 301):
            log.warning("---get wordpress feeds, status is %s, not valid" % d.status)
            return []

        entries = d.entries
        if not entries:
            return []

        if (not refresh) and hasattr(d,  'etag'):
            self.set_etag(d.etag)
        return [WordpressData(x) for x in entries]

########NEW FILE########
__FILENAME__ = config
#-*- coding:utf-8 -*- 
#-- db config --
DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWD = "123456"
DB_NAME = "thepast"

#-- smtp config --
SMTP_SERVER = "localhost"
SMTP_USER = ""
SMTP_PASSWORD = ""

#-- mc config --
# mc replace redis
MEMCACHED_HOST = "127.0.0.1"
MEMCACHED_PORT = 11211

#-- app config --
DEBUG = True
SECRET_KEY = "dev_key_of_thepast"
SESSION_COOKIE_NAME = "pastme"
PERMANENT_SESSION_LIFETIME = 3600 * 24 * 30

SITE_COOKIE = "pastck"

#-- class kind --#
K_SYNCTASK = 1000
K_TASKQUEUE = 1001

#-- openid type config --
OPENID_DOUBAN = 'douban'
OPENID_SINA = 'sina'
OPENID_QQ = 'qq' ##qq weibo
OPENID_TWITTER = 'twitter'
OPENID_THEPAST = 'thepast'
OPENID_RENREN = 'renren'
OPENID_INSTAGRAM = 'instagram'
##命名需要商榷
OPENID_WORDPRESS = 'wordpress'

OPENID_TYPE_DICT = {
    OPENID_DOUBAN : "D",
    OPENID_SINA : "S",
    OPENID_QQ : "Q",
    OPENID_TWITTER : "T",
    OPENID_WORDPRESS : "W",
    OPENID_THEPAST : "M",
    OPENID_RENREN: "R",
    OPENID_INSTAGRAM: "I",
}
OPENID_TYPE_DICT_REVERSE = dict((v,k) for k, v in OPENID_TYPE_DICT.iteritems())

OPENID_TYPE_NAME_DICT = {
    "D" : u"豆瓣",
    "S" : u"新浪微博",
    "T" : u"twitter",
    "Q" : u"腾讯微博",
    "W" : u"Wordpress",
    "M" : u"Thepast",
    "R" : u"人人",
    "I" : u"Instagram",
}

CAN_SHARED_OPENID_TYPE = [ "D", "S", "T", "Q", "R", "I", ]

wELCOME_MSG_DICT = {
    "D": u"#thepast.me# 今天的点滴，就是明天的旧时光， thepast.me， 备份广播，往事提醒  http://thepast.me ",
    "S": u"#thepast.me# 今天的点滴，就是明天的旧时光， thepast.me， 备份微博，往事提醒  http://thepast.me ",
    "T": u"#thepast.me# 今天的点滴，就是明天的旧时光， thepast.me， 备份twitter，往事提醒  http://thepast.me ",
    "Q": u"#thepast.me# 今天的点滴，就是明天的旧时光， thepast.me， 备份微博，往事提醒  http://thepast.me ",
    "R": u"#thepast.me# 今天的点滴，就是明天的旧时光， thepast.me， 备份人人，往事提醒  http://thepast.me ",
    "I": u"#thepast.me# 今天的点滴，就是明天的旧时光， thepast.me， 备份你的instagram，提醒往事  http://thepast.me ",
}

#-- oauth key & secret config --
APIKEY_DICT = {
    OPENID_DOUBAN : {
        "key" : "",
        "secret" : "",
        "redirect_uri" : "http://thepast.me/connect/douban/callback",
    },
    OPENID_SINA : {
        "key" : "",
        "secret" : "",
        "redirect_uri" : "http://thepast.me/connect/sina/callback",
    },
    OPENID_TWITTER : {
        "key" : "",
        "secret" : "",
        "redirect_uri" : "http://thepast.me/connect/twitter/callback",
    },
    OPENID_QQ: {
        "key" : "",
        "secret" : "",
        "redirect_uri" : "http://thepast.me/connect/qq/callback",
    },
    OPENID_RENREN: {
        "key" : "",
        "secret" : "",
        "redirect_uri" : "http://thepast.me/connect/renren/callback",
    },
    OPENID_INSTAGRAM: {
        "key" : "",
        "secret" : "",
        "redirect_uri" : "http://thepast.me/connect/instagram/callback",
    },
}

#-- category of status --
CATE_DOUBAN_STATUS = 100
CATE_DOUBAN_NOTE = 101
CATE_DOUBAN_MINIBLOG = 102
CATE_DOUBAN_PHOTO = 103
CATE_SINA_STATUS = 200
CATE_WORDPRESS_POST = 300
CATE_TWITTER_STATUS = 400
CATE_QQWEIBO_STATUS = 500
## thepast 的日记
CATE_THEPAST_NOTE = 600
CATE_RENREN_STATUS = 700
CATE_RENREN_FEED = 701
CATE_RENREN_BLOG = 702
CATE_RENREN_ALBUM = 703
CATE_RENREN_PHOTO = 704
CATE_INSTAGRAM_STATUS = 800

CATE_LIST = (
    CATE_DOUBAN_NOTE,
    CATE_DOUBAN_MINIBLOG,
    CATE_SINA_STATUS,
    CATE_TWITTER_STATUS,
    CATE_QQWEIBO_STATUS,
    CATE_THEPAST_NOTE,
    CATE_RENREN_STATUS,
    CATE_RENREN_FEED,
    CATE_RENREN_BLOG,
    CATE_RENREN_ALBUM,
    CATE_RENREN_PHOTO,
    CATE_INSTAGRAM_STATUS,
)

DOUBAN_NOTE = 'http://douban.com/note/%s'
DOUBAN_MINIBLOG = 'http://douban.com/people/%s/status/%s'
DOUBAN_STATUS = 'http://douban.com/people/%s/status/%s'
WEIBO_STATUS = 'http://weibo.com/%s'
QQWEIBO_STATUS = 'http://t.qq.com/t/%s'
TWITTER_STATUS = 'http://twitter.com/#!/%s/status/%s'
THEPAST_NOTE = 'http://thepast.me/note/%s'
RENREN_BLOG = 'http://blog.renren.com/blog/%s/%s'
INSTAGRAM_USER_PAGE = 'http://instagram.com/%s'

DOUBAN_SITE = "http://www.douban.com"
SINA_SITE = "http://weibo.com"
TWITTER_SITE = "http://twitter.com"
QQWEIBO_SITE = "http://t.qq.com"
RENREN_SITE = "http://www.renren.com"
INSTAGRAM_SITE = "http://instagram.com"

#uid of laiwei
MY_USER_ID = 4

#cache
CACHE_DIR = "/home/work/proj/thepast/var/cache"

#file download 
FILE_DOWNLOAD_DIR = "/home/work/proj/thepast/var/down"
PDF_FILE_DOWNLOAD_DIR = FILE_DOWNLOAD_DIR + "/pdf"

#suicide log
SUICIDE_LOG = "/home/work/proj/thepast/suicide.log"

try:
    from local_config import *
except:
    import warnings
    warnings.warn('no local config')




########NEW FILE########
__FILENAME__ = view
#-*- coding:utf-8 -*-

from flask import (session, redirect, request, abort, g, url_for, flash)
from past import config
from past.corelib import set_user_cookie 

from past.model.user import User, UserAlias, OAuth2Token
from past.model.status import SyncTask, TaskQueue

from past.api.douban import Douban
from past.api.sina import SinaWeibo
from past.api.qqweibo import QQWeibo
from past.api.renren import Renren
from past.api.instagram import Instagram
from past.api.twitter import TwitterOAuth1
from past.api.wordpress import Wordpress
from past.api.error import OAuthError

from past.utils.escape import json_encode
from past.connect import blue_print

from past.utils.logger import logging
log = logging.getLogger(__file__)

@blue_print.route("/",  defaults={"provider": config.OPENID_DOUBAN})
@blue_print.route("/<provider>")
def connect(provider):
    if provider == "renren":
        return "我已经实在受不了人人，被人人的管理员快搞死了，怎么修改都不通过，唉...  有兴趣可以看看这边豆瓣网友的帖子：http://www.douban.com/note/250372684/"
    #return "thepast.me 正在升级硬件，暂时不提供登录、注册功能，请谅解，有问题请邮件到 help@thepast.me"

    client = None
    if provider == config.OPENID_DOUBAN:
        client = Douban()
    elif provider == config.OPENID_SINA:
        client = SinaWeibo()
    elif provider == config.OPENID_TWITTER:
        client = TwitterOAuth1()
    elif provider == config.OPENID_QQ:
        client = QQWeibo()
    elif provider == config.OPENID_RENREN:
        client = Renren()
    elif provider == config.OPENID_INSTAGRAM:
        client = Instagram()
    if not client:
        abort(400, "不支持该第三方登录")

    try:
        login_uri = client.login()
    except OAuthError, e:
        log.warning(e)
        abort(400, "抱歉，跳转到第三方失败，请重新尝试一下:)")

    ## when use oauth1, MUST save request_token and secret to SESSION
    if provider == config.OPENID_TWITTER or provider == config.OPENID_QQ:
        client.save_request_token_to_session(session)

    return redirect(login_uri)

@blue_print.route("/<provider>/callback")
def connect_callback(provider):
    code = request.args.get("code")

    client = None
    user = None

    openid_type = config.OPENID_TYPE_DICT.get(provider)
    if not openid_type:
        abort(404, "not support such provider")

    if provider in [config.OPENID_DOUBAN, config.OPENID_SINA, config.OPENID_RENREN,
            config.OPENID_INSTAGRAM,]:
        if provider == config.OPENID_DOUBAN:
            client = Douban()
        elif provider == config.OPENID_SINA:
            client = SinaWeibo()
        elif provider == config.OPENID_RENREN:
            client = Renren()
        elif provider == config.OPENID_INSTAGRAM:
            client = Instagram()

        ## oauth2方式授权处理
        try:
            token_dict = client.get_access_token(code)
            print "---token_dict", token_dict
        except OAuthError, e:
            log.warning(e)
            abort(400, u"从第三方获取access_token失败了，请重新尝试一下，抱歉:)")

        if not (token_dict and token_dict.get("access_token")):
            abort(400, "no_access_token")
        try:
            access_token = token_dict.get("access_token", "") 
            refresh_token = token_dict.get("refresh_token", "") 
            #the last is instagram case:)
            uid = token_dict.get("uid") or token_dict.get("user", {}).get("uid") \
                    or token_dict.get("user", {}).get("id")
            client.set_token(access_token, refresh_token)
            user_info = client.get_user_info(uid)
            print "---user_info", user_info, user_info.data
        except OAuthError, e:
            log.warning(e)
            abort(400, u"我已经实在受不了人人，被人人的管理员快搞死了，怎么修改都不通过，唉")

        user = _save_user_and_token(token_dict, user_info, openid_type)

    else:
        ## 处理以oauth1的方式授权的
        if provider == config.OPENID_QQ:
            user = _qqweibo_callback(request)

        elif provider == config.OPENID_TWITTER:
            user = _twitter_callback(request)

    if user:
        _add_sync_task_and_push_queue(provider, user)

        if not user.get_email():
            return redirect("/settings")

        return redirect("/")
    else:
        flash(u"连接到%s失败了，可能是对方网站忙，请稍等重试..." %provider,  "error")
        return redirect("/")

def _qqweibo_callback(request):
    openid_type = config.OPENID_TYPE_DICT[config.OPENID_QQ]
    client = QQWeibo()
    
    ## from qqweibo
    token = request.args.get("oauth_token")
    verifier = request.args.get("oauth_verifier")

    ## from session
    token_secret_pair = client.get_request_token_from_session(session)
    if token == token_secret_pair['key']:
        client.set_token(token, token_secret_pair['secret'])
    ## get access_token from qq
    token, token_secret  = client.get_access_token(verifier)
    user = client.get_user_info()

    token_dict = {}
    token_dict['access_token'] = token
    #TODO:这里refresh_token其实就是access_token_secret
    token_dict['refresh_token'] = token_secret
    user = _save_user_and_token(token_dict, user, openid_type)

    return user

def _twitter_callback(request):
    openid_type = config.OPENID_TYPE_DICT[config.OPENID_TWITTER]
    client = TwitterOAuth1()

    ## from twitter
    code = request.args.get("oauth_code") ## FIXME no use
    verifier = request.args.get("oauth_verifier")
    
    ## from session
    request_token = client.get_request_token_from_session(session)
    
    ## set the authorized request_token to OAuthHandle
    client.auth.set_request_token(request_token.get("key"), 
            request_token.get("secret"))

    ## get access_token
    try:
        token_dict = client.get_access_token(verifier)
    except OAuthError, e:
        abort(401, e.msg)

    thirdparty_user = client.get_user_info()
    
    user = _save_user_and_token(token_dict, thirdparty_user, openid_type)
    return user
    
## 保存用户信息到数据库，并保存token
def _save_user_and_token(token_dict, thirdparty_user, openid_type):
    first_connect = False
    ua = UserAlias.get(openid_type, thirdparty_user.get_user_id())
    if not ua:
        if not g.user:
            ua = UserAlias.create_new_user(openid_type,
                    thirdparty_user.get_user_id(), thirdparty_user.get_nickname())
        else:
            ua = UserAlias.bind_to_exists_user(g.user, 
                    openid_type, thirdparty_user.get_user_id())
        first_connect = True
    if not ua:
        return None

    ##设置个人资料（头像等等）
    u = User.get(ua.user_id)
    u.set_avatar_url(thirdparty_user.get_avatar())
    u.set_icon_url(thirdparty_user.get_icon())

    ##把各个第三方的uid保存到profile里面
    k = openid_type
    v = {
        "uid": thirdparty_user.get_uid(), 
        "name": thirdparty_user.get_nickname(), 
        "intro": thirdparty_user.get_intro(),
        "signature": thirdparty_user.get_signature(),
        "avatar": thirdparty_user.get_avatar(),
        "icon": thirdparty_user.get_icon(),
        "email": thirdparty_user.get_email(),
        "first_connect": "Y" if first_connect else "N",
    }
    u.set_profile_item(k, json_encode(v))

    ##保存access token
    if openid_type == config.OPENID_TYPE_DICT[config.OPENID_TWITTER]:
        OAuth2Token.add(ua.id, token_dict.get("access_token"), 
                token_dict.get("access_token_secret", ""))
    else:
        OAuth2Token.add(ua.id, token_dict.get("access_token"), 
                token_dict.get("refresh_token", ""))
    ##set cookie，保持登录状态
    if not g.user:
        g.user = User.get(ua.user_id)
        set_user_cookie(g.user, session)
    
    return g.user

## 添加sync_task任务，并且添加到队列中
def _add_sync_task_and_push_queue(provider, user):
        
    task_ids = [x.category for x in SyncTask.gets_by_user(user)]

    if provider == config.OPENID_DOUBAN:
        if str(config.CATE_DOUBAN_STATUS) not in task_ids:
            t = SyncTask.add(config.CATE_DOUBAN_STATUS, user.id)
            t and TaskQueue.add(t.id, t.kind)

    elif provider == config.OPENID_SINA:
        if str(config.CATE_SINA_STATUS) not in task_ids:
            t = SyncTask.add(config.CATE_SINA_STATUS, user.id)
            t and TaskQueue.add(t.id, t.kind)
    elif provider == config.OPENID_TWITTER:
        if str(config.CATE_TWITTER_STATUS) not in task_ids:
            t = SyncTask.add(config.CATE_TWITTER_STATUS, user.id)
            t and TaskQueue.add(t.id, t.kind)
    elif provider == config.OPENID_QQ:
        if str(config.CATE_QQWEIBO_STATUS) not in task_ids:
            t = SyncTask.add(config.CATE_QQWEIBO_STATUS, user.id)
            t and TaskQueue.add(t.id, t.kind)
    elif provider == config.OPENID_RENREN:
        for cate in (config.CATE_RENREN_STATUS, config.CATE_RENREN_BLOG, 
                config.CATE_RENREN_ALBUM, config.CATE_RENREN_PHOTO):
            if str(cate) not in task_ids:
                t = SyncTask.add(cate, user.id)
                t and TaskQueue.add(t.id, t.kind)
    elif provider == config.OPENID_INSTAGRAM:
        if str(config.CATE_INSTAGRAM_STATUS) not in task_ids:
            t = SyncTask.add(config.CATE_INSTAGRAM_STATUS, user.id)
            t and TaskQueue.add(t.id, t.kind)


########NEW FILE########
__FILENAME__ = consts
#-*- coding:utf-8 -*-

import datetime

YESTERDAY = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
TODAY = datetime.datetime.now().strftime("%Y-%m-%d")
TOMORROW = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")


YES = 'Y'
NO = 'N'

USER_PRIVACY_PRIVATE = 'X'
USER_PRIVACY_PUBLIC = 'P'
USER_PRIVACY_FRIEND = 'F'
USER_PRIVACY_THEPAST = 'T'

NOTE_FMT_PLAIN = 'P'
NOTE_FMT_MARKDOWN = 'M'

STATUS_PRIVACY_PRIVATE = 'X'
STATUS_PRIVACY_PUBLIC = 'P'
STATUS_PRIVACY_FRIEND = 'F'
STATUS_PRIVACY_THEPAST = 'F'

########NEW FILE########
__FILENAME__ = cache
#-*- coding:utf-8 -*-

'''from douban code, cool '''

import inspect
from functools import wraps
import time

try:
    import cPickle as pickle
except:
    import pickle

from .empty import Empty
from .format import format

from past.store import mc

# some time consts for mc expire
HALF_HOUR =  1800
ONE_HOUR = 3600
HALF_DAY = ONE_HOUR * 12
ONE_DAY = ONE_HOUR * 24
ONE_WEEK = ONE_DAY * 7
ONE_MONTH = ONE_DAY * 30


def gen_key(key_pattern, arg_names, defaults, *a, **kw):
    return gen_key_factory(key_pattern, arg_names, defaults)(*a, **kw)


def gen_key_factory(key_pattern, arg_names, defaults):
    args = dict(zip(arg_names[-len(defaults):], defaults)) if defaults else {}
    if callable(key_pattern):
        names = inspect.getargspec(key_pattern)[0]
    def gen_key(*a, **kw):
        aa = args.copy()
        aa.update(zip(arg_names, a))
        aa.update(kw)
        if callable(key_pattern):
            key = key_pattern(*[aa[n] for n in names])
        else:
            key = format(key_pattern, *[aa[n] for n in arg_names], **aa)
        return key and key.replace(' ','_'), aa
    return gen_key

def cache_(key_pattern, mc, expire=0, max_retry=0):
    def deco(f):
        arg_names, varargs, varkw, defaults = inspect.getargspec(f)
        if varargs or varkw:
            raise Exception("do not support varargs")
        gen_key = gen_key_factory(key_pattern, arg_names, defaults)
        @wraps(f)
        def _(*a, **kw):
            key, args = gen_key(*a, **kw)
            if not key:
                return f(*a, **kw)
            if isinstance(key, unicode):
                key = key.encode("utf8")
            r = mc.get(key)

            # anti miss-storm
            retry = max_retry
            while r is None and retry > 0:
                time.sleep(0.1)
                r = mc.get(key)
                retry -= 1
            r = pickle.loads(r) if r else None
            
            if r is None:
                r = f(*a, **kw)
                if r is not None:
                    mc.set(key, pickle.dumps(r), expire)
            
            if isinstance(r, Empty):
                r = None
            return r
        _.original_function = f
        return _
    return deco

def pcache_(key_pattern, mc, count=300, expire=0, max_retry=0):
    def deco(f):
        arg_names, varargs, varkw, defaults = inspect.getargspec(f)
        if varargs or varkw:
            raise Exception("do not support varargs")
        if not ('limit' in arg_names):
            raise Exception("function must has 'limit' in args")
        gen_key = gen_key_factory(key_pattern, arg_names, defaults)
        @wraps(f)
        def _(*a, **kw):
            key, args = gen_key(*a, **kw)
            start = args.pop('start', 0)
            limit = args.pop('limit')
            start = int(start)
            limit = int(limit)
            if not key or limit is None or start+limit > count:
                return f(*a, **kw)
            if isinstance(key, unicode):
                key = key.encode("utf8")
            r = mc.get(key)
            
            # anti miss-storm
            retry = max_retry
            while r is None and retry > 0:
                time.sleep(0.1)
                r = mc.get(key)
                retry -= 1
            r = pickle.loads(r) if r else None

            if r is None:
                r = f(limit=count, **args)
                mc.set(key, pickle.dumps(r), expire)
            return r[start:start+limit]

        _.original_function = f
        return _
    return deco

def delete_cache_(key_pattern, mc):
    def deco(f):
        arg_names, varargs, varkw, defaults = inspect.getargspec(f)
        if varargs or varkw:
            raise Exception("do not support varargs")
        gen_key = gen_key_factory(key_pattern, arg_names, defaults)
        @wraps(f)
        def _(*a, **kw):
            key, args = gen_key(*a, **kw)
            r = f(*a, **kw)
            mc.delete(key)
            return r
        return _
        _.original_function = f
    return deco

def create_decorators(mc):

    def _cache(key_pattern, expire=0, mc=mc, max_retry=0):
        return cache_(key_pattern, mc, expire=expire, max_retry=max_retry)
    
    def _pcache(key_pattern, count=300, expire=0, max_retry=0):
        return pcache_(key_pattern, mc, count=count, expire=expire, max_retry=max_retry)
    
    def _delete_cache(key_pattern):
        return delete_cache_(key_pattern, mc=mc)
    
    return dict(cache=_cache, pcache=_pcache, delete_cache=_delete_cache)
                
    
globals().update(create_decorators(mc))


########NEW FILE########
__FILENAME__ = empty
# encoding: utf-8
"""
empty.py
from douban code, cool
"""

class Empty(object):
    def __call__(self, *a, **kw):
        return empty
    def __nonzero__(self):
        return False
    def __contains__(self, item):
        return False
    def __repr__(self):
        return '<Empty Object>'
    def __str__(self):
        return ''
    def __eq__(self, v):
        return isinstance(v, Empty)
    def __getattr__(self, name):
        if not name.startswith('__'):
            return empty
        raise AttributeError(name)
    def __len__(self):
        return 0
    def __getitem__(self, key):
        return empty
    def __setitem__(self, key, value):
        pass
    def __delitem__(self, key):
        pass
    def __iter__(self):
        return self
    def next(self):
        raise StopIteration

empty = Empty()

########NEW FILE########
__FILENAME__ = format
#!/bin/env python

import re

old_pattern = re.compile(r'%\w')
new_pattern = re.compile(r'\{(\w+(\.\w+|\[\w+\])?)\}')

__formaters = {}

def format(text, *a, **kw):
    f = __formaters.get(text)
    if f is None:
        f = formater(text)
        __formaters[text] = f
    return f(*a, **kw)
    #return formater(text)(*a, **kw)

def formater(text):
    """
    >>> format('%s %s', 3, 2, 7, a=7, id=8)
    '3 2'
    >>> format('%(a)d %(id)s', 3, 2, 7, a=7, id=8)
    '7 8'
    >>> format('{1} {id}', 3, 2, a=7, id=8)
    '2 8'
    >>> class Obj: id = 3
    >>> format('{obj.id} {0.id}', Obj(), obj=Obj())
    '3 3'
    """
#    def arg(k,a,kw):
#        if k.isdigit():
#            return a[int(k)]
#        return kw[k]
    def translator(k):
        if '.' in k:
            name,attr = k.split('.')
            if name.isdigit():
                k = int(name)
                return lambda *a, **kw: getattr(a[k], attr)
            return lambda *a, **kw: getattr(kw[name], attr)
#        elif '[' in k and k.endswith(']'):
#            name,index = k[:k.index('[')],k[k.index('[')+1:-1]
#            def _(*a, **kw):
#                if index.isdigit():
#                    return arg(name,a,kw)[int(index)]
#                return arg(name,a,kw)[index]
#            return _
        else:
            if k.isdigit():
                return lambda *a, **kw: a[int(k)]
            return lambda *a, **kw: kw[k]
    args = [translator(k) for k,_1 in new_pattern.findall(text)]
    if args:
        if old_pattern.findall(text):
            raise Exception('mixed format is not allowed')
        f = new_pattern.sub('%s', text)
        def _(*a, **kw):
            return f % tuple([k(*a,**kw) for k in args])
        return _
    elif '%(' in text:
        return lambda *a, **kw: text % kw 
    else:
        n = len(old_pattern.findall(text))
        return lambda *a, **kw: text % tuple(a[:n])
    
if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = api
#-*- coding:utf-8 -*-
# blueprint: dev -> view -> api

from past.dev import blue_print

from past.utils.logger import logging
log = logging.getLogger(__file__)

@blue_print.route("/api")
def api_index():
    return "ok"


########NEW FILE########
__FILENAME__ = token
#-*- coding:utf-8 -*-
# blueprint: dev -> view -> token

from past.dev import blue_print

from past.utils.logger import logging
log = logging.getLogger(__file__)

@blue_print.route("/token")
def token_index():
    return "ok"


########NEW FILE########
__FILENAME__ = data
#-*- coding:utf-8 -*-

import re
import time
import datetime
import hashlib

from past import config
from past.utils.escape import json_decode , clear_html_element
from past.model.note import Note

## User数据接口 
class AbsUserData(object):

    def __init__(self, data):
        if data:
            self.data = data
        else:
            self.data = {}
        if isinstance(data, basestring):
            self.data = json_decode(data)

    def get_user_id(self):
        raise NotImplementedError

    def get_uid(self):
        raise NotImplementedError

    def get_nickname(self):
        return ""

    def get_intro(self):
        return ""

    def get_signature(self):
        return ""

    def get_avatar(self):
        return ""

    def get_icon(self):
        return ""
    
    def get_email(self):
        return ""

## 豆瓣user数据接口
class DoubanUser(AbsUserData):
    def __init__(self, data):
        super(DoubanUser, self).__init__(data)

    def get_user_id(self):
        id_ = self.data.get("id", {}).get("$t")
        if id_:
            return (id_.rstrip("/").split("/"))[-1]
        return None

    def get_uid(self):
        return self.data.get("uid", {}).get("$t")

    def get_nickname(self):
        return self.data.get("title", {}).get("$t")

    def get_intro(self):
        return self.data.get("content", {}).get("$t")

    def get_signature(self):
        return self.data.get("signature", {}).get("$t")

    def get_avatar(self):
        icon = self.get_icon()
        user_id = self.get_user_id()

        return icon.replace(user_id, "l%s" % user_id)

    def get_icon(self):
        links = {}
        _links = self.data.get("link", [])
        for x in _links:
            rel = x.get("@rel")
            links[rel] = x.get("@href")
        return links.get("icon", "")

## 豆瓣user2数据接口
class DoubanUser2(AbsUserData):
    def __init__(self, data):
        super(DoubanUser2, self).__init__(data)

    def get_user_id(self):
        return self.data.get("id")

    def get_uid(self):
        return self.data.get("uid")

    def get_nickname(self):
        return self.data.get("screen_name")

    def get_intro(self):
        return self.data.get("description")

    def get_signature(self):
        return ""

    def get_avatar(self):
        return self.data.get("large_avatar")

    def get_icon(self):
        return self.data.get("small_avatar")

## 新浪微博user数据接口
class SinaWeiboUser(AbsUserData):

    def __init__(self, data):
        super(SinaWeiboUser, self).__init__(data)

    def get_user_id(self):
        return self.data.get("idstr","")

    def get_uid(self):
        return self.data.get("domain", "")

    def get_nickname(self):
        return self.data.get("screen_name", "")

    def get_intro(self):
        return self.data.get("description", "")

    def get_signature(self):
        return ""

    def get_avatar(self):
        return self.data.get("avatar_large", "")

    def get_icon(self):
        return self.data.get("profile_image_url", "")

    def get_email(self):
        return ""

## Twitter user数据接口
class TwitterUser(AbsUserData):

    def __init__(self, data):
        super(TwitterUser, self).__init__(data)

    def get_user_id(self):
        return self.data.get("id_str","")

    def get_uid(self):
        return self.data.get("name", "")

    def get_nickname(self):
        return self.data.get("screen_name", "")

    def get_intro(self):
        return self.data.get("description", "")

    def get_signature(self):
        return ""

    def get_avatar(self):
        return self.data.get("profile_image_url", "")

    def get_icon(self):
        return self.data.get("profile_image_url", "")

    def get_email(self):
        return ""

## qq weibo user 数据接口
class QQWeiboUser(AbsUserData):

    def __init__(self, data):
        super(QQWeiboUser, self).__init__(data)

    def get_user_id(self):
        return self.data.get("openid","")

    def get_uid(self):
        return self.data.get("name", "")

    def get_nickname(self):
        return self.data.get("nick", "")

    def get_intro(self):
        return self.data.get("introduction", "")

    def get_signature(self):
        return ""

    def get_avatar(self):
        r = self.data.get("head", "")
        if r:
            return r + "/100"
        return r

    def get_icon(self):
        r = self.data.get("head", "")
        if r:
            return r + "/40"
        return r

    def get_email(self):
        return self.data.get("email", "")

    def get_birthday(self):
        return "%s-%s-%s" % (self.data.get("birth_year", ""),
            self.data.get("birth_month", ""), self.data.get("birth_day"))

## renren user数据接口
class RenrenUser(AbsUserData):

    def __init__(self, data):
        super(RenrenUser, self).__init__(data)

    def get_user_id(self):
        return self.data.get("uid","")

    def get_uid(self):
        return self.data.get("uid", "")

    def get_nickname(self):
        return self.data.get("name", "")

    def get_intro(self):
        return ""

    def get_signature(self):
        return ""

    def get_avatar(self):
        return self.data.get("headurl", "")

    def get_icon(self):
        return self.data.get("tinyurl", "")

    def get_email(self):
        return ""

## instagram user数据接口
class InstagramUser(AbsUserData):

    def __init__(self, data):
        super(InstagramUser, self).__init__(data)

    def get_user_id(self):
        return self.data.get("id","")

    def get_uid(self):
        return self.data.get("username", "")

    def get_nickname(self):
        return self.data.get("full_name", "") or self.get_uid()

    def get_intro(self):
        return self.data.get("bio", "")

    def get_signature(self):
        return self.data.get("website", "")

    def get_avatar(self):
        return self.data.get("profile_picture", "")

    def get_icon(self):
        return self.data.get("profile_picture", "")

    def get_email(self):
        return ""

## 第三方数据接口
class AbsData(object):
    
    def __init__(self, site, category, data):
        self.site = site
        self.category = category
        self.data = data or {}
        if isinstance(data, basestring):
            try:
                self.data = json_decode(data)
            except Exception, e:
                #import traceback; print traceback.format_exc()
                self.data = {}

    ## 注释以微博为例
    ##原始的数据，json_decode之后的
    def get_data(self):
        return self.data
    
    ##原微博的id
    def get_origin_id(self):
        raise NotImplementedError
    
    ##原微博的创建时间
    def get_create_time(self):
        raise NotImplementedError
    
    ##如果有title的话，比如豆瓣广播
    def get_title(self):
        return ""

    ##原微博的内容
    def get_content(self):
        return ""

    ##原微博本身是个转发，获取被转发的内容
    def get_retweeted_data(self):
        return None

    ##原微博附带的图片，返回结果为list
    def get_images(self):
        return []
    
    ##原微博的作者，如果能获取到的话
    ##XXX
    def get_user(self):
        return None

    ##原微博的uri，可以点过去查看（有可能获取不到或者很麻烦，比如sina就很变态）
    ###XXX
    def get_origin_uri(self):
        return ""

    ##摘要信息，对于blog等长文来说很有用,视情况在子类中覆盖该方法
    def get_summary(self):
        return self.get_content()

    ##lbs信息
    def get_location(self):
        return ""

    ##附件信息(暂时只有豆瓣的有)
    def get_attachments(self):
        return None

class ThepastNoteData(AbsData):
    
    def __init__(self, note):
        self.site = config.OPENID_TYPE_DICT[config.OPENID_THEPAST]
        self.category = config.CATE_THEPAST_NOTE
        self.data = note
        super(ThepastNoteData, self).__init__(
                self.site, self.category, self.data)

    def get_origin_id(self):
        return self.data and self.data.id

    def get_create_time(self):
        return self.data and self.data.create_time

    def get_title(self):
        return self.data and self.data.title or ""

    def get_content(self):
        if self.data:
            return self.data.render_content()
        return ""

    def get_origin_uri(self):
        if self.data:
            return config.THEPAST_NOTE % self.data.id
        return ""

    def get_summary(self):
        return self.data and self.data.content[:140]
        

class DoubanData(AbsData):
    
    def __init__(self, category, data):
        super(DoubanData, self).__init__( 
                config.OPENID_TYPE_DICT[config.OPENID_DOUBAN], category, data)

# 日记
class DoubanNoteData(DoubanData):
    def __init__(self, data):
        super(DoubanNoteData, self).__init__(
                config.CATE_DOUBAN_NOTE, data)

    def get_origin_id(self):
        id_ = self.data.get("id", {}).get("$t")
        if id_:
            return (id_.rstrip("/").split("/"))[-1]
        return None

    def get_create_time(self):
        return self.data.get("published",{}).get("$t")

    def get_title(self):
        return self.data.get("title", {}).get("$t") or ""

    def get_content(self):
        return self.data.get("content", {}).get("$t") or ""

# 广播
class DoubanMiniBlogData(DoubanData):
    def __init__(self, data):
        super(DoubanMiniBlogData, self).__init__(
                config.CATE_DOUBAN_MINIBLOG, data)

    def get_origin_id(self):
        id_ = self.data.get("id", {}).get("$t")
        if id_:
            return (id_.rstrip("/").split("/"))[-1]
        return None

    def get_create_time(self):
        return self.data.get("published",{}).get("$t")

    def get_title(self):
        return self.data.get("title", {}).get("$t") or ""

    def get_content(self):
        return self.data.get("content", {}).get("$t") or ""
    
    def _get_links(self):
        links = {}
        _links = self.data.get("link", [])
        for x in _links:
            rel = x.get("@rel")
            links[rel] = x.get("@href", "").replace("/spic", "/lpic")
        return links

    def get_images(self):
        links = self._get_links()
        if links and links.get("image"):
            return [links.get("image")]
        return []

# 豆瓣新广播（豆瓣说）
class DoubanStatusData(DoubanData):
    def __init__(self, data):
        super(DoubanStatusData, self).__init__(
            config.CATE_DOUBAN_STATUS, data)

    def _parse_score(self, title):
        r1 = title.find("[score]")
        r2 = title.find("[/score]")
        if r1 >= 0 and r2 >= 0:
            result = title[0:r1]
            star = int(title[r1+7:r2])
            for i in range(0, star):
                result += u"\u2605"
            result += title[r2+8:]
            return result
        else:
            return title

    def get_origin_id(self):
        return str(self.data.get("id", ""))

    def get_create_time(self):
        return self.data.get("created_at")

    def get_content(self):
        title = self.data.get("title", "")
        title = self._parse_score(title)
        return "%s %s" %(title, self.data.get("text", ""))

    def get_retweeted_data(self):
        r = self.data.get("reshared_status")
        if r:
            return DoubanStatusData(r)
        else:
            return None

    def get_images(self):
        o = []
        atts = self.get_attachments()
        for att in atts:
            medias = att and att.get_medias()
            for x in medias:
                if x and x.get_type() == 'image':
                    o.append(x.get_src().replace("http://img3", "http://img2").replace("http://img1", "http://img2").replace("http://img5", "http://img2"))   
        return o

    def get_user(self):
        r = self.data.get("user")
        if r:
            return DoubanUser2(r)
        else:
            return None

    def get_origin_uri(self):
        u = self.get_user()
        if u:
            uid = u.get_uid()
            return config.DOUBAN_STATUS % (uid, self.get_origin_id())

    ### 特有的方法：
    def get_target_type(self):
        return self.data.get("target_type")

    def get_attachments(self):
        rs = self.data.get("attachments", [])
        return [_Attachment(r) for r in rs]

class _Attachment(object):
    def __init__(self, data):
        self.data = data or {}

    def get_description(self):
        return self.data.get("description")
    def get_title(self):
        return self.data.get("title", "")
    def get_href(self):
        return self.data.get("expaned_href") or self.data.get("href")
    def get_medias(self):
        rs = self.data.get("media", [])
        return [_Media(x) for x in rs]


class _Media(object):
    def __init__(self, data):
        self.data = data or {}

    def get_type(self):
        return self.data.get("type")
    def get_src(self):
        src = self.data.get("original_src", "") or self.data.get("src", "")
        return src.replace("/spic/", "/mpic/").replace("/small/", "/raw/")
    
class SinaWeiboData(AbsData):
    
    def __init__(self, category, data):
        super(SinaWeiboData, self).__init__( 
                config.OPENID_TYPE_DICT[config.OPENID_SINA], category, data)

# 新浪微博status
class SinaWeiboStatusData(SinaWeiboData):
    def __init__(self, data):
        super(SinaWeiboStatusData, self).__init__(
                config.CATE_SINA_STATUS, data)
    
    def get_origin_id(self):
        return self.data.get("idstr", "")

    def get_create_time(self):
        try:
            t = self.data.get("created_at", "")
            return datetime.datetime.strptime(t, "%a %b %d %H:%M:%S +0800 %Y")
        except Exception, e:
            print e
            return None
    
    def get_title(self):
        return ""

    def get_content(self):
        return self.data.get("text", "") 
    
    def get_retweeted_data(self):
        re = self.data.get("retweeted_status")
        if re:
            return SinaWeiboStatusData(re)

    def get_user(self):
        return SinaWeiboUser(self.data.get("user"))

    def get_origin_pic(self):
        return re.sub("ww[23456].sinaimg.cn", "ww1.sinaimg.cn", self.data.get("original_pic", ""))

    def get_thumbnail_pic(self):
        return re.sub("ww[23456].sinaimg.cn", "ww1.sinaimg.cn", self.data.get("thumbnail_pic", ""))

    def get_middle_pic(self):
        return re.sub("ww[23456].sinaimg.cn", "ww1.sinaimg.cn", self.data.get("bmiddle_pic", ""))

    def get_images(self, size="origin"):
        method = "get_%s_pic" % size
        if hasattr(self, method):
            i = getattr(self, method)()
            if i:
                return [i]
        return []
        
# twitter status
class TwitterStatusData(AbsData):
    def __init__(self, data):
        super(TwitterStatusData, self).__init__(
                config.OPENID_TYPE_DICT[config.OPENID_TWITTER], 
                config.CATE_TWITTER_STATUS, data)
    
    def get_origin_id(self):
        return str(self.data.get("id", ""))

    def get_create_time(self):
        t = self.data.get("created_at", "")
        return datetime.datetime.strptime(t, "%a %b %d %H:%M:%S +0000 %Y")

    def get_title(self):
        return ""

    def get_content(self):
        return self.data.get("text", "") 
    
    def get_retweeted_data(self):
        return None

    def get_user(self):
        return TwitterUser(self.data.get("user"))

    def get_origin_uri(self):
        u = self.get_user()
        if u:
            uid = u.get_user_id()
            status_id = self.get_origin_id()
            return config.TWITTER_STATUS % (uid, status_id)
        return None

# qqweibo status
class QQWeiboStatusData(AbsData):
    def __init__(self, data):
        super(QQWeiboStatusData, self).__init__(
                config.OPENID_TYPE_DICT[config.OPENID_QQ], 
                config.CATE_QQWEIBO_STATUS, data)
    
    def get_origin_id(self):
        return str(self.data.get("id", ""))

    def get_create_time(self):
        t = self.data.get("timestamp")
        if not t:
            return None
        t = float(t)
        return datetime.datetime.fromtimestamp(t)

    def get_title(self):
        return ""

    def get_content(self):
        return self.data.get("text", "") 
    
    def get_retweeted_data(self):
        re = self.data.get("source")
        if re and re != 'null':
            return QQWeiboStatusData(re)
        else:
            return ""

    def get_user(self):
        return QQWeiboUser(self.data) 

    def _get_images(self, size):
        r = []
        imgs = self.data.get("image")
        if imgs and imgs != "null" and isinstance(imgs, list):
            r = ["%s/%s" % (x, size) for x in imgs]
        return r
        
    def get_origin_pic(self):
        return self._get_images(size=2000)

    def get_thumbnail_pic(self):
        return self._get_images(size=160)

    def get_middle_pic(self):
        return self._get_images(size=460)

    def get_images(self, size="middle"):
        method = "get_%s_pic" % size
        if hasattr(self, method):
            return getattr(self, method)()
        return []

    def get_origin_uri(self):
        return self.data.get("fromurl")


class WordpressData(AbsData):
    def __init__(self, data):
        super(WordpressData, self).__init__(
                config.OPENID_TYPE_DICT[config.OPENID_WORDPRESS],
                config.CATE_WORDPRESS_POST, data)

    def get_origin_id(self):
        id_ = self.data.get("id", "") or self.data.get("link", "")
        m = hashlib.md5()
        m.update(id_)
        return m.hexdigest()[:16]

    def get_create_time(self):
        e = self.data
        published = None
        try:
            published = e.published_parsed
        except AttributeError:
            try:
                published = e.updated_parsed
            except AttributeError:
                try:
                    published = e.created_parsed
                except AttributeError:
                    published = None
        if published:
            return datetime.datetime.fromtimestamp(time.mktime(published))
        
    
    def get_title(self):
        return self.data.get("title", "")

    def get_content(self):
        content = self.data.get("content")
        if content:
            c = content[0]
            return c and c.get("value")
        return ""

    def get_user(self):
        return self.data.get("author", "")

    def get_origin_uri(self):
        return self.data.get("link", "") or self.data.get("id", "")

    def get_summary(self):
        return clear_html_element(self.data.get("summary", ""))[:150]

class RenrenData(AbsData):
    
    def __init__(self, category, data):
        super(RenrenData, self).__init__( 
                config.OPENID_TYPE_DICT[config.OPENID_RENREN], category, data)

class RenrenStatusData(RenrenData):
    def __init__(self, data):
        super(RenrenStatusData, self).__init__(
                config.CATE_RENREN_STATUS, data)
    
    def get_origin_id(self):
        return str(self.data.get("status_id", ""))

    def get_create_time(self):
        return self.data.get("time")

    def get_title(self):
        return ""

    def get_content(self):
        return self.data.get("message", "") 
    
    def get_retweeted_data(self):
        d = {}
        d["status_id"] = self.data.get("root_status_id", "")
        forward_message = self.data.get("forward_message", "")
        root_message = self.data.get("root_message", "")
        if forward_message or root_message:
            d["message"] = "%s %s" %(forward_message, root_message)
        else:
            d["message"] = ""
        d["uid"] = self.data.get("root_uid", "")
        d["username"] = self.data.get("root_username", "")
        d["time"] = self.data.get("time", "")
        
        return RenrenStatusData(d)

    def get_user(self):
        return self.data.get("uid", "")

    def get_origin_uri(self):
        return "%s/%s#//status/status?id=%s" %(config.RENREN_SITE, self.data.get("uid"), self.data.get("uid"))

    def get_location(self):
        return self.data.get("place")

class RenrenFeedData(RenrenData):
    def __init__(self, data):
        super(RenrenFeedData, self).__init__(
                config.CATE_RENREN_FEED, data)
    
class RenrenBlogData(RenrenData):
    def __init__(self, data):
        super(RenrenBlogData, self).__init__(
                config.CATE_RENREN_BLOG, data)
    
    def get_origin_id(self):
        return str(self.data.get("id", ""))

    def get_create_time(self):
        return self.data.get("time")

    def get_title(self):
        return self.data.get("title", "")

    def get_content(self):
        return self.data.get("content", "") 

    def get_user(self):
        return self.data.get("uid", "")
    
    def get_origin_uri(self):
        return config.RENREN_BLOG %(self.get_user(), self.get_origin_id())
    
    def get_summary(self):
        c = self.get_content()
        if c and isinstance(c, basestring):
            return c[:140]
        return ""

class RenrenAlbumData(RenrenData):
    def __init__(self, data):
        super(RenrenAlbumData, self).__init__(
                config.CATE_RENREN_ALBUM, data)
    
    def get_origin_id(self):
        return str(self.data.get("aid", ""))

    def get_create_time(self):
        return self.data.get("create_time")

    def get_title(self):
        return self.data.get("name", "")

    def get_content(self):
        return self.data.get("description", "")

    def get_user(self):
        return self.data.get("uid", "")

    def get_images(self):
        return [self.data.get("url", "")]

    def get_size(self):
        return self.data.get("size", 100)
        

class RenrenPhotoData(RenrenData):
    def __init__(self, data):
        super(RenrenPhotoData, self).__init__(
                config.CATE_RENREN_PHOTO, data)
    
    def get_origin_id(self):
        return str(self.data.get("pid", ""))

    def get_create_time(self):
        return self.data.get("time")

    def get_title(self):
        return self.data.get("caption", "")

    def get_content(self):
        return ""

    def get_user(self):
        return self.data.get("uid", "")
    
    def get_origin_pic(self):
        return self.data.get("url_large", "")

    def get_thumbnail_pic(self):
        return self.data.get("url_tiny", "")

    def get_middle_pic(self):
        return self.data.get("url_head", "")

    def get_images(self, size="origin"):
        method = "get_%s_pic" % size
        r = []
        if hasattr(self, method):
            p = getattr(self, method)()
            if p:
                if not isinstance(p, list):
                    r.append(p)
                else:
                    r.extend(p)
        return r

class InstagramStatusData(AbsData):
    def __init__(self, data):
        super(InstagramStatusData, self).__init__(
                config.OPENID_TYPE_DICT[config.OPENID_INSTAGRAM], 
                config.CATE_INSTAGRAM_STATUS, data)
    
    def get_origin_id(self):
        return str(self.data.get("id", ""))

    def get_create_time(self):
        t = self.data.get("created_time")
        if not t:
            return None
        t = float(t)
        return datetime.datetime.fromtimestamp(t)

    def get_title(self):
        caption = self.data.get("caption")
        if caption and isinstance(caption, dict):
            return caption.get("text", "")
        return ""

    def get_content(self):
        return ""

    def get_user(self):
        udata = self.data.get("user")
        if udata and isinstance(udata, dict):
            return InstagramUser(udata)
    
    def get_origin_pic(self):
        images = self.data.get("images")
        if images:
            return images.get("standard_resolution",{}).get("url")

    def get_thumbnail_pic(self):
        images = self.data.get("images")
        if images:
            return images.get("thumbnail",{}).get("url")

    def get_middle_pic(self):
        images = self.data.get("images")
        if images:
            return images.get("low_resolution",{}).get("url")

    def get_images(self, size="origin"):
        method = "get_%s_pic" % size
        r = []
        if hasattr(self, method):
            p = getattr(self, method)()
            if p:
                if not isinstance(p, list):
                    r.append(p)
                else:
                    r.extend(p)
        return r

    def get_origin_uri(self):
        return self.data.get("link", "")

    def get_location(self):
        return self.data.get("location")

########NEW FILE########
__FILENAME__ = kv
#-*- coding:utf-8 -*-

from MySQLdb import IntegrityError

from past.corelib.cache import cache
from past.store import db_conn, mc
from past.utils.escape import json_encode, json_decode

class Kv(object):
    def __init__(self, key_, val, time):
        self.key_ = key_
        self.val = val
        self.time = time

    @classmethod
    def clear_cache(cls, key_):
        mc.delete("mc_kv:%s" %key_)

    @classmethod
    @cache("mc_kv:{key_}")
    def get(cls, key_):
        cursor = db_conn.execute('''select `key`, value, time from kv 
                where `key`=%s''', key_)
        row = cursor.fetchone()
        if row:
            return cls(*row)
        cursor and cursor.close()

    @classmethod
    def set(cls, key_, val):
        cursor = None
        val = json_encode(val) if not isinstance(val, basestring) else val

        try:
            cursor = db_conn.execute('''replace into kv(`key`, value) 
                values(%s,%s)''', (key_, val))
            db_conn.commit()
            cls.clear_cache(key_)
        except IntegrityError:
            db_conn.rollback()

        cursor and cursor.close()

    @classmethod
    def remove(cls, key_):
        cursor = None
        try:
            cursor = db_conn.execute('''delete from kv where `key` = %s''', key_)
            db_conn.commit()
            cls.clear_cache(key_)
        except IntegrityError:
            db_conn.rollback()
        cursor and cursor.close()

class UserProfile(object):
    def __init__(self, user_id, val, time):
        self.user_id = user_id
        self.val = val
        self.time = time

    @classmethod
    def clear_cache(cls, user_id):
        mc.delete("mc_user_profile:%s" %user_id)

    @classmethod
    @cache("mc_user_profile:{user_id}")
    def get(cls, user_id):
        cursor = db_conn.execute('''select user_id, profile, time from user_profile
                where user_id=%s''', user_id)
        row = cursor.fetchone()
        if row:
            return cls(*row)
        cursor and cursor.close()

    @classmethod
    def set(cls, user_id, val):
        cursor = None
        val = json_encode(val) if not isinstance(val, basestring) else val

        try:
            cursor = db_conn.execute('''replace into user_profile (user_id, profile) 
                values(%s,%s)''', (user_id, val))
            db_conn.commit()
            cls.clear_cache(user_id)
        except IntegrityError:
            db_conn.rollback()

        cursor and cursor.close()

    @classmethod
    def remove(cls, user_id):
        cursor = None
        try:
            cursor = db_conn.execute('''delete from user_profile where user_id= %s''', user_id)
            db_conn.commit()
            cls.clear_cache(user_id)
        except IntegrityError:
            db_conn.rollback()
        cursor and cursor.close()

class RawStatus(object):
    def __init__(self, status_id, text, raw, time):
        self.status_id = status_id
        self.text = text
        self.raw = raw
        self.time = time

    @classmethod
    def clear_cache(cls, status_id):
        mc.delete("mc_raw_status:%s" %status_id)

    @classmethod
    @cache("mc_raw_status:{status_id}")
    def get(cls, status_id):
        cursor = db_conn.execute('''select status_id, text, raw, time from raw_status 
                where status_id=%s''', status_id)
        row = cursor.fetchone()
        if row:
            return cls(*row)
        cursor and cursor.close()

    @classmethod
    def set(cls, status_id, text, raw):
        cursor = None
        text = json_encode(text) if not isinstance(text, basestring) else text
        raw = json_encode(raw) if not isinstance(raw, basestring) else raw

        try:
            cursor = db_conn.execute('''replace into raw_status (status_id, text, raw) 
                values(%s,%s,%s)''', (status_id, text, raw))
            db_conn.commit()
            cls.clear_cache(status_id)
        except IntegrityError:
            db_conn.rollback()

        cursor and cursor.close()

    @classmethod
    def remove(cls, status_id):
        cursor = None
        try:
            cursor = db_conn.execute('''delete from raw_status where status_id = %s''', status_id )
            db_conn.commit()
            cls.clear_cache(status_id)
        except IntegrityError:
            db_conn.rollback()
        cursor and cursor.close()

########NEW FILE########
__FILENAME__ = note
#-*- coding:utf-8 -*-

import markdown2
from MySQLdb import IntegrityError
import datetime

from past.store import db_conn, mc
from past.corelib.cache import cache, pcache, HALF_HOUR
from past.utils.escape import json_encode, json_decode
from past import consts
from past import config

class Note(object):
    
    def __init__(self, id, user_id, title, content, create_time, update_time, fmt, privacy):
        self.id = id
        self.user_id = str(user_id)
        self.title = title
        self.content = content
        self.create_time = create_time
        self.update_time = update_time
        self.fmt = fmt
        self.privacy = privacy

    @classmethod
    def _clear_cache(cls, user_id, note_id):
        if user_id:
            mc.delete("note_ids:%s" % user_id)
            mc.delete("note_ids_asc:%s" % user_id)
        if note_id:
            mc.delete("note:%s" % note_id)

    def flush_note(self):
        Note._clear_cache(None, self.id)
        return Note.get(self.id)

    @classmethod
    @cache("note:{id}")
    def get(cls, id):
        cursor = db_conn.execute('''select id, user_id, title, content, create_time, update_time, fmt, privacy 
            from note where id = %s''', id)
        row = cursor.fetchone()
        if row:
            return cls(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7])

    def render_content(self):
        if self.fmt == consts.NOTE_FMT_MARKDOWN:
            return markdown2.markdown(self.content, extras=["wiki-tables", "code-friendly"])
        else:
            return self.content

    @classmethod
    def add(cls, user_id, title, content, fmt=consts.NOTE_FMT_PLAIN, privacy=consts.STATUS_PRIVACY_PUBLIC):
        cursor = None
        try:
            cursor = db_conn.execute('''insert into note (user_id, title, content, create_time, fmt, privacy) 
                    values (%s, %s, %s, %s, %s, %s)''',
                    (user_id, title, content, datetime.datetime.now(), fmt, privacy))
            db_conn.commit()

            note_id = cursor.lastrowid
            note = cls.get(note_id)
            from past.model.status import Status
            Status.add(user_id, note_id, 
                    note.create_time, config.OPENID_TYPE_DICT[config.OPENID_THEPAST], 
                    config.CATE_THEPAST_NOTE, "")
            cls._clear_cache(user_id, None)
            return note
        except IntegrityError:
            db_conn.rollback()
        finally:
            cursor and cursor.close()

    def update(self, title, content, fmt, privacy):
        if title and title != self.title or fmt and fmt != self.fmt or content and content != self.content or privacy and privacy != self.privacy:
            _fmt = fmt or self.fmt
            _title = title or self.title
            _content = content or self.content
            _privacy = privacy or self.privacy
            db_conn.execute('''update note set title = %s, content = %s, fmt = %s, privacy = %s where id = %s''', 
                    (_title, _content, _fmt, _privacy, self.id))
            db_conn.commit()
            self.flush_note()
            
            if title != self.title:
                from past.model.status import Status
                Status._clear_cache(None, self.get_status_id(), None)

    @cache("note:status_id:{self.id}")
    def get_status_id(self):
        cursor = db_conn.execute("""select id from status where origin_id = %s and category = %s""",
                (self.id, config.CATE_THEPAST_NOTE))
        row = cursor.fetchone()
        cursor and cursor.close()
        return row and row[0]
    
    @classmethod
    def delete(cls, id):
        note = cls.get(id)
        if note:
            db_conn.execute("""delete from status where id=%s""", id)
            db_conn.commit()
            cls._clear_cache(note.user_id, note.id)
        
    @classmethod
    @pcache("note_ids:user:{user_id}")
    def get_ids_by_user(cls, user_id, start, limit):
        return cls._get_ids_by_user(user_id, start, limit)

    @classmethod
    @pcache("note_ids_asc:user:{user_id}")
    def get_ids_by_user_asc(cls, user_id, start, limit):
        return cls._get_ids_by_user(user_id, start, limit, order="create_time asc")

    @classmethod
    def _get_ids_by_user(cls, user_id, start=0, limit=20, order="create_time desc"):
        sql = """select id from note where user_id=%s order by """ + order \
                + """ limit %s,%s"""
        cursor = db_conn.execute(sql, (user_id, start, limit))
        rows = cursor.fetchall()
        return [x[0] for x in  rows]

    @classmethod
    def gets(cls, ids):
        return [cls.get(x) for x in ids]

########NEW FILE########
__FILENAME__ = status
#-*- coding:utf-8 -*-

import datetime
import hashlib
import re
from MySQLdb import IntegrityError

from past.utils.escape import json_encode, json_decode, clear_html_element
from past.utils.logger import logging
from past.store import mc, db_conn
from past.corelib.cache import cache, pcache, HALF_HOUR
from .user import UserAlias, User
from .note import Note
from .data import DoubanMiniBlogData, DoubanNoteData, DoubanStatusData, \
        SinaWeiboStatusData, QQWeiboStatusData, TwitterStatusData,\
        WordpressData, ThepastNoteData, RenrenStatusData, RenrenBlogData, \
        RenrenAlbumData, RenrenPhotoData, InstagramStatusData
from .kv import RawStatus
from past import config
from past import consts

log = logging.getLogger(__file__)

#TODO:refactor,暴露在外面的接口为Status
#把Data相关的都应该隐藏起来,不允许外部import

class Status(object):
    
    def __init__(self, id, user_id, origin_id, 
            create_time, site, category, title=""):
        self.id = str(id)
        self.user_id = str(user_id)
        self.origin_id = str(origin_id)
        self.create_time = create_time
        self.site = site
        self.category = category
        self.title = title
        _data_obj = self.get_data()
        ##对于140字以内的消息，summary和text相同；对于wordpress等长文，summary只是摘要，text为全文
        ##summary当作属性来，可以缓存在mc中，text太大了，作为一个method
        self.summary = _data_obj and _data_obj.get_summary() or ""
        if self.site == config.OPENID_TYPE_DICT[config.OPENID_TWITTER]:
            self.create_time += datetime.timedelta(seconds=8*3600)
        
        self._bare_text = self._generate_bare_text()

    def __repr__(self):
        return "<Status id=%s, user_id=%s, origin_id=%s, cate=%s>" \
            %(self.id, self.user_id, self.origin_id, self.category)
    __str__ = __repr__

    def __eq__(self, other):
        ##同一用户，在一天之内发表的，相似的内容，认为是重复的^^, 
        ##对于23点和凌晨1点这种跨天的没有考虑
        ##FIXME:abs(self.create_time - other.create_time) <= datetime.timedelta(1) 
        if self.user_id == other.user_id \
                and abs(self.create_time.day - other.create_time.day) == 0 \
                and  self._bare_text == other._bare_text:
            return True
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        if self.category == config.CATE_QQWEIBO_STATUS and self.get_retweeted_data():
            return int(self.id)
        if (self.category == config.CATE_SINA_STATUS or self.category == config.CATE_DOUBAN_STATUS) \
                and self.get_retweeted_data():
            return int(self.id)
        if self.category == config.CATE_DOUBAN_STATUS and \
                self.get_data() and self.get_data().get_attachments():
            return int(self.id)
        if self.category == config.CATE_THEPAST_NOTE:
            return int(self.id)
        if self.category == config.CATE_RENREN_STATUS or \
                self.category == config.CATE_RENREN_BLOG or \
                self.category == config.CATE_RENREN_ALBUM or \
                self.category == config.CATE_RENREN_PHOTO or \
                self.category == config.CATE_INSTAGRAM_STATUS:
            return int(self.id)
        s = u"%s%s%s" % (self.user_id, self._bare_text, self.create_time.day)
        d = hashlib.md5()
        d.update(s.encode("utf8"))
        return int(d.hexdigest(),16)
        
    def _generate_bare_text(self, offset=140):
        bare_text = self.summary[:offset]
        bare_text = clear_html_element(bare_text).replace(u"《", "").replace(u"》", "").replace("amp;","")
        bare_text = re.sub("\s", "", bare_text)
        bare_text = re.sub("http://t.cn/[a-zA-Z0-9]+", "", bare_text)
        bare_text = re.sub("http://t.co/[a-zA-Z0-9]+", "", bare_text)
        bare_text = re.sub("http://url.cn/[a-zA-Z0-9]+", "", bare_text)
        bare_text = re.sub("http://goo.gl/[a-zA-Z0-9]+", "", bare_text)
        bare_text = re.sub("http://dou.bz/[a-zA-Z0-9]+", "", bare_text).replace(u"说：", "")
        return bare_text  

    ##TODO:这个clear_cache需要拆分
    @classmethod
    def _clear_cache(cls, user_id, status_id, cate=""):
        if status_id:
            mc.delete("status:%s" % status_id)
        if user_id:
            mc.delete("status_ids:user:%scate:" % user_id)
            if cate:
                mc.delete("status_ids:user:%scate:%s" % (user_id, cate))

    def privacy(self):
        if self.category == config.CATE_THEPAST_NOTE:
            note = Note.get(self.origin_id)
            return note and note.privacy
        else:
            return consts.STATUS_PRIVACY_PUBLIC
        
    @property
    def text(self):
        if self.category == config.CATE_THEPAST_NOTE:
            note = Note.get(self.origin_id)
            return note and note.content
        else:
            r = RawStatus.get(self.id)
            _text = r.text if r else ""
            return json_decode(_text) if _text else ""

    @property
    def raw(self):
        if self.category == config.CATE_THEPAST_NOTE:
            note = Note.get(self.origin_id)
            return note
        else:
            r = RawStatus.get(self.id)
            _raw = r.raw if r else ""
            try:
                return json_decode(_raw) if _raw else ""
            except:
                return ""
        
    @classmethod
    def add(cls, user_id, origin_id, create_time, site, category, title, 
            text=None, raw=None):
        status = None
        cursor = None
        try:
            cursor = db_conn.execute("""insert into status 
                    (user_id, origin_id, create_time, site, category, title)
                    values (%s,%s,%s,%s,%s,%s)""",
                    (user_id, origin_id, create_time, site, category, title))
            status_id = cursor.lastrowid
            if status_id > 0:
                text = json_encode(text) if text is not None else ""
                raw = json_encode(raw) if raw is not None else ""
                RawStatus.set(status_id, text, raw)
                db_conn.commit()
                status = cls.get(status_id)
        except IntegrityError:
            log.warning("add status duplicated, uniq key is %s:%s:%s, ignore..." %(origin_id, site, category))
            db_conn.rollback()
        finally:
            cls._clear_cache(user_id, None, cate=category)
            cursor and cursor.close()

        return status

    @classmethod
    def add_from_obj(cls, user_id, d, raw=None):
        origin_id = d.get_origin_id()
        create_time = d.get_create_time()
        title = d.get_title()
        content = d.get_content()

        site = d.site
        category = d.category
        user_id = user_id

        cls.add(user_id, origin_id, create_time, site, category, 
                title, content, raw)

    @classmethod
    @cache("status:{status_id}")
    def get(cls, status_id):
        status = None
        cursor = db_conn.execute("""select user_id, origin_id, create_time, site, 
                category, title from status 
                where id=%s""", status_id)
        row = cursor.fetchone()
        if row:
            status = cls(status_id, *row)
        cursor and cursor.close()

        if status and status.category == config.CATE_THEPAST_NOTE:
            note = Note.get(status.origin_id)
            status.title = note and note.title

        return status

    @classmethod
    @pcache("status_ids:user:{user_id}cate:{cate}")
    def get_ids(cls, user_id, start=0, limit=20, cate=""):
        return cls._get_ids(user_id, start, limit, 
                order="create_time desc", cate=cate)

    @classmethod
    @pcache("status_ids_asc:user:{user_id}cate:{cate}")
    def get_ids_asc(cls, user_id, start=0, limit=20, cate=""):
        return cls._get_ids(user_id, start, limit, 
                order="create_time", cate=cate)

    @classmethod
    def _get_ids(cls, user_id, start=0, limit=20, order="create_time desc", cate=""):
        cursor = None
        if not user_id:
            return []
        if cate:
            if str(cate) == str(config.CATE_DOUBAN_NOTE):
                return []
            sql = """select id from status where user_id=%s and category=%s
                    order by """ + order + """ limit %s,%s""" 
            cursor = db_conn.execute(sql, (user_id, cate, start, limit))
        else:
            sql = """select id from status where user_id=%s and category!=%s
                    order by """ + order + """ limit %s,%s""" 
            cursor = db_conn.execute(sql, (user_id, config.CATE_DOUBAN_NOTE, start, limit))
        rows = cursor.fetchall()
        cursor and cursor.close()
        return [x[0] for x in rows]

    @classmethod
    def get_ids_by_date(cls, user_id, start_date, end_date):
        cursor = db_conn.execute('''select id from status 
                where user_id=%s and category!=%s and create_time>=%s and create_time<=%s
                order by create_time desc''',
                (user_id, config.CATE_DOUBAN_NOTE, start_date, end_date))
        rows = cursor.fetchall()
        cursor and cursor.close()
        return [x[0] for x in rows]

    @classmethod
    def gets(cls, ids):
        return [cls.get(x) for x in ids]

    @classmethod
    @cache("recent_updated_users", expire=HALF_HOUR)
    def get_recent_updated_user_ids(cls, limit=16):
        cursor = db_conn.execute('''select distinct user_id from status 
                order by create_time desc limit %s''', limit)
        rows = cursor.fetchall()
        cursor and cursor.close()
        return [row[0]for row in rows]

    @classmethod
    def get_max_origin_id(cls, cate, user_id):
        cursor = db_conn.execute('''select origin_id from status 
            where category=%s and user_id=%s 
            order by length(origin_id) desc, origin_id desc limit 1''', (cate, user_id))
        row = cursor.fetchone()
        cursor and cursor.close()
        if row:
            return row[0]
        else:
            return None

    @classmethod
    def get_min_origin_id(cls, cate, user_id):
        cursor = db_conn.execute('''select origin_id from status 
            where category=%s and user_id=%s 
            order by length(origin_id), origin_id limit 1''', (cate, user_id))
        row = cursor.fetchone()
        cursor and cursor.close()
        if row:
            return row[0]
        else:
            return None

    ## just for tecent_weibo
    @classmethod
    def get_oldest_create_time(cls, cate, user_id):
        if cate:
            cursor = db_conn.execute('''select min(create_time) from status 
                where category=%s and user_id=%s''', (cate, user_id))
        else:
            cursor = db_conn.execute('''select min(create_time) from status 
                where user_id=%s''', user_id)
        row = cursor.fetchone()
        cursor and cursor.close()
        if row:
            return row[0]
        else:
            return None
    
    @classmethod
    def get_count_by_cate(cls, cate, user_id):
        cursor = db_conn.execute('''select count(1) from status 
            where category=%s and user_id=%s''', (cate, user_id))
        row = cursor.fetchone()
        cursor and cursor.close()
        if row:
            return row[0]
        else:
            return 0

    @classmethod
    def get_count_by_user(cls, user_id):
        cursor = db_conn.execute('''select count(1) from status 
            where user_id=%s''', user_id)
        row = cursor.fetchone()
        cursor and cursor.close()
        if row:
            return row[0]
        else:
            return 0

    #TODO:每次新增第三方，需要修改这里
    def get_data(self):
        if self.category == config.CATE_DOUBAN_MINIBLOG:
            return DoubanMiniBlogData(self.raw)
        elif self.category == config.CATE_DOUBAN_NOTE:
            return DoubanNoteData(self.raw)
        elif self.category == config.CATE_SINA_STATUS:
            return SinaWeiboStatusData(self.raw)
        elif self.category == config.CATE_TWITTER_STATUS:
            return TwitterStatusData(self.raw)
        elif self.category == config.CATE_QQWEIBO_STATUS:
            return QQWeiboStatusData(self.raw)
        elif self.category == config.CATE_DOUBAN_STATUS:
            return DoubanStatusData(self.raw)
        elif self.category == config.CATE_WORDPRESS_POST:
            return WordpressData(self.raw)
        elif self.category == config.CATE_THEPAST_NOTE:
            return ThepastNoteData(self.raw)
        elif self.category == config.CATE_RENREN_STATUS:
            return RenrenStatusData(self.raw)
        elif self.category == config.CATE_RENREN_BLOG:
            return RenrenBlogData(self.raw)
        elif self.category == config.CATE_RENREN_ALBUM:
            return RenrenAlbumData(self.raw)
        elif self.category == config.CATE_RENREN_PHOTO:
            return RenrenPhotoData(self.raw)
        elif self.category == config.CATE_INSTAGRAM_STATUS:
            return InstagramStatusData(self.raw)
        else:
            return None

    def get_origin_uri(self):
        ##d是AbsData的子类实例
        d = self.get_data()
        if self.category == config.CATE_DOUBAN_MINIBLOG or \
                self.category == config.CATE_DOUBAN_STATUS:
            ua = UserAlias.get_by_user_and_type(self.user_id, 
                    config.OPENID_TYPE_DICT[config.OPENID_DOUBAN])
            if ua:
                return (config.OPENID_DOUBAN, 
                        config.DOUBAN_MINIBLOG % (ua.alias, self.origin_id))
        elif self.category == config.CATE_DOUBAN_NOTE:
            return (config.OPENID_DOUBAN, config.DOUBAN_NOTE % self.origin_id)
        elif self.category == config.CATE_SINA_STATUS:
            return (config.OPENID_SINA, "")
        elif self.category == config.CATE_TWITTER_STATUS:
            return (config.OPENID_TWITTER, d.get_origin_uri())
        elif self.category == config.CATE_QQWEIBO_STATUS:
            return (config.OPENID_QQ, config.QQWEIBO_STATUS % self.origin_id)
        elif self.category == config.CATE_WORDPRESS_POST:
            return (config.OPENID_WORDPRESS, d.get_origin_uri())
        elif self.category == config.CATE_THEPAST_NOTE:
            return (config.OPENID_THEPAST, d.get_origin_uri())
        elif self.category == config.CATE_RENREN_STATUS or \
                self.category == config.CATE_RENREN_BLOG or \
                self.category == config.CATE_RENREN_ALBUM or \
                self.category == config.CATE_RENREN_PHOTO:
            return (config.OPENID_RENREN, d.get_origin_uri())
        elif self.category == config.CATE_INSTAGRAM_STATUS:
            return (config.OPENID_INSTAGRAM, d.get_origin_uri())
        else:
            return None

    def get_retweeted_data(self):
        d = self.get_data()
        if hasattr(d, "get_retweeted_data"):
            return d.get_retweeted_data()
        return None

    def get_thepast_user(self):
        return User.get(self.user_id)


## Sycktask: 用户添加的同步任务
class SyncTask(object):
    kind = config.K_SYNCTASK

    def __init__(self, id, category, user_id, time):
        self.id = str(id)
        self.category = category
        self.user_id = str(user_id)
        self.time = time

    def __repr__(self):
        return "<SyncTask id=%s, user_id=%s, cate=%s>" \
            %(self.id, self.user_id, self.category)
    __str__ = __repr__

    @classmethod
    def add(cls, category, user_id):
        task = None
        cursor = None
        try:
            cursor = db_conn.execute("""insert into sync_task
                    (category, user_id) values (%s,%s)""",
                    (category, user_id))
            db_conn.commit()
            task_id = cursor.lastrowid
            task = cls.get(task_id)
        except IntegrityError:
            db_conn.rollback()
        finally:
            cursor and cursor.close()

        return task

    @classmethod
    def get(cls, id):
        task = None
        cursor = db_conn.execute("""select category,user_id,time from sync_task
                where id=%s limit 1""", id) 
        row = cursor.fetchone()
        if row:
            task = cls(id, *row)
        cursor and cursor.close()

        return task
    
    @classmethod
    def get_ids(cls):
        cursor = db_conn.execute("""select id from sync_task""") 
        r = [row[0] for row in cursor.fetchall()]
        cursor and cursor.close()
        return r
    
    @classmethod
    def gets(cls, ids):
        return [cls.get(x) for x in ids]

    @classmethod
    def gets_by_user(cls, user):
        cursor = db_conn.execute("""select id from sync_task where user_id = %s""", user.id)
        rows = cursor.fetchall()
        cursor and cursor.close()
        return [cls.get(row[0] )for row in rows]

    @classmethod
    def gets_by_user_and_cate(cls,user,cate):
        tasks = cls.gets_by_user(user)
        return [x for x in tasks if str(x.category) == cate]

    def remove(self):
        cursor = db_conn.execute("""delete from sync_task
                where id=%s""", self.id) 
        db_conn.commit()
        cursor and cursor.close()
        return None
    
class TaskQueue(object):
    kind = config.K_TASKQUEUE

    def __init__(self, id, task_id, task_kind, time):
        self.id = str(id)
        self.task_id = str(task_id)
        self.task_kind = task_kind
        self.time = time

    @classmethod
    def add(cls, task_id, task_kind):
        task = None
        cursor = None
        try:
            cursor = db_conn.execute("""insert into task_queue
                    (task_id, task_kind) values (%s,%s)""",
                    (task_id, task_kind))
            db_conn.commit()
            task = cls.get(cursor.lastrowid)
        except IntegrityError:
            db_conn.rollback()
        finally:
            cursor and cursor.close()

        return task

    @classmethod
    def get(cls, id):
        task = None
        cursor = db_conn.execute("""select id, task_id, task_kind, time from task_queue
                where id=%s limit 1""", id) 
        row = cursor.fetchone()
        if row:
            task = cls(*row)
        cursor and cursor.close()

        return task
    
    @classmethod
    def get_all_ids(cls):
        cursor = db_conn.execute("""select id from task_queue order by time""") 
        r = [row[0] for row in cursor.fetchall()]
        cursor and cursor.close()
        return r

    def remove(self):
        cursor = db_conn.execute("""delete from task_queue
                where id=%s""", self.id) 
        db_conn.commit()
        cursor and cursor.close()
        
## functions
def get_all_text_by_user(user_id, limit=1000):
    text = ""
    status_ids = Status.get_ids(user_id, limit=limit)
    for s in Status.gets(status_ids):
        try:
            ##TODO:这里用的summary，是为了效率上的考虑
            _t = s.summary

            retweeted_data = s.get_retweeted_data()
            if retweeted_data:
                if isinstance(retweeted_data, basestring):
                    _t += retweeted_data
                else:
                    _t += retweeted_data.get_content()
            text += _t
        except Exception, e:
            print e
    return text

@cache("sids:{user_id}:{now}", expire=3600*24)
def get_status_ids_yesterday(user_id, now):
    s = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    e = now.strftime("%Y-%m-%d")
    ids = Status.get_ids_by_date(user_id, s, e)
    return ids

@cache("sids_today_in_history:{user_id}:{now}", expire=3600*24)
def get_status_ids_today_in_history(user_id, now):
    years = range(now.year-1, 2005, -1)
    dates = [("%s-%s" %(y,now.strftime("%m-%d")), 
        "%s-%s" %(y,(now+datetime.timedelta(days=1)).strftime("%m-%d"))) for y in years]
    ids = [Status.get_ids_by_date(user_id, d[0], d[1]) for d in dates]
    r =[]
    for x in ids:
        r.extend(x)
    return r


########NEW FILE########
__FILENAME__ = user
#-*- coding:utf-8 -*-

import re
from MySQLdb import IntegrityError
from past.corelib.cache import cache, pcache
from past.store import mc, db_conn
from past.utils import randbytes
from past.utils.escape import json_decode, json_encode
from .kv import Kv, UserProfile
from past import config

class User(object):
    UID_RE = r'^[a-z][0-9a-zA-Z_.-]{3,15}'
    UID_MAX_LEN = 16
    UID_MIN_LEN = 4

    def __init__(self, id):
        self.id = str(id)
        self.uid = None
        self.name = None
        self.create_time = None
        self.session_id = None
    
    def __repr__(self):
        return "<User id=%s, uid=%s, session_id=%s>" \
                % (self.id, self.uid, self.session_id)
    __str__ = __repr__

    @classmethod
    def _clear_cache(cls, user_id):
        if user_id:
            mc.delete("user:%s" % user_id)
            UserProfile.clear_cache(user_id)
        mc.delete("user:ids")
        
    @classmethod
    @cache("user:{id}")
    def get(cls, id):
        uid = None
        if isinstance(id, basestring) and not id.isdigit():
            uid = id
        cursor = None
        if uid:
            cursor = db_conn.execute("""select id, uid,name,session_id,time 
                from user where uid=%s""", uid)
        else:
            cursor = db_conn.execute("""select id, uid,name,session_id,time 
                from user where id=%s""", id)
        row = cursor.fetchone()
        cursor and cursor.close()
        if row:
            u = cls(row[0])
            u.uid = str(row[1])
            u.name = row[2]
            u.session_id = row[3]
            u.create_time = row[4]
            return u

        return None

    @classmethod
    @cache("email2user:{email}")
    def get_user_by_email(cls, email):
        cursor = db_conn.execute('''select user_id from passwd 
                where email=%s''', email)
        row = cursor.fetchone()
        cursor and cursor.close()
        return row and cls.get(row[0])

    @classmethod
    @cache("alias2user:{type_}{alias}")
    def get_user_by_alias(cls, type_, alias):
        cursor = db_conn.execute('''select user_id from user_alias
            where type=%s and alias=%s''', (type_, alias))
        row = cursor.fetchone()
        cursor and cursor.close()
        return row and cls.get(row[0])

    @classmethod
    def gets(cls, ids):
        return [cls.get(x) for x in ids]

    @classmethod
    @pcache("user:ids")
    def get_ids(cls, start=0, limit=20):
        sql = """select id from user 
                order by id desc limit %s, %s"""
        cursor = db_conn.execute(sql, (start, limit))
        rows = cursor.fetchall()
        cursor and cursor.close()
        return [x[0] for x in rows]

    @classmethod
    @pcache("user:ids:asc")
    def get_ids_asc(cls, start=0, limit=20):
        sql = """select id from user 
                order by id asc limit %s, %s"""
        cursor = db_conn.execute(sql, (start, limit))
        rows = cursor.fetchall()
        cursor and cursor.close()
        return [x[0] for x in rows]

    def get_alias(self):
        return UserAlias.gets_by_user_id(self.id)
    
    @cache("user_email:{self.id}")
    def get_email(self):
        cursor = db_conn.execute('''select email from passwd 
                where user_id=%s''', self.id)
        row = cursor.fetchone()
        cursor and cursor.close()
        return row and row[0]

    def set_email(self, email):
        cursor = None
        try:
            cursor = db_conn.execute('''replace into passwd (user_id, email) values (%s,%s)''',
                    (self.id, email))
            db_conn.commit()
            return True
        except IntegrityError:
            db_conn.rollback()
            return False
        finally:
            mc.delete("user_email:%s" % self.id)
            cursor and cursor.close()
            
    @classmethod
    def add(cls, name=None, uid=None, session_id=None):
        cursor = None
        user = None

        name = "" if name is None else name
        uid = "" if uid is None else uid
        session_id = session_id if session_id else randbytes(8)

        try:
            cursor = db_conn.execute("""insert into user (uid, name, session_id) 
                values (%s, %s, %s)""", 
                (uid, name, session_id))
            user_id = cursor.lastrowid
            if uid == "":
                cursor = db_conn.execute("""update user set uid=%s where id=%s""", 
                    (user_id, user_id), cursor=cursor)
            db_conn.commit()
            cls._clear_cache(None)
            user = cls.get(user_id)
        except IntegrityError:
            db_conn.rollback()
        finally:
            cursor and cursor.close()

        return user

    def clear_session(self):
        self.update_session(None)

    def update_session(self, session_id):
        cursor = db_conn.execute("""update user set session_id=%s where id=%s""", 
                (session_id, self.id))
        cursor and cursor.close()
        db_conn.commit()
        User._clear_cache(self.id)

    def update_uid(self, uid):
        assert isinstance(uid, basestring)
        if self.id != self.uid:
            return False, "already_set"

        if uid == self.uid:
            return True, "same_with_old"

        if len(uid) > User.UID_MAX_LEN:
            return False, u"太长了，不能超过%s" %User.UID_MAX_LEN
        if len(uid) < User.UID_MIN_LEN:
            return False, u"太短了，不能小于%s" %User.UID_MIN_LEN
        uid_re = re.compile(User.UID_RE)
        if not uid_re.match(uid):
            return False, u"只能包括字母数字和.-_"
        
        uid = uid.lower()
        if uid in ["user", "pdf", "explore", "home", "visual", "settings", "admin", "past", "connect", "bind",
            "i", "notes", "note", "status", "share", "timeline", "post", "login", "logout", "sync", "about", 
            "connect", "dev", "api", "thepast", "thepast.me", ]:
            return False, u"被系统占用了:)"
            
        try:
            cursor = db_conn.execute("""update user set uid=%s where id=%s""", 
                    (uid, self.id))
            db_conn.commit()
            User._clear_cache(self.id)
            return True, u"设置成功"
        except IntegrityError:
            db_conn.rollback()
            return False, u"被别人占用了:)"
        finally:
            cursor and cursor.close()

        return False, "fail"
            

    def set_profile(self, profile):
        UserProfile.set(self.id, json_encode(profile))
        return self.get_profile()

    def get_profile(self):
        r = UserProfile.get(self.id)
        p = r.val if r else ""
        try:
            return json_decode(p) if p else {}
        except ValueError, e:
            print '------decode profile fail:', e
            return {}
    
    def set_profile_item(self, k, v):
        p = self.get_profile()
        p[k] = v
        self.set_profile(p)
        return self.get_profile()

    def get_profile_item(self, k):
        profile = self.get_profile()
        return profile and profile.get(k)

    ##获取第三方帐号的profile信息
    def get_thirdparty_profile(self, openid_type):
        p = self.get_profile_item(openid_type)
        if isinstance(p, dict):
            return p
        else:
            r = json_decode(p) if p else {}
            return r

    def set_thirdparty_profile_item(self, openid_type, k, v):
        p = self.get_thirdparty_profile(openid_type)
        p[k] = v
        self.set_profile_item(openid_type, p)
        
    def get_avatar_url(self):
        return self.get_profile().get("avatar_url", "")

    def set_avatar_url(self, url):
        return self.set_profile_item("avatar_url", url)

    def get_icon_url(self):
        return self.get_profile().get("icon_url", "")

    def set_icon_url(self, url):
        return self.set_profile_item("icon_url", url)

    def is_pdf_ready(self):
        from past.utils.pdf import is_user_pdf_file_exists
        return is_user_pdf_file_exists(self.id)

    def get_dev_tokens(self):
        from past.model.user_tokens import UserTokens
        ids = UserTokens.get_ids_by_user_id(self.id)
        return [UserTokens.get(x) for x in ids] or []

class UserAlias(object):

    def __init__(self, id_, type_, alias, user_id):
        self.id = id_
        self.type = type_
        self.alias = alias
        self.user_id = str(user_id)

    def __repr__(self):
        return "<UserAlias type=%s, alias=%s, user_id=%s>" \
                % (self.type, self.alias, self.user_id)
    __str__ = __repr__

    @classmethod
    def get_by_id(cls, id):
        ua = None
        cursor = db_conn.execute("""select `id`, `type`, alias, user_id from user_alias 
                where id=%s""", id)
        row = cursor.fetchone()
        if row:
            ua = cls(*row)
        cursor and cursor.close()

        return ua

    @classmethod
    def get(cls, type_, alias):
        ua = None
        cursor = db_conn.execute("""select `id`, user_id from user_alias 
                where `type`=%s and alias=%s""", 
                (type_, alias))
        row = cursor.fetchone()
        if row:
            ua = cls(row[0], type_, alias, row[1])
        cursor and cursor.close()

        return ua

    @classmethod
    def gets_by_user_id(cls, user_id):
        uas = []
        cursor = db_conn.execute("""select `id`, `type`, alias from user_alias 
                where user_id=%s""", user_id)
        rows = cursor.fetchall()
        if rows and len(rows) > 0:
            uas = [cls(row[0], row[1], row[2], user_id) for row in rows]
        cursor and cursor.close()

        return uas

    @classmethod
    def get_ids(cls, start=0, limit=0):
        ids = []
        if limit == 0:
            limit = 100000000
        cursor = db_conn.execute("""select `id` from user_alias 
                limit %s, %s""", (start, limit))
        rows = cursor.fetchall()
        if rows and len(rows) > 0:
            ids = [row[0] for row in rows]
        cursor and cursor.close()

        return ids

    @classmethod
    def get_by_user_and_type(cls, user_id, type_):
        uas = cls.gets_by_user_id(user_id)
        for x in uas:
            if x.type == type_:
                return x
        return None

    @classmethod
    def bind_to_exists_user(cls, user, type_, alias):
        ua = cls.get(type_, alias)
        if ua:
            return None

        ua = None
        cursor = None
        try:
            cursor = db_conn.execute("""insert into user_alias (`type`,alias,user_id) 
                    values (%s, %s, %s)""", (type_, alias, user.id))
            db_conn.commit()
            ua = cls.get(type_, alias)
        except IntegrityError:
            db_conn.rollback()
        finally:
            cursor and cursor.close()

        return ua

    @classmethod
    def create_new_user(cls, type_, alias, name=None):
        if cls.get(type_, alias):
            return None

        user = User.add(name)
        if not user:
            return None

        return cls.bind_to_exists_user(user, type_, alias)

    def get_homepage_url(self):
        if self.type == config.OPENID_TYPE_DICT[config.OPENID_DOUBAN]:
            return config.OPENID_TYPE_NAME_DICT[self.type], \
                    "%s/people/%s" %(config.DOUBAN_SITE, self.alias), \
                    config.OPENID_DOUBAN

        if self.type == config.OPENID_TYPE_DICT[config.OPENID_SINA]:
            return config.OPENID_TYPE_NAME_DICT[self.type], \
                    "%s/%s" %(config.SINA_SITE, self.alias), \
                    config.OPENID_SINA

        ##FIXME:twitter的显示的不对
        if self.type == config.OPENID_TYPE_DICT[config.OPENID_TWITTER]:
            u = User.get(self.user_id)
            return config.OPENID_TYPE_NAME_DICT[self.type],\
                    "%s/#!%s" %(config.TWITTER_SITE, u.name),\
                    config.OPENID_TWITTER

        if self.type == config.OPENID_TYPE_DICT[config.OPENID_QQ]:
            ##XXX:腾讯微博比较奇怪
            return config.OPENID_TYPE_NAME_DICT[self.type],\
                    "%s/%s" %(config.QQWEIBO_SITE, \
                    User.get(self.user_id).get_thirdparty_profile(self.type).get("uid", "")), \
                    config.OPENID_QQ

        if self.type == config.OPENID_TYPE_DICT[config.OPENID_WORDPRESS]:
            ##FIXME: wordpress显示rss地址代替blog地址
            return config.OPENID_TYPE_NAME_DICT[self.type],\
                    self.alias, config.OPENID_WORDPRESS
        if self.type == config.OPENID_TYPE_DICT[config.OPENID_RENREN]:
            return config.OPENID_TYPE_NAME_DICT[self.type],\
                    "%s/%s" %(config.RENREN_SITE, self.alias), config.OPENID_RENREN
        if self.type == config.OPENID_TYPE_DICT[config.OPENID_INSTAGRAM]:
            user = User.get_user_by_alias(self.type, self.alias)
            profile = user and user.get_thirdparty_profile(self.type)
            uid = profile and profile.get("uid", "")
            return config.OPENID_TYPE_NAME_DICT[self.type],\
                    config.INSTAGRAM_USER_PAGE %uid, config.OPENID_INSTAGRAM


class OAuth2Token(object):
   
    def __init__(self, alias_id, access_token, refresh_token):
        self.alias_id = alias_id
        self.access_token = access_token
        self.refresh_token = refresh_token

    @classmethod
    def get(cls, alias_id):
        ot = None
        cursor = db_conn.execute("""select access_token, refresh_token  
                from oauth2_token where alias_id=%s order by time desc limit 1""", 
                (alias_id,))
        row = cursor.fetchone()
        if row:
            ot = cls(alias_id, row[0], row[1])
        cursor and cursor.close()
        return ot

    @classmethod
    def add(cls, alias_id, access_token, refresh_token):
        ot = None
        cursor = None
        try:
            cursor = db_conn.execute("""replace into oauth2_token 
                    (alias_id, access_token, refresh_token)
                    values (%s, %s, %s)""", 
                    (alias_id, access_token, refresh_token))
            db_conn.commit()
            ot = cls.get(alias_id)
        except IntegrityError:
            db_conn.rollback()
        finally:
            cursor and cursor.close()

        return ot


class Confirmation(object):
    def __init__(self, random_id, text, time):
        self.random_id = random_id
        self.text = text
        self.time = time
    
    @classmethod
    def get_by_random_id(cls, random_id):
        cursor = db_conn.execute('''select text, time from confirmation 
                where random_id=%s''', random_id)
        row = cursor.fetchone()
        cursor and cursor.close()
        if row:
            return cls(random_id, row[0], row[1])
    
    def delete(self):
        Confirmation.delete_by_random_id(self.random_id)

    @classmethod
    def delete_by_random_id(cls, random_id):
        db_conn.execute('''delete from confirmation 
                where random_id=%s''', random_id)
        db_conn.commit()

    @classmethod
    def add(cls, random_id, text):
        cursor = None
        try:
            cursor = db_conn.execute('''insert into confirmation (random_id, text) values(%s, %s)''',
                    (random_id, text))
            db_conn.commit()
            return True
        except IntegrityError:
            db_conn.rollback()
        finally:
            cursor and cursor.close()


class PdfSettings(object):
    def __init__(self, user_id, time):
        self.user_id = user_id
        self.time = time

    @classmethod
    def _clear_cache(cls, user_id=None):
        if user_id:
            mc.delete("pdf_settings:u%s" % user_id)
        mc.delete("pdf_settings:all_uids")
            

    @classmethod
    @cache("pdf_settings:all_uids")
    def get_all_user_ids(cls):
        cursor = db_conn.execute('''select user_id from pdf_settings''')
        rows = cursor.fetchall()
        cursor and cursor.close()
        return [str(row[0]) for row in rows]

    @classmethod
    @cache("pdf_settings:u{user_id}")
    def is_user_id_exists(cls, user_id):
        cursor = db_conn.execute('''select user_id from pdf_settings where user_id=%s''', user_id)
        row = cursor.fetchone()
        cursor and cursor.close()
        return True if row else False

    @classmethod
    def add_user_id(cls, user_id):
        cursor = None
        try:
            cursor = db_conn.execute('''insert into pdf_settings (user_id) values (%s)''', user_id)
            db_conn.commit()
            cls._clear_cache(user_id)
            return True
        except IntegrityError:
            db_conn.rollback()
        finally:
            cursor and cursor.close()

    @classmethod
    def remove_user_id(cls, user_id):
        cursor = db_conn.execute('''delete from pdf_settings where user_id=%s''', user_id)
        db_conn.commit()
        cls._clear_cache(user_id)


########NEW FILE########
__FILENAME__ = user_tokens
#-*- coding:utf-8 -*-
# for dev -> api

from MySQLdb import IntegrityError
from past.corelib.cache import cache, pcache
from past.store import mc, db_conn

class UserTokens(object):
    def __init__(self, id, user_id, token, device):
        self.id = id
        self.user_id = str(user_id)
        self.token = str(token)
        self.device = device

    def __repr__(self):
        return "<UserTokens id=%s, user_id=%s, token=%s, device=%s>" \
                % (self.id, self.user_id, self.token, self.device)
    __str__ = __repr__

    @classmethod
    @cache("user_token:{id}")
    def get(cls, id):
        return cls._find_by("id", id)

    @classmethod
    @cache("user_token:{token}")
    def get_by_token(cls, token):
        return cls._find_by("token", token)

    @classmethod
    @cache("user_token_ids:{user_id}")
    def get_ids_by_user_id(cls, user_id):
        r = cls._find_by("user_id", user_id, limit=0)
        if r:
            return [r.id for x in r]
        else:
            return []
    
    @classmethod
    def add(cls, user_id, token, device=""):
        cursor = None
        try:
            cursor = db_conn.execute('''insert into user_tokens (user_id, token, device)
                    values (%s, %s, %s)''', (user_id, token, device))
            id_ = cursor.lastrowid
            db_conn.commit()
            return cls.get(id_)
        except IntegrityError:
            db_conn.rollback()
        finally:
            cursor and cursor.close()

    def remove(self):
        db_conn.execute('''delete from user_tokens where id=%s''', self.id)
        db_conn.commit()
        self._clear_cache()

    def _clear_cache(self):
        mc.delete("user_token:%s" % self.id)
        mc.delete("user_token:%s" % self.token)
        mc.delete("user_token_ids:%s" % self.user_id)

    @classmethod
    def _find_by(cls, col, value, start=0, limit=1):
        assert limit >= 0
        if limit == 0:
            cursor = db_conn.execute("""select id, user_id, token, device 
                    from user_tokens where `""" + col + """`=%s""", value)
        else:
            cursor = db_conn.execute("""select id, user_id, token, device 
                    from user_tokens where `""" + col + """`=%s limit %s, %s""", (value, start, limit))
        if limit == 1:
            row = cursor.fetchone()
            cursor and cursor.close()
            return row and cls(*row)
        else:
            rows = cursor.fetchall()
            cursor and cursor.close()
            return [cls(*row) for row in rows]

########NEW FILE########
__FILENAME__ = weixin
#-*- coding:utf-8 -*-

from MySQLdb import IntegrityError
from past.corelib.cache import cache, pcache
from past.store import mc, db_conn

class UserWeixin(object):
    def __init__(self, user_id, weixin_name):
        self.user_id = str(user_id)
        self.weixin_name = weixin_name

    def __repr__(self):
        return "<UserWeixin user_id=%s, weixin_name=%s>" \
                %(self.user_id, self.weixin_name)
    __str__ = __repr__

    @classmethod
    @cache("user_weixin:{weixin_name}")
    def get_by_weixin(cls, weixin_name):
        return cls._find_by("weixin_name", weixin_name)
    
    @classmethod
    def add(cls, user_id, weixin_name):
        cursor = None
        try:
            cursor = db_conn.execute('''insert into user_weixin (user_id, weixin_name)
                    values (%s, %s) on duplicate key update user_id=%s''', (user_id, weixin_name, user_id))
            db_conn.commit()
            cls.clear_cache(user_id, weixin_name)
            return cls.get_by_weixin(weixin_name)
        except IntegrityError:
            db_conn.rollback()
        finally:
            cursor and cursor.close()

    @classmethod
    def clear_cache(cls, user_id, weixin_name):
        mc.delete("user_weixin:%s" % weixin_name)

    @classmethod
    def _find_by(cls, col, value, start=0, limit=1):
        assert limit >= 0
        if limit == 0:
            cursor = db_conn.execute("""select user_id, weixin_name
                    from user_weixin where `""" + col + """`=%s""", value)
        else:
            cursor = db_conn.execute("""select user_id, weixin_name
                    from user_weixin where `""" + col + """`=%s limit %s, %s""", (value, start, limit))
        if limit == 1:
            row = cursor.fetchone()
            cursor and cursor.close()
            return row and cls(*row)
        else:
            rows = cursor.fetchall()
            cursor and cursor.close()
            return [cls(*row) for row in rows]

########NEW FILE########
__FILENAME__ = store
#-*- coding:utf-8 -*-

import os
import commands
import datetime

import MySQLdb
import redis
import memcache

from past.utils.escape import json_decode, json_encode
from past import config 

def init_db():
    cmd = """mysql -h%s -P%s -u%s -p%s < %s""" \
        % (config.DB_HOST, config.DB_PORT, 
            config.DB_USER, config.DB_PASSWD,
            os.path.join(os.path.dirname(__file__), "schema.sql"))
    status, output = commands.getstatusoutput(cmd)

    if status != 0:
        print "init_db fail, output is: %s" % output   

    return status
        
def connect_db():
    try:
        conn = MySQLdb.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            passwd=config.DB_PASSWD,
            db=config.DB_NAME,
            use_unicode=True,
            charset="utf8")
        return conn
    except Exception, e:
        print "connect db fail:%s" % e
        return None

def connect_redis():
    return redis.Redis(config.REDIS_HOST, config.REDIS_PORT)

def connect_redis_cache():
    return redis.Redis(config.REDIS_CACHE_HOST, config.REDIS_CACHE_PORT)

def connect_mongo(dbname="thepast"):
    import pymongo
    conn = pymongo.connection.Connection('localhost')
    db = conn.thepast
    db = getattr(conn, dbname)
    return db and getattr(db, dbname)

class MongoDB(object):
    def __init__(self, dbname="thepast"):
        self.dbname = dbname
        self._conn = connect_mongo(self.dbname)

    def connect(self):
        self._conn = connect_mongo(self.dbname)
        return self._conn

    def get(self, k):
        d = {"k":k}
        r = self._conn.find_one(d)
        if r:
            return r.get("v")
        return None

    def mget(self, keys):
        d = {"k": {"$in" : keys}}
        rs = self._conn.find(d)
        return [r["v"] for r in rs]

    def set(self, k, v):
        self._conn.update({"k":k},{"k":k, "v":v}, upsert=True)

    def remove(self, k):
        self._conn.remove({"k":k})

    def get_connection(self):
        return self._conn or self.connect()

class DB(object):
    
    def __init__(self):
        self._conn = connect_db()

    def connect(self):
        self._conn = connect_db()
        return self._conn

    def execute(self, *a, **kw):
        cursor = kw.pop('cursor', None)
        try:
            cursor = cursor or self._conn.cursor()
            cursor.execute(*a, **kw)
        except (AttributeError, MySQLdb.OperationalError):
            print 'debug, %s re-connect to mysql' % datetime.datetime.now()
            self._conn and self._conn.close()
            self.connect()
            cursor = self._conn.cursor()
            cursor.execute(*a, **kw)
        return cursor
        
    def commit(self):
        return self._conn and self._conn.commit()

    def rollback(self):
        return self._conn and self._conn.rollback()

def connect_memcached():
    mc = memcache.Client(['%s:%s' % (config.MEMCACHED_HOST, config.MEMCACHED_PORT)], debug=0)
    return mc

db_conn = DB()
mc = redis_cache_conn = connect_memcached()
#redis_conn = connect_redis()
#mongo_conn = MongoDB()

########NEW FILE########
__FILENAME__ = escape
#!/usr/bin/env python
#
# Copyright 2009 Facebook
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

"""Escaping/unescaping methods for HTML, JSON, URLs, and others.

Also includes a few other miscellaneous string manipulation functions that
have crept in over time.
"""

from functools import wraps
import htmlentitydefs
import re
import sys
import urllib
import datetime
import time
import types
from HTMLParser import HTMLParser

# Python3 compatibility:  On python2.5, introduce the bytes alias from 2.6
try: bytes
except Exception: bytes = str

try:
    from urlparse import parse_qs  # Python 2.6+
except ImportError:
    from cgi import parse_qs

# json module is in the standard library as of python 2.6; fall back to
# simplejson if present for older versions.
try:
    import json
    assert hasattr(json, "loads") and hasattr(json, "dumps")
    _json_decode = json.loads
    _json_encode = json.dumps
except Exception:
    try:
        import simplejson
        _json_decode = lambda s: simplejson.loads(_unicode(s))
        _json_encode = lambda v: simplejson.dumps(v)
    except ImportError:
        try:
            # For Google AppEngine
            from django.utils import simplejson
            _json_decode = lambda s: simplejson.loads(_unicode(s))
            _json_encode = lambda v: simplejson.dumps(v)
        except ImportError:
            def _json_decode(s):
                raise NotImplementedError(
                    "A JSON parser is required, e.g., simplejson at "
                    "http://pypi.python.org/pypi/simplejson/")
            _json_encode = _json_decode


_XHTML_ESCAPE_RE = re.compile('[&<>"]')
_XHTML_ESCAPE_DICT = {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}
def xhtml_escape(value):
    """Escapes a string so it is valid within XML or XHTML."""
    return _XHTML_ESCAPE_RE.sub(lambda match: _XHTML_ESCAPE_DICT[match.group(0)],
                                to_basestring(value))


def xhtml_unescape(value):
    """Un-escapes an XML-escaped string."""
    return re.sub(r"&(#?)(\w+?);", _convert_entity, _unicode(value))


def json_encode(value):
    """JSON-encodes the given Python object."""
    # JSON permits but does not require forward slashes to be escaped.
    # This is useful when json data is emitted in a <script> tag
    # in HTML, as it prevents </script> tags from prematurely terminating
    # the javscript.  Some json libraries do this escaping by default,
    # although python's standard library does not, so we do it here.
    # http://stackoverflow.com/questions/1580647/json-why-are-forward-slashes-escaped
    return _json_encode(recursive_unicode(value)).replace("</", "<\\/")


def json_decode(value):
    """Returns Python objects for the given JSON string."""
    return _json_decode(to_basestring(value))


def squeeze(value):
    """Replace all sequences of whitespace chars with a single space."""
    return re.sub(r"[\x00-\x20]+", " ", value).strip()


def url_escape(value):
    """Returns a valid URL-encoded version of the given value."""
    return urllib.quote_plus(utf8(value))

# python 3 changed things around enough that we need two separate
# implementations of url_unescape.  We also need our own implementation
# of parse_qs since python 3's version insists on decoding everything.
if sys.version_info[0] < 3:
    def url_unescape(value, encoding='utf-8'):
        """Decodes the given value from a URL.

        The argument may be either a byte or unicode string.

        If encoding is None, the result will be a byte string.  Otherwise,
        the result is a unicode string in the specified encoding.
        """
        if encoding is None:
            return urllib.unquote_plus(utf8(value))
        else:
            return unicode(urllib.unquote_plus(utf8(value)), encoding)

    parse_qs_bytes = parse_qs
else:
    def url_unescape(value, encoding='utf-8'):
        """Decodes the given value from a URL.

        The argument may be either a byte or unicode string.

        If encoding is None, the result will be a byte string.  Otherwise,
        the result is a unicode string in the specified encoding.
        """
        if encoding is None:
            return urllib.parse.unquote_to_bytes(value)
        else:
            return urllib.unquote_plus(to_basestring(value), encoding=encoding)

    def parse_qs_bytes(qs, keep_blank_values=False, strict_parsing=False):
        """Parses a query string like urlparse.parse_qs, but returns the
        values as byte strings.

        Keys still become type str (interpreted as latin1 in python3!)
        because it's too painful to keep them as byte strings in
        python3 and in practice they're nearly always ascii anyway.
        """
        # This is gross, but python3 doesn't give us another way.
        # Latin1 is the universal donor of character encodings.
        result = parse_qs(qs, keep_blank_values, strict_parsing,
                          encoding='latin1', errors='strict')
        encoded = {}
        for k,v in result.iteritems():
            encoded[k] = [i.encode('latin1') for i in v]
        return encoded
        


_UTF8_TYPES = (bytes, type(None))
def utf8(value):
    """Converts a string argument to a byte string.

    If the argument is already a byte string or None, it is returned unchanged.
    Otherwise it must be a unicode string and is encoded as utf8.
    """
    if isinstance(value, _UTF8_TYPES):
        return value
    assert isinstance(value, unicode)
    return value.encode("utf-8")

_TO_UNICODE_TYPES = (unicode, type(None))
def to_unicode(value):
    """Converts a string argument to a unicode string.

    If the argument is already a unicode string or None, it is returned
    unchanged.  Otherwise it must be a byte string and is decoded as utf8.
    """
    if isinstance(value, _TO_UNICODE_TYPES):
        return value
    assert isinstance(value, bytes)
    return value.decode("utf-8")

# to_unicode was previously named _unicode not because it was private,
# but to avoid conflicts with the built-in unicode() function/type
_unicode = to_unicode

# When dealing with the standard library across python 2 and 3 it is
# sometimes useful to have a direct conversion to the native string type
if str is unicode:
    native_str = to_unicode
else:
    native_str = utf8

_BASESTRING_TYPES = (basestring, type(None))
def to_basestring(value):
    """Converts a string argument to a subclass of basestring.

    In python2, byte and unicode strings are mostly interchangeable,
    so functions that deal with a user-supplied argument in combination
    with ascii string constants can use either and should return the type
    the user supplied.  In python3, the two types are not interchangeable,
    so this method is needed to convert byte strings to unicode.
    """
    if isinstance(value, _BASESTRING_TYPES):
        return value
    assert isinstance(value, bytes)
    return value.decode("utf-8")


_DATE_FORMAT = "%Y-%m-%d"
_TIME_FORMAT = "%H:%M:%S"
def recursive_unicode(obj):
    """Walks a simple data structure, converting byte strings to unicode.

    Supports lists, tuples, and dictionaries.
    """
    if obj is True:
        return to_unicode("true")
    elif obj is False:
        return to_unicode("false")
    elif obj is None:
        return to_unicode("null")
    elif isinstance(obj, dict):
        return dict((recursive_unicode(k), recursive_unicode(v)) for (k,v) in obj.iteritems())
    elif isinstance(obj, list):
        return list(recursive_unicode(i) for i in obj)
    elif isinstance(obj, tuple):
        return tuple(recursive_unicode(i) for i in obj)
    elif isinstance(obj, bytes):
        return to_unicode(obj)
    elif isinstance(obj, datetime.datetime):
        return to_unicode(obj.strftime("%s %s" % (_DATE_FORMAT, _TIME_FORMAT)))
    elif isinstance(obj, datetime.date):
        return to_unicode(obj.strftime("%s" % _DATE_FORMAT))
    elif isinstance(obj, time.struct_time):
        t = datetime.datetime(obj.tm_year, obj.tm_mon, obj.tm_mday, obj.tm_hour, obj.tm_min, obj.tm_sec)
        return to_unicode(t.strftime("%s %s" % (_DATE_FORMAT, _TIME_FORMAT)))
    elif isinstance(obj, datetime.time):
        return to_unicode(obj.strftime("%s" % _TIME_FORMAT))
    elif isinstance(obj, types.IntType) or isinstance(obj, types.LongType):
        return to_unicode(str(obj))
    elif isinstance(obj, types.FloatType):
        return to_unicode("%f" % obj)
    else:
        return obj

# I originally used the regex from 
# http://daringfireball.net/2010/07/improved_regex_for_matching_urls
# but it gets all exponential on certain patterns (such as too many trailing
# dots), causing the regex matcher to never return.
# This regex should avoid those problems.
_URL_RE = re.compile(ur"""\b((?:([\w-]+):(/{1,3})|www[.])(?:(?:(?:[^\s&()]|&amp;|&quot;)*(?:[^!"#$%&'()*+,.:;<=>?@\[\]^`{|}~\s]))|(?:\((?:[^\s&()]|&amp;|&quot;)*\)))+)""")


def linkify(text, shorten=False, extra_params="",
            require_protocol=False, permitted_protocols=["http", "https"]):
    """Converts plain text into HTML with links.

    For example: ``linkify("Hello http://tornadoweb.org!")`` would return
    ``Hello <a href="http://tornadoweb.org">http://tornadoweb.org</a>!``

    Parameters:

    shorten: Long urls will be shortened for display.

    extra_params: Extra text to include in the link tag,
        e.g. linkify(text, extra_params='rel="nofollow" class="external"')

    require_protocol: Only linkify urls which include a protocol. If this is
        False, urls such as www.facebook.com will also be linkified.

    permitted_protocols: List (or set) of protocols which should be linkified,
        e.g. linkify(text, permitted_protocols=["http", "ftp", "mailto"]).
        It is very unsafe to include protocols such as "javascript".
    """
    if extra_params:
        extra_params = " " + extra_params.strip()

    def make_link(m):
        url = m.group(1)
        proto = m.group(2)
        if require_protocol and not proto:
            return url  # not protocol, no linkify

        if proto and proto not in permitted_protocols:
            return url  # bad protocol, no linkify

        href = m.group(1)
        if not proto:
            href = "http://" + href   # no proto specified, use http

        params = extra_params

        # clip long urls. max_len is just an approximation
        max_len = 30
        if shorten and len(url) > max_len:
            before_clip = url
            if proto:
                proto_len = len(proto) + 1 + len(m.group(3) or "")  # +1 for :
            else:
                proto_len = 0

            parts = url[proto_len:].split("/")
            if len(parts) > 1:
                # Grab the whole host part plus the first bit of the path
                # The path is usually not that interesting once shortened
                # (no more slug, etc), so it really just provides a little
                # extra indication of shortening.
                url = url[:proto_len] + parts[0] + "/" + \
                        parts[1][:8].split('?')[0].split('.')[0]

            if len(url) > max_len * 1.5:  # still too long
                url = url[:max_len]

            if url != before_clip:
                amp = url.rfind('&')
                # avoid splitting html char entities
                if amp > max_len - 5:
                    url = url[:amp]
                url += "..."

                if len(url) >= len(before_clip):
                    url = before_clip
                else:
                    # full url is visible on mouse-over (for those who don't
                    # have a status bar, such as Safari by default)
                    params += ' title="%s"' % href

        return u'<a href="%s"%s>%s</a>' % (href, params, url)

    # First HTML-escape so that our strings are all safe.
    # The regex is modified to avoid character entites other than &amp; so
    # that we won't pick up &quot;, etc.
    text = _unicode(xhtml_escape(text))
    return _URL_RE.sub(make_link, text)


class MyHTMLParser(HTMLParser):
    def __init__(self, text, preserve=None):
        HTMLParser.__init__(self)
        self.stack = [] 
        self.preserve = preserve
        if preserve is None:
            self.preserve = []
        elif isinstance(preserve, basestring):
            self.preserve = [preserve]

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.preserve:
            self.stack.append( self.__html_start_tag(tag, attrs) )

    def handle_endtag(self, tag):
        if tag.lower() in self.preserve:
            self.stack.append( self.__html_end_tag(tag) )

    def handle_startendtag(self, tag, attrs):
        if tag.lower() in self.preserve:
            self.stack.append( self.__html_startend_tag(tag, attrs) )

    def handle_data(self, data):
        self.stack.append(data)

    def __html_start_tag(self, tag, attrs): 
        return '<%s%s>' % (tag, self.__html_attrs(attrs)) 

    def __html_startend_tag(self, tag, attrs): 
        return '<%s%s/>' % (tag, self.__html_attrs(attrs)) 

    def __html_end_tag(self, tag): 
        return '</%s>' % (tag,) 

    def __html_attrs(self, attrs): 
        _attrs = '' 
        if attrs: 
            _attrs = ' %s' % (' '.join(['%s="%s"' % (item[0],item[1]) for item in attrs])) 
        return _attrs 

    @classmethod
    def parse(cls, text, preserve=None):
        _p = cls(text, preserve)
        _p.feed(text)
        _p.close()
        return "".join(_p.stack)

def clear_html_element(text, preserve=None):
    '''clear the html element in text'''
    if not preserve:
        p = re.compile(r'<[^>]*>')
        return p.sub("", text)
    if isinstance(preserve, basestring):
        preserve = [preserve]

    p = MyHTMLParser.parse(text, preserve)
    return p

def _convert_entity(m):
    if m.group(1) == "#":
        try:
            return unichr(int(m.group(2)))
        except ValueError:
            return "&#%s;" % m.group(2)
    try:
        return _HTML_UNICODE_MAP[m.group(2)]
    except KeyError:
        return "&%s;" % m.group(2)


def _build_unicode_map():
    unicode_map = {}
    for name, value in htmlentitydefs.name2codepoint.iteritems():
        unicode_map[name] = unichr(value)
    return unicode_map

_HTML_UNICODE_MAP = _build_unicode_map()

def jsonize(func):
    @wraps(func)
    def _(*a, **kw):
        r = func(*a, **kw)
        return json_encode(r)
    return _

########NEW FILE########
__FILENAME__ = filters
#!-*- coding:utf8 -*-
import re
from datetime import datetime, timedelta
from past.utils import escape

_paragraph_re = re.compile(r'(?:\r\n|\r|\n)')

def nl2br(value):
    result = u"<br/>\n".join(_paragraph_re.split(value))
    return result

def linkify(text):
    return escape.linkify(text)

def html_parse(s, preserve):
    return escape.MyHTMLParser.parse(text, preserve)

def stream_time(d):
    now = datetime.now()
    delta = now -d
    
    #duration = delta.total_seconds()  ##python2.7
    duration = delta.days * 365 * 86400 + delta.seconds
    if duration < 0:
        return u'穿越了...'
    elif duration <= 60:
        return u'%s秒前' %int(duration)
    elif duration <= 3600:
        return u'%s分钟前' %int(duration/60)
    elif duration <= 3600*12:
        return u'%s小时前' %int(duration/3600)
    elif d.year==now.year and d.month==now.month and d.day == now.day:
        return u'今天 %s' %d.strftime("%H:%M")
    elif d.year==now.year and d.month==now.month and d.day + 1 == now.day:
        return u'昨天 %s' %d.strftime("%H:%M")
    elif d.year==now.year and d.month==now.month and d.day + 2 == now.day:
        return u'前天 %s' %d.strftime("%H:%M")
    elif d.year == now.year:
        return u'今年 %s' %d.strftime("%m-%d %H:%M")
    elif d.year + 1 == now.year:
        return u'去年 %s' %d.strftime("%m-%d %H:%M")
    elif d.year + 2 == now.year:
        return u'前年 %s' %d.strftime("%m-%d %H:%M")
    elif d.year + 3 == now.year:
        return u'三年前 %s' %d.strftime("%m-%d %H:%M")
    elif d.year + 4 == now.year:
        return u'四年前 %s' %d.strftime("%m-%d %H:%M")
    elif d.year + 5 == now.year:
        return u'五年前 %s' %d.strftime("%m-%d %H:%M")
    elif d.year + 6 == now.year:
        return u'六年前 %s' %d.strftime("%m-%d %H:%M")
    else:
        return d.strftime("%Y-%m-%d %H:%M:%S")
    

########NEW FILE########
__FILENAME__ = logger
#-*- coding:utf-8 -*-

import logging
logging.basicConfig(
        format='%(asctime)s %(levelname)s:%(message)s',
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.DEBUG)


########NEW FILE########
__FILENAME__ = pdf
#-*- coding:utf-8 -*-

import os
import datetime
import hashlib
import urlparse
import httplib2
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

from past import app
from past.model.user import User
from past.model.status import Status
from past.utils import wrap_long_line, filters, randbytes, is_valid_image
from past.utils.escape import clear_html_element
from past import config

def generate_pdf(filename, uid, status_ids, with_head=True, capacity=50*1024):

    #########Set FONT################
    from xhtml2pdf.default import DEFAULT_FONT
    from xhtml2pdf.document import pisaDocument
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    pdfmetrics.registerFont(TTFont('zhfont', os.path.join(app.root_path, 'static/font/yahei-consolas.ttf')))
    DEFAULT_FONT["helvetica"] = "zhfont"
    css = open(os.path.join(app.root_path, "static/css/pdf.css")).read()

    #result = StringIO.StringIO()
    full_file_name = get_pdf_full_filename(filename)
    if not full_file_name:
        return None
    result = open(full_file_name, 'wb', 1024*1000)

    user = User.get(uid)
    if not user:
        return None

    # get status
    status_list = Status.gets(status_ids)
    _html = render(user, status_list, with_head)
    _pdf = pisaDocument(_html, result, default_css=css, link_callback=link_callback, capacity=capacity)
    result.close()

    if not _pdf.err:
        return full_file_name
    else:
        return None

def render(user, status_list, with_head=True):
    if not status_list:
        return
    date = status_list[0].create_time.strftime("%Y年%m月")
    date = date.decode("utf8")
    if with_head:
        _html = u"""<html> <body>
            <div id="Top">
                <img src="%s"/> &nbsp; &nbsp;&nbsp; The Past of Me | 个人杂志计划&nbsp;&nbsp;&nbsp;%s&nbsp;&nbsp;&nbsp;CopyRight©%s
                <br/>
            </div>
            <br/> <br/>

            <div class="box">
        """ % (os.path.join(app.root_path, "static/img/logo.png"), 
            date, user.name)
    else:
        _html = u"""<html> <body><div class="box">"""

    from jinja2 import Environment, PackageLoader
    env = Environment(loader=PackageLoader('past', 'templates'))
    env.filters['wrap_long_line'] = wrap_long_line
    env.filters['nl2br'] = filters.nl2br
    env.filters['stream_time'] = filters.stream_time
    env.filters['clear_html_element'] = clear_html_element
    env.filters['isstr'] = lambda x: isinstance(x, basestring)
    t = env.get_template('status.html')
    m = t.module
    for s in status_list:
        if not s:
            continue
        if s.category == config.CATE_DOUBAN_STATUS:
            r = m.douban_status(s, pdf=True)
        elif s.category == config.CATE_SINA_STATUS:
            r = m.sina_status(s, pdf=True)
        elif s.category == config.CATE_TWITTER_STATUS:
            r = m.twitter_status(s, pdf=True)
        elif s.category == config.CATE_QQWEIBO_STATUS:
            r = m.qq_weibo_status(s, pdf=True)
        elif s.category == config.CATE_WORDPRESS_POST:
            r = m.wordpress_status(s, pdf=True)
        elif s.category == config.CATE_THEPAST_NOTE:
            r = m.thepast_note_status(s, pdf=True)
        elif s.category == config.CATE_RENREN_STATUS:
            r = m.thepast_renren_status(s, pdf=True)
        elif s.category == config.CATE_RENREN_BLOG:
            r = m.thepast_renren_blog(s, pdf=True)
        elif s.category == config.CATE_RENREN_PHOTO or s.category == config.CATE_RENREN_ALBUM:
            r = m.thepast_renren_photo(s, pdf=True)
        elif s.category == config.CATE_INSTAGRAM_STATUS:
            r = m.thepast_default_status(s, pdf=True)
        else:
            r = ''
        if not r:
            continue
        _html += '''<div class="cell">''' + r + '''</div>'''
        Status._clear_cache(user_id = s.user_id, status_id = s.id)
    _html += """</div></body></html>"""
    return _html

def link_callback(uri, rel):
    #FIXME: 为了节省磁盘空间，PDF中不包含图片
    #return ''

    lower_uri = uri.lower()
    print '%s getting %s' % (datetime.datetime.now(), uri)
    if not (lower_uri.startswith('http://') or 
            lower_uri.startswith('https://') or 
            lower_uri.startswith('ftp://')):
        return ''
    if lower_uri.find(" ") != -1:
        return ''

    if lower_uri.find("\n") != -1:
        return ''

    if not (lower_uri.endswith(".jpg") or lower_uri.endswith(".jpeg")  or 
            lower_uri.endswith(".png")):
        return ''

    d = hashlib.md5()
    d.update(uri)
    d = d.hexdigest()
    _sub_dir = '%s/%s' % (config.CACHE_DIR, d[:2])

    if not os.path.isdir(_sub_dir):
        os.makedirs(_sub_dir)
    if not (os.path.exists(_sub_dir) and os.path.isdir(_sub_dir)):
        return uri

    _filename = d[0:8] + os.path.basename(urlparse.urlsplit(uri).path)
    cache_file = os.path.join(_sub_dir, _filename)

    if os.path.exists(cache_file) and os.path.getsize(cache_file) > 0:
        return cache_file
    
    resp, content = httplib2.Http().request(uri)
    if resp.status == 200:
        with open(cache_file, 'w') as f:
            f.write(content)
        if is_valid_image(cache_file):
            return cache_file
        else:
            return ''
    else:
        print 'get %s fail, status_code is %s, so return none' % (uri,resp.status)
        return ''

    return ''

def is_user_pdf_file_exists(uid, suffix=None, compressed=".tar.gz"):
    f = get_pdf_filename(uid, suffix, compressed)
    return is_pdf_file_exists(f)

def get_pdf_filename(uid, suffix=None, compressed=".tar.gz"):
    if suffix:
        return "thepast.me_%s_%s.pdf%s" % (uid, suffix, compressed)
    else:
        return "thepast.me_%s.pdf%s" % (uid, compressed)

def get_pdf_full_filename(filename):
    filename = filename.replace("..", "").replace("/", "")
    pdf_file_dir = config.PDF_FILE_DOWNLOAD_DIR

    if not os.path.isdir(pdf_file_dir):
        os.makedirs(pdf_file_dir)
    if not os.path.isdir(pdf_file_dir):
        return False

    return os.path.join(config.PDF_FILE_DOWNLOAD_DIR, filename)

def is_pdf_file_exists(filename):
    full_file_name = get_pdf_full_filename(filename)
    if os.path.exists(full_file_name) and os.path.getsize(full_file_name) > 0:
        return True
    return False


########NEW FILE########
__FILENAME__ = sendmail
#-*- coding:utf-8 -*-

import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.Utils import COMMASPACE, formatdate
from email import Encoders
import os

from past import config

_TO_UNICODE_TYPES = (unicode, type(None))
def to_unicode(value):
    if isinstance(value, _TO_UNICODE_TYPES):
        return value
    assert isinstance(value, bytes)
    return value.decode("utf-8")

    
def send_mail(to, fro, subject, text, html, files=None, 
            server=config.SMTP_SERVER, 
            user=config.SMTP_USER, password=config.SMTP_PASSWORD):
    if to and not isinstance(to, list):
        to = [to,]
    assert type(to)==list

    if files is None:
        files = []
    assert type(files)==list
 
    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')
    msg['From'] = fro
    msg['To'] = COMMASPACE.join(to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = to_unicode(subject)
 
    if text:
        msg.attach( MIMEText(text, 'plain', 'utf-8' ))
    if html:
        msg.attach( MIMEText(html, 'html', 'utf-8'))
 
    for file in files:
        part = MIMEBase('application', "octet-stream")
        part.set_payload( open(file,"rb").read() )
        Encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"'
                       % os.path.basename(file))
        msg.attach(part)
 
    smtp = smtplib.SMTP(server)
    if user and password:
        smtp.login(user, password)
    smtp.sendmail(fro, to, msg.as_string() )
    smtp.close()

if __name__ == "__main__":
    send_mail(['laiwei_ustc <laiwei.ustc@gmail.com>'],
        'today of the past<help@thepast.me>',
        'thepast.me | 历史上的今天',
        'http://thepast.me个人杂志计划', 'html内容',
        ['/home/work/proj/thepast/past/static/img/avatar.png'])


########NEW FILE########
__FILENAME__ = note
#-*- coding:utf-8 -*-

#past.view.note

import markdown2
from flask import g, flash, request, render_template, redirect, abort, url_for
from past import app

from past.utils.escape import json_encode
from past.utils import randbytes
from past.store import mc
from past.model.user import User
from past.model.note import Note
from past import consts
from past import config

from .utils import require_login, check_access_note

@app.route("/notes", methods=["GET"])
@require_login()
def my_notes():
    return redirect("/%s?cate=%s" % (g.user.uid, config.CATE_THEPAST_NOTE))

@app.route("/<uid>/notes", methods=["GET"])
def user_notes(uid):
    user = User.get(uid)
    if not user:
        abort(403, "no_such_user")
    
    return redirect("/%s?cate=%s" % (uid, config.CATE_THEPAST_NOTE))

@app.route("/note/<nid>", methods=["GET",])
def note(nid):
    note = Note.get(nid)
    if not note:
        abort(404, "no such note")
    
    r = check_access_note(note)
    if r:
        flash(r[1].decode("utf8"), "tip")
        return redirect(url_for("home"))

    title = note.title
    content = note.content
    fmt = note.fmt
    if fmt == consts.NOTE_FMT_MARKDOWN:
        content = markdown2.markdown(note.content, extras=["wiki-tables", "code-friendly"])
    create_time = note.create_time
    user = User.get(note.user_id)
    return render_template("v2/note.html", consts=consts, **locals())

@app.route("/note/edit/<nid>", methods=["GET", "POST"])
@require_login()
def note_edit(nid):
    note = Note.get(nid)
    if not note:
        abort(404, "no such note")

    if g.user.id != note.user_id:
        abort(403, "not edit privileges")
    
    error = ""
    if request.method == "GET":
        title = note.title
        content = note.content
        fmt = note.fmt
        privacy = note.privacy
        return render_template("v2/note_create.html", consts=consts, **locals())
        
    elif request.method == "POST":
        # edit
        title = request.form.get("title", "")       
        content = request.form.get("content", "")
        fmt = request.form.get("fmt", consts.NOTE_FMT_PLAIN)
        privacy = request.form.get("privacy", consts.STATUS_PRIVACY_PUBLIC)

        if request.form.get("cancel"):
            return redirect("/note/%s" % note.id)

        if request.form.get("submit"):
            error = check_note(title, content)
            if not error:
                note.update(title, content, fmt, privacy)
                flash(u"日记修改成功", "tip")
                return redirect("/note/%s" % note.id)
            else:
                flash(error.decode("utf8"), "error")
                return render_template("v2/note_create.html", consts=consts, **locals())
                
        else:
            return redirect("/note/%s" % note.id)
    
@app.route("/note/create", methods=["GET", "POST"])
@require_login(msg="先登录才能写日记")
def note_create():
    user = g.user
    error = ""
    if request.method == "POST":

        title = request.form.get("title", "")       
        content = request.form.get("content", "")
        fmt = request.form.get("fmt", consts.NOTE_FMT_PLAIN)
        privacy = request.form.get("privacy", consts.STATUS_PRIVACY_PUBLIC)

        if request.form.get("cancel"):
            return redirect("/i")
        
        # submit
        error = check_note(title, content)

        if not error:
            note = Note.add(g.user.id, title, content, fmt, privacy)
            if note:
                flash(u"日记写好了，看看吧", "tip")
                return redirect("/note/%s" % note.id)
            else:
                error = "添加日记的时候失败了，真不走运，再试试吧^^"
        if error:
            flash(error.decode("utf8"), "error")
            return render_template("v2/note_create.html", consts=consts, **locals())

    elif request.method == "GET":
        return render_template("v2/note_create.html", consts=consts, **locals())

    else:
        abort("wrong_http_method")

@app.route("/note/preview", methods=["POST"])
def note_preview():
    r = {}
    content = request.form.get("content", "")
    fmt = request.form.get("fmt", consts.NOTE_FMT_PLAIN)
    if fmt == consts.NOTE_FMT_MARKDOWN:
        r['data'] = markdown2.markdown(content, extras=["wiki-tables", "code-friendly"])
    else:
        r['data'] = content

    return json_encode(r)

def check_note(title, content):
    error = ""
    if not title:
        error = "得有个标题^^"
    elif not content:
        error = "写点内容撒^^"
    elif len(title) > 120:
        error = "标题有些太长了"
    elif len(content) > 102400:
        error = "正文也太长了吧"

    return error

########NEW FILE########
__FILENAME__ = pdf_view
#-*- coding:utf-8 -*-
import os
from datetime import datetime, timedelta
import calendar
import time
from collections import defaultdict

from flask import g, request, redirect, url_for, abort, render_template,\
        make_response, flash

from past import app
from past import config
from past.model.user import User, PdfSettings
from past.model.status import Status

from past.utils import sizeof_fmt
from past.utils.pdf import is_pdf_file_exists, get_pdf_filename, get_pdf_full_filename
from past.utils.escape import json_encode
from past import consts
from .utils import require_login, check_access_user, statuses_timelize, get_sync_list

@app.route("/pdf")
@require_login()
def mypdf():
    if not g.user:
        return redirect(url_for("pdf", uid=config.MY_USER_ID))
    else:
        return redirect(url_for("pdf", uid=g.user.id))

@app.route("/pdf/apply", methods=["POST"])
@require_login()
def pdf_apply():
    delete = request.form.get("delete")
    if delete:
        PdfSettings.remove_user_id(g.user.id)
        flash(u"删除PDF的请求提交成功，系统会在接下来的一天里删除掉PDF文件！", "tip")
        return redirect("/pdf")
    else:
        PdfSettings.add_user_id(g.user.id)
        flash(u"申请已通过，请明天早上来下载数据吧！", "tip")
        return redirect("/pdf")

@app.route("/demo-pdf")
def demo_pdf():
    pdf_filename = "demo.pdf"
    full_file_name = os.path.join(config.PDF_FILE_DOWNLOAD_DIR, pdf_filename)
    resp = make_response()
    resp.headers['Cache-Control'] = 'no-cache'
    resp.headers['Content-Type'] = 'application/pdf'
    resp.headers['Content-Disposition'] = 'attachment; filename=%s' % pdf_filename
    resp.headers['Content-Length'] = os.path.getsize(full_file_name)
    redir = '/down/pdf/' + pdf_filename
    resp.headers['X-Accel-Redirect'] = redir
    return resp
    
#PDF只允许登录用户查看
@app.route("/<uid>/pdf")
@require_login()
def pdf(uid):
    user = User.get(uid)
    if not user:
        abort(404, "No such user")

    if uid != g.user.id and user.get_profile_item('user_privacy') == consts.USER_PRIVACY_PRIVATE:
        flash(u"由于该用户设置了仅自己可见的权限，所以，我们就看不到了", "tip")
        return redirect("/")

    intros = [g.user.get_thirdparty_profile(x).get("intro") for x in config.OPENID_TYPE_DICT.values()]
    intros = filter(None, intros)

    pdf_files = []
    start_date = Status.get_oldest_create_time(None, user.id)
    now = datetime.now()
    d = start_date
    while d and d <= now:
        pdf_filename = get_pdf_filename(user.id, d.strftime("%Y%m"))
        if is_pdf_file_exists(pdf_filename):
            full_file_name = get_pdf_full_filename(pdf_filename)
            pdf_files.append([d, pdf_filename, sizeof_fmt(os.path.getsize(full_file_name))])

        days = calendar.monthrange(d.year, d.month)[1]
        d += timedelta(days=days)
        d = datetime(d.year, d.month, 1)
    files_dict = defaultdict(list)
    for date, filename, filesize in pdf_files:
        files_dict[date.year].append([date, filename, filesize])

    pdf_applyed = PdfSettings.is_user_id_exists(g.user.id)
    return render_template("v2/pdf.html", **locals())

@app.route("/pdf/<filename>")
@require_login()
def pdf_down(filename):
    pdf_filename = filename
    if not is_pdf_file_exists(pdf_filename):
        abort(404, "Please wait one day to  download the PDF version, because the vps memory is limited")

    user_id = pdf_filename.split('_')[1]
    u = User.get(user_id)
    if not u:
        abort(400, 'Bad request')

    if user_id != g.user.id and u.get_profile_item('user_privacy') == consts.USER_PRIVACY_PRIVATE:
        abort(403, 'Not allowed')

    full_file_name = get_pdf_full_filename(pdf_filename)
    resp = make_response()
    resp.headers['Cache-Control'] = 'no-cache'
    resp.headers['Content-Type'] = 'text/html'
    resp.headers['Content-Encoding'] = 'gzip'
    resp.headers['Content-Disposition'] = 'attachment; filename=%s' % pdf_filename
    resp.headers['Content-Length'] = os.path.getsize(full_file_name)
    redir = '/down/pdf/' + pdf_filename
    resp.headers['X-Accel-Redirect'] = redir
    return resp


########NEW FILE########
__FILENAME__ = settings
#-*- coding:utf-8 -*-

#past.view.settings

from flask import g, flash, request, render_template, redirect
from past import app
from past import config
from past.model.user import User, Confirmation, UserAlias
from past.model.status import SyncTask, TaskQueue
from past.utils import is_valid_email
from past.utils.escape import json_encode
from past.utils import randbytes
from past.api.wordpress import Wordpress
from past.store import mc
from past import consts

from .utils import require_login

@app.route("/settings", methods=["GET", "POST"])
@require_login()
def settings():
    uas = g.user.get_alias()
    wordpress_alias_list = [x for x in uas if x.type == config.OPENID_TYPE_DICT[config.OPENID_WORDPRESS]]
    wordpress_alias = wordpress_alias_list and wordpress_alias_list[0]
    user = g.user

    if request.method == "POST":
        email = request.form.get("email")
        if email and is_valid_email(email):
            r = g.user.set_email(email)
            if r:
                flash(u'个人信息更新成功', 'tip')
            else:
                flash(u'电子邮箱已被占用了', 'error')
        else:
            flash(u'电子邮箱格式不正确', 'error')
    return render_template("v2/settings.html", consts=consts, **locals())

@app.route("/settings/email_remind", methods=["POST"])
@require_login()
def settings_email_remind():
    today_in_history = request.form.get("today_in_history", consts.YES)
    g.user.set_profile_item("email_remind_today_in_history", today_in_history)
    flash(u'邮件提醒修改成功', 'tip')
    return redirect("/settings")

@app.route("/settings/privacy", methods=["POST"])
@require_login()
def settings_privacy():
    p = request.form.get("privacy", consts.USER_PRIVACY_PUBLIC)
    g.user.set_profile_item("user_privacy", p)
    flash(u'隐私设置修改成功', 'tip')
    return redirect("/settings")

@app.route("/settings/set_uid", methods=["POST"])
@require_login()
def settings_set_uid():
    ret = {
        "ok": False,
        "msg": "",
    }
    uid = request.form.get("uid")
    if not uid:
        ret["msg"] = "no uid"
        return json_encode(ret)
    
    r = g.user.update_uid(uid)
    if r:
        flag, msg = r
        ret['ok'] = flag
        ret['msg'] = msg

    return json_encode(ret)
    

@app.route("/bind/wordpress", methods=["GET", "POST"])
def bind_wordpress():
    if not g.user:
        flash(u"请先使用豆瓣、微博、QQ、Twitter任意一个帐号登录后，再来做绑定blog的操作^^", "tip")
        return redirect("/home")
    user = g.user

    intros = [g.user.get_thirdparty_profile(x).get("intro") for x in config.OPENID_TYPE_DICT.values()]
    intros = filter(None, intros)

    uas = g.user.get_alias()
    wordpress_alias_list = [x for x in uas if x.type == config.OPENID_TYPE_DICT[config.OPENID_WORDPRESS]]

    step = "1"
    random_id = mc.get("wordpress_bind:%s" % g.user.id)
    c = random_id and Confirmation.get_by_random_id(random_id)
    if c:
        _, feed_uri = c.text.split(":", 1)
        step = "2"
    else:
        feed_uri = ""
    

    if request.method == "GET":
        return render_template("v2/bind_wordpress.html", consts=consts, **locals())
    
    elif request.method == "POST":
        ret = {}
        ret['ok'] = False
        if step == '1':
            feed_uri = request.form.get("feed_uri")
            if not feed_uri:
                ret['msg'] = 'feed地址不能为空'
            elif not (feed_uri.startswith("http://") or feed_uri.startswith("https://")):
                ret['msg'] = 'feed地址貌似不对'
            else:
                ua = UserAlias.get(config.OPENID_TYPE_DICT[config.OPENID_WORDPRESS], feed_uri)
                if ua:
                    ret['msg'] = '该feed地址已被绑定'
                else:
                    ##设置一个激活码
                    code = randbytes(16)
                    val = "%s:%s" % (g.user.id, feed_uri)
                    r = Confirmation.add(code, val)
                    if r:
                        ret['ok'] = True
                        ret['msg'] = '为了验证blog的主人^^，请发一篇blog，内容为 %s，完成该步骤后，请点下一步完成绑定' \
                                % code
                        mc.set("wordpress_bind:%s" %g.user.id, code)
                    else:
                        ret['msg'] = '抱歉，出错了，请重试, 或者给管理员捎个话:help@thepast.me'
            return json_encode(ret)
        elif step == '2':
            if not (random_id and c):
                ret['msg'] = '出错了，激活码不对^^'
            else:
                text = c.text
                user_id, feed_uri = text.split(":", 1)
                ## 同步一下，看看验证码的文章是否正确
                client = Wordpress(feed_uri)
                rs = client.get_feeds(refresh=True)
                if not rs:
                    ret['msg'] = '没有发现含有验证码的文章，请检查后再提交验证'
                else:
                    latest_post = rs[0]
                    if not latest_post:
                        ret['msg'] = "你的feed地址可能无法访问，请检查下"
                    else:
                        content = latest_post.get_content() or latest_post.get_summary()
                        if content and content.encode("utf8")[:100].find(str(random_id)) != -1:
                            ua = UserAlias.bind_to_exists_user(g.user, 
                                    config.OPENID_TYPE_DICT[config.OPENID_WORDPRESS], feed_uri)
                            if not ua:
                                ret['msg'] = '出错了，麻烦你重试一下吧^^'
                            else:
                                ##添加同步任务
                                t = SyncTask.add(config.CATE_WORDPRESS_POST, g.user.id)
                                t and TaskQueue.add(t.id, t.kind)
                                ##删除confiration记录
                                c.delete()
                                mc.delete("wordpress_bind:%s" %g.user.id)

                                ret['ok'] = True
                                ret['msg'] = '恭喜，绑定成功啦'
                        else:
                            ret['msg'] = "没有发现含有验证码的文章，请检查后再提交验证"
            return json_encode(ret)
    else:
        return "method not allowed"


@app.route("/suicide")
@require_login()
def suicide():
    u = g.user
    from past.corelib import logout_user
    logout_user(g.user)

    from tools.remove_user import remove_user
    remove_user(u.id, True)

    flash(u"已注销",  "error")
    return redirect("/")

########NEW FILE########
__FILENAME__ = user_past
#-*- coding:utf-8 -*-
#个人过往页
import datetime
import random
from collections import defaultdict
from flask import (g, render_template, request, 
        redirect, abort, flash, url_for)
from past import app
from past import config
from past import consts

from past.model.user import User
from past.model.status import Status, get_status_ids_today_in_history
from .utils import require_login, check_access_user, statuses_timelize, get_sync_list

@app.route("/")
@app.route("/home")
@app.route("/explore")
def home():
    user_ids = User.get_ids(limit=10000)

    user = None
    i = 0
    while i <= 3:
        random_uid = random.choice(user_ids)
        user = User.get(random_uid)
        r = check_access_user(user)
        if not r:
            break
        i+=1

    if user:
        history_ids = Status.get_ids(user.id, start=0, limit=20)
        status_list = Status.gets(history_ids)
        status_list  = statuses_timelize(status_list)
        intros = [user.get_thirdparty_profile(x).get("intro") for x in config.OPENID_TYPE_DICT.values()]
        intros = filter(None, intros)
    else:
        status_list = []
        intros = []

    if g.user:
        sync_list = get_sync_list(g.user)
    else:
        sync_list = []

    d = defaultdict(list)
    for x in status_list:
        t = x.create_time.strftime("%Y年%m月%d日")
        d[t].append(x)
    history_status = d

    return render_template("v2/explore.html", **locals())

@app.route("/i")
def my_home():
    return redirect("/past")

@app.route("/<uid>/past")
def user_past(uid):
    user = User.get(uid)
    if not user:
        abort(404, "no such user")

    r = check_access_user(user)
    if r:
        flash(r[1].decode("utf8"), "tip")
        return redirect("/")

    try:
        now = datetime.datetime.strptime(request.args.get("now"), "%Y-%m-%d")
    except:
        now = datetime.datetime.now()

    history_ids = get_status_ids_today_in_history(user.id, now) 
    status_list = Status.gets(history_ids)
    if g.user and g.user.id == uid:
        pass
    elif g.user and g.user.id != uid:
        status_list = [x for x in status_list if x.privacy() != consts.STATUS_PRIVACY_PRIVATE]
    elif not g.user:
        status_list = [x for x in status_list if x.privacy() == consts.STATUS_PRIVACY_PUBLIC]

    status_list  = statuses_timelize(status_list)
    if g.user:
        sync_list = get_sync_list(g.user)
    else:
        sync_list = []

    intros = [user.get_thirdparty_profile(x).get("intro") for x in config.OPENID_TYPE_DICT.values()]
    intros = filter(None, intros)

    d = defaultdict(list)
    for x in status_list:
        t = x.create_time.strftime("%Y年%m月%d日")
        d[t].append(x)
    history_status = d

    return render_template("v2/user_past.html", **locals())

@app.route("/past")
@require_login()
def my_past():
    user = g.user
    return redirect(url_for(".user_past", uid=user.id))

##XXX:deprecated
@app.route("/user/<uid>")
def user(uid):
    u = User.get(uid)
    if not u:
        abort(404, "no such user")
    return redirect("/%s" % uid)

@app.route("/<uid>")
def user_by_domain(uid):
    u = User.get(uid)
    if not u:
        abort(404, "no such user")

    r = check_access_user(u)
    if r:
        flash(r[1].decode("utf8"), "tip")
        return redirect("/")

    ids = Status.get_ids(user_id=u.id, start=g.start, limit=g.count, cate=g.cate)
    status_list = Status.gets(ids)
    if g.user and g.user.id == uid:
        pass
    elif g.user and g.user.id != uid:
        status_list = [x for x in status_list if x.privacy() != consts.STATUS_PRIVACY_PRIVATE]
    elif not g.user:
        status_list = [x for x in status_list if x.privacy() == consts.STATUS_PRIVACY_PUBLIC]
        
    status_list  = statuses_timelize(status_list)
    intros = [u.get_thirdparty_profile(x).get("intro") for x in config.OPENID_TYPE_DICT.values()]
    intros = filter(None, intros)

    if g.user:
        sync_list = get_sync_list(g.user)
    else:
        sync_list = []

    now = datetime.datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
    return render_template("v2/user.html", user=u, intros=intros, 
            status_list=status_list, config=config, sync_list=sync_list, 
            now = now)

@app.route("/<uid>/more", methods=["GET"])
def user_more_by_domain(uid):
    u = User.get(uid)
    if not u:
        abort(404, "no such user")

    r = check_access_user(u)
    if r:
        abort(400, "no priv to access")

    ids = Status.get_ids(user_id=u.id, start=g.start, limit=g.count, cate=g.cate)
    status_list = Status.gets(ids)
    if g.user and g.user.id == uid:
        pass
    elif g.user and g.user.id != uid:
        status_list = [x for x in status_list if x.privacy() != consts.STATUS_PRIVACY_PRIVATE]
    elif not g.user:
        status_list = [x for x in status_list if x.privacy() == consts.STATUS_PRIVACY_PUBLIC]
        
    status_list  = statuses_timelize(status_list)
    intros = [u.get_thirdparty_profile(x).get("intro") for x in config.OPENID_TYPE_DICT.values()]
    intros = filter(None, intros)

    if g.user:
        sync_list = get_sync_list(g.user)
    else:
        sync_list = []

    now = datetime.datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
    return render_template("v2/user_more.html", user=u, intros=intros, 
            status_list=status_list, config=config, sync_list=sync_list, 
            now = now)

########NEW FILE########
__FILENAME__ = utils
#-*- coding:utf-8 -*-

from functools import wraps
from flask import g, flash, redirect, url_for, abort

from past.model.user import User
from past.model.note import Note
from past import consts
from past import config

def require_login(msg="", redir=""):
    def _(f):
        @wraps(f)
        def __(*a, **kw):
            if not g.user:
                flash(msg and msg.decode("utf8") or u"为了保护用户的隐私，请先登录^^", "tip")
                return redirect(redir or "/home")
            return f(*a, **kw)
        return __
    return _

def check_access_user(user):
    user_privacy = user.get_profile_item('user_privacy')
    if user_privacy == consts.USER_PRIVACY_PRIVATE and not (g.user and g.user.id == user.id):
        return (403, "由于该用户设置了仅自己可见的权限，所以，我们就看不到了")
    elif user_privacy == consts.USER_PRIVACY_THEPAST and not g.user:
        return (403, "由于用户设置了仅登录用户可见的权限，所以，需要登录后再看")

def check_access_note(note):
    if note.privacy == consts.STATUS_PRIVACY_PRIVATE and not (g.user and g.user.id == note.user_id):
        return (403, "由于该日记设置了仅自己可见的权限，所以，我们就看不到了")
    elif note.privacy == consts.STATUS_PRIVACY_THEPAST and not g.user:
        return (403, "由于该日记设置了仅登录用户可见的权限，所以，需要登录后再看")

## 把status_list构造为month，day的层级结构
def statuses_timelize(status_list):

    hashed = {}
    for s in status_list:
        hash_s = hash(s)
        if hash_s not in hashed:
            hashed[hash_s] = RepeatedStatus(s)
        else:
            hashed[hash_s].status_list.append(s)
    
    return sorted(hashed.values(), key=lambda x:x.create_time, reverse=True)

class RepeatedStatus(object):
    def __init__(self, status):
        self.create_time = status.create_time
        self.status_list = [status]

def get_sync_list(user):
    print '------user:',user
    user_binded_providers = [ua.type for ua in user.get_alias() if ua.type in config.CAN_SHARED_OPENID_TYPE]

    sync_list = []
    for t in user_binded_providers:
        p = user.get_thirdparty_profile(t)
        if p and p.get("share") == "Y":
            sync_list.append([t, "Y"])
        else:
            sync_list.append([t, "N"])
    return sync_list

########NEW FILE########
__FILENAME__ = views
#-*- coding:utf-8 -*-
import datetime

from collections import defaultdict
from flask import g, session, request, \
    redirect, url_for, abort, render_template, flash

from past import config
from past.store import db_conn
from past.corelib import auth_user_from_session, \
        logout_user, category2provider
from past.utils.escape import json_encode
from past.utils.logger import logging

from past.model.user import User, UserAlias, OAuth2Token
from past.model.status import SyncTask, Status, \
        get_status_ids_today_in_history, get_status_ids_yesterday
         
from past.api.error import OAuthError
from past.api.douban import Douban
from past.api.sina import SinaWeibo
from past.api.qqweibo import QQWeibo
from past.api.twitter import TwitterOAuth1

from past import consts

from past import app

from .utils import require_login, check_access_user, statuses_timelize, get_sync_list

log = logging.getLogger(__file__)


#TODO:
@app.route("/post/<id>")
def post(id):
    status = Status.get(id)
    if not status:
        abort(404, "访问的文章不存在^^")
    else:
        user = User.get(status.user_id)
        if user and not check_access_user(user):
            if status.category == config.CATE_THEPAST_NOTE:
                return redirect("/note/%s" % status.origin_id)
            intros = [user.get_thirdparty_profile(x).get("intro") for x in config.OPENID_TYPE_DICT.values()]
            intros = filter(None, intros)
            return render_template("post.html", config=config, **locals())
        else:
            abort(403, "没有权限访问该文章")

#XXX:
@app.route("/user")
def user_explore():
    g.count = 24
    user_ids = User.get_ids(start=g.start, limit=g.count)
    users = [User.get(x) for x in user_ids]
    users = [x for x in users if x.get_profile_item('user_privacy') != consts.USER_PRIVACY_PRIVATE]
    return render_template("v2/explore_user.html",
            users=users, config=config)
    
@app.route("/logout")
@require_login()
def logout():
    logout_user(g.user)
    flash(u"已退出",  "error")
    return redirect(url_for("home"))

@app.route("/about")
def about():
    return redirect("https://github.com/laiwei/thepast#readme")

@app.route("/reshare_ajax", methods=["POST",])
@require_login()
def reshare():
    text = request.form.get("text", "")
    providers = request.form.get("providers")
    providers = providers and providers.split("|") or []
    images = request.form.get("images")
    images = images and images.split("|") or []

    ret = {
        "ok": 1,
        "msg": "",
    }
    
    if not providers:
        providers = g.binds
    
    providers_ = []
    for p in config.CAN_SHARED_OPENID_TYPE:
        if p in providers:
            g.user.set_thirdparty_profile_item(p, "share", "Y")
            providers_.append(p)
        else:
            g.user.set_thirdparty_profile_item(p, "share", "N")
    
    failed_providers = []
    for p in providers_:
        try:
            post_status(g.user, p, text + ",".join(images))
        except OAuthError, e:
            log.warning("%s" % e)
            failed_providers.append(config.OPENID_TYPE_NAME_DICT.get(p, ""))
    if failed_providers:
        ret['ok'] = 0
        ret['msg'] = "分享到" + ",".join(failed_providers) + "失败了，可能是授权过期了，重新授权就ok：）"
    return json_encode(ret)

@app.route("/sync/<cates>", methods=["GET", "POST"])
@require_login()
def sync(cates):
    cates = cates.split("|")
    if not (cates and isinstance(cates, list)):
        return "no cates"

    cates = filter(lambda x: x in [str(y) for y in config.CATE_LIST], cates)
    if not cates:
        abort(400, "not support such cates")

    provider = category2provider(int(cates[0]))
    redir = "/connect/%s" % provider

    if not g.user:
        print '--- no g.user...'
        return redirect(redir)

    if request.form.get("remove"):
        for c in cates:
            r = SyncTask.gets_by_user_and_cate(g.user, str(c))
            for x in r:
                x.remove()
        return json_encode({'ok':'true'})

    uas = UserAlias.gets_by_user_id(g.user.id)
    r = filter(lambda x: x.type == config.OPENID_TYPE_DICT[provider], uas)
    user_alias = r and r[0]
    
    if not user_alias:
        print '--- no user_alias...'
        return json_encode({'ok':'false', 'redir':redir})

    token = OAuth2Token.get(user_alias.id)   
    
    if not token:
        print '--- no token...'
        return json_encode({'ok':'false', 'redir':redir})

    for c in cates:
        SyncTask.add(c, g.user.id)
    
    return json_encode({'ok':'true'})

def post_status(user, provider=None, msg=""):
    if msg and isinstance(msg, unicode):                                           
        msg = msg.encode("utf8") 
    if not provider or provider == config.OPENID_TYPE_DICT[config.OPENID_DOUBAN]:
        print "++++++++++post douban status"
        client = Douban.get_client(user.id)
        if client:
            if not msg:
                msg = "#thepast.me# 你好，旧时光| 我在用thepast, 广播备份，往事提醒，你也来试试吧 >> http://thepast.me "
            client.post_status(msg)

    if not provider or provider == config.OPENID_TYPE_DICT[config.OPENID_SINA]:
        print "++++++++++post sina status"
        client = SinaWeibo.get_client(user.id)
        if client:
            if not msg:
                msg = "#thepast.me# 你好，旧时光| 我在用thepast, 微博备份，往事提醒，你也来试试吧 >> http://thepast.me "
            client.post_status(msg)

    if not provider or provider == config.OPENID_TYPE_DICT[config.OPENID_TWITTER]:
        print "++++++++post twitter status"
        client = TwitterOAuth1.get_client(user.id)
        if client:
            if not msg:
                msg = "#thepast.me# 你好，旧时光| 我在用thepast, twitter备份，往事提醒，你也来试试吧 >> http://thepast.me "
            client.post_status(msg)

    if not provider or provider == config.OPENID_TYPE_DICT[config.OPENID_QQ]:
        print "++++++++post qq weibo status"
        client = QQWeibo.get_client(user.id)
        if client:
            if not msg:
                msg = "#thepast.me# 你好，旧时光| 我在用thepast, 微博备份，往事提醒，你也来试试吧 >> http://thepast.me "
            client.post_status(msg)

########NEW FILE########
__FILENAME__ = view
#-*- coding:utf-8 -*-
import hashlib
import xml.etree.ElementTree as ET
import time
import datetime

from flask import (session, redirect, request, abort, g, url_for, flash)
from past import config
from past import consts
from past.model.user import User
from past.model.weixin import UserWeixin
from past.model.status import Status, get_status_ids_today_in_history

from past.weixin import blue_print
from past.utils.logger import logging
log = logging.getLogger(__file__)

@blue_print.route("/callback", methods=["GET", "POST"])
def weixin_callback():
    #print "<<<method", request.method
    #print "<<<args:", request.args
    #print "<<<form:", request.form
    #print "<<<values:", request.values
    #print "<<<data:", request.data

    signature = request.args.get("signature", "")
    timestamp = request.args.get("timestamp", "")
    nonce = request.args.get("nonce", "")

    if not validate_sig(nonce, timestamp, signature):
        abort(400, "signature dismatch")

    if request.method == "GET":
        return request.args.get("echostr", "")

    elif request.method == "POST":
        content = request.data
        root = ET.fromstring(content)
        cmds = {}
        for x in root:
            cmds[x.tag] = x.text
        return echo(cmds)

def echo(cmds):
    msg_type = cmds.get("MsgType")
    if msg_type != "text":
        return ""

    content = cmds.get("Content")
    create_time = cmds.get("CreateTime")
    from_user = cmds.get("FromUserName")
    to_user = cmds.get("ToUserName")

    l = content.split()
    if not l:
        return ""

    reply_content = ""
    reply_type = "text"
    if l[0] == 'Hello2BizUser':
        reply_content = cmd_welcome()
    elif l[0] == 'h' or l[0] == 'help':
        reply_content = cmd_help()
    elif l[0] == 'b' or l[0] == 'bind':
        if len(l) == 1:
            reply_content = "你怎么没有提供thepast_id啊..."
        reply_content = cmd_bind(from_user, l[1])
    elif l[0] == 'p' or l[0] == 'past':
        
        if not UserWeixin.get_by_weixin(from_user):
            reply_content = "请先回复 bind thepast_id 告诉机器狗你的thepast_id是多少"
        else:
            reply_type = "news"
            if len(l) == 2:
                reply_content = cmd_past(from_user, l[1], reply_type)
            else:
                reply_content = cmd_past(from_user, "", reply_type)

    if not isinstance(reply_content, unicode):
        reply_content = reply_content.decode("utf8")
    reply_time = int(time.time())

    if reply_type == "text":
        reply_xml = u'''
            <xml>
             <ToUserName><![CDATA[{to_user}]]></ToUserName>
             <FromUserName><![CDATA[{from_user}]]></FromUserName>
             <CreateTime>{reply_time}</CreateTime>
             <MsgType><![CDATA[{reply_type}]]></MsgType>
             <Content><![CDATA[{reply_content}]]></Content>
             <FuncFlag>0</FuncFlag>
            </xml>'''.format(to_user=from_user, from_user=to_user, reply_time=reply_time, reply_type=reply_type, reply_content=reply_content)
    elif reply_type == "news":
        reply_xml = u'''
            <xml>
             <ToUserName><![CDATA[{to_user}]]></ToUserName>
             <FromUserName><![CDATA[{from_user}]]></FromUserName>
             <CreateTime>{reply_time}</CreateTime>
             <MsgType><![CDATA[{reply_type}]]></MsgType>
             {articles}
             <FuncFlag>1</FuncFlag>
            </xml>'''.format(to_user=from_user, from_user=to_user, reply_time=reply_time, reply_type=reply_type, articles=reply_content)
    print ">>>>> reply to %s" %from_user
    print reply_xml.encode("utf8")
    return reply_xml

def cmd_welcome():
    txt = "欢迎关注thepast^^\n%s" %cmd_help()
    return txt

def cmd_help():
    txt = '''现在，你面对的是，thepast.me的官方机器狗：）
输入
「help」 : 显示帮助信息
「bind thepast_id」 : 让机器狗知道你的thepast id
「past 02-28」  : 机器狗会回复你往年的这个日子，都发生了那些事情 '''

    return txt

def cmd_bind(from_user, thepast_id):
    u = User.get(thepast_id)
    if not u:
        return "不存在这个id啊，是不是搞错了啊"

    UserWeixin.add(u.id, from_user)
    return "绑定成功了，输入「past 日期」查看过往的碎碎念"

def cmd_past(from_user, date_, msg_type="text"):
    thepast_id = UserWeixin.get_by_weixin(from_user).user_id
    now = datetime.datetime.now()
    date_ = date_ or now.strftime("%m-%d") 
    date_ = "%s-%s" %(now.year + 1, date_)

    try:
        date_ = datetime.datetime.strptime(date_, "%Y-%m-%d")
    except:
        date_ = datetime.datetime(year=now.year+1, month=now.month, day=now.day)

    history_ids = get_status_ids_today_in_history(thepast_id, date_) 
    status_list = Status.gets(history_ids)
    status_list = [x for x in status_list if x.privacy() == consts.STATUS_PRIVACY_PUBLIC]

    r = ''
    if msg_type == "text":
        for x in status_list:
            r += x.create_time.strftime("%Y-%m-%d %H:%M") + "\n" + x.text + "\n~~~~~~~~~~\n"
    elif msg_type == "news":
        article_count = min(len(status_list)+1, 9)
        r += "<ArticleCount>%s</ArticleCount>" %article_count
        r += "<Articles>"
        date_str = u"{m}月{d}日".format(m=date_.month, d=date_.day)
        title0 = u"{d},找到{l}条往事,点击看更多".format(d=date_str, l=len(status_list))
        r += u'''
            <item>
            <Title><![CDATA[{title0}]]></Title> 
            <Description><![CDATA[{desc0}]]></Description>
            <PicUrl><![CDATA[{picurl0}]]></PicUrl>
            <Url><![CDATA[{url0}]]></Url>
            </item>
        '''.format(title0=title0, desc0="", picurl0="", url0="http://thepast.me/laiwei")

        for i in range(1, article_count):
            item_xml = '<item>'
            s = status_list[i-1]
            s_data = s.get_data()
            s_atts = s_data and s_data.get_attachments() or []
            s_images = s_data and s_data.get_images() or []

            s_re = s.get_retweeted_data()
            s_re_atts = s_re and s_re.get_attachments() or []
            s_re_images = s_re and s_re.get_images() or []
            s_re_user = s_re and s_re.get_user() or ""
            s_re_user_nickname = s_re_user if isinstance(s_re_user, basestring) else s_re_user.get_nickname()
            
            title = s.title

            desc = s.create_time.strftime("%Y-%m-%d %H:%M")
            desc += "\n" + s.summary
            for att in s_atts:
                desc += "\n" + att.get_href()
                desc += "\n" + att.get_description()
            if s_re_user_nickname and s_re.get_content():
                desc += "\n//@" + s_re_user_nickname + ":" + s_re.get_content()
            for att in s_re_atts:
                desc += "\n" + att.get_href()
                desc += "\n" + att.get_description()

            s_images.extend(s_re_images)
            pic_url = ""
            if s_images:
                pic_url = s_images[0]

            s_from = s.get_origin_uri()
            url = s_from and s_from[1] or pic_url

            item_xml += "<Title><![CDATA[" +title+desc+ "]]></Title>"
            item_xml += "<Description><![CDATA["+ title + desc +"]]></Description>"
            item_xml += "<PicUrl><![CDATA[" +pic_url+ "]]></PicUrl>"
            item_xml += "<Url><![CDATA[" +url+ "]]></Url>"
            item_xml += '</item>'
            r += item_xml

        r += "</Articles>"
    return r
   
def validate_sig(nonce, timestamp, signature, token="canuguess"):
    raw_str = "".join(sorted([str(nonce), str(timestamp), str(token)]))
    print "<<< raw_str:", raw_str
    enc = hashlib.sha1(raw_str).hexdigest()

    if enc and enc == signature:
        return True

    print "<<<invalid sig"
    return False
    

########NEW FILE########
__FILENAME__ = pastme
#-*- coding:utf-8 -*-

import os

activate_this = '%s/env/bin/activate_this.py' % os.path.dirname(os.path.abspath(__file__))
execfile(activate_this, dict(__file__=activate_this))

from werkzeug.contrib.fixers import ProxyFix
from past import app
app.wsgi_app = ProxyFix(app.wsgi_app)

if __name__ == "__main__":
    app.run(port=80)

########NEW FILE########
__FILENAME__ = add_all_synctask_for_old_user
#-*- coding:utf-8 -*-

import sys
sys.path.append('../')

import past
from past import config
from past.model.user import UserAlias
from past.model.status import SyncTask

all_alias_ids = UserAlias.get_ids()
for id_ in all_alias_ids:
    print id_
    ua = UserAlias.get_by_id(id_)
    if not ua:
        continue
    print ua

    if ua.type == 'D':
        SyncTask.add(config.CATE_DOUBAN_STATUS, ua.user_id)
        #SyncTask.add(config.CATE_DOUBAN_MINIBLOG, ua.user_id)

    #if ua.type == 'S':
    #    SyncTask.add(config.CATE_SINA_STATUS, ua.user_id)

    #if ua.type == 'T':
    #    SyncTask.add(config.CATE_TWITTER_STATUS, ua.user_id)


########NEW FILE########
__FILENAME__ = commpress_pdf
import sys
sys.path.append('../')
import os
import commands

def file_visitor(args, dir_, files):
    if not isinstance(files, list):
        return
    for f in files:
        if not (f.startswith("thepast.me_") and f.endswith(".pdf")):
            continue
        cmd = "cd ../var/down/pdf/ && tar -zcvf %s.tar.gz %s && rm %s" %(f, f, f)
        print "-----", cmd
        print commands.getoutput(cmd)

os.path.walk("../var/down/pdf/", file_visitor, None)

########NEW FILE########
__FILENAME__ = import_status_to_wordpress
#-*- coding:utf-8 -*-

import sys
sys.path.append('../')

from datetime import timedelta
import MySQLdb

import past
from past import config
from past.model.status import Status

def connect_db():
    try:
        conn = MySQLdb.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            user=config.DB_USER,
            passwd=config.DB_PASSWD,
            db="wp_linjuly",
            use_unicode=True,
            charset="utf8")
        return conn
    except Exception, e:
        print "connect db fail:%s" % e
        return None
db_conn = connect_db()

user_id = 34
limit = 250

status_ids = Status.get_ids(user_id, limit=limit, order="create_time desc")

for s in Status.gets(status_ids):
    try:
        _t = ''.join( [x for x in s.text] )

        retweeted_data = s.get_retweeted_data()
        if retweeted_data:
            if isinstance(retweeted_data, basestring):
                _t += retweeted_data
            else:
                _t += retweeted_data.get_content()
        print '---sid:', s.id
        post_author = 1 
        post_date = s.create_time
        post_date_gmt = s.create_time - timedelta(hours=8)
        post_content = _t
        post_title = u"%s" %post_content[:10]
        post_modified = post_date
        post_modified_gmt = post_date_gmt
        post_type = "post"

        post_excerpt = ""
        to_ping = ""
        pinged = ""
        post_content_filtered = ""
        
        cursor = None
        try:
            cursor = db_conn.cursor()
            cursor.execute('''insert into wp_posts (post_author, post_date, post_date_gmt,  post_content,
                    post_excerpt, to_ping, pinged, post_content_filtered,
                    post_title, post_modified, post_modified_gmt, post_type) 
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''', 
                    (post_author, post_date, post_date_gmt, post_content,
                    post_excerpt, to_ping, pinged, post_content_filtered,
                    post_title, post_modified, post_date_gmt, post_type))
            post_id = cursor.lastrowid
            cursor.execute('''update wp_posts set guid = %s''', 
                    "http://www.linjuly.com/?p=%s" %post_id)
            cursor.execute('''insert into wp_term_relationships values(%s,3,0)''', post_id)
            db_conn.commit()
        except Exception, e:
            import traceback; print traceback.format_exc()
            db_conn.rollback()
        finally:
            cursor and cursor.close()
    except Exception, e:
        import traceback; print traceback.format_exc()


#*************************** 1. row ***************************
#                   ID: 8
#          post_author: 1
#            post_date: 2012-01-01 22:29:57
#        post_date_gmt: 2012-01-01 14:29:57
#         post_content: 2011，其实是蛮惨的一年。。。
#           post_title: 我的2011
#         post_excerpt: 
#          post_status: publish
#       comment_status: open
#          ping_status: open
#        post_password: 
#            post_name: %e6%88%91%e7%9a%842011
#              to_ping: 
#               pinged: 
#        post_modified: 2012-03-29 23:31:37
#    post_modified_gmt: 2012-03-29 15:31:37
#post_content_filtered: 
#          post_parent: 0
#                 guid: http://www.linjuly.com/?p=8
#           menu_order: 0
#            post_type: post
#       post_mime_type: 
#        comment_count: 0
#1 row in set (0.00 sec)
#

########NEW FILE########
__FILENAME__ = manully_sync_user_timeline
#-*- coding:utf-8 -*-

import sys
sys.path.append("../")

activate_this = '../env/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

import datetime
from past import config
from past.model.status import SyncTask
from past.model.user import User
import jobs

if __name__ == '__main__':
    user = User.get(sys.argv[1])
    old = sys.argv[2] == "old"

    if not user:
        print "no such user"
        exit(1)

    ts = SyncTask.gets_by_user(user)
    if not ts:
        print "no sync tasks"

    for t in ts:
        try:
            if t.category == config.CATE_WORDPRESS_POST:
                jobs.sync_wordpress(t)
            else:
                jobs.sync(t, old=old)
        except Exception, e:
            import traceback
            print "%s %s" % (datetime.datetime.now(), traceback.format_exc())

        


########NEW FILE########
__FILENAME__ = merge_user
import sys
sys.path.append('../')

from past.store import db_conn

def merge_a2b(del_uid, merged_uid):
    
    
    print "-------update status:%s 2 %s" % (del_uid, merged_uid)
    db_conn.execute("update status set user_id=%s where user_id=%s", (merged_uid, del_uid))

    print "-------update alias:%s 2 %s" % (del_uid, merged_uid)
    db_conn.execute("update user_alias set user_id=%s where user_id=%s", (merged_uid, del_uid))
    
    print "-------update synctask:%s 2 %s" % (del_uid, merged_uid)
    db_conn.execute("update sync_task set user_id=%s where user_id=%s", (merged_uid, del_uid))

    db_conn.commit()


########NEW FILE########
__FILENAME__ = move_data_from_mongo_to_mysql
#-*- coding:utf-8 -*-

import sys
sys.path.append('../')
import datetime
import os
from MySQLdb import IntegrityError
from past.store import mongo_conn, db_conn
from past.model.kv import UserProfile, RawStatus, Kv
from past.utils.escape import json_decode, json_encode

def move_user_profile():
    RAW_USER_REDIS_KEY = "/user/raw/%s" 

    cursor = db_conn.execute("select id from user order by id")
    rows = cursor.fetchall()
    cursor and cursor.close()
    for row in rows:
        print '--------user raw id:', row[0]
        sys.stdout.flush()
        r1 = mongo_conn.get(RAW_USER_REDIS_KEY % row[0])
        if r1:
            print "r1"
            #UserProfile.set(row[0], r1)
            Kv.set('/profile/%s' %row[0], r1)
        r2 = mongo_conn.get("/profile/%s" % row[0])
        if r2:
            #Kv.set('/profile/%s' %row[0], r2)
            UserProfile.set(row[0], r2)

def myset(status_id, text, raw):
    cursor = None
    text = json_encode(text) if not isinstance(text, basestring) else text
    raw = json_encode(raw) if not isinstance(raw, basestring) else raw

    db_conn.execute('''replace into raw_status (status_id, text, raw) 
        values(%s,%s,%s)''', (status_id, text, raw))


def move_status():
    STATUS_REDIS_KEY = "/status/text/%s"
    RAW_STATUS_REDIS_KEY = "/status/raw/%s"

    start = 3720000
    limit = 100000
    #r =db_conn.execute("select count(1) from status")
    #total = r.fetchone()[0]
    total = 4423725
    print '----total status:', total
    sys.stdout.flush()

    ef = open("error.log", "a")
    #cf = open("cmd.txt", "w")
    while (start <= int(total)):
        f = open("./midfile.txt", "w")
        print '-------start ', start
        sys.stdout.flush()
        cursor = db_conn.execute("select id from status order by id limit %s,%s", (start, limit))
        rows = cursor.fetchall()
        for row in rows:
            text = mongo_conn.get(STATUS_REDIS_KEY % row[0])
            raw = mongo_conn.get(RAW_STATUS_REDIS_KEY% row[0])
            if text and raw:
                text = json_encode(text) if not isinstance(text, basestring) else text
                raw = json_encode(raw) if not isinstance(raw, basestring) else raw

                db_conn.execute('''replace into raw_status (status_id, text, raw) 
                    values(%s,%s,%s)''', (row[0], text, raw))
        db_conn.commit()
        start += limit


move_user_profile()
move_status()

########NEW FILE########
__FILENAME__ = move_data_from_redis_to_mongo
#-*- coding:utf-8 -*-

import sys
sys.path.append('../')
import datetime

from past.store import mongo_conn, db_conn
from past.utils.escape import json_decode, json_encode

def move_user_profile():
    RAW_USER_REDIS_KEY = "/user/raw/%s" 

    cursor = db_conn.execute("select id from user order by id")
    rows = cursor.fetchall()
    cursor and cursor.close()
    for row in rows:
        print '--------user raw id:', row[0]
        sys.stdout.flush()
        r = redis_conn.get(RAW_USER_REDIS_KEY % row[0])
        if r:
            mongo_conn.set(RAW_USER_REDIS_KEY % row[0], r)
        r2 = redis_conn.get("/profile/%s" % row[0])
        if r2:
            mongo_conn.set("/profile/%s" % row[0], r2)

def move_status():
    STATUS_REDIS_KEY = "/status/text/%s"
    RAW_STATUS_REDIS_KEY = "/status/raw/%s"

    start = 318003
    limit = 2500
    r =db_conn.execute("select count(1) from status")
    total = r.fetchone()[0]
    print '----total status:', total
    sys.stdout.flush()

    while (start <= int(total)):
        print '-------start ', start
        sys.stdout.flush()
        cursor = db_conn.execute("select id from status order by id limit %s,%s", (start, limit))
        rows = cursor.fetchall()
        if rows:
            keys = [STATUS_REDIS_KEY % row[0] for row in rows]
            values = redis_conn.mget(*keys)
            print '+++ mget text:', datetime.datetime.now()
            docs = []
            for i in xrange(0, len(keys)):
                if values[i]:
                    docs.append({"k":keys[i], "v":values[i]})
            mongo_conn.get_connection().insert(docs)
            ##mongo_conn.set(keys[i], values[i])
            print '+++ inserted text:', datetime.datetime.now()

            keys = [RAW_STATUS_REDIS_KEY % row[0] for row in rows]
            values = redis_conn.mget(*keys)
            print '+++ mget raw:', datetime.datetime.now()
            docs = []
            for i in xrange(0, len(keys)):
                if values[i]:
                    docs.append({"k":keys[i], "v":values[i]})
            mongo_conn.get_connection().insert(docs)
            print '+++ inserted raw:', datetime.datetime.now()

        start += limit

#move_user_profile()
move_status()

########NEW FILE########
__FILENAME__ = recover_wrong
#-*- coding:utf-8 -*-

import sys
sys.path.append('../')

from datetime import timedelta

from past.store import  db_conn
from past.model.kv import RawStatus

with open("ids.txt") as f:
    for id_ in f:
        id_ = id_.rstrip("\n")

        print id_
        cursor = db_conn.execute("delete from status where id=%s", id_)
        db_conn.commit()

        RawStatus.remove(id_)

        #cursor = db_conn.execute("select * from status where id=%s", id_)
        #print cursor.fetchone()

########NEW FILE########
__FILENAME__ = remove_pdf
import sys
sys.path.append('../')
import os

from past.store import db_conn

user_ids = []
cursor = db_conn.execute('''select user_id from pdf_settings''')
if cursor:
    rows = cursor.fetchall()
    user_ids = [row[0] for row in rows]
cursor and cursor.close()

print user_ids, len(user_ids)

def file_visitor(args, dir_, files):
    #print "-------", dir_, files
    pendding = set()
    if not isinstance(files, list):
        return
    for f in files:
        if not (f.startswith("thepast.me") and f.endswith(".pdf.tar.gz")):
            continue
        user_id = int(f.split("_")[1])
        if user_id not in user_ids:
            pendding.add(user_id)
    print pendding, len(pendding)
    for user_id in pendding:
        print '---deleting pdf of', user_id
        os.popen("rm ../var/down/pdf/thepast.me_%s_2*.pdf.tar.gz" %user_id)

os.path.walk("../var/down/pdf/", file_visitor, None)

########NEW FILE########
__FILENAME__ = remove_user
import sys
sys.path.append('../')

from past.store import db_conn
from past.model.user import User
from past.model.status import Status
from past.model.kv import RawStatus
from past import consts
from past import config

from past.utils.logger import logging
log = logging.getLogger(__file__)

suicide_log = logging.getLogger(__file__)
suicide_log.addHandler(logging.FileHandler(config.SUICIDE_LOG))

def remove_user(uid, clear_status=True):
    user = User.get(uid)
    if not user:
        print '---no user:%s' % uid

    suicide_log.info("---- delete from user, uid=%s" %uid)
    db_conn.execute("delete from user where id=%s", uid)
    db_conn.commit()
    User._clear_cache(uid)

    if clear_status:
        cursor = db_conn.execute("select id from status where user_id=%s", uid)
        if cursor:
            rows = cursor.fetchall()
            for row in rows:
                sid = row[0]
                suicide_log.info("---- delete status text, sid=%s" % sid)
                RawStatus.remove(sid)

        suicide_log.info("---- delete from status, uid=" %uid)
        db_conn.execute("delete from status where user_id=%s", uid)
        db_conn.commit()
        Status._clear_cache(uid, None)

    suicide_log.info("---- delete from passwd, uid=%s" %uid)
    db_conn.execute("delete from passwd where user_id=%s", uid)
    suicide_log.info("---- delete from sync_task, uid=%s" % uid)
    db_conn.execute("delete from sync_task where user_id=%s", uid)
    suicide_log.info("---- delete from user_alias, uid=%s" % uid)
    db_conn.execute("delete from user_alias where user_id=%s", uid)
    db_conn.commit()


def remove_status(uid):
    cursor = db_conn.execute("select id from status where user_id=%s", uid)
    if cursor:
        rows = cursor.fetchall()
        for row in rows:
            sid = row[0]
            print "---- delete mongo text, sid=", sid
            RawStatus.remove(sid)

    print "---- delete from status, uid=", uid
    db_conn.execute("delete from status where user_id=%s", uid)
    db_conn.commit()
    Status._clear_cache(uid, None)

if __name__ == "__main__":
    a = sys.argv
    uids = a[1:]
    for uid in uids:
        print "----- remove user:", uid
        remove_user(uid)
        print "----- remove status of user:", uid
        remove_status(uid)



########NEW FILE########
__FILENAME__ = repair_sinaweibo_time
#-*- coding:utf-8 -*-

import sys
sys.path.append('../')

import datetime
import past
from past.store import db_conn
from past.utils.escape import json_decode
from past.model.kv import RawStatus

cursor = db_conn.execute("select id from status where category=200")
rows = cursor.fetchall()
cursor and cursor.close()
ids = [x[0] for x in rows]

for x in ids:
    try:
        r = RawStatus.get(x)
        raw = r.raw if r else ""
        if raw:
            print x
            data = json_decode(raw)
            t = data.get("created_at")
            created_at = datetime.datetime.strptime(t, "%a %b %d %H:%M:%S +0800 %Y")
            db_conn.execute("update status set create_time = %s where id=%s", (created_at, x))
            db_conn.commit()
    except:
        import traceback
        print traceback.format_exc()
        sys.stdout.flush()

########NEW FILE########
__FILENAME__ = update_user_privacy
import sys
sys.path.append('../')

from past.store import db_conn
from past.model.user import User
from past import consts

def update_p2t():
    cursor = db_conn.execute("select id from user")
    rows = cursor and cursor.fetchall()
    cursor and cursor.close()
    for row in rows:
        uid = row[0]
        user = User.get(uid)
        if not user:
            print '---no user %s' %uid
            return

        old_p = user.get_profile_item("user_privacy")
        if not old_p or old_p == consts.USER_PRIVACY_PUBLIC:
            user.set_profile_item("user_privacy", consts.USER_PRIVACY_THEPAST)
        print '---updated user %s' %uid

update_p2t()

########NEW FILE########
