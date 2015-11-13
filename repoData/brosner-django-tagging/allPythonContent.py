__FILENAME__ = admin
from django.contrib import admin
from tagging.models import Tag, TaggedItem
from tagging.forms import TagAdminForm

class TagAdmin(admin.ModelAdmin):
    form = TagAdminForm

admin.site.register(TaggedItem)
admin.site.register(Tag, TagAdmin)





########NEW FILE########
__FILENAME__ = fields
"""
A custom Model Field for tagging.
"""
from django.db.models import signals
from django.db.models.fields import CharField
from django.utils.translation import ugettext_lazy as _

from tagging import settings
from tagging.models import Tag
from tagging.utils import edit_string_for_tags

class TagField(CharField):
    """
    A "special" character field that actually works as a relationship to tags
    "under the hood". This exposes a space-separated string of tags, but does
    the splitting/reordering/etc. under the hood.
    """
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 255)
        kwargs['blank'] = kwargs.get('blank', True)
        kwargs['default'] = kwargs.get('default', '')
        super(TagField, self).__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name):
        super(TagField, self).contribute_to_class(cls, name)

        # Make this object the descriptor for field access.
        setattr(cls, self.name, self)

        # Save tags back to the database post-save
        signals.post_save.connect(self._save, cls, True)

        # Update tags from Tag objects post-init
        signals.post_init.connect(self._update, cls, True)

    def __get__(self, instance, owner=None):
        """
        Tag getter. Returns an instance's tags if accessed on an instance, and
        all of a model's tags if called on a class. That is, this model::

           class Link(models.Model):
               ...
               tags = TagField()

        Lets you do both of these::

           >>> l = Link.objects.get(...)
           >>> l.tags
           'tag1 tag2 tag3'

           >>> Link.tags
           'tag1 tag2 tag3 tag4'

        """
        # Handle access on the model (i.e. Link.tags)
        if instance is None:
            return edit_string_for_tags(Tag.objects.usage_for_model(owner))

        return self._get_instance_tag_cache(instance)

    def __set__(self, instance, value):
        """
        Set an object's tags.
        """
        if instance is None:
            raise AttributeError(_('%s can only be set on instances.') % self.name)
        if settings.FORCE_LOWERCASE_TAGS and value is not None:
            value = value.lower()
        self._set_instance_tag_cache(instance, value)

    def _save(self, **kwargs): #signal, sender, instance):
        """
        Save tags back to the database
        """
        tags = self._get_instance_tag_cache(kwargs['instance'])
        Tag.objects.update_tags(kwargs['instance'], tags)

    def _update(self, **kwargs): #signal, sender, instance):
        """
        Update tag cache from TaggedItem objects.
        """
        instance = kwargs['instance']
        self._update_instance_tag_cache(instance)

    def __delete__(self, instance):
        """
        Clear all of an object's tags.
        """
        self._set_instance_tag_cache(instance, '')

    def _get_instance_tag_cache(self, instance):
        """
        Helper: get an instance's tag cache.
        """
        return getattr(instance, '_%s_cache' % self.attname, None)

    def _set_instance_tag_cache(self, instance, tags):
        """
        Helper: set an instance's tag cache.
        """
        setattr(instance, '_%s_cache' % self.attname, tags)

    def _update_instance_tag_cache(self, instance):
        """
        Helper: update an instance's tag cache from actual Tags.
        """
        # for an unsaved object, leave the default value alone
        if instance.pk is not None:
            tags = edit_string_for_tags(Tag.objects.get_for_object(instance))
            self._set_instance_tag_cache(instance, tags)

    def get_internal_type(self):
        return 'CharField'

    def formfield(self, **kwargs):
        from tagging import forms
        defaults = {'form_class': forms.TagField}
        defaults.update(kwargs)
        return super(TagField, self).formfield(**defaults)

########NEW FILE########
__FILENAME__ = forms
"""
Tagging components for Django's form library.
"""
from django import forms
from django.utils.translation import ugettext as _

from tagging import settings
from tagging.models import Tag
from tagging.utils import parse_tag_input

class TagAdminForm(forms.ModelForm):
    class Meta:
        model = Tag

    def clean_name(self):
        value = self.cleaned_data['name']
        tag_names = parse_tag_input(value)
        if len(tag_names) > 1:
            raise forms.ValidationError(_('Multiple tags were given.'))
        elif len(tag_names[0]) > settings.MAX_TAG_LENGTH:
            raise forms.ValidationError(
                _('A tag may be no more than %s characters long.') %
                    settings.MAX_TAG_LENGTH)
        return value

class TagField(forms.CharField):
    """
    A ``CharField`` which validates that its input is a valid list of
    tag names.
    """
    def clean(self, value):
        value = super(TagField, self).clean(value)
        if value == u'':
            return value
        for tag_name in parse_tag_input(value):
            if len(tag_name) > settings.MAX_TAG_LENGTH:
                raise forms.ValidationError(
                    _('Each tag may be no more than %s characters long.') %
                        settings.MAX_TAG_LENGTH)
        return value

########NEW FILE########
__FILENAME__ = generic
from django.contrib.contenttypes.models import ContentType

def fetch_content_objects(tagged_items, select_related_for=None):
    """
    Retrieves ``ContentType`` and content objects for the given list of
    ``TaggedItems``, grouping the retrieval of content objects by model
    type to reduce the number of queries executed.

    This results in ``number_of_content_types + 1`` queries rather than
    the ``number_of_tagged_items * 2`` queries you'd get by iterating
    over the list and accessing each item's ``object`` attribute.

    A ``select_related_for`` argument can be used to specify a list of
    of model names (corresponding to the ``model`` field of a
    ``ContentType``) for which ``select_related`` should be used when
    retrieving model instances.
    """
    if select_related_for is None: select_related_for = []

    # Group content object pks by their content type pks
    objects = {}
    for item in tagged_items:
        objects.setdefault(item.content_type_id, []).append(item.object_id)

    # Retrieve content types and content objects in bulk
    content_types = ContentType._default_manager.in_bulk(objects.keys())
    for content_type_pk, object_pks in objects.iteritems():
        model = content_types[content_type_pk].model_class()
        if content_types[content_type_pk].model in select_related_for:
            objects[content_type_pk] = model._default_manager.select_related().in_bulk(object_pks)
        else:
            objects[content_type_pk] = model._default_manager.in_bulk(object_pks)

    # Set content types and content objects in the appropriate cache
    # attributes, so accessing the 'content_type' and 'object'
    # attributes on each tagged item won't result in further database
    # hits.
    for item in tagged_items:
        item._object_cache = objects[item.content_type_id][item.object_id]
        item._content_type_cache = content_types[item.content_type_id]

########NEW FILE########
__FILENAME__ = managers
"""
Custom managers for Django models registered with the tagging
application.
"""
from django.contrib.contenttypes.models import ContentType
from django.db import models

from tagging.models import Tag, TaggedItem

class ModelTagManager(models.Manager):
    """
    A manager for retrieving tags for a particular model.
    """
    def get_query_set(self):
        ctype = ContentType.objects.get_for_model(self.model)
        return Tag.objects.filter(
            items__content_type__pk=ctype.pk).distinct()

    def cloud(self, *args, **kwargs):
        return Tag.objects.cloud_for_model(self.model, *args, **kwargs)

    def related(self, tags, *args, **kwargs):
        return Tag.objects.related_for_model(tags, self.model, *args, **kwargs)

    def usage(self, *args, **kwargs):
        return Tag.objects.usage_for_model(self.model, *args, **kwargs)

class ModelTaggedItemManager(models.Manager):
    """
    A manager for retrieving model instances based on their tags.
    """
    def related_to(self, obj, queryset=None, num=None):
        if queryset is None:
            return TaggedItem.objects.get_related(obj, self.model, num=num)
        else:
            return TaggedItem.objects.get_related(obj, queryset, num=num)

    def with_all(self, tags, queryset=None):
        if queryset is None:
            return TaggedItem.objects.get_by_model(self.model, tags)
        else:
            return TaggedItem.objects.get_by_model(queryset, tags)

    def with_any(self, tags, queryset=None):
        if queryset is None:
            return TaggedItem.objects.get_union_by_model(self.model, tags)
        else:
            return TaggedItem.objects.get_union_by_model(queryset, tags)

class TagDescriptor(object):
    """
    A descriptor which provides access to a ``ModelTagManager`` for
    model classes and simple retrieval, updating and deletion of tags
    for model instances.
    """
    def __get__(self, instance, owner):
        if not instance:
            tag_manager = ModelTagManager()
            tag_manager.model = owner
            return tag_manager
        else:
            return Tag.objects.get_for_object(instance)

    def __set__(self, instance, value):
        Tag.objects.update_tags(instance, value)

    def __delete__(self, instance):
        Tag.objects.update_tags(instance, None)

########NEW FILE########
__FILENAME__ = models
"""
Models and managers for generic tagging.
"""
# Python 2.3 compatibility
try:
    set
except NameError:
    from sets import Set as set

from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import connection, models
from django.db.models.query import QuerySet
from django.utils.translation import ugettext_lazy as _

from tagging import settings
from tagging.utils import calculate_cloud, get_tag_list, get_queryset_and_model, parse_tag_input
from tagging.utils import LOGARITHMIC

qn = connection.ops.quote_name

############
# Managers #
############

