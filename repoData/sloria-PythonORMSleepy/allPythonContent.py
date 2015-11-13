__FILENAME__ = api_mongoengine
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Hello Mongoengine.'''
from datetime import datetime, timedelta

from flask import Flask, jsonify, request, render_template, abort
from flask.ext.classy import FlaskView
from flask.ext.mongoengine import MongoEngine
from marshmallow import fields, Serializer
import mongoengine as mdb


class Settings:
    MONGODB_SETTINGS = {
        "DB": "inventory",
    }
    DEBUG = True

app = Flask(__name__)
app.config.from_object(Settings)

### Models ###

db = MongoEngine(app)

class Item(db.Document):
    name = mdb.StringField(max_length=100, required=True)
    checked_out = mdb.BooleanField(default=False)
    updated = mdb.DateTimeField(default=datetime.utcnow)

    def __repr__(self):
        return '<Item {0!r}>'.format(self.name)


class Person(db.Document):
    firstname = mdb.StringField(max_length=80, required=True)
    lastname = mdb.StringField(max_length=80, required=True)
    created = mdb.DateTimeField(default=datetime.utcnow)
    # Denormalize the items collection because there are no joins in MongoDB
    items = mdb.ListField(mdb.ReferenceField(Item))

    def __repr__(self):
        return "<Person '{0} {1}'>".format(self.firstname, self.lastname)

def get_item_person(item):
    '''Get an item's parent person.'''
    return Person.objects(items__in=[item]).first()

### Custom Serializers ###

class PersonDocSerializer(Serializer):
    id = fields.String()
    name = fields.Function(lambda p: "{0}, {1}".format(p['lastname'], p['firstname']))
    created = fields.DateTime()
    n_items = fields.Function(lambda p: len(p['items']))

class ItemDocSerializer(Serializer):
    id = fields.String()
    person = fields.Method("get_person")
    class Meta:
        additional = ('name', 'checked_out', 'updated')

    def get_person(self, item):
        person = Person.objects(items__in=[item['id']]).first()
        return PersonDocSerializer(person._data).data

### API ###

class ItemsView(FlaskView):
    route_base = '/items/'

    def index(self):
        '''Get all items.'''
        all_items = Item.objects.order_by("-updated")
        # Serializer takes data dict for each item
        item_data = [item._data for item in all_items]
        data = ItemDocSerializer(item_data, many=True).data
        return jsonify({"items": data})

    def get(self, id):
        '''Get an item.'''
        try:
            item = Item.objects.get_or_404(id=id)
        except mdb.ValidationError:  # Invalid ID
            abort(404)
        return jsonify(ItemDocSerializer(item._data).data)

    def post(self):
        '''Insert a new item.'''
        data = request.json
        name = data.get("name", None)
        checked_out = data.get("checked_out", False)
        if not name:
            abort(400)
        item = Item(name=name, checked_out=checked_out)
        item.save()
        person_id = data.get("person_id")
        if person_id:
            person = Person.objects(id=person_id).first()
            if not person:
                abort(404)
            # Add item to person's items list
            person.items.append(item)
            person.save()
        return jsonify({"message": "Successfully added new item",
                        "item": ItemDocSerializer(item._data).data}), 201

    def delete(self, id):
        '''Delete an item.'''
        item = Item.objects.get_or_404(id=id)
        item.delete()
        return jsonify({"message": "Successfully deleted item.",
                        "id": str(item.id)}), 200

    def put(self, id):
        '''Update an item.'''
        item = Item.objects.get_or_404(id=id)
        # Update item
        item.name = request.json.get("name", item.name)
        item.checked_out = request.json.get("checked_out", item.checked_out)
        if request.json.get("person_id"):
            person = Person.objects(id=str(request.json['person_id'])).first()
            if person:
                # remove the item from its person's items list and add it to the
                # new person's items list
                old_person = get_item_person(item)
                old_person.items.remove(item)
                old_person.save()
                person.items.append(item)
            person.save()
        item.updated = datetime.utcnow()
        item.save()
        return jsonify({"message": "Successfully updated item.",
                        "item": ItemDocSerializer(item._data).data})


class PeopleView(FlaskView):
    route_base = '/people/'

    def index(self):
        '''Get all people, ordered by creation date.'''
        all_people = Person.objects.order_by("-created")
        people_data = [p._data for p in all_people]  # Data for serializer
        data = PersonDocSerializer(people_data, many=True).data
        return jsonify({"people": data})

    def get(self, id):
        '''Get a person.'''
        try:
            person = Person.objects.get_or_404(id=str(id))
        except mdb.ValidationError:  # Invalid ID
            abort(404)
        return jsonify(PersonDocSerializer(person._data).data)

    def post(self):
        '''Insert a new person.'''
        data = request.json
        firstname = data.get("firstname")
        lastname = data.get("lastname")
        if not firstname or not lastname:
            abort(400)
        person = Person(firstname=firstname, lastname=lastname)
        person.save()
        return jsonify({"message": "Successfully added new person.",
                        "person": PersonDocSerializer(person._data).data}), 201

    def delete(self, id):
        '''Delete a person.'''
        person = Person.objects.get_or_404(id=id)
        pid = person.id
        person.delete()
        return jsonify({"message": "Successfully deleted person.",
                        "id": str(pid)}), 200

class RecentCheckoutsView(FlaskView):
    '''Demonstrates a more complex query.'''

    route_base = '/recentcheckouts/'

    def index(self):
        '''Return items checked out in the past hour.'''
        hour_ago  = datetime.utcnow() - timedelta(hours=1)
        recent = Item.objects(checked_out=True, updated__gt=hour_ago)\
                                .order_by("-updated")
        recent_data = [i._data for i in recent]
        serialized = ItemDocSerializer(recent_data, many=True)
        return jsonify({"items": serialized.data})

@app.route("/")
def home():
    return render_template('index.html', orm="Mongoengine")

def drop_collections():
    Person.drop_collection()
    Item.drop_collection()

# Register views
api_prefix = "/api/v1/"
ItemsView.register(app, route_prefix=api_prefix)
PeopleView.register(app, route_prefix=api_prefix)
RecentCheckoutsView.register(app, route_prefix=api_prefix)

if __name__ == '__main__':
    app.run(port=5000)

