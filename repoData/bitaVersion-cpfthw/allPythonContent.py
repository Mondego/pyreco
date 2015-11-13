__FILENAME__ = models
#!/usr/bin/python
# -*- coding: utf-8 -*-
from django.db import models
from django.forms import ModelForm

# Create your models here.

SUBJECT_CHOICES = (('English', 'English'), ('Mathematics', 'Mathematics'
                   ), ('History', 'History'), ('Philosophy',
                   'Philosophy'))


class Note(models.Model):

    title = models.CharField(max_length=200)
    description = models.TextField()
    subject = models.CharField(max_length=20, choices=SUBJECT_CHOICES)
    author = models.CharField(max_length=20)
    date_created = models.DateField(auto_now=True, auto_now_add=True)


class NoteForm(ModelForm):

    class Meta:

        model = Note



########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

urlpatterns = patterns('djangonotes.views',
url(r'^$', 'index', name='index'),
url(r'^create/$', 'create', name='create'),
url(r'^edit/(?P<note_id>\d+)/$', 'edit', name='edit'),
)


########NEW FILE########
__FILENAME__ = views
#!/usr/bin/python
# -*- coding: utf-8 -*-
# Create your views here.
from django.shortcuts import render, redirect

from models import Note, NoteForm


def index(request):
    notes = Note.objects.all()
    return render(request, 'index.html', {'notes': notes})


def create(request):
    form = NoteForm(data=request.POST or None)
    if form.is_valid():
        form.save()
        return redirect('/')
    return render(request, 'form.html', {'form': form})


def edit(request, note_id):
    instance_data = Note.objects.get(id=note_id)
    form = NoteForm(data=request.POST or None, instance=instance_data)
    if form.is_valid():
        form.save()
        return redirect('/')
    return render(request, 'form.html', {'form': form})

########NEW FILE########
__FILENAME__ = forms
#!/usr/bin/python
# -*- coding: utf-8 -*-
from flaskext import wtf
from flaskext.wtf import validators


class NotesForm(wtf.Form):

    subject_list = [('0', 'English'), ('1', 'Philosophy'), ('2',
                    'Theology'), ('3', 'Mathematics')]

    title = wtf.StringField('Title', validators=[validators.Required()])
    author = wtf.StringField('Author',
                             validators=[validators.Required()])
    description = wtf.TextAreaField('Description',
                                    validators=[validators.Required()])
    subject = wtf.SelectField(choices=subject_list)

########NEW FILE########
__FILENAME__ = manage
from flask.ext.script import Manager
from notes import app, db

manager = Manager(app)


@manager.command
def initdb():
    """Creates all database tables."""
    db.create_all()


@manager.command
def dropdb():
    """Drops all database tables."""
    db.drop_all()


if __name__ == '__main__':
    manager.run()

########NEW FILE########
__FILENAME__ = notes
#!/usr/bin/python
# -*- coding: utf-8 -*-
from datetime import datetime
from flask import Flask, request, render_template, flash, url_for, \
    redirect
from flaskext import wtf
from flaskext.wtf import validators

from forms import NotesForm

app = Flask(__name__)
app.config.from_pyfile('settings.py')
from flask.ext.sqlalchemy import SQLAlchemy
db = SQLAlchemy(app)


class Notes(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80))
    subject = db.Column(db.String(80))
    author = db.Column(db.String(80))
    description = db.Column(db.Text)
    pub_date = db.Column(db.Date)

    def __init__(
        self,
        title,
        author,
        description,
        subject,
        ):
        self.title = title
        self.author = author
        self.description = description
        self.subject = subject
        self.pub_date = datetime.now()


@app.route('/')
def redirect_to_home():
    return redirect(url_for('list_notes'))


@app.route('/notes/')
def list_notes():
    notes = Notes.query.all()
    return render_template('index.html', notes=notes)


@app.route('/notes/create/', methods=['GET', 'POST'])
def create():
    form = NotesForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            note = Notes(form.title.data, form.author.data,
                         form.description.data, form.subject.data)
            db.session.add(note)
            db.session.commit()
            flash('Note saved on database.')
            return redirect(url_for('list_notes'))
    return render_template('note.html', form=form)


