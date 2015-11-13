__FILENAME__ = api
# -*- coding: utf-8 -*-
from flask import Blueprint, request
from flask.ext.rest import RESTResource, need_auth

from models import db, Project, Person, Bill
from forms import (ProjectForm, EditProjectForm, MemberForm,
                   get_billform_for)


api = Blueprint("api", __name__, url_prefix="/api")


def check_project(*args, **kwargs):
    """Check the request for basic authentication for a given project.

    Return the project if the authorization is good, False otherwise
    """
    auth = request.authorization

    # project_id should be contained in kwargs and equal to the username
    if auth and "project_id" in kwargs and \
            auth.username == kwargs["project_id"]:
        project = Project.query.get(auth.username)
        if project and project.password == auth.password:
            return project
    return False


class ProjectHandler(object):

    def add(self):
        form = ProjectForm(csrf_enabled=False)
        if form.validate():
            project = form.save()
            db.session.add(project)
            db.session.commit()
            return 201, project.id
        return 400, form.errors

    @need_auth(check_project, "project")
    def get(self, project):
        return 200, project

    @need_auth(check_project, "project")
    def delete(self, project):
        db.session.delete(project)
        db.session.commit()
        return 200, "DELETED"

    @need_auth(check_project, "project")
    def update(self, project):
        form = EditProjectForm(csrf_enabled=False)
        if form.validate():
            form.update(project)
            db.session.commit()
            return 200, "UPDATED"
        return 400, form.errors


class MemberHandler(object):

    def get(self, project, member_id):
        member = Person.query.get(member_id, project)
        if not member or member.project != project:
            return 404, "Not Found"
        return 200, member

    def list(self, project):
        return 200, project.members

    def add(self, project):
        form = MemberForm(project, csrf_enabled=False)
        if form.validate():
            member = Person()
            form.save(project, member)
            db.session.commit()
            return 201, member.id
        return 400, form.errors

    def update(self, project, member_id):
        form = MemberForm(project, csrf_enabled=False)
        if form.validate():
            member = Person.query.get(member_id, project)
            form.save(project, member)
            db.session.commit()
            return 200, member
        return 400, form.errors

    def delete(self, project, member_id):
        if project.remove_member(member_id):
            return 200, "OK"
        return 404, "Not Found"


class BillHandler(object):

    def get(self, project, bill_id):
        bill = Bill.query.get(project, bill_id)
        if not bill:
            return 404, "Not Found"
        return 200, bill

    def list(self, project):
        return project.get_bills().all()

    def add(self, project):
        form = get_billform_for(project, True, csrf_enabled=False)
        if form.validate():
            bill = Bill()
            form.save(bill, project)
            db.session.add(bill)
            db.session.commit()
            return 201, bill.id
        return 400, form.errors

    def update(self, project, bill_id):
        form = get_billform_for(project, True, csrf_enabled=False)
        if form.validate():
            bill = Bill.query.get(project, bill_id)
            form.save(bill, project)
            db.session.commit()
            return 200, bill.id
        return 400, form.errors

    def delete(self, project, bill_id):
        bill = Bill.query.delete(project, bill_id)
        db.session.commit()
        if not bill:
            return 404, "Not Found"
        return 200, "OK"


project_resource = RESTResource(
    name="project",
    route="/projects",
    app=api,
    actions=["add", "update", "delete", "get"],
    handler=ProjectHandler())

member_resource = RESTResource(
    name="member",
    inject_name="project",
    route="/projects/<project_id>/members",
    app=api,
    handler=MemberHandler(),
    authentifier=check_project)

bill_resource = RESTResource(
    name="bill",
    inject_name="project",
    route="/projects/<project_id>/bills",
    app=api,
    handler=BillHandler(),
    authentifier=check_project)

########NEW FILE########
__FILENAME__ = default_settings
DEBUG = False
SQLALCHEMY_DATABASE_URI = 'sqlite:///budget.db'
SQLACHEMY_ECHO = DEBUG
SECRET_KEY = "tralala"

DEFAULT_MAIL_SENDER = ("Budget manager", "budget@notmyidea.org")

try:
    from settings import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = forms
from flask.ext.wtf import DateField, DecimalField, Email, Form, PasswordField, \
    Required, SelectField, SelectMultipleField, SubmitField, TextAreaField, \
    TextField, ValidationError
from flask.ext.babel import lazy_gettext as _
from flask import request

from wtforms.widgets import html_params
from models import Project, Person
from datetime import datetime
from jinja2 import Markup
from utils import slugify


def select_multi_checkbox(field, ul_class='', **kwargs):
    kwargs.setdefault('type', 'checkbox')
    field_id = kwargs.pop('id', field.id)
    html = [u'<ul %s>' % html_params(id=field_id, class_="inputs-list")]

    choice_id = u'toggleField'
    js_function = u'toggle();'
    options = dict(kwargs, id=choice_id, onclick=js_function)
    html.append(u'<p><a id="selectall" onclick="selectall()">%s</a> | <a id="selectnone" onclick="selectnone()">%s</a></p>'% (_("Select all"), _("Select none")))

    for value, label, checked in field.iter_choices():
        choice_id = u'%s-%s' % (field_id, value)
        options = dict(kwargs, name=field.name, value=value, id=choice_id)
        if checked:
            options['checked'] = 'checked'
        html.append(u'<p><label for="%s">%s<span>%s</span></label></p>'
            % (choice_id, '<input %s /> ' % html_params(**options), label))
    html.append(u'</ul>')
    return u''.join(html)


def get_billform_for(project, set_default=True, **kwargs):
    """Return an instance of BillForm configured for a particular project.

    :set_default: if set to True, on GET methods (usually when we want to
                  display the default form, it will call set_default on it.

    """
    form = BillForm(**kwargs)
    form.payed_for.choices = form.payer.choices = [(m.id, m.name)
        for m in project.active_members]
    form.payed_for.default = [m.id for m in project.active_members]

    if set_default and request.method == "GET":
        form.set_default()
    return form


class CommaDecimalField(DecimalField):
    """A class to deal with comma in Decimal Field"""
    def process_formdata(self, value):
        if value:
            value[0] = str(value[0]).replace(',', '.')
        return super(CommaDecimalField, self).process_formdata(value)


class EditProjectForm(Form):
    name = TextField(_("Project name"), validators=[Required()])
    password = TextField(_("Private code"), validators=[Required()])
    contact_email = TextField(_("Email"), validators=[Required(), Email()])

    def save(self):
        """Create a new project with the information given by this form.

        Returns the created instance
        """
        project = Project(name=self.name.data, id=self.id.data,
                password=self.password.data,
                contact_email=self.contact_email.data)
        return project

    def update(self, project):
        """Update the project with the information from the form"""
        project.name = self.name.data
        project.password = self.password.data
        project.contact_email = self.contact_email.data

        return project


