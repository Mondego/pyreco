__FILENAME__ = accounts
#-*-coding:utf-8-*-

"""
Copyright (c) 2012 wong2 <wonderfuly@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""


# 账号列表，一行一个
accounts = [
    ('email', 'password')
]

########NEW FILE########
__FILENAME__ = ai
#-*-coding:utf-8-*-

"""
Copyright (c) 2012 wong2 <wonderfuly@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""


# 小黄鸡的ai，先自己尝试处理，没结果则交给simsimi

import pkgutil
import plugins

plugin_modules = []
for plugin_name in plugins.__all__:
    __import__('plugins.%s' % plugin_name)
    plugin_modules.append(getattr(plugins, plugin_name))

# some magic here
def magic(data, bot=None):
    for plugin_module in plugin_modules:
        try:
            if plugin_module.test(data, bot):
                return plugin_module.handle(data, bot)
        except:
            continue

    return '呵呵'

if __name__ == '__main__':
    print magic({'message': '今天天气怎么样?'})

########NEW FILE########
__FILENAME__ = clear
#-*-coding:utf-8-*-

"""
Copyright (c) 2012 wong2 <wonderfuly@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""


from main import process
from controller import bots

# 用来出错重启前，先清理出错时间段内的通知

while True:
    for bot in bots:
        process(bot, True)

########NEW FILE########
__FILENAME__ = controller
#-*-coding:utf-8-*-

"""
Copyright (c) 2012 wong2 <wonderfuly@gmail.com>
Copyright (c) 2012 Qijiang Fan <fqj1994@gmail.com>

Original Author:
    Wong2 <wonderfuly@gmail.com>
Changes Statement:
    Changes made by Qijiang Fan <fqj1994@gmail.com> on
    Jan 6 2013:
        Add keywordfilter bindings.

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""


# 小黄鸡们

from ai import magic
from ntype import NTYPES
from filter_manager import questionfilter, answerfilter
import re
import sys
import redis

try:
    from renren_pro import RenRenPro as RenRen
except:
    from renren import RenRen
try:
    from my_accounts import accounts
except:
    from accounts import accounts
try:
    from settings import REDIS_HOST
except:
    REDIS_HOST = 'localhost'

# 匹配自己名字的正则
self_match_pattern = re.compile('@小黄鸡(\(601621937\))?')


# 登录账号得到bot
def getBots(accounts):
    if 'main.py' in sys.argv[0]:
        bots = []
        for account in accounts:
            bot = RenRen()
            bot.login(account[0], account[1])
            print bot.email, 'login'
            bots.append(bot)
        return bots
    else:
        r = redis.Redis(REDIS_HOST)
        cookies = r.get('xiaohuangji_cookies')
        bot = RenRen()
        if cookies:
            bot._loginByCookie(cookies)
            bot.email = ''
        else:
            account = accounts[0]
            bot.login(account[0], account[1])
        return [bot] if bot.token else []

bots = getBots(accounts)


# 从一条评论里提取出内容，去掉'回复xx:'和'@小黄鸡'
def extractContent(message):
    content = self_match_pattern.sub('', message)
    content_s = content.split('：', 1)
    if len(content_s) == 1:
        content_s = content.split(': ', 1)
    if len(content_s) == 1:
        content_s = content.split(':', 1)
    content = content_s[-1]
    return content

# 根据通知得到该回复的更详细信息
def getNotiData(bot, data):
    ntype, content = int(data['type']), ''

    payloads = {
        'owner_id': data['owner'],
        'source_id': data['source']
    }

    if ntype == NTYPES['at_in_status'] or ntype == NTYPES['reply_in_status_comment']:
        owner_id, doing_id = data['owner'], data['doing_id']

        payloads['type'] = 'status'

        if ntype == NTYPES['at_in_status'] and data['replied_id'] == data['from']:
            content = self_match_pattern.sub('', data['doing_content'].encode('utf-8'))
        else:
            # 防止在自己状态下@自己的时候有两条评论
            if ntype == NTYPES['at_in_status'] and owner_id == '601621937':
                return None, None
            reply_id = data['replied_id']
            comment = bot.getCommentById(owner_id, doing_id, reply_id)
            if comment:
                payloads.update({
                    'author_id': comment['ownerId'],
                    'author_name': comment['ubname'],
                    'reply_id': reply_id
                })
                content = extractContent(comment['replyContent'].encode('utf-8'))
            else:
                return None, None
    else:
        return None, None

    return payloads, content.strip()


# 得到数据，找到答案，发送回复
def reply(data):
    bot = bots[0]  # 现在只有一只小鸡了，且没了评论限制

    data, message = getNotiData(bot, data)

    if not data:
        return

    # 不要自问自答
    if '小黄鸡' in data.get('author_name', u'').encode('utf-8'):
        return

    print 'handling comment', data, '\n'

    data['message'] = questionfilter(message)
    answer = magic(data, bot)
    data['message'] = answerfilter(answer)

    result = bot.addComment(data)

    code = result['code']
    if code == 0:
        return

    if code == 10:
        print 'some server error'
    else:
        raise Exception('Error sending comment by bot %s' % bot.email)

########NEW FILE########
__FILENAME__ = encrypt
#-*-coding:utf-8-*-

"""
Copyright (c) 2012 wong2 <wonderfuly@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""


# 人人的登录密码加密算法

# 分段加密
CHUNK_SIZE = 30


# RSA加密
def enctypt(e, m, c):
    return pow(c, e, m)


# 加密一段
def enctyptChunk(e, m, chunk):
    chunk = map(ord, chunk)

    # 补成偶数长度
    if not len(chunk) % 2 == 0:
        chunk.append(0)

    nums = [chunk[i] + (chunk[i + 1] << 8) for i in range(0, len(chunk), 2)]

    c = sum([n << i * 16 for i, n in enumerate(nums)])

    encypted = enctypt(e, m, c)

    # 转成16进制并且去掉开头的0x
    return hex(encypted)[2:]


# 加密字符串，如果比较长，则分段加密
def encryptString(e, m, s):
    e, m = int(e, 16), int(m, 16)

    chunks = [s[:CHUNK_SIZE], s[CHUNK_SIZE:]] if len(s) > CHUNK_SIZE else [s]

    result = [enctyptChunk(e, m, chunk) for chunk in chunks]
    return ' '.join(result)[:-1]  # 去掉最后的'L'

if __name__ == '__main__':
    print encyptString('10001', '856381005a1659cb02d13f3837ae6bb0fab86012effb3a41c8b84badce287759', 'abcdef')

########NEW FILE########
__FILENAME__ = failure_handler
#-*-coding:utf-8-*-

"""
Copyright (c) 2012 Qijiang Fan <fqj1994@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""


import time
import sys
try:
    from settings import REDIS_HOST
except:
    REDIS_HOST = 'localhost'
try:
    from settings import REST_THRESHOLD
except:
    REST_THRESHOLD = 10
from rq import Worker
import redis

r = redis.Redis(host=REDIS_HOST)

failure_times = last_error_time = continuous_failure_times = 0


# 失败计数器
def job_failure_counter(prefix):
    global failure_times, last_error_time, continuous_failure_times
    n_failure_times = '.'.join([prefix, 'failure_times'])
    n_last_error_time = '.'.join([prefix, 'last_error_time'])
    n_continuous_failure_times = '.'.join([prefix, 'continuous_failure_times'])
    failure_times = int(r.get(n_failure_times) or 0)
    last_error_time = float(r.get(n_last_error_time) or 0)
    continuous_failure_times = int(r.get(n_continuous_failure_times) or 0)
    failure_times += 1
    r.incr(n_failure_times)
    if n_continuous_failure_times >= REST_THRESHOLD or time.time() - last_error_time <= 5:  # 将5s内的两次失败计作连续的失败
        continuous_failure_times += 1
        r.incr(n_continuous_failure_times)
    else:
        continuous_failure_times = 1
        r.set(n_continuous_failure_times, 1)
    last_error_time = time.time()
    r.set(n_last_error_time, last_error_time)
    failure_times = int(r.get(n_failure_times) or 0)
    continuous_failure_times = int(r.get(n_continuous_failure_times) or 0)


# 重置连续错误
def reset_failure(prefix):
    r.set('.'.join([prefix, 'continuous_failure_times']), 0)


# 得到 worker
def get_worker(traceback):
    p = traceback
    while p:
        l = p.tb_frame
        if 'self' in l.f_locals and isinstance(l.f_locals['self'], Worker):
            return l.f_locals['self']
        p = p.tb_next
    return None


# 额外的错误处理
def do_job_failure_handler_have_a_rest(job, exc_type, exc_val, traceback):
    worker = get_worker(traceback)
    if not worker:
        return True
    prefix = '.'.join(worker.name.split('.')[:-1])
    if 'simsimi.com' in str(exc_val):
        print 'count'
        job_failure_counter(prefix)
    if continuous_failure_times >= REST_THRESHOLD:
        print '%d continuous failed jobs. Sleep 60 seconds.' % (REST_THRESHOLD)
        time.sleep(60)
        reset_failure(prefix)
    return True

########NEW FILE########
__FILENAME__ = filter
#-*-coding:utf-8-*-

"""
Copyright (c) 2012 Qijiang Fan <fqj1994@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""


import re


# 过滤器基类
class Filter:
    def filter(self, sent):
        pass


# 修改过滤器
class ModificationFilter(Filter):
    def filter(self, sent):
        return sent


# 正则表达式修改过滤器
class RegexModificationFilter(ModificationFilter):
    def __init__(self, search, replacement):
        self.search = search
        self.replacement = replacement

    def filter(self, sent):
        return re.sub(self.search, self.replacement, sent)


# 问题屏蔽器基类
class BlockFilter(Filter):
    def __init__(self, default_text='呵呵'):
        self.default_text = default_text

    def block(self, sent):
        return False

    def filter(self, sent):
        if self.block(sent):
            return self.default_text
        else:
            return sent


# 正则表达式过滤屏蔽器
class RegexBlockFilter(BlockFilter):
    def __init__(self, reg, default_text='呵呵'):
        self.reg = reg
        BlockFilter.__init__(self, default_text)

    def block(self, sent):
        if re.match(self.reg, sent):
            return True
        else:
            return False

########NEW FILE########
__FILENAME__ = filterconfig
#-*-coding:utf-8-*-

"""
Copyright (c) 2012 Qijiang Fan <fqj1994@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""


from filter import *

rules_question = []
rules_answer = []

########NEW FILE########
__FILENAME__ = filter_manager
#-*-coding:utf-8-*-

