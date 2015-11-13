__FILENAME__ = log
# coding: utf-8
from os import path
import logging.config


def init_log(log_dir=None):
    if log_dir and not path.exists(log_dir):
        msg = u'指定路径不存在:%s' % log_dir
        print msg.encode('utf-8')
        log_dir = None

    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': '%(levelname)s %(asctime)s %(module)s:%(funcName)s:%(lineno)d %(message)s'
            },
            'simple': {
                'format': '%(level)s %(message)s'
            }
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'default',
            },
        },
        'loggers': {
            '': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': True,
            },
        }
    }

    if log_dir:
        config['handles']['file'] = {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': path.join(log_dir, 'essay.log'),
            'maxBytes': 1024 * 1024 * 50,
            'backupCount': 5,
            'formatter': 'default',
        }
        config['loggers']['handlers'] = ['console', 'file']

    logging.config.dictConfig(config)

########NEW FILE########
__FILENAME__ = main
# coding:utf-8

import re
import sys
import pip
from optparse import OptionParser
from fabric.state import env

from essay.project import create_project, init_project

usage = """es usage: es create/init [project_name]
    Commands available:
        create: create project with full structure
        pinstall: this command help you install package from our pypi server
        and other PIP support command
    """


def init_options():
    parser = OptionParser(usage=usage)

    parser.add_option("-t", "--template", dest="template", default="default",
                      help="project template:[default],[django]")

    return parser.parse_args()


def main():
    help_text = usage

    if len(sys.argv) == 2 and sys.argv[1] == 'init':
        init_project(None, 'init')
    elif len(sys.argv) >= 2 and sys.argv[1] == 'create':
        options, args = init_options()
        project_name = sys.argv[2]
        if re.match('^[a-zA-Z0-9_]+$', project_name):
            create_project(project_name, options.template)
        else:
            print u'无效工程名: ' + project_name
    elif len(sys.argv) >= 2 and sys.argv[1] == 'init':
        options, args = init_options()
        project_name = sys.argv[2]
        if re.match('^[a-zA-Z0-9_]+$', project_name):
            init_project(project_name, options.template)
        else:
            print u'无效工程名: ' + project_name
    elif len(sys.argv) >= 2 and sys.argv[1] == 'pinstall':
        if len(sys.argv) == 2 or sys.argv[2] == '-h':
            print "es pinstall <package>"
            return

        args = sys.argv[1:]
        args[0] = 'install'
        args.append('-i %s' % env.PYPI_INDEX)
        pip.main(args)
    else:
        if len(sys.argv) == 2 and '-h' in sys.argv:
            print help_text
        pip.main()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = pip_
# coding: utf-8
import os
from fabric.state import env


def install(args):
    cmd = 'pip install -i=%s %s' % (env.PYPI_INDEX, ' '.join(args))
    os.system(cmd)


def default(args):
    cmd = 'pip ' + ' '.join(args)
    os.system(cmd)

########NEW FILE########
__FILENAME__ = project
# coding: utf-8

"""
创建新工程结构
"""

import os
import string
import logging
from os import path

from fabric.api import lcd
from fabric.operations import prompt

from essay import settings
from essay.tasks import fs
from essay.tasks import git

logger = logging.getLogger(__name__)


def create_project(project, template='default'):
    """创建本地工程"""
    init_project(project, template)
    with lcd(project):
        git.command('git init', in_local=True)
        git.add(add_all=True, in_local=True)
        git.commit(u'初始化工程结构', in_local=True)
        repos = prompt('请输入Git仓库地址:')
        if repos:
            git.command('git remote add origin %s' % repos, in_local=True)
            git.command('git push -u origin master', in_local=True)


def init_project(project, template='default'):
    """初始化本地项目

    此方法不需要连接git服务器
    """
    if project is None:
        project_dir = path.abspath('.') 
        template = 'init'
        project = ''
        params = {
            'project_name': project
        }
    else:
        project_dir = path.abspath(project)
        fs.ensure_dir(project, in_local=True)

        params = {
            'project_name': project
        }

    build_structure(project, project_dir, params, template)


