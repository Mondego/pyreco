__FILENAME__ = apnsagent-server
#!/usr/bin/env python

from apnsagent import constants
from apnsagent import guard

if __name__ == '__main__':
    guard.execute()
########NEW FILE########
__FILENAME__ = client
#encoding=utf-8

import redis
import constants
import socket
import time
import simplejson


class PushClient(object):
    """推送服务的客户端，负责把消息扔进推送主队列即可。
    """

    def __init__(self, app_key, server_info={}):
        """建立推送客户端。
        - app_key 客户端的app_key,前期为局域网内部的服务，暂不作有效性检测。
        - server_info 连接推送服务后端的信息
        """
        self.app_key = app_key
        self.redis = redis.Redis(**server_info)
        self._socket = None
        self.server_conf = None

    def get_server_conf(self):
        """获得app对应的推送服务器配置信息
        """
        if not self.server_conf:
            d = {}
            d['production'] = self.redis.hgetall('config:' + self.app_key)
            d['develop'] = self.redis.hgetall('config_dev:' + self.app_key)
            self.server_conf = d
        return self.server_conf

    def register_token(self, token, user_id=None, develop=False):
        """添加Token到服务器，并标识是何种类型的，测试或生产
        Arguments:
        - `self`:
        - `token`:
        - `user_id`: token所对应的用户名,以后支持一个用户名对应多台机器
        - `develop`: 该token对应的推送环境，测试或生产
        """
        if develop:
            self.redis.sadd('%s:%s' % (constants.DEBUG_TOKENS, self.app_key),
                            token)
        else:
            self.redis.srem('%s:%s' % (constants.DEBUG_TOKENS, self.app_key),
                            token)
        # 检查token是否在黑名单里，如果在，则从黑名释放出来
        if self.redis.sismember('%s:%s' % (constants.INVALID_TOKENS,
                                           self.app_key), token):
            self.redis.srem('%s:%s' % (constants.INVALID_TOKENS,
                                       self.app_key), token)
        #TODO 为用户ID和token加上关联。

    def get_target(self, token, queue=None):
        """根据Token找到需要推送的目标队列
        Arguments:
        - `self`:
        - `token`:
        """
        is_develop = self.redis.sismember('%s:%s' % (constants.DEBUG_TOKENS,
                                                     self.app_key), token)
        queue = ':%s' % queue if queue else ''
        if not queue:
            # 如果不指定队列，那么自动分配到一个队列中
            if is_develop:
                config = self.get_server_conf().get('develop', {})
            else:
                config = self.get_server_conf().get('production', {})
            threads = 1
            try:
                threads = int(config.get('worker', '1'))
            except:
                pass

            if threads > 1:
                queue = ':%s' % (hash(token) % threads)

                if queue == ':0':
                    queue = ''
        return ('%s:%s%s' % (constants.PUSH_JOB_CHANNEL_DEV, self.app_key,
                             queue),
                '%s:%s%s' % (constants.PUSH_JOB_FALLBACK_DEV, self.app_key,
                             queue)) \
                if is_develop else \
                ('%s:%s%s' % (constants.PUSH_JOB_CHANNEL, self.app_key, queue),
                '%s:%s%s' % (constants.PUSH_JOB_FALLBACK, self.app_key, queue))

    def sent_message_count(self):
        return self.redis.hget("counter", self.app_key)

    def debug_tokens(self):
        return self.redis.smembers('%s:%s' % (constants.DEBUG_TOKENS,
                                              self.app_key))

    def invalid_tokens(self):
        return self.redis.smembers('%s:%s' % (constants.INVALID_TOKENS,
                                              self.app_key))

    def push(self, token=None, alert=None, badge=None,
             sound=None, custom=None, enhance=False, queue=None):
        """向推送服务发起推送消息。
        Arguments:
        - `token`:
        - `alert`:
        - `badge`:
        - `sound`:
        - `custom`:
        - `queue`: 指定推送的队列，默认由client自己来分配
        """
        assert token is not None, 'token is reqiured'

        if enhance:
            self.epush(token, alert, badge, sound, custom)
            return
        channel, fallback_set = self.get_target(token, queue)

        d = {'token': token}
        if alert:
            d['alert'] = alert
        if badge:
            d['badge'] = badge
        if sound:
            d['sound'] = sound
        if custom:
            d['custom'] = custom
        payload = simplejson.dumps(d)
        clients = self.redis.publish(channel, payload)
        if not clients:
            self.redis.sadd(fallback_set, payload)  # TODO 加上超时

    def push_batch(self, tokens, alert, queue=None):
        """push message in batch
        """
        token = tokens[0]
        channel, fallback_set = self.get_target(token, queue)

        for tk in tokens:
            d = {'token': tk}
            if alert:
                d['alert'] = alert
            payload = simplejson.dumps(d)

            clients = self.redis.publish(channel, payload)
            if not clients:
                self.redis.sadd(fallback_set, payload)  # TODO 加上超时

    def stop(self):
        self.redis.publish("app_watcher",
                           simplejson.dumps({'op': 'stop',
                                             'app_key': self.app_key}))

    def start(self):
        self.redis.publish("app_watcher",
                           simplejson.dumps({'op': 'start',
                                             'app_key': self.app_key}))

    def valid(self):
        """valid app_key
        """
        pass

    ################# enhanced push #################

    def _get_enhance_server(self, token):
        """返回增强推送服务的信息
        """
        is_develop = self.redis.sismember('%s:%s' % (constants.DEBUG_TOKENS,
                                                     self.app_key), token)
        port = self.redis.hget('ENHANCE_PORT',
                               ':'.join((self.app_key,
                                         'dev' if is_develop else 'pro')
                                        )
                               )
        return 'localhost', int(port)

    def epush(self, token=None, alert=None, badge=None,
             sound=None, custom=None):
        """使用Ehanced协议推送，使用socket连接池，
        """
        if not self._socket:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                self._socket.connect(self._get_enhance_server(token))
            except socket.error, e:
                raise e

        try:
            d = {'token': token}
            if alert:
                d['alert'] = alert
            if badge:
                d['badge'] = badge
            if sound:
                d['sound'] = sound
            if custom:
                d['custom'] = custom
            data = simplejson.dumps(d)
            self._socket.send(data)
        except socket.error:

            time.sleep(1)
            self._socket.close()
            self._socket = None
            self.epush(token, alert, badge, sound, custom)
        except:
            return

