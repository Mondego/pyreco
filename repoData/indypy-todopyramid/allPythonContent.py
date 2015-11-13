__FILENAME__ = grid
from webhelpers.html.builder import HTML
from webhelpers.html.grid import ObjectGrid

from .utils import localize_datetime


class TodoGrid(ObjectGrid):
    """A generated table for the todo list that supports ordering of
    the task name and due date columns. We also customize the init so
    that we accept the selected_tag and user_tz.
    """

    def __init__(self, request, selected_tag, user_tz, *args, **kwargs):
        self.request = request
        if 'url' not in kwargs:
            kwargs['url'] = request.current_route_url
        super(TodoGrid, self).__init__(*args, **kwargs)
        self.exclude_ordering = ['_numbered', 'tags']
        self.column_formats['due_date'] = self.due_date_td
        self.column_formats['tags'] = self.tags_td
        self.column_formats[''] = self.action_td
        self.selected_tag = selected_tag
        self.user_tz = user_tz

    def generate_header_link(self, column_number, column, label_text):
        """Override of the ObjectGrid to customize the headers. This is
        mostly taken from the example code in ObjectGrid itself.
        """
        GET = dict(self.request.copy().GET)
        self.order_column = GET.pop("order_col", None)
        self.order_dir = GET.pop("order_dir", None)
        # determine new order
        if column == self.order_column and self.order_dir == "desc":
            new_order_dir = "asc"
        else:
            new_order_dir = "desc"
        self.additional_kw['order_col'] = column
        self.additional_kw['order_dir'] = new_order_dir
        new_url = self.url_generator(_query=self.additional_kw)
        # set label for header with link
        label_text = HTML.tag("a", href=new_url, c=label_text)
        return super(TodoGrid, self).generate_header_link(column_number,
                                                             column,
                                                             label_text)

    def default_header_column_format(self, column_number, column_name,
        header_label):
        """Override of the ObjectGrid to use <th> for header columns
        """
        if column_name == "_numbered":
            column_name = "numbered"
        if column_name in self.exclude_ordering:
            class_name = "c%s %s" % (column_number, column_name)
            return HTML.tag("th", header_label, class_=class_name)
        else:
            header_label = HTML(
                header_label, HTML.tag("span", class_="marker"))
            class_name = "c%s ordering %s" % (column_number, column_name)
            return HTML.tag("th", header_label, class_=class_name)

    def default_header_ordered_column_format(self, column_number, column_name,
                                             header_label):
        """Override of the ObjectGrid to use <th> and to add an icon
        that represents the sort order for the column.
        """
        icon_direction = self.order_dir == 'asc' and 'up' or 'down'
        icon_class = 'icon-chevron-%s' % icon_direction
        icon_tag = HTML.tag("i", class_=icon_class)
        header_label = HTML(header_label, " ", icon_tag)
        if column_name == "_numbered":
            column_name = "numbered"
        class_name = "c%s ordering %s %s" % (
            column_number, self.order_dir, column_name)
        return HTML.tag("th", header_label, class_=class_name)

    def __html__(self):
        """Override of the ObjectGrid to use a <thead> so that bootstrap
        renders the styles correctly
        """
        records = []
        # first render headers record
        headers = self.make_headers()
        r = self.default_header_record_format(headers)
        # Wrap the headers in a thead
        records.append(HTML.tag('thead', r))
        # now lets render the actual item grid
        for i, record in enumerate(self.itemlist):
            columns = self.make_columns(i, record)
            if hasattr(self, 'custom_record_format'):
                r = self.custom_record_format(i + 1, record, columns)
            else:
                r = self.default_record_format(i + 1, record, columns)
            records.append(r)
        return HTML(*records)

    def tags_td(self, col_num, i, item):
        """Generate the column for the tags.
        """
        tag_links = []

        for tag in item.sorted_tags:
            tag_url = '%s/tags/%s' % (self.request.application_url, tag.name)
            tag_class = 'label'
            if self.selected_tag and tag.name == self.selected_tag:
                tag_class += ' label-warning'
            else:
                tag_class += ' label-info'
            anchor = HTML.tag("a", href=tag_url, c=tag.name,
                              class_=tag_class)
            tag_links.append(anchor)
        return HTML.td(*tag_links, _nl=True)

    def due_date_td(self, col_num, i, item):
        """Generate the column for the due date.
        """
        if item.due_date is None:
            return HTML.td('')
        span_class = 'due-date badge'
        if item.past_due:
            span_class += ' badge-important'
        due_date = localize_datetime(item.due_date, self.user_tz)
        span = HTML.tag(
            "span",
            c=HTML.literal(due_date.strftime('%Y-%m-%d %H:%M:%S')),
            class_=span_class,
        )
        return HTML.td(span)

    def action_td(self, col_num, i, item):
        """Generate the column that has the actions in it.
        """
        return HTML.td(HTML.literal("""\
        <div class="btn-group">
          <a class="btn dropdown-toggle" data-toggle="dropdown" href="#">
          Action
          <span class="caret"></span>
          </a>
          <ul class="dropdown-menu" id="%s">
            <li><a class="todo-edit" href="#">Edit</a></li>
            <li><a class="todo-complete" href="#">Complete</a></li>
          </ul>
        </div>
        """ % item.id))

