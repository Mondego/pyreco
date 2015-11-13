__FILENAME__ = admin
from django.contrib import admin
from tagging.models import Tag, TaggedItem, Synonym
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from tagging import settings
from tagging.forms import TagAdminForm

admin.site.register(TaggedItem)

if settings.MULTILINGUAL_TAGS:
    import multilingual

    def _name(tag):
        return tag.name_any
    _name.short_description = _('name')

    def _synonyms(tag):
        return ', '.join(s.name for s in tag.synonyms.all())
    _synonyms.short_description = _('synonyms')

    def _translations(tag):
        return ', '.join(s.name for s in tag.translations.all())
    _translations.short_description = _('translations')

    class TagAdmin(multilingual.ModelAdmin):
        form = TagAdminForm
        list_display = (_name, _synonyms, _translations)
        search_fields = ('name', 'synonyms__name', 'translations__name')

    _synonym_tag_name = 'name_any'
else:
    class TagAdmin(admin.ModelAdmin):
        form = TagAdminForm
        list_display = ('name',)
        search_fields = ('name', 'synonyms__name')

    _synonym_tag_name = 'name'


admin.site.register(Tag, TagAdmin)

def _tag_name(synonym):
    return '<a href="%s">%s</a>' % (
        reverse('admin:tagging_tag_change', args=(synonym.tag.id,)),
        getattr(synonym.tag, _synonym_tag_name)
    )
_tag_name.short_description = _('tag')
_tag_name.allow_tags = True

admin.site.register(Synonym,
    list_display = ('name', _tag_name),
    search_fields = ('name',),
)


########NEW FILE########
__FILENAME__ = fields
"""
A custom Model Field for tagging.
"""
from django.db import IntegrityError
from django.db.models import signals
from django.db.models.fields import CharField
from django.utils.translation import ugettext_lazy as _

from tagging import settings
from tagging.models import Tag, Synonym
from tagging.utils import edit_string_for_tags, parse_tag_input

class TagField(CharField):
    """
    A "special" character field that actually works as a relationship to tags
    "under the hood". This exposes a space-separated string of tags, but does
    the splitting/reordering/etc. under the hood.
    """
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 255)
        kwargs['blank'] = kwargs.get('blank', True)
        if kwargs.has_key('create_synonyms'):
            self.create_synonyms = kwargs.pop('create_synonyms')
        else:
            self.create_synonyms = None
        super(TagField, self).__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name):
        super(TagField, self).contribute_to_class(cls, name)

        # Make this object the descriptor for field access.
        setattr(cls, self.name, self)

        # Save tags back to the database post-save
        signals.post_save.connect(self._post_save, cls, True)
        signals.pre_save.connect(self._pre_save, cls, True)

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

        tags = self._get_instance_tag_cache(instance)
        if tags is None:
            if instance.pk is None:
                self._set_instance_tag_cache(instance, '')
            else:
                self._set_instance_tag_cache(
                    instance, edit_string_for_tags(Tag.objects.get_for_object(instance)))
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

    def _pre_save(self, **kwargs): #signal, sender, instance):
        """
        Save tags back to the database
        """
        tags = self._get_instance_tag_cache(kwargs['instance'])
        tags = parse_tag_input(tags)

        #print 'Tags before: %s' % tags
        instance = kwargs['instance']
        self._set_instance_tag_cache(
            instance, edit_string_for_tags(tags))

    def _post_save(self, **kwargs): #signal, sender, instance):
        """
        Save tags back to the database
        """
        tags = self._get_instance_tag_cache(kwargs['instance'])
        if tags is not None:
            Tag.objects.update_tags(kwargs['instance'], tags)

        if self.create_synonyms is not None:
            tags = parse_tag_input(tags)
            for tag in tags:
                synonyms = self.create_synonyms(tag)
                try:
                    tag = Tag.objects.get(name=tag)
                    for synonym in synonyms:
                        try:
                            synonym = Synonym.objects.create(name=synonym, tag=tag)
                        except IntegrityError:
                            pass
                except Tag.DoesNotExist:
                    pass

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

import logging

logger = logging.getLogger('tagging.models')

from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import connection, models, IntegrityError
from django.db.models.query import QuerySet
from django.utils.translation import ugettext_lazy as _

from tagging import settings
from tagging.utils import calculate_cloud, get_tag_list, get_queryset_and_model, parse_tag_input
from tagging.utils import LOGARITHMIC

qn = connection.ops.quote_name

if settings.MULTILINGUAL_TAGS:
    import multilingual
    BaseManager = multilingual.Manager
else:
    BaseManager = models.Manager

############
# Managers #
############

