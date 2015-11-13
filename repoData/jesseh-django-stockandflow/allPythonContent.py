__FILENAME__ = admin
"""
Create a second admin site for the stocks and flows.
"""
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

from stockandflow.admin import StockAndFlowAdminSite


site = StockAndFlowAdminSite("sfadmin")


########NEW FILE########
__FILENAME__ = models
from django.db import models

from django.contrib.auth.models import User

from stockandflow.models import FlowEventModel

from profiles.models import Profile


class ProfileFlowEvent(FlowEventModel):
    subject = models.ForeignKey(Profile, related_name="flow_event")

class UserFlowEvent(FlowEventModel):
    subject = models.ForeignKey(User, related_name="flow_event")


#import to get stocks and flow registered
import processes.stocksandflows.profiles_sandf
import processes.stocksandflows.user_sandf

########NEW FILE########
__FILENAME__ = facets
from django.contrib.auth.models import User

from stockandflow.models import Facet

from profiles.models import Ramp, Source, PayState

coach = Facet(slug="coach", name="Coach", field_lookup="coach__username",
              values=User.objects.filter(groups__name="coach")
                         .values_list("username", flat=True))

ramp = Facet(slug="ramp", name="Ramp", field_lookup="ramp__name",
              values=Ramp.objects.all().values_list("name", flat=True))

source = Facet(slug="source", name="Source", field_lookup="source__name",
              values=Source.objects.all().values_list("name", flat=True))

pay_state = Facet(slug="pay_state", name="Pay state", field_lookup="pay_state__name",
              values=PayState.objects.all().values_list("name", flat=True))

########NEW FILE########
__FILENAME__ = profiles_sandf
from datetime import date

from stockandflow.models import Stock, Flow
from stockandflow.tracker import ModelTracker
from stockandflow import periodic
from processes.models import ProfileFlowEvent
from processes import admin as sfadmin
from profiles.models import Profile, CONSISTENCY_CHOICES
from processes.stocksandflows import facets

# The Stocks
stocks = []
needs_coach_stock = Stock(slug="needs_coach", name="Needs coach user", 
                     facets=[facets.coach],
                     queryset=Profile.objects.filter(user__is_active=True, needs_coach=True))
stocks.append(needs_coach_stock)

all_member_stock = Stock(slug="members", name="Members",
                     facets=[facets.ramp, facets.source, facets.pay_state],
                     queryset=Profile.objects.filter(user__is_staff=False,
                                                     user__is_active=True))
stocks.append(all_member_stock)

inactive_member_stock = Stock(slug="inactive", name="Inactive members",
                     queryset=Profile.objects.filter(user__is_staff=False,
                                                     user__is_active=True,
                                                     next_contact__exact=None))
stocks.append(inactive_member_stock)

paying_member_stock = Stock(slug="paying", name="Paying members",
                     facets=[facets.ramp, facets.source],
                     queryset=Profile.objects.filter(user__groups__name="pay_paid",
                                                     user__is_active=True))
stocks.append(paying_member_stock)

# This is an example of generating a stock for each choice option.
consist_slug_to_stock = {}
for slug, name in CONSISTENCY_CHOICES:
    stock = Stock(slug=slug, name=name,
                  queryset=Profile.objects.filter(user__is_active=True, consistency=slug))
    consist_slug_to_stock[slug] = stock
    stocks.append(stock)


# The state to stock function
# This must correspond to the stocks' querysets.
def profile_states_to_stocks(prev_field_vals, cur_field_vals):
    """
    Compare the field values to determine the state.
    """
    prev_consist_slug, = prev_field_vals if prev_field_vals else (None, )
    cur_consist_slug, = cur_field_vals if cur_field_vals else (None, )

    prev_consist_stock = consist_slug_to_stock.get(prev_consist_slug, None)
    cur_consist_stock = consist_slug_to_stock.get(cur_consist_slug, None)

    return ((prev_consist_stock,), (cur_consist_stock,))

## The flows
flows = []
flows.append(Flow(slug="starting_user", name="Starting user",
                  flow_event_model=ProfileFlowEvent,
                  sources=[None], sinks=consist_slug_to_stock.values()))

#An example of how to generate flows for a choice set
def gen_flows_from_choice(choice, flow_event_model, choice_stocks):
    """
    Generate a series of flows from a choices tuple array.
    """
    rv = []
    i = 0
    try:
        while(True):
            up = choice[i+1]
            down = choice[i]
            up_stock_slug = up[0]
            down_stock_slug = down[0]
            up_slug = "rising_%s" % up_stock_slug
            up_name = "Rising to %s" % up[1].lower()
            down_slug = "dropping_%s" % down_stock_slug
            down_name = "Dropping to %s" % down[1].lower()
            rv.append(Flow(slug=up_slug, name=up_name, flow_event_model=flow_event_model,
                           sources=[choice_stocks[down_stock_slug]],
                           sinks=[choice_stocks[up_stock_slug]]))
            rv.append(Flow(slug=down_slug, name=down_name, flow_event_model=flow_event_model,
                           sources=[choice_stocks[up_stock_slug]],
                           sinks=[choice_stocks[down_stock_slug]]))
            i += 1
    except IndexError:
        pass
    return rv

flows += gen_flows_from_choice(CONSISTENCY_CHOICES, ProfileFlowEvent, consist_slug_to_stock)



# The tracker
profile_tracker = ModelTracker(
        fields_to_track=["consistency"],
        states_to_stocks_func=profile_states_to_stocks, stocks=stocks, flows=flows)

# Add to the periodic schedule
def record_profile_stocks():
    map(lambda s: s.save_count(), stocks)

# An automation example
def mark_needs_coach_when_next_contact_is_due():
    today = date.today()
    dues = Profile.objects.filter(next_contact__lte=today)
    marked = []
    for profile in dues:
        profile.needs_coach = True
        profile.save()
        marked.append(profile.name)
    if marked:
        done = "Marked as needing coach because next contact is due: " + ", ".join(marked)
    else:
        done = "Nobody has a next contact that is due."
    return done


periodic.schedule.register(periodic.DAILY, record_profile_stocks)
periodic.schedule.register(periodic.DAILY, mark_needs_coach_when_next_contact_is_due)
periodic.schedule.register(periodic.WEEKLY, Profile.new_period)



# The admin - this is a seperate stock and flow admin
class ProfileActionsMixin(sfadmin.ActionsMixinBase):
    """
    Actions to be included in the admin interface.

    NOTE: Every action mixin must include an 'actions' property that lists the
    actions to be mixed in.
    """

    actions = ['email_users', 'set_coach_message', 'add_internal_coach_note',
               'apply_assignment_list', 'assign_an_action']


    def user_ids(self, queryset):
        return queryset.values_list("user_id", flat=True).distinct()

# This example shows how admin features can be leveraged to create a usable mechansim.
stock_specific_action_mixins = {}
stock_specific_admin_attributes = {}
for s in stocks:
    # set defaults and adjust with stock-specific values
    action_mixins=[ProfileActionsMixin]
    action_mixins += stock_specific_action_mixins.get(s,[])
    admin_attributes={ 
        "list_display": ["staff_user_link", "needs_coach", "coach",
                         "requesting_help", "next_contact", "consistency",
                         "consist_history", "signup_referrer"],
        "list_filter": ["coach", "needs_coach", "signup_referrer",
                        "next_contact", "consistency"],
        "list_editable": ["coach", "needs_coach", "next_contact"],
        "list_display_links": [],
    }
    admin_attributes.update(stock_specific_admin_attributes.get(s,{}))
    sfadmin.site.register_stock(s, admin_attributes, action_mixins)

for f in flows:
    sfadmin.site.register_flow(f)


########NEW FILE########
__FILENAME__ = user_sandf
"""
This is a very simple stock and flow example which just tracks the flow of logged in users. It registers no stocks and one flow.
"""

from processes import admin as sfadmin
from stockandflow.models import Flow
from stockandflow.tracker import ModelTracker
from profiles.models import Profile
from processes.models import UserFlowEvent


# The stocks - user-specific stocks are in profile
stocks = []

# The flows
flows = []

# Track a record of logins, and as part of that flow update the profile consistency
# The states do not need to be recorded, so instead of stocks there are just
# integers for the source and sink.
login_flow = Flow(slug="logging_in", name="Logging in", flow_event_model=UserFlowEvent,
                  sources=[0], sinks=[1], event_callables=(Profile.logged_in,))
flows.append(login_flow)



# The tracker
def user_states_to_stocks(prev_field_vals, cur_field_vals):
    """
    Check if the last login day has changed.
    """
    no_change = ((0,),(0,))
    yes_change = ((0,),(1,))
    if prev_field_vals is None:
        if cur_field_vals is None:
            return no_change
        else:
            return yes_change
    prev_last_login = prev_field_vals[0]
    cur_last_login = cur_field_vals[0]
    if cur_last_login > prev_last_login:
        return yes_change
    else:
        return no_change

assignment_tracker = ModelTracker(
        fields_to_track=["last_login"], states_to_stocks_func=user_states_to_stocks,
        stocks=stocks, flows=flows
    )