########NEW FILE########
__FILENAME__ = api_peewee
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Hello Peewee.'''
from datetime import datetime, timedelta

from flask import Flask, jsonify, request, render_template, abort
from flask.ext.classy import FlaskView
from flask_peewee.db import Database
from flask_peewee.utils import get_object_or_404
import peewee as pw

from serializers import ItemSerializer, PersonSerializer


class Settings:
    DATABASE = {
        "name": "inventory.db",
        "engine": "peewee.SqliteDatabase"
    }
    DEBUG = True

app = Flask(__name__)
app.config.from_object(Settings)

### Models ###

db = Database(app)

class BaseModel(db.Model):
    def __marshallable__(self):
        '''Return marshallable dictionary for marshmallow support.'''
        return dict(self.__dict__)['_data']

class Person(BaseModel):
    firstname = pw.CharField(max_length=80, null=False)
    lastname = pw.CharField(max_length=80, null=False)
    created = pw.DateTimeField(default=datetime.utcnow)

    @property
    def n_items(self):
        return self.items.count()

    def __repr__(self):
        return "<Person '{0} {1}'>".format(self.firstname, self.lastname)

class Item(BaseModel):
    name = pw.CharField(max_length=100, null=False)
    person = pw.ForeignKeyField(Person, related_name="items", null=True)
    checked_out = pw.BooleanField(default=False)
    updated = pw.DateTimeField(default=datetime.utcnow)

    def __repr__(self):
        return '<Item {0!r}>'.format(self.name)


### API ###

class ItemsView(FlaskView):
    route_base = '/items/'

    def index(self):
        '''Get all items.'''
        all_items = Item.select().order_by(Item.updated.desc())
        data = ItemSerializer(all_items, many=True).data
        return jsonify({"items": data})

    def get(self, id):
        '''Get an item.'''
        # Could also use flask_peewee.utils.get_object_or_404
        try:
            item = Item.get(Item.id == id)
        except Item.DoesNotExist:
            abort(404)
        return jsonify(ItemSerializer(item).data)

    def post(self):
        '''Insert a new item.'''
        data = request.json
        name = data.get("name", None)
        checked_out = data.get('checked_out', False)
        if not name:
            abort(400)  # Must specify name
        person_id = data.get("person_id")
        if person_id:
            try:
                person = Person.get(Person.id == person_id)
            except Person.DoesNotExist:
                person = None
        else:
            person = None
        item = Item.create(name=name, person=person, checked_out=checked_out)
        return jsonify({"message": "Successfully added new item",
                        "item": ItemSerializer(item).data}), 201

    def delete(self, id):
        '''Delete an item.'''
        item = get_object_or_404(Item, Item.id == id)
        item.delete_instance()
        return jsonify({"message": "Successfully deleted item.",
                        "id": item.id}), 200

    def put(self, id):
        '''Update an item.'''
        item = get_object_or_404(Item, Item.id == id)
        # Update item
        item.name = request.json.get("name", item.name)
        item.checked_out = request.json.get("checked_out", item.checked_out)
        if request.json.get("person_id"):
            person = Person.get(Person.id == int(request.json['person_id']))
            item.person = person or item.person
        else:
            item.person = None
        item.updated = datetime.utcnow()
        item.save()
        return jsonify({"message": "Successfully updated item.",
                        "item": ItemSerializer(item).data})

class PeopleView(FlaskView):
    route_base = '/people/'

    def index(self):
        '''Get all people, ordered by creation date.'''
        all_items = Person.select().order_by(Person.created.desc())
        data = PersonSerializer(all_items, exclude=('created',), many=True).data
        return jsonify({"people": data})

    def get(self, id):
        '''Get a person.'''
        # Could also use flask_peewee.utils.get_object_or_404
        try:
            person = Person.get(Person.id == int(id))
        except Person.DoesNotExist:
            abort(404)
        return jsonify(PersonSerializer(person).data)

    def post(self):
        '''Insert a new person.'''
        data = request.json
        firstname = data.get("firstname")
        lastname = data.get("lastname")
        if not firstname or not lastname:
            abort(400)  # Must specify first and last name
        person = Person(firstname=firstname, lastname=lastname)
        person.save()
        return jsonify({"message": "Successfully added new person.",
                        "person": PersonSerializer(person).data}), 201

    def delete(self, id):
        '''Delete a person.'''
        person = get_object_or_404(Person, Person.id == int(id))
        pid = person.id
        person.delete_instance()
        return jsonify({"message": "Successfully deleted person.",
                        "id": pid}), 200

class RecentCheckoutsView(FlaskView):
    '''Demonstrates a more complex query.'''

    route_base = '/recentcheckouts/'

    def index(self):
        '''Return items checked out in the past hour.'''
        hour_ago  = datetime.utcnow() - timedelta(hours=1)
        query = Item.select().where(Item.checked_out &
                                    (Item.updated > hour_ago)) \
                                    .order_by(Item.updated.desc())
        recent = [item for item in query]  # Executes query
        return jsonify({"items": ItemSerializer(recent, many=True).data})

@app.route("/")
def home():
    return render_template('index.html', orm="Peewee")

def create_tables():
    Person.create_table(True)
    Item.create_table(True)

def drop_tables():
    Person.drop_table(True)
    Item.drop_table(True)

# Register views
api_prefix = "/api/v1/"
ItemsView.register(app, route_prefix=api_prefix)
PeopleView.register(app, route_prefix=api_prefix)
RecentCheckoutsView.register(app, route_prefix=api_prefix)

if __name__ == '__main__':
    create_tables()
    app.run(port=5000)

########NEW FILE########
__FILENAME__ = api_pony
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Hello Pony.'''
from datetime import datetime, timedelta

from flask import Flask, jsonify, request, render_template, abort
from flask.ext.classy import FlaskView
from pony import orm

from serializers import ItemSerializer, PersonSerializer


class Settings:
    DB_PROVIDER = "sqlite"
    DB_NAME = "inventory.db"
    DEBUG = True

app = Flask(__name__)
app.config.from_object(Settings)

### Models ###

db = orm.Database('sqlite', 'inventory.db', create_db=True)


