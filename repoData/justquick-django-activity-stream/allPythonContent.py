__FILENAME__ = actions
import datetime

from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from actstream.exceptions import check_actionable_model
from actstream import settings

try:
    from django.utils import timezone
    now = timezone.now
except ImportError:
    now = datetime.datetime.now


def follow(user, obj, send_action=True, actor_only=True):
    """
    Creates a relationship allowing the object's activities to appear in the
    user's stream.

    Returns the created ``Follow`` instance.

    If ``send_action`` is ``True`` (the default) then a
    ``<user> started following <object>`` action signal is sent.

    If ``actor_only`` is ``True`` (the default) then only actions where the
    object is the actor will appear in the user's activity stream. Set to
    ``False`` to also include actions where this object is the action_object or
    the target.

    Example::

        follow(request.user, group, actor_only=False)
    """
    from actstream.models import Follow, action

    check_actionable_model(obj)
    follow, created = Follow.objects.get_or_create(user=user,
        object_id=obj.pk,
        content_type=ContentType.objects.get_for_model(obj),
        actor_only=actor_only)
    if send_action and created:
        action.send(user, verb=_('started following'), target=obj)
    return follow


def unfollow(user, obj, send_action=False):
    """
    Removes a "follow" relationship.

    Set ``send_action`` to ``True`` (``False is default) to also send a
    ``<user> stopped following <object>`` action signal.

    Example::

        unfollow(request.user, other_user)
    """
    from actstream.models import Follow, action

    check_actionable_model(obj)
    Follow.objects.filter(user=user, object_id=obj.pk,
        content_type=ContentType.objects.get_for_model(obj)).delete()
    if send_action:
        action.send(user, verb=_('stopped following'), target=obj)


def is_following(user, obj):
    """
    Checks if a "follow" relationship exists.

    Returns True if exists, False otherwise.

    Example::

        is_following(request.user, group)
    """
    from actstream.models import Follow

    check_actionable_model(obj)
    return bool(Follow.objects.filter(user=user, object_id=obj.pk,
        content_type=ContentType.objects.get_for_model(obj)).count())


def action_handler(verb, **kwargs):
    """
    Handler function to create Action instance upon action signal call.
    """
    from actstream.models import Action

    kwargs.pop('signal', None)
    actor = kwargs.pop('sender')
    check_actionable_model(actor)

    # We must store the unstranslated string
    # If verb is an ugettext_lazyed string, fetch the original string
    if hasattr(verb, '_proxy____args'):
        verb = verb._proxy____args[0]

    newaction = Action(
        actor_content_type=ContentType.objects.get_for_model(actor),
        actor_object_id=actor.pk,
        verb=unicode(verb),
        public=bool(kwargs.pop('public', True)),
        description=kwargs.pop('description', None),
        timestamp=kwargs.pop('timestamp', now())
    )

    for opt in ('target', 'action_object'):
        obj = kwargs.pop(opt, None)
        if not obj is None:
            check_actionable_model(obj)
            setattr(newaction, '%s_object_id' % opt, obj.pk)
            setattr(newaction, '%s_content_type' % opt,
                    ContentType.objects.get_for_model(obj))
    if settings.USE_JSONFIELD and len(kwargs):
        newaction.data = kwargs
    newaction.save()

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from actstream import models


class ActionAdmin(admin.ModelAdmin):
    date_hierarchy = 'timestamp'
    list_display = ('__unicode__', 'actor', 'verb', 'target')
    list_editable = ('verb',)
    list_filter = ('timestamp',)
    raw_id_fields = ('actor_content_type','target_content_type',
                     'action_object_content_type')


class FollowAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'user', 'follow_object', 'actor_only', 'started')
    list_editable = ('user',)
    list_filter = ('user', 'started',)
    raw_id_fields = ('user', 'content_type')


admin.site.register(models.Action, ActionAdmin)
admin.site.register(models.Follow, FollowAdmin)

########NEW FILE########
__FILENAME__ = compat
from django.conf import settings


# Django 1.5 compatibility utilities, providing support for custom User models.
# Since get_user_model() causes a circular import if called when app models are
# being loaded, the user_model_label should be used when possible, with calls
# to get_user_model deferred to execution time

user_model_label = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')

try:
    from django.contrib.auth import get_user_model
except ImportError:
    from django.contrib.auth.models import User
    get_user_model = lambda: User

try:
    from django.utils.encoding import smart_text
except ImportError:
    from django.utils.encoding import smart_unicode as smart_text

########NEW FILE########
__FILENAME__ = decorators
from functools import wraps


def stream(func):
    """
    Stream decorator to be applied to methods of an ``ActionManager`` subclass

    Syntax::

        from actstream.decorators import stream
        from actstream.managers import ActionManager

        class MyManager(ActionManager):
            @stream
            def foobar(self, ...):
                ...

    """
    @wraps(func)
    def wrapped(manager, *args, **kwargs):
        offset, limit = kwargs.pop('_offset', None), kwargs.pop('_limit', None)
        try:
            return func(manager, *args, **kwargs)[offset:limit]\
                .fetch_generic_relations()
        except AttributeError:
            return func(manager, *args, **kwargs).fetch_generic_relations()
    return wrapped

########NEW FILE########
__FILENAME__ = exceptions
from django.db.models.base import ModelBase
from django.core.exceptions import ImproperlyConfigured

from actstream.settings import get_models


class ModelNotActionable(ImproperlyConfigured):
    """
    Raised when a Model not in ``ACTSTREAM_ACTION_MODELS`` setting is used in
    an Action.
    """

    def __str__(self):
        model = self.args[0]
        if not is_model(model):
            return 'Object %r must be a Django Model not %s' % (model,
                type(model))
        opts = model._meta
        return 'Model %s not recognized, add "%s.%s" to the ACTSTREAM_SETTINGS["MODELS"] settings' % (
            model.__name__, opts.app_label, opts.module_name)


class BadQuerySet(ValueError):
    """
    Action stream must return a QuerySet of Action items.
    """

def is_model(obj):
    """
    Returns True if the obj is a Django model
    """
    if not hasattr(obj, '_meta'):
        return False
    if not hasattr(obj._meta, 'db_table'):
        return False
    return True

def check_actionable_model(model):
    """
    If the model is not defined in the ``MODELS`` setting this check raises the
    ``ModelNotActionable`` exception.
    """
    model = model if hasattr(model, 'objects') else model.__class__
    if not model in get_models().values():
        raise ModelNotActionable(model)

########NEW FILE########
__FILENAME__ = feeds
from django.shortcuts import get_object_or_404
from django.core.urlresolvers import reverse
from django.utils.feedgenerator import Atom1Feed, rfc3339_date, get_tag_uri
from django.contrib.contenttypes.models import ContentType

try:
    from django.contrib.syndication.views import Feed
except ImportError:   # Pre 1.2
    from django.contrib.syndication.feeds import Feed

from actstream.models import model_stream, user_stream, action_object_stream


class AtomWithContentFeed(Atom1Feed):

    def add_item_elements(self, handler, item):
        super(AtomWithContentFeed, self).add_item_elements(handler, item)
        if 'content' in item:
            handler.addQuickElement(u"content", item['content'],
                {'type': 'html'})


class ObjectActivityFeed(Feed):
    """
    Feed of Activity for a given object (where the object is the Object or
    Target).
    """

    def get_object(self, request, content_type_id, object_id):
        return get_object_or_404(ContentType, pk=content_type_id)\
            .get_object_for_this_type(pk=object_id)

    def title(self, obj):
        return 'Activity for %s' % obj

    def link(self, obj):
        if hasattr(obj, 'get_absolute_url'):
            return obj.get_absolute_url()
        return reverse('actstream_actor', None,
                    (ContentType.objects.get_for_model(obj).pk, obj.pk))

    def description(self, obj):
        return 'Activity for %s' % obj

    def items(self, obj):
        i = action_object_stream(obj)
        if i:
            return i[:30]
        return []

    def item_extra_kwargs(self, obj):
        return  {
            'content': obj.description,
        }


class AtomObjectActivityFeed(ObjectActivityFeed):
    feed_type = AtomWithContentFeed
    subtitle = ObjectActivityFeed.description


class ActivityStreamsFeed(AtomWithContentFeed):
    """
    Custom feed generator for Activity Stream feeds
    """

    def root_attributes(self):
        attrs = super(ActivityStreamsFeed, self).root_attributes()
        attrs['xmlns: activity'] = 'http: //activitystrea.ms/spec/1.0/'
        return attrs

    def add_root_elements(self, handler):
        super(ActivityStreamsFeed, self).add_root_elements(handler)

    def add_item_elements(self, handler, item):
        super(ActivityStreamsFeed, self).add_item_elements(handler, item)
        handler.addQuickElement(u"activity: verb", item['verb'])

        if 'actor' in item:
            handler.startElement('author', {})
            handler.addQuickElement('name', item['actor'].display_name)
            handler.addQuickElement('uri', get_tag_uri(
                item['actor'].get_absolute_url(), None))
            handler.addQuickElement('id', item['actor'].get_absolute_url())
            handler.addQuickElement('activity: object-type', 'person')
            handler.addQuickElement('link', get_tag_uri(
                item['actor'].get_absolute_url(), None), {'type': 'text/html'})
            handler.endElement('author')

        if 'object' in item:
            handler.startElement('activity: object', {})
            handler.addQuickElement('id', item['object_id'])
            handler.addQuickElement('title', item['object_title'])
            handler.addQuickElement('published',
                rfc3339_date(item['object_timestamp']).decode('utf-8'))
            handler.addQuickElement('link', item['object'].get_absolute_url(),
                {'type': 'text/html'})
            handler.addQuickElement('activity: object-type',
                item['object_object_type'])
            handler.endElement('activity: object')

        if 'target' in item:
            handler.startElement('activity: target', {})
            handler.addQuickElement('id', item['target_id'])
            handler.addQuickElement('title', item['target_title'])
            handler.addQuickElement('activity: object-type',
                str(item['target_object_type']))
            handler.endElement('activity: target')


class ActivityStreamsObjectActivityFeed(AtomObjectActivityFeed):
    feed_type = ActivityStreamsFeed

    def feed_extra_kwargs(self, obj):
        """
        Returns an extra keyword arguments dictionary that is used when
        initializing the feed generator.
        """
        return {}

    def item_extra_kwargs(self, obj):
        """
        Returns an extra keyword arguments dictionary that is used with
        the `add_item` call of the feed generator.
        Add the 'content' field of the 'Entry' item, to be used by the custom
        feed generator.
        """
        try:
            object_id = obj.action_object.get_absolute_url()
        except:
            object_id = '%s/%s' % (obj.action_object_content_type.model,
                obj.action_object.id)

        object_id = get_tag_uri(object_id, None)

        item = {
            'content': obj.description,
            'actor': obj.actor,
            'verb': obj.verb_uri_prefix + obj.verb,
            # action object
            'object_timestamp': obj.timestamp,
            'object': obj.action_object,
            'object_id': object_id,
            'object_title': unicode(obj.action_object),
            'object_object_type': obj.action_object_content_type.model,
        }

        if obj.target:
            try:
                target_id = obj.target.get_absolute_url()
            except Exception:
                target_id = '%s/%s' % (obj.target_content_type.model,
                    obj.action_object.id)

            target_id = get_tag_uri(target_id, obj.timestamp)

            item['target'] = obj.target
            item['target_id'] = target_id
            item['target_title'] = unicode(obj.target)
            item['target_object_type'] = obj.target_content_type.name

        return item


class ModelActivityFeed(Feed):

    def get_object(self, request, content_type_id):
        return get_object_or_404(ContentType, pk=content_type_id).model_class()

    def title(self, model):
        return 'Activity feed from %s' % model

    def link(self, model):
        return reverse('actstream_model', None,
                (ContentType.objects.get_for_model(model).pk,))

    def description(self, model):
        return 'Public activities of %s' % model

    def items(self, model):
        i = model_stream(model)
        if i:
            return i[:30]
        return []


class AtomModelActivityFeed(ModelActivityFeed):
    feed_type = Atom1Feed
    subtitle = ModelActivityFeed.description


class UserActivityFeed(Feed):

    def get_object(self, request):
        if request.user.is_authenticated():
            return request.user

    def title(self, user):
        return 'Activity feed for your followed actors'

    def link(self, user):
        if not user:
            return reverse('actstream')
        if hasattr(user, 'get_absolute_url'):
            return user.get_absolute_url()
        return reverse('actstream_actor', None,
            (ContentType.objects.get_for_model(user).pk, user.pk))

    def description(self, user):
        return 'Public activities of actors you follow'

    def items(self, user):
        i = user_stream(user)
        if i:
            return i[:30]
        return []


class AtomUserActivityFeed(UserActivityFeed):
    feed_type = Atom1Feed
    subtitle = UserActivityFeed.description

########NEW FILE########
__FILENAME__ = gfk
from django.db.models import Manager
from django.db.models.query import QuerySet, EmptyQuerySet

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey

from actstream.compat import smart_text


class GFKManager(Manager):
    """
    A manager that returns a GFKQuerySet instead of a regular QuerySet.

    """
    def get_query_set(self):
        return GFKQuerySet(self.model)

    def none(self):
        return self.get_query_set().none()


class GFKQuerySet(QuerySet):
    """
    A QuerySet with a fetch_generic_relations() method to bulk fetch
    all generic related items.  Similar to select_related(), but for
    generic foreign keys.

    Based on http://www.djangosnippets.org/snippets/984/
    Firstly improved at http://www.djangosnippets.org/snippets/1079/

    Extended in django-activity-stream to allow for multi db, text primary keys
    and empty querysets.
    """
    def fetch_generic_relations(self, *args):
        from actstream import settings as actstream_settings

        qs = self._clone()

        if not actstream_settings.FETCH_RELATIONS:
            return qs

        gfk_fields = [g for g in self.model._meta.virtual_fields
                      if isinstance(g, GenericForeignKey)]

        if args:
            gfk_fields = filter(lambda g: g.name in args, gfk_fields)

        if actstream_settings.USE_PREFETCH and hasattr(self, 'prefetch_related'):
            return qs.prefetch_related(*[g.name for g in gfk_fields])

        ct_map, data_map = {}, {}

        for item in qs:
            for gfk in gfk_fields:
                if getattr(item, gfk.fk_field) is None:
                    continue
                ct_id_field = self.model._meta.get_field(gfk.ct_field).column
                if getattr(item, ct_id_field) is None:
                    continue
                ct_map.setdefault(getattr(item, ct_id_field), {}
                    )[smart_text(getattr(item, gfk.fk_field))] = (gfk.name,
                        item.pk)

        ctypes = ContentType.objects.in_bulk(ct_map.keys())

        for ct_id, items_ in ct_map.items():
            if ct_id:
                ct = ctypes[ct_id]
                model_class = ct.model_class()
                objects = model_class._default_manager.select_related(
                    depth=actstream_settings.GFK_FETCH_DEPTH)
                for o in objects.filter(pk__in=items_.keys()):
                    (gfk_name, item_id) = items_[smart_text(o.pk)]
                    data_map[(ct_id, smart_text(o.pk))] = o

        for item in qs:
            for gfk in gfk_fields:
                try:
                    if getattr(item, gfk.fk_field) is not None:
                        ct_id_field = self.model._meta.get_field(gfk.ct_field)\
                            .column
                        setattr(item, gfk.name,
                            data_map[(
                                getattr(item, ct_id_field),
                                smart_text(getattr(item, gfk.fk_field))
                            )])
                except KeyError:
                    continue

        return qs

    def none(self):
        return self._clone(klass=EmptyGFKQuerySet)


class EmptyGFKQuerySet(GFKQuerySet, EmptyQuerySet):
    def fetch_generic_relations(self):
        return self

########NEW FILE########
__FILENAME__ = managers
from collections import defaultdict

