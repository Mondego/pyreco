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
    redirect(URL('admin', 'default', 'index',
                 vars=dict(send=URL(args=request.args,vars=request.vars))))

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
    return str(db(query,ignore_common_filters=True).select())


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
                rows = db(query,ignore_common_filters=True).select(limitby=(start, stop), orderby=eval_in_global_env(orderby))
            else:
                rows = db(query,ignore_common_filters=True).select(limitby=(start, stop))
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
            record = db(db[table][key[0]] == request.vars[key[0]], ignore_common_filters=True).select().first()
    else:
        record = db(db[table].id == request.args(2),ignore_common_filters=True).select().first()

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
        'entries': 0,
        'bytes': 0,
        'objects': 0,
        'hits': 0,
        'misses': 0,
        'ratio': 0,
        'oldest': time.time(),
        'keys': []
    }
    disk = copy.copy(ram)
    total = copy.copy(ram)
    disk['keys'] = []
    total['keys'] = []

    def GetInHMS(seconds):
        hours = math.floor(seconds / 3600)
        seconds -= hours * 3600
        minutes = math.floor(seconds / 60)
        seconds -= minutes * 60
        seconds = math.floor(seconds)

        return (hours, minutes, seconds)

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
            ram['entries'] += 1
            if value[0] < ram['oldest']:
                ram['oldest'] = value[0]
            ram['keys'].append((key, GetInHMS(time.time() - value[0])))

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
                disk['entries'] += 1
                if value[0] < disk['oldest']:
                    disk['oldest'] = value[0]
                disk['keys'].append((key, GetInHMS(time.time() - value[0])))

    finally:
        portalocker.unlock(locker)
        locker.close()
        disk_storage.close()

    total['entries'] = ram['entries'] + disk['entries']
    total['bytes'] = ram['bytes'] + disk['bytes']
    total['objects'] = ram['objects'] + disk['objects']
    total['hits'] = ram['hits'] + disk['hits']
    total['misses'] = ram['misses'] + disk['misses']
    total['keys'] = ram['keys'] + disk['keys']
    try:
        total['ratio'] = total['hits'] * 100 / (total['hits'] + total['misses'])
    except (KeyError, ZeroDivisionError):
        total['ratio'] = 0

    if disk['oldest'] < ram['oldest']:
        total['oldest'] = disk['oldest']
    else:
        total['oldest'] = ram['oldest']

    ram['oldest'] = GetInHMS(time.time() - ram['oldest'])
    disk['oldest'] = GetInHMS(time.time() - disk['oldest'])
    total['oldest'] = GetInHMS(time.time() - total['oldest'])

    def key_table(keys):
        return TABLE(
            TR(TD(B('Key')), TD(B('Time in Cache (h:m:s)'))),
            *[TR(TD(k[0]), TD('%02d:%02d:%02d' % k[1])) for k in keys],
            **dict(_class='cache-keys',
                   _style="border-collapse: separate; border-spacing: .5em;"))

    ram['keys'] = key_table(ram['keys'])
    disk['keys'] = key_table(disk['keys'])
    total['keys'] = key_table(total['keys'])

    return dict(form=form, total=total,
                ram=ram, disk=disk, object_stats=hp != False)




########NEW FILE########
__FILENAME__ = default
# -*- coding: utf-8 -*-
# developed by Massimo Di Pierro, BSD License

@auth.requires_login()
def index():
    form=SQLFORM.factory(Field('url',requires=IS_URL(),default='http://...'))
    if form.process().accepted:
        redirect(URL('edit',vars=dict(url=form.vars.url)))
    clones = db(db.cms_clone).select()
    return locals()

@auth.requires_login()
def delete():
    db(db.cms_clone.id==request.args(0))(db.cms_clone.created_by==auth.user.id).delete()
    redirect(URL('index'))

@auth.requires_login()
def edit():
    return locals()

@auth.requires_login()
def edit_clone():
    session._unlock(response)                    
    import urllib,re
    if request.args(0)=='post':
        return request.vars.value or ''
    elif request.args(0)=='store':
        session.new_html = session.html.split('<body')[0]+'<body>' + \
            request.vars.html+'</body></html>'
        return 'ok'
    url = request.vars.url
    try:
        html = urllib.urlopen(url).read()
    except IOError:
        session.flash = 'web page does not exist!'
        redirect(URL('index'))
    url.rstrip('/')
    session.url = url
    a,b = url.split('://')
    items = b.split('/')
    base = a+'://'+items[0]+'/'
    if len(items)>2:
        full = base+'/'.join(items[1:-1])+'/'
    else:
        full = base
    html = re.sub('\s+[\n]','\n',html)
    html = re.sub('>[ \t]+<','> <',html)
    html = re.sub('(src|SRC)\s*=\s*"/(?!/)','src="'+base,html)
    html = re.sub('(src|SRC)\s*=\s*"(?!(/|http))','src="'+full,html)
    html = re.sub('(href|HREF)\s*=\s*"/(?!/)','href="'+base,html)
    html = re.sub('(href|HREF)\s*=\s*"(?!(/|http))','href="'+full,html)
    html = re.sub('url\(/(?!/)','url('+base,html)
    html = re.sub('url\((?!(/|http))','url('+full,html)
    session.new_html = session.html = html
    inject = '<script src="%s" language="javascript"></script>' % URL('static','js/inject.js')
    html = html.replace('</head>',inject+'</head>')
    return html

@auth.requires_login()
def clone():
    id = db.cms_clone.insert(url=session.url,html=session.new_html)
    redirect(URL('page',args=id))

def page():
    if request.args(0)=='clone': redirect(URL('index'))
    html = db.cms_clone(request.args(0)).html
    inject = '<script language="javascript">alert("This is an altered copy of another page.\nIt was made as an experimental proof of concept.\nIf this page infringes a copyright, we will take it down.");</script>'
    html = html.replace('</head>',inject+'</head>')
    return html

def user():
    return dict(form=auth())

@auth.requires_login()
def folder():
    folder = db.cms_folder(request.args(0),created_by=auth.user.id)
    if not folder:
        if db(db.cms_folder).isempty():
            db.cms_folder.insert(name='root',parent_folder=0,created_by=auth.user.id)
        folder = db.cms_folder(parent_folder=0,created_by=auth.user.id)
    folder.path, f = [folder.name], folder.parent_folder
    while f: folder.path, f = [A(f.name,_href=URL('folder',args=f))]+folder.path, f.parent_folder
    files = db(db.cms_file.folder==folder.id).select(orderby=db.cms_file.name)
    folders = db(db.cms_folder.parent_folder==folder.id).select(orderby=db.cms_folder.name)
    return locals()

@auth.requires_login()
def edit_file():
    folder = db.cms_folder(request.args(0),created_by=auth.user.id)
    db.cms_file.folder.default=folder.id
    db.cms_file.name.requires=IS_NOT_IN_DB(
        db(db.cms_file.folder==folder.id),'cms_file.name')
    file = db.cms_file(request.args(1),created_by=auth.user.id)
    form = SQLFORM(db.cms_file,file,deletable=True)\
        .process(next=URL('folder',args=folder.id))
    return locals()

@auth.requires_login()
def edit_folder():
    folder = db.cms_folder(request.args(0),created_by=auth.user.id)
    db.cms_folder.parent_folder.default=folder.id
    db.cms_folder.name.requires=IS_NOT_IN_DB(
        db(db.cms_folder.parent_folder==folder.id),'cms_folder.name')
    ofolder = db.cms_folder(request.args(1),created_by=auth.user.id)
    form = SQLFORM(db.cms_folder,ofolder,deletable=True)\
        .process(next=URL('folder',args=folder.id))
    return locals()

def doc():
    import re
    import contenttype
    items = re.compile('(?P<id>.*?)\.(?P<ext>\w*)').match(request.args(0) or '')
    if not items:
        raise HTTP(404)
    (id, ext) = (items.group('id'), items.group('ext'))
    name = db.cms_file(id).file
    (filename, stream) = db.cms_file.file.retrieve(name)
    print filename
    file = db.cms_file(id)
    response.headers['Content-Type'] = contenttype.contenttype(name)
    response.headers['Content-Disposition'] = "attachment; filename=%s" % filename
    return response.stream(stream, request=request)