@app.route('/notes/delete/<int:note_id>', methods=['GET'])
def delete(note_id):
    note = Notes.query.get_or_404(note_id)
    db.session.delete(note)
    db.session.commit()
    flash('Note Deleted')
    return redirect(url_for('list_notes'))


@app.route('/notes/edit/<int:note_id>', methods=['GET', 'POST'])
def edit(note_id):
    note = Notes.query.get_or_404(note_id)
    form = NotesForm(obj=note)
    if request.method == 'POST':
        print request.form
        if form.validate_on_submit():
            print request.form['title']
            note.title = request.form['title']
            note.author = request.form['author']
            note.description = request.form['description']
            note.subject = request.form['subject']
            db.session.add(note)
            db.session.commit()
        return redirect(url_for('list_notes'))
    else:
        return render_template('note.html', form=form)

########NEW FILE########
__FILENAME__ = settings
DEBUG=False
SQLALCHEMY_DATABASE_URI='sqlite:///notes_.db'
SECRET_KEY='development-key'
CSRF_ENABLED=True




########NEW FILE########
__FILENAME__ = models
#!/usr/bin/python
# -*- coding: utf-8 -*-
from datetime import datetime

from sqlalchemy import Column, Integer, Text, String, Date

from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import scoped_session, sessionmaker

from zope.sqlalchemy import ZopeTransactionExtension

DBSession = \
    scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()


class Note(Base):

    __tablename__ = 'note'
    note_id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False, unique=True)
    author = Column(String(100), nullable=False, unique=True)
    subject = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    date_created = Column(Date, default=datetime.now().date())

    def __init__(
        self,
        title,
        author,
        subject,
        description,
        ):
        self.title = title
        self.author = author
        self.subject = subject
        self.description = description



########NEW FILE########
__FILENAME__ = initializedb
import os
import sys
import transaction

from sqlalchemy import engine_from_config

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

from ..models import (
    DBSession,
    Note,
    Base,
    )

def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri>\n'
          '(example: "%s development.ini")' % (cmd, cmd)) 
    sys.exit(1)

def main(argv=sys.argv):
    if len(argv) != 2:
        usage(argv)
    config_uri = argv[1]
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.create_all(engine)
    with transaction.manager:
        model = Note('First Note', 'John Doe', 'This is the front page', 'History', )
        DBSession.add(model)

########NEW FILE########
__FILENAME__ = tests
import unittest
import transaction

from pyramid import testing

from .models import DBSession

