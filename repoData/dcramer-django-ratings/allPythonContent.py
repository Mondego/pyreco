__FILENAME__ = admin
from django.contrib import admin
from models import Vote, Score

class VoteAdmin(admin.ModelAdmin):
    list_display = ('content_object', 'user', 'ip_address', 'cookie', 'score', 'date_changed')
    list_filter = ('score', 'content_type', 'date_changed')
    search_fields = ('ip_address',)
    raw_id_fields = ('user',)

class ScoreAdmin(admin.ModelAdmin):
    list_display = ('content_object', 'score', 'votes')
    list_filter = ('content_type',)

admin.site.register(Vote, VoteAdmin)
admin.site.register(Score, ScoreAdmin)

########NEW FILE########
__FILENAME__ = default_settings
from django.conf import settings

# Used to limit the number of unique IPs that can vote on a single object+field.
#   useful if you're getting rating spam by users registering multiple accounts
RATINGS_VOTES_PER_IP = 3
########NEW FILE########
__FILENAME__ = exceptions
class InvalidRating(ValueError): pass
class AuthRequired(TypeError): pass
class CannotChangeVote(Exception): pass
class CannotDeleteVote(Exception): pass
class IPLimitReached(Exception): pass
########NEW FILE########
__FILENAME__ = fields
from django.db.models import IntegerField, PositiveIntegerField
from django.conf import settings

import forms
import itertools
from datetime import datetime

from models import Vote, Score
from default_settings import RATINGS_VOTES_PER_IP
from exceptions import *

if 'django.contrib.contenttypes' not in settings.INSTALLED_APPS:
    raise ImportError("djangoratings requires django.contrib.contenttypes in your INSTALLED_APPS")

from django.contrib.contenttypes.models import ContentType

__all__ = ('Rating', 'RatingField', 'AnonymousRatingField')

try:
    from hashlib import md5
except ImportError:
    from md5 import new as md5

try:
    from django.utils.timezone import now
except ImportError:
    now = datetime.now

def md5_hexdigest(value):
    return md5(value).hexdigest()

class Rating(object):
    def __init__(self, score, votes):
        self.score = score
        self.votes = votes