class ProjectForm(EditProjectForm):
    id = TextField(_("Project identifier"), validators=[Required()])
    password = PasswordField(_("Private code"), validators=[Required()])
    submit = SubmitField(_("Create the project"))

    def validate_id(form, field):
        form.id.data = slugify(field.data)
        if Project.query.get(form.id.data):
            raise ValidationError(Markup(_("The project identifier is used "
                "to log in and for the URL of the project. "
                "We tried to generate an identifier for you but a project "
                "with this identifier already exists. "
                "Please create a new identifier "
                "that you will be able to remember.")))


class AuthenticationForm(Form):
    id = TextField(_("Project identifier"), validators=[Required()])
    password = PasswordField(_("Private code"), validators=[Required()])
    submit = SubmitField(_("Get in"))


class PasswordReminder(Form):
    id = TextField(_("Project identifier"), validators=[Required()])
    submit = SubmitField(_("Send me the code by email"))

    def validate_id(form, field):
        if not Project.query.get(field.data):
            raise ValidationError(_("This project does not exists"))


class BillForm(Form):
    date = DateField(_("Date"), validators=[Required()], default=datetime.now)
    what = TextField(_("What?"), validators=[Required()])
    payer = SelectField(_("Payer"), validators=[Required()], coerce=int)
    amount = CommaDecimalField(_("Amount paid"), validators=[Required()])
    payed_for = SelectMultipleField(_("For whom?"),
            validators=[Required()], widget=select_multi_checkbox, coerce=int)
    submit = SubmitField(_("Submit"))
    submit2 = SubmitField(_("Submit and add a new one"))

    def save(self, bill, project):
        bill.payer_id = self.payer.data
        bill.amount = self.amount.data
        bill.what = self.what.data
        bill.date = self.date.data
        bill.owers = [Person.query.get(ower, project)
            for ower in self.payed_for.data]

        return bill

    def fill(self, bill):
        self.payer.data = bill.payer_id
        self.amount.data = bill.amount
        self.what.data = bill.what
        self.date.data = bill.date
        self.payed_for.data = [int(ower.id) for ower in bill.owers]

    def set_default(self):
        self.payed_for.data = self.payed_for.default

    def validate_amount(self, field):
        if field.data < 0:
            field.data = abs(field.data)
        elif field.data == 0:
            raise ValidationError(_("Bills can't be null"))


class MemberForm(Form):

    name = TextField(_("Name"), validators=[Required()])
    submit = SubmitField(_("Add"))

    def __init__(self, project, *args, **kwargs):
        super(MemberForm, self).__init__(*args, **kwargs)
        self.project = project

    def validate_name(form, field):
        if field.data == form.name.default:
            raise ValidationError(_("User name incorrect"))
        if Person.query.filter(Person.name == field.data)\
                .filter(Person.project == form.project)\
                .filter(Person.activated == True).all():
            raise ValidationError(_("This project already have this member"))

    def save(self, project, person):
        # if the user is already bound to the project, just reactivate him
        person.name = self.name.data
        person.project = project

        return person


class InviteForm(Form):
    emails = TextAreaField(_("People to notify"))
    submit = SubmitField(_("Send invites"))

    def validate_emails(form, field):
        validator = Email()
        for email in [email.strip() for email in form.emails.data.split(",")]:
            if not validator.regex.match(email):
                raise ValidationError(_("The email %(email)s is not valid",
                    email=email))


class CreateArchiveForm(Form):
    name = TextField(_("Name for this archive (optional)"), validators=[])
    start_date = DateField(_("Start date"), validators=[Required()])
    end_date = DateField(_("End date"), validators=[Required()], default=datetime.now)

########NEW FILE########
__FILENAME__ = models
from collections import defaultdict

from datetime import datetime
from flask.ext.sqlalchemy import SQLAlchemy, BaseQuery
from flask import g

from sqlalchemy import orm

db = SQLAlchemy()


# define models


class Project(db.Model):

    _to_serialize = ("id", "name", "password", "contact_email",
            "members", "active_members", "balance")

    id = db.Column(db.String, primary_key=True)

    name = db.Column(db.UnicodeText)
    password = db.Column(db.String)
    contact_email = db.Column(db.String)
    members = db.relationship("Person", backref="project")

    @property
    def active_members(self):
        return [m for m in self.members if m.activated]

    @property
    def balance(self):

        balances, should_pay, should_receive = (defaultdict(int)
            for time in (1, 2, 3))

        # for each person
        for person in self.members:
            # get the list of bills he has to pay
            bills = Bill.query.filter(Bill.owers.contains(person))
            for bill in bills.all():
                if person != bill.payer:
                    should_pay[person] += bill.pay_each()
                    should_receive[bill.payer] += bill.pay_each()

        for person in self.members:
            balance = should_receive[person] - should_pay[person]
            balances[person.id] = round(balance, 2)

        return balances

    def get_transactions_to_settle_bill(self):
        """Return a list of transactions that could be made to settle the bill"""
        #cache value for better performance
        balance = self.balance
        credits, debts, transactions = [],[],[]
        # Create lists of credits and debts
        for person in self.members:
            if balance[person.id] > 0:
                credits.append({"person": person, "balance": balance[person.id]})
            elif balance[person.id] < 0:
                debts.append({"person": person, "balance": -balance[person.id]})
        # Try and find exact matches
        for credit in credits:
            match = self.exactmatch(credit["balance"], debts)
            if match:
                for m in match:
                    transactions.append({"ower": m["person"], "receiver": credit["person"], "amount": m["balance"]})
                    debts.remove(m)
                credits.remove(credit)
        # Split any remaining debts & credits
        while credits and debts:
            if credits[0]["balance"] > debts[0]["balance"]:
                transactions.append({"ower": debts[0]["person"], "receiver": credits[0]["person"], "amount": debts[0]["balance"]})
                credits[0]["balance"] = credits[0]["balance"] - debts[0]["balance"]
                del debts[0]
            else:
                transactions.append({"ower": debts[0]["person"], "receiver": credits[0]["person"], "amount": credits[0]["balance"]})
                debts[0]["balance"] = debts[0]["balance"] - credits[0]["balance"]
                del credits[0]
        return transactions

    def exactmatch(self, credit, debts):
        """Recursively try and find subsets of 'debts' whose sum is equal to credit"""
        if not debts:
            return None
        if debts[0]["balance"] > credit:
            return self.exactmatch(credit, debts[1:])
        elif debts[0]["balance"] == credit:
            return [debts[0]]
        else:
            match = self.exactmatch(credit-debts[0]["balance"], debts[1:])
            if match:
                match.append(debts[0])
            else:
                match = self.exactmatch(credit, debts[1:])
            return match

    def has_bills(self):
        """return if the project do have bills or not"""
        return self.get_bills().count() > 0

    def get_bills(self):
        """Return the list of bills related to this project"""
        return Bill.query.join(Person, Project)\
            .filter(Bill.payer_id == Person.id)\
            .filter(Person.project_id == Project.id)\
            .filter(Project.id == self.id)\
            .order_by(Bill.date.desc())

    def remove_member(self, member_id):
        """Remove a member from the project.

        If the member is not bound to a bill, then he is deleted, otherwise
        he is only deactivated.

        This method returns the status DELETED or DEACTIVATED regarding the
        changes made.
        """
        try:
            person = Person.query.get(member_id, self)
        except orm.exc.NoResultFound:
            return None
        if not person.has_bills():
            db.session.delete(person)
            db.session.commit()
        else:
            person.activated = False
            db.session.commit()
        return person

    def remove_project(self):
        db.session.delete(self)
        db.session.commit()

    def __repr__(self):
        return "<Project %s>" % self.name


