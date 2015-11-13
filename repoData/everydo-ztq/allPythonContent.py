__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.

$Id$
"""

import os, shutil, sys, tempfile, urllib2

tmpeggs = tempfile.mkdtemp()

is_jython = sys.platform.startswith('java')

try:
    import pkg_resources
except ImportError:
    ez = {}
    exec urllib2.urlopen('http://peak.telecommunity.com/dist/ez_setup.py'
                         ).read() in ez
    ez['use_setuptools'](to_dir=tmpeggs, download_delay=0)

    import pkg_resources

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c # work around spawn lamosity on windows
        else:
            return c
else:
    def quote (c):
        return c

cmd = 'from setuptools.command.easy_install import main; main()'
ws  = pkg_resources.working_set

if is_jython:
    import subprocess
    
    assert subprocess.Popen([sys.executable] + ['-c', quote(cmd), '-mqNxd', 
           quote(tmpeggs), 'zc.buildout'], 
           env=dict(os.environ,
               PYTHONPATH=
               ws.find(pkg_resources.Requirement.parse('setuptools')).location
               ),
           ).wait() == 0

else:
    assert os.spawnle(
        os.P_WAIT, sys.executable, quote (sys.executable),
        '-c', quote (cmd), '-mqNxd', quote (tmpeggs), 'zc.buildout',
        dict(os.environ,
            PYTHONPATH=
            ws.find(pkg_resources.Requirement.parse('setuptools')).location
            ),
        ) == 0

ws.add_entry(tmpeggs)
ws.require('zc.buildout')
import zc.buildout.buildout
zc.buildout.buildout.main(sys.argv[1:] + ['bootstrap'])
shutil.rmtree(tmpeggs)

########NEW FILE########
__FILENAME__ = tests
#coding:utf-8

from paste.httpserver import serve
import sys,os
sys.path.insert(0, os.path.abspath('../'))
sys.path.append('E:\\workspace\\Everydo_DBank\\src\\fts\\ztq_core')

if __name__ == '__main__':
    # For Debug
    from ztq_console import main
    app = main('test')
    serve(app, host='0.0.0.0', port=9013)


########NEW FILE########
__FILENAME__ = dispatch
#coding:utf-8
"""
功能描述:调度算法模块, 根据服务器和队列的权重进行工作调度.
"""

import time
import ztq_core 

def update_queue_threads(worker_name, queue_name, action):
    """调整特定队列线程数量，可以增加或者减少
    """
    worker_config = ztq_core.get_worker_config()
    queue_config = worker_config[queue_name]
    if queue_config.get(queue_name, None):
        _config = queue_config[queue_name]

        # 生成新的配置信息
        if action == 'queue_down' : 
            _config.pop()
        elif action == 'queue_up' : 
            _config.append(_config[0])
        queue_config[queue_name] = _config

        worker_config[worker_name]= queue_config
        send_sync_command(worker_name)

def send_sync_command(worker_name):
    """向转换器下达同步指令
    """
    sync_command= {'command':'updateworker','timestamp':int(time.time())}
    cmd_queue = ztq_core.get_command_queue(worker_name)
    # 避免同时发送多条同步命令
    if cmd_queue:
        for command in cmd_queue:
            if command.get('command', None) == sync_command['command']:            
                return 0
    cmd_queue.push(sync_command)
                
                

########NEW FILE########
__FILENAME__ = get_fts_data
#coding:utf-8
'''
功能描述: 此模块用于数据整合, 被views模块调用.

Created on 2011-4-28

@author: Zay
'''
import time, pprint, datetime
import ztq_core
import urllib
try:
    import json
except: import simplejson as json

def get_sys_log(sindex=None, eindex=None):
    log_queue = ztq_core.get_system_log_queue()
    for log in log_queue[sindex:eindex]:
        log['_alias'] = log.get('alias', '')
        log['_host'] = log.get('host', '')
        log['_type'] = log.get('type', '')
        log['_timestamp'] = datetime.datetime.fromtimestamp(log.get('timestamp', 0))
        yield log

def get_worker_log(sindex=None, eindex=None):
    worker_log_queue = ztq_core.get_work_log_queue()
    for worker_log in worker_log_queue[sindex:eindex]:
        # 检查worker是否还存在
        log = {}
        log['_server'] = worker_log['runtime']['worker']
        log['_created'] = datetime.datetime.fromtimestamp(worker_log['runtime'].get('create', 0))
        log['_start'] = datetime.datetime.fromtimestamp(worker_log['runtime'].get('start', 0))
        log['_end'] = datetime.datetime.fromtimestamp(worker_log['runtime'].get('end', 0))
        log['_status'] = worker_log['runtime']['return']
        log['_func'] = worker_log['func']
        log['_comment'] = worker_log['process'].get('comment','')
        log['_file'] = worker_log['kw'].get('comment', worker_log['kw'].get('path', ''))
        log['_reason'] = ''.join(worker_log['runtime']['reason'])
        log['_detail'] = pprint.pformat(worker_log)
        yield log
        
def get_taskqueues_list():
    # 队列情况列表
    queues_list = ztq_core.get_queue_config()

    # 排序
    sort_queue_name = {}
    for queue_name, queue_config in queues_list.items():
        sort_queue_name[queue_name] = len(ztq_core.get_error_queue(queue_name))
    
    for queue_name in sorted(sort_queue_name, 
                            key=lambda x: sort_queue_name[x], 
                            reverse=True):
        task_queue = {}
        task_queue['name'] = queue_name
        #task_queue['tags'] = queue_config.get('tags',())
        queue = ztq_core.get_task_queue(queue_name)
        # 任务数/错误数
        task_queue['length'] = len(queue)
        task_queue['error_length'] = sort_queue_name[queue_name]

        #任务首个时间
        task_queue['error_end'] = task_queue['first'] = ''
        first_job = queue[0]
        first_job= ztq_core.get_task_hash(queue_name).get(first_job)
        if first_job:
            task_queue['first'] = datetime.datetime.fromtimestamp(first_job['runtime'].get('create', 0))
        
        #错误最末一个的时间
        error_first_job = ztq_core.get_error_queue(queue_name)[0]
        error_first_job = ztq_core.get_error_hash(queue_name).get(error_first_job)
        if error_first_job:
            task_queue['error_end'] = datetime.datetime.fromtimestamp(error_first_job['runtime'].get('create', 0))

        # 获取worker工作线程配置
        workers_config = ztq_core.get_worker_config()
        task_queue['from_right'] = True
        for worker_name,worker_config in workers_config.items():
            task_queue['workers'] = []
            for config in worker_config.get(queue_name,[]):
                task_queue['workers'].append([worker_name+':', config['interval']])
                if 'from_right' in config:
                    task_queue['from_right'] = config['from_right']
        task_queue['buffer_length'] = len(ztq_core.get_buffer_queue(queue_name))
        yield task_queue

def get_queues_jobs(queue_name):
    queue = ztq_core.get_task_queue(queue_name)
    for task_job_hash in queue.reverse():
        task_job = ztq_core.get_task_hash(queue_name).get(task_job_hash)
        tmp_job={}
        tmp_job['_queue_name'] = queue_name
        tmp_job['_id'] = urllib.quote(task_job_hash)
        #tmp_job['_ori'] = task_job
        tmp_job['_detail'] = pprint.pformat(task_job)
        tmp_job['_created'] = datetime.datetime.fromtimestamp(task_job['runtime'].get('create', 0))
        yield tmp_job

def get_all_error_jobs(sindex=0, eindex=-1):
    queues_list = ztq_core.get_queue_config()
    index = 0
    count = eindex - sindex
    for queue_name in queues_list.keys():
        error_len = len(ztq_core.get_error_queue(queue_name))
        if error_len == 0: continue
        # 确定从哪里开始
        index += error_len
        if index < sindex: continue
        
        start_index = 0 if sindex-(index-error_len) < 0 else sindex-(index-error_len)
        yield get_error_queue_jobs(queue_name, start_index, count+start_index)

        # 是否应该结束
        count -= error_len - start_index
        if count < 0: break

def get_error_queue(error_queue_name, sindex=0, eindex=-1):
    """ 模板问题的原因 """
    yield get_error_queue_jobs(error_queue_name, sindex, eindex)

def get_error_queue_jobs(error_queue_name, sindex=0, eindex=-1):
    error_queue = ztq_core.get_error_queue(error_queue_name)
    workers_state = ztq_core.get_worker_state()
    for hash_key in error_queue[sindex:eindex]:
        error_job = ztq_core.get_error_hash(error_queue_name)[hash_key]
        tmp_job={}
        tmp_job['json'] = json.dumps(error_job)
        tmp_job['_queue_name'] = error_queue_name
        worker_name = error_job['runtime']['worker']
        # 检查worker是否存在,存在则取得服务器ip
        if worker_name in workers_state:
            tmp_job['_server'] = workers_state[worker_name]['ip']
        else: tmp_job['_server'] = worker_name
        tmp_job['_created'] = datetime.datetime.fromtimestamp(error_job['runtime'].get('create',0))
        tmp_job['_start'] = datetime.datetime.fromtimestamp(error_job['runtime'].get('start',0))
        tmp_job['_end'] = datetime.datetime.fromtimestamp(error_job['runtime'].get('end',0))
        tmp_job['_reason'] = ''.join(error_job['runtime']['reason'])
        tmp_job['_file'] = error_job['kw'].get('comment', error_job['kw'].get('path', ''))
        tmp_job['_error_mime'] = error_job['process'].get('to_mime','')
        tmp_job['_detail'] = pprint.pformat(error_job)
        tmp_job['hash_id'] = urllib.quote(hash_key)
        yield tmp_job

def get_worker_list():
    workers_dict = ztq_core.get_worker_state().items()
    for worker_name, worker_status in workers_dict:
        worker_status['_worker_name'] = worker_name
        worker_status['_started'] = \
            datetime.datetime.fromtimestamp(worker_status['started'])
        worker_status['_timestamp'] = \
            datetime.datetime.fromtimestamp(worker_status['timestamp'])

        # 检查worker是否在工作
        cmd_queue = ztq_core.get_command_queue(worker_name)

        # 如果指令队列不为空的话,意味着worker没工作,属于下线状态
        if cmd_queue: 
            worker_status['_active'] = u'shutdown'
        else: 
            worker_status['_active'] = u'work'

        # 获取worker开了多少个线程
        worker_job = ztq_core.get_job_state(worker_name)
        worker_status['_threads'] = []
        for thread_name,thread_status in worker_job.items():
            thread_status['_detail'] = pprint.pformat(thread_status)
            thread_status['_name'] = thread_name
            thread_status['_comment'] = thread_status['kw'].get('comment',thread_status['process'].get('comment', ''))
            thread_status['_pid'] = thread_status['process'].get('pid', -1)
            ident = unicode(thread_status['process'].get('ident', -1))
            if ident in worker_status['traceback']:
                thread_status['_thread_detail'] = pprint.pformat(worker_status['traceback'][ident])
            # 任务进行了多少时间
            used_time = int(time.time())-thread_status['process']['start']
            if used_time > 3600:
                used_time = u'%.2f小时' % (used_time / 3600.0)
            elif used_time > 60:
                used_time = u'%.2f分钟' % (used_time / 60.0)
            thread_status['_take_time'] = used_time

            worker_status['_threads'].append(thread_status)

        yield worker_status
        
def send_command(worker_name, command_stm):
    """向worker发报告状态指令
    """
    send_command= {
    'command':command_stm,
    'timestamp':int(time.time())
    }
    cmd_queue = ztq_core.get_command_queue(worker_name)
    
    # 避免同时发送多条同步命令
    if cmd_queue:
        for command in cmd_queue:
            if command.get('command', None) == send_command['command']:            
                return 0
    cmd_queue.push(send_command)

########NEW FILE########
__FILENAME__ = models
#coding:utf-8
from pyramid.security import Allow, Everyone
    

class RootFactory(object):
    __acl__ = [ (Allow, Everyone, 'view'),
                (Allow, 'group:editors', 'edit') ]
    def __init__(self, request):
        pass

########NEW FILE########
__FILENAME__ = password
#coding:utf-8
from ConfigParser import ConfigParser, RawConfigParser
import sys
import os

def get_password():
    cf = ConfigParser()
    cf.read(sys.argv[2])
    password_path = cf.get('password_path', 'password_path')
    cf.read(password_path)
    return cf.get('password', 'password')

def modify_password(new_password):
    cf = ConfigParser()
    cf.read(sys.argv[2])
    password_path = cf.get('password_path', 'password_path')
    if os.path.exists(password_path):
        passwd_txt = ConfigParser()
        passwd_txt.read(password_path)
    else:
        passwd_txt = RawConfigParser()
        passwd_txt.add_section('password') 

    passwd_txt.set('password', 'password', new_password)
    with open(password_path, 'w') as new_password:
        passwd_txt.write(new_password)

########NEW FILE########
__FILENAME__ = security
#coding:utf-8
USERS = {'admin':'admin', 'viewer':'viewer'}
GROUPS = {'admin':['group:editors']}

def groupfinder(userid, request):
    if userid in USERS:
        return GROUPS.get(userid, [])

########NEW FILE########
__FILENAME__ = views
#coding:utf-8
from pyramid.response import Response
from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config, forbidden_view_config
from pyramid.security import remember, forget
from pyramid.events import subscriber
from pyramid.interfaces import IBeforeRender
from pyramid.url import static_url, resource_url, route_url
from pyramid.threadlocal import get_current_request
import time
import ztq_core
import utils 
import urllib
from utils.security import USERS

current_redis = None
MENU_CONFIG = {'title':u'ZTQ队列监控后台',
               'servers':[
                          #{'name':'oc', 'host':'192.168.1.115', 'port':60207, 'db':1, 'title':'OC'},
                          #{'name':'wo', 'host':'192.168.1.115', 'port':60206, 'db':1, 'title':'WO'},
                          #{'name':'viewer', 'host':'192.168.1.115', 'port':60208, 'db':0, 'title':'Viewer'},
                          ],
               'current_redis':'oc',
               'links':[('/workerstatus', u'工作状态'),
                     ('/taskqueues',u'工作队列'),
                     ('/errorlog',u'错误清单'),
                     ('/workerlog', u'工作历史'),
                     ('/syslog', u'系统日志'),
                     ('/password', u'修改密码'),
                     ('/logout', u'退出登录'),
                     ]
        }

@view_config(renderer='mainpage.html', permission='view')
def main_view(request):
    """后台管理首页
    """  
    return MENU_CONFIG

@view_config(name='top.html', renderer='top.html', permission='view')
def top_view(request):
    """后台管理首页
    """  
    return MENU_CONFIG

@view_config(name='menu.html', renderer='menu.html', permission='view')
def menu_view(request):
    """初始化菜单
    """
    return MENU_CONFIG

@view_config(name='workerstatus', renderer='worker.html', permission='edit')
def workers_view(request):
    """后台管理首页
    传出参数:worker的相关信息,各个队列的工作情况
    """

    workers = utils.get_worker_list()    
    return {'workers':workers}  

@view_config(name='syslog', permission='edit')
@view_config(name='workerlog', permission='edit')
@view_config(name='errorlog', permission='edit')
def route_main(request):
    route_name = request.view_name
    return HTTPFound(location=request.route_url(route_name, page=1))

#--------------日志信息--------------------------------    
@view_config(route_name='syslog', renderer='syslog.html', permission='edit')
def sys_log_view(request):
    """查看系统日志情况
    """
    page = request.matchdict.get('page', 1)
    page = int(page) or 1

    return pageination(utils.get_sys_log, page, 'sys_log')

#--------------转换历史--------------------------------    
@view_config(route_name='workerlog', renderer='workerlog.html', permission='edit')
def worker_log_view(request):
    """查看转换日志
    """
    page = request.matchdict.get('page', 1)
    page = int(page) or 1

    return pageination(utils.get_worker_log, page, 'worker_log')

#--------------切换Redis--------------------------------    
@view_config(name='switch_redis.html', permission='edit')
def switch_redis(request):
    """ 切换redis
    """
    redis_key = request.params.get('redis_name', '')
    for server in MENU_CONFIG['servers']:
        if server['name'] == redis_key:
            ztq_core.setup_redis('default', host=server['host'], port=server['port'], db=server.get('db', 1))
            MENU_CONFIG['current_redis'] = redis_key
            break

    route_name = request.view_name
    return HTTPFound(location="/")


#--------------调度管理--------------------------------
def config_worker(request):
    """对worker进行配置管理
    """
    url_action = request.params.get('action','')

    # 获取用户请求操作
    worker_id = request.matchdict['id']
    if url_action == 'delete': 
        #删除还没启用的worker,删除操作不会导致调度配置更新
        workers_dict = ztq_core.get_worker_state()
        del workers_dict[worker_id]
        worker_job = ztq_core.get_job_state(worker_id)
        for job_name, job_status in worker_job.items():
            del worker_job[job_name]
        return HTTPFound(location = '/workerstatus')
    elif url_action == 'update':
        # 发报告指令到各命令队列让worker报告自身状态
        worker_list = ztq_core.get_all_worker()
        for worker_name in worker_list:
            if worker_name == worker_id:
                utils.send_command(worker_name, 'report')
                time.sleep(1)
                return HTTPFound(location = '/workerstatus')
    return HTTPFound(location = '/workerstatus')

def stop_working_job(request):
    """停止正在进行中的转换的工作
    """
    kill_command =   {
     'command':'kill',
     'timestamp':int(time.time()),
     'pid':'',
     }
    # 获取url操作
    worker_id = request.matchdict['id']
    thread_pid = request.matchdict['pid']
    # pid为-1则不能杀
    if thread_pid == -1: return HTTPFound(location = '/workerstatus')
    else: kill_command['pid'] = thread_pid
    cmd_queue = ztq_core.get_command_queue(worker_id)
    # 避免同时发送多条结束命令
    if cmd_queue:
        for command in cmd_queue:
            if command.get('pid', None) == kill_command['pid']:    
                return HTTPFound(location = '/workerstatus')          
    cmd_queue.push(kill_command)  
    return HTTPFound(location = '/workerstatus')


#--------------查看队列详情-------------------------------
@view_config(name='taskqueues', renderer='queues.html', permission='edit')
def task_queues(request):
    """查看转换队列运行状态
    传出参数:所有原子队列的运行转换
    """
    task_job_length = 0
    error_job_length = 0
    # 计算原子队列,原始队列和错误队列的总长度
    queues_list = ztq_core.get_queue_config()
    for queue_name, queue_config in queues_list.items():
        task_job_length += len(ztq_core.get_task_queue(queue_name))
        error_job_length += len(ztq_core.get_error_queue(queue_name))
    task_queues = utils.get_taskqueues_list()
    
    return {'task_queues':task_queues,
            'task_job_length':task_job_length,
            'error_job_length':error_job_length, }
        
@view_config(route_name='taskqueue',renderer='jobs.html', permission='edit')
def taskqueue(request):
    """用于查看某个队列的详细信息和运行情况
    """
    queue_id = request.matchdict['id']
    jobs = utils.get_queues_jobs(queue_id)
    return {'jobs':jobs, 'queue_name':queue_id}    

def config_queue(request):
    """管理队列线程数量
       传入参数:http://server/taskqueues/q01/config?action=queue_down
    """
    queue_id = request.matchdict['id']
    url_action = request.params.get('action','')

    # 对所有的worker的队列调整数量
    for worker_name in ztq_core.get_worker_config():
        utils.update_queue_threads(work_name, queue_id, action=url_action)
    return HTTPFound(location = '/taskqueues') 
  
@view_config(route_name='taskqueue_action', permission='edit')
def task_jobs_handler(request):
    """将任务调整到队头或者队尾
    传入参数:http://server/taskqueues/q01/job?action=high_priority&hash_id={{job_hash_id}}
    """
    valid_action = ('high_priority','low_priority', 'delete')
    queue_name  = request.matchdict['id']
    url_action = request.params.get('action','')
    job_hash_id = urllib.unquote(request.params.get('hash_id').encode('utf8'))
    if url_action in valid_action:
        if url_action == 'high_priority':
            job_queue = ztq_core.get_task_queue(queue_name)
            job_queue.remove(job_hash_id)
            job_queue.push(job_hash_id, to_left=False)
        elif url_action == 'low_priority':
            job_queue = ztq_core.get_task_queue(queue_name)
            job_queue.remove(job_hash_id)
            job_queue.push(job_hash_id)
        elif url_action == 'delete':
            job_queue = ztq_core.get_task_queue(queue_name)
            job_queue.remove(job_hash_id)
            job_hash = ztq_core.get_task_hash(queue_name)
            job_hash.pop(job_hash_id)
        return HTTPFound(location = '/taskqueues/'+queue_name)
    else: 
        return Response('Invalid request')  

#--------------登录界面--------------------------------    
@view_config(route_name='login', renderer='templates/login.pt')
@forbidden_view_config(renderer='templates/login.pt')
def login(request):
    login_url = request.route_url('login')
    referrer = request.url
    if referrer == login_url:
        referrer = '/' # never use the login form itself as came_from
    came_from = request.params.get('came_from', referrer)
    message = ''
    login = 'admin'
    password = ''
    from utils.password import get_password
    if 'form.submitted' in request.params:
        login = request.params['login']
        password = request.params['password']
        try:
            if get_password() == password:
                headers = remember(request, login)
                return HTTPFound(location = came_from, headers = headers)
        except:
            if USERS.get(login) == password:
                headers = remember(request, login)
                return HTTPFound(location = came_from, headers = headers)
        message = 'Failed login'


    return dict(
        message = message,
        url = request.application_url + '/login',
        came_from = came_from,
        login = login,
        password = password,
        )

@view_config(route_name='logout')
def logout(request):
    headers = forget(request)
    return HTTPFound(location = '/workerstatus', headers = headers)

@view_config(route_name='password', renderer='templates/password.pt', permission='edit')
def password(request):
    new_password = ''
    from utils.password import modify_password
    if 'form.submitted' in request.params:
        new_password = request.params['new_password']
        modify_password(new_password)
        return HTTPFound(location= '/logout')

    return dict(
        new_password = new_password,
        url = request.application_url + '/password',
        )

#--------------错误处理--------------------------------    
@view_config(route_name='errorlog', renderer='errorlog.html', permission='edit')
def error_queue_detail(request):
    """用于查看所有错误队列的详细信息和运行情况
    error_queue = 'ztq:queue:error:' + queue_name
    """
    page = request.matchdict.get('page', 1)
    page = int(page) or 1
    return pageination(utils.get_all_error_jobs, page, 'error_jobs')

@view_config(route_name='errorqueue', renderer='errorlog.html', permission='edit')
def errorqueue(request):
    """用于查看单个错误队列的详细信息和运行情况
    """
    error_queue_id = request.matchdict['id']
    page = request.matchdict.get('page', 1)
    page = int(page) or 1
    return pageination(utils.get_error_queue, page, 
                        'error_jobs', error_queue_id)

def error_jobs_handler(request):
    """从错误队列中移除或重做某个失败的转换
       传入参数:http://server/errorqueues/q01/job?action=remove{redo}&hash_id={{hashid}}
    """
    valid_action = ('remove','redo')
    queue_id = request.matchdict['id']
    url_action = request.params.get('action','')
    hash_id = urllib.unquote(request.params.get('hash_id').encode('utf8'))
    if url_action in valid_action:
        if url_action == 'remove':
            ztq_core.pop_error(queue_id, hash_id)
        elif url_action == 'redo':
            task = ztq_core.pop_error(queue_id, hash_id)
            task['runtime'] = {'queue':queue_id, 'create':int(time.time())}
            ztq_core.push_runtime_task(queue_id, task)
        return HTTPFound(location = '/errorlog')
    else: return Response('Invalid request')

@view_config(route_name='redo_all_error_for_queue', permission='edit')
def redo_all_error_for_queue(request):    
    """重做这个错误队列所有的任务
    """
    queue_id = request.matchdict['id']

    while 1:
        error_task = ztq_core.pop_error(queue_id, timeout=-1)
        if error_task is None:
            break
        error_task['runtime'] = {'queue':queue_id, 'create':int(time.time())}
        ztq_core.push_runtime_task(queue_id, error_task)

    return HTTPFound(location = '/taskqueues')

@view_config(route_name='del_all_error_for_queue', permission='edit')
def del_all_error_for_queue(request):    
    """删除这个错误队列所有的任务
    """
    queue_id = request.matchdict['id']

    error_hash = ztq_core.get_error_hash(queue_id)
    error_queue = ztq_core.get_error_queue(queue_id)

    client = ztq_core.get_redis()
    client.delete(error_queue.name)
    client.delete(error_hash.name)

    return HTTPFound(location = '/taskqueues')

#-------------------------------------------------------------
@subscriber(IBeforeRender)
def add_globals(event):
    '''Add *context_url* and *static_url* functions to the template
    renderer global namespace for easy generation of url's within
    templates.
    '''
    request = event['request']
    def context_url(s, context=None,request=request):
        if context is None:
            context = request.context
        url = resource_url(context,request)
        if not url.endswith('/'):
            url += '/'
        return url + s
    def gen_url(route_name=None, request=request, **kw):
        if not route_name:
            local_request = get_current_request()
            route_name = local_request.matched_route.name
        url = route_url(route_name, request, **kw)
        return url
    event['gen_url'] = gen_url
    event['context_url'] = context_url
    event['static_url'] = lambda x: static_url(x, request)

def pageination(gen_func, page, resource_name, *args):
    sindex = ( page - 1 ) * 20
    eindex = page * 20
    fpage = page - 1
    npage = page + 1
    resource = gen_func(*args, sindex=sindex, eindex=eindex-1)
    return {resource_name:resource,
            'sindex':str(sindex + 1),
            'eindex':str(eindex),
            'fpage':fpage,
            'npage':npage,
            } 


########NEW FILE########
__FILENAME__ = test
#coding:utf-8
import unittest


import ztq_core

def echo():
    print 'hello'

class TestftsModel(unittest.TestCase):
    def setUp(self):
        ztq_core.setup_redis('default', '192.168.209.128', 6379)
        self.testmessage = {'test':'test'}
        
    def testJsonList(self):    
        """Test queue connect
        """
        self.queue = ztq_core.get_task_queue('q01')
        self.queue.append(self.testmessage)
        revmessage = self.queue.pop()
        self.assertEqual(revmessage,self.testmessage)
    
    def _testRegister(self):
        """测试JobThread
        """
        ztq_core.task.register(echo)
        ztq_core.task.task_push(u'foo:echo', 'aaa', 'bb', c='bar') 
        job_thread = ztq_core.task.JobThread('foo')
        job_thread.start()
        
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_list
'''
Created on 2011-4-18

@author: Zay
'''
from ztq_core import get_redis, get_list, get_hash, get_set, get_dict, setup_redis, \
get_key, set_key, get_queue

def main():
        setup_redis('default', '192.168.209.128', 6380)
        get_redis(system='default').delete('list')
        message = 'hello'
        
        Test_list = get_list('list',serialized_type='string')
        Test_list.append(message)
        
        #Test_list.remove(message)
        
        print get_redis(system='default').lrem('list', 0, 'hello')
        
        Test_set = get_set('set',serialized_type='string')
        Test_set.add(message)
        print get_redis(system='default').srem('set', 'hello')
        
        
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_redis_wrap
#coding:utf-8
'''
测试说明:
此测试是针对redis_wrap库进行自动json编码的测试

测试结果:
Ran 5 tests in 0.036s

FAILED (failures=1)

失败原因是在对list进行remove(value)操作的时候,redis的lrem无法删除序列化后的对象,
set类型能正常remove序列化后的对象.

@author: Zay
'''
import unittest
from ztq_core import get_redis, get_list, get_hash, get_set, get_dict, setup_redis, \
get_key, set_key, get_queue

class TestRediswrap(unittest.TestCase):
    def setUp(self):
        """初始化连接redis,和初始化变量
        """
        setup_redis('default', '192.168.209.128', 6379, socket_timeout=2)
        get_redis(system='default').delete('list')
        get_redis(system='default').delete('set')
        get_redis(system='default').delete('hash')
        get_redis(system='default').delete('dict')
        get_redis(system='default').delete('kv')
        get_redis(system='default').delete('queue')
        self.message = {"hello":"grizzly"}
        
    def test_getset(self):
        """进行基本的redis 的key进行get和set的操作.
        """
        Test_key = get_key('kv',serialized_type='json')
        self.assertEqual(Test_key,None)
        
        set_key('kv',self.message)
        
        Test_key = get_key('kv',serialized_type='json')
        self.assertEqual(Test_key,self.message)
        
    def test_dict(self):
        """测试redis_wrap的dict类型的操作
        """
        Test_dict = get_dict('dict',serialized_type='json')
        
        Test_dict['id'] = self.message
        self.assertEqual(self.message, Test_dict['id'])
        
        for k,v in Test_dict.items():
            self.assertEqual(k, 'id')
            self.assertEqual(v, self.message)
        
        del Test_dict['id']
        self.assertNotEqual(self.message,Test_dict.get('id'))
        
    def test_hash(self):
        """测试redis_wrap的 hash类型的操作
        """
        Test_dict = get_hash('hash',serialized_type='json')
        
        Test_dict['id'] = self.message
        self.assertEqual(self.message, Test_dict['id'])
        
        del Test_dict['id']
        self.assertNotEqual(self.message,Test_dict.get('id'))        
        
    def test_list(self):
        """进行redis_wrap的list的基本操作
        """
        Test_list = get_list('list',serialized_type='json')
        
        Test_list.append(self.message)
        self.assertEqual( len(Test_list),1)
    
        for item in Test_list:
            self.assertEqual(self.message, item)
            
        #这一步失败原因是redis的lrem方法有无法删除序列化后的数据
        Test_list.remove(self.message)
        self.assertEqual( len(Test_list),0)

    def test_set(self):
        """进行对redis_wrap的set类型的基本操作
        """
        Test_set = get_set('set',serialized_type='json')
        Test_set.add(self.message)
        
        for item in Test_set:
            self.assertEqual( item,self.message)
            
        Test_set.remove(self.message)
        self.assertEqual( len(Test_set),0)

    def test_queue(self):
        """进行redis_wrap的queue的基本操作
        """
        Test_queue = get_queue('queue',serialized_type='json')
        
        Test_queue.push(self.message)
        self.assertEqual( len(Test_queue),1)
    
        for item in Test_queue:
            self.assertEqual(self.message, item)
            
        #这一步失败原因是redis的lrem方法有无法删除数据
        Test_queue.remove(self.message)
        self.assertEqual( len(Test_queue),0)
    #===========================================================================
    # 
    #    message = Test_queue.pop(timeout= 1)
    #    self.assertEqual(self.message, message)
    #    self.assertEqual(len(Test_queue),0)
    #===========================================================================
        
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = async
# -*- encoding:utf-8 -*-

import types
from task import register, push_task, has_task, gen_task, push_buffer_task
import transaction

use_transaction = False

def _setup_callback(kw):
    callback = kw.pop('ztq_callback', None) 
    if callback is not None:
        callback_func, callback_args, callback_kw = callback
        callback_queue = callback_kw.pop('ztq_queue', callback_func._ztq_queue)
        kw.update({'ztq_callback':"%s:%s" % (callback_queue, callback_func.__raw__.__name__),
                   'ztq_callback_args':callback_args,
                   'ztq_callback_kw':callback_kw})
    fcallback = kw.pop('ztq_fcallback', None) 
    if fcallback is not None:
        callback_func, callback_args, callback_kw = fcallback
        callback_queue = callback_kw.pop('ztq_queue', callback_func._ztq_queue)
        kw.update({'ztq_fcallback':"%s:%s" % (callback_queue, callback_func.__raw__.__name__),
                   'ztq_fcallback_args':callback_args,
                   'ztq_fcallback_kw':callback_kw})
    pcallback = kw.pop('ztq_pcallback', None) 
    if pcallback is not None:
        callback_func, callback_args, callback_kw = pcallback
        callback_queue = callback_kw.pop('ztq_queue', callback_func._ztq_queue)
        kw.update({'ztq_pcallback':"%s:%s" % (callback_queue, callback_func.__raw__.__name__),
                   'ztq_pcallback_args':callback_args,
                   'ztq_pcallback_kw':callback_kw})

def push_task_to_queue(task_name, args, kw, on_commit=False, buffer=False):
    if on_commit:
        if buffer:
            add_after_commit_hook(push_buffer_task, (task_name,) + args, kw)
        else:
            add_after_commit_hook(push_task, (task_name,) + args, kw)
    else:
        if buffer:
            push_buffer_task(task_name, *args, **kw)
        else:
            push_task(task_name, *args, **kw)

def async(*_args, **_kw):
    """ 这是一个decorator，事务提交的时候，提交到job队列，异步执行 

    定义job
    =============
    第一种::

        @async
        def say_hello(name):
            print 'hello, ', name

    第二种, 预先指定队列执行信息::

        @async(queue='hello_queue', transaction=True)
        def say_hello(name):
            print 'hello, ', name

    使用方法
    ================
    支持如下几种::

        say_hello('asdfa')
        say_hello('asdfa', ztq_queue="asdfa", ztq_transaction=False)

    """
    if len(_args) == 1 and not _kw and isinstance(_args[0], types.FunctionType): # 不带参数的形式
        func = _args[0]
        def new_func1(*args, **kw):
            queue_name = kw.pop('ztq_queue', 'default')
            buffer = kw.pop('ztq_buffer', False)
            on_commit= kw.pop('ztq_transaction', use_transaction) 
            task_name = "%s:%s" % (queue_name, func.__name__)
            _setup_callback(kw)
            push_task_to_queue(task_name, args, kw, on_commit=on_commit, buffer=buffer)

        new_func1.__raw__ = func
        new_func1._ztq_queue = 'default'
        register(func)
        return new_func1
    else:
        _queue_name = _kw.get('queue', 'default')
        def _async(func):
            def new_func(*args, **kw):
                #on_commit= kw.pop('ztq_transaction', _on_commit) 
                on_commit= kw.pop('ztq_transaction', use_transaction) 
                queue_name = kw.pop('ztq_queue', _queue_name)
                buffer = kw.pop('ztq_buffer', False)
                task_name = "%s:%s" % (queue_name, func.__name__)
                _setup_callback(kw)
                push_task_to_queue(task_name, args, kw, on_commit=on_commit, buffer=buffer)

            new_func.__raw__ = func
            new_func._ztq_queue = _queue_name
            register(func)
            return new_func
        return _async

def prepare_task(func, *args, **kw):
    _setup_callback(kw)
    return func, args, kw

def ping_task(func, *args, **kw):
    queue_name = kw.pop('ztq_queue', func._ztq_queue)
    to_front = kw.pop('ztq_first', False)
    on_commit = kw.pop('ztq_transaction', None)
    run = kw.pop('ztq_run', False)
    task = gen_task(func.__raw__.__name__, *args, **kw)
    result = has_task(queue_name, task, to_front=to_front)
    if result == 'none' and run:
        kw['ztq_queue'] = queue_name
        kw['ztq_first'] = to_front
        if on_commit is not None:
            kw['ztq_transaction'] = on_commit
        func(*args, **kw)
    return result

#### 以下代码让队列的任务支持事务
def enable_transaction(enable):
    """ 是否支持transaction, 默认不支持 """
    global use_transaction
    use_transaction = bool(enable)

def _run_after_commit(success_commit, func, args, kw):
    if success_commit:
        func(*args, **kw)

def add_after_commit_hook(func, args, kw):
    """ 在事务最后添加一个钩子，让队列任务在事务完成后才做实际的操作
    """
    if not use_transaction: return 
    transaction.get().addAfterCommitHook(
                        _run_after_commit,
                        (func, args, kw),
                        )

########NEW FILE########
__FILENAME__ = cron
#coding:utf-8

""" 有一个定时执行的list: ztq:list:cron