def build_structure(project, dst, params, template='default'):
    """
        拷贝工程打包及fab文件到工程
    """
    dst = dst.rstrip('/')

    template_dir = path.join(settings.PROJECT_ROOT, 'templates', template)
    for root, dirs, files in os.walk(template_dir):
        for name in files:
            if name.endswith('.tpl'):
                src = path.join(root, name)
                dst_filename = src.replace(template_dir, dst).rstrip('.tpl').replace('__project__', project)
                dst_dir = os.path.dirname(dst_filename)

                fs.ensure_dir(dst_dir, in_local=True)

                content = open(src).read().decode('utf-8')
                if not name.endswith('.conf.tpl'):
                    content = string.Template(content).safe_substitute(**params)

                open(dst_filename, 'w').write(content.encode('utf-8'))

########NEW FILE########
__FILENAME__ = settings
# coding:utf-8

__version__ = '${version}'
__git_version__ = '${git_version}'
__release_time__ = '${release_time}'

import os
from log import init_log
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

init_log()

########NEW FILE########
__FILENAME__ = build
#!/usr/bin/env python
# encoding: utf-8

import os
import re
import datetime

from fabric.state import env
from fabric.api import cd, run, task, settings, roles

from essay.tasks import git, config, fs
from fabric.contrib import files
from pip.exceptions import DistributionNotFound

__all__ = ['build', 'get_latest_version', 'get_next_version']


@roles('build')  # 默认使用build role
@task(default=True)
def build(name=None, version=None, commit=None, branch=None):
    """
    打包

    参数:
        name: 描述, 如:seo。最后生成project_name-x.x.x.x-seo.tar.gz
        commit: 指定commit版本
        branch: 分支名称
        version: 自定义版本号，如果为None则根据日期生成

    commit和branch必须提供一个, 或者读取配置文件
    """

    if commit:
        check_out = commit
    elif branch:
        check_out = branch
    else:
        check_out = env.DEFAULT_BRANCH

    if not version:
        config.check('PROJECT')
        version = get_next_version(env.PROJECT)

    if name:
        version = '%s-%s' % (version, name)

    project_path = os.path.join(env.BUILD_PATH, env.PROJECT)

    if not files.exists(project_path):
        with(cd(env.BUILD_PATH)):
            git.clone('/'.join([env.PROJECT_OWNER, env.PROJECT]))

    with(cd(project_path)):
        git.checkout(check_out)
        # 在setup打包之前做进一步数据准备工作的hook
        if hasattr(env, 'PRE_BUILD_HOOK'):
            env.PRE_BUILD_HOOK()

        params = {
            'release_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'git_version': git.get_version(),
            'version': version,
        }

        fs.inplace_render(os.path.join(project_path, 'setup.py'), params)

        if hasattr(env, 'SETTINGS_BASE_FILE'):
            settings_file_path = os.path.join(project_path, *env.SETTINGS_BASE_FILE.split('/'))
            if files.exists(settings_file_path):
                fs.inplace_render(settings_file_path, params)
        else:
            settings_file_path = os.path.join(project_path, env.PROJECT, 'settings.py')
            if files.exists(settings_file_path):
                fs.inplace_render(settings_file_path, params)

            settings_dir_path = os.path.join(project_path, env.PROJECT, 'settings', '__init__.py')
            if files.exists(settings_dir_path):
                fs.inplace_render(settings_dir_path, params)

        run("python setup.py sdist upload -r internal")

@task
def get_latest_version(package_name=None):
    if not package_name:
        config.check('PROJECT')
        package_name = env.PROJECT

    # 这里直接使用了package finder，而非search command,
    # 是因为pypiserver不支持pip search
    from pip.index import PackageFinder
    from pip.req import InstallRequirement
    finder = PackageFinder(find_links=[], index_urls=[env.PYPI_INDEX])
    req = InstallRequirement(req=package_name, comes_from=None)
    try:
        url = finder.find_requirement(req, upgrade=True)
    except DistributionNotFound:
        print u'尚无任何版本！'
        return None
    filename = url.splitext()[0]
    version = re.search(r'(\d+\.?)+', filename)
    version = version.group() if version else None

    print u'当前版本: %s' % version
    return version

