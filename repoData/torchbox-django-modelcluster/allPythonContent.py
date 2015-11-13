__FILENAME__ = fields
from __future__ import unicode_literals

from django.db import models, IntegrityError, router
from django.db.models.fields.related import ForeignKey, ForeignRelatedObjectsDescriptor
from django.utils.functional import cached_property

try:
    from south.modelsinspector import add_introspection_rules
except ImportError:
    # south is not in use, so make add_introspection_rules a no-op
    def add_introspection_rules(*args):
        pass

from modelcluster.queryset import FakeQuerySet


def create_deferring_foreign_related_manager(related, original_manager_cls):
    """
    Create a DeferringRelatedManager class that wraps an ordinary RelatedManager
    with 'deferring' behaviour: any updates to the object set (via e.g. add() or clear())
    are written to a holding area rather than committed to the database immediately.
    Writing to the database is deferred until the model is saved.
    """

    relation_name = related.get_accessor_name()
    rel_field = related.field
    superclass = related.model._default_manager.__class__
    rel_model = related.model

    class DeferringRelatedManager(superclass):
        def __init__(self, instance):
            super(DeferringRelatedManager, self).__init__()
            self.model = rel_model
            self.instance = instance

        def get_live_query_set(self):
            """
            return the original manager's queryset, which reflects the live database
            """
            return original_manager_cls(self.instance).get_query_set()

        def get_query_set(self):
            """
            return the current object set with any updates applied,
            wrapped up in a FakeQuerySet if it doesn't match the database state
            """
            try:
                results = self.instance._cluster_related_objects[relation_name]
            except (AttributeError, KeyError):
                return self.get_live_query_set()

            return FakeQuerySet(related.model, results)

        def get_prefetch_queryset(self, instances):
            rel_obj_attr = rel_field.get_local_related_value
            instance_attr = rel_field.get_foreign_related_value
            instances_dict = dict((instance_attr(inst), inst) for inst in instances)
            db = self._db or router.db_for_read(self.model, instance=instances[0])
            query = {'%s__in' % rel_field.name: instances}
            qs = super(DeferringRelatedManager, self).get_queryset().using(db).filter(**query)
            # Since we just bypassed this class' get_queryset(), we must manage
            # the reverse relation manually.
            for rel_obj in qs:
                instance = instances_dict[rel_obj_attr(rel_obj)]
                setattr(rel_obj, rel_field.name, instance)
            cache_name = rel_field.related_query_name()
            return qs, rel_obj_attr, instance_attr, False, cache_name

        def get_object_list(self):
            """
            return the mutable list that forms the current in-memory state of
            this relation. If there is no such list (i.e. the manager is returning
            querysets from the live database instead), one is created, populating it
            with the live database state
            """
            try:
                cluster_related_objects = self.instance._cluster_related_objects
            except AttributeError:
                cluster_related_objects = {}
                self.instance._cluster_related_objects = cluster_related_objects

            try:
                object_list = cluster_related_objects[relation_name]
            except KeyError:
                object_list = list(self.get_live_query_set())
                cluster_related_objects[relation_name] = object_list

            return object_list


        def add(self, *new_items):
            """
            Add the passed items to the stored object set, but do not commit them
            to the database
            """
            items = self.get_object_list()

            # Rule for checking whether an item in the list matches one of our targets.
            # We can't do this with a simple 'in' check due to https://code.djangoproject.com/ticket/18864 -
            # instead, we consider them to match IF:
            # - they are exactly the same Python object (by reference), or
            # - they have a non-null primary key that matches
            items_match = lambda item, target: (item is target) or (item.pk == target.pk and item.pk is not None)

            for target in new_items:
                item_matched = False
                for i, item in enumerate(items):
                    if items_match(item, target):
                        # Replace the matched item with the new one. This ensures that any
                        # modifications to that item's fields take effect within the recordset -
                        # i.e. we can perform a virtual UPDATE to an object in the list
                        # by calling add(updated_object). Which is semantically a bit dubious,
                        # but it does the job...
                        items[i] = target
                        item_matched = True
                        break
                if not item_matched:
                    items.append(target)

                # update the foreign key on the added item to point back to the parent instance
                setattr(target, related.field.name, self.instance)

        def remove(self, *items_to_remove):
            """
            Remove the passed items from the stored object set, but do not commit the change
            to the database
            """
            items = self.get_object_list()

            # Rule for checking whether an item in the list matches one of our targets.
            # We can't do this with a simple 'in' check due to https://code.djangoproject.com/ticket/18864 -
            # instead, we consider them to match IF:
            # - they are exactly the same Python object (by reference), or
            # - they have a non-null primary key that matches
            items_match = lambda item, target: (item is target) or (item.pk == target.pk and item.pk is not None)

            for target in items_to_remove:
                # filter items list in place: see http://stackoverflow.com/a/1208792/1853523
                items[:] = [item for item in items if not items_match(item, target)]

        def create(self, **kwargs):
            items = self.get_object_list()
            new_item = related.model(**kwargs)
            items.append(new_item)
            return new_item

        def clear(self):
            """
            Clear the stored object set, without affecting the database
            """
            try:
                cluster_related_objects = self.instance._cluster_related_objects
            except AttributeError:
                cluster_related_objects = {}
                self.instance._cluster_related_objects = cluster_related_objects

            cluster_related_objects[relation_name] = []

        def commit(self):
            """
            Apply any changes made to the stored object set to the database.
            Any objects removed from the initial set will be deleted entirely
            from the database.
            """
            if not self.instance.pk:
                raise IntegrityError("Cannot commit relation %r on an unsaved model" % relation_name)

            try:
                final_items = self.instance._cluster_related_objects[relation_name]
            except (AttributeError, KeyError):
                # _cluster_related_objects entry never created => no changes to make
                return

            original_manager = original_manager_cls(self.instance)

            live_items = list(original_manager.get_query_set())
            for item in live_items:
                if item not in final_items:
                    item.delete()

            for item in final_items:
                original_manager.add(item)

            # purge the _cluster_related_objects entry, so we switch back to live SQL
            del self.instance._cluster_related_objects[relation_name]

    return DeferringRelatedManager


class ChildObjectsDescriptor(ForeignRelatedObjectsDescriptor):
    def __init__(self, related):
        super(ChildObjectsDescriptor, self).__init__(related)

    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self

        return self.child_object_manager_cls(instance)

    def __set__(self, instance, value):
        manager = self.__get__(instance)
        manager.clear()
        manager.add(*value)

    @cached_property
    def child_object_manager_cls(self):
        return create_deferring_foreign_related_manager(self.related, self.related_manager_cls)


class ParentalKey(ForeignKey):
    related_accessor_class = ChildObjectsDescriptor

    # prior to https://github.com/django/django/commit/fa2e1371cda1e72d82b4133ad0b49a18e43ba411
    # ForeignRelatedObjectsDescriptor is hard-coded in contribute_to_related_class -
    # so we need to patch in that change to look up related_accessor_class instead
    def contribute_to_related_class(self, cls, related):
        # Internal FK's - i.e., those with a related name ending with '+' -
        # and swapped models don't get a related descriptor.
        if not self.rel.is_hidden() and not related.model._meta.swapped:
            setattr(cls, related.get_accessor_name(), self.related_accessor_class(related))
            if self.rel.limit_choices_to:
                cls._meta.related_fkey_lookups.append(self.rel.limit_choices_to)
        if self.rel.field_name is None:
            self.rel.field_name = cls._meta.pk.name

        # store this as a child field in meta
        try:
            # TODO: figure out how model inheritance works with this
            cls._meta.child_relations.append(related)
        except AttributeError:
            cls._meta.child_relations = [related]

add_introspection_rules([], ["^modelcluster\.fields\.ParentalKey"])

########NEW FILE########
__FILENAME__ = forms
from __future__ import unicode_literals

from six import add_metaclass

from django.forms.models import (
    BaseModelFormSet, modelformset_factory,
    ModelForm, _get_foreign_key, ModelFormMetaclass, ModelFormOptions
)
from django.db.models.fields.related import RelatedObject