# No stocks to register

for f in flows:
    sfadmin.site.register_flow(f)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from processes import admin


urlpatterns = patterns("",
    url(r"^", include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = views
# Intentionally blank

########NEW FILE########
__FILENAME__ = admin
"""
Create an additonal admin site for the Stocks and Flows. This lets us customize
it without interfering with the normal admin site. And we get a lot of free features
by levereging the admin code.

The functions are called during the Stock and Flow initialization to set up corresponding admin
models.
"""
from types import MethodType

from django.contrib import admin

class StockAndFlowAdminSite(admin.AdminSite):
    """
    A seperate admin site to handle stocks and flows.

    This leverages Django's fantastic built-in admin to offer great
    functionality for both stocks and flows. Via this interface the stocks and
    flows can be viewed and actions applied.

    The StockAndFlowAdminSite registers a proxy model for each stock and flow
    to get around the fact that the admin site does not like a givem model to
    be registered more than once.

    This stock and flow admin is meant to be registered as a seperate admin
    site so that it does not clutter up the normal admin with dynamically
    created stock and flow entries.
    """
    def __init__(self, *args):
        """
        Remove the delete_selected action because these are proxy models.
        The action can be added back in for a given model stock or flow.
        """
        super(StockAndFlowAdminSite, self). __init__(*args)
        self.disable_action('delete_selected')

    registration_sequence = 0
    def next_reg_sequence(self):
        """
        Assign a sequence number for registrations so that they can be ordered in the display
        """
        self.registration_sequence += 1
        return self.registration_sequence

    def register_stock(self, stock, admin_attributes={}, action_mixins=[]):
        proxy_model = self.create_proxy_model(stock, stock.queryset.model,
                                                      stock.queryset.model.__module__)
        model_admin = self.create_model_admin(stock, stock.queryset, admin_attributes,
                                                      action_mixins)
        self.register(proxy_model, model_admin)

    def register_flow(self, flow, admin_attributes={}, action_mixins=[]):
        default_attrs = { "readonly_fields": ("flow","source","sink","subject",),
                          "list_display": ("timestamp", "source", "sink","subject"),
                          "list_filter": ("source", "sink", "timestamp"),
                          "date_hierarchy": "timestamp",
                        }
        default_attrs.update(admin_attributes)
        proxy_model = self.create_proxy_model(flow, flow.flow_event_model,
                                              flow.subject_model.__module__)
        model_admin = self.create_model_admin(flow, flow.queryset, default_attrs,
                                              action_mixins)
        self.register(proxy_model, model_admin)


    def create_proxy_model(self, represents, base_model, module):
        """
        Create a proxy of a model that can be used to represents a stock or a flow in an
        admin site.

        Django requires that either the module or an app label be set, so adding the new 
        model to an existing module is necessary.
        """

        class_name = represents.__class__.__name__
        name = represents.name.title().replace(" ","") + class_name
        class Meta:
            proxy = True
            verbose_name_plural = "%02d. %s: %s" % (self.next_reg_sequence(), class_name, 
                                                  represents.name.capitalize())
        attrs = {
            '__module__': module,
            '__str__': represents.name,
            'Meta': Meta,
        }
        rv = type(name, (base_model,), attrs)
        return rv

    def create_model_admin(self, represents, queryset, attrs={}, action_mixins=[]):
        """
        Dynamically create an admin model class that can be registered in the
        admin site to represent a stock or flow.
        
         - The queryset extracts the records that are included in the stock or
           flow.
         - The attrs dict become the properties of the class.
         - The action_mixins provide the a way to include sets of admin actions
           in the resulting class.
        """

        class_name = represents.__class__.__name__
        name = represents.name.title().replace(" ","") + class_name + 'Admin'
        inherits = tuple([admin.ModelAdmin] + action_mixins)
        ret_class = type(name, inherits, attrs)
        ret_class.queryset = MethodType(lambda self, request: queryset, None, ret_class)
        # Block add and delete permissions because stocks and flows are read only
        ret_class.has_add_permission = MethodType(lambda self, request: False, None, ret_class)
        ret_class.has_delete_permission = MethodType(lambda self, request, obj=None: 
                                                     False, None, ret_class)

        # Collect all the mixed in actions
        all_actions = []
        reduce(lambda a, cls: a.extend(cls.actions), action_mixins, all_actions)
        ret_class.actions = all_actions
        ret_class.actions_on_bottom = True
        return ret_class

########NEW FILE########
__FILENAME__ = geckoboard_urls
from django.conf.urls.defaults import *


urlpatterns = patterns("",
    url(r"^stock/line/(?P<slug>[-\w]+)/$", "stockandflow.views.stock_line_chart", name="stock_line_chart"),
)

########NEW FILE########
__FILENAME__ = run_periodic_schedule
from django.core.management.base import NoArgsCommand
import stockandflow

class Command(NoArgsCommand):
    args = ""
    help = "Run the periodic schedule entries. This should be called from cron at an interval that equals the shortest period length."
    
    def handle_noargs(self, *args, **options):
        stockandflow.periodic.schedule.run()

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'StockRecord'
        db.create_table('stockandflow_stockrecord', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('stock', self.gf('django.db.models.fields.SlugField')(max_length=50, db_index=True)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('count', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('stockandflow', ['StockRecord'])

        # Adding model 'PeriodicSchedule'
        db.create_table('stockandflow_periodicschedule', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('frequency', self.gf('django.db.models.fields.SlugField')(max_length=50, db_index=True)),
            ('last_run_timestamp', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('call_count', self.gf('django.db.models.fields.IntegerField')(default=0, null=True)),
        ))
        db.send_create_signal('stockandflow', ['PeriodicSchedule'])


    def backwards(self, orm):
        
        # Deleting model 'StockRecord'
        db.delete_table('stockandflow_stockrecord')

        # Deleting model 'PeriodicSchedule'
        db.delete_table('stockandflow_periodicschedule')


    models = {
        'stockandflow.periodicschedule': {
            'Meta': {'object_name': 'PeriodicSchedule'},
            'call_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'frequency': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_run_timestamp': ('django.db.models.fields.DateTimeField', [], {'null': 'True'})
        },
        'stockandflow.stockrecord': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'StockRecord'},
            'count': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'stock': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['stockandflow']

########NEW FILE########
__FILENAME__ = 0002_auto__add_stockfacetrecord
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'StockFacetRecord'
        db.create_table('stockandflow_stockfacetrecord', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('stock_record', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['stockandflow.StockRecord'])),
            ('facet', self.gf('django.db.models.fields.SlugField')(max_length=50, db_index=True)),
            ('value', self.gf('django.db.models.fields.CharField')(max_length=200, db_index=True)),
            ('count', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('stockandflow', ['StockFacetRecord'])


    def backwards(self, orm):
        
        # Deleting model 'StockFacetRecord'
        db.delete_table('stockandflow_stockfacetrecord')


    models = {
        'stockandflow.periodicschedule': {
            'Meta': {'object_name': 'PeriodicSchedule'},
            'call_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True'}),
            'frequency': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_run_timestamp': ('django.db.models.fields.DateTimeField', [], {'null': 'True'})
        },
        'stockandflow.stockfacetrecord': {
            'Meta': {'object_name': 'StockFacetRecord'},
            'count': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'facet': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'stock_record': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['stockandflow.StockRecord']"}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '200', 'db_index': 'True'})
        },
        'stockandflow.stockrecord': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'StockRecord'},
            'count': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'stock': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['stockandflow']

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.db.models.query import QuerySet
from django.contrib import admin

from model_utils.fields import AutoCreatedField


class Stock(object):
    """
    An accumulation defined by a queryset.

    In the abstract a stock is a collection that is counted at a specific time
    interval, generating a StockRecord). The state of an object defines it's
    membership in a given stock. As a result, the words state and stock are
    roughly interchangeable.

    In the specific a stock is a subset of records for a given model that meet
    the conditions defined in the queryset.

    For example a User may have an "active" stock and an "inactive" stock
    defined by whether or not each user.is_active == True.

    Facets is a list of either facet objects or tuples of the form (facet,
    field_prefix). The field prefix maps the object of the stock to the object
    that is filtered in the facet. For example, if there is a User with a
    Profile and a facet on the Profile object like "yada"="true" then a User
    stock would use the field_prefix "profile" so that the field lookup in the facet becomes
    "profile__yada"=True.
    """

    def __init__(self, slug, name, queryset, facets=[], description=""):
        self.name = name
        self.slug = slug
        self.queryset = queryset # defined but not executed at import time
        self._facet_lookup = {}
        self.description = description
        for f in facets:
            if isinstance(f, tuple):
                facet, field_prefix = f
            else:
                facet = f
                field_prefix = ""
            self._facet_lookup[facet.slug] = (facet, field_prefix)
        self.inflows = []
        self.outflows = []

    @property
    def facet_tuples(self):
        return self._facet_lookup.values()

    @property
    def subject_model(self):
        return self.queryset.model

    @property
    def definition(self):
        """
        Extract the WHERE clause of a query string
        """
        return str(self.queryset.query).split(" WHERE ")[1]

    def __str__(self):
        return "stock '%s'" % self.slug

    def register_inflow(self, flow):
        """
        Register an inward flow.
        """
        self.inflows.append(flow)

    def register_outflow(self, flow):
        """
        Register an outward flow.
        """
        self.outflows.append(flow)

    def most_recent_record(self):
        return StockRecord.objects.filter(stock=self.slug)[0]

    def all(self):
        """
        A shortcut for the queryset
        """
        return self.queryset

    def count(self):
        """
        A shortcut for a count of the queryset
        """
        return self.queryset.count()

    def flows_into(self):
        """
        A dict of flows that this stock as a sink in mapped to the queryset for
        those flow events.

        This method is used in views to get a lit of all the inflow events that
        impacted the stock.
        """
        rv = {}
        for f in self.inflows:
            rv[f] = f.all(sink=self)
        return rv

    def flows_outfrom(self):
        """
        A dict of flows that this stock as a source in mapped to the queryset for
        those flow events.

        This method is used in views to get a lit of all the outflow events that
        impacted the stock.
        """
        rv = {}
        for f in self.outflows:
            rv[f] = f.all(source=self)
        return rv

    def faceted_qs(self, facet_slug, value):
        """
        The queryset modified by applying a facet filter if it exists.
        """
        try:
            facet, field_prefix = self._facet_lookup[facet_slug]
        except KeyError:
            return self.queryset
        if not facet_slug or not value:
            return self.queryset
        if value in facet.values:
            q_obj = facet.get_Q(value, field_prefix)
            return self.queryset.filter(q_obj)
        else:
            raise ValueError("Invalid facet value")

    def get_facet(self, facet_slug):
        try:
            return self._facet_lookup[facet_slug][0]
        except KeyError:
            return None

    def save_count(self):
        """
        Save a record of the current count for the stock and any facets.
        """
        sr = StockRecord.objects.create(stock=self.slug, count=self.queryset.count())
        for facet_tuple in self.facet_tuples:
            facet, field_prefix = facet_tuple
            for value, q in facet.to_count(field_prefix):
                cnt = self.queryset.filter(q).count()
                srf = StockFacetRecord.objects.create(stock_record=sr, facet=facet.slug,
                                                      value=value, count=cnt)


class Facet(object):
    """
    A facet is used to split a stock or flow into sub-queries.
    
     - The name is used to refer to the facet.
     - The field lookup is the same as the left side of a kwarg in a filter function.
     - Values can either be a list or a ValuesQuerySet with flat=True. If it is a
       ValuesQuerySet then it will be re-evaluated at every use.
    """
    def __init__(self, slug, name, field_lookup, values):
        self.slug = slug
        self.name = name
        self.field_lookup = field_lookup
        self._given_values = values

    @property
    def values(self):
        if isinstance(self._given_values, models.query.ValuesQuerySet):
            return self._given_values.iterator()
        return self._given_values

    @property
    def choices(self):
        rv = ["", "Not selected"]
        for v in self.values():
            rv.append((v,v))
        return rv

    def get_Q(self, value, field_prefix=""):
        """
        Return a Q object that can be used in a filter to isolate this facet.

        The field_prefix string allows the field lookup to apply to related
        models by supplying the lookup path to the expected field.
        """
        if field_prefix:
            field_str = field_prefix + "__" + self.field_lookup
        else:
            field_str = self.field_lookup
        return models.Q(**{field_str: value})

    def to_count(self, field_prefix=""):
        """
        An generator of all the values and associated Q objects for this facet.
        Returns a list of tuples like (value, Q)

        The field_prefix string allows the field lookup to apply to related
        models by supplying the lookup path to the expected field.
        """
        return ((v, self.get_Q(v, field_prefix)) for v in self.values)


class StockFacetQuerySet(QuerySet):
    def __init__(self, stock=None, facet_slug="", facet_value="", *args, **kwargs):
        self.stock = stock
        if self.stock:
            if facet_slug:
                queryset = stock.faceted_qs(facet_slug, facet_value)
                self.facet = stock.get_facet(facet_slug)
            else:
                queryset = stock.queryset
                self.facet = None
            super(StockFacetQuerySet, self).__init__(model=queryset.model, query=queryset.query,
                                                     using=queryset._db, *args, **kwargs)
        else:
            super(StockFacetQuerySet, self).__init__(*args, **kwargs)


class Flow(object):
    """
    A named relationship between stocks representing the transition of an
    object from a source stock to a sink stock. A flow enables the transitions
    to measured over an interval of time to track the rate of occurence.

    A flow may have any number of source or sinks stocks. None is a valid
    source or sink that represents an external, or untracked stock. Any other
    class, such as an int or a string can be used a stock stand-in for creating
    flow events between states that do not have an associated Stock instance.

    Continuing the example in the Stock docstring, when a new user is created
    the flow from None to the stock "active". A flow to track this tranisition
    could be called "activating".  The activating flow would also have
    "inactive" as a source to handle the case where a previously inactive user
    becomes active again.

    The optional event_callables list is called whenever an flow event is created for
    this flow. It receives the flowed_obj, source and sink. An example use
    would be to send an email each time an activating flow occurs.
    """
    def __init__(self, slug, name, flow_event_model, sources=[], sinks=[],
                 event_callables=[], description=""):
        self.slug = slug
        self.name = name
        self.flow_event_model = flow_event_model
        self.sources = sources
        self.sinks = sinks
        self.event_callables = event_callables
        self.description = description
        self.queryset = flow_event_model.objects.filter(flow=self.slug)
        # If a flow connects stocks they must track the same class
        stock_cls = None
        stock_list = sources + sinks
        for s in stock_list: # Handles None stocks an no stocks
            if s:
                if isinstance(s, Stock):
                    s_cls = s.queryset.model
                else:
                    s_cls = s.__class__
                if not stock_cls:
                        stock_cls = s_cls
                elif s_cls != stock_cls:
                    raise ValueError("In %s the %s class %s does not match %s."
                                     % (self, s, s_cls, stock_cls))
        # Register the in and out flows
        for s in sources:
            if s and isinstance(s, Stock): s.register_outflow(self)
        for s in sinks:
            if s and isinstance(s, Stock): s.register_inflow(self)

    def __str__(self):
        return "flow '%s'" % self.slug

    @property
    def subject_model(self):
        return self.flow_event_model.subject.field.related.parent_model

    @property
    def definition(self):
        """
        Extract the WHERE clause of a query string without the wrapping parens.
        """
        str(self.queryset.query).split(" WHERE ")[1][1:-2]

    def add_event(self, flowed_obj, source=None, sink=None):
        """
        Record and return a flow event involving the (optional) object.
        If the flow does not connect the source and sink then return None.
        """
        if source is sink or source not in self.sources or sink not in self.sinks:
            return None
        args = { "flow": self.slug, "subject": flowed_obj }
        # If the source or sink is not a Stock instance then treat it as external
        args["source"] = source.slug if isinstance(source, Stock) else None
        args["sink"] = sink.slug if isinstance(sink, Stock) else None
        fe = self.flow_event_model(**args)
        fe.save()
        for c in self.event_callables:
            c(flowed_obj, source, sink)
        return fe

    def all(self, source=None, sink=None):
        """
        Return a queryset of all the events associated with this flow
        """
        qs = self.queryset
        if source:
            qs = qs.filter(source=source.slug)
        if sink:
            qs = qs.filter(sink=sink.slug)
        return qs

    def count(self, source=None, sink=None):
        """
        Return a count of all the events associated with this flow
        """
        return self.all(source, sink).count()


class StockRecord(models.Model):
    """
    A record of the count of a given stock at a point in time
    """
    stock = models.SlugField()
    timestamp = models.DateTimeField(auto_now_add=True)
    count = models.PositiveIntegerField()

    class Meta:
        ordering = ["-timestamp"]

class StockFacetRecord(models.Model):
    """
    A record of the count of a facet for a given stock at a point in time
    """
    stock_record = models.ForeignKey(StockRecord, db_index=True)
    facet = models.SlugField()
    value = models.CharField(max_length=200, db_index=True)
    count = models.PositiveIntegerField()

class StockRecordAdmin(admin.ModelAdmin):
    list_display=["timestamp", "stock", "count"]
    list_filter=["stock", "timestamp"]


class FlowEventModel(models.Model):
    """
    An abstract base class for the timestamped event of an object moving from 
    one stock to another

    Flow events combine to create a  flow variable that is measured over an
    interval of time. Therefore a flow would be measured per unit of time (say a
    year). Flow is roughly analogous to rate or speed in this sense.

    Subclasses must have a "subject" foreign key field.
    """
    flow = models.SlugField()
    timestamp = AutoCreatedField()
    source = models.SlugField(null=True, blank=True)
    sink = models.SlugField(null=True, blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return "%s (%s) at %s" % (self.flow, self.id, self.timestamp)


#admin.site.register(StockRecord, StockRecordAdmin) # removed because it caused circular import error.

########NEW FILE########
__FILENAME__ = periodic
import sys
import time
import calendar
from datetime import datetime

from django.db import models
from django.contrib import admin

# periods are in minutes

# Default period options
NEVER = "never"
MINUTELY = "minutely" #primarily for testing
TWELVE_MINUTELY = "twelve_minutely"
HOURLY = "hourly"
DAILY = "daily"
WEEKLY = "weekly"
TWO_WEEKLY = "two_weekly"
FOUR_WEEKLY = "four_weekly"

# The times are in minutes
FREQUENCIES = {}
FREQUENCIES["never"] = 0
FREQUENCIES["minutely"] = 1
FREQUENCIES["twelve_minutely"] = 12
FREQUENCIES["hourly"] = 60
FREQUENCIES["daily"] = FREQUENCIES["hourly"] * 24
FREQUENCIES["weekly"] = FREQUENCIES["daily"] * 7
FREQUENCIES["two_weekly"] = FREQUENCIES["weekly"] * 2
FREQUENCIES["four_weekly"] = FREQUENCIES["weekly"] * 4

class PeriodicSchedule(models.Model):
    """
    Periodically call a set of registered callable functions.

    This can be used, for example, to periodically count a stock. It could also
    be used to periodically decay objects from one stock to another.
    """

    frequency = models.SlugField()
    last_run_timestamp = models.DateTimeField(null=True)
    call_count = models.IntegerField(null=True, default=0)

    entries = {}

    def log(self, message):
        """
        A very basic logging function. Simply logs to stdout.
        """
        print >> sys.stdout, message

    def register(self, frequency, to_call, args=(), kwargs={}):
        """
        Register a callable with arguments to be called at the given frequency.
        The frequency must be one of the above constants.
        """
        if not FREQUENCIES[frequency]:
            raise ValueError("The frequency is invalid. it must be from the defined list.")
        if frequency == NEVER: return # Don't create an entry for something that never happens
        entry = (to_call, args, kwargs)
        try:
            self.entries[frequency].append(entry)
        except KeyError:
            self.entries[frequency] = [entry]

    def run_entries_for_frequency(self, frequency):
        """
        Run the entries for a given frequency.
        """
        self.log("Running %s entries." % frequency)
        call_count = 0
        for to_call, args, kwargs in self.entries.get(frequency, []):
            self.log("Running '%s'." % to_call.func_name)
            message = to_call(*args, **kwargs)
            self.log(message)
            call_count += 1
        return call_count


    def reset_schedule(self):
        """
        Used in testing to tearDown the entries.
        """
        self.entries = {}

    def run(self):
        """
        Run the schedule by checking if now is a higher period than the period
        of the last call for each frequency, and if so then run all the entries
        for that frequency.

        The period is determined by looking at the minutes since the epock, so
        it is safe to run this function repeatedly and it will still only run
        the entries for each frequency once per period.
        """
        now = datetime.now()
        now_seconds = int(time.mktime(now.utctimetuple()))
        self.log("Starting to run at %s." % now)
        period_mins_to_freq = dict((period, freq) for freq, period in FREQUENCIES.iteritems())
        for period_mins in sorted(period_mins_to_freq.keys()):
            if period_mins == 0: continue # Skip the never frequency
            freq = period_mins_to_freq[period_mins]
            to_run, created = PeriodicSchedule.objects.get_or_create(frequency=freq,
                    defaults={"last_run_timestamp": datetime.now(), "call_count": 0})
            if created:
                self.log("Not running %s frequency because it was just created." % freq)
                continue # Don't run just after creation because now may be mid-period
            last_run_timestamp = to_run.last_run_timestamp
            last_run_count = to_run.call_count
            if not last_run_timestamp:
                self.log("Giving defualt timestamp for %s" % freq)
                last_run_timestamp = datetime(1901,1,1)
                last_run_count = 0
            #Check for if this is overlapping a previous run
            elif to_run.call_count is None:
                self.log("Not running %s frequency because of an overlap." % freq)
                self.overlap_warning(freq, now)
            last_seconds = int(time.mktime(last_run_timestamp.utctimetuple()))
            now_period = now_seconds / 60 / period_mins
            last_period = last_seconds / 60 / period_mins
            if now_period > last_period:
                # Set that this is running in the database
                to_run.last_run_timestamp = now
                to_run.call_count = None #Mark to catch an overlap
                to_run.save()
                call_count = self.run_entries_for_frequency(freq)
                just_ran = PeriodicSchedule.objects.get(frequency=freq)
                if just_ran.last_run_timestamp == now:
                    just_ran.call_count = call_count
                    just_ran.save()
                else:
                    self.log("The run at %s has been overlapped." % freq)
                    # don't save the call count when there has been an overlap
            else:
                self.log("Not running %s because it is within the period" % freq)


    def overlap_warning(self, freq, timestamp):
        """
        Issue a warning about overlapping runs.
        This is a serperate function for easier testing.
        """
        print >> sys.stderr, "Overlapping run for '%s' frequency. There may have been an error, a slow process at %s" % (freq, timestamp)




# The schedule instance
schedule = PeriodicSchedule()

# Register to the normal admin
class PeriodicScheduleAdmin(admin.ModelAdmin):
    list_display = ["frequency", "last_run_timestamp", "call_count"]

admin.site.register(PeriodicSchedule, PeriodicScheduleAdmin)

########NEW FILE########
__FILENAME__ = tests
from datetime import datetime, timedelta
import time
from mock import Mock, MagicMock, patch

from django.core import management
from django.test import TestCase
from django.contrib.auth.models import User

from stockandflow.models import Stock, StockRecord, StockFacetRecord, Flow
from stockandflow.tracker import ModelTracker
from stockandflow import periodic


class StockTest(TestCase):

    def register_flows(self, stock):
        for f in self.inflows:
            stock.register_inflow(f)
        for f in self.outflows:
            stock.register_outflow(f)

    def setUp(self):
        self.mock_qs = Mock()
        self.mock_qs.count.return_value = 999
        self.stock_args = ['test name', 'test_slug', self.mock_qs]
        self.inflows = [Mock(), Mock()]
        self.outflows = [Mock(), Mock()]



    def testCreateAStockShouldStoreProperties(self):
        args = self.stock_args
        s = Stock(*args)
        self.assertEqual(s.slug, args[0])
        self.assertEqual(s.name, args[1])
        self.assertEqual(s.queryset, args[2])

    def testStockAllShouldReturnTheQueryset(self):
        s = Stock(*self.stock_args)
        self.assertEqual(s.all(), self.mock_qs)

    def testRegisterInAndOutFlowsShouldKeepLists(self):
        s = Stock(*self.stock_args)
        self.register_flows(s)
        for i, m in enumerate(self.inflows):
            self.assertEqual(s.inflows[i], m, msg="Inflow not registered")
        for i, m in enumerate(self.outflows):
            self.assertEqual(s.outflows[i], m, msg="Outflow not registered")

    def testSaveCountShouldCheckTheCount(self):
        s = Stock(*self.stock_args)
        s.save_count()
        self.assertTrue(self.mock_qs.count.called)

    @patch.object(StockRecord, 'save')
    def testSaveCountShouldCreateStockRecord(self, mock_save):
        s = Stock(*self.stock_args)
        s.save_count()
        self.assertTrue(mock_save.called)

    @patch.object(StockFacetRecord, 'save')
    def testSaveCountShouldCreateStockFacetRecord(self, mock_save):
        from stockandflow.models import Facet
        f = Facet("test_slug", "test name", "test_field", [1,2])
        s = Stock("test stock name", "test_stock_slug", self.mock_qs, facets=[f])
        s.facets = [f]
        s.save_count()
        self.assertEqual(mock_save.call_count, 2)

    @patch.object(StockFacetRecord, 'save')
    def testSaveCountShouldPassThroughFieldPrefix(self, mock_save):
        from stockandflow.models import Facet
        f = Facet("test_slug", "test name", "test_field", [1,2])
        f.to_count = MagicMock()
        s = Stock("test stock name", "test_stock_slug", self.mock_qs,
                  facets=[(f, "test_prefix")])
        s.save_count()
        self.assertEqual(f.to_count.call_args, (("test_prefix",), {}))

    def testMostRecentRecordShouldReturnCorrectStockRecord(self):
        s = Stock(*self.stock_args)
        s.save_count() # this would be the wrong record
        self.mock_qs.count.return_value = 111
        s.save_count()
        self.assertEqual(s.most_recent_record().count, 111)
        self.mock_qs.count.return_value = 222
        s.save_count()
        self.assertEqual(s.most_recent_record().count, 222)

    def testFlowIntoShouldReturnADictOfFlowsAndQuerysets(self):
        self.inflows = [Mock(), Mock()]
        self.outflows = [Mock(), Mock()]
        s = Stock(*self.stock_args)
        self.register_flows(s)
        rv = s.flows_into()
        self.assertEquals(len(rv), 2)
        self.assertTrue(self.inflows[0].all.called)
        self.assertEqual(rv[self.inflows[0]], self.inflows[0].all.return_value)
        self.assertTrue(self.inflows[1].all.called)
        self.assertEqual(rv[self.inflows[1]], self.inflows[1].all.return_value)

    def testFlowOutFromShouldReturnAListOfFlowsAndQuerysets(self):
        self.inflows = [Mock(), Mock()]
        self.outflows = [Mock(), Mock()]
        s = Stock(*self.stock_args)
        self.register_flows(s)
        rv = s.flows_outfrom()
        self.assertEquals(len(rv), 2)
        self.assertTrue(self.outflows[0].all.called)
        self.assertEqual(rv[self.outflows[0]], self.outflows[0].all.return_value)
        self.assertTrue(self.outflows[1].all.called)
        self.assertEqual(rv[self.outflows[1]], self.outflows[1].all.return_value)

    def testunitFacetedQSShouldReturnAQuerysetFilteredByAFacetBasedOnASlug(self):
        from stockandflow.models import Facet
        f = Facet("test_slug", "test name", "test_field", [1,2])
        s = Stock("test stock name", "test_stock_slug", self.mock_qs, facets=[f])
        s.faceted_qs("test_slug", value=1)
        self.assertEqual(str(self.mock_qs.filter.call_args[0][0]), "(AND: ('test_field', 1))")

    def testunitGetFacetedShouldReturnAFacetBasedOnASlug(self):
        from stockandflow.models import Facet
        f = Facet("test_slug", "test name", "test_field", [1,2])
        s = Stock("test stock name", "test_stock_slug", self.mock_qs, facets=[f])
        rv = s.get_facet("test_slug")
        self.assertEqual(rv, f)


class FlowTest(TestCase):

    def setUp(self):
        self.stock_mock = Mock()
        vals = [
           { "count" : 999, "args": ['test1 name', 'test1_slug', self.stock_mock] },
           { "count" : 444, "args": ['test2 name', 'test2_slug', self.stock_mock] },
        ]
        self.stocks = []
        for v in vals:
            v["args"][2].count.return_value = v["count"] #Set the mock's return value
            self.stocks.append(Stock(*v["args"]))
        self.args = {
                        "slug": "test_flow_slug", 
                        "name": "test flow name", 
                        "flow_event_model": Mock(),
                        "sources": (self.stocks[0],),
                        "sinks": (self.stocks[1],),
                    }

    def testCreateFlowShouldStoreProperties(self):
        f = Flow(**self.args)
        self.assertEqual(f.name, self.args["name"])
        self.assertEqual(f.slug, self.args["slug"])
        self.assertEqual(f.flow_event_model, self.args["flow_event_model"])
        self.assertEqual(f.sources, self.args["sources"])
        self.assertEqual(f.sinks, self.args["sinks"])

    def testCreateFlowShouldRegisterWithSourceAndSinkStocks(self):
        f = Flow(**self.args)
        self.assertEqual(self.stocks[0].outflows[0], f)
        self.assertEqual(self.stocks[1].inflows[0], f)

    def testFlowAddEventShouldReturnNoneIfSourceIsNotInSources(self):
        f = Flow(**self.args)
        self.assertTrue(f.add_event(Mock(), Mock(), self.stocks[1]) is None)

    def testCreateFlowBetweenMismatchedStocksShouldRaiseException(self):
        class MismatchClass():
            pass
        wrong_qs = StockRecord.objects.all() #could be any queryset
        s = Stock('test wrong class name', 'test_wc_slug', wrong_qs)
        self.args["sinks"] = (s,)
        self.assertRaises(ValueError, Flow, **self.args)

    def testCreateFlowEventShouldCreateDBRecord(self):
        # Create an object in the db - use stockrecord just because it is here and simple
        sr = StockRecord.objects.create(stock='no_stock', count=0)
        self.args["flow_event_model"] = Mock()
        f = Flow(**self.args)
        fe = f.add_event(sr, self.stocks[0], self.stocks[1])
        pos, kw = f.flow_event_model.call_args
        expect = {"flow": f.slug, "subject": sr, "source": self.stocks[0].slug,
                  "sink": self.stocks[1].slug }
        self.assertEqual(expect, kw)
        self.assertTrue(f.flow_event_model.return_value.save.called)

    def testFlowQuerysetShouldReturnAQSFilteredByTheFlowSlug(self):
        f = Flow(**self.args)
        objects_mock = f.flow_event_model.objects
        self.assertEqual(((), {"flow": f.slug}), objects_mock.filter.call_args)
        self.assertEqual(objects_mock.filter.return_value, f.queryset)

    def testFlowAllShouldReturnTheFlowQS(self):
        f = Flow(**self.args)
        self.assertEqual(f.queryset, f.all())

    def testFlowAllWithSourceAndOrSinkShouldReturnAQSFilteredByTheSink(self):
        f = Flow(**self.args)
        qs_mock = f.all()
        sink_mock = Mock()
        source_mock = Mock()
        rv_mock = f.all(sink=sink_mock)
        self.assertEqual(((), {"sink": sink_mock.slug}), qs_mock.filter.call_args)
        qs_mock.reset_mock()
        rv_mock = f.all(source=source_mock)
        self.assertEqual(((), {"source": source_mock.slug}), qs_mock.filter.call_args)
        qs_mock.reset_mock()
        rv_mock = f.all(sink=sink_mock, source=source_mock)
        self.assertEqual(((), {"source": source_mock.slug}), qs_mock.filter.call_args)
        qs2_mock = qs_mock.filter.return_value
        self.assertEqual(((), {"sink": sink_mock.slug}), qs2_mock.filter.call_args)


class ModelTrackerTest(TestCase):
    def setUp(self):
        self.staff_stock = Stock(slug="staff", name="Staff members",
                            queryset=User.objects.filter(is_staff=True))
        self.active_stock = Stock(slug="active", name="Active",
                             queryset=User.objects.filter(is_staff=False, 
                                                          is_active=True))
        self.inactive_stock = Stock(slug="inactive", name="Inactive",
                               queryset=User.objects.filter(is_staff=False, 
                                                            is_active=False))
        self.deactivating_flow = Flow(slug="deactivating", name="Deactivating",
                                      flow_event_model=Mock(),
                                      sources=[self.active_stock], 
                                      sinks=[self.inactive_stock])
        self.creating_flow = Flow(slug="creating", name="Creating",
                                  flow_event_model=Mock(),
                                  sources=[None], 
                                  sinks=[self.active_stock])
        self.args = {
            "fields_to_track": ("is_staff", "is_active"),
            "stocks": [self.staff_stock, self.active_stock, self.inactive_stock],
            "flows": [self.creating_flow, self.deactivating_flow],
            "states_to_stocks_func": self.user_states_to_stocks_f,
        }

    def user_states_to_stocks_f(self, prev_field_vals, cur_field_vals):
        return(self.user_state_to_stock(prev_field_vals), 
               self.user_state_to_stock(cur_field_vals)
              )
    def user_state_to_stock(self, field_vals):
        """
        Split users into a couple stocks for testing purposes
        """
        if field_vals == None: 
            return None, # This is an external stock
        is_staff, is_active = field_vals
        if is_staff: return self.staff_stock,
        if is_active: return self.active_stock,
        return self.inactive_stock,

    def testCheckForChangeShouldFlagChanges(self):
        mt = ModelTracker(**self.args)
        u = User(username="test1", is_active=True);
        u.save()
        cfe_mock = Mock()
        mt.create_flow_event = cfe_mock
        u2 = User.objects.get(username="test1")
        u2.is_active = False
        u2.save()
        self.assertTrue(cfe_mock.called)

    def testCreateFlowEventShouldCreateCorrectEvent(self):
        mt = ModelTracker(**self.args)
        u = User(username="test1", is_active=True);
        u.save()
        self.assertEqual(self.creating_flow.flow_event_model.call_count, 1)
        u2 = User.objects.get(username="test1")
        u2.is_active = False
        u2.save()
        self.assertEqual(self.deactivating_flow.flow_event_model.call_count, 1)
        u3 = User.objects.get(username="test1")
        u3.is_active = True
        u3.save()
        u4 = User.objects.get(username="test1")
        u4.is_active = False
        u4.save()
        self.assertEqual(self.deactivating_flow.flow_event_model.call_count, 2)

    def testModelTrackerShouldGenerateCreatingFlowEvent(self):
        mt = ModelTracker(**self.args)
        u = User(username="test1");
        u.save()
        self.assertTrue(self.creating_flow.flow_event_model.return_value.save.called)


class PeriodicScheduleShould(TestCase):
    def testHaveADefaultSchedule(self):
        self.assertTrue(periodic.schedule)

    def testCreateANewRecordForAnyNewTimePeriodsWithZeroCallCount(self):
        from stockandflow.periodic import PeriodicSchedule
        periodic.schedule.run()
        period = PeriodicSchedule.objects.get(frequency="weekly")
        self.assertEqual(period.call_count, 0)


class PeriodicScheduleRegistrationShould(TestCase):

    def setUp(self):
        periodic.schedule.reset_schedule()

    def tearDown(self):
        periodic.schedule.reset_schedule()

    def testAddMethodToSchedule(self):
        mock_callable = Mock()
        args = "test_arg",
        kwargs = {"a":"test_kwarg"}
        periodic.schedule.register(periodic.DAILY, mock_callable)
        self.assertEqual(periodic.schedule.entries[periodic.DAILY][0],
                         (mock_callable,(), {}))

    def testAddTwoMethodsToSchedule(self):
        mock_callable = Mock()
        mock_callable_2 = Mock()
        args = "test_arg",
        kwargs = {"a":"test_kwarg"}
        periodic.schedule.register(periodic.DAILY, mock_callable)
        periodic.schedule.register(periodic.DAILY, mock_callable_2,
                                   args, kwargs)
        self.assertEqual(periodic.schedule.entries[periodic.DAILY][1],
                         (mock_callable_2, args, kwargs))

    def testRaiseErrorWithANonFrequency(self):
        mock_callable = Mock()
        self.assertRaises(KeyError, periodic.schedule.register,
                          (periodic.schedule, "wrong", mock_callable), {})

class PeriodicScheduleRunnerShould(TestCase):
    def setUp(self):
        self.mock_callable = Mock()
        self.mock_callable_2 = Mock()
        self.args = "test_arg",
        self.kwargs = {"a":"test_kwarg"}

    def tearDown(self):
        periodic.schedule.reset_schedule()

    def testRunEntriesForAGivenFrequencyBasedOnCommandArgs(self):
        mock_callable = Mock()
        mock_callable_2 = Mock()
        args = "test_arg",
        kwargs = {"a":"test_kwarg"}
        periodic.schedule.register(periodic.DAILY, mock_callable)
        periodic.schedule.register(periodic.DAILY, mock_callable_2, args, kwargs)
        periodic.schedule.run_entries_for_frequency(periodic.DAILY)
        mock_callable.assertCalledOnceWithArgs((), {})
        mock_callable_2.assertCalledOnceWithArgs(args, kwargs)

    def testNotRunNewEntriesImmediately(self):
        mock_callable = Mock()
        periodic.schedule.register(periodic.DAILY, mock_callable)
        periodic.schedule.run()
        self.assertEqual(mock_callable.call_count, 0)

    def testCreateDbRecords(self):
        from stockandflow.periodic import PeriodicSchedule
        mock_callable = Mock()
        periodic.schedule.register(periodic.DAILY, mock_callable)
        periodic.schedule.run()
        entry = PeriodicSchedule.objects.get(frequency=periodic.DAILY)
        self.assertTrue(entry)

    def testNotSaveCallCountWhenTheRunOverlapsWithAnotherRun(self):
        #I'm not sure how to test this because it would need to change
        #the timestamp in another thread.
        pass

    @patch.object(periodic.schedule, "overlap_warning")
    def testCallOverlapWarningWhenRunWithAnOverlap(self, warning_mock):
        from stockandflow.periodic import PeriodicSchedule
        mock_callable = Mock()
        periodic.schedule.register(periodic.DAILY, mock_callable)
        periodic.schedule.run() # to register
        periodic.schedule.run() # to set timestamp
        entry = PeriodicSchedule.objects.get(frequency=periodic.DAILY)
        entry.call_count = None
        entry.save()
        periodic.schedule.run() # overlapping
        self.assertTrue(warning_mock.called)

    def testRunEntriesWhenThePeriodIsNew(self):
        mock_callable = Mock()
        mock_callable.func_name = "Mock function"
        periodic.schedule.run() # Get the frequencies into the db
        periodic.schedule.register(periodic.HOURLY, mock_callable)
        now = datetime.now()
        time_mock = Mock()
        with patch("stockandflow.periodic.datetime", new=time_mock):
            time_mock.now.return_value = now + timedelta(seconds=60*60+10) # an hour from now
            time_mock.side_effect = lambda *args, **kw: datetime(*args, **kw)
            periodic.schedule.run()
        self.assertTrue(mock_callable.called)

    def testRecordCallCountWhenThePeriodIsNew(self):
        mock_callable = Mock()
        mock_callable.func_name = "Mock function"
        mock_callable_2 = Mock()
        mock_callable_2.func_name = "Mock function 2"
        from stockandflow.periodic import PeriodicSchedule
        periodic.schedule.run() # Get the frequencies into the db
        periodic.schedule.register(periodic.HOURLY, mock_callable)
        periodic.schedule.register(periodic.HOURLY, mock_callable_2)
        now = datetime.now()
        time_mock = Mock()
        with patch("stockandflow.periodic.datetime", new=time_mock):
            time_mock.now.return_value = now + timedelta(seconds=60*60+10) # an hour from now
            time_mock.side_effect = lambda *args, **kw: datetime(*args, **kw)
            periodic.schedule.run()
        entry = PeriodicSchedule.objects.get(frequency=periodic.HOURLY)
        self.assertEqual(entry.call_count, 2)

    @patch.object(periodic.schedule, "run")
    def testRunAsAManagementCommand(self, run_mock):
        management.call_command("run_periodic_schedule")
        self.assertEqual(run_mock.call_count, 1)

    #write the callback functions and hook them up
    #create the stock amounts report



    #def testAdminAttribsShouldGetUpdatedForSpecificStocks(self):
        #mt = ModelTracker(**self.args)
        #expect = {
                    #"fake_1": "111",
                    #"fake_2": "222",
                 #}
        #active_admin = mt.stocks["active"].model_admin
        #self.assertEqual(active_admin.fake_1, "111")
        #self.assertEqual(active_admin.fake_2, "222")
        #staff_admin = mt.stocks["staff"].model_admin
        #self.assertEqual(staff_admin.fake_1, "999")

    #def testSaveCountShouldCallPreRecordCallable(self):
        #m = Mock()
        #s = Stock(*self.stock_args, pre_record_callable=m)
        #s.save_count()
        #self.assertTrue(m.called)

    #def testCreateWithNonIntegerFrequencyShouldRaiseError(self):
        #args = ['test name', 'test_slug', self.mock_qs, "month"]
        #self.assertRaises(InvalidFrequency, Stock, *args)

class PeriodicScheduleLogShould(TestCase):

    @patch('sys.stdout')
    def testPrintAMessageToStdOutDuringARun(self, stdout_mock):
        from stockandflow import periodic
        periodic.schedule.run()
        self.assertTrue(stdout_mock.write.called)
        periodic.schedule.run() # Get the frequencies into the db
        periodic.schedule.register(periodic.HOURLY, mock_callable)
        now = datetime.now()
        time_mock = Mock()
        with patch("stockandflow.periodic.datetime", new=time_mock):
            time_mock.now.return_value = now + timedelta(seconds=60*60+10) # an hour from now
            time_mock.side_effect = lambda *args, **kw: datetime(*args, **kw)
            periodic.schedule.run()
        self.assertTrue(self.mock_callable.called)

    def testRecordCallCountWhenThePeriodIsNew(self):
        from stockandflow.periodic import PeriodicSchedule
        periodic.schedule.run() # Get the frequencies into the db
        periodic.schedule.register(periodic.HOURLY, self.mock_callable)
        periodic.schedule.register(periodic.HOURLY, self.mock_callable_2)
        now = datetime.now()
        time_mock = Mock()
        with patch("stockandflow.periodic.datetime", new=time_mock):
            time_mock.now.return_value = now + timedelta(seconds=60*60+10) # an hour from now
            time_mock.side_effect = lambda *args, **kw: datetime(*args, **kw)
            periodic.schedule.run()
        entry = PeriodicSchedule.objects.get(frequency=periodic.HOURLY)
        self.assertEqual(entry.call_count, 2)

    @patch.object(periodic.schedule, "run")
    def testRunAsAManagementCommand(self, run_mock):
        management.call_command("run_periodic_schedule")
        self.assertEqual(run_mock.call_count, 1)

    #write the callback functions and hook them up
    #create the stock amounts report



    #def testAdminAttribsShouldGetUpdatedForSpecificStocks(self):
        #mt = ModelTracker(**self.args)
        #expect = {
                    #"fake_1": "111",
                    #"fake_2": "222",
                 #}
        #active_admin = mt.stocks["active"].model_admin
        #self.assertEqual(active_admin.fake_1, "111")
        #self.assertEqual(active_admin.fake_2, "222")
        #staff_admin = mt.stocks["staff"].model_admin
        #self.assertEqual(staff_admin.fake_1, "999")

    #def testSaveCountShouldCallPreRecordCallable(self):
        #m = Mock()
        #s = Stock(*self.stock_args, pre_record_callable=m)
        #s.save_count()
        #self.assertTrue(m.called)

    #def testCreateWithNonIntegerFrequencyShouldRaiseError(self):
        #args = ['test name', 'test_slug', self.mock_qs, "month"]
        #self.assertRaises(InvalidFrequency, Stock, *args)

class PeriodicScheduleLogShould(TestCase):

    @patch('sys.stdout')
    def testPrintAMessageToStdOutDuringARun(self, stdout_mock):
        from stockandflow import periodic
        periodic.schedule.run()
        self.assertTrue(stdout_mock.write.called)

class GeckoBoardStockLineChartViewShould(TestCase):
    def setUp(self):
        from django_geckoboard.tests.utils import TestSettingsManager
        self.settings_manager = TestSettingsManager()
        self.settings_manager.delete('GECKOBOARD_API_KEY')

    def tearDown(self):
        self.settings_manager.revert()

    def testReturnATupleOfValuesXAndYLabelsAndColor(self):
        """
        I need to write this test.
        """
        from nose.exc import SkipTest
        raise SkipTest

class FacetShould(TestCase):
    def testunitCallIteratorOnAValuesQuerySet(self):
        from stockandflow.models import Facet
        from django.db.models.query import ValuesQuerySet
        vqs = ValuesQuerySet()
        vqs.iterator = Mock()
        f = Facet("test_slug", "test_name", "test_field", vqs)
        f.values()
        vqs.iterator.assert_called()

    def testCreateAQObjectBasedOnAValue(self):
        from stockandflow.models import Facet
        f = Facet("test_slug", "test name", "test_field", [1,2])
        q = f.get_Q(1)
        self.assertEqual(str(q), "(AND: ('test_field', 1))")

    def testCreateAQObjectGivenAFieldPrefix(self):
        from stockandflow.models import Facet
        f = Facet("test_slug", "test name", "test_field", [1,2])
        q = f.get_Q(1, field_prefix="yada")
        self.assertEqual(str(q), "(AND: ('yada__test_field', 1))")

    def testCreateAGeneratorOfQObjectsForAllValues(self):
        from stockandflow.models import Facet
        f = Facet("test_slug", "test name", "test_field", [1,2])
        q_gen = f.to_count()
        rv = q_gen.next()
        self.assertEqual(rv[0], 1)
        self.assertEqual(str(rv[1]), "(AND: ('test_field', 1))")
        rv = q_gen.next()
        self.assertEqual(rv[0], 2)
        self.assertEqual(str(rv[1]), "(AND: ('test_field', 2))")

    def testCreateAGeneratorOfQObjectsForAllValuesWithAFieldPrefix(self):
        from stockandflow.models import Facet
        f = Facet("test_slug", "test name", "test_field", [1,2])
        q_gen = f.to_count("yada")
        rv = q_gen.next()
        self.assertEqual(rv[0], 1)
        self.assertEqual(str(rv[1]), "(AND: ('yada__test_field', 1))")
        rv = q_gen.next()
        self.assertEqual(rv[0], 2)
        self.assertEqual(str(rv[1]), "(AND: ('yada__test_field', 2))")


class StockFacetQuerysetShould(TestCase):
    def testunitFindTheFacetGivenAFacetSlug(self):
        from stockandflow.models import Facet, StockFacetQuerySet
        f = Facet("test_slug", "test name", "test_field", [1,2])
        s = Stock("test stock name", "test_stock_slug", Mock(), facets=[f])
        sfq = StockFacetQuerySet(stock=s, facet_slug=f.slug, facet_value=1)
        self.assertEqual(sfq.facet, f)

    def testunitBeTheStockQuerysetIfThereIsNoFacet(self):
        from stockandflow.models import StockFacetQuerySet, StockRecord
        s = Stock("test stock name", "test_stock_slug", StockRecord.objects.all())
        sfq = StockFacetQuerySet(stock=s)
        self.assertEqual(sfq.query, s.queryset.query)

    def testunitApplyTheFacetAndValueToTheQueryset(self):
        from stockandflow.models import Facet, StockFacetQuerySet
        mock_qs = Mock()
        f = Facet("test_slug", "test name", "test_field", [1,2])
        s = Stock("test stock name", "test_stock_slug", mock_qs, facets=[f])
        sfq = StockFacetQuerySet(stock=s, facet_slug=f.slug, facet_value=1)
        self.assertEqual(str(mock_qs.filter.call_args[0][0]), "(AND: ('test_field', 1))")


class ProcessShould(TestCase):
    def testGenerateAListOfFacetsSortedBySlugBasedOnTheStocks(self):
        from stockandflow.models import Stock, Facet
        from stockandflow.views import Process
        f1 = Facet("test_slug1", "test name1", "test_field", [1,2])
        f2 = Facet("test_slug2", "test name2", "test_field", [1,2])
        s1 = Stock('test name 1', 'test_slug_1', Mock(), [f1])
        s2 = Stock('test name 2', 'test_slug_2', Mock(), [f1, f2])
        process = Process("process_test", "process test", [s1, s2])
        self.assertEqual(process.facets, [f1, f2])




########NEW FILE########
__FILENAME__ = tracker
from django.db import models


class ModelTracker(object):
    """
    Manage the stock counting and flow event generation for a given model.
    
    It generates flow events by monitoring for changes to the fields_to_track
    list, runs the old and new field values through the states_to_stocks_func
    function to figure out the source and sink stocks. Then it tries to checks
    if any of the flows will make an event for that transition.

    The states_to_stocks_func recieves a list of the field values in the order
    that they are dexclared in fields_to_track. The function must return a
    tuple of stock (it can be a 1-tuple). This allows a single model's state be
    composed of any number of sub-states/stocks. The resulting previous and
    current state tuples are then compared element by element.

    Thanks to carljm for the monitor in django-model-utils on which the
    change tracking is based.
    """
    def __init__(self, fields_to_track, states_to_stocks_func, stocks=[], flows=[]):
        try:
            self.model = stocks[0].subject_model
        except IndexError:
            try:
                self.model = flows[0].subject_model
            except IndexError:
                self.model = None
        self.fields_to_track = fields_to_track
        self.states_to_stocks_func = states_to_stocks_func
        self.stocks = stocks
        self.flows = flows
        # cache the flow lookup table
        self.flow_lookup = {}
        # property names to store initial state-defining field values
        self.tracker_attnames = map(lambda f: '_modeltracker_%s' % f, fields_to_track)
        # Establish signals to get change notifications
        models.signals.post_init.connect(self._save_initial, sender=self.model)
        models.signals.post_save.connect(self._check_for_change, sender=self.model)

    def __str__(self):
        return "ModelTracker for %s" % self.model

    def get_tracked_value(self, instance, idx):
        return getattr(instance, self.fields_to_track[idx])

    def _save_initial(self, sender, instance, **kwargs):
        """
        Receives the post_init signal.
        """
        for i, f in enumerate(self.fields_to_track):
            setattr(instance, self.tracker_attnames[i],
                    self.get_tracked_value(instance, i))

    def _check_for_change(self, sender, instance, created, **kwargs):
        """
        Receives the post_save signal.
        """
        previous = []
        current = []
        for i, f in enumerate(self.fields_to_track):
            previous.append(getattr(instance, self.tracker_attnames[i], None))
            current.append(self.get_tracked_value(instance, i))
        if created:
            previous = None
        if previous != current: # short circuit if nothing has changed
            sources, sinks = self.states_to_stocks_func(previous, current)
            for source, sink in zip(sources, sinks):
                if source is not sink: # short circuit if no change in state/stock
                    self.create_flow_event(source, sink, instance)

    def create_flow_event(self, source, sink, instance):
        """
        Find a flow to create the event based on the source and sink.

        First try a cache of previous matches. Then try to add the event
        with all the flows in this tracker. If an event is created update
        the cache for next time.
        """
        try: # Check the cache
            flow = self.flow_lookup[(source, sink)]
            if flow:
                flow.add_event(instance, source, sink)
        except KeyError:
            for flow in self.flows:
                if flow.add_event(instance, source, sink): break
            else:
                flow = None
            # Cache the result
            self.flow_lookup[(source, sink)] = flow

    def record_count(self):
        if self.pre_record_callable:
            self.pre_record_callable()
        for stock in self.stocks:
            stock.save_count()


########NEW FILE########
__FILENAME__ = views
from operator import attrgetter
from collections import OrderedDict

from django.shortcuts import redirect
from django.views.generic.list_detail import object_detail
from django.core.urlresolvers import reverse
from django.template import loader
from django import forms
from django.http import QueryDict

from stockandflow.models import StockRecord, StockFacetQuerySet

class FacetForm(forms.Form):
    def __init__(self, facet_selection, *args, **kwargs):
        super(FacetForm, self).__init(*args, **kwargs)
        facets = facet_selection.process.facets
        for facet in facets:
            if facet.slug == facet_selection.slug:
                initial = facet_selection.value
            else:
                initial = None
            self.fields[facet.slug] = forms.ChoiceField(label=facet.name,
                    choices=facet.choices, initial=initial)


class FacetSelection(object):
    """
    This class is used to select the facets that should be applied.  The
    selected facets depend on information that is placed in the query string of
    a GET request.
    """
    def __init__(self, request=None, facet_slug=None, facet_value=None):
        """
        Values are either given or extracted from the request.
        """
        if request:
            self.slug = request.GET.get("facet_slug", "")
            self.value = request.GET.get("facet_value", "")
        if facet_slug is not None:
            self.slug = facet_slug
        if facet_value is not None:
            self.value = facet_value


    def stock_facet_qs(self, stock):
        return StockFacetQuerySet(stock=stock, facet_slug=self.slug, facet_value=self.value)

    def update_query_dict(self, query_dict):
        """
        Set the values relevant to this object in the query dict.
        """
        query_dict["facet_slug"] = self.slug
        query_dict["facet_value"] = self.value
        return query_dict

    def form(self, request, valid_redirect=None):
        """
        If valid_redirect is not defined it will just reload the current URL with an updated
        GET query string.

        NOTE: THE IS AN UNTESTED WORK IN PROGRESS
        """
        if request.method == 'POST':
            form = FacetForm(self, request.POST)
            if form.is_valid():
                # Process the data in form.cleaned_data
                # Find the facet that has a value, set the slug and value, update the querydict and redirect.
                for slug, value in enumerate(form.cleaned_data):
                    if value:
                        self.slug = slug
                        self.value = value
                        break
                if valid_redirect:
                    url = valid_redirect
                else:
                    url = request.path_info
                    #Update the GET params
                try:
                    query_str = self.update_query_dict(request.GET.copy()).urlencode()
                except ValueError:
                    query_str = None
                if query_str: 
                    url += "?%s" % query_str
                return redirect(url)
        else:
            form = FacetForm(self)
        return form


class StockSelection(object):
    """
    This class is used to select the stock that should be applied.  The
    selected stock depends on information that is placed in the query string of
    a GET request.
    """
    def __init__(self, process, request=None, stock=None):
        """
        Values are either given or extracted from the request.
        """
        if stock is None:
            stock_slug = request.GET.get("stock_slug", "")
            self.stock = process.stock_lookup[stock_slug] # raises a key error if invalid stoc
        else:
            self.stock = stock

    def update_query_dict(self, query_dict):
        """
        Set the values relevant to this object in the query dict.
        """
        query_dict["stock_slug"] = self.stock.slug
        return query_dict


class StockSequencer(object):
    """
    This class is used to create a view that iterates through a faceted stock
    based.  The iterating depends on information that is placed in the query
    string of a GET request.
    """

    #Movement constants
    (NEXT, PREVIOUS, FIRST, LAST, TO_INDEX) = range(5)

    def __init__(self, stock_selection=None, facet_selection=None, index=None, request=None):
        """
        Values are extracted from the request.

        This will raise an IndexError if there is no object at the given index.
        """
        if index is None:
            if request:
                self.index = int(request.GET.get("index", 0))
            else:
                self.index = 0
        else:
            self.index = index
        self.stock_selection = stock_selection
        self.facet_selection = facet_selection
        if facet_selection:
            self.stock_facet_qs = facet_selection.stock_facet_qs(self.stock_selection.stock)
        else:
            self.stock_facet_qs = StockFacetQuerySet(stock=self.stock_selection.stock)
        try:
            self.object_at_index = self.stock_facet_qs[self.index]
        except IndexError:
            self.object_at_index = None

    @property
    def stock(self):
        return self.stock_selection.stock

    def next(self, current_object_id=None, current_slug=None, slug_field=None):
        return self._step(1, current_object_id, current_slug, slug_field)

    def previous(self, current_object_id=None, current_slug=None, slug_field=None):
        return self._step(-1, current_object_id, current_slug, slug_field)

    def first(self):
        if self.count() == 0:
            raise StopIteration
        return StockSequencer(self.stock_selection, self.facet_selection, 0)

    def last(self ):
        if self.count() == 0:
            raise StopIteration
        return StockSequencer(self.stock_selection, self.facet_selection, self.count() - 1)

    def to_index(self, to_index):
        if self.count() == 0:
            raise StopIteration
        return StockSequencer(self.stock_selection, self.facet_selection, to_index)


    def _step(self, step_amount, current_object_id, current_slug, slug_field):
        """
        Return the next or previous in the sequence based on the step_amount.
        If cur_object_id and slug are None then the previous object is index +
        step.

        If current_object or slug is not None and if the object at index is not
        equal to current object's id or slug then previous will have the same
        index, so simply return self.

        Raises StopIteration if the next index is invalid.
        """
        if not current_object_id:
            self.index = 0
            rv = self
        elif not self.object_at_index:
            raise StopIteration
        elif current_object_id != self.object_at_index.id:
            rv = self
        elif current_slug is not None:
            if slug_field is None:
                raise ValueError("There must be a slug_field give if current_slug is given.")
            if current_slug != self.get_object()[slug_field]:
                rv = self
        else:
            stepped_index = self.index + step_amount
            if stepped_index < 0:
                raise StopIteration
            rv = StockSequencer(self.stock_selection, self.facet_selection, stepped_index)
        if not rv.object_at_index:
            raise StopIteration
        return rv

    def update_query_dict(self, query_dict):
        """
        Set the values relevant to this object in the query dict.
        """
        query_dict = self.stock_selection.update_query_dict(query_dict)
        if self.facet_selection:
            query_dict = self.facet_selection.update_query_dict(query_dict)
        query_dict["index"] = self.index
        return query_dict

    def query_str(self):
        """
        Update the request's GET query string with the values in this object
        and return the resulting query url encoded string.
        """
        qd = QueryDict("", mutable=True)
        qd = self.update_query_dict(qd)
        return qd.urlencode()

    def count(self):
        """
        Return a count that takes into account the facet.
        """
        return self.stock_facet_qs.count()



class Process(object):

    """
    A helper class to group stocks for use in a view.
    """

    def __init__(self, slug, name, stocks):
        self.slug = slug
        self.name = name
        self.stocks = stocks
        self.stock_lookup = {}
        facet_set = set()
        for stock in stocks:
            self.stock_lookup[stock.slug] = stock
            new_facets = []
            for facet_tuple in stock.facet_tuples:
                new_facets.append(facet_tuple[0])
            facet_set.update(new_facets)
        self.facets = sorted(facet_set, key=attrgetter("slug"))

    def all_stock_sequencers(self, facet_selection=None):
        # Get the facet select defined by the request.
        stock_seqs = []
        for stock in self.stocks:
            stock_selection = StockSelection(self, stock=stock)
            try:
                stock_seqs.append(StockSequencer(stock_selection, facet_selection))
            except StopIteration:
                pass
        return stock_seqs

    def next_in_stock(self, request, current_object_id=None, current_slug=None,
                      slug_field="slug", object_view=None, stop_iteration_view=None,
                      reverse_args=None, reverse_kwargs=None, stock_seq=None,
                      movement=StockSequencer.NEXT, to_index=None):
        """
        Either an object_id or a slug and slug_field are required. This is used
        to check if the index needs to advance or not which happens if the
        current object is no longer part of the stock.

        The object_view and stop_iteration_view parameters are either view
        functios or strings as expected by urlresolvers.reverse. This function
        always results in a redirect. The object_view is used if there is a
        next object. Stop iteration view is used if there is no next object.
        The reverse_args and reverse_kwargs are passed through to the reverse
        call.

        The kwargs are adjusted to have the target object_id or slug.

        All GET query arguments are also passed through to the redirected view.
        """
        if stock_seq is None:
            stock_seq = self.sequencer(request)
        if reverse_kwargs is None:
            reverse_kwargs = {}
        view = object_view
        query_str = None
        try:
            if movement == StockSequencer.NEXT:
                next_stock_seq = stock_seq.next(current_object_id, current_slug, slug_field)
            elif movement == StockSequencer.PREVIOUS:
                next_stock_seq = stock_seq.previous(current_object_id, current_slug, slug_field)
            elif movement == StockSequencer.FIRST:
                next_stock_seq = stock_seq.first()
            elif movement == StockSequencer.LAST:
                next_stock_seq = stock_seq.last()
            elif movement == StockSequencer.TO_INDEX:
                next_stock_seq = stock_seq.to_index(to_index)
            query_str = next_stock_seq.update_query_dict(request.GET.copy()).urlencode()
            if current_slug:
                reverse_kwargs[slug_field] = next_stock_seq.object_at_index[slug_field]
            else:
                reverse_kwargs["object_id"] = next_stock_seq.object_at_index.id
        except StopIteration:
            view = stop_iteration_view
            query_str = request.GET.urlencode()
        url = reverse(view, args=reverse_args, kwargs=reverse_kwargs)
        if query_str:
            url += "?%s" % query_str
        return redirect(url)

# Wrap all the geckoboard views to catch an import error
# in case the django-geckoboard app is not installed.
try:
    from django_geckoboard.decorators import line_chart

    @line_chart
    def stock_line_chart(request, slug):
        """
        Feed a geckoboard line chart. The options that can be set in a GET
        query are points (integer), x_label (string), y_label (string), color
        (string).
        """
        points = int(request.GET.get("points", 50))
        x_label = request.GET.get("x_label", "")
        y_label = request.GET.get("y_label", slug.capitalize())
        color = request.GET.get("color", None)
        records = list(StockRecord.objects.filter(stock=slug).values_list('count', flat=True)[:points])
        records.reverse()
        if color: return ( records, x_label, y_label, color)
        return ( records, x_label, y_label)

except ImportError:
    pass


########NEW FILE########