from django.db.models import get_model
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType

from actstream.gfk import GFKManager
from actstream.decorators import stream


class ActionManager(GFKManager):
    """
    Default manager for Actions, accessed through Action.objects
    """

    def public(self, *args, **kwargs):
        """
        Only return public actions
        """
        kwargs['public'] = True
        return self.filter(*args, **kwargs)

    @stream
    def actor(self, object, **kwargs):
        """
        Stream of most recent actions where object is the actor.
        Keyword arguments will be passed to Action.objects.filter
        """
        return object.actor_actions.public(**kwargs)

    @stream
    def target(self, object, **kwargs):
        """
        Stream of most recent actions where object is the target.
        Keyword arguments will be passed to Action.objects.filter
        """
        return object.target_actions.public(**kwargs)

    @stream
    def action_object(self, object, **kwargs):
        """
        Stream of most recent actions where object is the action_object.
        Keyword arguments will be passed to Action.objects.filter
        """
        return object.action_object_actions.public(**kwargs)

    @stream
    def model_actions(self, model, **kwargs):
        """
        Stream of most recent actions by any particular model
        """
        ctype = ContentType.objects.get_for_model(model)
        return self.public(
            (Q(target_content_type=ctype) |
            Q(action_object_content_type=ctype) |
            Q(actor_content_type=ctype)),
            **kwargs
        )

    @stream
    def user(self, object, **kwargs):
        """
        Stream of most recent actions by objects that the passed User object is
        following.
        """
        q = Q()
        qs = self.filter(public=True)
        actors_by_content_type = defaultdict(lambda: [])
        others_by_content_type = defaultdict(lambda: [])

        follow_gfks = get_model('actstream', 'follow').objects.filter(
            user=object).values_list('content_type_id',
                                     'object_id', 'actor_only')

        if not follow_gfks:
            return qs.none()

        for content_type_id, object_id, actor_only in follow_gfks.iterator():
            actors_by_content_type[content_type_id].append(object_id)
            if not actor_only:
                others_by_content_type[content_type_id].append(object_id)

        for content_type_id, object_ids in actors_by_content_type.iteritems():
            q = q | Q(
                actor_content_type=content_type_id,
                actor_object_id__in=object_ids,
            )
        for content_type_id, object_ids in others_by_content_type.iteritems():
            q = q | Q(
                target_content_type=content_type_id,
                target_object_id__in=object_ids,
            ) | Q(
                action_object_content_type=content_type_id,
                action_object_object_id__in=object_ids,
            )
        qs = qs.filter(q, **kwargs)
        return qs


class FollowManager(GFKManager):
    """
    Manager for Follow model.
    """

    def for_object(self, instance):
        """
        Filter to a specific instance.
        """
        content_type = ContentType.objects.get_for_model(instance).pk
        return self.filter(content_type=content_type, object_id=instance.pk)

    def is_following(self, user, instance):
        """
        Check if a user is following an instance.
        """
        if not user or user.is_anonymous():
            return False
        queryset = self.for_object(instance)
        return queryset.filter(user=user).exists()

    def followers(self, actor):
        """
        Returns a list of User objects who are following the given actor (eg my followers).
        """
        return [follow.user for follow in self.filter(
            content_type=ContentType.objects.get_for_model(actor),
            object_id=actor.pk
        ).select_related('user')]

    def following(self, user, *models):
        """
        Returns a list of actors that the given user is following (eg who im following).
        Items in the list can be of any model unless a list of restricted models are passed.
        Eg following(user, User) will only return users following the given user
        """
        qs = self.filter(user=user)
        if len(models):
            qs = qs.filter(content_type__in=(
                ContentType.objects.get_for_model(model) for model in models)
            )
        return [follow.follow_object for follow in qs.fetch_generic_relations()]

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