class TagManager(models.Manager):
    def update_tags(self, obj, tag_names):
        """
        Update tags associated with an object.
        """
        ctype = ContentType.objects.get_for_model(obj)
        current_tags = list(self.filter(items__content_type__pk=ctype.pk,
                                        items__object_id=obj.pk))
        updated_tag_names = parse_tag_input(tag_names)
        if settings.FORCE_LOWERCASE_TAGS:
            updated_tag_names = [t.lower() for t in updated_tag_names]

        # Remove tags which no longer apply
        tags_for_removal = [tag for tag in current_tags \
                            if tag.name not in updated_tag_names]
        if len(tags_for_removal):
            TaggedItem._default_manager.filter(content_type__pk=ctype.pk,
                                               object_id=obj.pk,
                                               tag__in=tags_for_removal).delete()
        # Add new tags
        current_tag_names = [tag.name for tag in current_tags]
        for tag_name in updated_tag_names:
            if tag_name not in current_tag_names:
                tag, created = self.get_or_create(name=tag_name)
                TaggedItem._default_manager.create(tag=tag, object=obj)

    def add_tag(self, obj, tag_name):
        """
        Associates the given object with a tag.
        """
        tag_names = parse_tag_input(tag_name)
        if not len(tag_names):
            raise AttributeError(_('No tags were given: "%s".') % tag_name)
        if len(tag_names) > 1:
            raise AttributeError(_('Multiple tags were given: "%s".') % tag_name)
        tag_name = tag_names[0]
        if settings.FORCE_LOWERCASE_TAGS:
            tag_name = tag_name.lower()
        tag, created = self.get_or_create(name=tag_name)
        ctype = ContentType.objects.get_for_model(obj)
        TaggedItem._default_manager.get_or_create(
            tag=tag, content_type=ctype, object_id=obj.pk)

    def get_for_object(self, obj):
        """
        Create a queryset matching all tags associated with the given
        object.
        """
        ctype = ContentType.objects.get_for_model(obj)
        return self.filter(items__content_type__pk=ctype.pk,
                           items__object_id=obj.pk)

    def _get_usage(self, model, counts=False, min_count=None, extra_joins=None, extra_criteria=None, params=None):
        """
        Perform the custom SQL query for ``usage_for_model`` and
        ``usage_for_queryset``.
        """
        if min_count is not None: counts = True

        model_table = qn(model._meta.db_table)
        model_pk = '%s.%s' % (model_table, qn(model._meta.pk.column))
        query = """
        SELECT DISTINCT %(tag)s.id, %(tag)s.name%(count_sql)s
        FROM
            %(tag)s
            INNER JOIN %(tagged_item)s
                ON %(tag)s.id = %(tagged_item)s.tag_id
            INNER JOIN %(model)s
                ON %(tagged_item)s.object_id = %(model_pk)s
            %%s
        WHERE %(tagged_item)s.content_type_id = %(content_type_id)s
            %%s
        GROUP BY %(tag)s.id, %(tag)s.name
        %%s
        ORDER BY %(tag)s.name ASC""" % {
            'tag': qn(self.model._meta.db_table),
            'count_sql': counts and (', COUNT(%s)' % model_pk) or '',
            'tagged_item': qn(TaggedItem._meta.db_table),
            'model': model_table,
            'model_pk': model_pk,
            'content_type_id': ContentType.objects.get_for_model(model).pk,
        }

        min_count_sql = ''
        if min_count is not None:
            min_count_sql = 'HAVING COUNT(%s) >= %%s' % model_pk
            params.append(min_count)

        cursor = connection.cursor()
        cursor.execute(query % (extra_joins, extra_criteria, min_count_sql), params)
        tags = []
        for row in cursor.fetchall():
            t = self.model(*row[:2])
            if counts:
                t.count = row[2]
            tags.append(t)
        return tags

    def usage_for_model(self, model, counts=False, min_count=None, filters=None):
        """
        Obtain a list of tags associated with instances of the given
        Model class.

        If ``counts`` is True, a ``count`` attribute will be added to
        each tag, indicating how many times it has been used against
        the Model class in question.

        If ``min_count`` is given, only tags which have a ``count``
        greater than or equal to ``min_count`` will be returned.
        Passing a value for ``min_count`` implies ``counts=True``.

        To limit the tags (and counts, if specified) returned to those
        used by a subset of the Model's instances, pass a dictionary
        of field lookups to be applied to the given Model as the
        ``filters`` argument.
        """
        if filters is None: filters = {}

        queryset = model._default_manager.filter()
        for f in filters.items():
            queryset.query.add_filter(f)
        usage = self.usage_for_queryset(queryset, counts, min_count)

        return usage

    def usage_for_queryset(self, queryset, counts=False, min_count=None):
        """
        Obtain a list of tags associated with instances of a model
        contained in the given queryset.

        If ``counts`` is True, a ``count`` attribute will be added to
        each tag, indicating how many times it has been used against
        the Model class in question.

        If ``min_count`` is given, only tags which have a ``count``
        greater than or equal to ``min_count`` will be returned.
        Passing a value for ``min_count`` implies ``counts=True``.
        """

        if getattr(queryset.query, 'get_compiler', None):
            # Django 1.2+
            compiler = queryset.query.get_compiler(using='default')
            extra_joins = ' '.join(compiler.get_from_clause()[0][1:])
            where, params = queryset.query.where.as_sql(
                compiler.quote_name_unless_alias, compiler.connection
            )
        else:
            # Django pre-1.2
            extra_joins = ' '.join(queryset.query.get_from_clause()[0][1:])
            where, params = queryset.query.where.as_sql()

        if where:
            extra_criteria = 'AND %s' % where
        else:
            extra_criteria = ''
        return self._get_usage(queryset.model, counts, min_count, extra_joins, extra_criteria, params)

    def related_for_model(self, tags, model, counts=False, min_count=None):
        """
        Obtain a list of tags related to a given list of tags - that
        is, other tags used by items which have all the given tags.

        If ``counts`` is True, a ``count`` attribute will be added to
        each tag, indicating the number of items which have it in
        addition to the given list of tags.

        If ``min_count`` is given, only tags which have a ``count``
        greater than or equal to ``min_count`` will be returned.
        Passing a value for ``min_count`` implies ``counts=True``.
        """
        if min_count is not None: counts = True
        tags = get_tag_list(tags)
        tag_count = len(tags)
        tagged_item_table = qn(TaggedItem._meta.db_table)
        query = """
        SELECT %(tag)s.id, %(tag)s.name%(count_sql)s
        FROM %(tagged_item)s INNER JOIN %(tag)s ON %(tagged_item)s.tag_id = %(tag)s.id
        WHERE %(tagged_item)s.content_type_id = %(content_type_id)s
          AND %(tagged_item)s.object_id IN
          (
              SELECT %(tagged_item)s.object_id
              FROM %(tagged_item)s, %(tag)s
              WHERE %(tagged_item)s.content_type_id = %(content_type_id)s
                AND %(tag)s.id = %(tagged_item)s.tag_id
                AND %(tag)s.id IN (%(tag_id_placeholders)s)
              GROUP BY %(tagged_item)s.object_id
              HAVING COUNT(%(tagged_item)s.object_id) = %(tag_count)s
          )
          AND %(tag)s.id NOT IN (%(tag_id_placeholders)s)
        GROUP BY %(tag)s.id, %(tag)s.name
        %(min_count_sql)s
        ORDER BY %(tag)s.name ASC""" % {
            'tag': qn(self.model._meta.db_table),
            'count_sql': counts and ', COUNT(%s.object_id)' % tagged_item_table or '',
            'tagged_item': tagged_item_table,
            'content_type_id': ContentType.objects.get_for_model(model).pk,
            'tag_id_placeholders': ','.join(['%s'] * tag_count),
            'tag_count': tag_count,
            'min_count_sql': min_count is not None and ('HAVING COUNT(%s.object_id) >= %%s' % tagged_item_table) or '',
        }

        params = [tag.pk for tag in tags] * 2
        if min_count is not None:
            params.append(min_count)

        cursor = connection.cursor()
        cursor.execute(query, params)
        related = []
        for row in cursor.fetchall():
            tag = self.model(*row[:2])
            if counts is True:
                tag.count = row[2]
            related.append(tag)
        return related

    def cloud_for_model(self, model, steps=4, distribution=LOGARITHMIC,
                        filters=None, min_count=None):
        """
        Obtain a list of tags associated with instances of the given
        Model, giving each tag a ``count`` attribute indicating how
        many times it has been used and a ``font_size`` attribute for
        use in displaying a tag cloud.

        ``steps`` defines the range of font sizes - ``font_size`` will
        be an integer between 1 and ``steps`` (inclusive).

        ``distribution`` defines the type of font size distribution
        algorithm which will be used - logarithmic or linear. It must
        be either ``tagging.utils.LOGARITHMIC`` or
        ``tagging.utils.LINEAR``.

        To limit the tags displayed in the cloud to those associated
        with a subset of the Model's instances, pass a dictionary of
        field lookups to be applied to the given Model as the
        ``filters`` argument.

        To limit the tags displayed in the cloud to those with a
        ``count`` greater than or equal to ``min_count``, pass a value
        for the ``min_count`` argument.
        """
        tags = list(self.usage_for_model(model, counts=True, filters=filters,
                                         min_count=min_count))
        return calculate_cloud(tags, steps, distribution)