"""
Copyright (c) 2012 Qijiang Fan <fqj1994@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

try:
    from my_filterconfig import rules_question, rules_answer
except:
    from filterconfig import rules_question, rules_answer


# 屏蔽
def keywordfiltercore(filters):
    def _keywordfilter(sent):
        res = sent
        for i in filters:
            res = i.filter(res)
        return res
    return _keywordfilter


questionfilter = keywordfiltercore(rules_question)
answerfilter = keywordfiltercore(rules_answer)

########NEW FILE########
__FILENAME__ = gui-watch
#!/usr/bin/env python
#-*-coding:utf-8-*-
#import redis
import MySQLdb
import requests
import sys
import time
import datetime

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from collections import *
from threading import Thread
from Queue import Queue

from settings import *

q = Queue()


class SThread(Thread):
    def __init__(self, func, args):
        self.func = func
        self.args = args
        Thread.__init__(self)
        self.daemon = True

    def run(self):
        self.func(*self.args)


def run_thread(fun, args):
    SThread(fun, args).start()


def update_stat(qlabel):
    while True:
        try:
            m = MySQLdb.connect(host=MYSQL_HOST, port=3306, user=MYSQL_USER, passwd=MYSQL_PASS,
                    db=MYSQL_DBNAME, charset="utf8", use_unicode=False, connect_timeout=5).cursor()
            m.execute("SELECT count(*) FROM `question_and_answers`")
            total = m.fetchone()[0]
            m.execute("SELECT MAX(`time`) FROM `question_and_answers`")
            maxtime = m.fetchone()[0]
            m.execute("SELECT count(*) FROM `question_and_answers` WHERE `time` = %s", (maxtime - datetime.timedelta(0, 1)))
            lastsec = m.fetchone()[0]
            m.execute("SELECT count(*) FROM `question_and_answers` WHERE `time` >= %s AND `time` < %s",
                    (maxtime - datetime.timedelta(0, 3600), maxtime))
            lasthour = m.fetchone()[0]
            m.execute("SELECT count(*) FROM `question_and_answers` WHERE `time` >= %s AND `time` < %s",
                    (maxtime - datetime.timedelta(0, 60), maxtime))
            lastmin = m.fetchone()[0]
            m.execute("SELECT count(*) FROM `question_and_answers` WHERE `time` >= %s AND `time` < %s",
                    (maxtime - datetime.timedelta(0, 3600 * 24), maxtime))
            lastday = m.fetchone()[0]

            q.put((qlabel, u'<center>统计数据</center>' + '<br/>'.join([
                u'最近更新：%s' % (maxtime - datetime.timedelta(0, 1)),
                u'总计：%d次' % total,
                u'最近一天：%d次' % lastday,
                u'最近一小时：%d次' % lasthour,
                u'最近一分钟：%d次' % lastmin,
                u'最近一秒：%d次' % lastsec,
                ])))
        finally:
            time.sleep(2)


def update_queues(qlabel):
    while True:
        try:
            r = requests.get('http://' + REDIS_HOST + ':9181/queues.json', timeout=5)
            j = r.json()
            s = u'<center>队列监控</center><br/>'
            if j[u'queues']:
                s += '<br/>'.join([
                    u'%s: %d' % (i[u'name'], i[u'count']) for i in j[u'queues']
                    ])
            else:
                s += u'所有队列为空'
            q.put((qlabel, s))
        finally:
            time.sleep(2)


def update_workers(qlabel):
    while True:
        try:
            r = requests.get('http://' + REDIS_HOST + ':9181/workers.json', timeout=5)
            j = r.json()
            workers = {}
            for i in j[u'workers']:
                name = '.'.join(i[u'name'].split('.')[:-1])
                if not name in workers:
                    workers[name] = defaultdict(int)
                workers[name][i[u'state']] += 1
            st = u'<center>Workers 状态</center><br/>' + u'<br/>'.join([
                worker + u'：   ' + u'   '.join([
                    u'%d %s(s)' % (workers[worker][state], state) for state in workers[worker]
                    ])
                for worker in workers])
            q.put((qlabel, st))
        finally:
            time.sleep(2)


def update_realtime(qlabel):
    while True:
        try:
            m = MySQLdb.connect(host=MYSQL_HOST, port=3306, user=MYSQL_USER, passwd=MYSQL_PASS,
                    db=MYSQL_DBNAME, charset="utf8", use_unicode=False, connect_timeout=5).cursor()
            m.execute("SELECT * FROM question_and_answers ORDER BY `id` DESC LIMIT 0, 3")
            l = m.fetchall()
            s = u'<center>最近三条问答</center><br/>' + '<br/>'.join([
                ("Q: %s<br/>A: %s<br/>Worker: %s<br/>Time: %s<br/>" % (t[1], t[2], t[3], t[4])).decode('UTF-8')
                for t in l])
            q.put((qlabel, s))
        finally:
            time.sleep(2)


def op(w):
    try:
        l = q.get_nowait()
        while l:
            l[0].setText(l[1])
            l = q.get_nowait()
    except:
        pass


class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self, windowTitle=u'小黄鸡监控')
        self.setCentralWidget(MainWidget())


class MainWidget(QWidget):
    def __init__(self):
        QWidget.__init__(self, windowTitle=u'小黄鸡监控')
        self.stat_data = QLabel("", parent=self)
        self.queues = QLabel("", parent=self)
        self.workers = QLabel("", parent=self)
        self.realtime = QLabel("", parent=self)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.stat_data)
        self.layout().addWidget(self.queues)
        self.layout().addWidget(self.workers)
        self.layout().addWidget(self.realtime)

        run_thread(update_stat, [self.stat_data])
        run_thread(update_queues, [self.queues])
        run_thread(update_workers, [self.workers])
        run_thread(update_realtime, [self.realtime])

        self.timer = QTimer(self)
        self.timer.timeout.connect(lambda: op(self))
        self.timer.start(100)


app = QApplication(sys.argv)
win = MainWindow()
win.show()
sys.exit(app.exec_())

########NEW FILE########
__FILENAME__ = main
#-*-coding:utf-8-*-

"""
Copyright (c) 2012 wong2 <wonderfuly@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""


# 主程序，轮询通知，处理通知

from renren import RenRen
from ntype import NTYPES
from multiprocessing import Pool
from urlparse import urlparse, parse_qsl
from redis import Redis
from rq import Queue
import requests
import time
import re
import sys
from controller import bots, reply

# 消息队列
redis_conn = Redis()
q = Queue(connection=redis_conn)


def handle(bot, notification):
    print time.strftime('%Y-%m-%d %I:%M:%S', time.localtime(time.time())), 'got notification'
    if int(notification['type']) in NTYPES.values():
        # 进入消息队列
        q.enqueue(reply, notification)


# 得到人人上的通知，处理之
def process(bot, just_clear=False):
    notifications = bot.getNotifications()

    for notification in notifications:
        notify_id = notification['notify_id']

        bot.removeNotification(notify_id)

        # 如果已经处理过了, 或在执行清空消息脚本
        if redis_conn.get(notify_id) or just_clear:
            print 'clear' if just_clear else 'get duplicate notification', notification
            return

        try:
            redis_conn.set(notify_id, True)
            handle(bot, notification)
            redis_conn.incr('comment_count')
        except Exception, e:
            print e

        print ''


def main():
    while True:
        try:
            map(process, bots)
        except KeyboardInterrupt:
            sys.exit()
        except Exception, e:
            print e

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = ntype
#-*-coding:utf-8-*-

"""
Copyright (c) 2012 wong2 <wonderfuly@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""


# 通知类型

NTYPES = {
    'reply_in_status_comment': 16,
    'at_in_status': 196
}

########NEW FILE########
__FILENAME__ = airpollution
#!/usr/bin/env python
#-*-coding:utf-8-*-

"""
Copyright (c) 2012 Qijiang Fan <fqj1994@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

# 空气污染
import urllib2
import re
import json
import redis
try:
    from settings import REDIS_HOST
except:
    REDIS_HOST = 'localhost'