from actstream.compat import user_model_label


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding model 'Follow'
        db.create_table('actstream_follow', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm[user_model_label])),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('actstream', ['Follow'])

        # Adding unique constraint on 'Follow', fields ['user', 'content_type', 'object_id']
        db.create_unique('actstream_follow', ['user_id', 'content_type_id', 'object_id'])

        # Adding model 'Action'
        db.create_table('actstream_action', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('actor_content_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='actor', to=orm['contenttypes.ContentType'])),
            ('actor_object_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('verb', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('target_content_type', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='target', null=True, to=orm['contenttypes.ContentType'])),
            ('target_object_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('action_object_content_type', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='action_object', null=True, to=orm['contenttypes.ContentType'])),
            ('action_object_object_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('public', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('actstream', ['Action'])


    def backwards(self, orm):

        # Removing unique constraint on 'Follow', fields ['user', 'content_type', 'object_id']
        db.delete_unique('actstream_follow', ['user_id', 'content_type_id', 'object_id'])

        # Deleting model 'Follow'
        db.delete_table('actstream_follow')

        # Deleting model 'Action'
        db.delete_table('actstream_action')


    models = {
        'actstream.action': {
            'Meta': {'object_name': 'Action'},
            'action_object_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'action_object'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'action_object_object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'actor_content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'actor'", 'to': "orm['contenttypes.ContentType']"}),
            'actor_object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'target_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'target'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'target_object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'verb': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'actstream.follow': {
            'Meta': {'unique_together': "(('user', 'content_type', 'object_id'),)", 'object_name': 'Follow'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s']" % user_model_label})
        },
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
        user_model_label: {
            'Meta': {'object_name': user_model_label.split('.')[-1]},
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
        }
    }

    complete_apps = ['actstream']

########NEW FILE########
__FILENAME__ = 0002_auto__chg_field_action_timestamp
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

from actstream.compat import user_model_label


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Action.timestamp'
        db.alter_column('actstream_action', 'timestamp', self.gf('django.db.models.fields.DateTimeField')())


    def backwards(self, orm):

        # Changing field 'Action.timestamp'
        db.alter_column('actstream_action', 'timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True))


    models = {
        'actstream.action': {
            'Meta': {'object_name': 'Action'},
            'action_object_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'action_object'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'action_object_object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'actor_content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'actor'", 'to': "orm['contenttypes.ContentType']"}),
            'actor_object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'target_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'target'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'target_object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'verb': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'actstream.follow': {
            'Meta': {'unique_together': "(('user', 'content_type', 'object_id'),)", 'object_name': 'Follow'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s']" % user_model_label})
        },
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
        user_model_label: {
            'Meta': {'object_name': user_model_label.split('.')[-1]},
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
        }
    }

    complete_apps = ['actstream']

########NEW FILE########
__FILENAME__ = 0003_text_field_ids
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

from actstream.compat import user_model_label

class Migration(SchemaMigration):

    def forwards(self, orm):
        pass

    def backwards(self, orm):
        pass

    models = {
        'actstream.action': {
            'Meta': {'object_name': 'Action'},
            'action_object_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'action_object'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'action_object_object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'actor_content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'actor'", 'to': "orm['contenttypes.ContentType']"}),
            'actor_object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'target_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'target'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'target_object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'verb': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'actstream.follow': {
            'Meta': {'unique_together': "(('user', 'content_type', 'object_id'),)", 'object_name': 'Follow'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s']" % user_model_label})
        },
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
        user_model_label: {
            'Meta': {'object_name': user_model_label.split('.')[-1]},
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
        }
    }

    complete_apps = ['actstream']

########NEW FILE########
__FILENAME__ = 0004_char_field_ids
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

from actstream.compat import user_model_label

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Follow.object_id'
        db.alter_column('actstream_follow', 'object_id', self.gf('django.db.models.fields.CharField')(max_length=255))

        # Changing field 'Action.action_object_object_id'
        db.alter_column('actstream_action', 'action_object_object_id', self.gf('django.db.models.fields.CharField')(max_length=255, null=True))

        # Changing field 'Action.actor_object_id'
        db.alter_column('actstream_action', 'actor_object_id', self.gf('django.db.models.fields.CharField')(max_length=255))

        # Changing field 'Action.target_object_id'
        db.alter_column('actstream_action', 'target_object_id', self.gf('django.db.models.fields.CharField')(max_length=255, null=True))


    def backwards(self, orm):

        # Changing field 'Follow.object_id'
        db.alter_column('actstream_follow', 'object_id', self.gf('django.db.models.fields.PositiveIntegerField')())

        # Changing field 'Action.action_object_object_id'
        db.alter_column('actstream_action', 'action_object_object_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True))

        # Changing field 'Action.actor_object_id'
        db.alter_column('actstream_action', 'actor_object_id', self.gf('django.db.models.fields.PositiveIntegerField')())

        # Changing field 'Action.target_object_id'
        db.alter_column('actstream_action', 'target_object_id', self.gf('django.db.models.fields.PositiveIntegerField')(null=True))


    models = {
        'actstream.action': {
            'Meta': {'ordering': "('-timestamp',)", 'object_name': 'Action'},
            'action_object_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'action_object'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'action_object_object_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'actor_content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'actor'", 'to': "orm['contenttypes.ContentType']"}),
            'actor_object_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'target_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'target'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'target_object_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'verb': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'actstream.follow': {
            'Meta': {'unique_together': "(('user', 'content_type', 'object_id'),)", 'object_name': 'Follow'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s']" % user_model_label})
        },
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
        user_model_label: {
            'Meta': {'object_name': user_model_label.split('.')[-1]},
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
        }
    }

    complete_apps = ['actstream']

########NEW FILE########
__FILENAME__ = 0005_auto__add_field_follow_actor_only
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

from actstream.compat import user_model_label

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding field 'Follow.actor_only'
        db.add_column('actstream_follow', 'actor_only', self.gf('django.db.models.fields.BooleanField')(default=True), keep_default=False)


    def backwards(self, orm):

        # Deleting field 'Follow.actor_only'
        db.delete_column('actstream_follow', 'actor_only')


    models = {
        'actstream.action': {
            'Meta': {'ordering': "('-timestamp',)", 'object_name': 'Action'},
            'action_object_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'action_object'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'action_object_object_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'actor_content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'actor'", 'to': "orm['contenttypes.ContentType']"}),
            'actor_object_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'target_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'target'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'target_object_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'verb': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'actstream.follow': {
            'Meta': {'unique_together': "(('user', 'content_type', 'object_id'),)", 'object_name': 'Follow'},
            'actor_only': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s']" % user_model_label})
        },
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
        user_model_label: {
            'Meta': {'object_name': user_model_label.split('.')[-1]},
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
        }
    }

    complete_apps = ['actstream']

########NEW FILE########
__FILENAME__ = 0006_auto__add_field_action_data
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

from actstream.compat import user_model_label


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Action.data'
        db.add_column('actstream_action', 'data', self.gf('django.db.models.fields.TextField')(null=True, blank=True), keep_default=False)

    def backwards(self, orm):
        # Deleting field 'Action.data'
        db.delete_column('actstream_action', 'data')

    models = {
        'actstream.action': {
            'Meta': {'ordering': "('-timestamp',)", 'object_name': 'Action'},
            'action_object_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'action_object'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'action_object_object_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'actor_content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'actor'", 'to': "orm['contenttypes.ContentType']"}),
            'actor_object_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'target_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'target'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'target_object_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'verb': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'actstream.follow': {
            'Meta': {'unique_together': "(('user', 'content_type', 'object_id'),)", 'object_name': 'Follow'},
            'actor_only': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s']" % user_model_label})
        },
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
        user_model_label: {
            'Meta': {'object_name': user_model_label.split('.')[-1]},
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
        }
    }

    complete_apps = ['actstream']

########NEW FILE########
__FILENAME__ = 0007_auto__add_field_follow_started
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

from actstream.compat import user_model_label

try:
    # timezone support for django > 1.4
    from django.utils import timezone
    tz = timezone
except ImportError:
    tz = datetime.datetime

class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Follow.started'
        db.add_column('actstream_follow', 'started', self.gf('django.db.models.fields.DateTimeField')(default=tz.now), keep_default=False)

    def backwards(self, orm):
        # Deleting field 'Follow.started'
        db.delete_column('actstream_follow', 'started')

    models = {
        'actstream.action': {
            'Meta': {'ordering': "('-timestamp',)", 'object_name': 'Action'},
            'action_object_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'action_object'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'action_object_object_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'actor_content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'actor'", 'to': "orm['contenttypes.ContentType']"}),
            'actor_object_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'target_content_type': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'target'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'target_object_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 7, 25, 18, 9, 44, 904569)'}),
            'verb': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'actstream.follow': {
            'Meta': {'unique_together': "(('user', 'content_type', 'object_id'),)", 'object_name': 'Follow'},
            'actor_only': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'started': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 7, 25, 18, 9, 44, 906684)'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s']" % user_model_label})
        },
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
        user_model_label: {
            'Meta': {'object_name': user_model_label.split('.')[-1]},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 7, 25, 18, 9, 44, 903165)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 7, 25, 18, 9, 44, 903031)'}),
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
        }
    }

    complete_apps = ['actstream']

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.core.urlresolvers import reverse
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext as _

from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType

try:
    from django.utils import timezone
    now = timezone.now
except ImportError:
    from datetime import datetime
    now = datetime.now

from actstream import settings as actstream_settings
from actstream.signals import action
from actstream.actions import action_handler
from actstream.managers import FollowManager
from actstream.compat import user_model_label

User = user_model_label


class Follow(models.Model):
    """
    Lets a user follow the activities of any specific actor
    """
    user = models.ForeignKey(User)

    content_type = models.ForeignKey(ContentType)
    object_id = models.CharField(max_length=255)
    follow_object = generic.GenericForeignKey()
    actor_only = models.BooleanField("Only follow actions where the object is "
        "the target.", default=True)
    started = models.DateTimeField(default=now)
    objects = FollowManager()

    class Meta:
        unique_together = ('user', 'content_type', 'object_id')

    def __unicode__(self):
        return u'%s -> %s' % (self.user, self.follow_object)


class Action(models.Model):
    """
    Action model describing the actor acting out a verb (on an optional
    target).
    Nomenclature based on http://activitystrea.ms/specs/atom/1.0/

    Generalized Format::

        <actor> <verb> <time>
        <actor> <verb> <target> <time>
        <actor> <verb> <action_object> <target> <time>

    Examples::

        <justquick> <reached level 60> <1 minute ago>
        <brosner> <commented on> <pinax/pinax> <2 hours ago>
        <washingtontimes> <started follow> <justquick> <8 minutes ago>
        <mitsuhiko> <closed> <issue 70> on <mitsuhiko/flask> <about 2 hours ago>

    Unicode Representation::

        justquick reached level 60 1 minute ago
        mitsuhiko closed issue 70 on mitsuhiko/flask 3 hours ago

    HTML Representation::

        <a href="http://oebfare.com/">brosner</a> commented on <a href="http://github.com/pinax/pinax">pinax/pinax</a> 2 hours ago

    """
    actor_content_type = models.ForeignKey(ContentType, related_name='actor')
    actor_object_id = models.CharField(max_length=255)
    actor = generic.GenericForeignKey('actor_content_type', 'actor_object_id')

    verb = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    target_content_type = models.ForeignKey(ContentType, related_name='target',
        blank=True, null=True)
    target_object_id = models.CharField(max_length=255, blank=True, null=True)
    target = generic.GenericForeignKey('target_content_type',
        'target_object_id')

    action_object_content_type = models.ForeignKey(ContentType,
        related_name='action_object', blank=True, null=True)
    action_object_object_id = models.CharField(max_length=255, blank=True,
        null=True)
    action_object = generic.GenericForeignKey('action_object_content_type',
        'action_object_object_id')

    timestamp = models.DateTimeField(default=now)

    public = models.BooleanField(default=True)

    objects = actstream_settings.get_action_manager()

    class Meta:
        ordering = ('-timestamp', )

    def __unicode__(self):
        ctx = {
            'actor': self.actor,
            'verb': self.verb,
            'action_object': self.action_object,
            'target': self.target,
            'timesince': self.timesince()
        }
        if self.target:
            if self.action_object:
                return _('%(actor)s %(verb)s %(action_object)s on %(target)s %(timesince)s ago') % ctx
            return _('%(actor)s %(verb)s %(target)s %(timesince)s ago') % ctx
        if self.action_object:
            return _('%(actor)s %(verb)s %(action_object)s %(timesince)s ago') % ctx
        return _('%(actor)s %(verb)s %(timesince)s ago') % ctx

    def actor_url(self):
        """
        Returns the URL to the ``actstream_actor`` view for the current actor.
        """
        return reverse('actstream_actor', None,
                       (self.actor_content_type.pk, self.actor_object_id))

    def target_url(self):
        """
        Returns the URL to the ``actstream_actor`` view for the current target.
        """
        return reverse('actstream_actor', None,
                       (self.target_content_type.pk, self.target_object_id))

    def action_object_url(self):
        """
        Returns the URL to the ``actstream_action_object`` view for the current action object
        """
        return reverse('actstream_actor', None,
            (self.action_object_content_type.pk, self.action_object_object_id))

    def timesince(self, now=None):
        """
        Shortcut for the ``django.utils.timesince.timesince`` function of the
        current timestamp.
        """
        from django.utils.timesince import timesince as timesince_
        return timesince_(self.timestamp, now)

    @models.permalink
    def get_absolute_url(self):
        return ('actstream.views.detail', [self.pk])


# convenient accessors
actor_stream = Action.objects.actor
action_object_stream = Action.objects.action_object
target_stream = Action.objects.target
user_stream = Action.objects.user
model_stream = Action.objects.model_actions
followers = Follow.objects.followers
following = Follow.objects.following


def setup_generic_relations():
    """
    Set up GenericRelations for actionable models.
    """
    for model in actstream_settings.get_models().values():
        if not model:
            continue
        for field in ('actor', 'target', 'action_object'):
            attr = '%s_actions' % field
            if isinstance(getattr(model, attr, None),
                          generic.ReverseGenericRelatedObjectsDescriptor):
                break
            generic.GenericRelation(Action,
                content_type_field='%s_content_type' % field,
                object_id_field='%s_object_id' % field,
                related_name='actions_with_%s_%s_as_%s' % (
                    model._meta.app_label, model._meta.module_name, field),
            ).contribute_to_class(model, attr)

            # @@@ I'm not entirely sure why this works
            setattr(Action, 'actions_with_%s_%s_as_%s' % (
                model._meta.app_label, model._meta.module_name, field), None)


setup_generic_relations()


if actstream_settings.USE_JSONFIELD:
    try:
        from jsonfield.fields import JSONField
    except ImportError:
        raise ImproperlyConfigured('You must have django-jsonfield installed '
                                'if you wish to use a JSONField on your actions')
    JSONField(blank=True, null=True).contribute_to_class(Action, 'data')

# connect the signal
action.connect(action_handler, dispatch_uid='actstream.models')

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python

# http://ericholscher.com/blog/2009/jun/29/enable-setuppy-test-your-django-apps/
# http://www.travisswicegood.com/2010/01/17/django-virtualenv-pip-and-fabric/
# http://code.djangoproject.com/svn/django/trunk/tests/runtests.py
# https://github.com/tomchristie/django-rest-framework/blob/master/rest_framework/runtests/runtests.py
import os
import sys

# fix sys path so we don't need to setup PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
os.environ['DJANGO_SETTINGS_MODULE'] = 'actstream.runtests.settings'

from django.conf import settings
from django.test.utils import get_runner


if __name__ == '__main__':
    sys.exit(get_runner(settings)().run_tests(['actstream', 'testapp']))

########NEW FILE########
__FILENAME__ = settings
# Django settings for example_project project.
import os, sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import django

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Justin Quick', 'justquick@gmail.com'),
)


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'dev.db',                      # Or path to database file if using sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/New_York'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = 'media'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'wzf0h@r2u%m^_zgj^39-y(kd%+n+j0r7=du(q0^s@q1asdfasdfasdft%^2!p'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    'templates',
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admindocs',
    'django.contrib.comments',
    'django.contrib.sites',
    'django.contrib.messages',
    'actstream',
    'testapp'
)

TEMPLATE_CONTEXT_PROCESSORS = (
    # for django 1.2 or 1.3
    'django.core.context_processors.auth',
    # for django 1.4 comment above line and uncomment below
    #'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
)


ACTSTREAM_SETTINGS = {
    'MODELS': ('auth.user', 'auth.group', 'sites.site', 'comments.comment'),
    'MANAGER': 'testapp.streams.MyActionManager',
    'FETCH_RELATIONS': True,
    'USE_PREFETCH': True,
    'USE_JSONFIELD': True,
    'GFK_FETCH_DEPTH': 0,
}

if django.VERSION[0] == 1 and django.VERSION[1] >= 5:
    AUTH_USER_MODEL = 'testapp.MyUser'
    ACTSTREAM_SETTINGS['MODELS'] += ('testapp.myuser',)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from models import Player

admin.site.register(Player)

########NEW FILE########
__FILENAME__ = models
import django
from django.db import models
from django.contrib.comments.signals import comment_was_posted

from actstream import action


def comment_action(sender, comment=None, target=None, **kwargs):
    if comment.user:
        action.send(comment.user, verb=u'commented', action_object=comment,
            target=comment.content_object)
comment_was_posted.connect(comment_action)


class Player(models.Model):
    state = models.IntegerField(default=0)

    def __unicode__(self):
        return '#%d' % self.pk

if django.VERSION[0] == 1 and django.VERSION[1] >= 5:
    from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin


    class MyUser(AbstractBaseUser, PermissionsMixin):
        username = models.CharField(max_length=30, unique=True)

        USERNAME_FIELD = 'username'

        def get_full_name(self):
            return 'full'

########NEW FILE########
__FILENAME__ = streams
from datetime import datetime

from actstream.managers import ActionManager, stream


class MyActionManager(ActionManager):

    @stream
    def testfoo(self, obj, time=None):
        if time is None:
            time = datetime.now()
        return obj.actor_actions.filter(timestamp__lte = time)

    @stream
    def testbar(self, verb):
        return self.filter(verb=verb)

########NEW FILE########
__FILENAME__ = tests
from datetime import datetime

import django
from django.utils.unittest import skipUnless
from django.test import TestCase

from actstream.models import Action
from actstream.signals import action
from actstream.compat import get_user_model


User = get_user_model()


class TestAppTests(TestCase):

    def setUp(self):
        self.user = User.objects.create(username='test')
        action.send(self.user, verb='was created')

    def test_accessor(self):
        self.assertEqual(len(Action.objects.testfoo(self.user)), 1)
        self.assertEqual(len(Action.objects.testfoo(self.user, datetime(1970, 1, 1))), 0)

    def test_mystream(self):
        self.assertEqual(len(self.user.actor_actions.testbar('was created')), 1)
        self.assertEqual(len(self.user.action_object_actions.testbar('was created')), 0)

    def test_jsonfield(self):
        action.send(self.user, verb='said', text='foobar', tags=['sayings'],
                    more_data={'pk': self.user.pk})
        newaction = Action.objects.filter(verb='said')[0]
        self.assertEqual(newaction.data['text'], 'foobar')
        self.assertEqual(newaction.data['tags'], ['sayings'])
        self.assertEqual(newaction.data['more_data'], {'pk': self.user.pk})

    @skipUnless(django.VERSION[0] == 1 and django.VERSION[1] >= 5, 'Django>=1.5 Required')
    def test_customuser(self):
        from testapp.models import MyUser

        self.assertEqual(User, MyUser)
        self.assertEqual(self.user.get_full_name(), 'full')

########NEW FILE########
__FILENAME__ = urls
import os
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^comments/', include('django.contrib.comments.urls')),
    (r'^accounts/', include('registration.backends.default.urls')),
    (r'^media/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': os.path.join(os.path.dirname(__file__), 'media')}),
    (r'auth/', include('django.contrib.auth.urls')),
    (r'', include('actstream.urls')),
)


########NEW FILE########
__FILENAME__ = settings
import django
from django.conf import settings
from django.db.models import get_model


SETTINGS = getattr(settings, 'ACTSTREAM_SETTINGS', {})

def get_models():
    """
    Returns a lookup of 'app_label.model': <model class> from ACTSTREAM_SETTINGS['MODELS']
    Only call this right before you need to inspect the models
    """
    models = {}
    for model in SETTINGS.get('MODELS', ('auth.User',)):
        models[model.lower()] = get_model(*model.split('.'))
    return models

def get_action_manager():
    """
    Returns the class of the action manager to use from ACTSTREAM_SETTINGS['MANAGER']
    """
    mod = SETTINGS.get('MANAGER', 'actstream.managers.ActionManager')
    a, j = mod.split('.'), lambda l: '.'.join(l)
    return getattr(__import__(j(a[:-1]), {}, {}, [a[-1]]), a[-1])()

USE_PREFETCH = SETTINGS.get('USE_PREFETCH',
                            django.VERSION[0] == 1 and django.VERSION[1] >= 4)

FETCH_RELATIONS = SETTINGS.get('FETCH_RELATIONS', True)

GFK_FETCH_DEPTH = SETTINGS.get('GFK_FETCH_DEPTH', 0)

USE_JSONFIELD = SETTINGS.get('USE_JSONFIELD', False)

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal

action = Signal(providing_args=['verb', 'action_object', 'target',
                                'description', 'timestamp'])

########NEW FILE########
__FILENAME__ = activity_tags
from actstream.models import Follow
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.template import Variable, Library, Node, TemplateSyntaxError
from django.template.base import TemplateDoesNotExist
from django.template.loader import render_to_string, find_template


register = Library()


def _is_following_helper(context, actor):
    return Follow.objects.is_following(context.get('user'), actor)


class DisplayActivityFollowUrl(Node):
    def __init__(self, actor, actor_only=True):
        self.actor = Variable(actor)
        self.actor_only = actor_only

    def render(self, context):
        actor_instance = self.actor.resolve(context)
        content_type = ContentType.objects.get_for_model(actor_instance).pk
        if Follow.objects.is_following(context.get('user'), actor_instance):
            return reverse('actstream_unfollow', kwargs={
                'content_type_id': content_type, 'object_id': actor_instance.pk})
        if self.actor_only:
            return reverse('actstream_follow', kwargs={
                'content_type_id': content_type, 'object_id': actor_instance.pk})
        return reverse('actstream_follow_all', kwargs={
            'content_type_id': content_type, 'object_id': actor_instance.pk})


class DisplayActivityActorUrl(Node):
    def __init__(self, actor):
        self.actor = Variable(actor)

    def render(self, context):
        actor_instance = self.actor.resolve(context)
        content_type = ContentType.objects.get_for_model(actor_instance).pk
        return reverse('actstream_actor', kwargs={
            'content_type_id': content_type, 'object_id': actor_instance.pk})


class AsNode(Node):
    """
    Base template Node class for template tags that takes a predefined number
    of arguments, ending in an optional 'as var' section.
    """
    args_count = 1

    @classmethod
    def handle_token(cls, parser, token):
        """
        Class method to parse and return a Node.
        """
        bits = token.split_contents()
        args_count = len(bits) - 1
        if args_count >= 2 and bits[-2] == 'as':
            as_var = bits[-1]
            args_count -= 2
        else:
            as_var = None
        if args_count != cls.args_count:
            arg_list = ' '.join(['[arg]' * cls.args_count])
            raise TemplateSyntaxError("Accepted formats {%% %(tagname)s "
                "%(args)s %%} or {%% %(tagname)s %(args)s as [var] %%}" %
                {'tagname': bits[0], 'args': arg_list})
        args = [parser.compile_filter(token) for token in
            bits[1:args_count + 1]]
        return cls(args, varname=as_var)

    def __init__(self, args, varname=None):
        self.args = args
        self.varname = varname

    def render(self, context):
        result = self.render_result(context)
        if self.varname is not None:
            context[self.varname] = result
            return ''
        return result

    def render_result(self, context):
        raise NotImplementedError("Must be implemented by a subclass")


class DisplayAction(AsNode):

    def render_result(self, context):
        action_instance = self.args[0].resolve(context)
        templates = [
            'actstream/%s/action.html' % action_instance.verb.replace(' ', '_'),
            'actstream/action.html',
            'activity/%s/action.html' % action_instance.verb.replace(' ', '_'),
            'activity/action.html',
        ]
        return render_to_string(templates, {'action': action_instance},
            context)


def display_action(parser, token):
    """
    Renders the template for the action description

    Example::

        {% display_action action %}
    """
    return DisplayAction.handle_token(parser, token)


def is_following(user, actor):
    """
    Returns true if the given user is following the actor

    Example::

        {% if request.user|is_following:another_user %}
            You are already following {{ another_user }}
        {% endif %}
    """
    return Follow.objects.is_following(user, actor)


def follow_url(parser, token):
    """
    Renders the URL of the follow view for a particular actor instance

    Example::

        <a href="{% follow_url other_user %}">
            {% if request.user|is_following:other_user %}
                stop following
            {% else %}
                follow
            {% endif %}
        </a>
    """
    bits = token.split_contents()
    if len(bits) != 2:
        raise TemplateSyntaxError("Accepted format {% follow_url [instance] %}")
    else:
        return DisplayActivityFollowUrl(bits[1])


def follow_all_url(parser, token):
    """
    Renders the URL to follow an object as both actor and target

    Example::

        <a href="{% follow_all_url other_user %}">
            {% if request.user|is_following:other_user %}
                stop following
            {% else %}
                follow
            {% endif %}
        </a>
    """
    bits = token.split_contents()
    if len(bits) != 2:
        raise TemplateSyntaxError("Accepted format {% follow_all_url [instance] %}")
    else:
        return DisplayActivityFollowUrl(bits[1], actor_only=False)


def actor_url(parser, token):
    """
    Renders the URL for a particular actor instance

    Example::

        <a href="{% actor_url request.user %}">View your actions</a>
        <a href="{% actor_url another_user %}">{{ another_user }}'s actions</a>

    """
    bits = token.split_contents()
    if len(bits) != 2:
        raise TemplateSyntaxError("Accepted format "
                                  "{% actor_url [actor_instance] %}")
    else:
        return DisplayActivityActorUrl(*bits[1:])

register.filter(is_following)
register.tag(display_action)
register.tag(follow_url)
register.tag(follow_all_url)
register.tag(actor_url)

@register.filter
def backwards_compatibility_check(template_name):
    backwards = False
    try:
        find_template('actstream/action.html')
    except TemplateDoesNotExist:
        backwards = True
    if backwards:
        template_name = template_name.replace('actstream/', 'activity/')
    return template_name
########NEW FILE########
__FILENAME__ = tests
from random import choice

from django.db import connection
from django.db.models import get_model
from django.test import TestCase
from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.template.loader import Template, Context
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import activate, get_language

from actstream.models import Action, Follow, model_stream, user_stream,\
    setup_generic_relations, following, followers
from actstream.actions import follow, unfollow
from actstream.exceptions import ModelNotActionable
from actstream.signals import action
from actstream.settings import get_models, SETTINGS
from actstream.compat import get_user_model

User = get_user_model()


class LTE(int):
    def __new__(cls, n):
        obj = super(LTE, cls).__new__(cls, n)
        obj.n = n
        return obj

    def __eq__(self, other):
        return other <= self.n

    def __repr__(self):
        return "<= %s" % self.n


class ActivityBaseTestCase(TestCase):
    actstream_models = ()

    def setUp(self):
        self.old_models = get_models()
        setup_generic_relations()

    def assertAllIn(self, bits, string):
        for bit in bits:
            self.assertIn(bit, string)

    def tearDown(self):
        SETTINGS['MODELS'] = self.old_models


class ActivityTestCase(ActivityBaseTestCase):
    urls = 'actstream.urls'
    actstream_models = ('auth.User', 'auth.Group', 'sites.Site')

    def setUp(self):
        super(ActivityTestCase, self).setUp()
        self.group = Group.objects.create(name='CoolGroup')
        self.user1 = User.objects.get_or_create(username='admin')[0]
        self.user1.set_password('admin')
        self.user1.is_superuser = self.user1.is_staff = True
        self.user1.save()
        self.user2 = User.objects.get_or_create(username='Two')[0]

        # User1 joins group
        self.user1.groups.add(self.group)
        action.send(self.user1, verb='joined', target=self.group)

        # User1 follows User2
        follow(self.user1, self.user2)

        # User2 joins group
        self.user2.groups.add(self.group)
        action.send(self.user2, verb='joined', target=self.group)

        # User2 follows group
        follow(self.user2, self.group)

        # User1 comments on group
        # Use a site object here and predict the "__unicode__ method output"
        action.send(self.user1, verb='commented on', target=self.group)
        self.comment = Site.objects.create(
            domain="admin: Sweet Group!...")

        # Group responds to comment
        action.send(self.group, verb='responded to', target=self.comment)

    def test_aauser1(self):
        self.assertEqual(map(unicode, self.user1.actor_actions.all()), [
            u'admin commented on CoolGroup 0 minutes ago',
            u'admin started following Two 0 minutes ago',
            u'admin joined CoolGroup 0 minutes ago',
        ])

    def test_user2(self):
        self.assertEqual(map(unicode, Action.objects.actor(self.user2)), [
            u'Two started following CoolGroup 0 minutes ago',
            u'Two joined CoolGroup 0 minutes ago',
        ])

    def test_group(self):
        self.assertEqual(map(unicode, Action.objects.actor(self.group)),
            [u'CoolGroup responded to admin: Sweet Group!... 0 minutes ago'])

    def test_following(self):
        self.assertEqual(list(following(self.user1)), [self.user2])
        self.assertEqual(len(following(self.user2, User)), 0)

    def test_followers(self):
        self.assertEqual(list(followers(self.group)), [self.user2])

    def test_empty_follow_stream(self):
        unfollow(self.user1, self.user2)
        self.assert_(not user_stream(self.user1))

    def test_stream(self):
        self.assertEqual(map(unicode, Action.objects.user(self.user1)), [
            u'Two started following CoolGroup 0 minutes ago',
            u'Two joined CoolGroup 0 minutes ago',
        ])
        self.assertEqual(map(unicode, Action.objects.user(self.user2)),
            [u'CoolGroup responded to admin: Sweet Group!... 0 minutes ago'])

    def test_stream_stale_follows(self):
        """
        Action.objects.user() should ignore Follow objects with stale actor
        references.
        """
        self.user2.delete()
        self.assert_(not 'Two' in str(Action.objects.user(self.user1)))

    def test_rss(self):
        self.assertAllIn([
            '<?xml version="1.0" encoding="utf-8"?>\n',
            '<rss ',
            'xmlns:atom="http://www.w3.org/2005/Atom"',
            'version="2.0"',
            'Activity feed for your followed actors'
        ], self.client.get('/feed/').content.decode())

    def test_atom(self):
        self.assertAllIn([
            '<?xml version="1.0" encoding="utf-8"?>\n',
            'xmlns="http://www.w3.org/2005/Atom"',
            'xml:lang="%s"' % settings.LANGUAGE_CODE,
            'Activity feed for your followed actors'
        ], self.client.get('/feed/atom/').content.decode())

    def test_action_object(self):
        action.send(self.user1, verb='created comment',
            action_object=self.comment, target=self.group)
        created_action = Action.objects.get(verb='created comment')

        self.assertEqual(created_action.actor, self.user1)
        self.assertEqual(created_action.action_object, self.comment)
        self.assertEqual(created_action.target, self.group)
        self.assertEqual(unicode(created_action),
            u'admin created comment admin: Sweet Group!... on CoolGroup 0 '
                'minutes ago')

    def test_doesnt_generate_duplicate_follow_records(self):
        g = Group.objects.get_or_create(name='DupGroup')[0]
        s = User.objects.get_or_create(username='dupuser')[0]

        f1 = follow(s, g)
        self.assertTrue(f1 is not None, "Should have received a new follow "
            "record")
        self.assertTrue(isinstance(f1, Follow), "Returns a Follow object")

        self.assertEquals(1, Follow.objects.filter(user=s, object_id=g.pk,
            content_type=ContentType.objects.get_for_model(g)).count(),
            "Should only have 1 follow record here")

        f2 = follow(s, g)
        self.assertEquals(1, Follow.objects.filter(user=s, object_id=g.pk,
            content_type=ContentType.objects.get_for_model(g)).count(),
            "Should still only have 1 follow record here")
        self.assertTrue(f2 is not None, "Should have received a Follow object")
        self.assertTrue(isinstance(f2, Follow), "Returns a Follow object")
        self.assertEquals(f1, f2, "Should have received the same Follow "
            "object that I first submitted")

    def test_y_no_orphaned_follows(self):
        follows = Follow.objects.count()
        self.user2.delete()
        self.assertEqual(follows - 1, Follow.objects.count())

    def test_z_no_orphaned_actions(self):
        actions = self.user1.actor_actions.count()
        self.user2.delete()
        self.assertEqual(actions - 1, self.user1.actor_actions.count())

    def test_generic_relation_accessors(self):
        self.assertEqual(self.user2.actor_actions.count(), 2)
        self.assertEqual(self.user2.target_actions.count(), 1)
        self.assertEqual(self.user2.action_object_actions.count(), 0)

    def test_bad_actionable_model(self):
        self.assertRaises(ModelNotActionable, follow, self.user1,
                          ContentType.objects.get_for_model(self.user1))

    def test_hidden_action(self):
        action = self.user1.actor_actions.all()[0]
        action.public = False
        action.save()
        self.assert_(not action in self.user1.actor_actions.public())

    def test_tag_follow_url(self):
        src = '{% load activity_tags %}{% follow_url user %}'
        output = Template(src).render(Context({'user': self.user1}))
        ct = ContentType.objects.get_for_model(User)
        self.assertEqual(output, '/follow/%s/%s/' % (ct.pk, self.user1.pk))

    def test_model_actions_with_kwargs(self):
        """
        Testing the model_actions method of the ActionManager
        by passing kwargs
        """
        self.assertEqual(map(unicode, model_stream(self.user1, verb='commented on')), [
                u'admin commented on CoolGroup 0 minutes ago',
                ])

    def test_user_stream_with_kwargs(self):
        """
        Testing the user method of the ActionManager by passing additional
        filters in kwargs
        """
        self.assertEqual(map(unicode, Action.objects.user(self.user1, verb='joined')), [
                u'Two joined CoolGroup 0 minutes ago',
                ])

    def test_is_following_filter(self):
        src = '{% load activity_tags %}{% if user|is_following:group %}yup{% endif %}'
        self.assertEqual(Template(src).render(Context({
            'user': self.user2, 'group': self.group
        })), u'yup')
        self.assertEqual(Template(src).render(Context({
            'user': self.user1, 'group': self.group
        })), u'')

    def test_store_untranslated_string(self):
        lang = get_language()
        activate("fr")
        verb = _(u'English')

        assert unicode(verb) == u"Anglais"
        action.send(self.user1, verb=verb, action_object=self.comment,
                    target=self.group)
        self.assertTrue(Action.objects.filter(verb=u'English'))
        # restore language
        activate(lang)


class ZombieTest(ActivityBaseTestCase):
    actstream_models = ('auth.User',)
    human = 10
    zombie = 1

    def setUp(self):
        super(ZombieTest, self).setUp()
        settings.DEBUG = True

        player_generator = lambda n, count: [User.objects.create(
            username='%s%d' % (n, i)) for i in range(count)]

        self.humans = player_generator('human', self.human)
        self.zombies = player_generator('zombie', self.zombie)

        self.zombie_apocalypse()

    def tearDown(self):
        settings.DEBUG = False
        super(ZombieTest, self).tearDown()

    def zombie_apocalypse(self):
        humans = self.humans[:]
        zombies = self.zombies[:]
        while humans:
            for z in self.zombies:
                victim = choice(humans)
                humans.remove(victim)
                zombies.append(victim)
                action.send(z, verb='killed', target=victim)
                if not humans:
                    break

    def check_query_count(self, queryset):
        ci = len(connection.queries)

        result = list([map(unicode, (x.actor, x.target, x.action_object))
            for x in queryset])
        self.assertTrue(len(connection.queries) - ci <= 4,
            'Too many queries, got %d expected no more than 4' %
                len(connection.queries))
        return result

    def test_query_count(self):
        queryset = model_stream(User)
        result = self.check_query_count(queryset)
        self.assertEqual(len(result), 10)

    def test_query_count_sliced(self):
        queryset = model_stream(User)[:5]
        result = self.check_query_count(queryset)
        self.assertEqual(len(result), 5)


class GFKManagerTestCase(TestCase):

    def setUp(self):
        self.user_ct = ContentType.objects.get_for_model(User)
        self.group_ct = ContentType.objects.get_for_model(Group)
        self.group, _ = Group.objects.get_or_create(name='CoolGroup')
        self.user1, _ = User.objects.get_or_create(username='admin')
        self.user2, _ = User.objects.get_or_create(username='Two')
        self.user3, _ = User.objects.get_or_create(username='Three')
        self.user4, _ = User.objects.get_or_create(username='Four')
        Action.objects.get_or_create(
            actor_content_type=self.user_ct,
            actor_object_id=self.user1.id,
            verb='followed',
            target_content_type=self.user_ct,
            target_object_id=self.user2.id
        )
        Action.objects.get_or_create(
            actor_content_type=self.user_ct,
            actor_object_id=self.user1.id,
            verb='followed',
            target_content_type=self.user_ct,
            target_object_id=self.user3.id
        )
        Action.objects.get_or_create(
            actor_content_type=self.user_ct,
            actor_object_id=self.user1.id,
            verb='followed',
            target_content_type=self.user_ct,
            target_object_id=self.user4.id
        )
        Action.objects.get_or_create(
            actor_content_type=self.user_ct,
            actor_object_id=self.user1.id,
            verb='joined',
            target_content_type=self.group_ct,
            target_object_id=self.group.id
        )

    def test_fetch_generic_relations(self):
        # baseline without fetch_generic_relations
        _actions = Action.objects.filter(actor_content_type=self.user_ct,
            actor_object_id=self.user1.id)
        actions = lambda: _actions._clone()
        num_content_types = len(set(actions().values_list(
            'target_content_type_id', flat=True)))
        n = actions().count()

        # compare to fetching only 1 generic relation
        self.assertNumQueries(LTE(n + 1),
            lambda: [a.target for a in actions()])
        self.assertNumQueries(LTE(num_content_types + 2),
            lambda: [a.target for a in
                actions().fetch_generic_relations('target')])

        action_targets = [(a.id, a.target) for a in actions()]
        action_targets_fetch_generic = [(a.id, a.target) for a in
                actions().fetch_generic_relations('target')]
        self.assertEqual(action_targets, action_targets_fetch_generic)

        # compare to fetching all generic relations
        num_content_types = len(set(sum(actions().values_list(
            'actor_content_type_id', 'target_content_type_id'), ())))
        self.assertNumQueries(LTE(2 * n + 1),
            lambda: [(a.actor, a.target) for a in actions()])
        self.assertNumQueries(LTE(num_content_types + 2),
            lambda: [(a.actor, a.target) for a in
                actions().fetch_generic_relations()])

        action_actor_targets = [(a.id, a.actor, a.target) for a in actions()]
        action_actor_targets_fetch_generic_all = [
            (a.id, a.actor, a.target) for a in
                actions().fetch_generic_relations()]
        self.assertEqual(action_actor_targets,
            action_actor_targets_fetch_generic_all)

        # fetch only 1 generic relation, but access both gfks
        self.assertNumQueries(LTE(n + num_content_types + 2),
            lambda: [(a.actor, a.target) for a in
                actions().fetch_generic_relations('target')])
        action_actor_targets_fetch_generic_target = [
            (a.id, a.actor, a.target) for a in
                actions().fetch_generic_relations('target')]
        self.assertEqual(action_actor_targets,
            action_actor_targets_fetch_generic_target)

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import url, patterns
except ImportError:
    from django.conf.urls.defaults import url, patterns

from actstream import feeds


urlpatterns = patterns('actstream.views',
    # Syndication Feeds
    url(r'^feed/(?P<content_type_id>\d+)/(?P<object_id>\d+)/atom/$',
        feeds.AtomObjectActivityFeed(), name='actstream_object_feed_atom'),
    url(r'^feed/(?P<content_type_id>\d+)/(?P<object_id>\d+)/$',
        feeds.ObjectActivityFeed(), name='actstream_object_feed'),
    url(r'^feed/(?P<content_type_id>\d+)/atom/$',
        feeds.AtomModelActivityFeed(), name='actstream_model_feed_atom'),
    url(r'^feed/(?P<content_type_id>\d+)/(?P<object_id>\d+)/as/$',
        feeds.ActivityStreamsObjectActivityFeed(),
        name='actstream_object_feed_as'),
    url(r'^feed/(?P<content_type_id>\d+)/$',
        feeds.ModelActivityFeed(), name='actstream_model_feed'),
    url(r'^feed/$', feeds.UserActivityFeed(), name='actstream_feed'),
    url(r'^feed/atom/$', feeds.AtomUserActivityFeed(),
        name='actstream_feed_atom'),

    # Follow/Unfollow API
    url(r'^follow/(?P<content_type_id>\d+)/(?P<object_id>\d+)/$',
        'follow_unfollow', name='actstream_follow'),
    url(r'^follow_all/(?P<content_type_id>\d+)/(?P<object_id>\d+)/$',
        'follow_unfollow', {'actor_only': False}, name='actstream_follow_all'),
    url(r'^unfollow/(?P<content_type_id>\d+)/(?P<object_id>\d+)/$',
        'follow_unfollow', {'do_follow': False}, name='actstream_unfollow'),

    # Follower and Actor lists
    url(r'^followers/(?P<content_type_id>\d+)/(?P<object_id>\d+)/$',
        'followers', name='actstream_followers'),
    url(r'^actors/(?P<content_type_id>\d+)/(?P<object_id>\d+)/$',
        'actor', name='actstream_actor'),
    url(r'^actors/(?P<content_type_id>\d+)/$',
        'model', name='actstream_model'),

    url(r'^detail/(?P<action_id>\d+)/$', 'detail', name='actstream_detail'),
    url(r'^(?P<username>.+)/$', 'user', name='actstream_user'),
    url(r'^$', 'stream', name='actstream'),
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponse

from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.views.decorators.csrf import csrf_exempt

from actstream import actions, models, compat

User = compat.get_user_model()


def respond(request, code):
    """
    Responds to the request with the given response code.
    If ``next`` is in the form, it will redirect instead.
    """
    if 'next' in request.REQUEST:
        return HttpResponseRedirect(request.REQUEST['next'])
    return type('Response%d' % code, (HttpResponse, ), {'status_code': code})()


@login_required
@csrf_exempt
def follow_unfollow(request, content_type_id, object_id, do_follow=True, actor_only=True):
    """
    Creates or deletes the follow relationship between ``request.user`` and the
    actor defined by ``content_type_id``, ``object_id``.
    """
    ctype = get_object_or_404(ContentType, pk=content_type_id)
    actor = get_object_or_404(ctype.model_class(), pk=object_id)

    if do_follow:
        actions.follow(request.user, actor, actor_only=actor_only)
        return respond(request, 201)   # CREATED
    actions.unfollow(request.user, actor)
    return respond(request, 204)   # NO CONTENT


@login_required
def stream(request):
    """
    Index page for authenticated user's activity stream. (Eg: Your feed at
    github.com)
    """
    return render_to_response(('actstream/actor.html', 'activity/actor.html'), {
        'ctype': ContentType.objects.get_for_model(User),
        'actor': request.user, 'action_list': models.user_stream(request.user)
    }, context_instance=RequestContext(request))


def followers(request, content_type_id, object_id):
    """
    Creates a listing of ``User``s that follow the actor defined by
    ``content_type_id``, ``object_id``.
    """
    ctype = get_object_or_404(ContentType, pk=content_type_id)
    actor = get_object_or_404(ctype.model_class(), pk=object_id)
    return render_to_response(('actstream/followers.html', 'activity/followers.html'), {
        'followers': models.followers(actor), 'actor': actor
    }, context_instance=RequestContext(request))


def following(request, user_id):
    """
    Returns a list of actors that the user identified by ``user_id`` is following (eg who im following).
    """
    user = get_object_or_404(User, pk=user_id)
    return render_to_response(('actstream/following.html', 'activity/following.html'), {
        'following': models.following(user), 'user': user
    }, context_instance=RequestContext(request))


def user(request, username):
    """
    ``User`` focused activity stream. (Eg: Profile page twitter.com/justquick)
    """
    user = get_object_or_404(User, username=username, is_active=True)
    return render_to_response(('actstream/actor.html', 'activity/actor.html'), {
        'ctype': ContentType.objects.get_for_model(User),
        'actor': user, 'action_list': models.user_stream(user)
    }, context_instance=RequestContext(request))


def detail(request, action_id):
    """
    ``Action`` detail view (pretty boring, mainly used for get_absolute_url)
    """
    return render_to_response(('actstream/detail.html', 'activity/detail.html'), {
        'action': get_object_or_404(models.Action, pk=action_id)
    }, context_instance=RequestContext(request))


def actor(request, content_type_id, object_id):
    """
    ``Actor`` focused activity stream for actor defined by ``content_type_id``,
    ``object_id``.
    """
    ctype = get_object_or_404(ContentType, pk=content_type_id)
    actor = get_object_or_404(ctype.model_class(), pk=object_id)
    return render_to_response(('actstream/actor.html', 'activity/actor.html'), {
        'action_list': models.actor_stream(actor), 'actor': actor,
        'ctype': ctype
    }, context_instance=RequestContext(request))


def model(request, content_type_id):
    """
    ``Actor`` focused activity stream for actor defined by ``content_type_id``,
    ``object_id``.
    """
    ctype = get_object_or_404(ContentType, pk=content_type_id)
    actor = ctype.model_class()
    return render_to_response(('actstream/actor.html', 'activity/actor.html'), {
        'action_list': models.model_stream(actor), 'ctype': ctype,
        'actor': actor
    }, context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Django Activity Stream documentation build configuration file, created by
# sphinx-quickstart on Sat Oct  1 12:35:29 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join('..', '..', 'actstream', 'runtests')))

import settings
from django.core.management import setup_environ
setup_environ(settings)

import actstream

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Django Activity Stream'
copyright = u'%s, Justin Quick' % datetime.now().year

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = actstream.get_version(False)
# The full version, including alpha/beta/rc tags.
release = actstream.get_version()

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
htmlhelp_basename = 'DjangoActivityStreamdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'DjangoActivityStream.tex', u'Django Activity Stream Documentation',
   u'Justin Quick', 'manual'),
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
    ('index', 'djangoactivitystream', u'Django Activity Stream Documentation',
     [u'Justin Quick'], 1)
]

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from django.contrib.sites.models import RequestSite
from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _

from registration.models import RegistrationProfile


class RegistrationAdmin(admin.ModelAdmin):
    actions = ['activate_users', 'resend_activation_email']
    list_display = ('user', 'activation_key_expired')
    raw_id_fields = ['user']
    search_fields = ('user__username', 'user__first_name')

    def activate_users(self, request, queryset):
        """
        Activates the selected users, if they are not alrady
        activated.
        
        """
        for profile in queryset:
            RegistrationProfile.objects.activate_user(profile.activation_key)
    activate_users.short_description = _("Activate users")

    def resend_activation_email(self, request, queryset):
        """
        Re-sends activation emails for the selected users.

        Note that this will *only* send activation emails for users
        who are eligible to activate; emails will not be sent to users
        whose activation keys have expired or who have already
        activated.
        
        """
        if Site._meta.installed:
            site = Site.objects.get_current()
        else:
            site = RequestSite(request)

        for profile in queryset:
            if not profile.activation_key_expired():
                profile.send_activation_email(site)
    resend_activation_email.short_description = _("Re-send activation emails")


admin.site.register(RegistrationProfile, RegistrationAdmin)

########NEW FILE########
__FILENAME__ = auth_urls
"""
URL patterns for the views included in ``django.contrib.auth``.

Including these URLs (via the ``include()`` directive) will set up the
following patterns based at whatever URL prefix they are included
under:

* User login at ``login/``.

* User logout at ``logout/``.

* The two-step password change at ``password/change/`` and
  ``password/change/done/``.

* The four-step password reset at ``password/reset/``,
  ``password/reset/confirm/``, ``password/reset/complete/`` and
  ``password/reset/done/``.

The default registration backend already has an ``include()`` for
these URLs, so under the default setup it is not necessary to manually
include these views. Other backends may or may not include them;
consult a specific backend's documentation for details.

"""

from django.conf.urls.defaults import *

from django.contrib.auth import views as auth_views


urlpatterns = patterns('',
                       url(r'^login/$',
                           auth_views.login,
                           {'template_name': 'registration/login.html'},
                           name='auth_login'),
                       url(r'^logout/$',
                           auth_views.logout,
                           {'template_name': 'registration/logout.html'},
                           name='auth_logout'),
                       url(r'^password/change/$',
                           auth_views.password_change,
                           name='auth_password_change'),
                       url(r'^password/change/done/$',
                           auth_views.password_change_done,
                           name='auth_password_change_done'),
                       url(r'^password/reset/$',
                           auth_views.password_reset,
                           name='auth_password_reset'),
                       url(r'^password/reset/confirm/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
                           auth_views.password_reset_confirm,
                           name='auth_password_reset_confirm'),
                       url(r'^password/reset/complete/$',
                           auth_views.password_reset_complete,
                           name='auth_password_reset_complete'),
                       url(r'^password/reset/done/$',
                           auth_views.password_reset_done,
                           name='auth_password_reset_done'),
)

########NEW FILE########
__FILENAME__ = urls
"""
URLconf for registration and activation, using django-registration's
default backend.

If the default behavior of these views is acceptable to you, simply
use a line like this in your root URLconf to set up the default URLs
for registration::

    (r'^accounts/', include('registration.backends.default.urls')),

This will also automatically set up the views in
``django.contrib.auth`` at sensible default locations.

If you'd like to customize the behavior (e.g., by passing extra
arguments to the various views) or split up the URLs, feel free to set
up your own URL patterns for these views instead.

"""


from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template

from registration.views import activate
from registration.views import register


urlpatterns = patterns('',
                       url(r'^activate/complete/$',
                           direct_to_template,
                           { 'template': 'registration/activation_complete.html' },
                           name='registration_activation_complete'),
                       # Activation keys get matched by \w+ instead of the more specific
                       # [a-fA-F0-9]{40} because a bad activation key should still get to the view;
                       # that way it can return a sensible "invalid key" message instead of a
                       # confusing 404.
                       url(r'^activate/(?P<activation_key>\w+)/$',
                           activate,
                           { 'backend': 'registration.backends.default.DefaultBackend' },
                           name='registration_activate'),
                       url(r'^register/$',
                           register,
                           { 'backend': 'registration.backends.default.DefaultBackend' },
                           name='registration_register'),
                       url(r'^register/complete/$',
                           direct_to_template,
                           { 'template': 'registration/registration_complete.html' },
                           name='registration_complete'),
                       url(r'^register/closed/$',
                           direct_to_template,
                           { 'template': 'registration/registration_closed.html' },
                           name='registration_disallowed'),
                       (r'', include('registration.auth_urls')),
                       )

########NEW FILE########
__FILENAME__ = forms
"""
Forms and validation code for user registration.

"""


from django.contrib.auth.models import User
from django import forms
from django.utils.translation import ugettext_lazy as _


# I put this on all required fields, because it's easier to pick up
# on them with CSS or JavaScript if they have a class of "required"
# in the HTML. Your mileage may vary. If/when Django ticket #3515
# lands in trunk, this will no longer be necessary.
attrs_dict = { 'class': 'required' }


class RegistrationForm(forms.Form):
    """
    Form for registering a new user account.
    
    Validates that the requested username is not already in use, and
    requires the password to be entered twice to catch typos.
    
    Subclasses should feel free to add any additional validation they
    need, but should avoid defining a ``save()`` method -- the actual
    saving of collected user data is delegated to the active
    registration backend.
    
    """
    username = forms.RegexField(regex=r'^\w+$',
                                max_length=30,
                                widget=forms.TextInput(attrs=attrs_dict),
                                label=_("Username"),
                                error_messages={ 'invalid': _("This value must contain only letters, numbers and underscores.") })
    email = forms.EmailField(widget=forms.TextInput(attrs=dict(attrs_dict,
                                                               maxlength=75)),
                             label=_("Email address"))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs=attrs_dict, render_value=False),
                                label=_("Password"))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs=attrs_dict, render_value=False),
                                label=_("Password (again)"))
    
    def clean_username(self):
        """
        Validate that the username is alphanumeric and is not already
        in use.
        
        """
        try:
            user = User.objects.get(username__iexact=self.cleaned_data['username'])
        except User.DoesNotExist:
            return self.cleaned_data['username']
        raise forms.ValidationError(_("A user with that username already exists."))

    def clean(self):
        """
        Verifiy that the values entered into the two password fields
        match. Note that an error here will end up in
        ``non_field_errors()`` because it doesn't apply to a single
        field.
        
        """
        if 'password1' in self.cleaned_data and 'password2' in self.cleaned_data:
            if self.cleaned_data['password1'] != self.cleaned_data['password2']:
                raise forms.ValidationError(_("The two password fields didn't match."))
        return self.cleaned_data


