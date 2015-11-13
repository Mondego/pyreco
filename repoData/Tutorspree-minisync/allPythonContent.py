__FILENAME__ = exceptions

class MinisyncError(Exception):
    pass

class PermissionError(MinisyncError):
    pass


########NEW FILE########
__FILENAME__ = sqlalchemy
import datetime

def rec_getattr(obj, attr):
    try:
        ret_attr = reduce(getattr, attr.split('.'), obj)
    except AttributeError:
        ret_attr = None
    return ret_attr


class JsonSerializer(object):
    __public__ = None

    def __init__(self, db):
        self.db = db
    
    def __call__(self, attr):
        """
        Return:
            A value, if attr is a scalar
            A dictionary of key-value pairs, if attr is a db.Model instance
            A list, if attr is a list
            If a value is a nonterminal (list or db.Model instance), recurse.
        """
        d = {}
        if isinstance(attr, self.db.Model):
           return self.to_serializable_dict(attr)
        elif isinstance(attr, list):
            return [self(a) for a in attr]
        elif isinstance(attr, datetime.datetime):
            return attr.isoformat()
        # TODO: Always return a Python primitive, and bail if we can't.
        return attr

    def to_serializable_dict(self, attr, props=None):
        d = {}
        props = props or attr.__public__
        for attr_name in props:
            attr_to_serialize = rec_getattr(self, attr_name)
            d[attr_name] = self(attr_to_serialize)
        return d


########NEW FILE########
__FILENAME__ = app
from sqlalchemy import create_engine

from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.principal import Principal, Identity, AnonymousIdentity, \
     identity_changed

app = Flask(__name__)
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
db_uri = "sqlite:///tests.db"
app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
principals = Principal(app)

if __name__ == '__main__':
    app.run(debug=True)
########NEW FILE########
__FILENAME__ = fixtures
from fixture import DataSet, SQLAlchemyFixture
from fixture.style import NamedDataStyle
from sqlalchemy import create_engine

import models

def install(app, *args):
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    db = SQLAlchemyFixture(env=models, style=NamedDataStyle(), engine=engine)
    data = db.data(*args)
    data.setup()
    db.dispose()

class SyncUserData(DataSet):

    class user01:
        username = "Thomas"
        email = "me@thomasboyt.com"

    class user02:
        username = "Bruce"
        email = "bruce@wayneenterprises.com"

    class user03:
        username =  "Zach"
        email = "zach@tutorspree.com"

class ThingData(DataSet):

    class thing01:
        user_id = 1
        description = "Foo"

    class thing02:
        user_id = 1
        description = "Bar"

    class thing03:
        user_id = 2
        description = "Baz"

class ChildThingData(DataSet):

    class child_thing01:
        thing_id = 3
        description = "Blergh"

    class child_thing03:
        id = 3
        thing_id = 3
        description = "Blergh"

# A simple trick for installing all fixtures from an external module.
all_data = (SyncUserData, ThingData, ChildThingData,)


########NEW FILE########
__FILENAME__ = models
from minisync import requireUser
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.ext.hybrid import hybrid_property

from app import app

db = SQLAlchemy()

def create_tables(app):
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    return engine


class Thing(db.Model):
    __tablename__ = "things"
    __allow_update__ = ["description", "children", "user_id"]
    __public__      = ["id"]
    id =            db.Column(db.Integer, primary_key=True)
    user_id =       db.Column(db.Integer, db.ForeignKey('users.id', deferrable=True, ondelete="CASCADE"), nullable=False)
    description =   db.Column(db.Text)
    children =      db.relationship('ChildThing', primaryjoin='ChildThing.parent_id == Thing.id',
                                    cascade='delete', backref=db.backref('parent'))
    only_child =    db.relationship('ChildThing', primaryjoin='ChildThing.parent_id == Thing.id',
                                    uselist=False, backref=db.backref('only_parent', uselist=False))

    @staticmethod
    @requireUser
    def permit_create(obj_dict, user=None):
        return obj_dict['user_id'] == user.id

    @requireUser
    def permit_update(self, obj_dict, user=None):
        return user.id == self.user_id or obj_dict.get('user_id', None)

    @hybrid_property
    def test(self):
        return 'hi'

class ChildThing(db.Model):
    __tablename__ = "child_things"
    __allow_update__ = ["description", "parent_id"]
    __allow_associate__ = ['Thing']
    __allow_disassociate__ = ['Thing']
    id =            db.Column(db.Integer, primary_key=True)
    description =   db.Column(db.Text)
    parent_id =     db.Column(db.Integer, db.ForeignKey('things.id', deferrable=True, ondelete='CASCADE'))

    @staticmethod
    @requireUser
    def permit_create(obj_dict, user=None):
        return True

    @requireUser
    def permit_update(self, obj_dict, user=None):
        return True

    @requireUser
    def permit_associate(self, parent, obj_dict, user=None):
        return parent.__class__.__name__ in self.__allow_associate__

    @requireUser
    def permit_disassociate(self, parent, user=None):
        allowed = parent.__class__.__name__ in self.__allow_disassociate__
        owned = user.id == parent.user_id
        return allowed and owned