########NEW FILE########
__FILENAME__ = cs-cz
# cs-cz.py pro web2py
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"update" je voliteľný výraz ako "field1=\'newvalue\'". Nemôžete upravovať alebo zmazať výsledky JOINu',
'%Y-%m-%d': '%d.%m.%Y',
'%Y-%m-%d %H:%M:%S': '%d.%m.%Y %H:%M:%S',
'%s rows deleted': '%s zmazaných záznamů',
'%s rows updated': '%s upravených záznamů',
'Administrative interface': 'pro administrátorské rozhranie kliknite sem',
'Are you sure you want to delete this object?': 'Opravdu chceš odstranit tento objekt?',
'Available databases and tables': 'Dostupné databáze a tabuľky',
'Cannot be empty': 'Nemůže být prázdné',
'Change password': 'Změna hesla',
'Check to delete': 'Označit ke smazání',
'Check to delete:': 'Check to delete:',
'Client IP': 'Client IP',
'Controller': 'Controller',
'Copyright': 'Copyright',
'Current request': 'Aktuální požadavek',
'Current response': 'Aktuální odpověď',
'Current session': 'Aktuální session',
'DB Model': 'DB Model',
'Database': 'Databáze',
'Delete:': 'Smazat:',
'Description': 'Popis',
'Documentation': 'Dokumentáce',
'E-mail': 'E-mail',
'Edit': 'Upravit',
'Edit Profile': 'Upravit profil',
'Edit current record': 'Upravit aktuální záznam',
'First name': 'Křestní jméno',
'Group %(group_id)s created': 'Skupina %(group_id)s vytvořena',
'Group ID': 'ID skupiny',
'Hello World': 'Ahoj světe',
'Import/Export': 'Import/Export',
'Index': 'Index',
'Internal State': 'Vnitřní stav',
'Invalid Query': 'Neplatná dotaz',
'Invalid email': 'Neplatný email',
'Invalid password': 'Nesprávné heslo',
'Last name': 'Příjmení',
'Layout': 'Layout',
'Logged in': 'Přihlášení úspěšné',
'Logged out': 'Odhlášení úspěšné',
'Login': 'Login',
'Lost Password': 'Ztracené heslo?',
'Menu Model': 'Menu Model',
'Name': 'Jméno',
'New Record': 'Nový záznam',
'New password': 'Nové heslo',
'No databases in this application': 'V této aplikáci nejsou databáze',
'Object or table name': 'Objekt či tabulka',
'Old password': 'Staré heslo',
'Online examples': 'pro online příklady klikněte sem',
'Origin': 'Púvod',
'Password': 'Heslo',
"Password fields don't match": 'Hesla se neshodují',
'Powered by': 'Powered by',
'Query:': 'Dotaz:',
'Readme': 'Nápověda',
'Record ID': 'ID záznamu',
'Register': 'Zaregistrovat se',
'Registration identifier': 'Registrační identifikátor',
'Registration key': 'Registrační kľíč',
'Remember me (for 30 days)': 'Zapamatuj si mne (na 30 dní)',
'Reset Password key': 'Nastavit registrační kľíč',
'Retrieve username': 'Retrieve username',
'Role': 'Role',
'Rows in table': 'řádků v tabulce',
'Rows selected': 'označených řádků',
'Stylesheet': 'CSS',
'Submit': 'Odeslat',
'Sure you want to delete this object?': 'Opravdu chceš smazat tento objekt?',
'Table name': 'Název tabulky',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': '"query" je podmínka jako "db.table1.field1==\'value\'". Něco jako "db.table1.field1==db.table2.field2" má za výsledek SQL JOIN.',
'The output of the file is a dictionary that was rendered by the view': 'Výstup zo souboru je slovník, ktorý byl zobrazený ve view',
'This is a copy of the scaffolding application': 'Toto je kopie skeletu aplikace',
'Timestamp': 'Časové razítko',
'Update:': 'Upravit:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Použijte (...)&(...) pro AND, (...)|(...) pro OR a ~(...) pro NOT na poskládaní komplexnejších dotazů.',
'User %(id)s Logged-in': 'Uživatel %(id)s prihlásen',
'User %(id)s Logged-out': 'Uživatel %(id)s odhlášen',
'User %(id)s Password changed': 'Uživatel %(id)s zmenil heslo',
'User %(id)s Profile updated': 'Uživatel %(id)s upravil profil',
'User %(id)s Registered': 'Uživatel %(id)s se zaregistroval',
'User %(id)s Username retrieved': 'User %(id)s Username retrieved',
'User ID': 'ID uživatele',
'Username': 'Nick',
'Verify Password': 'Zopakuj heslo',
'View': 'Zobrazit',
'Welcome': 'Vítej',
'Welcome to web2py': 'Vitejte ve web2py',
'Which called the function': 'Ktorý zavolal funkci',
'You are successfully running web2py': 'Úspešně jste spustili web2py',
'You can modify this application and adapt it to your needs': 'Můžete upravit tuto aplikáci a prispôsobit ji svojim potřebám',
'You visited the url': 'Navštívili jste URL',
'appadmin is disabled because insecure channel': 'appadmin je zakázaný bez zabezpečeného spojení',
'cache': 'cache',
'customize me!': 'uprav mě!',
'data uploaded': 'data nahrána',
'database': 'databáze',
'database %s select': 'databáze %s výber',
'db': 'db',
'design': 'návrh',
'done!': 'hotovo!',
'enter a number between %(min)g and %(max)g': 'zadej číslo mezi %(min)g a %(max)g',
'enter an integer between %(min)g and %(max)g': 'zadej celé číslo mezi %(min)g a %(max)g',
'export as csv file': 'exportovat do csv souboru',
'forgot username?': 'neznáš svúj nick?',
'insert new': 'vložit nový záznam ',
'insert new %s': 'vložit nový  záznam %s',
'invalid request': 'Neplatný požadavek',
'located in the file': 'v souboru ',
'login': 'prihlásit',
'logout': 'odhlásit',
'lost password?': 'neznáš heslo?',
'new record inserted': 'nový záznam byl vložen',
'next 100 rows': 'dalších 100 řádků',
'or import from csv file': 'a nebo naimportovat z csv souboru',
'password': 'heslo',
'previous 100 rows': 'předchádzajících 100 řádků',
'profile': 'profil',
'record': 'záznam',
'record does not exist': 'záznam neexistuje',
'record id': 'id záznamu',
'register': 'registrovat',
'selected': 'označených',
'state': 'stav',
'table': 'tabulka',
'unable to parse csv file': 'nedá sa zpracovat csv soubor',
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
'Are you sure you want to uninstall application "%s"': '¿Está seguro que desea desinstalar la aplicación "%s"',
'Are you sure you want to uninstall application "%s"?': '¿Está seguro que desea desinstalar la aplicación "%s"?',
'Authentication': 'Autenticación',
'Available databases and tables': 'Bases de datos y tablas disponibles',
'Cannot be empty': 'No puede estar vacío',
'Cannot compile: there are errors in your app.        Debug it, correct errors and try again.': 'No se puede compilar: hay errores en su aplicación. Depure, corrija errores y vuelva a intentarlo.',
'Change Password': 'Cambie Contraseña',
'Check to delete': 'Marque para eliminar',
'Client IP': 'IP del Cliente',
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
'Delete:': 'Elimine:',
'Deploy on Google App Engine': 'Instale en Google App Engine',
'Description': 'Descripción',
'Design for': 'Diseño para',
'E-mail': 'Correo electrónico',
'EDIT': 'EDITAR',
'Edit': 'Editar',
'Edit Profile': 'Editar Perfil',
'Edit This App': 'Edite esta App',
'Edit application': 'Editar aplicación',
'Edit current record': 'Edite el registro actual',
'Editing file': 'Editando archivo',
'Editing file "%s"': 'Editando archivo "%s"',
'Error logs for "%(app)s"': 'Bitácora de errores en "%(app)s"',
'First name': 'Nombre',
'Functions with no doctests will result in [passed] tests.': 'Funciones sin doctests equivalen a pruebas [aceptadas].',
'Group ID': 'ID de Grupo',
'Hello World': 'Hola Mundo',
'Import/Export': 'Importar/Exportar',
'Index': 'Indice',
'Installed applications': 'Aplicaciones instaladas',
'Internal State': 'Estado Interno',
'Invalid Query': 'Consulta inválida',
'Invalid action': 'Acción inválida',
'Invalid email': 'Correo inválido',
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
'Menu Model': 'Modelo "menu"',
'Models': 'Modelos',
'Modules': 'Módulos',
'NO': 'NO',
'Name': 'Nombre',
'New Record': 'Registro nuevo',
'No databases in this application': 'No hay bases de datos en esta aplicación',
'Origin': 'Origen',
'Original/Translation': 'Original/Traducción',
'Password': 'Contraseña',
'Peeking at file': 'Visualizando archivo',
'Powered by': 'Este sitio usa',
'Query:': 'Consulta:',
'Record ID': 'ID de Registro',
'Register': 'Registrese',
'Registration key': 'Contraseña de Registro',
'Reset Password key': 'Reset Password key',
'Resolve Conflict file': 'archivo Resolución de Conflicto',
'Role': 'Rol',
'Rows in table': 'Filas en la tabla',
'Rows selected': 'Filas seleccionadas',
'Saved file hash:': 'Hash del archivo guardado:',
'Static files': 'Archivos estáticos',
'Stylesheet': 'Hoja de estilo',
'Sure you want to delete this object?': '¿Está seguro que desea eliminar este objeto?',
'Table name': 'Nombre de la tabla',
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
'This is the %(filename)s template': 'Esta es la plantilla %(filename)s',
'Ticket': 'Tiquete',
'Timestamp': 'Timestamp',
'Unable to check for upgrades': 'No es posible verificar la existencia de actualizaciones',
'Unable to download': 'No es posible la descarga',
'Unable to download app': 'No es posible descarga la aplicación',
'Update:': 'Actualice:',
'Upload existing application': 'Suba esta aplicación',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Use (...)&(...) para AND, (...)|(...) para OR, y ~(...) para NOT, para crear consultas más complejas.',
'User ID': 'ID de Usuario',
'View': 'Vista',
'Views': 'Vistas',
'Welcome': 'Welcome',
'Welcome %s': 'Bienvenido %s',
'Welcome to web2py': 'Bienvenido a web2py',
'Which called the function': 'La cual llamó la función',
'YES': 'SI',
'You are successfully running web2py': 'Usted está ejecutando web2py exitosamente',
'You can modify this application and adapt it to your needs': 'Usted puede modificar esta aplicación y adaptarla a sus necesidades',
'You visited the url': 'Usted visitó la url',
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
'clean': 'limpiar',
'Online examples': 'Ejemplos en línea',
'Administrative interface': 'Interfaz administrativa',
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
'Documentation': 'Documentación',
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
'new application "%s" created': 'nueva aplicación "%s" creada',
'new record inserted': 'nuevo registro insertado',
'next 100 rows': '100 filas siguientes',
'or import from csv file': 'o importar desde archivo CSV',
'or provide application url:': 'o provea URL de la aplicación:',
'pack all': 'empaquetar todo',
'pack compiled': 'empaquete compiladas',
'previous 100 rows': '100 filas anteriores',
'record': 'registro',
'record does not exist': 'el registro no existe',
'record id': 'id de registro',
'register': 'registrese',
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
'Access Control': "Contrôle d'accès",
'Administrative interface': "Interface d'administration",
'Ajax Recipes': 'Recettes Ajax',
'Are you sure you want to delete this object?': 'Êtes-vous sûr de vouloir supprimer cet objet?',
'Authentication': 'Authentification',
'Available databases and tables': 'Bases de données et tables disponibles',
'Buy this book': 'Acheter ce livre',
'Cannot be empty': 'Ne peut pas être vide',
'Check to delete': 'Cliquez pour supprimer',
'Check to delete:': 'Cliquez pour supprimer:',
'Client IP': 'IP client',
'Community': 'Communauté',
'Controller': 'Contrôleur',
'Copyright': "Droit d'auteur",
'Current request': 'Demande actuelle',
'Current response': 'Réponse actuelle',
'Current session': 'Session en cours',
'DB Model': 'Modèle DB',
'Database': 'Base de données',
'Delete:': 'Supprimer:',
'Demo': 'Démo',
'Deployment Recipes': 'Recettes de déploiement ',
'Description': 'Descriptif',
'Documentation': 'Documentation',
'Download': 'Téléchargement',
'E-mail': 'Courriel',
'Edit': 'Éditer',
'Edit This App': 'Modifier cette application',
'Edit current record': "Modifier l'enregistrement courant",
'Errors': 'Erreurs',
'FAQ': 'faq',
'First name': 'Prénom',
'Forms and Validators': 'Formulaires et Validateurs',
'Free Applications': 'Applications gratuites',
'Function disabled': 'Fonction désactivée',
'Group %(group_id)s created': '%(group_id)s groupe créé',
'Group ID': 'Groupe ID',
'Group uniquely assigned to user %(id)s': "Groupe unique attribué à l'utilisateur %(id)s",
'Groups': 'Groupes',
'Hello World': 'Bonjour le monde',
'Home': 'Accueil',
'Import/Export': 'Importer/Exporter',
'Index': 'Index',
'Internal State': 'État interne',
'Introduction': 'Présentation',
'Invalid Query': 'Requête Invalide',
'Invalid email': 'Courriel invalide',
'Last name': 'Nom',
'Layout': 'Mise en page',
'Layouts': 'layouts',
'Live chat': 'Clavardage en direct',
'Logged in': 'Connecté',
'Login': 'Connectez-vous',
'Lost Password': 'Mot de passe perdu',
'Main Menu': 'Menu principal',
'Menu Model': 'Menu modèle',
'Name': 'Nom',
'New Record': 'Nouvel enregistrement',
'No databases in this application': "Cette application n'a pas de bases de données",
'Online examples': 'Exemples en ligne',
'Origin': 'Origine',
'Other Recipes': 'Autres recettes',
'Overview': 'Présentation',
'Password': 'Mot de passe',
"Password fields don't match": 'Les mots de passe ne correspondent pas',
'Plugins': 'Plugiciels',
'Powered by': 'Alimenté par',
'Preface': 'Préface',
'Python': 'Python',
'Query:': 'Requête:',
'Quick Examples': 'Examples Rapides',
'Readme': 'Lisez-moi',
'Recipes': 'Recettes',
'Record %(id)s created': 'Record %(id)s created',
'Record %(id)s updated': 'Record %(id)s updated',
'Record Created': 'Record Created',
'Record ID': "ID d'enregistrement",
'Record Updated': 'Record Updated',
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
'Semantic': 'Sémantique',
'Services': 'Services',
'Stylesheet': 'Feuille de style',
'Submit': 'Soumettre',
'Support': 'Soutien',
'Sure you want to delete this object?': 'Êtes-vous sûr de vouloir supprimer cet objet?',
'Table name': 'Nom du tableau',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'La "query" est une condition comme "db.table1.champ1==\'valeur\'". Quelque chose comme "db.table1.champ1==db.table2.champ2" résulte en un JOIN SQL.',
'The Core': 'Le noyau',
'The Views': 'Les Vues',
'The output of the file is a dictionary that was rendered by the view': 'La sortie de ce fichier est un dictionnaire qui été restitué par la vue',
'This App': 'Cette Appli',
'This is a copy of the scaffolding application': "Ceci est une copie de l'application échafaudage",
'Timestamp': 'Horodatage',
'Twitter': 'Twitter',
'Update:': 'Mise à jour:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Employez (...)&(...) pour AND, (...)|(...) pour OR, and ~(...)  pour NOT pour construire des requêtes plus complexes.',
'User %(id)s Logged-in': 'Utilisateur %(id)s connecté',
'User %(id)s Registered': 'Utilisateur %(id)s enregistré',
'User ID': 'ID utilisateur',
'User Voice': 'User Voice',
'Verify Password': 'Vérifiez le mot de passe',
'Videos': 'Vidéos',
'View': 'Présentation',
'Web2py': 'Web2py',
'Welcome': 'Bienvenu',
'Welcome %s': 'Bienvenue %s',
'Welcome to web2py': 'Bienvenue à web2py',
'Which called the function': 'Qui a appelé la fonction',
'You are successfully running web2py': 'Vous roulez avec succès web2py',
'You can modify this application and adapt it to your needs': "Vous pouvez modifier cette application et l'adapter à vos besoins",
'You visited the url': "Vous avez visité l'URL",
'about': 'à propos',
'appadmin is disabled because insecure channel': "appadmin est désactivée parce que le canal n'est pas sécurisé",
'cache': 'cache',
'change password': 'changer le mot de passe',
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
'invalid request': 'requête invalide',
'located in the file': 'se trouvant dans le fichier',
'login': 'connectez-vous',
'logout': 'déconnectez-vous',
'lost password': 'mot de passe perdu',
'lost password?': 'mot de passe perdu?',
'new record inserted': 'nouvel enregistrement inséré',
'next 100 rows': '100 prochaines lignes',
'or import from csv file': "ou importer d'un fichier CSV",
'password': 'mot de passe',
'please input your password again': "S'il vous plaît entrer votre mot de passe",
'previous 100 rows': '100 lignes précédentes',
'profile': 'profile',
'record': 'enregistrement',
'record does not exist': "l'archive n'existe pas",
'record id': "id d'enregistrement",
'register': "s'inscrire",
'selected': 'sélectionné',
'state': 'état',
'table': 'tableau',
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
'Access Control': 'Contrôle d\'accès',
'Ajax Recipes': 'Recettes Ajax',
'Are you sure you want to delete this object?': 'Êtes-vous sûr de vouloir supprimer cet objet?',
'Authentication': 'Authentification',
'Available databases and tables': 'Bases de données et tables disponibles',
'Buy this book': 'Acheter ce livre',
'Cannot be empty': 'Ne peut pas être vide',
'Check to delete': 'Cliquez pour supprimer',
'Check to delete:': 'Cliquez pour supprimer:',
'Client IP': 'IP client',
'Community': 'Communauté',
'Controller': 'Contrôleur',
'Copyright': 'Copyright',
'Current request': 'Demande actuelle',
'Current response': 'Réponse actuelle',
'Current session': 'Session en cours',
'DB Model': 'Modèle DB',
'Database': 'Base de données',
'Delete:': 'Supprimer:',
'Demo': 'Démo',
'Deployment Recipes': 'Recettes de déploiement',
'Description': 'Description',
'Documentation': 'Documentation',
'Download': 'Téléchargement',
'E-mail': 'E-mail',
'Edit': 'Éditer',
'Edit This App': 'Modifier cette application',
'Edit current record': "Modifier l'enregistrement courant",
'Errors': 'Erreurs',
'FAQ': 'FAQ',
'First name': 'Prénom',
'Forms and Validators': 'Formulaires et Validateurs',
'Free Applications': 'Applications gratuites',
'Function disabled': 'Fonction désactivée',
'Group ID': 'Groupe ID',
'Groups': 'Groups',
'Hello World': 'Bonjour le monde',
'Home': 'Accueil',
'Import/Export': 'Importer/Exporter',
'Index': 'Index',
'Internal State': 'État interne',
'Introduction': 'Introduction',
'Invalid Query': 'Requête Invalide',
'Invalid email': 'E-mail invalide',
'Last name': 'Nom',
'Layout': 'Mise en page',
'Layouts': 'Layouts',
'Live chat': 'Chat live',
'Login': 'Connectez-vous',
'Lost Password': 'Mot de passe perdu',
'Main Menu': 'Menu principal',
'Menu Model': 'Menu modèle',
'Name': 'Nom',
'New Record': 'Nouvel enregistrement',
'No databases in this application': "Cette application n'a pas de bases de données",
'Origin': 'Origine',
'Other Recipes': 'Autres recettes',
'Overview': 'Présentation',
'Password': 'Mot de passe',
"Password fields don't match": 'Les mots de passe ne correspondent pas',
'Plugins': 'Plugiciels',
'Powered by': 'Alimenté par',
'Preface': 'Préface',
'Python': 'Python',
'Query:': 'Requête:',
'Quick Examples': 'Examples Rapides',
'Recipes': 'Recettes',
'Record ID': 'ID d\'enregistrement',
'Register': "S'inscrire",
'Registration key': "Clé d'enregistrement",
'Remember me (for 30 days)': 'Se souvenir de moi (pendant 30 jours)',
'Request reset password': 'Demande de réinitialiser le mot clé',
'Reset Password key': 'Réinitialiser le mot clé',
'Resources': 'Ressources',
'Role': 'Rôle',
'Rows in table': 'Lignes du tableau',
'Rows selected': 'Lignes sélectionnées',
'Semantic': 'Sémantique',
'Services': 'Services',
'Stylesheet': 'Feuille de style',
'Submit': 'Soumettre',
'Support': 'Support',
'Sure you want to delete this object?': 'Êtes-vous sûr de vouloir supprimer cet objet?',
'Table name': 'Nom du tableau',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'La "query" est une condition comme "db.table1.champ1==\'valeur\'". Quelque chose comme "db.table1.champ1==db.table2.champ2" résulte en un JOIN SQL.',
'The Core': 'Le noyau',
'The Views': 'Les Vues',
'The output of the file is a dictionary that was rendered by the view': 'La sortie de ce fichier est un dictionnaire qui été restitué par la vue',
'This App': 'Cette Appli',
'This is a copy of the scaffolding application': 'Ceci est une copie de l\'application échafaudage',
'Timestamp': 'Horodatage',
'Twitter': 'Twitter',
'Update:': 'Mise à jour:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Employez (...)&(...) pour AND, (...)|(...) pour OR, and ~(...)  pour NOT pour construire des requêtes plus complexes.',
'User %(id)s Logged-in': 'Utilisateur %(id)s connecté',
'User %(id)s Registered': 'Utilisateur %(id)s enregistré',
'User ID': 'ID utilisateur',
'User Voice': 'User Voice',
'Verify Password': 'Vérifiez le mot de passe',
'Videos': 'Vidéos',
'View': 'Présentation',
'Web2py': 'Web2py',
'Welcome': 'Bienvenu',
'Welcome %s': 'Bienvenue %s',
'Welcome to web2py': 'Bienvenue à web2py',
'Which called the function': 'Qui a appelé la fonction',
'You are successfully running web2py': 'Vous roulez avec succès web2py',
'You can modify this application and adapt it to your needs': 'Vous pouvez modifier cette application et l\'adapter à vos besoins',
'You visited the url': 'Vous avez visité l\'URL',
'appadmin is disabled because insecure channel': "appadmin est désactivée parce que le canal n'est pas sécurisé",
'cache': 'cache',
'change password': 'changer le mot de passe',
'Online examples': 'Exemples en ligne',
'Administrative interface': "Interface d'administration",
'customize me!': 'personnalisez-moi!',
'data uploaded': 'données téléchargées',
'database': 'base de données',
'database %s select': 'base de données %s select',
'db': 'db',
'design': 'design',
'Documentation': 'Documentation',
'done!': 'fait!',
'edit profile': 'modifier le profil',
'enter an integer between %(min)g and %(max)g': 'enter an integer between %(min)g and %(max)g',
'export as csv file': 'exporter sous forme de fichier csv',
'insert new': 'insérer un nouveau',
'insert new %s': 'insérer un nouveau %s',
'invalid request': 'requête invalide',
'located in the file': 'se trouvant dans le fichier',
'login': 'connectez-vous',
'logout': 'déconnectez-vous',
'lost password': 'mot de passe perdu',
'lost password?': 'mot de passe perdu?',
'new record inserted': 'nouvel enregistrement inséré',
'next 100 rows': '100 prochaines lignes',
'or import from csv file': "ou importer d'un fichier CSV",
'previous 100 rows': '100 lignes précédentes',
'record': 'enregistrement',
'record does not exist': "l'archive n'existe pas",
'record id': "id d'enregistrement",
'register': "s'inscrire",
'selected': 'sélectionné',
'state': 'état',
'table': 'tableau',
'unable to parse csv file': "incapable d'analyser le fichier cvs",
'Readme': "Lisez-moi",
}


