__FILENAME__ = admin
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (C) 2011-2014 Star2Billing S.L.
#
# The Initial Developer of the Original Code is
# Arezqui Belaid <info@star2billing.com>
#
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from admin_tools_stats.models import DashboardStatsCriteria, DashboardStats
from admin_tools_stats.app_label_renamer import AppLabelRenamer
AppLabelRenamer(native_app_label=u'admin_tools_stats', app_label=_('Admin Tools Stats')).main()


class DashboardStatsCriteriaAdmin(admin.ModelAdmin):
    """
    Allows the administrator to view and modify certain attributes
    of a DashboardStats.
    """
    list_display = ('id', 'criteria_name', 'created_date')
    list_filter = ['created_date']
    ordering = ('id', )

admin.site.register(DashboardStatsCriteria, DashboardStatsCriteriaAdmin)


class DashboardStatsAdmin(admin.ModelAdmin):
    """
    Allows the administrator to view and modify certain attributes
    of a DashboardStats.
    """
    list_display = ('id', 'graph_key', 'graph_title', 'model_name',
                    'is_visible', 'created_date')
    list_filter = ['created_date']
    ordering = ('id', )

admin.site.register(DashboardStats, DashboardStatsAdmin)

########NEW FILE########
__FILENAME__ = app_label_renamer
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (C) 2011-2014 Star2Billing S.L.
#
# The Initial Developer of the Original Code is
# Arezqui Belaid <info@star2billing.com>
#
from django.contrib import admin
from django.db.models.base import ModelBase
from django.core.urlresolvers import resolve


#TODO: Follow evolution of https://code.djangoproject.com/ticket/3591

# Source link : http://django-notes.blogspot.in/2011/07/django-app-name-breadcrumbs-l10n.html
class AppLabelRenamer(object):
    """
    Rename app label and app breadcrumbs in admin
    """
    def __init__(self, native_app_label, app_label):
        self.native_app_label = native_app_label
        self.app_label = app_label
        self.module = '.'.join([native_app_label, 'models'])

    class string_with_realoaded_title(str):
        ''' thanks to Ionel Maries Cristian for http://ionelmc.wordpress.com/2011/06/24/custom-app-names-in-the-django-admin/'''
        def __new__(cls, value, title):
            instance = str.__new__(cls, value)
            instance._title = title
            return instance

        def title(self):
            return self._title

        __copy__ = lambda self: self
        __deepcopy__ = lambda self, memodict: self

    def rename_app_label(self, f):
        app_label = self.app_label

        def rename_breadcrumbs(f):
            def wrap(self, *args, **kwargs):
                extra_context = kwargs.get('extra_context', {})
                extra_context['app_label'] = app_label
                kwargs['extra_context'] = extra_context
                return f(self, *args, **kwargs)
            return wrap

        def wrap(model_or_iterable, admin_class=None, **option):
            if isinstance(model_or_iterable, ModelBase):
                model_or_iterable = [model_or_iterable]
            for model in model_or_iterable:
                if model.__module__ != self.module:
                    continue
                if admin_class is None:
                    admin_class = type(model.__name__ + 'Admin', (admin.ModelAdmin,), {})
                admin_class.add_view = rename_breadcrumbs(admin_class.add_view)
                admin_class.change_view = rename_breadcrumbs(admin_class.change_view)
                admin_class.changelist_view = rename_breadcrumbs(admin_class.changelist_view)
                model._meta.app_label = self.string_with_realoaded_title(self.native_app_label, self.app_label)
            return f(model, admin_class, **option)
        return wrap

    def rename_app_index(self, f):
        def wrap(request, app_label, extra_context=None):
            requested_app_label = resolve(request.path).kwargs.get('app_label', '')
            if requested_app_label and requested_app_label == self.native_app_label:
                app_label = self.string_with_realoaded_title(self.native_app_label, self.app_label)
            else:
                app_label = requested_app_label
            return f(request, app_label, extra_context=None)
        return wrap

    def main(self):
        admin.site.register = self.rename_app_label(admin.site.register)
        admin.site.app_index = self.rename_app_index(admin.site.app_index)