class TestMyView(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()
        from sqlalchemy import create_engine
        engine = create_engine('sqlite://')
        from .models import (
            Base,
            MyModel,
            )
        DBSession.configure(bind=engine)
        Base.metadata.create_all(engine)
        with transaction.manager:
            model = MyModel(name='one', value=55)
            DBSession.add(model)

    def tearDown(self):
        DBSession.remove()
        testing.tearDown()

    def test_it(self):
        from .views import my_view
        request = testing.DummyRequest()
        info = my_view(request)
        self.assertEqual(info['one'].name, 'one')
        self.assertEqual(info['project'], 'PyramidNotes')

########NEW FILE########
__FILENAME__ = views
#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
from docutils.core import publish_parts
from formencode import Schema, validators

from pyramid_simpleform import Form
from pyramid_simpleform.renderers import FormRenderer

from pyramid.httpexceptions import HTTPFound, HTTPNotFound

from pyramid.response import Response
from pyramid.view import view_config

from sqlalchemy.exc import DBAPIError

from models import DBSession, Note


class NoteSchema(Schema):

    filter_extra_fields = True
    allow_extra_fields = True

    title = validators.String(not_empty=True)
    author = validators.String(not_empty=True)
    subject = validators.String(not_empty=True)
    description = validators.PlainText(not_empty=True)


@view_config(name='edit', renderer='templates/edit.pt')
def edit(request):

    item_id = request.matchdict['item_id']
    item = session.query(Note).get(item_id)

    form = Form(request, schema=NoteSchema, obj=item)

    if form.validate():

        form.bind(item)

        # persist model somewhere...

        return HTTPFound(location='/')

    return dict(item=item, form=FormRenderer(form))


@view_config(name='add', renderer='templates/submit.pt')
def add(request):
    import ipdb
    ipdb.set_trace()
    form = Form(request, schema=NoteSchema)

    if form.validate():

        obj = form.bind(Note())

        # persist model somewhere...

        return HTTPFound(location='/')

    return dict(renderer=FormRenderer(form))


@view_config(route_name='home', renderer='templates/mytemplate.pt')
def my_view(request):
    try:
        one = DBSession.query(Note).filter(Note.note_id == 1).first()
    except DBAPIError:
        return Response(conn_err_msg, content_type='text/plain',
                        status_int=500)
    return {'one': one, 'project': 'PyramidNotes'}

conn_err_msg = \
    """\
Pyramid is having a problem using your SQL database.  The problem
might be caused by one of the following things:

1.  You may need to run the "initialize_PyramidNotes_db" script
    to initialize your database tables.  Check your virtual 
    environment's "bin" directory for this script and try to run it.

2.  Your database server may not be running.  Check that the
    database server referred to by the "sqlalchemy.url" setting in
    your "development.ini" file is running.

After you fix the problem, please restart the Pyramid application to
try it again.
"""

########NEW FILE########
__FILENAME__ = error
# -*- coding: utf-8 -*-
"""Error controller"""

from tg import request, expose

__all__ = ['ErrorController']


class ErrorController(object):
    """
    Generates error documents as and when they are required.

    The ErrorDocuments middleware forwards to ErrorController when error
    related status codes are returned from the application.

    This behaviour can be altered by changing the parameters to the
    ErrorDocuments middleware in your config/middleware.py file.
    
    """

    @expose('tgnotes.templates.error')
    def document(self, *args, **kwargs):
        """Render the error document"""
        resp = request.environ.get('pylons.original_response')
        default_message = ("<p>We're sorry but we weren't able to process "
                           " this request.</p>")
        values = dict(prefix=request.environ.get('SCRIPT_NAME', ''),
                      code=request.params.get('code', resp.status_int),
                      message=request.params.get('message', default_message))
        return values

########NEW FILE########
__FILENAME__ = root
"""Main Controller"""

from tgnotes.lib.base import BaseController
from tgext.crud import CrudRestController
from tgnotes.model import DBSession, Note
from sprox.tablebase import TableBase
from sprox.fillerbase import TableFiller
from sprox.fillerbase import EditFormFiller

from tgnotes.widgets.forms import note_add_form, note_edit_form

class NoteTable(TableBase):
    __model__ = Note
    __omit_fields__ = ['note_id']
note_table = NoteTable(DBSession)

class NoteTableFiller(TableFiller):
    __model__ = Note
note_table_filler = NoteTableFiller(DBSession)

class NoteEditFiller(EditFormFiller):
    __model__ = Note
note_edit_filler = NoteEditFiller(DBSession)

class RootController(BaseController):
    notes = NoteController(DBSession)

class NoteController(CrudRestController):
    model = Note
    table = note_table
    table_filler = note_table_filler
    edit_filler = note_edit_filler
    new_form = note_add_form
    edit_form = note_edit_form


########NEW FILE########
__FILENAME__ = secure
# -*- coding: utf-8 -*-
"""Sample controller with all its actions protected."""
# This controller is only used when you activate auth. You can safely remove
# this file from your project.

########NEW FILE########
__FILENAME__ = template
# -*- coding: utf-8 -*-
"""Fallback controller."""

from tgnotes.lib.base import BaseController
from tg import abort

__all__ = ['TemplateController']


class TemplateController(BaseController):
    """
    The fallback controller for TurboGearNotes.
    
    By default, the final controller tried to fulfill the request
    when no other routes match. It may be used to display a template
    when all else fails, e.g.::
    
        def view(self, url):
            return render('/%s' % url)
    
    Or if you're using Mako and want to explicitly send a 404 (Not
    Found) response code when the requested template doesn't exist::
    
        import mako.exceptions
        
        def view(self, url):
            try:
                return render('/%s' % url)
            except mako.exceptions.TopLevelLookupException:
                abort(404)
    
    """
    
    def view(self, url):
        """Abort the request with a 404 HTTP status code."""
        abort(404)

########NEW FILE########
__FILENAME__ = auth
# -*- coding: utf-8 -*-
"""
Auth* related model.

This is where the models used by :mod:`repoze.who` and :mod:`repoze.what` are
defined.

It's perfectly fine to re-use this definition in the TurboGearNotes application,
though.

"""

########NEW FILE########
__FILENAME__ = note
from sqlalchemy import *
from sqlalchemy.orm import mapper
from tgnotes.model import DeclarativeBase, metadata

from datetime import datetime

class Note(DeclarativeBase):
    __tablename__ = "notes"
    note_id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    author = Column(String(100), nullable=False)
    subject = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    date_taken = Column(Date, nullable=True)

########NEW FILE########
__FILENAME__ = forms
from tgnotes.model import DBSession, metadata, Note
from tw.core import WidgetsList
from tw.forms import TableForm, TextField, CalendarDatePicker, SingleSelectField, TextArea
from formencode.validators import Int, NotEmpty, DateConverter, DateValidator
from sprox.formbase import EditableForm

class NoteForm(TableForm):
    # This WidgetsList is just a container
    class fields(WidgetsList):
        title = TextField(validator=NotEmpty)
        author = TextField(validator=NotEmpty)
        description = TextArea(attrs=dict(rows=3, cols=25))
        date_taken = CalendarDatePicker(validator=DateConverter())
        subject_list = ((1,"Philosophy"),
                         (2,"Maths"),
                         (3,"Literature"),
                         (4,"History"),
                         (5,"Politics"),
                         (6,"Sociology"))
        subject = SingleSelectField(options=subject_list)
note_add_form = NoteForm("create_note_form")
        
class NoteEditForm(EditableForm):
    __model__ = Note
    __omit_fields__ = ['note_id']
note_edit_form = NoteEditForm(DBSession)




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
def index():

    ''' Makes a db query to select all the notes, 
    orders the notes by the publication date and 
    returns a dictionary to the template, containing 
    all the notes.'''

    response.flash = "Welcome to the index view!"
    notes = db(db.notes).select(orderby=db.notes.pub_date)    
    return dict(notes=notes)
     
def create():

    ''' Generates a form corresponding to the model and 
        renders it, if the form sends some data, the function 
        validates the data and saves the data in the database.'''
        
    response.flash = "This is the create page"
    form=SQLFORM(db.notes)
    if form.process().accepted:
       response.flash = 'form accepted'
    elif form.errors:
       response.flash = 'form has errors'
    else:
        response.flash = 'please fill the form'       
    return dict(form=form)


def edit():

    ''' The function pre-populates the data from the note instance
        that has been requested to be edited and renders it,
        once client sends in some data, it saves it in the database.'''
        
    note = db.notes(request.args(0)) or redirect(URL('error'))
    form=SQLFORM(db.notes, note, deletable = True)
    if form.validate():
        if form.deleted:
            db(db.notes.id==note.id).delete()
            redirect(URL('index'))
        else:
            note.update_record(**dict(form.vars))
            response.flash = 'records changed'
    else:
        response.flash = 'Something went wrong!'
    return dict(form=form)    
    
    
    # ALL THE FUNCTIONS BELOW ARE AUTO GENERATED
    
def user():
    """
    exposes:
    http://..../[app]/default/user/login
    http://..../[app]/default/user/logout
    http://..../[app]/default/user/register
    http://..../[app]/default/user/profile
    http://..../[app]/default/user/retrieve_password
    http://..../[app]/default/user/change_password
    use @auth.requires_login()
        @auth.requires_membership('group name')
        @auth.requires_permission('read','table name',record_id)
    to decorate functions that need access control
    """
    return dict(form=auth())




def call():
    """
    exposes services. for example:
    http://..../[app]/default/call/jsonrpc
    decorate with @services.jsonrpc the functions to expose
    supports xml, json, xmlrpc, jsonrpc, amfrpc, rss, csv
    """
    return service()


@auth.requires_signature()
def data():
    """
    http://..../[app]/default/data/tables
    http://..../[app]/default/data/create/[table]
    http://..../[app]/default/data/read/[table]/[id]
    http://..../[app]/default/data/update/[table]/[id]
    http://..../[app]/default/data/delete/[table]/[id]
    http://..../[app]/default/data/select/[table]
    http://..../[app]/default/data/search/[table]
    but URLs must be signed, i.e. linked with
      A('table',_href=URL('data/tables',user_signature=True))
    or with the signed load operator
      LOAD('default','data.load',args='tables',ajax=True,user_signature=True)
    """
    return dict(form=crud())

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

# ALL THE CONTENT ABOVE IS AUTO GENERATED

''' We create a table notes, with the columns title, description, author,
subject and a publication date. '''

db.define_table('notes',
                Field('title', length=200, required=True, requires=IS_NOT_EMPTY()),
                Field('description', length=2000, required=True, requires=IS_NOT_EMPTY()),
                Field('author', db.auth_user, required=True, requires=IS_NOT_EMPTY()),
                Field('subject', length=20,requires=IS_IN_SET(('english', 'philosophy', 'metaphysics'))),
                Field('pub_date', 'datetime', default=request.now, writable=False)
                )

########NEW FILE########
__FILENAME__ = menu
# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

#########################################################################
## Customize your APP title, subtitle and menus here
#########################################################################

response.title = ' '.join(word.capitalize() for word in request.application.split('_'))
response.subtitle = T('customize me!')

## read more at http://dev.w3.org/html5/markup/meta.name.html
response.meta.author = 'Your Name <you@example.com>'
response.meta.description = 'a cool new app'
response.meta.keywords = 'web2py, python, framework'
response.meta.generator = 'Web2py Web Framework'
response.meta.copyright = 'Copyright 2011'

## your http://google.com/analytics id
response.google_analytics_id = None

#########################################################################
## this is the main application menu add/remove items as required
#########################################################################

response.menu = [
    (T('Home'), False, URL('default','index'), [])
    ]

#########################################################################
## provide shortcuts for development. remove in production
#########################################################################

def _():
    # shortcuts
    app = request.application
    ctr = request.controller
    # useful links to internal and external resources
    response.menu+=[
        (SPAN('web2py',_style='color:yellow'),False, None, [
                (T('My Sites'),False,URL('admin','default','site')),
                (T('This App'),False,URL('admin','default','design/%s' % app), [
                        (T('Controller'),False,
                         URL('admin','default','edit/%s/controllers/%s.py' % (app,ctr))),
                        (T('View'),False,
                         URL('admin','default','edit/%s/views/%s' % (app,response.view))),
                        (T('Layout'),False,
                         URL('admin','default','edit/%s/views/layout.html' % app)),
                        (T('Stylesheet'),False,
                         URL('admin','default','edit/%s/static/css/web2py.css' % app)),
                        (T('DB Model'),False,
                         URL('admin','default','edit/%s/models/db.py' % app)),
                        (T('Menu Model'),False,
                         URL('admin','default','edit/%s/models/menu.py' % app)),
                        (T('Database'),False, URL(app,'appadmin','index')),
                        (T('Errors'),False, URL('admin','default','errors/' + app)),
                        (T('About'),False, URL('admin','default','about/' + app)),
                        ]),
                ('web2py.com',False,'http://www.web2py.com', [
                        (T('Download'),False,'http://www.web2py.com/examples/default/download'),
                        (T('Support'),False,'http://www.web2py.com/examples/default/support'),
                        (T('Demo'),False,'http://web2py.com/demo_admin'),
                        (T('Quick Examples'),False,'http://web2py.com/examples/default/examples'),
                        (T('FAQ'),False,'http://web2py.com/AlterEgo'),
                        (T('Videos'),False,'http://www.web2py.com/examples/default/videos/'),
                        (T('Free Applications'),False,'http://web2py.com/appliances'),
                        (T('Plugins'),False,'http://web2py.com/plugins'),
                        (T('Layouts'),False,'http://web2py.com/layouts'),
                        (T('Recipes'),False,'http://web2pyslices.com/'),
                        (T('Semantic'),False,'http://web2py.com/semantic'),
                        ]),
                (T('Documentation'),False,'http://www.web2py.com/book', [
                        (T('Preface'),False,'http://www.web2py.com/book/default/chapter/00'),
                        (T('Introduction'),False,'http://www.web2py.com/book/default/chapter/01'),
                        (T('Python'),False,'http://www.web2py.com/book/default/chapter/02'),
                        (T('Overview'),False,'http://www.web2py.com/book/default/chapter/03'),
                        (T('The Core'),False,'http://www.web2py.com/book/default/chapter/04'),
                        (T('The Views'),False,'http://www.web2py.com/book/default/chapter/05'),
                        (T('Database'),False,'http://www.web2py.com/book/default/chapter/06'),
                        (T('Forms and Validators'),False,'http://www.web2py.com/book/default/chapter/07'),
                        (T('Email and SMS'),False,'http://www.web2py.com/book/default/chapter/08'),
                        (T('Access Control'),False,'http://www.web2py.com/book/default/chapter/09'),
                        (T('Services'),False,'http://www.web2py.com/book/default/chapter/10'),
                        (T('Ajax Recipes'),False,'http://www.web2py.com/book/default/chapter/11'),
                        (T('Components and Plugins'),False,'http://www.web2py.com/book/default/chapter/12'),
                        (T('Deployment Recipes'),False,'http://www.web2py.com/book/default/chapter/13'),
                        (T('Other Recipes'),False,'http://www.web2py.com/book/default/chapter/14'),
                        (T('Buy this book'),False,'http://stores.lulu.com/web2py'),
                        ]),
                (T('Community'),False, None, [
                        (T('Groups'),False,'http://www.web2py.com/examples/default/usergroups'),
                        (T('Twitter'),False,'http://twitter.com/web2py'),
                        (T('Live Chat'),False,'http://webchat.freenode.net/?channels=web2py'),
                        ]),
                (T('Plugins'),False,None, [
                        ('plugin_wiki',False,'http://web2py.com/examples/default/download'),
                        (T('Other Plugins'),False,'http://web2py.com/plugins'),
                        (T('Layout Plugins'),False,'http://web2py.com/layouts'),
                        ])
                ]
         )]
_()


########NEW FILE########
__FILENAME__ = main
import webapp2
from views import MainPage, CreateNote, DeleteNote, EditNote

app = webapp2.WSGIApplication([
        ('/', MainPage), 
        ('/create', CreateNote), 
        ('/edit/([\d]+)', EditNote),
        ('/delete/([\d]+)', DeleteNote)
        ],
        debug=True)

########NEW FILE########
__FILENAME__ = models
from google.appengine.ext import db


class Notes(db.Model):

    author = db.StringProperty()
    text = db.StringProperty(multiline=True)
    priority = db.StringProperty()
    status = db.StringProperty()
    date = db.DateTimeProperty(auto_now_add=True)

########NEW FILE########
__FILENAME__ = views
import jinja2
import os
import webapp2
from datetime import datetime
from google.appengine.ext import db

from models import Notes

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
jinja_environment = \
    jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATE_DIR))