########NEW FILE########
__FILENAME__ = hi-hi
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN',
'%Y-%m-%d': '%Y-%m-%d',
'%Y-%m-%d %H:%M:%S': '%Y-%m-%d %H:%M:%S',
'%s rows deleted': '%s \xe0\xa4\xaa\xe0\xa4\x82\xe0\xa4\x95\xe0\xa5\x8d\xe0\xa4\xa4\xe0\xa4\xbf\xe0\xa4\xaf\xe0\xa4\xbe\xe0\xa4\x81 \xe0\xa4\xae\xe0\xa4\xbf\xe0\xa4\x9f\xe0\xa4\xbe\xe0\xa4\x8f\xe0\xa4\x81',
'%s rows updated': '%s \xe0\xa4\xaa\xe0\xa4\x82\xe0\xa4\x95\xe0\xa5\x8d\xe0\xa4\xa4\xe0\xa4\xbf\xe0\xa4\xaf\xe0\xa4\xbe\xe0\xa4\x81  \xe0\xa4\x85\xe0\xa4\xa6\xe0\xa5\x8d\xe0\xa4\xaf\xe0\xa4\xa4\xe0\xa4\xa8',
'Available databases and tables': '\xe0\xa4\x89\xe0\xa4\xaa\xe0\xa4\xb2\xe0\xa4\xac\xe0\xa5\x8d\xe0\xa4\xa7  \xe0\xa4\xa1\xe0\xa5\x87\xe0\xa4\x9f\xe0\xa4\xbe\xe0\xa4\xac\xe0\xa5\x87\xe0\xa4\xb8 \xe0\xa4\x94\xe0\xa4\xb0 \xe0\xa4\xa4\xe0\xa4\xbe\xe0\xa4\xb2\xe0\xa4\xbf\xe0\xa4\x95\xe0\xa4\xbe',
'Cannot be empty': '\xe0\xa4\x96\xe0\xa4\xbe\xe0\xa4\xb2\xe0\xa5\x80 \xe0\xa4\xa8\xe0\xa4\xb9\xe0\xa5\x80\xe0\xa4\x82 \xe0\xa4\xb9\xe0\xa5\x8b \xe0\xa4\xb8\xe0\xa4\x95\xe0\xa4\xa4\xe0\xa4\xbe',
'Change Password': '\xe0\xa4\xaa\xe0\xa4\xbe\xe0\xa4\xb8\xe0\xa4\xb5\xe0\xa4\xb0\xe0\xa5\x8d\xe0\xa4\xa1 \xe0\xa4\xac\xe0\xa4\xa6\xe0\xa4\xb2\xe0\xa5\x87\xe0\xa4\x82',
'Check to delete': '\xe0\xa4\xb9\xe0\xa4\x9f\xe0\xa4\xbe\xe0\xa4\xa8\xe0\xa5\x87 \xe0\xa4\x95\xe0\xa5\x87 \xe0\xa4\xb2\xe0\xa4\xbf\xe0\xa4\x8f \xe0\xa4\x9a\xe0\xa5\x81\xe0\xa4\xa8\xe0\xa5\x87\xe0\xa4\x82',
'Controller': 'Controller',
'Copyright': 'Copyright',
'Current request': '\xe0\xa4\xb5\xe0\xa4\xb0\xe0\xa5\x8d\xe0\xa4\xa4\xe0\xa4\xae\xe0\xa4\xbe\xe0\xa4\xa8 \xe0\xa4\x85\xe0\xa4\xa8\xe0\xa5\x81\xe0\xa4\xb0\xe0\xa5\x8b\xe0\xa4\xa7',
'Current response': '\xe0\xa4\xb5\xe0\xa4\xb0\xe0\xa5\x8d\xe0\xa4\xa4\xe0\xa4\xae\xe0\xa4\xbe\xe0\xa4\xa8 \xe0\xa4\xaa\xe0\xa5\x8d\xe0\xa4\xb0\xe0\xa4\xa4\xe0\xa4\xbf\xe0\xa4\x95\xe0\xa5\x8d\xe0\xa4\xb0\xe0\xa4\xbf\xe0\xa4\xaf\xe0\xa4\xbe',
'Current session': '\xe0\xa4\xb5\xe0\xa4\xb0\xe0\xa5\x8d\xe0\xa4\xa4\xe0\xa4\xae\xe0\xa4\xbe\xe0\xa4\xa8 \xe0\xa4\xb8\xe0\xa5\x87\xe0\xa4\xb6\xe0\xa4\xa8',
'DB Model': 'DB Model',
'Database': 'Database',
'Delete:': '\xe0\xa4\xae\xe0\xa4\xbf\xe0\xa4\x9f\xe0\xa4\xbe\xe0\xa4\xa8\xe0\xa4\xbe:',
'Edit': 'Edit',
'Edit Profile': '\xe0\xa4\xaa\xe0\xa5\x8d\xe0\xa4\xb0\xe0\xa5\x8b\xe0\xa4\xab\xe0\xa4\xbc\xe0\xa4\xbe\xe0\xa4\x87\xe0\xa4\xb2 \xe0\xa4\xb8\xe0\xa4\x82\xe0\xa4\xaa\xe0\xa4\xbe\xe0\xa4\xa6\xe0\xa4\xbf\xe0\xa4\xa4 \xe0\xa4\x95\xe0\xa4\xb0\xe0\xa5\x87\xe0\xa4\x82',
'Edit This App': 'Edit This App',
'Edit current record': '\xe0\xa4\xb5\xe0\xa4\xb0\xe0\xa5\x8d\xe0\xa4\xa4\xe0\xa4\xae\xe0\xa4\xbe\xe0\xa4\xa8 \xe0\xa4\xb0\xe0\xa5\x87\xe0\xa4\x95\xe0\xa5\x89\xe0\xa4\xb0\xe0\xa5\x8d\xe0\xa4\xa1 \xe0\xa4\xb8\xe0\xa4\x82\xe0\xa4\xaa\xe0\xa4\xbe\xe0\xa4\xa6\xe0\xa4\xbf\xe0\xa4\xa4 \xe0\xa4\x95\xe0\xa4\xb0\xe0\xa5\x87\xe0\xa4\x82 ',
'Hello World': 'Hello World',
'Hello from MyApp': 'Hello from MyApp',
'Import/Export': '\xe0\xa4\x86\xe0\xa4\xaf\xe0\xa4\xbe\xe0\xa4\xa4 / \xe0\xa4\xa8\xe0\xa4\xbf\xe0\xa4\xb0\xe0\xa5\x8d\xe0\xa4\xaf\xe0\xa4\xbe\xe0\xa4\xa4',
'Index': 'Index',
'Internal State': '\xe0\xa4\x86\xe0\xa4\x82\xe0\xa4\xa4\xe0\xa4\xb0\xe0\xa4\xbf\xe0\xa4\x95  \xe0\xa4\xb8\xe0\xa5\x8d\xe0\xa4\xa5\xe0\xa4\xbf\xe0\xa4\xa4\xe0\xa4\xbf',
'Invalid Query': '\xe0\xa4\x85\xe0\xa4\xae\xe0\xa4\xbe\xe0\xa4\xa8\xe0\xa5\x8d\xe0\xa4\xaf  \xe0\xa4\xaa\xe0\xa5\x8d\xe0\xa4\xb0\xe0\xa4\xb6\xe0\xa5\x8d\xe0\xa4\xa8',
'Layout': 'Layout',
'Login': '\xe0\xa4\xb2\xe0\xa5\x89\xe0\xa4\x97 \xe0\xa4\x87\xe0\xa4\xa8',
'Logout': '\xe0\xa4\xb2\xe0\xa5\x89\xe0\xa4\x97 \xe0\xa4\x86\xe0\xa4\x89\xe0\xa4\x9f',
'Lost Password': '\xe0\xa4\xaa\xe0\xa4\xbe\xe0\xa4\xb8\xe0\xa4\xb5\xe0\xa4\xb0\xe0\xa5\x8d\xe0\xa4\xa1 \xe0\xa4\x96\xe0\xa5\x8b \xe0\xa4\x97\xe0\xa4\xaf\xe0\xa4\xbe',
'Main Menu': 'Main Menu',
'Menu Model': 'Menu Model',
'New Record': '\xe0\xa4\xa8\xe0\xa4\xaf\xe0\xa4\xbe \xe0\xa4\xb0\xe0\xa5\x87\xe0\xa4\x95\xe0\xa5\x89\xe0\xa4\xb0\xe0\xa5\x8d\xe0\xa4\xa1',
'No databases in this application': '\xe0\xa4\x87\xe0\xa4\xb8  \xe0\xa4\x85\xe0\xa4\xa8\xe0\xa5\x81\xe0\xa4\xaa\xe0\xa5\x8d\xe0\xa4\xb0\xe0\xa4\xaf\xe0\xa5\x8b\xe0\xa4\x97 \xe0\xa4\xae\xe0\xa5\x87\xe0\xa4\x82 \xe0\xa4\x95\xe0\xa5\x8b\xe0\xa4\x88 \xe0\xa4\xa1\xe0\xa5\x87\xe0\xa4\x9f\xe0\xa4\xbe\xe0\xa4\xac\xe0\xa5\x87\xe0\xa4\xb8 \xe0\xa4\xa8\xe0\xa4\xb9\xe0\xa5\x80\xe0\xa4\x82 \xe0\xa4\xb9\xe0\xa5\x88\xe0\xa4\x82',
'Powered by': 'Powered by',
'Query:': '\xe0\xa4\xaa\xe0\xa5\x8d\xe0\xa4\xb0\xe0\xa4\xb6\xe0\xa5\x8d\xe0\xa4\xa8:',
'Register': '\xe0\xa4\xaa\xe0\xa4\x82\xe0\xa4\x9c\xe0\xa5\x80\xe0\xa4\x95\xe0\xa5\x83\xe0\xa4\xa4 (\xe0\xa4\xb0\xe0\xa4\x9c\xe0\xa4\xbf\xe0\xa4\xb8\xe0\xa5\x8d\xe0\xa4\x9f\xe0\xa4\xb0) \xe0\xa4\x95\xe0\xa4\xb0\xe0\xa4\xa8\xe0\xa4\xbe ',
'Rows in table': '\xe0\xa4\xa4\xe0\xa4\xbe\xe0\xa4\xb2\xe0\xa4\xbf\xe0\xa4\x95\xe0\xa4\xbe \xe0\xa4\xae\xe0\xa5\x87\xe0\xa4\x82 \xe0\xa4\xaa\xe0\xa4\x82\xe0\xa4\x95\xe0\xa5\x8d\xe0\xa4\xa4\xe0\xa4\xbf\xe0\xa4\xaf\xe0\xa4\xbe\xe0\xa4\x81 ',
'Rows selected': '\xe0\xa4\x9a\xe0\xa4\xaf\xe0\xa4\xa8\xe0\xa4\xbf\xe0\xa4\xa4 (\xe0\xa4\x9a\xe0\xa5\x81\xe0\xa4\xa8\xe0\xa5\x87 \xe0\xa4\x97\xe0\xa4\xaf\xe0\xa5\x87) \xe0\xa4\xaa\xe0\xa4\x82\xe0\xa4\x95\xe0\xa5\x8d\xe0\xa4\xa4\xe0\xa4\xbf\xe0\xa4\xaf\xe0\xa4\xbe\xe0\xa4\x81 ',
'Stylesheet': 'Stylesheet',
'Sure you want to delete this object?': '\xe0\xa4\xb8\xe0\xa5\x81\xe0\xa4\xa8\xe0\xa4\xbf\xe0\xa4\xb6\xe0\xa5\x8d\xe0\xa4\x9a\xe0\xa4\xbf\xe0\xa4\xa4 \xe0\xa4\xb9\xe0\xa5\x88\xe0\xa4\x82 \xe0\xa4\x95\xe0\xa4\xbf \xe0\xa4\x86\xe0\xa4\xaa \xe0\xa4\x87\xe0\xa4\xb8 \xe0\xa4\xb5\xe0\xa4\xb8\xe0\xa5\x8d\xe0\xa4\xa4\xe0\xa5\x81 \xe0\xa4\x95\xe0\xa5\x8b \xe0\xa4\xb9\xe0\xa4\x9f\xe0\xa4\xbe\xe0\xa4\xa8\xe0\xa4\xbe \xe0\xa4\x9a\xe0\xa4\xbe\xe0\xa4\xb9\xe0\xa4\xa4\xe0\xa5\x87 \xe0\xa4\xb9\xe0\xa5\x88\xe0\xa4\x82?',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.',
'Update:': '\xe0\xa4\x85\xe0\xa4\xa6\xe0\xa5\x8d\xe0\xa4\xaf\xe0\xa4\xa4\xe0\xa4\xa8 \xe0\xa4\x95\xe0\xa4\xb0\xe0\xa4\xa8\xe0\xa4\xbe:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.',
'View': 'View',
'Welcome %s': 'Welcome %s',
'Welcome to web2py': '\xe0\xa4\xb5\xe0\xa5\x87\xe0\xa4\xac\xe0\xa5\xa8\xe0\xa4\xaa\xe0\xa4\xbe\xe0\xa4\x87 (web2py)  \xe0\xa4\xae\xe0\xa5\x87\xe0\xa4\x82 \xe0\xa4\x86\xe0\xa4\xaa\xe0\xa4\x95\xe0\xa4\xbe \xe0\xa4\xb8\xe0\xa5\x8d\xe0\xa4\xb5\xe0\xa4\xbe\xe0\xa4\x97\xe0\xa4\xa4 \xe0\xa4\xb9\xe0\xa5\x88',
'appadmin is disabled because insecure channel': '\xe0\xa4\x85\xe0\xa4\xaa \xe0\xa4\x86\xe0\xa4\xa1\xe0\xa4\xae\xe0\xa4\xbf\xe0\xa4\xa8 (appadmin) \xe0\xa4\x85\xe0\xa4\x95\xe0\xa5\x8d\xe0\xa4\xb7\xe0\xa4\xae \xe0\xa4\xb9\xe0\xa5\x88 \xe0\xa4\x95\xe0\xa5\x8d\xe0\xa4\xaf\xe0\xa5\x8b\xe0\xa4\x82\xe0\xa4\x95\xe0\xa4\xbf \xe0\xa4\x85\xe0\xa4\xb8\xe0\xa5\x81\xe0\xa4\xb0\xe0\xa4\x95\xe0\xa5\x8d\xe0\xa4\xb7\xe0\xa4\xbf\xe0\xa4\xa4 \xe0\xa4\x9a\xe0\xa5\x88\xe0\xa4\xa8\xe0\xa4\xb2',
'cache': 'cache',
'change password': 'change password',
'Online examples': '\xe0\xa4\x91\xe0\xa4\xa8\xe0\xa4\xb2\xe0\xa4\xbe\xe0\xa4\x87\xe0\xa4\xa8 \xe0\xa4\x89\xe0\xa4\xa6\xe0\xa4\xbe\xe0\xa4\xb9\xe0\xa4\xb0\xe0\xa4\xa3 \xe0\xa4\x95\xe0\xa5\x87 \xe0\xa4\xb2\xe0\xa4\xbf\xe0\xa4\x8f \xe0\xa4\xaf\xe0\xa4\xb9\xe0\xa4\xbe\xe0\xa4\x81 \xe0\xa4\x95\xe0\xa5\x8d\xe0\xa4\xb2\xe0\xa4\xbf\xe0\xa4\x95 \xe0\xa4\x95\xe0\xa4\xb0\xe0\xa5\x87\xe0\xa4\x82',
'Administrative interface': '\xe0\xa4\xaa\xe0\xa5\x8d\xe0\xa4\xb0\xe0\xa4\xb6\xe0\xa4\xbe\xe0\xa4\xb8\xe0\xa4\xa8\xe0\xa4\xbf\xe0\xa4\x95 \xe0\xa4\x87\xe0\xa4\x82\xe0\xa4\x9f\xe0\xa4\xb0\xe0\xa4\xab\xe0\xa5\x87\xe0\xa4\xb8 \xe0\xa4\x95\xe0\xa5\x87 \xe0\xa4\xb2\xe0\xa4\xbf\xe0\xa4\x8f \xe0\xa4\xaf\xe0\xa4\xb9\xe0\xa4\xbe\xe0\xa4\x81 \xe0\xa4\x95\xe0\xa5\x8d\xe0\xa4\xb2\xe0\xa4\xbf\xe0\xa4\x95 \xe0\xa4\x95\xe0\xa4\xb0\xe0\xa5\x87\xe0\xa4\x82',
'customize me!': '\xe0\xa4\xae\xe0\xa5\x81\xe0\xa4\x9d\xe0\xa5\x87 \xe0\xa4\x85\xe0\xa4\xa8\xe0\xa5\x81\xe0\xa4\x95\xe0\xa5\x82\xe0\xa4\xb2\xe0\xa4\xbf\xe0\xa4\xa4 (\xe0\xa4\x95\xe0\xa4\xb8\xe0\xa5\x8d\xe0\xa4\x9f\xe0\xa4\xae\xe0\xa4\xbe\xe0\xa4\x87\xe0\xa4\x9c\xe0\xa4\xbc) \xe0\xa4\x95\xe0\xa4\xb0\xe0\xa5\x87\xe0\xa4\x82!',
'data uploaded': '\xe0\xa4\xa1\xe0\xa4\xbe\xe0\xa4\x9f\xe0\xa4\xbe \xe0\xa4\x85\xe0\xa4\xaa\xe0\xa4\xb2\xe0\xa5\x8b\xe0\xa4\xa1 \xe0\xa4\xb8\xe0\xa4\xae\xe0\xa5\x8d\xe0\xa4\xaa\xe0\xa4\xa8\xe0\xa5\x8d\xe0\xa4\xa8 ',
'database': '\xe0\xa4\xa1\xe0\xa5\x87\xe0\xa4\x9f\xe0\xa4\xbe\xe0\xa4\xac\xe0\xa5\x87\xe0\xa4\xb8',
'database %s select': '\xe0\xa4\xa1\xe0\xa5\x87\xe0\xa4\x9f\xe0\xa4\xbe\xe0\xa4\xac\xe0\xa5\x87\xe0\xa4\xb8  %s \xe0\xa4\x9a\xe0\xa5\x81\xe0\xa4\xa8\xe0\xa5\x80 \xe0\xa4\xb9\xe0\xa5\x81\xe0\xa4\x88',
'db': 'db',
'design': '\xe0\xa4\xb0\xe0\xa4\x9a\xe0\xa4\xa8\xe0\xa4\xbe \xe0\xa4\x95\xe0\xa4\xb0\xe0\xa5\x87\xe0\xa4\x82',
'done!': '\xe0\xa4\xb9\xe0\xa5\x8b \xe0\xa4\x97\xe0\xa4\xaf\xe0\xa4\xbe!',
'edit profile': 'edit profile',
'export as csv file': 'csv \xe0\xa4\xab\xe0\xa4\xbc\xe0\xa4\xbe\xe0\xa4\x87\xe0\xa4\xb2 \xe0\xa4\x95\xe0\xa5\x87 \xe0\xa4\xb0\xe0\xa5\x82\xe0\xa4\xaa \xe0\xa4\xae\xe0\xa5\x87\xe0\xa4\x82 \xe0\xa4\xa8\xe0\xa4\xbf\xe0\xa4\xb0\xe0\xa5\x8d\xe0\xa4\xaf\xe0\xa4\xbe\xe0\xa4\xa4',
'insert new': '\xe0\xa4\xa8\xe0\xa4\xaf\xe0\xa4\xbe \xe0\xa4\xa1\xe0\xa4\xbe\xe0\xa4\xb2\xe0\xa5\x87\xe0\xa4\x82',
'insert new %s': '\xe0\xa4\xa8\xe0\xa4\xaf\xe0\xa4\xbe   %s  \xe0\xa4\xa1\xe0\xa4\xbe\xe0\xa4\xb2\xe0\xa5\x87\xe0\xa4\x82',
'invalid request': '\xe0\xa4\x85\xe0\xa4\xb5\xe0\xa5\x88\xe0\xa4\xa7 \xe0\xa4\x85\xe0\xa4\xa8\xe0\xa5\x81\xe0\xa4\xb0\xe0\xa5\x8b\xe0\xa4\xa7',
'login': 'login',
'logout': 'logout',
'new record inserted': '\xe0\xa4\xa8\xe0\xa4\xaf\xe0\xa4\xbe \xe0\xa4\xb0\xe0\xa5\x87\xe0\xa4\x95\xe0\xa5\x89\xe0\xa4\xb0\xe0\xa5\x8d\xe0\xa4\xa1 \xe0\xa4\xa1\xe0\xa4\xbe\xe0\xa4\xb2\xe0\xa4\xbe',
'next 100 rows': '\xe0\xa4\x85\xe0\xa4\x97\xe0\xa4\xb2\xe0\xa5\x87 100 \xe0\xa4\xaa\xe0\xa4\x82\xe0\xa4\x95\xe0\xa5\x8d\xe0\xa4\xa4\xe0\xa4\xbf\xe0\xa4\xaf\xe0\xa4\xbe\xe0\xa4\x81',
'or import from csv file': '\xe0\xa4\xaf\xe0\xa4\xbe  csv \xe0\xa4\xab\xe0\xa4\xbc\xe0\xa4\xbe\xe0\xa4\x87\xe0\xa4\xb2 \xe0\xa4\xb8\xe0\xa5\x87 \xe0\xa4\x86\xe0\xa4\xaf\xe0\xa4\xbe\xe0\xa4\xa4',
'previous 100 rows': '\xe0\xa4\xaa\xe0\xa4\xbf\xe0\xa4\x9b\xe0\xa4\xb2\xe0\xa5\x87 100 \xe0\xa4\xaa\xe0\xa4\x82\xe0\xa4\x95\xe0\xa5\x8d\xe0\xa4\xa4\xe0\xa4\xbf\xe0\xa4\xaf\xe0\xa4\xbe\xe0\xa4\x81',
'record': 'record',
'record does not exist': '\xe0\xa4\xb0\xe0\xa4\xbf\xe0\xa4\x95\xe0\xa5\x89\xe0\xa4\xb0\xe0\xa5\x8d\xe0\xa4\xa1 \xe0\xa4\xae\xe0\xa5\x8c\xe0\xa4\x9c\xe0\xa5\x82\xe0\xa4\xa6 \xe0\xa4\xa8\xe0\xa4\xb9\xe0\xa5\x80\xe0\xa4\x82 \xe0\xa4\xb9\xe0\xa5\x88',
'record id': '\xe0\xa4\xb0\xe0\xa4\xbf\xe0\xa4\x95\xe0\xa5\x89\xe0\xa4\xb0\xe0\xa5\x8d\xe0\xa4\xa1 \xe0\xa4\xaa\xe0\xa4\xb9\xe0\xa4\x9a\xe0\xa4\xbe\xe0\xa4\xa8\xe0\xa4\x95\xe0\xa4\xb0\xe0\xa5\x8d\xe0\xa4\xa4\xe0\xa4\xbe (\xe0\xa4\x86\xe0\xa4\x88\xe0\xa4\xa1\xe0\xa5\x80)',
'register': 'register',
'selected': '\xe0\xa4\x9a\xe0\xa5\x81\xe0\xa4\xa8\xe0\xa4\xbe \xe0\xa4\xb9\xe0\xa5\x81\xe0\xa4\x86',
'state': '\xe0\xa4\xb8\xe0\xa5\x8d\xe0\xa4\xa5\xe0\xa4\xbf\xe0\xa4\xa4\xe0\xa4\xbf',
'table': '\xe0\xa4\xa4\xe0\xa4\xbe\xe0\xa4\xb2\xe0\xa4\xbf\xe0\xa4\x95\xe0\xa4\xbe',
'unable to parse csv file': 'csv \xe0\xa4\xab\xe0\xa4\xbc\xe0\xa4\xbe\xe0\xa4\x87\xe0\xa4\xb2 \xe0\xa4\xaa\xe0\xa4\xbe\xe0\xa4\xb0\xe0\xa5\x8d\xe0\xa4\xb8 \xe0\xa4\x95\xe0\xa4\xb0\xe0\xa4\xa8\xe0\xa5\x87 \xe0\xa4\xae\xe0\xa5\x87\xe0\xa4\x82 \xe0\xa4\x85\xe0\xa4\xb8\xe0\xa4\xae\xe0\xa4\xb0\xe0\xa5\x8d\xe0\xa4\xa5',
}