########NEW FILE########
__FILENAME__ = constants
#encoding=utf-8

# 开发版文件的目录名
DEVELOP_DIR = 'develop'

# 正式版文件的目录名
PRODUCTION_DIR = 'production'

# 证书文件名
CER_FILE = 'cer.pem'

# 密钥文件名
KEY_FILE = 'key.pem'

# 配置文件名
CONF_FILE = 'conf.ini'


# 推送频道前缀
PUSH_JOB_CHANNEL = 'push_job'

# 推送Fallback前缀
PUSH_JOB_FALLBACK = 'push_job_fallback'

# 开发版推送频道前缀
PUSH_JOB_CHANNEL_DEV = 'push_job_dev'

# 开发版Fallback前缀
PUSH_JOB_FALLBACK_DEV = 'push_job_fallback_dev'

# 开发版的Token集合
DEBUG_TOKENS = 'debug_tokens'

# 非法Token，不对里面的Token进行推送
INVALID_TOKENS = 'invalid_tokens'

# 推送发生错误的Token及其最后一次错误时间
FAIL_TOKEN_TIME = 'fail_token_time'

# 推送发生错误的token及其错误次数
FAIL_TOKEN_COUNT = 'fail_token_count'

# token最大失败次数
TOKEN_MAX_FAIL_TIME = 5

# Web的用户名密码
USERNAME = 'apns'
PASSWORD = '12345'

########NEW FILE########
__FILENAME__ = guard
#!/usr/bin/env python
#encoding=utf-8

import time
import os
import sys

if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())

import threading
from optparse import OptionParser
from ConfigParser import ConfigParser

from notification import EnhanceNotifier
from notification import Notifier
from logger import log, create_log
from webserver import start_webserver

import simplejson
import utils
import redis