city = json.loads("""[["\u5317\u4eac", "Beijing"], ["\u5929\u6d25", "Tianjin"], ["\u4e0a\u6d77", "Shanghai"], ["\u91cd\u5e86", "Chongqing"], ["\u77f3\u5bb6\u5e84", "Shijiazhuang"], ["\u5510\u5c71", "Tangshan"], ["\u79e6\u7687\u5c9b", "Qinhuangdao"], ["\u90af\u90f8", "Handan"], ["\u4fdd\u5b9a", "Baoding"], ["\u90a2\u53f0", "Xingtai"], ["\u5f20\u5bb6\u53e3", "Zhangjiakou"], ["\u627f\u5fb7", "Chengde"], ["\u5eca\u574a", "Cangzhou"], ["\u5eca\u574a", "Langfang"], ["\u8861\u6c34", "Hengshui"], ["\u592a\u539f", "Taiyuan"], ["\u5927\u540c", "Datong"], ["\u9633\u6cc9", "Yangquan"], ["\u957f\u6cbb", "Changzhi"], ["\u4e34\u6c7e", "Linfen"], ["\u547c\u548c\u6d69\u7279", "Huhehaote"], ["\u5305\u5934", "Baotou"], ["\u8d64\u5cf0", "Chifeng"], ["\u6c88\u9633", "Shenyang"], ["\u5927\u8fde", "Dalian"], ["\u978d\u5c71", "Anshan"], ["\u629a\u987a", "Fushun"], ["\u672c\u6eaa", "Benxi"], ["\u9526\u5dde", "Jinzhou"], ["\u957f\u6625", "Changchun"], ["\u5409\u6797", "Jilin"], ["\u54c8\u5c14\u6ee8", "Haerbin"], ["\u9f50\u9f50\u54c8\u5c14", "Qiqihaer"], ["\u5927\u5e86", "Daqing"], ["\u7261\u4e39\u6c5f", "Mudanjiang"], ["\u5357\u4eac", "Nanjing"], ["\u65e0\u9521", "Wuxi"], ["\u5f90\u5dde", "Xuzhou"], ["\u5e38\u5dde", "Changzhou"], ["\u82cf\u5dde", "Suzhou"], ["\u5357\u901a", "Nantong"], ["\u8fde\u4e91\u6e2f", "Lianyungang"], ["\u626c\u5dde", "Yangzhou"], ["\u9547\u6c5f", "Zhenjiang"], ["\u6dee\u5b89", "Huaian"], ["\u76d0\u57ce", "Yancheng"], ["\u53f0\u5dde", "Taizhou"], ["\u5bbf\u8fc1", "Suqian"], ["\u676d\u5dde", "Hangzhou"], ["\u5b81\u6ce2", "Ningbo"], ["\u6e29\u5dde", "Wenzhou"], ["\u5609\u5174", "Jiaxing"], ["\u6e56\u5dde", "Huzhou"], ["\u7ecd\u5174", "Shaoxing"], ["\u91d1\u534e", "Jinhua"], ["\u8862\u5dde", "Quzhou"], ["\u821f\u5c71", "Zhoushan"], ["\u4e3d\u6c34", "Lishui"], ["\u5408\u80a5", "Hefei"], ["\u829c\u6e56", "Wuhu"], ["\u9a6c\u978d\u5c71", "Maanshan"], ["\u798f\u5dde", "Fuzhou"], ["\u53a6\u95e8", "Xiamen"], ["\u6cc9\u5dde", "Quanzhou"], ["\u5357\u660c", "Nanchang"], ["\u4e5d\u6c5f", "Jiujiang"], ["\u6d4e\u5357", "Jinan"], ["\u9752\u5c9b", "Qingdao"], ["\u6dc4\u535a", "Zibo"], ["\u67a3\u5e84", "Zaozhuang"], ["\u70df\u53f0", "Yantai"], ["\u6f4d\u574a", "Weifang"], ["\u6d4e\u5b81", "Jining"], ["\u6cf0\u5b89", "Taian"], ["\u5a01\u6d77", "Weihai"], ["\u65e5\u7167", "Rizhao"], ["\u4e1c\u8425", "Dongying"], ["\u83b1\u829c", "Laiwu"], ["\u4e34\u6c82", "Linyi"], ["\u5fb7\u5dde", "Dezhou"], ["\u804a\u57ce", "Liaocheng"], ["\u6ee8\u5dde", "Binzhou"], ["\u83cf\u6cfd", "Heze"], ["\u90d1\u5dde", "Zhengzhou"], ["\u5f00\u5c01", "Kaifeng"], ["\u6d1b\u9633", "Luoyang"], ["\u5e73\u9876\u5c71", "Pingdingshan"], ["\u5b89\u9633", "Anyang"], ["\u7126\u4f5c", "Jiaozuo"], ["\u4e09\u95e8\u5ce1", "Sanmenxia"], ["\u6b66\u6c49", "Wuhan"], ["\u5b9c\u660c", "Yichang"], ["\u8346\u5dde", "Jingzhou"], ["\u957f\u6c99", "Changsha"], ["\u682a\u6d32", "Zhuzhou"], ["\u6e58\u6f6d", "Xiangtan"], ["\u5cb3\u9633", "Yueyang"], ["\u5e38\u5fb7", "Changde"], ["\u5f20\u5bb6\u754c", "Zhangjiajie"], ["\u5e7f\u5dde", "Guangzhou"], ["\u97f6\u5173", "Shaoguan"], ["\u6df1\u5733", "Shenzhen"], ["\u73e0\u6d77", "Zhuhai"], ["\u6c55\u5934", "Shantou"], ["\u4f5b\u5c71", "Foshan"], ["\u6e5b\u6c5f", "Zhanjiang"], ["\u4e2d\u5c71", "Zhongshan"], ["\u6c5f\u95e8", "Jiangmen"], ["\u8087\u5e86", "Zhaoqing"], ["\u4e1c\u839e", "Dongguan"], ["\u60e0\u5dde", "Huizhou"], ["\u987a\u5fb7", "Shunde"], ["\u5357\u5b81", "Nanning"], ["\u67f3\u5dde", "Liuzhou"], ["\u6842\u6797", "Guilin"], ["\u5317\u6d77", "Beihai"], ["\u6d77\u53e3", "Haikou"], ["\u4e09\u4e9a", "Sanya"], ["\u6210\u90fd", "Chengdu"], ["\u81ea\u8d21", "Zigong"], ["\u6500\u679d\u82b1", "Panzhihua"], ["\u6cf8\u5dde", "Luzhou"], ["\u5fb7\u9633", "Deyang"], ["\u7ef5\u9633", "Mianyang"], ["\u5357\u5145", "Nanchong"], ["\u5b9c\u5bbe", "Yibin"], ["\u8d35\u9633", "Guiyang"], ["\u9075\u4e49", "Zunyi"], ["\u6606\u660e", "Kunming"], ["\u66f2\u9756", "Qujing"], ["\u7389\u6eaa", "Yuxi"], ["\u62c9\u8428", "Lhasa"], ["\u897f\u5b89", "Xian"], ["\u94dc\u5ddd", "Tongchuan"], ["\u5b9d\u9e21", "Baoji"], ["\u54b8\u9633", "Xianyang"], ["\u6e2d\u5357", "Weinan"], ["\u5ef6\u5b89", "Yanan"], ["\u5170\u5dde", "Lanzhou"], ["\u91d1\u660c", "Jinchang"], ["\u897f\u5b81", "Xining"], ["\u94f6\u5ddd", "Yinchuan"], ["\u77f3\u5634\u5c71", "Shizuishan"], ["\u4e4c\u9c81\u6728\u9f50", "Wulumuqi"], ["\u514b\u62c9\u739b\u4f9d", "Karamay"]]""")


kv = redis.Redis(REDIS_HOST)


def test(data, bot):
    message = data['message']
    if '空气' not in message:
        return False
    req = filter(lambda p: p[0].encode('utf-8') in message, city)
    return len(req) > 0


def get_desc(cityname, cityshort):
    r = kv.get('airpollution.%s' % (cityshort))
    if r:
        return r
    r = urllib2.urlopen('http://www.aqicn.info/?city=%s&lang=cn' % (cityshort), timeout=60)
    p = r.read()
    m = re.search('%s[^"]*的空气质量([^"]*)' % (cityname), p)
    m_aqiindex = re.search(r'整体空气质量指数为([0-9]*)', p)
    if m and m_aqiindex:
        text = m.group(0).replace('。', '，').replace('.', '') + '，整体AQI指数为：' + m_aqiindex.group(1)
        kv.setex('airpollution.%s' % (cityshort), text, 1800)
        return text
    else:
        raise Exception


def handle(data, bot):
    message = data['message']
    reqs = filter(lambda p: p[0].encode('utf-8') in message, city)
    s = []
    for i in reqs:
        try:
            s.append(get_desc(i[0].encode('utf-8'), i[1].encode('utf-8')))
        except:
            pass
    if s:
        return '，'.join(s) + '。'
    else:
        raise Exception

########NEW FILE########
__FILENAME__ = arithmetic
#!/usr/bin/env python
#-*-coding:utf-8-*-

"""
Copyright (c) 2013 Pili Hu <hpl1989@gmail.com>

Original Author:
        Phili Hu <hpl1989@gmail.com>

Changed By
        Qijiang Fan <fqj1994@gmail.com>
        1. Convert expr to float values if accurate value is too long
        2. Handle TokenError.

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

# Arithmetic Module
#
# Emoji from:
#     http://zh.wikipedia.org/wiki/%E8%A1%A8%E6%83%85%E7%AC%A6%E5%8F%B7

import re
from timeout import timeout, TimeoutException
from sympy.parsing import sympy_parser
from sympy.parsing.sympy_tokenize import TokenError

try:
    from settings import AI_ARITHMETIC_REGEX_TEST
except:
    AI_ARITHMETIC_REGEX_TEST = '([ \(\.\)0-9a-zA-Z,+\-*^/]+)((\s*=\s*(\?|？))|(\s*(是多少|是几|等于几|等于多少)))'

try:
    from settings import AI_ARITHMETIC_REGEX_HANDLE
except:
    AI_ARITHMETIC_REGEX_HANDLE = AI_ARITHMETIC_REGEX_TEST

try:
    from settings import AI_ARITHMETIC_MAX_LEN_EXP
except:
    AI_ARITHMETIC_MAX_LEN_EXP = 120

try:
    from settings import AI_ARITHMETIC_MAX_LEN_REPLY
except:
    AI_ARITHMETIC_MAX_LEN_REPLY = 100

try:
    from settings import AI_ARITHMETIC_EVAL_TIMEOUT
except:
    AI_ARITHMETIC_EVAL_TIMEOUT = 1.0  # Second

REGEX_TEST = re.compile(AI_ARITHMETIC_REGEX_TEST)
REGEX_HANDLE = re.compile(AI_ARITHMETIC_REGEX_HANDLE)


def test(data, bot):
    return True if REGEX_TEST.search(data['message']) else False


def handle(data, bot):
    try:
        exp = REGEX_HANDLE.search(data['message']).groups()[0]
    except:
        # The flow is not supposed to reach here. 'data' is already
        # tested by AI_ARITHMETIC_REGEX_TEST so we should be able to
        # read group()[0]. This is just to prevent your customized
        # regex from causing errors.
        return '好复杂哦，计算鸡也不会了 ╮(︶︿︶)╭ （怎么会这样？）'

    try:
        return cal(exp)
    except TimeoutException:
        return '太难了，计算鸡半天都算不出来 ╮(︶︿︶)╭'


@timeout(AI_ARITHMETIC_EVAL_TIMEOUT)
def cal(exp):
    if len(exp) > AI_ARITHMETIC_MAX_LEN_EXP:
        return '太长了……小鸡才不算呢。╮(︶︿︶)╭'

    try:
        ansexp = sympy_parser.parse_expr(exp.replace('^', '**'))
        ans = str(ansexp).replace('**', '^')
        i = 15
        while len(ans) > AI_ARITHMETIC_MAX_LEN_EXP:
            ans = str(ansexp.evalf(i)).replace('**', '^')
            i = i - 1
            if i <= 0:
                break

        if len(ans) > AI_ARITHMETIC_MAX_LEN_REPLY:
            return '这个数字太长了！鸡才懒得回你呢╮(︶︿︶)╭'
        else:
            return '不就是%s嘛。啦啦啦……我是计算鸡…… ＼（￣︶￣）／' % ans
    except ZeroDivisionError:
        return '你好笨啊！除零了。跟小鸡学下四则运算吧 （＃￣▽￣＃）'
    except SyntaxError:
        return '(´･д･`) 这明显有问题嘛！！你确定没写错？'
    except TokenError:
        return '(´･д･`) 这明显有问题嘛！！你确定没写错？'
    except Exception, e:
        #TODO:
        #    Any logging convention in this project? We should log the
        #    error for further investigation
        #raise e
        return '好复杂哦，计算鸡也不会了 ╮(︶︿︶)╭'

if __name__ == '__main__':
    print "Unit tests are now moved to 'test_arithmetic.py'"
    pass

########NEW FILE########
__FILENAME__ = calc24
#coding=utf-8

"""
Copyright (c) 2013 Moody _"Kuuy"_ Wizmann <mail.kuuy@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import sys
import re
import os
import sqlite3