########NEW FILE########
__FILENAME__ = hu-hu
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN',
'%Y-%m-%d': '%Y.%m.%d.',
'%Y-%m-%d %H:%M:%S': '%Y.%m.%d. %H:%M:%S',
'%s rows deleted': '%s sorok t\xc3\xb6rl\xc5\x91dtek',
'%s rows updated': '%s sorok friss\xc3\xadt\xc5\x91dtek',
'Available databases and tables': 'El\xc3\xa9rhet\xc5\x91 adatb\xc3\xa1zisok \xc3\xa9s t\xc3\xa1bl\xc3\xa1k',
'Cannot be empty': 'Nem lehet \xc3\xbcres',
'Check to delete': 'T\xc3\xb6rl\xc3\xa9shez v\xc3\xa1laszd ki',
'Client IP': 'Client IP',
'Controller': 'Controller',
'Copyright': 'Copyright',
'Current request': 'Jelenlegi lek\xc3\xa9rdez\xc3\xa9s',
'Current response': 'Jelenlegi v\xc3\xa1lasz',
'Current session': 'Jelenlegi folyamat',
'DB Model': 'DB Model',
'Database': 'Adatb\xc3\xa1zis',
'Delete:': 'T\xc3\xb6r\xc3\xb6l:',
'Description': 'Description',
'E-mail': 'E-mail',
'Edit': 'Szerkeszt',
'Edit This App': 'Alkalmaz\xc3\xa1st szerkeszt',
'Edit current record': 'Aktu\xc3\xa1lis bejegyz\xc3\xa9s szerkeszt\xc3\xa9se',
'First name': 'First name',
'Group ID': 'Group ID',
'Hello World': 'Hello Vil\xc3\xa1g',
'Import/Export': 'Import/Export',
'Index': 'Index',
'Internal State': 'Internal State',
'Invalid Query': 'Hib\xc3\xa1s lek\xc3\xa9rdez\xc3\xa9s',
'Invalid email': 'Invalid email',
'Last name': 'Last name',
'Layout': 'Szerkezet',
'Main Menu': 'F\xc5\x91men\xc3\xbc',
'Menu Model': 'Men\xc3\xbc model',
'Name': 'Name',
'New Record': '\xc3\x9aj bejegyz\xc3\xa9s',
'No databases in this application': 'Nincs adatb\xc3\xa1zis ebben az alkalmaz\xc3\xa1sban',
'Origin': 'Origin',
'Password': 'Password',
'Powered by': 'Powered by',
'Query:': 'Lek\xc3\xa9rdez\xc3\xa9s:',
'Record ID': 'Record ID',
'Registration key': 'Registration key',
'Reset Password key': 'Reset Password key',
'Role': 'Role',
'Rows in table': 'Sorok a t\xc3\xa1bl\xc3\xa1ban',
'Rows selected': 'Kiv\xc3\xa1lasztott sorok',
'Stylesheet': 'Stylesheet',
'Sure you want to delete this object?': 'Biztos t\xc3\xb6rli ezt az objektumot?',
'Table name': 'Table name',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.',
'Timestamp': 'Timestamp',
'Update:': 'Friss\xc3\xadt:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.',
'User ID': 'User ID',
'View': 'N\xc3\xa9zet',
'Welcome %s': 'Welcome %s',
'Welcome to web2py': 'Isten hozott a web2py-ban',
'appadmin is disabled because insecure channel': 'az appadmin a biztons\xc3\xa1gtalan csatorna miatt letiltva',
'cache': 'gyors\xc3\xadt\xc3\xb3t\xc3\xa1r',
'change password': 'jelsz\xc3\xb3 megv\xc3\xa1ltoztat\xc3\xa1sa',
'Online examples': 'online p\xc3\xa9ld\xc3\xa1k\xc3\xa9rt kattints ide',
'Administrative interface': 'az adminisztr\xc3\xa1ci\xc3\xb3s fel\xc3\xbclet\xc3\xa9rt kattints ide',
'customize me!': 'v\xc3\xa1ltoztass meg!',
'data uploaded': 'adat felt\xc3\xb6ltve',
'database': 'adatb\xc3\xa1zis',
'database %s select': 'adatb\xc3\xa1zis %s kiv\xc3\xa1laszt\xc3\xa1s',
'db': 'db',
'design': 'design',
'done!': 'k\xc3\xa9sz!',
'edit profile': 'profil szerkeszt\xc3\xa9se',
'export as csv file': 'export\xc3\xa1l csv f\xc3\xa1jlba',
'insert new': '\xc3\xbaj beilleszt\xc3\xa9se',
'insert new %s': '\xc3\xbaj beilleszt\xc3\xa9se %s',
'invalid request': 'hib\xc3\xa1s k\xc3\xa9r\xc3\xa9s',
'login': 'bel\xc3\xa9p',
'logout': 'kil\xc3\xa9p',
'lost password': 'elveszett jelsz\xc3\xb3',
'new record inserted': '\xc3\xbaj bejegyz\xc3\xa9s felv\xc3\xa9ve',
'next 100 rows': 'k\xc3\xb6vetkez\xc5\x91 100 sor',
'or import from csv file': 'vagy bet\xc3\xb6lt\xc3\xa9s csv f\xc3\xa1jlb\xc3\xb3l',
'previous 100 rows': 'el\xc5\x91z\xc5\x91 100 sor',
'record': 'bejegyz\xc3\xa9s',
'record does not exist': 'bejegyz\xc3\xa9s nem l\xc3\xa9tezik',
'record id': 'bejegyz\xc3\xa9s id',
'register': 'regisztr\xc3\xa1ci\xc3\xb3',
'selected': 'kiv\xc3\xa1lasztott',
'state': '\xc3\xa1llapot',
'table': 't\xc3\xa1bla',
'unable to parse csv file': 'nem lehet a csv f\xc3\xa1jlt beolvasni',
}