class RegistrationFormTermsOfService(RegistrationForm):
    """
    Subclass of ``RegistrationForm`` which adds a required checkbox
    for agreeing to a site's Terms of Service.
    
    """
    tos = forms.BooleanField(widget=forms.CheckboxInput(attrs=attrs_dict),
                             label=_(u'I have read and agree to the Terms of Service'),
                             error_messages={ 'required': _("You must agree to the terms to register") })


class RegistrationFormUniqueEmail(RegistrationForm):
    """
    Subclass of ``RegistrationForm`` which enforces uniqueness of
    email addresses.
    
    """
    def clean_email(self):
        """
        Validate that the supplied email address is unique for the
        site.
        
        """
        if User.objects.filter(email__iexact=self.cleaned_data['email']):
            raise forms.ValidationError(_("This email address is already in use. Please supply a different email address."))
        return self.cleaned_data['email']


class RegistrationFormNoFreeEmail(RegistrationForm):
    """
    Subclass of ``RegistrationForm`` which disallows registration with
    email addresses from popular free webmail services; moderately
    useful for preventing automated spam registrations.
    
    To change the list of banned domains, subclass this form and
    override the attribute ``bad_domains``.
    
    """
    bad_domains = ['aim.com', 'aol.com', 'email.com', 'gmail.com',
                   'googlemail.com', 'hotmail.com', 'hushmail.com',
                   'msn.com', 'mail.ru', 'mailinator.com', 'live.com',
                   'yahoo.com']
    
    def clean_email(self):
        """
        Check the supplied email address against a list of known free
        webmail domains.
        
        """
        email_domain = self.cleaned_data['email'].split('@')[1]
        if email_domain in self.bad_domains:
            raise forms.ValidationError(_("Registration using free email addresses is prohibited. Please supply a different email address."))
        return self.cleaned_data['email']