class Person(db.Entity):
    _table_ = 'people'
    firstname = orm.Required(unicode, 80, nullable=False)
    lastname = orm.Required(unicode, 80, nullable=False)
    created = orm.Required(datetime, default=datetime.utcnow)
    items = orm.Set("Item")

    @property
    def n_items(self):
        return orm.count(item for item in self.items)

    def __repr__(self):
        return "<Person '{0} {1}'>".format(self.firstname, self.lastname)


class Item(db.Entity):
    _table_ = 'items'
    name = orm.Required(unicode, 100, nullable=False)
    person = orm.Optional(Person)
    checked_out = orm.Required(bool, default=False)
    updated = orm.Required(datetime, default=datetime.utcnow)

    def __repr__(self):
        return '<Item {0!r}>'.format(self.name)


### API ###

class ItemsView(FlaskView):
    route_base = '/items/'

    def index(self):
        '''Get all items.'''
        all_items = orm.select(item for item in Item)\
                                .order_by(orm.desc(Item.updated))[:]
        data = ItemSerializer(all_items, many=True).data
        return jsonify({"items": data})

    def get(self, id):
        '''Get an item.'''
        try:
            item = Item[id]
        except orm.ObjectNotFound:
            abort(404)
        return jsonify(ItemSerializer(item).data)

    def post(self):
        '''Insert a new item.'''
        data = request.json
        name = data.get("name", None)
        checked_out = data.get('checked_out', False)
        if not name:
            abort(400)
        pid = data.get("person_id")
        if pid:
            person = Person.get(id=pid)  # None if not found
        else:
            person = None
        item = Item(name=name, person=person, checked_out=checked_out)
        orm.commit()
        return jsonify({"message": "Successfully added new item",
                        "item": ItemSerializer(item).data}), 201

    def delete(self, id):
        '''Delete an item.'''
        try:
            item = Item[id]
        except orm.ObjectNotFound:
            abort(404)
        item.delete()
        orm.commit()
        return jsonify({"message": "Successfully deleted item.",
                        "id": id}), 200

    def put(self, id):
        '''Update an item.'''
        try:
            item = Item[id]
        except orm.ObjectNotFound:
            abort(404)
        # Update item
        item.name = request.json.get("name", item.name)
        item.checked_out = request.json.get("checked_out", item.checked_out)
        pid = request.json.get("person_id")
        if pid:
            person = Person.get(id=pid)
            item.person = person or item.person
        else:
            item.person = None
        item.updated = datetime.utcnow()
        orm.commit()
        return jsonify({"message": "Successfully updated item.",
                        "item": ItemSerializer(item).data})

class PeopleView(FlaskView):
    route_base = '/people/'

    def index(self):
        '''Get all people, ordered by creation date.'''
        all_people = orm.select(p for p in Person).order_by(orm.desc(Person.created))[:]
        data = PersonSerializer(all_people, many=True, exclude=('created',)).data
        return jsonify({"people": data})

    def get(self, id):
        '''Get a person.'''
        try:
            person = Person[id]
        except orm.ObjectNotFound:
            abort(404)
        return jsonify(PersonSerializer(person).data)

    def post(self):
        '''Insert a new person.'''
        data = request.json
        firstname = data.get("firstname")
        lastname = data.get("lastname")
        if not firstname or not lastname:
            abort(400)  # Must specify both first and last name
        person = Person(firstname=firstname, lastname=lastname)
        orm.commit()
        return jsonify({"message": "Successfully added new person.",
                        "person": PersonSerializer(person).data}), 201

    def delete(self, id):
        '''Delete a person.'''
        try:
            person = Person[id]
        except orm.ObjectNotFound:
            abort(404)
        person.delete()
        orm.commit()
        return jsonify({"message": "Successfully deleted person.",
                        "id": id}), 200

class RecentCheckoutsView(FlaskView):
    '''Demonstrates a more complex query.'''
    route_base = '/recentcheckouts/'

    def index(self):
        '''Return items checked out in the past hour.'''
        hour_ago  = datetime.utcnow() - timedelta(hours=1)
        recent = orm.select(item for item in Item
                                if item.checked_out and
                                    item.updated > hour_ago)\
                                    .order_by(Item.updated.desc())[:]
        return jsonify({"items": ItemSerializer(recent, many=True).data})

@app.route("/")
def home():
    return render_template('index.html', orm="Pony ORM")

# Generate object-database mapping
db.generate_mapping(check_tables=False)

# Register views
api_prefix = "/api/v1/"
ItemsView.register(app, route_prefix=api_prefix)
PeopleView.register(app, route_prefix=api_prefix)
RecentCheckoutsView.register(app, route_prefix=api_prefix)


if __name__ == '__main__':
    db.create_tables()
    # Make sure each thread gets a db session
    app.wsgi_app = orm.db_session(app.wsgi_app)
    app.run(port=5000)