########NEW FILE########
__FILENAME__ = layouts
from pyramid.renderers import get_renderer
from pyramid.decorator import reify


class Layouts(object):
    """This is the main layout for our application. This currently
    just sets up the global layout template. See the views module and
    their associated templates to see how this gets used.
    """

    @reify
    def global_template(self):
        renderer = get_renderer("templates/global_layout.pt")
        return renderer.implementation().macros['layout']

########NEW FILE########
__FILENAME__ = models
from datetime import datetime

from pyramid.security import Allow
from pyramid.security import Authenticated

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table
from sqlalchemy import Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from zope.sqlalchemy import ZopeTransactionExtension

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()

todoitemtag_table = Table(
    'todoitemtag',
    Base.metadata,
    Column('tag_id', Integer, ForeignKey('tags.name')),
    Column('todo_id', Integer, ForeignKey('todoitems.id')),
)


class RootFactory(object):
    """This object sets the security for our application. In this case
    we are only setting the `view` permission for all authenticated
    users.
    """
    __acl__ = [(Allow, Authenticated, 'view')]

    def __init__(self, request):
        pass


class Tag(Base):
    """The Tag model is a many to many relationship to the TodoItem.
    """
    __tablename__ = 'tags'
    name = Column(Text, primary_key=True)
    todoitem_id = Column(Integer, ForeignKey('todoitems.id'))

    def __init__(self, name):
        self.name = name


class TodoItem(Base):
    """This is the main model in our application. This is what powers
    the tasks in the todo list.
    """
    __tablename__ = 'todoitems'
    id = Column(Integer, primary_key=True)
    task = Column(Text, nullable=False)
    due_date = Column(DateTime)
    user = Column(Integer, ForeignKey('users.email'), nullable=False)
    tags = relationship(Tag, secondary=todoitemtag_table, lazy='dynamic')

    def __init__(self, user, task, tags=None, due_date=None):
        self.user = user
        self.task = task
        self.due_date = due_date
        if tags is not None:
            self.apply_tags(tags)

    def apply_tags(self, tags):
        """This helper function merely takes a list of tags and
        creates the associated tag object. We strip off whitespace
        and lowercase the tags to keep a normalized list.
        """
        for tag_name in tags:
            tag = tag_name.strip().lower()
            self.tags.append(DBSession.merge(Tag(tag)))

    @property
    def sorted_tags(self):
        """Return a list of sorted tags for this task.
        """
        return sorted(self.tags, key=lambda x: x.name)

    @property
    def past_due(self):
        """Determine if this task is past its due date. Notice that we
        compare to `utcnow` since dates are stored in UTC.
        """
        return self.due_date and self.due_date < datetime.utcnow()


class TodoUser(Base):
    """When a user signs in with their persona, this model is what
    stores their account information. It has a one to many relationship
    with the `TodoItem` model to create the `todo_list`.
    """
    __tablename__ = 'users'
    email = Column(Text, primary_key=True)
    first_name = Column(Text)
    last_name = Column(Text)
    time_zone = Column(Text)
    todo_list = relationship(TodoItem, lazy='dynamic')

    def __init__(self, email, first_name=None, last_name=None,
                 time_zone=u'US/Eastern'):
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.time_zone = time_zone

    @property
    def user_tags(self):
        """Find all tags a user has created
        """
        qry = self.todo_list.session.query(todoitemtag_table.columns['tag_id'])
        qry = qry.join(TodoItem).filter_by(user=self.email)
        qry = qry.group_by('tag_id')
        qry = qry.order_by('tag_id')
        return qry.all()

    @property
    def profile_complete(self):
        """A check to see if the user has completed their profile. If
        they have not, in the view code, we take them to their account
        settings.
        """
        return self.first_name and self.last_name