class PushGuard(object):
    """推送服务的主程序，主要职责:
    - 从指定目录读取一批app的配置文件(证书和Key)，并为之创建相应的推送和
    Feedback线程。
    - 定时轮询目录，在运行时对推送线程进行增删改管理
    """

    def __init__(self, app_dir, server_info):
        """初始化推送主进程，需要提供APP_DIR和SERVER_INFO参数
        app_dir: 存放应用信息的目录
        server_info: 用于连接redis的信息
        """
        assert app_dir, '"app_dir" argument is reqiured!'
        self.app_dir = app_dir
        self.server_info = server_info

        self.rds = redis.Redis(**self.server_info)

        #self.threads = {}
        self.notifiers = {}

    def run(self):
        """读取一个目录，遍历下面的app文件夹，每个app启动一到两条线程对此提供服
        务,一条用来发推送，一条用来收feedback
        """
        self.rds.set('ENHANCE_THREAD', 0)
        apps = utils.get_apps(self.app_dir)
        self.app_info = {}

        # 文件夹下面会有production,develop两个子目录，分别放不同的Key及Cert

        for app in apps:
            if app.startswith('.'):
                continue
            log.debug('getting ready for app : %s' % app)
            app_info = utils.get_app_info(self.app_dir, app)
            self.app_info[app] = app_info

            self.start_worker(app)

        start_webserver(self)
        self.watch_app()
        log.debug('just wait here,there are %d threads ' % len(self.notifiers))

        while True:
            time.sleep(10)

    def start_worker(self, app):
        log.debug('start an app : %s' % app)
        app_info = self.app_info[app]

        if 'production' in app_info:
            self.start_worker_thread(app, False,
                                     app_info['production']['cer_file'],
                                     app_info['production']['key_file'],
                                     app_info['production']['config'])
        if 'develop' in app_info:
            self.start_worker_thread(app, True,
                                     app_info['develop']['cer_file'],
                                     app_info['develop']['key_file'],
                                     app_info['develop']['config'])

    def start_worker_thread(self, app, dev, cer_file, key_file, conf):
        kwargs = {
            'develop': dev,
            'app_key': app,
            'cer_file': cer_file,
            'key_file': key_file,
            'server_info': self.server_info
        }
        # 检查配置里关于推送线程数的配置，启动相应数量的推送线程
        thread_cnt = 1
        log.debug('startting worker with config : %s' % conf)
        if conf:
            conf_prefix = 'config_dev:' if dev else 'config:'
            self.rds.hmset(conf_prefix + app, conf)
            try:
                thread_cnt = int(conf.get('worker', '1'))
            except:
                log.warn('invalid config of workers, just start one.')
        workers = []
        for cnt in range(thread_cnt):
            if cnt == 0:
                params = kwargs
                worker = threading.Thread(target=self.push, kwargs=params)
            else:
                params = kwargs.copy()
                params.update({'channel': cnt})
            worker = threading.Thread(target=self.push, kwargs=params)
            workers.append(worker)

        feedback_job = threading.Thread(target=self.feedback, kwargs=kwargs)
        enhance_job = threading.Thread(target=self.enhance, kwargs=kwargs)

        feedback_job.setDaemon(True)
        enhance_job.setDaemon(True)
        for w in workers:
            w.setDaemon(True)
            w.start()

        feedback_job.start()
        enhance_job.start()

    def stop_worker_thread(self, app_key):

        if (app_key + ":dev:push") in self.notifiers:
            self.notifiers[app_key + ":dev:push"].alive = False
            self.rds.publish('push_job_dev:%s' % app_key, 'kill')
            del self.notifiers[app_key + ":dev:push"]

        if (app_key + ":dev:feedback") in self.notifiers:
            self.notifiers[app_key + ":dev:feedback"].alive = False
            del self.notifiers[app_key + ":dev:feedback"]

        if (app_key + ":dev:enhance") in self.notifiers:
            self.notifiers[app_key + ":dev:enhance"].alive = False
            del self.notifiers[app_key + ":dev:enhance"]

        # 要看看有多少条推送线程，一条条退出
        if (app_key + ":pro:push") in self.notifiers:
            self.notifiers[app_key + ":pro:push"].alive = False
            self.rds.publish('push_job:%s' % app_key, 'kill')
            del self.notifiers[app_key + ":pro:push"]

        if (app_key + ":pro:feedback") in self.notifiers:
            self.notifiers[app_key + ":pro:feedback"].alive = False
            del self.notifiers[app_key + ":pro:feedback"]

        if (app_key + ":pro:enhance") in self.notifiers:
            self.notifiers[app_key + ":pro:enhance"].alive = False
            del self.notifiers[app_key + ":pro:enhance"]

    def watch_app(self):
        self.watcher = threading.Thread(target=self.app_watcher)
        self.watcher.setDaemon(True)
        self.watcher.start()

    def app_watcher(self):
        try:
            ps = self.rds.pubsub()
            ps.subscribe("app_watcher")
            channel = ps.listen()
            for message in channel:
                if message['type'] != 'message':
                    continue
                log.debug('got message from app_watcher %s' % message)
                msg = simplejson.loads(message["data"])
                if(msg["op"] == "stop"):
                    self.stop_worker_thread(msg["app_key"])
                elif(msg["op"] == "start"):
                    self.start_worker(msg["app_key"])
        except:
            log.error('app_watcher fail,retry.', exc_info=True)
            time.sleep(10)
            self.app_watcher()

    def push(self, develop, app_key, cer_file, key_file, server_info,
             channel=None):
        notifier = Notifier('push', develop, app_key,
                            cer_file, key_file, server_info, channel)

        channel = ':%s' % channel if channel else ''
        if develop:
            self.notifiers[app_key + ":dev:push" + channel] = notifier
        else:
            self.notifiers[app_key + ":pro:push" + channel] = notifier
        notifier.run()

    def feedback(self, develop, app_key, cer_file, key_file, server_info):
        notifier = Notifier('feedback', develop, app_key,
                            cer_file, key_file, server_info)
        if develop:
            self.notifiers[app_key + ":dev:feedback"] = notifier
        else:
            self.notifiers[app_key + ":pro:feedback"] = notifier
        notifier.run()

    def enhance(self, develop, app_key, cer_file, key_file, server_info):
        notifier = EnhanceNotifier('enhance', develop, app_key,
                                   cer_file, key_file, server_info)
        if develop:
            self.notifiers[app_key + ":dev:enhance"] = notifier
        else:
            self.notifiers[app_key + ":pro:enhance"] = notifier
        notifier.run()