########NEW FILE########
__FILENAME__ = api_sqlalchemy
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Hello SQLAlchemy.'''
from datetime import datetime, timedelta

from flask import Flask, jsonify, request, render_template, abort
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.classy import FlaskView

from serializers import ItemSerializer, PersonSerializer


class Settings:
    DB_NAME = "inventory.db"
    # Put the db file in project root
    SQLALCHEMY_DATABASE_URI = "sqlite:///{0}".format(DB_NAME)
    DEBUG = True

app = Flask(__name__)
app.config.from_object(Settings)

### Models ###

db = SQLAlchemy()
db.init_app(app)

class Person(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(80), nullable=False)
    lastname = db.Column(db.String(80), nullable=False)
    created = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def n_items(self):
        return len(self.items)

    def __repr__(self):
        return "<Person '{0} {1}'>".format(self.firstname, self.lastname)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    person_id = db.Column(db.Integer, db.ForeignKey('person.id'), nullable=True)
    person = db.relationship("Person", backref=db.backref("items"))
    checked_out = db.Column(db.Boolean, default=False)
    updated = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return '<Item {0!r}>'.format(self.name)


### API ###

class ItemsView(FlaskView):
    route_base = '/items/'

    def index(self):
        '''Get all items.'''
        all_items = Item.query.order_by(Item.updated.desc()).all()
        data = ItemSerializer(all_items, many=True).data
        return jsonify({"items": data})

    def get(self, id):
        '''Get an item.'''
        item = Item.query.get_or_404(int(id))
        return jsonify(ItemSerializer(item).data)

    def post(self):
        '''Insert a new item.'''
        data = request.json
        name = data.get("name", None)
        checked_out = data.get("checked_out", False)
        if not name:
            abort(400)
        person = Person.query.filter_by(id=data.get("person_id", None)).first()
        item = Item(name=name, person=person, checked_out=checked_out)
        db.session.add(item)
        db.session.commit()
        return jsonify({"message": "Successfully added new item",
                        "item": ItemSerializer(item).data}), 201

    def delete(self, id):
        '''Delete an item.'''
        item = Item.query.get_or_404(int(id))
        db.session.delete(item)
        db.session.commit()
        return jsonify({"message": "Successfully deleted item.",
                        "id": item.id}), 200

    def put(self, id):
        '''Update an item.'''
        item = Item.query.get_or_404(int(id))
        # Update item
        item.name = request.json.get("name", item.name)
        item.checked_out = request.json.get("checked_out", item.checked_out)
        if request.json.get("person_id"):
            person = Person.query.get(int(request.json['person_id']))
            item.person = person or item.person
        else:
            item.person = None
        item.updated = datetime.utcnow()
        db.session.add(item)
        db.session.commit()
        return jsonify({"message": "Successfully updated item.",
                        "item": ItemSerializer(item).data})

class PeopleView(FlaskView):
    route_base = '/people/'

    def index(self):
        '''Get all people, ordered by creation date.'''
        all_people = Person.query.order_by(Person.created.desc()).all()
        data = PersonSerializer(all_people, exclude=('created',), many=True).data
        return jsonify({"people": data})

    def get(self, id):
        '''Get a person.'''
        person = Person.query.get_or_404(int(id))
        return jsonify(PersonSerializer(person).data)

    def post(self):
        '''Insert a new person.'''
        data = request.json
        firstname = data.get("firstname")
        lastname = data.get("lastname")
        if not firstname or not lastname:
            abort(400)  # Must specify both first and last name
        person = Person(firstname=firstname, lastname=lastname)
        db.session.add(person)
        db.session.commit()
        return jsonify({"message": "Successfully added new person.",
                        "person": PersonSerializer(person).data}), 201

    def delete(self, id):
        '''Delete a person.'''
        person = Person.query.get_or_404(int(id))
        db.session.delete(person)
        db.session.commit()
        return jsonify({"message": "Successfully deleted person.",
                        "id": person.id}), 200

class RecentCheckoutsView(FlaskView):
    '''Demonstrates a more complex query.'''
    route_base = '/recentcheckouts/'

    def index(self):
        '''Return items checked out in the past hour.'''
        hour_ago  = datetime.utcnow() - timedelta(hours=1)
        recent = Item.query.filter(Item.checked_out &
                                    (Item.updated > hour_ago)) \
                                    .order_by(Item.updated.desc()).all()
        return jsonify({"items": ItemSerializer(recent, many=True).data})

@app.route("/")
def home():
    return render_template('index.html', orm="SQLAlchemy")

# Register views
api_prefix = "/api/v1/"
ItemsView.register(app, route_prefix=api_prefix)
PeopleView.register(app, route_prefix=api_prefix)
RecentCheckoutsView.register(app, route_prefix=api_prefix)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(port=5000)

########NEW FILE########
__FILENAME__ = api_stdnet
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Hello Stdnet.'''
import logging
from datetime import datetime, timedelta

from flask import Flask, jsonify, request, render_template, abort
from flask.ext.classy import FlaskView
from stdnet import odm
from serializers import ItemSerializer, PersonSerializer


class Settings:
    REDIS_URL = 'redis://'
    DEBUG = True

app = Flask(__name__)
app.config.from_object(Settings)

### Models ###

models = odm.Router(app.config['REDIS_URL'])

class Person(odm.StdModel):
    firstname = odm.CharField(required=True)
    lastname = odm.CharField(required=True)
    created = odm.DateTimeField(default=datetime.utcnow)

    @property
    def n_items(self):
        return len(self.items.all())

    def __unicode__(self):
        return "<Person '{0} {1}'>".format(self.firstname, self.lastname)


class Item(odm.StdModel):
    name = odm.CharField(required=True)
    person = odm.ForeignKey(Person, related_name='items', required=False)
    checked_out = odm.BooleanField(default=False)
    updated = odm.DateTimeField(default=datetime.utcnow)

    def __unicode__(self):
        return '<Item {0!r}>'.format(self.name)


### API ###

class ItemsView(FlaskView):
    route_base = '/items/'

    def index(self):
        '''Get all items.'''
        all_items = models.item.query().sort_by("-updated").all()
        data = ItemSerializer(all_items, many=True).data
        return jsonify({"items": data})

    def get(self, id):
        '''Get an item.'''
        try:
            item = models.item.query().get(id=id)
        except Item.DoesNotExist:
            abort(404)
        return jsonify(ItemSerializer(item).data)

    def post(self):
        '''Insert a new item.'''
        data = request.json
        name = data.get("name", None)
        person_id = data.get("person_id")
        person = None
        checked_out = data.get("checked_out", False)
        if not name:
            abort(400)
        if person_id:
            try:
                person = models.person.query().get(id=person_id)
            except Person.DoesNotExist:
                pass
        item = models.item.new(name=name, person=person, checked_out=checked_out)
        return jsonify({"message": "Successfully added new item",
                        "item": ItemSerializer(item).data}), 201

    def delete(self, id):
        '''Delete an item.'''
        try:
            item = models.item.query().get(id=id)
        except Item.DoesNotExist:
            abort(404)
        item.delete()
        return jsonify({"message": "Successfully deleted item.",
                        "id": item.id}), 200

    def put(self, id):
        '''Update an item.'''
        try:
            item = models.item.query().get(id=int(id))
        except Item.DoesNotExist:
            abort(404)
        # Update item
        item.name = request.json.get("name", item.name)
        item.checked_out = request.json.get("checked_out", item.checked_out)
        if request.json.get("person_id"):
            try:
                person = models.person.get(id=int(request.json['person_id']))
            except Person.DoesNotExist:
                abort(404)
            item.person = person or item.person
        else:
            item.person = None
        item.updated = datetime.utcnow()
        item.save()
        return jsonify({"message": "Successfully updated item.",
                        "item": ItemSerializer(item).data})