@task
def get_next_version(package_name=None):
    """计算下一个版本号"""

    if not package_name:
        config.check('PROJECT')
        package_name = env.PROJECT

    now = datetime.datetime.now()
    prefix = '%s.%s.%s' % (str(now.year)[-1], now.month, now.day)

    latest_version = get_latest_version(package_name)
    #如果该项目没有建立过版本,从1开始
    if not latest_version:
        index = 1
    else:
        last_prefix, last_index = latest_version.rsplit('.', 1)

        if last_prefix != prefix:
            index = 1
        else:
            index = int(last_index) + 1

    version = prefix + '.' + str(index)
    print u'下一个版本: ' + version

    return version

########NEW FILE########
__FILENAME__ = config
# coding: utf-8
from os import path

from fabric.api import task
from fabric.state import env
from fabric.contrib import files


def check(*properties):
    def _check(_property):
        if not hasattr(env, _property):
            msg = u'env没有%s属性' % _property
            print msg
            raise Exception(msg)

    for property in properties:
        _check(property)


@task(default=True)
def upload_conf(**context):
    if hasattr(env, 'LOCAL_SERVER_CONF'):
        for local_conf, server_conf in env.LOCAL_SERVER_CONF:
            template_dir, filename = path.dirname(local_conf), path.basename(local_conf)
            venv_dir = env.CURRENT_VIRTUAL_ENV_DIR
            destination = path.join(venv_dir, server_conf)

            files.upload_template(filename, destination, context=context, use_jinja=True, template_dir=template_dir)
    else:
        print 'no local conf to upload'

########NEW FILE########
__FILENAME__ = deploy
# coding: utf-8

from fabric.api import parallel, task
from fabric.state import env

from essay.tasks import virtualenv, supervisor, package, build

__all__ = ['deploy', 'quickdeploy']


@task(default=True)
@parallel(30)
def deploy(version, venv_dir, profile):
    """
    发布指定的版本

    会自动安装项目运行所需要的包
    """

    if not version:
        version = build.get_latest_version()

    virtualenv.ensure(venv_dir)

    with virtualenv.activate(venv_dir):
        supervisor.ensure(project=env.PROJECT, profile=profile)
        package.install(env.PROJECT, version)
        supervisor.shutdown()
        supervisor.start()


@task(default=True)
def quickdeploy(venv_dir, profile, branch=None):
    """
    快速部署

        $ fab -R yourroles quickdeploy:a,test,master
    """

    deploy_host_string = env.host_string

    build_host = env.roledefs.get('build')
    env.host_string = build_host[0] if isinstance(build_host, list) else build_host
    build.build(branch=branch)

    env.host_string = deploy_host_string
    version = build.get_latest_version()

    deploy(version, venv_dir, profile)

########NEW FILE########
__FILENAME__ = fs
# coding: utf-8

import os
from os import path
from fabric.contrib import files
from fabric.decorators import task
from fabric.operations import run, local

__all__ = ['rm_by_pattern']

KERNEL_NAME = os.uname()[0].lower()


def ensure_dir(dir, in_local=False):
    """确保指定的dir被创建"""

    if in_local:
        if not path.isdir(dir):
            local("mkdir -p " + dir)
    elif not files.exists(dir):
        run("mkdir -p " + dir)


def remove_dir(dir, in_local=False):
    """删除指定的文件夹"""

    if in_local:
        if not path.isdir(dir):
            local("rm -r " + dir)
    elif not files.exists(dir):
        run("rm -r " + dir)