class SyncUser(db.Model):
    __tablename__ = "users"

    id =        db.Column(db.Integer, primary_key=True)
    username =  db.Column(db.String(80), unique=True)
    email =     db.Column(db.String(120), unique=True)
    things =    db.relationship('Thing', primaryjoin=Thing.user_id==id, cascade='delete')

    __allow_update__ = ['things']

    @requireUser
    def permit_update(self, obj_dict, user=None):
        return user.id == self.id
 

########NEW FILE########
__FILENAME__ = test
import os

from unittest import TestCase
from nose.tools import raises

from flask import Flask, current_app
from flask.ext.testing import TestCase
from flask.ext.principal import Principal, Identity, AnonymousIdentity, \
     identity_changed

import unittest
import fixtures
import models
from minisync import Minisync, PermissionError

class ModelsTestCase(TestCase):

    def create_app(self):
        app = Flask(__name__)
        app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

        # absolute path gets around annoying cwd difference here & in fixtures
        db_uri = "sqlite:///" + os.getcwd() + "/tests.db"
        app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
        principals = Principal(app)

        from models import db
        db.init_app(app)
        self.db = db

        self.sync = Minisync(self.db)

        return app

    def setUp(self):
        self.db.create_all()
        fixtures.install(self.app, *fixtures.all_data)
        identity_changed.send(current_app._get_current_object(), identity=Identity(1))
        self.user = models.SyncUser.query.filter_by(id=1).first()

    def tearDown(self):
        self.db.session.remove()
        self.db.drop_all()

    # Serialization
    # ------------------------------------------------------------------------

    def test_serialize(self):
        new_thing = self.sync(models.Thing, {'user_id': 1, 'description': "Hello."}, user=self.user)
        obj = self.sync.serialize(new_thing)
        assert obj == {'id': None}

    # Basic crud operations, not handling relationships beyond setting FKs
    # ------------------------------------------------------------------------

    def test_create(self):
        user = models.SyncUser.query.filter_by(id=3).first()
        new_thing = self.sync(models.Thing, {'user_id': 3, 'description': "User ID 3 created a thing."}, user=user)
        self.assertEqual(new_thing.user_id, 3)
        self.assertEqual(new_thing.description, "User ID 3 created a thing.")
        # Database step
        thing = models.Thing.query.filter_by(user_id=3).first()
        self.assertEqual(thing.description, "User ID 3 created a thing.")

    def test_embedded_create(self):
        user = models.SyncUser.query.filter_by(id=3).first()
        test_string = 'User ID 3 created an embedded thing.'
        child_thing = {'description': test_string} 
        new_thing = self.sync(models.Thing,
            {'user_id': 3, 'description': "User ID 3 created a thing.",
             'children': [child_thing]}, user=user)
        self.assertEqual(new_thing.children[0].description, test_string)
        # Database step
        created_parent_thing = models.Thing.query.filter_by(user_id=3).first()
        self.assertEqual(created_parent_thing.children[0].description, test_string)

    def test_create_with_existing_parent(self):
        user = models.SyncUser.query.filter_by(id=3).first()
        test_string = 'User ID 1 created an embedded thing.'
        child_thing = {'description': test_string} 
        new_thing = self.sync(models.Thing,
                {'id': 1, 'children': [child_thing]}, user=user)
        self.assertEqual(new_thing.children[0].description, test_string)
        # Database step
        created_parent_thing = models.Thing.query.filter_by(user_id=1).first()
        self.assertEqual(created_parent_thing.children[0].description, test_string)

    @raises(PermissionError)
    def test_create_permission(self):
        new_thing = self.sync(models.Thing, {'user_id': 2, 'description': "Hello."}, user=self.user)

    def test_update(self):
        self.sync(models.Thing, {'id': 1, 'description': "blergh"}, user=self.user)
        updated_thing = models.Thing.query.filter_by(id=1).first()
        self.assertEqual(updated_thing.description, "blergh")
        # Database step
        thing = models.Thing.query.filter_by(id=1).first()
        self.assertEqual(thing.description, "blergh")

    @raises(PermissionError)
    def test_update_permission(self):
        self.sync(models.Thing, {'id': 1, 'user_id': 2, 'description': "blergh"}, user=self.user)

    # Relationship stuffs
    # ------------------------------------------------------------------------

    def test_parent_create(self):
        parent = self.sync(models.Thing, {
            'children': [{
                'description': "Foobar"
            }],
            'user_id': 1,
            'description': "Foobaz"
        }, user=self.user)
        self.assertEqual(parent.description, "Foobaz")
        self.assertEqual(parent.children[0].description, "Foobar")
        # Database step
        created_thing = models.Thing.query.filter_by(description="Foobaz").first()
        self.assertEqual(created_thing.description, "Foobaz")
        self.assertEqual(created_thing.children[0].description, "Foobar")

    def test_parent_update(self):
        user = models.SyncUser.query.filter_by(id=3).first()
        old = self.sync(models.Thing, {
            'children': [{
                'description': 'Foobar'
             }],
            'user_id': user.id,
            'test': 'yo',
            'description': "Foobaz"
        }, user=user)
        old_id = old.children[0].id

        parent = self.sync(models.Thing, {
            'children': [{
                'id': old_id,
                'description': 'Boom blergh blegh' # I'm really good at this naming thing
            }],
            'id': old.id
        }, user=user)
        self.assertEqual(parent.children[0].id, old_id)
        self.assertEqual(parent.children[0].description, "Boom blergh blegh")
        # Database step
        thing = models.Thing.query.filter_by(user_id=3).first()
        self.assertEqual(thing.description, "Foobaz")
        self.assertEqual(thing.children[0].description, "Boom blergh blegh")

    def test_associate_existing(self):
        user = models.SyncUser.query.filter_by(id=3).first()
        child = self.sync(models.ChildThing, {
            'description': 'Foobar'
        }, user=user)

        parent = self.sync(models.Thing, {
            'children': [{
                'id': child.id,
                '_op': 'associate'
            }],
            'user_id': 3,
            'id': 1
        }, user=user)
        self.assertEqual(parent.children[0].description, 'Foobar')

        # Database step
        thing = models.Thing.query.filter_by(user_id=3).first()
        self.assertEqual(thing.children[0].description, "Foobar")

    def test_associate_1to1(self):
        user = models.SyncUser.query.filter_by(id=3).first()
        only_child = self.sync(models.ChildThing, {
            'description': 'Foobar'
        }, user=user)

        parent = self.sync(models.Thing, {
            'only_child': {
                'id': only_child.id,
                '_op': 'associate'
            },
            'user_id': 3,
            'id': 1
        }, user=user)
        self.assertEqual(parent.only_child.description, 'Foobar')

        # Database step
        thing = models.Thing.query.filter_by(user_id=3).first()
        self.assertEqual(thing.only_child.description, "Foobar")

    def test_associate_existing_1to1(self):
        user = models.SyncUser.query.filter_by(id=3).first()
        only_child = models.ChildThing.query.filter_by(id=3).first()

        parent = self.sync(models.Thing, {
            'only_child': {
                'id': only_child.id,
                '_op': 'associate'
            },
            'user_id': 3,
            'id': 1
        }, user=user)
        self.assertEqual(parent.only_child.description, 'Blergh')

        # Database step
        thing = models.Thing.query.filter_by(user_id=3).first()
        self.assertEqual(thing.only_child.description, 'Blergh')

    def test_disassociate_1to1(self):
        user = models.SyncUser.query.filter_by(id=3).first()
        only_child = self.sync(models.ChildThing, {
            'description': 'Foobar'
        }, user=user)

        parent = self.sync(models.Thing, {
            'only_child': {
                'id': only_child.id,
                '_op': 'associate'
            },
            'user_id': 3,
            'id': 1
        }, user=user)
        self.assertEqual(parent.only_child.description, 'Foobar')

        parent = self.sync(models.Thing, {
            'children': [{
                'id': only_child.id,
                '_op': 'disassociate'
            }],
            'user_id': 3,
            'id': 1
        }, user=user)
        self.assertEqual(parent.only_child, None)

        # Database step
        thing = models.Thing.query.filter_by(user_id=3).first()
        self.assertEqual(thing.only_child, None)

    @raises(PermissionError)
    def test_bad_association(self):
        # make sure users can't add objects to other users' objects via FK

        child = self.sync(models.ChildThing, {
            'description': 'Barf',
            'parent_id': 3  #owned by userid 2
        }, user=self.user)

    def test_disassociate(self):
        child = self.sync(models.ChildThing, {
            'description': 'Foobar'
        }, user=self.user)

        parent = self.sync(models.Thing, {
            'children': [{
                'id': child.id,
                '_op': 'associate'
            }],
            'user_id': 1,
            'id': 1
        }, user=self.user)

        parent = self.sync(models.Thing, {
            'children': [{
                'id': child.id,
                '_op': 'disassociate'
            }],
            'id': 1,
            }, user=self.user)
        self.assertEqual(len(parent.children), 0)

        # Database step
        thing = models.Thing.query.filter_by(user_id=1).first()
        self.assertEqual(thing.children, [])

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