class Person(db.Model):

    class PersonQuery(BaseQuery):
        def get_by_name(self, name, project):
            return Person.query.filter(Person.name == name)\
                .filter(Project.id == project.id).one()

        def get(self, id, project=None):
            if not project:
                project = g.project
            return Person.query.filter(Person.id == id)\
                .filter(Project.id == project.id).one()

    query_class = PersonQuery

    _to_serialize = ("id", "name", "activated")

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.String, db.ForeignKey("project.id"))
    bills = db.relationship("Bill", backref="payer")

    name = db.Column(db.UnicodeText)
    activated = db.Column(db.Boolean, default=True)

    def has_bills(self):
        """return if the user do have bills or not"""
        bills_as_ower_number = db.session.query(billowers)\
            .filter(billowers.columns.get("person_id") == self.id)\
            .count()
        return bills_as_ower_number != 0 or len(self.bills) != 0

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<Person %s for project %s>" % (self.name, self.project.name)

# We need to manually define a join table for m2m relations
billowers = db.Table('billowers',
    db.Column('bill_id', db.Integer, db.ForeignKey('bill.id')),
    db.Column('person_id', db.Integer, db.ForeignKey('person.id')),
)


class Bill(db.Model):

    class BillQuery(BaseQuery):

        def get(self, project, id):
            try:
                return self.join(Person, Project)\
                    .filter(Bill.payer_id == Person.id)\
                    .filter(Person.project_id == Project.id)\
                    .filter(Project.id == project.id)\
                    .filter(Bill.id == id).one()
            except orm.exc.NoResultFound:
                return None

        def delete(self, project, id):
            bill = self.get(project, id)
            if bill:
                db.session.delete(bill)
            return bill

    query_class = BillQuery

    _to_serialize = ("id", "payer_id", "owers", "amount", "date", "what")

    id = db.Column(db.Integer, primary_key=True)

    payer_id = db.Column(db.Integer, db.ForeignKey("person.id"))
    owers = db.relationship(Person, secondary=billowers)

    amount = db.Column(db.Float)
    date = db.Column(db.Date, default=datetime.now)
    what = db.Column(db.UnicodeText)

    archive = db.Column(db.Integer, db.ForeignKey("archive.id"))

    def pay_each(self):
        """Compute what each person has to pay"""
	if self.owers:
		return round(self.amount / len(self.owers), 2)
	else:
		return 0

    def __repr__(self):
        return "<Bill of %s from %s for %s>" % (self.amount,
                self.payer, ", ".join([o.name for o in self.owers]))


class Archive(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.String, db.ForeignKey("project.id"))
    name = db.Column(db.UnicodeText)

    @property
    def start_date(self):
        pass

    @property
    def end_date(self):
        pass

    def __repr__(self):
        return "<Archive>"

########NEW FILE########
__FILENAME__ = run
from flask import Flask, g, request, session
from flask.ext.babel import Babel
from raven.contrib.flask import Sentry

from web import main, db, mail
from api import api


app = Flask(__name__)
app.config.from_object("default_settings")

app.register_blueprint(main)
app.register_blueprint(api)

# db
db.init_app(app)
db.app = app
db.create_all()

# mail
mail.init_app(app)

# translations
babel = Babel(app)

# sentry
sentry = Sentry(app)

@babel.localeselector
def get_locale():
    # get the lang from the session if defined, fallback on the browser "accept
    # languages" header.
    lang = session.get('lang', request.accept_languages.best_match(['fr', 'en']))
    setattr(g, 'lang', lang)
    return lang

def main():
    app.run(host="0.0.0.0", debug=True)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = tests
 # -*- coding: utf-8 -*-
try:
    import unittest2 as unittest
except ImportError:
    import unittest  # NOQA

import base64
import json
from collections import defaultdict

from flask import session

import run
import models


class TestCase(unittest.TestCase):

    def setUp(self):
        run.app.config['TESTING'] = True

        run.app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///memory"
        run.app.config['CSRF_ENABLED'] = False  # simplify the tests
        self.app = run.app.test_client()
        try:
            models.db.init_app(run.app)
            run.mail.init_app(run.app)
        except:
            pass

        models.db.app = run.app
        models.db.create_all()

    def tearDown(self):
        # clean after testing
        models.db.session.remove()
        models.db.drop_all()

    def login(self, project, password=None, test_client=None):
        password = password or project

        return self.app.post('/authenticate', data=dict(
            id=project, password=password), follow_redirects=True)

    def post_project(self, name):
        """Create a fake project"""
        # create the project
        self.app.post("/create", data={
                'name': name,
                'id': name,
                'password': name,
                'contact_email': '%s@notmyidea.org' % name
        })

    def create_project(self, name):
        models.db.session.add(models.Project(id=name, name=unicode(name),
            password=name, contact_email="%s@notmyidea.org" % name))
        models.db.session.commit()


