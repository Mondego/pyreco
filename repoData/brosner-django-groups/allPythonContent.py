__FILENAME__ = base
import datetime
import warnings

from django.db import models
from django.db.models.options import FieldDoesNotExist
from django.db.models.query import QuerySet
from django.db.models.sql.constants import LOOKUP_SEP
from django.utils.translation import ugettext_lazy as _

from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType



def _get_queryset(klass):
    """
    Returns a QuerySet from a Model, Manager, or QuerySet. Created to make
    get_object_or_404 and get_list_or_404 more DRY.
    
    Pulled from django.shortcuts
    """
    
    if isinstance(klass, QuerySet):
        return klass
    elif isinstance(klass, models.Manager):
        manager = klass
    else:
        manager = klass._default_manager
    return manager.all()


class GroupAware(models.Model):
    """
    A mixin abstract base model to use on models you want to make group-aware.
    """
    
    group_content_type = models.ForeignKey(ContentType, null=True, blank=True)
    group_object_id = models.PositiveIntegerField(null=True, blank=True)
    group = generic.GenericForeignKey("group_content_type", "group_object_id")
    
    class Meta:
        abstract = True


class GroupBase(models.Model):
    
    slug_attr = "slug"
    
    class Meta(object):
        abstract = True
    
    def member_queryset(self):
        if not hasattr(self, "_members_field"):
            # look for the common case of a m2m named members (in some cases
            # the related_name of the user FK on the intermediary model might
            # be named members and we need User instances)
            try:
                field = self._meta.get_field("members")
            except FieldDoesNotExist:
                raise NotImplementedError("You must define a member_queryset for %s" % str(self.__class__))
            else:
                self._members_field = field
        else:
            field = self._members_field
        if isinstance(field, models.ManyToManyField) and issubclass(field.rel.to, User):
            return self.members.all()
        else:
            raise NotImplementedError("You must define a member_queryset for %s" % str(self.__class__))
    
    def user_is_member(self, user):
        return user in self.member_queryset()
    
    def _group_gfk_field(self, model, join=None, field_name=None):
        opts = model._meta
        if field_name is None:
            field_name = "group"
        if join is not None:
            # see if we can get the model where the field actually lives
            parts = join.split(LOOKUP_SEP)
            for name in parts:
                f, model, direct, m2m = opts.get_field_by_name(name)
                # not handling the model is not None case (proxied models I think)
                if direct:
                    if m2m or f.rel:
                        opts = f.rel.to._meta
                    else:
                        break
                else:
                    opts = f.opts
        try:
            field = [f for f in opts.virtual_fields if f.name == field_name][0]
        except IndexError:
            from django.db.models.loading import cache as app_cache
            model = app_cache.get_model(opts.app_label, opts.module_name)
            raise LookupError("Unable to find generic foreign key named '%s' "
                "on %r\nThe model may have a different name or it does not "
                "exist." % (
                    field_name,
                    model,
                ))
        return field
    
    def lookup_params(self, model):
        content_type = ContentType.objects.get_for_model(self)
        group_gfk = self._group_gfk_field(model)
        params = {
            group_gfk.fk_field: self.id,
            group_gfk.ct_field: content_type,
        }
        return params
    
    def content_objects(self, queryable, join=None, gfk_field=None):
        queryset = _get_queryset(queryable)
        content_type = ContentType.objects.get_for_model(self)
        group_gfk = self._group_gfk_field(queryset.model, join=join, field_name=gfk_field)
        if join:
            lookup_kwargs = {
                "%s__%s" % (join, group_gfk.fk_field): self.id,
                "%s__%s" % (join, group_gfk.ct_field): content_type,
            }
        else:
            lookup_kwargs = {
                group_gfk.fk_field: self.id,
                group_gfk.ct_field: content_type,
            }
        content_objects = queryset.filter(**lookup_kwargs)
        return content_objects
    
    def associate(self, instance, commit=True, gfk_field=None):
        group_gfk = self._group_gfk_field(instance, field_name=gfk_field)
        setattr(instance, group_gfk.fk_field, self.id)
        setattr(instance, group_gfk.ct_field, ContentType.objects.get_for_model(self))
        if commit:
            instance.save()
        return instance
    
    def get_url_kwargs(self):
        kwargs = {}
        if hasattr(self, "group") and self.group:
            kwargs.update(self.group.get_url_kwargs())
        slug = getattr(self, self.slug_attr)
        kwargs.update({"%s_slug" % self._meta.object_name.lower(): slug})
        return kwargs


