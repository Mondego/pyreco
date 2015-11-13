__FILENAME__ = admin
# coding: utf-8

"""
    admin
    ~~~~~

    Admin extensions for django-reversion-compare

    :copyleft: 2012 by the django-reversion-compare team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""
import logging

from django import template
from django.conf.urls import patterns, url
from django.contrib.admin.util import unquote, quote
from django.core.urlresolvers import reverse
from django.http import Http404
from django.shortcuts import get_object_or_404, render_to_response
from django.template.loader import render_to_string
from django.utils.text import capfirst
from django.utils.translation import ugettext as _

from reversion.admin import VersionAdmin
from reversion.models import has_int_pk

from reversion_compare.forms import SelectDiffForm
from reversion_compare.helpers import html_diff
from django.conf import settings
from django.contrib.contenttypes.models import ContentType


logger = logging.getLogger(__name__)


class CompareObject(object):
    def __init__(self, field, field_name, obj, version, has_int_pk, adapter):
        self.field = field
        self.field_name = field_name
        self.obj = obj
        self.version = version  # instance of reversion.models.Version()
        self.has_int_pk = has_int_pk
        self.adapter = adapter
        # try and get a value, if none punt
        self.value =  version.field_dict.get(field_name, "Field Didn't exist!")

    def _obj_repr(self, obj):
        # FIXME: How to create a better representation of the current value?
        try:
            return unicode(obj)
        except Exception, e:
            return repr(obj)

    def _to_string_ManyToManyField(self):
        queryset = self.get_many_to_many()
        return ", ".join([self._obj_repr(item) for item in queryset])

    def _to_string_ForeignKey(self):
        obj = self.get_related()
        return self._obj_repr(obj)

    def to_string(self):
        internal_type = self.field.get_internal_type()
        func_name = "_to_string_%s" % internal_type
        if hasattr(self, func_name):
            func = getattr(self, func_name)
            return func()

        if isinstance(self.value, basestring):
            return self.value
        else:
            return self._obj_repr(self.value)

    def __cmp__(self, other):
        raise NotImplemented()

    def __eq__(self, other):
        assert self.field.get_internal_type() != "ManyToManyField"

        if self.value != other.value:
            return False

        if self.field.get_internal_type() == "ForeignKey":  # FIXME!
            if self.version.field_dict != other.version.field_dict:
                return False

        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def get_related(self):
        if self.field.rel is not None:
            obj = self.version.object_version.object
            related = getattr(obj, self.field.name)
            return related

    def get_many_to_many(self):
        """
        returns a queryset with all many2many objects
        """
        if self.field.get_internal_type() != "ManyToManyField":  # FIXME!
            return (None, None, None)

        if self.has_int_pk:
            ids = [int(v) for v in self.value]  # is: version.field_dict[field.name]

        # get instance of reversion.models.Revision():
        # A group of related object versions.
        old_revision = self.version.revision

        # Get the related model of the current field:
        related_model = self.field.rel.to

        # Get a queryset with all related objects.
        queryset = old_revision.version_set.filter(
            content_type=ContentType.objects.get_for_model(related_model),
            object_id__in=ids
        )
#        logger.debug("m2m queryset: %s", queryset)

        versions = sorted(list(queryset))
#        logger.debug("versions: %s", versions)

        if self.has_int_pk:
            # The primary_keys would be stored in a text field -> convert
            # it to integers
            # This is interesting in different places!
            for version in versions:
                version.object_id = int(version.object_id)

        missing_objects = []
        missing_ids = []

        if self.field_name not in self.adapter.follow:
            # This models was not registered with follow relations
            # Try to fill missing related objects
            target_ids = set(ids)
            actual_ids = set([version.object_id for version in versions])
            missing_ids1 = target_ids.difference(actual_ids)
            # logger.debug(self.field_name, "target: %s - actual: %s - missing: %s" % (target_ids, actual_ids, missing_ids1))
            if missing_ids1:
                missing_objects = related_model.objects.all().filter(pk__in=missing_ids1)
                missing_ids = list(target_ids.difference(set(missing_objects.values_list('pk', flat=True))))

        return versions, missing_objects, missing_ids

    def get_debug(self):
        if not settings.DEBUG:
            return

        result = [
            "field..............: %r" % self.field,
            "field_name.........: %r" % self.field_name,
            "field internal type: %r" % self.field.get_internal_type(),
            "field_dict.........: %s" % repr(self.version.field_dict),
            "adapter............: %r (follow: %r)" % (self.adapter, ", ".join(self.adapter.follow)),
            "has_int_pk ........: %r" % self.has_int_pk,
            "obj................: %r (pk: %s, id: %s)" % (self.obj, self.obj.pk, id(self.obj)),
            "version............: %r (pk: %s, id: %s)" % (self.version, self.version.pk, id(self.version)),
            "value..............: %r" % self.value,
            "to string..........: %s" % repr(self.to_string()),
            "related............: %s" % repr(self.get_related()),
        ]
        m2m_versions, missing_objects, missing_ids = self.get_many_to_many()
        if m2m_versions or missing_objects or missing_ids:
            result.append(
                "many-to-many.......: %s" % ", ".join(
                    ["%s" % item for item in m2m_versions]
                )
            )

            if missing_objects:
                result.append("missing m2m objects: %s" % repr(missing_objects))
            else:
                result.append("missing m2m objects: (has no)")

            if missing_ids:
                result.append("missing m2m IDs....: %s" % repr(missing_ids))
            else:
                result.append("missing m2m IDs....: (has no)")
        else:
            result.append("many-to-many.......: (has no)")

        return result

    def debug(self):
        if not settings.DEBUG:
            return
        for item in self.get_debug():
            logger.debug(item)


class CompareObjects(object):
    def __init__(self, field, field_name, obj, version1, version2, manager):
        self.field = field
        self.field_name = field_name
        self.obj = obj

        model = self.obj.__class__
        self.has_int_pk = has_int_pk(model)
        self.adapter = manager.get_adapter(model) # VersionAdapter instance

        # is a related field (ForeignKey, ManyToManyField etc.)
        self.is_related = self.field.rel is not None

        if not self.is_related:
            self.follow = None
        elif self.field_name in self.adapter.follow:
            self.follow = True
        else:
            self.follow = False

        self.compare_obj1 = CompareObject(field, field_name, obj, version1, self.has_int_pk, self.adapter)
        self.compare_obj2 = CompareObject(field, field_name, obj, version2, self.has_int_pk, self.adapter)

        self.value1 = self.compare_obj1.value
        self.value2 = self.compare_obj2.value

    def changed(self):
        """ return True if at least one field has changed values. """

        if self.field.get_internal_type() == "ManyToManyField":  # FIXME!
            info = self.get_m2m_change_info()
            keys = (
                "changed_items", "removed_items", "added_items",
                "removed_missing_objects", "added_missing_objects"
            )
            for key in keys:
                if info[key]:
                    return True
            return False

        return self.compare_obj1 != self.compare_obj2

    def _get_result(self, compare_obj, func_name):
        func = getattr(compare_obj, func_name)
        result = func()
        return result

    def _get_both_results(self, func_name):
        result1 = self._get_result(self.compare_obj1, func_name)
        result2 = self._get_result(self.compare_obj2, func_name)
        return (result1, result2)

    def to_string(self):
        return self._get_both_results("to_string")

    def get_related(self):
        return self._get_both_results("get_related")

    def get_many_to_many(self):
        #return self._get_both_results("get_many_to_many")
        m2m_data1, m2m_data2 = self._get_both_results("get_many_to_many")
        return m2m_data1, m2m_data2

    M2M_CHANGE_INFO = None

    def get_m2m_change_info(self):
        if self.M2M_CHANGE_INFO is not None:
            return self.M2M_CHANGE_INFO

        m2m_data1, m2m_data2 = self.get_many_to_many()

        result1, missing_objects1, missing_ids1 = m2m_data1
        result2, missing_objects2, missing_ids2 = m2m_data2

#        missing_objects_pk1 = [obj.pk for obj in missing_objects1]
#        missing_objects_pk2 = [obj.pk for obj in missing_objects2]
        missing_objects_dict2 = dict([(obj.pk, obj) for obj in missing_objects2])

        # logger.debug("missing_objects1: %s", missing_objects1)
        # logger.debug("missing_objects2: %s", missing_objects2)
        # logger.debug("missing_ids1: %s", missing_ids1)
        # logger.debug("missing_ids2: %s", missing_ids2)

        missing_object_set1 = set(missing_objects1)
        missing_object_set2 = set(missing_objects2)
        # logger.debug("%s %s", missing_object_set1, missing_object_set2)

        same_missing_objects = missing_object_set1.intersection(missing_object_set2)
        removed_missing_objects = missing_object_set1.difference(missing_object_set2)
        added_missing_objects = missing_object_set2.difference(missing_object_set1)

        # logger.debug("same_missing_objects: %s", same_missing_objects)
        # logger.debug("removed_missing_objects: %s", removed_missing_objects)
        # logger.debug("added_missing_objects: %s", added_missing_objects)


        # Create same_items, removed_items, added_items with related m2m items

        changed_items = []
        removed_items = []
        added_items = []
        same_items = []

        primary_keys1 = [version.object_id for version in result1]
        primary_keys2 = [version.object_id for version in result2]

        result_dict1 = dict([(version.object_id, version) for version in result1])
        result_dict2 = dict([(version.object_id, version) for version in result2])

        # logger.debug(result_dict1)
        # logger.debug(result_dict2)

        for primary_key in set(primary_keys1).union(set(primary_keys2)):
            if primary_key in result_dict1:
                version1 = result_dict1[primary_key]
            else:
                version1 = None

            if primary_key in result_dict2:
                version2 = result_dict2[primary_key]
            else:
                version2 = None

            #logger.debug("%r - %r - %r", primary_key, version1, version2)

            if version1 is not None and version2 is not None:
                # In both -> version changed or the same
                if version1.serialized_data == version2.serialized_data:
                    #logger.debug("same item: %s", version1)
                    same_items.append(version1)
                else:
                    changed_items.append((version1, version2))
            elif version1 is not None and version2 is None:
                # In 1 but not in 2 -> removed
                #logger.debug("%s %s", primary_key, missing_objects_pk2)
                #logger.debug("%s %s", repr(primary_key), repr(missing_objects_pk2))
                if primary_key in missing_objects_dict2:
                    missing_object = missing_objects_dict2[primary_key]
                    added_missing_objects.remove(missing_object)
                    same_missing_objects.add(missing_object)
                    continue

                removed_items.append(version1)
            elif version1 is None and version2 is not None:
                # In 2 but not in 1 -> added
                #logger.debug("added: %s", version2)
                added_items.append(version2)
            else:
                raise RuntimeError()

        self.M2M_CHANGE_INFO = {
            "changed_items": changed_items,
            "removed_items": removed_items,
            "added_items": added_items,
            "same_items": same_items,
            "same_missing_objects": same_missing_objects,
            "removed_missing_objects": removed_missing_objects,
            "added_missing_objects": added_missing_objects,
        }
        return self.M2M_CHANGE_INFO


    def debug(self):
        if not settings.DEBUG:
            return
        logger.debug("_______________________________")
        logger.debug(" *** CompareObjects debug: ***")
        logger.debug("changed: %s", self.changed())
        logger.debug("follow: %s", self.follow)

        debug1 = self.compare_obj1.get_debug()
        debug2 = self.compare_obj2.get_debug()
        debug_set1 = set(debug1)
        debug_set2 = set(debug2)

        logger.debug(" *** same attributes/values in obj1 and obj2: ***")
        intersection = debug_set1.intersection(debug_set2)
        for item in debug1:
            if item in intersection:
                logger.debug(item)

        logger.debug(" -" * 40)
        logger.debug(" *** unique attributes/values from obj1: ***")
        difference = debug_set1.difference(debug_set2)
        for item in debug1:
            if item in difference:
                logger.debug(item)

        logger.debug(" -" * 40)
        logger.debug(" *** unique attributes/values from obj2: ***")
        difference = debug_set2.difference(debug_set1)
        for item in debug2:
            if item in difference:
                logger.debug(item)

        logger.debug("-"*79)


class BaseCompareVersionAdmin(VersionAdmin):
    """
    Enhanced version of VersionAdmin with a flexible compare version API.

    You can define own method to compare fields in two ways (in this order):

        Create a method for a field via the field name, e.g.:
            "compare_%s" % field_name

        Create a method for every field by his internal type
            "compare_%s" % field.get_internal_type()

        see: https://docs.djangoproject.com/en/1.4/howto/custom-model-fields/#django.db.models.Field.get_internal_type

    If no method defined it would build a simple ndiff from repr().

    example:

    ----------------------------------------------------------------------------
    class MyModel(models.Model):
        date_created = models.DateTimeField(auto_now_add=True)
        last_update = models.DateTimeField(auto_now=True)
        user = models.ForeignKey(User)
        content = models.TextField()
        sub_text = models.ForeignKey(FooBar)

    class MyModelAdmin(CompareVersionAdmin):
        def compare_DateTimeField(self, obj, version1, version2, value1, value2):
            ''' compare all model datetime model field in ISO format '''
            date1 = value1.isoformat(" ")
            date2 = value2.isoformat(" ")
            html = html_diff(date1, date2)
            return html

        def compare_sub_text(self, obj, version1, version2, value1, value2):
            ''' field_name example '''
            return "%s -> %s" % (value1, value2)

    ----------------------------------------------------------------------------
    """

    # Template file used for the compare view:
    compare_template = "reversion-compare/compare.html"

    # list/tuple of field names for the compare view. Set to None for all existing fields
    compare_fields = None

    # list/tuple of field names to exclude from compare view.
    compare_exclude = None

    # change template from django-reversion to add compare selection form:
    object_history_template = "reversion-compare/object_history.html"

    # sort from new to old as default, see: https://github.com/etianen/django-reversion/issues/77
    history_latest_first = True

    def get_urls(self):
        """Returns the additional urls used by the Reversion admin."""
        urls = super(BaseCompareVersionAdmin, self).get_urls()
        admin_site = self.admin_site
        opts = self.model._meta
        info = opts.app_label, opts.module_name,
        reversion_urls = patterns("",
                                  url("^([^/]+)/history/compare/$", admin_site.admin_view(self.compare_view), name='%s_%s_compare' % info),
                                  )
        return reversion_urls + urls

    def _get_action_list(self, request, object_id, extra_context=None):
        """Renders the history view."""
        object_id = unquote(object_id) # Underscores in primary key get quoted to "_5F"
        opts = self.model._meta
        action_list = [
            {
                "version": version,
                "revision": version.revision,
                "url": reverse("%s:%s_%s_revision" % (self.admin_site.name, opts.app_label, opts.module_name), args=(quote(version.object_id), version.id)),
            }
            for version
            in self._order_version_queryset(self.revision_manager.get_for_object_reference(
                self.model,
                object_id,
            ).select_related("revision__user"))
        ]
        return action_list

    def history_view(self, request, object_id, extra_context=None):
        """Renders the history view."""
        action_list = self._get_action_list(request, object_id, extra_context=extra_context)

        if len(action_list) < 2:
            # Less than two history items aren't enough to compare ;)
            comparable = False
        else:
            comparable = True
            # for pre selecting the compare radio buttons depend on the ordering:
            if self.history_latest_first:
                action_list[0]["first"] = True
                action_list[1]["second"] = True
            else:
                action_list[-1]["first"] = True
                action_list[-2]["second"] = True

        # Compile the context.
        context = {
            "action_list": action_list,
            "comparable": comparable,
            "compare_view": True,
        }
        context.update(extra_context or {})
        return super(BaseCompareVersionAdmin, self).history_view(request, object_id, context)

    def fallback_compare(self, obj_compare):
        """
        Simply create a html diff from the repr() result.
        Used for every field which has no own compare method.
        """
        value1, value2 = obj_compare.to_string()
        html = html_diff(value1, value2)
        return html

    def _get_compare(self, obj_compare):
        """
        Call the methods to create the compare html part.
        Try:
            1. name scheme: "compare_%s" % field_name
            2. name scheme: "compare_%s" % field.get_internal_type()
            3. Fallback to: self.fallback_compare()
        """
        def _get_compare_func(suffix):
            func_name = "compare_%s" % suffix
            # logger.debug("func_name: %s", func_name)
            if hasattr(self, func_name):
                func = getattr(self, func_name)
                return func

        # Try method in the name scheme: "compare_%s" % field_name
        func = _get_compare_func(obj_compare.field_name)
        if func is not None:
            html = func(obj_compare)
            return html

        # Try method in the name scheme: "compare_%s" % field.get_internal_type()
        internal_type = obj_compare.field.get_internal_type()
        func = _get_compare_func(internal_type)
        if func is not None:
            html = func(obj_compare)
            return html

        # Fallback to self.fallback_compare()
        html = self.fallback_compare(obj_compare)
        return html

    def compare(self, obj, version1, version2):
        """
        Create a generic html diff from the obj between version1 and version2:

            A diff of every changes field values.

        This method should be overwritten, to create a nice diff view
        coordinated with the model.
        """
        diff = []

        # Create a list of all normal fields and append many-to-many fields
        fields = [field for field in obj._meta.fields]
        concrete_model = obj._meta.concrete_model
        fields += concrete_model._meta.many_to_many

        has_unfollowed_fields = False

        for field in fields:
            #logger.debug("%s %s %s", field, field.db_type, field.get_internal_type())

            field_name = field.name

            if self.compare_fields and field_name not in self.compare_fields:
                continue
            if self.compare_exclude and field_name in self.compare_exclude:
                continue

            obj_compare = CompareObjects(field, field_name, obj, version1, version2, self.revision_manager)
            #obj_compare.debug()

            is_related = obj_compare.is_related
            follow = obj_compare.follow
            if is_related and not follow:
                has_unfollowed_fields = True

            if not obj_compare.changed():
                # Skip all fields that aren't changed
                continue

            html = self._get_compare(obj_compare)

            diff.append({
                "field": field,
                "is_related": is_related,
                "follow": follow,
                "diff": html,
            })

        return diff, has_unfollowed_fields

    def compare_view(self, request, object_id, extra_context=None):
        """
        compare two versions.
        Used self.make_compare() to create the html diff.
        """
        if self.compare is None:
            raise Http404("Compare view not enabled.")

        form = SelectDiffForm(request.GET)
        if not form.is_valid():
            msg = "Wrong version IDs."
            if settings.DEBUG:
                msg += " (form errors: %s)" % ", ".join(form.errors)
            raise Http404(msg)

        version_id1 = form.cleaned_data["version_id1"]
        version_id2 = form.cleaned_data["version_id2"]

        object_id = unquote(object_id) # Underscores in primary key get quoted to "_5F"
        obj = get_object_or_404(self.model, pk=object_id)
        queryset = self.revision_manager.get_for_object(obj)
        version1 = get_object_or_404(queryset, pk=version_id1)
        version2 = get_object_or_404(queryset, pk=version_id2)

        if version_id1 > version_id2:
            # Compare always the newest one with the older one
            version1, version2 = version2, version1

        compare_data, has_unfollowed_fields = self.compare(obj, version1, version2)

        opts = self.model._meta

        context = {
            "opts": opts,
            "app_label": opts.app_label,
            "module_name": capfirst(opts.verbose_name),
            "title": _("Compare %(name)s") % {"name": version1.object_repr},
            "obj": obj,
            "compare_data": compare_data,
            "has_unfollowed_fields": has_unfollowed_fields,
            "version1": version1,
            "version2": version2,
            "changelist_url": reverse("%s:%s_%s_changelist" % (self.admin_site.name, opts.app_label, opts.module_name)),
            "change_url": reverse("%s:%s_%s_change" % (self.admin_site.name, opts.app_label, opts.module_name), args=(quote(obj.pk),)),
            "original": obj,
            "history_url": reverse("%s:%s_%s_history" % (self.admin_site.name, opts.app_label, opts.module_name), args=(quote(obj.pk),)),
        }
        extra_context = extra_context or {}
        context.update(extra_context)
        return render_to_response(self.compare_template or self._get_template_list("compare.html"),
            context, template.RequestContext(request))


class CompareVersionAdmin(BaseCompareVersionAdmin):
    """
    expand the base class with prepered compare methods.
    """
    def generic_add_remove(self, raw_value1, raw_value2, value1, value2):
        if raw_value1 is None:
            # a new values was added:
            context = {"value": value2}
            return render_to_string("reversion-compare/compare_generic_add.html", context)
        elif raw_value2 is None:
            # the existing value was removed:
            context = {"value": value1}
            return render_to_string("reversion-compare/compare_generic_remove.html", context)
        else:
            html = html_diff(value1, value2)
            return html

    def compare_ForeignKey(self, obj_compare):
        related1, related2 = obj_compare.get_related()
        obj_compare.debug()
        value1, value2 = unicode(related1), unicode(related2)
#        value1, value2 = repr(related1), repr(related2)
        return self.generic_add_remove(related1, related2, value1, value2)

    def simple_compare_ManyToManyField(self, obj_compare):
        """ comma separated list of all m2m objects """
        m2m1, m2m2 = obj_compare.get_many_to_many()
        old = ", ".join([unicode(item) for item in m2m1])
        new = ", ".join([unicode(item) for item in m2m2])
        html = html_diff(old, new)
        return html

    def compare_ManyToManyField(self, obj_compare):
        """ create a table for m2m compare """
        change_info = obj_compare.get_m2m_change_info()
        context = {"change_info": change_info}
        return render_to_string("reversion-compare/compare_generic_many_to_many.html", context)

#    compare_ManyToManyField = simple_compare_ManyToManyField

    def compare_FileField(self, obj_compare):
        value1 = obj_compare.value1
        value2 = obj_compare.value2

        # FIXME: Needed to not get 'The 'file' attribute has no file associated with it.'
        if value1:
            value1 = value1.url
        else:
            value1 = None

        if value2:
            value2 = value2.url
        else:
            value2 = None

        return self.generic_add_remove(value1, value2, value1, value2)

    def compare_DateTimeField(self, obj_compare):
        ''' compare all model datetime model field in ISO format '''
        context = {
            "date1": obj_compare.value1,
            "date2": obj_compare.value2,
        }
        return render_to_string("reversion-compare/compare_DateTimeField.html", context)

########NEW FILE########
__FILENAME__ = forms
"""Forms for django-reversion."""

from django import forms

class SelectDiffForm(forms.Form):
    version_id1 = forms.IntegerField(min_value=1)
    version_id2 = forms.IntegerField(min_value=1)

########NEW FILE########
__FILENAME__ = helpers
"""
    django-reversion helpers
    ~~~~~~~~~~~~~~~~~~~~~~~~
    
    A number of useful helper functions to automate common tasks.
    
    Used google-diff-match-patch [1] if installed, fallback to difflib.
    For installing use e.g. the unofficial package:
    
        pip install diff-match-patch
    
    [1] http://code.google.com/p/google-diff-match-patch/