reload(sys)
sys.setdefaultencoding('utf-8')


class Calc24db:
    def __init__(self):
        db_path = os.path.join(os.path.dirname(
            os.path.abspath(__file__)),
            'data', 'CalcXdb.sqlite3')
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

    def search(self, ans, nums):
        SQL = "SELECT `formula` FROM `calcx` \
                WHERE `ans`={0} AND `hashcode`={1}"
        hashcode = reduce(lambda x, y: x * 13 + y, sorted(nums))
        self.cursor.execute(SQL.format(ans, hashcode))
        answer = self.cursor.fetchall()
        if answer:
            return answer[0][0]
        else:
            return None


calc24db = Calc24db()


class Calc24Exception(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)


def test(data, bot):
    message = data['message']
    if not re.search('算[G\d-]+点', message) \
            or not re.search('(?:.*\[)(.+)(?:\][.]*)', message):
        return False
    else:
        return True


def solve(ans, nums):
    try:
        s = calc24db.search(ans, nums)
        if(s):
            return s.strip()
        else:
            return None
    except Exception, e:
        return str(e)


def handle(data, bot):
    message = data['message']
    query = re.findall('(?:.*\[)(.+)(?:\][.]*)', message)
    ans = re.findall('算([G\d-]+)点', message)
    try:
        if len(query) == 0 or len(ans) == 0:
            raise Calc24Exception("表达式错误哦~")
        else:
            try:
                ans_str = ans[0]
                if ans_str == 'G':
                    return '啊啊啊！不要碰那里！'
                ans = int(ans_str)
            except:
                raise Calc24Exception("表达式错误哦~")
            nums = map(lambda x: x.strip(), query[0].split(','))
            if ''.join(nums) == 'FUCK':
                return 'Coded by Wizmann~'
            elif ''.join(nums) == 'SEXY':
                return 'I love SEX!'
            elif len(nums) != 4:
                raise Calc24Exception("参数错误哦~")
            else:
                def conv(ch):
                    try:
                        t = int(ch)
                    except:
                        t = ch
                    if(1 <= t <= 13):
                        return t
                    else:
                        conv_dict = {'A': 1, 'J': 11, 'Q': 12, 'K': 13}
                        t = conv_dict.get(t, None)
                        if t:
                            return t
                        else:
                            raise Calc24Exception("明明没有那种牌嘛～")
                nums = map(conv, nums)
                formula = solve(ans, nums)
                return "没有答案哦~" if not formula else '答案是：' + formula
    except Exception, e:
        return str(e)


if(__name__ == '__main__'):
    print test({'message': "@小黄鸡  算24点 不算烧死 [1,2,3,4]你好世界"}, None)
    print test({'message': "@小黄鸡  算24点 不算烧死 [A,A,A,A]你好世界"}, None)
    print test({'message': "@小黄鸡  算16点 不算烧死 [4,4,4,4]你好世界"}, None)
    print test({'message': 'Hello World 算24点'}, None)
    print handle({'message':
                  '@小黄鸡  算24点 不算烧死 [Q,K,A,A]你好世界',
                  'author_id': 'Wizmann'}, None)
    print handle({'message':
                  '@小黄鸡  算24点 不算烧死 [A,A,A,A]你好世界',
                  'author_id': 'Wizmann'}, None)
    print handle({'message':
                  '@小黄鸡  算-2点 不算烧死 [A,A,A,A]你好世界',
                  'author_id': 'Wizmann'}, None)
    print handle({'message':
                  '@小黄鸡  算----------点 不算烧死 [3,3,8,8]你好世界',
                  'author_id': 'Wizmann'}, None)
    print handle({'message':
                  '@小黄鸡  算24点 不算烧死 [3,3,8,8]你好世界',
                  'author_id': 'Wizmann'}, None)
    print handle({'message':
                  '@小黄鸡  算16点 不算烧死 [4,4,4,4]你好世界',
                  'author_id': 'Wizmann'}, None)
    print handle({'message':
                  '@小黄鸡  算256点 不算烧死 [8,8,4,4]你好世界',
                  'author_id': 'Wizmann'}, None)
    print handle({'message':
                  '算132465点 [A,2,Q,K]',
                  'author_id': 'Wizmann'}, None)
    print handle({'message':
                  '算0点 [1,K,Q,K]',
                  'author_id': 'Wizmann'}, None)
    print handle({'message':
                  '算512点 [ZZ,2,Q,K]',
                  'author_id': 'Wizmann'}, None)
    print handle({'message': 'Hello World 算24点 [F,U,C,K]',
                 'author_id': 'Kuuy'}, None)
    print handle({'message': 'Hello World 算24点 [1, 1, 12, 13]'}, None)
    print handle({'message': '算G点 [1, 1, 12, 13]'}, None)

########NEW FILE########
__FILENAME__ = calcX
#coding=utf-8

"""
Copyright (c) 2013 Moody _"Kuuy"_ Wizmann <mail.kuuy@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

"""
算X点答案预处理脚本
速度极慢
CPU 2.3G + RAM 4G 用时为6分钟+

生成一个sqlite3数据库，查询速度较快，基本没有延时
没有在大规模并发下进行测试，目测问题不大

在使用CalcX插件前，先要生成答案数据库
而且要删除目录下的CalcXdb.sqlite3文件

由于不是线上代码，所以写的比较屎，见谅

By Moody _"Kuuy"_ Wizmann
"""

from __future__ import division
import sys
import os
import sqlite3

CREATE_SQL = '''
CREATE TABLE IF NOT EXISTS `calcX`
(
    id INTEGER NOT NULL  primary key autoincrement ,
    ans INTEGER NOT NULL,
    hashcode INTEGER NOT NULL,
    formula TEXT NOT NULL
);
'''

INDEX_SQL = '''
CREATE INDEX IF NOT EXISTS idx_ans_hashcode ON `calcX`(`ans`,`hashcode`);
'''


class CalcXdb:
    def __init__(self):
        db_path = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), 'CalcXdb.sqlite3')
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.cursor.execute(CREATE_SQL)
        self.cursor.execute(INDEX_SQL)
        self.visit = set()

    def insert(self, key, values):
        SQL = 'INSERT INTO `calcX` (`ans`,`hashcode`,`formula`)\
                VALUES ({0},{1},"{2}")'
        for ans, formula in values:
            if (ans, key) in self.visit:
                continue
            else:
                self.visit.add((ans, key))
            _SQL = SQL.format(ans, key, formula)
            #print _SQL
            self.cursor.execute(_SQL)

    def commit(self):
        self.conn.commit()


formula_set = (
    '(%d%c%d)%c(%d%c%d)',
    '((%d%c%d)%c%d)%c%d',
    '(%d%c(%d%c%d)%c%d)',
    '%d%c(%d%c(%d%c%d))',
    '%d%c((%d%c%d)%c%d)')


def conv_int(x):
    if abs(x-round(x)) < 1e-8:
        if abs(x) < 1e-8:
            return 0
        else:
            return int(x + (0.5 * (x / abs(x))))
    else:
        return None


def calc(formula, nums, oprs):
    oprs = map(lambda x: {0: '+', 1: '-', 2: '*', 3: '/'}[x], oprs)
    formula = formula % (nums[0], oprs[0],
                         nums[1], oprs[1],
                         nums[2], oprs[2],
                         nums[3])
    try:
        ans = conv_int(eval(formula))
        if ans:
            return (ans, formula)
        else:
            return None
    except Exception, e:
        return None


def slove(a, b, c, d):
    answer = []
    for i in xrange(4):
        for j in xrange(4):
            for k in xrange(4):
                for formula in formula_set:
                    ans = calc(formula, [a, b, c, d], [i, j, k])
                    if ans:
                        answer.append(ans)
    return answer


def main():
    _CalcXdb = CalcXdb()
    for i in xrange(13):
        for j in xrange(13):
            for k in xrange(13):
                for l in xrange(13):
                    nums = [i + 1, j + 1, k + 1, l + 1]
                    print nums
                    hashcode = reduce(lambda x, y: x * 13 + y, sorted(nums))
                    answer = slove(*nums)
                    _CalcXdb.insert(hashcode, answer)
    _CalcXdb.commit()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = earthquake
#!/usr/bin/env python
#-*-coding:utf-8-*-

"""
Copyright (c) 2012 Qijiang Fan <fqj1994@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

# 地震
import StringIO
import time
import urllib2
import re


def test(data, bot):
    return '地震了' in data['message']


def jw(a, b):
    aa = ''
    bb = ''
    if int(a.replace('.', '')) > 0:
        aa = '北纬' + a + '度'
    elif int(a.replace('.', '')) < 0:
        aa = '南纬' + a.replace('-', '') + '度'
    else:
        aa = '赤道附近'
    if int(b.replace('.', '')) > 0:
        bb = '东经' + b + '度'
    elif int(b.replace('.', '')) < 0:
        bb = '西经' + b.replace('-', '') + '度'
    else:
        bb = '本初子午线附近'
    return '，'.join((aa, bb))


def handle(data, bot):
    r = urllib2.urlopen('http://data.earthquake.cn/datashare/globeEarthquake_csn.html',
            timeout=5)
    t = [re.sub('(<[^>]*>|[\r\n])', '', a) for a in r.read().decode('gbk').encode('utf-8').split('\n')[170:178]]
    return '最近一次地震发生在%s（%s），发生时间%s，震级%s，震源深度%s千米，地震类型为%s。' %\
            (t[7], jw(t[2], t[3]), ' '.join(t[0:2]), t[5], t[4], t[6])

if __name__ == '__main__':
    print handle({'message': '地震了吗？'}, None)

########NEW FILE########
__FILENAME__ = orz
#-*-coding:utf-8-*-

"""
Copyright (c) 2012 wong2 <wonderfuly@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

# 来膜拜

import random

def test(data, bot=None):
    message = data['message']
    for word in ['膜拜', 'orz']:
        if word in message:
            return True
    return False

def handle(data, bot=None):
    mobai_icon = '(mb)'
    mobai_text = ' orz '
    return mobai_icon * random.randrange(1, 10) + mobai_text * random.randrange(3)

if __name__ == '__main__':
    print test({'message': 'orz'})
    print test({'message': 'rz'})
    print handle({'message': '来膜拜'})

########NEW FILE########
__FILENAME__ = qiubai
#!/usr/bin/env python
#-*-coding:utf-8-*-

"""
Copyright (c) 2013 Xiangyu Ye<yexiangyu1985@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