class RatingManager(object):
    def __init__(self, instance, field):
        self.content_type = None
        self.instance = instance
        self.field = field
        
        self.votes_field_name = "%s_votes" % (self.field.name,)
        self.score_field_name = "%s_score" % (self.field.name,)
    
    def get_percent(self):
        """get_percent()
        
        Returns the weighted percentage of the score from min-max values"""
        if not (self.votes and self.score):
            return 0
        return 100 * (self.get_rating() / self.field.range)
    
    def get_real_percent(self):
        """get_real_percent()
        
        Returns the unmodified percentage of the score based on a 0-point scale."""
        if not (self.votes and self.score):
            return 0
        return 100 * (self.get_real_rating() / self.field.range)
    
    def get_ratings(self):
        """get_ratings()
        
        Returns a Vote QuerySet for this rating field."""
        return Vote.objects.filter(content_type=self.get_content_type(), object_id=self.instance.pk, key=self.field.key)
        
    def get_rating(self):
        """get_rating()
        
        Returns the weighted average rating."""
        if not (self.votes and self.score):
            return 0
        return float(self.score)/(self.votes+self.field.weight)
    
    def get_opinion_percent(self):
        """get_opinion_percent()
        
        Returns a neutral-based percentage."""
        return (self.get_percent()+100)/2

    def get_real_rating(self):
        """get_rating()
        
        Returns the unmodified average rating."""
        if not (self.votes and self.score):
            return 0
        return float(self.score)/self.votes
    
    def get_rating_for_user(self, user, ip_address=None, cookies={}):
        """get_rating_for_user(user, ip_address=None, cookie=None)
        
        Returns the rating for a user or anonymous IP."""
        kwargs = dict(
            content_type    = self.get_content_type(),
            object_id       = self.instance.pk,
            key             = self.field.key,
        )

        if not (user and user.is_authenticated()):
            if not ip_address:
                raise ValueError('``user`` or ``ip_address`` must be present.')
            kwargs['user__isnull'] = True
            kwargs['ip_address'] = ip_address
        else:
            kwargs['user'] = user
        
        use_cookies = (self.field.allow_anonymous and self.field.use_cookies)
        if use_cookies:
            # TODO: move 'vote-%d.%d.%s' to settings or something
            cookie_name = 'vote-%d.%d.%s' % (kwargs['content_type'].pk, kwargs['object_id'], kwargs['key'][:6],) # -> md5_hexdigest?
            cookie = cookies.get(cookie_name)
            if cookie:    
                kwargs['cookie'] = cookie
            else:
                kwargs['cookie__isnull'] = True
            
        try:
            rating = Vote.objects.get(**kwargs)
            return rating.score
        except Vote.MultipleObjectsReturned:
            pass
        except Vote.DoesNotExist:
            pass
        return
    
    def get_iterable_range(self):
        return range(1, self.field.range) #started from 1, because 0 is equal to delete
        
    def add(self, score, user, ip_address, cookies={}, commit=True):
        """add(score, user, ip_address)
        
        Used to add a rating to an object."""
        try:
            score = int(score)
        except (ValueError, TypeError):
            raise InvalidRating("%s is not a valid choice for %s" % (score, self.field.name))
        
        delete = (score == 0)
        if delete and not self.field.allow_delete:
            raise CannotDeleteVote("you are not allowed to delete votes for %s" % (self.field.name,))
            # ... you're also can't delete your vote if you haven't permissions to change it. I leave this case for CannotChangeVote
        
        if score < 0 or score > self.field.range:
            raise InvalidRating("%s is not a valid choice for %s" % (score, self.field.name))

        is_anonymous = (user is None or not user.is_authenticated())
        if is_anonymous and not self.field.allow_anonymous:
            raise AuthRequired("user must be a user, not '%r'" % (user,))
        
        if is_anonymous:
            user = None
        
        defaults = dict(
            score = score,
            ip_address = ip_address,
        )
        
        kwargs = dict(
            content_type    = self.get_content_type(),
            object_id       = self.instance.pk,
            key             = self.field.key,
            user            = user,
        )
        if not user:
            kwargs['ip_address'] = ip_address
        
        use_cookies = (self.field.allow_anonymous and self.field.use_cookies)
        if use_cookies:
            defaults['cookie'] = now().strftime('%Y%m%d%H%M%S%f') # -> md5_hexdigest?
            # TODO: move 'vote-%d.%d.%s' to settings or something
            cookie_name = 'vote-%d.%d.%s' % (kwargs['content_type'].pk, kwargs['object_id'], kwargs['key'][:6],) # -> md5_hexdigest?
            cookie = cookies.get(cookie_name) # try to get existent cookie value
            if not cookie:
                kwargs['cookie__isnull'] = True
            kwargs['cookie'] = cookie

        try:
            rating, created = Vote.objects.get(**kwargs), False
        except Vote.DoesNotExist:
            if delete:
                raise CannotDeleteVote("attempt to find and delete your vote for %s is failed" % (self.field.name,))
            if getattr(settings, 'RATINGS_VOTES_PER_IP', RATINGS_VOTES_PER_IP):
                num_votes = Vote.objects.filter(
                    content_type=kwargs['content_type'],
                    object_id=kwargs['object_id'],
                    key=kwargs['key'],
                    ip_address=ip_address,
                ).count()
                if num_votes >= getattr(settings, 'RATINGS_VOTES_PER_IP', RATINGS_VOTES_PER_IP):
                    raise IPLimitReached()
            kwargs.update(defaults)
            if use_cookies:
                # record with specified cookie was not found ...
                cookie = defaults['cookie'] # ... thus we need to replace old cookie (if presented) with new one
                kwargs.pop('cookie__isnull', '') # ... and remove 'cookie__isnull' (if presented) from .create()'s **kwargs
            rating, created = Vote.objects.create(**kwargs), True
            
        has_changed = False
        if not created:
            if self.field.can_change_vote:
                has_changed = True
                self.score -= rating.score
                # you can delete your vote only if you have permission to change your vote
                if not delete:
                    rating.score = score
                    rating.save()
                else:
                    self.votes -= 1
                    rating.delete()
            else:
                raise CannotChangeVote()
        else:
            has_changed = True
            self.votes += 1
        if has_changed:
            if not delete:
                self.score += rating.score
            if commit:
                self.instance.save()
            #setattr(self.instance, self.field.name, Rating(score=self.score, votes=self.votes))
            
            defaults = dict(
                score   = self.score,
                votes   = self.votes,
            )
            
            kwargs = dict(
                content_type    = self.get_content_type(),
                object_id       = self.instance.pk,
                key             = self.field.key,
            )
            
            try:
                score, created = Score.objects.get(**kwargs), False
            except Score.DoesNotExist:
                kwargs.update(defaults)
                score, created = Score.objects.create(**kwargs), True
            
            if not created:
                score.__dict__.update(defaults)
                score.save()
        
        # return value
        adds = {}
        if use_cookies:
            adds['cookie_name'] = cookie_name
            adds['cookie'] = cookie
        if delete:
            adds['deleted'] = True
        return adds

    def delete(self, user, ip_address, cookies={}, commit=True):
        return self.add(0, user, ip_address, cookies, commit)
    
    def _get_votes(self, default=None):
        return getattr(self.instance, self.votes_field_name, default)
    
    def _set_votes(self, value):
        return setattr(self.instance, self.votes_field_name, value)
        
    votes = property(_get_votes, _set_votes)

    def _get_score(self, default=None):
        return getattr(self.instance, self.score_field_name, default)
    
    def _set_score(self, value):
        return setattr(self.instance, self.score_field_name, value)
        
    score = property(_get_score, _set_score)

    def get_content_type(self):
        if self.content_type is None:
            self.content_type = ContentType.objects.get_for_model(self.instance)
        return self.content_type
    
    def _update(self, commit=False):
        """Forces an update of this rating (useful for when Vote objects are removed)."""
        votes = Vote.objects.filter(
            content_type    = self.get_content_type(),
            object_id       = self.instance.pk,
            key             = self.field.key,
        )
        obj_score = sum([v.score for v in votes])
        obj_votes = len(votes)

        score, created = Score.objects.get_or_create(
            content_type    = self.get_content_type(),
            object_id       = self.instance.pk,
            key             = self.field.key,
            defaults        = dict(
                score       = obj_score,
                votes       = obj_votes,
            )
        )
        if not created:
            score.score = obj_score
            score.votes = obj_votes
            score.save()
        self.score = obj_score
        self.votes = obj_votes
        if commit:
            self.instance.save()

class RatingCreator(object):
    def __init__(self, field):
        self.field = field
        self.votes_field_name = "%s_votes" % (self.field.name,)
        self.score_field_name = "%s_score" % (self.field.name,)

    def __get__(self, instance, type=None):
        if instance is None:
            return self.field
            #raise AttributeError('Can only be accessed via an instance.')
        return RatingManager(instance, self.field)

    def __set__(self, instance, value):
        if isinstance(value, Rating):
            setattr(instance, self.votes_field_name, value.votes)
            setattr(instance, self.score_field_name, value.score)
        else:
            raise TypeError("%s value must be a Rating instance, not '%r'" % (self.field.name, value))