class TaggedItemManager(models.Manager):
    """
    FIXME There's currently no way to get the ``GROUP BY`` and ``HAVING``
          SQL clauses required by many of this manager's methods into
          Django's ORM.

          For now, we manually execute a query to retrieve the PKs of
          objects we're interested in, then use the ORM's ``__in``
          lookup to return a ``QuerySet``.

          Now that the queryset-refactor branch is in the trunk, this can be
          tidied up significantly.
    """
    def get_by_model(self, queryset_or_model, tags):
        """
        Create a ``QuerySet`` containing instances of the specified
        model associated with a given tag or list of tags.
        """
        tags = get_tag_list(tags)
        tag_count = len(tags)
        if tag_count == 0:
            # No existing tags were given
            queryset, model = get_queryset_and_model(queryset_or_model)
            return model._default_manager.none()
        elif tag_count == 1:
            # Optimisation for single tag - fall through to the simpler
            # query below.
            tag = tags[0]
        else:
            return self.get_intersection_by_model(queryset_or_model, tags)

        queryset, model = get_queryset_and_model(queryset_or_model)
        content_type = ContentType.objects.get_for_model(model)
        opts = self.model._meta
        tagged_item_table = qn(opts.db_table)
        return queryset.extra(
            tables=[opts.db_table],
            where=[
                '%s.content_type_id = %%s' % tagged_item_table,
                '%s.tag_id = %%s' % tagged_item_table,
                '%s.%s = %s.object_id' % (qn(model._meta.db_table),
                                          qn(model._meta.pk.column),
                                          tagged_item_table)
            ],
            params=[content_type.pk, tag.pk],
        )

    def get_intersection_by_model(self, queryset_or_model, tags):
        """
        Create a ``QuerySet`` containing instances of the specified
        model associated with *all* of the given list of tags.
        """
        tags = get_tag_list(tags)
        tag_count = len(tags)
        queryset, model = get_queryset_and_model(queryset_or_model)

        if not tag_count:
            return model._default_manager.none()

        model_table = qn(model._meta.db_table)
        # This query selects the ids of all objects which have all the
        # given tags.
        query = """
        SELECT %(model_pk)s
        FROM %(model)s, %(tagged_item)s
        WHERE %(tagged_item)s.content_type_id = %(content_type_id)s
          AND %(tagged_item)s.tag_id IN (%(tag_id_placeholders)s)
          AND %(model_pk)s = %(tagged_item)s.object_id
        GROUP BY %(model_pk)s
        HAVING COUNT(%(model_pk)s) = %(tag_count)s""" % {
            'model_pk': '%s.%s' % (model_table, qn(model._meta.pk.column)),
            'model': model_table,
            'tagged_item': qn(self.model._meta.db_table),
            'content_type_id': ContentType.objects.get_for_model(model).pk,
            'tag_id_placeholders': ','.join(['%s'] * tag_count),
            'tag_count': tag_count,
        }

        cursor = connection.cursor()
        cursor.execute(query, [tag.pk for tag in tags])
        object_ids = [row[0] for row in cursor.fetchall()]
        if len(object_ids) > 0:
            return queryset.filter(pk__in=object_ids)
        else:
            return model._default_manager.none()

    def get_union_by_model(self, queryset_or_model, tags):
        """
        Create a ``QuerySet`` containing instances of the specified
        model associated with *any* of the given list of tags.
        """
        tags = get_tag_list(tags)
        tag_count = len(tags)
        queryset, model = get_queryset_and_model(queryset_or_model)

        if not tag_count:
            return model._default_manager.none()

        model_table = qn(model._meta.db_table)
        # This query selects the ids of all objects which have any of
        # the given tags.
        query = """
        SELECT %(model_pk)s
        FROM %(model)s, %(tagged_item)s
        WHERE %(tagged_item)s.content_type_id = %(content_type_id)s
          AND %(tagged_item)s.tag_id IN (%(tag_id_placeholders)s)
          AND %(model_pk)s = %(tagged_item)s.object_id
        GROUP BY %(model_pk)s""" % {
            'model_pk': '%s.%s' % (model_table, qn(model._meta.pk.column)),
            'model': model_table,
            'tagged_item': qn(self.model._meta.db_table),
            'content_type_id': ContentType.objects.get_for_model(model).pk,
            'tag_id_placeholders': ','.join(['%s'] * tag_count),
        }

        cursor = connection.cursor()
        cursor.execute(query, [tag.pk for tag in tags])
        object_ids = [row[0] for row in cursor.fetchall()]
        if len(object_ids) > 0:
            return queryset.filter(pk__in=object_ids)
        else:
            return model._default_manager.none()

    def get_related(self, obj, queryset_or_model, num=None):
        """
        Retrieve a list of instances of the specified model which share
        tags with the model instance ``obj``, ordered by the number of
        shared tags in descending order.

        If ``num`` is given, a maximum of ``num`` instances will be
        returned.
        """
        queryset, model = get_queryset_and_model(queryset_or_model)
        model_table = qn(model._meta.db_table)
        content_type = ContentType.objects.get_for_model(obj)
        related_content_type = ContentType.objects.get_for_model(model)
        query = """
        SELECT %(model_pk)s, COUNT(related_tagged_item.object_id) AS %(count)s
        FROM %(model)s, %(tagged_item)s, %(tag)s, %(tagged_item)s related_tagged_item
        WHERE %(tagged_item)s.object_id = %%s
          AND %(tagged_item)s.content_type_id = %(content_type_id)s
          AND %(tag)s.id = %(tagged_item)s.tag_id
          AND related_tagged_item.content_type_id = %(related_content_type_id)s
          AND related_tagged_item.tag_id = %(tagged_item)s.tag_id
          AND %(model_pk)s = related_tagged_item.object_id"""
        if content_type.pk == related_content_type.pk:
            # Exclude the given instance itself if determining related
            # instances for the same model.
            query += """
          AND related_tagged_item.object_id != %(tagged_item)s.object_id"""
        query += """
        GROUP BY %(model_pk)s
        ORDER BY %(count)s DESC
        %(limit_offset)s"""
        query = query % {
            'model_pk': '%s.%s' % (model_table, qn(model._meta.pk.column)),
            'count': qn('count'),
            'model': model_table,
            'tagged_item': qn(self.model._meta.db_table),
            'tag': qn(self.model._meta.get_field('tag').rel.to._meta.db_table),
            'content_type_id': content_type.pk,
            'related_content_type_id': related_content_type.pk,
            # Hardcoding this for now just to get tests working again - this
            # should now be handled by the query object.
            'limit_offset': num is not None and 'LIMIT %s' or '',
        }

        cursor = connection.cursor()
        params = [obj.pk]
        if num is not None:
            params.append(num)
        cursor.execute(query, params)
        object_ids = [row[0] for row in cursor.fetchall()]
        if len(object_ids) > 0:
            # Use in_bulk here instead of an id__in lookup, because id__in would
            # clobber the ordering.
            object_dict = queryset.in_bulk(object_ids)
            return [object_dict[object_id] for object_id in object_ids \
                    if object_id in object_dict]
        else:
            return []

##########
# Models #
##########

class Tag(models.Model):
    """
    A tag.
    """
    name = models.CharField(_('name'), max_length=50, unique=True, db_index=True)

    objects = TagManager()

    class Meta:
        ordering = ('name',)
        verbose_name = _('tag')
        verbose_name_plural = _('tags')

    def __unicode__(self):
        return self.name

class TaggedItem(models.Model):
    """
    Holds the relationship between a tag and the item being tagged.
    """
    tag          = models.ForeignKey(Tag, verbose_name=_('tag'), related_name='items')
    content_type = models.ForeignKey(ContentType, verbose_name=_('content type'))
    object_id    = models.PositiveIntegerField(_('object id'), db_index=True)
    object       = generic.GenericForeignKey('content_type', 'object_id')

    objects = TaggedItemManager()

    class Meta:
        # Enforce unique tag association per object
        unique_together = (('tag', 'content_type', 'object_id'),)
        verbose_name = _('tagged item')
        verbose_name_plural = _('tagged items')

    def __unicode__(self):
        return u'%s [%s]' % (self.object, self.tag)

########NEW FILE########
__FILENAME__ = settings
"""
Convenience module for access of custom tagging application settings,
which enforces default settings when the main settings module does not
contain the appropriate settings.
"""
from django.conf import settings

# The maximum length of a tag's name.
MAX_TAG_LENGTH = getattr(settings, 'MAX_TAG_LENGTH', 50)

# Whether to force all tags to lowercase before they are saved to the
# database.
FORCE_LOWERCASE_TAGS = getattr(settings, 'FORCE_LOWERCASE_TAGS', False)

########NEW FILE########
__FILENAME__ = tagging_tags
from django.db.models import get_model
from django.template import Library, Node, TemplateSyntaxError, Variable, resolve_variable
from django.utils.translation import ugettext as _

from tagging.models import Tag, TaggedItem
from tagging.utils import LINEAR, LOGARITHMIC

register = Library()

class TagsForModelNode(Node):
    def __init__(self, model, context_var, counts):
        self.model = model
        self.context_var = context_var
        self.counts = counts

    def render(self, context):
        model = get_model(*self.model.split('.'))
        if model is None:
            raise TemplateSyntaxError(_('tags_for_model tag was given an invalid model: %s') % self.model)
        context[self.context_var] = Tag.objects.usage_for_model(model, counts=self.counts)
        return ''

class TagCloudForModelNode(Node):
    def __init__(self, model, context_var, **kwargs):
        self.model = model
        self.context_var = context_var
        self.kwargs = kwargs

    def render(self, context):
        model = get_model(*self.model.split('.'))
        if model is None:
            raise TemplateSyntaxError(_('tag_cloud_for_model tag was given an invalid model: %s') % self.model)
        context[self.context_var] = \
            Tag.objects.cloud_for_model(model, **self.kwargs)
        return ''

class TagsForObjectNode(Node):
    def __init__(self, obj, context_var):
        self.obj = Variable(obj)
        self.context_var = context_var

    def render(self, context):
        context[self.context_var] = \
            Tag.objects.get_for_object(self.obj.resolve(context))
        return ''

class TaggedObjectsNode(Node):
    def __init__(self, tag, model, context_var):
        self.tag = Variable(tag)
        self.context_var = context_var
        self.model = model

    def render(self, context):
        model = get_model(*self.model.split('.'))
        if model is None:
            raise TemplateSyntaxError(_('tagged_objects tag was given an invalid model: %s') % self.model)
        context[self.context_var] = \
            TaggedItem.objects.get_by_model(model, self.tag.resolve(context))
        return ''

def do_tags_for_model(parser, token):
    """
    Retrieves a list of ``Tag`` objects associated with a given model
    and stores them in a context variable.

    Usage::

       {% tags_for_model [model] as [varname] %}

    The model is specified in ``[appname].[modelname]`` format.

    Extended usage::

       {% tags_for_model [model] as [varname] with counts %}

    If specified - by providing extra ``with counts`` arguments - adds
    a ``count`` attribute to each tag containing the number of
    instances of the given model which have been tagged with it.

    Examples::

       {% tags_for_model products.Widget as widget_tags %}
       {% tags_for_model products.Widget as widget_tags with counts %}

    """
    bits = token.contents.split()
    len_bits = len(bits)
    if len_bits not in (4, 6):
        raise TemplateSyntaxError(_('%s tag requires either three or five arguments') % bits[0])
    if bits[2] != 'as':
        raise TemplateSyntaxError(_("second argument to %s tag must be 'as'") % bits[0])
    if len_bits == 6:
        if bits[4] != 'with':
            raise TemplateSyntaxError(_("if given, fourth argument to %s tag must be 'with'") % bits[0])
        if bits[5] != 'counts':
            raise TemplateSyntaxError(_("if given, fifth argument to %s tag must be 'counts'") % bits[0])
    if len_bits == 4:
        return TagsForModelNode(bits[1], bits[3], counts=False)
    else:
        return TagsForModelNode(bits[1], bits[3], counts=True)

def do_tag_cloud_for_model(parser, token):
    """
    Retrieves a list of ``Tag`` objects for a given model, with tag
    cloud attributes set, and stores them in a context variable.

    Usage::

       {% tag_cloud_for_model [model] as [varname] %}

    The model is specified in ``[appname].[modelname]`` format.

    Extended usage::

       {% tag_cloud_for_model [model] as [varname] with [options] %}

    Extra options can be provided after an optional ``with`` argument,
    with each option being specified in ``[name]=[value]`` format. Valid
    extra options are:

       ``steps``
          Integer. Defines the range of font sizes.

       ``min_count``
          Integer. Defines the minimum number of times a tag must have
          been used to appear in the cloud.

       ``distribution``
          One of ``linear`` or ``log``. Defines the font-size
          distribution algorithm to use when generating the tag cloud.

    Examples::

       {% tag_cloud_for_model products.Widget as widget_tags %}
       {% tag_cloud_for_model products.Widget as widget_tags with steps=9 min_count=3 distribution=log %}

    """
    bits = token.contents.split()
    len_bits = len(bits)
    if len_bits != 4 and len_bits not in range(6, 9):
        raise TemplateSyntaxError(_('%s tag requires either three or between five and seven arguments') % bits[0])
    if bits[2] != 'as':
        raise TemplateSyntaxError(_("second argument to %s tag must be 'as'") % bits[0])
    kwargs = {}
    if len_bits > 5:
        if bits[4] != 'with':
            raise TemplateSyntaxError(_("if given, fourth argument to %s tag must be 'with'") % bits[0])
        for i in range(5, len_bits):
            try:
                name, value = bits[i].split('=')
                if name == 'steps' or name == 'min_count':
                    try:
                        kwargs[str(name)] = int(value)
                    except ValueError:
                        raise TemplateSyntaxError(_("%(tag)s tag's '%(option)s' option was not a valid integer: '%(value)s'") % {
                            'tag': bits[0],
                            'option': name,
                            'value': value,
                        })
                elif name == 'distribution':
                    if value in ['linear', 'log']:
                        kwargs[str(name)] = {'linear': LINEAR, 'log': LOGARITHMIC}[value]
                    else:
                        raise TemplateSyntaxError(_("%(tag)s tag's '%(option)s' option was not a valid choice: '%(value)s'") % {
                            'tag': bits[0],
                            'option': name,
                            'value': value,
                        })
                else:
                    raise TemplateSyntaxError(_("%(tag)s tag was given an invalid option: '%(option)s'") % {
                        'tag': bits[0],
                        'option': name,
                    })
            except ValueError:
                raise TemplateSyntaxError(_("%(tag)s tag was given a badly formatted option: '%(option)s'") % {
                    'tag': bits[0],
                    'option': bits[i],
                })
    return TagCloudForModelNode(bits[1], bits[3], **kwargs)

