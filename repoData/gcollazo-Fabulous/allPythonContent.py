__FILENAME__ = cookbook
# cookbook.py
# This file describes the packages to install and how to set them up.
# 
# Ingredients: nginx, memecached, gunicorn, supervisord, virtualenv, git

recipe = [
  # First command as regular user
  {"action":"run", "params":"whoami"},

  # sudo apt-get update
  {"action":"sudo", "params":"apt-get update -qq",
    "message":"Updating apt-get"},
  
  # List of APT packages to install
  {"action":"apt",
    "params":["mysql-client", "libmysqlclient-dev", "nginx", "memcached", "git",
      "python-setuptools", "python-dev", "build-essential", "python-pip", "python-mysqldb"],
    "message":"Installing apt-get packages"},
  
  # List of pypi packages to install
  {"action":"pip", "params":["virtualenv", "virtualenvwrapper","supervisor"],
    "message":"Installing pip packages"},

  # nginx
  {"action":"put", "params":{"file":"%(FABULOUS_PATH)s/templates/nginx.conf",
    "destination":"/home/%(SERVER_USERNAME)s/nginx.conf"},
    "message":"Configuring nginx"},
  {"action":"sudo", "params":"mv /etc/nginx/nginx.conf /etc/nginx/nginx.conf.old"},
  {"action":"sudo", "params":"mv /home/%(SERVER_USERNAME)s/nginx.conf /etc/nginx/nginx.conf"},
  {"action":"sudo", "params":"chown root:root /etc/nginx/nginx.conf"},
  {"action":"put_template", "params":{"template":"%(FABULOUS_PATH)s/templates/nginx-app-proxy",
                                      "destination":"/home/%(SERVER_USERNAME)s/%(PROJECT_NAME)s"}},
  {"action":"sudo", "params":"rm -rf /etc/nginx/sites-enabled/default"},
  {"action":"sudo", "params":"mv /home/%(SERVER_USERNAME)s/%(PROJECT_NAME)s /etc/nginx/sites-available/%(PROJECT_NAME)s"},
  {"action":"sudo", "params":"ln -s /etc/nginx/sites-available/%(PROJECT_NAME)s /etc/nginx/sites-enabled/%(PROJECT_NAME)s"},
  {"action":"sudo", "params":"chown root:root /etc/nginx/sites-available/%(PROJECT_NAME)s"},
  {"action":"sudo", "params":"/etc/init.d/nginx restart", "message":"Restarting nginx"},
  
  # virtualenvwrapper
  {"action":"sudo", "params":"mkdir %(VIRTUALENV_DIR)s", "message":"Configuring virtualenvwrapper"},
  {"action":"sudo", "params":"chown -R %(SERVER_USERNAME)s: %(VIRTUALENV_DIR)s"},
  {"action":"run", "params":"echo 'export WORKON_HOME=%(VIRTUALENV_DIR)s' >> /home/%(SERVER_USERNAME)s/.profile"},
  {"action":"run", "params":"echo 'source /usr/local/bin/virtualenvwrapper.sh' >> /home/%(SERVER_USERNAME)s/.profile"},
  {"action":"run", "params":"source /home/%(SERVER_USERNAME)s/.profile"},
  
  # webapps alias
  {"action":"run", "params":"""echo "alias webapps='cd %(APPS_DIR)s'" >> /home/%(SERVER_USERNAME)s/.profile""",
    "message":"Creating webapps alias"},
  
  # webapps dir
  {"action":"sudo", "params":"mkdir %(APPS_DIR)s", "message":"Creating webapps directory"},
  {"action":"sudo", "params":"chown -R %(SERVER_USERNAME)s: %(APPS_DIR)s"},
  
  # git setup
  {"action":"run", "params":"git config --global user.name '%(GIT_USERNAME)s'",
    "message":"Configuring git"},
  {"action":"run", "params":"git config --global user.email '%(ADMIN_EMAIL)s'"},
  {"action":"put", "params":{"file":"%(GITHUB_DEPLOY_KEY_PATH)s",
                            "destination":"/home/%(SERVER_USERNAME)s/.ssh/%(GITHUB_DEPLOY_KEY_NAME)s"}},
  {"action":"run", "params":"chmod 600 /home/%(SERVER_USERNAME)s/.ssh/%(GITHUB_DEPLOY_KEY_NAME)s"},
  {"action":"run", "params":"""echo 'IdentityFile /home/%(SERVER_USERNAME)s/.ssh/%(GITHUB_DEPLOY_KEY_NAME)s' >> /home/%(SERVER_USERNAME)s/.ssh/config"""},
  {"action":"run", "params":"ssh-keyscan github.com >> /home/%(SERVER_USERNAME)s/.ssh/known_hosts"},
  
  # Create virtualevn
  {"action":"run", "params":"mkvirtualenv --no-site-packages %(PROJECT_NAME)s",
    "message":"Creating virtualenv"},
  
  # install django in virtual env
  {"action":"virtualenv", "params":"pip install django",
    "message":"Installing django"},
  {"action":"virtualenv", "params":"django-admin.py startproject %(PROJECT_NAME)s",
    "message":"Creating a blank django project"},
  
  # install gunicorn in virtual env
  {"action":"virtualenv", "params":"pip install gunicorn",
    "message":"Installing gunicorn"},
  {"action":"put", "params":{"file":"%(FABULOUS_PATH)s/templates/gunicorn.conf.py",
                            "destination":"%(PROJECT_PATH)s/gunicorn.conf.py"}},
                            
  # Setup supervisor
  {"action":"run", "params":"echo_supervisord_conf > /home/%(SERVER_USERNAME)s/supervisord.conf",
    "message":"Configuring supervisor"},
  {"action":"put_template", "params":{"template":"%(FABULOUS_PATH)s/templates/supervisord.conf",
                                      "destination":"/home/%(SERVER_USERNAME)s/my.supervisord.conf"}},
  {"action":"run", "params":"cat /home/%(SERVER_USERNAME)s/my.supervisord.conf >> /home/%(SERVER_USERNAME)s/supervisord.conf"},
  {"action":"run", "params":"rm /home/%(SERVER_USERNAME)s/my.supervisord.conf"},
  {"action":"sudo", "params":"mv /home/%(SERVER_USERNAME)s/supervisord.conf /etc/supervisord.conf"},
  {"action":"sudo", "params":"supervisord"},
  {"action":"put", "params":{"file":"%(FABULOUS_PATH)s/templates/supervisord-init",
                            "destination":"/home/%(SERVER_USERNAME)s/supervisord-init"}},
  {"action":"sudo", "params":"mv /home/%(SERVER_USERNAME)s/supervisord-init /etc/init.d/supervisord"},
  {"action":"sudo", "params":"chmod +x /etc/init.d/supervisord"},
  {"action":"sudo", "params":"update-rc.d supervisord defaults"}
]
########NEW FILE########
__FILENAME__ = fabulous
from fabric.api import *
from fabric.colors import green as _green, yellow as _yellow
from fabulous_conf import *
from cookbook import recipe
import boto
import boto.ec2
import time