def execute():
    parser = OptionParser(usage="%prog config [options]")
    parser.add_option("-f", "--folder", dest="app_dir",
                      help="folder where the certs and keys to stay")
    parser.add_option("-s", "--host", dest="host", default="127.0.0.1",
                      help="Redis host name or address")
    parser.add_option("-p", "--port", dest="port", default=6379, type="int",
                      help="Redis port")
    parser.add_option("-d", "--db", dest="db", default=0, type="int",
                      help="Redis database")
    parser.add_option("-a", "--password", dest="password", default="",
                      help="Redis password")
    parser.add_option("-l", "--log", dest="log",
                      help="log file")
    (options, args) = parser.parse_args(sys.argv)
    if options.log:
        create_log(options.log)
    else:
        create_log()

    if len(args) > 1:
        config = ConfigParser()
        config.read(args[1])
        guard = PushGuard(app_dir=config.get('app', 'app_dir'),
                          server_info={'host': config.get('redis', 'host'),
                                       'port': int(config.get('redis',
                                                              'port')),
                                       'db': int(config.get('redis', 'db')),
                                       'password': config.get('redis',
                                                              'password')})
    else:
        guard = PushGuard(app_dir=options.app_dir,
                          server_info={'host': options.host,
                                       'port': options.port,
                                       'db': options.db,
                                       'password': options.password})
    guard.run()

if __name__ == '__main__':
    execute()

########NEW FILE########
__FILENAME__ = logger
#encoding=utf-8

import logging
import os.path
import sys

"""
日志使用方法：
from logger import log

log.info('your info')
log.debug('heyhey')

"""

LOG_LEVEL = logging.DEBUG # 日志的输出级别，有 NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT = '[%(asctime)s] %(funcName)s(%(filename)s:%(lineno)s) [%(levelname)s]:%(message)s' # 日志的输出格式

log = logging.getLogger()
log.setLevel(LOG_LEVEL)

def create_log(log_file='/var/log/apnsagent.log'):
    global log
    
    formatter = logging.Formatter(LOG_FORMAT)
    filehandler = logging.FileHandler(log_file)
    filehandler.setFormatter(formatter)
    log.addHandler(filehandler)

create_log = create_log

def log_ex(msg=None):
    if msg:
        log.error(msg)
    excinfo = sys.exc_info()
    log.error(excinfo[0])
    log.error(excinfo[1])
    return excinfo

########NEW FILE########
__FILENAME__ = notification
#encoding=utf-8
import sys
import re
import traceback

import simplejson
from apns import APNs, Payload
from apns import PayloadTooLargeError
from ssl import SSLError
import socket
import select
import redis
import time
import uuid
from datetime import datetime

from apnsagent import constants
from apnsagent.logger import log
from client import PushClient


class SafePayload(Payload):
    """为了手动检查推送信息的长度，自制一个安全的Payload
    """
    def __init__(self, alert=None, badge=None, sound=None, custom={}):
        self.alert = alert
        self.badge = badge
        self.sound = sound
        self.custom = custom

    def as_payload(self):
        try:
            return Payload(self.alert, self.badge, self.sound, self.custom)
        except:
            log.error('payload still Tool long')