class PeopleView(FlaskView):
    route_base = '/people/'

    def index(self):
        '''Get all people, ordered by creation date.'''
        all_people = models.person.query().sort_by("-created")
        data = PersonSerializer(all_people, exclude=('created',), many=True).data
        return jsonify({"people": data})

    def get(self, id):
        '''Get a person.'''
        try:
            person = models.person.query().get(id=id)
        except Person.DoesNotExist:
            abort(404)
        return jsonify(PersonSerializer(person).data)

    def post(self):
        '''Insert a new person.'''
        data = request.json
        firstname = data.get("firstname")
        lastname = data.get("lastname")
        if not firstname or not lastname:
            abort(400)  # Must specify both first and last name
        person = models.person.new(firstname=firstname, lastname=lastname)
        person.save()
        return jsonify({"message": "Successfully added new person.",
                        "person": PersonSerializer(person).data}), 201

    def delete(self, id):
        '''Delete a person.'''
        try:
            person = models.person.query().get(id=id)
        except Person.DoesNotExist:
            abort(404)
        person.delete()
        return jsonify({"message": "Successfully deleted person.",
                        "id": person.id}), 200

class RecentCheckoutsView(FlaskView):
    '''Demonstrates a more complex query.'''
    route_base = '/recentcheckouts/'

    def index(self):
        '''Return items checked out in the past hour.'''
        hour_ago  = datetime.utcnow() - timedelta(hours=1)
        recent = models.item.filter(checked_out=True).sort_by("-updated").all()
        return jsonify({"items": ItemSerializer(recent, many=True).data})

@app.route("/")
def home():
    return render_template('index.html', orm="Stdnet")

def register_models(router):
    router.register(Item)
    router.register(Person)
    return router

# Register views
api_prefix = "/api/v1/"
ItemsView.register(app, route_prefix=api_prefix)
PeopleView.register(app, route_prefix=api_prefix)
RecentCheckoutsView.register(app, route_prefix=api_prefix)

# Register models
register_models(models)

if __name__ == '__main__':
    app.run(port=5000)

########NEW FILE########
__FILENAME__ = serializers
'''Serializers common to all apps.'''

from marshmallow import Serializer, fields


class PersonSerializer(Serializer):
    id = fields.Integer()
    name = fields.Function(lambda p: "{0}, {1}".format(p.lastname, p.firstname))
    created = fields.DateTime()
    n_items = fields.Integer()


class ItemSerializer(Serializer):
    person = fields.Nested(PersonSerializer, only=('id', 'name'), allow_null=True)

    class Meta:
        additional = ('id', 'name', 'checked_out', 'updated')

########NEW FILE########
__FILENAME__ = test_mongoengine_app
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import time
from nose.tools import *  # PEP8 asserts
from flask.ext.testing import TestCase

from flask import json
from sleepy.api_mongoengine import (Person, Item, app, drop_collections,
                                    ItemDocSerializer, get_item_person)


class TestMongoengineAPI(TestCase):
    TESTING = True
    MONGODB_SETTINGS = {
        "DB": "_test_inventory"
    }
    DEBUG = True

    def create_app(self):
        app.config.from_object(self)
        return app

    def setUp(self):
        # create some items
        self.person = Person(firstname="Steve", lastname="Loria")
        self.person2 = Person(firstname="Monty", lastname="Python")
        self.item = Item(name="Foo")
        self.item.save()
        self.person.items.append(self.item)
        self.person.save()
        self.item2 = Item(name="Bar")
        self.person2.save()
        self.item2.save()

    def tearDown(self):
        drop_collections()

    def test_get_items(self):
        url = "/api/v1/items/"
        res = self.client.get(url)
        data = res.json
        assert_equal(res.status_code, 200)
        assert_equal(len(data['items']), 2)
        assert_equal(data['items'][0]['name'], self.item2.name)

    def test_get_item(self):
        url = '/api/v1/items/{0}'.format(self.item.id)
        res = self.client.get(url)
        data = res.json
        assert_equal(res.status_code, 200)
        assert_equal(data['name'], self.item.name)
        assert_equal(data['person']['id'], str(self.person.id))

    def test_get_persons(self):
        res = self.client.get('/api/v1/people/')
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['people']), len(Person.objects))

    def test_get_person(self):
        res = self.client.get('/api/v1/people/{0}'.format(self.person.id))
        assert_equal(res.status_code, 200)
        assert_equal(res.json['name'], "{0}, {1}".format(self.person.lastname,
                                                        self.person.firstname))
        assert_equal(res.json['n_items'], 1)

    def test_get_nonexistent_person(self):
        res = self.client.get("/api/v1/people/10")
        assert_equal(res.status_code, 404)

    def _post_json(self, url, data):
        return self.client.post(url,
                                data=json.dumps(data),
                                content_type='application/json')

    def _put_json(self, url, data):
        return self.client.put(url,
                                data=json.dumps(data),
                                content_type='application/json')

    def test_post_item(self):
        res = self._post_json("/api/v1/items/", {"name": "Ipad", 'checked_out': True})
        assert_equal(res.status_code, 201)
        item = Item.objects.order_by("-updated").first()
        assert_true(item is not None)
        assert_equal(item.name, "Ipad")
        assert_true(item.checked_out)

    def test_post_item_with_person_id(self):
        res = self._post_json('/api/v1/items/',
                              {"name": "Ipod", "person_id": str(self.person.id)})
        assert_equal(res.status_code, 201)
        item = Item.objects.first()
        person = get_item_person(item)
        assert_equal(person, self.person)

    def test_post_person(self):
        res = self._post_json('/api/v1/people/',
                            {'firstname': 'Foo', 'lastname': 'Bar'})
        assert_equal(res.status_code, 201)
        person = Person.objects.order_by("-created").first()
        assert_equal(person.firstname, "Foo")
        assert_equal(person.lastname, "Bar")

    def test_delete_item(self):
        all_items = Item.objects
        assert_in(self.item, all_items)
        res = self.client.delete("/api/v1/items/{0}".format(self.item.id))
        all_items = Item.objects
        assert_not_in(self.item, all_items)

    def test_put_item(self):
        res = self._put_json("/api/v1/items/{0}".format(self.item.id),
                            {"checked_out": True,
                            "person_id": str(self.person2.id)})
        item = Item.objects(id=self.item.id).first()
        assert_true(item.checked_out)
        item_person = get_item_person(item)
        assert_equal(item_person, self.person2)

    def test_delete_person(self):
        all_persons = Person.objects
        assert_in(self.person, all_persons)
        self.client.delete('/api/v1/people/{0}'.format(self.person.id))
        all_persons = Person.objects
        assert_not_in(self.person, all_persons)

    def test_recent(self):
        self.item.checked_out = True
        self.item2.checked_out = False
        self.item.save()
        self.item2.save()
        res = self.client.get("/api/v1/recentcheckouts/")
        assert_in(ItemDocSerializer(self.item._data).data, res.json['items'])
        assert_not_in(ItemDocSerializer(self.item2._data).data, res.json['items'])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_peewee_app
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
from nose.tools import *  # PEP8 asserts
from flask.ext.testing import TestCase