class RatingField(IntegerField):
    """
    A rating field contributes two columns to the model instead of the standard single column.
    """
    def __init__(self, *args, **kwargs):
        if 'choices' in kwargs:
            raise TypeError("%s invalid attribute 'choices'" % (self.__class__.__name__,))
        self.can_change_vote = kwargs.pop('can_change_vote', False)
        self.weight = kwargs.pop('weight', 0)
        self.range = kwargs.pop('range', 2)
        self.allow_anonymous = kwargs.pop('allow_anonymous', False)
        self.use_cookies = kwargs.pop('use_cookies', False)
        self.allow_delete = kwargs.pop('allow_delete', False)
        kwargs['editable'] = False
        kwargs['default'] = 0
        kwargs['blank'] = True
        super(RatingField, self).__init__(*args, **kwargs)
    
    def contribute_to_class(self, cls, name):
        self.name = name

        # Votes tally field
        self.votes_field = PositiveIntegerField(
            editable=False, default=0, blank=True)
        cls.add_to_class("%s_votes" % (self.name,), self.votes_field)

        # Score sum field
        self.score_field = IntegerField(
            editable=False, default=0, blank=True)
        cls.add_to_class("%s_score" % (self.name,), self.score_field)

        self.key = md5_hexdigest(self.name)

        field = RatingCreator(self)

        if not hasattr(cls, '_djangoratings'):
            cls._djangoratings = []
        cls._djangoratings.append(self)

        setattr(cls, name, field)

    def get_db_prep_save(self, value):
        # XXX: what happens here?
        pass

    def get_db_prep_lookup(self, lookup_type, value):
        # TODO: hack in support for __score and __votes
        # TODO: order_by on this field should use the weighted algorithm
        raise NotImplementedError(self.get_db_prep_lookup)
        # if lookup_type in ('score', 'votes'):
        #     lookup_type = 
        #     return self.score_field.get_db_prep_lookup()
        if lookup_type == 'exact':
            return [self.get_db_prep_save(value)]
        elif lookup_type == 'in':
            return [self.get_db_prep_save(v) for v in value]
        else:
            return super(RatingField, self).get_db_prep_lookup(lookup_type, value)

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.RatingField}
        defaults.update(kwargs)
        return super(RatingField, self).formfield(**defaults)

    # TODO: flatten_data method


class AnonymousRatingField(RatingField):
    def __init__(self, *args, **kwargs):
        kwargs['allow_anonymous'] = True
        super(AnonymousRatingField, self).__init__(*args, **kwargs)

########NEW FILE########
__FILENAME__ = forms
from django import forms

__all__ = ('RatingField',)

class RatingField(forms.ChoiceField):
    pass
########NEW FILE########
__FILENAME__ = update_recommendations
from django.core.management.base import NoArgsCommand, CommandError

from djangoratings.models import SimilarUser

class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        SimilarUser.objects.update_recommendations()
########NEW FILE########
__FILENAME__ = managers
from django.db.models import Manager
from django.db.models.query import QuerySet

from django.contrib.contenttypes.models import ContentType
import itertools

class VoteQuerySet(QuerySet):
    def delete(self, *args, **kwargs):
        """Handles updating the related `votes` and `score` fields attached to the model."""
        # XXX: circular import
        from fields import RatingField

        qs = self.distinct().values_list('content_type', 'object_id').order_by('content_type')
    
        to_update = []
        for content_type, objects in itertools.groupby(qs, key=lambda x: x[0]):
            model_class = ContentType.objects.get(pk=content_type).model_class()
            if model_class:
                to_update.extend(list(model_class.objects.filter(pk__in=list(objects)[0])))
        
        retval = super(VoteQuerySet, self).delete(*args, **kwargs)
        
        # TODO: this could be improved
        for obj in to_update:
            for field in getattr(obj, '_djangoratings', []):
                getattr(obj, field.name)._update(commit=False)
            obj.save()
        
        return retval
        
class VoteManager(Manager):
    def get_query_set(self):
        return VoteQuerySet(self.model)

    def get_for_user_in_bulk(self, objects, user):
        objects = list(objects)
        if len(objects) > 0:
            ctype = ContentType.objects.get_for_model(objects[0])
            votes = list(self.filter(content_type__pk=ctype.id,
                                     object_id__in=[obj._get_pk_val() \
                                                    for obj in objects],
                                     user__pk=user.id))
            vote_dict = dict([(vote.object_id, vote) for vote in votes])
        else:
            vote_dict = {}
        return vote_dict

class SimilarUserManager(Manager):
    def get_recommendations(self, user, model_class, min_score=1):
        from djangoratings.models import Vote, IgnoredObject
        
        content_type = ContentType.objects.get_for_model(model_class)
        
        params = dict(
            v=Vote._meta.db_table,
            sm=self.model._meta.db_table,
            m=model_class._meta.db_table,
            io=IgnoredObject._meta.db_table,
        )
        
        objects = model_class._default_manager.extra(
            tables=[params['v']],
            where=[
                '%(v)s.object_id = %(m)s.id and %(v)s.content_type_id = %%s' % params,
                '%(v)s.user_id IN (select to_user_id from %(sm)s where from_user_id = %%s and exclude = 0)' % params,
                '%(v)s.score >= %%s' % params,
                # Exclude already rated maps
                '%(v)s.object_id NOT IN (select object_id from %(v)s where content_type_id = %(v)s.content_type_id and user_id = %%s)' % params,
                # IgnoredObject exclusions
                '%(v)s.object_id NOT IN (select object_id from %(io)s where content_type_id = %(v)s.content_type_id and user_id = %%s)' % params,
            ],
            params=[content_type.id, user.id, min_score, user.id, user.id]
        ).distinct()

        # objects = model_class._default_manager.filter(pk__in=content_type.votes.extra(
        #     where=['user_id IN (select to_user_id from %s where from_user_id = %d and exclude = 0)' % (self.model._meta.db_table, user.pk)],
        # ).filter(score__gte=min_score).exclude(
        #     object_id__in=IgnoredObject.objects.filter(content_type=content_type, user=user).values_list('object_id', flat=True),
        # ).exclude(
        #     object_id__in=Vote.objects.filter(content_type=content_type, user=user).values_list('object_id', flat=True)
        # ).distinct().values_list('object_id', flat=True))
        
        return objects
    
    def update_recommendations(self):
        # TODO: this is mysql only atm
        # TODO: this doesnt handle scores that have multiple values (e.g. 10 points, 5 stars)
        # due to it calling an agreement as score = score. We need to loop each rating instance
        # and express the condition based on the range.
        from djangoratings.models import Vote
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute('begin')
        cursor.execute('truncate table %s' % (self.model._meta.db_table,))
        cursor.execute("""insert into %(t1)s
          (to_user_id, from_user_id, agrees, disagrees, exclude)
          select v1.user_id, v2.user_id,
                 sum(if(v2.score = v1.score, 1, 0)) as agrees,
                 sum(if(v2.score != v1.score, 1, 0)) as disagrees, 0
            from %(t2)s as v1
              inner join %(t2)s as v2
                on v1.user_id != v2.user_id
                and v1.object_id = v2.object_id
                and v1.content_type_id = v2.content_type_id
            where v1.user_id is not null
              and v2.user_id is not null
            group by v1.user_id, v2.user_id
            having agrees / (disagrees + 0.0001) > 3
          on duplicate key update agrees = values(agrees), disagrees = values(disagrees);""" % dict(
            t1=self.model._meta.db_table,
            t2=Vote._meta.db_table,
        ))
        cursor.execute('commit')
        cursor.close()