class Group(GroupBase, GroupAware):
    """
    a group is a group of users with a common interest
    """
    
    slug = models.SlugField(_("slug"), unique=True)
    name = models.CharField(_("name"), max_length=80, unique=True)
    creator = models.ForeignKey(User, verbose_name=_("creator"), related_name="%(class)s_created")
    created = models.DateTimeField(_("created"), default=datetime.datetime.now)
    description = models.TextField(_("description"))
    
    def __unicode__(self):
        return self.name
    
    class Meta(object):
        abstract = True


class GroupScopedId(models.Model):
    """
    a model to store scoped IDs for tasks (specific to a group)
    """
    
    content_type = models.ForeignKey(ContentType, null=True, blank=True)
    object_id = models.IntegerField(null=True, blank=True)
    group = generic.GenericForeignKey()
    
    scoped_number = models.IntegerField()
    
    class Meta:
        abstract = True
        unique_together = (("content_type", "object_id", "scoped_number"),)

########NEW FILE########
__FILENAME__ = bridge
import sys

from django.shortcuts import render_to_response
from django.conf.urls.defaults import patterns, url as urlpattern
from django.core.urlresolvers import RegexURLPattern, RegexURLResolver, reverse as dreverse

from django.contrib.contenttypes.models import ContentType


class ContentBridge(object):
    
    def __init__(self, group_model, content_app_name=None, urlconf_aware=True):
        self.parent_bridge = None
        self.group_model = group_model
        self.urlconf_aware = urlconf_aware
        
        if content_app_name is None:
            self.content_app_name = group_model._meta.app_label
        else:
            self.content_app_name = content_app_name
        
        # attach the bridge to the model itself. we need to access it when
        # using groupurl to get the correct prefix for URLs for the given
        # group.
        self.group_model.content_bridge = self
    
    def include_urls(self, module_name, url_prefix, kwargs=None):
        if kwargs is None:
            kwargs = {}
        
        prefix = self.content_app_name
        
        __import__(module_name)
        module = sys.modules[module_name]
        
        if hasattr(module, "bridge"):
            module.bridge.parent_bridge = self
        
        urls = []
        
        for url in module.urlpatterns:
            extra_kwargs = {"bridge": self}
            
            if isinstance(url, RegexURLPattern):
                regex = url_prefix + url.regex.pattern.lstrip("^")
                
                if url._callback:
                    callback = url._callback
                else:
                    callback = url._callback_str
                
                if url.name:
                    name = url.name
                else:
                    # @@@ this seems sketchy
                    name = ""
                name = "%s_%s" % (prefix, name)
                
                extra_kwargs.update(kwargs)
                extra_kwargs.update(url.default_args)
                
                urls.append(urlpattern(regex, callback, extra_kwargs, name))
            else:
                # i don't see this case happening much at all. this case will be
                # executed likely if url is a RegexURLResolver. nesting an include
                # at the content object level may not be supported, but maybe the
                # code below works. i don't have time to test it, but if you are
                # reading this because something is broken then give it a shot.
                # then report back :-)
                raise Exception("ContentBridge.include_urls does not support a nested include.")
                
                # regex = url_prefix + url.regex.pattern.lstrip("^")
                # urlconf_name = url.urlconf_name
                # extra_kwargs.update(kwargs)
                # extra_kwargs.update(url.default_kwargs)
                # final_urls.append(urlpattern(regex, [urlconf_name], extra_kwargs))
        
        return patterns("", *urls)
    
    @property
    def _url_name_prefix(self):
        if self.urlconf_aware:
            parent_prefix = ""
            if self.parent_bridge is not None:
                parent_prefix = self.parent_bridge._url_name_prefix
            return "%s%s_" % (parent_prefix, self.content_app_name)
        else:
            return ""
    
    def reverse(self, view_name, group, kwargs=None):
        if kwargs is None:
            kwargs = {}
        
        final_kwargs = {}
        
        final_kwargs.update(group.get_url_kwargs())
        final_kwargs.update(kwargs)
        
        return dreverse("%s%s" % (self._url_name_prefix, view_name), kwargs=final_kwargs)
    
    def render(self, template_name, context, context_instance=None):
        # @@@ this method is practically useless -- consider removing it.
        ctype = ContentType.objects.get_for_model(self.group_model)
        return render_to_response([
            "%s/%s/%s" % (ctype.app_label, self.content_app_name, template_name),
            "%s/%s" % (self.content_app_name, template_name),
        ], context, context_instance=context_instance)
    
    def group_base_template(self, template_name="content_base.html"):
        return "%s/%s" % (self.content_app_name, template_name)
    
    def get_group(self, kwargs):
        
        lookup_params = {}
        
        if self.parent_bridge is not None:
            parent_group = self.parent_bridge.get_group(kwargs)
            lookup_params.update(parent_group.lookup_params(self.group_model))
        else:
            parent_group = None
        
        slug = kwargs.pop("%s_slug" % self.group_model._meta.object_name.lower())
        
        lookup_params.update({
            "slug": slug,
        })
        
        group = self.group_model._default_manager.get(**lookup_params)
        
        if parent_group:
            # cache parent_group on GFK to prevent database hits later on
            group.group = parent_group
        
        return group
        