########NEW FILE########
__FILENAME__ = hu
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN',
'%Y-%m-%d': '%Y.%m.%d.',
'%Y-%m-%d %H:%M:%S': '%Y.%m.%d. %H:%M:%S',
'%s rows deleted': '%s sorok t\xc3\xb6rl\xc5\x91dtek',
'%s rows updated': '%s sorok friss\xc3\xadt\xc5\x91dtek',
'Available databases and tables': 'El\xc3\xa9rhet\xc5\x91 adatb\xc3\xa1zisok \xc3\xa9s t\xc3\xa1bl\xc3\xa1k',
'Cannot be empty': 'Nem lehet \xc3\xbcres',
'Check to delete': 'T\xc3\xb6rl\xc3\xa9shez v\xc3\xa1laszd ki',
'Client IP': 'Client IP',
'Controller': 'Controller',
'Copyright': 'Copyright',
'Current request': 'Jelenlegi lek\xc3\xa9rdez\xc3\xa9s',
'Current response': 'Jelenlegi v\xc3\xa1lasz',
'Current session': 'Jelenlegi folyamat',
'DB Model': 'DB Model',
'Database': 'Adatb\xc3\xa1zis',
'Delete:': 'T\xc3\xb6r\xc3\xb6l:',
'Description': 'Description',
'E-mail': 'E-mail',
'Edit': 'Szerkeszt',
'Edit This App': 'Alkalmaz\xc3\xa1st szerkeszt',
'Edit current record': 'Aktu\xc3\xa1lis bejegyz\xc3\xa9s szerkeszt\xc3\xa9se',
'First name': 'First name',
'Group ID': 'Group ID',
'Hello World': 'Hello Vil\xc3\xa1g',
'Import/Export': 'Import/Export',
'Index': 'Index',
'Internal State': 'Internal State',
'Invalid Query': 'Hib\xc3\xa1s lek\xc3\xa9rdez\xc3\xa9s',
'Invalid email': 'Invalid email',
'Last name': 'Last name',
'Layout': 'Szerkezet',
'Main Menu': 'F\xc5\x91men\xc3\xbc',
'Menu Model': 'Men\xc3\xbc model',
'Name': 'Name',
'New Record': '\xc3\x9aj bejegyz\xc3\xa9s',
'No databases in this application': 'Nincs adatb\xc3\xa1zis ebben az alkalmaz\xc3\xa1sban',
'Origin': 'Origin',
'Password': 'Password',
'Powered by': 'Powered by',
'Query:': 'Lek\xc3\xa9rdez\xc3\xa9s:',
'Record ID': 'Record ID',
'Registration key': 'Registration key',
'Reset Password key': 'Reset Password key',
'Role': 'Role',
'Rows in table': 'Sorok a t\xc3\xa1bl\xc3\xa1ban',
'Rows selected': 'Kiv\xc3\xa1lasztott sorok',
'Stylesheet': 'Stylesheet',
'Sure you want to delete this object?': 'Biztos t\xc3\xb6rli ezt az objektumot?',
'Table name': 'Table name',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.',
'Timestamp': 'Timestamp',
'Update:': 'Friss\xc3\xadt:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.',
'User ID': 'User ID',
'View': 'N\xc3\xa9zet',
'Welcome %s': 'Welcome %s',
'Welcome to web2py': 'Isten hozott a web2py-ban',
'appadmin is disabled because insecure channel': 'az appadmin a biztons\xc3\xa1gtalan csatorna miatt letiltva',
'cache': 'gyors\xc3\xadt\xc3\xb3t\xc3\xa1r',
'change password': 'jelsz\xc3\xb3 megv\xc3\xa1ltoztat\xc3\xa1sa',
'Online examples': 'online p\xc3\xa9ld\xc3\xa1k\xc3\xa9rt kattints ide',
'Administrative interface': 'az adminisztr\xc3\xa1ci\xc3\xb3s fel\xc3\xbclet\xc3\xa9rt kattints ide',
'customize me!': 'v\xc3\xa1ltoztass meg!',
'data uploaded': 'adat felt\xc3\xb6ltve',
'database': 'adatb\xc3\xa1zis',
'database %s select': 'adatb\xc3\xa1zis %s kiv\xc3\xa1laszt\xc3\xa1s',
'db': 'db',
'design': 'design',
'done!': 'k\xc3\xa9sz!',
'edit profile': 'profil szerkeszt\xc3\xa9se',
'export as csv file': 'export\xc3\xa1l csv f\xc3\xa1jlba',
'insert new': '\xc3\xbaj beilleszt\xc3\xa9se',
'insert new %s': '\xc3\xbaj beilleszt\xc3\xa9se %s',
'invalid request': 'hib\xc3\xa1s k\xc3\xa9r\xc3\xa9s',
'login': 'bel\xc3\xa9p',
'logout': 'kil\xc3\xa9p',
'lost password': 'elveszett jelsz\xc3\xb3',
'new record inserted': '\xc3\xbaj bejegyz\xc3\xa9s felv\xc3\xa9ve',
'next 100 rows': 'k\xc3\xb6vetkez\xc5\x91 100 sor',
'or import from csv file': 'vagy bet\xc3\xb6lt\xc3\xa9s csv f\xc3\xa1jlb\xc3\xb3l',
'previous 100 rows': 'el\xc5\x91z\xc5\x91 100 sor',
'record': 'bejegyz\xc3\xa9s',
'record does not exist': 'bejegyz\xc3\xa9s nem l\xc3\xa9tezik',
'record id': 'bejegyz\xc3\xa9s id',
'register': 'regisztr\xc3\xa1ci\xc3\xb3',
'selected': 'kiv\xc3\xa1lasztott',
'state': '\xc3\xa1llapot',
'table': 't\xc3\xa1bla',
'unable to parse csv file': 'nem lehet a csv f\xc3\xa1jlt beolvasni',
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
'Administrative interface': 'Interfaccia amministrativa',
'Available databases and tables': 'Database e tabelle disponibili',
'Cannot be empty': 'Non può essere vuoto',
'Check to delete': 'Seleziona per cancellare',
'Client IP': 'Client IP',
'Controller': 'Controller',
'Copyright': 'Copyright',
'Current request': 'Richiesta (request) corrente',
'Current response': 'Risposta (response) corrente',
'Current session': 'Sessione (session) corrente',
'DB Model': 'Modello di DB',
'Database': 'Database',
'Delete': 'Delete',
'Delete:': 'Cancella:',
'Description': 'Descrizione',
'Documentation': 'Documentazione',
'E-mail': 'E-mail',
'Edit': 'Modifica',
'Edit This App': 'Modifica questa applicazione',
'Edit current record': 'Modifica record corrente',
'First name': 'Nome',
'Group ID': 'ID Gruppo',
'Hello': 'Hello',
'Hello World': 'Salve Mondo',
'Hello World in a flash!': 'Salve Mondo in un flash!',
'Import/Export': 'Importa/Esporta',
'Index': 'Indice',
'Internal State': 'Stato interno',
'Invalid Query': 'Richiesta (query) non valida',
'Invalid email': 'Email non valida',
'Last name': 'Cognome',
'Layout': 'Layout',
'Main Menu': 'Menu principale',
'Menu Model': 'Menu Modelli',
'Name': 'Nome',
'New Record': 'Nuovo elemento (record)',
'No databases in this application': 'Nessun database presente in questa applicazione',
'Online examples': 'Vedere gli esempi',
'Origin': 'Origine',
'Password': 'Password',
'Powered by': 'Powered by',
'Query:': 'Richiesta (query):',
'Record ID': 'Record ID',
'Registration key': 'Chiave di Registazione',
'Reset Password key': 'Resetta chiave Password ',
'Role': 'Ruolo',
'Rows in table': 'Righe nella tabella',
'Rows selected': 'Righe selezionate',
'Stylesheet': 'Foglio di stile (stylesheet)',
'Sure you want to delete this object?': 'Vuoi veramente cancellare questo oggetto?',
'Table name': 'Nome tabella',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'La richiesta (query) è una condizione come ad esempio  "db.tabella1.campo1==\'valore\'". Una condizione come "db.tabella1.campo1==db.tabella2.campo2" produce un "JOIN" SQL.',
'The output of the file is a dictionary that was rendered by the view': 'L\'output del file è un "dictionary" che è stato visualizzato dalla vista',
'This is a copy of the scaffolding application': "Questa è una copia dell'applicazione di base (scaffold)",
'Timestamp': 'Ora (timestamp)',
'Update:': 'Aggiorna:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Per costruire richieste (query) più complesse si usano (...)&(...) come "e" (AND), (...)|(...) come "o" (OR), e ~(...) come negazione (NOT).',
'User ID': 'ID Utente',
'View': 'Vista',
'Welcome %s': 'Benvenuto %s',
'Welcome to web2py': 'Benvenuto su web2py',
'Which called the function': 'che ha chiamato la funzione',
'You are successfully running web2py': 'Stai eseguendo web2py con successo',
'You can modify this application and adapt it to your needs': 'Puoi modificare questa applicazione adattandola alle tue necessità',
'You visited the url': "Hai visitato l'URL",
'appadmin is disabled because insecure channel': 'Amministrazione (appadmin) disabilitata: comunicazione non sicura',
'cache': 'cache',
'change password': 'Cambia password',
'customize me!': 'Personalizzami!',
'data uploaded': 'dati caricati',
'database': 'database',
'database %s select': 'database %s select',
'db': 'db',
'design': 'progetta',
'done!': 'fatto!',
'edit profile': 'modifica profilo',
'export as csv file': 'esporta come file CSV',
'hello': 'hello',
'hello world': 'salve mondo',
'insert new': 'inserisci nuovo',
'insert new %s': 'inserisci nuovo %s',
'invalid request': 'richiesta non valida',
'located in the file': 'presente nel file',
'login': 'accesso',
'logout': 'uscita',
'lost password?': 'dimenticato la password?',
'new record inserted': 'nuovo record inserito',
'next 100 rows': 'prossime 100 righe',
'not authorized': 'non autorizzato',
'or import from csv file': 'oppure importa da file CSV',
'previous 100 rows': '100 righe precedenti',
'record': 'record',
'record does not exist': 'il record non esiste',
'record id': 'record id',
'register': 'registrazione',
'selected': 'selezionato',
'state': 'stato',
'table': 'tabella',
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
'Administrative interface': 'Interfaccia amministrativa',
'Available databases and tables': 'Database e tabelle disponibili',
'Cannot be empty': 'Non può essere vuoto',
'Check to delete': 'Seleziona per cancellare',
'Client IP': 'Client IP',
'Controller': 'Controller',
'Copyright': 'Copyright',
'Current request': 'Richiesta (request) corrente',
'Current response': 'Risposta (response) corrente',
'Current session': 'Sessione (session) corrente',
'DB Model': 'Modello di DB',
'Database': 'Database',
'Delete': 'Delete',
'Delete:': 'Cancella:',
'Description': 'Descrizione',
'Documentation': 'Documentazione',
'E-mail': 'E-mail',
'Edit': 'Modifica',
'Edit This App': 'Modifica questa applicazione',
'Edit current record': 'Modifica record corrente',
'First name': 'Nome',
'Group ID': 'ID Gruppo',
'Hello World': 'Salve Mondo',
'Hello World in a flash!': 'Salve Mondo in un flash!',
'Import/Export': 'Importa/Esporta',
'Index': 'Indice',
'Internal State': 'Stato interno',
'Invalid Query': 'Richiesta (query) non valida',
'Invalid email': 'Email non valida',
'Last name': 'Cognome',
'Layout': 'Layout',
'Main Menu': 'Menu principale',
'Menu Model': 'Menu Modelli',
'Name': 'Nome',
'New Record': 'Nuovo elemento (record)',
'No databases in this application': 'Nessun database presente in questa applicazione',
'Online examples': 'Vedere gli esempi',
'Origin': 'Origine',
'Password': 'Password',
'Powered by': 'Powered by',
'Query:': 'Richiesta (query):',
'Record ID': 'Record ID',
'Registration key': 'Chiave di Registazione',
'Reset Password key': 'Resetta chiave Password ',
'Role': 'Ruolo',
'Rows in table': 'Righe nella tabella',
'Rows selected': 'Righe selezionate',
'Stylesheet': 'Foglio di stile (stylesheet)',
'Sure you want to delete this object?': 'Vuoi veramente cancellare questo oggetto?',
'Table name': 'Nome tabella',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'La richiesta (query) è una condizione come ad esempio  "db.tabella1.campo1==\'valore\'". Una condizione come "db.tabella1.campo1==db.tabella2.campo2" produce un "JOIN" SQL.',
'The output of the file is a dictionary that was rendered by the view': 'L\'output del file è un "dictionary" che è stato visualizzato dalla vista',
'This is a copy of the scaffolding application': "Questa è una copia dell'applicazione di base (scaffold)",
'Timestamp': 'Ora (timestamp)',
'Update': 'Update',
'Update:': 'Aggiorna:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Per costruire richieste (query) più complesse si usano (...)&(...) come "e" (AND), (...)|(...) come "o" (OR), e ~(...) come negazione (NOT).',
'User ID': 'ID Utente',
'View': 'Vista',
'Welcome %s': 'Benvenuto %s',
'Welcome to web2py': 'Benvenuto su web2py',
'Which called the function': 'che ha chiamato la funzione',
'You are successfully running web2py': 'Stai eseguendo web2py con successo',
'You can modify this application and adapt it to your needs': 'Puoi modificare questa applicazione adattandola alle tue necessità',
'You visited the url': "Hai visitato l'URL",
'appadmin is disabled because insecure channel': 'Amministrazione (appadmin) disabilitata: comunicazione non sicura',
'cache': 'cache',
'change password': 'Cambia password',
'customize me!': 'Personalizzami!',
'data uploaded': 'dati caricati',
'database': 'database',
'database %s select': 'database %s select',
'db': 'db',
'design': 'progetta',
'done!': 'fatto!',
'edit profile': 'modifica profilo',
'export as csv file': 'esporta come file CSV',
'hello': 'hello',
'hello world': 'salve mondo',
'insert new': 'inserisci nuovo',
'insert new %s': 'inserisci nuovo %s',
'invalid request': 'richiesta non valida',
'located in the file': 'presente nel file',
'login': 'accesso',
'logout': 'uscita',
'lost password?': 'dimenticato la password?',
'new record inserted': 'nuovo record inserito',
'next 100 rows': 'prossime 100 righe',
'not authorized': 'non autorizzato',
'or import from csv file': 'oppure importa da file CSV',
'previous 100 rows': '100 righe precedenti',
'record': 'record',
'record does not exist': 'il record non esiste',
'record id': 'record id',
'register': 'registrazione',
'selected': 'selezionato',
'state': 'stato',
'table': 'tabella',
'unable to parse csv file': 'non riesco a decodificare questo file CSV',
}


