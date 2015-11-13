__FILENAME__ = api
from fabric.api import *
from fabric.context_managers import *
from fabric.operations import _handle_failure
#from djangofab.vcs.git import update_remote, update_local, push, commit, add
from djangofab.decorator import user_settings
from djangofab.util import local as local, apply_settings
from djangofab.django import get_remote_db, put_local_db, change_ownership, touch_wsgi

from fabric.main import _internals
_internals.append(apply_settings)
_internals.append(user_settings)
_internals.append(contextmanager)
_internals.append(nested)
_internals.append(local)

########NEW FILE########
__FILENAME__ = decorator

def user_settings(file='fab.cfg', group='default'):
    "Decorator to load user settings from a config file into the env"
    from djangofab.util import apply_settings
    def wrap(f=None):
        def wrapped_f(*args):
            f(*args)
            apply_settings(file,group) 
        return wrapped_f
    return wrap



########NEW FILE########
__FILENAME__ = django

from __future__ import with_statement
import os
from djangofab.api import *

def get_remote_db():
    "Download the latest database from the server and load it onto your local database"
    dbsettings = get_db_settings()
    with cd(env.path):
        if dbsettings['engine']=='mysql': 
            run('mysqldump -u%(user)s -p%(pass)s %(name)s > database' % dbsettings )
        elif dbsettings['engine']=='postgresql' or dbsettings['engine']=='postgresql_psycopg2':
            run('psql -u%(user)s -p%(pass)s %(name)s > database' % dbsettings)
    
    get(env.path+'/database', 'database')
    if dbsettings['engine']=='mysql': 
        local('echo "create database if not exists %(name)s;" | mysql -u%(user)s -p%(pass)s' % dbsettings)
        local('mysql -u%(user)s -p%(pass)s %(name)s < database' % dbsettings)
    elif dbsettings['engine']=='postgresql' or dbsettings['engine']=='postgresql_psycopg2':
        run('echo "create database if not exists %(name)s;" | psql -u%(user)s -p%(pass)s' % dbsettings)

def put_local_db():
    "Dump your local database and load it onto the servers databse"
    dbsettings = get_db_settings()
    if dbsettings['engine']=='mysql': 
        local('mysqldump -u%s -p%s %s > database' %\
        (settings.DATABASE_USER, settings.DATABASE_PASSWORD, settings.DATABASE_NAME))
        put('database', 'database')
        local('mysql -u%s -p%s %s < database' %\
        (settings.DATABASE_USER, settings.DATABASE_PASSWORD, settings.DATABASE_NAME))
    elif dbsettings['engine']=='postgresql' or dbsettings['engine']=='postgresql_psycopg2':
        local('mysqldump -u%s -p%s %s > database' %\
        (settings.DATABASE_USER, settings.DATABASE_PASSWORD, settings.DATABASE_NAME))
        put('database', 'database')
        local('mysql -u%s -p%s %s < database' %\
        (settings.DATABASE_USER, settings.DATABASE_PASSWORD, settings.DATABASE_NAME))

def get_db_settings():
    try:
        from fabfile import settings
    except ImportError:
        msg = 'Please import django settings in your fabfile.py \nfrom django.conf import settings'
        _handle_failure(message=msg)
    if not 'DJANGO_SETTINGS_MODULE' in os.environ:
        msg = 'DJANGO_SETTINGS_MODULE not set \nYou must call a settings function that sets the os.environ[DJANGO_SETTINGS_MODULE] first'        
        _handle_failure(message=msg)
    if not hasattr(settings, 'DATABASE_USER'):
        # global settings is not the django settings
        msg = 'Please import django settings in your fabfile.py \nfrom django.conf import settings'        
        _handle_failure(message=msg)
    return {'user': settings.DATABASE_USER, 'pass':settings.DATABASE_PASSWORD, \
            'name':settings.DATABASE_NAME,'engine':settings.DATABASE_ENGINE}


def change_ownership():
    "Set user and group ownership on the website path"
    with cd(env.path):
        sudo('chown %s.%s -R .' % (env.site_user, env.site_group,))
        sudo('chmod ug+rw -R .')

def touch_wsgi():
    "Touch the wsgi file to trigger wsgi to reload the processes."
    with cd(env.path):
        #run("touch bin/django.wsgi")
        run("touch %s" % env.wsgi)

def syncdb():
    "Sync database and run"
    pass




########NEW FILE########
__FILENAME__ = util
import os
import ConfigParser
#from djangofab.api import *
from fabric.api import *
from fabric.operations import local as _local

def local(cmd):
    if hasattr(env,'capture_default'):
        _local(cmd, env.capture_default)
    else:
        _local(cmd)

