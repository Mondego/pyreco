__FILENAME__ = admin
"""Admin views for the models of the ``calendarium`` app."""
from django.contrib import admin

from calendarium.models import (
    Event,
    EventCategory,
    EventRelation,
    Occurrence,
    Rule,
)


class EventAdmin(admin.ModelAdmin):
    """Custom admin for the ``Event`` model."""
    model = Event
    fields = (
        'title', 'start', 'end', 'description', 'category', 'created_by',
        'rule', 'end_recurring_period', )
    list_display = (
        'title', 'start', 'end', 'category', 'created_by', 'rule',
        'end_recurring_period', )
    search_fields = ('title', 'description', )
    date_hierarchy = 'start'
    list_filter = ('category', )


class EventCategoryAdmin(admin.ModelAdmin):
    """Custom admin to display a small colored square."""
    model = EventCategory
    list_display = ('name', 'color', )
    list_editable = ('color', )


admin.site.register(Event, EventAdmin)
admin.site.register(EventCategory, EventCategoryAdmin)
admin.site.register(EventRelation)
admin.site.register(Occurrence)
admin.site.register(Rule)

########NEW FILE########
__FILENAME__ = constants
"""Constants for the ``calendarium`` app."""
from django.utils.translation import ugettext_lazy as _


FREQUENCIES = {
    'YEARLY': 'YEARLY',
    'MONTHLY': 'MONTHLY',
    'WEEKLY': 'WEEKLY',
    'DAILY': 'DAILY',
}


FREQUENCY_CHOICES = (
    (FREQUENCIES['YEARLY'], _('Yearly')),
    (FREQUENCIES['MONTHLY'], _('Monthly')),
    (FREQUENCIES['WEEKLY'], _('Weekly')),
    (FREQUENCIES['DAILY'], _('Daily')),
)


OCCURRENCE_DECISIONS = {
    'all': 'all',
    'following': 'following',
    'this one': 'this one',
}

OCCURRENCE_DECISION_CHOICESS = (
    (OCCURRENCE_DECISIONS['all'], _('all')),
    (OCCURRENCE_DECISIONS['following'], _('following')),
    (OCCURRENCE_DECISIONS['this one'], _('this one')),
)

########NEW FILE########
__FILENAME__ = forms
"""Forms for the ``calendarium`` app."""
from django import forms
from django.contrib.auth.models import User
from django.forms.models import model_to_dict
from django.utils.timezone import datetime, timedelta

from calendarium.constants import (
    OCCURRENCE_DECISION_CHOICESS,
    OCCURRENCE_DECISIONS,
)
from calendarium.models import Event, Occurrence


class OccurrenceForm(forms.ModelForm):
    """A form for the ``Occurrence`` model."""
    decision = forms.CharField(
        widget=forms.Select(choices=OCCURRENCE_DECISION_CHOICESS),
    )

    cancelled = forms.BooleanField(
        widget=forms.HiddenInput,
        required=False,
    )

    original_start = forms.DateTimeField(
        widget=forms.HiddenInput,
    )

    original_end = forms.DateTimeField(
        widget=forms.HiddenInput,
    )

    event = forms.ModelChoiceField(
        widget=forms.HiddenInput,
        queryset=Event.objects.all(),
    )

    class Meta:
        model = Occurrence

    def save(self):
        cleaned_data = self.cleaned_data
        if cleaned_data['decision'] == OCCURRENCE_DECISIONS['all']:
            changes = dict(
                (key, value) for key, value in cleaned_data.iteritems()
                if value != self.initial.get(key) and self.initial.get(key))
            event = self.instance.event
            # for each field on the event, check for new data in cleaned_data
            for field_name in [field.name for field in event._meta.fields]:
                value = changes.get(field_name)
                if value:
                    setattr(event, field_name, value)
            event.save()

            # repeat for persistent occurrences
            for occ in event.occurrences.all():
                for field_name in [field.name for field in occ._meta.fields]:
                    value = changes.get(field_name)
                    if value:
                        # since we can't just set a new datetime, we have to
                        # adjust the datetime fields according to the changes
                        # on the occurrence form instance
                        if type(value) != datetime:
                            setattr(occ, field_name, value)
                        else:
                            initial_time = self.initial.get(field_name)
                            occ_time = getattr(occ, field_name)
                            delta = value - initial_time
                            new_time = occ_time + delta
                            setattr(occ, field_name, new_time)
                occ.save()

            # get everything from initial and compare to cleaned_data to
            # retrieve what has been changed
            # apply those changes to the persistent occurrences (and the main
            # event)
        elif cleaned_data['decision'] == OCCURRENCE_DECISIONS['this one']:
            self.instance.save()
        elif cleaned_data['decision'] == OCCURRENCE_DECISIONS['following']:
            # get the changes
            changes = dict(
                (key, value) for key, value in cleaned_data.iteritems()
                if value != self.initial.get(key) and self.initial.get(key))

            # change the old event
            old_event = self.instance.event
            end_recurring_period = self.instance.event.end_recurring_period
            old_event.end_recurring_period = self.instance.start - timedelta(
                days=1)
            old_event.save()

            # the instance occurrence holds the info for the new event, that we
            # use to update the old event's fields
            new_event = old_event
            new_event.end_recurring_period = end_recurring_period
            new_event.id = None
            event_kwargs = model_to_dict(self.instance)
            for field_name in [field.name for field in new_event._meta.fields]:
                if (field_name == 'created_by'
                        and event_kwargs.get('created_by')):
                    value = User.objects.get(pk=event_kwargs.get(field_name))
                elif field_name in ['rule', 'category']:
                    continue
                else:
                    value = event_kwargs.get(field_name)
                if value:
                    setattr(new_event, field_name, value)
            new_event.save()