class BaseTransientModelFormSet(BaseModelFormSet):
    """ A ModelFormSet that doesn't assume that all its initial data instances exist in the db """
    def _construct_form(self, i, **kwargs):
        if self.is_bound and i < self.initial_form_count():
            pk_name = self.model._meta.pk.name
            pk_key = "%s-%s" % (self.add_prefix(i), pk_name)
            pk_val = self.data[pk_key]
            if pk_val:
                kwargs['instance'] = self.queryset.get(**{pk_name: pk_val})
            else:
                kwargs['instance'] = self.model()
        elif i < self.initial_form_count():
            kwargs['instance'] = self.get_queryset()[i]
        elif self.initial_extra:
            # Set initial values for extra forms
            try:
                kwargs['initial'] = self.initial_extra[i-self.initial_form_count()]
            except IndexError:
                pass

        # bypass BaseModelFormSet's own _construct_form
        return super(BaseModelFormSet, self)._construct_form(i, **kwargs)

def transientmodelformset_factory(model, formset=BaseTransientModelFormSet, **kwargs):
    return modelformset_factory(model, formset=formset, **kwargs)


class BaseChildFormSet(BaseTransientModelFormSet):
    def __init__(self, data=None, files=None, instance=None, queryset=None, **kwargs):
        if instance is None:
            self.instance = self.fk.rel.to()
        else:
            self.instance=instance

        self.rel_name = RelatedObject(self.fk.rel.to, self.model, self.fk).get_accessor_name()

        if queryset is None:
            queryset = getattr(self.instance, self.rel_name).all()

        super(BaseChildFormSet, self).__init__(data, files, queryset=queryset, **kwargs)

    def save(self, commit=True):
        # The base ModelFormSet's save(commit=False) will populate the lists
        # self.changed_objects, self.deleted_objects and self.new_objects;
        # use these to perform the appropriate updates on the relation's manager.
        saved_instances = super(BaseChildFormSet, self).save(commit=False)

        manager = getattr(self.instance, self.rel_name)

        # If the manager has existing instances with a blank ID, we have no way of knowing
        # whether these correspond to items in the submitted data. We'll assume that they do,
        # as that's the most common case (i.e. the formset contains the full set of child objects,
        # not just a selection of additions / updates) and so we delete all ID-less objects here
        # on the basis that they will be re-added by the formset saving mechanism.
        no_id_instances = [obj for obj in manager.all() if obj.pk is None]
        if no_id_instances:
            manager.remove(*no_id_instances)

        manager.add(*saved_instances)
        manager.remove(*self.deleted_objects)

        # if model has a sort_order_field defined, assign order indexes to the attribute
        # named in it
        if self.can_order and hasattr(self.model, 'sort_order_field'):
            sort_order_field = getattr(self.model, 'sort_order_field')
            for i, form in enumerate(self.ordered_forms):
                setattr(form.instance, sort_order_field, i)

        if commit:
            manager.commit()

        return saved_instances

    # Prior to Django 1.7, objects are deleted from the database even when commit=False:
    # https://code.djangoproject.com/ticket/10284
    # This was fixed in https://github.com/django/django/commit/65e03a424e82e157b4513cdebb500891f5c78363
    # We rely on the fixed behaviour here, so until 1.7 ships we need to override save_existing_objects
    # with a patched version.
    def save_existing_objects(self, commit=True):
        self.changed_objects = []
        self.deleted_objects = []
        if not self.initial_forms:
            return []

        saved_instances = []
        try:
            forms_to_delete = self.deleted_forms
        except AttributeError:
            forms_to_delete = []
        for form in self.initial_forms:
            pk_name = self._pk_field.name
            raw_pk_value = form._raw_value(pk_name)

            # clean() for different types of PK fields can sometimes return
            # the model instance, and sometimes the PK. Handle either.
            pk_value = form.fields[pk_name].clean(raw_pk_value)
            pk_value = getattr(pk_value, 'pk', pk_value)

            obj = self._existing_object(pk_value)
            if form in forms_to_delete:
                self.deleted_objects.append(obj)
                # === BEGIN PATCH ===
                if commit:
                    obj.delete()
                # === END PATCH ===
                continue
            if form.has_changed():
                self.changed_objects.append((obj, form.changed_data))
                saved_instances.append(self.save_existing(form, obj, commit=commit))
                if not commit:
                    self.saved_forms.append(form)
        return saved_instances

def childformset_factory(parent_model, model, form=ModelForm,
    formset=BaseChildFormSet, fk_name=None, fields=None, exclude=None,
    extra=3, can_order=False, can_delete=True, max_num=None,
    formfield_callback=None):

    fk = _get_foreign_key(parent_model, model, fk_name=fk_name)
    # enforce a max_num=1 when the foreign key to the parent model is unique.
    if fk.unique:
        max_num = 1

    if exclude is None:
        exclude = []
    exclude += [fk.name]

    kwargs = {
        'form': form,
        'formfield_callback': formfield_callback,
        'formset': formset,
        'extra': extra,
        'can_delete': can_delete,
        # if the model supplies a sort_order_field, enable ordering regardless of
        # the current setting of can_order
        'can_order': (can_order or hasattr(model, 'sort_order_field')),
        'fields': fields,
        'exclude': exclude,
        'max_num': max_num,
    }
    FormSet = transientmodelformset_factory(model, **kwargs)
    FormSet.fk = fk
    return FormSet


class ClusterFormOptions(ModelFormOptions):
    def __init__(self, options=None):
        super(ClusterFormOptions, self).__init__(options=options)
        self.formsets = getattr(options, 'formsets', None)
        self.exclude_formsets = getattr(options, 'exclude_formsets', None)

class ClusterFormMetaclass(ModelFormMetaclass):
    extra_form_count = 3

    def __new__(cls, name, bases, attrs):
        try:
            parents = [b for b in bases if issubclass(b, ClusterForm)]
        except NameError:
            # We are defining ClusterForm itself.
            parents = None

        # grab any formfield_callback that happens to be defined in attrs -
        # so that we can pass it on to child formsets - before ModelFormMetaclass deletes it.
        # BAD METACLASS NO BISCUIT.
        formfield_callback = attrs.get('formfield_callback')

        new_class = super(ClusterFormMetaclass, cls).__new__(cls, name, bases, attrs)
        if not parents:
            return new_class

        # ModelFormMetaclass will have set up new_class._meta as a ModelFormOptions instance;
        # replace that with ClusterFormOptions so that we can access _meta.formsets
        opts = new_class._meta = ClusterFormOptions(getattr(new_class, 'Meta', None))
        if opts.model:
            try:
                child_relations = opts.model._meta.child_relations
            except AttributeError:
                child_relations = []

            formsets = {}
            for rel in child_relations:
                # to build a childformset class from this relation, we need to specify:
                # - the base model (opts.model)
                # - the child model (rel.model)
                # - the fk_name from the child model to the base (rel.field.name)
                # Additionally, to specify widgets, we need to construct a custom ModelForm subclass.
                # (As of Django 1.6, modelformset_factory can be passed a widgets kwarg directly,
                # and it would make sense for childformset_factory to support that as well)

                rel_name = rel.get_accessor_name()

                # apply 'formsets' and 'exclude_formsets' rules from meta
                if opts.formsets is not None and rel_name not in opts.formsets:
                    continue
                if opts.exclude_formsets and rel_name in opts.exclude_formsets:
                    continue

                try:
                    subform_widgets = opts.widgets.get(rel_name)
                except AttributeError:  # thrown if opts.widgets is None
                    subform_widgets = None

                if subform_widgets:
                    class CustomModelForm(ModelForm):
                        class Meta:
                            widgets = subform_widgets
                    form_class = CustomModelForm
                else:
                    form_class = ModelForm

                formset = childformset_factory(opts.model, rel.model,
                    extra=cls.extra_form_count,
                    form=form_class, formfield_callback=formfield_callback, fk_name=rel.field.name)
                formsets[rel_name] = formset

            new_class.formsets = formsets

        return new_class


@add_metaclass(ClusterFormMetaclass)
class ClusterForm(ModelForm):
    def __init__(self, data=None, files=None, instance=None, prefix=None, **kwargs):
        super(ClusterForm, self).__init__(data, files, instance=instance, prefix=prefix, **kwargs)

        self.formsets = {}
        for rel_name, formset_class in self.__class__.formsets.items():
            if prefix:
                formset_prefix = "%s-%s" % (prefix, rel_name)
            else:
                formset_prefix = rel_name
            self.formsets[rel_name] = formset_class(data, files, instance=instance, prefix=formset_prefix)

    def as_p(self):
        form_as_p = super(ClusterForm, self).as_p()
        return form_as_p + ''.join([formset.as_p() for formset in self.formsets.values()])

    def is_valid(self):
        form_is_valid = super(ClusterForm, self).is_valid()
        formsets_are_valid = all([formset.is_valid() for formset in self.formsets.values()])
        return form_is_valid and formsets_are_valid

    def save(self, commit=True):
        instance = super(ClusterForm, self).save(commit=commit)

        # ensure save_m2m is called even if commit = false. We don't fully support m2m fields yet,
        # but if they perform save_form_data in a way that happens to play well with ClusterableModel
        # (as taggit's manager does), we want that to take effect immediately, not just on db save
        if not commit:
            self.save_m2m()

        for formset in self.formsets.values():
            formset.instance = instance
            formset.save(commit=commit)
        return instance