def do_tags_for_object(parser, token):
    """
    Retrieves a list of ``Tag`` objects associated with an object and
    stores them in a context variable.

    Usage::

       {% tags_for_object [object] as [varname] %}

    Example::

        {% tags_for_object foo_object as tag_list %}
    """
    bits = token.contents.split()
    if len(bits) != 4:
        raise TemplateSyntaxError(_('%s tag requires exactly three arguments') % bits[0])
    if bits[2] != 'as':
        raise TemplateSyntaxError(_("second argument to %s tag must be 'as'") % bits[0])
    return TagsForObjectNode(bits[1], bits[3])

def do_tagged_objects(parser, token):
    """
    Retrieves a list of instances of a given model which are tagged with
    a given ``Tag`` and stores them in a context variable.

    Usage::

       {% tagged_objects [tag] in [model] as [varname] %}

    The model is specified in ``[appname].[modelname]`` format.

    The tag must be an instance of a ``Tag``, not the name of a tag.

    Example::

        {% tagged_objects comedy_tag in tv.Show as comedies %}

    """
    bits = token.contents.split()
    if len(bits) != 6:
        raise TemplateSyntaxError(_('%s tag requires exactly five arguments') % bits[0])
    if bits[2] != 'in':
        raise TemplateSyntaxError(_("second argument to %s tag must be 'in'") % bits[0])
    if bits[4] != 'as':
        raise TemplateSyntaxError(_("fourth argument to %s tag must be 'as'") % bits[0])
    return TaggedObjectsNode(bits[1], bits[3], bits[5])

register.tag('tags_for_model', do_tags_for_model)
register.tag('tag_cloud_for_model', do_tag_cloud_for_model)
register.tag('tags_for_object', do_tags_for_object)
register.tag('tagged_objects', do_tagged_objects)

########NEW FILE########
__FILENAME__ = models
from django.db import models

from tagging.fields import TagField

class Perch(models.Model):
    size = models.IntegerField()
    smelly = models.BooleanField(default=True)

class Parrot(models.Model):
    state = models.CharField(max_length=50)
    perch = models.ForeignKey(Perch, null=True)

    def __unicode__(self):
        return self.state

    class Meta:
        ordering = ['state']

class Link(models.Model):
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']

class Article(models.Model):
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']

class FormTest(models.Model):
    tags = TagField('Test', help_text='Test')

class FormTestNull(models.Model):
    tags = TagField(null=True)


########NEW FILE########
__FILENAME__ = settings
import os
DIRNAME = os.path.dirname(__file__)

DEFAULT_CHARSET = 'utf-8'

test_engine = os.environ.get("TAGGING_TEST_ENGINE", "sqlite3")

DATABASE_ENGINE = test_engine
DATABASE_NAME = os.environ.get("TAGGING_DATABASE_NAME", "tagging_test")
DATABASE_USER = os.environ.get("TAGGING_DATABASE_USER", "")
DATABASE_PASSWORD = os.environ.get("TAGGING_DATABASE_PASSWORD", "")
DATABASE_HOST = os.environ.get("TAGGING_DATABASE_HOST", "localhost")

if test_engine == "sqlite":
    DATABASE_NAME = os.path.join(DIRNAME, 'tagging_test.db')
    DATABASE_HOST = ""
elif test_engine == "mysql":
    DATABASE_PORT = os.environ.get("TAGGING_DATABASE_PORT", 3306)
elif test_engine == "postgresql_psycopg2":
    DATABASE_PORT = os.environ.get("TAGGING_DATABASE_PORT", 5432)


INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'tagging',
    'tagging.tests',
)

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-

import os
from django import forms
from django.db.models import Q
from django.test import TestCase
from tagging.forms import TagField
from tagging import settings
from tagging.models import Tag, TaggedItem
from tagging.tests.models import Article, Link, Perch, Parrot, FormTest, FormTestNull
from tagging.utils import calculate_cloud, edit_string_for_tags, get_tag_list, get_tag, parse_tag_input
from tagging.utils import LINEAR

#############
# Utilities #
#############

class TestParseTagInput(TestCase):
    def test_with_simple_space_delimited_tags(self):
        """ Test with simple space-delimited tags. """
        
        self.assertEquals(parse_tag_input('one'), [u'one'])
        self.assertEquals(parse_tag_input('one two'), [u'one', u'two'])
        self.assertEquals(parse_tag_input('one two three'), [u'one', u'three', u'two'])
        self.assertEquals(parse_tag_input('one one two two'), [u'one', u'two'])
    
    def test_with_comma_delimited_multiple_words(self):
        """ Test with comma-delimited multiple words.
            An unquoted comma in the input will trigger this. """
            
        self.assertEquals(parse_tag_input(',one'), [u'one'])
        self.assertEquals(parse_tag_input(',one two'), [u'one two'])
        self.assertEquals(parse_tag_input(',one two three'), [u'one two three'])
        self.assertEquals(parse_tag_input('a-one, a-two and a-three'),
            [u'a-one', u'a-two and a-three'])
    
    def test_with_double_quoted_multiple_words(self):
        """ Test with double-quoted multiple words.
            A completed quote will trigger this.  Unclosed quotes are ignored. """
            
        self.assertEquals(parse_tag_input('"one'), [u'one'])
        self.assertEquals(parse_tag_input('"one two'), [u'one', u'two'])
        self.assertEquals(parse_tag_input('"one two three'), [u'one', u'three', u'two'])
        self.assertEquals(parse_tag_input('"one two"'), [u'one two'])
        self.assertEquals(parse_tag_input('a-one "a-two and a-three"'),
            [u'a-one', u'a-two and a-three'])
    
    def test_with_no_loose_commas(self):
        """ Test with no loose commas -- split on spaces. """
        self.assertEquals(parse_tag_input('one two "thr,ee"'), [u'one', u'thr,ee', u'two'])
        
    def test_with_loose_commas(self):
        """ Loose commas - split on commas """
        self.assertEquals(parse_tag_input('"one", two three'), [u'one', u'two three'])
        
    def test_tags_with_double_quotes_can_contain_commas(self):
        """ Double quotes can contain commas """
        self.assertEquals(parse_tag_input('a-one "a-two, and a-three"'),
            [u'a-one', u'a-two, and a-three'])
        self.assertEquals(parse_tag_input('"two", one, one, two, "one"'),
            [u'one', u'two'])
    
    def test_with_naughty_input(self):
        """ Test with naughty input. """
        
        # Bad users! Naughty users!
        self.assertEquals(parse_tag_input(None), [])
        self.assertEquals(parse_tag_input(''), [])
        self.assertEquals(parse_tag_input('"'), [])
        self.assertEquals(parse_tag_input('""'), [])
        self.assertEquals(parse_tag_input('"' * 7), [])
        self.assertEquals(parse_tag_input(',,,,,,'), [])
        self.assertEquals(parse_tag_input('",",",",",",","'), [u','])
        self.assertEquals(parse_tag_input('a-one "a-two" and "a-three'),
            [u'a-one', u'a-three', u'a-two', u'and'])
        
class TestNormalisedTagListInput(TestCase):
    def setUp(self):
        self.cheese = Tag.objects.create(name='cheese')
        self.toast = Tag.objects.create(name='toast')
        
    def test_single_tag_object_as_input(self):
        self.assertEquals(get_tag_list(self.cheese), [self.cheese])
    
    def test_space_delimeted_string_as_input(self):
        ret = get_tag_list('cheese toast')
        self.assertEquals(len(ret), 2)
        self.failUnless(self.cheese in ret)
        self.failUnless(self.toast in ret)
        
    def test_comma_delimeted_string_as_input(self):
        ret = get_tag_list('cheese,toast')
        self.assertEquals(len(ret), 2)
        self.failUnless(self.cheese in ret)
        self.failUnless(self.toast in ret)
    
    def test_with_empty_list(self):
        self.assertEquals(get_tag_list([]), [])
    
    def test_list_of_two_strings(self):
        ret = get_tag_list(['cheese', 'toast'])
        self.assertEquals(len(ret), 2)
        self.failUnless(self.cheese in ret)
        self.failUnless(self.toast in ret)
    
    def test_list_of_tag_primary_keys(self):
        ret = get_tag_list([self.cheese.id, self.toast.id])
        self.assertEquals(len(ret), 2)
        self.failUnless(self.cheese in ret)
        self.failUnless(self.toast in ret)
    
    def test_list_of_strings_with_strange_nontag_string(self):
        ret = get_tag_list(['cheese', 'toast', 'ŠĐĆŽćžšđ'])
        self.assertEquals(len(ret), 2)
        self.failUnless(self.cheese in ret)
        self.failUnless(self.toast in ret)
    
    def test_list_of_tag_instances(self):
        ret = get_tag_list([self.cheese, self.toast])
        self.assertEquals(len(ret), 2)
        self.failUnless(self.cheese in ret)
        self.failUnless(self.toast in ret)
    
    def test_tuple_of_instances(self):
        ret = get_tag_list((self.cheese, self.toast))
        self.assertEquals(len(ret), 2)
        self.failUnless(self.cheese in ret)
        self.failUnless(self.toast in ret)
    
    def test_with_tag_filter(self):
        ret = get_tag_list(Tag.objects.filter(name__in=['cheese', 'toast']))
        self.assertEquals(len(ret), 2)
        self.failUnless(self.cheese in ret)
        self.failUnless(self.toast in ret)
        
    def test_with_invalid_input_mix_of_string_and_instance(self):
        try:
            get_tag_list(['cheese', self.toast])
        except ValueError, ve:
            self.assertEquals(str(ve),
                'If a list or tuple of tags is provided, they must all be tag names, Tag objects or Tag ids.')
        except Exception, e:
            raise self.failureException('the wrong type of exception was raised: type [%s] value [%]' %\
                (str(type(e)), str(e)))
        else:
            raise self.failureException('a ValueError exception was supposed to be raised!')
    
    def test_with_invalid_input(self):
        try:
            get_tag_list(29)
        except ValueError, ve:
            self.assertEquals(str(ve), 'The tag input given was invalid.')
        except Exception, e:
            raise self.failureException('the wrong type of exception was raised: type [%s] value [%s]' %\
                (str(type(e)), str(e)))
        else:
            raise self.failureException('a ValueError exception was supposed to be raised!')

    def test_with_tag_instance(self):
        self.assertEquals(get_tag(self.cheese), self.cheese)
    
    def test_with_string(self):
        self.assertEquals(get_tag('cheese'), self.cheese)
    
    def test_with_primary_key(self):
        self.assertEquals(get_tag(self.cheese.id), self.cheese)
    
    def test_nonexistent_tag(self):
        self.assertEquals(get_tag('mouse'), None)