########NEW FILE########
__FILENAME__ = 0001_initial

from south.db import db
from django.db import models
from djangoratings.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'Score'
        db.create_table('djangoratings_score', (
            ('id', orm['djangoratings.Score:id']),
            ('content_type', orm['djangoratings.Score:content_type']),
            ('object_id', orm['djangoratings.Score:object_id']),
            ('key', orm['djangoratings.Score:key']),
            ('score', orm['djangoratings.Score:score']),
            ('votes', orm['djangoratings.Score:votes']),
        ))
        db.send_create_signal('djangoratings', ['Score'])
        
        # Adding model 'Vote'
        db.create_table('djangoratings_vote', (
            ('id', orm['djangoratings.Vote:id']),
            ('content_type', orm['djangoratings.Vote:content_type']),
            ('object_id', orm['djangoratings.Vote:object_id']),
            ('key', orm['djangoratings.Vote:key']),
            ('score', orm['djangoratings.Vote:score']),
            ('user', orm['djangoratings.Vote:user']),
            ('ip_address', orm['djangoratings.Vote:ip_address']),
            ('date_added', orm['djangoratings.Vote:date_added']),
            ('date_changed', orm['djangoratings.Vote:date_changed']),
        ))
        db.send_create_signal('djangoratings', ['Vote'])
        
        # Creating unique_together for [content_type, object_id, key, user, ip_address] on Vote.
        db.create_unique('djangoratings_vote', ['content_type_id', 'object_id', 'key', 'user_id', 'ip_address'])
        
        # Creating unique_together for [content_type, object_id, key] on Score.
        db.create_unique('djangoratings_score', ['content_type_id', 'object_id', 'key'])
        
    
    
    def backwards(self, orm):
        
        # Deleting unique_together for [content_type, object_id, key] on Score.
        db.delete_unique('djangoratings_score', ['content_type_id', 'object_id', 'key'])
        
        # Deleting unique_together for [content_type, object_id, key, user, ip_address] on Vote.
        db.delete_unique('djangoratings_vote', ['content_type_id', 'object_id', 'key', 'user_id', 'ip_address'])
        
        # Deleting model 'Score'
        db.delete_table('djangoratings_score')
        
        # Deleting model 'Vote'
        db.delete_table('djangoratings_vote')
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '30', 'unique': 'True', 'null': 'True', 'blank': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'djangoratings.score': {
            'Meta': {'unique_together': "(('content_type', 'object_id', 'key'),)"},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'score': ('django.db.models.fields.IntegerField', [], {}),
            'votes': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'djangoratings.vote': {
            'Meta': {'unique_together': "(('content_type', 'object_id', 'key', 'user', 'ip_address'),)"},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'votes'", 'to': "orm['contenttypes.ContentType']"}),
            'date_added': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'date_changed': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'score': ('django.db.models.fields.IntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'votes'", 'null': 'True', 'to': "orm['auth.User']"})
        }
    }
    
    complete_apps = ['djangoratings']

########NEW FILE########
__FILENAME__ = 0002_add_mean_and_stddev
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    
    def forwards(self, orm):
        
        # Adding field 'Score.stddev'
        db.add_column('djangoratings_score', 'stddev', self.gf('django.db.models.fields.FloatField')(default=0.0), keep_default=False)

        # Adding field 'Score.mean'
        db.add_column('djangoratings_score', 'mean', self.gf('django.db.models.fields.FloatField')(default=0.0), keep_default=False)
    
    
    def backwards(self, orm):
        
        # Deleting field 'Score.stddev'
        db.delete_column('djangoratings_score', 'stddev')

        # Deleting field 'Score.mean'
        db.delete_column('djangoratings_score', 'mean')
    
    
    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            '_battlenet_profiles': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'battlenet_profiles'", 'blank': 'True'}),
            'avatar': ('django.db.models.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'bio': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'custom_title': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'gold': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_moderator': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'level': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'signature': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'xp': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'djangoratings.score': {
            'Meta': {'unique_together': "(('content_type', 'object_id', 'key'),)", 'object_name': 'Score'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'mean': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'score': ('django.db.models.fields.IntegerField', [], {}),
            'stddev': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'votes': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'djangoratings.vote': {
            'Meta': {'unique_together': "(('content_type', 'object_id', 'key', 'user', 'ip_address'),)", 'object_name': 'Vote'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'votes'", 'to': "orm['contenttypes.ContentType']"}),
            'date_added': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'date_changed': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'score': ('django.db.models.fields.IntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'votes'", 'null': 'True', 'to': "orm['auth.User']"})
        }
    }
    
    complete_apps = ['djangoratings']

########NEW FILE########
__FILENAME__ = 0003_add_correlations
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    
    def forwards(self, orm):
        
        # Adding model 'ScoreCorrelation'
        db.create_table('djangoratings_scorecorrelation', (
            ('rank', self.gf('django.db.models.fields.FloatField')()),
            ('to_content_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='djr_sc_2', to=orm['contenttypes.ContentType'])),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='djr_sc_1', to=orm['contenttypes.ContentType'])),
            ('to_object_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('djangoratings', ['ScoreCorrelation'])
    
    
    def backwards(self, orm):
        
        # Deleting model 'ScoreCorrelation'
        db.delete_table('djangoratings_scorecorrelation')
    
    
    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            '_battlenet_profiles': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'battlenet_profiles'", 'blank': 'True'}),
            'avatar': ('django.db.models.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'bio': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'custom_title': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'gold': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_moderator': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'level': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'signature': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'xp': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'djangoratings.score': {
            'Meta': {'unique_together': "(('content_type', 'object_id', 'key'),)", 'object_name': 'Score'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'mean': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'score': ('django.db.models.fields.IntegerField', [], {}),
            'stddev': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
            'votes': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'djangoratings.scorecorrelation': {
            'Meta': {'unique_together': "(('content_type', 'object_id', 'to_content_type', 'to_object_id'),)", 'object_name': 'ScoreCorrelation'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'djr_sc_1'", 'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'rank': ('django.db.models.fields.FloatField', [], {}),
            'to_content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'djr_sc_2'", 'to': "orm['contenttypes.ContentType']"}),
            'to_object_id': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'djangoratings.vote': {
            'Meta': {'unique_together': "(('content_type', 'object_id', 'key', 'user', 'ip_address'),)", 'object_name': 'Vote'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'votes'", 'to': "orm['contenttypes.ContentType']"}),
            'date_added': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'date_changed': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'score': ('django.db.models.fields.IntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'votes'", 'null': 'True', 'to': "orm['auth.User']"})
        }
    }
    
    complete_apps = ['djangoratings']

########NEW FILE########
__FILENAME__ = 0004_rethink_recommendations
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    
    def forwards(self, orm):
        
        # Deleting model 'ScoreCorrelation'
        db.delete_table('djangoratings_scorecorrelation')

        # Adding model 'SimilarUser'
        db.create_table('djangoratings_similaruser', (
            ('to_user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='similar_users_from', to=orm['auth.User'])),
            ('agrees', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('disagrees', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('from_user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='similar_users', to=orm['auth.User'])),
        ))
        db.send_create_signal('djangoratings', ['SimilarUser'])

        # Deleting field 'Score.stddev'
        db.delete_column('djangoratings_score', 'stddev')

        # Deleting field 'Score.mean'
        db.delete_column('djangoratings_score', 'mean')
    
    
    def backwards(self, orm):
        
        # Adding model 'ScoreCorrelation'
        db.create_table('djangoratings_scorecorrelation', (
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('to_content_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='djr_sc_2', to=orm['contenttypes.ContentType'])),
            ('rank', self.gf('django.db.models.fields.FloatField')()),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='djr_sc_1', to=orm['contenttypes.ContentType'])),
            ('to_object_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('djangoratings', ['ScoreCorrelation'])

        # Deleting model 'SimilarUser'
        db.delete_table('djangoratings_similaruser')

        # Adding field 'Score.stddev'
        db.add_column('djangoratings_score', 'stddev', self.gf('django.db.models.fields.FloatField')(default=0.0), keep_default=False)

        # Adding field 'Score.mean'
        db.add_column('djangoratings_score', 'mean', self.gf('django.db.models.fields.FloatField')(default=0.0), keep_default=False)
    
    
    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            '_battlenet_profiles': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'battlenet_profiles'", 'blank': 'True'}),
            'avatar': ('django.db.models.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'bio': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'custom_title': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'gold': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_moderator': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'level': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'signature': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'xp': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'djangoratings.score': {
            'Meta': {'unique_together': "(('content_type', 'object_id', 'key'),)", 'object_name': 'Score'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'score': ('django.db.models.fields.IntegerField', [], {}),
            'votes': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'djangoratings.similaruser': {
            'Meta': {'unique_together': "(('from_user', 'to_user'),)", 'object_name': 'SimilarUser'},
            'agrees': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'disagrees': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'from_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'similar_users'", 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'to_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'similar_users_from'", 'to': "orm['auth.User']"})
        },
        'djangoratings.vote': {
            'Meta': {'unique_together': "(('content_type', 'object_id', 'key', 'user', 'ip_address'),)", 'object_name': 'Vote'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'votes'", 'to': "orm['contenttypes.ContentType']"}),
            'date_added': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'date_changed': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'score': ('django.db.models.fields.IntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'votes'", 'null': 'True', 'to': "orm['auth.User']"})
        }
    }
    
    complete_apps = ['djangoratings']

########NEW FILE########
__FILENAME__ = 0005_add_exclusions
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    
    def forwards(self, orm):
        
        # Adding model 'IgnoredObject'
        db.create_table('djangoratings_ignoredobject', (
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
        ))
        db.send_create_signal('djangoratings', ['IgnoredObject'])

        # Adding field 'SimilarUser.exclude'
        db.add_column('djangoratings_similaruser', 'exclude', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True), keep_default=False)
    
    
    def backwards(self, orm):
        
        # Deleting model 'IgnoredObject'
        db.delete_table('djangoratings_ignoredobject')

        # Deleting field 'SimilarUser.exclude'
        db.delete_column('djangoratings_similaruser', 'exclude')
    
    
    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            '_battlenet_profiles': ('django.db.models.fields.TextField', [], {'null': 'True', 'db_column': "'battlenet_profiles'", 'blank': 'True'}),
            'avatar': ('django.db.models.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'bio': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'custom_title': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'gold': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_moderator': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'level': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'signature': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'xp': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'djangoratings.ignoredobject': {
            'Meta': {'unique_together': "(('content_type', 'object_id'),)", 'object_name': 'IgnoredObject'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'djangoratings.score': {
            'Meta': {'unique_together': "(('content_type', 'object_id', 'key'),)", 'object_name': 'Score'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'score': ('django.db.models.fields.IntegerField', [], {}),
            'votes': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'djangoratings.similaruser': {
            'Meta': {'unique_together': "(('from_user', 'to_user'),)", 'object_name': 'SimilarUser'},
            'agrees': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'disagrees': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'exclude': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'from_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'similar_users'", 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'to_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'similar_users_from'", 'to': "orm['auth.User']"})
        },
        'djangoratings.vote': {
            'Meta': {'unique_together': "(('content_type', 'object_id', 'key', 'user', 'ip_address'),)", 'object_name': 'Vote'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'votes'", 'to': "orm['contenttypes.ContentType']"}),
            'date_added': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'date_changed': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'score': ('django.db.models.fields.IntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'votes'", 'null': 'True', 'to': "orm['auth.User']"})
        }
    }
    
    complete_apps = ['djangoratings']

########NEW FILE########
__FILENAME__ = 0006_add_cookies
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Removing unique constraint on 'Vote', fields ['key', 'ip_address', 'object_id', 'content_type', 'user']
        db.delete_unique('djangoratings_vote', ['key', 'ip_address', 'object_id', 'content_type_id', 'user_id'])

        # Adding field 'Vote.cookie'
        db.add_column('djangoratings_vote', 'cookie', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True), keep_default=False)

        # Adding unique constraint on 'Vote', fields ['content_type', 'object_id', 'cookie', 'user', 'key', 'ip_address']
        db.create_unique('djangoratings_vote', ['content_type_id', 'object_id', 'cookie', 'user_id', 'key', 'ip_address'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Vote', fields ['content_type', 'object_id', 'cookie', 'user', 'key', 'ip_address']
        db.delete_unique('djangoratings_vote', ['content_type_id', 'object_id', 'cookie', 'user_id', 'key', 'ip_address'])

        # Deleting field 'Vote.cookie'
        db.delete_column('djangoratings_vote', 'cookie')

        # Adding unique constraint on 'Vote', fields ['key', 'ip_address', 'object_id', 'content_type', 'user']
        db.create_unique('djangoratings_vote', ['key', 'ip_address', 'object_id', 'content_type_id', 'user_id'])


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
        'djangoratings.ignoredobject': {
            'Meta': {'unique_together': "(('content_type', 'object_id'),)", 'object_name': 'IgnoredObject'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'djangoratings.score': {
            'Meta': {'unique_together': "(('content_type', 'object_id', 'key'),)", 'object_name': 'Score'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'score': ('django.db.models.fields.IntegerField', [], {}),
            'votes': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'djangoratings.similaruser': {
            'Meta': {'unique_together': "(('from_user', 'to_user'),)", 'object_name': 'SimilarUser'},
            'agrees': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'disagrees': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'exclude': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'from_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'similar_users'", 'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'to_user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'similar_users_from'", 'to': "orm['auth.User']"})
        },
        'djangoratings.vote': {
            'Meta': {'unique_together': "(('content_type', 'object_id', 'key', 'user', 'ip_address', 'cookie'),)", 'object_name': 'Vote'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'votes'", 'to': "orm['contenttypes.ContentType']"}),
            'cookie': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'date_added': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'date_changed': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'score': ('django.db.models.fields.IntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'votes'", 'null': 'True', 'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['djangoratings']

########NEW FILE########
__FILENAME__ = models
from datetime import datetime

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.contrib.auth.models import User

try:
    from django.utils.timezone import now
except ImportError:
    now = datetime.now

from managers import VoteManager, SimilarUserManager

class Vote(models.Model):
    content_type    = models.ForeignKey(ContentType, related_name="votes")
    object_id       = models.PositiveIntegerField()
    key             = models.CharField(max_length=32)
    score           = models.IntegerField()
    user            = models.ForeignKey(User, blank=True, null=True, related_name="votes")
    ip_address      = models.IPAddressField()
    cookie          = models.CharField(max_length=32, blank=True, null=True)
    date_added      = models.DateTimeField(default=now, editable=False)
    date_changed    = models.DateTimeField(default=now, editable=False)

    objects         = VoteManager()

    content_object  = generic.GenericForeignKey()

    class Meta:
        unique_together = (('content_type', 'object_id', 'key', 'user', 'ip_address', 'cookie'))

    def __unicode__(self):
        return u"%s voted %s on %s" % (self.user_display, self.score, self.content_object)

    def save(self, *args, **kwargs):
        self.date_changed = now()
        super(Vote, self).save(*args, **kwargs)

    def user_display(self):
        if self.user:
            return "%s (%s)" % (self.user.username, self.ip_address)
        return self.ip_address
    user_display = property(user_display)

    def partial_ip_address(self):
        ip = self.ip_address.split('.')
        ip[-1] = 'xxx'
        return '.'.join(ip)
    partial_ip_address = property(partial_ip_address)

class Score(models.Model):
    content_type    = models.ForeignKey(ContentType)
    object_id       = models.PositiveIntegerField()
    key             = models.CharField(max_length=32)
    score           = models.IntegerField()
    votes           = models.PositiveIntegerField()
    
    content_object  = generic.GenericForeignKey()

    class Meta:
        unique_together = (('content_type', 'object_id', 'key'),)

    def __unicode__(self):
        return u"%s scored %s with %s votes" % (self.content_object, self.score, self.votes)

class SimilarUser(models.Model):
    from_user       = models.ForeignKey(User, related_name="similar_users")
    to_user         = models.ForeignKey(User, related_name="similar_users_from")
    agrees          = models.PositiveIntegerField(default=0)
    disagrees       = models.PositiveIntegerField(default=0)
    exclude         = models.BooleanField(default=False)
    
    objects         = SimilarUserManager()
    
    class Meta:
        unique_together = (('from_user', 'to_user'),)

    def __unicode__(self):
        print u"%s %s similar to %s" % (self.from_user, self.exclude and 'is not' or 'is', self.to_user)

class IgnoredObject(models.Model):
    user            = models.ForeignKey(User)
    content_type    = models.ForeignKey(ContentType)
    object_id       = models.PositiveIntegerField()
    
    content_object  = generic.GenericForeignKey()
    
    class Meta:
        unique_together = (('content_type', 'object_id'),)
    
    def __unicode__(self):
        return self.content_object
########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import sys

from os.path import dirname, abspath

from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASE_ENGINE='sqlite3',
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'djangoratings',
        ]
    )

from django.test.simple import run_tests


def runtests(*test_args):
    if not test_args:
        test_args = ['djangoratings']
    parent = dirname(abspath(__file__))
    sys.path.insert(0, parent)
    failures = run_tests(test_args, verbosity=1, interactive=True)
    sys.exit(failures)


if __name__ == '__main__':
    runtests(*sys.argv[1:])
########NEW FILE########
__FILENAME__ = ratings
"""
Template tags for Django
"""
# TODO: add in Jinja tags if Coffin is available

from django import template
from django.contrib.contenttypes.models import ContentType
from django.db.models import ObjectDoesNotExist

from djangoratings.models import Vote

register = template.Library()

class RatingByRequestNode(template.Node):
    def __init__(self, request, obj, context_var):
        self.request = request
        self.obj, self.field_name = obj.split('.')
        self.context_var = context_var
    
    def render(self, context):
        try:
            request = template.resolve_variable(self.request, context)
            obj = template.resolve_variable(self.obj, context)
            field = getattr(obj, self.field_name)
        except (template.VariableDoesNotExist, AttributeError):
            return ''
        try:
            vote = field.get_rating_for_user(request.user, request.META['REMOTE_ADDR'], request.COOKIES)
            context[self.context_var] = vote
        except ObjectDoesNotExist:
            context[self.context_var] = 0
        return ''

def do_rating_by_request(parser, token):
    """
    Retrieves the ``Vote`` cast by a user on a particular object and
    stores it in a context variable. If the user has not voted, the
    context variable will be 0.
    
    Example usage::
    
        {% rating_by_request request on instance as vote %}
    """
    
    bits = token.contents.split()
    if len(bits) != 6:
        raise template.TemplateSyntaxError("'%s' tag takes exactly five arguments" % bits[0])
    if bits[2] != 'on':
        raise template.TemplateSyntaxError("second argument to '%s' tag must be 'on'" % bits[0])
    if bits[4] != 'as':
        raise template.TemplateSyntaxError("fourth argument to '%s' tag must be 'as'" % bits[0])
    return RatingByRequestNode(bits[1], bits[3], bits[5])
register.tag('rating_by_request', do_rating_by_request)

class RatingByUserNode(RatingByRequestNode):
    def render(self, context):
        try:
            user = template.resolve_variable(self.request, context)
            obj = template.resolve_variable(self.obj, context)
            field = getattr(obj, self.field_name)
        except template.VariableDoesNotExist:
            return ''
        try:
            vote = field.get_rating_for_user(user)
            context[self.context_var] = vote
        except ObjectDoesNotExist:
            context[self.context_var] = 0
        return ''

def do_rating_by_user(parser, token):
    """
    Retrieves the ``Vote`` cast by a user on a particular object and
    stores it in a context variable. If the user has not voted, the
    context variable will be 0.
    
    Example usage::
    
        {% rating_by_user user on instance as vote %}
    """
    
    bits = token.contents.split()
    if len(bits) != 6:
        raise template.TemplateSyntaxError("'%s' tag takes exactly five arguments" % bits[0])
    if bits[2] != 'on':
        raise template.TemplateSyntaxError("second argument to '%s' tag must be 'on'" % bits[0])
    if bits[4] != 'as':
        raise template.TemplateSyntaxError("fourth argument to '%s' tag must be 'as'" % bits[0])
    return RatingByUserNode(bits[1], bits[3], bits[5])
register.tag('rating_by_user', do_rating_by_user)

########NEW FILE########
__FILENAME__ = tests
import unittest
import random

from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.conf import settings

from exceptions import *
from models import Vote, SimilarUser, IgnoredObject
from fields import AnonymousRatingField, RatingField

settings.RATINGS_VOTES_PER_IP = 1

class RatingTestModel(models.Model):
    rating = AnonymousRatingField(range=2, can_change_vote=True)
    rating2 = RatingField(range=2, can_change_vote=False)
    
    def __unicode__(self):
        return unicode(self.pk)

class RatingTestCase(unittest.TestCase):
    def testRatings(self):
        instance = RatingTestModel.objects.create()
        
        # Test adding votes
        instance.rating.add(score=1, user=None, ip_address='127.0.0.1')
        self.assertEquals(instance.rating.score, 1)
        self.assertEquals(instance.rating.votes, 1)

        # Test adding votes
        instance.rating.add(score=2, user=None, ip_address='127.0.0.2')
        self.assertEquals(instance.rating.score, 3)
        self.assertEquals(instance.rating.votes, 2)

        # Test changing of votes
        instance.rating.add(score=2, user=None, ip_address='127.0.0.1')
        self.assertEquals(instance.rating.score, 4)
        self.assertEquals(instance.rating.votes, 2)
        
        # Test users
        user = User.objects.create(username=str(random.randint(0, 100000000)))
        user2 = User.objects.create(username=str(random.randint(0, 100000000)))
        
        instance.rating.add(score=2, user=user, ip_address='127.0.0.3')
        self.assertEquals(instance.rating.score, 6)
        self.assertEquals(instance.rating.votes, 3)
        
        instance.rating2.add(score=2, user=user, ip_address='127.0.0.3')
        self.assertEquals(instance.rating2.score, 2)
        self.assertEquals(instance.rating2.votes, 1)
        
        self.assertRaises(IPLimitReached, instance.rating2.add, score=2, user=user2, ip_address='127.0.0.3')

        # Test deletion hooks
        Vote.objects.filter(ip_address='127.0.0.3').delete()
        
        instance = RatingTestModel.objects.get(pk=instance.pk)

        self.assertEquals(instance.rating.score, 4)
        self.assertEquals(instance.rating.votes, 2)
        self.assertEquals(instance.rating2.score, 0)
        self.assertEquals(instance.rating2.votes, 0)

class RecommendationsTestCase(unittest.TestCase):
    def setUp(self):
        self.instance = RatingTestModel.objects.create()
        self.instance2 = RatingTestModel.objects.create()
        self.instance3 = RatingTestModel.objects.create()
        self.instance4 = RatingTestModel.objects.create()
        self.instance5 = RatingTestModel.objects.create()
        
        # Test users
        self.user = User.objects.create(username=str(random.randint(0, 100000000)))
        self.user2 = User.objects.create(username=str(random.randint(0, 100000000)))
    
    def testExclusions(self):
        Vote.objects.all().delete()

        self.instance.rating.add(score=1, user=self.user, ip_address='127.0.0.1')
        self.instance2.rating.add(score=1, user=self.user, ip_address='127.0.0.1')
        self.instance3.rating.add(score=1, user=self.user, ip_address='127.0.0.1')
        self.instance4.rating.add(score=1, user=self.user, ip_address='127.0.0.1')
        self.instance5.rating.add(score=1, user=self.user, ip_address='127.0.0.1')
        self.instance.rating.add(score=1, user=self.user2, ip_address='127.0.0.2')

        # we should only need to call this once
        SimilarUser.objects.update_recommendations()

        self.assertEquals(SimilarUser.objects.count(), 2)

        recs = list(SimilarUser.objects.get_recommendations(self.user2, RatingTestModel))
        self.assertEquals(len(recs), 4)
        
        ct = ContentType.objects.get_for_model(RatingTestModel)
        
        IgnoredObject.objects.create(user=self.user2, content_type=ct, object_id=self.instance2.pk)

        recs = list(SimilarUser.objects.get_recommendations(self.user2, RatingTestModel))
        self.assertEquals(len(recs), 3)

        IgnoredObject.objects.create(user=self.user2, content_type=ct, object_id=self.instance3.pk)
        IgnoredObject.objects.create(user=self.user2, content_type=ct, object_id=self.instance4.pk)

        recs = list(SimilarUser.objects.get_recommendations(self.user2, RatingTestModel))
        self.assertEquals(len(recs), 1)
        self.assertEquals(recs, [self.instance5])
        
        self.instance5.rating.add(score=1, user=self.user2, ip_address='127.0.0.2')
        recs = list(SimilarUser.objects.get_recommendations(self.user2, RatingTestModel))
        self.assertEquals(len(recs), 0)
    
    def testSimilarUsers(self):
        Vote.objects.all().delete()

        self.instance.rating.add(score=1, user=self.user, ip_address='127.0.0.1')
        self.instance2.rating.add(score=1, user=self.user, ip_address='127.0.0.1')
        self.instance3.rating.add(score=1, user=self.user, ip_address='127.0.0.1')
        self.instance4.rating.add(score=1, user=self.user, ip_address='127.0.0.1')
        self.instance5.rating.add(score=1, user=self.user, ip_address='127.0.0.1')
        self.instance.rating.add(score=1, user=self.user2, ip_address='127.0.0.2')
        self.instance2.rating.add(score=1, user=self.user2, ip_address='127.0.0.2')
        self.instance3.rating.add(score=1, user=self.user2, ip_address='127.0.0.2')
        
        SimilarUser.objects.update_recommendations()

        self.assertEquals(SimilarUser.objects.count(), 2)

        recs = list(SimilarUser.objects.get_recommendations(self.user2, RatingTestModel))
        self.assertEquals(len(recs), 2)
        
        self.instance4.rating.add(score=1, user=self.user2, ip_address='127.0.0.2')

        SimilarUser.objects.update_recommendations()

        self.assertEquals(SimilarUser.objects.count(), 2)

        recs = list(SimilarUser.objects.get_recommendations(self.user2, RatingTestModel))
        self.assertEquals(len(recs), 1)
        self.assertEquals(recs, [self.instance5])
        
        self.instance5.rating.add(score=1, user=self.user2, ip_address='127.0.0.2')

        SimilarUser.objects.update_recommendations()

        self.assertEquals(SimilarUser.objects.count(), 2)

        recs = list(SimilarUser.objects.get_recommendations(self.user2, RatingTestModel))
        self.assertEquals(len(recs), 0)
########NEW FILE########
__FILENAME__ = views
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, Http404

from exceptions import *
from django.conf import settings
from default_settings import RATINGS_VOTES_PER_IP

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
        
        had_voted = bool(field.get_rating_for_user(request.user, request.META['REMOTE_ADDR'], request.COOKIES))
        
        context['had_voted'] = had_voted
                    
        try:
            adds = field.add(score, request.user, request.META.get('REMOTE_ADDR'), request.COOKIES)
        except IPLimitReached:
            return self.too_many_votes_from_ip_response(request, context)
        except AuthRequired:
            return self.authentication_required_response(request, context)
        except InvalidRating:
            return self.invalid_rating_response(request, context)
        except CannotChangeVote:
            return self.cannot_change_vote_response(request, context)
        except CannotDeleteVote:
            return self.cannot_delete_vote_response(request, context)
        if had_voted:
            return self.rating_changed_response(request, context, adds)
        return self.rating_added_response(request, context, adds)
    
    def get_context(self, request, context={}):
        return context
    
    def render_to_response(self, template, context, request):
        raise NotImplementedError

    def too_many_votes_from_ip_response(self, request, context):
        response = HttpResponse('Too many votes from this IP address for this object.')
        return response

    def rating_changed_response(self, request, context, adds={}):
        response = HttpResponse('Vote changed.')
        if 'cookie' in adds:
            cookie_name, cookie = adds['cookie_name'], adds['cookie']
            if 'deleted' in adds:
                response.delete_cookie(cookie_name)
            else:
                response.set_cookie(cookie_name, cookie, 31536000, path='/') # TODO: move cookie max_age to settings
        return response
    
    def rating_added_response(self, request, context, adds={}):
        response = HttpResponse('Vote recorded.')
        if 'cookie' in adds:
            cookie_name, cookie = adds['cookie_name'], adds['cookie']
            if 'deleted' in adds:
                response.delete_cookie(cookie_name)
            else:
                response.set_cookie(cookie_name, cookie, 31536000, path='/') # TODO: move cookie max_age to settings
        return response

    def authentication_required_response(self, request, context):
        response = HttpResponse('You must be logged in to vote.')
        response.status_code = 403
        return response
    
    def cannot_change_vote_response(self, request, context):
        response = HttpResponse('You have already voted.')
        response.status_code = 403
        return response
    
    def cannot_delete_vote_response(self, request, context):
        response = HttpResponse('You can\'t delete this vote.')
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
    def __call__(self, request, model, app_label, object_id, field_name, score):
        """__call__(request, model, app_label, object_id, field_name, score)
        
        Adds a vote to the specified model field."""
        try:
            content_type = ContentType.objects.get(model=model, app_label=app_label)
        except ContentType.DoesNotExist:
            raise Http404('Invalid `model` or `app_label`.')
        
        return super(AddRatingFromModel, self).__call__(request, content_type.id,
                                                        object_id, field_name, score)

########NEW FILE########