@task
def rm_by_pattern(directory, pattern, in_local=False):
    """
    删除指定格式的文件

    参数:
        directory: 目录
        pattern: 格式
        in_local: 在本地执行（默认）

    示例:
        fab fs.rm_by_pattern:.,.pyc,True
    """

    if in_local:
        local('find %s |grep %s | xargs rm -rf' % (directory, pattern))
    else:
        run('find %s |grep %s | xargs rm -rf' % (directory, pattern))


def inplace_render(filename, params):
    for key, value in params.items():
        files.sed(filename, '\$\{%s\}' % key, value)

########NEW FILE########
__FILENAME__ = git
# coding: utf-8
import logging
from fabric.state import env
from fabric.context_managers import lcd, cd
from fabric.operations import local, run

logger = logging.getLogger(__name__)


def command(cmd, in_local=False, git_path=None):
    cmd = cmd.encode('utf-8')
    print cmd, '###'

    if in_local:
        if git_path:
            with lcd(git_path):
                return local(cmd)
        else:
            return local(cmd)
    else:
        if git_path:
            with cd(git_path):
                return run(cmd)
        else:
            return run(cmd)

def clone(project_name, in_local=False, git_path=None):
    """
        把项目clone到本地
    """

    if env.GIT_SERVER.startswith('http'):
        cmd = 'git clone %s/%s' % (env.GIT_SERVER, project_name)
    else:
        cmd = 'git clone git@%s:%s' % (env.GIT_SERVER, project_name)
    command(cmd, in_local, git_path)


def reset(in_local=False, git_path=None):
    """
        把项目lone到本地
    """
    cmd = 'git reset --hard'
    command(cmd, in_local, git_path)


def push(branch=None, in_local=False, git_path=None):
    """
        把项目lone到本地
    """
    cmd = 'git push'
    if branch:
        cmd += ' origin ' + branch
    command(cmd, in_local, git_path)


def pull(in_local=False, git_path=None):
    """
        把项目lone到本地
    """
    cmd = 'git pull'

    command(cmd, in_local, git_path)


def add(files=None, add_all=False, in_local=False, git_path=None):
    if not files and not add_all:
        raise Exception(u'无效参数')

    if add_all:
        cmd = 'git add .'
    else:
        if not isinstance(files, (tuple, list)):
            files = [files]
        cmd = 'git add ' + ' '.join(files)
    command(cmd, in_local, git_path)


def commit(msg, in_local=False, git_path=None):
    """
        把项目lone到本地
    """
    cmd = u'git commit -a -m "%s"' % msg
    command(cmd, in_local, git_path)


def checkout(commit_or_branch, in_local=False, git_path=None):
    """
        根据commit回滚代码或者获取分支的所有代码

        commit据有优先权
    """

    cmd = 'git reset --hard && git pull && git checkout %s && git pull && git submodule update --init --recursive' % commit_or_branch
    command(cmd, in_local, git_path)


def get_version(in_local=False, git_path=None):
    cmd = "git rev-parse HEAD"
    return command(cmd, in_local, git_path)

########NEW FILE########
__FILENAME__ = nginx
#!/usr/bin/env python
# encoding: utf-8

from fabric.api import run, env, sudo, settings
from fabric.contrib import files
from fabric.decorators import task
from essay.tasks import config, fs


def _nginx_command(command, nginx_bin=None, nginx_conf=None, use_sudo=False):
    if not nginx_bin:
        config.check('NGINX_BIN')
        nginx_bin = env.NGINX_BIN

    if not nginx_conf:
        config.check('NGINX_CONF')
        nginx_conf = env.NGINX_CONF

    if command == 'start':
        cmd = '%(nginx_bin)s -c %(nginx_conf)s' % locals()
    else:
        cmd = '%(nginx_bin)s -c %(nginx_conf)s -s %(command)s' % locals()

    if use_sudo:
        sudo(cmd)
    else:
        run(cmd)

@task
def stop(nginx_bin=None, nginx_conf=None, use_sudo=False):
    """
    停止Nginx

    参数:
        nginx_bin: nginx可执行文件路径，如果为提供则从env获取。
        nginx_conf: nginx配置文件路径，如果为提供则从env获取。
    """

    _nginx_command('stop', nginx_bin, nginx_conf, use_sudo=use_sudo)