class BaseHandler(webapp2.RequestHandler):

    @webapp2.cached_property
    def jinja2(self):
        return jinja2.get_jinja2(app=self.app)

    def render_template(
        self,
        filename,
        template_values,
        **template_args
        ):
        template = jinja_environment.get_template(filename)
        self.response.out.write(template.render(template_values))


class MainPage(BaseHandler):

    def get(self):
        notes = Notes.all()
        self.render_template('index.html', {'notes': notes})


class CreateNote(BaseHandler):

    def post(self):
        n = Notes(author=self.request.get('author'),
                  text=self.request.get('text'),
                  priority=self.request.get('priority'),
                  status=self.request.get('status'))
        n.put()
        return webapp2.redirect('/')

    def get(self):
        self.render_template('create.html', {})


class EditNote(BaseHandler):

    def post(self, note_id):
        iden = int(note_id)
        note = db.get(db.Key.from_path('Notes', iden))
        note.author = self.request.get('author')
        note.text = self.request.get('text')
        note.priority = self.request.get('priority')
        note.status = self.request.get('status')
        note.date = datetime.now()
        note.put()
        return webapp2.redirect('/')

    def get(self, note_id):
        iden = int(note_id)
        note = db.get(db.Key.from_path('Notes', iden))
        self.render_template('edit.html', {'note': note})


class DeleteNote(BaseHandler):

    def get(self, note_id):
        iden = int(note_id)
        note = db.get(db.Key.from_path('Notes', iden))
        db.delete(note)
        return webapp2.redirect('/')

########NEW FILE########