class Notifier(object):
    def __init__(self, job='push', develop=False, app_key=None,
                 cer_file=None, key_file=None, server_info=None, channel=None):
        """
        job = push | feedback
        develop,是否使用sandbox服务器，调试时设为True
        app_key,使用推送服务的应用唯一标识，格式建议为com.company.appname
        cert_file,该应用的推送证书，PEM格式
        key_file,该应用的密钥，PEM格式，要求去掉passphase
        """
        self.job = job
        self.develop = develop
        self.app_key = app_key
        self.cert_file = cer_file
        self.key_file = key_file
        self.channel = channel

        self.alive = True
        self.retry_time_max = 99  # 如果redis连接断开，重试99次
        self.retry_time = 0

        self.last_sent_time = datetime.now()

        self.apns = APNs(use_sandbox=self.develop,
                         cert_file=self.cert_file, key_file=self.key_file)

        self.server_info = server_info or {
            'host': '127.0.0.1',
            'post': 6379,
            'db': 0,
            'password': ''
            }

        self.client = PushClient(self.app_key, self.server_info)

    def run(self):
        """
        - 监听redis队列，发送push消息
        - 从apns获取feedback service，处理无效token
        """
        log.debug('starting a thread')

        self.rds = redis.Redis(**self.server_info)
        if self.job == 'push':
            self.push()
        elif self.job == 'feedback':
            self.feedback()

        log.debug('leaving a thread')

    def log_error(self, message='message push fail'):
        self.rds.hincrby("fail_counter", self.app_key)
        log.error(message)
        type, value, tb = sys.exc_info()
        error_message = traceback.format_exception(type, value, tb)
        log.debug(type)
        log.error(error_message)

    def send_message(self, message):
        """
        发送消息，如果发生异常失败，重新连接再试一次，再失败则丢失
        """
        log.debug('get a message from channel')
        log.debug(message)
        try:
            if message['type'] != 'message':
                return
            self._send_message(message)
        except SSLError:
            self.log_error()
            self.resend(message)
        except socket.error:
            self.log_error()
            self.resend(message)
        except:
            self.log_error()

    def _send_message(self, message):
        real_message = simplejson.loads(message['data'])
        badge = real_message.get('badge', None)
        sound = real_message.get('sound', None)
        alert = real_message.get('alert', None)
        custom = real_message.get('custom', {})

        if self.rds.sismember('%s:%s' % (constants.INVALID_TOKENS,
                                             self.app_key),
                                  real_message['token']):
            # the token is invalid,do nothing
            return
        try:
            payload = Payload(sound=sound, badge=badge, alert=alert,
                              custom=custom)

        except PayloadTooLargeError:
            # 在内存保留100条缩短后消息，避免批量发送时，每条都要缩短的损耗
            if not alert:
                log.error('push meta data too long to trim, discard')
                payload = None
            if isinstance(alert, dict):
                log.error('payload too long to trim, discard')
                payload = None

            log.debug('try to trime large alert')
            payload = SafePayload(sound=sound, badge=badge, alert=alert,
                                  custom=custom)
            l_payload = len(payload.json())
            l_alert = len(alert.encode('unicode_escape'))
            l_allow = 256 - (l_payload - l_alert) - 3  # 允许提示长度

            ec_alert = alert.encode('unicode_escape')
            t_alert = re.sub(r'([^\\])\\(u|$)[0-9a-f]{0,3}$', r'\1',
                             ec_alert[:l_allow])
            alert = t_alert.decode('unicode_escape') + u'...'

            log.debug('payload is : %s' % alert)

            payload.alert = alert
            log.debug('how long dest it after trim %d' % len(payload.json()))
            payload = payload.as_payload()

        if not payload:
            return

        log.debug('will sent a meesage to token %s', real_message['token'])
        now = datetime.now()
        if (now - self.last_sent_time).seconds > 300:
            log.debug('idle for a long time , reconnect now.')
            self.reconnect()
        self.apns.gateway_server.send_notification(real_message['token'],
                                                   payload)
        self.last_sent_time = datetime.now()
        self.rds.hincrby("counter", self.app_key)

    def resend(self, message):
        log.debug('resending')
        self.reconnect()
        self._send_message(message)

    def reconnect(self):
        self.apns = APNs(use_sandbox=self.develop,
                         cert_file=self.cert_file, key_file=self.key_file)

    def push(self):
        """
        监听消息队列，获取推送请求，推送消息到客户端
        """
        #先处理fallback里面留下来的消息，理论上那里的数据不会很多
        fallback = constants.PUSH_JOB_FALLBACK_DEV \
                  if self.develop else \
                  constants.PUSH_JOB_FALLBACK

        channel = constants.PUSH_JOB_CHANNEL_DEV \
                  if self.develop else \
                  constants.PUSH_JOB_CHANNEL

        if self.channel:
            channel = '%s:%s:%s' % (channel, self.app_key, self.channel)
            fallback = '%s:%s:%s' % (fallback, self.app_key, self.channel)
        else:
            channel = '%s:%s' % (channel, self.app_key)
            fallback = '%s:%s' % (fallback, self.app_key)

        self.push_fallback(fallback)
        self.consume_message(channel)

    def push_fallback(self, fallback):
        log.debug('handle fallback messages for channel %s' % fallback)
        old_msg = self.rds.spop(fallback)
        while(old_msg):
            log.debug('handle message:%s' % old_msg)
            try:
                simplejson.loads(old_msg)
                self.send_message({'type': 'message', 'data': old_msg})
            except:
                log.debug('message is not a json object')
            finally:
                old_msg = self.rds.spop(fallback)

    def consume_message(self, channel):
        # 再订阅消息队列
        try:
            pubsub = self.rds.pubsub()
            pubsub.subscribe(channel)
            log.debug('subscribe push channel %s successfully' % channel)
            redis_channel = pubsub.listen()

            for message in redis_channel:
                self.retry_time = 0
                if 'kill' == message['data']:
                    break
                else:
                    self.send_message(message)
        except:
            # 连接redis不上, 睡眠几秒钟重试连接
            if self.retry_time <= self.retry_time_max:
                time.sleep(10)
                self.retry_time = self.retry_time + 1
                log.debug(u'redis cannot connect, retry %d' % self.retry_time)
                self.consume_message(channel)
            else:
                # 这时，需要Email通知管理员了
                log.error(u'retry time up, redis gone! help!')

        log.debug('i am leaving push')

    def handle_bad_token(self, token, fail_time):
        log.debug('push message fail to send to %s.' % token)
        # 设置token的失败次数及最后更新时间
        count = self.rds.hincrby('%s:%s' % (constants.FAIL_TOKEN_COUNT,
                                  self.app_key), token, 1)
        log.debug('fail count: %s' % count)
        if count >= constants.TOKEN_MAX_FAIL_TIME:
            # 如果token连续失败的次数达到了阀值，放进invalid_tokens
            log.debug('fail count access limit, die hard!')
            self.rds.hdel('%s:%s' % (constants.FAIL_TOKEN_COUNT,
                                     self.app_key), token)
            self.rds.hdel('%s:%s' % (constants.FAIL_TOKEN_TIME,
                                     self.app_key), token)
            self.rds.sadd('%s:%s' % (constants.INVALID_TOKENS,
                                     self.app_key), token)
        else:
            self.rds.hset('%s:%s' % (constants.FAIL_TOKEN_TIME,
                                     self.app_key), token, fail_time)

    def feedback(self):
        """
        从apns获取feedback,处理无效token
        """
        while(self.alive):
            try:
                self.reconnect()
                for (token, fail_time) in self.apns.feedback_server.items():
                    self.handle_bad_token(token, fail_time)
            except:
                self.log_error('get feedback fail')
            time.sleep(60)

        log.debug('i am leaving feedback')