class TagManager(BaseManager):
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
        current_tag_names = [tag.name or tag.name_any for tag in current_tags]
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
        SELECT DISTINCT %(tag)s.id%(count_sql)s
        FROM
            %(tag)s
            INNER JOIN %(tagged_item)s
                ON %(tag)s.id = %(tagged_item)s.tag_id
            INNER JOIN %(model)s
                ON %(tagged_item)s.object_id = %(model_pk)s
            %%s
        WHERE %(tagged_item)s.content_type_id = %(content_type_id)s
            %%s
        GROUP BY %(tag)s.id
        %%s""" % {
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
        # TODO add ordering by name right here
        for row in cursor.fetchall():
            t = self.model.objects.get(pk = row[0])
            if counts:
                t.count = row[1]
            tags.append(t)
        tags.sort()
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
        SELECT %(tag)s.id%(count_sql)s
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
        GROUP BY %(tag)s.id
        %(min_count_sql)s""" % {
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
            tag = self.model.objects.get(pk = row[0])
            if counts is True:
                tag.count = row[1]
            related.append(tag)
        related.sort()
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

    def process_rules(self, rules):
        for line in rules.split('\n'):
            self._process_line(line)
        return True

    def _process_line(self, line):
        logger.debug('processing line "%s"' % line)

        def join(tags):
            self.join([tag[0] for tag in tags if tag])

        if '==' in line:
            names = [name.strip() for name in line.split('==')]

            try:
                tag = self.get(name=names[0])
            except Tag.DoesNotExist:
                return

            for syn_name in names[1:]:
                try:
                    syn = Synonym(name=syn_name, tag=tag)
                    syn.save()
                except IntegrityError:
                    pass

            join([self.filter(name=name)[:1] for name in names])

        elif '=' in line:
            join([self.filter(name=name.strip())[:1] \
                  for name in line.split('=')])

        elif ':' in line:
            parts = line.split(';')
            if len(parts) > 0:
                changed = False
                head = [p.strip() for p in parts[0].split(':')][:2]
                tag_from = head[0]
                tag_to = (len(head)==2) and head[1] or head[0]

                try:
                    tag = self.get(name=tag_from)
                except Tag.DoesNotExist:
                    return

                if tag.name != tag_to:
                    tag.name = tag_to
                    changed = True

                names = [tuple(i.strip() for i in p.split(':')) for p in parts[1:]]
                for name in names:
                    if len(name) == 2 and getattr(tag, 'name_%s' % name[0], None) != name[1]:
                        setattr(tag, 'name_%s' % name[0], name[1])
                        changed = True

                if changed:
                    tag.save()

    def dumpAsText(self):
        tags = self.all()
        return '\n'.join(filter(lambda x: x, \
                [self.dumpSynonymsAsText(t) for t in tags] + \
                [self.dumpTagAsText(t) for t in tags]))

    def dumpTagAsText(self, tag):
        parts = [tag.name, ]
        for id, code in multilingual.languages.get_language_choices():
            name = tag.get_translation(id, 'name').name
            if name:
                parts.append('%s: %s' % (code, name))

        return '; '.join(parts)

    def dumpSynonymsAsText(self, tag):
        synonyms = tag.synonyms.all()
        if len(synonyms) > 0:
            return ' == '.join([tag.name, ] + [s.name for s in synonyms])
        return ''

    def join(self, query):
        """This method joins multiple tags together."""
        from tagging.utils import merge

        logger.info('Joining %s' % ','.join([unicode(obj) for obj in query]))
        tags = list(query)
        if len(tags) < 2:
            return

        first = tags[0]
        tags = tags[1:]
        for t in tags:
            merge(first, t)


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
    if settings.MULTILINGUAL_TAGS:
        class Translation(multilingual.Translation):
            name = models.CharField(_('name'), max_length=50, unique=True, db_index=True)
    else:
        name = models.CharField(_('name'), max_length=50, unique=True, db_index=True)

    objects = TagManager()

    class Meta:
        if not settings.MULTILINGUAL_TAGS:
            ordering = ('name',)
        verbose_name = _('tag')
        verbose_name_plural = _('tags')

    def __unicode__(self):
        return self.name or 'tag-with-id: %d' % self.id

    def __lt__(self, other):
        return self.name < other.name

    def delete(self, update = True):
        if update:
            self._updateLinkedObjects(remove_this = True)
        return super(Tag, self).delete()

    def save(self, *args, **kwargs):
        result = super(Tag, self).save(*args, **kwargs)
        self._updateLinkedObjects()
        return result

    def _updateLinkedObjects(self, remove_this = False):
        """Updates TagField's for all objects with this tag."""
        for item in TaggedItem.objects.filter(tag=self):
            item._updateLinkedObjects(remove_this=remove_this)

if settings.MULTILINGUAL_TAGS:
    """Monkey-patching for translation getter,
       to fallback to another translation."""

    from multilingual.translation import getter_generator
    _orig_name_getter = Tag.get_name
    def _my_get_name(self, language_id = None, fallback = False):
        value = _orig_name_getter(self, language_id, fallback)
        if value is None and language_id is None:
            #print 'BLAH BLAH for lang_id: %s' % language_id
            value = _orig_name_getter(self, settings.FALLBACK_LANGUAGE, fallback)
            #print 'New value for lang_id=%s is %s' % (settings.FALLBACK_LANGUAGE, value)
        return value
    _my_get_name.short_description = getattr(Tag.name, 'verbose_name', 'name')
    setattr(Tag, 'get_name', _my_get_name)

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

    def _updateLinkedObjects(self, remove_this = False):
        from tagging.fields import TagField
        object_tags = [ tag.name or tag.name_any \
                      for tag in Tag.objects.get_for_object(self.object) \
                              if not remove_this or tag.id != self.tag_id ]
        tags_as_string = ', '.join(object_tags)

        for field in self.object._meta.fields:
            if isinstance(field, TagField):
                setattr(self.object, field.attname, tags_as_string)
                self.object.save()
                break

    def delete(self, update = True):
        if update:
            self._updateLinkedObjects(remove_this=True)
        return super(TaggedItem, self).delete()

class Synonym(models.Model):
    name = models.CharField(max_length=50, unique=True, db_index=True)
    tag = models.ForeignKey(Tag, related_name='synonyms')

    def __unicode__(self):
        return u'%s, synonym for %s' % (self.name, self.tag)

    class Meta:
        verbose_name = _("Tag's synonym")
        verbose_name_plural = _("Tags' synonyms")
        ordering = ('name',)


########NEW FILE########
__FILENAME__ = settings
"""
Convenience module for access of custom tagging application settings,
which enforces default settings when the main settings module does not
contain the appropriate settings.
"""
from django.conf import settings

# Whether to force all tags to lowercase before they are saved to the
# database.
FORCE_LOWERCASE_TAGS = getattr(settings, 'FORCE_LOWERCASE_TAGS', False)

# Force a delimiter string for tags.
FORCE_TAG_DELIMITER = getattr(settings, 'FORCE_TAG_DELIMITER', None)

# The maximum length of a tag's name.
MAX_TAG_LENGTH = getattr(settings, 'MAX_TAG_LENGTH', 50)

# Whether to use multilingual tags
MULTILINGUAL_TAGS = getattr(settings, 'MULTILINGUAL_TAGS', False)
if MULTILINGUAL_TAGS:
    DEFAULT_LANGUAGE = getattr(settings, 'DEFAULT_LANGUAGE')
    FALLBACK_LANGUAGE = getattr(settings, 'FALLBACK_LANGUAGE', DEFAULT_LANGUAGE)


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

class RelatedObjectsNode(Node):
    def __init__(self, obj, context_var, limit):
        self.obj = obj
        self.context_var = context_var
        self.limit = int(limit)

    def render(self, context):
        self.obj = resolve_variable(self.obj, context)
        context[self.context_var] = TaggedItem.objects.get_related(
            self.obj,
            self.obj.__class__,
            num = self.limit
        )
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

def do_related_objects(parser, token):
    """
    Retrieves a list of related objects for a given object
    and stores them in a context variable.

    Example usage::

        {% related_objects for entry as object_list limit 10 %}
    """
    bits = token.contents.split()
    if len(bits) != 7:
        raise TemplateSyntaxError('%s tag requires exactly five arguments' % bits[0])
    if bits[1] != 'for':
        raise TemplateSyntaxError("first argument to %s tag must be 'for'" % bits[0])
    if bits[3] != 'as':
        raise TemplateSyntaxError("third argument to %s tag must be 'as'" % bits[0])
    if bits[5] != 'limit':
        raise TemplateSyntaxError("third argument to %s tag must be 'limit'" % bits[0])
    return RelatedObjectsNode(bits[2], bits[4], bits[6])

register.tag('tags_for_model', do_tags_for_model)
register.tag('tag_cloud_for_model', do_tag_cloud_for_model)
register.tag('tags_for_object', do_tags_for_object)
register.tag('tagged_objects', do_tagged_objects)
register.tag('related_objects', do_related_objects)

########NEW FILE########
__FILENAME__ = core_tests
# -*- coding: utf-8 -*-
import os
from pdb import set_trace
from unittest import TestCase
from django import forms
from django.db.models import Q
from tagging.forms import TagField
from tagging import settings
from tagging.models import Tag, TaggedItem
from tagging.tests.models import Article, Link, Perch, Parrot, FormTest
from tagging.utils import calculate_cloud, get_tag_list, get_tag, parse_tag_input
from tagging.utils import LINEAR

class BaseTestCase(TestCase):
    def setUp(self):
        super(BaseTestCase, self).setUp()
        Tag.objects.all().delete()

    def assertListsEqual(self, left, right):
        self.assertEqual(list(left), list(right))

class UtitlitiesTests(BaseTestCase):
    def testSimpleSpaceDelimitedTags(self):
        self.assertEqual([u'one'], parse_tag_input('one'))
        self.assertEqual([u'one', u'two'], parse_tag_input('one two'))
        self.assertEqual([u'one', u'three', u'two'], parse_tag_input('one two three'))
        self.assertEqual([u'one', u'two'], parse_tag_input('one one two two'))

    def testCommaDelimitedMultipleWords(self):
        """An unquoted comma in the input will trigger"""
        self.assertEqual([u'one'], parse_tag_input(',one'))
        self.assertEqual([u'one two'], parse_tag_input(',one two'))
        self.assertEqual([u'one two three'], parse_tag_input(',one two three'))
        self.assertEqual([u'a-one', u'a-two and a-three'], parse_tag_input('a-one, a-two and a-three'))

    def testDoubleQuotedMultipleWords(self):
        """A completed quote will trigger this. Unclosed quotes are ignored."""
        self.assertEqual([u'one'], parse_tag_input('"one'))
        self.assertEqual([u'one', u'two'], parse_tag_input('"one two'))
        self.assertEqual([u'one', u'three', u'two'], parse_tag_input('"one two three'))
        self.assertEqual([u'one two'], parse_tag_input('"one two"'))
        self.assertEqual([u'a-one', u'a-two and a-three'], parse_tag_input('a-one "a-two and a-three"'))

    def testNoLooseCommasSplitOnSpaces(self):
        self.assertEqual([u'one', u'thr,ee', u'two'], parse_tag_input('one two "thr,ee"'))

    def testLooseCommasSplitOnCommas(self):
        self.assertEqual([u'one', u'two three'], parse_tag_input('"one", two three'))

    def testDoubleQuotesCanContainCommas(self):
        self.assertEqual([u'a-one', u'a-two, and a-three'], parse_tag_input('a-one "a-two, and a-three"'))
        self.assertEqual([u'one', u'two'], parse_tag_input('"two", one, one, two, "one"'))

    def testBadUsersNaughtyUsers(self):
        self.assertEqual([], parse_tag_input(None))
        self.assertEqual([], parse_tag_input(''))
        self.assertEqual([], parse_tag_input('"'))
        self.assertEqual([], parse_tag_input('""'))
        self.assertEqual([], parse_tag_input('"' * 7))
        self.assertEqual([], parse_tag_input(',,,,,,'))
        self.assertEqual([u','], parse_tag_input('",",",",",",","'))
        self.assertEqual([u'a-one', u'a-three', u'a-two', u'and'], parse_tag_input('a-one "a-two" and "a-three'))

    def testNormalisedTagListInput(self):
        cheese = Tag.objects.create(name='cheese')
        toast = Tag.objects.create(name='toast')
        self.assertListsEqual([cheese], get_tag_list(cheese))
        self.assertListsEqual([cheese, toast], get_tag_list('cheese toast'))
        self.assertListsEqual([cheese, toast], get_tag_list('cheese,toast'))
        self.assertListsEqual([], get_tag_list([]))
        self.assertListsEqual([cheese, toast], get_tag_list(['cheese', 'toast']))
        self.assertListsEqual([cheese, toast], get_tag_list([cheese.id, toast.id]))
        self.assertListsEqual([cheese, toast], get_tag_list(['cheese', 'toast', 'ŠĐĆŽćžšđ']))
        self.assertListsEqual([cheese, toast], get_tag_list([cheese, toast]))
        self.assertEqual((cheese, toast), get_tag_list((cheese, toast)))
        self.assertListsEqual([cheese, toast], get_tag_list(Tag.objects.filter(name__in=['cheese', 'toast'])))
        self.assertRaises(ValueError, get_tag_list, ['cheese', toast])
        self.assertRaises(ValueError, get_tag_list, 29)

    def testNormalisedTagInput(self):
        cheese = Tag.objects.create(name='cheese')
        self.assertEqual(cheese, get_tag(cheese))
        self.assertEqual(cheese, get_tag('cheese'))
        self.assertEqual(cheese, get_tag(cheese.id))
        self.assertEqual(None, get_tag('mouse'))

    def testTagClouds(self):
        tags = []
        for line in open(os.path.join(os.path.dirname(__file__), 'tags.txt')).readlines():
            name, count = line.rstrip().split()
            tag = Tag(name=name)
            tag.count = int(count)
            tags.append(tag)

        sizes = {}
        for tag in calculate_cloud(tags, steps=5):
            sizes[tag.font_size] = sizes.get(tag.font_size, 0) + 1

        # This isn't a pre-calculated test, just making sure it's consistent
        self.assertEqual({1: 48, 2: 30, 3: 19, 4: 15, 5: 10}, sizes)

        sizes = {}
        for tag in calculate_cloud(tags, steps=5, distribution=LINEAR):
            sizes[tag.font_size] = sizes.get(tag.font_size, 0) + 1

        # This isn't a pre-calculated test, just making sure it's consistent
        self.assertEqual({1: 97, 2: 12, 3: 7, 4: 2, 5: 4}, sizes)

        self.assertRaises(ValueError, calculate_cloud, tags, steps=5, distribution='cheese')

def get_tagcounts(query):
    return [(tag.name, getattr(tag, 'count', False)) for tag in query]

def get_tagnames(query):
    return [tag.name for tag in query]

class TaggingTests(BaseTestCase):
    def testBasicTagging(self):
        dead = Parrot.objects.create(state='dead')
        Tag.objects.update_tags(dead, 'foo,bar,"ter"')

        self.assertListsEqual(get_tag_list('bar foo ter'), Tag.objects.get_for_object(dead))

        Tag.objects.update_tags(dead, '"foo" bar "baz"')
        self.assertListsEqual(get_tag_list('bar baz foo'), Tag.objects.get_for_object(dead))

        Tag.objects.add_tag(dead, 'foo')
        self.assertListsEqual(get_tag_list('bar baz foo'), Tag.objects.get_for_object(dead))

        Tag.objects.add_tag(dead, 'zip')
        self.assertListsEqual(get_tag_list('bar baz foo zip'), Tag.objects.get_for_object(dead))

        self.assertRaises(AttributeError, Tag.objects.add_tag, dead, '    ')
        self.assertRaises(AttributeError, Tag.objects.add_tag, dead, 'one two')

        Tag.objects.update_tags(dead, 'ŠĐĆŽćžšđ')
        self.assertEqual(
            '[<Tag: \xc5\xa0\xc4\x90\xc4\x86\xc5\xbd\xc4\x87\xc5\xbe\xc5\xa1\xc4\x91>]',
            repr(Tag.objects.get_for_object(dead)))

        Tag.objects.update_tags(dead, None)
        self.assertListsEqual([], Tag.objects.get_for_object(dead))

    def testUsingAModelsTagField(self):
        f1 = FormTest.objects.create(tags=u'test3 test2 test1')
        self.assertListsEqual(get_tag_list('test1 test2 test3'), Tag.objects.get_for_object(f1))
        f1.tags = u'test4'
        f1.save()
        self.assertListsEqual(get_tag_list('test4'), Tag.objects.get_for_object(f1))
        f1.tags = ''
        f1.save()
        self.assertListsEqual([], Tag.objects.get_for_object(f1))

    def testForcingTagsToLowercase(self):
        settings.FORCE_LOWERCASE_TAGS = True

        dead = Parrot.objects.create(state='dead')
        Tag.objects.update_tags(dead, 'foO bAr Ter')
        self.assertListsEqual(get_tag_list('bar foo ter'), Tag.objects.get_for_object(dead))

        Tag.objects.update_tags(dead, 'foO bAr baZ')
        self.assertListsEqual(get_tag_list('bar baz foo'), Tag.objects.get_for_object(dead))

        Tag.objects.add_tag(dead, 'FOO')
        self.assertListsEqual(get_tag_list('bar baz foo'), Tag.objects.get_for_object(dead))

        Tag.objects.add_tag(dead, 'Zip')
        self.assertListsEqual(get_tag_list('bar baz foo zip'), Tag.objects.get_for_object(dead))

        Tag.objects.update_tags(dead, None)
        f1 = FormTest.objects.create(tags=u'test3 test2 test1')
        f1.tags = u'TEST5'
        f1.save()
        self.assertListsEqual(get_tag_list('test5'), Tag.objects.get_for_object(f1))
        self.assertEqual(u'test5', f1.tags)

class RetrivingTests(BaseTestCase):
    def setUp(self):
        super(RetrivingTests, self).setUp()

        self.assertEqual([], Tag.objects.usage_for_model(Parrot))
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


    def testRetrievingTagsByModel(self):
        self.assertEqual(
            [(u'bar', 3), (u'baz', 1), (u'foo', 2), (u'ter', 3)],
            get_tagcounts(Tag.objects.usage_for_model(Parrot, counts=True)))
        self.assertEqual(
            [(u'bar', 3), (u'foo', 2), (u'ter', 3)],
            get_tagcounts(Tag.objects.usage_for_model(Parrot, min_count=2)))

    def testLimitingResultsToASubsetOfTheModel(self):
        self.assertEqual([(u'foo', 1), (u'ter', 1)],
            get_tagcounts(Tag.objects.usage_for_model(Parrot, counts=True, filters=dict(state='no more'))))
        self.assertEqual([(u'bar', 2), (u'baz', 1), (u'foo', 1), (u'ter', 1)],
            get_tagcounts(Tag.objects.usage_for_model(Parrot, counts=True, filters=dict(state__startswith='p'))))
        self.assertEqual([(u'bar', 2), (u'baz', 1), (u'foo', 1), (u'ter', 1)],
            get_tagcounts(Tag.objects.usage_for_model(Parrot, counts=True, filters=dict(perch__size__gt=4))))
        self.assertEqual([(u'bar', 1), (u'foo', 2), (u'ter', 1)],
            get_tagcounts(Tag.objects.usage_for_model(Parrot, counts=True, filters=dict(perch__smelly=True))))
        self.assertEqual([(u'foo', 2)],
            get_tagcounts(Tag.objects.usage_for_model(Parrot, min_count=2, filters=dict(perch__smelly=True))))
        self.assertEqual([(u'bar', False), (u'baz', False), (u'foo', False), (u'ter', False)],
            get_tagcounts(Tag.objects.usage_for_model(Parrot, filters=dict(perch__size__gt=4))))
        self.assertEqual([],
            get_tagcounts(Tag.objects.usage_for_model(Parrot, filters=dict(perch__size__gt=99))))

    def testRelatedTags(self):
        self.assertEqual([(u'baz', 1), (u'foo', 1), (u'ter', 2)],
            get_tagcounts(Tag.objects.related_for_model(Tag.objects.filter(name__in=['bar']), Parrot, counts=True)))
        self.assertEqual([(u'ter', 2)],
            get_tagcounts(Tag.objects.related_for_model(Tag.objects.filter(name__in=['bar']), Parrot, min_count=2)))
        self.assertEqual([u'baz', u'foo', u'ter'],
            get_tagnames(Tag.objects.related_for_model(Tag.objects.filter(name__in=['bar']), Parrot, counts=False)))
        self.assertEqual([(u'baz', 1)],
            get_tagcounts(Tag.objects.related_for_model(Tag.objects.filter(name__in=['bar', 'ter']), Parrot, counts=True)))
        self.assertEqual([],
            get_tagcounts(Tag.objects.related_for_model(Tag.objects.filter(name__in=['bar', 'ter', 'baz']), Parrot, counts=True)))

    def testRelatesTagsWithStrings(self):
        self.assertEqual([(u'baz', 1), (u'foo', 1), (u'ter', 2)],
            get_tagcounts(Tag.objects.related_for_model('bar', Parrot, counts=True)))
        self.assertEqual([(u'ter', 2)],
            get_tagcounts(Tag.objects.related_for_model('bar', Parrot, min_count=2)))
        self.assertEqual([u'baz', u'foo', u'ter'],
            get_tagnames(Tag.objects.related_for_model('bar', Parrot, counts=False)))
        self.assertEqual([(u'baz', 1)],
            get_tagcounts(Tag.objects.related_for_model(['bar', 'ter'], Parrot, counts=True)))
        self.assertEqual([],
            get_tagcounts(Tag.objects.related_for_model(['bar', 'ter', 'baz'], Parrot, counts=True)))

    def testRetrievingTaggedObjectsByModel(self):
        self.assertEqual(
            '[<Parrot: no more>, <Parrot: pining for the fjords>]',
            repr(TaggedItem.objects.get_by_model(Parrot, self.foo)))
        self.assertEqual(
            '[<Parrot: late>, <Parrot: passed on>, <Parrot: pining for the fjords>]',
            repr(TaggedItem.objects.get_by_model(Parrot, self.bar)))


    def testIntersectionsAreSupported(self):
        self.assertListsEqual([], TaggedItem.objects.get_by_model(Parrot, [self.foo, self.baz]))
        self.assertEqual('[<Parrot: pining for the fjords>]', repr(TaggedItem.objects.get_by_model(Parrot, [self.foo, self.bar])))
        self.assertEqual('[<Parrot: late>, <Parrot: passed on>]', repr(TaggedItem.objects.get_by_model(Parrot, [self.bar, self.ter])))

    def testIssue114IntersectionWithNonExistantTags(self):
        self.assertListsEqual([], TaggedItem.objects.get_intersection_by_model(Parrot, []))

    def testYouCanAlsoPassTagQuerySets(self):
        self.assertListsEqual([], TaggedItem.objects.get_by_model(Parrot, Tag.objects.filter(name__in=['foo', 'baz'])))
        self.assertEqual('[<Parrot: pining for the fjords>]',
            repr(TaggedItem.objects.get_by_model(Parrot, Tag.objects.filter(name__in=['foo', 'bar']))))
        self.assertEqual('[<Parrot: late>, <Parrot: passed on>]',
            repr(TaggedItem.objects.get_by_model(Parrot, Tag.objects.filter(name__in=['bar', 'ter']))))

    def testYouCanAlsoPassStringsAndListsOfStrings(self):
        self.assertListsEqual([], TaggedItem.objects.get_by_model(Parrot, 'foo baz'))
        self.assertEqual('[<Parrot: pining for the fjords>]', repr(TaggedItem.objects.get_by_model(Parrot, 'foo bar')))
        self.assertEqual('[<Parrot: late>, <Parrot: passed on>]', repr(TaggedItem.objects.get_by_model(Parrot, 'bar ter')))
        self.assertListsEqual([], TaggedItem.objects.get_by_model(Parrot, ['foo', 'baz']))
        self.assertEqual('[<Parrot: pining for the fjords>]', repr(TaggedItem.objects.get_by_model(Parrot, ['foo', 'bar'])))
        self.assertEqual('[<Parrot: late>, <Parrot: passed on>]', repr(TaggedItem.objects.get_by_model(Parrot, ['bar', 'ter'])))

    def testIssue50GetByNonExistentTag(self):
        self.assertListsEqual([], TaggedItem.objects.get_by_model(Parrot, 'argatrons'))

    def testUnions(self):
        self.assertEqual('[<Parrot: late>, <Parrot: no more>, <Parrot: passed on>, <Parrot: pining for the fjords>]',
            repr(TaggedItem.objects.get_union_by_model(Parrot, ['foo', 'ter'])))
        self.assertEqual('[<Parrot: late>, <Parrot: passed on>, <Parrot: pining for the fjords>]',
            repr(TaggedItem.objects.get_union_by_model(Parrot, ['bar', 'baz'])))

    def testIssue114UnionWithNonExistantTags(self):
        self.assertListsEqual([], TaggedItem.objects.get_union_by_model(Parrot, []))

    def testLimitingResultsToAQueryset(self):
        self.assertEqual([(u'foo', 1), (u'ter', 1)],
            get_tagcounts(Tag.objects.usage_for_queryset(Parrot.objects.filter(state='no more'), counts=True)))
        self.assertEqual([(u'bar', 2), (u'baz', 1), (u'foo', 1), (u'ter', 1)],
            get_tagcounts(Tag.objects.usage_for_queryset(Parrot.objects.filter(state__startswith='p'), counts=True)))
        self.assertEqual([(u'bar', 2), (u'baz', 1), (u'foo', 1), (u'ter', 1)],
            get_tagcounts(Tag.objects.usage_for_queryset(Parrot.objects.filter(perch__size__gt=4), counts=True)))
        self.assertEqual([(u'bar', 1), (u'foo', 2), (u'ter', 1)],
            get_tagcounts(Tag.objects.usage_for_queryset(Parrot.objects.filter(perch__smelly=True), counts=True)))
        self.assertEqual([(u'foo', 2)],
            get_tagcounts(Tag.objects.usage_for_queryset(Parrot.objects.filter(perch__smelly=True), min_count=2)))
        self.assertEqual([(u'bar', False), (u'baz', False), (u'foo', False), (u'ter', False)],
            get_tagcounts(Tag.objects.usage_for_queryset(Parrot.objects.filter(perch__size__gt=4))))
        self.assertEqual([],
            get_tagcounts(Tag.objects.usage_for_queryset(Parrot.objects.filter(perch__size__gt=99))))
        self.assertEqual([(u'bar', 2), (u'foo', 1), (u'ter', 1)],
            get_tagcounts(Tag.objects.usage_for_queryset(Parrot.objects.filter(Q(perch__size__gt=6) | Q(state__startswith='l')), counts=True)))
        self.assertEqual([(u'bar', 2)],
            get_tagcounts(Tag.objects.usage_for_queryset(Parrot.objects.filter(Q(perch__size__gt=6) | Q(state__startswith='l')), min_count=2)))
        self.assertEqual([(u'bar', False), (u'foo', False), (u'ter', False)],
            get_tagcounts(Tag.objects.usage_for_queryset(Parrot.objects.filter(Q(perch__size__gt=6) | Q(state__startswith='l')))))
        self.assertEqual([(u'bar', 2), (u'foo', 2), (u'ter', 2)],
            get_tagcounts(Tag.objects.usage_for_queryset(Parrot.objects.exclude(state='passed on'), counts=True)))
        self.assertEqual([(u'ter', 2)],
            get_tagcounts(Tag.objects.usage_for_queryset(Parrot.objects.exclude(state__startswith='p'), min_count=2)))
        self.assertEqual([(u'foo', 1), (u'ter', 1)],
            get_tagcounts(Tag.objects.usage_for_queryset(Parrot.objects.exclude(Q(perch__size__gt=6) | Q(perch__smelly=False)), counts=True)))
        self.assertEqual([(u'bar', 1), (u'ter', 1)],
            get_tagcounts(Tag.objects.usage_for_queryset(Parrot.objects.exclude(perch__smelly=True).filter(state__startswith='l'), counts=True)))


class RelatedTests(BaseTestCase):
    def setUp(self):
        super(RelatedTests, self).setUp()

        self.l1 = Link.objects.create(name='link 1')
        Tag.objects.update_tags(self.l1, 'tag1 tag2 tag3 tag4 tag5')
        self.l2 = Link.objects.create(name='link 2')
        Tag.objects.update_tags(self.l2, 'tag1 tag2 tag3')
        self.l3 = Link.objects.create(name='link 3')
        Tag.objects.update_tags(self.l3, 'tag1')
        self.l4 = Link.objects.create(name='link 4')

    def testRelatedInstancesOfTheSameModel(self):
        self.assertEqual('[<Link: link 2>, <Link: link 3>]', repr(TaggedItem.objects.get_related(self.l1, Link)))
        self.assertEqual('[<Link: link 2>]', repr(TaggedItem.objects.get_related(self.l1, Link, num=1)))
        self.assertListsEqual([], TaggedItem.objects.get_related(self.l4, Link))

    def testLimitRelatedItems(self):
        self.assertEqual([self.l2], TaggedItem.objects.get_related(self.l1, Link.objects.exclude(name='link 3')))

    def testRelatedInstanceOfADifferentModel(self):
        a1 = Article.objects.create(name='article 1')
        Tag.objects.update_tags(a1, 'tag1 tag2 tag3 tag4')
        self.assertListsEqual([self.l1, self.l2, self.l3], TaggedItem.objects.get_related(a1, Link))
        Tag.objects.update_tags(a1, 'tag6')
        self.assertListsEqual([], TaggedItem.objects.get_related(a1, Link))

class TagFieldTests(BaseTestCase):
    def testEnsureThatAutomaticallyCreatedFormsUseTagField(self):
        class TestForm(forms.ModelForm):
            class Meta:
                model = FormTest
        form = TestForm()
        self.assertEqual('TagField', form.fields['tags'].__class__.__name__)

    def testRecreatingStringRepresentaionsOfTagLists(self):
        plain = Tag.objects.create(name='plain')
        spaces = Tag.objects.create(name='spa ces')
        comma = Tag.objects.create(name='com,ma')

        from tagging.utils import edit_string_for_tags
        self.assertEqual(u'plain', edit_string_for_tags([plain]))
        self.assertEqual(u'plain, spa ces', edit_string_for_tags([plain, spaces]))
        self.assertEqual(u'plain, spa ces, "com,ma"', edit_string_for_tags([plain, spaces, comma]))
        self.assertEqual(u'plain "com,ma"', edit_string_for_tags([plain, comma]))
        self.assertEqual(u'"com,ma", spa ces', edit_string_for_tags([comma, spaces]))

    def testFormFields(self):
        from django.forms import ValidationError
        t = TagField()

        self.assertEqual(u'foo', t.clean('foo'))
        self.assertEqual(u'foo bar baz', t.clean('foo bar baz'))
        self.assertEqual(u'foo,bar,baz', t.clean('foo,bar,baz'))
        self.assertEqual(u'foo, bar, baz', t.clean('foo, bar, baz'))
        self.assertEqual(u'foo qwertyuiopasdfghjklzxcvbnmqwertyuiopasdfghjklzxcvb bar',
                         t.clean('foo qwertyuiopasdfghjklzxcvbnmqwertyuiopasdfghjklzxcvb bar'))
        self.assertRaises(ValidationError, t.clean, 'foo qwertyuiopasdfghjklzxcvbnmqwertyuiopasdfghjklzxcvbn bar')

########NEW FILE########
__FILENAME__ = merge
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from tagging.models import Tag, TaggedItem, Synonym
from tagging.utils import merge, get_tag
from tagging.tests.synonym_tests import TestItem, TestItemWithCallback

def with_tag(tag, cls = TestItem):
    return TaggedItem.objects.get_by_model(cls, [tag])

def model_to_ctype(model):
    return ContentType._default_manager.get_for_model(model)

class Merge(TestCase):
    def testMergeTagsDeletesSecondTagIfNoMoreTaggedItems(self):
        self.assertEqual(0, Tag.objects.count())
        self.assertEqual(0, TaggedItem.objects.count())
        self.assertEqual(0, Synonym.objects.count())

        first = TestItem(title = 'first', tags = 'one, two')
        first.save()
        second = TestItem(title = 'second', tags = 'second')
        second.save()

        self.assertEqual(1, len(with_tag('one')))
        self.assertEqual(1, len(with_tag('two')))
        self.assertEqual(1, len(with_tag('second')))

        ctype = model_to_ctype(TestItem)
        merge('two', 'second', ctype)

        self.assertEqual(1, len(with_tag('one')))
        self.assertEqual(2, len(with_tag('two')))
        self.assertRaises(Tag.DoesNotExist, Tag.objects.get, name = 'second')

    def testMergeTagsNotDeletesSecondTag(self):
        self.assertEqual(0, Tag.objects.count())
        self.assertEqual(0, TaggedItem.objects.count())
        self.assertEqual(0, Synonym.objects.count())

        first = TestItem(title = 'first', tags = 'one, two')
        first.save()
        second = TestItem(title = 'second', tags = 'second')
        second.save()
        third = TestItemWithCallback(title = 'third', tags = 'second')
        third.save()

        self.assertEqual(1, len(with_tag('second')))
        self.assertEqual(1, len(with_tag('second', TestItemWithCallback)))

        ctype = model_to_ctype(TestItem)
        merge('two', 'second', ctype)

        self.assertEqual(0, len(with_tag('second')))
        self.assertEqual(1, len(with_tag('second', TestItemWithCallback)))
        self.assert_(Tag.objects.get(name = 'second'))

    def testMergeTagsCreatesSynonyms(self):
        first = TestItem(title = 'first', tags = 'one, two')
        first.save()
        second = TestItem(title = 'second', tags = 'second')
        second.save()

        self.assertEqual([], [s.name for s in get_tag('two').synonyms.all()])

        ctype = model_to_ctype(TestItem)
        merge('two', 'second', ctype)

        self.assertEqual(['second'], [s.name for s in get_tag('two').synonyms.all()])

    def testMergeTagsWhenSynonymAlreadyExists(self):
        first = TestItem(title = 'first', tags = 'one, two, blah')
        first.save()
        second = TestItem(title = 'second', tags = 'second')
        second.save()
        blah = get_tag('blah')
        blah.synonyms.create(name='second')

        self.assertEqual([], [s.name for s in get_tag('two').synonyms.all()])

        ctype = model_to_ctype(TestItem)
        merge('two', 'second', ctype)

        self.assertEqual([], [s.name for s in get_tag('two').synonyms.all()])
        self.assertEqual(['second'], [s.name for s in get_tag('blah').synonyms.all()])


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

########NEW FILE########
__FILENAME__ = multilingual_tests
# -*- coding: utf-8 -*-
from unittest import TestCase
from pdb import set_trace

from django.utils.translation import get_language
from tagging.models import Tag, TaggedItem
from tagging.tests.models import Article, Link, Perch, Parrot, FormTest
from tagging import settings

if settings.MULTILINGUAL_TAGS:
    from multilingual.languages import set_default_language, get_default_language_code, get_language_code
    class MultilingualTests(TestCase):
        def setUp(self):
            super(MultilingualTests, self).setUp()
            Tag.objects.all().delete()

        def testDefaultLanguage(self):
            self.assertEqual('en-us', get_language())

        def testSetTagsForDifferentLanguages(self):
            set_default_language('en')
            self.assertEqual('en', get_default_language_code())

            en_name = u'apple'
            ru_name = u'яблоко'

            t = Tag.objects.create(name = en_name, name_ru = ru_name)
            self.assertEqual(en_name, t.name)
            self.assertEqual(ru_name, t.name_ru)

            set_default_language('ru')
            self.assertEqual(ru_name, t.name)
            self.assertEqual(en_name, t.name_en)

        def testDuplicateCreationRaisesError(self):
            from django.db import IntegrityError
            en_name = u'apple'
            ru_name = u'яблоко'
            Tag.objects.create(name = en_name, name_ru = ru_name)
            self.assertRaises(IntegrityError, Tag.objects.create, name = en_name)
            self.assertRaises(IntegrityError, Tag.objects.create, name_ru = ru_name)
            self.assertRaises(IntegrityError, Tag.objects.create, name = en_name, name_ru = ru_name)


        def testGetOrCreate(self):
            tag_name = u'test'

            tag, created = Tag.objects.get_or_create(name = tag_name)
            self.assertEqual(tag.name, tag_name)
            self.assertEqual(True, created)

            tag, created = Tag.objects.get_or_create(name = tag_name)
            self.assertEqual(tag.name, tag_name)
            self.assertEqual(False, created)

        def testFalbackToDefaultLanguage(self):
            set_default_language(settings.DEFAULT_LANGUAGE)

            default_name = u'apple'

            t = Tag.objects.create(name = default_name)
            self.assertEqual(default_name, t.name)
            self.assertEqual(default_name, t.name_en)
            self.assertEqual(None,         t.name_ru)

            set_default_language('ru')
            t = Tag.objects.get(id = t.id)
            self.assertEqual(default_name, t.name)
            self.assertEqual(default_name, t.name_en)
            self.assertEqual(None,         t.name_ru)


########NEW FILE########
__FILENAME__ = settings
import os
DIRNAME = os.path.dirname(__file__)

DEFAULT_CHARSET = 'utf-8'

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = os.path.join(DIRNAME, 'tagging_test.sqlite')

#DATABASE_ENGINE = 'mysql'
#DATABASE_NAME = 'tagging_test'
#DATABASE_USER = 'root'
#DATABASE_PASSWORD = ''
#DATABASE_HOST = 'localhost'
#DATABASE_PORT = '3306'

#DATABASE_ENGINE = 'postgresql_psycopg2'
#DATABASE_NAME = 'tagging_test'
#DATABASE_USER = 'postgres'
#DATABASE_PASSWORD = ''
#DATABASE_HOST = 'localhost'
#DATABASE_PORT = '5432'

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'tagging',
    'tagging.tests',
)