放进去的工作，会定期自动执行
"""
from threading import Thread
import datetime
import time
import model
from task import split_full_func_name, push_task


def has_cron(func):
    if type(func) == str:
        func_name = func
    else:
        func_name = func.__raw__.__name__
    for cron in model.get_cron_set():
        if cron['func_name'] == func_name:
            return True
    return False

def add_cron(cron_info, full_func, *args, **kw):
    """ 定时执行 

    cron_info： {'minute':3, 'hour':3,}
    """
    cron_set = model.get_cron_set()
    if type(full_func) == str:
        queue_name, func_name = split_full_func_name(full_func)
    else:
        queue_name = full_func._ztq_queue
        func_name = full_func.__raw__.__name__
    cron_set.add({'func_name':func_name, 
                'cron_info':cron_info,
                'queue': queue_name,
                'args':args,
                'kw':kw})

def remove_cron(func):
    cron_set = model.get_cron_set()
    if type(func) == str:
        func_name = func
    else:
        func_name = func.__raw__.__name__
    for cron in cron_set:
        if cron['func_name'] == func_name:
            cron_set.remove(cron)

class CronThread(Thread):
    """ 定时检查cron列表，如果满足时间条件，放入相关的队列 """
    def __init__(self):
        super(CronThread, self).__init__()

    def run(self):
        """
            获取cron_info信息格式:{'minute':3, 'hour':3,}
        """
        cron_set = model.get_cron_set()
        while True:
            # 遍历cron列表检查并检查定时执行信息
            for cron in cron_set:
                execute_flag = self.check_cron_info(cron['cron_info'])
                if execute_flag:
                    push_task(cron['queue'] + ':' + cron['func_name'], *cron['args'], **cron['kw'])

            time.sleep(55)

    def check_cron_info(self, cron_info):
        """检查定时执行信息是否满足条件
        """
        time_now = datetime.datetime.now()
        hour_cron = int(cron_info.get('hour', -1)) 
        if hour_cron != -1:
            hour_now = int(time_now.hour)
            if hour_now != hour_cron:
                return False

        minute_cron = int(cron_info.get('minute', 0))
        minute_now = int(time_now.minute)
        if minute_cron != minute_now:
            return False
        return True

def start_cron():
    cron_thread = CronThread()
    cron_thread.setDaemon(True)
    cron_thread.start()

########NEW FILE########
__FILENAME__ = demo
# encoding: utf-8
#  my_send.py
from ztq_core import async
import ztq_worker
import time

@async(queue='mail')
def send(body):
    print 'START: ', body
    time.sleep(5)
    print 'END: ', body

@async(queue='mail')
def send2(body):
    print 'START2 … ', body
    raise Exception('connection error')

@async(queue='mail')
def call_process(filename):
    print 'call process:', filename
    ztq_worker.report_job(12323, comment=filename)
    time.sleep(20)

@async(queue='mail')
def fail_callback(return_code, return_msg):
    print 'failed, noe in failed callback'
    print return_code, return_msg

def test():
    import ztq_core
    import transaction

    from ztq_core import demo

    ztq_core.setup_redis('default','localhost', 6379, 1)

    demo.send('*' * 40, ztq_queue='mail')

    demo.send('transaction will on', ztq_queue='mail')
    ztq_core.enable_transaction(True)

    demo.send('transaction msg show later')
    demo.send('no transaction msg show first', ztq_transaction=False)
    time.sleep(5)
    transaction.commit()
    
    ztq_core.enable_transaction(False)

    demo.send('transaction off')
    callback = ztq_core.prepare_task(demo.send, 'yes, callback!!')
    demo.send('see callback?', ztq_callback=callback)

    ff = ztq_core.prepare_task(demo.fail_callback)
    demo.send2('send a failed msg, see failed callback?', ztq_fcallback=ff)

    call_process('saa.exe')

if __name__ == '__main__':
    test()

########NEW FILE########
__FILENAME__ = model
#coding:utf-8
from redis_wrap import get_set, get_key, set_key, \
get_queue, get_dict, get_keys, get_limit_queue, get_hash

def get_all_task_queue():
    """返回所有原子队列的key
            返回类型:list
    """
    task_queue = "ztq:queue:task:"
    return get_keys(task_queue)

def get_all_error_queue():
    """返回所有原子队列的key
            返回类型:list
    """
    task_queue = "ztq:queue:error:"
    return get_keys(task_queue)

def get_task_hash(queue_name):
    """ 得到 一个 task_md5 -> task 的字典对象 """
    return get_hash('ztq:hash:task:' + queue_name)

def get_task_set(queue_name, serialized_type='json'):
    """ 得到 一个 task_md5 -> task 的字典对象 """
    return get_set('ztq:set:task:' + queue_name, serialized_type=serialized_type)

def get_task_queue(queue_name):
    """根据传入参数queue_name

    {"func":'transform',
     'args':(),
     'kw':{'path':'c:\\abc.doc',              #源文件路径
      'mime':'application/ms-word',      #源文件类型
      'transform':[
         {'path':'d:\\abc.html',  
          'mime':'text/html',
          'callback':'http://xxx.com/asss'

          'transform':[
             {'path':'d:\\abc.txt',
              'mime':'text/plain',
              'transform':[]
             }, # 转换子文件放在同一文件夹中
          ]}]},

     'callback':callback,            # 全部完成调用方法
     'callback_args':callback_args,  # 全部完成的调用参数
     'callback_kw':callback_kw,

     'pcallback':callback, # progress callback 部分完成的调用
     'pcallback_args':callback_args, # 部分完成的调用参数
     'pcallback_kw':callback_kw,     # 部分完成调用参数

     'fcallback':callback,            # 失败调用方法
     'fcallback_args':callback_args,  # 失败的调用参数
     'fcallback_kw':callback_kw,

     "runtime":{ # 队列运行相关信息
       'created':12323423   # 进入队列时间
     }
    }
    """
    #ListFu
    atom_queue = "ztq:queue:task:" + queue_name
    return get_queue(atom_queue, serialized_type='string')

def get_command_queue(name):
    """ 同步配置、状态报告、杀死转换线程
    
       要求同步worker配置
    {
     'command':'updateworker',
     'timestamp':''
                   }
        要求同步转换器线程驱动
    {
     'command':'updatedriver',
     'timestamp':''
                   }
                   
        要求worker报告整体工作状态::

     {
     'command':'report',
     'timestamp': 
     }
        后台杀一个转换进程（可能卡死）::
     {
     'command':'kill',
     'timestamp':
     'pid':'2121',
     }
    
    用户取消一个转换进程，和杀死类似，不应该进入错误队列，日志也需要说明是取消::
     {
     'command':'cancel',
     'timestamp':
     'pid':'2121',
     }
    """
    command_queue = 'ztq:queue:command:'+name
    return get_queue(command_queue)

def get_work_log_queue():
    """ json格式为::

     {'func':'transform',
      'kw':{ ... # 和前面task_queue相同
         },
      "runtime":{ # 队列运行相关信息
         'created':12323423   #进入原始队列时间
         'queue':'q01'  # 是在哪个原子原子队列
         'start':123213123    #转换开始时间
         'end':123213123    #转换结束时间
         'worker':'w01', # 转换器名
         'thread':'131231', # 
         'return':-1, # 返回的错误代号, 0表示成功 
         'reason':'失败原因' # 详细的原因
       }
      }
    """
    work__log_queue = "ztq:queue:worker_log"
    return get_limit_queue(work__log_queue, 200)

def get_error_hash(queue_name, system='default'):
    """ json格式和work_log相同 """
    error_queue = 'ztq:hash:error:' + queue_name
    return get_hash(error_queue, system=system)

def get_error_queue(queue_name, system='default'):
    """ json格式和work_log相同 """
    error_queue = 'ztq:queue:error:' + queue_name
    return get_queue(error_queue, system=system, serialized_type='string')

def get_buffer_queue(queue_name, system='default'):
    """ json格式和work_log相同 """
    buffer_queue = 'ztq:queue:buffer:' + queue_name
    return get_queue(buffer_queue, system=system)

def get_system_log_queue():
    """
    Json格式为:
    {'alias':'w01'
     'host':'192.168.1.100'
     'timestamp':123213123
     'type': 'reboot' or 'shutdown' or 'power' 三个值中其中一个
    }
    """
    system__log_queue ='ztq:queue:system_log'
    return get_limit_queue(system__log_queue, 200)

def get_callback_queue():
    callback_queue='ztq:queue:callback'
    return get_queue(callback_queue)

# state -------------------------------------------------------------------
def get_all_worker():
    """返回正在运行中的转换器列表
            返回类似:list
    """
    prefix = 'ztq:state:worker:'
    return get_keys(prefix)

def get_worker_state():
    """ transformer在如下2种状况下会，会由指令线程上报转换器的状态::

    - 启动的时候
    - 有指令要求

        在redis中的存放格式为::

      {'ip':'192.168.1.1',
       'cpu_style':'Dural Xommm 1G',
       'cpu_percent':'30%',
       'mem_total':'2G',
       'mem_percent':'60%',
       'started':1231231231,
       'timestamp':12312312,
       'tracebacks':'全部线程的traceback信息，用于死锁检查',
      }
        转换器状态信息，主要用于监控转换器是否良性工作，会在监控界面中显示。
    """
    prefix = 'ztq:state:worker:'
    return get_dict(prefix)

def get_job_state(worker_job_name):
    """ 转换器w01，第0号转换线程的当前转换任务信息

    - 每次开始转换，需要记录转换的信息
    - 每次结束的时候，需要清空

    json格式为::
    
     {'func':'transform',
      'kw':{ ... # 和上面task_queue相同
         },
      'runtime':{... # 和上面work_log相同
       }
      'process':{
          'pid': 212,  # -1 表示不能杀
          'start':131231,
          'comment':'d:\ssd.pdf'
         }
      }
    """
    prefix = 'ztq:state:job:%s:' % worker_job_name
    return get_dict(prefix)

def get_queue_config():
    """记录queue的基本信息
    {'title':'sys_cron-0',  #可选
     'tags':(['sys_cron']),  #可选
    }             #可选
    """
    prefix = 'ztq:config:queue:'
    return get_dict(prefix)

def get_worker_config():
    """ 配置工作线程：处理哪些队列，几个线程，间隔时间::
    {'q01':[{ 'interval':5,  # 间隔时间
              'from_right':True, }],  # 队列处理的方向，左（l）或者右（r） 
     'q02':[{'interval':5, 'from_right':False},
            {'interval':3, 'from_right':True}],
    }
    """
    prefix = 'ztq:config:worker:'
    return get_dict(prefix)

def get_driver_config():
    """
    TODO:消息格式
    """
    prefix = 'ztq:config:driver:'
    return get_dict(prefix)

def get_cron_set():
    """ 定时任务list
    TODO
    """
    return get_set('ztq:set:cron')
  

########NEW FILE########
__FILENAME__ = redis_wrap
#coding:utf-8

import redis
import pickle
try:
    import json
except :
    import simplejson as json

import UserDict, UserList

ConnectionError = redis.exceptions.ConnectionError
ResponseError = redis.exceptions.ResponseError

DEFAULT_ENCODING = 'UTF-8' # sys.getdefaultencoding()
#--- System related ----------------------------------------------
SYSTEMS = {
    'default': redis.Redis(host='localhost', port=6379)
}


def setup_redis(name, host, port, db=0, **kw):
    SYSTEMS[name] = redis.Redis(host=host, port=port, db=db, **kw)

def get_redis(system='default'):
    return SYSTEMS[system]

#--- Decorators ----------------------------------------------
def get_list(name, system='default',serialized_type='json'):
    return ListFu(name, system, serialized_type=serialized_type)

def get_queue(name, system='default',serialized_type='json'):
    return QueueFu(name, system, serialized_type=serialized_type)

def get_limit_queue(name, length, system='default',serialized_type='json'):
    return LimitQueueFu(name, length, system, serialized_type=serialized_type)

def get_hash(name, system='default',serialized_type='json'):
    return HashFu(name, system, serialized_type=serialized_type)

def get_set(name, system='default',serialized_type='json'):
    return SetFu(name, system, serialized_type=serialized_type)

def get_dict(name, system='default',serialized_type='json'):
    return DictFu(name, system, serialized_type=serialized_type)

def get_key(name, system='default',serialized_type='json'):
    loads = load_method[serialized_type]
    value = get_redis(system).get(name)
    try:
        return loads(value)
    except:return value

def del_key(name, system='default'):
    get_redis(system).delete(name)
    
def get_keys(name, system='default'):
    for key in get_redis(system).keys(name + "*"):
        key_name = key[len(name):]
        yield key_name
   
def set_key(name, value, system='default',serialized_type='json'):
    dumps = dump_method[serialized_type]
    value = dumps(value)
    get_redis(system).set(name, value)

#---serialize data type----------------------------------------
def _convert_persistent_obj(obj):
    # fix json.dumps raise TypeError
    # 是persistent 对象
    if isinstance(obj, (UserDict.UserDict, dict)):
        return dict(obj)
    elif isinstance(obj, (UserList.UserList, list, set)):
        return list(obj)
    raise TypeError, '%s: %s is not JSON serializable'%(type(obj), repr(obj))

dump_method = {'json':lambda item : json.dumps(item, sort_keys=True, \
                encoding=DEFAULT_ENCODING, default=_convert_persistent_obj),
               'pickle':pickle.dumps,
               'string':str
               }
load_method = {'json':json.loads,
               'pickle':pickle.loads,
               'string':str
               }
    
#--- Data impl. ----------------------------------------------
class ListFu(object):

    def __init__(self, name, system, serialized_type='json'):
        self.name = name
        self.system = system
        self.type = serialized_type
        self.dumps = dump_method[serialized_type]
        self.loads = load_method[serialized_type]
        
    def append(self, item):
        item = self.dumps(item)
        get_redis(self.system).lpush(self.name, item)

    def extend(self, iterable):
        for item in iterable:
            self.append(item)
    
    def remove(self, value):
        value = self.dumps(value)
        get_redis(self.system).lrem(self.name, value)

    def pop(self, index=None):
        if index:
            raise ValueError('Not supported')
        serialized_data = get_redis(self.system).rpop(self.name)
        if serialized_data[1]:
            item = self.loads(serialized_data[1])
            return item
        else: return None

    def __len__(self):
        return get_redis(self.system).llen(self.name)

    def __iter__(self):
        client = get_redis(self.system)
        i = 0
        while True:
            items = client.lrange(self.name, i, i+30)
            if len(items) == 0:
                break
                #raise StopIteration
            for item in items:
                yield self.loads(item)
            i += 30

    def __getitem__(self, index):
        client = get_redis(self.system)
        value = client.lindex(self.name, index)
        return self.loads(value) if value else None

    def __getslice__(self, i, j):
        client = get_redis(self.system)
        items = client.lrange(self.name, i, j)
        for item in items:
            yield self.loads(item)

class HashFu:

    def __init__(self, name, system, serialized_type='json'):
        self.name = name
        self.system = system
        self.dumps = dump_method[serialized_type]
        self.loads = load_method[serialized_type]

    def get(self, key, default=None):
        value = get_redis(self.system).hget(self.name, key)
        try:
            return self.loads(value)
        except: return default
        
    def items(self):
        for key in self.keys():
            # key_list 不是实时的数据
            # 这个任务可能已经被取走了（当监视这个队列的工作线程有多个的时候）
            value = self.get(key)
            if value is None: continue

            yield key, value

    def keys(self):
        return get_redis(self.system).hkeys(self.name) or []

    def values(self):
        _values = self.loads(get_redis(self.system).hvals(self.name))
        return _values or []

    def pop(self, key):
        pline = get_redis(self.system).pipeline()
        pline.hget(self.name, key).hdel(self.name, key)
        _value, _expire = pline.execute()
        if _expire:
            return self.loads(_value)
        else:
            #raise KeyError,'redis hasher not match the %s key\n\n'%key
            print 'redis hasher not match the %s key\n\n'%key
            return None

    def __len__(self):
        return get_redis(self.system).hlen(self.name) or 0

    def __getitem__(self, key):
        val = self.get(key)
        if not val:
            raise KeyError
        return val

    def __setitem__(self, key, value):
        value = self.dumps(value)
        return get_redis(self.system).hset(self.name, key, value)

    def __delitem__(self, key):
        get_redis(self.system).hdel(self.name, key)

    def __contains__(self, key):
        return get_redis(self.system).hexists(self.name, key)

    def update(self, new_dict, **kw):
        update = {}

        if new_dict and hasattr(new_dict, 'keys'):
            for key in new_dict:
                update[key] = self.dumps(new_dict[key])
        elif new_dict:
            for key, value in new_dict:
                update[key] = self.dumps(key)

        for key in kw:
            update[key] = self.dumps(key[key])

        if update:
            get_redis(self.system).hmset(self.name, update)

class SetFu:

    def __init__(self, name, system, serialized_type='json'):
        self.name = name
        self.system = system
        self.dumps = dump_method[serialized_type]
        self.loads = load_method[serialized_type]
        
    def add(self, item):
        item = self.dumps(item)
        get_redis(self.system).sadd(self.name, item)

    def remove(self, item):
        item = self.dumps(item)
        get_redis(self.system).srem(self.name, item)

    def pop(self, item):
        item = self.serializer.dumps(item)
        value = get_redis(self.system).spop(self.name, item)
        return self.loads(value)

    def __iter__(self):
        client = get_redis(self.system)
        for item in client.smembers(self.name):
            yield self.loads(item)

    def __len__(self):
        return len(get_redis(self.system).smembers(self.name))

    def __contains__(self, item):
        item = self.dumps(item)
        return get_redis(self.system).sismember(self.name, item)

class DictFu:
    
    def __init__(self, name, system, serialized_type='json'):
        self.name = name
        self.system = system
        self.dumps = dump_method[serialized_type]
        self.loads = load_method[serialized_type]
    
    def get(self, key, default=None):
        value = get_redis(self.system).get(self.name+key)
        try:
            return self.loads(value)
        except: return default
        
    def set(self, key, value):
        value = self.dumps(value)
        get_redis(self.system).set(self.name+key, value)
    
    def __delitem__(self, key):
        get_redis(self.system).delete(self.name+key)
    
    def __len__(self):
        listkey = get_redis(self.system).keys(self.name+"*")
        return len(listkey) or 0

    def keys(self):
        prefix_len = len(self.name)
        return [key[prefix_len:] for key in get_redis(self.system).keys(self.name + "*")]

    def items(self):
        # XXX self.get 每次都要连结redis， 这样不好
        key_list = get_redis(self.system).keys(self.name+"*")
        for key in key_list:
            key_name = key[len(self.name):]

            # key_list 不是实时的数据
            # 这个任务可能已经被取走了（当监视这个队列的工作线程有多个的时候）
            value = self.get(key_name)
            if value is None: continue

            yield key_name, value
    
    def __getitem__(self, key=''):
        val = self.get(key, None)
        if val is None:
            raise KeyError
        return val
    
    def __setitem__(self, key, value):
        self.set(key, value)
    
    def __contains__(self, key):
        return get_redis(self.system).exists(self.name+key)

class QueueFu(ListFu):

    def __init__(self, name, system, serialized_type='json'):
        super(QueueFu,self).__init__(name, system, serialized_type=serialized_type)
 
    def push(self, item, to_left=True):
        if to_left:
            self.append(item)
        else: 
            item = self.dumps(item)
            get_redis(self.system).rpush(self.name, item)
            
    def pop(self, timeout=0, from_right = True):
        """ 
            得到redis list 对象中的一个item，并把item 从 redis list 对象中删除
            from_right: 如果值为真，从redis list 对象右边读取，反之，从左边读取
            timeout: timeout 等于大于0，以阻塞式获取。timeout 小于0，直接获取返回
        """
        if from_right:
            if timeout >= 0:
                serialized_data = get_redis(self.system).brpop(self.name, timeout)
            else:
                serialized_data = get_redis(self.system).rpop(self.name)
        else:
            if timeout >= 0:
                serialized_data = get_redis(self.system).blpop(self.name, timeout)
            else:
                serialized_data = get_redis(self.system).lpop(self.name)

        if serialized_data:
            # 阻塞式获取，返回self.name, result
            if isinstance(serialized_data, (tuple, list, set)) and \
                    len(serialized_data) == 2:
                return self.loads(serialized_data[1]) if serialized_data[1] else None
            # 直接获取，返回 result
            else:
                return self.loads(serialized_data)

        return None
     
    def reverse(self):
        """倒序输出结果 
        """
        client = get_redis(self.system)
        length = client.llen(self.name)
        for index in xrange(length-1, -1, -1):
            item = client.lindex(self.name, index)
            yield self.loads(item)
        
class LimitQueueFu(QueueFu):
    """此队列类用于控制队列长度，主要用于日志
    """
    def __init__(self, name, length, system, serialized_type='json'):
        super(LimitQueueFu,self).__init__(name, system, serialized_type=serialized_type)
        self.length = length - 1
        
    def push(self, item):
        #QueueFu.push(self, item)
        #get_redis(self.system).ltrim(self.name, 0, self.length)

        item = self.dumps(item)
        pline = get_redis(self.system).pipeline()
        pline.lpush(self.name, item).ltrim(self.name, 0, self.length)
        pline.execute()


########NEW FILE########
__FILENAME__ = task
#coding:utf-8
""" redis任务队列
"""

import model
import time
from threading import Thread
from hashlib import md5
from redis_wrap import dump_method

task_registry = {}

def register(func, func_name = None):
    """ 注册task

    定义::

      def echo(aaa, bb, c=1):
          print aaa, bb, c

    注册远端任务::

      from zopen_redis import task_registry
      task_registry.register(echo)
    """
    task_registry[func_name or func.__name__] = func

def split_full_func_name(full_func_name):
    splitted_func_name = full_func_name.rsplit(':', 1)
    # 如果没有，就到默认队列
    if len(splitted_func_name) == 1:
        return 'default', full_func_name
    else:
        return splitted_func_name

def gen_task(func_name, *args, **kw):
    callback = kw.pop('ztq_callback', '')
    callback_args = kw.pop('ztq_callback_args', ()) 
    callback_kw = kw.pop('ztq_callback_kw', {})

    fcallback = kw.pop('ztq_fcallback', '')
    fcallback_args = kw.pop('ztq_fcallback_args', ()) 
    fcallback_kw = kw.pop('ztq_fcallback_kw', {})

    pcallback = kw.pop('ztq_pcallback', '')
    pcallback_args = kw.pop('ztq_pcallback_args', ()) 
    pcallback_kw = kw.pop('ztq_pcallback_kw', {})
    return {'func':func_name,
                'args':args,
                'kw':kw, 

                'callback':callback,
                'callback_args':callback_args,
                'callback_kw':callback_kw,

                'fcallback':fcallback,
                'fcallback_args':fcallback_args,
                'fcallback_kw':fcallback_kw,

                'pcallback':pcallback,
                'pcallback_args':pcallback_args,
                'pcallback_kw':pcallback_kw,
            }

def _get_task_md5(task):
    """ 得到task(dict) 的md5值 """
    #_value = json.dumps(task, sort_keys=True)
    _value = dump_method['json'](task)

    return md5(_value).digest()

def push_buffer_task(full_func_name, *args, **kw):
    queue_name, func_name = split_full_func_name(full_func_name)
    task = gen_task(func_name, *args, **kw)
    model.get_buffer_queue(queue_name).push(task)

def push_task(full_func_name, *args, **kw):
    """
    callback: 这是另外一个注册的task，在func调用完毕后，会启动这个

    加入队列::

     task_regitry.push(u'foo:echo', aaa, bb, foo='bar', 
            callback='foo:callback', callback_args=(12,32,3), callback_kw={}) 
    """
    queue_name, func_name = split_full_func_name(full_func_name)
    to_right = kw.pop('ztq_first', False)
    # 队列运行相关信息
    runtime = kw.pop('runtime', \
            {'create':int(time.time()), 'queue':queue_name})

    task = gen_task(func_name, *args, **kw)
    task_md5 = _get_task_md5(task)

    task_hash = model.get_task_hash(queue_name)

    # 因为queue队列有worker不停在监视,必须先将hash的内容push,在将queue的内容push
    task['runtime'] = runtime
    if task_hash.__setitem__(task_md5, task) == 1:
        # 如果返回值等于0， 说明task_md5已经存在
        queue = model.get_task_queue(queue_name)
        queue.push(task_md5, to_left=not to_right)

def push_runtime_task(queue_name, task):
    """ 直接将task push 到 redis """
    _push_runtime_job(queue_name, task, model.get_task_hash, model.get_task_queue)

def push_runtime_error(queue_name, error):
    _push_runtime_job(queue_name, error, model.get_error_hash, model.get_error_queue)

def _push_runtime_job(queue_name, task, get_hash, get_queue):
    to_left = task.get('kw', {}).pop('to_left', True)
    runtime = task.pop('runtime') 

    task_md5 = _get_task_md5(task)
    task_hash = get_hash(queue_name)

    # 因为queue队列有worker不停在监视,必须先将hash的内容push,在将queue的内容push
    task['runtime'] = runtime
    if task_hash.__setitem__(task_md5, task) == 1:
        # 如果返回值等于0， 说明task_md5已经存在
        queue = get_queue(queue_name)
        queue.push(task_md5, to_left=to_left)

def pop_task(queue_name, task_md5=None, timeout=0, from_right=True):
    """ 取出，并删除 """
    return _pop_job(queue_name, task_md5, 
            model.get_task_hash, model.get_task_queue, timeout, from_right)

def pop_error(queue_name, task_md5=None, timeout=0, from_right=True):
    return _pop_job(queue_name, task_md5, 
            model.get_error_hash, model.get_error_queue, timeout, from_right)

def _pop_job(queue_name, task_md5, get_hash, get_queue, timeout=0, from_right=True):

    if not task_md5:
        task_md5 = get_queue(queue_name).pop(timeout=timeout, \
                from_right=from_right)
    else:
        get_queue(queue_name).remove(task_md5)

    if not task_md5: return None # 可能超时了

    task_hash = get_hash(queue_name)
    return task_hash.pop(task_md5)

class JobThread(Thread):
    def __init__(self,queue_name):
        super(JobThread,self).__init__()
        self.queue_name = queue_name

    def run(self):
        """ 阻塞方式找到任务，并自动调用"""
        queue = model.get_task_queue(self.queue_name)
        while True:
            task = queue.pop()
            try:
                task_registry[task['func']](*task['args'], **task['kw'])
                if task['callback']:
                    callback_args = task.get('callback_args', ())
                    callback_kw = task.get('callback_kw', {})
                    push_task(task['callback'], *callback_args, **callback_kw)
            except Exception, e:
                print str(e)

def has_task(queue_name, task, to_front=False):
    """ 检查是否存在某个job
    在queue_name的队列上，在arg_index的位置，对于func_name, 值为arg_value 
    如果不存在，返回false， 在worker中工作，返回‘work'， 队列中返回’queue'
    """
    runtime = task.pop('runtime', None)
    task_md5 = _get_task_md5(task)
    if not runtime is None: task['runtime'] = runtime

    # 检查work现在的工作
    worker_list = model.get_all_worker()
    for worker_name in worker_list:
        worker_job = model.get_job_state(worker_name)
        if not worker_job: continue
        for thread_name, job in worker_job.items():
            job.pop('runtime', '')
            job.pop('process', '')
            if _get_task_md5(job) == task_md5:
                return 'running'

    # 检查所在队列
    queue_name = queue_name 
    task_hash = model.get_task_hash(queue_name)
    if task_md5 in task_hash:
        if to_front: # 调整顺序
            task_queue = model.get_task_queue(queue_name)
            task_queue.remove(task_md5)
            task_queue.push(task_md5, to_left=False)
        return 'queue'

    return 'none'


########NEW FILE########
__FILENAME__ = utils
#coding:utf-8
from async import async
import redis_wrap
import urllib2
from cron import has_cron, add_cron

@async(queue='clock')
def bgrewriteaof():
    """ 将redis的AOF文件压缩 """
    redis = redis_wrap.get_redis()
    redis.bgrewriteaof()

def set_bgrewriteaof():
    # 自动定时压缩reids
    if not has_cron(bgrewriteaof):
        add_cron({'hour':1}, bgrewriteaof)

@async(queue='urlopen')
def async_urlopen(url, params=None):
    try:
        # 将unicode转换成utf8
        urllib2.urlopen(url.encode('utf-8'), params)
    except IOError:
        raise IOError('Could not connected to %s' % url)


########NEW FILE########
__FILENAME__ = tasks
# encoding: utf-8
from ztq_core import async
import time

@async
def send(body):
    print 'START: ', body
    time.sleep(3)
    print 'END: ', body

@async(queue='mail')
def send_failed(body):
    print 'FAIL START:', body
    raise Exception('connection error...')

@async(queue='mail')
def failed_callback(return_code, return_msg):
    print 'FAILED CALLBACK:', return_code, return_msg

@async(queue='index')
def index(data):
    print 'INDEX:', data
    time.sleep(1)

def do_commit():
    print 'COMMITTED'

import ztq_worker
ztq_worker.register_batch_queue('index', 5, do_commit)

########NEW FILE########
__FILENAME__ = test5
# encoding: utf-8
#  my_send.py
import time
import ztq_core
import transaction
from ztq_demo.tasks import send, send_failed, failed_callback

ztq_core.setup_redis('default','localhost', 6379, 3)

#send('hello, world 1')
#send('hello, world 2')
#send('hello, world 3')



#send('hello, world 3', ztq_queue='mail')



#ztq_core.enable_transaction(True)
#send('send 1')
#send('send 2')
#print 'send, waitting for commit'
#time.sleep(5)
#transaction.commit()
#print 'committed'




#ztq_core.enable_transaction(True)
#send('transaction msg show later')
#send('no transaction msg show first', ztq_transaction=False)
#transaction.commit()


#ztq_core.enable_transaction(False)
#callback = ztq_core.prepare_task(send, 'yes, callback!!')
#send('see callback?', ztq_callback=callback)

#fc = ztq_core.prepare_task(failed_callback)
#send_failed('send a failed msg, see failed callback?', ztq_fcallback=fc)


########NEW FILE########
__FILENAME__ = test_batch
# encoding: utf-8
#  my_send.py
import time
import ztq_core
from ztq_demo.tasks import index

ztq_core.setup_redis('default','localhost', 6379, 3)

index('only one')

time.sleep(3)

for i in range(8):
   index('data %d' % i)

########NEW FILE########
__FILENAME__ = test_callback
# encoding: utf-8
#  my_send.py
import time
import ztq_core
import transaction
from ztq_demo.tasks import send

ztq_core.setup_redis('default','localhost', 6379, 3)

callback = ztq_core.prepare_task(send, 'yes, callback!!')
send('see callback?', ztq_callback=callback)


########NEW FILE########
__FILENAME__ = test_fcallback
# encoding: utf-8
#  my_send.py
import time
import ztq_core
import transaction
from ztq_demo.tasks import send, send_failed, failed_callback

ztq_core.setup_redis('default','localhost', 6379, 3)

callback = ztq_core.prepare_task(send, 'succeed!', ztq_queue='mail')
fcallback = ztq_core.prepare_task(failed_callback)

send('send a good msg, see what?', 
		ztq_queue= 'mail',
		ztq_callback=callback,
		ztq_fcallback=fcallback)

send_failed('send a failed msg, see what?', 
		ztq_callback=callback,
		ztq_fcallback=fcallback)


########NEW FILE########
__FILENAME__ = test_ping
import time
import ztq_core
from ztq_demo.tasks import send

ztq_core.setup_redis('default','localhost', 6379, 3)

send('hello, world 1')
send('hello, world 2')

print 'hello, world 1:'
import pdb; pdb.set_trace()
print ztq_core.ping_task(send, 'hello, world 1')
print 'hello, world 2:'
print ztq_core.ping_task(send, 'hello, world 2')

########NEW FILE########
__FILENAME__ = test_queue
import time
import ztq_core
from ztq_demo.tasks import send

ztq_core.setup_redis('default','localhost', 6379, 3)

send('hello, world 1')
send('hello, world 2')
send('hello, world 3')

send('hello, world 4', ztq_queue='mail')

########NEW FILE########
__FILENAME__ = test_transaction
# encoding: utf-8
#  my_send.py
import time
import ztq_core
import transaction
from ztq_demo.tasks import send

ztq_core.setup_redis('default','localhost', 6379, 3)

ztq_core.enable_transaction(True)

send('transaction send 1')
send('transaction send 2')

send('no transaction msg show first', ztq_transaction=False)

print 'send, waitting for commit'
time.sleep(5)

transaction.commit()
print 'committed'


########NEW FILE########
__FILENAME__ = buffer_thread
# -*- encoding: utf-8 -*-
import threading
import time

import ztq_core

class BufferThread(threading.Thread):

    def __init__(self, config):
        """ cofnig: {'job-0':{'thread_limit': 50},,,}
        """
        super(BufferThread, self).__init__()
        self.config = config
        self._stop = False

    def run(self):

        if not self.config: return 

        while not self._stop:
            for buffer_name, buffer_config in self.config.items():

                # 需要停止
                if self._stop: return

                self.buffer_queue = ztq_core.get_buffer_queue(buffer_name)
                self.task_queue = ztq_core.get_task_queue(buffer_name)
                self.buffer_name = buffer_name
                self.task_queue_limit = int(buffer_config['thread_limit'])

                while True:
                    try:
                        self.start_job()
                        break
                    except ztq_core.ConnectionError:
                        time.sleep(3)

            time.sleep(1)

    def start_job(self):
        over_task_limit = self.task_queue_limit - len(self.task_queue)

        # 这个任务可能还没有push上去，服务器就挂了，需要在重新push一次
        if getattr(self, 'buffer_task', None):
            self.push_buffer_task()

        # 相关的任务线程，处于繁忙状态
        if over_task_limit <= 0:
            return

        # 不繁忙，就填充满
        else:
            while over_task_limit > 1:

                # 需要停止
                if self._stop: return

                # 得到一个任务
                self.buffer_task = self.buffer_queue.pop(timeout=-1)
                if self.buffer_task is None:
                    return 

                self.push_buffer_task()

                self.buffer_task = None
                over_task_limit -= 1

    def push_buffer_task(self):
        if 'runtime' not in self.buffer_task:
            self.buffer_task['runtime'] = {}

        ztq_core.push_runtime_task(self.buffer_name, self.buffer_task)

    def stop(self):
        self._stop = True

########NEW FILE########
__FILENAME__ = command_execute
# -*- encoding: utf-8 -*-

#from zopen.transform import set_drive_config
from config_manager import CONFIG
from job_thread_manager import JobThreadManager
from buffer_thread import BufferThread
from system_info import get_cpu_style, get_cpu_usage, get_mem_usage
import os
import sys
import traceback
import time
import ztq_core

# 管理工作线程, 添加线程、删除线程、保存信息
job_thread_manager = JobThreadManager()

# buffer 线程
buffer_thread_instance = None

def set_job_threads(config_dict):
    """ 根据配置信息和job_thread_manager.threads 的数量差来退出/增加线程
        剩下的修改queue_name, interval
    """
    tmp_jobs = job_thread_manager.threads.copy()
    config = []
    # 将config_dict转换格式为dicter = [{'queue':'q01', 'interval':6, }, ]
    for queue_name, values in config_dict.items():
        for value in values:
            dicter = dict( queue=queue_name )
            dicter.update(value)
            config.append(dicter)

    diff_job = len(config) - len(tmp_jobs)
    if diff_job > 0: # 需要增加线程
        for i in xrange(diff_job):
            conf = config.pop()
            job_thread_manager.add(conf['queue'], conf['interval'], conf.get('from_right', True))

    elif diff_job < 0: # 需要退出线程
        for key in tmp_jobs.keys():
            tmp_jobs.pop(key)
            job_thread_manager.stop(key)
            diff_job += 1
            if diff_job >= 0:
                break

    # 剩下的修改queue、interval、from_right, 如果有
    for index, job_thread in enumerate(tmp_jobs.values()):
        conf = config[index]
        job_thread.queue_name = conf['queue']
        job_thread.sleep_time = conf['interval']
        job_thread.from_right = conf.get('from_right', True)

def init_job_threads(config_dict, force=True):
    # 如果首次注册，根据配置启动工作线程，否则根据之前的配置启动。
    set_job_threads(config_dict)

    # 将一些信息补全，让监视界面认为这个worker已经启动
    alias = CONFIG['server']['alias']

    # set worker config
    worker_config = ztq_core.get_worker_config()
    if alias not in worker_config or force:
        worker_config[alias] = config_dict 

def set_dirve( from_mime, to_mime, conf):
    """ 根据驱动配置, 更改驱动参数 """
    #set_drive_config(from_mime, to_mime, conf)
    pass

def report(start_time):
    """ 转换器向服务器报告状态 """
    cpu_style = get_cpu_style()
    cpu_percent = get_cpu_usage() 
    mem_percent, mem_total = get_mem_usage()
    ip = CONFIG['server']['alias']

    traceback_dict = {}
    for thread_id, frame in sys._current_frames().items():
        traceback_dict[thread_id] = traceback.format_stack(frame)

    # 向服务器报告
    return dict( ip=ip,
            cpu_style=cpu_style, 
            cpu_percent=cpu_percent, 
            mem_total=mem_total, 
            mem_percent=mem_percent, 
            started=start_time, 
            timestamp=int(time.time()),
            traceback=traceback_dict,
            )

def kill_transform(pid, timestamp):
    """ 中止 转换 """
    kill(pid)

def cancel_transform(pid, timestamp):
    """ 取消 转换 """
    kill(pid)

if os.sys.platform != 'win':
    def kill(pid):
        """ kill process by pid for linux """
        # XXX 无法杀孙子进程
        kill_command = "kill -9 `ps --no-heading --ppid %s|awk '{print $1}'` %s" % (pid, pid)
        os.system(kill_command)
else:
    def kill(pid):
        """ kill process by pid for windows """
        kill_command = "taskkill /F /T /pid %s" % pid
        os.system(kill_command)

def start_buffer_thread(buffer_thread_config):
    """ 开启一个buffer队列线程，监视所有的buffer队列，
        根据buffer队列对应的job队列拥塞情况, 将buffer队列的任务合适的推送到相应的job队列
    """
    if not buffer_thread_config: return

    global buffer_thread_instance
    if buffer_thread_instance is not None:
        buffer_thread_instance.stop()

    buffer_thread = BufferThread(buffer_thread_config)
    buffer_thread.setDaemon(True)
    buffer_thread.start()

    buffer_thread_instance = buffer_thread
    sys.stdout.write('start a buffer thread. \n')

def clear_transform_thread(threads=None):
    """ clear job_threads and buffer_thread """
    threads = threads or job_thread_manager.threads
    names = threads.keys()
    job_threads = threads.values()

    # 退出buffer 线程
    if buffer_thread_instance is not None:
        buffer_thread_instance.stop()
        sys.stdout.write('wait the buffer thread stop...\n')

    # 将进程的stop 标志 设置为True
    map(job_thread_manager.stop, names)

    # 如果这个线程没有工作，只是在阻塞等待任务，就发送一个空的任务
    # 让这个线程立刻结束
    for job_thread in job_threads:
        if job_thread.start_job_time == 0:
            queue_name = job_thread.queue_name
            queue = ztq_core.get_task_queue(queue_name)
            queue.push('')

    # 等待线程退出
    for job_thread in job_threads:
        sys.stdout.write('wait the %s stop...\n'%job_thread.getName())
        job_thread.join(30)

import atexit
atexit.register(clear_transform_thread) # 系统退出后清理工作线程


########NEW FILE########
__FILENAME__ = command_thread
# -*- encoding: utf-8 -*-

from config_manager import CONFIG
from command_execute import report, kill_transform, cancel_transform, set_job_threads
from threading import Thread
import logging
import time
import ztq_core

logger = logging.getLogger("ztq_worker")

class CommandThread(Thread):
    """ 监视命令队列，取得命令, 执行命令"""

    def __init__(self, worker_name=''):
        super(CommandThread, self).__init__()
        self.login_time = int(time.time())
        self.worker_name = worker_name or CONFIG['server']['alias']

    def init(self):
        """ 开机初始化工作 """
        reboot = False
        worker_state = ztq_core.get_worker_state()
        if self.worker_name in worker_state:
            # 重启，读取服务器配置信息
            reboot = True
        # 记录系统日志
        system_log = ztq_core.get_system_log_queue()
        system_log.push(dict( host=CONFIG['server']['alias'],
                              alias=self.worker_name,
                              type=reboot and 'reboot' or 'power',
                              timestamp=self.login_time,))
        # 报告机器状态
        worker_state[self.worker_name] = report(self.login_time)

    def run(self):
        self.init()
        # 监听指令
        commands = ztq_core.get_command_queue(self.worker_name)
        while True:
            try:
                command = commands.pop()
                if command['command'] == 'report':
                    worker_state = ztq_core.get_worker_state()
                    worker_state[self.worker_name] = report(self.login_time)
                elif command['command'] == 'updatedriver':
                    # TODO
                    #async_drive_config()
                    pass
                elif command['command'] == 'updateworker':
                    queue = ztq_core.get_worker_config()
                    set_job_threads(queue[self.worker_name])
                elif command['command'] == 'kill':
                    kill_transform(pid=command['pid'], timestamp=command['timestamp'])
                elif command['command'] == 'cancel':
                    cancel_transform(pid=command['pid'], timestamp=command['timestamp'])
            except ztq_core.ConnectionError, e:
                logger.error('ERROR: redis command connection error: %s' % str(e))
                time.sleep(3)
            except ztq_core.ResponseError, e:
                logger.error('ERROR: redis command response error: %s' % str(e))
                time.sleep(3)

            except KeyboardInterrupt:
                import os
                # 实际上调用的是command_execute.clear_thread
                os.sys.exitfunc()
                os._exit(0)
            except Exception, e:
                logger.error('ERROR: redis command unknown error: %s' % str(e))
                time.sleep(3)

########NEW FILE########
__FILENAME__ = config_manager
# -*- encoding: utf-8 -*-

import os 

from ConfigParser import ConfigParser
from system_info import get_ip

# 读取配置文件（app.ini），保存到CONFIG中，实际使用的都是CONFIG
CONFIG = {'server':{'alias':get_ip()},
          'queues':{} }

def read_config_file(location=None):
    """ 初始化配置管理
    """
    cfg = ConfigParser()
    if location:
        cfg.read(location)
    else:
        local_dir = os.path.dirname(os.path.realpath(__file__))
        cfg.read( os.path.join(local_dir, 'config.cfg') )

    global CONFIG
    for section in cfg.sections():
        CONFIG[section] = {}
        for option in cfg.options(section):
            CONFIG[section][option] = cfg.get(section, option)
    return CONFIG


def register_batch_queue(queue_name, batch_size, batch_func=None):
    """ 注册队列是批处理模式
        queue_name: 指定哪个队列为批处理模式
        batch_size: 整形
        batch_func: 方法对象

        可以让队列在完成batch_size 后，执行一次 batch_func
    """
    CONFIG.setdefault('batch_queue', {}).update(
                {queue_name:{'batch_size':batch_size, 'batch_func':batch_func}})


########NEW FILE########
__FILENAME__ = job_thread
# -*- encoding: utf-8 -*-
import threading
import time, sys
import traceback
import logging

from config_manager import CONFIG
import ztq_core

thread_context = threading.local()
logger = logging.getLogger("ztq_worker")
QUEUE_TIMEOUT = 30

def report_job(pid=-1, comment='', **kw):
    """ 报告当前转换进程信息 """
    if not hasattr(thread_context, 'job'):
        return  # 如果不在线程中，不用报告了

    job = thread_context.job

    # 报告转换状态
    job['process'].update({'pid': pid,
                        'start':int(time.time()),
                        'comment':comment})
    if kw:
        job['process'].update(kw)

    # 写入状态
    job_state = ztq_core.get_job_state(job['runtime']['worker'])
    job_state[job['runtime']['thread']] = job

def report_progress(**kw):
    """ 报告当前转换进程信息 """
    if not hasattr(thread_context, 'job'):
        return  # 如果不在线程中，不用报告了

    job = thread_context.job

    if not 'progress_callback' in job: return
    # 报告转换进度
    progress_func  = ztq_core.task_registry[job['pcallback']]
    progress_args = job.get('pcallback_args', [])
    progress_kw  = job.get('pcallback_kw', {})
    progress_kw.update(kw)
    progress_func(*progress_args, **progress_kw)

class JobThread(threading.Thread):
    """ 监视一个原子队列，调用转换引擎取转换
        转换结果记录转换队列，转换出错需要记录出错日志与错误队列
    """
    def __init__(self, queue_name, sleep_time, from_right=True):
        super(JobThread, self).__init__()
        self.queue_name = queue_name
        self.sleep_time = sleep_time
        self.from_right = from_right # 读取服务器队列的方向，从左边还是右边
        # _stop 为 True 就会停止这个线程
        self._stop = False
        self.start_job_time = 0  #  记录任务开始时间

    def run(self):
        """ 阻塞方式找到任务，并自动调用"""
        # 如果上次有任务在运行还没结束，重新执行
        jobs = ztq_core.get_job_state(CONFIG['server']['alias'])
        if self.name in jobs:
            self.start_job(jobs[self.name])

        # 队列批处理模式
        # batch_size: 批处理的阀值，达到这个阀值，就执行一次batch_func
        # batch_func: 
        #    1, 执行一批batch_size 大小的任务后，后续自动执行这个方法方法
        #    2, 执行一批小于batch_size 大小的任务后，再得不到任务，后续自动执行这个方法
        batch_config = CONFIG.get("batch_queue", {}).get(self.queue_name, {})
        batch_size = batch_config.get('batch_size', None) or -1
        batch_func = batch_config.get('batch_func', None) or (lambda *args, **kw: -1)

        run_job_index = 0
        queue_tiemout = QUEUE_TIMEOUT
        # 循环执行任务
        while not self._stop:
            try:
                task = ztq_core.pop_task(
                        self.queue_name, 
                        timeout=queue_tiemout, 
                        from_right=self.from_right
                        )
            except ztq_core.ConnectionError, e:
                logger.error('ERROR: redis connection error: %s' % str(e))
                time.sleep(3)
                continue
            except ztq_core.ResponseError, e:
                logger.error('ERROR: redis response error: %s' % str(e))
                time.sleep(3)
                continue
            except Exception, e:
                logger.error('ERROR: redis unknown error: %s' % str(e))
                time.sleep(3)
                continue

            if task is None: 
                # 没有后续任务了。执行batch_func
                if run_job_index > 0:
                    run_job_index = 0
                    queue_tiemout = QUEUE_TIMEOUT
                    try:
                        batch_func()
                    except Exception, e:
                        logger.error('ERROR: batch execution error: %s' % str(e))
                continue

            try:
                self.start_job(task)
            except Exception, e:
                logger.error('ERROR: job start error: %s' % str(e))

            if batch_size > 0: 
                if run_job_index >= batch_size - 1:
                    # 完成了一批任务。执行batch_func
                    run_job_index = 0
                    queue_tiemout = QUEUE_TIMEOUT
                    try:
                        batch_func()
                    except Exception, e:
                        logger.error('ERROR: batch execution error: %s' % str(e))
                else:
                    run_job_index += 1
                    queue_tiemout = -1

            if self.sleep_time:
                time.sleep(self.sleep_time)

    def start_job(self, task):
        self.start_job_time = int(time.time())
        task['runtime'].update({'worker': CONFIG['server']['alias'],
                                'thread': self.getName(),
                                'start': self.start_job_time, })
        # 记录当前在做什么
        task['process'] = {'ident':self.ident}
        thread_context.job = task
        try:
            # started report
            report_job(comment='start the job')
            self.run_task = ztq_core.task_registry[task['func']]
            self.run_task(*task['args'], **task['kw'])

            task['runtime']['return'] = 0
            task['runtime']['reason'] = 'success'

            if task.get('callback', None):
                callback_args = task.get('callback_args', ())
                callback_kw = task.get('callback_kw', {})
                ztq_core.push_task(task['callback'], *callback_args, **callback_kw)

        except Exception, e:
            reason = traceback.format_exception(*sys.exc_info())
            # 将错误信息记录到服务器
            try:
                return_code = str(e.args[0]) if len(e.args) > 1 else 300
            except:
                return_code = 300
            task['runtime']['return'] = return_code
            task['runtime']['reason'] = reason[-11:]
            task['runtime']['end'] = int( time.time() )
            ztq_core.push_runtime_error(self.queue_name, task)
            # 错误回调
            if task.get('fcallback', None):
                callback_args = task.get('fcallback_args', ())
                callback_kw = task.get('fcallback_kw', {})
                callback_kw['return_code'] = return_code
                callback_kw['return_msg'] = unicode(reason[-1], 'utf-8', 'ignore')
                ztq_core.push_task(task['fcallback'], *callback_args, **callback_kw)
            # 在终端打印错误信息
            #reason.insert(0, str(datetime.datetime.today()) + '\n')
            logger.error(''.join(reason))

        # 任务结束，记录日志
        task['runtime']['end'] = int( time.time() )
        ztq_core.get_work_log_queue().push(task)
        # 删除服务器的转换进程状态信息
        job_state = ztq_core.get_job_state(task['runtime']['worker'])
        del job_state[task['runtime']['thread']]
        self.start_job_time = 0

    def stop(self):
        """ 结束这个进程，会等待当前转换完成
            请通过JobThreadManager 来完成工作线程的退出，不要直接使用这个方法
        """
        self._stop = True


########NEW FILE########
__FILENAME__ = job_thread_manager
# -*- coding: utf-8 -*-

from job_thread import JobThread
import sys

class JobThreadManager:
    """ 管理工作线程， 开启/停止工作线程 """
    # 保存工作线程的信息
    # threads = {'thread-1':<object JobThread>, 'thread-2':<object JobThread>}
    threads = {}

    def add(self, queue_name, sleep_time, from_right=True):
        """ 开启一个工作线程 """
        job_thread = JobThread(queue_name, sleep_time, from_right)
        job_thread.setDaemon(True)
        job_thread.start()
        self.threads[job_thread.getName()] = job_thread
        sys.stdout.write(
                'start a job thread, name: %s,'
                ' ident: %s,'
                ' queue_name: %s\n'
                % (job_thread.getName(), job_thread.ident, queue_name)
                )

    def stop(self, job_name):
        """ 安全的停止一个工作线程
            正在转换中的时候，会等待转换完成后自动退出
        """
        if not job_name in self.threads:
            return
        #sys.stdout.write('stop %s job thread\n'% job_name)
        job_thread = self.threads[job_name]
        job_thread.stop()
        del self.threads[job_name]

########NEW FILE########
__FILENAME__ = main
# -*- encoding: utf-8 -*-

import sys, os
from command_thread import CommandThread
from config_manager import read_config_file
from command_execute import init_job_threads, set_job_threads
from system_info import get_ip

import ztq_core

def run():
    conf_file = ''
    # 用户指定一个配置文件
    if len(sys.argv) > 1:
        conf_file = sys.argv[1]

    config = read_config_file(conf_file)
    main(config)

def main(config):
    """ 主函数 

    config: {'server': {host:, port:, db:}
            }
    """

    server = config['server']
    # 动态注册task
    for module in server['modules'].split():
        try:
            __import__(module)
        except ImportError:
            modules = module.split('.')
            __import__(modules[0], globals(), locals(), modules[1])

    # 连结服务器
    redis_host = server['host']
    redis_port = int(server['port'])
    redis_db = int(server['db'])
    ztq_core.setup_redis('default', host=redis_host, port=redis_port, db=redis_db)

    # 开启一个命令线程
    alias = server.get('alias', '')
    if not alias:
        alias = get_ip()
        server['alias'] = alias

    command_thread = CommandThread(worker_name=alias)

    sys.stdout.write('Starting server in PID %s\n'%os.getpid())

    worker_state = ztq_core.get_worker_state()
    active_config = server.get('active_config', 'false')
    if active_config.lower() == 'true' and command_thread.worker_name in worker_state:
        # 如果服务器有这个机器的配置信息，需要自动启动工作线程
        queue = ztq_core.get_worker_config()
        if command_thread.worker_name in queue:
            set_job_threads(queue[command_thread.worker_name])
    elif config['queues']:
        # 把worker监视队列的情况上报到服务器
        queue_config = ztq_core.get_queue_config()
        # 如果配置有queues，自动启动线程监视
        job_threads = {}
        for queue_name, sleeps in config['queues'].items():
            job_threads[queue_name] = [
                    {'interval': int(sleep)} for sleep in sleeps.split(',')
                    ]
            if not queue_config.get(queue_name, []):
                queue_config[queue_name] = {'name':queue_name, 'title':queue_name, 'widget': 5}

        init_job_threads(job_threads)

    loggers = config['log']
    initlog(
        loggers.get('key', 'ztq_worker'), 
        loggers.get('handler_file'), 
        loggers.get('level', 'ERROR'),
        )

    # 不是以线程启动
    command_thread.run()

def initlog(key, handler_file, level):
    import logging
    level = logging.getLevelName(level)
    format = '%(asctime)s %(message)s'
    if not handler_file:
        logging.basicConfig(level=level, format=format)
    else:
        logging.basicConfig(
                filename=handler_file, 
                filemode='a', 
                level=level, 
                format=format
                )

########NEW FILE########
__FILENAME__ = linux
#!/usr/bin/env python

from __future__ import with_statement 
import subprocess as sp

def get_cpu_usage():
    with open('/proc/stat') as cpu_info:
        result = cpu_info.readline()

    user, nice, system, idle = tuple(result.split()[1:5])
    user = int(user); nice = int(nice)
    system = int(system); idle = int(idle)
    cpu_usage = 1.0 * 100 * (user + nice + system) / (user + nice + system + idle)

    return '%.1f%%'%cpu_usage

def get_mem_usage():
    with open('/proc/meminfo') as mem_info:
        mem_total = mem_info.readline()
        mem_free = mem_info.readline()
        mem_buff = mem_info.readline()
        mem_cached  = mem_info.readline()

    mem_total = int(mem_total.split(':', 1)[1].split()[0])
    mem_free = int(mem_free.split(':', 1)[1].split()[0])
    mem_buff = int(mem_buff.split(':', 1)[1].split()[0])
    mem_cached = int(mem_cached.split(':', 1)[1].split()[0])

    mem_usage = mem_total - (mem_free + mem_buff + mem_cached)
    mem_usage = 1.0 * 100 * mem_usage / mem_total

    return ( '%.1f%%'%mem_usage, '%dM'%(mem_total/1024) ) 

_CPU_STYLE = None
def get_cpu_style():
    global _CPU_STYLE
    if _CPU_STYLE is None:
        popen = sp.Popen('cat /proc/cpuinfo  | grep "model name" | head -n 1', stdout=sp.PIPE, shell=True)
        popen.wait()
        result = popen.stdout.read()
        _CPU_STYLE = result.split(':', 1)[1].strip()
    return _CPU_STYLE

_IP_ADDRESS = None
def get_ip():
    def get_ip_address(ifname):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack('256s', ifname[:15])
        )[20:24])

    global _IP_ADDRESS
    if _IP_ADDRESS is None:
        import socket, fcntl, struct
        popen = sp.Popen("ifconfig -s | cut -d ' ' -f 1", stdout=sp.PIPE, shell=True)
        popen.wait()
        result = popen.stdout.read()
        for iface_name in result.split():
            if iface_name in ('Iface', 'lo'):
                continue
            try:
                _IP_ADDRESS = get_ip_address(iface_name)
            except:
                pass
            else:
                break
        if _IP_ADDRESS is None:
            _IP_ADDRESS = '127.0.0.1'

    return _IP_ADDRESS

if __name__ == '__main__':
    print 'cpu style: %s' % get_cpu_style()
    print 'cpu usage: %s' % get_cpu_usage()
    print 'memory usage: %s, memory total: %s' % get_mem_usage()
    print 'local ip addrs: %s'%get_ip()
    

########NEW FILE########
__FILENAME__ = win
#!/usr/bin/env python
import subprocess as sp
import urllib
from os import path

LOCAL_DIR = path.dirname(path.realpath(__file__))

def get_cpu_usage():
    vbs_file = 'get_cpu_usage.vbs'
    vbs_path = path.join(LOCAL_DIR, vbs_file)
    popen = sp.Popen('cscript /nologo %s'%vbs_path, stdout=sp.PIPE, shell=True)
    popen.wait()
    result = popen.stdout.read()
    return '%s%%'%result.strip()

def get_mem_usage():
    vbs_file = 'get_mem_usage.vbs'
    vbs_path = path.join(LOCAL_DIR, vbs_file)
    popen = sp.Popen('cscript /nologo %s'%vbs_path, stdout=sp.PIPE, shell=True)
    popen.wait()
    result = popen.stdout.read()
    mem_total, mem_usage, mem_percent = result.split()
    return ( '%s%%'%mem_percent, '%sM'%mem_total ) 

_CPU_STYLE = None
def get_cpu_style():
    global _CPU_STYLE
    if _CPU_STYLE is None:
        vbs_file = 'get_cpu_style.vbs'
        vbs_path = path.join(LOCAL_DIR, vbs_file)
        popen = sp.Popen('cscript /nologo %s'%vbs_path, stdout=sp.PIPE, shell=True)
        popen.wait()
        result = popen.stdout.read()
        cpu_style = '%s'%result.strip()

        try:
            cpu_style = cpu_style.decode('gb18030')
        except UnicodeDecodeError:
            cpu_style = cpu_style.decode('utf8')

        _CPU_STYLE = cpu_style.encode('utf8')
            
    return _CPU_STYLE

def get_ip():
    return urllib.thishost()

if __name__ == '__main__':
    print 'cpu style: %s' % get_cpu_style()
    print 'cpu usage: %s' % get_cpu_usage()
    print 'memory usage: %s, memory total: %s' % get_mem_usage()
    print 'local ip addrs: %s'%get_ip()

########NEW FILE########