def apply_settings(file='fab.cfg', group='default'):
    if not os.path.exists(file):
        _handle_failure(message='Configuration file %s does not exist' % file)
        return
    config = ConfigParser.ConfigParser()
    config.readfp(open(file))
    user_settings = {}
    os.environ['DJANGO_SETTINGS_MODULE'] = config.get(group,'django.settings')
    for name,value in config.items(group):
        user_settings[name] = value
    for key in env:
        if env[key] and isinstance(env[key],str):
            env[key] = env[key] % user_settings


########NEW FILE########
__FILENAME__ = git
from __future__ import with_statement
from djangofab.api import *
import os

def update_remote():
    "Update remote checkout to the latest version"
    with cd(env.path):
        run('git reset --hard')
        run('git pull')

def update_app():
    "Update remote checkout to the latest version"
    app = prompt('app name?')
    #with cd(os.path.join(os.path.dirname(env.path),'src',app)):
    with cd(os.path.join(env.virtualenv,'src',app)):
        run('git reset --hard')
        run('git pull origin master')

def push():
    "Pull changes from version control"
    local('git push')

def update_local():  
    "Pull changes from version control"
    local('git pull')

def commit():
    "Save changes to version control"
    local('git commit -a')

def add(file):
    "Add files to the repository"
    local('git add %s' %file)

########NEW FILE########
__FILENAME__ = svn

from __future__ import with_statement
from djangofab.api import *

def update_remote():
    "Update remote checkout to the latest version"
    with cd(env.path):        
        if not remote_checkout_exists():
            run('svn co %s %s' % (env.svnurl, env.path))
        run('svn update')

def remote_export():
    "Update remote checkout to the latest version"
    with cd(env.path):
        run('svn export %s %s' % (env.svnurl, env.svnpath))

def update_local():  
    "Pull changes from version control"
    local('svn update')

def commit():
    "Save changes to version control"
    local('svn commit')

def add(file):
    "Add files to the repository"
    local('svn add %s' %file)

def checkout_local():
    local('svn co %s %s' % (env.svnurl, env.path))

def remote_checkout_exists():
    #with cd(env.path):
    out = run('ls -a | grep svn').strip()
    if out=='.svn':
        return True
    return False    

########NEW FILE########
__FILENAME__ = fabfile-git
from djangofab.api import *
from django.conf import settings
from djangofab.vcs.git import update_remote, update_local, push, commit, add
env.capture_default = False

# apply the settings from fab.cfg default section
# sets DJANGO_SETTINGS which allows access to django.conf.settings values
apply_settings()

#use the default section of fab.cfg
@user_settings()
def prod():
    "Production settings"
    env.hosts = ['server1']
    env.path = '%(prod_path)s'
    env.giturl = '%(giturl)s'
    env.site_user = 'owner'
    env.site_group = 'group'

@user_settings()
def dev():
    "Development settings"
    env.hosts = ['server1']
    env.path = '%(dev_path)s'
    env.giturl = '%(giturl)s'
    env.site_user = 'owner'
    env.site_group = 'group'

#use the local section
@user_settings('fab.cfg','local')
def localhost():
    "Local settings"
    env.path = '%(dev_path)s'
    env.giturl = '%(giturl)s'

def deploy():
    "Push local changes and update checkout on the remote host"
    push()
    update_remote() # reset and pull on the remote server
    #remote_export() 
    change_ownership()
    touch_wsgi()

def test():    
    print "website using database %s " % (settings.DATABASE_NAME,)
    

########NEW FILE########
__FILENAME__ = fabfile-svn
from djangofab.api import *
from djangofab.vcs.svn import update_remote, update_local, commit, add
env.capture_default = False

#use the default section of fab.cfg
@user_settings()
def prod():
    "Production settings"
    env.hosts = ['server1']
    env.path = '%(prod_path)s'
    env.svnurl = '%(svnurl)s'
    env.site_user = 'owner'
    env.site_group = 'group'

@user_settings()
def dev():
    "Development settings"
    env.hosts = ['server1']
    env.path = '%(dev_path)s'
    env.svnurl = '%(svnurl)s'
    env.site_user = 'owner'
    env.site_group = 'group'

#use the local section
@user_settings('fab.cfg','local')
def localhost():
    "Local settings"
    env.path = '%(dev_path)s'
    env.svnurl = '%(svnurl)s'

def deploy():
    "Push local changes and update checkout on the remote host"
    update_remote() #this will update a checkout
    #remote_export() 
    change_ownership()
    touch_wsgi()

########NEW FILE########