"""


import difflib

from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode

from django.contrib import admin
from django.contrib.admin.sites import NotRegistered


try:
    # http://code.google.com/p/google-diff-match-patch/
    from diff_match_patch import diff_match_patch
except ImportError:
    google_diff_match_patch = False
else:
    google_diff_match_patch = True
    dmp = diff_match_patch()
#google_diff_match_patch = False # manually disable, for testing


def highlight_diff(diff_text):
    """
    Simple highlight a diff text in the way pygments do it ;)
    """
    html = ['<pre class="highlight">']
    for line in diff_text.splitlines():
        line = escape(line)
        if line.startswith("+"):
            line = '<ins>%s</ins>' % line
        elif line.startswith("-"):
            line = '<del>%s</del>' % line

        html.append(line)
    html.append("</pre>")
    html = "\n".join(html)

    return html


SEMANTIC = 1
EFFICIENCY = 2

# Change from ndiff to unified_diff if old/new values are more than X lines:
LINE_COUNT_4_UNIFIED_DIFF = 4


def format_range(start, stop):
    """
    Convert range to the "ed" format
    difflib._format_range_unified() is new in python 2.7
    see also: https://github.com/jedie/django-reversion-compare/issues/5
    """
    # Per the diff spec at http://www.unix.org/single_unix_specification/
    beginning = start + 1     # lines start numbering with one
    length = stop - start
    if length == 1:
        return '{0}'.format(beginning)
    if not length:
        beginning -= 1        # empty ranges begin at line just before the range
    return '{0},{1}'.format(beginning, length)


def unified_diff(a, b, n=3, lineterm='\n'):
    r"""
    simmilar to the original difflib.unified_diff except:
        - no fromfile/tofile and no fromfiledate/tofiledate info lines
        - newline before diff control lines and not after

    Example:

    >>> for line in unified_diff('one two three four'.split(),
    ...             'zero one tree four'.split(), lineterm=''):
    ...     print line                  # doctest: +NORMALIZE_WHITESPACE
    @@ -1,4 +1,4 @@
    +zero
     one
    -two
    -three
    +tree
     four
    """
    started = False
    for group in difflib.SequenceMatcher(None, a, b).get_grouped_opcodes(n):
        first, last = group[0], group[-1]
        file1_range = format_range(first[1], last[2])
        file2_range = format_range(first[3], last[4])

        if not started:
            started = True
            yield '@@ -{0} +{1} @@'.format(file1_range, file2_range)
        else:
            yield '{0}@@ -{1} +{2} @@'.format(lineterm, file1_range, file2_range)

        for tag, i1, i2, j1, j2 in group:
            if tag == 'equal':
                for line in a[i1:i2]:
                    yield ' ' + line
                continue
            if tag in ('replace', 'delete'):
                for line in a[i1:i2]:
                    yield '-' + line
            if tag in ('replace', 'insert'):
                for line in b[j1:j2]:
                    yield '+' + line


def html_diff(value1, value2, cleanup=SEMANTIC):
    """
    Generates a diff used google-diff-match-patch is exist or ndiff as fallback
    
    The cleanup parameter can be SEMANTIC, EFFICIENCY or None to clean up the diff
    for greater human readibility.
    """
    value1 = force_unicode(value1)
    value2 = force_unicode(value2)
    if google_diff_match_patch:
        # Generate the diff with google-diff-match-patch
        diff = dmp.diff_main(value1, value2)
        if cleanup == SEMANTIC:
            dmp.diff_cleanupSemantic(diff)
        elif cleanup == EFFICIENCY:
            dmp.diff_cleanupEfficiency(diff)
        elif cleanup is not None:
            raise ValueError("cleanup parameter should be one of SEMANTIC, EFFICIENCY or None.")
        html = dmp.diff_prettyHtml(diff)
        html = html.replace("&para;<br>", "</br>") # IMHO mark paragraphs are needlessly
    else:
        # fallback: use built-in difflib
        value1 = value1.splitlines()
        value2 = value2.splitlines()

        if len(value1) > LINE_COUNT_4_UNIFIED_DIFF or len(value2) > LINE_COUNT_4_UNIFIED_DIFF:
            diff = unified_diff(value1, value2, n=2)
        else:
            diff = difflib.ndiff(value1, value2)

        diff_text = "\n".join(diff)
        html = highlight_diff(diff_text)

    html = mark_safe(html)

    return html


def compare_queryset(first, second):
    """
    Simple compare two querysets (used for many-to-many field compare)
    XXX: resort results?
    """
    result = []
    for item in set(first).union(set(second)):
        if item not in first: # item was inserted
            item.insert = True
        elif item not in second: # item was deleted
            item.delete = True
        result.append(item)
    return result

def patch_admin(model, admin_site=None, AdminClass=None):
    """
    Enables version control with full admin integration for a model that has
    already been registered with the django admin site.

    This is excellent for adding version control to existing Django contrib
    applications.
    """
    admin_site = admin_site or admin.site
    try:
        ModelAdmin = admin_site._registry[model].__class__
    except KeyError:
        raise NotRegistered("The model {model} has not been registered with the admin site.".format(
            model = model,
            ))
        # Unregister existing admin class.
    admin_site.unregister(model)
    # Register patched admin class.
    if not AdminClass:
        from reversion_compare.admin import CompareVersionAdmin
        class PatchedModelAdmin(CompareVersionAdmin, ModelAdmin):
            pass
    else:
        class PatchedModelAdmin(AdminClass, ModelAdmin):
            pass

    admin_site.register(model, PatchedModelAdmin)


if __name__ == "__main__":
    import doctest
    print doctest.testmod(
#        verbose=True
        verbose=False
    )

########NEW FILE########
__FILENAME__ = models
# needed for unittest
########NEW FILE########
__FILENAME__ = tests
#!/usr/bin/env python
# coding: utf-8

"""
    django-reversion-compare unittests
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    I used the setup from reversion_compare_test_project !

    TODO:
        * models.OneToOneField()
        * models.IntegerField()

    :copyleft: 2012 by the django-reversion-compare team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""
