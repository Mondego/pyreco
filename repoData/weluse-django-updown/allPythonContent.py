__FILENAME__ = runtests
#!/usr/bin/env python
import sys

from os.path import dirname, abspath

from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'updown',
        ],
        # Fix for Django versions < 1.5
        AUTH_USER_MODEL='auth.User'
    )

from django.test.simple import DjangoTestSuiteRunner


def runtests(*test_args):
    if not test_args:
        test_args = ['updown']
    parent = dirname(abspath(__file__))
    sys.path.insert(0, parent)

    test_runner = DjangoTestSuiteRunner(verbosity=1)
    failures = test_runner.run_tests(test_args)
    sys.exit(failures)


if __name__ == '__main__':
    runtests(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-
"""
updown.exceptions
~~~~~~~~~~~~~~~~~

Some custom exceptions

:copyright: 2011, weluse (http://weluse.de)
:author: 2011, Daniel Banck <dbanck@weluse.de>
:license: BSD, see LICENSE for more details.
"""

class InvalidRating(ValueError):
    pass

class AuthRequired(TypeError): 
    pass

class CannotChangeVote(Exception): 
    pass

########NEW FILE########
__FILENAME__ = fields
# -*- coding: utf-8 -*-
"""
updown.fields
~~~~~~~~~~~~~

Fields needed for the updown ratings

:copyright: 2011, weluse (http://weluse.de)
:author: 2011, Daniel Banck <dbanck@weluse.de>
:license: BSD, see LICENSE for more details.
"""
from django.db.models import IntegerField, PositiveIntegerField
from django.conf import settings

from updown.models import Vote, SCORE_TYPES
from updown.exceptions import InvalidRating, AuthRequired, CannotChangeVote
from updown import forms


if 'django.contrib.contenttypes' not in settings.INSTALLED_APPS:
    raise ImportError("django-updown requires django.contrib.contenttypes "
                      "in your INSTALLED_APPS")

from django.contrib.contenttypes.models import ContentType

__all__ = ('Rating', 'RatingField', 'AnonymousRatingField')

try:
    from hashlib import md5
except ImportError:
    from md5 import new as md5


def md5_hexdigest(value):
    return md5(value).hexdigest()


class Rating(object):
    def __init__(self, likes, dislikes):
        self.likes = likes
        self.dislikes = dislikes


class RatingManager(object):
    def __init__(self, instance, field):
        self.content_type = None
        self.instance = instance
        self.field = field

        self.like_field_name = "%s_likes" % (self.field.name,)
        self.dislike_field_name = "%s_dislikes" % (self.field.name,)

    def get_rating_for_user(self, user, ip_address=None):
        kwargs = {
            'content_type': self.get_content_type(),
            'object_id': self.instance.pk,
            'key': self.field.key
        }

        if not (user and user.is_authenticated()):
            if not ip_address:
                raise ValueError("``user`` or ``ip_address`` must be "
                                 "present.")
            kwargs['user__isnull'] = True
            kwargs['ip_address'] = ip_address
        else:
            kwargs['user'] = user

        try:
            rating = Vote.objects.get(**kwargs)
            return rating.score
        except Vote.DoesNotExist:
            pass
        return

    def get_content_type(self):
        if self.content_type is None:
            self.content_type = ContentType.objects.get_for_model(
                self.instance)
        return self.content_type

    def add(self, score, user, ip_address, commit=True):
        try:
            score = int(score)
        except (ValueError, TypeError):
            raise InvalidRating("%s is not a valid score for %s" % (
                score, self.field.name))

        if score not in SCORE_TYPES.values():
            raise InvalidRating("%s is not a valid score" % (score,))

        is_anonymous = (user is None or not user.is_authenticated())
        if is_anonymous and not self.field.allow_anonymous:
            raise AuthRequired("User must be a user, not '%r'" % (user,))

        if is_anonymous:
            user = None

        defaults = {
            'score': score,
            'ip_address': ip_address
        }

        kwargs = {
            'content_type': self.get_content_type(),
            'object_id': self.instance.pk,
            'key': self.field.key,
            'user': user
        }
        if not user:
            kwargs['ip_address'] = ip_address

        try:
            rating, created = Vote.objects.get(**kwargs), False
        except Vote.DoesNotExist:
            kwargs.update(defaults)
            rating, created = Vote.objects.create(**kwargs), True

        has_changed = False
        if not created:
            if self.field.can_change_vote:
                has_changed = True
                if (rating.score == SCORE_TYPES['LIKE']):
                    self.likes -= 1
                else:
                    self.dislikes -= 1
                if (score == SCORE_TYPES['LIKE']):
                    self.likes += 1
                else:
                    self.dislikes += 1
                rating.score = score
                rating.save()
            else:
                raise CannotChangeVote()
        else:
            has_changed = True
            if (rating.score == SCORE_TYPES['LIKE']):
                self.likes += 1
            else:
                self.dislikes += 1

        if has_changed:
            if commit:
                self.instance.save()

    def _get_likes(self, default=None):
        return getattr(self.instance, self.like_field_name, default)

    def _set_likes(self, value):
        return setattr(self.instance, self.like_field_name, value)

    likes = property(_get_likes, _set_likes)

    def _get_dislikes(self, default=None):
        return getattr(self.instance, self.dislike_field_name, default)

    def _set_dislikes(self, value):
        return setattr(self.instance, self.dislike_field_name, value)

    dislikes = property(_get_dislikes, _set_dislikes)

    def get_difference(self):
        return self.likes - self.dislikes

    def get_quotient(self):
        return float(self.likes) / max(self.dislikes, 1)


class RatingCreator(object):
    def __init__(self, field):
        self.field = field
        self.like_field_name = "%s_likes" % (self.field.name,)
        self.dislike_field_name = "%s_dislikes" % (self.field.name,)

    def __get__(self, instance, type=None):
        if instance is None:
            return self.field
        return RatingManager(instance, self.field)

    def __set__(self, instance, value):
        if isinstance(value, Rating):
            setattr(instance, self.like_field_name, value.likes)
            setattr(instance, self.dislike_field_name, value.dislikes)
        else:
            raise TypeError("%s value must be a Rating instance, not '%r'" % (
                self.field.name, value))


class RatingField(IntegerField):
    def __init__(self, delimiter="|", *args, **kwargs):
        self.can_change_vote = kwargs.pop('can_change_vote', False)
        self.allow_anonymous = kwargs.pop('allow_anonymous', False)
        self.delimiter = delimiter
        kwargs['editable'] = False
        kwargs['default'] = 0
        kwargs['blank'] = True
        super(RatingField, self).__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name):
        self.name = name
        self.like_field = PositiveIntegerField(editable=False, default=0,
                                               blank=True)
        cls.add_to_class("%s_likes" % (self.name,), self.like_field)
        self.dislike_field = PositiveIntegerField(editable=False, default=0,
                                                  blank=True)
        cls.add_to_class("%s_dislikes" % (self.name,), self.dislike_field)
        self.key = md5_hexdigest(self.name)

        field = RatingCreator(self)
        if not hasattr(cls, '_ratings'):
            cls._ratings = []
        cls._ratings.append(self)

        setattr(cls, name, field)

    def to_python(self, value):
        # If it's already a list, leave it
        if isinstance(value, list):
            return value

        # Otherwise, split by delimiter
        return value.split(self.delimiter)

    def get_prep_value(self, value):
        return self.delimiter.join(value)

    def get_db_prep_save(self, value, connection):
        pass

    def get_db_prep_lookup(self, lookup_type, value, connection,
                           prepared=False):
        raise NotImplementedError(self.get_db_prep_lookup)

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.RatingField}
        defaults.update(kwargs)
        return super(RatingField, self).formfield(**defaults)