# 糗事百科TOP10
import urllib2
import re
import redis
import time
import random

try:
    from settings import REDIS_HOST
except:
    REDIS_HOST = 'localhost'

kv = redis.Redis(REDIS_HOST)

key = time.strftime('%Y-%m-%d')


def test(data, bot):
    return any(w in data['message'] for w in ['糗百', '笑话'])

def handle(data, bot):
    r = kv.lrange(key, 0, -1)
    if r:
        return random.choice(r)
    r = urllib2.urlopen('http://feed.feedsky.com/qiushi', timeout=60)
    p = r.read()
    r = re.findall('&lt;p&gt;([\s]+)([^\t]+)&lt;br/&gt;', p)
    if r:
        for l in r:
            kv.rpush(key, l[1])
        return random.choice(r)[1]
    else:
        raise Exception

if __name__ == '__main__':
    print handle({'message': '糗百'}, None)
    print handle({'message': '笑话'}, None)

########NEW FILE########
__FILENAME__ = simsimi
#-*-coding:utf-8-*-

"""
Copyright (c) 2012 wong2 <wonderfuly@gmail.com>
Copyright (c) 2012 hupili <hpl1989@gmail.com>

Original Author:
    Wong2 <wonderfuly@gmail.com>
Changes Statement:
    Changes made by Pili Hu <hpl1989@gmail.com> on
    Jan 13 2013:
        Support Keepalive by using requests.Session

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""


# 从simsimi读数据

import sys
sys.path.append('..')

import requests
import random

try:
    from settings import SIMSIMI_KEY
except:
    SIMSIMI_KEY = ''


class SimSimi:

    def __init__(self):

        self.session = requests.Session()

        self.chat_url = 'http://www.simsimi.com/func/req?lc=ch&msg=%s'
        self.api_url = 'http://api.simsimi.com/request.p?key=%s&lc=ch&ft=1.0&text=%s'

        if not SIMSIMI_KEY:
            self.initSimSimiCookie()

    def initSimSimiCookie(self):
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:18.0) Gecko/20100101 Firefox/18.0'})
        self.session.get('http://www.simsimi.com/talk.htm')
        self.session.headers.update({'Referer': 'http://www.simsimi.com/talk.htm'})
        self.session.get('http://www.simsimi.com/talk.htm?lc=ch')
        self.session.headers.update({'Referer': 'http://www.simsimi.com/talk.htm?lc=ch'})

    def getSimSimiResult(self, message, method='normal'):
        if method == 'normal':
            r = self.session.get(self.chat_url % message)
        else:
            url = self.api_url % (SIMSIMI_KEY, message)
            r = requests.get(url)
        return r

    def chat(self, message=''):
        if message:
            r = self.getSimSimiResult(message, 'normal' if not SIMSIMI_KEY else 'api')
            try:
                answer = r.json()['response'].encode('utf-8')
                return answer
            except:
                return random.choice(['呵呵', '。。。', '= =', '=。='])
        else:
            return '叫我干嘛'

simsimi = SimSimi()


def test(data, bot):
    return True


def handle(data, bot):
    return simsimi.chat(data['message'])

if __name__ == '__main__':
    print handle({'message': '最后一个问题'}, None)
    print handle({'message': '还有一个问题'}, None)
    print handle({'message': '其实我有三个问题'}, None)

########NEW FILE########
__FILENAME__ = timeout
"""
Code to timeout with processes.

   * Code is from: http://code.activestate.com/recipes/577853-timeout-decorator-with-multiprocessing/
   * Original License: MIT License

>>> @timeout(.5)
... def sleep(x):
...     print "ABOUT TO SLEEP {0} SECONDS".format(x)
...     time.sleep(x)
...     return x

>>> sleep(1)
Traceback (most recent call last):
   ...
TimeoutException: timed out after 0 seconds

>>> sleep(.2)
0.2

>>> @timeout(.5)
... def exc():
...     raise Exception('Houston we have problems!')

>>> exc()
Traceback (most recent call last):
   ...
Exception: Houston we have problems!

"""
import multiprocessing
import time
#import logging
#logger = multiprocessing.log_to_stderr()
#logger.setLevel(logging.INFO)


class TimeoutException(Exception):
    pass


class RunableProcessing(multiprocessing.Process):
    def __init__(self, func, *args, **kwargs):
        self.queue = multiprocessing.Queue(maxsize=1)
        args = (func,) + args
        multiprocessing.Process.__init__(self, target=self.run_func, args=args, kwargs=kwargs)

    def run_func(self, func, *args, **kwargs):
        try:
            result = func(*args, **kwargs)
            self.queue.put((True, result))
        except Exception as e:
            self.queue.put((False, e))

    def done(self):
        return self.queue.full()

    def result(self):
        return self.queue.get()


def timeout(seconds, force_kill=True):
    def wrapper(function):
        def inner(*args, **kwargs):
            now = time.time()
            proc = RunableProcessing(function, *args, **kwargs)
            proc.start()
            proc.join(seconds)
            if proc.is_alive():
                if force_kill:
                    proc.terminate()
                runtime = int(time.time() - now)
                raise TimeoutException('timed out after {0} seconds'.format(runtime))
            assert proc.done()
            success, result = proc.result()
            if success:
                return result
            else:
                raise result
        return inner
    return wrapper


if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = visit
#-*-coding:utf-8-*-

"""
Copyright (c) 2012 wong2 <wonderfuly@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

# 求来访功能

import random

def test(data, bot):
    return '求来访' in data['message']

def handle(data, bot):
    bot.visit(data.get('author_id', data['owner_id']))
    return random.choice(['我来也', '马上就到', '来啦', '在路上了'])

if __name__ == '__main__':
    print test({'message': '小鸡鸡求来访'})

########NEW FILE########
__FILENAME__ = weather
#!/usr/bin/env python
#-*-coding:utf-8-*-

"""
Copyright (c) 2013 Qimin Huang <qiminis0801@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

# 天气
import os
import requests
import cPickle as pickle


def city(data):
    cityidDict = pickle.load(file(os.path.join(os.path.dirname(__file__), 'data' + os.path.sep + 'cityid'), 'r'))
    for city in cityidDict:
        if city.encode('utf8') in data['message']:
            return True
    return False


def test(data, bot):
    return '天气' in data['message'] and city(data)


def weather(cityid):
    try:
        weatherinfo = requests.get('http://www.weather.com.cn/data/cityinfo/' + cityid + '.html').json()['weatherinfo']
        return (weatherinfo['city'] + ', ' + weatherinfo['weather'] + ', ' + weatherinfo['temp1'] + ' ~ ' + weatherinfo['temp2']).encode('utf8')
    except:
        return 0


def handle(data, bot):
    cityidDict = pickle.load(file(os.path.join(os.path.dirname(__file__), 'data' + os.path.sep + 'cityid'), 'r'))
    for city in cityidDict:
        if city.encode('utf8') in data['message']:
            reply = weather(cityidDict[city])
            return reply if reply else '不会自己去看天气预报啊'


if __name__ == '__main__':
    print test({'message': '天气怎么样'}, None)
    print test({'message': '北京天气怎么样'}, None)
    print handle({'message': '北京天气怎么样', 'author_id': 'HQM'}, None)

########NEW FILE########
__FILENAME__ = wikipedia
#-*-coding:utf-8-*-

"""
Copyright (c) 2012 yangzhe1991 <ud1937@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

    The above copyright notice and this permission notice shall be
    included in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
    IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
    CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
    TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
    SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

# 维基百科

from pyquery import PyQuery
import requests
import re

def test(data, bot=None):
    return '什么是' in data['message']

def handle(data, bot=None):
    m = re.search('(?<=什么是)(.+?)(?=啊|那|呢|哈|！|。|？|\?|\s|\Z)', data['message'])
    if m and m.groups():
        return wikipedia(m.groups()[0])
    raise Exception

def wikipedia(title):
    r = requests.get('http://zh.wikipedia.org/w/index.php', params={'title': title, 'printable': 'yes', 'variant': 'zh-cn'}, timeout=10)
    dom = PyQuery(r.text)
    return dom('#mw-content-text > p:first').remove('sup')[0].text_content()

if __name__ == '__main__':
    for message in ['什么是SVM  ????', '什么是薛定谔方程啊', '什么是CSS？']:
        data = { 'message': message }
        print message, test(data)
        if test(data):
            print handle(data)

########NEW FILE########
__FILENAME__ = renren
#-*-coding:utf-8-*-