########NEW FILE########
__FILENAME__ = pl-pl
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"Uaktualnij" jest dodatkowym wyra\xc5\xbceniem postaci "pole1=\'nowawarto\xc5\x9b\xc4\x87\'". Nie mo\xc5\xbcesz uaktualni\xc4\x87 lub usun\xc4\x85\xc4\x87 wynik\xc3\xb3w z JOIN:',
'%Y-%m-%d': '%Y-%m-%d',
'%Y-%m-%d %H:%M:%S': '%Y-%m-%d %H:%M:%S',
'%s rows deleted': 'Wierszy usuni\xc4\x99tych: %s',
'%s rows updated': 'Wierszy uaktualnionych: %s',
'Available databases and tables': 'Dost\xc4\x99pne bazy danych i tabele',
'Cannot be empty': 'Nie mo\xc5\xbce by\xc4\x87 puste',
'Change Password': 'Change Password',
'Check to delete': 'Zaznacz aby usun\xc4\x85\xc4\x87',
'Controller': 'Controller',
'Copyright': 'Copyright',
'Current request': 'Aktualne \xc5\xbc\xc4\x85danie',
'Current response': 'Aktualna odpowied\xc5\xba',
'Current session': 'Aktualna sesja',
'DB Model': 'DB Model',
'Database': 'Database',
'Delete:': 'Usu\xc5\x84:',
'Edit': 'Edit',
'Edit Profile': 'Edit Profile',
'Edit This App': 'Edit This App',
'Edit current record': 'Edytuj aktualny rekord',
'Hello World': 'Witaj \xc5\x9awiecie',
'Import/Export': 'Importuj/eksportuj',
'Index': 'Index',
'Internal State': 'Stan wewn\xc4\x99trzny',
'Invalid Query': 'B\xc5\x82\xc4\x99dne zapytanie',
'Layout': 'Layout',
'Login': 'Zaloguj',
'Logout': 'Logout',
'Lost Password': 'Przypomnij has\xc5\x82o',
'Main Menu': 'Main Menu',
'Menu Model': 'Menu Model',
'New Record': 'Nowy rekord',
'No databases in this application': 'Brak baz danych w tej aplikacji',
'Powered by': 'Powered by',
'Query:': 'Zapytanie:',
'Register': 'Zarejestruj',
'Rows in table': 'Wiersze w tabeli',
'Rows selected': 'Wybrane wiersze',
'Stylesheet': 'Stylesheet',
'Sure you want to delete this object?': 'Czy na pewno chcesz usun\xc4\x85\xc4\x87 ten obiekt?',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': '"Zapytanie" jest warunkiem postaci "db.tabela1.pole1==\'warto\xc5\x9b\xc4\x87\'". Takie co\xc5\x9b jak "db.tabela1.pole1==db.tabela2.pole2" oznacza SQL JOIN.',
'Update:': 'Uaktualnij:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'U\xc5\xbcyj (...)&(...) jako AND, (...)|(...) jako OR oraz ~(...)  jako NOT do tworzenia bardziej skomplikowanych zapyta\xc5\x84.',
'View': 'View',
'Welcome %s': 'Welcome %s',
'Welcome to web2py': 'Witaj w web2py',
'appadmin is disabled because insecure channel': 'appadmin is disabled because insecure channel',
'cache': 'cache',
'change password': 'change password',
'Online examples': 'Kliknij aby przej\xc5\x9b\xc4\x87 do interaktywnych przyk\xc5\x82ad\xc3\xb3w',
'Administrative interface': 'Kliknij aby przej\xc5\x9b\xc4\x87 do panelu administracyjnego',
'customize me!': 'dostosuj mnie!',
'data uploaded': 'dane wys\xc5\x82ane',
'database': 'baza danych',
'database %s select': 'wyb\xc3\xb3r z bazy danych %s',
'db': 'baza danych',
'design': 'projektuj',
'done!': 'zrobione!',
'edit profile': 'edit profile',
'export as csv file': 'eksportuj jako plik csv',
'insert new': 'wstaw nowy rekord tabeli',
'insert new %s': 'wstaw nowy rekord do tabeli %s',
'invalid request': 'B\xc5\x82\xc4\x99dne \xc5\xbc\xc4\x85danie',
'login': 'login',
'logout': 'logout',
'new record inserted': 'nowy rekord zosta\xc5\x82 wstawiony',
'next 100 rows': 'nast\xc4\x99pne 100 wierszy',
'or import from csv file': 'lub zaimportuj z pliku csv',
'previous 100 rows': 'poprzednie 100 wierszy',
'record': 'record',
'record does not exist': 'rekord nie istnieje',
'record id': 'id rekordu',
'register': 'register',
'selected': 'wybranych',
'state': 'stan',
'table': 'tabela',
'unable to parse csv file': 'nie mo\xc5\xbcna sparsowa\xc4\x87 pliku csv',
}