import datetime


if __name__ == "__main__":
    # run unittest directly by execute manage.py from test project
    import os, sys
    os.environ['DJANGO_SETTINGS_MODULE'] = 'reversion_compare_test_project.settings'
    from django.core import management
    management.call_command("test", "reversion_compare", verbosity=2, traceback=True, interactive=False)
#    management.call_command("test", "reversion_compare.FactoryCarModelTest", verbosity=2, traceback=True, interactive=False)
#    management.call_command("test", "reversion_compare.PersonPetModelTest", verbosity=2, traceback=True, interactive=False)
    sys.exit()

from django.core.urlresolvers import reverse
from django.db.models.loading import get_models, get_app
from django.test import TestCase
from django.contrib.auth.models import User

#
try:
    import django_tools
except ImportError, err:
    msg = (
        "Please install django-tools for unittests"
        " - https://github.com/jedie/django-tools/"
        " - Original error: %s"
    ) % err
    raise ImportError(msg)
from django_tools.unittest_utils.BrowserDebug import debug_response

import reversion
from reversion import get_for_object
from reversion.models import Revision, Version

from reversion_compare import helpers

from reversion_compare_test_project.reversion_compare_test_app.models import SimpleModel, Person, Pet, \
    Factory, Car, VariantModel, CustomModel