class TestCalculateCloud(TestCase):
    def setUp(self):
        self.tags = []
        for line in open(os.path.join(os.path.dirname(__file__), 'tags.txt')).readlines():
            name, count = line.rstrip().split()
            tag = Tag(name=name)
            tag.count = int(count)
            self.tags.append(tag)
    
    def test_default_distribution(self):
        sizes = {}
        for tag in calculate_cloud(self.tags, steps=5):
            sizes[tag.font_size] = sizes.get(tag.font_size, 0) + 1
        
        # This isn't a pre-calculated test, just making sure it's consistent
        self.assertEquals(sizes[1], 48)
        self.assertEquals(sizes[2], 30)
        self.assertEquals(sizes[3], 19)
        self.assertEquals(sizes[4], 15)
        self.assertEquals(sizes[5], 10)
    
    def test_linear_distribution(self):
        sizes = {}
        for tag in calculate_cloud(self.tags, steps=5, distribution=LINEAR):
            sizes[tag.font_size] = sizes.get(tag.font_size, 0) + 1
        
        # This isn't a pre-calculated test, just making sure it's consistent
        self.assertEquals(sizes[1], 97)
        self.assertEquals(sizes[2], 12)
        self.assertEquals(sizes[3], 7)
        self.assertEquals(sizes[4], 2)
        self.assertEquals(sizes[5], 4)
    
    def test_invalid_distribution(self):
        try:
            calculate_cloud(self.tags, steps=5, distribution='cheese')
        except ValueError, ve:
            self.assertEquals(str(ve), 'Invalid distribution algorithm specified: cheese.')
        except Exception, e:
            raise self.failureException('the wrong type of exception was raised: type [%s] value [%s]' %\
                (str(type(e)), str(e)))
        else:
            raise self.failureException('a ValueError exception was supposed to be raised!')
        
###########
# Tagging #
###########

class TestBasicTagging(TestCase):
    def setUp(self):
        self.dead_parrot = Parrot.objects.create(state='dead')
    
    def test_update_tags(self):
        Tag.objects.update_tags(self.dead_parrot, 'foo,bar,"ter"')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 3)
        self.failUnless(get_tag('foo') in tags)
        self.failUnless(get_tag('bar') in tags)
        self.failUnless(get_tag('ter') in tags)
        
        Tag.objects.update_tags(self.dead_parrot, '"foo" bar "baz"')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 3)
        self.failUnless(get_tag('bar') in tags)
        self.failUnless(get_tag('baz') in tags)
        self.failUnless(get_tag('foo') in tags)
    
    def test_add_tag(self):
        # start off in a known, mildly interesting state
        Tag.objects.update_tags(self.dead_parrot, 'foo bar baz')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 3)
        self.failUnless(get_tag('bar') in tags)
        self.failUnless(get_tag('baz') in tags)
        self.failUnless(get_tag('foo') in tags)
        
        # try to add a tag that already exists
        Tag.objects.add_tag(self.dead_parrot, 'foo')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 3)
        self.failUnless(get_tag('bar') in tags)
        self.failUnless(get_tag('baz') in tags)
        self.failUnless(get_tag('foo') in tags)
        
        # now add a tag that doesn't already exist
        Tag.objects.add_tag(self.dead_parrot, 'zip')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 4)
        self.failUnless(get_tag('zip') in tags)
        self.failUnless(get_tag('bar') in tags)
        self.failUnless(get_tag('baz') in tags)
        self.failUnless(get_tag('foo') in tags)
    
    def test_add_tag_invalid_input_no_tags_specified(self):
        # start off in a known, mildly interesting state
        Tag.objects.update_tags(self.dead_parrot, 'foo bar baz')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 3)
        self.failUnless(get_tag('bar') in tags)
        self.failUnless(get_tag('baz') in tags)
        self.failUnless(get_tag('foo') in tags)
        
        try:
            Tag.objects.add_tag(self.dead_parrot, '    ')
        except AttributeError, ae:
            self.assertEquals(str(ae), 'No tags were given: "    ".')
        except Exception, e:
            raise self.failureException('the wrong type of exception was raised: type [%s] value [%s]' %\
                (str(type(e)), str(e)))
        else:
            raise self.failureException('an AttributeError exception was supposed to be raised!')
        
    def test_add_tag_invalid_input_multiple_tags_specified(self):
        # start off in a known, mildly interesting state
        Tag.objects.update_tags(self.dead_parrot, 'foo bar baz')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 3)
        self.failUnless(get_tag('bar') in tags)
        self.failUnless(get_tag('baz') in tags)
        self.failUnless(get_tag('foo') in tags)
        
        try:
            Tag.objects.add_tag(self.dead_parrot, 'one two')
        except AttributeError, ae:
            self.assertEquals(str(ae), 'Multiple tags were given: "one two".')
        except Exception, e:
            raise self.failureException('the wrong type of exception was raised: type [%s] value [%s]' %\
                (str(type(e)), str(e)))
        else:
            raise self.failureException('an AttributeError exception was supposed to be raised!')
    
    def test_update_tags_exotic_characters(self):
        # start off in a known, mildly interesting state
        Tag.objects.update_tags(self.dead_parrot, 'foo bar baz')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 3)
        self.failUnless(get_tag('bar') in tags)
        self.failUnless(get_tag('baz') in tags)
        self.failUnless(get_tag('foo') in tags)
        
        Tag.objects.update_tags(self.dead_parrot, u'ŠĐĆŽćžšđ')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 1)
        self.assertEquals(tags[0].name, u'ŠĐĆŽćžšđ')
        
        Tag.objects.update_tags(self.dead_parrot, u'你好')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 1)
        self.assertEquals(tags[0].name, u'你好')
    
    def test_update_tags_with_none(self):
        # start off in a known, mildly interesting state
        Tag.objects.update_tags(self.dead_parrot, 'foo bar baz')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 3)
        self.failUnless(get_tag('bar') in tags)
        self.failUnless(get_tag('baz') in tags)
        self.failUnless(get_tag('foo') in tags)
        
        Tag.objects.update_tags(self.dead_parrot, None)
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 0)

class TestModelTagField(TestCase):
    """ Test the 'tags' field on models. """
    
    def test_create_with_tags_specified(self):
        f1 = FormTest.objects.create(tags=u'test3 test2 test1')
        tags = Tag.objects.get_for_object(f1)
        test1_tag = get_tag('test1')
        test2_tag = get_tag('test2')
        test3_tag = get_tag('test3')
        self.failUnless(None not in (test1_tag, test2_tag, test3_tag))
        self.assertEquals(len(tags), 3)
        self.failUnless(test1_tag in tags)
        self.failUnless(test2_tag in tags)
        self.failUnless(test3_tag in tags)
    
    def test_update_via_tags_field(self):
        f1 = FormTest.objects.create(tags=u'test3 test2 test1')
        tags = Tag.objects.get_for_object(f1)
        test1_tag = get_tag('test1')
        test2_tag = get_tag('test2')
        test3_tag = get_tag('test3')
        self.failUnless(None not in (test1_tag, test2_tag, test3_tag))
        self.assertEquals(len(tags), 3)
        self.failUnless(test1_tag in tags)
        self.failUnless(test2_tag in tags)
        self.failUnless(test3_tag in tags)
        
        f1.tags = u'test4'
        f1.save()
        tags = Tag.objects.get_for_object(f1)
        test4_tag = get_tag('test4')
        self.assertEquals(len(tags), 1)
        self.assertEquals(tags[0], test4_tag)
        
        f1.tags = ''
        f1.save()
        tags = Tag.objects.get_for_object(f1)
        self.assertEquals(len(tags), 0)

    def test_update_via_tags(self):
        f1 = FormTest.objects.create(tags=u'one two three')
        Tag.objects.get(name='three').delete()
        t2 = Tag.objects.get(name='two')
        t2.name = 'new'
        t2.save()
        f1again = FormTest.objects.get(pk=f1.pk)
        self.failIf('three' in f1again.tags)
        self.failIf('two' in f1again.tags)
        self.failUnless('new' in f1again.tags)

    def test_creation_without_specifying_tags(self):
        f1 = FormTest()
        self.assertEquals(f1.tags, '')

    def test_creation_with_nullable_tags_field(self):
        f1 = FormTestNull()
        self.assertEquals(f1.tags, '')
        
class TestSettings(TestCase):
    def setUp(self):
        self.original_force_lower_case_tags = settings.FORCE_LOWERCASE_TAGS
        self.dead_parrot = Parrot.objects.create(state='dead')
    
    def tearDown(self):
        settings.FORCE_LOWERCASE_TAGS = self.original_force_lower_case_tags
    
    def test_force_lowercase_tags(self):
        """ Test forcing tags to lowercase. """
        
        settings.FORCE_LOWERCASE_TAGS = True
        
        Tag.objects.update_tags(self.dead_parrot, 'foO bAr Ter')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 3)
        foo_tag = get_tag('foo')
        bar_tag = get_tag('bar')
        ter_tag = get_tag('ter')
        self.failUnless(foo_tag in tags)
        self.failUnless(bar_tag in tags)
        self.failUnless(ter_tag in tags)
        
        Tag.objects.update_tags(self.dead_parrot, 'foO bAr baZ')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        baz_tag = get_tag('baz')
        self.assertEquals(len(tags), 3)
        self.failUnless(bar_tag in tags)
        self.failUnless(baz_tag in tags)
        self.failUnless(foo_tag in tags)
        
        Tag.objects.add_tag(self.dead_parrot, 'FOO')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 3)
        self.failUnless(bar_tag in tags)
        self.failUnless(baz_tag in tags)
        self.failUnless(foo_tag in tags)
        
        Tag.objects.add_tag(self.dead_parrot, 'Zip')
        tags = Tag.objects.get_for_object(self.dead_parrot)
        self.assertEquals(len(tags), 4)
        zip_tag = get_tag('zip')
        self.failUnless(bar_tag in tags)
        self.failUnless(baz_tag in tags)
        self.failUnless(foo_tag in tags)
        self.failUnless(zip_tag in tags)
        
        f1 = FormTest.objects.create()
        f1.tags = u'TEST5'
        f1.save()
        tags = Tag.objects.get_for_object(f1)
        test5_tag = get_tag('test5')
        self.assertEquals(len(tags), 1)
        self.failUnless(test5_tag in tags)
        self.assertEquals(f1.tags, u'test5')

class TestTagUsageForModelBaseCase(TestCase):
    def test_tag_usage_for_model_empty(self):
        self.assertEquals(Tag.objects.usage_for_model(Parrot), [])