########NEW FILE########
__FILENAME__ = cleanupregistration
"""
A management command which deletes expired accounts (e.g.,
accounts which signed up but never activated) from the database.

Calls ``RegistrationProfile.objects.delete_expired_users()``, which
contains the actual logic for determining which accounts are deleted.

"""

from django.core.management.base import NoArgsCommand

from registration.models import RegistrationProfile


class Command(NoArgsCommand):
    help = "Delete expired user registrations from the database"

    def handle_noargs(self, **options):
        RegistrationProfile.objects.delete_expired_users()

########NEW FILE########
__FILENAME__ = models
import datetime
import random
import re

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db import transaction
from django.template.loader import render_to_string
from django.utils.hashcompat import sha_constructor
from django.utils.translation import ugettext_lazy as _


SHA1_RE = re.compile('^[a-f0-9]{40}$')


class RegistrationManager(models.Manager):
    """
    Custom manager for the ``RegistrationProfile`` model.
    
    The methods defined here provide shortcuts for account creation
    and activation (including generation and emailing of activation
    keys), and for cleaning out expired inactive accounts.
    
    """
    def activate_user(self, activation_key):
        """
        Validate an activation key and activate the corresponding
        ``User`` if valid.
        
        If the key is valid and has not expired, return the ``User``
        after activating.
        
        If the key is not valid or has expired, return ``False``.
        
        If the key is valid but the ``User`` is already active,
        return ``False``.
        
        To prevent reactivation of an account which has been
        deactivated by site administrators, the activation key is
        reset to the string constant ``RegistrationProfile.ACTIVATED``
        after successful activation.

        """
        # Make sure the key we're trying conforms to the pattern of a
        # SHA1 hash; if it doesn't, no point trying to look it up in
        # the database.
        if SHA1_RE.search(activation_key):
            try:
                profile = self.get(activation_key=activation_key)
            except self.model.DoesNotExist:
                return False
            if not profile.activation_key_expired():
                user = profile.user
                user.is_active = True
                user.save()
                profile.activation_key = self.model.ACTIVATED
                profile.save()
                return user
        return False
    
    def create_inactive_user(self, username, email, password,
                             site, send_email=True):
        """
        Create a new, inactive ``User``, generate a
        ``RegistrationProfile`` and email its activation key to the
        ``User``, returning the new ``User``.

        By default, an activation email will be sent to the new
        user. To disable this, pass ``send_email=False``.
        
        """
        new_user = User.objects.create_user(username, email, password)
        new_user.is_active = False
        new_user.save()

        registration_profile = self.create_profile(new_user)

        if send_email:
            registration_profile.send_activation_email(site)

        return new_user
    create_inactive_user = transaction.commit_on_success(create_inactive_user)

    def create_profile(self, user):
        """
        Create a ``RegistrationProfile`` for a given
        ``User``, and return the ``RegistrationProfile``.
        
        The activation key for the ``RegistrationProfile`` will be a
        SHA1 hash, generated from a combination of the ``User``'s
        username and a random salt.
        
        """
        salt = sha_constructor(str(random.random())).hexdigest()[:5]
        username = user.username
        if isinstance(username, unicode):
            username = username.encode('utf-8')
        activation_key = sha_constructor(salt+username).hexdigest()
        return self.create(user=user,
                           activation_key=activation_key)
        
    def delete_expired_users(self):
        """
        Remove expired instances of ``RegistrationProfile`` and their
        associated ``User``s.
        
        Accounts to be deleted are identified by searching for
        instances of ``RegistrationProfile`` with expired activation
        keys, and then checking to see if their associated ``User``
        instances have the field ``is_active`` set to ``False``; any
        ``User`` who is both inactive and has an expired activation
        key will be deleted.
        
        It is recommended that this method be executed regularly as
        part of your routine site maintenance; this application
        provides a custom management command which will call this
        method, accessible as ``manage.py cleanupregistration``.
        
        Regularly clearing out accounts which have never been
        activated serves two useful purposes:
        
        1. It alleviates the ocasional need to reset a
           ``RegistrationProfile`` and/or re-send an activation email
           when a user does not receive or does not act upon the
           initial activation email; since the account will be
           deleted, the user will be able to simply re-register and
           receive a new activation key.
        
        2. It prevents the possibility of a malicious user registering
           one or more accounts and never activating them (thus
           denying the use of those usernames to anyone else); since
           those accounts will be deleted, the usernames will become
           available for use again.
        
        If you have a troublesome ``User`` and wish to disable their
        account while keeping it in the database, simply delete the
        associated ``RegistrationProfile``; an inactive ``User`` which
        does not have an associated ``RegistrationProfile`` will not
        be deleted.
        
        """
        for profile in self.all():
            if profile.activation_key_expired():
                user = profile.user
                if not user.is_active:
                    user.delete()