########NEW FILE########
__FILENAME__ = pl
# coding: utf8
{
'"update" is an optional expression like "field1=\'newvalue\'". You cannot update or delete the results of a JOIN': '"Uaktualnij" jest dodatkowym wyra\xc5\xbceniem postaci "pole1=\'nowawarto\xc5\x9b\xc4\x87\'". Nie mo\xc5\xbcesz uaktualni\xc4\x87 lub usun\xc4\x85\xc4\x87 wynik\xc3\xb3w z JOIN:',
'%Y-%m-%d': '%Y-%m-%d',
'%Y-%m-%d %H:%M:%S': '%Y-%m-%d %H:%M:%S',
'%s rows deleted': 'Wierszy usuni\xc4\x99tych: %s',
'%s rows updated': 'Wierszy uaktualnionych: %s',
'Authentication': 'Uwierzytelnienie',
'Available databases and tables': 'Dost\xc4\x99pne bazy danych i tabele',
'Cannot be empty': 'Nie mo\xc5\xbce by\xc4\x87 puste',
'Change Password': 'Zmie\xc5\x84 has\xc5\x82o',
'Check to delete': 'Zaznacz aby usun\xc4\x85\xc4\x87',
'Check to delete:': 'Zaznacz aby usun\xc4\x85\xc4\x87:',
'Client IP': 'IP klienta',
'Controller': 'Kontroler',
'Copyright': 'Copyright',
'Current request': 'Aktualne \xc5\xbc\xc4\x85danie',
'Current response': 'Aktualna odpowied\xc5\xba',
'Current session': 'Aktualna sesja',
'DB Model': 'Model bazy danych',
'Database': 'Baza danych',
'Delete:': 'Usu\xc5\x84:',
'Description': 'Opis',
'E-mail': 'Adres e-mail',
'Edit': 'Edycja',
'Edit Profile': 'Edytuj profil',
'Edit This App': 'Edytuj t\xc4\x99 aplikacj\xc4\x99',
'Edit current record': 'Edytuj obecny rekord',
'First name': 'Imi\xc4\x99',
'Function disabled': 'Funkcja wy\xc5\x82\xc4\x85czona',
'Group ID': 'ID grupy',
'Hello World': 'Witaj \xc5\x9awiecie',
'Import/Export': 'Importuj/eksportuj',
'Index': 'Indeks',
'Internal State': 'Stan wewn\xc4\x99trzny',
'Invalid Query': 'B\xc5\x82\xc4\x99dne zapytanie',
'Invalid email': 'B\xc5\x82\xc4\x99dny adres email',
'Last name': 'Nazwisko',
'Layout': 'Uk\xc5\x82ad',
'Login': 'Zaloguj',
'Logout': 'Wyloguj',
'Lost Password': 'Przypomnij has\xc5\x82o',
'Main Menu': 'Menu g\xc5\x82\xc3\xb3wne',
'Menu Model': 'Model menu',
'Name': 'Nazwa',
'New Record': 'Nowy rekord',
'No databases in this application': 'Brak baz danych w tej aplikacji',
'Origin': '\xc5\xb9r\xc3\xb3d\xc5\x82o',
'Password': 'Has\xc5\x82o',
"Password fields don't match": 'Pola has\xc5\x82a nie s\xc4\x85 zgodne ze sob\xc4\x85',
'Powered by': 'Zasilane przez',
'Query:': 'Zapytanie:',
'Record ID': 'ID rekordu',
'Register': 'Zarejestruj',
'Registration key': 'Klucz rejestracji',
'Role': 'Rola',
'Rows in table': 'Wiersze w tabeli',
'Rows selected': 'Wybrane wiersze',
'Stylesheet': 'Arkusz styl\xc3\xb3w',
'Submit': 'Wy\xc5\x9blij',
'Sure you want to delete this object?': 'Czy na pewno chcesz usun\xc4\x85\xc4\x87 ten obiekt?',
'Table name': 'Nazwa tabeli',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': '"Zapytanie" jest warunkiem postaci "db.tabela1.pole1==\'warto\xc5\x9b\xc4\x87\'". Takie co\xc5\x9b jak "db.tabela1.pole1==db.tabela2.pole2" oznacza SQL JOIN.',
'Timestamp': 'Znacznik czasu',
'Update:': 'Uaktualnij:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'U\xc5\xbcyj (...)&(...) jako AND, (...)|(...) jako OR oraz ~(...)  jako NOT do tworzenia bardziej skomplikowanych zapyta\xc5\x84.',
'User %(id)s Registered': 'U\xc5\xbcytkownik %(id)s zosta\xc5\x82 zarejestrowany',
'User ID': 'ID u\xc5\xbcytkownika',
'Verify Password': 'Potwierd\xc5\xba has\xc5\x82o',
'View': 'Widok',
'Welcome %s': 'Welcome %s',
'Welcome to web2py': 'Witaj w web2py',
'appadmin is disabled because insecure channel': 'administracja aplikacji wy\xc5\x82\xc4\x85czona z powodu braku bezpiecznego po\xc5\x82\xc4\x85czenia',
'cache': 'cache',
'change password': 'change password',
'Online examples': 'Kliknij aby przej\xc5\x9b\xc4\x87 do interaktywnych przyk\xc5\x82ad\xc3\xb3w',
'Administrative interface': 'Kliknij aby przej\xc5\x9b\xc4\x87 do panelu administracyjnego',
'customize me!': 'dostosuj mnie!',
'data uploaded': 'dane wys\xc5\x82ane',
'database': 'baza danych',
'database %s select': 'wyb\xc3\xb3r z bazy danych %s',
'db': 'baza danych',
'design': 'projektuj',
'done!': 'zrobione!',
'edit profile': 'edit profile',
'export as csv file': 'eksportuj jako plik csv',
'insert new': 'wstaw nowy rekord tabeli',
'insert new %s': 'wstaw nowy rekord do tabeli %s',
'invalid request': 'B\xc5\x82\xc4\x99dne \xc5\xbc\xc4\x85danie',
'login': 'login',
'logout': 'logout',
'new record inserted': 'nowy rekord zosta\xc5\x82 wstawiony',
'next 100 rows': 'nast\xc4\x99pne 100 wierszy',
'or import from csv file': 'lub zaimportuj z pliku csv',
'previous 100 rows': 'poprzednie 100 wierszy',
'record': 'rekord',
'record does not exist': 'rekord nie istnieje',
'record id': 'id rekordu',
'register': 'register',
'selected': 'wybranych',
'state': 'stan',
'table': 'tabela',
'unable to parse csv file': 'nie mo\xc5\xbcna sparsowa\xc4\x87 pliku csv',
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
'Access Control': 'Access Control',
'Ajax Recipes': 'Ajax Recipes',
'Available databases and tables': 'Bancos de dados e tabelas disponíveis',
'Buy this book': 'Buy this book',
'Cannot be empty': 'Não pode ser vazio',
'Check to delete': 'Marque para apagar',
'Client IP': 'Client IP',
'Community': 'Community',
'Controller': 'Controlador',
'Copyright': 'Copyright',
'Current request': 'Requisição atual',
'Current response': 'Resposta atual',
'Current session': 'Sessão atual',
'DB Model': 'Modelo BD',
'Database': 'Banco de dados',
'Delete:': 'Apagar:',
'Demo': 'Demo',
'Deployment Recipes': 'Deployment Recipes',
'Description': 'Description',
'Documentation': 'Documentation',
'Download': 'Download',
'E-mail': 'E-mail',
'Edit': 'Editar',
'Edit This App': 'Edit This App',
'Edit current record': 'Editar o registro atual',
'Errors': 'Errors',
'FAQ': 'FAQ',
'First name': 'First name',
'Forms and Validators': 'Forms and Validators',
'Free Applications': 'Free Applications',
'Group ID': 'Group ID',
'Groups': 'Groups',
'Hello World': 'Olá Mundo',
'Home': 'Home',
'Import/Export': 'Importar/Exportar',
'Index': 'Início',
'Internal State': 'Estado Interno',
'Introduction': 'Introduction',
'Invalid Query': 'Consulta Inválida',
'Invalid email': 'Invalid email',
'Last name': 'Last name',
'Layout': 'Layout',
'Layouts': 'Layouts',
'Live chat': 'Live chat',
'Login': 'Autentique-se',
'Lost Password': 'Esqueceu sua senha?',
'Main Menu': 'Menu Principal',
'Menu Model': 'Modelo de Menu',
'Name': 'Name',
'New Record': 'Novo Registro',
'No databases in this application': 'Sem bancos de dados nesta aplicação',
'Origin': 'Origin',
'Other Recipes': 'Other Recipes',
'Overview': 'Overview',
'Password': 'Password',
'Plugins': 'Plugins',
'Powered by': 'Powered by',
'Preface': 'Preface',
'Python': 'Python',
'Query:': 'Consulta:',
'Quick Examples': 'Quick Examples',
'Recipes': 'Recipes',
'Record ID': 'Record ID',
'Register': 'Registre-se',
'Registration key': 'Registration key',
'Reset Password key': 'Reset Password key',
'Resources': 'Resources',
'Role': 'Role',
'Rows in table': 'Linhas na tabela',
'Rows selected': 'Linhas selecionadas',
'Semantic': 'Semantic',
'Services': 'Services',
'Stylesheet': 'Stylesheet',
'Support': 'Support',
'Sure you want to delete this object?': 'Está certo(a) que deseja apagar esse objeto ?',
'Table name': 'Table name',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'Uma "consulta" é uma condição como "db.tabela1.campo1==\'valor\'". Expressões como "db.tabela1.campo1==db.tabela2.campo2" resultam em um JOIN SQL.',
'The Core': 'The Core',
'The Views': 'The Views',
'The output of the file is a dictionary that was rendered by the view': 'The output of the file is a dictionary that was rendered by the view',
'This App': 'This App',
'This is a copy of the scaffolding application': 'This is a copy of the scaffolding application',
'Timestamp': 'Timestamp',
'Twitter': 'Twitter',
'Update:': 'Atualizar:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Use (...)&(...) para AND, (...)|(...) para OR, e ~(...)  para NOT para construir consultas mais complexas.',
'User ID': 'User ID',
'User Voice': 'User Voice',
'Videos': 'Videos',
'View': 'Visualização',
'Web2py': 'Web2py',
'Welcome': 'Welcome',
'Welcome %s': 'Vem vindo %s',
'Welcome to web2py': 'Bem vindo ao web2py',
'Which called the function': 'Which called the function',
'You are successfully running web2py': 'You are successfully running web2py',
'You are successfully running web2py.': 'You are successfully running web2py.',
'You can modify this application and adapt it to your needs': 'You can modify this application and adapt it to your needs',
'You visited the url': 'You visited the url',
'appadmin is disabled because insecure channel': 'Administração desativada devido ao canal inseguro',
'cache': 'cache',
'change password': 'modificar senha',
'Online examples': 'Alguns exemplos',
'Administrative interface': 'Interface administrativa',
'customize me!': 'Personalize-me!',
'data uploaded': 'dados enviados',
'database': 'banco de dados',
'database %s select': 'Selecionar banco de dados %s',
'db': 'bd',
'design': 'design',
'Documentation': 'Documentation',
'done!': 'concluído!',
'edit profile': 'editar perfil',
'export as csv file': 'exportar como um arquivo csv',
'insert new': 'inserir novo',
'insert new %s': 'inserir novo %s',
'invalid request': 'requisição inválida',
'located in the file': 'located in the file',
'login': 'Entrar',
'logout': 'Sair',
'lost password?': 'lost password?',
'new record inserted': 'novo registro inserido',
'next 100 rows': 'próximas 100 linhas',
'or import from csv file': 'ou importar de um arquivo csv',
'previous 100 rows': '100 linhas anteriores',
'record': 'registro',
'record does not exist': 'registro não existe',
'record id': 'id do registro',
'register': 'Registre-se',
'selected': 'selecionado',
'state': 'estado',
'table': 'tabela',
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
'Author Reference Auth User': 'Author Reference Auth User',
'Author Reference Auth User.username': 'Author Reference Auth User.username',
'Available databases and tables': 'bases de dados e tabelas disponíveis',
'Cannot be empty': 'não pode ser vazio',
'Category Create': 'Category Create',
'Category Select': 'Category Select',
'Check to delete': 'seleccione para eliminar',
'Comment Create': 'Comment Create',
'Comment Select': 'Comment Select',
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
'Delete:': 'Eliminar:',
'Edit': 'Editar',
'Edit This App': 'Edite esta aplicação',
'Edit current record': 'Edição de registo currente',
'Email': 'Email',
'First Name': 'First Name',
'For %s #%s': 'For %s #%s',
'Hello World': 'Olá Mundo',
'Import/Export': 'Importar/Exportar',
'Index': 'Índice',
'Internal State': 'Estado interno',
'Invalid Query': 'Consulta Inválida',
'Last Name': 'Last Name',
'Layout': 'Esboço',
'Main Menu': 'Menu Principal',
'Menu Model': 'Menu do Modelo',
'Modified By': 'Modified By',
'Modified On': 'Modified On',
'Name': 'Name',
'New Record': 'Novo Registo',
'No Data': 'No Data',
'No databases in this application': 'Não há bases de dados nesta aplicação',
'Password': 'Password',
'Post Create': 'Post Create',
'Post Select': 'Post Select',
'Powered by': 'Suportado por',
'Query:': 'Interrogação:',
'Replyto Reference Post': 'Replyto Reference Post',
'Rows in table': 'Linhas numa tabela',
'Rows selected': 'Linhas seleccionadas',
'Stylesheet': 'Folha de estilo',
'Sure you want to delete this object?': 'Tem a certeza que deseja eliminar este objecto?',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'A "query" é uma condição do tipo "db.table1.field1==\'value\'". Algo como "db.table1.field1==db.table2.field2" resultaria num SQL JOIN.',
'Title': 'Title',
'Update:': 'Actualização:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Utilize (...)&(...) para AND, (...)|(...) para OR, e ~(...)  para NOT para construir interrogações mais complexas.',
'Username': 'Username',
'View': 'Vista',
'Welcome %s': 'Bem-vindo(a) %s',
'Welcome to Gluonization': 'Bem vindo ao Web2py',
'Welcome to web2py': 'Bem-vindo(a) ao web2py',
'When': 'When',
'appadmin is disabled because insecure channel': 'appadmin está desactivada pois o canal é inseguro',
'cache': 'cache',
'change password': 'alterar palavra-chave',
'Online examples': 'Exemplos online',
'Administrative interface': 'Painel administrativo',
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
'invalid request': 'Pedido Inválido',
'login': 'login',
'logout': 'logout',
'new record inserted': 'novo registo inserido',
'next 100 rows': 'próximas 100 linhas',
'or import from csv file': 'ou importe a partir de ficheiro csv',
'previous 100 rows': '100 linhas anteriores',
'record': 'registo',
'record does not exist': 'registo inexistente',
'record id': 'id de registo',
'register': 'register',
'search category': 'search category',
'search comment': 'search comment',
'search post': 'search post',
'select category': 'select category',
'select comment': 'select comment',
'select post': 'select post',
'selected': 'seleccionado(s)',
'show category': 'show category',
'show comment': 'show comment',
'show post': 'show post',
'state': 'estado',
'table': 'tabela',
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
'Author Reference Auth User': 'Author Reference Auth User',
'Author Reference Auth User.username': 'Author Reference Auth User.username',
'Available databases and tables': 'bases de dados e tabelas disponíveis',
'Cannot be empty': 'não pode ser vazio',
'Category Create': 'Category Create',
'Category Select': 'Category Select',
'Check to delete': 'seleccione para eliminar',
'Comment Create': 'Comment Create',
'Comment Select': 'Comment Select',
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
'Delete:': 'Eliminar:',
'Edit': 'Editar',
'Edit This App': 'Edite esta aplicação',
'Edit current record': 'Edição de registo currente',
'Email': 'Email',
'First Name': 'First Name',
'For %s #%s': 'For %s #%s',
'Hello World': 'Olá Mundo',
'Import/Export': 'Importar/Exportar',
'Index': 'Índice',
'Internal State': 'Estado interno',
'Invalid Query': 'Consulta Inválida',
'Last Name': 'Last Name',
'Layout': 'Esboço',
'Main Menu': 'Menu Principal',
'Menu Model': 'Menu do Modelo',
'Modified By': 'Modified By',
'Modified On': 'Modified On',
'Name': 'Name',
'New Record': 'Novo Registo',
'No Data': 'No Data',
'No databases in this application': 'Não há bases de dados nesta aplicação',
'Password': 'Password',
'Post Create': 'Post Create',
'Post Select': 'Post Select',
'Powered by': 'Suportado por',
'Query:': 'Interrogação:',
'Replyto Reference Post': 'Replyto Reference Post',
'Rows in table': 'Linhas numa tabela',
'Rows selected': 'Linhas seleccionadas',
'Stylesheet': 'Folha de estilo',
'Sure you want to delete this object?': 'Tem a certeza que deseja eliminar este objecto?',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': 'A "query" é uma condição do tipo "db.table1.field1==\'value\'". Algo como "db.table1.field1==db.table2.field2" resultaria num SQL JOIN.',
'Title': 'Title',
'Update:': 'Actualização:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Utilize (...)&(...) para AND, (...)|(...) para OR, e ~(...)  para NOT para construir interrogações mais complexas.',
'Username': 'Username',
'View': 'Vista',
'Welcome %s': 'Bem-vindo(a) %s',
'Welcome to Gluonization': 'Bem vindo ao Web2py',
'Welcome to web2py': 'Bem-vindo(a) ao web2py',
'When': 'When',
'appadmin is disabled because insecure channel': 'appadmin está desactivada pois o canal é inseguro',
'cache': 'cache',
'change password': 'alterar palavra-chave',
'Online examples': 'Exemplos online',
'Administrative interface': 'Painel administrativo',
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
'invalid request': 'Pedido Inválido',
'login': 'login',
'logout': 'logout',
'new record inserted': 'novo registo inserido',
'next 100 rows': 'próximas 100 linhas',
'or import from csv file': 'ou importe a partir de ficheiro csv',
'previous 100 rows': '100 linhas anteriores',
'record': 'registo',
'record does not exist': 'registo inexistente',
'record id': 'id de registo',
'register': 'register',
'search category': 'search category',
'search comment': 'search comment',
'search post': 'search post',
'select category': 'select category',
'select comment': 'select comment',
'select post': 'select post',
'selected': 'seleccionado(s)',
'show category': 'show category',
'show comment': 'show comment',
'show post': 'show post',
'state': 'estado',
'table': 'tabela',
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
'Available databases and tables': 'Базы данных и таблицы',
'Cannot be empty': 'Пустое значение недопустимо',
'Change Password': 'Смените пароль',
'Check to delete': 'Удалить',
'Check to delete:': 'Удалить:',
'Client IP': 'Client IP',
'Current request': 'Текущий запрос',
'Current response': 'Текущий ответ',
'Current session': 'Текущая сессия',
'Delete:': 'Удалить:',
'Description': 'Описание',
'E-mail': 'E-mail',
'Edit Profile': 'Редактировать профиль',
'Edit current record': 'Редактировать текущую запись',
'First name': 'Имя',
'Group ID': 'Group ID',
'Hello World': 'Заработало!',
'Import/Export': 'Импорт/экспорт',
'Internal State': 'Внутренне состояние',
'Invalid Query': 'Неверный запрос',
'Invalid email': 'Неверный email',
'Invalid login': 'Неверный логин',
'Invalid password': 'Неверный пароль',
'Last name': 'Фамилия',
'Logged in': 'Вход выполнен',
'Logged out': 'Выход выполнен',
'Login': 'Вход',
'Logout': 'Выход',
'Lost Password': 'Забыли пароль?',
'Name': 'Name',
'New Record': 'Новая запись',
'New password': 'Новый пароль',
'No databases in this application': 'В приложении нет баз данных',
'Old password': 'Старый пароль',
'Origin': 'Происхождение',
'Password': 'Пароль',
"Password fields don't match": 'Пароли не совпадают',
'Query:': 'Запрос:',
'Record ID': 'ID записи',
'Register': 'Зарегистрироваться',
'Registration key': 'Ключ регистрации',
'Remember me (for 30 days)': 'Запомнить меня (на 30 дней)',
'Reset Password key': 'Сбросить ключ пароля',
'Role': 'Роль',
'Rows in table': 'Строк в таблице',
'Rows selected': 'Выделено строк',
'Submit': 'Отправить',
'Sure you want to delete this object?': 'Подтвердите удаление объекта',
'Table name': 'Имя таблицы',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': '"Запрос" - это условие вида "db.table1.field1==\'значение\'". Выражение вида "db.table1.field1==db.table2.field2" формирует SQL JOIN.',
'Timestamp': 'Отметка времени',
'Update:': 'Изменить:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Для построение сложных запросов используйте операторы "И": (...)&(...), "ИЛИ": (...)|(...), "НЕ": ~(...).',
'User %(id)s Logged-in': 'Пользователь %(id)s вошёл',
'User %(id)s Logged-out': 'Пользователь %(id)s вышел',
'User %(id)s Password changed': 'Пользователь %(id)s сменил пароль',
'User %(id)s Profile updated': 'Пользователь %(id)s обновил профиль',
'User %(id)s Registered': 'Пользователь %(id)s зарегистрировался',
'User ID': 'ID пользователя',
'Verify Password': 'Повторите пароль',
'Welcome to web2py': 'Добро пожаловать в web2py',
'Online examples': 'примеры он-лайн',
'Administrative interface': 'административный интерфейс',
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
'invalid request': 'неверный запрос',
'login': 'вход',
'logout': 'выход',
'new record inserted': 'новая запись добавлена',
'next 100 rows': 'следующие 100 строк',
'or import from csv file': 'или импорт из csv-файла',
'password': 'пароль',
'previous 100 rows': 'предыдущие 100 строк',
'profile': 'профиль',
'record does not exist': 'запись не найдена',
'record id': 'id записи',
'selected': 'выбрано',
'state': 'состояние',
'table': 'таблица',
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
'Available databases and tables': 'Dostupné databázy a tabuľky',
'Cannot be empty': 'Nemôže byť prázdne',
'Check to delete': 'Označiť na zmazanie',
'Controller': 'Controller',
'Copyright': 'Copyright',
'Current request': 'Aktuálna požiadavka',
'Current response': 'Aktuálna odpoveď',
'Current session': 'Aktuálne sedenie',
'DB Model': 'DB Model',
'Database': 'Databáza',
'Delete:': 'Zmazať:',
'Description': 'Popis',
'Edit': 'Upraviť',
'Edit Profile': 'Upraviť profil',
'Edit current record': 'Upraviť aktuálny záznam',
'First name': 'Krstné meno',
'Group ID': 'ID skupiny',
'Hello World': 'Ahoj svet',
'Import/Export': 'Import/Export',
'Index': 'Index',
'Internal State': 'Vnútorný stav',
'Invalid email': 'Neplatný email',
'Invalid Query': 'Neplatná otázka',
'Invalid password': 'Nesprávne heslo',
'Last name': 'Priezvisko',
'Layout': 'Layout',
'Logged in': 'Prihlásený',
'Logged out': 'Odhlásený',
'Lost Password': 'Stratené heslo?',
'Menu Model': 'Menu Model',
'Name': 'Meno',
'New Record': 'Nový záznam',
'New password': 'Nové heslo',
'No databases in this application': 'V tejto aplikácii nie sú databázy',
'Old password': 'Staré heslo',
'Origin': 'Pôvod',
'Password': 'Heslo',
'Powered by': 'Powered by',
'Query:': 'Otázka:',
'Record ID': 'ID záznamu',
'Register': 'Zaregistrovať sa',
'Registration key': 'Registračný kľúč',
'Remember me (for 30 days)': 'Zapamätaj si ma (na 30 dní)',
'Reset Password key': 'Nastaviť registračný kľúč',
'Role': 'Rola',
'Rows in table': 'riadkov v tabuľke',
'Rows selected': 'označených riadkov',
'Submit': 'Odoslať',
'Stylesheet': 'Stylesheet',
'Sure you want to delete this object?': 'Ste si istí, že chcete zmazať tento objekt?',
'Table name': 'Názov tabuľky',
'The "query" is a condition like "db.table1.field1==\'value\'". Something like "db.table1.field1==db.table2.field2" results in a SQL JOIN.': '"query" je podmienka ako "db.table1.field1==\'value\'". Niečo ako "db.table1.field1==db.table2.field2" má za výsledok SQL JOIN.',
'The output of the file is a dictionary that was rendered by the view': 'Výstup zo súboru je slovník, ktorý bol zobrazený vo view',
'This is a copy of the scaffolding application': 'Toto je kópia skeletu aplikácie',
'Timestamp': 'Časová pečiatka',
'Update:': 'Upraviť:',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': 'Použite (...)&(...) pre AND, (...)|(...) pre OR a ~(...) pre NOT na poskladanie komplexnejších otázok.',
'User %(id)s Logged-in': 'Používateľ %(id)s prihlásený',
'User %(id)s Logged-out': 'Používateľ %(id)s odhlásený',
'User %(id)s Password changed': 'Používateľ %(id)s zmenil heslo',
'User %(id)s Profile updated': 'Používateľ %(id)s upravil profil',
'User %(id)s Registered': 'Používateľ %(id)s sa zaregistroval',
'User ID': 'ID používateľa',
'Verify Password': 'Zopakujte heslo',
'View': 'Zobraziť',
'Welcome to web2py': 'Vitajte vo web2py',
'Which called the function': 'Ktorý zavolal funkciu',
'You are successfully running web2py': 'Úspešne ste spustili web2py',
'You can modify this application and adapt it to your needs': 'Môžete upraviť túto aplikáciu a prispôsobiť ju svojim potrebám',
'You visited the url': 'Navštívili ste URL',
'appadmin is disabled because insecure channel': 'appadmin je zakázaný bez zabezpečeného spojenia',
'cache': 'cache',
'Online examples': 'pre online príklady kliknite sem',
'Administrative interface': 'pre administrátorské rozhranie kliknite sem',
'customize me!': 'prispôsob ma!',
'data uploaded': 'údaje naplnené',
'database': 'databáza',
'database %s select': 'databáza %s výber',
'db': 'db',
'design': 'návrh',
'Documentation': 'Dokumentácia',
'done!': 'hotovo!',
'export as csv file': 'exportovať do csv súboru',
'insert new': 'vložiť nový záznam ',
'insert new %s': 'vložiť nový  záznam %s',
'invalid request': 'Neplatná požiadavka',
'located in the file': 'nachádzajúci sa v súbore ',
'login': 'prihlásiť',
'logout': 'odhlásiť',
'lost password?': 'stratené heslo?',
'new record inserted': 'nový záznam bol vložený',
'next 100 rows': 'ďalších 100 riadkov',
'or import from csv file': 'alebo naimportovať z csv súboru',
'password': 'heslo',
'previous 100 rows': 'predchádzajúcich 100 riadkov',
'record': 'záznam',
'record does not exist': 'záznam neexistuje',
'record id': 'id záznamu',
'register': 'registrovať',
'selected': 'označených',
'state': 'stav',
'table': 'tabuľka',
'unable to parse csv file': 'nedá sa načítať csv súbor',
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
'Are you sure you want to uninstall application "%s"': '確定要移除應用程式 "%s"',
'Are you sure you want to uninstall application "%s"?': '確定要移除應用程式 "%s"',
'Authentication': '驗證',
'Available databases and tables': '可提供的資料庫和資料表',
'Cannot be empty': '不可空白',
'Cannot compile: there are errors in your app.        Debug it, correct errors and try again.': '無法編譯:應用程式中含有錯誤，請除錯後再試一次.',
'Change Password': '變更密碼',
'Check to delete': '打勾代表刪除',
'Check to delete:': '點選以示刪除:',
'Client IP': '客戶端網址(IP)',
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
'Editing file': '編輯檔案',
'Editing file "%s"': '編輯檔案"%s"',
'Error logs for "%(app)s"': '"%(app)s"的錯誤紀錄',
'First name': '名',
'Functions with no doctests will result in [passed] tests.': '沒有 doctests 的函式會顯示 [passed].',
'Group ID': '群組編號',
'Hello World': '嗨! 世界',
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
'License for': '軟體版權為',
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
'Password': '密碼',
"Password fields don't match": '密碼欄不匹配',
'Peeking at file': '選擇檔案',
'Powered by': '基於以下技術構建：',
'Query:': '查詢:',
'Record ID': '紀錄編號',
'Register': '註冊',
'Registration key': '註冊金鑰',
'Remember me (for 30 days)': '記住我(30 天)',
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
'Unable to check for upgrades': '無法做升級檢查',
'Unable to download': '無法下載',
'Unable to download app': '無法下載應用程式',
'Update:': '更新:',
'Upload existing application': '更新存在的應用程式',
'Use (...)&(...) for AND, (...)|(...) for OR, and ~(...)  for NOT to build more complex queries.': '使用下列方式來組合更複雜的條件式, (...)&(...) 代表同時存在的條件, (...)|(...) 代表擇一的條件, ~(...)則代表反向條件.',
'User %(id)s Logged-in': '使用者 %(id)s 已登入',
'User %(id)s Registered': '使用者 %(id)s 已註冊',
'User ID': '使用者編號',
'Verify Password': '驗證密碼',
'View': '視圖',
'Views': '視圖',
'Welcome %s': '歡迎 %s',
'Welcome to web2py': '歡迎使用 web2py',
'YES': '是',
'about': '關於',
'appadmin is disabled because insecure channel': '因為來自非安全通道,管理介面關閉',
'cache': '快取記憶體',
'change password': '變更密碼',
'Online examples': '點此處進入線上範例',
'Administrative interface': '點此處進入管理介面',
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
'invalid request': '不合法的網路要求(request)',
'login': '登入',
'logout': '登出',
'new record inserted': '已插入新紀錄',
'next 100 rows': '往後 100 筆',
'or import from csv file': '或是從逗號分隔檔(CSV)匯入',
'previous 100 rows': '往前 100 筆',
'record': '紀錄',
'record does not exist': '紀錄不存在',
'record id': '紀錄編號',
'register': '註冊',
'selected': '已選擇',
'state': '狀態',
'table': '資料表',
'unable to parse csv file': '無法解析逗號分隔檔(csv)',
}