MULTILINGUAL_TAGS = True
LANGUAGES = (
    ('en', 'English'),
    ('ru', 'Russian'),
)
DEFAULT_LANGUAGE = 1

########NEW FILE########
__FILENAME__ = synonym_tests
# -*- coding: utf-8 -*-
import unittest
import tagging

from pdb import set_trace
from StringIO import StringIO

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import smart_unicode

from tagging.fields import TagField
from tagging.models import Tag, TaggedItem, Synonym
from tagging.utils import replace_synonyms
from multilingual.languages import set_default_language

class TestItem( models.Model ):
    title = models.CharField( _('Title'), max_length = 30)
    tags = TagField()

    def __unicode__(self):
        return self.title

def create_synonyms(tag_name):
    from django.template.defaultfilters import slugify
    return [slugify(tag_name)]

class TestItemWithCallback( models.Model ):
    title = models.CharField( _('Title'), max_length = 30)
    tags = TagField(create_synonyms = create_synonyms)

    def __unicode__(self):
        return self.title

class TaggingTestCase(unittest.TestCase):
    def setUp(self):
        TestItem.objects.all().delete()
        Tag.objects.all().delete()
        TaggedItem.objects.all().delete()
        Synonym.objects.all().delete()

        self.first = TestItem(title = 'first')
        self.second = TestItem(title = 'second')
        self.third = TestItem(title = 'third')
        self.four = TestItem(title = 'four')

    def saveAll(self):
        self.first.save()
        self.second.save()
        self.third.save()
        self.four.save()

    def testJoining(self):
        self.first.tags = 'hello, world'
        self.second.tags = 'aloha'
        self.third.tags = 'bla'
        self.saveAll()

        # renaming
        aloha = Tag.objects.get(name = 'aloha')
        hello = Tag.objects.get(name = 'hello')
        Tag.objects.join([aloha, hello])

        all_tags = Tag.objects.all()
        self.assertEquals(3, len(all_tags))

        self.assertEquals(0, len(Tag.objects.filter(name = 'hello')))
        self.assertEquals(1, len(Tag.objects.filter(name = 'world')))
        self.assertEquals(1, len(Tag.objects.filter(name = 'bla')))

        tags = Tag.objects.filter(name = 'aloha')
        self.assertEquals(1, len(tags))
        objs = TaggedItem.objects.get_by_model(TestItem, tags)

        self.assertEquals(2, len(objs))
        self.assertTrue(self.first in objs)
        self.assertTrue(self.second in objs)

    def testJoiningMultiple(self):
        self.first.tags = 'hello, world'
        self.second.tags = 'aloha'
        self.third.tags = 'bla'
        self.saveAll()

        # renaming
        aloha = Tag.objects.get(name = 'aloha')
        hello = Tag.objects.get(name = 'hello')
        bla   = Tag.objects.get(name = 'bla')
        Tag.objects.join([aloha, hello, bla])

        all_tags = Tag.objects.all()
        self.assertEquals(2, len(all_tags))

        self.assertEquals(0, len(Tag.objects.filter(name = 'hello')))
        self.assertEquals(0, len(Tag.objects.filter(name = 'bla')))
        self.assertEquals(1, len(Tag.objects.filter(name = 'world')))
        self.assertEquals(1, len(Tag.objects.filter(name = 'aloha')))

        tags = Tag.objects.filter(name = 'aloha')
        self.assertEquals(1, len(tags))
        objs = TaggedItem.objects.get_by_model(TestItem, tags)

        self.assertEquals(3, len(objs))
        self.assertTrue(self.first in objs)
        self.assertTrue(self.second in objs)
        self.assertTrue(self.third in objs)

    def testJoiningTagsFromOneObject(self):
        self.first.tags = 'fruit, apple'
        self.saveAll()

        # renaming
        Tag.objects.join(\
                Tag.objects.filter(name__in = ('fruit', 'apple')))

        all_tags = Tag.objects.all()
        self.assertEquals(1, len(all_tags))

        self.assertEquals(1, len(Tag.objects.filter(name = 'apple')))
        self.assertEquals(0, len(Tag.objects.filter(name = 'fruit')))

    def testJoinUsingTextFormat(self):
        self.first.tags = 'hello, world'
        self.second.tags = 'aloha'
        self.third.tags = 'bla'
        self.saveAll()

        # renaming
        Tag.objects.process_rules(' first-non-existent = hello = aloha = second-non-existent = bla = non-existed')

        all_tags = Tag.objects.all()
        self.assertEquals(2, len(all_tags))

        self.assertEquals(1, len(Tag.objects.filter(name = 'hello')))
        self.assertEquals(1, len(Tag.objects.filter(name = 'world')))

        tags = Tag.objects.filter(name = 'hello')
        self.assertEquals(1, len(tags))
        objs = TaggedItem.objects.get_by_model(TestItem, tags)

        self.assertEquals(3, len(objs))
        self.assertTrue(self.first in objs)
        self.assertTrue(self.second in objs)
        self.assertTrue(self.third in objs)

    def testRenameUsingTextFormat(self):
        self.first.tags = 'hello-world'
        self.saveAll()

        Tag.objects.process_rules( \
                u'''hello-world: hello; ru: Привет;
                    hello; en: Hello;
                    non-existent: normal''')

        tag = Tag.objects.get(name='Hello')
        self.assertEquals(u'Привет', tag.name_ru)
        self.assertEquals(u'Hello', tag.name_en)

    def testDumpTagsAsText(self):
        set_default_language('en')

        hello = Tag.objects.create(name='hello')
        syn = Synonym.objects.create(name='aloha', tag=hello)

        self.first.tags = 'hello, world'
        self.second.tags = 'aloha'
        self.saveAll()

        self.assertEquals( \
u'''hello == aloha
hello; en: hello
world; en: world''', Tag.objects.dumpAsText())

        hello.name_ru = u'Привет'
        hello.name_en = u'Hello'
        hello.save()

        self.assertEquals( \
u'''Hello == aloha
Hello; en: Hello; ru: Привет
world; en: world''', Tag.objects.dumpAsText())

    def testTagRenameChangesObjectsProperties(self):
        self.first.tags = 'hello, world'
        self.saveAll()

        hello = Tag.objects.get(name='hello')
        hello.name = u'Привет'
        hello.save()

        self.first = TestItem.objects.get(id=self.first.id)
        self.assertEquals(u'world Привет', self.first.tags)

    def testTagJoinChangesObjectsProperties(self):
        self.first.tags = 'hello, world'
        self.saveAll()

        Tag.objects.join( \
                Tag.objects.filter(name__in = ('hello', 'world')))

        self.first = TestItem.objects.get(id=self.first.id)
        self.assertEquals('hello', self.first.tags)

    def testTagRemoveChangesObjectsProperties(self):
        self.first.tags = 'hello, world'
        self.saveAll()

        Tag.objects.get(name = 'world').delete()

        self.first = TestItem.objects.get(id=self.first.id)
        self.assertEquals('hello', self.first.tags)

    def testTagSynonym(self):
        tag = Tag.objects.create(name='hello')
        syn = Synonym.objects.create(name='aloha', tag=tag)

        self.first.tags = 'aloha, world'
        self.saveAll()

        self.first = TestItem.objects.get(id=self.first.id)
        self.assertEquals('hello world', self.first.tags)

    def testCreatingSynonymUsingTextFormat(self):
        self.first.tags = 'hello, world'
        self.second.tags = 'aloha'
        self.saveAll()

        # renaming
        self.assertEquals(3, Tag.objects.count())
        Tag.objects.process_rules('hello == aloha == privet')
        self.assertEquals(2, Tag.objects.count())

        self.assertEquals(1, len(Tag.objects.filter(name = 'hello')))
        self.assertEquals(1, len(Tag.objects.filter(name = 'world')))

        hello = Tag.objects.get(name = 'hello')
        self.assertEquals(2, len(hello.synonyms.all()))
        self.assertTrue('aloha', hello.synonyms.all()[0].name)
        self.assertTrue('privet', hello.synonyms.all()[1].name)

        objs = TaggedItem.objects.get_by_model(TestItem, [hello,])

        self.assertEquals(2, len(objs))
        self.assertTrue(self.first in objs)
        self.assertTrue(self.second in objs)

    def testExistingSynonymsAreIgnored(self):
        self.first.tags = 'hello, world'
        self.saveAll()
        Tag.objects.process_rules('hello == aloha == privet')
        self.assert_(Tag.objects.process_rules('hello == aloha == privet'))

    def testReplaceSynonyms(self):
        tag = Tag.objects.create(name='hello')
        Synonym.objects.create(name='aloha', tag=tag)
        self.assertEquals(['hello', 'world'], replace_synonyms(['aloha', 'world']))

    def testCreateSynonymUsingFieldCallback(self):
        tag = Tag.objects.create(name='hello')
        Synonym.objects.create(name='aloha', tag=tag)
        self.assertEquals(['hello', 'world'], replace_synonyms(['aloha', 'world']))

        Synonym.objects.all().delete()
        self.assertEqual(0, len(Synonym.objects.all()))
        test_item = TestItemWithCallback(title='Test callbacks', tags='Test, Create Callbacks')
        test_item.save()
        second_item = TestItemWithCallback(title='Another test', tags='Test')
        second_item.save()

        synonyms = Synonym.objects.all()
        self.assertEqual(2, len(synonyms))
        self.assertEqual('create-callbacks', synonyms[0].name)
        self.assertEqual('test', synonyms[1].name)

        objs = TaggedItem.objects.get_by_model(TestItemWithCallback, ['create-callbacks'])
        self.assertEqual(1, len(objs))
        self.assertEqual('Test callbacks', objs[0].title)