########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals

from django.db import models
from django.db.models.fields import FieldDoesNotExist
from django.utils.encoding import is_protected_type
from django.core.serializers.json import DjangoJSONEncoder

import json


def get_field_value(field, model):
    if field.rel is None:
        value = field._get_val_from_obj(model)
        if is_protected_type(value):
            return value
        else:
            return field.value_to_string(model)
    else:
        return getattr(model, field.get_attname())

def get_serializable_data_for_fields(model):
    pk_field = model._meta.pk
    # If model is a child via multitable inheritance, use parent's pk
    while pk_field.rel and pk_field.rel.parent_link:
        pk_field = pk_field.rel.to._meta.pk

    obj = {'pk': get_field_value(pk_field, model)}

    for field in model._meta.fields:
        if field.serialize:
            obj[field.name] = get_field_value(field, model)

    return obj

def model_from_serializable_data(model, data, check_fks=True, strict_fks=False):
    pk_field = model._meta.pk
    # If model is a child via multitable inheritance, use parent's pk
    while pk_field.rel and pk_field.rel.parent_link:
        pk_field = pk_field.rel.to._meta.pk

    kwargs = {pk_field.attname: data['pk']}
    for field_name, field_value in data.items():
        try:
            field = model._meta.get_field(field_name)
        except FieldDoesNotExist:
            continue

        if field.rel and isinstance(field.rel, models.ManyToManyRel):
            raise Exception('m2m relations not supported yet')
        elif field.rel and isinstance(field.rel, models.ManyToOneRel):
            if field_value is None:
                kwargs[field.attname] = None
            else:
                clean_value = field.rel.to._meta.get_field(field.rel.field_name).to_python(field_value)
                kwargs[field.attname] = clean_value
                if check_fks:
                    try:
                        field.rel.to._default_manager.get(**{field.rel.field_name: clean_value})
                    except field.rel.to.DoesNotExist:
                        if field.rel.on_delete == models.DO_NOTHING:
                            pass
                        elif field.rel.on_delete == models.CASCADE:
                            if strict_fks:
                                return None
                            else:
                                kwargs[field.attname] = None

                        elif field.rel.on_delete == models.SET_NULL:
                            kwargs[field.attname] = None

                        else:
                            raise Exception("can't currently handle on_delete types other than CASCADE, SET_NULL and DO_NOTHING")
        else:
            kwargs[field.name] = field.to_python(field_value)

    obj = model(**kwargs)

    if data['pk'] is not None:
        # Set state to indicate that this object has come from the database, so that
        # ModelForm validation doesn't try to enforce a uniqueness check on the primary key
        obj._state.adding = False

    return obj


class ClusterableModel(models.Model):
    def __init__(self, *args, **kwargs):
        """
        Extend the standard model constructor to allow child object lists to be passed in
        via kwargs
        """
        try:
            child_relation_names = [rel.get_accessor_name() for rel in self._meta.child_relations]
        except AttributeError:
            child_relation_names = []

        is_passing_child_relations = False
        for rel_name in child_relation_names:
            if rel_name in kwargs:
                is_passing_child_relations = True
                break

        if is_passing_child_relations:
            kwargs_for_super = kwargs.copy()
            relation_assignments = {}
            for rel_name in child_relation_names:
                if rel_name in kwargs:
                    relation_assignments[rel_name] = kwargs_for_super.pop(rel_name)

            super(ClusterableModel, self).__init__(*args, **kwargs_for_super)
            for (field_name, related_instances) in relation_assignments.items():
                setattr(self, field_name, related_instances)
        else:
            super(ClusterableModel, self).__init__(*args, **kwargs)

    def save(self, **kwargs):
        """
        Save the model and commit all child relations.
        """
        try:
            child_relation_names = [rel.get_accessor_name() for rel in self._meta.child_relations]
        except AttributeError:
            child_relation_names = []

        update_fields = kwargs.pop('update_fields', None)
        if update_fields is None:
            real_update_fields = None
            relations_to_commit = child_relation_names
        else:
            real_update_fields = []
            relations_to_commit = []
            for field in update_fields:
                if field in child_relation_names:
                    relations_to_commit.append(field)
                else:
                    real_update_fields.append(field)

        super(ClusterableModel, self).save(update_fields=real_update_fields, **kwargs)

        for relation in relations_to_commit:
            getattr(self, relation).commit()

    def serializable_data(self):
        obj = get_serializable_data_for_fields(self)

        try:
            child_relations = self._meta.child_relations
        except AttributeError:
            child_relations = []

        for rel in child_relations:
            rel_name = rel.get_accessor_name()
            children = getattr(self, rel_name).all()

            if hasattr(rel.model, 'serializable_data'):
                obj[rel_name] = [child.serializable_data() for child in children]
            else:
                obj[rel_name] = [get_serializable_data_for_fields(child) for child in children]

        return obj

    def to_json(self):
        return json.dumps(self.serializable_data(), cls=DjangoJSONEncoder)

    @classmethod
    def from_serializable_data(cls, data, check_fks=True, strict_fks=False):
        """
        Build an instance of this model from the JSON-like structure passed in,
        recursing into related objects as required.
        If check_fks is true, it will check whether referenced foreign keys still
        exist in the database.
        - dangling foreign keys on related objects are dealt with by either nullifying the key or
        dropping the related object, according to the 'on_delete' setting.
        - dangling foreign keys on the base object will be nullified, unless strict_fks is true,
        in which case any dangling foreign keys with on_delete=CASCADE will cause None to be
        returned for the entire object.
        """
        obj = model_from_serializable_data(cls, data, check_fks=check_fks, strict_fks=strict_fks)
        if obj is None:
            return None

        try:
            child_relations = cls._meta.child_relations
        except AttributeError:
            child_relations = []

        for rel in child_relations:
            rel_name = rel.get_accessor_name()
            try:
                child_data_list = data[rel_name]
            except KeyError:
                continue

            if hasattr(rel.model, 'from_serializable_data'):
                children = [
                    rel.model.from_serializable_data(child_data, check_fks=check_fks, strict_fks=True)
                    for child_data in child_data_list
                ]
            else:
                children = [
                    model_from_serializable_data(rel.model, child_data, check_fks=check_fks, strict_fks=True)
                    for child_data in child_data_list
                ]

            children = filter(lambda child: child is not None, children)

            setattr(obj, rel_name, children)

        return obj

    @classmethod
    def from_json(cls, json_data, check_fks=True, strict_fks=False):
        return cls.from_serializable_data(json.loads(json_data), check_fks=check_fks, strict_fks=strict_fks)

    class Meta:
        abstract = True

########NEW FILE########
__FILENAME__ = queryset
from __future__ import unicode_literals

from django.db.models import Model

# Constructor for test functions that determine whether an object passes some boolean condition
def test_exact(model, attribute_name, value):
    field = model._meta.get_field(attribute_name)
    # convert value to the correct python type for this field
    typed_value = field.to_python(value)
    if isinstance(typed_value, Model):
        if typed_value.pk is None:
            # comparing against an unsaved model, so objects need to match by reference
            return lambda obj: getattr(obj, attribute_name) is typed_value
        else:
            # comparing against a saved model; objects need to match by type and ID.
            # Additionally, where model inheritance is involved, we need to treat it as a
            # positive match if one is a subclass of the other
            def _test(obj):
                other_value = getattr(obj, attribute_name)
                if not (isinstance(typed_value, other_value.__class__) or isinstance(other_value, typed_value.__class__)):
                    return False
                return typed_value.pk == other_value.pk
            return _test
    else:
        # just a plain Python value = do a normal equality check
        return lambda obj: getattr(obj, attribute_name) == typed_value