########NEW FILE########
__FILENAME__ = schema
from colander import MappingSchema
from colander import SchemaNode
from colander import String
from colander import Integer
from colander import DateTime
from colander import deferred
from deform.widget import HiddenWidget
from deform.widget import SelectWidget
from deform_bootstrap_extra.widgets import TagsWidget
from pytz import all_timezones
from pytz import timezone


class SettingsSchema(MappingSchema):
    """This is the form schema used for the account view.
    """
    first_name = SchemaNode(String())
    last_name = SchemaNode(String())
    time_zone = SchemaNode(
        String(),
        default=u'US/Eastern',
        widget=SelectWidget(
            values=zip(all_timezones, all_timezones),
        ),
    )


@deferred
def deferred_datetime_node(node, kw):
    """We defer the creation of the datetime node so that we can get
    the timezone from the user's profile. See the generate_task_form
    method in views.py to see how this is bound together.
    """
    tz = timezone(kw['user_tz'])
    return DateTime(default_tzinfo=tz)


class TodoSchema(MappingSchema):
    """This is the form schema used for list_view and tag_view. This is
    the basis for the add and edit form for tasks.
    """
    id = SchemaNode(
        Integer(),
        missing=None,
        widget=HiddenWidget(),
    )
    name = SchemaNode(String())
    tags = SchemaNode(
        String(),
        widget=TagsWidget(
            autocomplete_url='/tags.autocomplete',
        ),
        description=(
            "Enter a comma after each tag to add it. Backspace to delete."
        ),
        missing=[],
    )
    due_date = SchemaNode(
        deferred_datetime_node,
        missing=None,
    )

########NEW FILE########
__FILENAME__ = initializedb
from datetime import datetime
from datetime import timedelta
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
    TodoItem,
    TodoUser,
    Base,
    )


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri>\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def create_dummy_content(user_id):
    """Create some tasks by default to show off the site
    """
    task = TodoItem(
        user=user_id,
        task=u'Find a shrubbery',
        tags=[u'quest', u'ni', u'knight'],
        due_date=datetime.utcnow() + timedelta(days=60),
    )
    DBSession.add(task)
    task = TodoItem(
        user=user_id,
        task=u'Search for the holy grail',
        tags=[u'quest'],
        due_date=datetime.utcnow() - timedelta(days=1),
    )
    DBSession.add(task)
    task = TodoItem(
        user=user_id,
        task=u'Recruit Knights of the Round Table',
        tags=[u'quest', u'knight', u'discuss'],
        due_date=datetime.utcnow() + timedelta(minutes=45),
    )
    DBSession.add(task)
    task = TodoItem(
        user=user_id,
        task=u'Build a Trojan Rabbit',
        tags=[u'quest', u'rabbit'],
        due_date=datetime.utcnow() + timedelta(days=1),
    )
    DBSession.add(task)
    task = TodoItem(
        user=user_id,
        task=u'Talk to Tim the Enchanter',
        tags=[u'quest', u'discuss'],
        due_date=datetime.utcnow() + timedelta(days=90),
    )
    DBSession.add(task)
    task = TodoItem(
        user=user_id,
        task=u'Defeat the Rabbit of Caerbannog',
        tags=[u'quest', u'rabbit'],
        due_date=None,
    )
    DBSession.add(task)
    task = TodoItem(
        user=user_id,
        task=u'Cross the Bridge of Death',
        tags=[u'quest'],
        due_date=None,
    )
    DBSession.add(task)


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
        user = TodoUser(
            email=u'king.arthur@example.com',
            first_name=u'Arthur',
            last_name=u'Pendragon',
        )
        DBSession.add(user)
        create_dummy_content(u'king.arthur@example.com')

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
        self.assertEqual(info['project'], 'todopyramid')

########NEW FILE########
__FILENAME__ = utils
import pytz


def localize_datetime(dt, tz_name):
    """Provide a timzeone-aware object for a given datetime and timezone name
    """
    assert dt.tzinfo == None
    utc = pytz.timezone('UTC')
    aware = utc.localize(dt)
    timezone = pytz.timezone(tz_name)
    tz_aware_dt = aware.astimezone(timezone)
    return tz_aware_dt


def universify_datetime(dt):
    """Makes a datetime object a naive object
    """
    utc = pytz.timezone('UTC')
    utc_dt = dt.astimezone(utc)
    utc_dt = utc_dt.replace(tzinfo=None)
    return utc_dt