########NEW FILE########
__FILENAME__ = tests
from tagging.tests.core_tests import *
from tagging.tests.multilingual_tests import *
from tagging.tests.synonym_tests import *
from tagging.tests.merge import *

########NEW FILE########
__FILENAME__ = utils
"""
Tagging utilities - from user tag input parsing to tag cloud
calculation.
"""
import logging
import math
import types

from django.db import IntegrityError
from django.db.models.query import QuerySet
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext as _

from tagging import settings

# Python 2.3 compatibility
try:
    set
except NameError:
    from sets import Set as set

def replace_synonyms(tag_list):
    """In given tag list, search synonyms and replace them with original names."""
    from tagging.models import Synonym

    def search_synonym(name):
        syn = Synonym.objects.filter(name=name).all()
        return len(syn)==1 and syn[0].tag.name or name

    words = list(set(search_synonym(tag) for tag in tag_list))
    words.sort()
    return words

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
        return replace_synonyms(split_strip(input, u' '))

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
    return replace_synonyms(words)

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
        name = getattr(tag, 'name', tag)
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
    if settings.FORCE_TAG_DELIMITER is not None:
        glue = settings.FORCE_TAG_DELIMITER
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
                tags = replace_synonyms(tags)
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



def merge(to_tag, from_tag, ctype = None):
    """ Merge items with given tags together.
        If there are no any items with tag 'from_tag' and
        other content types, then 'from_tag' becomes a synonym for 'to_tag'.
    """
    logger = logging.getLogger('tagging.utils')

    to_tag = get_tag(to_tag)
    from_tag = get_tag(from_tag)
    logger.debug('merging tag "%s" to tag "%s"' % (from_tag.name, to_tag.name))

    from_items = from_tag.items.all()
    if ctype is not None:
        from_items = from_items.filter(content_type = ctype)

    to_items = to_tag.items.all()

    if ctype is not None:
        to_items = to_items.filter(content_type = ctype)

    to_obj_ids = [item.object_id for item in to_items]

    for item in from_items:
        if item.object_id in to_obj_ids:
            logger.debug('item "%s" already binded to tag "%s"' % (item, to_tag))
            item.delete(update = False)
        else:
            item.tag = to_tag
            item.save()
            logger.debug('item "%s" merged' % item)

        _update_objects_tags(item.object)

    if from_tag.items.count() == 0:
        from_tag.delete()
        try:
            to_tag.synonyms.create(name = from_tag.name)
        except IntegrityError:
            pass


def _update_objects_tags(object):
    """ Updates TagField's value in given object.
    """
    from tagging.models import Tag
    from tagging.fields import TagField

    if object is None:
        return

    object_tags = (tag.name or tag.name_any for tag in Tag.objects.get_for_object(object))
    tags_as_string = edit_string_for_tags(object_tags)

    for field in object._meta.fields:
        if isinstance(field, TagField):
            setattr(object, field.attname, tags_as_string)
            object.save()
            break


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