# Needs to import admin module to register all models via CompareVersionAdmin/VersionAdmin
import reversion_compare_test_project.reversion_compare_test_app.admin
from reversion_compare_test_project.reversion_compare_test_app.admin import custom_revision_manager


class TestData(object):
    """
    Collection of all test data creation method.
    This will be also used from external scripts, too!
    """
    def __init__(self, verbose=False):
        self.verbose = verbose

    def create_all(self):
        """
        simple call all create_*_data() methods
        """
        for method_name in dir(self):
            if method_name.startswith("create_") and method_name.endswith("_data"):
                if self.verbose:
                    print "_"*79
                    print " *** %s ***" % method_name
                func = getattr(self, method_name)
                func()

    def create_Simple_data(self):
        with reversion.create_revision():
            item1 = SimpleModel.objects.create(text="version one")

        if self.verbose:
            print "version 1:", item1

        with reversion.create_revision():
            item1.text = "version two"
            item1.save()
            reversion.set_comment("simply change the CharField text.")

        if self.verbose:
            print "version 2:", item1

        return item1

    def create_FactoryCar_data(self):
        with reversion.create_revision():
            manufacture = Factory.objects.create(name="factory one")
            supplier1 = Factory.objects.create(name="always the same supplier")
            supplier2 = Factory.objects.create(name="would be deleted supplier")
            supplier3 = Factory.objects.create(name="would be removed supplier")
            car = Car.objects.create(
                name="motor-car one",
                manufacturer=manufacture
            )
            car.supplier.add(supplier1, supplier2, supplier3)
            car.save()
            reversion.set_comment("initial version 1")

        if self.verbose:
            print "version 1:", car
            # motor-car one from factory one supplier(s): always the same supplier, would be deleted supplier, would be removed supplier

        """ 1 to 2 diff:

        "manufacture" ForeignKey:
            "factory one" -> "factory I"

        "supplier" ManyToManyField:
            + new, would be renamed supplier
            - would be deleted supplier
            - would be removed supplier
            = always the same supplier
        """

        with reversion.create_revision():
            manufacture.name = "factory I"
            manufacture.save()
            supplier2.delete()
            supplier4 = Factory.objects.create(name="new, would be renamed supplier")
            car.supplier.add(supplier4)
            car.supplier.remove(supplier3)
            car.save()
            reversion.set_comment("version 2: change ForeignKey and ManyToManyField.")

        if self.verbose:
            print "version 2:", car
            # motor-car one from factory I supplier(s): always the same supplier, new, would be renamed supplier

        """ 2 to 3 diff:

        "name" CharField:
            "motor-car one" -> "motor-car II"

        "manufacture" ForeignKey:
            "factory I" -> "factory II"

        "supplier" ManyToManyField:
            new, would be renamed supplier -> not new anymore supplier
            = always the same supplier
        """

        with reversion.create_revision():
            car.name = "motor-car II"
            manufacture.name = "factory II"
            supplier4.name = "not new anymore supplier"
            supplier4.save()
            car.save()
            reversion.set_comment("version 3: change CharField, ForeignKey and ManyToManyField.")

        if self.verbose:
            print "version 3:", car
            # version 3: motor-car II from factory II supplier(s): always the same supplier, not new anymore supplier

        return car

    def create_PersonPet_data(self):
        with reversion.create_revision():
            pet1 = Pet.objects.create(name="would be changed pet")
            pet2 = Pet.objects.create(name="would be deleted pet")
            pet3 = Pet.objects.create(name="would be removed pet")
            pet4 = Pet.objects.create(name="always the same pet")
            person = Person.objects.create(name="Dave")
            person.pets.add(pet1, pet2, pet3, pet4)
            person.save()
            reversion.set_comment("initial version 1")

        if self.verbose:
            print "version 1:", person, person.pets.all()
            # Dave [<Pet: would be changed pet>, <Pet: would be deleted pet>, <Pet: would be removed pet>, <Pet: always the same pet>]

        """ 1 to 2 diff:

        "pets" ManyToManyField:
            would be changed pet -> Is changed pet
            - would be removed pet
            - would be deleted pet
            = always the same pet
        """

        with reversion.create_revision():
            pet1.name = "Is changed pet"
            pet1.save()
            pet2.delete()
            person.pets.remove(pet3)
            person.save()
            reversion.set_comment("version 2: change follow related pets.")

        if self.verbose:
            print "version 2:", person, person.pets.all()
            # Dave [<Pet: Is changed pet>, <Pet: always the same pet>]

        return pet1, pet2, person

    def create_VariantModel_data(self):
        with reversion.create_revision():
            item = VariantModel.objects.create(
                integer = 0,
                boolean = False,
                positive_integer = 0,
                big_integer = 0,
                time = datetime.time(hour=20, minute=15),
                date = datetime.date(year=1941, month=5, day=12), # Z3 was presented in germany ;)
                # PyLucid v0.0.1 release date:
                datetime = datetime.datetime(year=2005, month=8, day=19, hour=8, minute=13, second=24),
                decimal = 0,
                float = 0,
                ip_address = "192.168.0.1",
            )

        if self.verbose:
            print "version 1:", item

        return item

    def create_CustomModel_data(self):
        with reversion.create_revision():
            item1 = CustomModel.objects.create(text="version one")

        if self.verbose:
            print "version 1:", item1

        return item1