class AnonymousRatingField(RatingField):
    def __init__(self, *args, **kwargs):
        kwargs['allow_anonymous'] = True
        super(AnonymousRatingField, self).__init__(*args, **kwargs)


try:
    from south.modelsinspector import add_introspection_rules
except ImportError:
    pass
else:
    add_introspection_rules([
        (
            [RatingField],  # Class(es) these apply to
            [],             # Positional arguments (not used)
            {               # Keyword argument
                "delimiter": ["delimiter", {"default": "|"}],
            },
        ),
    ], ["^updown\.fields\.RatingField"])

########NEW FILE########
__FILENAME__ = forms
"""
updown.forms
~~~~~~~~~~~~~~~~~~~~~~~

Very basic form fields

:copyright: 2011, weluse (http://weluse.de)
:author: 2011, Daniel Banck <dbanck@weluse.de>
:license: BSD, see LICENSE for more details.
"""
from django import forms


__all__ = ('RatingField',)

class RatingField(forms.ChoiceField):
    pass

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Vote'
        db.create_table('updown_vote', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='votes', to=orm['contenttypes.ContentType'])),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('score', self.gf('django.db.models.fields.SmallIntegerField')()),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='votes', to=orm['auth.User'])),
            ('date_added', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('date_changed', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
        ))
        db.send_create_signal('updown', ['Vote'])

        # Adding unique constraint on 'Vote', fields ['content_type', 'object_id', 'key', 'user']
        db.create_unique('updown_vote', ['content_type_id', 'object_id', 'key', 'user_id'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Vote', fields ['content_type', 'object_id', 'key', 'user']
        db.delete_unique('updown_vote', ['content_type_id', 'object_id', 'key', 'user_id'])

        # Deleting model 'Vote'
        db.delete_table('updown_vote')


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
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'updown.vote': {
            'Meta': {'unique_together': "(('content_type', 'object_id', 'key', 'user'),)", 'object_name': 'Vote'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'votes'", 'to': "orm['contenttypes.ContentType']"}),
            'date_added': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'date_changed': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'score': ('django.db.models.fields.SmallIntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'votes'", 'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['updown']

########NEW FILE########
__FILENAME__ = 0002_auto__allow_anonymous
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding field 'Vote.ip_address'
        db.add_column('updown_vote', 'ip_address', self.gf('django.db.models.fields.IPAddressField')(default='0.0.0.0', max_length=15), keep_default=False)

        # Changing field 'Vote.user'
        db.alter_column('updown_vote', 'user_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['auth.User']))


    def backwards(self, orm):
        
        # Deleting field 'Vote.ip_address'
        db.delete_column('updown_vote', 'ip_address')

        # Changing field 'Vote.user'
        db.alter_column('updown_vote', 'user_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User']))


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
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'updown.vote': {
            'Meta': {'unique_together': "(('content_type', 'object_id', 'key', 'user'),)", 'object_name': 'Vote'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'votes'", 'to': "orm['contenttypes.ContentType']"}),
            'date_added': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'date_changed': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'score': ('django.db.models.fields.SmallIntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'votes'", 'null': 'True', 'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['updown']

########NEW FILE########
__FILENAME__ = 0003_auto__changed_unique_key
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Removing unique constraint on 'Vote', fields ['key', 'object_id', 'content_type', 'user']
        db.delete_unique('updown_vote', ['key', 'object_id', 'content_type_id', 'user_id'])

        # Adding unique constraint on 'Vote', fields ['key', 'ip_address', 'object_id', 'content_type', 'user']
        db.create_unique('updown_vote', ['key', 'ip_address', 'object_id', 'content_type_id', 'user_id'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Vote', fields ['key', 'ip_address', 'object_id', 'content_type', 'user']
        db.delete_unique('updown_vote', ['key', 'ip_address', 'object_id', 'content_type_id', 'user_id'])

        # Adding unique constraint on 'Vote', fields ['key', 'object_id', 'content_type', 'user']
        db.create_unique('updown_vote', ['key', 'object_id', 'content_type_id', 'user_id'])


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
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'updown.vote': {
            'Meta': {'unique_together': "(('content_type', 'object_id', 'key', 'user', 'ip_address'),)", 'object_name': 'Vote'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'votes'", 'to': "orm['contenttypes.ContentType']"}),
            'date_added': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'date_changed': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'score': ('django.db.models.fields.SmallIntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'votes'", 'null': 'True', 'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['updown']

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
"""
updown.models
~~~~~~~~~~~~~

The vote model for storing ratings

:copyright: 2011, weluse (http://weluse.de)
:author: 2011, Daniel Banck <dbanck@weluse.de>
:license: BSD, see LICENSE for more details.
"""
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone

_SCORE_TYPE_CHOICES = (
    (-1, 'DISLIKE'),
    (1, 'LIKE'),
)

SCORE_TYPES = dict((value, key) for key, value in _SCORE_TYPE_CHOICES)

class Vote(models.Model):
    content_type = models.ForeignKey(ContentType, related_name="updown_votes")
    object_id = models.PositiveIntegerField()
    key = models.CharField(max_length=32)
    score = models.SmallIntegerField(choices=_SCORE_TYPE_CHOICES)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name="updown_votes")
    ip_address = models.IPAddressField()
    date_added = models.DateTimeField(default=timezone.now, editable=False)
    date_changed = models.DateTimeField(default=timezone.now, editable=False)

    content_object = generic.GenericForeignKey()

    class Meta:
        unique_together = (('content_type', 'object_id', 'key', 'user',
                            'ip_address'))

    def __unicode__(self):
        return u"%s voted %s on %s" % (self.user, self.score,
                                       self.content_object)

    def save(self, *args, **kwargs):
        self.date_changed = timezone.now()
        super(Vote, self).save(*args, **kwargs)

    def partial_ip_address(self):
        ip = self.ip_address.split('.')
        ip[-1] = 'xxx'
        return '.'.join(ip)

    partial_ip_address = property(partial_ip_address)


########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
"""
updown.tests
~~~~~~~~~~~~

Tests the models provided by the updown rating app

:copyright: 2011, weluse (http://weluse.de)
:author: 2011, Daniel Banck <dbanck@weluse.de>
:license: BSD, see LICENSE for more details.
"""
import random

from django.test import TestCase
from django.db import models
from django.contrib.auth.models import User

from updown.models import SCORE_TYPES
from updown.fields import RatingField
from updown.exceptions import CannotChangeVote


class RatingTestModel(models.Model):
    rating = RatingField(can_change_vote=True)
    rating2 = RatingField(can_change_vote=False)

    def __unicode__(self):
        return unicode(self.pk)

class TestRatingModel(TestCase):
    """Test case for the generic rating app"""

    def setUp(self):
        self.instance = RatingTestModel.objects.create()

        self.user = User.objects.create(username=str(random.randint(0, 100000000)))
        self.user2 = User.objects.create(username=str(random.randint(0, 100000000)))


    def test_basic_vote(self):
        """Test a simple vote"""
        self.instance.rating.add(SCORE_TYPES['LIKE'], self.user, '192.168.0.1')

        self.assertEquals(self.instance.rating_likes, 1)

    def test_change_vote(self):
        self.instance.rating.add(SCORE_TYPES['LIKE'], self.user, '192.168.0.1')
        self.instance.rating.add(SCORE_TYPES['DISLIKE'], self.user,
                '192.168.0.1')

        self.assertEquals(self.instance.rating_likes, 0)
        self.assertEquals(self.instance.rating_dislikes, 1)

    def test_change_vote_disallowed(self):
        self.instance.rating2.add(SCORE_TYPES['LIKE'], self.user, '192.168.0.1')
        self.assertRaises(CannotChangeVote, self.instance.rating2.add,
                          SCORE_TYPES['DISLIKE'], self.user, '192.168.0.1')

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
"""
updown.views
~~~~~~~~~~~~

Basic views for voting

:copyright: 2011, weluse (http://weluse.de)
:author: 2011, Daniel Banck <dbanck@weluse.de>
:license: BSD, see LICENSE for more details.
"""
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, Http404

from updown.exceptions import *


class AddRatingView(object):
    def __call__(self, request, content_type_id, object_id, field_name, score):
        """__call__(request, content_type_id, object_id, field_name, score)

        Adds a vote to the specified model field."""

        try:
            instance = self.get_instance(content_type_id, object_id)
        except ObjectDoesNotExist:
            raise Http404('Object does not exist')

        context = self.get_context(request)
        context['instance'] = instance

        try:
            field = getattr(instance, field_name)
        except AttributeError:
            return self.invalid_field_response(request, context)

        context.update({
            'field': field,
            'score': score,
        })


        try:
            had_voted = bool(field.get_rating_for_user(request.user,
                                                       request.META['REMOTE_ADDR']))

            context['had_voted'] = had_voted
            field.add(score, request.user, request.META['REMOTE_ADDR'])
        except AuthRequired:
            return self.authentication_required_response(request, context)
        except InvalidRating:
            return self.invalid_rating_response(request, context)
        except CannotChangeVote:
            return self.cannot_change_vote_response(request, context)
        if had_voted:
            return self.rating_changed_response(request, context)
        return self.rating_added_response(request, context)

    def get_context(self, request, context={}):
        return context

    def render_to_response(self, template, context, request):
        raise NotImplementedError

    def rating_changed_response(self, request, context):
        response = HttpResponse('Vote changed.')
        return response

    def rating_added_response(self, request, context):
        response = HttpResponse('Vote recorded.')
        return response

    def authentication_required_response(self, request, context):
        response = HttpResponse('You must be logged in to vote.')
        response.status_code = 403
        return response

    def cannot_change_vote_response(self, request, context):
        response = HttpResponse('You have already voted.')
        response.status_code = 403
        return response

    def invalid_field_response(self, request, context):
        response = HttpResponse('Invalid field name.')
        response.status_code = 403
        return response

    def invalid_rating_response(self, request, context):
        response = HttpResponse('Invalid rating value.')
        response.status_code = 403
        return response

    def get_instance(self, content_type_id, object_id):
        return ContentType.objects.get(pk=content_type_id)\
            .get_object_for_this_type(pk=object_id)


class AddRatingFromModel(AddRatingView):
    def __call__(self, request, model, app_label, object_id, field_name, score, **kwargs):
        """__call__(request, model, app_label, object_id, field_name, score)

        Adds a vote to the specified model field."""
        try:
            content_type = ContentType.objects.get(model=model.lower(), app_label=app_label)
        except ContentType.DoesNotExist:
            raise Http404('Invalid `model` or `app_label`.')

        return super(AddRatingFromModel, self).__call__(request, content_type.id,
                                                        object_id, field_name, score)


########NEW FILE########