"""
Copyright (c) 2012 wong2 <wonderfuly@gmail.com>
Copyright (c) 2012 hupili <hpl1989@gmail.com>

Original Author:
    Wong2 <wonderfuly@gmail.com>
Changes Statement:
    Changes made by Pili Hu <hpl1989@gmail.com> on
    Jan 10 2013:
        Support captcha.

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""


# 人人各种接口

import requests
import json
import re
import random
from pyquery import PyQuery
from encrypt import encryptString
import os


class RenRen:

    def __init__(self, email=None, pwd=None):
        self.session = requests.Session()
        self.token = {}

        if email and pwd:
            self.login(email, pwd)

    def _loginByCookie(self, cookie_str):
        cookie_dict = dict([v.split('=', 1) for v in cookie_str.strip().split(';')])
        self.session.cookies = requests.utils.cookiejar_from_dict(cookie_dict)

        self.getToken()

    def loginByCookie(self, cookie_path):
        with open(cookie_path) as fp:
            cookie_str = fp.read()

        self._loginByCookie(cookie_str)

    def saveCookie(self, cookie_path):
        with open(cookie_path, 'w') as fp:
            cookie_dict = requests.utils.dict_from_cookiejar(self.session.cookies)
            cookie_str = '; '.join([k + '=' + v for k, v in cookie_dict.iteritems()])
            fp.write(cookie_str)

    def login(self, email, pwd):
        key = self.getEncryptKey()

        if self.getShowCaptcha(email) == 1:
            fn = 'icode.%s.jpg' % os.getpid()
            self.getICode(fn)
            print "Please input the code in file '%s':" % fn
            icode = raw_input().strip()
            os.remove(fn)
        else:
            icode = ''

        data = {
            'email': email,
            'origURL': 'http://www.renren.com/home',
            'icode': icode,
            'domain': 'renren.com',
            'key_id': 1,
            'captcha_type': 'web_login',
            'password': encryptString(key['e'], key['n'], pwd) if key['isEncrypt'] else pwd,
            'rkey': key['rkey']
        }
        print "login data: %s" % data
        url = 'http://www.renren.com/ajaxLogin/login?1=1&uniqueTimestamp=%f' % random.random()
        r = self.post(url, data)
        result = r.json()
        if result['code']:
            print 'login successfully'
            self.email = email
            r = self.get(result['homeUrl'])
            self.getToken(r.text)
        else:
            print 'login error', r.text

    def getICode(self, fn):
        r = self.get("http://icode.renren.com/getcode.do?t=web_login&rnd=%s" % random.random())
        if r.status_code == 200 and r.raw.headers['content-type'] == 'image/jpeg':
            with open(fn, 'wb') as f:
                for chunk in r.iter_content():
                    f.write(chunk)
        else:
            print "get icode failure"

    def getShowCaptcha(self, email=None):
        r = self.post('http://www.renren.com/ajax/ShowCaptcha', data={'email': email})
        return r.json()

    def getEncryptKey(self):
        r = requests.get('http://login.renren.com/ajax/getEncryptKey')
        return r.json()

    def getToken(self, html=''):
        p = re.compile("get_check:'(.*)',get_check_x:'(.*)',env")

        if not html:
            r = self.get('http://www.renren.com')
            html = r.text

        result = p.search(html)
        self.token = {
            'requestToken': result.group(1),
            '_rtk': result.group(2)
        }

    def request(self, url, method, data={}):
        if data:
            data.update(self.token)

        if method == 'get':
            return self.session.get(url, data=data)
        elif method == 'post':
            return self.session.post(url, data=data)

    def get(self, url, data={}):
        return self.request(url, 'get', data)

    def post(self, url, data={}):
        return self.request(url, 'post', data)

    def getUserInfo(self):
        r = self.get('http://notify.renren.com/wpi/getonlinecount.do')
        return r.json()

    def getNotifications(self):
        url = 'http://notify.renren.com/rmessage/get?getbybigtype=1&bigtype=1&limit=50&begin=0&view=17'
        r = self.get(url)
        try:
            result = json.loads(r.text, strict=False)
        except Exception, e:
            print 'error', e
            result = []
        return result

    def removeNotification(self, notify_id):
        self.get('http://notify.renren.com/rmessage/remove?nl=' + str(notify_id))

    def getDoings(self, uid, page=0):
        url = 'http://status.renren.com/GetSomeomeDoingList.do?userId=%s&curpage=%d' % (str(uid), page)
        r = self.get(url)
        return r.json().get('doingArray', [])

    def getDoingById(self, owner_id, doing_id):
        doings = self.getDoings(owner_id)
        doing = filter(lambda doing: doing['id'] == doing_id, doings)
        return doing[0] if doing else None

    def getDoingComments(self, owner_id, doing_id):
        url = 'http://status.renren.com/feedcommentretrieve.do'
        r = self.post(url, {
            'doingId': doing_id,
            'source': doing_id,
            'owner': owner_id,
            't': 3
        })

        return r.json()['replyList']

    def getCommentById(self, owner_id, doing_id, comment_id):
        comments = self.getDoingComments(owner_id, doing_id)
        comment = filter(lambda comment: comment['id'] == int(comment_id), comments)
        return comment[0] if comment else None

    def addComment(self, data):
        return {
            'status': self.addStatusComment,
            'album' : self.addAlbumComment,
            'photo' : self.addPhotoComment,
            'blog'  : self.addBlogComment,
            'share' : self.addShareComment,
            'gossip': self.addGossip
        }[data['type']](data)

    def sendComment(self, url, payloads):
        r = self.post(url, payloads)
        r.raise_for_status()
        try:
            return r.json()
        except:
            return { 'code': 0 }

    # 评论状态
    def addStatusComment(self, data):
        url = 'http://status.renren.com/feedcommentreply.do'

        payloads = {
            't': 3,
            'rpLayer': 0,
            'source': data['source_id'],
            'owner': data['owner_id'],
            'c': data['message']
        }

        if data.get('reply_id', None):
            payloads.update({
                'rpLayer': 1,
                'replyTo': data['author_id'],
                'replyName': data['author_name'],
                'secondaryReplyId': data['reply_id'],
                'c': '回复%s：%s' % (data['author_name'].encode('utf-8'), data['message'])
            })

        return self.sendComment(url, payloads)

    # 回复留言
    def addGossip(self, data):
        url = 'http://gossip.renren.com/gossip.do'
        
        payloads = {
            'id': data['owner_id'], 
            'only_to_me': 1,
            'mode': 'conversation',
            'cc': data['author_id'],
            'body': data['message'],
            'ref':'http://gossip.renren.com/getgossiplist.do'
        }

        return self.sendComment(url, payloads)

    # 回复分享
    def addShareComment(self, data):
        url = 'http://share.renren.com/share/addComment.do'

        if data.get('reply_id', None):
            body = '回复%s：%s' % (data['author_name'].encode('utf-8'), data['message']),
        else:
            body = data['message']
        
        payloads = {
            'comment': body,
            'shareId' : data['source_id'],
            'shareOwner': data['owner_id'],
            'replyToCommentId': data.get('reply_id', 0),
            'repetNo' : data.get('author_id', 0)
        }

        return self.sendComment(url, payloads)

    # 回复日志
    def addBlogComment(self, data):
        url = 'http://blog.renren.com/PostComment.do'
        
        payloads = {
            'body': '回复%s：%s' % (data['author_name'].encode('utf-8'), data['message']),
            'feedComment': 'true',
            'guestName': '小黄鸡', 
            'id' : data['source_id'],
            'only_to_me': 0,
            'owner': data['owner_id'],
            'replyCommentId': data['reply_id'],
            'to': data['author_id']
        }

        return self.sendComment(url, payloads)

    # 回复相册
    def addAlbumComment(self, data):
        url = 'http://photo.renren.com/photo/%d/album-%d/comment' % (data['owner_id'], data['source_id'])
        
        payloads = {
            'id': data['source_id'],
            'only_to_me' : 'false',
            'body': '回复%s：%s' % (data['author_name'].encode('utf-8'), data['message']),
            'feedComment' : 'true', 
            'owner' : data['owner_id'],
            'replyCommentId' : data['reply_id'],
            'to' : data['author_id']
        }

        return self.sendComment(url, payloads)

    def addPhotoComment(self, data):
        url = 'http://photo.renren.com/photo/%d/photo-%d/comment' % (data['owner_id'], data['source_id'])

        if 'author_name' in data:
            body = '回复%s：%s' % (data['author_name'].encode('utf-8'), data['message']),
        else:
            body = data['message']
        
        payloads = {
            'guestName': '小黄鸡',
            'feedComment' : 'true',
            'body': body,
            'owner' : data['owner_id'],
            'realWhisper':'false',
            'replyCommentId' : data.get('reply_id', 0),
            'to' : data.get('author_id', 0)
        }

        return self.sendComment(url, payloads)

    # 访问某人页面
    def visit(self, uid):
        self.get('http://www.renren.com/' + str(uid) + '/profile')

    # 根据关键词搜索最新状态(全站)
    def searchStatus(self, keyword, max_length=20):
        url = 'http://browse.renren.com/s/status?offset=0&sort=1&range=0&q=%s&l=%d' % (keyword, max_length)
        r = self.session.get(url, timeout=5)
        status_elements = PyQuery(r.text)('.list_status .status_content')
        id_pattern  = re.compile("forwardDoing\('(\d+)','(\d+)'\)")
        results = []
        for index, _ in enumerate(status_elements):
            status_element = status_elements.eq(index)

            # 跳过转发的
            if status_element('.status_root_msg'):
                continue

            status_element = status_element('.status_content_footer')
            status_time = status_element('span').text()
            m = id_pattern.search(status_element('.share_status').attr('onclick'))
            status_id, user_id = m.groups()
            results.append( (int(user_id), int(status_id), status_time) )
        return results

if __name__ == '__main__':
    renren = RenRen()
    renren.login('email', 'password')
    info = renren.getUserInfo()
    print 'hello', info['hostname']
    print renren.searchStatus('么么哒')

########NEW FILE########
__FILENAME__ = rqworker
#!/usr/bin/env python
import sys
import argparse
import logbook
from logbook import handlers
from rq import Queue, Worker
from redis.exceptions import ConnectionError
from rq.scripts import add_standard_arguments
from rq.scripts import setup_redis
from rq.scripts import read_config_file
from rq.scripts import setup_default_arguments

from controller import bots, getNotiData, self_match_pattern
from failure_handler import do_job_failure_handler_have_a_rest
from ai import plugin_modules

def format_colors(record, handler):
    from rq.utils import make_colorizer
    if record.level == logbook.WARNING:
        colorize = make_colorizer('darkyellow')
    elif record.level >= logbook.ERROR:
        colorize = make_colorizer('darkred')
    else:
        colorize = lambda x: x
    return '%s: %s' % (record.time.strftime('%H:%M:%S'), colorize(record.msg))


def setup_loghandlers(args):
    if args.verbose:
        loglevel = logbook.DEBUG
        formatter = None
    else:
        loglevel = logbook.INFO
        formatter = format_colors

    handlers.NullHandler(bubble=False).push_application()
    handler = handlers.StreamHandler(sys.stdout, level=loglevel, bubble=False)
    if formatter:
        handler.formatter = formatter
    handler.push_application()
    handler = handlers.StderrHandler(level=logbook.WARNING, bubble=False)
    if formatter:
        handler.formatter = formatter
    handler.push_application()


def parse_args():
    parser = argparse.ArgumentParser(description='Starts an RQ worker.')
    add_standard_arguments(parser)

    parser.add_argument('--burst', '-b', action='store_true', default=False, help='Run in burst mode (quit after all work is done)')
    parser.add_argument('--name', '-n', default=None, help='Specify a different name')
    parser.add_argument('--path', '-P', default='.', help='Specify the import path.')
    parser.add_argument('--verbose', '-v', action='store_true', default=False, help='Show more output')
    parser.add_argument('--sentry-dsn', action='store', default=None, metavar='URL', help='Report exceptions to this Sentry DSN')
    parser.add_argument('queues', nargs='*', default=['default'], help='The queues to listen on (default: \'default\')')

    return parser.parse_args()


def main():
    args = parse_args()

    if args.path:
        sys.path = args.path.split(':') + sys.path

    settings = {}
    if args.config:
        settings = read_config_file(args.config)

    setup_default_arguments(args, settings)

    # Other default arguments
    if args.sentry_dsn is None:
        args.sentry_dsn = settings.get('SENTRY_DSN', None)

    setup_loghandlers(args)
    setup_redis(args)
    try:
        queues = map(Queue, args.queues)
        w = Worker(queues, name=args.name)
        w.push_exc_handler(do_job_failure_handler_have_a_rest)

        # Should we configure Sentry?
        if args.sentry_dsn:
            from raven import Client
            from rq.contrib.sentry import register_sentry
            client = Client(args.sentry_dsn)
            register_sentry(client, w)

        w.work(burst=args.burst)
    except ConnectionError as e:
        print(e)
        sys.exit(1)

if __name__ == '__main__':
    reload(sys)
    sys.setdefaultencoding(sys.getfilesystemencoding())
    main()

########NEW FILE########
__FILENAME__ = test_airpollution
# -*- coding: utf-8 -*-

"""
Copyright (c) 2013 wgx731 <wgx731@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