class EnhanceNotifier(Notifier):

    def run(self):
        self.rds = redis.Redis(**self.server_info)
        self.enhance_push()

    def handle_error(self, identifier, errorcode):
        """处理推送错误
        """
        log.debug('apns sent back an error: %s %d', identifier, errorcode)
        if errorcode == 8:
            # add token to invalid token set
            sent = self.rds.smembers('ENHANCE_SENT:%s' % self.app_key)
            for s in sent:
                data = simplejson.loads(s)
                if data['id'] != identifier:
                    continue
                token = data['token']
                self.rds.sadd('%s:%s' % (constants.INVALID_TOKENS,
                                         self.app_key),
                              token)
        else:
            log.debug('not invalid token, ignore error')

    def send_enhance_message(self, buff):
        identifier = uuid.uuid4().hex[:4]
        #expiry = int(time.time() + 5)
        expiry = 0

        try:
            data = simplejson.loads(buff)
            token = data['token']
            badge = data.get('badge', None)
            sound = data.get('sound', None)
            alert = data.get('alert', None)
            custom = data.get('custom', {})
            payload = SafePayload(sound=sound, badge=badge, alert=alert,
                                  custom=custom)
        except:
            return

        # 把发送的内容记录下来,记到redis，还得有一个定时器去清除过期的记录。
        data = simplejson.dumps({'id': identifier,
                                 'token': token,
                                 'expiry': expiry})
        self.rds.sadd('ENHANCE_SENT:%s' % self.app_key, data)
        self.apns.gateway_server.send_enhance_notification(token, payload,
                                                           identifier, expiry)

    def _reconnect_apns(self, clean=False):
        if clean:
            self.apns.gateway_server._disconnect()
            self.apns._gateway_connection = None
            if self.cli_sock in self.rlist:
                self.rlist.remove(self.cli_sock)
        self.apns.gateway_server._connect()
        self.cli_sock = self.apns.gateway_server._ssl
        self.rlist.append(self.cli_sock)

    def enhance_push(self):
        """
        使用增强版协议推送消息
        """
        self.host = 'localhost'
        index = self.rds.incr('ENHANCE_THREAD', 1)
        self.port = 9527 + index - 1
        self.rds.hset('ENHANCE_PORT',
                      ':'.join((self.app_key,
                                'dev' if self.develop else 'pro')),
                      self.port)

        srv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv_sock.bind((self.host, self.port))
        srv_sock.listen(5)
        srv_sock.setblocking(0)

        self.apns.gateway_server._connect()
        self.cli_sock = self.apns.gateway_server._ssl

        log.debug('the apns client socket is : %s' % self.cli_sock)

        self.rlist = [srv_sock, self.cli_sock]
        self.wlist = []
        self.xlist = []

        while self.alive:
            rl, wl, xl = select.select(self.rlist,
                                       self.wlist,
                                       self.xlist, 10)

            if xl:
                for x in xl:
                    log.error('error occur %s' % x)

            if rl:
                log.debug('data to read %s' % rl)
                log.debug('rlist: %s' % self.rlist)
                for r in rl:
                    if r == srv_sock:
                        log.debug('connection from client!')
                        try:
                            new_sock, addr = srv_sock.accept()
                            self.rlist.append(new_sock)
                            continue
                        except socket.error:
                            pass
                    elif r == self.cli_sock:
                        log.debug('message from apns, some error eccour!')
                        error = self.apns.gateway_server.get_error()
                        if not error:
                            log.debug('apns drop the connection, reconnect!')
                            self._reconnect_apns(True)
                            continue
                        else:
                            self.handle_error(error[0], error[1])
                    else:
                        sk = self.apns.gateway_server._ssl
                        log.debug('message from client,will sent to %s' % sk)
                        buf = ''
                        try:
                            buf = r.recv(4096)
                        except socket.error:
                            self.rlist.remove(r)
                            r.close()
                            continue

                        if not buf:
                            # client close the socket.
                            self.rlist.remove(r)
                            r.close()
                            continue

                        try:
                            # 如果还没有连接，或闲置时间过长
                            now = datetime.now()
                            if not self.apns._gateway_connection:
                                log.debug('无连接,重连')
                                self._reconnect_apns(False)
                            elif (now - self.last_sent_time).seconds > 300:
                                log.debug('闲置时间过长，重连')
                                self._reconnect_apns(True)
                            log.debug('推送消息%s' % buf)
                            self.send_enhance_message(buf)
                            self.last_sent_time = now
                        except socket.error:
                            self.log_error('send notification fail, reconnect')
                            self._reconnect_apns(True)
                        except:
                            self.log_error('send notification fail with error')