env.user = fabconf['SERVER_USERNAME']
env.key_filename = fabconf['SSH_PRIVATE_KEY_PATH']


def ulous():
    """
    *** This is what you run the first time ***
    """
    fab()


def fab():
    """
    This does the real work for the ulous() task. Is here to provide backwards compatibility
    """
    start_time = time.time()
    print(_green("Started..."))
    env.host_string = _create_server()
    print(_green("Waiting 30 seconds for server to boot..."))
    time.sleep(30)
    _oven()
    end_time = time.time()
    print(_green("Runtime: %f minutes" % ((end_time - start_time) / 60)))
    print(_green(env.host_string))


def _oven():
    """
    Cooks the recipe. Fabulous!
    """
    for ingredient in recipe:
        try:
            print(_yellow(ingredient['message']))
        except KeyError:
            pass
        globals()["_" + ingredient['action']](ingredient['params'])


def _create_server():
    """
    Creates EC2 Instance
    """
    print(_yellow("Creating instance"))
    conn = boto.ec2.connect_to_region(ec2_region, aws_access_key_id=ec2_key, aws_secret_access_key=ec2_secret)

    image = conn.get_all_images(ec2_amis)

    reservation = image[0].run(1, 1, ec2_keypair, ec2_secgroups,
        instance_type=ec2_instancetype)

    instance = reservation.instances[0]
    conn.create_tags([instance.id], {"Name":fabconf['INSTANCE_NAME_TAG']})
    
    while instance.state == u'pending':
        print(_yellow("Instance state: %s" % instance.state))
        time.sleep(10)
        instance.update()

    print(_green("Instance state: %s" % instance.state))
    print(_green("Public dns: %s" % instance.public_dns_name))
    
    return instance.public_dns_name


def _virtualenv(params):
    """
    Allows running commands on the server
    with an active virtualenv
    """
    with cd(fabconf['APPS_DIR']):
        _virtualenv_command(_render(params))


def _apt(params):
    """
    Runs apt-get install commands
    """
    for pkg in params:
        _sudo("apt-get install -qq %s" % pkg)