from flask import json
from sleepy.api_peewee import Person, Item, db, app, create_tables, drop_tables
from sleepy.serializers import ItemSerializer


class TestPeeweeAPI(TestCase):
    TESTING = True
    DATABASE = {
        "name": "/tmp/test.db",
        "engine": "peewee.SqliteDatabase"
    }
    DEBUG = True

    def create_app(self):
        app.config.from_object(self)
        return app

    def setUp(self):
        create_tables()
        # create some items
        self.person = Person.create(firstname="Steve", lastname="Loria")
        self.person2 = Person.create(firstname="Monty", lastname="Python")
        self.item = Item.create(name="Foo", person=self.person)
        self.item2 = Item.create(name="Bar")

    def tearDown(self):
        drop_tables()

    def test_get_items(self):
        url = "/api/v1/items/"
        res = self.client.get(url)
        data = res.json
        assert_equal(res.status_code, 200)
        assert_equal(len(data['items']), 2)
        assert_equal(data['items'][0]['name'], self.item2.name)

    def test_get_item(self):
        url = '/api/v1/items/{0}'.format(self.item.id)
        res = self.client.get(url)
        data = res.json
        assert_equal(res.status_code, 200)
        assert_equal(data['name'], self.item.name)
        assert_equal(data['person']['id'], self.person.id)

    def test_get_persons(self):
        res = self.client.get('/api/v1/people/')
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['people']), 2)
        assert_equal(res.json['people'][0]['name'],
                    "{0}, {1}".format(self.person2.lastname, self.person2.firstname))

    def test_get_person(self):
        res = self.client.get('/api/v1/people/{0}'.format(self.person.id))
        assert_equal(res.status_code, 200)
        assert_equal(res.json['name'], "{0}, {1}".format(self.person.lastname,
                                                        self.person.firstname))
        assert_equal(res.json['n_items'], 1)


    def test_get_nonexistent_person(self):
        res = self.client.get("/api/v1/people/10")
        assert_equal(res.status_code, 404)

    def _post_json(self, url, data):
        return self.client.post(url,
                                data=json.dumps(data),
                                content_type='application/json')

    def _put_json(self, url, data):
        return self.client.put(url,
                                data=json.dumps(data),
                                content_type='application/json')

    def test_post_item(self):
        res = self._post_json("/api/v1/items/", {"name": "Ipad", 'checked_out': True})
        assert_equal(res.status_code, 201)
        item = Item.select().order_by(Item.updated.desc()).first()
        assert_true(item is not None)
        assert_equal(item.name, "Ipad")
        assert_true(item.checked_out)

    def test_post_item_with_person_id(self):
        res = self._post_json('/api/v1/items/',
                              {"name": "Ipod", "person_id": self.person.id})
        assert_equal(res.status_code, 201)
        item = Item.select().order_by(Item.updated.desc()).first()
        assert_equal(item.person, self.person)

    def test_post_person(self):
        res = self._post_json('/api/v1/people/',
                            {'firstname': 'Steven', 'lastname': 'Loria'})
        assert_equal(res.status_code, 201)
        person = Person.select().order_by(Person.created.desc()).first()
        assert_equal(person.firstname, "Steven")
        assert_equal(person.lastname, "Loria")

    def test_delete_item(self):
        all_items = [i for i in Item.select()]
        assert_in(self.item, all_items)
        res = self.client.delete("/api/v1/items/{0}".format(self.item.id))
        all_items = [i for i in Item.select()]
        assert_not_in(self.item, all_items)

    def test_put_item(self):
        res = self._put_json("/api/v1/items/{0}".format(self.item.id),
                            {"checked_out": True,
                            "person_id": self.person2.id})
        item = Item.get(Item.id == self.item.id)
        assert_true(item.checked_out)
        assert_equal(item.person, self.person2)

    def test_delete_person(self):
        all_persons = [p for p in Person.select()]
        assert_in(self.person, all_persons)
        self.client.delete('/api/v1/people/{0}'.format(self.person.id))
        all_persons = [p for p in Person.select()]
        assert_not_in(self.person, all_persons)

    def test_recent(self):
        self.item.checked_out = True
        self.item2.checked_out = False
        self.item.save()
        self.item2.save()
        res = self.client.get("/api/v1/recentcheckouts/")
        assert_in(ItemSerializer(self.item).data, res.json['items'])
        assert_not_in(ItemSerializer(self.item2).data, res.json['items'])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_pony_app
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
from nose.tools import *  # PEP8 asserts
from flask.ext.testing import TestCase
from flask import json

from sleepy.api_pony import Person, Item, app, db
from sleepy.serializers import ItemSerializer
from pony import orm
from pony.orm import db_session