class RegistrationProfile(models.Model):
    """
    A simple profile which stores an activation key for use during
    user account registration.
    
    Generally, you will not want to interact directly with instances
    of this model; the provided manager includes methods
    for creating and activating new accounts, as well as for cleaning
    out accounts which have never been activated.
    
    While it is possible to use this model as the value of the
    ``AUTH_PROFILE_MODULE`` setting, it's not recommended that you do
    so. This model's sole purpose is to store data temporarily during
    account registration and activation.
    
    """
    ACTIVATED = u"ALREADY_ACTIVATED"
    
    user = models.ForeignKey(User, unique=True, verbose_name=_('user'))
    activation_key = models.CharField(_('activation key'), max_length=40)
    
    objects = RegistrationManager()
    
    class Meta:
        verbose_name = _('registration profile')
        verbose_name_plural = _('registration profiles')
    
    def __unicode__(self):
        return u"Registration information for %s" % self.user
    
    def activation_key_expired(self):
        """
        Determine whether this ``RegistrationProfile``'s activation
        key has expired, returning a boolean -- ``True`` if the key
        has expired.
        
        Key expiration is determined by a two-step process:
        
        1. If the user has already activated, the key will have been
           reset to the string constant ``ACTIVATED``. Re-activating
           is not permitted, and so this method returns ``True`` in
           this case.

        2. Otherwise, the date the user signed up is incremented by
           the number of days specified in the setting
           ``ACCOUNT_ACTIVATION_DAYS`` (which should be the number of
           days after signup during which a user is allowed to
           activate their account); if the result is less than or
           equal to the current date, the key has expired and this
           method returns ``True``.
        
        """
        expiration_date = datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS)
        return self.activation_key == self.ACTIVATED or \
               (self.user.date_joined + expiration_date <= datetime.datetime.now())
    activation_key_expired.boolean = True

    def send_activation_email(self, site):
        """
        Send an activation email to the user associated with this
        ``RegistrationProfile``.
        
        The activation email will make use of two templates:

        ``registration/activation_email_subject.txt``
            This template will be used for the subject line of the
            email. Because it is used as the subject line of an email,
            this template's output **must** be only a single line of
            text; output longer than one line will be forcibly joined
            into only a single line.

        ``registration/activation_email.txt``
            This template will be used for the body of the email.

        These templates will each receive the following context
        variables:

        ``activation_key``
            The activation key for the new account.

        ``expiration_days``
            The number of days remaining during which the account may
            be activated.

        ``site``
            An object representing the site on which the user
            registered; depending on whether ``django.contrib.sites``
            is installed, this may be an instance of either
            ``django.contrib.sites.models.Site`` (if the sites
            application is installed) or
            ``django.contrib.sites.models.RequestSite`` (if
            not). Consult the documentation for the Django sites
            framework for details regarding these objects' interfaces.

        """
        ctx_dict = { 'activation_key': self.activation_key,
                     'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS,
                     'site': site }
        subject = render_to_string('registration/activation_email_subject.txt',
                                   ctx_dict)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        
        message = render_to_string('registration/activation_email.txt',
                                   ctx_dict)
        
        self.user.email_user(subject, message, settings.DEFAULT_FROM_EMAIL)
    

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal


# A new user has registered.
user_registered = Signal(providing_args=["user", "request"])

# A user has activated his or her account.
user_activated = Signal(providing_args=["user", "request"])

########NEW FILE########
__FILENAME__ = backends
import datetime

from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.core.handlers.wsgi import WSGIRequest
from django.test import Client
from django.test import TestCase

from registration import forms
from registration import signals
from registration.admin import RegistrationAdmin
from registration.backends import get_backend
from registration.backends.default import DefaultBackend
from registration.models import RegistrationProfile


class _MockRequestClient(Client):
    """
    A ``django.test.Client`` subclass which can return mock
    ``HttpRequest`` objects.
    
    """
    def request(self, **request):
        """
        Rather than issuing a request and returning the response, this
        simply constructs an ``HttpRequest`` object and returns it.
        
        """
        environ = {
            'HTTP_COOKIE':      self.cookies,
            'PATH_INFO':         '/',
            'QUERY_STRING':      '',
            'REMOTE_ADDR':       '127.0.0.1',
            'REQUEST_METHOD':    'GET',
            'SCRIPT_NAME':       '',
            'SERVER_NAME':       'testserver',
            'SERVER_PORT':       '80',
            'SERVER_PROTOCOL':   'HTTP/1.1',
            'wsgi.version':      (1,0),
            'wsgi.url_scheme':   'http',
            'wsgi.errors':       self.errors,
            'wsgi.multiprocess': True,
            'wsgi.multithread':  False,
            'wsgi.run_once':     False,
            }
        environ.update(self.defaults)
        environ.update(request)
        return WSGIRequest(environ)


def _mock_request():
    """
    Construct and return a mock ``HttpRequest`` object; this is used
    in testing backend methods which expect an ``HttpRequest`` but
    which are not being called from views.
    
    """
    return _MockRequestClient().request()


class BackendRetrievalTests(TestCase):
    """
    Test that utilities for retrieving the active backend work
    properly.

    """
    def test_get_backend(self):
        """
        Verify that ``get_backend()`` returns the correct value when
        passed a valid backend.

        """
        self.failUnless(isinstance(get_backend('registration.backends.default.DefaultBackend'),
                                   DefaultBackend))

    def test_backend_error_invalid(self):
        """
        Test that a nonexistent/unimportable backend raises the
        correct exception.

        """
        self.assertRaises(ImproperlyConfigured, get_backend,
                          'registration.backends.doesnotexist.NonExistentBackend')

    def test_backend_attribute_error(self):
        """
        Test that a backend module which exists but does not have a
        class of the specified name raises the correct exception.
        
        """
        self.assertRaises(ImproperlyConfigured, get_backend,
                          'registration.backends.default.NonexistentBackend')


class DefaultRegistrationBackendTests(TestCase):
    """
    Test the default registration backend.

    Running these tests successfull will require two templates to be
    created for the sending of activation emails; details on these
    templates and their contexts may be found in the documentation for
    the default backend.

    """
    def setUp(self):
        """
        Create an instance of the default backend for use in testing,
        and set ``ACCOUNT_ACTIVATION_DAYS`` if it's not set already.

        """
        from registration.backends.default import DefaultBackend
        self.backend = DefaultBackend()
        self.old_activation = getattr(settings, 'ACCOUNT_ACTIVATION_DAYS', None)
        if self.old_activation is None:
            settings.ACCOUNT_ACTIVATION_DAYS = 7

    def tearDown(self):
        """
        Yank out ``ACCOUNT_ACTIVATION_DAYS`` back out if it wasn't
        originally set.

        """
        if self.old_activation is None:
            settings.ACCOUNT_ACTIVATION_DAYS = self.old_activation

    def test_registration(self):
        """
        Test the registration process: registration creates a new
        inactive account and a new profile with activation key,
        populates the correct account data and sends an activation
        email.

        """
        new_user = self.backend.register(_mock_request(),
                                         username='bob',
                                         email='bob@example.com',
                                         password1='secret')

        # Details of the returned user must match what went in.
        self.assertEqual(new_user.username, 'bob')
        self.failUnless(new_user.check_password('secret'))
        self.assertEqual(new_user.email, 'bob@example.com')

        # New user must not be active.
        self.failIf(new_user.is_active)

        # A registration profile was created, and an activation email
        # was sent.
        self.assertEqual(RegistrationProfile.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_registration_no_sites(self):
        """
        Test that registration still functions properly when
        ``django.contrib.sites`` is not installed; the fallback will
        be a ``RequestSite`` instance.
        
        """
        Site._meta.installed = False

        new_user = self.backend.register(_mock_request(),
                                         username='bob',
                                         email='bob@example.com',
                                         password1='secret')

        self.assertEqual(new_user.username, 'bob')
        self.failUnless(new_user.check_password('secret'))
        self.assertEqual(new_user.email, 'bob@example.com')

        self.failIf(new_user.is_active)

        self.assertEqual(RegistrationProfile.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        
        Site._meta.installed = True

    def test_valid_activation(self):
        """
        Test the activation process: activating within the permitted
        window sets the account's ``is_active`` field to ``True`` and
        resets the activation key.

        """
        valid_user = self.backend.register(_mock_request(),
                                           username='alice',
                                           email='alice@example.com',
                                           password1='swordfish')

        valid_profile = RegistrationProfile.objects.get(user=valid_user)
        activated = self.backend.activate(_mock_request(),
                                          valid_profile.activation_key)
        self.assertEqual(activated.username, valid_user.username)
        self.failUnless(activated.is_active)

        # Fetch the profile again to verify its activation key has
        # been reset.
        valid_profile = RegistrationProfile.objects.get(user=valid_user)
        self.assertEqual(valid_profile.activation_key,
                         RegistrationProfile.ACTIVATED)

    def test_invalid_activation(self):
        """
        Test the activation process: trying to activate outside the
        permitted window fails, and leaves the account inactive.

        """
        expired_user = self.backend.register(_mock_request(),
                                             username='bob',
                                             email='bob@example.com',
                                             password1='secret')

        expired_user.date_joined = expired_user.date_joined - datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS)
        expired_user.save()
        expired_profile = RegistrationProfile.objects.get(user=expired_user)
        self.failIf(self.backend.activate(_mock_request(),
                                          expired_profile.activation_key))
        self.failUnless(expired_profile.activation_key_expired())

    def test_allow(self):
        """
        Test that the setting ``REGISTRATION_OPEN`` appropriately
        controls whether registration is permitted.

        """
        old_allowed = getattr(settings, 'REGISTRATION_OPEN', True)
        settings.REGISTRATION_OPEN = True
        self.failUnless(self.backend.registration_allowed(_mock_request()))

        settings.REGISTRATION_OPEN = False
        self.failIf(self.backend.registration_allowed(_mock_request()))
        settings.REGISTRATION_OPEN = old_allowed

    def test_form_class(self):
        """
        Test that the default form class returned is
        ``registration.forms.RegistrationForm``.

        """
        self.failUnless(self.backend.get_form_class(_mock_request()) is forms.RegistrationForm)

    def test_post_registration_redirect(self):
        """
        Test that the default post-registration redirect is the named
        pattern ``registration_complete``.

        """
        self.assertEqual(self.backend.post_registration_redirect(_mock_request(), User()),
                         ('registration_complete', (), {}))

    def test_registration_signal(self):
        """
        Test that registering a user sends the ``user_registered``
        signal.
        
        """
        def receiver(sender, **kwargs):
            self.failUnless('user' in kwargs)
            self.assertEqual(kwargs['user'].username, 'bob')
            self.failUnless('request' in kwargs)
            self.failUnless(isinstance(kwargs['request'], WSGIRequest))
            received_signals.append(kwargs.get('signal'))

        received_signals = []
        signals.user_registered.connect(receiver, sender=self.backend.__class__)

        self.backend.register(_mock_request(),
                              username='bob',
                              email='bob@example.com',
                              password1='secret')

        self.assertEqual(len(received_signals), 1)
        self.assertEqual(received_signals, [signals.user_registered])

    def test_activation_signal_success(self):
        """
        Test that successfully activating a user sends the
        ``user_activated`` signal.
        
        """
        def receiver(sender, **kwargs):
            self.failUnless('user' in kwargs)
            self.assertEqual(kwargs['user'].username, 'bob')
            self.failUnless('request' in kwargs)
            self.failUnless(isinstance(kwargs['request'], WSGIRequest))
            received_signals.append(kwargs.get('signal'))

        received_signals = []
        signals.user_activated.connect(receiver, sender=self.backend.__class__)

        new_user = self.backend.register(_mock_request(),
                                         username='bob',
                                         email='bob@example.com',
                                         password1='secret')
        profile = RegistrationProfile.objects.get(user=new_user)
        self.backend.activate(_mock_request(), profile.activation_key)

        self.assertEqual(len(received_signals), 1)
        self.assertEqual(received_signals, [signals.user_activated])

    def test_activation_signal_failure(self):
        """
        Test that an unsuccessful activation attempt does not send the
        ``user_activated`` signal.
        
        """
        receiver = lambda sender, **kwargs: received_signals.append(kwargs.get('signal'))

        received_signals = []
        signals.user_activated.connect(receiver, sender=self.backend.__class__)

        new_user = self.backend.register(_mock_request(),
                                         username='bob',
                                         email='bob@example.com',
                                         password1='secret')
        new_user.date_joined -= datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS + 1)
        new_user.save()
        profile = RegistrationProfile.objects.get(user=new_user)
        self.backend.activate(_mock_request(), profile.activation_key)

        self.assertEqual(len(received_signals), 0)

    def test_email_send_action(self):
        """
        Test re-sending of activation emails via admin action.
        
        """
        admin_class = RegistrationAdmin(RegistrationProfile, admin.site)
        
        alice = self.backend.register(_mock_request(),
                                      username='alice',
                                      email='alice@example.com',
                                      password1='swordfish')
        
        admin_class.resend_activation_email(_mock_request(),
                                            RegistrationProfile.objects.all())
        self.assertEqual(len(mail.outbox), 2) # One on registering, one more on the resend.
        
        RegistrationProfile.objects.filter(user=alice).update(activation_key=RegistrationProfile.ACTIVATED)
        admin_class.resend_activation_email(_mock_request(),
                                            RegistrationProfile.objects.all())
        self.assertEqual(len(mail.outbox), 2) # No additional email because the account has activated.

    def test_activation_action(self):
        """
        Test manual activation of users view admin action.
        
        """
        admin_class = RegistrationAdmin(RegistrationProfile, admin.site)

        alice = self.backend.register(_mock_request(),
                                      username='alice',
                                      email='alice@example.com',
                                      password1='swordfish')

        admin_class.activate_users(_mock_request(),
                                   RegistrationProfile.objects.all())
        self.failUnless(User.objects.get(username='alice').is_active)

########NEW FILE########
__FILENAME__ = forms
from django.contrib.auth.models import User
from django.test import TestCase

from registration import forms