""" Airpollution plugin test

    Test Cases for xiaohuangji airpollution plugin
"""

__author__ = 'wgx731'
__copyright__ = 'Copyright (c) 2013 wgx731'
__license__ = 'MIT'
__version__ = '0.1'
__maintainer__ = 'wgx731'
__email__ = 'wgx731@gmail.com'
__status__ = 'development'

from nose.tools import ok_
from nose.tools import eq_
from test_config import *
from ..plugins import airpollution

sys.path = [TEST_DIR] + sys.path


class TestAirPollution(TestBase):

    def setup(self):
        pass

    def teardown(self):
        pass

    #TODO: Add unit test for airpollution plugin
    def test_airpollution_test_1(self):
        eq_(False, airpollution.test({'message': 'wrong key'}, None), WRONG_KEY_WORD_ERROR)


########NEW FILE########
__FILENAME__ = test_arithmetic
# -*- coding: utf-8 -*-

"""
Copyright (c) 2013 Pili Hu <hpl1989@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

""" Arithmetic plugin test

    Test Cases for xiaohuangji Arithmetic plugin
"""

__author__ = 'hupili'
__copyright__ = 'Copyright (c) 2013 hupili'
__license__ = 'MIT'
__version__ = '0.1'
__maintainer__ = 'hupili'
__email__ = 'hpl1989@gmail.com'
__status__ = 'development'

from nose.tools import ok_
from nose.tools import eq_
from test_config import *
from ..plugins import arithmetic

sys.path = [TEST_DIR] + sys.path


class TestArithmetic(TestBase):

    def setup(self):
        pass

    def teardown(self):
        pass

    def test_arithmetic_test(self):
        _ut_test('hello', False)
        _ut_test('2 * 4+ 5/3 = ?', True)
        _ut_test('x *4+ 5/3 =?', True)
        _ut_test('2 * 4+ 5/3= ？', True)
        _ut_test('2 * 4+ 5/3 是多少', True)
        _ut_test('2 * 4+ 5/3 是几', True)
        _ut_test('2 * 4+ 5/3 等于多少', True)
        _ut_test('2 * 4+ 5/3 等于几', True)
        _ut_test('sys.exit(-1)', False)
        _ut_test('sys.exit(-1) = ?', True)
        _ut_test('sin(pi/2)=?', True)
        _ut_test('x^(1+3)=?', True)

    def test_arithmetic_handle_normal_basic(self):
        _ut_handle('2 * 4+ 5/3 = ?', '不就是29/3嘛。啦啦啦……我是计算鸡…… ＼（￣︶￣）／')
        _ut_handle('2 * 4+ 5/3= ？', '不就是29/3嘛。啦啦啦……我是计算鸡…… ＼（￣︶￣）／')
        _ut_handle('2 * 4+ 5/3 是多少', '不就是29/3嘛。啦啦啦……我是计算鸡…… ＼（￣︶￣）／')
        _ut_handle('2 * (4+ 5)/3 是几', '不就是6嘛。啦啦啦……我是计算鸡…… ＼（￣︶￣）／')
        _ut_handle('2 * 4+ 5/(3.0) 是几', '不就是9.66666666666667嘛。啦啦啦……我是计算鸡…… ＼（￣︶￣）／')
        # The matched part is "(-1)" not "sys.exit(-1)"
        _ut_handle('sys.exit(-1) = ?', '好复杂哦，计算鸡也不会了 ╮(︶︿︶)╭')

    def test_arithmetic_handle_normal_advanced(self):
        _ut_handle('sin(pi/2)=?', '不就是1嘛。啦啦啦……我是计算鸡…… ＼（￣︶￣）／')
        _ut_handle('atan(1)=?', '不就是pi/4嘛。啦啦啦……我是计算鸡…… ＼（￣︶￣）／')
        _ut_handle('integrate(x * e ** (-x), x)=?', '不就是-e^(-x)*x/log(e) - e^(-x)/log(e)^2嘛。啦啦啦……我是计算鸡…… ＼（￣︶￣）／')

    def test_arithmetic_handle_with_pre_and_post_process(self):
        # Test the conversion between "^" and "**"
        _ut_handle('x^(1+3)=?', '不就是x^4嘛。啦啦啦……我是计算鸡…… ＼（￣︶￣）／')

    def test_arithmetic_handle_exception(self):
        # Syntax error
        _ut_handle(' *4+ 5/3 =?', '(´･д･`) 这明显有问题嘛！！你确定没写错？')
        # The following is originally Syntax error.
        # After allowing letters in expression, it is no longer syntax error.
        # Also, sympy will retain x as a symbol.
        _ut_handle('x *4+ 5/3 =?', '不就是4*x + 5/3嘛。啦啦啦……我是计算鸡…… ＼（￣︶￣）／')
        # Zero division: error in Python eval; infinity in sympy
        #_ut_handle('2 * 4+ 5/0 是几', '你好笨啊！除零了。跟小鸡学下四则运算吧 （＃￣▽￣＃）')
        _ut_handle('2 * 4+ 5/0 是几', '不就是oo嘛。啦啦啦……我是计算鸡…… ＼（￣︶￣）／')
        # Long input expression
        _ut_handle('1' + ('+1' * (arithmetic.AI_ARITHMETIC_MAX_LEN_EXP / 2 - 1)) + '=?',
                   '不就是%d嘛。啦啦啦……我是计算鸡…… ＼（￣︶￣）／' % (arithmetic.AI_ARITHMETIC_MAX_LEN_EXP / 2))
        _ut_handle('1' + ('+1' * (arithmetic.AI_ARITHMETIC_MAX_LEN_EXP / 2)) + '=?', '太长了……小鸡才不算呢。╮(︶︿︶)╭')
        _ut_handle(('1' * (arithmetic.AI_ARITHMETIC_MAX_LEN_REPLY)) + '=?',
                   '不就是%s嘛。啦啦啦……我是计算鸡…… ＼（￣︶￣）／' % ('1' * (arithmetic.AI_ARITHMETIC_MAX_LEN_REPLY)))
        _ut_handle(('1' * (arithmetic.AI_ARITHMETIC_MAX_LEN_REPLY + 1)) + '=?', '这个数字太长了！鸡才懒得回你呢╮(︶︿︶)╭')

    def test_arithmetic_handle_false_flow(self):
        # The following text will not get True from test(). It will not
        # reach handle(). Verify whether we handle it correctly if this
        # happens due to incorrect configuration.
        _ut_handle('sys.exit(-1)', '好复杂哦，计算鸡也不会了 ╮(︶︿︶)╭ （怎么会这样？）')

    def test_arithmetic_handle_timeout(self):
        _ut_handle('2**' + ('9' * (arithmetic.AI_ARITHMETIC_MAX_LEN_EXP - 3)) + '=?', '太难了，计算鸡半天都算不出来 ╮(︶︿︶)╭')


def _ut_test(exp, ret):
    eq_(ret, arithmetic.test({'message': exp}, None), WRONG_RESULT_ERROR)


def _ut_handle(exp, ret):
    print exp, ': ', ret, '\n'
    eq_(ret, arithmetic.handle({'message': exp}, None), WRONG_RESULT_ERROR)

########NEW FILE########
__FILENAME__ = test_calc24
# -*- coding: utf-8 -*-

"""
Copyright (c) 2013 Moody _"Kuuy"_ Wizmann <mail.kuuy@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

""" Calc24 plugin test """

__author__ = 'Moody _"Kuuy"_ Wizmann'
__copyright__ = 'Copyright (c) 2013 Wizmann'
__license__ = 'MIT'
__version__ = '0.1'
__maintainer__ = 'Wizmann'
__email__ = 'mail.kuuy@gmail.com'
__status__ = 'development'

from nose.tools import ok_
from nose.tools import eq_
from test_config import *
from ..plugins import calc24

sys.path = [TEST_DIR] + sys.path


class TestCalc24(TestBase):

    def setup(self):
        pass

    def teardown(self):
        pass

    def test_calc24_test_1(self):
        eq_(False, calc24.test({'message': 'Hello World 24'}, None),
            WRONG_KEY_WORD_ERROR)

    def test_calc24_test_2(self):
        eq_(False, calc24.test({'message': 'Hello World 算24点'}, None),
            WRONG_KEY_WORD_ERROR)

    def test_calc24_test_3(self):
        eq_(True, calc24.test({'message': 'Hello World 算24点 [1,2,4,5]'},
            None), WRONG_RESULT_ERROR)

    def test_calc24_test_4(self):
        eq_(True, calc24.test({'message': 'Hello World 算1234567点 [1,2,4,5]'},
            None), WRONG_RESULT_ERROR)

    def test_calc24_test_5(self):
        eq_(True, calc24.test({'message': 'Hello World 算-123点 [1,2,4,5]'},
            None), WRONG_RESULT_ERROR)

    def test_calc24_test_6(self):
        eq_(True, calc24.test({'message': 'Hello World 算-点 [1,2,4,5]'},
            None), WRONG_RESULT_ERROR)

    def test_calc24_handle_1(self):
        result = calc24.handle({'message': 'Hello World 算24点 [1,2,4,5]',
                                'author_id': 'Wizmann'}, None)
        eq_(True, '答案' in result, WRONG_RESULT_FORMAT_ERROR)

    def test_calc24_handle_2(self):
        result = calc24.handle({'message': 'Hello World 算24点 [A,A,A,A]',
                                'author_id': 'Wizmann'}, None)
        eq_(True, '答案' in result, WRONG_RESULT_FORMAT_ERROR)

    def test_calc24_handle_3(self):
        result = calc24.handle({'message': 'Hello World 算24点 [Z,U,C,K]',
                                'author_id': 'Kuuy'}, None)
        eq_(True, '没有那种牌' in result, WRONG_RESULT_FORMAT_ERROR)

    def test_calc24_handle_4(self):
        result = calc24.handle({'message': 'Hello World 算24点 [F,U,C,K]',
                                'author_id': 'Kuuy'}, None)
        eq_(True, 'Wizmann' in result, WRONG_RESULT_FORMAT_ERROR)

    def test_calc24_handle_5(self):
        result = calc24.handle({'message': 'Hello World 算24点 [3,8,3,8]',
                                'author_id': 'Wizmann'}, None)
        eq_(True, '答案' in result, WRONG_RESULT_FORMAT_ERROR)

    def test_calc24_handle_6(self):
        result = calc24.handle({'message': 'Hello World 算576点 [3,8,3,8]',
                                'author_id': 'Wizmann'}, None)
        eq_(True, '答案' in result, WRONG_RESULT_FORMAT_ERROR)