def _pip(params):
    """
    Runs pip install commands
    """
    for pkg in params:
        _sudo("pip install %s" % pkg)


def _run(params):
    """
    Runs command with active user
    """
    command = _render(params)
    run(command)


def _sudo(params):
    """
    Run command as root
    """
    command = _render(params)
    sudo(command)


def _put(params):
    """
    Moves a file from local computer to server
    """
    put(_render(params['file']), _render(params['destination']))


def _put_template(params):
    """
    Same as _put() but it loads a file and does variable replacement
    """
    f = open(_render(params['template']), 'r')
    template = f.read()

    run(_write_to(_render(template), _render(params['destination'])))


def _render(template, context=fabconf):
    """
    Does variable replacement
    """
    return template % context


def _write_to(string, path):
    """
    Writes a string to a file on the server
    """
    return "echo '" + string + "' > " + path


def _append_to(string, path):
    """
    Appends to a file on the server
    """
    return "echo '" + string + "' >> " + path


def _virtualenv_command(command):
    """
    Activates virtualenv and runs command
    """
    with cd(fabconf['APPS_DIR']):
        sudo(fabconf['ACTIVATE'] + ' && ' + command, user=fabconf['SERVER_USERNAME'])

########NEW FILE########
__FILENAME__ = fabulous_conf
import os.path

fabconf = {}

#  Do not edit
fabconf['FABULOUS_PATH'] = os.path.dirname(__file__)

# Username for connecting to EC2 instaces
fabconf['SERVER_USERNAME'] = "ubuntu"

# Full local path for .ssh
fabconf['SSH_PATH'] = "/path/to/.ssh"

# Name of the private key file you use to connect to EC2 instances
fabconf['EC2_KEY_NAME'] = "key.pem"

# Don't edit. Full path of the ssh key you use to connect to EC2 instances
fabconf['SSH_PRIVATE_KEY_PATH'] = '%s/%s' % (fabconf['SSH_PATH'], fabconf['EC2_KEY_NAME'])

# Project name: polls
fabconf['PROJECT_NAME'] = "polls"

# Where to install apps
fabconf['APPS_DIR'] = "/home/%s/webapps" % fabconf['SERVER_USERNAME']

# Where you want your project installed: /APPS_DIR/PROJECT_NAME
fabconf['PROJECT_PATH'] = "%s/%s" % (fabconf['APPS_DIR'], fabconf['PROJECT_NAME'])

# App domains
fabconf['DOMAINS'] = "example.com www.example.com"

# Path for virtualenvs
fabconf['VIRTUALENV_DIR'] = "/home/%s/.virtualenvs" % fabconf['SERVER_USERNAME']

# Email for the server admin
fabconf['ADMIN_EMAIL'] = "webmaster@localhost"

# Git username for the server
fabconf['GIT_USERNAME'] = "Server"

# Name of the private key file used for github deployments
fabconf['GITHUB_DEPLOY_KEY_NAME'] = "github"

# Don't edit. Local path for deployment key you use for github
fabconf['GITHUB_DEPLOY_KEY_PATH'] = "%s/%s" % (fabconf['SSH_PATH'], fabconf['GITHUB_DEPLOY_KEY_NAME'])

# Path to the repo of the application you want to install
fabconf['GITHUB_REPO'] = "https://github.com/gcollazo/Blank-django-Project.git"

# Virtualenv activate command
fabconf['ACTIVATE'] = "source /home/%s/.virtualenvs/%s/bin/activate" % (fabconf['SERVER_USERNAME'], fabconf['PROJECT_NAME'])

# Name tag for your server instance on EC2
fabconf['INSTANCE_NAME_TAG'] = "AppServer"

# EC2 key. http://bit.ly/j5ImEZ
ec2_key = ''

# EC2 secret. http://bit.ly/j5ImEZ
ec2_secret = ''

#EC2 region. http://amzn.to/12jBkm7
ec2_region = 'us-east-1'

# AMI name. http://bit.ly/liLKxj
ec2_amis = ['ami-1335f37a']

# Name of the keypair you use in EC2. http://bit.ly/ldw0HZ
ec2_keypair = ''

# Name of the security group. http://bit.ly/kl0Jyn
ec2_secgroups = ['']

# API Name of instance type. http://bit.ly/mkWvpn
ec2_instancetype = 't1.micro'

########NEW FILE########
__FILENAME__ = gunicorn.conf
import os

def numCPUs():
    if not hasattr(os, "sysconf"):
        raise RuntimeError("No sysconf detected.")
    return os.sysconf("SC_NPROCESSORS_ONLN")

bind = "127.0.0.1:8000"
workers = numCPUs() * 2 + 1
########NEW FILE########