@task
def start(nginx_bin=None, nginx_conf=None, use_sudo=False):
    """
    启动Nginx

    参数:
        nginx_bin: nginx可执行文件路径，如果为提供则从env获取。
        nginx_conf: nginx配置文件路径，如果为提供则从env获取。
    """

    _nginx_command('start', nginx_bin, nginx_conf, use_sudo=use_sudo)


@task
def reload(nginx_bin=None, nginx_conf=None, use_sudo=False):
    """
    重启Nginx

    参数:
        nginx_bin: nginx可执行文件路径，如果为提供则从env获取。
        nginx_conf: nginx配置文件路径，如果为提供则从env获取。
    """
    _nginx_command('reload', nginx_bin, nginx_conf, use_sudo=use_sudo)


@task
def switch(src_pattern, dst_pattern, root=None, nginx_bin=None, nginx_conf=None):
    """
    修改配置文件并重启：源文本,目标文本,[root]（使用root)

    主要用于AB环境的切换，将配置文件中的src_pattern修改为dst_pattern，并重启。

    参数:
        src_pattern: 源模式，如upstreamA
        src_pattern: 目标模式，如upstreamB
        nginx_bin: nginx可执行文件路径，如果为提供则从env获取。
        nginx_conf: nginx配置文件路径，如果为提供则从env获取。
    """

    if not nginx_conf:
        config.check('NGINX_CONF')
        nginx_conf = env.NGINX_CONF

    use_sudo = (root=='root')
    files.sed(nginx_conf, src_pattern, dst_pattern, use_sudo=use_sudo)
    reload(nginx_bin, nginx_conf, use_sudo=use_sudo)

########NEW FILE########
__FILENAME__ = package
# coding: utf-8

import shutil
import tempfile
from essay.tasks.fs import ensure_dir, remove_dir

from fabric.api import cd, run, env
from fabric.context_managers import hide, settings
from fabric.contrib.files import exists
from fabric.decorators import task

__all__ = ['install']


def is_virtualenv_installed_in_system():
    """
    检查virtualenv是否在系统目录安装
    """

    with settings(warn_only=True):
        return 'no virtualenv' not in run('which virtualenv') or \
            'which' not in run('which virtualenv')


def is_virtualenv_installed_in_user():
    """
    检查virtualenv是否在系统目录安装
    """

    with settings(warn_only=True):
        return exists('~/.local/bin/virtualenv')


def is_virtualenv_installed():
    """
    检查virtualenv是否已安装
    """

    return is_virtualenv_installed_in_system() or is_virtualenv_installed_in_user()


def is_installed(package):
    """检查Python包是否被安装

    注意：只能在虚拟Python环境中执行
    """

    if not 'CURRENT_VIRTUAL_ENV_DIR' in env:
        raise Exception(u'只可以在虚拟环境安装Python包')
    venv_dir = env.CURRENT_VIRTUAL_ENV_DIR

    with settings(warn_only=True):
        res = run('%(venv_dir)s/bin/pip freeze' % locals())
    packages = [line.split('==')[0].lower() for line in res.splitlines()]

    return package.lower() in packages


@task
def install(package_name, version=None, private=True, user_mode=True):
    """
    用Pip安装Python包

    参数:
        package: 包名，可以指定版本，如Fabric==1.4.3
        private: 利用私有PYPI安装
        user_mode: 安装在用户目录

    注意：只能在虚拟Python环境中执行
    """

    if not 'CURRENT_VIRTUAL_ENV_DIR' in env:
        raise Exception(u'只可以在虚拟环境安装Python包')

    venv_dir = env.CURRENT_VIRTUAL_ENV_DIR

    options = []

    if hasattr(env, 'HTTP_PROXY'):
        options.append('--proxy=' + env.HTTP_PROXY)

    if private:
        options.append('-i ' + env.PYPI_INDEX)

    options_str = ' '.join(options)
    if version:
        package_name += '==' + version

    command = '%(venv_dir)s/bin/pip install %(options_str)s %(package_name)s' % locals()

    run(command)