########NEW FILE########
__FILENAME__ = helpers
from django.db import connection, transaction


qn = connection.ops.quote_name


def generate_next_scoped_id(content_object, scoped_id_model):
    """
    generates an ID unique to a content_object scoped in a group (if it has
    one).
    """
    
    kwargs = {}
    if content_object.group:
        kwargs.update({
            "content_type": content_object.content_type,
            "object_id": content_object.object_id,
        })
    get_or_create = scoped_id_model._default_manager.get_or_create
    scoped_id, created = get_or_create(**dict(kwargs, **{
        "defaults": {
            "scoped_number": 1,
        }
    }))
    if not created:
        sql = """
        UPDATE %(table_name)s
        SET scoped_number = scoped_number + 1
        """ % {"table_name": qn(scoped_id_model._meta.db_table)}
        if content_object.group:
            sql += """
            WHERE
                content_type_id = %(content_type_id)s AND
                object_id = %(object_id)s
            """ % {
                "content_type_id": kwargs["content_type"].pk,
                "object_id": kwargs["object_id"],
            }
        try:
            try:
                transaction.enter_transaction_management()
                transaction.managed(True)
                
                cursor = connection.cursor()
                cursor.execute(sql)
                
                # we modified data, mark dirty
                transaction.set_dirty()
                
                scoped_id = scoped_id_model._default_manager.get(pk=scoped_id.pk)
                transaction.commit()
            except:
                transaction.rollback()
                raise
        finally:
            transaction.leave_transaction_management()
            
    return scoped_id.scoped_number

########NEW FILE########
__FILENAME__ = internals
import copy



class GroupDummy(object):
    
    def __nonzero__(self):
        return False


class GroupRequestHelper(object):
    
    def __init__(self, request, group):
        self.request = request
        self.group = group
    
    def __deepcopy__(self, memo):
        obj = copy.copy(self)
        for k, v in self.__dict__.iteritems():
            if k == "request":
                continue
            setattr(obj, k, copy.deepcopy(v, memo))
        obj.request = self.request
        memo[id(self)] = obj
        return obj
    
    def user_is_member(self):
        if not self.request.user.is_authenticated():
            is_member = False
        else:
            if self.group:
                is_member = self.group.user_is_member(self.request.user)
            else:
                is_member = True
        return is_member

########NEW FILE########
__FILENAME__ = middleware
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.utils.functional import curry

from groups.internals import GroupDummy, GroupRequestHelper



class GroupAwareMiddleware(object):
    
    def process_view(self, request, view, view_args, view_kwargs):
        
        bridge = view_kwargs.pop("bridge", None)
        
        if bridge:
            try:
                group = bridge.get_group(view_kwargs)
            except ObjectDoesNotExist:
                raise Http404
        else:
            group = GroupDummy()
        
        # attach a request helper
        group.request = GroupRequestHelper(request, group)
        
        request.group = group
        request.bridge = bridge
        
        return None

########NEW FILE########
__FILENAME__ = group_tags
from django import template
from django.utils.encoding import smart_str
from django.core.urlresolvers import reverse, NoReverseMatch
from django.db.models import get_model
from django.db.models.query import QuerySet


register = template.Library()