########NEW FILE########
__FILENAME__ = utils
#encoding=utf-8

from os import listdir
from os.path import isdir
from os.path import exists
from os.path import join

from constants import DEVELOP_DIR
from constants import PRODUCTION_DIR
from constants import CER_FILE
from constants import KEY_FILE
from constants import CONF_FILE
from apnsagent.logger import log
from ConfigParser import ConfigParser


def get_app_info(app_dir, app):
    app_info = {'app_key': app}

    dev_dir = join(app_dir, app, DEVELOP_DIR)
    if isdir(dev_dir) and exists(join(dev_dir, CER_FILE)) \
           and exists(join(dev_dir, KEY_FILE)):
        # 读配置文件
        conf = join(dev_dir, CONF_FILE)
        conf_dict = {}
        if exists(conf):
            config = ConfigParser()
            config.read(conf)
            conf_dict = dict(config.items('apnsagent'))
        app_info['develop'] = {'cer_file': join(dev_dir, CER_FILE),
                               'key_file': join(dev_dir, KEY_FILE),
                               'config': conf_dict}

    pro_dir = join(app_dir, app, PRODUCTION_DIR)
    if isdir(pro_dir) and exists(join(pro_dir, CER_FILE)) \
           and exists(join(pro_dir, KEY_FILE)):
        conf = join(pro_dir, CONF_FILE)
        log.debug('config file: %s' % conf)
        conf_dict = {}
        if exists(conf):
            log.debug('load config file')
            config = ConfigParser()
            config.read(conf)
            conf_dict = dict(config.items('apnsagent'))
            log.debug('config content %s' % conf_dict)
        app_info['production'] = {'cer_file': join(pro_dir, CER_FILE),
                                'key_file': join(pro_dir, KEY_FILE),
                                'config': conf_dict}
    return app_info