class BudgetTestCase(TestCase):

    def test_notifications(self):
        """Test that the notifications are sent, and that email adresses
        are checked properly.
        """
        # sending a message to one person
        with run.mail.record_messages() as outbox:

            # create a project
            self.login("raclette")

            self.post_project("raclette")
            self.app.post("/raclette/invite",
                          data={"emails": 'alexis@notmyidea.org'})

            self.assertEqual(len(outbox), 2)
            self.assertEqual(outbox[0].recipients, ["raclette@notmyidea.org"])
            self.assertEqual(outbox[1].recipients, ["alexis@notmyidea.org"])

        # sending a message to multiple persons
        with run.mail.record_messages() as outbox:
            self.app.post("/raclette/invite",
                data={"emails": 'alexis@notmyidea.org, toto@notmyidea.org'})

            # only one message is sent to multiple persons
            self.assertEqual(len(outbox), 1)
            self.assertEqual(outbox[0].recipients,
                    ["alexis@notmyidea.org", "toto@notmyidea.org"])

        # mail address checking
        with run.mail.record_messages() as outbox:
            response = self.app.post("/raclette/invite",
                                     data={"emails": "toto"})
            self.assertEqual(len(outbox), 0)  # no message sent
            self.assertIn("The email toto is not valid", response.data)

        # mixing good and wrong adresses shouldn't send any messages
        with run.mail.record_messages() as outbox:
            self.app.post("/raclette/invite",
              data={"emails": 'alexis@notmyidea.org, alexis'})  # not valid

            # only one message is sent to multiple persons
            self.assertEqual(len(outbox), 0)

    def test_password_reminder(self):
        # test that it is possible to have an email cotaining the password of a
        # project in case people forget it (and it happens!)

        self.create_project("raclette")

        with run.mail.record_messages() as outbox:
            # a nonexisting project should not send an email
            self.app.post("/password-reminder", data={"id": "unexisting"})
            self.assertEqual(len(outbox), 0)

            # a mail should be sent when a project exists
            self.app.post("/password-reminder", data={"id": "raclette"})
            self.assertEqual(len(outbox), 1)
            self.assertIn("raclette", outbox[0].body)
            self.assertIn("raclette@notmyidea.org", outbox[0].recipients)

    def test_project_creation(self):
        with run.app.test_client() as c:

            # add a valid project
            c.post("/create", data={
                'name': 'The fabulous raclette party',
                'id': 'raclette',
                'password': 'party',
                'contact_email': 'raclette@notmyidea.org'
            })

            # session is updated
            self.assertEqual(session['raclette'], 'party')

            # project is created
            self.assertEqual(len(models.Project.query.all()), 1)

            # Add a second project with the same id
            models.Project.query.get('raclette')

            c.post("/create", data={
                'name': 'Another raclette party',
                'id': 'raclette',  # already used !
                'password': 'party',
                'contact_email': 'raclette@notmyidea.org'
            })

            # no new project added
            self.assertEqual(len(models.Project.query.all()), 1)

    def test_project_deletion(self):

        with run.app.test_client() as c:
            c.post("/create", data={
                'name': 'raclette party',
                'id': 'raclette',
                'password': 'party',
                'contact_email': 'raclette@notmyidea.org'
            })

            # project added
            self.assertEqual(len(models.Project.query.all()), 1)

            c.get('/raclette/delete')

            # project removed
            self.assertEqual(len(models.Project.query.all()), 0)

    def test_membership(self):
        self.post_project("raclette")
        self.login("raclette")

        # adds a member to this project
        self.app.post("/raclette/members/add", data={'name': 'alexis'})
        self.assertEqual(len(models.Project.query.get("raclette").members), 1)

        # adds him twice
        result = self.app.post("/raclette/members/add",
                               data={'name': 'alexis'})

        # should not accept him
        self.assertEqual(len(models.Project.query.get("raclette").members), 1)

        # add fred
        self.app.post("/raclette/members/add", data={'name': 'fred'})
        self.assertEqual(len(models.Project.query.get("raclette").members), 2)

        # check fred is present in the bills page
        result = self.app.get("/raclette/")
        self.assertIn("fred", result.data)

        # remove fred
        self.app.post("/raclette/members/%s/delete" %
                models.Project.query.get("raclette").members[-1].id)

        # as fred is not bound to any bill, he is removed
        self.assertEqual(len(models.Project.query.get("raclette").members), 1)

        # add fred again
        self.app.post("/raclette/members/add", data={'name': 'fred'})
        fred_id = models.Project.query.get("raclette").members[-1].id

        # bound him to a bill
        result = self.app.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': u'fromage à raclette',
            'payer': fred_id,
            'payed_for': [fred_id, ],
            'amount': '25',
        })

        # remove fred
        self.app.post("/raclette/members/%s/delete" % fred_id)

        # he is still in the database, but is deactivated
        self.assertEqual(len(models.Project.query.get("raclette").members), 2)
        self.assertEqual(
                len(models.Project.query.get("raclette").active_members), 1)

        # as fred is now deactivated, check that he is not listed when adding
        # a bill or displaying the balance
        result = self.app.get("/raclette/")
        self.assertNotIn("/raclette/members/%s/delete" % fred_id, result.data)

        result = self.app.get("/raclette/add")
        self.assertNotIn("fred", result.data)

        # adding him again should reactivate him
        self.app.post("/raclette/members/add", data={'name': 'fred'})
        self.assertEqual(
                len(models.Project.query.get("raclette").active_members), 2)

        # adding an user with the same name as another user from a different
        # project should not cause any troubles
        self.post_project("randomid")
        self.login("randomid")
        self.app.post("/randomid/members/add", data={'name': 'fred'})
        self.assertEqual(
                len(models.Project.query.get("randomid").active_members), 1)

    def test_person_model(self):
        self.post_project("raclette")
        self.login("raclette")

        # adds a member to this project
        self.app.post("/raclette/members/add", data={'name': 'alexis'})
        alexis = models.Project.query.get("raclette").members[-1]

        # should not have any bills
        self.assertFalse(alexis.has_bills())

        # bound him to a bill
        self.app.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': u'fromage à raclette',
            'payer': alexis.id,
            'payed_for': [alexis.id, ],
            'amount': '25',
        })

        # should have a bill now
        alexis = models.Project.query.get("raclette").members[-1]
        self.assertTrue(alexis.has_bills())

    def test_member_delete_method(self):
        self.post_project("raclette")
        self.login("raclette")

        # adds a member to this project
        self.app.post("/raclette/members/add", data={'name': 'alexis'})

        # try to remove the member using GET method
        response = self.app.get("/raclette/members/1/delete")
        self.assertEqual(response.status_code, 405)

        #delete user using POST method
        self.app.post("/raclette/members/1/delete")
        self.assertEqual(
                len(models.Project.query.get("raclette").active_members), 0)
        #try to delete an user already deleted
        self.app.post("/raclette/members/1/delete")

    def test_demo(self):
        # test that a demo project is created if none is defined
        self.assertEqual([], models.Project.query.all())
        self.app.get("/demo")
        self.assertTrue(models.Project.query.get("demo") is not None)

    def test_authentication(self):
	# try to authenticate without credentials should redirect
	# to the authentication page
	resp = self.app.post("/authenticate")
	self.assertIn("Authentication", resp.data)

        # raclette that the login / logout process works
        self.create_project("raclette")

        # try to see the project while not being authenticated should redirect
        # to the authentication page
        resp = self.app.post("/raclette", follow_redirects=True)
        self.assertIn("Authentication", resp.data)

        # try to connect with wrong credentials should not work
        with run.app.test_client() as c:
            resp = c.post("/authenticate",
                    data={'id': 'raclette', 'password': 'nope'})

            self.assertIn("Authentication", resp.data)
            self.assertNotIn('raclette', session)

        # try to connect with the right credentials should work
        with run.app.test_client() as c:
            resp = c.post("/authenticate",
                    data={'id': 'raclette', 'password': 'raclette'})

            self.assertNotIn("Authentication", resp.data)
            self.assertIn('raclette', session)
            self.assertEqual(session['raclette'], 'raclette')

            # logout should wipe the session out
            c.get("/exit")
            self.assertNotIn('raclette', session)

    def test_manage_bills(self):
        self.post_project("raclette")

        # add two persons
        self.app.post("/raclette/members/add", data={'name': 'alexis'})
        self.app.post("/raclette/members/add", data={'name': 'fred'})

        members_ids = [m.id for m in
                       models.Project.query.get("raclette").members]

        # create a bill
        self.app.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': u'fromage à raclette',
            'payer': members_ids[0],
            'payed_for': members_ids,
            'amount': '25',
        })
        models.Project.query.get("raclette")
        bill = models.Bill.query.one()
        self.assertEqual(bill.amount, 25)

        # edit the bill
        self.app.post("/raclette/edit/%s" % bill.id, data={
            'date': '2011-08-10',
            'what': u'fromage à raclette',
            'payer': members_ids[0],
            'payed_for': members_ids,
            'amount': '10',
        })

        bill = models.Bill.query.one()
        self.assertEqual(bill.amount, 10, "bill edition")

        # delete the bill
        self.app.get("/raclette/delete/%s" % bill.id)
        self.assertEqual(0, len(models.Bill.query.all()), "bill deletion")

        # test balance
        self.app.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': u'fromage à raclette',
            'payer': members_ids[0],
            'payed_for': members_ids,
            'amount': '19',
        })

        self.app.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': u'fromage à raclette',
            'payer': members_ids[1],
            'payed_for': members_ids[0],
            'amount': '20',
        })

        self.app.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': u'fromage à raclette',
            'payer': members_ids[1],
            'payed_for': members_ids,
            'amount': '17',
        })

        balance = models.Project.query.get("raclette").balance
        self.assertEqual(set(balance.values()), set([19.0, -19.0]))

        #Bill with negative amount
        self.app.post("/raclette/add", data={
            'date': '2011-08-12',
            'what': u'fromage à raclette',
            'payer': members_ids[0],
            'payed_for': members_ids,
            # bill with a negative value should be converted to a positive
            # value
            'amount': '-25'
        })
        bill = models.Bill.query.filter(models.Bill.date == '2011-08-12')[0]
        self.assertEqual(bill.amount, 25)

        #add a bill with a comma
        self.app.post("/raclette/add", data={
            'date': '2011-08-01',
            'what': u'fromage à raclette',
            'payer': members_ids[0],
            'payed_for': members_ids,
            'amount': '25,02',
        })
        bill = models.Bill.query.filter(models.Bill.date == '2011-08-01')[0]
        self.assertEqual(bill.amount, 25.02)

    def test_rounding(self):
        self.post_project("raclette")

        # add members
        self.app.post("/raclette/members/add", data={'name': 'alexis'})
        self.app.post("/raclette/members/add", data={'name': 'fred'})
        self.app.post("/raclette/members/add", data={'name': 'tata'})

        # create bills
        self.app.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': u'fromage à raclette',
            'payer': 1,
            'payed_for': [1, 2, 3],
            'amount': '24.36',
        })

        self.app.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': u'red wine',
            'payer': 2,
            'payed_for': [1],
            'amount': '19.12',
        })

        self.app.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': u'delicatessen',
            'payer': 1,
            'payed_for': [1, 2],
            'amount': '22',
        })

        balance = models.Project.query.get("raclette").balance
        result = {}
        result[models.Project.query.get("raclette").members[0].id] = 8.12
        result[models.Project.query.get("raclette").members[1].id] = 0.0
        result[models.Project.query.get("raclette").members[2].id] = -8.12
        self.assertDictEqual(balance, result)

    def test_edit_project(self):
        # A project should be editable

        self.post_project("raclette")
        new_data = {
            'name': 'Super raclette party!',
            'contact_email': 'alexis@notmyidea.org',
            'password': 'didoudida'
        }

        resp = self.app.post("/raclette/edit", data=new_data,
                follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        project = models.Project.query.get("raclette")

        for key, value in new_data.items():
            self.assertEqual(getattr(project, key), value, key)

        # Editing a project with a wrong email address should fail
        new_data['contact_email'] = 'wrong_email'

        resp = self.app.post("/raclette/edit", data=new_data,
                follow_redirects=True)
        self.assertIn("Invalid email address", resp.data)

    def test_dashboard(self):
        response = self.app.get("/dashboard")
        self.assertEqual(response.status_code, 200)

    def test_settle_page(self):
        self.post_project("raclette")
        response = self.app.get("/raclette/settle_bills")
        self.assertEqual(response.status_code, 200)

    def test_settle(self):
        self.post_project("raclette")

        # add members
        self.app.post("/raclette/members/add", data={'name': 'alexis'})
        self.app.post("/raclette/members/add", data={'name': 'fred'})
        self.app.post("/raclette/members/add", data={'name': 'tata'})
        #Add a member with a balance=0 :
        self.app.post("/raclette/members/add", data={'name': 'toto'})

        # create bills
        self.app.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': u'fromage à raclette',
            'payer': 1,
            'payed_for': [1, 2, 3],
            'amount': '10.0',
        })

        self.app.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': u'red wine',
            'payer': 2,
            'payed_for': [1],
            'amount': '20',
        })

        self.app.post("/raclette/add", data={
            'date': '2011-08-10',
            'what': u'delicatessen',
            'payer': 1,
            'payed_for': [1, 2],
            'amount': '10',
        })
        project  = models.Project.query.get('raclette')
        transactions = project.get_transactions_to_settle_bill()
        members = defaultdict(int)
        #We should have the same values between transactions and project balances
        for t in transactions:
            members[t['ower']]-=t['amount']
            members[t['receiver']]+=t['amount']
        balance = models.Project.query.get("raclette").balance
        for m, a in members.items():
            self.assertEqual(a, balance[m.id])
        return
        