########NEW FILE########
__FILENAME__ = views
from pyramid.httpexceptions import HTTPFound
from pyramid.response import Response
from pyramid.security import authenticated_userid
from pyramid.security import remember
from pyramid.security import forget
from pyramid.settings import asbool
from pyramid.view import forbidden_view_config
from pyramid.view import notfound_view_config
from pyramid.view import view_config

from deform import Form
from deform import ValidationFailure
from peppercorn import parse
from pyramid_persona.views import verify_login
import transaction

from .grid import TodoGrid
from .scripts.initializedb import create_dummy_content
from .layouts import Layouts
from .models import DBSession
from .models import Tag
from .models import TodoItem
from .models import TodoUser
from .schema import SettingsSchema
from .schema import TodoSchema
from .utils import localize_datetime
from .utils import universify_datetime


class ToDoViews(Layouts):
    """This class has all the views for our application. The Layouts
    base class has the master template set up.
    """

    def __init__(self, context, request):
        """Set some common variables needed for each view.
        """
        self.context = context
        self.request = request
        self.user_id = authenticated_userid(request)
        self.todo_list = []
        self.user = None
        if self.user_id is not None:
            query = DBSession.query(TodoUser)
            self.user = query.filter(TodoUser.email == self.user_id).first()

    def form_resources(self, form):
        """Get a list of css and javascript resources for a given form.
        These are then used to place the resources in the global layout.
        """
        resources = form.get_widget_resources()
        js_resources = resources['js']
        css_resources = resources['css']
        js_links = ['deform:static/%s' % r for r in js_resources]
        css_links = ['deform:static/%s' % r for r in css_resources]
        return (css_links, js_links)

    def sort_order(self):
        """The list_view and tag_view both use this helper method to
        determine what the current sort parameters are.
        """
        order = self.request.GET.get('order_col', 'due_date')
        order_dir = self.request.GET.get('order_dir', 'asc')
        if order == 'due_date':
            # handle sorting of NULL values so they are always at the end
            order = 'CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date'
        if order == 'task':
            # Sort ignoring case
            order += ' COLLATE NOCASE'
        if order_dir:
            order = ' '.join([order, order_dir])
        return order

    def generate_task_form(self, formid="deform"):
        """This helper code generates the form that will be used to add
        and edit the tasks based on the schema of the form.
        """
        schema = TodoSchema().bind(user_tz=self.user.time_zone)
        options = """
        {success:
          function (rText, sText, xhr, form) {
            deform.processCallbacks();
            deform.focusFirstInput();
            var loc = xhr.getResponseHeader('X-Relocate');
            if (loc) {
              document.location = loc;
            };
           }
        }
        """
        return Form(
            schema,
            buttons=('submit',),
            formid=formid,
            use_ajax=True,
            ajax_options=options,
        )

    def process_task_form(self, form):
        """This helper code processes the task from that we have
        generated from Colander and Deform.

        This handles both the initial creation and subsequent edits for
        a task.
        """
        try:
            # try to validate the submitted values
            controls = self.request.POST.items()
            captured = form.validate(controls)
            action = 'created'
            with transaction.manager:
                tags = captured.get('tags', [])
                if tags:
                    tags = tags.split(',')
                due_date = captured.get('due_date')
                if due_date is not None:
                    # Convert back to UTC for storage
                    due_date = universify_datetime(due_date)
                task_name = captured.get('name')
                task = TodoItem(
                    user=self.user_id,
                    task=task_name,
                    tags=tags,
                    due_date=due_date,
                )
                task_id = captured.get('id')
                if task_id is not None:
                    action = 'updated'
                    task.id = task_id
                DBSession.merge(task)
            msg = "Task <b><i>%s</i></b> %s successfully" % (task_name, action)
            self.request.session.flash(msg, queue='success')
            # Reload the page we were on
            location = self.request.url
            return Response(
                '',
                headers=[
                    ('X-Relocate', location),
                    ('Content-Type', 'text/html'),
                ]
            )
            html = form.render({})
        except ValidationFailure as e:
            # the submitted values could not be validated
            html = e.render()
        return Response(html)

    @view_config(route_name='about', renderer='templates/about.pt')
    def about_view(self):
        """This is just a static page with info about the site.
        """
        return {'section': 'about'}

    @notfound_view_config(renderer='templates/404.pt')
    def notfound(self):
        """This special view just renders a custom 404 page. We do this
        so that the 404 page fits nicely into our global layout.
        """
        return {}

    @forbidden_view_config(renderer='templates/signin.pt')
    def forbidden(self):
        """This special view renders a login page when a user requests
        a page that they don't have permission to see. In the same way
        that the notfound view is set up, this will fit nicely into our
        global layout.
        """
        return {'section': 'login'}

    @view_config(route_name='logout', check_csrf=True)
    def logout(self):
        """This is an override of the logout view that comes from the
        persona plugin. The only change here is that the user is always
        re-directed back to the home page when logging out. This is so
        that they don't see a `forbidden` page right after logging out.
        """
        headers = forget(self.request)
        # Send the user back home, everything else is protected
        return HTTPFound('/', headers=headers)

    @view_config(route_name='login', check_csrf=True)
    def login_view(self):
        """This is an override of the login view that comes from the
        persona plugin. The basics of verify_login and remembering the
        user in a cookie are still present.

        Here we check to see if the user has been created in the
        database, then create the user. If they are an existing user,
        we just take them to the page they were trying to access.
        """
        email = verify_login(self.request)
        headers = remember(self.request, email)
        # Check to see if the user exists
        user = DBSession.query(TodoUser).filter(
            TodoUser.email == email).first()
        if user and user.profile_complete:
            self.request.session.flash('Logged in successfully')
            return HTTPFound(self.request.POST['came_from'], headers=headers)
        elif user and not user.profile_complete:
            msg = "Before you begin, please update your profile."
            self.request.session.flash(msg, queue='info')
            return HTTPFound('/account', headers=headers)
        # Otherwise, create an account and optionally create some content
        settings = self.request.registry.settings
        generate_content = asbool(
            settings.get('todopyramid.generate_content', None)
        )
        # Create the skeleton user
        with transaction.manager:
            DBSession.add(TodoUser(email))
            if generate_content:
                create_dummy_content(email)
        msg = (
            "This is your first visit, we hope your stay proves to be "
            "prosperous. Before you begin, please update your profile."
        )
        self.request.session.flash(msg)
        return HTTPFound('/account', headers=headers)

    @view_config(route_name='account', renderer='templates/account.pt',
                permission='view')
    def account_view(self):
        """This is the settings form for the user. The first time a
        user logs in, they are taken here so we can get their first and
        last name.
        """
        # Special case when the db was blown away
        if self.user_id is not None and self.user is None:
            return self.logout()
        section_name = 'account'
        schema = SettingsSchema()
        form = Form(schema, buttons=('submit',))
        css_resources, js_resources = self.form_resources(form)
        if 'submit' in self.request.POST:
            controls = self.request.POST.items()
            try:
                form.validate(controls)
            except ValidationFailure as e:
                msg = 'There was an error saving your settings.'
                self.request.session.flash(msg, queue='error')
                return {
                    'form': e.render(),
                    'css_resources': css_resources,
                    'js_resources': js_resources,
                    'section': section_name,
                }
            values = parse(self.request.params.items())
            # Update the user
            with transaction.manager:
                self.user.first_name = values.get('first_name', u'')
                self.user.last_name = values.get('last_name', u'')
                self.user.time_zone = values.get('time_zone', u'US/Eastern')
                DBSession.add(self.user)
            self.request.session.flash(
                'Settings updated successfully',
                queue='success',
            )
            return HTTPFound('/list')
        # Get existing values
        if self.user is not None:
            appstruct = dict(
                first_name=self.user.first_name,
                last_name=self.user.last_name,
                time_zone=self.user.time_zone,
            )
        else:
            appstruct = {}
        return {
            'form': form.render(appstruct),
            'css_resources': css_resources,
            'js_resources': js_resources,
            'section': section_name,
        }

    @view_config(renderer='json', name='tags.autocomplete', permission='view')
    def tag_autocomplete(self):
        """Get a list of dictionaries for the given term. This gives
        the tag input the information it needs to do auto completion.
        """
        term = self.request.params.get('term', '')
        if len(term) < 2:
            return []
        # XXX: This is global tags, need to hook into "user_tags"
        tags = DBSession.query(Tag).filter(Tag.name.startswith(term)).all()
        return [
            dict(id=tag.name, value=tag.name, label=tag.name)
            for tag in tags
        ]

    @view_config(renderer='json', name='edit.task', permission='view')
    def edit_task(self):
        """Get the values to fill in the edit form
        """
        todo_id = self.request.params.get('id', None)
        if todo_id is None:
            return False
        task = DBSession.query(TodoItem).filter(
            TodoItem.id == todo_id).first()
        due_date = None
        # If there is a due date, localize the time
        if task.due_date is not None:
            due_dt = localize_datetime(task.due_date, self.user.time_zone)
            due_date = due_dt.strftime('%Y-%m-%d %H:%M:%S')
        return dict(
            id=task.id,
            name=task.task,
            tags=','.join([tag.name for tag in task.sorted_tags]),
            due_date=due_date,
        )

    @view_config(renderer='json', name='delete.task', permission='view')
    def delete_task(self):
        """Delete a todo list item

        TODO: Add a guard here so that you can only delete your tasks
        """
        todo_id = self.request.params.get('id', None)
        if todo_id is not None:
            todo_item = DBSession.query(TodoItem).filter(
                TodoItem.id == todo_id)
            with transaction.manager:
                todo_item.delete()
        return True

    @view_config(route_name='home', renderer='templates/home.pt')
    def home_view(self):
        """This is the first page the user will see when coming to the
        application. If they are anonymous, the count is None and the
        template shows some enticing welcome text.

        If the user is logged in, then this gets a count of the user's
        tasks, and shows that number on the home page with a link to
        the `list_view`.
        """
        # Special case when the db was blown away
        if self.user_id is not None and self.user is None:
            return self.logout()
        if self.user_id is None:
            count = None
        else:
            count = len(self.user.todo_list.all())
        return {'user': self.user, 'count': count, 'section': 'home'}

    @view_config(route_name='list', renderer='templates/todo_list.pt',
                permission='view')
    def list_view(self):
        """This is the main functional page of our application. It
        shows a listing of the tasks that the currently logged in user
        has created.
        """
        # Special case when the db was blown away
        if self.user_id is not None and self.user is None:
            return self.logout()
        form = self.generate_task_form()
        if 'submit' in self.request.POST:
            return self.process_task_form(form)
        order = self.sort_order()
        todo_items = self.user.todo_list.order_by(order).all()
        grid = TodoGrid(
            self.request,
            None,
            self.user.time_zone,
            todo_items,
            ['task', 'tags', 'due_date', ''],
        )
        count = len(todo_items)
        item_label = 'items' if count > 1 or count == 0 else 'item'
        css_resources, js_resources = self.form_resources(form)
        return {
            'page_title': 'Todo List',
            'count': count,
            'item_label': item_label,
            'section': 'list',
            'items': todo_items,
            'grid': grid,
            'form': form.render(),
            'css_resources': css_resources,
            'js_resources': js_resources,
        }

    @view_config(route_name='tags', renderer='templates/todo_tags.pt',
                permission='view')
    def tags_view(self):
        """This view simply shows all of the tags a user has created.
        """
        # Special case when the db was blown away
        if self.user_id is not None and self.user is None:
            return self.logout()
        tags = self.user.user_tags
        return {
            'section': 'tags',
            'count': len(tags),
            'tags': tags,
        }

    @view_config(route_name='tag', renderer='templates/todo_list.pt',
                 permission='view')
    def tag_view(self):
        """Very similar to the list_view, this view just filters the
        list of tags down to the tag selected in the url based on the
        tag route replacement marker that ends up in the `matchdict`.
        """
        # Special case when the db was blown away
        if self.user_id is not None and self.user is None:
            return self.logout()
        form = self.generate_task_form()
        if 'submit' in self.request.POST:
            return self.process_task_form(form)
        order = self.sort_order()
        qry = self.user.todo_list.order_by(order)
        tag_name = self.request.matchdict['tag_name']
        tag_filter = TodoItem.tags.any(Tag.name.in_([tag_name]))
        todo_items = qry.filter(tag_filter)
        count = todo_items.count()
        item_label = 'items' if count > 1 or count == 0 else 'item'
        grid = TodoGrid(
            self.request,
            tag_name,
            self.user.time_zone,
            todo_items,
            ['task', 'tags', 'due_date', ''],
        )
        css_resources, js_resources = self.form_resources(form)
        return {
            'page_title': 'Tag List',
            'count': count,
            'item_label': item_label,
            'section': 'tags',
            'tag_name': tag_name,
            'items': todo_items,
            'grid': grid,
            'form': form.render({'tags': tag_name}),
            'css_resources': css_resources,
            'js_resources': js_resources,
        }

########NEW FILE########