def ensure(package, private=True, user_mode=True):
    """检查Python包有没有被安装，如果没有则安装

    注意：只能在虚拟Python环境中执行
    """

    if not is_installed(package):
        install(package, private=private, user_mode=user_mode)


def uninstall(package):
    """卸载Python包

    注意：只能在虚拟Python环境中执行
    """

    if not 'CURRENT_VIRTUAL_ENV_DIR' in env:
        raise Exception(u'只可以在虚拟环境安装Python包')

    venv_dir = env.CURRENT_VIRTUAL_ENV_DIR
    run("%(venv_dir)s/bin/pip uninstall -y %(package)s" % locals())

########NEW FILE########
__FILENAME__ = process
# coding:utf-8
from fabric.api import run
from fabric.context_managers import settings, hide
from fabric.decorators import task


@task
def kill_by_name(name):
    """
    停止指定特征的进程
    """

    with settings(warn_only=True):
        run("ps aux | grep '%s' | grep -v 'grep' | awk '{print $2}' | xargs kill -9" % name)


@task
def top():
    """
    查看系统负载
    """

    run("top -b | head -n 1")


@task
def ps_by_venv(venv_dir):
    """"
    查看指定虚拟环境的进程CPU占用
    """

    with hide('status', 'running', 'stderr'):
        run("""ps aux | grep -v grep | grep -v supervisor | grep %s | awk '{print $3, "|", $4}'""" % venv_dir)

########NEW FILE########
__FILENAME__ = pypi
# coding: utf-8
from fabric.api import run, env, task
from fabric.context_managers import settings
import os
from essay.tasks import config, fs

__all__ = ['sync']


@task
def sync(*packages):
    """从http://pypi.python.org同步包

    用法:
        fab pypi.sync:django==1.3,tornado
    """

    config.check('PYPI_HOST',
                 'PYPI_USER',
                 'PYPI_ROOT')

    with settings(host_string=env.PYPI_HOST, user=env.PYPI_USER):
        cmd = ["pip", "-q", "install", "--no-deps", "-i", "https://pypi.python.org/simple",
               "-d", env.PYPI_ROOT,
               ' '.join(packages)]

        run(" ".join(cmd))
########NEW FILE########
__FILENAME__ = supervisor
# coding:utf-8

from os import path

from fabric.api import run, settings
from fabric.context_managers import cd
from fabric.contrib import files
from fabric.decorators import task
from fabric.state import env

from essay.tasks import config, util, virtualenv, package, fs

__all__ = ['start_process', 'stop_process', 'restart_process', 'reload']


def ensure(**context):
    if not 'CURRENT_VIRTUAL_ENV_DIR' in env:
        raise Exception(u'只可以在虚拟环境安装Python包')
    venv_dir = env.CURRENT_VIRTUAL_ENV_DIR

    package.ensure('supervisor')

    context.setdefault('run_root', venv_dir)
    context.setdefault('username', util.random_str(10))
    context.setdefault('password', util.random_str(20, True))
    context.setdefault('process_count', 2)
    context.setdefault('venv_dir', venv_dir)
    context.setdefault('virtualenv_name', venv_dir[-1:])
    if 'VENV_PORT_PREFIX_MAP' in env and isinstance(env.VENV_PORT_PREFIX_MAP, dict):
        try:
            context.setdefault('port', env.VENV_PORT_PREFIX_MAP[venv_dir[-1:]])
        except KeyError:
            raise Exception(u'你的端口配置VENV_DIR_PORT_MAP中key[%s]不存在!' % venv_dir[-1:])
    if 'PROCESS_COUNT' in env:
        context.setdefault('process_count', env.PROCESS_COUNT)
    config.check('SUPERVISOR_CONF_TEMPLATE')
    config_template = env.SUPERVISOR_CONF_TEMPLATE
    destination = path.join(venv_dir, 'etc', 'supervisord.conf')

    template_dir, filename = path.dirname(config_template), path.basename(config_template)

    files.upload_template(filename, destination, context=context, use_jinja=True, template_dir=template_dir)