class APITestCase(TestCase):
    """Tests the API"""

    def api_create(self, name, id=None, password=None, contact=None):
        id = id or name
        password = password or name
        contact = contact or "%s@notmyidea.org" % name

        return self.app.post("/api/projects", data={
            'name': name,
            'id': id,
            'password': password,
            'contact_email': contact
        })

    def api_add_member(self, project, name):
        self.app.post("/api/projects/%s/members" % project,
                data={"name": name}, headers=self.get_auth(project))

    def get_auth(self, username, password=None):
        password = password or username
        base64string = base64.encodestring(
                '%s:%s' % (username, password)).replace('\n', '')
        return {"Authorization": "Basic %s" % base64string}

    def assertStatus(self, expected, resp, url=""):

        return self.assertEqual(expected, resp.status_code,
                "%s expected %s, got %s" % (url, expected, resp.status_code))

    def test_basic_auth(self):
        # create a project
        resp = self.api_create("raclette")
        self.assertStatus(201, resp)

        # try to do something on it being unauth should return a 401
        resp = self.app.get("/api/projects/raclette")
        self.assertStatus(401, resp)

        # PUT / POST / DELETE / GET on the different resources
        # should also return a 401
        for verb in ('post',):
            for resource in ("/raclette/members", "/raclette/bills"):
                url = "/api/projects" + resource
                self.assertStatus(401, getattr(self.app, verb)(url),
                        verb + resource)

        for verb in ('get', 'delete', 'put'):
            for resource in ("/raclette", "/raclette/members/1",
                    "/raclette/bills/1"):
                url = "/api/projects" + resource

                self.assertStatus(401, getattr(self.app, verb)(url),
                        verb + resource)

    def test_project(self):
        # wrong email should return an error
        resp = self.app.post("/api/projects", data={
            'name': "raclette",
            'id': "raclette",
            'password': "raclette",
            'contact_email': "not-an-email"
        })

        self.assertTrue(400, resp.status_code)
        self.assertEqual('{"contact_email": ["Invalid email address."]}',
                         resp.data)

        # create it
        resp = self.api_create("raclette")
        self.assertTrue(201, resp.status_code)

        # create it twice should return a 400
        resp = self.api_create("raclette")

        self.assertTrue(400, resp.status_code)
        self.assertIn('id', json.loads(resp.data))

        # get information about it
        resp = self.app.get("/api/projects/raclette",
                headers=self.get_auth("raclette"))

        self.assertTrue(200, resp.status_code)
        expected = {
            "active_members": [],
            "name": "raclette",
            "contact_email": "raclette@notmyidea.org",
            "members": [],
            "password": "raclette",
            "id": "raclette",
            "balance": {},
        }
        self.assertDictEqual(json.loads(resp.data), expected)

        # edit should work
        resp = self.app.put("/api/projects/raclette", data={
            "contact_email": "yeah@notmyidea.org",
            "password": "raclette",
            "name": "The raclette party",
            }, headers=self.get_auth("raclette"))

        self.assertEqual(200, resp.status_code)

        resp = self.app.get("/api/projects/raclette",
                headers=self.get_auth("raclette"))

        self.assertEqual(200, resp.status_code)
        expected = {
            "active_members": [],
            "name": "The raclette party",
            "contact_email": "yeah@notmyidea.org",
            "members": [],
            "password": "raclette",
            "id": "raclette",
            "balance": {},
        }
        self.assertDictEqual(json.loads(resp.data), expected)

        # delete should work
        resp = self.app.delete("/api/projects/raclette",
                headers=self.get_auth("raclette"))

        self.assertEqual(200, resp.status_code)

        # get should return a 401 on an unknown resource
        resp = self.app.get("/api/projects/raclette",
                headers=self.get_auth("raclette"))
        self.assertEqual(401, resp.status_code)

    def test_member(self):
        # create a project
        self.api_create("raclette")

        # get the list of members (should be empty)
        req = self.app.get("/api/projects/raclette/members",
                headers=self.get_auth("raclette"))

        self.assertStatus(200, req)
        self.assertEqual('[]', req.data)

        # add a member
        req = self.app.post("/api/projects/raclette/members", data={
                "name": "Alexis"
            }, headers=self.get_auth("raclette"))

        # the id of the new member should be returned
        self.assertStatus(201, req)
        self.assertEqual("1", req.data)

        # the list of members should contain one member
        req = self.app.get("/api/projects/raclette/members",
                headers=self.get_auth("raclette"))

        self.assertStatus(200, req)
        self.assertEqual(len(json.loads(req.data)), 1)

        # edit this member
        req = self.app.put("/api/projects/raclette/members/1", data={
                "name": "Fred"
            }, headers=self.get_auth("raclette"))

        self.assertStatus(200, req)

        # get should return the new name
        req = self.app.get("/api/projects/raclette/members/1",
                headers=self.get_auth("raclette"))

        self.assertStatus(200, req)
        self.assertEqual("Fred", json.loads(req.data)["name"])

        # delete a member

        req = self.app.delete("/api/projects/raclette/members/1",
                headers=self.get_auth("raclette"))

        self.assertStatus(200, req)

        # the list of members should be empty
        # get the list of members (should be empty)
        req = self.app.get("/api/projects/raclette/members",
                headers=self.get_auth("raclette"))

        self.assertStatus(200, req)
        self.assertEqual('[]', req.data)

    def test_bills(self):
        # create a project
        self.api_create("raclette")

        # add members
        self.api_add_member("raclette", "alexis")
        self.api_add_member("raclette", "fred")
        self.api_add_member("raclette", "arnaud")

        # get the list of bills (should be empty)
        req = self.app.get("/api/projects/raclette/bills",
                headers=self.get_auth("raclette"))
        self.assertStatus(200, req)

        self.assertEqual("[]", req.data)

        # add a bill
        req = self.app.post("/api/projects/raclette/bills", data={
            'date': '2011-08-10',
            'what': u'fromage',
            'payer': "1",
            'payed_for': ["1", "2"],
            'amount': '25',
            }, headers=self.get_auth("raclette"))

        # should return the id
        self.assertStatus(201, req)
        self.assertEqual(req.data, "1")

        # get this bill details
        req = self.app.get("/api/projects/raclette/bills/1",
                headers=self.get_auth("raclette"))

        # compare with the added info
        self.assertStatus(200, req)
        expected = {
            "what": "fromage",
            "payer_id": 1,
            "owers": [
                {"activated": True, "id": 1, "name": "alexis"},
                {"activated": True, "id": 2, "name": "fred"}],
            "amount": 25.0,
            "date": "2011-08-10",
            "id": 1}

        self.assertDictEqual(expected, json.loads(req.data))

        # the list of bills should lenght 1
        req = self.app.get("/api/projects/raclette/bills",
                headers=self.get_auth("raclette"))
        self.assertStatus(200, req)
        self.assertEqual(1, len(json.loads(req.data)))

        # edit with errors should return an error
        req = self.app.put("/api/projects/raclette/bills/1", data={
            'date': '201111111-08-10',  # not a date
            'what': u'fromage',
            'payer': "1",
            'payed_for': ["1", "2"],
            'amount': '25',
            }, headers=self.get_auth("raclette"))

        self.assertStatus(400, req)
        self.assertEqual('{"date": ["This field is required."]}', req.data)

        # edit a bill
        req = self.app.put("/api/projects/raclette/bills/1", data={
            'date': '2011-09-10',
            'what': u'beer',
            'payer': "2",
            'payed_for': ["1", "2"],
            'amount': '25',
            }, headers=self.get_auth("raclette"))

        # check its fields
        req = self.app.get("/api/projects/raclette/bills/1",
                headers=self.get_auth("raclette"))

        expected = {
            "what": "beer",
            "payer_id": 2,
            "owers": [
                {"activated": True, "id": 1, "name": "alexis"},
                {"activated": True, "id": 2, "name": "fred"}],
            "amount": 25.0,
            "date": "2011-09-10",
            "id": 1}

        self.assertDictEqual(expected, json.loads(req.data))

        # delete a bill
        req = self.app.delete("/api/projects/raclette/bills/1",
                headers=self.get_auth("raclette"))
        self.assertStatus(200, req)

        # getting it should return a 404
        req = self.app.get("/api/projects/raclette/bills/1",
                headers=self.get_auth("raclette"))
        self.assertStatus(404, req)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = utils