class BaseTestCase(TestCase):
    def setUp(self):
        super(BaseTestCase, self).setUp()

        self.user = User(username="test_user", is_staff=True, is_superuser=True)
        self.user.set_password("foobar")
        self.user.save()
        # Log the user in.
        self.client.login(username="test_user", password="foobar")

        # http://code.google.com/p/google-diff-match-patch/
        if helpers.google_diff_match_patch:
            # run all tests without google-diff-match-patch as default
            # some tests can activate it temporary
            helpers.google_diff_match_patch = False
            self.google_diff_match_patch = True
        else:
            self.google_diff_match_patch = False

    def tearDown(self):
        super(BaseTestCase, self).tearDown()

        Revision.objects.all().delete()
        Version.objects.all().delete()

    def assertContainsHtml(self, response, *args):
        for html in args:
            try:
                self.assertContains(response, html, html=True)
            except AssertionError, e:
                debug_response(response, msg="%s" % e) # from django-tools
                raise

    def assertNotContainsHtml(self, response, *args):
        for html in args:
            try:
                self.assertNotContains(response, html, html=True)
            except AssertionError, e:
                debug_response(response, msg="%s" % e) # from django-tools
                raise


class EnvironmentTest(BaseTestCase):
    def test_admin_login(self):
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<strong>test_user</strong>")
        #debug_response(response) # from django-tools

    def test_model_registering(self):
        test_app = get_app(app_label="reversion_compare_test_app")
        models = get_models(app_mod=test_app, include_auto_created=False, include_deferred=False, only_installed=True)
        default_registered = len(reversion.get_registered_models())
        custom_registered = len(custom_revision_manager.get_registered_models())
        self.assertEqual(default_registered + custom_registered, len(models))


class SimpleModelTest(BaseTestCase):
    """
    unittests that used reversion_compare_test_app.models.SimpleModel

    Tests for the basic functions.
    """
    def setUp(self):
        super(SimpleModelTest, self).setUp()
        test_data = TestData(verbose=False)
#        test_data = TestData(verbose=True)
        self.item1 = test_data.create_Simple_data()

        queryset = get_for_object(self.item1)
        self.version_ids = queryset.values_list("pk", flat=True)

    def test_initial_state(self):
        self.assertTrue(reversion.is_registered(SimpleModel))

        self.assertEqual(SimpleModel.objects.count(), 1)
        self.assertEqual(SimpleModel.objects.all()[0].text, "version two")

        self.assertEqual(reversion.get_for_object(self.item1).count(), 2)
        self.assertEqual(Revision.objects.all().count(), 2)
        self.assertEqual(len(self.version_ids), 2)
        self.assertEqual(Version.objects.all().count(), 2)

    def test_select_compare(self):
        response = self.client.get("/admin/reversion_compare_test_app/simplemodel/%s/history/" % self.item1.pk)
#        debug_response(response) # from django-tools
        self.assertContainsHtml(response,
            '<input type="submit" value="compare">',
            '<input type="radio" name="version_id1" value="%i" style="visibility:hidden" />' % self.version_ids[0],
            '<input type="radio" name="version_id2" value="%i" checked="checked" />' % self.version_ids[0],
            '<input type="radio" name="version_id1" value="%i" checked="checked" />' % self.version_ids[1],
            '<input type="radio" name="version_id2" value="%i" />' % self.version_ids[1],
        )

    def test_diff(self):
        response = self.client.get(
            "/admin/reversion_compare_test_app/simplemodel/%s/history/compare/" % self.item1.pk,
            data={"version_id2":self.version_ids[0], "version_id1":self.version_ids[1]}
        )
        #debug_response(response) # from django-tools

        self.assertContainsHtml(response,
            '<del>- version one</del>',
            '<ins>+ version two</ins>',
            '<blockquote>simply change the CharField text.</blockquote>', # edit comment
        )

        if self.google_diff_match_patch:
            # google-diff-match-patch is available
            helpers.google_diff_match_patch = True
            try:
                self.assertContainsHtml(response,
                    """
                    <p><span>version </span>
                    <del style="background:#ffe6e6;">one</del>
                    <ins style="background:#e6ffe6;">two</ins>
                    </p>
                    """,
                    '<blockquote>simply change the CharField text.</blockquote>', # edit comment
                )
            finally:
                helpers.google_diff_match_patch = False # revert


class FactoryCarModelTest(BaseTestCase):
    """
    unittests that used:
        reversion_compare_test_app.models.Factory
        reversion_compare_test_app.models.Car

    Factory & Car would be registered only in admin.py
    so no relation data would be stored
    """
    def setUp(self):
        super(FactoryCarModelTest, self).setUp()

        test_data = TestData(verbose=False)
#        test_data = TestData(verbose=True)
        self.car = test_data.create_FactoryCar_data()

        queryset = get_for_object(self.car)
        self.version_ids = queryset.values_list("pk", flat=True)

    def test_initial_state(self):
        self.assertTrue(reversion.is_registered(Factory))
        self.assertTrue(reversion.is_registered(Car))

        self.assertEqual(Revision.objects.all().count(), 3)
        self.assertEqual(len(self.version_ids), 3)
        self.assertEqual(Version.objects.all().count(), 10)

    def test_select_compare(self):
        response = self.client.get("/admin/reversion_compare_test_app/car/%s/history/" % self.car.pk)
#        debug_response(response) # from django-tools
        self.assertContainsHtml(response,
            '<input type="submit" value="compare">',
            '<input type="radio" name="version_id1" value="%i" style="visibility:hidden" />' % self.version_ids[0],
            '<input type="radio" name="version_id2" value="%i" checked="checked" />' % self.version_ids[0],
            '<input type="radio" name="version_id1" value="%i" checked="checked" />' % self.version_ids[1],
            '<input type="radio" name="version_id2" value="%i" />' % self.version_ids[1],
            '<input type="radio" name="version_id2" value="%i" />' % self.version_ids[2],
            '<input type="radio" name="version_id2" value="%i" />' % self.version_ids[2],
        )

    def test_diff1(self):
        response = self.client.get(
            "/admin/reversion_compare_test_app/car/%s/history/compare/" % self.car.pk,
            data={"version_id2":self.version_ids[1], "version_id1":self.version_ids[2]}
        )