def _supervisor_command(command, venv_dir=None):
    if venv_dir:
        with virtualenv.activate(venv_dir):
            _supervisor_command(command)

    if not 'CURRENT_VIRTUAL_ENV_DIR' in env:
        raise Exception(u'只可以在虚拟环境安装Python包')

    venv_dir = env.CURRENT_VIRTUAL_ENV_DIR

    # 停止supervisor管理的进程
    with settings(warn_only=True), cd(venv_dir):
        run('bin/supervisorctl -c etc/supervisord.conf ' + command)


@task
def start(venv_dir=None):
    """重启指定虚拟环境的supervisor"""

    if venv_dir:
        with virtualenv.activate(venv_dir):
            start()

    if not 'CURRENT_VIRTUAL_ENV_DIR' in env:
        raise Exception(u'只可以在虚拟环境安装Python包')

    venv_dir = env.CURRENT_VIRTUAL_ENV_DIR

    with settings(warn_only=True), cd(venv_dir):
        # 停止supervisor管理的进程
        run('bin/supervisord -c etc/supervisord.conf ')


@task
def shutdown(venv_dir=None):
    """重启指定虚拟环境的supervisor"""

    _supervisor_command('shutdown', venv_dir)


@task
def reload(venv_dir=None):
    """重启指定虚拟环境的supervisor"""

    _supervisor_command('reload', venv_dir)


@task
def start_process(name, venv_dir=None):
    """
    启动进程
    """

    _supervisor_command(' start ' + name, venv_dir)


@task
def stop_process(name, venv_dir=None):
    """
    关闭进程
    """

    _supervisor_command(' stop ' + name, venv_dir)


@task
def restart_process(name, venv_dir=None):
    """
    重启进程
    """

    _supervisor_command(' restart ' + name, venv_dir)

########NEW FILE########
__FILENAME__ = util
#!/usr/bin/env python
# encoding: utf-8

import random
import string

from fabric.decorators import task

__all__ = ['random_str']

KEYS = [string.lowercase,
        string.uppercase,
        string.digits,
        string.punctuation]


@task
def random_str(length=10, level=1):
    """
    生成随机字符串

    参数:
        length: 字符串长度
        level: 使用的字符集
            1 -> abcdefghijklmnopqrstuvwxyz
            2 -> abcdefghijklmnopqrstuvwxyz + ABCDEFGHIJKLMNOPQRSTUVWXYZ
            3 -> abcdefghijklmnopqrstuvwxyz + ABCDEFGHIJKLMNOPQRSTUVWXYZ + 0123456789
            4 -> abcdefghijklmnopqrstuvwxyz + ABCDEFGHIJKLMNOPQRSTUVWXYZ + 0123456789 + !"#$%&'()*+,-./:;<=>?@[\]^_`{|}~
    """

    if length < 1 or 4 < level < 1:
        raise ValueError(u'无效参数')

    level = int(level) + 1
    keys = ''.join(KEYS[:level])

    result = ''.join([random.choice(keys) for i in range(length)])

    print result

    return result

########NEW FILE########
__FILENAME__ = virtualenv
# coding:utf-8

import posixpath
from os import path
from contextlib import contextmanager

from fabric.state import env
from fabric.api import run, prompt
from fabric.contrib.files import exists
from fabric.context_managers import prefix

from essay.tasks import process, package, fs

__all__ = []