def get_apps(app_dir):
    return [d for d in listdir(app_dir) if isdir(join(app_dir, d))]

########NEW FILE########
__FILENAME__ = webserver
import threading
import time

from apnsagent import constants
from apnsagent.constants import *

from redis import *
from flask import Flask, request, session, redirect, url_for, \
     render_template
from apnsagent.guard import *

app = Flask('apnsagent.webserver')
server = None
rds = None
elapsed = time.time()

app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'


@app.route("/")
def hello():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    """
    if request.method == 'POST' \
       and request.form['username'] == USERNAME \
       and request.form['password'] == PASSWORD:
        session['username'] = USERNAME
        session['password'] = PASSWORD
        return redirect(url_for('mainlist'))
    else:
        return render_template('login.html')


@app.route("/list")
def mainlist():
    if session['username'] != USERNAME or session['password'] != PASSWORD:
        return redirect(url_for('login'))

    global server
    global rds

    seq = []
    cnt = 0
    for app in server.app_info:
        cnt += 1
        seq.append({'id': cnt,
                    'appname': app,
                    'total_count': rds.hget("counter", app) or 0,
                    'fail_count': rds.hget("fail_counter", app) or 0,
                    'develop': ('develop' in server.app_info[app]),
                    'production': ('production' in server.app_info[app]), })

    return render_template('notification_service.html',
                           seq=seq,
                           threads=len(server.app_info),
                           elapsed=('%.1d' % ((time.time() - elapsed) / 60)))


@app.route("/detail/<who>")
def detail(who):

    if session['username'] != USERNAME or session['password'] != PASSWORD:
        return redirect(url_for('login'))

    seq = []
    cnt = 0
    global rds
    tks = rds.smembers('%s:%s' % (constants.INVALID_TOKENS, who))
    for tk in tks:
        cnt += 1
        seq.append({'id': cnt, 'token': tk})

    return render_template('invalid_tokens.html', seq=seq,
                           appname=who, tokens_count=len(tks))


@app.route("/switch_on/<who>")
def switch_on(who):
    global server
    server.start_worker(who)
    return 'done'


@app.route("/switch_off/<who>")
def switch_off(who):
    global server
    server.stop_worker_thread(who)
    return 'done'


def start_server():
    app.run(port=5555, host='0.0.0.0')


def start_webserver(serv):
    print 'srarting webserver at the port 5555'
    global server
    global rds
    server = serv
    rds = server.rds
    web_daemon = threading.Thread(target=start_server)
    web_daemon.setDaemon(True)
    web_daemon.start()


if __name__ == '__main__':
    start_server()

########NEW FILE########
__FILENAME__ = web_daemon
import redis
from flask import Flask
app = Flask(__name__)

from guard import *

rds = redis.Redis()


@app.route("/")
def hello():
    return "Hello World!"


@app.route("/apps")
def echo_apps():
    return str(rds.hkeys("counter"))


@app.route("/msg_count/<who>")
def echo_msg_count(who):
    return str(rds.hget("counter", who))


@app.route("/fail_msg_count/<who>")
def fail_echo_msg_count(who):
    if(who in msg_counter):
        return  who + ":" + str(fail_msg_counter[who])
    else:
        return "no such an app"


@app.route("/bad_tokens/<who>")
def echo_bad_tokens(who):
    return str(rds.smembers('%s:%s' % (constants.INVALID_TOKENS, who)))


@app.route("/x")
def echo():
    global server
    return str(len(server.notifiers))


def start_server():
    app.run()


web_daemon = "start web daemon"
server = None


def start_web_daemon(serv):
    global web_daemon
    global server
    server = serv
    print web_daemon
    web_daemon = threading.Thread(target=start_server)
    web_daemon.setDaemon(True)
    web_daemon.start()

########NEW FILE########