#        debug_response(response) # from django-tools

        self.assertContainsHtml(response,
            '<h3>manufacturer<sup class="follow">*</sup></h3>',
            '<h3>supplier<sup class="follow">*</sup></h3>',
            '''
            <p class="highlight">
                <del>- would be deleted supplier</del><br />
                <del>- would be removed supplier</del><br />
                <ins>+ new, would be renamed supplier</ins><br />
                always the same supplier<sup class="follow">*</sup><br />
            </p>
            ''',
            '<h4 class="follow">Note:</h4>', # info for non-follow related informations
            '<blockquote>version 2: change ForeignKey and ManyToManyField.</blockquote>', # edit comment
        )

    def test_diff2(self):
        response = self.client.get(
            "/admin/reversion_compare_test_app/car/%s/history/compare/" % self.car.pk,
            data={"version_id2":self.version_ids[0], "version_id1":self.version_ids[1]}
        )
#        debug_response(response) # from django-tools

        self.assertContainsHtml(response,
            "<del>- motor-car one</del>",
            "<ins>+ motor-car II</ins>",

            '<h3>manufacturer<sup class="follow">*</sup></h3>',
            '<h3>supplier<sup class="follow">*</sup></h3>',
            '''
            <p class="highlight">
                <del>new, would be renamed supplier</del> &rarr; <ins>not new anymore supplier</ins><br />
                always the same supplier<sup class="follow">*</sup><br />
            </p>
            ''',
            '<h4 class="follow">Note:</h4>', # info for non-follow related informations
            '<blockquote>version 3: change CharField, ForeignKey and ManyToManyField.</blockquote>', # edit comment
        )


class PersonPetModelTest(BaseTestCase):
    """
    unittests that used:
        reversion_compare_test_app.models.Person
        reversion_compare_test_app.models.Pet

    Person & Pet are registered with the follow information, so that
    related data would be also stored in django-reversion

    see "Advanced model registration" here:
        https://github.com/etianen/django-reversion/wiki/Low-level-API
    """
    def setUp(self):
        super(PersonPetModelTest, self).setUp()

        test_data = TestData(verbose=False)
#        test_data = TestData(verbose=True)
        self.pet1, self.pet2, self.person = test_data.create_PersonPet_data()

        queryset = get_for_object(self.person)
        self.version_ids = queryset.values_list("pk", flat=True)

    def test_initial_state(self):
        self.assertTrue(reversion.is_registered(Pet))
        self.assertTrue(reversion.is_registered(Person))

        self.assertEqual(Pet.objects.count(), 3)

        self.assertEqual(reversion.get_for_object(self.pet1).count(), 2)
        self.assertEqual(Revision.objects.all().count(), 2)

    def test_select_compare(self):
        response = self.client.get("/admin/reversion_compare_test_app/person/%s/history/" % self.person.pk)
#        debug_response(response) # from django-tools
        self.assertContainsHtml(response,
            '<input type="submit" value="compare">',
            '<input type="radio" name="version_id1" value="%i" style="visibility:hidden" />' % self.version_ids[0],
            '<input type="radio" name="version_id2" value="%i" checked="checked" />' % self.version_ids[0],
            '<input type="radio" name="version_id1" value="%i" checked="checked" />' % self.version_ids[1],
            '<input type="radio" name="version_id2" value="%i" />' % self.version_ids[1],
        )

    def test_diff(self):
        response = self.client.get(
            "/admin/reversion_compare_test_app/person/%s/history/compare/" % self.person.pk,
            data={"version_id2":self.version_ids[0], "version_id1":self.version_ids[1]}
        )
#        debug_response(response) # from django-tools

        self.assertContainsHtml(response,
            """
            <p class="highlight">
                <del>would be changed pet</del> &rarr; <ins>Is changed pet</ins><br />
                <del>- would be deleted pet</del><br />
                <del>- would be removed pet</del><br />
                always the same pet<br />
            </p>
            """,
            "<blockquote>version 2: change follow related pets.</blockquote>", # edit comment
        )
        self.assertNotContainsHtml(response,
            "<h3>name</h3>", # person name doesn't changed
            'class="follow"'# All fields are under reversion control
        )

    def test_add_m2m(self):
        with reversion.create_revision():
            new_pet = Pet.objects.create(name="added pet")
            self.person.pets.add(new_pet)
            self.person.save()
            reversion.set_comment("version 3: add a pet")

        self.assertEqual(Revision.objects.all().count(), 3)
        self.assertEqual(Version.objects.all().count(), 12)

        queryset = get_for_object(self.person)
        version_ids = queryset.values_list("pk", flat=True)
        self.assertEqual(len(version_ids), 3)

        response = self.client.get("/admin/reversion_compare_test_app/person/%s/history/" % self.person.pk)
#        debug_response(response) # from django-tools
        self.assertContainsHtml(response,
            '<input type="submit" value="compare">',
            '<input type="radio" name="version_id1" value="%i" style="visibility:hidden" />' % version_ids[0],
            '<input type="radio" name="version_id2" value="%i" checked="checked" />' % version_ids[0],
            '<input type="radio" name="version_id1" value="%i" checked="checked" />' % version_ids[1],
            '<input type="radio" name="version_id2" value="%i" />' % version_ids[1],
            '<input type="radio" name="version_id2" value="%i" />' % version_ids[2],
            '<input type="radio" name="version_id2" value="%i" />' % version_ids[2],
        )

        response = self.client.get(
            "/admin/reversion_compare_test_app/person/%s/history/compare/" % self.person.pk,
            data={"version_id2":version_ids[0], "version_id1":version_ids[1]}
        )
#        debug_response(response) # from django-tools

        self.assertContainsHtml(response,
            """
            <p class="highlight">
                <ins>+ added pet</ins><br />
                Is changed pet<br />
                always the same pet<br />
            </p>
            """,
            "<blockquote>version 3: add a pet</blockquote>", # edit comment
        )
        self.assertNotContainsHtml(response,
            "<h3>name</h3>", # person name doesn't changed
            'class="follow"'# All fields are under reversion control
        )

    def test_m2m_not_changed(self):
        with reversion.create_revision():
            self.person.name = "David"
            self.person.save()
            reversion.set_comment("version 3: change the name")

        self.assertEqual(Revision.objects.all().count(), 3)
        self.assertEqual(Version.objects.all().count(), 11)

        queryset = get_for_object(self.person)
        version_ids = queryset.values_list("pk", flat=True)
        self.assertEqual(len(version_ids), 3)

        response = self.client.get("/admin/reversion_compare_test_app/person/%s/history/" % self.person.pk)
#        debug_response(response) # from django-tools
        self.assertContainsHtml(response,
            '<input type="submit" value="compare">',
            '<input type="radio" name="version_id1" value="%i" style="visibility:hidden" />' % version_ids[0],
            '<input type="radio" name="version_id2" value="%i" checked="checked" />' % version_ids[0],
            '<input type="radio" name="version_id1" value="%i" checked="checked" />' % version_ids[1],
            '<input type="radio" name="version_id2" value="%i" />' % version_ids[1],
            '<input type="radio" name="version_id2" value="%i" />' % version_ids[2],
            '<input type="radio" name="version_id2" value="%i" />' % version_ids[2],
        )

        response = self.client.get(
            "/admin/reversion_compare_test_app/person/%s/history/compare/" % self.person.pk,
            data={"version_id2":version_ids[0], "version_id1":version_ids[1]}
        )
#        debug_response(response) # from django-tools

        self.assertContainsHtml(response,
            '''
            <p><pre class="highlight">
            <del>- Dave</del>
            <ins>+ David</ins>
            </pre></p>
            ''',
            "<blockquote>version 3: change the name</blockquote>", # edit comment
        )
        self.assertNotContainsHtml(response,
            "pet",
            'class="follow"'# All fields are under reversion control
        )


class VariantModelTest(BaseTestCase):
    """
    Tests with VariantModel
    """
    def setUp(self):
        super(VariantModelTest, self).setUp()

        test_data = TestData(verbose=False)