########NEW FILE########
__FILENAME__ = db
# -*- coding: utf-8 -*-

#########################################################################
## This scaffolding model makes your app work on Google App Engine too
## File is released under public domain and you can use without limitations
#########################################################################

## if SSL/HTTPS is properly configured and you want all HTTP requests to
## be redirected to HTTPS, uncomment the line below:
# request.requires_https()

if not request.env.web2py_runtime_gae:
    ## if NOT running on Google App Engine use SQLite or other DB
    db = DAL('sqlite://storage.sqlite')
else:
    ## connect to Google BigTable (optional 'google:datastore://namespace')
    db = DAL('google:datastore')
    ## store sessions and tickets there
    session.connect(request, response, db = db)
    ## or store session in Memcache, Redis, etc.
    ## from gluon.contrib.memdb import MEMDB
    ## from google.appengine.api.memcache import Client
    ## session.connect(request, response, db = MEMDB(Client()))

## by default give a view/generic.extension to all actions from localhost
## none otherwise. a pattern can be 'controller/function.extension'
response.generic_patterns = ['*'] if request.is_local else []
## (optional) optimize handling of static files
# response.optimize_css = 'concat,minify,inline'
# response.optimize_js = 'concat,minify,inline'

#########################################################################
## Here is sample code if you need for
## - email capabilities
## - authentication (registration, login, logout, ... )
## - authorization (role based authorization)
## - services (xml, csv, json, xmlrpc, jsonrpc, amf, rss)
## - old style crud actions
## (more options discussed in gluon/tools.py)
#########################################################################

from gluon.tools import Auth, Crud, Service, PluginManager, prettydate
auth = Auth(db, hmac_key=Auth.get_or_create_key())
crud, service, plugins = Crud(db), Service(), PluginManager()

## create all tables needed by auth if not custom tables
auth.define_tables()

## configure email
mail=auth.settings.mailer
mail.settings.server = 'logging' or 'smtp.gmail.com:587'
mail.settings.sender = 'you@gmail.com'
mail.settings.login = 'username:password'

## configure auth policy
auth.settings.registration_requires_verification = False
auth.settings.registration_requires_approval = False
auth.settings.reset_password_requires_verification = True

## if you need to use OpenID, Facebook, MySpace, Twitter, Linkedin, etc.
## register with janrain.com, write your domain:api_key in private/janrain.key
from gluon.contrib.login_methods.rpx_account import use_janrain
use_janrain(auth,filename='private/janrain.key')

#########################################################################
## Define your tables below (or better in another model file) for example
##
## >>> db.define_table('mytable',Field('myfield','string'))
##
## Fields can be 'string','text','password','integer','double','boolean'
##       'date','time','datetime','blob','upload', 'reference TABLENAME'
## There is an implicit 'id integer autoincrement' field
## Consult manual for more options, validators, etc.
##
## More API examples for controllers:
##
## >>> db.mytable.insert(myfield='value')
## >>> rows=db(db.mytable.myfield=='value').select(db.mytable.ALL)
## >>> for row in rows: print row.id, row.myfield
#########################################################################


########NEW FILE########
__FILENAME__ = menu
response.title = 'Plasmid'
response.subtitle = 'The CMS that replicates pages'

########NEW FILE########
__FILENAME__ = plasmid
db.define_table(
    'cms_clone',
    Field('url'),
    Field('html','text'),
    auth.signature)

db.define_table(
    'cms_folder',
    Field('name',requires=IS_NOT_EMPTY()),
    Field('parent_folder','reference cms_folder',readable=False,writable=False),
    auth.signature,
    format='%(name)s')

db.define_table(
    'cms_file',
    Field('folder','reference cms_folder',readable=False,writable=False),
    Field('name',requires=IS_NOT_EMPTY()),
    Field('file','upload'),
    auth.signature,
    format='%(name)s')


########NEW FILE########