class FakeQuerySet(object):
    def __init__(self, model, results):
        self.model = model
        self.results = results

    def all(self):
        return self

    def filter(self, **kwargs):
        filters = []  # a list of test functions; objects must pass all tests to be included
            # in the filtered list
        for key, val in kwargs.items():
            key_clauses = key.split('__')
            if len(key_clauses) != 1:
                raise NotImplementedError("Complex filters with double-underscore clauses are not implemented yet")

            filters.append(test_exact(self.model, key_clauses[0], val))

        filtered_results = [
            obj for obj in self.results
            if all([test(obj) for test in filters])
        ]

        return FakeQuerySet(self.model, filtered_results)

    def get(self, **kwargs):
        results = self.filter(**kwargs)
        result_count = results.count()

        if result_count == 0:
            raise self.model.DoesNotExist("%s matching query does not exist." % self.model._meta.object_name)
        elif result_count == 1:
            return results[0]
        else:
            raise self.model.MultipleObjectsReturned(
                "get() returned more than one %s -- it returned %s!" % (self.model._meta.object_name, result_count)
            )

    def count(self):
        return len(self.results)

    def select_related(self, *args):
        # has no meaningful effect on non-db querysets
        return self

    def values_list(self, *fields, **kwargs):
        # FIXME: values_list should return an object that behaves like both a queryset and a list,
        # so that we can do things like Foo.objects.values_list('id').order_by('id')

        flat = kwargs.get('flat')  # TODO: throw TypeError if other kwargs are present

        if not fields:
            # return a tuple of all fields
            field_names = [field.name for field in self.model._meta.fields]
            return [
                tuple([getattr(obj, field_name) for field_name in field_names])
                for obj in self.results
            ]

        if flat:
            if len(fields) > 1:
                raise TypeError("'flat' is not valid when values_list is called with more than one field.")
            field_name = fields[0]
            return [getattr(obj, field_name) for obj in self.results]
        else:
            return [
                tuple([getattr(obj, field_name) for field_name in fields])
                for obj in self.results
            ]

    def __getitem__(self, k):
        return self.results[k]

    def __iter__(self):
        return self.results.__iter__()

    def __nonzero__(self):
        return bool(self.results)

    def __repr__(self):
        return repr(list(self))

    def __len__(self):
        return len(self.results)

    ordered = True  # results are returned in a consistent order

########NEW FILE########
__FILENAME__ = tags
from __future__ import unicode_literals

from taggit.managers import TaggableManager, _TaggableManager
from taggit.utils import require_instance_manager

from modelcluster.queryset import FakeQuerySet

try:
    from south.modelsinspector import add_ignored_fields
except ImportError:
    # south is not in use, so make add_ignored_fields a no-op
    def add_ignored_fields(*args):
        pass

class _ClusterTaggableManager(_TaggableManager):
    @require_instance_manager
    def get_tagged_item_manager(self):
        """Return the manager that handles the relation from this instance to the tagged_item class.
        If content_object on the tagged_item class is defined as a ParentalKey, this will be a
        DeferringRelatedManager which allows writing related objects without committing them
        to the database.
        """
        rel_name = self.through._meta.get_field('content_object').related.get_accessor_name()
        return getattr(self.instance, rel_name)

    def get_query_set(self):
        # FIXME: we ought to have some way of querying the tagged item manager about whether
        # it has uncommitted changes, and return a real queryset (using the original taggit logic)
        # if not
        return FakeQuerySet(
            self.through.tag_model(),
            [tagged_item.tag for tagged_item in self.get_tagged_item_manager().all()]
        )

    # Django 1.6 renamed this
    get_queryset = get_query_set

    @require_instance_manager
    def add(self, *tags):
        # First turn the 'tags' list (which may be a mixture of tag objects and
        # strings which may or may not correspond to existing tag objects)
        # into 'tag_objs', a set of tag objects
        str_tags = set([
            t
            for t in tags
            if not isinstance(t, self.through.tag_model())
        ])
        tag_objs = set(tags) - str_tags
        # If str_tags has 0 elements Django actually optimizes that to not do a
        # query.  Malcolm is very smart.
        existing = self.through.tag_model().objects.filter(
            name__in=str_tags
        )
        tag_objs.update(existing)

        for new_tag in str_tags - set(t.name for t in existing):
            tag_objs.add(self.through.tag_model().objects.create(name=new_tag))

        # Now write these to the relation
        tagged_item_manager = self.get_tagged_item_manager()
        for tag in tag_objs:
            if not tagged_item_manager.filter(tag=tag):
                # make an instance of the self.through model and add it to the relation
                tagged_item = self.through(tag=tag)
                tagged_item_manager.add(tagged_item)

    @require_instance_manager
    def remove(self, *tags):
        tagged_item_manager = self.get_tagged_item_manager()
        tagged_items = [
            tagged_item for tagged_item in tagged_item_manager.all()
            if tagged_item.tag.name in tags
        ]
        tagged_item_manager.remove(*tagged_items)

    @require_instance_manager
    def clear(self):
        self.get_tagged_item_manager().clear()

class ClusterTaggableManager(TaggableManager):
    def __get__(self, instance, model):
        # override TaggableManager's requirement for instance to have a primary key
        # before we can access its tags
        try:
            manager = _ClusterTaggableManager(
                through=self.through, model=model, instance=instance, prefetch_cache_name = self.name
            )
        except TypeError:  # fallback for django-taggit pre 0.11
            manager = _ClusterTaggableManager(
                through=self.through, model=model, instance=instance
            )

        return manager

    def value_from_object(self, instance):
        # retrieve the queryset via the related manager on the content object,
        # to accommodate the possibility of this having uncommitted changes relative to
        # the live database
        rel_name = self.through._meta.get_field('content_object').related.get_accessor_name()
        return getattr(instance, rel_name).all()


# tell south to ignore ClusterTaggableManager, like it ignores taggit.TaggableManager
add_ignored_fields(["^modelcluster\.tags\.ClusterTaggableManager"])

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import os
import sys

from django.conf import settings
from django.core.management import execute_from_command_line


if not settings.configured:
    settings.configure(
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
            }
        },
        INSTALLED_APPS=[
            'modelcluster',

            'django.contrib.contenttypes',
            'taggit',

            'tests',
        ]
    )


def runtests():
    argv = sys.argv[:1] + ['test'] + sys.argv[1:]
    execute_from_command_line(argv)


if __name__ == '__main__':
    runtests()


########NEW FILE########
__FILENAME__ = shell
#!/usr/bin/env python
import os
import sys

from django.conf import settings
from django.core.management import execute_from_command_line


if not settings.configured:
    settings.configure(
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
            }
        },
        INSTALLED_APPS=[
            'modelcluster',
            'tests',
        ]
    )


def runtests():
    argv = sys.argv[:1] + ['shell'] + sys.argv[1:]
    execute_from_command_line(argv)


if __name__ == '__main__':
    runtests()


########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible

from modelcluster.tags import ClusterTaggableManager
from taggit.models import TaggedItemBase

from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel


@python_2_unicode_compatible
class Band(ClusterableModel):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class BandMember(models.Model):
    band = ParentalKey('Band', related_name='members')
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Album(models.Model):
    band = ParentalKey('Band', related_name='albums')
    name = models.CharField(max_length=255)
    release_date = models.DateField(null=True, blank=True)
    sort_order = models.IntegerField(null=True, blank=True, editable=False)

    sort_order_field = 'sort_order'

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['sort_order']


class TaggedPlace(TaggedItemBase):
    content_object = ParentalKey('Place', related_name='tagged_items')

@python_2_unicode_compatible
class Place(ClusterableModel):
    name = models.CharField(max_length=255)
    tags = ClusterTaggableManager(through=TaggedPlace)

    def __str__(self):
        return self.name


class Restaurant(Place):
    serves_hot_dogs = models.BooleanField()
    proprietor = models.ForeignKey('Chef', null=True, blank=True, on_delete=models.SET_NULL, related_name='restaurants')