#        test_data = TestData(verbose=True)
        self.item = test_data.create_VariantModel_data()

        queryset = get_for_object(self.item)
        self.version_ids = queryset.values_list("pk", flat=True)

    def test_initial_state(self):
        self.assertTrue(reversion.is_registered(VariantModel))

        self.assertEqual(VariantModel.objects.count(), 1)

        self.assertEqual(reversion.get_for_object(self.item).count(), 1)
        self.assertEqual(Revision.objects.all().count(), 1)

    def test_textfield(self):
        with reversion.create_revision():
            self.item.text = """\
first line
Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut
labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris
nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit
esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in
culpa qui officia deserunt mollit anim id est laborum.
last line"""
            self.item.save()

        with reversion.create_revision():
            self.item.text = """\
first line
Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut
labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris
nisi ut aliquip ex ea commodo consequat. Duis added aute irure dolor in reprehenderit in voluptate velit
esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in
culpa qui officia deserunt mollit anim id est laborum.
last line"""
            self.item.save()

        queryset = get_for_object(self.item)
        version_ids = queryset.values_list("pk", flat=True)
        self.assertEqual(len(version_ids), 3)

        response = self.client.get(
            "/admin/reversion_compare_test_app/variantmodel/%s/history/compare/" % self.item.pk,
            data={"version_id2":version_ids[0], "version_id1":version_ids[1]}
        )
#        debug_response(response) # from django-tools

        self.assertContains(response, """\
<del>-nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit</del>
<ins>+nisi ut aliquip ex ea commodo consequat. Duis added aute irure dolor in reprehenderit in voluptate velit</ins>
""")
        self.assertNotContains(response, "first line")
        self.assertNotContains(response, "last line")


class CustomModelTest(BaseTestCase):
    "Test a model which uses a custom reversion manager."

    def setUp(self):
        super(CustomModelTest, self).setUp()
        test_data = TestData(verbose=False)
        self.item = test_data.create_CustomModel_data()

    def test_initial_state(self):
        "Test initial data creation and model registration."
        self.assertTrue(custom_revision_manager.is_registered(CustomModel))
        self.assertEqual(CustomModel.objects.count(), 1)
        self.assertEqual(custom_revision_manager.get_for_object(self.item).count(), 1)
        self.assertEqual(Revision.objects.all().count(), 1)

    def test_text_diff(self):
        "Generate a new revision and check for a correctly generated diff."
        with reversion.create_revision():
            self.item.text = "version two"
            self.item.save()
        queryset = custom_revision_manager.get_for_object(self.item)
        version_ids = queryset.values_list("pk", flat=True)
        self.assertEqual(len(version_ids), 2)
        url_name = 'admin:%s_%s_compare' % (CustomModel._meta.app_label, CustomModel._meta.module_name)
        diff_url = reverse(url_name, args=(self.item.pk, ))
        data = {"version_id2": version_ids[0], "version_id1": version_ids[1]}
        response = self.client.get(diff_url, data=data)
        self.assertContains(response, "<del>- version one</del>")
        self.assertContains(response, "<ins>+ version two</ins>")

    def test_version_selection(self):
        "Generate two revisions and view the version history selection."
        with reversion.create_revision():
            self.item.text = "version two"
            self.item.save()
        with reversion.create_revision():
            self.item.text = "version three"
            self.item.save()
        queryset = custom_revision_manager.get_for_object(self.item)
        version_ids = queryset.values_list("pk", flat=True)
        self.assertEqual(len(version_ids), 3)
        url_name = 'admin:%s_%s_history' % (CustomModel._meta.app_label, CustomModel._meta.module_name)
        history_url = reverse(url_name, args=(self.item.pk, ))
        response = self.client.get(history_url)
        self.assertContainsHtml(response,
            '<input type="submit" value="compare">',
            '<input type="radio" name="version_id1" value="%i" style="visibility:hidden" />' % version_ids[0],
            '<input type="radio" name="version_id2" value="%i" checked="checked" />' % version_ids[0],
            '<input type="radio" name="version_id1" value="%i" checked="checked" />' % version_ids[1],
            '<input type="radio" name="version_id2" value="%i" />' % version_ids[1],
            '<input type="radio" name="version_id1" value="%i" />' % version_ids[2],
            '<input type="radio" name="version_id2" value="%i" />' % version_ids[2],
        )

########NEW FILE########
__FILENAME__ = create_test_data
#!/usr/bin/env python
# coding: utf-8

"""
    insert the test data from unittests to the test project database
    so you can easy play with them in a real admin page ;)
    
    this script will be called from "reset.sh"
    
    :copyleft: 2012 by the django-reversion-compare team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

import os
os.environ['DJANGO_SETTINGS_MODULE'] = "reversion_compare_test_project.settings"

import reversion
from reversion.models import Revision, Version

from reversion_compare.tests import TestData


if __name__ == "__main__":
    Revision.objects.all().delete()
    Version.objects.all().delete()
    
    TestData(verbose = True).create_all()

    print "\n+++ Test data from unittests created +++"

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
# coding: utf-8

import os

os.environ['DJANGO_SETTINGS_MODULE'] = "reversion_compare_test_project.settings"

from django.core.management import execute_manager
import imp
try:
    imp.find_module('settings') # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
    sys.exit(1)

import settings

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = admin
# coding: utf-8

"""
    admin
    ~~~~~
    
    All example admin classes would be used in django-reversion-compare unittests, too.

    :copyleft: 2012 by the django-reversion-compare team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""


from django.contrib import admin
from django.contrib.contenttypes.generic import GenericStackedInline
from django.template.loader import render_to_string

from reversion_compare.admin import CompareVersionAdmin
from reversion_compare.helpers import html_diff

from reversion_compare_test_project.reversion_compare_test_app.models import SimpleModel, Factory, Car, Person, Pet,\
    VariantModel, CustomModel

from reversion.models import Revision, Version
from reversion.revisions import RevisionManager


#------------------------------------------------------------------------------
# add django-revision models to admin, needful for debugging:

class RevisionAdmin(admin.ModelAdmin):
    list_display = ("id", "manager_slug", "date_created", "user", "comment")
    list_display_links = ("date_created",)
    date_hierarchy = 'date_created'
    ordering = ('-date_created',)
    list_filter = ("manager_slug", "user", "comment")
    search_fields = ("manager_slug", "user", "comment")

admin.site.register(Revision, RevisionAdmin)


class VersionAdmin(admin.ModelAdmin):
    list_display = ("object_repr", "revision", "type", "object_id", "content_type", "format",)
    list_display_links = ("object_repr", "object_id")
    list_filter = ("content_type", "format")
    search_fields = ("object_repr", "serialized_data")

admin.site.register(Version, VersionAdmin)

#------------------------------------------------------------------------------


class SimpleModelAdmin(CompareVersionAdmin):
    pass
admin.site.register(SimpleModel, SimpleModelAdmin)


class FactoryAdmin(CompareVersionAdmin):
    pass
admin.site.register(Factory, FactoryAdmin)

class CarAdmin(CompareVersionAdmin):
    pass
admin.site.register(Car, CarAdmin)


class PersonAdmin(CompareVersionAdmin):
    pass
admin.site.register(Person, PersonAdmin)

class PetAdmin(CompareVersionAdmin):
    pass
admin.site.register(Pet, PetAdmin)


class VariantModelAdmin(CompareVersionAdmin):
    pass
admin.site.register(VariantModel, VariantModelAdmin)


custom_revision_manager = RevisionManager("custom")

class CustomModelAdmin(CompareVersionAdmin):
    revision_manager = custom_revision_manager
admin.site.register(CustomModel, CustomModelAdmin)




"""
class RelatedModelInline(admin.StackedInline):
    model = RelatedModel


class GenericRelatedInline(GenericStackedInline):
    model = GenericRelatedModel


class ChildModelAdmin(CompareVersionAdmin):
    inlines = RelatedModelInline, GenericRelatedInline,
    list_display = ("parent_name", "child_name",)
    list_editable = ("child_name",)

admin.site.register(ChildModel, ChildModelAdmin)


class FlatExampleModelAdmin(CompareVersionAdmin):
    def compare_sub_text(self, obj, version1, version2, value1, value2):
        ''' field_name example '''
        return "%s -> %s" % (value1, value2)

admin.site.register(FlatExampleModel, FlatExampleModelAdmin)


class HobbyModelAdmin(CompareVersionAdmin):
    pass
admin.site.register(HobbyModel, HobbyModelAdmin)

class PersonModelAdmin(CompareVersionAdmin):
    pass
admin.site.register(PersonModel, PersonModelAdmin)

class GroupModelAdmin(CompareVersionAdmin):
    pass
admin.site.register(GroupModel, GroupModelAdmin)

class MembershipModelAdmin(CompareVersionAdmin):
    pass
admin.site.register(MembershipModel, MembershipModelAdmin)
"""