import re
import inspect

from flask import redirect
from werkzeug.routing import HTTPException, RoutingException


def slugify(value):
    """Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.

    Copy/Pasted from ametaireau/pelican/utils itself took from django sources.
    """
    if type(value) == unicode:
        import unicodedata
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(re.sub('[^\w\s-]', '', value).strip().lower())
    return re.sub('[-\s]+', '-', value)


class Redirect303(HTTPException, RoutingException):
    """Raise if the map requests a redirect. This is for example the case if
    `strict_slashes` are activated and an url that requires a trailing slash.

    The attribute `new_url` contains the absolute destination url.
    """
    code = 303

    def __init__(self, new_url):
        RoutingException.__init__(self, new_url)
        self.new_url = new_url

    def get_response(self, environ):
        return redirect(self.new_url, 303)

########NEW FILE########
__FILENAME__ = web
"""
The blueprint for the web interface.

Contains all the interaction logic with the end user (except forms which
are directly handled in the forms module.

Basically, this blueprint takes care of the authentication and provides
some shortcuts to make your life better when coding (see `pull_project`
and `add_project_id` for a quick overview)
"""

from flask import Blueprint, current_app, flash, g, redirect, \
    render_template, request, session, url_for
from flask.ext.mail import Mail, Message
from flask.ext.babel import get_locale, gettext as _
from smtplib import SMTPRecipientsRefused
import werkzeug