def ensure(venv_dir, sub_dirs=None, user_mode=True):
    """
    确保虚拟环境存在

    ::
    .. _virtual environment: http://www.virtualenv.org/
    """

    if not venv_dir.startswith('/'):
        if 'VIRTUALENV_PREFIX' in env:
            venv_dir = path.join(env.VIRTUALENV_PREFIX, venv_dir)
        else:
            user_home = run('USER_HOME=$(eval echo ~${SUDO_USER}) && echo ${USER_HOME}')
            venv_dir = path.join(user_home, 'w', venv_dir)

    if is_virtualenv(venv_dir):
        return

    if package.is_virtualenv_installed_in_system():
        virtualenv_bin = 'virtualenv'
    else:
        virtualenv_bin = '~/.local/bin/virtualenv'

    command = '%(virtualenv_bin)s --quiet "%(venv_dir)s"' % locals()
    run(command)

    if not sub_dirs:
        sub_dirs = ['logs', 'etc', 'tmp']

    if 'VIRTUALENV_SUB_DIRS' in env:
        sub_dirs = list(set(sub_dirs + env.VIRTUALENV_SUB_DIRS))

    for sub_dir in sub_dirs:
        fs.ensure_dir(path.join(venv_dir, sub_dir))


@contextmanager
def activate(venv_dir, local=False):
    """
    用来启用VirtualEnv的上下文管理器

    ::
        with virtualenv('/path/to/virtualenv'):
            run('python -V')

    .. _virtual environment: http://www.virtualenv.org/
    """

    if not venv_dir.startswith('/'):
        if 'VIRTUALENV_PREFIX' in env:
            venv_dir = path.join(env.VIRTUALENV_PREFIX, venv_dir)
        else:
            user_home = run('USER_HOME=$(eval echo ~${SUDO_USER}) && echo ${USER_HOME}')
            venv_dir = path.join(user_home, 'w', venv_dir)

    if not is_virtualenv(venv_dir):
        raise Exception(u'无效虚拟环境: %s' % venv_dir)

    join = path.join if local else posixpath.join
    with prefix('. "%s"' % join(venv_dir, 'bin', 'activate')):
        env.CURRENT_VIRTUAL_ENV_DIR = venv_dir
        yield
        # del env['CURRENT_VIRTUAL_ENV_DIR']


def is_virtualenv(venv_dir):
    """判断指定的虚拟环境是否正确"""
    return exists(path.join(venv_dir, 'bin', 'activate'))


def remove(venv_dir):
    """删除指定的虚拟环境"""

    answer = prompt(u"确定删除虚拟环境:%s  (y/n)?" % venv_dir)
    if answer.lower() in ['y', 'yes']:
        if is_virtualenv(venv_dir):
            process.kill_by_name(path.join(venv_dir, 'bin'))
            run('rm -rf ' + venv_dir)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# essay documentation build configuration file, created by
# sphinx-quickstart on Tue Sep 25 00:13:50 2012.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('../..'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest', 'sphinx.ext.ifconfig', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'essay'
copyright = u'2012, SOHU MPC'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '2.0.0.0'
# The full version, including alpha/beta/rc tags.
release = '2.0.0.0'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = []

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'essaydoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'essay.tex', u'essay Documentation',
   u'SOHU MPC', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'essay', u'essay Documentation',
     [u'SOHU MPC'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'essay', u'essay Documentation',
   u'SOHU MPC', 'essay', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'


# -- Options for Epub output ---------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = u'essay'
epub_author = u'SOHU MPC'
epub_publisher = u'SOHU MPC'
epub_copyright = u'2012, SOHU MPC'

# The language of the text. It defaults to the language option
# or en if the language is not set.
#epub_language = ''

# The scheme of the identifier. Typical schemes are ISBN or URL.
#epub_scheme = ''

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
#epub_identifier = ''

# A unique identification for the text.
#epub_uid = ''

# A tuple containing the cover image and cover page html template filenames.
#epub_cover = ()

# HTML files that should be inserted before the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_pre_files = []

# HTML files shat should be inserted after the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_post_files = []

# A list of files that should not be packed into the epub file.
#epub_exclude_files = []

# The depth of the table of contents in toc.ncx.
#epub_tocdepth = 3

# Allow duplicate toc entries.
#epub_tocdup = True

########NEW FILE########