########NEW FILE########
__FILENAME__ = middleware
"""
Print the query log to standard out.

Useful for optimizing database calls.

Insipired by the method at: <http://www.djangosnippets.org/snippets/344/>
"""

class QueryLogMiddleware:

    def process_response(self, request, response):
        from django.conf import settings
        from django.db import connection

        if settings.DEBUG:
            queries = {}
            for query in connection.queries:
                sql = query["sql"]
                queries.setdefault(sql, 0)
                queries[sql] += 1
            duplicates = sum([count - 1 for count in queries.values()])
            print "------------------------------------------------------"
            print "Total Queries:     %s" % len(queries)
            print "Duplicate Queries: %s" % duplicates
            print
            for query, count in queries.items():
                print "%s x %s" % (count, query)
            print "------------------------------------------------------"
        return response


########NEW FILE########
__FILENAME__ = models
# coding: utf-8

"""
    models
    ~~~~~~
    
    All example models would be used for django-reversion-compare unittests, too.

    :copyleft: 2012 by the django-reversion-compare team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

import os

from django.contrib.auth.models import User
from django.contrib.contenttypes.generic import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import ugettext_lazy as _

import reversion_compare_test_project
import reversion


class SimpleModel(models.Model):
    text = models.CharField(max_length=255)
    def __unicode__(self):
        return "SimpleModel pk: %r text: %r" % (self.pk, self.text)

#------------------------------------------------------------------------------

"""
models with relationships

Factory & Car would be only registered in admin.py
so no relation data would be stored

Person & Pet would be registered here with the follow information, so that
related data would be also stored in django-reversion

see "Advanced model registration" here:
    https://github.com/etianen/django-reversion/wiki/Low-level-API
"""


class Factory(models.Model):
    name = models.CharField(max_length=128)
    def __unicode__(self):
        return self.name

class Car(models.Model):
    name = models.CharField(max_length=128)
    manufacturer = models.ForeignKey(Factory)
    supplier = models.ManyToManyField(Factory, related_name="suppliers", blank=True)
    def __unicode__(self):
        return "%s from %s supplier(s): %s" % (self.name, self.manufacturer, ", ".join([s.name for s in self.supplier.all()]))


class Pet(models.Model):
    name = models.CharField(max_length=100)
    def __unicode__(self):
        return self.name

class Person(models.Model):
    name = models.CharField(max_length=100)
    pets = models.ManyToManyField(Pet, blank=True)
    def __unicode__(self):
        return self.name

reversion.register(Person, follow=["pets"])
#reversion.register(Pet, follow=["person_set"])
reversion.register(Pet)

#------------------------------------------------------------------------------

class VariantModel(models.Model):
    """
    This model should contain all variants of all existing types, 
    without the related fields.
    
    TODO: Add tests for all variants!
    """
    boolean = models.BooleanField()
    null_boolean = models.NullBooleanField()
    
    char = models.CharField(max_length=1)
    text = models.TextField()
    # skip: models.SlugField()
    
    integer = models.IntegerField()
    integers = models.CommaSeparatedIntegerField(max_length=64)
    positive_integer = models.PositiveIntegerField()
    big_integer = models.BigIntegerField()
    # skip:
    # models.PositiveSmallIntegerField()
    # models.SmallIntegerField()

    time = models.TimeField()    
    date = models.DateField()
    datetime = models.DateTimeField()
    
    decimal = models.DecimalField(max_digits=5, decimal_places=3)
    float = models.FloatField()
    
    email = models.EmailField()
    url = models.URLField()
    
    filepath = models.FilePathField(
        path=os.path.abspath(os.path.dirname(reversion_compare_test_project.__file__))
    )

    ip_address = models.IPAddressField()
    # skip: models.GenericIPAddressField()
        

#------------------------------------------------------------------------------


class CustomModel(models.Model):
    "Model which uses a custom version manager."
    text = models.TextField()

"""

class ParentModel(models.Model):
    parent_name = models.CharField(max_length=255)
    def __unicode__(self):
        return self.parent_name


class ChildModel(ParentModel):
    child_name = models.CharField(max_length=255)
    file = models.FileField(upload_to="test", blank=True)
    genericrelatedmodel_set = GenericRelation("reversion_compare_test_app.GenericRelatedModel")

    def __unicode__(self):
        return u"%s > %s" % (self.parent_name, self.child_name)

    class Meta:
        verbose_name = _("child model")
        verbose_name_plural = _("child models")


class RelatedModel(models.Model):
    child_model = models.ForeignKey(ChildModel)
    related_name = models.CharField(max_length=255)
    file = models.FileField(upload_to="test", blank=True)

    def __unicode__(self):
        return self.related_name


class GenericRelatedModel(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.TextField()
    child_model = GenericForeignKey()
    generic_related_name = models.CharField(max_length=255)

    def __unicode__(self):
        return self.generic_related_name


class FlatExampleModel(models.Model):
    date_created = models.DateTimeField(auto_now_add=True)
    last_update = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, blank=True, null=True)
    content = models.TextField(help_text="Here is a content text field and this line is the help text from the model field.")
    child_model = models.ForeignKey(ChildModel, blank=True, null=True)

"""



########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
# coding: utf-8

"""
    django-reversion-compare unittests
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This file mainly exists to allow python setup.py test to work.
    You can also call it directly or call:
        ./setup.py test

    :copyleft: 2012 by the django-reversion-compare team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'reversion_compare_test_project.settings'
test_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, test_dir)

from django.conf import settings
from django.test.utils import get_runner, setup_test_environment
from django.test.simple import DjangoTestSuiteRunner


class TestSuiteRunner(DjangoTestSuiteRunner):
    """
    FIXME: startup south migrate here, because settings.SOUTH_TESTS_MIGRATE doesn't work.
    http://south.readthedocs.org/en/latest/unittests.html
    """
    def setup_databases(self, **kwargs):
        result = super(TestSuiteRunner, self).setup_databases()
        from django.core import management
        management.call_command("migrate", verbosity=self.verbosity - 1, traceback=True, interactive=False)
        return result


def runtests():
#    from django.core import management
#    management.call_command("test", "reversion_compare", verbosity=2, traceback=True, interactive=False)

#    TestRunner = get_runner(settings)
#    test_runner = TestRunner(verbosity=2, interactive=True)

    test_runner = TestSuiteRunner(verbosity=2, interactive=True)

    failures = test_runner.run_tests(['reversion_compare'])
    sys.exit(bool(failures))


if __name__ == '__main__':
    runtests()

########NEW FILE########
__FILENAME__ = settings
# coding: utf-8

"""
    Django settings for test_project project.
"""

import os
import sys

#for path in sys.path:print path

#import reversion
#import reversion_compare
import reversion_compare_test_project

def _pkg_path(obj, subdir=None):
    abspath = os.path.abspath(os.path.dirname(obj.__file__))
    if subdir is not None:
        abspath = os.path.join(abspath, subdir)
    return abspath

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
#        'NAME': _pkg_path(reversion_compare_test_project, "test.db3"),
        'NAME': os.path.join(os.path.abspath(os.path.dirname(__file__)), "test.db3"),
    }
}

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

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
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = "change me, i'm not secret"

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
    "reversion.middleware.RevisionMiddleware",
    #"reversion_compare_test_project.reversion_compare_test_app.middleware.QueryLogMiddleware",
)

ROOT_URLCONF = 'reversion_compare_test_project.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    'django.contrib.admindocs',
    'reversion',
    'reversion_compare',
    'reversion_compare_test_project.reversion_compare_test_app',
    'south',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
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

########NEW FILE########
__FILENAME__ = urls
# coding: utf-8

from django.conf.urls import patterns, include, url
from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
from django.shortcuts import redirect
admin.autodiscover()

urlpatterns = patterns('',
    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),

    url(
        r'^media/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': settings.MEDIA_ROOT}
    ),

    # redirect root view to admin page:
    url(r'^$', lambda x: redirect("admin:index")),
)

########NEW FILE########