class GroupURLNode(template.Node):
    def __init__(self, view_name, group, kwargs, asvar):
        self.view_name = view_name
        self.group = group
        self.kwargs = kwargs
        self.asvar = asvar
    
    def render(self, context):
        url = ""
        group = self.group.resolve(context)
        
        kwargs = {}
        for k, v in self.kwargs.items():
            kwargs[smart_str(k, "ascii")] = v.resolve(context)
        
        if group:
            bridge = group.content_bridge
            try:
                url = bridge.reverse(self.view_name, group, kwargs=kwargs)
            except NoReverseMatch:
                if self.asvar is None:
                    raise
        else:
            try:
                url = reverse(self.view_name, kwargs=kwargs)
            except NoReverseMatch:
                if self.asvar is None:
                    raise
                
        if self.asvar:
            context[self.asvar] = url
            return ""
        else:
            return url


class ContentObjectsNode(template.Node):
    def __init__(self, group_var, model_name_var, gfk_field_var, context_var):
        self.group_var = template.Variable(group_var)
        self.model_name_var = template.Variable(model_name_var)
        if gfk_field_var is not None:
            self.gfk_field_var = template.Variable(gfk_field_var)
        else:
            self.gfk_field_var = None
        self.context_var = context_var
    
    def render(self, context):
        group = self.group_var.resolve(context)
        model_name = self.model_name_var.resolve(context)
        if self.gfk_field_var is not None:
            gfk_field = self.gfk_field_var.resolve(context)
        else:
            gfk_field = None
        
        if isinstance(model_name, QuerySet):
            model = model_name
        else:
            app_name, model_name = model_name.split(".")
            model = get_model(app_name, model_name)
        
        context[self.context_var] = group.content_objects(model, gfk_field=gfk_field)
        return ""


class ObjectGroupUrlNode(template.Node):
    def __init__(self, obj, group, asvar):
        self.obj_var = template.Variable(obj)
        self.group = group
        self.asvar = asvar
    
    def render(self, context):
        url = ""
        obj = self.obj_var.resolve(context)
        group = self.group.resolve(context)
        
        try:
            url = obj.get_absolute_url(group)
        except NoReverseMatch:
            if self.asvar is None:
                raise
        
        if self.asvar:
            context[self.asvar] = url
            return ""
        else:
            return url


@register.tag
def groupurl(parser, token):
    bits = token.contents.split()
    tag_name = bits[0]
    if len(bits) < 3:
        raise template.TemplateSyntaxError("'%s' takes at least two arguments"
            " (path to a view and a group)" % tag_name)
    
    view_name = bits[1]
    group = parser.compile_filter(bits[2])
    args = []
    kwargs = {}
    asvar = None
    
    if len(bits) > 3:
        bits = iter(bits[3:])
        for bit in bits:
            if bit == "as":
                asvar = bits.next()
                break
            else:
                for arg in bit.split(","):
                    if "=" in arg:
                        k, v = arg.split("=", 1)
                        k = k.strip()
                        kwargs[k] = parser.compile_filter(v)
                    elif arg:
                        raise template.TemplateSyntaxError("'%s' does not support non-kwargs arguments." % tag_name)
    
    return GroupURLNode(view_name, group, kwargs, asvar)


@register.tag
def content_objects(parser, token):
    """
    Basic usage::
    
        {% content_objects group "tasks.Task" as tasks %}
    
    or if you need to specify a custom generic foreign key field (default is
    group)::
    
        {% content_objects group "tasks.Task" "content_object" as tasks %}
    """
    bits = token.split_contents()
    if len(bits) not in [5, 6]:
        raise template.TemplateSyntaxError("'%s' requires five or six arguments." % bits[0])
    else:
        if len(bits) == 5:
            return ContentObjectsNode(bits[1], bits[2], None, bits[4])
        else:
            return ContentObjectsNode(bits[1], bits[2], bits[3], bits[5])


@register.tag
def object_group_url(parser, token):
    """
    given an object and an optional group, call get_absolute_url passing the
    group variable::
    
        {% object_group_url task group %}
    """
    bits = token.contents.split()
    tag_name = bits[0]
    if len(bits) < 3:
        raise template.TemplateSyntaxError("'%s' takes at least two arguments"
            " (object and a group)" % tag_name)
    
    obj = bits[1]
    group = parser.compile_filter(bits[2])
    
    if len(bits) > 3:
        if bits[3] != "as":
            raise template.TemplateSyntaxError("'%s' requires the forth"
                " argument to be 'as'" % tag_name)
        try:
            asvar = bits[4]
        except IndexError:
            raise template.TemplateSyntaxError("'%s' requires an argument"
                " after 'as'" % tag_name)
    
    return ObjectGroupUrlNode(obj, group, asvar)

########NEW FILE########
