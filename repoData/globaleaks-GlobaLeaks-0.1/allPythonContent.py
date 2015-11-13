__FILENAME__ = fabfile
import sys
import random
import string
import itertools
import collections
from fabric.api import run, env, put, get, local
import pystache

env.use_ssh_config = True

instance_dir = "/data/globaleaks-instances"
instances_config = "/etc/glinstances.conf"
tor_user = 'debian-tor'
hs_base_dir = '/usr/local/var/lib/tor/'
def consume(iterator, n):
    collections.deque(itertools.islice(iterator, n))

class FakeSecHead(object):
    def __init__(self, fp):
        self.fp = fp
        self.sechead = '[asection]\n'
    def readline(self):
        if self.sechead:
            try: return self.sechead
            finally: self.sechead = None
        else: return self.fp.readline()

def _make_tor2web_template():
    tor2web_template = 'tor2web/apache2/tor2web.template'
    f = open(tor2web_template)
    template = ''.join(f.readlines())
    f.close()
    return template

def delete(name):
    run('rm -rf %s/%s' % (instance_dir, name))
    run('rm -rf /data/globaleaks-instances/%s-globaleaks' % name)
    run('rm -rf %shs_%s' % (hs_base_dir, name))
    random_filename = '/tmp/'
    random_filename += ''.join(random.choice(string.ascii_lowercase)
                                for x in range(30))
    get('/etc/glinstances.conf',
            random_filename)
    instance_string = None
    with open(random_filename, 'r') as f:
        import ConfigParser
        config = ConfigParser.SafeConfigParser()
        config.readfp(FakeSecHead(f))
        r_instances = None
        for item, value in config.items('asection'):
            if item == 'instances':
                r_instances = value

    print "[+] Pushing new config file..."
    with open(random_filename, 'w+') as f:
        f.write('# THIS WAS SELF GENERATED\n')
        f.write('instance_dir='+instance_dir+'\n')
        if not r_instances:
            f.write('instances=\n')
        else:
            instances = r_instances.split(',')
            for i in instances:
                if i.startswith(name):
                    continue
                elif not instance_string:
                    instance_string = i
                else:
                    instance_string += ','+i
            instance_string = '' if not instance_string else instance_string
            f.write('instances='+instance_string+'\n')
    put(random_filename, instances_config)

    get('/etc/tor/torrc', random_filename+'.tor')
    lines = []
    with open(random_filename+'.tor', 'r') as f:
        for line in f:
            if name in line:
                lines.pop()
                consume(f, 3)
                continue
            else:
                lines.append(line)


    with open(random_filename+'.new_tor', 'w') as nt:
        for line in lines:
            nt.write(line)
    put(random_filename+'.new_tor', '/etc/tor/torrc')
    local('rm -rf '+random_filename+'*')

def list_instances():
    print "[+] Listing existing instances..."
    output = run('ls '+instance_dir)
    files = output.split()
    instances = []
    print "Currently installed instances"
    print "-----------------------------"
    for f in files:
        if f.startswith('demo'):
            instances.append(f)

        if not f.startswith('template'):
            print "    * %s" % f

    instances.sort()
    print "-----------------------------"
    return instances

def new_instance():
    print "[+] Creating a new instance"
    instances = list_instances()
    # Create the correct template
    idx = instances[-1].replace('demo','')
    if idx == '':
        print "[+] Creating the first new instance!"
        new_instance_idx = '1'
    else:
        new_instance_idx = str(int(idx) + 1)
    new_instance = 'demo'+'0'*(3 - len(new_instance_idx))+new_instance_idx
    new_instance = 'pentest2'
    template = _make_tor2web_template()

    # Check if template exists
    if not run('ls '+instance_dir+'/template'):
        print "[!] No Template found!"
        print "[+] Cloning globaleaks repo...."
        run('git clone https://github.com/globaleaks/GlobaLeaks.git'+
                                                    instance_dir+'/template')

    # Create copy of globaleaks
    print "[+] Creating copy of globaleaks template..."
    run('cp -R '+instance_dir+'/template '+instance_dir+'/'+new_instance)

    # Fill in the tor2web template
    print "[+] Creating tor2web template..."
    server_name = new_instance+'.globaleaks.org'
    port_number = str(8010 + int(new_instance_idx))
    tor2web_config = {'port_number': '80',
                  #'ssl_engine': 'Off',
                  #'path_to_sslcertificate': '',
                  #'path_to_certificate_key': '',
                  'server_name': server_name,
                  'rewrite_condition': server_name.replace('.', '\\.'),
                  'rewrite_host': env.host+':'+port_number,
                  'dot_onion': ''
                  }

    tor2web_conf_template = pystache.render(template, tor2web_config)
    random_filename = '/tmp/'
    random_filename += ''.join(random.choice(string.ascii_lowercase)
                               for x in range(30))
    with open(random_filename, 'w+') as f:
        f.write(tor2web_conf_template)

    # Push the template to the server
    print "[+] Pushing template to server..."
    put(random_filename,
        '/etc/apache2/sites-enabled/'+new_instance+'-globaleaks')

    print "[+] Getting remote config file..."
    get(instances_config, random_filename+'.cfg')
    with open(random_filename+'.cfg', 'r') as f:
        import ConfigParser
        config = ConfigParser.SafeConfigParser()
        config.readfp(FakeSecHead(f))
        r_instances = None
        for item, value in config.items('asection'):
            if item == 'instances':
                r_instances = value

    print "[+] Pushing new config file..."
    with open(random_filename+'.cfg', 'w+') as f:
        f.write('# THIS WAS SELF GENERATED\n')
        f.write('instance_dir='+instance_dir+'\n')
        if not r_instances:
            f.write('instances='+new_instance+':'+port_number+'\n')
        else:
            f.write('instances='+r_instances+','+new_instance+':'+port_number+'\n')

    put(random_filename+'.cfg', instances_config)

    # XXX Update torrc and restart the globaleaks init script. Get hidden
    # service of latest instance.
    print "[+] Getting remote torrc file..."
    get('/etc/tor/torrc', random_filename+'.tor')

    HSDir = hs_base_dir + 'hs_' + new_instance + '/'
    with open(random_filename+'.tor', 'a+') as f:
        f.write('\n\n# This part of config was auto generated\n')
        f.write('HiddenServiceDir %s\n' % HSDir)
        f.write('HiddenServicePort 80 127.0.0.1:%s\n' % port_number)
        f.write('# end\n')

    run('mkdir -p %s' % HSDir)
    run('chown -R %s %s' % (tor_user, HSDir))

    print "[+] Pushing new torrc config file..."
    put(random_filename+'.tor', '/etc/tor/torrc')
    run('/etc/init.d/tor restart')
    dot_onion = run('cat %s/hostname' % HSDir)

    print "[+] Replacing known values in globaleaks template"
    with open(random_filename+'.gl', 'w+') as gf:
        with open('globaleaks/defaults/original.globaleaks.conf') as f:
            for line in f:
                if line.strip().startswith('hsurl'):
                    print l
                    l = line.replace('oooooooooooooooo.onion', dot_onion)
                elif line.strip().startswith('baseurl'):
                    print l
                    l = line.replace('https://example.com', 'http://'+server_name)
                elif line.strip().startswith('server_port'):
                    print l
                    l = line.replace('8000', port_number)
                elif line.strip().startswith('server_ip'):
                    l = line.replace('127.0.0.1', env.host)
                    print l
                else:
                    l = line
                gf.write(l)

    print "[+] Pushing globaleaks.conf file to remote host"
    put(random_filename+'.gl',
            instance_dir+'/'+new_instance+'/globaleaks/globaleaks.conf')

    print "[+] Setting proper permissions..."
    run('chown -R globaleaks:globaleaks '+instance_dir+'/'+new_instance)

    print "[+] Cleaning up tmp files"
    local('rm -rf %s*' % random_filename)

    print "[+] Restarting Globaleaks-service"
    run('/etc/init.d/globaleaks-service restart')
    run('/etc/init.d/apache2 reload')

    print "[+] Created new globaleaks instance!"
    print ""
    print "Details"
    print "-------"
    print "Hostname: "+server_name
    print "Local Port: "+port_number
    print "Hidden Service: "+dot_onion


########NEW FILE########
__FILENAME__ = appadmin
# -*- coding: utf-8 -*-

# ##########################################################
# ## make sure administrator is on localhost
# ###########################################################

import os
import socket
import datetime
import copy
import gluon.contenttype
import gluon.fileutils

# ## critical --- make a copy of the environment

global_env = copy.copy(globals())
global_env['datetime'] = datetime

http_host = request.env.http_host.split(':')[0]
remote_addr = request.env.remote_addr
try:
    hosts = (http_host, socket.gethostname(),
             socket.gethostbyname(http_host),
             '::1','127.0.0.1','::ffff:127.0.0.1')
except:
    hosts = (http_host, )

if request.env.http_x_forwarded_for or request.env.wsgi_url_scheme\
     in ['https', 'HTTPS']:
    session.secure()
elif (remote_addr not in hosts) and (remote_addr != "127.0.0.1"):
    raise HTTP(200, T('appadmin is disabled because insecure channel'))

if (request.application=='admin' and not session.authorized) or \
        (request.application!='admin' and not gluon.fileutils.check_credentials(request)):
    redirect(URL('admin', 'default', 'index'))

ignore_rw = True
response.view = 'appadmin.html'
response.menu = [[T('design'), False, URL('admin', 'default', 'design',
                 args=[request.application])], [T('db'), False,
                 URL('index')], [T('state'), False,
                 URL('state')], [T('cache'), False,
                 URL('ccache')]]

# ##########################################################
# ## auxiliary functions
# ###########################################################


def get_databases(request):
    dbs = {}
    for (key, value) in global_env.items():
        cond = False
        try:
            cond = isinstance(value, GQLDB)
        except:
            cond = isinstance(value, SQLDB)
        if cond:
            dbs[key] = value
    return dbs


databases = get_databases(None)


def eval_in_global_env(text):
    exec ('_ret=%s' % text, {}, global_env)
    return global_env['_ret']


def get_database(request):
    if request.args and request.args[0] in databases:
        return eval_in_global_env(request.args[0])
    else:
        session.flash = T('invalid request')
        redirect(URL('index'))


def get_table(request):
    db = get_database(request)
    if len(request.args) > 1 and request.args[1] in db.tables:
        return (db, request.args[1])
    else:
        session.flash = T('invalid request')
        redirect(URL('index'))


def get_query(request):
    try:
        return eval_in_global_env(request.vars.query)
    except Exception:
        return None


def query_by_table_type(tablename,db,request=request):
    keyed = hasattr(db[tablename],'_primarykey')
    if keyed:
        firstkey = db[tablename][db[tablename]._primarykey[0]]
        cond = '>0'
        if firstkey.type in ['string', 'text']:
            cond = '!=""'
        qry = '%s.%s.%s%s' % (request.args[0], request.args[1], firstkey.name, cond)
    else:
        qry = '%s.%s.id>0' % tuple(request.args[:2])
    return qry



# ##########################################################
# ## list all databases and tables
# ###########################################################


def index():
    return dict(databases=databases)


# ##########################################################
# ## insert a new record
# ###########################################################


def insert():
    (db, table) = get_table(request)
    form = SQLFORM(db[table], ignore_rw=ignore_rw)
    if form.accepts(request.vars, session):
        response.flash = T('new record inserted')
    return dict(form=form,table=db[table])


# ##########################################################
# ## list all records in table and insert new record
# ###########################################################


def download():
    import os
    db = get_database(request)
    return response.download(request,db)

def csv():
    import gluon.contenttype
    response.headers['Content-Type'] = \
        gluon.contenttype.contenttype('.csv')
    db = get_database(request)
    query = get_query(request)
    if not query:
        return None
    response.headers['Content-disposition'] = 'attachment; filename=%s_%s.csv'\
         % tuple(request.vars.query.split('.')[:2])
    return str(db(query).select())


def import_csv(table, file):
    table.import_from_csv_file(file)

def select():
    import re
    db = get_database(request)
    dbname = request.args[0]
    regex = re.compile('(?P<table>\w+)\.(?P<field>\w+)=(?P<value>\d+)')
    if len(request.args)>1 and hasattr(db[request.args[1]],'_primarykey'):
        regex = re.compile('(?P<table>\w+)\.(?P<field>\w+)=(?P<value>.+)')
    if request.vars.query:
        match = regex.match(request.vars.query)
        if match:
            request.vars.query = '%s.%s.%s==%s' % (request.args[0],
                    match.group('table'), match.group('field'),
                    match.group('value'))
    else:
        request.vars.query = session.last_query
    query = get_query(request)
    if request.vars.start:
        start = int(request.vars.start)
    else:
        start = 0
    nrows = 0
    stop = start + 100
    table = None
    rows = []
    orderby = request.vars.orderby
    if orderby:
        orderby = dbname + '.' + orderby
        if orderby == session.last_orderby:
            if orderby[0] == '~':
                orderby = orderby[1:]
            else:
                orderby = '~' + orderby
    session.last_orderby = orderby
    session.last_query = request.vars.query
    form = FORM(TABLE(TR(T('Query:'), '', INPUT(_style='width:400px',
                _name='query', _value=request.vars.query or '',
                requires=IS_NOT_EMPTY(error_message=T("Cannot be empty")))), TR(T('Update:'),
                INPUT(_name='update_check', _type='checkbox',
                value=False), INPUT(_style='width:400px',
                _name='update_fields', _value=request.vars.update_fields
                 or '')), TR(T('Delete:'), INPUT(_name='delete_check',
                _class='delete', _type='checkbox', value=False), ''),
                TR('', '', INPUT(_type='submit', _value='submit'))),
                _action=URL(r=request,args=request.args))
    if request.vars.csvfile != None:
        try:
            import_csv(db[request.vars.table],
                       request.vars.csvfile.file)
            response.flash = T('data uploaded')
        except Exception, e:
            response.flash = DIV(T('unable to parse csv file'),PRE(str(e)))
    if form.accepts(request.vars, formname=None):
#         regex = re.compile(request.args[0] + '\.(?P<table>\w+)\.id\>0')
        regex = re.compile(request.args[0] + '\.(?P<table>\w+)\..+')

        match = regex.match(form.vars.query.strip())
        if match:
            table = match.group('table')
        try:
            nrows = db(query).count()
            if form.vars.update_check and form.vars.update_fields:
                db(query).update(**eval_in_global_env('dict(%s)'
                                  % form.vars.update_fields))
                response.flash = T('%s rows updated', nrows)
            elif form.vars.delete_check:
                db(query).delete()
                response.flash = T('%s rows deleted', nrows)
            nrows = db(query).count()
            if orderby:
                rows = db(query).select(limitby=(start, stop),
                        orderby=eval_in_global_env(orderby))
            else:
                rows = db(query).select(limitby=(start, stop))
        except Exception, e:
            (rows, nrows) = ([], 0)
            response.flash = DIV(T('Invalid Query'),PRE(str(e)))
    return dict(
        form=form,
        table=table,
        start=start,
        stop=stop,
        nrows=nrows,
        rows=rows,
        query=request.vars.query,
        )


# ##########################################################
# ## edit delete one record
# ###########################################################


def update():
    (db, table) = get_table(request)
    keyed = hasattr(db[table],'_primarykey')
    record = None
    if keyed:
        key = [f for f in request.vars if f in db[table]._primarykey]
        if key:
            record = db(db[table][key[0]] == request.vars[key[0]]).select().first()
    else:
        record = db(db[table].id == request.args(2)).select().first()

    if not record:
        qry = query_by_table_type(table, db)
        session.flash = T('record does not exist')
        redirect(URL('select', args=request.args[:1],
                     vars=dict(query=qry)))

    if keyed:
        for k in db[table]._primarykey:
            db[table][k].writable=False

    form = SQLFORM(db[table], record, deletable=True, delete_label=T('Check to delete'),
                   ignore_rw=ignore_rw and not keyed,
                   linkto=URL('select',
                   args=request.args[:1]), upload=URL(r=request,
                   f='download', args=request.args[:1]))

    if form.accepts(request.vars, session):
        session.flash = T('done!')
        qry = query_by_table_type(table, db)
        redirect(URL('select', args=request.args[:1],
                 vars=dict(query=qry)))
    return dict(form=form,table=db[table])


# ##########################################################
# ## get global variables
# ###########################################################


def state():
    return dict()

def ccache():
    form = FORM(
        P(TAG.BUTTON("Clear CACHE?", _type="submit", _name="yes", _value="yes")),
        P(TAG.BUTTON("Clear RAM", _type="submit", _name="ram", _value="ram")),
        P(TAG.BUTTON("Clear DISK", _type="submit", _name="disk", _value="disk")),
    )

    if form.accepts(request.vars, session):
        clear_ram = False
        clear_disk = False
        session.flash = ""
        if request.vars.yes:
            clear_ram = clear_disk = True
        if request.vars.ram:
            clear_ram = True
        if request.vars.disk:
            clear_disk = True

        if clear_ram:
            cache.ram.clear()
            session.flash += "Ram Cleared "
        if clear_disk:
            cache.disk.clear()
            session.flash += "Disk Cleared"

        redirect(URL(r=request))

    try:
        from guppy import hpy; hp=hpy()
    except ImportError:
        hp = False

    import shelve, os, copy, time, math
    from gluon import portalocker

    ram = {
        'bytes': 0,
        'objects': 0,
        'hits': 0,
        'misses': 0,
        'ratio': 0,
        'oldest': time.time()
    }
    disk = copy.copy(ram)
    total = copy.copy(ram)

    for key, value in cache.ram.storage.items():
        if isinstance(value, dict):
            ram['hits'] = value['hit_total'] - value['misses']
            ram['misses'] = value['misses']
            try:
                ram['ratio'] = ram['hits'] * 100 / value['hit_total']
            except (KeyError, ZeroDivisionError):
                ram['ratio'] = 0
        else:
            if hp:
                ram['bytes'] += hp.iso(value[1]).size
                ram['objects'] += hp.iso(value[1]).count

                if value[0] < ram['oldest']:
                    ram['oldest'] = value[0]

    locker = open(os.path.join(request.folder,
                                        'cache/cache.lock'), 'a')
    portalocker.lock(locker, portalocker.LOCK_EX)
    disk_storage = shelve.open(os.path.join(request.folder, 'cache/cache.shelve'))
    try:
        for key, value in disk_storage.items():
            if isinstance(value, dict):
                disk['hits'] = value['hit_total'] - value['misses']
                disk['misses'] = value['misses']
                try:
                    disk['ratio'] = disk['hits'] * 100 / value['hit_total']
                except (KeyError, ZeroDivisionError):
                    disk['ratio'] = 0
            else:
                if hp:
                    disk['bytes'] += hp.iso(value[1]).size
                    disk['objects'] += hp.iso(value[1]).count
                    if value[0] < disk['oldest']:
                        disk['oldest'] = value[0]
    finally:
        portalocker.unlock(locker)
        locker.close()
        disk_storage.close()

    total['bytes'] = ram['bytes'] + disk['bytes']
    total['objects'] = ram['objects'] + disk['objects']
    total['hits'] = ram['hits'] + disk['hits']
    total['misses'] = ram['misses'] + disk['misses']
    try:
        total['ratio'] = total['hits'] * 100 / (total['hits'] + total['misses'])
    except (KeyError, ZeroDivisionError):
        total['ratio'] = 0

    if disk['oldest'] < ram['oldest']:
        total['oldest'] = disk['oldest']
    else:
        total['oldest'] = ram['oldest']

    def GetInHMS(seconds):
        hours = math.floor(seconds / 3600)
        seconds -= hours * 3600
        minutes = math.floor(seconds / 60)
        seconds -= minutes * 60
        seconds = math.floor(seconds)

        return (hours, minutes, seconds)

    ram['oldest'] = GetInHMS(time.time() - ram['oldest'])
    disk['oldest'] = GetInHMS(time.time() - disk['oldest'])
    total['oldest'] = GetInHMS(time.time() - total['oldest'])

    return dict(form=form, total=total,
                ram=ram, disk=disk)


########NEW FILE########
__FILENAME__ = default
# coding: utf8

from gluon.admin import *
from gluon.fileutils import abspath, read_file, write_file
from glob import glob
import shutil
import platform

if DEMO_MODE and request.function in ['change_password','pack','pack_plugin','upgrade_web2py','uninstall','cleanup','compile_app','remove_compiled_app','delete','delete_plugin','create_file','upload_file','update_languages','reload_routes']:
    session.flash = T('disabled in demo mode')
    redirect(URL('site'))

if not is_manager() and request.function in ['change_password','upgrade_web2py']:
    session.flash = T('disabled in multi user mode')
    redirect(URL('site'))

if FILTER_APPS and request.args(0) and not request.args(0) in FILTER_APPS:
    session.flash = T('disabled in demo mode')
    redirect(URL('site'))

def safe_open(a,b):
    if DEMO_MODE and 'w' in b:
        class tmp:
            def write(self,data): pass
        return tmp()
    return open(a,b)

def safe_read(a, b='r'):
    safe_file = safe_open(a, b)
    try:
        return safe_file.read()
    finally:
        safe_file.close()

def safe_write(a, value, b='w'):
    safe_file = safe_open(a, b)
    try:
        safe_file.write(value)
    finally:
        safe_file.close()

def get_app(name=None):
    app = name or request.args(0)
    if app and (not MULTI_USER_MODE or db(db.app.name==app)(db.app.owner==auth.user.id).count()):
        return app
    session.flash = 'App does not exist or your are not authorized'
    redirect(URL('site'))

def index():
    """ Index handler """

    send = request.vars.send
    if DEMO_MODE:
        session.authorized = True
        session.last_time = t0
    if not send:
        send = URL('site')
    if session.authorized:
        redirect(send)
    elif request.vars.password:
        if verify_password(request.vars.password):
            session.authorized = True
            login_record(True)

            if CHECK_VERSION:
                session.check_version = True
            else:
                session.check_version = False

            session.last_time = t0
            if isinstance(send, list):  # ## why does this happen?
                send = str(send[0])

            redirect(send)
        else:
            times_denied = login_record(False)
            if times_denied >= allowed_number_of_attempts:
                response.flash = \
                    T('admin disabled because too many invalid login attempts')
            elif times_denied == allowed_number_of_attempts - 1:
                response.flash = \
                    T('You have one more login attempt before you are locked out')
            else:
                response.flash = T('invalid password.')
    return dict(send=send)


def check_version():
    """ Checks if web2py is up to date """

    session.forget()
    session._unlock(response)

    new_version, version_number = check_new_version(request.env.web2py_version,
                                    WEB2PY_VERSION_URL)

    if new_version == -1:
        return A(T('Unable to check for upgrades'), _href=WEB2PY_URL)
    elif new_version != True:
        return A(T('web2py is up to date'), _href=WEB2PY_URL)
    elif platform.system().lower() in ('windows','win32','win64') and os.path.exists("web2py.exe"):
        return SPAN('You should upgrade to version %s' % version_number)
    else:
        return sp_button(URL('upgrade_web2py'), T('upgrade now')) \
          + XML(' <strong class="upgrade_version">%s</strong>' % version_number)


def logout():
    """ Logout handler """
    session.authorized = None
    if MULTI_USER_MODE:
        redirect(URL('user/logout'))
    redirect(URL('index'))


def change_password():

    if session.pam_user:
        session.flash = T('PAM authenticated user, cannot change password here')
        redirect(URL('site'))
    form=SQLFORM.factory(Field('current_admin_password','password'),
                         Field('new_admin_password','password',requires=IS_STRONG()),
                         Field('new_admin_password_again','password'))
    if form.accepts(request.vars):
        if not verify_password(request.vars.current_admin_password):
            form.errors.current_admin_password = T('invalid password')
        elif form.vars.new_admin_password != form.vars.new_admin_password_again:
            form.errors.new_admin_password_again = T('no match')
        else:
            path = abspath('parameters_%s.py' % request.env.server_port)
            safe_write(path, 'password="%s"' % CRYPT()(request.vars.new_admin_password)[0])
            session.flash = T('password changed')
            redirect(URL('site'))
    return dict(form=form)

def site():
    """ Site handler """

    myversion = request.env.web2py_version

    # Shortcut to make the elif statements more legible
    file_or_appurl = 'file' in request.vars or 'appurl' in request.vars

    if DEMO_MODE:
        pass

    elif request.vars.filename and not 'file' in request.vars:
        # create a new application
        appname = cleanpath(request.vars.filename).replace('.', '_')
        if app_create(appname, request):
            if MULTI_USER_MODE:
                db.app.insert(name=appname,owner=auth.user.id)
            session.flash = T('new application "%s" created', appname)
            redirect(URL('design',args=appname))
        else:
            session.flash = \
                T('unable to create application "%s" (it may exist already)', request.vars.filename)
        redirect(URL(r=request))

    elif file_or_appurl and not request.vars.filename:
        # can't do anything without an app name
        msg = 'you must specify a name for the uploaded application'
        response.flash = T(msg)

    elif file_or_appurl and request.vars.filename:
        # fetch an application via URL or file upload
        f = None
        if request.vars.appurl is not '':
            try:
                f = urllib.urlopen(request.vars.appurl)
            except Exception, e:
                session.flash = DIV(T('Unable to download app because:'),PRE(str(e)))
                redirect(URL(r=request))
            fname = request.vars.appurl
        elif request.vars.file is not '':
            f = request.vars.file.file
            fname = request.vars.file.filename

        if f:
            appname = cleanpath(request.vars.filename).replace('.', '_')
            installed = app_install(appname, f, request, fname,
                                    overwrite=request.vars.overwrite_check)
        if f and installed:
            msg = 'application %(appname)s installed with md5sum: %(digest)s'
            session.flash = T(msg, dict(appname=appname,
                                        digest=md5_hash(installed)))
        elif f and request.vars.overwrite_check:
            msg = 'unable to install application "%(appname)s"'
            session.flash = T(msg, dict(appname=request.vars.filename))

        else:
            msg = 'unable to install application "%(appname)s"'
            session.flash = T(msg, dict(appname=request.vars.filename))

        redirect(URL(r=request))

    regex = re.compile('^\w+$')

    if is_manager():
        apps = [f for f in os.listdir(apath(r=request)) if regex.match(f)]
    else:
        apps = [f.name for f in db(db.app.owner==auth.user_id).select()]

    if FILTER_APPS:
        apps = [f for f in apps if f in FILTER_APPS]

    apps = sorted(apps,lambda a,b:cmp(a.upper(),b.upper()))

    return dict(app=None, apps=apps, myversion=myversion)


def pack():
    app = get_app()

    if len(request.args) == 1:
        fname = 'web2py.app.%s.w2p' % app
        filename = app_pack(app, request)
    else:
        fname = 'web2py.app.%s.compiled.w2p' % app
        filename = app_pack_compiled(app, request)

    if filename:
        response.headers['Content-Type'] = 'application/w2p'
        disposition = 'attachment; filename=%s' % fname
        response.headers['Content-Disposition'] = disposition
        return safe_read(filename, 'rb')
    else:
        session.flash = T('internal error')
        redirect(URL('site'))

def pack_plugin():
    app = get_app()
    if len(request.args) == 2:
        fname = 'web2py.plugin.%s.w2p' % request.args[1]
        filename = plugin_pack(app, request.args[1], request)
    if filename:
        response.headers['Content-Type'] = 'application/w2p'
        disposition = 'attachment; filename=%s' % fname
        response.headers['Content-Disposition'] = disposition
        return safe_read(filename, 'rb')
    else:
        session.flash = T('internal error')
        redirect(URL('plugin',args=request.args))

def upgrade_web2py():
    if 'upgrade' in request.vars:
        (success, error) = upgrade(request)
        if success:
            session.flash = T('web2py upgraded; please restart it')
        else:
            session.flash = T('unable to upgrade because "%s"', error)
        redirect(URL('site'))
    elif 'noupgrade' in request.vars:
        redirect(URL('site'))
    return dict()

def uninstall():
    app = get_app()
    if 'delete' in request.vars:
        if MULTI_USER_MODE:
            if is_manager() and db(db.app.name==app).delete():
                pass
            elif db(db.app.name==app)(db.app.owner==auth.user.id).delete():
                pass
            else:
                session.flash = T('no permission to uninstall "%s"', app)
                redirect(URL('site'))
        if app_uninstall(app, request):
            session.flash = T('application "%s" uninstalled', app)
        else:
            session.flash = T('unable to uninstall "%s"', app)
        redirect(URL('site'))
    elif 'nodelete' in request.vars:
        redirect(URL('site'))
    return dict(app=app)


def cleanup():
    app = get_app()
    clean = app_cleanup(app, request)
    if not clean:
        session.flash = T("some files could not be removed")
    else:
        session.flash = T('cache, errors and sessions cleaned')

    redirect(URL('site'))


def compile_app():
    app = get_app()
    c = app_compile(app, request)
    if not c:
        session.flash = T('application compiled')
    else:
        session.flash = DIV(T('Cannot compile: there are errors in your app:'),
                              CODE(c))
    redirect(URL('site'))


def remove_compiled_app():
    """ Remove the compiled application """
    app = get_app()
    remove_compiled_application(apath(app, r=request))
    session.flash = T('compiled application removed')
    redirect(URL('site'))

def delete():
    """ Object delete handler """
    app = get_app()
    filename = '/'.join(request.args)
    sender = request.vars.sender

    if isinstance(sender, list):  # ## fix a problem with Vista
        sender = sender[0]

    if 'nodelete' in request.vars:
        redirect(URL(sender))
    elif 'delete' in request.vars:
        try:
            os.unlink(apath(filename, r=request))
            session.flash = T('file "%(filename)s" deleted',
                              dict(filename=filename))
        except Exception:
            session.flash = T('unable to delete file "%(filename)s"',
                              dict(filename=filename))
        redirect(URL(sender))
    return dict(filename=filename, sender=sender)

def peek():
    """ Visualize object code """
    app = get_app()
    filename = '/'.join(request.args)
    try:
        data = safe_read(apath(filename, r=request)).replace('\r','')
    except IOError:
        session.flash = T('file does not exist')
        redirect(URL('site'))

    extension = filename[filename.rfind('.') + 1:].lower()

    return dict(app=request.args[0],
                filename=filename,
                data=data,
                extension=extension)


def test():
    """ Execute controller tests """
    app = get_app()
    if len(request.args) > 1:
        file = request.args[1]
    else:
        file = '.*\.py'

    controllers = listdir(apath('%s/controllers/' % app, r=request), file + '$')

    return dict(app=app, controllers=controllers)

def keepalive():
    return ''

def search():
    keywords=request.vars.keywords or ''
    app = get_app()
    def match(filename,keywords):
        filename=os.path.join(apath(app, r=request),filename)
        if keywords in read_file(filename,'rb'):
            return True
        return False
    path = apath(request.args[0], r=request)
    files1 = glob(os.path.join(path,'*/*.py'))
    files2 = glob(os.path.join(path,'*/*.html'))
    files3 = glob(os.path.join(path,'*/*/*.html'))
    files=[x[len(path)+1:].replace('\\','/') for x in files1+files2+files3 if match(x,keywords)]
    return response.json({'files':files})

def edit():
    """ File edit handler """
    # Load json only if it is ajax edited...
    app = get_app()
    filename = '/'.join(request.args)
    # Try to discover the file type
    if filename[-3:] == '.py':
        filetype = 'python'
    elif filename[-5:] == '.html':
        filetype = 'html'
    elif filename[-5:] == '.load':
        filetype = 'html'
    elif filename[-4:] == '.css':
        filetype = 'css'
    elif filename[-3:] == '.js':
        filetype = 'js'
    else:
        filetype = 'html'

    # ## check if file is not there

    path = apath(filename, r=request)

    if request.vars.revert and os.path.exists(path + '.bak'):
        try:
            data = safe_read(path + '.bak')
            data1 = safe_read(path)
        except IOError:
            session.flash = T('Invalid action')
            if 'from_ajax' in request.vars:
                 return response.json({'error': str(T('Invalid action'))})
            else:
                redirect(URL('site'))

        safe_write(path, data)
        file_hash = md5_hash(data)
        saved_on = time.ctime(os.stat(path)[stat.ST_MTIME])
        safe_write(path + '.bak', data1)
        response.flash = T('file "%s" of %s restored', (filename, saved_on))
    else:
        try:
            data = safe_read(path)
        except IOError:
            session.flash = T('Invalid action')
            if 'from_ajax' in request.vars:
                return response.json({'error': str(T('Invalid action'))})
            else:
                redirect(URL('site'))

        file_hash = md5_hash(data)
        saved_on = time.ctime(os.stat(path)[stat.ST_MTIME])

        if request.vars.file_hash and request.vars.file_hash != file_hash:
            session.flash = T('file changed on disk')
            data = request.vars.data.replace('\r\n', '\n').strip() + '\n'
            safe_write(path + '.1', data)
            if 'from_ajax' in request.vars:
                return response.json({'error': str(T('file changed on disk')),
                                      'redirect': URL('resolve',
                                                      args=request.args)})
            else:
                redirect(URL('resolve', args=request.args))
        elif request.vars.data:
            safe_write(path + '.bak', data)
            data = request.vars.data.replace('\r\n', '\n').strip() + '\n'
            safe_write(path, data)
            file_hash = md5_hash(data)
            saved_on = time.ctime(os.stat(path)[stat.ST_MTIME])
            response.flash = T('file saved on %s', saved_on)

    data_or_revert = (request.vars.data or request.vars.revert)

    # Check compile errors
    highlight = None
    if filetype == 'python' and request.vars.data:
        import _ast
        try:
            code = request.vars.data.rstrip().replace('\r\n','\n')+'\n'
            compile(code, path, "exec", _ast.PyCF_ONLY_AST)
        except Exception, e:
            start = sum([len(line)+1 for l, line
                            in enumerate(request.vars.data.split("\n"))
                            if l < e.lineno-1])
            if e.text and e.offset:
                offset = e.offset - (len(e.text) - len(e.text.splitlines()[-1]))
            else:
                offset = 0
            highlight = {'start': start, 'end': start + offset + 1}
            try:
                ex_name = e.__class__.__name__
            except:
                ex_name = 'unknown exception!'
            response.flash = DIV(T('failed to compile file because:'), BR(),
                                 B(ex_name), T(' at line %s') % e.lineno,
                                 offset and T(' at char %s') % offset or '',
                                 PRE(str(e)))

    if data_or_revert and request.args[1] == 'modules':
        # Lets try to reload the modules
        try:
            mopath = '.'.join(request.args[2:])[:-3]
            exec 'import applications.%s.modules.%s' % (request.args[0], mopath)
            reload(sys.modules['applications.%s.modules.%s'
                    % (request.args[0], mopath)])
        except Exception, e:
            response.flash = DIV(T('failed to reload module because:'),PRE(str(e)))

    edit_controller = None
    editviewlinks = None
    view_link = None
    if filetype == 'html' and len(request.args) >= 3:
        cfilename = os.path.join(request.args[0], 'controllers',
                                 request.args[2] + '.py')
        if os.path.exists(apath(cfilename, r=request)):
            edit_controller = URL('edit', args=[cfilename])
            view = request.args[3].replace('.html','')
            view_link = URL(request.args[0],request.args[2],view)
    elif filetype == 'python' and request.args[1] == 'controllers':
        ## it's a controller file.
        ## Create links to all of the associated view files.
        app = get_app()
        viewname = os.path.splitext(request.args[2])[0]
        viewpath = os.path.join(app,'views',viewname)
        aviewpath = apath(viewpath, r=request)
        viewlist = []
        if os.path.exists(aviewpath):
            if os.path.isdir(aviewpath):
                viewlist = glob(os.path.join(aviewpath,'*.html'))
        elif os.path.exists(aviewpath+'.html'):
            viewlist.append(aviewpath+'.html')
        if len(viewlist):
            editviewlinks = []
            for v in viewlist:
                vf = os.path.split(v)[-1]
                vargs = "/".join([viewpath.replace(os.sep,"/"),vf])
                editviewlinks.append(A(T(vf.split(".")[0]),\
                    _href=URL('edit',args=[vargs])))

    if len(request.args) > 2 and request.args[1] == 'controllers':
        controller = (request.args[2])[:-3]
        functions = regex_expose.findall(data)
    else:
        (controller, functions) = (None, None)

    if 'from_ajax' in request.vars:
        return response.json({'file_hash': file_hash, 'saved_on': saved_on, 'functions':functions, 'controller': controller, 'application': request.args[0], 'highlight': highlight })
    else:

        editarea_preferences = {}
        editarea_preferences['FONT_SIZE'] = '10'
        editarea_preferences['FULL_SCREEN'] = 'false'
        editarea_preferences['ALLOW_TOGGLE'] = 'true'
        editarea_preferences['REPLACE_TAB_BY_SPACES'] = '4'
        editarea_preferences['DISPLAY'] = 'onload'
        for key in editarea_preferences:
            if globals().has_key(key):
                editarea_preferences[key]=globals()[key]
        return dict(app=request.args[0],
                    filename=filename,
                    filetype=filetype,
                    data=data,
                    edit_controller=edit_controller,
                    file_hash=file_hash,
                    saved_on=saved_on,
                    controller=controller,
                    functions=functions,
                    view_link=view_link,
                    editarea_preferences=editarea_preferences,
                    editviewlinks=editviewlinks)

def resolve():
    """
    """

    filename = '/'.join(request.args)
    # ## check if file is not there
    path = apath(filename, r=request)
    a = safe_read(path).split('\n')
    try:
        b = safe_read(path + '.1').split('\n')
    except IOError:
        session.flash = 'Other file, no longer there'
        redirect(URL('edit', args=request.args))

    d = difflib.ndiff(a, b)

    def leading(line):
        """  """

        # TODO: we really need to comment this
        z = ''
        for (k, c) in enumerate(line):
            if c == ' ':
                z += '&nbsp;'
            elif c == ' \t':
                z += '&nbsp;'
            elif k == 0 and c == '?':
                pass
            else:
                break

        return XML(z)

    def getclass(item):
        """ Determine item class """

        if item[0] == ' ':
            return 'normal'
        if item[0] == '+':
            return 'plus'
        if item[0] == '-':
            return 'minus'

    if request.vars:
        c = ''.join([item[2:] for (i, item) in enumerate(d) if item[0] \
                     == ' ' or 'line%i' % i in request.vars])
        safe_write(path, c)
        session.flash = 'files merged'
        redirect(URL('edit', args=request.args))
    else:
        # Making the short circuit compatible with <= python2.4
        gen_data = lambda index,item: not item[:1] in ['+','-'] and "" \
                   or INPUT(_type='checkbox',
                            _name='line%i' % index,
                            value=item[0] == '+')

        diff = TABLE(*[TR(TD(gen_data(i,item)),
                          TD(item[0]),
                          TD(leading(item[2:]),
                          TT(item[2:].rstrip())), _class=getclass(item))
                       for (i, item) in enumerate(d) if item[0] != '?'])

    return dict(diff=diff, filename=filename)


def edit_language():
    """ Edit language file """
    app = get_app()
    filename = '/'.join(request.args)
    from gluon.languages import read_dict, write_dict
    strings = read_dict(apath(filename, r=request))
    keys = sorted(strings.keys(),lambda x,y: cmp(x.lower(), y.lower()))
    rows = []
    rows.append(H2(T('Original/Translation')))

    for key in keys:
        name = md5_hash(key)
        if key==strings[key]:
            _class='untranslated'
        else:
            _class='translated'
        if len(key) <= 40:
            elem = INPUT(_type='text', _name=name,value=strings[key],
                         _size=70,_class=_class)
        else:
            elem = TEXTAREA(_name=name, value=strings[key], _cols=70,
                            _rows=5, _class=_class)

        # Making the short circuit compatible with <= python2.4
        k = (strings[key] != key) and key or B(key)

        rows.append(P(k, BR(), elem, TAG.BUTTON(T('delete'),
                            _onclick='return delkey("%s")' % name), _id=name))

    rows.append(INPUT(_type='submit', _value=T('update')))
    form = FORM(*rows)
    if form.accepts(request.vars, keepvalues=True):
        strs = dict()
        for key in keys:
            name = md5_hash(key)
            if form.vars[name]==chr(127): continue
            strs[key] = form.vars[name]
        write_dict(apath(filename, r=request), strs)
        session.flash = T('file saved on %(time)s', dict(time=time.ctime()))
        redirect(URL(r=request,args=request.args))
    return dict(app=request.args[0], filename=filename, form=form)


def about():
    """ Read about info """
    app = get_app()
    # ## check if file is not there
    about = safe_read(apath('%s/ABOUT' % app, r=request))
    license = safe_read(apath('%s/LICENSE' % app, r=request))
    return dict(app=app, about=MARKMIN(about), license=MARKMIN(license))


def design():
    """ Application design handler """
    app = get_app()

    if not response.flash and app == request.application:
        msg = T('ATTENTION: you cannot edit the running application!')
        response.flash = msg

    if request.vars.pluginfile!=None and not isinstance(request.vars.pluginfile,str):
        filename=os.path.basename(request.vars.pluginfile.filename)
        if plugin_install(app, request.vars.pluginfile.file,
                          request, filename):
            session.flash = T('new plugin installed')
            redirect(URL('design',args=app))
        else:
            session.flash = \
                T('unable to create application "%s"', request.vars.filename)
        redirect(URL(r=request))
    elif isinstance(request.vars.pluginfile,str):
        session.flash = T('plugin not specified')
        redirect(URL(r=request))


    # If we have only pyc files it means that
    # we cannot design
    if os.path.exists(apath('%s/compiled' % app, r=request)):
        session.flash = \
            T('application is compiled and cannot be designed')
        redirect(URL('site'))

    # Get all models
    models = listdir(apath('%s/models/' % app, r=request), '.*\.py$')
    models=[x.replace('\\','/') for x in models]
    defines = {}
    for m in models:
        data = safe_read(apath('%s/models/%s' % (app, m), r=request))
        defines[m] = regex_tables.findall(data)
        defines[m].sort()

    # Get all controllers
    controllers = sorted(listdir(apath('%s/controllers/' % app, r=request), '.*\.py$'))
    controllers = [x.replace('\\','/') for x in controllers]
    functions = {}
    for c in controllers:
        data = safe_read(apath('%s/controllers/%s' % (app, c), r=request))
        items = regex_expose.findall(data)
        functions[c] = items

    # Get all views
    views = sorted(listdir(apath('%s/views/' % app, r=request), '[\w/\-]+\.\w+$'))
    views = [x.replace('\\','/') for x in views]
    extend = {}
    include = {}
    for c in views:
        data = safe_read(apath('%s/views/%s' % (app, c), r=request))
        items = regex_extend.findall(data)

        if items:
            extend[c] = items[0][1]

        items = regex_include.findall(data)
        include[c] = [i[1] for i in items]

    # Get all modules
    modules = listdir(apath('%s/modules/' % app, r=request), '.*\.py$')
    modules = modules=[x.replace('\\','/') for x in modules]
    modules.sort()

    # Get all static files
    statics = listdir(apath('%s/static/' % app, r=request), '[^\.#].*')
    statics = [x.replace('\\','/') for x in statics]
    statics.sort()

    # Get all languages
    languages = listdir(apath('%s/languages/' % app, r=request), '[\w-]*\.py')

    #Get crontab
    cronfolder = apath('%s/cron' % app, r=request)
    if not os.path.exists(cronfolder): os.mkdir(cronfolder)
    crontab = apath('%s/cron/crontab' % app, r=request)
    if not os.path.exists(crontab):
        safe_write(crontab, '#crontab')

    plugins=[]
    def filter_plugins(items,plugins):
        plugins+=[item[7:].split('/')[0].split('.')[0] for item in items if item.startswith('plugin_')]
        plugins[:]=list(set(plugins))
        plugins.sort()
        return [item for item in items if not item.startswith('plugin_')]

    return dict(app=app,
                models=filter_plugins(models,plugins),
                defines=defines,
                controllers=filter_plugins(controllers,plugins),
                functions=functions,
                views=filter_plugins(views,plugins),
                modules=filter_plugins(modules,plugins),
                extend=extend,
                include=include,
                statics=filter_plugins(statics,plugins),
                languages=languages,
                crontab=crontab,
                plugins=plugins)

def delete_plugin():
    """ Object delete handler """
    app=request.args(0)
    plugin = request.args(1)
    plugin_name='plugin_'+plugin
    if 'nodelete' in request.vars:
        redirect(URL('design',args=app))
    elif 'delete' in request.vars:
        try:
            for folder in ['models','views','controllers','static','modules']:
                path=os.path.join(apath(app,r=request),folder)
                for item in os.listdir(path):
                    if item.startswith(plugin_name):
                        filename=os.path.join(path,item)
                        if os.path.isdir(filename):
                            shutil.rmtree(filename)
                        else:
                            os.unlink(filename)
            session.flash = T('plugin "%(plugin)s" deleted',
                              dict(plugin=plugin))
        except Exception:
            session.flash = T('unable to delete file plugin "%(plugin)s"',
                              dict(plugin=plugin))
        redirect(URL('design',args=request.args(0)))
    return dict(plugin=plugin)

def plugin():
    """ Application design handler """
    app = get_app()
    plugin = request.args(1)

    if not response.flash and app == request.application:
        msg = T('ATTENTION: you cannot edit the running application!')
        response.flash = msg

    # If we have only pyc files it means that
    # we cannot design
    if os.path.exists(apath('%s/compiled' % app, r=request)):
        session.flash = \
            T('application is compiled and cannot be designed')
        redirect(URL('site'))

    # Get all models
    models = listdir(apath('%s/models/' % app, r=request), '.*\.py$')
    models=[x.replace('\\','/') for x in models]
    defines = {}
    for m in models:
        data = safe_read(apath('%s/models/%s' % (app, m), r=request))
        defines[m] = regex_tables.findall(data)
        defines[m].sort()

    # Get all controllers
    controllers = sorted(listdir(apath('%s/controllers/' % app, r=request), '.*\.py$'))
    controllers = [x.replace('\\','/') for x in controllers]
    functions = {}
    for c in controllers:
        data = safe_read(apath('%s/controllers/%s' % (app, c), r=request))
        items = regex_expose.findall(data)
        functions[c] = items

    # Get all views
    views = sorted(listdir(apath('%s/views/' % app, r=request), '[\w/\-]+\.\w+$'))
    views = [x.replace('\\','/') for x in views]
    extend = {}
    include = {}
    for c in views:
        data = safe_read(apath('%s/views/%s' % (app, c), r=request))
        items = regex_extend.findall(data)
        if items:
            extend[c] = items[0][1]

        items = regex_include.findall(data)
        include[c] = [i[1] for i in items]

    # Get all modules
    modules = listdir(apath('%s/modules/' % app, r=request), '.*\.py$')
    modules = modules=[x.replace('\\','/') for x in modules]
    modules.sort()

    # Get all static files
    statics = listdir(apath('%s/static/' % app, r=request), '[^\.#].*')
    statics = [x.replace('\\','/') for x in statics]
    statics.sort()

    # Get all languages
    languages = listdir(apath('%s/languages/' % app, r=request), '[\w-]*\.py')

    #Get crontab
    crontab = apath('%s/cron/crontab' % app, r=request)
    if not os.path.exists(crontab):
        safe_write(crontab, '#crontab')

    def filter_plugins(items):
        regex=re.compile('^plugin_'+plugin+'(/.*|\..*)?$')
        return [item for item in items if regex.match(item)]

    return dict(app=app,
                models=filter_plugins(models),
                defines=defines,
                controllers=filter_plugins(controllers),
                functions=functions,
                views=filter_plugins(views),
                modules=filter_plugins(modules),
                extend=extend,
                include=include,
                statics=filter_plugins(statics),
                languages=languages,
                crontab=crontab)


def create_file():
    """ Create files handler """
    try:
        app = get_app(name=request.vars.location.split('/')[0])
        path = apath(request.vars.location, r=request)
        filename = re.sub('[^\w./-]+', '_', request.vars.filename)

        if path[-11:] == '/languages/':
            # Handle language files
            if len(filename) == 0:
                raise SyntaxError
            if not filename[-3:] == '.py':
                filename += '.py'
            app = path.split('/')[-3]
            path=os.path.join(apath(app, r=request),'languages',filename)
            if not os.path.exists(path):
                safe_write(path, '')
            findT(apath(app, r=request), filename[:-3])
            session.flash = T('language file "%(filename)s" created/updated',
                              dict(filename=filename))
            redirect(request.vars.sender)

        elif path[-8:] == '/models/':
            # Handle python models
            if not filename[-3:] == '.py':
                filename += '.py'

            if len(filename) == 3:
                raise SyntaxError

            text = '# coding: utf8\n'

        elif path[-13:] == '/controllers/':
            # Handle python controllers
            if not filename[-3:] == '.py':
                filename += '.py'

            if len(filename) == 3:
                raise SyntaxError

            text = '# coding: utf8\n# %s\ndef index(): return dict(message="hello from %s")'
            text = text % (T('try something like'), filename)

        elif path[-7:] == '/views/':
            if request.vars.plugin and not filename.startswith('plugin_%s/' % request.vars.plugin):
                filename = 'plugin_%s/%s' % (request.vars.plugin, filename)
            # Handle template (html) views
            if filename.find('.')<0:
                filename += '.html'
            extension = filename.split('.')[-1].lower()

            if len(filename) == 5:
                raise SyntaxError

            msg = T('This is the %(filename)s template',
                    dict(filename=filename))
            if extension == 'html':
                text = dedent("""
                   {{extend 'layout.html'}}
                   <h1>%s</h1>
                   {{=BEAUTIFY(response._vars)}}""" % msg)
            else:
                generic = os.path.join(path,'generic.'+extension)
                if os.path.exists(generic):
                    text = read_file(generic)
                else:
                    text = ''

        elif path[-9:] == '/modules/':
            if request.vars.plugin and not filename.startswith('plugin_%s/' % request.vars.plugin):
                filename = 'plugin_%s/%s' % (request.vars.plugin, filename)
            # Handle python module files
            if not filename[-3:] == '.py':
                filename += '.py'

            if len(filename) == 3:
                raise SyntaxError

            text = dedent("""
                   #!/usr/bin/env python
                   # coding: utf8
                   from gluon import *\n""")

        elif path[-8:] == '/static/':
            if request.vars.plugin and not filename.startswith('plugin_%s/' % request.vars.plugin):
                filename = 'plugin_%s/%s' % (request.vars.plugin, filename)
            text = ''
        else:
            redirect(request.vars.sender)

        full_filename = os.path.join(path, filename)
        dirpath = os.path.dirname(full_filename)

        if not os.path.exists(dirpath):
            os.makedirs(dirpath)

        if os.path.exists(full_filename):
            raise SyntaxError

        safe_write(full_filename, text)
        session.flash = T('file "%(filename)s" created',
                          dict(filename=full_filename[len(path):]))
        redirect(URL('edit',
                 args=[os.path.join(request.vars.location, filename)]))
    except Exception, e:
        if not isinstance(e,HTTP):
            session.flash = T('cannot create file')

    redirect(request.vars.sender)


def upload_file():
    """ File uploading handler """

    try:
        filename = None
        app = get_app(name=request.vars.location.split('/')[0])
        path = apath(request.vars.location, r=request)

        if request.vars.filename:
            filename = re.sub('[^\w\./]+', '_', request.vars.filename)
        else:
            filename = os.path.split(request.vars.file.filename)[-1]

        if path[-8:] == '/models/' and not filename[-3:] == '.py':
            filename += '.py'

        if path[-9:] == '/modules/' and not filename[-3:] == '.py':
            filename += '.py'

        if path[-13:] == '/controllers/' and not filename[-3:] == '.py':
            filename += '.py'

        if path[-7:] == '/views/' and not filename[-5:] == '.html':
            filename += '.html'

        if path[-11:] == '/languages/' and not filename[-3:] == '.py':
            filename += '.py'

        filename = os.path.join(path, filename)
        dirpath = os.path.dirname(filename)

        if not os.path.exists(dirpath):
            os.makedirs(dirpath)

        safe_write(filename, request.vars.file.file.read(), 'wb')
        session.flash = T('file "%(filename)s" uploaded',
                          dict(filename=filename[len(path):]))
    except Exception:
        if filename:
            d = dict(filename = filename[len(path):])
        else:
            d = dict(filename = 'unkown')
        session.flash = T('cannot upload file "%(filename)s"', d)

    redirect(request.vars.sender)


def errors():
    """ Error handler """
    import operator
    import os
    import pickle
    import hashlib

    app = get_app()

    method = request.args(1) or 'new'


    if method == 'new':
        errors_path = apath('%s/errors' % app, r=request)

        delete_hashes = []
        for item in request.vars:
            if item[:7] == 'delete_':
                delete_hashes.append(item[7:])

        hash2error = dict()

        for fn in listdir(errors_path, '^\w.*'):
            fullpath = os.path.join(errors_path, fn)
            if not os.path.isfile(fullpath): continue
            try:
                fullpath_file = open(fullpath, 'r')
                try:
                    error = pickle.load(fullpath_file)
                finally:
                    fullpath_file.close()
            except IOError:
                continue

            hash = hashlib.md5(error['traceback']).hexdigest()

            if hash in delete_hashes:
                os.unlink(fullpath)
            else:
                try:
                    hash2error[hash]['count'] += 1
                except KeyError:
                    error_lines = error['traceback'].split("\n")
                    last_line = error_lines[-2]
                    error_causer = os.path.split(error['layer'])[1]
                    hash2error[hash] = dict(count=1, pickel=error,
                                            causer=error_causer,
                                            last_line=last_line,
                                            hash=hash,ticket=fn)

        decorated = [(x['count'], x) for x in hash2error.values()]
        decorated.sort(key=operator.itemgetter(0), reverse=True)

        return dict(errors = [x[1] for x in decorated], app=app, method=method)
    else:
        for item in request.vars:
            if item[:7] == 'delete_':
                os.unlink(apath('%s/errors/%s' % (app, item[7:]), r=request))
        func = lambda p: os.stat(apath('%s/errors/%s' % \
                                           (app, p), r=request)).st_mtime
        tickets = sorted(listdir(apath('%s/errors/' % app, r=request), '^\w.*'),
                         key=func,
                         reverse=True)

        return dict(app=app, tickets=tickets, method=method)


def make_link(path):
    """ Create a link from a path """
    tryFile = path.replace('\\', '/')

    if os.path.isabs(tryFile) and os.path.isfile(tryFile):
        (folder, filename) = os.path.split(tryFile)
        (base, ext) = os.path.splitext(filename)
        app = get_app()

        editable = {'controllers': '.py', 'models': '.py', 'views': '.html'}
        for key in editable.keys():
            check_extension = folder.endswith("%s/%s" % (app,key))
            if ext.lower() == editable[key] and check_extension:
                return A('"' + tryFile + '"',
                         _href=URL(r=request,
                         f='edit/%s/%s/%s' % (app, key, filename))).xml()
    return ''


def make_links(traceback):
    """ Make links using the given traceback """

    lwords = traceback.split('"')

    # Making the short circuit compatible with <= python2.4
    result = (len(lwords) != 0) and lwords[0] or ''

    i = 1

    while i < len(lwords):
        link = make_link(lwords[i])

        if link == '':
            result += '"' + lwords[i]
        else:
            result += link

            if i + 1 < len(lwords):
                result += lwords[i + 1]
                i = i + 1

        i = i + 1

    return result


class TRACEBACK(object):
    """ Generate the traceback """

    def __init__(self, text):
        """ TRACEBACK constructor """

        self.s = make_links(CODE(text).xml())

    def xml(self):
        """ Returns the xml """

        return self.s


def ticket():
    """ Ticket handler """

    if len(request.args) != 2:
        session.flash = T('invalid ticket')
        redirect(URL('site'))

    app = get_app()
    myversion = request.env.web2py_version
    ticket = request.args[1]
    e = RestrictedError()
    e.load(request, app, ticket)

    return dict(app=app,
                ticket=ticket,
                output=e.output,
                traceback=(e.traceback and TRACEBACK(e.traceback)),
                snapshot=e.snapshot,
                code=e.code,
                layer=e.layer,
                myversion=myversion)

def error():
    """ Generate a ticket (for testing) """
    raise RuntimeError('admin ticket generator at your service')

def update_languages():
    """ Update available languages """

    app = get_app()
    update_all_languages(apath(app, r=request))
    session.flash = T('Language files (static strings) updated')
    redirect(URL('design',args=app))

def twitter():
    session.forget()
    session._unlock(response)
    import gluon.tools
    import gluon.contrib.simplejson as sj
    try:
        if TWITTER_HASH:
            page = gluon.tools.fetch('http://twitter.com/%s?format=json'%TWITTER_HASH)
            return sj.loads(page)['#timeline']
        else:
            return 'disabled'
    except Exception, e:
        return DIV(T('Unable to download because:'),BR(),str(e))

def user():
    if MULTI_USER_MODE:
        if not db(db.auth_user).count():
            settings.auth.registration_requires_approval = False
        return dict(form=auth())
    else:
        return dict(form=T("Disabled"))

def reload_routes():
   """ Reload routes.py """
   gluon.rewrite.load()
   redirect(URL('site'))

########NEW FILE########
__FILENAME__ = gae
### this works on linux only

import re
try:
    import fcntl
    import subprocess
    import signal
    import os
    import shutil
    from gluon.fileutils import read_file, write_file    
except:
    session.flash='sorry, only on Unix systems'
    redirect(URL(request.application,'default','site'))

forever=10**8

def kill():
    p = cache.ram('gae_upload',lambda:None,forever)
    if not p or p.poll()!=None:
        return 'oops'
    os.kill(p.pid, signal.SIGKILL)
    cache.ram('gae_upload',lambda:None,-1)

class EXISTS(object):
    def __init__(self, error_message='file not found'):
        self.error_message = error_message
    def __call__(self, value):
        if os.path.exists(value):
            return (value,None)
        return (value,self.error_message)

def deploy():
    regex = re.compile('^\w+$')
    apps = sorted(file for file in os.listdir(apath(r=request)) if regex.match(file))
    form = SQLFORM.factory(
        Field('appcfg',default=GAE_APPCFG,label='Path to appcfg.py',
              requires=EXISTS(error_message=T('file not found'))),
        Field('google_application_id',requires=IS_ALPHANUMERIC()),
        Field('applications','list:string',
              requires=IS_IN_SET(apps,multiple=True),
              label=T('web2py apps to deploy')),
        Field('email',requires=IS_EMAIL(),label=T('GAE Email')),
        Field('password','password',requires=IS_NOT_EMPTY(),label=T('GAE Password')))
    cmd = output = errors= ""
    if form.accepts(request,session):
        try:
            kill()
        except:
            pass
        ignore_apps = [item for item in apps \
                           if not item in form.vars.applications]
        regex = re.compile('\(applications/\(.*')
        yaml = apath('../app.yaml', r=request)
        if not os.path.exists(yaml):
            example = apath('../app.example.yaml', r=request)
            shutil.copyfile(example,yaml)            
        data = read_file(yaml)
        data = re.sub('application:.*','application: %s' % form.vars.google_application_id,data)
        data = regex.sub('(applications/(%s)/.*)|' % '|'.join(ignore_apps),data)
        write_file(yaml, data)

        path = request.env.applications_parent
        cmd = '%s --email=%s --passin update %s' % \
            (form.vars.appcfg, form.vars.email, path)
        p = cache.ram('gae_upload',
                      lambda s=subprocess,c=cmd:s.Popen(c, shell=True,
                                                        stdin=s.PIPE,
                                                        stdout=s.PIPE,
                                                        stderr=s.PIPE, close_fds=True),-1)
        p.stdin.write(form.vars.password+'\n')
        fcntl.fcntl(p.stdout.fileno(), fcntl.F_SETFL, os.O_NONBLOCK)
        fcntl.fcntl(p.stderr.fileno(), fcntl.F_SETFL, os.O_NONBLOCK)
    return dict(form=form,command=cmd)

def callback():
    p = cache.ram('gae_upload',lambda:None,forever)
    if not p or p.poll()!=None:
        return '<done/>'
    try:
        output = p.stdout.read()
    except:
        output=''
    try:
        errors = p.stderr.read()
    except:
        errors=''
    return (output+errors).replace('\n','<br/>')

########NEW FILE########
__FILENAME__ = mercurial
from gluon.fileutils import read_file, write_file

if DEMO_MODE or MULTI_USER_MODE:
    session.flash = T('disabled in demo mode')
    redirect(URL('default','site'))
if not have_mercurial:
    session.flash=T("Sorry, could not find mercurial installed")
    redirect(URL('default','design',args=request.args(0)))

_hgignore_content = """\
syntax: glob
*~
*.pyc
*.pyo
*.bak
*.bak2
cache/*
private/*
uploads/*
databases/*
sessions/*
errors/*
"""

def hg_repo(path):
    import os
    uio = ui.ui()
    uio.quiet = True
    if not os.environ.get('HGUSER') and not uio.config("ui", "username"):
        os.environ['HGUSER'] = 'web2py@localhost'
    try:
        repo = hg.repository(ui=uio, path=path)
    except:
        repo = hg.repository(ui=uio, path=path, create=True)
    hgignore = os.path.join(path, '.hgignore')
    if not os.path.exists(hgignore):
        write_file(hgignore, _hgignore_content)
    return repo

def commit():
    app = request.args(0)
    path = apath(app, r=request)
    repo = hg_repo(path)
    form = FORM('Comment:',INPUT(_name='comment',requires=IS_NOT_EMPTY()),
                INPUT(_type='submit',_value='Commit'))
    if form.accepts(request.vars,session):
        oldid = repo[repo.lookup('.')]
        cmdutil.addremove(repo)
        repo.commit(text=form.vars.comment)
        if repo[repo.lookup('.')] == oldid:
            response.flash = 'no changes'
    try:
        files = TABLE(*[TR(file) for file in repo[repo.lookup('.')].files()])
        changes = TABLE(TR(TH('revision'),TH('description')))
        for change in repo.changelog:
            ctx=repo.changectx(change)
            revision, description = ctx.rev(), ctx.description()
            changes.append(TR(A(revision,_href=URL('revision',
                                                   args=(app,revision))),
                              description))
    except:
        files = []
        changes = []
    return dict(form=form,files=files,changes=changes,repo=repo)

def revision():
    app = request.args(0)
    path = apath(app, r=request)
    repo = hg_repo(path)
    revision = request.args(1)
    ctx=repo.changectx(revision)
    form=FORM(INPUT(_type='submit',_value='revert'))
    if form.accepts(request.vars):
        hg.update(repo, revision)
        session.flash = "reverted to revision %s" % ctx.rev()
        redirect(URL('default','design',args=app))
    return dict(
        files=ctx.files(),
        rev=str(ctx.rev()),
        desc=ctx.description(),
        form=form
        )

########NEW FILE########
__FILENAME__ = shell
import sys
import cStringIO
import gluon.contrib.shell
import code, thread
from gluon.shell import env

if DEMO_MODE or MULTI_USER_MODE:
    session.flash = T('disabled in demo mode')
    redirect(URL('default','site'))

FE=10**9

def index():
    app = request.args(0) or 'admin'
    reset()
    return dict(app=app)

def callback():
    app = request.args[0]
    command = request.vars.statement
    escape = command[:1]!='!'
    history = session['history:'+app] = session.get('history:'+app,gluon.contrib.shell.History())
    if not escape:
        command = command[1:]
    if command == '%reset':
        reset()
        return '*** reset ***'
    elif command[0] == '%':
        try:
            command=session['commands:'+app][int(command[1:])]
        except ValueError:
            return ''
    session['commands:'+app].append(command)
    environ=env(app,True)
    output = gluon.contrib.shell.run(history,command,environ)
    k = len(session['commands:'+app]) - 1
    #output = PRE(output)
    #return TABLE(TR('In[%i]:'%k,PRE(command)),TR('Out[%i]:'%k,output))
    return 'In [%i] : %s%s\n' % (k + 1, command, output)

def reset():
    app = request.args(0) or 'admin'
    session['commands:'+app] = []
    session['history:'+app] = gluon.contrib.shell.History()
    return 'done'

########NEW FILE########
__FILENAME__ = toolbar
import os
from gluon.settings import global_settings, read_file
#

def index():
    app = request.args(0)
    return dict(app=app)

def profiler():
    """
    to use the profiler start web2py with -F profiler.log
    """
    KEY = 'web2py_profiler_size'
    filename = global_settings.cmd_options.profiler_filename
    data = 'profiler disabled'
    if filename:
        if  KEY in request.cookies:
            size = int(request.cookies[KEY].value)
        else:
            size = 0
        if os.path.exists(filename):
            data = read_file('profiler.log','rb')
            if size<len(data): 
                data = data[size:]
            else: 
                size=0
            size += len(data)
            response.cookies[KEY] = size
    return data

########NEW FILE########
__FILENAME__ = wizard
# -*- coding: utf-8 -*-

import os, uuid, re, pickle, urllib, glob
from gluon.admin import app_create, plugin_install
from gluon.fileutils import abspath, read_file, write_file

def reset(session):
    session.app={
        'name':'',
        'params':[('title','My New App'),
                  ('subtitle','powered by web2py'),
                  ('author','you'),
                  ('author_email','you@example.com'),
                  ('keywords',''),
                  ('description',''),
                  ('layout_theme','Default'),
                  ('database_uri','sqlite://storage.sqlite'),
                  ('security_key',str(uuid.uuid4())),
                  ('email_server','localhost'),
                  ('email_sender','you@example.com'),
                  ('email_login',''),
                  ('login_method','local'),
                  ('login_config',''),
                  ('plugins',[])],
        'tables':['auth_user'],
        'table_auth_user':['username','first_name','last_name','email','password'],
        'pages':['index','error'],
        'page_index':'# Welcome to my new app',
        'page_error':'# Error: the document does not exist',
        }

if not session.app: reset(session)

def listify(x):
    if not isinstance(x,(list,tuple)):
        return x and [x] or []
    return x

def clean(name):
    return re.sub('\W+','_',name.strip().lower())

def index():
    response.view='wizard/step.html'
    reset(session)
    apps=os.listdir(os.path.join(request.folder,'..'))
    form=SQLFORM.factory(Field('name',requires=[IS_NOT_EMPTY(),IS_ALPHANUMERIC()]))
    if form.accepts(request.vars):
        app = form.vars.name
        session.app['name'] = app
        if MULTI_USER_MODE and db(db.app.name==app)(db.app.owner!=auth.user.id).count():
            session.flash = 'App belongs already to other user'
        elif app in apps:
            meta = os.path.normpath(\
                os.path.join(os.path.normpath(request.folder),
                             '..',app,'wizard.metadata'))
            if os.path.exists(meta):
                try:
                    metafile = open(meta,'rb')
                    try:
                        session.app = pickle.load(metafile)
                    finally:
                        metafile.close()
                    session.flash = "The app exists, was created by wizard, continue to overwrite!"
                except:
                    session.flash = "The app exists, was NOT created by wizard, continue to overwrite!"
        redirect(URL('step1'))
    return dict(step='Start',form=form)


def step1():
    from gluon.contrib.simplejson import loads
    import urllib
    if not session.themes:
        url=LAYOUTS_APP+'/default/layouts.json'
        try:
            data = urllib.urlopen(url).read()
            session.themes = ['Default'] + loads(data)['layouts']
        except:
            session.themes = ['Default']
    themes = session.themes
    if not session.plugins:
        url = PLUGINS_APP+'/default/plugins.json'
        try:
            data = urllib.urlopen(url).read()
            session.plugins = loads(data)['plugins']
        except:
            session.plugins = []
    plugins = [x.split('.')[2] for x in session.plugins]
    response.view='wizard/step.html'
    params = dict(session.app['params'])
    form=SQLFORM.factory(
                Field('title',default=params.get('title',None),
                                      requires=IS_NOT_EMPTY()),
                Field('subtitle',default=params.get('subtitle',None)),
                Field('author',default=params.get('author',None)),
                Field('author_email',default=params.get('author_email',None)),
                Field('keywords',default=params.get('keywords',None)),
                Field('description','text',
                      default=params.get('description',None)),
                Field('layout_theme',requires=IS_IN_SET(themes),
                      default=params.get('layout_theme',themes[0])),
                Field('database_uri',default=params.get('database_uri',None)),
                Field('security_key',default=params.get('security_key',None)),
                Field('email_server',default=params.get('email_server',None)),
                Field('email_sender',default=params.get('email_sender',None)),
                Field('email_login',default=params.get('email_login',None)),
                Field('login_method',requires=IS_IN_SET(('local','janrain')),
                      default=params.get('login_method','local')),
                Field('login_config',default=params.get('login_config',None)),
                Field('plugins','list:string',requires=IS_IN_SET(plugins,multiple=True)))

    if form.accepts(request.vars):
        session.app['params']=[(key,form.vars.get(key,None))
                               for key,value in session.app['params']]
        redirect(URL('step2'))
    return dict(step='1: Setting Parameters',form=form)

def step2():
    response.view='wizard/step.html'
    form=SQLFORM.factory(Field('table_names','list:string',
                               default=session.app['tables']))
    if form.accepts(request.vars):
        table_names = [clean(t) for t in listify(form.vars.table_names) if t.strip()]
        if [t for t in table_names if t.startswith('auth_') and not t=='auth_user']:
            form.error.table_names = T('invalid table names (auth_* tables already defined)')
        else:
            session.app['tables']=table_names
            for table in session.app['tables']:
                if not 'table_'+table in session.app:
                    session.app['table_'+table]=['name']
                if not table=='auth_user':
                    for key in ['create','read','update','select','search']:
                        name = table+'_'+key
                        if not name in session.app['pages']:
                            session.app['pages'].append(name)
                            session.app['page_'+name]='## %s %s' % (key.capitalize(),table)
            if session.app['tables']:
                redirect(URL('step3',args=0))
            else:
                redirect(URL('step4'))
    return dict(step='2: Tables',form=form)

def step3():
    response.view='wizard/step.html'
    n=int(request.args(0) or 0)
    m=len(session.app['tables'])
    if n>=m: redirect(URL('step2'))
    table=session.app['tables'][n]
    form=SQLFORM.factory(Field('field_names','list:string',
                               default=session.app.get('table_'+table,[])))
    if form.accepts(request.vars) and form.vars.field_names:
        fields=listify(form.vars.field_names)
        if table=='auth_user':
            for field in ['first_name','last_name','username','email','password']:
                if not field in fields:
                    fields.append(field)
        session.app['table_'+table]=[t.strip().lower()
                                       for t in listify(form.vars.field_names)
                                       if t.strip()]
        try:
            tables=sort_tables(session.app['tables'])
        except RuntimeError:
            response.flash=T('invalid circual reference')
        else:
            if n<m-1:
                redirect(URL('step3',args=n+1))
            else:
                redirect(URL('step4'))
    return dict(step='3: Fields for table "%s" (%s of %s)' % (table,n+1,m),table=table,form=form)

def step4():
    response.view='wizard/step.html'
    form=SQLFORM.factory(Field('pages','list:string',
                               default=session.app['pages']))
    if form.accepts(request.vars):
        session.app['pages']=[clean(t)
                              for t in listify(form.vars.pages)
                              if t.strip()]
        if session.app['pages']:
            redirect(URL('step5',args=0))
        else:
            redirect(URL('step6'))
    return dict(step='4: Pages',form=form)

def step5():
    response.view='wizard/step.html'
    n=int(request.args(0) or 0)
    m=len(session.app['pages'])
    if n>=m: redirect(URL('step4'))
    page=session.app['pages'][n]
    markmin_url='http://web2py.com/examples/static/markmin.html'
    form=SQLFORM.factory(Field('content','text',
                               default=session.app.get('page_'+page,[]),
                               comment=A('use markmin',_href=markmin_url,_target='_blank')),
                         formstyle='table2cols')
    if form.accepts(request.vars):
        session.app['page_'+page]=form.vars.content
        if n<m-1:
            redirect(URL('step5',args=n+1))
        else:
            redirect(URL('step6'))
    return dict(step='5: View for page "%s" (%s of %s)' % (page,n+1,m),form=form)

def step6():
    response.view='wizard/step.html'
    params = dict(session.app['params'])
    app = session.app['name']
    form=SQLFORM.factory(
        Field('generate_model','boolean',default=True),
        Field('generate_controller','boolean',default=True),
        Field('generate_views','boolean',default=True),
        Field('generate_menu','boolean',default=True),
        Field('apply_layout','boolean',default=True),
        Field('erase_database','boolean',default=True),
        Field('populate_database','boolean',default=True))
    if form.accepts(request.vars):
        if DEMO_MODE:
            session.flash = T('Application cannot be generated in demo mode')
            redirect(URL('index'))
        create(form.vars)
        session.flash = 'Application %s created' % app
        redirect(URL('generated'))
    return dict(step='6: Generate app "%s"' % app,form=form)

def generated():
    return dict(app=session.app['name'])

def sort_tables(tables):
    import re
    regex = re.compile('(%s)' % '|'.join(tables))
    is_auth_user = 'auth_user' in tables
    d={}
    for table in tables:
        d[table]=[]
        for field in session.app['table_%s' % table]:
            d[table]+=regex.findall(field)
    tables=[]
    if is_auth_user:
        tables.append('auth_user')
    def append(table,trail=[]):
        if table in trail:
            raise RuntimeError
        for t in d[table]: append(t,trail=trail+[table])
        if not table in tables: tables.append(table)
    for table in d: append(table)
    return tables

def make_table(table,fields):
    rawtable=table
    if table!='auth_user': table='t_'+table
    s=''
    s+='\n'+'#'*40+'\n'
    s+="db.define_table('%s',\n" % table
    s+="    Field('id','id',\n"
    s+="          represent=lambda id:SPAN(id,' ',A('view',_href=URL('%s_read',args=id)))),\n"%rawtable
    first_field='id'
    for field in fields:
        items=[x.lower() for x in field.split()]
        has = {}
        keys = []
        for key in ['notnull','unique','integer','double','boolean','float',
                    'boolean', 'date','time','datetime','text','wiki',
                    'html','file','upload','image','true',
                    'hidden','readonly','writeonly','multiple',
                    'notempty','required']:
            if key in items[1:]:
                keys.append(key)
                has[key] = True
        tables = session.app['tables']
        refs = [t for t in tables if t in items]
        items = items[:1] + [x for x in items[1:] if not x in keys and not x in tables]
        barename = name = '_'.join(items)
        if table[:2]=='t_': name='f_'+name
        if first_field=='id': first_field=name

        ### determine field type
        ftype='string'
        deftypes={'integer':'integer','double':'double','boolean':'boolean',
                  'float':'double','bool':'boolean',
                  'date':'date','time':'time','datetime':'datetime',
                  'text':'text','file':'upload','image':'upload','upload':'upload',
                  'wiki':'text', 'html':'text'}
        for key,t in deftypes.items():
            if key in has:
                ftype = t
        if refs:
            key = refs[0]
            if not key=='auth_user': key='t_'+key
            if 'multiple' in has:
                ftype='list:reference %s' % key
            else:
                ftype='reference %s' % key
        if ftype=='string' and 'multiple' in has:
            ftype='list:string'
        elif ftype=='integer' and 'multiple' in has:
            ftype='list:integer'
        elif name=='password':
            ftype='password'
        s+="    Field('%s', type='%s'" % (name, ftype)

        ### determine field attributes
        if 'notnull' in has or 'notempty' in has or 'required' in has:
            s+=', notnull=True'
        if 'unique' in has:
            s+=', unique=True'
        if ftype=='boolean' and 'true' in has:
            s+=",\n          default=True"

        ### determine field representation
        if 'image' in has:
            s+=",\n          represent=lambda x: x and IMG(_alt='image',_src=URL('download',args=x), _width='200px') or ''"
        elif ftype in ('file','upload'):
            s+=",\n          represent=lambda x: x and A('download',_href=URL('download',args=x)) or ''"
        elif 'wiki' in has:
            s+=",\n          represent=lambda x: MARKMIN(x)"
            s+=",\n          comment='WIKI (markmin)'"
        elif 'html' in has:
            s+=",\n          represent=lambda x: XML(x,sanitize=True)"
            s+=",\n          comment='HTML (sanitized)'"
        ### determine field access
        if name=='password' or 'writeonly' in has:
            s+=",\n          readable=False"
        elif 'hidden' in has:
            s+=",\n          writable=False, readable=False"
        elif 'readonly' in has:
            s+=",\n          writable=False"

        ### make up a label
        s+=",\n          label=T('%s')),\n" % \
            ' '.join(x.capitalize() for x in barename.split('_'))
    if table!='auth_user':
        s+="    Field('is_active','boolean',default=True,\n"
        s+="          label=T('Active'),writable=False,readable=False),\n"
    s+="    Field('created_on','datetime',default=request.now,\n"
    s+="          label=T('Created On'),writable=False,readable=False),\n"
    s+="    Field('modified_on','datetime',default=request.now,\n"
    s+="          label=T('Modified On'),writable=False,readable=False,\n"
    s+="          update=request.now),\n"
    if not table=='auth_user' and 'auth_user' in session.app['tables']:
        s+="    Field('created_by',db.auth_user,default=auth.user_id,\n"
        s+="          label=T('Created By'),writable=False,readable=False),\n"
        s+="    Field('modified_by',db.auth_user,default=auth.user_id,\n"
        s+="          label=T('Modified By'),writable=False,readable=False,\n"
        s+="          update=auth.user_id),\n"
    elif table=='auth_user':
        s+="    Field('registration_key',default='',\n"
        s+="          writable=False,readable=False),\n"
        s+="    Field('reset_password_key',default='',\n"
        s+="          writable=False,readable=False),\n"
        s+="    Field('registration_id',default='',\n"
        s+="          writable=False,readable=False),\n"
    s+="    format='%("+first_field+")s',\n"
    s+="    migrate=settings.globals.migrate)\n\n"
    if table=='auth_user':
        s+="""
db.auth_user.first_name.requires = IS_NOT_EMPTY(error_message=auth.messages.is_empty)
db.auth_user.last_name.requires = IS_NOT_EMPTY(error_message=auth.messages.is_empty)
db.auth_user.password.requires = CRYPT(key=settings.auth.hmac_key)
db.auth_user.username.requires = IS_NOT_IN_DB(db, db.auth_user.username)
db.auth_user.registration_id.requires = IS_NOT_IN_DB(db, db.auth_user.registration_id)
db.auth_user.email.requires = (IS_EMAIL(error_message=auth.messages.invalid_email),
                               IS_NOT_IN_DB(db, db.auth_user.email))
"""
    else:
        s+="db.define_table('%s_archive',db.%s,Field('current_record','reference %s'))\n" % (table,table,table)
    return s


def fix_db(filename):
    params = dict(session.app['params'])
    content = read_file(filename,'rb')
    if 'auth_user' in session.app['tables']:
        auth_user = make_table('auth_user',session.app['table_auth_user'])
        content = content.replace('sqlite://storage.sqlite',
                                params['database_uri'])
        content = content.replace('auth.define_tables()',\
            auth_user+'auth.define_tables(migrate = settings.globals.migrate)')
    content += """
mail.settings.server = settings.globals.email_server
mail.settings.sender = settings.globals.email_sender
mail.settings.login = settings.globals.email_login
"""
    if params['login_method']=='janrain':
        content+="""
from gluon.contrib.login_methods.rpx_account import RPXAccount
settings.auth.actions_disabled=['register','change_password','request_reset_password']
settings.auth.login_form = RPXAccount(request,
    api_key = settings.globals.login_config.split(':')[-1],
    domain = settings.globals.login_config.split(':')[0],
    url = "http://%s/%s/default/user/login" % (request.env.http_host,request.application))
"""
    write_file(filename, content, 'wb')

def make_menu(pages):
    s="""
response.title = settings.globals.title
response.subtitle = settings.globals.subtitle
response.meta.author = '%s <%s>' % (settings.globals.author, settings.globals.author_email)
response.meta.keywords = settings.globals.keywords
response.meta.description = settings.globals.description
response.menu = [
"""
    for page in pages:
        if not page.endswith('_read') and \
                not page.endswith('_update') and \
                not page.endswith('_search') and \
                not page.startswith('_') and not page.startswith('error'):
            s+="    (T('%s'),URL('default','%s')==URL(),URL('default','%s'),[]),\n" % \
                (' '.join(x.capitalize() for x in page.split('_')),page,page)
    s+=']'
    return s

def make_page(page,contents):
    if 'auth_user' in session.app['tables'] and not page in ('index','error'):
        s="@auth.requires_login()\ndef %s():\n" % page
    else:
        s="def %s():\n" % page
    items=page.rsplit('_',1)
    if items[0] in session.app['tables'] and len(items)==2:
        t=items[0]
        if items[1]=='read':
            s+="    record = db.t_%s(request.args(0)) or redirect(URL('error'))\n" % t
            s+="    form=crud.read(db.t_%s,record)\n" % t
            s+="    return dict(form=form)\n\n"
        elif items[1]=='update':
            s+="    record = db.t_%s(request.args(0),is_active=True) or redirect(URL('error'))\n" % t
            s+="    form=crud.update(db.t_%s,record,next='%s_read/[id]',\n"  % (t,t)
            s+="                     ondelete=lambda form: redirect(URL('%s_select')),\n" % t
            s+="                     onaccept=crud.archive)\n"
            s+="    return dict(form=form)\n\n"
        elif items[1]=='create':
            s+="    form=crud.create(db.t_%s,next='%s_read/[id]')\n" % (t,t)
            s+="    return dict(form=form)\n\n"
        elif items[1]=='select':
            s+="    f,v=request.args(0),request.args(1)\n"
            s+="    try: query=f and db.t_%s[f]==v or db.t_%s\n" % (t,t)
            s+="    except: redirect(URL('error'))\n"
            s+="    rows=db(query)(db.t_%s.is_active==True).select()\n" % t
            s+="    return dict(rows=rows)\n\n"
        elif items[1]=='search':
            s+="    form, rows=crud.search(db.t_%s,query=db.t_%s.is_active==True)\n" % (t,t)
            s+="    return dict(form=form, rows=rows)\n\n"
        else:
            t=None
    else:
        t=None
    if not t:
        s+="    return dict()\n\n"
    return s

def make_view(page,contents):
    s="{{extend 'layout.html'}}\n\n"
    s+=str(MARKMIN(contents))
    items=page.rsplit('_',1)
    if items[0] in session.app['tables'] and len(items)==2:
        t=items[0]
        if items[1]=='read':
            s+="\n{{=A(T('edit %s'),_href=URL('%s_update',args=request.args(0)))}}\n<br/>\n"%(t,t)
            s+='\n{{=form}}\n'
            s+="{{for t,f in db.t_%s._referenced_by:}}{{if not t[-8:]=='_archive':}}" % t
            s+="[{{=A(t[2:],_href=URL('%s_select'%t[2:],args=(f,form.record.id)))}}]"
            s+='{{pass}}{{pass}}'
        elif items[1]=='create':
            s+="\n{{=A(T('select %s'),_href=URL('%s_select'))}}\n<br/>\n"%(t,t)
            s+='\n{{=form}}\n'
        elif items[1]=='update':
            s+="\n{{=A(T('show %s'),_href=URL('%s_read',args=request.args(0)))}}\n<br/>\n"%(t,t)
            s+='\n{{=form}}\n'
        elif items[1]=='select':
            s+="\n{{if request.args:}}<h3>{{=T('For %s #%s' % (request.args(0)[2:],request.args(1)))}}</h3>{{pass}}\n"
            s+="\n{{=A(T('create new %s'),_href=URL('%s_create'))}}\n<br/>\n"%(t,t)
            s+="\n{{=A(T('search %s'),_href=URL('%s_search'))}}\n<br/>\n"%(t,t)
            s+="\n{{if rows:}}"
            s+="\n  {{headers=dict((str(k),k.label) for k in db.t_%s)}}" % t
            s+="\n  {{=SQLTABLE(rows,headers=headers)}}"
            s+="\n{{else:}}"
            s+="\n  {{=TAG.blockquote(T('No Data'))}}"
            s+="\n{{pass}}\n"
        elif items[1]=='search':
            s+="\n{{=A(T('create new %s'),_href=URL('%s_create'))}}\n<br/>\n"%(t,t)
            s+='\n{{=form}}\n'
            s+="\n{{if rows:}}"
            s+="\n  {{headers=dict((str(k),k.label) for k in db.t_%s)}}" % t
            s+="\n  {{=SQLTABLE(rows,headers=headers)}}"
            s+="\n{{else:}}"
            s+="\n  {{=TAG.blockquote(T('No Data'))}}"
            s+="\n{{pass}}\n"
    return s

def populate(tables):

    s = 'from gluon.contrib.populate import populate\n'
    s+= 'if not db(db.auth_user).count():\n'
    for table in sort_tables(tables):
        t=table=='auth_user' and 'auth_user' or 't_'+table
        s+="     populate(db.%s,10)\n" % t
    return s

def create(options):
    if DEMO_MODE:
        session.flash = T('disabled in demo mode')
        redirect(URL('step6'))
    params = dict(session.app['params'])
    app = session.app['name']
    if not app_create(app,request,force=True,key=params['security_key']):
        session.flash = 'Failure to create application'
        redirect(URL('step6'))

    ### save metadata in newapp/wizard.metadata
    try:
        meta = os.path.join(request.folder,'..',app,'wizard.metadata')
        file=open(meta,'wb')
        pickle.dump(session.app,file)
        file.close()
    except IOError:
        session.flash = 'Failure to write wizard metadata'
        redirect(URL('step6'))

    ### apply theme
    if options.apply_layout and params['layout_theme']!='Default':
        try:
            fn = 'web2py.plugin.layout_%s.w2p' % params['layout_theme']
            theme = urllib.urlopen(LAYOUTS_APP+'/static/plugin_layouts/plugins/'+fn)
            plugin_install(app, theme, request, fn)
        except:
            session.flash = T("unable to download layout")

    ### apply plugins
    for plugin in params['plugins']:
        try:
            plugin_name = 'web2py.plugin.'+plugin+'.w2p'
            stream = urllib.urlopen(PLUGINS_APP+'/static/'+plugin_name)
            plugin_install(app, stream, request, plugin_name)
        except Exception, e:
            session.flash = T("unable to download plugin: %s" % plugin)

    ### write configuration file into newapp/models/0.py
    model = os.path.join(request.folder,'..',app,'models','0.py')
    file = open(model, 'wb')
    try:
        file.write("from gluon.storage import Storage\n")
        file.write("settings = Storage()\n\n")
        file.write("settings.globals.migrate = True\n")
        for key,value in session.app['params']:
            file.write("settings.%s = %s\n" % (key,repr(value)))
    finally:
        file.close()

    ### write configuration file into newapp/models/menu.py
    if options.generate_menu:
        model = os.path.join(request.folder,'..',app,'models','menu.py')
        file = open(model,'wb')
        try:
            file.write(make_menu(session.app['pages']))
        finally:
            file.close()

    ### customize the auth_user table
    model = os.path.join(request.folder,'..',app,'models','db.py')
    fix_db(model)

    ### create newapp/models/db_wizard.py
    if options.generate_model:
        model = os.path.join(request.folder,'..',app,'models','db_wizard.py')
        file = open(model,'wb')
        try:
            file.write('### we prepend t_ to tablenames and f_ to fieldnames for disambiguity\n\n')
            tables = sort_tables(session.app['tables'])
            for table in tables:
                if table=='auth_user': continue
                file.write(make_table(table,session.app['table_'+table]))
        finally:
            file.close()

    model = os.path.join(request.folder,'..',app,
                         'models','db_wizard_populate.py')
    if os.path.exists(model): os.unlink(model)
    if options.populate_database and session.app['tables']:
        file = open(model,'wb')
        try:
            file.write(populate(session.app['tables']))
        finally:
            file.close()

    ### create newapp/controllers/default.py
    if options.generate_controller:
        controller = os.path.join(request.folder,'..',app,'controllers','default.py')
        file = open(controller,'wb')
        try:
            file.write("""# -*- coding: utf-8 -*-
### required - do no delete
def user(): return dict(form=auth())
def download(): return response.download(request,db)
def call():
    session.forget()
    return service()
### end requires
""")
            for page in session.app['pages']:
                file.write(make_page(page,session.app.get('page_'+page,'')))
        finally:
            file.close()

    ### create newapp/views/default/*.html
    if options.generate_views:
        for page in session.app['pages']:
            view = os.path.join(request.folder,'..',app,'views','default',page+'.html')
            file = open(view,'wb')
            try:
                file.write(make_view(page,session.app.get('page_'+page,'')))
            finally:
                file.close()

    if options.erase_database:
        path = os.path.join(request.folder,'..',app,'databases','*')
        for file in glob.glob(path):
            os.unlink(file)

########NEW FILE########
__FILENAME__ = expire_sessions
EXPIRATION_MINUTES = 60
DIGITS = ('0','1','2','3','4','5','6','7','8','9')
import os, time, stat, logging
path = os.path.join(request.folder, 'sessions')
if not os.path.exists(path):
   os.mkdir(path)
now = time.time()
for filename in os.listdir(path):
   fullpath = os.path.join(path,filename)
   try:
      if os.path.isfile(fullpath):
         t = os.stat(fullpath)[stat.ST_MTIME]
         if now-t > EXPIRATION_MINUTES*60 and filename.startswith(DIGITS):
            try:
               os.unlink(fullpath)
            except Exception,e:
               logging.warn('failure to unlink %s: %s' % (fullpath, e))
   except Exception, e:
      logging.warn('failure to stat %s: %s' % (fullpath, e))


########NEW FILE########
__FILENAME__ = af
# coding: utf8
{
'%Y-%m-%d': '%Y-%m-%d',
'%Y-%m-%d %H:%M:%S': '%Y-%m-%d %H:%M:%S',
'(requires internet access)': '(vereis internet toegang)',
'(something like "it-it")': '(iets soos "it-it")',
'About': 'Oor',
'About application': 'Oor program',
'Additional code for your application': 'Additionele kode vir u application',
'Admin language': 'Admin taal',
'Application name:': 'Program naam:',
'Controllers': 'Beheerders',
'Deploy on Google App Engine': 'Stuur na Google App Engine toe',
'Edit application': 'Wysig program',
'Installed applications': 'Geinstalleerde apps',
'Languages': 'Tale',
'License for': 'Lisensie vir',
'Models': 'Modelle',
'Modules': 'Modules',
'New application wizard': 'Nuwe app wizard',
'New simple application': 'Nuwe eenvoudige app',
'Plugins': 'Plugins',
'Powered by': 'Aangedryf deur',
'Searching:': 'Soek:',
'Static files': 'Static files',
'Sure you want to delete this object?': 'Is jy seker jy will hierde object verwyder?',
'The application logic, each URL path is mapped in one exposed function in the controller': 'The application logic, each URL path is mapped in one exposed function in the controller',
'The data representation, define database tables and sets': 'The data representation, define database tables and sets',
'The presentations layer, views are also known as templates': 'The presentations layer, views are also known as templates',
'There are no plugins': 'Daar is geen plugins',
'These files are served without processing, your images go here': 'Hierdie lêre is sonder veranderinge geserved, jou images gaan hier',
'To create a plugin, name a file/folder plugin_[name]': 'Om ''n plugin te skep, noem ''n lêer/gids plugin_[name]',
'Translation strings for the application': 'Vertaling woorde vir die program',
'Upload & install packed application': 'Oplaai & install gepakte program',
'Upload a package:': 'Oplaai ''n package:',
'Use an url:': 'Gebruik n url:',
'Views': 'Views',
'about': 'oor',
'administrative interface': 'administrative interface',
'and rename it:': 'en verander die naam:',
'change admin password': 'verander admin wagwoord',
'check for upgrades': 'soek vir upgrades',
'clean': 'maak skoon',
'collapse/expand all': 'collapse/expand all',
'compile': 'kompileer',
'controllers': 'beheerders',
'create': 'skep',
'create file with filename:': 'skep lêer met naam:',
'created by': 'geskep deur',
'crontab': 'crontab',
'currently running': 'loop tans',
'database administration': 'database administration',
'deploy': 'deploy',
'direction: ltr': 'direction: ltr',
'download layouts': 'aflaai layouts',
'download plugins': 'aflaai plugins',
'edit': 'wysig',
'errors': 'foute',
'exposes': 'exposes',
'extends': 'extends',
'files': 'lêre',
'filter': 'filter',
'help': 'hulp',
'includes': 'includes',
'install': 'installeer',
'languages': 'tale',
'loading...': 'laai...',
'logout': 'logout',
'models': 'modelle',
'modules': 'modules',
'overwrite installed app': 'skryf oor geinstalleerde program',
'pack all': 'pack alles',
'plugins': 'plugins',
'shell': 'shell',
'site': 'site',
'start wizard': 'start wizard',
'static': 'static',
'test': 'toets',
'uninstall': 'verwyder',
'update all languages': 'update all languages',
'upload': 'oplaai',
'upload file:': 'oplaai lêer:',
'upload plugin file:': 'upload plugin lêer:',
'versioning': 'versioning',
'views': 'views',
'web2py Recent Tweets': 'web2py Onlangse Tweets',
}

########NEW FILE########
__FILENAME__ = bg-bg
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN',
'%Y-%m-%d': '%Y-%m-%d',
'%Y-%m-%d %H:%M:%S': '%Y-%m-%d %H:%M:%S',
'%s rows deleted': '%s записите бяха изтрити',
'%s rows updated': '%s записите бяха обновени',
'(requires internet access)': '(requires internet access)',
'(something like "it-it")': '(something like "it-it")',
'A new version of web2py is available': 'A new version of web2py is available',
'A new version of web2py is available: %s': 'A new version of web2py is available: %s',
'ATTENTION: Login requires a secure (HTTPS) connection or running on localhost.': 'ATTENTION: Login requires a secure (HTTPS) connection or running on localhost.',
'ATTENTION: TESTING IS NOT THREAD SAFE SO DO NOT PERFORM MULTIPLE TESTS CONCURRENTLY.': 'ATTENTION: TESTING IS NOT THREAD SAFE SO DO NOT PERFORM MULTIPLE TESTS CONCURRENTLY.',
'ATTENTION: you cannot edit the running application!': 'ATTENTION: you cannot edit the running application!',
'About': 'About',
'About application': 'About application',
'Additional code for your application': 'Additional code for your application',
'Admin is disabled because insecure channel': 'Admin is disabled because insecure channel',
'Admin is disabled because unsecure channel': 'Admin is disabled because unsecure channel',
'Admin language': 'Admin language',
'Administrator Password:': 'Administrator Password:',
'Application name:': 'Application name:',
'Are you sure you want to delete file "%s"?': 'Are you sure you want to delete file "%s"?',
'Are you sure you want to delete plugin "%s"?': 'Are you sure you want to delete plugin "%s"?',
'Are you sure you want to uninstall application "%s"': 'Are you sure you want to uninstall application "%s"',
'Are you sure you want to uninstall application "%s"?': 'Are you sure you want to uninstall application "%s"?',
'Are you sure you want to upgrade web2py now?': 'Are you sure you want to upgrade web2py now?',
'Available databases and tables': 'Available databases and tables',
'Cannot be empty': 'Cannot be empty',
'Cannot compile: there are errors in your app.        Debug it, correct errors and try again.': 'Cannot compile: there are errors in your app.        Debug it, correct errors and try again.',
'Cannot compile: there are errors in your app:': 'Cannot compile: there are errors in your app:',
'Check to delete': 'Check to delete',
'Checking for upgrades...': 'Checking for upgrades...',
'Controllers': 'Controllers',
'Create new simple application': 'Create new simple application',
'Current request': 'Current request',
'Current response': 'Current response',
'Current session': 'Current session',
'DESIGN': 'DESIGN',
'Date and Time': 'Date and Time',
'Delete': 'Delete',
'Delete:': 'Delete:',
'Deploy on Google App Engine': 'Deploy on Google App Engine',
'Design for': 'Design for',
'EDIT': 'EDIT',
'Edit application': 'Edit application',
'Edit current record': 'Edit current record',
'Editing Language file': 'Editing Language file',
'Editing file': 'Editing file',
'Editing file "%s"': 'Editing file "%s"',
'Enterprise Web Framework': 'Enterprise Web Framework',
'Error logs for "%(app)s"': 'Error logs for "%(app)s"',
'Exception instance attributes': 'Exception instance attributes',
'Functions with no doctests will result in [passed] tests.': 'Functions with no doctests will result in [passed] tests.',
'Hello World': 'Здравей, свят',
'If the report above contains a ticket number it indicates a failure in executing the controller, before any attempt to execute the doctests. This is usually due to an indentation error or an error outside function code.\nA green title indicates that all tests (if defined) passed. In this case test results are not shown.': 'If the report above contains a ticket number it indicates a failure in executing the controller, before any attempt to execute the doctests. This is usually due to an indentation error or an error outside function code.\nA green title indicates that all tests (if defined) passed. In this case test results are not shown.',
'Import/Export': 'Import/Export',
'Installed applications': 'Installed applications',
'Internal State': 'Internal State',
'Invalid Query': 'Невалидна заявка',
'Invalid action': 'Invalid action',
'Language files (static strings) updated': 'Language files (static strings) updated',
'Languages': 'Languages',
'Last saved on:': 'Last saved on:',
'License for': 'License for',
'Login': 'Login',
'Login to the Administrative Interface': 'Login to the Administrative Interface',
'Models': 'Models',
'Modules': 'Modules',
'NO': 'NO',
'New Record': 'New Record',
'New application wizard': 'New application wizard',
'New simple application': 'New simple application',
'No databases in this application': 'No databases in this application',
'Original/Translation': 'Original/Translation',
'PAM authenticated user, cannot change password here': 'PAM authenticated user, cannot change password here',
'Peeking at file': 'Peeking at file',
'Plugin "%s" in application': 'Plugin "%s" in application',
'Plugins': 'Plugins',
'Powered by': 'Powered by',
'Query:': 'Query:',
'Resolve Conflict file': 'Resolve Conflict file',
'Rows in table': 'Rows in table',
'Rows selected': 'Rows selected',
'Saved file hash:': 'Saved file hash:',
'Searching:': 'Searching:',
'Static files': 'Static files',
'Sure you want to delete this object?': 'Сигурен ли си, че искаш да изтриеш този обект?',
'TM': 'TM',
'Testing application': 'Testing application',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.',
'The application logic, each URL path is mapped in one exposed function in the controller': 'The application logic, each URL path is mapped in one exposed function in the controller',
'The data representation, define database tables and sets': 'The data representation, define database tables and sets',
'The presentations layer, views are also known as templates': 'The presentations layer, views are also known as templates',
'There are no controllers': 'There are no controllers',
'There are no models': 'There are no models',
'There are no modules': 'There are no modules',
'There are no plugins': 'There are no plugins',
'There are no static files': 'There are no static files',
'There are no translators, only default language is supported': 'There are no translators, only default language is supported',
'There are no views': 'There are no views',
'These files are served without processing, your images go here': 'These files are served without processing, your images go here',
'This is the %(filename)s template': 'This is the %(filename)s template',
'Ticket': 'Ticket',
'To create a plugin, name a file/folder plugin_[name]': 'To create a plugin, name a file/folder plugin_[name]',
'Translation strings for the application': 'Translation strings for the application',
'Unable to check for upgrades': 'Unable to check for upgrades',
'Unable to download': 'Unable to download',
'Unable to download app because:': 'Unable to download app because:',
'Unable to download because': 'Unable to download because',
'Update:': 'Update:',
'Upload & install packed application': 'Upload & install packed application',
'Upload a package:': 'Upload a package:',
'Upload existing application': 'Upload existing application',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.',
'Use an url:': 'Use an url:',
'Version': 'Version',
'Views': 'Views',
'Welcome to web2py': 'Добре дошъл в web2py',
'YES': 'YES',
'about': 'about',
'additional code for your application': 'additional code for your application',
'admin disabled because no admin password': 'admin disabled because no admin password',
'admin disabled because not supported on google app engine': 'admin disabled because not supported on google apps engine',
'admin disabled because unable to access password file': 'admin disabled because unable to access password file',
'administrative interface': 'administrative interface',
'and rename it (required):': 'and rename it (required):',
'and rename it:': 'and rename it:',
'appadmin': 'appadmin',
'appadmin is disabled because insecure channel': 'appadmin is disabled because insecure channel',
'application "%s" uninstalled': 'application "%s" uninstalled',
'application compiled': 'application compiled',
'application is compiled and cannot be designed': 'application is compiled and cannot be designed',
'arguments': 'arguments',
'back': 'back',
'cache': 'cache',
'cache, errors and sessions cleaned': 'cache, errors and sessions cleaned',
'cannot create file': 'cannot create file',
'cannot upload file "%(filename)s"': 'cannot upload file "%(filename)s"',
'change admin password': 'change admin password',
'check all': 'check all',
'check for upgrades': 'check for upgrades',
'clean': 'clean',
'click here for online examples': 'щракни тук за онлайн примери',
'click here for the administrative interface': 'щракни тук за административния интерфейс',
'click to check for upgrades': 'click to check for upgrades',
'code': 'code',
'collapse/expand all': 'collapse/expand all',
'compile': 'compile',
'compiled application removed': 'compiled application removed',
'controllers': 'controllers',
'create': 'create',
'create file with filename:': 'create file with filename:',
'create new application:': 'create new application:',
'created by': 'created by',
'crontab': 'crontab',
'currently running': 'currently running',
'currently saved or': 'currently saved or',
'data uploaded': 'данните бяха качени',
'database': 'database',
'database %s select': 'database %s select',
'database administration': 'database administration',
'db': 'дб',
'defines tables': 'defines tables',
'delete': 'delete',
'delete all checked': 'delete all checked',
'delete plugin': 'delete plugin',
'deploy': 'deploy',
'design': 'дизайн',
'direction: ltr': 'direction: ltr',
'done!': 'готово!',
'download layouts': 'download layouts',
'download plugins': 'download plugins',
'edit': 'edit',
'edit controller': 'edit controller',
'edit views:': 'edit views:',
'errors': 'errors',
'export as csv file': 'export as csv file',
'exposes': 'exposes',
'extends': 'extends',
'failed to reload module': 'failed to reload module',
'failed to reload module because:': 'failed to reload module because:',
'file "%(filename)s" created': 'file "%(filename)s" created',
'file "%(filename)s" deleted': 'file "%(filename)s" deleted',
'file "%(filename)s" uploaded': 'file "%(filename)s" uploaded',
'file "%(filename)s" was not deleted': 'file "%(filename)s" was not deleted',
'file "%s" of %s restored': 'file "%s" of %s restored',
'file changed on disk': 'file changed on disk',
'file does not exist': 'file does not exist',
'file saved on %(time)s': 'file saved on %(time)s',
'file saved on %s': 'file saved on %s',
'files': 'files',
'filter': 'filter',
'help': 'help',
'htmledit': 'htmledit',
'includes': 'includes',
'insert new': 'insert new',
'insert new %s': 'insert new %s',
'install': 'install',
'internal error': 'internal error',
'invalid password': 'invalid password',
'invalid request': 'невалидна заявка',
'invalid ticket': 'invalid ticket',
'language file "%(filename)s" created/updated': 'language file "%(filename)s" created/updated',
'languages': 'languages',
'languages updated': 'languages updated',
'loading...': 'loading...',
'login': 'login',
'logout': 'logout',
'merge': 'merge',
'models': 'models',
'modules': 'modules',
'new application "%s" created': 'new application "%s" created',
'new plugin installed': 'new plugin installed',
'new record inserted': 'новият запис беше добавен',
'next 100 rows': 'next 100 rows',
'no match': 'no match',
'or import from csv file': 'or import from csv file',
'or provide app url:': 'or provide app url:',
'or provide application url:': 'or provide application url:',
'overwrite installed app': 'overwrite installed app',
'pack all': 'pack all',
'pack compiled': 'pack compiled',
'pack plugin': 'pack plugin',
'password changed': 'password changed',
'plugin "%(plugin)s" deleted': 'plugin "%(plugin)s" deleted',
'plugins': 'plugins',
'previous 100 rows': 'previous 100 rows',
'record': 'record',
'record does not exist': 'записът не съществува',
'record id': 'record id',
'remove compiled': 'remove compiled',
'restore': 'restore',
'revert': 'revert',
'save': 'save',
'selected': 'selected',
'session expired': 'session expired',
'shell': 'shell',
'site': 'site',
'some files could not be removed': 'some files could not be removed',
'start wizard': 'start wizard',
'state': 'състояние',
'static': 'static',
'submit': 'submit',
'table': 'table',
'test': 'test',
'the application logic, each URL path is mapped in one exposed function in the controller': 'the application logic, each URL path is mapped in one exposed function in the controller',
'the data representation, define database tables and sets': 'the data representation, define database tables and sets',
'the presentations layer, views are also known as templates': 'the presentations layer, views are also known as templates',
'these files are served without processing, your images go here': 'these files are served without processing, your images go here',
'to  previous version.': 'to  previous version.',
'translation strings for the application': 'translation strings for the application',
'try': 'try',
'try something like': 'try something like',
'unable to create application "%s"': 'unable to create application "%s"',
'unable to delete file "%(filename)s"': 'unable to delete file "%(filename)s"',
'unable to delete file plugin "%(plugin)s"': 'unable to delete file plugin "%(plugin)s"',
'unable to parse csv file': 'не е възможна обработката на csv файла',
'unable to uninstall "%s"': 'unable to uninstall "%s"',
'unable to upgrade because "%s"': 'unable to upgrade because "%s"',
'uncheck all': 'uncheck all',
'uninstall': 'uninstall',
'update': 'update',
'update all languages': 'update all languages',
'upgrade web2py now': 'upgrade web2py now',
'upload': 'upload',
'upload application:': 'upload application:',
'upload file:': 'upload file:',
'upload plugin file:': 'upload plugin file:',
'variables': 'variables',
'versioning': 'versioning',
'view': 'view',
'views': 'views',
'web2py Recent Tweets': 'web2py Recent Tweets',
'web2py is up to date': 'web2py is up to date',
'web2py upgraded; please restart it': 'web2py upgraded; please restart it',
}

########NEW FILE########
__FILENAME__ = de-de
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"Update" ist ein optionaler Ausdruck wie "Feld1 = \'newvalue". JOIN Ergebnisse können nicht aktualisiert oder gelöscht werden',
'%Y-%m-%d': '%Y-%m-%d',
'%Y-%m-%d %H:%M:%S': '%Y-%m-%d %H:%M:%S',
'%s rows deleted': '%s Zeilen gelöscht',
'%s rows updated': '%s Zeilen aktualisiert',
'(requires internet access)': '(requires internet access)',
'(something like "it-it")': '(so etwas wie "it-it")',
'A new version of web2py is available': 'Eine neue Version von web2py ist verfügbar',
'A new version of web2py is available: %s': 'Eine neue Version von web2py ist verfügbar: %s',
'A new version of web2py is available: Version 1.85.3 (2010-09-18 07:07:46)\n': 'Eine neue Version von web2py ist verfügbar: Version 1.85.3 (2010-09-18 07:07:46)\n',
'ATTENTION: Login requires a secure (HTTPS) connection or running on localhost.': 'ACHTUNG: Die Einwahl benötigt eine sichere (HTTPS) Verbindung. Es sei denn sie läuft Lokal(localhost).',
'ATTENTION: TESTING IS NOT THREAD SAFE SO DO NOT PERFORM MULTIPLE TESTS CONCURRENTLY.': 'ACHTUNG: Testen ist nicht threadsicher. Führen sie also nicht mehrere Tests gleichzeitig aus.',
'ATTENTION: This is an experimental feature and it needs more testing.': 'ACHTUNG: Dies ist eine experimentelle Funktion und benötigt noch weitere Tests.',
'ATTENTION: you cannot edit the running application!': 'ACHTUNG: Eine laufende Anwendung kann nicht editiert werden!',
'About': 'Über',
'About application': 'Über die Anwendung',
'Additional code for your application': 'Additional code for your application',
'Admin is disabled because insecure channel': 'Appadmin ist deaktiviert, wegen der Benutzung eines unsicheren Kanals',
'Admin is disabled because unsecure channel': 'Appadmin ist deaktiviert, wegen der Benutzung eines unsicheren Kanals',
'Admin language': 'Admin language',
'Administrator Password:': 'Administrator Passwort:',
'Application name:': 'Application name:',
'Are you sure you want to delete file "%s"?': 'Sind Sie sich sicher, dass Sie diese Datei löschen wollen "%s"?',
'Are you sure you want to uninstall application "%s"': 'Sind Sie sich sicher, dass Sie diese Anwendung deinstallieren wollen "%s"',
'Are you sure you want to uninstall application "%s"?': 'Sind Sie sich sicher, dass Sie diese Anwendung deinstallieren wollen "%s"?',
'Are you sure you want to upgrade web2py now?': 'Sind Sie sich sicher, dass Sie web2py jetzt upgraden möchten?',
'Authentication': 'Authentifizierung',
'Available databases and tables': 'Verfügbare Datenbanken und Tabellen',
'Cannot be empty': 'Darf nicht leer sein',
'Cannot compile: there are errors in your app.        Debug it, correct errors and try again.': 'Nicht Kompilierbar:Es sind Fehler in der Anwendung. Beseitigen Sie die Fehler und versuchen Sie es erneut.',
'Change Password': 'Passwort ändern',
'Check to delete': 'Markiere zum löschen',
'Checking for upgrades...': 'Auf Updates überprüfen...',
'Client IP': 'Client IP',
'Controller': 'Controller',
'Controllers': 'Controller',
'Copyright': 'Urheberrecht',
'Create new simple application': 'Erzeuge neue Anwendung',
'Current request': 'Aktuelle Anfrage (request)',
'Current response': 'Aktuelle Antwort (response)',
'Current session': 'Aktuelle Sitzung (session)',
'DB Model': 'DB Modell',
'DESIGN': 'design',
'Database': 'Datenbank',
'Date and Time': 'Datum und Uhrzeit',
'Delete': 'Löschen',
'Delete:': 'Löschen:',
'Deploy on Google App Engine': 'Auf Google App Engine installieren',
'Description': 'Beschreibung',
'Design for': 'Design für',
'E-mail': 'E-mail',
'EDIT': 'BEARBEITEN',
'Edit': 'Bearbeiten',
'Edit Profile': 'Bearbeite Profil',
'Edit This App': 'Bearbeite diese Anwendung',
'Edit application': 'Bearbeite Anwendung',
'Edit current record': 'Bearbeite aktuellen Datensatz',
'Editing Language file': 'Sprachdatei bearbeiten',
'Editing file': 'Bearbeite Datei',
'Editing file "%s"': 'Bearbeite Datei "%s"',
'Enterprise Web Framework': 'Enterprise Web Framework',
'Error logs for "%(app)s"': 'Fehlerprotokoll für "%(app)s"',
'Exception instance attributes': 'Atribute der Ausnahmeinstanz',
'Expand Abbreviation': 'Kürzel erweitern',
'First name': 'Vorname',
'Functions with no doctests will result in [passed] tests.': 'Funktionen ohne doctests erzeugen [passed] in Tests',
'Go to Matching Pair': 'gehe zum übereinstimmenden Paar',
'Group ID': 'Gruppen ID',
'Hello World': 'Hallo Welt',
'If the report above contains a ticket number it indicates a failure in executing the controller, before any attempt to execute the doctests. This is usually due to an indentation error or an error outside function code.\nA green title indicates that all tests (if defined) passed. In this case test results are not shown.': 'Falls der obere Test eine Fehler-Ticketnummer enthält deutet das auf einen Fehler in der Ausführung des Controllers hin, noch bevor der Doctest ausgeführt werden konnte. Gewöhnlich führen fehlerhafte Einrückungen oder fehlerhafter Code ausserhalb der Funktion zu solchen Fehlern. Ein grüner Titel deutet darauf hin, dass alle Test(wenn sie vorhanden sind) erfolgreich durchlaufen wurden. In diesem Fall werden die Testresultate nicht angezeigt.',
'If you answer "yes", be patient, it may take a while to download': '',
'If you answer yes, be patient, it may take a while to download': 'If you answer yes, be patient, it may take a while to download',
'Import/Export': 'Importieren/Exportieren',
'Index': 'Index',
'Installed applications': 'Installierte Anwendungen',
'Internal State': 'interner Status',
'Invalid Query': 'Ungültige Abfrage',
'Invalid action': 'Ungültige Aktion',
'Invalid email': 'Ungültige Email',
'Key bindings': 'Tastenbelegungen',
'Key bindings for ZenConding Plugin': 'Tastenbelegungen für das ZenConding Plugin',
'Language files (static strings) updated': 'Sprachdatei (statisch Strings) aktualisiert',
'Languages': 'Sprachen',
'Last name': 'Nachname',
'Last saved on:': 'Zuletzt gespeichert am:',
'Layout': 'Layout',
'License for': 'Lizenz für',
'Login': 'Anmelden',
'Login to the Administrative Interface': 'An das Administrations-Interface anmelden',
'Logout': 'Abmeldung',
'Lost Password': 'Passwort vergessen',
'Main Menu': 'Menú principal',
'Match Pair': 'Paare finden',
'Menu Model': 'Menü Modell',
'Merge Lines': 'Zeilen zusammenfügen',
'Models': 'Modelle',
'Modules': 'Module',
'NO': 'NEIN',
'Name': 'Name',
'New Record': 'Neuer Datensatz',
'New application wizard': 'New application wizard',
'New simple application': 'New simple application',
'Next Edit Point': 'nächster Bearbeitungsschritt',
'No databases in this application': 'Keine Datenbank in dieser Anwendung',
'Origin': 'Herkunft',
'Original/Translation': 'Original/Übersetzung',
'Password': 'Passwort',
'Peeking at file': 'Dateiansicht',
'Plugin "%s" in application': 'Plugin "%s" in Anwendung',
'Plugins': 'Plugins',
'Powered by': 'Unterstützt von',
'Previous Edit Point': 'vorheriger Bearbeitungsschritt',
'Query:': 'Abfrage:',
'Record ID': 'Datensatz ID',
'Register': 'registrieren',
'Registration key': 'Registrierungsschlüssel',
'Reset Password key': 'Passwortschlüssel zurücksetzen',
'Resolve Conflict file': 'bereinige Konflikt-Datei',
'Role': 'Rolle',
'Rows in table': 'Zeilen in Tabelle',
'Rows selected': 'Zeilen ausgewählt',
'Save via Ajax': 'via Ajax sichern',
'Saved file hash:': 'Gespeicherter Datei-Hash:',
'Searching:': 'Searching:',
'Static files': 'statische Dateien',
'Stylesheet': 'Stylesheet',
'Sure you want to delete this object?': 'Wollen Sie das Objekt wirklich löschen?',
'TM': 'TM',
'Table name': 'Tabellen Name',
'Testing application': 'Teste die Anwendung',
'Testing controller': 'teste Controller',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'Die "query" ist eine Bedingung wie "db.table1.field1 == \'Wert\'". Etwas wie "db.table1.field1 db.table2.field2 ==" führt zu einem SQL JOIN.',
'The application logic, each URL path is mapped in one exposed function in the controller': 'The application logic, each URL path is mapped in one exposed function in the controller',
'The data representation, define database tables and sets': 'The data representation, define database tables and sets',
'The output of the file is a dictionary that was rendered by the view': 'The output of the file is a dictionary that was rendered by the view',
'The presentations layer, views are also known as templates': 'The presentations layer, views are also known as templates',
'There are no controllers': 'Keine Controller vorhanden',
'There are no models': 'Keine Modelle vorhanden',
'There are no modules': 'Keine Module vorhanden',
'There are no plugins': 'There are no plugins',
'There are no static files': 'Keine statischen Dateien vorhanden',
'There are no translators, only default language is supported': 'Keine Übersetzungen vorhanden, nur die voreingestellte Sprache wird unterstützt',
'There are no views': 'Keine Views vorhanden',
'These files are served without processing, your images go here': 'These files are served without processing, your images go here',
'This is a copy of the scaffolding application': 'Dies ist eine Kopie einer Grundgerüst-Anwendung',
'This is the %(filename)s template': 'Dies ist das Template %(filename)s',
'Ticket': 'Ticket',
'Timestamp': 'Timestamp',
'To create a plugin, name a file/folder plugin_[name]': 'Um ein Plugin zu erstellen benennen Sie eine(n) Datei/Ordner plugin_[Name]',
'Translation strings for the application': 'Translation strings for the application',
'Unable to check for upgrades': 'überprüfen von Upgrades nicht möglich',
'Unable to download': 'herunterladen nicht möglich',
'Unable to download app': 'herunterladen der Anwendung nicht möglich',
'Update:': 'Aktualisiere:',
'Upload & install packed application': 'Verpackte Anwendung hochladen und installieren',
'Upload a package:': 'Upload a package:',
'Upload existing application': 'lade existierende Anwendung hoch',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Benutze (...)&(...) für AND, (...)|(...) für OR, und ~(...) für NOT, um komplexe Abfragen zu erstellen.',
'Use an url:': 'Use an url:',
'User ID': 'Benutzer ID',
'Version': 'Version',
'View': 'View',
'Views': 'Views',
'Welcome %s': 'Willkommen %s',
'Welcome to web2py': 'Willkommen zu web2py',
'Which called the function': 'Which called the function',
'Wrap with Abbreviation': 'mit Kürzel einhüllen',
'YES': 'JA',
'You are successfully running web2py': 'web2by wird erfolgreich ausgeführt',
'You can modify this application and adapt it to your needs': 'Sie können diese Anwendung verändern und Ihren Bedürfnissen anpassen',
'You visited the url': 'Sie besuchten die URL',
'about': 'Über',
'additional code for your application': 'zusätzlicher Code für Ihre Anwendung',
'admin disabled because no admin password': ' admin ist deaktiviert, weil kein Admin-Passwort gesetzt ist',
'admin disabled because not supported on google apps engine': 'admin ist deaktiviert, es existiert dafür keine Unterstützung auf der google apps engine',
'admin disabled because unable to access password file': 'admin ist deaktiviert, weil kein Zugriff auf die Passwortdatei besteht',
'administrative interface': 'administrative interface',
'and rename it (required):': 'und benenne sie um (erforderlich):',
'and rename it:': ' und benenne sie um:',
'appadmin': 'appadmin',
'appadmin is disabled because insecure channel': 'Appadmin ist deaktiviert, wegen der Benutzung eines unsicheren Kanals',
'application "%s" uninstalled': 'Anwendung "%s" deinstalliert',
'application compiled': 'Anwendung kompiliert',
'application is compiled and cannot be designed': 'Die Anwendung ist kompiliert kann deswegen nicht mehr geändert werden',
'arguments': 'arguments',
'back': 'zurück',
'beautify': 'beautify',
'cache': 'Cache',
'cache, errors and sessions cleaned': 'Zwischenspeicher (cache), Fehler und Sitzungen (sessions) gelöscht',
'call': 'call',
'cannot create file': 'Kann Datei nicht erstellen',
'cannot upload file "%(filename)s"': 'Kann Datei nicht Hochladen "%(filename)s"',
'change admin password': 'Administrator-Passwort ändern',
'change password': 'Passwort ändern',
'check all': 'alles auswählen',
'check for upgrades': 'check for upgrades',
'clean': 'löschen',
'click here for online examples': 'hier klicken für online Beispiele',
'click here for the administrative interface': 'hier klicken für die Administrationsoberfläche ',
'click to check for upgrades': 'hier klicken um nach Upgrades zu suchen',
'code': 'code',
'collapse/expand all': 'collapse/expand all',
'compile': 'kompilieren',
'compiled application removed': 'kompilierte Anwendung gelöscht',
'controllers': 'Controllers',
'create': 'erstellen',
'create file with filename:': 'erzeuge Datei mit Dateinamen:',
'create new application:': 'erzeuge neue Anwendung:',
'created by': 'created by',
'crontab': 'crontab',
'currently running': 'currently running',
'currently saved or': 'des derzeit gespeicherten oder',
'customize me!': 'pass mich an!',
'data uploaded': 'Daten hochgeladen',
'database': 'Datenbank',
'database %s select': 'Datenbank %s ausgewählt',
'database administration': 'Datenbankadministration',
'db': 'db',
'defines tables': 'definiere Tabellen',
'delete': 'löschen',
'delete all checked': 'lösche alle markierten',
'delete plugin': 'Plugin löschen',
'deploy': 'deploy',
'design': 'design',
'direction: ltr': 'direction: ltr',
'documentation': 'Dokumentation',
'done!': 'fertig!',
'download layouts': 'download layouts',
'download plugins': 'download plugins',
'edit': 'bearbeiten',
'edit controller': 'Bearbeite Controller',
'edit profile': 'bearbeite Profil',
'edit views:': 'Views bearbeiten:',
'errors': 'Fehler',
'escape': 'escape',
'export as csv file': 'Exportieren als CSV-Datei',
'exposes': 'stellt zur Verfügung',
'extends': 'erweitert',
'failed to reload module': 'neu laden des Moduls fehlgeschlagen',
'file "%(filename)s" created': 'Datei "%(filename)s" erstellt',
'file "%(filename)s" deleted': 'Datei "%(filename)s" gelöscht',
'file "%(filename)s" uploaded': 'Datei "%(filename)s" hochgeladen',
'file "%(filename)s" was not deleted': 'Datei "%(filename)s" wurde nicht gelöscht',
'file "%s" of %s restored': 'Datei "%s" von %s wiederhergestellt',
'file changed on disk': 'Datei auf Festplatte geändert',
'file does not exist': 'Datei existiert nicht',
'file saved on %(time)s': 'Datei gespeichert am %(time)s',
'file saved on %s': 'Datei gespeichert auf %s',
'files': 'files',
'filter': 'filter',
'help': 'Hilfe',
'htmledit': 'htmledit',
'includes': 'Einfügen',
'index': 'index',
'insert new': 'neu einfügen',
'insert new %s': 'neu einfügen %s',
'install': 'installieren',
'internal error': 'interner Fehler',
'invalid password': 'Ungültiges Passwort',
'invalid request': 'ungültige Anfrage',
'invalid ticket': 'ungültiges Ticket',
'language file "%(filename)s" created/updated': 'Sprachdatei "%(filename)s" erstellt/aktualisiert',
'languages': 'Sprachen',
'languages updated': 'Sprachen aktualisiert',
'loading...': 'lade...',
'located in the file': 'located in Datei',
'login': 'anmelden',
'logout': 'abmelden',
'lost password?': 'Passwort vergessen?',
'merge': 'verbinden',
'models': 'Modelle',
'modules': 'Module',
'new application "%s" created': 'neue Anwendung "%s" erzeugt',
'new record inserted': 'neuer Datensatz eingefügt',
'next 100 rows': 'nächsten 100 Zeilen',
'or import from csv file': 'oder importieren von cvs Datei',
'or provide app url:': 'oder geben Sie eine Anwendungs-URL an:',
'or provide application url:': 'oder geben Sie eine Anwendungs-URL an:',
'overwrite installed app': 'installierte Anwendungen überschreiben',
'pack all': 'verpacke alles',
'pack compiled': 'Verpacke kompiliert',
'pack plugin': 'Plugin verpacken',
'please wait!': 'bitte warten!',
'plugins': 'plugins',
'previous 100 rows': 'vorherige 100 zeilen',
'record': 'Datensatz',
'record does not exist': 'Datensatz existiert nicht',
'record id': 'Datensatz id',
'register': 'Registrierung',
'remove compiled': 'kompilat gelöscht',
'restore': 'wiederherstellen',
'revert': 'zurückkehren',
'save': 'sichern',
'selected': 'ausgewählt(e)',
'session expired': 'Sitzung Abgelaufen',
'shell': 'shell',
'site': 'Seite',
'some files could not be removed': 'einige Dateien konnten nicht gelöscht werden',
'start wizard': 'start wizard',
'state': 'Status',
'static': 'statische Dateien',
'submit': 'Absenden',
'table': 'Tabelle',
'test': 'Test',
'test_def': 'test_def',
'test_for': 'test_for',
'test_if': 'test_if',
'test_try': 'test_try',
'the application logic, each URL path is mapped in one exposed function in the controller': 'Die Logik der Anwendung, jeder URL-Pfad wird auf eine Funktion abgebildet die der Controller zur Verfügung stellt',
'the data representation, define database tables and sets': 'Die Datenrepräsentation definiert Mengen von Tabellen und Datenbanken ',
'the presentations layer, views are also known as templates': 'Die Präsentationsschicht, Views sind auch bekannt als Vorlagen/Templates',
'these files are served without processing, your images go here': 'Diese Dateien werden ohne Verarbeitung ausgeliefert. Beispielsweise Bilder kommen hier hin.',
'to  previous version.': 'zu einer früheren Version.',
'translation strings for the application': 'Übersetzungs-Strings für die Anwendung',
'try': 'versuche',
'try something like': 'versuche so etwas wie',
'unable to create application "%s"': 'erzeugen von Anwendung "%s" nicht möglich',
'unable to delete file "%(filename)s"': 'löschen von Datein "%(filename)s" nicht möglich',
'unable to parse csv file': 'analysieren der cvs Datei nicht möglich',
'unable to uninstall "%s"': 'deinstallieren von "%s" nicht möglich',
'uncheck all': 'alles demarkieren',
'uninstall': 'deinstallieren',
'update': 'aktualisieren',
'update all languages': 'aktualisiere alle Sprachen',
'upgrade web2py now': 'jetzt web2py upgraden',
'upload': 'upload',
'upload application:': 'lade Anwendung hoch:',
'upload file:': 'lade Datei hoch:',
'upload plugin file:': 'Plugin-Datei hochladen:',
'user': 'user',
'variables': 'variables',
'versioning': 'Versionierung',
'view': 'View',
'views': 'Views',
'web2py Recent Tweets': 'neuste Tweets von web2py',
'web2py is up to date': 'web2py ist auf dem neuesten Stand',
'xml': 'xml',
}

########NEW FILE########
__FILENAME__ = es-es
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"actualice" es una expresión opcional como "campo1=\'nuevo_valor\'". No se puede actualizar o eliminar resultados de un JOIN',
'%Y-%m-%d': '%Y-%m-%d',
'%Y-%m-%d %H:%M:%S': '%Y-%m-%d %H:%M:%S',
'%s rows deleted': '%s filas eliminadas',
'%s rows updated': '%s filas actualizadas',
'(something like "it-it")': '(algo como "it-it")',
'A new version of web2py is available': 'Hay una nueva versión de web2py disponible',
'A new version of web2py is available: %s': 'Hay una nueva versión de web2py disponible: %s',
'ATTENTION: Login requires a secure (HTTPS) connection or running on localhost.': 'ATENCION: Inicio de sesión requiere una conexión segura (HTTPS) o localhost.',
'ATTENTION: TESTING IS NOT THREAD SAFE SO DO NOT PERFORM MULTIPLE TESTS CONCURRENTLY.': 'ATENCION: NO EJECUTE VARIAS PRUEBAS SIMULTANEAMENTE, NO SON THREAD SAFE.',
'ATTENTION: you cannot edit the running application!': 'ATENCION: no puede modificar la aplicación que se ejecuta!',
'About': 'Acerca de',
'About application': 'Acerca de la aplicación',
'Admin is disabled because insecure channel': 'Admin deshabilitado, el canal no es seguro',
'Admin is disabled because unsecure channel': 'Admin deshabilitado, el canal no es seguro',
'Administrator Password:': 'Contraseña del Administrador:',
'Are you sure you want to delete file "%s"?': '¿Está seguro que desea eliminar el archivo "%s"?',
'Are you sure you want to delete plugin "%s"?': '¿Está seguro que quiere eliminar el plugin "%s"?',
'Are you sure you want to uninstall application "%s"': '¿Está seguro que desea desinstalar la aplicación "%s"',
'Are you sure you want to uninstall application "%s"?': '¿Está seguro que desea desinstalar la aplicación "%s"?',
'Are you sure you want to upgrade web2py now?': '¿Está seguro que desea actualizar web2py ahora?',
'Available databases and tables': 'Bases de datos y tablas disponibles',
'Cannot be empty': 'No puede estar vacío',
'Cannot compile: there are errors in your app.        Debug it, correct errors and try again.': 'No se puede compilar: hay errores en su aplicación. Depure, corrija errores y vuelva a intentarlo.',
'Cannot compile: there are errors in your app:': 'No se puede compilar: hay errores en su aplicación:',
'Change Password': 'Cambie Contraseña',
'Check to delete': 'Marque para eliminar',
'Checking for upgrades...': 'Buscando actulizaciones...',
'Click row to expand traceback': 'Click row to expand traceback',
'Client IP': 'IP del Cliente',
'Controllers': 'Controladores',
'Count': 'Count',
'Create new application using the Wizard': 'Create new application using the Wizard',
'Create new simple application': 'Cree una nueva aplicación',
'Current request': 'Solicitud en curso',
'Current response': 'Respuesta en curso',
'Current session': 'Sesión en curso',
'DESIGN': 'DISEÑO',
'Date and Time': 'Fecha y Hora',
'Delete': 'Elimine',
'Delete:': 'Elimine:',
'Deploy on Google App Engine': 'Instale en Google App Engine',
'Description': 'Descripción',
'Design for': 'Diseño para',
'E-mail': 'Correo electrónico',
'EDIT': 'EDITAR',
'Edit Profile': 'Editar Perfil',
'Edit application': 'Editar aplicación',
'Edit current record': 'Edite el registro actual',
'Editing Language file': 'Editando archivo de lenguaje',
'Editing file': 'Editando archivo',
'Editing file "%s"': 'Editando archivo "%s"',
'Enterprise Web Framework': 'Armazón Empresarial para Internet',
'Error': 'Error',
'Error logs for "%(app)s"': 'Bitácora de errores en "%(app)s"',
'Exception instance attributes': 'Atributos de la instancia de Excepción',
'File': 'File',
'First name': 'Nombre',
'Functions with no doctests will result in [passed] tests.': 'Funciones sin doctests equivalen a pruebas [aceptadas].',
'Group ID': 'ID de Grupo',
'Hello World': 'Hola Mundo',
'If the report above contains a ticket number it indicates a failure in executing the controller, before any attempt to execute the doctests. This is usually due to an indentation error or an error outside function code.\nA green title indicates that all tests (if defined) passed. In this case test results are not shown.': 'Si el reporte anterior contiene un número de tiquete este indica un falla en la ejecución del controlador, antes de cualquier intento de ejecutat doctests. Esto generalmente se debe a un error en la indentación o un error por fuera del código de la función.\r\nUn titulo verde indica que todas las pruebas pasaron (si existen). En dicho caso los resultados no se muestran.',
'Import/Export': 'Importar/Exportar',
'Installed applications': 'Aplicaciones instaladas',
'Internal State': 'Estado Interno',
'Invalid Query': 'Consulta inválida',
'Invalid action': 'Acción inválida',
'Invalid email': 'Correo inválido',
'Language files (static strings) updated': 'Archivos de lenguaje (cadenas estáticas) actualizados',
'Languages': 'Lenguajes',
'Last name': 'Apellido',
'Last saved on:': 'Guardado en:',
'License for': 'Licencia para',
'Login': 'Inicio de sesión',
'Login to the Administrative Interface': 'Inicio de sesión para la Interfaz Administrativa',
'Logout': 'Fin de sesión',
'Lost Password': 'Contraseña perdida',
'Models': 'Modelos',
'Modules': 'Módulos',
'NO': 'NO',
'Name': 'Nombre',
'New Record': 'Registro nuevo',
'No databases in this application': 'No hay bases de datos en esta aplicación',
'Origin': 'Origen',
'Original/Translation': 'Original/Traducción',
'PAM authenticated user, cannot change password here': 'usuario autenticado por PAM, no puede cambiar la contraseña aquí',
'Password': 'Contraseña',
'Peeking at file': 'Visualizando archivo',
'Plugin "%s" in application': 'Plugin "%s" en aplicación',
'Plugins': 'Plugins',
'Powered by': 'Este sitio usa',
'Query:': 'Consulta:',
'Record ID': 'ID de Registro',
'Register': 'Registrese',
'Registration key': 'Contraseña de Registro',
'Resolve Conflict file': 'archivo Resolución de Conflicto',
'Role': 'Rol',
'Rows in table': 'Filas en la tabla',
'Rows selected': 'Filas seleccionadas',
'Saved file hash:': 'Hash del archivo guardado:',
'Static files': 'Archivos estáticos',
'Sure you want to delete this object?': '¿Está seguro que desea eliminar este objeto?',
'TM': 'MR',
'Table name': 'Nombre de la tabla',
'Testing application': 'Probando aplicación',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'La "consulta" es una condición como "db.tabla1.campo1==\'valor\'". Algo como "db.tabla1.campo1==db.tabla2.campo2" resulta en un JOIN SQL.',
'There are no controllers': 'No hay controladores',
'There are no models': 'No hay modelos',
'There are no modules': 'No hay módulos',
'There are no static files': 'No hay archivos estáticos',
'There are no translators, only default language is supported': 'No hay traductores, sólo el lenguaje por defecto es soportado',
'There are no views': 'No hay vistas',
'This is the %(filename)s template': 'Esta es la plantilla %(filename)s',
'Ticket': 'Tiquete',
'Timestamp': 'Timestamp',
'To create a plugin, name a file/folder plugin_[name]': 'Para crear un plugin, nombre un archivo/carpeta plugin_[nombre]',
'Unable to check for upgrades': 'No es posible verificar la existencia de actualizaciones',
'Unable to download': 'No es posible la descarga',
'Unable to download app': 'No es posible descargar la aplicación',
'Unable to download app because:': 'No es posible descargar la aplicación porque:',
'Unable to download because': 'No es posible descargar porque',
'Update:': 'Actualice:',
'Upload & install packed application': 'Suba e instale aplicación empaquetada',
'Upload existing application': 'Suba esta aplicación',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Use (...)&(...) para AND, (...)|(...) para OR, y ~(...) para NOT, para crear consultas más complejas.',
'User ID': 'ID de Usuario',
'Version': 'Versión',
'Views': 'Vistas',
'Welcome to web2py': 'Bienvenido a web2py',
'YES': 'SI',
'about': 'acerca de',
'additional code for your application': 'código adicional para su aplicación',
'admin disabled because no admin password': ' por falta de contraseña',
'admin disabled because not supported on google app engine': 'admin deshabilitado, no es soportado en GAE',
'admin disabled because unable to access password file': 'admin deshabilitado, imposible acceder al archivo con la contraseña',
'and rename it (required):': 'y renombrela (requerido):',
'and rename it:': ' y renombrelo:',
'appadmin': 'appadmin',
'appadmin is disabled because insecure channel': 'admin deshabilitado, el canal no es seguro',
'application "%s" uninstalled': 'aplicación "%s" desinstalada',
'application compiled': 'aplicación compilada',
'application is compiled and cannot be designed': 'la aplicación está compilada y no puede ser modificada',
'arguments': 'argumentos',
'back': 'atrás',
'browse': 'buscar',
'cache': 'cache',
'cache, errors and sessions cleaned': 'cache, errores y sesiones eliminados',
'cannot create file': 'no es posible crear archivo',
'cannot upload file "%(filename)s"': 'no es posible subir archivo "%(filename)s"',
'change admin password': 'cambie contraseña admin',
'check all': 'marcar todos',
'clean': 'limpiar',
'click here for online examples': 'haga clic aquí para ver ejemplos en línea',
'click here for the administrative interface': 'haga clic aquí para usar la interfaz administrativa',
'click to check for upgrades': 'haga clic para buscar actualizaciones',
'click to open': 'click to open',
'code': 'código',
'commit (mercurial)': 'commit (mercurial)',
'compile': 'compilar',
'compiled application removed': 'aplicación compilada removida',
'controllers': 'controladores',
'create': 'crear',
'create file with filename:': 'cree archivo con nombre:',
'create new application:': 'nombre de la nueva aplicación:',
'created by': 'creado por',
'crontab': 'crontab',
'currently saved or': 'actualmente guardado o',
'customize me!': 'Adaptame!',
'data uploaded': 'datos subidos',
'database': 'base de datos',
'database %s select': 'selección en base de datos %s',
'database administration': 'administración base de datos',
'db': 'db',
'defines tables': 'define tablas',
'delete': 'eliminar',
'delete all checked': 'eliminar marcados',
'delete plugin': 'eliminar plugin',
'design': 'modificar',
'direction: ltr': 'direction: ltr',
'done!': 'listo!',
'edit': 'editar',
'edit controller': 'editar controlador',
'edit views:': 'editar vistas:',
'errors': 'errores',
'export as csv file': 'exportar como archivo CSV',
'exposes': 'expone',
'extends': 'extiende',
'failed to reload module': 'recarga del módulo ha fallado',
'failed to reload module because:': 'no es posible recargar el módulo por:',
'file "%(filename)s" created': 'archivo "%(filename)s" creado',
'file "%(filename)s" deleted': 'archivo "%(filename)s" eliminado',
'file "%(filename)s" uploaded': 'archivo "%(filename)s" subido',
'file "%(filename)s" was not deleted': 'archivo "%(filename)s" no fué eliminado',
'file "%s" of %s restored': 'archivo "%s" de %s restaurado',
'file changed on disk': 'archivo modificado en el disco',
'file does not exist': 'archivo no existe',
'file saved on %(time)s': 'archivo guardado %(time)s',
'file saved on %s': 'archivo guardado %s',
'help': 'ayuda',
'htmledit': 'htmledit',
'includes': 'incluye',
'insert new': 'inserte nuevo',
'insert new %s': 'inserte nuevo %s',
'install': 'instalar',
'internal error': 'error interno',
'invalid password': 'contraseña inválida',
'invalid request': 'solicitud inválida',
'invalid ticket': 'tiquete inválido',
'language file "%(filename)s" created/updated': 'archivo de lenguaje "%(filename)s" creado/actualizado',
'languages': 'lenguajes',
'languages updated': 'lenguajes actualizados',
'loading...': 'cargando...',
'login': 'inicio de sesión',
'logout': 'fin de sesión',
'manage': 'manage',
'merge': 'combinar',
'models': 'modelos',
'modules': 'módulos',
'new application "%s" created': 'nueva aplicación "%s" creada',
'new plugin installed': 'nuevo plugin instalado',
'new record inserted': 'nuevo registro insertado',
'next 100 rows': '100 filas siguientes',
'no match': 'no encontrado',
'or import from csv file': 'o importar desde archivo CSV',
'or provide app url:': 'o provea URL de la aplicación:',
'or provide application url:': 'o provea URL de la aplicación:',
'overwrite installed app': 'sobreescriba aplicación instalada',
'pack all': 'empaquetar todo',
'pack compiled': 'empaquete compiladas',
'pack plugin': 'empaquetar plugin',
'password changed': 'contraseña cambiada',
'plugin "%(plugin)s" deleted': 'plugin "%(plugin)s" eliminado',
'previous 100 rows': '100 filas anteriores',
'record': 'registro',
'record does not exist': 'el registro no existe',
'record id': 'id de registro',
'remove compiled': 'eliminar compiladas',
'restore': 'restaurar',
'revert': 'revertir',
'save': 'guardar',
'selected': 'seleccionado(s)',
'session expired': 'sesión expirada',
'shell': 'shell',
'site': 'sitio',
'some files could not be removed': 'algunos archivos no pudieron ser removidos',
'state': 'estado',
'static': 'estáticos',
'submit': 'enviar',
'table': 'tabla',
'test': 'probar',
'the application logic, each URL path is mapped in one exposed function in the controller': 'la lógica de la aplicación, cada ruta URL se mapea en una función expuesta en el controlador',
'the data representation, define database tables and sets': 'la representación de datos, define tablas y conjuntos de base de datos',
'the presentations layer, views are also known as templates': 'la capa de presentación, las vistas también son llamadas plantillas',
'these files are served without processing, your images go here': 'estos archivos son servidos sin procesar, sus imágenes van aquí',
'to  previous version.': 'a la versión previa.',
'translation strings for the application': 'cadenas de caracteres de traducción para la aplicación',
'try': 'intente',
'try something like': 'intente algo como',
'unable to create application "%s"': 'no es posible crear la aplicación "%s"',
'unable to delete file "%(filename)s"': 'no es posible eliminar el archivo "%(filename)s"',
'unable to delete file plugin "%(plugin)s"': 'no es posible eliminar plugin "%(plugin)s"',
'unable to parse csv file': 'no es posible analizar el archivo CSV',
'unable to uninstall "%s"': 'no es posible instalar "%s"',
'unable to upgrade because "%s"': 'no es posible actualizar porque "%s"',
'uncheck all': 'desmarcar todos',
'uninstall': 'desinstalar',
'update': 'actualizar',
'update all languages': 'actualizar todos los lenguajes',
'upgrade web2py now': 'actualize web2py ahora',
'upload application:': 'subir aplicación:',
'upload file:': 'suba archivo:',
'upload plugin file:': 'suba archivo de plugin:',
'variables': 'variables',
'versioning': 'versiones',
'view': 'vista',
'views': 'vistas',
'web2py Recent Tweets': 'Tweets Recientes de web2py',
'web2py is up to date': 'web2py está actualizado',
'web2py upgraded; please restart it': 'web2py actualizado; favor reiniciar',
}

########NEW FILE########
__FILENAME__ = fr-fr
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"update" est une expression en option tels que "field1 = \'newvalue\'". Vous ne pouvez pas mettre à jour ou supprimer les résultats d\'une jointure "a JOIN"',
'%Y-%m-%d': '%d-%m-%Y',
'%Y-%m-%d %H:%M:%S': '%d-%m-%Y %H:%M:%S',
'%s rows deleted': 'lignes %s supprimé',
'%s rows updated': 'lignes %s mis à jour',
'(requires internet access)': '(requires internet access)',
'(something like "it-it")': '(quelque chose comme "it-it") ',
'A new version of web2py is available: %s': 'Une nouvelle version de web2py est disponible: %s ',
'A new version of web2py is available: Version 1.68.2 (2009-10-21 09:59:29)\n': 'Une nouvelle version de web2py est disponible: Version 1.68.2 (2009-10-21 09:59:29)\r\n',
'ATTENTION: Login requires a secure (HTTPS) connection or running on localhost.': 'ATTENTION: nécessite une connexion sécurisée (HTTPS) ou être en localhost. ',
'ATTENTION: TESTING IS NOT THREAD SAFE SO DO NOT PERFORM MULTIPLE TESTS CONCURRENTLY.': 'ATTENTION: les tests ne sont pas thread-safe DONC NE PAS EFFECTUER DES TESTS MULTIPLES SIMULTANÉMENT.',
'ATTENTION: you cannot edit the running application!': "ATTENTION: vous ne pouvez pas modifier l'application qui tourne!",
'About': 'À propos',
'About application': "A propos de l'application",
'Additional code for your application': 'Additional code for your application',
'Admin is disabled because insecure channel': 'Admin est désactivé parce que canal non sécurisé',
'Admin language': 'Admin language',
'Administrator Password:': 'Mot de passe Administrateur:',
'Application name:': 'Application name:',
'Are you sure you want to delete file "%s"?': 'Etes-vous sûr de vouloir supprimer le fichier «%s»?',
'Are you sure you want to delete plugin "%s"?': 'Etes-vous sûr de vouloir effacer le plugin "%s"?',
'Are you sure you want to delete this object?': 'Are you sure you want to delete this object?',
'Are you sure you want to uninstall application "%s"?': "Êtes-vous sûr de vouloir désinstaller l'application «%s»?",
'Are you sure you want to upgrade web2py now?': 'Are you sure you want to upgrade web2py now?',
'Available databases and tables': 'Bases de données et tables disponible',
'Cannot be empty': 'Ne peut pas être vide',
'Cannot compile: there are errors in your app.        Debug it, correct errors and try again.': 'Ne peut pas compiler: il y a des erreurs dans votre application. corriger les erreurs et essayez à nouveau.',
'Cannot compile: there are errors in your app:': 'Cannot compile: there are errors in your app:',
'Check to delete': 'Cocher pour supprimer',
'Checking for upgrades...': 'Vérification des mises à jour ... ',
'Controllers': 'Contrôleurs',
'Create new simple application': 'Créer une nouvelle application',
'Current request': 'Requête actuel',
'Current response': 'Réponse actuelle',
'Current session': 'Session en cours',
'Date and Time': 'Date et heure',
'Delete': 'Supprimer',
'Delete this file (you will be asked to confirm deletion)': 'Delete this file (you will be asked to confirm deletion)',
'Delete:': 'Supprimer:',
'Deploy on Google App Engine': 'Déployer sur Google App Engine',
'EDIT': 'MODIFIER',
'Edit application': "Modifier l'application",
'Edit current record': 'Modifier cet entrée',
'Editing Language file': 'Modifier le fichier de langue',
'Editing file': 'Modifier le fichier',
'Editing file "%s"': 'Modifier le fichier "% s" ',
'Enterprise Web Framework': 'Enterprise Web Framework',
'Error logs for "%(app)s"': 'Journal d\'erreurs pour "%(app)s"',
'Exception instance attributes': 'Exception instance attributes',
'Functions with no doctests will result in [passed] tests.': 'Des fonctions sans doctests entraînera tests [passed] .',
'If the report above contains a ticket number it indicates a failure in executing the controller, before any attempt to execute the doctests. This is usually due to an indentation error or an error outside function code.\nA green title indicates that all tests (if defined) passed. In this case test results are not shown.': "Si le rapport ci-dessus contient un numéro de ticket, cela indique une défaillance dans l'exécution du contrôleur, avant toute tentative d'exécuter les doctests. Cela est généralement dû à une erreur d'indentation ou une erreur à l'extérieur du code de la fonction.\r\nUn titre verte indique que tous les tests (si définie) passed. Dans ce cas, les résultats des essais ne sont pas affichées.",
'Import/Export': 'Importer/Exporter',
'Installed applications': 'Les applications installées',
'Internal State': 'État Interne',
'Invalid Query': 'Requête non valide',
'Invalid action': 'Action non valide',
'Language files (static strings) updated': 'Fichiers de langue (static strings) Mise à jour ',
'Languages': 'Langues',
'Last saved on:': 'Dernière sauvegarde le:',
'License for': 'Licence pour',
'Login': 'Connexion',
'Login to the Administrative Interface': "Se connecter à l'interface d'administration",
'Models': 'Modèles',
'Modules': 'Modules',
'NO': 'NON',
'New Record': 'Nouvel Entrée',
'New application wizard': 'New application wizard',
'New simple application': 'New simple application',
'No databases in this application': 'Aucune base de données dans cette application',
'Original/Translation': 'Original / Traduction',
'PAM authenticated user, cannot change password here': 'PAM authenticated user, cannot change password here',
'Peeking at file': 'Jeter un oeil au fichier',
'Plugin "%s" in application': 'Plugin "%s" dans l\'application',
'Plugins': 'Plugins',
'Powered by': 'Propulsé par',
'Query:': 'Requête: ',
'Resolve Conflict file': 'Résoudre les conflits de fichiers',
'Rows in table': 'Lignes de la table',
'Rows selected': 'Lignes sélectionnées',
"Run tests in this file (to run all files, you may also use the button labelled 'test')": "Run tests in this file (to run all files, you may also use the button labelled 'test')",
'Save': 'Save',
'Saved file hash:': 'Hash du Fichier enregistré:',
'Searching:': 'Searching:',
'Static files': 'Fichiers statiques',
'Sure you want to delete this object?': 'Vous êtes sûr de vouloir supprimer cet objet? ',
'TM': 'MD',
'Testing application': "Test de l'application",
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'La "requête" est une condition comme "db.table1.field1==\'value\'". Quelque chose comme "db.table1.field1==db.table2.field2" aboutit à un JOIN SQL.',
'The application logic, each URL path is mapped in one exposed function in the controller': 'The application logic, each URL path is mapped in one exposed function in the controller',
'The data representation, define database tables and sets': 'The data representation, define database tables and sets',
'The presentations layer, views are also known as templates': 'The presentations layer, views are also known as templates',
'There are no controllers': "Il n'existe pas de contrôleurs",
'There are no models': "Il n'existe pas de modèles",
'There are no modules': "Il n'existe pas de modules",
'There are no plugins': 'There are no plugins',
'There are no static files': "Il n'existe pas de fichiers statiques",
'There are no translators, only default language is supported': "Il n'y a pas de traducteurs, est prise en charge uniquement la langue par défaut",
'There are no views': "Il n'existe pas de vues",
'These files are served without processing, your images go here': 'These files are served without processing, your images go here',
'This is the %(filename)s template': 'Ceci est le modèle %(filename)s ',
'Ticket': 'Ticket',
'To create a plugin, name a file/folder plugin_[name]': 'Pour créer un plugin, créer un fichier /dossier plugin_[nom]',
'Translation strings for the application': 'Translation strings for the application',
'Unable to check for upgrades': 'Impossible de vérifier les mises à niveau',
'Unable to download': 'Impossible de télécharger',
'Unable to download app': 'Impossible de télécharger app',
'Unable to download app because:': 'Unable to download app because:',
'Unable to download because': 'Unable to download because',
'Update:': 'Mise à jour:',
'Upload & install packed application': 'Upload & install packed application',
'Upload a package:': 'Upload a package:',
'Upload existing application': 'charger une application existante',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Utilisez (...)&(...) pour AND, (...)|(...) pour OR, et ~(...) pour NOT et construire des requêtes plus complexes. ',
'Use an url:': 'Use an url:',
'Version': 'Version',
'Views': 'Vues',
'Web Framework': 'Web Framework',
'YES': 'OUI',
'about': 'à propos',
'additional code for your application': 'code supplémentaire pour votre application',
'admin disabled because no admin password': 'admin désactivé car aucun mot de passe admin',
'admin disabled because not supported on google app engine': 'admin désactivé car non pris en charge sur Google Apps engine',
'admin disabled because unable to access password file': "admin désactivé car incapable d'accéder au fichier mot de passe",
'administrative interface': 'administrative interface',
'and rename it (required):': 'et renommez-la (obligatoire):',
'and rename it:': 'et renommez-le:',
'appadmin': 'appadmin',
'appadmin is disabled because insecure channel': 'appadmin est désactivé parce que canal non sécurisé',
'application "%s" uninstalled': 'application "%s" désinstallé',
'application %(appname)s installed with md5sum: %(digest)s': 'application %(appname)s installed with md5sum: %(digest)s',
'application compiled': 'application compilée',
'application is compiled and cannot be designed': "l'application est compilée et ne peut être désigné",
'arguments': 'arguments',
'back': 'retour',
'cache': 'cache',
'cache, errors and sessions cleaned': 'cache, erreurs et sessions nettoyé',
'cannot create file': 'ne peu pas créer de fichier',
'cannot upload file "%(filename)s"': 'ne peu pas charger le fichier "%(filename)s"',
'change admin password': 'change admin password',
'check all': 'tous vérifier ',
'check for upgrades': 'check for upgrades',
'clean': 'nettoyer',
'click to check for upgrades': 'Cliquez pour vérifier les mises à niveau',
'code': 'code',
'collapse/expand all': 'collapse/expand all',
'compile': 'compiler',
'compiled application removed': 'application compilée enlevé',
'controllers': 'contrôleurs',
'create': 'create',
'create file with filename:': 'créer un fichier avec nom de fichier:',
'create new application:': 'créer une nouvelle application:',
'created by': 'créé par',
'crontab': 'crontab',
'currently running': 'currently running',
'currently saved or': 'actuellement enregistrés ou',
'data uploaded': 'données chargées',
'database': 'base de données',
'database %s select': 'base de données  %s sélectionner',
'database administration': 'administration base de données',
'db': 'db',
'defines tables': 'définit les tables',
'delete': 'supprimer',
'delete all checked': 'supprimer tout ce qui est cocher',
'delete plugin': ' supprimer plugin',
'deploy': 'deploy',
'design': 'conception',
'direction: ltr': 'direction: ltr',
'docs': 'docs',
'done!': 'fait!',
'download layouts': 'download layouts',
'download plugins': 'download plugins',
'edit': 'modifier',
'edit controller': 'modifier contrôleur',
'edit views:': 'edit views:',
'errors': 'erreurs',
'export as csv file': 'exportation au format CSV',
'exposes': 'expose',
'exposes:': 'exposes:',
'extends': 'étend',
'failed to reload module': 'impossible de recharger le module',
'failed to reload module because:': 'failed to reload module because:',
'file "%(filename)s" created': 'fichier "%(filename)s" créé',
'file "%(filename)s" deleted': 'fichier "%(filename)s" supprimé',
'file "%(filename)s" uploaded': 'fichier "%(filename)s" chargé',
'file "%s" of %s restored': 'fichier "%s" de %s restauré',
'file changed on disk': 'fichier modifié sur le disque',
'file does not exist': "fichier n'existe pas",
'file saved on %(time)s': 'fichier enregistré le %(time)s',
'file saved on %s': 'fichier enregistré le %s',
'files': 'files',
'filter': 'filter',
'help': 'aide',
'htmledit': 'edition html',
'includes': 'inclus',
'index': 'index',
'insert new': 'insérer nouveau',
'insert new %s': 'insérer nouveau %s',
'install': 'install',
'internal error': 'erreur interne',
'invalid password': 'mot de passe invalide',
'invalid request': 'Demande incorrecte',
'invalid ticket': 'ticket non valide',
'language file "%(filename)s" created/updated': 'fichier de langue "%(filename)s" créé/mis à jour',
'languages': 'langues',
'loading...': 'Chargement ...',
'login': 'connexion',
'logout': 'déconnexion',
'merge': 'fusionner',
'models': 'modèles',
'modules': 'modules',
'new application "%s" created': 'nouvelle application "%s" créée',
'new plugin installed': 'nouveau plugin installé',
'new record inserted': 'nouvelle entrée inséré',
'next 100 rows': '100 lignes suivantes',
'no match': 'no match',
'or import from csv file': 'ou importer depuis un fichier CSV ',
'or provide app url:': 'or provide app url:',
'or provide application url:': "ou fournir l'URL de l'application:",
'overwrite installed app': 'overwrite installed app',
'pack all': 'tout empaqueter',
'pack compiled': 'paquet compilé',
'pack plugin': 'paquet plugin',
'password changed': 'password changed',
'plugin "%(plugin)s" deleted': 'plugin "%(plugin)s" supprimé',
'plugins': 'plugins',
'previous 100 rows': '100 lignes précédentes',
'record': 'entrée',
'record does not exist': "l'entrée n'existe pas",
'record id': 'id entrée',
'remove compiled': 'retirer compilé',
'restore': 'restaurer',
'revert': 'revenir',
'save': 'sauver',
'selected': 'sélectionnés',
'session expired': 'la session a expiré ',
'shell': 'shell',
'site': 'site',
'some files could not be removed': 'certains fichiers ne peuvent pas être supprimés',
'start wizard': 'start wizard',
'state': 'état',
'static': 'statiques',
'submit': 'envoyer',
'table': 'table',
'test': 'tester',
'the application logic, each URL path is mapped in one exposed function in the controller': "la logique de l'application, chaque route URL est mappé dans une fonction exposée dans le contrôleur",
'the data representation, define database tables and sets': 'la représentation des données, défini les tables de bases de données et sets',
'the presentations layer, views are also known as templates': 'la couche des présentations, les vues sont également connus en tant que modèles',
'these files are served without processing, your images go here': 'ces fichiers sont servis sans transformation, vos images vont ici',
'to  previous version.': 'à la version précédente.',
'translation strings for the application': "chaînes de traduction de l'application",
'try': 'essayer',
'try something like': 'essayez quelque chose comme',
'unable to create application "%s"': 'impossible de créer l\'application  "%s"',
'unable to delete file "%(filename)s"': 'impossible de supprimer le fichier "%(filename)s"',
'unable to delete file plugin "%(plugin)s"': 'impossible de supprimer le plugin "%(plugin)s"',
'unable to parse csv file': "impossible d'analyser les fichiers CSV",
'unable to uninstall "%s"': 'impossible de désinstaller "%s"',
'unable to upgrade because "%s"': 'unable to upgrade because "%s"',
'uncheck all': 'tout décocher',
'uninstall': 'désinstaller',
'update': 'mettre à jour',
'update all languages': 'mettre à jour toutes les langues',
'upgrade now': 'upgrade now',
'upgrade web2py now': 'upgrade web2py now',
'upload': 'upload',
'upload application:': "charger l'application:",
'upload file:': 'charger le fichier:',
'upload plugin file:': 'charger fichier plugin:',
'user': 'user',
'variables': 'variables',
'versioning': 'versioning',
'view': 'vue',
'views': 'vues',
'web2py Recent Tweets': 'web2py Tweets récentes',
'web2py is up to date': 'web2py est à jour',
'web2py upgraded; please restart it': 'web2py upgraded; please restart it',
}

########NEW FILE########
__FILENAME__ = he
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"עדכן" הוא ביטוי אופציונאלי, כגון "field1=newvalue". אינך יוכל להשתמש בjoin, בעת שימוש ב"עדכן" או "מחק".',
'%Y-%m-%d': '%Y-%m-%d',
'%Y-%m-%d %H:%M:%S': '%Y-%m-%d %H:%M:%S',
'%s rows deleted': '%s רשומות נמחקו',
'%s rows updated': '%s רשומות עודכנו',
'(requires internet access)': '(requires internet access)',
'(something like "it-it")': '(למשל "it-it")',
'A new version of web2py is available: %s': 'גירסא חדשה של web2py זמינה: %s',
'A new version of web2py is available: Version 1.85.3 (2010-09-18 07:07:46)\n': 'A new version of web2py is available: Version 1.85.3 (2010-09-18 07:07:46)\r\n',
'ATTENTION: Login requires a secure (HTTPS) connection or running on localhost.': 'לתשומת ליבך: ניתן להתחבר רק בערוץ מאובטח (HTTPS) או מlocalhost',
'ATTENTION: TESTING IS NOT THREAD SAFE SO DO NOT PERFORM MULTIPLE TESTS CONCURRENTLY.': 'לתשומת ליבך: אין לערוך מספר בדיקות במקביל, שכן הן עשויות להפריע זו לזו',
'ATTENTION: you cannot edit the running application!': 'לתשומת ליבך: לא ניתן לערוך אפליקציה בזמן הרצתה',
'About': 'אודות',
'About application': 'אודות אפליקציה',
'Additional code for your application': 'Additional code for your application',
'Admin is disabled because insecure channel': 'ממשק האדמין נוטרל בשל גישה לא מאובטחת',
'Admin language': 'Admin language',
'Administrator Password:': 'סיסמת מנהל',
'Application name:': 'Application name:',
'Are you sure you want to delete file "%s"?': 'האם אתה בטוח שברצונך למחוק את הקובץ "%s"?',
'Are you sure you want to delete plugin "%s"?': 'האם אתה בטוח שברצונך למחוק את התוסף "%s"?',
'Are you sure you want to uninstall application "%s"?': 'האם אתה בטוח שברצונך להסיר את האפליקציה "%s"?',
'Are you sure you want to upgrade web2py now?': 'האם אתה בטוח שאתה רוצה לשדרג את web2py עכשיו?',
'Available databases and tables': 'מסדי נתונים וטבלאות זמינים',
'Cannot be empty': 'אינו יכול להישאר ריק',
'Cannot compile: there are errors in your app:': 'לא ניתן לקמפל: ישנן שגיאות באפליקציה שלך:',
'Check to delete': 'סמן כדי למחוק',
'Checking for upgrades...': 'מחפש עדכונים',
'Controllers': 'בקרים',
'Create new simple application': 'צור אפליקציה חדשה',
'Current request': 'בקשה נוכחית',
'Current response': 'מענה נוכחי',
'Current session': 'סשן זה',
'Date and Time': 'תאריך ושעה',
'Delete': 'מחק',
'Delete:': 'מחק:',
'Deploy on Google App Engine': 'העלה ל Google App Engine',
'Detailed traceback description': 'Detailed traceback description',
'EDIT': 'ערוך!',
'Edit application': 'ערוך אפליקציה',
'Edit current record': 'ערוך רשומה נוכחית',
'Editing Language file': 'עורך את קובץ השפה',
'Editing file "%s"': 'עורך את הקובץ "%s"',
'Enterprise Web Framework': 'סביבת הפיתוח לרשת',
'Error logs for "%(app)s"': 'דו"ח שגיאות עבור אפליקציה "%(app)s"',
'Error snapshot': 'Error snapshot',
'Error ticket': 'Error ticket',
'Exception instance attributes': 'נתוני החריגה',
'Frames': 'Frames',
'Functions with no doctests will result in [passed] tests.': 'פונקציות שלא הוגדר להן doctest ירשמו כבדיקות ש[עברו בהצלחה].',
'If the report above contains a ticket number it indicates a failure in executing the controller, before any attempt to execute the doctests. This is usually due to an indentation error or an error outside function code.\nA green title indicates that all tests (if defined) passed. In this case test results are not shown.': 'אם בדו"ח לעיל מופיע מספר דו"ח שגיאה, זה מצביע על שגיאה בבקר, עוד לפני שניתן היה להריץ את הdoctest. לרוב מדובר בשגיאת הזחה, או שגיאה שאינה בקוד של הפונקציה.\r\nכותרת ירוקה מצביע על כך שכל הבדיקות (אם הוגדרו) עברו בהצלחה, במידה ותוצאות הבדיקה אינן מופיעות.',
'Import/Export': 'יבא\יצא',
'Installed applications': 'אפליקציות מותקנות',
'Internal State': 'מצב מובנה',
'Invalid Query': 'שאילתה לא תקינה',
'Invalid action': 'הוראה לא קיימת',
'Language files (static strings) updated': 'קובץ השפה (מחרוזות סטאטיות) עודכן',
'Languages': 'שפות',
'Last saved on:': 'לאחרונה נשמר בתאריך:',
'License for': 'רשיון עבור',
'Login': 'התחבר',
'Login to the Administrative Interface': 'התחבר לממשק המנהל',
'Models': 'מבני נתונים',
'Modules': 'מודולים',
'NO': 'לא',
'New Record': 'רשומה חדשה',
'New application wizard': 'New application wizard',
'New simple application': 'New simple application',
'No databases in this application': 'אין מסדי נתונים לאפליקציה זו',
'Original/Translation': 'מקור\תרגום',
'PAM authenticated user, cannot change password here': 'שינוי סיסמא באמצעות PAM אינו יכול להתבצע כאן',
'Peeking at file': 'מעיין בקובץ',
'Plugin "%s" in application': 'פלאגין "%s" של אפליקציה',
'Plugins': 'תוספים',
'Powered by': 'מופעל ע"י',
'Query:': 'שאילתה:',
'Resolve Conflict file': 'הסר קובץ היוצר קונפליקט',
'Rows in table': 'רשומות בטבלה',
'Rows selected': 'רשומות נבחרו',
'Saved file hash:': 'גיבוב הקובץ השמור:',
'Static files': 'קבצים סטאטיים',
'Sure you want to delete this object?': 'האם אתה בטוח שברצונך למחוק אובייקט זה?',
'TM': 'סימן רשום',
'Testing application': 'בודק את האפליקציה',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': '"שאליתה" היא תנאי כגון "db1.table1.filed1=\'value\'" ביטוי כמו db.table1.field1=db.table2.field1 יחולל join',
'The application logic, each URL path is mapped in one exposed function in the controller': 'The application logic, each URL path is mapped in one exposed function in the controller',
'The data representation, define database tables and sets': 'The data representation, define database tables and sets',
'The presentations layer, views are also known as templates': 'The presentations layer, views are also known as templates',
'There are no controllers': 'אין בקרים',
'There are no models': 'אין מבני נתונים',
'There are no modules': 'אין מודולים',
'There are no plugins': 'There are no plugins',
'There are no static files': 'אין קבצים סטאטיים',
'There are no translators, only default language is supported': 'אין תרגומים. רק שפת ברירת המחדל נתמכת',
'There are no views': 'אין קבצי תצוגה',
'These files are served without processing, your images go here': 'These files are served without processing, your images go here',
'This is the %(filename)s template': 'זוהי תבנית הקובץ %(filename)s ',
'Ticket': 'דו"ח שגיאה',
'Ticket ID': 'Ticket ID',
'To create a plugin, name a file/folder plugin_[name]': 'כדי ליצור תוסף, קרא לקובץ או סיפריה בשם לפי התבנית plugin_[name]',
'Traceback': 'Traceback',
'Translation strings for the application': 'Translation strings for the application',
'Unable to check for upgrades': 'לא ניתן היה לבדוק אם יש שדרוגים',
'Unable to download app because:': 'לא ניתן היה להוריד את האפליקציה כי:',
'Unable to download because': 'לא הצלחתי להוריד כי',
'Update:': 'עדכן:',
'Upload & install packed application': 'העלה והתקן אפליקציה ארוזה',
'Upload a package:': 'Upload a package:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'השתמש ב (...)&(...) עבור תנאי AND, (...)|(...) עבור תנאי OR ו~(...) עבור תנאי NOT ליצירת שאילתות מורכבות',
'Use an url:': 'Use an url:',
'Version': 'גירסא',
'Views': 'מראה',
'YES': 'כן',
'about': 'אודות',
'additional code for your application': 'קוד נוסף עבור האפליקציה שלך',
'admin disabled because no admin password': 'ממשק המנהל מנוטרל כי לא הוגדרה סיסמת מנהל',
'admin disabled because not supported on google app engine': 'ממשק המנהל נוטרל, כי אין תמיכה בGoogle app engine',
'admin disabled because unable to access password file': 'ממשק מנהל נוטרל, כי לא ניתן לגשת לקובץ הסיסמאות',
'administrative interface': 'administrative interface',
'and rename it (required):': 'ושנה את שמו (חובה):',
'and rename it:': 'ושנה את שמו:',
'appadmin': 'מנהל מסד הנתונים',
'appadmin is disabled because insecure channel': 'מנהל מסד הנתונים נוטרל בשל ערוץ לא מאובטח',
'application "%s" uninstalled': 'אפליקציה "%s" הוסרה',
'application compiled': 'אפליקציה קומפלה',
'application is compiled and cannot be designed': 'לא ניתן לערוך אפליקציה מקומפלת',
'arguments': 'פרמטרים',
'back': 'אחורה',
'cache': 'מטמון',
'cache, errors and sessions cleaned': 'מטמון, שגיאות וסשן נוקו',
'cannot create file': 'לא מצליח ליצור קובץ',
'cannot upload file "%(filename)s"': 'לא הצלחתי להעלות את הקובץ "%(filename)s"',
'change admin password': 'סיסמת מנהל שונתה',
'check all': 'סמן הכל',
'check for upgrades': 'check for upgrades',
'clean': 'נקה',
'click to check for upgrades': 'לחץ כדי לחפש עדכונים',
'code': 'קוד',
'collapse/expand all': 'collapse/expand all',
'compile': 'קמפל',
'compiled application removed': 'אפליקציה מקומפלת הוסרה',
'controllers': 'בקרים',
'create': 'צור',
'create file with filename:': 'צור קובץ בשם:',
'create new application:': 'צור אפליקציה חדשה:',
'created by': 'נוצר ע"י',
'crontab': 'משימות מתוזמנות',
'currently running': 'currently running',
'currently saved or': 'נשמר כעת או',
'data uploaded': 'המידע הועלה',
'database': 'מסד נתונים',
'database %s select': 'מסד הנתונים %s נבחר',
'database administration': 'ניהול מסד נתונים',
'db': 'מסד נתונים',
'defines tables': 'הגדר טבלאות',
'delete': 'מחק',
'delete all checked': 'סמן הכל למחיקה',
'delete plugin': 'מחק תוסף',
'deploy': 'deploy',
'design': 'עיצוב',
'direction: ltr': 'direction: rtl',
'done!': 'הסתיים!',
'download layouts': 'download layouts',
'download plugins': 'download plugins',
'edit': 'ערוך',
'edit controller': 'ערוך בקר',
'edit views:': 'ערוך קיבצי תצוגה:',
'errors': 'שגיאות',
'export as csv file': 'יצא לקובץ csv',
'exposes': 'חושף את',
'extends': 'הרחבה של',
'failed to reload module because:': 'נכשל בטעינה חוזרת של מודול בגלל:',
'file "%(filename)s" created': 'הקובץ "%(filename)s" נוצר',
'file "%(filename)s" deleted': 'הקובץ "%(filename)s" נמחק',
'file "%(filename)s" uploaded': 'הקובץ "%(filename)s" הועלה',
'file "%s" of %s restored': 'הקובץ "%s" of %s שוחזר',
'file changed on disk': 'קובץ שונה על גבי הדיסק',
'file does not exist': 'קובץ לא נמצא',
'file saved on %(time)s': 'הקובץ נשמר בשעה %(time)s',
'file saved on %s': 'הקובץ נשמר ב%s',
'filter': 'filter',
'help': 'עזרה',
'htmledit': 'עורך ויזואלי',
'includes': 'מכיל',
'insert new': 'הכנס נוסף',
'insert new %s': 'הכנס %s נוסף',
'inspect attributes': 'inspect attributes',
'install': 'התקן',
'internal error': 'שגיאה מובנית',
'invalid password': 'סיסמא שגויה',
'invalid request': 'בקשה לא תקינה',
'invalid ticket': 'דו"ח שגיאה לא קיים',
'language file "%(filename)s" created/updated': 'קובץ השפה "%(filename)s" נוצר\עודכן',
'languages': 'שפות',
'loading...': 'טוען...',
'locals': 'locals',
'login': 'התחבר',
'logout': 'התנתק',
'merge': 'מזג',
'models': 'מבני נתונים',
'modules': 'מודולים',
'new application "%s" created': 'האפליקציה "%s" נוצרה',
'new plugin installed': 'פלאגין חדש הותקן',
'new record inserted': 'הרשומה נוספה',
'next 100 rows': '100 הרשומות הבאות',
'no match': 'לא נמצאה התאמה',
'or import from csv file': 'או יבא מקובץ csv',
'or provide app url:': 'או ספק כתובת url של אפליקציה',
'overwrite installed app': 'התקן על גבי אפלקציה מותקנת',
'pack all': 'ארוז הכל',
'pack compiled': 'ארוז מקומפל',
'pack plugin': 'ארוז תוסף',
'password changed': 'סיסמא שונתה',
'plugin "%(plugin)s" deleted': 'תוסף "%(plugin)s" נמחק',
'plugins': 'plugins',
'previous 100 rows': '100 הרשומות הקודמות',
'record': 'רשומה',
'record does not exist': 'הרשומה אינה קיימת',
'record id': 'מזהה רשומה',
'remove compiled': 'הסר מקומפל',
'request': 'request',
'response': 'response',
'restore': 'שחזר',
'revert': 'חזור לגירסא קודמת',
'selected': 'נבחרו',
'session': 'session',
'session expired': 'תם הסשן',
'shell': 'שורת פקודה',
'site': 'אתר',
'some files could not be removed': 'לא ניתן היה להסיר חלק מהקבצים',
'start wizard': 'start wizard',
'state': 'מצב',
'static': 'קבצים סטאטיים',
'submit': 'שלח',
'table': 'טבלה',
'test': 'בדיקות',
'the application logic, each URL path is mapped in one exposed function in the controller': 'הלוגיקה של האפליקציה, כל url ממופה לפונקציה חשופה בבקר',
'the data representation, define database tables and sets': 'ייצוג המידע, בו מוגדרים טבלאות ומבנים',
'the presentations layer, views are also known as templates': 'שכבת התצוגה, המכונה גם template',
'these files are served without processing, your images go here': 'אלו הם קבצים הנשלחים מהשרת ללא עיבוד. הכנס את התמונות כאן',
'to  previous version.': 'אין גירסא קודמת',
'translation strings for the application': 'מחרוזות תרגום עבור האפליקציה',
'try': 'נסה',
'try something like': 'נסה משהו כמו',
'unable to create application "%s"': 'נכשל ביצירת האפליקציה "%s"',
'unable to delete file "%(filename)s"': 'נכשל במחיקת הקובץ "%(filename)s"',
'unable to delete file plugin "%(plugin)s"': 'נכשל במחיקת התוסף "%(plugin)s"',
'unable to parse csv file': 'לא הצלחתי לנתח את הקלט של קובץ csv',
'unable to uninstall "%s"': 'לא ניתן להסיר את "%s"',
'unable to upgrade because "%s"': 'לא ניתן היה לשדרג כי "%s"',
'uncheck all': 'הסר סימון מהכל',
'uninstall': 'הסר התקנה',
'update': 'עדכן',
'update all languages': 'עדכן את כלל קיבצי השפה',
'upgrade now': 'upgrade now',
'upgrade web2py now': 'שדרג את web2py עכשיו',
'upload': 'upload',
'upload application:': 'העלה אפליקציה:',
'upload file:': 'העלה קובץ:',
'upload plugin file:': 'העלה קובץ תוסף:',
'variables': 'משתנים',
'versioning': 'מנגנון גירסאות',
'view': 'הצג',
'views': 'מראה',
'web2py Recent Tweets': 'ציוצים אחרונים של web2py',
'web2py is up to date': 'web2py מותקנת בגירסתה האחרונה',
'web2py upgraded; please restart it': 'web2py שודרגה; נא אתחל אותה',
}

########NEW FILE########
__FILENAME__ = it-it
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"update" è un\'espressione opzionale come "campo1=\'nuovo valore\'". Non si può fare "update" o "delete" dei risultati di un JOIN ',
'%Y-%m-%d': '%d/%m/%Y',
'%Y-%m-%d %H:%M:%S': '%d/%m/%Y %H:%M:%S',
'%s rows deleted': '%s righe ("record") cancellate',
'%s rows updated': '%s righe ("record") modificate',
'(requires internet access)': '(requires internet access)',
'(something like "it-it")': '(qualcosa simile a "it-it")',
'A new version of web2py is available: %s': 'È disponibile una nuova versione di web2py: %s',
'ATTENTION: Login requires a secure (HTTPS) connection or running on localhost.': "ATTENZIONE: L'accesso richiede una connessione sicura (HTTPS) o l'esecuzione di web2py in locale (connessione su localhost)",
'ATTENTION: TESTING IS NOT THREAD SAFE SO DO NOT PERFORM MULTIPLE TESTS CONCURRENTLY.': 'ATTENTZIONE: NON ESEGUIRE PIÙ TEST IN PARALLELO (I TEST NON SONO "THREAD SAFE")',
'ATTENTION: you cannot edit the running application!': "ATTENZIONE: non puoi modificare l'applicazione correntemente in uso ",
'About': 'Informazioni',
'About application': "Informazioni sull'applicazione",
'Additional code for your application': 'Additional code for your application',
'Admin is disabled because insecure channel': 'amministrazione disabilitata: comunicazione non sicura',
'Admin language': 'Admin language',
'Administrator Password:': 'Password Amministratore:',
'Application name:': 'Application name:',
'Are you sure you want to delete file "%s"?': 'Confermi di voler cancellare il file "%s"?',
'Are you sure you want to delete plugin "%s"?': 'Confermi di voler cancellare il plugin "%s"?',
'Are you sure you want to delete this object?': 'Are you sure you want to delete this object?',
'Are you sure you want to uninstall application "%s"?': 'Confermi di voler disinstallare l\'applicazione "%s"?',
'Are you sure you want to upgrade web2py now?': 'Confermi di voler aggiornare web2py ora?',
'Available databases and tables': 'Database e tabelle disponibili',
'Begin': 'Begin',
'Cannot be empty': 'Non può essere vuoto',
'Cannot compile: there are errors in your app:': "Compilazione fallita: ci sono errori nell'applicazione.",
'Check to delete': 'Seleziona per cancellare',
'Checking for upgrades...': 'Controllo aggiornamenti in corso...',
'Click row to expand traceback': 'Click row to expand traceback',
'Controller': 'Controller',
'Controllers': 'Controllers',
'Copyright': 'Copyright',
'Count': 'Count',
'Create new simple application': 'Crea nuova applicazione',
'Current request': 'Richiesta (request) corrente',
'Current response': 'Risposta (response) corrente',
'Current session': 'Sessione (session) corrente',
'DB Model': 'Modello di DB',
'Database': 'Database',
'Date and Time': 'Data and Ora',
'Delete': 'Cancella',
'Delete this file (you will be asked to confirm deletion)': 'Delete this file (you will be asked to confirm deletion)',
'Delete:': 'Cancella:',
'Deploy on Google App Engine': 'Installa su Google App Engine',
'Detailed traceback description': 'Detailed traceback description',
'EDIT': 'MODIFICA',
'Edit': 'Modifica',
'Edit This App': 'Modifica questa applicazione',
'Edit application': 'Modifica applicazione',
'Edit current record': 'Modifica record corrente',
'Editing Language file': 'Modifica file linguaggio',
'Editing file "%s"': 'Modifica del file "%s"',
'Enterprise Web Framework': 'Enterprise Web Framework',
'Error': 'Error',
'Error logs for "%(app)s"': 'Log degli errori per "%(app)s"',
'Error snapshot': 'Error snapshot',
'Error ticket': 'Error ticket',
'Exception instance attributes': 'Exception instance attributes',
'File': 'File',
'Frames': 'Frames',
'Functions with no doctests will result in [passed] tests.': 'I test delle funzioni senza "doctests" risulteranno sempre [passed].',
'Hello World': 'Salve Mondo',
'If the report above contains a ticket number it indicates a failure in executing the controller, before any attempt to execute the doctests. This is usually due to an indentation error or an error outside function code.\nA green title indicates that all tests (if defined) passed. In this case test results are not shown.': 'If the report above contains a ticket number it indicates a failure in executing the controller, before any attempt to execute the doctests. This is usually due to an indentation error or an error outside function code.\nA green title indicates that all tests (if defined) passed. In this case test results are not shown.',
'Import/Export': 'Importa/Esporta',
'Index': 'Indice',
'Installed applications': 'Applicazioni installate',
'Internal State': 'Stato interno',
'Invalid Query': 'Richiesta (query) non valida',
'Invalid action': 'Azione non valida',
'Language files (static strings) updated': 'Linguaggi (documenti con stringhe statiche) aggiornati',
'Languages': 'Linguaggi',
'Last saved on:': 'Ultimo salvataggio:',
'Layout': 'Layout',
'License for': 'Licenza relativa a',
'Login': 'Accesso',
'Login to the Administrative Interface': "Accesso all'interfaccia amministrativa",
'Main Menu': 'Menu principale',
'Menu Model': 'Menu Modelli',
'Models': 'Modelli',
'Modules': 'Moduli',
'NO': 'NO',
'New Application Wizard': 'New Application Wizard',
'New Record': 'Nuovo elemento (record)',
'New application wizard': 'New application wizard',
'New simple application': 'New simple application',
'No databases in this application': 'Nessun database presente in questa applicazione',
'Original/Translation': 'Originale/Traduzione',
'PAM authenticated user, cannot change password here': 'utente autenticato tramite PAM, impossibile modificare password qui',
'Peeking at file': 'Uno sguardo al file',
'Plugin "%s" in application': 'Plugin "%s" nell\'applicazione',
'Plugins': 'I Plugins',
'Powered by': 'Powered by',
'Query:': 'Richiesta (query):',
'Resolve Conflict file': 'File di risoluzione conflitto',
'Rows in table': 'Righe nella tabella',
'Rows selected': 'Righe selezionate',
"Run tests in this file (to run all files, you may also use the button labelled 'test')": "Run tests in this file (to run all files, you may also use the button labelled 'test')",
'Save': 'Save',
'Saved file hash:': 'Hash del file salvato:',
'Start a new app': 'Start a new app',
'Static files': 'Files statici',
'Stylesheet': 'Foglio di stile (stylesheet)',
'Sure you want to delete this object?': 'Vuoi veramente cancellare questo oggetto?',
'TM': 'TM',
'Testing application': 'Test applicazione in corsg',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'La richiesta (query) è una condizione come ad esempio  "db.tabella1.campo1==\'valore\'". Una condizione come "db.tabella1.campo1==db.tabella2.campo2" produce un "JOIN" SQL.',
'The application logic, each URL path is mapped in one exposed function in the controller': 'The application logic, each URL path is mapped in one exposed function in the controller',
'The data representation, define database tables and sets': 'The data representation, define database tables and sets',
'The presentations layer, views are also known as templates': 'The presentations layer, views are also known as templates',
'There are no controllers': 'Non ci sono controller',
'There are no models': 'Non ci sono modelli',
'There are no modules': 'Non ci sono moduli',
'There are no plugins': 'There are no plugins',
'There are no static files': 'Non ci sono file statici',
'There are no translators, only default language is supported': 'Non ci sono traduzioni, viene solo supportato il linguaggio di base',
'There are no views': 'Non ci sono viste ("view")',
'These files are served without processing, your images go here': 'These files are served without processing, your images go here',
'This is the %(filename)s template': 'Questo è il template %(filename)s',
'Ticket': 'Ticket',
'Ticket ID': 'Ticket ID',
'To create a plugin, name a file/folder plugin_[name]': 'Per creare un plugin, chiamare un file o cartella plugin_[nome]',
'Traceback': 'Traceback',
'Unable to check for upgrades': 'Impossibile controllare presenza di aggiornamenti',
'Unable to download app because:': 'Impossibile scaricare applicazione perché',
'Unable to download because': 'Impossibile scaricare perché',
'Update:': 'Aggiorna:',
'Upload & install packed application': 'Carica ed installa pacchetto con applicazione',
'Upload a package:': 'Upload a package:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Per costruire richieste (query) più complesse si usano (...)&(...) come "e" (AND), (...)|(...) come "o" (OR), e ~(...) come negazione (NOT).',
'Use an url:': 'Use an url:',
'Version': 'Versione',
'View': 'Vista',
'Views': 'viste',
'Web Framework': 'Web Framework',
'Welcome %s': 'Benvenuto %s',
'Welcome to web2py': 'Benvenuto su web2py',
'YES': 'SI',
'about': 'informazioni',
'additional code for your application': 'righe di codice aggiuntive per la tua applicazione',
'admin disabled because no admin password': 'amministrazione disabilitata per mancanza di password amministrativa',
'admin disabled because not supported on google app engine': 'amministrazione non supportata da Google Apps Engine',
'admin disabled because unable to access password file': 'amministrazione disabilitata per impossibilità di leggere il file delle password',
'administrative interface': 'administrative interface',
'and rename it (required):': 'e rinominala (obbligatorio):',
'and rename it:': 'e rinominala:',
'appadmin': 'appadmin ',
'appadmin is disabled because insecure channel': 'amministrazione app (appadmin) disabilitata: comunicazione non sicura',
'application "%s" uninstalled': 'applicazione "%s" disinstallata',
'application compiled': 'applicazione compilata',
'application is compiled and cannot be designed': "l'applicazione è compilata e non si può modificare",
'arguments': 'arguments',
'back': 'indietro',
'cache': 'cache',
'cache, errors and sessions cleaned': 'pulitura cache, errori and sessioni ',
'cannot create file': 'impossibile creare il file',
'cannot upload file "%(filename)s"': 'impossibile caricare il file "%(filename)s"',
'change admin password': 'change admin password',
'change password': 'cambia password',
'check all': 'controlla tutto',
'check for upgrades': 'check for upgrades',
'clean': 'pulisci',
'click here for online examples': 'clicca per vedere gli esempi',
'click here for the administrative interface': "clicca per l'interfaccia amministrativa",
'click to check for upgrades': 'clicca per controllare presenza di aggiornamenti',
'code': 'code',
'collapse/expand all': 'collapse/expand all',
'compile': 'compila',
'compiled application removed': "rimosso il codice compilato dell'applicazione",
'config': 'config',
'controllers': 'controllers',
'create': 'crea',
'create file with filename:': 'crea un file col nome:',
'create new application:': 'create new application:',
'created by': 'creato da',
'crontab': 'crontab',
'currently running': 'currently running',
'currently saved or': 'attualmente salvato o',
'customize me!': 'Personalizzami!',
'data uploaded': 'dati caricati',
'database': 'database',
'database %s select': 'database %s select',
'database administration': 'amministrazione database',
'db': 'db',
'defines tables': 'defininisce le tabelle',
'delete': 'Cancella',
'delete all checked': 'cancella tutti i selezionati',
'delete plugin': 'cancella plugin',
'deploy': 'deploy',
'design': 'progetta',
'direction: ltr': 'direction: ltr',
'docs': 'docs',
'done!': 'fatto!',
'download layouts': 'download layouts',
'download plugins': 'download plugins',
'edit': 'modifica',
'edit controller': 'modifica controller',
'edit profile': 'modifica profilo',
'edit views:': 'modifica viste (view):',
'errors': 'errori',
'export as csv file': 'esporta come file CSV',
'exposes': 'espone',
'exposes:': 'exposes:',
'extends': 'estende',
'failed to reload module because:': 'ricaricamento modulo fallito perché:',
'file "%(filename)s" created': 'creato il file "%(filename)s"',
'file "%(filename)s" deleted': 'cancellato il file "%(filename)s"',
'file "%(filename)s" uploaded': 'caricato il file "%(filename)s"',
'file "%s" of %s restored': 'ripristinato "%(filename)s"',
'file changed on disk': 'il file ha subito una modifica su disco',
'file does not exist': 'file inesistente',
'file saved on %(time)s': "file salvato nell'istante %(time)s",
'file saved on %s': 'file salvato: %s',
'files': 'files',
'filter': 'filter',
'help': 'aiuto',
'htmledit': 'modifica come html',
'includes': 'include',
'index': 'index',
'insert new': 'inserisci nuovo',
'insert new %s': 'inserisci nuovo %s',
'inspect attributes': 'inspect attributes',
'install': 'installa',
'internal error': 'errore interno',
'invalid password': 'password non valida',
'invalid password.': 'invalid password.',
'invalid request': 'richiesta non valida',
'invalid ticket': 'ticket non valido',
'language file "%(filename)s" created/updated': 'file linguaggio "%(filename)s" creato/aggiornato',
'languages': 'linguaggi',
'loading...': 'caricamento...',
'locals': 'locals',
'login': 'accesso',
'logout': 'uscita',
'merge': 'unisci',
'models': 'modelli',
'modules': 'moduli',
'new application "%s" created': 'creata la nuova applicazione "%s"',
'new plugin installed': 'installato nuovo plugin',
'new record inserted': 'nuovo record inserito',
'next 100 rows': 'prossime 100 righe',
'no match': 'nessuna corrispondenza',
'or import from csv file': 'oppure importa da file CSV',
'or provide app url:': "oppure fornisci url dell'applicazione:",
'overwrite installed app': 'sovrascrivi applicazione installata',
'pack all': 'crea pacchetto',
'pack compiled': 'crea pacchetto del codice compilato',
'pack plugin': 'crea pacchetto del plugin',
'password changed': 'password modificata',
'plugin "%(plugin)s" deleted': 'plugin "%(plugin)s" cancellato',
'plugins': 'plugins',
'previous 100 rows': '100 righe precedenti',
'record': 'record',
'record does not exist': 'il record non esiste',
'record id': 'ID del record',
'register': 'registrazione',
'remove compiled': 'rimozione codice compilato',
'request': 'request',
'response': 'response',
'restore': 'ripristino',
'revert': 'versione precedente',
'selected': 'selezionato',
'session': 'session',
'session expired': 'sessions scaduta',
'shell': 'shell',
'site': 'sito',
'some files could not be removed': 'non è stato possibile rimuovere alcuni files',
'start wizard': 'start wizard',
'state': 'stato',
'static': 'statico',
'submit': 'invia',
'table': 'tabella',
'targets': 'targets',
'test': 'test',
'the application logic, each URL path is mapped in one exposed function in the controller': 'logica dell\'applicazione, ogni percorso "URL" corrisponde ad una funzione esposta da un controller',
'the data representation, define database tables and sets': 'rappresentazione dei dati, definizione di tabelle di database e di "set" ',
'the presentations layer, views are also known as templates': 'Presentazione dell\'applicazione, viste (views, chiamate anche "templates")',
'these files are served without processing, your images go here': 'questi files vengono serviti così come sono, le immagini vanno qui',
'to  previous version.': 'torna a versione precedente',
'translation strings for the application': "stringhe di traduzioni per l'applicazione",
'try': 'prova',
'try something like': 'prova qualcosa come',
'unable to create application "%s"': 'impossibile creare applicazione "%s"',
'unable to delete file "%(filename)s"': 'impossibile rimuovere file "%(plugin)s"',
'unable to delete file plugin "%(plugin)s"': 'impossibile rimuovere file di plugin "%(plugin)s"',
'unable to parse csv file': 'non riesco a decodificare questo file CSV',
'unable to uninstall "%s"': 'impossibile disinstallare "%s"',
'unable to upgrade because "%s"': 'impossibile aggiornare perché "%s"',
'uncheck all': 'smarca tutti',
'uninstall': 'disinstalla',
'update': 'aggiorna',
'update all languages': 'aggiorna tutti i linguaggi',
'upgrade now': 'upgrade now',
'upgrade web2py now': 'upgrade web2py now',
'upload': 'upload',
'upload application:': 'carica applicazione:',
'upload file:': 'carica file:',
'upload plugin file:': 'carica file di plugin:',
'variables': 'variables',
'versioning': 'sistema di versioni',
'view': 'vista',
'views': 'viste',
'web2py Recent Tweets': 'Tweets recenti per web2py',
'web2py is up to date': 'web2py è aggiornato',
'web2py upgraded; please restart it': 'web2py aggiornato; prego riavviarlo',
'wizard': 'wizard',
}

########NEW FILE########
__FILENAME__ = it
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"update" è un\'espressione opzionale come "campo1=\'nuovo valore\'". Non si può fare "update" o "delete" dei risultati di un JOIN ',
'%Y-%m-%d': '%d/%m/%Y',
'%Y-%m-%d %H:%M:%S': '%d/%m/%Y %H:%M:%S',
'%s rows deleted': '%s righe ("record") cancellate',
'%s rows updated': '%s righe ("record") modificate',
'(requires internet access)': '(requires internet access)',
'(something like "it-it")': '(qualcosa simile a "it-it")',
'A new version of web2py is available: %s': 'È disponibile una nuova versione di web2py: %s',
'ATTENTION: Login requires a secure (HTTPS) connection or running on localhost.': "ATTENZIONE: L'accesso richiede una connessione sicura (HTTPS) o l'esecuzione di web2py in locale (connessione su localhost)",
'ATTENTION: TESTING IS NOT THREAD SAFE SO DO NOT PERFORM MULTIPLE TESTS CONCURRENTLY.': 'ATTENTZIONE: NON ESEGUIRE PIÙ TEST IN PARALLELO (I TEST NON SONO "THREAD SAFE")',
'ATTENTION: you cannot edit the running application!': "ATTENZIONE: non puoi modificare l'applicazione correntemente in uso ",
'About': 'Informazioni',
'About application': "Informazioni sull'applicazione",
'Additional code for your application': 'Additional code for your application',
'Admin is disabled because insecure channel': 'amministrazione disabilitata: comunicazione non sicura',
'Admin language': 'Admin language',
'Administrator Password:': 'Password Amministratore:',
'Application name:': 'Application name:',
'Are you sure you want to delete file "%s"?': 'Confermi di voler cancellare il file "%s"?',
'Are you sure you want to delete plugin "%s"?': 'Confermi di voler cancellare il plugin "%s"?',
'Are you sure you want to delete this object?': 'Are you sure you want to delete this object?',
'Are you sure you want to uninstall application "%s"?': 'Confermi di voler disinstallare l\'applicazione "%s"?',
'Are you sure you want to upgrade web2py now?': 'Confermi di voler aggiornare web2py ora?',
'Available databases and tables': 'Database e tabelle disponibili',
'Cannot be empty': 'Non può essere vuoto',
'Cannot compile: there are errors in your app:': "Compilazione fallita: ci sono errori nell'applicazione.",
'Check to delete': 'Seleziona per cancellare',
'Checking for upgrades...': 'Controllo aggiornamenti in corso...',
'Controller': 'Controller',
'Controllers': 'Controllers',
'Copyright': 'Copyright',
'Create new simple application': 'Crea nuova applicazione',
'Current request': 'Richiesta (request) corrente',
'Current response': 'Risposta (response) corrente',
'Current session': 'Sessione (session) corrente',
'DB Model': 'Modello di DB',
'Database': 'Database',
'Date and Time': 'Data and Ora',
'Delete': 'Cancella',
'Delete this file (you will be asked to confirm deletion)': 'Delete this file (you will be asked to confirm deletion)',
'Delete:': 'Cancella:',
'Deploy on Google App Engine': 'Installa su Google App Engine',
'EDIT': 'MODIFICA',
'Edit': 'Modifica',
'Edit This App': 'Modifica questa applicazione',
'Edit application': 'Modifica applicazione',
'Edit current record': 'Modifica record corrente',
'Editing Language file': 'Modifica file linguaggio',
'Editing file "%s"': 'Modifica del file "%s"',
'Enterprise Web Framework': 'Enterprise Web Framework',
'Error logs for "%(app)s"': 'Log degli errori per "%(app)s"',
'Exception instance attributes': 'Exception instance attributes',
'Functions with no doctests will result in [passed] tests.': 'I test delle funzioni senza "doctests" risulteranno sempre [passed].',
'Hello World': 'Salve Mondo',
'If the report above contains a ticket number it indicates a failure in executing the controller, before any attempt to execute the doctests. This is usually due to an indentation error or an error outside function code.\nA green title indicates that all tests (if defined) passed. In this case test results are not shown.': 'If the report above contains a ticket number it indicates a failure in executing the controller, before any attempt to execute the doctests. This is usually due to an indentation error or an error outside function code.\nA green title indicates that all tests (if defined) passed. In this case test results are not shown.',
'Import/Export': 'Importa/Esporta',
'Index': 'Indice',
'Installed applications': 'Applicazioni installate',
'Internal State': 'Stato interno',
'Invalid Query': 'Richiesta (query) non valida',
'Invalid action': 'Azione non valida',
'Language files (static strings) updated': 'Linguaggi (documenti con stringhe statiche) aggiornati',
'Languages': 'Linguaggi',
'Last saved on:': 'Ultimo salvataggio:',
'Layout': 'Layout',
'License for': 'Licenza relativa a',
'Login': 'Accesso',
'Login to the Administrative Interface': "Accesso all'interfaccia amministrativa",
'Main Menu': 'Menu principale',
'Menu Model': 'Menu Modelli',
'Models': 'Modelli',
'Modules': 'Moduli',
'NO': 'NO',
'New Record': 'Nuovo elemento (record)',
'New application wizard': 'New application wizard',
'New simple application': 'New simple application',
'No databases in this application': 'Nessun database presente in questa applicazione',
'Original/Translation': 'Originale/Traduzione',
'PAM authenticated user, cannot change password here': 'utente autenticato tramite PAM, impossibile modificare password qui',
'Peeking at file': 'Uno sguardo al file',
'Plugin "%s" in application': 'Plugin "%s" nell\'applicazione',
'Plugins': 'I Plugins',
'Powered by': 'Powered by',
'Query:': 'Richiesta (query):',
'Resolve Conflict file': 'File di risoluzione conflitto',
'Rows in table': 'Righe nella tabella',
'Rows selected': 'Righe selezionate',
"Run tests in this file (to run all files, you may also use the button labelled 'test')": "Run tests in this file (to run all files, you may also use the button labelled 'test')",
'Save': 'Save',
'Saved file hash:': 'Hash del file salvato:',
'Searching:': 'Searching:',
'Static files': 'Files statici',
'Stylesheet': 'Foglio di stile (stylesheet)',
'Sure you want to delete this object?': 'Vuoi veramente cancellare questo oggetto?',
'TM': 'TM',
'Testing application': 'Test applicazione in corsg',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'La richiesta (query) è una condizione come ad esempio  "db.tabella1.campo1==\'valore\'". Una condizione come "db.tabella1.campo1==db.tabella2.campo2" produce un "JOIN" SQL.',
'The application logic, each URL path is mapped in one exposed function in the controller': 'The application logic, each URL path is mapped in one exposed function in the controller',
'The data representation, define database tables and sets': 'The data representation, define database tables and sets',
'The presentations layer, views are also known as templates': 'The presentations layer, views are also known as templates',
'There are no controllers': 'Non ci sono controller',
'There are no models': 'Non ci sono modelli',
'There are no modules': 'Non ci sono moduli',
'There are no plugins': 'There are no plugins',
'There are no static files': 'Non ci sono file statici',
'There are no translators, only default language is supported': 'Non ci sono traduzioni, viene solo supportato il linguaggio di base',
'There are no views': 'Non ci sono viste ("view")',
'These files are served without processing, your images go here': 'These files are served without processing, your images go here',
'This is the %(filename)s template': 'Questo è il template %(filename)s',
'Ticket': 'Ticket',
'To create a plugin, name a file/folder plugin_[name]': 'Per creare un plugin, chiamare un file o cartella plugin_[nome]',
'Translation strings for the application': 'Translation strings for the application',
'Unable to check for upgrades': 'Impossibile controllare presenza di aggiornamenti',
'Unable to download app because:': 'Impossibile scaricare applicazione perché',
'Unable to download because': 'Impossibile scaricare perché',
'Unable to download because:': 'Unable to download because:',
'Update:': 'Aggiorna:',
'Upload & install packed application': 'Carica ed installa pacchetto con applicazione',
'Upload a package:': 'Upload a package:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Per costruire richieste (query) più complesse si usano (...)&(...) come "e" (AND), (...)|(...) come "o" (OR), e ~(...) come negazione (NOT).',
'Use an url:': 'Use an url:',
'Version': 'Versione',
'View': 'Vista',
'Views': 'viste',
'Welcome %s': 'Benvenuto %s',
'Welcome to web2py': 'Benvenuto su web2py',
'YES': 'SI',
'about': 'informazioni',
'additional code for your application': 'righe di codice aggiuntive per la tua applicazione',
'admin disabled because no admin password': 'amministrazione disabilitata per mancanza di password amministrativa',
'admin disabled because not supported on google app engine': 'amministrazione non supportata da Google Apps Engine',
'admin disabled because unable to access password file': 'amministrazione disabilitata per impossibilità di leggere il file delle password',
'administrative interface': 'administrative interface',
'and rename it (required):': 'e rinominala (obbligatorio):',
'and rename it:': 'e rinominala:',
'appadmin': 'appadmin ',
'appadmin is disabled because insecure channel': 'amministrazione app (appadmin) disabilitata: comunicazione non sicura',
'application "%s" uninstalled': 'applicazione "%s" disinstallata',
'application compiled': 'applicazione compilata',
'application is compiled and cannot be designed': "l'applicazione è compilata e non si può modificare",
'arguments': 'arguments',
'back': 'indietro',
'cache': 'cache',
'cache, errors and sessions cleaned': 'pulitura cache, errori and sessioni ',
'cannot create file': 'impossibile creare il file',
'cannot upload file "%(filename)s"': 'impossibile caricare il file "%(filename)s"',
'change admin password': 'change admin password',
'change password': 'cambia password',
'check all': 'controlla tutto',
'check for upgrades': 'check for upgrades',
'clean': 'pulisci',
'click here for online examples': 'clicca per vedere gli esempi',
'click here for the administrative interface': "clicca per l'interfaccia amministrativa",
'click to check for upgrades': 'clicca per controllare presenza di aggiornamenti',
'code': 'code',
'collapse/expand all': 'collapse/expand all',
'compile': 'compila',
'compiled application removed': "rimosso il codice compilato dell'applicazione",
'controllers': 'controllers',
'create': 'crea',
'create file with filename:': 'crea un file col nome:',
'create new application:': 'create new application:',
'created by': 'creato da',
'crontab': 'crontab',
'currently running': 'currently running',
'currently saved or': 'attualmente salvato o',
'customize me!': 'Personalizzami!',
'data uploaded': 'dati caricati',
'database': 'database',
'database %s select': 'database %s select',
'database administration': 'amministrazione database',
'db': 'db',
'defines tables': 'defininisce le tabelle',
'delete': 'Cancella',
'delete all checked': 'cancella tutti i selezionati',
'delete plugin': 'cancella plugin',
'deploy': 'deploy',
'design': 'progetta',
'direction: ltr': 'direction: ltr',
'docs': 'docs',
'done!': 'fatto!',
'download layouts': 'download layouts',
'download plugins': 'download plugins',
'edit': 'modifica',
'edit controller': 'modifica controller',
'edit profile': 'modifica profilo',
'edit views:': 'modifica viste (view):',
'errors': 'errori',
'export as csv file': 'esporta come file CSV',
'exposes': 'espone',
'exposes:': 'exposes:',
'extends': 'estende',
'failed to reload module because:': 'ricaricamento modulo fallito perché:',
'file "%(filename)s" created': 'creato il file "%(filename)s"',
'file "%(filename)s" deleted': 'cancellato il file "%(filename)s"',
'file "%(filename)s" uploaded': 'caricato il file "%(filename)s"',
'file "%s" of %s restored': 'ripristinato "%(filename)s"',
'file changed on disk': 'il file ha subito una modifica su disco',
'file does not exist': 'file inesistente',
'file saved on %(time)s': "file salvato nell'istante %(time)s",
'file saved on %s': 'file salvato: %s',
'files': 'files',
'filter': 'filter',
'help': 'aiuto',
'htmledit': 'modifica come html',
'includes': 'include',
'index': 'index',
'insert new': 'inserisci nuovo',
'insert new %s': 'inserisci nuovo %s',
'install': 'installa',
'internal error': 'errore interno',
'invalid password': 'password non valida',
'invalid request': 'richiesta non valida',
'invalid ticket': 'ticket non valido',
'language file "%(filename)s" created/updated': 'file linguaggio "%(filename)s" creato/aggiornato',
'languages': 'linguaggi',
'loading...': 'caricamento...',
'login': 'accesso',
'logout': 'uscita',
'merge': 'unisci',
'models': 'modelli',
'modules': 'moduli',
'new application "%s" created': 'creata la nuova applicazione "%s"',
'new plugin installed': 'installato nuovo plugin',
'new record inserted': 'nuovo record inserito',
'next 100 rows': 'prossime 100 righe',
'no match': 'nessuna corrispondenza',
'online designer': 'online designer',
'or import from csv file': 'oppure importa da file CSV',
'or provide app url:': "oppure fornisci url dell'applicazione:",
'overwrite installed app': 'sovrascrivi applicazione installata',
'pack all': 'crea pacchetto',
'pack compiled': 'crea pacchetto del codice compilato',
'pack plugin': 'crea pacchetto del plugin',
'password changed': 'password modificata',
'plugin "%(plugin)s" deleted': 'plugin "%(plugin)s" cancellato',
'plugins': 'plugins',
'previous 100 rows': '100 righe precedenti',
'record': 'record',
'record does not exist': 'il record non esiste',
'record id': 'ID del record',
'register': 'registrazione',
'remove compiled': 'rimozione codice compilato',
'restore': 'ripristino',
'revert': 'versione precedente',
'selected': 'selezionato',
'session expired': 'sessions scaduta',
'shell': 'shell',
'site': 'sito',
'some files could not be removed': 'non è stato possibile rimuovere alcuni files',
'start wizard': 'start wizard',
'state': 'stato',
'static': 'statico',
'submit': 'invia',
'table': 'tabella',
'test': 'test',
'the application logic, each URL path is mapped in one exposed function in the controller': 'logica dell\'applicazione, ogni percorso "URL" corrisponde ad una funzione esposta da un controller',
'the data representation, define database tables and sets': 'rappresentazione dei dati, definizione di tabelle di database e di "set" ',
'the presentations layer, views are also known as templates': 'Presentazione dell\'applicazione, viste (views, chiamate anche "templates")',
'these files are served without processing, your images go here': 'questi files vengono serviti così come sono, le immagini vanno qui',
'to  previous version.': 'torna a versione precedente',
'translation strings for the application': "stringhe di traduzioni per l'applicazione",
'try': 'prova',
'try something like': 'prova qualcosa come',
'try view': 'try view',
'unable to create application "%s"': 'impossibile creare applicazione "%s"',
'unable to delete file "%(filename)s"': 'impossibile rimuovere file "%(plugin)s"',
'unable to delete file plugin "%(plugin)s"': 'impossibile rimuovere file di plugin "%(plugin)s"',
'unable to parse csv file': 'non riesco a decodificare questo file CSV',
'unable to uninstall "%s"': 'impossibile disinstallare "%s"',
'unable to upgrade because "%s"': 'impossibile aggiornare perché "%s"',
'uncheck all': 'smarca tutti',
'uninstall': 'disinstalla',
'update': 'aggiorna',
'update all languages': 'aggiorna tutti i linguaggi',
'upgrade web2py now': 'upgrade web2py now',
'upload': 'upload',
'upload application:': 'carica applicazione:',
'upload file:': 'carica file:',
'upload plugin file:': 'carica file di plugin:',
'variables': 'variables',
'versioning': 'sistema di versioni',
'view': 'vista',
'views': 'viste',
'web2py Recent Tweets': 'Tweets recenti per web2py',
'web2py is up to date': 'web2py è aggiornato',
'web2py upgraded; please restart it': 'web2py aggiornato; prego riavviarlo',
}

########NEW FILE########
__FILENAME__ = pl-pl
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"Uaktualnij" jest dodatkowym wyrażeniem postaci "pole1=\'nowawartość\'". Nie możesz uaktualnić lub usunąć wyników z JOIN:',
'%Y-%m-%d': '%Y-%m-%d',
'%Y-%m-%d %H:%M:%S': '%Y-%m-%d %H:%M:%S',
'%s rows deleted': 'Wierszy usuniętych: %s',
'%s rows updated': 'Wierszy uaktualnionych: %s',
'(requires internet access)': '(requires internet access)',
'(something like "it-it")': '(coś podobnego do "it-it")',
'A new version of web2py is available': 'Nowa wersja web2py jest dostępna',
'A new version of web2py is available: %s': 'A new version of web2py is available: %s',
'ATTENTION: Login requires a secure (HTTPS) connection or running on localhost.': 'UWAGA: Wymagane jest bezpieczne (HTTPS) połączenie lub połączenia z lokalnego adresu.',
'ATTENTION: TESTING IS NOT THREAD SAFE SO DO NOT PERFORM MULTIPLE TESTS CONCURRENTLY.': 'ATTENTION: TESTING IS NOT THREAD SAFE SO DO NOT PERFORM MULTIPLE TESTS CONCURRENTLY.',
'ATTENTION: you cannot edit the running application!': 'UWAGA: nie można edytować uruchomionych aplikacji!',
'About': 'Informacje o',
'About application': 'Informacje o aplikacji',
'Admin is disabled because insecure channel': 'Admin is disabled because insecure channel',
'Admin is disabled because unsecure channel': 'Panel administracyjny wyłączony z powodu braku bezpiecznego połączenia',
'Admin language': 'Admin language',
'Administrator Password:': 'Hasło administratora:',
'Application name:': 'Application name:',
'Are you sure you want to delete file "%s"?': 'Czy na pewno chcesz usunąć plik "%s"?',
'Are you sure you want to delete plugin "%s"?': 'Are you sure you want to delete plugin "%s"?',
'Are you sure you want to uninstall application "%s"': 'Czy na pewno chcesz usunąć aplikację "%s"',
'Are you sure you want to uninstall application "%s"?': 'Czy na pewno chcesz usunąć aplikację "%s"?',
'Are you sure you want to upgrade web2py now?': 'Are you sure you want to upgrade web2py now?',
'Available databases and tables': 'Dostępne bazy danych i tabele',
'Cannot be empty': 'Nie może być puste',
'Cannot compile: there are errors in your app.        Debug it, correct errors and try again.': 'Nie można skompilować: w Twojej aplikacji są błędy .        Znajdź je, popraw a następnie spróbój ponownie.',
'Cannot compile: there are errors in your app:': 'Cannot compile: there are errors in your app:',
'Check to delete': 'Zaznacz aby usunąć',
'Checking for upgrades...': 'Checking for upgrades...',
'Controllers': 'Kontrolery',
'Create new simple application': 'Utwórz nową aplikację',
'Current request': 'Aktualne żądanie',
'Current response': 'Aktualna odpowiedź',
'Current session': 'Aktualna sesja',
'DESIGN': 'PROJEKTUJ',
'Date and Time': 'Data i godzina',
'Delete': 'Usuń',
'Delete:': 'Usuń:',
'Deploy on Google App Engine': 'Umieść na Google App Engine',
'Design for': 'Projekt dla',
'EDIT': 'EDYTUJ',
'Edit application': 'Edycja aplikacji',
'Edit current record': 'Edytuj aktualny rekord',
'Editing Language file': 'Editing Language file',
'Editing file': 'Edycja pliku',
'Editing file "%s"': 'Edycja pliku "%s"',
'Enterprise Web Framework': 'Enterprise Web Framework',
'Error logs for "%(app)s"': 'Wpisy błędów dla "%(app)s"',
'Exception instance attributes': 'Exception instance attributes',
'Functions with no doctests will result in [passed] tests.': 'Functions with no doctests will result in [passed] tests.',
'Hello World': 'Witaj Świecie',
'If the report above contains a ticket number it indicates a failure in executing the controller, before any attempt to execute the doctests. This is usually due to an indentation error or an error outside function code.\nA green title indicates that all tests (if defined) passed. In this case test results are not shown.': 'If the report above contains a ticket number it indicates a failure in executing the controller, before any attempt to execute the doctests. This is usually due to an indentation error or an error outside function code.\nA green title indicates that all tests (if defined) passed. In this case test results are not shown.',
'Import/Export': 'Importuj/eksportuj',
'Installed applications': 'Zainstalowane aplikacje',
'Internal State': 'Stan wewnętrzny',
'Invalid Query': 'Błędne zapytanie',
'Invalid action': 'Błędna akcja',
'Language files (static strings) updated': 'Language files (static strings) updated',
'Languages': 'Tłumaczenia',
'Last saved on:': 'Ostatnio zapisany:',
'License for': 'Licencja dla',
'Login': 'Zaloguj',
'Login to the Administrative Interface': 'Logowanie do panelu administracyjnego',
'Models': 'Modele',
'Modules': 'Moduły',
'NO': 'NIE',
'New Record': 'Nowy rekord',
'New application wizard': 'New application wizard',
'New simple application': 'New simple application',
'No databases in this application': 'Brak baz danych w tej aplikacji',
'Original/Translation': 'Oryginał/tłumaczenie',
'PAM authenticated user, cannot change password here': 'PAM authenticated user, cannot change password here',
'Peeking at file': 'Podgląd pliku',
'Plugin "%s" in application': 'Plugin "%s" in application',
'Plugins': 'Plugins',
'Powered by': 'Powered by',
'Query:': 'Zapytanie:',
'Resolve Conflict file': 'Resolve Conflict file',
'Rows in table': 'Wiersze w tabeli',
'Rows selected': 'Wierszy wybranych',
'Saved file hash:': 'Suma kontrolna zapisanego pliku:',
'Static files': 'Pliki statyczne',
'Sure you want to delete this object?': 'Czy na pewno chcesz usunąć ten obiekt?',
'TM': 'TM',
'Testing application': 'Testing application',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': '"Zapytanie" jest warunkiem postaci "db.tabela1.pole1==\'wartość\'". Takie coś jak "db.tabela1.pole1==db.tabela2.pole2" oznacza SQL JOIN.',
'There are no controllers': 'Brak kontrolerów',
'There are no models': 'Brak modeli',
'There are no modules': 'Brak modułów',
'There are no static files': 'Brak plików statycznych',
'There are no translators, only default language is supported': 'Brak plików tłumaczeń, wspierany jest tylko domyślny język',
'There are no views': 'Brak widoków',
'This is the %(filename)s template': 'To jest szablon %(filename)s',
'Ticket': 'Bilet',
'To create a plugin, name a file/folder plugin_[name]': 'To create a plugin, name a file/folder plugin_[name]',
'Unable to check for upgrades': 'Nie można sprawdzić aktualizacji',
'Unable to download': 'Nie można ściągnąć',
'Unable to download app because:': 'Unable to download app because:',
'Unable to download because': 'Unable to download because',
'Update:': 'Uaktualnij:',
'Upload & install packed application': 'Upload & install packed application',
'Upload a package:': 'Upload a package:',
'Upload existing application': 'Wyślij istniejącą aplikację',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Użyj (...)&(...) jako AND, (...)|(...) jako OR oraz ~(...)  jako NOT do tworzenia bardziej skomplikowanych zapytań.',
'Use an url:': 'Use an url:',
'Version': 'Version',
'Views': 'Widoki',
'Welcome to web2py': 'Witaj w web2py',
'YES': 'TAK',
'about': 'informacje',
'additional code for your application': 'dodatkowy kod Twojej aplikacji',
'admin disabled because no admin password': 'panel administracyjny wyłączony z powodu braku hasła administracyjnego',
'admin disabled because not supported on google app engine': 'admin disabled because not supported on google apps engine',
'admin disabled because unable to access password file': 'panel administracyjny wyłączony z powodu braku dostępu do pliku z hasłem',
'administrative interface': 'administrative interface',
'and rename it (required):': 'i nadaj jej nową nazwę (wymagane):',
'and rename it:': 'i nadaj mu nową nazwę:',
'appadmin': 'administracja aplikacji',
'appadmin is disabled because insecure channel': 'appadmin is disabled because insecure channel',
'application "%s" uninstalled': 'aplikacja "%s" została odinstalowana',
'application compiled': 'aplikacja została skompilowana',
'application is compiled and cannot be designed': 'aplikacja jest skompilowana i nie może być projektowana',
'arguments': 'arguments',
'back': 'back',
'cache': 'cache',
'cache, errors and sessions cleaned': 'pamięć podręczna, bilety błędów oraz pliki sesji zostały wyczyszczone',
'cannot create file': 'nie można utworzyć pliku',
'cannot upload file "%(filename)s"': 'nie można wysłać pliku "%(filename)s"',
'change admin password': 'change admin password',
'check all': 'zaznacz wszystko',
'check for upgrades': 'check for upgrades',
'clean': 'oczyść',
'click here for online examples': 'kliknij aby przejść do interaktywnych przykładów',
'click here for the administrative interface': 'kliknij aby przejść do panelu administracyjnego',
'click to check for upgrades': 'kliknij aby sprawdzić aktualizacje',
'code': 'code',
'compile': 'skompiluj',
'compiled application removed': 'skompilowana aplikacja została usunięta',
'controllers': 'kontrolery',
'create': 'create',
'create file with filename:': 'utwórz plik o nazwie:',
'create new application:': 'utwórz nową aplikację:',
'created by': 'created by',
'crontab': 'crontab',
'currently running': 'currently running',
'currently saved or': 'aktualnie zapisany lub',
'data uploaded': 'dane wysłane',
'database': 'baza danych',
'database %s select': 'wybór z bazy danych %s',
'database administration': 'administracja bazy danych',
'db': 'baza danych',
'defines tables': 'zdefiniuj tabele',
'delete': 'usuń',
'delete all checked': 'usuń wszystkie zaznaczone',
'delete plugin': 'delete plugin',
'deploy': 'deploy',
'design': 'projektuj',
'direction: ltr': 'direction: ltr',
'done!': 'zrobione!',
'edit': 'edytuj',
'edit controller': 'edytuj kontroler',
'edit views:': 'edit views:',
'errors': 'błędy',
'export as csv file': 'eksportuj jako plik csv',
'exposes': 'eksponuje',
'extends': 'rozszerza',
'failed to reload module': 'nie udało się przeładować modułu',
'failed to reload module because:': 'failed to reload module because:',
'file "%(filename)s" created': 'plik "%(filename)s" został utworzony',
'file "%(filename)s" deleted': 'plik "%(filename)s" został usunięty',
'file "%(filename)s" uploaded': 'plik "%(filename)s" został wysłany',
'file "%(filename)s" was not deleted': 'plik "%(filename)s" nie został usunięty',
'file "%s" of %s restored': 'plik "%s" z %s został odtworzony',
'file changed on disk': 'plik na dysku został zmieniony',
'file does not exist': 'plik nie istnieje',
'file saved on %(time)s': 'plik zapisany o %(time)s',
'file saved on %s': 'plik zapisany o %s',
'help': 'pomoc',
'htmledit': 'edytuj HTML',
'includes': 'zawiera',
'insert new': 'wstaw nowy rekord tabeli',
'insert new %s': 'wstaw nowy rekord do tabeli %s',
'install': 'install',
'internal error': 'wewnętrzny błąd',
'invalid password': 'błędne hasło',
'invalid request': 'błędne zapytanie',
'invalid ticket': 'błędny bilet',
'language file "%(filename)s" created/updated': 'plik tłumaczeń "%(filename)s" został utworzony/uaktualniony',
'languages': 'pliki tłumaczeń',
'languages updated': 'pliki tłumaczeń zostały uaktualnione',
'loading...': 'wczytywanie...',
'login': 'zaloguj',
'logout': 'wyloguj',
'merge': 'merge',
'models': 'modele',
'modules': 'moduły',
'new application "%s" created': 'nowa aplikacja "%s" została utworzona',
'new plugin installed': 'new plugin installed',
'new record inserted': 'nowy rekord został wstawiony',
'next 100 rows': 'następne 100 wierszy',
'no match': 'no match',
'or import from csv file': 'lub zaimportuj z pliku csv',
'or provide app url:': 'or provide app url:',
'or provide application url:': 'lub podaj url aplikacji:',
'overwrite installed app': 'overwrite installed app',
'pack all': 'spakuj wszystko',
'pack compiled': 'spakuj skompilowane',
'pack plugin': 'pack plugin',
'password changed': 'password changed',
'plugin "%(plugin)s" deleted': 'plugin "%(plugin)s" deleted',
'previous 100 rows': 'poprzednie 100 wierszy',
'record': 'record',
'record does not exist': 'rekord nie istnieje',
'record id': 'id rekordu',
'remove compiled': 'usuń skompilowane',
'restore': 'odtwórz',
'revert': 'przywróć',
'save': 'zapisz',
'selected': 'zaznaczone',
'session expired': 'sesja wygasła',
'shell': 'powłoka',
'site': 'strona główna',
'some files could not be removed': 'niektóre pliki nie mogły zostać usunięte',
'start wizard': 'start wizard',
'state': 'stan',
'static': 'pliki statyczne',
'submit': 'submit',
'table': 'tabela',
'test': 'testuj',
'the application logic, each URL path is mapped in one exposed function in the controller': 'logika aplikacji, każda ścieżka URL jest mapowana na jedną z funkcji eksponowanych w kontrolerze',
'the data representation, define database tables and sets': 'reprezentacja danych, definicje zbiorów i tabel bazy danych',
'the presentations layer, views are also known as templates': 'warstwa prezentacji, widoki zwane są również szablonami',
'these files are served without processing, your images go here': 'pliki obsługiwane bez interpretacji, to jest miejsce na Twoje obrazy',
'to  previous version.': 'do  poprzedniej wersji.',
'translation strings for the application': 'ciągi tłumaczeń dla aplikacji',
'try': 'spróbój',
'try something like': 'spróbój czegos takiego jak',
'unable to create application "%s"': 'nie można utworzyć aplikacji "%s"',
'unable to delete file "%(filename)s"': 'nie można usunąć pliku "%(filename)s"',
'unable to delete file plugin "%(plugin)s"': 'unable to delete file plugin "%(plugin)s"',
'unable to parse csv file': 'nie można sparsować pliku csv',
'unable to uninstall "%s"': 'nie można odinstalować "%s"',
'unable to upgrade because "%s"': 'unable to upgrade because "%s"',
'uncheck all': 'odznacz wszystko',
'uninstall': 'odinstaluj',
'update': 'uaktualnij',
'update all languages': 'uaktualnij wszystkie pliki tłumaczeń',
'upgrade web2py now': 'upgrade web2py now',
'upload application:': 'wyślij plik aplikacji:',
'upload file:': 'wyślij plik:',
'upload plugin file:': 'upload plugin file:',
'variables': 'variables',
'versioning': 'versioning',
'view': 'widok',
'views': 'widoki',
'web2py Recent Tweets': 'najnowsze tweety web2py',
'web2py is up to date': 'web2py jest aktualne',
'web2py upgraded; please restart it': 'web2py upgraded; please restart it',
}

########NEW FILE########
__FILENAME__ = pl
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"Uaktualnij" jest dodatkowym wyrażeniem postaci "pole1=\'nowawartość\'". Nie możesz uaktualnić lub usunąć wyników z JOIN:',
'%Y-%m-%d': '%Y-%m-%d',
'%Y-%m-%d %H:%M:%S': '%Y-%m-%d %H:%M:%S',
'%s rows deleted': 'Wierszy usuniętych: %s',
'%s rows updated': 'Wierszy uaktualnionych: %s',
'(requires internet access)': '(requires internet access)',
'(something like "it-it")': '(coś podobnego do "it-it")',
'A new version of web2py is available': 'Nowa wersja web2py jest dostępna',
'A new version of web2py is available: %s': 'Nowa wersja web2py jest dostępna: %s',
'ATTENTION: Login requires a secure (HTTPS) connection or running on localhost.': 'UWAGA: Wymagane jest bezpieczne (HTTPS) połączenie lub połączenie z lokalnego adresu.',
'ATTENTION: TESTING IS NOT THREAD SAFE SO DO NOT PERFORM MULTIPLE TESTS CONCURRENTLY.': 'UWAGA: TESTOWANIE NIE JEST BEZPIECZNE W ŚRODOWISKU WIELOWĄTKOWYM, TAK WIĘC NIE URUCHAMIAJ WIELU TESTÓW JEDNOCZEŚNIE.',
'ATTENTION: you cannot edit the running application!': 'UWAGA: nie można edytować uruchomionych aplikacji!',
'About': 'Informacje o',
'About application': 'Informacje o aplikacji',
'Additional code for your application': 'Additional code for your application',
'Admin is disabled because insecure channel': 'Panel administracyjny wyłączony z powodu braku bezpiecznego połączenia',
'Admin is disabled because unsecure channel': 'Panel administracyjny wyłączony z powodu braku bezpiecznego połączenia',
'Administrator Password:': 'Hasło administratora:',
'Application name:': 'Application name:',
'Are you sure you want to delete file "%s"?': 'Czy na pewno chcesz usunąć plik "%s"?',
'Are you sure you want to delete plugin "%s"?': 'Czy na pewno chcesz usunąć wtyczkę "%s"?',
'Are you sure you want to uninstall application "%s"': 'Czy na pewno chcesz usunąć aplikację "%s"',
'Are you sure you want to uninstall application "%s"?': 'Czy na pewno chcesz usunąć aplikację "%s"?',
'Are you sure you want to upgrade web2py now?': 'Are you sure you want to upgrade web2py now?',
'Available databases and tables': 'Dostępne bazy danych i tabele',
'Cannot be empty': 'Nie może być puste',
'Cannot compile: there are errors in your app.        Debug it, correct errors and try again.': 'Nie można skompilować: w Twojej aplikacji są błędy .        Znajdź je, popraw a następnie spróbój ponownie.',
'Cannot compile: there are errors in your app:': 'Cannot compile: there are errors in your app:',
'Check to delete': 'Zaznacz aby usunąć',
'Checking for upgrades...': 'Sprawdzanie aktualizacji...',
'Controllers': 'Kontrolery',
'Create new simple application': 'Utwórz nową aplikację',
'Current request': 'Aktualne żądanie',
'Current response': 'Aktualna odpowiedź',
'Current session': 'Aktualna sesja',
'DESIGN': 'PROJEKTUJ',
'Date and Time': 'Data i godzina',
'Delete': 'Usuń',
'Delete:': 'Usuń:',
'Deploy on Google App Engine': 'Umieść na Google App Engine',
'Design for': 'Projekt dla',
'EDIT': 'EDYTUJ',
'Edit application': 'Edycja aplikacji',
'Edit current record': 'Edytuj aktualny rekord',
'Editing Language file': 'Edytuj plik tłumaczeń',
'Editing file': 'Edycja pliku',
'Editing file "%s"': 'Edycja pliku "%s"',
'Enterprise Web Framework': 'Enterprise Web Framework',
'Error logs for "%(app)s"': 'Wpisy błędów dla "%(app)s"',
'Exception instance attributes': 'Exception instance attributes',
'Functions with no doctests will result in [passed] tests.': 'Funkcje bez doctestów będą dołączone do [zaliczonych] testów.',
'Hello World': 'Witaj Świecie',
'If the report above contains a ticket number it indicates a failure in executing the controller, before any attempt to execute the doctests. This is usually due to an indentation error or an error outside function code.\nA green title indicates that all tests (if defined) passed. In this case test results are not shown.': 'Jeżeli powyższy raport zawiera numer biletu błędu, oznacza to błąd podczas wykonywania kontrolera przez próbą uruchomienia doctestów. Zazwyczaj jest to spowodowane nieprawidłowymi wcięciami linii kodu lub błędami w module poza ciałem funkcji.\nTytuł w kolorze zielonym oznacza, ze wszystkie (zdefiniowane) testy zakończyły się sukcesem. W tej sytuacji ich wyniki nie są pokazane.',
'Import/Export': 'Importuj/eksportuj',
'Installed applications': 'Zainstalowane aplikacje',
'Internal State': 'Stan wewnętrzny',
'Invalid Query': 'Błędne zapytanie',
'Invalid action': 'Błędna akcja',
'Language files (static strings) updated': 'Pliki tłumaczeń (ciągi statyczne) zostały uaktualnione',
'Languages': 'Tłumaczenia',
'Last saved on:': 'Ostatnio zapisany:',
'License for': 'Licencja dla',
'Login': 'Zaloguj',
'Login to the Administrative Interface': 'Logowanie do panelu administracyjnego',
'Models': 'Modele',
'Modules': 'Moduły',
'NO': 'NIE',
'New Record': 'Nowy rekord',
'New application wizard': 'New application wizard',
'New simple application': 'New simple application',
'No databases in this application': 'Brak baz danych w tej aplikacji',
'Original/Translation': 'Oryginał/tłumaczenie',
'PAM authenticated user, cannot change password here': 'PAM authenticated user, cannot change password here',
'Peeking at file': 'Podgląd pliku',
'Plugin "%s" in application': 'Wtyczka "%s" w aplikacji',
'Plugins': 'Wtyczki',
'Powered by': 'Zasilane przez',
'Query:': 'Zapytanie:',
'Resolve Conflict file': 'Rozwiąż konflikt plików',
'Rows in table': 'Wiersze w tabeli',
'Rows selected': 'Wierszy wybranych',
'Saved file hash:': 'Suma kontrolna zapisanego pliku:',
'Searching:': 'Searching:',
'Static files': 'Pliki statyczne',
'Sure you want to delete this object?': 'Czy na pewno chcesz usunąć ten obiekt?',
'TM': 'TM',
'Testing application': 'Testowanie aplikacji',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': '"Zapytanie" jest warunkiem postaci "db.tabela1.pole1==\'wartość\'". Takie coś jak "db.tabela1.pole1==db.tabela2.pole2" oznacza SQL JOIN.',
'The application logic, each URL path is mapped in one exposed function in the controller': 'The application logic, each URL path is mapped in one exposed function in the controller',
'The data representation, define database tables and sets': 'The data representation, define database tables and sets',
'The presentations layer, views are also known as templates': 'The presentations layer, views are also known as templates',
'There are no controllers': 'Brak kontrolerów',
'There are no models': 'Brak modeli',
'There are no modules': 'Brak modułów',
'There are no plugins': 'There are no plugins',
'There are no static files': 'Brak plików statycznych',
'There are no translators, only default language is supported': 'Brak plików tłumaczeń, wspierany jest tylko domyślny język',
'There are no views': 'Brak widoków',
'These files are served without processing, your images go here': 'These files are served without processing, your images go here',
'This is the %(filename)s template': 'To jest szablon %(filename)s',
'Ticket': 'Bilet',
'To create a plugin, name a file/folder plugin_[name]': 'Aby utworzyć wtyczkę, nazwij plik/katalog plugin_[nazwa]',
'Translation strings for the application': 'Translation strings for the application',
'Unable to check for upgrades': 'Nie można sprawdzić aktualizacji',
'Unable to download': 'Nie można ściągnąć',
'Unable to download app': 'Nie można ściągnąć aplikacji',
'Unable to download app because:': 'Unable to download app because:',
'Unable to download because': 'Unable to download because',
'Update:': 'Uaktualnij:',
'Upload & install packed application': 'Upload & install packed application',
'Upload a package:': 'Upload a package:',
'Upload existing application': 'Wyślij istniejącą aplikację',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Użyj (...)&(...) jako AND, (...)|(...) jako OR oraz ~(...)  jako NOT do tworzenia bardziej skomplikowanych zapytań.',
'Use an url:': 'Use an url:',
'Version': 'Wersja',
'Views': 'Widoki',
'Welcome to web2py': 'Witaj w web2py',
'YES': 'TAK',
'about': 'informacje',
'additional code for your application': 'dodatkowy kod Twojej aplikacji',
'admin disabled because no admin password': 'panel administracyjny wyłączony z powodu braku hasła administracyjnego',
'admin disabled because not supported on google app engine': 'panel administracyjny wyłączony z powodu braku wsparcia na google apps engine',
'admin disabled because unable to access password file': 'panel administracyjny wyłączony z powodu braku dostępu do pliku z hasłem',
'administrative interface': 'administrative interface',
'and rename it (required):': 'i nadaj jej nową nazwę (wymagane):',
'and rename it:': 'i nadaj mu nową nazwę:',
'appadmin': 'administracja aplikacji',
'appadmin is disabled because insecure channel': 'administracja aplikacji wyłączona z powodu braku bezpiecznego połączenia',
'application "%s" uninstalled': 'aplikacja "%s" została odinstalowana',
'application compiled': 'aplikacja została skompilowana',
'application is compiled and cannot be designed': 'aplikacja jest skompilowana i nie może być projektowana',
'arguments': 'arguments',
'back': 'wstecz',
'cache': 'cache',
'cache, errors and sessions cleaned': 'pamięć podręczna, bilety błędów oraz pliki sesji zostały wyczyszczone',
'cannot create file': 'nie można utworzyć pliku',
'cannot upload file "%(filename)s"': 'nie można wysłać pliku "%(filename)s"',
'change admin password': 'change admin password',
'check all': 'zaznacz wszystko',
'check for upgrades': 'check for upgrades',
'clean': 'oczyść',
'click here for online examples': 'kliknij aby przejść do interaktywnych przykładów',
'click here for the administrative interface': 'kliknij aby przejść do panelu administracyjnego',
'click to check for upgrades': 'kliknij aby sprawdzić aktualizacje',
'code': 'code',
'collapse/expand all': 'collapse/expand all',
'compile': 'skompiluj',
'compiled application removed': 'skompilowana aplikacja została usunięta',
'controllers': 'kontrolery',
'create': 'create',
'create file with filename:': 'utwórz plik o nazwie:',
'create new application:': 'utwórz nową aplikację:',
'created by': 'utworzone przez',
'crontab': 'crontab',
'currently running': 'currently running',
'currently saved or': 'aktualnie zapisany lub',
'data uploaded': 'dane wysłane',
'database': 'baza danych',
'database %s select': 'wybór z bazy danych %s',
'database administration': 'administracja bazy danych',
'db': 'baza danych',
'defines tables': 'zdefiniuj tabele',
'delete': 'usuń',
'delete all checked': 'usuń wszystkie zaznaczone',
'delete plugin': 'usuń wtyczkę',
'deploy': 'deploy',
'design': 'projektuj',
'direction: ltr': 'direction: ltr',
'done!': 'zrobione!',
'download layouts': 'download layouts',
'download plugins': 'download plugins',
'edit': 'edytuj',
'edit controller': 'edytuj kontroler',
'edit views:': 'edit views:',
'errors': 'błędy',
'export as csv file': 'eksportuj jako plik csv',
'exposes': 'eksponuje',
'extends': 'rozszerza',
'failed to reload module': 'nie udało się przeładować modułu',
'failed to reload module because:': 'failed to reload module because:',
'file "%(filename)s" created': 'plik "%(filename)s" został utworzony',
'file "%(filename)s" deleted': 'plik "%(filename)s" został usunięty',
'file "%(filename)s" uploaded': 'plik "%(filename)s" został wysłany',
'file "%(filename)s" was not deleted': 'plik "%(filename)s" nie został usunięty',
'file "%s" of %s restored': 'plik "%s" z %s został odtworzony',
'file changed on disk': 'plik na dysku został zmieniony',
'file does not exist': 'plik nie istnieje',
'file saved on %(time)s': 'plik zapisany o %(time)s',
'file saved on %s': 'plik zapisany o %s',
'files': 'files',
'filter': 'filter',
'help': 'pomoc',
'htmledit': 'edytuj HTML',
'includes': 'zawiera',
'insert new': 'wstaw nowy rekord tabeli',
'insert new %s': 'wstaw nowy rekord do tabeli %s',
'install': 'install',
'internal error': 'wewnętrzny błąd',
'invalid password': 'błędne hasło',
'invalid request': 'błędne zapytanie',
'invalid ticket': 'błędny bilet',
'language file "%(filename)s" created/updated': 'plik tłumaczeń "%(filename)s" został utworzony/uaktualniony',
'languages': 'pliki tłumaczeń',
'languages updated': 'pliki tłumaczeń zostały uaktualnione',
'loading...': 'wczytywanie...',
'login': 'zaloguj',
'logout': 'wyloguj',
'merge': 'zespól',
'models': 'modele',
'modules': 'moduły',
'new application "%s" created': 'nowa aplikacja "%s" została utworzona',
'new plugin installed': 'nowa wtyczka została zainstalowana',
'new record inserted': 'nowy rekord został wstawiony',
'next 100 rows': 'następne 100 wierszy',
'no match': 'no match',
'or import from csv file': 'lub zaimportuj z pliku csv',
'or provide app url:': 'or provide app url:',
'or provide application url:': 'lub podaj url aplikacji:',
'overwrite installed app': 'overwrite installed app',
'pack all': 'spakuj wszystko',
'pack compiled': 'spakuj skompilowane',
'pack plugin': 'spakuj wtyczkę',
'password changed': 'password changed',
'plugin "%(plugin)s" deleted': 'wtyczka "%(plugin)s" została usunięta',
'plugins': 'plugins',
'previous 100 rows': 'poprzednie 100 wierszy',
'record': 'rekord',
'record does not exist': 'rekord nie istnieje',
'record id': 'ID rekordu',
'remove compiled': 'usuń skompilowane',
'restore': 'odtwórz',
'revert': 'przywróć',
'save': 'zapisz',
'selected': 'zaznaczone',
'session expired': 'sesja wygasła',
'shell': 'powłoka',
'site': 'strona główna',
'some files could not be removed': 'niektóre pliki nie mogły zostać usunięte',
'start wizard': 'start wizard',
'state': 'stan',
'static': 'pliki statyczne',
'submit': 'wyślij',
'table': 'tabela',
'test': 'testuj',
'the application logic, each URL path is mapped in one exposed function in the controller': 'logika aplikacji, każda ścieżka URL jest mapowana na jedną z funkcji eksponowanych w kontrolerze',
'the data representation, define database tables and sets': 'reprezentacja danych, definicje zbiorów i tabel bazy danych',
'the presentations layer, views are also known as templates': 'warstwa prezentacji, widoki zwane są również szablonami',
'these files are served without processing, your images go here': 'pliki obsługiwane bez interpretacji, to jest miejsce na Twoje obrazy',
'to  previous version.': 'do  poprzedniej wersji.',
'translation strings for the application': 'ciągi tłumaczeń dla aplikacji',
'try': 'spróbój',
'try something like': 'spróbój czegos takiego jak',
'unable to create application "%s"': 'nie można utworzyć aplikacji "%s"',
'unable to delete file "%(filename)s"': 'nie można usunąć pliku "%(filename)s"',
'unable to delete file plugin "%(plugin)s"': 'nie można usunąc pliku wtyczki "%(plugin)s"',
'unable to parse csv file': 'nie można sparsować pliku csv',
'unable to uninstall "%s"': 'nie można odinstalować "%s"',
'unable to upgrade because "%s"': 'unable to upgrade because "%s"',
'uncheck all': 'odznacz wszystko',
'uninstall': 'odinstaluj',
'update': 'uaktualnij',
'update all languages': 'uaktualnij wszystkie pliki tłumaczeń',
'upgrade web2py now': 'upgrade web2py now',
'upload': 'upload',
'upload application:': 'wyślij plik aplikacji:',
'upload file:': 'wyślij plik:',
'upload plugin file:': 'wyślij plik wtyczki:',
'variables': 'variables',
'versioning': 'versioning',
'view': 'widok',
'views': 'widoki',
'web2py Recent Tweets': 'najnowsze tweety web2py',
'web2py is up to date': 'web2py jest aktualne',
'web2py upgraded; please restart it': 'web2py upgraded; please restart it',
}

########NEW FILE########
__FILENAME__ = pt-br
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"update" é uma expressão opcional como "campo1=\'novo_valor\'". Não é permitido atualizar ou apagar resultados de um JOIN',
'%Y-%m-%d': '%d/%m/%Y',
'%Y-%m-%d %H:%M:%S': '%d/%m/%Y %H:%M:%S',
'%s rows deleted': '%s registros apagados',
'%s rows updated': '%s registros atualizados',
'(requires internet access)': '(requer acesso a internet)',
'(something like "it-it")': '(algo como "it-it")',
'A new version of web2py is available': 'Está disponível uma nova versão do web2py',
'A new version of web2py is available: %s': 'Está disponível uma nova versão do web2py: %s',
'ATTENTION: Login requires a secure (HTTPS) connection or running on localhost.': 'ATENÇÃO o login requer uma conexão segura (HTTPS) ou executar de localhost.',
'ATTENTION: TESTING IS NOT THREAD SAFE SO DO NOT PERFORM MULTIPLE TESTS CONCURRENTLY.': 'ATENÇÃO OS TESTES NÃO THREAD SAFE, NÃO EFETUE MÚLTIPLOS TESTES AO MESMO TEMPO.',
'ATTENTION: you cannot edit the running application!': 'ATENÇÃO: Não pode modificar a aplicação em execução!',
'About': 'Sobre',
'About application': 'Sobre a aplicação',
'Additional code for your application': 'Additional code for your application',
'Admin is disabled because insecure channel': 'Admin desabilitado pois o canal não é seguro',
'Admin is disabled because unsecure channel': 'Admin desabilitado pois o canal não é seguro',
'Admin language': 'Linguagem do Admin',
'Administrator Password:': 'Senha de administrador:',
'Application name:': 'Nome da aplicação:',
'Are you sure you want to delete file "%s"?': 'Tem certeza que deseja apagar o arquivo "%s"?',
'Are you sure you want to delete plugin "%s"?': 'Tem certeza que deseja apagar o plugin "%s"?',
'Are you sure you want to uninstall application "%s"': 'Tem certeza que deseja apagar a aplicação "%s"?',
'Are you sure you want to uninstall application "%s"?': 'Tem certeza que deseja apagar a aplicação "%s"?',
'Are you sure you want to upgrade web2py now?': 'Tem certeza que deseja atualizar o web2py agora?',
'Available databases and tables': 'Bancos de dados e tabelas disponíveis',
'Cannot be empty': 'Não pode ser vazio',
'Cannot compile: there are errors in your app.        Debug it, correct errors and try again.': 'Não é possível compilar: Existem erros em sua aplicação.       Depure, corrija os errros e tente novamente',
'Cannot compile: there are errors in your app:': 'Não é possível compilar: Existem erros em sua aplicação',
'Change Password': 'Trocar Senha',
'Check to delete': 'Marque para apagar',
'Checking for upgrades...': 'Buscando atualizações...',
'Click row to expand traceback': 'Clique em uma coluna para expandir o log do erro',
'Client IP': 'IP do cliente',
'Controllers': 'Controladores',
'Count': 'Contagem',
'Create new application using the Wizard': 'Criar nova aplicação utilizando o assistente',
'Create new simple application': 'Crie uma nova aplicação',
'Current request': 'Requisição atual',
'Current response': 'Resposta atual',
'Current session': 'Sessão atual',
'DESIGN': 'Projeto',
'Date and Time': 'Data e Hora',
'Delete': 'Apague',
'Delete:': 'Apague:',
'Deploy on Google App Engine': 'Publicar no Google App Engine',
'Description': 'Descrição',
'Design for': 'Projeto de',
'Detailed traceback description': 'Detailed traceback description',
'E-mail': 'E-mail',
'EDIT': 'EDITAR',
'Edit Profile': 'Editar Perfil',
'Edit application': 'Editar aplicação',
'Edit current record': 'Editar o registro atual',
'Editing Language file': 'Editando arquivo de linguagem',
'Editing file': 'Editando arquivo',
'Editing file "%s"': 'Editando arquivo "%s"',
'Enterprise Web Framework': 'Framework web empresarial',
'Error': 'Erro',
'Error logs for "%(app)s"': 'Logs de erro para "%(app)s"',
'Error snapshot': 'Error snapshot',
'Error ticket': 'Error ticket',
'Exception instance attributes': 'Atributos da instancia de excessão',
'File': 'Arquivo',
'First name': 'Nome',
'Frames': 'Frames',
'Functions with no doctests will result in [passed] tests.': 'Funções sem doctests resultarão em testes [aceitos].',
'Group ID': 'ID do Grupo',
'Hello World': 'Olá Mundo',
'If the report above contains a ticket number it indicates a failure in executing the controller, before any attempt to execute the doctests. This is usually due to an indentation error or an error outside function code.\nA green title indicates that all tests (if defined) passed. In this case test results are not shown.': 'Se o relatório acima contém um número de ticket, isso indica uma falha no controlador em execução, antes de tantar executar os doctests. Isto acontece geralmente por erro de endentação ou erro fora do código da função.\nO titulo em verde indica que os testes (se definidos) passaram. Neste caso os testes não são mostrados.',
'Import/Export': 'Importar/Exportar',
'Installed applications': 'Aplicações instaladas',
'Internal State': 'Estado Interno',
'Invalid Query': 'Consulta inválida',
'Invalid action': 'Ação inválida',
'Invalid email': 'E-mail inválido',
'Language files (static strings) updated': 'Arquivos de linguagem (textos estáticos) atualizados',
'Languages': 'Linguagens',
'Last name': 'Sobrenome',
'Last saved on:': 'Salvo em:',
'License for': 'Licença para',
'Login': 'Entrar',
'Login to the Administrative Interface': 'Entrar na interface adminitrativa',
'Logout': 'Sair',
'Lost Password': 'Senha perdida',
'Models': 'Modelos',
'Modules': 'Módulos',
'NO': 'NÃO',
'Name': 'Nome',
'New Record': 'Novo registro',
'New application wizard': 'Assistente para novas aplicações ',
'New simple application': 'Nova aplicação básica',
'No databases in this application': 'Não existem bancos de dados nesta aplicação',
'Origin': 'Origem',
'Original/Translation': 'Original/Tradução',
'PAM authenticated user, cannot change password here': 'usuario autenticado por PAM, não pode alterar a senha por aqui',
'Password': 'Senha',
'Peeking at file': 'Visualizando arquivo',
'Plugin "%s" in application': 'Plugin "%s" na aplicação',
'Plugins': 'Plugins',
'Powered by': 'Este site utiliza',
'Query:': 'Consulta:',
'Record ID': 'ID do Registro',
'Register': 'Registrar-se',
'Registration key': 'Chave de registro',
'Resolve Conflict file': 'Arquivo de resolução de conflito',
'Role': 'Papel',
'Rows in table': 'Registros na tabela',
'Rows selected': 'Registros selecionados',
'Saved file hash:': 'Hash do arquivo salvo:',
'Searching:': 'Searching:',
'Static files': 'Arquivos estáticos',
'Sure you want to delete this object?': 'Tem certeza que deseja apaagr este objeto?',
'TM': 'MR',
'Table name': 'Nome da tabela',
'Testing application': 'Testando a aplicação',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'A "consulta" é uma condição como "db.tabela.campo1==\'valor\'". Algo como "db.tabela1.campo1==db.tabela2.campo2" resulta em um JOIN SQL.',
'The application logic, each URL path is mapped in one exposed function in the controller': 'The application logic, each URL path is mapped in one exposed function in the controller',
'The data representation, define database tables and sets': 'The data representation, define database tables and sets',
'The presentations layer, views are also known as templates': 'The presentations layer, views are also known as templates',
'There are no controllers': 'Não existem controllers',
'There are no models': 'Não existem modelos',
'There are no modules': 'Não existem módulos',
'There are no plugins': 'There are no plugins',
'There are no static files': 'Não existem arquicos estáticos',
'There are no translators, only default language is supported': 'Não há traduções, somente a linguagem padrão é suportada',
'There are no views': 'Não existem visões',
'These files are served without processing, your images go here': 'These files are served without processing, your images go here',
'This is the %(filename)s template': 'Este é o template %(filename)s',
'Ticket': 'Ticket',
'Ticket ID': 'Ticket ID',
'Timestamp': 'Data Atual',
'To create a plugin, name a file/folder plugin_[name]': 'Para criar um plugin, nomeio um arquivo/pasta como plugin_[nome]',
'Traceback': 'Traceback',
'Translation strings for the application': 'Translation strings for the application',
'Unable to check for upgrades': 'Não é possível checar as atualizações',
'Unable to download': 'Não é possível efetuar o download',
'Unable to download app': 'Não é possível baixar a aplicação',
'Unable to download app because:': 'Não é possível baixar a aplicação porque:',
'Unable to download because': 'Não é possível baixar porque',
'Update:': 'Atualizar:',
'Upload & install packed application': 'Faça upload e instale uma aplicação empacotada',
'Upload a package:': 'Faça upload de um pacote:',
'Upload existing application': 'Faça upload de uma aplicação existente',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Use (...)&(...) para AND, (...)|(...) para OR, y ~(...) para NOT, para criar consultas mais complexas.',
'Use an url:': 'Use uma url:',
'User ID': 'ID do Usuario',
'Version': 'Versão',
'Views': 'Visões',
'Welcome to web2py': 'Bem-vindo ao web2py',
'YES': 'SIM',
'about': 'sobre',
'additional code for your application': 'código adicional para sua aplicação',
'admin disabled because no admin password': ' admin desabilitado por falta de senha definida',
'admin disabled because not supported on google app engine': 'admin dehabilitado, não é soportado no GAE',
'admin disabled because unable to access password file': 'admin desabilitado, não foi possível ler o arquivo de senha',
'administrative interface': 'interface administrativa',
'and rename it (required):': 'e renomeie (requerido):',
'and rename it:': ' e renomeie:',
'appadmin': 'appadmin',
'appadmin is disabled because insecure channel': 'admin desabilitado, canal inseguro',
'application "%s" uninstalled': 'aplicação "%s" desinstalada',
'application compiled': 'aplicação compilada',
'application is compiled and cannot be designed': 'A aplicação está compilada e não pode ser modificada',
'arguments': 'argumentos',
'back': 'voltar',
'browse': 'buscar',
'cache': 'cache',
'cache, errors and sessions cleaned': 'cache, erros e sessões eliminadas',
'cannot create file': 'Não é possível criar o arquivo',
'cannot upload file "%(filename)s"': 'não é possível fazer upload do arquivo "%(filename)s"',
'change admin password': 'mudar senha de administrador',
'check all': 'marcar todos',
'check for upgrades': 'checar por atualizações',
'clean': 'limpar',
'click here for online examples': 'clique para ver exemplos online',
'click here for the administrative interface': 'Clique aqui para acessar a interface administrativa',
'click to check for upgrades': 'clique aqui para checar por atualizações',
'click to open': 'clique para abrir',
'code': 'código',
'collapse/expand all': 'collapse/expand all',
'commit (mercurial)': 'commit (mercurial)',
'compile': 'compilar',
'compiled application removed': 'aplicação compilada removida',
'controllers': 'controladores',
'create': 'criar',
'create file with filename:': 'criar um arquivo com o nome:',
'create new application:': 'nome da nova aplicação:',
'created by': 'criado por',
'crontab': 'crontab',
'currently running': 'Executando',
'currently saved or': 'Atualmente salvo ou',
'customize me!': 'Modifique-me',
'data uploaded': 'Dados enviados',
'database': 'banco de dados',
'database %s select': 'Seleção no banco de dados %s',
'database administration': 'administração de banco de dados',
'db': 'db',
'defines tables': 'define as tabelas',
'delete': 'apagar',
'delete all checked': 'apagar marcados',
'delete plugin': 'apagar plugin',
'deploy': 'publicar',
'design': 'modificar',
'direction: ltr': 'direção: ltr',
'done!': 'feito!',
'download layouts': 'download layouts',
'download plugins': 'download plugins',
'edit': 'editar',
'edit controller': 'editar controlador',
'edit views:': 'editar visões:',
'errors': 'erros',
'export as csv file': 'exportar como arquivo CSV',
'exposes': 'expõe',
'extends': 'estende',
'failed to reload module': 'Falha ao recarregar o módulo',
'failed to reload module because:': 'falha ao recarregar o módulo por:',
'file "%(filename)s" created': 'arquivo "%(filename)s" criado',
'file "%(filename)s" deleted': 'arquivo "%(filename)s" apagado',
'file "%(filename)s" uploaded': 'arquivo "%(filename)s" enviado',
'file "%(filename)s" was not deleted': 'arquivo "%(filename)s" não foi apagado',
'file "%s" of %s restored': 'arquivo "%s" de %s restaurado',
'file changed on disk': 'arquivo modificado no disco',
'file does not exist': 'arquivo não existe',
'file saved on %(time)s': 'arquivo salvo em %(time)s',
'file saved on %s': 'arquivo salvo em %s',
'files': 'files',
'filter': 'filter',
'help': 'ajuda',
'htmledit': 'htmledit',
'includes': 'inclui',
'insert new': 'inserir novo',
'insert new %s': 'inserir novo %s',
'inspect attributes': 'inspect attributes',
'install': 'instalar',
'internal error': 'erro interno',
'invalid password': 'senha inválida',
'invalid request': 'solicitação inválida',
'invalid ticket': 'ticket inválido',
'language file "%(filename)s" created/updated': 'arquivo de linguagem "%(filename)s" criado/atualizado',
'languages': 'linguagens',
'languages updated': 'linguagens atualizadas',
'loading...': 'carregando...',
'locals': 'locals',
'login': 'inicio de sessão',
'logout': 'finalizar sessão',
'manage': 'gerenciar',
'merge': 'juntar',
'models': 'modelos',
'modules': 'módulos',
'new application "%s" created': 'nova aplicação "%s" criada',
'new plugin installed': 'novo plugin instalado',
'new record inserted': 'novo registro inserido',
'next 100 rows': 'próximos 100 registros',
'no match': 'não encontrado',
'or import from csv file': 'ou importar de um arquivo CSV',
'or provide app url:': 'ou forneça a url de uma aplicação:',
'or provide application url:': 'ou forneça a url de uma aplicação:',
'overwrite installed app': 'sobrescrever aplicação instalada',
'pack all': 'criar pacote',
'pack compiled': 'criar pacote compilado',
'pack plugin': 'empacotar plugin',
'password changed': 'senha alterada',
'plugin "%(plugin)s" deleted': 'plugin "%(plugin)s" eliminado',
'plugins': 'plugins',
'previous 100 rows': '100 registros anteriores',
'record': 'registro',
'record does not exist': 'o registro não existe',
'record id': 'id do registro',
'remove compiled': 'eliminar compilados',
'request': 'request',
'response': 'response',
'restore': 'restaurar',
'revert': 'reverter',
'save': 'salvar',
'selected': 'selecionado(s)',
'session': 'session',
'session expired': 'sessão expirada',
'shell': 'Terminal',
'site': 'site',
'some files could not be removed': 'alguns arquicos não puderam ser removidos',
'start wizard': 'iniciar assistente',
'state': 'estado',
'static': 'estáticos',
'submit': 'enviar',
'table': 'tabela',
'test': 'testar',
'the application logic, each URL path is mapped in one exposed function in the controller': 'A lógica da aplicação, cada URL é mapeada para uma função exposta pelo controlador',
'the data representation, define database tables and sets': 'A representação dos dadps, define tabelas e estruturas de dados',
'the presentations layer, views are also known as templates': 'A camada de apresentação, As visões também são chamadas de templates',
'these files are served without processing, your images go here': 'Estes arquivos são servidos sem processamento, suas imagens ficam aqui',
'to  previous version.': 'para a versão anterior.',
'translation strings for the application': 'textos traduzidos para a aplicação',
'try': 'tente',
'try something like': 'tente algo como',
'unable to create application "%s"': 'não é possível criar a aplicação "%s"',
'unable to delete file "%(filename)s"': 'não é possível criar o arquico "%(filename)s"',
'unable to delete file plugin "%(plugin)s"': 'não é possível criar o plugin "%(plugin)s"',
'unable to parse csv file': 'não é possível analisar o arquivo CSV',
'unable to uninstall "%s"': 'não é possível instalar "%s"',
'unable to upgrade because "%s"': 'não é possível atualizar porque "%s"',
'uncheck all': 'desmarcar todos',
'uninstall': 'desinstalar',
'update': 'atualizar',
'update all languages': 'atualizar todas as linguagens',
'upgrade web2py now': 'atualize o web2py agora',
'upload': 'upload',
'upload application:': 'Fazer upload de uma aplicação:',
'upload file:': 'Enviar arquivo:',
'upload plugin file:': 'Enviar arquivo de plugin:',
'variables': 'variáveis',
'versioning': 'versionamento',
'view': 'visão',
'views': 'visões',
'web2py Recent Tweets': 'Tweets Recentes de @web2py',
'web2py is up to date': 'web2py está atualizado',
'web2py upgraded; please restart it': 'web2py atualizado; favor reiniciar',
}

########NEW FILE########
__FILENAME__ = zh-cn
# coding: utf8
{
'"browse"': '游览',
'"save"': '"保存"',
'"submit"': '"提交"',
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"更新"是可配置项 如 "field1=\'newvalue\'",你无法在JOIN 中更新或删除',
'%Y-%m-%d': '%Y-%m-%d',
'%Y-%m-%d %H:%M:%S': '%Y-%m-%d %H:%M:%S',
'%s rows deleted': '%s 行已删',
'%s rows updated': '%s 行更新',
'(requires internet access)': '(requires internet access)',
'(something like "it-it")': '(就酱 "it-it")',
'A new version of web2py is available': '新版本web2py已经可用',
'A new version of web2py is available: %s': '新版本web2py已经可用: %s',
'ATTENTION: Login requires a secure (HTTPS) connection or running on localhost.': '',
'ATTENTION: TESTING IS NOT THREAD SAFE SO DO NOT PERFORM MULTIPLE TESTS CONCURRENTLY.': '',
'ATTENTION: you cannot edit the running application!': '注意: 不能修改正在运行中的应用!',
'About': '关于',
'About application': '关于这个应用',
'Admin is disabled because insecure channel': '管理因不安全通道而关闭',
'Admin is disabled because unsecure channel': '管理因不稳定通道而关闭',
'Admin language': 'Admin language',
'Administrator Password:': '管理员密码:',
'Application name:': 'Application name:',
'Are you sure you want to delete file "%s"?': '你真想删除文件"%s"?',
'Are you sure you want to delete plugin "%s"?': 'Are you sure you want to delete plugin "%s"?',
'Are you sure you want to uninstall application "%s"': '你真确定要卸载应用 "%s"',
'Are you sure you want to uninstall application "%s"?': '你真确定要卸载应用 "%s" ?',
'Are you sure you want to upgrade web2py now?': 'Are you sure you want to upgrade web2py now?',
'Available databases and tables': '可用数据库/表',
'Cannot be empty': '不能不填',
'Cannot compile: there are errors in your app.        Debug it, correct errors and try again.': '无法编译: 应用中有错误,请修订后再试.',
'Cannot compile: there are errors in your app:': 'Cannot compile: there are errors in your app:',
'Change Password': '修改密码',
'Check to delete': '检验删除',
'Checking for upgrades...': '是否有升级版本检查ing...',
'Client IP': '客户端IP',
'Controllers': '控制器s',
'Create new simple application': '创建一个新应用',
'Current request': '当前请求',
'Current response': '当前返回',
'Current session': '当前会话',
'DESIGN': '设计',
'Date and Time': '时间日期',
'Delete': '删除',
'Delete:': '删除:',
'Deploy on Google App Engine': '部署到GAE',
'Description': '描述',
'Design for': '设计:',
'E-mail': '邮箱:',
'EDIT': '编辑',
'Edit Profile': '修订配置',
'Edit application': '修订应用',
'Edit current record': '修订当前记录',
'Editing Language file': '修订语言文件',
'Editing file': '修订文件',
'Editing file "%s"': '修订文件 %s',
'Enterprise Web Framework': '强悍的网络开发框架',
'Error logs for "%(app)s"': '"%(app)s" 的错误日志',
'Exception instance attributes': 'Exception instance attributes',
'First name': '姓',
'Functions with no doctests will result in [passed] tests.': '',
'Group ID': '组ID',
'Hello World': '道可道，非常道；名可名，非常名',
'If the report above contains a ticket number it indicates a failure in executing the controller, before any attempt to execute the doctests. This is usually due to an indentation error or an error outside function code.\nA green title indicates that all tests (if defined) passed. In this case test results are not shown.': 'If the report above contains a ticket number it indicates a failure in executing the controller, before any attempt to execute the doctests. This is usually due to an indentation error or an error outside function code.\nA green title indicates that all tests (if defined) passed. In this case test results are not shown.',
'Import/Export': '导入/导出',
'Installed applications': '已安装的应用',
'Internal State': '内部状态',
'Invalid Query': '无效查询',
'Invalid action': '无效动作',
'Invalid email': '无效的email',
'Language files (static strings) updated': '语言文件(静态部分)已更新',
'Languages': '语言',
'Last name': '名',
'Last saved on:': '最后保存于:',
'License for': '许可证',
'Login': '登录',
'Login to the Administrative Interface': '登录到管理员界面',
'Logout': '注销',
'Lost Password': '忘记密码',
'Models': '模型s',
'Modules': '模块s',
'NO': '不',
'Name': '姓名',
'New Record': '新记录',
'New application wizard': 'New application wizard',
'New simple application': 'New simple application',
'No databases in this application': '这应用没有数据库',
'Origin': '起源',
'Original/Translation': '原始文件/翻译文件',
'PAM authenticated user, cannot change password here': 'PAM authenticated user, cannot change password here',
'Password': '密码',
'Peeking at file': '选个文件',
'Plugin "%s" in application': 'Plugin "%s" in application',
'Plugins': 'Plugins',
'Powered by': '',
'Query:': '查询',
'Record ID': '记录ID',
'Register': '注册',
'Registration key': '注册密匙',
'Resolve Conflict file': '解决冲突文件',
'Role': '角色',
'Rows in table': '表行',
'Rows selected': '行选择',
'Saved file hash:': '已存文件Hash:',
'Static files': '静态文件',
'Sure you want to delete this object?': '真的要删除这个对象?',
'TM': '',
'Table name': '表名',
'Testing application': '应用测试',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': '',
'There are no controllers': '冇控制器',
'There are no models': '冇模型s',
'There are no modules': '冇模块s',
'There are no static files': '冇静态文件',
'There are no translators, only default language is supported': '没有找到相应翻译，只能使用默认语言',
'There are no views': '冇视图',
'This is the %(filename)s template': '这是 %(filename)s 模板',
'Ticket': '传票',
'Timestamp': '时间戳',
'To create a plugin, name a file/folder plugin_[name]': 'To create a plugin, name a file/folder plugin_[name]',
'Unable to check for upgrades': '无法检查是否需要升级',
'Unable to download': '无法下载',
'Unable to download app': '无法下载应用',
'Unable to download app because:': 'Unable to download app because:',
'Unable to download because': 'Unable to download because',
'Update:': '更新:',
'Upload & install packed application': 'Upload & install packed application',
'Upload a package:': 'Upload a package:',
'Upload existing application': '上传已有应用',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': '',
'Use an url:': 'Use an url:',
'User ID': '用户ID',
'Version': '版本',
'Views': '视图',
'Welcome to web2py': '欢迎使用web2py',
'YES': '是',
'about': '关于',
'additional code for your application': '给你的应用附加代码',
'admin disabled because no admin password': '管理员需要设定密码，否则无法管理',
'admin disabled because not supported on google app engine': '未支持GAE,无法管理',
'admin disabled because unable to access password file': '需要可以操作密码文件，否则无法进行管理',
'administrative interface': 'administrative interface',
'and rename it (required):': '重命名为 (必须):',
'and rename it:': ' 重命名为:',
'appadmin': '应用管理',
'appadmin is disabled because insecure channel': '应用管理因非法通道失效',
'application "%s" uninstalled': '应用"%s" 已被卸载',
'application compiled': '应用已编译完',
'application is compiled and cannot be designed': '应用已编译完无法设计',
'arguments': 'arguments',
'back': 'back',
'cache': 'cache',
'cache, errors and sessions cleaned': '缓存、错误、sesiones已被清空',
'cannot create file': '无法创建文件',
'cannot upload file "%(filename)s"': '无法上传文件 "%(filename)s"',
'change admin password': 'change admin password',
'check all': '检查所有',
'check for upgrades': 'check for upgrades',
'clean': '清除',
'click here for online examples': '猛击此处，查看在线实例',
'click here for the administrative interface': '猛击此处，进入管理界面',
'click to check for upgrades': '猛击查看是否有升级版本',
'code': 'code',
'compile': '编译',
'compiled application removed': '已编译应用已移走',
'controllers': '控制器',
'create': 'create',
'create file with filename:': '创建文件用这名:',
'create new application:': '创建新应用:',
'created by': '创建自',
'crontab': '定期事务',
'currently running': 'currently running',
'currently saved or': '保存当前的或',
'customize me!': '定制俺!',
'data uploaded': '数据已上传',
'database': '数据库',
'database %s select': '数据库 %s 选择',
'database administration': '数据库管理',
'db': '',
'defines tables': '已定义表',
'delete': '删除',
'delete all checked': '删除所有选择的',
'delete plugin': 'delete plugin',
'deploy': 'deploy',
'design': '设计',
'direction: ltr': 'direction: ltr',
'done!': '搞定!',
'edit': '修改',
'edit controller': '修订控制器',
'edit views:': 'edit views:',
'errors': '错误',
'export as csv file': '导出为CSV文件',
'exposes': '暴露',
'extends': '扩展',
'failed to reload module': '重新加载模块失败',
'failed to reload module because:': 'failed to reload module because:',
'file "%(filename)s" created': '文件 "%(filename)s" 已创建',
'file "%(filename)s" deleted': '文件 "%(filename)s" 已删除',
'file "%(filename)s" uploaded': '文件 "%(filename)s" 已上传',
'file "%(filename)s" was not deleted': '文件 "%(filename)s" 没删除',
'file "%s" of %s restored': '文件"%s" 有关 %s 已重存',
'file changed on disk': '硬盘上的文件已经修改',
'file does not exist': '文件并不存在',
'file saved on %(time)s': '文件保存于 %(time)s',
'file saved on %s': '文件保存在 %s',
'help': '帮助',
'htmledit': 'html编辑',
'includes': '包含',
'insert new': '新插入',
'insert new %s': '新插入 %s',
'install': 'install',
'internal error': '内部错误',
'invalid password': '无效密码',
'invalid request': '无效请求',
'invalid ticket': '无效传票',
'language file "%(filename)s" created/updated': '语言文件 "%(filename)s"被创建/更新',
'languages': '语言',
'languages updated': '语言已被刷新',
'loading...': '载入中...',
'login': '登录',
'logout': '注销',
'merge': '合并',
'models': '模型s',
'modules': '模块s',
'new application "%s" created': '新应用 "%s"已被创建',
'new plugin installed': 'new plugin installed',
'new record inserted': '新记录被插入',
'next 100 rows': '后100行',
'no match': 'no match',
'or import from csv file': '或者，从csv文件导入',
'or provide app url:': 'or provide app url:',
'or provide application url:': '或者，提供应用所在地址链接:',
'overwrite installed app': 'overwrite installed app',
'pack all': '全部打包',
'pack compiled': '包编译完',
'pack plugin': 'pack plugin',
'password changed': 'password changed',
'plugin "%(plugin)s" deleted': 'plugin "%(plugin)s" deleted',
'previous 100 rows': '前100行',
'record': 'record',
'record does not exist': '记录并不存在',
'record id': '记录ID',
'remove compiled': '已移除',
'restore': '重存',
'revert': '恢复',
'save': '保存',
'selected': '已选',
'session expired': '会话过期',
'shell': '',
'site': '总站',
'some files could not be removed': '有些文件无法被移除',
'start wizard': 'start wizard',
'state': '状态',
'static': '静态文件',
'submit': '提交',
'table': '表',
'test': '测试',
'the application logic, each URL path is mapped in one exposed function in the controller': '应用逻辑:每个URL由控制器暴露的函式完成映射',
'the data representation, define database tables and sets': '数据表达式,定义数据库/表',
'the presentations layer, views are also known as templates': '提交层/视图都在模板中可知',
'these files are served without processing, your images go here': '',
'to  previous version.': 'to  previous version.',
'to  previous version.': '退回前一版本',
'translation strings for the application': '应用的翻译字串',
'try': '尝试',
'try something like': '尝试',
'unable to create application "%s"': '无法创建应用 "%s"',
'unable to delete file "%(filename)s"': '无法删除文件 "%(filename)s"',
'unable to delete file plugin "%(plugin)s"': 'unable to delete file plugin "%(plugin)s"',
'unable to parse csv file': '无法生成 cvs',
'unable to uninstall "%s"': '无法卸载 "%s"',
'unable to upgrade because "%s"': 'unable to upgrade because "%s"',
'uncheck all': '反选全部',
'uninstall': '卸载',
'update': '更新',
'update all languages': '更新所有语言',
'upgrade web2py now': 'upgrade web2py now',
'upload application:': '提交已有的应用:',
'upload file:': '提交文件:',
'upload plugin file:': 'upload plugin file:',
'variables': 'variables',
'versioning': '版本',
'view': '视图',
'views': '视图s',
'web2py Recent Tweets': 'twitter上的web2py进展实播',
'web2py is up to date': 'web2py现在已经是最新的版本了',
'web2py upgraded; please restart it': 'web2py upgraded; please restart it',
}

########NEW FILE########
__FILENAME__ = zh-tw
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"更新" 是選擇性的條件式, 格式就像 "欄位1=\'值\'". 但是 JOIN 的資料不可以使用 update 或是 delete"',
'%Y-%m-%d': '%Y-%m-%d',
'%Y-%m-%d %H:%M:%S': '%Y-%m-%d %H:%M:%S',
'%s rows deleted': '已刪除 %s 筆',
'%s rows updated': '已更新 %s 筆',
'(something like "it-it")': '(格式類似 "zh-tw")',
'A new version of web2py is available': '新版的 web2py 已發行',
'A new version of web2py is available: %s': '新版的 web2py 已發行: %s',
'ATTENTION: Login requires a secure (HTTPS) connection or running on localhost.': '注意: 登入管理帳號需要安全連線(HTTPS)或是在本機連線(localhost).',
'ATTENTION: TESTING IS NOT THREAD SAFE SO DO NOT PERFORM MULTIPLE TESTS CONCURRENTLY.': '注意: 因為在測試模式不保證多執行緒安全性，也就是說不可以同時執行多個測試案例',
'ATTENTION: you cannot edit the running application!': '注意:不可編輯正在執行的應用程式!',
'About': '關於',
'About application': '關於本應用程式',
'Admin is disabled because insecure channel': '管理功能(Admin)在不安全連線環境下自動關閉',
'Admin is disabled because unsecure channel': '管理功能(Admin)在不安全連線環境下自動關閉',
'Administrator Password:': '管理員密碼:',
'Are you sure you want to delete file "%s"?': '確定要刪除檔案"%s"?',
'Are you sure you want to delete plugin "%s"?': '確定要刪除插件 "%s"?',
'Are you sure you want to uninstall application "%s"': '確定要移除應用程式 "%s"',
'Are you sure you want to uninstall application "%s"?': '確定要移除應用程式 "%s"',
'Are you sure you want to upgrade web2py now?': '確定現在要升級 web2py?',
'Authentication': '驗證',
'Available databases and tables': '可提供的資料庫和資料表',
'Cannot be empty': '不可空白',
'Cannot compile: there are errors in your app.        Debug it, correct errors and try again.': '無法編譯:應用程式中含有錯誤，請除錯後再試一次.',
'Cannot compile: there are errors in your app:': '無法編譯: 在你的應用程式存在錯誤:',
'Change Password': '變更密碼',
'Check to delete': '打勾代表刪除',
'Check to delete:': '打勾代表刪除:',
'Checking for upgrades...': '檢查新版本中...',
'Client IP': '客戶端網址(IP)',
'Controller': '控件',
'Controllers': '控件',
'Copyright': '版權所有',
'Create new simple application': '創建應用程式',
'Current request': '目前網路資料要求(request)',
'Current response': '目前網路資料回應(response)',
'Current session': '目前網路連線資訊(session)',
'DB Model': '資料庫模組',
'DESIGN': '設計',
'Database': '資料庫',
'Date and Time': '日期和時間',
'Delete': '刪除',
'Delete:': '刪除:',
'Deploy on Google App Engine': '配置到 Google App Engine',
'Description': '描述',
'Design for': '設計為了',
'E-mail': '電子郵件',
'EDIT': '編輯',
'Edit': '編輯',
'Edit Profile': '編輯設定檔',
'Edit This App': '編輯本應用程式',
'Edit application': '編輯應用程式',
'Edit current record': '編輯當前紀錄',
'Editing Language file': '編輯語言檔案',
'Editing file': '編輯檔案',
'Editing file "%s"': '編輯檔案"%s"',
'Enterprise Web Framework': '企業網站平台',
'Error logs for "%(app)s"': '"%(app)s"的錯誤紀錄',
'Exception instance attributes': 'Exception instance attributes',
'First name': '名',
'Functions with no doctests will result in [passed] tests.': '沒有 doctests 的函式會顯示 [passed].',
'Group ID': '群組編號',
'Hello World': '嗨! 世界',
'If the report above contains a ticket number it indicates a failure in executing the controller, before any attempt to execute the doctests. This is usually due to an indentation error or an error outside function code.\nA green title indicates that all tests (if defined) passed. In this case test results are not shown.': 'If the report above contains a ticket number it indicates a failure in executing the controller, before any attempt to execute the doctests. This is usually due to an indentation error or an error outside function code.\nA green title indicates that all tests (if defined) passed. In this case test results are not shown.',
'Import/Export': '匯入/匯出',
'Index': '索引',
'Installed applications': '已安裝應用程式',
'Internal State': '內部狀態',
'Invalid Query': '不合法的查詢',
'Invalid action': '不合法的動作(action)',
'Invalid email': '不合法的電子郵件',
'Language files (static strings) updated': '語言檔已更新',
'Languages': '各國語言',
'Last name': '姓',
'Last saved on:': '最後儲存時間:',
'Layout': '網頁配置',
'License for': '許可證',
'Login': '登入',
'Login to the Administrative Interface': '登入到管理員介面',
'Logout': '登出',
'Lost Password': '密碼遺忘',
'Main Menu': '主選單',
'Menu Model': '選單模組(menu)',
'Models': '資料模組',
'Modules': '程式模組',
'NO': '否',
'Name': '名字',
'New Record': '新紀錄',
'No databases in this application': '這應用程式不含資料庫',
'Origin': '原文',
'Original/Translation': '原文/翻譯',
'PAM authenticated user, cannot change password here': 'PAM 授權使用者, 無法在此變更密碼',
'Password': '密碼',
"Password fields don't match": '密碼欄不匹配',
'Peeking at file': '選個文件',
'Plugin "%s" in application': '在應用程式的插件 "%s"',
'Plugins': '插件',
'Powered by': '基於以下技術構建：',
'Query:': '查詢:',
'Record ID': '紀錄編號',
'Register': '註冊',
'Registration key': '註冊金鑰',
'Remember me (for 30 days)': '記住帳號(30 天)',
'Reset Password key': '重設密碼',
'Resolve Conflict file': '解決衝突檔案',
'Role': '角色',
'Rows in table': '在資料表裏的資料',
'Rows selected': '筆資料被選擇',
'Saved file hash:': '檔案雜湊值已紀錄:',
'Static files': '靜態檔案',
'Stylesheet': '網頁風格檔',
'Submit': '傳送',
'Sure you want to delete this object?': '確定要刪除此物件?',
'TM': 'TM',
'Table name': '資料表名稱',
'Testing application': '測試中的應用程式',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': '"查詢"是一個像 "db.表1.欄位1==\'值\'" 的條件式. 以"db.表1.欄位1==db.表2.欄位2"方式則相當於執行 JOIN SQL.',
'There are no controllers': '沒有控件(controllers)',
'There are no models': '沒有資料庫模組(models)',
'There are no modules': '沒有程式模組(modules)',
'There are no static files': '沒有靜態檔案',
'There are no translators, only default language is supported': '沒有翻譯檔,只支援原始語言',
'There are no views': '沒有視圖',
'This is the %(filename)s template': '這是%(filename)s檔案的樣板(template)',
'Ticket': '問題單',
'Timestamp': '時間標記',
'To create a plugin, name a file/folder plugin_[name]': '檔案或目錄名稱以 plugin_開頭來創建插件',
'Unable to check for upgrades': '無法做升級檢查',
'Unable to download': '無法下載',
'Unable to download app': '無法下載應用程式',
'Unable to download app because:': '無法下載應用程式因為:',
'Unable to download because': '因為下列原因無法下載:',
'Update:': '更新:',
'Upload & install packed application': '上傳並安裝已打包的應用程式',
'Upload existing application': '更新存在的應用程式',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': '使用下列方式來組合更複雜的條件式, (...)&(...) 代表同時存在的條件, (...)|(...) 代表擇一的條件, ~(...)則代表反向條件.',
'User %(id)s Logged-in': '使用者 %(id)s 已登入',
'User %(id)s Registered': '使用者 %(id)s 已註冊',
'User ID': '使用者編號',
'Verify Password': '驗證密碼',
'Version': '版本',
'View': '視圖',
'Views': '視圖',
'Welcome %s': '歡迎 %s',
'Welcome to web2py': '歡迎使用 web2py',
'YES': '是',
'about': '關於',
'additional code for your application': '應用程式額外的程式碼',
'admin disabled because no admin password': '管理介面關閉原因是沒有設定管理員密碼 ',
'admin disabled because not supported on google app engine': '管理介面關閉原因是不支援在google apps engine環境下運作',
'admin disabled because unable to access password file': '管理介面關閉原因是無法存取密碼檔',
'amy_ajax': 'amy_ajax',
'and rename it (required):': '同時更名為(必要的):',
'and rename it:': '同時更名為:',
'appadmin': '應用程式管理員',
'appadmin is disabled because insecure channel': '管理介面關閉理由是連線方式不安全',
'application "%s" uninstalled': '已移除應用程式 "%s"',
'application compiled': '已編譯應用程式',
'application is compiled and cannot be designed': '應用程式已經編譯無法重新設計',
'arguments': 'arguments',
'back': '回復(back)',
'cache': '快取記憶體',
'cache, errors and sessions cleaned': '快取記憶體,錯誤紀錄,連線紀錄已清除',
'cannot create file': '無法創建檔案',
'cannot upload file "%(filename)s"': '無法上傳檔案 "%(filename)s"',
'change admin password': 'change admin password',
'change_password': '變更密碼',
'check all': '全選',
'clean': '清除',
'click here for online examples': '點此處進入線上範例',
'click here for the administrative interface': '點此處進入管理介面',
'click to check for upgrades': '點擊打勾以便升級',
'code': 'code',
'compile': '編譯',
'compiled application removed': '已移除已編譯的應用程式',
'controllers': '控件',
'create': '創建',
'create file with filename:': '創建檔案:',
'create new application:': '創建新應用程式:',
'created by': '創建自',
'crontab': '定時執行表',
'currently saved or': '現在存檔或',
'customize me!': '請調整我!',
'data uploaded': '資料已上傳',
'database': '資料庫',
'database %s select': '已選擇 %s 資料庫',
'database administration': '資料庫管理',
'db': 'db',
'defines tables': '定義資料表',
'delete': '刪除',
'delete all checked': '刪除所有已選擇項目',
'delete plugin': '刪除插件',
'delete_plugin': '刪除插件',
'design': '設計',
'direction: ltr': 'direction: ltr',
'done!': '完成!',
'edit': '編輯',
'edit controller': '編輯控件',
'edit views:': '編輯視圖',
'edit_language': '編輯語言檔',
'errors': '錯誤紀錄',
'export as csv file': '以逗號分隔檔(csv)格式匯出',
'exposes': '外顯',
'extends': '擴展',
'failed to reload module because:': '因為下列原因無法重新載入程式模組:',
'file "%(filename)s" created': '檔案 "%(filename)s" 已創建',
'file "%(filename)s" deleted': '檔案 "%(filename)s" 已刪除',
'file "%(filename)s" uploaded': '檔案 "%(filename)s" 已上傳',
'file "%s" of %s restored': '檔案 %s 的 "%s" 已回存',
'file changed on disk': '在磁碟上檔案已改變',
'file does not exist': '檔案不存在',
'file saved on %(time)s': '檔案已於 %(time)s 儲存',
'file saved on %s': '檔案在 %s 已儲存',
'help': '說明檔',
'htmledit': 'html編輯',
'includes': '包含',
'index': '索引',
'insert new': '插入新資料',
'insert new %s': '插入新資料 %s',
'install': '安裝',
'internal error': '內部錯誤',
'invalid password': '密碼錯誤',
'invalid request': '不合法的網路要求(request)',
'invalid ticket': '不合法的問題單號',
'language file "%(filename)s" created/updated': '語言檔"%(filename)s"已創建或更新',
'languages': '語言檔',
'loading...': '載入中...',
'login': '登入',
'logout': '登出',
'merge': '合併',
'models': '資料庫模組',
'modules': '程式模組',
'new application "%s" created': '已創建新的應用程式 "%s"',
'new plugin installed': '已安裝新插件',
'new record inserted': '已新增新紀錄',
'next 100 rows': '往後 100 筆',
'no match': '無法匹配',
'or import from csv file': '或是從逗號分隔檔(CSV)匯入',
'or provide app url:': '或是提供應用程式的安裝網址:',
'overwrite installed app': '覆蓋已安裝的應用程式',
'pack all': '全部打包',
'pack compiled': '打包已編譯資料',
'pack plugin': '打包插件',
'password changed': '密碼已變更',
'peek': '選取',
'plugin': '插件',
'plugin "%(plugin)s" deleted': '已刪除插件"%(plugin)s"',
'previous 100 rows': '往前 100 筆',
'record': '紀錄',
'record does not exist': '紀錄不存在',
'record id': '紀錄編號',
'register': '註冊',
'remove compiled': '編譯檔案已移除',
'resolve': '解決',
'restore': '回存',
'revert': '反向恢復',
'save': '儲存',
'selected': '已選擇',
'session expired': '連線(session)已過時',
'shell': '命令列操作介面',
'site': '網站',
'some files could not be removed': '部份檔案無法移除',
'state': '狀態',
'static': '靜態檔案',
'submit': '傳送',
'table': '資料表',
'test': '測試',
'the application logic, each URL path is mapped in one exposed function in the controller': '應用程式邏輯 - 每個網址路徑對應到一個控件的函式',
'the data representation, define database tables and sets': '資料展現層 - 用來定義資料表和集合',
'the presentations layer, views are also known as templates': '外觀展現層 - 視圖有時也被稱為樣板',
'these files are served without processing, your images go here': '這些檔案保留未經處理,你的影像檔在此',
'ticket': '問題單',
'to  previous version.': '到前一個版本',
'translation strings for the application': '翻譯此應用程式的字串',
'try': '嘗試',
'try something like': '嘗試如',
'unable to create application "%s"': '無法創建應用程式 "%s"',
'unable to delete file "%(filename)s"': '無法刪除檔案 "%(filename)s"',
'unable to delete file plugin "%(plugin)s"': '無法刪查插件檔 "%(plugin)s"',
'unable to parse csv file': '無法解析逗號分隔檔(csv)',
'unable to uninstall "%s"': '無法移除安裝 "%s"',
'unable to upgrade because "%s"': '無法升級因為 "%s"',
'uncheck all': '全不選',
'uninstall': '解除安裝',
'update': '更新',
'update all languages': '將程式中待翻譯語句更新到所有的語言檔',
'upgrade web2py now': 'upgrade web2py now',
'upgrade_web2py': '升級 web2py',
'upload application:': '上傳應用程式:',
'upload file:': '上傳檔案:',
'upload plugin file:': '上傳插件檔:',
'variables': 'variables',
'versioning': '版本管理',
'view': '視圖',
'views': '視圖',
'web2py Recent Tweets': 'web2py 最近的 Tweets',
'web2py is up to date': 'web2py 已經是最新版',
'web2py upgraded; please restart it': '已升級 web2py ; 請重新啟動',
}

########NEW FILE########
__FILENAME__ = 0
EXPIRATION = 60 * 60  # logout after 60 minutes of inactivity
CHECK_VERSION = True
WEB2PY_URL = 'http://web2py.com'
WEB2PY_VERSION_URL = WEB2PY_URL+'/examples/default/version'

###########################################################################
# Preferences for EditArea
# the user-interface feature that allows you to edit files in your web
# browser.

## Default editor
TEXT_EDITOR = 'edit_area' or 'amy'

### edit_area
# The default font size, measured in 'points'. The value must be an integer > 0
FONT_SIZE = 10

# Displays the editor in full screen mode. The value must be 'true' or 'false'
FULL_SCREEN = 'false'

# Display a check box under the editor to allow the user to switch
# between the editor and a simple
# HTML text area. The value must be 'true' or 'false'
ALLOW_TOGGLE = 'true'

# Replaces tab characters with space characters.
# The value can be 'false' (meaning that tabs are not replaced),
# or an integer > 0 that specifies the number of spaces to replace a tab with.
REPLACE_TAB_BY_SPACES = 4

# Toggle on/off the code editor instead of textarea on startup
DISPLAY = "onload" or "later"

# if demo mode is True then admin works readonly and does not require login
DEMO_MODE = False

# if visible_apps is not empty only listed apps will be accessible
FILTER_APPS = []

# To upload on google app engine this has to point to the proper appengine
# config file
import os
# extract google_appengine_x.x.x.zip to web2py root directory
#GAE_APPCFG = os.path.abspath(os.path.join('appcfg.py'))
# extract google_appengine_x.x.x.zip to applications/admin/private/
GAE_APPCFG = os.path.abspath(os.path.join('/usr/local/bin/appcfg.py'))

# To use web2py as a teaching tool, set MULTI_USER_MODE to True
MULTI_USER_MODE = False

# configurable twitterbox, set to None/False to suppress
TWITTER_HASH = "web2py"

# parameter for downloading LAYOUTS
LAYOUTS_APP = 'http://web2py.com/layouts'
#LAYOUTS_APP = 'http://127.0.0.1:8000/layouts'


# parameter for downloading PLUGINS
PLUGINS_APP = 'http://web2py.com/plugins'
#PLUGINS_APP = 'http://127.0.0.1:8000/plugins'

# set the language
if 'adminLanguage' in request.cookies and not (request.cookies['adminLanguage'] is None):
    T.force(request.cookies['adminLanguage'].value)

########NEW FILE########
__FILENAME__ = 0_imports
import time
import os
import sys
import re
import urllib
import cgi
import difflib
import shutil
import stat
import socket

from textwrap import dedent

try:
    from mercurial import ui, hg, cmdutil
    have_mercurial = True
except ImportError:
    have_mercurial = False

from gluon.utils import md5_hash
from gluon.fileutils import listdir, cleanpath, up
from gluon.fileutils import tar, tar_compiled, untar, fix_newlines
from gluon.languages import findT, update_all_languages
from gluon.myregex import *
from gluon.restricted import *
from gluon.compileapp import compile_application, remove_compiled_application

########NEW FILE########
__FILENAME__ = access
import os, time
from gluon import portalocker
from gluon.admin import apath
from gluon.fileutils import read_file
# ###########################################################
# ## make sure administrator is on localhost or https
# ###########################################################

http_host = request.env.http_host.split(':')[0]

if request.env.web2py_runtime_gae:
    session_db = DAL('gae')
    session.connect(request, response, db=session_db)
    hosts = (http_host, )

if request.env.http_x_forwarded_for or request.is_https:
    session.secure()
elif not request.is_local and not DEMO_MODE:
    raise HTTP(200, T('Admin is disabled because insecure channel'))

try:
    _config = {}
    port = int(request.env.server_port or 0)
    restricted(read_file(apath('../parameters_%i.py' % port, request)), _config)

    if not 'password' in _config or not _config['password']:
        raise HTTP(200, T('admin disabled because no admin password'))
except IOError:
    import gluon.fileutils
    if request.env.web2py_runtime_gae:
        if gluon.fileutils.check_credentials(request):
            session.authorized = True
            session.last_time = time.time()
        else:
            raise HTTP(200,
                       T('admin disabled because not supported on google app engine'))
    else:
        raise HTTP(200, T('admin disabled because unable to access password file'))


def verify_password(password):
    session.pam_user = None
    if DEMO_MODE:
        return True
    elif not 'password' in _config:
        return False
    elif _config['password'].startswith('pam_user:'):
        session.pam_user = _config['password'][9:].strip()
        import gluon.contrib.pam
        return gluon.contrib.pam.authenticate(session.pam_user,password)
    else:
        return _config['password'] == CRYPT()(password)[0]


# ###########################################################
# ## handle brute-force login attacks
# ###########################################################

deny_file = os.path.join(request.folder, 'private', 'hosts.deny')
allowed_number_of_attempts = 5
expiration_failed_logins = 3600

def read_hosts_deny():
    import datetime
    hosts = {}
    if os.path.exists(deny_file):
        hosts = {}
        f = open(deny_file, 'r')
        portalocker.lock(f, portalocker.LOCK_SH)
        for line in f.readlines():
            if not line.strip() or line.startswith('#'):
                continue
            fields = line.strip().split()
            if len(fields) > 2:
                hosts[fields[0].strip()] = ( # ip
                    int(fields[1].strip()),  # n attemps
                    int(fields[2].strip())   # last attempts
                    )
        portalocker.unlock(f)
        f.close()  
    return hosts
        
def write_hosts_deny(denied_hosts):
    f = open(deny_file, 'w')
    portalocker.lock(f, portalocker.LOCK_EX)
    for key, val in denied_hosts.items():
        if time.time()-val[1] < expiration_failed_logins:
            line = '%s %s %s\n' % (key, val[0], val[1])
            f.write(line)
    portalocker.unlock(f)
    f.close()        

def login_record(success=True):
    denied_hosts = read_hosts_deny()
    val = (0,0)
    if success and request.client in denied_hosts:
        del denied_hosts[request.client]
    elif not success and not request.is_local:
        val = denied_hosts.get(request.client,(0,0))
        if time.time()-val[1]<expiration_failed_logins \
            and val[0] >= allowed_number_of_attempts:
            return val[0] # locked out
        time.sleep(2**val[0])
        val = (val[0]+1,int(time.time()))        
        denied_hosts[request.client] = val
    write_hosts_deny(denied_hosts)
    return val[0]
        

# ###########################################################
# ## session expiration
# ###########################################################

t0 = time.time()
if session.authorized:

    if session.last_time and session.last_time < t0 - EXPIRATION:
        session.flash = T('session expired')
        session.authorized = False
    else:
        session.last_time = t0

if not session.authorized and not \
    (request.controller == 'default' and \
     request.function in ('index','user')):

    if request.env.query_string:
        query_string = '?' + request.env.query_string
    else:
        query_string = ''

    if request.env.web2py_original_uri:
        url = request.env.web2py_original_uri
    else:
        url = request.env.path_info + query_string
    redirect(URL(request.application, 'default', 'index', vars=dict(send=url)))
elif session.authorized and \
     request.controller == 'default' and \
     request.function == 'index':
    redirect(URL(request.application, 'default', 'site'))


if request.controller=='appadmin' and DEMO_MODE:
    session.flash = 'Appadmin disabled in demo mode'
    redirect(URL('default','sites'))


########NEW FILE########
__FILENAME__ = buttons
# Template helpers

import os

def button(href, label):
  return A(SPAN(label),_class='button',_href=href)

def sp_button(href, label):
  return A(SPAN(label),_class='button special',_href=href)

def helpicon():
  return IMG(_src=URL('static', 'images/help.png'), _alt='help')

def searchbox(elementid):
  return TAG[''](LABEL(IMG(_src=URL('static', 'images/search.png'), _alt=T('filter')), _class='icon', _for=elementid), ' ', INPUT(_id=elementid, _type='text', _size=12))

########NEW FILE########
__FILENAME__ = db
# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

if MULTI_USER_MODE:
    db = DAL('sqlite://storage.sqlite')       # if not, use SQLite or other DB
    from gluon.tools import *
    mail = Mail()                                  # mailer
    auth = Auth(globals(),db)                      # authentication/authorization
    crud = Crud(globals(),db)                      # for CRUD helpers using auth
    service = Service(globals())                   # for json, xml, jsonrpc, xmlrpc, amfrpc
    plugins = PluginManager()

    settings.mail.settings.server = 'logging' or 'smtp.gmail.com:587'  # your SMTP server
    settings.mail.settings.sender = 'you@gmail.com'         # your email
    settings.mail.settings.login = 'username:password'      # your credentials or None

    settings.auth.hmac_key = '<your secret key>'   # before define_tables()
    settings.auth.define_tables()                           # creates all needed tables
    settings.auth.mailer = mail                    # for user email verification
    settings.auth.registration_requires_verification = False
    settings.auth.registration_requires_approval = True
    settings.auth.messages.verify_email = 'Click on the link http://'+request.env.http_host+URL('default','user',args=['verify_email'])+'/%(key)s to verify your email'
    settings.auth.reset_password_requires_verification = True
    auth.messages.reset_password = 'Click on the link http://'+request.env.http_host+URL('default','user',args=['reset_password'])+'/%(key)s to reset your password'

    db.define_table('app',Field('name'),Field('owner',db.auth_user))

if not session.authorized and MULTI_USER_MODE:
    if auth.user and not request.function=='user':
        session.authorized = True
    elif not request.function=='user':
        redirect(URL('default','user/login'))

def is_manager():
    if not MULTI_USER_MODE:
        return True
    elif auth.user and auth.user.id==1:
        return True
    else:
        return False

########NEW FILE########
__FILENAME__ = menu
# ###########################################################
# ## generate menu
# ###########################################################

_a = request.application
_c = request.controller
_f = request.function
response.title = '%s %s' % (_f, '/'.join(request.args))
response.subtitle = 'admin'
response.menu = [(T('site'), _f == 'site', URL(_a,'default','site'))]

if request.args:
    _t = request.args[0]
    response.menu.append((T('edit'), _c == 'default' and _f == 'design',
                         URL(_a,'default','design',args=_t)))
    response.menu.append((T('about'), _c == 'default' and _f == 'about',
                         URL(_a,'default','about',args=_t)))
    response.menu.append((T('errors'), _c == 'default' and _f == 'errors',
                         URL(_a,'default','errors',args=_t)))

    response.menu.append((T('versioning'),
                          _c == 'mercurial' and _f == 'commit',
                          URL(_a,'mercurial','commit',args=_t)))

if not session.authorized:
    response.menu = [(T('login'), True, '')]
else:
    response.menu.append((T('logout'), False,
                          URL(_a,'default',f='logout')))

response.menu.append((T('help'), False, URL('examples','default','index')))


########NEW FILE########
__FILENAME__ = plugin_multiselect
response.files.append(URL('static','plugin_multiselect/jquery.dimensions.js'))
response.files.append(URL('static','plugin_multiselect/jquery.multiselect.js'))
response.files.append(URL('static','plugin_multiselect/jquery.multiselect.css'))
response.files.append(URL('static','plugin_multiselect/start.js'))

########NEW FILE########
__FILENAME__ = admin
# coding: utf8
"""
Controller module for the admin interface.
Contains every controller that must run with admin privileges.

Every controller in this file must have the @auth.requires_login() decorator
"""
from shutil import copyfile
import hashlib
from config import projroot, cfgfile, copyform

session.admin = True

@auth.requires_login()
def index():
    """
    Controller for admin index page
    """
    session.admin = True
    return dict(message="hello from admin.py")

@auth.requires_login()
def targets():
    """
    Controller for page that lets the admin to create new targets
    """
    # first operation is get the target list, because every dict() returned 
    # will need it
    targets_list = gl.get_targets(None)

    crud.settings.detect_record_change = False
    if (request.vars.edit and request.vars.edit.startswith("delete")):
        gl.delete_target(request.vars.edit.split(".")[1])
        # update the list
        targets_list = gl.get_targets(None)
    
    # it's possible delete via ajax and add via POST
    if (request.vars.edit and request.vars.edit.startswith("edit")):

        update_form = crud.update(db.target, request.vars.edit.split(".")[1])

        return dict(targets=targets_list, default_group=settings['globals'].default_group, 
                    form=update_form, edit=True)

    # is hardcoded email, supposing that, at the moment, every subscription
    # happen with email only. in the future, other kind of contacts can be
    # setup from the start.
    form_content = (Field('Name', requires=IS_NOT_EMPTY()),
                    Field('Description',
                          requires=IS_LENGTH(minsize=5, maxsize=50)),
                    Field('contact', requires=[IS_EMAIL(),
                          IS_NOT_IN_DB(db, db.target.contact)]),
                    Field('can_delete', 'boolean'), #extern the text in view
                   )

    add_form = SQLFORM.factory(*form_content)

    # provide display only, when controller is called as targets/display
    if "display" in request.args and not request.vars:
        return dict(form=None, list_only=True, targets=targets_list,
                    default_group=settings['globals'].default_group, edit=None)
    # default: you don't call display, and the list is show anyway.

    if add_form.accepts(request.vars, session):
        req = request.vars

        # here some mistake happen, I wish that now has been fixed and not augmented

        target_id = gl.create_target(req.Name, None, req.Description,
                                     req.contact, req.can_delete)

        target = db.auth_user.insert(first_name=req.Name,
                                     last_name="",
                                     username=target_id,
                                     email=req.contact)
        auth.add_membership(auth.id_group("targets"), target)

        targets_list = gl.get_targets("ANY")

    # switch list_only=None if, in the adding interface, the list has not to be showed
    return dict(form=add_form, list_only=None, targets=targets_list,
                default_group=settings['globals'].default_group, edit=None)

@configuration_required
@auth.requires_login()
def statistics():
    collected_user = []
    target_list = db().select(db.target.ALL)
    for active_user in target_list:
        collected_user.append(active_user)

    leak_active = []
    flowers = db().select(db.leak.ALL)
    for leak in flowers:
        leak_active.append(leak)

    groups_usage = []
    group_list = db().select(db.targetgroup.ALL)
    for group in group_list:
        groups_usage.append(group)

    # this require to be splitted because tulip are leak x target matrix
    tulip_avail = []
    tulip_list = db().select(db.tulip.ALL)
    for single_t in tulip_list:
        tulip_avail.append(single_t)

    return dict(active=collected_user,
                flowers=leak_active,
                groups=groups_usage,
                tulips=tulip_avail)
    # nevah forget http://uiu.me/Nr9G.png


@auth.requires_login()
def target_add():
    """
    Receives parameters "target" and "group" from POST.
    Adds taget to group.
    """
    try:
        target_id = request.post_vars["target"]
        group_id = request.post_vars["group"]
    except KeyError:
        pass

    result = gl.add_to_targetgroup(target_id, group_id)

    if result:
        return response.json({'success': 'true'})

    return response.json({'success': 'false'})


@auth.requires_login()
def target_remove():
    """
    Receives parameters "target" and "group" from POST.
    Removes taget from group.
    """
    try:
        target_id = request.post_vars["target"]
        group_id = request.post_vars["group"]
    except KeyError:
        pass
    else:
        result = gl.remove_from_targetgroup(target_id, group_id)
        if result:
            return response.json({'success': 'true'})
    return response.json({'success': 'false'})

@auth.requires_login()
def target_delete():
    try:
        target_id = request.post_vars["target"]
    except KeyError:
        pass
    else:
        gl.delete_tulips_by_target(target_id)
        # delete_target remove simply the target
        result = gl.delete_target(target_id)
        if result:
            return response.json({'success': 'true'})
    return response.json({'success': 'false'})

########NEW FILE########
__FILENAME__ = default
#coding: utf-8
"""
Controller for the index
"""
from __future__ import with_statement
import logging
import os

session.admin = False
session.taget = False

def user():
    """
    Controller for user login
    """
    tulip = None
    form = auth()
    if '_next' in request.vars:
        next = request.vars['_next']
        # XXX: what the hell is this shit?
        if not isinstance(next, str):
            next = next[0]
        else:
            path = next.split(os.sep)
            if len(path) > 2:
                # print "path > 3"
                if len(path) > 0 and path[2] == "tulip":
                    # print path[4]
                    try:
                        tulip = Tulip(url=path[4]).target
                    except:
                        pass
                if not tulip:
                    tulip = "admin"
                for c in form.elements('input'):
                    if c['_name'] == "username":
                        c['_value'] = tulip
                return dict(form=form)
    try:
        for c in form.elements('input'):
            if c['_name'] == "username":
                c['_value'] = "admin"
    except:
        pass
    return dict(form=form)


def download():
    return response.download(request, db)


def call():
    session.forget()
    return service()
### end requires

@configuration_required
def index():
    """
    Controller for GlobaLeaks index page
    """
    import hashlib

    tulip_url = None

    if request.vars:
        req = request.vars
        if req.Receipt:
            leak_number = req.Receipt.replace(' ', '')
            tulip_url = hashlib.sha256(leak_number).hexdigest()
            redurl = "/globaleaks/tulip/status/" + tulip_url
            redirect(redurl)

    with open(settings.globals.presentation_file) as filestream:
        presentation_html = filestream.read()

    return dict(tulip_url=None, presentation_html=presentation_html)

def notfound():
    logging.debug('404 Error detected')
    return dict()

def oops():
    logging.error('Error %s : %%(ticket)s.' % request.url)
    return dict()

def error():
    return {}

def email_template():
    return {}

def disclaimer():
    with open(settings.globals.disclaimer_long_file) as filestream:
        content = filestream.read()

    return dict(content=content)


########NEW FILE########
__FILENAME__ = installation
"""
This controller is called only during the Node setup
"""

@auth.requires(auth.requires_login() or not configuration_required)
def password_setup():
    import os
    """
    This controller is the second mandatory step inside the procedure setup, is called after the
    requested reboot, and here the hidden service name can be accessess and shown to the admin.
    Here the admin can setup various information, saved in the config file (useful to avoid terminal
    editing)
    """

    # mandatory: admin login/password and node name
    mandatory_input = (Field('administrative_password', 'password', requires = IS_LENGTH(minsize=8) ),
        Field('confirm_password', 'password',
        requires=IS_EQUAL_TO(request.vars.administrative_password, error_message="passwords do not match")),
	)

    mandatory_form = SQLFORM.factory(*mandatory_input, table_name="mandatory")

    # handle the first connection
    if not mandatory_form.accepts(request.vars, session, keepvalues=True):
		return dict(configured=False, mandatory=mandatory_form)

    # handle the admin setup
    db.auth_user.insert(
        first_name="GlobaLeaks",
        last_name="node administrator",
        username=settings.globals.node_admin_username, # default: 'admin'
        password=db.auth_user.password.validate(request.vars.administrative_password)[0]
    )

    logger.info("recorded node administrator password (login: %s)" % settings['globals'].node_admin_username)
    db.commit()

    # this is a MANDATORY STEP, therefore HERE is added the default group
    if settings.globals.default_group:
        gl.create_targetgroup(settings.globals.default_group, "Default receiver group", None)

    settings.globals.under_installation = False;
    settings.globals.commit()

    return dict(configured=True, mandatory=mandatory_form)

########NEW FILE########
__FILENAME__ = plugin_translate
def translate():
    return "jQuery(document).ready(function(){jQuery('body').translate('%s');});" % request.args(0).split('.')[0]


########NEW FILE########
__FILENAME__ = preload
import os, gzip
import gluon.contenttype

def js():
    files = ['/js/jquery-1.7.2.min.js',
             '/js/modernizr-1.7.min.js',
             #'/js/superfish.js',
             #'/js/cufon.js',
             #'/js/AlteHaas_700.font.js',
             #'/js/web2py_ajax.js',
             #'/js/calendar.js',
             #'/js/main.js',
             '/js/fancybox/jquery.fancybox-1.3.4.pack.js',
             '/js/fileupload/jquery-ui.min.js',
             #'/js/jquery.inlineedit.js',
             #'/FormShaman/js/jquery.smartWizard.js',
             '/js/fileupload/jquery.iframe-transport.js',
             '/js/fileupload/jquery.fileupload.js',
             '/js/fileupload/jquery.fileupload-ui.js',
             '/js/fileupload/jquery.tmpl.min.js',
             '/js/jquery.cookie.js',
             '/js/jquery.qtip-1.0.0-rc3.min.js',
             '/js/bootstrap/bootstrap-tab.js'
             ]

    output_file = os.path.join(request.folder, 'static') + "/main_js_file.js"
    compressed_file = os.path.join(request.folder, 'static') + "/main_js_file.js.gz"

    response.headers['Content-Encoding'] = 'gzip'
    response.headers['Content-Type'] = gluon.contenttype.contenttype('.js')
    response.headers['Cache-Control'] =  "max-age=86400, private"
    response.headers['Pragma'] = "cache"

    if os.path.exists(output_file):
        return response.stream(open(compressed_file, 'rb'))

    fh = open(output_file, 'wb')
    fhg = gzip.open(compressed_file, 'wb')

    to_minify = ""

    for file in files:
        path = os.path.join(request.folder, 'static') + str(file)
        for line in open(path).readlines():
            fh.write(line)
            fhg.write(line)
            #to_minify += line

    #fh.write(minify(to_minify, mangle=False))
    fhg.close()
    fh.close()

    return response.stream(open(compressed_file, 'rb'))
        #for line in open(path).readlines():
        #    output += line
    #response.stream(output)

def css():
    files = ['/css/bootstrap.min.css',
             '/css/globaleaks.css',
             #'/css/style.css',
             '/css/bootstrap-responsive.min.css',
             #'/css/base.css',
             #'/css/superfish.css',
             #'/js/fancybox/jquery.fancybox-1.3.4.css',
             #'/css/calendar.css',
             #'/css/jq-fileupload.css',
             #'/FormShaman/css/smart_wizard.css',
             '/css/jquery.fileupload-ui.css',
             '/css/jquery-ui.css'
             ]

    output_file = os.path.join(request.folder, 'static') + "/main_css_file.css"
    compressed_file = os.path.join(request.folder, 'static') + "/main_css_file.css.gz"

    #response.headers['Content-Encoding'] = 'gzip'
    response.headers['Content-Type'] = gluon.contenttype.contenttype('.css')
    response.headers['Cache-Control'] =  "max-age=86400, private"
    response.headers['Pragma'] = "cache"

    #time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())

    if os.path.exists(output_file):
        return response.stream(open(output_file, 'rb'))

    fh = open(output_file, 'wb')
    #fhg = gzip.open(compressed_file, 'wb')

    for file in files:
        path = os.path.join(request.folder, 'static') + str(file)
        for line in open(path).readlines():
            fh.write(line)
            #fhb.write(line)

    #fhg.close()
    fh.close()

    return response.stream(open(output_file, 'rb'))

def img():
    file_path = request.args

    if ".." not in file_path:
        image_file = os.path.join(request.folder, 'static', '/'.join(file_path))
    else:
        image_file = os.path.join(request.folder, 'static', '/images/error.png')

    ftype = image_file.split(".")[-1:][0]
    #response.headers['Content-Encoding'] = 'gzip'
    response.headers['Content-Type'] = gluon.contenttype.contenttype(ftype)
    response.headers['Cache-Control'] =  "max-age=86400, private"
    response.headers['Pragma'] = "cache"

    return response.stream(open(image_file, 'rb'))

########NEW FILE########
__FILENAME__ = submission
#coding: utf-8
"""
This controller module contains every controller for leak submission.
"""

import os
import random
import time
from gluon.tools import Service
import gluon.contrib.simplejson as json
import shutil
import base64

T.force("EN")
#FormWizard = local_import('plugin_PowerFormWizard')

mutils = local_import('material').utils()
Anonymity = local_import('anonymity')
jQueryHelper = local_import('jquery_helper')
FileHelper = local_import('file_helper')

FileUpload = UploadHandler()

# XXX
# This should be made into one web service
# Integrate the methods suggested in the REST interface specification
@configuration_required
@request.restful()
def fileupload():
    response.view = 'generic.json'
    if not session.files:
        session.files = []

    def GET(file=None, deletefile=None, uploads=None):

        if deletefile:
            session.files = [f for f in session.files if f.filename != deletefile]
            return json.dumps(FileUpload.delete())
        elif file:
            upload = json.loads(FileUpload.get())

            filedir = FileUpload.get_file_dir()

            src_file = os.path.join(request.folder, 'uploads',
                                    session.upload_dir, upload[0]['name'])
            dst_folder = os.path.join(request.folder, 'material', filedir)

            return json.dumps(upload)
        elif uploads:
            return "not implemented"

        else:
            return "not implemented"

    def POST(**vars):
        upload = FileUpload.post()

        upload = json.loads(upload)

        filedata = Storage()

        # Store the number of bytes of the uploaded file
        filedata.bytes = upload[0]['size']

        # Store the file size in human readable format
        filedata.size = mutils.human_size(filedata.bytes)

        filedata.fileid = upload[0]['id']

        # Store filename and extension
        filedata.filename = upload[0]['name']

        filedata.ext = mutils.file_type(upload[0]['name'].split(".")[-1])

        session.files.append(filedata)

        filedir = FileUpload.get_file_dir()

        src_file = os.path.join(request.folder, 'uploads', session.upload_dir,
                                upload[0]['name'])
        dst_folder = os.path.join(request.folder, 'material', filedir)

        if not os.path.isdir(dst_folder):
            os.makedirs(dst_folder)

        # XXX this is necessary only for the resume support
        #if upload[0]['size'] == os.path.getsize(src_file):
            #print "THEY MATCH!!!!!.... %s != %s" % (upload[0]['size'], os.path.getsize(src_file))
        os.rename(src_file, os.path.join(dst_folder, upload[0]['name']))

        return json.dumps(upload)

    return locals()

def default_material(submission):

    file_array = [{"size": "20.0 KB",
                    "ext": "txt",
                    "fileid": "",
                    "bytes": 0,
                    "filename": "Submission.txt"},
                  {"size": "20.0 KB",
                    "ext": "txt",
                    "fileid": "",
                    "bytes": 0,
                    "filename": "DISCLAIMER.txt"}]

    filedir = FileUpload.get_file_dir()
    dst_folder = os.path.join(request.folder, 'material', filedir)

    if not os.path.isdir(dst_folder):
        os.makedirs(dst_folder)

    src_file = os.path.join(request.folder, "../../", "templates", "disclaimer_receiver.txt")
    dst_file = os.path.join(request.folder, 'material', filedir, file_array[1]['filename'])
    shutil.copyfile(src_file, dst_file)

    dst_file = os.path.join(request.folder, 'material', filedir, file_array[0]['filename'])
    fp = open(dst_file, "w+")

    fp.write("# GlobaLeaks submission\n\n")
    #fp.write("To view this submission visit: %s\n\n" % tulip_url)
    fp.write("## Details:\n")
    for key, value in submission.items():
        if key not in ("spooled", "id", "submission_timestamp"):
            fp.write("%s: %s\n" % (key, value))

    session.files.append(file_array[0])
    session.files.append(file_array[1])
    fp.close()
    return True


@configuration_required
def index():
    """
    This is the main submission page.
    """
    # Generate the number the WB will use to come back to
    # their submission
    wb_number = randomizer.generate_tulip_receipt()

    # Perform a check to see if the client is using Tor
    anonymity = Anonymity.TorAccessCheck(request.client, request.env)

    # If a session has not been created yet, create one.
    if not session.wb_id:
        session.wb_id = randomizer.generate_wb_id()

    # -- follow a comment preserved since 'the age of the upload'
    #
    # Tor Browser Bundle has JS enabled by default!
    # Hurray! I love you all!!
    # Yeah, even *you* the anti-JS taliban hater!
    # As someone put it, if you think JS is evil remember
    # that the world is in technicolor and not in black and white.
    # Look up, the sun is shining, thanks to jQuery.

    # This is necessary because otherwise web2py will go crazy when
    # it sees {{ }}
    upload_template = jQueryHelper.upload_tmpl()

    download_template = jQueryHelper.download_tmpl()

    # Generate the material upload elements
    # JavaScript version
    material_js = TR('Material',
                     DIV(_id='file-uploader'),
                     _id='file-uploader-js')

    # .. and non JavaScript
    material_njs = DIV(DIV(LABEL("Material:"),
                                _class="w2p_fl"),
                            DIV(INPUT(_name='material', _type='file',
                                      _id='file-uploader-nonjs'),
                                _class="w2p_fc"),
                                _id="file-uploader-nonjs")

    # Use the web2py captcha setting to generate a Captcha
    # captcha = TR('Are you human?', auth.settings.captcha)

    # The default fields and labels
    form_fields = ['title', 'desc']
    form_labels = {'title': 'Title', 'desc': 'Description'}

    form_extras = []

    # Add to the fields to be displayed the ones inside of
    # the extrafields setting
    #    for i in settings.extrafields.fields:
    #        form_extras.append(str(i['name']))
    #        form_fields.append(str(i['name']))
    #        form_labels[str(i['name'])] = i['desc']

    if settings.extrafields.wizard:
        the_steps = settings.extrafields.gen_wizard()

        form = FormShaman(db.leak, steps=the_steps)
        # this is the only error handled at the moment, the fact that __init__
        # could return only None, maybe an issue when more errors might be managed
        if not hasattr(form, 'vars'):
            return dict(error='No receiver present in the default group', existing_files=[])

    else:
        form = SQLFORM(db.leak,
                       fields=form_fields,
                       labels=form_labels)

    # Check to see if some files have been loaded from a previous session
    existing_files = []
    if session.files:
        for f in session.files:
            existing_files.append(f)

    # Make the submission not spooled and set the timestamp
    form.vars.spooled = False
    form.vars.submission_timestamp = time.time()

    # Insert all the data into the db
    if form.accepts(request.vars):
        logger.debug("Submission %s", request.vars)

        group_ids = []  # Will contain all the groups selected by the WB

        # XXX Since files are processed via AJAX, maybe this is unecessary?
        #     if we want to keep it to allow legacy file upload, then the
        #     file count should only be one.
        # File upload in a slightly smarter way
        # http://www.web2py.com/book/default/chapter/06#Manual-Uploads
        for var in request.vars:
            if var == "material":
                try:
                    f = Storage()
                    f.filename = request.vars.material.filename

                    tmp_file = db.material.file.store(request.body, filename)
                    logger.info("the tmp_file is [%s] with filename [%s]",
                                tmp_file, filename)

                    f.ext = mutils.file_type(filename.split(".")[-1])

                    tmp_fpath = os.path(os.path.join(request.folder,
                                                     'uploads',
                                                     session.upload_dir,
                                                     tmp_file + filename))

                    f.size = os.path.getsize(tmp_fpath)
                    files.append(f)

                    dst_folder = os.path.join(request.folder,
                                              'material',
                                              str(leak_id.id))
                    if not os.path.isdir(dst_folder):
                        os.mkdir(dst_folder)
                    os.rename(os.path.join(request.folder,
                                           'uploads',
                                           session.upload_dir,
                                           tmp_file),
                              dst_folder + filename)
                # XXX define exception for this except
                except:
                    logger.error("There was an error in processing the "
                                 "submission files.")


            if var.startswith("target_") and var.split("_")[-1].isdigit():
                group_ids.append(var.split("_")[-1])

        # The metadata associated with the file is stored inside
        # the session variable this should be safe to use this way.
        if not session.files:
            session.files = []

        # Add the default files
        default_material(form.vars)

        # XXX verify that this is safe
        pfile = json.dumps(session.files)

        # leak_id has been used in the previous code as this value,
        # I'm keeping to don't change the following lines
        leak_id = form.vars.id


        # XXX probably a better way to do this
        # Create a record in submission db associated with leak_id
        # used to keep track of sessions
        if not db(db.submission.session==session.wb_id).select():
            db.submission.insert(session=session.wb_id,
                                 leak_id=leak_id,
                                 dirname=session.dirname)

        # Instantiate the Leak object
        leak = Leak(leak_id)

        # Create the material entry for the submitted data
        leak.add_material(leak_id, None, "localfs", file=pfile)

        # Create the leak with the GlobaLeaks factory
        # (the data has actually already been added to db leak,
        # this just creates the tulips), the first is the whistleblower tulip
        gl.create_tulip(form.vars.id, 0, wb_number[1])

        # create the tulips for every receiver inside a basket

        # if len(group_ids):
        # fixme: we're not considering the selecred group, but *all*
        group_id = db().select(db.targetgroup.ALL).first().id
        leak.create_tulip_by_group(group_id)

        # Make the WB number be *** *** *****
        pretty_number = wb_number[0][:3] + " " + wb_number[0][3:6] + \
                        " " + wb_number[0][6:]

        session.wb_number = pretty_number
        # Clean up all sessions
        session.dirname = None
        session.wb_id = None
        session.files = None

        return dict(leak_id=leak_id, leaker_tulip=pretty_number, error=None,
                    form=None, tulip_url=wb_number[1], jQuery_templates=None,
                    existing_files=existing_files)

    elif form.errors:
        response.flash = 'form has errors'

    return dict(form=form,
                error=None,
                leak_id=None,
                tulip=None,
                tulips=None,
                anonymity=anonymity.result,
                jQuery_templates=(XML(upload_template),
                                  XML(download_template)),
                existing_files=existing_files)

########NEW FILE########
__FILENAME__ = target
#coding: utf-8
"""
This controller module contains every controller that the target can use
to edits its settings. (E.g.: Unsubscribe from a GL node)
"""

@configuration_required
def index():
    return dict(message="hello from target.py")

def valid_pgp_key(pgpkeystring):
    # implementation TODO: 
    # verify that is a valid PGP string, almost checking the header 
    return True

@configuration_required
def bouquet():
    """
    This page is indexed by an uniq identifier by the receiver, and shows
    all accessible Tulips, its the page where she/he could change their
    preferences
    """
    if request and request.args:
        target_url = request.args[0]
    else:
        return dict(err="Tulip index not supplied", password_req=None)

    tulip = Tulip(url=target_url)
    if tulip.id == -1:
        return dict(err="Invalid Tulip", password_req=None)

    receiver_row = db(db.target.id==tulip.target_id).select()

    # PASSWORD CHECKS IN BOUQUET
    if receiver_row[0]['password_enabled'] == True:
        password_form = SQLFORM.factory(Field('access_password', 'password', requires=IS_NOT_EMPTY()))

        if password_form.accepts(request.vars, session):
            if request.vars.access_password != receiver_row[0]['password']:
                print "Bouquet: password does not match"
                return dict(err="Invalid password", password_req=True, password_form=password_form)
            else:
                print "Bouquet: password match correctly!"
        else:
            print "Bouquet: invalid form received"
            return dict(err="Missing password", password_req=True, password_form=password_form)

    else:
        print "Bouquet: this receiver has not password set"


    # pretty string for password default
    if receiver_row[0]['password'] != None:
        passlen = str(len(receiver_row[0]['password']))
        password_default = "Password set and enabled (" + passlen + " char)"
        # MOVI QUI
    else:
        password_default= "password not configured"

    # SET NEW PASSWORD
    security_input = (
        Field('password', requires=IS_LENGTH(minsize=8), default=password_default),
        Field('confirm_password', 
            requires=IS_EQUAL_TO(request.vars.password, error_message="passwords do not match")),
    )

    security_form = SQLFORM.factory(*security_input, table_name="security")

    if security_form.accepts(request.vars, session, keepvalues=True):

        pref = request.vars

        if len(pref.password) > 7:
            # TODO: hash them before store
            db.target[receiver_row[0].id].update_record(password=pref.password)
            # Issue: https://github.com/globaleaks/GlobaLeaks/issues/13
            # specifiy some feature that can't be implemented now (mail notification)
            db.target[receiver_row[0].id].update_record(password_enabled=True)
            db.commit()
            print "saved password " + pref.password

    # this require to be splitted because tulip are leak x target matrix
    bouquet_list = []
    tulip_list = db(db.tulip.target_id==receiver_row[0].id).select()
    for single_t in tulip_list:
        bouquet_list.append(single_t)

    return dict(err=False,
                bouquet=bouquet_list,
                target=receiver_row[0],
                security=security_form, password_req=None)


########NEW FILE########
__FILENAME__ = tulip
#coding: utf-8
"""
This controller module contains every controller for accessing the tulip
from a target
"""

import gluon.contrib.simplejson as json
import os
import shutil

mutils = local_import('material').utils()

@configuration_required
def index():
    import hashlib

    form = SQLFORM.factory(Field('Receipt', requires=IS_NOT_EMPTY()))
    if form.accepts(request.vars, session):
        req = request.vars

        leak_number = req.Receipt.replace(' ', '')
        tulip_url = hashlib.sha256(leak_number).hexdigest()
        redirect("/globaleaks/tulip/status/" + tulip_url)

    redirect("/")

def access_increment(tulip):
    if tulip.accesses_counter:
        new_count = int(tulip.accesses_counter) + 1
        db.tulip[tulip.id].update_record(accesses_counter=str(new_count))
    else:
        db.tulip[tulip.id].update_record(accesses_counter="1")

    db.commit()

    if int(tulip.allowed_accesses) != 0 and \
       int(tulip.accesses_counter) > int(tulip.allowed_accesses):
        return True
    else:
        return False


# http://games.adultswim.com/robot-unicorn-attack-twitchy-online-game.html
def record_comment(comment_feedback, tulip):
    leak_id = tulip.get_leak().get_id()
    db.comment.insert(leak_id=leak_id,
                      commenter_name=tulip.get_target_name(),
                      commenter_id=tulip.get_target(),
                      comment=comment_feedback)
    db.commit()
    for t_id in gl.get_targets(None):
        target = gl.get_target(t_id)
        try:
            tulip_url = db((db.tulip.leak_id==leak_id) & (db.tulip.target_id==t_id.id)).select().first().url
            db.notification.insert(target=target.name,
                    address=target.contact,
                    tulip=tulip_url,
                    leak_id=leak_id,
                    type="comment")
        except:
            pass

    db.commit()

    if tulip.feedbacks_provided:
        new_count = int(tulip.feedbacks_provided) + 1
        db.tulip[tulip.id].update_record(feedbacks_provided=new_count)
    else:
        db.tulip[tulip.id].update_record(feedbacks_provided=1)

FileUpload = UploadHandler()

@configuration_required
@request.restful()
def fileupload():
    """
    Controller for file uploading for leak updating
    """
    response.view = 'generic.json'

    if not session.add_files:
        session.add_files = []

    def GET(tulip_url, file=None, deletefile=None, uploads=None, commit=None):
        try:
            tulip_url = request.args[0]
            tulip = Tulip(url=tulip_url)
        except:
            return json.dumps({"success": "false"})
        if not tulip.is_wb():
            return json.dumps({"success": "false"})

        if deletefile:
            session.add_files = [f for f in session.add_files \
                                 if f.filename != deletefile]
            return json.dumps(FileUpload.delete(uploads=True))
        elif file:
            upload = json.loads(FileUpload.get())

            filedir = FileUpload.get_file_dir(leak_id=tulip.leak.id)

            src_file = os.path.join(request.folder, 'uploads',
                                    session.upload_dir, upload[0]['name'])
            dst_folder = os.path.join(request.folder, 'material', filedir)

            return json.dumps(upload)
        elif commit:
            # print "Session value: %s" % session.add_files
            if not session.add_files:
                return json.dumps({"success": "false"})
            filedir = FileUpload.get_file_dir(leak_id=tulip.leak.id)
            # finding right progressive number
            prog = 1
            dst_folder = os.path.join(request.folder, 'material',
                                      filedir, str(prog))
            while os.path.exists(dst_folder):
                prog += 1
                dst_folder = os.path.join(request.folder, 'material',
                                          filedir, str(prog))
            os.makedirs(dst_folder)

            for filedata in session.add_files:
                if os.path.exists(os.path.join(request.folder,
                                               'uploads', session.upload_dir,
                                               filedata.filename)):
                    src_file = os.path.join(request.folder, 'uploads',
                                            session.upload_dir, filedata.filename)
                    try:
                        shutil.move(src_file,
                                    os.path.join(dst_folder.decode("utf-8"),
                                                 filedata.filename))
                    except OSError:
                        pass
                else:
                    session.add_files.remove(filedata)

            tulip.leak.add_material(tulip.leak.id, prog, None,
                                    file=json.dumps(session.add_files))
            add_files = [(f.ext, f.filename, f.size)
                         for f in session.add_files]
            session.add_files = None
            # Leak needs to be spooled again
            db(db.leak.id == tulip.leak.id).update(spooled=False)

            for t_id in gl.get_targets(None):
                target = gl.get_target(t_id)
                try:
                    t_url = db((db.tulip.leak_id==tulip.leak.id) & (db.tulip.target_id==t_id.id)).select().first().url
                    db.notification.insert(target=target.name,
                            address=target.contact,
                            tulip=t_url,
                            leak_id=tulip.leak.id,
                            type="material")
                except:
                    print "problem in adding to notification DB"

            db.commit()

            return json.dumps({"success": "true", "data": add_files})
        elif uploads:
            return "not implemented"
        else:
            return json.dumps({"success": "false"})

    def POST(tulip_url, **vars):
        try:
            tulip = Tulip(url=tulip_url)
        except:
            return json.dumps({"success": "false"})
        if not tulip.is_wb():
            return json.dumps({"success": "false"})
        upload = FileUpload.post(tulip.leak.id)

        upload = json.loads(upload)

        filedata = Storage()

        # Store the number of bytes of the uploaded file
        filedata.bytes = upload[0]['size']

        # Store the file size in human readable format
        filedata.size = mutils.human_size(filedata.bytes)

        filedata.fileid = upload[0]['id']

        # Store filename and extension
        filedata.filename = upload[0]['name']

        filedata.ext = mutils.file_type(upload[0]['name'].split(".")[-1])

        session.add_files.append(filedata)

        return json.dumps(upload)

    return locals()

@configuration_required
#@auth.requires(((request and request.args and request.args[0]) and
#                (Tulip(url=request.args[0]).target == "0" or not
#                 (gl.get_target_hash(int(Tulip(url=request.args[0]).get_target())))
#                )) or auth.has_membership('targets'))
def status():
    """
    The main TULIP status page
    """
    try:
        tulip_url = request.args[0]
    except IndexError:
        return dict(err=True)

    try:
        tulip = Tulip(url=tulip_url)
    except:
        return dict(err=True, password_req=None, delete=None)

    leak = tulip.get_leak()

    # those are the error not handled by the try/except before
    if tulip.id == -1:
        return dict(err=True, password_req=None, delete=None, tulip_url=tulip_url)

    whistleblower_msg_html = ''
    if tulip.target == "0":
        whistleblower = True
        session.target = None
        with open(settings.globals.whistleblower_file) as filestream:
            whistleblower_msg_html = filestream.read()

        target_url = ''
        delete_capability = False
    else:
        session.admin = False
        session.target = tulip_url
        whistleblower = False
        target_url = "target/" + tulip.url
        try:
            delete_capability = (gl.get_target(int(tulip.get_target()))).delete_cap
        except:
            delete_capability = None

        """
        HERE the receiver password authentication check
        """
        if gl.get_target(int(tulip.get_target())).password_enabled == True:

            password_form = SQLFORM.factory(Field('access_password', 'password', requires=IS_NOT_EMPTY()))

            if password_form.accepts(request.vars, session):
                if request.vars.access_password != gl.get_target(int(tulip.get_target())).password:
                    return dict(err=True, delete=None, 
                            password_req=True, password_form=password_form, tulip_url=tulip_url)
                else:
                    print "password match correctly!"
            else:
                print "invalid form received"
                return dict(err=True, delete=None, 
                        password_req=True, password_form=password_form, tulip_url=tulip_url)
        else:
            print "this receiver has not password set"


    # check if the tulip has been requested to be deleted
    if request.vars and request.vars.delete and delete_capability:
        deleted_tulips = tulip.delete_bros()
        return dict(err=False, password_req=False, delete=deleted_tulips, tulip_url=tulip_url)

    if whistleblower == False:
        # the stats of the whistleblower are not in their own tulip
        if leak.spooled:
            download_available = int(tulip.downloads_counter) < \
                                 int(tulip.allowed_downloads)
        else:
            download_available = -1
        access_available = access_increment(tulip)
        counter_accesses = tulip.accesses_counter
        limit_counter = tulip.allowed_accesses
    else:
        # the stats of the whistleblower stay in the leak/material
        # entry (is it right ?)
        download_available = False
        if leak.whistleblower_access:
            new_count = int(leak.whistleblowing_access) + 1
            leak.whistleblower_access = new_count
        else:
            leak.whistleblower_counter = 1

        counter_accesses = leak.whistleblower_access
        limit_counter = int("50")  # settings.max_submitter_accesses
        access_available = True

    # check if the comment or a vote has been provided:
    if request.vars and request.vars.Comment:
        record_comment(request.vars.Comment, tulip)

    # configuration issue
    # *) if we want permit, in Tulip, to see how many download/clicks has
    #    been doing from the receiver, we need to pass the entire tulip
    #    list, because in fact the information about "counter_access"
    #    "downloaded_access" are different for each tulip.
    # or if we want not permit this information crossing, the interface simply
    # has to stop in printing other receiver behaviour.
    # now is implement the extended version, but need to be selectable by the
    # maintainer.
    tulip_usage = []
    flowers = db(db.tulip.leak_id == leak.get_id()).select()
    for single_tulip in flowers:
        targetname = db(db.target.id == single_tulip.target_id).select(db.target.name).first()
        if targetname:
            if tulip.target == single_tulip.target_id:
                targetname = "You"
            else:
                targetname = targetname.name

        if single_tulip.leak_id == tulip.get_id():
            tulip_usage.append((targetname,single_tulip))
        else:
            tulip_usage.append((targetname, single_tulip))
    # this else is obviously an unsolved bug, but at the moment 0 lines seem
    # to match in leak_id

    feedbacks = []
    users_comment = db(db.comment.leak_id == leak.get_id()).select()
    for single_comment in users_comment:
        if single_comment.leak_id == leak.get_id():
            feedbacks.append(single_comment)

    jQueryHelper = local_import('jquery_helper')
    upload_template = jQueryHelper.upload_tmpl()
    download_template = jQueryHelper.download_tmpl()
    submission_mats = [(m.url, json.loads(m.file)) for m in leak.material]
    return dict(err=None,delete=None,password_req=False,
            access_available=access_available,
            download_available=download_available,
            whistleblower=whistleblower,
            whistleblower_msg_html=whistleblower_msg_html,
            tulip_url=tulip_url,
            leak_id=leak.id,
            leak_title=leak.title,
            leak_tags=leak.tags,
            leak_desc=leak.desc,
            leak_extra=leak.get_extra(),
            leak_material=leak.material,
            tulip_accesses=counter_accesses,
            tulip_allowed_accesses=limit_counter,
            tulip_download=tulip.downloads_counter,
            tulip_allowed_download=tulip.allowed_downloads,
            tulipUsage=tulip_usage,
            feedbacks=feedbacks,
            feedbacks_n=tulip.get_feedbacks_provided(),
            receiver_id=tulip.target,
            target_del_cap=delete_capability,
            target_url=target_url,
            targets=gl.get_targets("ANY"),
            submission_materials=submission_mats,
            jQuery_templates=(XML(upload_template),
                              XML(download_template))
            )


def download_increment(tulip):

    if (int(tulip.downloads_counter) > int(tulip.allowed_downloads)):
        return False

    if tulip.downloads_counter:
        new_count = int(tulip.downloads_counter) + 1
        db.tulip[tulip.id].update_record(downloads_counter=new_count)
    else:
        db.tulip[tulip.id].update_record(downloads_counter=1)

    return True


@configuration_required
def download():
    import os

    try:
        tulip_url = request.args[0]
    except IndexError:
        return dict(err=True)

    try:
        t = Tulip(url=tulip_url)
    except:
        redirect("/globaleaks/tulip/status/" + tulip_url)

    if not download_increment(t):
        redirect("/globaleaks/tulip/status/" + tulip_url)

    leak = t.get_leak()

    filename = db(db.submission.leak_id==leak.id).select().first().dirname
    try:
        filename = "%s-%s" % (filename, request.args[1])
    except IndexError:
        pass
    response.headers['Content-Type'] = "application/octet"
    response.headers['Content-Disposition'] = 'attachment; filename="' + \
                                              filename + '.zip"'

    download_file = os.path.join(request.folder, 'material/',
                                 filename + '.zip')

    # XXX to make proper handlers to manage the fetch of dirname
    return response.stream(open(download_file, 'rb'))

########NEW FILE########
__FILENAME__ = cleaner
#!/usr/bin/env python
"""
This is used to clean expired TULIPs and broken uploads

REMIND: test environment, if you're testing this script start/stopping globaleaks,
change in globaleaks/cron/crontab the timing, using "* *", because web2py start 
his own crontab only if set to run every minute
"""
import sys
import os
import time
import stat
import datetime
# from boto.ses.connection import SESConnection

from gluon.utils import md5_hash
from gluon.restricted import RestrictedError
from config import projroot

# recursively clean the directories
# shutil.rmtree: we are against you!
def clean_directory(subm_id, absolute_dir):
    removed_file_count = 0

    for submitted_file in os.listdir(absolute_dir):

        absfilename = os.path.join(absolute_dir, submitted_file)
        if os.path.isdir(absfilename):
            removed_file_count += clean_directory(subm_id, absfilename)
            continue

        if os.access(absfilename, os.W_OK):
            removed_file_count += 1
            os.unlink(absfilename)
        else:
            logger.fatal("anomaly in %s: unable to unlink", absfilename)

    logger.debug("related to tulip %d, has been removed %d from [%s]", subm_id, removed_file_count, absolute_dir)
    os.rmdir(absolute_dir)

    return removed_file_count

# useful init
# logger = local_import('logger').start_logger(settings.logging)
# logger = local_import('logger').logger

# tulip removal deadline, converted in seconds
if settings.tulip.expire_days:
    tulipsexpire = int(settings.tulip.expire_days) * (60 * 60 * 24)
else:
    logger.info("Unable to maintain clean GlobaLeaks database! required configuration in globaleaks.conf expire_days field")

total_submissions = db().select(db.leak.ALL)
actual_time = time.time()

for subm_row in total_submissions:

    submission_time = float(subm_row.submission_timestamp)
    print "debug: checking expire seconds: act %d subm %d expire %d" % (actual_time, submission_time, tulipsexpire)

    if actual_time > (submission_time + tulipsexpire):

        tulip_rows = db(db.tulip.leak_id==subm_row.id).select()
        # remember: material contains the description and the list of files
        material_rows = db(db.material.leak_id==subm_row.id).select()
        # submission contains the directory and the compressed version of the files
        file_row = db(db.submission.leak_id==subm_row.id).select().first()

        absdir = os.path.join(projroot, 'globaleaks', 'applications', 'globaleaks', 'material', file_row.dirname)
        logger.info("expired submission id #%d contains %d Tulips, filesystem ref: %s", subm_row.id, len(tulip_rows), absdir)

        # we may have: the /path/globaleaks/material + 'name-stored' [.zip|/],
        # the directory may contains the files uncompressed

        if os.access((absdir + '.zip'), os.W_OK):
            os.unlink(absdir + '.zip')

        file_deleted = 0
        if os.access(absdir, os.X_OK ):
            file_deleted += clean_directory(subm_row.id, absdir)

        # database removal sequence
        db(db.leak.id==subm_row.id).delete()
        db(db.material.leak_id==subm_row.id).delete()
        db(db.submission.leak_id==subm_row.id).delete()

        for single_tulip in tulip_rows:
            db(db.tulip.id==single_tulip.id).delete()
    
        db.commit()


# broken upload checks

########NEW FILE########
__FILENAME__ = mail_spool
#!/usr/bin/env python
"""
This is used to spool tulips send them to targets and
perform operations related to the health and wellbeing of
a GlobaLeaks node
"""
import sys
import os
import time
import stat
import datetime
# from boto.ses.connection import SESConnection

from gluon.utils import md5_hash
from gluon.restricted import RestrictedError
from gluon.tools import Mail

from config import projroot

MimeMail = local_import('mailer').MultiPart_Mail(settings)


# logger = local_import('logger').logger
# .start_logger(settings.logging)
compressor = local_import('compress_material').Zip()
randomizer = local_import('randomizer')

# conn = SESConnection(settings.aws_key, settings.aws_secret_key)

logger.debug('### Starting GlobaLeaks at: %s ###',  time.ctime())

unspooled = db(db.leak.spooled!=True).select()
logger.debug("New material: %s : ", unspooled)

for leak_to_spool in unspooled:
    leak = Leak(leak_to_spool.id)
    submission = db(db.submission.leak_id==leak_to_spool.id).select().first()
    if submission.dirname and not randomizer.is_human_dirname(submission.dirname):
        human_dirname = randomizer.generate_human_dirname(request,
                                                          leak,
                                                          submission.dirname)
        os.rename(os.path.join(request.folder, "material", submission.dirname),
                  os.path.join(request.folder, "material", human_dirname))
        db(db.submission.id == submission.id).update(dirname=human_dirname)
    if submission.dirname:
        human_path = os.path.join(request.folder, "material", submission.dirname)
        compressor.create_zip(db, leak_to_spool, request, logger)
        compressor.create_zip(db, leak_to_spool, request, logger, no_subdirs=True)
        first = True
        for directory in os.walk(human_path):
            if not first:
                mat_dir = directory[0]
                compressor.create_zip(db, leak_to_spool, request, logger,
                                      None, mat_dir)
            first = False
    db.leak[leak_to_spool.id].update_record(spooled=True)
    logger.debug(leak_to_spool)
    db.commit()

mails = db(db.mail).select()
logger.debug(str(mails))

for m in mails:
    context = dict(name=m.target,
                    sitename=settings.globals.sitename,
                    tulip_url=m.tulip,
                    site=settings.globals.baseurl,
                    sitehs=settings.globals.hsurl)

    message_txt = MimeMail.make_txt(context, settings.globals.email_txt_template)
    message_html = MimeMail.make_html(context, settings.globals.email_html_template)

    # XXX Use for AWS
    # conn.send_email(source='node@globaleaks.org', \
    #     subject='GlobaLeaks notification for:' + m.target,\
    #     body=message, to_addresses=m.address, cc_addresses=None, \
    #     bcc_addresses=None, format='text', reply_addresses=None, \
    #     return_path=None)

    to = m.target + " <" + m.address + ">"
    subject = "[GlobaLeaks] A TULIP from node %s for %s - %s" % (
              settings.globals.sitename, m.target, str(m.tulip[-8:]))
    logger.debug("Sending to %s", m.target)

    #if MimeMail.send(to=m.address, subject=subject,
    #                 message_text=message_txt,
    #                 message_html=message_html):
    if mail.send(to=m.address, subject=subject,
                    message=(message_txt, message_html)):
        logger.debug("email sent.")
        db(db.mail.id==m.id).delete()
        db.commit()
    else:
        logger.warn("error in sending mail (%s)", m.address)

    # XXX Uncomment in real world environment
    # mail.send(to=m.address,subject="GlobaLeaks notification for: " + \
    #    m.target,message=message_html)


##########
notifications = db(db.notification).select()
for n in notifications:
    context = dict(name=n.target,
                    sitename=settings.globals.sitename,
                    tulip_url=n.tulip,
                    site=settings.globals.baseurl,
                    sitehs=settings.globals.hsurl,
                    type=n.type)

    to = n.target + " <" + n.address + ">"
    if n.type == "comment":
        subject = "[GlobaLeaks] New comment from node %s for %s - %s" % (
              settings.globals.sitename, n.target, str(n.tulip[-8:]))
        message_txt = MimeMail.make_txt(context, settings.globals.notification_txt_template)
        message_html = MimeMail.make_html(context, settings.globals.notification_html_template)
    elif n.type == "material":
        subject = "[GlobaLeaks] New material from node %s for %s - %s" % (
              settings.globals.sitename, n.target, str(n.tulip[-8:]))
        message_txt = MimeMail.make_txt(context, settings.globals.notification_txt_template)
        message_html = MimeMail.make_html(context, settings.globals.notification_html_template)
    else:
        break

    logger.info("Sending to %s\n", n.target)
    if mail.send(to=n.address, subject=subject,
                    message=(message_txt, message_html)):

        logger.info("email sent.")
        db(db.notification.id==n.id).delete()
        db.commit()

    else:
        logger.info("error in sending mail.")


##########


path = os.path.join(projroot, 'globaleaks',
                    'applications', 'globaleaks', 'errors')

hashes = {}

### CONFIGURE HERE
ALLOW_DUPLICATES = True
### END CONFIGURATION

if settings.globals.debug_notification:
    for file in os.listdir(path):
        filename = os.path.join(path, file)

        if not ALLOW_DUPLICATES:
            file_data = open(filename, 'r').read()
            key = md5_hash(file_data)

            if key in hashes:
                continue

            hashes[key] = 1

        error = RestrictedError()
        error.load(request, request.application, filename)
        logger.debug("REQUEST-APP: %s" % dir(request))

        logger.debug("Sending email...")

        message = '<b>There has been an error on a node.</b><br>'
        message += '<h1>This is the trackback:</h1><br><pre>%s</pre><br><br><br>' % error.traceback
        message += "<h1>this is the environment:</h1><br>"
        try:
            message += "<h2>RESPONSE: </h2><br> %s<br><br>" % error.snapshot['response']
            message += "<h2>LOCALS: </h2><br> %s<br><br>" % error.snapshot['locals']
            message += "<h2>REQUEST: </h2><br> %s<br><br>" % error.snapshot['request']
            message += "<h2>SESSION:</h2><br>  %s<br><br>" % error.snapshot['session']
        except KeyError:
            pass

        # http://blog.transparency.org/2011/11/22/in-russia-the-fight-against-corruption-goes-online
        if MimeMail.send(to=settings.globals.debug_email, subject='new web2py ticket',
                         message_text=message,
                         message_html=message):
            logger.debug("... email sent.")
            if settings.globals.debug_deletetickets and os.access(filename, os.W_OK):
                os.unlink(filename)

    # xxx: should be removed, and used as soon as it becomes necessary
    db.commit()

########NEW FILE########
__FILENAME__ = dev
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN',
'%Y-%m-%d': '%Y-%m-%d',
'%Y-%m-%d %H:%M:%S': '%Y-%m-%d %H:%M:%S',
'Accept Disclaimer': 'DEVELOPMENT-MODE',
'Add': 'DEVELOPMENT-MODE',
'Add Files': 'DEVELOPMENT-MODE',
'Add files': 'DEVELOPMENT-MODE',
'Analyze the received material, your work is fundamental in uncovering the truth': 'DEVELOPMENT-MODE',
'Are you sure you want to delete this object?': 'DEVELOPMENT-MODE',
'Ask useful details to the whistleblower thru the comment box': 'DEVELOPMENT-MODE',
'Available databases and tables': 'DEVELOPMENT-MODE',
'Bouquet': 'DEVELOPMENT-MODE',
'Cancel upload': 'DEVELOPMENT-MODE',
'Comments': 'DEVELOPMENT-MODE',
'Complete Download': 'DEVELOPMENT-MODE',
'Config': 'DEVELOPMENT-MODE',
'Current request': 'DEVELOPMENT-MODE',
'Current response': 'DEVELOPMENT-MODE',
'Current session': 'DEVELOPMENT-MODE',
'Delete Files': 'DEVELOPMENT-MODE',
'Done': 'DEVELOPMENT-MODE',
'Download': 'DEVELOPMENT-MODE',
'Downloads': 'DEVELOPMENT-MODE',
'Edit current record': 'DEVELOPMENT-MODE',
'Encrypted ZIP': 'DEVELOPMENT-MODE',
'Error: only ten digits are accepted as receipt': 'DEVELOPMENT-MODE',
'Error: you puts more than 10 digits': 'DEVELOPMENT-MODE',
'Finish': 'Finish',
'Forward to another receiver group': 'DEVELOPMENT-MODE',
'Globalview': 'DEVELOPMENT-MODE',
'Groups': 'DEVELOPMENT-MODE',
'I want delete this tip-off and all the others derived from the same material': 'I want delete this tip-off and all the others derived from the same material',
'I want delete this tulip and all the tulips derived from the same material': 'DEVELOPMENT-MODE',
'ID': 'DEVELOPMENT-MODE',
'Import/Export': 'DEVELOPMENT-MODE',
'Incomplete configuration': 'DEVELOPMENT-MODE',
'Index': 'DEVELOPMENT-MODE',
'Internal State': 'DEVELOPMENT-MODE',
"It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.": 'DEVELOPMENT-MODE',
'Language': 'Language',
'Logout': 'DEVELOPMENT-MODE',
'Material': 'DEVELOPMENT-MODE',
'Material description': 'DEVELOPMENT-MODE',
'Material has not been processed yet': 'DEVELOPMENT-MODE',
'New Record': 'DEVELOPMENT-MODE',
'Next': 'Next',
'No comments': 'DEVELOPMENT-MODE',
'No databases in this application': 'DEVELOPMENT-MODE',
'Node View': 'DEVELOPMENT-MODE',
'Not spread this link. It is intended be for your eyes only': 'DEVELOPMENT-MODE',
'PGP Encrypted ZIP': 'DEVELOPMENT-MODE',
'Password': 'Password',
'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)': 'DEVELOPMENT-MODE',
'Preferences': 'DEVELOPMENT-MODE',
'Previous': 'Previous',
'Receiver': 'DEVELOPMENT-MODE',
'Receivers': 'DEVELOPMENT-MODE',
'Redirecting to Hidden Serivice in': 'Redirecting to Hidden Serivice in',
'Rows in table': 'DEVELOPMENT-MODE',
'Rows selected': 'DEVELOPMENT-MODE',
'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'DEVELOPMENT-MODE',
'Select Group': 'DEVELOPMENT-MODE',
'Select Group:': 'Select Group:',
'Stats': 'DEVELOPMENT-MODE',
'Step': 'DEVELOPMENT-MODE',
'Submission': 'DEVELOPMENT-MODE',
'Submission Interface': 'Submission Interface',
'Submission Receipt': 'DEVELOPMENT-MODE',
'Submission interface': 'DEVELOPMENT-MODE',
'Submission status': 'DEVELOPMENT-MODE',
'Submit material': 'DEVELOPMENT-MODE',
'Submit receipt': 'Submit receipt',
'Tags': 'DEVELOPMENT-MODE',
'Targets': 'Targets',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'DEVELOPMENT-MODE',
'This is a number you should write down to keep track of your submission': 'DEVELOPMENT-MODE',
'This is the material submitted by the whistleblower for your revision. You are invited to': 'DEVELOPMENT-MODE',
'Tip-off': 'DEVELOPMENT-MODE',
'Tip-off Receipt': 'DEVELOPMENT-MODE',
'Tip-off access statistics': 'DEVELOPMENT-MODE',
'Tip-off removed and all relatives': 'DEVELOPMENT-MODE',
'Tulip': 'Tulip',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.',
'Username': 'DEVELOPMENT-MODE',
'Views': 'DEVELOPMENT-MODE',
'Warning': 'Warning',
'Welcome back Whistleblower: this Tip-off interface is unique for you.': 'DEVELOPMENT-MODE',
'Welcome back Whistleblower: this interface is unique for you.': 'Welcome back Whistleblower: this interface is unique for you.',
'Whistleblower': 'DEVELOPMENT-MODE',
'You are also able to use your Whistleblower receipt from the first page.': 'DEVELOPMENT-MODE',
'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receiver.': 'DEVELOPMENT-MODE',
'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.': 'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.',
"You've received a": 'DEVELOPMENT-MODE',
'Your submission': 'DEVELOPMENT-MODE',
'Your tip-off': 'Your tip-off',
'ZIP': 'DEVELOPMENT-MODE',
'check back later': 'DEVELOPMENT-MODE',
'database': 'DEVELOPMENT-MODE',
'database %s select': 'DEVELOPMENT-MODE',
'export as csv file': 'DEVELOPMENT-MODE',
'insert new': 'DEVELOPMENT-MODE',
'insert new %s': 'DEVELOPMENT-MODE',
'invalid receipt: Tip-off not found': 'DEVELOPMENT-MODE',
'must accept disclaimer': 'DEVELOPMENT-MODE',
'next 100 rows': 'DEVELOPMENT-MODE',
'or import from csv file': 'DEVELOPMENT-MODE',
'powered by': 'powered by',
'previous 100 rows': 'DEVELOPMENT-MODE',
'record': 'DEVELOPMENT-MODE',
'record id': 'DEVELOPMENT-MODE',
'seconds': 'seconds',
'selected': 'DEVELOPMENT-MODE',
'table': 'DEVELOPMENT-MODE',
'tulips': 'DEVELOPMENT-MODE',
}

########NEW FILE########
__FILENAME__ = es-es
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"actualice" es una expresión opcional como "campo1=\'nuevo_valor\'". No se puede actualizar o eliminar resultados de un JOIN',
'%Y-%m-%d': '%Y-%m-%d',
'%Y-%m-%d %H:%M:%S': '%Y-%m-%d %H:%M:%S',
'%s rows deleted': '%s filas eliminadas',
'%s rows updated': '%s filas actualizadas',
'(something like "it-it")': '(algo como "it-it")',
'A new version of web2py is available': 'Hay una nueva versión de web2py disponible',
'A new version of web2py is available: %s': 'Hay una nueva versión de web2py disponible: %s',
'ATTENTION: Login requires a secure (HTTPS) connection or running on localhost.': 'ATENCION: Inicio de sesión requiere una conexión segura (HTTPS) o localhost.',
'ATTENTION: TESTING IS NOT THREAD SAFE SO DO NOT PERFORM MULTIPLE TESTS CONCURRENTLY.': 'ATENCION: NO EJECUTE VARIAS PRUEBAS SIMULTANEAMENTE, NO SON THREAD SAFE.',
'ATTENTION: you cannot edit the running application!': 'ATENCION: no puede modificar la aplicación que se ejecuta!',
'About': 'Acerca de',
'About application': 'Acerca de la aplicación',
'Accept Disclaimer': 'Accept Disclaimer',
'Add': 'Add',
'Add Files': 'Add Files',
'Add files': 'Add files',
'Admin is disabled because insecure channel': 'Admin deshabilitado, el canal no es seguro',
'Admin is disabled because unsecure channel': 'Admin deshabilitado, el canal no es seguro',
'Administrative interface': 'Interfaz administrativa',
'Administrator Password:': 'Contraseña del Administrador:',
'Analyze the received material, your work is fundamental in uncovering the truth': 'Analyze the received material, your work is fundamental in uncovering the truth',
'Are you sure you want to delete file "%s"?': '¿Está seguro que desea eliminar el archivo "%s"?',
'Are you sure you want to delete this object?': 'Are you sure you want to delete this object?',
'Are you sure you want to uninstall application "%s"': '¿Está seguro que desea desinstalar la aplicación "%s"',
'Are you sure you want to uninstall application "%s"?': '¿Está seguro que desea desinstalar la aplicación "%s"?',
'Ask useful details to the whistleblower thru the comment box': 'Ask useful details to the whistleblower thru the comment box',
'Authentication': 'Autenticación',
'Available databases and tables': 'Bases de datos y tablas disponibles',
'Bouquet': 'Bouquet',
'Cancel upload': 'Cancel upload',
'Cannot be empty': 'No puede estar vacío',
'Cannot compile: there are errors in your app.        Debug it, correct errors and try again.': 'No se puede compilar: hay errores en su aplicación. Depure, corrija errores y vuelva a intentarlo.',
'Change Password': 'Cambie Contraseña',
'Check to delete': 'Marque para eliminar',
'Client IP': 'IP del Cliente',
'Comments': 'Comments',
'Complete Download': 'Complete Download',
'Config': 'Config',
'Controller': 'Controlador',
'Controllers': 'Controladores',
'Copyright': 'Derechos de autor',
'Create new application': 'Cree una nueva aplicación',
'Current request': 'Solicitud en curso',
'Current response': 'Respuesta en curso',
'Current session': 'Sesión en curso',
'DB Model': 'Modelo "db"',
'DESIGN': 'DISEÑO',
'Database': 'Base de datos',
'Date and Time': 'Fecha y Hora',
'Delete': 'Elimine',
'Delete Files': 'Delete Files',
'Delete:': 'Elimine:',
'Deploy on Google App Engine': 'Instale en Google App Engine',
'Description': 'Descripción',
'Design for': 'Diseño para',
'Documentation': 'Documentación',
'Done': 'Done',
'Download': 'Download',
'Downloads': 'Downloads',
'E-mail': 'Correo electrónico',
'EDIT': 'EDITAR',
'Edit': 'Editar',
'Edit Profile': 'Editar Perfil',
'Edit This App': 'Edite esta App',
'Edit application': 'Editar aplicación',
'Edit current record': 'Edite el registro actual',
'Editing file': 'Editando archivo',
'Editing file "%s"': 'Editando archivo "%s"',
'Encrypted ZIP': 'Encrypted ZIP',
'Error logs for "%(app)s"': 'Bitácora de errores en "%(app)s"',
'Error: only ten digits are accepted as receipt': 'Error: only ten digits are accepted as receipt',
'Error: you puts more than 10 digits': 'Error: you puts more than 10 digits',
'Finish': 'Finish',
'First name': 'Nombre',
'Forward to another receiver group': 'Forward to another receiver group',
'Functions with no doctests will result in [passed] tests.': 'Funciones sin doctests equivalen a pruebas [aceptadas].',
'Globalview': 'Globalview',
'Group ID': 'ID de Grupo',
'Groups': 'Groups',
'Hello World': 'Hola Mundo',
'I want delete this tip-off and all the others derived from the same material': 'I want delete this tip-off and all the others derived from the same material',
'I want delete this tulip and all the tulips derived from the same material': 'I want delete this tulip and all the tulips derived from the same material',
'ID': 'ID',
'Import/Export': 'Importar/Exportar',
'Incomplete configuration': 'Incomplete configuration',
'Index': 'Indice',
'Installed applications': 'Aplicaciones instaladas',
'Internal State': 'Estado Interno',
'Invalid Query': 'Consulta inválida',
'Invalid action': 'Acción inválida',
'Invalid email': 'Correo inválido',
"It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.": "It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.",
'Language': 'Language',
'Language files (static strings) updated': 'Archivos de lenguaje (cadenas estáticas) actualizados',
'Languages': 'Lenguajes',
'Last name': 'Apellido',
'Last saved on:': 'Guardado en:',
'Layout': 'Diseño de página',
'License for': 'Licencia para',
'Login': 'Inicio de sesión',
'Login to the Administrative Interface': 'Inicio de sesión para la Interfaz Administrativa',
'Logout': 'Fin de sesión',
'Lost Password': 'Contraseña perdida',
'Main Menu': 'Menú principal',
'Material': 'Material',
'Material description': 'Material description',
'Material has not been processed yet': 'Material has not been processed yet',
'Menu Model': 'Modelo "menu"',
'Models': 'Modelos',
'Modules': 'Módulos',
'NO': 'NO',
'Name': 'Nombre',
'New Record': 'Registro nuevo',
'Next': 'Next',
'No comments': 'No comments',
'No databases in this application': 'No hay bases de datos en esta aplicación',
'Node View': 'Node View',
'Not spread this link. It is intended be for your eyes only': 'Not spread this link. It is intended be for your eyes only',
'Online examples': 'Ejemplos en línea',
'Origin': 'Origen',
'Original/Translation': 'Original/Traducción',
'PGP Encrypted ZIP': 'PGP Encrypted ZIP',
'Password': 'Contraseña',
'Peeking at file': 'Visualizando archivo',
'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)': 'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)',
'Powered by': 'Este sitio usa',
'Preferences': 'Preferences',
'Previous': 'Previous',
'Query:': 'Consulta:',
'Receiver': 'Receiver',
'Receivers': 'Receivers',
'Record ID': 'ID de Registro',
'Redirecting to Hidden Serivice in': 'Redirecting to Hidden Serivice in',
'Register': 'Registrese',
'Registration key': 'Contraseña de Registro',
'Reset Password key': 'Reset Password key',
'Resolve Conflict file': 'archivo Resolución de Conflicto',
'Role': 'Rol',
'Rows in table': 'Filas en la tabla',
'Rows selected': 'Filas seleccionadas',
'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Saved file hash:': 'Hash del archivo guardado:',
'Select Group:': 'Select Group:',
'Static files': 'Archivos estáticos',
'Stats': 'Stats',
'Step': 'Step',
'Stylesheet': 'Hoja de estilo',
'Submission': 'Submission',
'Submission Interface': 'Submission Interface',
'Submission Receipt': 'Submission Receipt',
'Submission interface': 'Submission interface',
'Submission status': 'Submission status',
'Submit material': 'Submit material',
'Submit receipt': 'Submit receipt',
'Sure you want to delete this object?': '¿Está seguro que desea eliminar este objeto?',
'Table name': 'Nombre de la tabla',
'Tags': 'Tags',
'Targets': 'Targets',
'Testing application': 'Probando aplicación',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'La "consulta" es una condición como "db.tabla1.campo1==\'valor\'". Algo como "db.tabla1.campo1==db.tabla2.campo2" resulta en un JOIN SQL.',
'The output of the file is a dictionary that was rendered by the view': 'La salida del archivo es un diccionario escenificado por la vista',
'There are no controllers': 'No hay controladores',
'There are no models': 'No hay modelos',
'There are no modules': 'No hay módulos',
'There are no static files': 'No hay archivos estáticos',
'There are no translators, only default language is supported': 'No hay traductores, sólo el lenguaje por defecto es soportado',
'There are no views': 'No hay vistas',
'This is a copy of the scaffolding application': 'Esta es una copia de la aplicación de andamiaje',
'This is a number you should write down to keep track of your submission': 'This is a number you should write down to keep track of your submission',
'This is the %(filename)s template': 'Esta es la plantilla %(filename)s',
'This is the material submitted by the whistleblower for your revision. You are invited to': 'This is the material submitted by the whistleblower for your revision. You are invited to',
'Ticket': 'Tiquete',
'Timestamp': 'Timestamp',
'Tip-off': 'Tip-off',
'Tip-off access statistics': 'Tip-off access statistics',
'Tip-off removed and all relatives': 'Tip-off removed and all relatives',
'Tulip': 'Tulip',
'Tulip Receipt': 'Tulip Receipt',
'Tulip access statistics': 'Tulip access statistics',
'Tulip removed and all relatives': 'Tulip removed and all relatives',
'Tulips': 'Tulips',
'Unable to check for upgrades': 'No es posible verificar la existencia de actualizaciones',
'Unable to download': 'No es posible la descarga',
'Unable to download app': 'No es posible descarga la aplicación',
'Update:': 'Actualice:',
'Upload existing application': 'Suba esta aplicación',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Use (...)&(...) para AND, (...)|(...) para OR, y ~(...) para NOT, para crear consultas más complejas.',
'User ID': 'ID de Usuario',
'Username': 'Username',
'View': 'Vista',
'Views': 'Vistas',
'Warning': 'Warning',
'Welcome': 'Welcome',
'Welcome %s': 'Bienvenido %s',
'Welcome back Whistleblower: this TULIP interface is unique for you.': 'Welcome back Whistleblower: this TULIP interface is unique for you.',
'Welcome back Whistleblower: this interface is unique for you.': 'Welcome back Whistleblower: this interface is unique for you.',
'Welcome to web2py': 'Bienvenido a web2py',
'Which called the function': 'La cual llamó la función',
'Whistleblower': 'Whistleblower',
'YES': 'SI',
'You are also able to use your Whistleblower receipt from the first page.': 'You are also able to use your Whistleblower receipt from the first page.',
'You are successfully running web2py': 'Usted está ejecutando web2py exitosamente',
'You can modify this application and adapt it to your needs': 'Usted puede modificar esta aplicación y adaptarla a sus necesidades',
'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.': 'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.',
'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.': 'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.',
'You visited the url': 'Usted visitó la url',
"You've received a": "You've received a",
"You've received a Tulip...": "You've received a Tulip...",
'Your submission': 'Your submission',
'Your tip-off': 'Your tip-off',
'ZIP': 'ZIP',
'about': 'acerca de',
'additional code for your application': 'código adicional para su aplicación',
'admin disabled because no admin password': ' por falta de contraseña',
'admin disabled because not supported on google app engine': 'admin deshabilitado, no es soportado en GAE',
'admin disabled because unable to access password file': 'admin deshabilitado, imposible acceder al archivo con la contraseña',
'and rename it (required):': 'y renombrela (requerido):',
'and rename it:': ' y renombrelo:',
'appadmin': 'appadmin',
'appadmin is disabled because insecure channel': 'admin deshabilitado, el canal no es seguro',
'application "%s" uninstalled': 'aplicación "%s" desinstalada',
'application compiled': 'aplicación compilada',
'application is compiled and cannot be designed': 'la aplicación está compilada y no puede ser modificada',
'cache': 'cache',
'cache, errors and sessions cleaned': 'cache, errores y sesiones eliminados',
'cannot create file': 'no es posible crear archivo',
'cannot upload file "%(filename)s"': 'no es posible subir archivo "%(filename)s"',
'change password': 'cambie contraseña',
'check all': 'marcar todos',
'check back later': 'check back later',
'clean': 'limpiar',
'click to check for upgrades': 'haga clic para buscar actualizaciones',
'compile': 'compilar',
'compiled application removed': 'aplicación compilada removida',
'controllers': 'controladores',
'create file with filename:': 'cree archivo con nombre:',
'create new application:': 'nombre de la nueva aplicación:',
'crontab': 'crontab',
'currently saved or': 'actualmente guardado o',
'customize me!': 'Adaptame!',
'data uploaded': 'datos subidos',
'database': 'base de datos',
'database %s select': 'selección en base de datos %s',
'database administration': 'administración base de datos',
'db': 'db',
'defines tables': 'define tablas',
'delete': 'eliminar',
'delete all checked': 'eliminar marcados',
'design': 'modificar',
'done!': 'listo!',
'edit': 'editar',
'edit controller': 'editar controlador',
'edit profile': 'editar perfil',
'errors': 'errores',
'export as csv file': 'exportar como archivo CSV',
'exposes': 'expone',
'extends': 'extiende',
'failed to reload module': 'recarga del módulo ha fallado',
'file "%(filename)s" created': 'archivo "%(filename)s" creado',
'file "%(filename)s" deleted': 'archivo "%(filename)s" eliminado',
'file "%(filename)s" uploaded': 'archivo "%(filename)s" subido',
'file "%(filename)s" was not deleted': 'archivo "%(filename)s" no fué eliminado',
'file "%s" of %s restored': 'archivo "%s" de %s restaurado',
'file changed on disk': 'archivo modificado en el disco',
'file does not exist': 'archivo no existe',
'file saved on %(time)s': 'archivo guardado %(time)s',
'file saved on %s': 'archivo guardado %s',
'help': 'ayuda',
'htmledit': 'htmledit',
'includes': 'incluye',
'insert new': 'inserte nuevo',
'insert new %s': 'inserte nuevo %s',
'internal error': 'error interno',
'invalid password': 'contraseña inválida',
'invalid receipt: Tip-off not found': 'invalid receipt: Tip-off not found',
'invalid receipt: Tulip not found': 'invalid receipt: Tulip not found',
'invalid request': 'solicitud inválida',
'invalid ticket': 'tiquete inválido',
'language file "%(filename)s" created/updated': 'archivo de lenguaje "%(filename)s" creado/actualizado',
'languages': 'lenguajes',
'languages updated': 'lenguajes actualizados',
'loading...': 'cargando...',
'located in the file': 'localizada en el archivo',
'login': 'inicio de sesión',
'logout': 'fin de sesión',
'lost password?': '¿olvido la contraseña?',
'merge': 'combinar',
'models': 'modelos',
'modules': 'módulos',
'must accept disclaimer': 'must accept disclaimer',
'new application "%s" created': 'nueva aplicación "%s" creada',
'new record inserted': 'nuevo registro insertado',
'next 100 rows': '100 filas siguientes',
'or import from csv file': 'o importar desde archivo CSV',
'or provide application url:': 'o provea URL de la aplicación:',
'pack all': 'empaquetar todo',
'pack compiled': 'empaquete compiladas',
'powered by': 'powered by',
'previous 100 rows': '100 filas anteriores',
'record': 'registro',
'record does not exist': 'el registro no existe',
'record id': 'id de registro',
'register': 'registrese',
'remove compiled': 'eliminar compiladas',
'restore': 'restaurar',
'revert': 'revertir',
'save': 'guardar',
'seconds': 'seconds',
'selected': 'seleccionado(s)',
'session expired': 'sesión expirada',
'shell': 'shell',
'site': 'sitio',
'some files could not be removed': 'algunos archivos no pudieron ser removidos',
'state': 'estado',
'static': 'estáticos',
'table': 'tabla',
'test': 'probar',
'the application logic, each URL path is mapped in one exposed function in the controller': 'la lógica de la aplicación, cada ruta URL se mapea en una función expuesta en el controlador',
'the data representation, define database tables and sets': 'la representación de datos, define tablas y conjuntos de base de datos',
'the presentations layer, views are also known as templates': 'la capa de presentación, las vistas también son llamadas plantillas',
'these files are served without processing, your images go here': 'estos archivos son servidos sin procesar, sus imágenes van aquí',
'to  previous version.': 'a la versión previa.',
'translation strings for the application': 'cadenas de caracteres de traducción para la aplicación',
'try': 'intente',
'try something like': 'intente algo como',
'tulips': 'tulips',
'unable to create application "%s"': 'no es posible crear la aplicación "%s"',
'unable to delete file "%(filename)s"': 'no es posible eliminar el archivo "%(filename)s"',
'unable to parse csv file': 'no es posible analizar el archivo CSV',
'unable to uninstall "%s"': 'no es posible instalar "%s"',
'uncheck all': 'desmarcar todos',
'uninstall': 'desinstalar',
'update': 'actualizar',
'update all languages': 'actualizar todos los lenguajes',
'upload application:': 'subir aplicación:',
'upload file:': 'suba archivo:',
'versioning': 'versiones',
'view': 'vista',
'views': 'vistas',
'web2py Recent Tweets': 'Tweets Recientes de web2py',
'web2py is up to date': 'web2py está actualizado',
}

########NEW FILE########
__FILENAME__ = fr-ca
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"update" est une expression optionnelle comme "champ1=\'nouvellevaleur\'". Vous ne pouvez mettre à jour ou supprimer les résultats d\'un JOIN',
'%Y-%m-%d': '%Y-%m-%d',
'%Y-%m-%d %H:%M:%S': '%Y-%m-%d %H:%M:%S',
'%s rows deleted': '%s rangées supprimées',
'%s rows updated': '%s rangées mises à jour',
'About': 'À propos',
'Accept Disclaimer': 'Accept Disclaimer',
'Access Control': "Contrôle d'accès",
'Add': 'Add',
'Add Files': 'Add Files',
'Add files': 'Add files',
'Administrative interface': "Interface d'administration",
'Ajax Recipes': 'Recettes Ajax',
'Analyze the received material, your work is fundamental in uncovering the truth': 'Analyze the received material, your work is fundamental in uncovering the truth',
'Are you sure you want to delete this object?': 'Êtes-vous sûr de vouloir supprimer cet objet?',
'Ask useful details to the whistleblower thru the comment box': 'Ask useful details to the whistleblower thru the comment box',
'Authentication': 'Authentification',
'Available databases and tables': 'Bases de données et tables disponibles',
'Bouquet': 'Bouquet',
'Buy this book': 'Acheter ce livre',
'Cancel upload': 'Cancel upload',
'Cannot be empty': 'Ne peut pas être vide',
'Check to delete': 'Cliquez pour supprimer',
'Check to delete:': 'Cliquez pour supprimer:',
'Client IP': 'IP client',
'Comments': 'Comments',
'Community': 'Communauté',
'Complete Download': 'Complete Download',
'Config': 'Config',
'Controller': 'Contrôleur',
'Copyright': "Droit d'auteur",
'Current request': 'Demande actuelle',
'Current response': 'Réponse actuelle',
'Current session': 'Session en cours',
'DB Model': 'Modèle DB',
'Database': 'Base de données',
'Delete Files': 'Delete Files',
'Delete:': 'Supprimer:',
'Demo': 'Démo',
'Deployment Recipes': 'Recettes de déploiement ',
'Description': 'Descriptif',
'Documentation': 'Documentation',
'Done': 'Done',
'Download': 'Téléchargement',
'Downloads': 'Downloads',
'E-mail': 'Courriel',
'Edit': 'Éditer',
'Edit This App': 'Modifier cette application',
'Edit current record': "Modifier l'enregistrement courant",
'Encrypted ZIP': 'Encrypted ZIP',
'Error: only ten digits are accepted as receipt': 'Error: only ten digits are accepted as receipt',
'Error: you puts more than 10 digits': 'Error: you puts more than 10 digits',
'Errors': 'Erreurs',
'FAQ': 'faq',
'Finish': 'Finish',
'First name': 'Prénom',
'Forms and Validators': 'Formulaires et Validateurs',
'Forward to another receiver group': 'Forward to another receiver group',
'Free Applications': 'Applications gratuites',
'Function disabled': 'Fonction désactivée',
'Globalview': 'Globalview',
'Group %(group_id)s created': '%(group_id)s groupe créé',
'Group ID': 'Groupe ID',
'Group uniquely assigned to user %(id)s': "Groupe unique attribué à l'utilisateur %(id)s",
'Groups': 'Groupes',
'Hello World': 'Bonjour le monde',
'Home': 'Accueil',
'I want delete this tip-off and all the others derived from the same material': 'I want delete this tip-off and all the others derived from the same material',
'I want delete this tulip and all the tulips derived from the same material': 'I want delete this tulip and all the tulips derived from the same material',
'ID': 'ID',
'Import/Export': 'Importer/Exporter',
'Incomplete configuration': 'Incomplete configuration',
'Index': 'Index',
'Internal State': 'État interne',
'Introduction': 'Présentation',
'Invalid Query': 'Requête Invalide',
'Invalid email': 'Courriel invalide',
"It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.": "It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.",
'Language': 'Language',
'Last name': 'Nom',
'Layout': 'Mise en page',
'Layouts': 'layouts',
'Live chat': 'Clavardage en direct',
'Logged in': 'Connecté',
'Login': 'Connectez-vous',
'Logout': 'Logout',
'Lost Password': 'Mot de passe perdu',
'Main Menu': 'Menu principal',
'Material': 'Material',
'Material description': 'Material description',
'Material has not been processed yet': 'Material has not been processed yet',
'Menu Model': 'Menu modèle',
'Name': 'Nom',
'New Record': 'Nouvel enregistrement',
'Next': 'Next',
'No comments': 'No comments',
'No databases in this application': "Cette application n'a pas de bases de données",
'Node View': 'Node View',
'Not spread this link. It is intended be for your eyes only': 'Not spread this link. It is intended be for your eyes only',
'Online examples': 'Exemples en ligne',
'Origin': 'Origine',
'Other Recipes': 'Autres recettes',
'Overview': 'Présentation',
'PGP Encrypted ZIP': 'PGP Encrypted ZIP',
'Password': 'Mot de passe',
"Password fields don't match": 'Les mots de passe ne correspondent pas',
'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)': 'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)',
'Plugins': 'Plugiciels',
'Powered by': 'Alimenté par',
'Preface': 'Préface',
'Preferences': 'Preferences',
'Previous': 'Previous',
'Python': 'Python',
'Query:': 'Requête:',
'Quick Examples': 'Examples Rapides',
'Readme': 'Lisez-moi',
'Receiver': 'Receiver',
'Receivers': 'Receivers',
'Recipes': 'Recettes',
'Record %(id)s created': 'Record %(id)s created',
'Record %(id)s updated': 'Record %(id)s updated',
'Record Created': 'Record Created',
'Record ID': "ID d'enregistrement",
'Record Updated': 'Record Updated',
'Redirecting to Hidden Serivice in': 'Redirecting to Hidden Serivice in',
'Register': "S'inscrire",
'Registration key': "Clé d'enregistrement",
'Registration successful': 'Inscription réussie',
'Remember me (for 30 days)': 'Se souvenir de moi (pendant 30 jours)',
'Request reset password': 'Demande de réinitialiser le mot clé',
'Reset Password key': 'Réinitialiser le mot clé',
'Resources': 'Ressources',
'Role': 'Rôle',
'Rows in table': 'Lignes du tableau',
'Rows selected': 'Lignes sélectionnées',
'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Select Group:': 'Select Group:',
'Semantic': 'Sémantique',
'Services': 'Services',
'Stats': 'Stats',
'Step': 'Step',
'Stylesheet': 'Feuille de style',
'Submission': 'Submission',
'Submission Interface': 'Submission Interface',
'Submission Receipt': 'Submission Receipt',
'Submission interface': 'Submission interface',
'Submission status': 'Submission status',
'Submit': 'Soumettre',
'Submit material': 'Submit material',
'Submit receipt': 'Submit receipt',
'Support': 'Soutien',
'Sure you want to delete this object?': 'Êtes-vous sûr de vouloir supprimer cet objet?',
'Table name': 'Nom du tableau',
'Tags': 'Tags',
'Targets': 'Targets',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'La "query" est une condition comme "db.table1.champ1==\'valeur\'". Quelque chose comme "db.table1.champ1==db.table2.champ2" résulte en un JOIN SQL.',
'The Core': 'Le noyau',
'The Views': 'Les Vues',
'The output of the file is a dictionary that was rendered by the view': 'La sortie de ce fichier est un dictionnaire qui été restitué par la vue',
'This App': 'Cette Appli',
'This is a copy of the scaffolding application': "Ceci est une copie de l'application échafaudage",
'This is a number you should write down to keep track of your submission': 'This is a number you should write down to keep track of your submission',
'This is the material submitted by the whistleblower for your revision. You are invited to': 'This is the material submitted by the whistleblower for your revision. You are invited to',
'Timestamp': 'Horodatage',
'Tip-off': 'Tip-off',
'Tip-off access statistics': 'Tip-off access statistics',
'Tip-off removed and all relatives': 'Tip-off removed and all relatives',
'Tulip': 'Tulip',
'Tulip Receipt': 'Tulip Receipt',
'Tulip access statistics': 'Tulip access statistics',
'Tulip removed and all relatives': 'Tulip removed and all relatives',
'Tulips': 'Tulips',
'Twitter': 'Twitter',
'Update:': 'Mise à jour:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Employez (...)&(...) pour AND, (...)|(...) pour OR, and ~(...)  pour NOT pour construire des requêtes plus complexes.',
'User %(id)s Logged-in': 'Utilisateur %(id)s connecté',
'User %(id)s Registered': 'Utilisateur %(id)s enregistré',
'User ID': 'ID utilisateur',
'User Voice': 'User Voice',
'Username': 'Username',
'Verify Password': 'Vérifiez le mot de passe',
'Videos': 'Vidéos',
'View': 'Présentation',
'Views': 'Views',
'Warning': 'Warning',
'Web2py': 'Web2py',
'Welcome': 'Bienvenu',
'Welcome %s': 'Bienvenue %s',
'Welcome back Whistleblower: this TULIP interface is unique for you.': 'Welcome back Whistleblower: this TULIP interface is unique for you.',
'Welcome back Whistleblower: this interface is unique for you.': 'Welcome back Whistleblower: this interface is unique for you.',
'Welcome to web2py': 'Bienvenue à web2py',
'Which called the function': 'Qui a appelé la fonction',
'Whistleblower': 'Whistleblower',
'You are also able to use your Whistleblower receipt from the first page.': 'You are also able to use your Whistleblower receipt from the first page.',
'You are successfully running web2py': 'Vous roulez avec succès web2py',
'You can modify this application and adapt it to your needs': "Vous pouvez modifier cette application et l'adapter à vos besoins",
'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.': 'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.',
'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.': 'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.',
'You visited the url': "Vous avez visité l'URL",
"You've received a": "You've received a",
"You've received a Tulip...": "You've received a Tulip...",
'Your submission': 'Your submission',
'Your tip-off': 'Your tip-off',
'ZIP': 'ZIP',
'about': 'à propos',
'appadmin is disabled because insecure channel': "appadmin est désactivée parce que le canal n'est pas sécurisé",
'cache': 'cache',
'change password': 'changer le mot de passe',
'check back later': 'check back later',
'customize me!': 'personnalisez-moi!',
'data uploaded': 'données téléchargées',
'database': 'base de données',
'database %s select': 'base de données %s select',
'db': 'db',
'design': 'design',
'done!': 'fait!',
'edit profile': 'modifier le profil',
'enter an integer between %(min)g and %(max)g': 'entrer un entier compris entre %(min)g et %(max)g',
'export as csv file': 'exporter sous forme de fichier csv',
'insert new': 'insérer un nouveau',
'insert new %s': 'insérer un nouveau %s',
'invalid receipt: Tip-off not found': 'invalid receipt: Tip-off not found',
'invalid receipt: Tulip not found': 'invalid receipt: Tulip not found',
'invalid request': 'requête invalide',
'located in the file': 'se trouvant dans le fichier',
'login': 'connectez-vous',
'logout': 'déconnectez-vous',
'lost password': 'mot de passe perdu',
'lost password?': 'mot de passe perdu?',
'must accept disclaimer': 'must accept disclaimer',
'new record inserted': 'nouvel enregistrement inséré',
'next 100 rows': '100 prochaines lignes',
'or import from csv file': "ou importer d'un fichier CSV",
'password': 'mot de passe',
'please input your password again': "S'il vous plaît entrer votre mot de passe",
'powered by': 'powered by',
'previous 100 rows': '100 lignes précédentes',
'profile': 'profile',
'record': 'enregistrement',
'record does not exist': "l'archive n'existe pas",
'record id': "id d'enregistrement",
'register': "s'inscrire",
'seconds': 'seconds',
'selected': 'sélectionné',
'state': 'état',
'table': 'tableau',
'tulips': 'tulips',
'unable to parse csv file': "incapable d'analyser le fichier cvs",
'value already in database or empty': 'valeur déjà dans la base ou vide',
}

########NEW FILE########
__FILENAME__ = fr-fr
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"update" est une expression optionnelle comme "champ1=\'nouvellevaleur\'". Vous ne pouvez mettre à jour ou supprimer les résultats d\'un JOIN',
'%Y-%m-%d': '%Y-%m-%d',
'%Y-%m-%d %H:%M:%S': '%Y-%m-%d %H:%M:%S',
'%s rows deleted': '%s rangées supprimées',
'%s rows updated': '%s rangées mises à jour',
'About': 'À propos',
'Accept Disclaimer': 'Accept Disclaimer',
'Access Control': "Contrôle d'accès",
'Add': 'Add',
'Add Files': 'Add Files',
'Add files': 'Add files',
'Administrative interface': "Interface d'administration",
'Ajax Recipes': 'Recettes Ajax',
'Analyze the received material, your work is fundamental in uncovering the truth': 'Analyze the received material, your work is fundamental in uncovering the truth',
'Are you sure you want to delete this object?': 'Êtes-vous sûr de vouloir supprimer cet objet?',
'Ask useful details to the whistleblower thru the comment box': 'Ask useful details to the whistleblower thru the comment box',
'Authentication': 'Authentification',
'Available databases and tables': 'Bases de données et tables disponibles',
'Bouquet': 'Bouquet',
'Buy this book': 'Acheter ce livre',
'Cancel upload': 'Cancel upload',
'Cannot be empty': 'Ne peut pas être vide',
'Check to delete': 'Cliquez pour supprimer',
'Check to delete:': 'Cliquez pour supprimer:',
'Client IP': 'IP client',
'Comments': 'Comments',
'Community': 'Communauté',
'Complete Download': 'Complete Download',
'Config': 'Config',
'Controller': 'Contrôleur',
'Copyright': 'Copyright',
'Current request': 'Demande actuelle',
'Current response': 'Réponse actuelle',
'Current session': 'Session en cours',
'DB Model': 'Modèle DB',
'Database': 'Base de données',
'Delete Files': 'Delete Files',
'Delete:': 'Supprimer:',
'Demo': 'Démo',
'Deployment Recipes': 'Recettes de déploiement',
'Description': 'Description',
'Documentation': 'Documentation',
'Done': 'Done',
'Download': 'Téléchargement',
'Downloads': 'Downloads',
'E-mail': 'E-mail',
'Edit': 'Éditer',
'Edit This App': 'Modifier cette application',
'Edit current record': "Modifier l'enregistrement courant",
'Encrypted ZIP': 'Encrypted ZIP',
'Error: only ten digits are accepted as receipt': 'Error: only ten digits are accepted as receipt',
'Error: you puts more than 10 digits': 'Error: you puts more than 10 digits',
'Errors': 'Erreurs',
'FAQ': 'FAQ',
'Finish': 'Finish',
'First name': 'Prénom',
'Forms and Validators': 'Formulaires et Validateurs',
'Forward to another receiver group': 'Forward to another receiver group',
'Free Applications': 'Applications gratuites',
'Function disabled': 'Fonction désactivée',
'Globalview': 'Globalview',
'Group ID': 'Groupe ID',
'Groups': 'Groups',
'Hello World': 'Bonjour le monde',
'Home': 'Accueil',
'I want delete this tip-off and all the others derived from the same material': 'I want delete this tip-off and all the others derived from the same material',
'I want delete this tulip and all the tulips derived from the same material': 'I want delete this tulip and all the tulips derived from the same material',
'ID': 'ID',
'Import/Export': 'Importer/Exporter',
'Incomplete configuration': 'Incomplete configuration',
'Index': 'Index',
'Internal State': 'État interne',
'Introduction': 'Introduction',
'Invalid Query': 'Requête Invalide',
'Invalid email': 'E-mail invalide',
"It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.": "It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.",
'Language': 'Language',
'Last name': 'Nom',
'Layout': 'Mise en page',
'Layouts': 'Layouts',
'Live chat': 'Chat live',
'Login': 'Connectez-vous',
'Logout': 'Logout',
'Lost Password': 'Mot de passe perdu',
'Main Menu': 'Menu principal',
'Material': 'Material',
'Material description': 'Material description',
'Material has not been processed yet': 'Material has not been processed yet',
'Menu Model': 'Menu modèle',
'Name': 'Nom',
'New Record': 'Nouvel enregistrement',
'Next': 'Next',
'No comments': 'No comments',
'No databases in this application': "Cette application n'a pas de bases de données",
'Node View': 'Node View',
'Not spread this link. It is intended be for your eyes only': 'Not spread this link. It is intended be for your eyes only',
'Online examples': 'Exemples en ligne',
'Origin': 'Origine',
'Other Recipes': 'Autres recettes',
'Overview': 'Présentation',
'PGP Encrypted ZIP': 'PGP Encrypted ZIP',
'Password': 'Mot de passe',
"Password fields don't match": 'Les mots de passe ne correspondent pas',
'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)': 'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)',
'Plugins': 'Plugiciels',
'Powered by': 'Alimenté par',
'Preface': 'Préface',
'Preferences': 'Preferences',
'Previous': 'Previous',
'Python': 'Python',
'Query:': 'Requête:',
'Quick Examples': 'Examples Rapides',
'Readme': 'Lisez-moi',
'Receiver': 'Receiver',
'Receivers': 'Receivers',
'Recipes': 'Recettes',
'Record ID': "ID d'enregistrement",
'Redirecting to Hidden Serivice in': 'Redirecting to Hidden Serivice in',
'Register': "S'inscrire",
'Registration key': "Clé d'enregistrement",
'Remember me (for 30 days)': 'Se souvenir de moi (pendant 30 jours)',
'Request reset password': 'Demande de réinitialiser le mot clé',
'Reset Password key': 'Réinitialiser le mot clé',
'Resources': 'Ressources',
'Role': 'Rôle',
'Rows in table': 'Lignes du tableau',
'Rows selected': 'Lignes sélectionnées',
'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Select Group:': 'Select Group:',
'Semantic': 'Sémantique',
'Services': 'Services',
'Stats': 'Stats',
'Step': 'Step',
'Stylesheet': 'Feuille de style',
'Submission': 'Submission',
'Submission Interface': 'Submission Interface',
'Submission Receipt': 'Submission Receipt',
'Submission interface': 'Submission interface',
'Submission status': 'Submission status',
'Submit': 'Soumettre',
'Submit material': 'Submit material',
'Submit receipt': 'Submit receipt',
'Support': 'Support',
'Sure you want to delete this object?': 'Êtes-vous sûr de vouloir supprimer cet objet?',
'Table name': 'Nom du tableau',
'Tags': 'Tags',
'Targets': 'Targets',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'La "query" est une condition comme "db.table1.champ1==\'valeur\'". Quelque chose comme "db.table1.champ1==db.table2.champ2" résulte en un JOIN SQL.',
'The Core': 'Le noyau',
'The Views': 'Les Vues',
'The output of the file is a dictionary that was rendered by the view': 'La sortie de ce fichier est un dictionnaire qui été restitué par la vue',
'This App': 'Cette Appli',
'This is a copy of the scaffolding application': "Ceci est une copie de l'application échafaudage",
'This is a number you should write down to keep track of your submission': 'This is a number you should write down to keep track of your submission',
'This is the material submitted by the whistleblower for your revision. You are invited to': 'This is the material submitted by the whistleblower for your revision. You are invited to',
'Timestamp': 'Horodatage',
'Tip-off': 'Tip-off',
'Tip-off access statistics': 'Tip-off access statistics',
'Tip-off removed and all relatives': 'Tip-off removed and all relatives',
'Tulip': 'Tulip',
'Tulip Receipt': 'Tulip Receipt',
'Tulip access statistics': 'Tulip access statistics',
'Tulip removed and all relatives': 'Tulip removed and all relatives',
'Tulips': 'Tulips',
'Twitter': 'Twitter',
'Update:': 'Mise à jour:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Employez (...)&(...) pour AND, (...)|(...) pour OR, and ~(...)  pour NOT pour construire des requêtes plus complexes.',
'User %(id)s Logged-in': 'Utilisateur %(id)s connecté',
'User %(id)s Registered': 'Utilisateur %(id)s enregistré',
'User ID': 'ID utilisateur',
'User Voice': 'User Voice',
'Username': 'Username',
'Verify Password': 'Vérifiez le mot de passe',
'Videos': 'Vidéos',
'View': 'Présentation',
'Views': 'Views',
'Warning': 'Warning',
'Web2py': 'Web2py',
'Welcome': 'Bienvenu',
'Welcome %s': 'Bienvenue %s',
'Welcome back Whistleblower: this TULIP interface is unique for you.': 'Welcome back Whistleblower: this TULIP interface is unique for you.',
'Welcome back Whistleblower: this interface is unique for you.': 'Welcome back Whistleblower: this interface is unique for you.',
'Welcome to web2py': 'Bienvenue à web2py',
'Which called the function': 'Qui a appelé la fonction',
'Whistleblower': 'Whistleblower',
'You are also able to use your Whistleblower receipt from the first page.': 'You are also able to use your Whistleblower receipt from the first page.',
'You are successfully running web2py': 'Vous roulez avec succès web2py',
'You can modify this application and adapt it to your needs': "Vous pouvez modifier cette application et l'adapter à vos besoins",
'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.': 'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.',
'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.': 'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.',
'You visited the url': "Vous avez visité l'URL",
"You've received a": "You've received a",
"You've received a Tulip...": "You've received a Tulip...",
'Your submission': 'Your submission',
'Your tip-off': 'Your tip-off',
'ZIP': 'ZIP',
'appadmin is disabled because insecure channel': "appadmin est désactivée parce que le canal n'est pas sécurisé",
'cache': 'cache',
'change password': 'changer le mot de passe',
'check back later': 'check back later',
'customize me!': 'personnalisez-moi!',
'data uploaded': 'données téléchargées',
'database': 'base de données',
'database %s select': 'base de données %s select',
'db': 'db',
'design': 'design',
'done!': 'fait!',
'edit profile': 'modifier le profil',
'enter an integer between %(min)g and %(max)g': 'enter an integer between %(min)g and %(max)g',
'export as csv file': 'exporter sous forme de fichier csv',
'insert new': 'insérer un nouveau',
'insert new %s': 'insérer un nouveau %s',
'invalid receipt: Tip-off not found': 'invalid receipt: Tip-off not found',
'invalid receipt: Tulip not found': 'invalid receipt: Tulip not found',
'invalid request': 'requête invalide',
'located in the file': 'se trouvant dans le fichier',
'login': 'connectez-vous',
'logout': 'déconnectez-vous',
'lost password': 'mot de passe perdu',
'lost password?': 'mot de passe perdu?',
'must accept disclaimer': 'must accept disclaimer',
'new record inserted': 'nouvel enregistrement inséré',
'next 100 rows': '100 prochaines lignes',
'or import from csv file': "ou importer d'un fichier CSV",
'powered by': 'powered by',
'previous 100 rows': '100 lignes précédentes',
'record': 'enregistrement',
'record does not exist': "l'archive n'existe pas",
'record id': "id d'enregistrement",
'register': "s'inscrire",
'seconds': 'seconds',
'selected': 'sélectionné',
'state': 'état',
'table': 'tableau',
'tulips': 'tulips',
'unable to parse csv file': "incapable d'analyser le fichier cvs",
}

########NEW FILE########
__FILENAME__ = hi-hi
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN',
'%Y-%m-%d': '%Y-%m-%d',
'%Y-%m-%d %H:%M:%S': '%Y-%m-%d %H:%M:%S',
'%s rows deleted': '%s पंक्तियाँ मिटाएँ',
'%s rows updated': '%s पंक्तियाँ  अद्यतन',
'Accept Disclaimer': 'Accept Disclaimer',
'Add': 'Add',
'Add Files': 'Add Files',
'Add files': 'Add files',
'Administrative interface': 'प्रशासनिक इंटरफेस के लिए यहाँ क्लिक करें',
'Analyze the received material, your work is fundamental in uncovering the truth': 'Analyze the received material, your work is fundamental in uncovering the truth',
'Are you sure you want to delete this object?': 'Are you sure you want to delete this object?',
'Ask useful details to the whistleblower thru the comment box': 'Ask useful details to the whistleblower thru the comment box',
'Available databases and tables': 'उपलब्ध  डेटाबेस और तालिका',
'Bouquet': 'Bouquet',
'Cancel upload': 'Cancel upload',
'Cannot be empty': 'खाली नहीं हो सकता',
'Change Password': 'पासवर्ड बदलें',
'Check to delete': 'हटाने के लिए चुनें',
'Comments': 'Comments',
'Complete Download': 'Complete Download',
'Config': 'Config',
'Controller': 'Controller',
'Copyright': 'Copyright',
'Current request': 'वर्तमान अनुरोध',
'Current response': 'वर्तमान प्रतिक्रिया',
'Current session': 'वर्तमान सेशन',
'DB Model': 'DB Model',
'Database': 'Database',
'Delete Files': 'Delete Files',
'Delete:': 'मिटाना:',
'Done': 'Done',
'Download': 'Download',
'Downloads': 'Downloads',
'Edit': 'Edit',
'Edit Profile': 'प्रोफ़ाइल संपादित करें',
'Edit This App': 'Edit This App',
'Edit current record': 'वर्तमान रेकॉर्ड संपादित करें ',
'Encrypted ZIP': 'Encrypted ZIP',
'Error: only ten digits are accepted as receipt': 'Error: only ten digits are accepted as receipt',
'Error: you puts more than 10 digits': 'Error: you puts more than 10 digits',
'Finish': 'Finish',
'Forward to another receiver group': 'Forward to another receiver group',
'Globalview': 'Globalview',
'Groups': 'Groups',
'Hello World': 'Hello World',
'Hello from MyApp': 'Hello from MyApp',
'I want delete this tip-off and all the others derived from the same material': 'I want delete this tip-off and all the others derived from the same material',
'I want delete this tulip and all the tulips derived from the same material': 'I want delete this tulip and all the tulips derived from the same material',
'ID': 'ID',
'Import/Export': 'आयात / निर्यात',
'Incomplete configuration': 'Incomplete configuration',
'Index': 'Index',
'Internal State': 'आंतरिक  स्थिति',
'Invalid Query': 'अमान्य  प्रश्न',
"It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.": "It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.",
'Language': 'Language',
'Layout': 'Layout',
'Login': 'लॉग इन',
'Logout': 'लॉग आउट',
'Lost Password': 'पासवर्ड खो गया',
'Main Menu': 'Main Menu',
'Material': 'Material',
'Material description': 'Material description',
'Material has not been processed yet': 'Material has not been processed yet',
'Menu Model': 'Menu Model',
'New Record': 'नया रेकॉर्ड',
'Next': 'Next',
'No comments': 'No comments',
'No databases in this application': 'इस  अनुप्रयोग में कोई डेटाबेस नहीं हैं',
'Node View': 'Node View',
'Not spread this link. It is intended be for your eyes only': 'Not spread this link. It is intended be for your eyes only',
'Online examples': 'ऑनलाइन उदाहरण के लिए यहाँ क्लिक करें',
'PGP Encrypted ZIP': 'PGP Encrypted ZIP',
'Password': 'Password',
'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)': 'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)',
'Powered by': 'Powered by',
'Preferences': 'Preferences',
'Previous': 'Previous',
'Query:': 'प्रश्न:',
'Receiver': 'Receiver',
'Receivers': 'Receivers',
'Redirecting to Hidden Serivice in': 'Redirecting to Hidden Serivice in',
'Register': 'पंजीकृत (रजिस्टर) करना ',
'Rows in table': 'तालिका में पंक्तियाँ ',
'Rows selected': 'चयनित (चुने गये) पंक्तियाँ ',
'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Select Group:': 'Select Group:',
'Stats': 'Stats',
'Step': 'Step',
'Stylesheet': 'Stylesheet',
'Submission': 'Submission',
'Submission Interface': 'Submission Interface',
'Submission Receipt': 'Submission Receipt',
'Submission interface': 'Submission interface',
'Submission status': 'Submission status',
'Submit material': 'Submit material',
'Submit receipt': 'Submit receipt',
'Sure you want to delete this object?': 'सुनिश्चित हैं कि आप इस वस्तु को हटाना चाहते हैं?',
'Tags': 'Tags',
'Targets': 'Targets',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.',
'This is a number you should write down to keep track of your submission': 'This is a number you should write down to keep track of your submission',
'This is the material submitted by the whistleblower for your revision. You are invited to': 'This is the material submitted by the whistleblower for your revision. You are invited to',
'Tip-off': 'Tip-off',
'Tip-off access statistics': 'Tip-off access statistics',
'Tip-off removed and all relatives': 'Tip-off removed and all relatives',
'Tulip': 'Tulip',
'Tulip Receipt': 'Tulip Receipt',
'Tulip access statistics': 'Tulip access statistics',
'Tulip removed and all relatives': 'Tulip removed and all relatives',
'Tulips': 'Tulips',
'Update:': 'अद्यतन करना:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.',
'Username': 'Username',
'View': 'View',
'Views': 'Views',
'Warning': 'Warning',
'Welcome %s': 'Welcome %s',
'Welcome back Whistleblower: this TULIP interface is unique for you.': 'Welcome back Whistleblower: this TULIP interface is unique for you.',
'Welcome back Whistleblower: this interface is unique for you.': 'Welcome back Whistleblower: this interface is unique for you.',
'Welcome to web2py': 'वेब२पाइ (web2py)  में आपका स्वागत है',
'Whistleblower': 'Whistleblower',
'You are also able to use your Whistleblower receipt from the first page.': 'You are also able to use your Whistleblower receipt from the first page.',
'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.': 'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.',
'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.': 'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.',
"You've received a": "You've received a",
"You've received a Tulip...": "You've received a Tulip...",
'Your submission': 'Your submission',
'Your tip-off': 'Your tip-off',
'ZIP': 'ZIP',
'appadmin is disabled because insecure channel': 'अप आडमिन (appadmin) अक्षम है क्योंकि असुरक्षित चैनल',
'cache': 'cache',
'change password': 'change password',
'check back later': 'check back later',
'customize me!': 'मुझे अनुकूलित (कस्टमाइज़) करें!',
'data uploaded': 'डाटा अपलोड सम्पन्न ',
'database': 'डेटाबेस',
'database %s select': 'डेटाबेस  %s चुनी हुई',
'db': 'db',
'design': 'रचना करें',
'done!': 'हो गया!',
'edit profile': 'edit profile',
'export as csv file': 'csv फ़ाइल के रूप में निर्यात',
'insert new': 'नया डालें',
'insert new %s': 'नया   %s  डालें',
'invalid receipt: Tip-off not found': 'invalid receipt: Tip-off not found',
'invalid receipt: Tulip not found': 'invalid receipt: Tulip not found',
'invalid request': 'अवैध अनुरोध',
'login': 'login',
'logout': 'logout',
'must accept disclaimer': 'must accept disclaimer',
'new record inserted': 'नया रेकॉर्ड डाला',
'next 100 rows': 'अगले 100 पंक्तियाँ',
'or import from csv file': 'या  csv फ़ाइल से आयात',
'powered by': 'powered by',
'previous 100 rows': 'पिछले 100 पंक्तियाँ',
'record': 'record',
'record does not exist': 'रिकॉर्ड मौजूद नहीं है',
'record id': 'रिकॉर्ड पहचानकर्ता (आईडी)',
'register': 'register',
'seconds': 'seconds',
'selected': 'चुना हुआ',
'state': 'स्थिति',
'table': 'तालिका',
'tulips': 'tulips',
'unable to parse csv file': 'csv फ़ाइल पार्स करने में असमर्थ',
}

########NEW FILE########
__FILENAME__ = hu-hu
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN',
'%Y-%m-%d': '%Y.%m.%d.',
'%Y-%m-%d %H:%M:%S': '%Y.%m.%d. %H:%M:%S',
'%s rows deleted': '%s sorok törlődtek',
'%s rows updated': '%s sorok frissítődtek',
'Accept Disclaimer': 'Accept Disclaimer',
'Add': 'Add',
'Add Files': 'Add Files',
'Add files': 'Add files',
'Administrative interface': 'az adminisztrációs felületért kattints ide',
'Analyze the received material, your work is fundamental in uncovering the truth': 'Analyze the received material, your work is fundamental in uncovering the truth',
'Are you sure you want to delete this object?': 'Are you sure you want to delete this object?',
'Ask useful details to the whistleblower thru the comment box': 'Ask useful details to the whistleblower thru the comment box',
'Available databases and tables': 'Elérhető adatbázisok és táblák',
'Bouquet': 'Bouquet',
'Cancel upload': 'Cancel upload',
'Cannot be empty': 'Nem lehet üres',
'Check to delete': 'Törléshez válaszd ki',
'Client IP': 'Client IP',
'Comments': 'Comments',
'Complete Download': 'Complete Download',
'Config': 'Config',
'Controller': 'Controller',
'Copyright': 'Copyright',
'Current request': 'Jelenlegi lekérdezés',
'Current response': 'Jelenlegi válasz',
'Current session': 'Jelenlegi folyamat',
'DB Model': 'DB Model',
'Database': 'Adatbázis',
'Delete Files': 'Delete Files',
'Delete:': 'Töröl:',
'Description': 'Description',
'Done': 'Done',
'Download': 'Download',
'Downloads': 'Downloads',
'E-mail': 'E-mail',
'Edit': 'Szerkeszt',
'Edit This App': 'Alkalmazást szerkeszt',
'Edit current record': 'Aktuális bejegyzés szerkesztése',
'Encrypted ZIP': 'Encrypted ZIP',
'Error: only ten digits are accepted as receipt': 'Error: only ten digits are accepted as receipt',
'Error: you puts more than 10 digits': 'Error: you puts more than 10 digits',
'Finish': 'Finish',
'First name': 'First name',
'Forward to another receiver group': 'Forward to another receiver group',
'Globalview': 'Globalview',
'Group ID': 'Group ID',
'Groups': 'Groups',
'Hello World': 'Hello Világ',
'I want delete this tip-off and all the others derived from the same material': 'I want delete this tip-off and all the others derived from the same material',
'I want delete this tulip and all the tulips derived from the same material': 'I want delete this tulip and all the tulips derived from the same material',
'ID': 'ID',
'Import/Export': 'Import/Export',
'Incomplete configuration': 'Incomplete configuration',
'Index': 'Index',
'Internal State': 'Internal State',
'Invalid Query': 'Hibás lekérdezés',
'Invalid email': 'Invalid email',
"It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.": "It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.",
'Language': 'Language',
'Last name': 'Last name',
'Layout': 'Szerkezet',
'Logout': 'Logout',
'Main Menu': 'Főmenü',
'Material': 'Material',
'Material description': 'Material description',
'Material has not been processed yet': 'Material has not been processed yet',
'Menu Model': 'Menü model',
'Name': 'Name',
'New Record': 'Új bejegyzés',
'Next': 'Next',
'No comments': 'No comments',
'No databases in this application': 'Nincs adatbázis ebben az alkalmazásban',
'Node View': 'Node View',
'Not spread this link. It is intended be for your eyes only': 'Not spread this link. It is intended be for your eyes only',
'Online examples': 'online példákért kattints ide',
'Origin': 'Origin',
'PGP Encrypted ZIP': 'PGP Encrypted ZIP',
'Password': 'Password',
'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)': 'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)',
'Powered by': 'Powered by',
'Preferences': 'Preferences',
'Previous': 'Previous',
'Query:': 'Lekérdezés:',
'Receiver': 'Receiver',
'Receivers': 'Receivers',
'Record ID': 'Record ID',
'Redirecting to Hidden Serivice in': 'Redirecting to Hidden Serivice in',
'Registration key': 'Registration key',
'Reset Password key': 'Reset Password key',
'Role': 'Role',
'Rows in table': 'Sorok a táblában',
'Rows selected': 'Kiválasztott sorok',
'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Select Group:': 'Select Group:',
'Stats': 'Stats',
'Step': 'Step',
'Stylesheet': 'Stylesheet',
'Submission': 'Submission',
'Submission Interface': 'Submission Interface',
'Submission Receipt': 'Submission Receipt',
'Submission interface': 'Submission interface',
'Submission status': 'Submission status',
'Submit material': 'Submit material',
'Submit receipt': 'Submit receipt',
'Sure you want to delete this object?': 'Biztos törli ezt az objektumot?',
'Table name': 'Table name',
'Tags': 'Tags',
'Targets': 'Targets',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.',
'This is a number you should write down to keep track of your submission': 'This is a number you should write down to keep track of your submission',
'This is the material submitted by the whistleblower for your revision. You are invited to': 'This is the material submitted by the whistleblower for your revision. You are invited to',
'Timestamp': 'Timestamp',
'Tip-off': 'Tip-off',
'Tip-off access statistics': 'Tip-off access statistics',
'Tip-off removed and all relatives': 'Tip-off removed and all relatives',
'Tulip': 'Tulip',
'Tulip Receipt': 'Tulip Receipt',
'Tulip access statistics': 'Tulip access statistics',
'Tulip removed and all relatives': 'Tulip removed and all relatives',
'Tulips': 'Tulips',
'Update:': 'Frissít:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.',
'User ID': 'User ID',
'Username': 'Username',
'View': 'Nézet',
'Views': 'Views',
'Warning': 'Warning',
'Welcome %s': 'Welcome %s',
'Welcome back Whistleblower: this TULIP interface is unique for you.': 'Welcome back Whistleblower: this TULIP interface is unique for you.',
'Welcome back Whistleblower: this interface is unique for you.': 'Welcome back Whistleblower: this interface is unique for you.',
'Welcome to web2py': 'Isten hozott a web2py-ban',
'Whistleblower': 'Whistleblower',
'You are also able to use your Whistleblower receipt from the first page.': 'You are also able to use your Whistleblower receipt from the first page.',
'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.': 'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.',
'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.': 'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.',
"You've received a": "You've received a",
"You've received a Tulip...": "You've received a Tulip...",
'Your submission': 'Your submission',
'Your tip-off': 'Your tip-off',
'ZIP': 'ZIP',
'appadmin is disabled because insecure channel': 'az appadmin a biztonságtalan csatorna miatt letiltva',
'cache': 'gyorsítótár',
'change password': 'jelszó megváltoztatása',
'check back later': 'check back later',
'customize me!': 'változtass meg!',
'data uploaded': 'adat feltöltve',
'database': 'adatbázis',
'database %s select': 'adatbázis %s kiválasztás',
'db': 'db',
'design': 'design',
'done!': 'kész!',
'edit profile': 'profil szerkesztése',
'export as csv file': 'exportál csv fájlba',
'insert new': 'új beillesztése',
'insert new %s': 'új beillesztése %s',
'invalid receipt: Tip-off not found': 'invalid receipt: Tip-off not found',
'invalid receipt: Tulip not found': 'invalid receipt: Tulip not found',
'invalid request': 'hibás kérés',
'login': 'belép',
'logout': 'kilép',
'lost password': 'elveszett jelszó',
'must accept disclaimer': 'must accept disclaimer',
'new record inserted': 'új bejegyzés felvéve',
'next 100 rows': 'következő 100 sor',
'or import from csv file': 'vagy betöltés csv fájlból',
'powered by': 'powered by',
'previous 100 rows': 'előző 100 sor',
'record': 'bejegyzés',
'record does not exist': 'bejegyzés nem létezik',
'record id': 'bejegyzés id',
'register': 'regisztráció',
'seconds': 'seconds',
'selected': 'kiválasztott',
'state': 'állapot',
'table': 'tábla',
'tulips': 'tulips',
'unable to parse csv file': 'nem lehet a csv fájlt beolvasni',
}

########NEW FILE########
__FILENAME__ = hu
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN',
'%Y-%m-%d': '%Y.%m.%d.',
'%Y-%m-%d %H:%M:%S': '%Y.%m.%d. %H:%M:%S',
'%s rows deleted': '%s sorok törlődtek',
'%s rows updated': '%s sorok frissítődtek',
'Accept Disclaimer': 'Accept Disclaimer',
'Add': 'Add',
'Add Files': 'Add Files',
'Add files': 'Add files',
'Administrative interface': 'az adminisztrációs felületért kattints ide',
'Analyze the received material, your work is fundamental in uncovering the truth': 'Analyze the received material, your work is fundamental in uncovering the truth',
'Are you sure you want to delete this object?': 'Are you sure you want to delete this object?',
'Ask useful details to the whistleblower thru the comment box': 'Ask useful details to the whistleblower thru the comment box',
'Available databases and tables': 'Elérhető adatbázisok és táblák',
'Bouquet': 'Bouquet',
'Cancel upload': 'Cancel upload',
'Cannot be empty': 'Nem lehet üres',
'Check to delete': 'Törléshez válaszd ki',
'Client IP': 'Client IP',
'Comments': 'Comments',
'Complete Download': 'Complete Download',
'Config': 'Config',
'Controller': 'Controller',
'Copyright': 'Copyright',
'Current request': 'Jelenlegi lekérdezés',
'Current response': 'Jelenlegi válasz',
'Current session': 'Jelenlegi folyamat',
'DB Model': 'DB Model',
'Database': 'Adatbázis',
'Delete Files': 'Delete Files',
'Delete:': 'Töröl:',
'Description': 'Description',
'Done': 'Done',
'Download': 'Download',
'Downloads': 'Downloads',
'E-mail': 'E-mail',
'Edit': 'Szerkeszt',
'Edit This App': 'Alkalmazást szerkeszt',
'Edit current record': 'Aktuális bejegyzés szerkesztése',
'Encrypted ZIP': 'Encrypted ZIP',
'Error: only ten digits are accepted as receipt': 'Error: only ten digits are accepted as receipt',
'Error: you puts more than 10 digits': 'Error: you puts more than 10 digits',
'Finish': 'Finish',
'First name': 'First name',
'Forward to another receiver group': 'Forward to another receiver group',
'Globalview': 'Globalview',
'Group ID': 'Group ID',
'Groups': 'Groups',
'Hello World': 'Hello Világ',
'I want delete this tip-off and all the others derived from the same material': 'I want delete this tip-off and all the others derived from the same material',
'I want delete this tulip and all the tulips derived from the same material': 'I want delete this tulip and all the tulips derived from the same material',
'ID': 'ID',
'Import/Export': 'Import/Export',
'Incomplete configuration': 'Incomplete configuration',
'Index': 'Index',
'Internal State': 'Internal State',
'Invalid Query': 'Hibás lekérdezés',
'Invalid email': 'Invalid email',
"It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.": "It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.",
'Language': 'Language',
'Last name': 'Last name',
'Layout': 'Szerkezet',
'Logout': 'Logout',
'Main Menu': 'Főmenü',
'Material': 'Material',
'Material description': 'Material description',
'Material has not been processed yet': 'Material has not been processed yet',
'Menu Model': 'Menü model',
'Name': 'Name',
'New Record': 'Új bejegyzés',
'Next': 'Next',
'No comments': 'No comments',
'No databases in this application': 'Nincs adatbázis ebben az alkalmazásban',
'Node View': 'Node View',
'Not spread this link. It is intended be for your eyes only': 'Not spread this link. It is intended be for your eyes only',
'Online examples': 'online példákért kattints ide',
'Origin': 'Origin',
'PGP Encrypted ZIP': 'PGP Encrypted ZIP',
'Password': 'Password',
'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)': 'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)',
'Powered by': 'Powered by',
'Preferences': 'Preferences',
'Previous': 'Previous',
'Query:': 'Lekérdezés:',
'Receiver': 'Receiver',
'Receivers': 'Receivers',
'Record ID': 'Record ID',
'Redirecting to Hidden Serivice in': 'Redirecting to Hidden Serivice in',
'Registration key': 'Registration key',
'Reset Password key': 'Reset Password key',
'Role': 'Role',
'Rows in table': 'Sorok a táblában',
'Rows selected': 'Kiválasztott sorok',
'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Select Group:': 'Select Group:',
'Stats': 'Stats',
'Step': 'Step',
'Stylesheet': 'Stylesheet',
'Submission': 'Submission',
'Submission Interface': 'Submission Interface',
'Submission Receipt': 'Submission Receipt',
'Submission interface': 'Submission interface',
'Submission status': 'Submission status',
'Submit material': 'Submit material',
'Submit receipt': 'Submit receipt',
'Sure you want to delete this object?': 'Biztos törli ezt az objektumot?',
'Table name': 'Table name',
'Tags': 'Tags',
'Targets': 'Targets',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.',
'This is a number you should write down to keep track of your submission': 'This is a number you should write down to keep track of your submission',
'This is the material submitted by the whistleblower for your revision. You are invited to': 'This is the material submitted by the whistleblower for your revision. You are invited to',
'Timestamp': 'Timestamp',
'Tip-off': 'Tip-off',
'Tip-off access statistics': 'Tip-off access statistics',
'Tip-off removed and all relatives': 'Tip-off removed and all relatives',
'Tulip': 'Tulip',
'Tulip Receipt': 'Tulip Receipt',
'Tulip access statistics': 'Tulip access statistics',
'Tulip removed and all relatives': 'Tulip removed and all relatives',
'Tulips': 'Tulips',
'Update:': 'Frissít:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.',
'User ID': 'User ID',
'Username': 'Username',
'View': 'Nézet',
'Views': 'Views',
'Warning': 'Warning',
'Welcome %s': 'Welcome %s',
'Welcome back Whistleblower: this TULIP interface is unique for you.': 'Welcome back Whistleblower: this TULIP interface is unique for you.',
'Welcome back Whistleblower: this interface is unique for you.': 'Welcome back Whistleblower: this interface is unique for you.',
'Welcome to web2py': 'Isten hozott a web2py-ban',
'Whistleblower': 'Whistleblower',
'You are also able to use your Whistleblower receipt from the first page.': 'You are also able to use your Whistleblower receipt from the first page.',
'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.': 'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.',
'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.': 'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.',
"You've received a": "You've received a",
"You've received a Tulip...": "You've received a Tulip...",
'Your submission': 'Your submission',
'Your tip-off': 'Your tip-off',
'ZIP': 'ZIP',
'appadmin is disabled because insecure channel': 'az appadmin a biztonságtalan csatorna miatt letiltva',
'cache': 'gyorsítótár',
'change password': 'jelszó megváltoztatása',
'check back later': 'check back later',
'customize me!': 'változtass meg!',
'data uploaded': 'adat feltöltve',
'database': 'adatbázis',
'database %s select': 'adatbázis %s kiválasztás',
'db': 'db',
'design': 'design',
'done!': 'kész!',
'edit profile': 'profil szerkesztése',
'export as csv file': 'exportál csv fájlba',
'insert new': 'új beillesztése',
'insert new %s': 'új beillesztése %s',
'invalid receipt: Tip-off not found': 'invalid receipt: Tip-off not found',
'invalid receipt: Tulip not found': 'invalid receipt: Tulip not found',
'invalid request': 'hibás kérés',
'login': 'belép',
'logout': 'kilép',
'lost password': 'elveszett jelszó',
'must accept disclaimer': 'must accept disclaimer',
'new record inserted': 'új bejegyzés felvéve',
'next 100 rows': 'következő 100 sor',
'or import from csv file': 'vagy betöltés csv fájlból',
'powered by': 'powered by',
'previous 100 rows': 'előző 100 sor',
'record': 'bejegyzés',
'record does not exist': 'bejegyzés nem létezik',
'record id': 'bejegyzés id',
'register': 'regisztráció',
'seconds': 'seconds',
'selected': 'kiválasztott',
'state': 'állapot',
'table': 'tábla',
'tulips': 'tulips',
'unable to parse csv file': 'nem lehet a csv fájlt beolvasni',
}

########NEW FILE########
__FILENAME__ = it-it
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"update" è un\'espressione opzionale come "campo1=\'nuovo valore\'". Non si può fare "update" o "delete" dei risultati di un JOIN ',
'%Y-%m-%d': '%d/%m/%Y',
'%Y-%m-%d %H:%M:%S': '%d/%m/%Y %H:%M:%S',
'%s rows deleted': '%s righe ("record") cancellate',
'%s rows updated': '%s righe ("record") modificate',
'< Back': '< Back',
'Accept Disclaimer': 'Accept Disclaimer',
'Add': 'Add',
'Add Files': 'Add Files',
'Add files': 'Add files',
'Administrative interface': 'Interfaccia amministrativa',
'Analyze the received material, your work is fundamental in uncovering the truth': 'Analyze the received material, your work is fundamental in uncovering the truth',
'Are you sure you want to delete this object?': 'Are you sure you want to delete this object?',
'Ask useful details to the whistleblower thru the comment box': 'Ask useful details to the whistleblower thru the comment box',
'Available databases and tables': 'Database e tabelle disponibili',
'Bouquet': 'Bouquet',
'Cancel upload': 'Cancel upload',
'Cannot be empty': 'Non può essere vuoto',
'Check to delete': 'Seleziona per cancellare',
'Check to delete:': 'Check to delete:',
'Client IP': 'Client IP',
'Comments': 'Comments',
'Complete Download': 'Complete Download',
'Config': 'Config',
'Controller': 'Controller',
'Copyright': 'Copyright',
'Current request': 'Richiesta (request) corrente',
'Current response': 'Risposta (response) corrente',
'Current session': 'Sessione (session) corrente',
'DB Model': 'Modello di DB',
'Database': 'Database',
'Delete Files': 'Delete Files',
'Delete:': 'Cancella:',
'Description': 'Descrizione',
'Documentation': 'Documentazione',
'Done': 'Done',
'Download': 'Download',
'Downloads': 'Downloads',
'E-mail': 'E-mail',
'Edit': 'Modifica',
'Edit This App': 'Modifica questa applicazione',
'Edit current record': 'Modifica record corrente',
'Encrypted ZIP': 'Encrypted ZIP',
'Error: only ten digits are accepted as receipt': 'Error: only ten digits are accepted as receipt',
'Error: you puts more than 10 digits': 'Error: you puts more than 10 digits',
'Finish': 'Finish',
'First name': 'Nome',
'Forward to another receiver group': 'Forward to another receiver group',
'Giornale1': 'Giornale1',
'Giornale2': 'Giornale2',
'Global View': 'Global View',
'Globalview': 'Globalview',
'Group %(group_id)s created': 'Group %(group_id)s created',
'Group ID': 'ID Gruppo',
'Group uniquely assigned to user %(id)s': 'Group uniquely assigned to user %(id)s',
'Groups': 'Groups',
'Gruppo1': 'Gruppo1',
'Hello World': 'Salve Mondo',
'Hello World in a flash!': 'Salve Mondo in un flash!',
'I want delete this tip-off and all the others derived from the same material': 'I want delete this tip-off and all the others derived from the same material',
'I want delete this tulip and all the tulips derived from the same material': 'I want delete this tulip and all the tulips derived from the same material',
'ID': 'ID',
'Import/Export': 'Importa/Esporta',
'Incomplete configuration': 'Incomplete configuration',
'Index': 'Indice',
'Internal State': 'Stato interno',
'Invalid Query': 'Richiesta (query) non valida',
'Invalid email': 'Email non valida',
'Invalid login': 'Invalid login',
"It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.": "It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.",
'Language': 'Language',
'Last name': 'Cognome',
'Layout': 'Layout',
'Logged in': 'Logged in',
'Logged out': 'Logged out',
'Login': 'Login',
'Logout': 'Logout',
'Main Menu': 'Menu principale',
'Material': 'Material',
'Material description': 'Material description',
'Material has not been processed yet': 'Material has not been processed yet',
'Menu Model': 'Menu Modelli',
'Name': 'Nome',
'New Record': 'Nuovo elemento (record)',
'Next': 'Next',
'Next >': 'Next >',
'No comments': 'No comments',
'No databases in this application': 'Nessun database presente in questa applicazione',
'Node View': 'Node View',
'Not spread this link. It is intended be for your eyes only': 'Not spread this link. It is intended be for your eyes only',
'Online examples': 'Vedere gli esempi',
'Only': 'Only',
'Origin': 'Origine',
'PGP Encrypted ZIP': 'PGP Encrypted ZIP',
'Password': 'Password',
"Password fields don't match": "Password fields don't match",
'Please accept the disclaimer': 'Please accept the disclaimer',
'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)': 'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)',
'Polizia': 'Polizia',
'Powered by': 'Powered by',
'Preferences': 'Preferences',
'Previous': 'Previous',
'Query:': 'Richiesta (query):',
'Receiver': 'Receiver',
'Receivers': 'Receivers',
'Record ID': 'Record ID',
'Redirecting to Hidden Serivice in': 'Redirecting to Hidden Serivice in',
'Register': 'Register',
'Registration identifier': 'Registration identifier',
'Registration key': 'Chiave di Registazione',
'Remember me (for 30 days)': 'Remember me (for 30 days)',
'Reset Password key': 'Resetta chiave Password ',
'Role': 'Ruolo',
'Rows in table': 'Righe nella tabella',
'Rows selected': 'Righe selezionate',
'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Select Group:': 'Select Group:',
'Start upload': 'Start upload',
'Stats': 'Stats',
'Step': 'Step',
'Stylesheet': 'Foglio di stile (stylesheet)',
'Submission': 'Submission',
'Submission Interface': 'Interfaccia di Submission',
'Submission Receipt': 'Submission Receipt',
'Submission interface': 'Interfaccia di invio',
'Submission status': 'Submission status',
'Submit material': 'Submit material',
'Submit receipt': 'Submit receipt',
'Sure you want to delete this object?': 'Vuoi veramente cancellare questo oggetto?',
'Table name': 'Nome tabella',
'Tags': 'Tags',
'Targets': 'Targets',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'La richiesta (query) è una condizione come ad esempio  "db.tabella1.campo1==\'valore\'". Una condizione come "db.tabella1.campo1==db.tabella2.campo2" produce un "JOIN" SQL.',
'The files are being uploaded, if you leave now the upload will be cancelled.': 'The files are being uploaded, if you leave now the upload will be cancelled.',
'The output of the file is a dictionary that was rendered by the view': 'L\'output del file è un "dictionary" che è stato visualizzato dalla vista',
'This is a copy of the scaffolding application': "Questa è una copia dell'applicazione di base (scaffold)",
'This is a number you should write down to keep track of your submission': 'This is a number you should write down to keep track of your submission',
'This is the material submitted by the whistleblower for your revision. You are invited to': 'This is the material submitted by the whistleblower for your revision. You are invited to',
'Timestamp': 'Ora (timestamp)',
'Tip-off': 'Tip-off',
'Tip-off access statistics': 'Tip-off access statistics',
'Tip-off removed and all relatives': 'Tip-off removed and all relatives',
'Tulip': 'Tulip',
'Tulip Receipt': 'Tulip Receipt',
'Tulip access statistics': 'Tulip access statistics',
'Tulip removed and all relatives': 'Tulip removed and all relatives',
'Tulips': 'Tulips',
'Update:': 'Aggiorna:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Per costruire richieste (query) più complesse si usano (...)&(...) come "e" (AND), (...)|(...) come "o" (OR), e ~(...) come negazione (NOT).',
'User %(id)s Logged-in': 'User %(id)s Logged-in',
'User %(id)s Logged-out': 'User %(id)s Logged-out',
'User ID': 'ID Utente',
'Username': 'Username',
'View': 'Vista',
'Views': 'Views',
'Warning': 'Warning',
'Welcome %s': 'Benvenuto %s',
'Welcome back Whistleblower: this TULIP interface is unique for you.': 'Welcome back Whistleblower: this TULIP interface is unique for you.',
'Welcome back Whistleblower: this interface is unique for you.': 'Welcome back Whistleblower: this interface is unique for you.',
'Welcome to web2py': 'Benvenuto su web2py',
'Which called the function': 'che ha chiamato la funzione',
'Whistleblower': 'Whistleblower',
'You are also able to use your Whistleblower receipt from the first page.': 'You are also able to use your Whistleblower receipt from the first page.',
'You are successfully running web2py': 'Stai eseguendo web2py con successo',
'You can modify this application and adapt it to your needs': 'Puoi modificare questa applicazione adattandola alle tue necessità',
'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.': 'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.',
'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.': 'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.',
'You visited the url': "Hai visitato l'URL",
"You've received a": "You've received a",
"You've received a Tulip...": "You've received a Tulip...",
'Your submission': 'Your submission',
'Your tip-off': 'Your tip-off',
'ZIP': 'ZIP',
'appadmin is disabled because insecure channel': 'Amministrazione (appadmin) disabilitata: comunicazione non sicura',
'are allowed.': 'are allowed.',
'cache': 'cache',
'change password': 'Cambia password',
'check back later': 'check back later',
'customize me!': 'Personalizzami!',
'data uploaded': 'dati caricati',
'database': 'database',
'database %s select': 'database %s select',
'db': 'db',
'design': 'progetta',
'done!': 'fatto!',
'edit profile': 'modifica profilo',
'enter a valid email address': 'enter a valid email address',
'enter an integer between %(min)g and %(max)g': 'enter an integer between %(min)g and %(max)g',
'enter from %(min)g to %(max)g characters': 'enter from %(min)g to %(max)g characters',
'export as csv file': 'esporta come file CSV',
'giornale,media': 'giornale,media',
'giornale,media,milano': 'giornale,media,milano',
'has invalid extension.': 'has invalid extension.',
'hello world': 'salve mondo',
'insert new': 'inserisci nuovo',
'insert new %s': 'inserisci nuovo %s',
'invalid receipt: Tip-off not found': 'invalid receipt: Tip-off not found',
'invalid receipt: Tulip not found': 'invalid receipt: Tulip not found',
'invalid request': 'richiesta non valida',
'is empty, please select files again without it.': 'is empty, please select files again without it.',
'is too large, maximum file size is': 'is too large, maximum file size is',
'is too small, minimum file size is': 'is too small, minimum file size is',
'located in the file': 'presente nel file',
'login': 'accesso',
'logout': 'uscita',
'lol,gruppo': 'lol,gruppo',
'lost password?': 'dimenticato la password?',
'must accept disclaimer': 'must accept disclaimer',
'new record inserted': 'nuovo record inserito',
'next 100 rows': 'prossime 100 righe',
'not authorized': 'non autorizzato',
'or import from csv file': 'oppure importa da file CSV',
'please input your password again': 'please input your password again',
'police, state': 'police, state',
'polizia, ordine': 'polizia, ordine',
'powered by': 'powered by',
'previous 100 rows': '100 righe precedenti',
'record': 'record',
'record does not exist': 'il record non esiste',
'record id': 'record id',
'register': 'registrazione',
'seconds': 'seconds',
'selected': 'selezionato',
'state': 'stato',
'table': 'tabella',
'tulips': 'tulips',
'unable to parse csv file': 'non riesco a decodificare questo file CSV',
}

########NEW FILE########
__FILENAME__ = it
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"update" è un\'espressione opzionale come "campo1=\'nuovo valore\'". Non si può fare "update" o "delete" dei risultati di un JOIN ',
'%Y-%m-%d': '%d/%m/%Y',
'%Y-%m-%d %H:%M:%S': '%d/%m/%Y %H:%M:%S',
'%s rows deleted': '%s righe ("record") cancellate',
'%s rows updated': '%s righe ("record") modificate',
'Accept': 'Accept',
'Accept Disclaimer': 'Accept Disclaimer',
'Add': 'Add',
'Add Files': 'Add Files',
'Add files': 'Add files',
'Administrative interface': 'Interfaccia amministrativa',
'Analyze the received material, your work is fundamental in uncovering the truth': 'Analyze the received material, your work is fundamental in uncovering the truth',
'Are you sure you want to delete this object?': 'Are you sure you want to delete this object?',
'Ask useful details to the whistleblower thru the comment box': 'Ask useful details to the whistleblower thru the comment box',
'Available databases and tables': 'Database e tabelle disponibili',
'Bouquet': 'Bouquet',
'Cancel upload': 'Cancel upload',
'Cannot be empty': 'Non può essere vuoto',
'Change password': 'Change password',
'Check to delete': 'Seleziona per cancellare',
'Check to delete:': 'Check to delete:',
'Client IP': 'Client IP',
'Comments': 'Comments',
'Complete Download': 'Complete Download',
'Config': 'Config',
'Controller': 'Controller',
'Copyright': 'Copyright',
'Current request': 'Richiesta (request) corrente',
'Current response': 'Risposta (response) corrente',
'Current session': 'Sessione (session) corrente',
'DB Model': 'Modello di DB',
'Database': 'Database',
'Delete Files': 'Delete Files',
'Delete:': 'Cancella:',
'Description': 'Descrizione',
'Documentation': 'Documentazione',
'Done': 'Done',
'Download': 'Download',
'Downloads': 'Downloads',
'E-mail': 'E-mail',
'Edit': 'Modifica',
'Edit This App': 'Modifica questa applicazione',
'Edit current record': 'Modifica record corrente',
'Email non valida': 'Email non valida',
'Encrypted ZIP': 'Encrypted ZIP',
'Error: only ten digits are accepted as receipt': 'Error: only ten digits are accepted as receipt',
'Error: you puts more than 10 digits': 'Error: you puts more than 10 digits',
'Finish': 'Finish',
'First name': 'Nome',
'Forward to another receiver group': 'Forward to another receiver group',
'Globalview': 'Globalview',
'Group %(group_id)s created': 'Group %(group_id)s created',
'Group ID': 'ID Gruppo',
'Group uniquely assigned to user %(id)s': 'Group uniquely assigned to user %(id)s',
'Groups': 'Groups',
'Hello World': 'Salve Mondo',
'Hello World in a flash!': 'Salve Mondo in un flash!',
'I want delete this tip-off and all the others derived from the same material': 'I want delete this tip-off and all the others derived from the same material',
'I want delete this tulip and all the tulips derived from the same material': 'I want delete this tulip and all the tulips derived from the same material',
'ID': 'ID',
'Import/Export': 'Importa/Esporta',
'Incomplete configuration': 'Incomplete configuration',
'Index': 'Indice',
'Internal State': 'Stato interno',
'Invalid Query': 'Richiesta (query) non valida',
'Invalid email': 'Email non valida',
'Invalid login': 'Invalid login',
'Invalid password': 'Invalid password',
"It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.": "It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.",
'Language': 'Language',
'Last name': 'Cognome',
'Layout': 'Layout',
'Logged in': 'Logged in',
'Logged out': 'Logged out',
'Login': 'Login',
'Logout': 'Logout',
'Main Menu': 'Menu principale',
'Material': 'Material',
'Material description': 'Material description',
'Material has not been processed yet': 'Material has not been processed yet',
'Menu Model': 'Menu Modelli',
'Name': 'Nome',
'New Record': 'Nuovo elemento (record)',
'New password': 'New password',
'Next': 'Next',
'No comments': 'No comments',
'No databases in this application': 'Nessun database presente in questa applicazione',
'Node View': 'Node View',
'Not spread this link. It is intended be for your eyes only': 'Not spread this link. It is intended be for your eyes only',
'Old password': 'Old password',
'Online examples': 'Vedere gli esempi',
'Origin': 'Origine',
'PGP Encrypted ZIP': 'PGP Encrypted ZIP',
'Password': 'Password',
"Password fields don't match": "Password fields don't match",
'Please read the disclaimer': 'Please read the disclaimer',
'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)': 'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)',
'Powered by': 'Powered by',
'Preferences': 'Preferences',
'Previous': 'Previous',
'Profile': 'Profile',
'Profile updated': 'Profile updated',
'Query:': 'Richiesta (query):',
'Receiver': 'Receiver',
'Receivers': 'Receivers',
'Record ID': 'Record ID',
'Redirecting to Hidden Serivice in': 'Redirecting to Hidden Serivice in',
'Register': 'Register',
'Registration identifier': 'Registration identifier',
'Registration key': 'Chiave di Registazione',
'Registration successful': 'Registration successful',
'Remember me (for 30 days)': 'Remember me (for 30 days)',
'Request reset password': 'Request reset password',
'Reset Password key': 'Resetta chiave Password ',
'Role': 'Ruolo',
'Rows in table': 'Righe nella tabella',
'Rows selected': 'Righe selezionate',
'Save profile': 'Save profile',
'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Select Group:': 'Select Group:',
'Stats': 'Stats',
'Step': 'Step',
'Stylesheet': 'Foglio di stile (stylesheet)',
'Submission': 'Submission',
'Submission Interface': 'Interfacccia di submission',
'Submission Receipt': 'Submission Receipt',
'Submission interface': 'Interfacccia di submission',
'Submission status': 'Submission status',
'Submit material': 'Submit material',
'Submit receipt': 'Submit receipt',
'Sure you want to delete this object?': 'Vuoi veramente cancellare questo oggetto?',
'Table name': 'Nome tabella',
'Tags': 'Tags',
'Targets': 'Targets',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'La richiesta (query) è una condizione come ad esempio  "db.tabella1.campo1==\'valore\'". Una condizione come "db.tabella1.campo1==db.tabella2.campo2" produce un "JOIN" SQL.',
'The output of the file is a dictionary that was rendered by the view': 'L\'output del file è un "dictionary" che è stato visualizzato dalla vista',
'This is a copy of the scaffolding application': "Questa è una copia dell'applicazione di base (scaffold)",
'This is a number you should write down to keep track of your submission': 'This is a number you should write down to keep track of your submission',
'This is the material submitted by the whistleblower for your revision. You are invited to': 'This is the material submitted by the whistleblower for your revision. You are invited to',
'Timestamp': 'Ora (timestamp)',
'Tip-off': 'Tip-off',
'Tip-off access statistics': 'Tip-off access statistics',
'Tip-off removed and all relatives': 'Tip-off removed and all relatives',
'Tulip': 'Tulip',
'Tulip Receipt': 'Tulip Receipt',
'Tulip access statistics': 'Tulip access statistics',
'Tulip removed and all relatives': 'Tulip removed and all relatives',
'Tulips': 'Tulips',
'Update:': 'Aggiorna:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Per costruire richieste (query) più complesse si usano (...)&(...) come "e" (AND), (...)|(...) come "o" (OR), e ~(...) come negazione (NOT).',
'User %(id)s Logged-in': 'User %(id)s Logged-in',
'User %(id)s Logged-out': 'User %(id)s Logged-out',
'User %(id)s Password changed': 'User %(id)s Password changed',
'User %(id)s Password reset': 'User %(id)s Password reset',
'User %(id)s Profile updated': 'User %(id)s Profile updated',
'User %(id)s Registered': 'User %(id)s Registered',
'User ID': 'ID Utente',
'Username': 'Username',
'Verify Password': 'Verify Password',
'View': 'Vista',
'Views': 'Views',
'Warning': 'Warning',
'Welcome': 'Welcome',
'Welcome %s': 'Benvenuto %s',
'Welcome back Whistleblower: this TULIP interface is unique for you.': 'Welcome back Whistleblower: this TULIP interface is unique for you.',
'Welcome back Whistleblower: this interface is unique for you.': 'Welcome back Whistleblower: this interface is unique for you.',
'Welcome to web2py': 'Benvenuto su web2py',
'Which called the function': 'che ha chiamato la funzione',
'Whistleblower': 'Whistleblower',
'You are also able to use your Whistleblower receipt from the first page.': 'You are also able to use your Whistleblower receipt from the first page.',
'You are successfully running web2py': 'Stai eseguendo web2py con successo',
'You can modify this application and adapt it to your needs': 'Puoi modificare questa applicazione adattandola alle tue necessità',
'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.': 'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.',
'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.': 'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.',
'You visited the url': "Hai visitato l'URL",
"You've received a": "You've received a",
"You've received a Tulip...": "You've received a Tulip...",
'Your submission': 'Your submission',
'Your tip-off': 'Your tip-off',
'ZIP': 'ZIP',
'appadmin is disabled because insecure channel': 'Amministrazione (appadmin) disabilitata: comunicazione non sicura',
'cache': 'cache',
'change password': 'Cambia password',
'check back later': 'check back later',
'customize me!': 'Personalizzami!',
'data uploaded': 'dati caricati',
'database': 'database',
'database %s select': 'database %s select',
'db': 'db',
'design': 'progetta',
'done!': 'fatto!',
'edit profile': 'modifica profilo',
'enter a value': 'enter a value',
'enter an integer between %(min)g and %(max)g': 'enter an integer between %(min)g and %(max)g',
'enter from %(min)g to %(max)g characters': 'enter from %(min)g to %(max)g characters',
'export as csv file': 'esporta come file CSV',
'hello world': 'salve mondo',
'insert new': 'inserisci nuovo',
'insert new %s': 'inserisci nuovo %s',
'invalid receipt: Tip-off not found': 'invalid receipt: Tip-off not found',
'invalid receipt: Tulip not found': 'invalid receipt: Tulip not found',
'invalid request': 'richiesta non valida',
'located in the file': 'presente nel file',
'login': 'accesso',
'logout': 'uscita',
'lost password?': 'dimenticato la password?',
'must accept disclaimer': 'must accept disclaimer',
'new record inserted': 'nuovo record inserito',
'next 100 rows': 'prossime 100 righe',
'not authorized': 'non autorizzato',
'or import from csv file': 'oppure importa da file CSV',
'password': 'password',
'please input your password again': 'please input your password again',
'powered by': 'powered by',
'previous 100 rows': '100 righe precedenti',
'profile': 'profile',
'record': 'record',
'record does not exist': 'il record non esiste',
'record id': 'record id',
'register': 'registrazione',
'seconds': 'seconds',
'selected': 'selezionato',
'state': 'stato',
'table': 'tabella',
'tulips': 'tulips',
'unable to parse csv file': 'non riesco a decodificare questo file CSV',
'value already in database or empty': 'value already in database or empty',
}

########NEW FILE########
__FILENAME__ = pl-pl
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"Uaktualnij" jest dodatkowym wyrażeniem postaci "pole1=\'nowawartość\'". Nie możesz uaktualnić lub usunąć wyników z JOIN:',
'%Y-%m-%d': '%Y-%m-%d',
'%Y-%m-%d %H:%M:%S': '%Y-%m-%d %H:%M:%S',
'%s rows deleted': 'Wierszy usuniętych: %s',
'%s rows updated': 'Wierszy uaktualnionych: %s',
'Accept Disclaimer': 'Accept Disclaimer',
'Add': 'Add',
'Add Files': 'Add Files',
'Add files': 'Add files',
'Administrative interface': 'Kliknij aby przejść do panelu administracyjnego',
'Analyze the received material, your work is fundamental in uncovering the truth': 'Analyze the received material, your work is fundamental in uncovering the truth',
'Are you sure you want to delete this object?': 'Are you sure you want to delete this object?',
'Ask useful details to the whistleblower thru the comment box': 'Ask useful details to the whistleblower thru the comment box',
'Available databases and tables': 'Dostępne bazy danych i tabele',
'Bouquet': 'Bouquet',
'Cancel upload': 'Cancel upload',
'Cannot be empty': 'Nie może być puste',
'Change Password': 'Change Password',
'Check to delete': 'Zaznacz aby usunąć',
'Comments': 'Comments',
'Complete Download': 'Complete Download',
'Config': 'Config',
'Controller': 'Controller',
'Copyright': 'Copyright',
'Current request': 'Aktualne żądanie',
'Current response': 'Aktualna odpowiedź',
'Current session': 'Aktualna sesja',
'DB Model': 'DB Model',
'Database': 'Database',
'Delete Files': 'Delete Files',
'Delete:': 'Usuń:',
'Done': 'Done',
'Download': 'Download',
'Downloads': 'Downloads',
'Edit': 'Edit',
'Edit Profile': 'Edit Profile',
'Edit This App': 'Edit This App',
'Edit current record': 'Edytuj aktualny rekord',
'Encrypted ZIP': 'Encrypted ZIP',
'Error: only ten digits are accepted as receipt': 'Error: only ten digits are accepted as receipt',
'Error: you puts more than 10 digits': 'Error: you puts more than 10 digits',
'Finish': 'Finish',
'Forward to another receiver group': 'Forward to another receiver group',
'Globalview': 'Globalview',
'Groups': 'Groups',
'Hello World': 'Witaj Świecie',
'I want delete this tip-off and all the others derived from the same material': 'I want delete this tip-off and all the others derived from the same material',
'I want delete this tulip and all the tulips derived from the same material': 'I want delete this tulip and all the tulips derived from the same material',
'ID': 'ID',
'Import/Export': 'Importuj/eksportuj',
'Incomplete configuration': 'Incomplete configuration',
'Index': 'Index',
'Internal State': 'Stan wewnętrzny',
'Invalid Query': 'Błędne zapytanie',
"It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.": "It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.",
'Language': 'Language',
'Layout': 'Layout',
'Login': 'Zaloguj',
'Logout': 'Logout',
'Lost Password': 'Przypomnij hasło',
'Main Menu': 'Main Menu',
'Material': 'Material',
'Material description': 'Material description',
'Material has not been processed yet': 'Material has not been processed yet',
'Menu Model': 'Menu Model',
'New Record': 'Nowy rekord',
'Next': 'Next',
'No comments': 'No comments',
'No databases in this application': 'Brak baz danych w tej aplikacji',
'Node View': 'Node View',
'Not spread this link. It is intended be for your eyes only': 'Not spread this link. It is intended be for your eyes only',
'Online examples': 'Kliknij aby przejść do interaktywnych przykładów',
'PGP Encrypted ZIP': 'PGP Encrypted ZIP',
'Password': 'Password',
'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)': 'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)',
'Powered by': 'Powered by',
'Preferences': 'Preferences',
'Previous': 'Previous',
'Query:': 'Zapytanie:',
'Receiver': 'Receiver',
'Receivers': 'Receivers',
'Redirecting to Hidden Serivice in': 'Redirecting to Hidden Serivice in',
'Register': 'Zarejestruj',
'Rows in table': 'Wiersze w tabeli',
'Rows selected': 'Wybrane wiersze',
'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Select Group:': 'Select Group:',
'Stats': 'Stats',
'Step': 'Step',
'Stylesheet': 'Stylesheet',
'Submission': 'Submission',
'Submission Interface': 'Submission Interface',
'Submission Receipt': 'Submission Receipt',
'Submission interface': 'Submission interface',
'Submission status': 'Submission status',
'Submit material': 'Submit material',
'Submit receipt': 'Submit receipt',
'Sure you want to delete this object?': 'Czy na pewno chcesz usunąć ten obiekt?',
'Tags': 'Tags',
'Targets': 'Targets',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': '"Zapytanie" jest warunkiem postaci "db.tabela1.pole1==\'wartość\'". Takie coś jak "db.tabela1.pole1==db.tabela2.pole2" oznacza SQL JOIN.',
'This is a number you should write down to keep track of your submission': 'This is a number you should write down to keep track of your submission',
'This is the material submitted by the whistleblower for your revision. You are invited to': 'This is the material submitted by the whistleblower for your revision. You are invited to',
'Tip-off': 'Tip-off',
'Tip-off access statistics': 'Tip-off access statistics',
'Tip-off removed and all relatives': 'Tip-off removed and all relatives',
'Tulip': 'Tulip',
'Tulip Receipt': 'Tulip Receipt',
'Tulip access statistics': 'Tulip access statistics',
'Tulip removed and all relatives': 'Tulip removed and all relatives',
'Tulips': 'Tulips',
'Update:': 'Uaktualnij:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Użyj (...)&(...) jako AND, (...)|(...) jako OR oraz ~(...)  jako NOT do tworzenia bardziej skomplikowanych zapytań.',
'Username': 'Username',
'View': 'View',
'Views': 'Views',
'Warning': 'Warning',
'Welcome %s': 'Welcome %s',
'Welcome back Whistleblower: this TULIP interface is unique for you.': 'Welcome back Whistleblower: this TULIP interface is unique for you.',
'Welcome back Whistleblower: this interface is unique for you.': 'Welcome back Whistleblower: this interface is unique for you.',
'Welcome to web2py': 'Witaj w web2py',
'Whistleblower': 'Whistleblower',
'You are also able to use your Whistleblower receipt from the first page.': 'You are also able to use your Whistleblower receipt from the first page.',
'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.': 'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.',
'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.': 'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.',
"You've received a": "You've received a",
"You've received a Tulip...": "You've received a Tulip...",
'Your submission': 'Your submission',
'Your tip-off': 'Your tip-off',
'ZIP': 'ZIP',
'appadmin is disabled because insecure channel': 'appadmin is disabled because insecure channel',
'cache': 'cache',
'change password': 'change password',
'check back later': 'check back later',
'customize me!': 'dostosuj mnie!',
'data uploaded': 'dane wysłane',
'database': 'baza danych',
'database %s select': 'wybór z bazy danych %s',
'db': 'baza danych',
'design': 'projektuj',
'done!': 'zrobione!',
'edit profile': 'edit profile',
'export as csv file': 'eksportuj jako plik csv',
'insert new': 'wstaw nowy rekord tabeli',
'insert new %s': 'wstaw nowy rekord do tabeli %s',
'invalid receipt: Tip-off not found': 'invalid receipt: Tip-off not found',
'invalid receipt: Tulip not found': 'invalid receipt: Tulip not found',
'invalid request': 'Błędne żądanie',
'login': 'login',
'logout': 'logout',
'must accept disclaimer': 'must accept disclaimer',
'new record inserted': 'nowy rekord został wstawiony',
'next 100 rows': 'następne 100 wierszy',
'or import from csv file': 'lub zaimportuj z pliku csv',
'powered by': 'powered by',
'previous 100 rows': 'poprzednie 100 wierszy',
'record': 'record',
'record does not exist': 'rekord nie istnieje',
'record id': 'id rekordu',
'register': 'register',
'seconds': 'seconds',
'selected': 'wybranych',
'state': 'stan',
'table': 'tabela',
'tulips': 'tulips',
'unable to parse csv file': 'nie można sparsować pliku csv',
}

########NEW FILE########
__FILENAME__ = pl
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"Uaktualnij" jest dodatkowym wyrażeniem postaci "pole1=\'nowawartość\'". Nie możesz uaktualnić lub usunąć wyników z JOIN:',
'%Y-%m-%d': '%Y-%m-%d',
'%Y-%m-%d %H:%M:%S': '%Y-%m-%d %H:%M:%S',
'%s rows deleted': 'Wierszy usuniętych: %s',
'%s rows updated': 'Wierszy uaktualnionych: %s',
'Accept Disclaimer': 'Accept Disclaimer',
'Add': 'Add',
'Add Files': 'Add Files',
'Add files': 'Add files',
'Administrative interface': 'Kliknij aby przejść do panelu administracyjnego',
'Analyze the received material, your work is fundamental in uncovering the truth': 'Analyze the received material, your work is fundamental in uncovering the truth',
'Are you sure you want to delete this object?': 'Are you sure you want to delete this object?',
'Ask useful details to the whistleblower thru the comment box': 'Ask useful details to the whistleblower thru the comment box',
'Authentication': 'Uwierzytelnienie',
'Available databases and tables': 'Dostępne bazy danych i tabele',
'Bouquet': 'Bouquet',
'Cancel upload': 'Cancel upload',
'Cannot be empty': 'Nie może być puste',
'Change Password': 'Zmień hasło',
'Check to delete': 'Zaznacz aby usunąć',
'Check to delete:': 'Zaznacz aby usunąć:',
'Client IP': 'IP klienta',
'Comments': 'Comments',
'Complete Download': 'Complete Download',
'Config': 'Config',
'Controller': 'Kontroler',
'Copyright': 'Copyright',
'Current request': 'Aktualne żądanie',
'Current response': 'Aktualna odpowiedź',
'Current session': 'Aktualna sesja',
'DB Model': 'Model bazy danych',
'Database': 'Baza danych',
'Delete Files': 'Delete Files',
'Delete:': 'Usuń:',
'Description': 'Opis',
'Done': 'Done',
'Download': 'Download',
'Downloads': 'Downloads',
'E-mail': 'Adres e-mail',
'Edit': 'Edycja',
'Edit Profile': 'Edytuj profil',
'Edit This App': 'Edytuj tę aplikację',
'Edit current record': 'Edytuj obecny rekord',
'Encrypted ZIP': 'Encrypted ZIP',
'Error: only ten digits are accepted as receipt': 'Error: only ten digits are accepted as receipt',
'Error: you puts more than 10 digits': 'Error: you puts more than 10 digits',
'Finish': 'Finish',
'First name': 'Imię',
'Forward to another receiver group': 'Forward to another receiver group',
'Function disabled': 'Funkcja wyłączona',
'Globalview': 'Globalview',
'Group ID': 'ID grupy',
'Groups': 'Groups',
'Hello World': 'Witaj Świecie',
'I want delete this tip-off and all the others derived from the same material': 'I want delete this tip-off and all the others derived from the same material',
'I want delete this tulip and all the tulips derived from the same material': 'I want delete this tulip and all the tulips derived from the same material',
'ID': 'ID',
'Import/Export': 'Importuj/eksportuj',
'Incomplete configuration': 'Incomplete configuration',
'Index': 'Indeks',
'Internal State': 'Stan wewnętrzny',
'Invalid Query': 'Błędne zapytanie',
'Invalid email': 'Błędny adres email',
"It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.": "It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.",
'Language': 'Language',
'Last name': 'Nazwisko',
'Layout': 'Układ',
'Login': 'Zaloguj',
'Logout': 'Wyloguj',
'Lost Password': 'Przypomnij hasło',
'Main Menu': 'Menu główne',
'Material': 'Material',
'Material description': 'Material description',
'Material has not been processed yet': 'Material has not been processed yet',
'Menu Model': 'Model menu',
'Name': 'Nazwa',
'New Record': 'Nowy rekord',
'Next': 'Next',
'No comments': 'No comments',
'No databases in this application': 'Brak baz danych w tej aplikacji',
'Node View': 'Node View',
'Not spread this link. It is intended be for your eyes only': 'Not spread this link. It is intended be for your eyes only',
'Online examples': 'Kliknij aby przejść do interaktywnych przykładów',
'Origin': 'Źródło',
'PGP Encrypted ZIP': 'PGP Encrypted ZIP',
'Password': 'Hasło',
"Password fields don't match": 'Pola hasła nie są zgodne ze sobą',
'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)': 'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)',
'Powered by': 'Zasilane przez',
'Preferences': 'Preferences',
'Previous': 'Previous',
'Query:': 'Zapytanie:',
'Receiver': 'Receiver',
'Receivers': 'Receivers',
'Record ID': 'ID rekordu',
'Redirecting to Hidden Serivice in': 'Redirecting to Hidden Serivice in',
'Register': 'Zarejestruj',
'Registration key': 'Klucz rejestracji',
'Role': 'Rola',
'Rows in table': 'Wiersze w tabeli',
'Rows selected': 'Wybrane wiersze',
'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Select Group:': 'Select Group:',
'Stats': 'Stats',
'Step': 'Step',
'Stylesheet': 'Arkusz stylów',
'Submission': 'Submission',
'Submission Interface': 'Submission Interface',
'Submission Receipt': 'Submission Receipt',
'Submission interface': 'Submission interface',
'Submission status': 'Submission status',
'Submit': 'Wyślij',
'Submit material': 'Submit material',
'Submit receipt': 'Submit receipt',
'Sure you want to delete this object?': 'Czy na pewno chcesz usunąć ten obiekt?',
'Table name': 'Nazwa tabeli',
'Tags': 'Tags',
'Targets': 'Targets',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': '"Zapytanie" jest warunkiem postaci "db.tabela1.pole1==\'wartość\'". Takie coś jak "db.tabela1.pole1==db.tabela2.pole2" oznacza SQL JOIN.',
'This is a number you should write down to keep track of your submission': 'This is a number you should write down to keep track of your submission',
'This is the material submitted by the whistleblower for your revision. You are invited to': 'This is the material submitted by the whistleblower for your revision. You are invited to',
'Timestamp': 'Znacznik czasu',
'Tip-off': 'Tip-off',
'Tip-off access statistics': 'Tip-off access statistics',
'Tip-off removed and all relatives': 'Tip-off removed and all relatives',
'Tulip': 'Tulip',
'Tulip Receipt': 'Tulip Receipt',
'Tulip access statistics': 'Tulip access statistics',
'Tulip removed and all relatives': 'Tulip removed and all relatives',
'Tulips': 'Tulips',
'Update:': 'Uaktualnij:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Użyj (...)&(...) jako AND, (...)|(...) jako OR oraz ~(...)  jako NOT do tworzenia bardziej skomplikowanych zapytań.',
'User %(id)s Registered': 'Użytkownik %(id)s został zarejestrowany',
'User ID': 'ID użytkownika',
'Username': 'Username',
'Verify Password': 'Potwierdź hasło',
'View': 'Widok',
'Views': 'Views',
'Warning': 'Warning',
'Welcome %s': 'Welcome %s',
'Welcome back Whistleblower: this TULIP interface is unique for you.': 'Welcome back Whistleblower: this TULIP interface is unique for you.',
'Welcome back Whistleblower: this interface is unique for you.': 'Welcome back Whistleblower: this interface is unique for you.',
'Welcome to web2py': 'Witaj w web2py',
'Whistleblower': 'Whistleblower',
'You are also able to use your Whistleblower receipt from the first page.': 'You are also able to use your Whistleblower receipt from the first page.',
'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.': 'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.',
'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.': 'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.',
"You've received a": "You've received a",
"You've received a Tulip...": "You've received a Tulip...",
'Your submission': 'Your submission',
'Your tip-off': 'Your tip-off',
'ZIP': 'ZIP',
'appadmin is disabled because insecure channel': 'administracja aplikacji wyłączona z powodu braku bezpiecznego połączenia',
'cache': 'cache',
'change password': 'change password',
'check back later': 'check back later',
'customize me!': 'dostosuj mnie!',
'data uploaded': 'dane wysłane',
'database': 'baza danych',
'database %s select': 'wybór z bazy danych %s',
'db': 'baza danych',
'design': 'projektuj',
'done!': 'zrobione!',
'edit profile': 'edit profile',
'export as csv file': 'eksportuj jako plik csv',
'insert new': 'wstaw nowy rekord tabeli',
'insert new %s': 'wstaw nowy rekord do tabeli %s',
'invalid receipt: Tip-off not found': 'invalid receipt: Tip-off not found',
'invalid receipt: Tulip not found': 'invalid receipt: Tulip not found',
'invalid request': 'Błędne żądanie',
'login': 'login',
'logout': 'logout',
'must accept disclaimer': 'must accept disclaimer',
'new record inserted': 'nowy rekord został wstawiony',
'next 100 rows': 'następne 100 wierszy',
'or import from csv file': 'lub zaimportuj z pliku csv',
'powered by': 'powered by',
'previous 100 rows': 'poprzednie 100 wierszy',
'record': 'rekord',
'record does not exist': 'rekord nie istnieje',
'record id': 'id rekordu',
'register': 'register',
'seconds': 'seconds',
'selected': 'wybranych',
'state': 'stan',
'table': 'tabela',
'tulips': 'tulips',
'unable to parse csv file': 'nie można sparsować pliku csv',
}

########NEW FILE########
__FILENAME__ = pt-br
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"update" é uma expressão opcional como "campo1=\'novovalor\'". Você não pode atualizar ou apagar os resultados de um JOIN',
'%Y-%m-%d': '%d-%m-%Y',
'%Y-%m-%d %H:%M:%S': '%d-%m-%Y %H:%M:%S',
'%s rows deleted': '%s linhas apagadas',
'%s rows updated': '%s linhas atualizadas',
'About': 'About',
'Accept Disclaimer': 'Accept Disclaimer',
'Access Control': 'Access Control',
'Add': 'Add',
'Add Files': 'Add Files',
'Add files': 'Add files',
'Administrative interface': 'Interface administrativa',
'Ajax Recipes': 'Ajax Recipes',
'Analyze the received material, your work is fundamental in uncovering the truth': 'Analyze the received material, your work is fundamental in uncovering the truth',
'Are you sure you want to delete this object?': 'Are you sure you want to delete this object?',
'Ask useful details to the whistleblower thru the comment box': 'Ask useful details to the whistleblower thru the comment box',
'Available databases and tables': 'Bancos de dados e tabelas disponíveis',
'Bouquet': 'Bouquet',
'Buy this book': 'Buy this book',
'Cancel upload': 'Cancel upload',
'Cannot be empty': 'Não pode ser vazio',
'Check to delete': 'Marque para apagar',
'Client IP': 'Client IP',
'Comments': 'Comments',
'Community': 'Community',
'Complete Download': 'Complete Download',
'Config': 'Config',
'Controller': 'Controlador',
'Copyright': 'Copyright',
'Current request': 'Requisição atual',
'Current response': 'Resposta atual',
'Current session': 'Sessão atual',
'DB Model': 'Modelo BD',
'Database': 'Banco de dados',
'Delete Files': 'Delete Files',
'Delete:': 'Apagar:',
'Demo': 'Demo',
'Deployment Recipes': 'Deployment Recipes',
'Description': 'Description',
'Documentation': 'Documentation',
'Done': 'Done',
'Download': 'Download',
'Downloads': 'Downloads',
'E-mail': 'E-mail',
'Edit': 'Editar',
'Edit This App': 'Edit This App',
'Edit current record': 'Editar o registro atual',
'Encrypted ZIP': 'Encrypted ZIP',
'Error: only ten digits are accepted as receipt': 'Error: only ten digits are accepted as receipt',
'Error: you puts more than 10 digits': 'Error: you puts more than 10 digits',
'Errors': 'Errors',
'FAQ': 'FAQ',
'Finish': 'Finish',
'First name': 'First name',
'Forms and Validators': 'Forms and Validators',
'Forward to another receiver group': 'Forward to another receiver group',
'Free Applications': 'Free Applications',
'Globalview': 'Globalview',
'Group ID': 'Group ID',
'Groups': 'Groups',
'Hello World': 'Olá Mundo',
'Home': 'Home',
'I want delete this tip-off and all the others derived from the same material': 'I want delete this tip-off and all the others derived from the same material',
'I want delete this tulip and all the tulips derived from the same material': 'I want delete this tulip and all the tulips derived from the same material',
'ID': 'ID',
'Import/Export': 'Importar/Exportar',
'Incomplete configuration': 'Incomplete configuration',
'Index': 'Início',
'Internal State': 'Estado Interno',
'Introduction': 'Introduction',
'Invalid Query': 'Consulta Inválida',
'Invalid email': 'Invalid email',
"It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.": "It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.",
'Language': 'Language',
'Last name': 'Last name',
'Layout': 'Layout',
'Layouts': 'Layouts',
'Live chat': 'Live chat',
'Login': 'Autentique-se',
'Logout': 'Logout',
'Lost Password': 'Esqueceu sua senha?',
'Main Menu': 'Menu Principal',
'Material': 'Material',
'Material description': 'Material description',
'Material has not been processed yet': 'Material has not been processed yet',
'Menu Model': 'Modelo de Menu',
'Name': 'Name',
'New Record': 'Novo Registro',
'Next': 'Next',
'No comments': 'No comments',
'No databases in this application': 'Sem bancos de dados nesta aplicação',
'Node View': 'Node View',
'Not spread this link. It is intended be for your eyes only': 'Not spread this link. It is intended be for your eyes only',
'Online examples': 'Alguns exemplos',
'Origin': 'Origin',
'Other Recipes': 'Other Recipes',
'Overview': 'Overview',
'PGP Encrypted ZIP': 'PGP Encrypted ZIP',
'Password': 'Password',
'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)': 'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)',
'Plugins': 'Plugins',
'Powered by': 'Powered by',
'Preface': 'Preface',
'Preferences': 'Preferences',
'Previous': 'Previous',
'Python': 'Python',
'Query:': 'Consulta:',
'Quick Examples': 'Quick Examples',
'Receiver': 'Receiver',
'Receivers': 'Receivers',
'Recipes': 'Recipes',
'Record ID': 'Record ID',
'Redirecting to Hidden Serivice in': 'Redirecting to Hidden Serivice in',
'Register': 'Registre-se',
'Registration key': 'Registration key',
'Reset Password key': 'Reset Password key',
'Resources': 'Resources',
'Role': 'Role',
'Rows in table': 'Linhas na tabela',
'Rows selected': 'Linhas selecionadas',
'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Select Group:': 'Select Group:',
'Semantic': 'Semantic',
'Services': 'Services',
'Stats': 'Stats',
'Step': 'Step',
'Stylesheet': 'Stylesheet',
'Submission': 'Submission',
'Submission Interface': 'Submission Interface',
'Submission Receipt': 'Submission Receipt',
'Submission interface': 'Submission interface',
'Submission status': 'Submission status',
'Submit material': 'Submit material',
'Submit receipt': 'Submit receipt',
'Support': 'Support',
'Sure you want to delete this object?': 'Está certo(a) que deseja apagar esse objeto ?',
'Table name': 'Table name',
'Tags': 'Tags',
'Targets': 'Targets',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'Uma "consulta" é uma condição como "db.tabela1.campo1==\'valor\'". Expressões como "db.tabela1.campo1==db.tabela2.campo2" resultam em um JOIN SQL.',
'The Core': 'The Core',
'The Views': 'The Views',
'The output of the file is a dictionary that was rendered by the view': 'The output of the file is a dictionary that was rendered by the view',
'This App': 'This App',
'This is a copy of the scaffolding application': 'This is a copy of the scaffolding application',
'This is a number you should write down to keep track of your submission': 'This is a number you should write down to keep track of your submission',
'This is the material submitted by the whistleblower for your revision. You are invited to': 'This is the material submitted by the whistleblower for your revision. You are invited to',
'Timestamp': 'Timestamp',
'Tip-off': 'Tip-off',
'Tip-off access statistics': 'Tip-off access statistics',
'Tip-off removed and all relatives': 'Tip-off removed and all relatives',
'Tulip': 'Tulip',
'Tulip Receipt': 'Tulip Receipt',
'Tulip access statistics': 'Tulip access statistics',
'Tulip removed and all relatives': 'Tulip removed and all relatives',
'Tulips': 'Tulips',
'Twitter': 'Twitter',
'Update:': 'Atualizar:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Use (...)&(...) para AND, (...)|(...) para OR, e ~(...)  para NOT para construir consultas mais complexas.',
'User ID': 'User ID',
'User Voice': 'User Voice',
'Username': 'Username',
'Videos': 'Videos',
'View': 'Visualização',
'Views': 'Views',
'Warning': 'Warning',
'Web2py': 'Web2py',
'Welcome': 'Welcome',
'Welcome %s': 'Vem vindo %s',
'Welcome back Whistleblower: this TULIP interface is unique for you.': 'Welcome back Whistleblower: this TULIP interface is unique for you.',
'Welcome back Whistleblower: this interface is unique for you.': 'Welcome back Whistleblower: this interface is unique for you.',
'Welcome to web2py': 'Bem vindo ao web2py',
'Which called the function': 'Which called the function',
'Whistleblower': 'Whistleblower',
'You are also able to use your Whistleblower receipt from the first page.': 'You are also able to use your Whistleblower receipt from the first page.',
'You are successfully running web2py': 'You are successfully running web2py',
'You are successfully running web2py.': 'You are successfully running web2py.',
'You can modify this application and adapt it to your needs': 'You can modify this application and adapt it to your needs',
'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.': 'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.',
'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.': 'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.',
'You visited the url': 'You visited the url',
"You've received a": "You've received a",
"You've received a Tulip...": "You've received a Tulip...",
'Your submission': 'Your submission',
'Your tip-off': 'Your tip-off',
'ZIP': 'ZIP',
'appadmin is disabled because insecure channel': 'Administração desativada devido ao canal inseguro',
'cache': 'cache',
'change password': 'modificar senha',
'check back later': 'check back later',
'customize me!': 'Personalize-me!',
'data uploaded': 'dados enviados',
'database': 'banco de dados',
'database %s select': 'Selecionar banco de dados %s',
'db': 'bd',
'design': 'design',
'done!': 'concluído!',
'edit profile': 'editar perfil',
'export as csv file': 'exportar como um arquivo csv',
'insert new': 'inserir novo',
'insert new %s': 'inserir novo %s',
'invalid receipt: Tip-off not found': 'invalid receipt: Tip-off not found',
'invalid receipt: Tulip not found': 'invalid receipt: Tulip not found',
'invalid request': 'requisição inválida',
'located in the file': 'located in the file',
'login': 'Entrar',
'logout': 'Sair',
'lost password?': 'lost password?',
'must accept disclaimer': 'must accept disclaimer',
'new record inserted': 'novo registro inserido',
'next 100 rows': 'próximas 100 linhas',
'or import from csv file': 'ou importar de um arquivo csv',
'powered by': 'powered by',
'previous 100 rows': '100 linhas anteriores',
'record': 'registro',
'record does not exist': 'registro não existe',
'record id': 'id do registro',
'register': 'Registre-se',
'seconds': 'seconds',
'selected': 'selecionado',
'state': 'estado',
'table': 'tabela',
'tulips': 'tulips',
'unable to parse csv file': 'não foi possível analisar arquivo csv',
}

########NEW FILE########
__FILENAME__ = pt-pt
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"update" é uma expressão opcional como "field1=\'newvalue\'". Não pode actualizar ou eliminar os resultados de um JOIN',
'%Y-%m-%d': '%Y-%m-%d',
'%Y-%m-%d %H:%M:%S': '%Y-%m-%d %H:%M:%S',
'%s rows deleted': '%s linhas eliminadas',
'%s rows updated': '%s linhas actualizadas',
'About': 'About',
'Accept Disclaimer': 'Accept Disclaimer',
'Add': 'Add',
'Add Files': 'Add Files',
'Add files': 'Add files',
'Administrative interface': 'Painel administrativo',
'Analyze the received material, your work is fundamental in uncovering the truth': 'Analyze the received material, your work is fundamental in uncovering the truth',
'Are you sure you want to delete this object?': 'Are you sure you want to delete this object?',
'Ask useful details to the whistleblower thru the comment box': 'Ask useful details to the whistleblower thru the comment box',
'Author Reference Auth User': 'Author Reference Auth User',
'Author Reference Auth User.username': 'Author Reference Auth User.username',
'Available databases and tables': 'bases de dados e tabelas disponíveis',
'Bouquet': 'Bouquet',
'Cancel upload': 'Cancel upload',
'Cannot be empty': 'não pode ser vazio',
'Category Create': 'Category Create',
'Category Select': 'Category Select',
'Check to delete': 'seleccione para eliminar',
'Comment Create': 'Comment Create',
'Comment Select': 'Comment Select',
'Comments': 'Comments',
'Complete Download': 'Complete Download',
'Config': 'Config',
'Content': 'Content',
'Controller': 'Controlador',
'Copyright': 'Direitos de cópia',
'Created By': 'Created By',
'Created On': 'Created On',
'Current request': 'pedido currente',
'Current response': 'resposta currente',
'Current session': 'sessão currente',
'DB Model': 'Modelo de BD',
'Database': 'Base de dados',
'Delete Files': 'Delete Files',
'Delete:': 'Eliminar:',
'Done': 'Done',
'Download': 'Download',
'Downloads': 'Downloads',
'Edit': 'Editar',
'Edit This App': 'Edite esta aplicação',
'Edit current record': 'Edição de registo currente',
'Email': 'Email',
'Encrypted ZIP': 'Encrypted ZIP',
'Error: only ten digits are accepted as receipt': 'Error: only ten digits are accepted as receipt',
'Error: you puts more than 10 digits': 'Error: you puts more than 10 digits',
'Finish': 'Finish',
'First Name': 'First Name',
'For %s #%s': 'For %s #%s',
'Forward to another receiver group': 'Forward to another receiver group',
'Globalview': 'Globalview',
'Groups': 'Groups',
'Hello World': 'Olá Mundo',
'I want delete this tip-off and all the others derived from the same material': 'I want delete this tip-off and all the others derived from the same material',
'I want delete this tulip and all the tulips derived from the same material': 'I want delete this tulip and all the tulips derived from the same material',
'ID': 'ID',
'Import/Export': 'Importar/Exportar',
'Incomplete configuration': 'Incomplete configuration',
'Index': 'Índice',
'Internal State': 'Estado interno',
'Invalid Query': 'Consulta Inválida',
"It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.": "It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.",
'Language': 'Language',
'Last Name': 'Last Name',
'Layout': 'Esboço',
'Logout': 'Logout',
'Main Menu': 'Menu Principal',
'Material': 'Material',
'Material description': 'Material description',
'Material has not been processed yet': 'Material has not been processed yet',
'Menu Model': 'Menu do Modelo',
'Modified By': 'Modified By',
'Modified On': 'Modified On',
'Name': 'Name',
'New Record': 'Novo Registo',
'Next': 'Next',
'No Data': 'No Data',
'No comments': 'No comments',
'No databases in this application': 'Não há bases de dados nesta aplicação',
'Node View': 'Node View',
'Not spread this link. It is intended be for your eyes only': 'Not spread this link. It is intended be for your eyes only',
'Online examples': 'Exemplos online',
'PGP Encrypted ZIP': 'PGP Encrypted ZIP',
'Password': 'Password',
'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)': 'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)',
'Post Create': 'Post Create',
'Post Select': 'Post Select',
'Powered by': 'Suportado por',
'Preferences': 'Preferences',
'Previous': 'Previous',
'Query:': 'Interrogação:',
'Receiver': 'Receiver',
'Receivers': 'Receivers',
'Redirecting to Hidden Serivice in': 'Redirecting to Hidden Serivice in',
'Replyto Reference Post': 'Replyto Reference Post',
'Rows in table': 'Linhas numa tabela',
'Rows selected': 'Linhas seleccionadas',
'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Select Group:': 'Select Group:',
'Stats': 'Stats',
'Step': 'Step',
'Stylesheet': 'Folha de estilo',
'Submission': 'Submission',
'Submission Interface': 'Submission Interface',
'Submission Receipt': 'Submission Receipt',
'Submission interface': 'Submission interface',
'Submission status': 'Submission status',
'Submit material': 'Submit material',
'Submit receipt': 'Submit receipt',
'Sure you want to delete this object?': 'Tem a certeza que deseja eliminar este objecto?',
'Tags': 'Tags',
'Targets': 'Targets',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'A "query" é uma condição do tipo "db.table1.field1==\'value\'". Algo como "db.table1.field1==db.table2.field2" resultaria num SQL JOIN.',
'This is a number you should write down to keep track of your submission': 'This is a number you should write down to keep track of your submission',
'This is the material submitted by the whistleblower for your revision. You are invited to': 'This is the material submitted by the whistleblower for your revision. You are invited to',
'Tip-off': 'Tip-off',
'Tip-off access statistics': 'Tip-off access statistics',
'Tip-off removed and all relatives': 'Tip-off removed and all relatives',
'Title': 'Title',
'Tulip': 'Tulip',
'Tulip Receipt': 'Tulip Receipt',
'Tulip access statistics': 'Tulip access statistics',
'Tulip removed and all relatives': 'Tulip removed and all relatives',
'Tulips': 'Tulips',
'Update:': 'Actualização:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Utilize (...)&(...) para AND, (...)|(...) para OR, e ~(...)  para NOT para construir interrogações mais complexas.',
'Username': 'Username',
'View': 'Vista',
'Views': 'Views',
'Warning': 'Warning',
'Welcome %s': 'Bem-vindo(a) %s',
'Welcome back Whistleblower: this TULIP interface is unique for you.': 'Welcome back Whistleblower: this TULIP interface is unique for you.',
'Welcome back Whistleblower: this interface is unique for you.': 'Welcome back Whistleblower: this interface is unique for you.',
'Welcome to Gluonization': 'Bem vindo ao Web2py',
'Welcome to web2py': 'Bem-vindo(a) ao web2py',
'When': 'When',
'Whistleblower': 'Whistleblower',
'You are also able to use your Whistleblower receipt from the first page.': 'You are also able to use your Whistleblower receipt from the first page.',
'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.': 'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.',
'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.': 'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.',
"You've received a": "You've received a",
"You've received a Tulip...": "You've received a Tulip...",
'Your submission': 'Your submission',
'Your tip-off': 'Your tip-off',
'ZIP': 'ZIP',
'appadmin is disabled because insecure channel': 'appadmin está desactivada pois o canal é inseguro',
'cache': 'cache',
'change password': 'alterar palavra-chave',
'check back later': 'check back later',
'create new category': 'create new category',
'create new comment': 'create new comment',
'create new post': 'create new post',
'customize me!': 'Personaliza-me!',
'data uploaded': 'informação enviada',
'database': 'base de dados',
'database %s select': 'selecção de base de dados %s',
'db': 'bd',
'design': 'design',
'done!': 'concluído!',
'edit category': 'edit category',
'edit comment': 'edit comment',
'edit post': 'edit post',
'edit profile': 'Editar perfil',
'export as csv file': 'exportar como ficheiro csv',
'insert new': 'inserir novo',
'insert new %s': 'inserir novo %s',
'invalid receipt: Tip-off not found': 'invalid receipt: Tip-off not found',
'invalid receipt: Tulip not found': 'invalid receipt: Tulip not found',
'invalid request': 'Pedido Inválido',
'login': 'login',
'logout': 'logout',
'must accept disclaimer': 'must accept disclaimer',
'new record inserted': 'novo registo inserido',
'next 100 rows': 'próximas 100 linhas',
'or import from csv file': 'ou importe a partir de ficheiro csv',
'powered by': 'powered by',
'previous 100 rows': '100 linhas anteriores',
'record': 'registo',
'record does not exist': 'registo inexistente',
'record id': 'id de registo',
'register': 'register',
'search category': 'search category',
'search comment': 'search comment',
'search post': 'search post',
'seconds': 'seconds',
'select category': 'select category',
'select comment': 'select comment',
'select post': 'select post',
'selected': 'seleccionado(s)',
'show category': 'show category',
'show comment': 'show comment',
'show post': 'show post',
'state': 'estado',
'table': 'tabela',
'tulips': 'tulips',
'unable to parse csv file': 'não foi possível carregar ficheiro csv',
}

########NEW FILE########
__FILENAME__ = pt
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"update" é uma expressão opcional como "field1=\'newvalue\'". Não pode actualizar ou eliminar os resultados de um JOIN',
'%Y-%m-%d': '%Y-%m-%d',
'%Y-%m-%d %H:%M:%S': '%Y-%m-%d %H:%M:%S',
'%s rows deleted': '%s linhas eliminadas',
'%s rows updated': '%s linhas actualizadas',
'About': 'About',
'Accept Disclaimer': 'Accept Disclaimer',
'Add': 'Add',
'Add Files': 'Add Files',
'Add files': 'Add files',
'Administrative interface': 'Painel administrativo',
'Analyze the received material, your work is fundamental in uncovering the truth': 'Analyze the received material, your work is fundamental in uncovering the truth',
'Are you sure you want to delete this object?': 'Are you sure you want to delete this object?',
'Ask useful details to the whistleblower thru the comment box': 'Ask useful details to the whistleblower thru the comment box',
'Author Reference Auth User': 'Author Reference Auth User',
'Author Reference Auth User.username': 'Author Reference Auth User.username',
'Available databases and tables': 'bases de dados e tabelas disponíveis',
'Bouquet': 'Bouquet',
'Cancel upload': 'Cancel upload',
'Cannot be empty': 'não pode ser vazio',
'Category Create': 'Category Create',
'Category Select': 'Category Select',
'Check to delete': 'seleccione para eliminar',
'Comment Create': 'Comment Create',
'Comment Select': 'Comment Select',
'Comments': 'Comments',
'Complete Download': 'Complete Download',
'Config': 'Config',
'Content': 'Content',
'Controller': 'Controlador',
'Copyright': 'Direitos de cópia',
'Created By': 'Created By',
'Created On': 'Created On',
'Current request': 'pedido currente',
'Current response': 'resposta currente',
'Current session': 'sessão currente',
'DB Model': 'Modelo de BD',
'Database': 'Base de dados',
'Delete Files': 'Delete Files',
'Delete:': 'Eliminar:',
'Done': 'Done',
'Download': 'Download',
'Downloads': 'Downloads',
'Edit': 'Editar',
'Edit This App': 'Edite esta aplicação',
'Edit current record': 'Edição de registo currente',
'Email': 'Email',
'Encrypted ZIP': 'Encrypted ZIP',
'Error: only ten digits are accepted as receipt': 'Error: only ten digits are accepted as receipt',
'Error: you puts more than 10 digits': 'Error: you puts more than 10 digits',
'Finish': 'Finish',
'First Name': 'First Name',
'For %s #%s': 'For %s #%s',
'Forward to another receiver group': 'Forward to another receiver group',
'Globalview': 'Globalview',
'Groups': 'Groups',
'Hello World': 'Olá Mundo',
'I want delete this tip-off and all the others derived from the same material': 'I want delete this tip-off and all the others derived from the same material',
'I want delete this tulip and all the tulips derived from the same material': 'I want delete this tulip and all the tulips derived from the same material',
'ID': 'ID',
'Import/Export': 'Importar/Exportar',
'Incomplete configuration': 'Incomplete configuration',
'Index': 'Índice',
'Internal State': 'Estado interno',
'Invalid Query': 'Consulta Inválida',
"It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.": "It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.",
'Language': 'Language',
'Last Name': 'Last Name',
'Layout': 'Esboço',
'Logout': 'Logout',
'Main Menu': 'Menu Principal',
'Material': 'Material',
'Material description': 'Material description',
'Material has not been processed yet': 'Material has not been processed yet',
'Menu Model': 'Menu do Modelo',
'Modified By': 'Modified By',
'Modified On': 'Modified On',
'Name': 'Name',
'New Record': 'Novo Registo',
'Next': 'Next',
'No Data': 'No Data',
'No comments': 'No comments',
'No databases in this application': 'Não há bases de dados nesta aplicação',
'Node View': 'Node View',
'Not spread this link. It is intended be for your eyes only': 'Not spread this link. It is intended be for your eyes only',
'Online examples': 'Exemplos online',
'PGP Encrypted ZIP': 'PGP Encrypted ZIP',
'Password': 'Password',
'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)': 'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)',
'Post Create': 'Post Create',
'Post Select': 'Post Select',
'Powered by': 'Suportado por',
'Preferences': 'Preferences',
'Previous': 'Previous',
'Query:': 'Interrogação:',
'Receiver': 'Receiver',
'Receivers': 'Receivers',
'Redirecting to Hidden Serivice in': 'Redirecting to Hidden Serivice in',
'Replyto Reference Post': 'Replyto Reference Post',
'Rows in table': 'Linhas numa tabela',
'Rows selected': 'Linhas seleccionadas',
'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Select Group:': 'Select Group:',
'Stats': 'Stats',
'Step': 'Step',
'Stylesheet': 'Folha de estilo',
'Submission': 'Submission',
'Submission Interface': 'Submission Interface',
'Submission Receipt': 'Submission Receipt',
'Submission interface': 'Submission interface',
'Submission status': 'Submission status',
'Submit material': 'Submit material',
'Submit receipt': 'Submit receipt',
'Sure you want to delete this object?': 'Tem a certeza que deseja eliminar este objecto?',
'Tags': 'Tags',
'Targets': 'Targets',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'A "query" é uma condição do tipo "db.table1.field1==\'value\'". Algo como "db.table1.field1==db.table2.field2" resultaria num SQL JOIN.',
'This is a number you should write down to keep track of your submission': 'This is a number you should write down to keep track of your submission',
'This is the material submitted by the whistleblower for your revision. You are invited to': 'This is the material submitted by the whistleblower for your revision. You are invited to',
'Tip-off': 'Tip-off',
'Tip-off access statistics': 'Tip-off access statistics',
'Tip-off removed and all relatives': 'Tip-off removed and all relatives',
'Title': 'Title',
'Tulip': 'Tulip',
'Tulip Receipt': 'Tulip Receipt',
'Tulip access statistics': 'Tulip access statistics',
'Tulip removed and all relatives': 'Tulip removed and all relatives',
'Tulips': 'Tulips',
'Update:': 'Actualização:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Utilize (...)&(...) para AND, (...)|(...) para OR, e ~(...)  para NOT para construir interrogações mais complexas.',
'Username': 'Username',
'View': 'Vista',
'Views': 'Views',
'Warning': 'Warning',
'Welcome %s': 'Bem-vindo(a) %s',
'Welcome back Whistleblower: this TULIP interface is unique for you.': 'Welcome back Whistleblower: this TULIP interface is unique for you.',
'Welcome back Whistleblower: this interface is unique for you.': 'Welcome back Whistleblower: this interface is unique for you.',
'Welcome to Gluonization': 'Bem vindo ao Web2py',
'Welcome to web2py': 'Bem-vindo(a) ao web2py',
'When': 'When',
'Whistleblower': 'Whistleblower',
'You are also able to use your Whistleblower receipt from the first page.': 'You are also able to use your Whistleblower receipt from the first page.',
'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.': 'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.',
'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.': 'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.',
"You've received a": "You've received a",
"You've received a Tulip...": "You've received a Tulip...",
'Your submission': 'Your submission',
'Your tip-off': 'Your tip-off',
'ZIP': 'ZIP',
'appadmin is disabled because insecure channel': 'appadmin está desactivada pois o canal é inseguro',
'cache': 'cache',
'change password': 'alterar palavra-chave',
'check back later': 'check back later',
'create new category': 'create new category',
'create new comment': 'create new comment',
'create new post': 'create new post',
'customize me!': 'Personaliza-me!',
'data uploaded': 'informação enviada',
'database': 'base de dados',
'database %s select': 'selecção de base de dados %s',
'db': 'bd',
'design': 'design',
'done!': 'concluído!',
'edit category': 'edit category',
'edit comment': 'edit comment',
'edit post': 'edit post',
'edit profile': 'Editar perfil',
'export as csv file': 'exportar como ficheiro csv',
'insert new': 'inserir novo',
'insert new %s': 'inserir novo %s',
'invalid receipt: Tip-off not found': 'invalid receipt: Tip-off not found',
'invalid receipt: Tulip not found': 'invalid receipt: Tulip not found',
'invalid request': 'Pedido Inválido',
'login': 'login',
'logout': 'logout',
'must accept disclaimer': 'must accept disclaimer',
'new record inserted': 'novo registo inserido',
'next 100 rows': 'próximas 100 linhas',
'or import from csv file': 'ou importe a partir de ficheiro csv',
'powered by': 'powered by',
'previous 100 rows': '100 linhas anteriores',
'record': 'registo',
'record does not exist': 'registo inexistente',
'record id': 'id de registo',
'register': 'register',
'search category': 'search category',
'search comment': 'search comment',
'search post': 'search post',
'seconds': 'seconds',
'select category': 'select category',
'select comment': 'select comment',
'select post': 'select post',
'selected': 'seleccionado(s)',
'show category': 'show category',
'show comment': 'show comment',
'show post': 'show post',
'state': 'estado',
'table': 'tabela',
'tulips': 'tulips',
'unable to parse csv file': 'não foi possível carregar ficheiro csv',
}

########NEW FILE########
__FILENAME__ = ru-ru
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"Изменить" - необязательное выражение вида "field1=\'новое значение\'". Результаты операции JOIN нельзя изменить или удалить.',
'%Y-%m-%d': '%Y-%m-%d',
'%Y-%m-%d %H:%M:%S': '%Y-%m-%d %H:%M:%S',
'%s rows deleted': '%s строк удалено',
'%s rows updated': '%s строк изменено',
'Accept Disclaimer': 'Accept Disclaimer',
'Add': 'Add',
'Add Files': 'Add Files',
'Add files': 'Add files',
'Administrative interface': 'административный интерфейс',
'Analyze the received material, your work is fundamental in uncovering the truth': 'Analyze the received material, your work is fundamental in uncovering the truth',
'Are you sure you want to delete this object?': 'Are you sure you want to delete this object?',
'Ask useful details to the whistleblower thru the comment box': 'Ask useful details to the whistleblower thru the comment box',
'Available databases and tables': 'Базы данных и таблицы',
'Bouquet': 'Bouquet',
'Cancel upload': 'Cancel upload',
'Cannot be empty': 'Пустое значение недопустимо',
'Change Password': 'Смените пароль',
'Check to delete': 'Удалить',
'Check to delete:': 'Удалить:',
'Client IP': 'Client IP',
'Comments': 'Comments',
'Complete Download': 'Complete Download',
'Config': 'Config',
'Current request': 'Текущий запрос',
'Current response': 'Текущий ответ',
'Current session': 'Текущая сессия',
'Delete Files': 'Delete Files',
'Delete:': 'Удалить:',
'Description': 'Описание',
'Done': 'Done',
'Download': 'Download',
'Downloads': 'Downloads',
'E-mail': 'E-mail',
'Edit Profile': 'Редактировать профиль',
'Edit current record': 'Редактировать текущую запись',
'Encrypted ZIP': 'Encrypted ZIP',
'Error: only ten digits are accepted as receipt': 'Error: only ten digits are accepted as receipt',
'Error: you puts more than 10 digits': 'Error: you puts more than 10 digits',
'Finish': 'Finish',
'First name': 'Имя',
'Forward to another receiver group': 'Forward to another receiver group',
'Globalview': 'Globalview',
'Group ID': 'Group ID',
'Groups': 'Groups',
'Hello World': 'Заработало!',
'I want delete this tip-off and all the others derived from the same material': 'I want delete this tip-off and all the others derived from the same material',
'I want delete this tulip and all the tulips derived from the same material': 'I want delete this tulip and all the tulips derived from the same material',
'ID': 'ID',
'Import/Export': 'Импорт/экспорт',
'Incomplete configuration': 'Incomplete configuration',
'Index': 'Index',
'Internal State': 'Внутренне состояние',
'Invalid Query': 'Неверный запрос',
'Invalid email': 'Неверный email',
'Invalid login': 'Неверный логин',
'Invalid password': 'Неверный пароль',
"It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.": "It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.",
'Language': 'Language',
'Last name': 'Фамилия',
'Logged in': 'Вход выполнен',
'Logged out': 'Выход выполнен',
'Login': 'Вход',
'Logout': 'Выход',
'Lost Password': 'Забыли пароль?',
'Material': 'Material',
'Material description': 'Material description',
'Material has not been processed yet': 'Material has not been processed yet',
'Name': 'Name',
'New Record': 'Новая запись',
'New password': 'Новый пароль',
'Next': 'Next',
'No comments': 'No comments',
'No databases in this application': 'В приложении нет баз данных',
'Node View': 'Node View',
'Not spread this link. It is intended be for your eyes only': 'Not spread this link. It is intended be for your eyes only',
'Old password': 'Старый пароль',
'Online examples': 'примеры он-лайн',
'Origin': 'Происхождение',
'PGP Encrypted ZIP': 'PGP Encrypted ZIP',
'Password': 'Пароль',
"Password fields don't match": 'Пароли не совпадают',
'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)': 'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)',
'Preferences': 'Preferences',
'Previous': 'Previous',
'Query:': 'Запрос:',
'Receiver': 'Receiver',
'Receivers': 'Receivers',
'Record ID': 'ID записи',
'Redirecting to Hidden Serivice in': 'Redirecting to Hidden Serivice in',
'Register': 'Зарегистрироваться',
'Registration key': 'Ключ регистрации',
'Remember me (for 30 days)': 'Запомнить меня (на 30 дней)',
'Reset Password key': 'Сбросить ключ пароля',
'Role': 'Роль',
'Rows in table': 'Строк в таблице',
'Rows selected': 'Выделено строк',
'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Select Group:': 'Select Group:',
'Stats': 'Stats',
'Step': 'Step',
'Submission': 'Submission',
'Submission Interface': 'Submission Interface',
'Submission Receipt': 'Submission Receipt',
'Submission interface': 'Submission interface',
'Submission status': 'Submission status',
'Submit': 'Отправить',
'Submit material': 'Submit material',
'Submit receipt': 'Submit receipt',
'Sure you want to delete this object?': 'Подтвердите удаление объекта',
'Table name': 'Имя таблицы',
'Tags': 'Tags',
'Targets': 'Targets',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': '"Запрос" - это условие вида "db.table1.field1==\'значение\'". Выражение вида "db.table1.field1==db.table2.field2" формирует SQL JOIN.',
'This is a number you should write down to keep track of your submission': 'This is a number you should write down to keep track of your submission',
'This is the material submitted by the whistleblower for your revision. You are invited to': 'This is the material submitted by the whistleblower for your revision. You are invited to',
'Timestamp': 'Отметка времени',
'Tip-off': 'Tip-off',
'Tip-off access statistics': 'Tip-off access statistics',
'Tip-off removed and all relatives': 'Tip-off removed and all relatives',
'Tulip': 'Tulip',
'Tulip Receipt': 'Tulip Receipt',
'Tulip access statistics': 'Tulip access statistics',
'Tulip removed and all relatives': 'Tulip removed and all relatives',
'Tulips': 'Tulips',
'Update:': 'Изменить:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Для построение сложных запросов используйте операторы "И": (...)&(...), "ИЛИ": (...)|(...), "НЕ": ~(...).',
'User %(id)s Logged-in': 'Пользователь %(id)s вошёл',
'User %(id)s Logged-out': 'Пользователь %(id)s вышел',
'User %(id)s Password changed': 'Пользователь %(id)s сменил пароль',
'User %(id)s Profile updated': 'Пользователь %(id)s обновил профиль',
'User %(id)s Registered': 'Пользователь %(id)s зарегистрировался',
'User ID': 'ID пользователя',
'Username': 'Username',
'Verify Password': 'Повторите пароль',
'Views': 'Views',
'Warning': 'Warning',
'Welcome back Whistleblower: this TULIP interface is unique for you.': 'Welcome back Whistleblower: this TULIP interface is unique for you.',
'Welcome back Whistleblower: this interface is unique for you.': 'Welcome back Whistleblower: this interface is unique for you.',
'Welcome to web2py': 'Добро пожаловать в web2py',
'Whistleblower': 'Whistleblower',
'You are also able to use your Whistleblower receipt from the first page.': 'You are also able to use your Whistleblower receipt from the first page.',
'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.': 'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.',
'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.': 'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.',
"You've received a": "You've received a",
"You've received a Tulip...": "You've received a Tulip...",
'Your submission': 'Your submission',
'Your tip-off': 'Your tip-off',
'ZIP': 'ZIP',
'check back later': 'check back later',
'customize me!': 'настройте внешний вид!',
'data uploaded': 'данные загружены',
'database': 'база данных',
'database %s select': 'выбор базы данных %s',
'db': 'БД',
'design': 'дизайн',
'done!': 'готово!',
'export as csv file': 'экспорт в  csv-файл',
'insert new': 'добавить',
'insert new %s': 'добавить %s',
'invalid receipt: Tip-off not found': 'invalid receipt: Tip-off not found',
'invalid receipt: Tulip not found': 'invalid receipt: Tulip not found',
'invalid request': 'неверный запрос',
'login': 'вход',
'logout': 'выход',
'must accept disclaimer': 'must accept disclaimer',
'new record inserted': 'новая запись добавлена',
'next 100 rows': 'следующие 100 строк',
'or import from csv file': 'или импорт из csv-файла',
'password': 'пароль',
'powered by': 'powered by',
'previous 100 rows': 'предыдущие 100 строк',
'profile': 'профиль',
'record': 'record',
'record does not exist': 'запись не найдена',
'record id': 'id записи',
'seconds': 'seconds',
'selected': 'выбрано',
'state': 'состояние',
'table': 'таблица',
'tulips': 'tulips',
'unable to parse csv file': 'нечитаемый csv-файл',
}

########NEW FILE########
__FILENAME__ = sk-sk
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"update" je voliteľný výraz ako "field1=\'newvalue\'". Nemôžete upravovať alebo zmazať výsledky JOINu',
'%Y-%m-%d': '%d.%m.%Y',
'%Y-%m-%d %H:%M:%S': '%d.%m.%Y %H:%M:%S',
'%s rows deleted': '%s zmazaných záznamov',
'%s rows updated': '%s upravených záznamov',
'Accept Disclaimer': 'Accept Disclaimer',
'Add': 'Add',
'Add Files': 'Add Files',
'Add files': 'Add files',
'Administrative interface': 'pre administrátorské rozhranie kliknite sem',
'Analyze the received material, your work is fundamental in uncovering the truth': 'Analyze the received material, your work is fundamental in uncovering the truth',
'Are you sure you want to delete this object?': 'Are you sure you want to delete this object?',
'Ask useful details to the whistleblower thru the comment box': 'Ask useful details to the whistleblower thru the comment box',
'Available databases and tables': 'Dostupné databázy a tabuľky',
'Bouquet': 'Bouquet',
'Cancel upload': 'Cancel upload',
'Cannot be empty': 'Nemôže byť prázdne',
'Check to delete': 'Označiť na zmazanie',
'Comments': 'Comments',
'Complete Download': 'Complete Download',
'Config': 'Config',
'Controller': 'Controller',
'Copyright': 'Copyright',
'Current request': 'Aktuálna požiadavka',
'Current response': 'Aktuálna odpoveď',
'Current session': 'Aktuálne sedenie',
'DB Model': 'DB Model',
'Database': 'Databáza',
'Delete Files': 'Delete Files',
'Delete:': 'Zmazať:',
'Description': 'Popis',
'Documentation': 'Dokumentácia',
'Done': 'Done',
'Download': 'Download',
'Downloads': 'Downloads',
'Edit': 'Upraviť',
'Edit Profile': 'Upraviť profil',
'Edit current record': 'Upraviť aktuálny záznam',
'Encrypted ZIP': 'Encrypted ZIP',
'Error: only ten digits are accepted as receipt': 'Error: only ten digits are accepted as receipt',
'Error: you puts more than 10 digits': 'Error: you puts more than 10 digits',
'Finish': 'Finish',
'First name': 'Krstné meno',
'Forward to another receiver group': 'Forward to another receiver group',
'Globalview': 'Globalview',
'Group ID': 'ID skupiny',
'Groups': 'Groups',
'Hello World': 'Ahoj svet',
'I want delete this tip-off and all the others derived from the same material': 'I want delete this tip-off and all the others derived from the same material',
'I want delete this tulip and all the tulips derived from the same material': 'I want delete this tulip and all the tulips derived from the same material',
'ID': 'ID',
'Import/Export': 'Import/Export',
'Incomplete configuration': 'Incomplete configuration',
'Index': 'Index',
'Internal State': 'Vnútorný stav',
'Invalid Query': 'Neplatná otázka',
'Invalid email': 'Neplatný email',
'Invalid password': 'Nesprávne heslo',
"It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.": "It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.",
'Language': 'Language',
'Last name': 'Priezvisko',
'Layout': 'Layout',
'Logged in': 'Prihlásený',
'Logged out': 'Odhlásený',
'Logout': 'Logout',
'Lost Password': 'Stratené heslo?',
'Material': 'Material',
'Material description': 'Material description',
'Material has not been processed yet': 'Material has not been processed yet',
'Menu Model': 'Menu Model',
'Name': 'Meno',
'New Record': 'Nový záznam',
'New password': 'Nové heslo',
'Next': 'Next',
'No comments': 'No comments',
'No databases in this application': 'V tejto aplikácii nie sú databázy',
'Node View': 'Node View',
'Not spread this link. It is intended be for your eyes only': 'Not spread this link. It is intended be for your eyes only',
'Old password': 'Staré heslo',
'Online examples': 'pre online príklady kliknite sem',
'Origin': 'Pôvod',
'PGP Encrypted ZIP': 'PGP Encrypted ZIP',
'Password': 'Heslo',
'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)': 'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)',
'Powered by': 'Powered by',
'Preferences': 'Preferences',
'Previous': 'Previous',
'Query:': 'Otázka:',
'Receiver': 'Receiver',
'Receivers': 'Receivers',
'Record ID': 'ID záznamu',
'Redirecting to Hidden Serivice in': 'Redirecting to Hidden Serivice in',
'Register': 'Zaregistrovať sa',
'Registration key': 'Registračný kľúč',
'Remember me (for 30 days)': 'Zapamätaj si ma (na 30 dní)',
'Reset Password key': 'Nastaviť registračný kľúč',
'Role': 'Rola',
'Rows in table': 'riadkov v tabuľke',
'Rows selected': 'označených riadkov',
'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Select Group:': 'Select Group:',
'Stats': 'Stats',
'Step': 'Step',
'Stylesheet': 'Stylesheet',
'Submission': 'Submission',
'Submission Interface': 'Submission Interface',
'Submission Receipt': 'Submission Receipt',
'Submission interface': 'Submission interface',
'Submission status': 'Submission status',
'Submit': 'Odoslať',
'Submit material': 'Submit material',
'Submit receipt': 'Submit receipt',
'Sure you want to delete this object?': 'Ste si istí, že chcete zmazať tento objekt?',
'Table name': 'Názov tabuľky',
'Tags': 'Tags',
'Targets': 'Targets',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': '"query" je podmienka ako "db.table1.field1==\'value\'". Niečo ako "db.table1.field1==db.table2.field2" má za výsledok SQL JOIN.',
'The output of the file is a dictionary that was rendered by the view': 'Výstup zo súboru je slovník, ktorý bol zobrazený vo view',
'This is a copy of the scaffolding application': 'Toto je kópia skeletu aplikácie',
'This is a number you should write down to keep track of your submission': 'This is a number you should write down to keep track of your submission',
'This is the material submitted by the whistleblower for your revision. You are invited to': 'This is the material submitted by the whistleblower for your revision. You are invited to',
'Timestamp': 'Časová pečiatka',
'Tip-off': 'Tip-off',
'Tip-off access statistics': 'Tip-off access statistics',
'Tip-off removed and all relatives': 'Tip-off removed and all relatives',
'Tulip': 'Tulip',
'Tulip Receipt': 'Tulip Receipt',
'Tulip access statistics': 'Tulip access statistics',
'Tulip removed and all relatives': 'Tulip removed and all relatives',
'Tulips': 'Tulips',
'Update:': 'Upraviť:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Použite (...)&(...) pre AND, (...)|(...) pre OR a ~(...) pre NOT na poskladanie komplexnejších otázok.',
'User %(id)s Logged-in': 'Používateľ %(id)s prihlásený',
'User %(id)s Logged-out': 'Používateľ %(id)s odhlásený',
'User %(id)s Password changed': 'Používateľ %(id)s zmenil heslo',
'User %(id)s Profile updated': 'Používateľ %(id)s upravil profil',
'User %(id)s Registered': 'Používateľ %(id)s sa zaregistroval',
'User ID': 'ID používateľa',
'Username': 'Username',
'Verify Password': 'Zopakujte heslo',
'View': 'Zobraziť',
'Views': 'Views',
'Warning': 'Warning',
'Welcome back Whistleblower: this TULIP interface is unique for you.': 'Welcome back Whistleblower: this TULIP interface is unique for you.',
'Welcome back Whistleblower: this interface is unique for you.': 'Welcome back Whistleblower: this interface is unique for you.',
'Welcome to web2py': 'Vitajte vo web2py',
'Which called the function': 'Ktorý zavolal funkciu',
'Whistleblower': 'Whistleblower',
'You are also able to use your Whistleblower receipt from the first page.': 'You are also able to use your Whistleblower receipt from the first page.',
'You are successfully running web2py': 'Úspešne ste spustili web2py',
'You can modify this application and adapt it to your needs': 'Môžete upraviť túto aplikáciu a prispôsobiť ju svojim potrebám',
'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.': 'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.',
'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.': 'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.',
'You visited the url': 'Navštívili ste URL',
"You've received a": "You've received a",
"You've received a Tulip...": "You've received a Tulip...",
'Your submission': 'Your submission',
'Your tip-off': 'Your tip-off',
'ZIP': 'ZIP',
'appadmin is disabled because insecure channel': 'appadmin je zakázaný bez zabezpečeného spojenia',
'cache': 'cache',
'check back later': 'check back later',
'customize me!': 'prispôsob ma!',
'data uploaded': 'údaje naplnené',
'database': 'databáza',
'database %s select': 'databáza %s výber',
'db': 'db',
'design': 'návrh',
'done!': 'hotovo!',
'export as csv file': 'exportovať do csv súboru',
'insert new': 'vložiť nový záznam ',
'insert new %s': 'vložiť nový  záznam %s',
'invalid receipt: Tip-off not found': 'invalid receipt: Tip-off not found',
'invalid receipt: Tulip not found': 'invalid receipt: Tulip not found',
'invalid request': 'Neplatná požiadavka',
'located in the file': 'nachádzajúci sa v súbore ',
'login': 'prihlásiť',
'logout': 'odhlásiť',
'lost password?': 'stratené heslo?',
'must accept disclaimer': 'must accept disclaimer',
'new record inserted': 'nový záznam bol vložený',
'next 100 rows': 'ďalších 100 riadkov',
'or import from csv file': 'alebo naimportovať z csv súboru',
'password': 'heslo',
'powered by': 'powered by',
'previous 100 rows': 'predchádzajúcich 100 riadkov',
'record': 'záznam',
'record does not exist': 'záznam neexistuje',
'record id': 'id záznamu',
'register': 'registrovať',
'seconds': 'seconds',
'selected': 'označených',
'state': 'stav',
'table': 'tabuľka',
'tulips': 'tulips',
'unable to parse csv file': 'nedá sa načítať csv súbor',
}

########NEW FILE########
__FILENAME__ = sr-sr
﻿# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN',
'%Y-%m-%d': '%Y-%m-%d',
'%Y-%m-%d %H:%M:%S': '%Y-%m-%d %H:%M:%S',
'Accept Disclaimer': 'Prihvati Ograničenja odgovornosti',
'Add': 'dodaj',
'Add Files': 'Dodaj dokumente',
'Add files': 'Додај dokumente',
'Analyze the received material, your work is fundamental in uncovering the truth': 'Analizirajte dobro materijal, Vaš rad je veoma bitan u otkrivanju istine',
'Are you sure you want to delete this object?': 'Da li ste sigurni da želite da obrišete ovaj dokument?',
'Ask useful details to the whistleblower thru the comment box': 'Pitajte Uzbunjivača kroz comment box',
'Available databases and tables': 'Raspoložive baze podataka i tabele',
'Bouquet': 'Bouquet',
'Cancel upload': 'Otkaži slanje',
'Cannot be empty': 'Ovo polje mora biti popunjeno',
'Client IP': 'IP adresa "klijenta" sta god to bilo',
'Comments': 'Komentari',
'Complete Download': 'Kompletan download',
'Config': 'Podešavanja',
'Current request': 'Aktuelni zahtev',
'Current response': 'Aktuelni odgovor',
'Current session': 'Aktuelna sesija',
'Delete Files': 'Obriši fajlove',
'Description': 'Opis',
'Done': 'Završeno',
'Download': 'Skini - Download',
'Downloads': 'Downloads',
'E-mail': 'E-mail',
'Edit current record': 'Edit current record',
'Encrypted ZIP': 'Šifrovana ZIP arhiva',
'Error: only ten digits are accepted as receipt': 'Greška: maksimalan broj cifara je 10',
'Error: you puts more than 10 digits': 'Greška: moguće je uneti maksimalno 10 cifara',
'Finish': 'Završi',
'First name': 'Ime',
'Forward to another receiver group': 'Prosledi još nekom mediju',
'Globalview': 'zbirni pregled',
'Group ID': 'Group ID',
'Groups': 'Groups',
'I want delete this tip-off and all the others derived from the same material': 'Želim da obrišem ovu dojavu i sve druge podatke u vezi sa tim materijalom',
'I want delete this tulip and all the tulips derived from the same material': 'Želim da obrišete ovu dojavu i sve druge podatke u vezi sa tim materijalom',
'ID': 'ID',
'Import/Export': 'Import/Export',
'Incomplete configuration': 'Incomplete configuration',
'Index': 'Index',
'Internal State': 'Internal State',
'Invalid email': 'Invalid email',
"It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.": "It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.",
'Language': 'језик',
'Last name': 'prezime',
'Logout': 'Odjavi se',
'Material': 'materijal',
'Material description': 'Opis materijala',
'Material has not been processed yet': 'Materijal još nije obrađen',
'Name': 'Naziv',
'New Record': 'New Record',
'Next': 'Sledeći',
'No comments': 'Nema komentara',
'No databases in this application': 'No databases in this application',
'Node View': 'Node View',
'Not spread this link. It is intended be for your eyes only': 'Ne prosleđujte nikome ovaj link. Namenjen je samo Vašim očima',
'Origin': 'Origin',
'PGP Encrypted ZIP': 'PGP Encrypted ZIP',
'Password': 'шифра',
'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)': 'Sačuvajte podatak na sigurnom mestu - npr. mobilnom telefonu, papiru..',
'Preferences': 'Podešavanja',
'Previous': 'Prethodna',
'Receiver': 'Primalac',
'Receivers': 'Primaoci',
'Record ID': 'Record ID',
'Redirecting to Hidden Serivice in': 'Preusmeravanje na "Sigurnu vezu"',
'Registration identifier': 'Registration identifier',
'Registration key': 'Registration key',
'Reset Password key': 'Reset Password key',
'Role': 'Role',
'Rows in table': 'Rows in table',
'Rows selected': 'Rows selected',
'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Sačuvajte ovaj broj, иначе ne postoji drugi način da proverite status svoje dojave i eventualno odgovorite na pitanja novinara u vezi sa dostavljenim informacijama.',
'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Sačuvajte ovaj broj, иначе ne postoji drugi način da proverite status svoje dojave i eventualno odgovorite na pitanja novinara u vezi sa dostavljenim informacijama.',
'Select Group:': 'Izaberite grupu:',
'Stats': 'Stats',
'Step': 'корак',
'Submission': 'Slanje',
'Submission Interface': 'Submission Interface',
'Submission Receipt': 'Potvrda prijema',
'Submission interface': 'Submission Interface',
'Submission status': 'Submission status',
'Submit material': 'pošalji materijal',
'Submit receipt': 'Pošalji kod',
'Table name': 'Table name',
'Tags': 'Tags',
'Targets': 'Targets',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.',
'This is a number you should write down to keep track of your submission': 'This is a number you should write down to keep track of your submission',
'This is the material submitted by the whistleblower for your revision. You are invited to': 'This is the material submitted by the whistleblower for your revision. You are invited to',
'Timestamp': 'Timestamp',
'Tip-off': 'Savet',
'Tip-off access statistics': 'Tip-off access statistics',
'Tip-off removed and all relatives': 'Tip-off removed and all relatives',
'Tulip': 'Dojava',
'Tulip Receipt': 'Potvrda o primljenoj dojavi',
'Tulip access statistics': 'Tulip access statistics',
'Tulip removed and all relatives': 'Kompletan materijal je uklonjen',
'Tulips': 'Tulips',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.',
'User ID': 'User ID',
'Username': 'Username',
'Views': 'Views',
'Warning': 'Upozorenje',
'Welcome back Whistleblower: this TULIP interface is unique for you.': 'Dobrodošli ponovo. Ova stranica je potpuno jedinstvena za Vas.',
'Welcome back Whistleblower: this interface is unique for you.': 'Dobrodošli ponovo. Ova stranica je potpuno jedinstvena za Vas.',
'Whistleblower': 'Uzbunjivač',
'You are also able to use your Whistleblower receipt from the first page.': 'Takođe ste u mogućnosti da koristite Vaš račun Uzbunjivača sa prve stranice.',
'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.': 'Imate mogućnost da obrišete sav dostavljeni materijal.',
'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.': 'Imate mogućnost da obrišete sav dostavljeni materijal.',
"You've received a": 'Dobili ste',
"You've received a Tulip...": 'Dobili ste dojavu',
'Your submission': 'Vaše slanje',
'Your tip-off': 'Vaša dojava',
'ZIP': 'ZIP',
'check back later': 'proverite kasnije',
'database': 'database',
'database %s select': 'database %s select',
'enter an integer between %(min)g and %(max)g': 'enter an integer between %(min)g and %(max)g',
'export as csv file': 'export as csv file',
'insert new': 'insert new',
'insert new %s': 'insert new %s',
'invalid receipt: Tip-off not found': 'Pogrešan broj: ne postoji dojava pod tim brojem.',
'invalid receipt: Tulip not found': 'Pogrešan broj: ne postoji dojava pod tim brojem.',
'must accept disclaimer': 'Morate prihvatiti Uslove korišćenja',
'next 100 rows': 'next 100 rows',
'or import from csv file': 'or import from csv file',
'powered by': 'powered by',
'previous 100 rows': 'previous 100 rows',
'record': 'record',
'record id': 'record id',
'seconds': 'seconds',
'selected': 'selected',
'table': 'table',
'tulips': 'dojave',
}

########NEW FILE########
__FILENAME__ = sr
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN',
'%Y-%m-%d': '%Y-%m-%d',
'%Y-%m-%d %H:%M:%S': '%Y-%m-%d %H:%M:%S',
'About': 'About',
'Accept Disclaimer': 'Prihvati Ograničenja odgovornosti',
'Add': 'dodaj',
'Add Files': 'Dodaj dokumente',
'Add files': 'Додај dokumente',
'Already Submitted?': 'Already Submitted?',
'Analyze the received material, your work is fundamental in uncovering the truth': 'Analizirajte dobro materijal, Vaš rad je veoma bitan u otkrivanju istine',
'Are you sure you want to delete this object?': 'Da li ste sigurni da želite da obrišete ovaj dokument?',
'Ask useful details to the whistleblower thru the comment box': 'Pitajte Uzbunjivača kroz comment box',
'Available databases and tables': 'Raspoložive baze podataka i tabele',
'Back to top': 'Back to top',
'Bouquet': 'Bouquet',
'Cancel upload': 'Otkaži slanje',
'Cannot be empty': 'Ovo polje mora biti popunjeno',
'Check your status here': 'Check your status here',
'Client IP': 'IP adresa "klijenta" sta god to bilo',
'Comments': 'Komentari',
'Complete Download': 'Kompletan download',
'Config': 'Podešavanja',
'Current request': 'Aktuelni zahtev',
'Current response': 'Aktuelni odgovor',
'Current session': 'Aktuelna sesija',
'Delete Files': 'Obriši fajlove',
'Description': 'Opis',
'Disclaimer': 'Disclaimer',
'Done': 'Završeno',
'Download': 'Skini - Download',
'Downloads': 'Downloads',
'E-mail': 'E-mail',
'Edit current record': 'Edit current record',
'Encrypted ZIP': 'Šifrovana ZIP arhiva',
'Error: only ten digits are accepted as receipt': 'Greška: maksimalan broj cifara je 10',
'Error: you puts more than 10 digits': 'Greška: moguće je uneti maksimalno 10 cifara',
'Finish': 'Završi',
'First name': 'Ime',
'Forward to another receiver group': 'Prosledi još nekom mediju',
'Globalview': 'zbirni pregled',
'Group ID': 'Group ID',
'Groups': 'Groups',
'I want delete this tip-off and all the others derived from the same material': 'Želim da obrišem ovu dojavu i sve druge podatke u vezi sa tim materijalom',
'I want delete this tulip and all the tulips derived from the same material': 'Želim da obrišete ovu dojavu i sve druge podatke u vezi sa tim materijalom',
'ID': 'ID',
'Import/Export': 'Import/Export',
'Incomplete configuration': 'Incomplete configuration',
'Index': 'Index',
'Internal State': 'Internal State',
'Invalid email': 'Invalid email',
"It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.": "It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.",
'Language': 'језик',
'Last name': 'prezime',
'Logout': 'Odjavi se',
'Material': 'materijal',
'Material description': 'Opis materijala',
'Material has not been processed yet': 'Materijal još nije obrađen',
'Name': 'Naziv',
'New Record': 'New Record',
'Next': 'Sledeći',
'No comments': 'Nema komentara',
'No databases in this application': 'No databases in this application',
'Node View': 'Node View',
'Not spread this link. It is intended be for your eyes only': 'Ne prosleđujte nikome ovaj link. Namenjen je samo Vašim očima',
'Origin': 'Origin',
'PGP Encrypted ZIP': 'PGP Encrypted ZIP',
'Password': 'шифра',
'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)': 'Sačuvajte podatak na sigurnom mestu - npr. mobilnom telefonu, papiru..',
'Preferences': 'Podešavanja',
'Previous': 'Prethodna',
'Receiver': 'Primalac',
'Receivers': 'Primaoci',
'Record ID': 'Record ID',
'Redirecting to Hidden Serivice in': 'Preusmeravanje na "Sigurnu vezu"',
'Registration identifier': 'Registration identifier',
'Registration key': 'Registration key',
'Reset Password key': 'Reset Password key',
'Role': 'Role',
'Rows in table': 'Rows in table',
'Rows selected': 'Rows selected',
'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Sačuvajte ovaj broj, иначе ne postoji drugi način da proverite status svoje dojave i eventualno odgovorite na pitanja novinara u vezi sa dostavljenim informacijama.',
'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Sačuvajte ovaj broj, иначе ne postoji drugi način da proverite status svoje dojave i eventualno odgovorite na pitanja novinara u vezi sa dostavljenim informacijama.',
'Select Group:': 'Izaberite grupu:',
'Stats': 'Stats',
'Step': 'корак',
'Submission': 'Slanje',
'Submission Interface': 'Submission Interface',
'Submission Receipt': 'Potvrda prijema',
'Submission interface': 'Submission Interface',
'Submission status': 'Submission status',
'Submit material': 'pošalji materijal',
'Submit receipt': 'Pošalji kod',
'Table name': 'Table name',
'Tags': 'Tags',
'Targets': 'Targets',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.',
'This is a number you should write down to keep track of your submission': 'This is a number you should write down to keep track of your submission',
'This is the material submitted by the whistleblower for your revision. You are invited to': 'This is the material submitted by the whistleblower for your revision. You are invited to',
'Timestamp': 'Timestamp',
'Tip-off': 'Savet',
'Tip-off access statistics': 'Tip-off access statistics',
'Tip-off removed and all relatives': 'Tip-off removed and all relatives',
'Tulip': 'Dojava',
'Tulip Receipt': 'Potvrda o primljenoj dojavi',
'Tulip access statistics': 'Tulip access statistics',
'Tulip removed and all relatives': 'Kompletan materijal je uklonjen',
'Tulips': 'Tulips',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.',
'User ID': 'User ID',
'Username': 'Username',
'Views': 'Views',
'Warning': 'Upozorenje',
'Welcome back Whistleblower: this TULIP interface is unique for you.': 'Dobrodošli ponovo. Ova stranica je potpuno jedinstvena za Vas.',
'Welcome back Whistleblower: this interface is unique for you.': 'Dobrodošli ponovo. Ova stranica je potpuno jedinstvena za Vas.',
'Welcome to': 'Welcome to',
'Whistleblower': 'Uzbunjivač',
'Why use Tor?': 'Why use Tor?',
'You are also able to use your Whistleblower receipt from the first page.': 'Takođe ste u mogućnosti da koristite Vaš račun Uzbunjivača sa prve stranice.',
'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.': 'Imate mogućnost da obrišete sav dostavljeni materijal.',
'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.': 'Imate mogućnost da obrišete sav dostavljeni materijal.',
"You've received a": 'Dobili ste',
"You've received a Tulip...": 'Dobili ste dojavu',
'Your submission': 'Vaše slanje',
'Your tip-off': 'Vaša dojava',
'ZIP': 'ZIP',
'check back later': 'proverite kasnije',
'database': 'database',
'database %s select': 'database %s select',
'enter a value': 'enter a value',
'enter an integer between %(min)g and %(max)g': 'enter an integer between %(min)g and %(max)g',
'export as csv file': 'export as csv file',
'insert new': 'insert new',
'insert new %s': 'insert new %s',
'invalid receipt: Tip-off not found': 'Pogrešan broj: ne postoji dojava pod tim brojem.',
'invalid receipt: Tulip not found': 'Pogrešan broj: ne postoji dojava pod tim brojem.',
'must accept disclaimer': 'Morate prihvatiti Uslove korišćenja',
'next 100 rows': 'next 100 rows',
'or import from csv file': 'or import from csv file',
'powered by': 'powered by',
'previous 100 rows': 'previous 100 rows',
'record': 'record',
'record id': 'record id',
'seconds': 'seconds',
'selected': 'selected',
'submit': 'submit',
'table': 'table',
'tulips': 'dojave',
}

########NEW FILE########
__FILENAME__ = zh-tw
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"更新" 是選擇性的條件式, 格式就像 "欄位1=\'值\'". 但是 JOIN 的資料不可以使用 update 或是 delete"',
'%Y-%m-%d': '%Y-%m-%d',
'%Y-%m-%d %H:%M:%S': '%Y-%m-%d %H:%M:%S',
'%s rows deleted': '已刪除 %s 筆',
'%s rows updated': '已更新 %s 筆',
'(something like "it-it")': '(格式類似 "zh-tw")',
'A new version of web2py is available': '新版的 web2py 已發行',
'A new version of web2py is available: %s': '新版的 web2py 已發行: %s',
'ATTENTION: Login requires a secure (HTTPS) connection or running on localhost.': '注意: 登入管理帳號需要安全連線(HTTPS)或是在本機連線(localhost).',
'ATTENTION: TESTING IS NOT THREAD SAFE SO DO NOT PERFORM MULTIPLE TESTS CONCURRENTLY.': '注意: 因為在測試模式不保證多執行緒安全性，也就是說不可以同時執行多個測試案例',
'ATTENTION: you cannot edit the running application!': '注意:不可編輯正在執行的應用程式!',
'About': '關於',
'About application': '關於本應用程式',
'Accept Disclaimer': 'Accept Disclaimer',
'Add': 'Add',
'Add Files': 'Add Files',
'Add files': 'Add files',
'Admin is disabled because insecure channel': '管理功能(Admin)在不安全連線環境下自動關閉',
'Admin is disabled because unsecure channel': '管理功能(Admin)在不安全連線環境下自動關閉',
'Administrative interface': '點此處進入管理介面',
'Administrator Password:': '管理員密碼:',
'Analyze the received material, your work is fundamental in uncovering the truth': 'Analyze the received material, your work is fundamental in uncovering the truth',
'Are you sure you want to delete file "%s"?': '確定要刪除檔案"%s"?',
'Are you sure you want to delete this object?': 'Are you sure you want to delete this object?',
'Are you sure you want to uninstall application "%s"': '確定要移除應用程式 "%s"',
'Are you sure you want to uninstall application "%s"?': '確定要移除應用程式 "%s"',
'Ask useful details to the whistleblower thru the comment box': 'Ask useful details to the whistleblower thru the comment box',
'Authentication': '驗證',
'Available databases and tables': '可提供的資料庫和資料表',
'Bouquet': 'Bouquet',
'Cancel upload': 'Cancel upload',
'Cannot be empty': '不可空白',
'Cannot compile: there are errors in your app.        Debug it, correct errors and try again.': '無法編譯:應用程式中含有錯誤，請除錯後再試一次.',
'Change Password': '變更密碼',
'Check to delete': '打勾代表刪除',
'Check to delete:': '點選以示刪除:',
'Client IP': '客戶端網址(IP)',
'Comments': 'Comments',
'Complete Download': 'Complete Download',
'Config': 'Config',
'Controller': '控件',
'Controllers': '控件',
'Copyright': '版權所有',
'Create new application': '創建應用程式',
'Current request': '目前網路資料要求(request)',
'Current response': '目前網路資料回應(response)',
'Current session': '目前網路連線資訊(session)',
'DB Model': '資料庫模組',
'DESIGN': '設計',
'Database': '資料庫',
'Date and Time': '日期和時間',
'Delete': '刪除',
'Delete Files': 'Delete Files',
'Delete:': '刪除:',
'Deploy on Google App Engine': '配置到 Google App Engine',
'Description': '描述',
'Design for': '設計為了',
'Done': 'Done',
'Download': 'Download',
'Downloads': 'Downloads',
'E-mail': '電子郵件',
'EDIT': '編輯',
'Edit': '編輯',
'Edit Profile': '編輯設定檔',
'Edit This App': '編輯本應用程式',
'Edit application': '編輯應用程式',
'Edit current record': '編輯當前紀錄',
'Editing file': '編輯檔案',
'Editing file "%s"': '編輯檔案"%s"',
'Encrypted ZIP': 'Encrypted ZIP',
'Error logs for "%(app)s"': '"%(app)s"的錯誤紀錄',
'Error: only ten digits are accepted as receipt': 'Error: only ten digits are accepted as receipt',
'Error: you puts more than 10 digits': 'Error: you puts more than 10 digits',
'Finish': 'Finish',
'First name': '名',
'Forward to another receiver group': 'Forward to another receiver group',
'Functions with no doctests will result in [passed] tests.': '沒有 doctests 的函式會顯示 [passed].',
'Globalview': 'Globalview',
'Group ID': '群組編號',
'Groups': 'Groups',
'Hello World': '嗨! 世界',
'I want delete this tip-off and all the others derived from the same material': 'I want delete this tip-off and all the others derived from the same material',
'I want delete this tulip and all the tulips derived from the same material': 'I want delete this tulip and all the tulips derived from the same material',
'ID': 'ID',
'Import/Export': '匯入/匯出',
'Incomplete configuration': 'Incomplete configuration',
'Index': '索引',
'Installed applications': '已安裝應用程式',
'Internal State': '內部狀態',
'Invalid Query': '不合法的查詢',
'Invalid action': '不合法的動作(action)',
'Invalid email': '不合法的電子郵件',
"It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.": "It's required that almost one receiver group has been configured from the administrative panel, in order to accept whistleblowing submission.",
'Language': 'Language',
'Language files (static strings) updated': '語言檔已更新',
'Languages': '各國語言',
'Last name': '姓',
'Last saved on:': '最後儲存時間:',
'Layout': '網頁配置',
'License for': '軟體版權為',
'Login': '登入',
'Login to the Administrative Interface': '登入到管理員介面',
'Logout': '登出',
'Lost Password': '密碼遺忘',
'Main Menu': '主選單',
'Material': 'Material',
'Material description': 'Material description',
'Material has not been processed yet': 'Material has not been processed yet',
'Menu Model': '選單模組(menu)',
'Models': '資料模組',
'Modules': '程式模組',
'NO': '否',
'Name': '名字',
'New Record': '新紀錄',
'Next': 'Next',
'No comments': 'No comments',
'No databases in this application': '這應用程式不含資料庫',
'Node View': 'Node View',
'Not spread this link. It is intended be for your eyes only': 'Not spread this link. It is intended be for your eyes only',
'Online examples': '點此處進入線上範例',
'Origin': '原文',
'Original/Translation': '原文/翻譯',
'PGP Encrypted ZIP': 'PGP Encrypted ZIP',
'Password': '密碼',
"Password fields don't match": '密碼欄不匹配',
'Peeking at file': '選擇檔案',
'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)': 'Please save it in a safe place (e.x. mobile phone, piece of paper, etc.)',
'Powered by': '基於以下技術構建：',
'Preferences': 'Preferences',
'Previous': 'Previous',
'Query:': '查詢:',
'Receiver': 'Receiver',
'Receivers': 'Receivers',
'Record ID': '紀錄編號',
'Redirecting to Hidden Serivice in': 'Redirecting to Hidden Serivice in',
'Register': '註冊',
'Registration key': '註冊金鑰',
'Remember me (for 30 days)': '記住我(30 天)',
'Reset Password key': '重設密碼',
'Resolve Conflict file': '解決衝突檔案',
'Role': '角色',
'Rows in table': '在資料表裏的資料',
'Rows selected': '筆資料被選擇',
'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tip-off link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.': 'Save the following number or the Tulip link: otherwise you could not have other ways to come back here, and comment your submitted information.',
'Saved file hash:': '檔案雜湊值已紀錄:',
'Select Group:': 'Select Group:',
'Static files': '靜態檔案',
'Stats': 'Stats',
'Step': 'Step',
'Stylesheet': '網頁風格檔',
'Submission': 'Submission',
'Submission Interface': 'Submission Interface',
'Submission Receipt': 'Submission Receipt',
'Submission interface': 'Submission interface',
'Submission status': 'Submission status',
'Submit': '傳送',
'Submit material': 'Submit material',
'Submit receipt': 'Submit receipt',
'Sure you want to delete this object?': '確定要刪除此物件?',
'Table name': '資料表名稱',
'Tags': 'Tags',
'Targets': 'Targets',
'Testing application': '測試中的應用程式',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': '"查詢"是一個像 "db.表1.欄位1==\'值\'" 的條件式. 以"db.表1.欄位1==db.表2.欄位2"方式則相當於執行 JOIN SQL.',
'There are no controllers': '沒有控件(controllers)',
'There are no models': '沒有資料庫模組(models)',
'There are no modules': '沒有程式模組(modules)',
'There are no static files': '沒有靜態檔案',
'There are no translators, only default language is supported': '沒有翻譯檔,只支援原始語言',
'There are no views': '沒有視圖',
'This is a number you should write down to keep track of your submission': 'This is a number you should write down to keep track of your submission',
'This is the %(filename)s template': '這是%(filename)s檔案的樣板(template)',
'This is the material submitted by the whistleblower for your revision. You are invited to': 'This is the material submitted by the whistleblower for your revision. You are invited to',
'Ticket': '問題單',
'Timestamp': '時間標記',
'Tip-off': 'Tip-off',
'Tip-off access statistics': 'Tip-off access statistics',
'Tip-off removed and all relatives': 'Tip-off removed and all relatives',
'Tulip': 'Tulip',
'Tulip Receipt': 'Tulip Receipt',
'Tulip access statistics': 'Tulip access statistics',
'Tulip removed and all relatives': 'Tulip removed and all relatives',
'Tulips': 'Tulips',
'Unable to check for upgrades': '無法做升級檢查',
'Unable to download': '無法下載',
'Unable to download app': '無法下載應用程式',
'Update:': '更新:',
'Upload existing application': '更新存在的應用程式',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': '使用下列方式來組合更複雜的條件式, (...)&(...) 代表同時存在的條件, (...)|(...) 代表擇一的條件, ~(...)則代表反向條件.',
'User %(id)s Logged-in': '使用者 %(id)s 已登入',
'User %(id)s Registered': '使用者 %(id)s 已註冊',
'User ID': '使用者編號',
'Username': 'Username',
'Verify Password': '驗證密碼',
'View': '視圖',
'Views': '視圖',
'Warning': 'Warning',
'Welcome %s': '歡迎 %s',
'Welcome back Whistleblower: this TULIP interface is unique for you.': 'Welcome back Whistleblower: this TULIP interface is unique for you.',
'Welcome back Whistleblower: this interface is unique for you.': 'Welcome back Whistleblower: this interface is unique for you.',
'Welcome to web2py': '歡迎使用 web2py',
'Whistleblower': 'Whistleblower',
'YES': '是',
'You are also able to use your Whistleblower receipt from the first page.': 'You are also able to use your Whistleblower receipt from the first page.',
'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.': 'You have the right to delete this submitted material. This effect delete also all the related Tip-off for the other receivers.',
'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.': 'You have the right to delete this submitted material. This effect delete also all the related Tulips for the other receiver.',
"You've received a": "You've received a",
"You've received a Tulip...": "You've received a Tulip...",
'Your submission': 'Your submission',
'Your tip-off': 'Your tip-off',
'ZIP': 'ZIP',
'about': '關於',
'appadmin is disabled because insecure channel': '因為來自非安全通道,管理介面關閉',
'cache': '快取記憶體',
'change password': '變更密碼',
'check back later': 'check back later',
'customize me!': '請調整我!',
'data uploaded': '資料已上傳',
'database': '資料庫',
'database %s select': '已選擇 %s 資料庫',
'db': 'db',
'design': '設計',
'done!': '完成!',
'edit profile': '編輯設定檔',
'export as csv file': '以逗號分隔檔(csv)格式匯出',
'insert new': '插入新資料',
'insert new %s': '插入新資料 %s',
'invalid receipt: Tip-off not found': 'invalid receipt: Tip-off not found',
'invalid receipt: Tulip not found': 'invalid receipt: Tulip not found',
'invalid request': '不合法的網路要求(request)',
'login': '登入',
'logout': '登出',
'must accept disclaimer': 'must accept disclaimer',
'new record inserted': '已插入新紀錄',
'next 100 rows': '往後 100 筆',
'or import from csv file': '或是從逗號分隔檔(CSV)匯入',
'powered by': 'powered by',
'previous 100 rows': '往前 100 筆',
'record': '紀錄',
'record does not exist': '紀錄不存在',
'record id': '紀錄編號',
'register': '註冊',
'seconds': 'seconds',
'selected': '已選擇',
'state': '狀態',
'table': '資料表',
'tulips': 'tulips',
'unable to parse csv file': '無法解析逗號分隔檔(csv)',
}

########NEW FILE########
__FILENAME__ = 00_settings
import ConfigParser
import os.path

from gluon.storage import Storage
from config import ConfigFile, cfgfile

class ThreadSafe(dict):
    forever=10**10
    def __init__(self):
         import thread
         self['lock']=thread.allocate_lock()
    def __setattr__(self,key,value):
         self['lock'].acquire()
         self[key]=value
         self['lock'].release()
    def __getattr__(self,key):
         self['lock'].acquire()
         value=self[key]
         self['lock'].release()
         return value

#x=cache.ram('elefante_in_sala_server',lambda:ThreadSafe(),ThreadSafe.forever)


################################################################
# Import the database and global settings from the config file #
################################################################
settings = Storage()
settings.globals = ConfigFile(cfgfile, 'global')
settings.database = ConfigFile(cfgfile, 'database')

response.headers.pop('X-Powered-By')
response.headers['Server'] = settings.globals.servername

default_lang = settings.globals.language
T.set_current_languages(default_lang, default_lang)
plugin_translate_current_language = default_lang
session._language = request.vars._language or session._language or plugin_translate_current_language
T.force(str(session._language))


########NEW FILE########
__FILENAME__ = 010_language
# Language settings
languages = settings.globals.supported_languages.split("|")
supported_languages = []
for l in languages:
    x = l.split(",")
    supported_languages.append((x[0].strip(),x[1].strip()))

# disable google translate "feature"
if T.accepted_language != session._language and 0:
    import re
    lang = re.compile('\w{2}').findall(session._language)[0]
    a = URL(r=request,c='static',f='plugin_translate/jquery.translate-1.4.3-debug-all.js')
    b = URL(r=request,c='plugin_translate',f='translate',args=lang+'.js')
    response.files.append(a)
    response.files.append(b)

def plugin_translate(languages=supported_languages):
    ret = []
    for v,k in languages:
        current = False
        if v == session._language:
            current = True
        ret.append({'url':
                    "%s?_language=%s" % (URL(r=request, args=request.args), v),
                    'name': v, 'current': current})
    return ret

    #return FORM(LI(
    #        _href="document.location='%s?_language='+jQuery(this).val()" \
    #            % URL(r=request,args=request.args),
    #        value=session._language,
    #        *[OPTION(k,_value=v) for v,k in languages]))

# Template internationalization
def localize_templates(name, lang='it'):
    fn = settings.globals.__getattr__(name).split(".")
    try:
        template_file = ".".join(fn[:-1]) + "-" + lang + "." + fn[-1]
        full_path = os.path.join(request.folder, "../../", template_file)
        if os.path.exists(full_path):
            pass
        else:
            template_file =  ".".join(fn[:-1]) + "." + fn[-1]
        settings.globals.__setattr__(name, template_file)
        fp = open(template_file, "r")
        content = fp.read()
    except:
        pass

for x in ["presentation_file", "disclaimer_file", "whistleblower_file",
"not_anonymous_file", "extrafields_wizard", "disclaimer_long_file"]:
    localize_templates(x, lang=session._language)

########NEW FILE########
__FILENAME__ = 01_db
"""
Define the main globaleaks database structure.
"""

db = DAL(settings.database.uri)


db.define_table('target',
    Field('name'),
    Field('hidden', writable=False, readable=False),
    Field('desc'),
    Field('contact_type', writable=False, readable=False), 
                            # this in the future need to be the trigger of external module loading
                            # with external database loading (e.g.: gpg key, ssh key, notification and
                            # material delivery treat and configured separately, etc).
    Field('contact'),
    Field('type', writable=False, readable=False),
    # security supports - configurable by Bouquet page
    Field('password'),
    Field('password_enabled', 'boolean'),
    Field('pgpkey'),
    Field('pgpkey_enabled', 'boolean'),
    # end of security supports
    Field('info'),
    Field('candelete', writable=False),     
                            # remove capability: the capability of a receiver could be managed with a
                            # bitmask, like contact_type in the future need to be. during the development
                            # other capability might be request, could be useful provide here a flexible
                            # interface
    Field('last_sent_tulip', writable=False),
    Field('last_access', writable=False),
    Field('last_download', writable=False),
    Field('tulip_counter', writable=False),
    Field('download_counter', writable=False),
    format='%(name)s'
    )

# The table for target groups
db.define_table('targetgroup',
    Field('name', unique=True),
    Field('desc'),
    Field('tags'),
    Field('targets'),
    format='%(name)s'
    )

# XXX
# Merge with submission, all references of the term "leak"
# should be removed and replaced with submission
from xml.dom.minidom import parse, parseString
from pprint import pprint

class ExtraField:
    def __init__(self, filename):
        from xml.dom.minidom import parse, parseString
        from pprint import pprint

        file = open(filename)
        dom = parse(file)
        self.dom = dom
        self.wizard = False

        self.step_desc = []
        self.fields = []

        if dom.getElementsByTagName("wizard"):
            self.wizard = True

        for i in dom.getElementsByTagName("field"):
            self.fields.append(self.parse_field(i))

    def get_content(self, field, tag):
        return field.getElementsByTagName(tag)[0].childNodes[0].data

    def parse_list(self, field):
        list = []
        for el in field.getElementsByTagName("el"):
            list.append(el.childNodes[0].data)
        return list

    def parse_field(self, field):
        parsed = {}
        parsed['name'] = self.get_content(field, "name")
        parsed['label'] = self.get_content(field, "label")
        parsed['desc']  = self.get_content(field, "description")
        parsed['type']  = self.get_content(field, "type")
        if parsed['type'] == "list":
            parsed['list'] = self.parse_list(field)
        return parsed

    def get_step(self, el):
        return el.getAttributeNode("number").value

    def get_step_n(self, steps, n):
        for step in steps:
            if self.get_step(step) == n:
                return step
        return None

    def parse_step(self, step):
        steps = []

        for node in step.childNodes:
            if node.nodeName == "field":
                steps.append(self.parse_field(node))
            elif node.nodeName == "material":
                steps.append("material")
            elif node.nodeName == "grouplist":
                steps.append("grouplist")
            elif node.nodeName == "disclaimer":
                steps.append("disclaimer")
            elif node.nodeName == "disclaimer_info":
                steps.append("disclaimer_info")
            elif node.nodeName == "captcha":
                steps.append("captcha")
            elif node.nodeName == "p":
                self.step_desc.append(node.childNodes[0].data)

        return steps

    def gen_wizard(self):
        steps = self.dom.getElementsByTagName("step")

        wizard = []

        for i in range(0, len(steps)):
            nstep = self.get_step_n(steps, i+1)
            if nstep:
                wizard.append(self.parse_step(nstep))
            else:
                wizard.append(self.parse_step(steps[i]))

        return wizard

    def gen_db(self):
        if self.fields:
            output = []
            for i in self.fields:
                if i['type'] == "list":
                    output.append(Field(str(i['name']),requires=IS_IN_SET(i['list'])))
                    #output.append((str(i['name']), i['list']))
                else:
                    output.append(Field(str(i['name']), str(i['type'])))
                    #output.append((str(i['name']), str(i['type'])))
            return output

#extrafile = os.path.join(os.path.dirname(__file__), 'extrafields_wizard.xml')
extrafile = os.path.join(request.folder, "../../", settings.globals.extrafields_wizard)
extrafields = ExtraField(extrafile)
settings.extrafields = extrafields

db_extrafields = extrafields.gen_db()

db.define_table('leak',
    Field('title', requires=IS_NOT_EMPTY()),
    Field('desc', 'text', requires=IS_NOT_EMPTY()),
    Field('submission_timestamp'),
    Field('leaker_id', db.target),
    Field('whistleblower_access'),
    Field('notified_groups'),
    Field('spooled', 'boolean', False),
    *db_extrafields,
    format='%(name)s'
)

db.define_table('comment',
    Field('leak_id', db.leak),
    Field('commenter_name'),
    Field('commenter_id'),
    Field('comment'),
    format='%(name)s'
)

db.define_table('material',
    Field('url'), #, unique=True),
    Field('leak_id', db.leak),
    Field('type'),
    Field('async_id'),
    Field('description'),
    Field('details'),
    Field('file'),
    format='%(name)s'
)

db.define_table('tulip',
    Field('url', unique=True),
    Field('leak_id', db.leak),
    Field('target_id'),
    Field('feedbacks_provided'),
    Field('allowed_accesses'),
    Field('accesses_counter'),
    Field('allowed_downloads'),
    Field('downloads_counter'),
    Field('expiry_time'),
    format='%(name)s'
    )

# XXX
# Probably there is a better solution for spooling email
db.define_table('mail',
    Field('target'),
    Field('address'),
    Field('tulip', unique=True),
    format='%(name)s'
)

# XXX
# Merge this with leak
db.define_table('submission',
    Field('session', unique=True),
    Field('leak_id'),
    Field('dirname'),
    format='%(name)s'
)

# XXX
# This should be merged with the above
# Notification table to keep track of notifications to be sent to targets.
db.define_table('notification',
                Field('target'),
                Field('address'),
                Field('tulip'),
                Field('leak_id'),
                Field('type'),
                format='%(name)s'
)


########NEW FILE########
__FILENAME__ = 02_globaleaks
import randomizer
import time

class Globaleaks(object):
    """
    Class that contains useful CRUD methods
    """

    def __init__(self):
        self._db = db
        # I'm sorry about this, but seem that in the logic of 2_init.py
        # seem that 'settings' is not usable here

    def create_targetgroup(self, name, desc, tags, targets=None):
        """
        Creates a new targetgroup.
        Returns the id of the new record.
        """
        # http://zimbabwenewsonline.com/top_news/2495.html 
        prev_row = self._db(self._db.targetgroup.name==name).select().first()
        if prev_row:
            self._db.targetgroup.update(id=prev_row.id, name=name, desc=desc,
                                              tags=tags, targets=targets)
            ret_id = prev_row.id
        else:
            ret_id = self._db.targetgroup.insert(name=name, desc=desc,
                                              tags=tags, targets=targets)

        self._db.commit()
        return ret_id

    def delete_targetgroup(self, group_id):
        """
        Deletes the targetgroup with the specified id.
        Returns True if the operation was successful.
        """
        result = False
        if self._db(self._db.targetgroup.id==group_id).select():
            result = True
            self._db(self._db.targetgroup.id==group_id).delete()
        self._db.commit()
        return result

    def update_targetgroup(self, group_id, **kwargs):
        """
        Changes the name field of the targetgroup with the specified id.
        """
        result = False
        if self._db(self._db.targetgroup.id==group_id).select():
            result = True
            self._db(self._db.targetgroup.id==group_id).update(**kwargs)
            self._db.commit()
        return result

    def get_group_id(self, group_name):
        return self._db(self._db.targetgroup.name==group_name
                       ).select().first().id

    def add_to_targetgroup(self, target_id, group_id=None, group_name=None):
        """
        Adds the target with id target_id to the targetgroup with id
        group_id.
        Returns True if the operation was successful
        """
        if group_name:
            group_id = self.get_group_id(group_name)
        target_row = self._db(self._db.target.id==target_id).select().first()
        group_row = self._db(self._db.targetgroup.id==group_id
                            ).select().first()
        result = False
        if target_row is not None and group_row is not None:
            targets_j = group_row.targets
            if not targets_j:
                # Dumps the json to the group table
                targets_j = json.dumps([target_id])
            else:
                tmp_j = json.loads(targets_j)
                tmp_j.append(target_id)
                targets_j = json.dumps(tmp_j)
            result = self._db(self._db.targetgroup.id==group_id
                             ).update(targets=targets_j)
            self._db.commit()

        return result

    def remove_from_targetgroup(self, target_id, group_id):
        """
        Removes a target from a group.
        Returns True if the operation was successful.
        """
        target_row = self._db(self._db.target.id==target_id).select().first()
        group_row = self._db(self._db.targetgroup.id==group_id
                            ).select().first()
        result = False
        if target_row is not None and group_row is not None:
            result = True
            targets_j = group_row.targets

            if not targets_j:
                targets_j = json.dumps([target_id])
            else:
                tmp = json.loads(targets_j)
                tmp.remove(target_id)
                targets_j = json.dumps(tmp)

            self._db(self._db.targetgroup.id==group_id
                    ).update(targets=targets_j)
            self._db.commit()
        return result

    def get_targetgroups(self):
        """
        Returns a dictionary that has the targetgroup ids as keys and
        another dictionary as value.
        This second dictionary has field "data" with group data and
        field "members" which is a list of targets that belong to that
        group.
        """
        result = {}
        for row in self._db().select(self._db.targetgroup.ALL):
            result[row.id] = {}
            result[row.id]["data"] = dict(row)
            result[row.id]["members"] = []
            try:
                members = result[row.id]["data"]['targets']
                for member in json.loads(members):
                    member_data = self._db(self._db.target.id==int(member)
                                          ).select().first()
                    result[row.id]["members"].append(dict(member_data))
            except:
                result[row.id]["members"] = []
        return result

    # by default, a target is inserted with an email type only as contact_type,
    # in the personal page, the receiver should change that or the contact type
    # (eg: facebook, irc ?, encrypted mail setting up a gpg pubkey)
    def create_target(self, name, group_name, desc, contact_mail, could_del):
        """
        Creates a new target with the specified parameters.
        Returns the id of the new record.

        |contact_type| supported values: [email]
        |type| supported values: [plain*|pgp]
        |could_del|: true or false*, mean: could delete material
        |group_name|: could be specified a single group name only

        * = default
        """

        target_id = self._db.target.insert(name=name,
            desc=desc, contact_type="email",
            contact=contact_mail, type="plain", info="",
            candelete=could_del, tulip_counter=0,
            download_counter=0)
        self._db.commit()

        # extract the ID of the request group, if any, of found the default, if supported
        requested_group = group_name if group_name else settings['globals'].default_group
        if requested_group:
            group_id = self.get_group_id(requested_group)
            group_row = self._db(self._db.targetgroup.id==group_id).select().first()

            if group_row['targets']:
                comrades = json.loads(group_row['targets'])
                comrades.append(target_id)
                self.update_targetgroup(group_id, targets=json.dumps(comrades))
            else:
                starting_json = '["' + str(target_id) + '"]'
                self.update_targetgroup(group_id, targets=starting_json)

        return target_id

    def delete_target(self, target_id):
        """
        Deletes a target.
        """
        self._db(self._db.target.id==target_id).delete()
        return True

    def delete_tulips_by_target(target_id):
        """
        Delete the tulips associated to a single target
        """
        associated_tulips = self._db().select(self._db.tulip.target_id==target_id)
        tulips_removed = 0
        for single_tulip in associated_tulips:
            tulips_removed += 1
            self._db(self._db.tulip.id==single_tulip.it).delete()
        return tulips_removed 

    def get_targets(self, group_set, target_set=[]):
        """
        If target_set is not a list it returns a rowset with all
        targets.
        If target_set is a list of groups it returns a rowset of targets
        that belong to these groups.
        """
        result_id = []
        if not isinstance(group_set, list):
            for target in self._db(self._db.target).select():
                result_id.append(target.id)
        else:
            rows = self._db(self._db.targetgroup).select()
            for row in rows:
                if row.id in group_set:
                    targets = json.loads(row.targets)
                    for t_id in targets:
                        result_id.append(self._db(self._db.target.id==t_id
                                                 ).select().first().id)
        result_id += target_set

        result = []
        for target_id in set(result_id):
            result.append(self.get_target(target_id))

        return result

    def get_target(self, target_id):
        """
        Returns the target with the specified id
        """
        return self._db(self._db.target.id==target_id).select().first()

    def get_target_hash(self, target_id):
        """
        Returns the target with the specified id
        """
        try:
            return self._db(self._db.target.id==target_id).select().first().hashpass
        except:
            return False


    def create_tulip(self, leak_id, target_id, hardcoded_url=None):
        """
        Creates a tulip for the target, and inserts it into the db
        (when target is 0, is the whitleblower and hardcoded_url is set by the caller)
        """
        if hardcoded_url and target_id:
            logger.error("Invalid usage of create_tulip: url and target specifyed")
            return NoneType

        tulip = self._db.tulip.insert(
            url= hardcoded_url if hardcoded_url else randomizer.generate_tulip_url(),
            leak_id=leak_id,
            target_id=target_id,
            allowed_accesses=settings.tulip.max_access,
            accesses_counter=0,
            allowed_downloads=0 if not target_id else settings.tulip.max_download,
            downloads_counter=0,
            expiry_time=settings.tulip.expire_days)
        self._db.commit()
        return tulip

    def get_leaks(self):
        pass

    def get_leak(self, leak_id):
        pass

    def get_tulips(self, leak_id):
        pass

    def get_tulip(self, tulip_id):
        pass

########NEW FILE########
__FILENAME__ = 03_init
from gluon.storage import Storage
from gluon.tools import Mail, Auth
from gluon.tools import Crud, Service, PluginManager, prettydate

crud = Crud(db)             # for CRUD helpers using auth
service = Service()         # for json, xml, jsonrpc, xmlrpc, amfrpc
plugins = PluginManager()   # for configuring plugins

# bind everything to settings
settings.private = Storage()
settings.tulip = ConfigFile(cfgfile, 'tulip')
settings.logging = ConfigFile(cfgfile, 'logging')

# GLOBAL setting
settings.private.author_email = settings.globals.author_email
settings.private.database_uri = settings.database.uri
settings.private.email_server = settings.globals.email_server
settings.private.email_sender = settings.globals.email_sender
settings.private.email_login = settings.globals.email_login
settings.private.plugins = []

# mail and auth are filled after the first settings.tulip initialization,
# because used inside Globaleaks object
# gl = local_import('logic.globaleaks').Globaleaks(db, settings)
gl = Globaleaks()

mail = Mail(db)
auth = Auth(db)

settings.auth = auth.settings
settings.mail = mail.settings
# XXX: hack
settings.mail.__dict__['commit'] = db.commit
settings.auth.__dict__['commit'] = db.commit

# reCAPTCHA support
#from gluon.tools import Recaptcha
#auth.settings.captcha = Recaptcha(request,
#        '6LdZ9sgSAAAAAAg621OrrkKkrCjbr3Zu4LFCZlY1',
#        '6LdZ9sgSAAAAAAJCZqqo2qLYa2wPzaZorEmc-qdJ')


# Disable remember me on admin login
auth.settings.remember_me_form = False

# Disable sensitive auth actions (list from http://web2py.com/book/default/chapter/08)
auth.settings.actions_disabled.append('register') #disable register
auth.settings.actions_disabled.append('verify_email') #disable register
auth.settings.actions_disabled.append('retrieve_username') #disable register
auth.settings.actions_disabled.append('reset_password') #disable register
auth.settings.actions_disabled.append('request_reset_password') #disable register
auth.settings.actions_disabled.append('impersonate') #disable register
auth.settings.actions_disabled.append('') #disable register

auth.settings.create_user_groups = False

# Set up the logger to be shared with all
# logger = local_import('logger').start_logger(settings.logging)
# logger = local_import('logger').logger

# AWS configuration
settings.private.aws_key = '<AWS-KEY>'
settings.private.aws_secret_key = '<AWS-SECRET-KEY>'
settings.private.hostname = '127.0.0.1'
settings.private.port     = '8000'
settings.private.mail_use_tls = True


# Mail setup
settings.mail.server = settings.globals.email_server
settings.mail.sender = settings.globals.email_sender
settings.mail.login = settings.globals.email_login
settings.mail.ssl = settings.globals.email_ssl

mail.settings.server = settings.mail.server
mail.settings.sender = settings.mail.sender
mail.settings.login = settings.mail.login


# settings.auth
settings.auth.hmac_key = 'sha512:7a716c8b015b5caca119e195533717fe9a3095d67b3f97114e30256b27392977'    # before define_tables()

auth.define_tables(username=True)


if auth.id_group("admin"):
    settings.private.admingroup = auth.id_group("admin")
else:
    auth.add_group('admin', 'Node admins')

if auth.id_group("targets"):
    settings.private.admingroup = auth.id_group("targets")
else:
    auth.add_group('targets', 'Targets')

if auth.id_group("candelete"):
    settings.private.admingroup = auth.id_group("candelete")
else:
    auth.add_group('candelete', 'candelete')

settings.auth.mailer = mail                                    # for user email verification
settings.auth.registration_requires_verification = False
settings.auth.registration_requires_approval = False
auth.messages.verify_email = 'Click on the link http://' + request.env.http_host + \
        URL('default','user',args=['verify_email']) + '/%(key)s to verify your email'

settings.auth.reset_password_requires_verification = True
auth.messages.reset_password = 'Click on the link http://' + request.env.http_host + \
        URL('default','user',args=['reset_password']) + '/%(key)s to reset your password'

settings.auth.table_user.email.label=T("Username")

randomizer = local_import('randomizer')

tor = local_import('anonymity').Tor(settings)

""" This module handles logging on globaleaks."""

import logging, os

class GLogger(logging.FileHandler):
    """
    Class GLogger provides two more logging options, secifically designed for
    client and server, so that the final user will be able to tune those ones
    in order to avoid leaks of undesidered information.
    """
    # Add two integers to identify server and client log severity.
    CLIENT = 10    # logging.NOTSET==0 < Glogger.CLIENT < Glogger.SERVER
    SERVER = 20    # GLogger.SERVER < logging.info

    def client(self, msg, *args, **kwargs):
        """
        Return a logging message with CLIENT level.
        """
        return log(self.CLIENT, msg, *args, **kwargs)

    def server(self, msg, *args, **kwargs):
        """
        Return a logging message with SERVER level.
        """
        return log(self.SERVER, msg, *args, **kwargs)


levels = dict(debug = logging.DEBUG,
              info = logging.INFO,
              warning = logging.WARNING,
              error = logging.ERROR,
              fatal = logging.FATAL,
              client = GLogger.CLIENT,
              server = GLogger.SERVER)


def start_logger(logsettings):
    """
    Start a new logger, set formatting options, and tune level according to use
    configuration.
    """
    logger = logging.getLogger('')
    if logger.handlers:

        if logsettings.enabled:
            if logsettings.logfile:
                logdest = logsettings.logfile
            else:
                logdest = os.devnull
                print "logfile is not configured: log will be suppressed"
        else:
            logdest = os.devnull

        hdlr = GLogger(logdest)

        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        logger.addHandler(hdlr)

        level = levels.get(logsettings.level, None)
        if not level:
            level = levels['fatal']
            logger.warning('Invalid level in config file: set [fatal] as default')

        logger.setLevel(level)

    return logger


logger = start_logger(settings.logging)


########NEW FILE########
__FILENAME__ = 04_datamodel
from gluon.contrib import simplejson as json

class Material(object):
    def __init__(self, id, url=None):
        if url:
            self._id = db(db.tulip.url==url).select().first().id
        else:
            self._id = id

    def get_id(self):
        return self._id

    def set_id(self, id):
        print "Error: id is read only"
        pass

    id = property(get_id, set_id)

    def get_url(self):
        return db.material[self.id].url
    def set_url(self, id):
        print "Error: url is read only"
        pass

    url = property(get_url, set_url)

    def get_type(self):
        return db.material[self.id].type

    def set_type(self, id):
        print "Error: url is read only"
        pass

    type = property(get_type, set_type)

    def get_files(self):
        files = db.material[self.id].file
        return json.loads(files)

    def set_files(self, id):
        print "Error: url is read only"
        pass

    files = property(get_files, set_files)

    @staticmethod
    def create_new(leak_id, url, type, file):
        return db.material.insert(leak_id=leak_id,
            url=url, type=type, file=file)

class Leak(object):
    def __init__(self, id):
        self._id = id
        self.title = "default title"

    def get_id(self):
        return self._id

    def set_id(self):
        print "Error: id is read only"
        pass

    id = property(get_id, set_id)

    def get_title(self):
        """
        issue 122
        """
        if not db.leak[self.id]:
            return self.title
        return db.leak[self.id].title

    def set_title(self, title):
        db.leak[self.id].title = title
        db.commit()

    title = property(get_title, set_title)

    #TODO:implement get/set tags
    def set_tags(self):
        pass

    def get_tags(self):
        pass

    tags = property(get_tags, set_tags)

    def get_desc(self):
        return db.leak[self.id].desc

    def set_desc(self, desc):
        db.leak[self.id].desc = desc
        db.commit()

    desc = property(get_desc, set_desc)

    def get_whistleblower_access(self):
        return db.leak[self.id].whistleblower_access

    def set_whistleblower_access(self, whistleblower_access):
        db.leak[self.id].whistleblower_access
        db.commit()

    whistleblower_access = property(get_whistleblower_access, set_whistleblower_access)

    #TODO: implement get/set material
    def get_material(self):
        return db(db.material.leak_id==self._id).select(db.material.ALL)

    def set_material(self, material):
        pass

    material = property(get_material, set_material)

    def get_spooled(self):
        """
        little fix of an adopters bug (issue #122)
        """
        return True

    def set_spooled(self, material):
        pass

    spooled = property(get_spooled, set_spooled)

    #TODO: implement get/set targets
    def get_targets(self):
        pass
    def set_targets(self, targets):
        pass
    targets = property(get_targets, set_targets)

    def get_submission_timestamp(self):
        return db.leak[self.id].submission_timestamp

    def set_submission_timstamp(self, timestamp):
        print "Error: submission_timestamp is read only"
        pass

    submission_timestamp = property(get_submission_timestamp, set_submission_timstamp)

    def get_leaker(self):
        pass

    def set_leaker(self, leaker):
        print "Error: leaker is read only"
        pass
    leaker = property(get_leaker, set_leaker)

    def get_tulips(self):
        for tulip_id in db(db.tulip.leak_id==self._id).select(db.tulip.id):
            yield Tulip(tulip_id["id"])

    def set_tulips(self, tulips):
        print "Error: tulip is read only"
        pass

    tulips = property(get_tulips, set_tulips)

    def add_material(self, leak_id, url, type, file):
        Material.create_new(leak_id, url, type, file)

    def get_extra(self):
        extra = []
        for row in db(db.leak.id==self._id).select():
            for i in settings.extrafields.fields:
                extra.append((i['label'], row[i['name']], i['type']))
        return extra

    def get_notified_targetgroups(self):
        """
        Returns a list of ids of the groups that had been notified of
        this leak
        """
        notified = db.leak[self.id].notified_groups
        if notified is None:
            return []
        else:
            return json.loads(notified)

    def create_tulip_by_group(self, group_id):
        """
        Notifies the targets of the selected targetgroup that have not
        been notified yet. Then adds that group to the notified_groups
        list
        """

        notified_groups = self.get_notified_targetgroups()
        # questo è vuoto: verifica
        print notified_groups

        notified_targets = [x.id for x in gl.get_targets(notified_groups)]
        # questo è vuoto: mah
        print notified_targets

        to_notify = [x.id for x in gl.get_targets([group_id])]
        to_notify = set(to_notify).difference(notified_targets)
        # questo è popolato, ok
        print to_notify

        for target_id in to_notify:
            target = gl.get_target(target_id)
            previously_generated = [tulip.target for tulip in self.tulips]
            # generate a tulip for targets thats haven't one
            if target not in previously_generated:
                tulip_id = gl.create_tulip(self._id, target.id)
            tulip_url = db.tulip[tulip_id].url

            # Add mail to db, sending managed by scheduler
            db.mail.insert(target=target.name,
                           address=target.contact,
                           tulip=tulip_url)

        notified_groups += [group_id]
        notified_groups = list(set(notified_groups))  # deletes duplicates

        db.leak[self._id].update_record(notified_groups=json.dumps(notified_groups))
        db.commit()

class Target(object):
    def __init__(self, id):
        self._id = id

    def get_id(self):
        return self._id

    def set_id(self):
        print "Error: id is read only"
        pass

    id = property(get_id, set_id)

class TargetList(object):
    def __init__(self, g=None):
        if g:
            self.build(g)

    def build(self, g):
        """for t in tlist:
            db.target.insert(name=t[0].name, desc=t[0].desc,
                            url=t[0].url, type=t[0].type,
                            info=t.info, status="active",
                            group=t.Name)
        """
        db.targetgroup.insert(name=g.Name, desc=g.Description, tags=g.Tags)

    def get_list(self):
        for group in db().select(db.targetgroup.ALL):
            yield group
        pass
    def set_list(self, value):
        pass
    list = property(get_list, set_list)

    def get_name(self):
        pass
    def set_name(self, value):
        pass
    name = property(get_name, set_name)

    def get_desc(self):
        pass
    def set_desc(self, value):
        pass
    desc = property(get_desc, set_desc)

    def get_url(self):
        pass
    def set_url(self, value):
        pass
    url = property(get_url, set_url)

    def get_type(self):
        pass
    def set_type(self, value):
        pass
    type = property(get_type, set_type)

    def get_info(self):
        pass
    def set_info(self, value):
        pass
    info = property(get_info, set_info)

class Tulip(object):
    def __init__(self, id=None, url=None):
        if url:
            # check if the URL is correct or an invalid
            tulip_row = db(db.tulip.url==url).select().first()
            if tulip_row:
                self._id = tulip_row.id
                self.target_id = tulip_row.target_id
            else:
                # The object does not handle the error code inside the obj
                print "Invalid url requested: ", url
                self._id = -1
        else:
            self._id = id

    def get_vote(self):
        return db.tulip[self.id].express_vote

    def set_vote(self, vote):
        # acceptable range is -1 0 and +1
        if(vote >= (-1) and vote <= 1):
            db.tulip[self.id].update_record(express_vote=vote)
            db.commit()
        else:
            print "Error: tulip vote has range of -1, 0 and +1"

    vote = property(get_vote, set_vote)

    # delete_bros used to delete the tulip self and all the legit brothers
    def delete_bros(self):
        retval = db(db.tulip.leak_id == db.tulip[self.id].leak_id).count()
        db(db.tulip.leak_id == db.tulip[self.id].leak_id).delete()
        return retval

    def get_id(self):
        return self._id

    def set_id(self, id):
        print "Error: id is read only"
        pass

    id = property(get_id, set_id)

    def get_url(self):
        return db.tulip[self.id].url

    def set_url(self, url):
        print "Error: url is read only"
        pass

    url = property(get_url, set_url)

    def get_target(self):
        if self.id == -1:
            print "requested target in invalid Tulip"
            return -1
        else:
            return db.tulip[self.id].target_id

    def set_target(self, target):
        print "Error: target is read only"
        pass

    target = property(get_target, set_target)

    def get_target_name(self):
        if self.id == -1:
            print "requested target name in invalid Tulip"
            return -1

        target_id = db.tulip[self.id].target_id
        if not int(target_id):
            return T("Whistleblower")

        target_selection = db.target[target_id]
        if target_selection:
            return target_selection.name

        print "requested a target id not available in target table"
        return "Error code: MACH3T3"

    def set_target_name(self, target):
        print "Error: target name not writable in Tulip object"
        return -1

    target_name = property(get_target_name, set_target_name)

    def is_wb(self):
        return int(self.target) == 0

    def get_allowed_accesses(self):
        return db.tulip[self.id].allowed_accesses

    def set_allowed_accesses(self, allowed_accesses):
        db.tulip[self.id].update_record(allowed_accessess=allowed_accesses)
        db.commit()

    allowed_accesses = property(get_allowed_accesses, set_allowed_accesses)

    def get_accesses_counter(self):
        return db.tulip[self.id].accesses_counter

    def set_accesses_counter(self, accesses_counter):
        db.tulip[self.id].update_record(accesses_counter=accesses_counter)
        db.commit()

    accesses_counter = property(get_accesses_counter, set_accesses_counter)

    def get_allowed_downloads(self):
        return db.tulip[self.id].allowed_downloads

    def set_allowed_downloads(self, allowed_downloads):
        db.tulip[self.id].update_record(allowed_downloads=allowed_downloads)
        db.commit()

    allowed_downloads = property(get_allowed_downloads, set_allowed_downloads)

    def get_downloads_counter(self):
        return db.tulip[self.id].downloads_counter

    def set_downloads_counter(self, downloads_counter):
        db.tulip[self.id].update_record(downloads_counter=downloads_counter)
        db.commit()

    downloads_counter = property(get_downloads_counter, set_downloads_counter)

    def get_feedbacks_provided(self):
        return db.tulip[self.id].feedbacks_provided

    def set_feedbacks_provided(self, feed_numbers):
        db.tulip[self.id].update_record(feedbacks_provided=feed_numbers)
        db.commit()

    feedbacks_provided = property(get_feedbacks_provided, set_feedbacks_provided)

    def get_leak(self):
        if self.id == -1:
            print "requested leak_id in invalid Tulip"
            return -1
        else:
            return Leak(db.tulip[self.id].leak_id)

    def set_leak(self):
        print "Error: leak is read only"
        pass

    leak = property(get_leak, set_leak)

########NEW FILE########
__FILENAME__ = 05_menu
response.title = settings.title
response.subtitle = settings.subtitle
response.meta.author = '%s <%s>' % (settings.author, settings.author_email)
response.meta.keywords = settings.keywords
response.meta.description = settings.description

response.menu = [
    (T('Index'),URL('default','index')==URL(),URL('default','index'),[]),
    (T('Submission'),URL('submission', 'index')==URL(),URL('submission','index'),[]),
]

response.menu_target = [
    (T('Tulip'),'/globaleaks/tulip/status/'+str(session.target)==URL(), '/globaleaks/tulip/status/'+str(session.target)),
    (T('Bouquet'),'/globaleaks/target/bouquet/'+str(session.target)==URL(), '/globaleaks/target/bouquet/'+str(session.target)),
]

response.menu_admin = [
    (T('Receivers'),'/globaleaks/admin/targets'==URL(), '/globaleaks/admin/targets'),
    (T('Stats'),'/globaleaks/admin/statistics'==URL(), '/globaleaks/admin/statistics/'),
    (T('Logout'),'/globaleaks/default/user/logout'==URL(), '/globaleaks/default/user/logout'),
    (T('Password'),'/globaleaks/default/user/change_password'==URL(), '/globaleaks/default/user/change_password'),
]

########NEW FILE########
__FILENAME__ = 06_wizard
class FormShaman(SQLFORM):
    def __init__(self, *args, **kwargs):

        # Creating a list of targetgroups
        groups_data = gl.get_targetgroups()

        # unroll the effective receiver inside the groups list
        # because could exist one or more group empty!
        effective_notification = 0
        for group_id in groups_data:
            effective_notification += len(groups_data[group_id]['members'])

        # this is the only error trapped by FormShaman.__init__
        if not groups_data or not effective_notification:
            return None

        if len(groups_data) > 1:
            grouplist = UL(_id="group_list")
            for group_id in groups_data:
                group = groups_data[group_id]['data']
                grouplist.insert(-1, LI(INPUT(_type="checkbox", _value="on",
                                              _name="target_%d" % group_id),
                                        SPAN(T(group["name"])),
                                        SPAN(T(group["tags"]),
                                             _class="group_tags")))
            grouplist = DIV(LABEL(T("Select Group:"),_class="submit_label"),grouplist,_class="groups")

        else:
            grouplist = ""

        jQueryFileUpload = DIV(
                           DIV(LABEL(T("Material") + ":", _class="submit_label"),
                                _class="w2p_fl"),
                           DIV(DIV(LABEL(DIV(T("Add Files")),
                                         INPUT(_type="file",
                                               _name="files[]"),
                                               _class="fileinput-button"),
                                       DIV(SPAN(),_id="speedbox"),
#                                   BUTTON(T("Cancel upload"),
#                                            _type="reset",
#                                            _class="cancel"),
#                                   BUTTON(T("Delete Files"),
#                                            _type="button",
#                                            _class="delete"),
                                   _class="fileupload-buttonbar"),
                                   DIV(TABLE(_class="files"),
                                       DIV(_class="fileupload-progressbar"),
                                       _class="fileupload-content"),
                                   _id="fileupload", _class="w2p_fl"),
                            DIV(_class="w2p_fc"),
                                _id="material__row")

        material_njs = DIV(DIV(LABEL(T("Material") + ":", _class="submit_label"),
                                _class="w2p_fl"),
                            DIV(INPUT(_name='material', _type='file',
                                      _id='file-uploader-nonjs'),
                                _class="w2p_fc"),
                                _id="file-uploader-nonjs")

        targetgroups = DIV(T('Targets'), DIV(DIV(_id="group_filter"),
                                         DIV(grouplist)))

        with open(settings.globals.disclaimer_file) as filestream:
            disclaimer_text = TAG(filestream.read())
            # sadly, HTML must not be passed to avoid XXSs

        disclaimer_info = DIV(disclaimer_text, _class="disclaimer_text")
        disclaimer_fb = DIV(LABEL(INPUT(_name='agree', value=False, _type='checkbox',
                                        _id="disclaimer",
                                        requires=IS_EQUAL_TO("on",
                                            error_message=T('must accept disclaimer'))),T('Accept Disclaimer')),
                            INPUT(_type="submit",_id="submission-button", _class="btn"))

        self.special_fields = {
                       'disclaimer_info' : disclaimer_info,
                       'disclaimer' : disclaimer_fb,
                       'captcha' : '' ,#auth.settings.captcha,
                       'material': DIV(jQueryFileUpload, material_njs),
                       #DIV(settings.globals.material_njs, settings.globals.jQueryFileUpload),
                       'grouplist': grouplist
                       }

        self.steps = kwargs.get('steps', None)
        if not self.steps:
            raise ValueError('FormShaman needs a steps argument')
        fields = []
        labels = {}
        for step in self.steps:
            for norm_field in filter(lambda x: x not in self.special_fields.keys(),
                                     step):
                fields.append(norm_field['name'])
                labels[norm_field['name']] = norm_field['label']

        # set up everything launching the parent class' init
        super(FormShaman, self).__init__(*args, fields=fields, labels=labels, **kwargs)
        # This is a hack to make the form submission work on Chrome
        if not self['_action']:
            self['_action'] = "#"

    def createform(self, xfields):
        table = DIV(_id="submission", _class="")
        step_head = UL(_class="nav nav-tabs", _id="submission-steps")
        for i in range(1,len(self.steps)+1):
            classval = "step active" if i == 1 else "step"
            # XXX Make this part much more customizable, such as the stepDesc
            step_head.append(LI(
                                A(
                                  #SPAN(str(i),_class="stepNumber"),
                                  SPAN(T("Step") + " " +str(i),_class="stepDesc"),
                                  _href="#step-"+str(i)), _class=classval
                                )
                             )
        table.append(step_head)

        try:
            i = 1
            j = 0
            steps = []
            for step in self.steps:
                classval = "tab-pane active" if i == 1 else "tab-pane"
                step_html = DIV(FIELDSET(
                                     P(settings.extrafields.step_desc[i-1]),
                                     _id="step-"+str(i), _class="step_holder"
                                     ), _class=classval, _id="step-"+str(i))
                for field in step:
                    if field in self.special_fields.keys():
                        step_html.append(DIV(self.special_fields[field],
                                             _class="field_holder"))
                    else:
                        step_html.append(DIV(
                                             xfields[j][1],
                                             xfields[j][2],
                                             _id=xfields[j][0], _class="field_holder"))
                        j += 1
                i += 1
                steps.append(step_html)

            table.append(DIV(steps, _class="tab-content"))

        except:
            raise RuntimeError, 'formstyle not supported'

        #response.files.append(URL('static','FormShaman',args=['css','smart_wizard.css']))
        #response.files.append(URL('static','FormShaman',args=['js','jquery.smartWizard.js']))
        return table

########NEW FILE########
__FILENAME__ = 07_file_upload
#!/usr/bin/env python
#
# Port of jQuery File Upload Plugin PHP example in web2py Python
#
# Original code
# Copyright 2010, Sebastian Tschan
# https://blueimp.net
#
# Licensed under the MIT license:
# http://creativecommons.org/licenses/MIT/


import os
import urllib
import shutil
import time

randomizer = local_import("randomizer")

class UploadHandler:
    def __init__(self, options=None):
        if not session.upload_dir:
            session.upload_dir = randomizer.generate_dirname()
        self.__options = {
            'script_url' : request.env.path_info,
            'upload_dir': os.path.join(request.folder, 'uploads',
                                       session.upload_dir),
            'upload_url': '',  # .. and this should removed?
            'param_name': 'files[]',
            'max_file_size': None,
            'min_file_size': 1,
            'accept_file_types': 'ALL',
            'max_number_of_files': None,
            'discard_aborted_uploads': True,
            'chunksize': None,
            'image_versions': {
                'thumbnail': {
                    'upload_dir': request.folder + '/thumbnails/',
                    'upload_uri': request.env.path_info + '/thumbnails/',
                    'max_width': 80,
                    'max_height': 80
                }
            }
        }
        if options:
            self.__options = options
        else:
            if not os.path.exists(self.__options["upload_dir"]):
                os.makedirs(self.__options["upload_dir"])

    def __get_file_object(self, file_name):
        file_path = os.path.join(self.__options['upload_dir'], file_name)
        if not os.path.isfile(file_path) and file_name[0] != '.':
            f = open(file_path, 'w')
            f.write('')
            f.close()

        if os.path.isfile(file_path) and file_name[0] != '.':
            file = Storage()
            file.name = file_name
            file.size = os.path.getsize(file_path)

            file.url = "#"
            #file.url = self.__options['upload_url'] + \
            #        file.name.replace(' ', '%20')
#           for version, options in self.__options['image_versions']:
#               if os.path.isfile(self.__options['upload_dir'] + file_name):
#                   file[version + '_url'] = options['upload_url'] + \
#                                       urllib.urlencode(file.name)

            file.delete_url = self.__options['script_url'] + \
                            "?deletefile=" + file.name.replace(' ','%20')

            file.delete_type = 'GET'

            return response.json([dict(**file)])

        return None

    def __get_file_objects(self):
        files = []
        for file in os.listdir(self.__options['upload_dir']):
            files.append(self.__get_file_object(file))
        return files

    def __create_scaled_image(self, file_name, options):
        # Function unimplemented because not needed by GL
        return True

    def __has_error(self, uploaded_file, file, error):
        if error:
            return error

        if file.name.split['.'][-1:][0] not in \
                self.__options['accepted_file_types'] and \
                self.__options['accepted_file_types'] != "ALL":
            return 'acceptFileTypes'

        if self.__options['max_file_size'] and \
            (file_size > self.__options['max_file_size'] or \
                file.size > self.__options['max_file_size']):
            return 'maxFileSize'

        if self.__options['min_file_size'] and \
            file_size > self.__options['min_file_size']:
            return 'minFileSize'

        if self.__options['max_number_of_files'] and \
            int(self.__options['max_number_of_files']) <= \
                len(self.__get_file_objects):
            return 'maxNumberOfFiles'

        return None

    def __handle_file_upload(self, uploaded_file, name, size, type, error,
                             leak_id=None):
        file = Storage()
        # checking name duplicates and in case change filename
        if os.path.exists(os.path.join(request.folder, 'material',
                                       self.get_file_dir(leak_id or None),
                                       name)):
            name = "%s%s.%s" % ("".join(name.split(".")[:-1]),
                                int(time.time()),
                                name.split(".")[-1])

        file.name = os.path.basename(name).strip('.\x20\x00..')
        #file.name = strip_path_and_sanitize(name)
        file.size = int(size)
        file.type = type
        file.id = randomizer.alphanumeric(20)

        # error = self.__has_error(uploaded_file, file, error)
        error = None

        if not error and file.name:
            file_path = os.path.join(self.__options['upload_dir'], file.name)
            # print "filepath: %s " % file_path
            append_file = not self.__options['discard_aborted_uploads'] and os.path.isfile(file_path) and file.size > os.path.getsize(file_path)
            # print "append: %s file.size: %s getsize: %s" % (append_file, file.size, os.path.getsize(file_path))

            # print "file position: %s" % (uploaded_file.tell())

            if uploaded_file:
            # multipart/formdata uploads (POST method uploads)
                if append_file:
                    dst_file = open(file_path, 'ab')
                    shutil.copyfileobj(
                                    uploaded_file,
                                    dst_file
                                    )
                else:
                    dst_file = open(file_path, 'w+b')
                    shutil.copyfileobj(
                                    uploaded_file,
                                    dst_file
                                    )
            else:
            # Non-multipart uploads (PUT method)
            # take the request.body web2py file stream
                if append_file:
                    shutil.copyfileobj(
                                    request.body,
                                    open(file_path, 'ab')
                                    )
                else:
                    shutil.copyfileobj(
                                    request.body,
                                    open(file_path, 'w+b')
                                    )
            file_size = os.path.getsize(file_path)

            if file_size == file.size or not request.env.http_x_file_name:
                #file.url = self.__options['upload_url'] + file.name.replace(" ", "%20")
                file.url = "#"

#               for version, options in self.__options['image_versions']:
#                   if os.path.isfile(self.__options['upload_dir'] + file_name):
#                       file[version + '_url'] = self.__options['upload_url'] + \
#                                           urllib.urlencode(file.name)

            elif self.__options['discard_aborted_uploads']:
                os.remove(file_path)
                file.error = 'abort'

            if request.env.http_x_file_size:
                file.size = int(request.env.http_x_file_size)
            else:
                file.size = file_size

            file.delete_url = self.__options['script_url'] + \
                        "?deletefile=" + file.name.replace(" ", "%20")

            file.delete_type = 'GET'

        else:
            file.error = error

        return response.json([dict(**file)])

    def get_file_dir(self, leak_id=None):
        if leak_id is None:
            filedir = db(db.submission.session ==
                         session.wb_id).select().first()

            if not filedir:
                if not session.dirname:
                    filedir = randomizer.generate_dirname()
                    session.dirname = filedir
                else:
                    filedir = session.dirname
            else:
                filedir = str(filedir.dirname)

            return filedir
        else:
            filedir = db(db.submission.leak_id == leak_id).select().first()
            filedir = str(filedir.dirname)
            return filedir

    def get(self):
        if request.vars.file:
            file_name = os.path.basename(request.vars.file)
            #file_name = strip_path_and_sanitize(request.vars.file)
            info = self.__get_file_object(file_name)
        else:
            filename = None
            info = self.__get_file_objects()
        return info

    def post(self, leak_id=None):
        upload = Storage()
        upload['error'] = False

        if request.env.http_x_file_name:
            info = self.__handle_file_upload(
                                        request.body,
                                        request.env.http_x_file_name,
                                        request.env.http_x_file_size,
                                        request.env.http_x_file_type,
                                        upload['error'],
                                        leak_id=leak_id
                                        )
            return info
        elif request.vars:
            try:
                upload.data = request.vars[self.__options['param_name']]
            except:
                return dict(error=True)
            upload['size'] = False #upload.data.file.tell()
            upload['type'] = upload.data.type
            upload.name = upload.data.filename
            # upload['file'] = upload_file.file
            # For the moment don't handle multiple files in one POST
            info = self.__handle_file_upload(
                                        upload.data.file,
                                        upload['name'],
                                        upload['size'],
                                        upload['type'],
                                        upload['error'],
                                        leak_id=leak_id
                                        )
            return info

        return dict(error=True)

    def delete(self, uploads=None):
        file_name = os.path.basename(request.vars.deletefile) \
                    if request.vars.deletefile else None
        if not uploads:
            file_path = os.path.join(request.folder, 'material',
                                     self.get_file_dir(), file_name)
        else:
            file_path = os.path.join(request.folder, 'uploads',
                                     session.upload_dir, file_name)
        success = False
        if os.path.isfile(file_path) and file_name[0] != ".":
            os.remove(file_path)
            success = True
        if success:
            return {'success': 'true'}
        else:
            return {'success': 'false'}


########NEW FILE########
__FILENAME__ = 08_configuration_required
def configuration_required(funct):
    """
    This function is called ahead of every controller function that
    require to run in a proper configured GlobaLeaks environment.
    """

    if settings.globals.under_installation:
        return lambda: redirect('/globaleaks/installation/password_setup.html')

    return funct

########NEW FILE########
__FILENAME__ = anonymity
#
# EXPERIMENTAL CODE - TO BE COMPLETED
#

from __future__ import with_statement

import re
import os.path
import signal
import subprocess
import socket
import threading
import time
import logging

from pytorctl import TorCtl

from config import projroot

torrc = os.path.join(projroot, 'globaleaks', 'tor', 'torrc')
hiddenservice = os.path.join(projroot, 'globaleaks', 'tor', 'hiddenservice')

class ThreadProc(threading.Thread):
    def __init__(self, cmd):
        threading.Thread.__init__(self)
        self.cmd = cmd
        self.proc = None

    def run(self):
        try:
            self.proc = subprocess.Popen(self.cmd,
                                         shell = False, stdout = subprocess.PIPE,
                                         stderr = subprocess.PIPE)
        except OSError:
           logging.fatal('cannot execute command')

class Tor:
    def __init__(self, s):
        self.settings = s
        if self.settings.globals.torifyconnections or self.settings.globals.hiddenservice:
            self.start()

    def check(self):
        conn = TorCtl.connect()
        if conn != None:
            conn.close()
            return True

        return False

    def get_hiddenservicename(self):
        name = ""
        if self.settings.globals.hiddenservice and self.check():
            hostnamefile = os.path.join(hiddenservice, 'hostname')
            while True:
                if not os.path.exists(hostnamefile):
                    time.sleep(1)
                    continue

                with open(hostnamefile, 'r') as f:
                    name = f.readline().strip()
                    break
        return name


    def start(self):
        if not self.check():

            if not os.path.exists(torrc):
                raise OSError("torrc doesn't exist (%s)" % torrc)

            tor_cmd = ["tor", "-f", torrc]

            if self.settings.globals.hiddenservice:
                tor_cmd.extend(["--HiddenServiceDir", hiddenservice, "--HiddenServicePort", "80 127.0.0.1:8000"])

            torproc = ThreadProc(tor_cmd)
            torproc.run()

            bootstrap_line = re.compile("Bootstrapped 100%: ")

            while True:
                if torproc.proc == None:
                    time.sleep(1)
                    continue

                init_line = torproc.proc.stdout.readline().strip()
                if not init_line:
                    torproc.proc.kill()
                    return False

                if bootstrap_line.search(init_line):
                    break

            return True

    def stop(self):
        if not self.check():
            return

        conn = TorCtl.connect()
        if conn != None:
            conn.send_signal("SHUTDOWN")
            conn.close()

class TorAccessCheck:
    def __init__(self, ip, headers):
            self.result = {}
            self.check(ip, headers)

    def check_tor2web(self, headers):
        """
        This is used to parse tor2web headers.
        The header format should be
        X-tor2web: encrypted|plain-trusted|untrusted-tor|notor
        """
        encryption = None
        trust = None
        withtor = None

        try:
            parsed = headers.http_x_tor2web.split('-')
        except:
            return False
        try:
            if parsed[0] == "plain":
                try:
                    if parsed[1] == "tor":
                        tor = True
                    else:
                        tor = False
                except:
                    tor = False

                encryption = False
                trust = False

            elif parsed[0] == "encrypted":
                encryption=True
                if parsed[1] == "trusted":
                    trust = True
                elif parsed[1] == "untrusted":
                    trust = False
                else:
                    trust = None

                if parsed[2] == "tor":
                    withtor = True
                elif parsed[2] == "notor":
                    withtor = False
        except:
            # XXX add error handling here.
            pass

        return dict(encryption=encryption, \
                    trust=trust, tor=withtor)


    def check_tor(self, ip):
        if str(ip) == "127.0.0.1":
            return True
        else:
            return False

    def check(self, ip, headers):
        self.result['tor2web'] = self.check_tor2web(headers)

        if not self.result['tor2web']:
            self.result['tor'] = self.check_tor(ip)
        else:
            self.result['tor'] = self.result['tor2web']['tor']


########NEW FILE########
__FILENAME__ = compress_material
import zipfile
import subprocess
import os

class Zip:
    """
    Class that creates the material archive.
    """
    def create_zip(self, db, submission, request, logger, passwd=None,
                   mat_dir=None, no_subdirs=None):
        """
        Function to create an unencrypted zipfile
        """
        if db(db.material.leak_id==submission.id).select().first():
            try:
                filedir = str(db(db.submission.leak_id==submission.id).select(
                          db.submission.dirname).first().dirname)
                filedir = os.path.join(request.folder, "material", filedir)
            except:
                logger.error('create_zip: invalid filedir')
                return dict(error='invalid filedir')
            err = None
            try:
                # XXX should need some refactoring
                if not mat_dir:
                    mat_dir = filedir
                splitted = os.path.split(mat_dir)
                if splitted[-1].isdigit():
                    filedir = "%s-%s" % (splitted[-2], splitted[-1])
                if no_subdirs:
                    save_file = filedir + "-0"
                    # get only files, no subdirectories
                    files = [f for f in os.listdir(mat_dir)
                             if not os.path.isdir(os.path.join(mat_dir, f))]
                else:
                    save_file = filedir
                    files = os.listdir(mat_dir)
                # XXX: issue #51
                if passwd and os.path.exists(mat_dir):
                    logger.error('Encrypted ZIP function disabled, due to security redesign needs')
                    return 0
       #             cmd = 'zip -e -P%(passwd) %(zipfile).zip %(files)' % dict(
       #                    passwd=passwd, zipfile=filedir,
       #                    files=" ".join(files))
       #             subprocess.check_call(cmd.split())
                elif not passwd and os.path.exists(mat_dir):
                    zipf = zipfile.ZipFile(save_file+'.zip', 'w')
                    for f in files:
                        path = os.path.join(mat_dir, f)
                        zipf.write(path, f)
                        subdirs = os.walk(path)
                        for subdir in subdirs:
                            inner_subdir = os.path.split(subdir[0])[-1]
                            if not inner_subdir.isdigit():
                                inner_subdir = ""
                            for subfile in subdir[2]:
                                zipf.write(os.path.join(subdir[0], subfile),
                                           os.path.join(inner_subdir,subfile))
                else:
                    logger.error('create_zip: invalid path')
            except RuntimeError as err:
                logger.error('create_zip: error in creating zip')
                try:
                    zipf.close()
                except (RuntimeError, zipfile.error) as err:
                    logger.info('create_zip: error when trying to save zip')
            except subprocess.CalledProcessError as err :
                    logger.error('create_zip: error in creating zip')
            finally:
                return dict(error=err) if err else None

########NEW FILE########
__FILENAME__ = crypto
#
# EXPERIMENTAL CODE - TO BE COMPLETED
#
# Notes for supporting PGP encryption
# Requires: python-gnupg
#           pip install python-gnupg

import gnupg


class PGP:
    def __init__(self, directory, keyserver=None):
        if keyserver:
            self.keyserver = keyserver
        else:
            self.keyserver = 'pgp.mit.edu'
        self.gpg = gnupg.GPG(gnupghome=directory)

    def get_key(self, keyid, fp = None):
        r_key = self.gpg.recv_keys(self.keyserver, keyid)
        if fp:
            if r_key.fingerprints[0] == fp:
                print "Fingerprint match"
            else:
                print "ERROR: Fingerprints do not match!"

    def encrypt(self, data, dst):
        return self.gpg.encrypt(data, dst, always_trust=True)


# Example usage
crypt = PGP("/tmp/globaleaks", "pgp.mit.edu")
crypt.get_key("150FE210", "46E5EF37DE264EA68DCF53EAE3A21297150FE210")
print "This is the Encrypted message:"
print crypt.encrypt("Hello :)", "art@fuffa.org")


########NEW FILE########
__FILENAME__ = file_helper
import os

def move(src, dst, cur_folder):
            dst_folder = os.path.join(cur_folder, 'material/' + filedir + '/')

            if not os.path.isdir(dst_folder):
                os.makedirs(dst_folder)
            os.rename(os.path.join(cur_folder, 'uploads/') +
                      tmp_file, dst_folder + filename)

########NEW FILE########
__FILENAME__ = jquery_helper
def upload_tmpl():
    return """<tr class="template-upload{{if error}} ui-state-error{{/if}}">
        <td class="preview"></td>
        <td class="name">${name}</td>
        <td class="size">${sizef}</td>
        {{if error}}
            <td class="error" colspan="2">Error:
                {{if error === 'maxFileSize'}}File is too big
                {{else error === 'minFileSize'}}File is too small
                {{else error === 'acceptFileTypes'}}Filetype not allowed
                {{else error === 'maxNumberOfFiles'}}Max number of files exceeded
                {{else}}${error}
                {{/if}}
            </td>
        {{else}}
            <td class="progress"><div></div></td>
            <td class="start"><button>Start</button></td>
        {{/if}}
        <td class="cancel"><button>Cancel</button></td>
    </tr>
    """

def download_tmpl():
    return """<tr class="template-download{{if error}} ui-state-error{{/if}}">
        {{if error}}
            <td></td>
            <td class="name">${name}</td>
            <td class="size">${sizef}</td>
            <td class="error" colspan="2">Error:
                {{if error === 1}}File exceeds upload_max_filesize (php.ini directive)
                {{else error === 2}}File exceeds MAX_FILE_SIZE (HTML form directive)
                {{else error === 3}}File was only partially uploaded
                {{else error === 4}}No File was uploaded
                {{else error === 5}}Missing a temporary folder
                {{else error === 6}}Failed to write file to disk
                {{else error === 7}}File upload stopped by extension
                {{else error === 'maxFileSize'}}File is too big
                {{else error === 'minFileSize'}}File is too small
                {{else error === 'acceptFileTypes'}}Filetype not allowed
                {{else error === 'maxNumberOfFiles'}}Max number of files exceeded
                {{else error === 'uploadedBytes'}}Uploaded bytes exceed file size
                {{else error === 'emptyResult'}}Empty file upload result
                {{else}}${error}
                {{/if}}
            </td>
        {{else}}
            <td class="preview">
                {{if thumbnail_url}}
                    <a href="${url}" target="_blank"><img src="${thumbnail_url}"></a>
                {{/if}}
            </td>
            <td class="name">
                <a href="${url}"{{if thumbnail_url}} target="_blank"{{/if}}>${name}</a>
            </td>
            <td class="size">${sizef}</td>
            <td colspan="2"></td>
        {{/if}}
        <td class="delete">
            <button data-type="${delete_type}" data-url="${delete_url}">Delete</button>
        </td>
    </tr>
    """ 

#
#def upload_tmpl():
#    return """<tr class="template-upload{{if error}} ui-state-error{{/if}}">
#            <td class="preview"></td>
#            <td class="name">${name}</td>
#            <td class="size">${sizef}</td>
#            {{if error}}
#                <td class="error" colspan="2">Error:
#                    {{if error === 'maxFileSize'}}""" + T("File is too big") + \
#                    """{{else error === 'minFileSize'}}""" + T("File is too small") + \
#                    """{{else error === 'acceptFileTypes'}}""" + T("Filetype not allowed") + \
#                    """{{else error === 'maxNumberOfFiles'}}""" + T("Max number of files exceeded") + \
#                    """{{else}}${error}
#                    {{/if}}
#                </td>
#            {{else}}
#                <td class="progress"><div></div></td>
#                <td class="start"><button>""" + T("Start") + """</button></td>
#            {{/if}}
#            <td class="cancel"><button>""" + T("Cancel") + """</button></td>
#        </tr>"""
#
#def download_tmpl():
#    return """
#        <tr class="template-download{{if error}} ui-state-error{{/if}}">
#        {{if error}}
#            <td></td>
#            <td class="name">${name}</td>
#            <td class="size">${sizef}</td>
#            <td class="error" colspan="2">Error:
#                {{if error === 1}}""" + T("File exceeds upload_max_filesize (php.ini directive)") + \
#                """{{else error === 2}}""" + T("File exceeds MAX_FILE_SIZE (HTML form directive)") + \
#                """{{else error === 3}}""" + T("File was only partially uploaded") + \
#                """{{else error === 4}}""" + T("No File was uploaded") + \
#                """{{else error === 5}}""" + T("Missing a temporary folder") + \
#                """{{else error === 6}}""" + T("Failed to write file to disk") + \
#                """{{else error === 7}}""" + T("File upload stopped by extension") + \
#                """{{else error === 'maxFileSize'}}""" + T("File is too big") + \
#                """{{else error === 'minFileSize'}}""" + T("File is too small") + \
#                """{{else error === 'acceptFileTypes'}}""" + T("Filetype not allowed") + \
#                """{{else error === 'maxNumberOfFiles'}}""" + T("Max number of files exceeded") + \
#                """{{else error === 'uploadedBytes'}}""" + T("Uploaded bytes exceed file size") + \
#                """{{else error === 'emptyResult'}}""" + T("Empty file upload result") + \
#                """{{else}}${error}
#                {{/if}}
#            </td>
#        {{else}}
#            <td class="preview">
#                {{if thumbnail_url}}
#                    <a href="${url}" target="_blank"><img src="${thumbnail_url}"></a>
#                {{/if}}
#            </td>
#            <td class="name">
#                <a href="${url}"{{if thumbnail_url}} target="_blank"{{/if}}>${name}</a>
#            </td>
#            <td class="size">${sizef}</td>
#            <td colspan="2"></td>
#        {{/if}}
#        <td class="delete">
#            <button data-type="${delete_type}" data-url="${delete_url}">""" + T("Delete") + """</button>
#        </td>
#    </tr>
#    """
########NEW FILE########
__FILENAME__ = logger


########NEW FILE########
__FILENAME__ = mailer
#import modules to work with MIME messages
from gluon.tools import MIMEMultipart, MIMEText, MIMEBase, Encoders
from gluon import *
from gluon.utils import logger
import smtplib
import os

from socksipy import socks

# socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, 'localhost', 9050)

# socks.wrapmodule(smtplib)

class MultiPart_Mail(object):
    def __init__(self, s):
        self.settings = s
    def buildMIME(self,
        sender,
        recipients,
        subject,
        message_text,
        message_html = None,
        attachments = None,
        cc = None,
        bcc = None,
        reply_to = None):
        #bases off of http://code.activestate.com/recipes/473810/

        # Create the root message and fill in the from, to, and subject headers
        msgRoot = MIMEMultipart.MIMEMultipart('related')
        msgRoot['Subject'] = subject
        msgRoot['From'] = sender

        if not isinstance(recipients, list):
            #presumably only given a string representing a single email address
            #convert to single element list
            to = [recipients]
        msgRoot['To'] = ', '.join(recipients)

        if cc and isinstance(cc, list):
            cc = ', '.join(cc)
            msgRoot['CC'] = cc

        if bcc and isinstance(cc, list):
            bcc = ', '.join(bcc)
            msgRoot['BCC'] = bcc

        if reply_to:
            msgRoot['Reply-To'] = reply_to

        msgRoot.preamble = 'This is a multi-part message in MIME format.'

        # Encapsulate the plain and HTML versions of the message body in an
        # 'alternative' part, so message agents can decide which they want to display.
        msgAlternative = MIMEMultipart.MIMEMultipart('alternative')
        msgRoot.attach(msgAlternative)

        #text only version
        msgText = MIMEText.MIMEText(message_text)
        msgAlternative.attach(msgText)

        #html version of message
        if message_html:
            msgText = MIMEText.MIMEText(message_html, 'html')
            msgAlternative.attach(msgText)
        # We reference the image in the IMG SRC attribute by the ID we give it
        #below <img src="cid:content-id">

        #attach images to message
        #attachments are a list as in (['filename1',filecontents1], ['filename2',filecontents2])
        #where the filecontents are as provided by open(file_path, 'rb') or other method (retreived from DB?)
        if attachments:
            for attachment in attachments:
                if attachment[0].split('.')[-1] in ('jpg','jpeg','png','gif','bmp'):
                    #attachment's contents
                    msgImage = MIMEImage(attachment[1])

                    # Define the image's ID as referenced above
                    msgImage.add_header('Content-ID', '<'+attachment[0]+'>')
                    msgRoot.attach(msgImage)
                else:
                    #based on http://snippets.dzone.com/posts/show/2038
                    part = MIMEBase.MIMEBase('application', "octet-stream")
                    part.set_payload(attachment[1])
                    Encoders.encode_base64(part)
                    part.add_header('Content-Disposition', 'attachment; filename="%s"' % attachment[0])
                    msgRoot.attach(part)
        #print msgRoot.as_string()
        return msgRoot

    def send(
        self,
        to = '', #list of email addresses - Required
        subject='None', #message's subject - Required
        message_text='None', #message body in plain text - Required
        message_html=None, #message body in html - Optional
        attachments=None, #list of truples [(filename, file_contents)] - Optional
        cc = None, #list of email addresses to CC message to
        bcc = None, #list of email addresses to BCC message to
        reply_to = None, #single email address to have replies send to
        ):
        """
        Sends an email. Returns True on success, False on failure.
        """        
        if not isinstance(to, list):
            to = [to]

        try:
            if self.settings.private.email_server == 'gae':
                from google.appengine.api import mail
                #untested on GAE, but in theory should work
                #http://code.google.com/appengine/docs/python/mail/emailmessagefields.html
                mail.send_mail(sender=self.settings.private.email_sender, to=to,
                               subject=subject, body=message_text, html=message_html, attachments=attachments, cc = cc,
                               bcc = bcc, reply_to = reply_to)
            else:

                msg = self.buildMIME(sender = self.settings.private.email_sender,
                    recipients = to, subject = subject,
                    message_text = message_text, message_html = message_html,
                    attachments = attachments,
                    cc = cc, bcc = bcc, reply_to = reply_to)
                #print 'message'+msg.as_string()
                #Build MIME body
                (host, port) = self.settings.mail.server.split(':')

                if self.settings.mail.ssl:                    
                    try:
                        server = smtplib.SMTP_SSL(host, port)
                    except:
                        # ERROR python <= 2.6
                        pass
                else:
                    server = smtplib.SMTP(host, port)

                if self.settings.mail.login:
                    try:
                        server.ehlo_or_helo_if_needed()
                    except SMTPHeloError:
                        logger.info("SMTP Helo Error in HELO")

                    if self.settings.mail.use_tls:
                        try:
                            server.starttls()
                        except SMTPHeloError:
                            logger.info("SMTP Helo Error in STARTTLS")
                        except SMTPException:
                            logger.info("Server does not support TLS")

                        except RuntimeError:
                            logger.info("Python version does not support TLS (<= 2.6?)")

                    try:
                        server.ehlo_or_helo_if_needed()
                    except SMTPHeloError:
                        logger.info("SMTP Helo Error in HELO")

                    (username, password) = self.settings.mail.login.split(':')
                    try:
                        server.login(username, password)
                    except SMTPHeloError:
                        logger.info("SMTP Helo Error in LOGIN")

                    except SMTPAuthenticationError:
                        logger.info("Invalid username/password combination")

                    except SMTPException:
                        logger.info("SMTP error in login")

                try:
                    server.sendmail(self.settings.private.email_sender, to, msg.as_string())
                    server.quit()

                except SMTPRecipientsRefused:
                    logger.info("All recipients were refused. Nobody got the mail.")

                except SMTPHeloError:
                    logger.info("The server didn't reply properly to the HELO greeting.")

                except SMTPSenderRefused:
                    logger.info("The server didn't accept the from_addr.")

                except SMTPDataError:
                    logger.info("The server replied with an unexpected error code (other than a refusal of a recipient).")
                                        
        except Exception, e:
            return False
        return True

    def make_txt(self, context, file):
        f = open(os.path.join(os.getcwd(), file))
        return f.read().strip() % context



    def make_html(self, context, file):
        f = open(os.path.join(os.getcwd(), file))
        return f.read().strip() % context
                                                        
                                                        

########NEW FILE########
__FILENAME__ = material
import os

class utils(object):
    def human_size(self, size, approx=False):
        SUFFIX = {1000: ['KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'],
                  1024: ['KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']}

        if size < 0:
            return False

        multiple = 1024 if approx else 1000

        for suffix in SUFFIX[multiple]:
            size /= multiple
            if size < multiple:
                return '%.1f %s' % (size, suffix)

    def file_type(self, ext):
        img = ['bmp', 'gif', 'jpg', 'jpeg', 'png', 'psd',
                'pspimage', 'thm', 'tif', 'yuv', 'svg', 'ps',
                'eps', 'drw', 'ai']

        data = ['7z', 'deb','gz', 'pkg','rar','rpm','sit', 'sitx', 'gz'
                'zip', 'zipx', 'iso', 'dmg', 'toast', 'vcd']

        doc = ['doc', 'docx', 'log', 'msg', 'pages', 'rtf', 'txt',
                'wpd', 'wps', 'pdf', 'xlr', 'xls', 'csv', 'key']

        if ext in img:
            return "img"
        elif ext in doc:
            return "pdf"
        else:
            return "zip"


########NEW FILE########
__FILENAME__ = randomizer
import random
import hashlib, os
import string

def generate_tulip_receipt():
    #FIXME is this a good idea?
    #      should i be converting the random number string to bytes?
    number = ""
    for i in range(0,10):
        number += str(ord(os.urandom(1)) % 10)
    return (number, hashlib.sha256(number).hexdigest())

def generate_wb_id():
    #FIXME is this a good idea?
    #      should i be converting the random number string to bytes?
    return hashlib.sha256(os.urandom(1024)).hexdigest()

def __sanitize_title(title):
    import unicodedata
    title = unicode(title, "utf-8")
    title = "".join([c for c in title if unicodedata.category(c)[0] == "L"])
    return title

# Maybe these three should be merged into one
def generate_human_dirname(request, leak, old_dirname):
    # Name like Data-$Title-$ID-$progressivo-.zip
    try:
        prog = 1
        title = __sanitize_title(leak.title)
        dirname = "Data-%s-%s-%s" % (title, old_dirname[:4], str(prog))
        while os.path.exists(os.path.join(request.folder, 'material', dirname)):
            prog += 1
            dirname = "Data-%s-%s-%s" % (title, old_dirname[:4], str(prog))
        return dirname
    except:
        return None

def is_human_dirname(dirname):
    try:
        return dirname.startswith("Data-")
    except:
        return None

def generate_dirname():
    return hashlib.sha256(os.urandom(1024)).hexdigest()

def generate_leaker_id():
    return hashlib.sha256(os.urandom(1024)).hexdigest()

def generate_tulip_url():
    return hashlib.sha256(os.urandom(100)).hexdigest()

def generate_target_passphrase():
    number = ""
    for i in range(0,14):
        number += str(ord(os.urandom(1)) % 10)
    return (number, hashlib.sha256(number).hexdigest())

#
def alphanumeric(n):
    output = ""
    for i in range(1, n):
        output += random.choice(string.ascii_letters+string.digits)
    return output

########NEW FILE########
__FILENAME__ = virus-scan
#
# EXPERIMENTAL CODE - TO BE COMPLETED
#

###
### Submit a sample to VirusTotal and check the result.
### Based on example code by Bryce Boe, downloaded from:
### http://www.bryceboe.com/2010/09/01/submitting-binaries-to-virustotal/
###
### Needs Python 2.6 or 2.7
###
### Usage:
###  - Put your VirusTotal API key in the file virus-scan.key in the current
###    working directory (obtain from http://www.virustotal.com/advanced.html#publicapi)
###  - Run PATH/TO/PYTHON virus-scan.py FILE_TO_SCAN
###
### Copyright 2010 Steven J. Murdoch <http://www.cl.cam.ac.uk/users/sjm217/>
### See LICENSE for licensing information
###

import hashlib, httplib, mimetypes, os, pprint, json, sys, urlparse

DEFAULT_TYPE = 'application/octet-stream'

REPORT_URL = 'https://www.virustotal.com/api/get_file_report.json'
SCAN_URL = 'https://www.virustotal.com/api/scan_file.json'

API_KEY_FILE = 'virus-scan.key'

# The following function is modified from the snippet at:
# http://code.activestate.com/recipes/146306/
def encode_multipart_formdata(fields, files=()):
    """
    fields is a dictionary of name to value for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be
    uploaded as files.
    Return (content_type, body) ready for httplib.HTTP instance
    """
    BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
    CRLF = '\r\n'
    L = []
    for key, value in fields.items():
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"' % key)
        L.append('')
        L.append(value)
    for (key, filename, value) in files:
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"; filename="%s"' %
                 (key, filename))
        content_type = mimetypes.guess_type(filename)[0] or DEFAULT_TYPE
        L.append('Content-Type: %s' % content_type)
        L.append('')
        L.append(value)
    L.append('--' + BOUNDARY + '--')
    L.append('')
    body = CRLF.join(L)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body

def post_multipart(url, fields, files=()):
    """
    url is the full to send the post request to.
    fields is a dictionary of name to value for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be
    uploaded as files.
    Return body of http response.
    """
    content_type, data = encode_multipart_formdata(fields, files)
    url_parts = urlparse.urlparse(url)
    if url_parts.scheme == 'http':
        h = httplib.HTTPConnection(url_parts.netloc)
    elif url_parts.scheme == 'https':
        h = httplib.HTTPSConnection(url_parts.netloc)
    else:
        raise Exception('Unsupported URL scheme')
    path = urlparse.urlunparse(('', '') + url_parts[2:])
    h.request('POST', path, data, {'content-type':content_type})
    return h.getresponse().read()

def scan_file(filename, api_key):
    files = [('file', filename, open(filename, 'rb').read())]
    json_result = post_multipart(SCAN_URL, {'key':api_key}, files)
    return json.loads(json_result)

def get_report(filename, api_key):
    md5sum = hashlib.md5(open(filename, 'rb').read()).hexdigest()
    json_result = post_multipart(REPORT_URL, {'resource':md5sum, 'key':api_key})
    data = json.loads(json_result)
    if data['result'] != 1:
        print 'Result not found, submitting file.'
        data = scan_file(filename, api_key)
        if data['result'] == 1:
            print 'Submit successful.'
            print 'Please wait a few minutes and try again to receive report.'
            return 1
        else:
            print 'Submit failed.'
            pprint.pprint(data)
            return 1
    else:
        #pprint.pprint(data['report'])
        scan_date, result_dict = data['report']
        print "Scanned on:", scan_date

        failures = 0
        for av_name, result in result_dict.items():
            if result != '':
                failures += 1
                print " %20s: %s"%(av_name, result)
        if not failures:
            print 'SUCCESS: no AV detection triggered'
            return 0
        else:
            print 'FAIL: %s AV detection(s)'%failures
            return 255

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print 'Usage: %s filename' % sys.argv[0]
        sys.exit(1)

    try:
        key_fh = open(API_KEY_FILE, "rt")
        api_key = key_fh.readline().strip()
        key_fh.close()
    except IOError, e:
        print 'Failed to open API key file %s: %s' % (API_KEY_FILE, e)
        sys.exit(1)

    filename = sys.argv[1]
    if not os.path.isfile(filename):
        print '%s is not a valid file' % filename
        sys.exit(1)

    exit_status = get_report(filename, api_key)
    sys.exit(exit_status)

########NEW FILE########
__FILENAME__ = config
from __future__ import with_statement

from gluon.storage import Storage

import ConfigParser
import os.path

GLpathsegment = (os.path.abspath(__file__).rsplit('config.py')[0]).split('/')
# the previous code has been changed, because there was a bug. 
# homedirectory, or project dir 'globaleaks' 'GlobaLeaks'
# would broke this generation
projroot = '/'.join([str(x) for x in GLpathsegment[:-2]])
cfgfile = os.path.join(projroot, 'globaleaks', 'globaleaks.conf')

def copyform(form, settings):
    """Copy each form value into the specific settings subsection. """
    for name, value in form.iteritems():
        setattr(settings, name, value)
    settings.commit()

class ConfigFile(Storage):
    """
    A Storage-like class which loads and store each attribute into a portable
    conf file.
    """

    def __init__(self, cfgfile, section):

        if not os.access(cfgfile, os.R_OK|os.W_OK):
            print "Unable to open configuration file " + cfgfile
            quit()

        super(ConfigFile, self).__init__()

        self._cfgfile = cfgfile
        # setting up confgiparser
        self._cfgparser = ConfigParser.ConfigParser()
        self._cfgparser.read([self._cfgfile])
        self._section = section

    def __getattr__(self, name):
        if name.startswith('_'):
            return self.__dict__.get(name, None)

        try:
            value = self._cfgparser.get(self._section, name)
            if value.isdigit():
                return int(value)
            elif value.lower() in ('true', 'false'):
                return value.lower() == 'true'
            else:
                return value
        except ConfigParser.NoOptionError:
            return ''  # if option doesn't exists return an empty string

    def __setattr__(self, name, value):
        # keep an open port with private attributes
        if name.startswith('_'):
            self.__dict__[name] = value
            return

        try:
            # XXX: Automagically discover variable type
            self._cfgparser.set(self._section, name, value)
        except ConfigParser.NoOptionError:
            raise NameError(name)

    def commit(self):
        """
        Commit changes in config file.
        """
        with open(self._cfgfile, 'w') as cfgfile:
            self._cfgparser.write(cfgfile)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# globaleaks documentation build configuration file, created by
# sphinx-quickstart on Fri Sep 23 23:19:23 2011.
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
glpath = os.path.join(
        os.path.dirname(__file__),  # GlobaLeaks/docs/source
        '..',                       # GlobaLeaks/docs
        '..')                       # GlobaLeaks/

sys.path.insert(0, glpath)
# then import metadata from there
from applications import globaleaks

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['sourcetemplates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = globaleaks.__name__
copyright = globaleaks.__copyright__

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = globaleaks.__version__
# The full version, including alpha/beta/rc tags.
release = globaleaks.__version__

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
html_theme_options = dict(
        sidebarbgcolor='lightblue',
        linkcolor='blue',
        sidebarlinkcolor='lightred',
        )

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
html_logo = '../../applications/globaleaks/static/images/globaleaks.png'

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['static']

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
htmlhelp_basename = 'globaleaksdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'globaleaks.tex', u'globaleaks Documentation',
   u'Random Globaleaks Developer', 'manual'),
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

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'globaleaks', u'globaleaks Documentation',
     [u'Random Globaleaks Developer'], 1)
]

########NEW FILE########
__FILENAME__ = routes
default_application = 'globaleaks'
default_controller  = 'default'
default_function    = 'index'

routes_in = (
             ('^/tulip(/)?', '/globaleaks/tulip/index'),
             ('^/targets(/)?', '/globaleaks/admin/targets'),
             ('^/tulip/(?P<tulip_id>[\w]+)', '/globaleaks/tulip/status/\g<tulip_id>'),
             ('^/submit(/)?(?P<any>.*)', '/globaleaks/submission/\g<any>'),
             ('^/receiver(/)?', '/globaleaks/target/receiver'),
             ('^/bouquet/(?P<target_id>[\w]+)', '/globaleaks/target/bouquet/\g<target_id>'),
             ('^/bouquet', '/globaleaks/target/bouquet'),
             ('^/js', '/globaleaks/preload/js'),
             ('^/css', '/globaleaks/preload/css'),
             ('^/disclaimer', '/globaleaks/default/disclaimer')
            )



########NEW FILE########
__FILENAME__ = example
"""
The following is a simple example of TorCtl usage. This attaches a listener
that prints the amount of traffic going over tor each second.
"""

import time
import TorCtl

class BandwidthListener(TorCtl.PostEventListener):
  def __init__(self):
    TorCtl.PostEventListener.__init__(self)

  def bandwidth_event(self, event):
    print "tor read %i bytes and wrote %i bytes" % (event.read, event.written)

# constructs a listener that prints BW events
myListener = BandwidthListener()

# initiates a TorCtl connection, returning None if it was unsuccessful
conn = TorCtl.connect()

if conn:
  # tells tor to send us BW events
  conn.set_events(["BW"])

  # attaches the listener so it'll receive BW events
  conn.add_event_listener(myListener)

  # run until we get a keyboard interrupt
  try:
    while True:
      time.sleep(10)
  except KeyboardInterrupt: pass


########NEW FILE########
__FILENAME__ = GeoIPSupport
#!/usr/bin/python
# Copyright 2007 Johannes Renner and Mike Perry. See LICENSE file.

import struct
import socket
import TorCtl
import StatsSupport

from TorUtil import plog
try:
  import GeoIP
  # GeoIP data object: choose database here
  geoip = GeoIP.new(GeoIP.GEOIP_STANDARD)
  #geoip = GeoIP.open("./GeoLiteCity.dat", GeoIP.GEOIP_STANDARD)
except:
  plog("NOTICE", "No GeoIP library. GeoIPSupport.py will not work correctly")
  # XXX: How do we bail entirely..  


class Continent:
  """ Continent class: The group attribute is to partition the continents
      in groups, to determine the number of ocean crossings """
  def __init__(self, continent_code):
    self.code = continent_code 
    self.group = None
    self.countries = []

  def contains(self, country_code):
    return country_code in self.countries

# Set countries to continents
africa = Continent("AF")
africa.group = 1
africa.countries = ["AO","BF","BI","BJ","BV","BW","CD","CF","CG","CI","CM",
   "CV","DJ","DZ","EG","EH","ER","ET","GA","GH","GM","GN","GQ","GW","HM","KE",
   "KM","LR","LS","LY","MA","MG","ML","MR","MU","MW","MZ","NA","NE","NG","RE",
   "RW","SC","SD","SH","SL","SN","SO","ST","SZ","TD","TF","TG","TN","TZ","UG",
   "YT","ZA","ZM","ZR","ZW"]

asia = Continent("AS")
asia.group = 1
asia.countries = ["AP","AE","AF","AM","AZ","BD","BH","BN","BT","CC","CN","CX",
   "CY","GE","HK","ID","IL","IN","IO","IQ","IR","JO","JP","KG","KH","KP","KR",
   "KW","KZ","LA","LB","LK","MM","MN","MO","MV","MY","NP","OM","PH","PK","PS",
   "QA","RU","SA","SG","SY","TH","TJ","TM","TP","TR","TW","UZ","VN","YE"]

europe = Continent("EU")
europe.group = 1
europe.countries = ["EU","AD","AL","AT","BA","BE","BG","BY","CH","CZ","DE",
   "DK","EE","ES","FI","FO","FR","FX","GB","GI","GR","HR","HU","IE","IS","IT",
   "LI","LT","LU","LV","MC","MD","MK","MT","NL","NO","PL","PT","RO","SE","SI",
   "SJ","SK","SM","UA","VA","YU"]

oceania = Continent("OC")
oceania.group = 2
oceania.countries = ["AS","AU","CK","FJ","FM","GU","KI","MH","MP","NC","NF",
   "NR","NU","NZ","PF","PG","PN","PW","SB","TK","TO","TV","UM","VU","WF","WS"]

north_america = Continent("NA")
north_america.group = 0
north_america.countries = ["CA","MX","US"]

south_america = Continent("SA")
south_america.group = 0
south_america.countries = ["AG","AI","AN","AR","AW","BB","BM","BO","BR","BS",
   "BZ","CL","CO","CR","CU","DM","DO","EC","FK","GD","GF","GL","GP","GS","GT",
   "GY","HN","HT","JM","KN","KY","LC","MQ","MS","NI","PA","PE","PM","PR","PY",
   "SA","SR","SV","TC","TT","UY","VC","VE","VG","VI"]

# List of continents
continents = [africa, asia, europe, north_america, oceania, south_america]

def get_continent(country_code):
  """ Perform country -- continent mapping """
  for c in continents:
    if c.contains(country_code):
      return c
  plog("INFO", country_code + " is not on any continent")
  return None

def get_country(ip):
  """ Get the country via the library """
  return geoip.country_code_by_addr(ip)

def get_country_from_record(ip):
  """ Get the country code out of a GeoLiteCity record (not used) """
  record = geoip.record_by_addr(ip)
  if record != None:
    return record['country_code']

class GeoIPRouter(TorCtl.Router):
  # TODO: Its really shitty that this has to be a TorCtl.Router
  # and can't be a StatsRouter..
  """ Router class extended to GeoIP """
  def __init__(self, router):
    self.__dict__ = router.__dict__
    self.country_code = get_country(self.get_ip_dotted())
    if self.country_code != None: 
      c = get_continent(self.country_code)
      if c != None:
        self.continent = c.code
        self.cont_group = c.group
    else: 
      plog("INFO", self.nickname + ": Country code not found")
      self.continent = None
   
  def get_ip_dotted(self):
    """ Convert long int back to dotted quad string """
    return socket.inet_ntoa(struct.pack('>I', self.ip))

class GeoIPConfig:
  """ Class to configure GeoIP-based path building """
  def __init__(self, unique_countries=None, continent_crossings=4,
     ocean_crossings=None, entry_country=None, middle_country=None,
     exit_country=None, excludes=None):
    # TODO: Somehow ensure validity of a configuration:
    #   - continent_crossings >= ocean_crossings
    #   - unique_countries=False --> continent_crossings!=None
    #   - echelon? set entry_country to source and exit_country to None

    # Do not use a country twice in a route 
    # [True --> unique, False --> same or None --> pass] 
    self.unique_countries = unique_countries
    
    # Configure max continent crossings in one path 
    # [integer number 0-n or None --> ContinentJumper/UniqueContinent]
    self.continent_crossings = continent_crossings
    self.ocean_crossings = ocean_crossings
 
    # Try to find an exit node in the destination country
    # use exit_country as backup, if country cannot not be found
    self.echelon = False

    # Specify countries for positions [single country code or None]
    self.entry_country = entry_country
    self.middle_country = middle_country
    self.exit_country = exit_country

    # List of countries not to use in routes 
    # [(empty) list of country codes or None]
    self.excludes = excludes

########NEW FILE########
__FILENAME__ = PathSupport
#!/usr/bin/python
# Copyright 2007-2010 Mike Perry. See LICENSE file.
"""

Support classes for path construction

The PathSupport package builds on top of TorCtl.TorCtl. It provides a
number of interfaces that make path construction easier.

The inheritance diagram for event handling is as follows:
TorCtl.EventHandler <- TorCtl.ConsensusTracker <- PathBuilder 
  <- CircuitHandler <- StreamHandler.

Basically, EventHandler is what gets all the control port events
packaged in nice clean classes (see help(TorCtl) for information on
those). 

ConsensusTracker tracks the NEWCONSENSUS and NEWDESC events to maintain
a view of the network that is consistent with the Tor client's current
consensus.

PathBuilder inherits from ConsensusTracker and is what builds all
circuits based on the requirements specified in the SelectionManager
instance passed to its constructor. It also handles attaching streams to
circuits. It only handles one building one circuit at a time.

CircuitHandler optionally inherits from PathBuilder, and overrides its
circuit event handling to manage building a pool of circuits as opposed
to just one. It still uses the SelectionManager for path selection.

StreamHandler inherits from CircuitHandler, and is what governs the
attachment of an incoming stream on to one of the multiple circuits of
the circuit handler. 

The SelectionManager is essentially a configuration wrapper around the
most elegant portions of TorFlow: NodeGenerators, NodeRestrictions, and
PathRestrictions. It extends from a BaseSelectionManager that provides
a basic example of using these mechanisms for custom implementations.

In the SelectionManager, a NodeGenerator is used to choose the nodes
probabilistically according to some distribution while obeying the
NodeRestrictions. These generators (one per hop) are handed off to the
PathSelector, which uses the generators to build a complete path that
satisfies the PathRestriction requirements.

Have a look at the class hierarchy directly below to get a feel for how
the restrictions fit together, and what options are available.

"""

import TorCtl
import re
import struct
import random
import socket
import copy
import Queue
import time
import TorUtil
import traceback
import threading
from TorUtil import *

import sys
if sys.version_info < (2, 5):
  from sets import Set as set

__all__ = ["NodeRestrictionList", "PathRestrictionList",
"PercentileRestriction", "OSRestriction", "ConserveExitsRestriction",
"FlagsRestriction", "MinBWRestriction", "VersionIncludeRestriction",
"VersionExcludeRestriction", "VersionRangeRestriction",
"ExitPolicyRestriction", "NodeRestriction", "PathRestriction",
"OrNodeRestriction", "MetaNodeRestriction", "AtLeastNNodeRestriction",
"NotNodeRestriction", "Subnet16Restriction", "UniqueRestriction",
"NodeGenerator", "UniformGenerator", "OrderedExitGenerator",
"BwWeightedGenerator", "PathSelector", "Connection", "NickRestriction",
"IdHexRestriction", "PathBuilder", "CircuitHandler", "StreamHandler",
"SelectionManager", "BaseSelectionManager", "CountryCodeRestriction",
"CountryRestriction", "UniqueCountryRestriction", "SingleCountryRestriction",
"ContinentRestriction", "ContinentJumperRestriction",
"UniqueContinentRestriction", "MetaPathRestriction", "RateLimitedRestriction",
"SmartSocket"]

#################### Path Support Interfaces #####################

class RestrictionError(Exception):
  "Error raised for issues with applying restrictions"
  pass

class NoNodesRemain(RestrictionError):
  "Error raised for issues with applying restrictions"
  pass

class NodeRestriction:
  "Interface for node restriction policies"
  def r_is_ok(self, r):
    "Returns true if Router 'r' is acceptable for this restriction"
    return True  

class PathRestriction:
  "Interface for path restriction policies"
  def path_is_ok(self, path):
    "Return true if the list of Routers in path satisfies this restriction"
    return True  

# TODO: Or, Not, N of M
class MetaPathRestriction(PathRestriction):
  "MetaPathRestrictions are path restriction aggregators."
  def add_restriction(self, rstr): raise NotImplemented()
  def del_restriction(self, RestrictionClass): raise NotImplemented()
 
class PathRestrictionList(MetaPathRestriction):
  """Class to manage a list of PathRestrictions"""
  def __init__(self, restrictions):
    "Constructor. 'restrictions' is a list of PathRestriction instances"
    self.restrictions = restrictions
  
  def path_is_ok(self, path):
    "Given list if Routers in 'path', check it against each restriction."
    for rs in self.restrictions:
      if not rs.path_is_ok(path):
        return False
    return True

  def add_restriction(self, rstr):
    "Add a PathRestriction 'rstr' to the list"
    self.restrictions.append(rstr)

  def del_restriction(self, RestrictionClass):
    "Remove all PathRestrictions of type RestrictionClass from the list."
    self.restrictions = filter(
        lambda r: not isinstance(r, RestrictionClass),
          self.restrictions)

  def __str__(self):
    return self.__class__.__name__+"("+str(map(str, self.restrictions))+")"

class NodeGenerator:
  "Interface for node generation"
  def __init__(self, sorted_r, rstr_list):
    """Constructor. Takes a bandwidth-sorted list of Routers 'sorted_r' 
    and a NodeRestrictionList 'rstr_list'"""
    self.rstr_list = rstr_list
    self.rebuild(sorted_r)

  def reset_restriction(self, rstr_list):
    "Reset the restriction list to a new list"
    self.rstr_list = rstr_list
    self.rebuild()

  def rewind(self):
    "Rewind the generator to the 'beginning'"
    self.routers = copy.copy(self.rstr_routers)
    if not self.routers:
      plog("NOTICE", "No routers left after restrictions applied: "+str(self.rstr_list))
      raise NoNodesRemain(str(self.rstr_list))
 
  def rebuild(self, sorted_r=None):
    """ Extra step to be performed when new routers are added or when
    the restrictions change. """
    if sorted_r != None:
      self.sorted_r = sorted_r
    self.rstr_routers = filter(lambda r: self.rstr_list.r_is_ok(r), self.sorted_r)
    if not self.rstr_routers:
      plog("NOTICE", "No routers left after restrictions applied: "+str(self.rstr_list))
      raise NoNodesRemain(str(self.rstr_list))

  def mark_chosen(self, r):
    """Mark a router as chosen: remove it from the list of routers 
     that can be returned in the future"""
    self.routers.remove(r)

  def all_chosen(self):
    "Return true if all the routers have been marked as chosen"
    return not self.routers

  def generate(self):
    "Return a python generator that yields routers according to the policy"
    raise NotImplemented()

class Connection(TorCtl.Connection):
  """Extended Connection class that provides a method for building circuits"""
  def __init__(self, sock):
    TorCtl.Connection.__init__(self,sock)
  def build_circuit(self, path):
    "Tell Tor to build a circuit chosen by the PathSelector 'path_sel'"
    circ = Circuit()
    circ.path = path
    circ.exit = circ.path[len(path)-1]
    circ.circ_id = self.extend_circuit(0, circ.id_path())
    return circ

######################## Node Restrictions ########################

# TODO: We still need more path support implementations
#  - NodeRestrictions:
#    - Uptime/LongLivedPorts (Does/should hibernation count?)
#    - Published/Updated
#    - Add a /8 restriction for ExitPolicy?
#  - PathRestrictions:
#    - NodeFamily
#    - GeoIP:
#      - Mathematical/empirical study of predecessor expectation
#        - If middle node on the same continent as exit, exit learns nothing
#        - else, exit has a bias on the continent of origin of user
#          - Language and browser accept string determine this anyway
#      - ContinentRestrictor (avoids doing more than N continent crossings)
#      - EchelonPhobicRestrictor
#        - Does not cross international boundaries for client->Entry or
#          Exit->destination hops

class PercentileRestriction(NodeRestriction):
  """Restriction to cut out a percentile slice of the network."""
  def __init__(self, pct_skip, pct_fast, r_list):
    """Constructor. Sets up the restriction such that routers in the 
     'pct_skip' to 'pct_fast' percentile of bandwidth rankings are 
     returned from the sorted list 'r_list'"""
    self.pct_fast = pct_fast
    self.pct_skip = pct_skip
    self.sorted_r = r_list

  def r_is_ok(self, r):
    "Returns true if r is in the percentile boundaries (by rank)"
    if r.list_rank < len(self.sorted_r)*self.pct_skip/100: return False
    elif r.list_rank > len(self.sorted_r)*self.pct_fast/100: return False
    
    return True

  def __str__(self):
    return self.__class__.__name__+"("+str(self.pct_skip)+","+str(self.pct_fast)+")"

class RatioPercentileRestriction(NodeRestriction):
  """Restriction to cut out a percentile slice of the network by ratio of
     consensus bw to descriptor bw."""
  def __init__(self, pct_skip, pct_fast, r_list):
    """Constructor. Sets up the restriction such that routers in the
     'pct_skip' to 'pct_fast' percentile of bandwidth rankings are
     returned from the sorted list 'r_list'"""
    self.pct_fast = pct_fast
    self.pct_skip = pct_skip
    self.sorted_r = r_list

  def r_is_ok(self, r):
    "Returns true if r is in the percentile boundaries (by rank)"
    if r.ratio_rank < len(self.sorted_r)*self.pct_skip/100: return False
    elif r.ratio_rank > len(self.sorted_r)*self.pct_fast/100: return False

    return True

  def __str__(self):
    return self.__class__.__name__+"("+str(self.pct_skip)+","+str(self.pct_fast)+")"

class UptimeRestriction(NodeRestriction):
  """Restriction to filter out routers with uptimes < min_uptime or
     > max_uptime"""
  def __init__(self, min_uptime=None, max_uptime=None):
    self.min_uptime = min_uptime
    self.max_uptime = max_uptime

  def r_is_ok(self, r):
    "Returns true if r is in the uptime boundaries"
    if self.min_uptime and r.uptime < self.min_uptime: return False
    if self.max_uptime and r.uptime > self.max_uptime: return False
    return True

class RankRestriction(NodeRestriction):
  """Restriction to cut out a list-rank slice of the network."""
  def __init__(self, rank_skip, rank_stop):
    self.rank_skip = rank_skip
    self.rank_stop = rank_stop

  def r_is_ok(self, r):
    "Returns true if r is in the boundaries (by rank)"
    if r.list_rank < self.rank_skip: return False
    elif r.list_rank > self.rank_stop: return False
    
    return True

  def __str__(self):
    return self.__class__.__name__+"("+str(self.rank_skip)+","+str(self.rank_stop)+")"
    
class OSRestriction(NodeRestriction):
  "Restriction based on operating system"
  def __init__(self, ok, bad=[]):
    """Constructor. Accept router OSes that match regexes in 'ok', 
       rejects those that match regexes in 'bad'."""
    self.ok = ok
    self.bad = bad

  def r_is_ok(self, r):
    "Returns true if r is in 'ok', false if 'r' is in 'bad'. If 'ok'"
    for y in self.ok:
      if re.search(y, r.os):
        return True
    for b in self.bad:
      if re.search(b, r.os):
        return False
    if self.ok: return False
    if self.bad: return True

  def __str__(self):
    return self.__class__.__name__+"("+str(self.ok)+","+str(self.bad)+")"

class ConserveExitsRestriction(NodeRestriction):
  "Restriction to reject exits from selection"
  def __init__(self, exit_ports=None):
    self.exit_ports = exit_ports

  def r_is_ok(self, r):
    if self.exit_ports:
      for port in self.exit_ports:
        if r.will_exit_to("255.255.255.255", port):
          return False
      return True
    return not "Exit" in r.flags

  def __str__(self):
    return self.__class__.__name__+"()"

class FlagsRestriction(NodeRestriction):
  "Restriction for mandatory and forbidden router flags"
  def __init__(self, mandatory, forbidden=[]):
    """Constructor. 'mandatory' and 'forbidden' are both lists of router 
     flags as strings."""
    self.mandatory = mandatory
    self.forbidden = forbidden

  def r_is_ok(self, router):
    for m in self.mandatory:
      if not m in router.flags: return False
    for f in self.forbidden:
      if f in router.flags: return False
    return True

  def __str__(self):
    return self.__class__.__name__+"("+str(self.mandatory)+","+str(self.forbidden)+")"

class NickRestriction(NodeRestriction):
  """Require that the node nickname is as specified"""
  def __init__(self, nickname):
    self.nickname = nickname

  def r_is_ok(self, router):
    return router.nickname == self.nickname

  def __str__(self):
    return self.__class__.__name__+"("+str(self.nickname)+")"

class IdHexRestriction(NodeRestriction):
  """Require that the node idhash is as specified"""
  def __init__(self, idhex):
    if idhex[0] == '$':
      self.idhex = idhex[1:].upper()
    else:
      self.idhex = idhex.upper()

  def r_is_ok(self, router):
    return router.idhex == self.idhex

  def __str__(self):
    return self.__class__.__name__+"("+str(self.idhex)+")"
 
class MinBWRestriction(NodeRestriction):
  """Require a minimum bandwidth"""
  def __init__(self, minbw):
    self.min_bw = minbw

  def r_is_ok(self, router): return router.bw >= self.min_bw

  def __str__(self):
    return self.__class__.__name__+"("+str(self.min_bw)+")"

class RateLimitedRestriction(NodeRestriction):
  def __init__(self, limited=True):
    self.limited = limited

  def r_is_ok(self, router): return router.rate_limited == self.limited

  def __str__(self):
    return self.__class__.__name__+"("+str(self.limited)+")"
   
class VersionIncludeRestriction(NodeRestriction):
  """Require that the version match one in the list"""
  def __init__(self, eq):
    "Constructor. 'eq' is a list of versions as strings"
    self.eq = map(TorCtl.RouterVersion, eq)
  
  def r_is_ok(self, router):
    """Returns true if the version of 'router' matches one of the 
     specified versions."""
    for e in self.eq:
      if e == router.version:
        return True
    return False

  def __str__(self):
    return self.__class__.__name__+"("+str(self.eq)+")"

class VersionExcludeRestriction(NodeRestriction):
  """Require that the version not match one in the list"""
  def __init__(self, exclude):
    "Constructor. 'exclude' is a list of versions as strings"
    self.exclude = map(TorCtl.RouterVersion, exclude)
  
  def r_is_ok(self, router):
    """Returns false if the version of 'router' matches one of the 
     specified versions."""
    for e in self.exclude:
      if e == router.version:
        return False
    return True

  def __str__(self):
    return self.__class__.__name__+"("+str(map(str, self.exclude))+")"

class VersionRangeRestriction(NodeRestriction):
  """Require that the versions be inside a specified range""" 
  def __init__(self, gr_eq, less_eq=None):
    self.gr_eq = TorCtl.RouterVersion(gr_eq)
    if less_eq: self.less_eq = TorCtl.RouterVersion(less_eq)
    else: self.less_eq = None
  
  def r_is_ok(self, router):
    return (not self.gr_eq or router.version >= self.gr_eq) and \
        (not self.less_eq or router.version <= self.less_eq)

  def __str__(self):
    return self.__class__.__name__+"("+str(self.gr_eq)+","+str(self.less_eq)+")"

class ExitPolicyRestriction(NodeRestriction):
  """Require that a router exit to an ip+port"""
  def __init__(self, to_ip, to_port):
    self.to_ip = to_ip
    self.to_port = to_port

  def r_is_ok(self, r): return r.will_exit_to(self.to_ip, self.to_port)

  def __str__(self):
    return self.__class__.__name__+"("+str(self.to_ip)+","+str(self.to_port)+")"

class MetaNodeRestriction(NodeRestriction):
  """Interface for a NodeRestriction that is an expression consisting of 
     multiple other NodeRestrictions"""
  def add_restriction(self, rstr): raise NotImplemented()
  # TODO: these should collapse the restriction and return a new
  # instance for re-insertion (or None)
  def next_rstr(self): raise NotImplemented()
  def del_restriction(self, RestrictionClass): raise NotImplemented()

class OrNodeRestriction(MetaNodeRestriction):
  """MetaNodeRestriction that is the boolean or of two or more
     NodeRestrictions"""
  def __init__(self, rs):
    "Constructor. 'rs' is a list of NodeRestrictions"
    self.rstrs = rs

  def r_is_ok(self, r):
    "Returns true if one of 'rs' is true for this router"
    for rs in self.rstrs:
      if rs.r_is_ok(r):
        return True
    return False

  def __str__(self):
    return self.__class__.__name__+"("+str(map(str, self.rstrs))+")"

class NotNodeRestriction(MetaNodeRestriction):
  """Negates a single restriction"""
  def __init__(self, a):
    self.a = a

  def r_is_ok(self, r): return not self.a.r_is_ok(r)

  def __str__(self):
    return self.__class__.__name__+"("+str(self.a)+")"

class AtLeastNNodeRestriction(MetaNodeRestriction):
  """MetaNodeRestriction that is true if at least n member 
     restrictions are true."""
  def __init__(self, rstrs, n):
    self.rstrs = rstrs
    self.n = n

  def r_is_ok(self, r):
    cnt = 0
    for rs in self.rstrs:
      if rs.r_is_ok(r):
        cnt += 1
    if cnt < self.n: return False
    else: return True

  def __str__(self):
    return self.__class__.__name__+"("+str(map(str, self.rstrs))+","+str(self.n)+")"

class NodeRestrictionList(MetaNodeRestriction):
  "Class to manage a list of NodeRestrictions"
  def __init__(self, restrictions):
    "Constructor. 'restrictions' is a list of NodeRestriction instances"
    self.restrictions = restrictions

  def r_is_ok(self, r):
    "Returns true of Router 'r' passes all of the contained restrictions"
    for rs in self.restrictions:
      if not rs.r_is_ok(r): return False
    return True

  def add_restriction(self, restr):
    "Add a NodeRestriction 'restr' to the list of restrictions"
    self.restrictions.append(restr)

  # TODO: This does not collapse meta restrictions..
  def del_restriction(self, RestrictionClass):
    """Remove all restrictions of type RestrictionClass from the list.
       Does NOT inspect or collapse MetaNode Restrictions (though 
       MetaRestrictions can be removed if RestrictionClass is 
       MetaNodeRestriction)"""
    self.restrictions = filter(
        lambda r: not isinstance(r, RestrictionClass),
          self.restrictions)
  
  def clear(self):
    """ Remove all restrictions """
    self.restrictions = []

  def __str__(self):
    return self.__class__.__name__+"("+str(map(str, self.restrictions))+")"


#################### Path Restrictions #####################

class Subnet16Restriction(PathRestriction):
  """PathRestriction that mandates that no two nodes from the same 
     /16 subnet be in the path"""
  def path_is_ok(self, path):
    mask16 = struct.unpack(">I", socket.inet_aton("255.255.0.0"))[0]
    ip16 = path[0].ip & mask16
    for r in path[1:]:
      if ip16 == (r.ip & mask16):
        return False
    return True

  def __str__(self):
    return self.__class__.__name__+"()"

class UniqueRestriction(PathRestriction):
  """Path restriction that mandates that the same router can't appear more
     than once in a path"""
  def path_is_ok(self, path):
    for i in xrange(0,len(path)):
      if path[i] in path[:i]:
        return False
    return True

  def __str__(self):
    return self.__class__.__name__+"()"

#################### GeoIP Restrictions ###################

class CountryCodeRestriction(NodeRestriction):
  """ Ensure that the country_code is set """
  def r_is_ok(self, r):
    return r.country_code != None

  def __str__(self):
    return self.__class__.__name__+"()"

class CountryRestriction(NodeRestriction):
  """ Only accept nodes that are in 'country_code' """
  def __init__(self, country_code):
    self.country_code = country_code

  def r_is_ok(self, r):
    return r.country_code == self.country_code

  def __str__(self):
    return self.__class__.__name__+"("+str(self.country_code)+")"

class ExcludeCountriesRestriction(NodeRestriction):
  """ Exclude a list of countries """
  def __init__(self, countries):
    self.countries = countries

  def r_is_ok(self, r):
    return not (r.country_code in self.countries)

  def __str__(self):
    return self.__class__.__name__+"("+str(self.countries)+")"

class UniqueCountryRestriction(PathRestriction):
  """ Ensure every router to have a distinct country_code """
  def path_is_ok(self, path):
    for i in xrange(0, len(path)-1):
      for j in xrange(i+1, len(path)):
        if path[i].country_code == path[j].country_code:
          return False;
    return True;

  def __str__(self):
    return self.__class__.__name__+"()"

class SingleCountryRestriction(PathRestriction):
  """ Ensure every router to have the same country_code """
  def path_is_ok(self, path):
    country_code = path[0].country_code
    for r in path:
      if country_code != r.country_code:
        return False
    return True

  def __str__(self):
    return self.__class__.__name__+"()"

class ContinentRestriction(PathRestriction):
  """ Do not more than n continent crossings """
  # TODO: Add src and dest
  def __init__(self, n, src=None, dest=None):
    self.n = n

  def path_is_ok(self, path):
    crossings = 0
    prev = None
    # Compute crossings until now
    for r in path:
      # Jump over the first router
      if prev:
        if r.continent != prev.continent:
          crossings += 1
      prev = r
    if crossings > self.n: return False
    else: return True

  def __str__(self):
    return self.__class__.__name__+"("+str(self.n)+")"

class ContinentJumperRestriction(PathRestriction):
  """ Ensure continent crossings between all hops """
  def path_is_ok(self, path):
    prev = None
    for r in path:
      # Jump over the first router
      if prev:
        if r.continent == prev.continent:
          return False
      prev = r
    return True

  def __str__(self):
    return self.__class__.__name__+"()"

class UniqueContinentRestriction(PathRestriction):
  """ Ensure every hop to be on a different continent """
  def path_is_ok(self, path):
    for i in xrange(0, len(path)-1):
      for j in xrange(i+1, len(path)):
        if path[i].continent == path[j].continent:
          return False;
    return True;

  def __str__(self):
    return self.__class__.__name__+"()"

class OceanPhobicRestriction(PathRestriction):
  """ Not more than n ocean crossings """
  # TODO: Add src and dest
  def __init__(self, n, src=None, dest=None):
    self.n = n

  def path_is_ok(self, path):
    crossings = 0
    prev = None
    # Compute ocean crossings until now
    for r in path:
      # Jump over the first router
      if prev:
        if r.cont_group != prev.cont_group:
          crossings += 1
      prev = r
    if crossings > self.n: return False
    else: return True

  def __str__(self):
    return self.__class__.__name__+"("+str(self.n)+")"

#################### Node Generators ######################

class UniformGenerator(NodeGenerator):
  """NodeGenerator that produces nodes in the uniform distribution"""
  def generate(self):
    # XXX: hrmm.. this is not really the right thing to check
    while not self.all_chosen():
      yield random.choice(self.routers)
     
class ExactUniformGenerator(NodeGenerator):
  """NodeGenerator that produces nodes randomly, yet strictly uniformly 
     over time"""
  def __init__(self, sorted_r, rstr_list, position=0):
    self.position = position
    NodeGenerator.__init__(self, sorted_r, rstr_list)  

  def generate(self):
    min_gen = min(map(lambda r: r._generated[self.position], self.routers))
    choices = filter(lambda r: r._generated[self.position]==min_gen, 
                       self.routers)
    while choices:
      r = random.choice(choices)
      yield r
      choices.remove(r)

    choices = filter(lambda r: r._generated[self.position]==min_gen,
                       self.routers)
    plog("NOTICE", "Ran out of choices in ExactUniformGenerator. Incrementing nodes")
    for r in choices:
      r._generated[self.position] += 1

  def mark_chosen(self, r):
    r._generated[self.position] += 1
    NodeGenerator.mark_chosen(self, r)

  def rebuild(self, sorted_r=None):
    plog("DEBUG", "Rebuilding ExactUniformGenerator")
    NodeGenerator.rebuild(self, sorted_r)
    for r in self.rstr_routers:
      lgen = len(r._generated)
      if lgen < self.position+1:
        for i in xrange(lgen, self.position+1):
          r._generated.append(0)


class OrderedExitGenerator(NodeGenerator):
  """NodeGenerator that produces exits in an ordered fashion for a 
     specific port"""
  def __init__(self, to_port, sorted_r, rstr_list):
    self.to_port = to_port
    self.next_exit_by_port = {}
    NodeGenerator.__init__(self, sorted_r, rstr_list)

  def rewind(self):
    NodeGenerator.rewind(self)
    if self.to_port not in self.next_exit_by_port or not self.next_exit_by_port[self.to_port]:
      self.next_exit_by_port[self.to_port] = 0
      self.last_idx = len(self.routers)
    else:
      self.last_idx = self.next_exit_by_port[self.to_port]

  def set_port(self, port):
    self.to_port = port
    self.rewind()
     
  def mark_chosen(self, r):
    self.next_exit_by_port[self.to_port] += 1
  
  def all_chosen(self):
    return self.last_idx == self.next_exit_by_port[self.to_port]

  def generate(self):
    while True: # A do..while would be real nice here..
      if self.next_exit_by_port[self.to_port] >= len(self.routers):
        self.next_exit_by_port[self.to_port] = 0
      yield self.routers[self.next_exit_by_port[self.to_port]]
      self.next_exit_by_port[self.to_port] += 1
      if self.last_idx == self.next_exit_by_port[self.to_port]:
        break

class BwWeightedGenerator(NodeGenerator):
  """

  This is a generator designed to match the Tor Path Selection
  algorithm.  It will generate nodes weighted by their bandwidth,
  but take the appropriate weighting into account against guard
  nodes and exit nodes when they are chosen for positions other
  than guard/exit. For background see:
  routerlist.c::smartlist_choose_by_bandwidth(),
  http://archives.seul.org/or/dev/Jul-2007/msg00021.html,
  http://archives.seul.org/or/dev/Jul-2007/msg00056.html, and
  https://tor-svn.freehaven.net/svn/tor/trunk/doc/spec/path-spec.txt
  The formulas used are from the first or-dev link, but are proven
  optimal and equivalent to the ones now used in routerlist.c in the 
  second or-dev link.
  
  """ 
  def __init__(self, sorted_r, rstr_list, pathlen, exit=False, guard=False):
    """ Pass exit=True to create a generator for exit-nodes """
    self.max_bandwidth = 10000000
    # Out for an exit-node?
    self.exit = exit
    # Is this a guard node? 
    self.guard = guard
    # Different sums of bandwidths
    self.total_bw = 0
    self.total_exit_bw = 0
    self.total_guard_bw = 0
    self.total_weighted_bw = 0
    self.pathlen = pathlen
    NodeGenerator.__init__(self, sorted_r, rstr_list)

  def rebuild(self, sorted_r=None):
    NodeGenerator.rebuild(self, sorted_r)
    NodeGenerator.rewind(self)
    # Set the exit_weight
    # We are choosing a non-exit
    self.total_exit_bw = 0
    self.total_guard_bw = 0
    self.total_bw = 0
    for r in self.routers:
      # TODO: Check max_bandwidth and cap...
      self.total_bw += r.bw
      if "Exit" in r.flags:
        self.total_exit_bw += r.bw
      if "Guard" in r.flags:
        self.total_guard_bw += r.bw

    bw_per_hop = (1.0*self.total_bw)/self.pathlen

    # Print some debugging info about bandwidth ratios
    if self.total_bw > 0:
      e_ratio = self.total_exit_bw/float(self.total_bw)
      g_ratio = self.total_guard_bw/float(self.total_bw)
    else:
      g_ratio = 0
      e_ratio = 0
    plog("DEBUG",
       "E = " + str(self.total_exit_bw) +
       ", G = " + str(self.total_guard_bw) +
       ", T = " + str(self.total_bw) +
       ", g_ratio = " + str(g_ratio) + ", e_ratio = " +str(e_ratio) +
       ", bw_per_hop = " + str(bw_per_hop))
   
    if self.exit:
      self.exit_weight = 1.0
    else:
      if self.total_exit_bw < bw_per_hop:
        # Don't use exit nodes at all
        self.exit_weight = 0
      else:
        if self.total_exit_bw > 0:
          self.exit_weight = ((self.total_exit_bw-bw_per_hop)/self.total_exit_bw)
        else: self.exit_weight = 0

    if self.guard:
      self.guard_weight = 1.0
    else:
      if self.total_guard_bw < bw_per_hop:
        # Don't use exit nodes at all
        self.guard_weight = 0
      else:
        if self.total_guard_bw > 0:
          self.guard_weight = ((self.total_guard_bw-bw_per_hop)/self.total_guard_bw)
        else: self.guard_weight = 0
    
    for r in self.routers:
      bw = r.bw
      if "Exit" in r.flags:
        bw *= self.exit_weight
      if "Guard" in r.flags:
        bw *= self.guard_weight
      self.total_weighted_bw += bw

    self.total_weighted_bw = int(self.total_weighted_bw)
    plog("DEBUG", "Bw: "+str(self.total_weighted_bw)+"/"+str(self.total_bw)
          +". The exit-weight is: "+str(self.exit_weight)
          + ", guard weight is: "+str(self.guard_weight))

  def generate(self):
    while True:
      # Choose a suitable random int
      i = random.randint(0, self.total_weighted_bw)

      # Go through the routers
      for r in self.routers:
        # Below zero here means next() -> choose a new random int+router 
        if i < 0: break
        bw = r.bw
        if "Exit" in r.flags:
          bw *= self.exit_weight
        if "Guard" in r.flags:
          bw *= self.guard_weight

        i -= bw
        if i < 0:
          plog("DEBUG", "Chosen router with a bandwidth of: " + str(r.bw))
          yield r

####################### Secret Sauce ###########################

class PathError(Exception):
  pass

class NoRouters(PathError):
  pass

class PathSelector:
  """Implementation of path selection policies. Builds a path according
     to entry, middle, and exit generators that satisfies the path 
     restrictions."""
  def __init__(self, entry_gen, mid_gen, exit_gen, path_restrict):
    """Constructor. The first three arguments are NodeGenerators with 
     their appropriate restrictions. The 'path_restrict' is a
     PathRestrictionList"""
    self.entry_gen = entry_gen
    self.mid_gen = mid_gen
    self.exit_gen = exit_gen
    self.path_restrict = path_restrict

  def rebuild_gens(self, sorted_r):
    "Rebuild the 3 generators with a new sorted router list"
    self.entry_gen.rebuild(sorted_r)
    self.mid_gen.rebuild(sorted_r)
    self.exit_gen.rebuild(sorted_r)

  def select_path(self, pathlen):
    """Creates a path of 'pathlen' hops, and returns it as a list of
       Router instances"""
    self.entry_gen.rewind()
    self.mid_gen.rewind()
    self.exit_gen.rewind()
    entry = self.entry_gen.generate()
    mid = self.mid_gen.generate()
    ext = self.exit_gen.generate()
      
    plog("DEBUG", "Selecting path..")

    while True:
      path = []
      plog("DEBUG", "Building path..")
      try:
        if pathlen == 1:
          path = [ext.next()]
        else:
          path.append(entry.next())
          for i in xrange(1, pathlen-1):
            path.append(mid.next())
          path.append(ext.next())
        if self.path_restrict.path_is_ok(path):
          self.entry_gen.mark_chosen(path[0])
          for i in xrange(1, pathlen-1):
            self.mid_gen.mark_chosen(path[i])
          self.exit_gen.mark_chosen(path[pathlen-1])
          plog("DEBUG", "Marked path.")
          break
        else:
          plog("DEBUG", "Path rejected by path restrictions.")
      except StopIteration:
        plog("NOTICE", "Ran out of routers during buildpath..");
        self.entry_gen.rewind()
        self.mid_gen.rewind()
        self.exit_gen.rewind()
        entry = self.entry_gen.generate()
        mid = self.mid_gen.generate()
        ext = self.exit_gen.generate()
    for r in path:
      r.refcount += 1
      plog("DEBUG", "Circ refcount "+str(r.refcount)+" for "+r.idhex)
    return path

# TODO: Implement example manager.
class BaseSelectionManager:
   """
   The BaseSelectionManager is a minimalistic node selection manager.

   It is meant to be used with a PathSelector that consists of an
   entry NodeGenerator, a middle NodeGenerator, and an exit NodeGenerator.

   However, none of these are absolutely necessary. It is possible
   to completely avoid them if you wish by hacking whatever selection
   mechanisms you want straight into this interface and then passing
   an instance to a PathBuilder implementation.
   """
   def __init__(self):
     self.bad_restrictions = False
     self.consensus = None

   def reconfigure(self, consensus=None):
     """ 
     This method is called whenever a significant configuration change
     occurs. Currently, this only happens via PathBuilder.__init__ and
     PathBuilder.schedule_selmgr().
     
     This method should NOT throw any exceptions.
     """
     pass

   def new_consensus(self, consensus):
     """ 
     This method is called whenever a consensus change occurs.
     
     This method should NOT throw any exceptions.
     """
     pass

   def set_exit(self, exit_name):
     """
     This method provides notification that a fixed exit is desired.

     This method should NOT throw any exceptions.
     """
     pass

   def set_target(self, host, port):
     """
     This method provides notification that a new target endpoint is
     desired.

     May throw a RestrictionError if target is impossible to reach.
     """
     pass

   def select_path(self):
     """
     Returns a new path in the form of a list() of Router instances.

     May throw a RestrictionError.
     """
     pass

class SelectionManager(BaseSelectionManager):
  """Helper class to handle configuration updates
    
    The methods are NOT threadsafe. They may ONLY be called from
    EventHandler's thread. This means that to update the selection 
    manager, you must schedule a config update job using 
    PathBuilder.schedule_selmgr() with a worker function to modify 
    this object.
 
    XXX: Warning. The constructor of this class is subject to change
    and may undergo reorganization in the near future. Watch for falling 
    bits.
    """
  # XXX: Hrmm, consider simplifying this. It is confusing and unweildy.
  def __init__(self, pathlen, order_exits,
         percent_fast, percent_skip, min_bw, use_all_exits,
         uniform, use_exit, use_guards,geoip_config=None,
         restrict_guards=False, extra_node_rstr=None, exit_ports=None,
         order_by_ratio=False):
    BaseSelectionManager.__init__(self)
    self.__ordered_exit_gen = None 
    self.pathlen = pathlen
    self.order_exits = order_exits
    self.percent_fast = percent_fast
    self.percent_skip = percent_skip
    self.min_bw = min_bw
    self.use_all_exits = use_all_exits
    self.uniform = uniform
    self.exit_id = use_exit
    self.use_guards = use_guards
    self.geoip_config = geoip_config
    self.restrict_guards_only = restrict_guards
    self.bad_restrictions = False
    self.consensus = None
    self.exit_ports = exit_ports
    self.extra_node_rstr=extra_node_rstr
    self.order_by_ratio = order_by_ratio

  def reconfigure(self, consensus=None):
    try:
      self._reconfigure(consensus)
      self.bad_restrictions = False
    except NoNodesRemain:
      plog("WARN", "No nodes remain in selection manager")
      self.bad_restrictions = True
    return self.bad_restrictions

  def _reconfigure(self, consensus=None):
    """This function is called after a configuration change, 
     to rebuild the RestrictionLists."""
    if consensus: 
      plog("DEBUG", "Reconfigure with consensus")
      self.consensus = consensus
    else:
      plog("DEBUG", "Reconfigure without consensus")

    sorted_r = self.consensus.sorted_r

    if self.use_all_exits:
      self.path_rstr = PathRestrictionList([UniqueRestriction()])
    else:
      self.path_rstr = PathRestrictionList(
           [Subnet16Restriction(), UniqueRestriction()])
  
    if self.use_guards: entry_flags = ["Guard", "Running", "Fast"]
    else: entry_flags = ["Running", "Fast"]

    if self.restrict_guards_only:
      nonentry_skip = 0
      nonentry_fast = 100
    else:
      nonentry_skip = self.percent_skip
      nonentry_fast = self.percent_fast

    if self.order_by_ratio:
      PctRstr = RatioPercentileRestriction
    else:
      PctRstr = PercentileRestriction

    # XXX: sometimes we want the ability to do uniform scans
    # without the conserve exit restrictions..
    entry_rstr = NodeRestrictionList(
      [PctRstr(self.percent_skip, self.percent_fast, sorted_r),
       OrNodeRestriction(
           [FlagsRestriction(["BadExit"]),
           ConserveExitsRestriction(self.exit_ports)]),
       FlagsRestriction(entry_flags, [])]
    )
    mid_rstr = NodeRestrictionList(
      [PctRstr(nonentry_skip, nonentry_fast, sorted_r),
       OrNodeRestriction(
           [FlagsRestriction(["BadExit"]),
           ConserveExitsRestriction(self.exit_ports)]),
       FlagsRestriction(["Running","Fast"], [])]

    )

    if self.exit_id:
      self._set_exit(self.exit_id)
      plog("DEBUG", "Applying Setexit: "+self.exit_id)
      self.exit_rstr = NodeRestrictionList([IdHexRestriction(self.exit_id)])
    elif self.use_all_exits:
      self.exit_rstr = NodeRestrictionList(
        [FlagsRestriction(["Running","Fast"], ["BadExit"])])
    else:
      self.exit_rstr = NodeRestrictionList(
        [PctRstr(nonentry_skip, nonentry_fast, sorted_r),
         FlagsRestriction(["Running","Fast"], ["BadExit"])])

    if self.extra_node_rstr:
      entry_rstr.add_restriction(self.extra_node_rstr)
      mid_rstr.add_restriction(self.extra_node_rstr)
      self.exit_rstr.add_restriction(self.extra_node_rstr)

    # GeoIP configuration
    if self.geoip_config:
      # Every node needs country_code 
      entry_rstr.add_restriction(CountryCodeRestriction())
      mid_rstr.add_restriction(CountryCodeRestriction())
      self.exit_rstr.add_restriction(CountryCodeRestriction())
      
      # Specified countries for different positions
      if self.geoip_config.entry_country:
        entry_rstr.add_restriction(CountryRestriction(self.geoip_config.entry_country))
      if self.geoip_config.middle_country:
        mid_rstr.add_restriction(CountryRestriction(self.geoip_config.middle_country))
      if self.geoip_config.exit_country:
        self.exit_rstr.add_restriction(CountryRestriction(self.geoip_config.exit_country))

      # Excluded countries
      if self.geoip_config.excludes:
        plog("INFO", "Excluded countries: " + str(self.geoip_config.excludes))
        if len(self.geoip_config.excludes) > 0:
          entry_rstr.add_restriction(ExcludeCountriesRestriction(self.geoip_config.excludes))
          mid_rstr.add_restriction(ExcludeCountriesRestriction(self.geoip_config.excludes))
          self.exit_rstr.add_restriction(ExcludeCountriesRestriction(self.geoip_config.excludes))
      
      # Unique countries set? None --> pass
      if self.geoip_config.unique_countries != None:
        if self.geoip_config.unique_countries:
          # If True: unique countries 
          self.path_rstr.add_restriction(UniqueCountryRestriction())
        else:
          # False: use the same country for all nodes in a path
          self.path_rstr.add_restriction(SingleCountryRestriction())
      
      # Specify max number of continent crossings, None means UniqueContinents
      if self.geoip_config.continent_crossings == None:
        self.path_rstr.add_restriction(UniqueContinentRestriction())
      else: self.path_rstr.add_restriction(ContinentRestriction(self.geoip_config.continent_crossings))
      # Should even work in combination with continent crossings
      if self.geoip_config.ocean_crossings != None:
        self.path_rstr.add_restriction(OceanPhobicRestriction(self.geoip_config.ocean_crossings))

    # This is kind of hokey..
    if self.order_exits:
      if self.__ordered_exit_gen:
        exitgen = self.__ordered_exit_gen
        exitgen.reset_restriction(self.exit_rstr)
      else:
        exitgen = self.__ordered_exit_gen = \
          OrderedExitGenerator(80, sorted_r, self.exit_rstr)
    elif self.uniform:
      exitgen = ExactUniformGenerator(sorted_r, self.exit_rstr)
    else:
      exitgen = BwWeightedGenerator(sorted_r, self.exit_rstr, self.pathlen, exit=True)

    if self.uniform:
      self.path_selector = PathSelector(
         ExactUniformGenerator(sorted_r, entry_rstr),
         ExactUniformGenerator(sorted_r, mid_rstr),
         exitgen, self.path_rstr)
    else:
      # Remove ConserveExitsRestriction for entry and middle positions
      # by removing the OrNodeRestriction that contains it...
      # FIXME: This is a landmine for a poor soul to hit.
      # Then again, most of the rest of this function is, too.
      entry_rstr.del_restriction(OrNodeRestriction)
      mid_rstr.del_restriction(OrNodeRestriction)
      self.path_selector = PathSelector(
         BwWeightedGenerator(sorted_r, entry_rstr, self.pathlen,
                             guard=self.use_guards),
         BwWeightedGenerator(sorted_r, mid_rstr, self.pathlen),
         exitgen, self.path_rstr)
      return

  def _set_exit(self, exit_name):
    # sets an exit, if bad, sets bad_exit
    exit_id = None
    if exit_name:
      if exit_name[0] == '$':
        exit_id = exit_name
      elif exit_name in self.consensus.name_to_key:
        exit_id = self.consensus.name_to_key[exit_name]
    self.exit_id = exit_id

  def set_exit(self, exit_name):
    self._set_exit(exit_name)
    self.exit_rstr.clear()
    if not self.exit_id:
      plog("NOTICE", "Requested null exit "+str(self.exit_id))
      self.bad_restrictions = True
    elif self.exit_id[1:] not in self.consensus.routers:
      plog("NOTICE", "Requested absent exit "+str(self.exit_id))
      self.bad_restrictions = True
    elif self.consensus.routers[self.exit_id[1:]].down:
      e = self.consensus.routers[self.exit_id[1:]]
      plog("NOTICE", "Requested downed exit "+str(self.exit_id)+" (bw: "+str(e.bw)+", flags: "+str(e.flags)+")")
      self.bad_restrictions = True
    elif self.consensus.routers[self.exit_id[1:]].deleted:
      e = self.consensus.routers[self.exit_id[1:]]
      plog("NOTICE", "Requested deleted exit "+str(self.exit_id)+" (bw: "+str(e.bw)+", flags: "+str(e.flags)+", Down: "+str(e.down)+", ref: "+str(e.refcount)+")")
      self.bad_restrictions = True
    else:
      self.exit_rstr.add_restriction(IdHexRestriction(self.exit_id))
      plog("DEBUG", "Added exit restriction for "+self.exit_id)
      try:
        self.path_selector.exit_gen.rebuild()
        self.bad_restrictions = False
      except RestrictionError, e:
        plog("WARN", "Restriction error "+str(e)+" after set_exit")
        self.bad_restrictions = True
    return self.bad_restrictions

  def new_consensus(self, consensus):
    self.consensus = consensus
    try:
      self.path_selector.rebuild_gens(self.consensus.sorted_r)
      if self.exit_id:
        self.set_exit(self.exit_id)
    except NoNodesRemain:
      plog("NOTICE", "No viable nodes in consensus for restrictions.")
      # Punting + performing reconfigure..")
      #self.reconfigure(consensus)

  def set_target(self, ip, port):
    # sets an exit policy, if bad, rasies exception..
    "Called to update the ExitPolicyRestrictions with a new ip and port"
    if self.bad_restrictions:
      plog("WARN", "Requested target with bad restrictions")
      raise RestrictionError()
    self.exit_rstr.del_restriction(ExitPolicyRestriction)
    self.exit_rstr.add_restriction(ExitPolicyRestriction(ip, port))
    if self.__ordered_exit_gen: self.__ordered_exit_gen.set_port(port)
    # Try to choose an exit node in the destination country
    # needs an IP != 255.255.255.255
    if self.geoip_config and self.geoip_config.echelon:
      import GeoIPSupport
      c = GeoIPSupport.get_country(ip)
      if c:
        plog("INFO", "[Echelon] IP "+ip+" is in ["+c+"]")
        self.exit_rstr.del_restriction(CountryRestriction)
        self.exit_rstr.add_restriction(CountryRestriction(c))
      else: 
        plog("INFO", "[Echelon] Could not determine destination country of IP "+ip)
        # Try to use a backup country
        if self.geoip_config.exit_country:
          self.exit_rstr.del_restriction(CountryRestriction) 
          self.exit_rstr.add_restriction(CountryRestriction(self.geoip_config.exit_country))
    # Need to rebuild exit generator
    self.path_selector.exit_gen.rebuild()

  def select_path(self):
    if self.bad_restrictions:
      plog("WARN", "Requested target with bad restrictions")
      raise RestrictionError()
    return self.path_selector.select_path(self.pathlen)

class Circuit:
  "Class to describe a circuit"
  def __init__(self):
    self.circ_id = 0
    self.path = [] # routers
    self.exit = None
    self.built = False
    self.failed = False
    self.dirty = False
    self.requested_closed = False
    self.detached_cnt = 0
    self.last_extended_at = time.time()
    self.extend_times = []      # List of all extend-durations
    self.setup_duration = None  # Sum of extend-times
    self.pending_streams = []   # Which stream IDs are pending us
    # XXX: Unused.. Need to use for refcounting because
    # sometimes circuit closed events come before the stream
    # close and we need to track those failures..
    self.carried_streams = []

  def id_path(self):
    "Returns a list of idhex keys for the path of Routers"
    return map(lambda r: r.idhex, self.path)

class Stream:
  "Class to describe a stream"
  def __init__(self, sid, host, port, kind):
    self.strm_id = sid
    self.detached_from = [] # circ id #'s
    self.pending_circ = None
    self.circ = None
    self.host = host
    self.port = port
    self.kind = kind
    self.attached_at = 0
    self.bytes_read = 0
    self.bytes_written = 0
    self.failed = False
    self.ignored = False # Set if PURPOSE=DIR_*
    self.failed_reason = None # Cheating a little.. Only used by StatsHandler

  def lifespan(self, now):
    "Returns the age of the stream"
    return now-self.attached_at

_origsocket = socket.socket
class _SocketWrapper(socket.socket):
  """ Ghetto wrapper to workaround python same_slots_added() and 
      socket __base__ braindamage """
  pass

class SmartSocket(_SocketWrapper):
  """ A SmartSocket is a socket that tracks global socket creation
      for local ports. It has a member StreamSelector that can
      be used as a PathBuilder stream StreamSelector (see below).

      Most users will want to reset the base class of SocksiPy to
      use this class:
      __oldsocket = socket.socket
      socket.socket = PathSupport.SmartSocket
      import SocksiPy
      socket.socket = __oldsocket
   """
  port_table = set()
  _table_lock = threading.Lock()

  def __init__(self, family=2, type=1, proto=0, _sock=None):
    ret = super(SmartSocket, self).__init__(family, type, proto, _sock)
    self.__local_addr = None
    plog("DEBUG", "New socket constructor")
    return ret

  def connect(self, args):
    ret = super(SmartSocket, self).connect(args)
    myaddr = self.getsockname()
    self.__local_addr = myaddr[0]+":"+str(myaddr[1])
    SmartSocket._table_lock.acquire()
    assert(self.__local_addr not in SmartSocket.port_table)
    SmartSocket.port_table.add(myaddr[0]+":"+str(myaddr[1]))
    SmartSocket._table_lock.release()
    plog("DEBUG", "Added "+self.__local_addr+" to our local port list")
    return ret

  def connect_ex(self, args):
    ret = super(SmartSocket, self).connect_ex(args)
    myaddr = ret.getsockname()
    self.__local_addr = myaddr[0]+":"+str(myaddr[1])
    SmartSocket._table_lock.acquire()
    assert(self.__local_addr not in SmartSocket.port_table)
    SmartSocket.port_table.add(myaddr[0]+":"+str(myaddr[1]))
    SmartSocket._table_lock.release()
    plog("DEBUG", "Added "+self.__local_addr+" to our local port list")
    return ret

  def __del__(self):
    if self.__local_addr:
      SmartSocket._table_lock.acquire()
      SmartSocket.port_table.remove(self.__local_addr)
      plog("DEBUG", "Removed "+self.__local_addr+" from our local port list")
      SmartSocket._table_lock.release()
    else:
      plog("DEBUG", "Got a socket deletion with no address")

  def table_size():
    SmartSocket._table_lock.acquire()
    ret = len(SmartSocket.port_table)
    SmartSocket._table_lock.release()
    return ret
  table_size = Callable(table_size)

  def clear_port_table():
    """ WARNING: Calling this periodically is a *really good idea*.
        Relying on __del__ can expose you to race conditions on garbage
        collection between your processes. """
    SmartSocket._table_lock.acquire()
    for i in list(SmartSocket.port_table):
      plog("DEBUG", "Cleared "+i+" from our local port list")
      SmartSocket.port_table.remove(i)
    SmartSocket._table_lock.release()
  clear_port_table = Callable(clear_port_table)

  def StreamSelector(host, port):
    to_test = host+":"+str(port)
    SmartSocket._table_lock.acquire()
    ret = (to_test in SmartSocket.port_table)
    SmartSocket._table_lock.release()
    return ret
  StreamSelector = Callable(StreamSelector)


def StreamSelector(host, port):
  """ A StreamSelector is a function that takes a host and a port as
      arguments (parsed from Tor's SOURCE_ADDR field in STREAM NEW
      events) and decides if it is a stream from this process or not.

      This StreamSelector is just a placeholder that always returns True.
      When you define your own, be aware that you MUST DO YOUR OWN
      LOCKING inside this function, as it is called from the Eventhandler
      thread.

      See PathSupport.SmartSocket.StreamSelctor for an actual
      implementation.

  """
  return True

# TODO: Make passive "PathWatcher" so people can get aggregate 
# node reliability stats for normal usage without us attaching streams
# Can use __metaclass__ and type

class PathBuilder(TorCtl.ConsensusTracker):
  """
  PathBuilder implementation. Handles circuit construction, subject
  to the constraints of the SelectionManager selmgr.
  
  Do not access this object from other threads. Instead, use the 
  schedule_* functions to schedule work to be done in the thread
  of the EventHandler.
  """
  def __init__(self, c, selmgr, RouterClass=TorCtl.Router,
               strm_selector=StreamSelector):
    """Constructor. 'c' is a Connection, 'selmgr' is a SelectionManager,
    and 'RouterClass' is a class that inherits from Router and is used
    to create annotated Routers."""
    TorCtl.ConsensusTracker.__init__(self, c, RouterClass)
    self.last_exit = None
    self.new_nym = False
    self.resolve_port = 0
    self.num_circuits = 1
    self.circuits = {}
    self.streams = {}
    self.selmgr = selmgr
    self.selmgr.reconfigure(self.current_consensus())
    self.imm_jobs = Queue.Queue()
    self.low_prio_jobs = Queue.Queue()
    self.run_all_jobs = False
    self.do_reconfigure = False
    self.strm_selector = strm_selector
    plog("INFO", "Read "+str(len(self.sorted_r))+"/"+str(len(self.ns_map))+" routers")

  def schedule_immediate(self, job):
    """
    Schedules an immediate job to be run before the next event is
    processed.
    """
    assert(self.c.is_live())
    self.imm_jobs.put(job)

  def schedule_low_prio(self, job):
    """
    Schedules a job to be run when a non-time critical event arrives.
    """
    assert(self.c.is_live())
    self.low_prio_jobs.put(job)

  def reset(self):
    """
    Resets accumulated state. Currently only clears the 
    ExactUniformGenerator state.
    """
    plog("DEBUG", "Resetting _generated values for ExactUniformGenerator")
    for r in self.routers.itervalues():
      for g in xrange(0, len(r._generated)):
        r._generated[g] = 0

  def is_urgent_event(event):
    # If event is stream:NEW*/DETACHED or circ BUILT/FAILED, 
    # it is high priority and requires immediate action.
    if isinstance(event, TorCtl.CircuitEvent):
      if event.status in ("BUILT", "FAILED", "CLOSED"):
        return True
    elif isinstance(event, TorCtl.StreamEvent):
      if event.status in ("NEW", "NEWRESOLVE", "DETACHED"):
        return True
    return False
  is_urgent_event = Callable(is_urgent_event)

  def schedule_selmgr(self, job):
    """
    Schedules an immediate job to be run before the next event is
    processed. Also notifies the selection manager that it needs
    to update itself.
    """
    assert(self.c.is_live())
    def notlambda(this):
      job(this.selmgr)
      this.do_reconfigure = True
    self.schedule_immediate(notlambda)

     
  def heartbeat_event(self, event):
    """This function handles dispatching scheduled jobs. If you 
       extend PathBuilder and want to implement this function for 
       some reason, be sure to call the parent class"""
    while not self.imm_jobs.empty():
      imm_job = self.imm_jobs.get_nowait()
      imm_job(self)
    
    if self.do_reconfigure:
      self.selmgr.reconfigure(self.current_consensus())
      self.do_reconfigure = False
    
    if self.run_all_jobs:
      while not self.low_prio_jobs.empty() and self.run_all_jobs:
        imm_job = self.low_prio_jobs.get_nowait()
        imm_job(self)
      self.run_all_jobs = False
      return

    # If event is stream:NEW*/DETACHED or circ BUILT/FAILED, 
    # don't run low prio jobs.. No need to delay streams for them.
    if PathBuilder.is_urgent_event(event): return
   
    # Do the low prio jobs one at a time in case a 
    # higher priority event is queued   
    if not self.low_prio_jobs.empty():
      delay_job = self.low_prio_jobs.get_nowait()
      delay_job(self)

  def build_path(self):
    """ Get a path from the SelectionManager's PathSelector, can be used 
        e.g. for generating paths without actually creating any circuits """
    return self.selmgr.select_path()

  def close_all_streams(self, reason):
    """ Close all open streams """
    for strm in self.streams.itervalues():
      if not strm.ignored:
        try:
          self.c.close_stream(strm.strm_id, reason)
        except TorCtl.ErrorReply, e:
          # This can happen. Streams can timeout before this call.
          plog("NOTICE", "Error closing stream "+str(strm.strm_id)+": "+str(e))

  def close_all_circuits(self):
    """ Close all open circuits """
    for circ in self.circuits.itervalues():
      self.close_circuit(circ.circ_id)

  def close_circuit(self, id):
    """ Close a circuit with given id """
    # TODO: Pass streams to another circ before closing?
    plog("DEBUG", "Requesting close of circuit id: "+str(id))
    if self.circuits[id].requested_closed: return
    self.circuits[id].requested_closed = True
    try: self.c.close_circuit(id)
    except TorCtl.ErrorReply, e: 
      plog("ERROR", "Failed closing circuit " + str(id) + ": " + str(e))

  def circuit_list(self):
    """ Return an iterator or a list of circuits prioritized for 
        stream selection."""
    return self.circuits.itervalues()

  def attach_stream_any(self, stream, badcircs):
    "Attach a stream to a valid circuit, avoiding any in 'badcircs'"
    # Newnym, and warn if not built plus pending
    unattached_streams = [stream]
    if self.new_nym:
      self.new_nym = False
      plog("DEBUG", "Obeying new nym")
      for key in self.circuits.keys():
        if (not self.circuits[key].dirty
            and len(self.circuits[key].pending_streams)):
          plog("WARN", "New nym called, destroying circuit "+str(key)
             +" with "+str(len(self.circuits[key].pending_streams))
             +" pending streams")
          unattached_streams.extend(self.circuits[key].pending_streams)
          self.circuits[key].pending_streams = []
        # FIXME: Consider actually closing circ if no streams.
        self.circuits[key].dirty = True
      
    for circ in self.circuit_list():
      if circ.built and not circ.requested_closed and not circ.dirty \
          and circ.circ_id not in badcircs:
        # XXX: Fails for 'tor-resolve 530.19.6.80' -> NEWRESOLVE
        if circ.exit.will_exit_to(stream.host, stream.port):
          try:
            self.c.attach_stream(stream.strm_id, circ.circ_id)
            stream.pending_circ = circ # Only one possible here
            circ.pending_streams.append(stream)
          except TorCtl.ErrorReply, e:
            # No need to retry here. We should get the failed
            # event for either the circ or stream next
            plog("WARN", "Error attaching new stream: "+str(e.args))
            return
          break
    # This else clause is executed when we go through the circuit
    # list without finding an entry (or it is empty).
    # http://docs.python.org/tutorial/controlflow.html#break-and-continue-statements-and-else-clauses-on-loops
    else:
      circ = None
      try:
        self.selmgr.set_target(stream.host, stream.port)
        circ = self.c.build_circuit(self.selmgr.select_path())
      except RestrictionError, e:
        # XXX: Dress this up a bit
        self.last_exit = None
        # Kill this stream
        plog("WARN", "Closing impossible stream "+str(stream.strm_id)+" ("+str(e)+")")
        try:
          self.c.close_stream(stream.strm_id, "4") # END_STREAM_REASON_EXITPOLICY
        except TorCtl.ErrorReply, e:
          plog("WARN", "Error closing stream: "+str(e))
        return
      except TorCtl.ErrorReply, e:
        plog("WARN", "Error building circ: "+str(e.args))
        self.last_exit = None
        # Kill this stream
        plog("NOTICE", "Closing stream "+str(stream.strm_id))
        try:
          self.c.close_stream(stream.strm_id, "5") # END_STREAM_REASON_DESTROY
        except TorCtl.ErrorReply, e:
          plog("WARN", "Error closing stream: "+str(e))
        return
      for u in unattached_streams:
        plog("DEBUG",
           "Attaching "+str(u.strm_id)+" pending build of "+str(circ.circ_id))
        u.pending_circ = circ
      circ.pending_streams.extend(unattached_streams)
      self.circuits[circ.circ_id] = circ
    self.last_exit = circ.exit
    plog("DEBUG", "Set last exit to "+self.last_exit.idhex)

  def circ_status_event(self, c):
    output = [str(time.time()-c.arrived_at), c.event_name, str(c.circ_id),
              c.status]
    if c.path: output.append(",".join(c.path))
    if c.reason: output.append("REASON=" + c.reason)
    if c.remote_reason: output.append("REMOTE_REASON=" + c.remote_reason)
    plog("DEBUG", " ".join(output))
    # Circuits we don't control get built by Tor
    if c.circ_id not in self.circuits:
      plog("DEBUG", "Ignoring circ " + str(c.circ_id))
      return
    if c.status == "EXTENDED":
      self.circuits[c.circ_id].last_extended_at = c.arrived_at
    elif c.status == "FAILED" or c.status == "CLOSED":
      # XXX: Can still get a STREAM FAILED for this circ after this
      circ = self.circuits[c.circ_id]
      for r in circ.path:
        r.refcount -= 1
        plog("DEBUG", "Close refcount "+str(r.refcount)+" for "+r.idhex)
        if r.deleted and r.refcount == 0:
          # XXX: This shouldn't happen with StatsRouters.. 
          if r.__class__.__name__ == "StatsRouter":
            plog("WARN", "Purging expired StatsRouter "+r.idhex)
          else:
            plog("INFO", "Purging expired router "+r.idhex)
          del self.routers[r.idhex]
          self.selmgr.new_consensus(self.current_consensus())
      del self.circuits[c.circ_id]
      for stream in circ.pending_streams:
        # If it was built, let Tor decide to detach or fail the stream
        if not circ.built:
          plog("DEBUG", "Finding new circ for " + str(stream.strm_id))
          self.attach_stream_any(stream, stream.detached_from)
        else:
          plog("NOTICE", "Waiting on Tor to hint about stream "+str(stream.strm_id)+" on closed circ "+str(circ.circ_id))
    elif c.status == "BUILT":
      self.circuits[c.circ_id].built = True
      try:
        for stream in self.circuits[c.circ_id].pending_streams:
          self.c.attach_stream(stream.strm_id, c.circ_id)
      except TorCtl.ErrorReply, e:
        # No need to retry here. We should get the failed
        # event for either the circ or stream in the next event
        plog("NOTICE", "Error attaching pending stream: "+str(e.args))
        return

  def stream_status_event(self, s):
    output = [str(time.time()-s.arrived_at), s.event_name, str(s.strm_id),
              s.status, str(s.circ_id),
          s.target_host, str(s.target_port)]
    if s.reason: output.append("REASON=" + s.reason)
    if s.remote_reason: output.append("REMOTE_REASON=" + s.remote_reason)
    if s.purpose: output.append("PURPOSE=" + s.purpose)
    if s.source_addr: output.append("SOURCE_ADDR="+s.source_addr)
    if not re.match(r"\d+.\d+.\d+.\d+", s.target_host):
      s.target_host = "255.255.255.255" # ignore DNS for exit policy check

    # Hack to ignore Tor-handled streams
    if s.strm_id in self.streams and self.streams[s.strm_id].ignored:
      if s.status == "CLOSED":
        plog("DEBUG", "Deleting ignored stream: " + str(s.strm_id))
        del self.streams[s.strm_id]
      else:
        plog("DEBUG", "Ignoring stream: " + str(s.strm_id))
      return

    plog("DEBUG", " ".join(output))
    # XXX: Copy s.circ_id==0 check+reset from StatsSupport here too?

    if s.status == "NEW" or s.status == "NEWRESOLVE":
      if s.status == "NEWRESOLVE" and not s.target_port:
        s.target_port = self.resolve_port
      if s.circ_id == 0:
        self.streams[s.strm_id] = Stream(s.strm_id, s.target_host, s.target_port, s.status)
      elif s.strm_id not in self.streams:
        plog("NOTICE", "Got new stream "+str(s.strm_id)+" with circuit "
                       +str(s.circ_id)+" already attached.")
        self.streams[s.strm_id] = Stream(s.strm_id, s.target_host, s.target_port, s.status)
        self.streams[s.strm_id].circ_id = s.circ_id

      # Remember Tor-handled streams (Currently only directory streams)

      if s.purpose and s.purpose.find("DIR_") == 0:
        self.streams[s.strm_id].ignored = True
        plog("DEBUG", "Ignoring stream: " + str(s.strm_id))
        return
      elif s.source_addr:
        src_addr = s.source_addr.split(":")
        src_addr[1] = int(src_addr[1])
        if not self.strm_selector(*src_addr):
          self.streams[s.strm_id].ignored = True
          plog("INFO", "Ignoring foreign stream: " + str(s.strm_id))
          return
      if s.circ_id == 0:
        self.attach_stream_any(self.streams[s.strm_id],
                   self.streams[s.strm_id].detached_from)
    elif s.status == "DETACHED":
      if s.strm_id not in self.streams:
        plog("WARN", "Detached stream "+str(s.strm_id)+" not found")
        self.streams[s.strm_id] = Stream(s.strm_id, s.target_host,
                      s.target_port, "NEW")
      # FIXME Stats (differentiate Resolved streams also..)
      if not s.circ_id:
        if s.reason == "TIMEOUT" or s.reason == "EXITPOLICY":
          plog("NOTICE", "Stream "+str(s.strm_id)+" detached with "+s.reason)
        else:
          plog("WARN", "Stream "+str(s.strm_id)+" detached from no circuit with reason: "+str(s.reason))
      else:
        self.streams[s.strm_id].detached_from.append(s.circ_id)

      if self.streams[s.strm_id].pending_circ and \
           self.streams[s.strm_id] in \
                  self.streams[s.strm_id].pending_circ.pending_streams:
        self.streams[s.strm_id].pending_circ.pending_streams.remove(
                                                self.streams[s.strm_id])
      self.streams[s.strm_id].pending_circ = None
      self.attach_stream_any(self.streams[s.strm_id],
                   self.streams[s.strm_id].detached_from)
    elif s.status == "SUCCEEDED":
      if s.strm_id not in self.streams:
        plog("NOTICE", "Succeeded stream "+str(s.strm_id)+" not found")
        return
      if s.circ_id and self.streams[s.strm_id].pending_circ.circ_id != s.circ_id:
        # Hrmm.. this can happen on a new-nym.. Very rare, putting warn
        # in because I'm still not sure this is correct
        plog("WARN", "Mismatch of pending: "
          +str(self.streams[s.strm_id].pending_circ.circ_id)+" vs "
          +str(s.circ_id))
        # This can happen if the circuit existed before we started up
        if s.circ_id in self.circuits:
          self.streams[s.strm_id].circ = self.circuits[s.circ_id]
        else:
          plog("NOTICE", "Stream "+str(s.strm_id)+" has unknown circuit: "+str(s.circ_id))
      else:
        self.streams[s.strm_id].circ = self.streams[s.strm_id].pending_circ
      self.streams[s.strm_id].pending_circ.pending_streams.remove(self.streams[s.strm_id])
      self.streams[s.strm_id].pending_circ = None
      self.streams[s.strm_id].attached_at = s.arrived_at
    elif s.status == "FAILED" or s.status == "CLOSED":
      # FIXME stats
      if s.strm_id not in self.streams:
        plog("NOTICE", "Failed stream "+str(s.strm_id)+" not found")
        return

      # XXX: Can happen on timeout
      if not s.circ_id:
        if s.reason == "TIMEOUT" or s.reason == "EXITPOLICY":
          plog("NOTICE", "Stream "+str(s.strm_id)+" "+s.status+" with "+s.reason)
        else:
          plog("WARN", "Stream "+str(s.strm_id)+" "+s.status+" from no circuit with reason: "+str(s.reason))

      # We get failed and closed for each stream. OK to return 
      # and let the closed do the cleanup
      if s.status == "FAILED":
        # Avoid busted circuits that will not resolve or carry
        # traffic. 
        self.streams[s.strm_id].failed = True
        if s.circ_id in self.circuits: self.circuits[s.circ_id].dirty = True
        elif s.circ_id != 0: 
          plog("WARN", "Failed stream "+str(s.strm_id)+" on unknown circ "+str(s.circ_id))
        return

      if self.streams[s.strm_id].pending_circ:
        self.streams[s.strm_id].pending_circ.pending_streams.remove(self.streams[s.strm_id])
      del self.streams[s.strm_id]
    elif s.status == "REMAP":
      if s.strm_id not in self.streams:
        plog("WARN", "Remap id "+str(s.strm_id)+" not found")
      else:
        if not re.match(r"\d+.\d+.\d+.\d+", s.target_host):
          s.target_host = "255.255.255.255"
          plog("NOTICE", "Non-IP remap for "+str(s.strm_id)+" to "
                   + s.target_host)
        self.streams[s.strm_id].host = s.target_host
        self.streams[s.strm_id].port = s.target_port

  def stream_bw_event(self, s):
    output = [str(time.time()-s.arrived_at), s.event_name, str(s.strm_id),
              str(s.bytes_written),
              str(s.bytes_read)]
    if not s.strm_id in self.streams:
      plog("DEBUG", " ".join(output))
      plog("WARN", "BW event for unknown stream id: "+str(s.strm_id))
    else:
      if not self.streams[s.strm_id].ignored:
        plog("DEBUG", " ".join(output))
      self.streams[s.strm_id].bytes_read += s.bytes_read
      self.streams[s.strm_id].bytes_written += s.bytes_written

  def new_consensus_event(self, n):
    TorCtl.ConsensusTracker.new_consensus_event(self, n)
    self.selmgr.new_consensus(self.current_consensus())

  def new_desc_event(self, d):
    if TorCtl.ConsensusTracker.new_desc_event(self, d):
      self.selmgr.new_consensus(self.current_consensus())

  def bandwidth_event(self, b): pass # For heartbeat only..

################### CircuitHandler #############################

class CircuitHandler(PathBuilder):
  """ CircuitHandler that extends from PathBuilder to handle multiple
      circuits as opposed to just one. """
  def __init__(self, c, selmgr, num_circuits, RouterClass):
    """Constructor. 'c' is a Connection, 'selmgr' is a SelectionManager,
    'num_circuits' is the number of circuits to keep in the pool,
    and 'RouterClass' is a class that inherits from Router and is used
    to create annotated Routers."""
    PathBuilder.__init__(self, c, selmgr, RouterClass)
    # Set handler to the connection here to 
    # not miss any circuit events on startup
    c.set_event_handler(self)
    self.num_circuits = num_circuits    # Size of the circuit pool
    self.check_circuit_pool()           # Bring up the pool of circs
    
  def check_circuit_pool(self):
    """ Init or check the status of the circuit-pool """
    # Get current number of circuits
    n = len(self.circuits.values())
    i = self.num_circuits-n
    if i > 0:
      plog("INFO", "Checked pool of circuits: we need to build " + 
         str(i) + " circuits")
    # Schedule (num_circs-n) circuit-buildups
    while (n < self.num_circuits):      
      # TODO: Should mimic Tor's learning here
      self.build_circuit("255.255.255.255", 80) 
      plog("DEBUG", "Scheduled circuit No. " + str(n+1))
      n += 1

  def build_circuit(self, host, port):
    """ Build a circuit """
    circ = None
    while circ == None:
      try:
        self.selmgr.set_target(host, port)
        circ = self.c.build_circuit(self.selmgr.select_path())
        self.circuits[circ.circ_id] = circ
        return circ
      except RestrictionError, e:
        # XXX: Dress this up a bit
        traceback.print_exc()
        plog("ERROR", "Impossible restrictions: "+str(e))
      except TorCtl.ErrorReply, e:
        traceback.print_exc()
        plog("WARN", "Error building circuit: " + str(e.args))

  def circ_status_event(self, c):
    """ Handle circuit status events """
    output = [c.event_name, str(c.circ_id), c.status]
    if c.path: output.append(",".join(c.path))
    if c.reason: output.append("REASON=" + c.reason)
    if c.remote_reason: output.append("REMOTE_REASON=" + c.remote_reason)
    plog("DEBUG", " ".join(output))
    
    # Circuits we don't control get built by Tor
    if c.circ_id not in self.circuits:
      plog("DEBUG", "Ignoring circuit " + str(c.circ_id) + 
         " (controlled by Tor)")
      return
    
    # EXTENDED
    if c.status == "EXTENDED":
      # Compute elapsed time
      extend_time = c.arrived_at-self.circuits[c.circ_id].last_extended_at
      self.circuits[c.circ_id].extend_times.append(extend_time)
      plog("INFO", "Circuit " + str(c.circ_id) + " extended in " + 
         str(extend_time) + " sec")
      self.circuits[c.circ_id].last_extended_at = c.arrived_at
    
    # FAILED & CLOSED
    elif c.status == "FAILED" or c.status == "CLOSED":
      PathBuilder.circ_status_event(self, c)
      # Check if there are enough circs
      self.check_circuit_pool()
      return
    # BUILT
    elif c.status == "BUILT":
      PathBuilder.circ_status_event(self, c)
      # Compute duration by summing up extend_times
      circ = self.circuits[c.circ_id]
      duration = reduce(lambda x, y: x+y, circ.extend_times, 0.0)
      plog("INFO", "Circuit " + str(c.circ_id) + " needed " + 
         str(duration) + " seconds to be built")
      # Save the duration to the circuit for later use
      circ.setup_duration = duration
      
    # OTHER?
    else:
      # If this was e.g. a LAUNCHED
      pass

################### StreamHandler ##############################

class StreamHandler(CircuitHandler):
  """ StreamHandler that extends from the CircuitHandler 
      to handle attaching streams to an appropriate circuit 
      in the pool. """
  def __init__(self, c, selmgr, num_circs, RouterClass):
    CircuitHandler.__init__(self, c, selmgr, num_circs, RouterClass)

  def clear_dns_cache(self):
    """ Send signal CLEARDNSCACHE """
    lines = self.c.sendAndRecv("SIGNAL CLEARDNSCACHE\r\n")
    for _, msg, more in lines:
      plog("DEBUG", "CLEARDNSCACHE: " + msg)

  def close_stream(self, id, reason):
    """ Close a stream with given id and reason """
    self.c.close_stream(id, reason)

  def address_mapped_event(self, event):
    """ It is necessary to listen to ADDRMAP events to be able to 
        perform DNS lookups using Tor """
    output = [event.event_name, event.from_addr, event.to_addr, 
       time.asctime(event.when)]
    plog("DEBUG", " ".join(output))

  def unknown_event(self, event):
    plog("DEBUG", "UNKNOWN EVENT '" + event.event_name + "':" + 
       event.event_string)

########################## Unit tests ##########################

def do_gen_unit(gen, r_list, weight_bw, num_print):
  trials = 0
  for r in r_list:
    if gen.rstr_list.r_is_ok(r):
      trials += weight_bw(gen, r)
  trials = int(trials/1024)
  
  print "Running "+str(trials)+" trials"

  # 0. Reset r.chosen = 0 for all routers
  for r in r_list:
    r.chosen = 0

  # 1. Generate 'trials' choices:
  #    1a. r.chosen++

  loglevel = TorUtil.loglevel
  TorUtil.loglevel = "INFO"

  gen.rewind()
  rtrs = gen.generate()
  for i in xrange(1, trials):
    r = rtrs.next()
    r.chosen += 1

  TorUtil.loglevel = loglevel

  # 2. Print top num_print routers choices+bandwidth stats+flags
  i = 0
  copy_rlist = copy.copy(r_list)
  copy_rlist.sort(lambda x, y: cmp(y.chosen, x.chosen))
  for r in copy_rlist:
    if r.chosen and not gen.rstr_list.r_is_ok(r):
      print "WARN: Restriction fail at "+r.idhex
    if not r.chosen and gen.rstr_list.r_is_ok(r):
      print "WARN: Generation fail at "+r.idhex
    if not gen.rstr_list.r_is_ok(r): continue
    flag = ""
    bw = int(weight_bw(gen, r))
    if "Exit" in r.flags:
      flag += "E"
    if "Guard" in r.flags:
      flag += "G"
    print str(r.list_rank)+". "+r.nickname+" "+str(r.bw/1024.0)+"/"+str(bw/1024.0)+": "+str(r.chosen)+", "+flag
    i += 1
    if i > num_print: break

def do_unit(rst, r_list, plamb):
  print "\n"
  print "-----------------------------------"
  print rst.r_is_ok.im_class
  above_i = 0
  above_bw = 0
  below_i = 0
  below_bw = 0
  for r in r_list:
    if rst.r_is_ok(r):
      print r.nickname+" "+plamb(r)+"="+str(rst.r_is_ok(r))+" "+str(r.bw)
      if r.bw > 400000:
        above_i = above_i + 1
        above_bw += r.bw
      else:
        below_i = below_i + 1
        below_bw += r.bw
        
  print "Routers above: " + str(above_i) + " bw: " + str(above_bw)
  print "Routers below: " + str(below_i) + " bw: " + str(below_bw)

# TODO: Tests:
#  - Test each NodeRestriction and print in/out lines for it
#  - Test NodeGenerator and reapply NodeRestrictions
#  - Same for PathSelector and PathRestrictions
#  - Also Reapply each restriction by hand to path. Verify returns true

if __name__ == '__main__':
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  s.connect((TorUtil.control_host,TorUtil.control_port))
  c = Connection(s)
  c.debug(file("control.log", "w"))
  c.authenticate(TorUtil.control_pass)
  nslist = c.get_network_status()
  sorted_rlist = c.read_routers(c.get_network_status())

  sorted_rlist.sort(lambda x, y: cmp(y.bw, x.bw))
  for i in xrange(len(sorted_rlist)): sorted_rlist[i].list_rank = i

  def flag_weighting(bwgen, r):
    bw = r.bw
    if "Exit" in r.flags:
      bw *= bwgen.exit_weight
    if "Guard" in r.flags:
      bw *= bwgen.guard_weight
    return bw

  def uniform_weighting(bwgen, r):
    return 10240000

  # XXX: Test OrderedexitGenerators
  do_gen_unit(
   UniformGenerator(sorted_rlist,
                    NodeRestrictionList([PercentileRestriction(20,30,sorted_rlist),
FlagsRestriction(["Valid"])])),
                    sorted_rlist, uniform_weighting, 1500)

  
  do_gen_unit(BwWeightedGenerator(sorted_rlist, FlagsRestriction(["Exit"]),
                                  3, exit=True),
              sorted_rlist, flag_weighting, 500)
  
  do_gen_unit(BwWeightedGenerator(sorted_rlist, FlagsRestriction(["Guard"]),
              3, guard=True),
              sorted_rlist, flag_weighting, 500)
  
  do_gen_unit(
   BwWeightedGenerator(sorted_rlist, FlagsRestriction(["Valid"]), 3),
   sorted_rlist, flag_weighting, 500)

 
  for r in sorted_rlist:
    if r.will_exit_to("211.11.21.22", 465):
      print r.nickname+" "+str(r.bw)

  do_unit(FlagsRestriction(["Guard"], []), sorted_rlist, lambda r: " ".join(r.flags))
  do_unit(FlagsRestriction(["Fast"], []), sorted_rlist, lambda r: " ".join(r.flags))

  do_unit(ExitPolicyRestriction("2.11.2.2", 80), sorted_rlist,
          lambda r: "exits to 80")
  do_unit(PercentileRestriction(0, 100, sorted_rlist), sorted_rlist,
          lambda r: "")
  do_unit(PercentileRestriction(10, 20, sorted_rlist), sorted_rlist,
          lambda r: "")
  do_unit(OSRestriction([r"[lL]inux", r"BSD", "Darwin"], []), sorted_rlist,
          lambda r: r.os)
  do_unit(OSRestriction([], ["Windows", "Solaris"]), sorted_rlist,
          lambda r: r.os)
   
  do_unit(VersionRangeRestriction("0.1.2.0"), sorted_rlist,
          lambda r: str(r.version))
  do_unit(VersionRangeRestriction("0.1.2.0", "0.1.2.5"), sorted_rlist,
          lambda r: str(r.version))
  do_unit(VersionIncludeRestriction(["0.1.1.26-alpha", "0.1.2.7-ignored"]),
          sorted_rlist, lambda r: str(r.version))
  do_unit(VersionExcludeRestriction(["0.1.1.26"]), sorted_rlist,
          lambda r: str(r.version))

  do_unit(ConserveExitsRestriction(), sorted_rlist, lambda r: " ".join(r.flags))
  do_unit(FlagsRestriction([], ["Valid"]), sorted_rlist, lambda r: " ".join(r.flags))

  do_unit(IdHexRestriction("$FFCB46DB1339DA84674C70D7CB586434C4370441"),
          sorted_rlist, lambda r: r.idhex)

  rl =  [AtLeastNNodeRestriction([ExitPolicyRestriction("255.255.255.255", 80), ExitPolicyRestriction("255.255.255.255", 443), ExitPolicyRestriction("255.255.255.255", 6667)], 2), FlagsRestriction([], ["BadExit"])]

  exit_rstr = NodeRestrictionList(rl)

  ug = UniformGenerator(sorted_rlist, exit_rstr)

  ug.rewind()
  rlist = []
  for r in ug.generate():
    print "Checking: " + r.nickname
    for rs in rl:
      if not rs.r_is_ok(r):
        raise PathError()
    if not "Exit" in r.flags:
      print "No exit in flags of "+r.idhex
      for e in r.exitpolicy:
        print " "+str(e)
      print " 80: "+str(r.will_exit_to("255.255.255.255", 80))
      print " 443: "+str(r.will_exit_to("255.255.255.255", 443))
      print " 6667: "+str(r.will_exit_to("255.255.255.255", 6667))

    ug.mark_chosen(r)
    rlist.append(r)
  for r in sorted_rlist:
    if "Exit" in r.flags and not r in rlist:
      print r.idhex+" is an exit not in rl!"
        

########NEW FILE########
__FILENAME__ = ScanSupport
#!/usr/bin/python
# Copyright 2009-2010 Mike Perry. See LICENSE file.
import PathSupport
import threading
import copy
import time
import shutil
import TorCtl

from TorUtil import plog

SQLSupport = None

# Note: be careful writing functions for this class. Remember that
# the PathBuilder has its own thread that it recieves events on
# independent from your thread that calls into here.
class ScanHandler(PathSupport.PathBuilder):
  def set_pct_rstr(self, percent_skip, percent_fast):
    def notlambda(sm):
      sm.percent_fast=percent_fast
      sm.percent_skip=percent_skip
    self.schedule_selmgr(notlambda)

  def reset_stats(self):
    def notlambda(this):
      this.reset()
    self.schedule_low_prio(notlambda)

  def commit(self):
    plog("INFO", "Scanner committing jobs...")
    cond = threading.Condition()
    def notlambda2(this):
      cond.acquire()
      this.run_all_jobs = False
      plog("INFO", "Commit done.")
      cond.notify()
      cond.release()

    def notlambda1(this):
      plog("INFO", "Committing jobs...")
      this.run_all_jobs = True
      self.schedule_low_prio(notlambda2)

    cond.acquire()
    self.schedule_immediate(notlambda1)

    cond.wait()
    cond.release()
    plog("INFO", "Scanner commit done.")

  def close_circuits(self):
    cond = threading.Condition()
    def notlambda(this):
      cond.acquire()
      this.close_all_circuits()
      cond.notify()
      cond.release()
    cond.acquire()
    self.schedule_low_prio(notlambda)
    cond.wait()
    cond.release()

  def close_streams(self, reason):
    cond = threading.Condition()
    plog("NOTICE", "Wedged Tor stream. Closing all streams")
    def notlambda(this):
      cond.acquire()
      this.close_all_streams(reason)
      cond.notify()
      cond.release()
    cond.acquire()
    self.schedule_low_prio(notlambda)
    cond.wait()
    cond.release()

  def new_exit(self):
    cond = threading.Condition()
    def notlambda(this):
      cond.acquire()
      this.new_nym = True
      if this.selmgr.bad_restrictions:
        plog("NOTICE", "Clearing bad restrictions with reconfigure..")
        this.selmgr.reconfigure(this.current_consensus())
      lines = this.c.sendAndRecv("SIGNAL CLEARDNSCACHE\r\n")
      for _,msg,more in lines:
        plog("DEBUG", msg)
      cond.notify()
      cond.release()
    cond.acquire()
    self.schedule_low_prio(notlambda)
    cond.wait()
    cond.release()

  def idhex_to_r(self, idhex):
    cond = threading.Condition()
    def notlambda(this):
      cond.acquire()
      if idhex in self.routers:
        cond._result = self.routers[idhex]
      else:
        cond._result = None
      cond.notify()
      cond.release()
    cond.acquire()
    self.schedule_low_prio(notlambda)
    cond.wait()
    cond.release()
    return cond._result

  def name_to_idhex(self, nick):
    cond = threading.Condition()
    def notlambda(this):
      cond.acquire()
      if nick in self.name_to_key:
        cond._result = self.name_to_key[nick]
      else:
        cond._result = None
      cond.notify()
      cond.release()
    cond.acquire()
    self.schedule_low_prio(notlambda)
    cond.wait()
    cond.release()
    return cond._result

  def rank_to_percent(self, rank):
    cond = threading.Condition()
    def notlambda(this):
      cond.acquire()
      cond._pct = (100.0*rank)/len(this.sorted_r) # lol moar haxx
      cond.notify()
      cond.release()
    cond.acquire()
    self.schedule_low_prio(notlambda)
    cond.wait()
    cond.release()
    return cond._pct

  def percent_to_rank(self, pct):
    cond = threading.Condition()
    def notlambda(this):
      cond.acquire()
      cond._rank = int(round((pct*len(this.sorted_r))/100.0,0)) # lol moar haxx
      cond.notify()
      cond.release()
    cond.acquire()
    self.schedule_low_prio(notlambda)
    cond.wait()
    cond.release()
    return cond._rank

  def get_exit_node(self):
    ret = copy.copy(self.last_exit) # GIL FTW
    if ret:
      plog("DEBUG", "Got last exit of "+ret.idhex)
    else:
      plog("DEBUG", "No last exit.")
    return ret

  def set_exit_node(self, arg):
    cond = threading.Condition()
    exit_name = arg
    plog("DEBUG", "Got Setexit: "+exit_name)
    def notlambda(sm):
      plog("DEBUG", "Job for setexit: "+exit_name)
      cond.acquire()
      # Clear last successful exit, we're running a new test
      self.last_exit = None
      sm.set_exit(exit_name)
      cond.notify()
      cond.release()
    cond.acquire()
    self.schedule_selmgr(notlambda)
    cond.wait()
    cond.release()

class SQLScanHandler(ScanHandler):
  def __init__(self, c, selmgr, RouterClass=TorCtl.Router,
               strm_selector=PathSupport.StreamSelector):
    # Only require sqlalchemy if we really need it.
    global SQLSupport
    if SQLSupport is None:
      import SQLSupport
    ScanHandler.__init__(self, c, selmgr, RouterClass, strm_selector)

  def attach_sql_listener(self, db_uri):
    plog("DEBUG", "Got db: "+db_uri)
    SQLSupport.setup_db(db_uri, echo=False, drop=True)
    self.sql_consensus_listener = SQLSupport.ConsensusTrackerListener()
    self.add_event_listener(self.sql_consensus_listener)
    self.add_event_listener(SQLSupport.StreamListener())

  def write_sql_stats(self, rfilename=None, stats_filter=None):
    if not rfilename:
      rfilename="./data/stats/sql-"+time.strftime("20%y-%m-%d-%H:%M:%S")
    cond = threading.Condition()
    def notlambda(h):
      cond.acquire()
      SQLSupport.RouterStats.write_stats(file(rfilename, "w"),
                            0, 100, order_by=SQLSupport.RouterStats.sbw,
                            recompute=True, disp_clause=stats_filter)
      cond.notify()
      cond.release()
    cond.acquire()
    self.schedule_low_prio(notlambda)
    cond.wait()
    cond.release()

  def write_strm_bws(self, rfilename=None, slice_num=0, stats_filter=None):
    if not rfilename:
      rfilename="./data/stats/bws-"+time.strftime("20%y-%m-%d-%H:%M:%S")
    cond = threading.Condition()
    def notlambda(this):
      cond.acquire()
      f=file(rfilename, "w")
      f.write("slicenum="+str(slice_num)+"\n")
      SQLSupport.RouterStats.write_bws(f, 0, 100,
                            order_by=SQLSupport.RouterStats.sbw,
                            recompute=False, disp_clause=stats_filter)
      f.close()
      cond.notify()
      cond.release()
    cond.acquire()
    self.schedule_low_prio(notlambda)
    cond.wait()
    cond.release()

  def save_sql_file(self, sql_file, new_file):
    cond = threading.Condition()
    def notlambda(this):
      cond.acquire()
      SQLSupport.tc_session.close()
      try:
        shutil.copy(sql_file, new_file)
      except Exception,e:
        plog("WARN", "Error moving sql file: "+str(e))
      SQLSupport.reset_all()
      cond.notify()
      cond.release()
    cond.acquire()
    self.schedule_low_prio(notlambda)
    cond.wait()
    cond.release()

  def wait_for_consensus(self):
    cond = threading.Condition()
    def notlambda(this):
      if this.sql_consensus_listener.last_desc_at \
                 != SQLSupport.ConsensusTrackerListener.CONSENSUS_DONE:
        this.sql_consensus_listener.wait_for_signal = False
        plog("INFO", "Waiting on consensus result: "+str(this.run_all_jobs))
        this.schedule_low_prio(notlambda)
      else:
        cond.acquire()
        this.sql_consensus_listener.wait_for_signal = True
        cond.notify()
        cond.release()
    plog("DEBUG", "Checking for consensus")
    cond.acquire()
    self.schedule_low_prio(notlambda)
    cond.wait()
    cond.release()
    plog("INFO", "Consensus OK")

  def reset_stats(self):
    cond = threading.Condition()
    def notlambda(this):
      cond.acquire()
      ScanHandler.reset_stats(self)
      SQLSupport.reset_all()
      this.sql_consensus_listener.update_consensus()
      this.sql_consensus_listener._update_rank_history(this.sql_consensus_listener.consensus.ns_map.iterkeys())
      SQLSupport.refresh_all()
      cond.notify()
      cond.release()
    cond.acquire()
    self.schedule_low_prio(notlambda)
    cond.wait()
    cond.release()

########NEW FILE########
__FILENAME__ = SQLSupport
#!/usr/bin/python
# Copyright 2009-2010 Mike Perry. See LICENSE file.

"""

Support classes for statisics gathering in SQL Databases

DOCDOC

"""

import socket
import sys
import time
import datetime
import math

import PathSupport, TorCtl
from TorUtil import *
from PathSupport import *
from TorUtil import meta_port, meta_host, control_port, control_host, control_pass
from TorCtl import EVENT_TYPE, EVENT_STATE, TorCtlError

import sqlalchemy
import sqlalchemy.orm.exc
from sqlalchemy.orm import scoped_session, sessionmaker, eagerload, lazyload, eagerload_all
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import create_engine, and_, or_, not_, func
from sqlalchemy.sql import func,select,alias,case
from sqlalchemy.schema import ThreadLocalMetaData,MetaData
from elixir import *
from elixir import options
# migrate from elixir 06 to 07
options.MIGRATION_TO_07_AID = True


# Nodes with a ratio below this value will be removed from consideration
# for higher-valued nodes
MIN_RATIO=0.5

NO_FPE=2**-50

#################### Session Usage ###############
# What is all this l_session madness? See:                                                                
# http://www.sqlalchemy.org/docs/orm/session.html#lifespan-of-a-contextual-session                        
#   "This has the effect such that each web request starts fresh with                                     
#   a brand new session, and is the most definitive approach to closing                                   
#   out a request." 

#################### Model #######################

# In elixir, the session (DB connection) is a property of the model..
# There can only be one for all of the listeners below that use it
# See http://elixir.ematia.de/trac/wiki/Recipes/MultipleDatabases
OP=None
tc_metadata = MetaData()
tc_metadata.echo=True
tc_session = scoped_session(sessionmaker(autoflush=True))

def setup_db(db_uri, echo=False, drop=False):
  tc_engine = create_engine(db_uri, echo=echo)
  tc_metadata.bind = tc_engine
  tc_metadata.echo = echo

  setup_all()
  if drop: drop_all()
  create_all()

  if sqlalchemy.__version__ < "0.5.0":
    # DIAF SQLAlchemy. A token gesture at backwards compatibility
    # wouldn't kill you, you know.
    tc_session.add = tc_session.save_or_update

  if sqlalchemy.__version__ < "0.6.0":
    # clear() replaced with expunge_all
    tc_session.clear = tc_session.expunge_all

class Router(Entity):
  using_options(shortnames=True, order_by='-published', session=tc_session, metadata=tc_metadata)
  using_mapper_options(save_on_init=False)
  idhex = Field(CHAR(40), primary_key=True, index=True)
  orhash = Field(CHAR(27))
  published = Field(DateTime)
  nickname = Field(Text)

  os = Field(Text)
  rate_limited = Field(Boolean)
  guard = Field(Boolean)
  exit = Field(Boolean)
  stable = Field(Boolean)
  v2dir = Field(Boolean)
  v3dir = Field(Boolean)
  hsdir = Field(Boolean)

  bw = Field(Integer)
  version = Field(Integer)
  # FIXME: is mutable=False what we want? Do we care?
  #router = Field(PickleType(mutable=False)) 
  circuits = ManyToMany('Circuit')
  streams = ManyToMany('Stream')
  detached_streams = ManyToMany('Stream')
  bw_history = OneToMany('BwHistory')
  stats = OneToOne('RouterStats', inverse="router")

  def from_router(self, router):
    self.published = router.published
    self.bw = router.bw
    self.idhex = router.idhex
    self.orhash = router.orhash
    self.nickname = router.nickname
    # XXX: Temporary hack. router.os can contain unicode, which makes
    # us barf. Apparently 'Text' types can't have unicode chars?
    # self.os = router.os
    self.rate_limited = router.rate_limited
    self.guard = "Guard" in router.flags
    self.exit = "Exit" in router.flags
    self.stable = "Stable" in router.flags
    self.v2dir = "V2Dir" in router.flags
    self.v3dir = "V3Dir" in router.flags
    self.hsdir = "HSDir" in router.flags
    self.version = router.version.version
    #self.router = router
    return self

class BwHistory(Entity):
  using_options(shortnames=True, session=tc_session, metadata=tc_metadata)
  using_mapper_options(save_on_init=False)
  router = ManyToOne('Router')
  bw = Field(Integer)
  desc_bw = Field(Integer)
  rank = Field(Integer)
  pub_time = Field(DateTime)

class Circuit(Entity):
  using_options(shortnames=True, order_by='-launch_time', session=tc_session, metadata=tc_metadata)
  using_mapper_options(save_on_init=False)
  routers = ManyToMany('Router')
  streams = OneToMany('Stream', inverse='circuit')
  detached_streams = ManyToMany('Stream', inverse='detached_circuits')
  extensions = OneToMany('Extension', inverse='circ')
  circ_id = Field(Integer, index=True)
  launch_time = Field(Float)
  last_extend = Field(Float)

class FailedCircuit(Circuit):
  using_mapper_options(save_on_init=False)
  using_options(shortnames=True, session=tc_session, metadata=tc_metadata)
  #failed_extend = ManyToOne('Extension', inverse='circ')
  fail_reason = Field(Text)
  fail_time = Field(Float)

class BuiltCircuit(Circuit):
  using_options(shortnames=True, session=tc_session, metadata=tc_metadata)
  using_mapper_options(save_on_init=False)
  built_time = Field(Float)
  tot_delta = Field(Float)

class DestroyedCircuit(Circuit):
  using_options(shortnames=True, session=tc_session, metadata=tc_metadata)
  using_mapper_options(save_on_init=False)
  destroy_reason = Field(Text)
  destroy_time = Field(Float)

class ClosedCircuit(BuiltCircuit):
  using_options(shortnames=True, session=tc_session, metadata=tc_metadata)
  using_mapper_options(save_on_init=False)
  closed_time = Field(Float)

class Extension(Entity):
  using_mapper_options(save_on_init=False)
  using_options(shortnames=True, order_by='-time', session=tc_session, metadata=tc_metadata)
  circ = ManyToOne('Circuit', inverse='extensions')
  from_node = ManyToOne('Router')
  to_node = ManyToOne('Router')
  hop = Field(Integer)
  time = Field(Float)
  delta = Field(Float)

class FailedExtension(Extension):
  using_options(shortnames=True, session=tc_session, metadata=tc_metadata)
  #failed_circ = ManyToOne('FailedCircuit', inverse='failed_extend')
  using_mapper_options(save_on_init=False)
  reason = Field(Text)

class Stream(Entity):
  using_options(shortnames=True, session=tc_session, metadata=tc_metadata)
  using_options(shortnames=True, order_by='-start_time')
  using_mapper_options(save_on_init=False)
  tgt_host = Field(Text)
  tgt_port = Field(Integer)
  circuit = ManyToOne('Circuit', inverse='streams')
  detached_circuits = ManyToMany('Circuit', inverse='detatched_streams')
  ignored = Field(Boolean) # Directory streams
  strm_id = Field(Integer, index=True)
  start_time = Field(Float)
  tot_read_bytes = Field(Integer)
  tot_write_bytes = Field(Integer)
  init_status = Field(Text)
  close_reason = Field(Text) # Shared by Failed and Closed. Unused here.

class FailedStream(Stream):
  using_options(shortnames=True, session=tc_session, metadata=tc_metadata)
  using_mapper_options(save_on_init=False)
  fail_reason = Field(Text)
  fail_time = Field(Float)

class ClosedStream(Stream):
  using_options(shortnames=True, session=tc_session, metadata=tc_metadata)
  using_mapper_options(save_on_init=False)
  end_time = Field(Float)
  read_bandwidth = Field(Float)
  write_bandwidth = Field(Float)

  def tot_bytes(self):
    return self.tot_read_bytes
    #return self.tot_read_bytes+self.tot_write_bytes

  def bandwidth(self):
    return self.tot_bandwidth()

  def tot_bandwidth(self):
    #return self.read_bandwidth+self.write_bandwidth 
    return self.read_bandwidth

class RouterStats(Entity):
  using_options(shortnames=True, session=tc_session, metadata=tc_metadata)
  using_mapper_options(save_on_init=False)
  router = ManyToOne('Router', inverse="stats")
   
  # Easily derived from BwHistory
  min_rank = Field(Integer)
  avg_rank = Field(Float)
  max_rank = Field(Integer)
  avg_bw = Field(Float)
  avg_desc_bw = Field(Float)

  percentile = Field(Float)

  # These can be derived with a single query over 
  # FailedExtension and Extension
  circ_fail_to = Field(Float) 
  circ_fail_from = Field(Float)
  circ_try_to = Field(Float)
  circ_try_from = Field(Float)

  circ_from_rate = Field(Float)
  circ_to_rate = Field(Float)
  circ_bi_rate = Field(Float)

  circ_to_ratio = Field(Float)
  circ_from_ratio = Field(Float)
  circ_bi_ratio = Field(Float)

  avg_first_ext = Field(Float)
  ext_ratio = Field(Float)
 
  strm_try = Field(Integer)
  strm_closed = Field(Integer)

  sbw = Field(Float)
  sbw_dev = Field(Float)
  sbw_ratio = Field(Float)
  filt_sbw = Field(Float)
  filt_sbw_ratio = Field(Float)

  def _compute_stats_relation(stats_clause):
    l_session = tc_session()
    for rs in RouterStats.query.\
                   filter(stats_clause).\
                   options(eagerload_all('router.circuits.extensions')).\
                   all():
      rs.circ_fail_to = 0
      rs.circ_try_to = 0
      rs.circ_fail_from = 0
      rs.circ_try_from = 0
      tot_extend_time = 0
      tot_extends = 0
      for c in rs.router.circuits: 
        for e in c.extensions: 
          if e.to_node == r:
            rs.circ_try_to += 1
            if isinstance(e, FailedExtension):
              rs.circ_fail_to += 1
            elif e.hop == 0:
              tot_extend_time += e.delta
              tot_extends += 1
          elif e.from_node == r:
            rs.circ_try_from += 1
            if isinstance(e, FailedExtension):
              rs.circ_fail_from += 1
            
        if isinstance(c, FailedCircuit):
          pass # TODO: Also count timeouts against earlier nodes?
        elif isinstance(c, DestroyedCircuit):
          pass # TODO: Count these somehow..

      if tot_extends > 0: rs.avg_first_ext = (1.0*tot_extend_time)/tot_extends
      else: rs.avg_first_ext = 0
      if rs.circ_try_from > 0:
        rs.circ_from_rate = (1.0*rs.circ_fail_from/rs.circ_try_from)
      if rs.circ_try_to > 0:
        rs.circ_to_rate = (1.0*rs.circ_fail_to/rs.circ_try_to)
      if rs.circ_try_to+rs.circ_try_from > 0:
        rs.circ_bi_rate = (1.0*rs.circ_fail_to+rs.circ_fail_from)/(rs.circ_try_to+rs.circ_try_from)

      l_session.add(rs)
    l_session.commit()
    tc_session.remove()
  _compute_stats_relation = Callable(_compute_stats_relation)


  def _compute_stats_query(stats_clause):
    tc_session.expunge_all()
    l_session = tc_session()
    # http://www.sqlalchemy.org/docs/04/sqlexpression.html#sql_update
    to_s = select([func.count(Extension.id)], 
        and_(stats_clause, Extension.table.c.to_node_idhex
             == RouterStats.table.c.router_idhex)).as_scalar()
    from_s = select([func.count(Extension.id)], 
        and_(stats_clause, Extension.table.c.from_node_idhex
             == RouterStats.table.c.router_idhex)).as_scalar()
    f_to_s = select([func.count(FailedExtension.id)], 
        and_(stats_clause, FailedExtension.table.c.to_node_idhex
             == RouterStats.table.c.router_idhex,
             FailedExtension.table.c.row_type=='failedextension')).as_scalar()
    f_from_s = select([func.count(FailedExtension.id)], 
        and_(stats_clause, FailedExtension.table.c.from_node_idhex
                       == RouterStats.table.c.router_idhex,
             FailedExtension.table.c.row_type=='failedextension')).as_scalar()
    avg_ext = select([func.avg(Extension.delta)], 
        and_(stats_clause,
             Extension.table.c.to_node_idhex==RouterStats.table.c.router_idhex,
             Extension.table.c.hop==0, 
             Extension.table.c.row_type=='extension')).as_scalar()

    RouterStats.table.update(stats_clause, values=
      {RouterStats.table.c.circ_try_to:to_s,
       RouterStats.table.c.circ_try_from:from_s,
       RouterStats.table.c.circ_fail_to:f_to_s,
       RouterStats.table.c.circ_fail_from:f_from_s,
       RouterStats.table.c.avg_first_ext:avg_ext}).execute()

      # added case() to set NULL and avoid divide-by-zeros (Postgres)
    RouterStats.table.update(stats_clause, values=
      {RouterStats.table.c.circ_from_rate:
          case([(RouterStats.table.c.circ_try_from == 0, None)],
              else_=(RouterStats.table.c.circ_fail_from/RouterStats.table.c.circ_try_from)),
       RouterStats.table.c.circ_to_rate:
          case([(RouterStats.table.c.circ_try_to == 0, None)],
              else_=(RouterStats.table.c.circ_fail_to/RouterStats.table.c.circ_try_to)),
       RouterStats.table.c.circ_bi_rate:
          case([(RouterStats.table.c.circ_try_to+RouterStats.table.c.circ_try_from == 0, None)],
           else_=((RouterStats.table.c.circ_fail_to+RouterStats.table.c.circ_fail_from)
                          /
                 (RouterStats.table.c.circ_try_to+RouterStats.table.c.circ_try_from))),
      }).execute()


    # TODO: Give the streams relation table a sane name and reduce this too
    for rs in RouterStats.query.filter(stats_clause).\
                        options(eagerload('router'),
                                eagerload('router.detached_streams'),
                                eagerload('router.streams')).all():
      tot_bw = 0.0
      s_cnt = 0
      tot_bytes = 0.0
      tot_duration = 0.0
      for s in rs.router.streams:
        if isinstance(s, ClosedStream):
          tot_bytes += s.tot_bytes()
          tot_duration += s.end_time - s.start_time
          tot_bw += s.bandwidth()
          s_cnt += 1
      # FIXME: Hrmm.. do we want to do weighted avg or pure avg here?
      # If files are all the same size, it shouldn't matter..
      if s_cnt > 0:
        rs.sbw = tot_bw/s_cnt
      else: rs.sbw = None
      rs.strm_closed = s_cnt
      rs.strm_try = len(rs.router.streams)+len(rs.router.detached_streams)
      if rs.sbw:
        tot_var = 0.0
        for s in rs.router.streams:
          if isinstance(s, ClosedStream):
            tot_var += (s.bandwidth()-rs.sbw)*(s.bandwidth()-rs.sbw)
        tot_var /= s_cnt
        rs.sbw_dev = math.sqrt(tot_var)
      l_session.add(rs)
    l_session.commit()
    tc_session.remove()
  _compute_stats_query = Callable(_compute_stats_query)


  def _compute_stats(stats_clause):
    RouterStats._compute_stats_query(stats_clause)
    #RouterStats._compute_stats_relation(stats_clause)
  _compute_stats = Callable(_compute_stats)

  def _compute_ranks():
    tc_session.expunge_all()
    l_session = tc_session()
    min_r = select([func.min(BwHistory.rank)],
        BwHistory.table.c.router_idhex
            == RouterStats.table.c.router_idhex).as_scalar()
    avg_r = select([func.avg(BwHistory.rank)],
        BwHistory.table.c.router_idhex
            == RouterStats.table.c.router_idhex).as_scalar()
    max_r = select([func.max(BwHistory.rank)],
        BwHistory.table.c.router_idhex
            == RouterStats.table.c.router_idhex).as_scalar()
    avg_bw = select([func.avg(BwHistory.bw)],
        BwHistory.table.c.router_idhex
            == RouterStats.table.c.router_idhex).as_scalar()
    avg_desc_bw = select([func.avg(BwHistory.desc_bw)],
        BwHistory.table.c.router_idhex
            == RouterStats.table.c.router_idhex).as_scalar()

    RouterStats.table.update(values=
       {RouterStats.table.c.min_rank:min_r,
        RouterStats.table.c.avg_rank:avg_r,
        RouterStats.table.c.max_rank:max_r,
        RouterStats.table.c.avg_bw:avg_bw,
        RouterStats.table.c.avg_desc_bw:avg_desc_bw}).execute()

    #min_avg_rank = select([func.min(RouterStats.avg_rank)]).as_scalar()

    # the commented query breaks mysql because UPDATE cannot reference
    # target table in the FROM clause. So we throw in an anonymous alias and wrap
    # another select around it in order to get the nested SELECT stored into a 
    # temporary table.
    # FIXME: performance? no idea 
    #max_avg_rank = select([func.max(RouterStats.avg_rank)]).as_scalar()
    max_avg_rank = select([alias(select([func.max(RouterStats.avg_rank)]))]).as_scalar()

    RouterStats.table.update(values=
       {RouterStats.table.c.percentile:
            (100.0*RouterStats.table.c.avg_rank)/max_avg_rank}).execute()

    l_session.commit()
    tc_session.remove()
  _compute_ranks = Callable(_compute_ranks)

  def _compute_ratios(stats_clause):
    tc_session.expunge_all()
    l_session = tc_session()
    avg_from_rate = select([alias(
        select([func.avg(RouterStats.circ_from_rate)],
                           stats_clause)
        )]).as_scalar()
    avg_to_rate = select([alias(
        select([func.avg(RouterStats.circ_to_rate)],
                           stats_clause)
        )]).as_scalar()
    avg_bi_rate = select([alias(
        select([func.avg(RouterStats.circ_bi_rate)],
                           stats_clause)
        )]).as_scalar()
    avg_ext = select([alias(
        select([func.avg(RouterStats.avg_first_ext)],
                           stats_clause)
        )]).as_scalar()
    avg_sbw = select([alias(
        select([func.avg(RouterStats.sbw)],
                           stats_clause)
        )]).as_scalar()

    RouterStats.table.update(stats_clause, values=
       {RouterStats.table.c.circ_from_ratio:
         (1-RouterStats.table.c.circ_from_rate)/(1-avg_from_rate),
        RouterStats.table.c.circ_to_ratio:
         (1-RouterStats.table.c.circ_to_rate)/(1-avg_to_rate),
        RouterStats.table.c.circ_bi_ratio:
         (1-RouterStats.table.c.circ_bi_rate)/(1-avg_bi_rate),
        RouterStats.table.c.ext_ratio:
         avg_ext/RouterStats.table.c.avg_first_ext,
        RouterStats.table.c.sbw_ratio:
         RouterStats.table.c.sbw/avg_sbw}).execute()
    l_session.commit()
    tc_session.remove()
  _compute_ratios = Callable(_compute_ratios)

  def _compute_filtered_relational(min_ratio, stats_clause, filter_clause):
    l_session = tc_session()
    badrouters = RouterStats.query.filter(stats_clause).filter(filter_clause).\
                   filter(RouterStats.sbw_ratio < min_ratio).all()

    # TODO: Turn this into a single query....
    for rs in RouterStats.query.filter(stats_clause).\
          options(eagerload_all('router.streams.circuit.routers')).all():
      tot_sbw = 0
      sbw_cnt = 0
      for s in rs.router.streams:
        if isinstance(s, ClosedStream):
          skip = False
          #for br in badrouters:
          #  if br != rs:
          #    if br.router in s.circuit.routers:
          #      skip = True
          if not skip:
            # Throw out outliers < mean 
            # (too much variance for stddev to filter much)
            if rs.strm_closed == 1 or s.bandwidth() >= rs.sbw:
              tot_sbw += s.bandwidth()
              sbw_cnt += 1

      if sbw_cnt: rs.filt_sbw = tot_sbw/sbw_cnt
      else: rs.filt_sbw = None
      l_session.add(rs)
    if sqlalchemy.__version__ < "0.5.0":
      avg_sbw = RouterStats.query.filter(stats_clause).avg(RouterStats.filt_sbw)
    else:
      avg_sbw = l_session.query(func.avg(RouterStats.filt_sbw)).filter(stats_clause).scalar()
    for rs in RouterStats.query.filter(stats_clause).all():
      if type(rs.filt_sbw) == float and avg_sbw:
        rs.filt_sbw_ratio = rs.filt_sbw/avg_sbw
      else:
        rs.filt_sbw_ratio = None
      l_session.add(rs)
    l_session.commit()
    tc_session.remove()
  _compute_filtered_relational = Callable(_compute_filtered_relational)

  def _compute_filtered_ratios(min_ratio, stats_clause, filter_clause):
    RouterStats._compute_filtered_relational(min_ratio, stats_clause, 
                                             filter_clause)
    #RouterStats._compute_filtered_query(filter,min_ratio)
  _compute_filtered_ratios = Callable(_compute_filtered_ratios)

  def reset():
    tc_session.expunge_all()
    l_session = tc_session()
    RouterStats.table.drop()
    RouterStats.table.create()
    for r in Router.query.all():
      rs = RouterStats()
      rs.router = r
      r.stats = rs
      l_session.add(r)
    l_session.commit()
    tc_session.remove()
  reset = Callable(reset)

  def compute(pct_low=0, pct_high=100, stat_clause=None, filter_clause=None):
    l_session = tc_session()
    pct_clause = and_(RouterStats.percentile >= pct_low, 
                         RouterStats.percentile < pct_high)
    if stat_clause:
      stat_clause = and_(pct_clause, stat_clause)
    else:
      stat_clause = pct_clause
     
    RouterStats.reset()
    RouterStats._compute_ranks() # No filters. Ranks are independent
    RouterStats._compute_stats(stat_clause)
    RouterStats._compute_ratios(stat_clause)
    RouterStats._compute_filtered_ratios(MIN_RATIO, stat_clause, filter_clause)
    l_session.commit()
    tc_session.remove()
  compute = Callable(compute)  

  def write_stats(f, pct_low=0, pct_high=100, order_by=None, recompute=False, stat_clause=None, filter_clause=None, disp_clause=None):
    l_session = tc_session()

    if not order_by:
      order_by=RouterStats.avg_first_ext

    if recompute:
      RouterStats.compute(pct_low, pct_high, stat_clause, filter_clause)

    pct_clause = and_(RouterStats.percentile >= pct_low, 
                         RouterStats.percentile < pct_high)

    # This is Fail City and sqlalchemy is running for mayor.
    if sqlalchemy.__version__ < "0.5.0":
      circ_from_rate = RouterStats.query.filter(pct_clause).filter(stat_clause).avg(RouterStats.circ_from_rate)
      circ_to_rate = RouterStats.query.filter(pct_clause).filter(stat_clause).avg(RouterStats.circ_to_rate)
      circ_bi_rate = RouterStats.query.filter(pct_clause).filter(stat_clause).avg(RouterStats.circ_bi_rate)

      avg_first_ext = RouterStats.query.filter(pct_clause).filter(stat_clause).avg(RouterStats.avg_first_ext)
      sbw = RouterStats.query.filter(pct_clause).filter(stat_clause).avg(RouterStats.sbw)
      filt_sbw = RouterStats.query.filter(pct_clause).filter(stat_clause).avg(RouterStats.filt_sbw)
      percentile = RouterStats.query.filter(pct_clause).filter(stat_clause).avg(RouterStats.percentile)
    else:
      circ_from_rate = l_session.query(func.avg(RouterStats.circ_from_rate)).filter(pct_clause).filter(stat_clause).scalar()
      circ_to_rate = l_session.query(func.avg(RouterStats.circ_to_rate)).filter(pct_clause).filter(stat_clause).scalar()
      circ_bi_rate = l_session.query(func.avg(RouterStats.circ_bi_rate)).filter(pct_clause).filter(stat_clause).scalar()
      
      avg_first_ext = l_session.query(func.avg(RouterStats.avg_first_ext)).filter(pct_clause).filter(stat_clause).scalar()
      sbw = l_session.query(func.avg(RouterStats.sbw)).filter(pct_clause).filter(stat_clause).scalar()
      filt_sbw = l_session.query(func.avg(RouterStats.filt_sbw)).filter(pct_clause).filter(stat_clause).scalar()
      percentile = l_session.query(func.avg(RouterStats.percentile)).filter(pct_clause).filter(stat_clause).scalar()

    tc_session.remove()

    def cvt(a,b,c=1):
      if type(a) == float: return round(a/c,b)
      elif type(a) == int: return a
      elif type(a) == long: return a
      elif type(a) == type(None): return "None"
      else: return type(a)

    sql_key = """SQLSupport Statistics:
    CF=Circ From Rate          CT=Circ To Rate      CB=Circ To/From Rate
    CE=Avg 1st Ext time (s)    SB=Avg Stream BW     FB=Filtered stream bw
    SD=Strm BW stddev          CC=Circ To Attempts  ST=Strem attempts
    SC=Streams Closed OK       RF=Circ From Ratio   RT=Circ To Ratio     
    RB=Circ To/From Ratio      RE=1st Ext Ratio     RS=Stream BW Ratio   
    RF=Filt Stream Ratio       PR=Percentile Rank\n\n"""
 
    f.write(sql_key)
    f.write("Average Statistics:\n")
    f.write("   CF="+str(cvt(circ_from_rate,2)))
    f.write("  CT="+str(cvt(circ_to_rate,2)))
    f.write("  CB="+str(cvt(circ_bi_rate,2)))
    f.write("  CE="+str(cvt(avg_first_ext,2)))
    f.write("  SB="+str(cvt(sbw,2,1024)))
    f.write("  FB="+str(cvt(filt_sbw,2,1024)))
    f.write("  PR="+str(cvt(percentile,2))+"\n\n\n")

    for s in RouterStats.query.filter(pct_clause).filter(stat_clause).\
             filter(disp_clause).order_by(order_by).all():
      f.write(s.router.idhex+" ("+s.router.nickname+")\n")
      f.write("   CF="+str(cvt(s.circ_from_rate,2)))
      f.write("  CT="+str(cvt(s.circ_to_rate,2)))
      f.write("  CB="+str(cvt(s.circ_bi_rate,2)))
      f.write("  CE="+str(cvt(s.avg_first_ext,2)))
      f.write("  SB="+str(cvt(s.sbw,2,1024)))
      f.write("  FB="+str(cvt(s.filt_sbw,2,1024)))
      f.write("  SD="+str(cvt(s.sbw_dev,2,1024))+"\n")
      f.write("   RF="+str(cvt(s.circ_from_ratio,2)))
      f.write("  RT="+str(cvt(s.circ_to_ratio,2)))
      f.write("  RB="+str(cvt(s.circ_bi_ratio,2)))
      f.write("  RE="+str(cvt(s.ext_ratio,2)))
      f.write("  RS="+str(cvt(s.sbw_ratio,2)))
      f.write("  RF="+str(cvt(s.filt_sbw_ratio,2)))
      f.write("  PR="+str(cvt(s.percentile,1))+"\n")
      f.write("   CC="+str(cvt(s.circ_try_to,1)))
      f.write("  ST="+str(cvt(s.strm_try, 1)))
      f.write("  SC="+str(cvt(s.strm_closed, 1))+"\n\n")

    f.flush()
  write_stats = Callable(write_stats)  
  

  def write_bws(f, pct_low=0, pct_high=100, order_by=None, recompute=False, stat_clause=None, filter_clause=None, disp_clause=None):
    l_session = tc_session()
    if not order_by:
      order_by=RouterStats.avg_first_ext

    if recompute:
      RouterStats.compute(pct_low, pct_high, stat_clause, filter_clause)

    pct_clause = and_(RouterStats.percentile >= pct_low, 
                         RouterStats.percentile < pct_high)

    # This is Fail City and sqlalchemy is running for mayor.
    if sqlalchemy.__version__ < "0.5.0":
      sbw = RouterStats.query.filter(pct_clause).filter(stat_clause).avg(RouterStats.sbw)
      filt_sbw = RouterStats.query.filter(pct_clause).filter(stat_clause).avg(RouterStats.filt_sbw)
    else:
      sbw = l_session.query(func.avg(RouterStats.sbw)).filter(pct_clause).filter(stat_clause).scalar()
      filt_sbw = l_session.query(func.avg(RouterStats.filt_sbw)).filter(pct_clause).filter(stat_clause).scalar()

    f.write(str(int(time.time()))+"\n")

    def cvt(a,b,c=1):
      if type(a) == float: return int(round(a/c,b))
      elif type(a) == int: return a
      elif type(a) == type(None): return "None"
      else: return type(a)

    for s in RouterStats.query.filter(pct_clause).filter(stat_clause).\
           filter(disp_clause).order_by(order_by).all():
      f.write("node_id=$"+s.router.idhex+" nick="+s.router.nickname)
      f.write(" strm_bw="+str(cvt(s.sbw,0)))
      f.write(" filt_bw="+str(cvt(s.filt_sbw,0)))
      f.write(" desc_bw="+str(int(cvt(s.avg_desc_bw,0))))
      f.write(" ns_bw="+str(int(cvt(s.avg_bw,0)))+"\n")

    f.flush()
    tc_session.remove()
  write_bws = Callable(write_bws)  
    

##################### End Model ####################

#################### Model Support ################
def reset_all():
  l_session = tc_session()
  plog("WARN", "SQLSupport.reset_all() called. See SQLSupport.py for details")
  # XXX: We still have a memory leak somewhere in here
  # Current suspects are sqlite, python-sqlite, or sqlalchemy misuse...
  # http://stackoverflow.com/questions/5552932/sqlalchemy-misuse-causing-memory-leak
  # The bandwidth scanners switched to a parent/child model because of this.

  # XXX: WARNING!
  # Must keep the routers around because circ_status_event may
  # reference old Routers that are no longer in consensus
  # and will raise an ObjectDeletedError. See function circ_status_event in
  # class CircuitListener in SQLSupport.py
  for r in Router.query.all():
    # This appears to be needed. the relation tables do not get dropped 
    # automatically.
    r.circuits = []
    r.streams = []
    r.detached_streams = []
    r.bw_history = [] 
    r.stats = None
    l_session.add(r)

  l_session.commit()
  tc_session.expunge_all()

  # XXX: WARNING!
  # May not clear relation all tables! (SQLAlchemy or Elixir bug)
  # Try: 
  # tc_session.execute('delete from router_streams__stream;')


  # XXX: WARNING!
  # This will cause Postgres databases to hang
  # on DROP TABLE. Possibly an issue with cascade.
  # Sqlite works though.

  BwHistory.table.drop() # Will drop subclasses
  Extension.table.drop()
  Stream.table.drop() 
  Circuit.table.drop()
  RouterStats.table.drop()

  RouterStats.table.create()
  BwHistory.table.create() 
  Extension.table.create()
  Stream.table.create() 
  Circuit.table.create()

  l_session.commit()

  #for r in Router.query.all():
  #  if len(r.bw_history) or len(r.circuits) or len(r.streams) or r.stats:
  #    plog("WARN", "Router still has dropped data!")

  plog("NOTICE", "Reset all SQL stats")
  tc_session.remove()

def refresh_all():
  # necessary to keep all sessions synchronized
  # This is probably a bug. See reset_all() above.
  # Call this after update_consensus(), _update_rank_history()
  # See: ScanSupport.reset_stats()
  # Could be a cascade problem too, see:
  # http://stackoverflow.com/questions/3481976/sqlalchemy-objectdeletederror-instance-class-at-has-been-deleted-help
  # Also see:
  # http://groups.google.com/group/sqlalchemy/browse_thread/thread/c9099eaaffd7c348
  [tc_session.refresh(r) for r in Router.query.all()]

##################### End Model Support ####################

class ConsensusTrackerListener(TorCtl.DualEventListener):
  def __init__(self):
    TorCtl.DualEventListener.__init__(self)
    self.last_desc_at = time.time()+60 # Give tor some time to start up
    self.consensus = None
    self.wait_for_signal = False

  CONSENSUS_DONE = 0x7fffffff

  # TODO: What about non-running routers and uptime information?
  def _update_rank_history(self, idlist):
    l_session = tc_session()
    plog("INFO", "Consensus change... Updating rank history")
    for idhex in idlist:
      if idhex not in self.consensus.routers: continue
      rc = self.consensus.routers[idhex]
      if rc.down: continue
      try:
        r = Router.query.options(eagerload('bw_history')).filter_by(
                                    idhex=idhex).with_labels().one()
        bwh = BwHistory(router=r, rank=rc.list_rank, bw=rc.bw,
                        desc_bw=rc.desc_bw, pub_time=r.published)
        r.bw_history.append(bwh)
        #l_session.add(bwh)
        l_session.add(r)
      except sqlalchemy.orm.exc.NoResultFound:
        plog("WARN", "No descriptor found for consenus router "+str(idhex))

    plog("INFO", "Consensus history updated.")
    l_session.commit()
    tc_session.remove()

  def _update_db(self, idlist):
    l_session = tc_session()
    # FIXME: It is tempting to delay this as well, but we need
    # this info to be present immediately for circuit construction...
    plog("INFO", "Consensus change... Updating db")
    for idhex in idlist:
      if idhex in self.consensus.routers:
        rc = self.consensus.routers[idhex]
        r = Router.query.filter_by(idhex=rc.idhex).first()
        if r and r.orhash == rc.orhash:
          # We already have it stored. (Possible spurious NEWDESC)
          continue
        if not r: r = Router()
        r.from_router(rc)
        l_session.add(r)
    plog("INFO", "Consensus db updated")
    l_session.commit()
    tc_session.remove()
    # testing
    #refresh_all() # Too many sessions, don't trust commit()

  def update_consensus(self):
    plog("INFO", "Updating DB with full consensus.")
    self.consensus = self.parent_handler.current_consensus()
    self._update_db(self.consensus.ns_map.iterkeys())

  def set_parent(self, parent_handler):
    if not isinstance(parent_handler, TorCtl.ConsensusTracker):
      raise TorCtlError("ConsensusTrackerListener can only be attached to ConsensusTracker instances")
    TorCtl.DualEventListener.set_parent(self, parent_handler)

  def heartbeat_event(self, e):
    l_session = tc_session()
    # This sketchiness is to ensure we have an accurate history
    # of each router's rank+bandwidth for the entire duration of the run..
    if e.state == EVENT_STATE.PRELISTEN:
      if not self.consensus: 
        global OP
        OP = Router.query.filter_by(
                 idhex="0000000000000000000000000000000000000000").first()
        if not OP:
          OP = Router(idhex="0000000000000000000000000000000000000000", 
                    orhash="000000000000000000000000000", 
                    nickname="!!TorClient", 
                    published=datetime.datetime.utcnow())
          l_session.add(OP)
          l_session.commit()
          tc_session.remove()
        self.update_consensus()
      # XXX: This hack exists because update_rank_history is expensive.
      # However, even if we delay it till the end of the consensus update, 
      # it still delays event processing for up to 30 seconds on a fast 
      # machine.
      # 
      # The correct way to do this is give SQL processing
      # to a dedicated worker thread that pulls events off of a secondary
      # queue, that way we don't block stream handling on this processing.
      # The problem is we are pretty heavily burdened with the need to 
      # stay in sync with our parent event handler. A queue will break this 
      # coupling (even if we could get all the locking right).
      #
      # A lighterweight hack might be to just make the scanners pause
      # on a condition used to signal we are doing this (and other) heavy 
      # lifting. We could have them possibly check self.last_desc_at..
      if not self.wait_for_signal and e.arrived_at - self.last_desc_at > 60.0:
        if self.consensus.consensus_count  < 0.95*(len(self.consensus.ns_map)):
          plog("INFO", "Not enough router descriptors: "
                       +str(self.consensus.consensus_count)+"/"
                       +str(len(self.consensus.ns_map)))
        elif not PathSupport.PathBuilder.is_urgent_event(e):
          plog("INFO", "Newdesc timer is up. Assuming we have full consensus")
          self._update_rank_history(self.consensus.ns_map.iterkeys())
          self.last_desc_at = ConsensusTrackerListener.CONSENSUS_DONE

  def new_consensus_event(self, n):
    if n.state == EVENT_STATE.POSTLISTEN:
      self.last_desc_at = n.arrived_at
      self.update_consensus()

  def new_desc_event(self, d): 
    if d.state == EVENT_STATE.POSTLISTEN:
      self.last_desc_at = d.arrived_at
      self.consensus = self.parent_handler.current_consensus()
      self._update_db(d.idlist)

class CircuitListener(TorCtl.PreEventListener):
  def set_parent(self, parent_handler):
    if not filter(lambda f: f.__class__ == ConsensusTrackerListener, 
                  parent_handler.post_listeners):
       raise TorCtlError("CircuitListener needs a ConsensusTrackerListener")
    TorCtl.PreEventListener.set_parent(self, parent_handler)
    # TODO: This is really lame. We only know the extendee of a circuit
    # if we have built the path ourselves. Otherwise, Tor keeps it a
    # secret from us. This prevents us from properly tracking failures
    # for normal Tor usage.
    if isinstance(parent_handler, PathSupport.PathBuilder):
      self.track_parent = True
    else:
      self.track_parent = False

  def circ_status_event(self, c):
    l_session = tc_session()
    if self.track_parent and c.circ_id not in self.parent_handler.circuits:
      tc_session.remove()
      return # Ignore circuits that aren't ours
    # TODO: Hrmm, consider making this sane in TorCtl.
    if c.reason: lreason = c.reason
    else: lreason = "NONE"
    if c.remote_reason: rreason = c.remote_reason
    else: rreason = "NONE"
    reason = c.event_name+":"+c.status+":"+lreason+":"+rreason

    output = [str(c.arrived_at), str(time.time()-c.arrived_at), c.event_name, str(c.circ_id), c.status]
    if c.path: output.append(",".join(c.path))
    if c.reason: output.append("REASON=" + c.reason)
    if c.remote_reason: output.append("REMOTE_REASON=" + c.remote_reason)
    plog("DEBUG", " ".join(output))
  
    if c.status == "LAUNCHED":
      circ = Circuit(circ_id=c.circ_id,launch_time=c.arrived_at,
                     last_extend=c.arrived_at)
      if self.track_parent:
        for r in self.parent_handler.circuits[c.circ_id].path:
          try:
            rq = Router.query.options(eagerload('circuits')).filter_by(
                                idhex=r.idhex).with_labels().one()
          except NoResultFound:
            plog("WARN", "Query for Router %s=%s in circ %s failed but was in parent_handler" %
                    (r.nickname, r.idhex, circ.circ_id))
            tc_session.remove()
            return
          circ.routers.append(rq) 
          #rq.circuits.append(circ) # done automagically?
          #l_session.add(rq)
      l_session.add(circ)
      l_session.commit()
    elif c.status == "EXTENDED":
      circ = Circuit.query.options(eagerload('extensions')).filter_by(
                       circ_id = c.circ_id).first()
      if not circ: 
        tc_session.remove()
        return # Skip circuits from before we came online

      e = Extension(circ=circ, hop=len(c.path)-1, time=c.arrived_at)

      if len(c.path) == 1:
        e.from_node = OP
      else:
        r_ext = c.path[-2]
        if r_ext[0] != '$': r_ext = self.parent_handler.name_to_key[r_ext]
        e.from_node = Router.query.filter_by(idhex=r_ext[1:]).one()

      r_ext = c.path[-1]
      if r_ext[0] != '$': r_ext = self.parent_handler.name_to_key[r_ext]

      e.to_node = Router.query.filter_by(idhex=r_ext[1:]).one()
      if not self.track_parent:
        # FIXME: Eager load here?
        circ.routers.append(e.to_node)
        e.to_node.circuits.append(circ)
        l_session.add(e.to_node)
 
      e.delta = c.arrived_at - circ.last_extend
      circ.last_extend = c.arrived_at
      circ.extensions.append(e)
      l_session.add(e)
      l_session.add(circ)
      l_session.commit()
    elif c.status == "FAILED":
      circ = Circuit.query.filter_by(circ_id = c.circ_id).first()
      if not circ: 
        tc_session.remove()
        return # Skip circuits from before we came online
        
      circ.expunge()
      if isinstance(circ, BuiltCircuit):
        # Convert to destroyed circuit
        Circuit.table.update(Circuit.id ==
                  circ.id).execute(row_type='destroyedcircuit')
        circ = DestroyedCircuit.query.filter_by(id=circ.id).one()
        circ.destroy_reason = reason
        circ.destroy_time = c.arrived_at
      else:
        # Convert to failed circuit
        Circuit.table.update(Circuit.id ==
                  circ.id).execute(row_type='failedcircuit')
        circ = FailedCircuit.query.options(
                  eagerload('extensions')).filter_by(id=circ.id).one()
        circ.fail_reason = reason
        circ.fail_time = c.arrived_at
        e = FailedExtension(circ=circ, hop=len(c.path), time=c.arrived_at)

        if len(c.path) == 0:
          e.from_node = OP
        else:
          r_ext = c.path[-1]
          if r_ext[0] != '$': r_ext = self.parent_handler.name_to_key[r_ext]
 
          e.from_node = Router.query.filter_by(idhex=r_ext[1:]).one()

        if self.track_parent:
          r=self.parent_handler.circuits[c.circ_id].path[len(c.path)]
          e.to_node = Router.query.filter_by(idhex=r.idhex).one()
        else:
          e.to_node = None # We have no idea..

        e.delta = c.arrived_at - circ.last_extend
        e.reason = reason
        circ.extensions.append(e)
        circ.fail_time = c.arrived_at
        l_session.add(e)

      l_session.add(circ)
      l_session.commit()
    elif c.status == "BUILT":
      circ = Circuit.query.filter_by(
                     circ_id = c.circ_id).first()
      if not circ:
        tc_session.remove()
        return # Skip circuits from before we came online

      circ.expunge()
      # Convert to built circuit
      Circuit.table.update(Circuit.id ==
                circ.id).execute(row_type='builtcircuit')
      circ = BuiltCircuit.query.filter_by(id=circ.id).one()
      
      circ.built_time = c.arrived_at
      circ.tot_delta = c.arrived_at - circ.launch_time
      l_session.add(circ)
      l_session.commit()
    elif c.status == "CLOSED":
      circ = BuiltCircuit.query.filter_by(circ_id = c.circ_id).first()
      if circ:
        circ.expunge()
        if lreason in ("REQUESTED", "FINISHED", "ORIGIN"):
          # Convert to closed circuit
          Circuit.table.update(Circuit.id ==
                    circ.id).execute(row_type='closedcircuit')
          circ = ClosedCircuit.query.filter_by(id=circ.id).one()
          circ.closed_time = c.arrived_at
        else:
          # Convert to destroyed circuit
          Circuit.table.update(Circuit.id ==
                    circ.id).execute(row_type='destroyedcircuit')
          circ = DestroyedCircuit.query.filter_by(id=circ.id).one()
          circ.destroy_reason = reason
          circ.destroy_time = c.arrived_at
        l_session.add(circ)
        l_session.commit()
    tc_session.remove()

class StreamListener(CircuitListener):
  def stream_bw_event(self, s):
    l_session = tc_session()
    strm = Stream.query.filter_by(strm_id = s.strm_id).first()
    if strm and strm.start_time and strm.start_time < s.arrived_at:
      plog("DEBUG", "Got stream bw: "+str(s.strm_id))
      strm.tot_read_bytes += s.bytes_read
      strm.tot_write_bytes += s.bytes_written
      l_session.add(strm)
      l_session.commit()
      tc_session.remove()
 
  def stream_status_event(self, s):
    l_session = tc_session()
    if s.reason: lreason = s.reason
    else: lreason = "NONE"
    if s.remote_reason: rreason = s.remote_reason
    else: rreason = "NONE"

    if s.status in ("NEW", "NEWRESOLVE"):
      strm = Stream(strm_id=s.strm_id, tgt_host=s.target_host, 
                    tgt_port=s.target_port, init_status=s.status,
                    tot_read_bytes=0, tot_write_bytes=0)
      l_session.add(strm)
      l_session.commit()
      tc_session.remove()
      return

    strm = Stream.query.filter_by(strm_id = s.strm_id).first()
    if self.track_parent and \
      (s.strm_id not in self.parent_handler.streams or \
           self.parent_handler.streams[s.strm_id].ignored):
      if strm:
        strm.delete()
        l_session.commit()
        tc_session.remove()
      return # Ignore streams that aren't ours

    if not strm: 
      plog("NOTICE", "Ignoring prior stream "+str(s.strm_id))
      return # Ignore prior streams

    reason = s.event_name+":"+s.status+":"+lreason+":"+rreason+":"+strm.init_status

    if s.status == "SENTCONNECT":
      # New circuit
      strm.circuit = Circuit.query.filter_by(circ_id=s.circ_id).first()
      if not strm.circuit:
        plog("NOTICE", "Ignoring prior stream "+str(strm.strm_id)+" with old circuit "+str(s.circ_id))
        strm.delete()
        l_session.commit()
        tc_session.remove()
        return
    else:
      circ = None
      if s.circ_id:
        circ = Circuit.query.filter_by(circ_id=s.circ_id).first()
      elif self.track_parent:
        circ = self.parent_handler.streams[s.strm_id].circ
        if not circ: circ = self.parent_handler.streams[s.strm_id].pending_circ
        if circ:
          circ = Circuit.query.filter_by(circ_id=circ.circ_id).first()

      if not circ:
        plog("WARN", "No circuit for "+str(s.strm_id)+" circ: "+str(s.circ_id))

      if not strm.circuit:
        plog("INFO", "No stream circuit for "+str(s.strm_id)+" circ: "+str(s.circ_id))
        strm.circuit = circ

      # XXX: Verify circ id matches stream.circ
    
    if s.status == "SUCCEEDED":
      strm.start_time = s.arrived_at
      for r in strm.circuit.routers: 
        plog("DEBUG", "Added router "+r.idhex+" to stream "+str(s.strm_id))
        r.streams.append(strm)
        l_session.add(r)
      l_session.add(strm)
      l_session.commit()
    elif s.status == "DETACHED":
      for r in strm.circuit.routers:
        r.detached_streams.append(strm)
        l_session.add(r)
      #strm.detached_circuits.append(strm.circuit)
      strm.circuit.detached_streams.append(strm)
      strm.circuit.streams.remove(strm)
      strm.circuit = None
      l_session.add(strm)
      l_session.commit()
    elif s.status == "FAILED":
      strm.expunge()
      # Convert to destroyed circuit
      Stream.table.update(Stream.id ==
                strm.id).execute(row_type='failedstream')
      strm = FailedStream.query.filter_by(id=strm.id).one()
      strm.fail_time = s.arrived_at
      strm.fail_reason = reason
      l_session.add(strm)
      l_session.commit()
    elif s.status == "CLOSED":
      if isinstance(strm, FailedStream):
        strm.close_reason = reason
      else:
        strm.expunge()
        if not (lreason == "DONE" or (lreason == "END" and rreason == "DONE")):
          # Convert to destroyed circuit
          Stream.table.update(Stream.id ==
                    strm.id).execute(row_type='failedstream')
          strm = FailedStream.query.filter_by(id=strm.id).one()
          strm.fail_time = s.arrived_at
        else: 
          # Convert to destroyed circuit
          Stream.table.update(Stream.id ==
                    strm.id).execute(row_type='closedstream')
          strm = ClosedStream.query.filter_by(id=strm.id).one()
          strm.read_bandwidth = strm.tot_read_bytes/(s.arrived_at-strm.start_time)
          strm.write_bandwidth = strm.tot_write_bytes/(s.arrived_at-strm.start_time)
          strm.end_time = s.arrived_at
          plog("DEBUG", "Stream "+str(strm.strm_id)+" xmitted "+str(strm.tot_bytes()))
        strm.close_reason = reason
      l_session.add(strm)
      l_session.commit()
    tc_session.remove()

def run_example(host, port):
  """ Example of basic TorCtl usage. See PathSupport for more advanced
      usage.
  """
  print "host is %s:%d"%(host,port)
  setup_db("sqlite:///torflow.sqlite", echo=False)

  #l_session = tc_session()
  #print l_session.query(((func.count(Extension.id)))).filter(and_(FailedExtension.table.c.row_type=='extension', FailedExtension.table.c.from_node_idhex == "7CAA2F5F998053EF5D2E622563DEB4A6175E49AC")).one()
  #return
  #for e in Extension.query.filter(FailedExtension.table.c.row_type=='extension').all():
  #  if e.from_node: print "From: "+e.from_node.idhex+" "+e.from_node.nickname
  #  if e.to_node: print "To: "+e.to_node.idhex+" "+e.to_node.nickname
  #tc_session.remove()
  #return

  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  s.connect((host,port))
  c = Connection(s)
  th = c.launch_thread()
  c.authenticate(control_pass)
  c.set_event_handler(TorCtl.ConsensusTracker(c))
  c.add_event_listener(ConsensusTrackerListener())
  c.add_event_listener(CircuitListener())

  print `c.extend_circuit(0,["moria1"])`
  try:
    print `c.extend_circuit(0,[""])`
  except TorCtl.ErrorReply: # wtf?
    print "got error. good."
  except:
    print "Strange error", sys.exc_info()[0]
   
  c.set_events([EVENT_TYPE.STREAM, EVENT_TYPE.CIRC,
          EVENT_TYPE.NEWCONSENSUS, EVENT_TYPE.NEWDESC,
          EVENT_TYPE.ORCONN, EVENT_TYPE.BW], True)

  th.join()
  return

  
if __name__ == '__main__':
  run_example(control_host,control_port)


########NEW FILE########
__FILENAME__ = StatsSupport
#!/usr/bin/python
#StatsSupport.py - functions and classes useful for calculating stream/circuit statistics

"""

Support classes for statisics gathering

The StatsSupport package contains several classes that extend
PathSupport to gather continuous statistics on the Tor network.

The main entrypoint is to extend or create an instance of the
StatsHandler class. The StatsHandler extends from
TorCtl.PathSupport.PathBuilder, which is itself a TorCtl.EventHandler.
The StatsHandler listens to CIRC and STREAM events and gathers all
manner of statics on their creation and failure before passing the
events back up to the PathBuilder code, which manages the actual
construction and the attachment of streams to circuits.

The package also contains a number of support classes that help gather
additional statistics on the reliability and performance of routers.

For the purpose of accounting failures, the code tracks two main classes
of failure: 'actual' failure and 'suspected' failure. The general rule
is that an actual failure is attributed to the node that directly
handled the circuit or stream. For streams, this is considered to be the
exit node. For circuits, it is both the extender and the extendee.
'Suspected' failures, on the other hand, are attributed to every member
of the circuit up until the extendee for circuits, and all hops for
streams.

For bandwidth accounting, the average stream bandwidth and the average
ratio of stream bandwidth to advertised bandwidth are tracked, and when
the statistics are written, a Z-test is performed to calculate the
probabilities of these values assuming a normal distribution. Note,
however, that it has not been verified that this distribution is
actually normal. It is likely to be something else (pareto, perhaps?).

"""

import sys
import re
import random
import copy
import time
import math
import traceback

import TorUtil, PathSupport, TorCtl
from TorUtil import *
from PathSupport import *
from TorUtil import meta_port, meta_host, control_port, control_host

class ReasonRouterList:
  "Helper class to track which Routers have failed for a given reason"
  def __init__(self, reason):
    self.reason = reason
    self.rlist = {}

  def sort_list(self): raise NotImplemented()

  def write_list(self, f):
    "Write the list of failure counts for this reason 'f'"
    rlist = self.sort_list()
    for r in rlist:
      susp = 0
      tot_failed = r.circ_failed+r.strm_failed
      tot_susp = tot_failed+r.circ_suspected+r.strm_suspected
      f.write(r.idhex+" ("+r.nickname+") F=")
      if self.reason in r.reason_failed:
        susp = r.reason_failed[self.reason]
      f.write(str(susp)+"/"+str(tot_failed))
      f.write(" S=")
      if self.reason in r.reason_suspected:
        susp += r.reason_suspected[self.reason]
      f.write(str(susp)+"/"+str(tot_susp)+"\n")
    
  def add_r(self, r):
    "Add a router to the list for this reason"
    self.rlist[r] = 1

  def total_suspected(self):
    "Get a list of total suspected failures for this reason"
    # suspected is disjoint from failed. The failed table
    # may not have an entry
    def notlambda(x, y):
      if self.reason in y.reason_suspected:
        if self.reason in y.reason_failed:
          return (x + y.reason_suspected[self.reason]
               + y.reason_failed[self.reason])
        else:
          return (x + y.reason_suspected[self.reason])
      else:
        if self.reason in y.reason_failed:
          return (x + y.reason_failed[self.reason])
        else: return x
    return reduce(notlambda, self.rlist.iterkeys(), 0)

  def total_failed(self):
    "Get a list of total failures for this reason"
    def notlambda(x, y):
      if self.reason in y.reason_failed:
        return (x + y.reason_failed[self.reason])
      else: return x
    return reduce(notlambda, self.rlist.iterkeys(), 0)
 
class SuspectRouterList(ReasonRouterList):
  """Helper class to track all routers suspected of failing for a given
     reason. The main difference between this and the normal
     ReasonRouterList is the sort order and the verification."""
  def __init__(self, reason): ReasonRouterList.__init__(self,reason)
  
  def sort_list(self):
    rlist = self.rlist.keys()
    rlist.sort(lambda x, y: cmp(y.reason_suspected[self.reason],
                  x.reason_suspected[self.reason]))
    return rlist
   
  def _verify_suspected(self):
    return reduce(lambda x, y: x + y.reason_suspected[self.reason],
            self.rlist.iterkeys(), 0)

class FailedRouterList(ReasonRouterList):
  """Helper class to track all routers that failed for a given
     reason. The main difference between this and the normal
     ReasonRouterList is the sort order and the verification."""
  def __init__(self, reason): ReasonRouterList.__init__(self,reason)

  def sort_list(self):
    rlist = self.rlist.keys()
    rlist.sort(lambda x, y: cmp(y.reason_failed[self.reason],
                  x.reason_failed[self.reason]))
    return rlist

  def _verify_failed(self):
    return reduce(lambda x, y: x + y.reason_failed[self.reason],
            self.rlist.iterkeys(), 0)
class BandwidthStats:
  "Class that manages observed bandwidth through a Router"
  def __init__(self):
    self.byte_list = []
    self.duration_list = []
    self.min_bw = 1e10
    self.max_bw = 0
    self.mean = 0
    self.dev = 0

  def _exp(self): # Weighted avg
    "Expectation - weighted average of the bandwidth through this node"
    tot_bw = reduce(lambda x, y: x+y, self.byte_list, 0.0)
    EX = 0.0
    for i in xrange(len(self.byte_list)):
      EX += (self.byte_list[i]*self.byte_list[i])/self.duration_list[i]
    if tot_bw == 0.0: return 0.0
    EX /= tot_bw
    return EX

  def _exp2(self): # E[X^2]
    "Second moment of the bandwidth"
    tot_bw = reduce(lambda x, y: x+y, self.byte_list, 0.0)
    EX = 0.0
    for i in xrange(len(self.byte_list)):
      EX += (self.byte_list[i]**3)/(self.duration_list[i]**2)
    if tot_bw == 0.0: return 0.0
    EX /= tot_bw
    return EX
    
  def _dev(self): # Weighted dev
    "Standard deviation of bandwidth"
    EX = self.mean
    EX2 = self._exp2()
    arg = EX2 - (EX*EX)
    if arg < -0.05:
      plog("WARN", "Diff of "+str(EX2)+" and "+str(EX)+"^2 is "+str(arg))
    return math.sqrt(abs(arg))

  def add_bw(self, bytes, duration):
    "Add an observed transfer of 'bytes' for 'duration' seconds"
    if not bytes: plog("NOTICE", "No bytes for bandwidth")
    bytes /= 1024.
    self.byte_list.append(bytes)
    self.duration_list.append(duration)
    bw = bytes/duration
    plog("DEBUG", "Got bandwidth "+str(bw))
    if self.min_bw > bw: self.min_bw = bw
    if self.max_bw < bw: self.max_bw = bw
    self.mean = self._exp()
    self.dev = self._dev()


class StatsRouter(TorCtl.Router):
  "Extended Router to handle statistics markup"
  def __init__(self, router): # Promotion constructor :)
    """'Promotion Constructor' that converts a Router directly into a 
    StatsRouter without a copy."""
    # TODO: Use __bases__ to do this instead?
    self.__dict__ = router.__dict__
    self.reset()
    # StatsRouters should not be destroyed when Tor forgets about them
    # Give them an extra refcount:
    self.refcount += 1
    plog("DEBUG", "Stats refcount "+str(self.refcount)+" for "+self.idhex)

  def reset(self):
    "Reset all stats on this Router"
    self.circ_uncounted = 0
    self.circ_failed = 0
    self.circ_succeeded = 0 # disjoint from failed
    self.circ_suspected = 0
    self.circ_chosen = 0 # above 4 should add to this
    self.strm_failed = 0 # Only exits should have these
    self.strm_succeeded = 0
    self.strm_suspected = 0 # disjoint from failed
    self.strm_uncounted = 0
    self.strm_chosen = 0 # above 4 should add to this
    self.reason_suspected = {}
    self.reason_failed = {}
    self.first_seen = time.time()
    if "Running" in self.flags:
      self.became_active_at = self.first_seen
      self.hibernated_at = 0
    else:
      self.became_active_at = 0
      self.hibernated_at = self.first_seen
    self.total_hibernation_time = 0
    self.total_active_uptime = 0
    self.total_extend_time = 0
    self.total_extended = 0
    self.bwstats = BandwidthStats()
    self.z_ratio = 0
    self.prob_zr = 0
    self.z_bw = 0
    self.prob_zb = 0
    self.rank_history = []
    self.bw_history = []

  def was_used(self):
    """Return True if this router was used in this round"""
    return self.circ_chosen != 0

  def avg_extend_time(self):
    """Return the average amount of time it took for this router
     to extend a circuit one hop"""
    if self.total_extended:
      return self.total_extend_time/self.total_extended
    else: return 0

  def bw_ratio(self):
    """Return the ratio of the Router's advertised bandwidth to its 
     observed average stream bandwidth"""
    bw = self.bwstats.mean
    if bw == 0.0: return 0
    else: return self.bw/(1024.*bw)

  def adv_ratio(self): # XXX
    """Return the ratio of the Router's advertised bandwidth to 
       the overall average observed bandwith"""
    bw = StatsRouter.global_bw_mean
    if bw == 0.0: return 0
    else: return self.bw/bw

  def avg_rank(self):
    if not self.rank_history: return self.list_rank
    return (1.0*sum(self.rank_history))/len(self.rank_history)

  def bw_ratio_ratio(self):
    bwr = self.bw_ratio()
    if bwr == 0.0: return 0
    # (avg_reported_bw/our_reported_bw) *
    # (our_stream_capacity/avg_stream_capacity)
    return StatsRouter.global_ratio_mean/bwr 

  def strm_bw_ratio(self):
    """Return the ratio of the Router's stream capacity to the average
       stream capacity passed in as 'mean'"""
    bw = self.bwstats.mean
    if StatsRouter.global_strm_mean == 0.0: return 0
    else: return (1.0*bw)/StatsRouter.global_strm_mean

  def circ_fail_rate(self):
    if self.circ_chosen == 0: return 0
    return (1.0*self.circ_failed)/self.circ_chosen

  def strm_fail_rate(self):
    if self.strm_chosen == 0: return 0
    return (1.0*self.strm_failed)/self.strm_chosen

  def circ_suspect_rate(self):
    if self.circ_chosen == 0: return 1
    return (1.0*(self.circ_suspected+self.circ_failed))/self.circ_chosen

  def strm_suspect_rate(self):
    if self.strm_chosen == 0: return 1
    return (1.0*(self.strm_suspected+self.strm_failed))/self.strm_chosen

  def circ_suspect_ratio(self):
    if 1.0-StatsRouter.global_cs_mean <= 0.0: return 0
    return (1.0-self.circ_suspect_rate())/(1.0-StatsRouter.global_cs_mean)

  def strm_suspect_ratio(self):
    if 1.0-StatsRouter.global_ss_mean <= 0.0: return 0
    return (1.0-self.strm_suspect_rate())/(1.0-StatsRouter.global_ss_mean)

  def circ_fail_ratio(self):
    if 1.0-StatsRouter.global_cf_mean <= 0.0: return 0
    return (1.0-self.circ_fail_rate())/(1.0-StatsRouter.global_cf_mean)

  def strm_fail_ratio(self):
    if 1.0-StatsRouter.global_sf_mean <= 0.0: return 0
    return (1.0-self.strm_fail_rate())/(1.0-StatsRouter.global_sf_mean)

  def current_uptime(self):
    if self.became_active_at:
      ret = (self.total_active_uptime+(time.time()-self.became_active_at))
    else:
      ret = self.total_active_uptime
    if ret == 0: return 0.000005 # eh..
    else: return ret
        
  def failed_per_hour(self):
    """Return the number of circuit extend failures per hour for this 
     Router"""
    return (3600.*(self.circ_failed+self.strm_failed))/self.current_uptime()

  # XXX: Seperate suspected from failed in totals 
  def suspected_per_hour(self):
    """Return the number of circuits that failed with this router as an
     earlier hop"""
    return (3600.*(self.circ_suspected+self.strm_suspected
          +self.circ_failed+self.strm_failed))/self.current_uptime()

  # These four are for sanity checking
  def _suspected_per_hour(self):
    return (3600.*(self.circ_suspected+self.strm_suspected))/self.current_uptime()

  def _uncounted_per_hour(self):
    return (3600.*(self.circ_uncounted+self.strm_uncounted))/self.current_uptime()

  def _chosen_per_hour(self):
    return (3600.*(self.circ_chosen+self.strm_chosen))/self.current_uptime()

  def _succeeded_per_hour(self):
    return (3600.*(self.circ_succeeded+self.strm_succeeded))/self.current_uptime()
  
  key = """Metatroller Router Statistics:
  CC=Circuits Chosen   CF=Circuits Failed      CS=Circuit Suspected
  SC=Streams Chosen    SF=Streams Failed       SS=Streams Suspected
  FH=Failed per Hour   SH=Suspected per Hour   ET=avg circuit Extend Time (s)
  EB=mean BW (K)       BD=BW std Dev (K)       BR=Ratio of observed to avg BW
  ZB=BW z-test value   PB=Probability(z-bw)    ZR=Ratio z-test value
  PR=Prob(z-ratio)     SR=Global mean/mean BW  U=Uptime (h)\n"""

  global_strm_mean = 0.0
  global_strm_dev = 0.0
  global_ratio_mean = 0.0
  global_ratio_dev = 0.0
  global_bw_mean = 0.0
  global_cf_mean = 0.0
  global_sf_mean = 0.0
  global_cs_mean = 0.0
  global_ss_mean = 0.0

  def __str__(self):
    return (self.idhex+" ("+self.nickname+")\n"
    +"   CC="+str(self.circ_chosen)
      +" CF="+str(self.circ_failed)
      +" CS="+str(self.circ_suspected+self.circ_failed)
      +" SC="+str(self.strm_chosen)
      +" SF="+str(self.strm_failed)
      +" SS="+str(self.strm_suspected+self.strm_failed)
      +" FH="+str(round(self.failed_per_hour(),1))
      +" SH="+str(round(self.suspected_per_hour(),1))+"\n"
    +"   ET="+str(round(self.avg_extend_time(),1))
      +" EB="+str(round(self.bwstats.mean,1))
      +" BD="+str(round(self.bwstats.dev,1))
      +" ZB="+str(round(self.z_bw,1))
      +" PB="+(str(round(self.prob_zb,3))[1:])
      +" BR="+str(round(self.bw_ratio(),1))
      +" ZR="+str(round(self.z_ratio,1))
      +" PR="+(str(round(self.prob_zr,3))[1:])
      +" SR="+(str(round(self.strm_bw_ratio(),1)))
      +" U="+str(round(self.current_uptime()/3600, 1))+"\n")

  def sanity_check(self):
    "Makes sure all stats are self-consistent"
    if (self.circ_failed + self.circ_succeeded + self.circ_suspected
      + self.circ_uncounted != self.circ_chosen):
      plog("ERROR", self.nickname+" does not add up for circs")
    if (self.strm_failed + self.strm_succeeded + self.strm_suspected
      + self.strm_uncounted != self.strm_chosen):
      plog("ERROR", self.nickname+" does not add up for streams")
    def check_reasons(reasons, expected, which, rtype):
      count = 0
      for rs in reasons.iterkeys():
        if re.search(r"^"+which, rs): count += reasons[rs]
      if count != expected:
        plog("ERROR", "Mismatch "+which+" "+rtype+" for "+self.nickname)
    check_reasons(self.reason_suspected,self.strm_suspected,"STREAM","susp")
    check_reasons(self.reason_suspected,self.circ_suspected,"CIRC","susp")
    check_reasons(self.reason_failed,self.strm_failed,"STREAM","failed")
    check_reasons(self.reason_failed,self.circ_failed,"CIRC","failed")
    now = time.time()
    tot_hib_time = self.total_hibernation_time
    tot_uptime = self.total_active_uptime
    if self.hibernated_at: tot_hib_time += now - self.hibernated_at
    if self.became_active_at: tot_uptime += now - self.became_active_at
    if round(tot_hib_time+tot_uptime) != round(now-self.first_seen):
      plog("ERROR", "Mismatch of uptimes for "+self.nickname)
    
    per_hour_tot = round(self._uncounted_per_hour()+self.failed_per_hour()+
         self._suspected_per_hour()+self._succeeded_per_hour(), 2)
    chosen_tot = round(self._chosen_per_hour(), 2)
    if per_hour_tot != chosen_tot:
      plog("ERROR", self.nickname+" has mismatch of per hour counts: "
                    +str(per_hour_tot) +" vs "+str(chosen_tot))


# TODO: Use __metaclass__ and type to make this inheritance flexible?
class StatsHandler(PathSupport.PathBuilder):
  """An extension of PathSupport.PathBuilder that keeps track of 
     router statistics for every circuit and stream"""
  def __init__(self, c, slmgr, RouterClass=StatsRouter, track_ranks=False):
    PathBuilder.__init__(self, c, slmgr, RouterClass)
    self.circ_count = 0
    self.strm_count = 0
    self.strm_failed = 0
    self.circ_failed = 0
    self.circ_succeeded = 0
    self.failed_reasons = {}
    self.suspect_reasons = {}
    self.track_ranks = track_ranks

  # XXX: Shit, all this stuff should be slice-based
  def run_zbtest(self): # Unweighted z-test
    """Run unweighted z-test to calculate the probabilities of a node
       having a given stream bandwidth based on the Normal distribution"""
    n = reduce(lambda x, y: x+(y.bwstats.mean > 0), self.sorted_r, 0)
    if n == 0: return (0, 0)
    avg = reduce(lambda x, y: x+y.bwstats.mean, self.sorted_r, 0)/float(n)
    def notlambda(x, y):
      if y.bwstats.mean <= 0: return x+0
      else: return x+(y.bwstats.mean-avg)*(y.bwstats.mean-avg)
    stddev = math.sqrt(reduce(notlambda, self.sorted_r, 0)/float(n))
    if not stddev: return (avg, stddev)
    for r in self.sorted_r:
      if r.bwstats.mean > 0:
        r.z_bw = abs((r.bwstats.mean-avg)/stddev)
        r.prob_zb = TorUtil.zprob(-r.z_bw)
    return (avg, stddev)

  def run_zrtest(self): # Unweighted z-test
    """Run unweighted z-test to calculate the probabilities of a node
       having a given ratio of stream bandwidth to advertised bandwidth
       based on the Normal distribution"""
    n = reduce(lambda x, y: x+(y.bw_ratio() > 0), self.sorted_r, 0)
    if n == 0: return (0, 0)
    avg = reduce(lambda x, y: x+y.bw_ratio(), self.sorted_r, 0)/float(n)
    def notlambda(x, y):
      if y.bw_ratio() <= 0: return x+0
      else: return x+(y.bw_ratio()-avg)*(y.bw_ratio()-avg)
    stddev = math.sqrt(reduce(notlambda, self.sorted_r, 0)/float(n))
    if not stddev: return (avg, stddev)
    for r in self.sorted_r:
      if r.bw_ratio() > 0:
        r.z_ratio = abs((r.bw_ratio()-avg)/stddev)
        r.prob_zr = TorUtil.zprob(-r.z_ratio)
    return (avg, stddev)

  def avg_adv_bw(self):
    n = reduce(lambda x, y: x+y.was_used(), self.sorted_r, 0)
    if n == 0: return (0, 0)
    avg = reduce(lambda x, y: x+y.bw, 
            filter(lambda r: r.was_used(), self.sorted_r), 0)/float(n)
    return avg 

  def avg_circ_failure(self):
    n = reduce(lambda x, y: x+y.was_used(), self.sorted_r, 0)
    if n == 0: return (0, 0)
    avg = reduce(lambda x, y: x+y.circ_fail_rate(), 
            filter(lambda r: r.was_used(), self.sorted_r), 0)/float(n)
    return avg 

  def avg_stream_failure(self):
    n = reduce(lambda x, y: x+y.was_used(), self.sorted_r, 0)
    if n == 0: return (0, 0)
    avg = reduce(lambda x, y: x+y.strm_fail_rate(), 
            filter(lambda r: r.was_used(), self.sorted_r), 0)/float(n)
    return avg 

  def avg_circ_suspects(self):
    n = reduce(lambda x, y: x+y.was_used(), self.sorted_r, 0)
    if n == 0: return (0, 0)
    avg = reduce(lambda x, y: x+y.circ_suspect_rate(), 
            filter(lambda r: r.was_used(), self.sorted_r), 0)/float(n)
    return avg 

  def avg_stream_suspects(self):
    n = reduce(lambda x, y: x+y.was_used(), self.sorted_r, 0)
    if n == 0: return (0, 0)
    avg = reduce(lambda x, y: x+y.strm_suspect_rate(), 
            filter(lambda r: r.was_used(), self.sorted_r), 0)/float(n)
    return avg 

  def write_reasons(self, f, reasons, name):
    "Write out all the failure reasons and statistics for all Routers"
    f.write("\n\n\t----------------- "+name+" -----------------\n")
    for rsn in reasons:
      f.write("\n"+rsn.reason+". Failed: "+str(rsn.total_failed())
          +", Suspected: "+str(rsn.total_suspected())+"\n")
      rsn.write_list(f)

  def write_routers(self, f, rlist, name):
    "Write out all the usage statistics for all Routers"
    f.write("\n\n\t----------------- "+name+" -----------------\n\n")
    for r in rlist:
      # only print it if we've used it.
      if r.circ_chosen+r.strm_chosen > 0: f.write(str(r))

  # FIXME: Maybe move this two up into StatsRouter too?
  ratio_key = """Metatroller Ratio Statistics:
  SR=Stream avg ratio     AR=Advertised bw ratio    BRR=Adv. bw avg ratio
  CSR=Circ suspect ratio  CFR=Circ Fail Ratio       SSR=Stream suspect ratio
  SFR=Stream fail ratio   CC=Circuit Count          SC=Stream Count
  P=Percentile Rank       U=Uptime (h)\n"""
  
  def write_ratios(self, filename):
    "Write out bandwith ratio stats StatsHandler has gathered"
    plog("DEBUG", "Writing ratios to "+filename)
    f = file(filename, "w")
    f.write(StatsHandler.ratio_key)

    (avg, dev) = self.run_zbtest()
    StatsRouter.global_strm_mean = avg
    StatsRouter.global_strm_dev = dev
    (avg, dev) = self.run_zrtest()
    StatsRouter.global_ratio_mean = avg
    StatsRouter.global_ratio_dev = dev

    StatsRouter.global_bw_mean = self.avg_adv_bw()

    StatsRouter.global_cf_mean = self.avg_circ_failure()
    StatsRouter.global_sf_mean = self.avg_stream_failure()
    
    StatsRouter.global_cs_mean = self.avg_circ_suspects()
    StatsRouter.global_ss_mean = self.avg_stream_suspects()

    strm_bw_ratio = copy.copy(self.sorted_r)
    strm_bw_ratio.sort(lambda x, y: cmp(x.strm_bw_ratio(), y.strm_bw_ratio()))
    for r in strm_bw_ratio:
      if r.circ_chosen == 0: continue
      f.write(r.idhex+"="+r.nickname+"\n  ")
      f.write("SR="+str(round(r.strm_bw_ratio(),4))+" AR="+str(round(r.adv_ratio(), 4))+" BRR="+str(round(r.bw_ratio_ratio(),4))+" CSR="+str(round(r.circ_suspect_ratio(),4))+" CFR="+str(round(r.circ_fail_ratio(),4))+" SSR="+str(round(r.strm_suspect_ratio(),4))+" SFR="+str(round(r.strm_fail_ratio(),4))+" CC="+str(r.circ_chosen)+" SC="+str(r.strm_chosen)+" U="+str(round(r.current_uptime()/3600,1))+" P="+str(round((100.0*r.avg_rank())/len(self.sorted_r),1))+"\n")
    f.close()
 
  def write_stats(self, filename):
    "Write out all the statistics the StatsHandler has gathered"
    # TODO: all this shit should be configurable. Some of it only makes
    # sense when scanning in certain modes.
    plog("DEBUG", "Writing stats to "+filename)
    # Sanity check routers
    for r in self.sorted_r: r.sanity_check()

    # Sanity check the router reason lists.
    for r in self.sorted_r:
      for rsn in r.reason_failed:
        if rsn not in self.failed_reasons:
          plog("ERROR", "Router "+r.idhex+" w/o reason "+rsn+" in fail table")
        elif r not in self.failed_reasons[rsn].rlist:
          plog("ERROR", "Router "+r.idhex+" missing from fail table")
      for rsn in r.reason_suspected:
        if rsn not in self.suspect_reasons:
          plog("ERROR", "Router "+r.idhex+" w/o reason "+rsn+" in fail table") 
        elif r not in self.suspect_reasons[rsn].rlist:
          plog("ERROR", "Router "+r.idhex+" missing from suspect table")

    # Sanity check the lists the other way
    for rsn in self.failed_reasons.itervalues(): rsn._verify_failed()
    for rsn in self.suspect_reasons.itervalues(): rsn._verify_suspected()

    f = file(filename, "w")
    f.write(StatsRouter.key)
    (avg, dev) = self.run_zbtest()
    StatsRouter.global_strm_mean = avg
    StatsRouter.global_strm_dev = dev
    f.write("\n\nBW stats: u="+str(round(avg,1))+" s="+str(round(dev,1))+"\n")

    (avg, dev) = self.run_zrtest()
    StatsRouter.global_ratio_mean = avg
    StatsRouter.global_ratio_dev = dev
    f.write("BW ratio stats: u="+str(round(avg,1))+" s="+str(round(dev,1))+"\n")


    # Circ, strm infoz
    f.write("Circ failure ratio: "+str(self.circ_failed)
            +"/"+str(self.circ_count)+"\n")

    f.write("Stream failure ratio: "+str(self.strm_failed)
            +"/"+str(self.strm_count)+"\n")

    # Extend times 
    n = 0.01+reduce(lambda x, y: x+(y.avg_extend_time() > 0), self.sorted_r, 0)
    avg_extend = reduce(lambda x, y: x+y.avg_extend_time(), self.sorted_r, 0)/n
    def notlambda(x, y):
      return x+(y.avg_extend_time()-avg_extend)*(y.avg_extend_time()-avg_extend) 
    dev_extend = math.sqrt(reduce(notlambda, self.sorted_r, 0)/float(n))

    f.write("Extend time: u="+str(round(avg_extend,1))
             +" s="+str(round(dev_extend,1)))
    
    # sort+print by bandwidth
    strm_bw_ratio = copy.copy(self.sorted_r)
    strm_bw_ratio.sort(lambda x, y: cmp(x.strm_bw_ratio(), y.strm_bw_ratio()))
    self.write_routers(f, strm_bw_ratio, "Stream Ratios")

    # sort+print by bandwidth
    bw_rate = copy.copy(self.sorted_r)
    bw_rate.sort(lambda x, y: cmp(y.bw_ratio(), x.bw_ratio()))
    self.write_routers(f, bw_rate, "Bandwidth Ratios")

    failed = copy.copy(self.sorted_r)
    failed.sort(lambda x, y:
          cmp(y.circ_failed+y.strm_failed,
            x.circ_failed+x.strm_failed))
    self.write_routers(f, failed, "Failed Counts")

    suspected = copy.copy(self.sorted_r)
    suspected.sort(lambda x, y: # Suspected includes failed
       cmp(y.circ_failed+y.strm_failed+y.circ_suspected+y.strm_suspected,
         x.circ_failed+x.strm_failed+x.circ_suspected+x.strm_suspected))
    self.write_routers(f, suspected, "Suspected Counts")

    fail_rate = copy.copy(failed)
    fail_rate.sort(lambda x, y: cmp(y.failed_per_hour(), x.failed_per_hour()))
    self.write_routers(f, fail_rate, "Fail Rates")

    suspect_rate = copy.copy(suspected)
    suspect_rate.sort(lambda x, y:
       cmp(y.suspected_per_hour(), x.suspected_per_hour()))
    self.write_routers(f, suspect_rate, "Suspect Rates")
    
    # TODO: Sort by failed/selected and suspect/selected ratios
    # if we ever want to do non-uniform scanning..

    # FIXME: Add failed in here somehow..
    susp_reasons = self.suspect_reasons.values()
    susp_reasons.sort(lambda x, y:
       cmp(y.total_suspected(), x.total_suspected()))
    self.write_reasons(f, susp_reasons, "Suspect Reasons")

    fail_reasons = self.failed_reasons.values()
    fail_reasons.sort(lambda x, y:
       cmp(y.total_failed(), x.total_failed()))
    self.write_reasons(f, fail_reasons, "Failed Reasons")
    f.close()

    # FIXME: sort+print by circ extend time

  def reset(self):
    PathSupport.PathBuilder.reset(self)
    self.reset_stats()

  def reset_stats(self):
    plog("DEBUG", "Resetting stats")
    self.circ_count = 0
    self.strm_count = 0
    self.strm_failed = 0
    self.circ_succeeded = 0
    self.circ_failed = 0
    self.suspect_reasons.clear()
    self.failed_reasons.clear()
    for r in self.routers.itervalues(): r.reset()

  def close_circuit(self, id):
    PathSupport.PathBuilder.close_circuit(self, id)
    # Shortcut so we don't have to wait for the CLOSE
    # events for stats update.
    self.circ_succeeded += 1
    for r in self.circuits[id].path:
      r.circ_chosen += 1
      r.circ_succeeded += 1

  def circ_status_event(self, c):
    if c.circ_id in self.circuits:
      # TODO: Hrmm, consider making this sane in TorCtl.
      if c.reason: lreason = c.reason
      else: lreason = "NONE"
      if c.remote_reason: rreason = c.remote_reason
      else: rreason = "NONE"
      reason = c.event_name+":"+c.status+":"+lreason+":"+rreason
      if c.status == "LAUNCHED":
        # Update circ_chosen count
        self.circ_count += 1
      elif c.status == "EXTENDED":
        delta = c.arrived_at - self.circuits[c.circ_id].last_extended_at
        r_ext = c.path[-1]
        try:
          if r_ext[0] != '$': r_ext = self.name_to_key[r_ext]
          self.routers[r_ext[1:]].total_extend_time += delta
          self.routers[r_ext[1:]].total_extended += 1
        except KeyError, e:
          traceback.print_exc()
          plog("WARN", "No key "+str(e)+" for "+r_ext+" in dict:"+str(self.name_to_key))
      elif c.status == "FAILED":
        for r in self.circuits[c.circ_id].path: r.circ_chosen += 1
        
        if len(c.path)-1 < 0: start_f = 0
        else: start_f = len(c.path)-1 

        # Count failed
        self.circ_failed += 1
        # XXX: Differentiate between extender and extendee
        for r in self.circuits[c.circ_id].path[start_f:len(c.path)+1]:
          r.circ_failed += 1
          if not reason in r.reason_failed:
            r.reason_failed[reason] = 1
          else: r.reason_failed[reason]+=1
          if reason not in self.failed_reasons:
             self.failed_reasons[reason] = FailedRouterList(reason)
          self.failed_reasons[reason].add_r(r)

        for r in self.circuits[c.circ_id].path[len(c.path)+1:]:
          r.circ_uncounted += 1

        # Don't count if failed was set this round, don't set 
        # suspected..
        for r in self.circuits[c.circ_id].path[:start_f]:
          r.circ_suspected += 1
          if not reason in r.reason_suspected:
            r.reason_suspected[reason] = 1
          else: r.reason_suspected[reason]+=1
          if reason not in self.suspect_reasons:
             self.suspect_reasons[reason] = SuspectRouterList(reason)
          self.suspect_reasons[reason].add_r(r)
      elif c.status == "CLOSED":
        # Since PathBuilder deletes the circuit on a failed, 
        # we only get this for a clean close that was not
        # requested by us.

        # Don't count circuits we requested closed from
        # pathbuilder, they are counted there instead.
        if not self.circuits[c.circ_id].requested_closed:
          self.circ_succeeded += 1
          for r in self.circuits[c.circ_id].path:
            r.circ_chosen += 1
            if lreason in ("REQUESTED", "FINISHED", "ORIGIN"):
              r.circ_succeeded += 1
            else:
              if not reason in r.reason_suspected:
                r.reason_suspected[reason] = 1
              else: r.reason_suspected[reason] += 1
              r.circ_suspected+= 1
              if reason not in self.suspect_reasons:
                self.suspect_reasons[reason] = SuspectRouterList(reason)
              self.suspect_reasons[reason].add_r(r)
    PathBuilder.circ_status_event(self, c)

  def count_stream_reason_failed(self, s, reason):
    "Count the routers involved in a failure"
    # Update failed count,reason_failed for exit
    r = self.circuits[s.circ_id].exit
    if not reason in r.reason_failed: r.reason_failed[reason] = 1
    else: r.reason_failed[reason]+=1
    r.strm_failed += 1
    if reason not in self.failed_reasons:
      self.failed_reasons[reason] = FailedRouterList(reason)
    self.failed_reasons[reason].add_r(r)

  def count_stream_suspects(self, s, lreason, reason):
    "Count the routers 'suspected' of being involved in a failure"
    if lreason in ("TIMEOUT", "INTERNAL", "TORPROTOCOL" "DESTROY"):
      for r in self.circuits[s.circ_id].path[:-1]:
        r.strm_suspected += 1
        if not reason in r.reason_suspected:
          r.reason_suspected[reason] = 1
        else: r.reason_suspected[reason]+=1
        if reason not in self.suspect_reasons:
          self.suspect_reasons[reason] = SuspectRouterList(reason)
        self.suspect_reasons[reason].add_r(r)
    else:
      for r in self.circuits[s.circ_id].path[:-1]:
        r.strm_uncounted += 1
  
  def stream_status_event(self, s):
    if s.strm_id in self.streams and not self.streams[s.strm_id].ignored:
      # TODO: Hrmm, consider making this sane in TorCtl.
      if s.reason: lreason = s.reason
      else: lreason = "NONE"
      if s.remote_reason: rreason = s.remote_reason
      else: rreason = "NONE"
      reason = s.event_name+":"+s.status+":"+lreason+":"+rreason+":"+self.streams[s.strm_id].kind
      circ = self.streams[s.strm_id].circ
      if not circ: circ = self.streams[s.strm_id].pending_circ
      if (s.status in ("DETACHED", "FAILED", "CLOSED", "SUCCEEDED")
          and not s.circ_id):
        # XXX: REMAPs can do this (normal). Also REASON=DESTROY (bug?)
        if circ:
          plog("INFO", "Stream "+s.status+" of "+str(s.strm_id)+" gave circ 0.  Resetting to stored circ id: "+str(circ.circ_id))
          s.circ_id = circ.circ_id
        #elif s.reason == "TIMEOUT" or s.reason == "EXITPOLICY":
        #  plog("NOTICE", "Stream "+str(s.strm_id)+" detached with "+s.reason)
        else:
          plog("WARN", "Stream "+str(s.strm_id)+" detached from no known circuit with reason: "+str(s.reason))
          PathBuilder.stream_status_event(self, s)
          return

      # Verify circ id matches stream.circ
      if s.status not in ("NEW", "NEWRESOLVE", "REMAP"):
        if s.circ_id and circ and circ.circ_id != s.circ_id:
          plog("WARN", str(s.strm_id) + " has mismatch of "
                +str(s.circ_id)+" v "+str(circ.circ_id))
        if s.circ_id and s.circ_id not in self.circuits:
          plog("NOTICE", "Unknown circuit "+str(s.circ_id)
                +" for stream "+str(s.strm_id))
          PathBuilder.stream_status_event(self, s)
          return
      
      if s.status == "DETACHED":
        if self.streams[s.strm_id].attached_at:
          plog("WARN", str(s.strm_id)+" detached after succeeded")
        # Update strm_chosen count
        self.strm_count += 1
        for r in self.circuits[s.circ_id].path: r.strm_chosen += 1
        self.strm_failed += 1
        self.count_stream_suspects(s, lreason, reason)
        self.count_stream_reason_failed(s, reason)
      elif s.status == "FAILED":
        # HACK. We get both failed and closed for the same stream,
        # with different reasons. Might as well record both, since they 
        # often differ.
        self.streams[s.strm_id].failed_reason = reason
      elif s.status == "CLOSED":
        # Always get both a closed and a failed.. 
        #   - Check if the circuit exists still
        # Update strm_chosen count
        self.strm_count += 1
        for r in self.circuits[s.circ_id].path: r.strm_chosen += 1

        if self.streams[s.strm_id].failed:
          reason = self.streams[s.strm_id].failed_reason+":"+lreason+":"+rreason

        self.count_stream_suspects(s, lreason, reason)
          
        r = self.circuits[s.circ_id].exit
        if (not self.streams[s.strm_id].failed
          and (lreason == "DONE" or (lreason == "END" and rreason == "DONE"))):
          r.strm_succeeded += 1

          # Update bw stats. XXX: Don't do this for resolve streams
          if self.streams[s.strm_id].attached_at:
            lifespan = self.streams[s.strm_id].lifespan(s.arrived_at)
            for r in self.streams[s.strm_id].circ.path:
              r.bwstats.add_bw(self.streams[s.strm_id].bytes_written+
                               self.streams[s.strm_id].bytes_read, lifespan)
  
        else:
          self.strm_failed += 1
          self.count_stream_reason_failed(s, reason)
    PathBuilder.stream_status_event(self, s)

  def _check_hibernation(self, r, now):
    if r.down:
      if not r.hibernated_at:
        r.hibernated_at = now
        r.total_active_uptime += now - r.became_active_at
      r.became_active_at = 0
    else:
      if not r.became_active_at:
        r.became_active_at = now
        r.total_hibernation_time += now - r.hibernated_at
      r.hibernated_at = 0

  def new_consensus_event(self, n):
    if self.track_ranks:
      # Record previous rank and history.
      for ns in n.nslist:
        if not ns.idhex in self.routers:
          continue
        r = self.routers[ns.idhex]
        r.bw_history.append(r.bw)
      for r in self.sorted_r:
        r.rank_history.append(r.list_rank)
    PathBuilder.new_consensus_event(self, n)
    now = n.arrived_at
    for ns in n.nslist:
      if not ns.idhex in self.routers: continue
      self._check_hibernation(self.routers[ns.idhex], now)

  def new_desc_event(self, d):
    if PathBuilder.new_desc_event(self, d):
      now = d.arrived_at
      for i in d.idlist:
        if not i in self.routers: continue
        self._check_hibernation(self.routers[i], now)
      
   

########NEW FILE########
__FILENAME__ = TorCtl
#!/usr/bin/python
# TorCtl.py -- Python module to interface with Tor Control interface.
# Copyright 2005 Nick Mathewson
# Copyright 2007-2010 Mike Perry. See LICENSE file.

"""
Library to control Tor processes.

This library handles sending commands, parsing responses, and delivering
events to and from the control port. The basic usage is to create a
socket, wrap that in a TorCtl.Connection, and then add an EventHandler
to that connection. For a simple example that prints our BW events (events
that provide the amount of traffic going over tor) see 'example.py'.

Note that the TorCtl.Connection is fully compatible with the more
advanced EventHandlers in TorCtl.PathSupport (and of course any other
custom event handlers that you may extend off of those).

This package also contains a helper class for representing Routers, and
classes and constants for each event.
 
To quickly fetch a TorCtl instance to experiment with use the following:

>>> import TorCtl
>>> conn = TorCtl.connect()
>>> conn.get_info("version")["version"]
'0.2.1.24'

"""

__all__ = ["EVENT_TYPE", "connect", "TorCtlError", "TorCtlClosed",
           "ProtocolError", "ErrorReply", "NetworkStatus", "ExitPolicyLine",
           "Router", "RouterVersion", "Connection", "parse_ns_body",
           "EventHandler", "DebugEventHandler", "NetworkStatusEvent",
           "NewDescEvent", "CircuitEvent", "StreamEvent", "ORConnEvent",
           "StreamBwEvent", "LogEvent", "AddrMapEvent", "BWEvent",
           "BuildTimeoutSetEvent", "UnknownEvent", "ConsensusTracker",
           "EventListener", "EVENT_STATE", "ns_body_iter",
           "preauth_connect" ]

import os
import re
import struct
import sys
import threading
import Queue
import datetime
import traceback
import socket
import getpass
import binascii
import types
import time
import copy

from TorUtil import *

if sys.version_info < (2, 5):
  from sets import Set as set
  from sha import sha as sha1
else:
  from hashlib import sha1

# Types of "EVENT" message.
EVENT_TYPE = Enum2(
          CIRC="CIRC",
          STREAM="STREAM",
          ORCONN="ORCONN",
          STREAM_BW="STREAM_BW",
          BW="BW",
          NS="NS",
          NEWCONSENSUS="NEWCONSENSUS",
          BUILDTIMEOUT_SET="BUILDTIMEOUT_SET",
          GUARD="GUARD",
          NEWDESC="NEWDESC",
          ADDRMAP="ADDRMAP",
          DEBUG="DEBUG",
          INFO="INFO",
          NOTICE="NOTICE",
          WARN="WARN",
          ERR="ERR")

EVENT_STATE = Enum2(
          PRISTINE="PRISTINE",
          PRELISTEN="PRELISTEN",
          HEARTBEAT="HEARTBEAT",
          HANDLING="HANDLING",
          POSTLISTEN="POSTLISTEN",
          DONE="DONE")

# Types of control port authentication
AUTH_TYPE = Enum2(
          NONE="NONE",
          PASSWORD="PASSWORD",
          COOKIE="COOKIE")

INCORRECT_PASSWORD_MSG = "Provided passphrase was incorrect"


class TorCtlError(Exception):
  "Generic error raised by TorControl code."
  pass

class TorCtlClosed(TorCtlError):
  "Raised when the controller connection is closed by Tor (not by us.)"
  pass

class ProtocolError(TorCtlError):
  "Raised on violations in Tor controller protocol"
  pass

class ErrorReply(TorCtlError):
  "Raised when Tor controller returns an error"
  def __init__(self, *args, **kwargs):
    if "status" in kwargs:
      self.status = kwargs.pop("status")
    if "message" in kwargs:
      self.message = kwargs.pop("message")
    TorCtlError.__init__(self, *args, **kwargs)

class NetworkStatus:
  "Filled in during NS events"
  def __init__(self, nickname, idhash, orhash, updated, ip, orport, dirport, flags, bandwidth=None):
    self.nickname = nickname
    self.idhash = idhash
    self.orhash = orhash
    self.ip = ip
    self.orport = int(orport)
    self.dirport = int(dirport)
    self.flags = flags
    self.idhex = (self.idhash + "=").decode("base64").encode("hex").upper()
    self.bandwidth = bandwidth
    m = re.search(r"(\d+)-(\d+)-(\d+) (\d+):(\d+):(\d+)", updated)
    self.updated = datetime.datetime(*map(int, m.groups()))

class Event:
  def __init__(self, event_name, body=None):
    self.body = body
    self.event_name = event_name
    self.arrived_at = 0
    self.state = EVENT_STATE.PRISTINE

class TimerEvent(Event):
  def __init__(self, event_name, body):
    Event.__init__(self, event_name, body)
    self.type = body

class NetworkStatusEvent(Event):
  def __init__(self, event_name, nslist, body):
    Event.__init__(self, event_name, body)
    self.nslist = nslist # List of NetworkStatus objects

class NewConsensusEvent(NetworkStatusEvent):
  pass

class NewDescEvent(Event):
  def __init__(self, event_name, idlist, body):
    Event.__init__(self, event_name, body)
    self.idlist = idlist

class GuardEvent(Event):
  def __init__(self, event_name, ev_type, guard, status, body):
    Event.__init__(self, event_name, body)
    if "~" in guard:
      (self.idhex, self.nick) = guard[1:].split("~")
    elif "=" in guard:
      (self.idhex, self.nick) = guard[1:].split("=")
    else:
      self.idhex = guard[1:]
    self.status = status

class BuildTimeoutSetEvent(Event):
  def __init__(self, event_name, set_type, total_times, timeout_ms, xm, alpha,
               quantile, body):
    Event.__init__(self, event_name, body)
    self.set_type = set_type
    self.total_times = total_times
    self.timeout_ms = timeout_ms
    self.xm = xm
    self.alpha = alpha
    self.cutoff_quantile = quantile

class CircuitEvent(Event):
  def __init__(self, event_name, circ_id, status, path, purpose,
         reason, remote_reason, body):
    Event.__init__(self, event_name, body)
    self.circ_id = circ_id
    self.status = status
    self.path = path
    self.purpose = purpose
    self.reason = reason
    self.remote_reason = remote_reason

class StreamEvent(Event):
  def __init__(self, event_name, strm_id, status, circ_id, target_host,
         target_port, reason, remote_reason, source, source_addr, purpose,
         body):
    Event.__init__(self, event_name, body)
    self.strm_id = strm_id
    self.status = status
    self.circ_id = circ_id
    self.target_host = target_host
    self.target_port = int(target_port)
    self.reason = reason
    self.remote_reason = remote_reason
    self.source = source
    self.source_addr = source_addr
    self.purpose = purpose

class ORConnEvent(Event):
  def __init__(self, event_name, status, endpoint, age, read_bytes,
         wrote_bytes, reason, ncircs, body):
    Event.__init__(self, event_name, body)
    self.status = status
    self.endpoint = endpoint
    self.age = age
    self.read_bytes = read_bytes
    self.wrote_bytes = wrote_bytes
    self.reason = reason
    self.ncircs = ncircs

class StreamBwEvent(Event):
  def __init__(self, event_name, saved_body, strm_id, written, read):
    Event.__init__(self, event_name, saved_body)
    self.strm_id = int(strm_id)
    self.bytes_read = int(read)
    self.bytes_written = int(written)

class LogEvent(Event):
  def __init__(self, level, msg):
    Event.__init__(self, level, msg)
    self.level = level
    self.msg = msg

class AddrMapEvent(Event):
  def __init__(self, event_name, from_addr, to_addr, when, body):
    Event.__init__(self, event_name, body)
    self.from_addr = from_addr
    self.to_addr = to_addr
    self.when = when

class AddrMap:
  def __init__(self, from_addr, to_addr, when):
    self.from_addr = from_addr
    self.to_addr = to_addr
    self.when = when

class BWEvent(Event):
  def __init__(self, event_name, read, written, body):
    Event.__init__(self, event_name, body)
    self.read = read
    self.written = written

class UnknownEvent(Event):
  def __init__(self, event_name, event_string):
    Event.__init__(self, event_name, event_string)
    self.event_string = event_string

ipaddress_re = re.compile(r"(\d{1,3}\.){3}\d{1,3}$")
class ExitPolicyLine:
  """ Class to represent a line in a Router's exit policy in a way 
      that can be easily checked. """
  def __init__(self, match, ip_mask, port_low, port_high):
    self.match = match
    if ip_mask == "*":
      self.ip = 0
      self.netmask = 0
    else:
      if not "/" in ip_mask:
        self.netmask = 0xFFFFFFFF
        ip = ip_mask
      else:
        ip, mask = ip_mask.split("/")
        if ipaddress_re.match(mask):
          self.netmask=struct.unpack(">I", socket.inet_aton(mask))[0]
        else:
          self.netmask = 0xffffffff ^ (0xffffffff >> int(mask))
      self.ip = struct.unpack(">I", socket.inet_aton(ip))[0]
    self.ip &= self.netmask
    if port_low == "*":
      self.port_low,self.port_high = (0,65535)
    else:
      if not port_high:
        port_high = port_low
      self.port_low = int(port_low)
      self.port_high = int(port_high)
  
  def check(self, ip, port):
    """Check to see if an ip and port is matched by this line. 
     Returns true if the line is an Accept, and False if it is a Reject. """
    ip = struct.unpack(">I", socket.inet_aton(ip))[0]
    if (ip & self.netmask) == self.ip:
      if self.port_low <= port and port <= self.port_high:
        return self.match
    return -1

  def __str__(self):
    retr = ""
    if self.match:
      retr += "accept "
    else:
      retr += "reject "
    retr += socket.inet_ntoa(struct.pack(">I",self.ip)) + "/"
    retr += socket.inet_ntoa(struct.pack(">I",self.netmask)) + ":"
    retr += str(self.port_low)+"-"+str(self.port_high)
    return retr

class RouterVersion:
  """ Represents a Router's version. Overloads all comparison operators
      to check for newer, older, or equivalent versions. """
  def __init__(self, version):
    if version:
      v = re.search("^(\d+)\.(\d+)\.(\d+)\.(\d+)", version).groups()
      self.version = int(v[0])*0x1000000 + int(v[1])*0x10000 + int(v[2])*0x100 + int(v[3])
      self.ver_string = version
    else: 
      self.version = version
      self.ver_string = "unknown"

  def __lt__(self, other): return self.version < other.version
  def __gt__(self, other): return self.version > other.version
  def __ge__(self, other): return self.version >= other.version
  def __le__(self, other): return self.version <= other.version
  def __eq__(self, other): return self.version == other.version
  def __ne__(self, other): return self.version != other.version
  def __str__(self): return self.ver_string


# map descriptor keywords to regular expressions.
desc_re = {
  "router":          r"(\S+) (\S+)",
  "opt fingerprint": r"(.+).*on (\S+)",
  "opt extra-info-digest": r"(\S+)",
  "opt hibernating": r"1$",
  "platform":  r"Tor (\S+).*on ([\S\s]+)",
  "accept":    r"(\S+):([^-]+)(?:-(\d+))?",
  "reject":    r"(\S+):([^-]+)(?:-(\d+))?",
  "bandwidth": r"(\d+) \d+ (\d+)",
  "uptime":    r"(\d+)",
  "contact":   r"(.+)",
  "published": r"(\S+ \S+)",
}
# Compile each regular expression now.
for kw, reg in desc_re.iteritems():
  desc_re[kw] = re.compile(reg)

def partition(string, delimiter):
  """ Implementation of string.partition-like function for Python <
  2.5.  Returns a tuple (first, rest), where first is the text up to
  the first delimiter, and rest is the text after the first delimiter.
  """
  sp = string.split(delimiter, 1)
  if len(sp) > 1:
    return sp[0], sp[1]
  else:
    return sp[0], ""

class Router:
  """ 
  Class to represent a router from a descriptor. Can either be
  created from the parsed fields, or can be built from a
  descriptor+NetworkStatus 
  """     
  def __init__(self, *args):
    if len(args) == 1:
      for i in args[0].__dict__:
        self.__dict__[i] =  copy.deepcopy(args[0].__dict__[i])
      return
    else:
      (idhex, name, bw, down, exitpolicy, flags, ip, version, os, uptime,
       published, contact, rate_limited, orhash,
       ns_bandwidth,extra_info_digest) = args
    self.idhex = idhex
    self.nickname = name
    if ns_bandwidth != None:
      self.bw = ns_bandwidth
    else:
     self.bw = bw
    self.desc_bw = bw
    self.exitpolicy = exitpolicy
    self.flags = flags # Technicaly from NS doc
    self.down = down
    self.ip = struct.unpack(">I", socket.inet_aton(ip))[0]
    self.version = RouterVersion(version)
    self.os = os
    self.list_rank = 0 # position in a sorted list of routers.
    self.ratio_rank = 0 # position in a ratio-sorted list of routers
    self.uptime = uptime
    self.published = published
    self.refcount = 0 # How many open circs are we currently in?
    self.deleted = False # Has Tor already deleted this descriptor?
    self.contact = contact
    self.rate_limited = rate_limited
    self.orhash = orhash
    self.extra_info_digest = extra_info_digest
    self._generated = [] # For ExactUniformGenerator

  def __str__(self):
    s = self.idhex, self.nickname
    return s.__str__()

  def build_from_desc(desc, ns):
    """
    Static method of Router that parses a descriptor string into this class.
    'desc' is a full descriptor as a string. 
    'ns' is a TorCtl.NetworkStatus instance for this router (needed for
    the flags, the nickname, and the idhex string). 
    Returns a Router instance.
    """
    exitpolicy = []
    dead = not ("Running" in ns.flags)
    bw_observed = 0
    version = None
    os = None
    uptime = 0
    ip = 0
    router = "[none]"
    published = "never"
    contact = None
    extra_info_digest = None

    for line in desc:
      # Pull off the keyword...
      kw, rest = partition(line, " ")

      # ...and if it's "opt", extend it by the next keyword
      # so we get "opt hibernating" as one keyword.
      if kw == "opt":
        okw, rest = partition(rest, " ")
        kw += " " + okw

      # try to match the descriptor line by keyword.
      try:
        match = desc_re[kw].match(rest)
      # if we don't handle this keyword, just move on to the next one.
      except KeyError:
        continue
      # if we do handle this keyword but its data is malformed,
      # move on to the next one without processing it.
      if not match:
        continue

      g = match.groups()

      # Handle each keyword individually.
      # TODO: This could possibly be sped up since we technically already
      # did the compare with the dictionary lookup... lambda magic time.
      if kw == "accept":
        exitpolicy.append(ExitPolicyLine(True, *g))
      elif kw == "reject":
        exitpolicy.append(ExitPolicyLine(False, *g))
      elif kw == "router":
        router,ip = g
      elif kw == "bandwidth":
        bws = map(int, g)
        bw_observed = min(bws)
        rate_limited = False
        if bws[0] < bws[1]:
          rate_limited = True
      elif kw == "platform":
        version, os = g
      elif kw == "uptime":
        uptime = int(g[0])
      elif kw == "published":
        t = time.strptime(g[0] + " UTC", "20%y-%m-%d %H:%M:%S %Z")
        published = datetime.datetime(*t[0:6])
      elif kw == "contact":
        contact = g[0]
      elif kw == "opt extra-info-digest":
        extra_info_digest = g[0]
      elif kw == "opt hibernating":
        dead = True 
        if ("Running" in ns.flags):
          plog("INFO", "Hibernating router "+ns.nickname+" is running, flags: "+" ".join(ns.flags))

    if router != ns.nickname:
      plog("INFO", "Got different names " + ns.nickname + " vs " +
             router + " for " + ns.idhex)
    if not bw_observed and not dead and ("Valid" in ns.flags):
      plog("INFO", "No bandwidth for live router "+ns.nickname+", flags: "+" ".join(ns.flags))
      dead = True
    if not version or not os:
      plog("INFO", "No version and/or OS for router " + ns.nickname)
    return Router(ns.idhex, ns.nickname, bw_observed, dead, exitpolicy,
        ns.flags, ip, version, os, uptime, published, contact, rate_limited,
        ns.orhash, ns.bandwidth, extra_info_digest)
  build_from_desc = Callable(build_from_desc)

  def update_to(self, new):
    """ Somewhat hackish method to update this router to be a copy of
    'new' """
    if self.idhex != new.idhex:
      plog("ERROR", "Update of router "+self.nickname+"changes idhex!")
    for i in new.__dict__.iterkeys():
      if i == "refcount" or i == "_generated": continue
      self.__dict__[i] = new.__dict__[i]

  def will_exit_to(self, ip, port):
    """ Check the entire exitpolicy to see if the router will allow
        connections to 'ip':'port' """
    for line in self.exitpolicy:
      ret = line.check(ip, port)
      if ret != -1:
        return ret
    plog("WARN", "No matching exit line for "+self.nickname)
    return False
   
class Connection:
  """A Connection represents a connection to the Tor process via the 
     control port."""
  def __init__(self, sock):
    """Create a Connection to communicate with the Tor process over the
       socket 'sock'.
    """
    self._handler = None
    self._handleFn = None
    self._sendLock = threading.RLock()
    self._queue = Queue.Queue()
    self._thread = None
    self._closedEx = None
    self._closed = 0
    self._closeHandler = None
    self._eventThread = None
    self._eventQueue = Queue.Queue()
    self._s = BufSock(sock)
    self._debugFile = None
    
    # authentication information (lazily fetched so None if still unknown)
    self._authType = None
    self._cookiePath = None

  def get_auth_type(self):
    """
    Provides the authentication type used for the control port (a member of
    the AUTH_TYPE enumeration). This raises an IOError if this fails to query
    the PROTOCOLINFO.
    """
    
    if self._authType: return self._authType
    else:
      # check PROTOCOLINFO for authentication type
      try:
        authInfo = self.sendAndRecv("PROTOCOLINFO\r\n")[1][1]
      except Exception, exc:
        if exc.message: excMsg = ": %s" % exc
        else: excMsg = ""
        raise IOError("Unable to query PROTOCOLINFO for the authentication type%s" % excMsg)
      
      authType, cookiePath = None, None
      if authInfo.startswith("AUTH METHODS=NULL"):
        # no authentication required
        authType = AUTH_TYPE.NONE
      elif authInfo.startswith("AUTH METHODS=HASHEDPASSWORD"):
        # password authentication
        authType = AUTH_TYPE.PASSWORD
      elif authInfo.startswith("AUTH METHODS=COOKIE"):
        # cookie authentication, parses authentication cookie path
        authType = AUTH_TYPE.COOKIE
        
        start = authInfo.find("COOKIEFILE=\"") + 12
        end = authInfo.find("\"", start)
        cookiePath = authInfo[start:end]
      else:
        # not of a recognized authentication type (new addition to the
        # control-spec?)
        raise IOError("Unrecognized authentication type: %s" % authInfo)
      
      self._authType = authType
      self._cookiePath = cookiePath
      return self._authType
  
  def get_auth_cookie_path(self):
    """
    Provides the path of tor's authentication cookie. If the connection isn't
    using cookie authentication then this provides None. This raises an IOError
    if PROTOCOLINFO can't be queried.
    """
    
    # fetches authentication type and cookie path if still unloaded
    if self._authType == None: self.get_auth_type()
    
    if self._authType == AUTH_TYPE.COOKIE:
      return self._cookiePath
    else:
      return None
  
  def set_close_handler(self, handler):
    """Call 'handler' when the Tor process has closed its connection or
       given us an exception.  If we close normally, no arguments are
       provided; otherwise, it will be called with an exception as its
       argument.
    """
    self._closeHandler = handler

  def close(self):
    """Shut down this controller connection"""
    self._sendLock.acquire()
    try:
      self._queue.put("CLOSE")
      self._eventQueue.put((time.time(), "CLOSE"))
      self._closed = 1
      self._s.close()
      self._thread.join()
      self._eventThread.join()
    finally:
      self._sendLock.release()

  def is_live(self):
    """ Returns true iff the connection is alive and healthy"""
    return self._thread.isAlive() and self._eventThread.isAlive() and not \
           self._closed

  def launch_thread(self, daemon=1):
    """Launch a background thread to handle messages from the Tor process."""
    assert self._thread is None
    t = threading.Thread(target=self._loop, name="TorLoop")
    if daemon:
      t.setDaemon(daemon)
    t.start()
    self._thread = t
    t = threading.Thread(target=self._eventLoop, name="EventLoop")
    if daemon:
      t.setDaemon(daemon)
    t.start()
    self._eventThread = t
    # eventThread provides a more reliable indication of when we are done.
    # The _loop thread won't always die when self.close() is called.
    return self._eventThread

  def _loop(self):
    """Main subthread loop: Read commands from Tor, and handle them either
       as events or as responses to other commands.
    """
    while 1:
      try:
        isEvent, reply = self._read_reply()
      except TorCtlClosed, exc:
        plog("NOTICE", "Tor closed control connection. Exiting event thread.")

        # notify anything blocking on a response of the error, for details see:
        # https://trac.torproject.org/projects/tor/ticket/1329
        try:
          self._closedEx = exc
          cb = self._queue.get(timeout=0)
          if cb != "CLOSE":
            cb("EXCEPTION")
        except Queue.Empty: pass

        return
      except Exception,e:
        if not self._closed:
          if sys:
            self._err(sys.exc_info())
          else:
            plog("NOTICE", "No sys left at exception shutdown: "+str(e))
            self._err((e.__class__, e, None))
          return
        else:
          isEvent = 0

      if isEvent:
        if self._handler is not None:
          self._eventQueue.put((time.time(), reply))
      else:
        cb = self._queue.get() # atomic..
        if cb == "CLOSE":
          self._s = None
          plog("INFO", "Closed control connection. Exiting thread.")
          return
        else:
          cb(reply)

  def _err(self, (tp, ex, tb), fromEventLoop=0):
    """DOCDOC"""
    # silent death is bad :(
    traceback.print_exception(tp, ex, tb)
    if self._s:
      try:
        self.close()
      except:
        pass
    self._sendLock.acquire()
    try:
      self._closedEx = ex
      self._closed = 1
    finally:
      self._sendLock.release()
    while 1:
      try:
        cb = self._queue.get(timeout=0)
        if cb != "CLOSE":
          cb("EXCEPTION")
      except Queue.Empty:
        break
    if self._closeHandler is not None:
      self._closeHandler(ex)
    # I hate you for making me resort to this, python
    os.kill(os.getpid(), 15)
    return

  def _eventLoop(self):
    """DOCDOC"""
    while 1:
      (timestamp, reply) = self._eventQueue.get()
      if reply[0][0] == "650" and reply[0][1] == "OK":
        plog("DEBUG", "Ignoring incompatible syntactic sugar: 650 OK")
        continue
      if reply == "CLOSE":
        plog("INFO", "Event loop received close message.")
        return
      try:
        self._handleFn(timestamp, reply)
      except:
        for code, msg, data in reply:
            plog("WARN", "No event for: "+str(code)+" "+str(msg))
        self._err(sys.exc_info(), 1)
        return

  def _sendImpl(self, sendFn, msg):
    """DOCDOC"""
    if self._thread is None and not self._closed:
      self.launch_thread(1)
    # This condition will get notified when we've got a result...
    condition = threading.Condition()
    # Here's where the result goes...
    result = []

    if self._closedEx is not None:
      raise self._closedEx
    elif self._closed:
      raise TorCtlClosed()

    def cb(reply,condition=condition,result=result):
      condition.acquire()
      try:
        result.append(reply)
        condition.notify()
      finally:
        condition.release()

    # Sends a message to Tor...
    self._sendLock.acquire() # ensure queue+sendmsg is atomic
    try:
      self._queue.put(cb)
      sendFn(msg) # _doSend(msg)
    finally:
      self._sendLock.release()

    # Now wait till the answer is in...
    condition.acquire()
    try:
      while not result:
        condition.wait()
    finally:
      condition.release()

    # ...And handle the answer appropriately.
    assert len(result) == 1
    reply = result[0]
    if reply == "EXCEPTION":
      raise self._closedEx

    return reply


  def debug(self, f):
    """DOCDOC"""
    self._debugFile = f

  def set_event_handler(self, handler):
    """Cause future events from the Tor process to be sent to 'handler'.
    """
    if self._handler:
      handler.pre_listeners = self._handler.pre_listeners
      handler.post_listeners = self._handler.post_listeners
    self._handler = handler
    self._handler.c = self
    self._handleFn = handler._handle1

  def add_event_listener(self, listener):
    if not self._handler:
      self.set_event_handler(EventHandler())
    self._handler.add_event_listener(listener)

  def block_until_close(self):
    """ Blocks until the connection to the Tor process is interrupted"""
    return self._eventThread.join()

  def _read_reply(self):
    lines = []
    while 1:
      line = self._s.readline()
      if not line:
        self._closed = True
        raise TorCtlClosed() 
      line = line.strip()
      if self._debugFile:
        self._debugFile.write(str(time.time())+"\t  %s\n" % line)
      if len(line)<4:
        raise ProtocolError("Badly formatted reply line: Too short")
      code = line[:3]
      tp = line[3]
      s = line[4:]
      if tp == "-":
        lines.append((code, s, None))
      elif tp == " ":
        lines.append((code, s, None))
        isEvent = (lines and lines[0][0][0] == '6')
        return isEvent, lines
      elif tp != "+":
        raise ProtocolError("Badly formatted reply line: unknown type %r"%tp)
      else:
        more = []
        while 1:
          line = self._s.readline()
          if self._debugFile:
            self._debugFile.write("+++ %s" % line)
          if line in (".\r\n", ".\n", "650 OK\n", "650 OK\r\n"): 
            break
          more.append(line)
        lines.append((code, s, unescape_dots("".join(more))))
        isEvent = (lines and lines[0][0][0] == '6')
        if isEvent: # Need "250 OK" if it's not an event. Otherwise, end
          return (isEvent, lines)

    # Notreached
    raise TorCtlError()

  def _doSend(self, msg):
    if self._debugFile:
      amsg = msg
      lines = amsg.split("\n")
      if len(lines) > 2:
        amsg = "\n".join(lines[:2]) + "\n"
      self._debugFile.write(str(time.time())+"\t>>> "+amsg)
    self._s.write(msg)

  def set_timer(self, in_seconds, type=None):
    event = (("650", "TORCTL_TIMER", type),)
    threading.Timer(in_seconds, lambda: 
                  self._eventQueue.put((time.time(), event))).start()

  def set_periodic_timer(self, every_seconds, type=None):
    event = (("650", "TORCTL_TIMER", type),)
    def notlambda():
      plog("DEBUG", "Timer fired for type "+str(type))
      self._eventQueue.put((time.time(), event))
      self._eventQueue.put((time.time(), event))
      threading.Timer(every_seconds, notlambda).start()
    threading.Timer(every_seconds, notlambda).start()

  def sendAndRecv(self, msg="", expectedTypes=("250", "251")):
    """Helper: Send a command 'msg' to Tor, and wait for a command
       in response.  If the response type is in expectedTypes,
       return a list of (tp,body,extra) tuples.  If it is an
       error, raise ErrorReply.  Otherwise, raise ProtocolError.
    """
    if type(msg) == types.ListType:
      msg = "".join(msg)
    assert msg.endswith("\r\n")

    lines = self._sendImpl(self._doSend, msg)

    # print lines
    for tp, msg, _ in lines:
      if tp[0] in '45':
        code = int(tp[:3])
        raise ErrorReply("%s %s"%(tp, msg), status = code, message = msg)
      if tp not in expectedTypes:
        raise ProtocolError("Unexpectd message type %r"%tp)

    return lines

  def authenticate(self, secret=""):
    """
    Authenticates to the control port. If an issue arises this raises either of
    the following:
      - IOError for failures in reading an authentication cookie or querying
        PROTOCOLINFO.
      - TorCtl.ErrorReply for authentication failures or if the secret is
        undefined when using password authentication
    """
    
    # fetches authentication type and cookie path if still unloaded
    if self._authType == None: self.get_auth_type()
    
    # validates input
    if self._authType == AUTH_TYPE.PASSWORD and secret == "":
      raise ErrorReply("Unable to authenticate: no passphrase provided")
    
    authCookie = None
    try:
      if self._authType == AUTH_TYPE.NONE:
        self.authenticate_password("")
      elif self._authType == AUTH_TYPE.PASSWORD:
        self.authenticate_password(secret)
      else:
        authCookie = open(self._cookiePath, "r")
        self.authenticate_cookie(authCookie)
        authCookie.close()
    except ErrorReply, exc:
      if authCookie: authCookie.close()
      issue = str(exc)
      
      # simplifies message if the wrong credentials were provided (common
      # mistake)
      if issue.startswith("515 Authentication failed: "):
        if issue[27:].startswith("Password did not match"):
          issue = "password incorrect"
        elif issue[27:] == "Wrong length on authentication cookie.":
          issue = "cookie value incorrect"
      
      raise ErrorReply("Unable to authenticate: %s" % issue)
    except IOError, exc:
      if authCookie: authCookie.close()
      issue = None
      
      # cleaner message for common errors
      if str(exc).startswith("[Errno 13] Permission denied"):
        issue = "permission denied"
      elif str(exc).startswith("[Errno 2] No such file or directory"):
        issue = "file doesn't exist"
      
      # if problem's recognized give concise message, otherwise print exception
      # string
      if issue: raise IOError("Failed to read authentication cookie (%s): %s" % (issue, self._cookiePath))
      else: raise IOError("Failed to read authentication cookie: %s" % exc)
  
  def authenticate_password(self, secret=""):
    """Sends an authenticating secret (password) to Tor.  You'll need to call 
       this method (or authenticate_cookie) before Tor can start.
    """
    #hexstr = binascii.b2a_hex(secret)
    self.sendAndRecv("AUTHENTICATE \"%s\"\r\n"%secret)
  
  def authenticate_cookie(self, cookie):
    """Sends an authentication cookie to Tor. This may either be a file or 
       its contents.
    """
    
    # read contents if provided a file
    if type(cookie) == file: cookie = cookie.read()
    
    # unlike passwords the cookie contents isn't enclosed by quotes
    self.sendAndRecv("AUTHENTICATE %s\r\n" % binascii.b2a_hex(cookie))

  def get_option(self, name):
    """Get the value of the configuration option named 'name'.  To
       retrieve multiple values, pass a list for 'name' instead of
       a string.  Returns a list of (key,value) pairs.
       Refer to section 3.3 of control-spec.txt for a list of valid names.
    """
    if not isinstance(name, str):
      name = " ".join(name)
    lines = self.sendAndRecv("GETCONF %s\r\n" % name)

    r = []
    for _,line,_ in lines:
      try:
        key, val = line.split("=", 1)
        r.append((key,val))
      except ValueError:
        r.append((line, None))

    return r

  def set_option(self, key, value):
    """Set the value of the configuration option 'key' to the value 'value'.
    """
    return self.set_options([(key, value)])

  def set_options(self, kvlist):
    """Given a list of (key,value) pairs, set them as configuration
       options.
    """
    if not kvlist:
      return
    msg = " ".join(["%s=\"%s\""%(k,quote(v)) for k,v in kvlist])
    return self.sendAndRecv("SETCONF %s\r\n"%msg)

  def reset_options(self, keylist):
    """Reset the options listed in 'keylist' to their default values.

       Tor started implementing this command in version 0.1.1.7-alpha;
       previous versions wanted you to set configuration keys to "".
       That no longer works.
    """
    return self.sendAndRecv("RESETCONF %s\r\n"%(" ".join(keylist)))

  def get_consensus(self, get_iterator=False):
    """Get the pristine Tor Consensus. Returns a list of
       TorCtl.NetworkStatus instances.

       Be aware that by default this reads the whole consensus into memory at
       once which can be fairly sizable (as of writing 3.5 MB), and even if
       freed it may remain allocated to the interpretor:
       http://effbot.org/pyfaq/why-doesnt-python-release-the-memory-when-i-delete-a-large-object.htm

       To avoid this use the iterator instead.
    """

    nsData = self.sendAndRecv("GETINFO dir/status-vote/current/consensus\r\n")[0][2]
    if get_iterator: return ns_body_iter(nsData)
    else: return parse_ns_body(nsData)

  def get_network_status(self, who="all", get_iterator=False):
    """Get the entire network status list. Returns a list of
       TorCtl.NetworkStatus instances.

       Be aware that by default this reads the whole consensus into memory at
       once which can be fairly sizable (as of writing 3.5 MB), and even if
       freed it may remain allocated to the interpretor:
       http://effbot.org/pyfaq/why-doesnt-python-release-the-memory-when-i-delete-a-large-object.htm

       To avoid this use the iterator instead.
      """

    nsData = self.sendAndRecv("GETINFO ns/"+who+"\r\n")[0][2]
    if get_iterator: return ns_body_iter(nsData)
    else: return parse_ns_body(nsData)

  def get_address_mappings(self, type="all"):
    # TODO: Also parse errors and GMTExpiry
    body = self.sendAndRecv("GETINFO address-mappings/"+type+"\r\n")
      
    #print "|"+body[0][1].replace("address-mappings/"+type+"=", "")+"|"
    #print str(body[0])

    if body[0][1].replace("address-mappings/"+type+"=", "") != "":
      # one line
      lines = [body[0][1].replace("address-mappings/"+type+"=", "")]
    elif not body[0][2]:
      return []
    else:
      lines = body[0][2].split("\n")
    if not lines: return []
    ret = []
    for l in lines:
      #print "|"+str(l)+"|"
      if len(l) == 0: continue #Skip last line.. it's empty
      m = re.match(r'(\S+)\s+(\S+)\s+(\"[^"]+\"|\w+)', l)
      if not m:
        raise ProtocolError("ADDRMAP response misformatted.")
      fromaddr, toaddr, when = m.groups()
      if when.upper() == "NEVER":  
        when = None
      else:
        when = time.strptime(when[1:-1], "%Y-%m-%d %H:%M:%S")
      ret.append(AddrMap(fromaddr, toaddr, when))
    return ret

  def get_router(self, ns):
    """Fill in a Router class corresponding to a given NS class"""
    desc = self.sendAndRecv("GETINFO desc/id/" + ns.idhex + "\r\n")[0][2]
    sig_start = desc.find("\nrouter-signature\n")+len("\nrouter-signature\n")
    fp_base64 = sha1(desc[:sig_start]).digest().encode("base64")[:-2]
    r = Router.build_from_desc(desc.split("\n"), ns)
    if fp_base64 != ns.orhash:
      plog("INFO", "Router descriptor for "+ns.idhex+" does not match ns fingerprint (NS @ "+str(ns.updated)+" vs Desc @ "+str(r.published)+")")
      return None
    else:
      return r


  def read_routers(self, nslist):
    """ Given a list a NetworkStatuses in 'nslist', this function will 
        return a list of new Router instances.
    """
    bad_key = 0
    new = []
    for ns in nslist:
      try:
        r = self.get_router(ns)
        if r:
          new.append(r)
      except ErrorReply:
        bad_key += 1
        if "Running" in ns.flags:
          plog("NOTICE", "Running router "+ns.nickname+"="
             +ns.idhex+" has no descriptor")
  
    return new

  def get_info(self, name):
    """Return the value of the internal information field named 'name'.
       Refer to section 3.9 of control-spec.txt for a list of valid names.
       DOCDOC
    """
    if not isinstance(name, str):
      name = " ".join(name)
    lines = self.sendAndRecv("GETINFO %s\r\n"%name)
    d = {}
    for _,msg,more in lines:
      if msg == "OK":
        break
      try:
        k,rest = msg.split("=",1)
      except ValueError:
        raise ProtocolError("Bad info line %r",msg)
      if more:
        d[k] = more
      else:
        d[k] = rest
    return d

  def set_events(self, events, extended=False):
    """Change the list of events that the event handler is interested
       in to those in 'events', which is a list of event names.
       Recognized event names are listed in section 3.3 of the control-spec
    """
    if extended:
      plog ("DEBUG", "SETEVENTS EXTENDED %s\r\n" % " ".join(events))
      self.sendAndRecv("SETEVENTS EXTENDED %s\r\n" % " ".join(events))
    else:
      self.sendAndRecv("SETEVENTS %s\r\n" % " ".join(events))

  def save_conf(self):
    """Flush all configuration changes to disk.
    """
    self.sendAndRecv("SAVECONF\r\n")

  def send_signal(self, sig):
    """Send the signal 'sig' to the Tor process; The allowed values for
       'sig' are listed in section 3.6 of control-spec.
    """
    sig = { 0x01 : "HUP",
        0x02 : "INT",
        0x03 : "NEWNYM",
        0x0A : "USR1",
        0x0C : "USR2",
        0x0F : "TERM" }.get(sig,sig)
    self.sendAndRecv("SIGNAL %s\r\n"%sig)

  def resolve(self, host):
    """ Launch a remote hostname lookup request:
        'host' may be a hostname or IPv4 address
    """
    # TODO: handle "mode=reverse"
    self.sendAndRecv("RESOLVE %s\r\n"%host)

  def map_address(self, kvList):
    """ Sends the MAPADDRESS command for each of the tuples in kvList """
    if not kvList:
      return
    m = " ".join([ "%s=%s" for k,v in kvList])
    lines = self.sendAndRecv("MAPADDRESS %s\r\n"%m)
    r = []
    for _,line,_ in lines:
      try:
        key, val = line.split("=", 1)
      except ValueError:
        raise ProtocolError("Bad address line %r",v)
      r.append((key,val))
    return r

  def extend_circuit(self, circid=None, hops=None):
    """Tell Tor to extend the circuit identified by 'circid' through the
       servers named in the list 'hops'.
    """
    if circid is None:
      circid = 0
    if hops is None:
      hops = ""
    plog("DEBUG", "Extending circuit")
    lines = self.sendAndRecv("EXTENDCIRCUIT %d %s\r\n"
                  %(circid, ",".join(hops)))
    tp,msg,_ = lines[0]
    m = re.match(r'EXTENDED (\S*)', msg)
    if not m:
      raise ProtocolError("Bad extended line %r",msg)
    plog("DEBUG", "Circuit extended")
    return int(m.group(1))

  def redirect_stream(self, streamid, newaddr, newport=""):
    """DOCDOC"""
    if newport:
      self.sendAndRecv("REDIRECTSTREAM %d %s %s\r\n"%(streamid, newaddr, newport))
    else:
      self.sendAndRecv("REDIRECTSTREAM %d %s\r\n"%(streamid, newaddr))

  def attach_stream(self, streamid, circid, hop=None):
    """Attach a stream to a circuit, specify both by IDs. If hop is given, 
       try to use the specified hop in the circuit as the exit node for 
       this stream.
    """
    if hop:
      self.sendAndRecv("ATTACHSTREAM %d %d HOP=%d\r\n"%(streamid, circid, hop))
      plog("DEBUG", "Attaching stream: "+str(streamid)+" to hop "+str(hop)+" of circuit "+str(circid))
    else:
      self.sendAndRecv("ATTACHSTREAM %d %d\r\n"%(streamid, circid))
      plog("DEBUG", "Attaching stream: "+str(streamid)+" to circuit "+str(circid))

  def close_stream(self, streamid, reason=0, flags=()):
    """DOCDOC"""
    self.sendAndRecv("CLOSESTREAM %d %s %s\r\n"
              %(streamid, reason, "".join(flags)))

  def close_circuit(self, circid, reason=0, flags=()):
    """DOCDOC"""
    self.sendAndRecv("CLOSECIRCUIT %d %s %s\r\n"
              %(circid, reason, "".join(flags)))

  def post_descriptor(self, desc):
    self.sendAndRecv("+POSTDESCRIPTOR purpose=controller\r\n%s"%escape_dots(desc))

def parse_ns_body(data):
  """Parse the body of an NS event or command into a list of
     NetworkStatus instances"""
  return list(ns_body_iter(data))

def ns_body_iter(data):
  """Generator for NetworkStatus instances of an NS event"""
  if data:
    nsgroups = re.compile(r"^r ", re.M).split(data)
    nsgroups.pop(0)

    while nsgroups:
      nsline = nsgroups.pop(0)
      m = re.search(r"^s((?:[ ]\S*)+)", nsline, re.M)
      flags = m.groups()
      flags = flags[0].strip().split(" ")
      m = re.match(r"(\S+)\s(\S+)\s(\S+)\s(\S+\s\S+)\s(\S+)\s(\d+)\s(\d+)", nsline)
      w = re.search(r"^w Bandwidth=(\d+)", nsline, re.M)

      if w:
        yield NetworkStatus(*(m.groups()+(flags,)+(int(w.group(1))*1000,)))
      else:
        yield NetworkStatus(*(m.groups() + (flags,)))

class EventSink:
  def heartbeat_event(self, event): pass
  def unknown_event(self, event): pass
  def circ_status_event(self, event): pass
  def stream_status_event(self, event): pass
  def stream_bw_event(self, event): pass
  def or_conn_status_event(self, event): pass
  def bandwidth_event(self, event): pass
  def new_desc_event(self, event): pass
  def msg_event(self, event): pass
  def ns_event(self, event): pass
  def new_consensus_event(self, event): pass
  def buildtimeout_set_event(self, event): pass
  def guard_event(self, event): pass
  def address_mapped_event(self, event): pass
  def timer_event(self, event): pass

class EventListener(EventSink):
  """An 'EventListener' is a passive sink for parsed Tor events. It 
     implements the same interface as EventHandler, but it should
     not alter Tor's behavior as a result of these events.
    
     Do not extend from this class. Instead, extend from one of 
     Pre, Post, or Dual event listener, to get events 
     before, after, or before and after the EventHandler handles them.
     """
  def __init__(self):
    """Create a new EventHandler."""
    self._map1 = {
      "CIRC" : self.circ_status_event,
      "STREAM" : self.stream_status_event,
      "ORCONN" : self.or_conn_status_event,
      "STREAM_BW" : self.stream_bw_event,
      "BW" : self.bandwidth_event,
      "DEBUG" : self.msg_event,
      "INFO" : self.msg_event,
      "NOTICE" : self.msg_event,
      "WARN" : self.msg_event,
      "ERR" : self.msg_event,
      "NEWDESC" : self.new_desc_event,
      "ADDRMAP" : self.address_mapped_event,
      "NS" : self.ns_event,
      "NEWCONSENSUS" : self.new_consensus_event,
      "BUILDTIMEOUT_SET" : self.buildtimeout_set_event,
      "GUARD" : self.guard_event,
      "TORCTL_TIMER" : self.timer_event
      }
    self.parent_handler = None
    self._sabotage()

  def _sabotage(self):
    raise TorCtlError("Error: Do not extend from EventListener directly! Use Pre, Post or DualEventListener instead.")
 
  def listen(self, event):
    self.heartbeat_event(event)
    self._map1.get(event.event_name, self.unknown_event)(event)

  def set_parent(self, parent_handler):
    self.parent_handler = parent_handler

class PreEventListener(EventListener):
  def _sabotage(self): pass
class PostEventListener(EventListener):
  def _sabotage(self): pass
class DualEventListener(PreEventListener,PostEventListener): 
  def _sabotage(self): pass

class EventHandler(EventSink):
  """An 'EventHandler' wraps callbacks for the events Tor can return. 
     Each event argument is an instance of the corresponding event
     class."""
  def __init__(self):
    """Create a new EventHandler."""
    self._map1 = {
      "CIRC" : self.circ_status_event,
      "STREAM" : self.stream_status_event,
      "ORCONN" : self.or_conn_status_event,
      "STREAM_BW" : self.stream_bw_event,
      "BW" : self.bandwidth_event,
      "DEBUG" : self.msg_event,
      "INFO" : self.msg_event,
      "NOTICE" : self.msg_event,
      "WARN" : self.msg_event,
      "ERR" : self.msg_event,
      "NEWDESC" : self.new_desc_event,
      "ADDRMAP" : self.address_mapped_event,
      "NS" : self.ns_event,
      "NEWCONSENSUS" : self.new_consensus_event,
      "BUILDTIMEOUT_SET" : self.buildtimeout_set_event,
      "GUARD" : self.guard_event,
      "TORCTL_TIMER" : self.timer_event
      }
    self.c = None # Gets set by Connection.set_event_hanlder()
    self.pre_listeners = []
    self.post_listeners = []

  def _handle1(self, timestamp, lines):
    """Dispatcher: called from Connection when an event is received."""
    for code, msg, data in lines:
      event = self._decode1(msg, data)
      event.arrived_at = timestamp
      event.state=EVENT_STATE.PRELISTEN
      for l in self.pre_listeners:
        l.listen(event)
      event.state=EVENT_STATE.HEARTBEAT
      self.heartbeat_event(event)
      event.state=EVENT_STATE.HANDLING
      self._map1.get(event.event_name, self.unknown_event)(event)
      event.state=EVENT_STATE.POSTLISTEN
      for l in self.post_listeners:
        l.listen(event)

  def _decode1(self, body, data):
    """Unpack an event message into a type/arguments-tuple tuple."""
    if " " in body:
      evtype,body = body.split(" ",1)
    else:
      evtype,body = body,""
    evtype = evtype.upper()
    if evtype == "CIRC":
      m = re.match(r"(\d+)\s+(\S+)(\s\S+)?(\s\S+)?(\s\S+)?(\s\S+)?", body)
      if not m:
        raise ProtocolError("CIRC event misformatted.")
      ident,status,path,purpose,reason,remote = m.groups()
      ident = int(ident)
      if path:
        if "PURPOSE=" in path:
          remote = reason
          reason = purpose
          purpose=path
          path=[]
        elif "REASON=" in path:
          remote = reason
          reason = path
          purpose = ""
          path=[]
        else:
          path_verb = path.strip().split(",")
          path = []
          for p in path_verb:
            path.append(p.replace("~", "=").split("=")[0])
      else:
        path = []

      if purpose and "REASON=" in purpose:
        remote=reason
        reason=purpose
        purpose=""

      if purpose: purpose = purpose[9:]
      if reason: reason = reason[8:]
      if remote: remote = remote[15:]
      event = CircuitEvent(evtype, ident, status, path, purpose, reason,
                           remote, body)
    elif evtype == "STREAM":
      #plog("DEBUG", "STREAM: "+body)
      m = re.match(r"(\S+)\s+(\S+)\s+(\S+)\s+(\S+)?:(\d+)(\sREASON=\S+)?(\sREMOTE_REASON=\S+)?(\sSOURCE=\S+)?(\sSOURCE_ADDR=\S+)?(\s+PURPOSE=\S+)?", body)
      if not m:
        raise ProtocolError("STREAM event misformatted.")
      ident,status,circ,target_host,target_port,reason,remote,source,source_addr,purpose = m.groups()
      ident,circ = map(int, (ident,circ))
      if not target_host: # This can happen on SOCKS_PROTOCOL failures
        target_host = "(none)"
      if reason: reason = reason[8:]
      if remote: remote = remote[15:]
      if source: source = source[8:]
      if source_addr: source_addr = source_addr[13:]
      if purpose:
        purpose = purpose.lstrip()
        purpose = purpose[8:]
      event = StreamEvent(evtype, ident, status, circ, target_host,
               int(target_port), reason, remote, source, source_addr,
               purpose, body)
    elif evtype == "ORCONN":
      m = re.match(r"(\S+)\s+(\S+)(\sAGE=\S+)?(\sREAD=\S+)?(\sWRITTEN=\S+)?(\sREASON=\S+)?(\sNCIRCS=\S+)?", body)
      if not m:
        raise ProtocolError("ORCONN event misformatted.")
      target, status, age, read, wrote, reason, ncircs = m.groups()

      #plog("DEBUG", "ORCONN: "+body)
      if ncircs: ncircs = int(ncircs[8:])
      else: ncircs = 0
      if reason: reason = reason[8:]
      if age: age = int(age[5:])
      else: age = 0
      if read: read = int(read[6:])
      else: read = 0
      if wrote: wrote = int(wrote[9:])
      else: wrote = 0
      event = ORConnEvent(evtype, status, target, age, read, wrote,
                reason, ncircs, body)
    elif evtype == "STREAM_BW":
      m = re.match(r"(\d+)\s+(\d+)\s+(\d+)", body)
      if not m:
        raise ProtocolError("STREAM_BW event misformatted.")
      event = StreamBwEvent(evtype, body, *m.groups())
    elif evtype == "BW":
      m = re.match(r"(\d+)\s+(\d+)", body)
      if not m:
        raise ProtocolError("BANDWIDTH event misformatted.")
      read, written = map(long, m.groups())
      event = BWEvent(evtype, read, written, body)
    elif evtype in ("DEBUG", "INFO", "NOTICE", "WARN", "ERR"):
      event = LogEvent(evtype, body)
    elif evtype == "NEWDESC":
      ids_verb = body.split(" ")
      ids = []
      for i in ids_verb:
        ids.append(i.replace("~", "=").split("=")[0].replace("$",""))
      event = NewDescEvent(evtype, ids, body)
    elif evtype == "ADDRMAP":
      # TODO: Also parse errors and GMTExpiry
      m = re.match(r'(\S+)\s+(\S+)\s+(\"[^"]+\"|\w+)', body)
      if not m:
        raise ProtocolError("ADDRMAP event misformatted.")
      fromaddr, toaddr, when = m.groups()
      if when.upper() == "NEVER":  
        when = None
      else:
        when = time.strptime(when[1:-1], "%Y-%m-%d %H:%M:%S")
      event = AddrMapEvent(evtype, fromaddr, toaddr, when, body)
    elif evtype == "NS":
      event = NetworkStatusEvent(evtype, parse_ns_body(data), data)
    elif evtype == "NEWCONSENSUS":
      event = NewConsensusEvent(evtype, parse_ns_body(data), data)
    elif evtype == "BUILDTIMEOUT_SET":
      m = re.match(
        r"(\S+)\sTOTAL_TIMES=(\d+)\sTIMEOUT_MS=(\d+)\sXM=(\d+)\sALPHA=(\S+)\sCUTOFF_QUANTILE=(\S+)",
        body)
      set_type, total_times, timeout_ms, xm, alpha, quantile = m.groups()
      event = BuildTimeoutSetEvent(evtype, set_type, int(total_times),
                                   int(timeout_ms), int(xm), float(alpha),
                                   float(quantile), body)
    elif evtype == "GUARD":
      m = re.match(r"(\S+)\s(\S+)\s(\S+)", body)
      entry, guard, status = m.groups()
      event = GuardEvent(evtype, entry, guard, status, body)
    elif evtype == "TORCTL_TIMER":
      event = TimerEvent(evtype, data)
    else:
      event = UnknownEvent(evtype, body)

    return event

  def add_event_listener(self, evlistener):
    if isinstance(evlistener, PreEventListener):
      self.pre_listeners.append(evlistener)
    if isinstance(evlistener, PostEventListener):
      self.post_listeners.append(evlistener)
    evlistener.set_parent(self)

  def heartbeat_event(self, event):
    """Called before any event is received. Convenience function
       for any cleanup/setup/reconfiguration you may need to do.
    """
    pass

  def unknown_event(self, event):
    """Called when we get an event type we don't recognize.  This
       is almost alwyas an error.
    """
    pass

  def circ_status_event(self, event):
    """Called when a circuit status changes if listening to CIRCSTATUS
       events."""
    pass

  def stream_status_event(self, event):
    """Called when a stream status changes if listening to STREAMSTATUS
       events.  """
    pass

  def stream_bw_event(self, event):
    pass

  def or_conn_status_event(self, event):
    """Called when an OR connection's status changes if listening to
       ORCONNSTATUS events."""
    pass

  def bandwidth_event(self, event):
    """Called once a second if listening to BANDWIDTH events.
    """
    pass

  def new_desc_event(self, event):
    """Called when Tor learns a new server descriptor if listenting to
       NEWDESC events.
    """
    pass

  def msg_event(self, event):
    """Called when a log message of a given severity arrives if listening
       to INFO_MSG, NOTICE_MSG, WARN_MSG, or ERR_MSG events."""
    pass

  def ns_event(self, event):
    pass

  def new_consensus_event(self, event):
    pass

  def buildtimeout_set_event(self, event):
    pass

  def guard_event(self, event):
    pass

  def address_mapped_event(self, event):
    """Called when Tor adds a mapping for an address if listening
       to ADDRESSMAPPED events.
    """
    pass

  def timer_event(self, event):
    pass

class Consensus:
  """
  A Consensus is a pickleable container for the members of
  ConsensusTracker. This should only be used as a temporary 
  reference, and will change after a NEWDESC or NEWCONSENUS event.
  If you want a copy of a consensus that is independent
  of subsequent updates, use copy.deepcopy()
  """

  def __init__(self, ns_map, sorted_r, router_map, nick_map, consensus_count):
    self.ns_map = ns_map
    self.sorted_r = sorted_r
    self.routers = router_map
    self.name_to_key = nick_map
    self.consensus_count = consensus_count

class ConsensusTracker(EventHandler):
  """
  A ConsensusTracker is an EventHandler that tracks the current
  consensus of Tor in self.ns_map, self.routers and self.sorted_r

  Users must subscribe to "NEWCONSENSUS" and "NEWDESC" events.

  If you also wish to track the Tor client's opinion on the Running flag
  based on reachability tests, you must subscribe to "NS" events,
  and you should set the constructor parameter "consensus_only" to
  False.
  """
  def __init__(self, c, RouterClass=Router, consensus_only=True):
    EventHandler.__init__(self)
    c.set_event_handler(self)
    self.ns_map = {}
    self.routers = {}
    self.sorted_r = []
    self.name_to_key = {}
    self.RouterClass = RouterClass
    self.consensus_count = 0
    self.consensus_only = consensus_only
    self.update_consensus()

  # XXX: If there were a potential memory leak through perpetually referenced
  # objects, this function would be the #1 suspect.
  def _read_routers(self, nslist):
    # Routers can fall out of our consensus five different ways:
    # 1. Their descriptors disappear
    # 2. Their NS documents disappear
    # 3. They lose the Running flag
    # 4. They list a bandwidth of 0
    # 5. They have 'opt hibernating' set
    routers = self.c.read_routers(nslist) # Sets .down if 3,4,5
    self.consensus_count = len(routers)
    old_idhexes = set(self.routers.keys())
    new_idhexes = set(map(lambda r: r.idhex, routers)) 
    for r in routers:
      if r.idhex in self.routers:
        if self.routers[r.idhex].nickname != r.nickname:
          plog("NOTICE", "Router "+r.idhex+" changed names from "
             +self.routers[r.idhex].nickname+" to "+r.nickname)
        # Must do IN-PLACE update to keep all the refs to this router
        # valid and current (especially for stats)
        self.routers[r.idhex].update_to(r)
      else:
        rc = self.RouterClass(r)
        self.routers[rc.idhex] = rc

    removed_idhexes = old_idhexes - new_idhexes
    removed_idhexes.update(set(map(lambda r: r.idhex,
                                   filter(lambda r: r.down, routers))))

    for i in removed_idhexes:
      if i not in self.routers: continue
      self.routers[i].down = True
      if "Running" in self.routers[i].flags:
        self.routers[i].flags.remove("Running")
      if self.routers[i].refcount == 0:
        self.routers[i].deleted = True
        if self.routers[i].__class__.__name__ == "StatsRouter":
          plog("WARN", "Expiring non-running StatsRouter "+i)
        else:
          plog("INFO", "Expiring non-running router "+i)
        del self.routers[i]
      else:
        plog("INFO", "Postponing expiring non-running router "+i)
        self.routers[i].deleted = True

    self.sorted_r = filter(lambda r: not r.down, self.routers.itervalues())
    self.sorted_r.sort(lambda x, y: cmp(y.bw, x.bw))
    for i in xrange(len(self.sorted_r)): self.sorted_r[i].list_rank = i

    ratio_r = copy.copy(self.sorted_r)
    ratio_r.sort(lambda x, y: cmp(float(y.bw)/y.desc_bw,
                                  float(x.bw)/x.desc_bw))
    for i in xrange(len(ratio_r)): ratio_r[i].ratio_rank = i

    # XXX: Verification only. Can be removed.
    self._sanity_check(self.sorted_r)

  def _sanity_check(self, list):
    if len(self.routers) > 1.5*self.consensus_count:
      plog("WARN", "Router count of "+str(len(self.routers))+" exceeds consensus count "+str(self.consensus_count)+" by more than 50%")

    if len(self.ns_map) < self.consensus_count:
      plog("WARN", "NS map count of "+str(len(self.ns_map))+" is below consensus count "+str(self.consensus_count))

    downed =  filter(lambda r: r.down, list)
    for d in downed:
      plog("WARN", "Router "+d.idhex+" still present but is down. Del: "+str(d.deleted)+", flags: "+str(d.flags)+", bw: "+str(d.bw))
 
    deleted =  filter(lambda r: r.deleted, list)
    for d in deleted:
      plog("WARN", "Router "+d.idhex+" still present but is deleted. Down: "+str(d.down)+", flags: "+str(d.flags)+", bw: "+str(d.bw))

    zero =  filter(lambda r: r.refcount == 0 and r.__class__.__name__ == "StatsRouter", list)
    for d in zero:
      plog("WARN", "Router "+d.idhex+" has refcount 0. Del:"+str(d.deleted)+", Down: "+str(d.down)+", flags: "+str(d.flags)+", bw: "+str(d.bw))
 
  def _update_consensus(self, nslist):
    self.ns_map = {}
    for n in nslist:
      self.ns_map[n.idhex] = n
      self.name_to_key[n.nickname] = "$"+n.idhex
   
  def update_consensus(self):
    if self.consensus_only:
      self._update_consensus(self.c.get_consensus())
    else:
      self._update_consensus(self.c.get_network_status(get_iterator=True))
    self._read_routers(self.ns_map.values())

  def new_consensus_event(self, n):
    self._update_consensus(n.nslist)
    self._read_routers(self.ns_map.values())
    plog("DEBUG", str(time.time()-n.arrived_at)+" Read " + str(len(n.nslist))
       +" NC => " + str(len(self.sorted_r)) + " routers")
 
  def new_desc_event(self, d):
    update = False
    for i in d.idlist:
      r = None
      try:
        if i in self.ns_map:
          ns = (self.ns_map[i],)
        else:
          plog("WARN", "Need to getinfo ns/id for router desc: "+i)
          ns = self.c.get_network_status("id/"+i)
        r = self.c.read_routers(ns)
      except ErrorReply, e:
        plog("WARN", "Error reply for "+i+" after NEWDESC: "+str(e))
        continue
      if not r:
        plog("WARN", "No router desc for "+i+" after NEWDESC")
        continue
      elif len(r) != 1:
        plog("WARN", "Multiple descs for "+i+" after NEWDESC")

      r = r[0]
      ns = ns[0]
      if ns.idhex in self.routers:
        if self.routers[ns.idhex].orhash == r.orhash:
          plog("NOTICE",
             "Got extra NEWDESC event for router "+ns.nickname+"="+ns.idhex)
      else:
        self.consensus_count += 1
      self.name_to_key[ns.nickname] = "$"+ns.idhex
      if r and r.idhex in self.ns_map:
        if ns.orhash != self.ns_map[r.idhex].orhash:
          plog("WARN", "Getinfo and consensus disagree for "+r.idhex)
          continue
        update = True
        if r.idhex in self.routers:
          self.routers[r.idhex].update_to(r)
        else:
          self.routers[r.idhex] = self.RouterClass(r)
    if update:
      self.sorted_r = filter(lambda r: not r.down, self.routers.itervalues())
      self.sorted_r.sort(lambda x, y: cmp(y.bw, x.bw))
      for i in xrange(len(self.sorted_r)): self.sorted_r[i].list_rank = i

      ratio_r = copy.copy(self.sorted_r)
      ratio_r.sort(lambda x, y: cmp(float(y.bw)/y.desc_bw,
                                    float(x.bw)/x.desc_bw))
      for i in xrange(len(ratio_r)): ratio_r[i].ratio_rank = i
    plog("DEBUG", str(time.time()-d.arrived_at)+ " Read " + str(len(d.idlist))
       +" ND => "+str(len(self.sorted_r))+" routers. Update: "+str(update))
    # XXX: Verification only. Can be removed.
    self._sanity_check(self.sorted_r)
    return update

  def ns_event(self, ev):
    update = False
    for ns in ev.nslist:
      # Check current consensus.. If present, check flags
      if ns.idhex in self.ns_map and ns.idhex in self.routers and \
         ns.orhash == self.ns_map[ns.idhex].orhash:
        if "Running" in ns.flags and \
           "Running" not in self.ns_map[ns.idhex].flags:
          plog("INFO", "Router "+ns.nickname+"="+ns.idhex+" is now up.")
          update = True
          self.routers[ns.idhex].flags = ns.flags
          self.routers[ns.idhex].down = False

        if "Running" not in ns.flags and \
           "Running" in self.ns_map[ns.idhex].flags:
          plog("INFO", "Router "+ns.nickname+"="+ns.idhex+" is now down.")
          update = True
          self.routers[ns.idhex].flags = ns.flags
          self.routers[ns.idhex].down = True
    if update:
      self.sorted_r = filter(lambda r: not r.down, self.routers.itervalues())
      self.sorted_r.sort(lambda x, y: cmp(y.bw, x.bw))
      for i in xrange(len(self.sorted_r)): self.sorted_r[i].list_rank = i

      ratio_r = copy.copy(self.sorted_r)
      ratio_r.sort(lambda x, y: cmp(float(y.bw)/y.desc_bw,
                                    float(x.bw)/x.desc_bw))
      for i in xrange(len(ratio_r)): ratio_r[i].ratio_rank = i
    self._sanity_check(self.sorted_r)

  def current_consensus(self):
    return Consensus(self.ns_map, self.sorted_r, self.routers, 
                     self.name_to_key, self.consensus_count)

class DebugEventHandler(EventHandler):
  """Trivial debug event handler: reassembles all parsed events to stdout."""
  def circ_status_event(self, circ_event): # CircuitEvent()
    output = [circ_event.event_name, str(circ_event.circ_id),
          circ_event.status]
    if circ_event.path:
      output.append(",".join(circ_event.path))
    if circ_event.reason:
      output.append("REASON=" + circ_event.reason)
    if circ_event.remote_reason:
      output.append("REMOTE_REASON=" + circ_event.remote_reason)
    print " ".join(output)

  def stream_status_event(self, strm_event):
    output = [strm_event.event_name, str(strm_event.strm_id),
          strm_event.status, str(strm_event.circ_id),
          strm_event.target_host, str(strm_event.target_port)]
    if strm_event.reason:
      output.append("REASON=" + strm_event.reason)
    if strm_event.remote_reason:
      output.append("REMOTE_REASON=" + strm_event.remote_reason)
    print " ".join(output)

  def ns_event(self, ns_event):
    for ns in ns_event.nslist:
      print " ".join((ns_event.event_name, ns.nickname, ns.idhash,
        ns.updated.isoformat(), ns.ip, str(ns.orport),
        str(ns.dirport), " ".join(ns.flags)))

  def new_consensus_event(self, nc_event):
    self.ns_event(nc_event)

  def new_desc_event(self, newdesc_event):
    print " ".join((newdesc_event.event_name, " ".join(newdesc_event.idlist)))
   
  def or_conn_status_event(self, orconn_event):
    if orconn_event.age: age = "AGE="+str(orconn_event.age)
    else: age = ""
    if orconn_event.read_bytes: read = "READ="+str(orconn_event.read_bytes)
    else: read = ""
    if orconn_event.wrote_bytes: wrote = "WRITTEN="+str(orconn_event.wrote_bytes)
    else: wrote = ""
    if orconn_event.reason: reason = "REASON="+orconn_event.reason
    else: reason = ""
    if orconn_event.ncircs: ncircs = "NCIRCS="+str(orconn_event.ncircs)
    else: ncircs = ""
    print " ".join((orconn_event.event_name, orconn_event.endpoint,
            orconn_event.status, age, read, wrote, reason, ncircs))

  def msg_event(self, log_event):
    print log_event.event_name+" "+log_event.msg
  
  def bandwidth_event(self, bw_event):
    print bw_event.event_name+" "+str(bw_event.read)+" "+str(bw_event.written)

def parseHostAndPort(h):
  """Given a string of the form 'address:port' or 'address' or
     'port' or '', return a two-tuple of (address, port)
  """
  host, port = "localhost", 9100
  if ":" in h:
    i = h.index(":")
    host = h[:i]
    try:
      port = int(h[i+1:])
    except ValueError:
      print "Bad hostname %r"%h
      sys.exit(1)
  elif h:
    try:
      port = int(h)
    except ValueError:
      host = h

  return host, port

def connect(controlAddr="127.0.0.1", controlPort=9051, passphrase=None,
            ConnClass=Connection):
  """
  Convenience function for quickly getting a TorCtl connection. This is very
  handy for debugging or CLI setup, handling setup and prompting for a password
  if necessary (if either none is provided as input or it fails). If any issues
  arise this prints a description of the problem and returns None.
  
  Arguments:
    controlAddr - ip address belonging to the controller
    controlPort - port belonging to the controller
    passphrase  - authentication passphrase (if defined this is used rather
                  than prompting the user)
  """

  conn = None
  try:
    conn, authType, authValue = preauth_connect(controlAddr, controlPort,
                                                ConnClass)

    if authType == AUTH_TYPE.PASSWORD:
      # password authentication, promting for the password if it wasn't provided
      if passphrase: authValue = passphrase
      else:
        try: authValue = getpass.getpass()
        except KeyboardInterrupt: return None

    conn.authenticate(authValue)
    return conn
  except Exception, exc:
    if conn: conn.close()

    if passphrase and str(exc) == "Unable to authenticate: password incorrect":
      # provide a warning that the provided password didn't work, then try
      # again prompting for the user to enter it
      print INCORRECT_PASSWORD_MSG
      return connect(controlAddr, controlPort)
    else:
      print exc
      return None

def preauth_connect(controlAddr="127.0.0.1", controlPort=9051,
                    ConnClass=Connection):
  """
  Provides an uninitiated torctl connection components for the control port,
  returning a tuple of the form...
  (torctl connection, authType, authValue)

  The authValue corresponds to the cookie path if using an authentication
  cookie, otherwise this is the empty string. This raises an IOError in case
  of failure.

  Arguments:
    controlAddr - ip address belonging to the controller
    controlPort - port belonging to the controller
  """

  conn = None
  try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((controlAddr, controlPort))
    conn = ConnClass(s)
    authType, authValue = conn.get_auth_type(), ""

    if authType == AUTH_TYPE.COOKIE:
      authValue = conn.get_auth_cookie_path()

    return (conn, authType, authValue)
  except socket.error, exc:
    if conn: conn.close()

    if "Connection refused" in exc.args:
      # most common case - tor control port isn't available
      raise IOError("Connection refused. Is the ControlPort enabled?")

    raise IOError("Failed to establish socket: %s" % exc)
  except Exception, exc:
    if conn: conn.close()
    raise IOError(exc)


########NEW FILE########
__FILENAME__ = TorUtil
#!/usr/bin/python
# TorCtl.py -- Python module to interface with Tor Control interface.
# Copyright 2007-2010 Mike Perry -- See LICENSE for licensing information.
# Portions Copyright 2005 Nick Mathewson

"""
TorUtil -- Support functions for TorCtl.py and metatroller
"""

import os
import re
import sys
import socket
import binascii
import math
import time
import logging
import ConfigParser

if sys.version_info < (2, 5):
  from sha import sha as sha1
else:
  from hashlib import sha1

__all__ = ["Enum", "Enum2", "Callable", "sort_list", "quote", "escape_dots", "unescape_dots",
      "BufSock", "secret_to_key", "urandom_rng", "s2k_gen", "s2k_check", "plog", 
     "ListenSocket", "zprob", "logfile", "loglevel", "loglevels"]

# TODO: This isn't the right place for these.. But at least it's unified.
tor_port = 9060
tor_host = '127.0.0.1'

control_port = 9061
control_host = '127.0.0.1'
control_pass = ""

meta_port = 9052
meta_host = '127.0.0.1'

class Referrer:
  def __init__(self, cl):
    self.referrers = {}
    self.cl_name = cl
    self.count = 0

  def recurse_store(self, gc, obj, depth, max_depth):
    if depth >= max_depth: return
    for r in gc.get_referrers(obj):
      if hasattr(r, "__class__"):
        cl = r.__class__.__name__
        # Skip frames and list iterators.. prob just us
        if cl in ("frame", "listiterator"): continue 
        if cl not in self.referrers:
          self.referrers[cl] = Referrer(cl)
        self.referrers[cl].count += 1
        self.referrers[cl].recurse_store(gc, r, depth+1, max_depth)

  def recurse_print(self, rcutoff, depth=""):
    refs = self.referrers.keys()
    refs.sort(lambda x, y: self.referrers[y].count - self.referrers[x].count)
    for r in refs:
      if self.referrers[r].count > rcutoff:
        plog("NOTICE", "GC:  "+depth+"Refed by "+r+": "+str(self.referrers[r].count))
        self.referrers[r].recurse_print(rcutoff, depth+" ")

def dump_class_ref_counts(referrer_depth=2, cutoff=500, rcutoff=1,
        ignore=('tuple', 'list', 'function', 'dict',
                 'builtin_function_or_method',
                 'wrapper_descriptor')):
  """ Debugging function to track down types of objects
      that cannot be garbage collected because we hold refs to them 
      somewhere."""
  import gc
  __dump_class_ref_counts(gc, referrer_depth, cutoff, rcutoff, ignore)
  gc.collect()
  plog("NOTICE", "GC: Done.")

def __dump_class_ref_counts(gc, referrer_depth, cutoff, rcutoff, ignore):
  """ loil
  """
  plog("NOTICE", "GC: Gathering garbage collection stats...")
  uncollectable = gc.collect()
  class_counts = {}
  referrers = {}
  plog("NOTICE", "GC: Uncollectable objects: "+str(uncollectable))
  objs = gc.get_objects()
  for obj in objs:
    if hasattr(obj, "__class__"):
      cl = obj.__class__.__name__
      if cl in ignore: continue
      if cl not in class_counts:
        class_counts[cl] = 0
        referrers[cl] = Referrer(cl)
      class_counts[cl] += 1
  if referrer_depth:
    for obj in objs:
      if hasattr(obj, "__class__"):
        cl = obj.__class__.__name__
        if cl in ignore: continue
        if class_counts[cl] > cutoff:
          referrers[cl].recurse_store(gc, obj, 0, referrer_depth)
  classes = class_counts.keys()
  classes.sort(lambda x, y: class_counts[y] - class_counts[x])
  for c in classes:
    if class_counts[c] < cutoff: continue
    plog("NOTICE", "GC: Class "+c+": "+str(class_counts[c]))
    if referrer_depth:
      referrers[c].recurse_print(rcutoff)



def read_config(filename):
  config = ConfigParser.SafeConfigParser()
  config.read(filename)
  global tor_port, tor_host, control_port, control_pass, control_host
  global meta_port, meta_host
  global loglevel

  tor_port = config.getint('TorCtl', 'tor_port')
  meta_port = config.getint('TorCtl', 'meta_port')
  control_port = config.getint('TorCtl', 'control_port')

  tor_host = config.get('TorCtl', 'tor_host')
  control_host = config.get('TorCtl', 'control_host')
  meta_host = config.get('TorCtl', 'meta_host')
  control_pass = config.get('TorCtl', 'control_pass')
  loglevel = config.get('TorCtl', 'loglevel')


class Enum:
  """ Defines an ordered dense name-to-number 1-1 mapping """
  def __init__(self, start, names):
    self.nameOf = {}
    idx = start
    for name in names:
      setattr(self,name,idx)
      self.nameOf[idx] = name
      idx += 1

class Enum2:
  """ Defines an ordered sparse name-to-number 1-1 mapping """
  def __init__(self, **args):
    self.__dict__.update(args)
    self.nameOf = {}
    for k,v in args.items():
      self.nameOf[v] = k

class Callable:
    def __init__(self, anycallable):
        self.__call__ = anycallable

def sort_list(list, key):
  """ Sort a list by a specified key """
  list.sort(lambda x,y: cmp(key(x), key(y))) # Python < 2.4 hack
  return list

def quote(s):
  return re.sub(r'([\r\n\\\"])', r'\\\1', s)

def escape_dots(s, translate_nl=1):
  if translate_nl:
    lines = re.split(r"\r?\n", s)
  else:
    lines = s.split("\r\n")
  if lines and not lines[-1]:
    del lines[-1]
  for i in xrange(len(lines)):
    if lines[i].startswith("."):
      lines[i] = "."+lines[i]
  lines.append(".\r\n")
  return "\r\n".join(lines)

def unescape_dots(s, translate_nl=1):
  lines = s.split("\r\n")

  for i in xrange(len(lines)):
    if lines[i].startswith("."):
      lines[i] = lines[i][1:]

  if lines and lines[-1]:
    lines.append("")

  if translate_nl:
    return "\n".join(lines)
  else:
    return "\r\n".join(lines)

# XXX: Exception handling
class BufSock:
  def __init__(self, s):
    self._s = s
    self._buf = []

  def readline(self):
    if self._buf:
      idx = self._buf[0].find('\n')
      if idx >= 0:
        result = self._buf[0][:idx+1]
        self._buf[0] = self._buf[0][idx+1:]
        return result

    while 1:
      try: s = self._s.recv(128)
      except: s = None

      if not s: return None
      # XXX: This really does need an exception
      #  raise ConnectionClosed()
      idx = s.find('\n')
      if idx >= 0:
        self._buf.append(s[:idx+1])
        result = "".join(self._buf)
        rest = s[idx+1:]
        if rest:
          self._buf = [ rest ]
        else:
          del self._buf[:]
        return result
      else:
        self._buf.append(s)

  def write(self, s):
    self._s.send(s)

  def close(self):
    # if we haven't yet established a connection then this raises an error
    # socket.error: [Errno 107] Transport endpoint is not connected
    try: self._s.shutdown(socket.SHUT_RDWR)
    except socket.error: pass

    self._s.close()

# SocketServer.TCPServer is nuts.. 
class ListenSocket:
  def __init__(self, listen_ip, port):
    msg = None
    self.s = None
    for res in socket.getaddrinfo(listen_ip, port, socket.AF_UNSPEC,
              socket.SOCK_STREAM, 0, socket.AI_PASSIVE):
      af, socktype, proto, canonname, sa = res
      try:
        self.s = socket.socket(af, socktype, proto)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      except socket.error, msg:
        self.s = None
        continue
      try:
        self.s.bind(sa)
        self.s.listen(1)
      except socket.error, msg:
        self.s.close()
        self.s = None
        continue
      break
    if self.s is None:
      raise socket.error(msg)

  def accept(self):
    conn, addr = self.s.accept()
    return conn

  def close(self):
    self.s.close()


def secret_to_key(secret, s2k_specifier):
  """Used to generate a hashed password string. DOCDOC."""
  c = ord(s2k_specifier[8])
  EXPBIAS = 6
  count = (16+(c&15)) << ((c>>4) + EXPBIAS)

  d = sha1()
  tmp = s2k_specifier[:8]+secret
  slen = len(tmp)
  while count:
    if count > slen:
      d.update(tmp)
      count -= slen
    else:
      d.update(tmp[:count])
      count = 0
  return d.digest()

def urandom_rng(n):
  """Try to read some entropy from the platform entropy source."""
  f = open('/dev/urandom', 'rb')
  try:
    return f.read(n)
  finally:
    f.close()

def s2k_gen(secret, rng=None):
  """DOCDOC"""
  if rng is None:
    if hasattr(os, "urandom"):
      rng = os.urandom
    else:
      rng = urandom_rng
  spec = "%s%s"%(rng(8), chr(96))
  return "16:%s"%(
    binascii.b2a_hex(spec + secret_to_key(secret, spec)))

def s2k_check(secret, k):
  """DOCDOC"""
  assert k[:3] == "16:"

  k =  binascii.a2b_hex(k[3:])
  return secret_to_key(secret, k[:9]) == k[9:]

## XXX: Make this a class?
loglevel = "DEBUG"
#loglevels = {"DEBUG" : 0, "INFO" : 1, "NOTICE" : 2, "WARN" : 3, "ERROR" : 4, "NONE" : 5}
logfile = None
logger = None

# Python logging levels are in increments of 10, so place our custom
# levels in between Python's default levels.
loglevels = { "DEBUG":  logging.DEBUG,
              "INFO":   logging.INFO,
              "NOTICE": logging.INFO + 5,
              "WARN":   logging.WARN,
              "ERROR":  logging.ERROR,
              "NONE":   logging.ERROR + 5 }
# Set loglevel => name translation.
for name, value in loglevels.iteritems():
  logging.addLevelName(value, name)

def plog_use_logger(name):
  """ Set the Python logger to use with plog() by name.
      Useful when TorCtl is integrated with an application using logging.
      The logger specified by name must be set up before the first call
      to plog()! """
  global logger, loglevels
  logger = logging.getLogger(name)

def plog(level, msg, *args):
  global logger, logfile
  if not logger:
    # Default init = old TorCtl format + default behavior
    # Default behavior = log to stdout if TorUtil.logfile is None,
    # or to the open file specified otherwise.
    logger = logging.getLogger("TorCtl")
    formatter = logging.Formatter("%(levelname)s[%(asctime)s]:%(message)s",
                                  "%a %b %d %H:%M:%S %Y")

    if not logfile:
      logfile = sys.stdout
    # HACK: if logfile is a string, assume is it the desired filename.
    if isinstance(logfile, basestring):
      f = logging.FileHandler(logfile)
      f.setFormatter(formatter)
      logger.addHandler(f)
    # otherwise, pretend it is a stream.
    else:
      ch = logging.StreamHandler(logfile)
      ch.setFormatter(formatter)
      logger.addHandler(ch)
    logger.setLevel(loglevels[loglevel])

  logger.log(loglevels[level], msg, *args)

# The following zprob routine was stolen from
# http://www.nmr.mgh.harvard.edu/Neural_Systems_Group/gary/python/stats.py
# pursuant to this license:
#
# Copyright (c) 1999-2007 Gary Strangman; All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# The above license applies only to the following 39 lines of code.
def zprob(z):
    """
Returns the area under the normal curve 'to the left of' the given z value.
Thus, 
    for z<0, zprob(z) = 1-tail probability
    for z>0, 1.0-zprob(z) = 1-tail probability
    for any z, 2.0*(1.0-zprob(abs(z))) = 2-tail probability
Adapted from z.c in Gary Perlman's |Stat.

Usage:   lzprob(z)
"""
    Z_MAX = 6.0    # maximum meaningful z-value
    if z == 0.0:
        x = 0.0
    else:
        y = 0.5 * math.fabs(z)
        if y >= (Z_MAX*0.5):
            x = 1.0
        elif (y < 1.0):
            w = y*y
            x = ((((((((0.000124818987 * w
                        -0.001075204047) * w +0.005198775019) * w
                      -0.019198292004) * w +0.059054035642) * w
                    -0.151968751364) * w +0.319152932694) * w
                  -0.531923007300) * w +0.797884560593) * y * 2.0
        else:
            y = y - 2.0
            x = (((((((((((((-0.000045255659 * y
                             +0.000152529290) * y -0.000019538132) * y
                           -0.000676904986) * y +0.001390604284) * y
                         -0.000794620820) * y -0.002034254874) * y
                       +0.006549791214) * y -0.010557625006) * y
                     +0.011630447319) * y -0.009279453341) * y
                   +0.005353579108) * y -0.002141268741) * y
                 +0.000535310849) * y +0.999936657524
    if z > 0.0:
        prob = ((x+1.0)*0.5)
    else:
        prob = ((1.0-x)*0.5)
    return prob

def get_git_version(path_to_repo):
  """ Returns a tuple of the branch and head from a git repo (.git)
      if available, or returns ('unknown', 'unknown')
  """
  try:
    f = open(path_to_repo+'HEAD')
    ref = f.readline().strip().split(' ')
    f.close()
  except IOError, e:
    plog('NOTICE', 'Git Repo at %s Not Found' % path_to_repo)
    return ('unknown','unknown')
  try:
    if len(ref) > 1:
      f = open(path_to_repo+ref[1])
      branch = ref[1].strip().split('/')[-1]
      head = f.readline().strip()
    else:
      branch = 'detached'
      head = ref[0]
    f.close()
    return (branch, head)
  except IOError, e:
    pass
  except IndexError, e:
    pass
  plog('NOTICE', 'Git Repo at %s Not Found' % path_to_repo)
  return ('unknown','unknown') 

########NEW FILE########
__FILENAME__ = socks
"""SocksiPy - Python SOCKS module.
Version 1.00

Copyright 2006 Dan-Haim. All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of Dan Haim nor the names of his contributors may be used
   to endorse or promote products derived from this software without specific
   prior written permission.
   
THIS SOFTWARE IS PROVIDED BY DAN HAIM "AS IS" AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
EVENT SHALL DAN HAIM OR HIS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA
OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMANGE.


This module provides a standard socket-like interface for Python
for tunneling connections through SOCKS proxies.

"""

"""

Minor modifications made by Christopher Gilbert (http://motomastyle.com/)
for use in PyLoris (http://pyloris.sourceforge.net/)

Minor modifications made by Mario Vilas (http://breakingcode.wordpress.com/)
mainly to merge bug fixes found in Sourceforge

"""

import socket
import struct
import sys

PROXY_TYPE_SOCKS4 = 1
PROXY_TYPE_SOCKS5 = 2
PROXY_TYPE_HTTP = 3

_defaultproxy = None
_orgsocket = socket.socket

class ProxyError(Exception): pass
class GeneralProxyError(ProxyError): pass
class Socks5AuthError(ProxyError): pass
class Socks5Error(ProxyError): pass
class Socks4Error(ProxyError): pass
class HTTPError(ProxyError): pass

_generalerrors = ("success",
    "invalid data",
    "not connected",
    "not available",
    "bad proxy type",
    "bad input")

_socks5errors = ("succeeded",
    "general SOCKS server failure",
    "connection not allowed by ruleset",
    "Network unreachable",
    "Host unreachable",
    "Connection refused",
    "TTL expired",
    "Command not supported",
    "Address type not supported",
    "Unknown error")

_socks5autherrors = ("succeeded",
    "authentication is required",
    "all offered authentication methods were rejected",
    "unknown username or invalid password",
    "unknown error")

_socks4errors = ("request granted",
    "request rejected or failed",
    "request rejected because SOCKS server cannot connect to identd on the client",
    "request rejected because the client program and identd report different user-ids",
    "unknown error")

def setdefaultproxy(proxytype=None, addr=None, port=None, rdns=True, username=None, password=None):
    """setdefaultproxy(proxytype, addr[, port[, rdns[, username[, password]]]])
    Sets a default proxy which all further socksocket objects will use,
    unless explicitly changed.
    """
    global _defaultproxy
    _defaultproxy = (proxytype, addr, port, rdns, username, password)

def wrapmodule(module):
    """wrapmodule(module)
    Attempts to replace a module's socket library with a SOCKS socket. Must set
    a default proxy using setdefaultproxy(...) first.
    This will only work on modules that import socket directly into the namespace;
    most of the Python Standard Library falls into this category.
    """
    if _defaultproxy != None:
        module.socket.socket = socksocket
    else:
        raise GeneralProxyError((4, "no proxy specified"))

class socksocket(socket.socket):
    """socksocket([family[, type[, proto]]]) -> socket object
    Open a SOCKS enabled socket. The parameters are the same as
    those of the standard socket init. In order for SOCKS to work,
    you must specify family=AF_INET, type=SOCK_STREAM and proto=0.
    """

    def __init__(self, family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, _sock=None):
        _orgsocket.__init__(self, family, type, proto, _sock)
        if _defaultproxy != None:
            self.__proxy = _defaultproxy
        else:
            self.__proxy = (None, None, None, None, None, None)
        self.__proxysockname = None
        self.__proxypeername = None

    def __recvall(self, count):
        """__recvall(count) -> data
        Receive EXACTLY the number of bytes requested from the socket.
        Blocks until the required number of bytes have been received.
        """
        data = self.recv(count)
        while len(data) < count:
            d = self.recv(count-len(data))
            if not d: raise GeneralProxyError((0, "connection closed unexpectedly"))
            data = data + d
        return data

    def setproxy(self, proxytype=None, addr=None, port=None, rdns=True, username=None, password=None):
        """setproxy(proxytype, addr[, port[, rdns[, username[, password]]]])
        Sets the proxy to be used.
        proxytype -    The type of the proxy to be used. Three types
                are supported: PROXY_TYPE_SOCKS4 (including socks4a),
                PROXY_TYPE_SOCKS5 and PROXY_TYPE_HTTP
        addr -        The address of the server (IP or DNS).
        port -        The port of the server. Defaults to 1080 for SOCKS
                servers and 8080 for HTTP proxy servers.
        rdns -        Should DNS queries be preformed on the remote side
                (rather than the local side). The default is True.
                Note: This has no effect with SOCKS4 servers.
        username -    Username to authenticate with to the server.
                The default is no authentication.
        password -    Password to authenticate with to the server.
                Only relevant when username is also provided.
        """
        self.__proxy = (proxytype, addr, port, rdns, username, password)

    def __negotiatesocks5(self, destaddr, destport):
        """__negotiatesocks5(self,destaddr,destport)
        Negotiates a connection through a SOCKS5 server.
        """
        # First we'll send the authentication packages we support.
        if (self.__proxy[4]!=None) and (self.__proxy[5]!=None):
            # The username/password details were supplied to the
            # setproxy method so we support the USERNAME/PASSWORD
            # authentication (in addition to the standard none).
            self.sendall(struct.pack('BBBB', 0x05, 0x02, 0x00, 0x02))
        else:
            # No username/password were entered, therefore we
            # only support connections with no authentication.
            self.sendall(struct.pack('BBB', 0x05, 0x01, 0x00))
        # We'll receive the server's response to determine which
        # method was selected
        chosenauth = self.__recvall(2)
        if chosenauth[0:1] != chr(0x05).encode():
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        # Check the chosen authentication method
        if chosenauth[1:2] == chr(0x00).encode():
            # No authentication is required
            pass
        elif chosenauth[1:2] == chr(0x02).encode():
            # Okay, we need to perform a basic username/password
            # authentication.
            self.sendall(chr(0x01).encode() + chr(len(self.__proxy[4])) + self.__proxy[4] + chr(len(self.__proxy[5])) + self.__proxy[5])
            authstat = self.__recvall(2)
            if authstat[0:1] != chr(0x01).encode():
                # Bad response
                self.close()
                raise GeneralProxyError((1, _generalerrors[1]))
            if authstat[1:2] != chr(0x00).encode():
                # Authentication failed
                self.close()
                raise Socks5AuthError((3, _socks5autherrors[3]))
            # Authentication succeeded
        else:
            # Reaching here is always bad
            self.close()
            if chosenauth[1] == chr(0xFF).encode():
                raise Socks5AuthError((2, _socks5autherrors[2]))
            else:
                raise GeneralProxyError((1, _generalerrors[1]))
        # Now we can request the actual connection
        req = struct.pack('BBB', 0x05, 0x01, 0x00)
        # If the given destination address is an IP address, we'll
        # use the IPv4 address request even if remote resolving was specified.
        try:
            ipaddr = socket.inet_aton(destaddr)
            req = req + chr(0x01).encode() + ipaddr
        except socket.error:
            # Well it's not an IP number,  so it's probably a DNS name.
            if self.__proxy[3]:
                # Resolve remotely
                ipaddr = None
                req = req + chr(0x03).encode() + chr(len(destaddr)).encode() + destaddr
            else:
                # Resolve locally
                ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
                req = req + chr(0x01).encode() + ipaddr
        req = req + struct.pack(">H", destport)
        self.sendall(req)
        # Get the response
        resp = self.__recvall(4)
        if resp[0:1] != chr(0x05).encode():
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        elif resp[1:2] != chr(0x00).encode():
            # Connection failed
            self.close()
            if ord(resp[1:2])<=8:
                raise Socks5Error((ord(resp[1:2]), _socks5errors[ord(resp[1:2])]))
            else:
                raise Socks5Error((9, _socks5errors[9]))
        # Get the bound address/port
        elif resp[3:4] == chr(0x01).encode():
            boundaddr = self.__recvall(4)
        elif resp[3:4] == chr(0x03).encode():
            resp = resp + self.recv(1)
            boundaddr = self.__recvall(ord(resp[4:5]))
        else:
            self.close()
            raise GeneralProxyError((1,_generalerrors[1]))
        boundport = struct.unpack(">H", self.__recvall(2))[0]
        self.__proxysockname = (boundaddr, boundport)
        if ipaddr != None:
            self.__proxypeername = (socket.inet_ntoa(ipaddr), destport)
        else:
            self.__proxypeername = (destaddr, destport)

    def getproxysockname(self):
        """getsockname() -> address info
        Returns the bound IP address and port number at the proxy.
        """
        return self.__proxysockname

    def getproxypeername(self):
        """getproxypeername() -> address info
        Returns the IP and port number of the proxy.
        """
        return _orgsocket.getpeername(self)

    def getpeername(self):
        """getpeername() -> address info
        Returns the IP address and port number of the destination
        machine (note: getproxypeername returns the proxy)
        """
        return self.__proxypeername

    def __negotiatesocks4(self,destaddr,destport):
        """__negotiatesocks4(self,destaddr,destport)
        Negotiates a connection through a SOCKS4 server.
        """
        # Check if the destination address provided is an IP address
        rmtrslv = False
        try:
            ipaddr = socket.inet_aton(destaddr)
        except socket.error:
            # It's a DNS name. Check where it should be resolved.
            if self.__proxy[3]:
                ipaddr = struct.pack("BBBB", 0x00, 0x00, 0x00, 0x01)
                rmtrslv = True
            else:
                ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
        # Construct the request packet
        req = struct.pack(">BBH", 0x04, 0x01, destport) + ipaddr
        # The username parameter is considered userid for SOCKS4
        if self.__proxy[4] != None:
            req = req + self.__proxy[4]
        req = req + chr(0x00).encode()
        # DNS name if remote resolving is required
        # NOTE: This is actually an extension to the SOCKS4 protocol
        # called SOCKS4A and may not be supported in all cases.
        if rmtrslv:
            req = req + destaddr + chr(0x00).encode()
        self.sendall(req)
        # Get the response from the server
        resp = self.__recvall(8)
        if resp[0:1] != chr(0x00).encode():
            # Bad data
            self.close()
            raise GeneralProxyError((1,_generalerrors[1]))
        if resp[1:2] != chr(0x5A).encode():
            # Server returned an error
            self.close()
            if ord(resp[1:2]) in (91, 92, 93):
                self.close()
                raise Socks4Error((ord(resp[1:2]), _socks4errors[ord(resp[1:2]) - 90]))
            else:
                raise Socks4Error((94, _socks4errors[4]))
        # Get the bound address/port
        self.__proxysockname = (socket.inet_ntoa(resp[4:]), struct.unpack(">H", resp[2:4])[0])
        if rmtrslv != None:
            self.__proxypeername = (socket.inet_ntoa(ipaddr), destport)
        else:
            self.__proxypeername = (destaddr, destport)

    def __negotiatehttp(self, destaddr, destport):
        """__negotiatehttp(self,destaddr,destport)
        Negotiates a connection through an HTTP server.
        """
        # If we need to resolve locally, we do this now
        if not self.__proxy[3]:
            addr = socket.gethostbyname(destaddr)
        else:
            addr = destaddr
        self.sendall(("CONNECT " + addr + ":" + str(destport) + " HTTP/1.1\r\n" + "Host: " + destaddr + "\r\n\r\n").encode())
        # We read the response until we get the string "\r\n\r\n"
        resp = self.recv(1)
        while resp.find("\r\n\r\n".encode()) == -1:
            resp = resp + self.recv(1)
        # We just need the first line to check if the connection
        # was successful
        statusline = resp.splitlines()[0].split(" ".encode(), 2)
        if statusline[0] not in ("HTTP/1.0".encode(), "HTTP/1.1".encode()):
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        try:
            statuscode = int(statusline[1])
        except ValueError:
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        if statuscode != 200:
            self.close()
            raise HTTPError((statuscode, statusline[2]))
        self.__proxysockname = ("0.0.0.0", 0)
        self.__proxypeername = (addr, destport)

    def connect(self, destpair):
        """connect(self, despair)
        Connects to the specified destination through a proxy.
        destpar - A tuple of the IP/DNS address and the port number.
        (identical to socket's connect).
        To select the proxy server use setproxy().
        """
        # Do a minimal input check first
        if (not type(destpair) in (list,tuple)) or (len(destpair) < 2) or (type(destpair[0]) != type('')) or (type(destpair[1]) != int):
            raise GeneralProxyError((5, _generalerrors[5]))
        if self.__proxy[0] == PROXY_TYPE_SOCKS5:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 1080
            _orgsocket.connect(self, (self.__proxy[1], portnum))
            self.__negotiatesocks5(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_SOCKS4:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 1080
            _orgsocket.connect(self,(self.__proxy[1], portnum))
            self.__negotiatesocks4(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_HTTP:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 8080
            _orgsocket.connect(self,(self.__proxy[1], portnum))
            self.__negotiatehttp(destpair[0], destpair[1])
        elif self.__proxy[0] == None:
            _orgsocket.connect(self, (destpair[0], destpair[1]))
        else:
            raise GeneralProxyError((4, _generalerrors[4]))

########NEW FILE########
__FILENAME__ = web2py
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

if '__file__' in globals():
    path = os.path.dirname(os.path.abspath(__file__))
    os.chdir(path)
else:
    path = os.getcwd() # Seems necessary for py2exe

sys.path = [path]+[p for p in sys.path if not p==path]

# import gluon.import_all ##### This should be uncommented for py2exe.py
import gluon.widget

gluon.widget.ProgramName="Open Source Whistleblowing Framework"
gluon.widget.ProgramAuthor="Created by Random GlobaLeaks Developers"
gluon.widget.ProgramVersion="version 0.0000"
gluon.widget.ProgramInfo="Starting up..."

# Start Web2py and Web2py cron service!
gluon.widget.start(cron=True)


########NEW FILE########