class TestPonyAPI(TestCase):
    '''WARNING: This test case drops all the tables in the dev db.'''

    TESTING = True
    DEBUG = True

    def create_app(self):
        app.config.from_object(self)
        return app

    def setUp(self):
        db.create_tables()
        # create some items
        with db_session:
            self.person = Person(firstname="Steve", lastname="Loria")
            self.person2 = Person(firstname="Monty", lastname="Python")
            self.item = Item(name="Foo", person=self.person)
            self.item2 = Item(name="Bar")

    def tearDown(self):
        db.drop_all_tables(with_all_data=True)

    @db_session
    def test_get_items(self):
        url = "/api/v1/items/"
        res = self.client.get(url)
        data = res.json
        item = Item[self.item2.id]
        assert_equal(res.status_code, 200)
        assert_equal(len(data['items']), 2)
        assert_equal(data['items'][0]['name'], item.name)

    @db_session
    def test_get_item(self):
        url = '/api/v1/items/{0}'.format(self.item.id)
        res = self.client.get(url)
        data = res.json
        item = Item[self.item.id]
        assert_equal(res.status_code, 200)
        assert_equal(data['name'], item.name)
        assert_equal(data['person']['id'], self.person.id)

    @db_session
    def test_get_persons(self):
        res = self.client.get('/api/v1/people/')
        person = Person[self.person2.id]
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['people']), 2)
        assert_equal(res.json['people'][0]['name'],
                    "{0}, {1}".format(person.lastname, person.firstname))

    @db_session
    def test_get_person(self):
        res = self.client.get('/api/v1/people/{0}'.format(self.person.id))
        assert_equal(res.status_code, 200)
        person = Person[self.person.id]
        assert_equal(res.json['name'], "{0}, {1}".format(person.lastname,
                                                        person.firstname))
        assert_equal(res.json['n_items'], 1)

    @db_session
    def test_get_nonexistent_person(self):
        res = self.client.get("/api/v1/people/10")
        assert_equal(res.status_code, 404)

    def _post_json(self, url, data):
        return self.client.post(url,
                                data=json.dumps(data),
                                content_type='application/json')

    def _put_json(self, url, data):
        return self.client.put(url,
                                data=json.dumps(data),
                                content_type='application/json')
    @db_session
    def test_post_item(self):
        res = self._post_json("/api/v1/items/", {"name": "Ipad", 'checked_out': True})
        assert_equal(res.status_code, 201)
        item = list(Item.select())[-1]
        assert_true(item is not None)
        assert_equal(item.name, "Ipad")
        assert_true(item.checked_out)

    @db_session
    def test_post_item_with_person_id(self):
        res = self._post_json('/api/v1/items/',
                              {"name": "Ipod", "person_id": self.person.id})
        assert_equal(res.status_code, 201)
        item = list(Item.select())[-1]
        person = Person[self.person.id]
        assert_equal(item.person, person)

    @db_session
    def test_post_person(self):
        res = self._post_json('/api/v1/people/',
                            {'firstname': 'Steven', 'lastname': 'Loria'})
        assert_equal(res.status_code, 201)
        person = list(Person.select())[-1]
        assert_equal(person.firstname, "Steven")
        assert_equal(person.lastname, "Loria")

    @db_session
    def test_delete_item(self):
        item = Item[self.item.id]
        assert_in(item, Item.select()[:])
        res = self.client.delete("/api/v1/items/{0}".format(self.item.id))
        assert_not_in(self.item, Item.select())

    @db_session
    def test_put_item(self):
        item = Item[self.item.id]
        person = Person[self.person2.id]
        res = self._put_json("/api/v1/items/{0}".format(item.id),
                            {"checked_out": True,
                            "person_id": self.person2.id})
        assert_true(item.checked_out)
        assert_equal(item.person, person)

    @db_session
    def test_delete_person(self):
        person = Person[self.person.id]
        assert_in(person, Person.select()[:])
        self.client.delete('/api/v1/people/{0}'.format(self.person.id))
        assert_not_in(person, Person.select()[:])

    @db_session
    def test_recent(self):
        item = Item[self.item.id]
        item2 = Item[self.item2.id]
        item.checked_out = True
        item2.checked_out = False
        orm.commit()
        res = self.client.get("/api/v1/recentcheckouts/")
        assert_in(ItemSerializer(item).data, res.json['items'])
        assert_not_in(ItemSerializer(item2).data, res.json['items'])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_sqlalchemy_app
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
from nose.tools import *  # PEP8 asserts
from flask.ext.testing import TestCase

from flask import json
from sleepy.api_sqlalchemy import Person, Item, db, app
from sleepy.serializers import ItemSerializer


class TestSQLAlchemyAPI(TestCase):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'

    def create_app(self):
        app.config.from_object(self)
        return app

    def setUp(self):
        db.create_all()
        # create some items
        self.person = Person(firstname="Steve", lastname="Loria")
        self.person2 = Person(firstname="Monty", lastname="Python")
        self.item = Item(name="Foo", person=self.person)
        self.item2 = Item(name="Bar")
        db.session.add_all([self.person, self.person2, self.item, self.item2])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_get_items(self):
        url = "/api/v1/items/"
        res = self.client.get(url)
        data = res.json
        assert_equal(res.status_code, 200)
        assert_equal(len(data['items']), 2)
        assert_equal(data['items'][0]['name'], self.item2.name)

    def test_get_item(self):
        url = '/api/v1/items/{0}'.format(self.item.id)
        res = self.client.get(url)
        data = res.json
        assert_equal(res.status_code, 200)
        assert_equal(data['name'], self.item.name)
        assert_equal(data['person']['id'], self.person.id)

    def test_get_persons(self):
        res = self.client.get('/api/v1/people/')
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['people']), 2)
        assert_equal(res.json['people'][0]['name'],
                    "{0}, {1}".format(self.person2.lastname, self.person2.firstname))

    def test_get_person(self):
        res = self.client.get('/api/v1/people/{0}'.format(self.person.id))
        assert_equal(res.status_code, 200)
        assert_equal(res.json['name'], "{0}, {1}".format(self.person.lastname,
                                                        self.person.firstname))
        assert_equal(res.json['n_items'], 1)


    def test_get_nonexistent_person(self):
        res = self.client.get("/api/v1/people/10")
        assert_equal(res.status_code, 404)

    def _post_json(self, url, data):
        return self.client.post(url,
                                data=json.dumps(data),
                                content_type='application/json')

    def _put_json(self, url, data):
        return self.client.put(url,
                                data=json.dumps(data),
                                content_type='application/json')

    def test_post_item(self):
        res = self._post_json("/api/v1/items/", {"name": "Ipad", "checked_out": True})
        assert_equal(res.status_code, 201)
        item = Item.query.all()[-1]
        assert_true(item is not None)
        assert_equal(item.name, "Ipad")
        assert_true(item.checked_out)

    def test_post_item_with_person_id(self):
        res = self._post_json('/api/v1/items/',
                              {"name": "Ipod", "person_id": self.person.id})
        assert_equal(res.status_code, 201)
        item = Item.query.all()[-1]
        assert_equal(item.person, self.person)

    def test_post_person(self):
        res = self._post_json('/api/v1/people/',
                            {'firstname': 'Steven', 'lastname': 'Loria'})
        assert_equal(res.status_code, 201)
        person = Person.query.all()[-1]
        assert_equal(person.firstname, "Steven")
        assert_equal(person.lastname, "Loria")

    def test_delete_item(self):
        assert_in(self.item, Item.query.all())
        res = self.client.delete("/api/v1/items/{0}".format(self.item.id))
        assert_not_in(self.item, Item.query.all())

    def test_put_item(self):
        res = self._put_json("/api/v1/items/{0}".format(self.item.id),
                            {"checked_out": True,
                            "person_id": self.person2.id})
        assert_true(self.item.checked_out)
        assert_equal(self.item.person, self.person2)

    def test_delete_person(self):
        all_persons = Person.query.all()
        assert_in(self.person, all_persons)
        self.client.delete('/api/v1/people/{0}'.format(self.person.id))
        all_persons = Person.query.all()
        assert_not_in(self.person, all_persons)

    def test_recent(self):
        self.item.checked_out = True
        self.item2.checked_out = False
        db.session.add_all([self.item, self.item2])
        db.session.commit()
        res = self.client.get("/api/v1/recentcheckouts/")
        assert_in(ItemSerializer(self.item).data, res.json['items'])
        assert_not_in(ItemSerializer(self.item2).data, res.json['items'])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_stdnet_app
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import time
from nose.tools import *  # PEP8 asserts
from flask.ext.testing import TestCase
from flask import json
from stdnet import odm