# local modules
from models import db, Project, Person, Bill
from forms import AuthenticationForm, CreateArchiveForm, EditProjectForm, \
    InviteForm, MemberForm, PasswordReminder, ProjectForm, get_billform_for
from utils import Redirect303


main = Blueprint("main", __name__)
mail = Mail()


@main.url_defaults
def add_project_id(endpoint, values):
    """Add the project id to the url calls if it is expected.

    This is to not carry it everywhere in the templates.
    """
    if 'project_id' in values or not hasattr(g, 'project'):
        return
    if current_app.url_map.is_endpoint_expecting(endpoint, 'project_id'):
        values['project_id'] = g.project.id


@main.url_value_preprocessor
def pull_project(endpoint, values):
    """When a request contains a project_id value, transform it directly
    into a project by checking the credentials are stored in session.

    If not, redirect the user to an authentication form
    """
    if endpoint == "authenticate":
        return
    if not values:
        values = {}
    project_id = values.pop('project_id', None)
    if project_id:
        project = Project.query.get(project_id)
        if not project:
            raise Redirect303(url_for(".create_project",
                project_id=project_id))
        if project.id in session and session[project.id] == project.password:
            # add project into kwargs and call the original function
            g.project = project
        else:
            # redirect to authentication page
            raise Redirect303(
                    url_for(".authenticate", project_id=project_id))


@main.route("/authenticate", methods=["GET", "POST"])
def authenticate(project_id=None):
    """Authentication form"""
    form = AuthenticationForm()
    if not form.id.data and request.args.get('project_id'):
        form.id.data = request.args['project_id']
    project_id = form.id.data
    if project_id is None:
        #User doesn't provide project identifier, return to authenticate form
        msg = _("You need to enter a project identifier")
        form.errors["id"] = [msg]
        return render_template("authenticate.html", form=form)
    else:
        project = Project.query.get(project_id)

    create_project = False  # We don't want to create the project by default
    if not project:
        # But if the user try to connect to an unexisting project, we will
        # propose him a link to the creation form.
        if request.method == "POST":
            form.validate()
        else:
            create_project = project_id

    else:
        # if credentials are already in session, redirect
        if project_id in session and project.password == session[project_id]:
            setattr(g, 'project', project)
            return redirect(url_for(".list_bills"))

        # else process the form
        if request.method == "POST":
            if form.validate():
                if not form.password.data == project.password:
                    msg = _("This private code is not the right one")
                    form.errors['password'] = [msg]
                else:
                    # maintain a list of visited projects
                    if "projects" not in session:
                        session["projects"] = []
                    # add the project on the top of the list
                    session["projects"].insert(0, (project_id, project.name))
                    session[project_id] = form.password.data
                    session.update()
                    setattr(g, 'project', project)
                    return redirect(url_for(".list_bills"))

    return render_template("authenticate.html", form=form,
            create_project=create_project)


@main.route("/")
def home():
    project_form = ProjectForm()
    auth_form = AuthenticationForm()
    return render_template("home.html", project_form=project_form,
            auth_form=auth_form, session=session)


@main.route("/create", methods=["GET", "POST"])
def create_project():
    form = ProjectForm()
    if request.method == "GET" and 'project_id' in request.values:
        form.name.data = request.values['project_id']

    if request.method == "POST":
        # At first, we don't want the user to bother with the identifier
        # so it will automatically be missing because not displayed into
        # the form
        # Thus we fill it with the same value as the filled name,
        # the validation will take care of the slug
        if not form.id.data:
            form.id.data = form.name.data
        if form.validate():
            # save the object in the db
            project = form.save()
            db.session.add(project)
            db.session.commit()

            # create the session object (authenticate)
            session[project.id] = project.password
            session.update()

            # send reminder email
            g.project = project

            message_title = _("You have just created '%(project)s' "
                "to share your expenses", project=g.project.name)

            message_body = render_template("reminder_mail.%s" %
                get_locale().language)

            msg = Message(message_title,
                body=message_body,
                recipients=[project.contact_email])
            try:
                mail.send(msg)
            except SMTPRecipientsRefused:
                msg_compl = 'Problem sending mail. '
                # TODO: destroy the project and cancel instead?
            else:
                msg_compl = ''

            # redirect the user to the next step (invite)
            flash(_("%(msg_compl)sThe project identifier is %(project)s",
                msg_compl=msg_compl, project=project.id))
            return redirect(url_for(".invite", project_id=project.id))

    return render_template("create_project.html", form=form)


@main.route("/password-reminder", methods=["GET", "POST"])
def remind_password():
    form = PasswordReminder()
    if request.method == "POST":
        if form.validate():
            # get the project
            project = Project.query.get(form.id.data)

            # send the password reminder
            password_reminder = "password_reminder.%s" % get_locale().language
            mail.send(Message("password recovery",
                body=render_template(password_reminder, project=project),
                recipients=[project.contact_email]))
            flash(_("a mail has been sent to you with the password"))

    return render_template("password_reminder.html", form=form)