########NEW FILE########
__FILENAME__ = 0001_initial_migration
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'DashboardStatsCriteria'
        db.create_table(u'dash_stats_criteria', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('criteria_name', self.gf('django.db.models.fields.CharField')(max_length=90, db_index=True)),
            ('criteria_fix_mapping', self.gf('jsonfield.fields.JSONField')(null=True, blank=True)),
            ('dynamic_criteria_field_name', self.gf('django.db.models.fields.CharField')(max_length=90, null=True, blank=True)),
            ('criteria_dynamic_mapping', self.gf('jsonfield.fields.JSONField')(null=True, blank=True)),
            ('created_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal(u'admin_tools_stats', ['DashboardStatsCriteria'])

        # Adding model 'DashboardStats'
        db.create_table(u'dashboard_stats', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('graph_key', self.gf('django.db.models.fields.CharField')(unique=True, max_length=90)),
            ('graph_title', self.gf('django.db.models.fields.CharField')(max_length=90, db_index=True)),
            ('model_app_name', self.gf('django.db.models.fields.CharField')(max_length=90)),
            ('model_name', self.gf('django.db.models.fields.CharField')(max_length=90)),
            ('date_field_name', self.gf('django.db.models.fields.CharField')(max_length=90)),
            ('is_visible', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('created_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal(u'admin_tools_stats', ['DashboardStats'])

        # Adding M2M table for field criteria on 'DashboardStats'
        m2m_table_name = db.shorten_name(u'dashboard_stats_criteria')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('dashboardstats', models.ForeignKey(orm[u'admin_tools_stats.dashboardstats'], null=False)),
            ('dashboardstatscriteria', models.ForeignKey(orm[u'admin_tools_stats.dashboardstatscriteria'], null=False))
        ))
        db.create_unique(m2m_table_name, ['dashboardstats_id', 'dashboardstatscriteria_id'])


    def backwards(self, orm):
        # Deleting model 'DashboardStatsCriteria'
        db.delete_table(u'dash_stats_criteria')

        # Deleting model 'DashboardStats'
        db.delete_table(u'dashboard_stats')

        # Removing M2M table for field criteria on 'DashboardStats'
        db.delete_table(db.shorten_name(u'dashboard_stats_criteria'))


    models = {
        u'admin_tools_stats.dashboardstats': {
            'Meta': {'object_name': 'DashboardStats', 'db_table': "u'dashboard_stats'"},
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'criteria': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['admin_tools_stats.DashboardStatsCriteria']", 'null': 'True', 'blank': 'True'}),
            'date_field_name': ('django.db.models.fields.CharField', [], {'max_length': '90'}),
            'graph_key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '90'}),
            'graph_title': ('django.db.models.fields.CharField', [], {'max_length': '90', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_visible': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'model_app_name': ('django.db.models.fields.CharField', [], {'max_length': '90'}),
            'model_name': ('django.db.models.fields.CharField', [], {'max_length': '90'}),
            'updated_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'admin_tools_stats.dashboardstatscriteria': {
            'Meta': {'object_name': 'DashboardStatsCriteria', 'db_table': "u'dash_stats_criteria'"},
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'criteria_dynamic_mapping': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'criteria_fix_mapping': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'criteria_name': ('django.db.models.fields.CharField', [], {'max_length': '90', 'db_index': 'True'}),
            'dynamic_criteria_field_name': ('django.db.models.fields.CharField', [], {'max_length': '90', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'updated_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['admin_tools_stats']
########NEW FILE########
__FILENAME__ = 0002_add_sum_field_name
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'DashboardStats.sum_field_name'
        db.add_column(u'dashboard_stats', 'sum_field_name',
                      self.gf('django.db.models.fields.CharField')(max_length=90, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'DashboardStats.sum_field_name'
        db.delete_column(u'dashboard_stats', 'sum_field_name')


    models = {
        u'admin_tools_stats.dashboardstats': {
            'Meta': {'object_name': 'DashboardStats', 'db_table': "u'dashboard_stats'"},
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'criteria': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['admin_tools_stats.DashboardStatsCriteria']", 'null': 'True', 'blank': 'True'}),
            'date_field_name': ('django.db.models.fields.CharField', [], {'max_length': '90'}),
            'graph_key': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '90'}),
            'graph_title': ('django.db.models.fields.CharField', [], {'max_length': '90', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_visible': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'model_app_name': ('django.db.models.fields.CharField', [], {'max_length': '90'}),
            'model_name': ('django.db.models.fields.CharField', [], {'max_length': '90'}),
            'sum_field_name': ('django.db.models.fields.CharField', [], {'max_length': '90', 'null': 'True', 'blank': 'True'}),
            'updated_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'admin_tools_stats.dashboardstatscriteria': {
            'Meta': {'object_name': 'DashboardStatsCriteria', 'db_table': "u'dash_stats_criteria'"},
            'created_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'criteria_dynamic_mapping': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'criteria_fix_mapping': ('jsonfield.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'criteria_name': ('django.db.models.fields.CharField', [], {'max_length': '90', 'db_index': 'True'}),
            'dynamic_criteria_field_name': ('django.db.models.fields.CharField', [], {'max_length': '90', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'updated_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['admin_tools_stats']
########NEW FILE########
__FILENAME__ = models
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (C) 2011-2014 Star2Billing S.L.
#
# The Initial Developer of the Original Code is
# Arezqui Belaid <info@star2billing.com>
#
from django.db import models
from django.utils.translation import ugettext_lazy as _
import jsonfield.fields


class DashboardStatsCriteria(models.Model):
    """
    To configure criteria for dashboard graphs

    **Attributes**:

        * ``criteria_name`` - Unique word .
        * ``criteria_fix_mapping`` - JSON data key-value pairs.
        * ``dynamic_criteria_field_name`` - Dynamic criteria field.
        * ``criteria_dynamic_mapping`` - JSON data key-value pairs.
        * ``created_date`` - record created date.
        * ``updated_date`` - record updated date.

    **Name of DB table**: dash_stats_criteria
    """
    criteria_name = models.CharField(max_length=90, db_index=True,
                                     verbose_name=_('criteria name'),
                                     help_text=_("it needs to be one word unique. Ex. status, yesno"))
    criteria_fix_mapping = jsonfield.fields.JSONField(
        null=True, blank=True,
        verbose_name=_("fixed criteria / value"),
        help_text=_("a JSON dictionary of key-value pairs that will be used for the criteria"))
    dynamic_criteria_field_name = models.CharField(
        max_length=90, blank=True, null=True,
        verbose_name=_("dynamic criteria field name"),
        help_text=_("ex. for call records - disposition"))
    criteria_dynamic_mapping = jsonfield.fields.JSONField(
        null=True, blank=True,
        verbose_name=_("dynamic criteria / value"),
        help_text=_("a JSON dictionary of key-value pairs that will be used for the criteria"))
    created_date = models.DateTimeField(auto_now_add=True, verbose_name=_('date'))
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = u'dash_stats_criteria'
        verbose_name = _("dashboard stats criteria")
        verbose_name_plural = _("dashboard stats criteria")

    def __unicode__(self):
            return u"%s" % self.criteria_name


class DashboardStats(models.Model):
    """To configure graphs for dashboard

    **Attributes**:

        * ``graph_key`` - unique graph name.
        * ``graph_title`` - graph title.
        * ``model_app_name`` - App name of model.
        * ``model_name`` - model name.
        * ``date_field_name`` - Date field of model_name.
        * ``criteria`` - many-to-many relationship.
        * ``is_visible`` - enable/disable.
        * ``created_date`` - record created date.
        * ``updated_date`` - record updated date.

    **Name of DB table**: dashboard_stats
    """
    graph_key = models.CharField(unique=True, max_length=90,
                                 verbose_name=_('graph key'),
                                 help_text=_("it needs to be one word unique. ex. auth, mygraph"))
    graph_title = models.CharField(max_length=90, db_index=True,
                                   verbose_name=_('graph title'),
                                   help_text=_("heading title of graph box"))
    model_app_name = models.CharField(max_length=90, verbose_name=_('app name'),
                                      help_text=_("ex. auth / dialer_cdr"))
    model_name = models.CharField(max_length=90, verbose_name=_('model name'),
                                  help_text=_("ex. User"))
    date_field_name = models.CharField(max_length=90, verbose_name=_("date field name"),
                                       help_text=_("ex. date_joined"))
    sum_field_name = models.CharField(max_length=90, verbose_name=_("Sum field name"),
                                      null=True, blank=True,
                                      help_text=_("The field you want to aggregate, ex. amount"))
    criteria = models.ManyToManyField(DashboardStatsCriteria, blank=True, null=True)
    is_visible = models.BooleanField(default=True, verbose_name=_('visible'))
    created_date = models.DateTimeField(auto_now_add=True, verbose_name=_('date'))
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = u'dashboard_stats'
        verbose_name = _("dashboard stats")
        verbose_name_plural = _("dashboard stats")

    def __unicode__(self):
            return u"%d %s" % (self.id, self.graph_key)

########NEW FILE########
__FILENAME__ = modules

#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (C) 2011-2014 Star2Billing S.L.
#
# The Initial Developer of the Original Code is
# Arezqui Belaid <info@star2billing.com>
#
from django.db.models.aggregates import Sum
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _
from django.db.models import get_model
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from qsstats import QuerySetStats
from cache_utils.decorators import cached
from admin_tools.dashboard import modules
from admin_tools_stats.models import DashboardStats
from datetime import datetime, timedelta
import time

# Make timezone aware for Django 1.4
try:
    from django.utils.timezone import now
except ImportError:
    now = datetime.now


class DashboardChart(modules.DashboardModule):
    """Dashboard module with user registration charts.

    Default values are best suited for 2-column dashboard layouts.
    """
    title = _('dashboard stats').title()
    template = 'admin_tools_stats/modules/chart.html'
    days = None
    interval = 'days'
    tooltip_date_format = "%d %b %Y"
    chart_type = 'discreteBarChart'
    chart_height = 300
    chart_width = '100%'
    require_chart_jscss = False
    extra = dict()

    model = None
    graph_key = None
    filter_list = None
    chart_container = None

    def is_empty(self):
        return False

    def __init__(self, *args, **kwargs):
        super(DashboardChart, self).__init__(*args, **kwargs)
        self.select_box_value = ''
        for key in kwargs:
            self.require_chart_jscss = kwargs['require_chart_jscss']
            self.graph_key = kwargs['graph_key']
            if kwargs.get('select_box_' + self.graph_key):
                self.select_box_value = kwargs['select_box_' + self.graph_key]

        if self.days is None:
            #self.days = {'days': 30, 'weeks': 30*7, 'months': 30*12}[self.interval]
            self.days = {'hours': 24, 'days': 7, 'weeks': 7 * 1, 'months': 30 * 2}[self.interval]

        self.data = self.get_registrations(self.interval, self.days,
                                           self.graph_key, self.select_box_value)
        self.prepare_template_data(self.data, self.graph_key, self.select_box_value)

    @cached(60 * 5)
    def get_registrations(self, interval, days, graph_key, select_box_value):
        """ Returns an array with new users count per interval."""
        try:
            conf_data = DashboardStats.objects.get(graph_key=graph_key)
            model_name = get_model(conf_data.model_app_name, conf_data.model_name)
            kwargs = {}

            for i in conf_data.criteria.all():
                # fixed mapping value passed info kwargs
                if i.criteria_fix_mapping:
                    for key in i.criteria_fix_mapping:
                        # value => i.criteria_fix_mapping[key]
                        kwargs[key] = i.criteria_fix_mapping[key]

                # dynamic mapping value passed info kwargs
                if i.dynamic_criteria_field_name and select_box_value:
                    kwargs[i.dynamic_criteria_field_name] = select_box_value

            aggregate = None
            if conf_data.sum_field_name:
                aggregate = Sum(conf_data.sum_field_name)

            stats = QuerySetStats(model_name.objects.filter(**kwargs),
                                  conf_data.date_field_name, aggregate)
            #stats = QuerySetStats(User.objects.filter(is_active=True), 'date_joined')
            today = now()
            if days == 24:
                begin = today - timedelta(hours=days - 1)
                return stats.time_series(begin, today + timedelta(hours=1), interval)

            begin = today - timedelta(days=days - 1)
            return stats.time_series(begin, today + timedelta(days=1), interval)
        except:
            User = get_user_model()
            stats = QuerySetStats(
                User.objects.filter(is_active=True), 'date_joined')
            today = now()
            if days == 24:
                begin = today - timedelta(hours=days - 1)
                return stats.time_series(begin, today + timedelta(hours=1), interval)
            begin = today - timedelta(days=days - 1)
            return stats.time_series(begin, today + timedelta(days=1), interval)

    def prepare_template_data(self, data, graph_key, select_box_value):
        """ Prepares data for template (passed as module attributes) """
        self.extra = {
            'x_is_date': True,
            'tag_script_js': False,
            'jquery_on_ready': False,
        }
        if self.interval == 'months':
            self.tooltip_date_format = "%b"
            self.extra['x_axis_format'] = "%b"
        if self.interval == 'days':
            self.tooltip_date_format = "%d %b %Y"
            self.extra['x_axis_format'] = "%a"
        if self.interval == 'hours':
            self.tooltip_date_format = "%d %b %Y %H:%S"
            self.extra['x_axis_format'] = "%H"

        self.chart_container = self.interval + '_' + self.graph_key
        # add string into href attr
        self.id = self.chart_container

        xdata = []
        ydata = []
        for data_date in self.data:
            start_time = int(time.mktime(data_date[0].timetuple()) * 1000)
            xdata.append(start_time)
            ydata.append(data_date[1])

        extra_serie = {"tooltip": {"y_start": "", "y_end": ""},
                       "date_format": self.tooltip_date_format}

        self.values = {
            'x': xdata,
            'name1': self.interval, 'y1': ydata, 'extra1': extra_serie,
        }

        self.form_field = get_dynamic_criteria(graph_key, select_box_value)


def get_title(graph_key):
    """Returns graph title"""
    try:
        return DashboardStats.objects.get(graph_key=graph_key).graph_title
    except:
        return ''


def get_dynamic_criteria(graph_key, select_box_value):
    """To get dynamic criteria & return into select box to display on dashboard"""
    try:
        temp = ''
        conf_data = DashboardStats.objects.get(graph_key=graph_key).criteria.all()
        for i in conf_data:
            dy_map = i.criteria_dynamic_mapping
            if dy_map:
                temp = '<select name="select_box_' + graph_key + '" onChange="$(\'#stateform\').submit();">'
                for key in dict(dy_map):
                    value = dy_map[key]
                    if key == select_box_value:
                        temp += '<option value="' + key + '" selected=selected>' + value + '</option>'
                    else:
                        temp += '<option value="' + key + '">' + value + '</option>'
                temp += '</select>'

        return mark_safe(force_unicode(temp))
    except:
        return ''


def get_active_graph():
    """Returns active graphs"""
    try:
        return DashboardStats.objects.filter(is_visible=1)
    except:
        return []


def get_registration_charts(**kwargs):
    """ Returns 3 basic chart modules (today, last 7 days & last 3 months) """
    return [
        DashboardChart(_('today').title(), interval='hours', **kwargs),
        DashboardChart(_('last week').title(), interval='days', **kwargs),
        DashboardChart(_('last 2 weeks'), interval='weeks', **kwargs),
        DashboardChart(_('last 3 months').title(), interval='months', **kwargs),
    ]


class DashboardCharts(modules.Group):
    """Group module with 3 default dashboard charts"""
    title = _('new users')

    def __init__(self, *args, **kwargs):
        key_value = kwargs.get('graph_key')
        self.title = get_title(key_value)
        kwargs.setdefault('children', get_registration_charts(**kwargs))
        super(DashboardCharts, self).__init__(*args, **kwargs)

########NEW FILE########
__FILENAME__ = tests
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (C) 2011-2014 Star2Billing S.L.
#
# The Initial Developer of the Original Code is
# Arezqui Belaid <info@star2billing.com>
#

from django.test import TestCase
from admin_tools_stats.models import DashboardStatsCriteria, DashboardStats
from admin_tools_stats.utils import BaseAuthenticatedClient


class AdminToolsStatsAdminInterfaceTestCase(BaseAuthenticatedClient):
    """
    Test cases for django-admin-tools-stats Admin Interface
    """

    def test_admin_tools_stats_dashboardstats(self):
        """Test function to check dashboardstats admin pages"""
        response = self.client.get('/admin/admin_tools_stats/')
        self.failUnlessEqual(response.status_code, 200)
        response = self.client.get('/admin/admin_tools_stats/dashboardstats/')
        self.failUnlessEqual(response.status_code, 200)

    def test_admin_tools_stats_dashboardstatscriteria(self):
        """Test function to check dashboardstatscriteria admin pages"""
        response = \
            self.client.get('/admin/admin_tools_stats/dashboardstatscriteria/')
        self.failUnlessEqual(response.status_code, 200)


class AdminToolsStatsModel(TestCase):
    """
    Test DashboardStatsCriteria, DashboardStats models
    """
    def setUp(self):
        # DashboardStatsCriteria model
        self.dashboard_stats_criteria = DashboardStatsCriteria(
            criteria_name="call_type",
            criteria_fix_mapping='',
            dynamic_criteria_field_name='disposition',
            criteria_dynamic_mapping={
                "INVALIDARGS": "INVALIDARGS",
                "BUSY": "BUSY",
                "TORTURE": "TORTURE",
                "ANSWER": "ANSWER",
                "DONTCALL": "DONTCALL",
                "FORBIDDEN": "FORBIDDEN",
                "NOROUTE": "NOROUTE",
                "CHANUNAVAIL": "CHANUNAVAIL",
                "NOANSWER": "NOANSWER",
                "CONGESTION": "CONGESTION",
                "CANCEL": "CANCEL"
            },
        )
        self.dashboard_stats_criteria.save()
        self.assertEqual(
            self.dashboard_stats_criteria.__unicode__(), 'call_type')

        # DashboardStats model
        self.dashboard_stats = DashboardStats(
            graph_key='user_graph',
            graph_title='User graph',
            model_app_name='auth',
            model_name='User',
            date_field_name='date_joined',
            criteria=self.dashboard_stats_criteria,
            is_visible=1,
        )
        self.dashboard_stats.save()
        self.assertEqual(self.dashboard_stats.__unicode__(), 'user_graph')

    def test_dashboard_criteria(self):
        self.assertEqual(
            self.dashboard_stats_criteria.criteria_name, "call_type")
        self.assertEqual(self.dashboard_stats.graph_key, 'user_graph')

    def teardown(self):
        self.dashboard_stats_criteria.delete()
        self.dashboard_stats.delete()

########NEW FILE########
__FILENAME__ = utils
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (C) 2011-2014 Star2Billing S.L.
#
# The Initial Developer of the Original Code is
# Arezqui Belaid <info@star2billing.com>
#

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.test.client import RequestFactory
import base64
import unittest
import inspect


def build_test_suite_from(test_cases):
    """Returns a single or group of unittest test suite(s) that's ready to be
    run. The function expects a list of classes that are subclasses of
    TestCase.

    The function will search the module where each class resides and
    build a test suite from that class and all subclasses of it.
    """
    test_suites = []
    for test_case in test_cases:
        mod = __import__(test_case.__module__)
        components = test_case.__module__.split('.')
        for comp in components[1:]:
            mod = getattr(mod, comp)
        tests = []
        for item in mod.__dict__.values():
            if type(item) is type and issubclass(item, test_case):
                tests.append(item)
        test_suites.append(unittest.TestSuite(
            map(unittest.TestLoader().loadTestsFromTestCase, tests)))

    return unittest.TestSuite(test_suites)


class BaseAuthenticatedClient(TestCase):
    """Common Authentication"""
    fixtures = ['auth_user.json']

    def setUp(self):
        """To create admin user"""
        self.client = Client()
        self.user = User.objects.get(username='admin')
        auth = '%s:%s' % ('admin', 'admin')
        auth = 'Basic %s' % base64.encodestring(auth)
        auth = auth.strip()
        self.extra = {
            'HTTP_AUTHORIZATION': auth,
        }
        login = self.client.login(username='admin', password='admin')
        self.assertTrue(login)
        self.factory = RequestFactory()


class Choice(object):

    class __metaclass__(type):
        def __init__(self, *args, **kwargs):
            self._data = []
            for name, value in inspect.getmembers(self):
                if not name.startswith('_') and not inspect.ismethod(value):
                    if isinstance(value, tuple) and len(value) > 1:
                        data = value
                    else:
                        pieces = [x.capitalize() for x in name.split('_')]
                        data = (value, ' '.join(pieces))
                    self._data.append(data)
                    setattr(self, name, data[0])

            self._hash = dict(self._data)

        def __iter__(self):
            for value, data in self._data:
                yield value, data

        @classmethod
        def get_value(self, key):
            return self._hash[key]

########NEW FILE########
__FILENAME__ = dashboard
"""
This file was generated with the customdashboard management command, it
contains the two classes for the main dashboard and app index dashboard.
You can customize these classes as you want.

To activate your index dashboard add the following to your settings.py::
    ADMIN_TOOLS_INDEX_DASHBOARD = 'demoproject.dashboard.CustomIndexDashboard'

And to activate the app index dashboard::
    ADMIN_TOOLS_APP_INDEX_DASHBOARD = 'demoproject.dashboard.CustomAppIndexDashboard'
"""

from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

from admin_tools.dashboard import modules, Dashboard, AppIndexDashboard
from admin_tools.utils import get_admin_site_name
from admin_tools_stats.modules import DashboardCharts, get_active_graph


class CustomIndexDashboard(Dashboard):
    """
    Custom index dashboard for demoproject.
    """
    def init_with_context(self, context):
        site_name = get_admin_site_name(context)
        # append a link list module for "quick links"
        self.children.append(modules.LinkList(
            _('Quick links'),
            layout='inline',
            draggable=False,
            deletable=False,
            collapsible=False,
            children=[
                [_('Return to site'), '/'],
                [_('Change password'),
                 reverse('%s:password_change' % site_name)],
                [_('Log out'), reverse('%s:logout' % site_name)],
            ]
        ))

        # append an app list module for "Applications"
        self.children.append(modules.AppList(
            _('Applications'),
            exclude=('django.contrib.*',),
        ))

        # append an app list module for "Administration"
        self.children.append(modules.AppList(
            _('Administration'),
            models=('django.contrib.*',),
        ))

        # append a recent actions module
        self.children.append(modules.RecentActions(_('Recent Actions'), 5))

        # append a feed module
        self.children.append(modules.Feed(
            _('Latest Django News'),
            feed_url='http://www.djangoproject.com/rss/weblog/',
            limit=5
        ))

        # append an app list module
        self.children.append(modules.AppList(
            _('Dashboard Stats Settings'),
            models=('admin_tools_stats.*', ),
        ))

        # Copy following code into your custom dashboard
        # append following code after recent actions module or
        # a link list module for "quick links"
        graph_list = get_active_graph()
        for i in graph_list:
            kwargs = {}
            kwargs['require_chart_jscss'] = True
            kwargs['graph_key'] = i.graph_key

            if context['request'].POST.get('select_box_' + i.graph_key):
                kwargs['select_box_' + i.graph_key] = context['request'].POST['select_box_' + i.graph_key]

            self.children.append(DashboardCharts(**kwargs))

        # append another link list module for "support".
        self.children.append(modules.LinkList(
            _('Support'),
            children=[
                {
                    'title': _('Django documentation'),
                    'url': 'http://docs.djangoproject.com/',
                    'external': True,
                },
                {
                    'title': _('Django "django-users" mailing list'),
                    'url': 'http://groups.google.com/group/django-users',
                    'external': True,
                },
                {
                    'title': _('Django irc channel'),
                    'url': 'irc://irc.freenode.net/django',
                    'external': True,
                },
            ]
        ))


class CustomAppIndexDashboard(AppIndexDashboard):
    """
    Custom app index dashboard for demoproject.
    """

    # we disable title because its redundant with the model list module
    title = ''

    def __init__(self, *args, **kwargs):
        AppIndexDashboard.__init__(self, *args, **kwargs)

        # append a model list module and a recent actions module
        self.children += [
            modules.ModelList(self.app_title, self.models),
            modules.RecentActions(
                _('Recent Actions'),
                include_list=self.get_app_content_types(),
                limit=5
            )
        ]

    def init_with_context(self, context):
        """
        Use this method if you need to access the request context.
        """
        return super(CustomAppIndexDashboard, self).init_with_context(context)

########NEW FILE########
__FILENAME__ = settings
# Django settings for demoproject project.

import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG

APPLICATION_DIR = os.path.dirname(globals()['__file__'])

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), ".."),
)

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'demoproject.db',                      # Or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',                      # Set to empty string for default.
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'static')

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    # 'django.contrib.staticfiles.finders.DefaultStorageFinder',
    'djangobower.finders.BowerFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'sq)9^f#mf444c(#om$zpo0v!%y=%pqem*9s_qav93fwr_&x40u'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)


TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.csrf",
    "django.core.context_processors.tz",
    "django.core.context_processors.request",
)

ROOT_URLCONF = 'demoproject.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'demoproject.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(APPLICATION_DIR, 'templates')
)

INSTALLED_APPS = (
    #admin tool apps
    'admin_tools',
    'admin_tools.theming',
    'admin_tools.menu',
    'admin_tools.dashboard',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_nvd3',
    'djangobower',
    'demoproject',
    'admin_tools_stats',
    'south',
)

# Django extensions
try:
    import django_extensions
except ImportError:
    pass
else:
    INSTALLED_APPS = INSTALLED_APPS + ('django_extensions',)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}


# Django-bower
# ------------

# Specifie path to components root (you need to use absolute path)
BOWER_COMPONENTS_ROOT = os.path.join(PROJECT_ROOT, 'components')

BOWER_PATH = '/usr/local/bin/bower'

BOWER_INSTALLED_APPS = (
    'jquery#2.0.3',
    'jquery-ui#~1.10.3',
    'd3#3.3.6',
    'nvd3#1.1.12-beta',
)

#DJANGO-ADMIN-TOOL
#=================
ADMIN_TOOLS_MENU = 'menu.CustomMenu'
ADMIN_TOOLS_INDEX_DASHBOARD = 'dashboard.CustomIndexDashboard'
ADMIN_TOOLS_APP_INDEX_DASHBOARD = 'dashboard.CustomAppIndexDashboard'
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Django extensions
try:
    import django_extensions
except ImportError:
    pass
else:
    INSTALLED_APPS = INSTALLED_APPS + ('django_extensions',)


#IMPORT LOCAL SETTINGS
#=====================
try:
    from settings_local import *
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url, include

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('demoproject.views',
    url(r'^$', 'home', name='home'),

    # url(r'^demoproject/', include('demoproject.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    url(r'^admin_tools/', include('admin_tools.urls')),
    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
from django.shortcuts import render_to_response
#from django.template.context import RequestContext


def home(request):
    """
    home page
    """
    return render_to_response('home.html')

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for demoproject project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

# We defer to a DJANGO_SETTINGS_MODULE already in the environment. This breaks
# if running multiple sites in the same mod_wsgi process. To fix this, use
# mod_wsgi daemon mode with each site in its own daemon process, or use
# os.environ["DJANGO_SETTINGS_MODULE"] = "demoproject.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demoproject.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demoproject.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = menu
"""
This file was generated with the custommenu management command, it contains
the classes for the admin menu, you can customize this class as you want.

To activate your custom menu add the following to your settings.py::
    ADMIN_TOOLS_MENU = 'demoproject.menu.CustomMenu'
"""

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from admin_tools.menu import items, Menu


class CustomMenu(Menu):
    """
    Custom Menu for demoproject admin site.
    """
    def __init__(self, **kwargs):
        Menu.__init__(self, **kwargs)
        self.children += [
            items.MenuItem(_('Dashboard'), reverse('admin:index')),
            items.Bookmarks(),
            items.AppList(
                _('Applications'),
                exclude=('django.contrib.*',)
            ),
            items.AppList(
                _('Administration'),
                models=('django.contrib.*',)
            )
        ]

    def init_with_context(self, context):
        """
        Use this method if you need to access the request context.
        """
        return super(CustomMenu, self).init_with_context(context)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-admin-tools-stats documentation build configuration file, created by
# sphinx-quickstart on Wed Sep  7 13:28:47 2011.
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
#sys.path.insert(0, os.path.abspath('.'))
#APP_DIR = os.path.normpath(os.path.join(os.getcwd(), '../..'))
#sys.path.insert(0, APP_DIR)

#import settings
#from django.core.management import setup_environ
#setup_environ(settings)
# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.coverage']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-admin-tools-stats'
copyright = u'2011-2014, Arezqui Belaid'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.6.0'
# The full version, including alpha/beta/rc tags.
release = version

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
exclude_patterns = ['_build']

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
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

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
htmlhelp_basename = 'django-admin-tools-stats-doc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index.html', 'django-admin-tools-stats.tex', u'django-admin-tools-stats Documentation',
   u'Arezqui Belaid', 'manual'),
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
    ('index', 'django-admin-tools-stats', u'django-admin-tools-stats Documentation',
     [u'Arezqui Belaid'], 1)
]

########NEW FILE########