@python_2_unicode_compatible
class Dish(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

@python_2_unicode_compatible
class Wine(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

@python_2_unicode_compatible
class Chef(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

@python_2_unicode_compatible
class MenuItem(models.Model):
    restaurant = ParentalKey('Restaurant', related_name='menu_items')
    dish = models.ForeignKey('Dish', related_name='+')
    price = models.DecimalField(max_digits=6, decimal_places=2)
    recommended_wine = models.ForeignKey('Wine', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    def __str__(self):
        return "%s - %f" % (self.dish, self.price)

########NEW FILE########
__FILENAME__ = test_cluster
from __future__ import unicode_literals

from django.test import TestCase
from django.db import IntegrityError

from tests.models import Band, BandMember, Album

class ClusterTest(TestCase):
    def test_can_create_cluster(self):
        beatles = Band(name='The Beatles')

        self.assertEqual(0, beatles.members.count())

        beatles.members = [
            BandMember(name='John Lennon'),
            BandMember(name='Paul McCartney'),
        ]

        # we should be able to query this relation using (some) queryset methods
        self.assertEqual(2, beatles.members.count())
        self.assertEqual('John Lennon', beatles.members.all()[0].name)
        self.assertEqual('Paul McCartney', beatles.members.filter(name='Paul McCartney')[0].name)
        self.assertEqual('Paul McCartney', beatles.members.get(name='Paul McCartney').name)
        self.assertRaises(BandMember.DoesNotExist, lambda: beatles.members.get(name='Reginald Dwight'))
        self.assertRaises(BandMember.MultipleObjectsReturned, lambda: beatles.members.get())

        self.assertEqual([('Paul McCartney',)], beatles.members.filter(name='Paul McCartney').values_list('name'))
        self.assertEqual(['Paul McCartney'], beatles.members.filter(name='Paul McCartney').values_list('name', flat=True))
        # quick-and-dirty check that we can invoke values_list with empty args list
        beatles.members.filter(name='Paul McCartney').values_list()

        # these should not exist in the database yet
        self.assertFalse(Band.objects.filter(name='The Beatles').exists())
        self.assertFalse(BandMember.objects.filter(name='John Lennon').exists())

        beatles.save()
        # this should create database entries
        self.assertTrue(Band.objects.filter(name='The Beatles').exists())
        self.assertTrue(BandMember.objects.filter(name='John Lennon').exists())

        john_lennon = BandMember.objects.get(name='John Lennon')
        beatles.members = [john_lennon]
        # reassigning should take effect on the in-memory record
        self.assertEqual(1, beatles.members.count())
        # but not the database
        self.assertEqual(2, Band.objects.get(name='The Beatles').members.count())

        beatles.save()
        # now updated in the database
        self.assertEqual(1, Band.objects.get(name='The Beatles').members.count())
        self.assertEqual(1, BandMember.objects.filter(name='John Lennon').count())
        # removed member should be deleted from the db entirely
        self.assertEqual(0, BandMember.objects.filter(name='Paul McCartney').count())

        # queries on beatles.members should now revert to SQL
        self.assertTrue(beatles.members.extra(where=["tests_bandmember.name='John Lennon'"]).exists())

    def test_related_manager_assignment_ops(self):
        beatles = Band(name='The Beatles')
        john = BandMember(name='John Lennon')
        paul = BandMember(name='Paul McCartney')

        beatles.members.add(john)
        self.assertEqual(1, beatles.members.count())

        beatles.members.add(paul)
        self.assertEqual(2, beatles.members.count())
        # ensure that duplicates are filtered
        beatles.members.add(paul)
        self.assertEqual(2, beatles.members.count())

        beatles.members.remove(john)
        self.assertEqual(1, beatles.members.count())
        self.assertEqual(paul, beatles.members.all()[0])

        george = beatles.members.create(name='George Harrison')
        self.assertEqual(2, beatles.members.count())
        self.assertEqual('George Harrison', george.name)

    def test_can_pass_child_relations_as_constructor_kwargs(self):
        beatles = Band(name='The Beatles', members=[
            BandMember(name='John Lennon'),
            BandMember(name='Paul McCartney'),
        ])
        self.assertEqual(2, beatles.members.count())
        self.assertEqual(beatles, beatles.members.all()[0].band)

    def test_can_only_commit_on_saved_parent(self):
        beatles = Band(name='The Beatles', members=[
            BandMember(name='John Lennon'),
            BandMember(name='Paul McCartney'),
        ])
        self.assertRaises(IntegrityError, lambda: beatles.members.commit())

        beatles.save()
        beatles.members.commit()

    def test_queryset_filtering(self):
        beatles = Band(name='The Beatles', members=[
            BandMember(id=1, name='John Lennon'),
            BandMember(id=2, name='Paul McCartney'),
        ])
        self.assertEqual('Paul McCartney', beatles.members.get(id=2).name)
        self.assertEqual('Paul McCartney', beatles.members.get(id='2').name)
        self.assertEqual(1, beatles.members.filter(name='Paul McCartney').count())

        # also need to be able to filter on foreign fields that return a model instance
        # rather than a simple python value
        self.assertEqual(2, beatles.members.filter(band=beatles).count())
        # and ensure that the comparison is not treating all unsaved instances as identical
        rutles = Band(name='The Rutles')
        self.assertEqual(0, beatles.members.filter(band=rutles).count())

        # and the comparison must be on the model instance's ID where available,
        # not by reference
        beatles.save()
        beatles.members.add(BandMember(id=3, name='George Harrison'))  # modify the relation so that we're not to a plain database-backed queryset

        also_beatles = Band.objects.get(id=beatles.id)
        self.assertEqual(3, beatles.members.filter(band=also_beatles).count())

    def test_prefetch_related(self):
        band1 = Band.objects.create(name='The Beatles', members=[
            BandMember(id=1, name='John Lennon'),
            BandMember(id=2, name='Paul McCartney'),
        ])
        with self.assertNumQueries(2):
            lists = [list(band.members.all()) for band in Band.objects.prefetch_related('members')]
        normal_lists = [list(band.members.all()) for band in Band.objects.all()]
        self.assertEqual(lists, normal_lists)

########NEW FILE########
__FILENAME__ = test_cluster_form
from __future__ import unicode_literals

from django.test import TestCase
from tests.models import Band, BandMember, Album
from modelcluster.forms import ClusterForm
from django.forms import Textarea, CharField

import datetime


class ClusterFormTest(TestCase):
    def test_cluster_form(self):
        class BandForm(ClusterForm):
            class Meta:
                model = Band

        self.assertTrue(BandForm.formsets)

        beatles = Band(name='The Beatles', members=[
            BandMember(name='John Lennon'),
            BandMember(name='Paul McCartney'),
        ])

        form = BandForm(instance=beatles)

        self.assertEqual(5, len(form.formsets['members'].forms))
        self.assertTrue('albums' in form.as_p())

    def test_empty_cluster_form(self):
        class BandForm(ClusterForm):
            class Meta:
                model = Band

        form = BandForm()
        self.assertEqual(3, len(form.formsets['members'].forms))

    def test_incoming_form_data(self):
        class BandForm(ClusterForm):
            class Meta:
                model = Band

        beatles = Band(name='The Beatles', members=[
            BandMember(name='George Harrison'),
        ])
        form = BandForm({
            'name': "The Beatles",

            'members-TOTAL_FORMS': 4,
            'members-INITIAL_FORMS': 1,
            'members-MAX_NUM_FORMS': 1000,

            'members-0-name': 'George Harrison',
            'members-0-DELETE': 'members-0-DELETE',
            'members-0-id': '',

            'members-1-name': 'John Lennon',
            'members-1-id': '',

            'members-2-name': 'Paul McCartney',
            'members-2-id': '',

            'members-3-name': '',
            'members-3-id': '',

            'albums-TOTAL_FORMS': 0,
            'albums-INITIAL_FORMS': 0,
            'albums-MAX_NUM_FORMS': 1000,
        }, instance=beatles)

        self.assertTrue(form.is_valid())
        result = form.save(commit=False)
        self.assertEqual(result, beatles)

        self.assertEqual(2, beatles.members.count())
        self.assertEqual('John Lennon', beatles.members.all()[0].name)

        # should not exist in the database yet
        self.assertFalse(BandMember.objects.filter(name='John Lennon').exists())

        beatles.save()
        # this should create database entries
        self.assertTrue(Band.objects.filter(name='The Beatles').exists())
        self.assertTrue(BandMember.objects.filter(name='John Lennon').exists())

    def test_explicit_formset_list(self):
        class BandForm(ClusterForm):
            class Meta:
                model = Band
                formsets = ('members',)

        form = BandForm()
        self.assertTrue(form.formsets.get('members'))
        self.assertFalse(form.formsets.get('albums'))

        self.assertTrue('members' in form.as_p())
        self.assertFalse('albums' in form.as_p())

    def test_excluded_formset_list(self):
        class BandForm(ClusterForm):
            class Meta:
                model = Band
                exclude_formsets = ('albums',)

        form = BandForm()
        self.assertTrue(form.formsets.get('members'))
        self.assertFalse(form.formsets.get('albums'))

        self.assertTrue('members' in form.as_p())
        self.assertFalse('albums' in form.as_p())

    def test_widget_overrides(self):
        class BandForm(ClusterForm):
            class Meta:
                model = Band
                widgets = {
                    'name': Textarea(),
                    'members': {
                        'name': Textarea()
                    }
                }

        form = BandForm()
        self.assertEqual(Textarea, type(form['name'].field.widget))
        self.assertEqual(Textarea, type(form.formsets['members'].forms[0]['name'].field.widget))

    def test_formfield_callback(self):

        def formfield_for_dbfield(db_field, **kwargs):
            # a particularly stupid formfield_callback that just uses Textarea for everything
            return CharField(widget=Textarea, **kwargs)

        class BandFormWithFFC(ClusterForm):
            formfield_callback = formfield_for_dbfield
            class Meta:
                model = Band

        form = BandFormWithFFC()
        self.assertEqual(Textarea, type(form['name'].field.widget))
        self.assertEqual(Textarea, type(form.formsets['members'].forms[0]['name'].field.widget))

    def test_saved_items(self):
        class BandForm(ClusterForm):
            class Meta:
                model = Band

        beatles = Band(name='The Beatles', members=[
            BandMember(name='John Lennon'),
            BandMember(name='Paul McCartney'),
        ])
        beatles.save()
        member0, member1 = beatles.members.all()
        self.assertTrue(member0.id)
        self.assertTrue(member1.id)

        form = BandForm({
            'name': "The New Beatles",

            'members-TOTAL_FORMS': 4,
            'members-INITIAL_FORMS': 2,
            'members-MAX_NUM_FORMS': 1000,

            'members-0-name': member0.name,
            'members-0-DELETE': 'members-0-DELETE',
            'members-0-id': member0.id,

            'members-1-name': member1.name,
            'members-1-id': member1.id,

            'members-2-name': 'George Harrison',
            'members-2-id': '',

            'members-3-name': '',
            'members-3-id': '',

            'albums-TOTAL_FORMS': 0,
            'albums-INITIAL_FORMS': 0,
            'albums-MAX_NUM_FORMS': 1000,
        }, instance=beatles)
        self.assertTrue(form.is_valid())
        form.save()

        new_beatles = Band.objects.get(id=beatles.id)
        self.assertEqual('The New Beatles', new_beatles.name)
        self.assertTrue(BandMember.objects.filter(name='George Harrison').exists())
        self.assertFalse(BandMember.objects.filter(name='John Lennon').exists())

    def test_saved_items_with_non_db_relation(self):
        class BandForm(ClusterForm):
            class Meta:
                model = Band

        beatles = Band(name='The Beatles', members=[
            BandMember(name='John Lennon'),
            BandMember(name='Paul McCartney'),
        ])
        beatles.save()
        member0, member1 = beatles.members.all()

        # pack and unpack the record so that we're working with a non-db-backed queryset
        new_beatles = Band.from_json(beatles.to_json())

        form = BandForm({
            'name': "The New Beatles",

            'members-TOTAL_FORMS': 4,
            'members-INITIAL_FORMS': 2,
            'members-MAX_NUM_FORMS': 1000,

            'members-0-name': member0.name,
            'members-0-DELETE': 'members-0-DELETE',
            'members-0-id': member0.id,

            'members-1-name': member1.name,
            'members-1-id': member1.id,

            'members-2-name': 'George Harrison',
            'members-2-id': '',

            'members-3-name': '',
            'members-3-id': '',

            'albums-TOTAL_FORMS': 0,
            'albums-INITIAL_FORMS': 0,
            'albums-MAX_NUM_FORMS': 1000,
        }, instance=new_beatles)
        self.assertTrue(form.is_valid())
        form.save()

        new_beatles = Band.objects.get(id=beatles.id)
        self.assertEqual('The New Beatles', new_beatles.name)
        self.assertTrue(BandMember.objects.filter(name='George Harrison').exists())
        self.assertFalse(BandMember.objects.filter(name='John Lennon').exists())

    def test_creation(self):
        class BandForm(ClusterForm):
            class Meta:
                model = Band

        form = BandForm({
            'name': "The Beatles",

            'members-TOTAL_FORMS': 4,
            'members-INITIAL_FORMS': 0,
            'members-MAX_NUM_FORMS': 1000,

            'members-0-name': 'John Lennon',
            'members-0-id': '',

            'members-1-name': 'Paul McCartney',
            'members-1-id': '',

            'members-2-name': 'Pete Best',
            'members-2-DELETE': 'members-0-DELETE',
            'members-2-id': '',

            'members-3-name': '',
            'members-3-id': '',

            'albums-TOTAL_FORMS': 0,
            'albums-INITIAL_FORMS': 0,
            'albums-MAX_NUM_FORMS': 1000,
        })
        self.assertTrue(form.is_valid())
        beatles = form.save()

        self.assertTrue(beatles.id)
        self.assertEqual('The Beatles', beatles.name)
        self.assertEqual('The Beatles', Band.objects.get(id=beatles.id).name)
        self.assertEqual(2, beatles.members.count())
        self.assertTrue(BandMember.objects.filter(name='John Lennon').exists())
        self.assertFalse(BandMember.objects.filter(name='Pete Best').exists())

    def test_sort_order_is_output_on_form(self):
        class BandForm(ClusterForm):
            class Meta:
                model = Band

        form = BandForm()
        form_html = form.as_p()
        self.assertTrue('albums-0-ORDER' in form_html)
        self.assertFalse('members-0-ORDER' in form_html)

    def test_sort_order_is_committed(self):
        class BandForm(ClusterForm):
            class Meta:
                model = Band

        form = BandForm({
            'name': "The Beatles",

            'members-TOTAL_FORMS': 0,
            'members-INITIAL_FORMS': 0,
            'members-MAX_NUM_FORMS': 1000,

            'albums-TOTAL_FORMS': 2,
            'albums-INITIAL_FORMS': 0,
            'albums-MAX_NUM_FORMS': 1000,

            'albums-0-name': 'With The Beatles',
            'albums-0-id': '',
            'albums-0-ORDER': 2,

            'albums-1-name': 'Please Please Me',
            'albums-1-id': '',
            'albums-1-ORDER': 1,
        })
        self.assertTrue(form.is_valid())
        beatles = form.save()

        self.assertEqual('Please Please Me', beatles.albums.all()[0].name)
        self.assertEqual('With The Beatles', beatles.albums.all()[1].name)

    def test_ignore_validation_on_deleted_items(self):
        class BandForm(ClusterForm):
            class Meta:
                model = Band

        please_please_me = Album(name='Please Please Me', release_date = datetime.date(1963, 3, 22))
        beatles = Band(name='The Beatles', albums=[please_please_me])
        beatles.save()

        form = BandForm({
            'name': "The Beatles",

            'members-TOTAL_FORMS': 0,
            'members-INITIAL_FORMS': 0,
            'members-MAX_NUM_FORMS': 1000,

            'albums-TOTAL_FORMS': 1,
            'albums-INITIAL_FORMS': 1,
            'albums-MAX_NUM_FORMS': 1000,

            'albums-0-name': 'With The Beatles',
            'albums-0-release_date': '1963-02-31',  # invalid date
            'albums-0-id': please_please_me.id,
            'albums-0-ORDER': 1,
        }, instance=beatles)

        self.assertFalse(form.is_valid())

        form = BandForm({
            'name': "The Beatles",

            'members-TOTAL_FORMS': 0,
            'members-INITIAL_FORMS': 0,
            'members-MAX_NUM_FORMS': 1000,

            'albums-TOTAL_FORMS': 1,
            'albums-INITIAL_FORMS': 1,
            'albums-MAX_NUM_FORMS': 1000,

            'albums-0-name': 'With The Beatles',
            'albums-0-release_date': '1963-02-31',  # invalid date
            'albums-0-id': please_please_me.id,
            'albums-0-ORDER': 1,
            'albums-0-DELETE': 'albums-0-DELETE',
        }, instance=beatles)

        self.assertTrue(form.is_valid())
        result = form.save(commit=False)
        self.assertEqual(0, beatles.albums.count())
        self.assertEqual(1, Band.objects.get(id=beatles.id).albums.count())
        beatles.save()
        self.assertEqual(0, Band.objects.get(id=beatles.id).albums.count())

    def test_cluster_form_without_formsets(self):
        class BandForm(ClusterForm):
            class Meta:
                model = Band
                formsets = ()

        beatles = Band(name='The Beatles')
        beatles.save()

        form = BandForm({
            'name': "The New Beatles",
        }, instance=beatles)

        self.assertTrue(form.is_valid())

        form.save(commit=False)

        self.assertEqual(1, Band.objects.filter(name='The Beatles').count())
        beatles.save()
        self.assertEqual(0, Band.objects.filter(name='The Beatles').count())

########NEW FILE########
__FILENAME__ = test_formset
from __future__ import unicode_literals

from django.test import TestCase
from modelcluster.forms import transientmodelformset_factory, childformset_factory
from tests.models import Band, BandMember

class TransientFormsetTest(TestCase):
    BandMembersFormset = transientmodelformset_factory(BandMember, exclude=['band'], extra=3, can_delete=True)

    def test_can_create_formset(self):
        beatles = Band(name='The Beatles', members=[
            BandMember(name='John Lennon'),
            BandMember(name='Paul McCartney'),
        ])
        band_members_formset = self.BandMembersFormset(queryset=beatles.members.all())

        self.assertEqual(5, len(band_members_formset.forms))
        self.assertEqual('John Lennon', band_members_formset.forms[0].instance.name)

    def test_incoming_formset_data(self):
        beatles = Band(name='The Beatles', members=[
            BandMember(name='George Harrison'),
        ])

        band_members_formset = self.BandMembersFormset({
            'form-TOTAL_FORMS': 3,
            'form-INITIAL_FORMS': 1,
            'form-MAX_NUM_FORMS': 1000,

            'form-0-name': 'John Lennon',
            'form-0-id': '',

            'form-1-name': 'Paul McCartney',
            'form-1-id': '',

            'form-2-name': '',
            'form-2-id': '',
        }, queryset=beatles.members.all())

        self.assertTrue(band_members_formset.is_valid())
        members = band_members_formset.save(commit=False)
        self.assertEqual(2, len(members))
        self.assertEqual('John Lennon', members[0].name)
        # should not exist in the database yet
        self.assertFalse(BandMember.objects.filter(name='John Lennon').exists())

    def test_save_commit_false(self):
        john = BandMember(name='John Lennon')
        paul = BandMember(name='Paul McCartney')
        ringo = BandMember(name='Richard Starkey')
        beatles = Band(name='The Beatles', members=[
            john, paul, ringo
        ])
        beatles.save()

        john_id, paul_id, ringo_id = john.id, paul.id, ringo.id

        self.assertTrue(john_id)
        self.assertTrue(paul_id)

        band_members_formset = self.BandMembersFormset({
            'form-TOTAL_FORMS': 5,
            'form-INITIAL_FORMS': 3,
            'form-MAX_NUM_FORMS': 1000,

            'form-0-name': 'John Lennon',
            'form-0-DELETE': 'form-0-DELETE',
            'form-0-id': john_id,

            'form-1-name': 'Paul McCartney',
            'form-1-id': paul_id,

            'form-2-name': 'Ringo Starr',  # changing data of an existing record
            'form-2-id': ringo_id,

            'form-3-name': '',
            'form-3-id': '',

            'form-4-name': 'George Harrison',  # Adding a record
            'form-4-id': '',
        }, queryset=beatles.members.all())
        self.assertTrue(band_members_formset.is_valid())

        updated_members = band_members_formset.save(commit=False)
        self.assertEqual(2, len(updated_members))
        self.assertEqual('Ringo Starr', updated_members[0].name)
        self.assertEqual(ringo_id, updated_members[0].id)

        # should not be updated in the db yet
        self.assertEqual('Richard Starkey', BandMember.objects.get(id=ringo_id).name)

        self.assertEqual('George Harrison', updated_members[1].name)
        self.assertFalse(updated_members[1].id)  # no ID yet

    def test_save_commit_true(self):
        john = BandMember(name='John Lennon')
        paul = BandMember(name='Paul McCartney')
        ringo = BandMember(name='Richard Starkey')
        beatles = Band(name='The Beatles', members=[
            john, paul, ringo
        ])
        beatles.save()

        john_id, paul_id, ringo_id = john.id, paul.id, ringo.id

        self.assertTrue(john_id)
        self.assertTrue(paul_id)

        band_members_formset = self.BandMembersFormset({
            'form-TOTAL_FORMS': 4,
            'form-INITIAL_FORMS': 3,
            'form-MAX_NUM_FORMS': 1000,

            'form-0-name': 'John Lennon',
            'form-0-DELETE': 'form-0-DELETE',
            'form-0-id': john_id,

            'form-1-name': 'Paul McCartney',
            'form-1-id': paul_id,

            'form-2-name': 'Ringo Starr',  # changing data of an existing record
            'form-2-id': ringo_id,

            'form-3-name': '',
            'form-3-id': '',
        }, queryset=beatles.members.all())
        self.assertTrue(band_members_formset.is_valid())

        updated_members = band_members_formset.save()
        self.assertEqual(1, len(updated_members))
        self.assertEqual('Ringo Starr', updated_members[0].name)
        self.assertEqual(ringo_id, updated_members[0].id)

        self.assertFalse(BandMember.objects.filter(id=john_id).exists())
        self.assertEqual('Paul McCartney', BandMember.objects.get(id=paul_id).name)
        self.assertEqual(beatles.id, BandMember.objects.get(id=paul_id).band_id)
        self.assertEqual('Ringo Starr', BandMember.objects.get(id=ringo_id).name)
        self.assertEqual(beatles.id, BandMember.objects.get(id=ringo_id).band_id)


class ChildFormsetTest(TestCase):
    def test_can_create_formset(self):
        beatles = Band(name='The Beatles', members=[
            BandMember(name='John Lennon'),
            BandMember(name='Paul McCartney'),
        ])
        BandMembersFormset = childformset_factory(Band, BandMember, extra=3)
        band_members_formset = BandMembersFormset(instance=beatles)

        self.assertEqual(5, len(band_members_formset.forms))
        self.assertEqual('John Lennon', band_members_formset.forms[0].instance.name)

    def test_empty_formset(self):
        BandMembersFormset = childformset_factory(Band, BandMember, extra=3)
        band_members_formset = BandMembersFormset()
        self.assertEqual(3, len(band_members_formset.forms))

    def test_save_commit_false(self):
        john = BandMember(name='John Lennon')
        paul = BandMember(name='Paul McCartney')
        ringo = BandMember(name='Richard Starkey')
        beatles = Band(name='The Beatles', members=[
            john, paul, ringo
        ])
        beatles.save()
        john_id, paul_id, ringo_id = john.id, paul.id, ringo.id

        BandMembersFormset = childformset_factory(Band, BandMember, extra=3)

        band_members_formset = BandMembersFormset({
            'form-TOTAL_FORMS': 5,
            'form-INITIAL_FORMS': 3,
            'form-MAX_NUM_FORMS': 1000,

            'form-0-name': 'John Lennon',
            'form-0-DELETE': 'form-0-DELETE',
            'form-0-id': john_id,

            'form-1-name': 'Paul McCartney',
            'form-1-id': paul_id,

            'form-2-name': 'Ringo Starr',  # changing data of an existing record
            'form-2-id': ringo_id,

            'form-3-name': '',
            'form-3-id': '',

            'form-4-name': 'George Harrison',  # adding a record
            'form-4-id': '',
        }, instance=beatles)
        self.assertTrue(band_members_formset.is_valid())
        updated_members = band_members_formset.save(commit=False)

        # updated_members should only include the items that have been changed and not deleted
        self.assertEqual(2, len(updated_members))
        self.assertEqual('Ringo Starr', updated_members[0].name)
        self.assertEqual(ringo_id, updated_members[0].id)

        self.assertEqual('George Harrison', updated_members[1].name)
        self.assertEqual(None, updated_members[1].id)

        # Changes should not be committed to the db yet
        self.assertTrue(BandMember.objects.filter(name='John Lennon', id=john_id).exists())
        self.assertEqual('Richard Starkey', BandMember.objects.get(id=ringo_id).name)
        self.assertFalse(BandMember.objects.filter(name='George Harrison').exists())

        beatles.members.commit()
        # this should create/update/delete database entries
        self.assertEqual('Ringo Starr', BandMember.objects.get(id=ringo_id).name)
        self.assertTrue(BandMember.objects.filter(name='George Harrison').exists())
        self.assertFalse(BandMember.objects.filter(name='John Lennon').exists())

    def test_child_updates_without_ids(self):
        john = BandMember(name='John Lennon')
        beatles = Band(name='The Beatles', members=[
            john
        ])
        beatles.save()
        john_id = john.id

        paul = BandMember(name='Paul McCartney')
        beatles.members.add(paul)

        BandMembersFormset = childformset_factory(Band, BandMember, extra=3)
        band_members_formset = BandMembersFormset({
            'form-TOTAL_FORMS': 2,
            'form-INITIAL_FORMS': 2,
            'form-MAX_NUM_FORMS': 1000,

            'form-0-name': 'John Lennon',
            'form-0-id': john_id,

            'form-1-name': 'Paul McCartney',  # NB no way to know programmatically that this form corresponds to the 'paul' object
            'form-1-id': '',
        }, instance=beatles)

        self.assertTrue(band_members_formset.is_valid())
        band_members_formset.save(commit=False)
        self.assertEqual(2, beatles.members.count())

########NEW FILE########
__FILENAME__ = test_serialize
from __future__ import unicode_literals

from django.test import TestCase
import datetime

from tests.models import Band, BandMember, Album, Restaurant, Dish, MenuItem, Chef, Wine

class SerializeTest(TestCase):
    def test_serialize(self):
        beatles = Band(name='The Beatles', members=[
            BandMember(name='John Lennon'),
            BandMember(name='Paul McCartney'),
        ])

        expected = {'pk': None, 'albums': [], 'name': 'The Beatles', 'members': [{'pk': None, 'name': 'John Lennon', 'band': None}, {'pk': None, 'name': 'Paul McCartney', 'band': None}]}
        self.assertEqual(expected, beatles.serializable_data())

    def test_serialize_json_with_dates(self):
        beatles = Band(name='The Beatles', members=[
            BandMember(name='John Lennon'),
            BandMember(name='Paul McCartney'),
        ], albums=[
            Album(name='Rubber Soul', release_date=datetime.date(1965, 12, 3))
        ])

        beatles_json = beatles.to_json()
        self.assertTrue("John Lennon" in beatles_json)
        self.assertTrue("1965-12-03" in beatles_json)
        unpacked_beatles = Band.from_json(beatles_json)
        self.assertEqual(datetime.date(1965, 12, 3), unpacked_beatles.albums.all()[0].release_date)

    def test_deserialize(self):
        beatles = Band.from_serializable_data({
            'pk': 9,
            'albums': [],
            'name': 'The Beatles',
            'members': [
                {'pk': None, 'name': 'John Lennon', 'band': None},
                {'pk': None, 'name': 'Paul McCartney', 'band': None},
            ]
        })
        self.assertEqual(9, beatles.id)
        self.assertEqual('The Beatles', beatles.name)
        self.assertEqual(2, beatles.members.count())
        self.assertEqual(BandMember, beatles.members.all()[0].__class__)

    def test_deserialize_json(self):
        beatles = Band.from_json('{"pk": 9, "albums": [], "name": "The Beatles", "members": [{"pk": null, "name": "John Lennon", "band": null}, {"pk": null, "name": "Paul McCartney", "band": null}]}')
        self.assertEqual(9, beatles.id)
        self.assertEqual('The Beatles', beatles.name)
        self.assertEqual(2, beatles.members.count())
        self.assertEqual(BandMember, beatles.members.all()[0].__class__)

    def test_deserialize_with_multi_table_inheritance(self):
        fatduck = Restaurant.from_json('{"pk": 42, "name": "The Fat Duck", "serves_hot_dogs": false}')
        self.assertEqual(42, fatduck.id)

        data = fatduck.serializable_data()
        self.assertEqual(42, data['pk'])
        self.assertEqual("The Fat Duck", data['name'])

    def test_dangling_foreign_keys(self):
        heston_blumenthal = Chef.objects.create(name="Heston Blumenthal")
        snail_ice_cream = Dish.objects.create(name="Snail ice cream")
        chateauneuf = Wine.objects.create(name="Chateauneuf-du-Pape 1979")
        fat_duck = Restaurant(name="The Fat Duck", proprietor=heston_blumenthal, serves_hot_dogs=False, menu_items=[
            MenuItem(dish=snail_ice_cream, price='20.00', recommended_wine=chateauneuf)
        ])
        fat_duck_json = fat_duck.to_json()

        fat_duck = Restaurant.from_json(fat_duck_json)
        self.assertEqual("Heston Blumenthal", fat_duck.proprietor.name)
        self.assertEqual("Chateauneuf-du-Pape 1979", fat_duck.menu_items.all()[0].recommended_wine.name)

        heston_blumenthal.delete()
        fat_duck = Restaurant.from_json(fat_duck_json)
        # the deserialised record should recognise that the heston_blumenthal record is now missing
        self.assertEqual(None, fat_duck.proprietor)
        self.assertEqual("Chateauneuf-du-Pape 1979", fat_duck.menu_items.all()[0].recommended_wine.name)

        chateauneuf.delete()  # oh dear, looks like we just drank the last bottle
        fat_duck = Restaurant.from_json(fat_duck_json)
        # the deserialised record should now have a null recommended_wine field
        self.assertEqual(None, fat_duck.menu_items.all()[0].recommended_wine)

        snail_ice_cream.delete()  # NOM NOM NOM
        fat_duck = Restaurant.from_json(fat_duck_json)
        # the menu item should now be dropped entirely (because the foreign key to Dish has on_delete=CASCADE)
        self.assertEqual(0, fat_duck.menu_items.count())

########NEW FILE########
__FILENAME__ = test_tag
from __future__ import unicode_literals

from django.test import TestCase
from taggit.models import Tag
from modelcluster.forms import ClusterForm

from tests.models import Place, TaggedPlace

class TagTest(TestCase):
    def test_can_access_tags_on_unsaved_instance(self):
        mission_burrito = Place(name='Mission Burrito')
        self.assertEqual(0, mission_burrito.tags.count())

        mission_burrito.tags.add('mexican', 'burrito')
        self.assertEqual(2, mission_burrito.tags.count())
        self.assertEqual(Tag, mission_burrito.tags.all()[0].__class__)
        self.assertTrue([tag for tag in mission_burrito.tags.all() if tag.name == 'mexican'])

        mission_burrito.save()
        self.assertEqual(2, TaggedPlace.objects.filter(content_object_id=mission_burrito.id).count())

        mission_burrito.tags.remove('burrito')
        self.assertEqual(1, mission_burrito.tags.count())
        # should not affect database until we save
        self.assertEqual(2, TaggedPlace.objects.filter(content_object_id=mission_burrito.id).count())
        mission_burrito.save()
        self.assertEqual(1, TaggedPlace.objects.filter(content_object_id=mission_burrito.id).count())

        mission_burrito.tags.clear()
        self.assertEqual(0, mission_burrito.tags.count())
        # should not affect database until we save
        self.assertEqual(1, TaggedPlace.objects.filter(content_object_id=mission_burrito.id).count())
        mission_burrito.save()
        self.assertEqual(0, TaggedPlace.objects.filter(content_object_id=mission_burrito.id).count())

        mission_burrito.tags.set('mexican', 'burrito')
        self.assertEqual(2, mission_burrito.tags.count())
        self.assertEqual(0, TaggedPlace.objects.filter(content_object_id=mission_burrito.id).count())
        mission_burrito.save()
        self.assertEqual(2, TaggedPlace.objects.filter(content_object_id=mission_burrito.id).count())

    def test_tag_form_field(self):
        class PlaceForm(ClusterForm):
            class Meta:
                model = Place
                exclude_formsets = ['tagged_items']

        mission_burrito = Place(name='Mission Burrito')
        mission_burrito.tags.add('mexican', 'burrito')

        form = PlaceForm(instance=mission_burrito)
        self.assertEqual(2, len(form['tags'].value()))
        self.assertEqual(TaggedPlace, form['tags'].value()[0].__class__)

        form = PlaceForm({
            'name': "Mission Burrito",
            'tags': "burrito, fajita"
        }, instance=mission_burrito)
        self.assertTrue(form.is_valid())
        mission_burrito = form.save(commit=False)
        self.assertTrue(Tag.objects.get(name='burrito') in mission_burrito.tags.all())
        self.assertTrue(Tag.objects.get(name='fajita') in mission_burrito.tags.all())
        self.assertFalse(Tag.objects.get(name='mexican') in mission_burrito.tags.all())

########NEW FILE########