class RegistrationFormTests(TestCase):
    """
    Test the default registration forms.

    """
    def test_registration_form(self):
        """
        Test that ``RegistrationForm`` enforces username constraints
        and matching passwords.

        """
        # Create a user so we can verify that duplicate usernames aren't
        # permitted.
        User.objects.create_user('alice', 'alice@example.com', 'secret')

        invalid_data_dicts = [
            # Non-alphanumeric username.
            {'data': {'username': 'foo/bar',
                      'email': 'foo@example.com',
                      'password1': 'foo',
                      'password2': 'foo'},
            'error': ('username', [u"This value must contain only letters, numbers and underscores."])},
            # Already-existing username.
            {'data': {'username': 'alice',
                      'email': 'alice@example.com',
                      'password1': 'secret',
                      'password2': 'secret'},
            'error': ('username', [u"A user with that username already exists."])},
            # Mismatched passwords.
            {'data': {'username': 'foo',
                      'email': 'foo@example.com',
                      'password1': 'foo',
                      'password2': 'bar'},
            'error': ('__all__', [u"The two password fields didn't match."])},
            ]

        for invalid_dict in invalid_data_dicts:
            form = forms.RegistrationForm(data=invalid_dict['data'])
            self.failIf(form.is_valid())
            self.assertEqual(form.errors[invalid_dict['error'][0]],
                             invalid_dict['error'][1])

        form = forms.RegistrationForm(data={'username': 'foo',
                                            'email': 'foo@example.com',
                                            'password1': 'foo',
                                            'password2': 'foo'})
        self.failUnless(form.is_valid())

    def test_registration_form_tos(self):
        """
        Test that ``RegistrationFormTermsOfService`` requires
        agreement to the terms of service.

        """
        form = forms.RegistrationFormTermsOfService(data={'username': 'foo',
                                                          'email': 'foo@example.com',
                                                          'password1': 'foo',
                                                          'password2': 'foo'})
        self.failIf(form.is_valid())
        self.assertEqual(form.errors['tos'],
                         [u"You must agree to the terms to register"])

        form = forms.RegistrationFormTermsOfService(data={'username': 'foo',
                                                          'email': 'foo@example.com',
                                                          'password1': 'foo',
                                                          'password2': 'foo',
                                                          'tos': 'on'})
        self.failUnless(form.is_valid())

    def test_registration_form_unique_email(self):
        """
        Test that ``RegistrationFormUniqueEmail`` validates uniqueness
        of email addresses.

        """
        # Create a user so we can verify that duplicate addresses
        # aren't permitted.
        User.objects.create_user('alice', 'alice@example.com', 'secret')

        form = forms.RegistrationFormUniqueEmail(data={'username': 'foo',
                                                       'email': 'alice@example.com',
                                                       'password1': 'foo',
                                                       'password2': 'foo'})
        self.failIf(form.is_valid())
        self.assertEqual(form.errors['email'],
                         [u"This email address is already in use. Please supply a different email address."])

        form = forms.RegistrationFormUniqueEmail(data={'username': 'foo',
                                                       'email': 'foo@example.com',
                                                       'password1': 'foo',
                                                       'password2': 'foo'})
        self.failUnless(form.is_valid())

    def test_registration_form_no_free_email(self):
        """
        Test that ``RegistrationFormNoFreeEmail`` disallows
        registration with free email addresses.

        """
        base_data = {'username': 'foo',
                     'password1': 'foo',
                     'password2': 'foo'}
        for domain in forms.RegistrationFormNoFreeEmail.bad_domains:
            invalid_data = base_data.copy()
            invalid_data['email'] = u"foo@%s" % domain
            form = forms.RegistrationFormNoFreeEmail(data=invalid_data)
            self.failIf(form.is_valid())
            self.assertEqual(form.errors['email'],
                             [u"Registration using free email addresses is prohibited. Please supply a different email address."])

        base_data['email'] = 'foo@example.com'
        form = forms.RegistrationFormNoFreeEmail(data=base_data)
        self.failUnless(form.is_valid())

########NEW FILE########
__FILENAME__ = models
import datetime
import re

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core import mail
from django.core import management
from django.test import TestCase
from django.utils.hashcompat import sha_constructor

from registration.models import RegistrationProfile


class RegistrationModelTests(TestCase):
    """
    Test the model and manager used in the default backend.
    
    """
    user_info = {'username': 'alice',
                 'password': 'swordfish',
                 'email': 'alice@example.com'}
    
    def setUp(self):
        self.old_activation = getattr(settings, 'ACCOUNT_ACTIVATION_DAYS', None)
        settings.ACCOUNT_ACTIVATION_DAYS = 7

    def tearDown(self):
        settings.ACCOUNT_ACTIVATION_DAYS = self.old_activation

    def test_profile_creation(self):
        """
        Creating a registration profile for a user populates the
        profile with the correct user and a SHA1 hash to use as
        activation key.
        
        """
        new_user = User.objects.create_user(**self.user_info)
        profile = RegistrationProfile.objects.create_profile(new_user)

        self.assertEqual(RegistrationProfile.objects.count(), 1)
        self.assertEqual(profile.user.id, new_user.id)
        self.failUnless(re.match('^[a-f0-9]{40}$', profile.activation_key))
        self.assertEqual(unicode(profile),
                         "Registration information for alice")

    def test_activation_email(self):
        """
        ``RegistrationProfile.send_activation_email`` sends an
        email.
        
        """
        new_user = User.objects.create_user(**self.user_info)
        profile = RegistrationProfile.objects.create_profile(new_user)
        profile.send_activation_email(Site.objects.get_current())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user_info['email']])

    def test_user_creation(self):
        """
        Creating a new user populates the correct data, and sets the
        user's account inactive.
        
        """
        new_user = RegistrationProfile.objects.create_inactive_user(site=Site.objects.get_current(),
                                                                    **self.user_info)
        self.assertEqual(new_user.username, 'alice')
        self.assertEqual(new_user.email, 'alice@example.com')
        self.failUnless(new_user.check_password('swordfish'))
        self.failIf(new_user.is_active)

    def test_user_creation_email(self):
        """
        By default, creating a new user sends an activation email.
        
        """
        new_user = RegistrationProfile.objects.create_inactive_user(site=Site.objects.get_current(),
                                                                    **self.user_info)
        self.assertEqual(len(mail.outbox), 1)

    def test_user_creation_no_email(self):
        """
        Passing ``send_email=False`` when creating a new user will not
        send an activation email.
        
        """
        new_user = RegistrationProfile.objects.create_inactive_user(site=Site.objects.get_current(),
                                                                    send_email=False,
                                                                    **self.user_info)
        self.assertEqual(len(mail.outbox), 0)

    def test_unexpired_account(self):
        """
        ``RegistrationProfile.activation_key_expired()`` is ``False``
        within the activation window.
        
        """
        new_user = RegistrationProfile.objects.create_inactive_user(site=Site.objects.get_current(),
                                                                    **self.user_info)
        profile = RegistrationProfile.objects.get(user=new_user)
        self.failIf(profile.activation_key_expired())

    def test_expired_account(self):
        """
        ``RegistrationProfile.activation_key_expired()`` is ``True``
        outside the activation window.
        
        """
        new_user = RegistrationProfile.objects.create_inactive_user(site=Site.objects.get_current(),
                                                                    **self.user_info)
        new_user.date_joined -= datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS + 1)
        new_user.save()
        profile = RegistrationProfile.objects.get(user=new_user)
        self.failUnless(profile.activation_key_expired())

    def test_valid_activation(self):
        """
        Activating a user within the permitted window makes the
        account active, and resets the activation key.
        
        """
        new_user = RegistrationProfile.objects.create_inactive_user(site=Site.objects.get_current(),
                                                                    **self.user_info)
        profile = RegistrationProfile.objects.get(user=new_user)
        activated = RegistrationProfile.objects.activate_user(profile.activation_key)

        self.failUnless(isinstance(activated, User))
        self.assertEqual(activated.id, new_user.id)
        self.failUnless(activated.is_active)

        profile = RegistrationProfile.objects.get(user=new_user)
        self.assertEqual(profile.activation_key, RegistrationProfile.ACTIVATED)

    def test_expired_activation(self):
        """
        Attempting to activate outside the permitted window does not
        activate the account.
        
        """
        new_user = RegistrationProfile.objects.create_inactive_user(site=Site.objects.get_current(),
                                                                    **self.user_info)
        new_user.date_joined -= datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS + 1)
        new_user.save()

        profile = RegistrationProfile.objects.get(user=new_user)
        activated = RegistrationProfile.objects.activate_user(profile.activation_key)

        self.failIf(isinstance(activated, User))
        self.failIf(activated)

        new_user = User.objects.get(username='alice')
        self.failIf(new_user.is_active)

        profile = RegistrationProfile.objects.get(user=new_user)
        self.assertNotEqual(profile.activation_key, RegistrationProfile.ACTIVATED)

    def test_activation_invalid_key(self):
        """
        Attempting to activate with a key which is not a SHA1 hash
        fails.
        
        """
        self.failIf(RegistrationProfile.objects.activate_user('foo'))

    def test_activation_already_activated(self):
        """
        Attempting to re-activate an already-activated account fails.
        
        """
        new_user = RegistrationProfile.objects.create_inactive_user(site=Site.objects.get_current(),
                                                                    **self.user_info)
        profile = RegistrationProfile.objects.get(user=new_user)
        RegistrationProfile.objects.activate_user(profile.activation_key)

        profile = RegistrationProfile.objects.get(user=new_user)
        self.failIf(RegistrationProfile.objects.activate_user(profile.activation_key))

    def test_activation_nonexistent_key(self):
        """
        Attempting to activate with a non-existent key (i.e., one not
        associated with any account) fails.
        
        """
        # Due to the way activation keys are constructed during
        # registration, this will never be a valid key.
        invalid_key = sha_constructor('foo').hexdigest()
        self.failIf(RegistrationProfile.objects.activate_user(invalid_key))

    def test_expired_user_deletion(self):
        """
        ``RegistrationProfile.objects.delete_expired_users()`` only
        deletes inactive users whose activation window has expired.
        
        """
        new_user = RegistrationProfile.objects.create_inactive_user(site=Site.objects.get_current(),
                                                                    **self.user_info)
        expired_user = RegistrationProfile.objects.create_inactive_user(site=Site.objects.get_current(),
                                                                        username='bob',
                                                                        password='secret',
                                                                        email='bob@example.com')
        expired_user.date_joined -= datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS + 1)
        expired_user.save()

        RegistrationProfile.objects.delete_expired_users()
        self.assertEqual(RegistrationProfile.objects.count(), 1)
        self.assertRaises(User.DoesNotExist, User.objects.get, username='bob')

    def test_management_command(self):
        """
        The ``cleanupregistration`` management command properly
        deletes expired accounts.
        
        """
        new_user = RegistrationProfile.objects.create_inactive_user(site=Site.objects.get_current(),
                                                                    **self.user_info)
        expired_user = RegistrationProfile.objects.create_inactive_user(site=Site.objects.get_current(),
                                                                        username='bob',
                                                                        password='secret',
                                                                        email='bob@example.com')
        expired_user.date_joined -= datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS + 1)
        expired_user.save()

        management.call_command('cleanupregistration')
        self.assertEqual(RegistrationProfile.objects.count(), 1)
        self.assertRaises(User.DoesNotExist, User.objects.get, username='bob')

########NEW FILE########
__FILENAME__ = urls
"""
URLs used in the unit tests for django-registration.

You should not attempt to use these URLs in any sort of real or
development environment; instead, use
``registration/backends/default/urls.py``. This URLconf includes those
URLs, and also adds several additional URLs which serve no purpose
other than to test that optional keyword arguments are properly
handled.

"""

from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template

from registration.views import activate
from registration.views import register


urlpatterns = patterns('',
                       # Test the 'activate' view with custom template
                       # name.
                       url(r'^activate-with-template-name/(?P<activation_key>\w+)/$',
                           activate,
                           {'template_name': 'registration/test_template_name.html',
                            'backend': 'registration.backends.default.DefaultBackend'},
                           name='registration_test_activate_template_name'),
                       # Test the 'activate' view with
                       # extra_context_argument.
                       url(r'^activate-extra-context/(?P<activation_key>\w+)/$',
                           activate,
                           {'extra_context': {'foo': 'bar', 'callable': lambda: 'called'},
                            'backend': 'registration.backends.default.DefaultBackend'},
                           name='registration_test_activate_extra_context'),
                       # Test the 'activate' view with success_url argument.
                       url(r'^activate-with-success-url/(?P<activation_key>\w+)/$',
                           activate,
                           {'success_url': 'registration_test_custom_success_url',
                            'backend': 'registration.backends.default.DefaultBackend'},
                           name='registration_test_activate_success_url'),
                       # Test the 'register' view with custom template
                       # name.
                       url(r'^register-with-template-name/$',
                           register,
                           {'template_name': 'registration/test_template_name.html',
                            'backend': 'registration.backends.default.DefaultBackend'},
                           name='registration_test_register_template_name'),
                       # Test the'register' view with extra_context
                       # argument.
                       url(r'^register-extra-context/$',
                           register,
                           {'extra_context': {'foo': 'bar', 'callable': lambda: 'called'},
                            'backend': 'registration.backends.default.DefaultBackend'},
                           name='registration_test_register_extra_context'),
                       # Test the 'register' view with custom URL for
                       # closed registration.
                       url(r'^register-with-disallowed-url/$',
                           register,
                           {'disallowed_url': 'registration_test_custom_disallowed',
                            'backend': 'registration.backends.default.DefaultBackend'},
                           name='registration_test_register_disallowed_url'),
                       # Set up a pattern which will correspond to the
                       # custom 'disallowed_url' above.
                       url(r'^custom-disallowed/$',
                           direct_to_template,
                           {'template': 'registration/registration_closed.html'},
                           name='registration_test_custom_disallowed'),
                       # Test the 'register' view with custom redirect
                       # on successful registration.
                       url(r'^register-with-success_url/$',
                           register,
                           {'success_url': 'registration_test_custom_success_url',
                            'backend': 'registration.backends.default.DefaultBackend'},
                           name='registration_test_register_success_url'
                           ),
                       # Pattern for custom redirect set above.
                       url(r'^custom-success/$',
                           direct_to_template,
                           {'template': 'registration/test_template_name.html'},
                           name='registration_test_custom_success_url'),
                       (r'', include('registration.backends.default.urls')),
                       )

########NEW FILE########
__FILENAME__ = views
import datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase

from registration import forms
from registration.models import RegistrationProfile