class TestTagUsageForModel(TestCase):
    def setUp(self):
        parrot_details = (
            ('pining for the fjords', 9, True,  'foo bar'),
            ('passed on',             6, False, 'bar baz ter'),
            ('no more',               4, True,  'foo ter'),
            ('late',                  2, False, 'bar ter'),
        )
        
        for state, perch_size, perch_smelly, tags in parrot_details:
            perch = Perch.objects.create(size=perch_size, smelly=perch_smelly)
            parrot = Parrot.objects.create(state=state, perch=perch)
            Tag.objects.update_tags(parrot, tags)
    
    def test_tag_usage_for_model(self):
        tag_usage = Tag.objects.usage_for_model(Parrot, counts=True)
        relevant_attribute_list = [(tag.name, tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 4)
        self.failUnless((u'bar', 3) in relevant_attribute_list)
        self.failUnless((u'baz', 1) in relevant_attribute_list)
        self.failUnless((u'foo', 2) in relevant_attribute_list)
        self.failUnless((u'ter', 3) in relevant_attribute_list)
    
    def test_tag_usage_for_model_with_min_count(self):
        tag_usage = Tag.objects.usage_for_model(Parrot, min_count = 2)
        relevant_attribute_list = [(tag.name, tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 3)
        self.failUnless((u'bar', 3) in relevant_attribute_list)
        self.failUnless((u'foo', 2) in relevant_attribute_list)
        self.failUnless((u'ter', 3) in relevant_attribute_list)
    
    def test_tag_usage_with_filter_on_model_objects(self):
        tag_usage = Tag.objects.usage_for_model(Parrot, counts=True, filters=dict(state='no more'))
        relevant_attribute_list = [(tag.name, tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 2)
        self.failUnless((u'foo', 1) in relevant_attribute_list)
        self.failUnless((u'ter', 1) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_model(Parrot, counts=True, filters=dict(state__startswith='p'))
        relevant_attribute_list = [(tag.name, tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 4)
        self.failUnless((u'bar', 2) in relevant_attribute_list)
        self.failUnless((u'baz', 1) in relevant_attribute_list)
        self.failUnless((u'foo', 1) in relevant_attribute_list)
        self.failUnless((u'ter', 1) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_model(Parrot, counts=True, filters=dict(perch__size__gt=4))
        relevant_attribute_list = [(tag.name, tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 4)
        self.failUnless((u'bar', 2) in relevant_attribute_list)
        self.failUnless((u'baz', 1) in relevant_attribute_list)
        self.failUnless((u'foo', 1) in relevant_attribute_list)
        self.failUnless((u'ter', 1) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_model(Parrot, counts=True, filters=dict(perch__smelly=True))
        relevant_attribute_list = [(tag.name, tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 3)
        self.failUnless((u'bar', 1) in relevant_attribute_list)
        self.failUnless((u'foo', 2) in relevant_attribute_list)
        self.failUnless((u'ter', 1) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_model(Parrot, min_count=2, filters=dict(perch__smelly=True))
        relevant_attribute_list = [(tag.name, tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 1)
        self.failUnless((u'foo', 2) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_model(Parrot, filters=dict(perch__size__gt=4))
        relevant_attribute_list = [(tag.name, hasattr(tag, 'counts')) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 4)
        self.failUnless((u'bar', False) in relevant_attribute_list)
        self.failUnless((u'baz', False) in relevant_attribute_list)
        self.failUnless((u'foo', False) in relevant_attribute_list)
        self.failUnless((u'ter', False) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_model(Parrot, filters=dict(perch__size__gt=99))
        relevant_attribute_list = [(tag.name, hasattr(tag, 'counts')) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 0)

class TestTagsRelatedForModel(TestCase):
    def setUp(self):
        parrot_details = (
            ('pining for the fjords', 9, True,  'foo bar'),
            ('passed on',             6, False, 'bar baz ter'),
            ('no more',               4, True,  'foo ter'),
            ('late',                  2, False, 'bar ter'),
        )
        
        for state, perch_size, perch_smelly, tags in parrot_details:
            perch = Perch.objects.create(size=perch_size, smelly=perch_smelly)
            parrot = Parrot.objects.create(state=state, perch=perch)
            Tag.objects.update_tags(parrot, tags)
            
    def test_related_for_model_with_tag_query_sets_as_input(self):
        related_tags = Tag.objects.related_for_model(Tag.objects.filter(name__in=['bar']), Parrot, counts=True)
        relevant_attribute_list = [(tag.name, tag.count) for tag in related_tags]
        self.assertEquals(len(relevant_attribute_list), 3)
        self.failUnless((u'baz', 1) in relevant_attribute_list)
        self.failUnless((u'foo', 1) in relevant_attribute_list)
        self.failUnless((u'ter', 2) in relevant_attribute_list)
        
        related_tags = Tag.objects.related_for_model(Tag.objects.filter(name__in=['bar']), Parrot, min_count=2)
        relevant_attribute_list = [(tag.name, tag.count) for tag in related_tags]
        self.assertEquals(len(relevant_attribute_list), 1)
        self.failUnless((u'ter', 2) in relevant_attribute_list)
        
        related_tags = Tag.objects.related_for_model(Tag.objects.filter(name__in=['bar']), Parrot, counts=False)
        relevant_attribute_list = [tag.name for tag in related_tags]
        self.assertEquals(len(relevant_attribute_list), 3)
        self.failUnless(u'baz' in relevant_attribute_list)
        self.failUnless(u'foo' in relevant_attribute_list)
        self.failUnless(u'ter' in relevant_attribute_list)
        
        related_tags = Tag.objects.related_for_model(Tag.objects.filter(name__in=['bar', 'ter']), Parrot, counts=True)
        relevant_attribute_list = [(tag.name, tag.count) for tag in related_tags]
        self.assertEquals(len(relevant_attribute_list), 1)
        self.failUnless((u'baz', 1) in relevant_attribute_list)
        
        related_tags = Tag.objects.related_for_model(Tag.objects.filter(name__in=['bar', 'ter', 'baz']), Parrot, counts=True)
        relevant_attribute_list = [(tag.name, tag.count) for tag in related_tags]
        self.assertEquals(len(relevant_attribute_list), 0)
        
    def test_related_for_model_with_tag_strings_as_input(self):
        # Once again, with feeling (strings)
        related_tags = Tag.objects.related_for_model('bar', Parrot, counts=True)
        relevant_attribute_list = [(tag.name, tag.count) for tag in related_tags]
        self.assertEquals(len(relevant_attribute_list), 3)
        self.failUnless((u'baz', 1) in relevant_attribute_list)
        self.failUnless((u'foo', 1) in relevant_attribute_list)
        self.failUnless((u'ter', 2) in relevant_attribute_list)
        
        related_tags = Tag.objects.related_for_model('bar', Parrot, min_count=2)
        relevant_attribute_list = [(tag.name, tag.count) for tag in related_tags]
        self.assertEquals(len(relevant_attribute_list), 1)
        self.failUnless((u'ter', 2) in relevant_attribute_list)
        
        related_tags = Tag.objects.related_for_model('bar', Parrot, counts=False)
        relevant_attribute_list = [tag.name for tag in related_tags]
        self.assertEquals(len(relevant_attribute_list), 3)
        self.failUnless(u'baz' in relevant_attribute_list)
        self.failUnless(u'foo' in relevant_attribute_list)
        self.failUnless(u'ter' in relevant_attribute_list)
        
        related_tags = Tag.objects.related_for_model(['bar', 'ter'], Parrot, counts=True)
        relevant_attribute_list = [(tag.name, tag.count) for tag in related_tags]
        self.assertEquals(len(relevant_attribute_list), 1)
        self.failUnless((u'baz', 1) in relevant_attribute_list)
        
        related_tags = Tag.objects.related_for_model(['bar', 'ter', 'baz'], Parrot, counts=True)
        relevant_attribute_list = [(tag.name, tag.count) for tag in related_tags]
        self.assertEquals(len(relevant_attribute_list), 0)
        
class TestGetTaggedObjectsByModel(TestCase):
    def setUp(self):
        parrot_details = (
            ('pining for the fjords', 9, True,  'foo bar'),
            ('passed on',             6, False, 'bar baz ter'),
            ('no more',               4, True,  'foo ter'),
            ('late',                  2, False, 'bar ter'),
        )
        
        for state, perch_size, perch_smelly, tags in parrot_details:
            perch = Perch.objects.create(size=perch_size, smelly=perch_smelly)
            parrot = Parrot.objects.create(state=state, perch=perch)
            Tag.objects.update_tags(parrot, tags)
            
        self.foo = Tag.objects.get(name='foo')
        self.bar = Tag.objects.get(name='bar')
        self.baz = Tag.objects.get(name='baz')
        self.ter = Tag.objects.get(name='ter')
        
        self.pining_for_the_fjords_parrot = Parrot.objects.get(state='pining for the fjords')
        self.passed_on_parrot = Parrot.objects.get(state='passed on')
        self.no_more_parrot = Parrot.objects.get(state='no more')
        self.late_parrot = Parrot.objects.get(state='late')
        
    def test_get_by_model_simple(self):
        parrots = TaggedItem.objects.get_by_model(Parrot, self.foo)
        self.assertEquals(len(parrots), 2)
        self.failUnless(self.no_more_parrot in parrots)
        self.failUnless(self.pining_for_the_fjords_parrot in parrots)
        
        parrots = TaggedItem.objects.get_by_model(Parrot, self.bar)
        self.assertEquals(len(parrots), 3)
        self.failUnless(self.late_parrot in parrots)
        self.failUnless(self.passed_on_parrot in parrots)
        self.failUnless(self.pining_for_the_fjords_parrot in parrots)
    
    def test_get_by_model_intersection(self):
        parrots = TaggedItem.objects.get_by_model(Parrot, [self.foo, self.baz])
        self.assertEquals(len(parrots), 0)
        
        parrots = TaggedItem.objects.get_by_model(Parrot, [self.foo, self.bar])
        self.assertEquals(len(parrots), 1)
        self.failUnless(self.pining_for_the_fjords_parrot in parrots)
        
        parrots = TaggedItem.objects.get_by_model(Parrot, [self.bar, self.ter])
        self.assertEquals(len(parrots), 2)
        self.failUnless(self.late_parrot in parrots)
        self.failUnless(self.passed_on_parrot in parrots)
        
        # Issue 114 - Intersection with non-existant tags
        parrots = TaggedItem.objects.get_intersection_by_model(Parrot, [])
        self.assertEquals(len(parrots), 0)
    
    def test_get_by_model_with_tag_querysets_as_input(self):
        parrots = TaggedItem.objects.get_by_model(Parrot, Tag.objects.filter(name__in=['foo', 'baz']))
        self.assertEquals(len(parrots), 0)
        
        parrots = TaggedItem.objects.get_by_model(Parrot, Tag.objects.filter(name__in=['foo', 'bar']))
        self.assertEquals(len(parrots), 1)
        self.failUnless(self.pining_for_the_fjords_parrot in parrots)
        
        parrots = TaggedItem.objects.get_by_model(Parrot, Tag.objects.filter(name__in=['bar', 'ter']))
        self.assertEquals(len(parrots), 2)
        self.failUnless(self.late_parrot in parrots)
        self.failUnless(self.passed_on_parrot in parrots)
    
    def test_get_by_model_with_strings_as_input(self):
        parrots = TaggedItem.objects.get_by_model(Parrot, 'foo baz')
        self.assertEquals(len(parrots), 0)
        
        parrots = TaggedItem.objects.get_by_model(Parrot, 'foo bar')
        self.assertEquals(len(parrots), 1)
        self.failUnless(self.pining_for_the_fjords_parrot in parrots)
        
        parrots = TaggedItem.objects.get_by_model(Parrot, 'bar ter')
        self.assertEquals(len(parrots), 2)
        self.failUnless(self.late_parrot in parrots)
        self.failUnless(self.passed_on_parrot in parrots)
        
    def test_get_by_model_with_lists_of_strings_as_input(self):
        parrots = TaggedItem.objects.get_by_model(Parrot, ['foo', 'baz'])
        self.assertEquals(len(parrots), 0)
        
        parrots = TaggedItem.objects.get_by_model(Parrot, ['foo', 'bar'])
        self.assertEquals(len(parrots), 1)
        self.failUnless(self.pining_for_the_fjords_parrot in parrots)
        
        parrots = TaggedItem.objects.get_by_model(Parrot, ['bar', 'ter'])
        self.assertEquals(len(parrots), 2)
        self.failUnless(self.late_parrot in parrots)
        self.failUnless(self.passed_on_parrot in parrots)
    
    def test_get_by_nonexistent_tag(self):
        # Issue 50 - Get by non-existent tag
        parrots = TaggedItem.objects.get_by_model(Parrot, 'argatrons')
        self.assertEquals(len(parrots), 0)
    
    def test_get_union_by_model(self):
        parrots = TaggedItem.objects.get_union_by_model(Parrot, ['foo', 'ter'])
        self.assertEquals(len(parrots), 4)
        self.failUnless(self.late_parrot in parrots)
        self.failUnless(self.no_more_parrot in parrots)
        self.failUnless(self.passed_on_parrot in parrots)
        self.failUnless(self.pining_for_the_fjords_parrot in parrots)
        
        parrots = TaggedItem.objects.get_union_by_model(Parrot, ['bar', 'baz'])
        self.assertEquals(len(parrots), 3)
        self.failUnless(self.late_parrot in parrots)
        self.failUnless(self.passed_on_parrot in parrots)
        self.failUnless(self.pining_for_the_fjords_parrot in parrots)
        
        # Issue 114 - Union with non-existant tags
        parrots = TaggedItem.objects.get_union_by_model(Parrot, [])
        self.assertEquals(len(parrots), 0)

class TestGetRelatedTaggedItems(TestCase):
    def setUp(self):
        parrot_details = (
            ('pining for the fjords', 9, True,  'foo bar'),
            ('passed on',             6, False, 'bar baz ter'),
            ('no more',               4, True,  'foo ter'),
            ('late',                  2, False, 'bar ter'),
        )
        
        for state, perch_size, perch_smelly, tags in parrot_details:
            perch = Perch.objects.create(size=perch_size, smelly=perch_smelly)
            parrot = Parrot.objects.create(state=state, perch=perch)
            Tag.objects.update_tags(parrot, tags)
            
        self.l1 = Link.objects.create(name='link 1')
        Tag.objects.update_tags(self.l1, 'tag1 tag2 tag3 tag4 tag5')
        self.l2 = Link.objects.create(name='link 2')
        Tag.objects.update_tags(self.l2, 'tag1 tag2 tag3')
        self.l3 = Link.objects.create(name='link 3')
        Tag.objects.update_tags(self.l3, 'tag1')
        self.l4 = Link.objects.create(name='link 4')
        
        self.a1 = Article.objects.create(name='article 1')
        Tag.objects.update_tags(self.a1, 'tag1 tag2 tag3 tag4')
    
    def test_get_related_objects_of_same_model(self):
        related_objects = TaggedItem.objects.get_related(self.l1, Link)
        self.assertEquals(len(related_objects), 2)
        self.failUnless(self.l2 in related_objects)
        self.failUnless(self.l3 in related_objects)
        
        related_objects = TaggedItem.objects.get_related(self.l4, Link)
        self.assertEquals(len(related_objects), 0)
    
    def test_get_related_objects_of_same_model_limited_number_of_results(self):
        # This fails on Oracle because it has no support for a 'LIMIT' clause.
        # See http://asktom.oracle.com/pls/asktom/f?p=100:11:0::::P11_QUESTION_ID:127412348064
        
        # ask for no more than 1 result
        related_objects = TaggedItem.objects.get_related(self.l1, Link, num=1)
        self.assertEquals(len(related_objects), 1)
        self.failUnless(self.l2 in related_objects)
        
    def test_get_related_objects_of_same_model_limit_related_items(self):
        related_objects = TaggedItem.objects.get_related(self.l1, Link.objects.exclude(name='link 3'))
        self.assertEquals(len(related_objects), 1)
        self.failUnless(self.l2 in related_objects)
    
    def test_get_related_objects_of_different_model(self):
        related_objects = TaggedItem.objects.get_related(self.a1, Link)
        self.assertEquals(len(related_objects), 3)
        self.failUnless(self.l1 in related_objects)
        self.failUnless(self.l2 in related_objects)
        self.failUnless(self.l3 in related_objects)
            
        Tag.objects.update_tags(self.a1, 'tag6')
        related_objects = TaggedItem.objects.get_related(self.a1, Link)
        self.assertEquals(len(related_objects), 0)
        
class TestTagUsageForQuerySet(TestCase):
    def setUp(self):
        parrot_details = (
            ('pining for the fjords', 9, True,  'foo bar'),
            ('passed on',             6, False, 'bar baz ter'),
            ('no more',               4, True,  'foo ter'),
            ('late',                  2, False, 'bar ter'),
        )
        
        for state, perch_size, perch_smelly, tags in parrot_details:
            perch = Perch.objects.create(size=perch_size, smelly=perch_smelly)
            parrot = Parrot.objects.create(state=state, perch=perch)
            Tag.objects.update_tags(parrot, tags)
    
    def test_tag_usage_for_queryset(self):
        tag_usage = Tag.objects.usage_for_queryset(Parrot.objects.filter(state='no more'), counts=True)
        relevant_attribute_list = [(tag.name, tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 2)
        self.failUnless((u'foo', 1) in relevant_attribute_list)
        self.failUnless((u'ter', 1) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_queryset(Parrot.objects.filter(state__startswith='p'), counts=True)
        relevant_attribute_list = [(tag.name, tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 4)
        self.failUnless((u'bar', 2) in relevant_attribute_list)
        self.failUnless((u'baz', 1) in relevant_attribute_list)
        self.failUnless((u'foo', 1) in relevant_attribute_list)
        self.failUnless((u'ter', 1) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_queryset(Parrot.objects.filter(perch__size__gt=4), counts=True)
        relevant_attribute_list = [(tag.name, tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 4)
        self.failUnless((u'bar', 2) in relevant_attribute_list)
        self.failUnless((u'baz', 1) in relevant_attribute_list)
        self.failUnless((u'foo', 1) in relevant_attribute_list)
        self.failUnless((u'ter', 1) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_queryset(Parrot.objects.filter(perch__smelly=True), counts=True)
        relevant_attribute_list = [(tag.name, tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 3)
        self.failUnless((u'bar', 1) in relevant_attribute_list)
        self.failUnless((u'foo', 2) in relevant_attribute_list)
        self.failUnless((u'ter', 1) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_queryset(Parrot.objects.filter(perch__smelly=True), min_count=2)
        relevant_attribute_list = [(tag.name, tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 1)
        self.failUnless((u'foo', 2) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_queryset(Parrot.objects.filter(perch__size__gt=4))
        relevant_attribute_list = [(tag.name, hasattr(tag, 'counts')) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 4)
        self.failUnless((u'bar', False) in relevant_attribute_list)
        self.failUnless((u'baz', False) in relevant_attribute_list)
        self.failUnless((u'foo', False) in relevant_attribute_list)
        self.failUnless((u'ter', False) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_queryset(Parrot.objects.filter(perch__size__gt=99))
        relevant_attribute_list = [(tag.name, hasattr(tag, 'counts')) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 0)
        
        tag_usage = Tag.objects.usage_for_queryset(Parrot.objects.filter(Q(perch__size__gt=6) | Q(state__startswith='l')), counts=True)
        relevant_attribute_list = [(tag.name, tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 3)
        self.failUnless((u'bar', 2) in relevant_attribute_list)
        self.failUnless((u'foo', 1) in relevant_attribute_list)
        self.failUnless((u'ter', 1) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_queryset(Parrot.objects.filter(Q(perch__size__gt=6) | Q(state__startswith='l')), min_count=2)
        relevant_attribute_list = [(tag.name, tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 1)
        self.failUnless((u'bar', 2) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_queryset(Parrot.objects.filter(Q(perch__size__gt=6) | Q(state__startswith='l')))
        relevant_attribute_list = [(tag.name, hasattr(tag, 'counts')) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 3)
        self.failUnless((u'bar', False) in relevant_attribute_list)
        self.failUnless((u'foo', False) in relevant_attribute_list)
        self.failUnless((u'ter', False) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_queryset(Parrot.objects.exclude(state='passed on'), counts=True)
        relevant_attribute_list = [(tag.name, tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 3)
        self.failUnless((u'bar', 2) in relevant_attribute_list)
        self.failUnless((u'foo', 2) in relevant_attribute_list)
        self.failUnless((u'ter', 2) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_queryset(Parrot.objects.exclude(state__startswith='p'), min_count=2)
        relevant_attribute_list = [(tag.name, tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 1)
        self.failUnless((u'ter', 2) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_queryset(Parrot.objects.exclude(Q(perch__size__gt=6) | Q(perch__smelly=False)), counts=True)
        relevant_attribute_list = [(tag.name, tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 2)
        self.failUnless((u'foo', 1) in relevant_attribute_list)
        self.failUnless((u'ter', 1) in relevant_attribute_list)
        
        tag_usage = Tag.objects.usage_for_queryset(Parrot.objects.exclude(perch__smelly=True).filter(state__startswith='l'), counts=True)
        relevant_attribute_list = [(tag.name, tag.count) for tag in tag_usage]
        self.assertEquals(len(relevant_attribute_list), 2)
        self.failUnless((u'bar', 1) in relevant_attribute_list)
        self.failUnless((u'ter', 1) in relevant_attribute_list)
        
################
# Model Fields #
################

class TestTagFieldInForms(TestCase):
    def test_tag_field_in_modelform(self):
        # Ensure that automatically created forms use TagField
        class TestForm(forms.ModelForm):
            class Meta:
                model = FormTest
                
        form = TestForm()
        self.assertEquals(form.fields['tags'].__class__.__name__, 'TagField')
    
    def test_recreation_of_tag_list_string_representations(self):
        plain = Tag.objects.create(name='plain')
        spaces = Tag.objects.create(name='spa ces')
        comma = Tag.objects.create(name='com,ma')
        self.assertEquals(edit_string_for_tags([plain]), u'plain')
        self.assertEquals(edit_string_for_tags([plain, spaces]), u'plain, spa ces')
        self.assertEquals(edit_string_for_tags([plain, spaces, comma]), u'plain, spa ces, "com,ma"')
        self.assertEquals(edit_string_for_tags([plain, comma]), u'plain "com,ma"')
        self.assertEquals(edit_string_for_tags([comma, spaces]), u'"com,ma", spa ces')
    
    def test_tag_d_validation(self):
        t = TagField()
        self.assertEquals(t.clean('foo'), u'foo')
        self.assertEquals(t.clean('foo bar baz'), u'foo bar baz')
        self.assertEquals(t.clean('foo,bar,baz'), u'foo,bar,baz')
        self.assertEquals(t.clean('foo, bar, baz'), u'foo, bar, baz')
        self.assertEquals(t.clean('foo qwertyuiopasdfghjklzxcvbnmqwertyuiopasdfghjklzxcvb bar'),
            u'foo qwertyuiopasdfghjklzxcvbnmqwertyuiopasdfghjklzxcvb bar')
        try:
            t.clean('foo qwertyuiopasdfghjklzxcvbnmqwertyuiopasdfghjklzxcvbn bar')
        except forms.ValidationError, ve:
            self.assertEquals(str(ve), "[u'Each tag may be no more than 50 characters long.']")
        except Exception, e:
            raise e
        else:
            raise self.failureException('a ValidationError exception was supposed to have been raised.')

########NEW FILE########
__FILENAME__ = utils
"""
Tagging utilities - from user tag input parsing to tag cloud
calculation.
"""
import math
import types

from django.db.models.query import QuerySet
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext as _

# Python 2.3 compatibility
try:
    set
except NameError:
    from sets import Set as set

def parse_tag_input(input):
    """
    Parses tag input, with multiple word input being activated and
    delineated by commas and double quotes. Quotes take precedence, so
    they may contain commas.

    Returns a sorted list of unique tag names.
    """
    if not input:
        return []

    input = force_unicode(input)

    # Special case - if there are no commas or double quotes in the
    # input, we don't *do* a recall... I mean, we know we only need to
    # split on spaces.
    if u',' not in input and u'"' not in input:
        words = list(set(split_strip(input, u' ')))
        words.sort()
        return words

    words = []
    buffer = []
    # Defer splitting of non-quoted sections until we know if there are
    # any unquoted commas.
    to_be_split = []
    saw_loose_comma = False
    open_quote = False
    i = iter(input)
    try:
        while 1:
            c = i.next()
            if c == u'"':
                if buffer:
                    to_be_split.append(u''.join(buffer))
                    buffer = []
                # Find the matching quote
                open_quote = True
                c = i.next()
                while c != u'"':
                    buffer.append(c)
                    c = i.next()
                if buffer:
                    word = u''.join(buffer).strip()
                    if word:
                        words.append(word)
                    buffer = []
                open_quote = False
            else:
                if not saw_loose_comma and c == u',':
                    saw_loose_comma = True
                buffer.append(c)
    except StopIteration:
        # If we were parsing an open quote which was never closed treat
        # the buffer as unquoted.
        if buffer:
            if open_quote and u',' in buffer:
                saw_loose_comma = True
            to_be_split.append(u''.join(buffer))
    if to_be_split:
        if saw_loose_comma:
            delimiter = u','
        else:
            delimiter = u' '
        for chunk in to_be_split:
            words.extend(split_strip(chunk, delimiter))
    words = list(set(words))
    words.sort()
    return words

def split_strip(input, delimiter=u','):
    """
    Splits ``input`` on ``delimiter``, stripping each resulting string
    and returning a list of non-empty strings.
    """
    if not input:
        return []

    words = [w.strip() for w in input.split(delimiter)]
    return [w for w in words if w]

def edit_string_for_tags(tags):
    """
    Given list of ``Tag`` instances, creates a string representation of
    the list suitable for editing by the user, such that submitting the
    given string representation back without changing it will give the
    same list of tags.

    Tag names which contain commas will be double quoted.

    If any tag name which isn't being quoted contains whitespace, the
    resulting string of tag names will be comma-delimited, otherwise
    it will be space-delimited.
    """
    names = []
    use_commas = False
    for tag in tags:
        name = tag.name
        if u',' in name:
            names.append('"%s"' % name)
            continue
        elif u' ' in name:
            if not use_commas:
                use_commas = True
        names.append(name)
    if use_commas:
        glue = u', '
    else:
        glue = u' '
    return glue.join(names)

def get_queryset_and_model(queryset_or_model):
    """
    Given a ``QuerySet`` or a ``Model``, returns a two-tuple of
    (queryset, model).

    If a ``Model`` is given, the ``QuerySet`` returned will be created
    using its default manager.
    """
    try:
        return queryset_or_model, queryset_or_model.model
    except AttributeError:
        return queryset_or_model._default_manager.all(), queryset_or_model

def get_tag_list(tags):
    """
    Utility function for accepting tag input in a flexible manner.

    If a ``Tag`` object is given, it will be returned in a list as
    its single occupant.

    If given, the tag names in the following will be used to create a
    ``Tag`` ``QuerySet``:

       * A string, which may contain multiple tag names.
       * A list or tuple of strings corresponding to tag names.
       * A list or tuple of integers corresponding to tag ids.

    If given, the following will be returned as-is:

       * A list or tuple of ``Tag`` objects.
       * A ``Tag`` ``QuerySet``.

    """
    from tagging.models import Tag
    if isinstance(tags, Tag):
        return [tags]
    elif isinstance(tags, QuerySet) and tags.model is Tag:
        return tags
    elif isinstance(tags, types.StringTypes):
        return Tag.objects.filter(name__in=parse_tag_input(tags))
    elif isinstance(tags, (types.ListType, types.TupleType)):
        if len(tags) == 0:
            return tags
        contents = set()
        for item in tags:
            if isinstance(item, types.StringTypes):
                contents.add('string')
            elif isinstance(item, Tag):
                contents.add('tag')
            elif isinstance(item, (types.IntType, types.LongType)):
                contents.add('int')
        if len(contents) == 1:
            if 'string' in contents:
                return Tag.objects.filter(name__in=[force_unicode(tag) \
                                                    for tag in tags])
            elif 'tag' in contents:
                return tags
            elif 'int' in contents:
                return Tag.objects.filter(id__in=tags)
        else:
            raise ValueError(_('If a list or tuple of tags is provided, they must all be tag names, Tag objects or Tag ids.'))
    else:
        raise ValueError(_('The tag input given was invalid.'))

def get_tag(tag):
    """
    Utility function for accepting single tag input in a flexible
    manner.

    If a ``Tag`` object is given it will be returned as-is; if a
    string or integer are given, they will be used to lookup the
    appropriate ``Tag``.

    If no matching tag can be found, ``None`` will be returned.
    """
    from tagging.models import Tag
    if isinstance(tag, Tag):
        return tag

    try:
        if isinstance(tag, types.StringTypes):
            return Tag.objects.get(name=tag)
        elif isinstance(tag, (types.IntType, types.LongType)):
            return Tag.objects.get(id=tag)
    except Tag.DoesNotExist:
        pass

    return None

# Font size distribution algorithms
LOGARITHMIC, LINEAR = 1, 2

def _calculate_thresholds(min_weight, max_weight, steps):
    delta = (max_weight - min_weight) / float(steps)
    return [min_weight + i * delta for i in range(1, steps + 1)]

def _calculate_tag_weight(weight, max_weight, distribution):
    """
    Logarithmic tag weight calculation is based on code from the
    `Tag Cloud`_ plugin for Mephisto, by Sven Fuchs.

    .. _`Tag Cloud`: http://www.artweb-design.de/projects/mephisto-plugin-tag-cloud
    """
    if distribution == LINEAR or max_weight == 1:
        return weight
    elif distribution == LOGARITHMIC:
        return math.log(weight) * max_weight / math.log(max_weight)
    raise ValueError(_('Invalid distribution algorithm specified: %s.') % distribution)

def calculate_cloud(tags, steps=4, distribution=LOGARITHMIC):
    """
    Add a ``font_size`` attribute to each tag according to the
    frequency of its use, as indicated by its ``count``
    attribute.

    ``steps`` defines the range of font sizes - ``font_size`` will
    be an integer between 1 and ``steps`` (inclusive).

    ``distribution`` defines the type of font size distribution
    algorithm which will be used - logarithmic or linear. It must be
    one of ``tagging.utils.LOGARITHMIC`` or ``tagging.utils.LINEAR``.
    """
    if len(tags) > 0:
        counts = [tag.count for tag in tags]
        min_weight = float(min(counts))
        max_weight = float(max(counts))
        thresholds = _calculate_thresholds(min_weight, max_weight, steps)
        for tag in tags:
            font_set = False
            tag_weight = _calculate_tag_weight(tag.count, max_weight, distribution)
            for i in range(steps):
                if not font_set and tag_weight <= thresholds[i]:
                    tag.font_size = i + 1
                    font_set = True
    return tags

########NEW FILE########
__FILENAME__ = views
"""
Tagging related views.
"""
from django.http import Http404
from django.utils.translation import ugettext as _
from django.views.generic.list_detail import object_list

from tagging.models import Tag, TaggedItem
from tagging.utils import get_tag, get_queryset_and_model

def tagged_object_list(request, queryset_or_model=None, tag=None,
        related_tags=False, related_tag_counts=True, **kwargs):
    """
    A thin wrapper around
    ``django.views.generic.list_detail.object_list`` which creates a
    ``QuerySet`` containing instances of the given queryset or model
    tagged with the given tag.

    In addition to the context variables set up by ``object_list``, a
    ``tag`` context variable will contain the ``Tag`` instance for the
    tag.

    If ``related_tags`` is ``True``, a ``related_tags`` context variable
    will contain tags related to the given tag for the given model.
    Additionally, if ``related_tag_counts`` is ``True``, each related
    tag will have a ``count`` attribute indicating the number of items
    which have it in addition to the given tag.
    """
    if queryset_or_model is None:
        try:
            queryset_or_model = kwargs.pop('queryset_or_model')
        except KeyError:
            raise AttributeError(_('tagged_object_list must be called with a queryset or a model.'))

    if tag is None:
        try:
            tag = kwargs.pop('tag')
        except KeyError:
            raise AttributeError(_('tagged_object_list must be called with a tag.'))

    tag_instance = get_tag(tag)
    if tag_instance is None:
        raise Http404(_('No Tag found matching "%s".') % tag)
    queryset = TaggedItem.objects.get_by_model(queryset_or_model, tag_instance)
    if not kwargs.has_key('extra_context'):
        kwargs['extra_context'] = {}
    kwargs['extra_context']['tag'] = tag_instance
    if related_tags:
        kwargs['extra_context']['related_tags'] = \
            Tag.objects.related_for_model(tag_instance, queryset_or_model,
                                          counts=related_tag_counts)
    return object_list(request, queryset, **kwargs)

########NEW FILE########