@main.route("/<project_id>/edit", methods=["GET", "POST"])
def edit_project():
    form = EditProjectForm()
    if request.method == "POST":
        if form.validate():
            project = form.update(g.project)
            db.session.commit()
            session[project.id] = project.password

            return redirect(url_for(".list_bills"))
    else:
        form.name.data = g.project.name
        form.password.data = g.project.password
        form.contact_email.data = g.project.contact_email

    return render_template("edit_project.html", form=form)


@main.route("/<project_id>/delete")
def delete_project():
    g.project.remove_project()
    flash(_('Project successfully deleted'))

    return redirect(url_for(".home"))


@main.route("/exit")
def exit():
    # delete the session
    session.clear()
    return redirect(url_for(".home"))


@main.route("/demo")
def demo():
    """
    Authenticate the user for the demonstration project and redirect him to
    the bills list for this project.

    Create a demo project if it doesnt exists yet (or has been deleted)
    """
    project = Project.query.get("demo")
    if not project:
        project = Project(id="demo", name=u"demonstration", password="demo",
                contact_email="demo@notmyidea.org")
        db.session.add(project)
        db.session.commit()
    session[project.id] = project.password
    return redirect(url_for(".list_bills", project_id=project.id))


@main.route("/<project_id>/invite", methods=["GET", "POST"])
def invite():
    """Send invitations for this particular project"""

    form = InviteForm()

    if request.method == "POST":
        if form.validate():
            # send the email

            message_body = render_template("invitation_mail.%s" %
                get_locale().language)

            message_title = _("You have been invited to share your "
                "expenses for %(project)s", project=g.project.name)
            msg = Message(message_title,
                body=message_body,
                recipients=[email.strip()
                    for email in form.emails.data.split(",")])
            mail.send(msg)
            flash(_("Your invitations have been sent"))
            return redirect(url_for(".list_bills"))

    return render_template("send_invites.html", form=form)


@main.route("/<project_id>/")
def list_bills():
    bill_form = get_billform_for(g.project)
    # set the last selected payer as default choice if exists
    if 'last_selected_payer' in session:
        bill_form.payer.data = session['last_selected_payer']
    bills = g.project.get_bills()

    return render_template("list_bills.html",
            bills=bills, member_form=MemberForm(g.project),
            bill_form=bill_form,
            add_bill=request.values.get('add_bill', False)
    )


@main.route("/<project_id>/members/add", methods=["GET", "POST"])
def add_member():
    # FIXME manage form errors on the list_bills page
    form = MemberForm(g.project)
    if request.method == "POST":
        if form.validate():
            member = form.save(g.project, Person())
            db.session.commit()
            flash(_("%(member)s had been added", member=member.name))
            return redirect(url_for(".list_bills"))

    return render_template("add_member.html", form=form)


@main.route("/<project_id>/members/<member_id>/reactivate", methods=["POST"])
def reactivate(member_id):
    person = Person.query.filter(Person.id == member_id)\
                .filter(Project.id == g.project.id).all()
    if person:
        person[0].activated = True
        db.session.commit()
        flash(_("%(name)s is part of this project again", name=person[0].name))
    return redirect(url_for(".list_bills"))


@main.route("/<project_id>/members/<member_id>/delete", methods=["POST"])
def remove_member(member_id):
    member = g.project.remove_member(member_id)
    if member:
        if member.activated == False:
            flash(_("User '%(name)s' has been deactivated", name=member.name))
        else:
            flash(_("User '%(name)s' has been removed", name=member.name))
    return redirect(url_for(".list_bills"))


@main.route("/<project_id>/add", methods=["GET", "POST"])
def add_bill():
    form = get_billform_for(g.project)
    if request.method == 'POST':
        if form.validate():
            # save last selected payer in session
            session['last_selected_payer'] = form.payer.data
            session.update()

            bill = Bill()
            db.session.add(form.save(bill, g.project))
            db.session.commit()

            flash(_("The bill has been added"))

            args = {}
            if form.submit2.data:
                args['add_bill'] = True

            return redirect(url_for('.list_bills', **args))

    return render_template("add_bill.html", form=form)


@main.route("/<project_id>/delete/<int:bill_id>")
def delete_bill(bill_id):
    # fixme: everyone is able to delete a bill
    bill = Bill.query.get(g.project, bill_id)
    if not bill:
        raise werkzeug.exceptions.NotFound()

    db.session.delete(bill)
    db.session.commit()
    flash(_("The bill has been deleted"))

    return redirect(url_for('.list_bills'))


@main.route("/<project_id>/edit/<int:bill_id>", methods=["GET", "POST"])
def edit_bill(bill_id):
    # FIXME: Test this bill belongs to this project !
    bill = Bill.query.get(g.project, bill_id)
    if not bill:
        raise werkzeug.exceptions.NotFound()

    form = get_billform_for(g.project, set_default=False)

    if request.method == 'POST' and form.validate():
        form.save(bill, g.project)
        db.session.commit()

        flash(_("The bill has been modified"))
        return redirect(url_for('.list_bills'))

    if not form.errors:
        form.fill(bill)

    return render_template("add_bill.html", form=form, edit=True)


@main.route("/lang/<lang>")
def change_lang(lang):
    session['lang'] = lang
    session.update()

    return redirect(request.headers.get('Referer') or url_for('.home'))


@main.route("/<project_id>/settle_bills")
def settle_bill():
    """Compute the sum each one have to pay to each other and display it"""
    bills = g.project.get_transactions_to_settle_bill()
    return render_template("settle_bills.html", bills=bills)


@main.route("/<project_id>/archives/create", methods=["GET", "POST"])
def create_archive():
    form = CreateArchiveForm()
    if request.method == "POST":
        if form.validate():
            pass
            flash(_("The data from XX to XX has been archived"))

    return render_template("create_archive.html", form=form)


@main.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", projects=Project.query.all())

########NEW FILE########
__FILENAME__ = gunicorn.conf
backlog = 2048
daemon = False
debug = True
workers = 3
logfile = "/path/to/your/app/budget.gunicorn.log"
loglevel = "info"
bind = "unix:/path/to/your/app/budget.gunicorn.sock"

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
import sys, os
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'

project = u'I hate money'
copyright = u'2011, The \'I hate money\' team'

version = '1.0'
release = '1.0'

exclude_patterns = ['_build']
pygments_style = 'sphinx'

sys.path.append(os.path.abspath('_themes'))
html_theme_path = ['_themes']
html_theme = 'pelican'
html_static_path = ['_static']
html_theme_options = { 'nosidebar': True }

########NEW FILE########
__FILENAME__ = fabfile
from fabric.api import env, cd, sudo, run

env.hosts = ['sites.lolnet.lan']


def deploy():
    with cd('/home//www/ihatemoney.org/code'):
        sudo('git pull', user="www-data")
    sudo('supervisorctl restart ihatemoney.org')


def whoami():
    run('/usr/bin/whoami')

########NEW FILE########