from sleepy.api_stdnet import app, register_models
from sleepy.serializers import ItemSerializer

models = odm.Router('redis://localhost:6379')


class TestStdnetAPI(TestCase):
    TESTING = True
    DEBUG = True

    def create_app(self):
        app.config.from_object(self)
        register_models(models)
        return app

    def setUp(self):
        # create some items
        self.person = models.person.new(firstname="Steve", lastname="Loria")
        self.person2 = models.person.new(firstname="Monty", lastname="Python")
        self.item = models.item.new(name="Foo", person=self.person)
        self.item.save()
        self.person.save()
        self.item2 = models.item.new(name="Bar")
        self.person2.save()
        self.item2.save()

    def tearDown(self):
        models.flush()

    def test_get_items(self):
        url = "/api/v1/items/"
        res = self.client.get(url)
        data = res.json
        assert_equal(res.status_code, 200)
        assert_equal(len(data['items']), 2)
        assert_equal(data['items'][0]['name'], self.item2.name)

    def test_get_item(self):
        url = '/api/v1/items/{0}'.format(self.item.id)
        res = self.client.get(url)
        data = res.json
        assert_equal(res.status_code, 200)
        assert_equal(data['name'], self.item.name)
        assert_equal(data['person']['id'], self.person.id)

    def test_get_nonexistent_item(self):
        url = '/api/v1/items/{0}'.format("abc")
        res = self.client.get(url)
        assert_equal(res.status_code, 404)

    def test_get_persons(self):
        res = self.client.get('/api/v1/people/')
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['people']), models.person.query().count())

    def test_get_person(self):
        res = self.client.get('/api/v1/people/{0}'.format(self.person.id))
        assert_equal(res.status_code, 200)
        assert_equal(res.json['name'], "{0}, {1}".format(self.person.lastname,
                                                        self.person.firstname))
        assert_equal(res.json['n_items'], 1)


    def test_get_nonexistent_person(self):
        res = self.client.get("/api/v1/people/10")
        assert_equal(res.status_code, 404)

    def _post_json(self, url, data):
        return self.client.post(url,
                                data=json.dumps(data),
                                content_type='application/json')

    def _put_json(self, url, data):
        return self.client.put(url,
                                data=json.dumps(data),
                                content_type='application/json')

    def test_post_item(self):
        res = self._post_json("/api/v1/items/", {"name": "Ipad", 'checked_out': True})
        assert_equal(res.status_code, 201)
        item = models.item.query().sort_by("-updated")[0]
        assert_true(item is not None)
        assert_equal(item.name, "Ipad")
        assert_true(item.checked_out)

    def test_post_item_with_person_id(self):
        res = self._post_json('/api/v1/items/',
                              {"name": "Ipod", "person_id": str(self.person.id)})
        assert_equal(res.status_code, 201)
        item = models.item.query()[0]
        assert_equal(item.person, self.person)

    def test_post_person(self):
        res = self._post_json('/api/v1/people/',
                            {'firstname': 'Foo', 'lastname': 'Bar'})
        assert_equal(res.status_code, 201)
        person = models.person.query().sort_by("-created")[0]
        assert_equal(person.firstname, "Foo")
        assert_equal(person.lastname, "Bar")

    def test_delete_item(self):
        all_items = models.item.query()
        assert_in(self.item, all_items)
        res = self.client.delete("/api/v1/items/{0}".format(self.item.id))
        all_items = models.item.query()
        assert_not_in(self.item, all_items)

    def test_put_item(self):
        res = self._put_json("/api/v1/items/{0}".format(self.item.id),
                            {"checked_out": True,
                            "person_id": str(self.person2.id)})
        item = models.item.get(id=self.item.id)
        assert_true(item.checked_out)
        assert_equal(item.person, self.person2)

    def test_delete_person(self):
        all_persons = models.person.query()
        assert_in(self.person, all_persons)
        self.client.delete('/api/v1/people/{0}'.format(self.person.id))
        all_persons = models.person.query()
        assert_not_in(self.person, all_persons)

    def test_recent(self):
        self.item.checked_out = True
        self.item2.checked_out = False
        self.item.save()
        self.item2.save()
        res = self.client.get("/api/v1/recentcheckouts/")
        assert_in(ItemSerializer(self.item).data, res.json['items'])
        assert_not_in(ItemSerializer(self.item2).data, res.json['items'])


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