########NEW FILE########
__FILENAME__ = test_config
#-*-coding:utf-8-*-

"""
Copyright (c) 2012 wgx731 <wgx731@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

""" Nose test config file

    config sys path for testing
"""

import os
import glob
import sys


TEST_DIR = os.path.abspath(os.path.dirname(__file__))
MAIN_CODE_DIR = os.path.abspath(os.path.join(TEST_DIR, os.path.pardir))
PLUGINS_CODE_DIR = os.path.abspath(os.path.join(MAIN_CODE_DIR, "plugins"))

# Result refers to result returned by plugin
WRONG_KEY_WORD_ERROR = "Missing or wrong keyword should not have result."
WRONG_RESULT_ERROR = "Correct keyword should have result."
WRONG_RESULT_FORMAT_ERROR = "Result should have correct format."


class TestBase(object):

    @classmethod
    def clean_up(klass, path, wildcard):
        os.chdir(path)
        for rm_file in glob.glob(wildcard):
            os.unlink(rm_file)

    @classmethod
    def setup_class(klass):
        sys.stderr.write("\nRunning %s\n" % klass)

    @classmethod
    def teardown_class(klass):
        klass.clean_up(TEST_DIR, "*.py?")
        klass.clean_up(PLUGINS_CODE_DIR, "*.py?")
        klass.clean_up(MAIN_CODE_DIR, "*.py?")

########NEW FILE########
__FILENAME__ = test_earthquake
# -*- coding: utf-8 -*-

"""
Copyright (c) 2013 wgx731 <wgx731@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

""" Earthquake plugin test

    Test Cases for xiaohuangji earthquake plugin
"""

__author__ = 'wgx731'
__copyright__ = 'Copyright (c) 2013 wgx731'
__license__ = 'MIT'
__version__ = '0.1'
__maintainer__ = 'wgx731'
__email__ = 'wgx731@gmail.com'
__status__ = 'development'

from nose.tools import ok_
from nose.tools import eq_
from test_config import *
from ..plugins import earthquake

sys.path = [TEST_DIR] + sys.path


class TestEarthQuake(TestBase):

    def setup(self):
        pass

    def teardown(self):
        pass

    def test_earthquake_test_1(self):
        eq_(False, earthquake.test({'message': '地'}, None), WRONG_KEY_WORD_ERROR)

    def test_earthquake_test_2(self):
        eq_(True, earthquake.test({'message': '地震了吗？'}, None), WRONG_RESULT_ERROR)

    #TODO: Add better unit test
    def test_earthquake_handle_1(self):
        eq_(True, "最近一次地震发生在" in earthquake.handle({'message': '地震了吗？'}, None), WRONG_RESULT_FORMAT_ERROR)

########NEW FILE########
__FILENAME__ = test_qiubai
# -*- coding: utf-8 -*-

"""
Copyright (c) 2013 Xiangyu Ye<yexiangyu1985@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

""" QiuBai plugin test
"""

from nose.tools import ok_
from nose.tools import eq_
from test_config import *
from ..plugins import qiubai

sys.path = [TEST_DIR] + sys.path


class TestQiuBai(TestBase):

    def setup(self):
        pass

    def teardown(self):
        pass

    def test_qiubai_test_1(self):
        eq_(False, qiubai.test({'message': '讲个感人的故事吧'}, None), WRONG_KEY_WORD_ERROR)

    def test_qiubai_test_2(self):
        eq_(True, qiubai.test({'message': '给我讲个笑话吧'}, None), WRONG_RESULT_ERROR)

    def test_qiubai_test_3(self):
        eq_(True, qiubai.test({'message': '给我讲个糗百上的故事吧'}, None), WRONG_RESULT_ERROR)

    #TODO: Add better unit test
    def test_qiubai_handle_1(self):
        eq_(True, qiubai.handle({'message': '讲个笑话吧'}, None) != '', WRONG_RESULT_FORMAT_ERROR)

########NEW FILE########
__FILENAME__ = test_simsimi
# -*- coding: utf-8 -*-

"""
Copyright (c) 2013 wgx731 <wgx731@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

""" Simsimi plugin test

    Test Cases for xiaohuangji Simsimi plugin
"""

__author__ = 'wgx731'
__copyright__ = 'Copyright (c) 2013 wgx731'
__license__ = 'MIT'
__version__ = '0.1'
__maintainer__ = 'wgx731'
__email__ = 'wgx731@gmail.com'
__status__ = 'development'

from nose.tools import ok_
from nose.tools import eq_
from test_config import *
from ..plugins import simsimi

sys.path = [TEST_DIR] + sys.path


class TestSimsimi(TestBase):

    def setup(self):
        pass

    def teardown(self):
        pass

    def test_simsimi_test_1(self):
        eq_(True, simsimi.test({'message': '最后一个问题'}, None), WRONG_RESULT_ERROR)

    #TODO: add better unit test
    def test_simsimi_handle_1(self):
        eq_(True, len(simsimi.handle({'message': '最后一个问题'}, None)) > 0, WRONG_RESULT_FORMAT_ERROR)

########NEW FILE########
__FILENAME__ = test_visit
# -*- coding: utf-8 -*-

"""
Copyright (c) 2013 wgx731 <wgx731@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

""" Visit plugin test

    Test Cases for xiaohuangji visit plugin
"""

__author__ = 'wgx731'
__copyright__ = 'Copyright (c) 2013 wgx731'
__license__ = 'MIT'
__version__ = '0.1'
__maintainer__ = 'wgx731'
__email__ = 'wgx731@gmail.com'
__status__ = 'development'

from nose.tools import ok_
from nose.tools import eq_
from test_config import *
from ..plugins import visit

sys.path = [TEST_DIR] + sys.path


class TestVisit(TestBase):

    def setup(self):
        pass

    def teardown(self):
        pass

    def test_visit_test_1(self):
        eq_(False, visit.test({'message': '别来访'}, None), WRONG_KEY_WORD_ERROR)

    def test_visit_test_2(self):
        eq_(True, visit.test({'message': '求来访'}, None), WRONG_RESULT_ERROR)

########NEW FILE########
__FILENAME__ = test_weather
# -*- coding: utf-8 -*-

"""
Copyright (c) 2013 wgx731 <wgx731@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

""" Weather plugin test

    Test Cases for xiaohuangji weather plugin
"""

__author__ = 'wgx731'
__copyright__ = 'Copyright (c) 2013 wgx731'
__license__ = 'MIT'
__version__ = '0.1'
__maintainer__ = 'wgx731'
__email__ = 'wgx731@gmail.com'
__status__ = 'development'

from nose.tools import ok_
from nose.tools import eq_
from test_config import *
from ..plugins import weather

sys.path = [TEST_DIR] + sys.path


class TestWeather(TestBase):

    def setup(self):
        pass

    def teardown(self):
        pass

    def test_weather_test_1(self):
        eq_(False, weather.test({'message': '天气怎么样'}, None), WRONG_KEY_WORD_ERROR)

    def test_weather_test_2(self):
        eq_(True, weather.test({'message': '北京天气怎么样'}, None), WRONG_RESULT_ERROR)

    #TODO: Add better unit test
    def test_weather_handle_1(self):
        result = weather.handle({'message': '北京天气怎么样', 'author_id': 'HQM'}, None)
        eq_(True, '北京,' in result and '℃ ' in result, WRONG_RESULT_FORMAT_ERROR)

########NEW FILE########
__FILENAME__ = crawl_info_config
#-*-coding:utf-8-*-

# 主动回复的一些配置

crawl_info_list = [
    {
        'keywords' : ['求安慰', '想死的心'],
        'responses': ['pat pat', '摸摸', '唔...', '>_<', '安慰你', '怎么了?']
    },
    {
        'keywords' : ['吓死我了'],
        'responses': ['不要怕，有我呢', '摸摸，不要怕']
    },
    {
        'keywords' : ['气死我了'],
        'responses': ['不要生气啦', '大爷您消消气']
    },
    {
        'keywords' : ['晚安'],
        'responses': ['晚安~', '早点睡~']
    },
    {
        'keywords' : ['生日快乐'],
        'responses': ['有人过生日？生日快乐！', '生日快乐！', '我说句生日快乐，有蛋糕吃么!']
    },
    {
        'keywords' : ['无聊死了'],
        'responses': ['无聊就来和我聊天吧~', '我也很无聊...>_<']
    },
    {
        'keywords' : ['睡不着'],
        'responses': ['我也睡不着(其实我都不睡觉的>_<)', '数绵羊试过了么?', '我也睡不着...', '实在睡不着就陪我聊天吧～']
    }
]

########NEW FILE########
__FILENAME__ = crawl_to_chat
#-*-coding:utf-8-*-

# 主动聊天

import sys
sys.path.append('..')

import random
from redis import Redis
from renren import RenRen
from my_accounts import accounts
import time
from crawl_info_config import crawl_info_list

kv = Redis(host='localhost')
account = accounts[0]
bot = RenRen(account[0], account[1])

def handle(keyword, responses):
    statuses = bot.searchStatus(keyword, max_length=10)
    for status in statuses:
        user_id, status_id, status_time = status
        status_id_hash = int(str(status_id)[1:])
        if not kv.getbit('status_record', status_id_hash):
            print keyword, user_id, status_id, status_time
            bot.addComment({
                'type': 'status',
                'source_id': status_id,
                'owner_id': user_id,
                'message': random.choice(responses)
            })
            kv.setbit('status_record', status_id_hash, 1)

def main():
    for crawl_info in crawl_info_list:
        for keyword in crawl_info['keywords']:
            try:
                handle(keyword, crawl_info['responses'])
            except Exception, e:
                print e
                continue

if __name__ == '__main__':
    while True:
        print 'fetching...'
        main()
        time.sleep(30)

########NEW FILE########