########NEW FILE########
__FILENAME__ = 0001_initial
# flake8: noqa
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Event'
        db.create_table('calendarium_event', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('start', self.gf('django.db.models.fields.DateTimeField')()),
            ('end', self.gf('django.db.models.fields.DateTimeField')()),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('description', self.gf('django.db.models.fields.TextField')(max_length=2048)),
            ('creation_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='events', to=orm['auth.User'])),
            ('category', self.gf('django.db.models.fields.related.ForeignKey')(related_name='events', to=orm['calendarium.EventCategory'])),
            ('rule', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['calendarium.Rule'])),
            ('end_recurring_period', self.gf('django.db.models.fields.DateTimeField')()),
        ))
        db.send_create_signal('calendarium', ['Event'])

        # Adding model 'EventCategory'
        db.create_table('calendarium_eventcategory', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('color', self.gf('django.db.models.fields.CharField')(max_length=6)),
        ))
        db.send_create_signal('calendarium', ['EventCategory'])

        # Adding model 'EventRelation'
        db.create_table('calendarium_eventrelation', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('event', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['calendarium.Event'])),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('object_id', self.gf('django.db.models.fields.IntegerField')()),
            ('relation_type', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
        ))
        db.send_create_signal('calendarium', ['EventRelation'])

        # Adding model 'Occurrence'
        db.create_table('calendarium_occurrence', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('start', self.gf('django.db.models.fields.DateTimeField')()),
            ('end', self.gf('django.db.models.fields.DateTimeField')()),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('description', self.gf('django.db.models.fields.TextField')(max_length=2048)),
            ('creation_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='occurrences', to=orm['auth.User'])),
            ('event', self.gf('django.db.models.fields.related.ForeignKey')(related_name='occurrences', to=orm['calendarium.Event'])),
            ('original_start', self.gf('django.db.models.fields.DateTimeField')()),
            ('original_end', self.gf('django.db.models.fields.DateTimeField')()),
        ))
        db.send_create_signal('calendarium', ['Occurrence'])

        # Adding model 'Rule'
        db.create_table('calendarium_rule', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('frequency', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('params', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('calendarium', ['Rule'])


    def backwards(self, orm):
        # Deleting model 'Event'
        db.delete_table('calendarium_event')

        # Deleting model 'EventCategory'
        db.delete_table('calendarium_eventcategory')

        # Deleting model 'EventRelation'
        db.delete_table('calendarium_eventrelation')

        # Deleting model 'Occurrence'
        db.delete_table('calendarium_occurrence')

        # Deleting model 'Rule'
        db.delete_table('calendarium_rule')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'calendarium.event': {
            'Meta': {'object_name': 'Event'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'events'", 'to': "orm['calendarium.EventCategory']"}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'events'", 'to': "orm['auth.User']"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '2048'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'end_recurring_period': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rule': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['calendarium.Rule']"}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'calendarium.eventcategory': {
            'Meta': {'object_name': 'EventCategory'},
            'color': ('django.db.models.fields.CharField', [], {'max_length': '6'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'calendarium.eventrelation': {
            'Meta': {'object_name': 'EventRelation'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['calendarium.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {}),
            'relation_type': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'})
        },
        'calendarium.occurrence': {
            'Meta': {'object_name': 'Occurrence'},
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'occurrences'", 'to': "orm['auth.User']"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '2048'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'occurrences'", 'to': "orm['calendarium.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'original_end': ('django.db.models.fields.DateTimeField', [], {}),
            'original_start': ('django.db.models.fields.DateTimeField', [], {}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'calendarium.rule': {
            'Meta': {'object_name': 'Rule'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'frequency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'params': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['calendarium']
########NEW FILE########
__FILENAME__ = 0002_auto__add_field_occurrence_cancelled__chg_field_event_rule
# flake8: noqa
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Occurrence.cancelled'
        db.add_column('calendarium_occurrence', 'cancelled',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


        # Changing field 'Event.rule'
        db.alter_column('calendarium_event', 'rule_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['calendarium.Rule'], null=True))

    def backwards(self, orm):
        # Deleting field 'Occurrence.cancelled'
        db.delete_column('calendarium_occurrence', 'cancelled')


        # User chose to not deal with backwards NULL issues for 'Event.rule'
        raise RuntimeError("Cannot reverse this migration. 'Event.rule' and its values cannot be restored.")

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'calendarium.event': {
            'Meta': {'object_name': 'Event'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'events'", 'to': "orm['calendarium.EventCategory']"}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'events'", 'to': "orm['auth.User']"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '2048'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'end_recurring_period': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rule': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['calendarium.Rule']", 'null': 'True', 'blank': 'True'}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'calendarium.eventcategory': {
            'Meta': {'object_name': 'EventCategory'},
            'color': ('django.db.models.fields.CharField', [], {'max_length': '6'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'calendarium.eventrelation': {
            'Meta': {'object_name': 'EventRelation'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['calendarium.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {}),
            'relation_type': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'})
        },
        'calendarium.occurrence': {
            'Meta': {'object_name': 'Occurrence'},
            'cancelled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'occurrences'", 'to': "orm['auth.User']"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '2048'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'occurrences'", 'to': "orm['calendarium.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'original_end': ('django.db.models.fields.DateTimeField', [], {}),
            'original_start': ('django.db.models.fields.DateTimeField', [], {}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'calendarium.rule': {
            'Meta': {'object_name': 'Rule'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'frequency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'params': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['calendarium']

########NEW FILE########
__FILENAME__ = 0003_auto__chg_field_event_end_recurring_period
# flake8: noqa
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Event.end_recurring_period'
        db.alter_column('calendarium_event', 'end_recurring_period', self.gf('django.db.models.fields.DateTimeField')(null=True))

    def backwards(self, orm):

        # User chose to not deal with backwards NULL issues for 'Event.end_recurring_period'
        raise RuntimeError("Cannot reverse this migration. 'Event.end_recurring_period' and its values cannot be restored.")

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'calendarium.event': {
            'Meta': {'object_name': 'Event'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'events'", 'to': "orm['calendarium.EventCategory']"}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'events'", 'to': "orm['auth.User']"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '2048', 'blank': 'True'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'end_recurring_period': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rule': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['calendarium.Rule']", 'null': 'True', 'blank': 'True'}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'calendarium.eventcategory': {
            'Meta': {'object_name': 'EventCategory'},
            'color': ('django.db.models.fields.CharField', [], {'max_length': '6'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'calendarium.eventrelation': {
            'Meta': {'object_name': 'EventRelation'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['calendarium.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {}),
            'relation_type': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'})
        },
        'calendarium.occurrence': {
            'Meta': {'object_name': 'Occurrence'},
            'cancelled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'occurrences'", 'to': "orm['auth.User']"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '2048', 'blank': 'True'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'occurrences'", 'to': "orm['calendarium.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'original_end': ('django.db.models.fields.DateTimeField', [], {}),
            'original_start': ('django.db.models.fields.DateTimeField', [], {}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '256', 'blank': 'True'})
        },
        'calendarium.rule': {
            'Meta': {'object_name': 'Rule'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'frequency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'params': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['calendarium']

########NEW FILE########
__FILENAME__ = 0004_auto__chg_field_eventcategory_color
# flake8: noqa
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'EventCategory.color'
        db.alter_column('calendarium_eventcategory', 'color', self.gf('calendarium.models.ColorField')(max_length=6))

    def backwards(self, orm):

        # Changing field 'EventCategory.color'
        db.alter_column('calendarium_eventcategory', 'color', self.gf('django.db.models.fields.CharField')(max_length=6))

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'calendarium.event': {
            'Meta': {'object_name': 'Event'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'events'", 'to': "orm['calendarium.EventCategory']"}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'events'", 'to': "orm['auth.User']"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '2048', 'blank': 'True'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'end_recurring_period': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rule': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['calendarium.Rule']", 'null': 'True', 'blank': 'True'}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'calendarium.eventcategory': {
            'Meta': {'object_name': 'EventCategory'},
            'color': ('calendarium.models.ColorField', [], {'max_length': '6'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'calendarium.eventrelation': {
            'Meta': {'object_name': 'EventRelation'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['calendarium.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {}),
            'relation_type': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'})
        },
        'calendarium.occurrence': {
            'Meta': {'object_name': 'Occurrence'},
            'cancelled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'occurrences'", 'to': "orm['auth.User']"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '2048', 'blank': 'True'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'occurrences'", 'to': "orm['calendarium.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'original_end': ('django.db.models.fields.DateTimeField', [], {}),
            'original_start': ('django.db.models.fields.DateTimeField', [], {}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '256', 'blank': 'True'})
        },
        'calendarium.rule': {
            'Meta': {'object_name': 'Rule'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'frequency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'params': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['calendarium']
########NEW FILE########
__FILENAME__ = 0005_auto__chg_field_event_created_by
# flake8: noqa
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Event.created_by'
        db.alter_column('calendarium_event', 'created_by_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['auth.User']))

    def backwards(self, orm):

        # User chose to not deal with backwards NULL issues for 'Event.created_by'
        raise RuntimeError("Cannot reverse this migration. 'Event.created_by' and its values cannot be restored.")

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'calendarium.event': {
            'Meta': {'object_name': 'Event'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'events'", 'to': "orm['calendarium.EventCategory']"}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'events'", 'null': 'True', 'to': "orm['auth.User']"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '2048', 'blank': 'True'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'end_recurring_period': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rule': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['calendarium.Rule']", 'null': 'True', 'blank': 'True'}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'calendarium.eventcategory': {
            'Meta': {'object_name': 'EventCategory'},
            'color': ('calendarium.models.ColorField', [], {'max_length': '6'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'calendarium.eventrelation': {
            'Meta': {'object_name': 'EventRelation'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['calendarium.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {}),
            'relation_type': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'})
        },
        'calendarium.occurrence': {
            'Meta': {'object_name': 'Occurrence'},
            'cancelled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'occurrences'", 'to': "orm['auth.User']"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '2048', 'blank': 'True'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'occurrences'", 'to': "orm['calendarium.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'original_end': ('django.db.models.fields.DateTimeField', [], {}),
            'original_start': ('django.db.models.fields.DateTimeField', [], {}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '256', 'blank': 'True'})
        },
        'calendarium.rule': {
            'Meta': {'object_name': 'Rule'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'frequency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'params': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['calendarium']
########NEW FILE########
__FILENAME__ = 0006_auto__chg_field_occurrence_created_by
# flake8: noqa
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Occurrence.created_by'
        db.alter_column('calendarium_occurrence', 'created_by_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['auth.User']))

    def backwards(self, orm):

        # User chose to not deal with backwards NULL issues for 'Occurrence.created_by'
        raise RuntimeError("Cannot reverse this migration. 'Occurrence.created_by' and its values cannot be restored.")

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'calendarium.event': {
            'Meta': {'object_name': 'Event'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'events'", 'to': "orm['calendarium.EventCategory']"}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'events'", 'null': 'True', 'to': "orm['auth.User']"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '2048', 'blank': 'True'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'end_recurring_period': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rule': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['calendarium.Rule']", 'null': 'True', 'blank': 'True'}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'calendarium.eventcategory': {
            'Meta': {'object_name': 'EventCategory'},
            'color': ('calendarium.models.ColorField', [], {'max_length': '6'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'calendarium.eventrelation': {
            'Meta': {'object_name': 'EventRelation'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['calendarium.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {}),
            'relation_type': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'})
        },
        'calendarium.occurrence': {
            'Meta': {'object_name': 'Occurrence'},
            'cancelled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'occurrences'", 'null': 'True', 'to': "orm['auth.User']"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '2048', 'blank': 'True'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'occurrences'", 'to': "orm['calendarium.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'original_end': ('django.db.models.fields.DateTimeField', [], {}),
            'original_start': ('django.db.models.fields.DateTimeField', [], {}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '256', 'blank': 'True'})
        },
        'calendarium.rule': {
            'Meta': {'object_name': 'Rule'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'frequency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'params': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['calendarium']
########NEW FILE########
__FILENAME__ = 0007_auto__chg_field_event_category
# flake8: noqa
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Event.category'
        db.alter_column('calendarium_event', 'category_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['calendarium.EventCategory']))

    def backwards(self, orm):

        # User chose to not deal with backwards NULL issues for 'Event.category'
        raise RuntimeError("Cannot reverse this migration. 'Event.category' and its values cannot be restored.")

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'calendarium.event': {
            'Meta': {'object_name': 'Event'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'events'", 'null': 'True', 'to': "orm['calendarium.EventCategory']"}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'events'", 'null': 'True', 'to': "orm['auth.User']"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '2048', 'blank': 'True'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'end_recurring_period': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rule': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['calendarium.Rule']", 'null': 'True', 'blank': 'True'}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'calendarium.eventcategory': {
            'Meta': {'object_name': 'EventCategory'},
            'color': ('calendarium.models.ColorField', [], {'max_length': '6'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'calendarium.eventrelation': {
            'Meta': {'object_name': 'EventRelation'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['calendarium.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {}),
            'relation_type': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'})
        },
        'calendarium.occurrence': {
            'Meta': {'object_name': 'Occurrence'},
            'cancelled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'occurrences'", 'null': 'True', 'to': "orm['auth.User']"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '2048', 'blank': 'True'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'occurrences'", 'to': "orm['calendarium.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'original_end': ('django.db.models.fields.DateTimeField', [], {}),
            'original_start': ('django.db.models.fields.DateTimeField', [], {}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '256', 'blank': 'True'})
        },
        'calendarium.rule': {
            'Meta': {'object_name': 'Rule'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'frequency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'params': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['calendarium']

########NEW FILE########
__FILENAME__ = 0008_auto__add_field_eventcategory_parent
# flake8: noqa
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'EventCategory.parent'
        db.add_column('calendarium_eventcategory', 'parent',
                      self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='parents', null=True, to=orm['calendarium.EventCategory']),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'EventCategory.parent'
        db.delete_column('calendarium_eventcategory', 'parent_id')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'calendarium.event': {
            'Meta': {'object_name': 'Event'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'events'", 'null': 'True', 'to': "orm['calendarium.EventCategory']"}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'events'", 'null': 'True', 'to': "orm['auth.User']"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '2048', 'blank': 'True'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'end_recurring_period': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rule': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['calendarium.Rule']", 'null': 'True', 'blank': 'True'}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'calendarium.eventcategory': {
            'Meta': {'object_name': 'EventCategory'},
            'color': ('calendarium.models.ColorField', [], {'max_length': '6'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'parents'", 'null': 'True', 'to': "orm['calendarium.EventCategory']"})
        },
        'calendarium.eventrelation': {
            'Meta': {'object_name': 'EventRelation'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['calendarium.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {}),
            'relation_type': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'})
        },
        'calendarium.occurrence': {
            'Meta': {'object_name': 'Occurrence'},
            'cancelled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'occurrences'", 'null': 'True', 'to': "orm['auth.User']"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '2048', 'blank': 'True'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'occurrences'", 'to': "orm['calendarium.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'original_end': ('django.db.models.fields.DateTimeField', [], {}),
            'original_start': ('django.db.models.fields.DateTimeField', [], {}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '256', 'blank': 'True'})
        },
        'calendarium.rule': {
            'Meta': {'object_name': 'Rule'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'frequency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'params': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['calendarium']

########NEW FILE########
__FILENAME__ = 0009_auto__add_field_eventcategory_slug
# flake8: noqa
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'EventCategory.slug'
        db.add_column('calendarium_eventcategory', 'slug',
                      self.gf('django.db.models.fields.SlugField')(default='', max_length=256, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'EventCategory.slug'
        db.delete_column('calendarium_eventcategory', 'slug')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'calendarium.event': {
            'Meta': {'object_name': 'Event'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'events'", 'null': 'True', 'to': "orm['calendarium.EventCategory']"}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'events'", 'null': 'True', 'to': "orm['auth.User']"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '2048', 'blank': 'True'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'end_recurring_period': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rule': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['calendarium.Rule']", 'null': 'True', 'blank': 'True'}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'calendarium.eventcategory': {
            'Meta': {'object_name': 'EventCategory'},
            'color': ('calendarium.models.ColorField', [], {'max_length': '6'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'parents'", 'null': 'True', 'to': "orm['calendarium.EventCategory']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '256', 'blank': 'True'})
        },
        'calendarium.eventrelation': {
            'Meta': {'object_name': 'EventRelation'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['calendarium.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {}),
            'relation_type': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'})
        },
        'calendarium.occurrence': {
            'Meta': {'object_name': 'Occurrence'},
            'cancelled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'occurrences'", 'null': 'True', 'to': "orm['auth.User']"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '2048', 'blank': 'True'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'occurrences'", 'to': "orm['calendarium.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'original_end': ('django.db.models.fields.DateTimeField', [], {}),
            'original_start': ('django.db.models.fields.DateTimeField', [], {}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '256', 'blank': 'True'})
        },
        'calendarium.rule': {
            'Meta': {'object_name': 'Rule'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'frequency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'params': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['calendarium']

########NEW FILE########
__FILENAME__ = 0010_auto__add_field_event_image
# flake8: noqa
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Event.image'
        db.add_column('calendarium_event', 'image',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['filer.Image'], null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Event.image'
        db.delete_column('calendarium_event', 'image_id')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'calendarium.event': {
            'Meta': {'object_name': 'Event'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'events'", 'null': 'True', 'to': "orm['calendarium.EventCategory']"}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'events'", 'null': 'True', 'to': "orm['auth.User']"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '2048', 'blank': 'True'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'end_recurring_period': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Image']", 'null': 'True', 'blank': 'True'}),
            'rule': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['calendarium.Rule']", 'null': 'True', 'blank': 'True'}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'calendarium.eventcategory': {
            'Meta': {'object_name': 'EventCategory'},
            'color': ('calendarium.models.ColorField', [], {'max_length': '6'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'parents'", 'null': 'True', 'to': "orm['calendarium.EventCategory']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '256', 'blank': 'True'})
        },
        'calendarium.eventrelation': {
            'Meta': {'object_name': 'EventRelation'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['calendarium.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {}),
            'relation_type': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'})
        },
        'calendarium.occurrence': {
            'Meta': {'object_name': 'Occurrence'},
            'cancelled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'occurrences'", 'null': 'True', 'to': "orm['auth.User']"}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '2048', 'blank': 'True'}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'occurrences'", 'to': "orm['calendarium.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'original_end': ('django.db.models.fields.DateTimeField', [], {}),
            'original_start': ('django.db.models.fields.DateTimeField', [], {}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '256', 'blank': 'True'})
        },
        'calendarium.rule': {
            'Meta': {'object_name': 'Rule'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'frequency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'params': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.file': {
            'Meta': {'object_name': 'File'},
            '_file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'all_files'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'polymorphic_ctype': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polymorphic_filer.file_set'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'sha1': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40', 'blank': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folder': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('parent', 'name'),)", 'object_name': 'Folder'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.image': {
            'Meta': {'object_name': 'Image', '_ormbases': ['filer.File']},
            '_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['filer.File']", 'unique': 'True', 'primary_key': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['calendarium']
########NEW FILE########
__FILENAME__ = models
"""
Models for the ``calendarium`` app.

The code of these models is highly influenced by or taken from the models of
django-schedule:

https://github.com/thauber/django-schedule/tree/master/schedule/models

"""
import json
from dateutil import rrule

from django.conf import settings
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.template.defaultfilters import slugify
from django.utils.timezone import timedelta
from django.utils.translation import ugettext_lazy as _

from calendarium.constants import FREQUENCY_CHOICES, OCCURRENCE_DECISIONS
from calendarium.utils import OccurrenceReplacer
from calendarium.widgets import ColorPickerWidget
from filer.fields.image import FilerImageField
from south.modelsinspector import add_introspection_rules


class ColorField(models.CharField):
    """Custom color field to display a color picker."""
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 6
        super(ColorField, self).__init__(*args, **kwargs)
        self.validators.append(RegexValidator(
            regex='^([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$',
            message='Only RGB color model inputs allowed, like 00000',
            code='nomatch'))

    def formfield(self, **kwargs):
        kwargs['widget'] = ColorPickerWidget
        return super(ColorField, self).formfield(**kwargs)


add_introspection_rules([], ["^calendarium\.models\.ColorField"])


class EventModelManager(models.Manager):
    """Custom manager for the ``Event`` model class."""
    def get_occurrences(self, start, end, category=None):
        """Returns a list of events and occurrences for the given period."""
        # we always want the time of start and end to be at 00:00
        start = start.replace(minute=0, hour=0)
        end = end.replace(minute=0, hour=0)
        # if we recieve the date of one day as start and end, we need to set
        # end one day forward
        if start == end:
            end = start + timedelta(days=1)

        # retrieving relevant events
        # TODO currently for events with a rule, I can't properly find out when
        # the last occurrence of the event ends, or find a way to filter that,
        # so I'm still fetching **all** events before this period, that have a
        # end_recurring_period.
        # For events without a rule, I fetch only the relevant ones.
        qs = self.get_query_set()
        if category:
            qs = qs.filter(start__lt=end)
            relevant_events = qs.filter(
                Q(category=category) |
                Q(category__parent=category)
            )
        else:
            relevant_events = qs.filter(start__lt=end)
        # get all occurrences for those events that don't already have a
        # persistent match and that lie in this period.
        all_occurrences = []
        for event in relevant_events:
            all_occurrences.extend(event.get_occurrences(start, end))

        # sort and return
        return sorted(all_occurrences, key=lambda x: x.start)


class EventModelMixin(models.Model):
    """
    Abstract base class to prevent code duplication.
    :start: The start date of the event.
    :end: The end date of the event.
    :creation_date: When this event was created.
    :description: The description of the event.

    """
    start = models.DateTimeField(
        verbose_name=_('Start date'),
    )

    end = models.DateTimeField(
        verbose_name=_('End date'),
    )

    creation_date = models.DateTimeField(
        verbose_name=_('Creation date'),
        auto_now_add=True,
    )

    description = models.TextField(
        max_length=2048,
        verbose_name=_('Description'),
        blank=True,
    )

    def __unicode__(self):
        return self.title

    def save(self, *args, **kwargs):
        # start should override end if end is set wrong. This auto-corrects
        # usage errors when creating or updating events.
        if self.end < self.start:
            self.end = self.start
        return super(EventModelMixin, self).save(*args, **kwargs)

    class Meta:
        abstract = True


class Event(EventModelMixin):
    """
    Hold the information about an event in the calendar.

    :created_by: FK to the ``User``, who created this event.
    :category: FK to the ``EventCategory`` this event belongs to.
    :rule: FK to the definition of the recurrence of an event.
    :end_recurring_period: The possible end of the recurring definition.
    :title: The title of the event.
    :image: Optional image of the event.

    """

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('Created by'),
        related_name='events',
        blank=True, null=True,
    )

    category = models.ForeignKey(
        'EventCategory',
        verbose_name=_('Category'),
        related_name='events',
        null=True, blank=True,
    )

    rule = models.ForeignKey(
        'Rule',
        verbose_name=_('Rule'),
        blank=True, null=True,
    )

    end_recurring_period = models.DateTimeField(
        verbose_name=_('End of recurring'),
        blank=True, null=True,
    )

    title = models.CharField(
        max_length=256,
        verbose_name=_('Title'),
    )

    image = FilerImageField(
        verbose_name=_('Image'),
        related_name='calendarium_event_images',
        null=True, blank=True,
    )

    objects = EventModelManager()

    def get_absolute_url(self):
        return reverse('calendar_event_detail', kwargs={'pk': self.pk})

    def _create_occurrence(self, occ_start, occ_end=None):
        """Creates an Occurrence instance."""
        # if the length is not altered, it is okay to only pass occ_start
        if not occ_end:
            occ_end = occ_start + (self.end - self.start)
        return Occurrence(
            event=self, start=occ_start, end=occ_end,
            # TODO not sure why original start and end also are occ_start/_end
            original_start=occ_start, original_end=occ_end,
            title=self.title, description=self.description,
            creation_date=self.creation_date, created_by=self.created_by)

    def _get_date_gen(self, rr, start, end):
        """Returns a generator to create the start dates for occurrences."""
        date = rr.after(start)
        while end and date <= end or not(end):
            yield date
            date = rr.after(date)

    def _get_occurrence_gen(self, start, end):
        """Computes all occurrences for this event from start to end."""
        # get length of the event
        length = self.end - self.start

        if self.rule:
            # if the end of the recurring period is before the end arg passed
            # the end of the recurring period should be the new end
            if self.end_recurring_period and end and (
                    self.end_recurring_period < end):
                end = self.end_recurring_period
            # making start date generator
            occ_start_gen = self._get_date_gen(
                self.get_rrule_object(),
                start - length, end)

            # chosing the first item from the generator to initiate
            occ_start = occ_start_gen.next()
            while not end or (end and occ_start <= end):
                occ_end = occ_start + length
                yield self._create_occurrence(occ_start, occ_end)
                occ_start = occ_start_gen.next()
        else:
            # check if event is in the period
            if (not end or self.start < end) and self.end >= start:
                yield self._create_occurrence(self.start, self.end)

    def get_occurrences(self, start, end=None):
        """Returns all occurrences from start to end."""
        # get persistent occurrences
        persistent_occurrences = self.occurrences.all()

        # setup occ_replacer with p_occs
        occ_replacer = OccurrenceReplacer(persistent_occurrences)

        # compute own occurrences according to rule that overlap with the
        # period
        occurrence_gen = self._get_occurrence_gen(start, end)
        # get additional occs, that we need to take into concern
        additional_occs = occ_replacer.get_additional_occurrences(
            start, end)
        occ = occurrence_gen.next()
        while not end or (occ.start < end or any(additional_occs)):
            if occ_replacer.has_occurrence(occ):
                p_occ = occ_replacer.get_occurrence(occ)

                # if the persistent occ falls into the period, replace it
                if (end and p_occ.start < end) and p_occ.end >= start:
                    estimated_occ = p_occ
            else:
                # if there is no persistent match, use the original occ
                estimated_occ = occ

            if any(additional_occs) and (
                    estimated_occ.start == additional_occs[0].start):
                final_occ = additional_occs.pop(0)
            else:
                final_occ = estimated_occ
            if not final_occ.cancelled:
                yield final_occ
            occ = occurrence_gen.next()

    def get_parent_category(self):
        """Returns the main category of this event."""
        if self.category.parent:
            return self.category.parent
        return self.category

    def get_rrule_object(self):
        """Returns the rrule object for this ``Event``."""
        if self.rule:
            params = self.rule.get_params()
            frequency = 'rrule.{0}'.format(self.rule.frequency)
            return rrule.rrule(eval(frequency), dtstart=self.start, **params)


class EventCategory(models.Model):
    """
    The category of an event.

    :name: The name of the category.
    :slug: The slug of the category.
    :color: The color of the category.
    :parent: Allows you to create hierarchies of event categories.

    """
    name = models.CharField(
        max_length=256,
        verbose_name=_('Name'),
    )

    slug = models.SlugField(
        max_length=256,
        verbose_name=_('Slug'),
        blank=True,
    )

    color = ColorField(
        verbose_name=_('Color'),
    )

    parent = models.ForeignKey(
        'calendarium.EventCategory',
        verbose_name=_('Parent'),
        related_name='parents',
        null=True, blank=True,
    )

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        return super(EventCategory, self).save(*args, **kwargs)


class EventRelation(models.Model):
    """
    This class allows to relate additional or external data to an event.

    :event: A FK to the ``Event`` this additional data is related to.
    :content_type: A FK to ContentType of the generic object.
    :object_id: The id of the generic object.
    :content_object: The generic foreign key to the generic object.
    :relation_type: A string representing the type of the relation. This allows
        to relate to the same content_type several times but mean different
        things, such as (normal_guests, speakers, keynote_speakers, all being
        Guest instances)

    """

    event = models.ForeignKey(
        'Event',
        verbose_name=_("Event"),
    )

    content_type = models.ForeignKey(
        ContentType,
    )

    object_id = models.IntegerField()

    content_object = generic.GenericForeignKey(
        'content_type',
        'object_id',
    )

    relation_type = models.CharField(
        verbose_name=_('Relation type'),
        max_length=32,
        blank=True, null=True,
    )

    def __unicode__(self):
        return 'type "{0}" for "{1}"'.format(
            self.relation_type, self.event.title)


class Occurrence(EventModelMixin):
    """
    Needed if one occurrence of an event has slightly different settings than
    all other.

    :created_by: FK to the ``User``, who created this event.
    :event: FK to the ``Event`` this ``Occurrence`` belongs to.
    :original_start: The original start of the related ``Event``.
    :original_end: The original end of the related ``Event``.
    :cancelled: True or false of the occurrence's cancellation status.
    :title: The title of the event.

    """
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('Created by'),
        related_name='occurrences',
        blank=True, null=True,
    )

    event = models.ForeignKey(
        'Event',
        verbose_name=_('Event'),
        related_name='occurrences',
    )

    original_start = models.DateTimeField(
        verbose_name=_('Original start'),
    )

    original_end = models.DateTimeField(
        verbose_name=_('Original end'),
    )

    cancelled = models.BooleanField(
        verbose_name=_('Cancelled'),
    )

    title = models.CharField(
        max_length=256,
        verbose_name=_('Title'),
        blank=True,
    )

    def category(self):
        return self.event.category

    def delete_period(self, period):
        """Deletes a set of occurrences based on the given decision."""
        # check if this is the last or only one
        is_last = False
        is_only = False
        gen = self.event.get_occurrences(
            self.start, self.event.end_recurring_period)
        occs = list(set([occ for occ in gen]))
        if len(occs) == 1:
            is_only = True
        elif len(occs) > 1 and self == occs[-1]:
            is_last = True
        if period == OCCURRENCE_DECISIONS['all']:
            # delete all persistent occurrences along with the parent event
            self.event.occurrences.all().delete()
            self.event.delete()
        elif period == OCCURRENCE_DECISIONS['this one']:
            # check if it is the last one. If so, shorten the recurring period,
            # otherwise cancel the event
            if is_last:
                self.event.end_recurring_period = self.start - timedelta(
                    days=1)
                self.event.save()
            elif is_only:
                self.event.occurrences.all().delete()
                self.event.delete()
            else:
                self.cancelled = True
                self.save()
        elif period == OCCURRENCE_DECISIONS['following']:
            # just shorten the recurring period
            self.event.end_recurring_period = self.start - timedelta(days=1)
            self.event.occurrences.filter(start__gte=self.start).delete()
            if is_only:
                self.event.delete()
            else:
                self.event.save()

    def get_absolute_url(self):
        return reverse(
            'calendar_occurrence_detail', kwargs={
                'pk': self.event.pk, 'year': self.start.year,
                'month': self.start.month, 'day': self.start.day})


class Rule(models.Model):
    """
    This defines the rule by which an event will recur.

    :name: Name of this rule.
    :description: Description of this rule.
    :frequency: A string representing the frequency of the recurrence.
    :params: JSON string to hold the exact rule parameters as used by
        dateutil.rrule to define the pattern of the recurrence.

    """
    name = models.CharField(
        verbose_name=_("name"),
        max_length=32,
    )

    description = models.TextField(
        _("description"),
    )

    frequency = models.CharField(
        verbose_name=_("frequency"),
        choices=FREQUENCY_CHOICES,
        max_length=10,
    )

    params = models.TextField(
        verbose_name=_("params"),
        blank=True, null=True,
    )

    def __unicode__(self):
        return self.name

    def get_params(self):
        if self.params:
            return json.loads(self.params)
        return {}

########NEW FILE########
__FILENAME__ = settings
"""Default settings for the calendarium app."""
from django.conf import settings


SHIFT_WEEKSTART = getattr(settings, 'CALENDARIUM_SHIFT_WEEKSTART', 0)

########NEW FILE########
__FILENAME__ = calendarium_tags
"""Templatetags for the ``calendarium`` project."""
from django.core.urlresolvers import reverse
from django import template
from django.utils.timezone import datetime, now, timedelta, utc

from ..models import Event, EventCategory

register = template.Library()


@register.filter
def get_week_URL(date, day=0):
    """
    Returns the week view URL for a given date.

    :param date: A date instance.
    :param day: Day number in a month.

    """
    if day < 1:
        day = 1
    date = datetime(year=date.year, month=date.month, day=day, tzinfo=utc)
    return reverse('calendar_week', kwargs={'year': date.isocalendar()[0],
                                            'week': date.isocalendar()[1]})


def _get_upcoming_events(amount=5, category=None):
    if not isinstance(category, EventCategory):
        category = None
    return Event.objects.get_occurrences(
        now(), now() + timedelta(days=356), category)[:amount]


@register.inclusion_tag('calendarium/upcoming_events.html')
def render_upcoming_events(event_amount=5, category=None):
    """Template tag to render a list of upcoming events."""
    return {
        'occurrences': _get_upcoming_events(
            amount=event_amount, category=category),
    }


@register.assignment_tag
def get_upcoming_events(amount=5, category=None):
    """Returns a list of upcoming events."""
    return _get_upcoming_events(amount=amount, category=category)

########NEW FILE########
__FILENAME__ = factories
"""Factories for the models of the ``calendarium`` app."""
import factory

from django.contrib.auth.models import Group, Permission
from django.utils.timezone import timedelta

from calendarium.models import (
    Event,
    EventCategory,
    EventRelation,
    Occurrence,
    Rule,
)
from calendarium.tests.test_app.models import DummyModelFactory
from calendarium.utils import now


class GroupFactory(factory.DjangoModelFactory):
    FACTORY_FOR = Group

    name = factory.Sequence(lambda n: 'Test Group %s' % n)

    @classmethod
    def _prepare(cls, create, **kwargs):
        group = super(GroupFactory, cls)._prepare(create, **kwargs)
        group.permissions.add(Permission.objects.get(
            codename='add_event', content_type__name='event'))
        return group


class EventCategoryFactory(factory.DjangoModelFactory):
    """Factory for the ``EventCategory`` model."""
    FACTORY_FOR = EventCategory

    name = factory.Sequence(lambda n: 'category{0}'.format(n))
    color = factory.Sequence(lambda n: 'col{0}'.format(n))


class EventFactoryMixin(factory.DjangoModelFactory):
    """Mixin for the event models."""
    FACTORY_FOR = None

    start = now()
    end = now() + timedelta(hours=1)
    title = factory.Sequence(lambda n: 'title{0}'.format(n))
    description = factory.Sequence(lambda n: 'description{0}'.format(n))
    creation_date = now()


class RuleFactory(factory.DjangoModelFactory):
    """Factory for the ``Rule`` model."""
    FACTORY_FOR = Rule

    name = factory.Sequence(lambda n: 'rule{0}'.format(n))
    description = factory.Sequence(lambda n: 'description{0}'.format(n))
    # standard is set to DAILY
    frequency = 'DAILY'
    # params are only needed for more precise rules, empty params are allowed
    params = ''


class EventFactory(EventFactoryMixin):
    """
    Factory for the ``Event`` model.

    If you set rule=None on creation, you get an event that occurs only once.
    Otherwise it defaults to an event with a DAILY rule over one week.

    """
    FACTORY_FOR = Event

    category = factory.SubFactory(EventCategoryFactory)
    rule = factory.SubFactory(RuleFactory)

    @factory.post_generation
    def set(self, create, extracted, **kwargs):
        """
        On initialization of the Factory one can pass following argument:

            'set__fieldname=value'

        where fieldname is the name of the field to set (e.g. start) and value
        is the time offset in hours to set.

        To set start 4 hours into the past you would pass the following:

            'set__start=-4'

        """
        self.creation_date = now() - timedelta(
            hours=kwargs.get('creation_date') or 0)
        self.start = now() + timedelta(hours=kwargs.get('start') or 0)
        if kwargs.get('end') is not None:
            self.end = now() + timedelta(hours=kwargs.get('end'))
        else:
            self.end = now() + timedelta(hours=1)
        # note that this defaults to seven, because the default rule is daily
        # for one week, so 6 days after the current
        if self.rule:
            self.end_recurring_period = now() + timedelta(
                days=kwargs.get('end_recurring_period') or 6)
        else:
            self.end_recurring_period = None
        if create:
            self.save()


class EventRelationFactory(factory.DjangoModelFactory):
    """Factory for the ``EventRelation`` model."""
    FACTORY_FOR = EventRelation

    event = factory.SubFactory(EventFactory)
    content_object = factory.SubFactory(DummyModelFactory)
    relation_type = factory.Sequence(lambda n: 'relation_type{0}'.format(n))


class EventRelation(EventRelationFactory):
    """Deprecated class name kept for backwards compatibility."""
    pass


class OccurrenceFactory(EventFactoryMixin):
    """Factory for the ``Occurrence`` model."""
    FACTORY_FOR = Occurrence

    event = factory.SubFactory(EventFactory)
    original_start = now()
    original_end = now() + timedelta(days=1)
    cancelled = False

    @factory.post_generation
    def set(self, create, extracted, **kwargs):
        """
        On initialization of the Factory one can pass following argument:

            'set__fieldname=value'

        where fieldname is the name of the field to set (e.g. start) and value
        is the time offset in hours to set.

        To set start 4 hours into the past you would pass the following:

            'set__start=-4'

        """
        self.creation_date = now() + timedelta(
            hours=kwargs.get('creation_date') or 0)
        self.start = now() + timedelta(
            hours=kwargs.get('start') or 0)
        self.end = now() + timedelta(
            hours=kwargs.get('end') or 0)
        self.original_start = now() + timedelta(
            hours=kwargs.get('original_start') or 0)
        if kwargs.get('original_end') is not None:
            self.original_end = now() + timedelta(hours=kwargs.get(
                'original_end'))
        else:
            self.original_end = now() + timedelta(hours=1)
        if create:
            self.save()

########NEW FILE########
__FILENAME__ = forms_tests
"""Tests for the forms of the ``calendarium`` app."""
import json

from django.forms.models import model_to_dict
from django.test import TestCase
from django.utils.timezone import timedelta

from django_libs.tests.factories import UserFactory

from calendarium.constants import FREQUENCIES, OCCURRENCE_DECISIONS
from calendarium.forms import OccurrenceForm
from calendarium.models import Event, Occurrence
from calendarium.tests.factories import EventFactory, RuleFactory
from calendarium.utils import now


class OccurrenceFormTestCase(TestCase):
    """Test for the ``OccurrenceForm`` form class."""
    longMessage = True

    def setUp(self):
        # single, not recurring event
        self.event = EventFactory(rule=None, end_recurring_period=None)
        self.event_occurrence = self.event.get_occurrences(
            self.event.start).next()

        # recurring event weekly on mondays over 6 weeks
        self.rule = RuleFactory(
            name='weekly', frequency=FREQUENCIES['WEEKLY'],
            params=json.dumps({'byweekday': 0}))
        self.rec_event = EventFactory(
            rule=self.rule, start=now(),
            set__end_recurring_period=41,
            created_by=UserFactory(),
        )
        self.rec_occurrence_list = [
            occ for occ in self.rec_event.get_occurrences(
                self.rec_event.start, self.rec_event.end_recurring_period)]
        self.rec_occurrence = self.rec_occurrence_list[1]

    def test_form(self):
        """Test if ``OccurrenceForm`` is valid and saves correctly."""
        # Test for not recurring event
        data = model_to_dict(self.event_occurrence)
        initial = data.copy()
        data.update({
            'decision': OCCURRENCE_DECISIONS['all'],
            'title': 'changed'})
        form = OccurrenceForm(data=data, initial=initial)
        self.assertTrue(form.is_valid(), msg=(
            'The OccurrenceForm should be valid'))
        form.save()
        event = Event.objects.get(pk=self.event.pk)
        self.assertEqual(event.title, 'changed', msg=(
            'When save is called, the event\'s title should be "changed".'))

        # Test for recurring event

        # Case 1: Altering occurrence 3 to be on a tuesday.
        data = model_to_dict(self.rec_occurrence)
        initial = data.copy()
        data.update({
            'decision': OCCURRENCE_DECISIONS['this one'],
            'title': 'different'})
        form = OccurrenceForm(data=data, initial=initial)
        self.assertTrue(form.is_valid(), msg=(
            'The OccurrenceForm should be valid'))
        form.save()
        self.assertEqual(Occurrence.objects.all().count(), 1, msg=(
            'After one occurrence has changed, there should be one persistent'
            ' occurrence.'))
        occ = Occurrence.objects.get()
        self.assertEqual(occ.title, 'different', msg=(
            'When save is called, the occurrence\'s title should be'
            ' "different".'))

        # Case 2: Altering the description of "all" on the first occurrence
        # should also change 3rd one
        occ_to_use = self.rec_occurrence_list[0]
        data = model_to_dict(occ_to_use)
        initial = data.copy()
        new_start = occ_to_use.start + timedelta(hours=1)
        data.update({
            'decision': OCCURRENCE_DECISIONS['all'],
            'description': 'has changed',
            'start': new_start})
        form = OccurrenceForm(data=data, initial=initial)
        self.assertTrue(form.is_valid(), msg=(
            'The OccurrenceForm should be valid'))
        form.save()
        self.assertEqual(Occurrence.objects.all().count(), 1, msg=(
            'After one occurrence has changed, there should be one persistent'
            ' occurrence.'))
        occ = Occurrence.objects.get()
        self.assertEqual(occ.title, 'different', msg=(
            'When save is called, the occurrence\'s title should still be'
            ' "different".'))
        self.assertEqual(occ.description, 'has changed', msg=(
            'When save is called, the occurrence\'s description should be'
            ' "has changed".'))
        self.assertEqual(
            occ.start, self.rec_occurrence.start + timedelta(hours=1), msg=(
                'When save is called, the occurrence\'s start time should be'
                ' set forward one hour.'))

        # Case 3: Altering everthing from occurrence 4 to 6 to one day later
        occ_to_use = self.rec_occurrence_list[4]
        data = model_to_dict(occ_to_use)
        initial = data.copy()
        new_start = occ_to_use.start - timedelta(days=1)
        data.update({
            'decision': OCCURRENCE_DECISIONS['following'],
            'start': new_start})
        form = OccurrenceForm(data=data, initial=initial)
        self.assertTrue(form.is_valid(), msg=(
            'The OccurrenceForm should be valid'))
        form.save()
        self.assertEqual(Event.objects.all().count(), 3, msg=(
            'After changing occurrence 4-6, a new event should have been'
            ' created.'))
        event1 = Event.objects.get(pk=self.rec_event.pk)
        event2 = Event.objects.exclude(
            pk__in=[self.rec_event.pk, self.event.pk]).get()
        self.assertEqual(
            event1.end_recurring_period,
            event2.start - timedelta(days=1), msg=(
                'The end recurring period of the old event should be the same'
                ' as the start of the new event minus one day.'))
        self.assertEqual(
            event2.end_recurring_period, self.rec_event.end_recurring_period,
            msg=(
                'The end recurring period of the new event should be the'
                ' old end recurring period of the old event.'))
        # -> should yield 2 events, one newly created one altered

########NEW FILE########
__FILENAME__ = views_tests
"""Tests for the views of the ``calendarium`` app."""
# ! Never use the timezone now, import calendarium.utils.now instead always
# inaccuracy on microsecond base can negatively influence your tests
# from django.utils.timezone import now
from django.utils.timezone import timedelta
from django.test import TestCase

from django_libs.tests.factories import UserFactory
from django_libs.tests.mixins import ViewTestMixin

from calendarium.models import Event
from ..factories import (
    EventFactory,
    EventCategoryFactory,
    GroupFactory,
    RuleFactory,
)
from calendarium.utils import now


class CalendariumRedirectViewTestCase(ViewTestMixin, TestCase):
    """Tests for the ``CalendariumRedirectView`` view."""
    longMessage = True

    def get_view_name(self):
        return 'calendar_current_month'

    def test_view(self):
        resp = self.client.get(self.get_url())
        self.assertEqual(resp.status_code, 301)


class MonthViewTestCase(ViewTestMixin, TestCase):
    """Tests for the ``MonthView`` view class."""
    longMessage = True

    def get_view_name(self):
        return 'calendar_month'

    def get_view_kwargs(self):
        return {'year': self.year, 'month': self.month}

    def setUp(self):
        self.year = now().year
        self.month = now().month

    def test_view(self):
        """Test for the ``MonthView`` view class."""
        # regular call
        resp = self.is_callable()
        self.assertEqual(
            resp.template_name[0], 'calendarium/calendar_month.html', msg=(
                'Returned the wrong template.'))
        self.is_callable(method='POST', data={'next': True})
        self.is_callable(method='POST', data={'previous': True})
        self.is_callable(method='POST', data={'today': True})

        # AJAX call
        resp = self.client.get(
            self.get_url(), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(
            resp.template_name[0], 'calendarium/partials/calendar_month.html',
            msg=('Returned the wrong template for AJAX request.'))

        # called with a invalid category pk
        resp = self.client.get('{0}?category=abc'.format(self.get_url()))
        self.assertEqual(resp.status_code, 200)

        # called with a non-existant category pk
        resp = self.client.get('{0}?category=999'.format(self.get_url()))
        self.assertEqual(resp.status_code, 200)

        # called with a category pk
        category = EventCategoryFactory()
        resp = self.client.get('{0}?category={1}'.format(self.get_url(),
                                                         category.id))
        self.assertEqual(resp.status_code, 200)

        # called with wrong values
        self.is_not_callable(kwargs={'year': 2000, 'month': 15})


class WeekViewTestCase(ViewTestMixin, TestCase):
    """Tests for the ``WeekView`` view class."""
    longMessage = True

    def get_view_name(self):
        return 'calendar_week'

    def get_view_kwargs(self):
        return {'year': self.year, 'week': self.week}

    def setUp(self):
        self.year = now().year
        # current week number
        self.week = now().date().isocalendar()[1]

    def test_view(self):
        """Tests for the ``WeekView`` view class."""
        resp = self.is_callable()
        self.assertEqual(
            resp.template_name[0], 'calendarium/calendar_week.html', msg=(
                'Returned the wrong template.'))
        self.is_callable(method='POST', data={'next': True})
        self.is_callable(method='POST', data={'previous': True})
        self.is_callable(method='POST', data={'today': True})

        resp = self.client.get(
            self.get_url(), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(
            resp.template_name[0], 'calendarium/partials/calendar_week.html',
            msg=('Returned the wrong template for AJAX request.'))
        self.is_not_callable(kwargs={'year': self.year, 'week': '60'})


class DayViewTestCase(ViewTestMixin, TestCase):
    """Tests for the ``DayView`` view class."""
    longMessage = True

    def get_view_name(self):
        return 'calendar_day'

    def get_view_kwargs(self):
        return {'year': self.year, 'month': self.month, 'day': self.day}

    def setUp(self):
        self.year = 2001
        self.month = 2
        self.day = 15

    def test_view(self):
        """Tests for the ``DayView`` view class."""
        resp = self.is_callable()
        self.assertEqual(
            resp.template_name[0], 'calendarium/calendar_day.html', msg=(
                'Returned the wrong template.'))
        self.is_callable(method='POST', data={'next': True})
        self.is_callable(method='POST', data={'previous': True})
        self.is_callable(method='POST', data={'today': True})

        resp = self.client.get(
            self.get_url(), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(
            resp.template_name[0], 'calendarium/partials/calendar_day.html',
            msg=('Returned the wrong template for AJAX request.'))
        self.is_not_callable(kwargs={'year': self.year, 'month': '14',
                                     'day': self.day})


class EventUpdateViewTestCase(ViewTestMixin, TestCase):
    """Tests for the ``EventUpdateView`` view class."""
    longMessage = True

    def get_view_name(self):
        return 'calendar_event_update'

    def get_view_kwargs(self):
        return {'pk': self.event.pk}

    def setUp(self):
        self.event = EventFactory()
        self.user = UserFactory()
        self.group = GroupFactory()
        self.user.groups.add(self.group)

    def test_view(self):
        self.should_be_callable_when_authenticated(self.user)


class EventCreateViewTestCase(ViewTestMixin, TestCase):
    """Tests for the ``EventCreateView`` view class."""
    longMessage = True

    def get_view_name(self):
        return 'calendar_event_create'

    def setUp(self):
        self.user = UserFactory()
        self.group = GroupFactory()
        self.user.groups.add(self.group)

    def test_view(self):
        self.should_be_callable_when_authenticated(self.user)
        self.is_callable(data={'delete': True})
        self.assertEqual(Event.objects.all().count(), 0)


class EventDetailViewTestCase(ViewTestMixin, TestCase):
    """Tests for the ``EventDetailView`` view class."""
    longMessage = True

    def get_view_name(self):
        return 'calendar_event_detail'

    def get_view_kwargs(self):
        return {'pk': self.event.pk}

    def setUp(self):
        self.event = EventFactory()

    def test_view(self):
        self.is_callable()


class OccurrenceViewTestCaseMixin(object):
    """Mixin to avoid repeating code for the Occurrence views."""
    longMessage = True

    def get_view_kwargs(self):
        return {
            'pk': self.event.pk,
            'year': self.event.start.date().year,
            'month': self.event.start.date().month,
            'day': self.event.start.date().day,
        }

    def setUp(self):
        self.rule = RuleFactory(name='daily')
        self.start = now() - timedelta(days=1)
        self.end = now() + timedelta(days=5)
        self.event = EventFactory(
            rule=self.rule, end_recurring_period=now() + timedelta(days=2))

    def test_view(self):
        # regular test with a valid request
        self.is_callable()


class OccurrenceDeleteViewTestCase(
        OccurrenceViewTestCaseMixin, ViewTestMixin, TestCase):
    """Tests for the ``OccurrenceDeleteView`` view class."""
    def get_view_name(self):
        return 'calendar_occurrence_delete'

    def test_deletion(self):
        self.is_callable(method='post')

        self.is_callable(kwargs={
            'pk': self.event.pk,
            'year': self.event.start.date().year,
            'month': self.event.start.date().month,
            'day': self.event.start.date().day + 1,
        }, message=('Should be callable, if date in period.'))

        self.is_not_callable(kwargs={
            'pk': 5,
            'year': self.event.start.date().year,
            'month': self.event.start.date().month,
            'day': self.event.start.date().day,
        }, message=('Wrong event pk.'))

        self.is_not_callable(kwargs={
            'pk': self.event.pk,
            'year': self.event.start.date().year,
            'month': '999',
            'day': self.event.start.date().day,
        }, message=('Wrong dates.'))

        new_rule = RuleFactory(name='weekly', frequency='WEEKLY')
        new_event = EventFactory(
            rule=new_rule,
            end_recurring_period=now() + timedelta(days=200),
            set__start=-5,
        )
        test_date = self.event.start.date() - timedelta(days=5)
        self.is_not_callable(kwargs={
            'pk': new_event.pk,
            'year': test_date.year,
            'month': test_date.month,
            'day': test_date.day,
        }, message=('No occurrence available for this day.'))


class OccurrenceDetailViewTestCase(
        OccurrenceViewTestCaseMixin, ViewTestMixin, TestCase):
    """Tests for the ``OccurrenceDetailView`` view class."""
    def get_view_name(self):
        return 'calendar_occurrence_detail'


class OccurrenceUpdateViewTestCase(
        OccurrenceViewTestCaseMixin, ViewTestMixin, TestCase):
    """Tests for the ``OccurrenceUpdateView`` view class."""
    def get_view_name(self):
        return 'calendar_occurrence_update'


class UpcomingEventsAjaxViewTestCase(ViewTestMixin, TestCase):
    """Tests for the ``UpcomingEventsAjaxView`` view class."""
    def get_view_name(self):
        return 'calendar_upcoming_events'

    def test_view(self):
        self.should_be_callable_when_anonymous()

    def test_view_with_count(self):
        url = self.get_url()
        url = url + '?count=5'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_view_with_category(self):
        cat = EventCategoryFactory()
        url = self.get_url()
        url = url + '?category={0}'.format(cat.slug)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

########NEW FILE########
__FILENAME__ = models_tests
"""Tests for the models of the ``calendarium`` app."""
from django.test import TestCase
from django.utils.timezone import timedelta

from calendarium.models import (
    EventCategory,
    Occurrence,
    Rule,
)
from calendarium.models import Event, ColorField
from calendarium.tests.factories import (
    EventCategoryFactory,
    EventFactory,
    EventRelationFactory,
    OccurrenceFactory,
)
from calendarium.utils import now
from calendarium.widgets import ColorPickerWidget


class EventModelManagerTestCase(TestCase):
    """Tests for the ``EventModelManager`` custom manager."""
    longMessage = True

    def setUp(self):
        # event that only occurs once
        self.event = EventFactory(rule=None)
        # event that occurs for one week daily with one custom occurrence
        self.event_daily = EventFactory()
        self.occurrence = OccurrenceFactory(
            event=self.event, title='foo_occurrence')

    def test_get_occurrences(self):
        """Test for the ``get_occurrences`` manager method."""
        occurrences = Event.objects.get_occurrences(
            now(), now() + timedelta(days=7))
        self.assertEqual(len(occurrences), 8, msg=(
            '``get_occurrences`` should return the correct amount of'
            ' occurrences.'))

        occurrences = Event.objects.get_occurrences(now(), now())
        self.assertEqual(len(occurrences), 2, msg=(
            '``get_occurrences`` should return the correct amount of'
            ' occurrences for one day.'))


class EventTestCase(TestCase):
    """Tests for the ``Event`` model."""
    longMessage = True

    def setUp(self):
        self.not_found_event = EventFactory(
            set__start=-24, set__end=-24, set__creation_date=-24,
            rule=None)
        self.event = EventFactory()
        self.occurrence = OccurrenceFactory(
            event=self.event, title='foo_occurrence')
        self.single_time_event = EventFactory(rule=None)

    def test_create_occurrence(self):
        """Test for ``_create_occurrence`` method."""
        occurrence = self.event._create_occurrence(now())
        self.assertEqual(type(occurrence), Occurrence, msg=(
            'Method ``_create_occurrence`` did not output the right type.'))

    def test_get_occurrence_gen(self):
        """Test for the ``_get_occurrence_gen`` method"""
        occurrence_gen = self.event._get_occurrence_gen(
            now(), now() + timedelta(days=8))
        occ_list = [occ for occ in occurrence_gen]
        self.assertEqual(len(occ_list), 7, msg=(
            'The method ``_get_occurrence_list`` did not return the expected'
            ' amount of items.'))

        occurrence_gen = self.not_found_event._get_occurrence_gen(
            now(), now() + timedelta(days=8))
        occ_list = [occ for occ in occurrence_gen]
        self.assertEqual(len(occ_list), 0, msg=(
            'The method ``_get_occurrence_list`` did not return the expected'
            ' amount of items.'))

    def test_get_occurrences(self):
        occurrence_gen = self.event.get_occurrences(
            now(), now() + timedelta(days=7))
        occ_list = [occ for occ in occurrence_gen]
        self.assertEqual(len(occ_list), 7, msg=(
            'Method ``get_occurrences`` did not output the correct amount'
            ' of occurrences.'))
        occurrence_gen = self.event.get_occurrences(
            now(), now() + timedelta(days=7))
        self.assertEqual(occurrence_gen.next().title, 'foo_occurrence', msg=(
            'The persistent occurrence should have been first in the list.'))

    def test_get_parent_category(self):
        """Tests for the ``get_parent_category`` method."""
        result = self.event.get_parent_category()
        self.assertEqual(result, self.event.category, msg=(
            "If the event's category has no parent, it should return the"
            " category"))

        cat2 = EventCategoryFactory()
        self.event.category.parent = cat2
        self.event.save()
        result = self.event.get_parent_category()
        self.assertEqual(result, self.event.category.parent, msg=(
            "If the event's category has a parent, it should return that"
            " parent"))

    def test_save_autocorrection(self):
        event = EventFactory(rule=None)
        event.end = event.end - timedelta(hours=2)
        event.save()
        self.assertEqual(event.start, event.end)


class EventCategoryTestCase(TestCase):
    """Tests for the ``EventCategory`` model."""
    longMessage = True

    def test_instantiation(self):
        """Test for instantiation of the ``EventCategory`` model."""
        event_category = EventCategory()
        self.assertTrue(event_category)


class ColorFieldTestCase(TestCase):
    """Tests for the ``ColorField`` model."""
    longMessage = True

    def test_functions(self):
        color_field = ColorField()
        color_field.formfield
        self.assertIsInstance(
            color_field.formfield().widget, ColorPickerWidget, msg=(
                'Should add the color field widget.'))


class EventRelationTestCase(TestCase):
    """Tests for the ``EventRelation`` model."""
    longMessage = True

    def test_instantiation(self):
        """Test for instantiation of the ``EventRelation`` model."""
        event_relation = EventRelationFactory()
        self.assertTrue(event_relation)


class OccurrenceTestCase(TestCase):
    """Tests for the ``Occurrence`` model."""
    longMessage = True

    def test_instantiation(self):
        """Test for instantiation of the ``Occurrence`` model."""
        occurrence = Occurrence()
        self.assertTrue(occurrence)

    def test_delete_period(self):
        """Test for the ``delete_period`` function."""
        occurrence = OccurrenceFactory()
        occurrence.delete_period('all')
        self.assertEqual(Occurrence.objects.all().count(), 0, msg=(
            'Should delete only the first occurrence.'))

        event = EventFactory(set__start=0, set__end=0)
        occurrence = OccurrenceFactory(event=event, set__start=0, set__end=0)
        occurrence.delete_period('this one')
        self.assertEqual(Occurrence.objects.all().count(), 0, msg=(
            'Should delete only the first occurrence.'))

        event = EventFactory(set__start=0, set__end=0)
        occurrence = OccurrenceFactory(event=event, set__start=0, set__end=0)
        occurrence.delete_period('following')
        self.assertEqual(Event.objects.all().count(), 0, msg=(
            'Should delete the event and the occurrence.'))

        occurrence_1 = OccurrenceFactory()
        occurrence_2 = OccurrenceFactory(event=occurrence_1.event)
        period = occurrence_2.event.end_recurring_period
        occurrence_2.delete_period('this one')
        # Result is equal instead of greater. Needs to be fixed.
        # self.assertGreater(period, occurrence_2.event.end_recurring_period,
        #                    msg=('Should shorten event period, if last'
        #                         ' occurencce is deleted.'))

        occurrence_2 = OccurrenceFactory(event=occurrence_1.event)
        occurrence_3 = OccurrenceFactory(event=occurrence_1.event)
        occurrence_2.delete_period('this one')
        self.assertTrue(Occurrence.objects.get(pk=occurrence_2.pk).cancelled,
                        msg=('Should set the occurrence to cancelled.'))

        occurrence_3.delete_period('following')
        self.assertEqual(Occurrence.objects.all().count(), 0, msg=(
            'Should delete all occurrences with this start date.'))


class RuleTestCase(TestCase):
    """Tests for the ``Rule`` model."""
    longMessage = True

    def test_instantiation(self):
        """Test for instantiation of the ``Rule`` model."""
        rule = Rule()
        self.assertTrue(rule)

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
"""
This script is a trick to setup a fake Django environment, since this reusable
app will be developed and tested outside any specifiv Django project.

Via ``settings.configure`` you will be able to set all necessary settings
for your app and run the tests as if you were calling ``./manage.py test``.

"""
import sys

from django.conf import settings
import test_settings


if not settings.configured:
    settings.configure(**test_settings.__dict__)


from django_coverage.coverage_runner import CoverageRunner
from django_nose import NoseTestSuiteRunner


class NoseCoverageTestRunner(CoverageRunner, NoseTestSuiteRunner):
    """Custom test runner that uses nose and coverage"""
    pass


def runtests(*test_args):
    failures = NoseCoverageTestRunner(verbosity=2, interactive=True).run_tests(
        test_args)
    sys.exit(failures)


if __name__ == '__main__':
    runtests(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = south_settings
"""
These settings are used by the ``manage.py`` command.

With normal tests we want to use the fastest possible way which is an
in-memory sqlite database but if you want to create South migrations you
need a persistant database.

Unfortunately there seems to be an issue with either South or syncdb so that
defining two routers ("default" and "south") does not work.

"""
from calendarium.tests.test_settings import *  # NOQA


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite',
    }
}

INSTALLED_APPS.append('south', )

########NEW FILE########
__FILENAME__ = tags_tests
"""Tests for the template tags of the ``calendarium`` app."""
from django.template import Context, Template
from django.test import TestCase
from django.utils import timezone

from .factories import OccurrenceFactory
from calendarium.templatetags.calendarium_tags import get_upcoming_events


class RenderUpcomingEventsTestCase(TestCase):
    """Tests for the ``render_upcoming_events`` tag."""
    longMessage = True

    def setUp(self):
        self.occurrence = OccurrenceFactory(
            original_start=timezone.now() + timezone.timedelta(seconds=20))

    def test_render_tag(self):
        t = Template('{% load calendarium_tags %}{% render_upcoming_events %}')
        self.assertIn('{0}'.format(self.occurrence.title), t.render(Context()))


class GetUpcomingEventsTestCase(TestCase):
    """Tests for the ``get_upcoming_ecents`` tag."""
    longMessage = True

    def setUp(self):
        self.occurrence = OccurrenceFactory(
            original_start=timezone.now() + timezone.timedelta(seconds=20))

    def test_tag(self):
        result = get_upcoming_events()
        self.assertEqual(len(result), 5)

########NEW FILE########
__FILENAME__ = 0001_initial
# flake8: noqa
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'DummyModel'
        db.create_table('test_app_dummymodel', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('content', self.gf('django.db.models.fields.CharField')(max_length=32)),
        ))
        db.send_create_signal('test_app', ['DummyModel'])


    def backwards(self, orm):
        # Deleting model 'DummyModel'
        db.delete_table('test_app_dummymodel')


    models = {
        'test_app.dummymodel': {
            'Meta': {'object_name': 'DummyModel'},
            'content': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['test_app']
########NEW FILE########
__FILENAME__ = models
"""Models for the ``test_app`` test app."""
import factory

from django.db import models


class DummyModel(models.Model):
    """
    This is a dummy model for testing purposes.

    :content: Just a dummy field.

    """
    content = models.CharField(
        max_length=32,
    )


class DummyModelFactory(factory.DjangoModelFactory):
    """Factory for the ``DummyModel`` model."""
    FACTORY_FOR = DummyModel

    content = factory.Sequence(lambda n: 'content{0}'.format(n))

########NEW FILE########
__FILENAME__ = test_settings
"""Settings that need to be set in order to run the tests."""
import os

DEBUG = True
USE_TZ = True
TIME_ZONE = 'Asia/Singapore'

AUTH_USER_MODEL = 'auth.User'

SITE_ID = 1

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

ROOT_URLCONF = 'calendarium.tests.urls'

STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(__file__, '../../static/')

STATICFILES_DIRS = (
    os.path.join(__file__, 'test_static'),
)

TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(__file__), '../templates'),
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.request',
)

COVERAGE_REPORT_HTML_OUTPUT_DIR = os.path.join(
    os.path.dirname(__file__), 'coverage')

COVERAGE_MODULE_EXCLUDES = [
    'tests$', 'settings$', 'urls$', 'locale$',
    'migrations', 'fixtures', 'admin$', 'django_extensions',
]

EXTERNAL_APPS = [
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'django.contrib.sites',
    'django_nose',
    'filer',
]

INTERNAL_APPS = [
    'calendarium',
]

TEST_APPS = [
    'calendarium.tests.test_app',
]

INSTALLED_APPS = EXTERNAL_APPS + INTERNAL_APPS + TEST_APPS

COVERAGE_MODULE_EXCLUDES += EXTERNAL_APPS

########NEW FILE########
__FILENAME__ = urls
"""
This ``urls.py`` is only used when running the tests via ``runtests.py``.
As you know, every app must be hooked into yout main ``urls.py`` so that
you can actually reach the app's views (provided it has any views, of course).

"""
from django.conf.urls import include, patterns, url
from django.contrib import admin


admin.autodiscover()


urlpatterns = patterns(
    '',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^', include('calendarium.urls')),
)

########NEW FILE########
__FILENAME__ = widget_tests
"""Tests for the widgets of the ``calendarium`` app."""
from django.test import TestCase

from ..widgets import ColorPickerWidget


class ColorPickerWidgetTestCase(TestCase):
    """Tests for the ``ColorPickerWidget`` widget."""
    longMessage = True

    def setUp(self):
        self.widget = ColorPickerWidget()

    def test_render_tag(self):
        self.assertIn('value="ffffff"', self.widget.render('field', 'ffffff'),
                      msg=('Should render the input form.'))

########NEW FILE########
__FILENAME__ = urls
"""URLs for the ``calendarium`` app."""
from django.conf.urls import patterns, url

from calendarium.views import (
    CalendariumRedirectView,
    DayView,
    EventCreateView,
    EventDeleteView,
    EventDetailView,
    EventUpdateView,
    MonthView,
    OccurrenceDeleteView,
    OccurrenceDetailView,
    OccurrenceUpdateView,
    UpcomingEventsAjaxView,
    WeekView,
)


urlpatterns = patterns(
    '',
    # event views
    url(r'^event/create/$',
        EventCreateView.as_view(),
        name='calendar_event_create'),

    url(r'^event/(?P<pk>\d+)/$',
        EventDetailView.as_view(),
        name='calendar_event_detail'),

    url(r'^event/(?P<pk>\d+)/update/$',
        EventUpdateView.as_view(),
        name='calendar_event_update'),

    url(r'^event/(?P<pk>\d+)/delete/$',
        EventDeleteView.as_view(),
        name='calendar_event_delete'),

    # occurrence views
    url(r'^event/(?P<pk>\d+)/date/(?P<year>\d+)/(?P<month>\d+)/(?P<day>\d+)/$',
        OccurrenceDetailView.as_view(),
        name='calendar_occurrence_detail'),

    url(
        r'^event/(?P<pk>\d+)/date/(?P<year>\d+)/(?P<month>\d+)/(?P<day>\d+)/update/$',  # NOPEP8
        OccurrenceUpdateView.as_view(),
        name='calendar_occurrence_update'),

    url(
        r'^event/(?P<pk>\d+)/date/(?P<year>\d+)/(?P<month>\d+)/(?P<day>\d+)/delete/$',  # NOPEP8
        OccurrenceDeleteView.as_view(),
        name='calendar_occurrence_delete'),

    # calendar views
    url(r'^(?P<year>\d+)/(?P<month>\d+)/$',
        MonthView.as_view(),
        name='calendar_month'),

    url(r'^(?P<year>\d+)/week/(?P<week>\d+)/$',
        WeekView.as_view(),
        name='calendar_week'),

    url(r'^(?P<year>\d+)/(?P<month>\d+)/(?P<day>\d+)/$',
        DayView.as_view(),
        name='calendar_day'),

    url(r'^get-events/$',
        UpcomingEventsAjaxView.as_view(),
        name='calendar_upcoming_events'),

    url(r'^$',
        CalendariumRedirectView.as_view(),
        name='calendar_current_month'),

)

########NEW FILE########
__FILENAME__ = utils
"""
Utils for the ``calendarium`` app.

The code of these utils is highly influenced by or taken from the utils of
django-schedule:

https://github.com/thauber/django-schedule/blob/master/schedule/utils.py


"""
import time
from django.utils import timezone


def now(**kwargs):
    """
    Utility function to zero microseconds to avoid inaccuracy.

    I replaced the microseconds, because there is some slightly varying
    difference that occurs out of unknown reason. Since we probably never
    schedule events on microsecond basis, seconds and microseconds will be
    zeroed everywhere.

    """
    return timezone.now(**kwargs).replace(second=0, microsecond=0)


def monday_of_week(year, week):
    """
    Returns a datetime for the monday of the given week of the given year.

    """
    str_time = time.strptime('{0} {1} 1'.format(year, week), '%Y %W %w')
    date = timezone.datetime(year=str_time.tm_year, month=str_time.tm_mon,
                             day=str_time.tm_mday, tzinfo=timezone.utc)
    if timezone.datetime(year, 1, 4).isoweekday() > 4:
        # ISO 8601 where week 1 is the first week that has at least 4 days in
        # the current year
        date -= timezone.timedelta(days=7)
    return date


class OccurrenceReplacer(object):
    """
    When getting a list of occurrences, the last thing that needs to be done
    before passing it forward is to make sure all of the occurrences that
    have been stored in the datebase replace, in the list you are returning,
    the generated ones that are equivalent.  This class makes this easier.

    """
    def __init__(self, persisted_occurrences):
        lookup = [
            ((occ.event, occ.original_start, occ.original_end), occ) for
            occ in persisted_occurrences]
        self.lookup = dict(lookup)

    def get_occurrence(self, occ):
        """
        Return a persisted occurrences matching the occ and remove it from
        lookup since it has already been matched
        """
        return self.lookup.pop(
            (occ.event, occ.original_start, occ.original_end),
            occ)

    def has_occurrence(self, occ):
        return (occ.event, occ.original_start, occ.original_end) in self.lookup

    def get_additional_occurrences(self, start, end):
        """
        Return persisted occurrences which are now in the period
        """
        return [occ for key, occ in self.lookup.items() if (
            (end and occ.start < end)
            and occ.end >= start and not occ.cancelled)]

########NEW FILE########
__FILENAME__ = views
"""Views for the ``calendarium`` app."""
import calendar
from dateutil.relativedelta import relativedelta

from django.contrib.auth.decorators import permission_required
from django.core.urlresolvers import reverse
from django.forms.models import model_to_dict
from django.http import Http404, HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.utils.timezone import datetime, now, timedelta, utc
from django.utils.translation import ugettext_lazy as _
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    RedirectView,
    TemplateView,
    UpdateView,
)

from .constants import OCCURRENCE_DECISIONS
from .forms import OccurrenceForm
from .models import EventCategory, Event, Occurrence
from .settings import SHIFT_WEEKSTART
from .utils import monday_of_week


class CategoryMixin(object):
    """Mixin to handle category filtering by category id."""
    def dispatch(self, request, *args, **kwargs):
        if hasattr(self, 'category'):
            # If we already have a category on the class, then we probably
            # already went through the CategorySlugMixin
            return super(CategoryMixin, self).dispatch(
                request, *args, **kwargs)

        if request.GET.get('category'):
            try:
                category_id = int(request.GET.get('category'))
            except ValueError:
                pass
            else:
                try:
                    self.category = EventCategory.objects.get(pk=category_id)
                except EventCategory.DoesNotExist:
                    pass
        return super(CategoryMixin, self).dispatch(request, *args, **kwargs)

    def get_category_context(self, **kwargs):
        context = {'categories': EventCategory.objects.all()}
        if hasattr(self, 'category'):
            context.update({'current_category': self.category})
        return context


class CategorySlugMixin(CategoryMixin):
    """Mixin to handle category filtering by category slug."""
    def dispatch(self, request, *args, **kwargs):
        if request.GET.get('category'):
            try:
                self.category = EventCategory.objects.get(
                    slug=request.GET.get('category'))
            except EventCategory.DoesNotExist:
                pass
        return super(CategorySlugMixin, self).dispatch(
            request, *args, **kwargs)


class CalendariumRedirectView(RedirectView):
    """View to redirect to the current month view."""
    def get_redirect_url(self, **kwargs):
        return reverse('calendar_month', kwargs={'year': now().year,
                                                 'month': now().month})


class MonthView(CategoryMixin, TemplateView):
    """View to return all occurrences of an event for a whole month."""
    template_name = 'calendarium/calendar_month.html'

    def dispatch(self, request, *args, **kwargs):
        self.month = int(kwargs.get('month'))
        self.year = int(kwargs.get('year'))
        if self.month not in range(1, 13):
            raise Http404
        if request.method == 'POST':
            if request.POST.get('next'):
                new_date = datetime(self.year, self.month, 1) + timedelta(
                    days=31)
                return HttpResponseRedirect(reverse('calendar_month', kwargs={
                    'year': new_date.year, 'month': new_date.month}))
            elif request.POST.get('previous'):
                new_date = datetime(self.year, self.month, 1) - timedelta(
                    days=1)
                return HttpResponseRedirect(reverse('calendar_month', kwargs={
                    'year': new_date.year, 'month': new_date.month}))
            elif request.POST.get('today'):
                return HttpResponseRedirect(reverse('calendar_month', kwargs={
                    'year': now().year, 'month': now().month}))
        if request.is_ajax():
            self.template_name = 'calendarium/partials/calendar_month.html'
        return super(MonthView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        firstweekday = 0 + SHIFT_WEEKSTART
        while firstweekday < 0:
            firstweekday += 7
        while firstweekday > 6:
            firstweekday -= 7

        ctx = self.get_category_context()
        month = [[]]
        week = 0
        start = datetime(year=self.year, month=self.month, day=1, tzinfo=utc)
        end = datetime(
            year=self.year, month=self.month, day=1, tzinfo=utc
        ) + relativedelta(months=1)

        all_occurrences = Event.objects.get_occurrences(
            start, end, ctx.get('current_category'))
        cal = calendar.Calendar()
        cal.setfirstweekday(firstweekday)
        for day in cal.itermonthdays(self.year, self.month):
            current = False
            if day:
                date = datetime(year=self.year, month=self.month, day=day,
                                tzinfo=utc)
                occurrences = filter(
                    lambda occ, date=date: occ.start.replace(
                        hour=0, minute=0, second=0, microsecond=0) == date,
                    all_occurrences)
                if date.date() == now().date():
                    current = True
            else:
                occurrences = []
            month[week].append((day, occurrences, current))
            if len(month[week]) == 7:
                month.append([])
                week += 1
        calendar.setfirstweekday(firstweekday)
        weekdays = [_(header) for header in calendar.weekheader(10).split()]
        ctx.update({'month': month, 'date': date, 'weekdays': weekdays})
        return ctx


class WeekView(CategoryMixin, TemplateView):
    """View to return all occurrences of an event for one week."""
    template_name = 'calendarium/calendar_week.html'

    def dispatch(self, request, *args, **kwargs):
        self.week = int(kwargs.get('week'))
        self.year = int(kwargs.get('year'))
        if self.week not in range(1, 53):
            raise Http404
        if request.method == 'POST':
            if request.POST.get('next'):
                date = monday_of_week(self.year, self.week) + timedelta(days=7)
                return HttpResponseRedirect(reverse('calendar_week', kwargs={
                    'year': date.year, 'week': date.date().isocalendar()[1]}))
            elif request.POST.get('previous'):
                date = monday_of_week(self.year, self.week) - timedelta(days=7)
                return HttpResponseRedirect(reverse('calendar_week', kwargs={
                    'year': date.year, 'week': date.date().isocalendar()[1]}))
            elif request.POST.get('today'):
                return HttpResponseRedirect(reverse('calendar_week', kwargs={
                    'year': now().year,
                    'week': now().date().isocalendar()[1]}))
        if request.is_ajax():
            self.template_name = 'calendarium/partials/calendar_week.html'
        return super(WeekView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = self.get_category_context()
        date = monday_of_week(self.year, self.week) + relativedelta(
            days=SHIFT_WEEKSTART)
        week = []
        day = SHIFT_WEEKSTART
        start = date
        end = date + relativedelta(days=7 + SHIFT_WEEKSTART)
        all_occurrences = Event.objects.get_occurrences(
            start, end, ctx.get('current_category'))
        while day < 7 + SHIFT_WEEKSTART:
            current = False
            occurrences = filter(
                lambda occ, date=date: occ.start.replace(
                    hour=0, minute=0, second=0, microsecond=0) == date,
                all_occurrences)
            if date.date() == now().date():
                current = True
            week.append((date, occurrences, current))
            day += 1
            date = date + timedelta(days=1)
        ctx.update({'week': week, 'date': date, 'week_nr': self.week})
        return ctx


class DayView(CategoryMixin, TemplateView):
    """View to return all occurrences of an event for one day."""
    template_name = 'calendarium/calendar_day.html'

    def dispatch(self, request, *args, **kwargs):
        self.day = int(kwargs.get('day'))
        self.month = int(kwargs.get('month'))
        self.year = int(kwargs.get('year'))
        try:
            self.date = datetime(year=self.year, month=self.month,
                                 day=self.day, tzinfo=utc)
        except ValueError:
            raise Http404
        if request.method == 'POST':
            if request.POST.get('next'):
                date = self.date + timedelta(days=1)
                return HttpResponseRedirect(reverse('calendar_day', kwargs={
                    'year': date.year, 'month': date.month, 'day': date.day}))
            elif request.POST.get('previous'):
                date = self.date - timedelta(days=1)
                return HttpResponseRedirect(reverse('calendar_day', kwargs={
                    'year': date.year, 'month': date.month, 'day': date.day}))
            elif request.POST.get('today'):
                return HttpResponseRedirect(reverse('calendar_day', kwargs={
                    'year': now().year, 'month': now().month,
                    'day': now().day}))
        if request.is_ajax():
            self.template_name = 'calendarium/partials/calendar_day.html'
        return super(DayView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = self.get_category_context()
        occurrences = Event.objects.get_occurrences(
            self.date, self.date, ctx.get('current_category'))
        ctx.update({'date': self.date, 'occurrences': occurrences})
        return ctx


class EventDetailView(DetailView):
    """View to return information of an event."""
    model = Event


class EventMixin(object):
    """Mixin to handle event-related functions."""
    model = Event

    @method_decorator(permission_required('calendarium.add_event'))
    def dispatch(self, request, *args, **kwargs):
        return super(EventMixin, self).dispatch(request, *args, **kwargs)


class EventUpdateView(EventMixin, UpdateView):
    """View to update information of an event."""
    pass


class EventCreateView(EventMixin, CreateView):
    """View to create an event."""
    pass


class EventDeleteView(EventMixin, DeleteView):
    """View to delete an event."""
    pass


class OccurrenceViewMixin(object):
    """Mixin to avoid repeating code for the Occurrence view classes."""
    form_class = OccurrenceForm

    def dispatch(self, request, *args, **kwargs):
        try:
            self.event = Event.objects.get(pk=kwargs.get('pk'))
        except Event.DoesNotExist:
            raise Http404
        year = int(kwargs.get('year'))
        month = int(kwargs.get('month'))
        day = int(kwargs.get('day'))
        try:
            date = datetime(year, month, day, tzinfo=utc)
        except (TypeError, ValueError):
            raise Http404
        # this should retrieve the one single occurrence, that has a
        # matching start date
        try:
            occ = Occurrence.objects.get(
                start__year=year, start__month=month, start__day=day)
        except Occurrence.DoesNotExist:
            occ_gen = self.event.get_occurrences(self.event.start)
            occ = occ_gen.next()
            while occ.start.date() < date.date():
                occ = occ_gen.next()
        if occ.start.date() == date.date():
            self.occurrence = occ
        else:
            raise Http404
        self.object = occ
        return super(OccurrenceViewMixin, self).dispatch(
            request, *args, **kwargs)

    def get_object(self):
        return self.object

    def get_form_kwargs(self):
        kwargs = super(OccurrenceViewMixin, self).get_form_kwargs()
        kwargs.update({'initial': model_to_dict(self.object)})
        return kwargs


class OccurrenceDeleteView(OccurrenceViewMixin, DeleteView):
    """View to delete an occurrence of an event."""
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        decision = self.request.POST.get('decision')
        self.object.delete_period(decision)
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, object):
        ctx = super(OccurrenceDeleteView, self).get_context_data()
        ctx.update({
            'decisions': OCCURRENCE_DECISIONS,
            'object': self.object
        })
        return ctx

    def get_success_url(self):
        return reverse('calendar_current_month')


class OccurrenceDetailView(OccurrenceViewMixin, DetailView):
    """View to show information of an occurrence of an event."""
    pass


class OccurrenceUpdateView(OccurrenceViewMixin, UpdateView):
    """View to edit an occurrence of an event."""
    pass


class UpcomingEventsAjaxView(CategoryMixin, ListView):
    template_name = 'calendarium/partials/upcoming_events.html'
    context_object_name = 'occurrences'

    def dispatch(self, request, *args, **kwargs):
        if request.GET.get('category'):
            self.category = EventCategory.objects.get(
                slug=request.GET.get('category'))
        else:
            self.category = None
        if request.GET.get('count'):
            self.count = int(request.GET.get('count'))
        else:
            self.count = None
        return super(UpcomingEventsAjaxView, self).dispatch(
            request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super(UpcomingEventsAjaxView, self).get_context_data(**kwargs)
        ctx.update(self.get_category_context(**kwargs))
        ctx.update({'show_excerpt': True, })
        return ctx

    def get_queryset(self):
        qs_kwargs = {
            'start': now(),
            'end': now() + timedelta(365),
        }
        if self.category:
            qs_kwargs.update({'category': self.category, })
        qs = Event.objects.get_occurrences(**qs_kwargs)
        if self.count:
            return qs[:self.count]
        return qs

########NEW FILE########
__FILENAME__ = widgets
"""Widgets for the ``calendarium`` app."""
from django import forms
from django.conf import settings
from django.utils.safestring import mark_safe


class ColorPickerWidget(forms.TextInput):
    class Media:
        css = {
            'all': (
                settings.STATIC_URL + 'calendarium/css/colorpicker.css',
            )
        }
        js = (
            '//ajax.googleapis.com/ajax/libs/jquery/1.2.6/jquery.min.js',
            settings.STATIC_URL + 'calendarium/js/colorpicker.js',
            settings.STATIC_URL + 'calendarium/js/colorpicker_list.js',
            settings.STATIC_URL + 'calendarium/js/eye.js',
            settings.STATIC_URL + 'calendarium/js/layout.js',
            settings.STATIC_URL + 'calendarium/js/utils.js',
        )

    def __init__(self, language=None, attrs=None):
        self.language = language or settings.LANGUAGE_CODE[:2]
        super(ColorPickerWidget, self).__init__(attrs=attrs)

    def render(self, name, value, attrs=None):
        rendered = super(ColorPickerWidget, self).render(name, value, attrs)
        return rendered + mark_safe(
            u'''<script type="text/javascript">
                $('#id_%s').ColorPicker({
                onSubmit: function(hsb, hex, rgb, el) {
                    $(el).val(hex);
                    $(el).ColorPickerHide();
                },
                onBeforeShow: function () {
                    $(this).ColorPickerSetColor(this.value);
                }
             }).bind('keyup', function(){
                 $(this).ColorPickerSetColor(this.value);
             });
            </script>''' % name)

########NEW FILE########
__FILENAME__ = conf
# flake8: noqa
# -*- coding: utf-8 -*-
#
# django-calendarium documentation build configuration file, created by
# sphinx-quickstart on Fri May  3 09:21:59 2013.
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

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'sphinx.ext.todo', 'sphinx.ext.coverage', 'sphinx.ext.ifconfig', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-calendarium'
copyright = u'2013, Martin Brochhaus'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.2'
# The full version, including alpha/beta/rc tags.
release = '0.2'

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

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


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
htmlhelp_basename = 'django-calendariumdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-calendarium.tex', u'django-calendarium Documentation',
   u'Martin Brochhaus', 'manual'),
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

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'django-calendarium', u'django-calendarium Documentation',
     [u'Martin Brochhaus'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'django-calendarium', u'django-calendarium Documentation',
   u'Martin Brochhaus', 'django-calendarium', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                          'calendarium.tests.south_settings')

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