class RegistrationViewTests(TestCase):
    """
    Test the registration views.

    """
    urls = 'registration.tests.urls'

    def setUp(self):
        """
        These tests use the default backend, since we know it's
        available; that needs to have ``ACCOUNT_ACTIVATION_DAYS`` set.

        """
        self.old_activation = getattr(settings, 'ACCOUNT_ACTIVATION_DAYS', None)
        if self.old_activation is None:
            settings.ACCOUNT_ACTIVATION_DAYS = 7

    def tearDown(self):
        """
        Yank ``ACCOUNT_ACTIVATION_DAYS`` back out if it wasn't
        originally set.

        """
        if self.old_activation is None:
            settings.ACCOUNT_ACTIVATION_DAYS = self.old_activation

    def test_registration_view_initial(self):
        """
        A ``GET`` to the ``register`` view uses the appropriate
        template and populates the registration form into the context.

        """
        response = self.client.get(reverse('registration_register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response,
                                'registration/registration_form.html')
        self.failUnless(isinstance(response.context['form'],
                                   forms.RegistrationForm))

    def test_registration_view_success(self):
        """
        A ``POST`` to the ``register`` view with valid data properly
        creates a new user and issues a redirect.

        """
        response = self.client.post(reverse('registration_register'),
                                    data={'username': 'alice',
                                          'email': 'alice@example.com',
                                          'password1': 'swordfish',
                                          'password2': 'swordfish'})
        self.assertRedirects(response,
                             'http://testserver%s' % reverse('registration_complete'))
        self.assertEqual(RegistrationProfile.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_registration_view_failure(self):
        """
        A ``POST`` to the ``register`` view with invalid data does not
        create a user, and displays appropriate error messages.

        """
        response = self.client.post(reverse('registration_register'),
                                    data={'username': 'bob',
                                          'email': 'bobe@example.com',
                                          'password1': 'foo',
                                          'password2': 'bar'})
        self.assertEqual(response.status_code, 200)
        self.failIf(response.context['form'].is_valid())
        self.assertFormError(response, 'form', field=None,
                             errors=u"The two password fields didn't match.")
        self.assertEqual(len(mail.outbox), 0)

    def test_registration_view_closed(self):
        """
        Any attempt to access the ``register`` view when registration
        is closed fails and redirects.

        """
        old_allowed = getattr(settings, 'REGISTRATION_OPEN', True)
        settings.REGISTRATION_OPEN = False

        closed_redirect = 'http://testserver%s' % reverse('registration_disallowed')

        response = self.client.get(reverse('registration_register'))
        self.assertRedirects(response, closed_redirect)

        # Even if valid data is posted, it still shouldn't work.
        response = self.client.post(reverse('registration_register'),
                                    data={'username': 'alice',
                                          'email': 'alice@example.com',
                                          'password1': 'swordfish',
                                          'password2': 'swordfish'})
        self.assertRedirects(response, closed_redirect)
        self.assertEqual(RegistrationProfile.objects.count(), 0)

        settings.REGISTRATION_OPEN = old_allowed

    def test_registration_template_name(self):
        """
        Passing ``template_name`` to the ``register`` view will result
        in that template being used.

        """
        response = self.client.get(reverse('registration_test_register_template_name'))
        self.assertTemplateUsed(response,
                                'registration/test_template_name.html')

    def test_registration_extra_context(self):
        """
        Passing ``extra_context`` to the ``register`` view will
        correctly populate the context.

        """
        response = self.client.get(reverse('registration_test_register_extra_context'))
        self.assertEqual(response.context['foo'], 'bar')
        # Callables in extra_context are called to obtain the value.
        self.assertEqual(response.context['callable'], 'called')

    def test_registration_disallowed_url(self):
        """
        Passing ``disallowed_url`` to the ``register`` view will
        result in a redirect to that URL when registration is closed.

        """
        old_allowed = getattr(settings, 'REGISTRATION_OPEN', True)
        settings.REGISTRATION_OPEN = False

        closed_redirect = 'http://testserver%s' % reverse('registration_test_custom_disallowed')

        response = self.client.get(reverse('registration_test_register_disallowed_url'))
        self.assertRedirects(response, closed_redirect)

        settings.REGISTRATION_OPEN = old_allowed

    def test_registration_success_url(self):
        """
        Passing ``success_url`` to the ``register`` view will result
        in a redirect to that URL when registration is successful.
        
        """
        success_redirect = 'http://testserver%s' % reverse('registration_test_custom_success_url')
        response = self.client.post(reverse('registration_test_register_success_url'),
                                    data={'username': 'alice',
                                          'email': 'alice@example.com',
                                          'password1': 'swordfish',
                                          'password2': 'swordfish'})
        self.assertRedirects(response, success_redirect)

    def test_valid_activation(self):
        """
        Test that the ``activate`` view properly handles a valid
        activation (in this case, based on the default backend's
        activation window).

        """
        success_redirect = 'http://testserver%s' % reverse('registration_activation_complete')
        
        # First, register an account.
        self.client.post(reverse('registration_register'),
                         data={'username': 'alice',
                               'email': 'alice@example.com',
                               'password1': 'swordfish',
                               'password2': 'swordfish'})
        profile = RegistrationProfile.objects.get(user__username='alice')
        response = self.client.get(reverse('registration_activate',
                                           kwargs={'activation_key': profile.activation_key}))
        self.assertRedirects(response, success_redirect)
        self.failUnless(User.objects.get(username='alice').is_active)

    def test_invalid_activation(self):
        """
        Test that the ``activate`` view properly handles an invalid
        activation (in this case, based on the default backend's
        activation window).

        """
        # Register an account and reset its date_joined to be outside
        # the activation window.
        self.client.post(reverse('registration_register'),
                         data={'username': 'bob',
                               'email': 'bob@example.com',
                               'password1': 'secret',
                               'password2': 'secret'})
        expired_user = User.objects.get(username='bob')
        expired_user.date_joined = expired_user.date_joined - datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS)
        expired_user.save()

        expired_profile = RegistrationProfile.objects.get(user=expired_user)
        response = self.client.get(reverse('registration_activate',
                                           kwargs={'activation_key': expired_profile.activation_key}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['activation_key'],
                         expired_profile.activation_key)
        self.failIf(User.objects.get(username='bob').is_active)

    def test_activation_success_url(self):
        """
        Passing ``success_url`` to the ``activate`` view and
        successfully activating will result in that URL being used for
        the redirect.
        
        """
        success_redirect = 'http://testserver%s' % reverse('registration_test_custom_success_url')
        self.client.post(reverse('registration_register'),
                         data={'username': 'alice',
                               'email': 'alice@example.com',
                               'password1': 'swordfish',
                               'password2': 'swordfish'})
        profile = RegistrationProfile.objects.get(user__username='alice')
        response = self.client.get(reverse('registration_test_activate_success_url',
                                           kwargs={'activation_key': profile.activation_key}))
        self.assertRedirects(response, success_redirect)
        
    def test_activation_template_name(self):
        """
        Passing ``template_name`` to the ``activate`` view will result
        in that template being used.

        """
        response = self.client.get(reverse('registration_test_activate_template_name',
                                   kwargs={'activation_key': 'foo'}))
        self.assertTemplateUsed(response, 'registration/test_template_name.html')

    def test_activation_extra_context(self):
        """
        Passing ``extra_context`` to the ``activate`` view will
        correctly populate the context.

        """
        response = self.client.get(reverse('registration_test_activate_extra_context',
                                           kwargs={'activation_key': 'foo'}))
        self.assertEqual(response.context['foo'], 'bar')
        # Callables in extra_context are called to obtain the value.
        self.assertEqual(response.context['callable'], 'called')

########NEW FILE########
__FILENAME__ = urls
"""
Backwards-compatible URLconf for existing django-registration
installs; this allows the standard ``include('registration.urls')`` to
continue working, but that usage is deprecated and will be removed for
django-registration 1.0. For new installs, use
``include('registration.backends.default.urls')``.

"""

import warnings

warnings.warn("include('registration.urls') is deprecated; use include('registration.backends.default.urls') instead.",
              PendingDeprecationWarning)

from registration.backends.default.urls import *

########NEW FILE########
__FILENAME__ = views
"""
Views which allow users to create and activate accounts.

"""


from django.shortcuts import redirect
from django.shortcuts import render_to_response
from django.template import RequestContext

from registration.backends import get_backend


def activate(request, backend,
             template_name='registration/activate.html',
             success_url=None, extra_context=None, **kwargs):
    """
    Activate a user's account.

    The actual activation of the account will be delegated to the
    backend specified by the ``backend`` keyword argument (see below);
    the backend's ``activate()`` method will be called, passing any
    keyword arguments captured from the URL, and will be assumed to
    return a ``User`` if activation was successful, or a value which
    evaluates to ``False`` in boolean context if not.

    Upon successful activation, the backend's
    ``post_activation_redirect()`` method will be called, passing the
    ``HttpRequest`` and the activated ``User`` to determine the URL to
    redirect the user to. To override this, pass the argument
    ``success_url`` (see below).

    On unsuccessful activation, will render the template
    ``registration/activate.html`` to display an error message; to
    override thise, pass the argument ``template_name`` (see below).

    **Arguments**

    ``backend``
        The dotted Python import path to the backend class to
        use. Required.

    ``extra_context``
        A dictionary of variables to add to the template context. Any
        callable object in this dictionary will be called to produce
        the end result which appears in the context. Optional.

    ``success_url``
        The name of a URL pattern to redirect to on successful
        acivation. This is optional; if not specified, this will be
        obtained by calling the backend's
        ``post_activation_redirect()`` method.
    
    ``template_name``
        A custom template to use. This is optional; if not specified,
        this will default to ``registration/activate.html``.

    ``\*\*kwargs``
        Any keyword arguments captured from the URL, such as an
        activation key, which will be passed to the backend's
        ``activate()`` method.
    
    **Context:**
    
    The context will be populated from the keyword arguments captured
    in the URL, and any extra variables supplied in the
    ``extra_context`` argument (see above).
    
    **Template:**
    
    registration/activate.html or ``template_name`` keyword argument.
    
    """
    backend = get_backend(backend)
    account = backend.activate(request, **kwargs)

    if account:
        if success_url is None:
            to, args, kwargs = backend.post_activation_redirect(request, account)
            return redirect(to, *args, **kwargs)
        else:
            return redirect(success_url)

    if extra_context is None:
        extra_context = {}
    context = RequestContext(request)
    for key, value in extra_context.items():
        context[key] = callable(value) and value() or value

    return render_to_response(template_name,
                              kwargs,
                              context_instance=context)


def register(request, backend, success_url=None, form_class=None,
             disallowed_url='registration_disallowed',
             template_name='registration/registration_form.html',
             extra_context=None):
    """
    Allow a new user to register an account.

    The actual registration of the account will be delegated to the
    backend specified by the ``backend`` keyword argument (see below);
    it will be used as follows:

    1. The backend's ``registration_allowed()`` method will be called,
       passing the ``HttpRequest``, to determine whether registration
       of an account is to be allowed; if not, a redirect is issued to
       the view corresponding to the named URL pattern
       ``registration_disallowed``. To override this, see the list of
       optional arguments for this view (below).

    2. The form to use for account registration will be obtained by
       calling the backend's ``get_form_class()`` method, passing the
       ``HttpRequest``. To override this, see the list of optional
       arguments for this view (below).

    3. If valid, the form's ``cleaned_data`` will be passed (as
       keyword arguments, and along with the ``HttpRequest``) to the
       backend's ``register()`` method, which should return the new
       ``User`` object.

    4. Upon successful registration, the backend's
       ``post_registration_redirect()`` method will be called, passing
       the ``HttpRequest`` and the new ``User``, to determine the URL
       to redirect the user to. To override this, see the list of
       optional arguments for this view (below).
    
    **Required arguments**
    
    None.
    
    **Optional arguments**

    ``backend``
        The dotted Python import path to the backend class to use.

    ``disallowed_url``
        URL to redirect to if registration is not permitted for the
        current ``HttpRequest``. Must be a value which can legally be
        passed to ``django.shortcuts.redirect``. If not supplied, this
        will be whatever URL corresponds to the named URL pattern
        ``registration_disallowed``.
    
    ``form_class``
        The form class to use for registration. If not supplied, this
        will be retrieved from the registration backend.
    
    ``extra_context``
        A dictionary of variables to add to the template context. Any
        callable object in this dictionary will be called to produce
        the end result which appears in the context.

    ``success_url``
        URL to redirect to after successful registration. Must be a
        value which can legally be passed to
        ``django.shortcuts.redirect``. If not supplied, this will be
        retrieved from the registration backend.
    
    ``template_name``
        A custom template to use. If not supplied, this will default
        to ``registration/registration_form.html``.
    
    **Context:**
    
    ``form``
        The registration form.
    
    Any extra variables supplied in the ``extra_context`` argument
    (see above).
    
    **Template:**
    
    registration/registration_form.html or ``template_name`` keyword
    argument.
    
    """
    backend = get_backend(backend)
    if not backend.registration_allowed(request):
        return redirect(disallowed_url)
    if form_class is None:
        form_class = backend.get_form_class(request)

    if request.method == 'POST':
        form = form_class(data=request.POST, files=request.FILES)
        if form.is_valid():
            new_user = backend.register(request, **form.cleaned_data)
            if success_url is None:
                to, args, kwargs = backend.post_registration_redirect(request, new_user)
                return redirect(to, *args, **kwargs)
            else:
                return redirect(success_url)
    else:
        form = form_class()
    
    if extra_context is None:
        extra_context = {}
    context = RequestContext(request)
    for key, value in extra_context.items():
        context[key] = callable(value) and value() or value

    return render_to_response(template_name,
                              { 'form': form },
                              context_instance=context)

########NEW FILE########
__FILENAME__ = settings
# Django settings for example_project project.
import os,sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Justin Quick', 'justquick@gmail.com'),
)


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'dev.db',                      # Or path to database file if using sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/New_York'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = 'media'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'wzf0h@r2u%m^_zgj^39-y(kd%+n+j0r7=du(q0^s@q10t%^2!p'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

ROOT_URLCONF = 'example_project.urls'

TEMPLATE_DIRS = (
    'templates',
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admindocs',
    'django.contrib.comments',
    'django.contrib.sites',
    'django.contrib.messages',
    'registration',
    'testapp',
    'south',
    'actstream',
    'debug_toolbar',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    # for django 1.2 or 1.3
    'django.core.context_processors.auth',
    # for django 1.4 comment above line and uncomment below
    #'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'settings.users',
)

def users(request):
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.auth.models import User
    return {'users': User.objects.all(), 'user_ctype': ContentType.objects.get_for_model(User)}

def user_override(user):
    from django.contrib.contenttypes.models import ContentType
    from django.core.urlresolvers import reverse
    return reverse('actstream_actor',None,(ContentType.objects.get_for_model(user).pk,user.pk))

ABSOLUTE_URL_OVERRIDES = {
    'auth.user': user_override
}

ACCOUNT_ACTIVATION_DAYS = 7

ACTSTREAM_SETTINGS = {
    'MODELS': ('auth.user', 'auth.group', 'sites.site', 'comments.comment'),
    'MANAGER': 'testapp.streams.MyActionManager',
    'FETCH_RELATIONS': True,
    'USE_PREFETCH': True,
    'USE_JSONFIELD': True,
    'GFK_FETCH_DEPTH': 0,
}


DEBUG_TOOLBAR_PANELS = (
    'debug_toolbar.panels.template.TemplateDebugPanel',
)

INTERNAL_IPS = ('127.0.0.1',)

DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
}

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from models import Player

admin.site.register(Player)
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.comments.signals import comment_was_posted

from actstream import action

def comment_action(sender, comment=None, target=None, **kwargs):
    if comment.user:
        action.send(comment.user, verb=u'commented', action_object=comment, 
            target=comment.content_object)
comment_was_posted.connect(comment_action)

class Player(models.Model):
    state = models.IntegerField(default=0)
    
    def __unicode__(self):
        return '#%d' % self.pk
########NEW FILE########
__FILENAME__ = streams
from datetime import datetime

from actstream.managers import ActionManager, stream


class MyActionManager(ActionManager):

    @stream
    def testfoo(self, obj, time=None):
        if time is None:
            time = datetime.now()
        return obj.actor_actions.filter(timestamp__lte = time)

    @stream
    def testbar(self, verb):
        return self.filter(verb=verb)

########NEW FILE########
__FILENAME__ = tests
from datetime import datetime

from django.test import TestCase
from django.contrib.auth.models import User

from actstream.models import Action
from actstream.signals import action


class TestAppTests(TestCase):

    def setUp(self):
        self.user = User.objects.create(username='test')
        action.send(self.user, verb='was created')

    def test_accessor(self):
        self.assertEqual(len(Action.objects.testfoo(self.user)), 1)
        self.assertEqual(len(Action.objects.testfoo(self.user, datetime(1970, 1, 1))), 0)

    def test_mystream(self):
        self.assertEqual(len(self.user.actor_actions.testbar('was created')), 1)
        self.assertEqual(len(self.user.action_object_actions.testbar('was created')), 0)

    def test_jsonfield(self):
        action.send(self.user, verb='said', text='foobar', tags=['sayings'],
                    more_data={'pk': self.user.pk})
        newaction = Action.objects.filter(verb='said')[0]
        self.assertEqual(newaction.data['text'], 'foobar')
        self.assertEqual(newaction.data['tags'], ['sayings'])
        self.assertEqual(newaction.data['more_data'], {'pk': self.user.pk})

########NEW FILE########
__FILENAME__ = urls
import os
from django.conf.urls.defaults import *
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/', include(admin.site.urls)),
    (r'^comments/', include('django.contrib.comments.urls')),
    (r'^accounts/', include('registration.backends.default.urls')),
    (r'^media/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': os.path.join(os.path.dirname(__file__), 'media')}),
    (r'auth/', include('django.contrib.auth.urls')),
    (r'', include('actstream.urls')),
)


########NEW FILE########
